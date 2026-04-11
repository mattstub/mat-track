"""Main application window — three-panel layout with bottom tab bar."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs.new_po import NewPODialog
from ui.dialogs.new_project import NewProjectDialog
from ui.panels.po_panel import POPanel
from ui.panels.project_panel import ProjectPanel
from ui.panels.submittal_panel import SubmittalPanel
from ui.panels.supplier_panel import SupplierPanel


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn
        self.setWindowTitle("MatTrack")
        self.setMinimumSize(1100, 700)
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Toolbar ────────────────────────────────────────────────────────────
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        btn_new_project = QPushButton("+ Project")
        btn_new_project.clicked.connect(self._on_new_project)
        toolbar.addWidget(btn_new_project)

        toolbar.addSeparator()

        self._btn_new_submittal = QPushButton("+ Submittal")
        self._btn_new_submittal.setEnabled(False)
        self._btn_new_submittal.clicked.connect(self._on_new_submittal)
        toolbar.addWidget(self._btn_new_submittal)

        # + Material — Phase 6
        btn_material = QPushButton("+ Material")
        btn_material.setEnabled(False)
        toolbar.addWidget(btn_material)

        self._btn_new_po = QPushButton("+ PO")
        self._btn_new_po.setEnabled(False)
        self._btn_new_po.clicked.connect(self._on_new_po)
        toolbar.addWidget(self._btn_new_po)

        # Spacer to push future search widget to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # ── Central area ───────────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Content area (tab pages stacked)
        self._content_stack = QStackedWidget()
        root_layout.addWidget(self._content_stack, stretch=1)

        # ── Tab bar at the bottom ──────────────────────────────────────────────
        self._tab_bar = QTabBar()
        self._tab_bar.setExpanding(False)
        tab_labels = ["Projects", "Catalog", "Suppliers", "All POs"]
        for label in tab_labels:
            self._tab_bar.addTab(label)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        root_layout.addWidget(self._tab_bar)

        # ── Build individual tab pages ─────────────────────────────────────────
        # Tab 0 — Projects: three-panel layout
        self._page_projects = self._build_projects_page()
        self._content_stack.addWidget(self._page_projects)

        # Tab 1 — Catalog: placeholder (Phase 2 catalog panel wired in later)
        catalog_placeholder = QWidget()
        ph_layout = QVBoxLayout(catalog_placeholder)
        lbl = QLabel("Catalog — coming in a later phase")
        lbl.setAlignment(Qt.AlignCenter)
        ph_layout.addWidget(lbl)
        self._content_stack.addWidget(catalog_placeholder)

        # Tab 2 — Suppliers
        self._supplier_panel = SupplierPanel(self.conn)
        self._content_stack.addWidget(self._supplier_panel)

        # Tab 3 — All POs
        self._po_panel_all = POPanel(self.conn)
        self._content_stack.addWidget(self._po_panel_all)

        # Load initial data for always-visible panels
        self._po_panel_all.load_all()

        # Start on Projects tab
        self._tab_bar.setCurrentIndex(0)
        self._content_stack.setCurrentIndex(0)

    def _build_projects_page(self) -> QWidget:
        """Three-panel layout for the Projects tab."""
        page = QWidget()
        h_layout = QHBoxLayout(page)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # Left panel — ProjectPanel
        self._project_panel = ProjectPanel(self.conn, parent=page)
        self._project_panel.setFixedWidth(220)
        self._project_panel.project_selected.connect(self._on_project_selected)
        h_layout.addWidget(self._project_panel)

        # Vertical separator
        sep1 = QWidget()
        sep1.setFixedWidth(1)
        sep1.setStyleSheet("background-color: #cccccc;")
        h_layout.addWidget(sep1)

        # Center panel — SubmittalPanel
        self._submittal_panel = SubmittalPanel(self.conn, parent=page)
        h_layout.addWidget(self._submittal_panel, stretch=2)

        # Vertical separator
        sep2 = QWidget()
        sep2.setFixedWidth(1)
        sep2.setStyleSheet("background-color: #cccccc;")
        h_layout.addWidget(sep2)

        # Right panel — placeholder (Phase 3: detail/actions panel)
        self._right_panel = QWidget()
        right_layout = QVBoxLayout(self._right_panel)
        right_lbl = QLabel("Detail / Actions — Phase 3")
        right_lbl.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_lbl)
        h_layout.addWidget(self._right_panel, stretch=1)

        return page

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_tab_changed(self, index: int) -> None:
        self._content_stack.setCurrentIndex(index)

    def _on_new_project(self) -> None:
        dlg = NewProjectDialog(self.conn, parent=self)
        if dlg.exec():
            # Refresh the project panel so the new project appears
            try:
                self._project_panel.refresh()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Could not refresh project list:\n{exc}")

    def _on_project_selected(self, project_id: int) -> None:
        """Called when the user selects a project in the left panel."""
        self._current_project_id = project_id
        self._submittal_panel.load_project(project_id)
        self._btn_new_submittal.setEnabled(True)
        self._btn_new_po.setEnabled(True)

    def _on_new_submittal(self) -> None:
        self._submittal_panel._on_new_package()

    def _on_new_po(self) -> None:
        if not hasattr(self, "_current_project_id"):
            return
        dlg = NewPODialog(self.conn, self._current_project_id, parent=self)
        if dlg.exec():
            self._po_panel_all.refresh()
