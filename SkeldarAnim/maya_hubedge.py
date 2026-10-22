"""maya_hubedge - the hub as a panel sliding out of a screen edge.

2026-10-08 (the animator: «когда я подношу мышку к левому краю экрана то
появляется наша полка когда убираю то полка скрывается»); since 2026-10-09
the left OR the right edge («Можем добавить опцию выбора стороны монитора
откуда выезжает наша полка?» - `side`, `set_side`). Every quantity the
controller keeps counts from the screen edge inward - the slot's OFFSET
(-width off the edge, 0 out) and the FRAME; maya_edgerules turns them into
host-local x for the side, so the left side's numbers are the right side's
too. Three windows of ours, each a frameless Qt.Tool owned by Maya's main
window (so above Maya, never above another application, gone with Maya
minimized):

    host    the panel: the work area's chosen edge, its full height; holds
            the SLOT, which holds the Skin's root. A slide moves the SLOT
            inside the host - no window crosses into a monitor beside it,
            nothing is laid out again per frame. The host paints the hub's
            `panel` colour and a 1 px `inset_line` down its inner edge (the
            right on the left side, the left on the right side); the slot
            stops short of that line, so it always shows. Only its
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
    grip    5 logical px on the host's inner side: drag the width inward to
            widen (a child of the host, painting nothing - the host's line
            is under it).

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
import traceback

import maya_edgerules as rules
import maya_hubburst as hubburst
import maya_hubmotion as hubmotion
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

HOST = "skeldarAnimHubEdge"
SENSOR = "skeldarAnimHubEdgeSensor"
SLOT = "skeldarAnimHubEdgeSlot"
GRIP = "skeldarAnimHubEdgeGrip"
HGRIP = "skeldarAnimHubEdgeHeightGrip"

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


def _viewport_area(side="left"):
    """Maya's viewport area (the MainPane workspaceControl: under the menus, the
    status line, the shelf and the scene tabs), global physical px, or None. Found
    every time (trap 135)."""
    if not hubqt._maya_ui_ok():
        return None
    try:
        import maya.OpenMayaUI as omui
        q = hubqt.qt()
        ptr = omui.MQtUtil.findControl("MainPane")
        if not ptr:
            return None
        pane = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
        if not pane.isVisible() or pane.width() <= 0 or pane.height() <= 0:
            return None
        p = pane.mapToGlobal(pane.rect().topLeft())
        x, y, w, h = p.x(), p.y(), pane.width(), pane.height()
        #  below the viewport's own menus and icons (2026-10-17, «реил не должен
        #  перекрывать другие меню»): the drawing area of the model panel standing
        #  against the pane's left edge starts lower than the pane
        top = _drawing_top(x if side != "right" else x + w, side)
        if top is not None and y < top < y + h - 100:
            h, y = h - (top - y), top
        return (x, y, w, h)
    except Exception:                                        # noqa: BLE001
        return None


def _above_timebar(area):
    """`area` ending above the Time Bar's band while the Time Bar sits at the
    bottom edge (2026-10-17, «некоторые окошки в рейле например как волк билдер
    сильно высокие и ломают тайм слайдер»): a tall card scrolls inside the panel
    instead of reaching the bar, and the bar keeps its whole width."""
    try:
        bar = (getattr(sys, "_skeldar_timebar", None) or {}).get("edge")
        if bar is None or not bar.alive():
            return area
        top = bar.host.geometry().y()
    except Exception:                                        # noqa: BLE001
        return area
    x, y, w, h = area
    if y < top < y + h:
        h = top - y
    return (x, y, w, h)


def _drawing_top(edge, side="left"):
    """The global top of the drawing area of the visible model panel whose left
    edge is the viewport's `left` (the upper one when panes are stacked), or None."""
    try:
        import maya.cmds as cmds
        import maya.OpenMayaUI as omui
        q = hubqt.qt()
        tops = []
        for panel in cmds.getPanel(visiblePanels=True) or []:
            if cmds.getPanel(typeOf=panel) != "modelPanel":
                continue
            #  the M3dView's widget: the modelEditor control is the whole panel,
            #  its icon bar included (read live: 167 against the drawing's 228)
            m3d = omui.M3dView()
            omui.M3dView.getM3dViewFromModelPanel(panel, m3d)
            ptr = m3d.widget()
            if not ptr:
                continue
            view = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
            g = view.mapToGlobal(view.rect().topLeft())
            at = g.x() + view.width() if side == "right" else g.x()
            if abs(at - edge) <= 8:
                tops.append(g.y())
        return min(tops) if tops else None
    except Exception:                                        # noqa: BLE001
        return None


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
                #  the frame's inner edge, so it slides out with it
                if self.edge.rail:
                    #  see-through: the rail and the card paint themselves
                    return
                side = self.edge.side
                frame = max(1, min(self.width(), self.edge.frame))
                fx, fw = rules.frame_span(frame, self.width(), side)
                painter = QtGui.QPainter(self)
                try:
                    painter.fillRect(fx, 0, fw, self.height(), QtGui.QColor(
                        hubstyle.TOKENS["panel"]))
                    line = self.edge._line()
                    painter.fillRect(
                        rules.line_x(frame, self.width(), line, side), 0,
                        line, self.height(),
                        QtGui.QColor(hubstyle.TOKENS["inset_line"]))
                finally:
                    painter.end()

        class WidthGrip(QtWidgets.QWidget):
            """The host's inner edge (its right on the left side, its left on
            the right side): a drag inward widens the panel, the release
            remembers the width. `press/drag/release` take GLOBAL x
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
                self.edge.set_width(
                    rules.dragged_width(width0, gx - x0, self.edge.scale,
                                        self.edge.side), save=False)

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

        class HeightGrip(QtWidgets.QWidget):
            """The rail card's bottom (2026-10-22): a drag sets the card's height,
            the release remembers it, a double click gives the card its content's
            height back. `press/drag/release` take GLOBAL y (physical px)."""

            def __init__(self, edge, parent=None):
                super(HeightGrip, self).__init__(parent)
                self.edge = edge
                self._start = None
                self.setCursor(QtCore.Qt.SizeVerCursor)
                self.setToolTip("Drag to make the card taller or shorter - "
                                "double click: as tall as its content")

            def press(self, gy):
                self._start = (gy, self.edge.card_height())

            def drag(self, gy):
                if self._start is None:
                    return
                y0, height0 = self._start
                self.edge.set_height(
                    rules.dragged_height(height0, gy - y0, self.edge.scale),
                    save=False)

            def release(self):
                if self._start is not None:
                    self.edge.set_height(self.edge.card_height(), save=True)
                self._start = None

            def mousePressEvent(self, event):              # noqa: N802
                if event.button() == QtCore.Qt.LeftButton:
                    self.press(_global_point(event)[1])
                    event.accept()
                else:
                    event.ignore()

            def mouseMoveEvent(self, event):               # noqa: N802
                self.drag(_global_point(event)[1])

            def mouseReleaseEvent(self, event):            # noqa: N802
                self.release()

            def mouseDoubleClickEvent(self, event):        # noqa: N802
                self._start = None
                self.edge.set_height(None, save=True)

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
                        hgrip=HeightGrip, watch=PressWatch)
    return _CLASSES


# ------------------------------------------------------------- the controller

class Edge(object):
    """The edge panel: its three windows, its timers, and the controller the
    windows' events and the timers call. Every decision is maya_edgerules'.

    `scale` is the display scale (Qt px are physical in Maya); `width` the
    panel's logical width; `motion()` whether it slides (default: the hub's
    Interface animations); `on_width(width)` is called when a drag of the
    grip ends (the caller remembers it); `side` the screen edge it stands
    on, "left" or "right" (2026-10-09; `set_side` moves it). The seams:
    `work_area()` -> (x, y, w, h), `cursor()` -> (x, y), `buttons()` ->
    bool, `app_active()` -> bool, all physical px, default Qt's."""

    def __init__(self, scale=1.0, parent=None, width=rules.WIDTH,
                 motion=None, on_width=None, work_area=None, cursor=None,
                 buttons=None, app_active=None, side="left", rail=False,
                 rest=None, shape=None, burst=None, burst_stop=None,
                 card=None, on_height=None, least=None):
        q = hubqt.qt()
        QtCore, QtWidgets = q.QtCore, q.QtWidgets
        classes = _classes()
        #  2026-10-17 («вешаем наш реил к боку экрана вьюпорта пусть он там висит
        #  постоянно, а при клике по иконкам рейла будут выезжать наши разделы»):
        #  `rail` - the panel stands on the VIEWPORT's side, its rail always
        #  showing (`rest()` px of it from the edge), the card out only by a
        #  click (reveal / conceal); the edge's hover does nothing
        self.rail = bool(rail)
        self.rest = rest
        #  host-local rects (x, y, w, h) shown beyond the rail when out - the card;
        #  None: the whole frame (2026-10-17)
        self.shape = shape
        #  2026-10-18 (floating windows): `burst(showing, origin, done, on_shape)`
        #  -> bool bursts the card out of a global point or folds it into one;
        #  `on_shape((x0, y0, x1, y1))` hears the shape, host-local, each tick,
        #  and `burst_shape` (x, y, w, h) cuts the card from the mask while it
        #  runs. None, or a burst that cannot start: the frame's old slide.
        self.burst = burst
        self.burst_stop = burst_stop   # () stops every card's burst still drawing (2026-10-19)
        #  2026-10-22: `card()` -> the rail card's host-local rect (x, y, w, h) or None:
        #  the width grip stands down its inner side and the height grip along its
        #  bottom; `on_height(logical or None, save)` sets the card's height (None:
        #  its content's) - None: no height grip
        self.card = card
        self.on_height = on_height
        #  `least()` -> the logical width the shown card needs (2026-10-22: a card
        #  held narrower than its content was cut at its inner side); the panel is
        #  never narrower, whatever width the grip left
        self.least = least
        self._least_seen = None
        self.burst_shape = None
        self._burst_gen = 0         # each rail move's number: stale bursts are deaf
        self.scale = float(scale or 1.0)
        self.width = rules.clamp_width(width)
        self.side = rules.side_of(side)
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
        self.slot = self.grip = self.hgrip = None
        if parent is None:
            parent = main_window()
        flags = QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint

        host = classes["host"](self, parent, flags)
        host.setObjectName(HOST)
        #  the panel coming out under the cursor must not take the keyboard
        #  from the viewport; a click inside still activates it
        host.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        if self.rail:
            #  see-through (2026-10-22, «видно артефакт острого края»): the window's
            #  mask is square, so its corners showed the host's fill round the
            #  card's rounded frame; translucent, they show what is behind it
            host.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
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
        if self.rail and self.on_height is not None:
            hgrip = classes["hgrip"](self, host)
            hgrip.setObjectName(HGRIP)
            hgrip.hide()
            self.hgrip = hgrip

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
        self._area = None
        if self.rail:
            self.sensor.hide()
            self.host.show()
            #  the viewport moves and resizes with Maya's window and its docks
            self.follow = q.QtCore.QTimer(self.host)
            self.follow.setInterval(150)
            self.follow.timeout.connect(self._follow)
            self.follow.start()
        else:
            self.host.hide()
            self.sensor.show()
            self.sensor.raise_()

    def _follow(self):
        """The rail panel stands on the viewport's side wherever it moves."""
        if not self.alive():
            return
        try:
            area = (tuple(self.work_area()), self.rest_px())
        except Exception:                                    # noqa: BLE001
            return
        if self._anim is not None:
            return
        least = self.least_width()
        if area != self._area or least != self._least_seen:
            self._area = area
            self._least_seen = least
            self.place()
            return
        self._place_grips()
        if self.shape is not None and self._rest_out:
            #  the card grows and shrinks (a section opened, a list filled)
            try:
                shape = tuple(tuple(r) for r in (self.shape() or []))
            except Exception:                                # noqa: BLE001
                shape = ()
            if shape != getattr(self, "_shape_seen", None):
                self._shape_seen = shape
                self._set_frame(self._frame)

    def rest_px(self):
        """How much of the host shows at rest, physical px from the edge: the
        rail (`rest()`), or nothing for the hover panel."""
        if not self.rail or self.rest is None:
            return 0
        try:
            return int(max(0, self.rest()))
        except Exception:                                    # noqa: BLE001
            return 0

    def visible_rects(self):
        """Every part of the panel showing on screen now (global x, y, w, h): the
        rail, and - when out - the card `shape()` names, as far as the frame has
        opened. The time bar steps aside for these and not for the empty height
        under a card (2026-10-17)."""
        if not self.alive() or not self.host.isVisible() or self._frame <= 0:
            return []
        if not (self.rail and self.shape is not None):
            one = self.visible_rect()
            return [one] if one else []
        x, y, w, h = self._host_rect()
        out = []
        rx, rw = rules.frame_span(max(1, min(w, self.rest_px())), w, self.side)
        out.append((x + rx, y, rw, h))
        fx, fw = rules.frame_span(max(1, self._frame), w, self.side)
        try:
            rects = self.shape() or []
        except Exception:                                    # noqa: BLE001
            rects = []
        cut = self.burst_shape
        for sx, sy, sw, sh in rects:
            left, right = max(sx, fx), min(sx + sw, fx + fw)
            top, bottom = sy, sy + sh
            if cut is not None:                  # a burst: as far as it has grown
                left, right = max(left, cut[0]), min(right, cut[0] + cut[2])
                top, bottom = max(top, cut[1]), min(bottom, cut[1] + cut[3])
            if right > left and bottom > top:
                out.append((x + left, y + top, right - left, bottom - top))
        return out

    def visible_rect(self):
        """What of the panel shows on screen now (global x, y, w, h), or None:
        the time bar steps aside for it (maya_timebar.edge._obstacles). The
        frame's whole span: a rail panel's time bar asks `visible_rects`, which
        cuts the card to a running burst (2026-10-18); this one rect is the
        bound round all of it."""
        if not self.alive() or not self.host.isVisible() or self._frame <= 0:
            return None
        x, y, w, h = self._host_rect()
        fx, fw = rules.frame_span(max(1, self._frame), w, self.side)
        return x + fx, y, fw, h

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
        if self._work_area:
            return self._work_area()
        if self.rail:
            area = _viewport_area(self.side) or _maya_work_area()
            return _above_timebar(area)
        return _maya_work_area()

    def _host_rect(self):
        return self.host.geometry().getRect()

    def _line(self):
        """The host's inner line, physical px (1 logical)."""
        return hubstyle.px(1, self.scale)

    @property
    def offset(self):
        """The slot's offset from the screen edge, physical px: -the host's
        width off the edge, 0 out - the same numbers on either side
        (rules.slot_x turns it into the slot's x)."""
        return rules.offset_of(self.slot.x(), self._line(), self.side)

    def _put_slot(self, offset):
        self.slot.move(rules.slot_x(int(round(offset)), self._line(),
                                    self.side), 0)

    # ------------------------------------------------------------ geometry

    def place(self):
        """The windows' geometry from the work area: the host on its
        `side` edge, its full height, the sensor over that edge."""
        if not self.alive():
            return
        area = self.work_area()
        x, y, w, h = rules.panel_rect(area, self.shown_width(), self.scale,
                                      self.side)
        self.host.setGeometry(x, y, w, h)
        sx, sy, sw, sh = rules.sensor_rect(area, self.side)
        self.sensor.setGeometry(sx, sy, sw, sh)
        self._fit_slot()

    def _fit_slot(self):
        """The slot over the host (short of its line) - out (offset 0), off
        the edge in, where the slide has it while one runs - and the grip
        on the host's inner side."""
        host, slot, grip = self.host, self.slot, self.grip
        if not (hubqt._valid(host) and slot is not None
                and hubqt._valid(slot)):
            return
        w, h = host.width(), host.height()
        line = self._line()
        if self.rail:
            #  the slot never moves: the frame (the window's mask) opens from
            #  the rail to the whole panel and closes back onto it
            offset = 0
            if self._anim is None:
                self._set_frame(w if self._rest_out else self.rest_px())
            if grip is not None and hubqt._valid(grip):
                grip.setVisible(bool(self._rest_out))
            slot.setGeometry(rules.slot_x(offset, line, self.side), 0,
                             max(1, w - line), h)
            self._place_grips()
            return
        elif self._anim is not None:
            offset = self.offset
        else:
            offset = 0 if self._rest_out else -w
            self._set_frame(w if self._rest_out else 0)
        slot.setGeometry(rules.slot_x(offset, line, self.side), 0,
                         max(1, w - line), h)
        if grip is not None and hubqt._valid(grip):
            g = hubstyle.px(rules.GRIP_PX, self.scale)
            grip.setGeometry(rules.grip_x(w, g, self.side), 0, g, h)

    @property
    def frame(self):
        """How much of the host shows, physical px from the screen edge."""
        return self._frame

    def _set_frame(self, px):
        """Show `px` of the host from the screen edge: a window mask (Qt
        never paints the rest), none once it is all of it. A mask of nothing
        is no mask at all to Qt, so the least is one pixel - the host is
        hidden at rest anyway."""
        host = self.host
        if not hubqt._valid(host):
            return
        w = host.width()
        px = int(max(0, min(w, round(px))))
        self._frame = px
        if self.rail and self.shape is not None:
            #  the rail panel shows its rail and, as far as the frame has opened,
            #  only what `shape()` names (the card): no backdrop under it
            #  (2026-10-17, «не нужно им рисовать фон под ними»)
            q = hubqt.qt()
            h = host.height()
            rx, rw = rules.frame_span(max(1, min(w, self.rest_px())), w, self.side)
            region = q.QtGui.QRegion(rx, 0, rw, h)
            fx, fw = rules.frame_span(max(1, px), w, self.side)
            opened = q.QtGui.QRegion(fx, 0, fw, h)
            try:
                rects = self.shape() or []
            except Exception:                                # noqa: BLE001
                rects = []
            cut = self.burst_shape
            if cut is not None:
                #  a burst running: the card as far as its shape has grown
                opened = opened.intersected(q.QtGui.QRegion(*[int(v) for v in cut]))
            for x, y, rw2, rh in rects:
                region = region.united(opened.intersected(
                    q.QtGui.QRegion(int(x), int(y), int(rw2), int(rh))))
            host.setMask(region)
            host.update()
            return
        if px >= w:
            host.clearMask()
        else:
            q = hubqt.qt()
            fx, fw = rules.frame_span(max(1, px), w, self.side)
            host.setMask(q.QtGui.QRegion(fx, 0, fw, host.height()))
        host.update()

    # ------------------------------------------------------------ in, out

    def reveal(self, hold=False, origin=None):
        """Bring the panel out. `hold`: by command (the shelf button, a
        hotkey, a tool's show_window) - it stays until visited or a press
        lands outside it (rules.Hold). `origin`: the rail's card bursts out
        of that global point (2026-10-18; None: the frame's slide)."""
        if not self.alive():
            return
        for timer in (self.dwell, self.hide, self.retry):
            timer.stop()
        if self.rail:
            self._rail_slide(True, origin)
            return
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

    def conceal(self, origin=None):
        """Send the panel back off the edge (the sensor comes back when the
        slide ends). `origin`: the rail's card folds into that global point
        (2026-10-18: the ✕, the ⧉ or the lit rail icon pressed)."""
        if not self.alive():
            return
        for timer in (self.dwell, self.hide, self.retry):
            timer.stop()
        if not self._shown:
            return
        if self.rail:
            self._rail_slide(False, origin)
            return
        self._shown = False
        self.hold = rules.Hold()
        self._sync_watch()
        self._slide(False)

    def toggle(self):
        """The rail: out when in, in when out."""
        if self._shown:
            self.conceal()
        else:
            self.reveal()
        return self._shown

    def _rail_slide(self, showing, origin=None):
        """The rail panel: the window's frame opens from the rail to the whole
        width (out) or closes back onto it (in), from where it stands; the
        host stays up with its rail. With a `burst` seam and an `origin`
        (2026-10-18, «Из точки»), the card bursts out of that point instead -
        the frame whole at once, the mask showing the rail and the card as far
        as the burst has grown it - or folds into it, the frame back on the
        rail when the fold ends."""
        self._stop_anim()
        self._burst_gen += 1        # any burst still running is no longer heard
        self._shown = bool(showing)
        self.place()
        self.host.show()
        self.host.raise_()
        width = max(1, self.host.width())
        rest = min(width, self.rest_px())
        end = width if showing else rest
        start = self._frame
        try:
            moving = bool(self.motion())
        except Exception:                                    # noqa: BLE001
            moving = False
        if moving and self.burst is not None and self._rail_burst(showing, origin):
            return
        self._stop_bursts()
        self.burst_shape = None
        if showing:
            self._rest_out = True        # the grip and the frame follow at the end
            if hubqt._valid(self.grip):
                self.grip.setVisible(True)
                self.grip.raise_()
        if not moving or start == end:
            self._rail_done(showing)
            return
        span = max(1, width - rest)
        self._animate(rules.IN_MS if showing else rules.OUT_MS, span, showing,
                      start, end, self._set_frame,
                      lambda: self._rail_done(showing))

    def _stop_bursts(self):
        """A move without a burst (2026-10-19): a card's burst still drawing its
        fold must not go on over the plain slide."""
        if self.burst_stop is not None:
            try:
                self.burst_stop()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()

    def _rail_burst(self, showing, origin):
        """Start the card's burst out of global `origin` (or its fold into it)
        through the `burst` seam; False when it cannot (no origin, the seam
        refusing or raising) and nothing was changed."""
        if origin is None:
            return False
        width = max(1, self.host.width())
        #  only the newest burst speaks (review 2026-10-18): a card folding
        #  while another bursts out (each card has its own Burster) must not
        #  write its shape or send the panel back to the rail when it ends
        gen = self._burst_gen

        def current():
            return self._burst_gen == gen and self.alive()

        if showing:
            #  until the first tick the card shows as the burst's start box
            #  about the point, pulled inside the card as the plan pulls it
            #  (the host-local shape replaces it then)
            self.burst_shape = self._start_box(origin)

        def on_shape(shape):
            if not current():
                return
            x0, y0, x1, y1 = shape
            self.burst_shape = (int(round(x0)), int(round(y0)),
                                max(0, int(round(x1 - x0))),
                                max(0, int(round(y1 - y0))))
            self._set_frame(self._frame)

        def done():
            if not current():
                return
            self.burst_shape = None
            if not showing:
                self._shown = False
                self._set_frame(min(width, self.rest_px()))
            self._rail_done(showing)

        try:
            ran = bool(self.burst(showing, origin, done, on_shape))
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            ran = False
        if not ran:
            self.burst_shape = None
            return False
        if showing and self._burst_gen == gen:
            #  asked first, the frame whole only once the burst runs: a refused
            #  one would have flashed the whole card for a frame
            self._rest_out = True
            self._set_frame(width)
            if hubqt._valid(self.grip):
                self.grip.setVisible(True)
                self.grip.raise_()
        return True

    def _start_box(self, origin):
        """The burst's start box (x, y, w, h), host-local, about global `origin`
        pulled ORIGIN_PAD inside the card (the largest of `shape()`'s rects) the
        way maya_hubburst.plan_open pulls it."""
        q = hubqt.qt()
        at = self.host.mapFromGlobal(q.QtCore.QPoint(int(origin[0]),
                                                    int(origin[1])))
        px, py = at.x(), at.y()
        try:
            rects = [r for r in (self.shape() or []) if r[2] > 0 and r[3] > 0] \
                if self.shape is not None else []
        except Exception:                                    # noqa: BLE001
            rects = []
        hx = hubstyle.px(hubburst.START_HALF[0], self.scale)
        hy = hubstyle.px(hubburst.START_HALF[1], self.scale)
        if not rects:
            return (px - hx, py - hy, 2 * hx, 2 * hy)
        cx, cy, cw, ch = max(rects, key=lambda r: r[2] * r[3])
        lx, ly = hubburst.clamp_origin((px - cx, py - cy), (cw, ch),
                                       hubburst.ORIGIN_PAD * self.scale)
        if hubburst.MOTION == "spring":
            #  the spring starts as the card scaled about the point (2026-10-22)
            x0, y0, x1, y1 = hubburst.plan_spring(True, (lx, ly), (cw, ch),
                                                  self.scale).start
            return (int(round(cx + x0)), int(round(cy + y0)),
                    int(round(x1 - x0)), int(round(y1 - y0)))
        #  and the box kept inside the card (maya_hubburst._box)
        x0, y0 = max(0.0, lx - hx), max(0.0, ly - hy)
        x1, y1 = min(float(cw), lx + hx), min(float(ch), ly + hy)
        return (int(round(cx + x0)), int(round(cy + y0)),
                int(round(x1 - x0)), int(round(y1 - y0)))

    def _rail_done(self, showing):
        self._stop_anim()
        self._rest_out = bool(showing)
        if self.alive():
            self._fit_slot()

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
        hub_out = self.offset > -width
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
        start = self.offset
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
            frame, offset = rules.reveal_at(t * total, width)
            self._set_frame(frame)
            self._put_slot(offset)
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

    def _move_slot(self, offset, width, showing):
        if not hubqt._valid(self.slot):
            return
        offset = int(round(offset))
        self._put_slot(offset)
        if not showing:
            self._set_frame(width + offset)           # the frame leaves with it

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
        if not self.alive() or self.rail:
            return
        area = self.work_area()
        if not rules.contains(rules.sensor_rect(area, self.side),
                              self.cursor(), margin=1):
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
        if not self.alive() or self.rail:      # the rail panel goes by a click only
            return
        if self.hold.leave():
            self._sync_watch()
        if self._shown:
            self.hide.start()

    def press_at(self, point):
        """A press anywhere in the application, global physical px: outside
        the panel it releases a command's hold."""
        if not self.alive() or not self._shown or self.rail:
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
        if not self.alive() or not self._shown or self.rail:
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

    def set_side(self, side):
        """Stand on `side` from now on (2026-10-09, ⋮ -> Edge panel ▸ Left
        edge / Right edge). A new side: any slide stops, the panel goes at
        once (no slide back across the screen), the windows stand at the new
        edge with the slot off it and the sensor up - the caller reveals it
        there. True when it moved; the side it already stands on, False."""
        side = rules.side_of(side)
        if side == self.side or not self.alive():
            return False
        self._stop_anim()
        for timer in (self.dwell, self.hide, self.retry):
            timer.stop()
        self._shown = False
        self._rest_out = False
        self.hold = rules.Hold()
        self._sync_watch()
        self.side = side
        if self.rail:
            self.place()
            self.host.show()
            return True
        self.host.hide()
        self.place()
        self.sensor.show()
        self.sensor.raise_()
        return True

    def card_rect(self):
        """The rail card's host-local rect (x, y, w, h), or None."""
        if self.card is None:
            return None
        try:
            rect = self.card()
        except Exception:                                    # noqa: BLE001
            return None
        if not rect or rect[2] <= 0 or rect[3] <= 0:
            return None
        return tuple(int(v) for v in rect)

    def card_height(self):
        """The rail card's shown height, logical px (0 with no card)."""
        rect = self.card_rect()
        return int(round(rect[3] / self.scale)) if rect else 0

    def _place_grips(self):
        """The rail card's grips on the card while it is out and still (2026-10-22):
        the width grip down its inner side, the height grip along its bottom; in
        the old place (the host's whole inner side) with no card to follow."""
        if not self.rail or not self.alive():
            return
        if self.card is None:
            grip = self.grip
            if grip is not None and hubqt._valid(grip):
                g = hubstyle.px(rules.GRIP_PX, self.scale)
                w, h = self.host.width(), self.host.height()
                grip.setGeometry(rules.grip_x(w, g, self.side), 0, g, h)
            return
        rect = self.card_rect()
        out = bool(self._rest_out) and self._anim is None and rect is not None
        g = hubstyle.px(rules.GRIP_PX, self.scale)
        grips = rules.card_grips(rect, g, self.side) if rect else None
        for widget, at in ((self.grip, grips[0] if grips else None),
                           (self.hgrip, grips[1] if grips else None)):
            if widget is None or not hubqt._valid(widget):
                continue
            if out and at is not None:
                widget.setGeometry(*at)
                widget.show()
                widget.raise_()
            elif widget is self.hgrip or self.card is not None:
                widget.hide()

    def set_height(self, logical, save=True):
        """The rail card's height, logical px (None: as tall as its content), handed
        to `on_height`; the grips follow."""
        if self.on_height is None:
            return
        if logical is not None:
            logical = max(rules.MIN_HEIGHT, int(round(logical)))
        try:
            self.on_height(logical, save)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
        self._place_grips()
        self._set_frame(self._frame)

    def least_width(self):
        """The logical width the shown card needs (`least()`), 0 without one."""
        if self.least is None:
            return 0
        try:
            return int(max(0, self.least() or 0))
        except Exception:                                    # noqa: BLE001
            return 0

    def shown_width(self):
        """The width the panel stands at: the grip's, or what the card needs."""
        return max(self.width, self.least_width())

    def set_width(self, logical, save=True):
        """The panel's logical width, clamped and laid out - never under what the
        shown card needs; `save` (the end of a grip drag) reports it to `on_width`."""
        self.width = rules.clamp_width(max(logical, self.least_width()))
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
