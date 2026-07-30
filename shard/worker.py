"""Download job execution and queue management (QProcess based)."""

from __future__ import annotations

import itertools
import os
import re
from typing import Optional

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from .config import Options
from .ytdlp import POST_MARK, PROGRESS_MARK, build_args, format_command

_ids = itertools.count(1)

RE_DESTINATION = re.compile(r"^\[download\]\s+Destination:\s*(.+)$")
RE_MERGE = re.compile(r'^\[Merger\]\s+Merging formats into\s+"(.+)"$')
RE_EXTRACT = re.compile(r"^\[ExtractAudio\]\s+Destination:\s*(.+)$")
RE_ALREADY = re.compile(r"^\[download\]\s+(.+?)\s+has already been downloaded")
RE_ERROR = re.compile(r"^ERROR:\s*(.+)$")
RE_PLAYLIST_ITEM = re.compile(r"^\[download\]\s+Downloading item (\d+) of (\d+)")


def human_bytes(value: float | None) -> str:
    if not value or value <= 0:
        return "-"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    idx = 0
    size = float(value)
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    return f"{size:.1f} {units[idx]}"


def human_speed(value: float | None) -> str:
    if not value or value <= 0:
        return "-"
    return human_bytes(value) + "/s"


def human_eta(seconds: float | None) -> str:
    if seconds is None or seconds <= 0:
        return "-"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _num(token: str) -> Optional[float]:
    token = token.strip()
    if not token or token in ("NA", "None"):
        return None
    try:
        return float(token)
    except ValueError:
        return None


class DownloadJob(QObject):
    """A single yt-dlp invocation for one URL."""

    changed = Signal(object)
    logged = Signal(object, str)
    finished = Signal(object)

    def __init__(self, url: str, options: Options, binary: str):
        super().__init__()
        self.id = next(_ids)
        self.url = url
        self.options = options.clone()
        self.binary = binary

        self.status = "Queued"
        self.title = ""
        self.filename = ""
        self.percent = 0.0
        self.speed = ""
        self.eta = ""
        self.size = ""
        self.error = ""
        self.playlist_pos = ""

        self._proc: QProcess | None = None
        self._buffer = ""
        self._cancelled = False
        self._paused = False
        self._saw_error = False

    # ------------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.status in ("Starting", "Downloading", "Processing")

    @property
    def is_terminal(self) -> bool:
        return self.status in ("Done", "Error", "Cancelled")

    # ------------------------------------------------------------------
    def start(self) -> None:
        if self.is_active:
            return
        self._cancelled = False
        self._paused = False
        self._saw_error = False
        self._buffer = ""
        self.error = ""
        self.status = "Starting"
        self.changed.emit(self)

        args = build_args(self.options, self.url)

        proc = QProcess()
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        # Must start from the system environment: a bare QProcessEnvironment is
        # empty, and clearing TEMP/TMP breaks yt-dlp's PyInstaller bootstrap.
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUTF8", "1")
        proc.setProcessEnvironment(env)
        proc.readyReadStandardOutput.connect(self._on_output)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_proc_error)

        self._proc = proc
        self.logged.emit(self, "$ " + format_command(self.binary, args))
        proc.start(self.binary, args)

    def cancel(self) -> None:
        self._cancelled = True
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()
        else:
            self.status = "Cancelled"
            self.changed.emit(self)
            self.finished.emit(self)

    def pause(self) -> None:
        """yt-dlp has no true pause; stop now and resume via --continue later."""
        if not self.is_active:
            return
        self._paused = True
        if self._proc:
            self._proc.kill()

    def reset(self) -> None:
        self.status = "Queued"
        self.percent = 0.0
        self.speed = ""
        self.eta = ""
        self.error = ""
        self.changed.emit(self)

    # ------------------------------------------------------------------
    def _on_proc_error(self, err: QProcess.ProcessError) -> None:
        if err == QProcess.ProcessError.FailedToStart:
            self.status = "Error"
            self.error = f"Could not launch yt-dlp at: {self.binary}"
            self.logged.emit(self, "ERROR: " + self.error)
            self.changed.emit(self)
            self.finished.emit(self)

    def _on_output(self) -> None:
        if not self._proc:
            return
        raw = bytes(self._proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._buffer += raw.replace("\r\n", "\n").replace("\r", "\n")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._handle_line(line.rstrip())

    def _handle_line(self, line: str) -> None:
        if not line:
            return

        if line.startswith(PROGRESS_MARK):
            self._parse_progress(line)
            return

        if line.startswith(POST_MARK):
            parts = line.split("|")
            if len(parts) >= 3 and parts[2].strip() not in ("", "NA"):
                self.title = self.title or parts[2].strip()
            self.status = "Processing"
            self.speed = ""
            self.eta = ""
            self.changed.emit(self)
            return

        self.logged.emit(self, line)

        m = RE_PLAYLIST_ITEM.match(line)
        if m:
            self.playlist_pos = f"{m.group(1)}/{m.group(2)}"
            self.changed.emit(self)
            return

        for pattern in (RE_DESTINATION, RE_MERGE, RE_EXTRACT):
            m = pattern.match(line)
            if m:
                self.filename = m.group(1).strip()
                if not self.title:
                    self.title = os.path.splitext(os.path.basename(self.filename))[0]
                self.changed.emit(self)
                return

        m = RE_ALREADY.match(line)
        if m:
            self.filename = m.group(1).strip()
            if not self.title:
                self.title = os.path.splitext(os.path.basename(self.filename))[0]
            self.percent = 100.0
            self.changed.emit(self)
            return

        m = RE_ERROR.match(line)
        if m:
            self._saw_error = True
            self.error = m.group(1).strip()
            self.changed.emit(self)
            return

        if line.startswith("[Merger]") or line.startswith("[ExtractAudio]") \
                or line.startswith("[EmbedThumbnail]") or line.startswith("[Metadata]") \
                or line.startswith("[SponsorBlock]") or line.startswith("[VideoConvertor]"):
            self.status = "Processing"
            self.changed.emit(self)

    def _parse_progress(self, line: str) -> None:
        parts = line.split("|")
        if len(parts) < 7:
            return
        _, state, downloaded, total, total_est, speed, eta = parts[:7]
        title = parts[7] if len(parts) > 7 else ""

        if title.strip() and title.strip() != "NA":
            self.title = title.strip()

        got = _num(downloaded)
        tot = _num(total) or _num(total_est)
        if got is not None and tot:
            self.percent = max(0.0, min(100.0, got / tot * 100.0))
        self.size = human_bytes(tot)
        self.speed = human_speed(_num(speed))
        self.eta = human_eta(_num(eta))

        state = state.strip()
        if state == "finished":
            self.percent = 100.0
            self.speed = ""
            self.eta = ""
            self.status = "Processing"
        elif state == "downloading":
            self.status = "Downloading"
        self.changed.emit(self)

    def _on_finished(self, exit_code: int, _status) -> None:
        if self._cancelled:
            self.status = "Cancelled"
        elif self._paused:
            self.status = "Paused"
        elif exit_code == 0 and not self._saw_error:
            self.status = "Done"
            self.percent = 100.0
        elif exit_code == 0 and self._saw_error:
            # --ignore-errors keeps the exit code at 0 for skipped entries.
            self.status = "Done"
            self.percent = 100.0
        else:
            self.status = "Error"
            if not self.error:
                self.error = f"yt-dlp exited with code {exit_code}"
        self.speed = ""
        self.eta = ""
        self._proc = None
        self.changed.emit(self)
        self.finished.emit(self)


class QueueManager(QObject):
    """Holds all jobs and runs up to `concurrency` of them at once."""

    job_added = Signal(object)
    job_changed = Signal(object)
    job_logged = Signal(object, str)
    queue_idle = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.jobs: list[DownloadJob] = []
        self.concurrency = 2
        self._running = False

    # ------------------------------------------------------------------
    def add(self, url: str, options: Options, binary: str) -> DownloadJob:
        job = DownloadJob(url, options, binary)
        job.changed.connect(self.job_changed.emit)
        job.logged.connect(self.job_logged.emit)
        job.finished.connect(self._on_job_finished)
        self.jobs.append(job)
        self.job_added.emit(job)
        return job

    def remove(self, job: DownloadJob) -> None:
        if job.is_active:
            job.cancel()
        if job in self.jobs:
            self.jobs.remove(job)

    def clear_finished(self) -> None:
        self.jobs = [j for j in self.jobs if not j.is_terminal]

    # ------------------------------------------------------------------
    @property
    def active_count(self) -> int:
        return sum(1 for j in self.jobs if j.is_active)

    def start(self) -> None:
        self._running = True
        self._pump()

    def stop_all(self) -> None:
        self._running = False
        for job in self.jobs:
            if job.is_active:
                job.cancel()
            elif job.status == "Queued":
                job.status = "Cancelled"
                job.changed.emit(job)

    def pause_all(self) -> None:
        self._running = False
        for job in self.jobs:
            if job.is_active:
                job.pause()

    def _pump(self) -> None:
        if not self._running:
            return
        for job in self.jobs:
            if self.active_count >= max(1, self.concurrency):
                return
            if job.status in ("Queued", "Paused"):
                job.start()
        if self.active_count == 0:
            self._running = False
            self.queue_idle.emit()

    def _on_job_finished(self, _job: DownloadJob) -> None:
        self._pump()
