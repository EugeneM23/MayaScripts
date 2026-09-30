"""The Win32 styles the overlay stands on. ctypes only - never Maya, never Qt.

* The GHOST - our Graph Editor at a layered alpha of 1 (set by Qt's own
  `setWindowOpacity` in ghost.py; Qt drops a WS_EX_LAYERED it did not set,
  measured). It keeps rendering (frameSwapped fires, the time marker
  moves) and keeps taking clicks (WindowFromPoint answers its canvas) - a
  layered window lets the mouse through only where its alpha is ZERO.
  `layered_alpha` is how the mode checks it.
* CLICK-THROUGH - WS_EX_TRANSPARENT on a layered window: the OS hit-tests
  straight through it (the Curve Overlay measured it, 2026-09-05). The
  glass carries it for good; the ghost while alt is held, so the click
  reaches the viewport and Maya's camera.

`argtypes`/`restype` are declared because a handle truncates on 64-bit
otherwise (CLAUDE.md trap 26). Off Windows everything answers something
harmless and `available()` is False.
"""

import contextlib
import ctypes

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
LWA_ALPHA = 0x00000002
VK_MENU = 0x12
GHOST_ALPHA = 1
# NOSIZE | NOMOVE | NOZORDER | NOACTIVATE | FRAMECHANGED
_SWP_REFRESH = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020

_LIBS = {}


def with_bits(style, on=0, off=0):
    """`style` with the `on` bits set and the `off` bits cleared, 32 bits."""
    return ((int(style) | on) & ~off) & 0xFFFFFFFF


def _user32():
    if "user32" in _LIBS:
        return _LIBS["user32"]
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        from ctypes import wintypes as wt
    except (AttributeError, OSError, ImportError):
        _LIBS["user32"] = None
        return None
    user32.GetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_longlong
    user32.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int,
                                         ctypes.c_longlong]
    user32.SetWindowLongPtrW.restype = ctypes.c_longlong
    user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_uint]
    user32.SetWindowPos.restype = wt.BOOL
    user32.GetLayeredWindowAttributes.argtypes = [
        wt.HWND, ctypes.POINTER(wt.DWORD), ctypes.POINTER(ctypes.c_ubyte),
        ctypes.POINTER(wt.DWORD)]
    user32.GetLayeredWindowAttributes.restype = wt.BOOL
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.WindowFromPoint.argtypes = [wt.POINT]
    user32.WindowFromPoint.restype = wt.HWND
    _LIBS["user32"] = user32
    return user32


def _opengl32():
    if "opengl32" in _LIBS:
        return _LIBS["opengl32"]
    try:
        gl = ctypes.WinDLL("opengl32")
        from ctypes import wintypes as wt
    except (AttributeError, OSError, ImportError):
        _LIBS["opengl32"] = None
        return None
    gl.wglGetCurrentContext.restype = wt.HANDLE
    gl.wglGetCurrentDC.restype = wt.HDC
    gl.wglMakeCurrent.argtypes = [wt.HDC, wt.HANDLE]
    gl.wglMakeCurrent.restype = wt.BOOL
    _LIBS["opengl32"] = gl
    return gl


def _gdi32():
    if "gdi32" in _LIBS:
        return _LIBS["gdi32"]
    try:
        gdi = ctypes.WinDLL("gdi32")
        from ctypes import wintypes as wt
    except (AttributeError, OSError, ImportError):
        _LIBS["gdi32"] = None
        return None
    gdi.CreateCompatibleDC.argtypes = [wt.HDC]
    gdi.CreateCompatibleDC.restype = wt.HDC
    gdi.CreateDIBSection.argtypes = [wt.HDC, ctypes.c_void_p, wt.UINT,
                                     ctypes.POINTER(ctypes.c_void_p),
                                     wt.HANDLE, wt.DWORD]
    gdi.CreateDIBSection.restype = wt.HBITMAP
    gdi.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
    gdi.SelectObject.restype = wt.HGDIOBJ
    gdi.DeleteObject.argtypes = [wt.HGDIOBJ]
    gdi.DeleteDC.argtypes = [wt.HDC]
    _LIBS["gdi32"] = gdi
    return gdi


PW_RENDERFULLCONTENT = 0x00000002


def capture(hwnd, width, height):
    """The window's own pixels as B G R x bytes (top row first), or None.

    From DWM's copy of the window (`PrintWindow` with PW_RENDERFULLCONTENT):
    nothing of the application's paint code runs, where `QWidget.grab()`
    re-renders every widget - and re-rendering Maya's channel list right
    after its panel was re-parented crashed Maya (measured 2026-09-30, an
    access violation in SharedUI/ufe reached through shiboken). The fourth
    byte is not an alpha: read the bytes as RGB32.
    """
    user32, gdi = _user32(), _gdi32()
    if user32 is None or gdi is None or width <= 0 or height <= 0:
        return None
    from ctypes import wintypes as wt

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                    ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                    ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                    ("biClrImportant", wt.DWORD)]

    user32.GetDC.argtypes = [wt.HWND]
    user32.GetDC.restype = wt.HDC
    user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
    user32.PrintWindow.argtypes = [wt.HWND, wt.HDC, wt.UINT]
    user32.PrintWindow.restype = wt.BOOL
    header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), int(width),
                              -int(height), 1, 32, 0, 0, 0, 0, 0, 0)
    screen = user32.GetDC(None)
    dc = gdi.CreateCompatibleDC(screen)
    bits = ctypes.c_void_p()
    bitmap = gdi.CreateDIBSection(dc, ctypes.byref(header), 0,
                                  ctypes.byref(bits), None, 0)
    if not bitmap:
        gdi.DeleteDC(dc)
        user32.ReleaseDC(None, screen)
        return None
    old = gdi.SelectObject(dc, bitmap)
    try:
        if not user32.PrintWindow(_hwnd(hwnd), dc, PW_RENDERFULLCONTENT):
            return None
        return ctypes.string_at(bits, int(width) * int(height) * 4)
    finally:
        gdi.SelectObject(dc, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(dc)
        user32.ReleaseDC(None, screen)


def available():
    return _user32() is not None


def _hwnd(hwnd):
    from ctypes import wintypes as wt
    return wt.HWND(int(hwnd))


def exstyle(hwnd):
    user32 = _user32()
    if user32 is None:
        return 0
    return int(user32.GetWindowLongPtrW(_hwnd(hwnd), GWL_EXSTYLE)) \
        & 0xFFFFFFFF


def _write(hwnd, style):
    user32 = _user32()
    from ctypes import wintypes as wt
    handle = _hwnd(hwnd)
    user32.SetWindowLongPtrW(handle, GWL_EXSTYLE, style)
    user32.SetWindowPos(handle, wt.HWND(0), 0, 0, 0, 0, _SWP_REFRESH)


def layered_alpha(hwnd):
    """The window's layered alpha, or None when it is not layered by alpha."""
    user32 = _user32()
    if user32 is None or not exstyle(hwnd) & WS_EX_LAYERED:
        return None
    from ctypes import wintypes as wt
    key, alpha, flags = wt.DWORD(), ctypes.c_ubyte(), wt.DWORD()
    if not user32.GetLayeredWindowAttributes(_hwnd(hwnd), ctypes.byref(key),
                                             ctypes.byref(alpha),
                                             ctypes.byref(flags)):
        return None
    return int(alpha.value) if flags.value & LWA_ALPHA else None


def set_click_through(hwnd, on):
    """WS_EX_TRANSPARENT on (with LAYERED) or off. The style it ends with."""
    if _user32() is None:
        return 0
    style = exstyle(hwnd)
    if on:
        wanted = with_bits(style, on=WS_EX_LAYERED | WS_EX_TRANSPARENT)
    else:
        wanted = with_bits(style, off=WS_EX_TRANSPARENT)
    if wanted != style:
        _write(hwnd, wanted)
    return exstyle(hwnd)


def is_click_through(hwnd):
    style = exstyle(hwnd)
    return bool(style & WS_EX_LAYERED) and bool(style & WS_EX_TRANSPARENT)


def alt_down():
    """Whether alt is held right now, whoever has the keyboard."""
    user32 = _user32()
    if user32 is None:
        return False
    return bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)


def window_at(x, y):
    """The window a click at (x, y) would reach - for the live proof."""
    user32 = _user32()
    if user32 is None:
        return 0
    from ctypes import wintypes as wt
    return int(user32.WindowFromPoint(wt.POINT(int(x), int(y))) or 0)


def children(hwnd):
    """Every native child window of `hwnd`."""
    user32 = _user32()
    if user32 is None:
        return []
    from ctypes import wintypes as wt
    found = []
    proto = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def visit(handle, _param):
        found.append(int(handle))
        return True

    user32.EnumChildWindows(_hwnd(hwnd), proto(visit), 0)
    return found


@contextlib.contextmanager
def gl_kept():
    """Whatever OpenGL context was current comes back afterwards.

    `grabFramebuffer` makes the Graph Editor's context current and leaves
    it so; Maya's own GL code may expect what it had. WGL is what Qt and
    Maya both stand on, so this restores either.
    """
    gl = _opengl32()
    if gl is None:
        yield
        return
    context, dc = gl.wglGetCurrentContext(), gl.wglGetCurrentDC()
    try:
        yield
    finally:
        try:
            gl.wglMakeCurrent(dc, context)
        except Exception:                                     # noqa: BLE001
            pass
