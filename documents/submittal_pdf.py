"""Submittal package PDF builder.

Receives plain data objects (not DB connections) so this module is
reusable in a web context during ProManage migration.

Output structure:
  Page 1:   Cover sheet (company logo, project info, stamp boxes)
  Page 2+:  Table of contents
  Then per fixture group:
    Divider page (tag — description, centered)
    Cut sheet PDF pages (or placeholder if missing)
"""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas

from documents.templates.cover_sheet import draw_cover_sheet
from documents.templates.toc import build_toc_pdf

_W, _H = letter
_MARGIN = 0.75 * inch


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build(package_data: dict, output_path: Path) -> None:
    """Write the submittal package PDF to output_path."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()

    # ── Page 1: Cover sheet ───────────────────────────────────────────────
    cover_buf = _build_cover_buf(package_data)
    cover_reader = PdfReader(cover_buf)
    for page in cover_reader.pages:
        writer.add_page(page)

    # ── Pages 2+: TOC ─────────────────────────────────────────────────────
    toc_bytes = build_toc_pdf(package_data)
    toc_reader = PdfReader(BytesIO(toc_bytes))
    for page in toc_reader.pages:
        writer.add_page(page)

    # ── Per fixture group: divider + cut sheets ────────────────────────────
    cut_sheets_dir: Path = package_data.get("cut_sheets_dir", Path("."))
    for group in package_data.get("fixture_groups", []):
        # Divider page
        div_buf = _build_divider_buf(group)
        div_reader = PdfReader(div_buf)
        writer.add_page(div_reader.pages[0])

        # Cut sheet pages for each material in the group
        for mat in group.get("materials", []):
            filename = mat.get("cut_sheet_filename")
            appended = False
            if filename:
                cs_path = cut_sheets_dir / filename
                if cs_path.exists():
                    try:
                        cs_reader = PdfReader(str(cs_path))
                        for cs_page in cs_reader.pages:
                            writer.add_page(cs_page)
                        appended = True
                    except Exception:
                        pass  # Fall through to placeholder on error

            if not appended:
                ph_buf = _build_placeholder_buf(mat)
                ph_reader = PdfReader(ph_buf)
                writer.add_page(ph_reader.pages[0])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)


# ---------------------------------------------------------------------------
# Page builders (each returns a BytesIO containing a PDF)
# ---------------------------------------------------------------------------


def _build_cover_buf(package_data: dict) -> BytesIO:
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    draw_cover_sheet(c, package_data)
    c.save()
    buf.seek(0)
    return buf


def _build_divider_buf(group: dict) -> BytesIO:
    """Single-page section divider: tag — description centered on the page."""
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)

    tag = group.get("tag_designation", "")
    desc = group.get("description", "")
    label = f"{tag}  —  {desc}" if desc else tag

    # Light blue header bar
    c.setFillColor(colors.HexColor("#1565C0"))
    c.rect(0, _H / 2 - 0.5 * inch, _W, inch, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(_W / 2, _H / 2 - 0.1 * inch, label)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def _build_placeholder_buf(mat: dict) -> BytesIO:
    """Single-page placeholder for a material with no cut sheet."""
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)

    mfr = mat.get("product_manufacturer") or ""
    model = mat.get("product_model_number") or ""
    desc = mat.get("line_description") or mat.get("product_description") or ""
    item_label = f"{mfr} {model}".strip() if (mfr or model) else desc

    c.setFillColor(colors.HexColor("#FFF3E0"))
    c.rect(0, 0, _W, _H, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#E65100"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(_W / 2, _H / 2 + 0.3 * inch, "CUT SHEET NOT ATTACHED")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawCentredString(_W / 2, _H / 2 - 0.1 * inch, item_label)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#777777"))
    c.drawCentredString(
        _W / 2,
        _H / 2 - 0.4 * inch,
        "Import the cut sheet PDF in the product catalog to include it in future submittals.",
    )

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
