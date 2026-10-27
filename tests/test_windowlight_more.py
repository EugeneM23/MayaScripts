"""maya_windowlight - the switches, the watch's life on `sys`, the window
Windows finds under the cursor (Win32 faked), and what a mouse over a real
offscreen window ends up lighting.

The cursor and Win32 are fakes handed in through the module's seams
(`_hwnd_at`, `_parent_hwnd`, `ctypes.windll`); Maya's commands are a fake
(`_cmds`); every window is a real offscreen QWidget.
"""

import contextlib
import ctypes
import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtGui, QtWidgets

import maya_hubqt as hubqt
import maya_windowlight as wl

_MISSING = object()


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeCmds(object):
    """optionVars and workspaceControl -exists, as the light asks them."""

    def __init__(self, controls=()):
        self.optionvars = {}
        self.controls = set(controls)
        self.asked = []
        self.fail = False

    def optionVar(self, **kw):
        if self.fail:
            raise RuntimeError("no prefs")
        if "exists" in kw:
            return kw["exists"] in self.optionvars
        if "query" in kw:
            return self.optionvars[kw["query"]]
        name, value = kw["intValue"]
        self.optionvars[name] = value

    def workspaceControl(self, name, **kw):
        self.asked.append(name)
        if self.fail:
            raise RuntimeError("no UI")
        return name in self.controls


class LightCase(unittest.TestCase):
    """The session's light put aside and back; `_cmds` a fake."""

    def setUp(self):
        self.app = _app()
        self.saved_state = getattr(sys, wl.STATE, _MISSING)
        if hasattr(sys, wl.STATE):
            delattr(sys, wl.STATE)
        self.cmds = FakeCmds()
        self.real_cmds = wl._cmds
        wl._cmds = lambda: self.cmds

    def tearDown(self):
        st = getattr(sys, wl.STATE, None)
        light = st.get("light") if st else None
        if light is not None and hasattr(light, "stop"):
            try:
                light.stop()
            except Exception:                                # noqa: BLE001
                pass
        if self.saved_state is _MISSING:
            if hasattr(sys, wl.STATE):
                delattr(sys, wl.STATE)
        else:
            setattr(sys, wl.STATE, self.saved_state)
        wl._cmds = self.real_cmds
        self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


# ------------------------------------------------------------- the switches

class Switches(LightCase):

    def test_both_on_by_default(self):
        self.assertTrue(wl.enabled())
        self.assertTrue(wl.maya_enabled())

    def test_the_switches_read_their_option_vars(self):
        self.cmds.optionvars[wl.OPTIONVAR] = 0
        self.cmds.optionvars[wl.MAYA_OPTIONVAR] = 0
        self.assertFalse(wl.enabled())
        self.assertFalse(wl.maya_enabled())

    def test_prefs_that_fail_answer_the_default(self):
        self.cmds.fail = True
        self.assertTrue(wl.enabled())
        self.assertTrue(wl.maya_enabled())

    def test_on_starts_the_watch_and_off_stops_it(self):
        with mock.patch.object(wl, "ensure") as ensure:
            said = wl.set_enabled(True)
        ensure.assert_called_once_with()
        self.assertEqual(self.cmds.optionvars[wl.OPTIONVAR], 1)
        self.assertEqual(said, "Window light: the window under the mouse is lit")
        with mock.patch.object(wl, "stop") as stop:
            said = wl.set_enabled(False)
        stop.assert_called_once_with()
        self.assertEqual(self.cmds.optionvars[wl.OPTIONVAR], 0)
        self.assertEqual(said, "Window light off")

    def test_maya_s_windows_switch_tells_a_standing_watch(self):
        light = mock.Mock(maya_on=True)
        wl._state()["light"] = light
        said = wl.set_maya_enabled(False)
        self.assertEqual(self.cmds.optionvars[wl.MAYA_OPTIONVAR], 0)
        self.assertFalse(light.maya_on)
        light.poll.assert_called_once_with(force=True)
        self.assertEqual(said, "Only our windows light under the mouse")
        self.assertEqual(wl.set_maya_enabled(True),
                         "Maya's windows light under the mouse too")
        self.assertTrue(light.maya_on)

    def test_maya_s_windows_switch_with_no_watch_only_remembers(self):
        self.assertEqual(wl.set_maya_enabled(True),
                         "Maya's windows light under the mouse too")
        self.assertEqual(self.cmds.optionvars[wl.MAYA_OPTIONVAR], 1)


class SessionState(LightCase):

    def setUp(self):
        super(SessionState, self).setUp()
        #  mayapy has no Maya UI; the offscreen QApplication stands for it
        patcher = mock.patch.object(hubqt, "available", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_state_lives_on_sys_and_is_made_once(self):
        st = wl._state()
        self.assertIs(getattr(sys, wl.STATE), st)
        self.assertEqual(st, {"light": None})
        st["light"] = "x"
        self.assertIs(wl._state(), st)

    def test_ensure_starts_one_watch_and_hands_it_back(self):
        light = wl.ensure()
        self.assertIsInstance(light, wl.Light)
        self.assertTrue(light.alive())
        self.assertIs(wl._state()["light"], light)
        self.assertIs(wl.ensure(), light)

    def test_ensure_does_nothing_while_switched_off(self):
        self.cmds.optionvars[wl.OPTIONVAR] = 0
        self.assertIsNone(wl.ensure())
        self.assertIsNone(wl._state()["light"])

    def test_ensure_without_maya_s_ui_does_nothing(self):
        with mock.patch.object(hubqt, "available", return_value=False):
            self.assertIsNone(wl.ensure())

    def test_a_watch_from_an_older_module_is_stopped_and_replaced(self):
        """An install purges our modules: the watch the purged module made is
        another class - stopped, and a new one started."""
        older = mock.Mock()
        older.alive.return_value = True
        wl._state()["light"] = older
        light = wl.ensure()
        older.stop.assert_called_once_with()
        self.assertIsInstance(light, wl.Light)
        self.assertIsNot(light, older)

    def test_a_dead_watch_is_replaced(self):
        first = wl.ensure()
        first.stop()
        self.assertFalse(first.alive())
        second = wl.ensure()
        self.assertIsNot(second, first)
        self.assertTrue(second.alive())

    def test_stop_forgets_the_watch(self):
        light = wl.ensure()
        wl.stop()
        self.assertIsNone(wl._state()["light"])
        self.assertFalse(light.alive())
        wl.stop()                                     # nothing standing: fine

    def test_reload_live_starts_a_new_watch(self):
        first = wl.ensure()
        second = wl.reload_live()
        self.assertIsNot(second, first)
        self.assertFalse(first.alive())
        self.assertTrue(second.alive())


# --------------------------------------------------------------- Win32 faked

class FakeUser32(object):
    """user32 as `_hwnd_at` / `_parent_hwnd` call it."""

    def __init__(self, cursor=(30, 40), hwnd=777, pid=None, parent=0,
                 cursor_ok=True):
        self.cursor, self.hwnd, self.cursor_ok = cursor, hwnd, cursor_ok
        self.pid = os.getpid() if pid is None else pid
        self.parent = parent
        self.points = []

        def GetCursorPos(ref):
            if not self.cursor_ok:
                return 0
            ref._obj.x, ref._obj.y = self.cursor
            return 1

        def WindowFromPoint(point):
            self.points.append((point.x, point.y))
            return self.hwnd

        def GetWindowThreadProcessId(hwnd, ref):
            ref._obj.value = self.pid
            return 1

        def GetParent(hwnd):
            return self.parent

        self.GetCursorPos = GetCursorPos
        self.WindowFromPoint = WindowFromPoint
        self.GetWindowThreadProcessId = GetWindowThreadProcessId
        self.GetParent = GetParent


@contextlib.contextmanager
def _user32(user32):
    with mock.patch.object(ctypes, "windll",
                           types.SimpleNamespace(user32=user32), create=True):
        yield


@unittest.skipUnless(sys.platform == "win32", "Win32 ctypes")
class HwndAt(unittest.TestCase):

    def test_our_window_under_the_cursor(self):
        user32 = FakeUser32()
        with _user32(user32):
            self.assertEqual(wl._hwnd_at(), (777, True))
        self.assertEqual(user32.points, [(30, 40)])

    def test_another_program_s_window(self):
        with _user32(FakeUser32(pid=os.getpid() + 1)):
            self.assertEqual(wl._hwnd_at(), (777, False))

    def test_no_window_there(self):
        with _user32(FakeUser32(hwnd=0)):
            self.assertEqual(wl._hwnd_at(), (0, False))

    def test_no_cursor_no_answer(self):
        with _user32(FakeUser32(cursor_ok=False)):
            self.assertIsNone(wl._hwnd_at())

    def test_a_failing_call_is_no_answer(self):
        user32 = FakeUser32()

        def boom(_ref):
            raise OSError("access denied")
        user32.GetCursorPos = boom
        with _user32(user32):
            self.assertIsNone(wl._hwnd_at())

    def test_off_windows_no_answer(self):
        with mock.patch.object(sys, "platform", "linux"):
            self.assertIsNone(wl._hwnd_at())

    def test_the_parent_window(self):
        with _user32(FakeUser32(parent=4242)):
            self.assertEqual(wl._parent_hwnd(5), 4242)
        with _user32(FakeUser32(parent=None)):
            self.assertEqual(wl._parent_hwnd(5), 0)

    def test_a_failing_parent_call_is_none(self):
        with mock.patch.object(ctypes, "windll", None, create=True):
            self.assertEqual(wl._parent_hwnd(5), 0)


# ---------------------------------------------------------------- widget_at

class WidgetAt(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.q = hubqt.qt()
        self.real = (wl._hwnd_at, wl._parent_hwnd)
        self.found = None
        self.parents = {}
        wl._hwnd_at = lambda: self.found
        wl._parent_hwnd = lambda hwnd: self.parents.get(hwnd, 0)
        self.top = QtWidgets.QWidget()
        self.top.setGeometry(200, 150, 300, 200)
        self.leaf = QtWidgets.QWidget(self.top)
        self.leaf.setGeometry(20, 30, 100, 80)
        self.top.show()
        self.app.processEvents()
        self.hwnd = int(self.top.winId())

    def tearDown(self):
        wl._hwnd_at, wl._parent_hwnd = self.real
        self.top.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    def at(self, x, y):
        return self.top.mapToGlobal(QtCore.QPoint(x, y))

    def test_the_deepest_widget_of_our_window(self):
        self.found = (self.hwnd, True)
        self.assertIs(wl.widget_at(self.q, self.at(40, 50)), self.leaf)

    def test_the_window_itself_where_no_child_is(self):
        self.found = (self.hwnd, True)
        self.assertIs(wl.widget_at(self.q, self.at(250, 180)), self.top)

    def test_another_program_in_front_lights_nothing(self):
        self.found = (self.hwnd, False)
        self.assertIsNone(wl.widget_at(self.q, self.at(40, 50)))
        self.found = (0, False)
        self.assertIsNone(wl.widget_at(self.q, self.at(40, 50)))

    def test_a_native_child_with_no_widget_is_walked_up_to_one(self):
        """WindowFromPoint can answer a native child Qt does not know (a GL
        canvas): its parents are asked until one is a widget."""
        self.found = (9001, True)
        self.parents = {9001: 9002, 9002: self.hwnd}
        self.assertIs(wl.widget_at(self.q, self.at(40, 50)), self.leaf)

    def test_a_window_of_nobody_s_widgets_is_nothing(self):
        self.found = (9001, True)
        self.parents = {9001: 0}
        self.assertIsNone(wl.widget_at(self.q, self.at(40, 50)))

    def test_off_windows_qt_s_own_widget_at(self):
        self.found = None
        pos = self.at(40, 50)
        with mock.patch.object(QtWidgets.QApplication, "widgetAt",
                               return_value=self.leaf) as asked:
            self.assertIs(wl.widget_at(self.q, pos), self.leaf)
        asked.assert_called_once_with(pos)


# ------------------------------------------------------------- the watch

def _paint(widget):
    """paintEvent run at once (`render`, trap 57): a repaint() waits for an
    exposed window."""
    image = QtGui.QImage(max(1, widget.width()), max(1, widget.height()),
                         QtGui.QImage.Format_ARGB32)
    image.fill(0)
    widget.render(image)
    return image


class Watch(LightCase):

    def setUp(self):
        super(Watch, self).setUp()
        self.cmds.controls = {"Outliner"}
        self.real_at = wl.widget_at
        self.under = None
        wl.widget_at = lambda q, pos: self.under
        self.light = wl.Light()
        self.light.start()
        self.light.tick_timer.stop()
        self.made = []

    def tearDown(self):
        self.light.stop()
        wl.widget_at = self.real_at
        for widget in self.made:
            widget.deleteLater()
        super(Watch, self).tearDown()

    def window(self, name="Outliner", top_name="FakeMain"):
        top = QtWidgets.QWidget()
        top.setObjectName(top_name)
        inner = QtWidgets.QWidget(top)
        inner.setObjectName(name)
        inner.setGeometry(0, 0, 200, 200)
        leaf = QtWidgets.QWidget(inner)
        leaf.setGeometry(10, 10, 50, 50)
        top.resize(220, 220)
        top.show()
        self.made.append(top)
        return top, inner, leaf

    def settle(self):
        for _ in range(200):
            self.light.tick_at = (self.light.tick_at or 0) - 0.05
            self.light.tick()
            if not self.light.tick_timer.isActive():
                break

    def test_alive_while_its_poll_timer_stands(self):
        self.assertTrue(self.light.alive())
        self.light.stop()
        self.assertFalse(self.light.alive())

    def test_a_workspace_control_answer_is_kept_a_while(self):
        clock = [1000.0]
        with mock.patch.object(wl, "time", types.SimpleNamespace(
                time=lambda: clock[0])):
            self.assertTrue(self.light._is_control("Outliner"))
            self.assertFalse(self.light._is_control("treeView"))
            self.assertTrue(self.light._is_control("Outliner"))
            self.assertEqual(self.cmds.asked, ["Outliner", "treeView"])
            clock[0] += wl.CONTROLS_S + 0.1
            self.assertTrue(self.light._is_control("Outliner"))
        self.assertEqual(self.cmds.asked, ["Outliner", "treeView", "Outliner"])

    def test_a_failing_workspace_control_query_is_no_control(self):
        self.cmds.fail = True
        self.assertFalse(self.light._is_control("Outliner"))

    def test_maya_s_main_window_is_never_lit(self):
        top, _inner, leaf = self.window(name="plainChild", top_name="MayaWin")
        self.light.main = wl._ptr(self.light.q, top)
        self.under = leaf
        self.light.poll(force=True)
        self.assertIsNone(self.light.target)

    def test_a_floating_maya_window_is_lit_whole(self):
        top, _inner, leaf = self.window(name="plainChild",
                                        top_name="hotkeyEditor")
        self.under = leaf
        self.light.poll(force=True)
        self.assertEqual(self.light.target[1], "ring")
        self.assertIs(self.light.target[2], top)
        self.assertEqual(self.light._radius(top), wl.RADIUS_MAYA)

    def test_maya_s_windows_off_lights_only_ours(self):
        self.light.maya_on = False
        _top, _inner, leaf = self.window()
        self.under = leaf
        self.light.poll(force=True)
        self.assertIsNone(self.light.target)
        ours_top, ours, ours_leaf = self.window(name="skeldarPoseLibrary")
        self.cmds.controls.add("skeldarPoseLibrary")
        self.under = ours_leaf
        self.light.poll(force=True)
        self.assertIs(self.light.target[2], ours)
        self.assertEqual(self.light._radius(ours), wl.RADIUS_OURS)

    def test_a_menu_under_the_mouse_lights_nothing(self):
        popup = QtWidgets.QWidget(None, QtCore.Qt.Popup)
        popup.resize(200, 200)
        popup.show()
        self.made.append(popup)
        self.under = popup
        self.light.poll(force=True)
        self.assertIsNone(self.light.target)

    def test_an_unmoved_cursor_is_not_looked_at_again_at_once(self):
        _top, inner, leaf = self.window()
        self.under = leaf
        self.light.poll(force=True)
        self.under = None                          # would put it out
        self.light.poll()                          # the cursor did not move
        self.assertIs(self.light.target[2], inner)

    def test_a_drag_keeps_its_window_lit(self):
        _top, inner, leaf = self.window()
        self.under = leaf
        self.light.poll(force=True)
        self.under = None
        with mock.patch.object(QtWidgets.QApplication, "mouseButtons",
                               return_value=QtCore.Qt.LeftButton):
            self.light.poll(force=True)
        self.assertIs(self.light.target[2], inner)

    def test_a_hidden_window_puts_its_ring_out(self):
        top, inner, leaf = self.window()
        self.under = leaf
        self.light.poll(force=True)
        key = self.light.target[0]
        top.hide()
        self.app.processEvents()
        self.assertIsNone(self.light.target)
        self.settle()
        self.assertNotIn(key, self.light.overlays)

    def test_animations_off_light_at_once(self):
        _top, inner, leaf = self.window()
        self.under = leaf
        with mock.patch.object(self.light.hubmotion, "enabled",
                               return_value=False):
            self.light.poll(force=True)
        overlay = self.light.overlays[wl._ptr(self.light.q, inner)]
        self.assertEqual(overlay.level, 1.0)

    def test_the_timer_slots_poll_and_tick_and_swallow_a_failure(self):
        with mock.patch.object(self.light, "poll") as poll, \
                mock.patch.object(self.light, "tick") as tick:
            self.light._poll_slot()
            self.light._tick_slot()
        poll.assert_called_once_with()
        tick.assert_called_once_with()
        with mock.patch.object(self.light, "poll",
                               side_effect=RuntimeError("boom")), \
                mock.patch.object(self.light, "tick",
                                  side_effect=RuntimeError("boom")), \
                mock.patch.object(wl.traceback, "print_exc") as printed:
            self.light._poll_slot()
            self.light._tick_slot()
        self.assertEqual(printed.call_count, 2)

    def test_a_ring_is_painted_and_a_broken_painter_stops_trying(self):
        _top, inner, leaf = self.window()
        self.under = leaf
        with mock.patch.object(self.light.hubmotion, "enabled",
                               return_value=False):
            self.light.poll(force=True)
        overlay = self.light.overlays[wl._ptr(self.light.q, inner)]
        painted = []
        with mock.patch.object(hubqt, "paint_light",
                               side_effect=lambda *a, **k: painted.append(k)):
            _paint(overlay)
        self.assertTrue(painted)
        self.assertEqual(painted[0]["face"], False)
        with mock.patch.object(hubqt, "paint_light",
                               side_effect=RuntimeError("no painter")), \
                mock.patch.object(wl.traceback, "print_exc"):
            _paint(overlay)
        self.assertTrue(overlay.broken)
        with mock.patch.object(hubqt, "paint_light") as again:
            _paint(overlay)
        again.assert_not_called()

    def test_a_ring_out_paints_nothing(self):
        overlay = wl._overlay_class()(1.0, 0)
        overlay.resize(100, 100)
        overlay.show()
        self.made.append(overlay)
        with mock.patch.object(hubqt, "paint_light") as painted:
            _paint(overlay)
        painted.assert_not_called()

    def test_a_failing_follow_in_the_filter_is_printed(self):
        follower = wl._follower_class()(types.SimpleNamespace(
            _follow=mock.Mock(side_effect=RuntimeError("boom"))))
        with mock.patch.object(wl.traceback, "print_exc") as printed:
            self.assertFalse(follower.eventFilter(
                None, QtCore.QEvent(QtCore.QEvent.Move)))
        printed.assert_called_once_with()
        follower.deleteLater()

    def test_a_window_too_small_keeps_its_ring_out(self):
        _top, inner, leaf = self.window()
        self.under = leaf
        self.light.poll(force=True)
        overlay = self.light.overlays[wl._ptr(self.light.q, inner)]
        inner.resize(30, 30)
        self.light._place(overlay, inner)
        self.assertEqual(overlay.goal, 0.0)

    def test_a_deleted_window_gives_no_rect_and_maya_s_radius(self):
        widget = QtWidgets.QWidget()
        import shiboken6
        shiboken6.delete(widget)
        self.assertIsNone(self.light.rect_of(widget))
        self.assertEqual(self.light._radius(widget), wl.RADIUS_MAYA)

    def test_an_empty_window_has_no_rect(self):
        widget = QtWidgets.QWidget()
        widget.resize(0, 0)
        self.made.append(widget)
        self.assertIsNone(self.light.rect_of(widget))

    def test_a_masked_host_is_lit_where_its_mask_shows(self):
        top, inner, leaf = self.window()
        inner.setMask(QtCore.QRect(20, 30, 100, 90))
        rect = self.light.rect_of(inner)
        self.assertEqual((rect.width(), rect.height()), (100, 90))
        self.assertEqual(rect.topLeft(),
                         inner.mapToGlobal(QtCore.QPoint(20, 30)))

    def test_turning_a_ring_off_that_never_was_does_nothing(self):
        widget = QtWidgets.QWidget()
        self.made.append(widget)
        self.light._light((1, "ring", widget), False, animate=True)
        self.assertEqual(self.light.overlays, {})

    def test_a_frame_of_ours_lights_and_goes_out_at_once_without_motion(self):
        frame = types.SimpleNamespace(level=0.0, updated=0)
        frame.update = lambda: setattr(frame, "updated", frame.updated + 1)
        with mock.patch.object(self.light.hubqt, "_valid", return_value=True):
            self.light._light((5, "frame", frame), True, animate=False)
            self.assertEqual(frame.level, 1.0)
            self.assertEqual(self.light.frames[5][1], 1.0)
            self.light._light((5, "frame", frame), False, animate=False)
        self.assertEqual(frame.level, 0.0)
        self.assertEqual(frame.updated, 2)

    def test_a_deleted_frame_is_forgotten(self):
        self.light.frames[5] = ["dead", 1.0]
        with mock.patch.object(self.light.hubqt, "_valid", return_value=False):
            self.light._light((5, "frame", "dead"), True, animate=True)
        self.assertNotIn(5, self.light.frames)

    def test_a_frame_fades_in_the_tick_and_is_dropped_once_out(self):
        frame = types.SimpleNamespace(level=0.0, update=lambda: None)
        with mock.patch.object(self.light.hubqt, "_valid", return_value=True):
            self.light._light((5, "frame", frame), True, animate=True)
            self.settle()
            self.assertEqual(frame.level, 1.0)
            self.light._light((5, "frame", frame), False, animate=True)
            self.settle()
        self.assertEqual(frame.level, 0.0)
        self.assertNotIn(5, self.light.frames)

    def test_a_frame_deleted_while_it_fades_is_dropped(self):
        self.light.frames[5] = ["dead", 1.0]
        with mock.patch.object(self.light.hubqt, "_valid",
                               side_effect=lambda obj: obj != "dead"):
            self.light.tick()
        self.assertEqual(self.light.frames, {})

    def test_an_overlay_deleted_while_it_fades_is_dropped(self):
        overlay = wl._overlay_class()(1.0, 0)
        import shiboken6
        shiboken6.delete(overlay)
        self.light.overlays[7] = overlay
        self.light.tick()
        self.assertEqual(self.light.overlays, {})

    def test_stop_puts_the_frames_it_lit_out(self):
        frame = types.SimpleNamespace(level=1.0, update=lambda: None)
        self.light.frames[5] = [frame, 1.0]
        with mock.patch.object(self.light.hubqt, "_valid", return_value=True):
            self.light.stop()
        self.assertEqual(frame.level, 0.0)
        self.assertEqual(self.light.frames, {})

    def test_a_section_window_lights_through_its_popup(self):
        """A section's floating window draws its own light: the watch asks its
        popup (maya_hubpop) - not while it bursts."""
        frame = QtWidgets.QWidget()
        self.made.append(frame)
        popup = mock.Mock(frame=frame)
        popup.alive.return_value = True
        popup.bursting.return_value = False
        fake = types.SimpleNamespace(_state=lambda: {"popups": {"tools": popup}})
        with mock.patch.dict(sys.modules, {"maya_hubpop": fake}):
            key = wl._ptr(self.light.q, frame)
            self.light._light((key, "frame", frame), True, animate=True)
            popup.set_light.assert_called_once_with(True, animate=True)
            popup.bursting.return_value = True
            self.light._light((key, "frame", frame), False, animate=True)
            popup.set_light.assert_called_once_with(True, animate=True)
        self.assertEqual(self.light.frames, {})

    def test_no_popup_module_or_a_broken_one_means_no_popup(self):
        frame = QtWidgets.QWidget()
        self.made.append(frame)
        with mock.patch.dict(sys.modules, {"maya_hubpop": None}):
            self.assertIsNone(self.light._popup_of(frame))
        broken = types.SimpleNamespace(_state=mock.Mock(
            side_effect=RuntimeError("purged")))
        with mock.patch.dict(sys.modules, {"maya_hubpop": broken}):
            self.assertIsNone(self.light._popup_of(frame))
        other = mock.Mock(frame=QtWidgets.QWidget())
        self.made.append(other.frame)
        with mock.patch.dict(sys.modules, {"maya_hubpop": types.SimpleNamespace(
                _state=lambda: {"popups": {"x": other}})}):
            self.assertIsNone(self.light._popup_of(frame))

    def test_no_window_frame_module_means_no_frame(self):
        widget = QtWidgets.QWidget()
        self.made.append(widget)
        with mock.patch.dict(sys.modules, {"maya_hubwindow": None}):
            self.assertIsNone(self.light._framed(widget))
        broken = types.SimpleNamespace(frame_class=mock.Mock(
            side_effect=RuntimeError("no Qt")))
        with mock.patch.dict(sys.modules, {"maya_hubwindow": broken}):
            self.assertIsNone(self.light._framed(widget))

    def test_stop_puts_every_light_out(self):
        _top, inner, leaf = self.window()
        self.under = leaf
        self.light.poll(force=True)
        self.assertTrue(self.light.overlays)
        self.light.stop()
        self.assertEqual(self.light.overlays, {})
        self.assertIsNone(self.light.target)
        self.assertIsNone(self.light.poll_timer)


if __name__ == "__main__":
    unittest.main()
