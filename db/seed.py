"""Development seed data.

Call seed(conn) at startup in dev mode. It is idempotent — it checks whether
the companies table is already populated before inserting anything.
"""

import sqlite3

from db.models import company as company_model
from db.models import project as project_model


def seed(conn: sqlite3.Connection) -> None:
    """Insert development seed data if the companies table is empty."""
    cur = conn.execute("SELECT COUNT(*) FROM companies")
    if cur.fetchone()[0] > 0:
        return

    mpu_id = company_model.create(
        conn,
        name="Matthews Plumbing & Utilities",
        short_name="MP&U",
        phone="(405) 748-4400",
        address="301 NW 132nd St, Oklahoma City, OK 73114",
    )

    company_model.create(
        conn,
        name="Utility Co",
        short_name="Utility Co",
    )

    project_model.create(
        conn,
        company_id=mpu_id,
        name="Wings Residence 001",
        project_number="2512",
        gc_name="Wynn Construction Co., Inc.",
        gc_project_number="25-392",
        architect_name="Bockus Payne",
        engineer_name="Darr & Collins Consulting Engineers",
        status="Active",
    )
