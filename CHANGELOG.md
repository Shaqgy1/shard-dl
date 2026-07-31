# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.0.2] - 2026-07-31

### Fixed

- The packaged `Shard.exe` was always running its bundled (build-time) copy
  of yt-dlp, silently ignoring a newer installed one. Root cause:
  PyInstaller's onefile bootloader prepends its own extraction folder
  (`_MEIPASS`) to the process's `PATH` so bundled DLLs can be found - and
  since the bundled `yt-dlp.exe` sits in that same folder, `shutil.which
  ("yt-dlp")` found it before ever checking for a real install, completely
  inverting the intended "installed wins over bundled" precedence.
  `find_ytdlp()` now discards a `shutil.which()` hit that resolves inside
  the app's own extraction directory.
- A related, independent robustness bug in the same function: the
  installed-copy search used `Path.glob("**/...")`, which aborts its
  *entire* walk the moment any single subdirectory raises `OSError` -
  and `%LOCALAPPDATA%\Microsoft\WinGet\Packages` routinely holds dozens of
  unrelated apps, any one of which can be transiently locked by antivirus
  scanning. Replaced with a manual walk that skips a bad subdirectory
  instead of abandoning the search.
- The status bar and title bar now say `(bundled)` when Shard is running
  the copy embedded in the exe rather than an installed one, so a mismatch
  like this no longer fails silently.

## [1.0.1] - 2026-07-31

### Fixed

- The window is now manageable by tiling window managers (komorebi,
  GlazeWM, and similar). `Qt.FramelessWindowHint` produced a `WS_POPUP`
  window on Windows - the same style used by tooltips and splash screens -
  so Shard was invisible to WM window enumeration entirely, not merely
  excluded. The custom titlebar is now achieved by keeping a normal
  `WS_OVERLAPPEDWINDOW` style and hiding the native chrome purely visually
  via `WM_NCCALCSIZE`, the same technique Windows Terminal uses. See
  `shard/win32_chrome.py`.
- Maximizing no longer overhangs the screen edge by the (now invisible)
  resize border, a standard side effect of the above technique.
- Win11's rounded window corners are now disabled, so the window sits flush
  against tiled neighbours instead of leaving visible corner gaps.

## [1.0.0] - 2026-07-30

First public release.

### Added

- Ten option sections covering the yt-dlp surface: format selection, audio
  extraction, subtitles, metadata, SponsorBlock, playlists, networking,
  cookies and authentication, and raw flag passthrough
- Download queue with configurable concurrency, per-row progress, speed and
  ETA, pause/resume via `--continue`, retry, and drag-and-drop links
- Clip a time range with `--download-sections`, with optional frame-accurate
  cuts
- Livestream capture — from the start, or waiting for a scheduled stream
- Format explorer that probes a URL and lists every available stream
- Command preview showing the exact yt-dlp invocation
- Presets: six built in, plus save/delete and a startup preset
- Seven themes with live switching, adjustable font, size, density and corner
  radius; all icons drawn at runtime so they recolour with the palette
- Frameless window with an integrated 40px title bar, OS-delegated move and
  resize, and system tray support
- Preferences: window behaviour, queue behaviour, clipboard watching,
  notifications, logging to file, binary overrides, export/import, reset
- Portable single-file build with yt-dlp bundled as a fallback

### Notes

- Shard passes `--ignore-config` by default so the GUI is the single source of
  truth for every setting
- Passwords and 2FA codes are kept in memory for the session only and are never
  written to the settings file
