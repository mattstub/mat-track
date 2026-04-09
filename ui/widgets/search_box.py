"""Reusable catalog search widget."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget


class SearchBox(QWidget):
    search_changed = Signal(str)

    def __init__(self, placeholder: str = "Search...", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui(placeholder)

    def _build_ui(self, placeholder: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.textChanged.connect(self.search_changed)
        layout.addWidget(self._edit)

    def text(self) -> str:
        return self._edit.text()
