"""Dialog — create or edit a supplier record."""

import sqlite3

from PySide6.QtWidgets import QDialog


class SupplierEditDialog(QDialog):
    def __init__(
        self,
        conn: sqlite3.Connection,
        supplier_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.supplier_id = supplier_id  # None = create mode
        self.setWindowTitle("Supplier" if supplier_id else "New Supplier")
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
