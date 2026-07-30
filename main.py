"""Shard - launcher."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from shard import APP_NAME, __version__
from shard.main_window import MainWindow


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)  # the tray icon may keep the app alive

    window = MainWindow()  # applies the saved theme to the QApplication
    if not window.prefs.start_minimized:
        window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
