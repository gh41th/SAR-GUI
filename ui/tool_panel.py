"""
ui/tool_panel.py — Right dock panel for tool parameter controls.

Uses QStackedWidget to swap between different tool UIs.
Think of it as a deck of cards — only one card is visible at a time,
and we flip to the right one when a tool is selected.
"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout,
    QStackedWidget, QLabel
)


class ToolPanel(QDockWidget):

    def __init__(self, parent=None):
        super().__init__("Tool Controls", parent)
        self.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
        )
        self.setMinimumWidth(220)

        # Map tool names → their page index in the stack
        self._tool_index: dict[str, int] = {}

        self._build_ui()

    def _build_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self.title_label = QLabel("No tool selected")
        self.title_label.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self.title_label)

        # QStackedWidget holds multiple pages; only one is shown at a time
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Page 0 — default empty page
        empty_page = QLabel("Select a tool from the\nTools menu to begin.")
        empty_page.setWordWrap(True)
        empty_page.setStyleSheet("color: #888; padding: 8px;")
        self.stack.addWidget(empty_page)

        # Register the placeholder tools
        # Later, these will be replaced with real parameter widgets
        for tool_name in ["Boxcar Filter", "Coherency Matrix", "Covariance Matrix"]:
            page = self._make_placeholder_page(tool_name)
            idx = self.stack.addWidget(page)
            self._tool_index[tool_name] = idx

        self.setWidget(container)

    def _make_placeholder_page(self, tool_name: str) -> QWidget:
        """Creates a simple placeholder page for a tool."""
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(f"Parameters for:\n{tool_name}\n\n(coming soon)")
        label.setWordWrap(True)
        label.setStyleSheet("padding: 8px; color: #555;")
        layout.addWidget(label)
        layout.addStretch()   # pushes content to the top
        return page

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------
    def show_tool(self, tool_name: str):
        """Switch the stack to show the given tool's parameter page."""
        self.title_label.setText(tool_name)
        idx = self._tool_index.get(tool_name, 0)
        self.stack.setCurrentIndex(idx)