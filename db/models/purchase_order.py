"""CRUD operations for purchase_orders and po_line_items."""

import sqlite3
from typing import Any


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    raise NotImplementedError


def get(conn: sqlite3.Connection, po_id: int) -> sqlite3.Row | None:
    raise NotImplementedError


def list_for_project(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    raise NotImplementedError


def update(conn: sqlite3.Connection, po_id: int, **fields: Any) -> None:
    raise NotImplementedError


def add_line_item(conn: sqlite3.Connection, **fields: Any) -> int:
    raise NotImplementedError


def list_line_items(conn: sqlite3.Connection, po_id: int) -> list[sqlite3.Row]:
    raise NotImplementedError


def update_line_item(conn: sqlite3.Connection, line_item_id: int, **fields: Any) -> None:
    raise NotImplementedError
