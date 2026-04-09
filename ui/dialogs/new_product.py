"""Dialog — add a new product to the catalog (or view an existing one)."""

import re
import shutil
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from db.models import product as product_model

# Destination directory for imported cut sheets, relative to the repo root.
_CUT_SHEETS_DIR = Path(__file__).parent.parent.parent / "data" / "cut_sheets"


def _sanitize_filename(manufacturer: str, model_number: str) -> str:
    """Build a safe PDF filename from manufacturer and model number.

    Strips everything except ASCII alphanumerics and underscores, then removes
    any leading dots so the result can never be an empty string, a dot-file,
    or a path traversal component.
    """
    raw = f"{manufacturer}_{model_number}".lower().replace(" ", "_")
    # ASCII-only: exclude Unicode word chars by using re.ASCII flag.
    sanitized = re.sub(r"[^\w]", "", raw, flags=re.ASCII)
    sanitized = sanitized.lstrip("_") or "unnamed"
    return f"{sanitized}.pdf"


class NewProductDialog(QDialog):
    def __init__(
        self,
        conn: sqlite3.Connection,
        product_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self._product_id = product_id
        self._cut_sheet_filename: str | None = None  # stores filename only

        read_only = product_id is not None
        self.setWindowTitle("View Product" if read_only else "New Product")
        self.setMinimumWidth(480)
        self._build_ui(read_only)

        if read_only:
            self._load_product(product_id)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, read_only: bool) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(6)

        # --- Manufacturer (required) ---
        self._lbl_manufacturer = QLabel("Manufacturer*")
        self._edit_manufacturer = QLineEdit()
        self._edit_manufacturer.setReadOnly(read_only)
        form.addRow(self._lbl_manufacturer, self._edit_manufacturer)

        # --- Model Number (required) ---
        self._lbl_model_number = QLabel("Model Number*")
        self._edit_model_number = QLineEdit()
        self._edit_model_number.setReadOnly(read_only)
        form.addRow(self._lbl_model_number, self._edit_model_number)

        # --- Description (required) ---
        self._lbl_description = QLabel("Description*")
        self._edit_description = QLineEdit()
        self._edit_description.setReadOnly(read_only)
        form.addRow(self._lbl_description, self._edit_description)

        # --- Spec Section ---
        self._edit_spec_section = QLineEdit()
        self._edit_spec_section.setPlaceholderText("e.g. 220000")
        self._edit_spec_section.setReadOnly(read_only)
        form.addRow("Spec Section", self._edit_spec_section)

        # --- Spec Section Title ---
        self._edit_spec_section_title = QLineEdit()
        self._edit_spec_section_title.setPlaceholderText("e.g. Plumbing Fixtures")
        self._edit_spec_section_title.setReadOnly(read_only)
        form.addRow("Spec Section Title", self._edit_spec_section_title)

        # --- Product URL ---
        self._edit_product_url = QLineEdit()
        self._edit_product_url.setReadOnly(read_only)
        form.addRow("Product URL", self._edit_product_url)

        # --- Submittal Notes ---
        self._edit_submittal_notes = QTextEdit()
        self._edit_submittal_notes.setFixedHeight(62)  # ~3 lines
        self._edit_submittal_notes.setReadOnly(read_only)
        form.addRow("Submittal Notes", self._edit_submittal_notes)

        # --- Cut Sheet ---
        cut_sheet_row = QHBoxLayout()
        cut_sheet_row.setSpacing(6)
        self._edit_cut_sheet = QLineEdit()
        self._edit_cut_sheet.setReadOnly(True)  # always read-only; set via Import button
        self._edit_cut_sheet.setPlaceholderText("No file selected")
        cut_sheet_row.addWidget(self._edit_cut_sheet, stretch=1)

        self._btn_import_cut_sheet = QPushButton("Import Cut Sheet")
        self._btn_import_cut_sheet.clicked.connect(self._on_import_cut_sheet)
        self._btn_import_cut_sheet.setEnabled(not read_only)
        cut_sheet_row.addWidget(self._btn_import_cut_sheet)

        form.addRow("Cut Sheet", cut_sheet_row)

        root.addLayout(form)

        # --- Buttons ---
        btn_box = QDialogButtonBox()
        if read_only:
            btn_close = QPushButton("Close")
            btn_box.addButton(btn_close, QDialogButtonBox.RejectRole)
            btn_box.rejected.connect(self.reject)
        else:
            self._btn_save = QPushButton("Save")
            self._btn_save.setDefault(True)
            btn_cancel = QPushButton("Cancel")
            btn_box.addButton(self._btn_save, QDialogButtonBox.AcceptRole)
            btn_box.addButton(btn_cancel, QDialogButtonBox.RejectRole)
            btn_box.rejected.connect(self.reject)
            self._btn_save.clicked.connect(self._on_save)

        root.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Data loading (read-only / edit mode)
    # ------------------------------------------------------------------

    def _load_product(self, product_id: int) -> None:
        try:
            row = product_model.get(self.conn, product_id)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load product:\n{exc}")
            return

        if row is None:
            QMessageBox.critical(self, "Not Found", f"Product #{product_id} not found.")
            return

        self._edit_manufacturer.setText(row["manufacturer"] or "")
        self._edit_model_number.setText(row["model_number"] or "")
        self._edit_description.setText(row["description"] or "")
        self._edit_spec_section.setText(row["spec_section"] or "")
        self._edit_spec_section_title.setText(row["spec_section_title"] or "")
        self._edit_product_url.setText(row["product_url"] or "")
        self._edit_submittal_notes.setPlainText(row["submittal_notes"] or "")
        if row["cut_sheet_filename"]:
            self._cut_sheet_filename = row["cut_sheet_filename"]
            self._edit_cut_sheet.setText(row["cut_sheet_filename"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _required_labels(self):
        return (self._lbl_manufacturer, self._lbl_model_number, self._lbl_description)

    def _reset_label_colors(self) -> None:
        for lbl in self._required_labels():
            lbl.setStyleSheet("")

    def _mark_invalid(self, label: QLabel) -> None:
        label.setStyleSheet("color: red;")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_import_cut_sheet(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cut Sheet PDF",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not path:
            return  # user cancelled

        manufacturer = self._edit_manufacturer.text().strip()
        model_number = self._edit_model_number.text().strip()
        if not manufacturer or not model_number:
            QMessageBox.warning(
                self,
                "Fields Required",
                "Enter Manufacturer and Model Number before importing a cut sheet.",
            )
            return

        src = Path(path)
        filename = _sanitize_filename(manufacturer, model_number)

        try:
            _CUT_SHEETS_DIR.mkdir(parents=True, exist_ok=True)
            dest = _CUT_SHEETS_DIR / filename
            shutil.copy2(src, dest)
        except Exception as exc:
            QMessageBox.critical(self, "File Error", f"Could not copy cut sheet:\n{exc}")
            return

        self._cut_sheet_filename = filename
        self._edit_cut_sheet.setText(filename)

    def _on_save(self) -> None:
        self._reset_label_colors()

        manufacturer = self._edit_manufacturer.text().strip()
        model_number = self._edit_model_number.text().strip()
        description = self._edit_description.text().strip()

        valid = True
        if not manufacturer:
            self._mark_invalid(self._lbl_manufacturer)
            valid = False
        if not model_number:
            self._mark_invalid(self._lbl_model_number)
            valid = False
        if not description:
            self._mark_invalid(self._lbl_description)
            valid = False
        if not valid:
            return

        fields: dict = dict(
            manufacturer=manufacturer,
            model_number=model_number,
            description=description,
            spec_section=self._edit_spec_section.text().strip() or None,
            spec_section_title=self._edit_spec_section_title.text().strip() or None,
            product_url=self._edit_product_url.text().strip() or None,
            submittal_notes=self._edit_submittal_notes.toPlainText().strip() or None,
            cut_sheet_filename=self._cut_sheet_filename or None,
        )
        # Strip None optional fields to keep the INSERT clean.
        required = {"manufacturer", "model_number", "description"}
        fields = {k: v for k, v in fields.items() if v is not None or k in required}

        try:
            product_model.create(self.conn, **fields)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not save product:\n{exc}")
            return

        self.accept()
