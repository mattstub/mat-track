"""Left panel — project list with company filter."""

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from db.models import company as company_model
from db.models import project as project_model


class ProjectPanel(QWidget):
    project_selected = Signal(int)  # emits project id

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._companies: list = []  # list of sqlite3.Row
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(4)

        lbl = QLabel("Projects")
        lbl.setAlignment(Qt.AlignLeft)
        layout.addWidget(lbl)

        # Company filter
        self._combo_company = QComboBox()
        self._combo_company.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._combo_company.currentIndexChanged.connect(self._on_company_changed)
        layout.addWidget(self._combo_company)

        # Project list
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list, stretch=1)

        # Manage Companies placeholder button
        self._btn_manage = QPushButton("Manage Companies")
        self._btn_manage.setEnabled(False)
        layout.addWidget(self._btn_manage)

        # Initial data load
        self.refresh()

    def refresh(self) -> None:
        """Reload companies and projects from the database."""
        self._reload_companies()
        self._reload_projects()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reload_companies(self) -> None:
        try:
            self._companies = company_model.list_all(self.conn)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load companies:\n{exc}")
            self._companies = []

        # Preserve current selection if possible
        current_id = self._combo_company.currentData()

        self._combo_company.blockSignals(True)
        self._combo_company.clear()
        self._combo_company.addItem("All Companies", userData=None)
        for c in self._companies:
            self._combo_company.addItem(c["name"], userData=c["id"])

        # Restore previous selection
        if current_id is not None:
            idx = self._combo_company.findData(current_id)
            if idx >= 0:
                self._combo_company.setCurrentIndex(idx)

        self._combo_company.blockSignals(False)

    def _reload_projects(self) -> None:
        company_id = self._combo_company.currentData()  # None means "All"

        try:
            projects = project_model.list_all(self.conn, company_id=company_id)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load projects:\n{exc}")
            projects = []

        self._list.clear()
        for p in projects:
            number = p["project_number"] or ""
            label = f"{number}  {p['name']}".strip() if number else p["name"]
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, p["id"])
            self._list.addItem(item)

    def _on_company_changed(self, _index: int) -> None:
        self._reload_projects()

    def _on_selection_changed(self) -> None:
        items = self._list.selectedItems()
        if items:
            project_id = items[0].data(Qt.UserRole)
            if project_id is not None:
                self.project_selected.emit(project_id)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        project_id = item.data(Qt.UserRole)
        if project_id is not None:
            self.project_selected.emit(project_id)
