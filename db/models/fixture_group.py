"""CRUD operations for the fixture_groups table."""

import sqlite3
from typing import Any

_ALLOWED_COLS = frozenset(
    {
        "submittal_package_id",
        "tag_designation",
        "description",
        "quantity",
        "sort_order",
        "review_status",
        "review_notes",
        "notes",
    }
)


def _validate_cols(fields: dict) -> None:
    bad = set(fields) - _ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for fixture_groups: {bad}")


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert a new fixture group. Returns the new row id."""
    _validate_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO fixture_groups ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, group_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM fixture_groups WHERE id = ?", (group_id,))
    return cur.fetchone()


def list_for_package(conn: sqlite3.Connection, package_id: int) -> list[sqlite3.Row]:
    cur = conn.execute(
        """SELECT * FROM fixture_groups
           WHERE submittal_package_id = ?
           ORDER BY sort_order ASC, tag_designation ASC""",
        (package_id,),
    )
    return cur.fetchall()


def update(conn: sqlite3.Connection, group_id: int, **fields: Any) -> None:
    if not fields:
        return
    _validate_cols(fields)
    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [group_id]
    conn.execute(f"UPDATE fixture_groups SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete(conn: sqlite3.Connection, group_id: int) -> None:
    conn.execute("DELETE FROM fixture_groups WHERE id = ?", (group_id,))
    conn.commit()
