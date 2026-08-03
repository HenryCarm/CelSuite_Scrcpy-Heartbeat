"""
Live hardware dashboard widget for ScrcpyUltimateLink.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFormLayout, QGroupBox, QLabel, QPushButton


class DashboardWidget(QGroupBox):
    """
    Displays live device hardware info: model, Android version,
    battery, temperature, resolution, and network latency.
    """

    def __init__(self) -> None:
        super().__init__("\U0001f4ca  Live Hardware Dashboard")

        form = QFormLayout(self)
        form.setSpacing(6)

        self.model_label = QLabel("Model: \u2014")
        self.android_label = QLabel("Android: \u2014")
        self.battery_label = QLabel("Battery: \u2014")
        self.temp_label = QLabel("Temp: \u2014")
        self.resolution_label = QLabel("Resolution: \u2014")
        self.latency_label = QLabel("WiFi Latency: \u2014")

        form.addRow(self.model_label, self.android_label)
        form.addRow(self.battery_label, self.temp_label)
        form.addRow(self.resolution_label, self.latency_label)

        self.refresh_btn = QPushButton("\U0001f504  Refresh")
        form.addRow(self.refresh_btn)

    def update_info(self, info: dict) -> None:
        """Update dashboard labels from a hardware info dict."""
        if "error" in info:
            return

        self.model_label.setText(f"Model: {info.get('model', '\u2014')}")
        self.android_label.setText(f"Android: {info.get('android_version', '\u2014')}")
        self.battery_label.setText(
            f"Battery: {info.get('battery_level', '\u2014')} "
            f"({info.get('charging', '\u2014')})"
        )
        self.temp_label.setText(f"Temp: {info.get('temperature', '\u2014')}")
        self.resolution_label.setText(
            f"Resolution: {info.get('resolution', '\u2014')}"
        )

    def update_latency(self, latency_ms: float | None) -> None:
        """Update the latency display."""
        if latency_ms is not None:
            self.latency_label.setText(f"Ping: {latency_ms:.1f} ms")
        else:
            self.latency_label.setText("Ping: Timeout")

    def reset(self) -> None:
        """Reset all labels to defaults."""
        self.model_label.setText("Model: \u2014")
        self.android_label.setText("Android: \u2014")
        self.battery_label.setText("Battery: \u2014")
        self.temp_label.setText("Temp: \u2014")
        self.resolution_label.setText("Resolution: \u2014")
        self.latency_label.setText("WiFi Latency: \u2014")
