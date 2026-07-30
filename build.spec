# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a portable single-file Shard.exe."""

import os
import shutil
from pathlib import Path

PROJECT = Path(SPECPATH)  # noqa: F821 - injected by PyInstaller


def locate_ytdlp() -> str:
    """Bundle a copy of yt-dlp so the exe works on machines without it."""
    found = shutil.which("yt-dlp")
    if found:
        return found
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if base.exists():
        for hit in base.glob("**/yt-dlp.exe"):
            return str(hit)
    return ""


ytdlp = locate_ytdlp()
binaries = [(ytdlp, ".")] if ytdlp else []
print(f"[spec] bundling yt-dlp from: {ytdlp or 'NOT FOUND - exe will rely on the host system'}")

# Qt ships far more than this app touches; dropping the unused modules keeps
# the one-file exe small and its startup extraction fast.
EXCLUDES = [
    "tkinter", "numpy", "PIL", "matplotlib", "scipy", "pandas", "pytest",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
    "PySide6.QtWebSockets", "PySide6.Qt3DCore", "PySide6.Qt3DRender",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras", "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtDesigner", "PySide6.QtUiTools",
    "PySide6.QtHelp", "PySide6.QtTest", "PySide6.QtSql", "PySide6.QtBluetooth",
    "PySide6.QtNfc", "PySide6.QtSerialPort", "PySide6.QtSerialBus",
    "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtTextToSpeech",
    "PySide6.QtSpatialAudio", "PySide6.QtScxml", "PySide6.QtSensors",
    "PySide6.QtRemoteObjects", "PySide6.QtStateMachine", "PySide6.QtOpenGLWidgets",
]

a = Analysis(  # noqa: F821
    ["main.py"],
    pathex=[str(PROJECT)],
    binaries=binaries,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Shard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX trips antivirus heuristics more often than it saves space
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT / "assets" / "icon.ico"),
)
