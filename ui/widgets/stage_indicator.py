"""Color-coded pipeline stage badge widget.

Colors:
  Gray   — Not started        #9E9E9E
  Yellow — In progress        #FFC107
  Green  — Complete           #4CAF50
  Red    — Rejected           #F44336
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from core import lifecycle as lifecycle_mod

_COLOR_MAP: dict[str, QColor] = {
    "gray": QColor("#9E9E9E"),
    "yellow": QColor("#FFC107"),
    "green": QColor("#4CAF50"),
    "red": QColor("#F44336"),
}

_CIRCLE_D = 18  # diameter in px
_GAP = 6  # gap between circles in px
_STAGES = 5


class StageIndicator(QWidget):
    """Displays a 5-stage pipeline indicator with per-stage color coding."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Internal state: list of 5 color keys
        self._stages: list[str] = ["gray"] * _STAGES
        self.setFixedSize(self.sizeHint())

    # ------------------------------------------------------------------
    # Size hint
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:
        width = _STAGES * _CIRCLE_D + (_STAGES - 1) * _GAP
        return QSize(width, _CIRCLE_D)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_stage(self, stage: int, color: str) -> None:
        """Set the color for stage 1–5. color: 'gray' | 'yellow' | 'green' | 'red'."""
        if not (1 <= stage <= _STAGES):
            raise ValueError(f"stage must be 1–{_STAGES}, got {stage}")
        if color not in _COLOR_MAP:
            raise ValueError(f"color must be one of {list(_COLOR_MAP)}, got {color!r}")
        self._stages[stage - 1] = color
        self.update()

    def load_from_material(self, material, fixture_group) -> None:
        """Convenience method: derive stage colors from a material and its fixture_group.

        Both arguments may be sqlite3.Row objects or plain dicts.
        """
        # Normalise to dict so lifecycle functions can use .get()
        if hasattr(material, "keys"):
            mat_dict = dict(material)
        else:
            mat_dict = material

        if hasattr(fixture_group, "keys"):
            fg_dict = dict(fixture_group)
        else:
            fg_dict = fixture_group

        current = lifecycle_mod.current_stage(mat_dict, fg_dict)

        review_status = fg_dict.get("review_status", "")
        rejected = review_status in ("Revise & Resubmit", "Rejected")

        for s in range(1, _STAGES + 1):
            if s <= current:
                color = "green"
            else:
                color = "gray"
            self._stages[s - 1] = color

        # Override stage 1 with red when the fixture group is rejected/R&R
        if rejected:
            self._stages[0] = "red"

        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for i, color_key in enumerate(self._stages):
            color = _COLOR_MAP.get(color_key, _COLOR_MAP["gray"])
            x = i * (_CIRCLE_D + _GAP)
            y = 0
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x, y, _CIRCLE_D, _CIRCLE_D)

        painter.end()
