"""The AT bar's strip (layout B of the AT Rail Mockups): painted 24 px controls with the Time Bar's hover,
press and toggle motion, our glyphs in group colours, a caption over each group, Time Bar-style blend tracks."""
import math
import time
import traceback

import maya.cmds as cmds

try:
    from PySide6 import QtCore, QtGui, QtSvg, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtCore, QtGui, QtSvg, QtWidgets
    from shiboken2 import wrapInstance

from . import CONTROL, TIMEBAR, core, glyphs

BAR_NAME = "skeldarATBarRoot"
NUDGE_OPT = "skeldarATBarFrames"
RECOVERY_OPT = "skeldarATBarRecoveryMinutes"

#  maya_hubstyle.TOKENS and the Time Bar's numbers (SkeldarAnim docs/interface-motion.md)
PANEL, CARD, FIELD, LINE, HOVER = "#1f2023", "#2a2c30", "#1b1c1f", "#45474d", "#34363b"
TRACK, TRACK_EDGE, DOT = "#17181a", "#26282c", "#6a6c72"
TEXT, TEXT2, MUTED, FAINT = "#e4e4e6", "#c9cacf", "#9a9ca3", "#77797f"
ACCENT, ACCENT_TEXT, ON_ACCENT, ACCENT_TINT = "#e07a36", "#f0a26b", "#2a1405", "#3a2a1f"
DANGER, DANGER_TINT = "#e39a93", "#3a2626"
KEYS, BLEND, POSE, SPACE, TIME, TOOLS = "#7fa9e6", "#6fb7c9", "#c89be8", "#f0a26b", "#e39a93", "#c9cacf"
HOVER_MS, FLASH_MS, POP_MS, LIFT, FRAME_MS = 110.0, 120.0, 200.0, 0.10, 16

FACE, MARGIN, CAPTION_H = 24, 3, 14
SLIDER_PRESETS = (5, 15, 50, 100, 105, 120, 150)


def _ui():
    try:
        return float(cmds.mayaDpiSetting(q=True, realScaleValue=True) or 1.0)
    except Exception:                                        # noqa: BLE001
        return 1.0


def _now():
    return time.perf_counter() * 1000.0


def _mix(a, b, t):
    a, b = QtGui.QColor(a), QtGui.QColor(b)
    t = max(0.0, min(1.0, t))
    return QtGui.QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                        round(a.blue() + (b.blue() - a.blue()) * t))


def _alpha(colour, a):
    c = QtGui.QColor(colour)
    c.setAlphaF(max(0.0, min(1.0, a)))
    return c


def _back_out(u):
    c = 1.70158
    u -= 1.0
    return 1.0 + (c + 1.0) * u ** 3 + c * u ** 2


_PIXMAPS = {}


def _glyph(name, colour, px, dpr):
    """The glyph rendered in `colour` at `px` logical pixels, cached."""
    key = (name, QtGui.QColor(colour).name(), int(px), dpr)
    pm = _PIXMAPS.get(key)
    if pm is None:
        renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(glyphs.svg(name, key[1]).encode("utf-8")))
        side = max(1, int(round(px * dpr)))
        pm = QtGui.QPixmap(side, side)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        renderer.render(p, QtCore.QRectF(0, 0, side, side))
        p.end()
        pm.setDevicePixelRatio(dpr)
        _PIXMAPS[key] = pm
    return pm


def _safe(fn, *args, **kwargs):
    def run(*_):
        try:
            fn(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            cmds.warning("AT: %s failed (see script editor)" % getattr(fn, "__name__", "tool"))
    return run


def _shift():
    return bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)


def _pos(e):
    return e.position().x() if hasattr(e, "position") else e.x()


class Driver(QtCore.QObject):
    """One 16 ms timer for the whole bar, running only while a control is moving."""

    def __init__(self, parent=None):
        super(Driver, self).__init__(parent)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)
        self._busy = set()

    def kick(self, widget):
        self._busy.add(widget)
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self):
        now = _now()
        for w in list(self._busy):
            try:
                busy = w.step(now)
                w.update()
            except RuntimeError:                             # the widget is gone
                busy = False
            if not busy:
                self._busy.discard(w)
        if not self._busy:
            self._timer.stop()


class ATButton(QtWidgets.QAbstractButton):
    """A painted 24 px control: the glyph in its group colour; hover lifts and lights it, a press flashes
    the accent, a toggle pops. Left click runs `click` ("menu": opens the menu), right click shows `menu()`."""

    def __init__(self, glyph, colour, tip, click=None, menu=None, checkable=False, driver=None, ui=1.0):
        super(ATButton, self).__init__()
        self.glyph, self.colour, self._ui, self.driver = glyph, colour, ui, driver
        side = int(round((FACE + 2 * MARGIN) * ui))
        self.setFixedSize(side, side)
        self.setToolTip(tip)
        self.setCheckable(checkable)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setAccessibleName(tip.split(":")[0].split("\n")[0])
        self._hover = self._goal = 0.0
        self._last = self._flash_t = self._pop_t = None
        self._menu = menu
        if click == "menu":
            self.clicked.connect(lambda: self._show_menu(QtCore.QPoint(0, self.height())))
        elif click:
            self.clicked.connect(_safe(click))
        if menu:
            self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self._show_menu)
        self.toggled.connect(self._popped)

    def _kick(self):
        if self.driver is not None:
            self.driver.kick(self)
        else:
            self.update()

    def enterEvent(self, e):
        self._goal = 1.0
        self._kick()
        super(ATButton, self).enterEvent(e)

    def leaveEvent(self, e):
        self._goal = 0.0
        self._kick()
        super(ATButton, self).leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._flash_t = _now()
            self._kick()
        super(ATButton, self).mousePressEvent(e)

    def _popped(self, _on):
        self._pop_t = _now()
        self._kick()

    def step(self, now):
        dt = now - (self._last if self._last is not None else now)
        self._last = now
        if self._hover != self._goal:
            self._hover += (self._goal - self._hover) * (1.0 - math.exp(-3.0 * dt / HOVER_MS))
            if abs(self._goal - self._hover) < 0.005:
                self._hover = self._goal
        busy = (self._hover != self._goal
                or (self._flash_t is not None and now - self._flash_t < FLASH_MS)
                or (self._pop_t is not None and now - self._pop_t < POP_MS))
        if not busy:
            self._last = None
        return busy

    def paintEvent(self, _):
        ui, now = self._ui, _now()
        flash = 0.0
        if self._flash_t is not None:
            flash = max(0.0, 1.0 - (now - self._flash_t) / FLASH_MS)
        pop = 1.0
        if self._pop_t is not None and now - self._pop_t < POP_MS:
            pop = 0.7 + 0.3 * _back_out((now - self._pop_t) / POP_MS)
        scale = (1.0 + LIFT * self._hover) * (1.0 - 0.06 * flash) * pop
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = QtCore.QPointF(self.width() / 2.0, self.height() / 2.0)
        p.translate(c)
        p.scale(scale, scale)
        half = FACE * ui / 2.0
        face = QtCore.QRectF(-half, -half, 2 * half, 2 * half)
        radius = 5 * ui
        checked = self.isChecked()
        if self._hover > 0.01:                               # the glow: rings of added accent light
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
            for i in range(2):
                p.setPen(QtGui.QPen(_alpha(ACCENT, 46 / 255.0 * self._hover * (2 - i) / 2.0), 1.2 * ui))
                p.setBrush(QtCore.Qt.NoBrush)
                grow = (i + 1) * 1.2 * ui
                p.drawRoundedRect(face.adjusted(-grow, -grow, grow, grow), radius + grow, radius + grow)
            p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
        base = QtGui.QColor(ACCENT_TINT) if checked else _alpha(HOVER, 0.0)
        fill = _mix(base, HOVER, self._hover) if checked else _alpha(HOVER, self._hover)
        if flash > 0:
            fill = _mix(fill if fill.alpha() else QtGui.QColor(HOVER), ACCENT, flash)
        edge = QtGui.QColor(ACCENT) if checked else _alpha(ACCENT, self._hover)
        p.setPen(QtGui.QPen(edge, 1.0) if edge.alpha() else QtCore.Qt.NoPen)
        p.setBrush(fill)
        p.drawRoundedRect(face.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        if flash > 0.5:
            ink = QtGui.QColor(ON_ACCENT)
        else:
            ink = _mix(self.colour, TEXT, round(self._hover * 10) / 10.0) if not checked else QtGui.QColor(self.colour)
        px = 16 * ui
        pm = _glyph(self.glyph, ink, px, self.devicePixelRatioF())
        p.drawPixmap(QtCore.QRectF(-px / 2.0, -px / 2.0, px, px), pm, QtCore.QRectF(pm.rect()))
        p.end()

    def _show_menu(self, pos):
        m = QtWidgets.QMenu(self)
        for entry in self._menu():
            if entry is None:
                m.addSeparator()
            elif isinstance(entry[1], list):
                sub = m.addMenu(entry[0])
                for label, fn in entry[1]:
                    sub.addAction(label).triggered.connect(_safe(fn))
            else:
                m.addAction(entry[0]).triggered.connect(_safe(entry[1]))
        m.exec_(self.mapToGlobal(pos)) if hasattr(m, "exec_") else m.exec(self.mapToGlobal(pos))


class BlendSlider(QtWidgets.QWidget):
    """A Time Bar-style blend track: click a mark for a preset, drag anywhere to scrub from -150% to 150%;
    the centre chip shows the code, and the value while dragging."""

    def __init__(self, code, mode, colour, tip, ui=1.0, width=214):
        super(BlendSlider, self).__init__()
        self.code, self.mode, self.colour, self._ui = code, mode, QtGui.QColor(colour), ui
        self.setToolTip(tip)
        self.setFixedSize(int(round(width * ui)), int(round((FACE + 2 * MARGIN) * ui)))
        self.setMouseTracking(True)
        self._hover = None
        self._press_x = None
        self._dragging = False
        self._session = None
        self._value = None

    def _chip(self):
        return 34 * self._ui

    def _points(self):
        w = float(self.width())
        cx = w / 2.0
        half = (w - self._chip()) / 2.0 - 8 * self._ui
        step = half / len(SLIDER_PRESETS)
        pts = [(cx, 0.0)]
        for i, v in enumerate(SLIDER_PRESETS):
            off = self._chip() / 2.0 + 4 * self._ui + step * (i + 0.5)
            pts += [(cx + off, float(v)), (cx - off, float(-v))]
        return sorted(pts)

    def _x_of(self, value):
        pts = self._points()
        for (x0, v0), (x1, v1) in zip(pts, pts[1:]):
            if v0 <= value <= v1:
                return x0 + (x1 - x0) * ((value - v0) / (v1 - v0) if v1 != v0 else 0.0)
        return pts[0][0] if value < 0 else pts[-1][0]

    def _value_at(self, x):
        pts = self._points()
        if x <= pts[0][0]:
            return pts[0][1]
        if x >= pts[-1][0]:
            return pts[-1][1]
        for (x0, v0), (x1, v1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
        return 0.0

    def _dot_at(self, x):
        best = None
        for px, v in self._points():
            if v and abs(px - x) <= 6 * self._ui and (best is None or abs(px - x) < abs(best[0] - x)):
                best = (px, v)
        return best[1] if best else None

    def paintEvent(self, _):
        ui = self._ui
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        cy = self.height() / 2.0
        track = QtCore.QRectF(0.5, cy - 8 * ui + 0.5, self.width() - 1, 16 * ui - 1)
        p.setPen(QtGui.QPen(QtGui.QColor(TRACK_EDGE), 1))
        p.setBrush(QtGui.QColor(TRACK))
        p.drawRoundedRect(track, 8 * ui, 8 * ui)
        value = self._value
        if value is not None:
            x0, x1 = self.width() / 2.0, self._x_of(value)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(_alpha(self.colour, 0.45))
            p.drawRoundedRect(QtCore.QRectF(min(x0, x1), cy - 2 * ui, abs(x1 - x0), 4 * ui), 2 * ui, 2 * ui)
        p.setPen(QtCore.Qt.NoPen)
        for px, v in self._points():
            if not v:
                continue
            lit = value is not None and (v > 0) == (value > 0) and abs(v) <= abs(value)
            hot = self._hover == v
            if abs(v) == 100:
                s = (7 if hot else 6) * ui
                p.setBrush(self.colour)
                p.drawRoundedRect(QtCore.QRectF(px - s / 2.0, cy - s / 2.0, s, s), 1.5 * ui, 1.5 * ui)
            else:
                s = (5 if hot else 3) * ui
                p.setBrush(self.colour if (hot or lit) else QtGui.QColor(DOT))
                p.drawEllipse(QtCore.QPointF(px, cy), s / 2.0, s / 2.0)
        chip = QtCore.QRectF(self.width() / 2.0 - self._chip() / 2.0, cy - FACE * ui / 2.0, self._chip(), FACE * ui)
        dragging = value is not None
        p.setPen(QtGui.QPen(QtGui.QColor(ACCENT if dragging else LINE), 1))
        p.setBrush(QtGui.QColor(ACCENT_TINT if dragging else CARD))
        p.drawRoundedRect(chip.adjusted(0.5, 0.5, -0.5, -0.5), 5 * ui, 5 * ui)
        f = QtGui.QFont("Consolas" if dragging else self.font().family())
        f.setPixelSize(int(round(11 * ui)))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QtGui.QColor(ACCENT_TEXT) if dragging else self.colour)
        p.drawText(chip, QtCore.Qt.AlignCenter, "%d" % round(value) if dragging else self.code)
        p.end()

    def _apply(self, value):
        if self._session is None:
            self._session = core.SliderSession(self.mode)
        self._value = value
        self._session.apply(value)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._press_x = _pos(e)
            self._dragging = False

    def mouseMoveEvent(self, e):
        x = _pos(e)
        if self._press_x is None:
            hover = self._dot_at(x)
            if hover != self._hover:
                self._hover = hover
                self.update()
            return
        if not self._dragging and abs(x - self._press_x) > 3:
            self._dragging = True
        if self._dragging:
            try:
                self._apply(self._value_at(x))
            except Exception:
                traceback.print_exc()

    def mouseReleaseEvent(self, e):
        if self._press_x is None:
            return
        try:
            if not self._dragging:
                dot = self._dot_at(self._press_x)
                if dot is not None:
                    self._apply(dot)
        except Exception:
            traceback.print_exc()
        finally:
            if self._session is not None:
                self._session.finish()
            self._session = None
            self._press_x = None
            self._dragging = False
            self._value = None
            self.update()

    def leaveEvent(self, _):
        self._hover = None
        self.update()


SET_COLOURS = (("Purple", POSE), ("Blue", KEYS), ("Cyan", BLEND), ("Orange", SPACE), ("Pink", TIME),
               ("Grey", TOOLS))
POP_OPEN_MS, START_SCALE = 240.0, 0.3                        # the Time Bar's burst: a part popping in


class SetCell(QtWidgets.QAbstractButton):
    """A select set's cell: its colour bar, its name, how many it holds - or, `new`, the cell that makes a
    set of the selection. Hover lifts and lights it, a press flashes the accent, it pops in when the panel
    opens (nearest the Select Sets button first)."""

    def __init__(self, label, node, colour, size, popup, new=False):
        super(SetCell, self).__init__(popup)
        self.label, self.node, self.colour, self.count, self.popup, self.new = label, node, colour, size, popup, new
        ui = popup.ui
        self.setFixedSize(int(round(156 * ui)), int(round(34 * ui)))
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setAccessibleName(label)
        self.setToolTip("Make a select set of the selection" if new else
                        "%s: %d objects\nClick: select, Shift: add, Ctrl: remove, x: delete the set\n"
                        "Right click: update, rename, colour, delete" % (label, size or 0))
        self.setMouseTracking(True)
        self._hover = self._goal = 0.0
        self._last = self._flash_t = self._born = None
        self._delay = 0.0
        self._on_x = self._x_down = False
        if not new:
            self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(lambda pos: popup.cell_menu(self, self.mapToGlobal(pos)))
        self.clicked.connect(lambda *_a: popup.picked(self))

    def pop_in(self, now, delay):
        self._born, self._delay = now, delay

    def enterEvent(self, e):
        self._goal = 1.0
        self.popup.driver.kick(self)
        super(SetCell, self).enterEvent(e)

    def leaveEvent(self, e):
        self._goal = 0.0
        self._on_x = False
        self.popup.driver.kick(self)
        super(SetCell, self).leaveEvent(e)

    def x_rect(self):
        """The delete ×, in the painter's centred coordinates (unscaled)."""
        ui = self.popup.ui
        right = self.width() / 2.0 - 3 * ui - 8 * ui
        return QtCore.QRectF(right - 14 * ui, -7 * ui, 14 * ui, 14 * ui)

    def _over_x(self, e):
        if self.new:
            return False
        pos = e.position() if hasattr(e, "position") else QtCore.QPointF(e.pos())
        return self.x_rect().translated(self.width() / 2.0, self.height() / 2.0).adjusted(-3, -3, 3, 3).contains(pos)

    def mouseMoveEvent(self, e):
        on = self._over_x(e)
        if on != self._on_x:
            self._on_x = on
            self.update()
        super(SetCell, self).mouseMoveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton and self._over_x(e):
            self._x_down = True                               # the ×: no click, no flash
            self.update()
            return
        if e.button() == QtCore.Qt.LeftButton:
            self._flash_t = _now()
            self.popup.driver.kick(self)
        super(SetCell, self).mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if self._x_down:
            self._x_down = False
            if self._over_x(e):
                self.popup.remove(self)
            return
        super(SetCell, self).mouseReleaseEvent(e)

    def step(self, now):
        dt = now - (self._last if self._last is not None else now)
        self._last = now
        if self._hover != self._goal:
            self._hover += (self._goal - self._hover) * (1.0 - math.exp(-3.0 * dt / HOVER_MS))
            if abs(self._goal - self._hover) < 0.005:
                self._hover = self._goal
        busy = (self._hover != self._goal
                or (self._flash_t is not None and now - self._flash_t < FLASH_MS)
                or (self._born is not None and now - self._born - self._delay < POP_OPEN_MS))
        if not busy:
            self._last = None
        return busy

    def paintEvent(self, _):
        ui, now = self.popup.ui, _now()
        appear = 1.0
        if self._born is not None:
            u = (now - self._born - self._delay) / POP_OPEN_MS
            if u <= 0:
                return
            appear = min(1.0, u)
        scale = START_SCALE + (1.0 - START_SCALE) * _back_out(appear) if appear < 1.0 else 1.0
        flash = max(0.0, 1.0 - (now - self._flash_t) / FLASH_MS) if self._flash_t is not None else 0.0
        scale *= (1.0 + 0.04 * self._hover) * (1.0 - 0.04 * flash)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setOpacity(min(1.0, appear * 1.6))
        c = QtCore.QPointF(self.width() / 2.0, self.height() / 2.0)
        p.translate(c)
        p.scale(scale, scale)
        m = 3 * ui
        face = QtCore.QRectF(-self.width() / 2.0 + m, -self.height() / 2.0 + m, self.width() - 2 * m,
                             self.height() - 2 * m)
        radius = 6 * ui
        fill = _mix(FIELD, HOVER, self._hover)
        if flash > 0:
            fill = _mix(fill, ACCENT, flash)
        edge = QtGui.QPen(_mix(LINE, ACCENT, self._hover), 1)
        if self.new and self._hover < 0.5:
            edge.setStyle(QtCore.Qt.DashLine)
        p.setPen(edge)
        p.setBrush(fill)
        p.drawRoundedRect(face.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        ink = QtGui.QColor(ON_ACCENT) if flash > 0.5 else None
        f = QtGui.QFont(self.font())
        f.setPixelSize(int(round(12 * ui)))
        if self.new:
            p.setPen(ink or _mix(MUTED, TEXT, self._hover))
            p.setFont(f)
            p.drawText(face, QtCore.Qt.AlignCenter, "+   New from selection")
            p.end()
            return
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(self.colour))
        p.drawRoundedRect(QtCore.QRectF(face.left() + 5 * ui, face.top() + 6 * ui, 3 * ui, face.height() - 12 * ui),
                          1.5 * ui, 1.5 * ui)
        text = face.adjusted(14 * ui, 0, -8 * ui, 0)
        if self._hover > 0.01:                               # the delete ×, out on hover; soft red under the cursor
            x = self.x_rect()
            hot = self._on_x or self._x_down
            if hot:
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(QtGui.QColor(DANGER_TINT))
                p.drawEllipse(x.adjusted(-2 * ui, -2 * ui, 2 * ui, 2 * ui))
            pen = QtGui.QPen(_alpha(DANGER if hot else _mix(FAINT, TEXT2, self._hover).name(), self._hover),
                             1.5 * ui, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
            p.setPen(pen)
            inset = 3.5 * ui
            p.drawLine(QtCore.QPointF(x.left() + inset, x.top() + inset), QtCore.QPointF(x.right() - inset, x.bottom() - inset))
            p.drawLine(QtCore.QPointF(x.right() - inset, x.top() + inset), QtCore.QPointF(x.left() + inset, x.bottom() - inset))
            text = text.adjusted(0, 0, -(x.width() + 6 * ui) * self._hover, 0)
        count = QtGui.QFont("Consolas")
        count.setPixelSize(int(round(11 * ui)))
        p.setFont(count)
        p.setPen(ink or QtGui.QColor(FAINT))
        p.drawText(text, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, str(self.count or 0))
        p.setFont(f)
        p.setPen(ink or _mix(TEXT2, TEXT, self._hover))
        name = QtGui.QFontMetrics(f).elidedText(self.label, QtCore.Qt.ElideRight, int(text.width() - 26 * ui))
        p.drawText(text, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, name)
        p.end()


class SetsPopup(QtWidgets.QWidget):
    """The select sets' cells, out of the Select Sets button (2026-10-21, «окремі ячейки щоб вони спливали при
    нажатті кнопки селекшн сет»): click a cell to select its set (Shift adds, Ctrl removes), right click for
    update / rename / colour / delete, the last cell makes a set of the selection. Esc or a click outside
    closes it."""

    COLUMNS = 4

    def __init__(self, anchor, ui):
        super(SetsPopup, self).__init__(anchor, QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint
                                        | QtCore.Qt.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.anchor, self.ui = anchor, ui
        self.setStyleSheet(_style(ui))
        self.driver = Driver(self)
        self.pad = int(round(10 * ui))
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(self.pad, self.pad, self.pad, self.pad)
        lay.setSpacing(int(round(6 * ui)))
        head = QtWidgets.QHBoxLayout()
        head.setContentsMargins(int(round(3 * ui)), 0, int(round(3 * ui)), 0)
        head.addWidget(self._label("SELECT SETS", POSE, 10, bold=True))
        head.addStretch(1)
        head.addWidget(self._label("click: select    shift: add    ctrl: remove    right click: more", FAINT, 10))
        lay.addLayout(head)
        self.grid = QtWidgets.QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(0)
        self.cells = []
        for i, (label, node) in enumerate(core.selection_sets()):
            colour = core.set_colour(node) or SET_COLOURS[i % len(SET_COLOURS)][1]
            self.cells.append(SetCell(label, node, colour, core.set_size(node), self))
        self.cells.append(SetCell("New from selection", None, MUTED, None, self, new=True))
        self._place_cells()
        lay.addLayout(self.grid)
        self._above = True

    def _place_cells(self):
        while self.grid.count():
            self.grid.takeAt(0)
        for cell, (row, column) in zip(self.cells, core.sets_grid(len(self.cells), self.COLUMNS)):
            self.grid.addWidget(cell, row, column)

    def remove(self, cell):
        """The set deleted from its cell's ×: the cell goes, the others close up, the panel stays open and
        keeps its edge on the button."""
        _safe(core.delete_selection_set, cell.node)()
        if cmds.objExists(cell.node):
            return
        self.cells.remove(cell)
        cell.setParent(None)
        cell.deleteLater()
        self._place_cells()
        edge = self.geometry().bottom() if self._above else self.geometry().top()
        self.layout().activate()
        self.adjustSize()
        self.move(self.x(), edge - self.height() + 1 if self._above else edge)

    def _label(self, text, colour, size, bold=False):
        label = QtWidgets.QLabel(text)
        f = label.font()
        f.setPixelSize(int(round(size * self.ui)))
        f.setBold(bold)
        if bold:
            f.setLetterSpacing(QtGui.QFont.PercentageSpacing, 108)
        label.setFont(f)
        label.setStyleSheet("color: %s; background: transparent;" % colour)
        return label

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(QtGui.QColor(LINE), 1))
        p.setBrush(QtGui.QColor(CARD))
        r = 8 * self.ui
        p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), r, r)
        p.end()

    def open_at(self):
        """Shown above the Select Sets button (below it when there is no room), the cells popping in."""
        self.adjustSize()
        a, ui = self.anchor, self.ui
        corner = a.mapToGlobal(QtCore.QPoint(0, 0))
        screen = (a.screen() or QtWidgets.QApplication.primaryScreen()).availableGeometry()
        x = max(screen.left(), min(corner.x() - self.pad, screen.right() - self.width()))
        y = corner.y() - self.height() - int(round(4 * ui))
        self._above = y >= screen.top()
        if not self._above:
            y = corner.y() + a.height() + int(round(4 * ui))
        self.move(x, y)
        self.show()
        origin = a.mapToGlobal(a.rect().center())
        now = _now()
        for cell in self.cells:
            centre = cell.mapToGlobal(cell.rect().center())
            far = math.hypot(centre.x() - origin.x(), 1.5 * (centre.y() - origin.y())) / ui
            cell.pop_in(now, 48.0 + 21.6 * far / 60.0)
            self.driver.kick(cell)
        return self

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
            return
        super(SetsPopup, self).keyPressEvent(e)

    def picked(self, cell):
        if cell.new:
            return self._after(core.create_selection_set)
        mods = QtWidgets.QApplication.keyboardModifiers()
        if mods & QtCore.Qt.ControlModifier:
            _safe(core.deselect_set, cell.node)()
        else:
            _safe(core.select_set, cell.node, add=bool(mods & QtCore.Qt.ShiftModifier))()

    def cell_menu(self, cell, where):
        node = cell.node
        m = QtWidgets.QMenu(self)
        m.addAction("Select").triggered.connect(_safe(core.select_set, node))
        m.addAction("Add to selection").triggered.connect(_safe(core.select_set, node, add=True))
        m.addAction("Remove from selection").triggered.connect(_safe(core.deselect_set, node))
        m.addSeparator()
        m.addAction("Update from selection").triggered.connect(
            lambda *_a: self._after(lambda: core.update_selection_set(node)))
        m.addAction("Rename...").triggered.connect(lambda *_a: self._after(lambda: core.rename_selection_set(node)))
        colours = m.addMenu("Colour")
        for name, colour in SET_COLOURS:
            swatch = QtGui.QPixmap(12, 12)
            swatch.fill(QtGui.QColor(colour))
            colours.addAction(QtGui.QIcon(swatch), name).triggered.connect(
                lambda *_a, c=colour: self._after(lambda: core.paint_set(node, c)))
        m.addSeparator()
        m.addAction("Delete").triggered.connect(lambda *_a: self._after(lambda: core.delete_selection_set(node)))
        m.exec_(where) if hasattr(m, "exec_") else m.exec(where)

    def _after(self, fn):
        """A change that asks a question or changes the cells: the panel closes, `fn` runs, a fresh panel
        opens out of the same button."""
        anchor, ui = self.anchor, self.ui
        self.close()

        def run():
            _safe(fn)()
            try:
                if anchor.isVisible():
                    open_sets(anchor, ui)
            except RuntimeError:                             # the bar was rebuilt meanwhile
                pass
        QtCore.QTimer.singleShot(0, run)


def open_sets(anchor, ui):
    return SetsPopup(anchor, ui).open_at()


class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, spacing=6, margins=(4, 3, 4, 3)):
        super(FlowLayout, self).__init__(parent)
        self._items = []
        self.setSpacing(spacing)
        self.setContentsMargins(*margins)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return QtCore.Qt.Orientations(0) if hasattr(QtCore.Qt, "Orientations") else QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._layout(QtCore.QRect(0, 0, w, 0), True)

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QtCore.QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())

    def _layout(self, rect, test):
        m = self.contentsMargins()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = r.x(), r.y(), 0
        for it in self._items:
            hint = it.sizeHint()
            nx = x + hint.width() + self.spacing()
            if nx - self.spacing() > r.right() and line_h > 0:
                x, y = r.x(), y + line_h + self.spacing()
                nx = x + hint.width() + self.spacing()
                line_h = 0
            if not test:
                it.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), hint))
            x, line_h = nx, max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()


def _group(title, colour, widgets, ui=1.0, spacing=0):
    """A caption in the group's colour over a row of its controls."""
    box = QtWidgets.QWidget()
    col = QtWidgets.QVBoxLayout(box)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(0)
    cap = QtWidgets.QLabel(title)
    f = cap.font()
    f.setPixelSize(int(round(10 * ui)))
    f.setBold(True)
    f.setLetterSpacing(QtGui.QFont.PercentageSpacing, 108)
    cap.setFont(f)
    cap.setFixedHeight(int(round(CAPTION_H * ui)))
    cap.setContentsMargins(int(round(MARGIN * ui)), 0, 0, 0)
    cap.setStyleSheet("color: %s; background: transparent;" % colour)
    col.addWidget(cap)
    row = QtWidgets.QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(int(round(spacing * ui)))
    for w in widgets:
        row.addWidget(w, 0, QtCore.Qt.AlignVCenter)
    col.addLayout(row)
    return box


def _style(ui, embedded=False):
    px = lambda v: int(round(v * ui))                         # noqa: E731 - Qt stylesheet pixels are physical
    return """
QWidget#{root} {{ background: {panel}; border: none; {edge} }}
QSpinBox {{ background: {field}; color: {text}; border: 1px solid {line}; border-radius: {r}px;
            font-family: Consolas; font-size: {f}px; padding: 0; selection-background-color: {accent}; }}
QSpinBox:hover {{ border-color: {accent}; }}
QMenu {{ background: {card}; color: {text}; border: 1px solid {line}; border-radius: {r}px; padding: {pad}px; }}
QMenu::item {{ padding: {ipy}px {ipx}px; border-radius: {r}px; }}
QMenu::item:selected {{ background: {hover}; color: {accent_text}; }}
QMenu::separator {{ height: 1px; background: {line}; margin: {pad}px {ipx}px; }}
QToolTip {{ background: {card}; color: {text2}; border: 1px solid {line}; padding: {pad}px {ipy}px; }}
""".format(root=BAR_NAME, edge="" if embedded else "border-bottom: 1px solid %s;" % TRACK, panel=PANEL, track=TRACK, field=FIELD, text=TEXT, text2=TEXT2, line=LINE, card=CARD, hover=HOVER,
           accent=ACCENT, accent_text=ACCENT_TEXT, r=px(5), f=px(12), pad=px(4), ipy=px(5), ipx=px(12))


class ATBar(QtWidgets.QWidget):
    """`embedded`: the Time Bar's top row, inside its control - one surface with it, no edge of our own."""

    def __init__(self, parent=None, embedded=False):
        super(ATBar, self).__init__(parent)
        self.setObjectName(BAR_NAME)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.embedded = embedded
        self.ui = _ui()
        self.setStyleSheet(_style(self.ui, embedded))
        self.driver = Driver(self)
        self._recovery_timer = QtCore.QTimer(self)
        self._recovery_timer.timeout.connect(_safe(core.save_recovery))
        self._toggles = []

        ui = self.ui
        #  the groups apart by space alone (2026-10-21, «прибери ще сірі роздєлітєльні лінії»)
        lay = FlowLayout(self, spacing=int(round(16 * ui)),
                         margins=tuple(int(round(v * ui)) for v in (12, 6, 12, 7)))
        lay.addWidget(_group("", ACCENT_TEXT, [self._mark()], ui))
        for group in [self._keys_group(), self._blend_group()] + self._tool_groups():
            lay.addWidget(group)

        self._sync_timer = QtCore.QTimer(self)
        self._sync_timer.timeout.connect(self._sync_toggles)
        self._sync_timer.start(1000)

    def needed_height(self, width=None):
        if not width:
            #  not laid out yet (1 px wide): its host's width, else a row as wide as Maya's window
            host = self.parentWidget()
            width = self.width() if self.width() > 200 else (host.width() if host is not None and host.width() > 200
                                                             else int(1920 * self.ui))
        return self.layout().heightForWidth(width)

    def logical_height(self):
        return int(round(self.needed_height() / self.ui))

    def resizeEvent(self, e):
        super(ATBar, self).resizeEvent(e)
        QtCore.QTimer.singleShot(0, self.fit_dock)

    def fit_dock(self):
        """The dock as tall as the bar's rows at its current width (it wraps when narrow): the Time Bar's
        control when we are its top row, else our own."""
        want = self.needed_height()
        if self.minimumHeight() != want:
            self.setMinimumHeight(want)
        if self.embedded:
            _fit_timebar()
            return
        host = self.parentWidget()
        if host is None or host.height() >= want:
            return
        try:
            cmds.workspaceControl(CONTROL, edit=True, resizeHeight=int(round(want / self.ui)))
        except RuntimeError:
            pass
        if host.height() >= want:
            return
        #  a docked control Maya keeps at its row's height in the splitter: grow our row there, taking the
        #  room from the tallest neighbour (the viewport)
        child = host
        while child is not None and not isinstance(child.parentWidget(), QtWidgets.QSplitter):
            child = child.parentWidget()
        if child is None:
            return
        splitter = child.parentWidget()
        if splitter.orientation() != QtCore.Qt.Vertical:
            return
        sizes = splitter.sizes()
        i = splitter.indexOf(child)
        delta = want - host.height()
        others = [j for j in range(len(sizes)) if j != i]
        if i < 0 or not others:
            return
        j = max(others, key=lambda k: sizes[k])
        if sizes[j] - delta > 100:
            sizes[i] += delta
            sizes[j] -= delta
            splitter.setSizes(sizes)

    def _button(self, glyph, colour, tip, click=None, menu=None, checkable=False):
        return ATButton(glyph, colour, tip, click, menu=menu, checkable=checkable, driver=self.driver, ui=self.ui)

    def _mark(self):
        ui = self.ui
        mark = QtWidgets.QLabel("AT")
        f = mark.font()
        f.setPixelSize(int(round(12 * ui)))
        f.setBold(True)
        mark.setFont(f)
        mark.setAlignment(QtCore.Qt.AlignCenter)
        mark.setFixedSize(int(round(32 * ui)), int(round(FACE * ui)))
        mark.setStyleSheet("color: %s; border: 1px solid %s; border-radius: %dpx; background: transparent;"
                           % (ACCENT_TEXT, ACCENT, int(round(5 * ui))))
        box = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(box)
        lay.setContentsMargins(0, int(round(MARGIN * ui)), 0, int(round(MARGIN * ui)))
        lay.addWidget(mark)
        return box

    # ---- groups

    def _keys_group(self):
        ui = self.ui
        self.nudge_spin = QtWidgets.QSpinBox()
        self.nudge_spin.setRange(1, 999)
        self.nudge_spin.setFixedSize(int(round(34 * ui)), int(round(FACE * ui)))
        self.nudge_spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.nudge_spin.setAlignment(QtCore.Qt.AlignCenter)
        self.nudge_spin.setToolTip("Frames for the nudge and inbetween buttons")
        self.nudge_spin.setValue(cmds.optionVar(q=NUDGE_OPT) if cmds.optionVar(exists=NUDGE_OPT) else 2)
        self.nudge_spin.valueChanged.connect(lambda v: cmds.optionVar(iv=(NUDGE_OPT, v)))
        n = self.nudge_spin.value
        field = QtWidgets.QWidget()
        fl = QtWidgets.QHBoxLayout(field)
        fl.setContentsMargins(int(round(MARGIN * ui)), 0, int(round(MARGIN * ui)), 0)
        fl.addWidget(self.nudge_spin)
        return _group("KEYS", KEYS, [
            self._button("nudge_left", KEYS, "Nudge Left: all keys of the selected controls back by the field's frames",
                         lambda: core.nudge(-n())),
            self._button("nudge_right", KEYS, "Nudge Right: all keys of the selected controls forward by the field's "
                                              "frames", lambda: core.nudge(n())),
            field,
            self._button("insert", KEYS, "Insert Inbetween: the field's frames after the current time (selected controls)",
                         lambda: core.inbetween(n())),
            self._button("remove", KEYS, "Remove Inbetween: the field's frames after the current time (selected controls)",
                         lambda: core.inbetween(-n())),
            self._button("insert_scene", KEYS, "Insert Inbetween: the field's frames after the current time (whole scene)",
                         lambda: core.inbetween(n(), scene=True)),
            self._button("remove_scene", KEYS, "Remove Inbetween: the field's frames after the current time (whole scene)",
                         lambda: core.inbetween(-n(), scene=True)),
        ], self.ui)

    def _blend_group(self):
        ui = self.ui
        return _group("BLEND", BLEND, [
            BlendSlider("SM", "SM", KEYS, "Smooth / Rough: left smooths the curve, right roughens it\n"
                                          "Selected keys in the Graph Editor, else the key on the current frame", ui),
            BlendSlider("TW", "TW", BLEND, "Tweener: -100 = previous key, 0 = halfway, 100 = next key", ui),
            BlendSlider("BD", "BD", BLEND, "Blend to Default: 100 = default pose (snapshot or attribute default)", ui),
            BlendSlider("BN", "BN", BLEND, "Blend to Neighbors: left toward the previous key, right toward the next", ui),
        ], ui, spacing=10)

    def _tool_groups(self):
        b = self._button
        self.temp_ctrl_btn = b("temp_controls", SPACE,
                               "Temp Controls: world-space locators drive the selection; click again to bake back",
                               self._toggle_temp_controls, checkable=True)
        self.temp_pivot_btn = b("temp_pivot", SPACE,
                                "Temp Pivot: rotate the selection around the last selected; click again to key",
                                self._toggle_temp_pivot, checkable=True)
        self.trail_btn = b("motion_trail", TIME, "Motion Trail (time slider range) - click again to remove",
                           self._toggle_trail, checkable=True)
        self.recovery_btn = b("recovery", TOOLS, "Anim Recovery: auto-save a backup copy of the scene every few minutes",
                              self._toggle_recovery, menu=self._recovery_menu, checkable=True)
        self._toggles = [(self.temp_ctrl_btn, core.temp_controls_active),
                         (self.temp_pivot_btn, core.temp_pivot_active),
                         (self.trail_btn, core.motion_trails_exist)]
        ui = self.ui
        self.sets_btn = b("select_sets", POSE, "Select Sets: click for the sets' cells\nRight click: the sets as a menu",
                          lambda: open_sets(self.sets_btn, self.ui), menu=self._sets_menu)
        return [
            _group("POSE", POSE, [
                self.sets_btn,
                b("copy_anim", POSE, "Copy Animation of the selected controls", core.copy_animation),
                b("paste_anim", POSE, "Paste Animation at the current frame (matched by name, else by selection order)\n"
                                      "Right click: insert at the current frame, or replace at the copied frames",
                  core.paste_animation, menu=self._paste_anim_menu),
                b("copy_pose", POSE, "Copy Pose", core.copy_pose),
                b("paste_pose", POSE, "Paste Pose (matched by name, else by selection order)", core.paste_pose),
            ], ui),
            _group("SPACE", SPACE, [
                b("mirror", SPACE, "Mirror Pose: flip L/R pairs, mirror center controls\nRight click: select opposite",
                  core.mirror_pose, menu=self._mirror_menu),
                b("align", SPACE, "Align Objects: snap the selection to the last selected", core.align_objects),
                b("relationship", SPACE, "Xform Relationship: click = copy (followers, anchor last)\n"
                                         "Shift+click = paste T+R, Ctrl+Shift+click = translate only, "
                                         "Alt+Shift+click = rotate only\n"
                                         "Right click: paste translate / rotate separately, current frame or all keys",
                  self._relationship_click, menu=self._relationship_menu),
                b("world", SPACE, "World Space: click = copy, Shift+click = paste\nRight click for paste on all keys",
                  self._world_click, menu=self._world_menu),
                b("space_switch", SPACE, "Space Switcher: switch an enum attribute keeping the world position "
                                         "(current frame)", "menu", menu=lambda: self._space_entries(False)),
                b("space_switch_all", SPACE, "Space Switcher (all keys): switch an enum attribute on every key, "
                                             "keeping world motion", "menu", menu=lambda: self._space_entries(True)),
                self.temp_ctrl_btn,
                self.temp_pivot_btn,
            ], ui),
            _group("TIME", TIME, [
                self.trail_btn,
                b("bookmark", TIME, "Time Bookmark: add at the current frame / highlighted range\n"
                                    "Right click: next, previous, delete", core.add_bookmark, menu=self._bookmark_menu),
                b("bookmark_panel", TIME, "Time Bookmarks Panel: jump to any bookmark", "menu",
                  menu=self._bookmarks_panel),
            ], ui),
            _group("TOOLS", TOOLS, [
                b("more", TOOLS, "Extra tools", "menu", menu=self._extra_menu),
                b("euler", TOOLS, "Euler Filter rotation curves (selection, or whole scene)", core.euler_filter),
                b("snapshot", TOOLS, "Snapshot Default Pose of the selected controls (used by BD)\n"
                                     "Right click: reset to default pose, clear snapshot",
                  core.snapshot_default_pose, menu=self._snapshot_menu),
                self.recovery_btn,
            ], ui),
        ]

    # ---- toggles

    def _sync_toggles(self):
        for btn, query in self._toggles:
            try:
                state = bool(query())
            except Exception:
                continue
            if btn.isChecked() != state:
                btn.setChecked(state)

    def _toggle_temp_controls(self):
        core.toggle_temp_controls()
        self._sync_toggles()

    def _toggle_temp_pivot(self):
        core.toggle_temp_pivot()
        self._sync_toggles()

    def _toggle_trail(self):
        core.toggle_motion_trail()
        self._sync_toggles()

    def _toggle_suspend(self):
        core.set_viewport_suspended(not core._state["suspended"])

    def _toggle_recovery(self):
        if self.recovery_btn.isChecked():
            minutes = cmds.optionVar(q=RECOVERY_OPT) if cmds.optionVar(exists=RECOVERY_OPT) else 5
            self._recovery_timer.start(int(minutes * 60 * 1000))
            core.message("anim recovery on: every %d min" % minutes)
        else:
            self._recovery_timer.stop()
            core.message("anim recovery off")

    def _recovery_menu(self):
        def set_minutes(m):
            cmds.optionVar(iv=(RECOVERY_OPT, m))
            if self.recovery_btn.isChecked():
                self._recovery_timer.start(m * 60 * 1000)
        return [("Save backup now", lambda: core.message("saved " + core.save_recovery(force=True))),
                ("Open backups folder", core.open_recovery_folder),
                ("Interval", [("%d min" % m, (lambda m=m: set_minutes(m))) for m in (2, 5, 10, 20)])]

    # ---- menus

    def _sets_menu(self):
        sets = core.selection_sets()
        entries = [(label, (lambda s=node: core.select_set(s, add=_shift()))) for label, node in sets]
        entries += [None, ("Create set from selection...", core.create_selection_set)]
        if sets:
            entries.append(("Delete set", [(label, (lambda s=node: core.delete_selection_set(s)))
                                           for label, node in sets]))
        return entries

    def _paste_anim_menu(self):
        return [("Paste at current frame", core.paste_animation),
                ("Paste insert at current frame (push later keys)", lambda: core.paste_animation("insert")),
                ("Paste replacing at the copied frames", lambda: core.paste_animation("original"))]

    def _mirror_menu(self):
        return [("Mirror pose", core.mirror_pose), None,
                ("Select opposite", core.select_opposite),
                ("Add opposite to selection", lambda: core.select_opposite(add=True))]

    def _relationship_click(self):
        mods = QtWidgets.QApplication.keyboardModifiers()
        if not mods & QtCore.Qt.ShiftModifier:
            return core.copy_relationship()
        if mods & QtCore.Qt.ControlModifier:
            return core.paste_relationship(channels="t")
        if mods & QtCore.Qt.AltModifier:
            return core.paste_relationship(channels="r")
        core.paste_relationship()

    def _relationship_menu(self):
        modes = (("Translate + Rotate", "tr"), ("Translate only", "t"), ("Rotate only", "r"))
        entries = [("Copy relationship", core.copy_relationship), None]
        entries += [("Paste %s" % label, (lambda ch=ch: core.paste_relationship(channels=ch))) for label, ch in modes]
        entries.append(None)
        entries += [("Paste %s on all keys" % label, (lambda ch=ch: core.paste_relationship(all_keys=True, channels=ch)))
                    for label, ch in modes]
        return entries

    def _world_click(self):
        core.paste_world_space() if _shift() else core.copy_world_space()

    def _world_menu(self):
        return [("Copy world space", core.copy_world_space),
                ("Paste (current frame)", core.paste_world_space),
                ("Paste on all keys", lambda: core.paste_world_space(all_keys=True))]

    def _space_entries(self, all_keys):
        attrs = core.enum_attrs(core.selection())
        if not attrs:
            return [("(no enum attributes on the selection)", lambda: None)]
        return [(attr, [(name, (lambda a=attr, i=i: core.space_switch(a, i, all_keys=all_keys)))
                        for i, name in enumerate(fields)]) for attr, fields in sorted(attrs.items())]

    def _bookmark_menu(self):
        return [("Add bookmark", core.add_bookmark),
                ("Next bookmark", lambda: core.go_to_bookmark(1)),
                ("Previous bookmark", lambda: core.go_to_bookmark(-1)), None,
                ("Delete bookmark at current frame", core.delete_bookmark_here),
                ("Clear all bookmarks", core.clear_bookmarks)]

    def _bookmarks_panel(self):
        marks = core.bookmarks()
        if not marks:
            return [("(no bookmarks)", lambda: None), None, ("Add bookmark", core.add_bookmark)]
        return [("%s   %d-%d" % (name, a, b), (lambda a=a: cmds.currentTime(a))) for name, a, b in marks] + \
            [None, ("Add bookmark", core.add_bookmark), ("Clear all bookmarks", core.clear_bookmarks)]

    def _extra_menu(self):
        return [("Select rig controls", core.select_rig_controls),
                ("Select animated controls", core.select_animated),
                ("Select opposite", core.select_opposite), None,
                ("Key selection", core.key_selection),
                ("Delete static channels", core.delete_static_channels),
                ("Bake selection (time range)", core.bake_selection),
                ("Euler filter", core.euler_filter), None,
                ("Resume viewport" if core._state["suspended"] else "Suspend viewport", self._toggle_suspend)]

    def _snapshot_menu(self):
        return [("Snapshot default pose", core.snapshot_default_pose),
                ("Reset selection to default pose", core.reset_to_default_pose),
                ("Clear snapshot", core.clear_default_pose)]


# ---------------------------------------------------------------- workspace control

def _control_widget(control=CONTROL):
    import maya.OpenMayaUI as omui
    ptr = omui.MQtUtil.findControl(control)
    return wrapInstance(int(ptr), QtWidgets.QWidget) if ptr else None


def _strip_in(host):
    found = host.findChildren(QtWidgets.QWidget, BAR_NAME) if host is not None else []
    return found[0] if found else None


def embedded():
    """The strip standing as the Time Bar's top row, or None."""
    return _strip_in(_control_widget(TIMEBAR))


def current():
    """The live strip - in our own control, else in the Time Bar's - or None."""
    return _strip_in(_control_widget()) or embedded()


def _fit_timebar():
    """The Time Bar's control as tall as its page and our row on top of it."""
    try:
        from maya_timebar import bar as timebar, scene
        strip = timebar.current()
        if strip is not None:
            scene.page_height(strip)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()


def attach(host):
    """The strip as the Time Bar's top row, inside its control `host`: one surface, no splitter line
    between them. The strip."""
    strip = _strip_in(host)
    if strip is None:
        strip = ATBar(embedded=True)
        host.layout().insertWidget(0, strip)
    #  the host's own spacing (Maya's style default, 6 px) showed its grey between the two rows
    host.layout().setSpacing(0)
    strip.show()
    QtCore.QTimer.singleShot(0, strip.fit_dock)
    return strip


def detach():
    """The strip out of the Time Bar, which shrinks back to its page. True when one was there."""
    strip = embedded()
    if strip is None:
        return False
    strip.setParent(None)
    strip.deleteLater()
    _fit_timebar()
    return True


def build():
    """The workspace control's uiScript: the strip built (again) inside it."""
    host = _control_widget()
    if host is None:
        return None
    for old in host.findChildren(QtWidgets.QWidget, BAR_NAME):
        old.setParent(None)
        old.deleteLater()
    lay = host.layout()
    if lay is None:
        lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    strip = ATBar()
    lay.addWidget(strip)
    QtCore.QTimer.singleShot(0, strip.fit_dock)
    return strip
