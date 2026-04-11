"""Dialog — search catalog and assign a product to a fixture group."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core import catalog
from db.models import project_material as project_material_model
from ui.widgets.search_box import SearchBox


class AddMaterialDialog(QDialog):
    """Search the catalog and assign a product to a fixture group as a project_material.

    Args:
        conn: Active SQLite connection.
        fixture_group_id: ID of the fixture group to attach the material to.
        project_id: ID of the parent project.
        parent: Optional parent widget.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        fixture_group_id: int,
        project_id: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.fixture_group_id = fixture_group_id
        self.project_id = project_id
        self._selected_product_id: int | None = None
        self.setWindowTitle("Add Material")
        self.setMinimumWidth(680)
        self.setMinimumHeight(500)
        self._build_ui()
        self._load_results("")

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Search box
        self._search = SearchBox(placeholder="Search by manufacturer, model, or description…")
        self._search.search_changed.connect(self._load_results)
        root.addWidget(self._search)

        # Results table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Manufacturer", "Model", "Description", "Spec Section", "Prior Use"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        root.addWidget(self._table, stretch=1)

        # Bottom form area
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(6)

        self._spin_qty = QSpinBox()
        self._spin_qty.setMinimum(1)
        self._spin_qty.setValue(1)
        form.addRow("Quantity", self._spin_qty)

        self._edit_line_desc = QLineEdit()
        self._edit_line_desc.setPlaceholderText(
            "Optional — overrides product description for this job"
        )
        form.addRow("Line Description", self._edit_line_desc)

        root.addLayout(form)

        # Validation label (hidden until needed)
        self._lbl_validation = QLabel("Please select a product from the list above.")
        self._lbl_validation.setStyleSheet("color: red;")
        self._lbl_validation.setVisible(False)
        root.addWidget(self._lbl_validation)

        # Buttons
        btn_box = QDialogButtonBox()
        self._btn_save = QPushButton("Save")
        self._btn_save.setDefault(True)
        btn_cancel = QPushButton("Cancel")
        btn_box.addButton(self._btn_save, QDialogButtonBox.AcceptRole)
        btn_box.addButton(btn_cancel, QDialogButtonBox.RejectRole)
        btn_box.rejected.connect(self.reject)
        self._btn_save.clicked.connect(self._on_save)
        root.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_results(self, query: str) -> None:
        try:
            results = catalog.search_products(self.conn, query)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not search catalog:\n{exc}")
            results = []

        self._results = results
        self._table.setRowCount(0)
        self._selected_product_id = None

        for row_idx, product in enumerate(results):
            self._table.insertRow(row_idx)
            prior_use = product.last_project_name or "—"

            items = [
                product.manufacturer,
                product.model_number,
                product.description,
                product.spec_section or "—",
                prior_use,
            ]
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setData(Qt.UserRole, product.id)
                self._table.setItem(row_idx, col_idx, item)

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        selected = self._table.selectedItems()
        if selected:
            self._selected_product_id = selected[0].data(Qt.UserRole)
            # Hide any validation warning once user selects something
            self._lbl_validation.setVisible(False)
            self._table.setStyleSheet("")
        else:
            self._selected_product_id = None

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        if self._selected_product_id is None:
            self._lbl_validation.setVisible(True)
            self._table.setStyleSheet("QTableWidget { border: 2px solid red; }")
            return

        # Clear any previous validation state
        self._lbl_validation.setVisible(False)
        self._table.setStyleSheet("")

        fields: dict = {
            "fixture_group_id": self.fixture_group_id,
            "product_id": self._selected_product_id,
            "project_id": self.project_id,
            "quantity": self._spin_qty.value(),
        }

        line_desc = self._edit_line_desc.text().strip()
        if line_desc:
            fields["line_description"] = line_desc

        try:
            project_material_model.create(self.conn, **fields)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not save material:\n{exc}")
            return

        self.accept()
