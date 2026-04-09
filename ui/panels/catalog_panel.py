"""Bottom-tab panel — product catalog browser, search, and management."""

import sqlite3

from PySide6.QtWidgets import QWidget


class CatalogPanel(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError

    def refresh(self) -> None:
        raise NotImplementedError
