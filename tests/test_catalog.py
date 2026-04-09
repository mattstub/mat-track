"""Tests for core/catalog.py — product search and usage history."""

import sqlite3
import time

from core.catalog import ProductResult, search_products
from db.models import product as product_model

# ---------------------------------------------------------------------------
# Helpers for setting up relational fixture data
# ---------------------------------------------------------------------------


def _insert_company(db: sqlite3.Connection, name: str = "Test Co") -> int:
    cur = db.execute("INSERT INTO companies (name) VALUES (?)", (name,))
    db.commit()
    return cur.lastrowid


def _insert_project(db: sqlite3.Connection, company_id: int, name: str = "Test Project") -> int:
    cur = db.execute(
        "INSERT INTO projects (company_id, name) VALUES (?, ?)",
        (company_id, name),
    )
    db.commit()
    return cur.lastrowid


def _insert_submittal_package(
    db: sqlite3.Connection, project_id: int, number: str = "SP-001"
) -> int:
    cur = db.execute(
        "INSERT INTO submittal_packages (project_id, submittal_number) VALUES (?, ?)",
        (project_id, number),
    )
    db.commit()
    return cur.lastrowid


def _insert_fixture_group(
    db: sqlite3.Connection, submittal_package_id: int, tag: str = "FG-A"
) -> int:
    cur = db.execute(
        "INSERT INTO fixture_groups"
        " (submittal_package_id, tag_designation, description) VALUES (?, ?, ?)",
        (submittal_package_id, tag, "Test fixture group"),
    )
    db.commit()
    return cur.lastrowid


def _insert_project_material(
    db: sqlite3.Connection,
    fixture_group_id: int,
    product_id: int,
    project_id: int,
) -> int:
    cur = db.execute(
        "INSERT INTO project_materials (fixture_group_id, product_id, project_id) VALUES (?, ?, ?)",
        (fixture_group_id, product_id, project_id),
    )
    db.commit()
    return cur.lastrowid


def _make_product(db: sqlite3.Connection, **overrides) -> int:
    defaults = dict(manufacturer="Acme", model_number="XR-100", description="Widget")
    defaults.update(overrides)
    return product_model.create(db, **defaults)


# ---------------------------------------------------------------------------
# Empty DB
# ---------------------------------------------------------------------------


class TestSearchProductsEmptyDB:
    def test_empty_db_returns_empty_list(self, db: sqlite3.Connection) -> None:
        results = search_products(db, "anything")
        assert results == []


# ---------------------------------------------------------------------------
# Blank / empty query returns all products
# ---------------------------------------------------------------------------


class TestSearchProductsBlankQuery:
    def test_blank_query_returns_all_products(self, db: sqlite3.Connection) -> None:
        _make_product(db, manufacturer="Alpha", model_number="A-1", description="Alpha widget")
        _make_product(db, manufacturer="Beta", model_number="B-2", description="Beta widget")
        results = search_products(db, "")
        assert len(results) == 2

    def test_whitespace_only_query_returns_all_products(self, db: sqlite3.Connection) -> None:
        _make_product(db, manufacturer="Gamma", model_number="G-3", description="Gamma widget")
        results = search_products(db, "   ")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Matching on different fields
# ---------------------------------------------------------------------------


class TestSearchProductsFieldMatching:
    def test_query_matching_manufacturer(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db, manufacturer="LiteCo", model_number="L-1", description="LED")
        _make_product(db, manufacturer="DarkCo", model_number="D-1", description="Halogen")
        results = search_products(db, "LiteCo")
        assert len(results) == 1
        assert results[0].id == pid

    def test_query_matching_model_number(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db, manufacturer="Acme", model_number="XZ-999", description="Special")
        _make_product(db, manufacturer="Acme", model_number="AB-001", description="Normal")
        results = search_products(db, "XZ-999")
        assert len(results) == 1
        assert results[0].id == pid

    def test_query_matching_description(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db, manufacturer="Acme", model_number="Z-1", description="Brass")
        _make_product(db, manufacturer="Acme", model_number="Z-2", description="Ceiling")
        results = search_products(db, "Brass")
        assert len(results) == 1
        assert results[0].id == pid

    def test_query_with_no_match_returns_empty_list(self, db: sqlite3.Connection) -> None:
        _make_product(db, manufacturer="Acme", model_number="A-1", description="Widget")
        results = search_products(db, "zzznomatch999")
        assert results == []

    def test_query_is_case_insensitive(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db, manufacturer="LiteCo", model_number="L-1", description="LED")
        results = search_products(db, "liteco")
        assert len(results) == 1
        assert results[0].id == pid


# ---------------------------------------------------------------------------
# usage_count
# ---------------------------------------------------------------------------


class TestSearchProductsUsageCount:
    def test_usage_count_zero_for_product_with_no_project_materials(
        self, db: sqlite3.Connection
    ) -> None:
        _make_product(db)
        results = search_products(db, "")
        assert len(results) == 1
        assert results[0].usage_count == 0

    def test_usage_count_correct_when_project_materials_exist(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db, manufacturer="Acme", model_number="A-1", description="Widget")
        company_id = _insert_company(db)
        project_id = _insert_project(db, company_id)
        sp_id = _insert_submittal_package(db, project_id)
        fg_id1 = _insert_fixture_group(db, sp_id, tag="FG-1")
        fg_id2 = _insert_fixture_group(db, sp_id, tag="FG-2")
        _insert_project_material(db, fg_id1, pid, project_id)
        _insert_project_material(db, fg_id2, pid, project_id)

        results = search_products(db, "")
        assert len(results) == 1
        assert results[0].usage_count == 2


# ---------------------------------------------------------------------------
# last_project_name
# ---------------------------------------------------------------------------


class TestSearchProductsLastProjectName:
    def test_last_project_name_is_none_when_no_project_materials(
        self, db: sqlite3.Connection
    ) -> None:
        _make_product(db)
        results = search_products(db, "")
        assert len(results) == 1
        assert results[0].last_project_name is None

    def test_last_project_name_populated_when_project_material_exists(
        self, db: sqlite3.Connection
    ) -> None:
        pid = _make_product(db, manufacturer="Acme", model_number="A-1", description="Widget")
        company_id = _insert_company(db)
        project_id = _insert_project(db, company_id, name="Sunrise Tower")
        sp_id = _insert_submittal_package(db, project_id)
        fg_id = _insert_fixture_group(db, sp_id)
        _insert_project_material(db, fg_id, pid, project_id)

        results = search_products(db, "")
        assert len(results) == 1
        assert results[0].last_project_name == "Sunrise Tower"


# ---------------------------------------------------------------------------
# Ordering by last_used_at DESC
# ---------------------------------------------------------------------------


class TestSearchProductsOrdering:
    def test_results_ordered_by_last_used_at_desc(self, db: sqlite3.Connection) -> None:
        # Create product A first, then B after a delay so B has a later last_used_at
        pid_a = _make_product(db, manufacturer="AlphaA", model_number="AA-1", description="First")
        time.sleep(1.1)
        pid_b = _make_product(db, manufacturer="BetaB", model_number="BB-2", description="Second")

        results = search_products(db, "")
        assert len(results) == 2
        # Most recently used first → B before A
        assert results[0].id == pid_b
        assert results[1].id == pid_a


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


class TestSearchProductsReturnType:
    def test_returns_list_of_product_result_instances(self, db: sqlite3.Connection) -> None:
        _make_product(db)
        results = search_products(db, "")
        assert isinstance(results, list)
        assert all(isinstance(r, ProductResult) for r in results)
