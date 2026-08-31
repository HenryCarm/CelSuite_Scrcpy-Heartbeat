#!/usr/bin/env python3
"""
Scrcpy Cloud Build & Deploy Hub (PySide6)
========================================
Local zero-AI-bandwidth monitor for GitHub Actions builds and one-click ADB deployment.
Author: Henny & Antigravity 💖✨
"""

import sys
import os
import json
import subprocess
import shutil
import re
import argparse
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit,
    QProgressBar, QFrame, QSplitter, QListWidget, QListWidgetItem,
    QMessageBox, QSizePolicy
)

DEFAULT_REPO = "HenryCarm/Scr-Heartbeat-Scrcpy-WiFi-Auto-Launcher"
DEFAULT_PHONE_IP = "10.132.152.85:5555"
PROJECT_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = PROJECT_DIR / "downloaded_artifacts"


class CommandWorker(QThread):
    """Executes shell commands in the background without freezing the GUI."""
    sig_log = Signal(str)
    sig_result = Signal(str, dict)
    sig_error = Signal(str, str)

    def __init__(self, action_id: str, func, *args, **kwargs):
        super().__init__()
        self.action_id = action_id
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.func(self.sig_log.emit, *self.args, **self.kwargs)
            self.sig_result.emit(self.action_id, res if isinstance(res, dict) else {"data": res})
        except Exception as e:
            self.sig_error.emit(self.action_id, str(e))


def run_gh_json(args: list[str]) -> list | dict:
    """Helper to run gh CLI and return parsed JSON."""
    cmd = ["gh"] + args
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        raise RuntimeError(f"GitHub CLI error: {result.stderr.strip() or result.stdout.strip()}")
    text = result.stdout.strip()
    if not text:
        return []
    return json.loads(text)


def extract_smart_error_snippet(full_log: str) -> str:
    """Intelligently parses a failed build log to extract the core compiler/Gradle/Python error."""
    lines = full_log.splitlines()
    error_lines = []
    
    indicators = [
        "FAILURE: Build failed with an exception",
        "BUILD FAILED",
        "* What went wrong:",
        "error: duplicate class",
        "Fatal signal",
        "SIGABRT",
        "Modified UTF-8",
        "ClassNotFoundException",
        "A problem occurred evaluating root project",
        "Execution failed for task",
        "Cython.Compiler.Errors",
        "SyntaxError:",
        "Traceback (most recent call last):",
        "Exception in thread",
        "error: "
    ]

    for i, line in enumerate(lines):
        clean = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', line)
        if any(ind.lower() in clean.lower() for ind in indicators):
            start = max(0, i - 2)
            end = min(len(lines), i + 25)
            context = "\n".join(lines[start:end])
            if context not in error_lines:
                error_lines.append(context)

    if error_lines:
        return "=== 🚨 AUTOMATIC ERROR EXTRACTION ===\n\n" + "\n\n---\n\n".join(error_lines[:3])
    
    return "=== 📋 BUILD LOG TAIL ===\n\n" + "\n".join(lines[-40:])


class BuildMonitorWindow(QMainWindow):
    def __init__(self, is_test_mode=False):
        super().__init__()
        self.is_test_mode = is_test_mode
        self.active_runs = []
        self.selected_run = None
        self.worker = None

        self.setWindowTitle("Scrcpy Cloud Build & Deploy Hub ✨")
        self.resize(1180, 750)
        self.setMinimumSize(1000, 650)

        self._apply_dark_theme()
        self._init_ui()

        if not self.is_test_mode:
            QTimer.singleShot(100, self.refresh_adb_devices)
            QTimer.singleShot(300, self.fetch_workflow_runs)

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d1117;
                color: #e6edf3;
            }
            QWidget {
                color: #e6edf3;
                font-family: 'Inter', 'Segoe UI', 'DejaVu Sans', sans-serif;
                font-size: 13px;
            }
            QFrame.card {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
                padding: 12px;
            }
            QFrame.headerCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #374151;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
            QPushButton.primary {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
                color: #ffffff;
                border: 1px solid #3b82f6;
            }
            QPushButton.primary:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton.success {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
                color: #ffffff;
                border: 1px solid #10b981;
            }
            QPushButton.success:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
            }
            QPushButton.danger {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:1 #b91c1c);
                color: #ffffff;
                border: 1px solid #ef4444;
            }
            QPushButton.danger:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #dc2626);
            }
            QLineEdit, QComboBox {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #58a6ff;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QListWidget {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #161b22;
                border: 1px solid #21262d;
                border-radius: 6px;
                margin-bottom: 6px;
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #1f2937;
                border: 1px solid #3b82f6;
            }
            QTextEdit {
                background-color: #090d13;
                color: #7ee787;
                font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 8px;
            }
            QProgressBar {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 16px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #10b981);
                border-radius: 5px;
            }
            QSplitter::handle {
                background-color: #30363d;
                width: 2px;
            }
            QScrollBar:vertical {
                background: #0d1117;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #8b949e;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. Header Bar
        header_card = QFrame()
        header_card.setProperty("class", "headerCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title_box = QVBoxLayout()
        title_label = QLabel("🚀 Scrcpy Cloud Build & Deploy Hub")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #60a5fa;")
        
        subtitle_label = QLabel("Zero AI bandwidth consumption • Local status & One-click ADB installation")
        subtitle_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh Runs")
        self.btn_refresh.setProperty("class", "primary")
        self.btn_refresh.clicked.connect(self.fetch_workflow_runs)
        header_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(header_card)

        # 2. ADB Device Control Bar
        adb_card = QFrame()
        adb_card.setProperty("class", "card")
        adb_layout = QHBoxLayout(adb_card)
        adb_layout.setContentsMargins(14, 10, 14, 10)
        adb_layout.setSpacing(12)

        adb_icon = QLabel("📱")
        adb_icon.setFont(QFont("Arial", 14))
        adb_layout.addWidget(adb_icon)

        adb_label = QLabel("Target Phone ADB:")
        adb_label.setFont(QFont("Arial", 11, QFont.Bold))
        adb_layout.addWidget(adb_label)

        self.combo_devices = QComboBox()
        self.combo_devices.setMinimumWidth(220)
        self.combo_devices.addItem(DEFAULT_PHONE_IP)
        adb_layout.addWidget(self.combo_devices)

        self.btn_refresh_adb = QPushButton("🔍 Scan Devices")
        self.btn_refresh_adb.clicked.connect(self.refresh_adb_devices)
        adb_layout.addWidget(self.btn_refresh_adb)

        self.btn_connect_ip = QPushButton("⚡ Connect IP")
        self.btn_connect_ip.clicked.connect(self.connect_custom_adb_ip)
        adb_layout.addWidget(self.btn_connect_ip)

        self.lbl_adb_status = QLabel("Checking...")
        self.lbl_adb_status.setStyleSheet("color: #fbbf24; font-weight: bold;")
        adb_layout.addWidget(self.lbl_adb_status)

        adb_layout.addStretch()
        main_layout.addWidget(adb_card)

        # 3. Main Splitter (Left: Runs List, Right: Run Details & Actions)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- Left Panel: Runs List ---
        left_panel = QFrame()
        left_panel.setProperty("class", "card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        runs_header = QHBoxLayout()
        lbl_runs = QLabel("📦 Recent Workflow Runs")
        lbl_runs.setFont(QFont("Arial", 12, QFont.Bold))
        lbl_runs.setStyleSheet("color: #e5e7eb;")
        runs_header.addWidget(lbl_runs)
        runs_header.addStretch()

        self.lbl_run_count = QLabel("0 runs")
        self.lbl_run_count.setStyleSheet("color: #9ca3af; font-size: 11px;")
        runs_header.addWidget(self.lbl_run_count)
        left_layout.addLayout(runs_header)

        self.list_runs = QListWidget()
        self.list_runs.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_runs.setWordWrap(True)
        self.list_runs.itemClicked.connect(self.on_run_selected)
        left_layout.addWidget(self.list_runs)

        splitter.addWidget(left_panel)

        # --- Right Panel: Run Details, Actions & Logs ---
        right_panel = QFrame()
        right_panel.setProperty("class", "card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(12)

        # Details Header
        self.lbl_selected_title = QLabel("Select a workflow run on the left to inspect")
        self.lbl_selected_title.setFont(QFont("Arial", 14, QFont.Bold))
        self.lbl_selected_title.setStyleSheet("color: #f3f4f6;")
        right_layout.addWidget(self.lbl_selected_title)

        self.lbl_selected_meta = QLabel("ID: - | Tag: - | Duration: -")
        self.lbl_selected_meta.setStyleSheet("color: #9ca3af; font-size: 11px;")
        right_layout.addWidget(self.lbl_selected_meta)

        # Jobs Breakdown Box
        self.jobs_frame = QFrame()
        self.jobs_frame.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border-radius: 8px;
                border: 1px solid #21262d;
            }
        """)
        jobs_layout = QHBoxLayout(self.jobs_frame)
        jobs_layout.setContentsMargins(14, 10, 14, 10)
        jobs_layout.setSpacing(24)

        self.lbl_android_job = QLabel("🤖 Android APK: Unknown")
        self.lbl_android_job.setStyleSheet("color: #d1d5db; font-weight: 600; font-size: 13px;")
        jobs_layout.addWidget(self.lbl_android_job)

        self.lbl_pc_job = QLabel("💻 PC Nuitka: Unknown")
        self.lbl_pc_job.setStyleSheet("color: #d1d5db; font-weight: 600; font-size: 13px;")
        jobs_layout.addWidget(self.lbl_pc_job)

        jobs_layout.addStretch()
        right_layout.addWidget(self.jobs_frame)

        # Action Buttons Row
        actions_box = QHBoxLayout()
        actions_box.setSpacing(10)

        self.btn_install_apk = QPushButton("📥 Download && ADB Install APK")
        self.btn_install_apk.setProperty("class", "success")
        self.btn_install_apk.setEnabled(False)
        self.btn_install_apk.clicked.connect(self.download_and_install_apk)
        actions_box.addWidget(self.btn_install_apk)

        self.btn_copy_error = QPushButton("📋 Copy Error Snippet for Agent")
        self.btn_copy_error.setProperty("class", "danger")
        self.btn_copy_error.setEnabled(False)
        self.btn_copy_error.clicked.connect(self.copy_error_snippet)
        actions_box.addWidget(self.btn_copy_error)

        self.btn_open_browser = QPushButton("🌐 Open in GitHub")
        self.btn_open_browser.setEnabled(False)
        self.btn_open_browser.clicked.connect(self.open_run_in_browser)
        actions_box.addWidget(self.btn_open_browser)

        right_layout.addLayout(actions_box)

        # Log and Console View
        log_header = QHBoxLayout()
        lbl_console = QLabel("🖥️ Activity & Build Console")
        lbl_console.setFont(QFont("Arial", 11, QFont.Bold))
        lbl_console.setStyleSheet("color: #d1d5db;")
        log_header.addWidget(lbl_console)
        log_header.addStretch()

        self.btn_view_full_log = QPushButton("📄 Fetch Full Log")
        self.btn_view_full_log.setEnabled(False)
        self.btn_view_full_log.clicked.connect(self.fetch_full_log)
        log_header.addWidget(self.btn_view_full_log)

        self.btn_clear_log = QPushButton("🧹 Clear")
        self.btn_clear_log.clicked.connect(lambda: self.txt_logs.clear())
        log_header.addWidget(self.btn_clear_log)

        right_layout.addLayout(log_header)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setPlaceholderText("Logs and build output will appear here...")
        right_layout.addWidget(self.txt_logs)

        # Progress bar at bottom of right panel
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)
        self.progress_bar.hide()
        right_layout.addWidget(self.progress_bar)

        splitter.addWidget(right_panel)
        splitter.setSizes([320, 800])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        main_layout.addWidget(splitter, 1)

        # 4. Status Bar
        self.status_bar = QLabel("Ready • Zero AI bandwidth consumption ✨")
        self.status_bar.setStyleSheet("color: #6ee7b7; font-size: 11px; padding: 2px 6px;")
        main_layout.addWidget(self.status_bar)

    def log(self, message: str, color: str = "#7ee787"):
        """Appends formatted message to console."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.append(f"<span style='color:#6b7280;'>[{timestamp}]</span> <span style='color:{color};'>{message}</span>")
        sb = self.txt_logs.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_loading(self, is_loading: bool, status_text: str = ""):
        """Controls loading animation and button states."""
        if is_loading:
            self.progress_bar.show()
            self.btn_refresh.setEnabled(False)
            if status_text:
                self.status_bar.setText(f"⏳ {status_text}")
        else:
            self.progress_bar.hide()
            self.btn_refresh.setEnabled(True)
            if status_text:
                self.status_bar.setText(f"✨ {status_text}")

    # =========================================================================
    # ADB Operations
    # =========================================================================
    def refresh_adb_devices(self):
        """Scans connected ADB devices."""
        def _scan(emit_log):
            emit_log("Scanning ADB devices...")
            res = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            lines = res.stdout.strip().splitlines()[1:]
            devices = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            return {"devices": devices}

        self._start_worker("adb_scan", _scan)

    def connect_custom_adb_ip(self):
        """Attempts to connect to target IP."""
        target = self.combo_devices.currentText().strip() or DEFAULT_PHONE_IP

        def _connect(emit_log):
            emit_log(f"Connecting to ADB endpoint: {target}...")
            res = subprocess.run(["adb", "connect", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return {"output": res.stdout.strip()}

        self._start_worker("adb_connect", _connect)

    # =========================================================================
    # GitHub Workflow Operations
    # =========================================================================
    def fetch_workflow_runs(self):
        """Fetches the latest runs list from GitHub Actions."""
        self.set_loading(True, "Fetching recent workflow runs from GitHub...")

        def _fetch(emit_log):
            emit_log("Running 'gh run list'...")
            fields = "status,conclusion,name,headBranch,databaseId,createdAt,updatedAt,url,workflowName"
            runs = run_gh_json(["run", "list", f"--json={fields}", "--limit=12"])
            return {"runs": runs}

        self._start_worker("fetch_runs", _fetch)

    def on_run_selected(self, item: QListWidgetItem):
        """Handles selecting a run card."""
        run_data = item.data(Qt.UserRole)
        if not run_data:
            return
        self.selected_run = run_data
        run_id = run_data.get("databaseId")
        tag = run_data.get("headBranch") or run_data.get("name")
        status = run_data.get("status")
        conclusion = run_data.get("conclusion") or "running"

        self.lbl_selected_title.setText(f"Run #{run_id} ({tag})")
        self.lbl_selected_meta.setText(f"Status: {status.upper()} | Conclusion: {conclusion.upper()} | Created: {run_data.get('createdAt')}")

        self.btn_open_browser.setEnabled(True)
        self.btn_view_full_log.setEnabled(True)

        if conclusion == "success" or status == "completed":
            self.btn_install_apk.setEnabled(True)
        else:
            self.btn_install_apk.setEnabled(False)

        if conclusion == "failure":
            self.btn_copy_error.setEnabled(True)
        else:
            self.btn_copy_error.setEnabled(False)

        self.fetch_run_jobs(run_id)

    def fetch_run_jobs(self, run_id: int):
        """Fetches detailed sub-jobs for the selected run."""
        def _fetch_jobs(emit_log):
            emit_log(f"Fetching job steps for Run #{run_id}...")
            details = run_gh_json(["run", "view", str(run_id), "--json=jobs,conclusion,status"])
            return {"details": details}

        self._start_worker("fetch_jobs", _fetch_jobs)

    def download_and_install_apk(self):
        """Downloads the APK artifact for the selected run and installs it via ADB."""
        if not self.selected_run:
            return
        run_id = self.selected_run.get("databaseId")
        target_device = self.combo_devices.currentText().strip() or DEFAULT_PHONE_IP

        self.set_loading(True, f"Downloading APK for Run #{run_id}...")
        self.log(f"Starting APK download and install pipeline for Run #{run_id} to device [{target_device}]...", "#38bdf8")

        def _download_and_install(emit_log):
            DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
            target_dir = DOWNLOADS_DIR / f"run_{run_id}"
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            target_dir.mkdir(parents=True, exist_ok=True)

            emit_log(f"Downloading 'android-apk' artifact via gh CLI to {target_dir}...")
            res = subprocess.run(
                ["gh", "run", "download", str(run_id), "-n", "android-apk", "-D", str(target_dir)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(PROJECT_DIR)
            )

            apk_files = list(target_dir.glob("**/*.apk"))
            if not apk_files:
                raise RuntimeError(f"No .apk found in downloaded artifact! Output: {res.stdout} {res.stderr}")

            apk_path = apk_files[0]
            emit_log(f"Found APK: {apk_path.name} ({round(apk_path.stat().st_size / (1024*1024), 2)} MB)")

            emit_log(f"Installing APK to ADB device {target_device}...")
            cmd = ["adb"]
            if target_device:
                cmd.extend(["-s", target_device])
            cmd.extend(["install", "-r", str(apk_path)])

            install_res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if "Success" not in install_res.stdout and install_res.returncode != 0:
                raise RuntimeError(f"ADB install failed: {install_res.stderr or install_res.stdout}")

            return {"apk_name": apk_path.name, "output": install_res.stdout.strip()}

        self._start_worker("download_install", _download_and_install)

    def copy_error_snippet(self):
        """Fetches failed logs and automatically copies the extracted error snippet to clipboard."""
        if not self.selected_run:
            return
        run_id = self.selected_run.get("databaseId")
        self.set_loading(True, f"Extracting failure snippet for Run #{run_id}...")

        def _get_log(emit_log):
            emit_log(f"Fetching failed log for Run #{run_id}...")
            res = subprocess.run(
                ["gh", "run", "view", str(run_id), "--log-failed"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(PROJECT_DIR)
            )
            raw_log = res.stdout
            if not raw_log.strip():
                emit_log("Fetching full run log as fallback...")
                res = subprocess.run(
                    ["gh", "run", "view", str(run_id), "--log"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(PROJECT_DIR)
                )
                raw_log = res.stdout

            snippet = extract_smart_error_snippet(raw_log)
            return {"snippet": snippet}

        self._start_worker("copy_error", _get_log)

    def fetch_full_log(self):
        """Fetches full log into the console."""
        if not self.selected_run:
            return
        run_id = self.selected_run.get("databaseId")
        self.set_loading(True, f"Downloading full log for Run #{run_id}...")

        def _fetch(emit_log):
            emit_log(f"Retrieving full log for Run #{run_id}...")
            res = subprocess.run(
                ["gh", "run", "view", str(run_id), "--log"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(PROJECT_DIR)
            )
            return {"log": res.stdout}

        self._start_worker("fetch_full_log", _fetch)

    def open_run_in_browser(self):
        """Opens selected run on GitHub in the user's browser."""
        if self.selected_run and self.selected_run.get("url"):
            import webbrowser
            webbrowser.open(self.selected_run.get("url"))

    # =========================================================================
    # Worker Thread Manager
    # =========================================================================
    def _start_worker(self, action_id: str, func, *args, **kwargs):
        if self.worker and self.worker.isRunning():
            self.worker.wait()

        self.worker = CommandWorker(action_id, func, *args, **kwargs)
        self.worker.sig_log.connect(lambda msg: self.log(msg, "#94a3b8"))
        self.worker.sig_result.connect(self._handle_worker_result)
        self.worker.sig_error.connect(self._handle_worker_error)
        self.worker.start()

    @Slot(str, dict)
    def _handle_worker_result(self, action_id: str, payload: dict):
        self.set_loading(False)

        if action_id == "adb_scan":
            devices = payload.get("devices", [])
            self.combo_devices.clear()
            if devices:
                for d in devices:
                    self.combo_devices.addItem(d)
                self.lbl_adb_status.setText(f"🟢 {len(devices)} device(s) online")
                self.lbl_adb_status.setStyleSheet("color: #34d399; font-weight: bold;")
                self.log(f"ADB online devices: {', '.join(devices)}", "#34d399")
            else:
                self.combo_devices.addItem(DEFAULT_PHONE_IP)
                self.lbl_adb_status.setText("🔴 No devices found")
                self.lbl_adb_status.setStyleSheet("color: #f87171; font-weight: bold;")
                self.log("No ADB devices detected. Check USB/Wi-Fi connection.", "#f87171")

        elif action_id == "adb_connect":
            out = payload.get("output", "")
            self.log(f"ADB connect result: {out}", "#60a5fa")
            self.refresh_adb_devices()

        elif action_id == "fetch_runs":
            runs = payload.get("runs", [])
            self.active_runs = runs
            self.list_runs.clear()
            self.lbl_run_count.setText(f"{len(runs)} runs")

            for run in runs:
                item = QListWidgetItem()
                tag = run.get("headBranch") or run.get("name") or "Workflow"
                status = run.get("status")
                conclusion = run.get("conclusion")
                created = run.get("createdAt", "")[:19].replace("T", " ")

                if conclusion == "success":
                    badge = "🟢 SUCCESS"
                elif conclusion == "failure":
                    badge = "🔴 FAILED"
                elif status == "in_progress":
                    badge = "🟡 BUILDING"
                elif status == "queued":
                    badge = "⚪ QUEUED"
                else:
                    badge = f"🔵 {status.upper()}"

                item.setText(f"{badge}  •  {tag}\nRun #{run.get('databaseId')}  |  {created}")
                item.setData(Qt.UserRole, run)
                self.list_runs.addItem(item)

            if runs:
                self.list_runs.setCurrentRow(0)
                self.on_run_selected(self.list_runs.item(0))
                self.log(f"Loaded {len(runs)} latest workflow runs successfully!", "#34d399")

        elif action_id == "fetch_jobs":
            details = payload.get("details", {})
            jobs = details.get("jobs", [])
            
            android_status = "Not Run"
            pc_status = "Not Run"

            for j in jobs:
                jname = j.get("name", "")
                jconc = j.get("conclusion") or j.get("status")
                if "Android" in jname:
                    android_status = jconc.upper()
                elif "PC" in jname:
                    pc_status = jconc.upper()

            def _color(st):
                if "SUCCESS" in st: return "#34d399"
                if "FAIL" in st: return "#f87171"
                if "IN_PROGRESS" in st or "BUILD" in st: return "#fbbf24"
                return "#9ca3af"

            self.lbl_android_job.setText(f"🤖 Android APK: {android_status}")
            self.lbl_android_job.setStyleSheet(f"color: {_color(android_status)}; font-weight: bold;")
            
            self.lbl_pc_job.setText(f"💻 PC Binary: {pc_status}")
            self.lbl_pc_job.setStyleSheet(f"color: {_color(pc_status)}; font-weight: bold;")

        elif action_id == "download_install":
            apk_name = payload.get("apk_name", "")
            out = payload.get("output", "")
            self.log(f"🎉 SUCCESS! APK '{apk_name}' was installed on your phone!\n{out}", "#34d399")
            QMessageBox.information(self, "Installation Successful 🚀", f"APK '{apk_name}' was successfully installed on your device!")

        elif action_id == "copy_error":
            snippet = payload.get("snippet", "")
            clipboard = QApplication.clipboard()
            clipboard.setText(snippet)
            self.log("📋 Smart error snippet copied to clipboard! Paste it directly into chat with your agent!", "#38bdf8")
            self.status_bar.setText("📋 Copied error snippet to clipboard! Just paste into chat ✨")

        elif action_id == "fetch_full_log":
            full_log = payload.get("log", "")
            self.txt_logs.setText(full_log)
            self.log("Full log loaded into console.", "#60a5fa")

    @Slot(str, str)
    def _handle_worker_error(self, action_id: str, error_msg: str):
        self.set_loading(False)
        self.log(f"❌ Error during '{action_id}': {error_msg}", "#f87171")
        self.status_bar.setText(f"❌ Operation failed: {error_msg[:60]}")
        QMessageBox.warning(self, "Operation Failed", f"Action '{action_id}' encountered an error:\n\n{error_msg}")


def main():
    parser = argparse.ArgumentParser(description="Scrcpy Cloud Build & Deploy Hub")
    parser.add_argument("--auto-screenshot", type=str, help="Take offscreen GUI screenshot and exit")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = BuildMonitorWindow(is_test_mode=bool(args.auto_screenshot))

    if args.auto_screenshot:
        window.show()
        
        mock_runs = [
            {"databaseId": 33395164190, "headBranch": "v26.08.17", "status": "in_progress", "conclusion": "", "createdAt": "2026-08-31T13:06:40Z"},
            {"databaseId": 33389423981, "headBranch": "v26.08.16", "status": "completed", "conclusion": "success", "createdAt": "2026-08-31T11:57:57Z"},
            {"databaseId": 33388287417, "headBranch": "v26.08.15", "status": "completed", "conclusion": "failure", "createdAt": "2026-08-31T11:43:18Z"}
        ]
        window._handle_worker_result("fetch_runs", {"runs": mock_runs})
        
        window.lbl_selected_title.setText("Run #33395164190 (v26.08.17)")
        window.lbl_selected_meta.setText("Status: IN_PROGRESS | Conclusion: RUNNING | Created: 2026-08-31 13:06:40")
        window.lbl_android_job.setText("🤖 Android APK: IN_PROGRESS")
        window.lbl_android_job.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 13px;")
        window.lbl_pc_job.setText("💻 PC Binary: SUCCESS")
        window.lbl_pc_job.setStyleSheet("color: #34d399; font-weight: bold; font-size: 13px;")
        window.lbl_adb_status.setText("🟢 10.132.152.85:5555 Online")
        window.lbl_adb_status.setStyleSheet("color: #34d399; font-weight: bold;")
        window.btn_install_apk.setEnabled(True)
        window.btn_copy_error.setEnabled(True)
        window.btn_open_browser.setEnabled(True)
        window.log("Connected to phone: 10.132.152.85:5555 (Samsung Galaxy)", "#34d399")
        window.log("Cloud Build & Auto-Release triggered for tag: v26.08.17", "#60a5fa")
        window.log("PC Nuitka Standalone & Portable build completed successfully!", "#34d399")
        window.log("Android APK build in progress via GitHub Actions Cloud...", "#fbbf24")
        
        app.processEvents()
        window.repaint()
        
        screenshot_path = Path(args.auto_screenshot).resolve()
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap = window.grab()
        pixmap.save(str(screenshot_path))
        print(f"AUTO_SCREENSHOT_SAVED: {screenshot_path}")
        sys.exit(0)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
