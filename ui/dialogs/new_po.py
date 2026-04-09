"""Dialog — create a purchase order: select supplier and assign materials."""

import sqlite3

from PySide6.QtWidgets import QDialog


class NewPODialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, project_id: int, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.project_id = project_id
        self.setWindowTitle("New Purchase Order")
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
