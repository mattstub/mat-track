"""CRUD operations for submittal_packages and submittal_revisions."""

import sqlite3
from typing import Any


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    raise NotImplementedError


def get(conn: sqlite3.Connection, package_id: int) -> sqlite3.Row | None:
    raise NotImplementedError


def list_for_project(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    raise NotImplementedError


def update(conn: sqlite3.Connection, package_id: int, **fields: Any) -> None:
    raise NotImplementedError


def next_submittal_number(conn: sqlite3.Connection, project_number: str) -> str:
    """Suggest the next sequential submittal number for a project (e.g. '2512-019')."""
    raise NotImplementedError


def has_open_revise_and_resubmit(
    conn: sqlite3.Connection, project_id: int, spec_section: str
) -> sqlite3.Row | None:
    """Return the open R&R package for this spec section, if one exists."""
    raise NotImplementedError


def create_revision(conn: sqlite3.Connection, package_id: int, **fields: Any) -> int:
    raise NotImplementedError
