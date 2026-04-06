"""
ui/layer_panel.py — Left dock panel showing the layer list.

QDockWidget is a container that can be docked to any side of QMainWindow.
Inside it we put a QTreeWidget — a list that can have nested items,
like QGIS or ArcGIS layers panels.
"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout,
    QTreeWidget, QTreeWidgetItem, QLabel
)
from PyQt5.QtCore import Qt


class LayerPanel(QDockWidget):

    def __init__(self, parent=None):
        super().__init__("Layers", parent)   # "Layers" is the panel title

        # Prevent the panel from being closed or floated for now
        # We'll make this configurable later
        self.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
        )
        self.setMinimumWidth(200)

        # Build the inner widget
        self._build_ui()

    def _build_ui(self):
        """
        QDockWidget needs one inner widget. We give it a container
        with a vertical layout holding our tree.
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header label
        header = QLabel("Layers")
        header.setStyleSheet("font-weight: bold; padding: 2px;")
        layout.addWidget(header)

        # The tree widget — each row is a layer
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)    # hide the default "column 1" header
        self.tree.setColumnCount(1)

        # Add a placeholder item so it's not empty
        placeholder = QTreeWidgetItem(["No layers loaded"])
        placeholder.setFlags(Qt.NoItemFlags)   # make it non-selectable
        self.tree.addTopLevelItem(placeholder)

        layout.addWidget(self.tree)
        self.setWidget(container)

    # ------------------------------------------------------------------
    # PUBLIC API — we'll call these from main_window when files are opened
    # ------------------------------------------------------------------
    def add_layer(self, name: str, layer_type: str = "Raster"):
        """Add a new layer entry to the tree."""
        # Clear placeholder if present
        if self.tree.topLevelItemCount() == 1:
            first = self.tree.topLevelItem(0)
            if first.flags() == Qt.NoItemFlags:
                self.tree.clear()

        item = QTreeWidgetItem([name])
        item.setToolTip(0, f"Type: {layer_type}")
        self.tree.addTopLevelItem(item)
        self.tree.setCurrentItem(item)

    def clear_layers(self):
        self.tree.clear()