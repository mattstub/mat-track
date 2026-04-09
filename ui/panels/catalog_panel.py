"""Bottom-tab panel — product catalog browser, search, and management."""

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core import catalog
from ui.dialogs.new_product import NewProductDialog
from ui.widgets.search_box import SearchBox


class CatalogPanel(QWidget):
    product_selected = Signal(int)  # emits product_id when a row is selected

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 6, 4, 4)
        root.setSpacing(6)

        # --- Top row: search + new product button ---
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self._search_box = SearchBox("Search products…")
        self._search_box.search_changed.connect(self._on_search_changed)
        top_row.addWidget(self._search_box, stretch=1)

        self._btn_new = QPushButton("+ New Product")
        self._btn_new.clicked.connect(self._on_new_product)
        top_row.addWidget(self._btn_new)

        root.addLayout(top_row)

        # --- Product table ---
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            [
                "Manufacturer",
                "Model Number",
                "Description",
                "Spec Section",
                "Cut Sheet",
            ]
        )
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.itemDoubleClicked.connect(self._on_row_double_clicked)
        root.addWidget(self._table, stretch=1)

        # Initial data load
        self.refresh()

    def refresh(self) -> None:
        """Re-run the current search query and repopulate the table."""
        query = self._search_box.text()
        self._run_search(query)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_search(self, query: str) -> None:
        try:
            results = catalog.search_products(self.conn, query)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not search products:\n{exc}")
            results = []

        self._table.setRowCount(0)
        for row_idx, product in enumerate(results):
            self._table.insertRow(row_idx)

            item_mfr = QTableWidgetItem(product.manufacturer or "")
            item_mfr.setData(Qt.UserRole, product.id)

            self._table.setItem(row_idx, 0, item_mfr)
            self._table.setItem(row_idx, 1, QTableWidgetItem(product.model_number or ""))
            self._table.setItem(row_idx, 2, QTableWidgetItem(product.description or ""))
            self._table.setItem(row_idx, 3, QTableWidgetItem(product.spec_section or ""))
            cut_sheet_text = "Yes" if product.cut_sheet_filename else "No"
            self._table.setItem(row_idx, 4, QTableWidgetItem(cut_sheet_text))

    def _selected_product_id(self) -> int | None:
        items = self._table.selectedItems()
        if not items:
            return None
        row = items[0].row()
        return self._table.item(row, 0).data(Qt.UserRole)

    def _open_product(self, product_id: int | None) -> None:
        dlg = NewProductDialog(self.conn, product_id=product_id, parent=self)
        if dlg.exec() and product_id is None:
            # A new product was created — refresh the list
            self.refresh()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_search_changed(self, query: str) -> None:
        self._run_search(query)

    def _on_new_product(self) -> None:
        self._open_product(product_id=None)

    def _on_row_double_clicked(self, item) -> None:
        row = item.row()
        product_id = self._table.item(row, 0).data(Qt.UserRole)
        if product_id is not None:
            self.product_selected.emit(product_id)
            self._open_product(product_id)
