"""
main.py — Entry point for the NISAR SAR Tools GUI
Run this file to launch the application.
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import apply_theme


def main():
    # Every PyQt app needs one QApplication instance.
    # sys.argv lets Qt handle command-line arguments (you can ignore this for now).
    app = QApplication(sys.argv)

    # Set a global application style. "Fusion" is the best base for custom QSS.
    # Always set this BEFORE applying a stylesheet.
    app.setStyle("Fusion")

    # Apply our custom dark theme (defined in ui/theme.py)
    apply_theme(app, "light")

    # Create and show the main window
    window = MainWindow()
    window.show()

    # Start the event loop — this keeps the app running and responsive.
    # sys.exit ensures a clean exit code when the window is closed.
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()