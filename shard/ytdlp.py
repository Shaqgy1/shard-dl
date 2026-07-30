"""Locating the yt-dlp binary and translating Options into a command line."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .config import Options

# Marker prefixes we ask yt-dlp to emit so progress can be parsed reliably.
PROGRESS_MARK = "@@P@@"
POST_MARK = "@@PP@@"

PROGRESS_TEMPLATE = (
    "download:" + PROGRESS_MARK + "|%(progress.status)s|%(progress.downloaded_bytes)s"
    "|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s"
    "|%(progress.eta)s|%(info.title)s"
)
POSTPROCESS_TEMPLATE = "postprocess:" + POST_MARK + "|%(progress.status)s|%(info.title)s"

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# Codec preference -> yt-dlp format-filter regex
VIDEO_CODEC_FILTERS = {
    "avc1": r"[vcodec~='^(avc1|h264)']",
    "hevc": r"[vcodec~='^(hev1|hvc1|h265)']",
    "vp9": r"[vcodec~='^(vp0?9)']",
    "av1": r"[vcodec~='^av01']",
}
AUDIO_CODEC_FILTERS = {
    "aac": r"[acodec~='^(mp4a|aac)']",
    "opus": r"[acodec~='^opus']",
    "mp3": r"[acodec~='^mp3']",
    "vorbis": r"[acodec~='^vorbis']",
}

SPONSORBLOCK_CATEGORIES = [
    "sponsor", "intro", "outro", "selfpromo", "preview",
    "filler", "interaction", "music_offtopic",
]


# ----------------------------------------------------------------------------
# Binary discovery
# ----------------------------------------------------------------------------
def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """Folder holding the running app - the .exe's folder when frozen."""
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """PyInstaller's extraction folder, or the app folder when running from source."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else app_dir()


def _sidecar(name: str) -> str:
    """Look for a helper binary next to the exe, then inside the bundle."""
    for base in (app_dir(), bundle_dir()):
        candidate = base / name
        if candidate.exists():
            return str(candidate)
    return ""


def find_ytdlp(explicit: str = "") -> str:
    """Return a usable path to yt-dlp, or '' if none was found.

    An installed copy wins over the bundled one so winget/pip updates take
    effect; the bundled copy is the fallback on machines without yt-dlp.
    """
    if explicit and Path(explicit).exists():
        return explicit

    found = shutil.which("yt-dlp")
    if found:
        return found

    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
        Path.home(),
    ]
    for base in candidates:
        if not base.exists():
            continue
        try:
            for hit in base.glob("**/yt-dlp.exe"):
                return str(hit)
        except OSError:
            continue

    return _sidecar("yt-dlp.exe")


def find_ffmpeg() -> str:
    """Prefer an ffmpeg sitting beside the exe, then fall back to PATH."""
    return _sidecar("ffmpeg.exe") or shutil.which("ffmpeg") or ""


def probe_version(binary: str) -> str:
    if not binary:
        return ""
    try:
        out = subprocess.run(
            [binary, "--version"], capture_output=True, text=True,
            timeout=20, creationflags=CREATE_NO_WINDOW,
        )
        return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def split_args(text: str) -> list[str]:
    """Split a user-supplied extra-args string without mangling Windows paths."""
    if not text.strip():
        return []
    try:
        parts = shlex.split(text, posix=False)
    except ValueError:
        parts = text.split()
    cleaned = []
    for part in parts:
        if len(part) >= 2 and part[0] == part[-1] and part[0] in "\"'":
            part = part[1:-1]
        cleaned.append(part)
    return cleaned


def build_format_selector(opt: Options) -> str:
    """Translate the format widgets into a yt-dlp -f expression."""
    if opt.custom_format.strip():
        return opt.custom_format.strip()

    if opt.mode == "audio_only":
        afilter = AUDIO_CODEC_FILTERS.get(opt.audio_codec_pref, "")
        if afilter:
            return f"ba{afilter}/ba/b"
        return "ba/b"

    vfilter = ""
    if opt.quality not in ("best", "worst"):
        vfilter += f"[height<={opt.quality}]"
    if opt.fps_cap != "any":
        vfilter += f"[fps<={opt.fps_cap}]"
    vfilter += VIDEO_CODEC_FILTERS.get(opt.video_codec, "")

    if opt.quality == "worst":
        base = "wv*+wa/w" if opt.mode == "video_audio" else "wv*/w"
        return base

    if opt.mode == "video_only":
        chain = [f"bv*{vfilter}"]
        if vfilter:
            chain.append("bv*")
        chain.append("b")
        return "/".join(chain)

    afilter = AUDIO_CODEC_FILTERS.get(opt.audio_codec_pref, "")
    chain = [f"bv*{vfilter}+ba{afilter}"]
    if afilter:
        chain.append(f"bv*{vfilter}+ba")
    if vfilter:
        chain.append("bv*+ba")
        chain.append(f"b{vfilter}")
    chain.append("b")
    # De-duplicate while preserving order.
    seen, ordered = set(), []
    for item in chain:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return "/".join(ordered)


# ----------------------------------------------------------------------------
# Command construction
# ----------------------------------------------------------------------------
def build_args(opt: Options, url: str, *, for_display: bool = False) -> list[str]:
    """Build the full yt-dlp argument list (excluding the binary itself)."""
    a: list[str] = []

    # --- Make the GUI authoritative -------------------------------------
    if opt.ignore_config:
        a.append("--ignore-config")
    a += ["--color", "never", "--encoding", "utf-8", "--newline"]
    if not for_display:
        a += ["--progress-template", PROGRESS_TEMPLATE]
        a += ["--progress-template", POSTPROCESS_TEMPLATE]

    # --- Output ----------------------------------------------------------
    if opt.output_dir.strip():
        a += ["-P", opt.output_dir.strip()]
    if opt.temp_dir.strip():
        a += ["-P", f"temp:{opt.temp_dir.strip()}"]
    if opt.output_template.strip():
        a += ["-o", opt.output_template.strip()]
    if opt.restrict_filenames:
        a.append("--restrict-filenames")
    a.append("--windows-filenames" if opt.windows_filenames else "--no-windows-filenames")
    if opt.trim_filenames > 0:
        a += ["--trim-filenames", str(opt.trim_filenames)]
    if opt.overwrite_mode == "overwrite":
        a.append("--force-overwrites")
    elif opt.overwrite_mode == "skip":
        a += ["--no-overwrites", "--continue"]
    else:
        a.append("--continue")
    if opt.use_archive and opt.archive_file.strip():
        a += ["--download-archive", opt.archive_file.strip()]
    if opt.no_mtime:
        a.append("--no-mtime")

    # --- Format ----------------------------------------------------------
    a += ["-f", build_format_selector(opt)]
    if opt.format_sort.strip():
        a += ["-S", opt.format_sort.strip()]
    if opt.prefer_free_formats:
        a.append("--prefer-free-formats")
    if opt.video_multistreams:
        a.append("--video-multistreams")
    if opt.audio_multistreams:
        a.append("--audio-multistreams")
    if opt.check_formats:
        a.append("--check-formats")

    # --- Clip a time range ------------------------------------------------
    if opt.download_sections.strip():
        a += ["--download-sections", opt.download_sections.strip()]
        if opt.force_keyframes:
            a.append("--force-keyframes-at-cuts")

    if opt.mode == "audio_only":
        a.append("-x")
        if opt.audio_format != "best":
            a += ["--audio-format", opt.audio_format]
        if opt.audio_quality.strip():
            a += ["--audio-quality", opt.audio_quality.strip()]
        if opt.keep_video:
            a.append("-k")
    else:
        if opt.merge_container != "default":
            a += ["--merge-output-format", opt.merge_container]
        if opt.remux_to != "none":
            a += ["--remux-video", opt.remux_to]
        if opt.recode_to != "none":
            a += ["--recode-video", opt.recode_to]

    # --- Subtitles -------------------------------------------------------
    if opt.write_subs:
        a.append("--write-subs")
    if opt.auto_subs:
        a.append("--write-auto-subs")
    if opt.embed_subs:
        a.append("--embed-subs")
    wants_subs = opt.write_subs or opt.auto_subs or opt.embed_subs
    if wants_subs:
        if opt.sub_langs.strip():
            a += ["--sub-langs", opt.sub_langs.strip()]
        if opt.sub_format.strip() and opt.sub_format != "best":
            a += ["--sub-format", f"{opt.sub_format}/best"]
        if opt.convert_subs != "none":
            a += ["--convert-subs", opt.convert_subs]

    # --- Metadata --------------------------------------------------------
    if opt.embed_thumbnail:
        a.append("--embed-thumbnail")
    if opt.write_thumbnail:
        a.append("--write-thumbnail")
    if opt.embed_metadata:
        a.append("--embed-metadata")
    if opt.embed_chapters:
        a.append("--embed-chapters")
    if opt.write_info_json:
        a.append("--write-info-json")
    if opt.write_description:
        a.append("--write-description")
    if opt.write_comments:
        a.append("--write-comments")
    if opt.split_chapters:
        a.append("--split-chapters")
    if opt.xattrs:
        a.append("--xattrs")
    if opt.convert_thumbnails != "none":
        a += ["--convert-thumbnails", opt.convert_thumbnails]
    if opt.clean_info_json:
        a.append("--clean-info-json")
    if opt.embed_info_json:
        a.append("--embed-info-json")
    if opt.remove_chapters.strip():
        for pattern in opt.remove_chapters.splitlines():
            if pattern.strip():
                a += ["--remove-chapters", pattern.strip()]
    for line in opt.parse_metadata.splitlines():
        if line.strip():
            a += ["--parse-metadata", line.strip()]
    for line in opt.replace_in_metadata.splitlines():
        parts = split_args(line)
        if len(parts) >= 3:
            a += ["--replace-in-metadata", *parts[:3]]

    # --- SponsorBlock ----------------------------------------------------
    if opt.sb_remove:
        a += ["--sponsorblock-remove", ",".join(opt.sb_remove)]
    if opt.sb_mark:
        a += ["--sponsorblock-mark", ",".join(opt.sb_mark)]
    if (opt.sb_remove or opt.sb_mark) and opt.sponsorblock_chapter_title.strip():
        a += ["--sponsorblock-chapter-title", opt.sponsorblock_chapter_title.strip()]

    # --- Playlist --------------------------------------------------------
    if opt.playlist_mode == "single":
        a.append("--no-playlist")
    elif opt.playlist_mode == "playlist":
        a.append("--yes-playlist")
    if opt.playlist_items.strip():
        a += ["-I", opt.playlist_items.strip()]
    if opt.playlist_reverse:
        a.append("--playlist-reverse")
    if opt.playlist_random:
        a.append("--playlist-random")
    if opt.max_downloads > 0:
        a += ["--max-downloads", str(opt.max_downloads)]
    if opt.date_after.strip():
        a += ["--dateafter", opt.date_after.strip()]
    if opt.date_before.strip():
        a += ["--datebefore", opt.date_before.strip()]
    if opt.match_filter.strip():
        a += ["--match-filters", opt.match_filter.strip()]
    if opt.break_on_existing:
        a.append("--break-on-existing")
    if opt.lazy_playlist:
        a.append("--lazy-playlist")
    if opt.write_playlist_metafiles:
        a.append("--write-playlist-metafiles")
    if opt.mark_watched:
        a.append("--mark-watched")
    if opt.min_filesize.strip():
        a += ["--min-filesize", opt.min_filesize.strip()]
    if opt.max_filesize.strip():
        a += ["--max-filesize", opt.max_filesize.strip()]
    if opt.age_limit.strip():
        a += ["--age-limit", opt.age_limit.strip()]

    # --- Livestreams ------------------------------------------------------
    if opt.live_from_start:
        a.append("--live-from-start")
    if opt.wait_for_video.strip():
        a += ["--wait-for-video", opt.wait_for_video.strip()]

    # --- Network ---------------------------------------------------------
    if opt.rate_limit.strip():
        a += ["-r", opt.rate_limit.strip()]
    if opt.concurrent_fragments > 1:
        a += ["-N", str(opt.concurrent_fragments)]
    if opt.retries.strip():
        a += ["-R", opt.retries.strip()]
    if opt.fragment_retries.strip():
        a += ["--fragment-retries", opt.fragment_retries.strip()]
    if opt.socket_timeout.strip():
        a += ["--socket-timeout", opt.socket_timeout.strip()]
    if opt.proxy.strip():
        a += ["--proxy", opt.proxy.strip()]
    if opt.force_ip == "4":
        a.append("-4")
    elif opt.force_ip == "6":
        a.append("-6")
    if opt.downloader != "native":
        a += ["--downloader", opt.downloader]
    if opt.downloader_args.strip():
        a += ["--downloader-args", opt.downloader_args.strip()]
    if opt.sleep_interval.strip():
        a += ["--sleep-interval", opt.sleep_interval.strip()]
    if opt.max_sleep_interval.strip():
        a += ["--max-sleep-interval", opt.max_sleep_interval.strip()]
    if opt.sleep_requests.strip():
        a += ["--sleep-requests", opt.sleep_requests.strip()]
    if opt.throttled_rate.strip():
        a += ["--throttled-rate", opt.throttled_rate.strip()]
    if opt.http_chunk_size.strip():
        a += ["--http-chunk-size", opt.http_chunk_size.strip()]
    if opt.buffer_size.strip():
        a += ["--buffer-size", opt.buffer_size.strip()]
    if opt.retry_sleep.strip():
        a += ["--retry-sleep", opt.retry_sleep.strip()]
    if opt.file_access_retries.strip():
        a += ["--file-access-retries", opt.file_access_retries.strip()]
    if opt.no_part:
        a.append("--no-part")
    if opt.keep_fragments:
        a.append("--keep-fragments")
    if opt.abort_on_unavailable_fragment:
        a.append("--abort-on-unavailable-fragment")
    if opt.no_check_certificate:
        a.append("--no-check-certificates")
    if opt.legacy_server_connect:
        a.append("--legacy-server-connect")
    if opt.hls_use_mpegts:
        a.append("--hls-use-mpegts")

    # --- Auth / access ---------------------------------------------------
    if opt.cookies_mode == "browser" and opt.cookies_browser:
        spec = opt.cookies_browser
        if opt.cookies_profile.strip():
            spec += f":{opt.cookies_profile.strip()}"
        a += ["--cookies-from-browser", spec]
    elif opt.cookies_mode == "file" and opt.cookies_file.strip():
        a += ["--cookies", opt.cookies_file.strip()]
    if opt.netrc:
        a.append("--netrc")
    if opt.username.strip():
        a += ["-u", opt.username.strip()]
    if opt.password:
        a += ["-p", "********" if for_display else opt.password]
    if opt.twofactor:
        a += ["-2", "******" if for_display else opt.twofactor]
    if opt.user_agent.strip():
        a += ["--add-header", f"User-Agent:{opt.user_agent.strip()}"]
    if opt.referer.strip():
        a += ["--add-header", f"Referer:{opt.referer.strip()}"]
    for line in opt.extra_headers.splitlines():
        line = line.strip()
        if line and ":" in line:
            a += ["--add-header", line]
    if opt.geo_bypass_country.strip():
        a += ["--geo-bypass-country", opt.geo_bypass_country.strip()]

    # --- Advanced --------------------------------------------------------
    # An ffmpeg placed next to the exe wins unless one was set explicitly.
    ffmpeg = opt.ffmpeg_location.strip() or _sidecar("ffmpeg.exe")
    if ffmpeg:
        a += ["--ffmpeg-location", ffmpeg]
    for line in opt.extractor_args.splitlines():
        if line.strip():
            a += ["--extractor-args", line.strip()]
    if opt.postprocessor_args.strip():
        a += ["--postprocessor-args", opt.postprocessor_args.strip()]
    if opt.exec_cmd.strip():
        a += ["--exec", opt.exec_cmd.strip()]
    if opt.no_cache:
        a.append("--no-cache-dir")
    if opt.ignore_errors:
        a.append("-i")
    if opt.verbose:
        a.append("-v")
    if opt.simulate:
        a.append("-s")
    a += split_args(opt.extra_args)

    a.append(url)
    return a


def build_probe_args(opt: Options, url: str) -> list[str]:
    """Arguments for fetching metadata/formats as JSON (no download)."""
    a: list[str] = []
    if opt.ignore_config:
        a.append("--ignore-config")
    a += ["--color", "never", "--encoding", "utf-8", "-J", "--no-warnings"]
    if opt.playlist_mode != "playlist":
        a.append("--no-playlist")
    if opt.cookies_mode == "browser" and opt.cookies_browser:
        spec = opt.cookies_browser
        if opt.cookies_profile.strip():
            spec += f":{opt.cookies_profile.strip()}"
        a += ["--cookies-from-browser", spec]
    elif opt.cookies_mode == "file" and opt.cookies_file.strip():
        a += ["--cookies", opt.cookies_file.strip()]
    if opt.proxy.strip():
        a += ["--proxy", opt.proxy.strip()]
    a.append(url)
    return a


def format_command(binary: str, args: list[str]) -> str:
    """Render a copy-pasteable command line for display."""
    def quote(token: str) -> str:
        return f'"{token}"' if (" " in token or "\t" in token) else token

    return " ".join(quote(t) for t in [binary, *args])
