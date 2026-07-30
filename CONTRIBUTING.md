# Contributing to Shard

Thanks for taking a look. Issues and pull requests are both welcome.

## Reporting a bug

Open an issue with:

- What you did, what you expected, what happened instead
- The output of **Preview command** (`Ctrl+K`) — this is usually the fastest
  route to a diagnosis, since it shows the exact yt-dlp invocation
- The relevant lines from the log pane
- Your Shard version, yt-dlp version (shown in the title bar), and Windows build

If a download fails, please check whether the same command works when pasted
straight into a terminal. If it fails there too, the bug likely belongs to
[yt-dlp](https://github.com/yt-dlp/yt-dlp/issues) rather than Shard.

## Development setup

```bash
git clone https://github.com/Shaqgy1/shard-dl.git
cd shard-dl
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

## Architecture in one minute

```
options_panel.py  widgets  ->  config.Options   (a dataclass, one field per flag)
config.Options    ->  ytdlp.build_args()        (the only place flags are emitted)
build_args()      ->  worker.DownloadJob        (a QProcess per URL)
DownloadJob       ->  main_window               (signals drive the table and log)
```

Three rules keep it maintainable:

1. **`ytdlp.py` is the single source of truth for command-line flags.** No other
   module builds arguments.
2. **`config.py` holds no UI code, `options_panel.py` holds no yt-dlp
   knowledge.** They meet through field names.
3. **Themes are data.** `theme.py` exposes palettes and one stylesheet
   generator; no colour literals belong anywhere else.

## Adding a yt-dlp option

1. Add a field to `Options` in `config.py` with a sensible default.
2. Emit it in `build_args()` in `ytdlp.py`, in the matching section.
3. Bind a widget in `options_panel.py` with `self.bind("field_name", widget)`.

The binding is name-based, so round-tripping to and from JSON works with no
further wiring. Keep checkbox labels **under about 36 characters** — `QCheckBox`
never wraps, and a long label sets the minimum width of the whole panel.

## Style

- Follow the surrounding code: type hints, `from __future__ import annotations`,
  four-space indent, ~92 column soft limit.
- Comment the *why*, not the *what*. Most existing comments mark a non-obvious
  constraint (a Qt quirk, a yt-dlp behaviour) — that is the bar.
- No new runtime dependencies without a good reason. PySide6 is the only one.

## Testing a change

There is no test suite yet. At minimum, before opening a PR:

- Launch the app and switch through all seven themes
- Open every one of the ten sections and confirm nothing clips
- Run a real download end to end
- Check **Preview command** reflects your new option

A contribution that adds real tests would be very welcome.

## Licensing

By contributing you agree that your work is licensed under the
[MIT License](LICENSE) that covers the project.
