"""ReportLab canvas drawing for the submittal package cover sheet (Page 1)."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas

# Page dimensions
_W, _H = letter  # 612 x 792 pts
_MARGIN = 0.75 * inch


def draw_cover_sheet(c: rl_canvas.Canvas, package_data: dict) -> None:
    """Draw the cover sheet onto a single canvas page.

    Args:
        c: ReportLab Canvas (already positioned at the start of the page).
        package_data: Assembled data dict from document_builder._assemble_submittal_data.
    """
    pkg = package_data.get("package", {})
    project = package_data.get("project", {})
    company = package_data.get("company", {})
    assets_dir: Path = package_data.get("assets_dir", Path("."))

    # ── Company logo (top-left) ────────────────────────────────────────────
    logo_filename = company.get("logo_filename")
    logo_y_top = _H - _MARGIN
    logo_height = 0.75 * inch

    if logo_filename:
        logo_path = assets_dir / logo_filename
        if logo_path.exists():
            try:
                c.drawImage(
                    str(logo_path),
                    _MARGIN,
                    logo_y_top - logo_height,
                    width=2.5 * inch,
                    height=logo_height,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass  # If image fails, continue without it

    # ── "SUBMITTAL" heading (top-right) ───────────────────────────────────
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(_W - _MARGIN, _H - _MARGIN - 0.1 * inch, "SUBMITTAL")

    # ── Horizontal rule below header ──────────────────────────────────────
    rule_y = _H - _MARGIN - logo_height - 0.1 * inch
    c.setStrokeColor(colors.HexColor("#1565C0"))
    c.setLineWidth(2)
    c.line(_MARGIN, rule_y, _W - _MARGIN, rule_y)

    # ── Project info block ────────────────────────────────────────────────
    y = rule_y - 0.3 * inch
    label_x = _MARGIN
    value_x = _MARGIN + 1.6 * inch

    def _label_value(label: str, value: str, y_pos: float, bold_label: bool = True) -> float:
        """Draw a label:value pair, return new y position."""
        if bold_label:
            c.setFont("Helvetica-Bold", 9)
        else:
            c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(label_x, y_pos, label)
        c.setFont("Helvetica", 9)
        c.drawString(value_x, y_pos, value or "")
        return y_pos - 0.2 * inch

    line_h = 0.2 * inch

    y = _label_value("Job:", project.get("name") or "", y)
    y = _label_value("Location:", project.get("location") or "", y)
    y = _label_value("Project No:", project.get("project_number") or "", y)
    y -= 0.1 * inch  # small gap

    y = _label_value("Spec Section:", pkg.get("spec_section") or "", y)
    y = _label_value("Spec Title:", pkg.get("spec_section_title") or "", y)
    y = _label_value("Submittal Title:", pkg.get("title") or "", y)
    y = _label_value("Submittal No:", pkg.get("submittal_number") or "", y)
    y = _label_value("Revision No:", str(pkg.get("revision_number") or 0), y)
    y = _label_value("Date Submitted:", pkg.get("date_submitted") or "", y)
    y -= 0.2 * inch  # gap before parties

    # ── Parties block ─────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.drawString(label_x, y, "Contractor:")
    c.setFont("Helvetica", 9)
    c.drawString(value_x, y, company.get("name") or "")
    y -= line_h
    if company.get("address"):
        c.drawString(value_x, y, company["address"])
        y -= line_h
    if company.get("phone"):
        c.drawString(value_x, y, company["phone"])
        y -= line_h
    y -= 0.1 * inch

    c.setFont("Helvetica-Bold", 9)
    c.drawString(label_x, y, "General Contractor:")
    c.setFont("Helvetica", 9)
    gc_name = project.get("gc_name") or ""
    gc_num = project.get("gc_project_number") or ""
    gc_label = f"{gc_name}  (GC #{gc_num})" if gc_num else gc_name
    c.drawString(value_x, y, gc_label)
    y -= line_h
    y -= 0.1 * inch

    c.setFont("Helvetica-Bold", 9)
    c.drawString(label_x, y, "Architect:")
    c.setFont("Helvetica", 9)
    c.drawString(value_x, y, project.get("architect_name") or "")
    y -= line_h
    y -= 0.1 * inch

    c.setFont("Helvetica-Bold", 9)
    c.drawString(label_x, y, "Engineer:")
    c.setFont("Helvetica", 9)
    c.drawString(value_x, y, project.get("engineer_name") or "")
    y -= line_h

    # ── Stamp boxes (bottom of page) ──────────────────────────────────────
    box_y = _MARGIN
    box_h = 1.5 * inch
    box_w = (_W - 2 * _MARGIN - 2 * 0.25 * inch) / 3
    box_gap = 0.25 * inch

    c.setStrokeColor(colors.HexColor("#555555"))
    c.setLineWidth(0.75)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#EEEEEE"))

    stamp_labels = ["Contractor's Stamp", "Architect's Stamp", "Engineer's Stamp"]
    for i, label in enumerate(stamp_labels):
        bx = _MARGIN + i * (box_w + box_gap)
        c.rect(bx, box_y, box_w, box_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawCentredString(bx + box_w / 2, box_y + box_h - 0.2 * inch, label)
        c.setFillColor(colors.HexColor("#EEEEEE"))

    c.showPage()
