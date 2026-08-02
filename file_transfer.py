import os
import sys
import time
import socket
import json
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QFileDialog, QMessageBox, QFrame, QGroupBox,
    QListWidget, QListWidgetItem, QSplitter
)
# Make sure we use absolute imports or relative imports depending on setup
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer

FILE_TYPE_ICONS = {
    '.mp4': '🎥', '.mkv': '🎥', '.avi': '🎥', '.mov': '🎥',
    '.png': '🖼️', '.jpg': '🖼️', '.jpeg': '🖼️', '.webp': '🖼️', '.gif': '🖼️',
    '.apk': '📦',
    '.mp3': '🎵', '.wav': '🎵', '.ogg': '🎵', '.flac': '🎵',
    '.pdf': '📄', '.doc': '📄', '.docx': '📄', '.txt': '📄',
    '.zip': '🗜️', '.tar': '🗜️', '.gz': '🗜️',
}

def get_file_type_icon(filename):
    ext = os.path.splitext(filename)[1].lower()
    return FILE_TYPE_ICONS.get(ext, '📁')

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

PORT_TCP_TRANSFER = 5558
LARGE_FILE_THRESHOLD = 200 * 1024 * 1024  # 200MB

class DropZone(QFrame):
    file_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QFrame { 
                border: 2px dashed #00d9a5; 
                border-radius: 12px; 
                background-color: #16213e; 
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        drop_label = QLabel("Drag & Drop File Here\n-- or --")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet("color: #888; font-size: 14px; border: none; background: transparent;")
        
        self.file_label = QLabel("")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setStyleSheet("color: #00d9a5; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        
        browse_btn = QPushButton("Browse File...")
        browse_btn.setFixedWidth(180)
        browse_btn.setStyleSheet("""
            QPushButton { 
                background-color: #0f3460; 
                color: #00d9a5; 
                font-weight: bold; 
                border-radius: 6px; 
                padding: 10px; 
                border: 1px solid #00d9a5;
            }
            QPushButton:hover { background-color: #00d9a5; color: #1a1a2e; }
        """)
        browse_btn.clicked.connect(self.browse_file)
        
        layout.addWidget(drop_label)
        layout.addWidget(self.file_label)
        layout.addWidget(browse_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QFrame { border: 2px solid #00d9a5; background-color: #1f2e5a; border-radius: 12px; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("QFrame { border: 2px dashed #00d9a5; background-color: #16213e; border-radius: 12px; }")

    def dropEvent(self, event):
        self.dragLeaveEvent(event)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.file_label.setText(f"{get_file_type_icon(os.path.basename(file_path))} {os.path.basename(file_path)}")
                self.file_selected.emit(file_path)
                break

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Send", "", "All Files (*)")
        if path:
            self.file_label.setText(f"{get_file_type_icon(os.path.basename(path))} {os.path.basename(path)}")
            self.file_selected.emit(path)


class TCPFileClient(QObject):
    progress_updated = pyqtSignal(int, float, float)  # percent, speed_mbps, eta_seconds
    transfer_finished = pyqtSignal(bool, str)  # success, message
    file_list_ready = pyqtSignal(list)  # list of dicts: [{"name": str, "size": int}]

    def __init__(self):
        super().__init__()
        self.running = False

    def send_file(self, local_path, device_ip):
        if not os.path.exists(local_path):
            self.transfer_finished.emit(False, "Local file not found.")
            return

        def _thread():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            try:
                sock.connect((device_ip, PORT_TCP_TRANSFER))
                filesize = os.path.getsize(local_path)
                filename = os.path.basename(local_path)
                
                # Send Header: FILE_SEND|filename|filesize\n
                header = f"FILE_SEND|{filename}|{filesize}\n"
                sock.sendall(header.encode('utf-8'))
                
                sent_bytes = 0
                start_time = time.time()
                last_progress_time = start_time
                last_bytes = 0
                
                with open(local_path, "rb") as f:
                    while sent_bytes < filesize:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        sock.sendall(chunk)
                        sent_bytes += len(chunk)
                        
                        now = time.time()
                        if now - last_progress_time >= 0.5:
                            dt = now - last_progress_time
                            delta = sent_bytes - last_bytes
                            speed = (delta / dt) / (1024 * 1024)
                            percent = int((sent_bytes / filesize) * 100)
                            eta = (filesize - sent_bytes) / (delta / dt) if delta > 0 else 0
                            self.progress_updated.emit(percent, speed, eta)
                            
                            last_bytes = sent_bytes
                            last_progress_time = now
                
                sock.close()
                self.progress_updated.emit(100, 0, 0)
                self.transfer_finished.emit(True, f"Successfully sent '{filename}' to phone!")
            except Exception as e:
                try: sock.close()
                except: pass
                self.transfer_finished.emit(False, f"Connection failed: {e}")

        threading.Thread(target=_thread, daemon=True).start()

    def request_file_list(self, device_ip):
        def _thread():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(6.0)
            try:
                sock.connect((device_ip, PORT_TCP_TRANSFER))
                sock.sendall(b"FILE_LIST\n")
                
                # Read all response until closed
                resp_bytes = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    resp_bytes += chunk
                
                sock.close()
                data = json.loads(resp_bytes.decode('utf-8').strip())
                self.file_list_ready.emit(data)
            except Exception as e:
                try: sock.close()
                except: pass
                self.file_list_ready.emit([])

        threading.Thread(target=_thread, daemon=True).start()

    def pull_file(self, remote_filename, device_ip, local_save_path):
        def _thread():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15.0)
            try:
                sock.connect((device_ip, PORT_TCP_TRANSFER))
                req = f"FILE_GET|{remote_filename}\n"
                sock.sendall(req.encode('utf-8'))
                
                # Server sends header: FILE_SEND|filename|size\n
                header_bytes = b""
                while b"\n" not in header_bytes:
                    c = sock.recv(1)
                    if not c:
                        break
                    header_bytes += c
                
                header = header_bytes.decode('utf-8', errors='ignore').strip()
                if not header.startswith("FILE_SEND|"):
                    raise Exception("Invalid server response")
                
                parts = header.split('|')
                filesize = int(parts[2])
                
                received_bytes = 0
                start_time = time.time()
                last_progress_time = start_time
                last_bytes = 0
                
                with open(local_save_path, "wb") as f:
                    while received_bytes < filesize:
                        to_read = min(65536, filesize - received_bytes)
                        chunk = sock.recv(to_read)
                        if not chunk:
                            raise Exception("Disconnected prematurely")
                        f.write(chunk)
                        received_bytes += len(chunk)
                        
                        now = time.time()
                        if now - last_progress_time >= 0.5:
                            dt = now - last_progress_time
                            delta = received_bytes - last_bytes
                            speed = (delta / dt) / (1024 * 1024)
                            percent = int((received_bytes / filesize) * 100)
                            eta = (filesize - received_bytes) / (delta / dt) if delta > 0 else 0
                            self.progress_updated.emit(percent, speed, eta)
                            
                            last_bytes = received_bytes
                            last_progress_time = now
                
                sock.close()
                self.progress_updated.emit(100, 0, 0)
                self.transfer_finished.emit(True, f"Successfully downloaded '{remote_filename}' to PC!")
            except Exception as e:
                try: sock.close()
                except: pass
                self.transfer_finished.emit(False, f"Download failed: {e}")

        threading.Thread(target=_thread, daemon=True).start()


class TCPFileServer(QObject):
    progress_updated = pyqtSignal(int, float, float)  # percent, speed_mbps, eta_seconds
    transfer_finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, port=PORT_TCP_TRANSFER, save_dir=None):
        super().__init__()
        self.port = port
        self.save_dir = save_dir or os.path.expanduser("~/Downloads")
        self.sock = None
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.running = False
        if self.sock:
            try: self.sock.close()
            except: pass

    def _run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(("0.0.0.0", self.port))
            self.sock.listen(1)
        except Exception as e:
            return

        while self.running:
            try:
                conn, addr = self.sock.accept()
                self._handle_client(conn, addr[0])
            except:
                time.sleep(1)

    def _handle_client(self, conn, ip):
        try:
            conn.settimeout(15.0)
            header_bytes = b""
            while b"\n" not in header_bytes:
                c = conn.recv(1)
                if not c:
                    break
                header_bytes += c
            
            if not header_bytes:
                conn.close()
                return
            
            header = header_bytes.decode('utf-8', errors='ignore').strip()
            if header == "FILE_LIST":
                # Send PC files in Downloads
                os.makedirs(self.save_dir, exist_ok=True)
                files = []
                for f in os.listdir(self.save_dir):
                    p = os.path.join(self.save_dir, f)
                    if os.path.isfile(p):
                        files.append({"name": f, "size": os.path.getsize(p)})
                conn.sendall((json.dumps(files) + "\n").encode('utf-8'))
                conn.close()
                return
            elif header.startswith("FILE_GET|"):
                parts = header.split('|')
                fname = parts[1]
                p = os.path.join(self.save_dir, fname)
                if os.path.exists(p):
                    filesize = os.path.getsize(p)
                    conn.sendall(f"FILE_SEND|{fname}|{filesize}\n".encode('utf-8'))
                    with open(p, "rb") as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            conn.sendall(chunk)
                conn.close()
                return
            elif header.startswith("FILE_SEND|"):
                parts = header.split('|')
                filename = parts[1]
                filesize = int(parts[2])
                
                os.makedirs(self.save_dir, exist_ok=True)
                filepath = os.path.join(self.save_dir, filename)
                
                received_bytes = 0
                start_time = time.time()
                last_progress_time = start_time
                last_bytes = 0
                
                with open(filepath, "wb") as f:
                    while received_bytes < filesize:
                        to_read = min(65536, filesize - received_bytes)
                        chunk = conn.recv(to_read)
                        if not chunk:
                            raise Exception("Disconnected")
                        f.write(chunk)
                        received_bytes += len(chunk)
                        
                        now = time.time()
                        if now - last_progress_time >= 0.5:
                            dt = now - last_progress_time
                            delta = received_bytes - last_bytes
                            speed = (delta / dt) / (1024 * 1024)
                            percent = int((received_bytes / filesize) * 100)
                            eta = (filesize - received_bytes) / (delta / dt) if delta > 0 else 0
                            self.progress_updated.emit(percent, speed, eta)
                            
                            last_bytes = received_bytes
                            last_progress_time = now
                
                conn.close()
                self.progress_updated.emit(100, 0, 0)
                self.transfer_finished.emit(True, f"Received file from mobile: '{filename}'")
        except Exception as e:
            try: conn.close()
            except: pass
            self.transfer_finished.emit(False, str(e))


class FileTransferScreen(QWidget):
    def __init__(self, get_device_ip_func, log_callback=None):
        super().__init__()
        self.get_device_ip = get_device_ip_func
        self.log = log_callback or print
        self.client = TCPFileClient()
        self.client.progress_updated.connect(self.update_progress)
        self.client.transfer_finished.connect(self.on_transfer_finished)
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("WiFi File Push (PC ➔ Phone)")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00d9a5;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.drop_zone = DropZone()
        self.drop_zone.file_selected.connect(self.on_file_selected)
        layout.addWidget(self.drop_zone)

        self.file_info = QLabel("No file selected")
        self.file_info.setStyleSheet("color: #888; font-size: 14px;")
        self.file_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.file_info)

        progress_group = QGroupBox("Push Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #0f3460; border-radius: 6px; text-align: center; color: white; font-weight: bold; height: 24px; background-color: #1a1a2e; }
            QProgressBar::chunk { background-color: #00d9a5; border-radius: 5px; }
        """)
        progress_layout.addWidget(self.progress_bar)

        stats_layout = QHBoxLayout()
        self.speed_label = QLabel("Speed: -- MB/s")
        self.speed_label.setStyleSheet("color: #888; font-size: 12px;")
        self.eta_label = QLabel("ETA: --:--")
        self.eta_label.setStyleSheet("color: #888; font-size: 12px;")
        self.size_label = QLabel("Size: --")
        self.size_label.setStyleSheet("color: #888; font-size: 12px;")
        stats_layout.addWidget(self.speed_label)
        stats_layout.addWidget(self.eta_label)
        stats_layout.addWidget(self.size_label)
        progress_layout.addLayout(stats_layout)
        layout.addWidget(progress_group)

        self.send_btn = QPushButton("🚀 Send File Over WiFi")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.start_transfer)
        layout.addWidget(self.send_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 13px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def on_file_selected(self, file_path):
        self.selected_file = file_path
        size = os.path.getsize(file_path)
        self.file_info.setText(f"{get_file_type_icon(os.path.basename(file_path))} {os.path.basename(file_path)}")
        self.send_btn.setEnabled(True)
        self.size_label.setText(f"Size: {format_size(size)}")

    def start_transfer(self):
        ip = self.get_device_ip()
        if not ip:
            QMessageBox.warning(self, "No Device Connected", "Make sure your phone is discovered first!")
            return
        
        self.send_btn.setEnabled(False)
        self.status_label.setText("Sending file wirelessly...")
        self.client.send_file(self.selected_file, ip)

    def update_progress(self, percent, speed, eta):
        self.progress_bar.setValue(percent)
        self.speed_label.setText(f"Speed: {speed:.1f} MB/s")
        if percent < 100 and eta > 0:
            self.eta_label.setText(f"ETA: {int(eta)//60:02d}:{int(eta)%60:02d}")
        else:
            self.eta_label.setText("ETA: --:--")

    def on_transfer_finished(self, success, msg):
        self.send_btn.setEnabled(True)
        self.status_label.setText(msg)
        if success:
            self.status_label.setStyleSheet("color: #00d9a5;")
        else:
            self.status_label.setStyleSheet("color: #ff6b6b;")


class PullScreen(QWidget):
    def __init__(self, get_device_ip_func, log_callback=None):
        super().__init__()
        self.get_device_ip = get_device_ip_func
        self.log = log_callback or print
        self.client = TCPFileClient()
        self.client.progress_updated.connect(self.update_progress)
        self.client.transfer_finished.connect(self.on_transfer_finished)
        self.client.file_list_ready.connect(self.on_file_list_ready)
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("WiFi File Pull (Phone ➔ PC)")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00d9a5;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.refresh_btn = QPushButton("🔄 Refresh Remote File List")
        self.refresh_btn.clicked.connect(self.refresh_files)
        layout.addWidget(self.refresh_btn)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget { background-color: #1a1a2e; color: #e0e0e0; border: 2px solid #0f3460; border-radius: 8px; font-size: 14px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #0f3460; }
            QListWidget::item:selected { background-color: #0f3460; color: #00d9a5; }
        """)
        layout.addWidget(self.file_list)

        self.selected_info = QLabel("No remote file selected")
        self.selected_info.setStyleSheet("color: #888; font-size: 13px;")
        self.selected_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.selected_info)

        progress_group = QGroupBox("Pull Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #0f3460; border-radius: 6px; text-align: center; color: white; font-weight: bold; height: 24px; background-color: #1a1a2e; }
            QProgressBar::chunk { background-color: #00d9a5; border-radius: 5px; }
        """)
        progress_layout.addWidget(self.progress_bar)

        stats_layout = QHBoxLayout()
        self.speed_label = QLabel("Speed: -- MB/s")
        self.speed_label.setStyleSheet("color: #888; font-size: 11px;")
        self.eta_label = QLabel("ETA: --:--")
        self.eta_label.setStyleSheet("color: #888; font-size: 11px;")
        self.size_label = QLabel("Size: --")
        self.size_label.setStyleSheet("color: #888; font-size: 11px;")
        stats_layout.addWidget(self.speed_label)
        stats_layout.addWidget(self.eta_label)
        stats_layout.addWidget(self.size_label)
        progress_layout.addLayout(stats_layout)
        layout.addWidget(progress_group)

        self.pull_btn = QPushButton("📥 Pull Selected File")
        self.pull_btn.setEnabled(False)
        self.pull_btn.clicked.connect(self.start_pull)
        layout.addWidget(self.pull_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 13px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def refresh_files(self):
        ip = self.get_device_ip()
        if not ip:
            QMessageBox.warning(self, "No Device Connected", "No discovered device found.")
            return
        self.file_list.clear()
        self.file_list.addItem("Fetching file list over TCP...")
        self.client.request_file_list(ip)

    def on_file_list_ready(self, files):
        self.file_list.clear()
        if not files:
            self.file_list.addItem("No files found or unable to reach phone TCP server.")
            return
        
        self.remote_files = files
        for item in files:
            name = item["name"]
            size = item["size"]
            icon = get_file_type_icon(name)
            list_item = QListWidgetItem(f"{icon} {name}  ({format_size(size)})")
            list_item.setData(Qt.ItemDataRole.UserRole, name)
            self.file_list.addItem(list_item)
            
        self.file_list.itemClicked.connect(self.on_item_clicked)

    def on_item_clicked(self, item):
        self.selected_filename = item.data(Qt.ItemDataRole.UserRole)
        for f in self.remote_files:
            if f["name"] == self.selected_filename:
                self.selected_size = f["size"]
                self.selected_info.setText(f"{get_file_type_icon(self.selected_filename)} {self.selected_filename} ({format_size(self.selected_size)})")
                self.pull_btn.setEnabled(True)
                break

    def start_pull(self):
        ip = self.get_device_ip()
        if not ip or not hasattr(self, 'selected_filename'):
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", 
            os.path.expanduser(f"~/Downloads/{self.selected_filename}"),
            "All Files (*)"
        )
        if not save_path:
            return
            
        self.pull_btn.setEnabled(False)
        self.status_label.setText("Downloading file wirelessly...")
        self.client.pull_file(self.selected_filename, ip, save_path)

    def update_progress(self, percent, speed, eta):
        self.progress_bar.setValue(percent)
        self.speed_label.setText(f"Speed: {speed:.1f} MB/s")
        if percent < 100 and eta > 0:
            self.eta_label.setText(f"ETA: {int(eta)//60:02d}:{int(eta)%60:02d}")
        else:
            self.eta_label.setText("ETA: --:--")

    def on_transfer_finished(self, success, msg):
        self.pull_btn.setEnabled(True)
        self.status_label.setText(msg)
        if success:
            self.status_label.setStyleSheet("color: #00d9a5;")
        else:
            self.status_label.setStyleSheet("color: #ff6b6b;")
