import sys
import subprocess
import threading
import socket
import time
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QMainWindow, 
    QSpinBox, QHBoxLayout, QTabWidget, QPushButton, QFileDialog, QCheckBox,
    QGroupBox, QFormLayout, QLineEdit, QMessageBox, QComboBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QIcon

# Import from modules
from heartbeat_listener import (
    start_scrcpy, get_local_ip, LOG_FILE, set_gui_log_callback,
    send_adb_keyevent, send_adb_text, open_url_on_phone, 
    get_device_hardware_info, test_network_latency
)
from file_transfer import FileTransferScreen, PullScreen, TCPFileServer

APP_VERSION = "268.02.5"
APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

def get_desktop_ip_path():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.exists(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    return os.path.join(desktop, "last_ip.txt")

def load_config():
    defaults = {
        "heartbeat_port": 5556,
        "discovery_port": 5557,
        "adb_port": 5555,
        "scrcpy_bin": "scrcpy",
        "last_ip_file": get_desktop_ip_path(),
        "log_file": os.path.join(APP_DIR, "ScrcpyUltimateLink_debug.log"),
        "logging_enabled": False,
        "connection_mode": "heartbeat",
        "scrcpy_preset": "Balanced (Default)",
        "auto_clip_sync": False
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            for k, v in defaults.items():
                if k not in config:
                    config[k] = v
            return config
    except:
        pass
    return defaults

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except:
        pass

config = load_config()

DISCOVERY_PORT = config["discovery_port"]
HEARTBEAT_PORT = config["heartbeat_port"]
ADB_PORT = config["adb_port"]
SCRCPY_BIN = config["scrcpy_bin"]
LAST_IP_FILE = config["last_ip_file"]
LOG_FILE = config["log_file"]
LOGGING_ENABLED = config.get("logging_enabled", False)
CONNECTION_MODE = config.get("connection_mode", "heartbeat")
SCRCPY_PRESET = config.get("scrcpy_preset", "Balanced (Default)")
AUTO_CLIP_SYNC = config.get("auto_clip_sync", False)

_log_panel = None

def gui_log(msg):
    global _log_panel
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {msg}"
    if _log_panel:
        _log_panel.append(line)
        scrollbar = _log_panel.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    if LOGGING_ENABLED:
        try:
            with open(LOG_FILE, "a") as f:
                f.write(line + "\n")
        except:
            pass

class DiscoveryBroadcaster:
    def __init__(self, local_ip, port=DISCOVERY_PORT):
        self.local_ip = local_ip
        self.port = port
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._broadcast_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"SCRCPC_HERE {self.local_ip} {HEARTBEAT_PORT}".encode()

        gui_log(f"Broadcaster starting on port {self.port} (PC IP: {self.local_ip})")

        while self.running:
            try:
                sock.sendto(message, ('255.255.255.255', self.port))
                for ip in self._get_interface_ips():
                    parts = ip.split('.')
                    if len(parts) == 4:
                        bcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                        sock.sendto(message, (bcast, self.port))
                time.sleep(3)
            except Exception as e:
                gui_log(f"Broadcast error: {e}")
                time.sleep(1)
        sock.close()

    def _get_interface_ips(self):
        ips = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except:
            pass
        return ips

class HeartbeatWorker(QObject):
    heartbeat_received = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def run(self):
        gui_log("HeartbeatWorker starting...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", HEARTBEAT_PORT))
            gui_log(f"GUI listener bound to 0.0.0.0:{HEARTBEAT_PORT}")
            sock.settimeout(2.0)
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    ip = addr[0]
                    message = data.decode('utf-8').strip()
                    if "HELLO_" in message:
                        self.heartbeat_received.emit(ip)
                except socket.timeout:
                    pass
        except Exception as e:
            gui_log(f"GUI Listener Error: {e}")
            self.log_signal.emit(f"Listener Error: {e}")

class ScrcpyUltimateLink(QMainWindow):
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.log_signal.connect(self.add_log)
        self.setWindowTitle(f"Scrcpy Ultimate Link v{APP_VERSION}")
        self.setMinimumSize(850, 680)
        
        self.scrcpy_presets = {
            "Balanced (Default)": [],
            "High Quality (1080p, 16M)": ["-m", "1920", "-b", "16M"],
            "Fluid Performance (720p, 60fps, 8M)": ["-m", "1280", "--max-fps", "60", "-b", "8M"],
            "Battery Saver (480p, 30fps, 2M)": ["-m", "854", "--max-fps", "30", "-b", "2M", "--tunnel-forward"]
        }

        self.setStyleSheet("""
            QMainWindow, QTabWidget::pane { background-color: #121224; border: none; }
            QLabel { color: #e0e0e0; }
            QTextEdit { background-color: #1a1a3a; border: 1px solid #1f1f4e; border-radius: 8px; padding: 10px; color: #e0e0e0; font-family: monospace; font-size: 12px; }
            QSpinBox, QComboBox, QLineEdit { background-color: #1a1a3a; border: 1px solid #1f1f4e; border-radius: 4px; padding: 6px; color: #00d9a5; font-size: 14px; }
            QPushButton { background-color: #1f1f4e; color: #00d9a5; border: 2px solid #00d9a5; border-radius: 8px; padding: 10px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background-color: #00d9a5; color: #121224; }
            QPushButton:disabled { background-color: #121224; color: #666; border-color: #444; }
            QCheckBox { color: #e0e0e0; font-size: 14px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #00d9a5; border-radius: 4px; background: #1a1a3a; }
            QCheckBox::indicator:checked { background: #00d9a5; }
            QGroupBox { color: #00d9a5; font-weight: bold; font-size: 14px; border: 2px solid #1f1f4e; border-radius: 8px; margin-top: 12px; padding-top: 10px; background-color: #161632; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QTabBar::tab { background: #1a1a3a; color: #888; padding: 10px 20px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
            QTabBar::tab:selected { background: #1f1f4e; color: #00d9a5; font-weight: bold; }
        """)

        # Start PC TCP File server to handle direct Mobile transfers!
        self.file_server = TCPFileServer()
        self.file_server.start()

        # UI Setup
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- MIRROR PHONE TAB ---
        self.main_tab = QWidget()
        main_layout = QVBoxLayout(self.main_tab)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header_layout = QHBoxLayout()
        self.title = QLabel("Scrcpy Ultimate Link")
        self.title.setStyleSheet("font-size: 26px; font-weight: bold; color: #00d9a5;")
        header_layout.addWidget(self.title)
        
        # Fast Subnet scan fallback button
        self.scan_subnet_btn = QPushButton("🔍 Fallback Subnet Scan")
        self.scan_subnet_btn.clicked.connect(self.scan_subnet_for_phone)
        header_layout.addWidget(self.scan_subnet_btn)
        
        header_layout.addStretch()

        self.connect_saved_btn = QPushButton("Connect Saved IP")
        self.connect_saved_btn.clicked.connect(self.connect_using_saved_ip)
        self.connect_heartbeat_btn = QPushButton("Auto-Discover (Heartbeat)")
        self.connect_heartbeat_btn.clicked.connect(self.start_heartbeat_mode)

        header_layout.addWidget(self.connect_saved_btn)
        header_layout.addWidget(self.connect_heartbeat_btn)
        main_layout.addLayout(header_layout)

        # Status Label
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #00d9a5;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        # GRID FOR UTILITIES
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        # 1. Preset Profile Groupbox
        preset_group = QGroupBox("Preset Video Quality Profiles")
        preset_form = QFormLayout(preset_group)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.scrcpy_presets.keys()))
        self.preset_combo.setCurrentText(SCRCPY_PRESET)
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_form.addRow("Preset:", self.preset_combo)
        grid_layout.addWidget(preset_group, 0, 0)

        # 2. Bidirectional Clipboard Groupbox
        clip_group = QGroupBox("📋 Clipboard Sync Tools")
        clip_layout = QVBoxLayout(clip_group)
        
        self.clip_chk = QCheckBox("Auto-sync PC clipboard ➔ Phone")
        self.clip_chk.setChecked(AUTO_CLIP_SYNC)
        self.clip_chk.toggled.connect(self.on_clip_chk_toggled)
        clip_layout.addWidget(self.clip_chk)

        clip_btn_layout = QHBoxLayout()
        push_clip_btn = QPushButton("📤 Push Clipboard")
        push_clip_btn.clicked.connect(self.push_clipboard_to_phone)
        fetch_clip_btn = QPushButton("📥 Fetch Clipboard")
        fetch_clip_btn.clicked.connect(self.fetch_clipboard_from_phone)
        clip_btn_layout.addWidget(push_clip_btn)
        clip_btn_layout.addWidget(fetch_clip_btn)
        clip_layout.addLayout(clip_btn_layout)
        grid_layout.addWidget(clip_group, 0, 1)

        # 3. Live Hardware Diagnostics Dashboard
        self.dash_group = QGroupBox("📊 Live Hardware Dashboard")
        dash_form = QFormLayout(self.dash_group)
        self.dash_model = QLabel("Model: --")
        self.dash_android = QLabel("Android: --")
        self.dash_batt = QLabel("Battery: --")
        self.dash_temp = QLabel("Temp: --")
        self.dash_latency = QLabel("WiFi Latency: --")
        self.dash_res = QLabel("Resolution: --")
        
        dash_form.addRow(self.dash_model, self.dash_android)
        dash_form.addRow(self.dash_batt, self.dash_temp)
        dash_form.addRow(self.dash_res, self.dash_latency)
        
        self.refresh_dash_btn = QPushButton("🔄 Refresh Dashboard")
        self.refresh_dash_btn.clicked.connect(self.update_dashboard)
        dash_form.addRow(self.refresh_dash_btn)
        grid_layout.addWidget(self.dash_group, 1, 0)

        # 4. Quick Screen Actions (Screenshot & Record)
        actions_group = QGroupBox("📸 Screen capture / Recording")
        actions_layout = QVBoxLayout(actions_group)
        
        screenshot_btn = QPushButton("📷 Take Quick Screenshot")
        screenshot_btn.clicked.connect(self.take_screenshot)
        
        record_btn = QPushButton("🎥 Start Video Recording")
        record_btn.clicked.connect(self.start_video_recording)
        
        actions_layout.addWidget(screenshot_btn)
        actions_layout.addWidget(record_btn)
        grid_layout.addWidget(actions_group, 1, 1)

        main_layout.addLayout(grid_layout)

        # 5. Quick Remote Control Key Bar
        control_group = QGroupBox("📱 Fast Remote Control Bar")
        control_layout = QHBoxLayout(control_group)
        control_layout.setSpacing(6)
        
        btns = [
            ("⚡ Power", 26), ("🏠 Home", 3), ("↩️ Back", 4),
            ("⬜ Recents", 187), ("🔊 Vol +", 24), ("🔉 Vol -", 25)
        ]
        for label, code in btns:
            btn = QPushButton(label)
            btn.clicked.connect(lambda ch, c=code: send_adb_keyevent(c))
            control_layout.addWidget(btn)
            
        sleep_btn = QPushButton("🔒 Turn Screen Off")
        sleep_btn.clicked.connect(lambda: send_adb_keyevent(223))
        control_layout.addWidget(sleep_btn)
        
        main_layout.addWidget(control_group)

        # Live logs (bottom)
        log_group = QGroupBox("System Logs")
        log_layout = QVBoxLayout(log_group)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        log_layout.addWidget(self.log_area)
        main_layout.addWidget(log_group)

        global _log_panel
        _log_panel = self.log_area
        set_gui_log_callback(lambda msg: self.log_signal.emit(msg))

        self.tabs.addTab(self.main_tab, "Mirror Phone")

        # --- FILE TRANSFER TAB ---
        self.file_transfer_tab = QWidget()
        file_transfer_layout = QVBoxLayout(self.file_transfer_tab)
        file_transfer_layout.setContentsMargins(0, 0, 0, 0)
        
        file_tabs = QTabWidget()
        file_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1f1f4e; border-radius: 8px; background-color: #121224; }
            QTabBar::tab { background-color: #1a1a3a; color: #888; padding: 10px 20px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #1f1f4e; color: #00d9a5; font-weight: bold; }
        """)
        
        self.file_transfer_screen = FileTransferScreen(
            get_device_ip_func=lambda: self.get_current_phone_ip(),
            log_callback=gui_log
        )
        self.pull_screen = PullScreen(
            get_device_ip_func=lambda: self.get_current_phone_ip(),
            log_callback=gui_log
        )
        
        file_tabs.addTab(self.file_transfer_screen, "Push to Phone (TCP over WiFi)")
        file_tabs.addTab(self.pull_screen, "Pull from Phone")
        file_transfer_layout.addWidget(file_tabs)
        self.tabs.addTab(self.file_transfer_tab, "File Transfer")

        # --- SETTINGS TAB ---
        self.settings_tab = QWidget()
        settings_outer = QVBoxLayout(self.settings_tab)
        
        from PyQt6.QtWidgets import QScrollArea
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        settings_layout.setSpacing(15)

        ports_group = QGroupBox("Network Ports")
        ports_form = QFormLayout(ports_group)
        
        self.heartbeat_port_spin = QSpinBox()
        self.heartbeat_port_spin.setRange(1024, 65535)
        self.heartbeat_port_spin.setValue(HEARTBEAT_PORT)
        self.heartbeat_port_spin.valueChanged.connect(self.on_port_changed)

        self.discovery_port_spin = QSpinBox()
        self.discovery_port_spin.setRange(1024, 65535)
        self.discovery_port_spin.setValue(DISCOVERY_PORT)
        self.discovery_port_spin.valueChanged.connect(self.on_port_changed)

        self.adb_port_spin = QSpinBox()
        self.adb_port_spin.setRange(1024, 65535)
        self.adb_port_spin.setValue(ADB_PORT)
        self.adb_port_spin.valueChanged.connect(self.on_port_changed)

        ports_form.addRow("Heartbeat Port (Phone→PC):", self.heartbeat_port_spin)
        ports_form.addRow("Discovery Port (PC Broadcast):", self.discovery_port_spin)
        ports_form.addRow("ADB Port (scrcpy):", self.adb_port_spin)
        settings_layout.addWidget(ports_group)

        scrcpy_group = QGroupBox("scrcpy Binary")
        scrcpy_form = QFormLayout(scrcpy_group)
        scrcpy_layout = QHBoxLayout()
        self.scrcpy_path_edit = QLineEdit(SCRCPY_BIN)
        self.scrcpy_path_edit.setReadOnly(True)
        self.scrcpy_browse_btn = QPushButton("Browse...")
        self.scrcpy_browse_btn.clicked.connect(self.browse_scrcpy_binary)
        scrcpy_layout.addWidget(self.scrcpy_path_edit)
        scrcpy_layout.addWidget(self.scrcpy_browse_btn)
        scrcpy_form.addRow("Binary Path:", scrcpy_layout)
        settings_layout.addWidget(scrcpy_group)

        # Settings for clipboard monitor
        self.pc_clip = QApplication.clipboard()
        self.pc_clip.dataChanged.connect(self.on_pc_clipboard_changed)

        settings_scroll.setWidget(settings_widget)
        settings_outer.addWidget(settings_scroll)
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")

        # Timer to query Dashboard and Clipboard every 5 seconds
        self.dash_timer = QTimer()
        self.dash_timer.timeout.connect(self.update_dashboard)
        self.dash_timer.start(5000)

        self.discovery = None
        self.worker = None
        self.thread = None

    def start_heartbeat_mode(self):
        if self.thread and self.thread.is_alive():
            return
        
        if hasattr(self, 'discovery') and self.discovery:
            self.discovery.stop()

        local_ip = get_local_ip()
        self.discovery = DiscoveryBroadcaster(local_ip)
        self.discovery.start()

        self.worker = HeartbeatWorker()
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker.heartbeat_received.connect(self.handle_heartbeat)
        self.worker.log_signal.connect(self.add_log)
        self.thread.start()

        self.status_label.setText("Status: Listening for phone heartbeat...")
        self.add_log("Heartbeat mode active.")

    def connect_using_saved_ip(self):
        ip = self.get_current_phone_ip()
        if not ip:
            QMessageBox.warning(self, "No Saved IP", "No saved IP found. Broadcast discovery first.")
            return
        self.status_label.setText(f"Connecting to Saved IP: {ip}...")
        threading.Thread(target=self.connect_and_launch, args=(ip,), daemon=True).start()

    def get_current_phone_ip(self):
        from heartbeat_listener import get_connected_phone_ip, current_phone_ip
        ip, port = get_connected_phone_ip()
        if ip:
            return ip
        if current_phone_ip:
            return current_phone_ip
        try:
            if os.path.exists(LAST_IP_FILE):
                with open(LAST_IP_FILE, "r") as f:
                    return f.read().strip()
        except:
            pass
        return None

    def on_preset_changed(self, val):
        global SCRCPY_PRESET
        SCRCPY_PRESET = val
        config["scrcpy_preset"] = val
        save_config(config)

    def on_clip_chk_toggled(self, checked):
        global AUTO_CLIP_SYNC
        AUTO_CLIP_SYNC = checked
        config["auto_clip_sync"] = checked
        save_config(config)

    def on_pc_clipboard_changed(self):
        if AUTO_CLIP_SYNC:
            text = self.pc_clip.text()
            if text:
                threading.Thread(target=send_adb_text, args=(text,), daemon=True).start()

    def push_clipboard_to_phone(self):
        text = self.pc_clip.text()
        if text:
            success, msg = send_adb_text(text)
            if success:
                gui_log("Clipboard synced to Phone successfully.")
            else:
                gui_log(f"Clipboard push error: {msg}")

    def fetch_clipboard_from_phone(self):
        ip = self.get_current_phone_ip()
        if not ip:
            return
        try:
            cmd = ["adb", "-s", f"{ip}:{ADB_PORT}", "shell", "am", "broadcast", "-a", "org.henry.scrcpy.GET_CLIPBOARD"]
            subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            gui_log("Triggered Phone clipboard fetch via ADB intent.")
        except Exception as e:
            gui_log(f"Fetch clipboard failed: {e}")

    def update_dashboard(self):
        ip = self.get_current_phone_ip()
        if not ip:
            return
            
        def _task():
            info = get_device_hardware_info(ip, ADB_PORT)
            latency, lat_str = test_network_latency(ip, ADB_PORT)
            
            def _update():
                if "error" not in info:
                    self.dash_model.setText(f"Model: {info.get('model', '--')}")
                    self.dash_android.setText(f"Android: {info.get('android_version', '--')}")
                    self.dash_batt.setText(f"Battery: {info.get('battery_level', '--')} ({info.get('charging', '--')})")
                    self.dash_temp.setText(f"Temp: {info.get('temperature', '--')}")
                    self.dash_res.setText(f"Resolution: {info.get('resolution', '--')}")
                if latency:
                    self.dash_latency.setText(f"Ping: {latency:.1f} ms")
                else:
                    self.dash_latency.setText("Ping: Timeout")
            QTimer.singleShot(0, _update)

        threading.Thread(target=_task, daemon=True).start()

    def take_screenshot(self):
        ip = self.get_current_phone_ip()
        if not ip:
            return
        def _task():
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = f"scrcpy_screenshot_{int(time.time())}.png"
            local_path = os.path.join(desktop, filename)
            try:
                subprocess.run(["adb", "-s", f"{ip}:{ADB_PORT}", "shell", "screencap", "-p", "/sdcard/screen.png"], timeout=4)
                subprocess.run(["adb", "-s", f"{ip}:{ADB_PORT}", "pull", "/sdcard/screen.png", local_path], timeout=4)
                gui_log(f"Screenshot saved to Desktop: {filename}")
            except Exception as e:
                gui_log(f"Screenshot error: {e}")
        threading.Thread(target=_task, daemon=True).start()

    def start_video_recording(self):
        ip = self.get_current_phone_ip()
        if not ip:
            return
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filename = f"scrcpy_recording_{int(time.time())}.mp4"
        local_path = os.path.join(desktop, filename)
        
        args = ["--record", local_path] + self.scrcpy_presets.get(SCRCPY_PRESET, [])
        gui_log(f"Launching scrcpy recording: {filename}")
        threading.Thread(target=start_scrcpy, args=(ip, ADB_PORT, args), daemon=True).start()

    def scan_subnet_for_phone(self):
        self.scan_subnet_btn.setEnabled(False)
        self.status_label.setText("Scanning local subnet...")
        gui_log("Starting fast fallback concurrent subnet scanner...")

        def _scan():
            local_ip = get_local_ip()
            if "unknown" in local_ip:
                QTimer.singleShot(0, lambda: self.status_label.setText("No connection (IP unknown)"))
                QTimer.singleShot(0, lambda: self.scan_subnet_btn.setEnabled(True))
                return
            
            parts = local_ip.split('.')
            base = f"{parts[0]}.{parts[1]}.{parts[2]}."
            
            threads = []
            found_ip = []

            def _ping_port(ip):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    s.connect((ip, ADB_PORT))
                    s.close()
                    found_ip.append(ip)
                except:
                    pass

            for i in range(1, 255):
                t = threading.Thread(target=_ping_port, args=(base + str(i),), daemon=True)
                threads.append(t)
                t.start()
                if i % 50 == 0:
                    time.sleep(0.05) # mitigate socket overload

            for t in threads:
                t.join()

            def _done():
                self.scan_subnet_btn.setEnabled(True)
                if found_ip:
                    gui_log(f"Subnet scanner discovered ADB: {found_ip[0]}")
                    self.handle_heartbeat(found_ip[0])
                else:
                    self.status_label.setText("No phones found on subnet.")
                    gui_log("No ADB ports open on local subnet.")
            QTimer.singleShot(0, _done)

        threading.Thread(target=_scan, daemon=True).start()

    def handle_heartbeat(self, ip):
        self.status_label.setText(f"Found phone at {ip}! Launching...")
        threading.Thread(target=self.connect_and_launch, args=(ip,), daemon=True).start()

    def connect_and_launch(self, ip):
        preset_args = self.scrcpy_presets.get(SCRCPY_PRESET, [])
        success = start_scrcpy(ip, ADB_PORT, preset_args)
        if success:
            QTimer.singleShot(0, lambda: self.status_label.setText(f"Mirrored successfully! Preset: {SCRCPY_PRESET}"))
        else:
            QTimer.singleShot(0, lambda: self.status_label.setText("Mirror connection failed."))

    def on_port_changed(self):
        global HEARTBEAT_PORT, DISCOVERY_PORT, ADB_PORT
        HEARTBEAT_PORT = self.heartbeat_port_spin.value()
        DISCOVERY_PORT = self.discovery_port_spin.value()
        ADB_PORT = self.adb_port_spin.value()
        config["heartbeat_port"] = HEARTBEAT_PORT
        config["discovery_port"] = DISCOVERY_PORT
        config["adb_port"] = ADB_PORT
        save_config(config)
        if self.worker:
            self.start_heartbeat_mode()

    def browse_scrcpy_binary(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select scrcpy Binary", "", "Executables (*)")
        if file_path:
            self.scrcpy_path_edit.setText(file_path)
            global SCRCPY_BIN
            SCRCPY_BIN = file_path
            config["scrcpy_bin"] = file_path
            save_config(config)

    def add_log(self, message):
        self.log_area.append(message)
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        self.file_server.stop()
        if hasattr(self, 'discovery') and self.discovery:
            self.discovery.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScrcpyUltimateLink()
    window.show()
    sys.exit(app.exec())
