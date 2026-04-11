"""CRUD operations for purchase_orders and po_line_items."""

import sqlite3
from typing import Any

_PO_ALLOWED_COLS = frozenset(
    {
        "project_id",
        "supplier_id",
        "po_number",
        "issue_date",
        "status",
        "shipping_address",
        "notes",
    }
)

_LINE_ITEM_ALLOWED_COLS = frozenset(
    {
        "purchase_order_id",
        "project_material_id",
        "qty_ordered",
        "qty_received",
        "unit_price",
        "receipt_date",
        "receipt_notes",
        "notes",
    }
)


def _validate_po_cols(fields: dict) -> None:
    bad = set(fields) - _PO_ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for purchase_orders: {bad}")


def _validate_line_item_cols(fields: dict) -> None:
    bad = set(fields) - _LINE_ITEM_ALLOWED_COLS
    if bad:
        raise ValueError(f"Invalid column(s) for po_line_items: {bad}")


# ---------------------------------------------------------------------------
# Purchase order CRUD
# ---------------------------------------------------------------------------


def create(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert a new purchase order. Returns the new row id."""
    _validate_po_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO purchase_orders ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, po_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM purchase_orders WHERE id = ?", (po_id,))
    return cur.fetchone()


def list_for_project(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    """Return all POs for a project, JOINed with supplier name, ordered by created_at DESC."""
    cur = conn.execute(
        """
        SELECT po.*, s.company_name AS supplier_company_name
        FROM purchase_orders po
        JOIN suppliers s ON s.id = po.supplier_id
        WHERE po.project_id = ?
        ORDER BY po.created_at DESC, po.id DESC
        """,
        (project_id,),
    )
    return cur.fetchall()


def list_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all POs across all projects, JOINed with supplier name, ordered by created_at DESC."""
    cur = conn.execute(
        """
        SELECT po.*, s.company_name AS supplier_company_name
        FROM purchase_orders po
        JOIN suppliers s ON s.id = po.supplier_id
        ORDER BY po.created_at DESC, po.id DESC
        """
    )
    return cur.fetchall()


def update(conn: sqlite3.Connection, po_id: int, **fields: Any) -> None:
    if not fields:
        return
    _validate_po_cols(fields)
    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [po_id]
    conn.execute(f"UPDATE purchase_orders SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete(conn: sqlite3.Connection, po_id: int) -> None:
    conn.execute("DELETE FROM purchase_orders WHERE id = ?", (po_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Line item CRUD
# ---------------------------------------------------------------------------


def add_line_item(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert a new PO line item. Returns the new row id."""
    _validate_line_item_cols(fields)
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO po_line_items ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def list_line_items_for_po(conn: sqlite3.Connection, po_id: int) -> list[sqlite3.Row]:
    """Return all line items for a PO, JOINed with project_materials, products, fixture_groups."""
    cur = conn.execute(
        """
        SELECT
            li.*,
            pm.quantity,
            pm.line_description,
            pm.fixture_group_id,
            p.manufacturer,
            p.model_number,
            p.description AS product_description,
            fg.tag_designation,
            fg.submittal_package_id
        FROM po_line_items li
        JOIN project_materials pm ON pm.id = li.project_material_id
        JOIN products p ON p.id = pm.product_id
        JOIN fixture_groups fg ON fg.id = pm.fixture_group_id
        WHERE li.purchase_order_id = ?
        """,
        (po_id,),
    )
    return cur.fetchall()


def update_line_item(conn: sqlite3.Connection, line_item_id: int, **fields: Any) -> None:
    if not fields:
        return
    _validate_line_item_cols(fields)
    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [line_item_id]
    conn.execute(f"UPDATE po_line_items SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete_line_item(conn: sqlite3.Connection, line_item_id: int) -> None:
    conn.execute("DELETE FROM po_line_items WHERE id = ?", (line_item_id,))
    conn.commit()
