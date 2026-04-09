"""Center panel — materials view (by package or all for a project)."""

import sqlite3

from PySide6.QtWidgets import QWidget


class MaterialPanel(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError

    def load_package(self, package_id: int) -> None:
        raise NotImplementedError
