"""Database schema — CREATE TABLE statements and migration runner.

All SQL is standard (no SQLite-specific features) to ease future PostgreSQL migration.
"""

import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    short_name      TEXT,
    address         TEXT,
    phone           TEXT,
    logo_filename   TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id        INTEGER NOT NULL REFERENCES companies(id),
    name              TEXT NOT NULL,
    project_number    TEXT,
    gc_name           TEXT,
    gc_project_number TEXT,
    architect_name    TEXT,
    engineer_name     TEXT,
    location          TEXT,
    status            TEXT DEFAULT 'Active',
    notes             TEXT,
    created_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS suppliers (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name       TEXT NOT NULL,
    contact_name       TEXT,
    email              TEXT,
    phone              TEXT,
    address            TEXT,
    notes              TEXT,
    notify_on_po       INTEGER DEFAULT 1,
    notify_on_approval INTEGER DEFAULT 1,
    created_at         TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer        TEXT NOT NULL,
    model_number        TEXT NOT NULL,
    description         TEXT NOT NULL,
    spec_section        TEXT,
    spec_section_title  TEXT,
    product_url         TEXT,
    submittal_notes     TEXT,
    cut_sheet_filename  TEXT,
    last_used_at        TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS submittal_packages (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id        INTEGER NOT NULL REFERENCES projects(id),
    submittal_number  TEXT NOT NULL,
    spec_section      TEXT,
    spec_section_title TEXT,
    title             TEXT,
    revision_number   INTEGER DEFAULT 0,
    date_submitted    TEXT,
    date_returned     TEXT,
    status            TEXT DEFAULT 'Not Submitted',
    reviewer_name     TEXT,
    returned_pdf_path TEXT,
    notes             TEXT,
    created_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fixture_groups (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    submittal_package_id INTEGER NOT NULL REFERENCES submittal_packages(id),
    tag_designation      TEXT NOT NULL,
    description          TEXT NOT NULL,
    quantity             INTEGER,
    sort_order           INTEGER DEFAULT 0,
    review_status        TEXT DEFAULT 'Pending',
    review_notes         TEXT,
    notes                TEXT
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id       INTEGER NOT NULL REFERENCES projects(id),
    supplier_id      INTEGER NOT NULL REFERENCES suppliers(id),
    po_number        TEXT,
    issue_date       TEXT,
    status           TEXT DEFAULT 'Draft',
    shipping_address TEXT,
    notes            TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_materials (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_group_id         INTEGER NOT NULL REFERENCES fixture_groups(id),
    product_id               INTEGER NOT NULL REFERENCES products(id),
    project_id               INTEGER NOT NULL REFERENCES projects(id),
    supplier_id              INTEGER REFERENCES suppliers(id),
    line_description         TEXT,
    quantity                 INTEGER DEFAULT 1,
    stage                    INTEGER DEFAULT 1,
    supplier_notified        INTEGER DEFAULT 0,
    supplier_notified_date   TEXT,
    supplier_notified_notes  TEXT,
    po_id                    INTEGER REFERENCES purchase_orders(id),
    qty_received             INTEGER DEFAULT 0,
    receipt_date             TEXT,
    receipt_notes            TEXT,
    fully_received           INTEGER DEFAULT 0,
    notes                    TEXT,
    created_at               TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS po_line_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_order_id   INTEGER NOT NULL REFERENCES purchase_orders(id),
    project_material_id INTEGER NOT NULL REFERENCES project_materials(id),
    qty_ordered         INTEGER DEFAULT 0,
    qty_received        INTEGER DEFAULT 0,
    unit_price          REAL,
    receipt_date        TEXT,
    receipt_notes       TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS submittal_revisions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    submittal_package_id INTEGER NOT NULL REFERENCES submittal_packages(id),
    revision_number      INTEGER NOT NULL,
    date_submitted       TEXT,
    date_returned        TEXT,
    status               TEXT,
    reviewer_name        TEXT,
    notes                TEXT,
    pdf_path             TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);
"""


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create all tables if they do not already exist."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()
