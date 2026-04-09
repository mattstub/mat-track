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
    params: list = []
    where_clause = ""

    if query.strip():
        pattern = f"%{query}%"
        where_clause = """
        WHERE
            p.manufacturer  LIKE ? COLLATE NOCASE
         OR p.model_number  LIKE ? COLLATE NOCASE
         OR p.description   LIKE ? COLLATE NOCASE
        """
        params.extend([pattern, pattern, pattern])

    sql = f"""
        SELECT
            p.id,
            p.manufacturer,
            p.model_number,
            p.description,
            p.spec_section,
            p.cut_sheet_filename,
            COUNT(pm.id)                AS usage_count,
            latest.project_name         AS last_project_name,
            latest.submittal_status     AS last_submittal_status
        FROM products p
        LEFT JOIN project_materials pm
            ON pm.product_id = p.id
        LEFT JOIN (
            -- For each product, find the single most-recent project_material row
            -- and walk the chain to get project name and submittal status.
            SELECT
                pm2.product_id,
                proj.name               AS project_name,
                sp.status               AS submittal_status
            FROM project_materials pm2
            JOIN fixture_groups fg
                ON fg.id = pm2.fixture_group_id
            JOIN submittal_packages sp
                ON sp.id = fg.submittal_package_id
            JOIN projects proj
                ON proj.id = sp.project_id
            WHERE pm2.id = (
                SELECT pm3.id
                FROM project_materials pm3
                WHERE pm3.product_id = pm2.product_id
                ORDER BY pm3.created_at DESC, pm3.id DESC
                LIMIT 1
            )
        ) latest
            ON latest.product_id = p.id
        {where_clause}
        GROUP BY
            p.id,
            p.manufacturer,
            p.model_number,
            p.description,
            p.spec_section,
            p.cut_sheet_filename,
            latest.project_name,
            latest.submittal_status
        ORDER BY
            p.last_used_at DESC NULLS LAST,
            p.manufacturer  ASC
    """

    cursor = conn.execute(sql, params)
    rows = cursor.fetchall()

    results: list[ProductResult] = []
    for row in rows:
        results.append(
            ProductResult(
                id=row[0],
                manufacturer=row[1],
                model_number=row[2],
                description=row[3],
                spec_section=row[4],
                cut_sheet_filename=row[5],
                usage_count=row[6],
                last_project_name=row[7],
                last_submittal_status=row[8],
            )
        )
    return results
