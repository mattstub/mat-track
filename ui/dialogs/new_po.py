"""Dialog — create a purchase order: select supplier and assign materials."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from db.models import project_material as project_material_model
from db.models import purchase_order as po_model
from db.models import supplier as supplier_model

# Line-items table column indices
_COL_CHECK = 0
_COL_TAG = 1
_COL_MFR = 2
_COL_MODEL = 3
_COL_DESC = 4
_COL_QTY = 5
_COL_PRICE = 6


class NewPODialog(QDialog):
    """Create a new purchase order by selecting a supplier and materials.

    Args:
        conn: Active SQLite connection.
        project_id: ID of the project to create the PO under.
        parent: Optional parent widget.
    """

    def __init__(self, conn: sqlite3.Connection, project_id: int, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.project_id = project_id
        self._materials: list = []
        self._supplier_ids: list[int] = []
        self.setWindowTitle("New Purchase Order")
        self.setMinimumWidth(820)
        self.setMinimumHeight(560)
        self._build_ui()
        self._populate_suppliers()
        self._load_materials()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Header form ────────────────────────────────────────────────
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(6)

        self._lbl_supplier = QLabel("Supplier*")
        self._combo_supplier = QComboBox()
        form.addRow(self._lbl_supplier, self._combo_supplier)

        self._edit_po_number = QLineEdit()
        self._edit_po_number.setPlaceholderText("e.g. PO-2512-001")
        form.addRow("PO Number", self._edit_po_number)

        self._edit_issue_date = QLineEdit()
        self._edit_issue_date.setPlaceholderText("YYYY-MM-DD (optional)")
        form.addRow("Issue Date", self._edit_issue_date)

        self._edit_ship_addr = QLineEdit()
        self._edit_ship_addr.setPlaceholderText("Shipping address (optional)")
        form.addRow("Shipping Address", self._edit_ship_addr)

        self._edit_notes = QTextEdit()
        self._edit_notes.setFixedHeight(56)
        form.addRow("Notes", self._edit_notes)

        root.addLayout(form)

        # ── Materials table ────────────────────────────────────────────
        root.addWidget(QLabel("Select materials to include (check rows, set quantities):"))

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["", "Tag", "Manufacturer", "Model", "Description", "Qty Ordered", "Unit Price"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.AnyKeyPressed
        )
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(_COL_CHECK, QHeaderView.Fixed)
        self._table.setColumnWidth(_COL_CHECK, 28)
        hdr.setSectionResizeMode(_COL_TAG, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(_COL_MFR, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(_COL_MODEL, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(_COL_DESC, QHeaderView.Stretch)
        hdr.setSectionResizeMode(_COL_QTY, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(_COL_PRICE, QHeaderView.ResizeToContents)

        root.addWidget(self._table, stretch=1)

        # ── Validation label ───────────────────────────────────────────
        self._lbl_validation = QLabel()
        self._lbl_validation.setStyleSheet("color: red;")
        self._lbl_validation.setVisible(False)
        root.addWidget(self._lbl_validation)

        # ── Buttons ────────────────────────────────────────────────────
        btn_box = QDialogButtonBox()
        self._btn_save = QPushButton("Save")
        self._btn_save.setDefault(True)
        btn_cancel = QPushButton("Cancel")
        btn_box.addButton(self._btn_save, QDialogButtonBox.AcceptRole)
        btn_box.addButton(btn_cancel, QDialogButtonBox.RejectRole)
        btn_box.rejected.connect(self.reject)
        self._btn_save.clicked.connect(self._on_save)
        root.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _populate_suppliers(self) -> None:
        try:
            suppliers = supplier_model.get_all(self.conn)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load suppliers:\n{exc}")
            suppliers = []

        self._supplier_ids = []
        self._combo_supplier.clear()

        if not suppliers:
            self._combo_supplier.addItem("— No suppliers defined —")
            return

        for s in suppliers:
            label = s["company_name"]
            if s["contact_name"]:
                label += f"  ({s['contact_name']})"
            self._combo_supplier.addItem(label)
            self._supplier_ids.append(s["id"])

    def _load_materials(self) -> None:
        """Load project materials not yet on any PO, JOINed with product and group info."""
        try:
            cur = self.conn.execute(
                """
                SELECT pm.*,
                       p.manufacturer     AS product_manufacturer,
                       p.model_number     AS product_model_number,
                       p.description      AS product_description,
                       fg.tag_designation AS tag_designation
                  FROM project_materials pm
                  JOIN products p        ON p.id  = pm.product_id
                  JOIN fixture_groups fg ON fg.id = pm.fixture_group_id
                 WHERE pm.project_id = ? AND pm.po_id IS NULL
                 ORDER BY fg.tag_designation ASC, pm.id ASC
                """,
                (self.project_id,),
            )
            self._materials = cur.fetchall()
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load materials:\n{exc}")
            self._materials = []

        self._table.setRowCount(0)
        for row_idx, mat in enumerate(self._materials):
            self._table.insertRow(row_idx)

            # Checkbox column — not editable via keyboard, only by clicking
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Unchecked)
            self._table.setItem(row_idx, _COL_CHECK, chk_item)

            # Read-only display columns
            tag = mat["tag_designation"] or "—"
            mfr = mat["product_manufacturer"] or "—"
            model = mat["product_model_number"] or "—"
            desc = mat["line_description"] or mat["product_description"] or "—"

            for col, text in [
                (_COL_TAG, tag),
                (_COL_MFR, mfr),
                (_COL_MODEL, model),
                (_COL_DESC, desc),
            ]:
                cell = QTableWidgetItem(text)
                cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self._table.setItem(row_idx, col, cell)

            # Qty ordered — editable, pre-filled from material quantity
            qty_item = QTableWidgetItem(str(mat["quantity"] or 1))
            qty_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self._table.setItem(row_idx, _COL_QTY, qty_item)

            # Unit price — editable, blank
            price_item = QTableWidgetItem("")
            price_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self._table.setItem(row_idx, _COL_PRICE, price_item)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        self._lbl_validation.setVisible(False)
        self._lbl_supplier.setStyleSheet("")

        # Validate supplier
        if not self._supplier_ids:
            self._lbl_validation.setText("No suppliers available. Add a supplier first.")
            self._lbl_validation.setVisible(True)
            return

        supplier_idx = self._combo_supplier.currentIndex()
        if supplier_idx < 0 or supplier_idx >= len(self._supplier_ids):
            self._lbl_supplier.setStyleSheet("color: red;")
            return
        supplier_id = self._supplier_ids[supplier_idx]

        # Collect checked rows
        selected_rows = [
            i
            for i in range(self._table.rowCount())
            if (item := self._table.item(i, _COL_CHECK)) and item.checkState() == Qt.Checked
        ]

        if not selected_rows:
            self._lbl_validation.setText("Select at least one material to include in the PO.")
            self._lbl_validation.setVisible(True)
            return

        # Build PO record
        po_fields: dict = {
            "project_id": self.project_id,
            "supplier_id": supplier_id,
            "status": "Draft",
        }
        po_number = self._edit_po_number.text().strip()
        if po_number:
            po_fields["po_number"] = po_number
        issue_date = self._edit_issue_date.text().strip()
        if issue_date:
            po_fields["issue_date"] = issue_date
        ship_addr = self._edit_ship_addr.text().strip()
        if ship_addr:
            po_fields["shipping_address"] = ship_addr
        notes = self._edit_notes.toPlainText().strip()
        if notes:
            po_fields["notes"] = notes

        try:
            po_id = po_model.create(self.conn, **po_fields)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not create PO:\n{exc}")
            return

        # Create line items and link materials to the PO
        for row_idx in selected_rows:
            mat = self._materials[row_idx]
            material_id = mat["id"]

            qty_text = (self._table.item(row_idx, _COL_QTY) or QTableWidgetItem("1")).text().strip()
            try:
                qty_ordered = int(qty_text) if qty_text else 1
            except ValueError:
                qty_ordered = 1

            price_item = self._table.item(row_idx, _COL_PRICE) or QTableWidgetItem("")
            price_text = price_item.text().strip()
            unit_price: float | None = None
            if price_text:
                try:
                    unit_price = float(price_text)
                except ValueError:
                    unit_price = None

            line_fields: dict = {
                "purchase_order_id": po_id,
                "project_material_id": material_id,
                "qty_ordered": qty_ordered,
            }
            if unit_price is not None:
                line_fields["unit_price"] = unit_price

            try:
                po_model.add_line_item(self.conn, **line_fields)
                project_material_model.update(self.conn, material_id, po_id=po_id)
            except Exception as exc:
                QMessageBox.critical(self, "Database Error", f"Could not save line items:\n{exc}")
                return

        self.accept()
