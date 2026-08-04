"""
File Transfer tab for ScrcpyUltimateLink.

Two sub-tabs:
- Push to Phone: drag-drop + send
- Pull from Phone: browse remote files + download
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import AppConfig
from src.constants import (
    DEFAULT_TCP_TRANSFER_PORT,
    format_size,
    get_file_icon,
)
from src.logger import get_logger
from src.transfer.tcp_client import TCPFileClient
from src.ui.widgets.drop_zone import DropZone
from src.ui.animations import AnimatedButton
from src.ui.widgets.section_card import SectionCard

log = get_logger(__name__)


class TransferTab(QWidget):
    """File transfer tab with push and pull sub-tabs."""

    def __init__(self, config: AppConfig, get_phone_ip: callable) -> None:
        super().__init__()
        self._config = config
        self._get_phone_ip = get_phone_ip
        self._tcp_client = TCPFileClient(
            port=config.get("tcp_transfer_port", DEFAULT_TCP_TRANSFER_PORT),
        )
        self._selected_file: str | None = None

        layout = QVBoxLayout(self)

        # Sub-tabs
        sub_tabs = QTabWidget()
        sub_tabs.addTab(self._build_push_tab(), "\u2b06  Push to Phone")
        sub_tabs.addTab(self._build_pull_tab(), "\u2b07  Pull from Phone")
        layout.addWidget(sub_tabs)

    # ── Push Tab ──────────────────────────────────────────────────────────

    def _build_push_tab(self) -> QWidget:
        """Build the Push to Phone sub-tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        # Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        layout.addWidget(self._drop_zone)

        # File info
        self._push_info = QLabel("No file selected")
        self._push_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._push_info.setObjectName("subtitle")
        layout.addWidget(self._push_info)

        # Progress group
        push_progress_group = SectionCard("Transfer Progress")
        pp_layout = QVBoxLayout()

        self._push_progress = QProgressBar()
        self._push_progress.setRange(0, 100)
        self._push_progress.setValue(0)
        pp_layout.addWidget(self._push_progress)

        self._push_speed_label = QLabel("")
        self._push_speed_label.setObjectName("subtitle")
        pp_layout.addWidget(self._push_speed_label)
        push_progress_group.addLayout(pp_layout)
        layout.addWidget(push_progress_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self._send_btn = AnimatedButton("\U0001f680  Send File")
        self._send_btn.setObjectName("action-primary")
        self._send_btn.setEnabled(False)
        self._send_btn.clicked.connect(self._send_file)

        self._cancel_push_btn = AnimatedButton("\u274c  Cancel")
        self._cancel_push_btn.setObjectName("action-danger")
        self._cancel_push_btn.setEnabled(False)
        self._cancel_push_btn.clicked.connect(self._cancel_send)

        btn_layout.addWidget(self._send_btn)
        btn_layout.addWidget(self._cancel_push_btn)
        layout.addLayout(btn_layout)

        # Status
        self._push_status = QLabel("")
        self._push_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._push_status)

        layout.addStretch()

        # Connect client signals
        self._tcp_client.progress_updated.connect(self._on_push_progress)
        self._tcp_client.transfer_finished.connect(self._on_push_finished)

        return tab

    # ── Pull Tab ──────────────────────────────────────────────────────────

    def _build_pull_tab(self) -> QWidget:
        """Build the Pull from Phone sub-tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        # Controls
        ctrl_layout = QHBoxLayout()
        refresh_btn = AnimatedButton("\U0001f504  Refresh Remote File List")
        refresh_btn.clicked.connect(self._refresh_file_list)
        ctrl_layout.addWidget(refresh_btn)
        layout.addLayout(ctrl_layout)

        # File list
        self._file_list = QListWidget()
        self._file_list.setMinimumHeight(200)
        # Connect itemClicked ONCE here to avoid stacking callbacks
        self._file_list.itemClicked.connect(self._on_file_list_clicked)
        layout.addWidget(self._file_list)

        # Progress
        pull_progress_group = SectionCard("Download Progress")
        dp_layout = QVBoxLayout()

        self._pull_progress = QProgressBar()
        self._pull_progress.setRange(0, 100)
        self._pull_progress.setValue(0)
        dp_layout.addWidget(self._pull_progress)

        self._pull_speed_label = QLabel("")
        self._pull_speed_label.setObjectName("subtitle")
        dp_layout.addWidget(self._pull_speed_label)
        pull_progress_group.addLayout(dp_layout)
        layout.addWidget(pull_progress_group)

        # Pull button
        btn_layout = QHBoxLayout()
        self._pull_btn = AnimatedButton("\u2b07  Download Selected")
        self._pull_btn.setObjectName("action-primary")
        self._pull_btn.setEnabled(False)
        self._pull_btn.clicked.connect(self._pull_file)

        self._cancel_pull_btn = AnimatedButton("\u274c  Cancel")
        self._cancel_pull_btn.setObjectName("action-danger")
        self._cancel_pull_btn.setEnabled(False)
        self._cancel_pull_btn.clicked.connect(self._cancel_pull)

        btn_layout.addWidget(self._pull_btn)
        btn_layout.addWidget(self._cancel_pull_btn)
        layout.addLayout(btn_layout)

        # Status
        self._pull_status = QLabel("")
        self._pull_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._pull_status)

        layout.addStretch()

        # Connect client signals for pull
        self._tcp_client.file_list_ready.connect(self._on_file_list_ready)

        return tab

    # ── Push Handlers ─────────────────────────────────────────────────────

    def _on_file_selected(self, path: str) -> None:
        self._selected_file = path
        name = os.path.basename(path)
        size = format_size(os.path.getsize(path))
        self._push_info.setText(f"{get_file_icon(name)}  {name}  ({size})")
        self._send_btn.setEnabled(True)

    def _send_file(self) -> None:
        if not self._selected_file:
            return
        ip = self._get_phone_ip()
        if not ip:
            self._push_status.setText("No phone connected.")
            return

        self._push_progress.setValue(0)
        self._push_speed_label.setText("")
        self._push_status.setText("Sending...")
        self._send_btn.setEnabled(False)
        self._cancel_push_btn.setEnabled(True)
        self._tcp_client.send_file(self._selected_file, ip)

    def _cancel_send(self) -> None:
        self._tcp_client.cancel()
        self._cancel_push_btn.setEnabled(False)

    def _on_push_progress(self, percent: int, speed: float, eta: float) -> None:
        self._push_progress.setValue(percent)
        eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta / 60:.1f}m"
        self._push_speed_label.setText(
            f"{speed:.1f} MB/s  |  ETA: {eta_str}  |  {percent}%"
        )

    def _on_push_finished(self, success: bool, message: str) -> None:
        self._push_status.setText(message)
        self._push_status.setObjectName("status" if success else "status-error")
        self._push_status.style().unpolish(self._push_status)
        self._push_status.style().polish(self._push_status)
        self._send_btn.setEnabled(True)
        self._cancel_push_btn.setEnabled(False)

    # ── Pull Handlers ─────────────────────────────────────────────────────

    def _refresh_file_list(self) -> None:
        ip = self._get_phone_ip()
        if not ip:
            self._pull_status.setText("No phone connected.")
            return
        self._pull_status.setText("Loading file list...")
        self._tcp_client.request_file_list(ip)

    def _on_file_list_ready(self, files: list) -> None:
        self._file_list.clear()
        if not files:
            self._pull_status.setText("No files found on phone.")
            return

        for f in files:
            name = f.get("name", "unknown")
            size = format_size(f.get("size", 0))
            icon = get_file_icon(name)
            item = QListWidgetItem(f"{icon}  {name}  ({size})")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._file_list.addItem(item)

        self._pull_status.setText(f"Found {len(files)} files")

    def _on_file_list_clicked(self, item: QListWidgetItem) -> None:
        self._pull_btn.setEnabled(True)

    def _pull_file(self) -> None:
        item = self._file_list.currentItem()
        if not item:
            return
        remote_name = item.data(Qt.ItemDataRole.UserRole)
        ip = self._get_phone_ip()
        if not ip:
            self._pull_status.setText("No phone connected.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", os.path.expanduser(f"~/Downloads/{remote_name}"),
        )
        if not save_path:
            return

        # Create a separate client for pull to avoid signal conflicts
        pull_client = TCPFileClient(
            port=self._config.get("tcp_transfer_port", DEFAULT_TCP_TRANSFER_PORT),
        )
        pull_client.progress_updated.connect(self._on_pull_progress)
        pull_client.transfer_finished.connect(self._on_pull_finished)
        self._cancel_pull_btn.setEnabled(True)
        self._pull_btn.setEnabled(False)
        self._pull_progress.setValue(0)
        self._pull_status.setText("Downloading...")
        pull_client.pull_file(remote_name, ip, save_path)

    def _cancel_pull(self) -> None:
        self._tcp_client.cancel()
        self._cancel_pull_btn.setEnabled(False)

    def _on_pull_progress(self, percent: int, speed: float, eta: float) -> None:
        self._pull_progress.setValue(percent)
        eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta / 60:.1f}m"
        self._pull_speed_label.setText(
            f"{speed:.1f} MB/s  |  ETA: {eta_str}  |  {percent}%"
        )

    def _on_pull_finished(self, success: bool, message: str) -> None:
        self._pull_status.setText(message)
        self._pull_status.setObjectName("status" if success else "status-error")
        self._pull_status.style().unpolish(self._pull_status)
        self._pull_status.style().polish(self._pull_status)
        self._pull_btn.setEnabled(True)
        self._cancel_pull_btn.setEnabled(False)
