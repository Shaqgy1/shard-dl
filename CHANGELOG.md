# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

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
