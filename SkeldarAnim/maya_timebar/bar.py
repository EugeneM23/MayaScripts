"""The Time Bar (2026-10-16): Maya's two rows - the range row on top, the time row
below - painted in the hub's look.

Range row: animation start | playback start | the range block | playback end |
animation end | character set | layer | fps | loop | cached playback | speed |
sound | Auto key | layers | preferences.
Time row: the timeline (bookmarks, the sound's waveform, keys and breakdowns, the
highlight that moves and scales keys, the playhead) | the current frame | eight
transport buttons.

No motion and no light (2026-11-19, «удаляем все подсветки и анимации из плагина»):
everything is drawn in its end state at once, a control's face changes flatly under
the mouse. The widget talks to Maya only through a `link` (scene.py in Maya, a fake
in the tests); the jobs find the strip through the module state - never a held
wrapper (trap 135).
Spec: docs/superpowers/specs/2026-10-16-time-bar-design.md
"""

import math
import time
import traceback
import types

from . import CONTROL, look, _state

ROOT_NAME = "skeldarTimeBarRoot"
TIMER_MS = 250
PAD = 1                # logical px either side of the timeline's frames: inside its border only
#  (was 10, 2026-10-22: the pads read as black gaps at both ends, dimmed as outside the range)
TIMELINE_H = 40         # logical px: the bookmarks band, the keys, the ruler
BAND_H = 11             # the bookmarks band, its name inside
LABEL_H = 11            # the frame numbers' row at the very top, the band under it (2026-10-17)
KEY_Y = 21              # the keys' centre
KEY_W = 2.0             # a key's mark, logical px wide (2026-10-17: a line, as Maya's; 20 % narrower since)
DASH_W = 0.8            # a key between frames: its dashes this share of a mark's width
DASH, DASH_GAP = 3.0, 2.0
HEAD_FILL = 70          # the playhead's cell, its fill's alpha
CARET_H = 15            # logical px: the caret line over the timeline's numbers (2026-10-19, B1)
CARET_FLAG_H = 11.5     # the caret's flag
CARET_MIN_W = 20


def key_span(h, ui):
    """(top, bottom) of a key's mark: under the bookmarks band to the bottom."""
    return (LABEL_H + 1) * ui, h - 1.5 * ui

REC = "#e0524a"
BREAKDOWN = "#6fb7c9"
HIGHLIGHT = "#7fa9e6"
WAVE = "#565a68"

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
    #  cached playback: a strip of film with a bolt in its frame (2026-10-20, the two bars
    #  read as «=»: «перерисуй иконку на понятную»)
    "cache": ("M1 2h14v12H1zM2.4 4.6v6.8h11.2V4.6zM3 2.7h1.6v1.2H3zM7.2 2.7h1.6v1.2H7.2z"
              "M11.4 2.7h1.6v1.2h-1.6zM3 12.1h1.6v1.2H3zM7.2 12.1h1.6v1.2H7.2zM11.4 12.1h1.6v1.2h-1.6z"
              "M9.7 4.9L5 8.7h2.9l-1.4 2.5 4.8-3.9H8.4z"),
    "sound": "M2 6h3l4-3v10L5 10H2zM11 4.6l1-1a6.4 6.4 0 0 1 0 8.8l-1-1a5 5 0 0 0 0-6.8z",
    "auto": "M8 2a6 6 0 1 1 0 12A6 6 0 0 1 8 2zm0 1.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9zM8 5a3 3 0 1 1 0 6 3 3 0 0 1 0-6z",
    "pin": "M9.5 1.5l5 5-1.4 1.4-1.1-.4-2.6 2.6.4 3.1-1.4 1.4-3-3-3.4 3.4-1-1 3.4-3.4-3-3 1.4-1.4 3.1.4 2.6-2.6-.4-1.1z",
    "prefs": ("M7 1h2l.4 1.8 1.4.6 1.6-1 1.4 1.4-1 1.6.6 1.4L15 7v2l-1.8.4-.6 1.4 1 1.6-1.4 1.4-1.6-1-1.4.6"
              "L9 15H7l-.4-1.8-1.4-.6-1.6 1-1.4-1.4 1-1.6-.6-1.4L1 9V7l1.8-.4.6-1.4-1-1.6 1.4-1.4 1.6 1 1.4-.6z"
              "M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z"),
}

#  the layer panel's glyphs (2026-10-18)
GLYPHS.update({
    "layers": "M8 1.2l7 3.6-7 3.6-7-3.6zM2.4 7.3L8 10.2l5.6-2.9 1.4.7L8 11.6 1 8zM2.4 10.5L8 13.4l5.6-2.9 1.4.7L8 14.8 1 11.2z",
    "lanes": "M1 3h4v2H1zM6 3h9v2H6zM1 7h7v2H1zM9 7h6v2H9zM1 11h3v2H1zM5 11h10v2H5z",
    "lock": "M4.5 7V5a3.5 3.5 0 0 1 7 0v2H13v7H3V7zm1.6 0h3.8V5a1.9 1.9 0 0 0-3.8 0z",
    "plus": "M7 2h2v5h5v2H9v5H7V9H2V7h5z",
    "addsel": "M2 2h6v2H4v8h4v2H2zM9 7h3V4l3.5 4-3.5 4V9H9z",
    "remsel": "M8 2h6v12H8v-2h4V4H8zM10 7H6.5V4L3 8l3.5 4V9H10z",
    "merge": "M3 2h2v4c0 1.2 1 2 3 2s3-.8 3-2V2h2v4c0 2-1.4 3.4-4 3.9V12h2.2L8 15l-3.2-3H7V9.9C4.4 9.4 3 8 3 6z",
    "select": "M3 1.5l9.5 7.2-4.2.6 2.5 4.6-1.9 1-2.5-4.7L3 13z",
    "trash": "M6 1h4v1.5h4V4H2V2.5h4zM3.5 5h9l-.8 10H4.3z",
})

_KIT = None


def skill_look():
    from maya_skillbar import look as skill_look_
    return skill_look_


def _skills_of(link):
    """The skill bar's model as the link gives it (Maya: the user's file), else in memory."""
    from maya_skillbar import skills
    try:
        made = link.skills() if (hasattr(link, "skills") or isinstance(link, Link)) else None
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        made = None
    return made if made is not None else skills.MemorySkills()


def kit():
    """The strip's paint helpers for the layer panel (made with the classes)."""
    if _KIT is None:
        classes()
    return _KIT


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


def steel_on():
    """⋮ -> Time bar ▸ Steel keys: the animator's choice, else on - the default since
    2026-10-20 («стальные ключи сделаем ключами по умолчанию»); off where Maya cannot
    be asked (the tests)."""
    try:
        import maya.cmds as cmds
        if cmds.optionVar(exists=look.STEEL_VAR):
            return bool(cmds.optionVar(q=look.STEEL_VAR))
        return look.STEEL_DEFAULT
    except Exception:                                        # noqa: BLE001
        return False


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

    def draw_span_labels(p, t, span, top, width, ui, tk):
        """A highlight's first and last frame on blue pills at its edges (inside the
        block when both fit, else beyond them) - the same on the timeline and the lanes."""
        a, b = span
        font = QtGui.QFont("Consolas")
        font.setPixelSize(max(8, int(10 * ui)))
        font.setBold(True)
        p.setFont(font)
        metrics = QtGui.QFontMetricsF(font)
        pad, ph = 3 * ui, metrics.height() + 1 * ui
        single = abs(b - a) < 1e-6
        texts = [look.frame_text(a)] + ([] if single else [look.frame_text(b)])
        widths = [metrics.horizontalAdvance(s) + 2 * pad for s in texts]
        lefts = look.span_labels(t.x(a), t.end(b), widths[0], widths[-1], width,
                                 look.SPAN_GAP * ui, single)
        for text, tw, left in zip(texts, widths, lefts):
            if left is None:
                continue
            r = QtCore.QRectF(left, top, tw, ph)
            p.setPen(Qt.NoPen)
            p.setBrush(colour(HIGHLIGHT))
            p.drawRoundedRect(r, 3 * ui, 3 * ui)
            p.setPen(colour(tk["panel"]))
            p.drawText(r, Qt.AlignCenter, text)
        p.setPen(Qt.NoPen)

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

    ingots = {}

    def _ratio(p):
        try:
            return float(p.device().devicePixelRatioF()) or 1.0
        except Exception:                                    # noqa: BLE001
            return 1.0

    def ingot(p, rect, hex_, ui, shadow=True):
        """A steel key on a whole frame, drawn once per size, place within its pixel,
        colour and scale into a picture (2026-10-27: drawing each ingot's gradient and
        faces cost 3.7 ms a frame on a dense take - with a picture it is one
        drawPixmap). Sizes and the place inside the pixel are kept to a quarter pixel."""
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        if w <= 0 or h <= 0:
            return
        dpr = _ratio(p)
        qw, qh = round(w * 4) / 4.0, round(h * 4) / 4.0
        bx, by = math.floor(x), math.floor(y)
        ox, oy = round((x - bx) * 4) / 4.0, round((y - by) * 4) / 4.0
        pad = int(math.ceil(3 * ui)) + 1
        key = (qw, qh, ox, oy, hex_, round(ui, 3), bool(shadow), dpr)
        picture = ingots.get(key)
        if picture is None:
            if len(ingots) >= 800:
                ingots.clear()
            pw, ph = qw + ox + 2 * pad, qh + oy + 2 * pad
            picture = QtGui.QPixmap(int(math.ceil(pw * dpr)), int(math.ceil(ph * dpr)))
            picture.setDevicePixelRatio(dpr)
            picture.fill(Qt.transparent)
            ip = QtGui.QPainter(picture)
            ip.setRenderHint(QtGui.QPainter.Antialiasing)
            draw_ingot(ip, QtCore.QRectF(pad + ox, pad + oy, qw, qh), hex_, ui, shadow)
            ip.end()
            ingots[key] = picture
        p.drawPixmap(QtCore.QPointF(bx - pad, by - pad), picture)

    def draw_ingot(p, rect, hex_, ui, shadow=True):
        """A steel key on a whole frame (2026-10-20, the mockup's «фаска»): a bevelled bar -
        a soft shadow under it, the face lit at its top and shaded to its bottom, a light
        left face and a dark right one, a light top edge and a dark bottom edge."""
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        if w <= 0 or h <= 0:
            return
        r = min(2.0 * ui, w * 0.2)
        p.setPen(Qt.NoPen)
        if shadow:
            p.setBrush(colour("#000000", 255 * look.INGOT_SHADOW * 0.35))
            p.drawRoundedRect(rect.translated(ui, 2 * ui).adjusted(-0.5 * ui, -0.5 * ui, 0.5 * ui, 0.5 * ui),
                              r + 0.5 * ui, r + 0.5 * ui)
            p.setBrush(colour("#000000", 255 * look.INGOT_SHADOW * 0.6))
            p.drawRoundedRect(rect.translated(ui, 2 * ui), r, r)
        top, mid, bottom = look.ingot_shades(hex_)
        g = QtGui.QLinearGradient(0.0, y, 0.0, y + h)
        g.setColorAt(0.0, colour(top))
        g.setColorAt(look.INGOT_MID, colour(mid))
        g.setColorAt(1.0, colour(bottom))
        p.setBrush(QtGui.QBrush(g))
        p.drawRoundedRect(rect, r, r)
        side = look.ingot_side(w, ui)
        line = max(1.0, 0.75 * ui)
        if h > 2 * line:
            p.fillRect(QtCore.QRectF(x, y + line, side, h - 2 * line),
                       colour("#ffffff", 255 * look.INGOT_SIDE[0]))
            p.fillRect(QtCore.QRectF(x + w - side, y + line, side, h - 2 * line),
                       colour("#000000", 255 * look.INGOT_SIDE[1]))
        if w > side * 1.2:
            p.fillRect(QtCore.QRectF(x + side * 0.6, y, w - side * 1.2, line),
                       colour("#ffffff", 255 * look.INGOT_EDGE[0]))
            p.fillRect(QtCore.QRectF(x + side * 0.5, y + h - line, w - side, line),
                       colour("#000000", 255 * look.INGOT_EDGE[1]))

    def add_key(path, x, h, ui, whole, cell=None):
        """A key's mark into `path`: on a whole frame its frame's cell filled, with a
        gap between neighbours (`cell`, px a frame; the animator's mockup, 2026-10-17);
        where it stands between frames a dashed line on its time (Maya's slider: the
        mark is where the key is in time)."""
        top, bottom = key_span(h, ui)
        if whole and cell:
            l, tp, w, hh = look.key_cell(x, cell, top, bottom, ui)
            path.addRoundedRect(QtCore.QRectF(l, tp, w, hh), 1.5 * ui, 1.5 * ui)
            return
        kw = KEY_W * ui * (1.0 if whole else DASH_W)
        if whole:
            path.addRect(QtCore.QRectF(x - kw / 2, top, kw, bottom - top))
            return
        dash, gap = DASH * ui, DASH_GAP * ui
        y = top
        while y < bottom:
            path.addRect(QtCore.QRectF(x - kw / 2, y, kw, min(dash, bottom - y)))
            y += dash + gap

    # -- a painted control -------------------------------------------------------

    class Pill(QtWidgets.QAbstractButton):
        """A button the strip paints: an icon, a text or both; plain, a chip, the
        orange play, a toggle lit when on. Its face changes flatly under the mouse."""

        def __init__(self, strip, glyph="", text="", tip="", style="plain", toggle=False, accent_glyph=False):
            super(Pill, self).__init__(strip)
            self.strip, self.glyph, self.style_ = strip, glyph, style
            self.accent_glyph = accent_glyph
            self.setText(text)
            self.setToolTip(tip)
            self.setCheckable(toggle)
            self.setCursor(Qt.PointingHandCursor)
            self.hovered = False        # the mouse over it: the hover face
            self.badge = ""             # a small round count at the top-right (2026-10-18)
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

        def set_badge(self, text):
            text = str(text) if text else ""
            if text != self.badge:
                self.badge = text
                self.update()

        def enterEvent(self, event):
            self.hovered = True
            self.update()
            super(Pill, self).enterEvent(event)

        def leaveEvent(self, event):
            self.hovered = False
            self.update()
            super(Pill, self).leaveEvent(event)

        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            tk, ui = self.strip.tokens, self.strip.ui
            hover = self.hovered
            m = self.margin()
            base = QtCore.QRectF(self.rect()).adjusted(m, m, -m, -m)
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            radius = (base.height() / 2.0) if self.style_ == "chip" else 5 * ui
            on = self.isCheckable() and self.isChecked()
            if self.style_ == "play":
                face = colour(tk["accent_hover"] if hover else tk["accent"])
            elif self.style_ == "chip":
                face = colour(tk["hover"] if hover else tk["card"])
            elif on:
                face = colour("#3a2323") if self.style_ == "rec" else colour(tk["accent_tint"])
            else:
                face = colour(tk["hover"], 255 if hover else 0)
            p.setPen(QtGui.QPen(colour(tk["line"]), 1) if self.style_ == "chip" else Qt.NoPen)
            p.setBrush(face)
            p.drawRoundedRect(base, radius, radius)
            if self.style_ == "play":
                ink = colour(tk["on_accent"])
            elif self.style_ == "rec" and on:
                ink = colour(REC)
            elif on or self.accent_glyph:
                ink = colour(tk["accent_text"])
            else:
                ink = colour(tk["text"] if hover else tk["muted"])
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
            if self.badge:
                self._paint_badge(p, base, on)
            p.end()

        def _paint_badge(self, p, base, on):
            """The count: card_active face and text2 ink (accent and on_accent while the pill is on),
            a 1 px panel border."""
            tk, ui = self.strip.tokens, self.strip.ui
            font = QtGui.QFont("Consolas")
            font.setPixelSize(max(7, int(9 * ui)))
            p.setFont(font)
            w = max(13 * ui, QtGui.QFontMetrics(font).horizontalAdvance(self.badge) + 7 * ui)
            h = 13 * ui
            box = QtCore.QRectF(base.right() - w + 4 * ui, base.top() - 3 * ui, w, h)
            p.setPen(QtGui.QPen(colour(tk["panel"]), max(1.0, ui)))
            p.setBrush(colour(tk["accent"] if on else tk["card_active"]))
            p.drawRoundedRect(box, h / 2.0, h / 2.0)
            p.setPen(colour(tk["on_accent"] if on else tk["text2"]))
            p.drawText(box, Qt.AlignCenter, self.badge)

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

        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            s, tk, ui = self.strip.state, self.strip.tokens, self.strip.ui
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            r = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
            p.setBrush(colour(tk["track"]))
            p.drawRoundedRect(r, 6 * ui, 6 * ui)
            x0, x1 = self.edges()
            thumb = QtCore.QRectF(x0 + 1, 2 * ui, x1 - x0 - 2, r.height() - 4 * ui)
            p.setPen(Qt.NoPen)
            p.setBrush(colour(tk["thumb"]))
            p.drawRoundedRect(thumb, 4 * ui, 4 * ui)
            p.setBrush(colour(tk["accent"]))
            for x in (thumb.left() + 2 * ui, thumb.right() - 6 * ui):
                ew, eh = 4 * ui, thumb.height() - 2 * ui
                edge = QtCore.QRectF(x + 2 * ui - ew / 2, thumb.center().y() - eh / 2, ew, eh)
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
                self.setCursor(Qt.SizeHorCursor if part in ("l", "r") else Qt.OpenHandCursor)
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

    # -- keys during a drag ------------------------------------------------------

    TEXT_INPUTS = (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit,
                   QtWidgets.QAbstractSpinBox)

    class DragKeys(QtCore.QObject):
        """S (Shift+W/E/R) on the strip (`look.key_action`): during a timeline drag a
        held button keeps the key from Maya's hotkeys, so we catch it application-wide
        and run Maya's own command (`look.DRAG_KEYS`), or put a copy of a dragged key
        block where the drag has it now (only the selected keys, none in the gaps);
        with no drag and a highlight standing, the key goes on every frame of the
        highlight. Installed for the strip's life."""

        def __init__(self, strip):
            super(DragKeys, self).__init__(strip)
            self.strip = strip

        def _plain_key(self):
            """Not typing into a field: only then is S the strip's. The strip may be
            hidden at the bottom edge - a highlight set, the mouse gone to the
            viewport, S pressed there is still the highlight's."""
            focus = QtWidgets.QApplication.focusWidget()
            return not (focus is not None and isinstance(focus, TEXT_INPUTS))

        def eventFilter(self, obj, event):
            kind = event.type()
            override = kind == QtCore.QEvent.ShortcutOverride
            if kind != QtCore.QEvent.KeyPress and not override:
                return False
            tl = self.strip.timeline
            if event.isAutoRepeat():
                return bool(tl.drag) and int(event.key()) in (83, 87, 69, 82)   # S W E R held down
            mods, code = event.modifiers(), int(event.key())
            letter = chr(code) if 65 <= code <= 90 else ""          # Qt.Key_A .. Key_Z
            name = look.drag_key(letter,
                                 bool(mods & Qt.ShiftModifier), bool(mods & Qt.ControlModifier),
                                 bool(mods & Qt.AltModifier))
            if not name:
                return False
            if not tl.drag and not self._plain_key():
                return False
            action = look.key_action(name, tl.drag, self.strip.state.get("highlight"), tl.preview)
            if action is None:
                return False
            if override:
                #  Maya's own S is a shortcut: taking the override keeps it from
                #  firing, and the key press then comes here (2026-10-18: «ключи не
                #  ставятся при переносе»)
                event.accept()
                return True
            if action[0] == "stamp":
                tl.flush_live()                 # a step still waiting: the keys where they are drawn
            if action[0] == "stamp" and tl.live:
                #  the keys stand on the target already: their copies stay there
                got = self.strip.call("live_stamp")
                if got:
                    tl.stamped = got
                    self.strip.add_drawn_copies(got, action[1], action[2])
            elif action[0] == "stamp":
                got = self.strip.call("stamp_keys", action[1], action[2], tl.stamped)
                if tl.stamped is None and got:
                    tl.stamped = got            # the keys dragged: the release moves only them
            elif action[0] == "range":
                self.strip.call("key_range", action[1], action[2], name)
            else:
                self.strip.call("run_key_command", name)
            #  the strip's tick reads no keys while the playhead is dragged: the key
            #  shows now, not on the release (2026-10-18)
            self.strip.refresh(keys=True)
            self.strip.timeline.repaint()
            return True

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
            self.stamped = None         # {curve: [times]} once S put copies down in a drag
            self.live = None            # a key drag moving the scene's keys (None: not begun)
            #  the scene's step of a key drag: the drag painted first, then one step to the
            #  NEWEST target on the next event-loop turn (2026-10-20, «ключи сильно
            #  задерживаются за курсором»: the keys were drawn only after each step, and a
            #  step a mouse move could queue behind a slow one)
            self.live_timer = QtCore.QTimer(self)
            self.live_timer.setSingleShot(True)
            self.live_timer.setInterval(0)
            self.live_timer.timeout.connect(self._flush_live)
            self.right_at = None        # ms of a right press whose key menu waits for a second one
            self.menu_wait = QtCore.QTimer(self)    # the key menu, opened once no second press came
            self.menu_wait.setSingleShot(True)
            self.menu_wait.timeout.connect(self._open_menu)
            self._menu_at = None        # (global point, frame) of the waiting menu
            self._static = None         # the still part, drawn once (`_paint`)
            self._static_for = None
            self.static_builds = 0

        def track(self):
            s, pad = self.strip.state, PAD * self.strip.ui
            v0, v1 = self.view or (s["p0"], s["p1"])
            return look.Track(v0, v1, pad, self.width() - pad, cells=True)

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
            changes (`_static_key`); each frame paints that picture and the playhead
            over it (2026-10-16, «фпс проседает когда перетаскиваешь ползунок»: the
            whole timeline drawn element by element was 3-5 ms a step)."""
            t = self.drag[2] if self.drag else self.track()
            w, h = float(self.width()), float(self.height())
            moving = self.moving()
            key = self._static_key(t, w, h, moving)
            if key != self._static_for or self._static is None:
                dpr = max(1.0, float(self.devicePixelRatioF()))
                picture = QtGui.QPixmap(max(1, int(round(w * dpr))), max(1, int(round(h * dpr))))
                picture.setDevicePixelRatio(dpr)
                picture.fill(Qt.transparent)
                sp = QtGui.QPainter(picture)
                sp.setRenderHint(QtGui.QPainter.Antialiasing)
                self._draw_static(sp, t, w, h, moving)
                sp.end()
                self._static, self._static_for = picture, key
                self.static_builds += 1
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.drawPixmap(0, 0, self._static)
            p.setClipRect(QtCore.QRectF(1, 1, w - 2, h - 2))
            p.setPen(Qt.NoPen)
            self._draw_playhead(p, t, w, h)
            p.end()

        def own_moving(self):
            """(selection, target, carried) of this timeline's own key drag, else None."""
            if self.preview and self.drag and len(self.drag) > 3:
                return (tuple(self.drag[3]), tuple(self.preview), look.held(self.stamped))
            return None

        def moving(self):
            """The keys drawn moved: this timeline's own drag, else a drag on the layer
            panel's lanes that holds the active layer - the layer these keys are
            (2026-10-20: «ключи должны перемещаться при переносе и на таймслайдере и на
            выдвижной панели слоев не важно где я их перемещаю»)."""
            own = self.own_moving()
            if own is not None:
                return own
            view = getattr(self.strip.layer_panel, "active_lane_drag", None)
            if view is None:
                return None
            try:
                return view()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                return None

        def _static_key(self, t, w, h, moving):
            """What the cached picture shows; a new one is drawn when this changes."""
            st, s = self.strip, self.strip.state
            return (int(w), int(h), st.ui, round(t.v0, 4), round(t.v1, 4), s["p0"], s["p1"],
                    bool(s.get("sound_shown")), id(st.wave), len(st.wave), tuple(st.marks),
                    self.preview or s.get("highlight"), moving,
                    hash(tuple(st.keys)), hash(tuple(st.breakdowns)), self.devicePixelRatioF(),
                    st.key_hex())

        def _draw_static(self, p, t, w, h, moving):
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
            #  each tick in its frame's cell middle, the number centred over it - as the
            #  caret line above (2026-10-22: on the cell's left edge the last frame's
            #  cell read as one frame past the timeline's end)
            for frame, kind in look.ticks(t, ui):
                c0, c1 = t.cell(frame)
                x = round((c0 + c1) / 2.0)
                tall = tall_of[kind]
                p.setPen(Qt.NoPen)
                p.setBrush(major if kind == "label" else minor)
                p.drawRect(QtCore.QRectF(x, tick_y - tall, tick_w, tall))
                if kind == "label":
                    text = look.frame_text(frame)
                    tw = metrics.horizontalAdvance(text)
                    tx = min(max(x - tw / 2.0, 2 * ui), w - 2 * ui - tw)
                    p.setPen(label_pen)
                    p.drawText(QtCore.QPointF(tx, ry + metrics.ascent()), text)
            # the keys
            p.setPen(Qt.NoPen)
            for frames, hex_ in ((st.keys, st.key_hex()), (st.breakdowns, BREAKDOWN)):
                path = QtGui.QPainterPath()
                #  a copy S put down stands where its key is dragged: under the default
                #  odd-even fill two equal shapes cancel out (2026-10-19)
                path.setFillRule(Qt.WindingFill)
                bars = []                    # Steel keys: each whole-frame key an ingot
                top, bottom = key_span(h, ui)
                for frame in frames:
                    for shown in (look.shown_at(frame, *moving) if moving else (frame,)):
                        if t.v0 - 1 <= shown <= t.v1 + 2:
                            whole = look.on_frame(shown)
                            if st.steel and whole and t.cells:
                                bars.append(QtCore.QRectF(
                                    *look.key_cell(t.x(shown), t.scale, top, bottom, ui)))
                            else:
                                add_key(path, t.x(shown), h, ui, whole, cell=t.scale)
                p.fillPath(path, colour(hex_))
                for rect in bars:
                    ingot(p, rect, hex_, ui)
                p.setPen(Qt.NoPen)
            # the highlight's first and last frame, over the ruler (2026-10-20)
            if sel:
                draw_span_labels(p, t, sel, 1.5 * ui, w, ui, tk)

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
            #  the frame's number rides the caret line above (2026-10-19, B1)

        # the caret line above follows whatever repaints the timeline -------------
        def update(self, *args):
            super(Timeline, self).update(*args)
            caret = getattr(self.strip, "caret", None)
            if caret is not None and caret.stale():
                caret.update()

        def repaint(self, *args):
            super(Timeline, self).repaint(*args)
            caret = getattr(self.strip, "caret", None)
            if caret is not None and caret.stale():
                caret.repaint()

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
            self.flush_live()                   # a drag whose release never came: its last step
            if self.live:
                #  a drag whose release never came (focus taken away): set it down
                self.live = None
                st.call("live_end", tuple(self.preview) if self.preview else None)
                st.refresh(keys=True)
            if event.button() == Qt.RightButton:
                self._right_press(event, self._frame(x, t))
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
                st.lanes_unhighlight()
                self.update()
                return
            part = look.highlight_hit(t, x, s.get("highlight"), st.ui)
            if part:
                self.drag = (part, self._grip(part, x, t), t, tuple(s["highlight"]))
                self.stamped, self.live = None, None
                self.preview = tuple(s["highlight"])
                return
            key = self._key_under(x, t)
            if key is not None and self._frame(x, t) != s["now"]:      # the playhead's own cell scrubs
                #  a key pressed: dragged past Qt's start distance it moves on its own,
                #  no highlight needed; let go where it was, it is a click on the time
                #  (2026-10-18: «перетаскивать ключи без обязательного выделения»)
                self.drag = ("kpend", self._frame(x, t), t, x, key)
                return
            self._press_time(x, t)

        def _press_time(self, x, t):
            st, s = self.strip, self.strip.state
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
            if kind == "kpend":
                if abs(x - self.drag[3]) < QtWidgets.QApplication.startDragDistance():
                    return
                frame = int(math.floor(self.drag[4] + 1e-6))
                self.drag = ("hmove", start, t, (frame, frame), "loose")
                self.stamped, self.live = None, None
                self.preview = (frame, frame)
                kind = "hmove"
            if kind in ("now", "mid"):
                self._scrub(x, update=(kind == "now"))
            elif kind == "hl":
                s["highlight"] = look.highlight(start, self._frame(x, t))
                self.update()
            else:
                target = look.key_drag(kind, self.drag[3], start, self._grip(kind, x, t))
                if target != self.preview:
                    self.preview = target
                    self.repaint()                  # the keys under the cursor at once
                    self.strip.lanes_follow()       # and on the active layer's lane
                    if not self.live_timer.isActive():
                        self.live_timer.start()     # the scene follows on the next turn, newest only

        def _flush_live(self):
            """The scene's keys to the NEWEST target of the drag: every move handled
            since the last step costs nothing, one step for all of them."""
            if not self.drag or self.drag[0] not in ("hmove", "h0", "h1") or self.preview is None:
                return
            self._live_to(self.preview)

        def flush_live(self):
            """A step still waiting, made now (S in the drag: the copies where the keys are drawn)."""
            if self.live_timer.isActive():
                self.live_timer.stop()
                self._flush_live()

        def live_waiting(self):
            return self.live_timer.isActive()

        def _live_to(self, target):
            """The scene's keys follow the drag, as under Maya's own slider (2026-10-19:
            «во время переноса анимация во вьюпорте не обновляется»). The strip keeps
            drawing the keys it read before the drag; it reads them again on the release."""
            st = self.strip
            if self.live is None:
                self.live = bool(st.call("live_begin", tuple(self.drag[3])))
            if self.live:
                st.call("live_to", tuple(target))

        def mouseReleaseEvent(self, event):
            #  a step still waiting is not made: the release sets the keys down on the
            #  preview itself (live_end, or move_keys when no step was made)
            self.live_timer.stop()
            if not self.drag:
                return
            kind = self.drag[0]
            st, s = self.strip, self.strip.state
            if kind == "kpend":
                #  a key clicked, not dragged: the time goes there, as on the track
                self._press_time(self.drag[3], self.drag[2])
                kind = "now"
            if kind == "now":
                st.call("end_scrub")
            elif kind == "mid":
                st.refresh()
            elif kind == "hl":
                st.call("set_highlight", s["highlight"])
            elif kind in ("hmove", "h0", "h1"):
                selection, target = self.drag[3], self.preview
                if self.live:
                    self.live = None
                    st.call("live_end", tuple(target or selection))
                    if target and target != selection:
                        loose = len(self.drag) > 4 and self.drag[4] == "loose"
                        s["highlight"] = None if loose else target
                        st.call("set_highlight", s["highlight"])
                    self.drag, self.preview = None, None
                    st.refresh(keys=True)
                elif target and target != selection:
                    if self.stamped:
                        st.call("move_keys", selection, target, self.stamped)
                    else:
                        st.call("move_keys", selection, target)
                    loose = len(self.drag) > 4 and self.drag[4] == "loose"
                    s["highlight"] = None if loose else target
                    st.call("set_highlight", s["highlight"])
                    self.drag, self.preview = None, None
                    st.refresh(keys=True)
            self.drag = None
            self.preview = None
            self.update()

        def mouseDoubleClickEvent(self, event):
            """A double click of either button highlights every key (Qt sends the
            second press as this event; 2026-10-19). With no keys, a left double
            frames the playback range again after a zoom, as it used to."""
            if event.button() == Qt.RightButton:
                self._right_press(event, self._frame(self._x(event)))
                return
            if event.button() == Qt.LeftButton:
                if not self.highlight_all() and self.view is not None:
                    self.strip.frame_playback()

        # the right button: the key menu, or every key on a double --------------
        def double_window(self):
            return min(QtWidgets.QApplication.doubleClickInterval(), look.RIGHT_DOUBLE_MS)

        def _right_press(self, event, frame):
            """A right press waits `double_window` ms before opening the key menu: a
            second one in that time highlights every key instead (2026-10-19)."""
            now = time.perf_counter() * 1000.0
            if look.right_double(self.right_at, now, self.double_window()):
                self.right_at, self._menu_at = None, None
                self.menu_wait.stop()
                self.highlight_all()
                return
            point = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self.right_at, self._menu_at = now, (QtCore.QPoint(point), frame)
            self.menu_wait.start(self.double_window())

        def _open_menu(self):
            waiting, self._menu_at, self.right_at = self._menu_at, None, None
            if waiting is not None:
                self.strip.key_menu(waiting[0], waiting[1])

        def highlight_all(self):
            """Every key the strip shows highlighted, first to last - then the blue
            block moves or scales them all, the key menu acts on them all."""
            st, s = self.strip, self.strip.state
            if st.keys_dirty:
                st.refresh()
            sel = look.all_keys(st.keys, st.breakdowns)
            if sel is None:
                return False
            s["highlight"] = sel
            st.call("set_highlight", sel)
            st.lanes_unhighlight()
            self.update()
            return True

        def wheelEvent(self, event):
            #  the wheel does not zoom the timeline (2026-10-19)
            event.ignore()

        def _aim(self, x):
            """The cursor: an open hand over what a press would drag."""
            t, ui = self.track(), self.strip.ui
            part = look.highlight_hit(t, x, self.strip.state.get("highlight"), ui)
            grab = part == "hmove" or (not part and self._key_under(x, t) is not None)
            self.setCursor(Qt.OpenHandCursor if grab else Qt.SizeHorCursor)

        def _key_under(self, x, t):
            """The key whose cell the press is in (a key between frames: within half a
            cell, at least 3 px, of its line); None off every key."""
            near = max(3 * self.strip.ui, t.scale / 2.0)
            best = None
            for k in self.strip.keys + self.strip.breakdowns:
                d = abs(look.key_centre(t, k) - x)
                if d <= near:
                    best, near = k, d
            return best

        def _scrub(self, x, update=True):
            """The playhead drawn on the new frame at once, then Maya sent there:
            `currentTime` evaluates the scene before it returns, and a paint left
            to the event loop waited for it - the playhead jumped frames."""
            t = self.drag[2] if self.drag else self.track()
            self.strip.scrub_to(self._frame(x, t), update)

    # -- the caret line over the timeline's numbers --------------------------------

    class CaretLine(QtWidgets.QWidget):
        """A hairline with a division on every frame above the timeline, and a caret
        - a flag with the current frame - riding it; a press anywhere on it sends the
        time there, a drag scrubs (2026-10-19, mockup B1: «линия с делениями и
        кареткой ... двигать таймслайдер за каретку»). Its x is the timeline's: the
        same column, the same track."""

        def __init__(self, strip):
            super(CaretLine, self).__init__(strip)
            self.strip = strip
            self.setObjectName("skeldarTimeBarCaret")
            self.setFixedHeight(int(CARET_H * strip.ui))
            self.setCursor(Qt.SizeHorCursor)
            self.setMouseTracking(True)
            self.aim = False            # the mouse over the flag

        def _dragging(self):
            drag = self.strip.timeline.drag
            return bool(drag and drag[0] in ("now", "mid") and getattr(self, "_own", False))

        def _x_on_timeline(self, x):
            tl = self.strip.timeline
            g = self.mapToGlobal(QtCore.QPoint(int(round(x)), 0))
            return float(tl.mapFromGlobal(g).x()) + (x - round(x))

        def flag_rect(self, t=None):
            """The caret's flag, in this widget (clamped inside it)."""
            st, ui = self.strip, self.strip.ui
            t = t or st.timeline.track()
            c0, c1 = t.cell(st.state["now"])
            x = (c0 + c1) / 2.0 - self._x_on_timeline(0.0)
            metrics = QtGui.QFontMetricsF(self._font())
            tw = max(CARET_MIN_W * ui, metrics.horizontalAdvance(look.frame_text(st.state["now"])) + 8 * ui)
            th = CARET_FLAG_H * ui
            fx = min(max(x - tw / 2.0, 1.0), self.width() - tw - 1.0)
            line = self.height() - 1.5 * ui
            return QtCore.QRectF(fx, line - 1.5 * ui - th, tw, th), x, line

        def _font(self):
            font = QtGui.QFont("Consolas")
            font.setBold(True)
            font.setPixelSize(max(7, int(round(9 * self.strip.ui))))
            return font

        # painting -------------------------------------------------------------
        def _lit(self):
            """The flag under the mouse or held: its face a little lighter, nothing more."""
            return self.aim or self._dragging()

        def _shown(self):
            """What the line's picture reads: the time, the track, the flag's face."""
            st = self.strip
            t = st.timeline.track()
            drag = st.timeline.drag
            return (st.state.get("now"), t.v0, t.v1, t.left, t.right, self.width(), self.height(),
                    self._lit(), bool(drag and drag[0] == "mid"), st.ui)

        def stale(self):
            """The timeline repainting asks the line too only when the line would look
            different (2026-10-27, half a millisecond a paint)."""
            try:
                return self._shown() != getattr(self, "_painted", None)
            except Exception:                                # noqa: BLE001
                return True

        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            st = self.strip
            tk, ui = st.tokens, st.ui
            try:
                self._painted = self._shown()
            except Exception:                                # noqa: BLE001
                self._painted = None
            t = st.timeline.track()
            w = float(self.width())
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            off = self._x_on_timeline(0.0)
            flag, x, line = self.flag_rect(t)
            # the hairline, then a division on every frame's middle
            p.setBrush(colour(tk["line"]))
            p.drawRect(QtCore.QRectF(t.left - off, line, t.right - t.left, max(1.0, ui)))
            tall_of = {"label": 5.0 * ui, "mid": 3.5 * ui, "tick": 2.0 * ui}
            tick_w = max(1.0, ui * 0.75)
            for frame, kind in look.ticks(t, ui):
                c0, c1 = t.cell(frame)
                cx = round((c0 + c1) / 2.0 - off)
                if cx < 0 or cx > w:
                    continue
                p.setBrush(colour(tk["muted"] if kind == "label" else tk["line"]))
                tall = tall_of[kind]
                p.drawRect(QtCore.QRectF(cx, line - tall, tick_w, tall))
            # the caret: a flag with the frame, a stem down to the line
            drag = st.timeline.drag
            head = colour(HIGHLIGHT if drag and drag[0] == "mid" else
                          (tk["accent_text"] if self._lit() else tk["accent"]))
            p.setPen(Qt.NoPen)
            p.setBrush(head)
            p.drawRoundedRect(flag, 3 * ui, 3 * ui)
            stem = 1.5 * ui
            p.drawRect(QtCore.QRectF(x - stem / 2.0, flag.bottom() - 0.5, stem, line - flag.bottom() + 1.5 * ui))
            p.setFont(self._font())
            p.setPen(colour(tk["on_accent"]))
            p.drawText(flag, Qt.AlignCenter, look.frame_text(st.state["now"]))
            p.end()

        # input ----------------------------------------------------------------
        def _x(self, event):
            return event.position().x() if hasattr(event, "position") else event.x()

        def mousePressEvent(self, event):
            tl = self.strip.timeline
            x = self._x_on_timeline(self._x(event))
            if event.button() == Qt.LeftButton:
                self._own = True
                tl._press_time(x, tl.track())
            elif event.button() == Qt.MiddleButton:
                self._own = True
                tl.drag = ("mid", None, tl.track())
                tl._scrub(x, update=False)
            else:
                return
            self.setCursor(Qt.ClosedHandCursor)
            self.update()

        def mouseMoveEvent(self, event):
            tl = self.strip.timeline
            if getattr(self, "_own", False) and tl.drag and tl.drag[0] in ("now", "mid"):
                tl._scrub(self._x_on_timeline(self._x(event)), update=(tl.drag[0] == "now"))
                return
            over = self.flag_rect()[0].adjusted(-3, -3, 3, 3).contains(QtCore.QPointF(self._x(event), self.height() / 2.0))
            self.setCursor(Qt.OpenHandCursor if over else Qt.SizeHorCursor)
            if over != self.aim:
                self.aim = over
                self.update()

        def mouseReleaseEvent(self, event):
            tl, st = self.strip.timeline, self.strip
            if not getattr(self, "_own", False):
                return
            self._own = False
            kind = tl.drag[0] if tl.drag else None
            tl.drag = None
            if kind == "now":
                st.call("end_scrub")
            elif kind == "mid":
                st.refresh()
            self.setCursor(Qt.OpenHandCursor if self.aim else Qt.SizeHorCursor)
            tl.update()
            self.update()

        def leaveEvent(self, event):
            if self.aim:
                self.aim = False
                self.update()

    # -- the strip -------------------------------------------------------------------

    class Strip(QtWidgets.QWidget):

        def __init__(self, link, ui=1.0, tokens=None, parent=None):
            super(Strip, self).__init__(parent)
            self.setObjectName(ROOT_NAME)
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.link, self.ui = link, float(ui)
            self.tokens = tokens or _tokens()
            self.steel = steel_on()          # ⋮ -> Time bar ▸ Steel keys (2026-10-20)
            self.state = {"now": 0.0, "a0": 0.0, "a1": 120.0, "p0": 0.0, "p1": 120.0,
                          "unit": "ntsc", "auto": False, "playing": False, "highlight": None,
                          "loop": "continuous", "speed": 1.0, "cache": False, "sound": "",
                          "sound_shown": False, "character": ""}
            self.keys, self.breakdowns, self.marks, self.wave = [], [], [], []
            self._wave_key = None
            self.keys_dirty = True
            self.setStyleSheet(stylesheet(self.tokens, self.ui))
            ui = self.ui
            column = QtWidgets.QVBoxLayout(self)
            column.setContentsMargins(int(6 * ui), int(1 * ui), int(6 * ui), int(3 * ui))
            column.setSpacing(0)
            #  the skill bar (2026-10-19): the page row on top, F1 the two time rows (in one
            #  box), F2-F12 a page of skill cells in their place
            self.skills = _skills_of(link)
            self.lit_aim = None
            from maya_skillbar import grid as skillgrid
            PageTabs, SkillGrid = skillgrid.classes()
            self.tabs = PageTabs(self)
            column.addWidget(self.tabs)
            self.time_box = QtWidgets.QWidget(self)
            self.time_box.setObjectName("skeldarTimeBarTimeBox")
            box = QtWidgets.QVBoxLayout(self.time_box)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(0)
            column.addWidget(self.time_box)
            self.skill_grid = SkillGrid(self)
            column.addWidget(self.skill_grid)
            top, bottom = QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout()
            for row in (top, bottom):
                row.setSpacing(int(2 * ui))
                box.addLayout(row)
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
            self.character = Pill(self, text="No Character Set", tip="Character set", style="chip")
            self.layer = Pill(self, text="BaseAnimation", tip="The animation layer keys go to", style="chip")
            self.fps = Pill(self, text="30 fps", tip="Frame rate", style="chip")
            self.character.clicked.connect(lambda *_a: self._character_menu())
            self.layer.clicked.connect(lambda *_a: self.toggle_layers())
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
            #  the layer panel's pill (2026-10-18), in place of the bookmark pills
            self.layers_btn = Pill(self, "layers", tip="Animation and display layers", toggle=True)
            self.layers_btn.clicked.connect(lambda *_a: self.toggle_layers())
            self.layer_panel = None
            self.loop.clicked.connect(lambda *_a: self._do("cycle_loop"))
            self.cache.clicked.connect(lambda *_a: self._do("toggle_cache"))
            self.speed.clicked.connect(lambda *_a: self._speed_menu())
            self.sound.clicked.connect(lambda *_a: self._sound_menu())
            self.auto.clicked.connect(lambda *_a: self._do("toggle_auto"))
            self.prefs.clicked.connect(lambda *_a: self.call("preferences"))
            #  the 📌 of the bottom edge (2026-10-16): only shown there
            self.edge = None
            self.pin = Pill(self, "pin", tip="Keep the time bar out", toggle=True)
            self.pin.clicked.connect(lambda checked=False: self.edge and getattr(
                self.edge, "pin_pressed", self.edge.set_pinned)(self.pin.isChecked()))
            self.pin.setVisible(False)
            for b in (self.loop, self.cache, self.speed, self.sound, self.auto):
                top.addWidget(b)
            top.addWidget(self._sep())
            for b in (self.layers_btn, self.prefs, self.pin):
                top.addWidget(b)
            # time row
            self.timeline = Timeline(self)
            self.caret = CaretLine(self)
            stack = QtWidgets.QVBoxLayout()
            stack.setContentsMargins(0, 0, 0, 0)
            stack.setSpacing(0)
            stack.addWidget(self.caret)
            stack.addWidget(self.timeline)
            bottom.addLayout(stack, 1)
            bottom.addSpacing(int(4 * ui))
            self.field = QtWidgets.QLineEdit(self)
            self.field.setObjectName("skeldarTimeBarFrame")
            self.field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.field.setFixedSize(int(58 * ui), int(24 * ui))
            self.field.setToolTip("Current frame")
            self.field.setFocusPolicy(Qt.ClickFocus)
            self.field.returnPressed.connect(self._typed)
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
            self._apply_page()
            # the timer
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(TIMER_MS)
            self.timer.timeout.connect(self.tick)
            # S on the strip: during a drag, and over a highlight (2026-10-18)
            self.drag_keys = DragKeys(self)
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.installEventFilter(self.drag_keys)
            self.refresh(keys=True, force=True)     # read once even if Maya is playing
            self.timer.start()

        # building -----------------------------------------------------------
        def set_edge(self, controller):
            """Standing in the bottom edge's host: the 📌 shows."""
            self.edge = controller
            self.pin.setVisible(controller is not None)

        def _sep(self):
            sep = QtWidgets.QFrame(self)
            sep.setObjectName("skeldarTimeBarSep")
            sep.setFixedSize(max(1, int(self.ui)), int(20 * self.ui))
            return sep

        def _field(self, tip, on_value):
            field = QtWidgets.QLineEdit(self)
            field.setObjectName("skeldarTimeBarField")
            field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            field.setFixedSize(int(52 * self.ui), int(24 * self.ui))
            field.setToolTip(tip)
            field.setFocusPolicy(Qt.ClickFocus)

            def done():
                try:
                    on_value(float(field.text()))
                except ValueError:
                    pass
                field.clearFocus()
                self.refresh()
            field.returnPressed.connect(done)
            return field

        def key_hex(self):
            """The keys' colour: steel with ⋮ -> Time bar ▸ Steel keys, else the accent."""
            return look.STEEL if self.steel else self.tokens["accent"]

        def set_steel(self, on):
            """Steel keys on or off: the keys repaint at once."""
            self.steel = bool(on)
            self.timeline.update()
            lanes = getattr(self.layer_panel, "lanes", None)
            if lanes is not None:
                lanes.update()

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

        def refresh(self, keys=False, force=False, idle=False):
            """Everything read again and painted. `idle` (the 250 ms tick): painted only
            when what the strip shows changed - four repaints a second of an unchanged
            strip cost ~5 ms a second for nothing (2026-10-27)."""
            light = self.call("light")
            if light:
                self.state.update(light)
            extra = self.call("extra")
            if extra:
                self.state.update(extra)
            if keys:
                self.keys_dirty = True
            read_keys = bool(self.keys_dirty and (force or not self.state.get("playing")))
            if (getattr(self.timeline, "live", None) or self.timeline.live_waiting()
                    or self._lanes_moving()):
                read_keys = False       # a live key drag: drawn from the keys read before it
            if read_keys:
                found = self.call("keys")
                if found is not None:
                    self.keys, self.breakdowns = list(found[0]), list(found[1])
                    self.keys_dirty = False
                self.marks = self.call("bookmarks") or []
            self._sound()
            if idle and not read_keys:
                shown = self._shown()
                if shown == getattr(self, "_shown_last", None):
                    if self.layer_panel is not None and self.layer_panel.is_open():
                        self.layer_panel.refresh(keys=False, force=force)
                    return
            self._paint_widgets()
            self._shown_last = self._shown()
            self.timeline.update()
            self.range.update()
            #  the open layer panel reads with the strip (2026-10-18 final review): the
            #  jobs and the tick reach it; its lanes' keys only when the strip read keys
            if self.layer_panel is not None and self.layer_panel.is_open():
                self.layer_panel.refresh(keys=read_keys, force=force)

        def add_drawn_copies(self, stamped, selection, target):
            """The copies S put down in a live drag, drawn where they went down: the
            scene holds them, but the strip reads keys again only on the release."""
            keys, bds = set(self.keys), set(self.breakdowns)
            for rec in stamped.values():
                for t, data in rec.get("keys", ()):
                    nt = round(look.mapped(t, selection, target), 4)
                    if round(nt, 4) in rec.get("stamped", ()):
                        (bds if data.get("breakdown") else keys).add(nt)
            self.keys, self.breakdowns = sorted(keys), sorted(bds)

        def scrub_to(self, frame, update=True):
            """One playhead for the timeline and the layer lanes, whichever is dragged
            (2026-10-20: «Каретка должна бегать одинаково»): drawn on the new frame at
            once on both, then Maya sent there - `currentTime` evaluates the scene before
            it returns, and a paint left to the event loop waited for it."""
            t0 = time.perf_counter()
            s, tl = self.state, self.timeline
            if frame == s["now"]:
                return
            s["now"] = frame
            self.show_now()
            tl.repaint()
            self.field.repaint()
            self.lanes_follow()
            t1 = time.perf_counter()
            self.call("set_time" if update else "scrub_only", frame)
            meter = _state().get("meter")
            if meter is not None:          # the scrub meter: our work, then Maya's frame change
                meter["ours"].append((t1 - t0) * 1000.0)
                meter["mayas"].append((time.perf_counter() - t1) * 1000.0)

        def lanes_follow(self):
            """The layer lanes repainted now: the playhead or a timeline key drag moved."""
            on_time = getattr(self.layer_panel, "on_time", None)
            if on_time is not None:
                try:
                    on_time()
                except Exception:                            # noqa: BLE001
                    print(traceback.format_exc())

        def lanes_unhighlight(self):
            """A highlight made on the timeline takes the layer lanes' own away, or S
            keyed the lanes' block instead of the timeline's (2026-10-20: «если мы
            выделяем что-то на тайм слайдере то выделение на выдвижной панели слоев не
            должно работать»)."""
            panel = self.layer_panel
            if panel is None or not getattr(panel, "lane_sel", None):
                return
            try:
                panel.lane_clear()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def _lanes_moving(self):
            """A key drag on the layer panel's lanes stands: the strip reads no keys."""
            moving = getattr(self.layer_panel, "lanes_moving", None)
            return bool(moving()) if moving is not None else False

        def selection_changed(self):
            """Another object's keys: read again."""
            self.refresh(True)

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
                self.state["now"] = now
                self.show_now()
                #  painted now, inside Maya's frame: Maya's playback does not let
                #  the event loop run between frames, so `update()` drew one frame
                #  in several (2026-10-16)
                self.timeline.repaint()
                self.field.repaint()
                if self.layer_panel is not None:
                    self.layer_panel.on_time()

        def tick(self):
            try:
                if not self.timeline.drag and not self.range.drag:
                    self.refresh(idle=True)
            except Exception:                                # noqa: BLE001 - four times a second
                if not getattr(self, "_tick_failed", False):
                    print(traceback.format_exc())
                self._tick_failed = True

        def show_now(self):
            if not self.field.hasFocus():
                self.field.setText(look.frame_text(self.state["now"]))

        def _shown(self):
            """What the strip's painting reads, to tell an idle refresh that changed
            nothing (`refresh(idle=True)`)."""
            return (tuple(sorted((k, repr(v)) for k, v in self.state.items())),
                    tuple(self.keys), tuple(self.breakdowns), repr(self.marks),
                    repr(self.call("layer_state")), self.steel,
                    bool(self.layer_panel and self.layer_panel.is_open()))

        def _paint_widgets(self):
            s = self.state
            self.show_now()
            for field, key in ((self.anim_start, "a0"), (self.play_start, "p0"),
                               (self.play_end, "p1"), (self.anim_end, "a1")):
                if not field.hasFocus():
                    field.setText(look.frame_text(s[key]))
            playing = bool(s["playing"])
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
            layer, count = self.call("layer_state") or ("", 0)
            self.layer.set_label((layer + u" ▾") if layer else "No layers")
            self.layers_btn.set_badge(count if count else "")
            self.layers_btn.setChecked(bool(self.layer_panel and self.layer_panel.is_open()))

        # presses ---------------------------------------------------------------
        def _typed(self):
            try:
                frame = float(self.field.text())
            except ValueError:
                self.show_now()
                return
            self.call("set_time", frame)
            self.field.clearFocus()
            self.refresh()

        def _typed_range(self, which, value):
            s = self.state
            a0, a1, p0, p1 = look.dragged(which, value, s["a0"], s["a1"], s["p0"], s["p1"])
            self.call("set_ranges", a0, a1, p0, p1)

        def _go(self, where):
            s, n = self.state, int(round(self.state["now"]))
            frame = {"start": s["p0"], "end": s["p1"], "pfrm": max(s["p0"], n - 1),
                     "nfrm": min(s["p1"], n + 1)}[where]
            self.call("set_time", frame)

        def _step(self, forward):
            self.call("step_key", forward, self.keys + self.breakdowns)
            self.refresh()

        def toggle_layers(self):
            """The layers pill or the chip: the layer panel opened or closed out of the pill."""
            from . import layerpanel
            if self.layer_panel is None:
                parent = None
                try:
                    from . import edge as _edge
                    parent = _edge.main_window()
                except Exception:                            # noqa: BLE001
                    parent = None
                self.layer_panel = layerpanel.Panel(self, self.link.layer_link(), self.ui, self.tokens,
                                                    parent)
            c = self.layers_btn.mapToGlobal(self.layers_btn.rect().center())
            self.layer_panel.toggle((c.x(), c.y()))
            self.layers_btn.setChecked(self.layer_panel.is_open())

        # the skill bar (2026-10-19) ---------------------------------------------------
        def time_height(self):
            """The two time rows' height: a skill page is as tall (F1 and F2 do not jump)."""
            hint = self.time_box.sizeHint().height()
            return float(max(hint, int(56 * self.ui)))

        def page(self):
            return self.skills.page()

        def _apply_page(self):
            n = self.skills.page()
            time = not skill_look().is_skill_page(n)
            self.time_box.setVisible(time)
            self.skill_grid.setVisible(not time)
            if not time:
                self.skill_grid.setFixedHeight(self.skill_grid.wanted_height())
            self.tabs.update()
            self.skill_grid.update()
            self.layout().activate()            # the size hint the host reads is the new page's
            self.updateGeometry()
            if hasattr(self.link, "page_height") or isinstance(self.link, Link):
                self.call("page_height", self)

        def show_page(self, n, origin=None):
            """Page n (1 the Time Bar, 2-12 skills): shown at once, the host sized to it.
            `origin` (where it was asked from) is taken and not used: nothing moves."""
            look_ = skill_look()
            if n != look_.TIME_PAGE and not look_.is_skill_page(n):
                return
            self.skills.set_page(n)
            self._apply_page()
            if n == look_.TIME_PAGE:
                self.refresh(keys=True)

        def skill_aim(self, gx, gy):
            """("cell", n, r, c) / ("tab", n) / None under the global point (gx, gy)."""
            point = QtCore.QPoint(int(gx), int(gy))
            if self.tabs.isVisible():
                local = self.tabs.mapFromGlobal(point)
                if self.tabs.rect().contains(local):
                    n = self.tabs.page_at(local.x())
                    return ("tab", n) if n and skill_look().is_skill_page(n) else None
            grid = self.skill_grid
            if grid.isVisible():
                local = grid.mapFromGlobal(point)
                if grid.rect().contains(local):
                    cell = grid.cell_at(local.x(), local.y())
                    return ("cell", self.skills.page(), cell[0], cell[1]) if cell else None
            return None

        def light_aim(self, aim):
            if aim != self.lit_aim:
                self.lit_aim = aim
                self.tabs.drop_on = aim[1] if aim and aim[0] == "tab" else None
                self.tabs.update()
                self.skill_grid.update()

        def _cols(self):
            return max(1, self.skill_grid.cols())

        def place_skill(self, aim, item):
            """`item` onto the aim: a cell (what was there replaced), or a tab (its first free
            cell). Returns the line said."""
            look_ = skill_look()
            data = self.skills.data()
            if not aim or not look_.valid_item(item):
                return ""
            label = self.skills.label(item)
            if aim[0] == "cell":
                data = look_.put(data, aim[1], aim[2], aim[3], item)
                place = (aim[2], aim[3])
                n = aim[1]
            else:
                n = aim[1]
                data, place = look_.put_on_page(data, n, item, self._cols())
                if place is None:
                    message = "%s is full - nothing put there" % look_.fkey(n)
                    self.skills.say(message)
                    return message
            self.skills.set_data(data)
            message = "%s on %s" % (label, look_.cell_caption(n, place[0], place[1]))
            self.tabs.update()
            self.skill_grid.update()
            self.skills.say(message)
            return message

        def move_skill(self, source, aim):
            """A cell dragged: onto a cell swaps the two, onto a tab goes to that page's first
            free cell."""
            look_ = skill_look()
            data = self.skills.data()
            item = look_.item_at(data, *source)
            if not item or not aim:
                return ""
            if aim[0] == "cell":
                if tuple(aim[1:]) == tuple(source):
                    return ""
                self.skills.set_data(look_.swap(data, source, aim[1:]))
            else:
                if aim[1] == source[0]:
                    return ""
                moved, place = look_.put_on_page(look_.take(data, *source), aim[1], item, self._cols())
                if place is None:
                    message = "%s is full" % look_.fkey(aim[1])
                    self.skills.say(message)
                    return message
                self.skills.set_data(moved)
            self.tabs.update()
            self.skill_grid.update()
            return "moved"

        def cell_rows(self, n, r, c):
            look_ = skill_look()
            item = look_.item_at(self.skills.data(), n, r, c)
            aim = ("cell", n, r, c)
            point = self.skill_grid.cell_centre(r, c)
            rows = [(look_.cell_caption(n, r, c), None)]
            if item:
                rows += [("Run  " + self.skills.label(item), lambda: self.skill_grid.run_cell((r, c))),
                         ("Rename...", lambda: self._rename_cell(n, r, c)),
                         ("Change skill...", lambda: self.skills.open_library(aim, point)),
                         ("Clear", lambda: self._clear_cell(n, r, c))]
            else:
                rows += [("Skill library...", lambda: self.skills.open_library(aim, point)),
                         ("Script from the Script Editor", lambda: self._script_cell(aim))]
            return rows + [None,
                           ("Skill library...", lambda: self.skills.open_library(None, point))]

        def page_rows(self, n):
            look_ = skill_look()
            point = self.tabs.tab_centre(n) or (0, 0)
            rows = [("Show %s" % look_.fkey(n), lambda: self.show_page(n, point))]
            if look_.is_skill_page(n):
                rows += [("Rename page...", lambda: self._rename_page(n)),
                         ("Clear page", (lambda: self._clear_page(n))
                          if look_.filled(self.skills.data(), n) else None)]
            return rows + [None,
                           ("Skill library...", lambda: self.skills.open_library(None, point))]

        def cell_menu(self, n, r, c, where):
            self._menu(where, self.cell_rows(n, r, c))

        def page_menu(self, n, where):
            self._menu(where, self.page_rows(n))

        def _ask(self, title, label, text):
            value, ok = QtWidgets.QInputDialog.getText(self, title, label, QtWidgets.QLineEdit.Normal, text)
            return value if ok else None

        def _rename_cell(self, n, r, c):
            look_ = skill_look()
            item = look_.item_at(self.skills.data(), n, r, c)
            if not item:
                return
            value = self._ask("Rename skill", "Name:", self.skills.label(item))
            if value is None:
                return
            item = dict(item)
            if value.strip():
                item["label"] = value.strip()[:40]
            else:
                item.pop("label", None)
            self.skills.set_data(look_.put(self.skills.data(), n, r, c, item))
            self.skill_grid.update()

        def _clear_cell(self, n, r, c):
            self.skills.set_data(skill_look().take(self.skills.data(), n, r, c))
            self.tabs.update()
            self.skill_grid.update()

        def _script_cell(self, aim):
            item = self.skills.script_editor()
            if item is None:
                self.skills.say("The Script Editor's current tab holds no text")
                return
            self.place_skill(aim, item)

        def _rename_page(self, n):
            look_ = skill_look()
            value = self._ask("Rename page", "%s name:" % look_.fkey(n), look_.page_name(self.skills.data(), n))
            if value is not None:
                self.skills.set_data(look_.rename_page(self.skills.data(), n, value))
                self.tabs.update()

        def _clear_page(self, n):
            self.skills.set_data(skill_look().clear_page(self.skills.data(), n))
            self.tabs.update()
            self.skill_grid.update()

        def strip_rect(self):
            p = self.mapToGlobal(self.rect().topLeft())
            return (p.x(), p.y(), self.width(), self.height())

        def timeline_rect(self):
            t = self.timeline
            p = t.mapToGlobal(t.rect().topLeft())
            return (p.x(), p.y(), t.width(), t.height())

        def top_room(self):
            """From the strip's top to the top of Maya's viewport area (else the screen)."""
            top = None
            try:
                import maya_hubedge
                area = maya_hubedge._viewport_area("right")
                top = area[1] if area else None
            except Exception:                                # noqa: BLE001
                top = None
            if top is None:
                screen = self.screen().availableGeometry() if self.screen() else None
                top = screen.y() if screen is not None else 0
            return self.strip_rect()[1] - top

        def track(self):
            return self.timeline.track()

        def now(self):
            return self.state.get("now", 0.0)

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
                    #  what the row runs is read off exec's answer, never found by its
                    #  wrapper (maya_hubqt.tag_row, 2026-10-28)
                    picked[maya_hubqt.tag_row(row, action)] = action
            return menu, picked

        def _menu(self, where, rows):
            menu, _picked = self.menu_rows(rows)
            point = where if isinstance(where, QtCore.QPoint) else where.mapToGlobal(QtCore.QPoint(0, where.height()))
            action = maya_hubqt.row_value(menu.exec(point))     # before deleteLater
            menu.deleteLater()
            if callable(action):
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
                    ("Highlight all keys (double click)",
                     self.timeline.highlight_all if (self.keys or self.breakdowns) else None),
                    ("Add bookmark", lambda: c("add_bookmark", sel)),
                    ("Playback range = highlight", (lambda: c("playback_from", sel)) if sel else None),
                    ("Frame the playback range", self.frame_playback), None,
                    ("Measure scrubbing (10 s)", lambda: c("measure")),
                    ("Back to Maya's time slider", lambda: c("back_to_maya"))]

        def _fps_menu(self):
            self._menu(self.fps, self.fps_rows())

        def _speed_menu(self):
            self._menu(self.speed, self.speed_rows())

        def _character_menu(self):
            self._menu(self.character, self.character_rows())

        def _sound_menu(self):
            self._menu(self.sound, self.sound_rows())

        def key_menu(self, where, frame):
            """`where`: a global QPoint, or the mouse event the menu opens at."""
            if isinstance(where, QtCore.QPoint):
                point = where
            elif hasattr(where, "globalPosition"):
                point = where.globalPosition().toPoint()
            else:
                point = where.globalPos()
            self._menu(point, self.key_rows(frame))

    global _KIT
    _KIT = types.SimpleNamespace(colour=colour, blend=blend, draw_glyph=draw_glyph,
                                 ingot=ingot, draw_span_labels=draw_span_labels)
    return Strip, Timeline, RangeBlock, Pill


def make(link=None, ui=1.0, tokens=None, parent=None):
    strip_class = classes()[0]
    strip = strip_class(link or Link(), ui, tokens, parent)
    try:
        #  no field holds the keyboard until clicked, no button ever (2026-11-19)
        import maya_hubqt
        maya_hubqt.quiet_focus(strip)
    except Exception:                                        # noqa: BLE001
        pass
    return strip


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
        if widget.layer_panel is not None:
            widget.layer_panel.keys_dirty()


def _command(command, *_args):
    """Every MEL command Maya runs passes here: a setKeyframe, and Maya's own
    Delete (Edit > Delete, the Delete key: a bare `delete;`), which plays the
    delete sound (2026-10-22)."""
    if command.strip().rstrip(";").strip() == "delete":
        #  bare `delete;` on the selection is Maya's own Delete (doDelete runs it,
        #  measured: doDelete itself is not reported); a Python cmds.delete never is
        import maya_hubsound
        maya_hubsound.deleted()
        return
    if not command.startswith("setKeyframe"):
        return
    widget = current()
    if widget is not None and look.set_key_command(command) is not None:
        widget.keys_dirty = True
    edge = _state().get("edge")
    if edge is not None and look.set_key_command(command) is not None:
        #  a key set (the S hotkey, the Channel Box): the bar out, its wait for the
        #  hide begun again (2026-10-17, «если я ставлю ключик хоткеем то панель тайм
        #  слайдера должна появиться а время его ожидания откатиться») - when the event
        #  loop next turns, not inside Maya's command
        try:
            import maya_hubqt
            q = maya_hubqt.qt()
            q.QtCore.QTimer.singleShot(0, lambda: _key_set_on(edge))
        except Exception:                                    # noqa: BLE001
            pass


def _key_set_on(edge):
    try:
        if edge.alive():
            edge.key_set()
    except Exception:                                        # noqa: BLE001
        pass


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


#  (event, the strip's method, its arguments); refresh's are (keys, force). A scene
#  opened reads everything again, forced, so the layer panel never writes to a
#  closed scene's nodes (2026-10-18 final review)
JOB_EVENTS = (("playbackRangeChanged", "refresh", ()),
              ("SelectionChanged", "selection_changed", ()),
              ("animLayerRefresh", "refresh", (True,)),
              ("Undo", "refresh", (True,)),
              ("Redo", "refresh", (True,)),
              ("SceneOpened", "refresh", (True, True)),
              ("NewSceneOpened", "refresh", (True, True)),
              ("displayLayerChange", "refresh", ()),
              ("displayLayerManagerChange", "refresh", ()),
              ("displayLayerAdded", "refresh", ()),
              ("displayLayerDeleted", "refresh", ()),
              ("displayLayerVisibilityChanged", "refresh", ()))


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
    for event, method, args in JOB_EVENTS:
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
    try:
        import maya.api.OpenMaya as om
        callbacks.append(om.MCommandMessage.addCommandCallback(_command))
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
    try:
        from . import layerpanel
        layerpanel.destroy_all()
    except Exception:                                        # noqa: BLE001
        pass
    for old in host.findChildren(q.QtWidgets.QWidget, ROOT_NAME):
        old.setParent(None)
        old.deleteLater()
    ui = cmds.mayaDpiSetting(q=True, realScaleValue=True) or 1.0
    widget = make(Link(), ui)
    host.layout().addWidget(widget)
    _state()["bar"] = widget
    _state()["host"] = "docked"
    start_jobs()
    widget._apply_page()                # the docked control as tall as the page shown
    return widget
