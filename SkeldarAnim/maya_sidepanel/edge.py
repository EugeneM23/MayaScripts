"""The side panel sliding out of the right edge of Maya's window (2026-10-17): the Time
Bar's bottom edge (maya_timebar.edge) turned on its side.

Two windows of ours, frameless Qt.Tool children of Maya's main window:

    host    the band along the right of Maya's window, its full height; holds the
            panel. It unrolls from the cursor's height through the host's mask.
    sensor  a 2 px strip at the very right at window opacity 1/255 (trap 110), shown
            only while the panel is hidden.

Plus the zone: the cursor resting look.ZONE_DWELL_MS in a strip along the right edge
(watched by a poll - a window there would take the viewport's clicks).

The cursor, the buttons, Maya's window, whether Maya is active and whether the cursor
is over Maya come through seams, so the tests drive it with no mouse.
"""

import traceback

import maya_edgerules as rules
import maya_hubqt as hubqt

from . import look
from maya_timebar.edge import main_window

HOST = "skeldarSidePanelHost"
SENSOR = "skeldarSidePanelSensor"
SENSOR_OPACITY = 1.0 / 255
PLACE_MS = 300
WATCH_MS = 60


def _global_rect(widget):
    top_left = widget.mapToGlobal(widget.rect().topLeft())
    return top_left.x(), top_left.y(), widget.width(), widget.height()


def _window_rect():
    """Where the panel lives: the viewport area (Maya's MainPane), down to its
    bottom - the Time Bar at the bottom edge steps aside for the panel instead
    (2026-10-17, maya_timebar.edge._obstacles); Maya's window without a pane.
    Looked up every time (trap 135)."""
    window = main_window()
    if window is None:
        return None
    pane = None
    try:
        from . import holder
        w = holder.widget("MainPane")
        if w is not None and w.isVisible() and w.width() > 0 and w.height() > 0:
            pane = _global_rect(w)
    except Exception:                                        # noqa: BLE001
        pane = None
    return look.area(pane, _global_rect(window))


def in_timebar_band(point):
    """The point is in the Time Bar's bottom-edge band: the bottom-right corner is
    the bar's (it runs to the edge while the panel is hidden), not the panel's zone."""
    import sys
    bar = (getattr(sys, "_skeldar_timebar", None) or {}).get("edge")
    try:
        if bar is not None and bar.alive():
            window = bar._window_rect()
            if window:
                return rules.contains(bar._bands(window)[0], point)
    except Exception:                                        # noqa: BLE001
        pass
    return False


def nudge_timebar():
    """The Time Bar at the bottom edge placed again now (it steps aside for the
    side panel when the panel comes out, and back when it goes)."""
    import sys
    bar = (getattr(sys, "_skeldar_timebar", None) or {}).get("edge")
    try:
        if bar is not None and bar.alive():
            bar.place()
    except Exception:                                        # noqa: BLE001
        pass


def destroy_all():
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


class SideEdge(object):
    """Build the panel with `make_panel(parent, on_tab, on_pin, on_width)`; it comes
    out when the cursor rests on the right edge and goes when it leaves."""

    def __init__(self, make_panel, width=look.WIDTH, scale=1.0, parent=None, window_rect=None,
                 cursor=None, buttons=None, app_active=None, over_maya=None, motion=None,
                 on_tab=None, on_width=None, tick=None, on_reveal=None, capture=None, selected=None,
                 playing=None, timebar=None):
        q = hubqt.qt()
        QtCore, QtWidgets = q.QtCore, q.QtWidgets
        self._window_rect = window_rect or _window_rect
        self._cursor = cursor
        self._buttons = buttons
        self._app_active = app_active
        self._over_maya = over_maya
        self._on_tab = on_tab
        self._on_width = on_width
        self._tick = tick
        self._on_reveal = on_reveal
        self._capture = capture        # a seam: (host) -> QPixmap, for the tests
        self._selected = selected      # (2026-10-17) something selected: out and kept out
        self._playing = playing
        self._timebar = timebar
        self.closed = False            # sent away by the close button: the edge waits for the cursor to leave
        import maya_hubstyle
        self._face = maya_hubstyle.TOKENS["panel"]
        self.motion = motion
        self.scale = float(scale or 1.0)
        self.width = look.clamp_width(width)
        self.least = 0                # physical px Maya's borrowed forms ask for
        self._width0 = None
        self.pinned = False
        self.shown = False
        self.dwelt = 0.0
        self.hold = rules.Hold()
        self._slide = None
        self._rect = None
        if parent is None:
            parent = main_window()
        flags = QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
        host = QtWidgets.QWidget(parent, flags)
        host.setObjectName(HOST)
        host.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        layout = QtWidgets.QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        #  never grown by what it holds: Maya's Attribute Editor asks for more
        #  than the band, and a host that grew outran its mask (2026-10-17, live)
        layout.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)
        self.host = host
        self.panel = make_panel(host, self._tab_picked, self.set_pinned, self._grip)
        close = getattr(self.panel, "close_button", None)
        if close is not None:
            close.clicked.connect(lambda checked=False: self.close_by_hand())
        layout.addWidget(self.panel)
        controller = self

        class Overlay(QtWidgets.QWidget):
            """Over the panel while it bursts: the panel's picture, moving."""
            def paintEvent(self, event):
                painter = q.QtGui.QPainter(self)
                try:
                    controller.paint_burst(painter)
                except Exception:                            # noqa: BLE001 - a paint: never raise
                    print(traceback.format_exc())
                finally:
                    painter.end()

        self.overlay = Overlay(host)
        self.overlay.setObjectName("skeldarSidePanelBurst")
        self.overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.overlay.hide()

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
        self.hide_timer = timer(look.HIDE_MS, self.hide_due)
        self.place_timer = timer(PLACE_MS, self.place_tick, single=False)
        self.watch = timer(WATCH_MS, self.watch_tick, single=False)
        self.anim = timer(16, self.slide_tick, single=False)
        self.zone = timer(look.ZONE_POLL_MS, self.zone_tick, single=False)
        self.place()
        self.host.hide()
        self.sensor.show()
        self.sensor.raise_()
        self.place_timer.start()
        self.zone.start()

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

    def playing(self):
        """Maya is playing back: no timer ticks and no idle comes between frames, so
        the panel comes out at once and paints now (2026-10-17, «во время плей мода
        выделяю объект то панель не выезжает»)."""
        if self._playing is not None:
            return bool(self._playing())
        try:
            import maya.cmds as cmds
            return bool(cmds.play(q=True, state=True))
        except Exception:                                    # noqa: BLE001
            return False

    def timebar_out(self):
        """The Time Bar at the bottom edge is out: it stepped aside for this panel,
        and the panel hiding by itself would make it jump wider (2026-10-17, «таймслайдер
        меняет свой размер если панель закрывается»)."""
        if self._timebar is not None:
            return bool(self._timebar())
        import sys
        bar = (getattr(sys, "_skeldar_timebar", None) or {}).get("edge")
        try:
            return bool(bar is not None and bar.alive() and bar.shown)
        except Exception:                                    # noqa: BLE001
            return False

    def close_by_hand(self):
        """The close button: away now, whatever would keep it out; the edge does not
        bring it back until the cursor has left the edge's zone."""
        self.closed = True
        self.hold.held = self.hold.entered = False
        if self.pinned:
            self.set_pinned(False)
        self.conceal()

    def _waits_after_close(self, zone_rect):
        """True while the panel, closed by hand, waits for the cursor to leave."""
        if not self.closed:
            return False
        if rules.contains(zone_rect, self.cursor(), margin=2):
            return True
        self.closed = False
        return False

    def selected(self):
        """Something is selected in the scene (the panel is wanted then)."""
        if self._selected is not None:
            return bool(self._selected())
        try:
            import maya.cmds as cmds
            return bool(cmds.ls(selection=True, head=1))
        except Exception:                                    # noqa: BLE001
            return False

    def selection_changed(self):
        """2026-10-17 («если у нас не пустое выделение то она выезжает и не
        прячется ... показывать панель тогда когда она нужна»): something selected
        brings the panel out and keeps it out; nothing selected lets it go by the
        usual rules (the cursor over it, the pin, ... still keep it).
        True when this call brought it out."""
        if self.selected():
            self.hide_timer.stop()
            if not self.shown:
                self.reveal()
                return True
            return False
        if self.shown and not self.hide_timer.isActive():
            self.hide_timer.start()
        return False

    def over_maya(self):
        if self._over_maya:
            return self._over_maya()
        q = hubqt.qt()
        app = q.QtWidgets.QApplication
        if app.activePopupWidget() is not None or app.activeModalWidget() is not None:
            return False
        x, y = self.cursor()
        widget = app.widgetAt(x, y)
        if widget is None:
            return False
        top = widget.window()
        return top is main_window() or top is self.host or top is self.sensor

    def _motion(self):
        if self.motion is not None:
            return bool(self.motion)
        return bool(getattr(self.panel, "motion", True))

    def _guard(self, call):
        try:
            if self.alive():
                call()
        except Exception:                                    # noqa: BLE001 - a timer: never raise
            print(traceback.format_exc())

    def alive(self):
        return hubqt._valid(self.host)

    # placement -----------------------------------------------------------------------
    def place(self):
        window = self._window_rect()
        if not window:
            return
        rect = (tuple(window), self.width, self.least)
        if rect == self._rect:
            return
        self._rect = rect
        x, y, w, h = look.side_band(window, self.width, self.scale, self.least)
        self.host.setGeometry(x, y, w, h)
        if self._slide is None:
            self._full_mask()
        sx, sy, sw, sh = look.sensor_band(window, look.SENSOR_PX)
        self.sensor.setGeometry(sx, sy, sw, sh)

    def place_tick(self):
        self.place()
        if self._tick is not None:
            self._tick(self)

    def _full_mask(self):
        q = hubqt.qt()
        self.host.setMask(q.QtGui.QRegion(0, 0, max(1, self.host.width()),
                                          max(1, self.host.height())))
        self.host.update()

    def _host_rect(self):
        g = self.host.geometry()
        return g.x(), g.y(), g.width(), g.height()

    def _grip(self, dx, done):
        if self._width0 is None:
            self._width0 = self.width
        self.width = look.dragged_width(self._width0, dx, self.scale)
        self.place()
        if done:
            self._width0 = None
            if self._on_width is not None:
                self._on_width(self.width)

    def _tab_picked(self, tab):
        if self._on_tab is not None:
            self._on_tab(tab)

    # coming out -----------------------------------------------------------------------
    def sensor_entered(self):
        self.dwell.start()

    def zone_tick(self):
        if self.shown:
            self.dwelt = 0.0
            return
        window = self._window_rect()
        if not window:
            return
        zone = look.zone_band(window, self.scale)
        inside = rules.contains(zone, self.cursor())
        if self._waits_after_close(zone):
            inside = False
        if inside and (self.buttons() or not self.app_active() or not self.over_maya()
                       or in_timebar_band(self.cursor())):
            inside = False
        self.dwelt = look.zone_dwell(self.dwelt, inside, look.ZONE_POLL_MS)
        if self.dwelt >= look.ZONE_DWELL_MS:
            self.dwelt = 0.0
            self.reveal()

    def dwell_done(self):
        window = self._window_rect()
        if not window or not rules.contains(look.sensor_band(window, look.SENSOR_PX), self.cursor(),
                                            margin=2):
            return
        if self._waits_after_close(look.zone_band(window, self.scale)):
            return
        if rules.may_reveal(True, self.shown, self.buttons(), self.app_active()):
            self.reveal()

    def reveal(self, instant=False, held=False, tab=None):
        """Out (from the cursor's height); `held` keeps it out until the cursor has
        visited it and left (a reveal by command); `tab` shows that page."""
        if tab is not None:
            self.panel.set_tab(tab)
        if held:
            self.hold.start()
        if self.shown:
            if tab is not None and self._on_reveal is not None:
                self._on_reveal()
            return
        self.place()
        self.shown = True
        self.closed = False
        nudge_timebar()
        self.sensor.hide()
        if instant or not self._motion() or self.playing():
            self.host.show()
            self.host.raise_()
            self._start_slide(True, instant=True)
            self.watch.start()
            if self._on_reveal is not None:
                self._on_reveal()
            return
        #  the picture first, the panel invisible: Maya's editors brought up to date
        #  and painted once, then only the picture moves (the Time Bar's burst)
        self.host.setWindowOpacity(0.0)
        self._full_mask()
        self.host.show()
        self.host.raise_()
        if self._on_reveal is not None:
            self._on_reveal()
        picture = self._picture(settle=True)
        self._start_slide(True, picture=picture)
        self.host.setWindowOpacity(1.0)
        self.watch.start()

    def conceal(self, instant=False):
        if not self.shown:
            return
        self.shown = False
        self.watch.stop()
        self.hide_timer.stop()
        picture = None if (instant or not self._motion()) else self._picture()
        self._start_slide(False, instant=instant, picture=picture)

    # the burst ------------------------------------------------------------------------
    def _picture(self, settle=False):
        """The panel as it stands now, a QPixmap, or None. From DWM's copy of the
        window (no Maya paint code runs - trap 134); `settle` turns the event loop
        first so a panel just shown has painted."""
        if self._capture is not None:
            return self._capture(self.host)
        q = hubqt.qt()
        if settle:
            for _ in range(3):
                q.QtWidgets.QApplication.processEvents()
        try:
            from maya_graphoverlay import winstyle
            w, h = self.host.width(), self.host.height()
            data = winstyle.capture(int(self.host.winId()), w, h)
            if not data:
                return None
            image = q.QtGui.QImage(data, w, h, w * 4, q.QtGui.QImage.Format_RGB32).copy()
            return q.QtGui.QPixmap.fromImage(image)
        except Exception:                                    # noqa: BLE001 - no burst then
            return None

    def _start_slide(self, showing, instant=False, picture=None):
        if instant or not self._motion():
            self._slide = None
            self.anim.stop()
            self.overlay.hide()
            self._settle(showing)
            return
        g = self.host.geometry()
        gy = self.cursor()[1]
        h = g.height()
        cy = float(max(0, min(h, gy - g.y())))
        ui = float(getattr(self.panel, "ui", 1.0))
        self._slide = {"t0": self.panel.clock(), "showing": bool(showing), "cy": cy,
                       "picture": picture, "rows": look.rows(h, ui), "ui": ui,
                       "far": max(cy, h - cy),
                       "folded": look.close_folded(cy, h, ui) + look.CLOSE_AFTER_MS}
        if picture is not None:
            self.overlay.setGeometry(0, 0, self.host.width(), h)
            self.overlay.show()
            self.overlay.raise_()
        if showing:
            self._mask_span(cy, cy)
        self.anim.start()

    def slide_tick(self):
        b = self._slide
        if b is None:
            self.anim.stop()
            return
        h = self.host.height()
        age = self.panel.clock() - b["t0"]
        burst = b["picture"] is not None
        if b["showing"]:
            u = age / look.UNROLL_MS
            done = age >= (look.open_total(b["cy"], h, b["ui"]) if burst else look.UNROLL_MS)
        else:
            after = b["folded"] if burst else 0.0
            u = (age - after) / look.CLOSE_MS
            done = u >= 1
        if b["showing"] or u > 0:
            y0, y1 = look.unroll(max(0.0, u), b["cy"], h, b["showing"])
            self._mask_span(y0, y1, paint=not burst)
        if burst:
            self.overlay.update()
        if done:
            self.anim.stop()
            self._slide = None
            self.overlay.hide()
            self._settle(b["showing"])

    def paint_burst(self, painter):
        """The overlay's picture `age` ms into the burst: the panel's face, and each
        row of the picture popping in (nearest the cursor first) or folding away
        (farthest first), scaled about its own middle."""
        b = self._slide
        if b is None or b["picture"] is None:
            return
        q = hubqt.qt()
        QtCore = q.QtCore
        w = float(self.host.width())
        age = self.panel.clock() - b["t0"]
        painter.fillRect(self.overlay.rect(), q.QtGui.QColor(self._face))
        painter.setRenderHint(q.QtGui.QPainter.SmoothPixmapTransform, True)
        for row in b["rows"]:
            mid = look.row_middle(row)
            if b["showing"]:
                scale, opacity = look.popping(age, look.open_delay(mid - b["cy"], b["ui"]))
            else:
                scale, opacity = look.folding(age, look.fold_delay(mid - b["cy"], b["ui"], b["far"]))
            if opacity <= 0.0:
                continue
            painter.save()
            painter.setOpacity(opacity)
            painter.translate(w / 2.0, mid)
            painter.scale(scale, scale)
            painter.translate(-w / 2.0, -mid)
            rect = QtCore.QRectF(0, row[0], w, row[1] - row[0])
            painter.drawPixmap(rect, b["picture"], rect)
            painter.restore()

    def _mask_span(self, y0, y1, paint=True):
        q = hubqt.qt()
        w, h = self.host.width(), self.host.height()
        y0, y1 = max(0.0, y0), min(float(h), y1)
        if y1 - y0 < 1:
            y1 = y0 + 1
        if y1 - y0 >= h - 0.5:
            self._full_mask()
            return
        radius = 12 * getattr(self.panel, "ui", 1.0) * (1 - (y1 - y0) / float(max(h, 1)))
        path = q.QtGui.QPainterPath()
        path.addRoundedRect(q.QtCore.QRectF(0, y0, w, y1 - y0), radius, radius)
        self.host.setMask(q.QtGui.QRegion(path.toFillPolygon().toPolygon()))
        if paint:
            self.host.update()

    def repaint_all(self):
        """Every widget in the panel asked to paint again. A mask growing over Maya's
        borrowed editors exposes them without a paint: the Attribute Editor's
        values came only where the mouse passed (2026-10-17, live)."""
        q = hubqt.qt()
        QWidget = q.QtWidgets.QWidget
        self.host.update()
        asked = 0
        #  QWidget.update unbound: an item view's own update() wants an index
        #  (QTableView.update() raised TypeError in Maya's Attribute Editor)
        for widget in self.host.findChildren(QWidget):
            try:
                QWidget.update(widget)
                asked += 1
            except (RuntimeError, TypeError):
                pass
        if self.playing():
            self.host.repaint()       # no idle comes between frames of playback (trap 269)
        return asked

    def _settle(self, showing):
        if showing:
            self._full_mask()
            self.repaint_all()
            return
        self.host.hide()
        nudge_timebar()
        self._full_mask()
        self.sensor.show()
        self.sensor.raise_()

    # going back -----------------------------------------------------------------------
    def watch_tick(self):
        inside = rules.contains(self._host_rect(), self.cursor())
        if inside:
            self.hold.enter()
            self.hide_timer.stop()
            return
        self.hold.leave()
        if self.buttons() and self.hold.held:
            self.hold.press_outside()
        if not self.hide_timer.isActive():
            self.hide_timer.start()

    def blockers(self):
        q = hubqt.qt()
        app = q.QtWidgets.QApplication
        focus = app.focusWidget()
        typing = bool(focus is not None and self.host.isAncestorOf(focus)
                      and isinstance(focus, (q.QtWidgets.QLineEdit, q.QtWidgets.QAbstractSpinBox,
                                             q.QtWidgets.QTextEdit)))
        return look.blockers(pinned=self.pinned, held=self.hold.held,
                             inside=rules.contains(self._host_rect(), self.cursor()),
                             buttons=self.buttons(), popup=app.activePopupWidget() is not None,
                             modal=app.activeModalWidget() is not None, typing=typing,
                             dragging=self._width0 is not None, selected=self.selected(),
                             timebar=self.timebar_out())

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
        self.panel.set_pinned(self.pinned)
        if not on and self.shown:
            self.hide_timer.start()

    def destroy(self):
        for t in (self.dwell, self.hide_timer, self.place_timer, self.watch, self.anim, self.zone):
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
