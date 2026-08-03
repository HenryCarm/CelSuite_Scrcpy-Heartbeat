# Scrcpy Ultimate Link (Dark Green Edition)

A zero-config, cross-platform wireless screen mirroring and control suite built on top of **Scrcpy v4.0+**, featuring an automated Android **Shizuku / Root Heartbeat client** and a close to modern **PyQt6 Tabbed Desktop GUI**.

---

## Key Features

- **Zero-Cable Wireless Mirroring:** Connects your PC and Android device seamlessly over local WiFi or Hotspot without ever needing a dying USB cable.
- **Android Heartbeat & Shizuku Client:** Native Kivy mobile app that binds TCP port `5555` in the background using **Shizuku (`rish`)** or **Magisk Root** with automatic auto-reconnect loops.
- **PyQt6 Tabbed Desktop GUI:** Clean, resizable desktop application with dedicated tabs for Main Controls, Server Configuration, and Setup Guides.
- **Smart mDNS Zero-Config Discovery:** Automatically discovers your phone's IP address and ADB debugging ports across network shifts without slow subnet sweeps.
- **100% Cloud-Compiled Releases:** All standalone Linux desktop binaries and Android APKs are compiled and published automatically via GitHub Actions CI/CD datacenters.

---

## Quick Start & Installation

### 1. Desktop Application (Linux / Windows / macOS)

1. Head over to the [Latest GitHub Release](../../releases/latest) page.
2. Download the standalone executable for your system (e.g., `ScrcpyUltimateLink-Linux-x86_64`).
3. Make it executable and run:

```bash
chmod +x ScrcpyUltimateLink-Linux-x86_64
./ScrcpyUltimateLink-Linux-x86_64
```

> Ensure you have [Scrcpy v4.0+](https://github.com/Genymobile/scrcpy) installed on your system. The app uses your system PATH default (`scrcpy`), but you can point it to a custom binary in the Settings tab.

### 2. Android Heartbeat Client

1. Download the latest `scrcpyheartbeat-*.apk` from the [Releases](../../releases/latest) tab.
2. Install the APK on your Android device (enable *Install from Unknown Sources* if prompted).
3. **Shizuku Setup (Recommended for Unrooted Devices):**
   - Open your [Shizuku](https://shizuku.rikka.app/) app and ensure the service is running.
   - Go to **Authorized Applications** inside Shizuku and toggle **Scrcpy Heartbeat** to **ON**.
   - Open the app and tap **Restart Connection** to instantly bind your wireless debugging port.

---

## How It Works

```
Phone (Heartbeat)                    PC (Listener)
       |                                  |
       |--- UDP "HELLO_USER|IP|PORT" --->|  (Auto-Discovery)
       |                                  |
       |<--- ADB connect IP:PORT --------|  (TCP Binding)
       |                                  |
       |<--- scrcpy --tcpip=IP:PORT -----|  (Mirroring!)
```

1. The Android app broadcasts a UDP heartbeat packet containing the device IP and ADB port.
2. The PC listener receives the packet, connects via ADB, and launches `scrcpy` automatically.
3. If the connection drops, the phone retries every 5 seconds until the PC is back online.

---

## Architecture & Portability

- **Portable Configuration:** All settings and logs are saved dynamically using `sys.argv[0]` pathing right next to your executable binary. No hardcoded paths anywhere.
- **Cloud Builds:** Pushing a version tag (`v*`) automatically spins up GitHub Actions to compile both the Nuitka PC executable and the Buildozer Android APK simultaneously, then publishes them as release assets.
- **Android 11+ Scoped Storage:** Fully supports modern Android storage Intents (`MANAGE_EXTERNAL_STORAGE`) with automatic fallback to internal private app directories.

---

## Development

### Building Locally (Not Recommended on Metered Networks)

**PC Binary (Nuitka):**
```bash
python compile_nuitka.py
```

**Android APK (Buildozer):**
```bash
cd android
buildozer android debug
```

### Cloud Builds (Recommended)

```bash
git tag v268.03.15
git push origin v268.03.15
```

GitHub Actions will automatically compile and publish both binaries to the Releases page.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
