# MatTrack — Material Lifecycle Tracker
## Application Planning Document
**Version:** 0.2 — Revised Per Review  
**Author:** Matt Stubenhofer / Matthews Plumbing & Utilities  
**Purpose:** Standalone desktop application for managing material submittals, purchase orders, and lifecycle tracking across projects. Designed for eventual integration into ProManage.

---

## 1. Overview

MatTrack is a PyQt/PySide desktop application backed by a local SQLite database. Its primary purpose is to manage the full lifecycle of construction materials — from initial submittal through final field receipt — across multiple concurrent projects and companies.

The app operates on a **catalog-first model**: products are stored once as master records, then instantiated on projects with project-specific quantities, tag designations, and lifecycle status. This enables rapid reuse of previously approved submittal data across new jobs without re-entering manufacturer information.

A critical secondary function is **document generation**: the app produces submittal packages (PDF) and purchase orders (PDF) directly from the same dataset that drives the lifecycle tracking, ensuring the information flowing to the design team and the supplier is always in sync with what is tracked internally.

---

## 2. Core Concepts

### 2.1 The Five Lifecycle Stages

Every material line item moves through five sequential stages:

| Stage | Name | Key Action |
|---|---|---|
| 1 | Submittal Status | Package created, submitted to GC/Architect, status returned |
| 2 | Supplier Notified | Approved submittal communicated to supplier with product confirmation |
| 3 | PO Issued | Purchase order number assigned, sent to supplier |
| 4 | Quantities Released | Final quantities confirmed on PO |
| 5 | Material Received | Full or partial receipt logged at field or warehouse |

### 2.2 Catalog vs. Instance

- A **Product** (in the catalog) represents what a thing *is*: manufacturer, model number, description, spec section, cut sheet data. It exists once and is reused across any number of projects.
- A **ProjectMaterial** represents how that product is *used on a specific job*: tag designation (WC-1, SB-1), quantity, which submittal package it belongs to, which PO it's on, and its current lifecycle status.

### 2.3 Submittal Packages

A submittal package corresponds to a spec section (e.g., 220000 – Plumbing Fixtures). Within a project, you may have many submittal packages across different spec sections. Each package:

- Has a cover sheet (project info, GC, architect, engineer, submittal number, dates)
- Has a table of contents listing all fixture types and their components
- Contains one or more **Fixture Groups** (e.g., WC-1, LAV-1, SB-1)
- Each Fixture Group contains one or more **line items** drawn from the product catalog
- Is submitted as a single PDF to the GC/Architect
- Returns with a **package-level status** (Approved As Submitted, Approved As Noted, Revise & Resubmit)

**Fixture-Group-Level Status (within a returned package)**

When a package comes back with a Revise & Resubmit, not every fixture group inside it is necessarily rejected. The design team may approve WC-1 and LAV-1 outright while rejecting SK-1 (Sink) and requiring resubmission of only those items. MatTrack tracks approval status at both levels:

- The **package** carries the overall returned status and the reviewer's stamp information
- Each **fixture group** carries its own individual status from that review

This matters for lifecycle tracking downstream: if WC-1 is approved inside a Revise & Resubmit package, the toilet and seat are cleared for procurement. The sink items are not. Without fixture-group-level status, you cannot correctly advance Stage 1 (Submittal) for any individual material line inside a mixed-result package.

**The Revision Workflow**

The correct workflow when a package comes back Revise & Resubmit is:

1. Record the returned status at the package level (Revise & Resubmit)
2. Update each fixture group with its individual result (WC-1: Approved, SK-1: Revise & Resubmit)
3. Fixture groups marked approved advance their materials to Stage 2
4. Rejected fixture groups are updated — products swapped or specs revised in the catalog
5. A **Revision** of the same submittal number is created (2512-018 Rev 1), not a new package number
6. Only the rejected fixture groups are included in the revision package PDF
7. The revision is submitted, and the process repeats

The real-world failure mode this app prevents: generating a new submittal number (2512-019) for what should have been a revision to 2512-018. MatTrack surfaces the existing open package and prompts "This spec section has an open Revise & Resubmit — create Revision 1?" rather than allowing a new package to be started that orphans the original tracking record.

### 2.4 Purchase Orders

A PO is issued to a single supplier and references specific ProjectMaterial line items. The same project may have multiple POs to different suppliers. A PO:

- Links to a supplier record (contact, company, email, phone)
- Contains line items pulled from ProjectMaterials
- Tracks PO number, issue date, quantities ordered per line, and receipt status per line
- Is generated as a PDF

---

## 3. Database Schema (SQLite)

> All tables are designed to migrate to PostgreSQL (ProManage) with minimal changes. Use standard SQL types and avoid SQLite-specific features.

### 3.1 Companies

```sql
CREATE TABLE companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    short_name      TEXT,               -- e.g. "MP&U", "Utility Co"
    address         TEXT,
    phone           TEXT,
    logo_filename   TEXT,               -- filename in data/assets/ (e.g. "logo_mp.png")
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

**Company Logo in PDFs:** Both the submittal package cover sheet and purchase order header pull the logo from the company assigned to the project. Logo files are stored in `data/assets/` and referenced by filename, same pattern as cut sheets. The UI provides an **Import Logo** button on the company record. Since no project ever spans two companies, every document generated from a project will always use a single, consistent logo with no ambiguity.

### 3.2 Projects

```sql
CREATE TABLE projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    name            TEXT NOT NULL,
    project_number  TEXT,               -- e.g. "2512"
    gc_name         TEXT,               -- General Contractor
    gc_project_number TEXT,             -- GC's own project number
    architect_name  TEXT,
    engineer_name   TEXT,
    location        TEXT,
    status          TEXT DEFAULT 'Active',  -- Active, Complete, On Hold
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### 3.3 Suppliers

```sql
CREATE TABLE suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name    TEXT NOT NULL,
    contact_name    TEXT,
    email           TEXT,
    phone           TEXT,
    address         TEXT,
    notes           TEXT,
    notify_on_po    INTEGER DEFAULT 1,       -- boolean: send PO notification
    notify_on_approval INTEGER DEFAULT 1,   -- boolean: send approved submittal notification
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### 3.4 Product Catalog

```sql
CREATE TABLE products (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer        TEXT NOT NULL,
    model_number        TEXT NOT NULL,
    description         TEXT NOT NULL,
    spec_section        TEXT,               -- e.g. "220000", "221000"
    spec_section_title  TEXT,               -- e.g. "Plumbing Fixtures"
    product_url         TEXT,
    submittal_notes     TEXT,               -- notes that carry forward to new submittals
    cut_sheet_filename  TEXT,               -- filename only (e.g. "kohler_k25077.pdf")
                                            -- full path = data/cut_sheets/<filename>
    last_used_at        TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);
```

**Cut Sheet Storage:** All cut sheet PDFs are stored in `data/cut_sheets/` alongside the database. The `cut_sheet_filename` column stores only the filename, never an absolute path, so the whole `data/` folder can be moved or backed up as a unit. The UI provides an **Import Cut Sheet** button on the product detail dialog — this copies the selected file into `data/cut_sheets/` under a sanitized filename (manufacturer + model number), then writes the filename to the record. This makes it immediately obvious in the UI whether a product has a cut sheet attached or not, and removes the problem of broken paths from files moved after the fact.

### 3.5 Submittal Packages

**Submittal Number Auto-Suggestion:** When creating a new package on a project, the app reads the highest existing submittal sequence number for that project and suggests the next one. For project `2512`, if packages 001–018 exist, the dialog pre-fills `2512-019`. The number remains editable — the suggestion just removes the mental overhead of tracking the count.

```sql
CREATE TABLE submittal_packages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(id),
    submittal_number    TEXT NOT NULL,      -- e.g. "2512-018" (auto-suggested, user-editable)
    spec_section        TEXT,               -- e.g. "220000"
    spec_section_title  TEXT,               -- e.g. "Plumbing Fixtures"
    title               TEXT,               -- user-defined package title
    revision_number     INTEGER DEFAULT 0,
    date_submitted      TEXT,
    date_returned       TEXT,
    status              TEXT DEFAULT 'Not Submitted',
        -- Not Submitted | Submitted | Approved As Submitted |
        -- Approved As Noted | Revise & Resubmit | Rejected
    reviewer_name       TEXT,               -- architect/engineer who stamped it
    returned_pdf_path   TEXT,               -- filename in data/returned_submittals/
    notes               TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);
```

### 3.6 Fixture Groups

A fixture group is a logical grouping within a submittal package — e.g., "WC-1 Water Closet, LH" or "LAV-1 Lavatory". It maps to a line on the submittal table of contents. Each fixture group carries its own approval status independent of the package-level status, which is critical when a package comes back as Revise & Resubmit but only some groups are affected.

```sql
CREATE TABLE fixture_groups (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    submittal_package_id    INTEGER NOT NULL REFERENCES submittal_packages(id),
    tag_designation         TEXT NOT NULL,   -- e.g. "WC-1", "LAV-1", "SB-1"
    description             TEXT NOT NULL,   -- e.g. "Water Closet, LH Trip Lever"
    quantity                INTEGER,
    sort_order              INTEGER DEFAULT 0,
    -- Individual approval status returned from design team review
    review_status           TEXT DEFAULT 'Pending',
        -- Pending | Approved As Submitted | Approved As Noted |
        -- Revise & Resubmit | Rejected
    review_notes            TEXT,            -- reviewer comments specific to this group
    notes                   TEXT
);
```

> **Logic rule:** A fixture group's `review_status` can only be set after the parent `submittal_package` has been returned (i.e., `date_returned` is set). The `lifecycle.py` module uses the fixture group's `review_status` — not the package status — to determine whether its materials are cleared to advance to Stage 2.

### 3.7 Project Materials

A ProjectMaterial is a single product line item belonging to a fixture group. Many items may share one fixture group (e.g., WC-1 contains: toilet, seat, wax ring, supply line, angle valve, escutcheon).

```sql
CREATE TABLE project_materials (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_group_id    INTEGER NOT NULL REFERENCES fixture_groups(id),
    product_id          INTEGER NOT NULL REFERENCES products(id),
    project_id          INTEGER NOT NULL REFERENCES projects(id),
    supplier_id         INTEGER REFERENCES suppliers(id),

    -- Identity on this project
    line_description    TEXT,   -- override/clarify product description for this job if needed
    quantity            INTEGER DEFAULT 1,

    -- Lifecycle fields
    stage               INTEGER DEFAULT 1,   -- current highest completed stage (1-5)

    -- Stage 1: Submittal
    -- (derived from submittal_packages / fixture_groups — no duplicate fields needed)

    -- Stage 2: Supplier notified
    supplier_notified           INTEGER DEFAULT 0,   -- boolean
    supplier_notified_date      TEXT,
    supplier_notified_notes     TEXT,

    -- Stage 3: PO Issued
    po_id                       INTEGER REFERENCES purchase_orders(id),
    -- (qty_ordered lives on po_line_items)

    -- Stage 4: Quantities confirmed
    -- (tracked via po_line_items.qty_ordered and PO status)

    -- Stage 5: Receipt
    qty_received                INTEGER DEFAULT 0,
    receipt_date                TEXT,
    receipt_notes               TEXT,
    fully_received              INTEGER DEFAULT 0,   -- boolean

    notes                       TEXT,
    created_at                  TEXT DEFAULT (datetime('now'))
);
```

### 3.8 Purchase Orders

```sql
CREATE TABLE purchase_orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id),
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id),
    po_number       TEXT,
    issue_date      TEXT,
    status          TEXT DEFAULT 'Draft',
        -- Draft | Issued | Partial Receipt | Complete | Cancelled
    shipping_address TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE po_line_items (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_order_id       INTEGER NOT NULL REFERENCES purchase_orders(id),
    project_material_id     INTEGER NOT NULL REFERENCES project_materials(id),
    qty_ordered             INTEGER DEFAULT 0,
    qty_received            INTEGER DEFAULT 0,
    unit_price              REAL,               -- nullable; omitted from field receipt sheet
    receipt_date            TEXT,
    receipt_notes           TEXT,
    notes                   TEXT
);
```

**Field Receipt Sheet:** The PO PDF generator supports two output modes controlled by a checkbox at generation time:

- **Standard PO** — includes unit prices, totals, all fields. Sent to supplier and kept on file.
- **Field Receipt Sheet** — same line items and quantities, prices suppressed, `qty_received` column added as a blank write-in field, and a signature/date line at the bottom. Printed and handed to field personnel to count and sign off on delivery. The completed sheet is turned in and the `qty_received` values are manually entered into the system per line item, advancing the lifecycle to Stage 5.

### 3.9 Submittal History (Revisions)

```sql
CREATE TABLE submittal_revisions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    submittal_package_id    INTEGER NOT NULL REFERENCES submittal_packages(id),
    revision_number         INTEGER NOT NULL,
    date_submitted          TEXT,
    date_returned           TEXT,
    status                  TEXT,
    reviewer_name           TEXT,
    notes                   TEXT,
    pdf_path                TEXT,
    created_at              TEXT DEFAULT (datetime('now'))
);
```

---

## 4. Application Architecture

### 4.1 Technology Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| UI Framework | PySide6 (Qt6) |
| Database | SQLite via Python `sqlite3` |
| PDF Generation | ReportLab (programmatic) or WeasyPrint |
| Packaging | PyInstaller (single .exe or .app eventually) |
| Version Control | Git — eventually merged into ProManage repo |

### 4.2 Project Folder Structure

```
mat-track/
│
├── main.py                         # App entry point, splash, main window launch
│
├── db/
│   ├── __init__.py
│   ├── connection.py               # SQLite connection management
│   ├── schema.py                   # CREATE TABLE statements, migration runner
│   └── models/
│       ├── project.py
│       ├── product.py
│       ├── supplier.py
│       ├── submittal_package.py
│       ├── fixture_group.py
│       ├── project_material.py
│       └── purchase_order.py
│
├── core/
│   ├── __init__.py
│   ├── lifecycle.py                # Stage calculation logic (pure Python, no UI)
│   ├── catalog.py                  # Product search, reuse, fuzzy matching
│   └── document_builder.py        # PDF assembly logic (submittal packages, POs)
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py              # Main window shell, tab bar, panel layout
│   ├── panels/
│   │   ├── project_panel.py        # Left panel: project list + filter by company
│   │   ├── submittal_panel.py      # Center: submittal packages for selected project
│   │   ├── material_panel.py       # Center: materials view (by package or all)
│   │   ├── po_panel.py             # PO list and detail for selected project
│   │   ├── catalog_panel.py        # Product catalog browser/search/manage
│   │   └── supplier_panel.py       # Supplier management
│   ├── dialogs/
│   │   ├── new_project.py
│   │   ├── new_submittal_package.py
│   │   ├── new_fixture_group.py
│   │   ├── add_material.py         # Search catalog → assign to fixture group
│   │   ├── new_product.py          # Add new product to catalog
│   │   ├── new_po.py               # Create PO, select items + supplier
│   │   ├── lifecycle_edit.py       # Edit stages 2-5 for a material
│   │   └── supplier_edit.py
│   └── widgets/
│       ├── stage_indicator.py      # Color-coded pipeline stage badge widget
│       └── search_box.py           # Reusable catalog search widget
│
├── documents/
│   ├── __init__.py
│   ├── submittal_pdf.py            # Submittal package PDF builder
│   ├── po_pdf.py                   # Purchase order PDF builder
│   └── templates/
│       ├── cover_sheet.py          # Submittal cover sheet layout
│       └── toc.py                  # Table of contents layout
│
├── data/
│   ├── mat_tracker.db              # SQLite database (gitignored)
│   ├── cut_sheets/                 # Managed cut sheet PDFs (gitignored)
│   ├── assets/                     # Company logos and other static assets (gitignored)
│   ├── returned_submittals/        # PDFs of stamped/returned submittal packages (gitignored)
│   └── output/                     # Generated PDFs: submittals, POs, receipt sheets (gitignored)
│
├── assets/
│   ├── logo_mp.png                 # Matthews Plumbing logo
│   └── icons/                      # UI icons
│
├── tests/
│   ├── test_lifecycle.py
│   ├── test_catalog.py
│   └── test_document_builder.py
│
├── requirements.txt
└── README.md
```

---

## 5. UI Layout and Navigation

### 5.1 Main Window — Three-Panel Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  TOOLBAR:  [+ Project]  [+ Submittal]  [+ Material]  [+ PO]  [Search]   │
├────────────────┬──────────────────────────────┬─────────────────────────┤
│  PROJECTS      │  SUBMITTAL PACKAGES           │  DETAIL / ACTIONS       │
│  ─────────     │  ────────────────────         │  ───────────────────    │
│  Filter:       │  2512-018  Plbg Fixtures  ✓   │  [selected item info]   │
│  [All / MP&U   │  2512-019  Water Heaters  ●   │                         │
│   Utility Co]  │  2512-020  HVAC Equip     ○   │  Lifecycle Stage:       │
│                │                               │  ██ ██ ██ □ □  Stage 3  │
│  ▶ 2512 Wings  │  MATERIALS IN PACKAGE         │                         │
│    Residence   │  ────────────────────         │  [Edit Stages]          │
│  ▶ 2518 Cross- │  WC-1  │ K-25077-0  Kohler ✓ │  [Generate Submittal]   │
│    ings Church │  WC-1  │ PFTSC0FE.. Proflo ✓ │  [Generate PO]          │
│  ▶ 2601 Tinker │  LAV-1 │ K-2349-0   Kohler ✓ │                         │
│    Ops         │  LAV-1 │ 559HA-BL.. Delta  ✓ │  Supplier:              │
│                │  SB-1  │ 696-G1010  Sioux  ○ │  [Ferguson - Conrad G.] │
│  ─────────     │                               │                         │
│  [Manage       │                               │  PO: [None Issued]      │
│   Companies]   │                               │  Received: 0 / 4       │
└────────────────┴──────────────────────────────┴─────────────────────────┘
│  BOTTOM TABS:  [ Projects ]  [ Catalog ]  [ Suppliers ]  [ All POs ]    │
└──────────────────────────────────────────────────────────────────────────┘
```

**Stage indicator colors:**
- ⬜ Gray — Not started
- 🟡 Yellow — In progress / submitted / awaiting response
- 🟢 Green — Complete
- 🔴 Red — Rejected / action required

### 5.2 Key Workflows (User Stories)

**Starting a new project:**
1. Click `+ Project` → fill name, number, company, GC, architect, engineer
2. Project appears in left panel

**Building a submittal package:**
1. Select project → click `+ Submittal`
2. Enter spec section, submittal number, title
3. Add fixture groups (tags + descriptions): WC-1, WC-2, LAV-1, SB-1, etc.
4. For each fixture group, click `+ Material` → search catalog by manufacturer/model/description
5. Select matching product(s) from catalog — OR — add new product if not found
6. Set quantity per line item
7. Click `Generate Submittal PDF` → PDF opens/saves with cover sheet, TOC, and cut sheets

**Reusing catalog items on a new project:**
1. Adding a material → search catalog
2. Results show past usage: "Used on 2512 Wings, 2318 CrossingsChurch — previously approved"
3. Select → product data pre-fills; only set new quantity and tag designation

**Creating a purchase order:**
1. Select project → click `+ PO`
2. Select supplier from dropdown (or add new)
3. Dialog shows all project materials that do not yet have a PO assigned
4. Check items to include → enter quantities
5. Click `Generate PO PDF` → PDF saved, PO record created, materials linked

**Updating receipt status:**
1. Select a material → click `Edit Stages`
2. Enter qty received, date, notes
3. Stage indicator updates to 5 (or partial marker)

---

## 6. Document Generation

### 6.1 Submittal Package PDF Structure

All document output is PDF (not editable). PDF is generated programmatically using ReportLab.

```
Page 1:  Cover Sheet
         ─────────────────────────────
         [Company Logo]
         Job: [Project Name]
         Location: [Location]
         Project #: [Project Number]
         
         Spec Section No: [220000]
         Spec Section Title: [Plumbing Fixtures]
         Submittal Title: [user-defined]
         Submittal No: [2512-018]
         Revision No: [0]
         Sent Date: [10/23/2025]
         
         Contractor: [Matthews Plumbing]
           [Address]
         
         General Contractor: [Wynn Construction]
           [Address, Phone, Fax]
         
         Architect: [Bockus Payne]
           [Address, Phone]
         
         [Contractor Stamp Box]   [Architect Stamp Box]   [Engineer Stamp Box]

Page 2:  Table of Contents
         ─────────────────────────────
         Item No.  | Description               | Manufacturer | Model     | Qty
         ──────────────────────────────────────────────────────────────────────
         WC-1      | Water Closet, LH Trip Lev | Kohler       | K-25077-0 | 10
                   |   Toilet Seat             | ProFlo       | PFTSC0FE… | 10
                   |   Supply Line             | BrassCraft   | B1-12DL F | 10
                   |   Angle Stop              | BrassCraft   | G2CR19X C | 10
         LAV-1     | Lavatory                  | Kohler       | K-2349-0  | 13
                   |   Faucet                  | Delta        | 559HA-BL… | 13
                   |   Drain                   | Kohler       | K-7129-BL | 13
                   |   P-Trap                  | ProFlo       | PFPTP100  | 13
         ...

Pages 3+: Cut Sheets
         ─────────────────────────────
         Section divider page: "WC-1 — Water Closet"
         [Attached product cut sheet PDF pages for each item in WC-1]
         Section divider page: "LAV-1 — Lavatory"
         [Attached product cut sheet PDF pages for each item in LAV-1]
         ...
```

**Cut sheet attachment strategy:**  
When a product has a `cut_sheet_path` pointing to a stored PDF, those pages are merged directly into the submittal package PDF using PyPDF2 or pypdf. If no cut sheet is stored, a placeholder page is inserted indicating the item needs a cut sheet.

### 6.2 Purchase Order PDF Structure

```
Page 1:  PO Header
         ─────────────────────────────
         [Company Logo]                    PO NUMBER: [PO-2512-001]
         Matthews Plumbing & Utilities     DATE: [03/18/2026]
         301 NW 132nd St
         Oklahoma City, OK 73114
         (405) 748-4400

         TO:                               PROJECT:
         [Supplier Company Name]           [Project Name]
         [Contact Name]                    [Project Number]
         [Email]                           [GC Name]
         [Phone]

         ──────────────────────────────────────────────────────────────────
         QTY  | SPEC     | TAG   | MANUFACTURER | MODEL NUMBER | DESCRIPTION
         ─────────────────────────────────────────────────────────────────
          10  | 220000   | WC-1  | Kohler       | K-25077-0    | Kingston Toilet LH ADA
          10  | 220000   | WC-1  | ProFlo       | PFTSC0FE2000 | Commercial Toilet Seat
          13  | 220000   | LAV-1 | Kohler       | K-2349-0     | Camber Undermount Lav
         ...

         ──────────────────────────────────────────────────────────────────
         NOTES: [PO notes field]

         Authorized By: _______________________   Date: _______________
```

---

## 7. Catalog Reuse Logic (core/catalog.py)

When a user clicks `+ Material` and searches the catalog, the search returns:

```python
def search_products(query: str) -> list[ProductResult]:
    """
    Search by: manufacturer, model_number, description (all LIKE %query%)
    Returns results sorted by: last_used_at DESC (most recently used first)
    Each result includes:
      - product fields
      - usage_count: number of projects it has appeared on
      - last_project_name: name of most recent project
      - last_submittal_status: approval status from most recent use
    """
```

This surfaces "previously approved on 2512 Wings" information directly in the search results, making the reuse case fast and obvious.

---

## 8. Build Phases

### Phase 1 — Core Shell (get something running)
- [ ] `db/schema.py` — all CREATE TABLE statements, db init
- [ ] `db/connection.py` — connection singleton
- [ ] `db/models/` — basic CRUD for Company, Project
- [ ] `ui/main_window.py` — window shell, 3-panel layout, bottom tabs
- [ ] `ui/panels/project_panel.py` — project list with company filter
- [ ] `ui/dialogs/new_project.py` — create project dialog
- [ ] Seed 2 test companies + 1 test project

### Phase 2 — Product Catalog
- [ ] `db/models/product.py` — CRUD
- [ ] `ui/panels/catalog_panel.py` — browse, search
- [ ] `ui/dialogs/new_product.py` — add product, attach cut sheet path
- [ ] `core/catalog.py` — search with usage history

### Phase 3 — Submittals & Materials ✓
- [x] `db/models/submittal_package.py`, `fixture_group.py`, `project_material.py`
- [x] `ui/panels/submittal_panel.py` — package list per project
- [x] `ui/dialogs/new_submittal_package.py`
- [x] `ui/dialogs/new_fixture_group.py`
- [x] `ui/dialogs/add_material.py` — catalog search → assign to group
- [x] `ui/widgets/stage_indicator.py` — color-coded stage widget
- [x] `core/lifecycle.py` — stage calculation

### Phase 4 — Suppliers & Purchase Orders
- [ ] `db/models/supplier.py`, `purchase_order.py`
- [ ] `ui/panels/supplier_panel.py`
- [ ] `ui/panels/po_panel.py`
- [ ] `ui/dialogs/new_po.py` — select items, assign to PO
- [ ] `ui/dialogs/supplier_edit.py`

### Phase 5 — PDF: Submittal Package
- [ ] `documents/submittal_pdf.py` — ReportLab cover sheet + TOC
- [ ] `documents/po_pdf.py` — ReportLab PO layout
- [ ] Cut sheet PDF merging via pypdf
- [ ] PDF saved to `data/output/` keyed by project + submittal number

### Phase 6 — Lifecycle Editing
- [ ] `ui/dialogs/lifecycle_edit.py` — edit stages 2–5
- [ ] Supplier notification status fields
- [ ] Receipt logging (partial vs. full)

### Phase 7 — Dashboard & Action Queues
- [ ] "Items Needing Action" view — anything stuck at stage 1-4
- [ ] Supplier notification queue — approved submittals not yet sent to supplier
- [ ] Overdue receipt tracking
- [ ] Export to CSV

---

## 9. ProManage Migration Path

The following design decisions are intentional to ease future migration:

| Decision | Reason |
|---|---|
| Standard SQL (no SQLite-isms) | Direct schema port to PostgreSQL |
| `core/lifecycle.py` has no UI imports | Drop into ProManage's backend unchanged |
| `core/catalog.py` is stateless | Works as a service function in Flask/FastAPI |
| `documents/` module takes data objects, not DB calls | Reusable in web context with minimal changes |
| `company_id` on projects (not siloed DBs) | Matches multi-tenant ProManage model |
| All IDs are integers | Compatible with PostgreSQL serial/sequence IDs |

When the time comes, the migration steps will be:
1. Export SQLite DB to CSV (one table per file)
2. Import CSVs into PostgreSQL with matching schema
3. Swap `db/connection.py` for a PostgreSQL adapter (psycopg2 or SQLAlchemy)
4. Port `ui/` panels into Flask/React views
5. `core/` and `documents/` modules require no changes

---

## 10. Key Design Decisions

All items below have been decided. No open questions remain before coding begins.

| Decision | Resolution |
|---|---|
| PDF output only | No editable Word/Excel output. PDF prevents recipients from manipulating content. |
| Single SQLite database | One DB, company filter on projects. No siloed databases per company. |
| Cut sheet storage | `data/cut_sheets/` alongside DB. Import function copies file in and records filename. No absolute paths stored. |
| Submittal number format | Auto-suggested (`[project_number]-[NNN]` sequential), user-editable before saving. |
| Company logo in PDFs | Pulled from company record assigned to the project. Stored in `data/assets/`. Import Logo button on company form. |
| Small consumable items | No special flag needed. All items can appear on a Field Receipt Sheet with a blank write-in qty column. Prices suppressed on receipt sheet — field personnel fill in what was received and return it. Values entered into system manually. |
| Fixture-group-level status | Each fixture group carries its own `review_status` independent of the package. `lifecycle.py` advances materials based on group status, not package status. |
| Revision vs. new package | MatTrack detects open Revise & Resubmit packages per spec section and prompts to create a Revision rather than a new package number. Revisions increment `revision_number` on the original package record and are logged in `submittal_revisions`. Only rejected fixture groups are included in the revision PDF. |
| ReportLab for PDF generation | Programmatic layout control needed for cover sheets, TOC, and PO forms. |
| pypdf for cut sheet merging | Merges stored cut sheet PDFs directly into submittal package output. |
| PySide6 for UI | Qt6, modern, capable. |

---

## 11. Reference Data From 2512 Wings Residence

The following data from the attached submittal package and order email can seed initial catalog records and validate the data model during development.

### Sample Projects
- **Project:** Wings Residence 001 | Number: 2512 | Company: Matthews Plumbing & Utilities
- **GC:** Wynn Construction Co., Inc. | GC Project #: 25-392
- **Architect:** Bockus Payne
- **Engineer:** Darr & Collins Consulting Engineers

### Sample Submittal Package
- **Submittal #:** 2512-018
- **Spec Section:** 220000 – Plumbing Fixtures
- **Sent Date:** 10/23/2025
- **Returned:** 3/18/2026 | Reviewer: Danny Choate (BPA) | Status: No Exceptions

### Sample Fixture Groups and Products (for catalog seeding)

| Tag | Fixture Description | Qty | Manufacturer | Model | Description |
|---|---|---|---|---|---|
| WC-1 | Water Closet, LH | 10 | Kohler | K-25077-0 | Kingston LH Trip Lever ADA Toilet 1.28GPF |
| WC-1 | | 10 | ProFlo | PFTSC0FE2000WH | Elongated Commercial Toilet Seat, White |
| WC-2 | Water Closet, RH | 3 | Kohler | K-25077-RA-0 | Kingston RH Trip Lever ADA Toilet 1.28GPF |
| WC-2 | | 3 | ProFlo | PFTSC0FE2000WH | Elongated Commercial Toilet Seat, White |
| LAV-1 | Lavatory | 13 | Kohler | K-2349-0 | Camber 16-1/4" Round Undermount Lav |
| LAV-1 | | 13 | Delta | 559HA-BL-DST | Trinsic High Arc Swivel Faucet, Matte Black |
| LAV-1 | | 13 | Kohler | K-7129-BL | Grid Drain No Overflow, Matte Black |
| LAV-1 | | 13 | (Generic) | — | Tubular Bag Trap 1-1/2 x 1-1/4 |
| SK-1 | Sink | 4 | Blanco | 402928 | PRECIS Cascade SILGRANIT, Volcano Gray |
| SK-1 | | 4 | Delta | 9159-BL-DST | Trinsic Single Handle Pull-Down, Matte Black |
| SK-1 | | 4 | ProFlo | PF171MB | Basket Strainer, Matte Black |
| SK-1 | | 4 | (Generic) | — | Tubular Bag Trap 1-1/2 x 1-1/4 |
| WH-1 | Water Heater | 4 | State | ENG-40-DORT | ProLine 40-Gal Electric Water Heater |
| WH-1 | | 4 | ProFlo | PFXT5I | Potable Water Expansion Tank 2.1 gal |
| WH-1 | | 4 | (Generic) | — | 21" Stand |
| WH-1 | | 4 | (Generic) | — | 21" Pan w/ CPVC Connection |
| WC-3 | Water Cooler | 1 | Elkay | LZSTL8WSLP | Enhanced Bottle Filler & Bi-Level ADA Cooler |
| MS-1 | Mop Sink | 1 | Florestone | MSR-2424 | Molded Mop Receptor 24x24 w/ 3" Rubber Gasket |
| MS-1 | | 1 | Moen | 8230 | Commercial Two-Handle Service Sink Faucet |
| IMB-1 | Ice Maker Box | — | Sioux Chief | 696-G1010 | OxBox Ice Maker Outlet Box w/ Arresters |
| WMB-1 | Washer Box | — | Sioux Chief | 696-G2313XF | OxBox Washing Machine Outlet Box |
| WH-2 | Wall Hydrant | — | PRIER | C-144 | Freezeless Wall Hydrant, Anti-Siphon |
| CO-1 | Cleanout | — | Sioux Chief | 834-4PNR | FinishLine Adjustable Floor Cleanout 4" |

### Sample Supplier (from order email context)
- **Company:** Ferguson Enterprises
- **Contact:** Conrad Garcia
- **CC:** Scott Rudes
- **Email:** (from email chain — to be recorded)

---

*End of Planning Document v0.2 — All design decisions finalized. Ready for Phase 1 coding.*
