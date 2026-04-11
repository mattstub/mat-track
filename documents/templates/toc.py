"""ReportLab canvas drawing for the submittal package table of contents (Page 2+)."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_W, _H = letter
_MARGIN = 0.75 * inch


def build_toc_pdf(package_data: dict) -> bytes:
    """Build the TOC page(s) as PDF bytes using platypus (handles pagination).

    Args:
        package_data: Assembled data dict from document_builder.

    Returns:
        PDF bytes for the TOC section (one or more pages).
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Title ──────────────────────────────────────────────────────────────
    pkg = package_data.get("package", {})
    project = package_data.get("project", {})

    title_text = (
        f"<b>{pkg.get('submittal_number', '')}</b>"
        f"  {pkg.get('title') or pkg.get('spec_section_title') or 'Table of Contents'}"
    )
    story.append(Paragraph(title_text, styles["Heading2"]))

    proj_line = f"{project.get('name', '')}  —  {project.get('project_number', '')}"
    story.append(Paragraph(proj_line, styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    # ── Table ──────────────────────────────────────────────────────────────
    col_widths = [0.9 * inch, 2.3 * inch, 1.5 * inch, 1.5 * inch, 0.6 * inch]
    header = [["Item", "Description", "Manufacturer", "Model No.", "Qty"]]

    rows = []
    fixture_groups = package_data.get("fixture_groups", [])
    for group in fixture_groups:
        tag = group.get("tag_designation", "")
        desc = group.get("description", "")
        materials = group.get("materials", [])

        if not materials:
            rows.append([tag, desc, "", "", str(group.get("quantity") or "")])
            continue

        for i, mat in enumerate(materials):
            row_tag = tag if i == 0 else ""
            row_desc = mat.get("line_description") or mat.get("product_description") or ""
            mfr = mat.get("product_manufacturer") or ""
            model = mat.get("product_model_number") or ""
            qty = str(mat.get("quantity") or "")
            rows.append([row_tag, row_desc, mfr, model, qty])

    all_rows = header + rows

    tbl = Table(all_rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Body
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
                ("ALIGN", (-1, 1), (-1, -1), "CENTER"),  # Qty column centered
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tbl)

    doc.build(story)
    buf.seek(0)
    return buf.read()
