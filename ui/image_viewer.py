"""
ui/image_viewer.py — The central image display widget.

Key Qt classes used:
  - QGraphicsView  : the "viewport" — the visible window into the scene
  - QGraphicsScene : the "canvas"   — holds all the items (images, shapes)
  - QGraphicsPixmapItem : an image item placed on the scene

Think of it like Google Maps:
  - QGraphicsScene = the entire map
  - QGraphicsView  = the browser window you look through
  - You can pan and zoom the view over the scene
"""

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsTextItem
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter


class ImageViewer(QGraphicsView):

    ZOOM_FACTOR = 1.15   # how much each zoom step scales the view

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create the scene and attach it to this view
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Appearance settings
        self.setBackgroundBrush(QColor("#1e1e2e"))   # dark background
        self.setRenderHint(QPainter.Antialiasing)

        # Allow the view to anchor zoom to the mouse cursor position
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        # Enable drag-to-pan with the left mouse button
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        # Draw a placeholder message so the window isn't blank
        self._draw_placeholder()

    # ------------------------------------------------------------------
    # PLACEHOLDER
    # ------------------------------------------------------------------
    def _draw_placeholder(self):
        """Shows a message in the center until an image is loaded."""
        text = QGraphicsTextItem("No image loaded\nUse File → Open to load a SAR dataset")
        text.setDefaultTextColor(QColor("#888888"))
        font = QFont("Arial", 14)
        text.setFont(font)
        self._scene.addItem(text)
        # Center the text at origin
        text.setPos(-text.boundingRect().width() / 2,
                    -text.boundingRect().height() / 2)

    # ------------------------------------------------------------------
    # ZOOM CONTROLS
    # ------------------------------------------------------------------
    def zoom_in(self):
        self.scale(self.ZOOM_FACTOR, self.ZOOM_FACTOR)

    def zoom_out(self):
        self.scale(1 / self.ZOOM_FACTOR, 1 / self.ZOOM_FACTOR)

    def reset_view(self):
        """Reset zoom and pan to the default state."""
        self.resetTransform()
        self.fitInView(self._scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    # ------------------------------------------------------------------
    # MOUSE WHEEL ZOOM
    # Overrides the default wheel behavior to zoom instead of scroll
    # ------------------------------------------------------------------
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()