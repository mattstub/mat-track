# MatTrack — Material Lifecycle Tracker

MatTrack is a desktop application built for **Matthews Plumbing & Utilities** to manage the full lifecycle of construction materials across active projects — from initial submittal through final field receipt.

The app replaces manual spreadsheet tracking with a structured, catalog-driven workflow that ensures the right product data flows consistently from the design team's approval all the way to the supplier's purchase order and the field crew's delivery receipt.

## What it does

- **Submittal management** — build and track submittal packages by spec section, manage fixture groups, and generate professional PDF packages with cover sheet, table of contents, and attached cut sheets.
- **Catalog reuse** — products are stored once and reused across any number of projects, surfacing prior approval history when selecting items for a new job.
- **Purchase orders** — generate POs directly from the same dataset driving lifecycle tracking. Supports a separate field receipt sheet (prices suppressed) for field crew sign-off on delivery.
- **Lifecycle tracking** — every material line item moves through five stages (Submittal → Supplier Notified → PO Issued → Quantities Released → Material Received) with a visual stage indicator per item.
- **Revision workflow** — detects open Revise & Resubmit packages and prompts to create a revision rather than a new submittal number, preventing orphaned tracking records.

## Development resources

| Resource | Purpose |
|---|---|
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Full application design doc — schema, UI layout, workflows, build phases |
| [`CLAUDE.md`](CLAUDE.md) | Development rules — coding conventions, agent team structure, branch/testing/security workflow |

## Tech stack

- **Python 3.11+** / **PySide6** (Qt6)
- **SQLite** (local) → designed to migrate to PostgreSQL for ProManage integration
- **ReportLab** for PDF generation, **pypdf** for cut sheet merging
- **qt-material** for Material Design UI theming

## Status

Active development — Phase 1 (core shell) in progress. See `DEVELOPMENT.md` §8 for the full phase breakdown.

---

*Built with the assistance of **[Claude Code](https://claude.ai/code)** by Anthropic — an AI coding assistant capable of architecting, scaffolding, and implementing full applications from a planning document. The project structure, database schema, agent-based development workflow, and initial codebase were generated collaboratively using Claude Code.*
