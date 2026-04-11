"""Phase 6 — lifecycle editing integration tests.

Tests verify that all lifecycle-stage fields can be written and read back through
the project_material model, and that current_stage derives the correct stage from
the persisted values (no Qt widgets required).
"""

import sqlite3

import pytest

from core.lifecycle import current_stage
from db.models import company as company_model
from db.models import fixture_group as fixture_group_model
from db.models import product as product_model
from db.models import project as project_model
from db.models import project_material as pm_model
from db.models import purchase_order as po_model
from db.models import submittal_package as package_model
from db.models import supplier as supplier_model

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(db: sqlite3.Connection) -> sqlite3.Connection:
    return db


@pytest.fixture
def company_id(conn: sqlite3.Connection) -> int:
    return company_model.create(conn, name="Test Co")


@pytest.fixture
def project_id(conn: sqlite3.Connection, company_id: int) -> int:
    return project_model.create(
        conn,
        name="Test Project",
        project_number="TP-001",
        company_id=company_id,
    )


@pytest.fixture
def product_id(conn: sqlite3.Connection) -> int:
    return product_model.create(
        conn,
        manufacturer="Acme",
        model_number="X-100",
        description="Widget",
    )


@pytest.fixture
def package_id(conn: sqlite3.Connection, project_id: int) -> int:
    return package_model.create(
        conn,
        project_id=project_id,
        submittal_number="SP-01",
        spec_section="26 50 00",
        spec_section_title="Lighting",
    )


@pytest.fixture
def group_id(conn: sqlite3.Connection, package_id: int) -> int:
    return fixture_group_model.create(
        conn,
        submittal_package_id=package_id,
        tag_designation="LP-1",
        description="LED Pendant",
        quantity=4,
    )


@pytest.fixture
def material_id(conn: sqlite3.Connection, group_id: int, product_id: int, project_id: int) -> int:
    return pm_model.create(
        conn,
        fixture_group_id=group_id,
        product_id=product_id,
        project_id=project_id,
    )


@pytest.fixture
def supplier_id(conn: sqlite3.Connection) -> int:
    return supplier_model.create(conn, company_name="Best Supply")


@pytest.fixture
def po_id(conn: sqlite3.Connection, project_id: int, supplier_id: int) -> int:
    return po_model.create(conn, project_id=project_id, supplier_id=supplier_id, po_number="PO-001")


# ---------------------------------------------------------------------------
# Stage field update roundtrip
# ---------------------------------------------------------------------------


class TestLifecycleFieldRoundtrip:
    def test_update_supplier_notified_fields(self, conn, material_id):
        pm_model.update(
            conn,
            material_id,
            supplier_notified=1,
            supplier_notified_date="2026-04-10",
            supplier_notified_notes="Called Alex",
        )
        row = dict(pm_model.get(conn, material_id))
        assert row["supplier_notified"] == 1
        assert row["supplier_notified_date"] == "2026-04-10"
        assert row["supplier_notified_notes"] == "Called Alex"

    def test_clear_supplier_notified(self, conn, material_id):
        pm_model.update(conn, material_id, supplier_notified=1)
        pm_model.update(conn, material_id, supplier_notified=0, supplier_notified_date=None)
        row = dict(pm_model.get(conn, material_id))
        assert row["supplier_notified"] == 0
        assert row["supplier_notified_date"] is None

    def test_update_receipt_fields(self, conn, material_id):
        pm_model.update(
            conn,
            material_id,
            qty_received=4,
            fully_received=1,
            receipt_date="2026-05-01",
            receipt_notes="All on truck",
        )
        row = dict(pm_model.get(conn, material_id))
        assert row["qty_received"] == 4
        assert row["fully_received"] == 1
        assert row["receipt_date"] == "2026-05-01"
        assert row["receipt_notes"] == "All on truck"

    def test_update_stage_field(self, conn, material_id):
        pm_model.update(conn, material_id, stage=4)
        row = dict(pm_model.get(conn, material_id))
        assert row["stage"] == 4

    def test_invalid_column_raises(self, conn, material_id):
        with pytest.raises(ValueError, match="Invalid column"):
            pm_model.update(conn, material_id, qty_released=10)

    def test_invalid_column_lifecycle_stage_raises(self, conn, material_id):
        with pytest.raises(ValueError, match="Invalid column"):
            pm_model.update(conn, material_id, lifecycle_stage=4)


# ---------------------------------------------------------------------------
# Stage derivation after save (mirrors LifecycleEditDialog._on_save logic)
# ---------------------------------------------------------------------------


class TestStageAfterSave:
    def _approve_group(self, conn, group_id):
        fixture_group_model.update(conn, group_id, review_status="Approved As Submitted")

    def test_stage_1_when_not_approved(self, conn, material_id, group_id):
        mat = dict(pm_model.get(conn, material_id))
        grp = dict(fixture_group_model.get(conn, group_id))
        assert current_stage(mat, grp) == 1

    def test_stage_2_after_supplier_notified(self, conn, material_id, group_id):
        self._approve_group(conn, group_id)
        pm_model.update(conn, material_id, supplier_notified=1, stage=2)
        mat = dict(pm_model.get(conn, material_id))
        grp = dict(fixture_group_model.get(conn, group_id))
        assert current_stage(mat, grp) == 2

    def test_stage_3_after_po_assigned(
        self, conn, material_id, group_id, project_id, supplier_id, po_id
    ):
        self._approve_group(conn, group_id)
        pm_model.update(conn, material_id, supplier_notified=1, po_id=po_id, stage=3)
        mat = dict(pm_model.get(conn, material_id))
        grp = dict(fixture_group_model.get(conn, group_id))
        assert current_stage(mat, grp) == 3

    def test_stage_4_after_qty_released(
        self, conn, material_id, group_id, project_id, supplier_id, po_id
    ):
        self._approve_group(conn, group_id)
        pm_model.update(conn, material_id, supplier_notified=1, po_id=po_id, stage=4)
        mat = dict(pm_model.get(conn, material_id))
        grp = dict(fixture_group_model.get(conn, group_id))
        assert current_stage(mat, grp) == 4

    def test_stage_5_after_receipt(self, conn, material_id, group_id):
        pm_model.update(conn, material_id, qty_received=4, fully_received=1, stage=5)
        mat = dict(pm_model.get(conn, material_id))
        grp = dict(fixture_group_model.get(conn, group_id))
        assert current_stage(mat, grp) == 5

    def test_stage_5_partial_receipt(self, conn, material_id, group_id):
        pm_model.update(conn, material_id, qty_received=2, fully_received=0, stage=5)
        mat = dict(pm_model.get(conn, material_id))
        grp = dict(fixture_group_model.get(conn, group_id))
        assert current_stage(mat, grp) == 5

    def test_qty_released_checkbox_seeds_stage_4_correctly(
        self, conn, material_id, group_id, po_id
    ):
        """Mirrors the dialog's save logic: seed stage=4 in temp_mat if qty_released checked."""
        self._approve_group(conn, group_id)
        pm_model.update(conn, material_id, supplier_notified=1, po_id=po_id, stage=3)

        # Simulate dialog save: user checks "qty released"
        mat = dict(pm_model.get(conn, material_id))
        grp = dict(fixture_group_model.get(conn, group_id))

        # Seed stage=4 in temp_mat as the dialog does
        temp_mat = {**mat, "stage": 4}
        computed = current_stage(temp_mat, grp)
        assert computed == 4

        pm_model.update(conn, material_id, stage=computed)
        row = dict(pm_model.get(conn, material_id))
        assert row["stage"] == 4
