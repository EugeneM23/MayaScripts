"""The Time Bar sliding out of the bottom of Maya's window (2026-10-16, the animator:
«А можем сделать так что бы это окно было всплывающим когда наводим в область нижней
части экрана?»; asked: a third mode beside Maya's and Docked, the edge of Maya's
window, not the screen).

Two windows of ours, frameless Qt.Tool children of Maya's main window (above Maya,
never above another application, gone with Maya minimized):

    host    the band along the bottom of Maya's window; holds the strip. A slide
            moves the strip inside the host and the host's mask shows only the
            part standing in it, so nothing is laid out again per frame.
    sensor  a 2 px strip at the very bottom at window opacity 1/255 (Qt keeps it
            layered and it still takes the mouse - CLAUDE.md trap 110). Shown only
            while the bar is hidden.

When it comes out and what keeps it out are the hub's edge panel's rules
(maya_edgerules: may_reveal, hide_blockers, the dwell and the hide delays), plus
a drag inside the strip itself. The cursor, the buttons, Maya's window and whether
Maya is the active application come through seams, so the tests drive it with no
mouse.
"""

import traceback

import maya_edgerules as rules
import maya_hubqt as hubqt

from . import look

HOST = "skeldarTimeBarEdgeHost"
SENSOR = "skeldarTimeBarEdgeSensor"
SENSOR_OPACITY = 1.0 / 255
PLACE_MS = 300          # Maya's window moved or resized: followed this often
WATCH_MS = 60           # while out: is the cursor still on it


def main_window():
    """Maya's main window, or None. Fetched when needed, never kept (trap 135)."""
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


def _window_rect():
    """Maya's window's client area, global (x, y, w, h), or None."""
    window = main_window()
    if window is None:
        return None
    top_left = window.mapToGlobal(window.rect().topLeft())
    return top_left.x(), top_left.y(), window.width(), window.height()


def destroy_all():
    """Every host and sensor of ours standing, found by name (an older module
    object's too - trap 102). Returns how many."""
    q = hubqt.qt()
    if q is None:
        return 0
    gone = 0
    for widget in list(q.QtWidgets.QApplication.topLevelWidgets()):
        try:
            if widget.objectName() in (HOST, SENSOR):
                widget.hide()
                widget.deleteLater()
                gone += 1
        except RuntimeError:
            pass
    return gone


class BottomEdge(object):
    """The controller: build the strip with `make_strip(parent)`, then it comes
    out when the cursor rests on the bottom edge and goes when it leaves."""

    def __init__(self, make_strip, parent=None, window_rect=None, cursor=None, buttons=None,
                 app_active=None, motion=None):
        q = hubqt.qt()
        QtCore, QtWidgets = q.QtCore, q.QtWidgets
        self._window_rect = window_rect or _window_rect
        self._cursor = cursor
        self._buttons = buttons
        self._app_active = app_active
        self.motion = motion
        self.pinned = False
        self.shown = False
        self.offset = 0               # px the strip stands below its place
        self._slide = None            # (started clock ms, showing, from offset)
        self._rect = None
        if parent is None:
            parent = main_window()
        flags = QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
        host = QtWidgets.QWidget(parent, flags)
        host.setObjectName(HOST)
        host.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.host = host
        self.strip = make_strip(host)
        self.strip.set_edge(self)
        controller = self

        class Sensor(QtWidgets.QWidget):
            def enterEvent(self, event):
                controller.sensor_entered()

            def leaveEvent(self, event):
                controller.dwell.stop()

        sensor = Sensor(parent, flags | QtCore.Qt.WindowDoesNotAcceptFocus)
        sensor.setObjectName(SENSOR)
        sensor.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        sensor.setWindowOpacity(SENSOR_OPACITY)
        self.sensor = sensor

        def timer(ms, call, single=True):
            t = QtCore.QTimer(host)
            t.setSingleShot(single)
            t.setInterval(int(ms))
            t.timeout.connect(lambda: controller._guard(call))
            return t
        self.dwell = timer(rules.DWELL_MS, self.dwell_done)
        self.hide_timer = timer(rules.HIDE_MS, self.hide_due)
        self.place_timer = timer(PLACE_MS, self.place, single=False)
        self.watch = timer(WATCH_MS, self.watch_tick, single=False)
        self.anim = timer(16, self.slide_tick, single=False)
        self.place()
        self.host.hide()
        self.sensor.show()
        self.sensor.raise_()
        self.place_timer.start()

    # seams --------------------------------------------------------------------------
    def cursor(self):
        if self._cursor:
            return self._cursor()
        p = hubqt.qt().QtGui.QCursor.pos()
        return p.x(), p.y()

    def buttons(self):
        if self._buttons:
            return self._buttons()
        return bool(hubqt.qt().QtWidgets.QApplication.mouseButtons())

    def app_active(self):
        if self._app_active:
            return self._app_active()
        q = hubqt.qt()
        return q.QtGui.QGuiApplication.applicationState() == q.QtCore.Qt.ApplicationActive

    def _motion(self):
        if self.motion is not None:
            return self.motion
        return bool(getattr(self.strip, "motion", True))

    def _guard(self, call):
        try:
            if self.alive():
                call()
        except Exception:                                    # noqa: BLE001 - a timer: never raise
            print(traceback.format_exc())

    def alive(self):
        return hubqt._valid(self.host)

    # placement ---------------------------------------------------------------------
    def height(self):
        return max(1, self.strip.sizeHint().height())

    def place(self):
        window = self._window_rect()
        if not window:
            return
        rect = (tuple(window), self.height())
        if rect == self._rect:
            return
        self._rect = rect
        x, y, w, h = look.bottom_band(window, self.height())
        self.host.setGeometry(x, y, w, h)
        self.strip.setGeometry(0, self.offset, w, h)
        self._mask()
        sx, sy, sw, sh = look.sensor_band(window, rules.SENSOR_PX)
        self.sensor.setGeometry(sx, sy, sw, sh)

    def _mask(self):
        q = hubqt.qt()
        w, h = self.host.width(), self.host.height()
        shown = max(0, h - self.offset)
        self.host.setMask(q.QtGui.QRegion(0, h - shown, w, max(1, shown)))

    def _host_rect(self):
        g = self.host.geometry()
        return g.x(), g.y(), g.width(), g.height()

    # coming out ------------------------------------------------------------------
    def sensor_entered(self):
        self.dwell.start()

    def dwell_done(self):
        window = self._window_rect()
        if not window or not rules.contains(look.sensor_band(window, rules.SENSOR_PX), self.cursor(),
                                            margin=2):
            return
        if rules.may_reveal(True, self.shown, self.buttons(), self.app_active()):
            self.reveal()

    def reveal(self):
        if self.shown:
            return
        self.place()
        self.shown = True
        self.sensor.hide()
        self.host.show()
        self.host.raise_()
        self._start_slide(True)
        self.watch.start()

    def conceal(self):
        if not self.shown:
            return
        self.shown = False
        self.watch.stop()
        self.hide_timer.stop()
        self._start_slide(False)

    def _start_slide(self, showing):
        if not self._motion():
            self.offset = 0 if showing else self.host.height()
            self._settle(showing)
            return
        self._slide = (self.strip.clock(), showing, self.offset)
        self.anim.start()

    def slide_tick(self):
        if self._slide is None:
            self.anim.stop()
            return
        started, showing, start = self._slide
        h = self.host.height()
        ms = look.SLIDE_MS if showing else look.SLIDE_BACK_MS
        t = self.strip.clock() - started
        #  from where the strip stands: a reveal during a slide back turns there
        span = (start if showing else h - start) or h
        part = look.slide(t, span, showing, ms)
        self.offset = part if showing else start + part
        self.strip.move(0, self.offset)
        self._mask()
        if t >= ms:
            self.anim.stop()
            self._slide = None
            self._settle(showing)

    def _settle(self, showing):
        self.offset = 0 if showing else self.host.height()
        self.strip.move(0, self.offset)
        self._mask()
        if not showing:
            self.host.hide()
            self.sensor.show()
            self.sensor.raise_()

    # going back ------------------------------------------------------------------
    def watch_tick(self):
        """While out: the cursor off it starts the hide; back on it stops it."""
        inside = rules.contains(self._host_rect(), self.cursor())
        if inside:
            self.hide_timer.stop()
        elif not self.hide_timer.isActive():
            self.hide_timer.start()

    def blockers(self):
        q = hubqt.qt()
        app = q.QtWidgets.QApplication
        focus = app.focusWidget()
        typing = bool(focus is not None and self.host.isAncestorOf(focus)
                      and isinstance(focus, q.QtWidgets.QLineEdit))
        reasons = rules.hide_blockers(pinned=self.pinned,
                                      inside=rules.contains(self._host_rect(), self.cursor()),
                                      buttons=self.buttons(),
                                      popup=app.activePopupWidget() is not None,
                                      modal=app.activeModalWidget() is not None, typing=typing)
        if getattr(self.strip.timeline, "drag", None) or getattr(self.strip.range, "drag", None):
            reasons.append("dragging")
        return reasons

    def hide_due(self):
        if not self.shown:
            return
        if self.blockers():
            if not self.pinned:
                self.hide_timer.start()       # asked again
            return
        self.conceal()

    def set_pinned(self, on):
        self.pinned = bool(on)
        if not on and self.shown:
            self.hide_timer.start()

    def destroy(self):
        for t in (self.dwell, self.hide_timer, self.place_timer, self.watch, self.anim):
            try:
                t.stop()
            except RuntimeError:
                pass
        for w in (self.sensor, self.host):
            try:
                w.hide()
                w.deleteLater()
            except RuntimeError:
                pass
