"""Tests for core/document_builder.py and document PDF builders."""

from pathlib import Path

import pytest

from core import document_builder
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


def make_company(conn, **kw):
    return company_model.create(conn, name=kw.get("name", "Acme Corp"))


def make_project(conn, company_id, **kw):
    return project_model.create(
        conn,
        company_id=company_id,
        name=kw.get("name", "Test Project"),
        project_number=kw.get("project_number", "2512"),
        gc_name=kw.get("gc_name", "Wynn Construction"),
        architect_name=kw.get("architect_name", "Bockus Payne"),
        engineer_name=kw.get("engineer_name", "MEP Engineers"),
        location=kw.get("location", "Oklahoma City, OK"),
    )


def make_supplier(conn, **kw):
    return supplier_model.create(
        conn,
        company_name=kw.get("company_name", "Ferguson Enterprises"),
        contact_name=kw.get("contact_name", "Jane Smith"),
    )


def make_package(conn, project_id, **kw):
    return package_model.create(
        conn,
        project_id=project_id,
        submittal_number=kw.get("submittal_number", "2512-018"),
        spec_section=kw.get("spec_section", "220000"),
        spec_section_title=kw.get("spec_section_title", "Plumbing Fixtures"),
        title=kw.get("title", "Plumbing Fixtures"),
    )


def make_fixture_group(conn, package_id, **kw):
    return fixture_group_model.create(
        conn,
        submittal_package_id=package_id,
        tag_designation=kw.get("tag_designation", "WC-1"),
        description=kw.get("description", "Water Closet"),
        quantity=kw.get("quantity", 10),
    )


def make_product(conn, **kw):
    return product_model.create(
        conn,
        manufacturer=kw.get("manufacturer", "Kohler"),
        model_number=kw.get("model_number", "K-25077"),
        description=kw.get("description", "Kingston Toilet"),
        spec_section=kw.get("spec_section", "220000"),
        cut_sheet_filename=kw.get("cut_sheet_filename"),
    )


def make_project_material(conn, fixture_group_id, product_id, project_id, **kw):
    return project_material_model.create(
        conn,
        fixture_group_id=fixture_group_id,
        product_id=product_id,
        project_id=project_id,
        quantity=kw.get("quantity", 10),
    )


def make_po(conn, project_id, supplier_id, **kw):
    return po_model.create(
        conn,
        project_id=project_id,
        supplier_id=supplier_id,
        po_number=kw.get("po_number", "PO-2512-001"),
        status="Draft",
    )


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def full_setup(db):
    """Create a complete data graph: company → project → package → group → material + PO."""
    cid = make_company(db)
    pid = make_project(db, cid)
    sid = make_supplier(db)
    pkg_id = make_package(db, pid)
    fg_id = make_fixture_group(db, pkg_id)
    prod_id = make_product(db)
    pm_id = make_project_material(db, fg_id, prod_id, pid)
    po_id = make_po(db, pid, sid)
    po_model.add_line_item(
        db, purchase_order_id=po_id, project_material_id=pm_id, qty_ordered=10, unit_price=250.00
    )
    project_material_model.update(db, pm_id, po_id=po_id)
    return {
        "company_id": cid,
        "project_id": pid,
        "supplier_id": sid,
        "package_id": pkg_id,
        "fixture_group_id": fg_id,
        "product_id": prod_id,
        "project_material_id": pm_id,
        "po_id": po_id,
    }


# ===========================================================================
# _assemble_submittal_data
# ===========================================================================


class TestAssembleSubmittalData:
    def test_raises_for_missing_package(self, db):
        with pytest.raises(ValueError, match="not found"):
            document_builder._assemble_submittal_data(db, 9999)

    def test_returns_package(self, db, full_setup):
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        assert data["package"]["submittal_number"] == "2512-018"

    def test_returns_project(self, db, full_setup):
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        assert data["project"]["name"] == "Test Project"
        assert data["project"]["gc_name"] == "Wynn Construction"

    def test_returns_company(self, db, full_setup):
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        assert data["company"]["name"] == "Acme Corp"

    def test_fixture_groups_present(self, db, full_setup):
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        assert len(data["fixture_groups"]) == 1
        assert data["fixture_groups"][0]["tag_designation"] == "WC-1"

    def test_materials_nested_in_group(self, db, full_setup):
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        mats = data["fixture_groups"][0]["materials"]
        assert len(mats) == 1
        assert mats[0]["product_manufacturer"] == "Kohler"
        assert mats[0]["product_model_number"] == "K-25077"

    def test_cut_sheet_filename_none_by_default(self, db, full_setup):
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        mat = data["fixture_groups"][0]["materials"][0]
        assert mat["cut_sheet_filename"] is None

    def test_cut_sheet_filename_populated_when_set(self, db, full_setup):
        product_model.update(db, full_setup["product_id"], cut_sheet_filename="kohler_k25077.pdf")
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        mat = data["fixture_groups"][0]["materials"][0]
        assert mat["cut_sheet_filename"] == "kohler_k25077.pdf"

    def test_spec_section_populated_from_product(self, db, full_setup):
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        mat = data["fixture_groups"][0]["materials"][0]
        assert mat["spec_section"] == "220000"

    def test_assets_and_cut_sheets_dirs_are_paths(self, db, full_setup):
        data = document_builder._assemble_submittal_data(db, full_setup["package_id"])
        assert isinstance(data["assets_dir"], Path)
        assert isinstance(data["cut_sheets_dir"], Path)

    def test_empty_package_has_no_groups(self, db):
        cid = make_company(db)
        pid = make_project(db, cid)
        pkg_id = make_package(db, pid)
        data = document_builder._assemble_submittal_data(db, pkg_id)
        assert data["fixture_groups"] == []


# ===========================================================================
# _assemble_po_data
# ===========================================================================


class TestAssemblePOData:
    def test_raises_for_missing_po(self, db):
        with pytest.raises(ValueError, match="not found"):
            document_builder._assemble_po_data(db, 9999)

    def test_returns_po(self, db, full_setup):
        data = document_builder._assemble_po_data(db, full_setup["po_id"])
        assert data["po"]["po_number"] == "PO-2512-001"

    def test_returns_supplier(self, db, full_setup):
        data = document_builder._assemble_po_data(db, full_setup["po_id"])
        assert data["supplier"]["company_name"] == "Ferguson Enterprises"
        assert data["supplier"]["contact_name"] == "Jane Smith"

    def test_returns_project(self, db, full_setup):
        data = document_builder._assemble_po_data(db, full_setup["po_id"])
        assert data["project"]["name"] == "Test Project"

    def test_returns_company(self, db, full_setup):
        data = document_builder._assemble_po_data(db, full_setup["po_id"])
        assert data["company"]["name"] == "Acme Corp"

    def test_line_items_present(self, db, full_setup):
        data = document_builder._assemble_po_data(db, full_setup["po_id"])
        assert len(data["line_items"]) == 1
        li = data["line_items"][0]
        assert li["qty_ordered"] == 10
        assert abs(li["unit_price"] - 250.00) < 0.001

    def test_line_items_include_product_fields(self, db, full_setup):
        data = document_builder._assemble_po_data(db, full_setup["po_id"])
        li = data["line_items"][0]
        assert li["manufacturer"] == "Kohler"
        assert li["model_number"] == "K-25077"
        assert li["tag_designation"] == "WC-1"

    def test_empty_po_has_no_line_items(self, db, full_setup):
        cid = make_company(db, name="Other Corp")
        pid = make_project(db, cid)
        sid = make_supplier(db, company_name="Other Supplier")
        po_id = make_po(db, pid, sid, po_number="PO-EMPTY")
        data = document_builder._assemble_po_data(db, po_id)
        assert data["line_items"] == []


# ===========================================================================
# build_submittal_pdf — file output
# ===========================================================================


class TestBuildSubmittalPDF:
    def test_creates_pdf_file(self, db, full_setup, tmp_path):
        out = document_builder.build_submittal_pdf(db, full_setup["package_id"], tmp_path)
        assert out.exists()
        assert out.suffix == ".pdf"
        assert out.stat().st_size > 1000

    def test_output_filename_uses_submittal_number(self, db, full_setup, tmp_path):
        out = document_builder.build_submittal_pdf(db, full_setup["package_id"], tmp_path)
        assert "2512-018" in out.name

    def test_raises_for_missing_package(self, db, tmp_path):
        with pytest.raises(ValueError):
            document_builder.build_submittal_pdf(db, 9999, tmp_path)

    def test_package_with_no_materials_still_generates(self, db, tmp_path):
        cid = make_company(db)
        pid = make_project(db, cid)
        pkg_id = make_package(db, pid, submittal_number="2512-099")
        out = document_builder.build_submittal_pdf(db, pkg_id, tmp_path)
        assert out.exists()

    def test_creates_output_dir_if_missing(self, db, full_setup, tmp_path):
        nested = tmp_path / "subdir" / "output"
        out = document_builder.build_submittal_pdf(db, full_setup["package_id"], nested)
        assert out.exists()


# ===========================================================================
# build_po_pdf — file output
# ===========================================================================


class TestBuildPOPDF:
    def test_creates_pdf_file(self, db, full_setup, tmp_path):
        out = document_builder.build_po_pdf(db, full_setup["po_id"], tmp_path)
        assert out.exists()
        assert out.suffix == ".pdf"
        assert out.stat().st_size > 1000

    def test_output_filename_uses_po_number(self, db, full_setup, tmp_path):
        out = document_builder.build_po_pdf(db, full_setup["po_id"], tmp_path)
        assert "PO-2512-001" in out.name

    def test_field_receipt_mode_creates_different_file(self, db, full_setup, tmp_path):
        standard = document_builder.build_po_pdf(db, full_setup["po_id"], tmp_path)
        receipt = document_builder.build_po_pdf(
            db, full_setup["po_id"], tmp_path, field_receipt_mode=True
        )
        assert standard != receipt
        assert "receipt" in receipt.name
        assert receipt.exists()

    def test_raises_for_missing_po(self, db, tmp_path):
        with pytest.raises(ValueError):
            document_builder.build_po_pdf(db, 9999, tmp_path)

    def test_po_with_no_line_items_still_generates(self, db, full_setup, tmp_path):
        cid = make_company(db, name="Other Corp")
        pid = make_project(db, cid)
        sid = make_supplier(db, company_name="Other Supplier")
        po_id = make_po(db, pid, sid, po_number="PO-EMPTY")
        out = document_builder.build_po_pdf(db, po_id, tmp_path)
        assert out.exists()
