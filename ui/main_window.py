"""
ui/main_window.py — The main application window.

QMainWindow is a special Qt class that comes with built-in slots for:
  - A menu bar (top)
  - A toolbar (below menu bar)
  - A status bar (bottom)
  - A central widget (the main content area)
  - Dock widgets (panels that can attach to the sides)
"""

from PyQt5.QtWidgets import (
    QMainWindow, QAction, QMenuBar,
    QStatusBar, QLabel
)
from PyQt5.QtCore import Qt

from ui.layer_panel import LayerPanel
from ui.tool_panel import ToolPanel
from ui.image_viewer import ImageViewer


class MainWindow(QMainWindow):

    def __init__(self):
        # Always call the parent class constructor first
        super().__init__()

        self.setWindowTitle("NISAR SAR Tools")
        self.setMinimumSize(1200, 800)   # minimum window size in pixels

        # Build the UI pieces in order
        self._init_menu_bar()
        self._init_central_widget()
        self._init_dock_panels()
        self._init_status_bar()

    # ------------------------------------------------------------------
    # MENU BAR
    # ------------------------------------------------------------------
    def _init_menu_bar(self):
        """
        Creates the top menu bar with File and Tools menus.
        QAction represents a clickable item inside a menu.
        """
        menubar = self.menuBar()

        # ── File menu ──────────────────────────────────────────────────
        file_menu = menubar.addMenu("File")

        # QAction(text, parent) — the parent is 'self' (the main window)
        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("Open a SAR data file")
        open_action.triggered.connect(self._on_open)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip("Save current project")
        save_action.triggered.connect(self._on_save)

        export_action = QAction("Export...", self)
        export_action.setStatusTip("Export processed data")
        export_action.triggered.connect(self._on_export)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(export_action)
        file_menu.addSeparator()          # horizontal dividing line
        file_menu.addAction(exit_action)

        # ── Tools menu ─────────────────────────────────────────────────
        tools_menu = menubar.addMenu("Tools")

        boxcar_action = QAction("Boxcar Filter", self)
        boxcar_action.setStatusTip("Apply a boxcar (mean) spatial filter")
        boxcar_action.triggered.connect(lambda: self._on_tool_selected("Boxcar Filter"))

        coherency_action = QAction("Coherency Matrix", self)
        coherency_action.setStatusTip("Compute the coherency matrix [T]")
        coherency_action.triggered.connect(lambda: self._on_tool_selected("Coherency Matrix"))

        covariance_action = QAction("Covariance Matrix", self)
        covariance_action.setStatusTip("Compute the covariance matrix [C]")
        covariance_action.triggered.connect(lambda: self._on_tool_selected("Covariance Matrix"))

        tools_menu.addAction(boxcar_action)
        tools_menu.addSeparator()
        tools_menu.addAction(coherency_action)
        tools_menu.addAction(covariance_action)

        # ── View menu ──────────────────────────────────────────────────
        view_menu = menubar.addMenu("View")

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self._on_zoom_in)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self._on_zoom_out)

        reset_view_action = QAction("Reset View", self)
        reset_view_action.setShortcut("Ctrl+0")
        reset_view_action.triggered.connect(self._on_reset_view)

        view_menu.addAction(zoom_in_action)
        view_menu.addAction(zoom_out_action)
        view_menu.addAction(reset_view_action)

        # ── Help menu ──────────────────────────────────────────────────
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # CENTRAL WIDGET (the image viewer)
    # ------------------------------------------------------------------
    def _init_central_widget(self):
        """
        The central widget fills the middle of the window.
        We use our custom ImageViewer here.
        """
        self.image_viewer = ImageViewer()
        self.setCentralWidget(self.image_viewer)

    # ------------------------------------------------------------------
    # DOCK PANELS (left and right side panels)
    # ------------------------------------------------------------------
    def _init_dock_panels(self):
        """
        QDockWidget is a panel that 'docks' to a side of the main window.
        We create one for layers (left) and one for tool controls (right).
        """
        # Left panel — Layers
        self.layer_panel = LayerPanel()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.layer_panel)

        # Right panel — Tool Controls
        self.tool_panel = ToolPanel()
        self.addDockWidget(Qt.RightDockWidgetArea, self.tool_panel)

    # ------------------------------------------------------------------
    # STATUS BAR
    # ------------------------------------------------------------------
    def _init_status_bar(self):
        """
        The status bar lives at the very bottom of the window.
        It's useful for showing pixel coordinates, progress messages, etc.
        """
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    # ------------------------------------------------------------------
    # SLOT METHODS (what happens when menu items are clicked)
    # These are placeholders for now — we'll fill them in later.
    # ------------------------------------------------------------------
    def _on_open(self):
        self.status_bar.showMessage("Open file dialog — coming soon")

    def _on_save(self):
        self.status_bar.showMessage("Save — coming soon")

    def _on_export(self):
        self.status_bar.showMessage("Export — coming soon")

    def _on_tool_selected(self, tool_name: str):
        self.status_bar.showMessage(f"Tool selected: {tool_name}")
        self.tool_panel.show_tool(tool_name)

    def _on_zoom_in(self):
        self.image_viewer.zoom_in()

    def _on_zoom_out(self):
        self.image_viewer.zoom_out()

    def _on_reset_view(self):
        self.image_viewer.reset_view()

    def _on_about(self):
        self.status_bar.showMessage("NISAR SAR Tools — built with PyQt5")