"""The sectioned options panel: every yt-dlp flag plus app preferences."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget, QVBoxLayout,
    QWidget,
)

from .config import AppPrefs, Options
from .theme import DENSITY, FONT_CHOICES, THEME_ORDER, THEMES
from .ytdlp import SPONSORBLOCK_CATEGORIES

QUALITIES = [
    ("Best available", "best"), ("4320p (8K)", "4320"), ("2160p (4K)", "2160"),
    ("1440p (2K)", "1440"), ("1080p (Full HD)", "1080"), ("720p (HD)", "720"),
    ("480p", "480"), ("360p", "360"), ("240p", "240"), ("144p", "144"),
    ("Worst available", "worst"),
]
VIDEO_CODECS = [
    ("Any (best available)", "any"), ("H.264 / AVC  - most compatible", "avc1"),
    ("H.265 / HEVC - efficient", "hevc"), ("VP9 - YouTube native", "vp9"),
    ("AV1 - newest, smallest", "av1"),
]
AUDIO_FORMATS = [
    ("Best (no re-encode)", "best"), ("MP3", "mp3"), ("M4A / AAC", "m4a"),
    ("Opus", "opus"), ("FLAC (lossless)", "flac"), ("ALAC (lossless)", "alac"),
    ("WAV (uncompressed)", "wav"), ("Vorbis", "vorbis"), ("AAC", "aac"),
]
AUDIO_QUALITIES = [
    ("Best VBR (0)", "0"), ("High VBR (2)", "2"), ("Medium VBR (5)", "5"),
    ("Low VBR (9)", "9"), ("320 kbps CBR", "320K"), ("256 kbps CBR", "256K"),
    ("192 kbps CBR", "192K"), ("128 kbps CBR", "128K"), ("96 kbps CBR", "96K"),
]
CONTAINERS = [
    ("MP4", "mp4"), ("MKV (most flexible)", "mkv"), ("WebM", "webm"),
    ("MOV", "mov"), ("Leave as-is", "default"),
]
BROWSERS = ["chrome", "firefox", "edge", "brave", "opera", "vivaldi", "chromium", "safari", "whale"]

TEMPLATE_PRESETS = [
    ("Title [id].ext", "%(title)s [%(id)s].%(ext)s"),
    ("Title.ext", "%(title)s.%(ext)s"),
    ("Uploader / Title.ext", "%(uploader)s/%(title)s.%(ext)s"),
    ("Playlist / 01 - Title.ext", "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s"),
    ("Date - Title.ext", "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s"),
    ("Uploader / Date - Title [id].ext",
     "%(uploader)s/%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s"),
]


class PathEdit(QWidget):
    """A line edit paired with a browse button."""

    def __init__(self, mode: str = "dir", caption: str = "Select", filt: str = ""):
        super().__init__()
        self.mode, self.caption, self.filt = mode, caption, filt
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.edit = QLineEdit()
        btn = QPushButton("Browse")
        btn.setObjectName("Ghost")
        btn.setFixedWidth(78)
        btn.clicked.connect(self._browse)
        lay.addWidget(self.edit, 1)
        lay.addWidget(btn)

    def _browse(self) -> None:
        current = self.edit.text().strip()
        if self.mode == "dir":
            path = QFileDialog.getExistingDirectory(self, self.caption, current)
        elif self.mode == "save":
            path, _ = QFileDialog.getSaveFileName(self, self.caption, current, self.filt)
        else:
            path, _ = QFileDialog.getOpenFileName(self, self.caption, current, self.filt)
        if path:
            self.edit.setText(path.replace("/", "\\"))


def _combo(items: list[tuple[str, str]] | list[str]) -> QComboBox:
    box = QComboBox()
    for item in items:
        if isinstance(item, tuple):
            box.addItem(item[0], item[1])
        else:
            box.addItem(item, item)
    # Long option labels must not force the whole panel wider than its pane.
    box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    box.setMinimumContentsLength(12)
    box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return box


def _page() -> tuple[QScrollArea, QVBoxLayout]:
    area = QScrollArea()
    area.setWidgetResizable(True)
    # Never scroll sideways - the content must compress to the pane instead.
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    inner = QWidget()
    inner.setMinimumWidth(0)
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(4, 2, 10, 10)
    lay.setSpacing(12)
    area.setWidget(inner)
    return area, lay


def _group(title: str, rows: list[tuple[str, QWidget]]) -> QGroupBox:
    box = QGroupBox(title)
    form = QFormLayout(box)
    form.setSpacing(9)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    # When the pane is narrow, stack the label above its field rather than clip.
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    for label, widget in rows:
        if label:
            form.addRow(label, widget)
        else:
            form.addRow(widget)
    return box


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Hint")
    label.setWordWrap(True)
    return label


def _checks(items: list[tuple[str, str]], columns: int = 2) -> tuple[QWidget, dict]:
    holder = QWidget()
    grid = QGridLayout(holder)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(6)
    widgets = {}
    for i, (key, label) in enumerate(items):
        cb = QCheckBox(label)
        widgets[key] = cb
        grid.addWidget(cb, i // columns, i % columns)
    return holder, widgets


class SectionPanel(QWidget):
    """A numbered sidebar nav driving a stack of pages."""

    def __init__(self) -> None:
        super().__init__()
        self._titles: list[str] = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFixedWidth(140)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stack = QStackedWidget()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

        lay.addWidget(self.nav)
        lay.addWidget(self.stack, 1)

    def addTab(self, widget: QWidget, title: str) -> None:  # noqa: N802 - Qt-style name
        index = len(self._titles)
        self._titles.append(title)
        item = QListWidgetItem(f"{index + 1:02d}   {title}")
        self.nav.addItem(item)
        self.stack.addWidget(widget)
        if index == 0:
            self.nav.setCurrentRow(0)

    def count(self) -> int:
        return len(self._titles)

    def tabText(self, index: int) -> str:  # noqa: N802 - Qt-style name
        return self._titles[index] if 0 <= index < len(self._titles) else ""

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802 - Qt-style name
        if 0 <= index < len(self._titles):
            self.nav.setCurrentRow(index)

    def currentIndex(self) -> int:  # noqa: N802 - Qt-style name
        return self.nav.currentRow()

    def refresh_labels(self) -> None:
        for i, title in enumerate(self._titles):
            self.nav.item(i).setText(f"{i + 1:02d}   {title}")


class OptionsPanel(SectionPanel):
    """Binds every Options field and every AppPrefs field to a widget."""

    changed = Signal()
    prefs_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._binds: list[tuple[str, QWidget]] = []
        self._pref_binds: list[tuple[str, QWidget]] = []
        self._build_format()
        self._build_audio()
        self._build_subs()
        self._build_metadata()
        self._build_output()
        self._build_playlist()
        self._build_network()
        self._build_access()
        self._build_advanced()
        self._build_preferences()
        self._wire()

    # ------------------------------------------------------------------
    def bind(self, name: str, widget: QWidget) -> QWidget:
        self._binds.append((name, widget))
        return widget

    def bindp(self, name: str, widget: QWidget) -> QWidget:
        self._pref_binds.append((name, widget))
        return widget

    # ------------------------------------------------------------- pages
    def _build_format(self) -> None:
        page, lay = _page()
        self.mode = self.bind("mode", _combo([
            ("Video + Audio (normal download)", "video_audio"),
            ("Video only (no sound)", "video_only"),
            ("Audio only (extract)", "audio_only"),
        ]))
        self.quality = self.bind("quality", _combo(QUALITIES))
        self.video_codec = self.bind("video_codec", _combo(VIDEO_CODECS))
        self.fps_cap = self.bind("fps_cap", _combo(
            [("Any", "any"), ("Cap at 30 fps", "30"), ("Cap at 60 fps", "60")]))
        self.merge_container = self.bind("merge_container", _combo(CONTAINERS))
        lay.addWidget(_group("WHAT TO DOWNLOAD", [
            ("Mode", self.mode), ("Max quality", self.quality),
            ("Video codec", self.video_codec), ("Frame rate", self.fps_cap),
            ("Output container", self.merge_container),
        ]))

        self.remux_to = self.bind("remux_to", _combo(
            [("No remux", "none"), ("MP4", "mp4"), ("MKV", "mkv"), ("WebM", "webm"),
             ("MOV", "mov"), ("AVI", "avi"), ("FLV", "flv")]))
        self.recode_to = self.bind("recode_to", _combo(
            [("No re-encode", "none"), ("MP4", "mp4"), ("MKV", "mkv"), ("WebM", "webm"),
             ("MOV", "mov"), ("AVI", "avi")]))
        self.prefer_free_formats = self.bind("prefer_free_formats",
                                             QCheckBox("Prefer free (open) formats"))
        lay.addWidget(_group("CONVERSION", [
            ("Remux to", self.remux_to),
            ("Re-encode to", self.recode_to),
            ("", self.prefer_free_formats),
        ]))

        self.download_sections = self.bind("download_sections", QLineEdit())
        self.download_sections.setPlaceholderText("*00:01:30-00:04:00   or   *from-url")
        self.force_keyframes = self.bind("force_keyframes",
                                         QCheckBox("Frame-accurate cuts (re-encodes)"))
        lay.addWidget(_group("CLIP A SECTION", [
            ("Time range", self.download_sections),
            ("", self.force_keyframes),
            ("", _hint("Downloads only part of a video. Repeat ranges with commas. "
                       "Without the keyframe option, cuts land on the nearest keyframe.")),
        ]))

        self.custom_format = self.bind("custom_format", QLineEdit())
        self.custom_format.setPlaceholderText("e.g. bv*[height<=1080]+ba/b  - overrides the settings above")
        self.format_sort = self.bind("format_sort", QLineEdit())
        self.format_sort.setPlaceholderText("e.g. res,fps,vcodec:av01  (yt-dlp -S)")
        self.video_multistreams = self.bind("video_multistreams",
                                            QCheckBox("Multiple video streams"))
        self.audio_multistreams = self.bind("audio_multistreams",
                                            QCheckBox("Multiple audio streams"))
        self.check_formats = self.bind("check_formats",
                                       QCheckBox("Verify formats first (slower)"))
        lay.addWidget(_group("ADVANCED SELECTION", [
            ("Custom -f selector", self.custom_format),
            ("Format sort -S", self.format_sort),
            ("", self.video_multistreams), ("", self.audio_multistreams),
            ("", self.check_formats),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Format")

    def _build_audio(self) -> None:
        page, lay = _page()
        self.audio_format = self.bind("audio_format", _combo(AUDIO_FORMATS))
        self.audio_quality = self.bind("audio_quality", _combo(AUDIO_QUALITIES))
        self.audio_quality.setEditable(True)
        self.audio_codec_pref = self.bind("audio_codec_pref", _combo(
            [("Any", "any"), ("AAC / M4A", "aac"), ("Opus", "opus"),
             ("MP3", "mp3"), ("Vorbis", "vorbis")]))
        self.keep_video = self.bind("keep_video",
                                    QCheckBox("Keep the original video file"))
        lay.addWidget(_group("AUDIO EXTRACTION", [
            ("", _hint("Applies when Mode is <b>Audio only</b>.")),
            ("Convert to", self.audio_format),
            ("Quality / bitrate", self.audio_quality),
            ("", self.keep_video),
        ]))
        lay.addWidget(_group("TRACK SELECTION", [
            ("Audio codec", self.audio_codec_pref),
            ("", _hint("Also influences which audio track is picked for normal "
                       "video downloads.")),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Audio")

    def _build_subs(self) -> None:
        page, lay = _page()
        self.write_subs = self.bind("write_subs", QCheckBox("Download subtitle files"))
        self.auto_subs = self.bind("auto_subs", QCheckBox("Auto-generated subtitles"))
        self.embed_subs = self.bind("embed_subs", QCheckBox("Embed into the video"))
        self.sub_langs = self.bind("sub_langs", QLineEdit())
        self.sub_langs.setPlaceholderText("en,es,fr   or   all")
        self.sub_format = self.bind("sub_format", _combo(
            [("SRT", "srt"), ("ASS", "ass"), ("VTT", "vtt"), ("Best available", "best")]))
        self.convert_subs = self.bind("convert_subs", _combo(
            [("No conversion", "none"), ("SRT", "srt"), ("ASS", "ass"),
             ("VTT", "vtt"), ("LRC", "lrc")]))
        lay.addWidget(_group("SUBTITLES", [
            ("", self.write_subs), ("", self.auto_subs), ("", self.embed_subs),
            ("Languages", self.sub_langs), ("Preferred format", self.sub_format),
            ("Convert to", self.convert_subs),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Subtitles")

    def _build_metadata(self) -> None:
        page, lay = _page()
        self.embed_thumbnail = self.bind("embed_thumbnail", QCheckBox("Embed thumbnail as cover art"))
        self.write_thumbnail = self.bind("write_thumbnail", QCheckBox("Save thumbnail as an image"))
        self.convert_thumbnails = self.bind("convert_thumbnails", _combo(
            [("Leave as-is", "none"), ("JPG", "jpg"), ("PNG", "png"), ("WebP", "webp")]))
        self.embed_metadata = self.bind("embed_metadata", QCheckBox("Embed title/artist/date"))
        self.embed_chapters = self.bind("embed_chapters", QCheckBox("Embed chapter markers"))
        self.split_chapters = self.bind("split_chapters", QCheckBox("One file per chapter"))
        lay.addWidget(_group("THUMBNAILS & METADATA", [
            ("", self.embed_thumbnail), ("", self.write_thumbnail),
            ("Convert to", self.convert_thumbnails),
            ("", self.embed_metadata), ("", self.embed_chapters), ("", self.split_chapters),
        ]))

        self.write_info_json = self.bind("write_info_json", QCheckBox("Save .info.json sidecar"))
        self.clean_info_json = self.bind("clean_info_json", QCheckBox("Strip internal fields"))
        self.embed_info_json = self.bind("embed_info_json", QCheckBox("Embed info JSON in the file"))
        self.write_description = self.bind("write_description", QCheckBox("Save the description"))
        self.write_comments = self.bind("write_comments", QCheckBox("Download comments (slow)"))
        self.xattrs = self.bind("xattrs", QCheckBox("Write to extended attributes"))
        lay.addWidget(_group("SIDECAR FILES", [
            ("", self.write_info_json), ("", self.clean_info_json),
            ("", self.embed_info_json), ("", self.write_description),
            ("", self.write_comments), ("", self.xattrs),
        ]))

        sb_labels = [(c, c.replace("_", " ").title()) for c in SPONSORBLOCK_CATEGORIES]
        remove_holder, self.sb_remove_boxes = _checks(sb_labels, columns=2)
        mark_holder, self.sb_mark_boxes = _checks(sb_labels, columns=2)
        self.sponsorblock_chapter_title = self.bind("sponsorblock_chapter_title", QLineEdit())
        self.sponsorblock_chapter_title.setPlaceholderText("[SponsorBlock]: %(category_names)l")
        lay.addWidget(_group("SPONSORBLOCK", [
            ("", _hint("<b>Remove</b> cuts segments out of the file. "
                       "<b>Mark</b> only adds chapter markers.")),
            ("Remove", remove_holder), ("Mark", mark_holder),
            ("Chapter title", self.sponsorblock_chapter_title),
        ]))

        self.remove_chapters = self.bind("remove_chapters", QPlainTextEdit())
        self.remove_chapters.setPlaceholderText("One regex per line, e.g.  intro\nor a time range  *0-30")
        self.remove_chapters.setFixedHeight(58)
        self.parse_metadata = self.bind("parse_metadata", QPlainTextEdit())
        self.parse_metadata.setPlaceholderText("One rule per line, e.g.\n%(title)s:%(artist)s - %(title)s")
        self.parse_metadata.setFixedHeight(58)
        self.replace_in_metadata = self.bind("replace_in_metadata", QPlainTextEdit())
        self.replace_in_metadata.setPlaceholderText('One rule per line: FIELD REGEX REPLACEMENT\ntitle "\\s+" " "')
        self.replace_in_metadata.setFixedHeight(58)
        lay.addWidget(_group("CHAPTER & METADATA REWRITING", [
            ("Remove chapters", self.remove_chapters),
            ("Parse metadata", self.parse_metadata),
            ("Replace in metadata", self.replace_in_metadata),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Metadata")

    def _build_output(self) -> None:
        page, lay = _page()
        self.output_dir = PathEdit("dir", "Choose the download folder")
        self.bind("output_dir", self.output_dir)
        self.temp_dir = PathEdit("dir", "Choose a temporary folder")
        self.bind("temp_dir", self.temp_dir)
        self.temp_dir.edit.setPlaceholderText("Optional - partial files land here first")
        self.template_preset = _combo(TEMPLATE_PRESETS)
        self.output_template = self.bind("output_template", QLineEdit())
        self.template_preset.currentIndexChanged.connect(
            lambda: self.output_template.setText(self.template_preset.currentData()))
        lay.addWidget(_group("DESTINATION", [
            ("Download folder", self.output_dir), ("Temp folder", self.temp_dir),
            ("Naming preset", self.template_preset),
            ("Filename template", self.output_template),
        ]))

        self.restrict_filenames = self.bind("restrict_filenames",
                                            QCheckBox("ASCII-only filenames"))
        self.windows_filenames = self.bind("windows_filenames",
                                           QCheckBox("Windows-safe filenames"))
        self.trim_filenames = self.bind("trim_filenames", QSpinBox())
        self.trim_filenames.setRange(0, 250)
        self.trim_filenames.setSpecialValueText("No limit")
        self.overwrite_mode = self.bind("overwrite_mode", _combo([
            ("Skip files that already exist", "skip"),
            ("Resume partial downloads", "continue"),
            ("Always overwrite", "overwrite"),
        ]))
        self.no_mtime = self.bind("no_mtime", QCheckBox("Use download time as file date"))
        self.no_part = self.bind("no_part", QCheckBox("No .part files"))
        lay.addWidget(_group("FILENAMES", [
            ("", self.restrict_filenames), ("", self.windows_filenames),
            ("Max filename length", self.trim_filenames),
            ("If the file exists", self.overwrite_mode),
            ("", self.no_mtime), ("", self.no_part),
        ]))

        self.use_archive = self.bind("use_archive", QCheckBox("Use a download archive"))
        self.archive_file = PathEdit("save", "Choose an archive file", "Text files (*.txt)")
        self.bind("archive_file", self.archive_file)
        self.archive_file.edit.setPlaceholderText("e.g. X:\\11_YT-DLP\\downloaded.txt")
        lay.addWidget(_group("DOWNLOAD ARCHIVE", [
            ("", self.use_archive), ("Archive file", self.archive_file),
        ]))

        self.exec_cmd = self.bind("exec_cmd", QLineEdit())
        self.exec_cmd.setPlaceholderText('e.g. echo %(filepath)q   - runs after each download')
        lay.addWidget(_group("RUN AFTER DOWNLOAD", [("Command", self.exec_cmd)]))
        lay.addStretch(1)
        self.addTab(page, "Output")

    def _build_playlist(self) -> None:
        page, lay = _page()
        self.playlist_mode = self.bind("playlist_mode", _combo([
            ("Auto - follow the URL", "auto"),
            ("Single video only (ignore the playlist)", "single"),
            ("Always download the whole playlist", "playlist"),
        ]))
        self.playlist_items = self.bind("playlist_items", QLineEdit())
        self.playlist_items.setPlaceholderText("e.g. 1-5,8,12-  (blank = all)")
        self.max_downloads = self.bind("max_downloads", QSpinBox())
        self.max_downloads.setRange(0, 100000)
        self.max_downloads.setSpecialValueText("Unlimited")
        self.playlist_reverse = self.bind("playlist_reverse", QCheckBox("Reverse order"))
        self.playlist_random = self.bind("playlist_random", QCheckBox("Random order"))
        self.lazy_playlist = self.bind("lazy_playlist", QCheckBox("Lazy playlist parsing"))
        self.write_playlist_metafiles = self.bind("write_playlist_metafiles",
                                                  QCheckBox("Playlist metadata files"))
        lay.addWidget(_group("PLAYLIST HANDLING", [
            ("If the URL is a playlist", self.playlist_mode),
            ("Items to download", self.playlist_items),
            ("Stop after N videos", self.max_downloads),
            ("", self.playlist_reverse), ("", self.playlist_random),
            ("", self.lazy_playlist), ("", self.write_playlist_metafiles),
        ]))

        self.date_after = self.bind("date_after", QLineEdit())
        self.date_after.setPlaceholderText("YYYYMMDD  or  today-2weeks")
        self.date_before = self.bind("date_before", QLineEdit())
        self.date_before.setPlaceholderText("YYYYMMDD")
        self.match_filter = self.bind("match_filter", QLineEdit())
        self.match_filter.setPlaceholderText("e.g. duration < 600 & view_count > 1000")
        self.min_filesize = self.bind("min_filesize", QLineEdit())
        self.min_filesize.setPlaceholderText("e.g. 5M")
        self.max_filesize = self.bind("max_filesize", QLineEdit())
        self.max_filesize.setPlaceholderText("e.g. 2G")
        self.age_limit = self.bind("age_limit", QLineEdit())
        self.age_limit.setPlaceholderText("e.g. 18")
        self.break_on_existing = self.bind("break_on_existing",
                                           QCheckBox("Stop at first existing video"))
        self.mark_watched = self.bind("mark_watched", QCheckBox("Mark as watched on the site"))
        lay.addWidget(_group("FILTERS", [
            ("Uploaded after", self.date_after), ("Uploaded before", self.date_before),
            ("Match filter", self.match_filter),
            ("Min filesize", self.min_filesize), ("Max filesize", self.max_filesize),
            ("Age limit", self.age_limit),
            ("", self.break_on_existing), ("", self.mark_watched),
        ]))

        self.live_from_start = self.bind("live_from_start",
                                         QCheckBox("Livestream from the start"))
        self.wait_for_video = self.bind("wait_for_video", QLineEdit())
        self.wait_for_video.setPlaceholderText("e.g. 30-300  (poll until a scheduled stream starts)")
        lay.addWidget(_group("LIVESTREAMS", [
            ("", self.live_from_start), ("Wait for video", self.wait_for_video),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Playlist")

    def _build_network(self) -> None:
        page, lay = _page()
        self.rate_limit = self.bind("rate_limit", QLineEdit())
        self.rate_limit.setPlaceholderText("e.g. 5M or 500K  (blank = unlimited)")
        self.throttled_rate = self.bind("throttled_rate", QLineEdit())
        self.throttled_rate.setPlaceholderText("e.g. 100K - re-extract below this speed")
        self.concurrent_fragments = self.bind("concurrent_fragments", QSpinBox())
        self.concurrent_fragments.setRange(1, 64)
        self.http_chunk_size = self.bind("http_chunk_size", QLineEdit())
        self.http_chunk_size.setPlaceholderText("e.g. 10M")
        self.buffer_size = self.bind("buffer_size", QLineEdit())
        self.buffer_size.setPlaceholderText("e.g. 16K")
        lay.addWidget(_group("SPEED", [
            ("Speed limit", self.rate_limit), ("Throttle threshold", self.throttled_rate),
            ("Parallel fragments", self.concurrent_fragments),
            ("HTTP chunk size", self.http_chunk_size), ("Buffer size", self.buffer_size),
        ]))

        self.retries = self.bind("retries", QLineEdit())
        self.fragment_retries = self.bind("fragment_retries", QLineEdit())
        self.file_access_retries = self.bind("file_access_retries", QLineEdit())
        self.retry_sleep = self.bind("retry_sleep", QLineEdit())
        self.retry_sleep.setPlaceholderText("e.g. exp=1:20")
        self.socket_timeout = self.bind("socket_timeout", QLineEdit())
        self.socket_timeout.setPlaceholderText("seconds")
        self.keep_fragments = self.bind("keep_fragments", QCheckBox("Keep fragments after merging"))
        self.abort_on_unavailable_fragment = self.bind(
            "abort_on_unavailable_fragment", QCheckBox("Abort on missing fragment"))
        lay.addWidget(_group("RELIABILITY", [
            ("Retries", self.retries), ("Fragment retries", self.fragment_retries),
            ("File access retries", self.file_access_retries),
            ("Retry sleep", self.retry_sleep), ("Socket timeout", self.socket_timeout),
            ("", self.keep_fragments), ("", self.abort_on_unavailable_fragment),
        ]))

        self.proxy = self.bind("proxy", QLineEdit())
        self.proxy.setPlaceholderText("http://host:port  or  socks5://host:port")
        self.force_ip = self.bind("force_ip", _combo(
            [("Automatic", "auto"), ("Force IPv4", "4"), ("Force IPv6", "6")]))
        self.geo_bypass_country = self.bind("geo_bypass_country", QLineEdit())
        self.geo_bypass_country.setPlaceholderText("Two-letter code, e.g. US")
        self.no_check_certificate = self.bind("no_check_certificate",
                                              QCheckBox("Skip TLS verification"))
        self.legacy_server_connect = self.bind("legacy_server_connect",
                                               QCheckBox("Allow legacy TLS renegotiation"))
        self.hls_use_mpegts = self.bind("hls_use_mpegts",
                                        QCheckBox("MPEG-TS for HLS"))
        lay.addWidget(_group("CONNECTION", [
            ("Proxy", self.proxy), ("IP version", self.force_ip),
            ("Geo-bypass", self.geo_bypass_country),
            ("", self.no_check_certificate), ("", self.legacy_server_connect),
            ("", self.hls_use_mpegts),
        ]))

        self.downloader = self.bind("downloader", _combo(
            [("Built-in (native)", "native"), ("aria2c (fastest, must be installed)", "aria2c"),
             ("ffmpeg", "ffmpeg")]))
        self.downloader_args = self.bind("downloader_args", QLineEdit())
        self.downloader_args.setPlaceholderText("e.g. aria2c:-x16 -k1M")
        self.sleep_interval = self.bind("sleep_interval", QLineEdit())
        self.max_sleep_interval = self.bind("max_sleep_interval", QLineEdit())
        self.sleep_requests = self.bind("sleep_requests", QLineEdit())
        lay.addWidget(_group("DOWNLOADER & THROTTLING", [
            ("Downloader", self.downloader),
            ("Downloader args", self.downloader_args),
            ("Sleep between DLs", self.sleep_interval),
            ("Max sleep", self.max_sleep_interval),
            ("Sleep per request", self.sleep_requests),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Network")

    def _build_access(self) -> None:
        page, lay = _page()
        self.cookies_mode = self.bind("cookies_mode", _combo([
            ("Do not use cookies", "none"), ("Import from a browser", "browser"),
            ("Use a cookies.txt file", "file"),
        ]))
        self.cookies_browser = self.bind("cookies_browser", _combo(BROWSERS))
        self.cookies_profile = self.bind("cookies_profile", QLineEdit())
        self.cookies_profile.setPlaceholderText("Optional profile, e.g. Default")
        self.cookies_file = PathEdit("open", "Choose a cookies file", "Text files (*.txt)")
        self.bind("cookies_file", self.cookies_file)
        lay.addWidget(_group("COOKIES", [
            ("", _hint("Needed for age-restricted, members-only or private videos. "
                       "Close the browser first - it locks its cookie database.")),
            ("Source", self.cookies_mode), ("Browser", self.cookies_browser),
            ("Profile", self.cookies_profile), ("Cookies file", self.cookies_file),
        ]))

        self.username = self.bind("username", QLineEdit())
        self.password = self.bind("password", QLineEdit())
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.twofactor = self.bind("twofactor", QLineEdit())
        self.netrc = self.bind("netrc", QCheckBox("Use .netrc credentials"))
        lay.addWidget(_group("SITE LOGIN", [
            ("Username", self.username), ("Password", self.password),
            ("2FA code", self.twofactor), ("", self.netrc),
            ("", _hint("Credentials live in memory for this session only and are "
                       "never written to the settings file.")),
        ]))

        self.user_agent = self.bind("user_agent", QLineEdit())
        self.referer = self.bind("referer", QLineEdit())
        self.extra_headers = self.bind("extra_headers", QPlainTextEdit())
        self.extra_headers.setPlaceholderText("One header per line:\nX-Example: value")
        self.extra_headers.setFixedHeight(64)
        lay.addWidget(_group("HTTP HEADERS", [
            ("User agent", self.user_agent), ("Referer", self.referer),
            ("Extra headers", self.extra_headers),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Access")

    def _build_advanced(self) -> None:
        page, lay = _page()
        self.ffmpeg_location = PathEdit("open", "Locate ffmpeg.exe", "Executables (*.exe)")
        self.bind("ffmpeg_location", self.ffmpeg_location)
        self.ffmpeg_location.edit.setPlaceholderText("Auto-detected if left blank")
        self.postprocessor_args = self.bind("postprocessor_args", QLineEdit())
        self.postprocessor_args.setPlaceholderText('e.g. ffmpeg:-vf scale=1280:-2')
        lay.addWidget(_group("FFMPEG", [
            ("ffmpeg path", self.ffmpeg_location),
            ("Postproc args", self.postprocessor_args),
        ]))

        self.extractor_args = self.bind("extractor_args", QPlainTextEdit())
        self.extractor_args.setPlaceholderText(
            "One per line, e.g.\nyoutube:player_client=android,web\nyoutube:skip=hls,dash")
        self.extractor_args.setFixedHeight(64)
        lay.addWidget(_group("EXTRACTOR ARGUMENTS", [
            ("", self.extractor_args),
            ("", _hint("Site-specific tuning. The YouTube client switch above is the "
                       "usual fix when a video refuses to download.")),
        ]))

        self.ignore_config = self.bind("ignore_config", QCheckBox(
            "Ignore yt-dlp config files"))
        self.ignore_errors = self.bind("ignore_errors", QCheckBox("Continue past errors"))
        self.no_cache = self.bind("no_cache", QCheckBox("Disable the yt-dlp cache"))
        self.verbose = self.bind("verbose", QCheckBox("Verbose logging"))
        self.simulate = self.bind("simulate", QCheckBox("Simulate (download nothing)"))
        lay.addWidget(_group("BEHAVIOUR", [
            ("", self.ignore_config), ("", self.ignore_errors), ("", self.no_cache),
            ("", self.verbose), ("", self.simulate),
            ("", _hint("<b>Ignore config</b> makes this app the single source of truth, "
                       "so nothing in %APPDATA%\\yt-dlp\\config can override it.")),
        ]))

        self.concurrent_downloads = self.bind("concurrent_downloads", QSpinBox())
        self.concurrent_downloads.setRange(1, 10)
        self.extra_args = self.bind("extra_args", QPlainTextEdit())
        self.extra_args.setPlaceholderText("Raw yt-dlp flags, appended last")
        self.extra_args.setFixedHeight(64)
        lay.addWidget(_group("QUEUE & RAW FLAGS", [
            ("Simultaneous", self.concurrent_downloads),
            ("Extra arguments", self.extra_args),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Advanced")

    # ------------------------------------------------------- preferences
    def _build_preferences(self) -> None:
        page, lay = _page()

        self.theme = self.bindp("theme", _combo([(n, n) for n in THEME_ORDER]))
        self.theme_blurb = _hint("")
        self.swatches = QWidget()
        sw = QHBoxLayout(self.swatches)
        sw.setContentsMargins(0, 0, 0, 0)
        sw.setSpacing(5)
        self._swatch_labels = []
        for _ in range(6):
            chip = QLabel()
            chip.setFixedSize(30, 18)
            self._swatch_labels.append(chip)
            sw.addWidget(chip)
        sw.addStretch(1)

        self.font_family = self.bindp("font_family", _combo([(f, f) for f in FONT_CHOICES]))
        self.font_size = self.bindp("font_size", QSpinBox())
        self.font_size.setRange(10, 20)
        self.font_size.setSuffix(" px")
        self.density = self.bindp("density", _combo([(d, d) for d in DENSITY]))
        self.corner_radius = self.bindp("corner_radius", QSpinBox())
        self.corner_radius.setRange(0, 16)
        self.corner_radius.setSuffix(" px")
        self.uppercase_nav = self.bindp("uppercase_nav", QCheckBox("Uppercase nav labels"))
        lay.addWidget(_group("APPEARANCE", [
            ("Theme", self.theme), ("", self.theme_blurb), ("Palette", self.swatches),
            ("Font", self.font_family), ("Font size", self.font_size),
            ("Density", self.density), ("Corner radius", self.corner_radius),
            ("", self.uppercase_nav),
        ]))

        self.remember_window = self.bindp("remember_window", QCheckBox("Remember size and position"))
        self.always_on_top = self.bindp("always_on_top", QCheckBox("Always on top"))
        self.start_minimized = self.bindp("start_minimized", QCheckBox("Start minimized"))
        self.minimize_to_tray = self.bindp("minimize_to_tray", QCheckBox("Minimize to tray"))
        lay.addWidget(_group("WINDOW", [
            ("", self.remember_window), ("", self.always_on_top),
            ("", self.start_minimized), ("", self.minimize_to_tray),
        ]))

        self.auto_start_on_add = self.bindp("auto_start_on_add",
                                            QCheckBox("Auto-start when a URL is added"))
        self.skip_duplicates = self.bindp("skip_duplicates",
                                          QCheckBox("Skip duplicate URLs"))
        self.auto_clear_completed = self.bindp("auto_clear_completed",
                                               QCheckBox("Auto-remove finished rows"))
        self.auto_retry_failed = self.bindp("auto_retry_failed", QSpinBox())
        self.auto_retry_failed.setRange(0, 10)
        self.auto_retry_failed.setSpecialValueText("Off")
        self.confirm_on_quit = self.bindp("confirm_on_quit",
                                          QCheckBox("Confirm quit while downloading"))
        self.shutdown_when_done = self.bindp("shutdown_when_done",
                                             QCheckBox("Shut down PC when finished"))
        lay.addWidget(_group("QUEUE BEHAVIOUR", [
            ("", self.auto_start_on_add), ("", self.skip_duplicates),
            ("", self.auto_clear_completed),
            ("Auto-retry failed", self.auto_retry_failed),
            ("", self.confirm_on_quit), ("", self.shutdown_when_done),
        ]))

        self.clipboard_watch = self.bindp("clipboard_watch",
                                          QCheckBox("Auto-queue copied links"))
        self.notify_on_complete = self.bindp("notify_on_complete",
                                             QCheckBox("Notify when finished"))
        self.sound_on_complete = self.bindp("sound_on_complete", QCheckBox("Play a sound when finished"))
        self.open_folder_when_done = self.bindp("open_folder_when_done",
                                                QCheckBox("Open folder when finished"))
        lay.addWidget(_group("INTEGRATION", [
            ("", self.clipboard_watch),
            ("", _hint("Clipboard watching only reacts to http(s) links you copy, "
                       "and never to anything else on the clipboard.")),
            ("", self.notify_on_complete), ("", self.sound_on_complete),
            ("", self.open_folder_when_done),
        ]))

        self.log_max_lines = self.bindp("log_max_lines", QSpinBox())
        self.log_max_lines.setRange(500, 100000)
        self.log_max_lines.setSingleStep(500)
        self.log_to_file = self.bindp("log_to_file", QCheckBox("Write log to a file"))
        self.log_file = PathEdit("save", "Choose a log file", "Log files (*.log *.txt)")
        self.bindp("log_file", self.log_file)
        lay.addWidget(_group("LOGGING", [
            ("Max log lines", self.log_max_lines),
            ("", self.log_to_file), ("Log file", self.log_file),
        ]))

        self.ytdlp_path = PathEdit("open", "Locate yt-dlp.exe", "Executables (*.exe)")
        self.bindp("ytdlp_path", self.ytdlp_path)
        self.ytdlp_path.edit.setPlaceholderText("Auto-detected if left blank")
        self.ffmpeg_path = PathEdit("open", "Locate ffmpeg.exe", "Executables (*.exe)")
        self.bindp("ffmpeg_path", self.ffmpeg_path)
        self.ffmpeg_path.edit.setPlaceholderText("Auto-detected if left blank")

        tools = QWidget()
        trow = QHBoxLayout(tools)
        trow.setContentsMargins(0, 0, 0, 0)
        trow.setSpacing(8)
        self.btn_update_ytdlp = QPushButton("Update yt-dlp")
        self.btn_update_ytdlp.setObjectName("Ghost")
        self.btn_open_settings = QPushButton("Settings")
        self.btn_open_settings.setObjectName("Ghost")
        trow.addWidget(self.btn_update_ytdlp)
        trow.addWidget(self.btn_open_settings)
        trow.addStretch(1)

        io_tools = QWidget()
        irow = QHBoxLayout(io_tools)
        irow.setContentsMargins(0, 0, 0, 0)
        irow.setSpacing(8)
        self.btn_export = QPushButton("Export")
        self.btn_export.setObjectName("Ghost")
        self.btn_import = QPushButton("Import")
        self.btn_import.setObjectName("Ghost")
        self.btn_reset_all = QPushButton("Reset all")
        self.btn_reset_all.setObjectName("Danger")
        irow.addWidget(self.btn_export)
        irow.addWidget(self.btn_import)
        irow.addWidget(self.btn_reset_all)
        irow.addStretch(1)

        lay.addWidget(_group("BINARIES & MAINTENANCE", [
            ("yt-dlp path", self.ytdlp_path), ("ffmpeg path", self.ffmpeg_path),
            ("", tools), ("", io_tools),
        ]))
        lay.addStretch(1)
        self.addTab(page, "Preferences")

    # ------------------------------------------------------------- wiring
    def _signal_for(self, widget: QWidget):
        target = widget.edit if isinstance(widget, PathEdit) else widget
        if isinstance(target, QLineEdit):
            return target.textChanged
        if isinstance(target, QComboBox):
            return target.currentIndexChanged
        if isinstance(target, QCheckBox):
            return target.toggled
        if isinstance(target, QSpinBox):
            return target.valueChanged
        if isinstance(target, QPlainTextEdit):
            return target.textChanged
        return None

    def _wire(self) -> None:
        for _, widget in self._binds:
            sig = self._signal_for(widget)
            if sig is not None:
                sig.connect(self.changed)
            target = widget.edit if isinstance(widget, PathEdit) else widget
            if isinstance(target, QComboBox) and target.isEditable():
                target.editTextChanged.connect(self.changed)
        for boxes in (self.sb_remove_boxes, self.sb_mark_boxes):
            for cb in boxes.values():
                cb.toggled.connect(self.changed)

        for _, widget in self._pref_binds:
            sig = self._signal_for(widget)
            if sig is not None:
                sig.connect(self.prefs_changed)

        self.mode.currentIndexChanged.connect(self._sync_enabled)
        self.cookies_mode.currentIndexChanged.connect(self._sync_enabled)
        self.use_archive.toggled.connect(self._sync_enabled)
        self.custom_format.textChanged.connect(self._sync_enabled)
        self.log_to_file.toggled.connect(self._sync_enabled)
        self.download_sections.textChanged.connect(self._sync_enabled)
        self.theme.currentIndexChanged.connect(self._sync_theme_preview)
        self._sync_theme_preview()

    def _sync_theme_preview(self) -> None:
        palette = THEMES.get(self.theme.currentData()) or THEMES[THEME_ORDER[0]]
        self.theme_blurb.setText(palette.blurb)
        colors = [palette.accent, palette.accent2, palette.ok,
                  palette.warn, palette.err, palette.panel_alt]
        for chip, color in zip(self._swatch_labels, colors):
            chip.setStyleSheet(
                f"background-color: {color}; border-radius: 4px; "
                f"border: 1px solid {palette.border_light};")

    def _sync_enabled(self) -> None:
        audio_only = self.mode.currentData() == "audio_only"
        custom = bool(self.custom_format.text().strip())
        for w in (self.quality, self.video_codec, self.fps_cap):
            w.setEnabled(not audio_only and not custom)
        for w in (self.merge_container, self.remux_to, self.recode_to):
            w.setEnabled(not audio_only)
        for w in (self.audio_format, self.audio_quality, self.keep_video):
            w.setEnabled(audio_only)

        cookies = self.cookies_mode.currentData()
        self.cookies_browser.setEnabled(cookies == "browser")
        self.cookies_profile.setEnabled(cookies == "browser")
        self.cookies_file.setEnabled(cookies == "file")
        self.archive_file.setEnabled(self.use_archive.isChecked())
        self.log_file.setEnabled(self.log_to_file.isChecked())
        self.force_keyframes.setEnabled(bool(self.download_sections.text().strip()))

    # --------------------------------------------------------------- sync
    def _read_widget(self, widget: QWidget):
        target = widget.edit if isinstance(widget, PathEdit) else widget
        if isinstance(target, QLineEdit):
            return target.text()
        if isinstance(target, QComboBox):
            if target.isEditable() and target.findText(target.currentText()) < 0:
                return target.currentText()
            data = target.currentData()
            return str(data) if data is not None else target.currentText()
        if isinstance(target, QCheckBox):
            return target.isChecked()
        if isinstance(target, QSpinBox):
            return target.value()
        if isinstance(target, QPlainTextEdit):
            return target.toPlainText()
        return None

    def _write_widget(self, widget: QWidget, value) -> None:
        target = widget.edit if isinstance(widget, PathEdit) else widget
        target.blockSignals(True)
        if isinstance(target, QLineEdit):
            target.setText(str(value))
        elif isinstance(target, QComboBox):
            idx = target.findData(str(value))
            if idx >= 0:
                target.setCurrentIndex(idx)
            elif target.isEditable():
                target.setEditText(str(value))
        elif isinstance(target, QCheckBox):
            target.setChecked(bool(value))
        elif isinstance(target, QSpinBox):
            target.setValue(int(value))
        elif isinstance(target, QPlainTextEdit):
            target.setPlainText(str(value))
        target.blockSignals(False)

    def load_options(self, opt: Options) -> None:
        for name, widget in self._binds:
            self._write_widget(widget, getattr(opt, name))
        for key, cb in self.sb_remove_boxes.items():
            cb.blockSignals(True)
            cb.setChecked(key in opt.sb_remove)
            cb.blockSignals(False)
        for key, cb in self.sb_mark_boxes.items():
            cb.blockSignals(True)
            cb.setChecked(key in opt.sb_mark)
            cb.blockSignals(False)
        self._sync_enabled()
        self.changed.emit()

    def read_options(self) -> Options:
        opt = Options()
        for name, widget in self._binds:
            value = self._read_widget(widget)
            if value is not None:
                setattr(opt, name, value)
        opt.sb_remove = [k for k, cb in self.sb_remove_boxes.items() if cb.isChecked()]
        opt.sb_mark = [k for k, cb in self.sb_mark_boxes.items() if cb.isChecked()]
        return opt

    def load_prefs(self, prefs: AppPrefs) -> None:
        for name, widget in self._pref_binds:
            self._write_widget(widget, getattr(prefs, name))
        self._sync_enabled()
        self._sync_theme_preview()

    def read_prefs(self) -> AppPrefs:
        prefs = AppPrefs()
        for name, widget in self._pref_binds:
            value = self._read_widget(widget)
            if value is not None:
                setattr(prefs, name, value)
        return prefs
