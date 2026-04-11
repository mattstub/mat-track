"""Dialog — create or edit a supplier record."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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

from db.models import supplier as supplier_model


class SupplierEditDialog(QDialog):
    """Form dialog to create a new supplier or edit an existing one.

    Args:
        conn: Active SQLite connection.
        supplier: Existing supplier row/dict to pre-fill (edit mode), or None (create mode).
        parent: Optional parent widget.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        supplier=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self._supplier = supplier
        self._supplier_id: int | None = supplier["id"] if supplier else None
        self.setWindowTitle("Edit Supplier" if supplier else "New Supplier")
        self.setMinimumWidth(440)
        self._build_ui()
        if supplier:
            self._prefill(supplier)

    # ------------------------------------------------------------------
    # Property
    # ------------------------------------------------------------------

    @property
    def supplier_id(self) -> int | None:
        """ID of the supplier after a successful create, or the existing ID in edit mode."""
        return self._supplier_id

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

        # Company Name (required)
        self._lbl_company_name = QLabel("Company Name*")
        self._edit_company_name = QLineEdit()
        self._edit_company_name.setPlaceholderText("e.g. Ferguson Enterprises")
        form.addRow(self._lbl_company_name, self._edit_company_name)

        # Contact Name
        self._edit_contact_name = QLineEdit()
        self._edit_contact_name.setPlaceholderText("e.g. Jane Smith")
        form.addRow("Contact Name", self._edit_contact_name)

        # Email
        self._edit_email = QLineEdit()
        self._edit_email.setPlaceholderText("e.g. jane@ferguson.com")
        form.addRow("Email", self._edit_email)

        # Phone
        self._edit_phone = QLineEdit()
        self._edit_phone.setPlaceholderText("e.g. (555) 867-5309")
        form.addRow("Phone", self._edit_phone)

        # Address
        self._edit_address = QLineEdit()
        self._edit_address.setPlaceholderText("e.g. 123 Main St, City, ST 00000")
        form.addRow("Address", self._edit_address)

        # Notes
        self._edit_notes = QTextEdit()
        self._edit_notes.setFixedHeight(62)  # ~3 lines
        form.addRow("Notes", self._edit_notes)

        # Notify checkboxes
        self._chk_notify_po = QCheckBox("Notify on PO")
        self._chk_notify_po.setChecked(True)
        form.addRow("", self._chk_notify_po)

        self._chk_notify_approval = QCheckBox("Notify on Approval")
        self._chk_notify_approval.setChecked(True)
        form.addRow("", self._chk_notify_approval)

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

    def _prefill(self, supplier) -> None:
        """Pre-fill form fields from an existing supplier record."""
        self._edit_company_name.setText(supplier["company_name"] or "")
        self._edit_contact_name.setText(supplier["contact_name"] or "")
        self._edit_email.setText(supplier["email"] or "")
        self._edit_phone.setText(supplier["phone"] or "")
        self._edit_address.setText(supplier["address"] or "")
        self._edit_notes.setPlainText(supplier["notes"] or "")
        self._chk_notify_po.setChecked(bool(supplier["notify_on_po"]))
        self._chk_notify_approval.setChecked(bool(supplier["notify_on_approval"]))

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _reset_label_colors(self) -> None:
        self._lbl_company_name.setStyleSheet("")

    def _mark_invalid(self, label: QLabel) -> None:
        label.setStyleSheet("color: red;")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        self._reset_label_colors()

        company_name = self._edit_company_name.text().strip()
        valid = True

        if not company_name:
            self._mark_invalid(self._lbl_company_name)
            valid = False

        if not valid:
            return

        fields: dict = {
            "company_name": company_name,
            "notify_on_po": 1 if self._chk_notify_po.isChecked() else 0,
            "notify_on_approval": 1 if self._chk_notify_approval.isChecked() else 0,
        }

        contact_name = self._edit_contact_name.text().strip()
        if contact_name:
            fields["contact_name"] = contact_name

        email = self._edit_email.text().strip()
        if email:
            fields["email"] = email

        phone = self._edit_phone.text().strip()
        if phone:
            fields["phone"] = phone

        address = self._edit_address.text().strip()
        if address:
            fields["address"] = address

        notes = self._edit_notes.toPlainText().strip()
        if notes:
            fields["notes"] = notes

        try:
            if self._supplier is None:
                new_id = supplier_model.create(self.conn, **fields)
                self._supplier_id = new_id
            else:
                supplier_model.update(self.conn, self._supplier_id, **fields)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not save supplier:\n{exc}")
            return

        self.accept()
