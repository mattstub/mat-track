"""Dialog — search catalog and assign a product to a fixture group."""

import sqlite3

from PySide6.QtWidgets import QDialog


class AddMaterialDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, group_id: int, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.group_id = group_id
        self.setWindowTitle("Add Material")
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
