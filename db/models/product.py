"""CRUD operations for the products (catalog) table."""

import sqlite3
from typing import Any


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    raise NotImplementedError


def get(conn: sqlite3.Connection, product_id: int) -> sqlite3.Row | None:
    raise NotImplementedError


def update(conn: sqlite3.Connection, product_id: int, **fields: Any) -> None:
    raise NotImplementedError


def delete(conn: sqlite3.Connection, product_id: int) -> None:
    raise NotImplementedError
