"""
Settings tab for ScrcpyUltimateLink.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config import AppConfig
from src.constants import (
    DEFAULT_ADB_PORT,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_HEARTBEAT_PORT,
    DEFAULT_TCP_TRANSFER_PORT,
)
from src.logger import get_logger
from src.ui.animations import AnimatedButton
from src.ui.widgets.section_card import SectionCard

log = get_logger(__name__)


class SettingsTab(QWidget):
    """Application settings with grouped configuration sections."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)

        title = QLabel("\u2699  Settings")
        title.setObjectName("title")
        layout.addWidget(title)

        # ── Network Ports ─────────────────────────────────────────────
        ports_group = SectionCard("\U0001f310  Network Ports")
        ports_layout = QVBoxLayout()

        self._port_widgets: dict[str, QSpinBox] = {}
        port_defs = [
            ("heartbeat_port", "Heartbeat Port (Phone \u2192 PC)", DEFAULT_HEARTBEAT_PORT),
            ("discovery_port", "Discovery Port (PC Broadcast)", DEFAULT_DISCOVERY_PORT),
            ("adb_port", "ADB TCP Port", DEFAULT_ADB_PORT),
            ("tcp_transfer_port", "File Transfer TCP Port", DEFAULT_TCP_TRANSFER_PORT),
        ]

        for key, label_text, default in port_defs:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            spin = QSpinBox()
            spin.setRange(1024, 65535)
            spin.setValue(self._config.get(key, default))
            spin.valueChanged.connect(lambda v, k=key: self._save_port(k, v))
            row.addWidget(spin)
            ports_layout.addLayout(row)
            self._port_widgets[key] = spin

        ports_group.addLayout(ports_layout)
        layout.addWidget(ports_group)

        # ── Binary Paths ──────────────────────────────────────────────
        bins_group = SectionCard("\U0001f527  Binary Paths")
        bins_layout = QVBoxLayout()

        # scrcpy
        scrcpy_row = QHBoxLayout()
        scrcpy_row.addWidget(QLabel("scrcpy Binary:"))
        self._scrcpy_input = QLineEdit(self._config.get("scrcpy_bin", "scrcpy"))
        self._scrcpy_input.textChanged.connect(
            lambda t: self._config.__setitem__("scrcpy_bin", t)
        )
        scrcpy_browse = AnimatedButton("Browse\u2026")
        scrcpy_browse.clicked.connect(
            lambda: self._browse_binary(self._scrcpy_input, "scrcpy_bin")
        )
        scrcpy_row.addWidget(self._scrcpy_input)
        scrcpy_row.addWidget(scrcpy_browse)
        bins_layout.addLayout(scrcpy_row)

        # adb
        adb_row = QHBoxLayout()
        adb_row.addWidget(QLabel("ADB Binary:"))
        self._adb_input = QLineEdit(self._config.get("adb_bin", "adb"))
        self._adb_input.textChanged.connect(
            lambda t: self._config.__setitem__("adb_bin", t)
        )
        adb_browse = AnimatedButton("Browse\u2026")
        adb_browse.clicked.connect(
            lambda: self._browse_binary(self._adb_input, "adb_bin")
        )
        adb_row.addWidget(self._adb_input)
        adb_row.addWidget(adb_browse)
        bins_layout.addLayout(adb_row)

        bins_group.addLayout(bins_layout)
        layout.addWidget(bins_group)

        # ── Directories ───────────────────────────────────────────────
        dirs_group = SectionCard("\U0001f4c2  Directories")
        dirs_layout = QVBoxLayout()

        ss_row = QHBoxLayout()
        ss_row.addWidget(QLabel("Screenshot Save Directory:"))
        self._ss_dir_input = QLineEdit(
            self._config.get("screenshot_dir", "")
        )
        self._ss_dir_input.setPlaceholderText("~/Pictures/ScrcpyUltimateLink/ (default)")
        self._ss_dir_input.textChanged.connect(
            lambda t: self._config.__setitem__("screenshot_dir", t)
        )
        ss_browse = AnimatedButton("Browse\u2026")
        ss_browse.clicked.connect(self._browse_ss_dir)
        ss_row.addWidget(self._ss_dir_input)
        ss_row.addWidget(ss_browse)
        dirs_layout.addLayout(ss_row)
        dirs_group.addLayout(dirs_layout)
        layout.addWidget(dirs_group)

        # ── Reset ─────────────────────────────────────────────────────
        reset_btn = AnimatedButton("\U0001f504  Reset All Settings to Defaults")
        reset_btn.setObjectName("action-danger")
        reset_btn.clicked.connect(self._reset_all)
        layout.addWidget(reset_btn)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _save_port(self, key: str, value: int) -> None:
        self._config[key] = value
        log.debug("Setting %s = %d", key, value)

    def _browse_binary(self, line_edit: QLineEdit, config_key: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {config_key} binary", "",
        )
        if path:
            line_edit.setText(path)
            self._config[config_key] = path

    def _browse_ss_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Screenshot Directory", "",
        )
        if path:
            self._ss_dir_input.setText(path)
            self._config["screenshot_dir"] = path

    def _reset_all(self) -> None:
        self._config.reset()
        # Update UI to reflect defaults
        for key, spin in self._port_widgets.items():
            spin.setValue(self._config.get(key, 5555))
        self._scrcpy_input.setText(self._config.get("scrcpy_bin", "scrcpy"))
        self._adb_input.setText(self._config.get("adb_bin", "adb"))
        self._ss_dir_input.setText("")
        log.info("Settings reset to defaults")
