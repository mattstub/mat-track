"""Center panel — submittal packages for the selected project."""

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core import document_builder
from db.models import fixture_group as fixture_group_model
from db.models import project as project_model
from db.models import project_material as project_material_model
from db.models import submittal_package as submittal_package_model
from ui.dialogs.add_material import AddMaterialDialog
from ui.dialogs.lifecycle_edit import LifecycleEditDialog
from ui.dialogs.new_fixture_group import NewFixtureGroupDialog
from ui.dialogs.new_submittal_package import NewSubmittalPackageDialog
from ui.widgets.stage_indicator import StageIndicator

# Column indices
COL_TITLE = 0
COL_STATUS = 1
COL_STAGE = 2
COL_QTY = 3


class SubmittalPanel(QWidget):
    """Center panel showing submittal packages for the selected project.

    Signals:
        package_selected(int): Emitted with package_id when a package row is selected.
        fixture_group_selected(int): Emitted with group_id when a fixture group row is selected.
    """

    package_selected = Signal(int)
    fixture_group_selected = Signal(int)

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._project_id: int | None = None
        self._project_number: str = ""
        self._selected_package_id: int | None = None
        self._selected_group_id: int | None = None
        self._selected_material_id: int | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(4)

        # --- Toolbar row ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._btn_new_package = QPushButton("+ Submittal Package")
        self._btn_new_package.clicked.connect(self._on_new_package)
        toolbar.addWidget(self._btn_new_package)

        self._btn_new_group = QPushButton("+ Fixture Group")
        self._btn_new_group.setEnabled(False)
        self._btn_new_group.clicked.connect(self._on_new_group)
        toolbar.addWidget(self._btn_new_group)

        self._btn_add_material = QPushButton("+ Material")
        self._btn_add_material.setEnabled(False)
        self._btn_add_material.clicked.connect(self._on_add_material)
        toolbar.addWidget(self._btn_add_material)

        self._btn_edit_stages = QPushButton("Edit Stages")
        self._btn_edit_stages.setEnabled(False)
        self._btn_edit_stages.clicked.connect(self._on_edit_stages)
        toolbar.addWidget(self._btn_edit_stages)

        toolbar.addStretch()

        self._btn_generate_pdf = QPushButton("Generate Submittal PDF")
        self._btn_generate_pdf.setEnabled(False)
        self._btn_generate_pdf.clicked.connect(self._on_generate_pdf)
        toolbar.addWidget(self._btn_generate_pdf)

        layout.addLayout(toolbar)

        # --- Tree widget ---
        self._tree = QTreeWidget()
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(["Tag / Title", "Status", "Stage", "Qty"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setUniformRowHeights(False)

        header = self._tree.header()
        header.setSectionResizeMode(COL_TITLE, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_STAGE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_QTY, QHeaderView.ResizeToContents)

        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._tree, stretch=1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_project(self, project_id: int) -> None:
        """Load all submittal packages (and their children) for the given project."""
        self._project_id = project_id
        self._selected_package_id = None
        self._selected_group_id = None
        self._selected_material_id = None
        self._btn_new_group.setEnabled(False)
        self._btn_add_material.setEnabled(False)
        self._btn_edit_stages.setEnabled(False)

        # Resolve project_number for submittal-number suggestions
        try:
            proj = project_model.get(self.conn, project_id)
            self._project_number = (proj["project_number"] or "") if proj else ""
        except Exception:
            self._project_number = ""

        self._populate_tree()

    def refresh(self) -> None:
        """Re-run load_project with the current project_id."""
        if self._project_id is not None:
            self.load_project(self._project_id)

    # ------------------------------------------------------------------
    # Tree population
    # ------------------------------------------------------------------

    def _populate_tree(self) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()

        if self._project_id is None:
            self._tree.blockSignals(False)
            return

        try:
            packages = submittal_package_model.list_for_project(self.conn, self._project_id)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load packages:\n{exc}")
            self._tree.blockSignals(False)
            return

        for pkg in packages:
            pkg_item = self._make_package_item(pkg)
            self._tree.addTopLevelItem(pkg_item)

            try:
                groups = fixture_group_model.list_for_package(self.conn, pkg["id"])
            except Exception as exc:
                QMessageBox.critical(
                    self, "Database Error", f"Could not load fixture groups:\n{exc}"
                )
                groups = []

            for grp in groups:
                grp_item = self._make_group_item(grp)
                pkg_item.addChild(grp_item)

                try:
                    materials = project_material_model.list_for_fixture_group(self.conn, grp["id"])
                except Exception as exc:
                    QMessageBox.critical(
                        self, "Database Error", f"Could not load materials:\n{exc}"
                    )
                    materials = []

                for mat in materials:
                    mat_item = self._make_material_item(mat, grp)
                    grp_item.addChild(mat_item)

                    # Embed StageIndicator via setItemWidget
                    indicator = StageIndicator()
                    indicator.load_from_material(mat, grp)
                    self._tree.setItemWidget(mat_item, COL_STAGE, indicator)

        self._tree.expandAll()
        self._tree.blockSignals(False)

    def _make_package_item(self, pkg) -> QTreeWidgetItem:
        number = pkg["submittal_number"] or ""
        title = pkg["title"] or ""
        label = f"{number}  {title}".strip() if title else number
        status = pkg["status"] or ""

        item = QTreeWidgetItem([label, status, "—", "—"])
        item.setData(COL_TITLE, Qt.UserRole, ("package", pkg["id"]))
        return item

    def _make_group_item(self, grp) -> QTreeWidgetItem:
        tag = grp["tag_designation"] or ""
        desc = grp["description"] or ""
        label = f"{tag}  {desc}".strip() if desc else tag
        review_status = grp["review_status"] or ""
        qty = str(grp["quantity"]) if grp["quantity"] is not None else "—"

        item = QTreeWidgetItem([label, review_status, "—", qty])
        item.setData(COL_TITLE, Qt.UserRole, ("group", grp["id"]))
        return item

    def _make_material_item(self, mat, grp) -> QTreeWidgetItem:
        # Prefer explicit line_description; fall back to joined product info
        label = mat["line_description"] or ""
        if not label:
            mfr = mat["product_manufacturer"] or ""
            model = mat["product_model_number"] or ""
            desc = mat["product_description"] or ""
            label = f"{mfr} {model} — {desc}".strip(" —") if (mfr or model) else desc
        qty = str(mat["quantity"]) if mat["quantity"] is not None else "—"

        item = QTreeWidgetItem([label, "—", "", qty])
        item.setData(COL_TITLE, Qt.UserRole, ("material", mat["id"]))
        return item

    # ------------------------------------------------------------------
    # Selection handling
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        selected = self._tree.selectedItems()
        if not selected:
            self._selected_package_id = None
            self._selected_group_id = None
            self._selected_material_id = None
            self._btn_new_group.setEnabled(False)
            self._btn_add_material.setEnabled(False)
            self._btn_edit_stages.setEnabled(False)
            self._btn_generate_pdf.setEnabled(False)
            return

        item = selected[0]
        kind, row_id = item.data(COL_TITLE, Qt.UserRole)

        if kind == "package":
            self._selected_package_id = row_id
            self._selected_group_id = None
            self._selected_material_id = None
            self._btn_new_group.setEnabled(True)
            self._btn_add_material.setEnabled(False)
            self._btn_edit_stages.setEnabled(False)
            self._btn_generate_pdf.setEnabled(True)
            self.package_selected.emit(row_id)

        elif kind == "group":
            parent_item = item.parent()
            if parent_item:
                _, pkg_id = parent_item.data(COL_TITLE, Qt.UserRole)
                self._selected_package_id = pkg_id
            self._selected_group_id = row_id
            self._selected_material_id = None
            self._btn_new_group.setEnabled(True)
            self._btn_add_material.setEnabled(True)
            self._btn_edit_stages.setEnabled(False)
            self._btn_generate_pdf.setEnabled(True)
            self.fixture_group_selected.emit(row_id)

        elif kind == "material":
            group_item = item.parent()
            if group_item:
                _, grp_id = group_item.data(COL_TITLE, Qt.UserRole)
                self._selected_group_id = grp_id
                pkg_item = group_item.parent()
                if pkg_item:
                    _, pkg_id = pkg_item.data(COL_TITLE, Qt.UserRole)
                    self._selected_package_id = pkg_id
            self._selected_material_id = row_id
            self._btn_new_group.setEnabled(True)
            self._btn_add_material.setEnabled(True)
            self._btn_edit_stages.setEnabled(True)
            self._btn_generate_pdf.setEnabled(True)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_new_package(self) -> None:
        if self._project_id is None:
            QMessageBox.information(self, "No Project", "Please select a project first.")
            return

        # Check for open Revise & Resubmit on each unique spec section
        # We don't know the spec section yet, so we check after the dialog's spec section
        # field is available. Per spec: check before opening the dialog using the
        # spec sections that already exist in the project.
        #
        # Implementation: gather all distinct spec sections already in this project,
        # check each for an open R&R, and if found, prompt the user.
        try:
            existing = submittal_package_model.list_for_project(self.conn, self._project_id)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not check packages:\n{exc}")
            return

        # Collect unique spec sections that have an open R&R
        seen: set[str] = set()
        for pkg in existing:
            sec = pkg["spec_section"]
            if sec and sec not in seen:
                seen.add(sec)
                try:
                    rr = submittal_package_model.has_open_revise_and_resubmit(
                        self.conn, self._project_id, sec
                    )
                except Exception:
                    rr = None
                if rr:
                    answer = QMessageBox.question(
                        self,
                        "Open Revise & Resubmit",
                        f"Spec section {sec} has an open Revise & Resubmit — "
                        f"create Revision 1 instead?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if answer == QMessageBox.Yes:
                        QMessageBox.information(
                            self,
                            "Revision Workflow",
                            "Revision workflow coming in Phase 6.",
                        )
                        return
                    # No → fall through and open the new package dialog

        dlg = NewSubmittalPackageDialog(
            self.conn,
            self._project_id,
            self._project_number,
            parent=self,
        )
        if dlg.exec():
            self.refresh()

    def _on_new_group(self) -> None:
        if self._selected_package_id is None:
            QMessageBox.information(
                self, "No Package Selected", "Please select a submittal package first."
            )
            return

        dlg = NewFixtureGroupDialog(self.conn, self._selected_package_id, parent=self)
        if dlg.exec():
            self.refresh()

    def _on_add_material(self) -> None:
        if self._selected_group_id is None:
            QMessageBox.information(
                self, "No Fixture Group Selected", "Please select a fixture group first."
            )
            return
        if self._project_id is None:
            return

        dlg = AddMaterialDialog(
            self.conn,
            fixture_group_id=self._selected_group_id,
            project_id=self._project_id,
            parent=self,
        )
        if dlg.exec():
            self.refresh()

    def _on_edit_stages(self) -> None:
        if self._selected_material_id is None:
            QMessageBox.information(
                self, "No Material Selected", "Please select a material row first."
            )
            return
        dlg = LifecycleEditDialog(self.conn, self._selected_material_id, parent=self)
        if dlg.exec():
            self.refresh()

    def _on_generate_pdf(self) -> None:
        if self._selected_package_id is None:
            QMessageBox.information(
                self, "No Package Selected", "Select a submittal package first."
            )
            return

        try:
            output_path = document_builder.build_submittal_pdf(self.conn, self._selected_package_id)
            QMessageBox.information(
                self,
                "PDF Generated",
                f"Submittal PDF saved to:\n{output_path}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "PDF Error", f"Could not generate PDF:\n{exc}")
