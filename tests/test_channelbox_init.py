"""maya_channelbox, the switch and the callbacks: the optionVar ours is on by, what
switching it does to the side panel and the hub's menu, when the box counts as shown,
which attribute messages ask for a full read and which for the values, and the
OpenMaya callbacks it puts on (and takes off) - on fakes, nothing of Maya's runs."""

import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_channelbox as cb


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


class OptionVars(object):
    def __init__(self, values=None):
        self.values = dict(values or {})

    def optionVar(self, q=None, exists=None, intValue=None, **_):
        if exists is not None:
            return exists in self.values
        if q is not None:
            return self.values[q]
        if intValue is not None:
            self.values[intValue[0]] = intValue[1]


class StateCase(unittest.TestCase):
    """The module's state on `sys` saved and put back around every test."""

    def setUp(self):
        self.had_state = hasattr(sys, "_skeldar_channelbox")
        self.saved_state = getattr(sys, "_skeldar_channelbox", None)
        if self.had_state:
            del sys._skeldar_channelbox
        self.saved_cmds = cb._cmds

    def tearDown(self):
        cb._cmds = self.saved_cmds
        if self.had_state:
            sys._skeldar_channelbox = self.saved_state
        elif hasattr(sys, "_skeldar_channelbox"):
            del sys._skeldar_channelbox


class Enabled(StateCase):

    def test_on_by_default_then_as_remembered(self):
        fake = OptionVars()
        cb._cmds = lambda: fake
        self.assertTrue(cb.enabled())
        fake.values[cb.VAR] = 0
        self.assertFalse(cb.enabled())
        fake.values[cb.VAR] = 1
        self.assertTrue(cb.enabled())

    def test_on_where_maya_cannot_be_asked(self):
        def boom():
            raise ImportError("no maya")
        cb._cmds = boom
        self.assertTrue(cb.enabled())

    def test_cmds_is_maya_s(self):
        import maya.cmds
        self.assertIs(self.saved_cmds(), maya.cmds)


class SetEnabled(StateCase):

    def setUp(self):
        super(SetEnabled, self).setUp()
        import maya_sidepanel
        self.side = maya_sidepanel
        self.saved_side = (maya_sidepanel.mode, maya_sidepanel.rebuild)
        self.fake = OptionVars()
        cb._cmds = lambda: self.fake
        self.rebuilt = []
        self.painted = []
        self.side_mode = "edge"
        maya_sidepanel.mode = lambda: self.side_mode
        maya_sidepanel.rebuild = lambda: self.rebuilt.append(True)
        hub = types.ModuleType("maya_hub")
        hub.repaint_sidepanel = lambda: self.painted.append(True)
        self.hub = ModuleSwap("maya_hub", hub)
        self.hub.start()

    def tearDown(self):
        self.hub.stop()
        self.side.mode, self.side.rebuild = self.saved_side
        super(SetEnabled, self).tearDown()

    def test_off_remembered_the_panel_rebuilt_and_the_menu_repainted(self):
        self.assertEqual(cb.set_enabled(0), "Side panel: Maya's Channel Box")
        self.assertEqual(self.fake.values[cb.VAR], 0)
        self.assertEqual(self.rebuilt, [True])
        self.assertEqual(self.painted, [True])

    def test_on_in_maya_s_mode_leaves_the_panel_alone(self):
        self.side_mode = "maya"
        self.assertEqual(cb.set_enabled("yes"), "Side panel: our Channel Box")
        self.assertEqual(self.fake.values[cb.VAR], 1)
        self.assertEqual(self.rebuilt, [])
        self.assertEqual(self.painted, [True])

    def test_a_rebuild_that_fails_still_answers(self):
        def boom():
            raise RuntimeError("no window")
        self.side.rebuild = boom
        out = []
        with mock.patch("builtins.print", lambda *a, **k: out.append(a)):
            self.assertEqual(cb.set_enabled(True), "Side panel: our Channel Box")
        self.assertTrue(any("no window" in str(a) for a in out))
        self.assertEqual(self.painted, [True])

    def test_a_hub_that_cannot_repaint_is_passed_by(self):
        sys.modules["maya_hub"].repaint_sidepanel = None        # not callable
        self.assertEqual(cb.set_enabled(False), "Side panel: Maya's Channel Box")


class Shown(StateCase):

    def setUp(self):
        super(Shown, self).setUp()
        import maya_sidepanel
        self.side = maya_sidepanel
        self.saved_side_state = maya_sidepanel._state

    def tearDown(self):
        self.side._state = self.saved_side_state
        super(Shown, self).tearDown()

    def edge(self, alive=True, shown=True, tab="channels"):
        panel = types.SimpleNamespace(tab=tab)
        return types.SimpleNamespace(alive=lambda: alive, shown=shown, panel=panel)

    def with_edge(self, edge):
        self.side._state = lambda: {"edge": edge}
        return cb._shown()

    def test_shown_only_out_and_on_the_channels_tab(self):
        self.assertTrue(self.with_edge(self.edge()))
        self.assertFalse(self.with_edge(self.edge(tab="attributes")))
        self.assertFalse(self.with_edge(self.edge(shown=False)))
        self.assertFalse(self.with_edge(self.edge(alive=False)))
        self.assertFalse(self.with_edge(None))

    def test_shown_when_the_side_panel_cannot_be_asked(self):
        def boom():
            raise RuntimeError("no panel")
        self.side._state = boom
        self.assertTrue(cb._shown())


class AttrChanged(StateCase):

    def setUp(self):
        super(AttrChanged, self).setUp()
        self.saved_schedule = cb._schedule
        self.asked = []
        cb._schedule = self.asked.append

    def tearDown(self):
        cb._schedule = self.saved_schedule
        super(AttrChanged, self).tearDown()

    def test_a_connection_or_a_lock_asks_for_a_full_read(self):
        import maya.api.OpenMaya as om
        for msg in (om.MNodeMessage.kConnectionMade, om.MNodeMessage.kConnectionBroken,
                    om.MNodeMessage.kAttributeLocked, om.MNodeMessage.kAttributeUnlocked,
                    om.MNodeMessage.kAttributeKeyable, om.MNodeMessage.kAttributeUnkeyable,
                    om.MNodeMessage.kConnectionMade | om.MNodeMessage.kAttributeSet):
            cb._attr_changed(msg, None, None)
        self.assertEqual(self.asked, ["full"] * 7)

    def test_a_value_set_asks_for_the_values(self):
        import maya.api.OpenMaya as om
        cb._attr_changed(om.MNodeMessage.kAttributeSet, None, None, "client data")
        self.assertEqual(self.asked, ["values"])

    def test_anything_else_asks_nothing(self):
        import maya.api.OpenMaya as om
        cb._attr_changed(om.MNodeMessage.kAttributeEval, None, None)
        cb._attr_changed(0, None, None)
        self.assertEqual(self.asked, [])

    def test_a_message_that_is_no_number_is_swallowed(self):
        cb._attr_changed("nonsense", None, None)
        self.assertEqual(self.asked, [])


class FakeOpenMaya(object):
    """maya.api.OpenMaya and OpenMayaAnim as fakes: every callback added gets an id
    and its function kept; every removal recorded."""

    def __init__(self):
        self.next = [100]
        self.added = []                  # (kind, what, fn)
        self.removed = []
        self.bad_nodes = set()
        self.refuse_events = set()
        self.refuse_time = False
        fake = self

        def add(kind, what, fn):
            fake.next[0] += 1
            fake.added.append((kind, what, fn))
            return fake.next[0]

        class MSelectionList(object):
            def __init__(self):
                self.nodes = []

            def add(self, node):
                if node in fake.bad_nodes:
                    raise RuntimeError("no object " + node)
                self.nodes.append(node)

            def getDependNode(self, i):
                return "MObject(%s)" % self.nodes[i]

        class MNodeMessage(object):
            @staticmethod
            def addAttributeChangedCallback(obj, fn):
                return add("attr", obj, fn)

        class MEventMessage(object):
            @staticmethod
            def addEventCallback(event, fn):
                if event in fake.refuse_events:
                    raise RuntimeError("no event " + event)
                return add("event", event, fn)

        class MDGMessage(object):
            @staticmethod
            def addTimeChangeCallback(fn):
                if fake.refuse_time:
                    raise RuntimeError("no time callback")
                return add("time", None, fn)

        class MMessage(object):
            @staticmethod
            def removeCallback(cid):
                if cid == "bad":
                    raise RuntimeError("bad id")
                fake.removed.append(cid)

        class MAnimMessage(object):
            @staticmethod
            def addAnimKeyframeEditedCallback(fn):
                return add("keys", None, fn)

        self.om = types.ModuleType("maya.api.OpenMaya")
        for cls in (MSelectionList, MNodeMessage, MEventMessage, MDGMessage, MMessage):
            setattr(self.om, cls.__name__, cls)
        self.oma = types.ModuleType("maya.api.OpenMayaAnim")
        self.oma.MAnimMessage = MAnimMessage

    def patches(self):
        import maya.api
        return [ModuleSwap("maya.api.OpenMaya", self.om),
                ModuleSwap("maya.api.OpenMayaAnim", self.oma),
                mock.patch.object(maya.api, "OpenMaya", self.om, create=True),
                mock.patch.object(maya.api, "OpenMayaAnim", self.oma, create=True)]


class Callbacks(StateCase):

    def setUp(self):
        super(Callbacks, self).setUp()
        self.fake = FakeOpenMaya()
        self.patches = self.fake.patches()
        for p in self.patches:
            p.start()
        self.saved_schedule = cb._schedule
        self.asked = []
        cb._schedule = self.asked.append

    def tearDown(self):
        cb._schedule = self.saved_schedule
        for p in reversed(self.patches):
            p.stop()
        super(Callbacks, self).tearDown()

    def test_watch_nodes_puts_one_callback_on_each_node_and_drops_the_last_ones(self):
        cb._state()["node_callbacks"] = [7, "bad", 8]
        cb._watch_nodes(["|a", "|gone", "|b"])
        self.assertEqual(self.fake.removed, [7, 8])
        attrs = [a for a in self.fake.added if a[0] == "attr"]
        self.assertEqual([a[1] for a in attrs], ["MObject(|a)", "MObject(|gone)", "MObject(|b)"])
        self.assertEqual(len(cb._state()["node_callbacks"]), 3)
        self.assertIs(attrs[0][2], cb._attr_changed)

    def test_watch_nodes_skips_a_node_it_cannot_find(self):
        self.fake.bad_nodes.add("|gone")
        cb._watch_nodes(["|a", "|gone"])
        self.assertEqual([a[1] for a in self.fake.added], ["MObject(|a)"])
        self.assertEqual(cb._state()["node_callbacks"], [101])

    def test_watch_nodes_with_nothing_selected(self):
        cb._watch_nodes(None)
        self.assertEqual(cb._state()["node_callbacks"], [])

    def test_start_callbacks_hears_the_four_events_the_time_and_the_keys(self):
        cb._state()["callbacks"] = [1, 2]
        cb._state()["node_callbacks"] = [3]
        cb._start_callbacks()
        self.assertEqual(self.fake.removed, [1, 2, 3])               # the old ones first
        events = [a[1] for a in self.fake.added if a[0] == "event"]
        self.assertEqual(events, ["SelectionChanged", "Undo", "Redo", "animLayerRefresh"])
        kinds = [a[0] for a in self.fake.added]
        self.assertEqual(kinds, ["event"] * 4 + ["time", "keys"])
        self.assertEqual(cb._state()["callbacks"], [101, 102, 103, 104, 105, 106])
        self.assertEqual(cb._state()["node_callbacks"], [])
        time_fn = [a[2] for a in self.fake.added if a[0] == "time"][0]
        keys_fn = [a[2] for a in self.fake.added if a[0] == "keys"][0]
        self.assertIs(time_fn, cb._time_changed)
        self.assertIs(keys_fn, cb._key_edited)

    def test_every_event_asks_for_a_full_read(self):
        cb._start_callbacks()
        for kind, what, fn in self.fake.added:
            if kind == "event":
                fn("client", "data")
        self.assertEqual(self.asked, ["full"] * 4)

    def test_an_event_maya_refuses_is_passed_by(self):
        self.fake.refuse_events.add("animLayerRefresh")
        cb._start_callbacks()
        self.assertEqual(len(cb._state()["callbacks"]), 5)

    def test_a_failing_time_callback_keeps_what_was_added(self):
        self.fake.refuse_time = True
        out = []
        with mock.patch("builtins.print", lambda *a, **k: out.append(a)):
            cb._start_callbacks()
        self.assertEqual(cb._state()["callbacks"], [101, 102, 103, 104])
        self.assertTrue(any("no time callback" in str(a) for a in out))

    def test_stop_callbacks_takes_off_both_lists(self):
        cb._state()["callbacks"] = [5]
        cb._state()["node_callbacks"] = [6]
        cb._stop_callbacks()
        self.assertEqual(self.fake.removed, [5, 6])
        self.assertEqual((cb._state()["callbacks"], cb._state()["node_callbacks"]), ([], []))


class TimeChanged(StateCase):

    def setUp(self):
        super(TimeChanged, self).setUp()
        self.saved = (cb.current, cb._shown)
        self.box = types.SimpleNamespace(calls=[])
        self.box.on_time = lambda: self.box.calls.append("time")
        self.shown = True
        cb.current = lambda: self.box
        cb._shown = lambda: self.shown

    def tearDown(self):
        cb.current, cb._shown = self.saved
        super(TimeChanged, self).tearDown()

    def test_shown_the_key_cells_follow_the_time(self):
        cb._time_changed(12.0)
        self.assertEqual(self.box.calls, ["time"])

    def test_hidden_it_is_read_again_when_shown(self):
        self.shown = False
        cb._time_changed()
        self.assertEqual(self.box.calls, [])
        self.assertTrue(cb._state()["missed"])

    def test_no_box_nothing(self):
        cb.current = lambda: None
        cb._time_changed()
        self.assertNotIn("missed", cb._state())

    def test_a_box_that_fails_never_raises(self):
        def boom():
            raise RuntimeError("dead")
        self.box.on_time = boom
        cb._time_changed()


class FakeQt(object):
    """maya_hubqt.qt(): a shiboken that answers whether a wrapper is alive, and a
    QTimer whose single shots are kept to be fired by hand."""

    def __init__(self, valid=True):
        self.valid = valid
        self.shots = []
        fake = self

        class Shiboken(object):
            @staticmethod
            def isValid(obj):
                return fake.valid

        class QTimer(object):
            @staticmethod
            def singleShot(ms, fn):
                fake.shots.append(fn)

        self.shiboken = Shiboken
        self.QtCore = types.SimpleNamespace(QTimer=QTimer)


class Reads(StateCase):
    """The box found again, the reads scheduled and run, each failure kept away from
    Maya's callbacks."""

    def setUp(self):
        super(Reads, self).setUp()
        import maya_hubqt
        self.hubqt = maya_hubqt
        self.qt = FakeQt()
        self.patcher = mock.patch.object(maya_hubqt, "qt", lambda: self.qt)
        self.patcher.start()
        self.printed = []
        self.printer = mock.patch.object(cb, "print", lambda *a, **k: self.printed.append(a), create=True)
        self.printer.start()

    def tearDown(self):
        self.printer.stop()
        self.patcher.stop()
        super(Reads, self).tearDown()

    def box(self, **raises):
        box = types.SimpleNamespace(calls=[], objects=["|a"])
        for name in ("refresh", "on_values", "on_time"):
            def call(*a, _name=name, **k):
                box.calls.append(_name)
                if _name in raises:
                    raise RuntimeError(raises[_name])
            setattr(box, name, call)
        return box

    def test_current_is_the_box_while_its_wrapper_lives(self):
        self.assertIsNone(cb.current())
        box = self.box()
        cb._state()["box"] = box
        self.assertIs(cb.current(), box)
        self.qt.valid = False
        self.assertIsNone(cb.current())
        self.assertIsNone(cb._state()["box"])                    # the dead wrapper dropped

    def test_current_is_none_where_qt_cannot_be_asked(self):
        cb._state()["box"] = self.box()
        with mock.patch.object(self.hubqt, "qt", mock.Mock(side_effect=ImportError("no Qt"))):
            self.assertIsNone(cb.current())

    def test_refresh_without_a_box_reads_nothing(self):
        cb.refresh()
        self.assertNotIn("read_gen", cb._state())

    def test_a_read_that_fails_is_printed(self):
        cb._state()["box"] = self.box(refresh="dead model")
        with mock.patch.object(cb, "_watch_nodes", lambda nodes: None):
            cb.refresh()
        self.assertTrue(any("dead model" in str(a) for a in self.printed))

    def test_a_full_read_waiting_takes_no_second_timer(self):
        cb._schedule("full")
        cb._schedule("full")
        cb._schedule("values")
        self.assertEqual(len(self.qt.shots), 1)
        self.assertEqual((cb._state()["pending"], cb._state()["gen"]), ("full", 2))

    def test_values_then_a_full_read_one_timer(self):
        cb._schedule("values")
        cb._schedule("values")
        self.assertEqual(cb._state()["pending"], "values")
        cb._schedule("full")
        self.assertEqual(len(self.qt.shots), 1)
        self.assertEqual(cb._state()["pending"], "full")

    def test_no_timer_runs_the_read_at_once(self):
        ran = []
        with mock.patch.object(self.hubqt, "qt", mock.Mock(side_effect=RuntimeError("no Qt"))), \
                mock.patch.object(cb, "_run_pending", lambda: ran.append(True)):
            cb._schedule("values")
        self.assertEqual(ran, [True])

    def test_a_pending_read_with_nothing_asked_or_no_box_does_nothing(self):
        cb._run_pending()                                       # nothing pending
        cb._state()["pending"] = "values"
        cb._run_pending()                                       # no box
        self.assertIsNone(cb._state()["pending"])

    def test_a_values_read_that_fails_is_printed(self):
        cb._state().update(box=self.box(on_values="no plug"), pending="values")
        with mock.patch.object(cb, "_shown", lambda: True):
            cb._run_pending()
        self.assertTrue(any("no plug" in str(a) for a in self.printed))

    def test_a_pending_full_read_reads_the_box_once(self):
        box = self.box()
        cb._state().update(box=box, pending="full")
        with mock.patch.object(cb, "_shown", lambda: True), \
                mock.patch.object(cb, "_watch_nodes", lambda nodes: None):
            cb._run_pending()
            cb._state()["pending"] = "full"
            cb._run_pending()                                   # current already: not again
        self.assertEqual(box.calls, ["refresh"])

    def test_unmount_where_qt_fails_answers_false(self):
        cb._state()["box"] = self.box()
        with mock.patch.object(self.hubqt, "qt", mock.Mock(side_effect=RuntimeError("no Qt"))), \
                mock.patch.object(cb, "_stop_callbacks", lambda: None):
            self.assertFalse(cb.unmount())
        self.assertIsNone(cb._state()["box"])


class Mount(StateCase):
    """mount's early answers and a first read that fails, on real offscreen widgets."""

    def setUp(self):
        super(Mount, self).setUp()
        import maya_hubqt
        from maya_sidepanel import holder
        from maya_channelbox import box as box_module
        self.QtWidgets = maya_hubqt.qt().QtWidgets
        self.app = self.QtWidgets.QApplication.instance() or self.QtWidgets.QApplication([])
        self.holder, self.box_module = holder, box_module
        self.saved = (holder.widget, cb.enabled, cb._start_callbacks, box_module.make)
        cb._start_callbacks = lambda: None
        self.on = True
        cb.enabled = lambda: self.on
        self.page = self.QtWidgets.QWidget()
        self.layout = self.QtWidgets.QVBoxLayout(self.page)
        self.form = self.QtWidgets.QWidget(self.page)
        self.layout.addWidget(self.form)
        self.panel = types.SimpleNamespace(pages={"channels": self.layout})

    def tearDown(self):
        cb.unmount()
        (self.holder.widget, cb.enabled, cb._start_callbacks, self.box_module.make) = self.saved
        self.page.deleteLater()
        super(Mount, self).tearDown()

    def test_off_mounts_nothing(self):
        self.on = False
        self.assertIsNone(cb.mount(self.panel, [{"form": "F"}]))

    def test_no_form_found_mounts_nothing(self):
        self.holder.widget = lambda name: None
        self.assertIsNone(cb.mount(self.panel, [{"form": "F"}]))
        self.assertIsNone(cb._state()["box"])

    def test_a_first_read_that_fails_still_mounts(self):
        QtWidgets = self.QtWidgets

        class Box(QtWidgets.QWidget):
            def refresh(self, effects=True):
                raise RuntimeError("first read")
        self.holder.widget = lambda name: self.form
        self.box_module.make = lambda link, ui, tokens, parent=None, motion=None: Box(parent)
        printed = []
        with mock.patch.object(cb, "print", lambda *a, **k: printed.append(a), create=True):
            built = cb.mount(self.panel, [{"form": "F"}])
        self.assertIsInstance(built, Box)
        self.assertIs(cb._state()["box"], built)
        self.assertTrue(any("first read" in str(a) for a in printed))


class NoOpenMaya(StateCase):

    def test_no_openmaya_watches_nothing_and_drops_nothing(self):
        import maya.api
        swap = ModuleSwap("maya.api.OpenMaya", None)
        swap.start()
        try:
            with mock.patch.object(maya.api, "OpenMaya", None):
                cb._watch_nodes(["|a"])
                cb._drop([1, 2])
        finally:
            swap.stop()
        self.assertEqual(cb._state()["node_callbacks"], [])


if __name__ == "__main__":
    unittest.main()
