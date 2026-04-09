"""SQLite connection singleton.

Provides a single shared connection for the lifetime of the app.
Swap this module for a PostgreSQL adapter (psycopg2/SQLAlchemy) during ProManage migration.
"""

import sqlite3
from pathlib import Path

_conn: sqlite3.Connection | None = None

DB_PATH = Path(__file__).parent.parent / "data" / "mat_tracker.db"


def get_connection() -> sqlite3.Connection:
    """Return the shared SQLite connection, creating it if needed."""
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


def close_connection() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
