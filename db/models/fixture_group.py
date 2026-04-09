"""CRUD operations for the fixture_groups table."""

import sqlite3
from typing import Any


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    raise NotImplementedError


def get(conn: sqlite3.Connection, group_id: int) -> sqlite3.Row | None:
    raise NotImplementedError


def list_for_package(conn: sqlite3.Connection, package_id: int) -> list[sqlite3.Row]:
    raise NotImplementedError


def update(conn: sqlite3.Connection, group_id: int, **fields: Any) -> None:
    raise NotImplementedError


def delete(conn: sqlite3.Connection, group_id: int) -> None:
    raise NotImplementedError
