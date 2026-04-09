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

from ui.dialogs.new_project import NewProjectDialog
from ui.panels.project_panel import ProjectPanel


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

        # Placeholder buttons for later phases
        for label in ("+ Submittal", "+ Material", "+ PO"):
            btn = QPushButton(label)
            btn.setEnabled(False)
            toolbar.addWidget(btn)

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

        # Tabs 1-3 — placeholders
        for label in ("Catalog", "Suppliers", "All POs"):
            placeholder = QWidget()
            ph_layout = QVBoxLayout(placeholder)
            lbl = QLabel(f"{label} — coming in a later phase")
            lbl.setAlignment(Qt.AlignCenter)
            ph_layout.addWidget(lbl)
            self._content_stack.addWidget(placeholder)

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

        # Center panel — placeholder (Phase 3: submittal panel)
        self._center_panel = QWidget()
        center_layout = QVBoxLayout(self._center_panel)
        center_lbl = QLabel("Submittal packages — Phase 3")
        center_lbl.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(center_lbl)
        h_layout.addWidget(self._center_panel, stretch=2)

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
        # Phase 3 will wire this to the center and right panels.
        # For now, store the selection so later phases can use it.
        self._current_project_id = project_id
