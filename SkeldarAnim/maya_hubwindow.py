"""maya_hubwindow - what a section's floating window and the edge rail's card draw alike.

2026-10-18 (spec: docs/superpowers/specs/2026-10-18-floating-windows-design.md): the section
windows in the Time Bar's style.

It holds:
- `frame_class()`: WindowFrame, a CardFrame painting its own face, its `content` the card;
- `pill_class()`: PillButton, a QToolButton painting itself.

2026-10-22 (spec: docs/superpowers/specs/2026-10-22-window-look-d-wells-design.md): the frame
is look D, an instrument like the Time Bar's strip - lighter at the top with a light line inside
the top edge, a dark outline, a grip, the group's dot and the name in the title - and inside it
look B's wells: each group of controls (those between two headings) on a recessed `track`
plate, the fields standing on `panel` in them (`recessed_sheet`).

2026-11-19 (the animator: «удаляем все подсветки и анимации из плагина больше они не нужны.
интерфейс должен быть максимально легким»): the window's light, the pills' lift, glow and press
flash and the burst out of a point are gone; a window opens and closes at once.

Qt is imported lazily through maya_hubqt; the classes are made on first use.
"""

import traceback

import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

PILL_W, PILL_H = 24, 22  # logical px: the face
PILL_PAD = 4             # logical px of room round the face (the title row's height)
PILL_RADIUS = 5
PILL_ICON = 14

_CLASSES = {}


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
    a grip at the top's middle. Its `content` (a child the caller makes and names) stands on
    the face in wells (`content_face` "panel") or on a `card` (the chat window)."""
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
DOT_BOX = 15             # logical px: the dot's widget, the dot in its middle


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
    """The group's dot: a flat DOT disc in `colour` in the middle of a DOT_BOX square."""
    q = hubqt.qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    box = hubstyle.px(DOT_BOX, scale)
    image = QtGui.QPixmap(box, box)
    image.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(image)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        c = box / 2.0
        d = float(hubstyle.px(DOT, scale))
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(colour))
        painter.drawEllipse(QtCore.QRectF(c - d / 2.0, c - d / 2.0, d, d))
    finally:
        painter.end()
    return image


def title_icon(icon_name, colour, scale, name):
    """The window title's mark (look D, 2026-10-22): the group's dot in its colour.
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
    5, `field`, a 1 px `track_edge`) centred in a 32 x 30 widget. Under the mouse its face is
    `hover`, flat. `set_lit(on)` shows the icon in `accent_text` (its window stands)."""
    if "pill" not in _CLASSES:
        q = hubqt.qt()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        tokens = hubstyle.TOKENS

        class PillButton(QtWidgets.QToolButton):

            def __init__(self, icon_name, scale=1.0, parent=None):
                super(PillButton, self).__init__(parent)
                self.scale = scale
                self.icon_name = icon_name
                self.lit = False
                self.hovered = False
                self._failed = False
                self._icons = {}
                self.setFixedSize(hubstyle.px(PILL_W + 2 * PILL_PAD, scale),
                                  hubstyle.px(PILL_H + 2 * PILL_PAD, scale))
                self.setAutoRaise(True)
                self.setCursor(QtCore.Qt.PointingHandCursor)

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
                on = bool(on)
                if on != self.hovered:
                    self.hovered = on
                    self.update()

            # --- events
            def enterEvent(self, event):                   # noqa: N802
                self.hover(True)
                super(PillButton, self).enterEvent(event)

            def leaveEvent(self, event):                   # noqa: N802
                self.hover(False)
                super(PillButton, self).leaveEvent(event)

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
                w, h = float(self.width()), float(self.height())
                face_w = float(hubstyle.px(PILL_W, sc))
                face_h = float(hubstyle.px(PILL_H, sc))
                painter = QtGui.QPainter(self)
                try:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing)
                    painter.translate(w / 2.0, h / 2.0)
                    rect = QtCore.QRectF(-face_w / 2.0 + 0.5, -face_h / 2.0 + 0.5,
                                         face_w - 1.0, face_h - 1.0)
                    r = float(hubstyle.px(PILL_RADIUS, sc))
                    face = tokens["hover"] if self.hovered else tokens["field"]
                    painter.setPen(QtGui.QPen(QtGui.QColor(tokens["track_edge"]), 1.0))
                    painter.setBrush(QtGui.QColor(face))
                    painter.drawRoundedRect(rect, r, r)
                    colour = tokens["accent_text"] if self.lit else tokens["muted"]
                    pix = self._pix(colour)
                    pw, ph = pix.width(), pix.height()
                    painter.drawPixmap(QtCore.QRectF(-pw / 2.0, -ph / 2.0, pw, ph), pix,
                                       QtCore.QRectF(0, 0, pw, ph))
                finally:
                    painter.end()

        _CLASSES["pill"] = PillButton
    return _CLASSES["pill"]
