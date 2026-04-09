# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MatTrack** is a standalone PySide6 desktop application for Matthews Plumbing & Utilities that manages the full lifecycle of construction materials — from initial submittal through field receipt — across multiple projects. It is backed by a local SQLite database and generates PDFs for submittal packages and purchase orders.

The app is in early development (planning phase only as of the initial commit). The authoritative design document is `DEVELOPMENT.md`.

## Technology Stack

- **Python 3.11+**, **PySide6** (Qt6 UI), **SQLite** via `sqlite3`
- **ReportLab** for PDF generation (cover sheets, TOC, PO forms)
- **pypdf** for merging cut sheet PDFs into submittal packages
- **PyInstaller** for eventual packaging to .exe/.app

## Project Structure

```
mat_tracker/
├── main.py                  # App entry point
├── db/
│   ├── connection.py        # SQLite connection singleton
│   ├── schema.py            # CREATE TABLE + migration runner
│   └── models/              # CRUD per entity
├── core/
│   ├── lifecycle.py         # Stage calculation — no UI imports
│   ├── catalog.py           # Product search with usage history
│   └── document_builder.py  # PDF assembly orchestration
├── ui/
│   ├── main_window.py       # 3-panel layout + bottom tab bar
│   ├── panels/              # project, submittal, material, PO, catalog, supplier
│   ├── dialogs/             # new_project, new_submittal_package, add_material, etc.
│   └── widgets/             # stage_indicator, search_box
├── documents/
│   ├── submittal_pdf.py     # ReportLab submittal package builder
│   └── po_pdf.py            # ReportLab PO builder
├── data/                    # Runtime data — gitignored
│   ├── mat_tracker.db
│   ├── cut_sheets/          # Imported PDFs, referenced by filename only
│   ├── assets/              # Company logos
│   ├── returned_submittals/ # Stamped/returned PDFs from design team
│   └── output/              # Generated submittal + PO PDFs
└── tests/
    ├── test_lifecycle.py
    ├── test_catalog.py
    └── test_document_builder.py
```

## Core Domain Concepts

**Catalog vs. Instance:** A `Product` is a master catalog record (manufacturer, model, cut sheet). A `ProjectMaterial` is how that product appears on a specific job (tag designation, quantity, lifecycle stage, PO link, receipt data). Products are reused across projects; instances are per-project.

**Five Lifecycle Stages:**
1. Submittal Status — package submitted, awaiting review
2. Supplier Notified — approved product communicated to supplier
3. PO Issued — PO number assigned
4. Quantities Released — final quantities confirmed
5. Material Received — qty received logged at field/warehouse

**Lifecycle stage advancement** is determined by `core/lifecycle.py` using the fixture group's `review_status` — not the submittal package's overall status. A package returned as "Revise & Resubmit" may contain fixture groups individually marked "Approved As Submitted"; those groups' materials can advance to Stage 2 while rejected groups cannot.

**Submittal revisions vs. new packages:** When a spec section has an open "Revise & Resubmit" package, the app prompts to create a Revision (incrementing `revision_number` on the original record) rather than a new submittal number. Only rejected fixture groups are included in the revision PDF.

**Cut sheet storage:** Files live in `data/cut_sheets/`. The DB stores only the filename, never an absolute path. The same pattern applies to company logos (`data/assets/`) and returned submittals (`data/returned_submittals/`).

**PO Field Receipt Sheet:** The PO PDF has two output modes — standard (with unit prices) and field receipt sheet (prices suppressed, blank qty_received write-in column, signature line). Controlled by a checkbox at generation time.

## Database Design Notes

- Use standard SQL only — no SQLite-specific features. Schema must port to PostgreSQL with minimal changes (future ProManage integration).
- All IDs are integers (compatible with PostgreSQL serial).
- `core/lifecycle.py` and `core/catalog.py` must have zero UI imports — they will be reused as backend service functions in the ProManage web app.
- `documents/` module receives data objects, not DB connections — keeps it reusable in a web context.

## Build Phases (from DEVELOPMENT.md)

1. Core shell — DB schema, connection, Company/Project CRUD, main window, project panel
2. Product catalog — Product CRUD, catalog panel, catalog search with usage history
3. Submittals & materials — submittal packages, fixture groups, project materials, lifecycle widget
4. Suppliers & purchase orders
5. PDF generation — submittal packages + POs via ReportLab, cut sheet merging via pypdf
6. Lifecycle editing — stages 2–5 edit dialogs, receipt logging
7. Dashboard & action queues — "items needing action" views, CSV export

## Commands

```bash
# First-time setup — create venv and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run the app
.venv/bin/python main.py

# Run all tests
.venv/bin/python -m pytest

# Run a single test file
.venv/bin/python -m pytest tests/test_db_models.py

# Lint and format
.venv/bin/ruff check .
.venv/bin/ruff format .
```

## UI / UX Rules

### Material Design
- **qt-material** (`light_blue.xml` theme) is applied globally in `main.py`. Do not fight the theme with per-widget `setStyleSheet()` calls unless absolutely necessary.
- Follow Material Design principles: 8px spacing grid, clear typographic hierarchy (title → subtitle → body), flat buttons for secondary actions and raised/filled buttons for primary actions.
- Keep layouts simple and dense — users are tradespeople in the field, not designers. Minimize clicks to accomplish common tasks.

### Dialogs
- Every dialog that modifies data must have explicit **Save / Cancel** (or **OK / Cancel**) buttons — no auto-save on close.
- Validate required fields before accepting a dialog; highlight invalid fields inline rather than using a separate error popup.
- Dialogs that create records which could conflict (e.g., new submittal on a spec section with an open R&R) must check and prompt before proceeding.

### Error surfacing
- Use `QMessageBox.critical()` for errors the user must acknowledge. Never swallow exceptions silently or log to console only.
- Use `QMessageBox.question()` for destructive or irreversible actions (delete, override).

### Panels and navigation
- Panels are never responsible for fetching their own data unprompted — the main window drives data loading by calling `panel.load_project(id)` / `panel.refresh()` in response to user selection events.
- Selection changes in one panel emit a Qt signal; other panels connect to it. Panels do not call each other directly.

## Agent Team

Development uses a multi-agent model to parallelize work within each build phase. The main Claude Code instance acts as **Project Manager** and spawns specialist agents as needed.

### Roles

| Agent | Type | Responsibility |
|---|---|---|
| **Project Manager** | Main instance | Owns the branch, sequences work, spawns agents, synthesizes results, merges when clean |
| **Implementation** | `general-purpose` | Writes feature code for a specific module or layer (DB, core, UI, documents) |
| **Testing** | `general-purpose` | Writes and runs unit tests; reports failures and coverage gaps back to PM |
| **Security** | `general-purpose` | Reviews code for security issues; reports findings to PM for remediation |
| **Explore** | `Explore` | Reads and maps the codebase when the PM needs to understand structure before delegating |

The PM may spawn additional agents (e.g., a dedicated UI agent and a dedicated DB agent working in parallel) whenever two bodies of work within a phase are genuinely independent.

### Standard phase workflow

1. **PM** creates the branch (`phase/N-name`) before any code is written.
2. **PM** identifies which work within the phase can run in parallel and spawns Implementation agents accordingly — e.g., DB models and core logic can usually be implemented simultaneously.
3. When implementation is complete, **PM** spawns **Testing** and **Security** agents **in parallel** against the new code.
4. Both agents report findings back to PM. PM addresses all failures and warnings before proceeding.
5. **PM** runs `ruff check . && ruff format .` and confirms all tests pass, then merges to `main`.

### Agent ground rules

- **Security agent runs after every phase** — not just at the end of the project.
- **Testing agent writes tests before or alongside implementation** — not as an afterthought. PM should spawn the Testing agent as soon as the interface (function signatures, data shapes) is stable enough to test against.
- Agents do not merge to `main` — only the PM does, after all agent reports are clean.
- If a Testing or Security agent finds a blocking issue, PM pauses other agents and fixes it before continuing.
- Agents scoped to a layer (e.g., DB) do not touch files outside that layer without PM approval.

## Workflow Requirements

### Code style
- **ruff** is the linter and formatter (configured in `pyproject.toml`). Line length 100, Python 3.11+.
- Run `ruff check . && ruff format .` before committing. Fix all lint errors; do not suppress them without a comment explaining why.

### Git conventions
- **All work happens on a branch — never commit directly to `main`.** Create the branch before writing any code.
- Name branches by phase or feature: `phase/1-core-shell`, `feat/catalog-search`, `fix/submittal-revision-prompt`.
- Use **conventional commits**: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Commit at the logical unit level — one cohesive change per commit, not one commit per file.
- Merge to `main` only when the phase or feature is complete and tests pass.

### Testing
- Tests use a real **in-memory SQLite database** (`:memory:`) via the `db` fixture in `tests/conftest.py` — not mocks.
- `core/lifecycle.py` and `core/catalog.py` are pure Python with no UI imports; they should be fully unit-tested.
- `documents/` modules receive plain data dicts; test them by asserting on the PDF output file.
- The DB layer (`db/models/`) is tested by exercising real SQL against the in-memory schema.

### Build-phase discipline
- Complete each phase fully — all functions implemented, all related tests passing — before starting the next phase.
- Do not add features or UI polish that belong to a later phase while working on an earlier one.
- Stubs use `raise NotImplementedError`; replace them as each phase is worked, don't leave partial implementations.
