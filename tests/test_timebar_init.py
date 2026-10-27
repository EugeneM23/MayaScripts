"""maya_timebar's own module (2026-10-16): Maya's, Docked or Bottom edge - the
optionVars each choice writes, what it hides and shows (ours, Maya's Time Slider and
Range Slider), the update's one switch to the bottom edge, the docked control made or
restored, the edge built and dropped, the jobs taken down, Steel keys - on a fake
maya.cmds put where `import maya.cmds` finds it; nothing of Maya's runs."""

import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_timebar as tb
#  every module that binds maya.cmds at its import imported now, before any test puts
#  its fake where `import maya.cmds` looks (CLAUDE.md trap 60)
from maya_timebar import bar, edge as edge_module, layerpanel, layerscene, look, scene  # noqa: F401
from PySide6 import QtWidgets  # noqa: F401


class ModuleSwap(object):
    """One `sys.modules` entry replaced and put back as it was - never
    `mock.patch.dict(sys.modules)`, which on stop drops every module imported
    meanwhile (a second copy of it on the next import)."""

    def __init__(self, name, module):
        self.name, self.module = name, module

    def start(self):
        self.had = self.name in sys.modules
        self.old = sys.modules.get(self.name)
        sys.modules[self.name] = self.module

    def stop(self):
        if self.had:
            sys.modules[self.name] = self.old
        else:
            sys.modules.pop(self.name, None)


class Cmds(object):
    """optionVar, about, workspaceControl, mayaDpiSetting, scriptJob."""

    def __init__(self):
        self.vars = {}
        self.batch = False
        self.ws = {}                        # control -> visible
        self.dpi = 1.5
        self.calls = []
        self.fail = set()
        self.jobs = {}
        self.killed = []

    def optionVar(self, q=None, exists=None, intValue=None, stringValue=None, **_):
        if exists is not None:
            return exists in self.vars
        if q is not None:
            return self.vars[q]
        for pair in (intValue, stringValue):
            if pair is not None:
                self.vars[pair[0]] = pair[1]
        return None

    def about(self, batch=False):
        if "about" in self.fail:
            raise RuntimeError("no about")
        return self.batch

    def workspaceControl(self, name, exists=False, q=False, edit=False, **kw):
        if exists:
            if "exists" in self.fail:
                raise RuntimeError("no layout")
            return name in self.ws
        if q:
            return self.ws[name]
        if edit:
            for flag in kw:
                if flag in self.fail:
                    raise RuntimeError("no flag " + flag)
            self.calls.append(("edit", name, kw))
            if "visible" in kw:
                self.ws[name] = bool(kw["visible"])
            return None
        self.calls.append(("create", name, kw))
        self.ws[name] = True
        return name

    def mayaDpiSetting(self, q=True, realScaleValue=True):
        return self.dpi

    def scriptJob(self, exists=None, kill=None, force=None):
        if "scriptJob" in self.fail:
            raise RuntimeError("no jobs")
        if exists is not None:
            return self.jobs.get(exists, False)
        self.killed.append((kill, force))
        return None


class Base(unittest.TestCase):

    def setUp(self):
        self.had_state = hasattr(sys, "_skeldar_timebar")
        self.saved_state = getattr(sys, "_skeldar_timebar", None)
        sys._skeldar_timebar = {"bar": None, "jobs": [], "callbacks": []}
        self.cmds = Cmds()
        import maya
        self.set(maya, "cmds", self.cmds, create=True)
        patcher = ModuleSwap("maya.cmds", self.cmds)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.printed = []
        self.set(tb, "print", lambda *a, **k: self.printed.append(a), create=True)

    def tearDown(self):
        if self.had_state:
            sys._skeldar_timebar = self.saved_state
        elif hasattr(sys, "_skeldar_timebar"):
            del sys._skeldar_timebar

    def set(self, obj, name, value, create=False):
        patcher = mock.patch.object(obj, name, value, create=create)
        patcher.start()
        self.addCleanup(patcher.stop)

    def record(self, obj, name, answer=None, calls=None):
        calls = [] if calls is None else calls

        def recorder(*args, **kw):
            calls.append((name, args, kw))
            if isinstance(answer, Exception):
                raise answer
            return answer(*args, **kw) if callable(answer) else answer
        self.set(obj, name, recorder)
        return calls

    def state(self):
        return sys._skeldar_timebar

    def edits(self, name=None):
        return [c for c in self.cmds.calls if c[0] == "edit" and (name is None or c[1] == name)]


class FakeEdge(object):

    def __init__(self, alive=True):
        self._alive = alive
        self.calls = []
        self.strip = "the strip"

    def alive(self):
        return self._alive

    def destroy(self):
        self.calls.append("destroy")

    def set_pinned(self, on):
        self.calls.append(("set_pinned", on))

    def reveal(self, instant=False):
        self.calls.append(("reveal", instant))


class State(Base):

    def test_a_missing_state_is_made(self):
        del sys._skeldar_timebar
        self.assertEqual(tb._state(), {"bar": None, "jobs": [], "callbacks": []})
        self.assertIs(tb._state(), sys._skeldar_timebar)


class Paths(unittest.TestCase):

    def test_the_plugin_root_holds_the_package(self):
        root = tb.plugin_root()
        self.assertNotIn("\\", root)
        self.assertTrue(os.path.isdir(os.path.join(root, "maya_timebar")))

    def test_the_ui_script_puts_the_root_on_the_path_and_builds_the_bar(self):
        text = tb.uiscript("C:\\plug\\SkeldarAnim\\")
        self.assertIn('_p = "C:/plug/SkeldarAnim"', text)
        self.assertIn("sys.path.insert(0, _p)", text)
        self.assertTrue(text.rstrip().endswith("maya_timebar.bar.build()"))
        compile(text, "uiscript", "exec")


class Mode(Base):

    def test_the_bottom_edge_by_default(self):
        self.assertEqual(tb.mode(), "edge")
        self.assertTrue(tb.wanted())

    def test_the_chosen_mode(self):
        for choice in ("maya", "docked", "edge"):
            self.cmds.vars[tb.MODE_VAR] = choice
            self.assertEqual(tb.mode(), choice)
        self.cmds.vars[tb.MODE_VAR] = "maya"
        self.assertFalse(tb.wanted())

    def test_an_older_build_s_on_off_read_when_there_is_no_mode(self):
        self.cmds.vars[tb.OPTIONVAR] = 0
        self.assertEqual(tb.mode(), "maya")
        self.cmds.vars[tb.OPTIONVAR] = 1
        self.assertEqual(tb.mode(), "docked")
        self.cmds.vars[tb.MODE_VAR] = "sideways"
        self.assertEqual(tb.mode(), "docked")                   # junk: the old one decides


class Active(Base):

    def test_nothing_standing_is_not_active(self):
        self.assertFalse(tb.active())

    def test_no_ui_is_not_active(self):
        self.state()["bar"] = "strip"
        self.cmds.batch = True
        self.assertFalse(tb.active())

    def test_a_live_edge_is_active(self):
        self.state().update(bar="strip", edge=FakeEdge())
        self.assertTrue(tb.active())

    def test_the_docked_control_counts_while_visible(self):
        self.state().update(bar="strip", edge=FakeEdge(alive=False))
        self.assertFalse(tb.active())
        self.cmds.ws[tb.CONTROL] = True
        self.assertTrue(tb.active())
        self.cmds.ws[tb.CONTROL] = False
        self.assertFalse(tb.active())

    def test_a_maya_that_fails_is_not_active(self):
        self.state()["bar"] = "strip"
        self.cmds.fail.add("about")
        self.assertFalse(tb.active())


class Highlight(unittest.TestCase):

    def test_the_highlight_as_maya_s_range_array(self):
        from maya_timebar import scene
        with mock.patch.object(scene, "read_highlight", lambda: (10.0, 20.0)):
            self.assertEqual(tb.highlight(), (10.0, 21.0))
        with mock.patch.object(scene, "read_highlight", lambda: None):
            self.assertIsNone(tb.highlight())
        with mock.patch.object(scene, "read_highlight", lambda: (5.0, 5.0)):
            self.assertIsNone(tb.highlight())                   # one frame is none


class ExtraHeight(unittest.TestCase):

    def test_the_at_bar_s_rows_or_none(self):
        import maya_atbar
        with mock.patch.object(maya_atbar, "docked_height", lambda: 57.9):
            self.assertEqual(tb.extra_height(), 57)
        with mock.patch.object(maya_atbar, "docked_height", mock.Mock(side_effect=RuntimeError("gone"))):
            self.assertEqual(tb.extra_height(), 0)


class MayaSlider(Base):

    def test_both_of_maya_s_shown_or_hidden_where_they_exist(self):
        self.cmds.ws = {"TimeSlider": True}
        tb.maya_slider(False)
        self.assertEqual(self.edits(), [("edit", "TimeSlider", {"visible": False})])
        tb.maya_slider(1)
        self.assertTrue(self.cmds.ws["TimeSlider"])

    def test_a_layout_that_fails_is_passed_by(self):
        self.cmds.fail.add("exists")
        tb.maya_slider(True)
        self.assertEqual(self.cmds.calls, [])

    def test_hide_control_only_when_it_stands(self):
        tb._hide_control()
        self.assertEqual(self.cmds.calls, [])
        self.cmds.ws[tb.CONTROL] = True
        tb._hide_control()
        self.assertFalse(self.cmds.ws[tb.CONTROL])
        self.cmds.fail.add("exists")
        tb._hide_control()                                      # swallowed


class Pinned(Base):

    def test_pinned_by_default_then_as_pressed(self):
        self.assertTrue(tb.pinned())
        tb.remember_pinned(False)
        self.assertEqual(self.cmds.vars[tb.PIN_VAR], 0)
        self.assertFalse(tb.pinned())
        tb.remember_pinned("yes")
        self.assertEqual(self.cmds.vars[tb.PIN_VAR], 1)


class EnsureDocked(Base):

    def setUp(self):
        super(EnsureDocked, self).setUp()
        self.calls = []
        self.record(tb, "drop_edge", calls=self.calls)
        self.set(tb, "extra_height", lambda: 12)
        self.current = None
        self.set(bar, "current", lambda: self.current)
        self.record(bar, "build", calls=self.calls)

    def test_batch_makes_nothing(self):
        self.cmds.batch = True
        self.assertEqual(tb.ensure_docked(), "")
        self.assertEqual(self.calls, [])

    def test_made_against_maya_s_time_slider_and_maya_s_two_hidden(self):
        self.cmds.ws = {"TimeSlider": True, "RangeSlider": True}
        self.assertEqual(tb.ensure_docked(), tb.CONTROL)
        created = [c for c in self.cmds.calls if c[0] == "create"]
        self.assertEqual(len(created), 1)
        kw = created[0][2]
        self.assertEqual(kw["dockToControl"], ("TimeSlider", "top"))
        self.assertNotIn("dockToMainWindow", kw)
        self.assertEqual((kw["initialHeight"], kw["heightProperty"], kw["actLikeMayaUIElement"]),
                         (tb.HEIGHT, "fixed", True))
        self.assertIn("maya_timebar.bar.build()", kw["uiScript"])
        self.assertEqual((self.cmds.ws["TimeSlider"], self.cmds.ws["RangeSlider"]), (False, False))
        self.assertEqual([c[0] for c in self.calls], ["drop_edge"])   # the uiScript builds it

    def test_made_at_the_window_s_bottom_without_a_time_slider(self):
        tb.ensure_docked()
        kw = [c for c in self.cmds.calls if c[0] == "create"][0][2]
        self.assertEqual(kw["dockToMainWindow"], ("bottom", False))

    def test_restored_two_rows_tall_with_no_tab_and_the_strip_built(self):
        self.cmds.ws[tb.CONTROL] = False
        tb.ensure_docked()
        edits = [c[2] for c in self.edits(tb.CONTROL)]
        self.assertEqual(edits, [{"restore": True, "visible": True}, {"actLikeMayaUIElement": True},
                                 {"resizeHeight": tb.HEIGHT + 12}])
        self.assertEqual([c[0] for c in self.calls], ["drop_edge", "build"])

    def test_a_standing_docked_strip_is_kept(self):
        self.cmds.ws[tb.CONTROL] = True
        self.current = "strip"
        self.state()["host"] = "docked"
        tb.ensure_docked()
        self.assertEqual([c[0] for c in self.calls], ["drop_edge"])

    def test_a_strip_of_the_edge_is_built_again_docked(self):
        self.cmds.ws[tb.CONTROL] = True
        self.current = "strip"
        self.state()["host"] = "edge"
        tb.ensure_docked()
        self.assertEqual([c[0] for c in self.calls], ["drop_edge", "build"])

    def test_flags_an_older_maya_refuses_are_passed_by(self):
        self.cmds.ws[tb.CONTROL] = True
        self.cmds.fail.update(("actLikeMayaUIElement", "resizeHeight"))
        self.assertEqual(tb.ensure_docked(), tb.CONTROL)


class EnsureEdge(Base):

    def setUp(self):
        super(EnsureEdge, self).setUp()
        self.made = []
        test = self

        class BottomEdge(FakeEdge):
            def __init__(self, make, on_pinned=None):
                FakeEdge.__init__(self)
                self.make, self.on_pinned = make, on_pinned
                test.made.append(self)
        self.set(edge_module, "BottomEdge", BottomEdge)
        self.calls = []
        self.record(edge_module, "destroy_all", calls=self.calls)
        from maya_timebar import layerpanel
        self.record(layerpanel, "destroy_all", calls=self.calls)
        self.record(bar, "start_jobs", calls=self.calls)
        self.cmds.ws = {tb.CONTROL: True, "TimeSlider": True, "RangeSlider": True}

    def test_batch_makes_nothing(self):
        self.cmds.batch = True
        self.assertIsNone(tb.ensure_edge())
        self.assertEqual(self.made, [])

    def test_a_standing_edge_kept_and_maya_s_hidden(self):
        standing = FakeEdge()
        self.state()["edge"] = standing
        self.assertIs(tb.ensure_edge(), standing)
        self.assertEqual(self.made, [])
        self.assertFalse(self.cmds.ws["TimeSlider"])

    def test_built_the_docked_hidden_the_strip_its_and_pinned_out(self):
        controller = tb.ensure_edge()
        self.assertIs(controller, self.made[0])
        self.assertEqual((self.state()["edge"], self.state()["bar"], self.state()["host"]),
                         (controller, "the strip", "edge"))
        self.assertIs(controller.on_pinned, tb.remember_pinned)
        self.assertEqual([c[0] for c in self.calls], ["destroy_all", "destroy_all", "start_jobs"])
        self.assertEqual(self.cmds.ws, {tb.CONTROL: False, "TimeSlider": False, "RangeSlider": False})
        self.assertEqual(controller.calls, [("set_pinned", True), ("reveal", True)])

    def test_the_strip_made_with_maya_s_scale(self):
        made = self.record(bar, "make", answer="strip")
        controller = tb.ensure_edge()
        self.assertEqual(controller.make("host"), "strip")
        args, kw = made[0][1], made[0][2]
        self.assertIsInstance(args[0], bar.Link)
        self.assertEqual((args[1], kw), (1.5, {"parent": "host"}))

    def test_unpinned_it_waits_at_the_edge(self):
        self.cmds.vars[tb.PIN_VAR] = 0
        self.cmds.dpi = None
        controller = tb.ensure_edge()
        self.assertEqual(controller.calls, [])

    def test_a_reveal_that_fails_is_printed(self):
        class Bad(FakeEdge):
            def __init__(self, make, on_pinned=None):
                FakeEdge.__init__(self)

            def reveal(self, instant=False):
                raise RuntimeError("no window")
        self.set(edge_module, "BottomEdge", Bad)
        self.assertIsNotNone(tb.ensure_edge())
        self.assertTrue(any("no window" in str(a) for a in self.printed))

    def test_a_layer_panel_that_fails_is_passed_by(self):
        from maya_timebar import layerpanel
        self.set(layerpanel, "destroy_all", mock.Mock(side_effect=RuntimeError("dead column")))
        self.assertIsNotNone(tb.ensure_edge())


class DropEdge(Base):

    def setUp(self):
        super(DropEdge, self).setUp()
        from maya_timebar import layerpanel
        self.columns = self.record(layerpanel, "destroy_all")

    def test_the_edge_and_its_strip_dropped(self):
        edge = FakeEdge()
        self.state().update(edge=edge, bar="strip", host="edge")
        tb.drop_edge()
        self.assertEqual(edge.calls, ["destroy"])
        self.assertNotIn("edge", self.state())
        self.assertEqual((self.state()["bar"], self.state()["host"]), (None, None))
        self.assertEqual(len(self.columns), 1)

    def test_a_docked_strip_stays(self):
        self.state().update(edge=FakeEdge(), bar="docked strip", host="docked")
        tb.drop_edge()
        self.assertEqual((self.state()["bar"], self.state()["host"]), ("docked strip", "docked"))

    def test_failures_are_swallowed_and_nothing_standing_is_fine(self):
        from maya_timebar import layerpanel
        self.set(layerpanel, "destroy_all", mock.Mock(side_effect=RuntimeError("dead")))
        edge = FakeEdge()
        edge.destroy = mock.Mock(side_effect=RuntimeError("gone"))
        self.state().update(edge=edge, host="edge", bar="s")
        tb.drop_edge()
        self.assertIsNone(self.state()["bar"])
        tb.drop_edge()


class SetMode(Base):

    def setUp(self):
        super(SetMode, self).setUp()
        self.calls = []
        for name in ("ensure_docked", "ensure_edge", "drop_edge", "_hide_control", "maya_slider"):
            self.record(tb, name, calls=self.calls)

    def test_maya_s_remembered_ours_dropped_and_maya_s_shown(self):
        self.assertEqual(tb.set_mode("maya"), tb.MESSAGES["maya"])
        self.assertEqual((self.cmds.vars[tb.MODE_VAR], self.cmds.vars[tb.OPTIONVAR]), ("maya", 0))
        self.assertNotIn(tb.LAST_VAR, self.cmds.vars)
        self.assertEqual(self.calls, [("drop_edge", (), {}), ("_hide_control", (), {}),
                                      ("maya_slider", (True,), {})])

    def test_docked_remembered_as_the_last_and_stood(self):
        self.assertEqual(tb.set_mode("docked"), tb.MESSAGES["docked"])
        self.assertEqual((self.cmds.vars[tb.MODE_VAR], self.cmds.vars[tb.OPTIONVAR],
                          self.cmds.vars[tb.LAST_VAR]), ("docked", 1, "docked"))
        self.assertEqual([c[0] for c in self.calls], ["ensure_docked"])

    def test_the_edge(self):
        self.assertEqual(tb.set_mode("edge"), tb.MESSAGES["edge"])
        self.assertEqual(self.cmds.vars[tb.LAST_VAR], "edge")
        self.assertEqual([c[0] for c in self.calls], ["ensure_edge"])

    def test_an_unknown_choice_is_docked(self):
        self.assertEqual(tb.set_mode("floating"), tb.MESSAGES["docked"])
        self.assertEqual(self.cmds.vars[tb.MODE_VAR], "docked")


class Switches(Base):

    def setUp(self):
        super(Switches, self).setUp()
        self.chosen = self.record(tb, "set_mode", answer=lambda c: "said " + c)

    def test_show_brings_back_the_last_of_ours(self):
        self.assertEqual(tb.show(), "said docked")
        self.cmds.vars[tb.LAST_VAR] = "edge"
        self.assertEqual(tb.show(), "said edge")
        self.cmds.vars[tb.LAST_VAR] = "maya"
        self.assertEqual(tb.show(), "said docked")

    def test_hide_is_maya_s(self):
        self.assertEqual(tb.hide(), "said maya")

    def test_set_on_takes_a_choice_or_on_off(self):
        self.assertEqual(tb.set_on("edge"), "said edge")
        self.assertEqual(tb.set_on(True), "said docked")
        self.assertEqual(tb.set_on(False), "said maya")

    def test_toggle_hides_a_standing_bar_and_shows_one_that_is_not(self):
        self.set(tb, "active", lambda: True)
        self.assertEqual(tb.toggle(), "said maya")                # wanted (the edge) and active
        self.set(tb, "active", lambda: False)
        self.assertEqual(tb.toggle(), "said docked")
        self.cmds.vars[tb.MODE_VAR] = "maya"
        self.set(tb, "active", lambda: True)
        self.assertEqual(tb.toggle(), "said docked")


class Upgrade(Base):

    def test_once_to_the_bottom_edge(self):
        self.cmds.vars[tb.MODE_VAR] = "docked"
        self.assertEqual(tb.upgrade(), "edge")
        self.assertEqual(self.cmds.vars[tb.MODE_VAR], "edge")
        self.assertEqual(self.cmds.vars[tb.DEFAULTS_VAR], look.DEFAULT_VERSION)
        self.cmds.vars[tb.MODE_VAR] = "docked"                  # chosen again after the update
        self.assertEqual(tb.upgrade(), "docked")
        self.assertEqual(self.cmds.vars[tb.MODE_VAR], "docked")

    def test_maya_s_own_slider_is_kept(self):
        self.cmds.vars[tb.MODE_VAR] = "maya"
        self.assertEqual(tb.upgrade(), "maya")
        self.assertEqual(self.cmds.vars[tb.DEFAULTS_VAR], look.DEFAULT_VERSION)

    def test_ensure_stands_what_upgrade_answers(self):
        calls = []
        self.record(tb, "ensure_edge", answer="edge", calls=calls)
        self.record(tb, "ensure_docked", answer="docked", calls=calls)
        for choice, want in (("edge", "edge"), ("docked", "docked"), ("maya", None)):
            self.set(tb, "upgrade", lambda c=choice: c)
            self.assertEqual(tb.ensure(), want)
        self.assertEqual([c[0] for c in calls], ["ensure_edge", "ensure_docked"])


class FakeOpenMaya(object):
    def __init__(self):
        self.removed = []
        fake = self

        class MMessage(object):
            @staticmethod
            def removeCallback(cid):
                if cid == "bad":
                    raise RuntimeError("bad id")
                fake.removed.append(cid)
        self.om = types.ModuleType("maya.api.OpenMaya")
        self.om.MMessage = MMessage


class StopJobs(Base):

    def setUp(self):
        super(StopJobs, self).setUp()
        import maya.api
        self.fake = FakeOpenMaya()
        self.set(maya.api, "OpenMaya", self.fake.om, create=True)
        patcher = ModuleSwap("maya.api.OpenMaya", self.fake.om)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_live_jobs_killed_and_callbacks_removed(self):
        self.cmds.jobs = {3: True}
        self.state().update(jobs=[3, 4], callbacks=[7, "bad", 8])
        tb._stop_jobs()
        self.assertEqual(self.cmds.killed, [(3, True)])
        self.assertEqual(self.fake.removed, [7, 8])
        self.assertEqual((self.state()["jobs"], self.state()["callbacks"]), ([], []))

    def test_a_maya_that_cannot_ask_still_forgets_them(self):
        self.cmds.fail.add("scriptJob")
        self.state().update(jobs=[3])
        tb._stop_jobs()
        self.assertEqual(self.state()["jobs"], [])

    def test_no_openmaya_still_forgets_the_callbacks(self):
        import maya.api
        self.set(maya.api, "OpenMaya", None)
        patcher = ModuleSwap("maya.api.OpenMaya", None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.state().update(callbacks=[1])
        tb._stop_jobs()
        self.assertEqual(self.state()["callbacks"], [])


class ReloadLive(Base):

    def setUp(self):
        super(ReloadLive, self).setUp()
        self.calls = []
        self.record(tb, "drop_edge", calls=self.calls)
        self.record(tb, "_stop_jobs", calls=self.calls)
        self.answer = "bar"
        self.record(tb, "ensure", answer=lambda: self.answer, calls=self.calls)

    def test_batch_reloads_nothing(self):
        self.cmds.batch = True
        self.assertFalse(tb.reload_live())
        self.assertEqual(self.calls, [])

    def test_the_old_bar_forgotten_and_built_again(self):
        self.state().update(bar="old strip", host="docked")
        self.assertTrue(tb.reload_live())
        self.assertEqual([c[0] for c in self.calls], ["drop_edge", "_stop_jobs", "ensure"])
        self.assertEqual((self.state()["bar"], self.state()["host"]), (None, None))
        self.answer = None
        self.assertFalse(tb.reload_live())


class Steel(Base):

    def test_steel_asks_the_strip_s_choice(self):
        self.set(bar, "steel_on", lambda: "as chosen")
        self.assertEqual(tb.steel(), "as chosen")

    def widget(self, name, steel=True):
        w = types.SimpleNamespace(objectName=lambda: name, got=[])
        if steel:
            w.set_steel = w.got.append
        return w

    def test_remembered_and_every_standing_strip_repainted(self):
        from PySide6 import QtWidgets
        ours = self.widget(bar.ROOT_NAME)
        old = self.widget(bar.ROOT_NAME, steel=False)          # an older strip's root
        other = self.widget("someone else")
        self.set(QtWidgets.QApplication, "allWidgets", staticmethod(lambda: [ours, old, other]))
        self.assertIn("cools into steel", tb.set_steel(True))
        self.assertEqual(self.cmds.vars[look.STEEL_VAR], 1)
        self.assertEqual(ours.got, [True])
        self.assertEqual(other.got, [])
        self.assertIn("orange", tb.set_steel(0))
        self.assertEqual(self.cmds.vars[look.STEEL_VAR], 0)
        self.assertEqual(ours.got, [True, 0])

    def test_a_qt_that_fails_still_remembers(self):
        from PySide6 import QtWidgets
        self.set(QtWidgets.QApplication, "allWidgets",
                 staticmethod(mock.Mock(side_effect=RuntimeError("no app"))))
        tb.set_steel(False)
        self.assertEqual(self.cmds.vars[look.STEEL_VAR], 0)
        self.assertTrue(any("no app" in str(a) for a in self.printed))


if __name__ == "__main__":
    unittest.main()
