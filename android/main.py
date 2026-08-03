import os
import sys
import time
import socket
import threading
import json
import subprocess
import traceback

# Samsung JNI and Modified UTF-8 sensor workarounds
os.environ['SDL_SENSOR_DRIVER'] = 'dummy'

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.core.window import Window

Window.fullscreen = 'auto'

# Port configuration
PORT_TCP_TRANSFER = 5558

# Kivy theme configuration
DARK_BG = (0.07, 0.07, 0.14, 1)
PANEL_BG = (0.1, 0.1, 0.22, 1)
ACCENT = (0.0, 0.85, 0.647, 1)
TEXT = (0.9, 0.9, 0.9, 1)

def get_storage_dirs():
    """Determines the correct internal and external storage directories for the app."""
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        internal_dir = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
    except Exception:
        internal_dir = os.path.join(os.path.expanduser("~"), "scrcpy_link")
    
    external_config = "/sdcard/scrcpy_heartbeat_config.json"
    external_log_dir = "/sdcard/log"
    
    can_write_external = False
    try:
        if os.path.exists("/sdcard"):
            test_file = "/sdcard/.scrcpy_test"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            can_write_external = True
    except OSError:
        pass
    
    if can_write_external:
        config_file = external_config
        log_dir = external_log_dir
    else:
        os.makedirs(internal_dir, exist_ok=True)
        config_file = os.path.join(internal_dir, "scrcpy_heartbeat_config.json")
        log_dir = os.path.join(internal_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
    
    return config_file, log_dir, can_write_external

CONFIG_FILE, LOG_DIR, CAN_WRITE_EXTERNAL = get_storage_dirs()
LOG_FILE = os.path.join(LOG_DIR, "ScrcpyLink.log")
VAULT_DIR = "/sdcard/ScrcpyUltimateLink" if CAN_WRITE_EXTERNAL else os.path.join(LOG_DIR, "Vault")

try:
    os.makedirs(VAULT_DIR, exist_ok=True)
except OSError as e:
    print(f"Failed to create vault dir: {e}")

def load_config():
    """Loads the application configuration from JSON."""
    defaults = {
        "heartbeat_port": 5556,
        "discovery_port": 5557,
        "adb_port": 5555,
        "logging_enabled": True,
        "use_system_font": True
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            for k, v in defaults.items():
                if k not in config: config[k] = v
            return config
    except OSError as e:
        print(f"Config load failed: {e}")
    except json.JSONDecodeError as e:
        print(f"Config parse failed: {e}")
    return defaults

def save_config(config):
    """Saves the application configuration to JSON."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        print(f"Config save failed: {e}")

config = load_config()

LOG_MAX_BYTES = 50 * 1024
def app_log(msg):
    """Logs messages to console and file, maintaining a size limit."""
    print(msg)
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_str = f"[{timestamp}] {msg}\n"
        with open(LOG_FILE, "a") as f:
            f.write(log_str)
        
        if os.path.getsize(LOG_FILE) > LOG_MAX_BYTES:
            with open(LOG_FILE, "r") as f:
                content = f.read()
            with open(LOG_FILE, "w") as f:
                f.write(content[len(content)//2:])
    except OSError as e:
        print(f"Logging failed: {e}")

def disable_file_uri_exposure_check():
    """Disables the FileUriExposedException checks on Android 11+."""
    try:
        from jnius import autoclass
        StrictMode = autoclass('android.os.StrictMode')
        VmPolicy = autoclass('android.os.StrictMode$VmPolicy')
        Builder = autoclass('android.os.StrictMode$VmPolicy$Builder')
        builder = Builder()
        StrictMode.setVmPolicy(builder.build())
        app_log("Disabled VmPolicy FileUriExposedException checks.")
    except Exception as e:
        app_log(f"Failed to disable VmPolicy: {e}")

def enable_shizuku_wireless_adb():
    """Attempts to enable wireless ADB via Shizuku or root."""
    app_log("Starting Shizuku/Root wireless ADB trigger...")
    adb_cmd = "setprop service.adb.tcp.port 5555; setprop persist.adb.tcp.port 5555; setprop service.adb.tcp.bind 0.0.0.0; stop adbd && start adbd"
    
    try:
        import jnius
        jnius.autoclass('java.lang.System')
        Runtime = jnius.autoclass('java.lang.Runtime')
        process = Runtime.getRuntime().exec(["su", "-c", adb_cmd])
        process.waitFor()
        app_log("Root trigger successful via JNI Runtime")
        return
    except Exception as e:
        app_log(f"JNI Root failed: {e}")

    try:
        subprocess.run(["su", "-c", adb_cmd], check=True, timeout=5)
        app_log("Root trigger successful via subprocess su")
        return
    except Exception as e:
        app_log(f"Subprocess Root failed: {e}")
        
    try:
        pkg_name = "org.henry.scrcpy.scrcpyheartbeat"
        env = os.environ.copy()
        env["RISH_APPLICATION_ID"] = pkg_name
        unrooted_cmd = "setprop service.adb.tcp.port 5555; setprop ctl.restart adbd; adb tcpip 5555; cmd appops set moe.shizuku.privileged.api RUN_IN_BACKGROUND allow 2>/dev/null; cmd appops set com.thedjchi.shizuku RUN_IN_BACKGROUND allow 2>/dev/null"
        subprocess.run(["rish", "-c", unrooted_cmd], check=False, timeout=5, env=env)
        app_log("Shizuku rish execution attempted.")
    except Exception as e:
        app_log(f"Shizuku execution failed: {e}")


class ColoredBoxLayout(BoxLayout):
    """BoxLayout with a customizable background color."""
    def __init__(self, bg_color=DARK_BG, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*bg_color)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


class SlopButton(Button):
    """Button that cancels touch if dragged beyond a threshold."""
    touch_slop = dp(25)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touch_start_pos = None
        self._touch_cancelled = False
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start_pos = touch.pos
            self._touch_cancelled = False
            touch.grab(self)
        return super().on_touch_down(touch)
    
    def on_touch_move(self, touch):
        if touch.grab_current is self and self._touch_start_pos:
            dx = abs(touch.x - self._touch_start_pos[0])
            dy = abs(touch.y - self._touch_start_pos[1])
            if max(dx, dy) > self.touch_slop:
                touch.ungrab(self)
                self.state = 'normal'
                self._touch_cancelled = True
                self._touch_start_pos = None
        return super().on_touch_move(touch)
    
    def on_touch_up(self, touch):
        if self._touch_cancelled:
            self._touch_cancelled = False
            self._touch_start_pos = None
            return True
        self._touch_start_pos = None
        return super().on_touch_up(touch)


class TCPFileServerThread(threading.Thread):
    """Dedicated background thread for handling incoming TCP file transfers."""
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.sock = None

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(("0.0.0.0", PORT_TCP_TRANSFER))
            self.sock.listen(1)
            app_log(f"Mobile TCP Server active on port {PORT_TCP_TRANSFER}")
        except Exception as e:
            app_log(f"Mobile TCP Server bind error: {e}")
            return

        while True:
            try:
                conn, addr = self.sock.accept()
                self._handle_client(conn, addr[0])
            except Exception as e:
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
                files_data = []
                for f in os.listdir(VAULT_DIR):
                    p = os.path.join(VAULT_DIR, f)
                    if os.path.isfile(p):
                        files_data.append({"name": f, "size": os.path.getsize(p)})
                conn.sendall((json.dumps(files_data) + "\n").encode('utf-8'))
                conn.close()
                return
                
            elif header.startswith("FILE_GET|"):
                parts = header.split('|')
                fname = parts[1]
                filepath = os.path.join(VAULT_DIR, fname)
                if os.path.exists(filepath):
                    filesize = os.path.getsize(filepath)
                    conn.sendall(f"FILE_SEND|{fname}|{filesize}\n".encode('utf-8'))
                    with open(filepath, "rb") as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk: break
                            conn.sendall(chunk)
                conn.close()
                return
                
            elif header.startswith("FILE_SEND|"):
                parts = header.split('|')
                filename = parts[1]
                filesize = int(parts[2])
                
                app_log(f"Receiving '{filename}' ({filesize} bytes)...")
                filepath = os.path.join(VAULT_DIR, filename)
                
                received_bytes = 0
                start_time = time.time()
                last_progress_time = start_time
                last_bytes = 0
                
                app = App.get_running_app()
                transfer_screen = app.root.get_screen('transfer') if app and app.root else None
                
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
                            speed = (delta / dt) / (1024 * 1024) if dt > 0 else 0
                            percent = int((received_bytes / filesize) * 100) if filesize > 0 else 0
                            eta = (filesize - received_bytes) / (delta / dt) if delta > 0 else 0
                            
                            if transfer_screen:
                                transfer_screen.update_progress_from_server(percent, speed, eta, filename)
                            
                            last_bytes = received_bytes
                            last_progress_time = now
                
                conn.close()
                app_log(f"Successfully received '{filename}'")
                if transfer_screen:
                    transfer_screen.on_server_transfer_complete(True, filename)
        except Exception as e:
            try:
                conn.close()
            except OSError:
                pass
            app_log(f"TCP server receive error: {e}")
            app = App.get_running_app()
            transfer_screen = app.root.get_screen('transfer') if app and app.root else None
            if transfer_screen:
                transfer_screen.on_server_transfer_complete(False, str(e))


class MainScreen(Screen):
    """The main interface for the Scrcpy Link."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        self.label = Label(text="Scrcpy Ultimate Link", font_size=sp(26), bold=True, color=ACCENT, size_hint_y=None, height=dp(50))
        self.pc_ip_input = TextInput(text="Discovering PC...", readonly=True, halign='center', font_size=sp(18), background_color=PANEL_BG, foreground_color=TEXT, size_hint_y=None, height=dp(50))
        self.status_label = Label(text="Listening for PC broadcast...", font_size=sp(14), color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=dp(30))
        
        btn_layout = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None, height=dp(340))
        
        restart_btn = SlopButton(text="Restart Link", background_color=(0.1, 0.2, 0.4, 1), color=ACCENT, font_size=sp(16))
        restart_btn.bind(on_press=self.restart_connection)
        
        transfer_btn = SlopButton(text="WiFi File Transfer (Send/Recv)", background_color=(0.1, 0.35, 0.25, 1), color=ACCENT, font_size=sp(16))
        transfer_btn.bind(on_press=self.go_transfer)

        vault_btn = SlopButton(text="Received Files Vault", background_color=(0.3, 0.15, 0.05, 1), color=ACCENT, font_size=sp(16))
        vault_btn.bind(on_press=self.go_vault)
        
        logs_btn = SlopButton(text="Live System Logs", background_color=(0.2, 0.1, 0.35, 1), color=ACCENT, font_size=sp(16))
        logs_btn.bind(on_press=self.go_logs)
        
        settings_btn = SlopButton(text="App Settings", background_color=(0.2, 0.2, 0.25, 1), color=ACCENT, font_size=sp(16))
        settings_btn.bind(on_press=self.go_settings)

        help_btn = SlopButton(text="Help Guide", background_color=(0.05, 0.25, 0.15, 1), color=ACCENT, font_size=sp(16))
        help_btn.bind(on_press=self.go_help)
        
        btn_layout.add_widget(restart_btn)
        btn_layout.add_widget(transfer_btn)
        btn_layout.add_widget(vault_btn)
        btn_layout.add_widget(logs_btn)
        btn_layout.add_widget(settings_btn)
        btn_layout.add_widget(help_btn)
        
        layout.add_widget(self.label)
        layout.add_widget(self.pc_ip_input)
        layout.add_widget(self.status_label)
        layout.add_widget(btn_layout)
        layout.add_widget(Widget())
        self.add_widget(layout)
        
        self.sending = False
        self.discovered_pc_ip = None
        self._discovery_running = False

    def go_transfer(self, instance):
        """Navigate to transfer screen."""
        self.manager.transition.direction = 'left'
        self.manager.current = 'transfer'

    def go_vault(self, instance):
        """Navigate to vault screen."""
        self.manager.transition.direction = 'left'
        self.manager.current = 'vault'

    def go_logs(self, instance):
        """Navigate to logs screen."""
        self.manager.transition.direction = 'left'
        self.manager.current = 'logs'

    def go_settings(self, instance):
        """Navigate to settings screen."""
        self.manager.transition.direction = 'left'
        self.manager.current = 'settings'

    def go_help(self, instance):
        """Navigate to help screen."""
        self.manager.transition.direction = 'left'
        self.manager.current = 'help'

    def on_enter(self):
        disable_file_uri_exposure_check()
        if not self._discovery_running:
            app_log("Launching background ADB triggers")
            threading.Thread(target=enable_shizuku_wireless_adb, daemon=True).start()
            self._start_services()

    def restart_connection(self, instance):
        """Restarts the network services."""
        app_log("Restarting link...")
        self._stop_services()
        threading.Thread(target=enable_shizuku_wireless_adb, daemon=True).start()
        self.pc_ip_input.text = "Discovering PC..."
        self.status_label.text = "Listening for PC broadcast..."
        self._start_services()

    def _start_services(self):
        self._discovery_running = True
        threading.Thread(target=self.discovery_listener, daemon=True).start()

    def _stop_services(self):
        self._discovery_running = False
        self.sending = False

    def discovery_listener(self):
        """Listens for PC UDP broadcasts."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(2.0)
            sock.bind(("0.0.0.0", config["discovery_port"]))
            
            while self._discovery_running:
                try:
                    data, addr = sock.recvfrom(1024)
                    msg = data.decode('utf-8').strip()
                    if msg.startswith("SCRCPC_HERE"):
                        pc_ip = msg.split()[1]
                        if self.discovered_pc_ip != pc_ip:
                            self.discovered_pc_ip = pc_ip
                            app_log(f"Discovered PC: {pc_ip}")
                            Clock.schedule_once(lambda dt: self.start_heartbeat(pc_ip))
                except socket.timeout:
                    pass
                except Exception as e:
                    app_log(f"Discovery receive error: {e}")
                    time.sleep(1)
        except Exception as e:
            app_log(f"Discovery socket failed: {e}")
        finally:
            sock.close()

    def start_heartbeat(self, pc_ip):
        """Initiates the heartbeat loop."""
        self.pc_ip_input.text = pc_ip
        self.status_label.text = f"PC found! Initiating link..."
        if not self.sending:
            self.sending = True
            threading.Thread(target=self.heartbeat_loop, args=(pc_ip,), daemon=True).start()

    def heartbeat_loop(self, target_ip):
        """Sends periodic heartbeats back to the PC."""
        port = config["heartbeat_port"]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            while self.sending:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    phone_ip = s.getsockname()[0]
                    s.close()
                    
                    msg = f"HELLO_USER|{phone_ip}|{config['adb_port']}"
                    sock.sendto(msg.encode('utf-8'), (target_ip, port))
                except Exception as e:
                    app_log(f"Heartbeat loop error: {e}")
                time.sleep(4)
        finally:
            sock.close()


class FileTransferScreen(Screen):
    """Screen for handling file transfers."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        
        title = Label(text="WiFi File Transfer Hub", font_size=sp(22), bold=True, color=ACCENT, size_hint_y=None, height=dp(40))
        layout.add_widget(title)

        server_group = ColoredBoxLayout(orientation='vertical', bg_color=PANEL_BG, padding=dp(12), spacing=dp(8), size_hint_y=None, height=dp(180))
        server_group.add_widget(Label(text="WiFi Receiver Status: ACTIVE", font_size=sp(14), bold=True, color=ACCENT, halign='left'))
        
        self.serv_file_lbl = Label(text="Waiting for PC transfer...", font_size=sp(12), color=TEXT, halign='center')
        self.serv_progress = Label(text="0%", font_size=sp(16), bold=True, color=ACCENT)
        self.serv_stats = Label(text="Speed: -- MB/s  |  ETA: --:--", font_size=sp(11), color=(0.7, 0.7, 0.7, 1))
        
        server_group.add_widget(self.serv_file_lbl)
        server_group.add_widget(self.serv_progress)
        server_group.add_widget(self.serv_stats)
        layout.add_widget(server_group)

        sender_group = ColoredBoxLayout(orientation='vertical', bg_color=PANEL_BG, padding=dp(12), spacing=dp(8), size_hint_y=None, height=dp(200))
        sender_group.add_widget(Label(text="Send Vault File to PC", font_size=sp(14), bold=True, color=ACCENT))
        
        self.sender_spinner = Spinner(text="Select file from Vault...", values=[], background_color=DARK_BG, color=TEXT)
        self.sender_spinner.bind(on_press=self.populate_vault_files)
        
        self.send_progress_lbl = Label(text="Push speed: --  |  ETA: --", font_size=sp(12), color=TEXT)
        self.send_btn = SlopButton(text="Push Selected File to PC", background_color=(0.1, 0.35, 0.2, 1), color=ACCENT)
        self.send_btn.bind(on_press=self.start_file_send_to_pc)

        sender_group.add_widget(self.sender_spinner)
        sender_group.add_widget(self.send_progress_lbl)
        sender_group.add_widget(self.send_btn)
        layout.add_widget(sender_group)

        back_btn = SlopButton(text="Back to Home", background_color=(0.2, 0.1, 0.3, 1), color=ACCENT, size_hint_y=None, height=dp(50))
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def go_back(self, instance):
        """Navigate back to main screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'

    def populate_vault_files(self, instance):
        """Populates the list of files to send."""
        try:
            files = sorted(os.listdir(VAULT_DIR))
            self.sender_spinner.values = [f for f in files if os.path.isfile(os.path.join(VAULT_DIR, f))]
        except OSError as e:
            app_log(f"Failed to list vault files: {e}")
            self.sender_spinner.values = []

    def start_file_send_to_pc(self, instance):
        """Begins transferring the selected file to the PC."""
        filename = self.sender_spinner.text
        if filename == "Select file from Vault..." or not filename:
            self.send_progress_lbl.text = "Please select a file first!"
            return
            
        main_screen = self.manager.get_screen('main')
        pc_ip = main_screen.discovered_pc_ip
        if not pc_ip:
            self.send_progress_lbl.text = "No discovered PC IP!"
            return

        self.send_btn.disabled = True
        self.send_progress_lbl.text = "Connecting to PC File server..."
        
        def _task():
            filepath = os.path.join(VAULT_DIR, filename)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            try:
                sock.connect((pc_ip, PORT_TCP_TRANSFER))
                filesize = os.path.getsize(filepath)
                header = f"FILE_SEND|{filename}|{filesize}\n"
                sock.sendall(header.encode('utf-8'))
                
                sent_bytes = 0
                start_time = time.time()
                last_progress_time = start_time
                last_bytes = 0
                
                with open(filepath, "rb") as f:
                    while sent_bytes < filesize:
                        chunk = f.read(65536)
                        if not chunk: break
                        sock.sendall(chunk)
                        sent_bytes += len(chunk)
                        
                        now = time.time()
                        if now - last_progress_time >= 0.5:
                            dt = now - last_progress_time
                            delta = sent_bytes - last_bytes
                            speed = (delta / dt) / (1024 * 1024) if dt > 0 else 0
                            percent = int((sent_bytes / filesize) * 100) if filesize > 0 else 0
                            eta = (filesize - sent_bytes) / (delta / dt) if delta > 0 else 0
                            
                            Clock.schedule_once(lambda dt, p=percent, s=speed, e=eta: self.update_send_ui(p, s, e))
                            
                            last_bytes = sent_bytes
                            last_progress_time = now
                
                sock.close()
                Clock.schedule_once(lambda dt: self.on_send_complete(True, f"Sent '{filename}' successfully!"))
            except Exception as e:
                try: sock.close()
                except OSError: pass
                Clock.schedule_once(lambda dt, err=str(e): self.on_send_complete(False, f"Push failed: {err}"))

        threading.Thread(target=_task, daemon=True).start()

    def update_send_ui(self, percent, speed, eta):
        """Updates the progress UI for sending."""
        self.send_progress_lbl.text = f"Progress: {percent}% | Speed: {speed:.1f} MB/s | ETA: {int(eta)}s"

    def on_send_complete(self, success, msg):
        """Handles completion of the file send task."""
        self.send_btn.disabled = False
        self.send_progress_lbl.text = msg

    def update_progress_from_server(self, percent, speed, eta, filename):
        """Updates UI based on incoming server transfer."""
        def _update(dt):
            self.serv_file_lbl.text = f"Receiving: '{filename}'"
            self.serv_progress.text = f"{percent}%"
            self.serv_stats.text = f"Speed: {speed:.1f} MB/s  |  ETA: {int(eta)}s"
        Clock.schedule_once(_update)

    def on_server_transfer_complete(self, success, details):
        """Handles completion of incoming server transfer."""
        def _update(dt):
            self.serv_progress.text = "100%" if success else "Error!"
            self.serv_file_lbl.text = f"Success: {details}" if success else f"Failed: {details}"
            self.serv_stats.text = "Done" if success else "Stopped"
        Clock.schedule_once(_update)


class LogsScreen(Screen):
    """Screen for viewing application logs."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        title = Label(text="Live System Logs", font_size=sp(20), bold=True, color=ACCENT)
        refresh_btn = SlopButton(text="Refresh", background_color=(0.1, 0.25, 0.4, 1), size_hint_x=None, width=dp(90))
        refresh_btn.bind(on_press=lambda x: self.load_logs())
        header.add_widget(title)
        header.add_widget(refresh_btn)
        layout.add_widget(header)

        self.scroll = ScrollView()
        self.log_label = Label(text="Loading system logs...", font_size=sp(12), color=TEXT, size_hint_y=None, halign='left', valign='top')
        self.log_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        self.log_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
        
        self.scroll.add_widget(self.log_label)
        layout.add_widget(self.scroll)

        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        clear_btn = SlopButton(text="Clear Logs", background_color=(0.4, 0.1, 0.1, 1), color=ACCENT)
        clear_btn.bind(on_press=self.clear_logs)
        back_btn = SlopButton(text="Back to Home", background_color=(0.2, 0.1, 0.3, 1), color=ACCENT)
        back_btn.bind(on_press=self.go_back)
        btn_row.add_widget(clear_btn)
        btn_row.add_widget(back_btn)
        layout.add_widget(btn_row)

        self.add_widget(layout)

    def go_back(self, instance):
        """Navigate back to main screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'

    def on_enter(self):
        self.load_logs()

    def load_logs(self):
        """Loads and displays the latest log content."""
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    self.log_label.text = f.read().strip() or "Log file is empty."
            else:
                self.log_label.text = "No log file found."
        except OSError as e:
            self.log_label.text = f"Error reading logs: {e}"

    def clear_logs(self, instance):
        """Clears the application logs."""
        try:
            with open(LOG_FILE, "w") as f:
                f.write("")
            self.log_label.text = "Logs cleared successfully."
        except OSError as e:
            self.log_label.text = f"Failed to clear logs: {e}"


class SettingsScreen(Screen):
    """Screen for app configuration."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12))
        
        title = Label(text="App Configuration", font_size=sp(22), bold=True, color=ACCENT, size_hint_y=None, height=dp(40))
        layout.add_widget(title)
        
        log_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        log_layout.add_widget(Label(text="Enable Session Logging", color=TEXT, font_size=sp(15), size_hint_x=0.7))
        self.log_switch = Switch(active=config.get("logging_enabled", True))
        self.log_switch.bind(active=self.on_log_switch)
        log_layout.add_widget(self.log_switch)
        layout.add_widget(log_layout)
        
        self.add_port_spinner(layout, "Heartbeat Port (Phone -> PC)", "heartbeat_port")
        self.add_port_spinner(layout, "Discovery Port (PC Broadcast)", "discovery_port")
        self.add_port_spinner(layout, "scrcpy ADB Port", "adb_port")
        
        layout.add_widget(Widget())
        
        back_btn = SlopButton(text="Save & Return", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size=sp(18), size_hint_y=None, height=dp(50))
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def go_back(self, instance):
        """Navigate back to main screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'

    def add_port_spinner(self, layout, label_text, config_key):
        """Adds a UI spinner for port configuration."""
        box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        box.add_widget(Label(text=label_text, color=TEXT, font_size=sp(14), size_hint_x=0.6))
        spinner = Spinner(text=str(config.get(config_key)), values=[str(p) for p in range(5550, 5560)], background_color=PANEL_BG, color=TEXT, size_hint_x=0.4)
        spinner.bind(text=lambda instance, text: self.on_port_change(config_key, text))
        box.add_widget(spinner)
        layout.add_widget(box)

    def on_log_switch(self, instance, value):
        """Toggles logging feature."""
        config["logging_enabled"] = value
        save_config(config)

    def on_port_change(self, key, value):
        """Updates port configuration."""
        try:
            config[key] = int(value)
            save_config(config)
        except ValueError:
            pass


class HelpScreen(Screen):
    """Screen that displays the help guide."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        with layout.canvas.before:
            Color(*DARK_BG)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self.bg_rect, 'pos', v))
        layout.bind(size=lambda i, v: setattr(self.bg_rect, 'size', v))
        
        title = Label(text="Help & Setup Manual", color=ACCENT, font_size=sp(22), bold=True, size_hint_y=None, height=dp(40))
        layout.add_widget(title)
        
        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        content.bind(minimum_height=content.setter('height'))
        
        guide_text = (
            "[b]Quick Launch Instructions:[/b]\n"
            "1. Link phone and PC to the same WiFi/hotspot.\n"
            "2. Open the PC PyQt6 client, then open this app on your phone.\n"
            "3. High-performance scrcpy mirroring session starts instantly!\n\n"
            "[b]Shizuku Wireless Setup:[/b]\n"
            "• Execute: [color=00d9a5]rish -c 'adb tcpip 5555'[/color]\n\n"
            "[b]Bidirectional Clipboard Sync:[/b]\n"
            "• Turn on auto-sync on the PC app for seamless, instant, zero-delay copying across systems!\n\n"
            "[b]WiFi File Transfer Hub:[/b]\n"
            "• Uses dedicated, multi-megabyte TCP file protocol. Super fast and bypasses restrictive ADB permission pipelines."
        )
        
        guide_label = Label(text=guide_text, markup=True, color=TEXT, font_size=sp(14), halign='left', valign='top', size_hint_y=None)
        guide_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        guide_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
        
        content.add_widget(guide_label)
        scroll.add_widget(content)
        layout.add_widget(scroll)
        
        back_btn = SlopButton(text="Back to Home", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size=sp(16), size_hint_y=None, height=dp(55))
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def go_back(self, instance):
        """Navigate back to main screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'


class VaultScreen(Screen):
    """Screen for displaying downloaded vault files."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        title = Label(text="Vault Files", color=ACCENT, font_size=sp(20), bold=True)
        refresh_btn = SlopButton(text="Refresh", background_color=(0.1, 0.25, 0.4, 1), size_hint_x=None, width=dp(90))
        refresh_btn.bind(on_press=lambda x: self.refresh_vault())
        header.add_widget(title)
        header.add_widget(refresh_btn)
        layout.add_widget(header)
        
        self.scroll = ScrollView()
        self.file_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        self.file_list.bind(minimum_height=self.file_list.setter('height'))
        self.scroll.add_widget(self.file_list)
        layout.add_widget(self.scroll)
        
        self.empty_label = Label(text="No files found in Vault.\nTry pushing files from your PC wirelessly!", color=(0.5, 0.5, 0.5, 1), font_size=sp(13), halign='center')
        layout.add_widget(self.empty_label)
        
        back_btn = SlopButton(text="Back to Home", background_color=(0.2, 0.1, 0.3, 1), color=ACCENT, font_size=sp(16), size_hint_y=None, height=dp(55))
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def go_back(self, instance):
        """Navigate back to main screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'
    
    def on_enter(self):
        self.refresh_vault()
    
    def refresh_vault(self):
        """Refreshes the list of files stored in the vault."""
        self.file_list.clear_widgets()
        try:
            files = sorted(os.listdir(VAULT_DIR))
            received_files = [f for f in files if os.path.isfile(os.path.join(VAULT_DIR, f))]
            
            if not received_files:
                self.empty_label.opacity = 1
                return
            
            self.empty_label.opacity = 0
            
            for filename in received_files:
                filepath = os.path.join(VAULT_DIR, filename)
                size = os.path.getsize(filepath)
                
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(8))
                
                name_label = Label(text=filename, color=TEXT, font_size=sp(13), halign='left')
                name_label.bind(width=lambda i, v: setattr(i, 'text_size', (v, None)))
                
                size_label = Label(text=f"{size / (1024*1024):.1f} MB" if size >= 1024*1024 else f"{size/1024:.1f} KB", color=(0.5, 0.5, 0.5, 1), font_size=sp(11), size_hint_x=None, width=dp(70))
                
                share_btn = SlopButton(text="Share", background_color=(0.1, 0.3, 0.2, 1), color=ACCENT, size_hint_x=None, width=dp(70))
                share_btn.bind(on_press=lambda btn, path=filepath: self.share_file(path))
                
                row.add_widget(name_label)
                row.add_widget(size_label)
                row.add_widget(share_btn)
                self.file_list.add_widget(row)
        except OSError as e:
            app_log(f"Vault refresh failed: {e}")
    
    def share_file(self, file_path):
        """Triggers the Android share intent for the specified file."""
        try:
            from jnius import autoclass, cast
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            File = autoclass('java.io.File')
            
            context = PythonActivity.mActivity
            file_obj = File(file_path)
            uri = Uri.fromFile(file_obj)
            
            intent = Intent(Intent.ACTION_SEND)
            intent.setType("*/*")
            intent.putExtra(Intent.EXTRA_STREAM, cast('android.os.Parcelable', uri))
            
            chooser = Intent.createChooser(intent, "Share File via:")
            context.startActivity(chooser)
        except Exception as e:
            app_log(f"Share trigger failed: {e}")


class HeartbeatApp(App):
    """The main application class."""
    def build(self):
        Window.bind(on_keyboard=self.on_keyboard)

        server = TCPFileServerThread()
        server.start()

        self.root_sm = ScreenManager(transition=SlideTransition())
        self.root_sm.add_widget(MainScreen(name='main'))
        self.root_sm.add_widget(FileTransferScreen(name='transfer'))
        self.root_sm.add_widget(VaultScreen(name='vault'))
        self.root_sm.add_widget(LogsScreen(name='logs'))
        self.root_sm.add_widget(SettingsScreen(name='settings'))
        self.root_sm.add_widget(HelpScreen(name='help'))
        
        try:
            from android.broadcast import BroadcastReceiver
            
            def on_clipboard_intent(context, intent):
                action = intent.getAction()
                if action == "org.henry.scrcpy.SET_CLIPBOARD":
                    txt = intent.getStringExtra("text")
                    if txt:
                        self.set_local_clipboard(txt)
                elif action == "org.henry.scrcpy.GET_CLIPBOARD":
                    self.send_local_clipboard_to_pc()
            
            receiver = BroadcastReceiver(on_clipboard_intent, actions=["org.henry.scrcpy.SET_CLIPBOARD", "org.henry.scrcpy.GET_CLIPBOARD"])
            receiver.start()
            app_log("Clipboard broadcast receiver bound successfully.")
        except Exception as e:
            app_log(f"Clipboard receiver bind failed: {e}")
            
        return self.root_sm

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        """Handles hardware back button and escape key."""
        if key == 27:
            if self.root_sm.current != 'main':
                self.root_sm.transition.direction = 'right'
                self.root_sm.current = 'main'
                return True
        return False

    def set_local_clipboard(self, text):
        """Sets the Android clipboard."""
        try:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)
            ClipData = autoclass('android.content.ClipData')
            clip = ClipData.newPlainText("scrcpy", text)
            clipboard.setPrimaryClip(clip)
            app_log("Successfully updated local device clipboard.")
        except Exception as e:
            app_log(f"Failed to write device clipboard: {e}")

    def send_local_clipboard_to_pc(self):
        """Sends clipboard content back to the PC."""
        try:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)
            if clipboard.hasPrimaryClip():
                clip_data = clipboard.getPrimaryClip()
                if clip_data.getItemCount() > 0:
                    text = clip_data.getItemAt(0).coerceToText(activity).toString()
                    main_screen = self.root_sm.get_screen('main')
                    pc_ip = main_screen.discovered_pc_ip
                    if pc_ip:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        sock.sendto(f"HELLO_CLIPBOARD|{text}".encode('utf-8'), (pc_ip, config["heartbeat_port"]))
                        sock.close()
        except Exception as e:
            app_log(f"Failed to fetch device clipboard: {e}")

if __name__ == "__main__":
    try:
        app_log("Launcher initializing...")
        HeartbeatApp().run()
    except Exception as e:
        app_log(f"CRASH ENCOUNTERED: {traceback.format_exc()}")
