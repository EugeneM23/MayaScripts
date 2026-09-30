# Graph Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A mode (alt+c, and a hub section) that lays Maya's own Graph Editor exactly on the viewport with its background removed, every click and key still the Graph Editor's, alt+mouse the camera.

**Architecture:** A Graph Editor panel of ours in a frameless host, chrome hidden, its canvas aligned pixel for pixel on the viewport and made invisible with a layered alpha of 1 (the GHOST, which still renders and takes clicks); a click-through translucent window (the GLASS) on the same rectangle showing the ghost's `grabFramebuffer()` frames with the flat background keyed out; a 30 ms alt poll making the ghost click-through while alt is held.

**Tech Stack:** Maya 2027 `cmds`, PySide6 6.8.3 (QtWidgets, QtOpenGL), numpy (Maya's), ctypes user32/opengl32, stdlib unittest under mayapy.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-30-graph-overlay-design.md`.
- `keying.py` and `geometry.py` import neither Maya nor Qt; `winstyle.py` imports neither; `glass.py` never imports `maya.cmds` (subprocess-tested).
- `SOFT` = 28 levels, `BANDS` = 4, `SAMPLE_STEP` = 7, `GHOST_ALPHA` = 1, follow timer 100 ms, alt poll 30 ms, minimum 15 ms between keyed frames.
- Names: panel `skeldarGraphOverlayPanel`, host `skeldarGraphOverlayHost`, glass `skeldarGraphOverlayGlass`, status `skeldarGraphOverlayStatus`, button `skeldarGraphOverlayButton`, hub section key `graphoverlay`, hotkey row `graph.overlay` on alt+c, `DEFAULT_KEYS_VERSION` 6.
- Nothing of the animator's preferences is written (the background colour is read off the picture). No window of ours is ever topmost.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .` from the repo root (no system Python).

---

### Task 1: The pure core — keying and geometry

**Files:**
- Create: `SkeldarAnim/maya_graphoverlay/__init__.py`, `SkeldarAnim/maya_graphoverlay/keying.py`, `SkeldarAnim/maya_graphoverlay/geometry.py`
- Test: `tests/test_graphoverlay_keying.py`, `tests/test_graphoverlay_geometry.py`

**Interfaces:**
- Produces: `keying.alpha_table(soft=SOFT) -> np.ndarray[256] uint8`; `keying.make_pool(workers=BANDS) -> ThreadPoolExecutor`; `keying.background(bgra, step=SAMPLE_STEP) -> (r, g, b)`; `keying.key_out(bgra, key_rgb, table, pool=None, bands=BANDS) -> np.ndarray (h, w, 4) uint8`. `geometry.usable(rect) -> bool`; `geometry.host_rect(target, host, canvas) -> (x, y, w, h)`; `geometry.let_through(alt_down, maya_active, placed) -> bool`; `geometry.due_in(now, last, min_interval) -> float`.

- [ ] **Step 1: Write the failing tests**

`tests/test_graphoverlay_keying.py`:

```python
"""The Graph Editor's picture with its flat background taken out."""

import os
import subprocess
import sys
import unittest

import numpy as np

from maya_graphoverlay import keying

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def frame(height=6, width=8, rgb=(64, 64, 64)):
    bgra = np.zeros((height, width, 4), np.uint8)
    bgra[..., 0], bgra[..., 1], bgra[..., 2], bgra[..., 3] = rgb[2], rgb[1], rgb[0], 255
    return bgra


class AlphaTable(unittest.TestCase):

    def test_it_rises_over_soft_levels(self):
        table = keying.alpha_table(28)
        self.assertEqual(table.dtype, np.uint8)
        self.assertEqual(len(table), 256)
        self.assertEqual(table[0], 0)
        self.assertEqual(table[14], 127)
        self.assertEqual(table[28], 255)
        self.assertEqual(table[255], 255)
        self.assertTrue(np.all(np.diff(table.astype(int)) >= 0))


class Background(unittest.TestCase):

    def test_the_commonest_colour_wins(self):
        bgra = frame(40, 40)
        bgra[5:8, :, :3] = (0, 170, 255)          # a curve across it
        self.assertEqual(keying.background(bgra, step=1), (64, 64, 64))

    def test_it_answers_r_g_b_from_b_g_r_bytes(self):
        self.assertEqual(keying.background(frame(rgb=(30, 20, 10)), step=1), (30, 20, 10))


class KeyOut(unittest.TestCase):

    def setUp(self):
        self.table = keying.alpha_table(28)

    def test_the_background_goes_and_its_colour_stays(self):
        out = keying.key_out(frame(), (64, 64, 64), self.table)
        self.assertTrue(np.all(out[..., 3] == 0))
        self.assertTrue(np.all(out[..., :3] == 64))

    def test_a_curve_is_opaque_in_its_own_colour(self):
        bgra = frame()
        bgra[2, 3, :3] = (35, 35, 255)             # red, B G R
        out = keying.key_out(bgra, (64, 64, 64), self.table)
        self.assertEqual(out[2, 3, 3], 255)
        self.assertEqual(tuple(out[2, 3, :3]), (35, 35, 255))

    def test_the_farthest_channel_decides(self):
        bgra = frame()
        bgra[1, 1, :3] = (64, 78, 64)              # 14 levels off in green only
        bgra[1, 2, :3] = (50, 64, 64)              # 14 levels under in blue only
        out = keying.key_out(bgra, (64, 64, 64), self.table)
        self.assertEqual(out[1, 1, 3], 127)
        self.assertEqual(out[1, 2, 3], 127)

    def test_bands_on_threads_give_the_same_picture(self):
        rng = np.random.default_rng(3)
        bgra = rng.integers(0, 256, (37, 23, 4), dtype=np.uint8)
        alone = keying.key_out(bgra, (64, 70, 80), self.table)
        pool = keying.make_pool(4)
        try:
            banded = keying.key_out(bgra, (64, 70, 80), self.table, pool, bands=4)
        finally:
            pool.shutdown()
        self.assertTrue(np.array_equal(alone, banded))

    def test_fewer_rows_than_bands(self):
        pool = keying.make_pool(4)
        try:
            out = keying.key_out(frame(2, 5), (64, 64, 64), self.table, pool, bands=4)
        finally:
            pool.shutdown()
        self.assertEqual(out.shape, (2, 5, 4))

    def test_the_input_is_left_alone(self):
        bgra = frame()
        before = bgra.copy()
        keying.key_out(bgra, (64, 64, 64), self.table)
        self.assertTrue(np.array_equal(bgra, before))


class Purity(unittest.TestCase):

    def test_keying_and_geometry_import_neither_maya_nor_qt(self):
        code = ("import sys; import maya_graphoverlay.keying, maya_graphoverlay.geometry; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'shiboken6')]; "
                "print(bad)")
        result = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stdout.strip(), "[]", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

`tests/test_graphoverlay_geometry.py`:

```python
"""Where the ghost goes, when it lets the mouse through, when a frame is due."""

import unittest

from maya_graphoverlay import geometry


class HostRect(unittest.TestCase):

    def test_the_measured_case_lands_the_canvas_on_the_viewport(self):
        """2026-09-30: host (300, 250, 900, 560), canvas (305, 253, 892, 554),
        viewport (462, 374, 861, 500) - the canvas came out on the viewport."""
        self.assertEqual(geometry.host_rect((462, 374, 861, 500),
                                            (300, 250, 900, 560),
                                            (305, 253, 892, 554)),
                         (457, 371, 869, 506))

    def test_already_aligned_is_a_fixed_point(self):
        host, canvas = (457, 371, 869, 506), (462, 374, 861, 500)
        self.assertEqual(geometry.host_rect(canvas, host, canvas), host)


class Usable(unittest.TestCase):

    def test_a_rectangle_with_area(self):
        self.assertTrue(geometry.usable((0, 0, 10, 10)))

    def test_nothing_or_a_flat_one(self):
        self.assertFalse(geometry.usable(None))
        self.assertFalse(geometry.usable((0, 0, 0, 10)))
        self.assertFalse(geometry.usable((0, 0, 10, 0)))


class LetThrough(unittest.TestCase):

    def test_alt_is_the_camera(self):
        self.assertTrue(geometry.let_through(True, True, True))

    def test_without_alt_the_graph_takes_the_click(self):
        self.assertFalse(geometry.let_through(False, True, True))

    def test_maya_behind_or_no_viewport(self):
        self.assertTrue(geometry.let_through(False, False, True))
        self.assertTrue(geometry.let_through(False, True, False))


class DueIn(unittest.TestCase):

    def test_the_first_frame_is_due_now(self):
        self.assertEqual(geometry.due_in(10.0, None, 0.015), 0.0)

    def test_too_soon_waits_out_the_rest(self):
        self.assertAlmostEqual(geometry.due_in(10.005, 10.0, 0.015), 0.010)

    def test_late_is_now(self):
        self.assertEqual(geometry.due_in(11.0, 10.0, 0.015), 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail** — `mayapy -m unittest tests.test_graphoverlay_keying tests.test_graphoverlay_geometry` → ImportError (no package).

- [ ] **Step 3: Implement**

`SkeldarAnim/maya_graphoverlay/__init__.py`:

```python
"""maya_graphoverlay - Maya's own Graph Editor over the viewport, see-through.

    import maya_graphoverlay; maya_graphoverlay.toggle()      # alt+c in our set

The names are resolved lazily so that importing the package drags in neither
Qt nor numpy nor Maya - the pure halves are tested without any of them.
Spec: docs/superpowers/specs/2026-09-30-graph-overlay-design.md
"""

_EXPORTS = ("toggle", "enable", "disable", "is_on", "show_window",
            "build_panel", "is_open")


def __getattr__(name):
    if name in _EXPORTS:
        from maya_graphoverlay import mode
        return getattr(mode, name)
    raise AttributeError(name)
```

`SkeldarAnim/maya_graphoverlay/keying.py`:

```python
"""The Graph Editor's picture with its flat background taken out. numpy only.

The curve area of Maya 2027's Graph Editor is a QOpenGLWindow that clears
OPAQUE whatever alpha its background colour carries (measured 2026-09-30:
alpha 255 on every pixel at a background alpha of 0). So the transparency
is made here, from the picture: a pixel's alpha is how far it stands from
the background colour, and its colour stays exactly as Maya drew it.

Straight alpha: `alpha = table[max over channels |P - K|]`, the table rising
from 0 to 255 over `SOFT` levels. The background is 0; a curve, a key, a
number, the time marker are opaque; the grid (23 levels off the default
background) about 82 %. An anti-aliased curve pixel keeps the K it was
blended with - which is how the curve looks in the Graph Editor itself.

Speed, measured in Maya's numpy at 1850x1067: lookup tables on every
channel 44.5 ms, this uint8 version 19.7 ms on one thread and 5.7 ms on
four - numpy lets the GIL go, so the bands really run side by side.
"""

from concurrent.futures import ThreadPoolExecutor

import numpy as np

SOFT = 28          # levels off the background at which a pixel is opaque
BANDS = 4          # horizontal bands keyed side by side
SAMPLE_STEP = 7    # every 7th pixel both ways finds the background


def alpha_table(soft=SOFT):
    """Channel distance 0..255 -> alpha 0..255, as uint8."""
    levels = np.arange(256, dtype=np.int32)
    return np.minimum(levels * 255 // max(1, int(soft)), 255).astype(np.uint8)


def make_pool(workers=BANDS):
    """The keying threads. Made once a session by the mode."""
    return ThreadPoolExecutor(max_workers=workers,
                              thread_name_prefix="skeldarGraphKey")


def background(bgra, step=SAMPLE_STEP):
    """The flat background as (r, g, b): the commonest colour of a sparse
    sample.

    Read off the picture rather than a preference, so the classic Graph
    Editor and a colour the animator changed are both right, and nothing
    of theirs is written.
    """
    sample = np.ascontiguousarray(bgra[::step, ::step, :3])
    sample = sample.reshape(-1, 3).astype(np.uint32)
    packed = (sample[:, 2] << 16) | (sample[:, 1] << 8) | sample[:, 0]
    values, counts = np.unique(packed, return_counts=True)
    top = int(values[int(np.argmax(counts))])
    return ((top >> 16) & 255, (top >> 8) & 255, top & 255)


def _band(src, out, key_bgr, table, y0, y1):
    part = src[y0:y1]
    dist = None
    for channel, k in enumerate(key_bgr):
        plane = part[..., channel]
        d = np.maximum(plane, k) - np.minimum(plane, k)
        dist = d if dist is None else np.maximum(dist, d)
    out[y0:y1, :, :3] = part[..., :3]
    out[y0:y1, :, 3] = table[dist]


def key_out(bgra, key_rgb, table, pool=None, bands=BANDS):
    """A copy of `bgra` - (h, w, 4) uint8, the bytes B G R A as QImage's
    ARGB32 lays them out - whose alpha says how far each pixel stands from
    `key_rgb`. The input is not written.
    """
    height = bgra.shape[0]
    out = np.empty(bgra.shape, np.uint8)
    key_bgr = (np.uint8(key_rgb[2]), np.uint8(key_rgb[1]),
               np.uint8(key_rgb[0]))
    if pool is None or bands <= 1 or height < bands:
        _band(bgra, out, key_bgr, table, 0, height)
        return out
    step = -(-height // bands)
    jobs = [pool.submit(_band, bgra, out, key_bgr, table, y,
                        min(height, y + step))
            for y in range(0, height, step)]
    for job in jobs:
        job.result()
    return out
```

`SkeldarAnim/maya_graphoverlay/geometry.py`:

```python
"""Pure rules: where the ghost goes, when it lets the mouse through, when a
frame is due. Stdlib only.

Rectangles are (x, y, width, height) in global pixels - physical ones in
Maya 2027, where Qt's devicePixelRatio is 1.0 (the hub skin measured it).
"""


def usable(rect):
    """A rectangle with an area to lie on."""
    return (rect is not None and len(rect) == 4
            and rect[2] > 0 and rect[3] > 0)


def host_rect(target, host, canvas):
    """Where the host goes so that its canvas lands exactly on `target`.

    The canvas sits in the host at an offset with a border round it -
    measured (5, 3) and 8x6 once the chrome is hidden - read off the host
    as it stands rather than assumed, so a Maya that frames its panels
    another way is still right.
    """
    dx, dy = canvas[0] - host[0], canvas[1] - host[1]
    return (target[0] - dx, target[1] - dy,
            target[2] + (host[2] - canvas[2]),
            target[3] + (host[3] - canvas[3]))


def let_through(alt_down, maya_active, placed):
    """Whether the ghost lets the mouse through to the viewport.

    alt held is the camera (the animator, 2026-09-30: «1, камеры»); with
    Maya not in front, or no viewport to lie on, the graph has no click to
    take.
    """
    return bool(alt_down) or not maya_active or not placed


def due_in(now, last, min_interval):
    """Seconds until the next frame may be keyed; 0 when it may be now."""
    if last is None:
        return 0.0
    return max(0.0, min_interval - (now - last))
```

- [ ] **Step 4: Run them to see them pass** — the same command, all green.
- [ ] **Step 5: Commit** — `feat(graphoverlay): the keyer and the rules, pure`.

### Task 2: The Win32 layer

**Files:**
- Create: `SkeldarAnim/maya_graphoverlay/winstyle.py`
- Test: `tests/test_graphoverlay_winstyle.py`

**Interfaces:**
- Produces: `with_bits(style, on=0, off=0) -> int`; `available() -> bool`; `exstyle(hwnd) -> int`; `make_ghost(hwnd, alpha=GHOST_ALPHA) -> bool`; `layered_alpha(hwnd) -> int | None`; `set_click_through(hwnd, on) -> int`; `is_click_through(hwnd) -> bool`; `alt_down() -> bool`; `window_at(x, y) -> int`; `children(hwnd) -> list[int]`; `gl_kept()` (context manager). Constants `WS_EX_LAYERED`, `WS_EX_TRANSPARENT`, `GHOST_ALPHA`.

- [ ] **Step 1: Write the failing test** `tests/test_graphoverlay_winstyle.py`:

```python
"""The two Win32 styles the overlay stands on."""

import os
import subprocess
import sys
import unittest

from maya_graphoverlay import winstyle

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


class WithBits(unittest.TestCase):

    def test_on_and_off(self):
        style = 0x100
        on = winstyle.with_bits(style, on=winstyle.WS_EX_LAYERED | winstyle.WS_EX_TRANSPARENT)
        self.assertEqual(on, 0x100 | 0x80000 | 0x20)
        self.assertEqual(winstyle.with_bits(on, off=winstyle.WS_EX_TRANSPARENT), 0x100 | 0x80000)

    def test_it_stays_32_bits(self):
        self.assertEqual(winstyle.with_bits(-1, off=0x20), 0xFFFFFFDF)


class OnThisMachine(unittest.TestCase):

    def test_windows_is_here(self):
        self.assertTrue(winstyle.available())

    def test_alt_answers_a_bool(self):
        self.assertIn(winstyle.alt_down(), (True, False))

    def test_the_ghost_is_one_level_of_alpha(self):
        self.assertEqual(winstyle.GHOST_ALPHA, 1)

    def test_gl_kept_is_harmless_with_no_context(self):
        with winstyle.gl_kept():
            pass


class Purity(unittest.TestCase):

    def test_it_imports_neither_maya_nor_qt(self):
        code = ("import sys; import maya_graphoverlay.winstyle; "
                "print([m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'shiboken6')])")
        result = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stdout.strip(), "[]", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to see it fail** (ImportError).
- [ ] **Step 3: Implement** `SkeldarAnim/maya_graphoverlay/winstyle.py`:

```python
"""The Win32 styles the overlay stands on. ctypes only - never Maya, never Qt.

* The GHOST - our Graph Editor made invisible with WS_EX_LAYERED and a
  layered alpha of 1. Measured 2026-09-30: it keeps rendering
  (frameSwapped fires, the time marker moves) and keeps taking clicks
  (WindowFromPoint answers its canvas) - a layered window lets the mouse
  through only where its alpha is ZERO.
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
    user32.SetLayeredWindowAttributes.argtypes = [wt.HWND, wt.DWORD,
                                                  ctypes.c_ubyte, wt.DWORD]
    user32.SetLayeredWindowAttributes.restype = wt.BOOL
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


def available():
    return _user32() is not None


def _hwnd(hwnd):
    from ctypes import wintypes as wt
    return wt.HWND(int(hwnd))


def exstyle(hwnd):
    user32 = _user32()
    if user32 is None:
        return 0
    return int(user32.GetWindowLongPtrW(_hwnd(hwnd), GWL_EXSTYLE)) & 0xFFFFFFFF


def _write(hwnd, style):
    user32 = _user32()
    from ctypes import wintypes as wt
    handle = _hwnd(hwnd)
    user32.SetWindowLongPtrW(handle, GWL_EXSTYLE, style)
    user32.SetWindowPos(handle, wt.HWND(0), 0, 0, 0, 0, _SWP_REFRESH)


def make_ghost(hwnd, alpha=GHOST_ALPHA):
    """Layered, at `alpha` of 255: drawn at next to nothing, clicks taken."""
    user32 = _user32()
    if user32 is None:
        return False
    style = exstyle(hwnd)
    if not style & WS_EX_LAYERED:
        _write(hwnd, with_bits(style, on=WS_EX_LAYERED))
    return bool(user32.SetLayeredWindowAttributes(_hwnd(hwnd), 0,
                                                  int(alpha), LWA_ALPHA))


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

    def visit(handle, _):
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
```

- [ ] **Step 4: Run it to see it pass.**
- [ ] **Step 5: Commit** — `feat(graphoverlay): the ghost and click-through styles, ctypes only`.

### Task 3: The Maya and Qt halves — viewport, ghost, glass

**Files:**
- Create: `SkeldarAnim/maya_graphoverlay/viewport.py`, `SkeldarAnim/maya_graphoverlay/ghost.py`, `SkeldarAnim/maya_graphoverlay/glass.py`
- Test: `tests/test_graphoverlay_glass.py` (purity + the frame it holds, offscreen)

**Interfaces:**
- Consumes: `geometry.host_rect`, `winstyle.make_ghost`, `winstyle.set_click_through`.
- Produces: `viewport.model_panels()`, `viewport.active_panel()`, `viewport.visible(panel) -> bool`, `viewport.gl_rect(panel) -> rect | None`, `viewport.maya_main_window() -> QWidget | None`, `viewport.maya_active() -> bool`. `ghost.Ghost(parent, rect)` with `.panel`, `.host`, `.hwnd()`, `.canvas() -> QOpenGLWindow | None`, `.canvas_rect()`, `.host_rect()`, `.place(rect)`, `.aligned(rect)`, `.grab() -> QImage | None`, `.alive()`, `.hide_chrome()`, `.destroy()`; `ghost.delete_leftovers()`; constants `PANEL`, `HOST`. `glass.Glass(parent)` with `.place(rect)`, `.set_frame(bgra)`, `.frame() -> QImage | None`, `.paint_count`, `.close_glass()`; `glass.NAME`.

- [ ] **Step 1: Write the failing test** `tests/test_graphoverlay_glass.py`:

```python
"""The see-through window: Qt only, never Maya."""

import os
import subprocess
import sys
import unittest

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


class Purity(unittest.TestCase):

    def test_the_glass_never_imports_maya_cmds(self):
        code = ("import os, sys; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; "
                "import maya_graphoverlay.glass; "
                "print('maya.cmds' in sys.modules)")
        result = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stdout.strip().splitlines()[-1:], ["False"], result.stderr)


class TheFrame(unittest.TestCase):

    def test_it_holds_the_array_and_shows_it_as_argb32(self):
        code = ("import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; "
                "import numpy as np; from PySide6 import QtWidgets, QtGui; "
                "app = QtWidgets.QApplication([]); "
                "from maya_graphoverlay import glass; g = glass.Glass(); "
                "a = np.zeros((3, 4, 4), np.uint8); a[1, 2] = (35, 35, 255, 255); "
                "g.set_frame(a); im = g.frame(); c = im.pixelColor(2, 1); "
                "print(im.width(), im.height(), im.format() == QtGui.QImage.Format_ARGB32, "
                "c.red(), c.green(), c.blue(), c.alpha(), im.pixelColor(0, 0).alpha(), g.objectName())")
        result = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stdout.strip().splitlines()[-1:],
                         ["4 3 True 255 35 35 255 0 skeldarGraphOverlayGlass"], result.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to see it fail.**
- [ ] **Step 3: Implement the three modules.**

`SkeldarAnim/maya_graphoverlay/viewport.py`:

```python
"""Where the viewport is, right now. cmds, with Qt imported inside.

From the Curve Overlay (archive/maya_curveview/viewport.py, measured
2026-09-05), with one change the hub skin paid for (trap 96): the rectangle
is read while the panel's wrapper is held, never through a child wrapper
handed out of the function - one handed out read "already deleted" a call
later on 2026-09-30.
"""

import maya.cmds as cmds

GL_CLASS = "QmayaGLWidget"     # the model panel's native GL surface


def _type_of(panel):
    try:
        return cmds.getPanel(typeOf=panel) or ""
    except Exception:                                         # noqa: BLE001
        return ""


def model_panels():
    """Every visible model panel, in Maya's own order."""
    visible = cmds.getPanel(visiblePanels=True) or []
    return [panel for panel in visible if _type_of(panel) == "modelPanel"]


def visible(panel):
    return bool(panel) and panel in model_panels()


def active_panel():
    """The focused model panel, else the first visible one, else None."""
    panels = model_panels()
    if not panels:
        return None
    try:
        focus = cmds.getPanel(withFocus=True)
    except Exception:                                         # noqa: BLE001
        focus = None
    return focus if focus in panels else panels[0]


def maya_main_window():
    """Maya's main window as a QWidget, or None: what our windows are owned
    by, so they ride its z-order and hide with it."""
    try:
        from maya import OpenMayaUI as omui
        from PySide6 import QtWidgets
        from shiboken6 import wrapInstance
    except ImportError:
        return None
    pointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(pointer), QtWidgets.QWidget) if pointer else None


def gl_rect(panel):
    """The panel's GL surface as (x, y, width, height) in global pixels."""
    if not panel:
        return None
    try:
        from maya import OpenMayaUI as omui
        from PySide6 import QtCore, QtWidgets
        from shiboken6 import wrapInstance
    except ImportError:
        return None
    pointer = omui.MQtUtil.findControl(panel)
    if not pointer:
        return None
    holder = wrapInstance(int(pointer), QtWidgets.QWidget)
    for child in holder.findChildren(QtWidgets.QWidget):
        try:
            if (child.metaObject().className() != GL_CLASS
                    or not child.isVisible()):
                continue
            corner = child.mapToGlobal(QtCore.QPoint(0, 0))
            return (corner.x(), corner.y(), child.width(), child.height())
        except RuntimeError:                  # a widget Maya deleted mid-walk
            continue
    return None


def maya_active():
    """Whether a Maya window is the active window."""
    try:
        from PySide6 import QtWidgets
        return QtWidgets.QApplication.activeWindow() is not None
    except (ImportError, RuntimeError):
        return True
```

`SkeldarAnim/maya_graphoverlay/ghost.py`:

```python
"""Our own Graph Editor: invisible, its curve area exactly on the viewport.

A `scriptedPanel` of type graphEditor inside a frameless Qt host of ours
(the hub skin's `cmds.setParent(fullName(layout))`), never the animator's
graphEditor1 - their Graph Editor stays where they docked it. Measured
2026-09-30 on this very construction:

- the curve area is `TanimCurveCanvas`, a QOpenGLWindow named
  `<panel>GraphEdImpl` inside a QWindowContainer - a native child HWND;
- the menu bar goes with `menuBarVisible=False`, the toolbar is the panel's
  one frameLayout (the parent of its `QadskFrameLayoutFrame`) unmanaged,
  the channel list the QSplitter's other side sized 0, handle width 0;
- then the canvas sits (5, 3) into the host with 8x6 of border, and the
  host placed by `geometry.host_rect` puts it on the viewport pixel for
  pixel.

PySide hands the canvas back as a QPaintDeviceWindow; the cached wrapper is
invalidated and the pointer wrapped as the QOpenGLWindow it is, which is
what reaches `grabFramebuffer()` and `frameSwapped`.
"""

import maya.cmds as cmds
from maya import OpenMayaUI as omui
from PySide6 import QtCore, QtGui, QtOpenGL, QtWidgets
import shiboken6

from maya_graphoverlay import geometry, winstyle

PANEL = "skeldarGraphOverlayPanel"
HOST = "skeldarGraphOverlayHost"
LAYOUT = "skeldarGraphOverlayLayout"
PANE = "skeldarGraphOverlayPane"
LABEL = "Graph Overlay"
CANVAS_CLASS = "TanimCurveCanvas"
CONTAINER_CLASS = "QWindowContainer"
FRAME_CLASS = "QadskFrameLayoutFrame"


def _full_name(qobject):
    return omui.MQtUtil.fullName(int(shiboken6.getCppPointer(qobject)[0]))


def _widget(name):
    pointer = omui.MQtUtil.findControl(name)
    return shiboken6.wrapInstance(int(pointer), QtWidgets.QWidget) \
        if pointer else None


def delete_leftovers():
    """A panel of ours a saved scene brought back; a host an older module
    object built (an install purges modules, not widgets - trap 102)."""
    try:
        if cmds.scriptedPanel(PANEL, exists=True):
            cmds.deleteUI(PANEL, panel=True)
    except Exception:                                         # noqa: BLE001
        pass
    app = QtWidgets.QApplication.instance()
    for widget in (app.topLevelWidgets() if app else []):
        try:
            if widget.objectName() == HOST:
                widget.hide()
                widget.deleteLater()
        except RuntimeError:
            continue


class Ghost(object):
    """The panel, its host, and the canvas wrapper, held together."""

    def __init__(self, parent, rect):
        delete_leftovers()
        host = QtWidgets.QWidget(parent, QtCore.Qt.Tool
                                 | QtCore.Qt.FramelessWindowHint)
        host.setObjectName(HOST)
        host.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        layout = QtWidgets.QVBoxLayout(host)
        layout.setObjectName(LAYOUT)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.host, self.layout = host, layout
        self._canvas = None
        host.setGeometry(*[int(v) for v in rect])
        # Invisible before it is ever shown: no frame of a grey Graph
        # Editor flashes over the viewport.
        winstyle.make_ghost(int(host.winId()))
        host.show()
        previous = cmds.setParent(query=True)
        cmds.setParent(_full_name(layout))
        pane = cmds.paneLayout(PANE, configuration="single")
        self.panel = cmds.scriptedPanel(PANEL, type="graphEditor",
                                        label=LABEL, parent=pane)
        try:
            cmds.setParent(previous)
        except Exception:                                     # noqa: BLE001
            pass
        self.hide_chrome()

    # ------------------------------------------------------------ the chrome

    def hide_chrome(self):
        """Menu bar, toolbar and channel list out; idempotent."""
        try:
            if cmds.scriptedPanel(self.panel, query=True,
                                  menuBarVisible=True):
                cmds.scriptedPanel(self.panel, edit=True,
                                   menuBarVisible=False)
        except Exception:                                     # noqa: BLE001
            pass
        panel_widget = _widget(self.panel)
        if panel_widget is None:
            return
        for frame in panel_widget.findChildren(QtWidgets.QWidget):
            try:
                if frame.metaObject().className() != FRAME_CLASS:
                    continue
                name = _full_name(frame.parentWidget())
            except RuntimeError:
                continue
            if cmds.frameLayout(name, exists=True) and \
                    cmds.frameLayout(name, query=True, manage=True):
                cmds.frameLayout(name, edit=True, manage=False)
        port = _widget(self.panel + "GraphEd")
        split = port.parentWidget() if port is not None else None
        if isinstance(split, QtWidgets.QSplitter):
            if split.handleWidth():
                split.setHandleWidth(0)
            index, sizes = split.indexOf(port), split.sizes()
            wanted = [sum(sizes) if i == index else 0
                      for i in range(len(sizes))]
            if sizes != wanted:
                split.setSizes(wanted)

    # ------------------------------------------------------------ the canvas

    def canvas(self):
        """The curve area as a QOpenGLWindow, or None."""
        if self._canvas is not None:
            try:
                self._canvas.objectName()
                return self._canvas
            except RuntimeError:
                self._canvas = None
        wanted = self.panel + "GraphEdImpl"
        for window in QtGui.QGuiApplication.allWindows():
            try:
                if window.objectName() != wanted or \
                        window.metaObject().className() != CANVAS_CLASS:
                    continue
                pointer = shiboken6.getCppPointer(window)[0]
            except RuntimeError:
                continue
            shiboken6.invalidate(window)
            self._canvas = shiboken6.wrapInstance(int(pointer),
                                                  QtOpenGL.QOpenGLWindow)
            return self._canvas
        return None

    def canvas_rect(self):
        port = _widget(self.panel + "GraphEd")
        if port is None:
            return None
        for child in port.children():
            try:
                if isinstance(child, QtWidgets.QWidget) and \
                        child.metaObject().className() == CONTAINER_CLASS:
                    corner = child.mapToGlobal(QtCore.QPoint(0, 0))
                    return (corner.x(), corner.y(), child.width(),
                            child.height())
            except RuntimeError:
                continue
        return None

    def grab(self):
        canvas = self.canvas()
        return canvas.grabFramebuffer() if canvas is not None else None

    # --------------------------------------------------------------- the host

    def hwnd(self):
        return int(self.host.winId())

    def host_rect(self):
        g = self.host.geometry()
        return (g.x(), g.y(), g.width(), g.height())

    def place(self, target):
        """Move the host so its canvas lands on `target` (converges in the
        next layout pass when the size changed)."""
        self.hide_chrome()
        canvas = self.canvas_rect()
        if canvas is None:
            self.host.setGeometry(*[int(v) for v in target])
            return
        wanted = geometry.host_rect(target, self.host_rect(), canvas)
        if wanted != self.host_rect():
            self.host.setGeometry(*wanted)

    def aligned(self, target):
        return self.canvas_rect() == tuple(target)

    def alive(self):
        try:
            self.host.objectName()
            return bool(cmds.scriptedPanel(self.panel, exists=True))
        except (RuntimeError, Exception):                     # noqa: BLE001
            return False

    def destroy(self):
        self._canvas = None
        try:
            if cmds.scriptedPanel(self.panel, exists=True):
                cmds.deleteUI(self.panel, panel=True)
        except Exception:                                     # noqa: BLE001
            pass
        try:
            self.host.hide()
            self.host.deleteLater()
        except RuntimeError:
            pass
```

`SkeldarAnim/maya_graphoverlay/glass.py`:

```python
"""The see-through window: the ghost's picture, background taken out.

Qt and ctypes - never Maya. The Curve Overlay's measured window
(2026-09-05): frameless, translucent, a TOP-LEVEL (a native GL child would
paint over any child of ours), owned by Maya's main window so it rides its
z-order; WA_TransparentForMouseEvents does not cross a native window, so
the click-through is WS_EX_TRANSPARENT, set after `show()`.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from maya_graphoverlay import winstyle

NAME = "skeldarGraphOverlayGlass"


class Glass(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(Glass, self).__init__(parent, QtCore.Qt.Tool
                                    | QtCore.Qt.FramelessWindowHint)
        self.setObjectName(NAME)
        for attribute in (QtCore.Qt.WA_TranslucentBackground,
                          QtCore.Qt.WA_NoSystemBackground,
                          QtCore.Qt.WA_TransparentForMouseEvents,
                          QtCore.Qt.WA_ShowWithoutActivating):
            self.setAttribute(attribute, True)
        self.setAutoFillBackground(False)
        self._image = None
        self._buffer = None
        self.paint_count = 0

    def place(self, rect):
        """Geometry, then show, then the style - that order (re-showing
        recreates the native window and drops the style)."""
        self.setGeometry(*[int(v) for v in rect])
        if not self.isVisible():
            self.show()
        winstyle.set_click_through(int(self.winId()), True)

    def set_frame(self, bgra):
        """Show `bgra`: (h, w, 4) uint8, B G R A, straight alpha. The array
        is held - the image reads it in place."""
        height, width = bgra.shape[:2]
        self._buffer = bgra
        self._image = QtGui.QImage(bgra.data, width, height, width * 4,
                                   QtGui.QImage.Format_ARGB32)
        self.update()

    def frame(self):
        return self._image

    def paintEvent(self, event):
        self.paint_count += 1
        if self._image is None:
            return
        painter = QtGui.QPainter(self)
        try:
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
            painter.drawImage(0, 0, self._image)
        finally:
            painter.end()

    def close_glass(self):
        try:
            self.hide()
            self._image = None
            self._buffer = None
            self.deleteLater()
        except RuntimeError:
            pass
```

- [ ] **Step 4: Run the glass tests to see them pass.**
- [ ] **Step 5: Commit** — `feat(graphoverlay): the viewport, the ghost panel and the glass`.

### Task 4: The mode and its hub section

**Files:**
- Create: `SkeldarAnim/maya_graphoverlay/mode.py`
- Test: `tests/test_graphoverlay_mode.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `mode.enable() -> str`, `mode.disable() -> str`, `mode.toggle() -> str`, `mode.is_on() -> bool`, `mode.is_open() -> bool`, `mode.show_window()`, `mode.build_panel() -> str`, `mode.button_label() -> str`, `mode.HUB_SECTION = "graphoverlay"`, `mode.STATUS`, `mode.BUTTON`, `mode.HINT`; internals the verify drives: `mode._STATE`, `mode._update()`, `mode._follow()`, `mode._poll_alt(alt=None)`.

- [ ] **Step 1: Write the failing test** `tests/test_graphoverlay_mode.py`:

```python
"""The mode's refusals, its toggle and its hub section, on fakes."""

import unittest
from unittest import mock

from tests.uifakes import FakeUiCmds

from maya_graphoverlay import mode, viewport, winstyle


class Refusals(unittest.TestCase):

    def setUp(self):
        mode._STATE.reset()

    def test_off_when_already_off(self):
        self.assertEqual(mode.disable(), "Graph Overlay is already off")

    def test_no_windows_no_overlay(self):
        with mock.patch.object(winstyle, "available", return_value=False):
            self.assertEqual(mode.enable(), "Graph Overlay needs Windows")
        self.assertFalse(mode.is_on())

    def test_no_viewport_no_overlay(self):
        with mock.patch.object(winstyle, "available", return_value=True), \
                mock.patch.object(viewport, "active_panel", return_value=None), \
                mock.patch.object(viewport, "gl_rect", return_value=None):
            self.assertEqual(mode.enable(), "Graph Overlay: no viewport to lie on")
        self.assertFalse(mode.is_on())


class HubSection(unittest.TestCase):

    def setUp(self):
        mode._STATE.reset()
        self.fake = FakeUiCmds()
        self.real = mode.cmds
        mode.cmds = self.fake

    def tearDown(self):
        mode.cmds = self.real

    def test_it_builds_a_hint_the_button_and_the_status(self):
        mode.build_panel()
        made = [(name, args) for name, args, _kw in self.fake.calls]
        self.assertIn(("button", (mode.BUTTON,)), made)
        self.assertIn(("text", (mode.STATUS,)), made)

    def test_the_button_says_the_state(self):
        self.assertEqual(mode.button_label(), "Graph Overlay: OFF")
        mode._STATE.ghost = object()
        try:
            self.assertEqual(mode.button_label(), "Graph Overlay: ON")
        finally:
            mode._STATE.reset()

    def test_the_section_key(self):
        self.assertEqual(mode.HUB_SECTION, "graphoverlay")


class TheHint(unittest.TestCase):

    def test_it_names_the_camera_and_the_key(self):
        self.assertIn("alt+mouse: camera", mode.HINT)
        self.assertIn("alt+c", mode.HINT)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to see it fail.**
- [ ] **Step 3: Implement** `SkeldarAnim/maya_graphoverlay/mode.py`:

```python
"""Graph Overlay: Maya's own Graph Editor over the viewport, background out.

The animator (2026-09-30): «мне нужен граф эдитор с прозрачным фоном» -
shape Б, a mode on a key, the curve area on the whole viewport; alt+mouse
is the camera. Maya's drawing cannot be made transparent (the canvas
clears opaque whatever the background alpha, measured), so:

- the GHOST (`ghost.py`): a Graph Editor panel of ours, chrome hidden, its
  canvas on the viewport pixel for pixel, invisible at a layered alpha of 1
  - it still renders and takes every click and key;
- the GLASS (`glass.py`): a click-through translucent window on the same
  rectangle showing the ghost's frames with the flat background keyed out
  (`keying.py`) - grabbed on every `frameSwapped`, coalesced, at most every
  `MIN_UPDATE_S`;
- a 30 ms alt poll: held, the ghost lets the mouse through to the viewport
  and Maya's camera takes it; released, the graph takes it again;
- a 10 Hz follow timer: the viewport moved, the two follow it; Maya behind
  another program or no viewport, the glass hides and the ghost lets
  clicks through; our panel gone, the mode ends.

    import maya_graphoverlay; maya_graphoverlay.toggle()      # alt+c

Spec: docs/superpowers/specs/2026-09-30-graph-overlay-design.md
"""

import time
import traceback

import maya.cmds as cmds

import maya_hubstyle as hubstyle
from maya_graphoverlay import geometry

HUB_SECTION = "graphoverlay"
STATUS = "skeldarGraphOverlayStatus"
BUTTON = "skeldarGraphOverlayButton"

FOLLOW_MS = 100
ALT_MS = 30
MIN_UPDATE_S = 0.015

HINT = "alt+mouse: camera  |  F / A: frame the graph  |  alt+c: leave"
PANEL_HINT = "The Graph Editor over the viewport, see-through (alt+c)"
PANEL_NOTE = ("Maya's own Graph Editor lies on the viewport with its "
              "background taken out: every click and key is the Graph "
              "Editor's. Hold alt for the camera; select objects in the "
              "outliner or the channel box, or leave the mode.")


class _State(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.ghost = None
        self.glass = None
        self.canvas = None
        self.model_panel = None
        self.timers = []
        self.jobs = []
        self.rect = None
        self.placed = False
        self.active = True
        self.through = None
        self.key = None
        self.table = None
        self.pending = False
        self.last = None
        self.frames = 0
        self.cost = 0.0
        self.closing = False


_STATE = _State()
_POOL = []          # the keying threads, made once a session


# ------------------------------------------------------------------ the mode

def is_on():
    return _STATE.ghost is not None


def enable():
    if is_on():
        return "Graph Overlay is already on"
    from maya_graphoverlay import viewport, winstyle
    if not winstyle.available():
        return "Graph Overlay needs Windows"
    panel = viewport.active_panel()
    rect = viewport.gl_rect(panel)
    if not geometry.usable(rect):
        return "Graph Overlay: no viewport to lie on"
    from maya_graphoverlay import ghost, glass, keying
    parent = viewport.maya_main_window()
    try:
        _STATE.model_panel = panel
        _STATE.ghost = ghost.Ghost(parent, rect)
        _STATE.glass = glass.Glass(parent)
        _STATE.glass.place(rect)
        _STATE.rect, _STATE.placed = rect, True
        _STATE.table = keying.alpha_table()
        if not _POOL:
            _POOL.append(keying.make_pool())
        _connect_canvas()
        _start_timers()
        _install_jobs()
    except Exception:
        traceback.print_exc()
        disable()
        raise
    return "Graph Overlay ON  -  " + HINT


def disable():
    if not is_on():
        return "Graph Overlay is already off"
    _STATE.closing = True
    try:
        _stop_timers()
        _kill_jobs()
        canvas = _STATE.canvas
        if canvas is not None:
            try:
                canvas.frameSwapped.disconnect(_on_swap)
            except (RuntimeError, TypeError):
                pass
        if _STATE.glass is not None:
            _STATE.glass.close_glass()
        if _STATE.ghost is not None:
            _STATE.ghost.destroy()
    finally:
        _STATE.reset()
    return "Graph Overlay OFF"


def toggle():
    return _show(disable() if is_on() else enable())


# ------------------------------------------------------------- the pipeline

def _connect_canvas():
    canvas = _STATE.ghost.canvas() if _STATE.ghost is not None else None
    if canvas is None:
        return
    canvas.frameSwapped.connect(_on_swap)
    _STATE.canvas = canvas
    _on_swap()


def _on_swap():
    """The graph drew a frame: key it now, or as soon as it is due."""
    if not is_on() or _STATE.pending:
        return
    _STATE.pending = True
    from PySide6 import QtCore
    delay = geometry.due_in(time.perf_counter(), _STATE.last, MIN_UPDATE_S)
    QtCore.QTimer.singleShot(int(round(delay * 1000)), _update)


def _update():
    _STATE.pending = False
    if not is_on() or not _STATE.placed or _STATE.closing:
        return
    started = time.perf_counter()
    try:
        import numpy as np
        from maya_graphoverlay import keying, winstyle
        with winstyle.gl_kept():
            image = _STATE.ghost.grab()
        if image is None or image.isNull():
            return
        width, height = image.width(), image.height()
        pixels = np.frombuffer(image.constBits(), np.uint8).reshape(
            height, image.bytesPerLine() // 4, 4)[:, :width]
        if _STATE.key is None:
            _STATE.key = keying.background(pixels)
        _STATE.glass.set_frame(keying.key_out(
            pixels, _STATE.key, _STATE.table, _POOL[0] if _POOL else None))
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()
        return
    _STATE.last = time.perf_counter()
    _STATE.frames += 1
    _STATE.cost = _STATE.last - started


# ---------------------------------------------------------------- following

def _start_timers():
    from PySide6 import QtCore
    for interval, slot in ((FOLLOW_MS, _follow), (ALT_MS, _alt_tick)):
        timer = QtCore.QTimer()
        timer.setInterval(interval)
        timer.timeout.connect(slot)
        timer.start()
        _STATE.timers.append(timer)


def _stop_timers():
    for timer in _STATE.timers:
        try:
            timer.stop()
            timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass
    _STATE.timers = []


def _follow():
    if not is_on() or _STATE.closing:
        return
    try:
        _follow_once()
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()


def _follow_once():
    from maya_graphoverlay import viewport, winstyle
    ghost_, glass_ = _STATE.ghost, _STATE.glass
    if not ghost_.alive():
        _show(disable() + " - its Graph Editor panel was deleted")
        return
    if not viewport.visible(_STATE.model_panel):
        _STATE.model_panel = viewport.active_panel()
    rect = viewport.gl_rect(_STATE.model_panel)
    _STATE.active = viewport.maya_active()
    _STATE.placed = geometry.usable(rect)
    if not (_STATE.active and _STATE.placed):
        if glass_.isVisible():
            glass_.hide()
    else:
        if rect != _STATE.rect or not glass_.isVisible():
            _STATE.rect = rect
            glass_.place(rect)
        if not ghost_.aligned(rect):
            ghost_.place(rect)
    if winstyle.layered_alpha(ghost_.hwnd()) != winstyle.GHOST_ALPHA:
        winstyle.make_ghost(ghost_.hwnd())
        _STATE.through = None
    if _STATE.canvas is None:
        _connect_canvas()
    _poll_alt()


def _alt_tick():
    try:
        _poll_alt()
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()


def _poll_alt(alt=None):
    if not is_on() or _STATE.closing:
        return
    from maya_graphoverlay import winstyle
    if alt is None:
        alt = winstyle.alt_down()
    through = geometry.let_through(alt, _STATE.active, _STATE.placed)
    if through != _STATE.through:
        winstyle.set_click_through(_STATE.ghost.hwnd(), through)
        _STATE.through = through


def _install_jobs():
    for event in ("SceneOpened", "NewSceneOpened"):
        try:
            _STATE.jobs.append(cmds.scriptJob(event=[event, _on_scene],
                                              killWithScene=False))
        except Exception:                                     # noqa: BLE001
            pass


def _kill_jobs():
    for job in _STATE.jobs:
        try:
            cmds.scriptJob(kill=job, force=True)
        except Exception:                                     # noqa: BLE001
            pass
    _STATE.jobs = []


def _on_scene():
    """A scene's UI configuration may delete panels: leave cleanly first."""
    if is_on() and not _STATE.closing:
        cmds.evalDeferred(lambda: _show(disable() + " - a scene was opened")
                          if is_on() else None)


# --------------------------------------------------------------- the section

def button_label():
    return "Graph Overlay: ON" if is_on() else "Graph Overlay: OFF"


def _paint_button():
    try:
        if cmds.control(BUTTON, exists=True):
            cmds.button(BUTTON, edit=True, label=button_label())
    except Exception:                                         # noqa: BLE001
        pass


def _show(text):
    """The first line on the section's status line and in the viewport, the
    whole of it in the Script Editor."""
    print(text)
    first = text.splitlines()[0] if text.strip() else ""
    try:
        if cmds.control(STATUS, exists=True):
            cmds.text(STATUS, edit=True, label=first)
    except Exception:                                         # noqa: BLE001
        pass
    _paint_button()
    try:
        cmds.inViewMessage(assistMessage=first, position="midCenterTop",
                           fade=True)
    except Exception:                                         # noqa: BLE001
        pass
    return text


def _press(*_args):
    try:
        return toggle()
    except Exception as exc:                                  # noqa: BLE001
        _show("%s: %s" % (type(exc).__name__, exc))
        raise


def is_open():
    return bool(cmds.control(STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on this section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def build_panel():
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(label=PANEL_HINT, align="left", wordWrap=True,
                            height=36), "note")
    hubstyle.mark(cmds.button(BUTTON, label=button_label(), height=34,
                              backgroundColor=(0.45, 0.60, 0.70),
                              annotation=PANEL_NOTE, command=_press),
                  "primary", "chart-line")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    return column
```

- [ ] **Step 4: Run it to see it pass.**
- [ ] **Step 5: Commit** — `feat(graphoverlay): the mode - ghost, glass, alt, follow; the hub section`.

### Task 5: Wiring — hub, icon, hotkey, payload

**Files:**
- Modify: `SkeldarAnim/maya_hub.py` (a Section after retarget), `SkeldarAnim/maya_hubicons.py` (`chart-line`), `SkeldarAnim/maya_hotkeys.py` (row, DEFAULT_KEYS, RELEASED_KEYS, version 6), `SkeldarAnim/install.py` (payload row)
- Test: `tests/test_hub.py`, `tests/test_hotkeys.py`, `tests/test_install.py`

- [ ] **Step 1: Update the tests first** — `test_hub.py`: the card list gains `"graphoverlay"` after `"retarget"`; the module map gains `"graphoverlay": ("maya_graphoverlay.mode", "build_panel")`. `test_hotkeys.py`: DEFAULT_KEYS table gains `("c", "graph.overlay")`; the version test asserts `>= 6`; RELEASED_KEYS table is `[("4", "time.insert"), ("5", "time.remove")]`; the alt+c release test becomes "alt+c is ours again: bound to the Graph Overlay, not released"; add a test that `graph.overlay` is a row whose action is the package's toggle. `test_install.py`: `maya_graphoverlay` ships.

```python
    # test_install.py, class Payload
    def test_the_graph_overlay_ships(self):
        self.assertIn("maya_graphoverlay", install.payload())
```

```python
    # test_hotkeys.py, class ReleasedKeys - replaces the alt+c release test
    def test_alt_c_is_ours_again(self):
        """Given back with the Curve Overlay on 2026-09-08, taken again for
        the Graph Overlay on 2026-09-30 - the same idea, the same key."""
        self.assertNotIn("c", [key for key, _m, _r in maya_hotkeys.RELEASED_KEYS])
        self.assertIn(("c", "graph.overlay"),
                      [(key, row) for key, _m, row in maya_hotkeys.DEFAULT_KEYS])
        maya_hotkeys.bind_defaults()
        self.assertEqual(self.fake.bindings[("c", True)],
                         maya_hotkeys.name_command("graph.overlay"))

    def test_the_overlay_row(self):
        found = maya_hotkeys.row("graph.overlay")
        self.assertIsNotNone(found)
        self.assertEqual(found[1], "Editors")
```

- [ ] **Step 2: Run them to see them fail.**
- [ ] **Step 3: Implement**

`maya_hub.py`, after the retarget Section:

```python
    #  2026-09-30: Maya's own Graph Editor over the viewport, see-through.
    Section("graphoverlay", "Graph Overlay", "maya_graphoverlay.mode",
            "build_panel", "skeldarHubFrameGraphOverlay",
            "animation", "chart-line"),
```

`maya_hubicons.py`, a Tabler outline icon (MIT, like the rest):

```python
    "chart-line": (                       # the Graph Overlay (2026-09-30)
        "M4 19l16 0",
        "M4 15l4 -6l4 2l4 -5l4 4",
    ),
```

`maya_hotkeys.py`: in DEFAULT_KEYS add `("c", {"altModifier": True}, "graph.overlay"),`; remove the `("c", ..., "window.curveview")` row from RELEASED_KEYS; `DEFAULT_KEYS_VERSION = 6`; comments say why; in `_OURS` after `editor.outliner`:

```python
    ("graph.overlay", "Editors", "Graph Overlay",
     "Maya's Graph Editor over the viewport with its background taken out; "
     "alt+mouse is the camera. The same key leaves it",
     partial(_show, "maya_graphoverlay", "toggle")),
```

`install.py` payload, after `maya_rig_retarget.py`: `"maya_graphoverlay",           # the Graph Editor over the viewport (2026-09-30)`.

- [ ] **Step 4: Run the whole suite** — all green.
- [ ] **Step 5: Commit** — `feat(graphoverlay): a hub section, alt+c, the payload`.

### Task 6: The live proof

**Files:**
- Create: `docs/superpowers/plans/verify_graphoverlay.py`

A phased script (the phase name read from a file beside it, one send per phase, because the Qt event loop must turn between them — trap 68) run in a disposable Maya on port 7003 with a scratch `MAYA_APP_DIR`, the repo's `SkeldarAnim` first on `sys.path`, never the animator's scene. Phases and gates:

1. `setup` — Home screen hidden, main window shown (trap 105), Manny's skeleton imported, a cube keyed on tx/ty/rz, the cube selected, playback 1..24, `maya_graphoverlay.enable()`.
2. `placed` — gate 1 the ghost's layered alpha is 1; gate 2 its canvas rect equals the viewport GL rect; gate 3 the glass rect equals it too; gate 4 the glass is click-through; gate 5 at least one frame keyed; gate 6 the glass's image is the canvas size and its corner alpha is 0 (background out) while some pixel is opaque (the curves in).
3. `time` — `currentTime(12)`; next phase gate 7: the glass's time-marker column moved.
4. `click` — the pixel of the key at frame 12 found in the glass image (orange); `QTest.mouseClick` on the canvas QWindow there; gate 8 `keyframe(q, selected)` holds that key.
5. `alt` — `_poll_alt(alt=True)`: gate 9 ghost click-through; with the ghost made transiently topmost (it is invisible), gate 10 `window_at` at the canvas centre is not the canvas; `_poll_alt(alt=False)`: gate 11 not click-through and `window_at` is the canvas.
6. `cost` — gate 12 `_update()` timed over 10 runs at the viewport's size, reported (under 40 ms).
7. `look` — the glass image composited over a playblast of the viewport, saved to the scratchpad (the picture for the animator).
8. `leave` — `disable()`: gate 13 no host, no glass, no panel, no timers; gate 14 `modernGraphEditorBackground` as before the run.

- [ ] Run it phase by phase, fix until every gate is green, keep the picture.
- [ ] Commit — `test(graphoverlay): the live proof`.

### Task 7: Hand-off

- [ ] Refresh the animator's installed copy over port 7001 (`install.install(quiet=True)` from the repo, `install` purged first) if the port listens; else say so.
- [ ] CLAUDE.md: a section «Graph Overlay: Maya's own Graph Editor over the viewport (2026-09-30)» with the measured facts, the proof and its numbers, any trap met.
- [ ] Memory: update `maya-graph-editor-canvas-transparency.md` with what the build learned.
- [ ] Commit — `docs: the Graph Overlay - proofs and notes`.
