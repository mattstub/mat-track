"""Bottom-tab panel — supplier management."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from db.models import supplier as supplier_model
from ui.dialogs.supplier_edit import SupplierEditDialog


class SupplierPanel(QWidget):
    """Full-width panel for browsing, creating, editing, and deleting suppliers.

    Public API:
        refresh(): Reload the supplier list from the database.
    """

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._selected_supplier_id: int | None = None
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 6, 4, 4)
        root.setSpacing(4)

        # --- Toolbar row ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._btn_new = QPushButton("+ New Supplier")
        self._btn_new.clicked.connect(self._on_new)
        toolbar.addWidget(self._btn_new)

        self._btn_edit = QPushButton("Edit")
        self._btn_edit.setEnabled(False)
        self._btn_edit.clicked.connect(self._on_edit)
        toolbar.addWidget(self._btn_edit)

        self._btn_delete = QPushButton("Delete")
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._on_delete)
        toolbar.addWidget(self._btn_delete)

        toolbar.addStretch()
        root.addLayout(toolbar)

        # --- Splitter: list (left) + detail (right) ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: list widget
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._list)

        # Right: read-only detail area
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(12, 8, 12, 8)
        detail_layout.setSpacing(6)

        self._detail_form = QFormLayout()
        self._detail_form.setLabelAlignment(Qt.AlignRight)
        self._detail_form.setSpacing(6)

        self._detail_company = QLabel("")
        self._detail_contact = QLabel("")
        self._detail_email = QLabel("")
        self._detail_phone = QLabel("")
        self._detail_address = QLabel("")
        self._detail_notes = QLabel("")
        self._detail_notes.setWordWrap(True)
        self._detail_notify_po = QLabel("")
        self._detail_notify_approval = QLabel("")

        self._detail_form.addRow("Company:", self._detail_company)
        self._detail_form.addRow("Contact:", self._detail_contact)
        self._detail_form.addRow("Email:", self._detail_email)
        self._detail_form.addRow("Phone:", self._detail_phone)
        self._detail_form.addRow("Address:", self._detail_address)
        self._detail_form.addRow("Notes:", self._detail_notes)
        self._detail_form.addRow("Notify on PO:", self._detail_notify_po)
        self._detail_form.addRow("Notify on Approval:", self._detail_notify_approval)

        detail_layout.addLayout(self._detail_form)
        detail_layout.addStretch()

        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter, stretch=1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload the supplier list from the database."""
        self._list.blockSignals(True)
        self._list.clear()

        try:
            suppliers = supplier_model.get_all(self.conn)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load suppliers:\n{exc}")
            self._list.blockSignals(False)
            return

        for sup in suppliers:
            label = sup["company_name"] or "(unnamed)"
            contact = sup["contact_name"] or ""
            if contact:
                label = f"{label}\n{contact}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, sup["id"])
            self._list.addItem(item)

        self._list.blockSignals(False)

        # Re-select the previously selected supplier if it still exists
        if self._selected_supplier_id is not None:
            self._reselect(self._selected_supplier_id)
        else:
            self._clear_detail()
            self._btn_edit.setEnabled(False)
            self._btn_delete.setEnabled(False)

    # ------------------------------------------------------------------
    # Selection handling
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        selected = self._list.selectedItems()
        if not selected:
            self._selected_supplier_id = None
            self._clear_detail()
            self._btn_edit.setEnabled(False)
            self._btn_delete.setEnabled(False)
            return

        supplier_id = selected[0].data(Qt.UserRole)
        self._selected_supplier_id = supplier_id
        self._btn_edit.setEnabled(True)
        self._btn_delete.setEnabled(True)
        self._populate_detail(supplier_id)

    def _populate_detail(self, supplier_id: int) -> None:
        try:
            sup = supplier_model.get(self.conn, supplier_id)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load supplier:\n{exc}")
            return

        if sup is None:
            self._clear_detail()
            return

        self._detail_company.setText(sup["company_name"] or "")
        self._detail_contact.setText(sup["contact_name"] or "")
        self._detail_email.setText(sup["email"] or "")
        self._detail_phone.setText(sup["phone"] or "")
        self._detail_address.setText(sup["address"] or "")
        self._detail_notes.setText(sup["notes"] or "")
        self._detail_notify_po.setText("Yes" if sup["notify_on_po"] else "No")
        self._detail_notify_approval.setText("Yes" if sup["notify_on_approval"] else "No")

    def _clear_detail(self) -> None:
        for lbl in (
            self._detail_company,
            self._detail_contact,
            self._detail_email,
            self._detail_phone,
            self._detail_address,
            self._detail_notes,
            self._detail_notify_po,
            self._detail_notify_approval,
        ):
            lbl.setText("")

    def _reselect(self, supplier_id: int) -> None:
        """Re-select the list item matching supplier_id after a refresh."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.UserRole) == supplier_id:
                self._list.setCurrentItem(item)
                return
        # Supplier no longer exists — clear
        self._selected_supplier_id = None
        self._clear_detail()
        self._btn_edit.setEnabled(False)
        self._btn_delete.setEnabled(False)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_new(self) -> None:
        dlg = SupplierEditDialog(self.conn, supplier=None, parent=self)
        if dlg.exec():
            self._selected_supplier_id = dlg.supplier_id
            self.refresh()

    def _on_edit(self) -> None:
        if self._selected_supplier_id is None:
            return

        try:
            sup = supplier_model.get(self.conn, self._selected_supplier_id)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load supplier:\n{exc}")
            return

        if sup is None:
            QMessageBox.critical(self, "Not Found", "Supplier record no longer exists.")
            self.refresh()
            return

        dlg = SupplierEditDialog(self.conn, supplier=sup, parent=self)
        if dlg.exec():
            self.refresh()

    def _on_delete(self) -> None:
        if self._selected_supplier_id is None:
            return

        # Get the name for the confirmation prompt
        try:
            sup = supplier_model.get(self.conn, self._selected_supplier_id)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Could not load supplier:\n{exc}")
            return

        name = sup["company_name"] if sup else "this supplier"
        answer = QMessageBox.question(
            self,
            "Delete Supplier",
            f"Delete '{name}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            supplier_model.delete(self.conn, self._selected_supplier_id)
        except Exception as exc:
            err = str(exc)
            if "FOREIGN KEY" in err.upper() or "IntegrityError" in type(exc).__name__:
                QMessageBox.critical(
                    self,
                    "Cannot Delete",
                    "Cannot delete: supplier is in use.",
                )
            else:
                QMessageBox.critical(self, "Database Error", f"Could not delete supplier:\n{exc}")
            return

        self._selected_supplier_id = None
        self.refresh()
