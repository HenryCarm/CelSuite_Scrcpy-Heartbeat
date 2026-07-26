import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QFileDialog, QMessageBox, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QProcess, QTimer, QObject
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

# File type icon mapping (lightweight Unicode badges)
FILE_TYPE_ICONS = {
    '.mp4': '[VIDEO]', '.mkv': '[VIDEO]', '.avi': '[VIDEO]', '.mov': '[VIDEO]',
    '.png': '[IMG]', '.jpg': '[IMG]', '.jpeg': '[IMG]', '.webp': '[IMG]', '.gif': '[IMG]',
    '.apk': '[APK]',
    '.mp3': '[AUDIO]', '.wav': '[AUDIO]', '.ogg': '[AUDIO]', '.flac': '[AUDIO]',
    '.pdf': '[DOC]', '.doc': '[DOC]', '.docx': '[DOC]', '.txt': '[DOC]',
    '.zip': '[ARCHIVE]', '.tar': '[ARCHIVE]', '.gz': '[ARCHIVE]',
}

def get_file_type_icon(filename):
    ext = os.path.splitext(filename)[1].lower()
    return FILE_TYPE_ICONS.get(ext, '[FILE]')

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

# 500MB warning threshold
LARGE_FILE_THRESHOLD = 524288000


class DropZone(QFrame):
    """Unified drag-and-drop zone with Browse button"""
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

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QFrame { border: 2px solid #00d9a5; background-color: #1f2e5a; border-radius: 12px; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("QFrame { border: 2px dashed #00d9a5; background-color: #16213e; border-radius: 12px; }")

    def dropEvent(self, event: QDropEvent):
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


class FileTransferWorker(QObject):
    """Handles ADB push with QProcess + QTimer progress polling"""
    progress_updated = pyqtSignal(int, float, float)  # percent, speed_mbps, eta_seconds
    transfer_finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self):
        super().__init__()
        self.process = None
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_progress)
        self.local_path = ""
        self.remote_path = ""
        self.total_bytes = 0
        self.last_bytes = 0
        self.last_time = 0
        self.device_ip = ""
        self.device_port = 5555

    def start_transfer(self, local_path, device_ip, device_port=5555):
        self.local_path = local_path
        self.device_ip = device_ip
        self.device_port = device_port
        self.total_bytes = os.path.getsize(local_path)
        self.last_bytes = 0
        self.last_time = time.time()
        
        filename = os.path.basename(local_path)
        self.remote_path = f"/sdcard/ScrcpyUltimateLink/{filename}"
        
        # Ensure remote directory exists
        mkdir_cmd = ["adb", "-s", f"{device_ip}:{device_port}", "shell", "mkdir", "-p", "/sdcard/ScrcpyUltimateLink"]
        import subprocess
        subprocess.run(mkdir_cmd, capture_output=True)
        
        # Start adb push via QProcess
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.finished.connect(self.on_process_finished)
        
        cmd = ["-s", f"{device_ip}:{device_port}", "push", local_path, self.remote_path]
        self.process.start("adb", cmd)
        
        # Start polling every 500ms
        self.poll_timer.start(500)

    def poll_progress(self):
        if not self.process or self.process.state() != QProcess.ProcessState.Running:
            return
        
        try:
            # Check remote file size
            cmd = ["-s", f"{self.device_ip}:{self.device_port}", "shell", "stat", "-c", "%s", self.remote_path]
            result = subprocess.run(["adb"] + cmd, capture_output=True, text=True, timeout=2)
            current_bytes = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        except:
            current_bytes = 0
        
        now = time.time()
        dt = now - self.last_time
        if dt > 0:
            bytes_delta = current_bytes - self.last_bytes
            speed_bps = bytes_delta / dt if dt > 0 else 0
            speed_mbps = speed_bps / (1024 * 1024)
            
            percent = int((current_bytes / self.total_bytes) * 100) if self.total_bytes > 0 else 0
            percent = min(percent, 100)
            
            remaining_bytes = self.total_bytes - current_bytes
            eta = remaining_bytes / speed_bps if speed_bps > 0 else 0
            
            self.progress_updated.emit(percent, speed_mbps, eta)
            
            self.last_bytes = current_bytes
            self.last_time = now

    def on_process_finished(self, exit_code, exit_status):
        self.poll_timer.stop()
        if exit_code == 0:
            self.progress_updated.emit(100, 0, 0)
            self.transfer_finished.emit(True, f"File sent successfully!\n{self.remote_path}")
        else:
            error = self.process.readAllStandardOutput().data().decode()
            self.transfer_finished.emit(False, f"Transfer failed: {error}")

    def cancel(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
        self.poll_timer.stop()


import subprocess


class FileTransferScreen(QWidget):
    """Complete File Transfer screen with DropZone, progress, and transfer controls"""
    def __init__(self, get_device_ip_func):
        super().__init__()
        self.get_device_ip = get_device_ip_func
        self.worker = FileTransferWorker()
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.transfer_finished.connect(self.on_transfer_finished)
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("File Transfer (PC -> Phone)")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00d9a5;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Drop Zone
        self.drop_zone = DropZone()
        self.drop_zone.file_selected.connect(self.on_file_selected)
        layout.addWidget(self.drop_zone)

        # File Info
        self.file_info = QLabel("No file selected")
        self.file_info.setStyleSheet("color: #888; font-size: 14px;")
        self.file_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.file_info)

        # Progress Group
        progress_group = QGroupBox("Transfer Progress")
        progress_group.setStyleSheet("""
            QGroupBox { color: #00d9a5; font-weight: bold; border: 2px solid #0f3460; border-radius: 8px; margin-top: 12px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #0f3460; border-radius: 6px; text-align: center; color: white; font-weight: bold; height: 28px; background-color: #1a1a2e; }
            QProgressBar::chunk { background-color: #00d9a5; border-radius: 5px; }
        """)
        progress_layout.addWidget(self.progress_bar)

        # Stats row
        stats_layout = QHBoxLayout()
        self.speed_label = QLabel("Speed: -- MB/s")
        self.speed_label.setStyleSheet("color: #888; font-size: 13px;")
        self.eta_label = QLabel("ETA: --:--")
        self.eta_label.setStyleSheet("color: #888; font-size: 13px;")
        self.size_label = QLabel("Size: --")
        self.size_label.setStyleSheet("color: #888; font-size: 13px;")
        stats_layout.addWidget(self.speed_label)
        stats_layout.addWidget(self.eta_label)
        stats_layout.addWidget(self.size_label)
        progress_layout.addLayout(stats_layout)

        layout.addWidget(progress_group)

        # Send Button
        self.send_btn = QPushButton("Send to Phone")
        self.send_btn.setMinimumHeight(50)
        self.send_btn.setEnabled(False)
        self.send_btn.setStyleSheet("""
            QPushButton { 
                background-color: #0f3460; 
                color: #00d9a5; 
                border: 2px solid #00d9a5; 
                border-radius: 8px; 
                padding: 14px; 
                font-size: 16px; 
                font-weight: bold; 
            }
            QPushButton:hover { background-color: #00d9a5; color: #1a1a2e; }
            QPushButton:disabled { background-color: #1a1a2e; color: #666; border-color: #444; }
        """)
        self.send_btn.clicked.connect(self.start_transfer)
        layout.addWidget(self.send_btn)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 13px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

    def on_file_selected(self, file_path):
        self.selected_file = file_path
        size = os.path.getsize(file_path)
        self.file_info.setText(f"{get_file_type_icon(os.path.basename(file_path))} {os.path.basename(file_path)}  ({format_size(size)})")
        self.file_info.setStyleSheet("color: #00d9a5; font-size: 14px;")
        self.send_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.speed_label.setText("Speed: -- MB/s")
        self.eta_label.setText("ETA: --:--")
        self.size_label.setText(f"Size: {format_size(size)}")

    def start_transfer(self):
        if not hasattr(self, 'selected_file'):
            return
        
        # Check file size warning
        size = os.path.getsize(self.selected_file)
        if size > LARGE_FILE_THRESHOLD:
            size_str = format_size(size)
            reply = QMessageBox.question(
                self, "Large File Detected",
                f"Large file detected ({size_str})!\n\nOver wireless debugging, this may take several minutes depending on WiFi signal.\n\nKeep your phone screen on. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        device_ip = self.get_device_ip()
        if not device_ip:
            QMessageBox.warning(self, "No Device", "No phone connected!\n\nUse Mirror Phone first to discover your device.")
            return
        
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Sending...")
        self.status_label.setText(f"Pushing to {device_ip}...")
        self.worker.start_transfer(self.selected_file, device_ip)

    def update_progress(self, percent, speed_mbps, eta_seconds):
        self.progress_bar.setValue(percent)
        self.speed_label.setText(f"Speed: {speed_mbps:.1f} MB/s")
        
        if eta_seconds > 0 and percent < 100:
            mins = int(eta_seconds // 60)
            secs = int(eta_seconds % 60)
            self.eta_label.setText(f"ETA: {mins:02d}:{secs:02d}")
        else:
            self.eta_label.setText("ETA: --:--")

    def on_transfer_finished(self, success, message):
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send to Phone")
        
        if success:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #00d9a5; font-size: 13px;")
            self.progress_bar.setValue(100)
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
