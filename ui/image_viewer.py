"""
ui/image_viewer.py — Central image display with multi-resolution zoom.

Two-layer design:
  _overview_item (z=0) — always present, full scene, low-res overview
  _tile_item     (z=1) — optional, covers visible area at higher res

When zoomed out:            only overview visible
When zoomed in:             high-res tile drawn on top of overview
When panning (zoomed in):   tile refreshed for new visible area
When zooming out past 64dpp: tile hidden, overview shows through
"""

import numpy as np
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene,
                              QGraphicsPixmapItem, QGraphicsTextItem)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QImage, QPixmap, QTransform


class ImageViewer(QGraphicsView):

    ZOOM_FACTOR = 1.15
    MAX_DATA_PX = 4096

    # args: r0, r1, c0, c1, downsample  — all -1 means "zoomed out"
    zoom_requested = pyqtSignal(int, int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setBackgroundBrush(QColor("#1e1e2e"))
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        self._data_rows       = 0
        self._data_cols       = 0
        self._zoom_level      = 1
        self._last_downsample = 999

        self._overview_item: QGraphicsPixmapItem = None
        self._tile_item:     QGraphicsPixmapItem = None

        self._request_timer = QTimer()
        self._request_timer.setSingleShot(True)
        self._request_timer.timeout.connect(self._on_interaction_settled)

        self._draw_placeholder()

    # ------------------------------------------------------------------
    # PLACEHOLDER
    # ------------------------------------------------------------------
    def _draw_placeholder(self):
        text = QGraphicsTextItem(
            "No image loaded\nUse File → Open to load a SAR dataset"
        )
        text.setDefaultTextColor(QColor("#888888"))
        text.setFont(QFont("Arial", 14))
        self._scene.addItem(text)
        text.setPos(-text.boundingRect().width()  / 2,
                    -text.boundingRect().height() / 2)

    # ------------------------------------------------------------------
    # ARRAY → PIXMAP
    # ------------------------------------------------------------------
    def _to_pixmap(self, array: np.ndarray) -> QPixmap:
        """
        Convert a 2D grayscale OR 3D RGB uint8 numpy array to QPixmap.
        Handles both (rows, cols) and (rows, cols, 3) shapes.
        """
        if array.ndim == 3 and array.shape[2] == 3:
            # RGB
            rows, cols = array.shape[:2]
            array = np.ascontiguousarray(array)
            img = QImage(array.data, cols, rows, cols * 3,
                         QImage.Format_RGB888)
        else:
            # Grayscale
            rows, cols = array.shape
            array = np.ascontiguousarray(array)
            img = QImage(array.data, cols, rows, cols,
                         QImage.Format_Grayscale8)
        return QPixmap.fromImage(img)

    # ------------------------------------------------------------------
    # INITIAL OVERVIEW DISPLAY
    # ------------------------------------------------------------------
    def display_array(self, array: np.ndarray,
                      data_rows: int = 0, data_cols: int = 0):
        """
        Called when a file is first opened or overview is reloaded.
        Scene units == full-res data pixels throughout.
        """
        self._scene.clear()
        self._overview_item   = None
        self._tile_item       = None
        self._zoom_level      = 1
        self._last_downsample = 999

        self._data_rows = data_rows if data_rows > 0 else array.shape[0]
        self._data_cols = data_cols if data_cols > 0 else array.shape[1]

        self._scene.setSceneRect(0, 0, self._data_cols, self._data_rows)

        # Overview — scaled to fill entire scene
        pixmap = self._to_pixmap(array)
        self._overview_item = self._scene.addPixmap(pixmap)
        self._overview_item.setZValue(0)
        sx = self._data_cols / pixmap.width()
        sy = self._data_rows / pixmap.height()
        self._overview_item.setTransform(QTransform.fromScale(sx, sy))

        # Tile item — invisible placeholder, drawn on top
        empty = QPixmap(1, 1)
        empty.fill(Qt.transparent)
        self._tile_item = self._scene.addPixmap(empty)
        self._tile_item.setZValue(1)
        self._tile_item.setVisible(False)

        QTimer.singleShot(50, self.reset_view)

    # ------------------------------------------------------------------
    # HIGH-RES TILE UPDATE
    # ------------------------------------------------------------------
    def update_region(self, array: np.ndarray,
                      row_start: int, row_end: int,
                      col_start: int, col_end: int):
        """
        Place a high-res tile over the overview.
        Each array pixel covers ds x ds scene (data) units.
        """
        if self._tile_item is None:
            return

        ds = max(1, (row_end - row_start) // max(1, array.shape[0]))
        pixmap = self._to_pixmap(array)

        self._tile_item.setPixmap(pixmap)
        self._tile_item.setPos(col_start, row_start)
        self._tile_item.setTransform(QTransform.fromScale(ds, ds))
        self._tile_item.setVisible(True)

        print(f"[viewer] tile placed ds={ds} shape={array.shape} "
              f"pos=({col_start},{row_start})", flush=True)

    def _remove_tile(self):
        """Hide tile — overview shows through."""
        if self._tile_item is not None:
            self._tile_item.setVisible(False)
        self._zoom_level      = 1
        self._last_downsample = 999

    # ------------------------------------------------------------------
    # ZOOM & PAN
    # ------------------------------------------------------------------
    def zoom_in(self):
        self.scale(self.ZOOM_FACTOR, self.ZOOM_FACTOR)
        self._schedule_request()

    def zoom_out(self):
        self.scale(1 / self.ZOOM_FACTOR, 1 / self.ZOOM_FACTOR)
        self._schedule_request()

    def reset_view(self):
        self.resetTransform()
        if self._scene.items():
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._remove_tile()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(self.ZOOM_FACTOR, self.ZOOM_FACTOR)
        else:
            self.scale(1 / self.ZOOM_FACTOR, 1 / self.ZOOM_FACTOR)
        self._schedule_request()

    def mouseMoveEvent(self, event):
        """Refresh tile on pan, but only when zoomed in."""
        super().mouseMoveEvent(event)
        if self._zoom_level > 1:
            self._schedule_request()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._zoom_level == 1 and self._scene.items():
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    # ------------------------------------------------------------------
    # TILE REQUEST LOGIC
    # ------------------------------------------------------------------
    def _schedule_request(self):
        self._request_timer.start(400)

    def _on_interaction_settled(self):
        if self._data_rows == 0:
            return

        visible  = self.mapToScene(self.viewport().rect()).boundingRect()
        vis_cols = max(1, int(visible.width()))
        screen_w = max(1, self.viewport().width())
        dpp      = vis_cols / screen_w

        print(f"[viewer] settled — {dpp:.1f} dpp", flush=True)

        # Resolution ladder
        if dpp < 10:
            desired_level, downsample = 4, 1
        elif dpp < 16:
            desired_level, downsample = 3, 2
        elif dpp < 32:
            desired_level, downsample = 2, 4

        else:
            # Zoomed out — just hide the tile, overview is already there
            if self._tile_item and self._tile_item.isVisible():
                self._remove_tile()
            return

        # Skip if same resolution AND same zoom level (not panning)
        # Always fire if downsample changed (resolution step up or down)
        if (desired_level == self._zoom_level
                and downsample == self._last_downsample
                and not self._request_timer.isActive()):
            return

        self._zoom_level      = desired_level
        self._last_downsample = downsample

        # Visible region in data coords (scene == data coords)
        r0 = max(0, int(visible.top()))
        r1 = min(self._data_rows, int(visible.bottom()))
        c0 = max(0, int(visible.left()))
        c1 = min(self._data_cols, int(visible.right()))

        # Cap to avoid huge requests
        if (r1 - r0) > self.MAX_DATA_PX:
            mid = (r0 + r1) // 2
            r0, r1 = mid - self.MAX_DATA_PX // 2, mid + self.MAX_DATA_PX // 2
        if (c1 - c0) > self.MAX_DATA_PX:
            mid = (c0 + c1) // 2
            c0, c1 = mid - self.MAX_DATA_PX // 2, mid + self.MAX_DATA_PX // 2

        print(f"[viewer] requesting ds={downsample} "
              f"rows={r0}:{r1} cols={c0}:{c1}", flush=True)
        self.zoom_requested.emit(r0, r1, c0, c1, downsample)