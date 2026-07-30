# Third-party notices

Shard is original work released under the [MIT License](LICENSE). It is a
**graphical front-end** — it does not reimplement downloading. All extraction
and downloading is performed by **yt-dlp**, which Shard invokes as an external
process.

---

## yt-dlp

- Project: <https://github.com/yt-dlp/yt-dlp>
- License: **The Unlicense** (public domain dedication)
- Relationship: Shard builds a command line and runs `yt-dlp` as a subprocess.
  Shard is **not** affiliated with, endorsed by, or maintained by the yt-dlp
  project.
- Distribution: the packaged `Shard.exe` embeds a copy of `yt-dlp.exe` as a
  fallback for machines that do not have it installed. An installed yt-dlp
  always takes precedence, so updates from winget/pip keep taking effect.

yt-dlp is itself a fork of `youtube-dl`, which is also released into the public
domain under the Unlicense.

## Qt / PySide6

- Project: <https://www.qt.io/> · <https://pypi.org/project/PySide6/>
- License: **LGPL v3** (also available commercially from The Qt Company)
- Relationship: Shard's interface is built with PySide6.

When Shard is installed from source with `pip`, Qt is a normal dynamically
linked dependency and the LGPL's relinking requirement is satisfied in the
usual way.

The **single-file `Shard.exe`** produced by PyInstaller embeds Qt. Distributing
that binary carries the LGPL obligation to let recipients relink it against a
modified Qt. Publishing the full source and the PyInstaller spec — as this
repository does — is the customary way that obligation is met. If you plan to
redistribute the binary yourself, confirm this for your own situation rather
than relying on this file.

## FFmpeg

- Project: <https://ffmpeg.org/>
- License: **LGPL v2.1+** or **GPL v2+**, depending on how the binary was built
- Relationship: **not bundled.** Shard calls whichever `ffmpeg` the user already
  has on `PATH`, or one placed next to the executable. Shard never ships it.

FFmpeg is required for merging separate video and audio streams and for audio
conversion.

---

## Trademarks and content

Shard is a tool. It does not host, index, or provide access to any media. What
you download with it, and whether you have the right to do so, is your
responsibility — respect the terms of service of the sites you use and the
copyright of the material you access.

"YouTube" and other site names appear only to describe compatibility and are
trademarks of their respective owners.
