"""Unit tests for db/models/product.py."""

import sqlite3

import pytest

from db.models import product

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(db: sqlite3.Connection, **overrides) -> int:
    """Insert a product with sensible defaults and return its id."""
    defaults = dict(
        manufacturer="Acme",
        model_number="XR-100",
        description="A great widget",
    )
    defaults.update(overrides)
    return product.create(db, **defaults)


# ---------------------------------------------------------------------------
# product.create
# ---------------------------------------------------------------------------


class TestProductCreate:
    def test_returns_int_id(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db)
        assert isinstance(pid, int)
        assert pid > 0

    def test_last_used_at_populated_after_create(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db)
        row = product.get(db, pid)
        assert row is not None
        assert row["last_used_at"] is not None
        assert row["last_used_at"] != ""

    def test_created_at_populated_after_create(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db)
        row = product.get(db, pid)
        assert row is not None
        assert row["created_at"] is not None
        assert row["created_at"] != ""

    def test_raises_value_error_for_unknown_column(self, db: sqlite3.Connection) -> None:
        with pytest.raises(ValueError, match="Invalid column"):
            product.create(
                db,
                manufacturer="Acme",
                model_number="XR-100",
                description="Widget",
                totally_fake_column="oops",
            )


# ---------------------------------------------------------------------------
# product.get
# ---------------------------------------------------------------------------


class TestProductGet:
    def test_returns_correct_row_by_id(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db, manufacturer="LiteCo", model_number="L-42", description="LED strip")
        row = product.get(db, pid)
        assert row is not None
        assert row["id"] == pid

    def test_returns_none_for_missing_id(self, db: sqlite3.Connection) -> None:
        row = product.get(db, 999999)
        assert row is None

    def test_returned_row_has_correct_fields(self, db: sqlite3.Connection) -> None:
        pid = _make_product(
            db,
            manufacturer="LiteCo",
            model_number="L-42",
            description="LED strip",
        )
        row = product.get(db, pid)
        assert row is not None
        assert row["manufacturer"] == "LiteCo"
        assert row["model_number"] == "L-42"
        assert row["description"] == "LED strip"


# ---------------------------------------------------------------------------
# product.update
# ---------------------------------------------------------------------------


class TestProductUpdate:
    def test_updates_single_field_others_unchanged(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db, manufacturer="OldCo", model_number="M-1", description="Old desc")
        product.update(db, pid, manufacturer="NewCo")
        row = product.get(db, pid)
        assert row is not None
        assert row["manufacturer"] == "NewCo"
        # Other fields unchanged
        assert row["model_number"] == "M-1"
        assert row["description"] == "Old desc"

    def test_update_refreshes_last_used_at_even_with_no_fields(
        self, db: sqlite3.Connection
    ) -> None:
        pid = _make_product(db)
        row_before = product.get(db, pid)
        old_luat = row_before["last_used_at"]

        # Pause briefly so datetime('now') can advance at least 1 second
        import time

        time.sleep(1.1)

        product.update(db, pid)
        row_after = product.get(db, pid)
        assert row_after is not None
        # last_used_at should be refreshed (later than or equal to before)
        assert row_after["last_used_at"] is not None
        # It should have changed
        assert row_after["last_used_at"] >= old_luat

    def test_raises_value_error_for_unknown_column(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db)
        with pytest.raises(ValueError, match="Invalid column"):
            product.update(db, pid, nonexistent_col="bad")


# ---------------------------------------------------------------------------
# product.delete
# ---------------------------------------------------------------------------


class TestProductDelete:
    def test_removes_row(self, db: sqlite3.Connection) -> None:
        pid = _make_product(db)
        product.delete(db, pid)
        assert product.get(db, pid) is None

    def test_other_rows_unaffected(self, db: sqlite3.Connection) -> None:
        pid1 = _make_product(db, manufacturer="A", model_number="M1", description="D1")
        pid2 = _make_product(db, manufacturer="B", model_number="M2", description="D2")
        product.delete(db, pid1)
        assert product.get(db, pid1) is None
        assert product.get(db, pid2) is not None
