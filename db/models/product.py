"""CRUD operations for the products (catalog) table."""

import sqlite3
from typing import Any

_ALLOWED_COLS = frozenset(
    {
        "manufacturer",
        "model_number",
        "description",
        "spec_section",
        "spec_section_title",
        "product_url",
        "submittal_notes",
        "cut_sheet_filename",
        "last_used_at",
    }
)


def _validate_cols(fields: dict) -> None:
    bad = set(fields) - _ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for products: {bad}")


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert a new product. Returns the new row id.

    Also sets last_used_at to the current UTC time automatically.
    """
    _validate_cols(fields)
    # Always stamp last_used_at on creation; caller value is overridden.
    fields["last_used_at"] = "datetime('now')"
    # Build the column list and placeholders, treating last_used_at specially
    # so the value goes through SQLite's datetime() function rather than as a
    # literal string.
    cols_except_luat = [c for c in fields if c != "last_used_at"]
    all_cols = cols_except_luat + ["last_used_at"]
    placeholders = ", ".join("?" for _ in cols_except_luat) + (
        (", " if cols_except_luat else "") + "datetime('now')"
    )
    columns = ", ".join(all_cols)
    values = [fields[c] for c in cols_except_luat]
    cur = conn.execute(
        f"INSERT INTO products ({columns}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, product_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    return cur.fetchone()


def update(conn: sqlite3.Connection, product_id: int, **fields: Any) -> None:
    """Update a product's fields. Always refreshes last_used_at to now."""
    # Remove last_used_at from caller fields (we control it); validate the rest.
    fields.pop("last_used_at", None)
    _validate_cols(fields)
    # Build SET clause: caller-supplied cols use ? placeholders; last_used_at
    # uses the SQLite function directly (not a value placeholder).
    set_parts = [f"{col} = ?" for col in fields.keys()]
    set_parts.append("last_used_at = datetime('now')")
    set_clause = ", ".join(set_parts)
    values = list(fields.values()) + [product_id]
    conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete(conn: sqlite3.Connection, product_id: int) -> None:
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
