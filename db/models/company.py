"""CRUD operations for the companies table."""

import sqlite3
from typing import Any

_ALLOWED_COLS = frozenset({"name", "short_name", "address", "phone", "logo_filename", "notes"})


def _validate_cols(fields: dict) -> None:
    bad = set(fields) - _ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for companies: {bad}")


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert a new company. Returns the new row id."""
    _validate_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO companies ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, company_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
    return cur.fetchone()


def list_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM companies ORDER BY name")
    return cur.fetchall()


def update(conn: sqlite3.Connection, company_id: int, **fields: Any) -> None:
    if not fields:
        return
    _validate_cols(fields)
    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [company_id]
    conn.execute(f"UPDATE companies SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete(conn: sqlite3.Connection, company_id: int) -> None:
    conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
    conn.commit()
