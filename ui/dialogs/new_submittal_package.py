"""Dialog — create a new submittal package (or revision) for a project."""

import sqlite3

from PySide6.QtWidgets import QDialog


class NewSubmittalPackageDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, project_id: int, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.project_id = project_id
        self.setWindowTitle("New Submittal Package")
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
