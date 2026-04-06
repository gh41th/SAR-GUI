"""
ui/main_window.py — The main application window.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QAction, QStatusBar,
    QFileDialog, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt

from ui.layer_panel import LayerPanel
from ui.tool_panel import ToolPanel
from ui.image_viewer import ImageViewer
from data.worker import FileLoaderThread, OverviewLoaderThread, RegionLoaderThread
from data.io import NISARFileInfo, has_cached_overview


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NISAR SAR Tools")
        self.setMinimumSize(1200, 800)

        self._active_threads = []   # keep refs so GC doesn't kill running threads
        self._current_info   = None # NISARFileInfo of the currently loaded file

        self._init_menu_bar()
        self._init_central_widget()
        self._init_dock_panels()
        self._init_status_bar()

    # ------------------------------------------------------------------
    # UI SETUP
    # ------------------------------------------------------------------

    def _init_menu_bar(self):
        menubar = self.menuBar()

        # ── File ──────────────────────────────────────────────────────
        file_menu = menubar.addMenu("File")
        self._add_action(file_menu, "Open...",   "Ctrl+O", "Open a SAR data file",  self._on_open)
        self._add_action(file_menu, "Save",      "Ctrl+S", "Save current project",  self._on_save)
        self._add_action(file_menu, "Export...", "",       "Export processed data", self._on_export)
        file_menu.addSeparator()
        self._add_action(file_menu, "Exit",      "Ctrl+Q", "", self.close)

        # ── Tools ─────────────────────────────────────────────────────
        tools_menu = menubar.addMenu("Tools")
        self._add_action(tools_menu, "Boxcar Filter",     "", "Apply boxcar filter",       lambda: self._on_tool_selected("Boxcar Filter"))
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Coherency Matrix",  "", "Compute coherency matrix",  lambda: self._on_tool_selected("Coherency Matrix"))
        self._add_action(tools_menu, "Covariance Matrix", "", "Compute covariance matrix", lambda: self._on_tool_selected("Covariance Matrix"))

        # ── View ──────────────────────────────────────────────────────
        view_menu = menubar.addMenu("View")
        self._add_action(view_menu, "Zoom In",    "Ctrl++", "", self.image_viewer.zoom_in   if hasattr(self, "image_viewer") else lambda: None)
        self._add_action(view_menu, "Zoom Out",   "Ctrl+-", "", self.image_viewer.zoom_out  if hasattr(self, "image_viewer") else lambda: None)
        self._add_action(view_menu, "Reset View", "Ctrl+0", "", self.image_viewer.reset_view if hasattr(self, "image_viewer") else lambda: None)

        # ── Help ──────────────────────────────────────────────────────
        help_menu = menubar.addMenu("Help")
        self._add_action(help_menu, "About", "", "", self._on_about)

    def _add_action(self, menu, text, shortcut, tip, slot):
        """Helper to create and add a QAction in one line."""
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        if tip:
            action.setStatusTip(tip)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _init_central_widget(self):
        self.image_viewer = ImageViewer()
        self.image_viewer.zoom_requested.connect(self._on_zoom_requested)
        self.setCentralWidget(self.image_viewer)

    def _init_dock_panels(self):
        self.layer_panel = LayerPanel()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.layer_panel)

        self.tool_panel = ToolPanel()
        self.addDockWidget(Qt.RightDockWidgetArea, self.tool_panel)

    def _init_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(180)
        self._progress_bar.setFixedHeight(14)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self._progress_bar)

        self.status_bar.showMessage("Ready")

    # ------------------------------------------------------------------
    # FILE OPEN
    # ------------------------------------------------------------------

    def _on_open(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open NISAR File", "",
            "NISAR HDF5 Files (*.h5 *.hdf5);;All Files (*)"
        )
        if not file_path:
            return

        self.status_bar.showMessage(f"Reading metadata: {file_path} ...")
        t = FileLoaderThread(file_path)
        t.result.connect(self._on_metadata_loaded)
        t.error.connect(self._on_error)
        t.start()
        self._active_threads.append(t)

    def _on_metadata_loaded(self, info: NISARFileInfo):
        print(f"[main] metadata loaded: {info.product_type} "
              f"{[p.name for p in info.polarizations]}", flush=True)

        self._current_info = info

        pol_names   = ", ".join(p.name for p in info.polarizations)
        layer_label = f"{info.display_name}  [{info.product_type} · {pol_names}]"
        self.layer_panel.add_layer(layer_label, info.product_type)

        shape = info.polarizations[0].shape if info.polarizations else "?"
        self.status_bar.showMessage(
            f"{info.product_type} | {info.band} | "
            f"Freq {info.frequency} | {shape} | {pol_names}"
        )

        if not info.polarizations:
            return

        first_pol = info.polarizations[0]
        cached    = has_cached_overview(info.file_path, first_pol.name)
        self.status_bar.showMessage(
            "Loading cached overview..." if cached
            else "Building overview (~5s on first load, cached after)..."
        )
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)

        t = OverviewLoaderThread(
            file_path=info.file_path,
            h5_path=first_pol.h5_path,
            dataset_name=first_pol.name,
        )
        t.progress.connect(self._progress_bar.setValue)
        t.result.connect(lambda arr: self._on_overview_ready(arr, info))
        t.error.connect(self._on_error)
        t.start()
        self._active_threads.append(t)
        print(f"[main] OverviewLoaderThread started for {first_pol.name}", flush=True)

    def _on_overview_ready(self, display_array, info: NISARFileInfo):
        self._progress_bar.setVisible(False)
        self.status_bar.showMessage("Image loaded. Scroll to zoom.")
        pol = info.polarizations[0]
        print(f"[main] displaying overview, full res={pol.shape}", flush=True)
        self.image_viewer.display_array(
            display_array,
            data_rows=pol.shape[0],
            data_cols=pol.shape[1],
        )

    # ------------------------------------------------------------------
    # ZOOM REGION LOADING
    # ------------------------------------------------------------------

    def _on_zoom_requested(self, r0, r1, c0, c1, downsample):
        if self._current_info is None:
            return
        pol = self._current_info.polarizations[0]
        print(f"[main] zoom request rows={r0}:{r1} cols={c0}:{c1} ds={downsample}", flush=True)
        self.status_bar.showMessage("Loading higher resolution...")
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)

        t = RegionLoaderThread(
            file_path=self._current_info.file_path,
            h5_path=pol.h5_path,
            row_start=r0, row_end=r1,
            col_start=c0, col_end=c1,
            downsample=downsample,
        )
        t.progress.connect(self._progress_bar.setValue)
        t.result.connect(self._on_region_ready)
        t.error.connect(self._on_error)
        t.start()
        self._active_threads.append(t)

    def _on_region_ready(self, array, r0, r1, c0, c1):
        self._progress_bar.setVisible(False)
        self.status_bar.showMessage("Higher resolution loaded.")
        print(f"[main] region ready shape={array.shape}", flush=True)
        self.image_viewer.update_region(array, r0, r1, c0, c1)

    # ------------------------------------------------------------------
    # OTHER SLOTS
    # ------------------------------------------------------------------

    def _on_save(self):
        self.status_bar.showMessage("Save — coming soon")

    def _on_export(self):
        self.status_bar.showMessage("Export — coming soon")

    def _on_tool_selected(self, tool_name: str):
        self.status_bar.showMessage(f"Tool selected: {tool_name}")
        self.tool_panel.show_tool(tool_name)

    def _on_about(self):
        self.status_bar.showMessage("NISAR SAR Tools — built with PyQt5")

    def _on_error(self, message: str):
        self._progress_bar.setVisible(False)
        self.status_bar.showMessage("Error.")
        QMessageBox.critical(self, "Error", message)