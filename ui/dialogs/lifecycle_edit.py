"""Dialog — edit lifecycle stages 2–5 for a project material."""

import sqlite3
from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.lifecycle import current_stage
from db.models import fixture_group as fixture_group_model
from db.models import project_material as pm_model
from ui.widgets.stage_indicator import StageIndicator


def _section_header(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #1565C0;")
    return lbl


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


def _field_row(label: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    lbl = QLabel(label)
    lbl.setFixedWidth(150)
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    row.addWidget(lbl)
    row.addWidget(widget, stretch=1)
    return row


class LifecycleEditDialog(QDialog):
    """Edit lifecycle stages 2–5 for a single project material.

    Stage 1 data (review_status on the fixture group) is read-only here.
    Stages 2–5 fields are enabled progressively based on prerequisites:
      Stage 2: requires fixture_group.review_status in approved set
      Stage 3: read-only PO info (assigned via PO dialog, not here)
      Stage 4: requires material.po_id is set; checkbox sets stage=4 explicitly
      Stage 5: requires stage >= 4; qty_received / fully_received / receipt info
    """

    def __init__(self, conn: sqlite3.Connection, material_id: int, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.material_id = material_id
        self._material: dict = {}
        self._fixture_group: dict = {}
        self.setWindowTitle("Edit Lifecycle Stages")
        self.setMinimumWidth(500)
        self._load_data()
        self._build_ui()
        self._prefill()
        self._update_enabled_states()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        row = pm_model.get(self.conn, self.material_id)
        if row is None:
            raise ValueError(f"ProjectMaterial #{self.material_id} not found")
        self._material = dict(row)
        fg_row = fixture_group_model.get(self.conn, self._material["fixture_group_id"])
        if fg_row is None:
            raise ValueError(f"FixtureGroup #{self._material['fixture_group_id']} not found")
        self._fixture_group = dict(fg_row)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(12, 12, 12, 12)

        # Material identity title
        mat = self._material
        tag = self._fixture_group.get("tag_designation") or ""
        mfr = mat.get("product_manufacturer") or mat.get("manufacturer") or ""
        model_num = mat.get("product_model_number") or mat.get("model_number") or ""
        ident = f"{mfr} {model_num}".strip()
        title_text = f"{tag}  —  {ident}" if tag and ident else (tag or ident)
        title_lbl = QLabel(title_text)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        root.addWidget(title_lbl)
        root.addWidget(_divider())

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        inner = QVBoxLayout(content)
        inner.setSpacing(8)
        inner.setContentsMargins(0, 0, 8, 0)

        # Stage indicator
        stage_val = current_stage(self._material, self._fixture_group)
        self._stage_indicator = StageIndicator(stage_val)
        inner.addWidget(self._stage_indicator)
        inner.addWidget(_divider())

        # ── Stage 1: Review status (read-only) ────────────────────────
        inner.addWidget(_section_header("Stage 1 — Submittal Review"))
        review = self._fixture_group.get("review_status") or "Pending"
        review_lbl = QLabel(review)
        review_lbl.setStyleSheet("color: #555;")
        inner.addLayout(_field_row("Review Status:", review_lbl))
        inner.addWidget(_divider())

        # ── Stage 2: Supplier notified ────────────────────────────────
        inner.addWidget(_section_header("Stage 2 — Supplier Notified"))

        self._stage2_widget = QWidget()
        stage2_layout = QVBoxLayout(self._stage2_widget)
        stage2_layout.setContentsMargins(0, 0, 0, 0)
        stage2_layout.setSpacing(6)

        self._chk_supplier_notified = QCheckBox("Supplier has been notified")
        stage2_layout.addWidget(self._chk_supplier_notified)

        self._de_supplier_notified = QDateEdit()
        self._de_supplier_notified.setCalendarPopup(True)
        self._de_supplier_notified.setDisplayFormat("yyyy-MM-dd")
        self._de_supplier_notified.setDate(date.today())
        stage2_layout.addLayout(_field_row("Notification Date:", self._de_supplier_notified))

        self._txt_supplier_notes = QPlainTextEdit()
        self._txt_supplier_notes.setFixedHeight(60)
        self._txt_supplier_notes.setPlaceholderText("Optional notes…")
        stage2_layout.addLayout(_field_row("Notes:", self._txt_supplier_notes))

        inner.addWidget(self._stage2_widget)
        inner.addWidget(_divider())

        # ── Stage 3: PO issued (read-only) ────────────────────────────
        inner.addWidget(_section_header("Stage 3 — PO Issued"))

        self._stage3_widget = QWidget()
        stage3_layout = QVBoxLayout(self._stage3_widget)
        stage3_layout.setContentsMargins(0, 0, 0, 0)
        stage3_layout.setSpacing(4)

        po_id = self._material.get("po_id")
        po_num = self._material.get("po_number") or (f"PO #{po_id}" if po_id else "No PO assigned")
        po_lbl = QLabel(po_num)
        po_lbl.setStyleSheet("color: #555;")
        stage3_layout.addLayout(_field_row("Purchase Order:", po_lbl))

        inner.addWidget(self._stage3_widget)
        inner.addWidget(_divider())

        # ── Stage 4: Quantities released ──────────────────────────────
        inner.addWidget(_section_header("Stage 4 — Quantities Released"))

        self._stage4_widget = QWidget()
        stage4_layout = QVBoxLayout(self._stage4_widget)
        stage4_layout.setContentsMargins(0, 0, 0, 0)
        stage4_layout.setSpacing(6)

        self._chk_qty_released = QCheckBox("Quantities released to supplier")
        stage4_layout.addWidget(self._chk_qty_released)

        inner.addWidget(self._stage4_widget)
        inner.addWidget(_divider())

        # ── Stage 5: Material received ────────────────────────────────
        inner.addWidget(_section_header("Stage 5 — Material Received"))

        self._stage5_widget = QWidget()
        stage5_layout = QVBoxLayout(self._stage5_widget)
        stage5_layout.setContentsMargins(0, 0, 0, 0)
        stage5_layout.setSpacing(6)

        self._spn_qty_received = QSpinBox()
        self._spn_qty_received.setRange(0, 99999)
        stage5_layout.addLayout(_field_row("Qty Received:", self._spn_qty_received))

        self._chk_fully_received = QCheckBox("Fully received")
        stage5_layout.addWidget(self._chk_fully_received)

        self._de_receipt_date = QDateEdit()
        self._de_receipt_date.setCalendarPopup(True)
        self._de_receipt_date.setDisplayFormat("yyyy-MM-dd")
        self._de_receipt_date.setDate(date.today())
        stage5_layout.addLayout(_field_row("Receipt Date:", self._de_receipt_date))

        self._txt_receipt_notes = QPlainTextEdit()
        self._txt_receipt_notes.setFixedHeight(60)
        self._txt_receipt_notes.setPlaceholderText("Optional receipt notes…")
        stage5_layout.addLayout(_field_row("Receipt Notes:", self._txt_receipt_notes))

        inner.addWidget(self._stage5_widget)
        inner.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # ── Buttons ───────────────────────────────────────────────────
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

        # Live enable/disable updates
        self._chk_supplier_notified.toggled.connect(self._update_enabled_states)
        self._chk_qty_released.toggled.connect(self._update_enabled_states)

    # ------------------------------------------------------------------
    # Pre-fill from current values
    # ------------------------------------------------------------------

    def _prefill(self) -> None:
        mat = self._material

        # Stage 2
        self._chk_supplier_notified.setChecked(bool(mat.get("supplier_notified")))

        notif_date = mat.get("supplier_notified_date")
        if notif_date:
            qd = QDate.fromString(str(notif_date), "yyyy-MM-dd")
            if qd.isValid():
                self._de_supplier_notified.setDate(qd)

        self._txt_supplier_notes.setPlainText(mat.get("supplier_notified_notes") or "")

        # Stage 4: checkbox reflects stored stage >= 4
        self._chk_qty_released.setChecked((mat.get("stage") or 1) >= 4)

        # Stage 5
        try:
            self._spn_qty_received.setValue(int(mat.get("qty_received") or 0))
        except (ValueError, TypeError):
            pass

        self._chk_fully_received.setChecked(bool(mat.get("fully_received")))

        receipt_date = mat.get("receipt_date")
        if receipt_date:
            qd = QDate.fromString(str(receipt_date), "yyyy-MM-dd")
            if qd.isValid():
                self._de_receipt_date.setDate(qd)

        self._txt_receipt_notes.setPlainText(mat.get("receipt_notes") or "")

    # ------------------------------------------------------------------
    # Enable/disable logic
    # ------------------------------------------------------------------

    def _update_enabled_states(self) -> None:
        review = self._fixture_group.get("review_status") or ""
        approved_statuses = {"Approved As Submitted", "Approved As Noted"}
        approved = review in approved_statuses
        has_po = bool(self._material.get("po_id"))
        supplier_checked = self._chk_supplier_notified.isChecked()
        qty_released_checked = self._chk_qty_released.isChecked()

        # Stage 2: requires approval
        self._stage2_widget.setEnabled(approved)
        self._de_supplier_notified.setEnabled(approved and supplier_checked)
        self._txt_supplier_notes.setEnabled(approved)

        # Stage 4: requires a PO
        self._stage4_widget.setEnabled(has_po)

        # Stage 5: requires qty_released checked
        self._stage5_widget.setEnabled(has_po and qty_released_checked)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        fields: dict = {}

        # Stage 2 fields
        fields["supplier_notified"] = 1 if self._chk_supplier_notified.isChecked() else 0
        fields["supplier_notified_date"] = (
            self._de_supplier_notified.date().toString("yyyy-MM-dd")
            if self._chk_supplier_notified.isChecked()
            else None
        )
        fields["supplier_notified_notes"] = self._txt_supplier_notes.toPlainText().strip() or None

        # Stage 5 fields
        fields["qty_received"] = self._spn_qty_received.value()
        fields["fully_received"] = 1 if self._chk_fully_received.isChecked() else 0
        fields["receipt_date"] = self._de_receipt_date.date().toString("yyyy-MM-dd")
        fields["receipt_notes"] = self._txt_receipt_notes.toPlainText().strip() or None

        # Compute new stage: seed stage=4 in temp_mat if qty_released is checked,
        # so current_stage() sees stage_4_met = True.
        temp_mat = {**self._material, **fields}
        if self._chk_qty_released.isChecked():
            temp_mat["stage"] = 4

        fields["stage"] = current_stage(temp_mat, self._fixture_group)

        pm_model.update(self.conn, self.material_id, **fields)
        self.accept()
