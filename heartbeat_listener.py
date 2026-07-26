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
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
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
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
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
    """Get the actual phone IP from adb devices (the one ADB can reach)."""
    devices = get_adb_devices()
    for d in devices:
        if d["status"] == "device" and ":" in d["serial"]:
            ip = d["serial"].split(":")[0]
            return ip
    return None

def start_scrcpy(phone_ip=None, adb_port=ADB_PORT):
    """Connects to the device, saves IP to desktop, and launches scrcpy."""
    global scrcpy_process, current_phone_ip
    
    with scrcpy_lock:
        target_ip = phone_ip
        if not target_ip:
            log("ERROR: No phone IP provided")
            return False
        
        # Check if phone is already connected via ADB — use THAT IP instead
        connected_ip = get_connected_phone_ip()
        if connected_ip:
            log(f"Phone already connected via ADB at {connected_ip} (ignoring heartbeat IP {target_ip})")
            target_ip = connected_ip
        
        current_phone_ip = target_ip
        
        # Save the ACTUAL working IP to file
        try:
            with open(LAST_IP_FILE, "w") as f:
                f.write(str(target_ip))
            log(f"Saved active phone IP {target_ip} straight to {LAST_IP_FILE}!")
        except Exception as e:
            log(f"Could not save IP to {LAST_IP_FILE}: {e}")
        
        # Check if scrcpy is already running
        if scrcpy_process and scrcpy_process.poll() is None:
            return True
        
        # Check if phone is already connected via ADB
        if not is_phone_connected(target_ip, adb_port):
            log(f"Connecting to phone at {target_ip}:{adb_port}...")
            result = subprocess.run(["adb", "connect", f"{target_ip}:{adb_port}"], capture_output=True, text=True)
            log(f"ADB connect stdout: {result.stdout.strip()}")
            log(f"ADB connect stderr: {result.stderr.strip()}")
            
            if "connected to" not in result.stdout.lower() and "already connected" not in result.stdout.lower():
                log(f"Failed to connect to {target_ip}:{adb_port}. Is ADB over TCP enabled?")
                return False
        else:
            log(f"Phone already connected at {target_ip}:{adb_port}")
        
        log(f"Connected! Launching scrcpy on port {adb_port}...")
        scrcpy_process = subprocess.Popen([SCRCPY_BIN, "--audio-source=playback", "-s", f"{target_ip}:{adb_port}"])
        return True

def monitor_scrcpy():
    """Monitor scrcpy process and restart if it dies."""
    global scrcpy_process, current_phone_ip
    
    while True:
        with scrcpy_lock:
            if scrcpy_process and scrcpy_process.poll() is None:
                # scrcpy is running fine — check less frequently to save battery
                time.sleep(30)
                continue
            elif scrcpy_process and scrcpy_process.poll() is not None:
                exit_code = scrcpy_process.poll()
                log(f"scrcpy exited with code {exit_code}, attempting reconnect...")
                scrcpy_process = None
                
                if current_phone_ip:
                    log(f"Reconnecting to {current_phone_ip}...")
                    start_scrcpy(current_phone_ip)
                else:
                    log("No phone IP to reconnect to, waiting for heartbeat...")
            else:
                # No scrcpy process — check occasionally in case we need to launch
                time.sleep(10)
        time.sleep(2)

def listen_for_heartbeat():
    """Listens for UDP packets from the Android app."""
    local_ip = get_local_ip()
    log("=" * 60)
    log("Scrcpy Ultimate Link - Heartbeat Listener Starting...")
    log(f"Local PC IP: {local_ip}")
    log(f"Heartbeat port: {HEARTBEAT_PORT}")
    log(f"Discovery port: {DISCOVERY_PORT}")
    log(f"ADB port: {ADB_PORT}")
    log(f"SCRCPY_BIN: {SCRCPY_BIN}")
    
    # Check ADB availability cleanly on Windows, Mac, and Linux:
    adb_path = shutil.which('adb') or "Not found in PATH"
    log(f"ADB available at: {adb_path}")
    
    log("=" * 60)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", HEARTBEAT_PORT))
        log(f"Bound to 0.0.0.0:{HEARTBEAT_PORT}")
    except Exception as e:
        log(f"FAILED to bind port {HEARTBEAT_PORT}: {e}")
        log(f"   Check if another process is using it: lsof -i :{HEARTBEAT_PORT}")
        return
    
    sock.settimeout(5.0)
    log(f"Heartbeat listener ACTIVE on port {HEARTBEAT_PORT}...")
    log("Waiting for phone to say hello...")
    
    beat_count = 0
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            beat_count += 1
            message = data.decode('utf-8').strip()
            ip = addr[0]
            
            log(f"[Beat #{beat_count}] From {addr[0]}:{addr[1]} -> Message: '{message}'")
            
            if "HELLO_" in message or "SCRCPY_LINK" in message:
                log(f"VALID heartbeat from {ip}!")
                # Parse phone IP and ADB port from message: "HELLO_<HOSTNAME>|PHONE_IP|ADB_PORT"
                phone_ip = None
                adb_port = ADB_PORT  # default
                parts = message.split('|')
                if len(parts) >= 3:
                    phone_ip = parts[1].strip()
                    try:
                        adb_port = int(parts[2].strip())
                    except:
                        adb_port = ADB_PORT
                    log(f"Phone ADB IP from heartbeat: '{phone_ip}' (sender: {ip}), ADB port: {adb_port}")
                elif '|' in message:
                    phone_ip = message.split('|')[-1].strip()
                    log(f"WARNING: Old format heartbeat, using default ADB port: {adb_port}")
                else:
                    log(f"WARNING: No phone IP in heartbeat, using sender IP: {ip}")
                    phone_ip = ip
                
                # Automatically save connected IP to Desktop for Win/Mac/Linux scripts:
                try:
                    desktop_file = os.path.join(os.path.expanduser("~"), "Desktop", "phone_ip.txt")
                    with open(desktop_file, "w") as f:
                        f.write(f"{phone_ip}:{adb_port}")
                    log(f"Saved phone IP to {desktop_file}")
                except Exception as e:
                    log(f"Could not save phone IP to desktop: {e}")
                
                log(f"Attempting connection to PHONE IP: {phone_ip}:{adb_port}")
                if start_scrcpy(phone_ip, adb_port):
                    log("Success! Everything is mirrored!")
                else:
                    log("Heartbeat was heard, but ADB connection failed.")
            else:
                log(f"Ignoring non-HELLO packet: '{message}' from {ip}")
                
        except socket.timeout:
            log(f"Still listening... (received {beat_count} total packets so far)")
        except Exception as e:
            log(f"Socket error: {e}")
            time.sleep(1)

def broadcast_discovery():
    """Broadcast PC's presence for phone discovery."""
    local_ip = get_local_ip()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    message = f"SCRCPC_HERE {local_ip} {HEARTBEAT_PORT}".encode()
    
    log(f"Starting discovery broadcast on port {DISCOVERY_PORT} (PC IP: {local_ip})")
    
    while True:
        try:
            sock.sendto(message, ('255.255.255.255', DISCOVERY_PORT))
            # Also send to each interface's broadcast
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_iface_ip = s.getsockname()[0]
            s.close()
            parts = local_iface_ip.split('.')
            if len(parts) == 4:
                bcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                sock.sendto(message, (bcast, DISCOVERY_PORT))
        except Exception as e:
            log(f"Broadcast error: {e}")
        time.sleep(3)

if __name__ == "__main__":
    # Clear old log
    with open(LOG_FILE, "w") as f:
        f.write("")
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