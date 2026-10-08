"""maya_hubqt - the SkeldarAnim hub's skin: its Qt widgets.

What `maya_hub` builds when Qt is there (2026-09-28, style B + scheme 3 of
the brainstorm): a root of ours inside the same workspaceControl, holding

    header    the SA mark, the jump icons (one per section: expand it and
              scroll to it), the hotkeys button (lit while the map is on),
              the pin (edge panel), a menu - ONE row since 2026-10-08
    message   up to three lines under the header, shown while it holds text,
              with the icon of the card that said it (`say`, `_told`)
    scroll    CARDS - a clickable header (icon chip, title, the moved
              subtitle, chevron) over a BODY whose named layout is where a
              tool's `build_panel()` runs, a group-colour stripe down its
              left edge

Every cmds control a builder makes lands in a body through
`cmds.setParent(path_of(body_layout))` -- measured 2026-09-28 in a probe
window: names, exists/edit/query all as before, the full path running
through the Qt objects (which is why every object here has a name). The
look is `maya_hubstyle.stylesheet()` on the root; the builders' marks are
turned into `skRole` properties, icons, swatches and moved subtitles by
`apply_marks`.

Two Maya seams, replaced by the tests: `find` (MQtUtil -> a QWidget
wrapper) and `path_of` (MQtUtil.fullName). Class-specific calls on Maya's
own widgets go through Qt PROPERTIES (`wordWrap`, `icon`, `iconSize`):
`wrapInstance(ptr, QLabel)` hands back the cached QWidget wrapper when one
exists, and its `setWordWrap` raises AttributeError (measured).

Spec: docs/superpowers/specs/2026-09-28-hub-skin-design.md
"""

import time
import types
import zlib

import maya_hubicons as hubicons
import maya_hubmotion as hubmotion
import maya_hubstyle as hubstyle

_QT = []

#  Qt's largest widget size: a body's height cap taken off after a slide
_NO_CAP = 16777215

#  How long the mouse may be off every card before the light goes to the
#  resting card (see Skin.resting): long enough to cross the gap between two
#  cards without a flash, short enough to read as immediate.
FALLBACK_MS = 150

#  How long a jump's glide waits at most for the other cards to finish
#  sliding (every slide is over within maya_hubmotion.MAX_MS)
GLIDE_WAIT_S = 0.6


def qt():
    """PySide6 (Maya 2025+), else PySide2, as one namespace; None without Qt."""
    if _QT:
        return _QT[0]
    ns = None
    try:
        from PySide6 import QtCore, QtGui, QtSvg, QtWidgets
        import shiboken6 as shiboken
        ns = types.SimpleNamespace(QtCore=QtCore, QtGui=QtGui, QtSvg=QtSvg,
                                   QtWidgets=QtWidgets, shiboken=shiboken)
    except ImportError:
        try:
            from PySide2 import QtCore, QtGui, QtSvg, QtWidgets
            import shiboken2 as shiboken
            ns = types.SimpleNamespace(QtCore=QtCore, QtGui=QtGui,
                                       QtSvg=QtSvg, QtWidgets=QtWidgets,
                                       shiboken=shiboken)
        except ImportError:
            ns = None
    _QT.append(ns)
    return ns


def _maya_ui_ok():
    """Maya's UI is up: OpenMayaUI imports, not batch, a QApplication runs."""
    try:
        import maya.cmds as cmds
        import maya.OpenMayaUI  # noqa: F401
        if cmds.about(batch=True):
            return False
    except Exception:                                        # noqa: BLE001
        return False
    q = qt()
    return bool(q and q.QtWidgets.QApplication.instance())


def available():
    """Whether the skin can be built here."""
    return qt() is not None and _maya_ui_ok()


# ------------------------------------------------------------------- seams

def find(name, layout=False):
    """The QWidget of Maya control (or layout) `name`, or None."""
    import maya.OpenMayaUI as omui
    q = qt()
    ptr = (omui.MQtUtil.findLayout(name) if layout
           else omui.MQtUtil.findControl(name))
    if not ptr and not layout:
        ptr = omui.MQtUtil.findLayout(name)
    if not ptr:
        return None
    widget = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
    if not q.shiboken.isValid(widget):
        #  a dead wrapper cached at this address (see _spread): drop it and
        #  wrap afresh; still dead means nothing to style
        q.shiboken.invalidate(widget)
        widget = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
        if not q.shiboken.isValid(widget):
            return None
    return widget


def on_hub(gx, gy, control="skeldarAnimHub"):
    """Whether the global point lies on the hub: the widget under it descends
    from the hub's root or control, or it falls inside the visible control.
    A drag released there does nothing (the Characters grid's since
    2026-09-30, the UE Bridge list's since 2026-10-01)."""
    q = qt()
    point = q.QtCore.QPoint(int(gx), int(gy))
    names = []
    widget = q.QtWidgets.QApplication.widgetAt(point)
    while widget is not None:
        names.append(widget.objectName())
        widget = widget.parentWidget()
    if hubstyle.over_hub(names, control):
        return True
    try:
        host = find(control)
    except Exception:                                        # noqa: BLE001
        host = None
    return bool(host is not None and host.isVisible()
                and host.rect().contains(host.mapFromGlobal(point)))


def path_of(obj):
    """The Maya path of a Qt object of ours: what `cmds.setParent` takes."""
    import maya.OpenMayaUI as omui
    q = qt()
    return omui.MQtUtil.fullName(int(q.shiboken.getCppPointer(obj)[0]))


def destroy_roots(control):
    """Delete every skin root standing in workspaceControl `control`, NOW.

    Measured 2026-09-28: after an install the fresh `maya_hub` does not know
    the skin an older module object built, so a rebuild left that root in
    the control beside the new one -- two sets of controls with the same
    names, and `find` styling the old set. Found by objectName, never by
    module state. Returns how many were deleted."""
    q = qt()
    host = host_widget(control)
    if host is None:
        return 0
    roots = [w for w in host.findChildren(q.QtWidgets.QWidget)
             if w.objectName() == hubstyle.ROOT]
    for root in roots:
        root.setParent(None)
        q.shiboken.delete(root)
    return len(roots)


def host_widget(control):
    """The QWidget of workspaceControl `control`, which a root goes into.

    The WIDGET, not its layout: a layout reached through a temporary
    wrapper is invalidated with that wrapper -- measured 2026-09-28,
    `find(control).layout()` returned valid and was "Internal C++ object
    already deleted" one call later, when the wrapper had been collected.
    The Skin holds the widget for as long as it needs the layout.
    """
    return find(control)


# ------------------------------------------------------------------- icons

def pixmap(name, colour, size):
    """Icon `name` in `colour`, `size` physical pixels square."""
    q = qt()
    data = q.QtCore.QByteArray(hubicons.svg(name, colour).encode("utf-8"))
    renderer = q.QtSvg.QSvgRenderer(data)
    image = q.QtGui.QPixmap(size, size)
    image.fill(q.QtCore.Qt.transparent)
    painter = q.QtGui.QPainter(image)
    renderer.render(painter)
    painter.end()
    return image


def _valid(obj):
    """`obj`'s C++ object still stands (a hub rebuilt mid-glide deletes it)."""
    try:
        return bool(qt().shiboken.isValid(obj))
    except Exception:                                        # noqa: BLE001
        return False


def rotated(image, angle):
    """`image` turned `angle` degrees clockwise about its centre, the same
    size (a card's chevron while the body slides)."""
    q = qt()
    out = q.QtGui.QPixmap(image.size())
    out.fill(q.QtCore.Qt.transparent)
    painter = q.QtGui.QPainter(out)
    painter.setRenderHint(q.QtGui.QPainter.Antialiasing)
    painter.setRenderHint(q.QtGui.QPainter.SmoothPixmapTransform)
    half_w, half_h = image.width() / 2.0, image.height() / 2.0
    painter.translate(half_w, half_h)
    painter.rotate(angle)
    painter.translate(-half_w, -half_h)
    painter.drawPixmap(0, 0, image)
    painter.end()
    return out


def icon_file(name, colour, folder=None):
    """Icon `name` in `colour` written as an SVG file; its path, forward
    slashes (what a stylesheet's `url()` takes -- the dropdown arrow)."""
    import os
    import tempfile
    folder = folder or os.path.join(tempfile.gettempdir(), "skeldar_hub")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, "{0}_{1}.svg".format(name,
                                                     colour.lstrip("#")))
    with open(path, "w") as handle:
        handle.write(hubicons.svg(name, colour))
    return path.replace("\\", "/")


def icon(name, colour, size, on_colour=None):
    """A QIcon; `on_colour` draws its checked state."""
    q = qt()
    result = q.QtGui.QIcon()
    result.addPixmap(pixmap(name, colour, size), q.QtGui.QIcon.Normal,
                     q.QtGui.QIcon.Off)
    if on_colour:
        result.addPixmap(pixmap(name, on_colour, size), q.QtGui.QIcon.Normal,
                         q.QtGui.QIcon.On)
    return result


# ICON colour per role: the text colour the stylesheet gives that role.
_ICON_COLOUR = {"primary": "on_accent", "danger": "danger"}


def repolish(widget):
    """Re-read the stylesheet after a property the rules select on changed."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _named(widget, name, role=None):
    widget.setObjectName(name)
    if role:
        widget.setProperty("skRole", role)
    return widget


# ------------------------------------------------------------------- cards

_CLASSES = {}


def _head_class():
    """A QWidget that calls back on a left click: the card's header."""
    if "head" not in _CLASSES:
        q = qt()

        class CardHead(q.QtWidgets.QWidget):

            def __init__(self, on_click, parent=None):
                super(CardHead, self).__init__(parent)
                self._on_click = on_click
                self.setCursor(q.QtCore.Qt.PointingHandCursor)

            def mousePressEvent(self, event):              # noqa: N802
                if event.button() == q.QtCore.Qt.LeftButton:
                    self._on_click()
                    event.accept()
                    return
                super(CardHead, self).mousePressEvent(event)

        _CLASSES["head"] = CardHead
    return _CLASSES["head"]


def sounding(widget, root):
    """Whether the mouse entering `widget` plays the hover sound (2026-10-01,
    «звук наводки на кнопочку»): a button (QAbstractButton -- Maya's
    buttons, checkboxes and segments, measured on the live hub, and our
    strip and header), a dropdown or a card's header, enabled, under
    `root`. The type is asked first: every Enter in Maya comes through
    here."""
    q = qt()
    w = q.QtWidgets
    if not isinstance(widget, (w.QAbstractButton, w.QComboBox,
                               _head_class())):
        return False
    if not widget.isEnabled():
        return False
    return widget is root or root.isAncestorOf(widget)


def _frame_class():
    """A card's QFrame (still `QFrame[skCard]` to the stylesheet, which draws
    its plain face) painting its own LIGHT over that face: `level` 0..1 and
    `flash` 0..1, animated by its Card (2026-10-01, «красивый глоу и анимацию
    подсветки»). A full repaint of a card costs 1.5 ms (UE Bridge, measured),
    so the whole light - the face's tint too - can fade. Since 2026-10-08 it
    also paints its group's colour as a `stripe` down its left edge (the
    group labels are gone from the compact skin), under the light."""
    if "frame" not in _CLASSES:
        q = qt()

        class CardFrame(q.QtWidgets.QFrame):

            def __init__(self, scale=1.0, parent=None):
                super(CardFrame, self).__init__(parent)
                self.scale = scale
                self.level = 0.0
                self.flash = 0.0
                self.stripe = None

            def paintEvent(self, event):                   # noqa: N802
                super(CardFrame, self).paintEvent(event)
                if self.stripe:
                    paint_stripe(self, self.stripe, self.scale)
                if self.level > 0.002 or self.flash > 0.002:
                    paint_light(self, self.level, self.flash, self.scale)

        _CLASSES["frame"] = CardFrame
    return _CLASSES["frame"]


def paint_stripe(widget, colour, scale):
    """The card's group as a bar down its left edge (2026-10-08: the group
    labels are gone in the compact skin), clipped by the rounded face."""
    q = qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    radius = float(hubstyle.px(8, scale))
    bar = float(hubstyle.px(3, scale))
    painter = QtGui.QPainter(widget)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        face = QtGui.QPainterPath()
        face.addRoundedRect(QtCore.QRectF(widget.rect()), radius, radius)
        painter.setClipPath(face)
        painter.fillRect(QtCore.QRectF(0, 0, bar, widget.height()),
                         QtGui.QColor(colour))
    finally:
        painter.end()


def paint_light(widget, level, flash, scale):
    """The card light on `widget`: the face card_active at `level`, the inner
    glow (`maya_hubstyle.glow_rings`), the 2 px ring card_edge at `level` -
    brighter toward accent_text, and fully drawn, while it `flash`es."""
    q = qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    tokens = hubstyle.TOKENS
    edge = float(hubstyle.px(2, scale))
    radius = float(hubstyle.px(8, scale))
    outer = QtCore.QRectF(widget.rect())
    painter = QtGui.QPainter(widget)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        face = QtGui.QColor(tokens["card_active"])
        face.setAlphaF(min(1.0, level))
        painter.setBrush(face)
        inner = outer.adjusted(edge, edge, -edge, -edge)
        painter.drawRoundedRect(inner, max(0.0, radius - edge),
                                max(0.0, radius - edge))
        painter.setBrush(QtCore.Qt.NoBrush)
        glow = QtGui.QColor(tokens["accent"])
        for inset, width, alpha in hubstyle.glow_rings(level, flash, scale):
            if alpha <= 0.0:
                continue
            d = edge + (inset + width / 2.0) * scale
            w = width * scale
            glow.setAlphaF(alpha)
            painter.setPen(QtGui.QPen(glow, w))
            painter.drawRoundedRect(outer.adjusted(d, d, -d, -d),
                                    max(0.0, radius - d),
                                    max(0.0, radius - d))
        ring = QtGui.QColor(hubstyle.mix(tokens["card_edge"],
                                         tokens["accent_text"], flash))
        ring.setAlphaF(min(1.0, max(level, flash)))
        painter.setPen(QtGui.QPen(ring, edge))
        half = edge / 2.0
        painter.drawRoundedRect(outer.adjusted(half, half, -half, -half),
                                radius - half, radius - half)
    finally:
        painter.end()


def _watcher_class():
    """An application-wide event filter: a press or a focus change anywhere
    is handed to `on_press(widget)`, the mouse entering a widget to
    `on_enter(widget)`; it never swallows the event."""
    if "watch" not in _CLASSES:
        q = qt()
        pressed = (q.QtCore.QEvent.MouseButtonPress, q.QtCore.QEvent.FocusIn)
        entered = q.QtCore.QEvent.Enter
        left = q.QtCore.QEvent.Leave

        class Watcher(q.QtCore.QObject):

            def __init__(self, on_press, on_enter, on_leave, parent=None):
                super(Watcher, self).__init__(parent)
                self._on_press = on_press
                self._on_enter = on_enter
                self._on_leave = on_leave

            def eventFilter(self, obj, event):             # noqa: N802
                kind = event.type()
                try:
                    if kind in pressed:
                        self._on_press(obj)
                    elif kind == entered:
                        self._on_enter(obj)
                    elif kind == left:
                        self._on_leave(obj)
                except Exception:                            # noqa: BLE001
                    pass
                return False

        _CLASSES["watch"] = Watcher
    return _CLASSES["watch"]


# ------------------------------------------------------------- hover glow

#  The glow of a control under the mouse (2026-10-02, «все надпись немного
#  подсвечивались легким свечением когда мы наводим на них мышкой»; the
#  animator chose the glow in the text's own colour, on everything
#  clickable). maya_hubglow is the arithmetic; here, the effect that draws it
#  and the Glower that the skin's watcher drives.

GLOW_TICK_MS = 16


def glowing(widget, root):
    """Whether `widget` glows under the mouse: a control that ticks on hover
    (`sounding`), not a card header (its card lights up already - the
    animator, minutes after the first build: «уберем свечение из надписей
    заголовков разделов мы и так разделы подсвечивали раньше»), not a colour
    swatch (a dot has no ink), carrying no graphics effect of somebody
    else's."""
    if widget is None or not sounding(widget, root):
        return False
    if isinstance(widget, _head_class()):
        return False
    if widget.property("skRole") == "swatch":
        return False
    effect = widget.graphicsEffect()
    return effect is None or (isinstance(effect, _glow_class())
                              and _valid(effect))


def _glow_class():
    """A QGraphicsEffect drawing a control's glow at `level` (0..1): its ink
    bloomed in the ink's own colour (`mode` "ink"), or a warm rim inside the
    edge ("rim", the orange primary button). The glow image is computed once
    per picture of the control (`computed` counts the numpy runs) and drawn at
    `level` opacity, so a fade only changes a number. Level 0 draws the
    control as it is; a glow that fails marks the effect `broken`, which then
    draws the control as it is for good."""
    if "glow" not in _CLASSES:
        q = qt()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

        class HoverGlow(QtWidgets.QGraphicsEffect):

            def __init__(self, mode="ink", scale=1.0, parent=None):
                super(HoverGlow, self).__init__(parent)
                self.mode = mode
                self.scale = scale
                self.level = 0.0
                self.broken = False
                self.error = None
                self.computed = 0
                #  coming up or lit (the Glower says): drawn from the source
                #  pixmap; going dark: drawn directly (see draw)
                self.rising = True
                self.from_pixmap = 0
                self._key = None
                self._image = None
                self._delta = QtCore.QPoint()

            def boundingRectFor(self, rect):               # noqa: N802
                if self.mode != "ink":
                    return rect
                import maya_hubglow as hubglow
                reach = hubglow.pad(self.scale)
                return rect.adjusted(-reach, -reach, reach, reach)

            def draw(self, painter):
                if self.level <= 0.002 or self.broken:
                    self.drawSource(painter)
                    return
                if not self.rising and self._image is not None:
                    self._draw_fading(painter)
                    return
                #  Coming up or lit: the control drawn from its source
                #  pixmap, which feeds the glow (crc-cached). Its text is
                #  then grayscale-antialiased, not ClearType (a pixmap with
                #  alpha; measured 2026-10-02: 434 edge pixels of "Camera
                #  Setup" up to 52 levels apart) - the switch lands with the
                #  hover style's own repaint. Qt offers no way round it:
                #  drawSource after sourcePixmap draws that very pixmap,
                #  and sourcePixmap after drawSource broke the drawing.
                offset = QtCore.QPoint()
                padding = (QtWidgets.QGraphicsEffect.PadToEffectiveBoundingRect
                           if self.mode == "ink"
                           else QtWidgets.QGraphicsEffect.NoPad)
                source = self.sourcePixmap(QtCore.Qt.DeviceCoordinates,
                                           offset, padding)
                if source.isNull():
                    self.drawSource(painter)
                    return
                self.from_pixmap += 1
                inner = self.sourceBoundingRect(QtCore.Qt.DeviceCoordinates)
                self._delta = offset - QtCore.QPoint(int(round(inner.left())),
                                                     int(round(inner.top())))
                painter.save()
                try:
                    painter.setWorldTransform(QtGui.QTransform())
                    painter.drawPixmap(offset, source)
                    image = self._glow(source, inner, offset)
                    if image is not None:
                        self._plus(painter, offset, image)
                finally:
                    painter.restore()

            def _draw_fading(self, painter):
                """Going dark: the control drawn as Qt draws it - DIRECTLY
                once it has repainted itself (the hover style coming off
                as the mouse leaves), so its ClearType text is back at that
                very moment and not when the glow ends - the glow of the
                lit picture over it (the ink did not move), where the
                control stands now."""
                self.drawSource(painter)
                inner = self.sourceBoundingRect(QtCore.Qt.DeviceCoordinates)
                offset = QtCore.QPoint(int(round(inner.left())),
                                       int(round(inner.top()))) + self._delta
                painter.save()
                try:
                    painter.setWorldTransform(QtGui.QTransform())
                    self._plus(painter, offset, self._image)
                finally:
                    painter.restore()

            def _plus(self, painter, offset, image):
                painter.setOpacity(min(1.0, self.level))
                painter.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                painter.drawImage(offset, image)

            def _glow(self, source, inner, offset):
                try:
                    image = source.toImage().convertToFormat(
                        QtGui.QImage.Format_ARGB32_Premultiplied)
                    w, h = image.width(), image.height()
                    bpl = image.bytesPerLine()
                    data = bytes(image.constBits())[:bpl * h]
                    key = (w, h, self.mode, zlib.crc32(data))
                    if key == self._key:
                        return self._image
                    import numpy as np
                    import maya_hubglow as hubglow
                    bgra = np.frombuffer(data, np.uint8).reshape(
                        h, bpl // 4, 4)[:, :w]
                    if self.mode == "rim":
                        out = hubglow.rim(bgra, self.scale)
                    else:
                        #  the control's own rect inside the padded picture
                        #  (sourceBoundingRect is a QRectF)
                        top = max(0, int(round(inner.top())) - offset.y())
                        left = max(0, int(round(inner.left())) - offset.x())
                        box = (top, left,
                               min(h, top + max(1, int(inner.height()))),
                               min(w, left + max(1, int(inner.width()))))
                        out = hubglow.bloom(bgra, self.scale, box)
                    self.computed += 1
                    glow = None
                    if out is not None:
                        glow = QtGui.QImage(
                            out.tobytes(), w, h, w * 4,
                            QtGui.QImage.Format_ARGB32_Premultiplied).copy()
                    self._key, self._image = key, glow
                    return glow
                except Exception as exc:                     # noqa: BLE001
                    #  kept for a verify to read: the glow goes quiet
                    self.broken = True
                    self.error = repr(exc)
                    return None

        _CLASSES["glow"] = HoverGlow
    return _CLASSES["glow"]


class Glower(object):
    """The one control glowing under the mouse, fading in and out.

    The skin's application-wide watcher hands it every Enter and Leave. It
    never keeps a WIDGET: a wrapper of a Maya-owned widget that Maya deletes
    reads freed memory (CLAUDE.md trap 135). It holds its EFFECTS instead -
    ours, Python-made, so one whose control died answers `isValid` False and
    raises on a call rather than crashing - found again through
    `widget.graphicsEffect()` while the widget is in its own event. Every
    effect is held: PySide deletes one whose wrapper is collected (measured
    2026-10-02). An effect stays on its control once made; dark it is
    disabled, and Qt paints the control as if it had none."""

    def __init__(self, root, scale=1.0, motion=None):
        q = qt()
        self.root = root
        self.scale = scale
        self._motion = motion
        self._clock = time.monotonic
        self.effects = []
        self.lit = None
        self._fades = {}          # id(effect) -> [effect, start, end, t0, ms]
        self._timer = q.QtCore.QTimer(root)
        self._timer.setObjectName("skeldarHubGlowTimer")
        self._timer.setInterval(GLOW_TICK_MS)
        self._timer.timeout.connect(self.tick)

    def _animated(self):
        return bool(self._motion is None or self._motion())

    def _target(self, widget):
        """`widget` or its nearest ancestor that glows, inside the root."""
        q = qt()
        root = self.root
        if not isinstance(widget, q.QtWidgets.QWidget):
            return None
        if widget is not root and not root.isAncestorOf(widget):
            return None
        node = widget
        while node is not None and node is not root:
            if glowing(node, root):
                return node
            node = node.parentWidget()
        return None

    def _effect_of(self, widget, create=False):
        effect = widget.graphicsEffect()
        cls = _glow_class()
        if isinstance(effect, cls):
            return effect if _valid(effect) else None
        if effect is not None or not create:
            return None
        mode = "rim" if widget.property("skRole") == "primary" else "ink"
        effect = cls(mode, self.scale)
        effect.setEnabled(False)                  # dark until it fades up
        widget.setGraphicsEffect(effect)
        self.effects = [e for e in self.effects if _valid(e)]
        self.effects.append(effect)
        return effect

    def enter(self, widget):
        """The mouse entered `widget`: its glowing control fades up, any
        other down; nothing glowing there, everything down."""
        target = self._target(widget)
        if target is None and self.lit is None:
            return
        effect = (self._effect_of(target, create=True)
                  if target is not None else None)
        if effect is self.lit:
            return
        if self.lit is not None:
            self._fade(self.lit, 0.0)
        self.lit = effect
        if effect is not None:
            self._fade(effect, 1.0)

    def leave(self, widget):
        """The mouse left `widget`: if it is the one glowing, it fades."""
        q = qt()
        if self.lit is None or not isinstance(widget, q.QtWidgets.QWidget):
            return
        if self._effect_of(widget) is self.lit:
            self._fade(self.lit, 0.0)
            self.lit = None

    def _drop(self, effect):
        self._fades.pop(id(effect), None)
        if self.lit is effect:
            self.lit = None
        self.effects = [e for e in self.effects if e is not effect]

    def _set(self, effect, level):
        """`effect` at `level`; dark, it is DISABLED - Qt then paints its
        control directly and never calls our Python `draw` (every control
        hovered once keeps its effect, and a card sliding repaints them
        all)."""
        if not _valid(effect):
            self._drop(effect)
            return False
        effect.level = level
        lit = level > 0.002
        if effect.isEnabled() != lit:
            effect.setEnabled(lit)
        effect.update()
        return True

    def _fade(self, effect, end):
        if not _valid(effect):
            self._drop(effect)
            return
        start = effect.level
        effect.rising = end > 0.0
        if not self._animated() or start == end:
            self._fades.pop(id(effect), None)
            self._set(effect, end)
            return
        ms = hubmotion.glow_ms(end > start, start, end)
        self._fades[id(effect)] = [effect, start, end, self._clock(), ms]
        if not self._timer.isActive():
            self._timer.start()

    def tick(self):
        """One step of every fade under way; the timer stops when none is."""
        now = self._clock()
        for key, (effect, start, end, t0, ms) in list(self._fades.items()):
            t = (now - t0) * 1000.0 / float(ms)
            t = 1.0 if t >= 1.0 - 1e-6 else t
            shape = hubmotion.ease if end > start else hubmotion.smooth
            level = end if t >= 1.0 else hubmotion.lerp(start, end, shape(t))
            if self._set(effect, level) and t >= 1.0:
                self._fades.pop(key, None)
        if not self._fades:
            self._timer.stop()

    def finish(self):
        """Every fade at its end now (Interface animations switched off)."""
        for effect, _start, end, _t0, _ms in list(self._fades.values()):
            self._set(effect, end)
        self._fades.clear()
        self._timer.stop()

    def stop(self):
        """Nothing glows or moves, no effect is held (the skin is going)."""
        if _valid(self._timer):
            self._timer.stop()
        self._fades.clear()
        self.lit = None
        self.effects = []


class Card(object):
    """One section: header over body. `body_layout` is where a builder runs.

    Since 2026-10-01 the body SLIDES open and shut on the animator's moves
    («открывать закрывать с какими-то анимациями»): `set_collapsed(c,
    animate=True)` caps the body's height tick by tick with the body's own
    layout DISABLED for the length of it and laid out once at the full
    height, so a short body clips its children instead of squeezing them to
    their minimums. `motion` is the skin's switch (a callable); without it,
    off screen, or with `animate` False the old instant show / hide."""

    def __init__(self, key, label, icon_name, colour, chip, scale,
                 collapsed=False, on_toggle=None, motion=None):
        q = qt()
        w = q.QtWidgets
        self.key = key
        self.scale = scale
        #  What a section's status line says about its card (2026-10-08): the
        #  icon and colour go to the message line when this card said
        #  something; `status_controls` are the cmds controls whose text the
        #  status relay (maya_hubstyle.tell) takes for this card's; `_hints`
        #  are its builders' static hints, now the header's tooltip.
        self.icon_name, self.colour = icon_name, colour
        self.status_controls = set()
        self._hints = []
        self._on_toggle = on_toggle
        self._motion = motion
        self._anim = None
        self._angle = 0.0
        self._chevron_base = None
        self._laid = None
        self._opening = False
        self._from_height = self._shown = 0
        self._from_angle = 0.0
        s = lambda n: hubstyle.px(n, scale)             # noqa: E731

        self._light_anim = None
        self._flash_anim = None
        self.frame = _named(_frame_class()(scale), "skeldarHubCard_" + key)
        self.frame.setProperty("skCard", True)
        self.frame.stripe = colour
        column = w.QVBoxLayout(self.frame)
        column.setObjectName("skeldarHubCardLayout_" + key)
        #  compact (2026-10-08, variant B): 5 / 4 / 5 / 5, was 8 / 7 / 8 / 8
        column.setContentsMargins(s(5), s(4), s(5), s(5))
        #  The gap under the header is the BODY's top margin (it was this
        #  column's spacing): it opens and shuts with the body instead of
        #  appearing on the first frame of a slide and vanishing on the last.
        column.setSpacing(0)

        self.header = _named(_head_class()(self.toggle),
                             "skeldarHubCardHead_" + key, "cardhead")
        #  Exactly its own height, never more or less: while a body slides
        #  the card's column was laid out a moment before the card got its
        #  new height, the difference went to the header, and the title and
        #  chevron, centred in it, shook (the animator saw it, 2026-10-01;
        #  measured: the header 33 -> 34, 36 ... 350 px shutting, 17 opening).
        self.header.setSizePolicy(w.QSizePolicy.Preferred,
                                  w.QSizePolicy.Fixed)
        row = w.QHBoxLayout(self.header)
        row.setObjectName("skeldarHubCardHeadLayout_" + key)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(s(5))
        chip_label = _named(w.QLabel(), "skeldarHubCardIcon_" + key,
                            "cardicon")
        chip_label.setFixedSize(s(18), s(18))
        chip_label.setAlignment(q.QtCore.Qt.AlignCenter)
        chip_label.setPixmap(pixmap(icon_name, colour, s(12)))
        chip_label.setStyleSheet("background: {0}; border-radius: {1}px;"
                                 .format(chip, s(5)))
        title = _named(w.QLabel(label), "skeldarHubCardTitle_" + key,
                       "cardtitle")
        #  Where a moved subtitle goes: takes what the title leaves and never
        #  asks for more, so a long line clips instead of widening the hub.
        self.subtitle_slot = _named(w.QWidget(), "skeldarHubCardSub_" + key)
        self.subtitle_slot.setSizePolicy(w.QSizePolicy.Ignored,
                                         w.QSizePolicy.Preferred)
        sub = w.QHBoxLayout(self.subtitle_slot)
        sub.setObjectName("skeldarHubCardSubLayout_" + key)
        sub.setContentsMargins(0, 0, 0, 0)
        self.chevron = _named(w.QLabel(), "skeldarHubCardChevron_" + key)
        row.addWidget(chip_label)
        row.addWidget(title)
        row.addWidget(self.subtitle_slot, 1)
        row.addWidget(self.chevron)

        self.body = _named(w.QWidget(), "skeldarHubBody_" + key)
        self.body_layout = w.QVBoxLayout(self.body)
        self.body_layout.setObjectName("skeldarHubBodyLayout_" + key)
        self.body_layout.setContentsMargins(0, s(4), 0, 0)
        self.body_layout.setSpacing(0)
        column.addWidget(self.header)
        column.addWidget(self.body)
        self._collapsed = None
        self.set_collapsed(collapsed)

    def body_path(self):
        return path_of(self.body_layout)

    def add_hint(self, text):
        """A builder's static hint, now the header's tooltip (2026-10-08:
        the compact skin keeps no hint line in the body)."""
        text = (text or "").strip()
        if text:
            self._hints.append(text)
            self.header.setToolTip("\n".join(self._hints))

    def collapsed(self):
        return bool(self._collapsed)

    def sliding(self):
        """A slide is under way."""
        return self._anim is not None

    def set_collapsed(self, collapsed, animate=False):
        """Show or hide the body -- sliding when `animate` (the animator's
        move), the skin's switch and the screen allow it. `collapsed()`
        answers the new state at once. No callback: code opening a card
        remembers through the hub; only the animator's click calls back
        (`toggle`)."""
        collapsed = bool(collapsed)
        if collapsed == self._collapsed:
            return
        first = self._collapsed is None
        self._collapsed = collapsed
        if (animate and not first and self._motion is not None
                and self._motion() and self.frame.isVisible()):
            self._slide(not collapsed)
            return
        self._stop()
        self._settle()

    def toggle(self):
        self.set_collapsed(not self._collapsed, animate=True)
        if self._on_toggle:
            self._on_toggle(self.key, self._collapsed)

    # -------------------------------------------------------------- motion

    def natural_height(self, width=None):
        """The body's own height at the card's width (the header's: the two
        share the card's column), laid out or not."""
        layout = self.body_layout
        width = self.header.width() if width is None else width
        height = (layout.heightForWidth(width) if layout.hasHeightForWidth()
                  else -1)
        if height < 0:
            height = layout.sizeHint().height()
        return max(height, layout.minimumSize().height())

    def _lay_out_full(self):
        """The body's children laid out at its full height, whatever the
        body's own (capped) height is: they slide into view, never squeezed.
        Re-read every tick -- a grid inside settles a frame later (measured
        2026-10-01: Characters 422 shown, 420 settled) -- so a slide ends on
        the settled height."""
        q = qt()
        width = self.header.width()
        full = self.natural_height(width)
        if (width, full) != self._laid:
            self.body_layout.setGeometry(q.QtCore.QRect(0, 0, width, full))
            self._laid = (width, full)
        return full

    def _slide(self, opening):
        q = qt()
        if self.sliding():
            start = self._shown                     # turned back mid-way
        else:
            start = self.body.height() if self.body.isVisible() else 0
        self._stop()
        if opening and not self.body.isVisible():
            self.body.setMaximumHeight(0)
            self.body.setVisible(True)
            start = 0
        self.body_layout.setEnabled(False)
        self._laid = None
        self._opening = opening
        self._from_height = start
        self._from_angle = self._angle
        self._shown = start
        target = self._lay_out_full() if opening else 0
        anim = q.QtCore.QVariantAnimation(self.frame)
        anim.setObjectName("skeldarHubCardSlide_" + self.key)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(hubmotion.duration(target - start, self.scale,
                                            opening=opening))
        anim.valueChanged.connect(self._tick)
        anim.finished.connect(self._finished)
        self._anim = anim
        anim.start()

    def _tick(self, value):
        k = hubmotion.ease(value)
        target = self._lay_out_full() if self._opening else 0
        self._shown = int(round(hubmotion.lerp(self._from_height, target, k)))
        self.body.setMaximumHeight(self._shown)
        self._lay_out_now()
        end = hubmotion.CHEVRON_OPEN if self._opening else 0.0
        self._angle = hubmotion.lerp(self._from_angle, end, k)
        self._paint_chevron(self._angle)

    def _lay_out_now(self):
        """The card and the column holding it laid out NOW, before anything
        is painted: left to Qt's posted LayoutRequests, the card's own column
        ran first, on the card's old height, and the card's edge lagged the
        body a frame behind."""
        layout = self.frame.layout()
        if layout is not None:
            layout.activate()
        parent = self.frame.parentWidget()
        if parent is not None and parent.layout() is not None:
            parent.layout().activate()

    def _finished(self):
        self._stop()
        self._settle()

    def _stop(self):
        anim, self._anim = self._anim, None
        if anim is not None:
            try:
                anim.valueChanged.disconnect(self._tick)
                anim.finished.disconnect(self._finished)
            except (RuntimeError, TypeError):
                pass
            anim.stop()
            anim.deleteLater()

    def _settle(self):
        """The idle card: the body shown or hidden, no height cap, its own
        layout managing it again -- exactly what it was before the slides."""
        self.body.setVisible(not self._collapsed)
        self.body.setMaximumHeight(_NO_CAP)
        if not self.body_layout.isEnabled():
            self.body_layout.setEnabled(True)
            self.body_layout.invalidate()
            self.body_layout.activate()
        self._angle = 0.0 if self._collapsed else hubmotion.CHEVRON_OPEN
        self._paint_chevron(None)

    def _paint_chevron(self, angle):
        """The chevron at rest (None: the right / down icons themselves) or
        turned `angle` degrees from right."""
        size = hubstyle.px(14, self.scale)
        colour = hubstyle.TOKENS["muted"]
        if angle is None:
            name = "chevron-right" if self._collapsed else "chevron-down"
            self.chevron.setPixmap(pixmap(name, colour, size))
            return
        if self._chevron_base is None:
            self._chevron_base = pixmap("chevron-right", colour, size)
        self.chevron.setPixmap(rotated(self._chevron_base, angle))

    # --------------------------------------------------------------- light

    def set_lit(self, on, animate=False):
        """The card's light up (`on`) or down: fading from wherever it stands
        when `animate` and the card is on screen, else at once."""
        target = 1.0 if on else 0.0
        self._stop_anim("_light_anim")
        frame = self.frame
        start = frame.level
        if not animate or not frame.isVisible() or start == target:
            frame.level = target
            frame.update()
            return
        q = qt()
        shape = hubmotion.ease if on else hubmotion.smooth
        anim = q.QtCore.QVariantAnimation(frame)
        anim.setObjectName("skeldarHubCardLight_" + self.key)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(hubmotion.light_ms(on, start, target))

        def tick(value):
            frame.level = hubmotion.lerp(start, target, shape(value))
            frame.update()
        anim.valueChanged.connect(tick)
        anim.finished.connect(lambda: self._done_anim("_light_anim", "level",
                                                      target))
        self._light_anim = anim
        anim.start()

    def pulse(self, animate=False):
        """A flash: the ring brightens and the glow widens for FLASH_MS (the
        card just chosen). Nothing when not `animate` or off screen."""
        self._stop_anim("_flash_anim")
        frame = self.frame
        if not animate or not frame.isVisible():
            frame.flash = 0.0
            frame.update()
            return
        q = qt()
        anim = q.QtCore.QVariantAnimation(frame)
        anim.setObjectName("skeldarHubCardFlash_" + self.key)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(hubmotion.FLASH_MS)

        def tick(value):
            frame.flash = hubmotion.flash_at(value)
            frame.update()
        anim.valueChanged.connect(tick)
        anim.finished.connect(lambda: self._done_anim("_flash_anim", "flash",
                                                      0.0))
        self._flash_anim = anim
        anim.start()

    def _done_anim(self, slot, attr, value):
        self._stop_anim(slot)
        if _valid(self.frame):
            setattr(self.frame, attr, value)
            self.frame.update()

    def _stop_anim(self, slot):
        anim = getattr(self, slot)
        setattr(self, slot, None)
        if anim is not None:
            try:
                anim.valueChanged.disconnect()
                anim.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            anim.stop()
            anim.deleteLater()

    def add_subtitle(self, widget):
        """Move a builder's line into the header, one line, never widening."""
        q = qt()
        widget.setProperty("wordWrap", False)
        widget.setProperty("skRole", "subtitle")
        widget.setProperty("alignment", q.QtCore.Qt.AlignRight
                           | q.QtCore.Qt.AlignVCenter)
        widget.setMinimumHeight(0)
        widget.setMaximumHeight(16777215)
        widget.setMinimumWidth(0)
        widget.setSizePolicy(q.QtWidgets.QSizePolicy.Ignored,
                             q.QtWidgets.QSizePolicy.Preferred)
        self.subtitle_slot.layout().addWidget(widget, 1)
        return widget


# -------------------------------------------------------------------- skin

class Skin(object):
    """The whole skinned hub. `parent_layout` is the workspaceControl's."""

    def __init__(self, parent, scale=1.0, callbacks=None):
        q = qt()
        w = q.QtWidgets
        #  a widget (the workspaceControl's) or a layout; the widget wrapper
        #  is kept, or its layout's wrapper dies with it (see host_widget)
        self.host = parent
        parent_layout = (parent if isinstance(parent, w.QLayout) or parent
                         is None else parent.layout())
        self.scale = scale
        self.cb = callbacks or {}
        self.cards = {}
        self.jumps = {}
        #  each jump's own colour and icon: the update jump's state paints
        #  it (set_state) and its group's colour comes back with no state
        self._jump_colour = {}
        self._jump_icon = {}
        #  ⋮ -> Interface animations (2026-10-01): the cards slide, a jump
        #  glides (maya_hub sets it from maya_hubmotion's optionVar)
        self.animations = True
        self._glide = None
        s = self.px

        self.root = _named(w.QWidget(), hubstyle.ROOT)
        top = w.QVBoxLayout(self.root)
        top.setObjectName("skeldarHubRootLayout")
        #  compact (2026-10-08, variant B): margins and gaps 3, was 6
        top.setContentsMargins(s(3), s(3), s(3), s(3))
        top.setSpacing(s(3))
        if parent_layout is not None:
            parent_layout.addWidget(self.root)

        self.header = self._build_header()
        top.addWidget(self.header)
        self.message = self._build_message()
        top.addWidget(self.message)

        self.scroll = _named(w.QScrollArea(), hubstyle.SCROLL)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(w.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            q.QtCore.Qt.ScrollBarAlwaysOff)
        self.content = _named(w.QWidget(), hubstyle.CONTENT)
        self.column = w.QVBoxLayout(self.content)
        self.column.setObjectName("skeldarHubColumnLayout")
        self.column.setContentsMargins(0, 0, s(2), 0)
        self.column.setSpacing(s(3))
        self.column.addStretch(1)
        self.scroll.setWidget(self.content)
        self.scroll.viewport().setObjectName(hubstyle.VIEWPORT)
        top.addWidget(self.scroll, 1)
        #  the animator's own scroll wins over a glide: the wheel and the
        #  bar's arrows/page clicks trigger an action, a drag presses the
        #  slider (our own setValue does neither)
        bar = self.scroll.verticalScrollBar()
        bar.actionTriggered.connect(self._stop_glide)
        bar.sliderPressed.connect(self._stop_glide)
        #  a jump waits for the OTHER cards to finish sliding before it glides
        self._glide_card = None
        self._glide_deadline = 0.0
        self._glide_wait = q.QtCore.QTimer(self.root)
        self._glide_wait.setObjectName("skeldarHubGlideWait")
        self._glide_wait.setSingleShot(True)
        self._glide_wait.setInterval(16)
        self._glide_wait.timeout.connect(self._glide_when_settled)

        #  The lit card (2026-09-28, «активное окно подсвечивалось немного
        #  другим цветом»; then «когда я наводил мышкой на какой-то раздел у
        #  него включалась подсветка»): the card under the mouse. With the
        #  mouse off every card, the one last pressed or focused in, or
        #  jumped to (`pinned`) -- only while it is OPEN, and only after
        #  FALLBACK_MS («подсветка перепрыгивает на последний активный
        #  раздел ... картинка как бы мигает»): crossing the gap between two
        #  cards lit the pinned one for a moment. The watcher is the root's
        #  child, so it leaves the application's filters when the root is
        #  deleted; the timer likewise.
        self.active = None
        self.pinned = None
        self._fallback = q.QtCore.QTimer(self.root)
        self._fallback.setObjectName("skeldarHubFallback")
        self._fallback.setSingleShot(True)
        self._fallback.setInterval(FALLBACK_MS)
        self._fallback.timeout.connect(self._fall_back)
        #  the control under the mouse glows (2026-10-02); fading with the
        #  menu's Interface animations
        self.glow = Glower(self.root, scale, motion=lambda: self.animations)
        self._watcher = _watcher_class()(self._activate_from,
                                         self._hover_from, self._left_from,
                                         self.root)
        app = q.QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self._watcher)
        #  One message line for the whole hub (2026-10-08): every section's
        #  status writer tells it (maya_hubstyle.tell); the card marked that
        #  control (apply_marks -> Card.status_controls).
        self._message_source = None
        hubstyle.listen(self._told)

    # --------------------------------------------------------------- parts

    def px(self, value):
        return hubstyle.px(value, self.scale)

    def _call(self, key, *args):
        fn = self.cb.get(key)
        if fn:
            return fn(*args)
        return None

    def _head_button(self, name, icon_name, tip, checkable=False):
        q = qt()
        button = _named(q.QtWidgets.QToolButton(), name, "headbtn")
        button.setIcon(icon(icon_name, hubstyle.TOKENS["muted"], self.px(16),
                            on_colour=hubstyle.TOKENS["accent_text"]))
        button.setIconSize(q.QtCore.QSize(self.px(16), self.px(16)))
        button.setToolTip(tip)
        button.setCheckable(checkable)
        button.setAutoRaise(True)
        return button

    def _build_header(self):
        q = qt()
        w = q.QtWidgets
        s = self.px
        header = _named(w.QWidget(), "skeldarHubHeader", "header")
        row = w.QHBoxLayout(header)
        row.setObjectName("skeldarHubHeaderLayout")
        #  ONE row (2026-10-08, variant B): the mark, the jump icons, the
        #  hotkeys, the pin, the menu - no title, no version chip, no strip
        row.setContentsMargins(s(1), s(1), s(1), s(1))
        row.setSpacing(s(2))
        logo = _named(w.QLabel("SA"), "skeldarHubLogo", "logo")
        logo.setFixedSize(s(18), s(18))
        logo.setAlignment(q.QtCore.Qt.AlignCenter)
        #  the jumps share what the mark and the buttons leave (add_jump)
        self.jump_row = w.QHBoxLayout()
        self.jump_row.setObjectName("skeldarHubJumpRow")
        self.jump_row.setContentsMargins(0, 0, 0, 0)
        self.jump_row.setSpacing(s(1))
        self.hotkeys = self._head_button(
            "skeldarHubHotkeys", "keyboard", "Hotkey map: OFF",
            checkable=True)
        self.hotkeys.clicked.connect(lambda *_a: self._call("hotkeys"))
        #  the edge panel's pin: shown only while the hub stands in it
        #  (set_edge_mode); a checked pin keeps the panel out
        #  (`_head_button` gives it the muted icon and the accent one for its
        #  checked state: the pin turns the accent colour while it holds)
        self.pin = self._head_button("skeldarHubPin", "pin",
                                     "Keep the panel out (edge panel)",
                                     checkable=True)
        self.pin.clicked.connect(
            lambda checked=False: self._call("pin", bool(checked)))
        self.pin.setVisible(False)
        self.menu_button = self._head_button("skeldarHubMenu",
                                             "dots-vertical", "More")
        self.menu = w.QMenu(self.menu_button)
        self.menu.setObjectName("skeldarHubMenuPopup")
        for text, key in (("Check update", "check_update"),
                          ("Hotkey Editor...", "hotkey_editor"),
                          ("Interface sounds", "sounds"),
                          ("Interface animations", "animations"),
                          ("Edge panel", "edge"),
                          (None, None),
                          ("Classic look", "classic")):
            if text is None:
                self.menu.addSeparator()
                continue
            action = self.menu.addAction(text)
            if key in ("sounds", "animations", "edge"):
                #  a switch (2026-10-01, the hover sound, the card motion;
                #  2026-10-08, the edge panel): `triggered` carries the new
                #  state and is not emitted by paint_sounds /
                #  paint_animations / paint_edge
                action.setCheckable(True)
                action.triggered.connect(
                    lambda checked=False, k=key: self._call(k, bool(checked)))
                setattr(self, key + "_action", action)
                continue
            action.triggered.connect(lambda *_a, k=key: self._call(k))
        self.menu_button.setMenu(self.menu)
        self.menu_button.setPopupMode(w.QToolButton.InstantPopup)
        row.addWidget(logo)
        row.addLayout(self.jump_row, 1)
        row.addWidget(self.hotkeys)
        row.addWidget(self.pin)
        row.addWidget(self.menu_button)
        return header

    def _build_message(self):
        q = qt()
        w = q.QtWidgets
        s = self.px
        box = _named(w.QWidget(), "skeldarHubMessage", "message")
        row = w.QHBoxLayout(box)
        row.setObjectName("skeldarHubMessageLayout")
        row.setContentsMargins(s(6), s(2), s(2), s(2))
        row.setSpacing(s(4))
        #  the icon of the card that said it (2026-10-08): hidden for a
        #  message nobody's card owns ("Hotkey map: ON")
        self.message_icon = _named(w.QLabel(), "skeldarHubMessageIcon",
                                   "messageicon")
        self.message_icon.setFixedSize(s(14), s(14))
        self.message_icon.setVisible(False)
        self.message_text = _named(w.QLabel(""), "skeldarHubMessageText",
                                   "messagetext")
        self.message_text.setWordWrap(True)
        self.message_text.setSizePolicy(w.QSizePolicy.Ignored,
                                        w.QSizePolicy.Preferred)
        #  three lines at most; the tooltip holds the whole text (`say`)
        lines = self.message_text.fontMetrics().lineSpacing()
        self.message_text.setMaximumHeight(3 * lines + 2)
        self.message_close = self._head_button("skeldarHubMessageClose", "x",
                                               "Hide")
        self.message_close.clicked.connect(lambda *_a: box.setVisible(False))
        row.addWidget(self.message_icon, 0, q.QtCore.Qt.AlignTop)
        row.addWidget(self.message_text, 1)
        row.addWidget(self.message_close, 0, q.QtCore.Qt.AlignTop)
        box.setVisible(False)
        return box

    # ----------------------------------------------------------------- api

    def add_group(self, key, label):
        q = qt()
        group = _named(q.QtWidgets.QLabel(label), "skeldarHubGroup_" + key,
                       "grouplabel")
        group.setContentsMargins(self.px(3), self.px(2), 0, 0)
        self.column.insertWidget(self.column.count() - 1, group)
        return group

    def add_card(self, key, label, icon_name, colour, chip, collapsed=False):
        card = Card(key, label, icon_name, colour, chip, self.scale,
                    collapsed=collapsed,
                    on_toggle=lambda k, c: self._call("toggled", k, c),
                    motion=lambda: self.animations)
        self.column.insertWidget(self.column.count() - 1, card.frame)
        self.cards[key] = card
        return card

    def add_jump(self, key, label, icon_name, colour):
        q = qt()
        button = _named(q.QtWidgets.QToolButton(), "skeldarHubJump_" + key,
                        "jump")
        button.setIcon(icon(icon_name, colour, self.px(16)))
        button.setIconSize(q.QtCore.QSize(self.px(16), self.px(16)))
        button.setToolTip(label)
        button.setAutoRaise(True)
        button.setSizePolicy(q.QtWidgets.QSizePolicy.Expanding,
                             q.QtWidgets.QSizePolicy.Fixed)
        button.setMinimumWidth(self.px(16))
        button.clicked.connect(lambda *_a, k=key: self._call("jump", k))
        self.jump_row.addWidget(button)
        self.jumps[key] = button
        self._jump_colour[key] = colour
        self._jump_icon[key] = icon_name
        return button

    def finish(self, sheet):
        self.root.setStyleSheet(sheet)

    def say(self, text, state=None, source=None):
        """The message line: shown while it holds text; `source` a card key
        puts that card's icon at its left. The whole text is the tooltip
        (the line shows three lines at most)."""
        self.message_text.setText(text or "")
        self.message_text.setToolTip(text or "")
        card = self.cards.get(source) if source else None
        if card is not None:
            self.message_icon.setPixmap(pixmap(card.icon_name, card.colour,
                                               self.px(14)))
        self.message_icon.setVisible(card is not None and bool(text))
        self._message_source = source if text else None
        self.message.setVisible(bool(text))
        if state is not None:
            self.set_state(state)

    def _told(self, control, text, viewport):
        """The relay: a section's status control said `text`
        (maya_hubstyle.tell). The card that marked that control owns the
        line while it holds text; an empty text from the card that owns it
        clears the line, from any other it leaves it alone."""
        if not self.alive():
            hubstyle.unlisten(self._told)
            return
        key = next((k for k, card in self.cards.items()
                    if control in card.status_controls), None)
        if key is None:
            return
        if text:
            self.say(text, source=key)
        elif self._message_source == key:
            self.say("")
        self._call("told", key, text, viewport)

    def set_state(self, state):
        """The update jump's colour: "new" accent, "ok" ok, else its group's
        (2026-10-08: the version chip is gone from the compact header)."""
        button = self.jumps.get("update")
        if button is None:
            return
        button.setProperty("skState", state or "")
        tokens = hubstyle.TOKENS
        colour = {"new": tokens["accent"], "ok": tokens["ok"]}.get(
            state or "", self._jump_colour.get("update", tokens["muted"]))
        button.setIcon(icon(self._jump_icon.get("update", "refresh"), colour,
                            self.px(16)))
        repolish(button)

    def set_version(self, text, tooltip, state=None):
        """The installed build, as the update jump's tooltip."""
        button = self.jumps.get("update")
        if button is not None:
            button.setToolTip("Update - " + (tooltip or text or ""))
        if state is not None:
            self.set_state(state)

    def paint_edge(self, on):
        """The menu's Edge panel row shows `on` (no callback)."""
        self.edge_action.setChecked(bool(on))

    def set_edge_mode(self, on):
        """The hub stands in the edge panel (`on`): the pin is shown."""
        self.pin.setVisible(bool(on))
        if not on:
            self.pin.setChecked(False)
        self.paint_edge(on)

    def paint_hotkeys(self, active):
        self.hotkeys.setChecked(bool(active))
        self.hotkeys.setToolTip("Hotkey map: " + ("ON" if active else "OFF")
                                + " - press to switch")

    def paint_sounds(self, on):
        """The menu's Interface sounds row shows `on` (no callback)."""
        self.sounds_action.setChecked(bool(on))

    def paint_animations(self, on):
        """The cards slide and a jump glides (`on`) or everything is
        instant; the menu's row shows it (no callback)."""
        self.animations = bool(on)
        self.animations_action.setChecked(self.animations)
        if not self.animations:
            self._stop_glide()
            self.glow.finish()

    def set_active(self, key):
        """Card `key` is the one worked in (None: none): pinned and lit -
        and, when that is a CHANGE, flashed (2026-10-01); a press inside the
        card already chosen does not flash again."""
        self._fallback.stop()
        key = key if key in self.cards else None
        changed = key is not None and key != self.pinned
        self.pinned = key
        self._light(self.pinned)
        if changed:
            self.cards[key].pulse(animate=self.animations)

    def resting(self):
        """What is lit with the mouse off every card: the pinned card if it
        is open, else none."""
        card = self.cards.get(self.pinned) if self.pinned else None
        if card is not None and not card.collapsed():
            return self.pinned
        return None

    def _fall_back(self):
        self._light(self.resting())

    def _light(self, key):
        """Light card `key` (None: none), the previous one back to plain:
        cross-fading when the switch allows it (the card paints its light,
        CardFrame; `skActive` says at once which card is lit)."""
        key = key if key in self.cards else None
        if key == self.active:
            return
        for other in (self.active, key):
            card = self.cards.get(other) if other else None
            if card is not None:
                card.frame.setProperty("skActive", other == key)
                card.set_lit(other == key, animate=self.animations)
        self.active = key

    def card_of(self, widget):
        """The key of the card holding `widget`, or None."""
        q = qt()
        if not isinstance(widget, q.QtWidgets.QWidget):
            return None
        if widget is not self.root and not self.root.isAncestorOf(widget):
            return None                     # most of Maya: one walk, out
        for key, card in self.cards.items():
            if card.frame is widget or card.frame.isAncestorOf(widget):
                return key
        return None

    def _activate_from(self, widget):
        key = self.card_of(widget)
        if key is not None:
            self.set_active(key)

    def _hover_from(self, widget):
        """The mouse entered `widget`: its card lit at once; off every card,
        the resting light after FALLBACK_MS -- entering another card first
        cancels it, so a gap between cards lights nothing in between. A
        clickable control of ours calls back "hover" (the sound) and glows
        (`glow`)."""
        key = self.card_of(widget)
        if key is not None:
            self._fallback.stop()
            self._light(key)
        elif self.active != self.resting():
            self._fallback.start()
        if sounding(widget, self.root):
            self._call("hover")
        self.glow.enter(widget)

    def _left_from(self, widget):
        """The mouse left the hub (to another window, where no Enter of
        ours arrives): the resting light, after the same pause. The control
        it left stops glowing."""
        self.glow.leave(widget)
        if widget is self.root and self.active != self.resting():
            self._fallback.start()

    def scroll_to(self, key, animate=False):
        """Card `key` to the top of the scroll (as far as the bar goes): at
        once, or GLIDING when `animate` (the animator's move), the switch
        and the screen allow it (2026-10-01). A glide waits for the OTHER
        cards to finish sliding (`_glide_when_settled`), then eases toward
        the card's place as far as the bar reaches -- both read live, the
        chosen card's own opening growing the reach. Answers the card's
        offset now."""
        card = self.cards.get(key)
        if card is None:
            return None
        self._stop_glide()
        offset = card.frame.y()
        bar = self.scroll.verticalScrollBar()
        if not (animate and self.animations and self.root.isVisible()):
            bar.setValue(offset)
            return offset
        self._glide_card = card
        self._glide_deadline = time.monotonic() + GLIDE_WAIT_S
        self._glide_when_settled()
        return offset

    def _glide_when_settled(self):
        """Start the glide once no other card is sliding. Aimed while cards
        shut above the chosen one, it climbed toward the card's place while
        the scroll's range shrank under it and was pulled back by the clamp
        (measured live 2026-10-01: a jump to Studio with three cards open
        above ended on the range's 207 after passing it)."""
        card = self._glide_card
        if card is None or not _valid(card.frame):
            self._glide_card = None
            return
        moving = [c for c in self.cards.values()
                  if c is not card and c.sliding()]
        if moving and time.monotonic() < self._glide_deadline:
            self._glide_wait.start()
            return
        self._glide_card = None
        q = qt()
        start = self.scroll.verticalScrollBar().value()
        glide = q.QtCore.QVariantAnimation(self.root)
        glide.setObjectName("skeldarHubGlide")
        glide.setStartValue(0.0)
        glide.setEndValue(1.0)
        #  never over before the chosen card has finished opening: its own
        #  opening (1.5 times slower than a shutting since the same evening)
        #  lengthens the range, and a glide that ended first stopped short
        #  of a card near the bottom
        remaining = 0
        if card.sliding():
            remaining = card._anim.duration() - card._anim.currentTime()
        glide.setDuration(max(hubmotion.SCROLL_MS, remaining))
        glide.valueChanged.connect(
            lambda value: self._glide_tick(card, start, value))
        glide.finished.connect(lambda: self._glide_done(card))
        self._glide = glide
        glide.start()

    def _glide_tick(self, card, start, value):
        if not _valid(card.frame):
            self._stop_glide()
            return
        bar = self.scroll.verticalScrollBar()
        target = min(card.frame.y(), bar.maximum())
        bar.setValue(int(round(
            hubmotion.lerp(start, target, hubmotion.ease(value)))))

    def _glide_done(self, card):
        self._stop_glide()
        if not _valid(card.frame):
            return
        self._land(card)
        #  The scroll area widens its range on a LayoutRequest of its own,
        #  after this: a glide ending as its card finished opening was
        #  clamped by the old maximum (663 against the card's 969 offscreen)
        #  and stayed there. Land again once the range has caught up.
        qt().QtCore.QTimer.singleShot(0, self.root, lambda: self._land(card))

    def _land(self, card):
        """The bar on the card, unless the card is gone or a new glide (or
        the animator's own scroll, which stops one) took over."""
        if self._glide is None and self._glide_card is None \
                and _valid(card.frame):
            self.scroll.verticalScrollBar().setValue(card.frame.y())

    def _stop_glide(self, *_args):
        """No glide any more: the animator's own scroll (the wheel, the
        bar), another jump, the switch off, the end."""
        self._glide_card = None
        if _valid(self._glide_wait):
            self._glide_wait.stop()
        glide, self._glide = self._glide, None
        if glide is not None:
            try:
                glide.valueChanged.disconnect()
                glide.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            glide.stop()
            glide.deleteLater()

    def alive(self):
        q = qt()
        try:
            return bool(q.shiboken.isValid(self.root))
        except Exception:                                    # noqa: BLE001
            return False

    def destroy(self):
        """Delete the root NOW (not deferred): a classic build right after
        must not meet the controls' names still standing."""
        hubstyle.unlisten(self._told)
        self.glow.stop()
        if not self.alive():
            return
        q = qt()
        self.root.setParent(None)
        q.shiboken.delete(self.root)


# ------------------------------------------------------------------- marks

def _luminance(hex_colour):
    """Relative brightness 0..1 of "#rrggbb" (Rec. 709 weights)."""
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _swatch_sheet(hex_colour, radius, scale):
    #  a colour's name readable on it: dark on the light ones, light on
    #  the dark ones (blue and violet)
    text = (hubstyle.TOKENS["panel"] if _luminance(hex_colour) > 0.45
            else hubstyle.TOKENS["text"])
    return ("QPushButton {{ background: {0}; border: none; border-radius: "
            "{1}px; padding: 0px; color: {2}; }} QPushButton:hover {{ border: "
            "{3}px solid {4}; }}").format(hex_colour, radius, text,
                                          hubstyle.px(2, scale),
                                          hubstyle.TOKENS["text"])


def _fill_class():
    """An event filter keeping a widget of ours over the whole of another."""
    if "fill" not in _CLASSES:
        q = qt()

        class Fill(q.QtCore.QObject):

            def __init__(self, cover, parent=None):
                super(Fill, self).__init__(parent)
                self._cover = cover

            def eventFilter(self, obj, event):             # noqa: N802
                if event.type() == q.QtCore.QEvent.Resize:
                    self._cover.setGeometry(obj.rect())
                return False

        _CLASSES["fill"] = Fill
    return _CLASSES["fill"]


def ghost_class():
    """The drag ghost the hub's drags share: a pixmap riding the cursor with a
    caption pill under it naming what a release would do - the accent where
    it lands, danger where it does not. The weapon inventory's since
    2026-09-29, the Characters portrait grid's too since 2026-09-30.

    `icon_w` / `icon_h` are physical px; `anchor` is where the cursor sits on
    the icon (fractions of its width and height); `backdrop` is a token
    painted rounded behind the icon, or None. `name` is the objectName an
    owner finds its ghosts by (an update's show() deletes an older build's)."""
    if "ghost" not in _CLASSES:
        q = qt()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        Qt = QtCore.Qt

        def colour(name):
            return QtGui.QColor(hubstyle.TOKENS[name])

        def font(px):
            f = QtGui.QFont()
            f.setPixelSize(max(1, int(round(px))))
            return f

        class Ghost(QtWidgets.QWidget):

            def __init__(self, pixmap, icon_w, icon_h, k, anchor=(0.5, 0.25),
                         name="skeldarDragGhost", backdrop=None):
                QtWidgets.QWidget.__init__(
                    self, None, Qt.ToolTip | Qt.FramelessWindowHint
                    | Qt.WindowStaysOnTopHint)
                self.setObjectName(name)
                self.setAttribute(Qt.WA_TranslucentBackground)
                self.setAttribute(Qt.WA_TransparentForMouseEvents)
                self.setAttribute(Qt.WA_ShowWithoutActivating)
                self.pixmap, self.k = pixmap, float(k or 1.0)
                self.icon_w, self.icon_h = int(icon_w), int(icon_h)
                self.anchor, self.backdrop = anchor, backdrop
                self.text, self.good = "", True
                self._resize()

            def _caption_width(self):
                if not self.text:
                    return 0
                metrics = QtGui.QFontMetrics(font(12 * self.k))
                return metrics.horizontalAdvance(self.text) + int(16 * self.k)

            def _resize(self):
                width = max(self.icon_w, self._caption_width())
                self.resize(width, self.icon_h + int(26 * self.k))

            def set_caption(self, text, good):
                if (text, good) != (self.text, self.good):
                    self.text, self.good = text, good
                    self._resize()
                    self.update()

            def follow(self, point):
                """The cursor on the icon's anchor; the caption hangs below."""
                left = (self.width() - self.icon_w) // 2
                self.move(point.x() - left - int(self.icon_w * self.anchor[0]),
                          point.y() - int(self.icon_h * self.anchor[1]))

            def paintEvent(self, _event):                    # noqa: N802
                p = QtGui.QPainter(self)
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                box = QtCore.QRect((self.width() - self.icon_w) // 2, 0,
                                   self.icon_w, self.icon_h)
                radius = 6 * self.k
                p.setOpacity(0.85)
                if self.backdrop:
                    p.setPen(Qt.NoPen)
                    p.setBrush(colour(self.backdrop))
                    p.drawRoundedRect(QtCore.QRectF(box), radius, radius)
                inset = int(2 * self.k)
                inner = box.adjusted(inset, inset, -inset, -inset)
                if not self.pixmap.isNull() and inner.width() > 0 \
                        and inner.height() > 0:
                    size = self.pixmap.size().scaled(inner.size(),
                                                     Qt.KeepAspectRatio)
                    target = QtCore.QRect(
                        inner.x() + (inner.width() - size.width()) // 2,
                        inner.y() + (inner.height() - size.height()) // 2,
                        size.width(), size.height())
                    p.drawPixmap(target, self.pixmap)
                p.setOpacity(1.0)
                if self.text:
                    cw = self._caption_width()
                    cap = QtCore.QRectF((self.width() - cw) // 2,
                                        self.icon_h + int(3 * self.k), cw,
                                        int(21 * self.k))
                    edge = max(1.0, self.k)
                    shape = cap.adjusted(edge / 2, edge / 2, -edge / 2,
                                         -edge / 2)
                    p.setPen(QtGui.QPen(colour("accent" if self.good
                                               else "danger"), edge))
                    p.setBrush(colour("card"))
                    p.drawRoundedRect(shape, radius, radius)
                    p.setFont(font(12 * self.k))
                    p.setPen(colour("text" if self.good else "muted"))
                    p.drawText(cap, Qt.AlignCenter, self.text)
                p.end()

        _CLASSES["ghost"] = Ghost
    return _CLASSES["ghost"]


def build_menu(parent, actions):
    """A right-button menu over `parent`: `actions` is a list of (label,
    callable), a None callable showing the row disabled (its label says why),
    and None for a separator. Returns (menu, [(QAction, callable)]). The hub's
    stylesheet reaches it through `parent` (its QMenu rules). The Weapons
    inventory's and the Characters grid's since 2026-09-30 (Open scene)."""
    menu = qt().QtWidgets.QMenu(parent)
    rows = []
    for item in actions:
        if item is None:
            menu.addSeparator()
            continue
        label, action = item
        row = menu.addAction(label)
        row.setEnabled(action is not None)
        rows.append((row, action))
    return menu, rows


def run_menu(parent, point, actions):
    """`build_menu` shown at the global `point`; the picked row's callable is
    run and what it returns handed back (None when nothing was picked)."""
    if not actions:
        return None
    menu, rows = build_menu(parent, actions)
    try:
        picked = menu.exec(point)
    finally:
        menu.deleteLater()
    for row, action in rows:
        if picked is row and action is not None:
            return action()
    return None


def _spread(row, scale=1.0):
    """The segments of a Maya rowLayout share its width equally.

    Measured 2026-09-28: the rowLayout's layout is `QmayaRowLayout` (a
    QHBoxLayout underneath) and it places its children at their own widths
    whatever their stretch or size policy says -- the segments packed to
    the left of their track. A minimum width does move them, and would
    also stop the dock from ever getting narrower. So the buttons go into
    a row of OURS laid over the track (kept over it on every resize), with
    equal stretches; the track keeps no minimum width of theirs. Maya
    finds a moved control by name as before (the subtitle's move proved
    it). `row` stays referenced while its children are used."""
    q = qt()
    w = q.QtWidgets
    buttons = [child for child in row.children()
               if isinstance(child, w.QAbstractButton)]
    if not buttons:
        return 0
    cover = _named(w.QWidget(row), row.objectName() + "_skinSegments")
    box = w.QHBoxLayout(cover)
    box.setObjectName(row.objectName() + "_skinSegmentsLayout")
    inset = hubstyle.px(2, scale)
    box.setContentsMargins(inset, inset, inset, inset)
    box.setSpacing(inset)
    height = 0
    for button in buttons:
        button.setSizePolicy(w.QSizePolicy.Expanding, w.QSizePolicy.Preferred)
        box.addWidget(button, 1)
        height = max(height, button.sizeHint().height())
    row.setMinimumHeight(height + 2 * inset)
    watcher = _fill_class()(cover, cover)
    row.installEventFilter(watcher)
    cover.setGeometry(row.rect())
    cover.show()
    return len(buttons)


def apply_marks(marks, card, scale):
    """Turn a builder's marks into the skin: properties, icons, swatches,
    subtitles moved into `card`'s header. Returns how many were applied."""
    applied = 0
    size = hubstyle.px(15, scale)
    for mark in marks:
        try:
            if _apply_mark(mark, card, scale, size):
                applied += 1
        except Exception:                                    # noqa: BLE001
            #  one control that will not take its look must not cost the
            #  whole skin (the hub would fall back to classic)
            import traceback
            print("SkeldarAnim hub: no look for {0} ({1})".format(
                mark.name, mark.role))
            print(traceback.format_exc())
    #  The segment tracks last: their buttons have their own marks applied
    #  by now, and move into the skin's row with them (_spread).
    for mark in marks:
        if mark.role != "segments":
            continue
        try:
            row = find(mark.name, True)
            if row is not None:
                _spread(row, scale)
        except Exception:                                    # noqa: BLE001
            import traceback
            print(traceback.format_exc())
    return applied


def _apply_mark(mark, card, scale, size):
    """One mark onto its control; False when the control is not there."""
    q = qt()
    widget = find(mark.name, mark.layout)
    if widget is None:
        return False
    if mark.role == "subtitle":
        card.add_subtitle(widget)
        return True
    if mark.role == "swatchonly":
        for child in widget.findChildren(q.QtWidgets.QWidget):
            if child.objectName() in ("slider", "color"):
                child.setVisible(False)
        widget.setProperty("skRole", "swatchonly")
        return True
    widget.setProperty("skRole", mark.role)
    if mark.role == "inset":
        #  A plain QWidget paints no stylesheet background unless asked to
        #  (2026-10-02, the Connect block); its own layout gets the padding.
        widget.setAttribute(q.QtCore.Qt.WA_StyledBackground, True)
        layout = widget.layout()
        if layout is not None:
            pad = hubstyle.px(8, scale)
            layout.setContentsMargins(pad, pad, pad, pad)
        return True
    if mark.role == "segments":
        #  after the segment marks (they come later in the list): see
        #  apply_marks
        return True
    if mark.role == "segment":
        widget.setSizePolicy(q.QtWidgets.QSizePolicy.Expanding,
                             q.QtWidgets.QSizePolicy.Preferred)
    if mark.role == "swatch":
        side = min(widget.maximumWidth(), widget.maximumHeight())
        radius = (side // 2 if side <= hubstyle.px(24, scale)
                  else hubstyle.px(6, scale))
        widget.setStyleSheet(_swatch_sheet(mark.colour, radius, scale))
        return True
    if mark.icon:
        colour = hubstyle.TOKENS[_ICON_COLOUR.get(mark.role, "text2")]
        widget.setProperty("icon", icon(mark.icon, colour, size))
        widget.setProperty("iconSize", q.QtCore.QSize(size, size))
    return True
