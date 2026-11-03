"""The shutdown cleanup (2026-11-02): the ordered plan, the guarded runner, the sweep.

Maya crashed in shiboken6 at every quit because our Qt objects were still attached to
Maya's own when Python finalised. These tests pin the three things that make the cure
work: the order (Maya's borrowed widgets go back BEFORE anything of ours is destroyed),
that nothing is imported by the teardown (it tears down only what is standing), and that
every name in the plan is really there (a rename would silently skip a step).
"""

import ast
import os
import sys
import types
import unittest
from unittest import mock

import maya_shutdown as ms


HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(HERE, "SkeldarAnim")


def fake(name, record, blow_up=False):
    """A stand-in module whose steps record themselves."""
    module = types.ModuleType(name)
    for step in ms.PLAN:
        if step.module != name:
            continue

        def call(_step=step, *_a, **_k):
            record.append((_step.module, _step.function))
            if blow_up:
                raise RuntimeError("step refused")
        setattr(module, step.function, call)
    return module


class Plan(unittest.TestCase):
    def test_every_step_names_a_module_and_a_function(self):
        self.assertTrue(ms.PLAN)
        for step in ms.PLAN:
            self.assertTrue(step.module.startswith("maya_"), step.module)
            self.assertTrue(step.function)
            self.assertTrue(step.what, "every step says what it is for")

    def test_mayas_own_widgets_come_back_before_anything_of_ours_is_destroyed(self):
        # The one ordering that matters: a host deleted with Maya's editor inside it
        # would delete Maya's editor (the side panel's own docstring says so).
        give_back = [i for i, s in enumerate(ms.PLAN) if s.phase == ms.GIVE_BACK]
        destroy = [i for i, s in enumerate(ms.PLAN) if s.phase == ms.DESTROY]
        self.assertTrue(give_back and destroy)
        self.assertLess(max(give_back), min(destroy))

    def test_the_watchers_stop_before_our_windows_go(self):
        stop = [i for i, s in enumerate(ms.PLAN) if s.phase == ms.STOP]
        destroy = [i for i, s in enumerate(ms.PLAN) if s.phase == ms.DESTROY]
        self.assertLess(max(stop), min(destroy))

    def test_maya_s_borrowed_editors_are_given_back(self):
        pairs = [(s.module, s.function) for s in ms.PLAN]
        for pair in (("maya_sidepanel", "drop_edge"),
                     ("maya_channelbox", "unmount"),
                     ("maya_timebar", "drop_edge"),
                     ("maya_graphoverlay.mode", "disable")):
            self.assertIn(pair, pairs)

    def test_steps_keeps_plan_order_and_leaves_out_what_is_not_loaded(self):
        loaded = {"maya_timebar", "maya_windowlight"}
        got = ms.steps(loaded)
        self.assertEqual([s.module for s in got],
                         [s.module for s in ms.PLAN if s.module in loaded])


class Run(unittest.TestCase):
    def test_a_module_that_is_not_loaded_is_never_imported(self):
        record = []
        with mock.patch.dict(sys.modules, {}, clear=False):
            for step in ms.PLAN:
                sys.modules.pop(step.module, None)

            def no(*_a, **_k):
                raise AssertionError("the teardown imported a module")
            with mock.patch("builtins.__import__", no):
                report = ms.run()
        self.assertEqual(report["done"], [])
        self.assertEqual(record, [])

    def test_each_standing_step_runs_once_in_plan_order(self):
        record = []
        names = sorted({s.module for s in ms.PLAN})
        fakes = {n: fake(n, record) for n in names}
        with mock.patch.dict(sys.modules, fakes):
            report = ms.run()
        self.assertEqual(record, [(s.module, s.function) for s in ms.PLAN])
        self.assertEqual(len(report["done"]), len(ms.PLAN))
        self.assertEqual(report["failed"], [])

    def test_a_step_that_raises_does_not_stop_the_rest(self):
        record = []
        names = sorted({s.module for s in ms.PLAN})
        first = ms.PLAN[0].module
        fakes = {n: fake(n, record, blow_up=(n == first)) for n in names}
        with mock.patch.dict(sys.modules, fakes), mock.patch("builtins.print"):
            report = ms.run()
        self.assertEqual(len(record), len(ms.PLAN), "every step was still tried")
        self.assertTrue(any(first in f for f in report["failed"]))
        self.assertTrue(report["done"])

    def test_a_module_without_the_function_is_skipped_not_fatal(self):
        record = []
        names = sorted({s.module for s in ms.PLAN})
        gone = ms.PLAN[0].module
        fakes = {n: (types.ModuleType(n) if n == gone else fake(n, record))
                 for n in names}
        with mock.patch.dict(sys.modules, fakes):
            report = ms.run()
        self.assertEqual(report["failed"], [])
        self.assertTrue(any(ms.PLAN[0].function in s for s in report["skipped"]))
        self.assertTrue(report["done"], "the rest still ran")

    def test_running_twice_is_harmless(self):
        record = []
        names = sorted({s.module for s in ms.PLAN})
        fakes = {n: fake(n, record) for n in names}
        with mock.patch.dict(sys.modules, fakes):
            ms.run()
            ms.run()
        self.assertEqual(len(record), 2 * len(ms.PLAN))


class Ours(unittest.TestCase):
    def test_a_widget_of_one_of_our_modules_is_ours(self):
        for module in ("maya_hubqt", "maya_timebar.bar", "maya_chat.window"):
            self.assertTrue(ms.ours(module), module)

    def test_mayas_own_and_qts_own_are_not_ours(self):
        for module in ("maya.app.general.shelfEditorWindow", "maya", "maya.cmds",
                       "PySide6.QtWidgets", "shiboken6", "animBot._api.core",
                       "__main__", None, ""):
            self.assertFalse(ms.ours(module), module)


class QObjectStub(object):
    """What the fake PySide6.QtCore.QObject is, so isinstance() works in the tests."""

    def disconnect(self):
        return True


class _Widget(QObjectStub):
    def __init__(self, name="w", timers=(), raises=False):
        self.name = name
        self.timers = list(timers)
        self.raises = raises
        self.hidden = False
        self.unparented = False
        self.parent_widget = None

    def objectName(self):
        return self.name

    def parent(self):
        return self.parent_widget

    def findChildren(self, _kind):
        return self.timers

    def hide(self):
        if self.raises:
            raise RuntimeError("gone")
        self.hidden = True

    def setParent(self, _p):
        self.unparented = True
        self.parent_widget = None


def Widget(name="w", module="maya_fake", timers=(), raises=False):
    """A stand-in widget whose CLASS comes from `module`: `ours` reads
    type(widget).__module__, and that is the whole discriminator."""
    cls = type("Widget_" + name.replace(".", "_"), (_Widget,), {"__module__": module})
    return cls(name, timers, raises)


class Timer(QObjectStub):
    def __init__(self, active=True, dead=False):
        self.active = active
        self.dead = dead
        self.stopped = False

    def isActive(self):
        if self.dead:
            raise RuntimeError("Internal C++ object already deleted")
        return self.active

    def stop(self):
        self.stopped = True
        self.active = False


def qtcore():
    module = types.ModuleType("PySide6.QtCore")
    module.QTimer = Timer
    module.QObject = QObjectStub
    return module


class StopTimers(unittest.TestCase):
    def test_a_timer_under_one_of_our_widgets_is_stopped(self):
        timer = Timer()
        ours_widget = Widget("ours", "maya_timebar.bar", timers=[timer])
        with mock.patch.dict(sys.modules, {"PySide6.QtCore": qtcore()}):
            self.assertEqual(ms.stop_timers([ours_widget]), 1)
        self.assertTrue(timer.stopped)

    def test_mayas_own_widgets_are_left_alone(self):
        timer = Timer()
        theirs = Widget("theirs", "PySide6.QtWidgets", timers=[timer])
        with mock.patch.dict(sys.modules, {"PySide6.QtCore": qtcore()}):
            self.assertEqual(ms.stop_timers([theirs]), 0)
        self.assertFalse(timer.stopped)

    def test_a_timer_already_at_rest_is_not_counted(self):
        with mock.patch.dict(sys.modules, {"PySide6.QtCore": qtcore()}):
            self.assertEqual(
                ms.stop_timers([Widget("a", "maya_hub", timers=[Timer(active=False)])]), 0)

    def test_a_dead_timer_wrapper_does_not_stop_the_sweep(self):
        live = Timer()
        widget = Widget("a", "maya_hub", timers=[Timer(dead=True), live])
        with mock.patch.dict(sys.modules, {"PySide6.QtCore": qtcore()}):
            self.assertEqual(ms.stop_timers([widget]), 1)
        self.assertTrue(live.stopped)

    def test_without_qt_it_does_nothing(self):
        with mock.patch.dict(sys.modules, {}, clear=False):
            sys.modules.pop("PySide6.QtCore", None)
            self.assertEqual(ms.stop_timers([Widget("a", "maya_hub", timers=[Timer()])]), 0)


class Sweep(unittest.TestCase):
    def test_only_our_own_windows_are_destroyed(self):
        mine = Widget("skeldarChatWindow", "maya_chat.window")
        mayas = Widget("someOptionMenuPopup", "PySide6.QtWidgets")
        killed = []
        gone = ms.sweep_windows([mine, mayas], delete=killed.append)
        self.assertEqual(gone, ["skeldarChatWindow"])
        self.assertEqual(killed, [mine])
        self.assertTrue(mine.unparented, "out of Maya's tree before it is deleted")
        self.assertFalse(mayas.unparented)

    def test_one_window_that_refuses_does_not_stop_the_others(self):
        bad = Widget("bad", "maya_hub", raises=True)
        good = Widget("good", "maya_hub")
        killed = []
        with mock.patch("builtins.print"):
            gone = ms.sweep_windows([bad, good], delete=killed.append)
        self.assertEqual(gone, ["good"])
        self.assertEqual(killed, [good])


class SweepWidgets(unittest.TestCase):
    """Not only the top-level windows: measured, 32 of our widgets were still standing
    re-parented under MayaWindow with the named steps all done, and Maya still crashed."""

    def test_children_go_before_their_parents(self):
        parent = Widget("parent", "maya_timebar.bar")
        child = Widget("child", "maya_timebar.bar")
        child.parent_widget = parent
        order = []
        ms.sweep_widgets([parent, child], delete=order.append)
        self.assertEqual([w.name for w in order], ["child", "parent"])

    def test_only_ours_are_destroyed(self):
        mine = Widget("mine", "maya_skillbar.grid")
        mayas = Widget("mayas", "PySide6.QtWidgets")
        killed = []
        gone = ms.sweep_widgets([mine, mayas], delete=killed.append)
        self.assertEqual(gone, ["mine"])
        self.assertEqual(killed, [mine])


class Takeable(unittest.TestCase):
    def test_a_qobject_of_one_of_our_classes_is_ours(self):
        with mock.patch.dict(sys.modules, {"PySide6.QtWidgets": qtwidgets()}):
            self.assertTrue(ms.takeable(Widget("w", "maya_timebar.bar")))

    def test_a_timer_or_a_watcher_we_made_is_ours(self):
        with mock.patch.dict(sys.modules, {"PySide6.QtWidgets": qtwidgets()}):
            self.assertTrue(ms.takeable(Timer()), "not a widget: we made it")

    def test_mayas_own_widget_in_our_state_is_left_alone(self):
        """`_skeldar_scenetabs['quit_filter'][1]` is Maya's main window."""
        with mock.patch.dict(sys.modules, {"PySide6.QtWidgets": qtwidgets()}):
            self.assertFalse(ms.takeable(MayaWidget()))


class MayaWidget(QObjectStub):
    """A plain PySide widget, as Maya's main window wraps."""
    __module__ = "PySide6.QtWidgets"


def qtwidgets():
    module = types.ModuleType("PySide6.QtWidgets")
    module.QWidget = MayaWidget
    return module


class DropState(unittest.TestCase):
    def setUp(self):
        self.addCleanup(lambda: [delattr(sys, n) for n in
                                 ("_skeldar_probe_one", "_skeldar_probe_two")
                                 if hasattr(sys, n)])

    def test_every_qobject_our_state_holds_is_disconnected_and_deleted(self):
        timer = Timer()
        watcher = Timer()                     # stands in for the QMediaDevices watcher
        sys._skeldar_probe_one = {"timer": timer}
        sys._skeldar_probe_two = {"devices": watcher, "deep": [{"w": timer}]}
        killed = []
        with mock.patch.dict(sys.modules, {"PySide6.QtCore": qtcore(),
                                           "PySide6.QtWidgets": qtwidgets()}):
            gone = ms.drop_qt_state(delete=killed.append)
        self.assertEqual(len(killed), 2, "each object once, however many paths reach it")
        self.assertTrue(all("_skeldar_probe" in p for p in gone))

    def test_mayas_own_widget_in_our_state_is_never_deleted(self):
        sys._skeldar_probe_one = {"quit_filter": [Widget("f", "maya_scenetabs.hooks"),
                                                  MayaWidget()]}
        killed = []
        with mock.patch.dict(sys.modules, {"PySide6.QtCore": qtcore(),
                                           "PySide6.QtWidgets": qtwidgets()}):
            ms.drop_qt_state(delete=killed.append)
        self.assertEqual(len(killed), 1)
        self.assertFalse(any(isinstance(k, MayaWidget) for k in killed))


class Forget(unittest.TestCase):
    """Handing shiboken its wrappers of MAYA's widgets back.

    A wrapper of a Maya-owned widget is not ours to delete - the C++ is Maya's - so
    the only thing to give back is shiboken's knowledge of it."""

    def test_mayas_widgets_are_handed_back_and_ours_are_not(self):
        mayas = [MayaWidget(), MayaWidget()]
        mine = Widget("mine", "maya_timebar.bar")
        given = []
        count = ms.forget_maya_wrappers(mayas + [mine], invalidate=given.append)
        self.assertEqual(count, 2)
        self.assertEqual(given, mayas, "ours are destroyed, not forgotten")

    def test_without_shiboken_it_does_nothing(self):
        with mock.patch.dict(sys.modules, {}, clear=False):
            sys.modules.pop("shiboken6", None)
            self.assertEqual(ms.forget_maya_wrappers([MayaWidget()]), 0)

    def test_one_that_refuses_does_not_stop_the_rest(self):
        given = []

        def invalidate(widget):
            if len(given) == 0:
                given.append(widget)
                raise RuntimeError("already deleted")
            given.append(widget)
        count = ms.forget_maya_wrappers([MayaWidget(), MayaWidget(), MayaWidget()],
                                        invalidate=invalidate)
        self.assertEqual(len(given), 3, "every one was still tried")
        self.assertEqual(count, 2)


class Deep(unittest.TestCase):
    def test_only_the_exit_sweeps_widgets_and_state(self):
        with mock.patch.object(ms, "run", return_value={"done": [], "skipped": [],
                                                        "failed": []}), \
                mock.patch.object(ms, "stop_timers", return_value=0), \
                mock.patch.object(ms, "sweep_windows", return_value=[]), \
                mock.patch.object(ms, "forget_maya_wrappers", return_value=3) as back, \
                mock.patch.object(ms, "sweep_widgets", return_value=["w"]) as widgets, \
                mock.patch.object(ms, "drop_qt_state", return_value=["s"]) as state:
            shallow = ms.teardown("an install")
            self.assertEqual(widgets.call_count, 0, "an install rebuilds: it keeps them")
            self.assertEqual(state.call_count, 0)
            self.assertEqual(back.call_count, 0)
            self.assertNotIn("widgets", shallow)
            deep = ms.teardown("Maya exiting", deep=True)
            self.assertEqual(widgets.call_count, 1)
            self.assertEqual(state.call_count, 1)
            self.assertEqual(back.call_count, 1)
            self.assertEqual(deep["widgets"], ["w"])
            self.assertEqual(deep["forgotten"], 3)

    def test_mayas_wrappers_are_handed_back_last_of_all(self):
        """Ours are destroyed first: a wrapper invalidated under a widget we still
        have to hide and unparent would raise instead of going down."""
        order = []
        with mock.patch.object(ms, "run", return_value={"done": ["x"], "skipped": [],
                                                        "failed": []}), \
                mock.patch.object(ms, "stop_timers", return_value=0), \
                mock.patch.object(ms, "sweep_windows", return_value=[]), \
                mock.patch.object(ms, "sweep_widgets",
                                  side_effect=lambda: order.append("ours") or []), \
                mock.patch.object(ms, "drop_qt_state",
                                  side_effect=lambda: order.append("state") or []), \
                mock.patch.object(ms, "forget_maya_wrappers",
                                  side_effect=lambda: order.append("back") or 0), \
                mock.patch("builtins.print"):
            ms.teardown("Maya exiting", deep=True)
        self.assertEqual(order, ["ours", "state", "back"])

    def test_the_hook_goes_deep(self):
        with mock.patch.object(ms, "teardown") as down:
            ms._on_exiting()
        down.assert_called_once()
        self.assertTrue(down.call_args.kwargs.get("deep"))


class Arm(unittest.TestCase):
    def setUp(self):
        self.addCleanup(lambda: setattr(sys, ms.STATE, None))
        setattr(sys, ms.STATE, None)

    def test_arm_registers_one_callback_and_is_idempotent(self):
        added = []
        api = mock.Mock()
        api.MSceneMessage.addCallback.side_effect = lambda *a, **k: added.append(a) or len(added)
        api.MSceneMessage.kMayaExiting = 7
        self.assertTrue(ms.arm(api=api))
        self.assertFalse(ms.arm(api=api), "a second arm adds nothing")
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0][0], 7, "the callback is kMayaExiting")

    def test_the_id_lives_on_sys_so_a_purged_module_does_not_double_register(self):
        api = mock.Mock()
        api.MSceneMessage.addCallback.return_value = 42
        ms.arm(api=api)
        self.assertEqual(getattr(sys, ms.STATE).get("callback"), 42)

    def test_disarm_removes_it(self):
        api = mock.Mock()
        api.MSceneMessage.addCallback.return_value = 42
        ms.arm(api=api)
        self.assertTrue(ms.disarm(api=api))
        api.MMessage.removeCallback.assert_called_once_with(42)
        self.assertIsNone(getattr(sys, ms.STATE).get("callback"))


class NamesExist(unittest.TestCase):
    """A step is (module, function) by name: a rename elsewhere would skip it in silence."""

    @staticmethod
    def source_of(module):
        parts = module.split(".")
        path = os.path.join(PLUGIN, *parts) + ".py"
        if not os.path.exists(path):
            path = os.path.join(PLUGIN, *parts, "__init__.py")
        return path

    def test_every_step_names_a_function_that_is_really_there(self):
        missing = []
        for step in ms.PLAN:
            path = self.source_of(step.module)
            if not os.path.exists(path):
                missing.append("%s (no such module)" % step.module)
                continue
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            names = {node.name for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            if step.function not in names:
                missing.append("%s.%s" % (step.module, step.function))
        self.assertEqual(missing, [], "the plan names something that is gone")


if __name__ == "__main__":
    unittest.main()
