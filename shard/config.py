"""Configuration model, persistence and presets for Shard."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

_APPDATA = Path(os.environ.get("APPDATA", Path.home()))
APP_DIR = _APPDATA / "Shard"
CONFIG_PATH = APP_DIR / "settings.json"
LEGACY_CONFIG_PATH = _APPDATA / "ytdlp-studio" / "settings.json"

# Never written to disk.
SECRET_FIELDS = {"password", "twofactor"}


@dataclass
class Options:
    # ---------------- Output ----------------
    output_dir: str = "X:\\11_YT-DLP"
    temp_dir: str = ""
    output_template: str = "%(title)s [%(id)s].%(ext)s"
    restrict_filenames: bool = False
    windows_filenames: bool = True
    trim_filenames: int = 0
    overwrite_mode: str = "skip"  # skip | overwrite | continue
    use_archive: bool = False
    archive_file: str = ""
    ignore_config: bool = True
    no_mtime: bool = False

    # ---------------- Format / video ----------------
    mode: str = "video_audio"  # video_audio | video_only | audio_only
    quality: str = "best"  # best | 4320 | 2160 | ... | 144 | worst
    video_codec: str = "any"  # any | avc1 | hevc | vp9 | av1
    fps_cap: str = "any"  # any | 30 | 60
    merge_container: str = "mp4"  # default | mp4 | mkv | webm | mov
    remux_to: str = "none"
    recode_to: str = "none"
    prefer_free_formats: bool = False
    custom_format: str = ""  # overrides all format logic when set
    format_sort: str = ""  # -S value

    # ---------------- Audio ----------------
    audio_format: str = "mp3"
    audio_quality: str = "0"  # 0-10 (VBR) or a bitrate like 320K
    audio_codec_pref: str = "any"  # any | aac | opus | mp3 | vorbis
    keep_video: bool = False

    # ---------------- Subtitles ----------------
    write_subs: bool = False
    auto_subs: bool = False
    embed_subs: bool = False
    sub_langs: str = "en"
    sub_format: str = "srt"
    convert_subs: str = "none"

    # ---------------- Metadata / extras ----------------
    embed_thumbnail: bool = True
    write_thumbnail: bool = False
    embed_metadata: bool = True
    embed_chapters: bool = True
    write_info_json: bool = False
    write_description: bool = False
    write_comments: bool = False
    split_chapters: bool = False
    xattrs: bool = False

    # ---------------- SponsorBlock ----------------
    sb_remove: list[str] = field(default_factory=list)
    sb_mark: list[str] = field(default_factory=list)

    # ---------------- Playlist ----------------
    playlist_mode: str = "auto"  # auto | single | playlist
    playlist_items: str = ""
    playlist_reverse: bool = False
    playlist_random: bool = False
    max_downloads: int = 0
    date_after: str = ""
    date_before: str = ""
    match_filter: str = ""
    break_on_existing: bool = False

    # ---------------- Network ----------------
    rate_limit: str = ""
    concurrent_fragments: int = 4
    retries: str = "10"
    fragment_retries: str = "10"
    socket_timeout: str = ""
    proxy: str = ""
    force_ip: str = "auto"  # auto | 4 | 6
    downloader: str = "native"  # native | aria2c | ffmpeg
    downloader_args: str = ""
    sleep_interval: str = ""
    max_sleep_interval: str = ""
    sleep_requests: str = ""

    # ---------------- Auth / access ----------------
    cookies_mode: str = "none"  # none | browser | file
    cookies_browser: str = "chrome"
    cookies_profile: str = ""
    cookies_file: str = ""
    username: str = ""
    password: str = ""  # session only
    twofactor: str = ""  # session only
    netrc: bool = False
    user_agent: str = ""
    referer: str = ""
    extra_headers: str = ""  # one "Key: Value" per line
    geo_bypass_country: str = ""

    # ---------------- Clip / sections ----------------
    download_sections: str = ""  # e.g. *00:10:00-00:15:00
    force_keyframes: bool = False

    # ---------------- Size / age filters ----------------
    min_filesize: str = ""
    max_filesize: str = ""
    age_limit: str = ""

    # ---------------- Livestreams ----------------
    live_from_start: bool = False
    wait_for_video: str = ""

    # ---------------- Fragments / buffering ----------------
    no_part: bool = False
    http_chunk_size: str = ""
    buffer_size: str = ""
    throttled_rate: str = ""
    keep_fragments: bool = False
    abort_on_unavailable_fragment: bool = False
    retry_sleep: str = ""
    file_access_retries: str = ""

    # ---------------- Streams / probing ----------------
    video_multistreams: bool = False
    audio_multistreams: bool = False
    check_formats: bool = False

    # ---------------- TLS / transport ----------------
    no_check_certificate: bool = False
    legacy_server_connect: bool = False
    hls_use_mpegts: bool = False

    # ---------------- Playlist extras ----------------
    lazy_playlist: bool = False
    write_playlist_metafiles: bool = False
    mark_watched: bool = False

    # ---------------- Post-processing extras ----------------
    convert_thumbnails: str = "none"
    remove_chapters: str = ""
    sponsorblock_chapter_title: str = ""
    exec_cmd: str = ""
    postprocessor_args: str = ""
    parse_metadata: str = ""
    replace_in_metadata: str = ""
    clean_info_json: bool = False
    embed_info_json: bool = False

    # ---------------- Advanced ----------------
    ffmpeg_location: str = ""
    extractor_args: str = ""
    no_cache: bool = False
    extra_args: str = ""
    ignore_errors: bool = True
    verbose: bool = False
    simulate: bool = False

    # ---------------- App behaviour ----------------
    concurrent_downloads: int = 2

    # ------------------------------------------------
    def clone(self) -> "Options":
        return copy.deepcopy(self)

    def to_dict(self, include_secrets: bool = False) -> dict[str, Any]:
        data = asdict(self)
        if not include_secrets:
            for key in SECRET_FIELDS:
                data.pop(key, None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Options":
        known = {f.name: f for f in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in (data or {}).items():
            if key not in known:
                continue
            # Guard against a settings file written by a different version.
            try:
                if known[key].type in ("int", int):
                    value = int(value)
                elif known[key].type in ("bool", bool):
                    value = bool(value)
                elif known[key].type in ("str", str):
                    value = str(value)
            except (TypeError, ValueError):
                continue
            kwargs[key] = value
        return cls(**kwargs)


@dataclass
class AppPrefs:
    """Application-level preferences - appearance and behaviour, not download flags."""

    # Appearance
    theme: str = "Neon Crystal"
    font_family: str = "Segoe UI"
    font_size: int = 13
    density: str = "Comfortable"
    corner_radius: int = 8
    uppercase_nav: bool = True

    # Window
    remember_window: bool = True
    always_on_top: bool = False
    start_minimized: bool = False
    minimize_to_tray: bool = False

    # Queue behaviour
    auto_start_on_add: bool = False
    skip_duplicates: bool = True
    auto_clear_completed: bool = False
    auto_retry_failed: int = 0
    confirm_on_quit: bool = True
    shutdown_when_done: bool = False

    # Integration
    clipboard_watch: bool = False
    notify_on_complete: bool = True
    sound_on_complete: bool = False
    open_folder_when_done: bool = False

    # Logging
    log_max_lines: int = 6000
    log_to_file: bool = False
    log_file: str = ""

    # Binaries
    ytdlp_path: str = ""
    ffmpeg_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppPrefs":
        known = {f.name: f for f in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in (data or {}).items():
            if key not in known:
                continue
            try:
                if known[key].type in ("int", int):
                    value = int(value)
                elif known[key].type in ("bool", bool):
                    value = bool(value)
                elif known[key].type in ("str", str):
                    value = str(value)
            except (TypeError, ValueError):
                continue
            kwargs[key] = value
        return cls(**kwargs)


@dataclass
class Settings:
    """Top-level persisted state: the active options plus named presets."""

    options: Options = field(default_factory=Options)
    prefs: AppPrefs = field(default_factory=AppPrefs)
    presets: dict[str, dict] = field(default_factory=dict)
    default_preset: str = ""
    ytdlp_path: str = ""  # legacy - migrated into prefs on load
    window_geometry: str = ""

    # ------------------------------------------------
    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Settings":
        # Carry over settings from the pre-rename install, once.
        if path == CONFIG_PATH and not path.exists() and LEGACY_CONFIG_PATH.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"),
                                encoding="utf-8")
            except OSError:
                pass
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        prefs = AppPrefs.from_dict(raw.get("prefs", {}))
        legacy = raw.get("ytdlp_path", "") or ""
        if legacy and not prefs.ytdlp_path:
            prefs.ytdlp_path = legacy
        return cls(
            options=Options.from_dict(raw.get("options", {})),
            prefs=prefs,
            presets=raw.get("presets", {}) or {},
            default_preset=raw.get("default_preset", "") or "",
            ytdlp_path=legacy,
            window_geometry=raw.get("window_geometry", "") or "",
        )

    def save(self, path: Path = CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "options": self.options.to_dict(),
            "prefs": self.prefs.to_dict(),
            "presets": self.presets,
            "default_preset": self.default_preset,
            "window_geometry": self.window_geometry,
        }
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(path)

    # ------------------------------------------------
    def save_preset(self, name: str, options: Options) -> None:
        self.presets[name] = options.to_dict()

    def load_preset(self, name: str) -> Options | None:
        if name not in self.presets:
            return None
        return Options.from_dict(self.presets[name])

    def delete_preset(self, name: str) -> None:
        self.presets.pop(name, None)
        if self.default_preset == name:
            self.default_preset = ""


# Built-in presets offered on first run.
BUILTIN_PRESETS: dict[str, dict] = {
    "Best quality (MP4)": {
        "mode": "video_audio", "quality": "best", "video_codec": "avc1",
        "merge_container": "mp4", "embed_thumbnail": True, "embed_metadata": True,
    },
    "1080p H.264 (max compatibility)": {
        "mode": "video_audio", "quality": "1080", "video_codec": "avc1",
        "merge_container": "mp4", "embed_thumbnail": True, "embed_metadata": True,
    },
    "4K HDR (MKV)": {
        "mode": "video_audio", "quality": "2160", "video_codec": "any",
        "merge_container": "mkv", "embed_metadata": True, "embed_chapters": True,
    },
    "MP3 320k (audio only)": {
        "mode": "audio_only", "audio_format": "mp3", "audio_quality": "320K",
        "embed_thumbnail": True, "embed_metadata": True,
    },
    "FLAC lossless (audio only)": {
        "mode": "audio_only", "audio_format": "flac",
        "embed_thumbnail": True, "embed_metadata": True,
    },
    "Archive + subtitles": {
        "mode": "video_audio", "quality": "best", "merge_container": "mkv",
        "write_subs": True, "auto_subs": True, "embed_subs": True,
        "sub_langs": "en", "write_info_json": True, "write_thumbnail": True,
    },
}
