"""maya_hubedge - the hub as a panel sliding out of the left screen edge.

2026-10-08 (the animator: «когда я подношу мышку к левому краю экрана то
появляется наша полка когда убираю то полка скрывается»). Three windows of
ours, each a frameless Qt.Tool owned by Maya's main window (so above Maya,
never above another application, gone with Maya minimized):

    host    the panel: the work area's left edge, its full height; holds
            the SLOT, which holds the Skin's root. A slide moves the SLOT
            inside the host - no window crosses into a monitor on the
            left, nothing is laid out again per frame. The host paints the
            hub's `panel` colour and a 1 px `inset_line` down its right edge;
            the slot stops short of that line, so it always shows. Only its
            FRAME shows (a window mask): out, the frame leads and the slot
            follows close behind it (rules.reveal_at); back, both go
            together (2026-10-09, «фоновая рамка ... появляется сильно
            резко»: the host had popped up whole and the hub slid inside
            it). The spec's
            "soft shadow" is NOT drawn: a shadow wants a translucent
            top-level, and a translucent top-level holding Maya's own widgets
            is untried here (every Maya control would be composited through
            it) - the line costs nothing and marks the edge.
    sensor  2 physical px over the edge at window opacity 1/255: Qt keeps
            it layered and it still takes the mouse (CLAUDE.md trap 110;
            the Graph Overlay's ghost measured alpha 1 hit-testable).
            Shown only while the panel is hidden.
    grip    5 logical px on the host's right: drag the width (a child of the
            host, painting nothing - the host's line is under it).

Every decision is maya_edgerules'. The cursor, the buttons, the work area
and whether Maya is the active application come through constructor seams,
so a verify drives the controller without moving the animator's mouse.

Three details the rules cannot see:
  - A reveal by command (`reveal(hold=True)`) with the cursor ALREADY over
    the panel gets no Enter event - the cursor did not cross an edge. The
    visit is counted as begun right there, or the hold would outlast it
    (leaving would not release it).
  - "A press outside releases the hold" needs an application-wide event
    filter. It is installed only while a hold stands and taken off the
    moment it goes: otherwise every one of Maya's events would pass through
    a Python call for nothing. It is a child of the host (it dies with it -
    Qt clears a deleted filter from the application's list), never swallows
    an event, and does nothing once the host is gone.
  - A slide starts from where the slot STANDS: a reveal arriving while the
    panel is still sliding out turns back from there, no jump.

The controller is NOT registered by its constructor (tests build several);
the caller puts it on `sys._skeldar_hubedge` through `state()` (an install
purges our modules; trap 111), and every window is found again by its
objectName (`destroy_all`, trap 102's family). `destroy` deletes the slot and
whatever still stands in it: take the Skin's root out first.

Spec: docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md
"""

import sys

import maya_edgerules as rules
import maya_hubmotion as hubmotion
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

HOST = "skeldarAnimHubEdge"
SENSOR = "skeldarAnimHubEdgeSensor"
SLOT = "skeldarAnimHubEdgeSlot"
GRIP = "skeldarAnimHubEdgeGrip"

#  the sensor's window opacity: invisible, and still hit-testable (alpha 0
#  would let the mouse through - a layered window is transparent to the
#  mouse only where its alpha is 0)
SENSOR_OPACITY = 1.0 / 255


def state():
    """The edge panel's session state, on `sys` (an install purges our
    modules; the controller and its windows outlive them)."""
    st = getattr(sys, "_skeldar_hubedge", None)
    if st is None:
        st = {"edge": None}
        sys._skeldar_hubedge = st
    return st


def main_window():
    """Maya's main window, or None (tests, mayapy). Fetched when needed and
    never kept: a wrapper of a Maya-owned widget held across event
    processing can outlive its widget (CLAUDE.md trap 135/148)."""
    if not hubqt._maya_ui_ok():
        return None
    try:
        import maya.OpenMayaUI as omui
        q = hubqt.qt()
        ptr = omui.MQtUtil.mainWindow()
        if ptr:
            return q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
    except Exception:                                        # noqa: BLE001
        pass
    return None


def destroy_all():
    """Delete every host and sensor of ours standing, found by name (an
    older module object's included - trap 102). Returns how many."""
    q = hubqt.qt()
    if q is None or q.QtWidgets.QApplication.instance() is None:
        return 0
    count = 0
    for widget in list(q.QtWidgets.QApplication.topLevelWidgets()):
        try:
            if widget.objectName() in (HOST, SENSOR):
                widget.hide()
                widget.setParent(None)
                q.shiboken.delete(widget)
                count += 1
        except RuntimeError:
            pass
    st = getattr(sys, "_skeldar_hubedge", None)
    if st and st.get("edge") is not None:
        try:
            if not st["edge"].alive():
                st["edge"] = None
        except Exception:                                    # noqa: BLE001
            st["edge"] = None
    return count


# ------------------------------------------------------------- the seams

def _maya_work_area():
    """The work area (no taskbar) of the screen holding Maya's main window,
    physical px: (x, y, w, h)."""
    q = hubqt.qt()
    screen = None
    window = main_window()
    if window is not None:
        try:
            screen = window.screen()
        except Exception:                                    # noqa: BLE001
            screen = None
    if screen is None:
        screen = q.QtGui.QGuiApplication.primaryScreen()
    if screen is None:
        return (0, 0, 1920, 1080)
    return screen.availableGeometry().getRect()


def _qt_cursor():
    pos = hubqt.qt().QtGui.QCursor.pos()
    return (pos.x(), pos.y())


def _qt_buttons():
    q = hubqt.qt()
    return q.QtWidgets.QApplication.mouseButtons() != q.QtCore.Qt.NoButton


def _qt_app_active():
    q = hubqt.qt()
    return (q.QtGui.QGuiApplication.applicationState()
            == q.QtCore.Qt.ApplicationActive)


def _global_point(event):
    """A mouse event's global point, physical px, as ints (Qt6, else Qt5)."""
    if hasattr(event, "globalPosition"):
        point = event.globalPosition()
        return (int(round(point.x())), int(round(point.y())))
    point = event.globalPos()
    return (point.x(), point.y())


# ------------------------------------------------------------- the widgets

_CLASSES = {}


def _classes():
    """The edge's Qt classes, built once per module object (a dict like
    maya_hubqt's: Qt is imported only when an edge is built)."""
    if not _CLASSES:
        q = hubqt.qt()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

        class Sensor(QtWidgets.QWidget):
            """The strip at the edge: the cursor resting on it starts the
            dwell."""

            def __init__(self, edge, parent, flags):
                super(Sensor, self).__init__(parent, flags)
                self.edge = edge

            def enterEvent(self, event):                   # noqa: N802
                self.edge.sensor_entered()
                super(Sensor, self).enterEvent(event)

            def leaveEvent(self, event):                   # noqa: N802
                self.edge.sensor_left()
                super(Sensor, self).leaveEvent(event)

        class Host(QtWidgets.QWidget):
            """The panel's window: the hub's colour, a line on its right."""

            def __init__(self, edge, parent, flags):
                super(Host, self).__init__(parent, flags)
                self.edge = edge

            def enterEvent(self, event):                   # noqa: N802
                self.edge.host_entered()
                super(Host, self).enterEvent(event)

            def leaveEvent(self, event):                   # noqa: N802
                self.edge.host_left()
                super(Host, self).leaveEvent(event)

            def resizeEvent(self, event):                  # noqa: N802
                super(Host, self).resizeEvent(event)
                self.edge._fit_slot()

            def paintEvent(self, event):                   # noqa: N802
                #  only the frame shows (the window's mask); its line on
                #  the frame's right edge, so it slides out with it
                frame = max(1, min(self.width(), self.edge.frame))
                painter = QtGui.QPainter(self)
                try:
                    painter.fillRect(0, 0, frame, self.height(), QtGui.QColor(
                        hubstyle.TOKENS["panel"]))
                    line = self.edge._line()
                    painter.fillRect(frame - line, 0, line,
                                     self.height(), QtGui.QColor(
                                         hubstyle.TOKENS["inset_line"]))
                finally:
                    painter.end()

        class WidthGrip(QtWidgets.QWidget):
            """The host's right edge: a drag sets the panel's width, the
            release remembers it. `press/drag/release` take GLOBAL x
            (physical px), so the tests drive them without a mouse."""

            def __init__(self, edge, parent=None):
                super(WidthGrip, self).__init__(parent)
                self.edge = edge
                self._start = None
                self.setCursor(QtCore.Qt.SizeHorCursor)
                self.setToolTip("Drag to make the panel wider or narrower")

            def press(self, gx):
                self._start = (gx, self.edge.width)

            def drag(self, gx):
                if self._start is None:
                    return
                x0, width0 = self._start
                self.edge.set_width(width0 + (gx - x0) / self.edge.scale,
                                    save=False)

            def release(self):
                if self._start is not None:
                    self.edge.set_width(self.edge.width, save=True)
                self._start = None

            def mousePressEvent(self, event):              # noqa: N802
                if event.button() == QtCore.Qt.LeftButton:
                    self.press(_global_point(event)[0])
                    event.accept()
                else:
                    event.ignore()

            def mouseMoveEvent(self, event):               # noqa: N802
                self.drag(_global_point(event)[0])

            def mouseReleaseEvent(self, event):            # noqa: N802
                self.release()

        class PressWatch(QtCore.QObject):
            """An application event filter: a press anywhere is handed to
            `edge.press_at` (which asks whether it lies outside the panel).
            Never swallows the event."""

            def __init__(self, edge, parent=None):
                super(PressWatch, self).__init__(parent)
                self.edge = edge

            def eventFilter(self, obj, event):             # noqa: N802
                try:
                    if (event.type() == QtCore.QEvent.MouseButtonPress
                            and self.edge.alive()):
                        self.edge.press_at(_global_point(event))
                except Exception:                            # noqa: BLE001
                    pass
                return False

        _CLASSES.update(sensor=Sensor, host=Host, grip=WidthGrip,
                        watch=PressWatch)
    return _CLASSES


# ------------------------------------------------------------- the controller

class Edge(object):
    """The edge panel: its three windows, its timers, and the controller the
    windows' events and the timers call. Every decision is maya_edgerules'.

    `scale` is the display scale (Qt px are physical in Maya); `width` the
    panel's logical width; `motion()` whether it slides (default: the hub's
    Interface animations); `on_width(width)` is called when a drag of the
    grip ends (the caller remembers it). The seams: `work_area()` ->
    (x, y, w, h), `cursor()` -> (x, y), `buttons()` -> bool, `app_active()`
    -> bool, all physical px, default Qt's."""

    def __init__(self, scale=1.0, parent=None, width=rules.WIDTH,
                 motion=None, on_width=None, work_area=None, cursor=None,
                 buttons=None, app_active=None):
        q = hubqt.qt()
        QtCore, QtWidgets = q.QtCore, q.QtWidgets
        classes = _classes()
        self.scale = float(scale or 1.0)
        self.width = rules.clamp_width(width)
        self.motion = motion or hubmotion.enabled
        self.on_width = on_width
        self._work_area = work_area
        self.cursor = cursor or _qt_cursor
        self.buttons = buttons or _qt_buttons
        self.app_active = app_active or _qt_app_active
        self.hold = rules.Hold()
        self.pinned = False
        self._anim = None
        self._shown = False
        #  where the slot RESTS between slides: out (x 0) once a slide in has
        #  ended, off the edge otherwise. Not `_shown`, which turns True as a
        #  reveal begins - the host's first resize event arrives on its
        #  show(), and a slot put at 0 there would leave nothing to slide.
        self._rest_out = False
        #  how much of the host shows, physical px from the screen edge: the
        #  frame slides out before the hub and leaves with it (2026-10-09)
        self._frame = 0
        self._watching = False
        self.slot = self.grip = None
        if parent is None:
            parent = main_window()
        flags = QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint

        host = classes["host"](self, parent, flags)
        host.setObjectName(HOST)
        #  the panel coming out under the cursor must not take the keyboard
        #  from the viewport; a click inside still activates it
        host.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.host = host

        slot = QtWidgets.QWidget(host)
        slot.setObjectName(SLOT)
        layout = QtWidgets.QVBoxLayout(slot)
        layout.setObjectName(SLOT + "Layout")
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.slot = slot

        grip = classes["grip"](self, host)
        grip.setObjectName(GRIP)
        self.grip = grip

        sensor = classes["sensor"](
            self, parent, flags | QtCore.Qt.WindowDoesNotAcceptFocus)
        sensor.setObjectName(SENSOR)
        sensor.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        sensor.setWindowOpacity(SENSOR_OPACITY)
        self.sensor = sensor

        self.dwell = self._timer(rules.DWELL_MS, self.dwell_done)
        self.hide = self._timer(rules.HIDE_MS, self.hide_due)
        self.retry = self._timer(rules.RETRY_MS, self.hide_due)
        self._watch = classes["watch"](self, host)

        self.place()
        self.grip.raise_()
        self.host.hide()
        self.sensor.show()
        self.sensor.raise_()

    def _timer(self, ms, call):
        q = hubqt.qt()
        timer = q.QtCore.QTimer(self.host)
        timer.setSingleShot(True)
        timer.setInterval(int(ms))
        timer.timeout.connect(call)
        return timer

    # ------------------------------------------------------------ state

    @property
    def shown(self):
        """The panel is out (or sliding out)."""
        return self._shown

    def alive(self):
        return hubqt._valid(self.host)

    def sliding(self):
        return self._anim is not None

    def work_area(self):
        return self._work_area() if self._work_area else _maya_work_area()

    def _host_rect(self):
        return self.host.geometry().getRect()

    def _line(self):
        """The host's right line, physical px (1 logical)."""
        return hubstyle.px(1, self.scale)

    # ------------------------------------------------------------ geometry

    def place(self):
        """The windows' geometry from the work area: the host on its left
        edge, its full height, the sensor over that edge."""
        if not self.alive():
            return
        area = self.work_area()
        x, y, w, h = rules.panel_rect(area, self.width, self.scale)
        self.host.setGeometry(x, y, w, h)
        sx, sy, sw, sh = rules.sensor_rect(area)
        self.sensor.setGeometry(sx, sy, sw, sh)
        self._fit_slot()

    def _fit_slot(self):
        """The slot over the host (short of its line) - at 0 out, off the
        edge in, where the slide has it while one runs - and the grip on
        the host's right."""
        host, slot, grip = self.host, self.slot, self.grip
        if not (hubqt._valid(host) and slot is not None
                and hubqt._valid(slot)):
            return
        w, h = host.width(), host.height()
        if self._anim is not None:
            x = slot.x()
        else:
            x = 0 if self._rest_out else -w
            self._set_frame(w if self._rest_out else 0)
        slot.setGeometry(x, 0, max(1, w - self._line()), h)
        if grip is not None and hubqt._valid(grip):
            g = hubstyle.px(rules.GRIP_PX, self.scale)
            grip.setGeometry(w - g, 0, g, h)

    @property
    def frame(self):
        """How much of the host shows, physical px from the screen edge."""
        return self._frame

    def _set_frame(self, px):
        """Show `px` of the host from its left: a window mask (Qt never
        paints the rest), none once it is all of it. A mask of nothing is no
        mask at all to Qt, so the least is one pixel - the host is hidden at
        rest anyway."""
        host = self.host
        if not hubqt._valid(host):
            return
        w = host.width()
        px = int(max(0, min(w, round(px))))
        self._frame = px
        if px >= w:
            host.clearMask()
        else:
            q = hubqt.qt()
            host.setMask(q.QtGui.QRegion(0, 0, max(1, px), host.height()))
        host.update()

    # ------------------------------------------------------------ in, out

    def reveal(self, hold=False):
        """Bring the panel out. `hold`: by command (the shelf button, a
        hotkey, a tool's show_window) - it stays until visited or a press
        lands outside it (rules.Hold)."""
        if not self.alive():
            return
        for timer in (self.dwell, self.hide, self.retry):
            timer.stop()
        if self._shown and self._anim is None:
            self.host.raise_()
        else:
            #  a slot at rest waits off the edge (`_rest_out`), and the
            #  slide starts from where it stands
            self.place()
            self._shown = True
            self.sensor.hide()
            self.host.show()
            self.host.raise_()
            self.grip.raise_()
            self._slide(True)
        if hold:
            self.hold.start()
            #  the cursor already over the panel crossed no edge, so no
            #  Enter will come: the visit has begun
            if rules.contains(self._host_rect(), self.cursor()):
                self.hold.enter()
        self._sync_watch()

    def conceal(self):
        """Send the panel back off the edge (the sensor comes back when the
        slide ends)."""
        if not self.alive():
            return
        for timer in (self.dwell, self.hide, self.retry):
            timer.stop()
        if not self._shown:
            return
        self._shown = False
        self.hold = rules.Hold()
        self._sync_watch()
        self._slide(False)

    def _slide(self, showing):
        """Out: the frame first, then the hub inside it (2026-10-09: the
        frame had popped up whole and the hub slid in it). Back: the hub and
        the frame together - no empty frame is left standing. Each phase
        starts from where it stands, so a turn back part way never jumps."""
        self._stop_anim()
        width = max(1, self.host.width())
        try:
            moving = bool(self.motion())
        except Exception:                                    # noqa: BLE001
            moving = False
        if not moving:
            self._slide_done(showing)
            return
        hub_out = self.slot.x() > -width
        if showing and not hub_out and self._frame <= 0:
            #  from rest: one timeline, the frame leading, the hub close
            #  behind it (rules.reveal_at)
            self._reveal_from_rest(width)
            return
        if showing and not hub_out and self._frame < width:
            #  a frame part way out (a hide turned back): it finishes, then
            #  the hub
            self._animate(rules.FRAME_MS, width, True, self._frame, width,
                          self._set_frame, lambda: self._slide(True))
            return
        if not showing and not hub_out:
            #  only the frame was out: a reveal turned back in its first phase
            self._animate(rules.OUT_MS, width, False, self._frame, 0,
                          self._set_frame, lambda: self._slide_done(False))
            return
        if showing:
            self._set_frame(width)
        start = self.slot.x()
        end = 0 if showing else -width
        if start == end:
            self._slide_done(showing)
            return
        self._animate(rules.IN_MS if showing else rules.OUT_MS, width,
                      showing, start, end,
                      lambda x: self._move_slot(x, width, showing),
                      lambda: self._slide_done(showing))

    def _reveal_from_rest(self, width):
        q = hubqt.qt()
        total = rules.reveal_ms()
        anim = q.QtCore.QVariantAnimation(self.host)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(total)

        def step(t):
            if not hubqt._valid(self.slot):
                return
            frame, x = rules.reveal_at(t * total, width)
            self._set_frame(frame)
            self.slot.move(x, 0)
        anim.valueChanged.connect(step)
        anim.finished.connect(lambda: self._slide_done(True))
        self._anim = anim
        anim.start()

    def _animate(self, full, width, showing, start, end, step, done):
        """`step(value)` from `start` to `end` with the rules' easing
        (slide_x), over the rules' time for the whole width shortened for a
        part of it; `done()` at the end."""
        q = hubqt.qt()
        anim = q.QtCore.QVariantAnimation(self.host)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(max(1, int(round(
            full * abs(end - start) / float(width)))))
        anim.valueChanged.connect(lambda t: step(
            start + (end - start) * self._eased(t, width, showing)))
        anim.finished.connect(done)
        self._anim = anim
        anim.start()

    @staticmethod
    def _eased(t, width, showing):
        """The rules' easing as a fraction 0..1 of the way: exactly slide_x
        when a phase starts at rest."""
        full = rules.slide_x(t, width, showing)
        if showing:
            return (full + width) / float(width)      # -width..0 -> 0..1
        return -full / float(width)                   # 0..-width -> 0..1

    def _move_slot(self, x, width, showing):
        if not hubqt._valid(self.slot):
            return
        x = int(round(x))
        self.slot.move(x, 0)
        if not showing:
            self._set_frame(width + x)                # the frame leaves with it

    def _slide_done(self, showing):
        self._stop_anim()
        self._rest_out = bool(showing)
        if not self.alive():
            return
        self._fit_slot()
        if not showing:
            self.host.hide()
            self.sensor.show()
            #  above any floating window of Maya's left at the edge
            self.sensor.raise_()

    def _stop_anim(self):
        anim, self._anim = self._anim, None
        if anim is not None and hubqt._valid(anim):
            anim.blockSignals(True)
            anim.stop()
            anim.deleteLater()

    # ------------------------------------------------------------ events

    def sensor_entered(self):
        if self.alive():
            self.dwell.start()

    def sensor_left(self):
        if self.alive():
            self.dwell.stop()

    def dwell_done(self):
        """The dwell is over: the cursor still on the edge, no button held,
        Maya the active application -> out."""
        if not self.alive():
            return
        area = self.work_area()
        if not rules.contains(rules.sensor_rect(area), self.cursor(),
                              margin=1):
            return
        if rules.may_reveal(True, self._shown, self.buttons(),
                            self.app_active()):
            self.reveal()

    def host_entered(self):
        if not self.alive():
            return
        self.hide.stop()
        self.retry.stop()
        self.hold.enter()

    def host_left(self):
        if not self.alive():
            return
        if self.hold.leave():
            self._sync_watch()
        if self._shown:
            self.hide.start()

    def press_at(self, point):
        """A press anywhere in the application, global physical px: outside
        the panel it releases a command's hold."""
        if not self.alive() or not self._shown:
            return
        if rules.contains(self._host_rect(), point):
            return
        if self.hold.press_outside():
            self._sync_watch()
            self.hide.start()

    def blockers(self):
        """Why the panel must stay right now (rules.hide_blockers)."""
        if not self.alive():
            return []
        q = hubqt.qt()
        app = q.QtWidgets.QApplication
        focus = app.focusWidget()
        typing = bool(
            focus is not None and self.host.isAncestorOf(focus)
            and isinstance(focus, (q.QtWidgets.QLineEdit,
                                   q.QtWidgets.QAbstractSpinBox,
                                   q.QtWidgets.QTextEdit,
                                   q.QtWidgets.QPlainTextEdit))
            and self.host.isActiveWindow())
        return rules.hide_blockers(
            pinned=self.pinned, held=self.hold.held,
            inside=rules.contains(self._host_rect(), self.cursor()),
            buttons=self.buttons(),
            popup=app.activePopupWidget() is not None,
            modal=app.activeModalWidget() is not None, typing=typing)

    def hide_due(self):
        """The hide (or a retry) timer: go, unless something holds it - then
        ask again in RETRY_MS."""
        if not self.alive() or not self._shown:
            return
        reasons = self.blockers()
        if reasons:
            #  the pin and a command's hold have their own way out
            #  (unpinning, the visit, a press outside each start the hide):
            #  asking again every RETRY_MS for as long as the panel stays
            #  pinned would tick for hours for nothing
            if "pinned" not in reasons and "held" not in reasons:
                self.retry.start()
            return
        self.conceal()

    def set_pinned(self, on):
        """The 📌: a pinned panel stays out; unpinned, it goes once the
        cursor is off it."""
        self.pinned = bool(on)
        if not on and self._shown and self.alive():
            self.hide.start()

    def set_width(self, logical, save=True):
        """The panel's logical width, clamped and laid out; `save` (the end
        of a grip drag) reports it to `on_width`."""
        self.width = rules.clamp_width(logical)
        self.place()
        if save and self.on_width:
            self.on_width(self.width)

    # ------------------------------------------------------------ the press watch

    def _sync_watch(self):
        """The application press filter stands exactly while a command's
        hold does (see the module)."""
        want = bool(self._shown and self.hold.held)
        if want == self._watching:
            return
        q = hubqt.qt()
        app = q.QtWidgets.QApplication.instance()
        watch = self._watch
        if want:
            if app is not None and hubqt._valid(watch):
                app.installEventFilter(watch)
                self._watching = True
            return
        if app is not None and hubqt._valid(watch):
            app.removeEventFilter(watch)
        self._watching = False

    # ------------------------------------------------------------ the end

    def destroy(self):
        """Delete the windows (the slot and what stands in it with them).
        Harmless twice, and after `destroy_all`."""
        self._stop_anim()
        self.hold = rules.Hold()
        self._shown = False
        self._sync_watch()
        q = hubqt.qt()
        for widget in (self.sensor, self.host):
            if hubqt._valid(widget):
                widget.hide()
                widget.setParent(None)
                q.shiboken.delete(widget)
        st = getattr(sys, "_skeldar_hubedge", None)
        if st and st.get("edge") is self:
            st["edge"] = None
