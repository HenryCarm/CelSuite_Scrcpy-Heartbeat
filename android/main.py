import os, sys, time, socket, threading, json, subprocess, traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.core.window import Window

# Disable fullscreen - allow status bar visibility
Window.fullscreen = 'auto'

# 1. Request Scoped Storage & Network Permissions
try:
    from android.permissions import request_permissions, Permission
    from android import api_version
    from jnius import autoclass

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Environment = autoclass('android.os.Environment')

    perms = [Permission.INTERNET, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
    request_permissions(perms)

    # Only request MANAGE_EXTERNAL_STORAGE once per install
    if api_version >= 30 and not Environment.isExternalStorageManager() and not app_state.get("storage_perm_requested", False):
        try:
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            Uri = autoclass('android.net.Uri')
            intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
            intent.setData(Uri.parse("package:" + PythonActivity.mActivity.getPackageName()))
            PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            print(f"MANAGE_EXTERNAL_STORAGE request failed: {e}")
        # Lock the flag in internal storage (always writable)
        app_state["storage_perm_requested"] = True
        save_internal_state(app_state)
except Exception as e:
    print(f"Permission request failed: {e}")

# 2. Dynamic Config & Logging Paths - fallback to internal storage if external not available
def get_storage_dirs():
    """Get available storage directories, preferring external but falling back to internal"""
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        internal_dir = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
    except:
        # Fallback for testing outside Android
        internal_dir = os.path.join(os.path.expanduser("~"), "scrcpy_link")
    external_config = "/sdcard/scrcpy_heartbeat_config.json"
    external_log_dir = "/sdcard/log"
    
    # Check if we can write to external storage
    can_write_external = False
    try:
        if os.path.exists("/sdcard"):
            test_file = "/sdcard/.scrcpy_test"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            can_write_external = True
    except:
        pass
    
    if can_write_external:
        config_file = external_config
        log_dir = external_log_dir
    else:
        # Use internal storage
        os.makedirs(internal_dir, exist_ok=True)
        config_file = os.path.join(internal_dir, "scrcpy_heartbeat_config.json")
        log_dir = os.path.join(internal_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
    
    return config_file, log_dir, can_write_external

CONFIG_FILE, LOG_DIR, CAN_WRITE_EXTERNAL = get_storage_dirs()
LOG_FILE = os.path.join(LOG_DIR, "ScrcpyLink.log")

# Internal state file for critical flags (always writable, no permissions needed)
def get_internal_state_file():
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        return os.path.join(PythonActivity.mActivity.getFilesDir().getAbsolutePath(), "app_state.json")
    except:
        return os.path.join(os.path.expanduser("~"), ".scrcpy_app_state.json")

INTERNAL_STATE_FILE = get_internal_state_file()

def load_internal_state():
    defaults = {"storage_perm_requested": False}
    try:
        if os.path.exists(INTERNAL_STATE_FILE):
            with open(INTERNAL_STATE_FILE, "r") as f:
                state = json.load(f)
            for k, v in defaults.items():
                if k not in state:
                    state[k] = v
            return state
    except:
        pass
    return defaults

def save_internal_state(state):
    try:
        os.makedirs(os.path.dirname(INTERNAL_STATE_FILE), exist_ok=True)
        with open(INTERNAL_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except:
        pass

app_state = load_internal_state()

def load_config():
    defaults = {"heartbeat_port": 5556, "discovery_port": 5557, "adb_port": 5555, "logging_enabled": False, "use_system_font": True}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            for k, v in defaults.items():
                if k not in config: config[k] = v
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

# 3. Enterprise File Logger (with 50-line sliding window to prevent memory leaks on Samsung A035F)
LOG_MAX_LINES = 50

def app_log(msg):
    if not config.get("logging_enabled", False):
        return
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_str = f"[{timestamp}] {msg}\n"
        with open(LOG_FILE, "a") as f:
            f.write(log_str)
        # Sliding window: keep only last N lines to prevent memory bloat
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
            if len(lines) > LOG_MAX_LINES:
                with open(LOG_FILE, "w") as f:
                    f.writelines(lines[-LOG_MAX_LINES:])
        except:
            pass
        print(log_str.strip())
    except Exception as e:
        print(f"Logging failed: {e}")

# 4. Safe Threaded Shizuku Execution (Prevents ANR block)
def enable_shizuku_wireless_adb():
    app_log("Starting Shizuku/Root ADB background sequence...")
    adb_cmd = "setprop service.adb.tcp.port 5555; setprop persist.adb.tcp.port 5555; setprop service.adb.tcp.bind 0.0.0.0; stop adbd && start adbd"
    
    # Try JNI (Attach JVM thread safely)
    try:
        import jnius
        jnius.autoclass('java.lang.System') # Forces safe JVM attachment
        Runtime = jnius.autoclass('java.lang.Runtime')
        process = Runtime.getRuntime().exec(["su", "-c", adb_cmd])
        process.waitFor()
        app_log("Success: Pyjnius Runtime (su)")
        return
    except Exception as e:
        app_log(f"Pyjnius fallback triggered: {e}")

    # Try subprocess su
    try:
        subprocess.run(["su", "-c", adb_cmd], check=True, timeout=5)
        app_log("Success: subprocess su")
        return
    except Exception as e:
        app_log(f"Subprocess su fallback: {e}")
        
    # Try unrooted rish (Supports both standard and thedjchi forks)
    try:
        pkg_name = "org.henry.scrcpy.scrcpyheartbeat"
        env = os.environ.copy()
        env["RISH_APPLICATION_ID"] = pkg_name
        unrooted_cmd = "setprop service.adb.tcp.port 5555; setprop ctl.restart adbd; adb tcpip 5555; cmd appops set moe.shizuku.privileged.api RUN_IN_BACKGROUND allow 2>/dev/null; cmd appops set com.thedjchi.shizuku RUN_IN_BACKGROUND allow 2>/dev/null"
        subprocess.run(["rish", "-c", unrooted_cmd], check=False, timeout=5, env=env)
        app_log("Success: Shizuku rish (unrooted/thedjchi)")
    except Exception as e:
        app_log(f"Shizuku rish failed: {e}")

# --- SCREENS ---

DARK_BG = (0.1, 0.1, 0.18, 1)
PANEL_BG = (0.086, 0.13, 0.243, 1)
ACCENT = (0.0, 0.85, 0.647, 1)
TEXT = (0.878, 0.878, 0.878, 1)

class ColoredBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*DARK_BG)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


# Custom button with touch slop to prevent accidental clicks when dragging away
class SlopButton(Button):
    touch_slop = dp(20)  # pixels finger can move before cancelling press
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touch_start_pos = None
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start_pos = touch.pos
            touch.grab(self)
        return super().on_touch_down(touch)
    
    def on_touch_move(self, touch):
        if touch.grab_current is self and self._touch_start_pos:
            dx = abs(touch.x - self._touch_start_pos[0])
            dy = abs(touch.y - self._touch_start_pos[1])
            if max(dx, dy) > self.touch_slop:
                touch.ungrab(self)
                self.state = 'normal'
                self._touch_start_pos = None
        return super().on_touch_move(touch)
    
    def on_touch_up(self, touch):
        self._touch_start_pos = None
        return super().on_touch_up(touch)

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        self.label = Label(text="Scrcpy Heartbeat", font_size=sp(28), bold=True, color=ACCENT, size_hint_y=None, height=dp(60))
        self.pc_ip_input = TextInput(text="Discovering PC...", readonly=True, halign='center', font_size=sp(20), background_color=PANEL_BG, foreground_color=TEXT, size_hint_y=None, height=dp(60))
        self.status_label = Label(text="Listening for PC broadcast...", font_size=sp(16), color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=dp(40))
        
        # Removed the spacer widget here so the buttons float higher up!
        btn_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(300))
        
        restart_btn = SlopButton(text=">> Restart Connection", background_color=(0.059, 0.204, 0.376, 1), color=ACCENT, font_size=sp(18))
        restart_btn.bind(on_press=self.restart_connection)
        
        settings_btn = SlopButton(text="[+] Settings", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size=sp(18))
        settings_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'settings'))

        help_btn = SlopButton(text="[?] Help Guide", background_color=(0.1, 0.4, 0.2, 1), color=ACCENT, font_size=sp(18))
        help_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'help'))

        vault_btn = SlopButton(text="[*] Received Files", background_color=(0.3, 0.15, 0.05, 1), color=ACCENT, font_size=sp(18))
        vault_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'vault'))
        
        btn_layout.add_widget(restart_btn)
        btn_layout.add_widget(settings_btn)
        btn_layout.add_widget(help_btn)
        btn_layout.add_widget(vault_btn)
        
        layout.add_widget(self.label)
        layout.add_widget(self.pc_ip_input)
        layout.add_widget(self.status_label)
        layout.add_widget(btn_layout)
        layout.add_widget(Widget()) # Pushed the spacer below the buttons!
        
        self.add_widget(layout)
        
        self.sending = False
        self.discovered_pc_ip = None
        self._discovery_running = False

    def on_enter(self):
        if not self._discovery_running:
            app_log("Main screen entered - Launching background workers")
            threading.Thread(target=enable_shizuku_wireless_adb, daemon=True).start()
            self._start_services()

    def restart_connection(self, instance):
        app_log("Restarting connection manually...")
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
        app_log("Discovery listener active")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
                    time.sleep(1)
        except Exception as e:
            app_log(f"Discovery bind error: {e}")

    def start_heartbeat(self, pc_ip):
        self.pc_ip_input.text = pc_ip
        self.status_label.text = f"Found {pc_ip}! Sending heartbeat..."
        if not self.sending:
            self.sending = True
            threading.Thread(target=self.heartbeat_loop, args=(pc_ip,), daemon=True).start()

    def heartbeat_loop(self, target_ip):
        app_log(f"Starting heartbeat to {target_ip}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        port = config["heartbeat_port"]
        while self.sending:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                phone_ip = s.getsockname()[0]
                s.close()
                
                msg = f"HELLO_USER|{phone_ip}|{config['adb_port']}"
                sock.sendto(msg.encode('utf-8'), (target_ip, port))
                app_log(f"Beat sent: {msg}")
            except Exception as e:
                app_log(f"Heartbeat error: {e}")
            time.sleep(5)
        sock.close()

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        title = Label(text="Settings", font_size=sp(24), bold=True, color=ACCENT, size_hint_y=None, height=dp(50))
        layout.add_widget(title)
        
        # Log Info
        log_info = Label(text=f"Logs saved to:\n{LOG_DIR}", font_size=sp(14), color=TEXT, halign='center', size_hint_y=None, height=dp(50))
        log_info.bind(texture_size=lambda i, v: setattr(i, 'height', v[1]))
        layout.add_widget(log_info)
        
        # Logging Toggle
        log_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        log_layout.add_widget(Label(text="Enable Logging", color=TEXT, font_size=sp(16), size_hint_x=0.7))
        self.log_switch = Switch(active=config.get("logging_enabled", False))
        self.log_switch.bind(active=self.on_log_switch)
        log_layout.add_widget(self.log_switch)
        layout.add_widget(log_layout)
        
        # Font picker
        font_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        font_layout.add_widget(Label(text="Use System Font", color=TEXT, font_size=sp(16), size_hint_x=0.7))
        self.font_switch = Switch(active=config.get("use_system_font", True))
        self.font_switch.bind(active=self.on_font_switch)
        font_layout.add_widget(self.font_switch)
        layout.add_widget(font_layout)
        
        # Ports
        self.add_port_spinner(layout, "ADB Port", "adb_port")
        self.add_port_spinner(layout, "Heartbeat Port", "heartbeat_port")
        self.add_port_spinner(layout, "Discovery Port", "discovery_port")
        
        layout.add_widget(Widget()) # Spacer
        
        back_btn = SlopButton(text="[<] Back", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size=sp(18), size_hint_y=None, height=dp(60))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'main'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def add_port_spinner(self, layout, label_text, config_key):
        box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        box.add_widget(Label(text=label_text, color=TEXT, font_size=sp(16), size_hint_x=0.6))
        spinner = Spinner(text=str(config.get(config_key)), values=[str(p) for p in range(5550, 5560)], background_color=PANEL_BG, color=TEXT, size_hint_x=0.4)
        spinner.bind(text=lambda instance, text: self.on_port_change(config_key, text))
        box.add_widget(spinner)
        layout.add_widget(box)

    def on_log_switch(self, instance, value):
        config["logging_enabled"] = value
        save_config(config)
        app_log(f"Logging toggled to {value}")

    def on_font_switch(self, instance, value):
        config["use_system_font"] = value
        save_config(config)
        app_log(f"System font toggled to {value}")

    def on_port_change(self, key, value):
        try:
            config[key] = int(value)
            save_config(config)
            app_log(f"{key} changed to {value}")
        except:
            pass

class HelpScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Colors
        BG = (0.07, 0.05, 0.12, 1)
        TEXT = (0.88, 0.88, 0.88, 1)
        ACCENT = (0.0, 0.85, 0.65, 1)
        
        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        with layout.canvas.before:
            Color(*BG)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self.bg_rect, 'pos', v))
        layout.bind(size=lambda i, v: setattr(self.bg_rect, 'size', v))
        
        title = Label(text="Help & Guide", color=ACCENT, font_size=sp(24), bold=True, size_hint_y=None, height=dp(50))
        layout.add_widget(title)
        
        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8), padding=dp(4))
        content.bind(minimum_height=content.setter('height'))
        
        # Proper Kivy BBCode markup (not HTML!)
        guide_text = (
            "[b]Quick Start:[/b]\n"
            "1. Make sure phone and PC are on the same network.\n"
            "2. Open this app on PC, then open [color=00d9a5]Scrcpy Heartbeat[/color] on your phone.\n\n"
            "[b]Shizuku Setup:[/b]\n"
            "• Run: [font=Roboto][color=00d9a5]rish -c 'adb tcpip 5555'[/color][/font]\n\n"
            "[b]Shizuku Persistent Setup (Auto on Boot):[/b]\n"
            "1. Install Termux + Termux:Boot from F-Droid\n"
            "2. Create [color=00d9a5]~/.termux/boot/99-adb-wifi.sh[/color] with the script from GitHub wiki\n"
            "3. [color=00d9a5]chmod +x ~/.termux/boot/99-adb-wifi.sh[/color]\n"
            "4. Run whitelist commands (see GitHub wiki)\n"
            "5. Reboot phone - ADB over WiFi starts automatically!\n\n"
            "[b]Links:[/b]\n"
            "• GitHub: [ref=https://github.com/HenryCarm/ScrcpyUltimateLink][color=00d9a5]github.com/HenryCarm/ScrcpyUltimateLink[/color][/ref]\n"
            "• Shizuku: [ref=https://shizuku.rikka.app/][color=00d9a5]shizuku.rikka.app[/color][/ref]\n"
            "• Termux:Boot: [ref=https://f-droid.org/packages/com.termux.boot/][color=00d9a5]F-Droid[/color][/ref]"
        )
        
        guide_label = Label(
            text=guide_text,
            markup=True,
            color=TEXT,
            font_size=sp(14),
            halign='left',
            valign='top',
            size_hint_y=None
        )
        # Enable text wrapping and auto-height
        guide_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        guide_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))
        
        content.add_widget(guide_label)
        scroll.add_widget(content)
        layout.add_widget(scroll)
        
        back_btn = SlopButton(text="[<] Back", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size=sp(18), size_hint_y=None, height=dp(60))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'main'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)


# File type icon mapping (lightweight Unicode badges)
FILE_TYPE_ICONS = {
    '.mp4': '[VIDEO]', '.mkv': '[VIDEO]', '.avi': '[VIDEO]', '.mov': '[VIDEO]',
    '.png': '[IMG]', '.jpg': '[IMG]', '.jpeg': '[IMG]', '.webp': '[IMG]', '.gif': '[IMG]',
    '.apk': '[APK]',
    '.mp3': '[AUDIO]', '.wav': '[AUDIO]', '.ogg': '[AUDIO]', '.flac': '[AUDIO]',
    '.pdf': '[DOC]', '.doc': '[DOC]', '.docx': '[DOC]', '.txt': '[DOC]',
    '.zip': '[ARCHIVE]', '.tar': '[ARCHIVE]', '.gz': '[ARCHIVE]',
}

VAULT_DIR = "/sdcard/ScrcpyUltimateLink"


def get_file_icon(filename):
    ext = os.path.splitext(filename)[1].lower()
    return FILE_TYPE_ICONS.get(ext, '[FILE]')


def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def share_file_via_intent(file_path):
    """Fire Android Share Intent via Pyjnius"""
    try:
        from jnius import autoclass, cast
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Intent = autoclass('android.content.Intent')
        Uri = autoclass('android.net.Uri')
        File = autoclass('java.io.File')
        
        context = PythonActivity.mActivity
        file_obj = File(file_path)
        
        # Get content URI via FileProvider
        pkg_name = context.getPackageName()
        try:
            FileProvider = autoclass('androidx.core.content.FileProvider')
            uri = FileProvider.getUriForFile(context, f"{pkg_name}.fileprovider", file_obj)
        except:
            # Fallback: use file:// URI directly
            uri = Uri.fromFile(file_obj)
        
        intent = Intent(Intent.ACTION_SEND)
        intent.setType("*/*")
        intent.putExtra(Intent.EXTRA_STREAM, cast('android.os.Parcelable', uri))
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        
        chooser = Intent.createChooser(intent, "Share File With...")
        context.startActivity(chooser)
    except Exception as e:
        print(f"Share Intent failed: {e}")


class VaultScreen(Screen):
    """Received files vault with file type icons and share functionality"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        BG = (0.07, 0.05, 0.12, 1)
        TEXT = (0.88, 0.88, 0.88, 1)
        ACCENT = (0.0, 0.85, 0.65, 1)
        
        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        with layout.canvas.before:
            Color(*BG)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self.bg_rect, 'pos', v))
        layout.bind(size=lambda i, v: setattr(self.bg_rect, 'size', v))
        
        # Header
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        title = Label(text="Received Files", color=ACCENT, font_size=sp(24), bold=True)
        header.add_widget(title)
        
        refresh_btn = SlopButton(text="[R] Refresh", background_color=(0.059, 0.204, 0.376, 1), color=ACCENT, font_size=sp(14), size_hint_x=None, width=dp(100))
        refresh_btn.bind(on_press=lambda x: self.refresh_vault())
        header.add_widget(refresh_btn)
        layout.add_widget(header)
        
        # File list in scroll view
        self.scroll = ScrollView()
        self.file_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self.file_list.bind(minimum_height=self.file_list.setter('height'))
        self.scroll.add_widget(self.file_list)
        layout.add_widget(self.scroll)
        
        # Empty state
        self.empty_label = Label(text="No files received yet.\nSend files from your PC using File Transfer!", color=(0.5, 0.5, 0.5, 1), font_size=sp(14), halign='center')
        layout.add_widget(self.empty_label)
        
        # Back button
        back_btn = SlopButton(text="[<] Back", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size=sp(18), size_hint_y=None, height=dp(60))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'main'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def on_enter(self):
        self.refresh_vault()
    
    def refresh_vault(self):
        self.file_list.clear_widgets()
        
        try:
            if not os.path.exists(VAULT_DIR):
                os.makedirs(VAULT_DIR, exist_ok=True)
                return
            
            files = sorted(os.listdir(VAULT_DIR), reverse=True)
            received_files = [f for f in files if os.path.isfile(os.path.join(VAULT_DIR, f))]
            
            if not received_files:
                self.empty_label.opacity = 1
                return
            
            self.empty_label.opacity = 0
            
            for filename in received_files:
                filepath = os.path.join(VAULT_DIR, filename)
                try:
                    size = os.path.getsize(filepath)
                    icon = get_file_icon(filename)
                    
                    row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
                    
                    icon_label = Label(text=icon, color=ACCENT, font_size=sp(14), size_hint_x=None, width=dp(70))
                    name_label = Label(text=filename, color=TEXT, font_size=sp(14), halign='left')
                    name_label.bind(width=lambda i, v: setattr(i, 'text_size', (v, None)))
                    size_label = Label(text=format_file_size(size), color=(0.5, 0.5, 0.5, 1), font_size=sp(12), size_hint_x=None, width=dp(80))
                    
                    share_btn = SlopButton(text="Share", background_color=(0.059, 0.204, 0.376, 1), color=ACCENT, font_size=sp(12), size_hint_x=None, width=dp(70))
                    share_btn.bind(on_press=lambda btn, path=filepath: self.share_file(path))
                    
                    row.add_widget(icon_label)
                    row.add_widget(name_label)
                    row.add_widget(size_label)
                    row.add_widget(share_btn)
                    
                    # Add separator line
                    sep = Widget(size_hint_y=None, height=dp(1))
                    with sep.canvas:
                        Color(0.2, 0.2, 0.3, 1)
                        Rectangle(pos=sep.pos, size=sep.size)
                    
                    self.file_list.add_widget(row)
                    self.file_list.add_widget(sep)
                except:
                    continue
        except Exception as e:
            app_log(f"Vault refresh error: {e}")
    
    def share_file(self, file_path):
        share_file_via_intent(file_path)


class HeartbeatApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.add_widget(HelpScreen(name='help'))
        sm.add_widget(VaultScreen(name='vault'))
        return sm

if __name__ == "__main__":
    try:
        HeartbeatApp().run()
    except Exception as e:
        print(f"FATAL APP CRASH: {traceback.format_exc()}")