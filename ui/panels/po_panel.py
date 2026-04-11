"""Panel — PO list and detail for the selected project (or all projects)."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from db.models import purchase_order as po_model
from ui.dialogs.new_po import NewPODialog

# PO list table columns
_PO_COL_NUMBER = 0
_PO_COL_SUPPLIER = 1
_PO_COL_STATUS = 2
_PO_COL_DATE = 3

# Line items table columns
_LI_COL_TAG = 0
_LI_COL_MFR = 1
_LI_COL_MODEL = 2
_LI_COL_DESC = 3
_LI_COL_QTY_ORD = 4
_LI_COL_PRICE = 5


class POPanel(QWidget):
    """Panel showing purchase orders — either for a specific project or all projects.

    Public API:
        load_project(project_id): Show POs for one project; enables + PO button.
        load_all(): Show all POs across all projects.
        refresh(): Re-run the last load.
    """

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._project_id: int | None = None
        self._mode: str = "all"  # "project" | "all"
        self._build_ui()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 6, 4, 4)
        root.setSpacing(4)

        # ── Toolbar ────────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._btn_new_po = QPushButton("+ New PO")
        self._btn_new_po.setEnabled(False)
        self._btn_new_po.clicked.connect(self._on_new_po)
        toolbar.addWidget(self._btn_new_po)

        toolbar.addStretch()

        self._lbl_context = QLabel("All Purchase Orders")
        toolbar.addWidget(self._lbl_context)

        root.addLayout(toolbar)

        # ── Splitter: PO list (top) + line items (bottom) ──────────────
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # Top: PO list
        po_container = QWidget()
        po_layout = QVBoxLayout(po_container)
        po_layout.setContentsMargins(0, 0, 0, 0)
        po_layout.setSpacing(2)
        po_layout.addWidget(QLabel("Purchase Orders:"))

        self._po_table = QTableWidget(0, 4)
        self._po_table.setHorizontalHeaderLabels(["PO Number", "Supplier", "Status", "Issue Date"])
        self._po_table.setSelectionBehavior(self._po_table.SelectRows)
        self._po_table.setSelectionMode(self._po_table.SingleSelection)
        self._po_table.setEditTriggers(self._po_table.NoEditTriggers)
        self._po_table.setAlternatingRowColors(True)
        self._po_table.verticalHeader().setVisible(False)

        po_hdr = self._po_table.horizontalHeader()
        po_hdr.setSectionResizeMode(_PO_COL_NUMBER, QHeaderView.ResizeToContents)
        po_hdr.setSectionResizeMode(_PO_COL_SUPPLIER, QHeaderView.Stretch)
        po_hdr.setSectionResizeMode(_PO_COL_STATUS, QHeaderView.ResizeToContents)
        po_hdr.setSectionResizeMode(_PO_COL_DATE, QHeaderView.ResizeToContents)

        self._po_table.itemSelectionChanged.connect(self._on_po_selected)
        po_layout.addWidget(self._po_table)

        splitter.addWidget(po_container)

        # Bottom: line items
        li_container = QWidget()
        li_layout = QVBoxLayout(li_container)
        li_layout.setContentsMargins(0, 0, 0, 0)
        li_layout.setSpacing(2)
        li_layout.addWidget(QLabel("Line Items:"))

        self._li_table = QTableWidget(0, 6)
        self._li_table.setHorizontalHeaderLabels(
            ["Tag", "Manufacturer", "Model", "Description", "Qty Ordered", "Unit Price"]
        )
        self._li_table.setSelectionBehavior(self._li_table.SelectRows)
        self._li_table.setEditTriggers(self._li_table.NoEditTriggers)
        self._li_table.setAlternatingRowColors(True)
        self._li_table.verticalHeader().setVisible(False)

        li_hdr = self._li_table.horizontalHeader()
        li_hdr.setSectionResizeMode(_LI_COL_TAG, QHeaderView.ResizeToContents)
        li_hdr.setSectionResizeMode(_LI_COL_MFR, QHeaderView.ResizeToContents)
        li_hdr.setSectionResizeMode(_LI_COL_MODEL, QHeaderView.ResizeToContents)
        li_hdr.setSectionResizeMode(_LI_COL_DESC, QHeaderView.Stretch)
        li_hdr.setSectionResizeMode(_LI_COL_QTY_ORD, QHeaderView.ResizeToContents)
        li_hdr.setSectionResizeMode(_LI_COL_PRICE, QHeaderView.ResizeToContents)

        li_layout.addWidget(self._li_table)
        splitter.addWidget(li_container)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_project(self, project_id: int) -> None:
        """Show POs for a single project and enable the + New PO button."""
        self._project_id = project_id
        self._mode = "project"
        self._btn_new_po.setEnabled(True)
        self._lbl_context.setText(f"Project #{project_id} — Purchase Orders")
        self._populate_pos()

    def load_all(self) -> None:
        """Show all POs across all projects (read-only view)."""
        self._project_id = None
        self._mode = "all"
        self._btn_new_po.setEnabled(False)
        self._lbl_context.setText("All Purchase Orders")
        self._populate_pos()

    def refresh(self) -> None:
        if self._mode == "project" and self._project_id is not None:
            self.load_project(self._project_id)
        else:
            self.load_all()

    # ------------------------------------------------------------------
    # PO list population
    # ------------------------------------------------------------------

    def _populate_pos(self) -> None:
        self._po_table.blockSignals(True)
        self._po_table.setRowCount(0)
        self._li_table.setRowCount(0)

        try:
            if self._mode == "project" and self._project_id is not None:
                pos = po_model.list_for_project(self.conn, self._project_id)
            else:
                pos = po_model.list_all(self.conn)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load POs:\n{exc}")
            self._po_table.blockSignals(False)
            return

        for row_idx, po in enumerate(pos):
            self._po_table.insertRow(row_idx)
            number = po["po_number"] or f"(Draft #{po['id']})"
            supplier = po["supplier_company_name"] or "—"
            status = po["status"] or "—"
            date = po["issue_date"] or "—"

            for col, text in [
                (_PO_COL_NUMBER, number),
                (_PO_COL_SUPPLIER, supplier),
                (_PO_COL_STATUS, status),
                (_PO_COL_DATE, date),
            ]:
                cell = QTableWidgetItem(text)
                cell.setData(Qt.UserRole, po["id"])
                self._po_table.setItem(row_idx, col, cell)

        self._po_table.blockSignals(False)

    # ------------------------------------------------------------------
    # Line items population
    # ------------------------------------------------------------------

    def _on_po_selected(self) -> None:
        selected = self._po_table.selectedItems()
        if not selected:
            self._li_table.setRowCount(0)
            return

        po_id = selected[0].data(Qt.UserRole)
        self._populate_line_items(po_id)

    def _populate_line_items(self, po_id: int) -> None:
        self._li_table.setRowCount(0)

        try:
            items = po_model.list_line_items_for_po(self.conn, po_id)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load line items:\n{exc}")
            return

        for row_idx, item in enumerate(items):
            self._li_table.insertRow(row_idx)
            tag = item["tag_designation"] or "—"
            mfr = item["manufacturer"] or "—"
            model = item["model_number"] or "—"
            desc = item["line_description"] or item["product_description"] or "—"
            qty = str(item["qty_ordered"]) if item["qty_ordered"] is not None else "—"
            price = f"${item['unit_price']:.2f}" if item["unit_price"] is not None else "—"

            for col, text in [
                (_LI_COL_TAG, tag),
                (_LI_COL_MFR, mfr),
                (_LI_COL_MODEL, model),
                (_LI_COL_DESC, desc),
                (_LI_COL_QTY_ORD, qty),
                (_LI_COL_PRICE, price),
            ]:
                self._li_table.setItem(row_idx, col, QTableWidgetItem(text))

    # ------------------------------------------------------------------
    # New PO
    # ------------------------------------------------------------------

    def _on_new_po(self) -> None:
        if self._project_id is None:
            return
        dlg = NewPODialog(self.conn, self._project_id, parent=self)
        if dlg.exec():
            self.refresh()
