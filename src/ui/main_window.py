"""
Main application window for ScrcpyUltimateLink.

Assembles all tabs, menu bar, status bar, and system tray.
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
)

from src.config import AppConfig
from src.constants import APP_NAME, APP_VERSION, ConnectionState
from src.logger import get_logger
from src.networking import adb
from src.transfer.tcp_server import TCPFileServer
from src.ui.about_tab import AboutTab
from src.ui.mirror_tab import MirrorTab
from src.ui.settings_tab import SettingsTab
from src.ui.transfer_tab import TransferTab
from src.ui.styles import STYLESHEET

log = get_logger(__name__)


class MainWindow(QMainWindow):
    """The main application window with tabbed interface."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._build_window()
        self._build_menubar()
        self._build_statusbar()
        self._build_tabs()
        self._start_services()

    def _build_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(QSize(800, 600))

        # Restore saved window geometry
        w = self._config.get("window_width", 950)
        h = self._config.get("window_height", 720)
        x = self._config.get("window_x", -1)
        y = self._config.get("window_y", -1)
        self.resize(w, h)
        if x >= 0 and y >= 0:
            self.move(x, y)

        # Apply global stylesheet
        self.setStyleSheet(STYLESHEET)

    def _build_menubar(self) -> None:
        """Build the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        quit_action = QAction("Exit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_statusbar(self) -> None:
        """Build the status bar."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        self._conn_indicator = QLabel("\U0001f534  Disconnected")
        self._statusbar.addPermanentWidget(self._conn_indicator)

    def _build_tabs(self) -> None:
        """Build all tab widgets."""
        self._tabs = QTabWidget()

        self._mirror_tab = MirrorTab(self._config)
        self._mirror_tab.connection_state_changed.connect(self._on_connection_state)

        self._transfer_tab = TransferTab(
            self._config,
            get_phone_ip=lambda: self._mirror_tab.phone_ip,
        )

        self._settings_tab = SettingsTab(self._config)
        self._about_tab = AboutTab(self._config)

        self._tabs.addTab(self._mirror_tab, "\U0001f4f1  Mirror Phone")
        self._tabs.addTab(self._transfer_tab, "\U0001f4e4  File Transfer")
        self._tabs.addTab(self._settings_tab, "\u2699  Settings")
        self._tabs.addTab(self._about_tab, "\u2753  About")

        self.setCentralWidget(self._tabs)

    def _start_services(self) -> None:
        """Start background network services."""
        self._file_server = TCPFileServer(
            port=self._config.get("tcp_transfer_port", 5558),
            save_dir=self._config.screenshot_directory(),
        )
        self._file_server.start()
        log.info("Application started — TCP file server active")

    # ── Signal Handlers ───────────────────────────────────────────────────

    def _on_connection_state(self, state: str) -> None:
        """Update status bar based on connection state."""
        indicators = {
            ConnectionState.DISCONNECTED: "\U0001f534  Disconnected",
            ConnectionState.DISCOVERING: "\U0001f7e1  Discovering...",
            ConnectionState.CONNECTING: "\U0001f7e1  Connecting...",
            ConnectionState.CONNECTED: "\U0001f7e2  Connected",
            ConnectionState.MIRRORING: "\U0001f7e2  Mirroring",
            ConnectionState.ERROR: "\U0001f534  Connection Error",
        }
        self._conn_indicator.setText(
            indicators.get(state, f"\u2753  {state}")
        )

    # ── Dialogs ───────────────────────────────────────────────────────────

    def _show_about(self) -> None:
        """Switch to the About tab."""
        for i in range(self._tabs.count()):
            if isinstance(self._tabs.widget(i), AboutTab):
                self._tabs.setCurrentIndex(i)
                break

    # ── Window Events ─────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close — confirm if connected, save geometry."""
        if self._mirror_tab.is_connected:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "A device is still connected. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        # Save window geometry
        self._config.update({
            "window_width": self.width(),
            "window_height": self.height(),
            "window_x": self.x(),
            "window_y": self.y(),
        })

        # Cleanup
        self._mirror_tab.cleanup()
        self._file_server.stop()
        adb.stop_scrcpy()
        adb.disconnect_all(self._config)
        log.info("Application closed")

        event.accept()

    def keyPressEvent(self, event) -> None:
        """Handle global keyboard shortcuts."""
        if event.key() == Qt.Key.Key_F5:
            self._mirror_tab._refresh_dashboard()
        else:
            super().keyPressEvent(event)
