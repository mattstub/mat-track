"""CRUD operations for the suppliers table."""

import sqlite3
from typing import Any

_ALLOWED_COLS = frozenset(
    {
        "company_name",
        "contact_name",
        "email",
        "phone",
        "address",
        "notes",
        "notify_on_po",
        "notify_on_approval",
    }
)


def _validate_cols(fields: dict) -> None:
    bad = set(fields) - _ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for suppliers: {bad}")


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert a new supplier. Returns the new row id."""
    _validate_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO suppliers ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, supplier_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
    return cur.fetchone()


def get_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all suppliers ordered by company_name ASC."""
    cur = conn.execute("SELECT * FROM suppliers ORDER BY company_name ASC")
    return cur.fetchall()


def update(conn: sqlite3.Connection, supplier_id: int, **fields: Any) -> None:
    if not fields:
        return
    _validate_cols(fields)
    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [supplier_id]
    conn.execute(f"UPDATE suppliers SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete(conn: sqlite3.Connection, supplier_id: int) -> None:
    conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    conn.commit()
