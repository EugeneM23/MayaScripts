"""maya_hubwindow - what a section's floating window and the edge rail's card draw alike.

2026-10-18 (spec: docs/superpowers/specs/2026-10-18-floating-windows-design.md). The
animator wants the section windows in the Time Bar's style: look B (the hub's own dark
panel, a card inside it, no stripe and no title hairline), painted pill buttons that lift and
glow under the mouse and flash on a press, and the burst out of a point with the Time Bar's
racing-edge light (docs/interface-motion.md).

It holds:
- `frame_class()`: WindowFrame, the look-B frame, a CardFrame painting its own face, its
  `content` the card; the card's light (`level` / `flash`) over it;
- `pill_class()`: PillButton, a QToolButton painting itself;
- `burst_class()`: the burst effect, moved from maya_hubpop (the popups draw it from here now);
  plus `maya_hubburst.light` drawn as added light inside the shape;
- `Burster`: drives that effect out of a global point or into one.

Qt is imported lazily through maya_hubqt; the classes are made on first use.
"""

import time
import traceback

import maya_hubburst as hubburst
import maya_hubmotion as hubmotion
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle
from maya_timebar import look as tlook

ACCENT = hubstyle.TOKENS["accent"]
RIM = tlook.RIM
HOVER_MS = tlook.HOVER_MS
FLASH_MS = float(tlook.FLASH_MS)   # a press
TICK_MS = 16
PILL_W, PILL_H = 24, 22  # logical px: the face
PILL_PAD = 4             # room round the face for the lift and the first rings
PILL_RADIUS = 5
PILL_ICON = 14

_CLASSES = {}


def _now():
    return time.monotonic() * 1000.0


def _approach(value, goal, dt, ms):
    """The Time Bar's ease (maya_timebar.look.approach)."""
    return tlook.approach(value, goal, dt, ms)


# ------------------------------------------------------------------ the frame

def frame_class():
    """WindowFrame(scale, parent=None): the look-B frame. Its face is `panel` with a 1 px
    `track_edge` outline (radius 8); its `content` (a child the caller makes and names) is
    filled `card` (radius 6). No stripe, no accent, no title hairline. The card's light
    (`level`, `flash`: maya_hubqt.paint_light) is drawn over it all."""
    if "frame" not in _CLASSES:
        q = hubqt.qt()
        QtCore, QtGui = q.QtCore, q.QtGui
        base = hubqt._frame_class()
        tokens = hubstyle.TOKENS

        class WindowFrame(base):

            def __init__(self, scale=1.0, parent=None):
                super(WindowFrame, self).__init__(scale, parent)
                self.content = None
                self._failed = False

            def paintEvent(self, event):                   # noqa: N802
                # not the CardFrame's: it would paint the skin's QFrame[skCard] face
                if self._failed:
                    return
                try:
                    self._paint()
                except Exception:                            # noqa: BLE001
                    self._failed = True
                    traceback.print_exc()

            def _paint(self):
                s = self.scale
                painter = QtGui.QPainter(self)
                try:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing)
                    r = float(hubstyle.px(8, s))
                    outer = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
                    painter.setPen(QtGui.QPen(QtGui.QColor(tokens["track_edge"]), 1.0))
                    painter.setBrush(QtGui.QColor(tokens["panel"]))
                    painter.drawRoundedRect(outer, r, r)
                    content = self.content
                    if content is not None and hubqt._valid(content) \
                            and content.isVisible():
                        rect = QtCore.QRectF(content.geometry())
                        if content.parentWidget() is not self:
                            top = content.mapTo(self, QtCore.QPoint(0, 0))
                            rect = QtCore.QRectF(top.x(), top.y(),
                                                 content.width(), content.height())
                        rc = float(hubstyle.px(6, s))
                        painter.setPen(QtCore.Qt.NoPen)
                        painter.setBrush(QtGui.QColor(tokens["card"]))
                        painter.drawRoundedRect(rect, rc, rc)
                finally:
                    painter.end()
                if self.level > 0.002 or self.flash > 0.002:
                    hubqt.paint_light(self, self.level, self.flash, self.scale)

        _CLASSES["frame"] = WindowFrame
    return _CLASSES["frame"]


def dress(frame, scale):
    """No stylesheet face over ours: the frame paints no styled background and its content
    is transparent. The frame's `skCard` property is NOT set (the skin's rule would paint
    it). The content's rule names the content alone: a selector-less rule reaches every
    widget under it, and the section's fields would lose their faces (trap 98)."""
    q = hubqt.qt()
    frame.setAttribute(q.QtCore.Qt.WA_StyledBackground, False)
    content = getattr(frame, "content", None)
    if content is not None:
        name = content.objectName()
        if name:
            content.setStyleSheet("#{0} {{ background: transparent; }}".format(name))
        else:
            content.setAttribute(q.QtCore.Qt.WA_StyledBackground, False)


TITLE_H = 34             # logical px: the title row, room for a 30-tall pill (2026-10-18)


def title_label(text, scale, name):
    """The look-B title's name (a section window's and the edge rail card's,
    2026-10-18): `text` in capitals, the heading role's look - spaced, bold,
    `muted`, at the caption size - on no background, named `name`."""
    q = hubqt.qt()
    label = hubqt._named(q.QtWidgets.QLabel((text or "").upper()), name)
    label.setStyleSheet(
        "color: {0}; font-weight: bold; letter-spacing: {2}px; font-size: {1}px; "
        "background: transparent;".format(hubstyle.TOKENS["muted"],
                                          hubstyle.px(8.5, scale),
                                          hubstyle.px(1, scale)))
    return label


def title_icon(icon_name, colour, scale, name):
    """The look-B title's icon: in its group colour, with no chip (15 px)."""
    q = hubqt.qt()
    icon = hubqt._named(q.QtWidgets.QLabel(), name)
    icon.setPixmap(hubqt.pixmap(icon_name, colour, hubstyle.px(15, scale)))
    icon.setStyleSheet("background: transparent;")
    return icon


# ------------------------------------------------------------------- the pill

def pill_class():
    """PillButton(icon_name, scale, parent=None): a painted button, its 24 x 22 face (radius
    5, `field`, a 1 px `track_edge`) centred in a 32 x 30 widget, so the lift and the first
    rings show (the outer rings reaching past 4 px are clipped; review 2026-10-18). Under the mouse it lifts +10 %, its face `hover`, four
    accent rings outside it; a press flashes 120 ms (face `accent`, -6 %, the icon
    `on_accent`). `set_lit(on)` shows the icon in `accent_text` (its window stands)."""
    if "pill" not in _CLASSES:
        q = hubqt.qt()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        tokens = hubstyle.TOKENS

        class PillButton(QtWidgets.QToolButton):

            def __init__(self, icon_name, scale=1.0, parent=None):
                super(PillButton, self).__init__(parent)
                self.scale = scale
                self.icon_name = icon_name
                self.level = 0.0
                self.lit = False
                self._hovered = False
                self._press_t0 = None
                self._failed = False
                self._icons = {}
                self.setFixedSize(hubstyle.px(PILL_W + 2 * PILL_PAD, scale),
                                  hubstyle.px(PILL_H + 2 * PILL_PAD, scale))
                self.setAutoRaise(True)
                self.setCursor(QtCore.Qt.PointingHandCursor)
                #  its own lift and glow: the hub's ink glow passes it by
                #  (maya_hubqt.glowing; the edge rail card's pills stand in the hub)
                self.setProperty("skOwnLight", True)
                self.timer = QtCore.QTimer(self)
                self.timer.setInterval(TICK_MS)
                self.timer.timeout.connect(self._tick)
                self._last = _now()

            # --- state
            def set_icon(self, name):
                if name != self.icon_name:
                    self.icon_name = name
                    self._icons = {}
                    self.update()

            def set_lit(self, on):
                on = bool(on)
                if on != self.lit:
                    self.lit = on
                    self.update()

            def hover(self, on):
                self._hovered = bool(on)
                if not hubmotion.enabled():
                    self.level = 1.0 if on else 0.0
                    self.update()
                    return
                self._start()

            def press(self):
                if not hubmotion.enabled():
                    self._press_t0 = None
                    return
                self._press_t0 = _now()
                self._start()

            def flash_at(self, age):
                if age is None or age < 0.0 or age >= FLASH_MS:
                    return 0.0
                return max(0.0, 1.0 - age / FLASH_MS)

            def _flash(self):
                if self._press_t0 is None:
                    return 0.0
                return self.flash_at(_now() - self._press_t0)

            def _start(self):
                self._last = _now()
                if not self.timer.isActive():
                    self.timer.start()

            def _tick(self):
                now = _now()
                dt, self._last = now - self._last, now
                try:
                    self.advance(dt)
                except Exception:                            # noqa: BLE001
                    self.timer.stop()
                    traceback.print_exc()

            def advance(self, dt):
                goal = 1.0 if self._hovered else 0.0
                self.level = _approach(self.level, goal, dt, HOVER_MS)
                if self.level == goal and self._flash() == 0.0:
                    self._press_t0 = None
                    self.timer.stop()
                self.update()

            # --- events
            def enterEvent(self, event):                   # noqa: N802
                self.hover(True)
                super(PillButton, self).enterEvent(event)

            def leaveEvent(self, event):                   # noqa: N802
                self.hover(False)
                super(PillButton, self).leaveEvent(event)

            def mousePressEvent(self, event):              # noqa: N802
                self.press()
                super(PillButton, self).mousePressEvent(event)

            # --- paint
            def _pix(self, colour):
                pix = self._icons.get(colour)
                if pix is None:
                    pix = hubqt.pixmap(self.icon_name, colour,
                                       hubstyle.px(PILL_ICON, self.scale))
                    self._icons[colour] = pix
                return pix

            def paintEvent(self, event):                   # noqa: N802
                if self._failed:
                    return
                try:
                    self._paint()
                except Exception:                            # noqa: BLE001
                    self._failed = True
                    traceback.print_exc()

            def _paint(self):
                sc = self.scale
                level, flash = self.level, self._flash()
                s = 1.0 + 0.10 * level - 0.06 * flash
                w, h = float(self.width()), float(self.height())
                face_w = hubstyle.px(PILL_W, sc) / 1.0
                face_h = hubstyle.px(PILL_H, sc) / 1.0
                painter = QtGui.QPainter(self)
                try:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing)
                    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                    painter.translate(w / 2.0, h / 2.0)
                    painter.scale(s, s)
                    rect = QtCore.QRectF(-face_w / 2.0 + 0.5, -face_h / 2.0 + 0.5,
                                         face_w - 1.0, face_h - 1.0)
                    r = float(hubstyle.px(PILL_RADIUS, sc))
                    face = hubstyle.mix(tokens["field"], tokens["hover"], level)
                    face = hubstyle.mix(face, tokens["accent"], flash)
                    painter.setPen(QtGui.QPen(QtGui.QColor(tokens["track_edge"]), 1.0))
                    painter.setBrush(QtGui.QColor(face))
                    painter.drawRoundedRect(rect, r, r)
                    if level > 0.002:
                        painter.setBrush(QtCore.Qt.NoBrush)
                        glow = QtGui.QColor(tokens["accent"])
                        for i in range(4):
                            glow.setAlphaF(min(1.0, 46.0 * level * (5 - i) / 4.0 / 255.0))
                            painter.setPen(QtGui.QPen(glow, 1.6 * sc))
                            d = -(1.6 * i + 0.8) * sc
                            painter.drawRoundedRect(rect.adjusted(d, d, -d, -d),
                                                    r - d, r - d)
                    if flash > 0.5:
                        colour = tokens["on_accent"]
                    elif self.lit:
                        colour = tokens["accent_text"]
                    else:
                        colour = tokens["muted"]
                    pix = self._pix(colour)
                    pw, ph = pix.width(), pix.height()
                    painter.drawPixmap(QtCore.QRectF(-pw / 2.0, -ph / 2.0, pw, ph), pix,
                                       QtCore.QRectF(0, 0, pw, ph))
                finally:
                    painter.end()

        _CLASSES["pill"] = PillButton
    return _CLASSES["pill"]


# ----------------------------------------------------------------- the burst

def _band(p, QtCore, QtGui, axis, pos, half, colour, alpha, shape):
    """One racing edge's band of added light, across the shape."""
    x0, y0, x1, y1 = shape
    c = QtGui.QColor(colour)
    clear = QtGui.QColor(c)
    clear.setAlphaF(0.0)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    if axis == "x":
        grad = QtGui.QLinearGradient(pos - half, 0, pos + half, 0)
        rect = QtCore.QRectF(pos - half, y0, 2 * half, y1 - y0)
    else:
        grad = QtGui.QLinearGradient(0, pos - half, 0, pos + half)
        rect = QtCore.QRectF(x0, pos - half, x1 - x0, 2 * half)
    grad.setColorAt(0.0, clear)
    grad.setColorAt(0.5, c)
    grad.setColorAt(1.0, clear)
    p.fillRect(rect, QtGui.QBrush(grad))


def _top(p, QtCore, QtGui, x0, x1, top, depth, line):
    """The card's lit top edge: a line and a glow fading down."""
    c = QtGui.QColor(ACCENT)
    c.setAlphaF(min(1.0, 0.95 * top))
    p.fillRect(QtCore.QRectF(x0, 0, x1 - x0, line), c)
    grad = QtGui.QLinearGradient(0, 0, 0, depth)
    g = QtGui.QColor(ACCENT)
    g.setAlphaF(min(1.0, 0.32 * top))
    clear = QtGui.QColor(ACCENT)
    clear.setAlphaF(0.0)
    grad.setColorAt(0.0, g)
    grad.setColorAt(1.0, clear)
    p.fillRect(QtCore.QRectF(x0, 0, x1 - x0, depth), QtGui.QBrush(grad))


def burst_class():
    """The burst (2026-10-17, maya_hubburst; moved here from maya_hubpop 2026-10-18): a
    QGraphicsEffect on the frame, DISABLED at rest so the frame paints as it always has
    (trap 204). While a burst runs it takes the frame's picture once and draws it each tick:
    the whole picture, each row's place filled with the card's face, each row's piece back at
    its opacity and scale, all of it masked by the rounded shape and drawn at the face's
    opacity - then the Time Bar's racing-edge light (`maya_hubburst.light`) added inside the
    shape. Maya's controls are never touched; their text is grayscale-antialiased only while
    the picture stands in (trap 202). A failure marks it `broken` and the frame is drawn as it
    is from then on."""
    if "burst" not in _CLASSES:
        q = hubqt.qt()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

        class PopupBurst(QtWidgets.QGraphicsEffect):

            def __init__(self, planner, parent=None):
                super(PopupBurst, self).__init__(parent)
                self.planner = planner      # opening -> (hubburst.Plan, (r, g, b) face)
                self.opening = True
                self.ms = 0.0
                self.plan = None
                self.face = None
                self.pix = None
                self.offset = QtCore.QPoint()
                self.ratio = 1.0
                self.draws = 0
                self.broken = False
                self.error = None
                self._image = None
                self._mask = None
                self.setEnabled(False)

            def begin(self, opening):
                self.opening = opening
                self.ms = 0.0
                self.plan = None
                self.pix = None
                self.setEnabled(True)

            def stop(self):
                self.plan = None
                self.pix = None
                self._image = None
                self._mask = None
                self.setEnabled(False)

            def done(self):
                return self.broken or (self.plan is not None
                                       and self.ms >= self.plan.total)

            def draw(self, painter):
                if self.broken:
                    self.drawSource(painter)
                    return
                try:
                    if not self._draw(painter):
                        self.drawSource(painter)
                except Exception:                            # noqa: BLE001
                    self.broken = True
                    self.error = traceback.format_exc()
                    traceback.print_exc()                    # once: broken from now on
                    self.drawSource(painter)

            def _take(self):
                offset = QtCore.QPoint()
                pix = self.sourcePixmap(QtCore.Qt.DeviceCoordinates, offset,
                                        QtWidgets.QGraphicsEffect.NoPad)
                if pix.isNull():
                    return False
                inner = self.sourceBoundingRect(QtCore.Qt.LogicalCoordinates)
                self.pix = pix
                self.offset = QtCore.QPoint(offset)
                self.ratio = pix.width() / max(1.0, float(inner.width()))
                self.plan, self.face = self.planner(self.opening)
                fmt = QtGui.QImage.Format_ARGB32_Premultiplied
                self._image = QtGui.QImage(pix.width(), pix.height(), fmt)
                self._mask = QtGui.QImage(pix.width(), pix.height(), fmt)
                return True

            def _draw(self, painter):
                if self.pix is None and not self._take():
                    return False
                if self.plan is None:
                    return False
                k = self.ratio
                state = hubburst.at(self.plan, self.ms)
                face = QtGui.QColor(*self.face)
                image = self._image
                image.fill(0)
                p = QtGui.QPainter(image)
                try:
                    p.drawPixmap(0, 0, self.pix)
                    rects = [QtCore.QRectF(r[0] * k, r[1] * k, r[2] * k, r[3] * k)
                             for r in self.plan.parts]
                    for rect in rects:
                        p.fillRect(rect, face)
                    p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
                    for rect, piv, (op, sc) in zip(rects, self.plan.pivots, state.parts):
                        if op <= 0.002:
                            continue
                        px, py = rect.left() + piv[0] * k, rect.top() + piv[1] * k
                        p.save()
                        p.setOpacity(min(1.0, op))
                        p.translate(px, py)
                        p.scale(sc, sc)
                        p.translate(-px, -py)
                        p.drawPixmap(rect, self.pix, rect)
                        p.restore()
                    mask = self._mask
                    mask.fill(0)
                    m = QtGui.QPainter(mask)
                    try:
                        m.setRenderHint(QtGui.QPainter.Antialiasing, True)
                        m.setPen(QtCore.Qt.NoPen)
                        m.setBrush(QtGui.QColor(0, 0, 0))
                        x0, y0, x1, y1 = state.shape
                        r = state.radius * k
                        m.drawRoundedRect(QtCore.QRectF(x0 * k, y0 * k, (x1 - x0) * k,
                                                        (y1 - y0) * k), r, r)
                    finally:
                        m.end()
                    p.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationIn)
                    p.drawImage(0, 0, mask)
                    lit = hubburst.light(self.plan, self.ms)
                    if lit.edges or lit.top > 0.003:
                        p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
                        x0, y0, x1, y1 = (v * k for v in state.shape)
                        clip = QtGui.QPainterPath()
                        rr = state.radius * k
                        clip.addRoundedRect(QtCore.QRectF(x0, y0, x1 - x0, y1 - y0), rr, rr)
                        p.setClipPath(clip)              # the shape itself, corners too
                        sc = self.plan.scale * k
                        for axis, pos, inten in lit.edges:
                            for half, colour, alpha in (
                                    (hubburst.EDGE_GLOW * sc, ACCENT, 0.55 * inten),
                                    (hubburst.EDGE_CORE * sc, RIM, 0.9 * inten)):
                                _band(p, QtCore, QtGui, axis, pos * k, half, colour, alpha,
                                      (x0, y0, x1, y1))
                        if lit.top > 0.003:
                            _top(p, QtCore, QtGui, x0, x1, lit.top, hubburst.TOP_GLOW * sc,
                                 max(1.0, 1.5 * sc))
                finally:
                    p.end()
                painter.save()
                try:
                    painter.setWorldTransform(QtGui.QTransform())
                    painter.setOpacity(max(0.0, min(1.0, state.face)))
                    painter.drawImage(self.offset, image)
                finally:
                    painter.restore()
                self.draws += 1
                return True

        _CLASSES["burst"] = PopupBurst
    return _CLASSES["burst"]


class Burster(object):
    """A frame's burst out of a global point, or its fold into one (maya_hubburst), drawn by
    the held effect; `on_tick(shape)` hears the shape each tick (the edge's mask)."""

    def __init__(self, frame, parts, face, scale):
        self.frame, self.parts, self.face, self.scale = frame, parts, face, scale
        self.effect = None
        self.anim = None
        self._origin = None
        self._done = None
        self._on_tick = None
        self._spent = None

    def busy(self):
        try:
            return bool(self.effect is not None and self.effect.isEnabled())
        except RuntimeError:
            return False

    def _plan(self, opening):
        q = hubqt.qt()
        o = self.frame.mapFromGlobal(q.QtCore.QPoint(int(self._origin[0]),
                                                     int(self._origin[1])))
        make = hubburst.plan_open if opening else hubburst.plan_close
        return (make((o.x(), o.y()), (self.frame.width(), self.frame.height()),
                     self.parts(), self.scale), self.face())

    def run(self, opening, origin, done, on_tick=None):
        """Start a burst (`opening`) or a fold toward the global `origin`; `done` is called
        when it ends. False when it cannot start (animations off, no frame, a failure)."""
        if not hubmotion.enabled() or self.frame is None or not hubqt._valid(self.frame):
            return False
        try:
            if self.effect is None:
                self.effect = burst_class()(self._plan)
                self.frame.setGraphicsEffect(self.effect)    # held: trap 201
            self.stop()
            self._origin = origin
            self._done, self._on_tick = done, on_tick
            self.effect.begin(opening)
            self.frame.update()
        except Exception:                                        # noqa: BLE001
            traceback.print_exc()
            self.stop()
            return False
        q = hubqt.qt()
        anim = q.QtCore.QVariantAnimation()
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(int(hubburst.MAX_MS))
        anim.valueChanged.connect(lambda v: self._tick(v * hubburst.MAX_MS))
        anim.finished.connect(self._finish)
        self.anim = anim
        anim.start()
        return True

    def tick_now(self):
        """One tick at the effect's current ms (the tests hold the animation)."""
        self._tick(self.effect.ms)

    def _tick(self, ms):
        effect = self.effect
        if effect is None:
            return
        try:
            effect.ms = ms
            if effect.plan is None:
                #  the plan is geometry alone: made here when no paint has made
                #  it yet (a frame masked down to nothing may never be painted;
                #  review 2026-10-18). The effect's first paint makes the same.
                effect.plan, effect.face = self._plan(effect.opening)
            self.frame.update()
            if self._on_tick is not None and effect.plan is not None:
                self._on_tick(hubburst.at(effect.plan, ms).shape)
            if effect.done():
                self._finish()
        except RuntimeError:                                     # the frame is gone
            self.stop()
        except Exception:                                        # noqa: BLE001
            traceback.print_exc()                                # a driver that raises stops
            self._finish()

    def _finish(self):
        done, self._done = self._done, None
        self.stop()
        if done is not None:
            done()

    def stop(self):
        anim, self.anim = self.anim, None
        if anim is not None:
            self._spent = anim          # not collected while its own signal runs
            try:
                anim.stop()
            except RuntimeError:
                pass
        if self.effect is not None:
            try:
                self.effect.stop()
                self.frame.update()
            except RuntimeError:
                self.effect = None
