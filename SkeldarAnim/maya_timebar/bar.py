"""The Time Bar (2026-10-16): Maya's two rows - the range row on top, the time row
below - painted in the hub's look and moving as the radial menu does.

Range row: animation start | playback start | the range block | playback end |
animation end | bookmarks (previous, add, next) | character set | layer | fps |
loop | cached playback | speed | sound | Auto key | preferences.
Time row: the timeline (bookmarks, the sound's waveform, keys and breakdowns, the
highlight that moves and scales keys, the playhead) | the current frame | eight
transport buttons.

Motion: the controls open from small with a bounce, lift and glow under the
mouse, flash on a press; the key under the mouse grows; a key the playhead
reaches lights up and fades back. ⋮ -> Interface animations off makes it all
instant. The widget talks to Maya only through a `link` (scene.py in Maya, a
fake in the tests); the jobs find the strip through the module state - never a
held wrapper (trap 135).
Spec: docs/superpowers/specs/2026-10-16-time-bar-design.md
"""

import math
import time
import traceback

from . import CONTROL, look, _state

ROOT_NAME = "skeldarTimeBarRoot"
TIMER_MS = 250
FRAME_MS = 16
HOVER_MS = 110          # the radial menu's lift
FLASH_MS = 120          # a press
POP_MS = 200            # a toggle
KEY_FADE_MS = 600       # a key the playhead reached
LIFT = 0.10             # +10 % under the mouse
KEY_LIFT = 0.6          # a key grows 60 % (under the mouse or reached)
PAD = 10                # logical px either side of the timeline's frames
TIMELINE_H = 40         # logical px: the bookmarks band, the keys, the ruler
BAND_H = 11             # the bookmarks band, its name inside
LABEL_H = 11            # the frame numbers' row at the very top, the band under it (2026-10-17)
KEY_Y = 21              # the keys' centre
KEY_W = 2.5             # a key's mark, logical px wide (2026-10-17: a line, as Maya's)
DASH_W = 0.8            # a key between frames: its dashes this share of a mark's width
DASH, DASH_GAP = 3.0, 2.0
HEAD_FILL = 70          # the playhead's cell, its fill's alpha


def key_span(h, ui):
    """(top, bottom) of a key's mark: under the bookmarks band to the bottom."""
    return (LABEL_H + 1) * ui, h - 1.5 * ui

REC = "#e0524a"
BREAKDOWN = "#6fb7c9"
HIGHLIGHT = "#7fa9e6"
WAVE = "#565a68"
RIM = "#fff1e2"

#  the mockup's glyphs (16 x 16 SVG paths), drawn with QtSvg in the control's colour
GLYPHS = {
    "start": "M2 3h2v10H2zM9 3v10L4 8zM15 3v10l-5-5z",
    "pfrm": "M3 3h2v10H3zM13 3v10L6 8z",
    "pkey": "M3 3h2v10H3zM13 3v10L6 8zM11 2l2 2-2 2-2-2z",
    "back": "M11 3v10L3 8z",
    "play": "M5 3l8 5-8 5z",
    "pause": "M4 3h3v10H4zM9 3h3v10H9z",
    "nkey": "M11 3h2v10h-2zM3 3v10l7-5zM5 2l2 2-2 2-2-2z",
    "nfrm": "M11 3h2v10h-2zM3 3v10l7-5z",
    "end": "M12 3h2v10h-2zM7 3v10l5-5zM1 3v10l5-5z",
    "bm_prev": "M10 2h4v12l-2-2-2 2zM2 8l6-4v8z",
    "bm_add": "M4 2h8v12l-4-3-4 3zM7.3 4v2h-2v1.4h2v2h1.4v-2h2V6h-2V4z",
    "bm_next": "M2 2h4v12l-2-2-2 2zM14 8L8 4v8z",
    "loop": ("M4 5h7V3l3 3-3 3V7H4a1 1 0 0 0-1 1v1H1V8a3 3 0 0 1 3-3zM12 11H5v2l-3-3 3-3v2h7a1 1 0 "
             "0 0 1-1V7h2v1a3 3 0 0 1-3 3z"),
    "once": "M1 7h9V4l5 4-5 4V9H1z",
    "oscillate": "M1 8l4-4v3h6V4l4 4-4 4V9H5v3z",
    "cache": "M2 4h12v3H2zM2 9h12v3H2z",
    "sound": "M2 6h3l4-3v10L5 10H2zM11 4.6l1-1a6.4 6.4 0 0 1 0 8.8l-1-1a5 5 0 0 0 0-6.8z",
    "auto": "M8 2a6 6 0 1 1 0 12A6 6 0 0 1 8 2zm0 1.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9zM8 5a3 3 0 1 1 0 6 3 3 0 0 1 0-6z",
    "pin": "M9.5 1.5l5 5-1.4 1.4-1.1-.4-2.6 2.6.4 3.1-1.4 1.4-3-3-3.4 3.4-1-1 3.4-3.4-3-3 1.4-1.4 3.1.4 2.6-2.6-.4-1.1z",
    "prefs": ("M7 1h2l.4 1.8 1.4.6 1.6-1 1.4 1.4-1 1.6.6 1.4L15 7v2l-1.8.4-.6 1.4 1 1.6-1.4 1.4-1.6-1-1.4.6"
              "L9 15H7l-.4-1.8-1.4-.6-1.6 1-1.4-1.4 1-1.6-.6-1.4L1 9V7l1.8-.4.6-1.4-1-1.6 1.4-1.4 1.6 1 1.4-.6z"
              "M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z"),
}


class Link(object):
    """The strip's road into Maya: scene.py, plus going back to Maya's slider."""

    def __getattr__(self, name):
        from . import scene
        return getattr(scene, name)

    def measure(self):
        from . import meter
        return meter.start()

    def back_to_maya(self):
        import maya.cmds as cmds
        from . import hide
        message = hide()
        cmds.inViewMessage(assistMessage=message, position="topCenter", fade=True)


def _tokens():
    import maya_hubstyle
    return maya_hubstyle.TOKENS


def animations_on():
    """⋮ -> Interface animations (maya_hubmotion; on where it cannot be asked)."""
    try:
        import maya_hubmotion
        return bool(maya_hubmotion.enabled())
    except Exception:                                        # noqa: BLE001
        return True


def stylesheet(tokens, ui):
    px = lambda v: "%dpx" % max(1, int(round(v * ui)))              # noqa: E731
    return (
        "QWidget#{root} {{ background: {panel}; }}"
        "QLineEdit#skeldarTimeBarField {{ background: {field}; color: {text};"
        " border: 1px solid {track_edge}; border-radius: {r5}; padding: 0 {p6};"
        " font-family: Consolas, monospace; }}"
        "QLineEdit#skeldarTimeBarField:hover {{ border-color: {accent}; }}"
        "QLineEdit#skeldarTimeBarField:focus {{ border: 2px solid {accent}; }}"
        "QLineEdit#skeldarTimeBarFrame {{ background: {field}; color: {accent_text};"
        " border: 1px solid {accent}; border-radius: {r5}; padding: 0 {p6};"
        " font-family: Consolas, monospace; font-weight: 600; }}"
        "QLineEdit#skeldarTimeBarFrame:focus {{ border: 2px solid {accent}; }}"
        "QFrame#skeldarTimeBarSep {{ background: {line}; }}"
        "QMenu {{ background: {card}; color: {text}; border: 1px solid {line}; padding: {p4}; }}"
        "QMenu::item {{ padding: {p4} {p12}; border-radius: {r4}; }}"
        "QMenu::item:selected {{ background: {hover}; }}"
        "QMenu::item:disabled {{ color: {faint}; }}"
        "QMenu::separator {{ height: 1px; background: {line}; margin: {p4} {p2}; }}"
    ).format(root=ROOT_NAME, p2=px(2), p4=px(4), p6=px(6), p12=px(12), r4=px(4), r5=px(5), **tokens)


def classes():
    """(Strip, Timeline, RangeBlock, Pill), made on first use (no Qt at import)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    QtSvg = getattr(q, "QtSvg", None)
    renderers = {}

    def colour(hex_, alpha=255):
        c = QtGui.QColor(hex_)
        c.setAlpha(int(max(0, min(255, alpha))))
        return c

    def blend(a, b, u):
        ca, cb = QtGui.QColor(a), QtGui.QColor(b)
        u = max(0.0, min(1.0, u))
        return QtGui.QColor(int(ca.red() + (cb.red() - ca.red()) * u),
                            int(ca.green() + (cb.green() - ca.green()) * u),
                            int(ca.blue() + (cb.blue() - ca.blue()) * u))

    def draw_glyph(p, name, rect, colour_):
        path = GLYPHS.get(name)
        if not path:
            return
        hex_ = colour_.name()
        key = (name, hex_)
        renderer = renderers.get(key)
        if renderer is None and QtSvg is not None:
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path fill="%s" '
                   'fill-rule="evenodd" d="%s"/></svg>') % (hex_, path)
            renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
            renderers[key] = renderer
        if renderer is not None:
            renderer.render(p, rect)

    halos = {}

    def halo(hex_, ui):
        """A key's glow at full strength - three rings fading outward - drawn once
        per colour and size into a picture: a lit key is one drawPixmap, not three
        antialiased rectangles (2026-10-16, a dense take lights dozens at a time)."""
        key = (hex_, round(ui, 3))
        picture = halos.get(key)
        if picture is None:
            z = 1.0 + KEY_LIFT
            kw, kh = 3 * ui * min(z, 1.5), 14 * ui * z
            grow = 4.5 * ui
            w, h = kw + 2 * grow, kh + 2 * grow
            picture = QtGui.QPixmap(int(round(w * 2)), int(round(h * 2)))
            picture.setDevicePixelRatio(2.0)
            picture.fill(Qt.transparent)
            hp = QtGui.QPainter(picture)
            hp.setRenderHint(QtGui.QPainter.Antialiasing)
            hp.setPen(Qt.NoPen)
            body = QtCore.QRectF(grow, grow, kw, kh)
            for i in range(3, 0, -1):
                g = i * 1.5 * ui
                hp.setBrush(colour(hex_, 40 * (4 - i) / 3.0))
                hp.drawRoundedRect(body.adjusted(-g, -g, g, g), 1.5 * ui + g, 1.5 * ui + g)
            hp.end()
            halos[key] = picture
        return picture

    def add_key(path, x, h, ui, whole, width=None, cell=None, grow=0.0):
        """A key's mark into `path`: on a whole frame its frame's cell filled, with a
        gap between neighbours (`cell`, px a frame; the animator's mockup, 2026-10-17),
        grown by `grow` when lit; where it stands between frames a dashed line on its
        time (Maya's slider: the mark is where the key is in time)."""
        top, bottom = key_span(h, ui)
        if whole and cell:
            l, tp, w, hh = look.key_cell(x, cell, top, bottom, ui)
            path.addRoundedRect(QtCore.QRectF(l - grow, tp - grow, w + 2 * grow, hh + 2 * grow),
                                1.5 * ui, 1.5 * ui)
            return
        kw = (width or KEY_W * ui) * (1.0 if whole else DASH_W)
        if whole:
            path.addRect(QtCore.QRectF(x - kw / 2, top, kw, bottom - top))
            return
        dash, gap = DASH * ui, DASH_GAP * ui
        y = top
        while y < bottom:
            path.addRect(QtCore.QRectF(x - kw / 2, y, kw, min(dash, bottom - y)))
            y += dash + gap

    def glow(p, rect, radius, hex_, level, ui):
        """The radial menu's lit ring: rings fading outward, then a 2 px edge."""
        if level <= 0.01:
            return
        p.setBrush(Qt.NoBrush)
        for i in range(4, 0, -1):
            p.setPen(QtGui.QPen(colour(hex_, 46 * level * (5 - i) / 4.0), max(1.0, ui)))
            grow = i * 1.6 * ui
            p.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow), radius + grow, radius + grow)
        p.setPen(QtGui.QPen(colour(hex_, 255 * level), 2 * ui))
        p.drawRoundedRect(rect, radius, radius)

    def soft_dot(p, cx, cy, r, hex_, alpha):
        """A round glow: a radial gradient from `alpha` at the centre to nothing."""
        if r <= 0.5 or alpha <= 1:
            return
        g = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), r)
        g.setColorAt(0.0, colour(hex_, alpha))
        g.setColorAt(0.45, colour(hex_, alpha * 0.45))
        g.setColorAt(1.0, colour(hex_, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QBrush(g))
        p.drawEllipse(QtCore.QPointF(cx, cy), r, r)

    # -- a painted control -------------------------------------------------------

    class Pill(QtWidgets.QAbstractButton):
        """A button the strip paints and moves: an icon, a text or both; plain,
        a chip, the orange play, a toggle lit when on."""

        def __init__(self, strip, glyph="", text="", tip="", style="plain", toggle=False, accent_glyph=False):
            super(Pill, self).__init__(strip)
            self.strip, self.glyph, self.style_ = strip, glyph, style
            self.accent_glyph = accent_glyph
            self.setText(text)
            self.setToolTip(tip)
            self.setCheckable(toggle)
            self.setCursor(Qt.PointingHandCursor)
            self.hover = 0.0            # 0..1, eased toward self.goal
            self.goal = 0.0
            self.flash_at = None
            self.pop_at = None
            self._was_busy = False
            self.index = strip.register(self)
            self._fit()

        def margin(self):
            return int(round(5 * self.strip.ui))

        def _font(self):
            font = QtGui.QFont(self.font())
            font.setPixelSize(max(9, int(12 * self.strip.ui)))
            return font

        def _fit(self):
            ui, m = self.strip.ui, self.margin()
            h = int(24 * ui)
            if self.text():
                w = QtGui.QFontMetrics(self._font()).horizontalAdvance(self.text()) + int(20 * ui)
                if self.glyph:
                    w += int(18 * ui)
            else:
                w = int(26 * ui)
            self.setFixedSize(w + 2 * m, h + 2 * m)

        def set_label(self, text):
            if text != self.text():
                self.setText(text)
                self._fit()
                self.update()

        def enterEvent(self, event):
            self.goal = 1.0
            self.strip.kick()
            super(Pill, self).enterEvent(event)

        def leaveEvent(self, event):
            self.goal = 0.0
            self.strip.kick()
            super(Pill, self).leaveEvent(event)

        def mousePressEvent(self, event):
            self.flash_at = self.strip.clock()
            self.strip.kick()
            super(Pill, self).mousePressEvent(event)

        def nextCheckState(self):
            super(Pill, self).nextCheckState()
            self.pop_at = self.strip.clock()

        def busy(self, now):
            return (abs(self.hover - self.goal) > 0.005
                    or (self.flash_at is not None and now - self.flash_at < FLASH_MS)
                    or (self.pop_at is not None and now - self.pop_at < POP_MS))

        def step(self, dt):
            self.hover = look.approach(self.hover, self.goal, dt, HOVER_MS) if self.strip.motion else self.goal

        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            s, tk, ui = self.strip, self.strip.tokens, self.strip.ui
            now = s.clock()
            scale, opacity = s.opening_of(self.index)
            flash = 0.0
            if self.flash_at is not None and s.motion and now - self.flash_at < FLASH_MS:
                flash = 1.0 - (now - self.flash_at) / float(FLASH_MS)
            pop = 1.0
            if self.pop_at is not None and s.motion and now - self.pop_at < POP_MS:
                pop = 0.7 + 0.3 * look.back_out((now - self.pop_at) / float(POP_MS))
            z = scale * pop * (1.0 + LIFT * self.hover) * (1.0 - 0.06 * flash)
            m = self.margin()
            base = QtCore.QRectF(self.rect()).adjusted(m, m, -m, -m)
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setOpacity(opacity)
            c = base.center()
            p.translate(c)
            p.scale(z, z)
            p.translate(-c)
            radius = (base.height() / 2.0) if self.style_ == "chip" else 5 * ui
            on = self.isCheckable() and self.isChecked()
            if self.style_ == "play":
                face = blend(tk["accent"], tk["accent_hover"], self.hover)
            elif self.style_ == "chip":
                face = blend(tk["card"], tk["hover"], self.hover)
            elif on:
                face = colour("#3a2323") if self.style_ == "rec" else colour(tk["accent_tint"])
            else:
                face = colour(tk["hover"], 255 * self.hover)
            if flash > 0:
                face = blend(face.name(), tk["accent"], flash)
            p.setPen(QtGui.QPen(colour(tk["line"]), 1) if self.style_ == "chip" else Qt.NoPen)
            p.setBrush(face)
            p.drawRoundedRect(base, radius, radius)
            glow(p, base, radius, RIM if self.style_ == "play" else tk["accent"], self.hover, ui)
            if self.style_ == "play" or flash > 0.5:
                ink = colour(tk["on_accent"])
            elif self.style_ == "rec" and on:
                ink = colour(REC)
            elif on or self.accent_glyph:
                ink = colour(tk["accent_text"])
            else:
                ink = blend(tk["muted"], tk["text"], self.hover)
            left = base.left()
            if self.glyph:
                side = 15 * ui
                gx = base.center().x() - side / 2 if not self.text() else base.left() + 9 * ui
                draw_glyph(p, self.glyph, QtCore.QRectF(gx, base.center().y() - side / 2, side, side), ink)
                left = gx + side + 4 * ui
            if self.text():
                p.setFont(self._font())
                p.setPen(ink)
                if self.glyph:
                    p.drawText(QtCore.QRectF(left, base.top(), base.right() - left - 6 * ui, base.height()),
                               Qt.AlignVCenter | Qt.AlignLeft, self.text())
                else:
                    p.drawText(base, Qt.AlignCenter, self.text())
            p.end()

    # -- the range block -------------------------------------------------------

    class RangeBlock(QtWidgets.QWidget):
        """The playback range inside the animation range: drag the block to slide
        it, its orange edges to resize it."""

        def __init__(self, strip):
            super(RangeBlock, self).__init__(strip)
            self.strip = strip
            self.setFixedHeight(int(24 * strip.ui))
            self.setMinimumWidth(int(120 * strip.ui))
            self.setMouseTracking(True)
            self.setCursor(Qt.OpenHandCursor)
            self.drag = None
            self.hover = {"l": 0.0, "r": 0.0}
            self.goal = {"l": 0.0, "r": 0.0}
            self._was_busy = False
            self.index = strip.register(self)

        def edges(self):
            s, ui = self.strip.state, self.strip.ui
            w = float(self.width())
            span = max(1.0, s["a1"] - s["a0"])
            x0 = (s["p0"] - s["a0"]) / span * w
            x1 = (s["p1"] - s["a0"]) / span * w
            if x1 - x0 < 30 * ui:
                x1 = x0 + 30 * ui
            return x0, x1

        def part(self, x):
            x0, x1 = self.edges()
            reach = 7 * self.strip.ui
            if abs(x - x0 - 3 * self.strip.ui) <= reach:
                return "l"
            if abs(x - x1 + 3 * self.strip.ui) <= reach:
                return "r"
            return "m" if x0 < x < x1 else None

        def busy(self, now):
            return any(abs(self.hover[k] - self.goal[k]) > 0.005 for k in self.hover)

        def step(self, dt):
            for k in self.hover:
                self.hover[k] = (look.approach(self.hover[k], self.goal[k], dt, HOVER_MS)
                                 if self.strip.motion else self.goal[k])

        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            s, tk, ui = self.strip.state, self.strip.tokens, self.strip.ui
            scale, opacity = self.strip.opening_of(self.index)
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setOpacity(opacity)
            r = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            c = r.center()
            p.translate(c)
            p.scale(1.0, scale)
            p.translate(-c)
            p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
            p.setBrush(colour(tk["track"]))
            p.drawRoundedRect(r, 6 * ui, 6 * ui)
            x0, x1 = self.edges()
            thumb = QtCore.QRectF(x0 + 1, 2 * ui, x1 - x0 - 2, r.height() - 4 * ui)
            p.setPen(Qt.NoPen)
            p.setBrush(colour(tk["thumb"]))
            p.drawRoundedRect(thumb, 4 * ui, 4 * ui)
            for key, x in (("l", thumb.left() + 2 * ui), ("r", thumb.right() - 6 * ui)):
                h = self.hover[key]
                cx_, cy_ = x + 2 * ui, thumb.center().y()
                ew, eh = 4 * ui * (1 + 0.6 * h), (thumb.height() - 2 * ui) * (1 + 0.25 * h)
                edge = QtCore.QRectF(cx_ - ew / 2, cy_ - eh / 2, ew, eh)
                glow(p, edge, 2 * ui, tk["accent"], h * 0.7, ui)
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["accent"]))
                p.drawRoundedRect(edge, 2 * ui, 2 * ui)
            font = QtGui.QFont("Consolas")
            font.setPixelSize(max(8, int(11 * ui)))
            p.setFont(font)
            p.setPen(colour(tk["text"]))
            inner = thumb.adjusted(10 * ui, 0, -10 * ui, 0)
            if inner.width() > 40 * ui:
                p.drawText(inner, Qt.AlignVCenter | Qt.AlignLeft, look.frame_text(s["p0"]))
                p.drawText(inner, Qt.AlignVCenter | Qt.AlignRight, look.frame_text(s["p1"]))
            p.end()

        def _x(self, event):
            return event.position().x() if hasattr(event, "position") else event.x()

        def mouseMoveEvent(self, event):
            x = self._x(event)
            if self.drag is None:
                part = self.part(x)
                for k in self.goal:
                    self.goal[k] = 1.0 if part == k else 0.0
                self.setCursor(Qt.SizeHorCursor if part in ("l", "r") else Qt.OpenHandCursor)
                self.strip.kick()
                return
            kind, x_start, p0, p1 = self.drag
            s = self.strip.state
            span = max(1.0, s["a1"] - s["a0"])
            d = int(round((x - x_start) / max(1.0, self.width()) * span))
            if kind == "m":
                length = p1 - p0
                n0 = max(s["a0"], min(s["a1"] - length, p0 + d))
                n1 = n0 + length
            elif kind == "l":
                n0, n1 = max(s["a0"], min(p1 - 1, p0 + d)), p1
            else:
                n0, n1 = p0, min(s["a1"], max(p0 + 1, p1 + d))
            if (n0, n1) != (s["p0"], s["p1"]):
                s["p0"], s["p1"] = n0, n1
                s["now"] = max(n0, min(n1, s["now"]))
                self.strip.call("set_ranges", s["a0"], s["a1"], n0, n1)
                self.strip.ranges_changed()

        def mousePressEvent(self, event):
            if event.button() != Qt.LeftButton:
                return
            part = self.part(self._x(event)) or "m"
            s = self.strip.state
            self.drag = (part, self._x(event), s["p0"], s["p1"])
            if part == "m":
                self.setCursor(Qt.ClosedHandCursor)

        def mouseReleaseEvent(self, event):
            self.drag = None
            self.setCursor(Qt.OpenHandCursor)
            self.strip.refresh()

        def leaveEvent(self, event):
            for k in self.goal:
                self.goal[k] = 0.0
            self.strip.kick()

    # -- the timeline ------------------------------------------------------------

    class Timeline(QtWidgets.QWidget):

        def __init__(self, strip):
            super(Timeline, self).__init__(strip)
            self.strip = strip
            self.setObjectName("skeldarTimeBarTimeline")
            self.setMinimumWidth(int(160 * strip.ui))
            self.setFixedHeight(int(TIMELINE_H * strip.ui))
            self.setCursor(Qt.SizeHorCursor)
            self.setMouseTracking(True)
            self.drag = None            # (kind, start frame, the track at the press[, the highlight])
            self.view = None            # (v0, v1) after a zoom; None follows the playback range
            self.preview = None         # the highlight's target while keys are dragged
            self.aim_key = None         # the key under the mouse
            self.aim_head = False
            self.key_lift = {}          # key -> 0..1, eased
            self.head_lift = 0.0
            self.reached = {}           # key -> clock() when the playhead reached it
            self.trail = {}             # cell -> clock() when the playhead left it (scrub, play)
            self.play_at = None         # Play pressed: a frame closes in round the bar
            self._static = None         # the still part, drawn once (`_paint`)
            self._static_for = None
            self.static_builds = 0
            self._was_busy = False
            self.index = strip.register(self)

        def track(self):
            s, pad = self.strip.state, PAD * self.strip.ui
            v0, v1 = self.view or (s["p0"], s["p1"])
            return look.Track(v0, v1, pad, self.width() - pad, cells=True)

        # motion -------------------------------------------------------------
        def busy(self, now):
            if abs(self.head_lift - (1.0 if self.aim_head else 0.0)) > 0.005:
                return True
            if any(abs(v - (1.0 if k == self.aim_key else 0.0)) > 0.005 for k, v in self.key_lift.items()):
                return True
            if self.aim_key is not None and self.key_lift.get(self.aim_key, 0.0) < 0.995:
                return True
            if self.trail:
                return True
            if self.play_at is not None and look.progress(now - self.play_at, "play") is not None:
                return True
            return any(now - t0 < KEY_FADE_MS for t0 in self.reached.values())

        def step(self, dt):
            on = self.strip.motion
            goal = 1.0 if self.aim_head else 0.0
            self.head_lift = look.approach(self.head_lift, goal, dt, HOVER_MS) if on else goal
            keys = set(self.key_lift) | ({self.aim_key} if self.aim_key is not None else set())
            for k in keys:
                g = 1.0 if k == self.aim_key else 0.0
                v = look.approach(self.key_lift.get(k, 0.0), g, dt, HOVER_MS) if on else g
                if v <= 0.0 and g == 0.0:
                    self.key_lift.pop(k, None)
                else:
                    self.key_lift[k] = v
            now = self.strip.clock()
            for k in [k for k, t0 in self.reached.items() if now - t0 >= KEY_FADE_MS]:
                del self.reached[k]
            self._prune_trail(now)

        def _prune_trail(self, now):
            for f in [f for f, t0 in self.trail.items() if look.progress(now - t0, "trail") is None]:
                del self.trail[f]

        def leave(self, frame):
            """The playhead left `frame`'s cell (a scrub, playback): it glows and fades."""
            if not self.strip.motion:
                return
            now = self.strip.clock()
            self._prune_trail(now)          # playback turns no timer: prune here too
            self.trail[math.floor(frame + 1e-9)] = now
            self.strip.kick()

        def played(self):
            """Play pressed: an accent frame closes in round the bar."""
            if self.strip.motion:
                self.play_at = self.strip.clock()
                self.strip.kick()

        def _draw_trail(self, p, t, h):
            now, accent = self.strip.clock(), self.strip.tokens["accent"]
            p.setPen(Qt.NoPen)
            for frame, t0 in self.trail.items():
                u = look.progress(now - t0, "trail")
                if u is None:
                    continue
                c0, c1 = t.cell(frame)
                p.setBrush(colour(accent, look.TRAIL_ALPHA * 255 * (1.0 - u)))
                p.drawRect(QtCore.QRectF(c0, 0, max(1.0, c1 - c0), h))

        def _draw_play_frame(self, p, w, h):
            st = self.strip
            u = look.progress(st.clock() - self.play_at, "play") if self.play_at is not None else None
            if u is None:
                return
            ui = st.ui
            inset = 1 + 7 * ui * look.ease_out_quint(u)
            p.setBrush(Qt.NoBrush)
            p.setPen(QtGui.QPen(colour(st.tokens["accent"], 255 * (1.0 - u)), 1 + 2.5 * ui * (1.0 - u)))
            p.drawRoundedRect(QtCore.QRectF(inset, inset, w - 2 * inset, h - 2 * inset), 6 * ui, 6 * ui)

        def key_effect(self, kind, frame, breakdown=False):
            """A key set ("set": a round glow) or deleted ("delete": sparks) at `frame`."""
            st = self.strip
            t = self.track()
            if not st.motion or not (t.v0 - 0.5 <= frame <= t.v1 + 1.5):
                return
            top, bottom = key_span(float(self.height()), st.ui)
            cx, cy = st.point_of(self, look.key_centre(t, frame), (top + bottom) / 2.0)
            st.fx.add(kind, cx=cx, cy=cy, hex=BREAKDOWN if breakdown else st.tokens["accent"])

        def reach(self, before, after):
            """The playhead went from `before` to `after`: the keys it reached light up."""
            if not self.strip.motion:
                return
            hit = look.passed(self.strip.keys + self.strip.breakdowns, before, after)
            if hit:
                now = self.strip.clock()
                for k in hit:
                    self.reached[k] = now
                self.strip.kick()

        # painting -------------------------------------------------------------
        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001 - never a paint loop of tracebacks
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            """The still part - the track, the sound, the bookmarks, the highlight, the
            ruler and the keys - is one cached picture, drawn again only when it
            changes (`_static_key`); each frame paints that picture, the keys that are
            lit or lifted and the playhead over it (2026-10-16, «фпс проседает когда
            перетаскиваешь ползунок»: the whole timeline drawn element by element was
            3-5 ms a step and the key-fade tick 10 ms every 16 ms on a dense take)."""
            st = self.strip
            t = self.drag[2] if self.drag else self.track()
            tk, ui, s = st.tokens, st.ui, st.state
            w, h = float(self.width()), float(self.height())
            scale, opacity = st.opening_of(self.index)
            entrance = st.entrance is not None
            moving = (self.drag[3], self.preview) if (self.preview and self.drag and len(self.drag) > 3) else None
            key = self._static_key(t, w, h, not entrance, moving)
            if key != self._static_for or self._static is None:
                dpr = max(1.0, float(self.devicePixelRatioF()))
                picture = QtGui.QPixmap(max(1, int(round(w * dpr))), max(1, int(round(h * dpr))))
                picture.setDevicePixelRatio(dpr)
                picture.fill(Qt.transparent)
                sp = QtGui.QPainter(picture)
                sp.setRenderHint(QtGui.QPainter.Antialiasing)
                self._draw_static(sp, t, w, h, not entrance, moving)
                sp.end()
                self._static, self._static_for = picture, key
                self.static_builds += 1
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setOpacity(opacity)
            p.translate(0, h / 2)
            p.scale(1.0, scale)
            p.translate(0, -h / 2)
            p.drawPixmap(0, 0, self._static)
            p.setClipRect(QtCore.QRectF(1, 1, w - 2, h - 2))
            p.setPen(Qt.NoPen)
            if st.motion and self.trail:
                self._draw_trail(p, t, h)
            self._draw_moving_keys(p, t, entrance, moving, opacity)
            self._draw_playhead(p, t, w, h)
            if st.motion and self.play_at is not None:
                self._draw_play_frame(p, w, h)
            p.end()

        def _static_key(self, t, w, h, with_keys, moving):
            """What the cached picture shows; a new one is drawn when this changes."""
            st, s = self.strip, self.strip.state
            return (int(w), int(h), st.ui, round(t.v0, 4), round(t.v1, 4), s["p0"], s["p1"],
                    bool(s.get("sound_shown")), id(st.wave), len(st.wave), tuple(st.marks),
                    self.preview or s.get("highlight"), moving, with_keys,
                    hash(tuple(st.keys)), hash(tuple(st.breakdowns)), self.devicePixelRatioF())

        def _draw_static(self, p, t, w, h, with_keys, moving):
            st = self.strip
            tk, ui, s = st.tokens, st.ui, st.state
            p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
            p.setBrush(colour(tk["track"]))
            p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, w - 1, h - 1), 6 * ui, 6 * ui)
            p.setClipRect(QtCore.QRectF(1, 1, w - 2, h - 2))
            p.setPen(Qt.NoPen)
            # the sound: one path, not a rectangle a bin
            if s.get("sound_shown") and st.wave:
                path = QtGui.QPainterPath()
                bw = max(1.0, ui * 0.8)
                for frame, amp in st.wave:
                    if t.v0 <= frame <= t.v1:
                        hh = amp * (h - 12 * ui) / 2.0
                        path.addRect(QtCore.QRectF(t.x(frame), h / 2 - hh + 2 * ui, bw, hh * 2))
                p.setRenderHint(QtGui.QPainter.Antialiasing, False)
                p.fillPath(path, colour(WAVE))
                p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            # the bookmarks along the top
            small = QtGui.QFont(self.font())
            small.setPixelSize(max(7, int(9 * ui)))
            p.setFont(small)
            small_metrics = QtGui.QFontMetricsF(small)
            for start, stop, rgb, name in st.marks:
                x0, x1 = t.x(start), t.x(stop)
                if x1 < 0 or x0 > w:
                    continue
                c = QtGui.QColor.fromRgbF(*[max(0.0, min(1.0, float(v))) for v in rgb])
                band = QtCore.QRectF(x0 + 1, (LABEL_H + 1) * ui, max(2.0, x1 - x0 - 2), BAND_H * ui)
                c.setAlpha(70)
                p.setPen(Qt.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(band, 3 * ui, 3 * ui)
                c.setAlpha(255)
                p.setBrush(c)
                p.drawRoundedRect(QtCore.QRectF(band.left(), band.top(), 3 * ui, band.height()), 1.5 * ui, 1.5 * ui)
                if band.width() > small_metrics.horizontalAdvance(name) + 10 * ui:
                    p.setPen(blend(c.name(), "#ffffff", 0.35))
                    p.drawText(band.adjusted(6 * ui, 0, -2 * ui, 0), Qt.AlignVCenter | Qt.AlignLeft, name)
            p.setPen(Qt.NoPen)
            # outside the playback range (a zoom shows it): dimmed
            p.setBrush(colour("#000000", 85))
            if t.x(s["p0"]) > 0:
                p.drawRect(QtCore.QRectF(0, 0, t.x(s["p0"]), h))
            if t.end(s["p1"]) < w:
                p.drawRect(QtCore.QRectF(t.end(s["p1"]), 0, w, h))
            # the highlight
            sel = self.preview or s.get("highlight")
            if sel:
                hx0, hx1 = t.x(sel[0]), t.end(sel[1])
                p.setBrush(colour(HIGHLIGHT, 0x4a))
                p.drawRoundedRect(QtCore.QRectF(hx0, 1, hx1 - hx0, h - 2), 3 * ui, 3 * ui)
                p.setBrush(colour(HIGHLIGHT))
                p.drawRect(QtCore.QRectF(hx0, 1, 2 * ui, h - 2))
                p.drawRect(QtCore.QRectF(hx1 - 2 * ui, 1, 2 * ui, h - 2))
                if sel[1] > sel[0] and hx1 - hx0 > 16 * ui:
                    p.setBrush(colour("#ffffff", 176))
                    for gx in (hx0 + 5 * ui, hx1 - 6.5 * ui):
                        for gy in (-4, 0, 4):
                            p.drawRect(QtCore.QRectF(gx, h / 2 + (gy - 1) * ui, 1.5 * ui, 2 * ui))
            # the ruler
            font = QtGui.QFont("Consolas")
            font.setPixelSize(max(8, int(10 * ui)))
            p.setFont(font)
            metrics = QtGui.QFontMetricsF(font)
            #  as Maya's slider (2026-10-17): the ticks stand at the bottom, a frame's
            #  number at the top under the bookmarks band; the playhead's own number
            #  is at the bottom
            ry = 1 * ui                                   # the numbers at the very top
            tick_y = h - 3 * ui
            major, minor = colour(tk["muted"]), colour(tk["line"])
            label_pen = colour(tk["faint"])
            tall_of = {"label": 10.4 * ui, "mid": 6.5 * ui, "tick": 3.9 * ui}      # 30 % taller (2026-10-17)
            tick_w = max(1.0, ui * 0.75)
            for frame, kind in look.ticks(t, ui):
                x = round(t.x(frame))
                tall = tall_of[kind]
                p.setPen(Qt.NoPen)
                p.setBrush(major if kind == "label" else minor)
                p.drawRect(QtCore.QRectF(x, tick_y - tall, tick_w, tall))
                if kind == "label":
                    text = look.frame_text(frame)
                    if x + 3 * ui + metrics.horizontalAdvance(text) <= w - 2 * ui:
                        p.setPen(label_pen)
                        p.drawText(QtCore.QPointF(x + 3 * ui, ry + metrics.ascent()), text)
            # the keys at rest
            if with_keys:
                p.setPen(Qt.NoPen)
                for frames, hex_ in ((st.keys, tk["accent"]), (st.breakdowns, BREAKDOWN)):
                    path = QtGui.QPainterPath()
                    for frame in frames:
                        shown = look.mapped(frame, moving[0], moving[1]) if moving else frame
                        if t.v0 - 1 <= shown <= t.v1 + 2:
                            add_key(path, t.x(shown), h, ui, look.on_frame(shown), cell=t.scale)
                    p.fillPath(path, colour(hex_))

        def _draw_moving_keys(self, p, t, entrance, moving, opacity):
            """Over the picture: the keys that are lit or lifted, bigger and glowing -
            or, while the bar bursts out or folds, every key at its own size."""
            st = self.strip
            tk, ui = st.tokens, st.ui
            h = float(self.height())
            now = st.clock()
            if entrance:
                frames = [(f, tk["accent"]) for f in st.keys] + [(f, BREAKDOWN) for f in st.breakdowns]
            else:
                live = set(self.reached) | set(k for k, v in self.key_lift.items() if v > 0.005)
                if not live:
                    return
                keys, bds = set(st.keys), set(st.breakdowns)
                frames = [(f, tk["accent"] if f in keys else BREAKDOWN) for f in live if f in keys or f in bds]
            plain = {}
            for frame, hex_ in frames:
                shown = look.mapped(frame, moving[0], moving[1]) if moving else frame
                if not (t.v0 - 1 <= shown <= t.v1 + 1):
                    continue
                lit = look.flash(now - self.reached[frame], KEY_FADE_MS) if frame in self.reached else 0.0
                lift = max(self.key_lift.get(frame, 0.0), lit)
                z = 1.0 + KEY_LIFT * lift
                burst = 1.0
                if entrance:
                    g = self.mapToGlobal(QtCore.QPoint(int(look.key_centre(t, shown)), int(KEY_Y * ui)))
                    ks, burst = st.entrance_of(g.x(), g.y())
                    z *= ks
                x = t.x(shown)
                whole = look.on_frame(shown)
                top, bottom = key_span(h, ui)
                kw = KEY_W * ui * min(z, 1.6)
                grow = 0.0
                if whole:
                    #  the cell, grown a little when lit and squeezed toward its middle
                    #  while it pops in
                    l, tp, cw, ch = look.key_cell(x, t.scale, top, bottom, ui)
                    grow = 1.5 * ui * lift
                    if z < 1.0:
                        cx, cy = l + cw / 2.0, tp + ch / 2.0
                        cw, ch = cw * max(z, 0.05), ch * max(z, 0.05)
                        l, tp = cx - cw / 2.0, cy - ch / 2.0
                    rect = QtCore.QRectF(l - grow, tp - grow, cw + 2 * grow, ch + 2 * grow)
                else:
                    rect = QtCore.QRectF(x - kw / 2, top, kw, bottom - top)
                if lift > 0.01:
                    picture = halo(hex_, ui)
                    grow = 4.5 * ui * z / (1.0 + KEY_LIFT)
                    p.setOpacity(opacity * burst * lift)
                    p.drawPixmap(rect.adjusted(-grow, -grow, grow, grow), picture,
                                 QtCore.QRectF(picture.rect()))
                p.setOpacity(opacity * burst)
                if lit > 0.01:
                    p.setBrush(blend(hex_, RIM, lit * 0.7))
                else:
                    brush = plain.get(hex_)
                    if brush is None:
                        brush = plain[hex_] = colour(hex_)
                    p.setBrush(brush)
                mark = QtGui.QPainterPath()
                if whole:
                    mark.addRoundedRect(rect, 1.5 * ui, 1.5 * ui)
                else:
                    add_key(mark, x, h, ui, whole, width=kw)
                p.drawPath(mark)
            p.setOpacity(opacity)

        def _draw_playhead(self, p, t, w, h):
            st = self.strip
            tk, ui, s = st.tokens, st.ui, st.state
            c0, c1 = t.cell(s["now"])
            x = (c0 + c1) / 2.0
            head = colour(HIGHLIGHT if self.drag and self.drag[0] == "mid" else tk["accent"])
            p.setPen(Qt.NoPen)
            #  the frame's cell filled, as Maya's slider fills it (2026-10-17): the
            #  keys inside it show through; at least a line when cells are thin
            cw = max(c1 - c0, 2 * ui)
            cx = x - cw / 2.0
            p.setBrush(colour(head.name(), HEAD_FILL))
            p.drawRect(QtCore.QRectF(cx, 0, cw, h))
            p.setBrush(head)
            p.drawRect(QtCore.QRectF(cx, 0, cw, 1.5 * ui))
            p.drawRect(QtCore.QRectF(cx, h - 1.5 * ui, cw, 1.5 * ui))
            fz = 1.0 + 0.12 * self.head_lift
            bold = QtGui.QFont("Consolas")
            bold.setBold(True)
            bold.setPixelSize(max(8, int(10 * ui * fz)))
            p.setFont(bold)
            text = look.frame_text(s["now"])
            tw = QtGui.QFontMetricsF(bold).horizontalAdvance(text) + 10 * ui * fz
            th = 14 * ui * fz
            fx = min(max(x - tw / 2, 1), w - tw - 1)
            flag = QtCore.QRectF(fx, h - th, tw, th)          # at the bottom, as Maya's
            glow(p, flag, 3 * ui, head.name(), self.head_lift * 0.8, ui)
            p.setPen(Qt.NoPen)
            p.setBrush(head)
            p.drawRoundedRect(flag, 3 * ui, 3 * ui)
            p.setPen(colour(tk["on_accent"]))
            p.drawText(flag, Qt.AlignCenter, text)

        # input ------------------------------------------------------------
        def _x(self, event):
            return event.position().x() if hasattr(event, "position") else event.x()

        def _grip(self, part, x, t):
            """The frame a highlight drag counts from: an edge counts frame lines
            (it sits on one, the edge of a cell), the body counts cells."""
            if part in ("h0", "h1"):
                return int(round(t.frame(x)))
            return self._frame(x, t)

        def _frame(self, x, t=None):
            s = self.strip.state
            return (t or self.track()).whole(x, lo=s["a0"], hi=s["a1"])

        def mousePressEvent(self, event):
            st, s = self.strip, self.strip.state
            x, t = self._x(event), self.track()
            if event.button() == Qt.RightButton:
                st.key_menu(event, self._frame(x, t))
                return
            if event.button() == Qt.MiddleButton:
                self.drag = ("mid", None, t)
                self._scrub(x, update=False)
                return
            if event.button() != Qt.LeftButton:
                return
            if event.modifiers() & Qt.ShiftModifier:
                start = self._frame(x, t)
                self.drag = ("hl", start, t)
                s["highlight"] = (start, start)
                self.update()
                return
            part = look.highlight_hit(t, x, s.get("highlight"), st.ui)
            if part:
                self.drag = (part, self._grip(part, x, t), t, tuple(s["highlight"]))
                self.preview = tuple(s["highlight"])
                return
            self.drag = ("now", None, t)
            st.call("begin_scrub")
            if s.get("highlight"):
                s["highlight"] = None
                st.call("set_highlight", None)
            self._scrub(x)

        def mouseMoveEvent(self, event):
            x, s = self._x(event), self.strip.state
            if not self.drag:
                self._aim(x)
                return
            kind, start, t = self.drag[0], self.drag[1], self.drag[2]
            if kind in ("now", "mid"):
                self._scrub(x, update=(kind == "now"))
            elif kind == "hl":
                s["highlight"] = look.highlight(start, self._frame(x, t))
                self.update()
            else:
                target = look.key_drag(kind, self.drag[3], start, self._grip(kind, x, t))
                if target != self.preview:
                    self.preview = target
                    self.update()

        def mouseReleaseEvent(self, event):
            if not self.drag:
                return
            kind = self.drag[0]
            st, s = self.strip, self.strip.state
            if kind == "now":
                st.call("end_scrub")
            elif kind == "mid":
                st.refresh()
            elif kind == "hl":
                st.call("set_highlight", s["highlight"])
            elif kind in ("hmove", "h0", "h1"):
                selection, target = self.drag[3], self.preview
                if target and target != selection:
                    st._quiet_keys = True               # a move is no set and delete
                    st.call("move_keys", selection, target)
                    s["highlight"] = target
                    st.call("set_highlight", target)
                    self.drag, self.preview = None, None
                    st.refresh(keys=True)
            self.drag = None
            self.preview = None
            self.update()

        def mouseDoubleClickEvent(self, event):
            """Frame the playback range again after a zoom."""
            if event.button() == Qt.LeftButton and self.view is not None:
                self.strip.frame_playback()

        def wheelEvent(self, event):
            s, t = self.strip.state, self.track()
            delta = event.angleDelta().y()
            if not delta:
                return
            at = t.frame(event.position().x() if hasattr(event, "position") else event.x())
            #  zoomed over the cells' edges, the last cell's end included
            v0, v1 = look.zoomed(t.v0, t.v1 + 1, at, 1.15 if delta < 0 else 1 / 1.15, s["a0"], s["a1"] + 1)
            self.view = (v0, v1 - 1)
            self.strip.view_changed()
            event.accept()

        def leaveEvent(self, event):
            self.aim_key, self.aim_head = None, False
            self.strip.kick()

        def _aim(self, x):
            t, ui = self.track(), self.strip.ui
            best, near = None, 7 * ui
            near = max(near, t.scale / 2.0)
            for k in self.strip.keys + self.strip.breakdowns:
                d = abs(look.key_centre(t, k) - x)
                if d < near:
                    best, near = k, d
            head = abs(t.x(self.strip.state["now"]) - x) < 8 * ui
            part = look.highlight_hit(t, x, self.strip.state.get("highlight"), ui)
            self.setCursor(Qt.OpenHandCursor if part == "hmove" else Qt.SizeHorCursor)
            if best != self.aim_key or head != self.aim_head:
                self.aim_key, self.aim_head = best, head
                self.strip.kick()

        def _scrub(self, x, update=True):
            """The playhead drawn on the new frame at once, then Maya sent there:
            `currentTime` evaluates the scene before it returns, and a paint left
            to the event loop waited for it - the playhead jumped frames."""
            t0 = time.perf_counter()
            s, t = self.strip.state, self.drag[2] if self.drag else self.track()
            frame = self._frame(x, t)
            if frame == s["now"]:
                return
            before = s["now"]
            s["now"] = frame
            self.reach(before, frame)
            self.leave(before)
            self.strip.show_now()
            self.repaint()
            t1 = time.perf_counter()
            self.strip.call("set_time" if update else "scrub_only", frame)
            meter = _state().get("meter")
            if meter is not None:          # the scrub meter: our work, then Maya's frame change
                meter["ours"].append((t1 - t0) * 1000.0)
                meter["mayas"].append((time.perf_counter() - t1) * 1000.0)

    # -- the key effects' overlay -------------------------------------------------

    class FxLayer(QtWidgets.QWidget):
        """Over the whole strip, deaf to the mouse: a key set flashes a round glow,
        a key deleted throws sparks (2026-10-17). Each is drawn from its age alone -
        a spark's flight is a formula - and the layer paints only while one lives."""

        def __init__(self, strip):
            super(FxLayer, self).__init__(strip)
            self.strip = strip
            self.setObjectName("skeldarTimeBarFx")
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setAttribute(Qt.WA_NoSystemBackground, True)
            self.items = []
            self._was_busy = False
            self._seed = 1

        def add(self, kind, **data):
            if not self.strip.motion:
                return
            self._seed += 1
            data.update(kind=kind, t0=self.strip.clock(), seed=self._seed)
            self.items.append(data)
            self.raise_()
            self.strip.kick()

        def busy(self, now):
            self.items = [i for i in self.items if look.progress(now - i["t0"], i["kind"]) is not None]
            return bool(self.items)

        def paintEvent(self, _event):
            if not self.items:
                return
            try:
                p = QtGui.QPainter(self)
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                now, ui = self.strip.clock(), self.strip.ui
                for i in self.items:
                    age = now - i["t0"]
                    u = look.progress(age, i["kind"])
                    if u is None:
                        continue
                    if i["kind"] == "set":
                        # a round flash, out and gone
                        soft_dot(p, i["cx"], i["cy"], 30 * ui * (0.6 + 0.4 * look.back_out(min(1.0, u / 0.4))),
                                 i["hex"], 235 * (1.0 - u) ** 2)
                        soft_dot(p, i["cx"], i["cy"], 9 * ui, RIM, 200 * (1.0 - u) ** 3)
                    else:
                        for dx, dy, life in look.sparks(i["seed"], 24, age, look.EFFECT_MS["delete"],
                                                        170 * ui, 620 * ui):
                            size = 1.5 * ui * (0.5 + 0.5 * life)
                            p.setPen(Qt.NoPen)
                            p.setBrush(colour(i["hex"], 255 * life))
                            p.drawEllipse(QtCore.QPointF(i["cx"] + dx, i["cy"] + dy), size, size)
                p.end()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

    # -- the strip -------------------------------------------------------------------

    class Strip(QtWidgets.QWidget):

        def __init__(self, link, ui=1.0, tokens=None, parent=None, motion=None):
            super(Strip, self).__init__(parent)
            self.setObjectName(ROOT_NAME)
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.link, self.ui = link, float(ui)
            self.tokens = tokens or _tokens()
            self.motion = animations_on() if motion is None else bool(motion)
            self.state = {"now": 0.0, "a0": 0.0, "a1": 120.0, "p0": 0.0, "p1": 120.0,
                          "unit": "ntsc", "auto": False, "playing": False, "highlight": None,
                          "loop": "continuous", "speed": 1.0, "cache": False, "sound": "",
                          "sound_shown": False, "character": ""}
            self.keys, self.breakdowns, self.marks, self.wave = [], [], [], []
            self._wave_key = None
            self.keys_dirty = True
            self.moving = []
            self._t0 = time.time()
            self.opened = 0.0
            self.entrance = None        # the burst from / fold to the cursor (the bottom edge)
            self.fades = []             # Qt's own fields and the dividers: faded in the burst
            self._last_step = None
            self.setStyleSheet(stylesheet(self.tokens, self.ui))
            ui = self.ui
            column = QtWidgets.QVBoxLayout(self)
            column.setContentsMargins(int(6 * ui), int(1 * ui), int(6 * ui), int(3 * ui))
            column.setSpacing(0)
            top, bottom = QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout()
            for row in (top, bottom):
                row.setSpacing(int(2 * ui))
                column.addLayout(row)
            # range row
            self.anim_start = self._field("Animation start", lambda v: self._typed_range("a0", v))
            self.play_start = self._field("Playback start", lambda v: self._typed_range("p0", v))
            self.range = RangeBlock(self)
            self.play_end = self._field("Playback end", lambda v: self._typed_range("p1", v))
            self.anim_end = self._field("Animation end", lambda v: self._typed_range("a1", v))
            top.addWidget(self.anim_start)
            top.addWidget(self.play_start)
            top.addWidget(self.range, 1)
            top.addWidget(self.play_end)
            top.addWidget(self.anim_end)
            top.addWidget(self._sep())
            self.bm_prev = Pill(self, "bm_prev", tip="Previous bookmark")
            self.bm_add = Pill(self, "bm_add", tip="Add a bookmark over the highlight", accent_glyph=True)
            self.bm_next = Pill(self, "bm_next", tip="Next bookmark")
            self.bm_prev.clicked.connect(lambda *_a: self._bookmark(False))
            self.bm_next.clicked.connect(lambda *_a: self._bookmark(True))
            self.bm_add.clicked.connect(lambda *_a: self._add_bookmark())
            for b in (self.bm_prev, self.bm_add, self.bm_next):
                top.addWidget(b)
            top.addWidget(self._sep())
            self.character = Pill(self, text="No Character Set", tip="Character set", style="chip")
            self.layer = Pill(self, text="BaseAnimation", tip="The animation layer keys go to", style="chip")
            self.fps = Pill(self, text="30 fps", tip="Frame rate", style="chip")
            self.character.clicked.connect(lambda *_a: self._character_menu())
            self.layer.clicked.connect(lambda *_a: self._layer_menu())
            self.fps.clicked.connect(lambda *_a: self._fps_menu())
            for b in (self.character, self.layer, self.fps):
                top.addWidget(b)
            top.addWidget(self._sep())
            self.loop = Pill(self, "loop", tip="Looping", toggle=True)
            self.cache = Pill(self, "cache", tip="Cached playback", toggle=True)
            self.speed = Pill(self, text="Real-time", tip="Playback speed", style="chip")
            self.sound = Pill(self, "sound", tip="Sound under the frames", toggle=True)
            self.auto = Pill(self, "auto", tip="Auto key", style="rec", toggle=True)
            self.prefs = Pill(self, "prefs", tip="Time slider preferences")
            self.loop.clicked.connect(lambda *_a: self._do("cycle_loop"))
            self.cache.clicked.connect(lambda *_a: self._do("toggle_cache"))
            self.speed.clicked.connect(lambda *_a: self._speed_menu())
            self.sound.clicked.connect(lambda *_a: self._sound_menu())
            self.auto.clicked.connect(lambda *_a: self._do("toggle_auto"))
            self.prefs.clicked.connect(lambda *_a: self.call("preferences"))
            #  the 📌 of the bottom edge (2026-10-16): only shown there
            self.edge = None
            self.pin = Pill(self, "pin", tip="Keep the time bar out", toggle=True)
            self.pin.clicked.connect(lambda checked=False: self.edge and self.edge.set_pinned(self.pin.isChecked()))
            self.pin.setVisible(False)
            for b in (self.loop, self.cache, self.speed, self.sound, self.auto, self.prefs, self.pin):
                top.addWidget(b)
            # time row
            self.timeline = Timeline(self)
            bottom.addWidget(self.timeline, 1)
            bottom.addSpacing(int(4 * ui))
            self.field = QtWidgets.QLineEdit(self)
            self.field.setObjectName("skeldarTimeBarFrame")
            self.field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.field.setFixedSize(int(58 * ui), int(24 * ui))
            self.field.setToolTip("Current frame")
            self.field.setFocusPolicy(Qt.ClickFocus)
            self.field.returnPressed.connect(self._typed)
            self._fading(self.field)
            bottom.addWidget(self.field)
            bottom.addWidget(self._sep())
            self.transport = {}
            for name, tip, action, accent in (
                    ("start", "Go to start", lambda: self._go("start"), False),
                    ("pfrm", "Step back a frame", lambda: self._go("pfrm"), False),
                    ("pkey", "Step back a key", lambda: self._step(False), True),
                    ("back", "Play backwards", lambda: self.call("toggle_play", False), False),
                    ("play", "Play forwards", lambda: self.call("toggle_play", True), False),
                    ("nkey", "Step forward a key", lambda: self._step(True), True),
                    ("nfrm", "Step forward a frame", lambda: self._go("nfrm"), False),
                    ("end", "Go to end", lambda: self._go("end"), False)):
                b = Pill(self, name, tip=tip, style="play" if name == "play" else "plain", accent_glyph=accent)
                b.clicked.connect(lambda *_a, f=action: (f(), self.refresh()))
                bottom.addWidget(b)
                self.transport[name] = b
            self.play, self.prev, self.next = self.transport["play"], self.transport["pkey"], self.transport["nkey"]
            # the key effects (2026-10-17)
            self.fx = FxLayer(self)
            self.fx.setGeometry(self.rect())
            self._keys_read = False     # the first read of the keys is no edit
            self._quiet_keys = False    # a key move is no set and delete
            # timers
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(TIMER_MS)
            self.timer.timeout.connect(self.tick)
            self.anim = QtCore.QTimer(self)
            self.anim.setInterval(FRAME_MS)
            self.anim.timeout.connect(self._animate)
            self.refresh(keys=True, force=True)     # read once even if Maya is playing
            self.timer.start()
            self.opened = self.clock()
            self.kick()

        # building -----------------------------------------------------------
        def set_edge(self, controller):
            """Standing in the bottom edge's host: the 📌 shows."""
            self.edge = controller
            self.pin.setVisible(controller is not None)

        def register(self, widget):
            self.moving.append(widget)
            return len(self.moving) - 1

        def _sep(self):
            sep = QtWidgets.QFrame(self)
            sep.setObjectName("skeldarTimeBarSep")
            sep.setFixedSize(max(1, int(self.ui)), int(20 * self.ui))
            return self._fading(sep)

        def _fading(self, widget):
            """A widget we do not paint (a field, a divider) fades in the burst:
            an opacity effect, held here (PySide deletes an effect whose wrapper is
            collected, CLAUDE.md trap 201) and switched off at rest (trap 204)."""
            effect = QtWidgets.QGraphicsOpacityEffect(widget)
            effect.setEnabled(False)
            widget.setGraphicsEffect(effect)
            self.fades.append((widget, effect))
            return widget

        def _fade(self):
            for widget, effect in self.fades:
                try:
                    if self.entrance is None:
                        if effect.isEnabled():
                            effect.setOpacity(1.0)
                            effect.setEnabled(False)
                        continue
                    c = widget.mapToGlobal(widget.rect().center())
                    effect.setOpacity(self.entrance_of(c.x(), c.y())[1])
                    effect.setEnabled(True)
                except RuntimeError:
                    pass

        def _field(self, tip, on_value):
            field = QtWidgets.QLineEdit(self)
            field.setObjectName("skeldarTimeBarField")
            field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            field.setFixedSize(int(52 * self.ui), int(24 * self.ui))
            field.setToolTip(tip)
            field.setFocusPolicy(Qt.ClickFocus)
            self._fading(field)

            def done():
                try:
                    on_value(float(field.text()))
                except ValueError:
                    pass
                field.clearFocus()
                self.refresh()
            field.returnPressed.connect(done)
            return field

        # motion -------------------------------------------------------------
        def clock(self):
            return (time.time() - self._t0) * 1000.0

        def opening_of(self, index):
            if not self.motion:
                return 1.0, 1.0
            e = self.entrance
            if e is not None:
                age = self.clock() - e["t0"]
                delay = e["delays"].get(index, 0.0)
                return look.popping(age, delay) if e["open"] else look.folding(age, delay)
            return look.opening(self.clock() - self.opened, index)

        def entrance_of(self, gx, gy):
            """(scale, opacity) of a thing at the global point (gx, gy) in the
            burst or the fold standing (a key on the timeline)."""
            e = self.entrance
            if e is None or not self.motion:
                return 1.0, 1.0
            age = self.clock() - e["t0"]
            if e["open"]:
                return look.popping(age, look.burst_delay(gx - e["gx"], gy - e["gy"], self.ui))
            return look.folding(age, look.fold_delay(gx - e["gx"], self.ui))

        def burst_at(self, gx, gy, opening=True, instant=False):
            """The controls - and the keys - pop in from the global point (gx, gy),
            the nearest first, or fold toward it, the farthest first (2026-10-16,
            mockup A, 1.5x slower). Returns how long it takes, ms."""
            delays, far = {}, 0.0
            points = [(w.index, w.mapToGlobal(w.rect().center())) for w in self.moving]
            t = self.timeline.track()
            points += [(None, self.timeline.mapToGlobal(QtCore.QPoint(int(look.key_centre(t, k)), int(KEY_Y * self.ui))))
                       for k in self.keys + self.breakdowns]
            for index, c in points:
                if opening:
                    d = look.burst_delay(c.x() - gx, c.y() - gy, self.ui)
                else:
                    d = look.fold_delay(c.x() - gx, self.ui)
                far = max(far, d)
                if index is not None:
                    delays[index] = d
            if not self.motion or instant:
                self.entrance = None
                self._fade()
                self.update()
                return 0.0
            for widget, _effect in self.fades:
                c = widget.mapToGlobal(widget.rect().center())
                far = max(far, look.burst_delay(c.x() - gx, c.y() - gy, self.ui) if opening
                          else look.fold_delay(c.x() - gx, self.ui))
            self.entrance = {"open": bool(opening), "t0": self.clock(), "gx": gx, "gy": gy,
                             "delays": delays,
                             "ends": far + (look.POP_OPEN_MS if opening else look.FOLD_MS)}
            self._fade()
            self.kick()
            return self.entrance["ends"]

        def replay_opening(self):
            self.opened = self.clock()
            self.kick()

        def resizeEvent(self, event):
            super(Strip, self).resizeEvent(event)
            fx = getattr(self, "fx", None)
            if fx is not None:
                fx.setGeometry(self.rect())
                fx.raise_()

        def point_of(self, widget, x, y):
            """(x, y) in `widget` as a point of the strip (the overlay's)."""
            g = widget.mapTo(self, QtCore.QPoint(int(round(x)), int(round(y))))
            return float(g.x()), float(g.y())

        def kick(self):
            if not self.anim.isActive():
                self._last_step = self.clock()
                self.anim.start()

        def _animate(self):
            try:
                now = self.clock()
                dt = now - (self._last_step or now)
                self._last_step = now
                opening = self.motion and now - self.opened < 260 + 18 * len(self.moving)
                e = self.entrance
                if e is not None:
                    if now - e["t0"] < e["ends"] + 20:
                        opening = True
                    elif e["open"]:
                        self.entrance = None        # popped in: the controls as they are
                        opening = True              # one more paint at rest
                self._fade()
                busy = opening
                for widget in self.moving:
                    widget.step(dt)
                    moving = widget.busy(now)
                    if opening or moving or widget._was_busy:
                        widget.update()
                    widget._was_busy = moving
                    busy = busy or moving
                fx = self.fx
                moving = fx.busy(now)
                if moving or fx._was_busy:
                    fx.update()
                fx._was_busy = moving
                busy = busy or moving
                if not busy:
                    self.anim.stop()
            except Exception:                                # noqa: BLE001
                self.anim.stop()
                print(traceback.format_exc())

        # Maya ---------------------------------------------------------------
        def call(self, name, *args):
            """A write to Maya; a failure goes to the Script Editor, never out of a Qt slot."""
            try:
                return getattr(self.link, name)(*args)
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                return None

        def _do(self, name, *args):
            self.call(name, *args)
            self.refresh()

        def refresh(self, keys=False, force=False):
            light = self.call("light")
            if light:
                self.state.update(light)
            extra = self.call("extra")
            if extra:
                self.state.update(extra)
            if keys:
                self.keys_dirty = True
            if self.keys_dirty and (force or not self.state.get("playing")):
                found = self.call("keys")
                old_keys, old_bds = self.keys, self.breakdowns
                if found is not None:
                    self.keys, self.breakdowns = list(found[0]), list(found[1])
                    self.keys_dirty = False
                    if self._keys_read and not self._quiet_keys:
                        self._key_effects(old_keys, old_bds)
                    self._keys_read, self._quiet_keys = True, False
                self.marks = self.call("bookmarks") or []
            self._sound()
            self._paint_widgets()
            self.timeline.update()
            self.range.update()

        def _key_effects(self, old_keys, old_bds):
            """A key set flashes, a key deleted throws sparks."""
            if not self.motion:
                return
            for old, new, bd in ((old_keys, self.keys, False), (old_bds, self.breakdowns, True)):
                added, removed, _snapped = look.key_changes(old, new)
                for k in added:
                    self.timeline.key_effect("set", k, bd)
                for k in removed:
                    self.timeline.key_effect("delete", k, bd)

        def _sound(self):
            s, t = self.state, self.timeline.track()
            key = (s.get("sound"), round(t.v0, 2), round(t.v1, 2), s.get("sound_shown"))
            if key != self._wave_key:
                self._wave_key = key
                self.wave = (self.call("waveform", s["sound"], t.v0, t.v1) or []) if s.get("sound") else []

        def view_changed(self):
            self._sound()
            self.timeline.update()

        def frame_playback(self):
            self.timeline.view = None
            self.view_changed()

        def ranges_changed(self):
            self._paint_widgets()
            self._sound()
            self.timeline.update()
            self.range.update()

        def on_time(self):
            """timeChanged: the playhead only (playback calls it every frame)."""
            now = self.call("now")
            if now is not None and now != self.state["now"]:
                before = self.state["now"]
                self.state["now"] = now
                self.timeline.reach(before, now)
                if self.state.get("playing"):
                    self.timeline.leave(before)
                self.show_now()
                #  painted now, inside Maya's frame: Maya's playback does not let
                #  the event loop run between frames, so `update()` drew one frame
                #  in several (2026-10-16)
                self.timeline.repaint()
                self.field.repaint()

        def tick(self):
            try:
                if not self.timeline.drag and not self.range.drag:
                    self.refresh()
            except Exception:                                # noqa: BLE001 - four times a second
                if not getattr(self, "_tick_failed", False):
                    print(traceback.format_exc())
                self._tick_failed = True

        def show_now(self):
            if not self.field.hasFocus():
                self.field.setText(look.frame_text(self.state["now"]))

        def _paint_widgets(self):
            s = self.state
            self.show_now()
            for field, key in ((self.anim_start, "a0"), (self.play_start, "p0"),
                               (self.play_end, "p1"), (self.anim_end, "a1")):
                if not field.hasFocus():
                    field.setText(look.frame_text(s[key]))
            playing = bool(s["playing"])
            if playing and getattr(self, "_was_playing", None) is False:
                self.timeline.played()
            self._was_playing = playing
            self.play.glyph = "pause" if playing else "play"
            self.play.update()
            self.fps.set_label(look.fps_label(s["unit"]) + u" ▾")
            self.auto.setChecked(bool(s["auto"]))
            loop = s.get("loop") or "continuous"
            self.loop.glyph = {"continuous": "loop", "once": "once", "oscillate": "oscillate"}.get(loop, "loop")
            self.loop.setChecked(loop != "once")
            self.loop.setToolTip("Looping: %s - press for the next" % loop)
            self.cache.setChecked(bool(s.get("cache")))
            self.sound.setChecked(bool(s.get("sound")) and bool(s.get("sound_shown")))
            speed = s.get("speed", 1.0)
            label = next((t for t, v in look.SPEEDS if abs(v - speed) < 1e-6), "%gx" % speed)
            self.speed.set_label(label + u" ▾")
            self.character.set_label((s.get("character") or "No Character Set") + u" ▾")
            layer = self.call("layer_label") or ""
            self.layer.set_label((layer + u" ▾") if layer else "No layers")

        # presses ---------------------------------------------------------------
        def _typed(self):
            try:
                frame = float(self.field.text())
            except ValueError:
                self.show_now()
                return
            before = self.state["now"]
            self.call("set_time", frame)
            self.field.clearFocus()
            self.refresh()
            self.timeline.reach(before, self.state["now"])

        def _typed_range(self, which, value):
            s = self.state
            a0, a1, p0, p1 = look.dragged(which, value, s["a0"], s["a1"], s["p0"], s["p1"])
            self.call("set_ranges", a0, a1, p0, p1)

        def _go(self, where):
            s, n = self.state, int(round(self.state["now"]))
            frame = {"start": s["p0"], "end": s["p1"], "pfrm": max(s["p0"], n - 1),
                     "nfrm": min(s["p1"], n + 1)}[where]
            before = s["now"]
            self.call("set_time", frame)
            self.timeline.reach(before, frame)

        def _step(self, forward):
            before = self.state["now"]
            self.call("step_key", forward, self.keys + self.breakdowns)
            self.refresh()
            self.timeline.reach(before, self.state["now"])

        def _bookmark(self, forward):
            self.call("step_bookmark", forward)
            self.refresh()

        def _add_bookmark(self):
            self.call("add_bookmark", self.state.get("highlight"))
            self.refresh(keys=True)

        def menu_rows(self, rows, menu=None):
            """A QMenu of `rows`: (label, callable | None [, checked]), None for a
            separator, (label, [rows]) for a submenu. Returns (menu, {QAction: callable})."""
            menu = menu or QtWidgets.QMenu(self)
            picked = {}
            for item in rows:
                if item is None:
                    menu.addSeparator()
                    continue
                label, action = item[0], item[1]
                if isinstance(action, list):
                    _sub, inner = self.menu_rows(action, menu.addMenu(label))
                    picked.update(inner)
                    continue
                row = menu.addAction(label)
                if len(item) > 2:
                    row.setCheckable(True)
                    row.setChecked(bool(item[2]))
                if action is None:
                    row.setEnabled(False)
                else:
                    picked[row] = action
            return menu, picked

        def _menu(self, where, rows):
            menu, picked = self.menu_rows(rows)
            point = where if isinstance(where, QtCore.QPoint) else where.mapToGlobal(QtCore.QPoint(0, where.height()))
            chosen = menu.exec(point)
            menu.deleteLater()
            action = picked.get(chosen)
            if action is not None:
                try:
                    action()
                except Exception:                            # noqa: BLE001
                    print(traceback.format_exc())
            self.refresh(keys=True)

        def fps_rows(self):
            return [(text + " fps", (lambda u=unit: self.call("set_unit", u)), self.state["unit"] == unit)
                    for text, unit in look.FPS]

        def speed_rows(self):
            speed = self.state.get("speed", 1.0)
            return [(text, (lambda v=value: self.call("set_speed", v)), abs(speed - value) < 1e-6)
                    for text, value in look.SPEEDS]

        def layer_rows(self):
            found = self.call("layers") or []
            if not found:
                return [("No animation layers", None)]
            return [(label, (lambda n=name: self.call("pick_layer", n)), sel) for name, label, sel in found]

        def character_rows(self):
            current = self.state.get("character") or ""
            rows = [("No Character Set", (lambda: self.call("pick_character", "")), not current)]
            return rows + [(name, (lambda n=name: self.call("pick_character", n)), name == current)
                           for name in (self.call("character_sets") or [])]

        def sound_rows(self):
            current = self.state.get("sound") or ""
            rows = [("No sound", (lambda: self.call("set_sound", "")), not current)]
            rows += [(name, (lambda n=name: self.call("set_sound", n)), name == current)
                     for name in (self.call("sounds") or [])]
            return rows + [None, ("Show on the timeline", (lambda: self.call("toggle_sound")),
                                  bool(self.state.get("sound_shown")))]

        def key_rows(self, frame):
            sel = self.state.get("highlight")
            caption = ("Keys in %s-%s" % (look.frame_text(sel[0]), look.frame_text(sel[1])) if sel
                       else "Keys at frame %s" % look.frame_text(frame))
            c = self.call
            return [(caption, None),
                    ("Set key", lambda: c("set_key")),
                    ("Breakdown", lambda: c("breakdown", sel, frame)), None,
                    ("Cut", lambda: c("cut_keys", sel, frame)),
                    ("Copy", lambda: c("copy_keys", sel, frame)),
                    ("Paste", lambda: c("paste_keys", sel, frame)),
                    ("Delete", lambda: c("delete_keys", sel, frame)), None,
                    ("Tangents", [(label, (lambda k=kind: c("tangents", sel, frame, k)))
                                  for label, kind in look.TANGENTS]),
                    ("Snap to whole frames", lambda: c("snap_keys", sel, frame)), None,
                    ("Add bookmark", lambda: c("add_bookmark", sel)),
                    ("Playback range = highlight", (lambda: c("playback_from", sel)) if sel else None),
                    ("Frame the playback range", self.frame_playback), None,
                    ("Measure scrubbing (10 s)", lambda: c("measure")),
                    ("Back to Maya's time slider", lambda: c("back_to_maya"))]

        def _fps_menu(self):
            self._menu(self.fps, self.fps_rows())

        def _speed_menu(self):
            self._menu(self.speed, self.speed_rows())

        def _layer_menu(self):
            self._menu(self.layer, self.layer_rows())

        def _character_menu(self):
            self._menu(self.character, self.character_rows())

        def _sound_menu(self):
            self._menu(self.sound, self.sound_rows())

        def key_menu(self, event, frame):
            point = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self._menu(point, self.key_rows(frame))

    return Strip, Timeline, RangeBlock, Pill


def make(link=None, ui=1.0, tokens=None, parent=None, motion=None):
    strip_class = classes()[0]
    return strip_class(link or Link(), ui, tokens, parent, motion)


# -- in Maya ---------------------------------------------------------------------------

def current():
    """The live strip, or None (a dead wrapper dropped)."""
    widget = _state().get("bar")
    if widget is None:
        return None
    try:
        import maya_hubqt
        if maya_hubqt.qt().shiboken.isValid(widget):
            return widget
    except Exception:                                        # noqa: BLE001
        pass
    _state()["bar"] = None
    return None


def _job(method, *args):
    widget = current()
    if widget is not None:
        try:
            getattr(widget, method)(*args)
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())


def _time_changed(*_args):
    """Maya's time changed - every frame of playback too (2026-10-16): the
    `timeChanged` scriptJob did not run during playback, so the playhead moved
    only with the 250 ms timer, 7-10 frames at a time."""
    widget = current()
    if widget is not None:
        try:
            widget.on_time()
        except Exception:                                    # noqa: BLE001 - every frame: never raise
            pass
    edge = _state().get("edge")
    if edge is not None:
        try:
            edge.on_time()                    # Play while the bottom edge hides it: out
        except Exception:                                    # noqa: BLE001
            pass


def _keys_edited(*_args):
    widget = current()
    if widget is not None:
        widget.keys_dirty = True


def _drop_callbacks():
    state = _state()
    try:
        import maya.api.OpenMaya as om
        for cid in state.get("callbacks", []):
            try:
                om.MMessage.removeCallback(cid)
            except Exception:                                # noqa: BLE001
                pass
    except Exception:                                        # noqa: BLE001
        pass
    state["callbacks"] = []


def start_jobs():
    """The jobs and callbacks that keep the live strip current - one set, whichever
    host it stands in (the docked control or the bottom edge): the old ones killed
    first, none parented to a control that may be hidden."""
    import maya.cmds as cmds
    from functools import partial
    for job in _state().get("jobs", []):
        try:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        except Exception:                                    # noqa: BLE001
            pass
    jobs = []
    for event, method, args in (("playbackRangeChanged", "refresh", ()),
                                ("SelectionChanged", "refresh", (True,)),
                                ("animLayerRefresh", "refresh", (True,)),
                                ("Undo", "refresh", (True,)),
                                ("Redo", "refresh", (True,))):
        try:
            jobs.append(cmds.scriptJob(event=[event, partial(_job, method, *args)]))
        except Exception:                                    # noqa: BLE001 - an event this Maya lacks
            pass
    _state()["jobs"] = jobs
    _drop_callbacks()
    callbacks = []
    try:
        import maya.api.OpenMaya as om
        callbacks.append(om.MDGMessage.addTimeChangeCallback(_time_changed))
    except Exception:                                        # noqa: BLE001
        #  no callback: the scriptJob at least moves it when Maya is idle
        try:
            jobs.append(cmds.scriptJob(event=["timeChanged", partial(_job, "on_time")]))
        except Exception:                                    # noqa: BLE001
            pass
    try:
        import maya.api.OpenMayaAnim as oma
        callbacks.append(oma.MAnimMessage.addAnimKeyframeEditedCallback(_keys_edited))
    except Exception:                                        # noqa: BLE001
        pass
    _state()["callbacks"] = callbacks


def build():
    """The uiScript body: the strip inside the workspaceControl - unless the bar
    lives at the bottom edge now (Maya restoring a workspace that held the docked
    control): then the control is hidden and nothing is built in it."""
    import maya.cmds as cmds
    import maya_hubqt
    from . import mode, _hide_control
    if mode() == "edge":
        cmds.evalDeferred(_hide_control, lowestPriority=True)
        return None
    q = maya_hubqt.qt()
    host = maya_hubqt.host_widget(CONTROL) if q is not None else None
    if host is None:
        return None
    for old in host.findChildren(q.QtWidgets.QWidget, ROOT_NAME):
        old.setParent(None)
        old.deleteLater()
    ui = cmds.mayaDpiSetting(q=True, realScaleValue=True) or 1.0
    widget = make(Link(), ui)
    host.layout().addWidget(widget)
    _state()["bar"] = widget
    _state()["host"] = "docked"
    start_jobs()
    return widget
