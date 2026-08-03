"""
Mirror Phone tab — the primary interface for ScrcpyUltimateLink.

Handles device discovery, connection, scrcpy launch, remote control,
hardware dashboard, clipboard sync, and screen capture.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import timedelta

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config import AppConfig
from src.constants import (
    APP_NAME,
    APP_VERSION,
    DASHBOARD_REFRESH_SEC,
    DEFAULT_ADB_PORT,
    ConnectionState,
    KEYCODE_BACK,
    KEYCODE_HOME,
    KEYCODE_POWER,
    KEYCODE_RECENTS,
    KEYCODE_SCREEN_OFF,
    KEYCODE_VOLUME_DOWN,
    KEYCODE_VOLUME_UP,
    SCRCPY_PRESETS,
)
from src.logger import get_logger
from src.networking import adb, heartbeat, latency, scanner
from src.ui.widgets.dashboard import DashboardWidget
from src.ui.widgets.log_panel import LogPanel

log = get_logger(__name__)


class MirrorTab(QWidget):
    """Main mirror phone tab with connection, controls, and dashboard."""

    connection_state_changed = pyqtSignal(str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._phone_ip: str | None = None
        self._adb_port: int = config.get("adb_port", DEFAULT_ADB_PORT)
        self._connected = False
        self._connect_time: float | None = None
        self._dashboard_timer: QTimer | None = None
        self._duration_timer: QTimer | None = None

        # Initialize networking components
        self._heartbeat = heartbeat.HeartbeatListener(config)
        self._broadcaster = heartbeat.DiscoveryBroadcaster(config)
        self._scanner = scanner.SubnetScanner(config)

        # Build UI
        self._build_ui()

        # Connect signals
        self._heartbeat.heartbeat_received.connect(self._on_heartbeat)
        self._heartbeat.state_changed.connect(self._on_state_changed)
        self._scanner.device_found.connect(self._on_device_found)
        self._scanner.scan_complete.connect(self._on_scan_complete)

    def _build_ui(self) -> None:
        """Construct the tab layout."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(14)

        # ── Header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel(f"{APP_NAME} v{APP_VERSION}")
        title.setObjectName("title")
        local_ip = heartbeat.get_local_ip()
        ip_label = QLabel(f"\U0001f4e1  PC IP: {local_ip}")
        ip_label.setObjectName("subtitle")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(ip_label)
        main_layout.addLayout(header)

        # ── Status ──────────────────────────────────────────────────────
        status_layout = QHBoxLayout()
        self._status_label = QLabel("\U0001f534  Disconnected")
        self._status_label.setObjectName("status")
        self._duration_label = QLabel("")
        self._duration_label.setObjectName("subtitle")
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()
        status_layout.addWidget(self._duration_label)
        main_layout.addLayout(status_layout)

        # ── Connection Buttons ──────────────────────────────────────────
        conn_group = QGroupBox("\U0001f50c  Connection")
        conn_layout = QHBoxLayout(conn_group)

        self._auto_btn = QPushButton("\U0001f4e1  Auto-Discover (Heartbeat)")
        self._auto_btn.setObjectName("action-primary")
        self._auto_btn.clicked.connect(self._start_auto_discover)

        self._saved_btn = QPushButton("\U0001f4be  Connect Saved IP")
        self._saved_btn.clicked.connect(self._connect_saved_ip)

        self._scan_btn = QPushButton("\U0001f50d  Subnet Scan")
        self._scan_btn.clicked.connect(self._start_subnet_scan)

        self._disconnect_btn = QPushButton("\u274c  Disconnect")
        self._disconnect_btn.setObjectName("action-danger")
        self._disconnect_btn.clicked.connect(self._disconnect)
        self._disconnect_btn.setEnabled(False)

        conn_layout.addWidget(self._auto_btn)
        conn_layout.addWidget(self._saved_btn)
        conn_layout.addWidget(self._scan_btn)
        conn_layout.addWidget(self._disconnect_btn)
        main_layout.addWidget(conn_group)

        # ── Scrcpy Preset ──────────────────────────────────────────────
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Video Quality:"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(SCRCPY_PRESETS.keys())
        saved_preset = self._config.get("scrcpy_preset", "Balanced (Default)")
        idx = self._preset_combo.findText(saved_preset)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self._preset_combo)
        main_layout.addLayout(preset_layout)

        # ── Clipboard Sync ─────────────────────────────────────────────
        clip_group = QGroupBox("\U0001f4cb  Clipboard Sync")
        clip_layout = QHBoxLayout(clip_group)
        self._auto_clip_cb = QCheckBox("Auto Sync")
        self._auto_clip_cb.setChecked(self._config.get("auto_clip_sync", False))
        self._auto_clip_cb.toggled.connect(
            lambda v: self._config.__setitem__("auto_clip_sync", v)
        )
        push_clip_btn = QPushButton("\u2b06  Push to Phone")
        push_clip_btn.clicked.connect(self._push_clipboard)
        pull_clip_btn = QPushButton("\u2b07  Pull from Phone")
        pull_clip_btn.clicked.connect(self._pull_clipboard)
        clip_layout.addWidget(self._auto_clip_cb)
        clip_layout.addWidget(push_clip_btn)
        clip_layout.addWidget(pull_clip_btn)
        main_layout.addWidget(clip_group)

        # ── Remote Control ─────────────────────────────────────────────
        ctrl_group = QGroupBox("\U0001f3ae  Remote Control")
        ctrl_main = QVBoxLayout(ctrl_group)

        # Navigation row
        nav_layout = QHBoxLayout()
        for label, keycode in [
            ("\u2b60  Back", KEYCODE_BACK),
            ("\u2302  Home", KEYCODE_HOME),
            ("\u25a1  Recents", KEYCODE_RECENTS),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("control-btn")
            btn.clicked.connect(lambda _, k=keycode: self._send_key(k))
            nav_layout.addWidget(btn)
        ctrl_main.addLayout(nav_layout)

        # Media + power row
        media_layout = QHBoxLayout()
        for label, keycode in [
            ("\U0001f50a  Vol+", KEYCODE_VOLUME_UP),
            ("\U0001f509  Vol\u2212", KEYCODE_VOLUME_DOWN),
            ("\u23fb  Power", KEYCODE_POWER),
            ("\U0001f4f4  Screen Off", KEYCODE_SCREEN_OFF),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("control-btn")
            btn.clicked.connect(lambda _, k=keycode: self._send_key(k))
            media_layout.addWidget(btn)
        ctrl_main.addLayout(media_layout)

        # Custom keycode row
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Custom Key:"))
        self._custom_key_input = QSpinBox()
        self._custom_key_input.setRange(0, 999)
        self._custom_key_input.setToolTip("Enter Android keycode number")
        custom_key_btn = QPushButton("Send Key")
        custom_key_btn.clicked.connect(self._send_custom_key)
        custom_layout.addWidget(self._custom_key_input)
        custom_layout.addWidget(custom_key_btn)
        ctrl_main.addLayout(custom_layout)

        main_layout.addWidget(ctrl_group)

        # ── Screen Capture ─────────────────────────────────────────────
        capture_group = QGroupBox("\U0001f4f8  Screen Capture")
        capture_layout = QHBoxLayout(capture_group)
        screenshot_btn = QPushButton("\U0001f4f7  Take Screenshot")
        screenshot_btn.clicked.connect(self._take_screenshot)
        capture_layout.addWidget(screenshot_btn)
        main_layout.addWidget(capture_group)

        # ── Open URL on Phone ──────────────────────────────────────────
        url_group = QGroupBox("\U0001f310  Open URL on Phone")
        url_layout = QHBoxLayout(url_group)
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com")
        url_btn = QPushButton("Open")
        url_btn.clicked.connect(self._open_url)
        url_layout.addWidget(self._url_input)
        url_layout.addWidget(url_btn)
        main_layout.addWidget(url_group)

        # ── Hardware Dashboard ─────────────────────────────────────────
        self._dashboard = DashboardWidget()
        self._dashboard.refresh_btn.clicked.connect(self._refresh_dashboard)
        main_layout.addWidget(self._dashboard)

        # ── Log Panel ──────────────────────────────────────────────────
        self._log_panel = LogPanel()
        main_layout.addWidget(self._log_panel)

        # Final layout
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Connection Handlers ───────────────────────────────────────────────

    def _start_auto_discover(self) -> None:
        """Start heartbeat listener + discovery broadcaster."""
        self._update_status("\U0001f7e1  Discovering...", "status-warning")
        self._heartbeat.start()
        self._broadcaster.start()
        log.info("Auto-discovery started")

    def _connect_saved_ip(self) -> None:
        """Try connecting to the last known phone IP."""
        saved_ip = self._config.get("last_phone_ip", "")
        if not saved_ip:
            log.warning("No saved phone IP found")
            self._update_status("\U0001f534  No saved IP", "status-error")
            return
        self._update_status(f"\U0001f7e1  Connecting to {saved_ip}...", "status-warning")
        port = self._config.get("last_phone_port", DEFAULT_ADB_PORT)
        threading.Thread(
            target=self._connect_worker, args=(saved_ip, port),
            daemon=True,
        ).start()

    def _start_subnet_scan(self) -> None:
        """Launch a subnet scan."""
        self._update_status("\U0001f7e1  Scanning subnet...", "status-warning")
        self._scan_btn.setEnabled(False)
        self._scanner.start_scan()

    def _disconnect(self) -> None:
        """Disconnect from the phone."""
        adb.stop_scrcpy()
        if self._phone_ip:
            adb.disconnect(self._config, self._phone_ip, self._adb_port)
        self._set_disconnected()
        log.info("Disconnected from phone")

    # ── Signal Handlers ───────────────────────────────────────────────────

    def _on_heartbeat(self, ip: str, port: int) -> None:
        """Handle incoming heartbeat — connect and launch."""
        self._connect_worker(ip, port)

    def _on_state_changed(self, state: str) -> None:
        """Handle connection state changes from heartbeat listener."""
        self.connection_state_changed.emit(state)

    def _on_device_found(self, ip: str) -> None:
        """Handle subnet scan finding a device."""
        threading.Thread(
            target=self._connect_worker,
            args=(ip, self._config.get("adb_port", DEFAULT_ADB_PORT)),
            daemon=True,
        ).start()

    def _on_scan_complete(self, result: str | None) -> None:
        """Handle subnet scan completion."""
        self._scan_btn.setEnabled(True)
        if result is None:
            self._update_status("\U0001f534  No devices found on subnet", "status-error")

    # ── Workers ───────────────────────────────────────────────────────────

    def _connect_worker(self, ip: str, port: int) -> None:
        """Connect to phone and launch scrcpy (runs in background thread)."""
        preset_name = self._preset_combo.currentText()
        extra_args = SCRCPY_PRESETS.get(preset_name, [])

        success, msg = adb.launch_scrcpy(self._config, ip, port, extra_args)

        if success:
            QTimer.singleShot(0, lambda: self._set_connected(ip, port))
        else:
            QTimer.singleShot(
                0, lambda: self._update_status(f"\U0001f534  {msg}", "status-error")
            )

    # ── UI State ──────────────────────────────────────────────────────────

    def _set_connected(self, ip: str, port: int) -> None:
        """Update UI to connected state."""
        self._phone_ip = ip
        self._adb_port = port
        self._connected = True
        self._connect_time = time.time()
        self._update_status(
            f"\U0001f7e2  Connected to {ip}:{port} | scrcpy running", "status"
        )
        self._disconnect_btn.setEnabled(True)
        self._auto_btn.setEnabled(False)
        self._saved_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self.connection_state_changed.emit(ConnectionState.MIRRORING)
        self._start_dashboard_timer()
        self._start_duration_timer()
        log.info("Connected and mirroring: %s:%d", ip, port)

    def _set_disconnected(self) -> None:
        """Update UI to disconnected state."""
        self._phone_ip = None
        self._connected = False
        self._connect_time = None
        self._update_status("\U0001f534  Disconnected", "status-error")
        self._duration_label.setText("")
        self._disconnect_btn.setEnabled(False)
        self._auto_btn.setEnabled(True)
        self._saved_btn.setEnabled(True)
        self._scan_btn.setEnabled(True)
        self._dashboard.reset()
        self._stop_dashboard_timer()
        self._stop_duration_timer()
        self.connection_state_changed.emit(ConnectionState.DISCONNECTED)

    def _update_status(self, text: str, obj_name: str = "status") -> None:
        self._status_label.setText(text)
        self._status_label.setObjectName(obj_name)
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    # ── Dashboard ─────────────────────────────────────────────────────────

    def _start_dashboard_timer(self) -> None:
        if self._dashboard_timer is None:
            self._dashboard_timer = QTimer()
            self._dashboard_timer.timeout.connect(self._refresh_dashboard)
        self._dashboard_timer.start(int(DASHBOARD_REFRESH_SEC * 1000))
        self._refresh_dashboard()  # immediate first refresh

    def _stop_dashboard_timer(self) -> None:
        if self._dashboard_timer:
            self._dashboard_timer.stop()

    def _refresh_dashboard(self) -> None:
        """Refresh hardware info (only when connected)."""
        if not self._connected or not self._phone_ip:
            return

        def worker() -> None:
            info = adb.get_hardware_info(
                self._config, self._phone_ip, self._adb_port
            )
            lat, _ = latency.measure_latency(self._phone_ip, self._adb_port)
            QTimer.singleShot(0, lambda: self._dashboard.update_info(info))
            QTimer.singleShot(0, lambda: self._dashboard.update_latency(lat))

        threading.Thread(target=worker, daemon=True).start()

    # ── Duration Timer ────────────────────────────────────────────────────

    def _start_duration_timer(self) -> None:
        if self._duration_timer is None:
            self._duration_timer = QTimer()
            self._duration_timer.timeout.connect(self._update_duration)
        self._duration_timer.start(1000)

    def _stop_duration_timer(self) -> None:
        if self._duration_timer:
            self._duration_timer.stop()

    def _update_duration(self) -> None:
        if self._connect_time:
            elapsed = int(time.time() - self._connect_time)
            td = str(timedelta(seconds=elapsed))
            self._duration_label.setText(f"\u23f1  Connected for {td}")

    # ── Remote Control ────────────────────────────────────────────────────

    def _send_key(self, keycode: int) -> None:
        if not self._phone_ip:
            return
        threading.Thread(
            target=lambda: adb.send_keyevent(
                self._config, keycode, self._phone_ip, self._adb_port,
            ),
            daemon=True,
        ).start()

    def _send_custom_key(self) -> None:
        code = self._custom_key_input.value()
        self._send_key(code)

    # ── Clipboard ─────────────────────────────────────────────────────────

    def _push_clipboard(self) -> None:
        if not self._phone_ip:
            return
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            text = clipboard.text()
            if text:
                threading.Thread(
                    target=lambda: adb.send_broadcast(
                        self._config,
                        "org.henry.scrcpy.SET_CLIPBOARD",
                        {"text": text},
                        self._phone_ip, self._adb_port,
                    ),
                    daemon=True,
                ).start()

    def _pull_clipboard(self) -> None:
        if not self._phone_ip:
            return
        threading.Thread(
            target=lambda: adb.send_broadcast(
                self._config,
                "org.henry.scrcpy.GET_CLIPBOARD",
                phone_ip=self._phone_ip, adb_port=self._adb_port,
            ),
            daemon=True,
        ).start()

    # ── Screen Capture ────────────────────────────────────────────────────

    def _take_screenshot(self) -> None:
        if not self._phone_ip:
            return
        save_dir = self._config.screenshot_directory()
        filename = f"screenshot_{int(time.time())}.png"
        save_path = os.path.join(save_dir, filename)

        def worker() -> None:
            ok, msg = adb.take_screenshot(
                self._config, save_path, self._phone_ip, self._adb_port,
            )
            if ok:
                log.info("Screenshot: %s", save_path)
            else:
                log.error("Screenshot failed: %s", msg)

        threading.Thread(target=worker, daemon=True).start()

    # ── Open URL ──────────────────────────────────────────────────────────

    def _open_url(self) -> None:
        url = self._url_input.text().strip()
        if not url or not self._phone_ip:
            return
        threading.Thread(
            target=lambda: adb.open_url(
                self._config, url, self._phone_ip, self._adb_port,
            ),
            daemon=True,
        ).start()

    # ── Preset ────────────────────────────────────────────────────────────

    def _on_preset_changed(self, text: str) -> None:
        self._config["scrcpy_preset"] = text

    # ── Cleanup ───────────────────────────────────────────────────────────

    def cleanup(self) -> None:
        """Stop all background services."""
        self._heartbeat.stop()
        self._broadcaster.stop()
        self._scanner.cancel()
        self._stop_dashboard_timer()
        self._stop_duration_timer()

    @property
    def phone_ip(self) -> str | None:
        return self._phone_ip

    @property
    def is_connected(self) -> bool:
        return self._connected
