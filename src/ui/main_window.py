"""
Main application window for ScrcpyUltimateLink.

Assembles all tabs, menu bar, status bar with heartbeat indicator,
and system tray. Features animated tab transitions.
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QStackedWidget,
    QListWidget,
    QVBoxLayout,
    QWidget,
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
from src.ui.widgets.heartbeat_indicator import HeartbeatIndicator

log = get_logger(__name__)


class MainWindow(QMainWindow):
    """The main application window with tabbed interface."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._build_window()
        self._build_menubar()
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

    # Status bar removed; integrated into sidebar.

    def _build_tabs(self) -> None:
        """Build the sidebar navigation and content stack."""
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        # We use a horizontal layout: Sidebar on left, Stack on right
        layout = QHBoxLayout(self._central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar Container
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(220)
        sidebar_container.setStyleSheet("background-color: #0D0A14;")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(8)
        
        # App Title in Sidebar
        title_lbl = QLabel(f" {APP_NAME}")
        title_lbl.setStyleSheet("color: #F0F0F5; font-size: 16px; font-weight: bold;")
        sidebar_layout.addWidget(title_lbl)
        
        # Sidebar List
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        sidebar_layout.addWidget(self._sidebar)
        
        sidebar_layout.addStretch()
        
        # Connection Status in Sidebar
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(16, 0, 16, 0)
        self._heartbeat = HeartbeatIndicator(size=24)
        self._heartbeat.set_state("disconnected")
        status_layout.addWidget(self._heartbeat)

        self._conn_label = QLabel("Disconnected")
        self._conn_label.setStyleSheet("color: #9CA3AF; font-size: 13px; font-weight: bold;")
        status_layout.addWidget(self._conn_label)
        status_layout.addStretch()
        sidebar_layout.addLayout(status_layout)
        
        layout.addWidget(sidebar_container)

        # Content Stack
        self._stack = QStackedWidget()
        self._stack.setObjectName("content-stack")
        layout.addWidget(self._stack)

        self._mirror_tab = MirrorTab(self._config)
        self._mirror_tab.connection_state_changed.connect(self._on_connection_state)

        self._transfer_tab = TransferTab(
            self._config,
            get_phone_ip=lambda: self._mirror_tab.phone_ip,
        )

        self._settings_tab = SettingsTab(self._config)
        self._about_tab = AboutTab(self._config)

        # Add items to sidebar and stack
        tabs = [
            ("📱  Mirror Phone", self._mirror_tab),
            ("📤  File Transfer", self._transfer_tab),
            ("⚙️  Settings", self._settings_tab),
            ("❓  About", self._about_tab),
        ]
        
        for name, widget in tabs:
            self._sidebar.addItem(name)
            self._stack.addWidget(widget)

        self._sidebar.setCurrentRow(0)

    def _on_sidebar_changed(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

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
        """Update status bar heartbeat indicator and label."""
        self._heartbeat.set_state(state)

        labels = {
            ConnectionState.DISCONNECTED: ("Disconnected", "#9CA3AF"),
            ConnectionState.DISCOVERING: ("Discovering...", "#F59E0B"),
            ConnectionState.CONNECTING: ("Connecting...", "#F59E0B"),
            ConnectionState.CONNECTED: ("Connected", "#10B981"),
            ConnectionState.MIRRORING: ("Mirroring Active", "#10B981"),
            ConnectionState.ERROR: ("Connection Error", "#EF4444"),
        }
        label_text, color = labels.get(state, (state, "#9CA3AF"))
        self._conn_label.setText(label_text)
        self._conn_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

    # ── Dialogs ───────────────────────────────────────────────────────────

    def _show_about(self) -> None:
        """Switch to the About tab."""
        for i in range(self._stack.count()):
            if isinstance(self._stack.widget(i), AboutTab):
                self._sidebar.setCurrentRow(i)
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
