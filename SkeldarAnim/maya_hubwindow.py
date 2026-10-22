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

2026-10-22 (spec: docs/superpowers/specs/2026-10-22-window-look-b-spring-design.md): look B
is the Time Bar's now - one dark surface (`content_face` "panel"), a hairline under the title,
the fields recessed (`recessed_sheet`) - and the motion is the spring out of the point
(maya_hubburst.MOTION): the one picture drawn scaled, its clock starting at the picture.

2026-10-22, later (spec: docs/superpowers/specs/2026-10-22-window-look-d-wells-design.md): the
frame is look D, an instrument like the Time Bar's strip - lighter at the top with a light line
inside the top edge, a dark outline, a grip, the group's glowing dot and the name in the title,
the light (accent ring and glow) on the edge with no face change - and inside it look B's
wells: each group of controls (those between two headings) on a recessed `track` plate, the
fields standing on `panel` in them.

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

#  Look D's frame (2026-10-22, the animator's pick of four: «как вариант B ... мне нравится
#  как ты сделал D с объемом»): an instrument like the Time Bar's strip. Logical px.
RADIUS = 10
EDGE = "#101113"          # the frame's outline, darker than the panel
BEVEL_TOP = "#26282c"     # the face at the top, fading to `panel` by BEVEL_FADE
BEVEL_FADE = 46
BEVEL_ALPHA = 0.07        # the light line inside the top edge
GRIP_W, GRIP_H, GRIP_Y, GRIP_ALPHA = 34, 3, 5, 0.6
#  Look B's wells (the 2026-10-22 mockup): each group of controls on a recessed plate
WELL_RADIUS = 6
WELL_PAD = 4              # above the first and below the last control of a group
WELL_GAP = 5              # kept clear above the next heading
WELL_MARGIN = 5           # the wells' sides kept this far in from the frame's
HEAD_ROLES = ("heading", "subhead")


def wells(heads, items, left, right, pad, gap):
    """The wells of a column of controls, pure. `heads`: (top, bottom) of each heading;
    `items`: (top, bottom) or (top, bottom, left, right) of each control; all in one space.
    A group is the controls whose middle falls between two headings (before the first, after
    the last); its well is the group's own height plus `pad`, never over its headings (it ends
    `gap` above the next one). Every well is as wide as all the controls together plus `pad`
    each side, kept within `left`..`right` (so they line up). Groups with no control get no
    well. Returns (x0, y0, x1, y1)."""
    heads = sorted(heads)
    sides = [it for it in items if len(it) == 4]
    if sides:
        left = max(left, min(it[2] for it in sides) - pad)
        right = min(right, max(it[3] for it in sides) + pad)
    bounds = [float("-inf")] + [h[0] for h in heads] + [float("inf")]
    floors = [float("-inf")] + [h[1] for h in heads]
    out = []
    for i in range(len(heads) + 1):
        lo, hi = bounds[i], bounds[i + 1]
        tops, bottoms = [], []
        for item in items:
            top, bottom = item[0], item[1]
            mid = (top + bottom) / 2.0
            if lo <= mid < hi and bottom > top:
                tops.append(top)
                bottoms.append(bottom)
        if not tops:
            continue
        y0 = max(min(tops) - pad, floors[i] + 1)
        y1 = min(max(bottoms) + pad, hi - gap)
        if y1 > y0:
            out.append((left, y0, right, y1))
    return out


def _mapped(widget, frame):
    """`widget`'s rect in `frame`'s coordinates (a QRectF)."""
    q = hubqt.qt()
    top = widget.mapTo(frame, q.QtCore.QPoint(0, 0))
    return q.QtCore.QRectF(top.x(), top.y(), widget.width(), widget.height())


def _groups(content, frame):
    """The headings and the controls shown under `content`, as (top, bottom) in `frame`'s
    coordinates: a control is a visible widget holding no visible widget of its own (scroll
    bars and the scroll area's viewport left out); a heading is a widget marked
    `heading` / `subhead`, and what is inside it does not count."""
    q = hubqt.qt()
    QtWidgets = q.QtWidgets
    heads, items = [], []
    skip = (QtWidgets.QScrollBar,)
    for widget in content.findChildren(QtWidgets.QWidget):
        if not widget.isVisibleTo(content) or widget.width() <= 0 or widget.height() <= 0:
            continue
        if isinstance(widget, skip):
            continue
        role = widget.property("skRole")
        if role in HEAD_ROLES:
            r = _mapped(widget, frame)
            heads.append((r.top(), r.bottom()))
            continue
        if any(isinstance(c, QtWidgets.QWidget) and not isinstance(c, skip)
               and c.isVisibleTo(content) for c in widget.children()):
            continue
        parent = widget.parentWidget()
        inside = False
        while parent is not None and parent is not content:
            if parent.property("skRole") in HEAD_ROLES:
                inside = True
                break
            parent = parent.parentWidget()
        if inside:
            continue
        r = _mapped(widget, frame)
        items.append((r.top(), r.bottom(), r.left(), r.right()))
    return heads, items


def frame_class():
    """WindowFrame(scale, parent=None): the look-D frame (2026-10-22). Its face fades from
    BEVEL_TOP to `panel`, a light line inside the top edge, an EDGE outline (radius RADIUS),
    a grip at the top's middle; the light (`level`, `flash`: maya_hubqt.paint_light, no face
    change) on its edge. Its `content` (a child the caller makes and names) stands on the
    face in wells (`content_face` "panel") or on a `card` (the chat window)."""
    if "frame" not in _CLASSES:
        q = hubqt.qt()
        QtCore, QtGui = q.QtCore, q.QtGui
        base = hubqt._frame_class()
        tokens = hubstyle.TOKENS

        class WindowFrame(base):

            def __init__(self, scale=1.0, parent=None):
                super(WindowFrame, self).__init__(scale, parent)
                self.content = None
                self.content_view = None      # the rail card's scroll viewport (2026-10-22)
                #  "panel": the content stands on the frame's own face, a hairline under
                #  the title (look B, 2026-10-22); "card": a lighter card (the chat window)
                self.content_face = "panel"
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
                lit = self.level > 0.002 or self.flash > 0.002
                painter = QtGui.QPainter(self)
                try:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing)
                    r = float(hubstyle.px(RADIUS, s))
                    outer = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
                    #  the body: lighter at the top, `panel` from BEVEL_FADE down
                    face = QtGui.QLinearGradient(0.0, 0.0, 0.0,
                                                 float(hubstyle.px(BEVEL_FADE, s)))
                    face.setColorAt(0.0, QtGui.QColor(BEVEL_TOP))
                    face.setColorAt(1.0, QtGui.QColor(tokens["panel"]))
                    painter.setPen(QtGui.QPen(QtGui.QColor(EDGE), 1.0))
                    painter.setBrush(QtGui.QBrush(face))
                    painter.drawRoundedRect(outer, r, r)
                    #  the bevel: a light line just inside the top edge
                    painter.save()
                    painter.setClipRect(QtCore.QRectF(0.0, 0.0, self.width(), r + 1.0))
                    shine = QtGui.QColor(255, 255, 255)
                    shine.setAlphaF(BEVEL_ALPHA)
                    painter.setPen(QtGui.QPen(shine, 1.0))
                    painter.setBrush(QtCore.Qt.NoBrush)
                    painter.drawRoundedRect(outer.adjusted(1.0, 1.0, -1.0, -1.0),
                                            r - 1.0, r - 1.0)
                    painter.restore()
                    #  the grip: a short bar in the middle of the top edge
                    gw, gh = float(hubstyle.px(GRIP_W, s)), float(hubstyle.px(GRIP_H, s))
                    grip = QtGui.QColor(tokens["line"])
                    grip.setAlphaF(GRIP_ALPHA)
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.setBrush(grip)
                    painter.drawRoundedRect(
                        QtCore.QRectF((self.width() - gw) / 2.0,
                                      float(hubstyle.px(GRIP_Y, s)), gw, gh),
                        gh / 2.0, gh / 2.0)
                finally:
                    painter.end()
                if lit:
                    hubqt.paint_light(self, self.level, self.flash, s,
                                      radius=RADIUS, face=False)
                painter = QtGui.QPainter(self)
                try:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing)
                    content = self.content
                    if content is not None and hubqt._valid(content) \
                            and content.isVisible():
                        rect = _mapped(content, self)
                        view = getattr(self, "content_view", None)
                        if view is not None and hubqt._valid(view):
                            #  the rail card's own scroll (2026-10-22): wells only
                            #  where its content shows
                            rect = rect.intersected(_mapped(view, self))
                        if self.content_face == "card":
                            rc = float(hubstyle.px(6, s))
                            painter.setPen(QtCore.Qt.NoPen)
                            painter.setBrush(QtGui.QColor(tokens["card"]))
                            painter.drawRoundedRect(rect, rc, rc)
                        elif self.content_face == "panel":
                            self._paint_wells(painter, content, rect)
                        #  "none": the content paints its own faces (the chat's look A,
                        #  2026-10-22)
                finally:
                    painter.end()

            def _paint_wells(self, painter, content, rect):
                """Look B's wells: each group of the section's controls - those between
                two headings - on a recessed `track` plate."""
                s = self.scale
                heads, items = _groups(content, self)
                left = float(hubstyle.px(WELL_MARGIN, s))
                right = self.width() - left
                rw = float(hubstyle.px(WELL_RADIUS, s))
                painter.save()
                #  the content's own height and a pad round it (the rail card's content has
                #  no margin of its own: the pad stands outside it)
                pad = float(hubstyle.px(WELL_PAD, s))
                painter.setClipRect(QtCore.QRectF(left, rect.top() - pad, right - left,
                                                  rect.height() + 2.0 * pad))
                painter.setPen(QtGui.QPen(QtGui.QColor(tokens["track_edge"]), 1.0))
                painter.setBrush(QtGui.QColor(tokens["track"]))
                for x0, y0, x1, y1 in wells(heads, items, left, right,
                                            hubstyle.px(WELL_PAD, s),
                                            hubstyle.px(WELL_GAP, s)):
                    painter.drawRoundedRect(
                        QtCore.QRectF(x0 + 0.5, y0 + 0.5, x1 - x0 - 1.0, y1 - y0 - 1.0),
                        rw, rw)
                painter.restore()

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


def recessed_sheet(name, scale):
    """Look B's fields (2026-10-22): line edits, drop-downs, lists, tool buttons, chips,
    check boxes and segment tracks with a 1 px `track_edge` edge, on `panel` inside the
    `track` wells (so they stand up from the well) - every rule under the widget `name` (set
    on the frame), so nothing outside the window changes. Pixels are physical (trap 98)."""
    t = hubstyle.TOKENS
    b = max(1, hubstyle.px(1, scale))
    f = "#" + name
    return (
        "{f} QLineEdit, {f} QComboBox, {f} QListWidget {{ background: {tr};"
        " border: {b}px solid {te}; }}\n"
        "{f} QLineEdit:focus {{ border: {b}px solid {ac}; }}\n"
        "{f} QComboBox:hover {{ background: {fh}; }}\n"
        "{f} QPushButton[skRole=\"tool\"] {{ background: {tr}; border: {b}px solid {te}; }}\n"
        "{f} QPushButton[skRole=\"tool\"]:hover {{ background: {hv}; }}\n"
        "{f} QCheckBox[skRole=\"chip\"] {{ background: {tr}; border: {b}px solid {te}; }}\n"
        "{f} QCheckBox[skRole=\"chip\"]:checked {{ background: {at};"
        " border: {b}px solid {at}; }}\n"
        "{f} QCheckBox::indicator {{ background: {tr}; }}\n"
        "{f} QCheckBox::indicator:checked {{ background: {ac}; }}\n"
        "{f} QWidget[skRole=\"segments\"] {{ background: {tr}; border: {b}px solid {te}; }}\n"
        "{f} QSlider::groove:horizontal {{ background: {tr}; }}\n").format(
            f=f, b=b, tr=t["panel"], te=t["track_edge"], ac=t["accent"],
            fh=t["field_hover"], hv=t["hover"], at=t["accent_tint"])


def recess(frame, scale):
    """`recessed_sheet` set on `frame` (it needs a name); its face stays its own paint."""
    name = frame.objectName()
    if name:
        frame.setStyleSheet(recessed_sheet(name, scale))


TITLE_H = 34             # logical px: the title row, room for a 30-tall pill (2026-10-18)


TITLE_SIZE = 10.5        # logical px: the title's name, a step over the body text
DOT = 8                  # logical px: the group's dot in the title
DOT_BOX = 15             # logical px: the dot's widget, with room for its glow


def title_label(text, scale, name):
    """The window title's name (look D, 2026-10-22): `text` as written, bold, `text`, a
    step over the body size, on no background, named `name`."""
    q = hubqt.qt()
    label = hubqt._named(q.QtWidgets.QLabel(text or ""), name)
    label.setStyleSheet(
        "color: {0}; font-weight: bold; font-size: {1}px; "
        "background: transparent;".format(hubstyle.TOKENS["text"],
                                          hubstyle.px(TITLE_SIZE, scale)))
    return label


def dot_pixmap(colour, scale):
    """The group's dot: a DOT disc in `colour` with a soft glow of it round it."""
    q = hubqt.qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    box = hubstyle.px(DOT_BOX, scale)
    image = QtGui.QPixmap(box, box)
    image.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(image)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        c = box / 2.0
        glow = QtGui.QRadialGradient(c, c, c)
        tint = QtGui.QColor(colour)
        tint.setAlphaF(0.55)
        glow.setColorAt(0.0, tint)
        tint.setAlphaF(0.0)
        glow.setColorAt(1.0, tint)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(glow))
        painter.drawEllipse(QtCore.QRectF(0, 0, box, box))
        d = float(hubstyle.px(DOT, scale))
        painter.setBrush(QtGui.QColor(colour))
        painter.drawEllipse(QtCore.QRectF(c - d / 2.0, c - d / 2.0, d, d))
    finally:
        painter.end()
    return image


def title_icon(icon_name, colour, scale, name):
    """The window title's mark (look D, 2026-10-22): the group's dot in its colour, glowing.
    `icon_name` is kept on the widget (`skIconName`) for what reads it."""
    q = hubqt.qt()
    icon = hubqt._named(q.QtWidgets.QLabel(), name)
    icon.setProperty("skIconName", icon_name or "")
    icon.setPixmap(dot_pixmap(colour, scale))
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
                self.started = None         # the clock's zero: when the picture was taken
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
                self.started = None
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
                if self.started is None:
                    #  the clock starts now, not at the press: the picture of a window full
                    #  of Maya's controls takes tens of ms (2026-10-22, the stutter)
                    self.started = _now()
                if self.plan.kind == "spring":
                    return True
                fmt = QtGui.QImage.Format_ARGB32_Premultiplied
                self._image = QtGui.QImage(pix.width(), pix.height(), fmt)
                self._mask = QtGui.QImage(pix.width(), pix.height(), fmt)
                return True

            def _draw(self, painter):
                if self.pix is None and not self._take():
                    return False
                if self.plan is None:
                    return False
                if self.plan.kind == "spring":
                    return self._draw_spring(painter)
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

            def _draw_spring(self, painter):
                """The picture scaled about the point, at its opacity: nothing else."""
                state = hubburst.at(self.plan, self.ms)
                k = hubburst.scale_of(self.plan, state)
                r = self.ratio
                ox = self.offset.x() + self.plan.origin[0] * r
                oy = self.offset.y() + self.plan.origin[1] * r
                painter.save()
                try:
                    painter.setWorldTransform(QtGui.QTransform())
                    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
                    painter.setOpacity(max(0.0, min(1.0, state.face)))
                    painter.translate(ox, oy)
                    painter.scale(k, k)
                    painter.translate(-ox, -oy)
                    painter.drawPixmap(self.offset, self.pix)
                finally:
                    painter.restore()
                self.draws += 1
                return True

        _CLASSES["burst"] = PopupBurst
    return _CLASSES["burst"]


PICTURE_WAIT_MS = 150     # a burst whose frame has not painted runs its clock from the press


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
        plan = hubburst.plan(opening, (o.x(), o.y()),
                             (self.frame.width(), self.frame.height()),
                             self.parts, self.scale)
        return plan, (self.face() if plan.kind != "spring" else None)

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
            self._run_at = _now()
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
        #  a heartbeat: the time is the effect's own clock (`_clock`), which starts at the
        #  picture; the driver runs on until the motion is done, at most 3 x MAX_MS
        anim.setDuration(int(hubburst.MAX_MS * 3))
        anim.valueChanged.connect(lambda v: self._tick(self._clock()))
        anim.finished.connect(self._finish)
        self.anim = anim
        anim.start()
        return True

    def _clock(self):
        """ms since the effect took its picture; 0 until it has."""
        effect = self.effect
        started = getattr(effect, "started", None) if effect is not None else None
        if started is None:
            #  a frame that is not painted (masked down to nothing) never takes its picture:
            #  its clock runs from the press, PICTURE_WAIT_MS late
            run_at = getattr(self, "_run_at", None)
            if run_at is None:
                return 0.0
            return max(0.0, _now() - run_at - PICTURE_WAIT_MS)
        return max(0.0, _now() - started)

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
            elif self._moved(effect.plan):
                #  the window laid itself out again after the picture (2026-10-19:
                #  Animation Setup's portrait grid fits its width on the first
                #  resize, which a hidden window gets only once shown): the plan
                #  again now, the picture at the next paint, the same ms
                effect.plan, effect.face = self._plan(effect.opening)
                effect.pix = None
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

    def _moved(self, plan):
        """Whether the frame's rows or size are no longer the ones `plan` was made for
        (0.2 ms on Animation Setup's window; a spring has no rows, its size alone)."""
        size = (float(self.frame.width()), float(self.frame.height()))
        if size != tuple(plan.size):
            return True
        if plan.kind == "spring":
            return False
        return [tuple(r) for r in self.parts()] != [tuple(r) for r in plan.parts]

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
