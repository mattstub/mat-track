"""Unit tests for Phase 4 DB layer: supplier model and purchase_order model."""

import sqlite3

import pytest

from db.models import company as company_model
from db.models import fixture_group as fixture_group_model
from db.models import product as product_model
from db.models import project as project_model
from db.models import project_material as project_material_model
from db.models import purchase_order as po_model
from db.models import submittal_package as package_model
from db.models import supplier as supplier_model

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_company(conn, *, name="Acme Corp", **extra):
    return company_model.create(conn, name=name, short_name="Acme", **extra)


def make_project(conn, company_id, *, name="Test Project", project_number="001", **extra):
    return project_model.create(
        conn, company_id=company_id, name=name, project_number=project_number, **extra
    )


def make_supplier(conn, *, company_name="Supply Co", **extra):
    return supplier_model.create(conn, company_name=company_name, **extra)


def make_package(conn, project_id, *, submittal_number="22-001", **extra):
    return package_model.create(
        conn, project_id=project_id, submittal_number=submittal_number, **extra
    )


def make_fixture_group(conn, package_id, *, tag_designation="FG-1", description="Group 1", **extra):
    return fixture_group_model.create(
        conn,
        submittal_package_id=package_id,
        tag_designation=tag_designation,
        description=description,
        **extra,
    )


def make_product(conn, *, manufacturer="Acme", model_number="X100", description="Widget", **extra):
    return product_model.create(
        conn,
        manufacturer=manufacturer,
        model_number=model_number,
        description=description,
        **extra,
    )


def make_project_material(conn, fixture_group_id, product_id, project_id, **extra):
    return project_material_model.create(
        conn,
        fixture_group_id=fixture_group_id,
        product_id=product_id,
        project_id=project_id,
        **extra,
    )


def make_po(conn, project_id, supplier_id, *, po_number="PO-001", **extra):
    return po_model.create(
        conn,
        project_id=project_id,
        supplier_id=supplier_id,
        po_number=po_number,
        **extra,
    )


# ---------------------------------------------------------------------------
# Shared setup fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def setup(db):
    """Create a minimal graph of records needed by PO and line-item tests."""
    cid = make_company(db)
    pid = make_project(db, cid)
    sid = make_supplier(db, company_name="Pipe World")
    pkg_id = make_package(db, pid)
    fg_id = make_fixture_group(db, pkg_id)
    prod_id = make_product(db)
    pm_id = make_project_material(db, fg_id, prod_id, pid, line_description='12" Gate Valve')
    return {
        "company_id": cid,
        "project_id": pid,
        "supplier_id": sid,
        "package_id": pkg_id,
        "fixture_group_id": fg_id,
        "product_id": prod_id,
        "project_material_id": pm_id,
    }


# ===========================================================================
# supplier model
# ===========================================================================


class TestSupplierCreate:
    def test_returns_int_id(self, db):
        sid = make_supplier(db)
        assert isinstance(sid, int)
        assert sid > 0

    def test_id_increments(self, db):
        sid1 = make_supplier(db, company_name="Alpha Supply")
        sid2 = make_supplier(db, company_name="Beta Supply")
        assert sid2 > sid1

    def test_stores_all_fields(self, db):
        sid = supplier_model.create(
            db,
            company_name="Full Fields Co",
            contact_name="Jane Doe",
            email="jane@example.com",
            phone="555-1234",
            address="123 Main St",
            notes="Reliable",
            notify_on_po=0,
            notify_on_approval=1,
        )
        row = supplier_model.get(db, sid)
        assert row["company_name"] == "Full Fields Co"
        assert row["contact_name"] == "Jane Doe"
        assert row["email"] == "jane@example.com"
        assert row["phone"] == "555-1234"
        assert row["notify_on_po"] == 0
        assert row["notify_on_approval"] == 1

    def test_invalid_column_raises(self, db):
        with pytest.raises(ValueError, match="Invalid column"):
            supplier_model.create(db, company_name="X", bogus_col="nope")


class TestSupplierGet:
    def test_returns_correct_row(self, db):
        sid = make_supplier(db, company_name="Acme Pipes", contact_name="Bob")
        row = supplier_model.get(db, sid)
        assert row is not None
        assert row["id"] == sid
        assert row["company_name"] == "Acme Pipes"
        assert row["contact_name"] == "Bob"

    def test_returns_none_for_missing_id(self, db):
        row = supplier_model.get(db, 9999)
        assert row is None


class TestSupplierGetAll:
    def test_returns_all_suppliers(self, db):
        make_supplier(db, company_name="Charlie Supply")
        make_supplier(db, company_name="Alpha Supply")
        make_supplier(db, company_name="Bravo Supply")
        rows = supplier_model.get_all(db)
        assert len(rows) == 3

    def test_ordered_by_company_name(self, db):
        make_supplier(db, company_name="Charlie Supply")
        make_supplier(db, company_name="Alpha Supply")
        make_supplier(db, company_name="Bravo Supply")
        rows = supplier_model.get_all(db)
        names = [r["company_name"] for r in rows]
        assert names == sorted(names)

    def test_empty_when_no_suppliers(self, db):
        assert supplier_model.get_all(db) == []


class TestSupplierUpdate:
    def test_changes_specified_field(self, db):
        sid = make_supplier(db, company_name="Old Name")
        supplier_model.update(db, sid, company_name="New Name")
        row = supplier_model.get(db, sid)
        assert row["company_name"] == "New Name"

    def test_other_fields_unchanged(self, db):
        sid = supplier_model.create(
            db, company_name="Stable Co", contact_name="Alice", phone="000-0000"
        )
        supplier_model.update(db, sid, company_name="Changed Co")
        row = supplier_model.get(db, sid)
        assert row["contact_name"] == "Alice"
        assert row["phone"] == "000-0000"

    def test_update_multiple_fields(self, db):
        sid = supplier_model.create(db, company_name="Multi Co", email="old@x.com", phone="111")
        supplier_model.update(db, sid, email="new@x.com", phone="999")
        row = supplier_model.get(db, sid)
        assert row["email"] == "new@x.com"
        assert row["phone"] == "999"
        assert row["company_name"] == "Multi Co"

    def test_no_fields_is_noop(self, db):
        sid = make_supplier(db, company_name="Unchanged")
        supplier_model.update(db, sid)
        row = supplier_model.get(db, sid)
        assert row["company_name"] == "Unchanged"

    def test_invalid_column_raises(self, db):
        sid = make_supplier(db)
        with pytest.raises(ValueError, match="Invalid column"):
            supplier_model.update(db, sid, bad_col="x")


class TestSupplierDelete:
    def test_removes_row(self, db):
        sid = make_supplier(db)
        supplier_model.delete(db, sid)
        assert supplier_model.get(db, sid) is None

    def test_other_rows_unaffected(self, db):
        sid1 = make_supplier(db, company_name="Keep Me")
        sid2 = make_supplier(db, company_name="Delete Me")
        supplier_model.delete(db, sid2)
        assert supplier_model.get(db, sid1) is not None
        assert supplier_model.get(db, sid2) is None


# ===========================================================================
# purchase_order model
# ===========================================================================


class TestPOCreate:
    def test_returns_int_id(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        assert isinstance(po_id, int)
        assert po_id > 0

    def test_id_increments(self, db, setup):
        po_id1 = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-001")
        po_id2 = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-002")
        assert po_id2 > po_id1

    def test_stores_all_fields(self, db, setup):
        po_id = po_model.create(
            db,
            project_id=setup["project_id"],
            supplier_id=setup["supplier_id"],
            po_number="PO-999",
            status="Issued",
            shipping_address="456 Job Site Rd",
            notes="Rush order",
        )
        row = po_model.get(db, po_id)
        assert row["po_number"] == "PO-999"
        assert row["status"] == "Issued"
        assert row["shipping_address"] == "456 Job Site Rd"
        assert row["notes"] == "Rush order"

    def test_invalid_project_raises_integrity_error(self, db, setup):
        with pytest.raises(sqlite3.IntegrityError):
            po_model.create(db, project_id=99999, supplier_id=setup["supplier_id"])

    def test_invalid_supplier_raises_integrity_error(self, db, setup):
        with pytest.raises(sqlite3.IntegrityError):
            po_model.create(db, project_id=setup["project_id"], supplier_id=99999)

    def test_invalid_column_raises(self, db, setup):
        with pytest.raises(ValueError, match="Invalid column"):
            po_model.create(
                db,
                project_id=setup["project_id"],
                supplier_id=setup["supplier_id"],
                bogus="x",
            )


class TestPOGet:
    def test_returns_correct_row(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-42")
        row = po_model.get(db, po_id)
        assert row is not None
        assert row["id"] == po_id
        assert row["po_number"] == "PO-42"
        assert row["project_id"] == setup["project_id"]
        assert row["supplier_id"] == setup["supplier_id"]

    def test_returns_none_for_missing_id(self, db):
        row = po_model.get(db, 9999)
        assert row is None


class TestPOListForProject:
    def test_returns_only_project_pos(self, db, setup):
        cid2 = make_company(db, name="Other Corp")
        pid2 = make_project(db, cid2, name="Other Project", project_number="002")
        make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-A")
        make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-B")
        make_po(db, pid2, setup["supplier_id"], po_number="PO-C")
        rows = po_model.list_for_project(db, setup["project_id"])
        assert len(rows) == 2
        assert all(r["project_id"] == setup["project_id"] for r in rows)

    def test_includes_supplier_company_name(self, db, setup):
        make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-X")
        rows = po_model.list_for_project(db, setup["project_id"])
        assert len(rows) == 1
        assert rows[0]["supplier_company_name"] == "Pipe World"

    def test_ordered_by_created_at_desc(self, db, setup):
        po_id1 = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-1")
        po_id2 = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-2")
        rows = po_model.list_for_project(db, setup["project_id"])
        # Most recently inserted should be first
        assert rows[0]["id"] == po_id2
        assert rows[1]["id"] == po_id1

    def test_empty_when_no_pos(self, db, setup):
        rows = po_model.list_for_project(db, setup["project_id"])
        assert rows == []


class TestPOListAll:
    def test_returns_all_pos(self, db, setup):
        cid2 = make_company(db, name="Firm B")
        pid2 = make_project(db, cid2, name="Project B", project_number="B01")
        make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-1")
        make_po(db, pid2, setup["supplier_id"], po_number="PO-2")
        rows = po_model.list_all(db)
        assert len(rows) == 2

    def test_includes_supplier_company_name(self, db, setup):
        make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-Y")
        rows = po_model.list_all(db)
        assert len(rows) == 1
        assert rows[0]["supplier_company_name"] == "Pipe World"

    def test_empty_when_no_pos(self, db):
        rows = po_model.list_all(db)
        assert rows == []


class TestPOUpdate:
    def test_changes_specified_field(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"], status="Draft")
        po_model.update(db, po_id, status="Issued")
        row = po_model.get(db, po_id)
        assert row["status"] == "Issued"

    def test_other_fields_unchanged(self, db, setup):
        po_id = make_po(
            db, setup["project_id"], setup["supplier_id"], po_number="PO-STABLE", status="Draft"
        )
        po_model.update(db, po_id, status="Issued")
        row = po_model.get(db, po_id)
        assert row["po_number"] == "PO-STABLE"
        assert row["project_id"] == setup["project_id"]

    def test_no_fields_is_noop(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        po_model.update(db, po_id)
        row = po_model.get(db, po_id)
        assert row is not None

    def test_invalid_column_raises(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        with pytest.raises(ValueError, match="Invalid column"):
            po_model.update(db, po_id, bad_col="x")


class TestPODelete:
    def test_removes_row(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        po_model.delete(db, po_id)
        assert po_model.get(db, po_id) is None

    def test_other_rows_unaffected(self, db, setup):
        po_id1 = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-KEEP")
        po_id2 = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-DEL")
        po_model.delete(db, po_id2)
        assert po_model.get(db, po_id1) is not None
        assert po_model.get(db, po_id2) is None


# ===========================================================================
# po_line_items
# ===========================================================================


class TestAddLineItem:
    def test_returns_int_id(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=5,
        )
        assert isinstance(li_id, int)
        assert li_id > 0

    def test_id_increments(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id1 = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=1,
        )
        li_id2 = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=2,
        )
        assert li_id2 > li_id1

    def test_stores_all_fields(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=10,
            qty_received=3,
            unit_price=49.99,
            receipt_notes="Partial delivery",
        )
        rows = po_model.list_line_items_for_po(db, po_id)
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == li_id
        assert row["qty_ordered"] == 10
        assert row["qty_received"] == 3
        assert abs(row["unit_price"] - 49.99) < 0.001
        assert row["receipt_notes"] == "Partial delivery"

    def test_invalid_column_raises(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        with pytest.raises(ValueError, match="Invalid column"):
            po_model.add_line_item(
                db,
                purchase_order_id=po_id,
                project_material_id=setup["project_material_id"],
                bogus="x",
            )


class TestListLineItemsForPO:
    def test_returns_only_pos_line_items(self, db, setup):
        po_id1 = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-1")
        po_id2 = make_po(db, setup["project_id"], setup["supplier_id"], po_number="PO-2")
        po_model.add_line_item(
            db,
            purchase_order_id=po_id1,
            project_material_id=setup["project_material_id"],
            qty_ordered=1,
        )
        po_model.add_line_item(
            db,
            purchase_order_id=po_id2,
            project_material_id=setup["project_material_id"],
            qty_ordered=2,
        )
        rows = po_model.list_line_items_for_po(db, po_id1)
        assert len(rows) == 1
        assert rows[0]["purchase_order_id"] == po_id1

    def test_includes_product_fields(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=4,
        )
        rows = po_model.list_line_items_for_po(db, po_id)
        assert len(rows) == 1
        row = rows[0]
        assert row["manufacturer"] == "Acme"
        assert row["model_number"] == "X100"
        assert row["product_description"] == "Widget"

    def test_includes_project_material_fields(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=2,
        )
        rows = po_model.list_line_items_for_po(db, po_id)
        row = rows[0]
        assert row["line_description"] == '12" Gate Valve'
        assert row["fixture_group_id"] == setup["fixture_group_id"]

    def test_includes_fixture_group_fields(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=1,
        )
        rows = po_model.list_line_items_for_po(db, po_id)
        row = rows[0]
        assert row["tag_designation"] == "FG-1"
        assert row["submittal_package_id"] == setup["package_id"]

    def test_empty_when_no_line_items(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        rows = po_model.list_line_items_for_po(db, po_id)
        assert rows == []


class TestUpdateLineItem:
    def test_changes_specified_field(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=5,
        )
        po_model.update_line_item(db, li_id, qty_ordered=10)
        rows = po_model.list_line_items_for_po(db, po_id)
        assert rows[0]["qty_ordered"] == 10

    def test_other_fields_unchanged(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=5,
            unit_price=25.00,
        )
        po_model.update_line_item(db, li_id, qty_ordered=8)
        rows = po_model.list_line_items_for_po(db, po_id)
        assert abs(rows[0]["unit_price"] - 25.00) < 0.001

    def test_no_fields_is_noop(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=3,
        )
        po_model.update_line_item(db, li_id)
        rows = po_model.list_line_items_for_po(db, po_id)
        assert rows[0]["qty_ordered"] == 3

    def test_invalid_column_raises(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
        )
        with pytest.raises(ValueError, match="Invalid column"):
            po_model.update_line_item(db, li_id, bad_col="x")


class TestDeleteLineItem:
    def test_removes_line_item(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=1,
        )
        po_model.delete_line_item(db, li_id)
        rows = po_model.list_line_items_for_po(db, po_id)
        assert rows == []

    def test_other_line_items_unaffected(self, db, setup):
        po_id = make_po(db, setup["project_id"], setup["supplier_id"])
        li_id1 = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=1,
        )
        li_id2 = po_model.add_line_item(
            db,
            purchase_order_id=po_id,
            project_material_id=setup["project_material_id"],
            qty_ordered=2,
        )
        po_model.delete_line_item(db, li_id2)
        rows = po_model.list_line_items_for_po(db, po_id)
        assert len(rows) == 1
        assert rows[0]["id"] == li_id1
