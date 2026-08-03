"""
Application entry point for ScrcpyUltimateLink.

Sets up logging, config, exception handling, and launches the GUI.
"""

from __future__ import annotations

import sys
import traceback

from src.config import AppConfig
from src.constants import APP_NAME, LOG_FILE
from src.logger import configure as configure_logging, get_logger


def _install_exception_hook() -> None:
    """Install a global exception hook to log unhandled crashes."""
    log = get_logger("crash")

    def hook(exc_type, exc_value, exc_tb):
        log.critical(
            "Unhandled exception:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


def main() -> int:
    """Launch the ScrcpyUltimateLink application."""
    # 1. Load config
    config = AppConfig()

    # 2. Configure logging
    configure_logging(
        log_file=config.get("log_file", LOG_FILE),
        file_logging=config.get("logging_enabled", True),
    )

    # 3. Install crash handler
    _install_exception_hook()

    log = get_logger("app")
    log.info("Starting %s", APP_NAME)

    # 4. Create Qt application
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # 5. Create and show main window
    from src.ui.main_window import MainWindow
    window = MainWindow(config)
    window.show()

    log.info("GUI ready")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
