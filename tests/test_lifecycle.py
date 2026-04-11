"""Tests for core/lifecycle.py — stage calculation logic."""

from core.lifecycle import can_advance_to_stage_2, current_stage, stage_label

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_material(**overrides):
    """Return a minimal project_materials-like dict."""
    defaults = {
        "fully_received": 0,
        "qty_received": 0,
        "supplier_notified": 0,
        "po_id": None,
        "stage": 1,
    }
    defaults.update(overrides)
    return defaults


def make_group(**overrides):
    """Return a minimal fixture_groups-like dict."""
    defaults = {"review_status": "Pending"}
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# current_stage
# ---------------------------------------------------------------------------


class TestCurrentStage:
    def test_returns_1_when_review_status_is_pending(self):
        m = make_material()
        g = make_group(review_status="Pending")
        assert current_stage(m, g) == 1

    def test_returns_1_when_approved_but_supplier_not_notified(self):
        m = make_material(supplier_notified=0)
        g = make_group(review_status="Approved As Submitted")
        assert current_stage(m, g) == 1

    def test_returns_1_when_approved_as_noted_but_supplier_not_notified(self):
        m = make_material(supplier_notified=None)
        g = make_group(review_status="Approved As Noted")
        assert current_stage(m, g) == 1

    def test_returns_2_when_approved_and_supplier_notified_and_no_po(self):
        m = make_material(supplier_notified=1, po_id=None)
        g = make_group(review_status="Approved As Submitted")
        assert current_stage(m, g) == 2

    def test_returns_2_for_approved_as_noted_and_supplier_notified_and_no_po(self):
        m = make_material(supplier_notified=1, po_id=None)
        g = make_group(review_status="Approved As Noted")
        assert current_stage(m, g) == 2

    def test_returns_3_when_stage2_met_and_po_set(self):
        m = make_material(supplier_notified=1, po_id=42, stage=3)
        g = make_group(review_status="Approved As Submitted")
        assert current_stage(m, g) == 3

    def test_returns_4_when_stage3_met_and_material_stage_gte_4(self):
        m = make_material(supplier_notified=1, po_id=42, stage=4)
        g = make_group(review_status="Approved As Submitted")
        assert current_stage(m, g) == 4

    def test_returns_4_when_stage_is_5_but_not_received(self):
        # stage field >= 4 puts us at stage 4 (no receipt data)
        m = make_material(supplier_notified=1, po_id=42, stage=5, fully_received=0, qty_received=0)
        g = make_group(review_status="Approved As Submitted")
        assert current_stage(m, g) == 4

    def test_returns_5_when_fully_received(self):
        m = make_material(fully_received=1)
        g = make_group(review_status="Pending")
        assert current_stage(m, g) == 5

    def test_returns_5_when_qty_received_gt_0(self):
        m = make_material(qty_received=3)
        g = make_group(review_status="Pending")
        assert current_stage(m, g) == 5

    def test_returns_5_even_when_lower_stage_conditions_not_met(self):
        # supplier_notified is falsy but qty_received > 0 — most advanced wins
        m = make_material(supplier_notified=0, po_id=None, qty_received=1)
        g = make_group(review_status="Pending")
        assert current_stage(m, g) == 5

    def test_none_qty_received_treated_as_zero(self):
        m = make_material(qty_received=None, fully_received=0, supplier_notified=0)
        g = make_group(review_status="Pending")
        # qty_received=None should NOT trigger stage 5
        assert current_stage(m, g) == 1

    def test_none_po_id_treated_as_not_set(self):
        m = make_material(supplier_notified=1, po_id=None)
        g = make_group(review_status="Approved As Submitted")
        # po_id=None → stage 2, not 3
        assert current_stage(m, g) == 2


# ---------------------------------------------------------------------------
# can_advance_to_stage_2
# ---------------------------------------------------------------------------


class TestCanAdvanceToStage2:
    def test_true_for_approved_as_submitted(self):
        assert can_advance_to_stage_2({"review_status": "Approved As Submitted"}) is True

    def test_true_for_approved_as_noted(self):
        assert can_advance_to_stage_2({"review_status": "Approved As Noted"}) is True

    def test_false_for_pending(self):
        assert can_advance_to_stage_2({"review_status": "Pending"}) is False

    def test_false_for_revise_and_resubmit(self):
        assert can_advance_to_stage_2({"review_status": "Revise & Resubmit"}) is False

    def test_false_for_rejected(self):
        assert can_advance_to_stage_2({"review_status": "Rejected"}) is False

    def test_false_when_review_status_is_none(self):
        assert can_advance_to_stage_2({"review_status": None}) is False

    def test_false_when_key_missing(self):
        assert can_advance_to_stage_2({}) is False


# ---------------------------------------------------------------------------
# stage_label
# ---------------------------------------------------------------------------


class TestStageLabel:
    def test_stage_1(self):
        assert stage_label(1) == "Submittal"

    def test_stage_2(self):
        assert stage_label(2) == "Supplier Notified"

    def test_stage_3(self):
        assert stage_label(3) == "PO Issued"

    def test_stage_4(self):
        assert stage_label(4) == "Quantities Released"

    def test_stage_5(self):
        assert stage_label(5) == "Material Received"

    def test_out_of_range_returns_unknown(self):
        assert stage_label(0) == "Unknown"

    def test_large_out_of_range_returns_unknown(self):
        assert stage_label(99) == "Unknown"
