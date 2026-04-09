"""ReportLab layout for the submittal package cover sheet (Page 1)."""

from pathlib import Path

from reportlab.platypus import BaseDocTemplate


def build_cover_sheet(doc: BaseDocTemplate, package_data: dict, assets_dir: Path) -> list:
    """Return a list of ReportLab flowables for the cover sheet page."""
    raise NotImplementedError
