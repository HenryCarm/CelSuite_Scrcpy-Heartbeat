"""
Collapsible log panel widget for ScrcpyUltimateLink.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.logger import get_signal_bridge


class LogPanel(QGroupBox):
    """
    A collapsible log viewer that auto-scrolls and can be connected
    to the centralized logging system.
    """

    def __init__(self, title: str = "System Logs", max_height: int = 180) -> None:
        super().__init__(title)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Log text area
        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setMaximumHeight(max_height)
        layout.addWidget(self._log_area)

        # Button bar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self._toggle_btn = QPushButton("\u25bc  Collapse")
        self._toggle_btn.setObjectName("control-btn")
        self._toggle_btn.clicked.connect(self._toggle)

        copy_btn = QPushButton("\U0001f4cb  Copy")
        copy_btn.setObjectName("control-btn")
        copy_btn.clicked.connect(self._copy_logs)

        clear_btn = QPushButton("\U0001f5d1  Clear")
        clear_btn.setObjectName("control-btn")
        clear_btn.clicked.connect(self._clear_logs)

        btn_layout.addWidget(self._toggle_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        self._collapsed = False

        # Connect to centralized logging bridge
        bridge = get_signal_bridge()
        bridge.log_message.connect(self.append)

    def append(self, message: str) -> None:
        """Append a log line and auto-scroll to bottom."""
        self._log_area.append(message)
        scrollbar = self._log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _toggle(self) -> None:
        """Toggle the log area visibility."""
        self._collapsed = not self._collapsed
        self._log_area.setVisible(not self._collapsed)
        self._toggle_btn.setText(
            "\u25b6  Expand" if self._collapsed else "\u25bc  Collapse"
        )

    def _copy_logs(self) -> None:
        """Copy all log text to the clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._log_area.toPlainText())

    def _clear_logs(self) -> None:
        """Clear the log display."""
        self._log_area.clear()
