"""maya_graphoverlay.ghost - Maya's own graphEditor1 borrowed into a window of
ours and given back where it lived (2026-09-30 / 2026-10-02), on fakes.

Maya's panels are a fake `cmds` (a registry of scripted panels and the layout
each one's control stands in); MQtUtil is a fake that hands back real offscreen
Qt widgets; Win32 (`winstyle`) is a fake. The window itself is a real
offscreen QWidget, so the frame insets, the splitter and the chrome widgets are
Qt's own.
"""

import os
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtGui, QtOpenGL, QtWidgets
import shiboken6

from maya_graphoverlay import geometry, ghost

HOME = "MayaWindow|graphEditor1Window|graphEditor1Form"
PANE = ghost.HOST + "|" + ghost.LAYOUT + "|" + ghost.PANE


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _flush():
    app = _app()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()


def _pointer(qobject):
    return int(shiboken6.getCppPointer(qobject)[0])


class GhostCmds(object):
    """maya.cmds as the ghost drives it: scripted panels by name -> the path of
    their control ("" when unparented), layouts that exist, the current
    parent."""

    def __init__(self, borrowed=True, home=HOME):
        self.panels = {}
        if borrowed:
            self.panels[ghost.BORROWED] = (home + "|" + ghost.BORROWED
                                           if home else "")
        self.layouts = set([home]) if home else set()
        self.parent = "MayaWindow|mainForm"
        self.calls = []
        self.fail = False

    def scriptedPanel(self, name=None, **kw):
        self.calls.append(("scriptedPanel", name, kw))
        if self.fail:
            raise RuntimeError("no UI")
        if kw.get("exists"):
            return name in self.panels
        if kw.get("query"):
            if name not in self.panels:
                raise RuntimeError("no panel " + name)
            return self.panels[name] if kw.get("control") else None
        if kw.get("edit"):
            if "parent" in kw:
                self.panels[name] = kw["parent"] + "|" + name
            elif kw.get("unParent"):
                self.panels[name] = ""
            return name
        self.panels[name] = kw["parent"] + "|" + name
        return name

    def control(self, path, **kw):
        self.calls.append(("control", path, kw))
        if kw.get("query") and kw.get("parent"):
            return path.rsplit("|", 1)[0] if "|" in path else None
        return None

    def layout(self, name, **kw):
        return name in self.layouts

    def paneLayout(self, name, **kw):
        path = self.parent + "|" + name
        self.layouts.add(path)
        self.calls.append(("paneLayout", name, kw))
        return path

    def setParent(self, *args, **kw):
        if kw.get("query"):
            return self.parent
        self.calls.append(("setParent", args, kw))
        self.parent = args[0]
        return self.parent

    def deleteUI(self, name, **kw):
        self.calls.append(("deleteUI", name, kw))
        self.panels.pop(name, None)


class FakeQtUtil(object):

    def __init__(self):
        self.controls = {}      # control name -> a real QWidget

    def fullName(self, pointer):
        return ghost.HOST + "|" + ghost.LAYOUT

    def findControl(self, name):
        widget = self.controls.get(name)
        return _pointer(widget) if widget is not None else None


class FakeWinstyle(object):
    GHOST_ALPHA = ghost.winstyle.GHOST_ALPHA

    def __init__(self):
        self.visible = None         # fn(hwnd) -> rect or None
        self.window = None          # the whole window's rect or None
        self.alpha = self.GHOST_ALPHA
        self.data = True            # True: bytes of the asked size; None
        self.captured = []

    def visible_rect(self, hwnd):
        return self.visible(hwnd) if self.visible else None

    def window_rect(self, hwnd):
        return self.window

    def layered_alpha(self, hwnd):
        return self.alpha

    def capture(self, hwnd, width, height):
        self.captured.append((hwnd, width, height))
        if self.data is None:
            return None
        return bytes([40, 50, 60, 255]) * (width * height)


class GhostCase(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.real = (ghost.cmds, ghost.omui, ghost.winstyle)
        self.cmds = GhostCmds()
        self.qtutil = FakeQtUtil()
        self.win = FakeWinstyle()
        ghost.cmds = self.cmds
        ghost.omui = types.SimpleNamespace(MQtUtil=self.qtutil)
        ghost.winstyle = self.win
        self.ghosts = []
        self.made = []

    def tearDown(self):
        for g in self.ghosts:
            try:
                g.host.hide()
                g.host.deleteLater()
            except RuntimeError:
                pass
        for widget in self.made:
            try:
                widget.deleteLater()
            except RuntimeError:
                pass
        ghost.cmds, ghost.omui, ghost.winstyle = self.real
        _flush()

    def make(self, rect=(100, 100, 600, 400), borrow=True):
        g = ghost.Ghost(None, rect, borrow=borrow)
        self.ghosts.append(g)
        return g

    def splitter(self, panel, list_size=0, width=1000, list_min=200):
        """Maya's Graph Editor layout: the channel list beside the graph port
        in a QSplitter; findControl(panel + "GraphEd") is the port. The list's
        own minimum (its minimumSizeHint) is `list_min` and its margins."""
        split = QtWidgets.QSplitter()
        outliner = QtWidgets.QWidget()
        inner = QtWidgets.QWidget()
        inner.setMinimumWidth(list_min)
        QtWidgets.QHBoxLayout(outliner).addWidget(inner)
        port = QtWidgets.QWidget()
        split.addWidget(outliner)
        split.addWidget(port)
        split.setHandleWidth(0)
        split.resize(width, 300)
        split.show()
        self.app.processEvents()
        split.setSizes([list_size, width - list_size])
        self.qtutil.controls[panel + "GraphEd"] = port
        self.made.append(split)
        return split, outliner, port


# --------------------------------------------------------------- borrowing

class Borrowing(GhostCase):

    def test_graph_editor1_is_borrowed_and_its_home_remembered(self):
        g = self.make()
        self.assertTrue(g.borrowed)
        self.assertEqual(g.panel, ghost.BORROWED)
        self.assertEqual(g.home, HOME)
        self.assertEqual(self.cmds.panels[ghost.BORROWED],
                         PANE + "|" + ghost.BORROWED)
        self.assertTrue(ghost.in_host(ghost.BORROWED))
        self.assertEqual(ghost.home_of(ghost.BORROWED), PANE)

    def test_the_parent_maya_had_is_put_back(self):
        before = self.cmds.parent
        self.make()
        self.assertEqual(self.cmds.parent, before)

    def test_the_window_opens_invisible_and_named(self):
        g = self.make()
        self.assertEqual(g.host.objectName(), ghost.HOST)
        self.assertEqual(g.layout.objectName(), ghost.LAYOUT)
        self.assertEqual(g.host.windowTitle(), ghost.LABEL)
        self.assertAlmostEqual(g.host.windowOpacity(), ghost.GHOST_OPACITY,
                               places=2)
        self.assertTrue(g.host.isVisible())

    def test_without_graph_editor1_a_panel_of_its_own_is_made(self):
        self.cmds = GhostCmds(borrowed=False)
        ghost.cmds = self.cmds
        g = self.make()
        self.assertFalse(g.borrowed)
        self.assertEqual(g.panel, ghost.PANEL)
        self.assertIsNone(g.home)
        made = [c for c in self.cmds.calls if c[0] == "scriptedPanel"
                and c[2].get("type") == "graphEditor"]
        self.assertEqual(len(made), 1)
        self.assertEqual(made[0][2]["parent"], PANE)

    def test_borrow_off_makes_its_own_and_leaves_graph_editor1_alone(self):
        g = self.make(borrow=False)
        self.assertEqual(g.panel, ghost.PANEL)
        self.assertEqual(self.cmds.panels[ghost.BORROWED],
                         HOME + "|" + ghost.BORROWED)

    def test_given_back_to_its_home(self):
        g = self.make()
        self.assertTrue(g.give_back())
        self.assertEqual(self.cmds.panels[ghost.BORROWED],
                         HOME + "|" + ghost.BORROWED)
        self.assertFalse(ghost.in_host(ghost.BORROWED))

    def test_a_home_that_is_gone_means_unparented(self):
        g = self.make()
        self.cmds.layouts.discard(HOME)
        self.assertTrue(g.give_back())
        self.assertEqual(self.cmds.panels[ghost.BORROWED], "")

    def test_an_unparented_panel_goes_back_unparented(self):
        self.cmds = GhostCmds(home=None)
        ghost.cmds = self.cmds
        g = self.make()
        self.assertTrue(g.borrowed)
        self.assertIsNone(g.home)
        g.give_back()
        self.assertEqual(self.cmds.panels[ghost.BORROWED], "")

    def test_nothing_to_give_back_when_maya_took_it_back(self):
        """Opening the Graph Editor meanwhile re-parents graphEditor1 into
        its own window: give_back must not pull it out again."""
        g = self.make()
        self.cmds.panels[ghost.BORROWED] = "MayaWindow|graphEditor1Window|x|" \
            + ghost.BORROWED
        before = list(self.cmds.calls)
        self.assertFalse(g.give_back())
        edits = [c for c in self.cmds.calls[len(before):]
                 if c[0] == "scriptedPanel" and c[2].get("edit")]
        self.assertEqual(edits, [])

    def test_a_panel_of_its_own_gives_nothing_back(self):
        g = self.make(borrow=False)
        self.assertFalse(g.give_back())

    def test_destroy_gives_the_borrowed_panel_back_and_closes_the_window(self):
        g = self.make()
        g.destroy()
        self.assertEqual(self.cmds.panels[ghost.BORROWED],
                         HOME + "|" + ghost.BORROWED)
        self.assertFalse(g.host.isVisible())
        self.assertIsNone(g._canvas)

    def test_destroy_deletes_a_panel_of_its_own(self):
        g = self.make(borrow=False)
        g.destroy()
        self.assertNotIn(ghost.PANEL, self.cmds.panels)
        self.assertIn(("deleteUI", ghost.PANEL, {"panel": True}),
                      self.cmds.calls)

    def test_destroy_survives_maya_failing(self):
        g = self.make(borrow=False)
        self.cmds.fail = True
        with mock.patch("traceback.print_exc") as printed:
            g.destroy()
        printed.assert_called_once_with()
        self.assertFalse(g.host.isVisible())


class Alive(GhostCase):

    def test_alive_while_the_window_stands_and_holds_the_panel(self):
        self.assertTrue(self.make().alive())

    def test_not_alive_once_maya_took_the_panel_back(self):
        g = self.make()
        self.cmds.panels[ghost.BORROWED] = HOME + "|" + ghost.BORROWED
        self.assertFalse(g.alive())

    def test_not_alive_once_the_panel_is_deleted(self):
        g = self.make(borrow=False)
        del self.cmds.panels[ghost.PANEL]
        self.assertFalse(g.alive())

    def test_a_panel_of_its_own_need_not_stand_in_the_host(self):
        g = self.make(borrow=False)
        self.cmds.panels[ghost.PANEL] = "elsewhere|" + ghost.PANEL
        self.assertTrue(g.alive())

    def test_not_alive_when_maya_raises(self):
        g = self.make()
        self.cmds.fail = True
        self.assertFalse(g.alive())


class Leftovers(GhostCase):

    def test_a_panel_of_ours_a_scene_brought_back_is_deleted(self):
        self.cmds.panels[ghost.PANEL] = "somewhere|" + ghost.PANEL
        ghost.delete_leftovers()
        self.assertNotIn(ghost.PANEL, self.cmds.panels)

    def test_a_borrowed_panel_left_in_a_host_is_unparented_first(self):
        """Deleting the host would delete Maya's own Graph Editor with it."""
        self.cmds.panels[ghost.BORROWED] = PANE + "|" + ghost.BORROWED
        ghost.delete_leftovers()
        self.assertEqual(self.cmds.panels[ghost.BORROWED], "")

    def test_graph_editor1_at_home_is_not_touched(self):
        ghost.delete_leftovers()
        self.assertEqual(self.cmds.panels[ghost.BORROWED],
                         HOME + "|" + ghost.BORROWED)

    def test_hosts_and_glasses_an_older_module_built_go(self):
        old_host = QtWidgets.QWidget()
        old_host.setObjectName(ghost.HOST)
        old_glass = QtWidgets.QWidget()
        old_glass.setObjectName(ghost.GLASS_NAME)
        stranger = QtWidgets.QWidget()
        stranger.setObjectName("somebodyElse")
        for widget in (old_host, old_glass, stranger):
            widget.show()
        self.made.append(stranger)
        holder = []
        old_host.destroyed.connect(lambda *_a: holder.append("host"))
        old_glass.destroyed.connect(lambda *_a: holder.append("glass"))
        ghost.delete_leftovers()
        self.assertFalse(old_host.isVisible())
        self.assertFalse(old_glass.isVisible())
        self.assertTrue(stranger.isVisible())
        _flush()
        self.assertEqual(sorted(holder), ["glass", "host"])

    def test_maya_failing_is_swallowed(self):
        self.cmds.fail = True
        ghost.delete_leftovers()            # does not raise

    def test_a_new_ghost_sweeps_the_old_one_first(self):
        first = self.make()
        second = self.make()
        _flush()
        with self.assertRaises(RuntimeError):
            first.host.objectName()          # deleted by the second's sweep
        self.assertTrue(second.alive())


class ControlPath(GhostCase):

    def test_a_missing_panel_has_no_control_and_no_home(self):
        self.assertEqual(ghost._control_path("nope"), "")
        self.assertIsNone(ghost.home_of("nope"))
        self.assertFalse(ghost.in_host("nope"))

    def test_an_unparented_panel_has_no_home(self):
        self.cmds.panels["loose"] = ""
        self.assertIsNone(ghost.home_of("loose"))

    def test_a_control_query_that_raises_means_no_home(self):
        def boom(*_a, **_k):
            raise RuntimeError("gone")
        self.cmds.control = boom
        self.assertIsNone(ghost.home_of(ghost.BORROWED))

    def test_widget_is_none_for_an_unknown_control(self):
        self.assertIsNone(ghost._widget("unknownControl"))


# ------------------------------------------------------------------ window

class Window(GhostCase):

    def test_qt_s_own_frame_when_dwm_says_nothing(self):
        g = self.make()
        frame = g.host.frameGeometry()
        self.assertEqual(g.frame_rect(), (frame.x(), frame.y(),
                                          frame.width(), frame.height()))

    def test_dwm_s_visible_frame_wins(self):
        g = self.make()
        self.win.visible = lambda hwnd: (5, 6, 700, 500)
        self.assertEqual(g.frame_rect(), (5, 6, 700, 500))

    def test_the_frame_is_placed_on_the_rect_the_client_inside_it(self):
        """The insets are read off the window as it stands: a title bar of 30
        and borders of 8 put the client area that far inside the frame."""
        g = self.make()

        def visible(_hwnd):
            inner = g.host.geometry()
            return (inner.x() - 8, inner.y() - 30, inner.width() + 16,
                    inner.height() + 38)
        self.win.visible = visible
        g.place((200, 150, 640, 480))
        inner = g.host.geometry()
        self.assertEqual((inner.x(), inner.y(), inner.width(), inner.height()),
                         (208, 180, 624, 442))
        self.assertEqual(g.frame_rect(), (200, 150, 640, 480))

    def test_a_tiny_rect_keeps_a_window_at_least_one_pixel(self):
        g = self.make()
        inner = g.host.geometry()
        self.win.visible = lambda _h: (inner.x() - 50, inner.y() - 50,
                                       inner.width() + 100,
                                       inner.height() + 100)
        g.place((0, 0, 20, 20))
        self.assertEqual((g.host.geometry().width(),
                          g.host.geometry().height()), (1, 1))

    def test_showing_needs_shown_not_minimised_and_exposed(self):
        g = self.make()
        self.app.processEvents()
        self.assertTrue(g.showing())
        g.host.hide()
        self.assertFalse(g.showing())
        g.host.show()
        g.host.showMinimized()
        self.assertFalse(g.showing())

    def test_hwnd_is_the_window_id(self):
        g = self.make()
        self.assertEqual(g.hwnd(), int(g.host.winId()))

    def test_keep_invisible_puts_the_alpha_back_only_when_taken(self):
        g = self.make()
        self.assertFalse(g.keep_invisible())
        self.win.alpha = 255
        g.host.setWindowOpacity(1.0)
        self.assertTrue(g.keep_invisible())
        self.assertAlmostEqual(g.host.windowOpacity(), ghost.GHOST_OPACITY,
                               places=2)


# ------------------------------------------------------------------ chrome

class Chrome(GhostCase):

    def port_with_canvas(self, g, at=(10, 40), size=(300, 200)):
        """graphEditor1GraphEd holding a QWindowContainer, as Maya builds it,
        laid into the window."""
        port = QtWidgets.QWidget()
        port.setObjectName("graphEditor1GraphEd")
        g.layout.addWidget(port)
        container = QtWidgets.QWidget.createWindowContainer(QtGui.QWindow(),
                                                            port)
        container.setGeometry(at[0], at[1], size[0], size[1])
        self.qtutil.controls[g.panel + "GraphEd"] = port
        self.app.processEvents()
        return port, container

    def test_the_chrome_is_every_widget_but_the_canvas_container(self):
        g = self.make()
        _port, container = self.port_with_canvas(g)
        widgets = g.chrome_widgets()
        self.assertTrue(widgets)
        self.assertNotIn(_pointer(container), [_pointer(w) for w in widgets])
        self.assertTrue(all(w.metaObject().className() !=
                            ghost.CONTAINER_CLASS for w in widgets))

    def test_the_canvas_rect_is_the_container_on_screen(self):
        g = self.make()
        _port, container = self.port_with_canvas(g)
        corner = container.mapToGlobal(QtCore.QPoint(0, 0))
        self.assertEqual(g.canvas_rect(), (corner.x(), corner.y(), 300, 200))
        fx, fy = g.frame_rect()[:2]
        self.assertEqual(g.canvas_in_frame(),
                         (corner.x() - fx, corner.y() - fy, 300, 200))
        self.assertEqual(g.canvas_offset(), (corner.x() - fx, corner.y() - fy))

    def test_no_curve_area_means_no_canvas_and_no_pieces(self):
        g = self.make()
        self.assertIsNone(g.canvas_rect())
        self.assertIsNone(g.canvas_in_frame())
        self.assertEqual(g.canvas_offset(), (0, 0))
        self.assertEqual(g.chrome_pieces(), [])

    def test_a_port_without_a_container_has_no_canvas(self):
        g = self.make()
        port = QtWidgets.QWidget()
        QtWidgets.QWidget(port)
        self.qtutil.controls[g.panel + "GraphEd"] = port
        self.made.append(port)
        self.assertIsNone(g.canvas_rect())

    def test_the_chrome_is_cut_in_bands_around_the_canvas(self):
        g = self.make()
        self.port_with_canvas(g)
        fx, fy, fw, fh = g.frame_rect()
        x, y, w, h = g.canvas_in_frame()
        pieces = g.chrome_pieces()
        bands = geometry.chrome_bands((fw, fh), (x, y, w, h))
        self.assertTrue(bands)
        self.assertEqual([(px, py, img.width(), img.height())
                          for img, px, py in pieces], bands)
        self.assertEqual(self.win.captured, [(g.hwnd(), fw, fh)])
        first = pieces[0][0]
        self.assertEqual(first.format(), QtGui.QImage.Format_ARGB32)
        self.assertEqual(first.pixelColor(0, 0).getRgb()[:3], (60, 50, 40))

    def test_the_whole_window_capture_is_cropped_to_what_shows(self):
        """DWM's capture is the whole window, its invisible border included:
        the chrome is the part the animator sees."""
        g = self.make()
        self.port_with_canvas(g)
        fx, fy, fw, fh = g.frame_rect()
        self.win.window = (fx - 7, fy - 1, fw + 14, fh + 8)
        pieces = g.chrome_pieces()
        self.assertEqual(self.win.captured[-1], (g.hwnd(), fw + 14, fh + 8))
        self.assertEqual(pieces[0][0].width(), fw)

    def test_a_failed_capture_gives_no_pieces(self):
        g = self.make()
        self.port_with_canvas(g)
        self.win.data = None
        self.assertEqual(g.chrome_pieces(), [])


# -------------------------------------------------------------- the list

class ChannelList(GhostCase):

    def test_a_shut_list_is_opened_and_what_it_was_kept(self):
        g = self.make(rect=(0, 0, 600, 400))
        split, outliner, port = self.splitter(g.panel)
        before = split.sizes()
        self.assertTrue(g.open_channel_list())
        self.assertEqual(g.list_sizes, before)
        #  the handle widened to 10 in the same call: the list comes out a
        #  few px short of LIST_WIDTH (the sizes are scaled to the new room)
        self.assertGreaterEqual(split.sizes()[0], ghost.LIST_WIDTH - 10)
        self.assertEqual(split.handleWidth(), 10)

    def test_never_narrower_than_the_list_s_own_minimum(self):
        g = self.make(rect=(0, 0, 600, 400))
        split, outliner, port = self.splitter(g.panel, list_min=450)
        least = outliner.minimumSizeHint().width()
        self.assertGreater(least, ghost.LIST_WIDTH)
        self.assertTrue(g.open_channel_list())
        self.assertGreaterEqual(split.sizes()[0], least)

    def test_an_open_list_is_left_alone(self):
        g = self.make(rect=(0, 0, 600, 400))
        split, _outliner, _port = self.splitter(g.panel, list_size=300)
        sizes = split.sizes()
        self.assertFalse(g.open_channel_list())
        self.assertEqual(split.sizes(), sizes)
        self.assertIsNone(g.list_sizes)

    def test_a_splitter_not_laid_out_yet_waits(self):
        g = self.make(rect=(0, 0, 2000, 400))
        self.splitter(g.panel, width=500)
        self.assertFalse(g.open_channel_list())
        self.assertIsNone(g.list_sizes)

    def test_no_splitter_no_list(self):
        g = self.make()
        self.assertFalse(g.open_channel_list())
        port = QtWidgets.QWidget()
        self.qtutil.controls[g.panel + "GraphEd"] = port
        self.made.append(port)
        self.assertEqual(g._splitter(), (None, -1))
        self.assertFalse(g.open_channel_list())

    def test_looked_after_for_its_ticks_then_left_shut(self):
        g = self.make(rect=(0, 0, 600, 400))
        split, _outliner, _port = self.splitter(g.panel)
        g._list_ticks = ghost.LIST_TICKS
        self.assertFalse(g.open_channel_list())
        self.assertLess(split.sizes()[0], ghost.MIN_LIST)

    def test_the_first_sizes_are_kept_across_reopenings(self):
        g = self.make(rect=(0, 0, 600, 400))
        split, _outliner, _port = self.splitter(g.panel)
        first = split.sizes()
        g.open_channel_list()
        split.setSizes([0, 1000])               # the panel shut it once more
        g.open_channel_list()
        self.assertEqual(g.list_sizes, first)

    def test_give_back_puts_the_list_s_sizes_back(self):
        g = self.make(rect=(0, 0, 600, 400))
        split, _outliner, _port = self.splitter(g.panel)
        first = split.sizes()
        g.open_channel_list()
        self.assertGreater(split.sizes()[0], ghost.MIN_LIST)
        g.give_back()
        self.assertEqual(split.sizes()[0], first[0])     # shut again


# --------------------------------------------------------------- the canvas

class TanimCurveCanvas(QtOpenGL.QOpenGLWindow):
    """Maya's curve area: a QOpenGLWindow of this class name."""


#  a canvas PySide hands back as a plain window: its class name is Maya's
TanimCurveCanvasAsWindow = type("TanimCurveCanvas", (QtGui.QWindow,), {})


class Canvas(GhostCase):

    def tearDown(self):
        for window in getattr(self, "windows", []):
            try:
                window.deleteLater()
            except RuntimeError:
                pass
        super(Canvas, self).tearDown()

    def canvas_window(self, name="graphEditor1GraphEdImpl"):
        window = TanimCurveCanvas()
        window.setObjectName(name)
        self.windows = getattr(self, "windows", []) + [window]
        return window

    def test_the_canvas_is_found_among_the_live_windows(self):
        g = self.make()
        window = self.canvas_window()
        self.assertIs(g.canvas(), window)
        self.assertEqual(g.canvas_pointer(), _pointer(window))

    def test_the_same_canvas_is_handed_back_from_the_cache(self):
        g = self.make()
        window = self.canvas_window()
        first = g.canvas()
        self.assertIs(g.canvas(), first)
        self.assertIs(first, window)

    def test_a_window_of_another_name_or_class_is_not_the_canvas(self):
        g = self.make()
        self.canvas_window("somebodyElsesGraphEdImpl")
        plain = QtGui.QWindow()
        plain.setObjectName("graphEditor1GraphEdImpl")
        self.windows.append(plain)
        self.assertIsNone(g.canvas())
        self.assertIsNone(g.canvas_pointer())

    def test_a_deleted_canvas_is_forgotten(self):
        g = self.make()
        window = self.canvas_window()
        self.assertIsNotNone(g.canvas())
        self.windows.remove(window)
        shiboken6.delete(window)
        self.assertIsNone(g.canvas())
        self.assertIsNone(g._canvas)
        self.assertIsNone(g._canvas_pointer)

    def test_a_recreated_canvas_replaces_the_cached_one(self):
        g = self.make()
        first = self.canvas_window()
        g.canvas()
        second = self.canvas_window()       # made while the first stands:
        self.windows.remove(first)          # another address, for certain
        shiboken6.delete(first)
        self.assertIs(g.canvas(), second)
        self.assertEqual(g.canvas_pointer(), _pointer(second))

    def test_a_canvas_recreated_at_the_old_address_is_not_the_old_wrapper(self):
        """Fixed 2026-10-27 (ghost.py Ghost.canvas, the cache check): the cache was
        keyed by the C++ address alone; it now also asks the mark the cached canvas
        was given. Maya deletes the canvas and makes another when
        it re-parents the panel; when the new one lands at the freed address
        (seen here: offscreen Qt reused it in the full graphoverlay run),
        canvas() hands back the cached wrapper of the DELETED canvas - and
        mode._follow_once, comparing canvas_pointer() by address, never
        connects the new canvas's frameSwapped: the glass stops updating.
        Simulated deterministically: the second canvas given the cached
        address."""
        g = self.make()
        first = self.canvas_window()
        g.canvas()
        self.windows.remove(first)
        shiboken6.delete(first)
        second = self.canvas_window()
        g._canvas_pointer = _pointer(second)     # the freed address reused
        self.assertIs(g.canvas(), second)

    def test_a_canvas_handed_back_as_a_plain_window_is_wrapped_afresh(self):
        """PySide hands Maya's canvas back as a QPaintDeviceWindow: the cached
        wrapper is invalidated and the pointer wrapped again."""
        g = self.make()
        window = TanimCurveCanvasAsWindow()
        window.setObjectName("graphEditor1GraphEdImpl")
        pointer = _pointer(window)
        found = g.canvas()
        try:
            self.assertEqual(_pointer(found), pointer)
            self.assertEqual(g.canvas_pointer(), pointer)
            self.assertIs(g.canvas(), found)                 # then cached
        finally:
            shiboken6.delete(found)

    def test_no_canvas_no_frame(self):
        self.assertIsNone(self.make().canvas_frame())

    def test_the_frame_is_the_canvas_s_framebuffer(self):
        g = self.make()
        image = QtGui.QImage(4, 4, QtGui.QImage.Format_ARGB32)
        g.canvas = lambda: types.SimpleNamespace(grabFramebuffer=lambda: image)
        self.assertIs(g.canvas_frame(), image)


if __name__ == "__main__":
    unittest.main()
