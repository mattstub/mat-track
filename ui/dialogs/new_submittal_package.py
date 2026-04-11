"""Dialog — create a new submittal package (or revision) for a project."""

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
    QTextEdit,
    QVBoxLayout,
)

from db.models import submittal_package as submittal_package_model


class NewSubmittalPackageDialog(QDialog):
    """Form dialog to create a new submittal package for a project.

    Args:
        conn: Active SQLite connection.
        project_id: ID of the parent project.
        project_number: Project number string used to suggest the submittal number.
        parent: Optional parent widget.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        project_id: int,
        project_number: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.project_id = project_id
        self.project_number = project_number or ""
        self.setWindowTitle("New Submittal Package")
        self.setMinimumWidth(440)
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

        # Spec Section
        self._edit_spec_section = QLineEdit()
        self._edit_spec_section.setPlaceholderText("e.g. 220000")
        form.addRow("Spec Section", self._edit_spec_section)

        # Spec Section Title
        self._edit_spec_title = QLineEdit()
        self._edit_spec_title.setPlaceholderText("e.g. Plumbing Fixtures")
        form.addRow("Spec Section Title", self._edit_spec_title)

        # Title (user-defined)
        self._edit_title = QLineEdit()
        form.addRow("Title", self._edit_title)

        # Submittal Number (required, pre-filled)
        self._lbl_number = QLabel("Submittal Number*")
        self._edit_number = QLineEdit()
        suggested = submittal_package_model.next_submittal_number(self.conn, self.project_number)
        self._edit_number.setText(suggested)
        form.addRow(self._lbl_number, self._edit_number)

        # Date Submitted
        self._edit_date = QLineEdit()
        self._edit_date.setPlaceholderText("YYYY-MM-DD (optional)")
        form.addRow("Date Submitted", self._edit_date)

        # Notes
        self._edit_notes = QTextEdit()
        self._edit_notes.setFixedHeight(62)  # ~3 lines
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
        self._lbl_number.setStyleSheet("")

    def _mark_invalid(self, label: QLabel) -> None:
        label.setStyleSheet("color: red;")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        self._reset_label_colors()

        submittal_number = self._edit_number.text().strip()
        valid = True

        if not submittal_number:
            self._mark_invalid(self._lbl_number)
            valid = False

        if not valid:
            return

        fields: dict = {
            "project_id": self.project_id,
            "submittal_number": submittal_number,
        }

        spec_section = self._edit_spec_section.text().strip()
        if spec_section:
            fields["spec_section"] = spec_section

        spec_title = self._edit_spec_title.text().strip()
        if spec_title:
            fields["spec_section_title"] = spec_title

        title = self._edit_title.text().strip()
        if title:
            fields["title"] = title

        date_submitted = self._edit_date.text().strip()
        if date_submitted:
            fields["date_submitted"] = date_submitted

        notes = self._edit_notes.toPlainText().strip()
        if notes:
            fields["notes"] = notes

        try:
            submittal_package_model.create(self.conn, **fields)
        except Exception as exc:
            QMessageBox.critical(
                self, "Database Error", f"Could not save submittal package:\n{exc}"
            )
            return

        self.accept()
