"""CRUD operations for the projects table."""

import sqlite3
from typing import Any

_ALLOWED_COLS = frozenset(
    {
        "company_id",
        "name",
        "project_number",
        "gc_name",
        "gc_project_number",
        "architect_name",
        "engineer_name",
        "location",
        "status",
        "notes",
    }
)


def _validate_cols(fields: dict) -> None:
    bad = set(fields) - _ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for projects: {bad}")


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    _validate_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO projects ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    return cur.fetchone()


def list_all(conn: sqlite3.Connection, company_id: int | None = None) -> list[sqlite3.Row]:
    """Return all projects, optionally filtered by company."""
    if company_id is not None:
        cur = conn.execute(
            "SELECT * FROM projects WHERE company_id = ? ORDER BY name",
            (company_id,),
        )
    else:
        cur = conn.execute("SELECT * FROM projects ORDER BY name")
    return cur.fetchall()


def update(conn: sqlite3.Connection, project_id: int, **fields: Any) -> None:
    if not fields:
        return
    _validate_cols(fields)
    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [project_id]
    conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete(conn: sqlite3.Connection, project_id: int) -> None:
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
