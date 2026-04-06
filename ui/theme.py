"""
ui/theme.py — Centralized theme/styling for the SAR GUI.

HOW QSS WORKS:
  QSS is Qt's version of CSS. You write rules like:
      WidgetType { property: value; }
  Qt reads these rules and applies them to matching widgets.

  You can target:
    - Widget types:        QMenuBar { ... }
    - Object names:        QLabel#titleLabel { ... }  (set via setObjectName())
    - States:              QPushButton:hover { ... }
    - Sub-elements:        QDockWidget::title { ... }

HOW WE USE IT:
  We define the full stylesheet as a Python string and call
      app.setStyleSheet(stylesheet)
  once at startup. This applies globally to every widget.
"""


# ── Color palette ──────────────────────────────────────────────────────────────
# Defining colors as constants means you change one line to retheme everything.
# This is the dark theme, modeled after ArcGIS Pro's dark interface.

COLORS = {
    # Backgrounds — from darkest to lightest
    "bg_darkest":   "#1a1a2e",   # app background, image viewer
    "bg_dark":      "#16213e",   # menu bar, tool bar
    "bg_mid":       "#0f3460",   # dock panel titles
    "bg_panel":     "#1e1e2e",   # dock panel body
    "bg_widget":    "#2a2a3e",   # input fields, list items
    "bg_hover":     "#3a3a5e",   # hover state for items
    "bg_selected":  "#0f3460",   # selected item background

    # Text
    "text_primary":  "#e0e0e0",  # main text
    "text_secondary":"#a0a0b0",  # labels, hints
    "text_disabled": "#555566",  # disabled widgets

    # Accent — used for highlights, active elements
    "accent":        "#4fc3f7",  # light blue (NISAR brand-ish)
    "accent_dark":   "#0288d1",  # darker blue for pressed states

    # Borders
    "border":        "#2a2a4a",  # subtle borders
    "border_light":  "#3a3a5a",  # slightly more visible borders

    # Status colors
    "success":       "#66bb6a",
    "warning":       "#ffa726",
    "error":         "#ef5350",
}


# ── The full QSS stylesheet ────────────────────────────────────────────────────
# Each section is commented so you know exactly what it controls.

DARK_STYLESHEET = f"""

/* ── MAIN WINDOW & GENERAL ─────────────────────────────────────── */

QMainWindow {{
    background-color: {COLORS['bg_darkest']};
}}

/* QWidget is the base class — this sets defaults for everything */
QWidget {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['text_primary']};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}


/* ── MENU BAR ───────────────────────────────────────────────────── */
/*
   QMenuBar        = the top bar containing "File  Tools  View  Help"
   QMenuBar::item  = each individual top-level word in the bar
*/

QMenuBar {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 2px 0px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    background: transparent;
    border-radius: 3px;
}}

QMenuBar::item:selected {{           /* hover over a top-level menu name */
    background-color: {COLORS['bg_hover']};
}}

QMenuBar::item:pressed {{            /* clicking a top-level menu name */
    background-color: {COLORS['bg_selected']};
}}


/* ── DROP-DOWN MENUS ────────────────────────────────────────────── */
/*
   QMenu       = the dropdown that appears when you click "File" etc.
   QMenu::item = each row inside the dropdown
*/

QMenu {{
    background-color: {COLORS['bg_widget']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 4px;
    padding: 4px 0px;
}}

QMenu::item {{
    padding: 6px 28px 6px 16px;    /* top right bottom left */
}}

QMenu::item:selected {{
    background-color: {COLORS['bg_selected']};
    color: {COLORS['accent']};
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 4px 8px;
}}


/* ── DOCK WIDGETS (the left/right panels) ───────────────────────── */
/*
   QDockWidget         = the whole panel container
   QDockWidget::title  = the title bar at the top of the panel
*/

QDockWidget {{
    color: {COLORS['text_primary']};
    titlebar-close-icon: none;
}}

QDockWidget::title {{
    background-color: {COLORS['bg_mid']};
    padding: 6px 8px;
    font-weight: bold;
    font-size: 12px;
    letter-spacing: 0.5px;
    border-bottom: 1px solid {COLORS['border']};
}}


/* ── TREE WIDGET (the layer list) ───────────────────────────────── */

QTreeWidget {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    outline: none;                  /* removes the dotted focus border */
}}

QTreeWidget::item {{
    padding: 4px 4px;
    border-radius: 3px;
}}

QTreeWidget::item:hover {{
    background-color: {COLORS['bg_hover']};
}}

QTreeWidget::item:selected {{
    background-color: {COLORS['bg_selected']};
    color: {COLORS['accent']};
}}


/* ── LABELS ─────────────────────────────────────────────────────── */

QLabel {{
    background: transparent;        /* labels shouldn't have a background box */
    color: {COLORS['text_primary']};
}}


/* ── BUTTONS ────────────────────────────────────────────────────── */

QPushButton {{
    background-color: {COLORS['bg_widget']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 64px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['accent']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent_dark']};
    color: #ffffff;
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['text_disabled']};
    border-color: {COLORS['border']};
}}

/* A special "primary action" button style —
   apply it with: button.setObjectName("primaryButton") */
QPushButton#primaryButton {{
    background-color: {COLORS['accent_dark']};
    color: #ffffff;
    font-weight: bold;
    border: none;
}}

QPushButton#primaryButton:hover {{
    background-color: {COLORS['accent']};
}}


/* ── INPUT FIELDS ───────────────────────────────────────────────── */

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['bg_widget']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {COLORS['accent_dark']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['accent']};   /* blue outline when active */
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{          /* the dropdown list of a combobox */
    background-color: {COLORS['bg_widget']};
    selection-background-color: {COLORS['bg_selected']};
    border: 1px solid {COLORS['border_light']};
}}


/* ── SCROLL BARS ────────────────────────────────────────────────── */
/*
   Scroll bars have many sub-elements. The key ones:
   ::handle  = the draggable part
   ::add-line / ::sub-line = the arrow buttons at each end (we hide them)
*/

QScrollBar:vertical {{
    background: {COLORS['bg_panel']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['bg_hover']};
    min-height: 24px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent_dark']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;                    /* hide the arrow buttons */
}}

QScrollBar:horizontal {{
    background: {COLORS['bg_panel']};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS['bg_hover']};
    min-width: 24px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS['accent_dark']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}


/* ── STATUS BAR ─────────────────────────────────────────────────── */

QStatusBar {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
    font-size: 11px;
    padding: 2px 8px;
}}


/* ── PROGRESS BAR (we'll use this later for processing) ─────────── */

QProgressBar {{
    background-color: {COLORS['bg_widget']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    color: {COLORS['text_primary']};
    height: 16px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_dark']};
    border-radius: 3px;
}}


/* ── SPLITTER (the divider between panels) ──────────────────────── */

QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:hover {{
    background-color: {COLORS['accent']};
}}

"""


# ── Light theme (minimal for now — can be expanded later) ─────────────────────

LIGHT_STYLESHEET = """
QWidget {
    background-color: #f5f5f5;
    color: #1a1a1a;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QMenuBar {
    background-color: #e8e8e8;
    border-bottom: 1px solid #cccccc;
}
QDockWidget::title {
    background-color: #dcdcdc;
    padding: 6px 8px;
    font-weight: bold;
}
QStatusBar {
    background-color: #e8e8e8;
    border-top: 1px solid #cccccc;
}
"""


# ── Public function called from main.py ───────────────────────────────────────

def apply_theme(app, theme: str = "dark"):
    """
    Apply a theme to the entire application.

    Usage:
        from ui.theme import apply_theme
        apply_theme(app, "dark")   # or "light"

    Args:
        app   : the QApplication instance
        theme : "dark" or "light"
    """
    if theme == "dark":
        app.setStyleSheet(DARK_STYLESHEET)
    elif theme == "light":
        app.setStyleSheet(LIGHT_STYLESHEET)
    else:
        raise ValueError(f"Unknown theme '{theme}'. Use 'dark' or 'light'.")