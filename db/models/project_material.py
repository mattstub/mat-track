"""CRUD operations for the project_materials table."""

import sqlite3
from typing import Any

_ALLOWED_COLS = frozenset(
    {
        "fixture_group_id",
        "product_id",
        "project_id",
        "supplier_id",
        "line_description",
        "quantity",
        "stage",
        "supplier_notified",
        "supplier_notified_date",
        "supplier_notified_notes",
        "po_id",
        "qty_received",
        "receipt_date",
        "receipt_notes",
        "fully_received",
        "notes",
    }
)


def _validate_cols(fields: dict) -> None:
    bad = set(fields) - _ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for project_materials: {bad}")


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert a new project material. Returns the new row id."""
    _validate_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO project_materials ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, material_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM project_materials WHERE id = ?", (material_id,))
    return cur.fetchone()


def list_for_project(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM project_materials WHERE project_id = ?",
        (project_id,),
    )
    return cur.fetchall()


def list_for_fixture_group(conn: sqlite3.Connection, group_id: int) -> list[sqlite3.Row]:
    """Return materials for a fixture group, joined with product info for display."""
    cur = conn.execute(
        """
        SELECT pm.*,
               p.manufacturer  AS product_manufacturer,
               p.model_number  AS product_model_number,
               p.description   AS product_description
          FROM project_materials pm
          JOIN products p ON p.id = pm.product_id
         WHERE pm.fixture_group_id = ?
        """,
        (group_id,),
    )
    return cur.fetchall()


def list_without_po(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    """Return materials not yet assigned to any PO — used when building a new PO."""
    cur = conn.execute(
        "SELECT * FROM project_materials WHERE project_id = ? AND po_id IS NULL",
        (project_id,),
    )
    return cur.fetchall()


def update(conn: sqlite3.Connection, material_id: int, **fields: Any) -> None:
    if not fields:
        return
    _validate_cols(fields)
    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [material_id]
    conn.execute(f"UPDATE project_materials SET {set_clause} WHERE id = ?", values)
    conn.commit()
