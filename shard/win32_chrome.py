"""Native Win32 chrome plumbing.

Qt's Qt.FramelessWindowHint produces a WS_POPUP window on Windows - the same
style used by tooltips, splash screens and dropdown menus. Tiling window
managers (komorebi, GlazeWM, ...) filter their window list on GWL_STYLE and
routinely skip WS_POPUP windows for exactly that reason, so a frameless Qt
app is invisible to them by default: it never appears in the layout at all,
not even as a floating or ignored window.

The fix is the same one Windows Terminal and most native "custom titlebar"
Win32 apps use: keep the window's real style as a normal WS_OVERLAPPEDWINDOW
(WS_CAPTION | WS_THICKFRAME | ...) so the OS and any window manager treat it
as an ordinary resizable top-level window, and hide the native titlebar
purely *visually* by collapsing the non-client area to nothing on
WM_NCCALCSIZE. Everything already drawn (TitleBar, resize grips) keeps
working unchanged, because the client area then simply covers the whole
window - there is no separate "frame" region left for Windows to paint.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"

WM_NCCALCSIZE = 0x0083

_SM_CXSIZEFRAME = 32
_SM_CYSIZEFRAME = 33
_SM_CXPADDEDBORDER = 92

_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWC_DONOTROUND = 1

if IS_WINDOWS:
    _user32 = ctypes.windll.user32

    class _NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]


def parse_message(message_ptr) -> "wintypes.MSG | None":
    """Turn the raw pointer PySide6 hands nativeEvent() into a Win32 MSG."""
    if not IS_WINDOWS:
        return None
    return wintypes.MSG.from_address(int(message_ptr))


def filter_nc_calcsize(is_maximized: bool, lparam: int) -> None:
    """Handle WM_NCCALCSIZE: claim the entire window rect as client area.

    When maximized, Windows still proposes a rect that overhangs the work
    area by the (now invisible) resize border, so content clips past the
    screen edge unless we inset by that border - a well-known quirk of
    this technique, most visibly documented in Windows Terminal's source.
    """
    if not IS_WINDOWS or not is_maximized:
        return
    params = ctypes.cast(lparam, ctypes.POINTER(_NCCALCSIZE_PARAMS)).contents
    cx = _user32.GetSystemMetrics(_SM_CXSIZEFRAME) + _user32.GetSystemMetrics(_SM_CXPADDEDBORDER)
    cy = _user32.GetSystemMetrics(_SM_CYSIZEFRAME) + _user32.GetSystemMetrics(_SM_CXPADDEDBORDER)
    rect = params.rgrc[0]
    rect.left += cx
    rect.right -= cx
    rect.top += cy
    rect.bottom -= cy
    params.rgrc[0] = rect


def disable_rounded_corners(hwnd: int) -> None:
    """Square off Win11's default corner rounding.

    Rounded corners leave visible triangular gaps where the window meets
    its tiled neighbours edge-to-edge - harmless standalone, but wrong once
    the window is actually being tiled, which is the whole point of this
    module. No-ops silently on Windows 10 or older, where the attribute
    does not exist.
    """
    if not IS_WINDOWS or not hwnd:
        return
    value = ctypes.c_int(_DWMWC_DONOTROUND)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(value), ctypes.sizeof(value))
