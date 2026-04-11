"""Purchase order PDF builder using ReportLab.

Supports two output modes:
  Standard PO         — includes unit prices and totals
  Field Receipt Sheet — prices suppressed, blank qty_received write-in column,
                        signature/date line at bottom
"""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_W, _H = letter
_MARGIN = 0.75 * inch


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build(po_data: dict, output_path: Path, field_receipt_mode: bool = False) -> None:
    """Write the PO PDF to output_path."""
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
    story = _build_story(po_data, styles, field_receipt_mode)
    doc.build(story)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    buf.seek(0)
    with open(output_path, "wb") as f:
        f.write(buf.read())


# ---------------------------------------------------------------------------
# Story assembly
# ---------------------------------------------------------------------------


def _build_story(po_data: dict, styles, field_receipt_mode: bool) -> list:
    po = po_data.get("po", {})
    supplier = po_data.get("supplier", {})
    project = po_data.get("project", {})
    company = po_data.get("company", {})
    line_items = po_data.get("line_items", [])

    story = []

    # ── Header: logo row + PO number / date ───────────────────────────────
    story.extend(_build_header(company, po, styles, field_receipt_mode))
    story.append(Spacer(1, 0.2 * inch))

    # ── TO / PROJECT two-column block ─────────────────────────────────────
    story.append(_build_to_project_block(supplier, project, styles))
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1565C0")))
    story.append(Spacer(1, 0.15 * inch))

    # ── Line items table ──────────────────────────────────────────────────
    story.append(_build_line_items_table(line_items, field_receipt_mode))

    if field_receipt_mode:
        story.append(Spacer(1, 0.5 * inch))
        story.extend(_build_signature_block(styles))
    else:
        total = _compute_total(line_items)
        if total is not None:
            story.append(Spacer(1, 0.1 * inch))
            story.append(_build_total_row(total, styles))

    return story


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_header(company: dict, po: dict, styles, field_receipt_mode: bool) -> list:
    """Two-column header: company info (left) | PO number + mode label (right)."""
    company_lines = [company.get("name") or ""]
    if company.get("address"):
        company_lines.append(company["address"])
    if company.get("phone"):
        company_lines.append(company["phone"])

    left_text = "<br/>".join(company_lines)
    left_para = Paragraph(f"<b>{left_text}</b>", styles["Normal"])

    mode_label = "FIELD RECEIPT SHEET" if field_receipt_mode else "PURCHASE ORDER"
    po_number = po.get("po_number") or f"PO-{po.get('id', '')}"
    right_text = (
        f"<b>{mode_label}</b><br/>PO No: {po_number}<br/>Date: {po.get('issue_date') or '—'}"
    )
    right_para = Paragraph(right_text, styles["Normal"])

    content_width = _W - 2 * _MARGIN
    header_table = Table(
        [[left_para, right_para]],
        colWidths=[content_width * 0.55, content_width * 0.45],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [header_table]


def _build_to_project_block(supplier: dict, project: dict, styles) -> Table:
    """Two-column TO / PROJECT block."""
    sup_lines = ["<b>TO:</b>"]
    if supplier.get("company_name"):
        sup_lines.append(supplier["company_name"])
    if supplier.get("contact_name"):
        sup_lines.append(supplier["contact_name"])
    if supplier.get("email"):
        sup_lines.append(supplier["email"])
    if supplier.get("phone"):
        sup_lines.append(supplier["phone"])
    if supplier.get("address"):
        sup_lines.append(supplier["address"])

    proj_lines = ["<b>PROJECT:</b>"]
    if project.get("name"):
        proj_lines.append(project["name"])
    if project.get("project_number"):
        proj_lines.append(f"Project #: {project['project_number']}")
    if project.get("gc_name"):
        proj_lines.append(f"GC: {project['gc_name']}")

    left = Paragraph("<br/>".join(sup_lines), styles["Normal"])
    right = Paragraph("<br/>".join(proj_lines), styles["Normal"])

    content_width = _W - 2 * _MARGIN
    tbl = Table(
        [[left, right]],
        colWidths=[content_width * 0.5, content_width * 0.5],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return tbl


def _build_line_items_table(line_items: list, field_receipt_mode: bool) -> Table:
    """Build the line items table, with or without pricing columns."""
    content_width = _W - 2 * _MARGIN

    if field_receipt_mode:
        headers = [
            "Qty\nOrdered",
            "Spec\nSection",
            "Tag",
            "Manufacturer",
            "Model No.",
            "Description",
            "Qty\nReceived",
        ]
        col_widths = [
            0.6 * inch,
            0.65 * inch,
            0.65 * inch,
            1.1 * inch,
            1.2 * inch,
            content_width - 0.6 - 0.65 - 0.65 - 1.1 - 1.2 - 0.7,
            0.7 * inch,
        ]
    else:
        headers = [
            "Qty",
            "Spec\nSection",
            "Tag",
            "Manufacturer",
            "Model No.",
            "Description",
            "Unit Price",
            "Total",
        ]
        col_widths = [
            0.5 * inch,
            0.65 * inch,
            0.65 * inch,
            1.05 * inch,
            1.05 * inch,
            content_width - 0.5 - 0.65 - 0.65 - 1.05 - 1.05 - 0.8 - 0.85,
            0.8 * inch,
            0.85 * inch,
        ]

    rows = [headers]
    for item in line_items:
        qty = str(item.get("qty_ordered") or "")
        spec = item.get("spec_section") or ""
        tag = item.get("tag_designation") or ""
        mfr = item.get("manufacturer") or ""
        model = item.get("model_number") or ""
        desc = item.get("line_description") or item.get("product_description") or ""

        if field_receipt_mode:
            rows.append([qty, spec, tag, mfr, model, desc, ""])  # blank Qty Received write-in
        else:
            unit_price = item.get("unit_price")
            price_str = f"${unit_price:.2f}" if unit_price is not None else ""
            if unit_price is not None and item.get("qty_ordered"):
                total_str = f"${unit_price * item['qty_ordered']:.2f}"
            else:
                total_str = ""
            rows.append([qty, spec, tag, mfr, model, desc, price_str, total_str])

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Body
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Qty col
                ("ALIGN", (-2, 1), (-1, -1), "RIGHT"),  # Price/total cols (standard) or right col
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    if field_receipt_mode:
        # Highlight the write-in column header with a different color
        tbl.setStyle(TableStyle([("BACKGROUND", (-1, 0), (-1, 0), colors.HexColor("#E65100"))]))

    return tbl


def _compute_total(line_items: list) -> float | None:
    """Return total value if any line items have unit prices, else None."""
    total = 0.0
    has_price = False
    for item in line_items:
        price = item.get("unit_price")
        qty = item.get("qty_ordered") or 0
        if price is not None:
            total += price * qty
            has_price = True
    return total if has_price else None


def _build_total_row(total: float, styles) -> Table:
    content_width = _W - 2 * _MARGIN
    tbl = Table(
        [["", f"TOTAL:  ${total:.2f}"]],
        colWidths=[content_width * 0.75, content_width * 0.25],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (1, 0), (1, 0), 9),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    return tbl


def _build_signature_block(styles) -> list:
    """Signature / date line for field receipt sheet mode."""
    flowables = []
    flowables.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#555555")))
    flowables.append(Spacer(1, 0.15 * inch))

    sig_table = Table(
        [["Received by (print name):", "", "Signature:", "", "Date:", ""]],
        colWidths=[
            1.6 * inch,
            1.8 * inch,
            0.85 * inch,
            1.8 * inch,
            0.55 * inch,
            1.1 * inch,
        ],
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LINEBELOW", (1, 0), (1, 0), 0.75, colors.black),
                ("LINEBELOW", (3, 0), (3, 0), 0.75, colors.black),
                ("LINEBELOW", (5, 0), (5, 0), 0.75, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    flowables.append(sig_table)
    return flowables
