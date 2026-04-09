"""Dialog — add a fixture group (tag + description) to a submittal package."""

import sqlite3

from PySide6.QtWidgets import QDialog


class NewFixtureGroupDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, package_id: int, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.package_id = package_id
        self.setWindowTitle("New Fixture Group")
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
