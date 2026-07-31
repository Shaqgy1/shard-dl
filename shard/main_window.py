"""Main application window."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QFileDialog, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QMainWindow, QMenu, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSplitter, QStatusBar,
    QSystemTrayIcon, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import APP_NAME, TAGLINE, __version__
from .config import BUILTIN_PRESETS, CONFIG_PATH, AppPrefs, Options, Settings
from .dialogs import CommandDialog, FormatsDialog
from .icons import app_icon
from .options_panel import OptionsPanel
from .theme import DEFAULT_THEME, THEMES, build_stylesheet, status_colors
from .titlebar import TitleBar, install_resize_grips, layout_resize_grips
from .win32_chrome import IS_WINDOWS, WM_NCCALCSIZE, disable_rounded_corners, filter_nc_calcsize, parse_message
from .worker import DownloadJob, QueueManager
from .ytdlp import (
    build_args, find_ffmpeg, find_ytdlp, format_command, is_bundled_ytdlp, probe_version,
)

QUEUE_COLUMNS = ["#", "Title", "Status", "Progress", "Size", "Speed", "ETA"]
URL_RE = re.compile(r"https?://\S+")
PREFS_SECTION = 9


class QueueTable(QTableWidget):
    """Queue view with a centred empty-state message."""

    def __init__(self, columns: int):
        super().__init__(0, columns)
        self.empty = QLabel(
            "Nothing queued yet.\nPaste a link above, or drop one onto the window.",
            self.viewport())
        self.empty.setObjectName("EmptyState")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.empty.setGeometry(self.viewport().rect())

    def sync_empty(self) -> None:
        self.empty.setVisible(self.rowCount() == 0)
        self.empty.raise_()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.load()
        self.prefs = self.settings.prefs
        if not self.settings.presets:
            self.settings.presets = dict(BUILTIN_PRESETS)

        self.binary = find_ytdlp(self.prefs.ytdlp_path)
        self.queue = QueueManager()
        self.queue.job_added.connect(self._on_job_added)
        self.queue.job_changed.connect(self._on_job_changed)
        self.queue.job_logged.connect(self._on_job_logged)
        self.queue.queue_idle.connect(self._on_queue_idle)

        self._bars: dict[int, QProgressBar] = {}
        self._retries: dict[int, int] = {}
        self._log_handle = None
        self._force_quit = False
        self._tray: QSystemTrayIcon | None = None
        self._clip_seen = ""
        self._clip_connected = False

        # Deliberately NOT Qt.FramelessWindowHint: on Windows that produces a
        # WS_POPUP window, which tiling window managers (komorebi, GlazeWM)
        # filter out entirely - it never appears in the layout, not even as
        # floating/ignored. Keeping the normal window style and hiding the
        # native titlebar via nativeEvent()/WM_NCCALCSIZE instead keeps the
        # window fully manageable. See win32_chrome.py.
        self._build_ui()
        self._grips = install_resize_grips(self)
        self._install_shortcuts()
        disable_rounded_corners(int(self.winId()))
        self.options_panel.load_prefs(self.prefs)
        self.options_panel.prefs_changed.connect(self._on_prefs_changed)
        self._wire_pref_buttons()
        self.apply_theme()
        self._load_startup_options()
        self._apply_window_prefs()
        self._refresh_status()
        self.table.sync_empty()

    # ================================================================ UI
    def _build_ui(self) -> None:
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setMinimumSize(1020, 620)
        screen = QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            self.resize(min(1460, int(avail.width() * 0.9)),
                        min(900, int(avail.height() * 0.9)))
        else:
            self.resize(1460, 900)
        self.setAcceptDrops(True)

        root = QWidget()
        root.setObjectName("RootFrame")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        self.title_bar = TitleBar(self)
        self.title_bar.action_triggered.connect(self._on_bar_action)
        outer.addWidget(self.title_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([780, 660])

        wrap = QWidget()
        wrap_lay = QVBoxLayout(wrap)
        wrap_lay.setContentsMargins(10, 10, 10, 6)
        wrap_lay.addWidget(splitter)
        outer.addWidget(wrap, 1)

        self.setCentralWidget(root)
        bar = QStatusBar()
        bar.setSizeGripEnabled(False)
        self.setStatusBar(bar)

    def _build_left(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(9)

        url_card = QWidget()
        url_card.setObjectName("Card")
        url_lay = QVBoxLayout(url_card)
        url_lay.setContentsMargins(13, 11, 13, 11)
        url_lay.setSpacing(8)

        head_row = QHBoxLayout()
        head = QLabel("URLS")
        head.setObjectName("SectionTitle")
        head_row.addWidget(head)
        head_row.addStretch(1)
        self.queue_count = QLabel("")
        self.queue_count.setObjectName("Hint")
        head_row.addWidget(self.queue_count)
        url_lay.addLayout(head_row)

        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText(
            "Paste one or more links, one per line - videos, playlists or channels.")
        self.url_input.setFixedHeight(72)
        url_lay.addWidget(self.url_input)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.add_btn = QPushButton("Add to queue")
        self.add_btn.setObjectName("Primary")
        self.add_btn.clicked.connect(self.add_urls)
        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("Ghost")
        paste_btn.clicked.connect(self._paste)
        self.start_btn = QPushButton("Start downloads")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self.start_queue)
        row.addWidget(self.add_btn)
        row.addWidget(paste_btn)
        row.addStretch(1)
        row.addWidget(self.start_btn)
        url_lay.addLayout(row)
        lay.addWidget(url_card)

        self.table = QueueTable(len(QUEUE_COLUMNS))
        self.table.setHorizontalHeaderLabels(QUEUE_COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(46)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in range(2, len(QUEUE_COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        for col, width in ((0, 38), (2, 104), (3, 118), (4, 90), (5, 86), (6, 58)):
            self.table.setColumnWidth(col, width)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._queue_menu)
        self.table.doubleClicked.connect(self._open_selected_file)
        lay.addWidget(self.table, 3)

        log_head = QHBoxLayout()
        lbl = QLabel("LOG")
        lbl.setObjectName("SectionTitle")
        log_head.addWidget(lbl)
        log_head.addStretch(1)
        clear_log = QPushButton("Clear")
        clear_log.setObjectName("Ghost")
        clear_log.clicked.connect(lambda: self.log.clear())
        log_head.addWidget(clear_log)
        lay.addLayout(log_head)

        self.log = QPlainTextEdit()
        self.log.setObjectName("LogView")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(self.prefs.log_max_lines)
        lay.addWidget(self.log, 2)
        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(6, 0, 0, 0)
        lay.setSpacing(9)

        preset_card = QWidget()
        preset_card.setObjectName("Card")
        pl = QHBoxLayout(preset_card)
        pl.setContentsMargins(13, 9, 13, 9)
        pl.setSpacing(8)
        head = QLabel("PRESET")
        head.setObjectName("SectionTitle")
        pl.addWidget(head)
        self.preset_box = QComboBox()
        self.preset_box.activated.connect(self._apply_preset)
        pl.addWidget(self.preset_box, 1)
        for text, slot, style in (("Save as...", self._save_preset, "Ghost"),
                                  ("Startup", self._set_default_preset, "Ghost"),
                                  ("Delete", self._delete_preset, "Danger")):
            btn = QPushButton(text)
            btn.setObjectName(style)
            btn.clicked.connect(slot)
            pl.addWidget(btn)
        lay.addWidget(preset_card)

        self.default_label = QLabel()
        self.default_label.setObjectName("Hint")
        self.default_label.setWordWrap(True)
        lay.addWidget(self.default_label)

        self.options_panel = OptionsPanel()
        lay.addWidget(self.options_panel, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        note = QLabel("Settings save automatically on exit.")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        save_btn = QPushButton("Save as my defaults")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self.save_defaults)
        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("Ghost")
        reset_btn.clicked.connect(self.reset_defaults)
        footer.addWidget(note, 1)
        footer.addWidget(reset_btn)
        footer.addWidget(save_btn)
        lay.addLayout(footer)
        return panel

    # ============================================================ chrome
    def _on_bar_action(self, key: str) -> None:
        handlers = {
            "add": self.add_urls,
            "start": self.start_queue,
            "pause": self.queue.pause_all,
            "stop": self.queue.stop_all,
            "formats": self.show_formats,
            "command": self.show_command,
            "folder": self.open_output_folder,
            "clear": self.clear_finished,
            "prefs": lambda: self.options_panel.setCurrentIndex(PREFS_SECTION),
            "minimize": self.showMinimized,
            "maximize": self._toggle_maximize,
            "close": self.close,
        }
        handler = handlers.get(key)
        if handler is not None:
            handler()

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _install_shortcuts(self) -> None:
        binds = [
            ("Ctrl+Return", self.add_urls), ("Ctrl+Enter", self.add_urls),
            ("Ctrl+D", self.start_queue),
            ("Ctrl+L", lambda: (self.url_input.setFocus(), self.url_input.selectAll())),
            ("Ctrl+I", self.show_formats), ("Ctrl+K", self.show_command),
            ("Ctrl+O", self.open_output_folder),
            ("Ctrl+,", lambda: self.options_panel.setCurrentIndex(PREFS_SECTION)),
            ("Ctrl+Q", self._quit_from_tray),
            ("Delete", self._remove_selected),
        ]
        for sequence, slot in binds:
            QShortcut(QKeySequence(sequence), self, activated=slot)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        layout_resize_grips(self._grips, self.width(), self.height())

    def nativeEvent(self, eventType, message):
        if IS_WINDOWS and eventType == b"windows_generic_MSG":
            msg = parse_message(message)
            if msg is not None and msg.message == WM_NCCALCSIZE and msg.wParam:
                # Claim the whole window as client area - no native titlebar
                # gets drawn, but the underlying window style stays a normal
                # WS_OVERLAPPEDWINDOW, so komorebi still sees a manageable
                # window.
                filter_nc_calcsize(self.isMaximized(), msg.lParam)
                return True, 0
        return super().nativeEvent(eventType, message)

    # ============================================================ theming
    def apply_theme(self) -> None:
        palette = THEMES.get(self.prefs.theme) or THEMES[DEFAULT_THEME]
        self.palette_obj = palette
        self.status_colors = status_colors(palette)

        app = QApplication.instance()
        app.setStyleSheet(build_stylesheet(
            palette,
            font=self.prefs.font_family,
            font_size=self.prefs.font_size,
            density=self.prefs.density,
            radius=self.prefs.corner_radius,
            uppercase_tabs=self.prefs.uppercase_nav,
        ))
        app.setFont(QFont(self.prefs.font_family, max(8, self.prefs.font_size - 4)))

        window_icon = app_icon(palette.accent, palette.accent2, palette.bg)
        self.setWindowIcon(window_icon)
        self.title_bar.retheme(palette)
        self._sync_tray(window_icon)
        for job in self.queue.jobs:
            self._on_job_changed(job)

    def _sync_tray(self, window_icon) -> None:
        wanted = self.prefs.minimize_to_tray or self.prefs.notify_on_complete
        if wanted and self._tray is None and QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = QSystemTrayIcon(self)
            menu = QMenu()
            menu.addAction("Show window", self._restore_from_tray)
            menu.addAction("Start queue", self.start_queue)
            menu.addSeparator()
            menu.addAction("Quit", self._quit_from_tray)
            self._tray.setContextMenu(menu)
            self._tray.activated.connect(
                lambda reason: self._restore_from_tray()
                if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        if self._tray is not None:
            self._tray.setIcon(window_icon)
            self._tray.setToolTip(f"{APP_NAME} - {TAGLINE}")
            self._tray.setVisible(wanted)

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._force_quit = True
        self.close()
        QApplication.instance().quit()

    def _apply_window_prefs(self) -> None:
        flag = Qt.WindowType.WindowStaysOnTopHint
        if bool(self.windowFlags() & flag) != self.prefs.always_on_top:
            self.setWindowFlag(flag, self.prefs.always_on_top)
            if self.isVisible():
                self.show()
        if self.prefs.remember_window and self.settings.window_geometry:
            try:
                from PySide6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromBase64(
                    self.settings.window_geometry.encode("ascii")))
            except (ValueError, TypeError):
                pass
        self.log.setMaximumBlockCount(self.prefs.log_max_lines)
        self._sync_clipboard_watch()

    def _on_prefs_changed(self) -> None:
        new = self.options_panel.read_prefs()
        theme_changed = (
            new.theme != self.prefs.theme or new.font_family != self.prefs.font_family
            or new.font_size != self.prefs.font_size or new.density != self.prefs.density
            or new.corner_radius != self.prefs.corner_radius
            or new.uppercase_nav != self.prefs.uppercase_nav
        )
        binary_changed = new.ytdlp_path != self.prefs.ytdlp_path
        self.prefs = new
        self.settings.prefs = new
        if theme_changed:
            self.apply_theme()
            self.options_panel.refresh_labels()
        if binary_changed:
            self.binary = find_ytdlp(self.prefs.ytdlp_path)
            self._refresh_status()
        self._apply_window_prefs()

    # ============================================================ clipboard
    def _sync_clipboard_watch(self) -> None:
        if self.prefs.clipboard_watch == self._clip_connected:
            return
        clipboard = QApplication.clipboard()
        if self.prefs.clipboard_watch:
            clipboard.dataChanged.connect(self._on_clipboard)
        else:
            clipboard.dataChanged.disconnect(self._on_clipboard)
        self._clip_connected = self.prefs.clipboard_watch

    def _on_clipboard(self) -> None:
        """Only ever reacts to plain http(s) links the user copied."""
        if not self.prefs.clipboard_watch or not self.binary:
            return
        text = QApplication.clipboard().text().strip()
        if not text or text == self._clip_seen or len(text) > 2000:
            return
        urls = URL_RE.findall(text)
        if not urls:
            return
        self._clip_seen = text
        added = self._enqueue(urls)
        if added:
            self.statusBar().showMessage(f"Clipboard: queued {added} link(s)", 5000)

    # ============================================================ actions
    def current_options(self) -> Options:
        return self.options_panel.read_options()

    def _enqueue(self, urls: list[str]) -> int:
        opt = self.current_options()
        existing = {j.url for j in self.queue.jobs} if self.prefs.skip_duplicates else set()
        added = 0
        for url in urls:
            if url in existing:
                continue
            self.queue.add(url, opt, self.binary)
            existing.add(url)
            added += 1
        if added and self.prefs.auto_start_on_add:
            self.start_queue(silent=True)
        return added

    def add_urls(self) -> None:
        if not self.binary:
            QMessageBox.warning(self, APP_NAME, "yt-dlp was not found on this system.")
            return
        urls = [ln.strip() for ln in self.url_input.toPlainText().splitlines() if ln.strip()]
        if not urls:
            QMessageBox.information(self, APP_NAME, "Paste at least one URL first.")
            return
        added = self._enqueue(urls)
        self.url_input.clear()
        skipped = len(urls) - added
        msg = f"Added {added} item(s) to the queue."
        if skipped:
            msg += f"  {skipped} duplicate(s) skipped."
        self.statusBar().showMessage(msg, 5000)

    def start_queue(self, silent: bool = False) -> None:
        opt = self.current_options()
        self.queue.concurrency = opt.concurrent_downloads
        pending = [j for j in self.queue.jobs if j.status in ("Queued", "Paused")]
        if not pending:
            if not silent:
                QMessageBox.information(self, APP_NAME, "Nothing in the queue to download.")
            return
        if opt.output_dir.strip():
            try:
                Path(opt.output_dir).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                QMessageBox.warning(
                    self, APP_NAME,
                    f"Could not create the download folder:\n{opt.output_dir}\n\n{exc}")
                return
        # Options are captured per-job at queue time, so a setting changed
        # after "Add to queue" but before "Start" would otherwise be
        # silently ignored. Refresh every not-yet-started job to whatever
        # is currently in the panel - "Start" should mean "start with what
        # I've got configured now."
        for job in pending:
            job.options = opt.clone()
        self.queue.start()

    def clear_finished(self) -> None:
        self.queue.clear_finished()
        self._rebuild_table()

    def open_output_folder(self) -> None:
        folder = self.current_options().output_dir.strip()
        if not folder:
            return
        Path(folder).mkdir(parents=True, exist_ok=True)
        self._open_path(folder)

    @staticmethod
    def _open_path(path: str) -> None:
        try:
            os.startfile(path)  # noqa: S606 - intentional shell-open on Windows
        except OSError:
            subprocess.Popen(["explorer", path])

    def show_formats(self) -> None:
        url = self._first_url()
        if not url:
            return
        dlg = FormatsDialog(url, self.current_options(), self.binary, self)
        if dlg.exec() and dlg.selected_format:
            self.options_panel.custom_format.setText(dlg.selected_format)
            self.options_panel.setCurrentIndex(0)

    def show_command(self) -> None:
        url = self._first_url() or "<URL>"
        args = build_args(self.current_options(), url, for_display=True)
        CommandDialog(format_command(self.binary or "yt-dlp", args), self).exec()

    def _first_url(self) -> str:
        urls = [ln.strip() for ln in self.url_input.toPlainText().splitlines() if ln.strip()]
        if urls:
            return urls[0]
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if rows and rows[0].row() < len(self.queue.jobs):
            return self.queue.jobs[rows[0].row()].url
        if self.queue.jobs:
            return self.queue.jobs[0].url
        QMessageBox.information(self, APP_NAME, "Enter a URL first.")
        return ""

    def _paste(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            existing = self.url_input.toPlainText()
            self.url_input.setPlainText(f"{existing}\n{text}".strip() if existing else text)

    def _remove_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        jobs = [self.queue.jobs[r.row()] for r in rows if r.row() < len(self.queue.jobs)]
        for job in jobs:
            self.queue.remove(job)
        if jobs:
            self._rebuild_table()

    # ============================================================ prefs UI
    def _wire_pref_buttons(self) -> None:
        p = self.options_panel
        p.btn_update_ytdlp.clicked.connect(self.update_ytdlp)
        p.btn_open_settings.clicked.connect(
            lambda: self._open_path(str(CONFIG_PATH.parent)))
        p.btn_export.clicked.connect(self.export_settings)
        p.btn_import.clicked.connect(self.import_settings)
        p.btn_reset_all.clicked.connect(self.reset_everything)

    def update_ytdlp(self) -> None:
        if not self.binary:
            return
        self.log.appendPlainText(f"[updater] running {self.binary} -U")
        try:
            out = subprocess.run(
                [self.binary, "-U"], capture_output=True, text=True, timeout=180,
                creationflags=0x08000000,
            )
            for line in (out.stdout + out.stderr).splitlines():
                if line.strip():
                    self.log.appendPlainText(f"[updater] {line}")
        except (OSError, subprocess.SubprocessError) as exc:
            self.log.appendPlainText(f"[updater] failed: {exc}")
        self._refresh_status()

    def export_settings(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export settings", "shard-settings.json", "JSON (*.json)")
        if not path:
            return
        self.settings.options = self.current_options()
        self.settings.prefs = self.options_panel.read_prefs()
        try:
            self.settings.save(Path(path))
            self.statusBar().showMessage(f"Exported to {path}", 6000)
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not export:\n{exc}")

    def import_settings(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import settings", "", "JSON (*.json)")
        if not path:
            return
        try:
            json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, APP_NAME, f"Not a valid settings file:\n{exc}")
            return
        imported = Settings.load(Path(path))
        self.settings.options = imported.options
        self.settings.prefs = imported.prefs
        self.settings.presets = imported.presets or self.settings.presets
        self.settings.default_preset = imported.default_preset
        self.prefs = imported.prefs
        self.options_panel.load_options(imported.options)
        self.options_panel.load_prefs(imported.prefs)
        self.apply_theme()
        self._refresh_presets()
        self.statusBar().showMessage("Settings imported.", 6000)

    def reset_everything(self) -> None:
        if QMessageBox.question(
                self, APP_NAME,
                "Reset every download option AND every preference to defaults?\n"
                "Saved presets are kept.") != QMessageBox.StandardButton.Yes:
            return
        self.prefs = AppPrefs()
        self.settings.prefs = self.prefs
        self.options_panel.load_options(Options())
        self.options_panel.load_prefs(self.prefs)
        self.apply_theme()

    # ============================================================ presets
    def _load_startup_options(self) -> None:
        opt = self.settings.options
        if self.settings.default_preset:
            loaded = self.settings.load_preset(self.settings.default_preset)
            if loaded:
                loaded.output_dir = opt.output_dir or loaded.output_dir
                opt = loaded
        self.options_panel.load_options(opt)
        self._refresh_presets()

    def _refresh_presets(self) -> None:
        self.preset_box.blockSignals(True)
        self.preset_box.clear()
        self.preset_box.addItem("- Select a preset -", "")
        for name in sorted(self.settings.presets):
            label = f"{name}  *" if name == self.settings.default_preset else name
            self.preset_box.addItem(label, name)
        self.preset_box.blockSignals(False)
        self.default_label.setText(
            f"Startup preset: <b>{self.settings.default_preset}</b>"
            if self.settings.default_preset else
            "No startup preset - your saved settings are used.")

    def _apply_preset(self) -> None:
        name = self.preset_box.currentData()
        if not name:
            return
        loaded = self.settings.load_preset(name)
        if not loaded:
            return
        loaded.output_dir = self.current_options().output_dir
        self.options_panel.load_options(loaded)
        self.statusBar().showMessage(f"Applied preset: {name}", 4000)

    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save preset", "Preset name:")
        if not ok or not name.strip():
            return
        self.settings.save_preset(name.strip(), self.current_options())
        self.settings.save()
        self._refresh_presets()
        self.statusBar().showMessage(f"Saved preset: {name.strip()}", 4000)

    def _delete_preset(self) -> None:
        name = self.preset_box.currentData()
        if not name:
            return
        if QMessageBox.question(self, "Delete preset", f"Delete the preset '{name}'?") \
                == QMessageBox.StandardButton.Yes:
            self.settings.delete_preset(name)
            self.settings.save()
            self._refresh_presets()

    def _set_default_preset(self) -> None:
        self.settings.default_preset = self.preset_box.currentData() or ""
        self.settings.save()
        self._refresh_presets()

    def save_defaults(self) -> None:
        self.settings.options = self.current_options()
        self.settings.prefs = self.options_panel.read_prefs()
        self.settings.save()
        self.statusBar().showMessage(
            f"Defaults saved. Downloads go to {self.settings.options.output_dir}", 6000)

    def reset_defaults(self) -> None:
        if QMessageBox.question(self, "Reset", "Reset every download option?") \
                == QMessageBox.StandardButton.Yes:
            self.options_panel.load_options(Options())

    # ============================================================ status
    def _refresh_status(self) -> None:
        if not self.binary:
            self.title_bar.set_status("yt-dlp NOT FOUND")
            self.statusBar().showMessage(
                "yt-dlp was not found. Install it with:  winget install yt-dlp.yt-dlp")
            for key in ("start", "add"):
                self.title_bar.buttons[key].setEnabled(False)
            self.start_btn.setEnabled(False)
            self.add_btn.setEnabled(False)
            return
        self.start_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        for key in ("start", "add"):
            self.title_bar.buttons[key].setEnabled(True)
        version = probe_version(self.binary)
        label = f"yt-dlp {version}" if version else "yt-dlp ready"
        bundled = is_bundled_ytdlp(self.binary)
        if bundled:
            label += "  (bundled)"
        self.title_bar.set_status(label)
        ffmpeg = self.prefs.ffmpeg_path.strip() or find_ffmpeg()
        parts = [f"yt-dlp: {self.binary}"]
        if bundled:
            parts.append("using the bundled copy - an installed yt-dlp could not be found or "
                         "reached; install one with 'winget install yt-dlp.yt-dlp' to stay updated")
        parts.append(f"ffmpeg: {ffmpeg}" if ffmpeg else "ffmpeg: NOT FOUND (merging will fail)")
        self.statusBar().showMessage("     |     ".join(parts))

    def _refresh_counts(self) -> None:
        total = len(self.queue.jobs)
        if not total:
            self.queue_count.setText("")
        else:
            done = sum(1 for j in self.queue.jobs if j.status == "Done")
            self.queue_count.setText(
                f"{done}/{total} done   -   {self.queue.active_count} running")
        self.table.sync_empty()

    # ============================================================ queue view
    def _on_job_added(self, job: DownloadJob) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        bar = QProgressBar()
        bar.setTextVisible(True)
        bar.setValue(0)
        self._bars[job.id] = bar
        self.table.setCellWidget(row, 3, bar)
        self._paint_row(row, job)
        self._refresh_counts()

    def _rebuild_table(self) -> None:
        self.table.setRowCount(0)
        self._bars.clear()
        for job in self.queue.jobs:
            self._on_job_added(job)
        self._refresh_counts()

    def _row_for(self, job: DownloadJob) -> int:
        try:
            return self.queue.jobs.index(job)
        except ValueError:
            return -1

    def _paint_row(self, row: int, job: DownloadJob) -> None:
        title = job.title or job.url
        if job.playlist_pos:
            title = f"[{job.playlist_pos}] {title}"
        cells = [str(row + 1), title, job.status, None,
                 job.size or "-", job.speed or "-", job.eta or "-"]
        for col, value in enumerate(cells):
            if col == 3:
                continue
            item = self.table.item(row, col)
            if item is None:
                item = QTableWidgetItem()
                if col in (0, 2, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
            item.setText(str(value))
            if col == 2:
                item.setForeground(QColor(self.status_colors.get(job.status, "#888888")))
            if col == 1 and job.error:
                item.setToolTip(job.error)

        bar = self._bars.get(job.id)
        if bar is not None:
            bar.setValue(int(job.percent))
            bar.setFormat({"Error": "failed", "Processing": "processing...",
                           "Cancelled": "cancelled"}.get(job.status, "%p%"))

    def _on_job_changed(self, job: DownloadJob) -> None:
        row = self._row_for(job)
        if row >= 0:
            self._paint_row(row, job)
        self._refresh_counts()
        if job.status == "Error" and self.prefs.auto_retry_failed:
            used = self._retries.get(job.id, 0)
            if used < self.prefs.auto_retry_failed:
                self._retries[job.id] = used + 1
                self.log.appendPlainText(
                    f"[retry] {job.title or job.url} - attempt {used + 1}"
                    f"/{self.prefs.auto_retry_failed}")
                QTimer.singleShot(2000, lambda j=job: self._auto_retry(j))

    def _auto_retry(self, job: DownloadJob) -> None:
        job.options = self.current_options().clone()
        job.reset()
        self.queue.start()

    def _on_job_logged(self, job: DownloadJob, line: str) -> None:
        tag = (job.title or job.url)[:42]
        text = f"[{tag}] {line}"
        self.log.appendPlainText(text)
        if self.prefs.log_to_file and self.prefs.log_file.strip():
            try:
                if self._log_handle is None:
                    self._log_handle = open(self.prefs.log_file.strip(), "a",
                                            encoding="utf-8", buffering=1)
                self._log_handle.write(text + "\n")
            except OSError:
                self.prefs.log_to_file = False

    def _on_queue_idle(self) -> None:
        done = sum(1 for j in self.queue.jobs if j.status == "Done")
        failed = sum(1 for j in self.queue.jobs if j.status == "Error")
        msg = f"Queue finished - {done} completed"
        if failed:
            msg += f", {failed} failed"
        self.statusBar().showMessage(msg, 10000)
        self.log.appendPlainText(f"[queue] {msg}")

        if self.prefs.sound_on_complete:
            QApplication.beep()
        if self.prefs.notify_on_complete and self._tray is not None and self._tray.isVisible():
            self._tray.showMessage(APP_NAME, msg, QSystemTrayIcon.MessageIcon.Information, 6000)
        if self.prefs.open_folder_when_done and done:
            self.open_output_folder()
        if self.prefs.auto_clear_completed:
            self.clear_finished()
        if self.prefs.shutdown_when_done and done:
            self._schedule_shutdown()

    def _schedule_shutdown(self) -> None:
        """Opt-in only. Gives a 60s window and tells the user how to abort."""
        try:
            subprocess.run(["shutdown", "/s", "/t", "60", "/c",
                            f"{APP_NAME}: queue finished."],
                           creationflags=0x08000000, check=False)
        except OSError as exc:
            self.log.appendPlainText(f"[shutdown] could not schedule: {exc}")
            return
        self.log.appendPlainText("[shutdown] PC shuts down in 60s - run 'shutdown /a' to cancel.")
        QMessageBox.warning(
            self, APP_NAME,
            "The queue finished and 'shut down when done' is enabled.\n\n"
            "This PC will shut down in 60 seconds.\n"
            "Run  shutdown /a  in a terminal to cancel it.")

    def _open_selected_file(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows or rows[0].row() >= len(self.queue.jobs):
            return
        job = self.queue.jobs[rows[0].row()]
        if job.filename and Path(job.filename).exists():
            self._open_path(job.filename)

    def _queue_menu(self, pos) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        jobs = [self.queue.jobs[r.row()] for r in rows if r.row() < len(self.queue.jobs)]
        if not jobs:
            return

        menu = QMenu(self)
        act_start = menu.addAction("Start now")
        act_cancel = menu.addAction("Cancel")
        act_retry = menu.addAction("Retry")
        menu.addSeparator()
        act_open = menu.addAction("Open file")
        act_folder = menu.addAction("Open containing folder")
        act_copy = menu.addAction("Copy URL")
        menu.addSeparator()
        act_remove = menu.addAction("Remove from queue")

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_start:
            opt = self.current_options()
            self.queue.concurrency = opt.concurrent_downloads
            self.queue._running = True
            for job in jobs:
                job.options = opt.clone()
                job.start()
        elif chosen == act_cancel:
            for job in jobs:
                job.cancel()
        elif chosen == act_retry:
            opt = self.current_options()
            for job in jobs:
                self._retries.pop(job.id, None)
                job.options = opt.clone()
                job.reset()
            self.queue.start()
        elif chosen == act_open:
            if jobs[0].filename and Path(jobs[0].filename).exists():
                self._open_path(jobs[0].filename)
        elif chosen == act_folder:
            target = jobs[0].filename
            folder = str(Path(target).parent) if target else self.current_options().output_dir
            if folder and Path(folder).exists():
                self._open_path(folder)
        elif chosen == act_copy:
            QApplication.clipboard().setText("\n".join(j.url for j in jobs))
        elif chosen == act_remove:
            for job in jobs:
                self.queue.remove(job)
            self._rebuild_table()

    # ============================================================ events
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText() or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        md = event.mimeData()
        text = ""
        if md.hasUrls():
            text = "\n".join(u.toString() for u in md.urls())
        elif md.hasText():
            text = md.text()
        if text:
            existing = self.url_input.toPlainText()
            self.url_input.setPlainText(f"{existing}\n{text}".strip() if existing else text)
        event.acceptProposedAction()

    def changeEvent(self, event) -> None:
        if event.type() == event.Type.WindowStateChange:
            self.title_bar.set_maximized(self.isMaximized())
            self.title_bar.retheme(getattr(self, "palette_obj", None)
                                   or THEMES[DEFAULT_THEME])
            if (self.isMinimized() and self.prefs.minimize_to_tray
                    and self._tray is not None and self._tray.isVisible()):
                QTimer.singleShot(0, self.hide)
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        if (not self._force_quit and self.prefs.minimize_to_tray
                and self._tray is not None and self._tray.isVisible()):
            event.ignore()
            self.hide()
            return

        active = [j for j in self.queue.jobs if j.is_active]
        if active and self.prefs.confirm_on_quit:
            reply = QMessageBox.question(
                self, APP_NAME,
                f"{len(active)} download(s) are still running. Stop them and quit?")
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.queue.stop_all()

        self.settings.options = self.current_options()
        self.settings.prefs = self.options_panel.read_prefs()
        if self.prefs.remember_window:
            self.settings.window_geometry = bytes(
                self.saveGeometry().toBase64()).decode("ascii")
        try:
            self.settings.save()
        except OSError:
            pass
        if self._log_handle:
            self._log_handle.close()
        if self._tray:
            self._tray.hide()
        event.accept()
        QApplication.instance().quit()
