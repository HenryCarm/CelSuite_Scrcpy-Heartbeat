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
    QGroupBox, QFormLayout, QLineEdit, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon
from heartbeat_listener import start_scrcpy, get_local_ip, LOG_FILE
from file_transfer import FileTransferScreen, PullScreen

APP_VERSION = "4.27.0"
APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

# Default desktop path for last_ip.txt
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
        "connection_mode": "heartbeat"  # "heartbeat" or "saved_ip"
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

def gui_log(msg):
    if not LOGGING_ENABLED:
        return ""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] [GUI] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)
    return line

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

        gui_log(f"Starting discovery broadcast on port {self.port} (PC IP: {self.local_ip})")

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
        gui_log("HeartbeatWorker thread starting...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", HEARTBEAT_PORT))
            gui_log(f"GUI listener bound to 0.0.0.0:{HEARTBEAT_PORT}")
            sock.settimeout(60.0)
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    ip = addr[0]
                    message = data.decode('utf-8').strip()
                    gui_log(f"GUI got packet from {ip}:{addr[1]} -> '{message}'")
                    if "HELLO_" in message:
                        gui_log(f"VALID heartbeat from {ip}")
                        self.heartbeat_received.emit(ip)
                    else:
                        gui_log(f"Ignoring non-HELLO: '{message}'")
                except socket.timeout:
                    pass
        except Exception as e:
            gui_log(f"GUI Listener Error: {e}")
            self.log_signal.emit(f"Listener Error: {e}")

    def gui_log(self, msg):
        self.log_signal.emit(msg)

class StartupScreen(QWidget):
    """Welcome screen with two main action buttons"""
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Scrcpy Ultimate Link")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #00d9a5;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Wireless Screen Mirroring & Control")
        subtitle.setStyleSheet("font-size: 16px; color: #888;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Button 1: Mirror Phone
        self.mirror_btn = QPushButton("📱 Mirror Phone")
        self.mirror_btn.setMinimumSize(300, 80)
        self.mirror_btn.setStyleSheet("""
            QPushButton { 
                background-color: #0f3460; 
                color: #00d9a5; 
                border: 3px solid #00d9a5; 
                border-radius: 12px; 
                padding: 20px; 
                font-size: 18px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #00d9a5; 
                color: #1a1a2e; 
            }
        """)
        self.mirror_btn.clicked.connect(lambda: parent_window.show_main_tab(0))

        # Button 2: File Transfer
        self.transfer_btn = QPushButton("File Transfer (PC -> Phone)")
        self.transfer_btn.setMinimumSize(300, 80)
        self.transfer_btn.setStyleSheet("""
            QPushButton { 
                background-color: #1a1a2e; 
                color: #00d9a5; 
                border: 3px solid #00d9a5; 
                border-radius: 12px; 
                padding: 20px; 
                font-size: 18px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #00d9a5; 
                color: #1a1a2e; 
            }
        """)
        self.transfer_btn.clicked.connect(lambda: parent_window.show_file_transfer())

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(self.mirror_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.transfer_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

class ScrcpyUltimateLink(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Scrcpy Ultimate Link v{APP_VERSION}")
        self.setMinimumSize(700, 550)
        icon_path = os.path.join(APP_DIR, "android", "icon.png")
        self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QMainWindow, QTabWidget::pane { background-color: #1a1a2e; border: none; }
            QLabel { color: #e0e0e0; }
            QTextEdit { background-color: #16213e; border: 1px solid #0f3460; border-radius: 8px; padding: 10px; color: #e0e0e0; font-family: monospace; font-size: 12px; }
            QSpinBox { background-color: #16213e; border: 1px solid #0f3460; border-radius: 4px; padding: 5px; color: #e0e0e0; font-size: 14px; }
            QLineEdit { background-color: #16213e; border: 1px solid #0f3460; border-radius: 4px; padding: 5px; color: #e0e0e0; font-size: 14px; }
            QPushButton { background-color: #0f3460; color: #00d9a5; border: 2px solid #00d9a5; border-radius: 8px; padding: 12px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #00d9a5; color: #1a1a2e; }
            QPushButton:disabled { background-color: #1a1a2e; color: #666; border-color: #444; }
            QCheckBox { color: #e0e0e0; font-size: 14px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #00d9a5; border-radius: 4px; background: #16213e; }
            QCheckBox::indicator:checked { background: #00d9a5; }
            QGroupBox { color: #00d9a5; font-weight: bold; font-size: 14px; border: 2px solid #0f3460; border-radius: 8px; margin-top: 12px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QTabBar::tab { background: #16213e; color: #00d9a5; padding: 10px 20px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
            QTabBar::tab:selected { background: #0f3460; font-weight: bold; }
        """)

        # Main stacked widget: Index 0 = Startup, Index 1 = Main Tabs
        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        # --- STARTUP SCREEN (Index 0) ---
        self.startup_screen = StartupScreen(self)
        self.stacked.addWidget(self.startup_screen)

        # --- MAIN TABS (Index 1) ---
        self.main_tabs = QWidget()
        tabs_layout = QVBoxLayout(self.main_tabs)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(0)

        self.tabs = QTabWidget()
        tabs_layout.addWidget(self.tabs)

        # --- MAIN TAB (Mirror Phone) ---
        self.main_tab = QWidget()
        main_layout = QVBoxLayout(self.main_tab)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        self.title = QLabel("Scrcpy Ultimate Link")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00d9a5;")
        header_layout.addWidget(self.title)
        header_layout.addStretch()

        # Connection mode buttons
        self.connect_saved_btn = QPushButton("🔗 Connect Using Saved IP")
        self.connect_saved_btn.setMinimumHeight(45)
        self.connect_saved_btn.clicked.connect(self.connect_using_saved_ip)

        self.connect_heartbeat_btn = QPushButton("🔍 Auto-Discover (Heartbeat)")
        self.connect_heartbeat_btn.setMinimumHeight(45)
        self.connect_heartbeat_btn.clicked.connect(self.start_heartbeat_mode)

        header_layout.addWidget(self.connect_saved_btn)
        header_layout.addWidget(self.connect_heartbeat_btn)
        main_layout.addLayout(header_layout)

        # Status
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d9a5;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        # Log area (bottom)
        log_group = QGroupBox("Live Logs")
        log_layout = QVBoxLayout(log_group)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(200)
        log_layout.addWidget(self.log_area)
        main_layout.addWidget(log_group)

        self.tabs.addTab(self.main_tab, "📱 Mirror Phone")

        # --- SETTINGS TAB ---
        self.settings_tab = QWidget()
        settings_outer = QVBoxLayout(self.settings_tab)
        settings_outer.setContentsMargins(0, 0, 0, 0)
        settings_outer.setSpacing(0)
        
        from PyQt6.QtWidgets import QScrollArea
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        settings_layout.setSpacing(20)
        settings_layout.setContentsMargins(20, 20, 20, 20)

        # Ports Group
        ports_group = QGroupBox("Network Ports")
        ports_form = QFormLayout(ports_group)
        ports_form.setSpacing(15)

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

        # scrcpy Binary Path
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

        # IP File Location
        ip_file_group = QGroupBox("Saved IP File Location")
        ip_file_form = QFormLayout(ip_file_group)
        ip_file_layout = QHBoxLayout()
        self.ip_file_edit = QLineEdit(LAST_IP_FILE)
        self.ip_file_edit.setReadOnly(True)
        self.ip_file_browse_btn = QPushButton("Browse...")
        self.ip_file_browse_btn.clicked.connect(self.browse_ip_file)
        ip_file_layout.addWidget(self.ip_file_edit)
        ip_file_layout.addWidget(self.ip_file_browse_btn)
        ip_file_form.addRow("File Path:", ip_file_layout)
        settings_layout.addWidget(ip_file_group)

        # Logging Group
        log_group = QGroupBox("Logging")
        log_layout = QVBoxLayout(log_group)
        
        self.log_checkbox = QCheckBox("Enable Logging (persists across restarts)")
        self.log_checkbox.setChecked(LOGGING_ENABLED)
        self.log_checkbox.toggled.connect(self.on_log_toggled)
        log_layout.addWidget(self.log_checkbox)
        
        self.log_path_label = QLabel(f"Log file: {LOG_FILE}")
        self.log_path_label.setStyleSheet("color: #888; font-size: 12px; font-family: monospace;")
        log_layout.addWidget(self.log_path_label)
        
        settings_layout.addWidget(log_group)

        # Connection Mode
        conn_mode_group = QGroupBox("Default Connection Mode")
        conn_mode_layout = QVBoxLayout(conn_mode_group)
        
        self.conn_mode_heartbeat = QCheckBox("Auto-Discover via Heartbeat (recommended)")
        self.conn_mode_heartbeat.setChecked(CONNECTION_MODE == "heartbeat")
        self.conn_mode_heartbeat.toggled.connect(self.on_conn_mode_changed)
        conn_mode_layout.addWidget(self.conn_mode_heartbeat)
        
        self.conn_mode_saved = QCheckBox("Connect Using Saved IP File")
        self.conn_mode_saved.setChecked(CONNECTION_MODE == "saved_ip")
        self.conn_mode_saved.toggled.connect(self.on_conn_mode_changed)
        conn_mode_layout.addWidget(self.conn_mode_saved)
        
        settings_layout.addWidget(conn_mode_group)
        settings_layout.addStretch()
        
        settings_scroll.setWidget(settings_widget)
        settings_outer.addWidget(settings_scroll)
        
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")

        # --- HELP TAB ---
        self.help_tab = QWidget()
        help_layout = QVBoxLayout(self.help_tab)
        help_layout.setContentsMargins(20, 20, 20, 20)

        help_title = QLabel("📖 Complete Setup Guide")
        help_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00d9a5;")
        help_layout.addWidget(help_title)

        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setStyleSheet("background-color: #16213e; border: none; color: #e0e0e0; font-size: 14px;")
        self.help_text.setHtml(
            "<b>🚀 Quick Start:</b><br/>"
            "1. Make sure your phone and PC are on the same network (or phone hotspot)<br/>"
            "2. Open this app on PC, then open 'Scrcpy Heartbeat' on your phone<br/>"
            "3. Tap 'Restart Connection' on phone if needed<br/>"
            "4. scrcpy will launch automatically!<br/><br/>"

            "<b>📱 Android App Install:</b><br/>"
            "• Download APK from GitHub Actions artifacts<br/>"
            "• Install on phone (allow unknown sources)<br/>"
            "• Grant all permissions when prompted<br/><br/>"

            "<b>⚡ Shizuku Setup (Persistent ADB over WiFi):</b><br/>"
            "1. Install <b>Magisk</b> → Install <b>Shizuku</b> module in Magisk app → Reboot<br/>"
            "2. Open <b>Shizuku</b> app → Start service (grant root when prompted)<br/>"
            "3. Install <b>Termux</b> + <b>Termux:Boot</b> from F-Droid/Play Store<br/>"
            "4. In Termux, run:<br/>"
            "<code style='color:#00d9a5;'>su -c \"setprop service.adb.tcp.port 5555; setprop persist.adb.tcp.port 5555; "
            "setprop service.adb.tcp.bind 0.0.0.0; stop adbd && start adbd\"</code><br/>"
            "5. Create Termux:Boot script: <code style='color:#00d9a5;'>~/.termux/boot/99-adb-wifi.sh</code><br/>"
            "6. Whitelist from battery optimization:<br/>"
            "<code style='color:#00d9a5;'>su -c \"cmd appops set com.termux RUN_IN_BACKGROUND allow\"</code><br/>"
            "<code style='color:#00d9a5;'>su -c \"dumpsys deviceidle whitelist +com.termux\"</code><br/><br/>"

            "<b>🔧 Port Configuration:</b><br/>"
            "• Heartbeat Port (default 5556): Phone→PC discovery<br/>"
            "• Discovery Port (default 5557): PC broadcast<br/>"
            "• ADB Port (default 5555): scrcpy connection<br/>"
            "Change ports in the Settings tab, then click 'Restart Server'<br/><br/>"

            "<b>🔗 Connection Modes:</b><br/>"
            "• <b>Auto-Discover (Heartbeat)</b>: Phone broadcasts, PC listens, auto-connects<br/>"
            "• <b>Connect Using Saved IP</b>: Reads IP from file, connects directly (faster for known IPs)<br/><br/>"

            "<b>🔍 Troubleshooting:</b><br/>"
            "• Phone not found? Check both devices on same network<br/>"
            "• ADB connection refused? Run Shizuku ADB command on phone<br/>"
            "• IP cycling? Restart both apps using restart buttons<br/>"
            "• Black screen on phone? Tap 'Restart Connection' on phone app<br/>"
            "• 'unrecognized option' error? Ensure scrcpy v4.0+ is configured<br/><br/>"

            "<b>🔗 Links:</b><br/>"
            "• GitHub: <a href='https://github.com/HenryCarm/ScrcpyUltimateLink' style='color:#00d9a5;'>github.com/HenryCarm/ScrcpyUltimateLink</a><br/>"
            "• Shizuku: <a href='https://shizuku.rikka.app/' style='color:#00d9a5;'>shizuku.rikka.app</a><br/>"
            "• Termux:Boot: <a href='https://f-droid.org/packages/com.termux.boot/' style='color:#00d9a5;'>F-Droid</a>"
        )
        help_layout.addWidget(self.help_text)
        self.tabs.addTab(self.help_tab, "📖 Help")

        # Add tabs widget to main_tabs
        self.stacked.addWidget(self.main_tabs)

        # --- FILE TRANSFER SCREEN (Index 2) with Push/Pull tabs ---
        from PyQt6.QtWidgets import QTabWidget
        
        file_transfer_container = QWidget()
        file_transfer_layout = QVBoxLayout(file_transfer_container)
        file_transfer_layout.setContentsMargins(0, 0, 0, 0)
        
        file_tabs = QTabWidget()
        file_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #0f3460; border-radius: 8px; background-color: #1a1a2e; }
            QTabBar::tab { background-color: #16213e; color: #888; padding: 10px 20px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background-color: #0f3460; color: #00d9a5; font-weight: bold; }
            QTabBar::tab:hover { background-color: #1a1a2e; color: #00d9a5; }
        """)
        
        self.file_transfer_screen = FileTransferScreen(
            get_device_ip_func=lambda: self.get_current_phone_ip()
        )
        self.pull_screen = PullScreen(
            get_device_ip_func=lambda: self.get_current_phone_ip()
        )
        
        file_tabs.addTab(self.file_transfer_screen, "Push to Phone")
        file_tabs.addTab(self.pull_screen, "Pull from Phone")
        
        file_transfer_layout.addWidget(file_tabs)
        self.stacked.addWidget(file_transfer_container)

        # Initialize threads
        self.discovery = None
        self.worker = None
        self.thread = None

    def show_main_tab(self, tab_index):
        """Switch from startup screen to main tabs"""
        self.stacked.setCurrentIndex(1)
        self.tabs.setCurrentIndex(tab_index)

    def show_file_transfer(self):
        """Switch to file transfer screen"""
        self.stacked.setCurrentIndex(2)

    def get_current_phone_ip(self):
        """Return the last known phone IP"""
        ip = self.read_saved_ip()
        return ip

    def start_heartbeat_mode(self):
        """Start discovery broadcast and heartbeat listener (singleton — won't duplicate)"""
        global HEARTBEAT_PORT, DISCOVERY_PORT, ADB_PORT
        
        # Prevent duplicate threads
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

        self.connect_heartbeat_btn.setStyleSheet("""
            QPushButton { background-color: #00d9a5; color: #1a1a2e; border: 2px solid #00d9a5; border-radius: 8px; padding: 12px; font-size: 14px; font-weight: bold; }
        """)
        self.connect_saved_btn.setStyleSheet("""
            QPushButton { background-color: #0f3460; color: #00d9a5; border: 2px solid #00d9a5; border-radius: 8px; padding: 12px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #00d9a5; color: #1a1a2e; }
        """)
        self.status_label.setText("Status: Listening for phone heartbeat...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d9a5;")
        self.add_log("Heartbeat mode started - waiting for phone...")

    def connect_using_saved_ip(self):
        """Read IP from saved file and connect"""
        ip = self.read_saved_ip()
        if not ip:
            self.status_label.setText("No saved IP found!")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff6b6b;")
            self.add_log("No saved IP file found")
            QMessageBox.warning(self, "No Saved IP", f"No IP found in:\n{LAST_IP_FILE}\n\nRun heartbeat mode first to discover and save the IP.")
            return

        self.status_label.setText(f"Connecting to saved IP: {ip}...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffcc00;")
        self.add_log(f"Connecting using saved IP: {ip}")
        
        self.connect_saved_btn.setStyleSheet("""
            QPushButton { background-color: #00d9a5; color: #1a1a2e; border: 2px solid #00d9a5; border-radius: 8px; padding: 12px; font-size: 14px; font-weight: bold; }
        """)
        self.connect_heartbeat_btn.setStyleSheet("""
            QPushButton { background-color: #0f3460; color: #00d9a5; border: 2px solid #00d9a5; border-radius: 8px; padding: 12px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #00d9a5; color: #1a1a2e; }
        """)
        
        threading.Thread(target=self.connect_and_launch, args=(ip,), daemon=True).start()

    def read_saved_ip(self):
        """Read IP from the saved file"""
        try:
            if os.path.exists(LAST_IP_FILE):
                with open(LAST_IP_FILE, "r") as f:
                    return f.read().strip()
        except:
            pass
        return None

    def on_port_changed(self):
        global HEARTBEAT_PORT, DISCOVERY_PORT, ADB_PORT
        HEARTBEAT_PORT = self.heartbeat_port_spin.value()
        DISCOVERY_PORT = self.discovery_port_spin.value()
        ADB_PORT = self.adb_port_spin.value()
        config = load_config()
        config["heartbeat_port"] = HEARTBEAT_PORT
        config["discovery_port"] = DISCOVERY_PORT
        config["adb_port"] = ADB_PORT
        save_config(config)
        gui_log(f"Ports updated: Heartbeat={HEARTBEAT_PORT}, Discovery={DISCOVERY_PORT}, ADB={ADB_PORT}")
        self.add_log(f"Ports updated: Heartbeat={HEARTBEAT_PORT}, Discovery={DISCOVERY_PORT}, ADB={ADB_PORT}")
        if self.worker:
            self.start_heartbeat_mode()

    def browse_scrcpy_binary(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select scrcpy Binary", "", "Executables (*)")
        if file_path:
            self.scrcpy_path_edit.setText(file_path)
            global SCRCPY_BIN
            SCRCPY_BIN = file_path
            config = load_config()
            config["scrcpy_bin"] = file_path
            save_config(config)
            gui_log(f"scrcpy binary set to: {file_path}")
            self.add_log(f"scrcpy binary set to: {file_path}")

    def browse_ip_file(self):
        global LAST_IP_FILE
        file_path, _ = QFileDialog.getSaveFileName(self, "Select IP File Location", LAST_IP_FILE, "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.ip_file_edit.setText(file_path)
            LAST_IP_FILE = file_path
            config = load_config()
            config["last_ip_file"] = file_path
            save_config(config)
            gui_log(f"IP file location set to: {file_path}")
            self.add_log(f"IP file location set to: {file_path}")

    def on_log_toggled(self, checked):
        global LOGGING_ENABLED, LOG_FILE
        LOGGING_ENABLED = checked
        config = load_config()
        config["logging_enabled"] = checked
        save_config(config)
        gui_log(f"Logging {'enabled' if checked else 'disabled'}")
        self.add_log(f"Logging {'enabled' if checked else 'disabled'}")

    def on_conn_mode_changed(self):
        global CONNECTION_MODE
        if self.conn_mode_heartbeat.isChecked():
            CONNECTION_MODE = "heartbeat"
            self.conn_mode_saved.setChecked(False)
        elif self.conn_mode_saved.isChecked():
            CONNECTION_MODE = "saved_ip"
            self.conn_mode_heartbeat.setChecked(False)
        else:
            CONNECTION_MODE = "heartbeat"
            self.conn_mode_heartbeat.setChecked(True)
        
        config = load_config()
        config["connection_mode"] = CONNECTION_MODE
        save_config(config)
        gui_log(f"Default connection mode set to: {CONNECTION_MODE}")
        self.add_log(f"Default connection mode set to: {CONNECTION_MODE}")

    def add_log(self, message):
        if LOGGING_ENABLED:
            self.log_area.append(message)
            scrollbar = self.log_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def handle_heartbeat(self, ip):
        self.status_label.setText(f"Found {ip}! Connecting...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d9a5;")
        threading.Thread(target=self.connect_and_launch, args=(ip,), daemon=True).start()

    def connect_and_launch(self, ip):
        if start_scrcpy(ip):
            self.status_label.setText("Launched! Enjoy!")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d9a5;")
            self.add_log(f"Successfully connected to {ip}")
        else:
            self.status_label.setText("Connection failed...")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff6b6b;")
            self.add_log(f"Failed to connect to {ip}")

    def closeEvent(self, event):
        if hasattr(self, 'discovery') and self.discovery:
            self.discovery.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = os.path.join(APP_DIR, "android", "icon.png")
    app.setWindowIcon(QIcon(icon_path))
    window = ScrcpyUltimateLink()
    window.show()
    sys.exit(app.exec())