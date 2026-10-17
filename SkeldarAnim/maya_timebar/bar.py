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

    def add_key(path, x, h, ui, whole, width=None):
        """A key's mark into `path`: a solid bar on its frame line for a key on a
        whole frame, a dashed one where it stands between frames (2026-10-17,
        Maya's slider: the mark is where the key is in time)."""
        top, bottom = key_span(h, ui)
        kw = (width or KEY_W * ui) * (1.0 if whole else DASH_W)
        if whole:
            path.addRect(QtCore.QRectF(x - kw / 2, top, kw, bottom - top))
            return
        dash, gap = DASH * ui, DASH_GAP * ui
        y = top
        while y < bottom:
            path.addRect(QtCore.QRectF(x - kw / 2, y, kw, min(dash, bottom - y)))
            y += dash + gap

    def glow(p, rect, radius, hex_, level, ui, spread=1.0, strength=1.0, edge=True):
        """The radial menu's lit ring: rings fading outward, then a 2 px edge."""
        if level <= 0.01:
            return
        p.setBrush(Qt.NoBrush)
        for i in range(4, 0, -1):
            p.setPen(QtGui.QPen(colour(hex_, min(255, 46 * strength * level * (5 - i) / 4.0)),
                                max(1.0, ui * spread)))
            grow = i * 1.6 * ui * spread
            p.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow), radius + grow, radius + grow)
        if edge:
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

    def age_u(now, t0, kind):
        """0..1 through an effect started at `t0`, None when there is none."""
        if t0 is None:
            return None
        return look.progress(now - t0, kind)

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
            #  the effects (2026-10-17, the mockup): where the press landed, the
            #  glyph that is morphing away, the label that is rolling away, the
            #  loop's turn, the step buttons' push, the bookmark's drop
            self.press_at, self.press_pos = None, None
            self.morph = None           # (old glyph, t0)
            self.roll = None            # (old text, t0)
            self.spin_at = None
            self.reveal_at = None
            self.drop_at = None
            self.nudge = 0              # -1 / +1: a step button's direction
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
                old = self.text()
                self.setText(text)
                self._fit()
                if old and self.strip.motion and self.style_ == "chip":
                    self.roll = (old, self.strip.clock())     # the value rolls up
                    self.strip.kick()
                self.update()

        def set_glyph(self, glyph):
            """A new glyph: the old one shrinks away as the new one grows in."""
            if glyph != self.glyph:
                old = self.glyph
                self.glyph = glyph
                if old and self.strip.motion:
                    self.morph = (old, self.strip.clock())
                    self.strip.kick()
                self.update()

        def spin(self):
            """The loop's arrows turn a third of a turn."""
            if self.strip.motion:
                self.spin_at = self.strip.clock()
                self.strip.kick()

        def drop(self):
            """The bookmark's flag drops in with a swing."""
            if self.strip.motion:
                self.drop_at = self.strip.clock()
                self.strip.kick()

        def enterEvent(self, event):
            self.goal = 1.0
            self.strip.kick()
            super(Pill, self).enterEvent(event)

        def leaveEvent(self, event):
            self.goal = 0.0
            self.strip.kick()
            super(Pill, self).leaveEvent(event)

        def mousePressEvent(self, event):
            now = self.strip.clock()
            self.flash_at = now
            if event.button() == Qt.LeftButton:
                self.press_at = now
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                self.press_pos = QtCore.QPointF(pos)
                self.strip.pressed(self)
            self.strip.kick()
            super(Pill, self).mousePressEvent(event)

        def nextCheckState(self):
            super(Pill, self).nextCheckState()
            self.pop_at = self.strip.clock()
            if self.isChecked() and self.strip.motion:
                self.reveal_at = self.pop_at        # waves staggered in, a fill sweeping

        def breathing(self):
            """Auto key's red dot breathes while it is on."""
            return (self.style_ == "rec" and self.isCheckable() and self.isChecked()
                    and self.strip.motion and self.isVisible())

        def busy(self, now):
            if (abs(self.hover - self.goal) > 0.005
                    or (self.flash_at is not None and now - self.flash_at < FLASH_MS)
                    or (self.pop_at is not None and now - self.pop_at < POP_MS)
                    or self.breathing()):
                return True
            for t0, kind in ((self.press_at, "press"), (self.morph and self.morph[1], "morph"),
                             (self.roll and self.roll[1], "roll"), (self.spin_at, "spin"),
                             (self.reveal_at, "reveal"), (self.drop_at, "drop")):
                if t0 is not None and age_u(now, t0, kind) is not None:
                    return True
            return False

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
            #  a press squeezes it to 0.88 (the mockup), then it springs back
            z = scale * pop * (1.0 + LIFT * self.hover) * (1.0 - 0.12 * flash)
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
            motion = s.motion
            shape = QtGui.QPainterPath()
            shape.addRoundedRect(base, radius, radius)
            # Auto key turned on: the red fill sweeps out from the press
            reveal = age_u(now, self.reveal_at, "reveal") if motion else None
            if reveal is not None and self.style_ == "rec" and self.press_pos is not None:
                p.save()
                p.setClipPath(shape)
                r = max(base.width(), base.height()) * 1.2 * look.ease_out_quint(reveal)
                p.setPen(Qt.NoPen)
                p.setBrush(colour(REC, 110 * (1.0 - reveal)))
                p.drawEllipse(self.press_pos, r, r)
                p.restore()
            # the press: a hot ripple from where it landed
            press = age_u(now, self.press_at, "press") if motion else None
            if press is not None and self.press_pos is not None:
                p.save()
                p.setClipPath(shape)
                r = max(base.width(), base.height()) * (0.25 + 1.1 * look.ease_out_quint(press))
                soft_dot(p, self.press_pos.x(), self.press_pos.y(), r, RIM, 150 * (1.0 - press))
                p.restore()
            # lit: the play button while it plays, a toggle that is on, the
            # breathing red of Auto key, the hover - brighter than a plain glow
            lit = self.hover
            if self.style_ == "play" and s.state.get("playing"):
                lit = max(lit, 0.75)
            elif on and self.style_ == "plain" and self.glyph in ("sound", "cache", "loop"):
                lit = max(lit, 0.35)
            hue = RIM if self.style_ == "play" else tk["accent"]
            if self.breathing():
                breath = 0.5 + 0.5 * math.sin(2 * math.pi * now / float(look.BREATH_MS))
                glow(p, base, radius, REC, 0.25 + 0.45 * breath, ui, spread=1.3, strength=1.4, edge=False)
            glow(p, base, radius, hue, lit, ui, spread=1.4, strength=1.5)
            if press is not None:
                glow(p, base, radius, tk["accent"], 1.0 - press, ui, spread=1.6, strength=2.0)
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
                grect = QtCore.QRectF(gx, base.center().y() - side / 2, side, side)
                self._paint_glyph(p, grect, ink, now)
                left = gx + side + 4 * ui
            if self.text():
                p.setFont(self._font())
                if self.glyph:
                    box = QtCore.QRectF(left, base.top(), base.right() - left - 6 * ui, base.height())
                    p.setPen(ink)
                    p.drawText(box, Qt.AlignVCenter | Qt.AlignLeft, self.text())
                else:
                    self._paint_label(p, base, ink, now, flash)
            p.end()

        def _paint_glyph(self, p, rect, ink, now):
            """The glyph and its motion: a morph from the old one, the loop's turn,
            the step buttons' push, the bookmark's drop, the gear's turn, the sound's
            waves coming in one by one."""
            ui, motion = self.strip.ui, self.strip.motion
            c = rect.center()
            angle, dx, dy = 0.0, 0.0, 0.0
            if self.glyph == "prefs":
                angle += 60.0 * self.hover                  # the gear turns under the mouse
            spin = age_u(now, self.spin_at, "spin") if motion else None
            if spin is not None:
                angle += -120.0 * (1.0 - look.back_out(spin))
            if self.nudge:
                push = look.nudge(age_u(now, self.press_at, "nudge") if motion else None)
                dx += self.nudge * 5 * ui * push
            drop = age_u(now, self.drop_at, "drop") if motion else None
            if drop is not None:
                dy -= 7 * ui * (1.0 - look.back_out(drop))
                angle += 18.0 * math.sin(drop * 3 * math.pi) * (1.0 - drop)
            morph = age_u(now, self.morph[1], "morph") if (motion and self.morph) else None
            p.save()
            p.translate(c.x() + dx, c.y() + dy)
            p.rotate(angle)
            p.translate(-c.x(), -c.y())
            if morph is not None:
                p.save()
                p.setOpacity(p.opacity() * (1.0 - morph))
                k = 1.0 - 0.6 * morph
                p.translate(c)
                p.rotate(-90.0 * morph)
                p.scale(k, k)
                p.translate(-c)
                draw_glyph(p, self.morph[0], rect, ink)
                p.restore()
                k = 0.4 + 0.6 * look.back_out(morph)
                p.translate(c)
                p.rotate(90.0 * (1.0 - morph))
                p.scale(k, k)
                p.translate(-c)
            reveal = age_u(now, self.reveal_at, "reveal") if motion else None
            if reveal is not None and self.glyph == "sound":
                #  the speaker, then its waves one after the other
                p.setClipRect(QtCore.QRectF(rect.left(), rect.top(),
                                            rect.width() * (0.62 + 0.38 * look.ease_out_quint(reveal)),
                                            rect.height()))
            draw_glyph(p, self.glyph, rect, ink)
            p.restore()
            if self.breathing():
                breath = 0.5 + 0.5 * math.sin(2 * math.pi * now / float(look.BREATH_MS))
                soft_dot(p, c.x(), c.y(), 6 * ui * (1.0 + 0.25 * breath), REC, 90 + 90 * breath)

        def _paint_label(self, p, base, ink, now, flash):
            """A chip's text: the old value rolls up and out as the new one rolls in;
            its arrow dips on a press."""
            text, arrow = self.text(), ""
            if text.endswith(u"\u25be"):
                text, arrow = text[:-1].rstrip(), u"\u25be"
            metrics = QtGui.QFontMetricsF(p.font())
            gap = metrics.horizontalAdvance(" ")
            aw = metrics.horizontalAdvance(arrow) if arrow else 0.0
            tw = metrics.horizontalAdvance(text)
            x0 = base.center().x() - (tw + (gap + aw if arrow else 0.0)) / 2.0
            roll = age_u(now, self.roll[1], "roll") if (self.strip.motion and self.roll) else None
            p.save()
            p.setClipRect(base)
            if roll is not None:
                e = look.ease_out_quint(roll)
                old = self.roll[0]
                if old.endswith(u"\u25be"):
                    old = old[:-1].rstrip()
                full = p.opacity()
                p.setOpacity(full * (1.0 - e))
                p.setPen(ink)
                ow = metrics.horizontalAdvance(old)
                p.drawText(QtCore.QRectF(base.center().x() - ow / 2.0 - (gap + aw) / 2.0,
                                         base.top() - base.height() * e, ow + 2, base.height()),
                           Qt.AlignVCenter | Qt.AlignLeft, old)
                p.setOpacity(full * e)
                p.drawText(QtCore.QRectF(x0, base.top() + base.height() * (1.0 - e), tw + 2, base.height()),
                           Qt.AlignVCenter | Qt.AlignLeft, text)
                p.setOpacity(full)
            else:
                p.setPen(ink)
                p.drawText(QtCore.QRectF(x0, base.top(), tw + 2, base.height()), Qt.AlignVCenter | Qt.AlignLeft, text)
            if arrow:
                dip = 3 * self.strip.ui * flash
                p.setPen(ink)
                p.drawText(QtCore.QRectF(x0 + tw + gap, base.top() + dip, aw + 2, base.height()),
                           Qt.AlignVCenter | Qt.AlignLeft, arrow)
            p.restore()

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
            #  the effects (2026-10-17): drawn over the still picture from their age
            self.effects = []           # {"kind", "t0", ...}
            self.trail = {}             # frame -> clock() when the scrub left its cell
            self.glide = None           # (from, to, t0): the playhead gliding there
            self.pulse_at = None        # the playhead's flag pulsing (play on / off)
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
            if self.effects or self.trail:
                return True
            if self.glide is not None and age_u(now, self.glide[2], "glide") is not None:
                return True
            if self.pulse_at is not None and age_u(now, self.pulse_at, "play_on") is not None:
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
            self.effects = [e for e in self.effects if now - e["t0"] < look.EFFECT_MS[e["kind"]]]
            for f in [f for f, t0 in self.trail.items() if now - t0 >= look.EFFECT_MS["trail"]]:
                del self.trail[f]

        # the effects ----------------------------------------------------------
        def fx(self, kind, **data):
            if not self.strip.motion:
                return
            data.update(kind=kind, t0=self.strip.clock())
            self.effects.append(data)
            self.strip.kick()

        def _key_point(self, frame):
            """Where key `frame` stands, as a point of the strip; None off the view."""
            t = self.track()
            if not (t.v0 - 0.5 <= frame <= t.v1 + 1.5):
                return None
            top, bottom = key_span(float(self.height()), self.strip.ui)
            return self.strip.point_of(self, t.x(frame), (top + bottom) / 2.0)

        def key_set(self, frame, breakdown=False):
            """A key set: a beam up its frame line, the key white-hot, two rings
            and sparks thrown up (520 ms)."""
            st = self.strip
            if not st.motion:
                return
            hex_ = BREAKDOWN if breakdown else st.tokens["accent"]
            self.reached[frame] = st.clock()
            self.fx("set", frame=frame, hex=hex_)
            at = self._key_point(frame)
            if at is None:
                return
            ui, ms = st.ui, look.EFFECT_MS["set"]
            cx, cy = at
            st.fx.add("glow", ms, cx=cx, cy=cy, r=30 * ui, hex=hex_, alpha=230)
            st.fx.add("rings", ms, cx=cx, cy=cy, rx=46 * ui, ry=34 * ui, hex=RIM, width=2.6 * ui)
            st.fx.add("rings", ms * 0.85, delay=ms * 0.15, cx=cx, cy=cy, rx=40 * ui, ry=28 * ui, hex=hex_,
                      width=2.0 * ui)
            st.fx.add("sparks", ms, cx=cx, cy=cy, count=12, speed=190 * ui, gravity=320 * ui,
                      spread=120.0, hex=hex_, size=1.6)

        def key_deleted(self, frame, breakdown=False):
            """A key deleted: a flash, a shock ring, the key pinching out, sparks
            falling (600 ms)."""
            st = self.strip
            if not st.motion:
                return
            hex_ = BREAKDOWN if breakdown else st.tokens["accent"]
            self.fx("delete", frame=frame, hex=hex_)
            at = self._key_point(frame)
            if at is None:
                return
            ui, ms = st.ui, look.EFFECT_MS["delete"]
            cx, cy = at
            st.fx.add("glow", ms * 0.6, cx=cx, cy=cy, r=26 * ui, hex=RIM, alpha=230)
            st.fx.add("rings", ms * 0.7, cx=cx, cy=cy, rx=44 * ui, ry=30 * ui, hex=RIM, width=3.0 * ui)
            st.fx.add("sparks", ms, cx=cx, cy=cy, count=24, speed=170 * ui, gravity=620 * ui,
                      spread=360.0, hex=hex_, size=1.5)

        def glide_from(self, before, after):
            """The playhead glides from `before` to `after` (260 ms); False when it
            already glides there or nothing moves."""
            if not self.strip.motion:
                return False
            now = self.strip.clock()
            g = self.glide
            if g is not None and g[1] == after and age_u(now, g[2], "glide") is not None:
                return False
            self.glide = (before, after, now)
            self.strip.kick()
            return True

        def play_changed(self, playing):
            """Play on: a frame closes in round the bar and the flag pulses; off:
            the pulse."""
            if not self.strip.motion:
                return
            if playing:
                self.fx("play_on")
            self.pulse_at = self.strip.clock()
            self.strip.kick()

        def _draw_effects(self, p, t, w, h):
            st = self.strip
            tk, ui, s = st.tokens, st.ui, st.state
            now = st.clock()
            accent = tk["accent"]
            # the scrub's trail: the cells it left, fading
            for frame, t0 in self.trail.items():
                u = look.progress(now - t0, "trail")
                if u is None:
                    continue
                c0, c1 = t.cell(frame)
                p.setPen(Qt.NoPen)
                p.setBrush(colour(accent, 0.28 * 255 * (1.0 - u)))
                p.drawRect(QtCore.QRectF(c0, 0, max(1.0, c1 - c0), h))
            top, bottom = key_span(h, ui)
            for e in self.effects:
                u = look.progress(now - e["t0"], e["kind"])
                if u is None:
                    continue
                kind = e["kind"]
                if kind == "set":
                    x = t.x(e["frame"])
                    rise = look.ease_out_quint(min(1.0, u / 0.45))
                    beam = QtGui.QLinearGradient(0, h, 0, 0)
                    beam.setColorAt(0.0, colour(RIM, 230 * (1.0 - u)))
                    beam.setColorAt(1.0, colour(e["hex"], 0))
                    p.setPen(Qt.NoPen)
                    p.setBrush(QtGui.QBrush(beam))
                    bw = 7 * ui * (1.0 - 0.5 * u)
                    p.drawRect(QtCore.QRectF(x - bw / 2, h * (1.0 - rise), bw, h * rise))
                    # the key rises in with a back ease, white-hot
                    k = look.back_out(min(1.0, u / 0.5))
                    mid = (top + bottom) / 2.0
                    half = (bottom - top) / 2.0 * k
                    p.setBrush(blend(e["hex"], "#ffffff", 0.85 * (1.0 - u)))
                    kw = KEY_W * ui * (1.0 + 1.2 * (1.0 - u))
                    p.drawRect(QtCore.QRectF(x - kw / 2, mid - half, kw, 2 * half))
                elif kind == "delete":
                    x = t.x(e["frame"])
                    c0, c1 = t.cell(e["frame"])
                    p.setPen(Qt.NoPen)
                    p.setBrush(colour("#ffffff", 150 * (1.0 - u) ** 2))
                    p.drawRect(QtCore.QRectF(c0, 0, max(2 * ui, c1 - c0), h))
                    pinch = 1.0 - look.ease_in_quint(min(1.0, u / 0.7))
                    if pinch > 0.01:
                        mid = (top + bottom) / 2.0
                        half = (bottom - top) / 2.0 * pinch
                        kw = KEY_W * ui * (1.0 + 1.5 * (1.0 - pinch))
                        p.setBrush(blend(e["hex"], RIM, 1.0 - pinch))
                        p.drawRect(QtCore.QRectF(x - kw / 2 * pinch, mid - half, kw * pinch, 2 * half))
                elif kind == "snap":
                    hex_ = BREAKDOWN if e.get("bd") else accent
                    ghost = QtGui.QPainterPath()
                    add_key(ghost, t.x(e["src"]), h, ui, False)
                    p.fillPath(ghost, colour(hex_, 200 * (1.0 - u)))
                    x = t.x(e["src"] + (e["dst"] - e["src"]) * look.back_out(u))
                    mark = QtGui.QPainterPath()
                    add_key(mark, x, h, ui, True, width=KEY_W * ui * 1.4)
                    p.fillPath(mark, blend(hex_, RIM, 0.7 * (1.0 - u)))
                elif kind == "move":
                    k = look.back_out(u)
                    for src, dst in e["pairs"]:
                        ghost = QtGui.QPainterPath()
                        add_key(ghost, t.x(src), h, ui, look.on_frame(src))
                        p.fillPath(ghost, colour(RIM, 110 * (1.0 - u)))
                        mark = QtGui.QPainterPath()
                        add_key(mark, t.x(src + (dst - src) * k), h, ui, look.on_frame(dst),
                                width=KEY_W * ui * 1.3)
                        p.fillPath(mark, blend(accent, RIM, 0.6 * (1.0 - u)))
                    a, b = e["target"]
                    rect = QtCore.QRectF(t.x(a), 1, t.end(b) - t.x(a), h - 2)
                    glow(p, rect, 3 * ui, HIGHLIGHT, 1.0 - u, ui, strength=1.5)
                elif kind == "mark":
                    x0, x1 = t.x(e["start"]), t.x(e["stop"])
                    if x1 < 0 or x0 > w:
                        continue
                    c = QtGui.QColor.fromRgbF(*[max(0.0, min(1.0, float(v))) for v in e["rgb"]])
                    full = max(2.0, x1 - x0 - 2)
                    open_ = look.ease_out_quint(min(1.0, u / 0.7))
                    mid = x0 + 1 + full / 2.0
                    band = QtCore.QRectF(mid - full * open_ / 2.0, (LABEL_H + 1) * ui, full * open_, BAND_H * ui)
                    p.setPen(Qt.NoPen)
                    c.setAlpha(int(200 * (1.0 - u)))
                    p.setBrush(c)
                    p.drawRoundedRect(band, 3 * ui, 3 * ui)
                    glow(p, band, 3 * ui, c.name(), 1.0 - u, ui, strength=1.6, edge=False)
                elif kind == "loop":
                    # an orange sweep from the end back to the start
                    xe, xs = t.end(s["p1"]), t.x(s["p0"])
                    head = xe + (xs - xe) * look.ease_in_out(u)
                    tail = 70 * ui
                    sweep = QtGui.QLinearGradient(head, 0, head + tail, 0)
                    sweep.setColorAt(0.0, colour(RIM, 200 * (1.0 - u * 0.5)))
                    sweep.setColorAt(0.25, colour(accent, 150 * (1.0 - u * 0.5)))
                    sweep.setColorAt(1.0, colour(accent, 0))
                    p.setPen(Qt.NoPen)
                    p.setBrush(QtGui.QBrush(sweep))
                    p.drawRect(QtCore.QRectF(head, 0, tail, h))

        def _draw_play_frame(self, p, w, h):
            """Play on: an accent frame closing in round the bar."""
            st, now = self.strip, self.strip.clock()
            for e in self.effects:
                if e["kind"] != "play_on":
                    continue
                u = look.progress(now - e["t0"], "play_on")
                if u is None:
                    continue
                ui = st.ui
                inset = 1 + 7 * ui * look.ease_out_quint(u)
                p.setBrush(Qt.NoBrush)
                p.setPen(QtGui.QPen(colour(st.tokens["accent"], 255 * (1.0 - u)), 1 + 2.5 * ui * (1.0 - u)))
                p.drawRoundedRect(QtCore.QRectF(inset, inset, w - 2 * inset, h - 2 * inset), 6 * ui, 6 * ui)

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
            if st.motion and (self.effects or self.trail):
                self._draw_effects(p, t, w, h)
            self._draw_moving_keys(p, t, entrance, moving, opacity)
            self._draw_playhead(p, t, w, h)
            if st.motion and self.effects:
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
                            add_key(path, t.x(shown), h, ui, look.on_frame(shown))
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
                    g = self.mapToGlobal(QtCore.QPoint(int(t.x(shown)), int(KEY_Y * ui)))
                    ks, burst = st.entrance_of(g.x(), g.y())
                    z *= ks
                x = t.x(shown)
                whole = look.on_frame(shown)
                top, bottom = key_span(h, ui)
                kw = KEY_W * ui * min(z, 1.6)
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
                add_key(mark, x, h, ui, whole, width=kw)
                p.drawPath(mark)
            p.setOpacity(opacity)

        def _draw_playhead(self, p, t, w, h):
            st = self.strip
            tk, ui, s = st.tokens, st.ui, st.state
            now = st.clock()
            c0, c1 = t.cell(s["now"])
            g = self.glide
            gu = age_u(now, g[2], "glide") if (g is not None and st.motion) else None
            if gu is not None and g[1] == s["now"]:
                #  gliding there: the cell slides from the frame it left
                f0, f1 = math.floor(g[0] + 1e-9), math.floor(g[1] + 1e-9)
                shown = f0 + (f1 - f0) * look.ease_in_out(gu)
                c0, c1 = t.x(shown), t.x(shown + 1)
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
            pu = age_u(now, self.pulse_at, "play_on") if (self.pulse_at is not None and st.motion) else None
            pulse = math.sin(math.pi * pu) if pu is not None else 0.0
            fz = (1.0 + 0.12 * self.head_lift) * (1.0 + 0.25 * pulse)
            bold = QtGui.QFont("Consolas")
            bold.setBold(True)
            bold.setPixelSize(max(8, int(10 * ui * fz)))
            p.setFont(bold)
            text = look.frame_text(s["now"])
            tw = QtGui.QFontMetricsF(bold).horizontalAdvance(text) + 10 * ui * fz
            th = 14 * ui * fz
            fx = min(max(x - tw / 2, 1), w - tw - 1)
            flag = QtCore.QRectF(fx, h - th, tw, th)          # at the bottom, as Maya's
            glow(p, flag, 3 * ui, head.name(), max(self.head_lift * 0.8, pulse), ui, strength=1.0 + pulse)
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
                    pairs = [(k, look.mapped(k, selection, target)) for k in st.keys + st.breakdowns
                             if look.inside(k, selection)]
                    st._quiet_keys = True
                    self.fx("move", pairs=pairs, target=tuple(target))
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
            for k in self.strip.keys + self.strip.breakdowns:
                d = abs(t.x(k) - x)
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
            if self.strip.motion:
                self.trail[math.floor(before + 1e-9)] = self.strip.clock()
            self.strip.show_now()
            self.repaint()
            t1 = time.perf_counter()
            self.strip.call("set_time" if update else "scrub_only", frame)
            meter = _state().get("meter")
            if meter is not None:          # the scrub meter: our work, then Maya's frame change
                meter["ours"].append((t1 - t0) * 1000.0)
                meter["mayas"].append((time.perf_counter() - t1) * 1000.0)

    # -- the effects' overlay ------------------------------------------------------

    class FxLayer(QtWidgets.QWidget):
        """Over the whole strip, deaf to the mouse: the rings, sparks and glows of
        the effects (2026-10-17), which fly past the control that made them. Each
        is drawn from its age alone - a spark's flight is a formula, not a state -
        and the layer paints only while one is alive."""

        def __init__(self, strip):
            super(FxLayer, self).__init__(strip)
            self.strip = strip
            self.setObjectName("skeldarTimeBarFx")
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setAttribute(Qt.WA_NoSystemBackground, True)
            self.items = []
            self._was_busy = False
            self._seed = 1

        def add(self, kind, ms, delay=0.0, **data):
            if not self.strip.motion:
                return
            self._seed += 1
            data.update(kind=kind, ms=float(ms), t0=self.strip.clock() + delay, seed=self._seed)
            self.items.append(data)
            self.raise_()
            self.strip.kick()

        def busy(self, now):
            self.items = [i for i in self.items if now - i["t0"] < i["ms"]]
            return bool(self.items)

        def paintEvent(self, _event):
            if not self.items:
                return
            try:
                p = QtGui.QPainter(self)
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                now = self.strip.clock()
                for item in self.items:
                    age = now - item["t0"]
                    if 0 <= age < item["ms"]:
                        getattr(self, "_" + item["kind"])(p, item, age / item["ms"], age)
                p.end()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _rings(self, p, i, u, _age):
            e = look.ease_out_quint(u)
            p.setBrush(Qt.NoBrush)
            p.setPen(QtGui.QPen(colour(i["hex"], 235 * (1.0 - u) ** 1.4), i["width"] * (1.0 - 0.6 * u)))
            p.drawEllipse(QtCore.QPointF(i["cx"], i["cy"]), i["rx"] * (0.15 + 0.85 * e), i["ry"] * (0.15 + 0.85 * e))

        def _glow(self, p, i, u, _age):
            soft_dot(p, i["cx"], i["cy"], i["r"] * (0.7 + 0.3 * u), i["hex"], i.get("alpha", 210) * (1.0 - u) ** 2)

        def _sparks(self, p, i, _u, age):
            ui = self.strip.ui
            for dx, dy, life in look.sparks(i["seed"], i["count"], age, i["ms"], i["speed"],
                                            i["gravity"], up=i.get("up", True), spread=i.get("spread", 180.0)):
                x, y = i["cx"] + dx, i["cy"] + dy
                size = i.get("size", 1.6) * ui * (0.5 + 0.5 * life)
                soft_dot(p, x, y, size * 3.2, i["hex"], 150 * life)
                p.setPen(Qt.NoPen)
                p.setBrush(colour(RIM, 255 * life))
                p.drawEllipse(QtCore.QPointF(x, y), size, size)

        def _frame_glow(self, p, i, u, _age):
            glow(p, i["rect"], i["radius"], i["hex"], 1.0 - u, self.strip.ui, spread=1.4, strength=1.8)

        def _plus(self, p, i, u, _age):
            ui = self.strip.ui
            font = QtGui.QFont(self.font())
            font.setBold(True)
            font.setPixelSize(max(9, int(13 * ui)))
            p.setFont(font)
            p.setPen(colour(i["hex"], 255 * (1.0 - u) ** 1.2))
            y = i["cy"] - 18 * ui * look.ease_out_quint(u)
            p.drawText(QtCore.QRectF(i["cx"] - 10 * ui, y - 10 * ui, 20 * ui, 20 * ui), Qt.AlignCenter, "+")

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
            self.loop.clicked.connect(lambda *_a: (self.loop.spin(), self._do("cycle_loop")))
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
                b.nudge = {"start": -1, "pfrm": -1, "pkey": -1, "back": -1,
                           "nkey": 1, "nfrm": 1, "end": 1}.get(name, 0)
                b.clicked.connect(lambda *_a, f=action: (f(), self.refresh()))
                bottom.addWidget(b)
                self.transport[name] = b
            self.play, self.prev, self.next = self.transport["play"], self.transport["pkey"], self.transport["nkey"]
            # the effects (2026-10-17)
            self.fx = FxLayer(self)
            self.fx.setGeometry(self.rect())
            self._keys_read = False     # the first read of the keys is no edit
            self._quiet_keys = False    # a key move draws its own effect
            self._was_playing = None
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

        def burst_at(self, gx, gy, opening=True):
            """The controls - and the keys - pop in from the global point (gx, gy),
            the nearest first, or fold toward it, the farthest first (2026-10-16,
            mockup A, 1.5x slower). Returns how long it takes, ms."""
            delays, far = {}, 0.0
            points = [(w.index, w.mapToGlobal(w.rect().center())) for w in self.moving]
            t = self.timeline.track()
            points += [(None, self.timeline.mapToGlobal(QtCore.QPoint(int(t.x(k)), int(KEY_Y * self.ui))))
                       for k in self.keys + self.breakdowns]
            for index, c in points:
                if opening:
                    d = look.burst_delay(c.x() - gx, c.y() - gy, self.ui)
                else:
                    d = look.fold_delay(c.x() - gx, self.ui)
                far = max(far, d)
                if index is not None:
                    delays[index] = d
            if not self.motion:
                self.entrance = None
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

        def pressed(self, pill):
            """A press: a ring out of the button and its sparks (the mockup)."""
            if not self.motion:
                return
            ui, m = self.ui, pill.margin()
            cx, cy = self.point_of(pill, pill.width() / 2.0, pill.height() / 2.0)
            w, h = pill.width() - 2 * m, pill.height() - 2 * m
            hue = RIM if pill.style_ == "play" else self.tokens["accent"]
            self.fx.add("rings", look.EFFECT_MS["press"], cx=cx, cy=cy, rx=w * 0.95, ry=h * 1.05,
                        hex=hue, width=2.2 * ui)
            self.fx.add("sparks", look.EFFECT_MS["press"], cx=cx, cy=cy, count=8, speed=120 * ui,
                        gravity=160 * ui, spread=300.0, hex=self.tokens["accent"], size=1.3)

        def glow_field(self):
            """The frame field glows when the time jumps."""
            if not self.motion:
                return
            m = 1
            x0, y0 = self.point_of(self.field, m, m)
            rect = QtCore.QRectF(x0, y0, self.field.width() - 2 * m, self.field.height() - 2 * m)
            self.fx.add("frame_glow", look.EFFECT_MS["field"], rect=rect, radius=5 * self.ui,
                        hex=self.tokens["accent"])

        def jumped(self, before, after):
            """The time went from `before` to `after` by a press (a step, a key, the
            field): the playhead glides there and the field glows."""
            if self.state.get("playing") or abs(after - before) < 1.5:
                return
            if self.timeline.glide_from(before, after):
                self.glow_field()

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
                old_keys, old_bds, old_marks = self.keys, self.breakdowns, self.marks
                if found is not None:
                    self.keys, self.breakdowns = list(found[0]), list(found[1])
                    self.keys_dirty = False
                self.marks = self.call("bookmarks") or []
                if found is not None:
                    if self._keys_read and not self._quiet_keys:
                        self._edit_effects(old_keys, old_bds, old_marks)
                    self._keys_read, self._quiet_keys = True, False
            self._sound()
            self._paint_widgets()
            self.timeline.update()
            self.range.update()

        def _edit_effects(self, old_keys, old_bds, old_marks):
            """A key set, deleted or snapped, a bookmark added: its effect."""
            if not self.motion:
                return
            tl = self.timeline
            for old, new, bd in ((old_keys, self.keys, False), (old_bds, self.breakdowns, True)):
                added, removed, snapped = look.key_changes(old, new)
                for k in added:
                    tl.key_set(k, bd)
                for k in removed:
                    tl.key_deleted(k, bd)
                for src, dst in snapped:
                    tl.fx("snap", src=src, dst=dst, bd=bd)
            before = set((m[0], m[1]) for m in old_marks)
            fresh = [m for m in self.marks if (m[0], m[1]) not in before]
            if len(fresh) <= 2:
                for m in fresh:
                    tl.fx("mark", start=m[0], stop=m[1], rgb=tuple(m[2]))

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
                    if now < before - 1:               # the loop went round: a sweep back
                        self.timeline.fx("loop")
                elif not self.timeline.drag:
                    self.jumped(before, now)
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
            if self._was_playing is not None and playing != self._was_playing:
                self.timeline.play_changed(playing)
            self._was_playing = playing
            self.play.set_glyph("pause" if playing else "play")
            self.play.update()
            self.fps.set_label(look.fps_label(s["unit"]) + u" ▾")
            self.auto.setChecked(bool(s["auto"]))
            loop = s.get("loop") or "continuous"
            self.loop.set_glyph({"continuous": "loop", "once": "once", "oscillate": "oscillate"}.get(loop, "loop"))
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
            self.jumped(before, self.state["now"])

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
            self.jumped(before, frame)

        def _step(self, forward):
            before = self.state["now"]
            self.call("step_key", forward, self.keys + self.breakdowns)
            self.refresh()
            self.timeline.reach(before, self.state["now"])
            self.jumped(before, self.state["now"])

        def _bookmark(self, forward):
            self.call("step_bookmark", forward)
            self.refresh()

        def _add_bookmark(self):
            self.bm_add.drop()
            if self.motion:
                cx, cy = self.point_of(self.bm_add, self.bm_add.width() / 2.0, self.bm_add.margin())
                self.fx.add("plus", look.EFFECT_MS["plus"], cx=cx, cy=cy, hex=self.tokens["accent_text"])
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
