"""The radial menu's untested half (maya_radial): the key reads, the press and the release, the overlay's
events, the Finish popup, the editor card and the deferred runs - offscreen, on fakes."""

import contextlib
import io
import os
import sys
import time
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya.cmds  # noqa: F401
    HAVE_MAYA = True
except ImportError:
    HAVE_MAYA = False

if HAVE_MAYA:
    import maya_radial as radial
    import maya_radial_rules as rules
    import maya_hubstyle as hubstyle


class Ui(object):
    """maya.cmds for the card and the presses: optionVars kept, every UI command recorded, a control
    made by name exists afterwards, edits and queries read what it was made with."""

    def __init__(self):
        self.vars = {}
        self.messages = []
        self.controls = {}
        self.calls = []
        self.count = 0

    def optionVar(self, exists=None, query=None, stringValue=None, intValue=None, **_kw):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars.get(query, 0)
        if stringValue is not None:
            self.vars[stringValue[0]] = stringValue[1]
        if intValue is not None:
            self.vars[intValue[0]] = intValue[1]
        return None

    def inViewMessage(self, assistMessage=None, **_kw):
        self.messages.append(assistMessage)

    def mayaDpiSetting(self, **_kw):
        return 1.0

    def setParent(self, *args, **kw):
        self.calls.append(("setParent", args, kw))

    def __getattr__(self, kind):
        if kind.startswith("_"):
            raise AttributeError(kind)

        def call(*args, **kw):
            self.calls.append((kind, args, kw))
            name = args[0] if args and isinstance(args[0], str) else None
            if kw.get("exists"):
                return name in self.controls
            if kw.get("query") or kw.get("q"):
                props = self.controls.get(name, {})
                for key, value in kw.items():
                    if key not in ("query", "q") and value is True:
                        return props.get(key)
                return None
            if kw.get("edit") or kw.get("e"):
                self.controls.setdefault(name, {}).update(kw)
                return name
            if name is None:
                self.count += 1
                name = "%s%d" % (kind, self.count)
            self.controls[name] = dict(kw, kind=kind)
            return name
        return call

    def made(self, kind, **match):
        return [(name, props) for name, props in self.controls.items()
                if props.get("kind") == kind and all(props.get(k) == v for k, v in match.items())]


def _app():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class Patched(unittest.TestCase):
    """Rebinds module attributes for one test and puts the radial menu's state back."""

    def setUp(self):
        self.ui = Ui()
        self.patch(radial, "cmds", self.ui)
        state = radial._state()
        saved = dict(state)
        self.addCleanup(lambda: (state.clear(), state.update(saved)))
        state["menu"] = state["leaving"] = state["finish"] = None
        self.addCleanup(hubstyle.take_marks)

    def patch(self, target, name, value, create=False):
        patcher = mock.patch.object(target, name, value, create=create)
        patcher.start()
        self.addCleanup(patcher.stop)


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Motion(Patched):
    def test_animations_follow_the_hubs_switch(self):
        import maya_hubmotion
        self.patch(maya_hubmotion, "enabled", lambda: False)
        self.assertFalse(radial.animated())
        self.patch(maya_hubmotion, "enabled", lambda: True)
        self.assertTrue(radial.animated())

    def test_a_switch_that_raises_means_animated(self):
        import maya_hubmotion

        def broken():
            raise RuntimeError("no optionVar")
        self.patch(maya_hubmotion, "enabled", broken)
        self.assertTrue(radial.animated())

    def test_the_clock_runs_in_milliseconds(self):
        first = radial._now_ms()
        time.sleep(0.002)
        self.assertGreater(radial._now_ms() - first, 1.0)


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Waiting(Patched):
    def test_a_row_that_is_no_two_step_never_waits(self):
        self.assertFalse(radial.waiting("tools.knot"))

    def test_a_two_step_asks_its_module(self):
        import maya_tools.knots as knots
        self.patch(knots, "aims_waiting", lambda: ["one"])
        self.assertTrue(radial.waiting("tools.aim"))
        self.patch(knots, "aims_waiting", lambda: [])
        self.assertFalse(radial.waiting("tools.aim"))

    def test_a_module_that_raises_is_not_waiting(self):
        import maya_tools.knots as knots

        def broken():
            raise RuntimeError("scene gone")
        self.patch(knots, "waiting", broken)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(radial.waiting("tools.knot_offset"))


class FakeUser32(object):
    def __init__(self, down):
        self.down = set(down)
        self.asked = []

    def GetAsyncKeyState(self, vk):  # noqa: N802
        self.asked.append(vk)
        return 0x8001 if vk in self.down else 0x0001      # the low bit: "pressed since" - not held


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Keys(Patched):
    def test_a_key_is_down_only_on_the_high_bit(self):
        self.patch(radial, "_user32", lambda: FakeUser32({0x51}))
        self.assertTrue(radial.key_down(0x51))
        self.assertFalse(radial.key_down(0x41))

    def test_without_user32_nothing_is_down(self):
        self.patch(radial, "_user32", lambda: None)
        self.assertFalse(radial.key_down(0x51))
        self.assertEqual(radial.keys_down(), [])

    def test_the_held_keys_leave_out_buttons_modifiers_and_escape(self):
        down = {0x01, 0x10, 0x11, 0x12, 0xA0, 0x5B, radial.VK_ESCAPE, 0x51, 0x20, 0x41}
        self.patch(radial, "_user32", lambda: FakeUser32(down))
        self.assertEqual(radial.keys_down(), [0x20, 0x41, 0x51])

    def test_windows_user32_is_there(self):
        if sys.platform != "win32":
            self.skipTest("Windows only")
        self.assertIsNotNone(radial._user32())


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Qt(Patched):
    def test_qt_needs_mayas_ui(self):
        import maya_hubqt
        self.patch(maya_hubqt, "available", lambda: False)
        self.assertIsNone(radial._qt())
        self.patch(maya_hubqt, "available", lambda: True)
        self.assertIs(radial._qt(), maya_hubqt.qt())

    def test_the_screen_is_the_one_under_the_point(self):
        _app()
        import maya_hubqt
        q = maya_hubqt.qt()
        rect = radial._screen_rect(q, (10, 10))
        self.assertEqual(rect, q.QtGui.QGuiApplication.primaryScreen().geometry())
        far = radial._screen_rect(q, (100000, 100000))          # off every screen: the primary
        self.assertEqual(far, q.QtGui.QGuiApplication.primaryScreen().geometry())

    def _omui(self, pointer):
        """maya.OpenMayaUI stood in for (its real MQtUtil.mainWindow() kills a mayapy with no UI)."""
        import maya
        fake = types.SimpleNamespace(MQtUtil=types.SimpleNamespace(mainWindow=lambda: pointer))
        patcher = mock.patch.dict(sys.modules, {"maya.OpenMayaUI": fake})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.patch(maya, "OpenMayaUI", fake, create=True)

    def test_mayas_main_window_is_wrapped(self):
        _app()
        import maya_hubqt
        q = maya_hubqt.qt()
        window = q.QtWidgets.QWidget()
        self.addCleanup(window.deleteLater)
        self._omui(q.shiboken.getCppPointer(window)[0])
        wrapped = radial._main_window(q)
        self.assertEqual(q.shiboken.getCppPointer(wrapped)[0], q.shiboken.getCppPointer(window)[0])

    def test_no_main_window_is_none(self):
        import maya_hubqt
        self._omui(0)
        self.assertIsNone(radial._main_window(maya_hubqt.qt()))


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Runs(Patched):
    def test_run_later_runs_the_item_when_the_loop_turns(self):
        ran = []
        timers = []
        q = types.SimpleNamespace(QtCore=types.SimpleNamespace(QTimer=types.SimpleNamespace(
            singleShot=lambda ms, fn: timers.append((ms, fn)))))
        self.patch(radial, "run_item", lambda item, point: ran.append((item, point)))
        radial._run_later(q, "cmd:tools.knot", (5, 6))
        self.assertEqual(ran, [])                              # not at once
        self.assertEqual(timers[0][0], 0)
        timers[0][1]()
        self.assertEqual(ran, [("cmd:tools.knot", (5, 6))])

    def test_a_run_that_raises_is_said(self):
        q = types.SimpleNamespace(QtCore=types.SimpleNamespace(QTimer=types.SimpleNamespace(
            singleShot=lambda ms, fn: fn())))

        def boom(item, point):
            raise RuntimeError("boom")
        self.patch(radial, "run_item", boom)
        with contextlib.redirect_stderr(io.StringIO()):
            radial._run_later(q, "cmd:tools.knot", (0, 0))
        self.assertEqual(self.ui.messages, ["Radial menu: boom"])

    def test_call_later_calls_and_reports_a_failure(self):
        q = types.SimpleNamespace(QtCore=types.SimpleNamespace(QTimer=types.SimpleNamespace(
            singleShot=lambda ms, fn: fn())))
        called = []
        radial._call_later(q, lambda: called.append(1))
        self.assertEqual(called, [1])

        def boom():
            raise ValueError("tap failed")
        with contextlib.redirect_stderr(io.StringIO()):
            radial._call_later(q, boom)
        self.assertEqual(self.ui.messages, ["Radial menu: tap failed"])

    def test_a_camera_item_looks_through_it(self):
        import maya_camradial
        self.patch(maya_camradial, "look_through", lambda key: "through " + key)
        self.assertEqual(radial.run_item("camera:|persp", (0, 0)), "through |persp")
        self.assertEqual(radial.run_item("", (0, 0)), "")

    def test_a_header_only_section_is_shown_in_the_hub(self):
        import maya_hub
        shown = []
        self.patch(maya_hub, "show", lambda key=None: shown.append(key) or "shown")
        self.assertEqual(radial.run_item("section:hotkeys", (0, 0)), "shown")
        self.assertEqual(shown, ["hotkeys"])

    def test_a_window_section_opens_its_window_by_the_point(self):
        import maya_hub
        opened = []
        self.patch(maya_hub, "open_window", lambda key, point=None: opened.append((key, point)))
        self.assertEqual(radial.run_item("section:chat", (40, 50)), maya_hub.section("chat").label)
        self.assertEqual(opened, [("chat", (40, 50))])

    def test_a_section_whose_window_cannot_open_says_why(self):
        import maya_hubpop

        def boom(key, point):
            raise RuntimeError("no main window")
        self.patch(maya_hubpop, "open_at", boom)
        with contextlib.redirect_stderr(io.StringIO()):
            message = radial.run_item("section:tools", (0, 0))
        self.assertIn("no main window", message)
        self.assertEqual(self.ui.messages, [message])

    def test_a_section_with_no_window_falls_back_to_the_hub(self):
        import maya_hub
        import maya_hubpop
        self.patch(maya_hubpop, "open_at", lambda key, point: None)
        self.patch(maya_hub, "show", lambda key=None: "hub on " + key)
        self.assertEqual(radial.run_item("section:tools", (0, 0)), "hub on tools")

    def test_an_unknown_section_is_said(self):
        self.assertIn("set this slot again", radial.run_item("section:nope", (0, 0)))


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Presses(Patched):
    """press() and release() on a real overlay offscreen (no Maya main window)."""

    def setUp(self):
        super(Presses, self).setUp()
        self.app = _app()
        import maya_hubqt
        self.q = maya_hubqt.qt()
        self.down = set()
        self.ran = []
        self.patch(radial, "_qt", lambda: self.q)
        self.patch(radial, "_main_window", lambda q: None)
        self.patch(radial, "key_down", lambda vk: vk in self.down)
        self.patch(radial, "waiting", lambda key: False)
        self.patch(radial, "animated", lambda: False)
        self.patch(radial, "_run_later", lambda q, item, point: self.ran.append((item, point)))
        self.addCleanup(self._close)

    def _close(self):
        menu = radial._state()["menu"]
        if menu is not None:
            menu.destroy()
        radial.drop_leaving()

    def test_a_press_puts_the_menu_up_under_the_cursor(self):
        self.down = {rules_q()}
        self.patch(radial, "held_keys", lambda kind: [rules_q()])
        self.assertEqual(radial.press(), "")
        menu = radial._state()["menu"]
        self.assertTrue(radial.is_up())
        pos = self.q.QtGui.QCursor.pos()
        self.assertEqual(menu.centre, (pos.x(), pos.y()))
        self.assertEqual(menu.keys, [rules_q()])
        self.assertEqual(menu.mode, "hold")
        self.assertEqual(menu.window.geometry(), radial._screen_rect(self.q, menu.centre))
        self.assertEqual(menu.window.objectName(), "skeldarRadialMenu")
        self.assertTrue(menu.timer.isActive())
        self.assertEqual(menu.timer.interval(), radial.TICK_MS)
        self.assertEqual(menu.count, radial.count())
        self.assertEqual(menu.cursor(), (pos.x(), pos.y()))

    def test_auto_repeat_makes_no_second_menu(self):
        self.patch(radial, "held_keys", lambda kind: [rules_q()])
        radial.press()
        first = radial._state()["menu"]
        self.assertEqual(radial.press(), "")
        self.assertIs(radial._state()["menu"], first)

    def test_without_qt_the_press_is_said(self):
        self.patch(radial, "_qt", lambda: None)
        self.assertIn("Qt UI", radial.press())
        self.assertFalse(radial.is_up())
        self.assertEqual(len(self.ui.messages), 1)

    def test_a_scripted_press_with_no_key_waits_for_a_click(self):
        self.patch(radial, "held_keys", lambda kind: [])
        radial.press()
        self.assertEqual(radial._state()["menu"].mode, "click")

    def test_the_camera_menu_takes_its_spec(self):
        import maya_camradial
        spec = {"items": ["camera:|persp", "", "camera:|top"], "texts": ["Persp", "", "Top"],
                "marked": [0], "centre": "camera"}
        self.patch(maya_camradial, "spec", lambda: spec)
        self.patch(radial, "held_keys", lambda kind: [radial.VK_SPACE] if kind == "cameras" else [])
        radial.press("cameras")
        menu = radial._state()["menu"]
        self.assertEqual((menu.items, menu.texts, menu.count), (spec["items"], spec["texts"], 3))
        self.assertEqual(menu.marked, {0})
        self.assertEqual(menu.keys, [radial.VK_SPACE])

    def test_a_press_drops_a_menu_still_closing(self):
        old = types.SimpleNamespace(destroyed=[])
        old.destroy = lambda: old.destroyed.append(1)
        radial._state()["leaving"] = old
        self.patch(radial, "held_keys", lambda kind: [])
        radial.press()
        self.assertEqual(old.destroyed, [1])
        self.assertIsNone(radial._state()["leaving"])

    def _up(self, keys=(0x51,), items=None):
        self.patch(radial, "held_keys", lambda kind: list(keys))
        radial.press()
        menu = radial._state()["menu"]
        if items is not None:
            menu.items = list(items)
        return menu

    def test_release_with_nothing_up_does_nothing(self):
        self.assertEqual(radial.release(), "")

    def test_release_while_the_key_is_still_down_waits(self):
        menu = self._up()
        self.down = {0x51}
        menu.pointed = lambda: None
        radial.release()
        self.assertEqual(menu.mode, "hold")
        self.assertTrue(radial.is_up())

    def test_a_quick_tap_in_the_centre_keeps_it_up_for_a_click(self):
        menu = self._up()
        menu.pointed = lambda: None
        radial.release()
        self.assertEqual(menu.mode, "click")
        self.assertTrue(radial.is_up())

    def test_a_slow_release_in_the_centre_closes(self):
        menu = self._up()
        menu.pointed = lambda: None
        menu.started = time.time() - 10.0
        radial.release()
        self.assertFalse(radial.is_up())
        self.assertIsNone(menu.window)
        self.assertEqual(self.ran, [])

    def test_a_release_over_a_filled_slot_runs_it_at_the_cursor(self):
        menu = self._up(items=["", "cmd:tools.knot"])
        menu.pointed = lambda: 1
        menu.cursor = lambda: (123, 45)
        radial.release()
        self.assertEqual(self.ran, [("cmd:tools.knot", (123, 45))])
        self.assertFalse(radial.is_up())

    def test_a_release_over_an_empty_slot_closes_and_runs_nothing(self):
        menu = self._up(items=["", "cmd:tools.knot"])
        menu.pointed = lambda: 0
        radial.release()
        self.assertEqual(self.ran, [])
        self.assertFalse(radial.is_up())

    def test_the_camera_menus_tap_runs_its_tap_later(self):
        import maya_camradial
        taps = []
        spec = {"items": ["camera:|persp"], "on_tap": lambda: taps.append("tap"),
                "release": lambda slot, filled, elapsed: rules.TAP}
        self.patch(maya_camradial, "spec", lambda: spec)
        self.patch(radial, "_call_later", lambda q, fn: fn())
        self.patch(radial, "held_keys", lambda kind: [radial.VK_SPACE])
        radial.press("cameras")
        radial.release()
        self.assertEqual(taps, ["tap"])
        self.assertFalse(radial.is_up())

    def test_a_tick_sees_the_key_go_up(self):
        menu = self._up()
        menu.pointed = lambda: None
        self.down = {0x51}
        menu.tick()
        self.assertEqual(menu.mode, "hold")
        self.down = set()
        menu.tick()
        self.assertEqual(menu.mode, "click")                    # a quick tap: kept for a click

    def test_escape_pressed_while_up_closes_it(self):
        menu = self._up()
        menu.pointed = lambda: None
        self.down = {0x51}
        menu.tick()
        self.down = {0x51, radial.VK_ESCAPE}
        menu.tick()
        self.assertFalse(radial.is_up())

    def test_escape_held_at_the_press_does_not_close_it(self):
        self.down = {radial.VK_ESCAPE, 0x51}
        menu = self._up()
        menu.pointed = lambda: None
        menu.tick()
        self.assertTrue(radial.is_up())

    def test_a_tick_on_a_dead_menu_does_nothing(self):
        menu = self._up()
        menu.destroy()
        menu.tick()                                            # no raise
        self.assertFalse(menu.alive())


def rules_q():
    return radial.VK_Q


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class OverlayEvents(Patched):
    def setUp(self):
        super(OverlayEvents, self).setUp()
        self.app = _app()
        import maya_hubqt
        self.q = maya_hubqt.qt()
        self.got = []
        self.menu = types.SimpleNamespace(
            paint=lambda widget: self.got.append(("paint", widget)),
            clicked=lambda left: self.got.append(("clicked", left)),
            tick=lambda: self.got.append(("tick",)))
        self.window = radial._overlay_class(self.q)(self.menu)
        self.addCleanup(self.window.deleteLater)

    def event(self, button):
        QtCore, QtGui = self.q.QtCore, self.q.QtGui
        point = QtCore.QPointF(5, 5)
        return QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, point, point, button, button,
                                 QtCore.Qt.NoModifier)

    def test_it_is_a_frameless_tool_that_takes_no_focus(self):
        flags = self.window.windowFlags()
        Qt = self.q.QtCore.Qt
        for flag in (Qt.Tool, Qt.FramelessWindowHint, Qt.WindowStaysOnTopHint,
                     Qt.WindowDoesNotAcceptFocus):
            self.assertTrue(flags & flag, flag)
        self.assertTrue(self.window.testAttribute(Qt.WA_TranslucentBackground))
        self.assertTrue(self.window.hasMouseTracking())

    def test_its_paint_is_the_menus(self):
        self.window.paintEvent(None)
        self.assertEqual(self.got, [("paint", self.window)])

    def test_a_paint_that_raises_does_not_escape(self):
        def boom(widget):
            raise RuntimeError("bad paint")
        self.menu.paint = boom
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.window.paintEvent(None)
        self.assertIn("bad paint", err.getvalue())

    def test_left_and_right_presses_reach_the_menu(self):
        Qt = self.q.QtCore.Qt
        self.window.mousePressEvent(self.event(Qt.LeftButton))
        self.window.mousePressEvent(self.event(Qt.RightButton))
        self.assertEqual(self.got, [("clicked", True), ("clicked", False)])

    def test_a_click_that_raises_does_not_escape(self):
        def boom(left):
            raise RuntimeError("bad click")
        self.menu.clicked = boom
        with contextlib.redirect_stderr(io.StringIO()):
            self.window.mousePressEvent(self.event(self.q.QtCore.Qt.LeftButton))

    def test_a_move_ticks(self):
        self.window.mouseMoveEvent(None)
        self.assertEqual(self.got, [("tick",)])

    def test_the_class_is_made_once(self):
        self.assertIs(radial._overlay_class(self.q), radial._overlay_class(self.q))


class FakeCursor(object):
    at = [(0, 0)]

    @staticmethod
    def pos():
        from PySide6 import QtCore
        return QtCore.QPoint(*FakeCursor.at[0])


class GuiWithCursor(object):
    """QtGui with the cursor stood in for: a drag is driven by where the test says it is."""

    def __init__(self, real):
        self.real = real
        self.QCursor = FakeCursor

    def __getattr__(self, name):
        return getattr(self.real, name)


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class FinishPopup(Patched):
    def setUp(self):
        super(FinishPopup, self).setUp()
        self.app = _app()
        import maya_hubqt
        real = maya_hubqt.qt()
        self.q = types.SimpleNamespace(QtCore=real.QtCore, QtWidgets=real.QtWidgets, QtSvg=real.QtSvg,
                                       shiboken=real.shiboken, QtGui=GuiWithCursor(real.QtGui))
        self.wait = [True]
        self.runs = []
        self.patch(radial, "_qt", lambda: self.q)
        self.patch(radial, "_main_window", lambda q: None)
        self.patch(radial, "_screen_rect", lambda q, point: real.QtCore.QRect(0, 0, 800, 600))
        self.patch(radial, "waiting", lambda key: self.wait[0])
        import maya_hotkeys
        self.patch(maya_hotkeys, "run", lambda key: self.runs.append(key) or "Aim: aimed")
        self.addCleanup(radial.close_finish)

    def find(self, finish, name):
        return finish.window.findChild(self.q.QtWidgets.QPushButton, name)

    def test_no_qt_no_popup(self):
        self.patch(radial, "_qt", lambda: None)
        self.assertIsNone(radial.show_finish("tools.aim", (0, 0)))

    def test_it_stands_by_the_cursor_naming_the_tool(self):
        finish = radial.show_finish("tools.aim", (100, 200), "Place the target")
        self.assertIs(radial._state()["finish"], finish)
        self.assertTrue(finish.alive())
        self.assertEqual((finish.window.x(), finish.window.y()), (116, 212))
        labels = [label.text() for label in finish.window.findChildren(self.q.QtWidgets.QLabel)]
        self.assertIn("Aim waiting", labels)
        self.assertEqual(finish.line.text(), "Place the target")
        self.assertFalse(finish.line.isHidden())
        self.assertTrue(finish.timer.isActive())
        self.assertEqual(finish.timer.interval(), radial.FINISH_POLL_MS)

    def test_no_message_no_line(self):
        finish = radial.show_finish("tools.knot_offset", (10, 10))
        self.assertTrue(finish.line.isHidden())

    def test_it_is_kept_on_the_screen(self):
        finish = radial.show_finish("tools.aim", (790, 590), "x")
        self.assertLessEqual(finish.window.x() + finish.window.width(), 800)
        self.assertLessEqual(finish.window.y() + finish.window.height(), 600)

    def test_a_second_popup_takes_the_first_away(self):
        first = radial.show_finish("tools.aim", (10, 10))
        second = radial.show_finish("tools.knot_offset", (10, 10))
        self.assertFalse(first.alive())
        self.assertIs(radial._state()["finish"], second)

    def test_finish_presses_the_tool_again_and_goes_when_it_is_done(self):
        finish = radial.show_finish("tools.aim", (10, 10))
        self.wait[0] = False
        self.find(finish, "skeldarRadialFinishGo").click()
        self.assertEqual(self.runs, ["tools.aim"])
        self.assertIsNone(radial._state()["finish"])
        self.assertFalse(finish.alive())

    def test_finish_still_waiting_shows_the_tools_line(self):
        finish = radial.show_finish("tools.aim", (10, 10))
        self.assertEqual(finish.finish(), "Aim: aimed")
        self.assertEqual(finish.line.text(), "Aim: aimed")
        self.assertFalse(finish.line.isHidden())
        self.assertIs(radial._state()["finish"], finish)

    def test_the_cross_closes_it_and_the_tool_keeps_waiting(self):
        finish = radial.show_finish("tools.aim", (10, 10))
        self.find(finish, "skeldarRadialFinishX").click()
        self.assertIsNone(radial._state()["finish"])
        self.assertEqual(self.runs, [])

    def test_the_poll_closes_it_once_nothing_waits(self):
        finish = radial.show_finish("tools.aim", (10, 10))
        finish.poll()
        self.assertTrue(finish.alive())
        self.wait[0] = False
        finish.poll()
        self.assertIsNone(radial._state()["finish"])

    def test_it_is_dragged_by_its_body(self):
        finish = radial.show_finish("tools.aim", (100, 100))
        start = (finish.window.x(), finish.window.y())
        FakeCursor.at[0] = (start[0] + 5, start[1] + 5)
        finish.window.mousePressEvent(None)
        FakeCursor.at[0] = (start[0] + 45, start[1] + 25)
        finish.window.mouseMoveEvent(None)
        self.assertEqual((finish.window.x(), finish.window.y()), (start[0] + 40, start[1] + 20))
        finish.window.mouseReleaseEvent(None)
        self.assertIsNone(finish.grab)
        FakeCursor.at[0] = (0, 0)
        finish.window.mouseMoveEvent(None)                     # no grab: it stays
        self.assertEqual((finish.window.x(), finish.window.y()), (start[0] + 40, start[1] + 20))

    def test_destroy_twice_is_harmless(self):
        finish = radial.show_finish("tools.aim", (10, 10))
        finish.destroy()
        finish.destroy()
        self.assertFalse(finish.alive())


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Card(Patched):
    """The Radial Menu card on a recording cmds."""

    def setUp(self):
        super(Card, self).setUp()
        radial.build_panel()

    def control(self, name):
        return self.ui.controls[name]

    def rows(self):
        return [self.control(radial.SLOT_ROW.format(i)).get("manage") for i in range(rules.MAX_SLOTS)]

    def popup_command(self, index, button):
        """The postMenuCommand (button 1) or the Clear item's command (button 3) of slot `index`."""
        name = radial.SLOT_BTN.format(index)
        popup = [n for n, props in self.ui.made("popupMenu") if props.get("parent") == name
                 and props.get("button") == button][0]
        if button == 1:
            return self.control(popup)["postMenuCommand"]
        return [props["command"] for _n, props in self.ui.made("menuItem", label="Clear")
                if props.get("parent") == popup][0]

    def test_it_reads_open_and_builds_every_slot_row(self):
        self.assertTrue(radial.is_open())
        for i in range(rules.MAX_SLOTS):
            self.assertIn(radial.SLOT_BTN.format(i), self.ui.controls)
            self.assertIn(radial.SLOT_DIR.format(i), self.ui.controls)
        counts = [props["label"] for _n, props in self.ui.made("menuItem")
                  if props.get("label", "").isdigit()]
        self.assertEqual(counts, [str(n) for n in range(rules.MIN_SLOTS, rules.MAX_SLOTS + 1)])

    def test_the_first_count_rows_show_their_direction_and_item(self):
        self.assertEqual(self.rows(), [True] * 8 + [False] * 4)
        self.assertEqual(self.control(radial.COUNT_MENU)["value"], "8")
        for i, item in enumerate(rules.DEFAULTS):
            self.assertEqual(self.control(radial.SLOT_DIR.format(i))["label"], rules.direction(i, 8))
            self.assertEqual(self.control(radial.SLOT_BTN.format(i))["label"], radial.item_label(item))

    def test_the_count_menu_shows_fewer_rows(self):
        change = self.control(radial.COUNT_MENU)["changeCommand"]
        self.assertEqual(change("5"), "5 slots on the ring")
        self.assertEqual(self.rows(), [True] * 5 + [False] * 7)
        self.assertEqual(radial.count(), 5)
        self.assertEqual(self.control(radial.STATUS)["label"], "5 slots on the ring")
        self.assertEqual(self.control(radial.SLOT_DIR.format(1))["label"], rules.direction(1, 5))

    def test_a_slots_menu_offers_empty_sections_and_functions(self):
        self.popup_command(2, 1)()
        section = [props for _n, props in self.ui.made("menuItem", label="Tools") if "command" in props][0]
        section["command"]()
        self.assertEqual(radial.slots()[2], "section:tools")
        self.assertEqual(self.control(radial.STATUS)["label"], "E: Tools")
        aim = [props for _n, props in self.ui.made("menuItem", label="Aim") if "command" in props][0]
        aim["command"]()
        self.assertEqual(radial.slots()[2], "cmd:tools.aim")
        empty = [props for _n, props in self.ui.made("menuItem", label="Empty")][-1]
        empty["command"]()
        self.assertEqual(radial.slots()[2], "")
        self.assertEqual(self.control(radial.SLOT_BTN.format(2))["label"], "(empty)")
        self.assertEqual(self.control(radial.STATUS)["label"], "E: empty")

    def test_the_menu_is_built_afresh_each_time_it_opens(self):
        self.popup_command(0, 1)()
        popup = [n for n, props in self.ui.made("popupMenu")
                 if props.get("parent") == radial.SLOT_BTN.format(0) and props.get("button") == 1][0]
        clears = [c for c in self.ui.calls if c[0] == "popupMenu" and c[2].get("deleteAllItems")]
        self.assertEqual(clears[-1][1], (popup,))

    def test_right_click_clears_a_slot_and_keeps_the_others(self):
        self.popup_command(3, 3)()
        self.assertEqual(radial.slots()[3], "")
        self.assertEqual(radial.slots()[4], rules.DEFAULTS[4])

    def button(self, label):
        return [props for _n, props in self.ui.made("button", label=label)][0]

    def test_reset_brings_the_defaults_back(self):
        radial.set_count(3)
        radial.set_slot(0, "")
        self.button("Reset to defaults")["command"]()
        self.assertEqual(radial.count(), 8)
        self.assertEqual(radial.slots()[:8], rules.DEFAULTS)
        self.assertEqual(self.rows()[:8], [True] * 8)

    def test_bind_asks_for_the_hotkey_map_first(self):
        import maya_hotkeys
        self.patch(maya_hotkeys, "is_active", lambda: False)
        message = self.button("Bind " + radial.KEY_LABEL)["command"]()
        self.assertIn("Turn the hotkey map on", message)

    def test_bind_puts_the_menu_on_alt_q_and_names_what_it_held(self):
        import maya_hotkeys
        bound = []
        self.patch(maya_hotkeys, "is_active", lambda: True)
        self.patch(maya_hotkeys, "register", lambda dest=None: bound.append("register"))
        self.patch(maya_hotkeys, "bind_row",
                   lambda key, mods, row: bound.append((key, mods, row)) or "QuickRig")
        message = radial.bind_key()
        self.assertEqual(bound, ["register", ("q", {"altModifier": True}, "radial.press")])
        self.assertEqual(message, "alt+q opens the radial menu (it held QuickRig)")
        self.patch(maya_hotkeys, "bind_row", lambda key, mods, row: None)
        self.assertEqual(radial.bind_key(), "alt+q opens the radial menu")

    def test_the_status_is_told_to_the_hub(self):
        heard = []
        listeners = hubstyle._LISTENERS
        listener = lambda control, text, viewport: heard.append((control, text))  # noqa: E731
        listeners.append(listener)
        self.addCleanup(listeners.remove, listener)
        radial.status("hello")
        self.assertIn((radial.STATUS, "hello"), heard)

    def test_with_the_card_closed_status_writes_nothing(self):
        self.ui.controls.clear()
        self.assertFalse(radial.is_open())
        self.assertEqual(radial.status("x"), "x")
        radial.refresh()                                       # no control: nothing raises

    def test_show_window_opens_the_hub_on_the_card(self):
        import maya_hub
        self.patch(maya_hub, "show", lambda key=None: "hub " + key)
        self.assertEqual(radial.show_window(), "hub radial")


if __name__ == "__main__":
    unittest.main()
