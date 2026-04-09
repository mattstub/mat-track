"""Color-coded pipeline stage badge widget.

Colors:
  Gray   — Not started
  Yellow — In progress / submitted / awaiting response
  Green  — Complete
  Red    — Rejected / action required
"""

from PySide6.QtWidgets import QWidget


class StageIndicator(QWidget):
    """Displays a 5-stage pipeline indicator with per-stage color coding."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stages: list[str] = ["gray"] * 5
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError

    def set_stage(self, stage: int, color: str) -> None:
        """Set the color for a stage (1–5). color: 'gray' | 'yellow' | 'green' | 'red'."""
        raise NotImplementedError
