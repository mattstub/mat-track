"""Dialog — edit lifecycle stages 2–5 for a project material."""

import sqlite3

from PySide6.QtWidgets import QDialog


class LifecycleEditDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, material_id: int, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.material_id = material_id
        self.setWindowTitle("Edit Lifecycle Stages")
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
