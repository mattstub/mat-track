"""Shared pytest fixtures.

Tests use an in-memory SQLite database — not mocks and not the real data file.
This catches real SQL errors while staying fast and isolated.
"""

import sqlite3

import pytest

from db.schema import initialize_schema


@pytest.fixture
def db() -> sqlite3.Connection:
    """Return a fresh in-memory database with the full schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    initialize_schema(conn)
    return conn
