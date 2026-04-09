"""Dialog — create a new project."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from db.models import company as company_model
from db.models import project as project_model


class NewProjectDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("New Project")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(6)

        # --- Project Name (required) ---
        self._lbl_name = QLabel("Project Name*")
        self._edit_name = QLineEdit()
        form.addRow(self._lbl_name, self._edit_name)

        # --- Project Number ---
        self._edit_number = QLineEdit()
        form.addRow("Project Number", self._edit_number)

        # --- Company (required) ---
        self._lbl_company = QLabel("Company*")
        self._combo_company = QComboBox()
        self._load_companies()
        form.addRow(self._lbl_company, self._combo_company)

        # --- GC Name ---
        self._edit_gc_name = QLineEdit()
        form.addRow("GC Name", self._edit_gc_name)

        # --- GC Project Number ---
        self._edit_gc_number = QLineEdit()
        form.addRow("GC Project Number", self._edit_gc_number)

        # --- Architect ---
        self._edit_architect = QLineEdit()
        form.addRow("Architect", self._edit_architect)

        # --- Engineer ---
        self._edit_engineer = QLineEdit()
        form.addRow("Engineer", self._edit_engineer)

        # --- Location ---
        self._edit_location = QLineEdit()
        form.addRow("Location", self._edit_location)

        # --- Status ---
        self._combo_status = QComboBox()
        self._combo_status.addItems(["Active", "On Hold", "Complete"])
        form.addRow("Status", self._combo_status)

        # --- Notes ---
        self._edit_notes = QTextEdit()
        self._edit_notes.setFixedHeight(62)  # ~3 lines
        form.addRow("Notes", self._edit_notes)

        root.addLayout(form)

        # --- Buttons ---
        btn_box = QDialogButtonBox()
        self._btn_save = QPushButton("Save")
        self._btn_save.setDefault(True)
        btn_cancel = QPushButton("Cancel")
        btn_box.addButton(self._btn_save, QDialogButtonBox.AcceptRole)
        btn_box.addButton(btn_cancel, QDialogButtonBox.RejectRole)
        btn_box.rejected.connect(self.reject)
        self._btn_save.clicked.connect(self._on_save)
        root.addWidget(btn_box)

    def _load_companies(self) -> None:
        self._combo_company.clear()
        self._combo_company.addItem("— select —", userData=None)
        try:
            companies = company_model.list_all(self.conn)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load companies:\n{exc}")
            return
        for c in companies:
            self._combo_company.addItem(c["name"], userData=c["id"])

    def _reset_label_colors(self) -> None:
        for lbl in (self._lbl_name, self._lbl_company):
            lbl.setStyleSheet("")

    def _mark_invalid(self, label: QLabel) -> None:
        label.setStyleSheet("color: red;")

    def _on_save(self) -> None:
        self._reset_label_colors()

        name = self._edit_name.text().strip()
        company_id = self._combo_company.currentData()

        valid = True
        if not name:
            self._mark_invalid(self._lbl_name)
            valid = False
        if company_id is None:
            self._mark_invalid(self._lbl_company)
            valid = False
        if not valid:
            return

        fields = dict(
            name=name,
            company_id=company_id,
            project_number=self._edit_number.text().strip() or None,
            gc_name=self._edit_gc_name.text().strip() or None,
            gc_project_number=self._edit_gc_number.text().strip() or None,
            architect_name=self._edit_architect.text().strip() or None,
            engineer_name=self._edit_engineer.text().strip() or None,
            location=self._edit_location.text().strip() or None,
            status=self._combo_status.currentText(),
            notes=self._edit_notes.toPlainText().strip() or None,
        )
        # Remove None values so the model's dynamic INSERT stays clean
        required = {"name", "company_id", "status"}
        fields = {k: v for k, v in fields.items() if v is not None or k in required}

        try:
            project_model.create(self.conn, **fields)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not save project:\n{exc}")
            return

        self.accept()
