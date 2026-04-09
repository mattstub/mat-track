"""CRUD operations for the project_materials table."""

import sqlite3
from typing import Any


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    raise NotImplementedError


def get(conn: sqlite3.Connection, material_id: int) -> sqlite3.Row | None:
    raise NotImplementedError


def list_for_project(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    raise NotImplementedError


def list_for_fixture_group(conn: sqlite3.Connection, group_id: int) -> list[sqlite3.Row]:
    raise NotImplementedError


def list_without_po(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    """Return materials not yet assigned to any PO — used when building a new PO."""
    raise NotImplementedError


def update(conn: sqlite3.Connection, material_id: int, **fields: Any) -> None:
    raise NotImplementedError
