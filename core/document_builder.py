"""PDF assembly orchestration.

Fetches data from the DB, converts it to plain dicts, and hands off to
documents/submittal_pdf.py and documents/po_pdf.py.  No PDF library imports
here — keeps the data-assembly layer testable without a display environment.
"""

import sqlite3
from pathlib import Path

from db.models import company as company_model
from db.models import fixture_group as fixture_group_model
from db.models import project as project_model
from db.models import project_material as project_material_model
from db.models import purchase_order as po_model
from db.models import submittal_package as package_model
from db.models import supplier as supplier_model
from documents import po_pdf, submittal_pdf

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _assets_dir() -> Path:
    return _DATA_DIR / "assets"


def _cut_sheets_dir() -> Path:
    return _DATA_DIR / "cut_sheets"


def _output_dir_default() -> Path:
    return _DATA_DIR / "output"


# ---------------------------------------------------------------------------
# Row → plain dict
# ---------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row | None) -> dict:
    """Convert a sqlite3.Row to a plain dict; returns {} if row is None."""
    if row is None:
        return {}
    return dict(row)


# ---------------------------------------------------------------------------
# Submittal data assembly
# ---------------------------------------------------------------------------


def _assemble_submittal_data(conn: sqlite3.Connection, package_id: int) -> dict:
    """Fetch and structure all data needed to render a submittal package PDF."""
    pkg = _row_to_dict(package_model.get(conn, package_id))
    if not pkg:
        raise ValueError(f"Submittal package {package_id} not found.")

    project = _row_to_dict(project_model.get(conn, pkg["project_id"]))
    company = _row_to_dict(company_model.get(conn, project.get("company_id", 0)))

    groups_raw = fixture_group_model.list_for_package(conn, package_id)
    groups: list[dict] = []
    for grp_row in groups_raw:
        grp = _row_to_dict(grp_row)

        # list_for_fixture_group JOINs products — rows include product_manufacturer etc.
        mats_raw = project_material_model.list_for_fixture_group(conn, grp["id"])
        materials: list[dict] = []
        for mat_row in mats_raw:
            mat = _row_to_dict(mat_row)
            # The JOIN row includes product_manufacturer, product_model_number,
            # product_description but not cut_sheet_filename / spec_section — fetch those.
            if "cut_sheet_filename" not in mat:
                mat["cut_sheet_filename"] = _lookup_product_col(
                    conn, mat.get("product_id"), "cut_sheet_filename"
                )
            if "spec_section" not in mat:
                mat["spec_section"] = _lookup_product_col(
                    conn, mat.get("product_id"), "spec_section"
                )
            materials.append(mat)

        grp["materials"] = materials
        groups.append(grp)

    return {
        "package": pkg,
        "project": project,
        "company": company,
        "fixture_groups": groups,
        "assets_dir": _assets_dir(),
        "cut_sheets_dir": _cut_sheets_dir(),
    }


def _lookup_product_col(conn: sqlite3.Connection, product_id: int | None, col: str) -> str | None:
    if not product_id:
        return None
    row = conn.execute(
        f"SELECT {col} FROM products WHERE id = ?",  # noqa: S608 — col is internal only
        (product_id,),
    ).fetchone()
    return row[col] if row else None


# ---------------------------------------------------------------------------
# PO data assembly
# ---------------------------------------------------------------------------


def _assemble_po_data(conn: sqlite3.Connection, po_id: int) -> dict:
    """Fetch and structure all data needed to render a PO PDF."""
    po = _row_to_dict(po_model.get(conn, po_id))
    if not po:
        raise ValueError(f"Purchase order {po_id} not found.")

    supplier = _row_to_dict(supplier_model.get(conn, po["supplier_id"]))
    project = _row_to_dict(project_model.get(conn, po["project_id"]))
    company = _row_to_dict(company_model.get(conn, project.get("company_id", 0)))

    line_items = [_row_to_dict(li) for li in po_model.list_line_items_for_po(conn, po_id)]

    return {
        "po": po,
        "supplier": supplier,
        "project": project,
        "company": company,
        "line_items": line_items,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_submittal_pdf(
    conn: sqlite3.Connection,
    package_id: int,
    output_dir: Path | None = None,
) -> Path:
    """Assemble and write the submittal package PDF. Returns the output path."""
    if output_dir is None:
        output_dir = _output_dir_default()
    output_dir.mkdir(parents=True, exist_ok=True)

    data = _assemble_submittal_data(conn, package_id)
    pkg = data["package"]

    number = (pkg.get("submittal_number") or f"pkg{package_id}").replace("/", "-")
    rev = pkg.get("revision_number") or 0
    output_path = output_dir / f"{number}_rev{rev}.pdf"

    submittal_pdf.build(data, output_path)
    return output_path


def build_po_pdf(
    conn: sqlite3.Connection,
    po_id: int,
    output_dir: Path | None = None,
    field_receipt_mode: bool = False,
) -> Path:
    """Assemble and write the PO PDF (or field receipt sheet). Returns the output path."""
    if output_dir is None:
        output_dir = _output_dir_default()
    output_dir.mkdir(parents=True, exist_ok=True)

    data = _assemble_po_data(conn, po_id)
    po = data["po"]

    number = (po.get("po_number") or f"po{po_id}").replace("/", "-")
    suffix = "_receipt" if field_receipt_mode else ""
    output_path = output_dir / f"{number}{suffix}.pdf"

    po_pdf.build(data, output_path, field_receipt_mode=field_receipt_mode)
    return output_path
