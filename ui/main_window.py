"""Main application window — three-panel layout with bottom tab bar."""

import sqlite3

from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn
        self.setWindowTitle("MatTrack")
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
