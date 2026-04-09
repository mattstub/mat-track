"""Product catalog search and reuse logic — stateless, no UI imports.

Stateless design means this module works as a service function in Flask/FastAPI
during ProManage migration without changes.
"""

import sqlite3
from dataclasses import dataclass


@dataclass
class ProductResult:
    id: int
    manufacturer: str
    model_number: str
    description: str
    spec_section: str | None
    cut_sheet_filename: str | None
    usage_count: int
    last_project_name: str | None
    last_submittal_status: str | None


def search_products(conn: sqlite3.Connection, query: str) -> list[ProductResult]:
    """Search catalog by manufacturer, model_number, or description.

    Results are sorted by last_used_at DESC (most recently used first).
    Each result includes usage history so the UI can surface
    "Previously approved on 2512 Wings" context.
    """
    raise NotImplementedError
