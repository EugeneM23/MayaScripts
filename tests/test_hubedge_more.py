"""maya_hubedge - the rest of the edge panel: its seams to Maya (the main window,
the work area, the viewport under its icon bar, the Time Bar's band), the
grips' and the windows' own mouse events, a grip kept on top of its card, the
follow, the slides' turns, and a controller whose windows went.

Offscreen Qt with sent events; animations driven by setting their current time
(no sleeping); `maya.cmds` / `maya.OpenMayaUI` stood in for one entry at a time.
The edge's and the Time Bar's state on `sys` are swapped for each test.
"""

import contextlib
import io
import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets
import shiboken6

import maya_edgerules as rules
import maya_hubburst as hubburst
import maya_hubedge as hubedge
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

_MISSING = object()


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@contextlib.contextmanager
def maya_modules(**fakes):
    """`maya.<name>` stood in for, one entry at a time (sys.modules and the
    package's attribute both, as `import maya.X as y` reads them), and put back."""
    import maya
    saved = []
    for name, fake in fakes.items():
        key = "maya." + name
        saved.append((key, sys.modules.get(key, _MISSING), name,
                      maya.__dict__.get(name, _MISSING)))
        sys.modules[key] = fake
        setattr(maya, name, fake)
    try:
        yield
    finally:
        for key, module, name, attr in reversed(saved):
            if module is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = module
            if attr is _MISSING:
                if name in maya.__dict__:
                    delattr(maya, name)
            else:
                setattr(maya, name, attr)


def pointer(widget):
    return shiboken6.getCppPointer(widget)[0]


def fake_omui(main_window=lambda: 0, controls=None, views=None):
    """A maya.OpenMayaUI: MQtUtil.mainWindow / findControl, and M3dView, whose
    getM3dViewFromModelPanel hands the view of `views[panel]` (a QWidget)."""
    controls = controls or {}
    views = views or {}

    class M3dView(object):
        def __init__(self):
            self._ptr = 0

        @staticmethod
        def getM3dViewFromModelPanel(panel, view):     # noqa: N802
            widget = views.get(panel)
            view._ptr = pointer(widget) if widget is not None else 0

        def widget(self):
            return self._ptr

    module = types.ModuleType("maya.OpenMayaUI")
    module.MQtUtil = types.SimpleNamespace(
        mainWindow=main_window,
        findControl=lambda name: (pointer(controls[name]) if name in controls
                                  else 0))
    module.M3dView = M3dView
    return module


class FakePanels(object):
    """maya.cmds as _drawing_top asks it: the visible panels and their types."""

    def __init__(self, panels):
        self.panels = panels

    def getPanel(self, visiblePanels=False, typeOf=None):  # noqa: N802
        if visiblePanels:
            return list(self.panels)
        return self.panels.get(typeOf)


class FakeBar(object):
    """The Time Bar's edge as the rail asks it: alive, and its host's top."""

    def __init__(self, top, alive=True):
        self._alive = alive
        self.host = types.SimpleNamespace(
            geometry=lambda: QtCore.QRect(0, top, 1500, 84))

    def alive(self):
        return self._alive


def finish(anim):
    """An animation run to its end now (its last value, then `finished`)."""
    anim.setCurrentTime(anim.duration())


def mouse(kind, button, buttons, gx, gy):
    return QtGui.QMouseEvent(kind, QtCore.QPointF(2, 2), QtCore.QPointF(gx, gy),
                             button, buttons, QtCore.Qt.NoModifier)


def enter():
    at = QtCore.QPointF(2, 2)
    return QtGui.QEnterEvent(at, at, at)


class Isolated(unittest.TestCase):
    """The edge's and the Time Bar's session state on `sys`, fresh and put back;
    every Edge made through `make` destroyed after the test."""

    def setUp(self):
        self.app = _app()
        for name in ("_skeldar_hubedge", "_skeldar_timebar"):
            saved = getattr(sys, name, _MISSING)
            self.addCleanup(self._put_back, name, saved)
            if saved is not _MISSING:
                delattr(sys, name)

    @staticmethod
    def _put_back(name, saved):
        if saved is _MISSING:
            if hasattr(sys, name):
                delattr(sys, name)
        else:
            setattr(sys, name, saved)

    def make(self, **kw):
        args = dict(scale=1.0, width=360, motion=lambda: False,
                    work_area=lambda: (0, 0, 1600, 900),
                    cursor=lambda: (900, 300), buttons=lambda: False,
                    app_active=lambda: True)
        args.update(kw)
        edge = hubedge.Edge(**args)
        self.addCleanup(edge.destroy)
        return edge

    def widget(self, rect=None, parent=None, shown=True):
        widget = QtWidgets.QWidget(parent)
        if rect is not None:
            widget.setGeometry(*rect)
        if shown:
            widget.show()
        if parent is None:
            self.addCleanup(widget.deleteLater)
        return widget


# ------------------------------------------------------------- the Maya seams

class MainWindow(Isolated):

    def test_no_maya_ui_no_window(self):
        with mock.patch.object(hubqt, "_maya_ui_ok", lambda: False):
            self.assertIsNone(hubedge.main_window())

    def test_maya_s_main_window_wrapped_from_its_pointer(self):
        window = self.widget(shown=False)
        with mock.patch.object(hubqt, "_maya_ui_ok", lambda: True), \
                maya_modules(OpenMayaUI=fake_omui(lambda: pointer(window))):
            found = hubedge.main_window()
        self.assertEqual(pointer(found), pointer(window))

    def test_a_null_pointer_or_a_failure_is_no_window(self):
        def broken():
            raise RuntimeError("no main window yet")
        for answer in (lambda: 0, broken):
            with mock.patch.object(hubqt, "_maya_ui_ok", lambda: True), \
                    maya_modules(OpenMayaUI=fake_omui(answer)):
                self.assertIsNone(hubedge.main_window())


class MayaWorkArea(Isolated):
    """The work area of the screen holding Maya's window."""

    def test_the_screen_of_maya_s_window(self):
        window = self.widget((40, 40, 300, 200))
        with mock.patch.object(hubedge, "main_window", lambda: window):
            area = hubedge._maya_work_area()
        self.assertEqual(area, window.screen().availableGeometry().getRect())

    def test_a_window_that_cannot_say_its_screen_falls_back_on_the_primary(self):
        class Gone(object):
            def screen(self):
                raise RuntimeError("Internal C++ object already deleted")
        with mock.patch.object(hubedge, "main_window", lambda: Gone()):
            area = hubedge._maya_work_area()
        primary = QtGui.QGuiApplication.primaryScreen()
        self.assertEqual(area, primary.availableGeometry().getRect())

    def test_no_screen_at_all_is_full_hd(self):
        gui = types.SimpleNamespace(QGuiApplication=types.SimpleNamespace(
            primaryScreen=lambda: None))
        with mock.patch.object(hubedge, "main_window", lambda: None), \
                mock.patch.object(hubqt, "qt",
                                  lambda: types.SimpleNamespace(QtGui=gui)):
            self.assertEqual(hubedge._maya_work_area(), (0, 0, 1920, 1080))


class ViewportArea(Isolated):
    """Maya's MainPane, below the icon bar of the model panel standing on the
    rail's side (2026-10-17)."""

    PANE = (100, 150, 1500, 700)

    def area(self, side="left", views=None, panels=None, controls=None):
        pane = controls if controls is not None else {"MainPane": self.pane}
        omui = fake_omui(controls=pane, views=views or {})
        cmds = FakePanels(panels or {})
        with mock.patch.object(hubqt, "_maya_ui_ok", lambda: True), \
                maya_modules(OpenMayaUI=omui, cmds=cmds):
            return hubedge._viewport_area(side)

    def setUp(self):
        super(ViewportArea, self).setUp()
        self.pane = self.widget(self.PANE)

    def test_no_maya_ui_no_area(self):
        with mock.patch.object(hubqt, "_maya_ui_ok", lambda: False):
            self.assertIsNone(hubedge._viewport_area())

    def test_no_main_pane_no_area(self):
        self.assertIsNone(self.area(controls={}))

    def test_a_hidden_pane_is_no_area(self):
        self.pane.hide()
        self.assertIsNone(self.area())

    def test_the_area_starts_below_the_viewport_s_icon_bar(self):
        view = self.widget((100, 228, 700, 500))
        found = self.area(views={"modelPanel4": view},
                          panels={"modelPanel4": "modelPanel"})
        self.assertEqual(found, (100, 228, 1500, 622))

    def test_no_model_panel_on_the_rail_s_side_is_the_whole_pane(self):
        view = self.widget((600, 228, 700, 500))
        found = self.area(views={"modelPanel4": view},
                          panels={"modelPanel4": "modelPanel"})
        self.assertEqual(found, self.PANE)

    def test_a_drawing_top_too_low_is_not_taken(self):
        view = self.widget((100, 760, 700, 80))         # under the pane's last 100 px
        found = self.area(views={"modelPanel4": view},
                          panels={"modelPanel4": "modelPanel"})
        self.assertEqual(found, self.PANE)

    def test_on_the_right_the_panel_on_the_pane_s_right(self):
        view = self.widget((900, 240, 700, 500))         # its right edge at 1600
        panels = {"modelPanel2": "modelPanel"}
        self.assertEqual(self.area("right", {"modelPanel2": view}, panels),
                         (100, 240, 1500, 610))
        self.assertEqual(self.area("left", {"modelPanel2": view}, panels),
                         self.PANE)

    def test_a_failure_is_no_area(self):
        def broken(_name):
            raise RuntimeError("no UI")
        omui = fake_omui()
        omui.MQtUtil.findControl = broken
        with mock.patch.object(hubqt, "_maya_ui_ok", lambda: True), \
                maya_modules(OpenMayaUI=omui):
            self.assertIsNone(hubedge._viewport_area())


class DrawingTop(Isolated):
    """The top of the drawing area of the model panel on an edge."""

    def top(self, edge, side, views, panels):
        with maya_modules(OpenMayaUI=fake_omui(views=views),
                          cmds=FakePanels(panels)):
            return hubedge._drawing_top(edge, side)

    def test_the_upper_of_two_stacked_panels_on_the_edge(self):
        upper = self.widget((100, 228, 700, 260))
        lower = self.widget((104, 500, 700, 300))       # within 8 px of the edge
        views = {"modelPanel1": lower, "modelPanel4": upper}
        panels = {"modelPanel1": "modelPanel", "outlinerPanel1": "outlinerPanel",
                  "modelPanel4": "modelPanel", "modelPanel9": "modelPanel"}
        self.assertEqual(self.top(100, "left", views, panels), 228)

    def test_none_without_a_model_panel_on_the_edge(self):
        far = self.widget((700, 228, 700, 260))
        self.assertIsNone(self.top(100, "left", {"modelPanel4": far},
                                   {"modelPanel4": "modelPanel"}))
        self.assertIsNone(self.top(100, "left", {}, {}))

    def test_a_failure_is_none(self):
        class Broken(object):
            def getPanel(self, **_kw):                     # noqa: N802
                raise RuntimeError("no UI")
        with maya_modules(OpenMayaUI=fake_omui(), cmds=Broken()):
            self.assertIsNone(hubedge._drawing_top(100))


class AboveTimebar(Isolated):
    """The rail panel ends above the Time Bar's band while it stands at the
    bottom edge (2026-10-17)."""

    AREA = (100, 150, 1500, 700)

    def with_bar(self, bar):
        sys._skeldar_timebar = {"edge": bar}
        return hubedge._above_timebar(self.AREA)

    def test_no_time_bar_leaves_the_area(self):
        self.assertEqual(hubedge._above_timebar(self.AREA), self.AREA)
        self.assertEqual(self.with_bar(None), self.AREA)

    def test_a_bar_that_went_leaves_the_area(self):
        self.assertEqual(self.with_bar(FakeBar(700, alive=False)), self.AREA)

    def test_the_area_ends_at_the_bar_s_top(self):
        self.assertEqual(self.with_bar(FakeBar(700)), (100, 150, 1500, 550))

    def test_a_bar_below_the_area_leaves_it(self):
        self.assertEqual(self.with_bar(FakeBar(900)), self.AREA)
        self.assertEqual(self.with_bar(FakeBar(120)), self.AREA)

    def test_a_bar_that_cannot_say_where_it_is_leaves_the_area(self):
        bar = FakeBar(700)

        def gone():
            raise RuntimeError("Internal C++ object already deleted")
        bar.host = types.SimpleNamespace(geometry=gone)
        self.assertEqual(self.with_bar(bar), self.AREA)


class RailWorkArea(Isolated):
    """A rail with no work-area seam stands on the viewport, above the Time Bar."""

    def rail(self):
        return self.make(rail=True, rest=lambda: 40, work_area=None)

    def test_the_rail_stands_on_the_viewport(self):
        with mock.patch.object(hubedge, "_viewport_area",
                               lambda side="left": (100, 150, 1500, 700)):
            edge = self.rail()
        self.assertEqual(edge.host.geometry().getRect(), (100, 150, 360, 700))

    def test_the_rail_ends_above_the_time_bar(self):
        sys._skeldar_timebar = {"edge": FakeBar(700)}
        with mock.patch.object(hubedge, "_viewport_area",
                               lambda side="left": (100, 150, 1500, 700)):
            edge = self.rail()
        self.assertEqual(edge.host.geometry().getRect(), (100, 150, 360, 550))

    def test_no_viewport_the_maya_work_area(self):
        with mock.patch.object(hubedge, "_viewport_area", lambda side="left": None), \
                mock.patch.object(hubedge, "_maya_work_area",
                                  lambda: (0, 0, 800, 600)):
            edge = self.rail()
        self.assertEqual(edge.host.geometry().getRect(), (0, 0, 360, 600))


# --------------------------------------------------------------- on top

class OnTop(Isolated):

    def setUp(self):
        super(OnTop, self).setUp()
        self.parent = self.widget((0, 0, 200, 200))
        self.a = self.widget((0, 0, 20, 20), self.parent)
        self.b = self.widget((0, 0, 20, 20), self.parent)
        self.c = self.widget((0, 0, 20, 20), self.parent)

    def test_a_window_with_no_parent_is_on_top(self):
        self.assertTrue(hubedge._on_top(self.parent))

    def test_the_last_raised_child_is_on_top(self):
        self.assertTrue(hubedge._on_top(self.c))
        self.assertFalse(hubedge._on_top(self.a))
        self.a.raise_()
        self.assertTrue(hubedge._on_top(self.a))
        self.assertFalse(hubedge._on_top(self.c))

    def test_siblings_named_beside_and_hidden_ones_do_not_count(self):
        self.assertTrue(hubedge._on_top(self.a, (self.b, self.c, None)))
        self.b.hide()
        self.c.hide()
        self.assertTrue(hubedge._on_top(self.a))

    def test_objects_that_are_not_widgets_do_not_count(self):
        QtCore.QTimer(self.parent)                  # a child, not a widget
        self.assertTrue(hubedge._on_top(self.c))

    def test_a_stranger_in_beside_is_not_on_top(self):
        self.assertFalse(hubedge._on_top(self.a, (object(),)))


class GripsKeptOnTop(Isolated):
    """2026-10-27 (`_on_top`): something raised over the card's grips is put back
    under them by the next follow - and only then are they raised."""

    def setUp(self):
        super(GripsKeptOnTop, self).setUp()
        self.card = [60, 10, 280, 200]
        self.edge = self.make(rail=True, rest=lambda: 40,
                              work_area=lambda: (100, 150, 1500, 700),
                              card=lambda: tuple(self.card),
                              on_height=lambda logical, save: None)
        self.edge.reveal()
        self.edge._place_grips()
        self.grips = (self.edge.grip, self.edge.hgrip)

    def test_a_widget_raised_over_the_grips_goes_back_under_them(self):
        cover = self.widget((0, 0, 400, 400), self.edge.host)
        cover.raise_()
        self.assertFalse(hubedge._on_top(self.edge.hgrip, self.grips))
        self.assertFalse(hubedge._on_top(self.edge.grip, self.grips))
        self.edge._place_grips()
        self.assertTrue(hubedge._on_top(self.edge.grip, self.grips))
        self.assertTrue(hubedge._on_top(self.edge.hgrip, self.grips))

    def test_the_grips_on_top_are_not_raised_again(self):
        raised = []
        for grip in self.grips:
            grip.raise_ = lambda _g=grip: raised.append(_g)
        try:
            self.edge._place_grips()
        finally:
            for grip in self.grips:
                del grip.raise_
        self.assertEqual(raised, [])


# ------------------------------------------------------- the windows' events

class WindowEvents(Isolated):
    """The sensor's and the host's own Enter and Leave."""

    def test_the_cursor_entering_the_sensor_starts_the_dwell_and_leaving_stops_it(self):
        edge = self.make()
        QtWidgets.QApplication.sendEvent(edge.sensor, enter())
        self.assertTrue(edge.dwell.isActive())
        QtWidgets.QApplication.sendEvent(edge.sensor, QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertFalse(edge.dwell.isActive())

    def test_leaving_the_host_starts_the_hide_and_entering_cancels_it(self):
        edge = self.make()
        edge.reveal()
        QtWidgets.QApplication.sendEvent(edge.host, QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertTrue(edge.hide.isActive())
        QtWidgets.QApplication.sendEvent(edge.host, enter())
        self.assertFalse(edge.hide.isActive())

    def test_a_qt5_event_gives_its_global_pos(self):
        class Qt5Event(object):
            def globalPos(self):                          # noqa: N802
                return QtCore.QPoint(17, 23)
        self.assertEqual(hubedge._global_point(Qt5Event()), (17, 23))


class WidthGripMouse(Isolated):
    """The width grip driven by real mouse events."""

    def setUp(self):
        super(WidthGripMouse, self).setUp()
        self.widths = []
        self.edge = self.make(on_width=self.widths.append)
        self.edge.reveal()
        self.grip = self.edge.grip

    def send(self, kind, button, buttons, gx):
        event = mouse(kind, button, buttons, gx, 300)
        QtWidgets.QApplication.sendEvent(self.grip, event)
        return event

    def test_press_drag_release_widens_and_remembers(self):
        press = self.send(QtCore.QEvent.MouseButtonPress, QtCore.Qt.LeftButton,
                          QtCore.Qt.LeftButton, 360)
        self.assertTrue(press.isAccepted())
        self.send(QtCore.QEvent.MouseMove, QtCore.Qt.NoButton,
                  QtCore.Qt.LeftButton, 460)
        self.assertEqual(self.edge.host.width(), 460)
        self.assertEqual(self.widths, [])
        self.send(QtCore.QEvent.MouseButtonRelease, QtCore.Qt.LeftButton,
                  QtCore.Qt.NoButton, 460)
        self.assertEqual(self.widths, [460])

    def test_a_right_press_starts_no_drag(self):
        press = self.send(QtCore.QEvent.MouseButtonPress, QtCore.Qt.RightButton,
                          QtCore.Qt.RightButton, 360)
        self.assertFalse(press.isAccepted())
        self.send(QtCore.QEvent.MouseMove, QtCore.Qt.NoButton,
                  QtCore.Qt.RightButton, 500)
        self.assertEqual(self.edge.host.width(), 360)
        self.send(QtCore.QEvent.MouseButtonRelease, QtCore.Qt.RightButton,
                  QtCore.Qt.NoButton, 500)
        self.assertEqual(self.widths, [])


class HeightGripMouse(Isolated):
    """The rail card's bottom grip driven by real mouse events."""

    def setUp(self):
        super(HeightGripMouse, self).setUp()
        self.card = [60, 10, 280, 200]
        self.heights = []
        self.edge = self.make(rail=True, rest=lambda: 40,
                              work_area=lambda: (100, 150, 1500, 700),
                              card=lambda: tuple(self.card),
                              on_height=self.set_height)
        self.edge.reveal()
        self.edge._place_grips()

    def set_height(self, logical, save):
        self.heights.append((logical, save))
        if logical is not None:
            self.card[3] = logical

    def send(self, kind, button, buttons, gy):
        event = mouse(kind, button, buttons, 200, gy)
        QtWidgets.QApplication.sendEvent(self.edge.hgrip, event)
        return event

    def test_press_drag_release_sets_the_card_s_height(self):
        press = self.send(QtCore.QEvent.MouseButtonPress, QtCore.Qt.LeftButton,
                          QtCore.Qt.LeftButton, 500)
        self.assertTrue(press.isAccepted())
        self.send(QtCore.QEvent.MouseMove, QtCore.Qt.NoButton,
                  QtCore.Qt.LeftButton, 560)
        self.assertEqual(self.heights, [(260, False)])
        self.send(QtCore.QEvent.MouseButtonRelease, QtCore.Qt.LeftButton,
                  QtCore.Qt.NoButton, 560)
        self.assertEqual(self.heights[-1], (260, True))

    def test_a_right_press_starts_no_drag(self):
        press = self.send(QtCore.QEvent.MouseButtonPress, QtCore.Qt.RightButton,
                          QtCore.Qt.RightButton, 500)
        self.assertFalse(press.isAccepted())
        self.send(QtCore.QEvent.MouseMove, QtCore.Qt.NoButton,
                  QtCore.Qt.RightButton, 600)
        self.send(QtCore.QEvent.MouseButtonRelease, QtCore.Qt.RightButton,
                  QtCore.Qt.NoButton, 600)
        self.assertEqual(self.heights, [])
        self.assertEqual(self.card[3], 200)

    def test_a_double_click_after_a_press_ends_the_drag(self):
        self.send(QtCore.QEvent.MouseButtonPress, QtCore.Qt.LeftButton,
                  QtCore.Qt.LeftButton, 500)
        self.send(QtCore.QEvent.MouseButtonDblClick, QtCore.Qt.LeftButton,
                  QtCore.Qt.LeftButton, 500)
        self.assertEqual(self.heights, [(None, True)])
        self.send(QtCore.QEvent.MouseMove, QtCore.Qt.NoButton,
                  QtCore.Qt.LeftButton, 600)
        self.assertEqual(self.heights, [(None, True)])   # no drag left over


class PressWatchFailing(Isolated):

    def test_an_edge_raising_on_a_press_never_breaks_the_application_s_events(self):
        pressed = []

        class Other(QtWidgets.QWidget):
            def mousePressEvent(self, event):              # noqa: N802
                pressed.append(1)

        other = Other()
        self.addCleanup(other.deleteLater)
        other.show()
        edge = self.make(cursor=lambda: (900, 300))
        edge.reveal(hold=True)
        self.assertTrue(edge._watching)

        def boom(_point):
            raise RuntimeError("the edge broke")
        edge.press_at = boom
        QtWidgets.QApplication.sendEvent(
            other, mouse(QtCore.QEvent.MouseButtonPress, QtCore.Qt.LeftButton,
                         QtCore.Qt.LeftButton, 900, 300))
        self.assertEqual(pressed, [1])
        self.assertTrue(edge.hold.held)


# ------------------------------------------------------------- the follow

class Follow(Isolated):

    def setUp(self):
        super(Follow, self).setUp()
        self.viewport = (100, 150, 1500, 700)
        self.card = [(60, 10, 280, 200)]
        self.broken_area = False
        self.moving = False

    def rail(self, **kw):
        def area():
            if self.broken_area:
                raise RuntimeError("no viewport")
            return self.viewport
        args = dict(rail=True, rest=lambda: 40, work_area=area,
                    motion=lambda: self.moving, shape=lambda: self.card)
        args.update(kw)
        return self.make(**args)

    def test_a_work_area_that_raises_leaves_the_panel_where_it_stands(self):
        edge = self.rail()
        self.broken_area = True
        self.viewport = (0, 0, 800, 600)
        edge._follow()
        self.assertEqual(edge.host.geometry().getRect(), (100, 150, 360, 700))

    def test_no_follow_while_the_card_slides_then_it_follows(self):
        self.moving = True
        edge = self.rail()
        edge.reveal()
        self.assertTrue(edge.sliding())
        self.viewport = (0, 100, 1200, 600)
        edge._follow()
        self.assertEqual(edge.host.geometry().getRect(), (100, 150, 360, 700))
        finish(edge._anim)
        self.assertFalse(edge.sliding())
        self.assertEqual(edge.frame, edge.host.width())
        edge._follow()
        self.assertEqual(edge.host.geometry().getRect(), (0, 100, 360, 600))

    def test_a_still_area_follows_the_card_growing(self):
        edge = self.rail()
        edge.reveal()
        edge._follow()                              # the area seen
        self.assertFalse(edge.host.mask().contains(QtCore.QPoint(100, 400)))
        self.card = [(60, 10, 280, 500)]
        edge._follow()
        self.assertTrue(edge.host.mask().contains(QtCore.QPoint(100, 400)))

    def test_a_shape_that_raises_shows_the_rail_alone(self):
        edge = self.rail()
        edge.reveal()
        edge._follow()

        def broken():
            raise RuntimeError("card gone")
        edge.shape = broken
        edge._follow()
        mask = edge.host.mask()
        self.assertTrue(mask.contains(QtCore.QPoint(20, 300)))      # the rail
        self.assertFalse(mask.contains(QtCore.QPoint(100, 100)))    # no card
        self.assertEqual(edge.visible_rects(), [(100, 150, 40, 700)])


# --------------------------------------------------------- rest and rects

class RestAndRects(Isolated):

    def test_the_hover_panel_has_no_rest(self):
        self.assertEqual(self.make().rest_px(), 0)

    def test_a_rest_that_raises_is_none(self):
        def broken():
            raise RuntimeError("rail gone")
        edge = self.make(rail=True, rest=broken)
        self.assertEqual(edge.rest_px(), 0)

    def test_the_hover_panel_shows_one_rect_out_and_none_in(self):
        edge = self.make()
        self.assertEqual(edge.visible_rects(), [])
        self.assertIsNone(edge.visible_rect())
        edge.reveal()
        self.assertEqual(edge.visible_rects(), [(0, 0, 360, 900)])

    def test_a_conceal_of_a_hidden_panel_does_nothing(self):
        edge = self.make()
        edge.conceal()
        self.assertFalse(edge.shown)
        self.assertFalse(edge.sliding())
        self.assertTrue(edge.sensor.isVisible())

    def test_a_least_width_that_raises_asks_nothing(self):
        def broken():
            raise RuntimeError("card gone")
        edge = self.make(rail=True, rest=lambda: 40, least=broken)
        self.assertEqual(edge.least_width(), 0)
        self.assertEqual(edge.shown_width(), 360)


class MotionThatRaises(Isolated):
    """A motion seam that raises: the move happens at once."""

    def broken(self):
        raise RuntimeError("no optionVar")

    def test_the_rail_card_comes_out_whole(self):
        edge = self.make(rail=True, rest=lambda: 40, motion=self.broken)
        edge.reveal()
        self.assertTrue(edge.shown)
        self.assertFalse(edge.sliding())
        self.assertEqual(edge.frame, edge.host.width())

    def test_the_hover_panel_comes_out_whole(self):
        edge = self.make(motion=self.broken)
        edge.reveal()
        self.assertFalse(edge.sliding())
        self.assertEqual((edge.frame, edge.slot.x()), (edge.host.width(), 0))

    def test_a_burst_stop_that_raises_still_moves(self):
        def stop():
            raise RuntimeError("burst gone")
        edge = self.make(rail=True, rest=lambda: 40, burst_stop=stop)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            edge.reveal()
        self.assertTrue(edge.shown)
        self.assertIn("burst gone", err.getvalue())


class StartBox(Isolated):
    """The burst's start box, before the first tick names a shape."""

    def setUp(self):
        super(StartBox, self).setUp()
        self.calls = []

    def seam(self, showing, origin, done, on_shape):
        self.calls.append((showing, origin))
        return True

    def rail(self, shape=None):
        return self.make(rail=True, rest=lambda: 40, motion=lambda: True,
                         work_area=lambda: (100, 150, 1500, 700),
                         burst=self.seam, shape=shape)

    def half(self):
        return (hubstyle.px(hubburst.START_HALF[0], 1.0),
                hubstyle.px(hubburst.START_HALF[1], 1.0))

    def test_with_no_card_the_box_stands_about_the_point(self):
        edge = self.rail()
        edge.reveal(origin=(140, 270))                  # host-local (40, 120)
        hx, hy = self.half()
        self.assertEqual(edge.burst_shape, (40 - hx, 120 - hy, 2 * hx, 2 * hy))
        self.assertEqual(self.calls, [(True, (140, 270))])

    def test_a_shape_that_raises_is_no_card(self):
        def broken():
            raise RuntimeError("card gone")
        edge = self.rail(shape=broken)
        edge.reveal(origin=(140, 270))
        hx, hy = self.half()
        self.assertEqual(edge.burst_shape, (40 - hx, 120 - hy, 2 * hx, 2 * hy))

    def test_the_burst_motion_s_box_is_kept_inside_the_card(self):
        card = (60, 10, 280, 200)
        edge = self.rail(shape=lambda: [card, (0, 0, 0, 0)])
        with mock.patch.object(hubburst, "MOTION", "burst"):
            edge.reveal(origin=(140, 270))
        hx, hy = self.half()
        lx, ly = hubburst.clamp_origin((40 - 60, 120 - 10), (280, 200),
                                       hubburst.ORIGIN_PAD)
        x0, y0 = max(0.0, lx - hx), max(0.0, ly - hy)
        x1, y1 = min(280.0, lx + hx), min(200.0, ly + hy)
        expected = (int(round(60 + x0)), int(round(10 + y0)),
                    int(round(x1 - x0)), int(round(y1 - y0)))
        self.assertEqual(edge.burst_shape, expected)
        x, y, w, h = edge.burst_shape
        self.assertTrue(60 <= x and x + w <= 340 and 10 <= y and y + h <= 210)
        self.assertGreaterEqual(x, 60)                  # pulled in from the rail


# ------------------------------------------------------------ the slide

class SlideTurns(Isolated):
    """The hover panel's slide turned back part way, driven frame by frame."""

    def setUp(self):
        super(SlideTurns, self).setUp()
        self.moving = True
        self.edge = self.make(work_area=lambda: (0, 0, 800, 600),
                              motion=lambda: self.moving)
        self.w = self.edge.host.width()

    def test_a_reveal_after_a_turned_back_frame_finishes_the_frame_then_the_hub(self):
        edge, w = self.edge, self.w
        edge.reveal()
        edge._anim.setCurrentTime(40)                   # the frame only, so far
        stood = edge.frame
        self.assertTrue(0 < stood < w)
        self.assertEqual(edge.slot.x(), -w)
        edge.conceal()                                  # turned back
        edge.reveal()                                   # and out again
        frame_phase = edge._anim
        self.assertIsNotNone(frame_phase)
        self.assertEqual(edge.slot.x(), -w)
        frame_phase.setCurrentTime(frame_phase.duration() // 2)
        self.assertGreater(edge.frame, stood)           # from where it stood, onward
        self.assertEqual(edge.slot.x(), -w)
        finish(frame_phase)                             # the frame whole: the hub's turn
        hub_phase = edge._anim
        self.assertIsNotNone(hub_phase)
        self.assertIsNot(hub_phase, frame_phase)
        self.assertEqual(edge.frame, w)
        finish(hub_phase)
        self.assertFalse(edge.sliding())
        self.assertEqual((edge.frame, edge.slot.x()), (w, 0))
        self.assertTrue(edge.host.isVisible())

    def test_a_reveal_right_after_a_conceal_began_stays_out(self):
        edge, w = self.edge, self.w
        self.moving = False
        edge.reveal()
        self.moving = True
        edge.conceal()                                  # a slide back, not one frame yet
        self.assertTrue(edge.sliding())
        edge.reveal()
        self.assertFalse(edge.sliding())
        self.assertTrue(edge.shown)
        self.assertEqual((edge.frame, edge.slot.x()), (w, 0))
        self.assertTrue(edge.host.isVisible())

    def test_a_slide_whose_hub_went_does_nothing_and_ends(self):
        edge = self.edge
        edge.reveal()
        anim = edge._anim
        shiboken6.delete(edge.slot)
        anim.setCurrentTime(200)
        finish(anim)
        self.assertFalse(edge.sliding())
        self.assertTrue(edge.shown)

    def test_a_slide_back_whose_hub_went_still_hides_the_panel(self):
        edge = self.edge
        self.moving = False
        edge.reveal()
        self.moving = True
        edge.conceal()
        anim = edge._anim
        shiboken6.delete(edge.slot)
        anim.setCurrentTime(anim.duration() // 2)
        finish(anim)
        self.assertFalse(edge.host.isVisible())
        self.assertTrue(edge.sensor.isVisible())


class WindowsGone(Isolated):
    """A controller whose host was deleted under it (an install, trap 102): every
    call is quiet and nothing is asked of the dead windows."""

    def check(self, edge):
        shiboken6.delete(edge.host)
        self.assertFalse(edge.alive())
        edge._follow()
        edge.place()
        edge._fit_slot()
        edge._set_frame(10)
        edge.reveal()
        edge.conceal()
        edge.host_entered()
        edge._place_grips()
        edge._slide_done(False)
        self.assertEqual(edge.blockers(), [])
        self.assertEqual(edge.visible_rects(), [])
        self.assertIsNone(edge.visible_rect())

    def test_the_hover_panel(self):
        self.check(self.make())

    def test_the_rail(self):
        self.check(self.make(rail=True, rest=lambda: 40, card=lambda: (60, 10, 280, 200),
                             on_height=lambda logical, save: None))


# ------------------------------------------------------------ the card

class CardRect(Isolated):

    def rail(self, card, on_height=None):
        return self.make(rail=True, rest=lambda: 40,
                         work_area=lambda: (100, 150, 1500, 700),
                         card=card, on_height=on_height)

    def test_no_card_no_rect_and_no_height(self):
        edge = self.rail(None)
        self.assertIsNone(edge.card_rect())
        self.assertEqual(edge.card_height(), 0)

    def test_a_card_that_raises_or_has_no_size_is_none(self):
        def broken():
            raise RuntimeError("card gone")
        self.assertIsNone(self.rail(broken).card_rect())
        self.assertIsNone(self.rail(lambda: (60, 10, 0, 200)).card_rect())
        self.assertIsNone(self.rail(lambda: None).card_rect())

    def test_a_card_s_rect_is_whole_pixels(self):
        edge = self.rail(lambda: (60.4, 10.0, 280.6, 199.9))
        self.assertEqual(edge.card_rect(), (60, 10, 280, 199))

    def test_with_no_height_seam_only_the_width_grip_stands_on_the_card(self):
        edge = self.rail(lambda: (60, 10, 280, 200))
        self.assertIsNone(edge.hgrip)
        edge.reveal()
        edge._place_grips()
        g = hubstyle.px(rules.GRIP_PX, 1.0)
        self.assertTrue(edge.grip.isVisible())
        self.assertEqual(edge.grip.geometry().getRect(), (340 - g, 10, g, 200 - g))

    def test_a_card_that_goes_takes_its_grips_with_it(self):
        card = [60, 10, 280, 200]
        edge = self.rail(lambda: tuple(card), on_height=lambda logical, save: None)
        edge.reveal()
        edge._place_grips()
        self.assertTrue(edge.hgrip.isVisible())
        card[2] = 0
        edge._place_grips()
        self.assertFalse(edge.grip.isVisible())
        self.assertFalse(edge.hgrip.isVisible())

    def test_the_hover_panel_has_no_card_grips(self):
        edge = self.make()
        edge.reveal()
        before = edge.grip.geometry().getRect()
        edge._place_grips()
        self.assertEqual(edge.grip.geometry().getRect(), before)

    def test_a_height_with_no_seam_does_nothing(self):
        edge = self.rail(lambda: (60, 10, 280, 200))
        edge.reveal()
        frame = edge.frame
        edge.set_height(300)
        self.assertEqual(edge.frame, frame)

    def test_a_height_seam_that_raises_still_places_the_grips(self):
        def broken(logical, save):
            raise RuntimeError("card gone")
        edge = self.rail(lambda: (60, 10, 280, 200), on_height=broken)
        edge.reveal()
        with contextlib.redirect_stderr(io.StringIO()) as err:
            edge.set_height(50)
        self.assertIn("card gone", err.getvalue())
        self.assertTrue(edge.hgrip.isVisible())
        self.assertEqual(edge.frame, edge.host.width())


# ------------------------------------------------------------ destroy_all

class DestroyAll(Isolated):

    def test_no_qt_nothing_to_destroy(self):
        with mock.patch.object(hubqt, "qt", lambda: None):
            self.assertEqual(hubedge.destroy_all(), 0)

    def test_a_window_dying_during_the_sweep_is_skipped_and_the_rest_go(self):
        class Dying(object):
            def objectName(self):                          # noqa: N802
                raise RuntimeError("Internal C++ object already deleted")
        edge = self.make()
        app = types.SimpleNamespace(
            instance=QtWidgets.QApplication.instance,
            topLevelWidgets=lambda: [Dying(), edge.host, edge.sensor])
        q = types.SimpleNamespace(QtWidgets=types.SimpleNamespace(QApplication=app),
                                  shiboken=shiboken6)
        with mock.patch.object(hubqt, "qt", lambda: q):
            self.assertEqual(hubedge.destroy_all(), 2)
        self.assertFalse(edge.alive())

    def test_a_registered_edge_whose_windows_went_is_forgotten(self):
        edge = self.make()
        hubedge.state()["edge"] = edge
        self.assertGreaterEqual(hubedge.destroy_all(), 2)
        self.assertIsNone(hubedge.state()["edge"])

    def test_a_registered_edge_that_cannot_answer_is_forgotten(self):
        class Broken(object):
            def alive(self):
                raise RuntimeError("an older module's edge")
        hubedge.state()["edge"] = Broken()
        hubedge.destroy_all()
        self.assertIsNone(hubedge.state()["edge"])

    def test_a_living_registered_edge_is_kept(self):
        class Living(object):
            def alive(self):
                return True
        living = Living()
        hubedge.state()["edge"] = living
        hubedge.destroy_all()
        self.assertIs(hubedge.state()["edge"], living)


if __name__ == "__main__":
    unittest.main()
