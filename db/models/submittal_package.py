"""CRUD operations for submittal_packages and submittal_revisions."""

import sqlite3
from typing import Any

_ALLOWED_COLS = frozenset(
    {
        "project_id",
        "submittal_number",
        "spec_section",
        "spec_section_title",
        "title",
        "revision_number",
        "date_submitted",
        "date_returned",
        "status",
        "reviewer_name",
        "returned_pdf_path",
        "notes",
    }
)

_REVISION_ALLOWED_COLS = frozenset(
    {
        "submittal_package_id",
        "revision_number",
        "date_submitted",
        "date_returned",
        "status",
        "reviewer_name",
        "notes",
        "pdf_path",
    }
)


def _validate_cols(fields: dict) -> None:
    bad = set(fields) - _ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for submittal_packages: {bad}")


def _validate_revision_cols(fields: dict) -> None:
    bad = set(fields) - _REVISION_ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for submittal_revisions: {bad}")


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert a new submittal package. Returns the new row id."""
    _validate_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO submittal_packages ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, package_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM submittal_packages WHERE id = ?", (package_id,))
    return cur.fetchone()


def list_for_project(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM submittal_packages WHERE project_id = ? ORDER BY submittal_number ASC",
        (project_id,),
    )
    return cur.fetchall()


def update(conn: sqlite3.Connection, package_id: int, **fields: Any) -> None:
    if not fields:
        return
    _validate_cols(fields)
    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [package_id]
    conn.execute(f"UPDATE submittal_packages SET {set_clause} WHERE id = ?", values)
    conn.commit()


def next_submittal_number(conn: sqlite3.Connection, project_number: str) -> str:
    """Suggest the next sequential submittal number for a project (e.g. '2512-019')."""
    prefix = f"{project_number}-"
    cur = conn.execute(
        "SELECT submittal_number FROM submittal_packages WHERE submittal_number LIKE ?",
        (prefix + "%",),
    )
    rows = cur.fetchall()
    if not rows:
        return f"{project_number}-001"

    max_seq = 0
    for row in rows:
        number = row["submittal_number"]
        suffix = number[len(prefix) :]
        try:
            seq = int(suffix)
            if seq > max_seq:
                max_seq = seq
        except ValueError:
            continue

    next_seq = max_seq + 1
    return f"{project_number}-{next_seq:03d}"


def has_open_revise_and_resubmit(
    conn: sqlite3.Connection, project_id: int, spec_section: str
) -> sqlite3.Row | None:
    """Return the open R&R package for this spec section, if one exists."""
    cur = conn.execute(
        """SELECT * FROM submittal_packages
           WHERE project_id = ?
             AND spec_section = ?
             AND status = 'Revise & Resubmit'
           LIMIT 1""",
        (project_id, spec_section),
    )
    return cur.fetchone()


def create_revision(conn: sqlite3.Connection, package_id: int, **fields: Any) -> int:
    """Insert a row into submittal_revisions and return its id."""
    # Ensure submittal_package_id is set from the positional argument
    fields = {"submittal_package_id": package_id, **fields}
    _validate_revision_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO submittal_revisions ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid
