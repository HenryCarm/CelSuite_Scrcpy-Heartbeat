"""
ADB command wrappers for ScrcpyUltimateLink.

Every ADB interaction flows through this module so we get consistent
error handling, timeout management, and logging.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from typing import Any, Optional

from src.config import AppConfig
from src.constants import (
    ADB_COMMAND_TIMEOUT_SEC,
    ADB_CONNECT_TIMEOUT_SEC,
    DEFAULT_ADB_PORT,
)
from src.logger import get_logger

log = get_logger(__name__)

# ── Device Cache ──────────────────────────────────────────────────────────────
# ADB devices results are cached for a short period to avoid hammering the ADB
# server on every heartbeat + dashboard refresh cycle.

_device_cache: list[dict[str, str]] = []
_device_cache_time: float = 0.0
_device_cache_ttl: float = 2.0  # seconds
_device_cache_lock = threading.Lock()


def _clear_device_cache() -> None:
    """Invalidate the device cache."""
    global _device_cache_time
    with _device_cache_lock:
        _device_cache_time = 0.0


# ── Binary Detection ──────────────────────────────────────────────────────────

def find_adb_binary(config: AppConfig) -> str:
    """Return the path to the ADB binary, checking config then PATH."""
    configured = config.get("adb_bin", "adb")
    if configured and configured != "adb" and shutil.which(configured):
        return configured
    found = shutil.which("adb")
    if found:
        return found
    return "adb"  # Let it fail at runtime with a clear error


def is_adb_available(config: AppConfig) -> bool:
    """Check if ADB is reachable."""
    adb = find_adb_binary(config)
    try:
        result = subprocess.run(
            [adb, "version"],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_adb_version(config: AppConfig) -> str:
    """Return the ADB version string, or an error message."""
    adb = find_adb_binary(config)
    try:
        result = subprocess.run(
            [adb, "version"],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        if result.returncode == 0:
            first_line = result.stdout.strip().split("\n")[0]
            return first_line
        return f"ADB error: {result.stderr.strip()}"
    except FileNotFoundError:
        return "ADB not found"
    except subprocess.SubprocessError as exc:
        return f"ADB error: {exc}"


# ── Device Listing ────────────────────────────────────────────────────────────

def get_adb_devices(config: AppConfig) -> list[dict[str, str]]:
    """
    Return a list of connected ADB devices.

    Each entry is ``{"serial": "ip:port", "status": "device"}``.
    Results are cached for 2 seconds to reduce subprocess overhead.
    """
    global _device_cache, _device_cache_time

    with _device_cache_lock:
        if time.time() - _device_cache_time < _device_cache_ttl:
            return list(_device_cache)

    adb = find_adb_binary(config)
    devices: list[dict[str, str]] = []
    try:
        result = subprocess.run(
            [adb, "devices"],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n")[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) == 2:
                    devices.append({"serial": parts[0], "status": parts[1]})
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        log.warning("Failed to list ADB devices: %s", exc)

    with _device_cache_lock:
        _device_cache = devices
        _device_cache_time = time.time()

    return devices


def is_phone_connected(
    config: AppConfig,
    phone_ip: str,
    adb_port: int = DEFAULT_ADB_PORT,
) -> bool:
    """Check if a specific phone IP:port is connected and authorized."""
    target = f"{phone_ip}:{adb_port}"
    for d in get_adb_devices(config):
        if target in d["serial"] and d["status"] == "device":
            return True
    return False


def get_connected_phone(config: AppConfig) -> tuple[Optional[str], Optional[int]]:
    """
    Return ``(ip, port)`` of the first wirelessly connected device,
    or ``(None, None)`` if none found.
    """
    for d in get_adb_devices(config):
        if d["status"] == "device" and ":" in d["serial"]:
            parts = d["serial"].split(":")
            ip = parts[0]
            try:
                port = int(parts[1])
            except (ValueError, IndexError):
                port = config.get("adb_port", DEFAULT_ADB_PORT)
            return ip, port
    return None, None


# ── Connection Management ─────────────────────────────────────────────────────

def connect(
    config: AppConfig,
    phone_ip: str,
    adb_port: int = DEFAULT_ADB_PORT,
) -> tuple[bool, str]:
    """
    Connect to a phone via ADB wireless.

    Returns ``(success, message)``
    """
    adb = find_adb_binary(config)
    target = f"{phone_ip}:{adb_port}"

    # Already connected?
    if is_phone_connected(config, phone_ip, adb_port):
        log.info("Phone already connected at %s", target)
        return True, f"Already connected to {target}"

    log.info("Connecting to phone at %s ...", target)
    try:
        result = subprocess.run(
            [adb, "connect", target],
            capture_output=True, text=True,
            timeout=ADB_CONNECT_TIMEOUT_SEC,
        )
        output = result.stdout.strip().lower()
        log.debug("ADB connect output: %s", result.stdout.strip())

        if "connected to" in output or "already connected" in output:
            _clear_device_cache()
            return True, f"Connected to {target}"
        else:
            return False, f"Connection failed: {result.stdout.strip()}"
    except FileNotFoundError:
        return False, "ADB binary not found"
    except subprocess.TimeoutExpired:
        return False, f"Connection to {target} timed out"
    except subprocess.SubprocessError as exc:
        return False, f"ADB error: {exc}"


def disconnect(
    config: AppConfig,
    phone_ip: str,
    adb_port: int = DEFAULT_ADB_PORT,
) -> tuple[bool, str]:
    """Disconnect a specific device."""
    adb = find_adb_binary(config)
    target = f"{phone_ip}:{adb_port}"
    try:
        result = subprocess.run(
            [adb, "disconnect", target],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        _clear_device_cache()
        return True, f"Disconnected from {target}"
    except subprocess.SubprocessError as exc:
        return False, f"Disconnect failed: {exc}"


def disconnect_all(config: AppConfig) -> None:
    """Disconnect all ADB devices (cleanup on app exit)."""
    adb = find_adb_binary(config)
    try:
        subprocess.run(
            [adb, "disconnect"],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        _clear_device_cache()
    except subprocess.SubprocessError:
        pass


# ── Remote Commands ───────────────────────────────────────────────────────────

def send_keyevent(
    config: AppConfig,
    key_code: int,
    phone_ip: Optional[str] = None,
    adb_port: int = DEFAULT_ADB_PORT,
) -> tuple[bool, str]:
    """Send an Android keyevent to the device."""
    if not phone_ip:
        phone_ip, _ = get_connected_phone(config)
    if not phone_ip:
        return False, "No phone connected"

    adb = find_adb_binary(config)
    target = f"{phone_ip}:{adb_port}"
    try:
        result = subprocess.run(
            [adb, "-s", target, "shell", "input", "keyevent", str(key_code)],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        return result.returncode == 0, result.stdout or result.stderr
    except subprocess.SubprocessError as exc:
        return False, str(exc)


def send_broadcast(
    config: AppConfig,
    action: str,
    extras: Optional[dict[str, str]] = None,
    phone_ip: Optional[str] = None,
    adb_port: int = DEFAULT_ADB_PORT,
) -> tuple[bool, str]:
    """Send an Android broadcast intent."""
    if not phone_ip:
        phone_ip, _ = get_connected_phone(config)
    if not phone_ip:
        return False, "No phone connected"

    adb = find_adb_binary(config)
    target = f"{phone_ip}:{adb_port}"
    cmd = [adb, "-s", target, "shell", "am", "broadcast", "-a", action]
    if extras:
        for key, value in extras.items():
            cmd.extend(["--es", key, value])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.SubprocessError as exc:
        return False, str(exc)


def open_url(
    config: AppConfig,
    url: str,
    phone_ip: Optional[str] = None,
    adb_port: int = DEFAULT_ADB_PORT,
) -> tuple[bool, str]:
    """Open a URL on the phone's browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not phone_ip:
        phone_ip, _ = get_connected_phone(config)
    if not phone_ip:
        return False, "No phone connected"

    adb = find_adb_binary(config)
    target = f"{phone_ip}:{adb_port}"
    try:
        result = subprocess.run(
            [adb, "-s", target, "shell", "am", "start",
             "-a", "android.intent.action.VIEW", "-d", url],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        return result.returncode == 0, f"Opened: {url}"
    except subprocess.SubprocessError as exc:
        return False, str(exc)


# ── Hardware Info ─────────────────────────────────────────────────────────────

def get_hardware_info(
    config: AppConfig,
    phone_ip: Optional[str] = None,
    adb_port: int = DEFAULT_ADB_PORT,
) -> dict[str, Any]:
    """
    Query live device specs in a single batched ADB shell command.

    Returns a dict with keys: model, android_version, battery_level,
    charging, temperature, resolution, error (if any).
    """
    if not phone_ip:
        phone_ip, _ = get_connected_phone(config)
    if not phone_ip:
        return {"error": "No device connected"}

    adb = find_adb_binary(config)
    target = f"{phone_ip}:{adb_port}"
    info: dict[str, Any] = {"ip": phone_ip, "port": adb_port}

    # Batch multiple queries into one shell call for efficiency
    batch_cmd = "getprop ro.product.model; getprop ro.build.version.release; dumpsys battery; wm size"

    try:
        result = subprocess.run(
            [adb, "-s", target, "shell", batch_cmd],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC + 2,
        )
        if result.returncode != 0:
            info["error"] = "ADB command failed"
            return info

        output = result.stdout
        lines = [l.strip() for l in output.splitlines() if l.strip()]

        if lines:
            info["model"] = lines[0]
        if len(lines) > 1:
            info["android_version"] = f"Android {lines[1]}"

        import re
        lvl = re.search(r"level:\s*(\d+)", output)
        if lvl:
            info["battery_level"] = f"{lvl.group(1)}%"

        st = re.search(r"status:\s*(\d+)", output)
        if st and st.group(1) in ("2", "5"):
            info["charging"] = "Charging"
        else:
            info["charging"] = "Discharging"

        temp = re.search(r"temperature:\s*(\d+)", output)
        if temp:
            try:
                info["temperature"] = f"{int(temp.group(1)) / 10.0:.1f}\u00b0C"
            except ValueError:
                pass

        res = re.search(r"Physical size:\s*(\d+x\d+)", output)
        if res:
            info["resolution"] = res.group(1)

    except FileNotFoundError:
        info["error"] = "ADB not found"
    except subprocess.TimeoutExpired:
        info["error"] = "ADB timeout"
    except subprocess.SubprocessError as exc:
        info["error"] = str(exc)

    return info


# ── Screenshot & Recording ────────────────────────────────────────────────────

def take_screenshot(
    config: AppConfig,
    save_path: str,
    phone_ip: Optional[str] = None,
    adb_port: int = DEFAULT_ADB_PORT,
) -> tuple[bool, str]:
    """Capture a screenshot from the device and pull it to *save_path*."""
    if not phone_ip:
        phone_ip, _ = get_connected_phone(config)
    if not phone_ip:
        return False, "No phone connected"

    adb = find_adb_binary(config)
    target = f"{phone_ip}:{adb_port}"
    remote_path = "/sdcard/scrcpy_screenshot_tmp.png"

    try:
        subprocess.run(
            [adb, "-s", target, "shell", "screencap", "-p", remote_path],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        subprocess.run(
            [adb, "-s", target, "pull", remote_path, save_path],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        # Clean up remote temp file
        subprocess.run(
            [adb, "-s", target, "shell", "rm", remote_path],
            capture_output=True, text=True,
            timeout=ADB_COMMAND_TIMEOUT_SEC,
        )
        log.info("Screenshot saved: %s", save_path)
        return True, f"Screenshot saved: {save_path}"
    except subprocess.SubprocessError as exc:
        return False, f"Screenshot failed: {exc}"


# ── scrcpy Launch ─────────────────────────────────────────────────────────────

_scrcpy_process: Optional[subprocess.Popen] = None
_scrcpy_lock = threading.Lock()


def launch_scrcpy(
    config: AppConfig,
    phone_ip: str,
    adb_port: int = DEFAULT_ADB_PORT,
    extra_args: Optional[list[str]] = None,
) -> tuple[bool, str]:
    """
    Connect to device via ADB and launch scrcpy.

    Returns ``(success, message)``.
    """
    global _scrcpy_process

    # Check if already running
    with _scrcpy_lock:
        if _scrcpy_process is not None and _scrcpy_process.poll() is None:
            return True, "scrcpy is already running"

    # Connect via ADB first
    connected, msg = connect(config, phone_ip, adb_port)
    if not connected:
        return False, msg

    # Save the working IP for next time
    config.update({
        "last_phone_ip": phone_ip,
        "last_phone_port": adb_port,
    })

    # Build scrcpy command
    scrcpy_bin = config.get("scrcpy_bin", "scrcpy")
    cmd = [
        scrcpy_bin,
        "--audio-source=playback",
        "-s", f"{phone_ip}:{adb_port}",
    ]
    if extra_args:
        cmd.extend(extra_args)

    log.info("Launching scrcpy: %s", " ".join(cmd))

    with _scrcpy_lock:
        try:
            _scrcpy_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            return True, f"scrcpy launched (PID {_scrcpy_process.pid})"
        except FileNotFoundError:
            return False, f"scrcpy binary not found: {scrcpy_bin}"
        except subprocess.SubprocessError as exc:
            return False, f"Failed to launch scrcpy: {exc}"


def is_scrcpy_running() -> bool:
    """Check if the scrcpy process is still alive."""
    with _scrcpy_lock:
        return _scrcpy_process is not None and _scrcpy_process.poll() is None


def get_scrcpy_pid() -> Optional[int]:
    """Return the PID of the running scrcpy process, or None."""
    with _scrcpy_lock:
        if _scrcpy_process is not None and _scrcpy_process.poll() is None:
            return _scrcpy_process.pid
    return None


def stop_scrcpy() -> None:
    """Terminate the running scrcpy process."""
    global _scrcpy_process
    with _scrcpy_lock:
        if _scrcpy_process is not None:
            try:
                _scrcpy_process.terminate()
                _scrcpy_process.wait(timeout=3)
            except subprocess.SubprocessError:
                try:
                    _scrcpy_process.kill()
                except subprocess.SubprocessError:
                    pass
            _scrcpy_process = None
            log.info("scrcpy process terminated")


def monitor_scrcpy(
    config: AppConfig,
    phone_ip: str,
    adb_port: int,
    on_restart: Optional[callable] = None,
) -> None:
    """
    Monitor scrcpy and restart if it exits unexpectedly.

    Designed to be run in a daemon thread.
    """
    global _scrcpy_process

    while True:
        time.sleep(2)
        with _scrcpy_lock:
            if _scrcpy_process is not None and _scrcpy_process.poll() is not None:
                exit_code = _scrcpy_process.poll()
                log.warning("scrcpy exited (code %d), attempting reconnect...", exit_code)
                _scrcpy_process = None

                if on_restart:
                    on_restart()
                else:
                    launch_scrcpy(config, phone_ip, adb_port)
