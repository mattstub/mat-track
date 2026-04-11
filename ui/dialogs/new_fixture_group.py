"""Dialog — add a fixture group (tag + description) to a submittal package."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from db.models import fixture_group as fixture_group_model


class NewFixtureGroupDialog(QDialog):
    """Form dialog to add a fixture group to a submittal package.

    Args:
        conn: Active SQLite connection.
        package_id: ID of the parent submittal package.
        parent: Optional parent widget.
    """

    def __init__(self, conn: sqlite3.Connection, package_id: int, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.package_id = package_id
        self.setWindowTitle("New Fixture Group")
        self.setMinimumWidth(400)
        self._build_ui()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(6)

        # Tag Designation (required)
        self._lbl_tag = QLabel("Tag Designation*")
        self._edit_tag = QLineEdit()
        self._edit_tag.setPlaceholderText("e.g. WC-1")
        form.addRow(self._lbl_tag, self._edit_tag)

        # Description (required)
        self._lbl_desc = QLabel("Description*")
        self._edit_desc = QLineEdit()
        self._edit_desc.setPlaceholderText("e.g. Water Closet, LH Trip Lever")
        form.addRow(self._lbl_desc, self._edit_desc)

        # Quantity
        self._spin_qty = QSpinBox()
        self._spin_qty.setMinimum(0)
        self._spin_qty.setValue(1)
        form.addRow("Quantity", self._spin_qty)

        # Notes
        self._edit_notes = QTextEdit()
        self._edit_notes.setFixedHeight(48)  # ~2 lines
        form.addRow("Notes", self._edit_notes)

        root.addLayout(form)

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
    # Validation helpers
    # ------------------------------------------------------------------

    def _reset_label_colors(self) -> None:
        for lbl in (self._lbl_tag, self._lbl_desc):
            lbl.setStyleSheet("")

    def _mark_invalid(self, label: QLabel) -> None:
        label.setStyleSheet("color: red;")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        self._reset_label_colors()

        tag = self._edit_tag.text().strip()
        desc = self._edit_desc.text().strip()
        valid = True

        if not tag:
            self._mark_invalid(self._lbl_tag)
            valid = False
        if not desc:
            self._mark_invalid(self._lbl_desc)
            valid = False
        if not valid:
            return

        fields: dict = {
            "submittal_package_id": self.package_id,
            "tag_designation": tag,
            "description": desc,
            "quantity": self._spin_qty.value(),
        }

        notes = self._edit_notes.toPlainText().strip()
        if notes:
            fields["notes"] = notes

        try:
            fixture_group_model.create(self.conn, **fields)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not save fixture group:\n{exc}")
            return

        self.accept()
