import socket
import subprocess
import sys
import os
import time
import threading
import json
import shutil
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

def load_config():
    defaults = {
        "heartbeat_port": 5556,
        "discovery_port": 5557,
        "adb_port": 5555,
        "scrcpy_bin": "scrcpy",
        "last_ip_file": os.path.join(APP_DIR, "last_ip.txt"),
        "log_file": os.path.join(APP_DIR, "ScrcpyUltimateLink_debug.log")
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

# Configuration
HEARTBEAT_PORT = config["heartbeat_port"]
DISCOVERY_PORT = config["discovery_port"]
ADB_PORT = config["adb_port"]
SCRCPY_BIN = config["scrcpy_bin"]
LAST_IP_FILE = config["last_ip_file"]
LOG_FILE = config["log_file"]

# Track if scrcpy is already running
scrcpy_process = None
scrcpy_lock = threading.Lock()
current_phone_ip = None

# Callback for GUI log panel display
_gui_log_callback = None

def set_gui_log_callback(callback):
    global _gui_log_callback
    _gui_log_callback = callback

def log(msg, also_print=True):
    """Write to log file, print to stdout, and update GUI panel."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {msg}"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass
    if also_print:
        print(line, flush=True)
    if _gui_log_callback:
        _gui_log_callback(line)

def get_local_ip():
    """Get the actual local IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"unknown ({e})"

def get_adb_devices():
    """Get list of connected ADB devices."""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3)
        lines = result.stdout.strip().split('\n')
        devices = []
        for line in lines[1:]:
            if line.strip():
                parts = line.split('\t')
                if len(parts) == 2:
                    devices.append({"serial": parts[0], "status": parts[1]})
        return devices
    except Exception as e:
        log(f"Error getting ADB devices: {e}")
        return []

def is_phone_connected(phone_ip, adb_port=ADB_PORT):
    """Check if the specific phone IP is connected via ADB on the given port."""
    devices = get_adb_devices()
    target = f"{phone_ip}:{adb_port}"
    for d in devices:
        if target in d["serial"] and d["status"] == "device":
            return True
    return False

def get_connected_phone_ip():
    """Get the actual phone IP and port from adb devices (the one ADB can reach)."""
    devices = get_adb_devices()
    for d in devices:
        if d["status"] == "device" and ":" in d["serial"]:
            parts = d["serial"].split(":")
            ip = parts[0]
            try:
                port = int(parts[1])
            except:
                port = ADB_PORT
            return ip, port
    return None, None


# --- REMOTE CONTROL HELPERS (FEATURE 2, 4, 5) ---

def send_adb_keyevent(key_code, phone_ip=None, adb_port=ADB_PORT):
    """Send Android keyevent."""
    target_ip = phone_ip or current_phone_ip
    if not target_ip:
        return False, "No phone IP available"
    try:
        cmd = ["adb", "-s", f"{target_ip}:{adb_port}", "shell", "input", "keyevent", str(key_code)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return res.returncode == 0, res.stdout or res.stderr
    except Exception as e:
        return False, str(e)

def send_adb_text(text, phone_ip=None, adb_port=ADB_PORT):
    """Send text to phone clipboard or text input."""
    target_ip = phone_ip or current_phone_ip
    if not target_ip:
        return False, "No phone IP available"
    try:
        # Broadcast standard intent with text parameter for Kivy app to receive
        # (This bypasses issues with spaces and non-ASCII in standard 'input text'!)
        cmd = ["adb", "-s", f"{target_ip}:{adb_port}", "shell", "am", "broadcast", 
               "-a", "org.henry.scrcpy.SET_CLIPBOARD", "--es", "text", text]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        return res.returncode == 0, "Clipboard pushed successfully"
    except Exception as e:
        return False, str(e)

def open_url_on_phone(url, phone_ip=None, adb_port=ADB_PORT):
    """Open URL on phone browser."""
    target_ip = phone_ip or current_phone_ip
    if not target_ip:
        return False, "No phone IP available"
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        cmd = ["adb", "-s", f"{target_ip}:{adb_port}", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        return res.returncode == 0, f"Opened URL: {url}"
    except Exception as e:
        return False, str(e)

def get_device_hardware_info(phone_ip=None, adb_port=ADB_PORT):
    """Query live device specs: Battery, Charging, Temperature, Resolution, Model, Android version."""
    target_ip = phone_ip or current_phone_ip
    if not target_ip:
        return {"error": "No device connected"}
    
    target = f"{target_ip}:{adb_port}"
    info = {"ip": target_ip, "port": adb_port}
    try:
        # Battery stats
        batt_cmd = subprocess.run(["adb", "-s", target, "shell", "dumpsys", "battery"], capture_output=True, text=True, timeout=3)
        if batt_cmd.returncode == 0:
            for line in batt_cmd.stdout.splitlines():
                line = line.strip()
                if line.startswith("level:"):
                    info["battery_level"] = f"{line.split(':')[1].strip()}%"
                elif line.startswith("status:"):
                    code = line.split(':')[1].strip()
                    info["charging"] = "Charging ⚡" if code in ["2", "5"] else "Discharging 🔋"
                elif line.startswith("temperature:"):
                    try:
                        raw_t = int(line.split(':')[1].strip())
                        info["temperature"] = f"{raw_t / 10.0:.1f}°C"
                    except:
                        pass
        
        # Model & Android version
        props_cmd = subprocess.run(["adb", "-s", target, "shell", "getprop", "ro.product.model"], capture_output=True, text=True, timeout=3)
        if props_cmd.returncode == 0:
            info["model"] = props_cmd.stdout.strip()
            
        ver_cmd = subprocess.run(["adb", "-s", target, "shell", "getprop", "ro.build.version.release"], capture_output=True, text=True, timeout=3)
        if ver_cmd.returncode == 0:
            info["android_version"] = f"Android {ver_cmd.stdout.strip()}"

        # Display size
        wm_cmd = subprocess.run(["adb", "-s", target, "shell", "wm", "size"], capture_output=True, text=True, timeout=3)
        if wm_cmd.returncode == 0:
            info["resolution"] = wm_cmd.stdout.strip().replace("Physical size: ", "")
            
    except Exception as e:
        info["error"] = str(e)
        
    return info

def test_network_latency(phone_ip=None, adb_port=ADB_PORT):
    """Test ping latency to the phone in ms."""
    target_ip = phone_ip or current_phone_ip
    if not target_ip:
        return None, "No phone IP available"
    
    times = []
    for _ in range(3):
        try:
            start = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            s.connect((target_ip, adb_port))
            s.close()
            latency = (time.time() - start) * 1000.0
            times.append(latency)
        except:
            pass
        time.sleep(0.05)
    
    if times:
        avg_latency = sum(times) / len(times)
        return avg_latency, f"Average Ping: {avg_latency:.1f} ms"
    return None, "Timeout"


# --- MONITOR & PROCESS HANDLERS ---

def start_scrcpy(phone_ip=None, adb_port=ADB_PORT, extra_args=None):
    """Connects to the device, saves IP to desktop, and launches scrcpy."""
    global scrcpy_process, current_phone_ip
    
    # Fast exit: if scrcpy is already running, do nothing
    if scrcpy_process and scrcpy_process.poll() is None:
        return True
    
    with scrcpy_lock:
        target_ip = phone_ip
        if not target_ip:
            log("ERROR: No phone IP provided")
            return False
        
        # Check if phone is already connected via ADB
        connected_ip, connected_port = get_connected_phone_ip()
        if connected_ip:
            log(f"Phone already connected via ADB at {connected_ip}:{connected_port}")
            target_ip = connected_ip
            adb_port = connected_port
        
        current_phone_ip = target_ip
        
        # Save the ACTUAL working IP to file
        try:
            with open(LAST_IP_FILE, "w") as f:
                f.write(str(target_ip))
        except Exception as e:
            log(f"Could not save IP to {LAST_IP_FILE}: {e}")
        
        # Check if scrcpy is already running (double-check inside lock)
        if scrcpy_process and scrcpy_process.poll() is None:
            return True
        
        # Check if phone is already connected via ADB
        if not is_phone_connected(target_ip, adb_port):
            log(f"Connecting to phone at {target_ip}:{adb_port}...")
            result = subprocess.run(["adb", "connect", f"{target_ip}:{adb_port}"], capture_output=True, text=True, timeout=5)
            log(f"ADB connect stdout: {result.stdout.strip()}")
            
            if "connected to" not in result.stdout.lower() and "already connected" not in result.stdout.lower():
                log(f"Failed to connect to {target_ip}:{adb_port}")
                return False
        else:
            log(f"Phone already connected at {target_ip}:{adb_port}")
        
        log(f"Connected! Launching scrcpy on port {adb_port}...")
        cmd = [SCRCPY_BIN, "--audio-source=playback", "-s", f"{target_ip}:{adb_port}"]
        if extra_args:
            if isinstance(extra_args, list):
                cmd.extend(extra_args)
            elif isinstance(extra_args, str):
                cmd.extend(extra_args.split())
        scrcpy_process = subprocess.Popen(cmd)
        return True

def monitor_scrcpy():
    """Monitor scrcpy process and restart if it dies, safely without holding locks during sleep."""
    global scrcpy_process, current_phone_ip
    
    while True:
        time.sleep(2)
        run_reconnect = False
        with scrcpy_lock:
            if scrcpy_process and scrcpy_process.poll() is not None:
                exit_code = scrcpy_process.poll()
                log(f"scrcpy exited with code {exit_code}, attempting reconnect...")
                scrcpy_process = None
                run_reconnect = True
        
        if run_reconnect and current_phone_ip:
            log(f"Reconnecting to {current_phone_ip}...")
            start_scrcpy(current_phone_ip)

def listen_for_heartbeat():
    """Listens for UDP packets from the Android app."""
    local_ip = get_local_ip()
    log("=" * 60)
    log("Scrcpy Ultimate Link - Heartbeat Listener Starting...")
    log(f"Local PC IP: {local_ip}")
    log(f"Heartbeat port: {HEARTBEAT_PORT}")
    log("=" * 60)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", HEARTBEAT_PORT))
    except Exception as e:
        log(f"FAILED to bind port {HEARTBEAT_PORT}: {e}")
        return
    
    sock.settimeout(5.0)
    
    beat_count = 0
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            beat_count += 1
            message = data.decode('utf-8').strip()
            ip = addr[0]
            
            if "HELLO_" in message:
                phone_ip = None
                adb_port = ADB_PORT
                parts = message.split('|')
                if len(parts) >= 3:
                    phone_ip = parts[1].strip()
                    try:
                        adb_port = int(parts[2].strip())
                    except:
                        adb_port = ADB_PORT
                else:
                    phone_ip = ip
                
                log(f"Attempting connection to PHONE IP: {phone_ip}:{adb_port}")
                start_scrcpy(phone_ip, adb_port)
        except socket.timeout:
            pass
        except Exception as e:
            time.sleep(1)

def broadcast_discovery():
    """Broadcast PC's presence for phone discovery."""
    local_ip = get_local_ip()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    message = f"SCRCPC_HERE {local_ip} {HEARTBEAT_PORT}".encode()
    
    while True:
        try:
            sock.sendto(message, ('255.255.255.255', DISCOVERY_PORT))
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_iface_ip = s.getsockname()[0]
            s.close()
            parts = local_iface_ip.split('.')
            if len(parts) == 4:
                bcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                sock.sendto(message, (bcast, DISCOVERY_PORT))
        except:
            pass
        time.sleep(3)

if __name__ == "__main__":
    # Clear old log
    try:
        with open(LOG_FILE, "w") as f:
            f.write("")
    except:
        pass
    log("Logger initialized.")
    
    # Start monitor thread
    monitor_thread = threading.Thread(target=monitor_scrcpy, daemon=True)
    monitor_thread.start()
    
    # Start discovery broadcast thread
    broadcast_thread = threading.Thread(target=broadcast_discovery, daemon=True)
    broadcast_thread.start()
    
    try:
        listen_for_heartbeat()
    except KeyboardInterrupt:
        log("\nStopping listener... See you soon!")
