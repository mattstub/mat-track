"""CRUD operations for the projects table."""

import sqlite3
from typing import Any


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    raise NotImplementedError


def get(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    raise NotImplementedError


def list_all(conn: sqlite3.Connection, company_id: int | None = None) -> list[sqlite3.Row]:
    """Return all projects, optionally filtered by company."""
    raise NotImplementedError


def update(conn: sqlite3.Connection, project_id: int, **fields: Any) -> None:
    raise NotImplementedError


def delete(conn: sqlite3.Connection, project_id: int) -> None:
    raise NotImplementedError
