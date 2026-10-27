"""maya_sidepanel's own module (2026-10-17): the mode and what switching it hides or
gives back, the optionVars it reads and writes, the borrow of Maya's forms and their
return, the build of the edge and its callbacks, the selection callback and its
fallback, refresh and the least width - on a fake cmds and fake holder / skin / edge,
nothing of Maya's runs."""

import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_hubstyle
import maya_sidepanel as sp
from maya_sidepanel import edge as edge_module, holder, look, panel, skin


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
    """optionVar, about, workspaceControl, play, evalDeferred, scriptJob, ls."""

    def __init__(self):
        self.vars = {}
        self.batch = False
        self.ws = set()
        self.dpi = 1.5
        self.sel = []
        self.playing = False
        self.fail = set()
        self.deferred = []
        self.jobs = {}
        self.killed = []
        self.next_job = [500]

    def optionVar(self, q=None, exists=None, intValue=None, stringValue=None, floatValue=None,
                  remove=None, stringValueAppend=None, **_):
        if exists is not None:
            return exists in self.vars
        if q is not None:
            return self.vars[q]
        if remove is not None:
            self.vars.pop(remove, None)
            return None
        for pair in (intValue, stringValue, floatValue):
            if pair is not None:
                self.vars[pair[0]] = pair[1]
        if stringValueAppend is not None:
            self.vars.setdefault(stringValueAppend[0], []).append(stringValueAppend[1])
        return None

    def about(self, batch=False):
        return self.batch

    def workspaceControl(self, name, exists=False):
        return name in self.ws

    def mayaDpiSetting(self, q=True, realScaleValue=True):
        return self.dpi

    def play(self, q=True, state=True):
        if "play" in self.fail:
            raise RuntimeError("no play")
        return self.playing

    def evalDeferred(self, fn, lowestPriority=False):
        if "evalDeferred" in self.fail:
            raise RuntimeError("no idle queue")
        self.deferred.append((fn, lowestPriority))

    def scriptJob(self, event=None, killWithScene=None, exists=None, kill=None, force=None):
        if "scriptJob" in self.fail:
            raise RuntimeError("no jobs")
        if exists is not None:
            return self.jobs.get(exists, False)
        if kill is not None:
            self.killed.append((kill, force))
            return None
        self.next_job[0] += 1
        self.jobs[self.next_job[0]] = True
        self.event = (event, killWithScene)
        return self.next_job[0]

    def ls(self, selection=False, head=None):
        return list(self.sel)


class Base(unittest.TestCase):

    def setUp(self):
        self.had_state = hasattr(sys, "_skeldar_sidepanel")
        self.saved_state = getattr(sys, "_skeldar_sidepanel", None)
        sys._skeldar_sidepanel = {"edge": None, "held": {}}
        self.cmds = Cmds()
        self.real_cmds = sp._cmds
        self.set(sp, "_cmds", lambda: self.cmds)
        self.printed = []
        self.set(sp, "print", lambda *a, **k: self.printed.append(a), create=True)

    def tearDown(self):
        if self.had_state:
            sys._skeldar_sidepanel = self.saved_state
        elif hasattr(sys, "_skeldar_sidepanel"):
            del sys._skeldar_sidepanel

    def set(self, obj, name, value, create=False):
        patcher = mock.patch.object(obj, name, value, create=create)
        patcher.start()
        self.addCleanup(patcher.stop)

    def record(self, obj, name, answer=None, calls=None):
        """`obj.name` replaced by a recorder; its calls in the list returned."""
        calls = [] if calls is None else calls

        def recorder(*args, **kw):
            calls.append((name, args, kw))
            if isinstance(answer, Exception):
                raise answer
            return answer(*args, **kw) if callable(answer) else answer
        self.set(obj, name, recorder)
        return calls

    def state(self):
        return sys._skeldar_sidepanel


class FakeEdge(object):
    """What the module asks of the SideEdge controller."""

    def __init__(self, alive=True, shown=True, tab="channels", selection=False):
        self._alive = alive
        self.shown = shown
        self.calls = []
        self.least = 0
        self.selection = selection
        self.panel = types.SimpleNamespace(tab=tab, ui=1.5, pages={"channels": "Lc", "attributes": "La"},
                                           stack=types.SimpleNamespace(currentWidget=lambda: None))
        self.panel.set_tab = lambda value: self.calls.append(("set_tab", value))

    def alive(self):
        return self._alive

    def reveal(self, **kw):
        self.calls.append(("reveal", kw))

    def set_pinned(self, on):
        self.calls.append(("set_pinned", on))

    def selection_changed(self):
        self.calls.append(("selection_changed",))
        if isinstance(self.selection, Exception):
            raise self.selection
        return self.selection

    def place(self):
        self.calls.append(("place",))

    def repaint_all(self):
        self.calls.append(("repaint_all",))

    def destroy(self):
        self.calls.append(("destroy",))


class Vars(Base):

    def test_mode_is_maya_s_unless_the_edge_was_chosen(self):
        self.assertEqual(sp.mode(), "maya")
        self.cmds.vars[sp.MODE_VAR] = "edge"
        self.assertEqual(sp.mode(), "edge")
        self.cmds.vars[sp.MODE_VAR] = "sideways"
        self.assertEqual(sp.mode(), "maya")

    def test_tab_is_channels_unless_attributes_was_left(self):
        self.assertEqual(sp.tab(), "channels")
        self.cmds.vars[sp.TAB_VAR] = "attributes"
        self.assertEqual(sp.tab(), "attributes")

    def test_pinned_by_default_then_as_pressed(self):
        self.assertTrue(sp.pinned())
        sp._remember_pinned(False)
        self.assertEqual(self.cmds.vars[sp.PIN_VAR], 0)
        self.assertFalse(sp.pinned())
        sp._remember_pinned(True)
        self.assertTrue(sp.pinned())

    def test_pinned_where_maya_cannot_be_asked(self):
        def boom():
            raise ImportError("no maya")
        self.set(sp, "_cmds", boom)
        self.assertTrue(sp.pinned())
        self.assertTrue(sp.on_select())

    def test_tab_width_and_share_remembered_with_their_types(self):
        sp._remember_tab("attributes")
        sp._remember_width(412.7)
        sp._remember_share("0.4")
        self.assertEqual(self.cmds.vars[sp.TAB_VAR], "attributes")
        self.assertEqual(self.cmds.vars[sp.WIDTH_VAR], 412)
        self.assertEqual(self.cmds.vars[sp.HEIGHT_VAR], 0.4)

    def test_the_hidden_list_replaces_the_last_one(self):
        self.cmds.vars[sp.HIDDEN_VAR] = ["Old"]
        sp._remember_hidden(["ChannelBoxLayerEditor", "AttributeEditor"])
        self.assertEqual(self.cmds.vars[sp.HIDDEN_VAR], ["ChannelBoxLayerEditor", "AttributeEditor"])
        sp._remember_hidden([])
        self.assertNotIn(sp.HIDDEN_VAR, self.cmds.vars)

    def test_holds_is_zero_on_a_broken_state(self):
        sys._skeldar_sidepanel = {"edge": None, "held": None}
        self.assertEqual(sp.holds("channels"), 0)

    def test_cmds_is_maya_s(self):
        import maya.cmds
        self.assertIs(self.real_cmds(), maya.cmds)

    def test_a_missing_state_is_made(self):
        del sys._skeldar_sidepanel
        self.assertEqual(sp._state(), {"edge": None, "held": {}})


class ShowHidden(Base):

    def setUp(self):
        super(ShowHidden, self).setUp()
        self.shown = self.record(holder, "_set_ws")

    def test_only_controls_that_still_exist_are_shown_and_the_list_forgotten(self):
        self.cmds.vars[sp.HIDDEN_VAR] = ["ChannelBoxLayerEditor", "Gone"]
        self.cmds.ws = {"ChannelBoxLayerEditor"}
        sp._show_hidden()
        self.assertEqual(self.shown, [("_set_ws", ("ChannelBoxLayerEditor", True), {})])
        self.assertNotIn(sp.HIDDEN_VAR, self.cmds.vars)

    def test_one_name_reads_as_a_string(self):
        self.cmds.vars[sp.HIDDEN_VAR] = "AttributeEditor"
        self.cmds.ws = {"AttributeEditor"}
        sp._show_hidden()
        self.assertEqual(self.shown, [("_set_ws", ("AttributeEditor", True), {})])

    def test_nothing_remembered_shows_nothing(self):
        sp._show_hidden()
        self.assertEqual(self.shown, [])


class FitLayers(Base):

    def test_the_rows_on_the_track_colour(self):
        calls = self.record(holder, "fit_layers")
        sp._fit_layers()
        h = maya_hubstyle.TOKENS["track"].lstrip("#")
        want = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
        self.assertEqual(calls, [("fit_layers", (), {"background": want})])


class MayaWants(Base):

    def setUp(self):
        super(MayaWants, self).setUp()
        self.visible = set()
        self.set(holder, "ws_visible", lambda name: name in self.visible)
        self.ws_set = self.record(holder, "_set_ws")
        self.fitted = self.record(sp, "_fit_layers")
        self.state()["held"] = {"channels": [{"ws": "ChannelBoxLayerEditor"}],
                                "attributes": [{"ws": None}, {"ws": "AttributeEditor"}]}

    def test_maya_showing_its_control_again_hides_it_and_brings_ours_out_on_that_tab(self):
        self.visible = {"AttributeEditor"}
        edge = FakeEdge()
        sp._maya_wants(edge)
        self.assertEqual(self.fitted, [("_fit_layers", (), {})])
        self.assertEqual(self.ws_set, [("_set_ws", ("AttributeEditor", False), {})])
        self.assertEqual(edge.calls, [("reveal", {"held": True, "tab": "attributes"})])
        self.assertEqual(self.cmds.vars[sp.TAB_VAR], "attributes")

    def test_nothing_shown_by_maya_changes_nothing(self):
        edge = FakeEdge(shown=False)
        sp._maya_wants(edge)
        self.assertEqual((self.fitted, self.ws_set, edge.calls), ([], [], []))
        self.assertNotIn(sp.TAB_VAR, self.cmds.vars)

    def test_the_layers_fitted_only_while_out_holding_the_channels(self):
        self.state()["held"] = {"attributes": [{"ws": "AttributeEditor"}]}
        sp._maya_wants(FakeEdge(shown=True))
        self.assertEqual(self.fitted, [])


class Borrow(Base):

    def setUp(self):
        super(Borrow, self).setUp()
        self.separate = False
        self.set(holder, "separate", lambda: self.separate)
        self.taken = []

        def take(component, form, layout):
            self.taken.append((component, form, layout))
            if form == "MainAttributeEditorLayout":
                return None                                 # not in this Maya
            return {"form": form, "ws": "ChannelBoxLayerEditor" if "Channels" in form else None}
        self.set(holder, "take", take)
        self.installed = self.record(holder, "install")
        self.mounted = self.record(sp, "_mount_box")

    def test_each_tab_s_forms_taken_into_its_page_and_the_hidden_controls_remembered(self):
        edge = FakeEdge()
        held = sp._borrow(edge)
        self.assertEqual(self.taken, [("Channel Box / Layer Editor", "MainChannelsLayersLayout", "Lc"),
                                      ("Attribute Editor", "MainAttributeEditorLayout", "La")])
        record = {"form": "MainChannelsLayersLayout", "ws": "ChannelBoxLayerEditor"}
        self.assertEqual(held, {"channels": [record], "attributes": []})
        self.assertEqual(self.state()["held"], held)
        self.assertEqual(self.cmds.vars[sp.HIDDEN_VAR], ["ChannelBoxLayerEditor"])
        self.assertEqual(len(self.installed), 1)
        self.assertEqual(self.mounted, [("_mount_box", (edge, [record]), {})])

    def test_separate_channel_box_and_layer_editor_both_taken(self):
        self.separate = True
        held = sp._borrow(FakeEdge())
        self.assertEqual([r["form"] for r in held["channels"]],
                         ["MainChannelBoxLayout", "MainLayerEditorLayout"])
        self.assertNotIn(sp.HIDDEN_VAR, self.cmds.vars)            # neither had a control


class MountBox(Base):

    def setUp(self):
        super(MountBox, self).setUp()
        import maya_channelbox
        self.cb = maya_channelbox
        self.on = True
        self.set(maya_channelbox, "enabled", lambda: self.on)
        self.calls = []
        self.record(maya_channelbox, "mount", calls=self.calls)
        self.record(maya_channelbox, "unmount", calls=self.calls)

    def test_ours_mounted_with_the_panel_s_scale(self):
        edge = FakeEdge()
        sp._mount_box(edge, [{"form": "F"}])
        self.assertEqual(self.calls, [("mount", (edge.panel, [{"form": "F"}], 1.5), {})])

    def test_a_panel_without_a_scale_mounts_at_one(self):
        panel_ = types.SimpleNamespace()
        sp._mount_box(types.SimpleNamespace(panel=panel_), [{"form": "F"}])
        self.assertEqual(self.calls[0][1][2], 1.0)

    def test_off_or_nothing_held_mounts_nothing(self):
        sp._mount_box(FakeEdge(), [])
        self.on = False
        sp._mount_box(FakeEdge(), [{"form": "F"}])
        self.assertEqual(self.calls, [])

    def test_a_mount_that_fails_takes_ours_away_again(self):
        self.set(self.cb, "mount", mock.Mock(side_effect=RuntimeError("no box")))
        sp._mount_box(FakeEdge(), [{"form": "F"}])
        self.assertEqual([c[0] for c in self.calls], ["unmount"])
        self.assertTrue(any("could not mount" in str(a) for a in self.printed))

    def test_an_unmount_that_fails_too_is_swallowed(self):
        self.set(self.cb, "mount", mock.Mock(side_effect=RuntimeError("no box")))
        self.set(self.cb, "unmount", mock.Mock(side_effect=RuntimeError("no page")))
        sp._mount_box(FakeEdge(), [{"form": "F"}])


class GiveBack(Base):

    def setUp(self):
        super(GiveBack, self).setUp()
        import maya_channelbox
        self.calls = []
        self.record(maya_channelbox, "unmount", calls=self.calls)
        self.widgets = {"F1": "w1", "F3": "w3"}
        self.set(holder, "widget", lambda name: self.widgets.get(name))
        self.record(skin, "recolor", calls=self.calls)

        def give(record):
            self.calls.append(("give", record["form"]))
            if record["form"] == "F3":
                raise RuntimeError("parent gone")
            return record["form"] == "F1"
        self.set(holder, "give", give)
        self.record(holder, "uninstall", calls=self.calls)
        self.record(skin, "channel_box", calls=self.calls)
        self.record(holder, "unfit_layers", calls=self.calls)
        self.state()["held"] = {"channels": [{"form": "F1"}],
                                "attributes": [{"form": "F2"}, {"form": "F3"}]}

    def test_ours_away_maya_s_colours_and_forms_back_then_maya_s_procs(self):
        self.assertEqual(sp.give_back(), 1)
        names = [c[0] for c in self.calls]
        self.assertEqual(names, ["unmount", "recolor", "recolor", "give", "give", "give",
                                 "uninstall", "channel_box", "unfit_layers"])
        recolored = [(c[1][0], c[2]) for c in self.calls if c[0] == "recolor"]
        self.assertEqual(recolored, [("w1", {"back": True}), ("w3", {"back": True})])
        self.assertEqual(self.calls[-2], ("channel_box", (False,), {}))
        self.assertEqual(self.state()["held"], {})
        self.assertTrue(any("parent gone" in str(a) for a in self.printed))

    def test_a_failing_unmount_and_recolour_still_give_the_forms_back(self):
        import maya_channelbox
        self.set(maya_channelbox, "unmount", mock.Mock(side_effect=RuntimeError("dead box")))
        self.set(skin, "recolor", mock.Mock(side_effect=RuntimeError("dead widget")))
        self.assertEqual(sp.give_back(), 1)
        self.assertTrue(any("dead box" in str(a) for a in self.printed))

    def test_nothing_held_gives_nothing(self):
        self.state()["held"] = None
        self.assertEqual(sp.give_back(), 0)


class Rebuild(Base):

    def setUp(self):
        super(Rebuild, self).setUp()
        self.calls = []
        self.record(sp, "drop_edge", calls=self.calls)
        self.built = object()
        self.record(sp, "ensure_edge", answer=lambda: self.built, calls=self.calls)

    def test_rebuild_drops_then_builds(self):
        self.assertIs(sp.rebuild(), self.built)
        self.assertEqual([c[0] for c in self.calls], ["drop_edge", "ensure_edge"])

    def test_reload_live_only_in_the_edge_mode_with_a_ui(self):
        self.cmds.batch = True
        self.assertFalse(sp.reload_live())
        self.cmds.batch = False
        self.assertFalse(sp.reload_live())                    # Maya's mode
        self.assertEqual(self.calls, [])
        self.cmds.vars[sp.MODE_VAR] = "edge"
        self.assertTrue(sp.reload_live())
        self.built = None
        self.assertFalse(sp.reload_live())


class EnsureEdge(Base):

    def setUp(self):
        super(EnsureEdge, self).setUp()
        self.made = []
        test = self

        class SideEdge(FakeEdge):
            def __init__(self, make, **kw):
                FakeEdge.__init__(self)
                self.make = make
                self.kw = kw
                test.made.append(self)
        self.set(edge_module, "SideEdge", SideEdge)
        self.calls = []
        self.record(edge_module, "destroy_all", calls=self.calls)
        for name in ("_borrow", "_fit", "_start_job", "drop_edge", "_show_hidden"):
            self.record(sp, name, calls=self.calls)
        self.record(sp, "_skin", calls=self.calls)

    def test_batch_builds_nothing(self):
        self.cmds.batch = True
        self.assertIsNone(sp.ensure_edge())
        self.assertEqual(self.made, [])

    def test_a_standing_edge_is_the_answer(self):
        standing = FakeEdge()
        self.state()["edge"] = standing
        self.assertIs(sp.ensure_edge(), standing)
        self.assertEqual(self.calls, [])

    def test_built_with_the_remembered_width_share_and_tab_then_pinned_out(self):
        self.cmds.vars.update({sp.WIDTH_VAR: 400, sp.HEIGHT_VAR: 0.7, sp.TAB_VAR: "attributes"})
        self.state()["edge"] = FakeEdge(alive=False)           # a dead one is dropped first
        controller = sp.ensure_edge()
        self.assertIs(controller, self.made[0])
        self.assertIs(self.state()["edge"], controller)
        kw = controller.kw
        self.assertEqual((kw["width"], kw["scale"], kw["share"]), (400, 1.5, 0.7))
        self.assertIs(kw["on_width"], sp._remember_width)
        self.assertIs(kw["on_height"], sp._remember_share)
        self.assertIs(kw["on_pinned"], sp._remember_pinned)
        self.assertIs(kw["tick"], sp._maya_wants)
        self.assertIs(kw["selected"], sp._has_selection)
        self.assertIs(kw["on_reveal"], sp.refresh)
        names = [c[0] for c in self.calls]
        self.assertEqual(names, ["drop_edge", "destroy_all", "_borrow", "_skin", "_fit", "_start_job"])
        self.assertEqual(self.calls[3][1], (controller, 1.5))
        self.assertEqual(controller.calls, [("set_tab", "attributes"), ("set_pinned", True),
                                            ("reveal", {"instant": True}), ("selection_changed",)])

    def test_defaults_and_unpinned(self):
        self.cmds.vars[sp.PIN_VAR] = 0
        self.cmds.dpi = None
        controller = sp.ensure_edge()
        self.assertEqual((controller.kw["width"], controller.kw["share"], controller.kw["scale"]),
                         (look.WIDTH, look.SHARE, 1.0))
        self.assertEqual(controller.calls, [("set_tab", "channels"), ("selection_changed",)])

    def test_the_panel_made_with_the_hub_s_tokens_and_a_tab_press_remembered(self):
        made = self.record(panel, "make", answer="the panel")
        refreshed = self.record(sp, "refresh")
        controller = sp.ensure_edge()
        self.assertEqual(controller.make("parent", "on_tab", "on_pin", "on_width"), "the panel")
        args, kw = made[0][1], made[0][2]
        self.assertEqual(args, ("parent", 1.5, maya_hubstyle.TOKENS))
        self.assertEqual((kw["on_tab"], kw["on_pin"], kw["on_width"]), ("on_tab", "on_pin", "on_width"))
        self.assertIn("motion", kw)
        controller.kw["on_tab"]("attributes")
        self.assertEqual(self.cmds.vars[sp.TAB_VAR], "attributes")
        self.assertEqual(len(refreshed), 1)

    def test_a_borrow_that_fails_gives_maya_s_editors_back(self):
        self.record(sp, "_borrow", answer=RuntimeError("no forms"), calls=self.calls)
        self.assertIsNone(sp.ensure_edge())
        names = [c[0] for c in self.calls]
        self.assertEqual(names[-2:], ["drop_edge", "_show_hidden"])
        self.assertTrue(any("could not take" in str(a) for a in self.printed))


class SkinAndFit(Base):

    def test_skin_applies_the_sheet_and_the_box_colours(self):
        calls = self.record(skin, "apply")
        self.record(skin, "channel_box", calls=calls)
        edge = FakeEdge()
        sp._skin(edge, 2.0)
        self.assertEqual(calls[0][1][0], edge.panel.stack)
        self.assertEqual(calls[0][1][2], 2.0)
        self.assertEqual(calls[1], ("channel_box", (True,), {}))

    def test_a_skin_that_fails_is_never_fatal(self):
        self.set(skin, "apply", mock.Mock(side_effect=RuntimeError("bad sheet")))
        sp._skin(FakeEdge(), 1.0)
        self.assertTrue(any("bad sheet" in str(a) for a in self.printed))

    def test_recolor_the_page_on_show_else_the_stack(self):
        calls = self.record(skin, "recolor")
        edge = FakeEdge()
        sp._recolor(edge)
        self.assertIs(calls[0][1][0], edge.panel.stack)
        edge.panel.stack = types.SimpleNamespace(currentWidget=lambda: "page")
        sp._recolor(edge)
        self.assertEqual(calls[1][1][0], "page")
        self.set(skin, "recolor", mock.Mock(side_effect=RuntimeError("dead")))
        sp._recolor(edge)                                       # swallowed

    def hint(self, width):
        return types.SimpleNamespace(minimumSizeHint=lambda: types.SimpleNamespace(width=lambda: width))

    def test_fit_holds_the_panel_at_least_as_wide_as_the_shown_tab_s_forms(self):
        self.set(holder, "widget", lambda name: {"AE": self.hint(600), "X": self.hint(300)}.get(name))
        self.state()["held"] = {"attributes": [{"form": "AE"}, {"form": "X"}, {"form": "gone"}]}
        edge = FakeEdge(tab="attributes")
        sp._fit(edge)
        self.assertEqual(edge.least, look.min_width_px([600, 300], 1.5))
        self.assertEqual(edge.calls, [("place",)])
        sp._fit(edge)                                           # the same: not placed again
        self.assertEqual(edge.calls, [("place",)])

    def test_fit_asks_nothing_for_our_channel_box(self):
        import maya_channelbox
        self.set(maya_channelbox, "current", lambda: object())
        self.set(holder, "widget", lambda name: self.hint(700))
        self.state()["held"] = {"channels": [{"form": "CB"}]}
        edge = FakeEdge(tab="channels")
        edge.least = 300
        sp._fit(edge)
        self.assertEqual((edge.least, edge.calls), (0, [("place",)]))

    def test_fit_reads_maya_s_channel_box_when_ours_is_not_there(self):
        import maya_channelbox
        self.set(maya_channelbox, "current", mock.Mock(side_effect=RuntimeError("no box")))
        self.set(holder, "widget", lambda name: self.hint(250))
        self.state()["held"] = {"channels": [{"form": "CB"}]}
        edge = FakeEdge(tab="channels")
        sp._fit(edge)
        self.assertEqual(edge.least, look.min_width_px([250], 1.5))


class Refresh(Base):

    def setUp(self):
        super(Refresh, self).setUp()
        import maya_channelbox
        self.calls = []
        self.record(holder, "refresh_attribute_editor", calls=self.calls)
        self.record(holder, "update_channel_box", calls=self.calls)
        self.record(maya_channelbox, "refresh", calls=self.calls)
        self.record(sp, "_fit", calls=self.calls)
        self.record(sp, "_recolor", calls=self.calls)

    def test_nothing_while_in_or_gone(self):
        sp.refresh()
        self.state()["edge"] = FakeEdge(shown=False)
        sp.refresh()
        self.state()["edge"] = FakeEdge(alive=False)
        sp.refresh()
        self.assertEqual(self.calls, [])

    def test_the_attributes_tab_asks_the_attribute_editor(self):
        edge = FakeEdge(tab="attributes")
        self.state()["edge"] = edge
        sp.refresh()
        self.assertEqual([c[0] for c in self.calls], ["refresh_attribute_editor", "_fit", "_recolor"])
        self.assertEqual(edge.calls, [("repaint_all",)])

    def test_the_channels_tab_asks_both_channel_boxes(self):
        self.state()["edge"] = FakeEdge(tab="channels")
        sp.refresh()
        self.assertEqual([c[0] for c in self.calls], ["update_channel_box", "refresh", "_fit", "_recolor"])

    def test_our_box_failing_is_passed_by(self):
        import maya_channelbox
        self.set(maya_channelbox, "refresh", mock.Mock(side_effect=RuntimeError("dead box")))
        self.state()["edge"] = FakeEdge(tab="channels")
        sp.refresh()
        self.assertEqual([c[0] for c in self.calls], ["update_channel_box", "_fit", "_recolor"])


class FakeOldOpenMaya(object):
    """maya.OpenMaya (API 1): an event callback added, a callback removed."""

    def __init__(self):
        self.added = []
        self.removed = []
        self.refuse = False
        fake = self

        class MEventMessage(object):
            @staticmethod
            def addEventCallback(event, fn):
                if fake.refuse:
                    raise RuntimeError("no callbacks")
                fake.added.append((event, fn))
                return 42

        class MMessage(object):
            @staticmethod
            def removeCallback(cid):
                if cid == "bad":
                    raise RuntimeError("bad id")
                fake.removed.append(cid)

        self.om = types.ModuleType("maya.OpenMaya")
        self.om.MEventMessage = MEventMessage
        self.om.MMessage = MMessage


class Jobs(Base):

    def setUp(self):
        super(Jobs, self).setUp()
        import maya
        self.fake = FakeOldOpenMaya()
        self.set(maya, "OpenMaya", self.fake.om, create=True)
        patcher = ModuleSwap("maya.OpenMaya", self.fake.om)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.selections = self.record(sp, "_on_selection")

    def test_an_openmaya_callback_that_hears_every_selection(self):
        self.state()["callback"] = 7
        sp._start_job()
        self.assertEqual(self.fake.removed, [7])                # the old one first
        self.assertEqual(self.state()["callback"], 42)
        event, fn = self.fake.added[0]
        self.assertEqual(event, "SelectionChanged")
        fn("client data")
        self.assertEqual(len(self.selections), 1)

    def test_a_scriptjob_when_openmaya_refuses(self):
        self.fake.refuse = True
        sp._start_job()
        self.assertIsNone(self.state()["callback"])
        self.assertEqual(self.state()["job"], 501)
        self.assertEqual(self.cmds.event, (["SelectionChanged", sp._on_selection], False))

    def test_neither_leaves_no_job(self):
        self.fake.refuse = True
        self.cmds.fail.add("scriptJob")
        sp._start_job()
        self.assertIsNone(self.state()["job"])

    def test_kill_job_takes_off_the_callback_and_a_live_job(self):
        self.state().update(callback="bad", job=9)
        self.cmds.jobs[9] = True
        sp._kill_job()
        self.assertEqual(self.cmds.killed, [(9, True)])
        self.assertNotIn("callback", self.state())
        self.assertNotIn("job", self.state())
        self.state().update(callback=3, job=10)                 # a job already gone
        sp._kill_job()
        self.assertEqual(self.fake.removed, [3])
        self.assertEqual(self.cmds.killed, [(9, True)])

    def test_kill_job_swallows_a_maya_that_cannot_ask(self):
        self.state()["job"] = 11
        self.cmds.fail.add("scriptJob")
        sp._kill_job()


class Selection(Base):

    def setUp(self):
        super(Selection, self).setUp()
        self.refreshed = self.record(sp, "refresh")

    def test_playing(self):
        self.assertFalse(sp.playing())
        self.cmds.playing = 1
        self.assertTrue(sp.playing())
        self.cmds.fail.add("play")
        self.assertFalse(sp.playing())

    def test_after_maya_s_own_handlers_when_idle(self):
        edge = FakeEdge(selection=False)
        self.state()["edge"] = edge
        sp._on_selection()
        self.assertEqual(self.refreshed, [])
        fn, lowest = self.cmds.deferred[0]
        self.assertTrue(lowest)
        fn()
        self.assertEqual(edge.calls, [("selection_changed",)])
        self.assertEqual(len(self.refreshed), 1)               # not brought out: refreshed

    def test_brought_out_by_the_selection_the_reveal_refreshed_it(self):
        self.state()["edge"] = FakeEdge(selection=True)
        self.cmds.playing = True
        sp._on_selection()                                      # playback: at once
        self.assertEqual(self.cmds.deferred, [])
        self.assertEqual(self.refreshed, [])

    def test_no_edge_just_refreshes(self):
        self.cmds.fail.add("evalDeferred")
        sp._on_selection()                                      # no idle queue: at once
        self.assertEqual(len(self.refreshed), 1)

    def test_a_failure_inside_is_printed(self):
        self.state()["edge"] = FakeEdge(selection=RuntimeError("dead edge"))
        self.cmds.playing = True
        sp._on_selection()
        self.assertTrue(any("dead edge" in str(a) for a in self.printed))


class DropEdge(Base):

    def setUp(self):
        super(DropEdge, self).setUp()
        self.calls = []
        self.record(sp, "_kill_job", calls=self.calls)
        self.record(sp, "give_back", calls=self.calls)

    def test_the_forms_back_before_the_windows_go(self):
        edge = FakeEdge()
        edge.destroy = lambda: self.calls.append(("destroy",))
        self.state()["edge"] = edge
        sp.drop_edge()
        self.assertEqual([c[0] for c in self.calls], ["_kill_job", "give_back", "destroy"])
        self.assertNotIn("edge", self.state())

    def test_a_destroy_that_fails_and_no_edge_are_fine(self):
        edge = FakeEdge()
        edge.destroy = mock.Mock(side_effect=RuntimeError("gone"))
        self.state()["edge"] = edge
        sp.drop_edge()
        sp.drop_edge()
        self.assertEqual([c[0] for c in self.calls], ["_kill_job", "give_back"] * 2)


class Modes(Base):

    def setUp(self):
        super(Modes, self).setUp()
        self.calls = []
        self.built = FakeEdge()
        self.record(sp, "ensure_edge", answer=lambda: self.built, calls=self.calls)
        self.record(sp, "drop_edge", calls=self.calls)
        self.record(sp, "_show_hidden", calls=self.calls)

    def test_the_edge_chosen_and_built(self):
        self.assertEqual(sp.set_mode("edge"), sp.MESSAGES["edge"])
        self.assertEqual(self.cmds.vars[sp.MODE_VAR], "edge")
        self.assertEqual([c[0] for c in self.calls], ["ensure_edge"])

    def test_an_edge_that_cannot_be_built_leaves_maya_s(self):
        self.built = None
        message = sp.set_mode("edge")
        self.assertIn("could not be built", message)
        self.assertEqual(self.cmds.vars[sp.MODE_VAR], "maya")

    def test_maya_s_gives_everything_back(self):
        self.assertEqual(sp.set_mode("nonsense"), sp.MESSAGES["maya"])
        self.assertEqual(self.cmds.vars[sp.MODE_VAR], "maya")
        self.assertEqual([c[0] for c in self.calls], ["drop_edge", "_show_hidden"])

    def test_ensure_stands_the_chosen_mode(self):
        self.assertIsNone(sp.ensure())
        self.assertEqual([c[0] for c in self.calls], ["_show_hidden"])
        self.cmds.vars[sp.MODE_VAR] = "edge"
        self.assertIs(sp.ensure(), self.built)

    def test_toggle_switches_the_other_way(self):
        chosen = self.record(sp, "set_mode", answer="said")
        self.assertEqual(sp.toggle(), "said")
        self.cmds.vars[sp.MODE_VAR] = "edge"
        sp.toggle()
        self.assertEqual([c[1][0] for c in chosen], ["edge", "maya"])


class ShowTab(Base):

    def test_out_on_the_tab_held(self):
        edge = FakeEdge()
        self.state()["edge"] = edge
        self.assertEqual(sp.show_tab("attributes"), "Side panel: Attributes")
        self.assertEqual(self.cmds.vars[sp.TAB_VAR], "attributes")
        self.assertEqual(edge.calls, [("reveal", {"held": True, "tab": "attributes"})])

    def test_an_unknown_tab_is_the_channels(self):
        self.state()["edge"] = FakeEdge()
        self.assertEqual(sp.show_tab("layers"), "Side panel: Channels")

    def test_the_panel_switched_on_first(self):
        edge = FakeEdge()
        chosen = self.record(sp, "set_mode", answer=lambda c: self.state().__setitem__("edge", edge))
        self.state()["edge"] = FakeEdge(alive=False)
        sp.show_tab("channels")
        self.assertEqual(chosen[0][1], ("edge",))
        self.assertEqual(edge.calls, [("reveal", {"held": True, "tab": "channels"})])

    def test_not_available_when_it_cannot_be_built(self):
        self.record(sp, "set_mode")
        self.assertEqual(sp.show_tab("channels"), "The side panel is not available")


class OnSelect(Base):

    def test_switched_on_a_standing_panel_looks_at_the_selection(self):
        edge = FakeEdge()
        self.state()["edge"] = edge
        self.assertIn("comes out", sp.set_on_select(True))
        self.assertEqual(edge.calls, [("selection_changed",)])
        sp.set_on_select(False)
        self.assertEqual(edge.calls, [("selection_changed",)])

    def test_a_panel_that_fails_is_printed(self):
        self.state()["edge"] = FakeEdge(selection=RuntimeError("dead edge"))
        sp.set_on_select(True)
        self.assertTrue(any("dead edge" in str(a) for a in self.printed))

    def test_a_selection_maya_cannot_list_is_none(self):
        def ls(**kw):
            raise RuntimeError("no scene")
        self.cmds.ls = ls
        self.assertFalse(sp._has_selection())


if __name__ == "__main__":
    unittest.main()
