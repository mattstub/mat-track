"""Unit tests for Phase 1 DB layer: company model, project model, and seed."""

import sqlite3

import pytest

from db.models import company as company_model
from db.models import project as project_model
from db.seed import seed

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_company(conn, *, name="Acme Corp", short_name="Acme", **extra):
    """Insert a company and return its id."""
    return company_model.create(conn, name=name, short_name=short_name, **extra)


def make_project(conn, company_id, *, name="Project Alpha", project_number="001", **extra):
    """Insert a project under the given company and return its id."""
    return project_model.create(
        conn,
        company_id=company_id,
        name=name,
        project_number=project_number,
        **extra,
    )


# ===========================================================================
# company model
# ===========================================================================

class TestCompanyCreate:
    def test_returns_int_id(self, db):
        cid = make_company(db)
        assert isinstance(cid, int)
        assert cid > 0

    def test_id_increments(self, db):
        cid1 = make_company(db, name="Alpha")
        cid2 = make_company(db, name="Beta")
        assert cid2 > cid1


class TestCompanyGet:
    def test_returns_correct_row(self, db):
        cid = make_company(db, name="Zeta Corp", short_name="Zeta", phone="555-0000")
        row = company_model.get(db, cid)
        assert row is not None
        assert row["id"] == cid
        assert row["name"] == "Zeta Corp"
        assert row["short_name"] == "Zeta"
        assert row["phone"] == "555-0000"

    def test_returns_none_for_missing_id(self, db):
        row = company_model.get(db, 9999)
        assert row is None


class TestCompanyListAll:
    def test_returns_all_companies(self, db):
        make_company(db, name="Charlie")
        make_company(db, name="Alpha")
        make_company(db, name="Bravo")
        rows = company_model.list_all(db)
        assert len(rows) == 3

    def test_ordered_by_name(self, db):
        make_company(db, name="Charlie")
        make_company(db, name="Alpha")
        make_company(db, name="Bravo")
        rows = company_model.list_all(db)
        names = [r["name"] for r in rows]
        assert names == sorted(names)

    def test_empty_when_no_companies(self, db):
        assert company_model.list_all(db) == []


class TestCompanyUpdate:
    def test_changes_specified_field(self, db):
        cid = make_company(db, name="Old Name", short_name="Old", phone="111-1111")
        company_model.update(db, cid, name="New Name")
        row = company_model.get(db, cid)
        assert row["name"] == "New Name"

    def test_other_fields_unchanged(self, db):
        cid = make_company(db, name="Original", short_name="Orig", phone="222-2222")
        company_model.update(db, cid, name="Changed")
        row = company_model.get(db, cid)
        assert row["short_name"] == "Orig"
        assert row["phone"] == "222-2222"

    def test_update_multiple_fields(self, db):
        cid = make_company(db, name="Corp", short_name="C", phone="000-0000")
        company_model.update(db, cid, name="Corp Updated", phone="999-9999")
        row = company_model.get(db, cid)
        assert row["name"] == "Corp Updated"
        assert row["phone"] == "999-9999"
        assert row["short_name"] == "C"  # unchanged

    def test_no_fields_is_noop(self, db):
        cid = make_company(db, name="Stable")
        company_model.update(db, cid)  # no fields — should not raise
        row = company_model.get(db, cid)
        assert row["name"] == "Stable"


class TestCompanyDelete:
    def test_removes_row(self, db):
        cid = make_company(db)
        company_model.delete(db, cid)
        assert company_model.get(db, cid) is None

    def test_other_rows_unaffected(self, db):
        cid1 = make_company(db, name="Keep Me")
        cid2 = make_company(db, name="Delete Me")
        company_model.delete(db, cid2)
        assert company_model.get(db, cid1) is not None
        assert company_model.get(db, cid2) is None


# ===========================================================================
# project model
# ===========================================================================

class TestProjectCreate:
    def test_returns_int_id(self, db):
        cid = make_company(db)
        pid = make_project(db, cid)
        assert isinstance(pid, int)
        assert pid > 0

    def test_valid_company_id_succeeds(self, db):
        cid = make_company(db)
        pid = make_project(db, cid, name="Valid Project")
        row = project_model.get(db, pid)
        assert row is not None
        assert row["name"] == "Valid Project"
        assert row["company_id"] == cid

    def test_invalid_company_id_raises_integrity_error(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            project_model.create(
                db,
                company_id=99999,  # does not exist
                name="Orphan Project",
                project_number="X01",
            )


class TestProjectGet:
    def test_returns_correct_row(self, db):
        cid = make_company(db)
        pid = make_project(
            db, cid, name="Beta Project", project_number="B42", gc_name="Builder Inc"
        )
        row = project_model.get(db, pid)
        assert row is not None
        assert row["id"] == pid
        assert row["name"] == "Beta Project"
        assert row["project_number"] == "B42"
        assert row["gc_name"] == "Builder Inc"
        assert row["company_id"] == cid

    def test_returns_none_for_missing_id(self, db):
        row = project_model.get(db, 9999)
        assert row is None


class TestProjectListAll:
    def test_returns_all_projects_no_filter(self, db):
        cid1 = make_company(db, name="Co One")
        cid2 = make_company(db, name="Co Two")
        make_project(db, cid1, name="Project A")
        make_project(db, cid2, name="Project B")
        make_project(db, cid1, name="Project C")
        rows = project_model.list_all(db)
        assert len(rows) == 3

    def test_no_filter_ordered_by_name(self, db):
        cid = make_company(db)
        make_project(db, cid, name="Zebra")
        make_project(db, cid, name="Apple")
        make_project(db, cid, name="Mango")
        rows = project_model.list_all(db)
        names = [r["name"] for r in rows]
        assert names == sorted(names)

    def test_filter_by_company_id_returns_only_that_companys_projects(self, db):
        cid1 = make_company(db, name="Firm A")
        cid2 = make_company(db, name="Firm B")
        make_project(db, cid1, name="A Project 1")
        make_project(db, cid1, name="A Project 2")
        make_project(db, cid2, name="B Project 1")
        rows = project_model.list_all(db, company_id=cid1)
        assert len(rows) == 2
        assert all(r["company_id"] == cid1 for r in rows)

    def test_filter_returns_empty_when_no_match(self, db):
        cid = make_company(db)
        rows = project_model.list_all(db, company_id=cid)
        assert rows == []

    def test_empty_when_no_projects(self, db):
        assert project_model.list_all(db) == []


class TestProjectUpdate:
    def test_changes_specified_field(self, db):
        cid = make_company(db)
        pid = make_project(db, cid, name="Old Name", gc_name="Old GC")
        project_model.update(db, pid, name="New Name")
        row = project_model.get(db, pid)
        assert row["name"] == "New Name"

    def test_other_fields_unchanged(self, db):
        cid = make_company(db)
        pid = make_project(
            db, cid, name="Stable", project_number="S01", gc_name="GC Corp"
        )
        project_model.update(db, pid, name="Changed Name")
        row = project_model.get(db, pid)
        assert row["project_number"] == "S01"
        assert row["gc_name"] == "GC Corp"
        assert row["company_id"] == cid

    def test_update_multiple_fields(self, db):
        cid = make_company(db)
        pid = make_project(db, cid, name="Multi", project_number="M01", status="Active")
        project_model.update(db, pid, name="Multi Updated", status="Closed")
        row = project_model.get(db, pid)
        assert row["name"] == "Multi Updated"
        assert row["status"] == "Closed"
        assert row["project_number"] == "M01"

    def test_no_fields_is_noop(self, db):
        cid = make_company(db)
        pid = make_project(db, cid, name="Unchanged")
        project_model.update(db, pid)
        row = project_model.get(db, pid)
        assert row["name"] == "Unchanged"


class TestProjectDelete:
    def test_removes_row(self, db):
        cid = make_company(db)
        pid = make_project(db, cid)
        project_model.delete(db, pid)
        assert project_model.get(db, pid) is None

    def test_other_rows_unaffected(self, db):
        cid = make_company(db)
        pid1 = make_project(db, cid, name="Keep")
        pid2 = make_project(db, cid, name="Remove")
        project_model.delete(db, pid2)
        assert project_model.get(db, pid1) is not None
        assert project_model.get(db, pid2) is None


# ===========================================================================
# seed
# ===========================================================================

class TestSeed:
    def test_seed_inserts_two_companies(self, db):
        seed(db)
        companies = company_model.list_all(db)
        assert len(companies) == 2

    def test_seed_inserts_one_project(self, db):
        seed(db)
        projects = project_model.list_all(db)
        assert len(projects) == 1

    def test_seed_company_names(self, db):
        seed(db)
        names = {r["name"] for r in company_model.list_all(db)}
        assert "Matthews Plumbing & Utilities" in names
        assert "Utility Co" in names

    def test_seed_project_name(self, db):
        seed(db)
        projects = project_model.list_all(db)
        assert projects[0]["name"] == "Wings Residence 001"

    def test_seed_is_idempotent_companies(self, db):
        seed(db)
        seed(db)  # second call should be a no-op
        companies = company_model.list_all(db)
        assert len(companies) == 2

    def test_seed_is_idempotent_projects(self, db):
        seed(db)
        seed(db)
        projects = project_model.list_all(db)
        assert len(projects) == 1

    def test_seed_project_linked_to_mpu(self, db):
        seed(db)
        companies = {r["name"]: r["id"] for r in company_model.list_all(db)}
        mpu_id = companies["Matthews Plumbing & Utilities"]
        projects = project_model.list_all(db, company_id=mpu_id)
        assert len(projects) == 1
        assert projects[0]["name"] == "Wings Residence 001"

    def test_seed_utility_co_has_no_projects(self, db):
        seed(db)
        companies = {r["name"]: r["id"] for r in company_model.list_all(db)}
        utility_id = companies["Utility Co"]
        projects = project_model.list_all(db, company_id=utility_id)
        assert len(projects) == 0
