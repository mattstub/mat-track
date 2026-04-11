"""Stage calculation logic — no UI imports allowed.

This module is intentionally UI-free so it can be dropped into ProManage's backend unchanged.

Stage advancement rules:
  Stage 1 → 2: fixture_group.review_status is 'Approved As Submitted' or 'Approved As Noted'
  Stage 2 → 3: project_material.po_id is set
  Stage 3 → 4: po status is 'Issued' and qty_ordered is confirmed on po_line_items
  Stage 4 → 5: qty_received > 0 on po_line_items (partial) or fully_received = 1
"""

from typing import Any


def current_stage(material: dict[str, Any], fixture_group: dict[str, Any]) -> int:
    """Derive the current lifecycle stage for a project material.

    Args:
        material: A project_materials row as a dict.
        fixture_group: The parent fixture_groups row as a dict.

    Returns:
        The highest completed stage (1–5).
    """
    # Stage 5: fully received OR any qty received — trust most advanced state regardless
    fully_received = material.get("fully_received")
    qty_received = material.get("qty_received") or 0
    if fully_received or qty_received > 0:
        return 5

    # Evaluate stages 2–4 sequentially; each requires all prior conditions.
    approved_statuses = {"Approved As Submitted", "Approved As Noted"}
    review_status = fixture_group.get("review_status")
    supplier_notified = material.get("supplier_notified")
    stage_2_met = review_status in approved_statuses and bool(supplier_notified)

    if not stage_2_met:
        return 1

    po_id = material.get("po_id")
    stage_3_met = po_id is not None

    if not stage_3_met:
        return 2

    stored_stage = material.get("stage") or 1
    stage_4_met = stored_stage >= 4

    if not stage_4_met:
        return 3

    return 4


def can_advance_to_stage_2(fixture_group: dict[str, Any]) -> bool:
    """True if the fixture group's review_status clears materials for procurement."""
    approved_statuses = {"Approved As Submitted", "Approved As Noted"}
    return fixture_group.get("review_status") in approved_statuses


def stage_label(stage: int) -> str:
    """Human-readable label for a lifecycle stage number."""
    labels = {
        1: "Submittal",
        2: "Supplier Notified",
        3: "PO Issued",
        4: "Quantities Released",
        5: "Material Received",
    }
    return labels.get(stage, "Unknown")
