"""PDF assembly orchestration.

Coordinates data retrieval and hands off to documents/submittal_pdf.py
and documents/po_pdf.py. Receives data objects — no direct DB calls from
within documents/ modules (keeps them reusable in web context).
"""

import sqlite3
from pathlib import Path


def build_submittal_pdf(
    conn: sqlite3.Connection, package_id: int, output_dir: Path
) -> Path:
    """Assemble and write the submittal package PDF. Returns the output path."""
    raise NotImplementedError


def build_po_pdf(
    conn: sqlite3.Connection,
    po_id: int,
    output_dir: Path,
    field_receipt_mode: bool = False,
) -> Path:
    """Assemble and write the PO PDF (or field receipt sheet). Returns the output path."""
    raise NotImplementedError
