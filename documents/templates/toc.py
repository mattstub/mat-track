"""ReportLab layout for the submittal package table of contents (Page 2)."""

from reportlab.platypus import BaseDocTemplate


def build_toc(doc: BaseDocTemplate, fixture_groups: list, materials: list) -> list:
    """Return a list of ReportLab flowables for the TOC page."""
    raise NotImplementedError
