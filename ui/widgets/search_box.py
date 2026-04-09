"""Reusable catalog search widget."""

from PySide6.QtWidgets import QWidget


class SearchBox(QWidget):
    def __init__(self, placeholder: str = "Search...", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui(placeholder)

    def _build_ui(self, placeholder: str) -> None:
        raise NotImplementedError

    def text(self) -> str:
        raise NotImplementedError
