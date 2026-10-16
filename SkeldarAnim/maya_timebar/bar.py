"""The Time Bar's strip (2026-10-16): mockup A, one bar.

Previous key, play, next key | the timeline (the animation range; the playback
range a lit band with two handles; the selection's keys; the playhead) | the
current frame | fps | Auto key | the active layer. The widget talks to Maya only
through a `link` (scene.py's functions in Maya, a fake in the tests), and the jobs
find the strip again through the module state - never a held wrapper (trap 135).
"""

import traceback

from . import CONTROL, look, _state

ROOT_NAME = "skeldarTimeBarRoot"
PAD = 12            # logical px either side of the track (the grips live there)
TRACK_H = 32
TIMER_MS = 250


class Link(object):
    """The strip's road into Maya: scene.py, plus going back to Maya's slider."""

    def __getattr__(self, name):
        from . import scene
        return getattr(scene, name)

    def back_to_maya(self):
        import maya.cmds as cmds
        from . import hide
        message = hide()
        cmds.inViewMessage(assistMessage=message, position="topCenter", fade=True)


def _tokens():
    import maya_hubstyle
    return maya_hubstyle.TOKENS


def stylesheet(tokens, ui):
    px = lambda v: "%dpx" % max(1, int(round(v * ui)))              # noqa: E731
    return (
        "QWidget#{root} {{ background: {panel}; }}"
        "QToolButton#skeldarTimeBarButton {{ border: none; border-radius: {r5}; padding: {p2}; }}"
        "QToolButton#skeldarTimeBarButton:hover {{ background: {hover}; }}"
        "QToolButton#skeldarTimeBarPlay {{ border: none; border-radius: {r5}; background: {accent};"
        " padding: {p2}; }}"
        "QToolButton#skeldarTimeBarPlay:hover {{ background: {accent_hover}; }}"
        "QLineEdit#skeldarTimeBarFrame {{ background: {field}; color: {accent_text};"
        " border: 1px solid {accent}; border-radius: {r5}; padding: 0 {p6};"
        " font-family: Consolas, monospace; font-weight: 600; }}"
        "QToolButton#skeldarTimeBarChip {{ background: {card}; color: {muted};"
        " border: 1px solid {line}; border-radius: {r12}; padding: {p2} {p10}; }}"
        "QToolButton#skeldarTimeBarChip:hover {{ background: {hover}; color: {text}; }}"
        "QToolButton#skeldarTimeBarChip:checked {{ color: {text}; border-color: {rec}; }}"
        "QToolButton#skeldarTimeBarChip::menu-indicator {{ image: none; width: 0; }}"
        "QFrame#skeldarTimeBarSep {{ background: {line}; }}"
        "QMenu {{ background: {card}; color: {text}; border: 1px solid {line}; padding: {p4}; }}"
        "QMenu::item {{ padding: {p4} {p12}; border-radius: {r4}; }}"
        "QMenu::item:selected {{ background: {hover}; }}"
    ).format(root=ROOT_NAME, rec=REC, p2=px(2), p4=px(4), p6=px(6), p10=px(10), p12=px(12),
             r4=px(4), r5=px(5), r12=px(12), **tokens)


REC = "#e0524a"            # Auto key's red, Maya's own record colour toned to the palette
BREAKDOWN = "#6fb7c9"
HIGHLIGHT = "#7fa9e6"      # the hub's tool blue


def classes():
    """(Strip, Timeline), made on first use (no Qt at import)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt

    def colour(hex_, alpha=255):
        c = QtGui.QColor(hex_)
        c.setAlpha(alpha)
        return c

    def glyph(kind, side, hex_):
        """A transport icon drawn: 'prev' / 'next' (bar + triangle), 'play', 'pause'."""
        image = QtGui.QPixmap(side, side)
        image.fill(Qt.transparent)
        p = QtGui.QPainter(image)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(colour(hex_))
        s = side / 16.0
        tri = lambda pts: p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x * s, y * s) for x, y in pts]))  # noqa: E731
        if kind == "play":
            tri([(5, 3), (13, 8), (5, 13)])
        elif kind == "pause":
            p.drawRoundedRect(QtCore.QRectF(4 * s, 3 * s, 3 * s, 10 * s), s, s)
            p.drawRoundedRect(QtCore.QRectF(9 * s, 3 * s, 3 * s, 10 * s), s, s)
        elif kind == "prev":
            p.drawRect(QtCore.QRectF(3 * s, 3 * s, 2 * s, 10 * s))
            tri([(13, 3), (13, 13), (6, 8)])
        else:
            p.drawRect(QtCore.QRectF(11 * s, 3 * s, 2 * s, 10 * s))
            tri([(3, 3), (3, 13), (10, 8)])
        p.end()
        return QtGui.QIcon(image)

    class Timeline(QtWidgets.QWidget):

        def __init__(self, strip):
            super(Timeline, self).__init__(strip)
            self.strip = strip
            self.setObjectName("skeldarTimeBarTimeline")
            self.setMinimumWidth(int(160 * strip.ui))
            self.setFixedHeight(int(TRACK_H * strip.ui))
            self.setCursor(Qt.SizeHorCursor)
            self.drag = None            # (kind, start frame, the track at the press)

        # geometry ---------------------------------------------------------
        def track(self):
            s = self.strip.state
            pad = PAD * self.strip.ui
            return look.Track(s["a0"], s["a1"], pad, self.width() - pad)

        # painting ---------------------------------------------------------
        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001 - never a paint loop of tracebacks
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            t = self.drag[2] if self.drag and self.drag[0] in ("a0", "a1") else self.track()
            tk, ui, s = self.strip.tokens, self.strip.ui, self.strip.state
            w, h = float(self.width()), float(self.height())
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
            p.setBrush(colour(tk["track"]))
            p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, w - 1, h - 1), 6 * ui, 6 * ui)
            p.setClipRect(QtCore.QRectF(1, 1, w - 2, h - 2))
            p.setPen(Qt.NoPen)
            # the playback band
            x0, x1 = t.x(s["p0"]), t.x(s["p1"])
            p.setBrush(colour(tk["accent"], 0x22))
            p.drawRect(QtCore.QRectF(x0, 2 * ui, x1 - x0, h - 4 * ui))
            # the highlight
            sel = s.get("highlight")
            if sel:
                hx0, hx1 = t.x(sel[0]), t.x(sel[1])
                p.setBrush(colour(HIGHLIGHT, 0x3c))
                p.drawRect(QtCore.QRectF(hx0, 1, max(hx1 - hx0, 2 * ui), h - 2))
                p.setBrush(colour(HIGHLIGHT, 0xc0))
                p.drawRect(QtCore.QRectF(hx0, 1, 1 * ui, h - 2))
                p.drawRect(QtCore.QRectF(hx1 - 1 * ui, 1, 1 * ui, h - 2))
            # the band's handles
            p.setBrush(colour(tk["accent"]))
            for x in (x0, x1 - 3 * ui):
                p.drawRoundedRect(QtCore.QRectF(x, 2 * ui, 3 * ui, h - 4 * ui), 1.5 * ui, 1.5 * ui)
            # the grips (the animation range)
            p.setBrush(colour(tk["faint"]))
            for gx in (PAD * ui * 0.35, w - PAD * ui * 0.35):
                for gy in (-4, 0, 4):
                    p.drawEllipse(QtCore.QPointF(gx, h / 2 + gy * ui), 1.1 * ui, 1.1 * ui)
            # the ruler
            font = QtGui.QFont("Consolas")
            font.setPixelSize(max(8, int(10 * ui)))
            p.setFont(font)
            metrics = QtGui.QFontMetricsF(font)
            ry = h - 3 * ui
            for frame, kind in look.ticks(t, ui):
                x = round(t.x(frame))
                tall = {"label": 8, "mid": 5, "tick": 3}[kind] * ui
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["muted"] if kind == "label" else tk["line"]))
                p.drawRect(QtCore.QRectF(x, ry - tall, max(1.0, ui * 0.75), tall))
                if kind == "label":
                    text = look.frame_text(frame)
                    if x + 3 * ui + metrics.horizontalAdvance(text) <= w - 2 * ui:
                        p.setPen(colour(tk["faint"]))
                        p.drawText(QtCore.QPointF(x + 3 * ui, ry - 1 * ui), text)
            # the keys
            p.setPen(Qt.NoPen)
            ky = 4 * ui
            for frames, hex_ in ((self.strip.keys, tk["accent"]), (self.strip.breakdowns, BREAKDOWN)):
                p.setBrush(colour(hex_))
                for frame in frames:
                    if t.v0 - 1 <= frame <= t.v1 + 1:
                        p.drawRoundedRect(QtCore.QRectF(t.x(frame) - 1.5 * ui, ky, 3 * ui, 15 * ui),
                                          1.5 * ui, 1.5 * ui)
            # the playhead
            x = t.x(s["now"])
            p.setBrush(colour(tk["accent"]))
            p.drawRect(QtCore.QRectF(x - 1 * ui, 0, 2 * ui, h))
            text = look.frame_text(s["now"])
            bold = QtGui.QFont(font)
            bold.setBold(True)
            p.setFont(bold)
            tw = QtGui.QFontMetricsF(bold).horizontalAdvance(text) + 10 * ui
            fx = min(max(x - tw / 2, 1), w - tw - 1)
            p.drawRoundedRect(QtCore.QRectF(fx, 0, tw, 14 * ui), 3 * ui, 3 * ui)
            p.setPen(colour(tk["on_accent"]))
            p.drawText(QtCore.QRectF(fx, 0, tw, 14 * ui), Qt.AlignCenter, text)
            p.end()

        # input ------------------------------------------------------------
        def _x(self, event):
            return event.position().x() if hasattr(event, "position") else event.x()

        def mousePressEvent(self, event):
            if event.button() == Qt.RightButton:
                self.strip.context_menu(event)
                return
            if event.button() != Qt.LeftButton:
                return
            x, s, t = self._x(event), self.strip.state, self.track()
            if event.modifiers() & Qt.ShiftModifier:
                start = t.whole(x, lo=s["a0"], hi=s["a1"])
                self.drag = ("highlight", start, t)
                s["highlight"] = (start, start)
                self.update()
                return
            kind = look.hit(t, x, s["now"], s["p0"], s["p1"], self.strip.ui)
            self.drag = (kind, None, t)
            if kind == "now":
                if s.get("highlight"):
                    s["highlight"] = None
                    self.strip.call("set_highlight", None)
                self._scrub(x)

        def mouseMoveEvent(self, event):
            if not self.drag:
                return
            kind, start, t = self.drag
            x, s = self._x(event), self.strip.state
            if kind == "now":
                self._scrub(x)
            elif kind == "highlight":
                s["highlight"] = look.highlight(start, t.whole(x, lo=s["a0"], hi=s["a1"]))
                self.update()
            else:
                a0, a1, p0, p1 = look.dragged(kind, t.frame(x), s["a0"], s["a1"], s["p0"], s["p1"])
                s.update(a0=a0, a1=a1, p0=p0, p1=p1)
                if kind in ("p0", "p1"):
                    self.strip.call("set_ranges", a0, a1, p0, p1)
                self.update()

        def mouseReleaseEvent(self, event):
            if not self.drag or event.button() != Qt.LeftButton:
                return
            kind = self.drag[0]
            self.drag = None
            s = self.strip.state
            if kind == "highlight":
                sel = s.get("highlight")
                if not sel or sel[1] <= sel[0]:
                    s["highlight"] = None
                self.strip.call("set_highlight", s["highlight"])
            elif kind in ("a0", "a1"):
                self.strip.call("set_ranges", s["a0"], s["a1"], s["p0"], s["p1"])
            self.strip.refresh()

        def mouseDoubleClickEvent(self, event):
            t, s, x = self.track(), self.strip.state, self._x(event)
            kind = look.hit(t, x, s["now"], s["p0"], s["p1"], self.strip.ui)
            if kind not in ("p0", "p1", "a0", "a1"):
                return
            self.drag = None
            names = {"p0": "Playback start", "p1": "Playback end",
                     "a0": "Animation start", "a1": "Animation end"}
            value, ok = QtWidgets.QInputDialog.getInt(self, "Time Bar", names[kind],
                                                      int(round(s[kind])), -1000000, 1000000)
            if ok:
                a0, a1, p0, p1 = look.dragged(kind, value, s["a0"], s["a1"], s["p0"], s["p1"])
                self.strip.call("set_ranges", a0, a1, p0, p1)
                self.strip.refresh()

        def _scrub(self, x):
            s, t = self.strip.state, self.drag[2] if self.drag else self.track()
            frame = t.whole(x, lo=s["a0"], hi=s["a1"])
            if frame != s["now"]:
                s["now"] = frame
                self.strip.call("set_time", frame)
                self.strip.show_now()
            self.update()

    class Strip(QtWidgets.QWidget):

        def __init__(self, link, ui=1.0, tokens=None, parent=None):
            super(Strip, self).__init__(parent)
            self.setObjectName(ROOT_NAME)
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.link, self.ui = link, float(ui)
            self.tokens = tokens or _tokens()
            self.state = {"now": 0.0, "a0": 0.0, "a1": 120.0, "p0": 0.0, "p1": 120.0,
                          "unit": "ntsc", "auto": False, "playing": False, "highlight": None}
            self.keys, self.breakdowns = [], []
            self.keys_dirty = True
            self.setStyleSheet(stylesheet(self.tokens, self.ui))
            row = QtWidgets.QHBoxLayout(self)
            m = int(6 * self.ui)
            row.setContentsMargins(int(10 * self.ui), m, int(10 * self.ui), m)
            row.setSpacing(int(8 * self.ui))
            side = int(16 * self.ui)
            self.prev = self._button("skeldarTimeBarButton", glyph("prev", side, self.tokens["muted"]),
                                     "Previous key", lambda: self._step(False))
            self.play = self._button("skeldarTimeBarPlay", glyph("play", side, self.tokens["on_accent"]),
                                     "Play / stop", lambda: self.call("toggle_play"))
            self.next = self._button("skeldarTimeBarButton", glyph("next", side, self.tokens["muted"]),
                                     "Next key", lambda: self._step(True))
            for b in (self.prev, self.play, self.next):
                row.addWidget(b)
            self.timeline = Timeline(self)
            row.addWidget(self.timeline, 1)
            self.field = QtWidgets.QLineEdit(self)
            self.field.setObjectName("skeldarTimeBarFrame")
            self.field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.field.setFixedSize(int(58 * self.ui), int(24 * self.ui))
            self.field.setToolTip("Current frame")
            self.field.returnPressed.connect(self._typed)
            row.addWidget(self.field)
            sep = QtWidgets.QFrame(self)
            sep.setObjectName("skeldarTimeBarSep")
            sep.setFixedSize(max(1, int(self.ui)), int(20 * self.ui))
            row.addWidget(sep)
            self.fps = self._chip("Frame rate", self._fps_menu)
            self.auto = self._chip("Auto key", lambda: self.call("toggle_auto"))
            self.auto.setCheckable(True)
            self.auto.setText(u"● Auto key")
            self.layer = self._chip("Animation layer keys go to", self._layer_menu)
            for b in (self.fps, self.auto, self.layer):
                row.addWidget(b)
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(TIMER_MS)
            self.timer.timeout.connect(self.tick)
            self.refresh(keys=True, force=True)     # read once even if Maya is playing
            self.timer.start()

        def _button(self, name, icon, tip, action):
            b = QtWidgets.QToolButton(self)
            b.setObjectName(name)
            b.setIcon(icon)
            b.setIconSize(QtCore.QSize(int(16 * self.ui), int(16 * self.ui)))
            b.setFixedSize(int(26 * self.ui), int(24 * self.ui))
            b.setToolTip(tip)
            b.clicked.connect(lambda *_a: action())
            return b

        def _chip(self, tip, action):
            b = QtWidgets.QToolButton(self)
            b.setObjectName("skeldarTimeBarChip")
            b.setToolTip(tip)
            b.setFixedHeight(int(24 * self.ui))
            b.clicked.connect(lambda *_a: action())
            return b

        # Maya ---------------------------------------------------------------
        def call(self, name, *args):
            """A write to Maya; a failure goes to the Script Editor, never out of a Qt slot."""
            try:
                return getattr(self.link, name)(*args)
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                return None

        def refresh(self, keys=False, force=False):
            light = self.call("light")
            if light:
                self.state.update(light)
            if keys:
                self.keys_dirty = True
            if self.keys_dirty and (force or not self.state.get("playing")):
                found = self.call("keys")
                if found is not None:
                    self.keys, self.breakdowns = list(found[0]), list(found[1])
                    self.keys_dirty = False
            self._paint_widgets()
            self.timeline.update()

        def on_time(self):
            """timeChanged: the playhead only (playback calls it every frame)."""
            now = self.call("now")
            if now is not None and now != self.state["now"]:
                self.state["now"] = now
                self.show_now()
                self.timeline.update()

        def tick(self):
            try:
                if not self.timeline.drag:
                    self.refresh()
            except Exception:                                # noqa: BLE001 - four times a second
                if not getattr(self, "_tick_failed", False):
                    print(traceback.format_exc())
                self._tick_failed = True

        def show_now(self):
            if not self.field.hasFocus():
                self.field.setText(look.frame_text(self.state["now"]))

        def _paint_widgets(self):
            s, side = self.state, int(16 * self.ui)
            self.show_now()
            self.play.setIcon(glyph("pause" if s["playing"] else "play", side, self.tokens["on_accent"]))
            self.fps.setText(look.fps_label(s["unit"]))
            self.auto.setChecked(bool(s["auto"]))
            label = self.call("layer_label") or ""
            self.layer.setText(label + u" ▾" if label else "No layers")

        def _typed(self):
            try:
                frame = float(self.field.text())
            except ValueError:
                self.show_now()
                return
            self.call("set_time", frame)
            self.field.clearFocus()
            self.refresh()

        def _step(self, forward):
            self.call("step_key", forward, self.keys + self.breakdowns)
            self.refresh()

        def _menu(self, button, rows):
            import maya_hubqt
            return maya_hubqt.run_menu(button, button.mapToGlobal(button.rect().bottomLeft()), rows)

        def _fps_menu(self):
            rows = [(text + " fps", (lambda u=unit: self.call("set_unit", u)))
                    for text, unit in look.FPS]
            self._menu(self.fps, rows)
            self.refresh(keys=True)

        def _layer_menu(self):
            found = self.call("layers") or []
            if not found:
                return
            rows = [((u"✓ " if sel else "   ") + label, (lambda n=name: self.call("pick_layer", n)))
                    for name, label, sel in found]
            self._menu(self.layer, rows)
            self.refresh(keys=True)

        def context_menu(self, event):
            import maya_hubqt
            point = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            maya_hubqt.run_menu(self, point, [("Back to Maya's time slider",
                                               lambda: self.call("back_to_maya"))])

    return Strip, Timeline


def make(link=None, ui=1.0, tokens=None, parent=None):
    strip_class, _timeline = classes()
    return strip_class(link or Link(), ui, tokens, parent)


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


def _start_jobs():
    import maya.cmds as cmds
    from functools import partial
    jobs = []
    for event, method, args in (("timeChanged", "on_time", ()),
                                ("playbackRangeChanged", "refresh", ()),
                                ("SelectionChanged", "refresh", (True,)),
                                ("animLayerRefresh", "refresh", (True,)),
                                ("Undo", "refresh", (True,)),
                                ("Redo", "refresh", (True,))):
        try:
            jobs.append(cmds.scriptJob(event=[event, partial(_job, method, *args)], parent=CONTROL))
        except Exception:                                    # noqa: BLE001 - an event this Maya lacks
            pass
    _state()["jobs"] = jobs
    _drop_callbacks()
    try:
        import maya.api.OpenMayaAnim as oma
        _state()["callbacks"] = [oma.MAnimMessage.addAnimKeyframeEditedCallback(_keys_edited)]
    except Exception:                                        # noqa: BLE001
        pass


def build():
    """The uiScript body: the strip inside the workspaceControl."""
    import maya.cmds as cmds
    import maya_hubqt
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
    _start_jobs()
    return widget
