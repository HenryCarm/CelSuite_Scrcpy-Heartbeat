"""
Drag-and-drop file selection widget for ScrcpyUltimateLink.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QFrame, QLabel, QPushButton, QVBoxLayout

from src.constants import get_file_icon


class DropZone(QFrame):
    """
    A drag-and-drop zone for selecting files to transfer.

    Signals
    -------
    file_selected(path)
        Emitted when a file is selected via drag-drop or the browse dialog.
    """

    file_selected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self.setObjectName("drop-zone")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        hint_label = QLabel("Drag & Drop File Here\n\u2014 or \u2014")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setObjectName("subtitle")

        self._file_label = QLabel("")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_label.setObjectName("status")

        browse_btn = QPushButton("Browse File\u2026")
        browse_btn.setFixedWidth(180)
        browse_btn.clicked.connect(self._browse)

        layout.addWidget(hint_label)
        layout.addWidget(self._file_label)
        layout.addWidget(browse_btn, 0, Qt.AlignmentFlag.AlignCenter)

    # ── Drag & Drop ──────────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setObjectName("drop-zone-active")
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.setObjectName("drop-zone")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event) -> None:  # noqa: N802
        self.setObjectName("drop-zone")
        self.style().unpolish(self)
        self.style().polish(self)

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self._set_file(file_path)
                break

    # ── Browse ────────────────────────────────────────────────────────

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Send", "", "All Files (*)",
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str) -> None:
        name = os.path.basename(path)
        icon = get_file_icon(name)
        self._file_label.setText(f"{icon}  {name}")
        self.file_selected.emit(path)
