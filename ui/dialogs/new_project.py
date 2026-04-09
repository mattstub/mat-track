"""Dialog — create a new project."""

import sqlite3

from PySide6.QtWidgets import QDialog


class NewProjectDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("New Project")
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
