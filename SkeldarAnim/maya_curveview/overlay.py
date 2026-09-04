"""The window the curves are drawn on. Qt and ctypes only -- never Maya.

Measured 2026-09-05, and the whole shape of this module follows from it:

* `QmayaGLWidget` is a NATIVE Windows window, and a native child window
  composites above every non-native sibling -- so a child widget cannot
  paint over the viewport at all. Maya's own layout also owns the panel and
  gave a child overlay a height of ZERO, `paintEvent` never running.
* A frameless translucent TOP-LEVEL window does composite, with real alpha
  over live GL.
* Qt's `WA_TransparentForMouseEvents` does NOT pass the mouse through a
  top-level window: it is a Qt-internal routing flag that forwards an event
  to the widget below inside the SAME window, and Qt forwards nothing across
  a native-window boundary. Under the overlay there was no marquee and no
  camera orbit at all.
* `WS_EX_LAYERED | WS_EX_TRANSPARENT` on the window does pass it through,
  and `alt`+LMB then orbits the camera straight through the overlay.

So this window draws and never sees a mouse event. Input arrives in
`tool.py` from an ordinary `cmds.draggerContext`, which is what leaves
`alt`+mouse to the camera in Maya's own event dispatch rather than in ours.
"""

import ctypes
import math
from collections import namedtuple

from PySide6 import QtCore, QtGui, QtWidgets

from maya_curveview import mapping

# One curve as the painter needs it. `frame` is this curve's own Y window --
# the same object as the scene's when the shared axis is in use, its own when
# normalised. `tangents` is {index: (in_angle, out_angle)} and only ever
# holds selected keys.
Drawn = namedtuple("Drawn", "attribute frame samples keys selected tangents")

# `frame` here is the shared X axis (the playback range). `marquee` is a
# pixel rectangle (x0, y0, x1, y1) or None. `normalised` says whether each
# curve carries its own Y window, in which case the value grid is not drawn:
# with one scale per curve a shared value line would be a lie.
Scene = namedtuple("Scene",
                   "frame curves current_time message marquee normalised")
Scene.__new__.__defaults__ = (False,)


def empty_scene(frame=None):
    frame = frame or mapping.Frame(0.0, 1.0, -1.0, 1.0)
    return Scene(frame, [], None, "", None, False)


# --------------------------------------------------------- the Windows part

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
_SWP_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020


def click_through(widget):
    """Let the OS hit-test straight through `widget`. Returns the ex-style.

    Windows only, and a no-op returning 0 anywhere else -- the studio is on
    Windows and the honest failure is "the overlay eats clicks on a Mac",
    not a traceback at import.

    Must be called AFTER `show()`: re-parenting or re-showing recreates the
    native window and the ex-style goes with it.

    `argtypes`/`restype` are declared because a handle silently truncates on
    64-bit otherwise (CLAUDE.md trap 26, from the same ctypes corner).
    """
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    except (AttributeError, OSError):
        return 0
    from ctypes import wintypes
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_longlong
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int,
                                         ctypes.c_longlong]
    user32.SetWindowLongPtrW.restype = ctypes.c_longlong
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                    ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int,
                                    ctypes.c_uint]
    user32.SetWindowPos.restype = wintypes.BOOL

    handle = wintypes.HWND(int(widget.winId()))
    style = user32.GetWindowLongPtrW(handle, GWL_EXSTYLE)
    user32.SetWindowLongPtrW(handle, GWL_EXSTYLE,
                             style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
    user32.SetWindowPos(handle, wintypes.HWND(0), 0, 0, 0, 0, _SWP_FLAGS)
    return int(user32.GetWindowLongPtrW(handle, GWL_EXSTYLE)) & 0xFFFFFFFF


def is_click_through(widget):
    """Whether the ex-style really carries both bits. For the live proof."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    except (AttributeError, OSError):
        return False
    from ctypes import wintypes
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_longlong
    style = user32.GetWindowLongPtrW(
        wintypes.HWND(int(widget.winId())), GWL_EXSTYLE)
    return bool(style & WS_EX_LAYERED) and bool(style & WS_EX_TRANSPARENT)


# ------------------------------------------------------------------ the paint

_GRID = QtGui.QColor(255, 255, 255, 26)
_GRID_TEXT = QtGui.QColor(255, 255, 255, 110)
_TIME = QtGui.QColor(255, 190, 60, 190)
_ZERO = QtGui.QColor(255, 255, 255, 64)
_KEY_EDGE = QtGui.QColor(20, 20, 20, 220)
_KEY_SELECTED = QtGui.QColor(255, 255, 255)
_MESSAGE = QtGui.QColor(255, 255, 255, 200)
_MARQUEE_LINE = QtGui.QColor(255, 255, 255, 200)
_MARQUEE_FILL = QtGui.QColor(255, 255, 255, 26)

KEY_SIZE = 7.0
TANGENT_LENGTH = 48.0


class CurveOverlay(QtWidgets.QWidget):
    """A frameless translucent window that draws a graph and nothing else."""

    def __init__(self, parent=None):
        super(CurveOverlay, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setAutoFillBackground(False)
        self.setWindowTitle("Curve Overlay")
        self._scene = empty_scene()
        self.paint_count = 0

    # ------------------------------------------------------------- geometry

    def place(self, rect):
        """Put the window on `rect` = (x, y, width, height) in global pixels.

        The order is load-bearing: geometry, then `show`, then the ex-style.
        """
        x, y, width, height = rect
        self.setGeometry(int(x), int(y), int(width), int(height))
        if not self.isVisible():
            self.show()
        click_through(self)

    def rect_size(self):
        return mapping.Rect(self.width(), self.height())

    def close_overlay(self):
        try:
            self.hide()
            self.setParent(None)
            self.deleteLater()
        except RuntimeError:
            pass

    # ---------------------------------------------------------------- scene

    def set_scene(self, scene):
        self._scene = scene
        self.update()

    def scene(self):
        return self._scene

    def set_marquee(self, marquee):
        self._scene = self._scene._replace(marquee=marquee)
        self.update()

    # ---------------------------------------------------------------- paint

    def paintEvent(self, event):
        self.paint_count += 1
        scene = self._scene
        rect = self.rect_size()
        if rect.width <= 0 or rect.height <= 0:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        try:
            self._paint_grid(painter, scene, rect)
            self._paint_time(painter, scene, rect)
            for drawn in scene.curves:
                self._paint_curve(painter, drawn, rect)
            self._paint_marquee(painter, scene)
            self._paint_message(painter, scene)
        finally:
            painter.end()

    def _paint_grid(self, painter, scene, rect):
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        step = mapping.grid_step(scene.frame.t1 - scene.frame.t0)
        frame = math.ceil(scene.frame.t0 / step) * step
        while frame <= scene.frame.t1:
            x, _ = mapping.to_pixels(scene.frame, rect, frame, 0.0)
            painter.setPen(QtGui.QPen(_GRID, 1))
            painter.drawLine(int(x), 0, int(x), rect.height)
            painter.setPen(_GRID_TEXT)
            painter.drawText(int(x) + 3, rect.height - 4,
                             str(int(round(frame))))
            frame += step

        # The value grid. Without it the shape reads and the magnitude does
        # not, which is half a graph editor. Skipped when each curve carries
        # its own Y window, where one shared line would be a lie.
        if scene.normalised or not scene.curves:
            return
        for value in mapping.value_lines(scene.frame):
            _, y = mapping.to_pixels(scene.frame, rect, scene.frame.t0,
                                     value)
            zero = abs(value) < 1e-9
            painter.setPen(QtGui.QPen(_ZERO if zero else _GRID,
                                      1.4 if zero else 1))
            painter.drawLine(0, int(y), rect.width, int(y))
            painter.setPen(_GRID_TEXT)
            painter.drawText(4, int(y) - 3, mapping.value_label(value))

    def _paint_time(self, painter, scene, rect):
        if scene.current_time is None:
            return
        x, _ = mapping.to_pixels(scene.frame, rect, scene.current_time, 0.0)
        painter.setPen(QtGui.QPen(_TIME, 1.5))
        painter.drawLine(int(x), 0, int(x), rect.height)

    def _paint_curve(self, painter, drawn, rect):
        colour = QtGui.QColor(*mapping.axis_colour(drawn.attribute))
        if len(drawn.samples) > 1:
            path = QtGui.QPainterPath()
            for index, (t, v) in enumerate(drawn.samples):
                x, y = mapping.to_pixels(drawn.frame, rect, t, v)
                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QPen(colour, 2.0))
            painter.drawPath(path)

        self._paint_tangents(painter, drawn, rect, colour)

        half = KEY_SIZE / 2.0
        for index, (t, v) in enumerate(drawn.keys):
            x, y = mapping.to_pixels(drawn.frame, rect, t, v)
            painter.setPen(QtGui.QPen(_KEY_EDGE, 1))
            painter.setBrush(_KEY_SELECTED if index in drawn.selected
                             else colour)
            painter.drawRect(QtCore.QRectF(x - half, y - half,
                                           KEY_SIZE, KEY_SIZE))

    def _paint_tangents(self, painter, drawn, rect, colour):
        if not drawn.tangents:
            return
        handle = QtGui.QColor(colour)
        handle.setAlpha(180)
        painter.setPen(QtGui.QPen(handle, 1.2))
        painter.setBrush(handle)
        for index, angles in drawn.tangents.items():
            if index >= len(drawn.keys):
                continue
            key = drawn.keys[index]
            x, y = mapping.to_pixels(drawn.frame, rect, key[0], key[1])
            into, out = mapping.tangent_points(
                drawn.frame, rect, key, angles[0], angles[1],
                length=TANGENT_LENGTH)
            for point in (into, out):
                painter.drawLine(QtCore.QPointF(x, y),
                                 QtCore.QPointF(*point))
                painter.drawEllipse(QtCore.QPointF(*point), 3.0, 3.0)

    def _paint_marquee(self, painter, scene):
        if not scene.marquee:
            return
        x0, y0, x1, y1 = scene.marquee
        rectangle = QtCore.QRectF(QtCore.QPointF(x0, y0),
                                  QtCore.QPointF(x1, y1)).normalized()
        painter.setPen(QtGui.QPen(_MARQUEE_LINE, 1, QtCore.Qt.DashLine))
        painter.setBrush(_MARQUEE_FILL)
        painter.drawRect(rectangle)

    def _paint_message(self, painter, scene):
        if not scene.message:
            return
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(_MESSAGE)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(12, 8, -12, -8),
                         QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft,
                         scene.message)
