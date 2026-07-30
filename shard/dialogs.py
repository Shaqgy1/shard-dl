"""Auxiliary dialogs: format explorer and command preview."""

from __future__ import annotations

import json

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .config import Options
from .worker import human_bytes
from .ytdlp import build_probe_args


class FormatsDialog(QDialog):
    """Probes a URL with -J and lists every available format."""

    COLUMNS = ["ID", "Ext", "Resolution", "FPS", "Video codec",
               "Audio codec", "Bitrate", "Size", "Note"]

    def __init__(self, url: str, options: Options, binary: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Available formats")
        self.resize(940, 560)
        self.selected_format = ""
        self._raw = b""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        self.heading = QLabel("Fetching format list...")
        self.heading.setWordWrap(True)
        lay.addWidget(self.heading)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            len(self.COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._use_selected)
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        hint = QLabel("Double-click a row (or use the button) to copy its ID into the "
                      "custom format field. Combine video+audio with <code>136+140</code>.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        row.addWidget(hint, 1)
        self.use_btn = QPushButton("Use this format")
        self.use_btn.setObjectName("Primary")
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self._use_selected)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        row.addWidget(self.use_btn)
        row.addWidget(close_btn)
        lay.addLayout(row)

        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.proc.readyReadStandardOutput.connect(self._collect)
        self.proc.finished.connect(self._done)
        self.proc.start(binary, build_probe_args(options, url))

    # ------------------------------------------------------------------
    def _collect(self) -> None:
        self._raw += bytes(self.proc.readAllStandardOutput())

    def _done(self, exit_code: int, _status) -> None:
        if exit_code != 0 or not self._raw.strip():
            err = bytes(self.proc.readAllStandardError()).decode("utf-8", "replace")
            self.heading.setText(
                f"<b style='color:#ff5d5d'>Could not read formats.</b><br>"
                f"<span style='font-size:11px'>{err.strip()[:600] or 'yt-dlp returned no data.'}</span>")
            return
        try:
            info = json.loads(self._raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            self.heading.setText("<b style='color:#ff5d5d'>Could not parse yt-dlp output.</b>")
            return

        if info.get("_type") == "playlist" and info.get("entries"):
            info = info["entries"][0] or {}

        title = info.get("title", "(unknown title)")
        uploader = info.get("uploader", "")
        duration = info.get("duration")
        bits = [f"<b>{title}</b>"]
        if uploader:
            bits.append(uploader)
        if duration:
            mins, secs = divmod(int(duration), 60)
            bits.append(f"{mins}:{secs:02d}")
        self.heading.setText("  -  ".join(bits))

        formats = info.get("formats") or []
        self.table.setRowCount(0)
        for fmt in formats:
            self._add_row(fmt)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            len(self.COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)
        self.table.selectionModel().selectionChanged.connect(
            lambda: self.use_btn.setEnabled(bool(self.table.selectedItems())))

    def _add_row(self, fmt: dict) -> None:
        vcodec = fmt.get("vcodec") or "none"
        acodec = fmt.get("acodec") or "none"
        height = fmt.get("height")
        width = fmt.get("width")
        if height and width:
            res = f"{width}x{height}"
        elif vcodec == "none":
            res = "audio only"
        else:
            res = fmt.get("resolution") or "-"

        tbr = fmt.get("tbr")
        size = fmt.get("filesize") or fmt.get("filesize_approx")

        values = [
            str(fmt.get("format_id", "")),
            str(fmt.get("ext", "")),
            res,
            str(int(fmt["fps"])) if fmt.get("fps") else "-",
            vcodec.split(".")[0] if vcodec != "none" else "-",
            acodec.split(".")[0] if acodec != "none" else "-",
            f"{tbr:.0f}k" if tbr else "-",
            human_bytes(size),
            fmt.get("format_note", "") or "",
        ]
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col in (3, 6, 7):
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, col, item)

    def _use_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return
        item = self.table.item(rows[0].row(), 0)
        if item:
            self.selected_format = item.text()
            self.accept()


class CommandDialog(QDialog):
    """Shows the exact command line the app will run."""

    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command preview")
        self.resize(820, 320)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        label = QLabel("This is exactly what Shard will execute:")
        label.setObjectName("Hint")
        lay.addWidget(label)

        view = QPlainTextEdit(command)
        view.setObjectName("LogView")
        view.setReadOnly(True)
        view.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        lay.addWidget(view, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        copy_btn = QPushButton("Copy to clipboard")
        copy_btn.setObjectName("Primary")

        def do_copy() -> None:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(command)
            copy_btn.setText("Copied")

        copy_btn.clicked.connect(do_copy)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row.addWidget(copy_btn)
        row.addWidget(close_btn)
        lay.addLayout(row)
