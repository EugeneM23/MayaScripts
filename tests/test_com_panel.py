"""The Center of Mass card's presses, on a fake cmds (no Maya).

test_com_scene.py proves the character line; this proves what each button
and chip does to the scene and says on the status line: Add, Remove and
Rebuild (the settings kept, one undo chunk each), Select CoM, the chips and
the range writing the group, and the card's own refresh job."""

import sys
import types
import unittest
from unittest import mock

import maya_hubcopy as hubcopy
import maya_hubstyle as hubstyle
from maya_com import drag, engine, network, panel

_MISSING = object()


def swap_module(test, name, module):
    """sys.modules[name] is `module` until the test ends (only that key)."""
    old = sys.modules.get(name, _MISSING)
    test.addCleanup(lambda: sys.modules.pop(name, None) if old is _MISSING
                    else sys.modules.__setitem__(name, old))
    sys.modules[name] = module

CHAR = network.Character("|r|root", "a rig", "Manny_Rig", "Manny_Rig")
GROUP = "|Manny_Rig_Character|Manny_Rig:CenterOfMass"
NEW = "|Manny_Rig_Character|Manny_Rig:CenterOfMass1"


class PanelCmds(object):
    """The commands the card calls; every UI creation is recorded."""

    def __init__(self):
        self.labels = {}                     # existing text control -> label
        self.values = {panel.TRAIL: True, panel.FLOOR: False, panel.AROUND: 20}
        self.attrs = {}
        self.sets = []
        self.chunks = []
        self.selected = []
        self.uuids = {GROUP: "UU-OLD", NEW: "UU-NEW"}
        self.jobs = {}
        self.killed = []
        self.next_job = 700
        self.made = []                       # (command, args, kwargs)
        self.edits = []

    # the card's controls
    def text(self, name=None, exists=False, edit=False, label=None, **kw):
        if exists:
            return name in self.labels
        if edit:
            self.labels[name] = label
            return name
        self.made.append(("text", name, dict(kw, label=label)))
        if name:
            self.labels[name] = label
        return name

    def checkBox(self, name, query=False, value=None, edit=False, **kw):
        if query:
            return self.values[name]
        if edit:
            self.edits.append(("checkBox", name, value))
            return name
        self.made.append(("checkBox", name, dict(kw, value=value)))
        return name

    def intField(self, name, query=False, value=None, edit=False, **kw):
        if query:
            return self.values[name]
        if edit:
            self.edits.append(("intField", name, value))
            return name
        self.made.append(("intField", name, dict(kw, value=value)))
        return name

    def iconTextRadioButton(self, name, exists=False, edit=False, select=None, **kw):
        if exists:
            return True
        if edit:
            self.edits.append(("segment", name, select))
            return name
        self.made.append(("segment", name, dict(kw, select=select)))
        return name

    def button(self, **kw):
        self.made.append(("button", kw.get("label"), kw))
        return "button%d" % len(self.made)

    def __getattr__(self, command):            # layouts and the rest
        def call(*args, **kw):
            self.made.append((command, args, kw))
            return "%s%d" % (command, len(self.made))
        return call

    # the scene
    def getAttr(self, plug):
        return self.attrs[plug]

    def setAttr(self, plug, value):
        self.attrs[plug] = value
        self.sets.append((plug, value))

    def ls(self, name, uuid=False):
        return [self.uuids[name]] if name in self.uuids else []

    def undoInfo(self, openChunk=False, closeChunk=False, chunkName=None):
        self.chunks.append(("open", chunkName) if openChunk else ("close", None))

    def refresh(self):
        pass

    def select(self, node, replace=False):
        self.selected.append((node, replace))

    def scriptJob(self, event=None, parent=None, exists=None, kill=None, force=False):
        if exists is not None:
            return exists in self.jobs
        if kill is not None:
            self.jobs.pop(kill, None)
            self.killed.append(kill)
            return None
        self.next_job += 1
        self.jobs[self.next_job] = (event[0], event[1], parent)
        return self.next_job


class Model(object):
    volume = 83300.0                         # cm³
    masses = dict(("j%d" % i, 1.0) for i in range(74))


class PanelCase(unittest.TestCase):

    def setUp(self):
        self.cmds = PanelCmds()
        self.cmds.labels[panel.STATUS] = ""
        self.patch(panel, "cmds", self.cmds)
        self.groups = {"group": GROUP}
        self.character = [(CHAR, "")]
        self.calls = []
        self.patch(network, "character", lambda: self.character[0])
        self.patch(network, "group_for", lambda char: self.groups["group"])
        self.patch(network, "build_model",
                   lambda char: (Model(), {"seconds": 1.24}))
        self.patch(network, "create", self._create)
        self.patch(network, "remove", self._remove)
        self.patch(network, "part", lambda group, name: group + "|COM_" + name)
        self.patch(network, "mass_joints", lambda group: ["|j"] * 74)
        self.patch(engine, "track", lambda group: self.calls.append(("track", group)))
        self.patch(engine, "untrack", lambda uuid: self.calls.append(("untrack", uuid)))
        self.patch(hubstyle, "tell", lambda control, text, viewport=False: text)

    def patch(self, target, name, value):
        p = mock.patch.object(target, name, value)
        p.start()
        self.addCleanup(p.stop)

    def _create(self, char, model, info):
        self.calls.append(("create", char.label, self.cmds.chunks[-1][0]))
        for attr, value in (("trail", 1), ("floor", 1), ("range", 0), ("around", 20)):
            self.cmds.attrs[NEW + "." + attr] = value
        return NEW

    def _remove(self, group):
        self.calls.append(("remove", group, self.cmds.chunks[-1][0]))

    def status(self):
        return self.cmds.labels[panel.STATUS]


class Presses(PanelCase):

    def test_run_answers_the_action_or_says_it_failed(self):
        self.assertEqual(panel._run(lambda: "fine"), "fine")

        def boom():
            raise RuntimeError("no skin")
        with mock.patch("builtins.print") as printed:
            text = panel._run(boom)
        self.assertEqual(text, "Center of Mass failed: no skin")
        self.assertEqual(self.status(), text)
        self.assertIn("RuntimeError: no skin", printed.call_args[0][0])

    def test_with_no_character_every_press_says_the_refusal(self):
        self.character[0] = (None, network.NO_CHARACTER)
        for press in (panel.add, panel.remove, panel.rebuild, panel.select_com):
            self.assertEqual(press(), network.NO_CHARACTER)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.cmds.chunks, [])

    def test_add_weighs_the_body_in_one_undo_chunk_and_tracks_it(self):
        self.groups["group"] = None
        text = panel.add()
        self.assertEqual(text, "Manny_Rig: CoM added - 83 L over 74 bones, "
                               "weighed in 1.2 s")
        self.assertEqual(self.cmds.chunks, [("open", "skeldarComAdd"), ("close", None)])
        self.assertEqual(self.calls, [("create", "Manny_Rig", "open"),
                                      ("track", NEW)])

    def test_add_on_a_character_that_has_one_changes_nothing(self):
        text = panel.add()
        self.assertEqual(text, "Manny_Rig already has a CoM - Rebuild weighs it again")
        self.assertEqual(self.calls, [])

    def test_a_create_that_fails_still_closes_the_chunk(self):
        self.groups["group"] = None
        self.patch(network, "create", mock.Mock(side_effect=RuntimeError("locked")))
        with mock.patch("builtins.print"):
            text = panel._run(panel.add)
        self.assertEqual(text, "Center of Mass failed: locked")
        self.assertEqual(self.cmds.chunks, [("open", "skeldarComAdd"), ("close", None)])

    def test_remove_stops_the_trail_then_deletes_in_one_chunk(self):
        self.assertEqual(panel.remove(), "Manny_Rig: CoM removed")
        self.assertEqual(self.calls, [("untrack", "UU-OLD"), ("remove", GROUP, "open")])
        self.assertEqual(self.cmds.chunks, [("open", "skeldarComRemove"), ("close", None)])

    def test_remove_with_no_com_says_so(self):
        self.groups["group"] = None
        self.assertEqual(panel.remove(), "Manny_Rig has no CoM")
        self.assertEqual(self.calls, [])

    def test_rebuild_weighs_again_and_keeps_the_settings(self):
        self.cmds.attrs.update({GROUP + ".trail": 0, GROUP + ".floor": 1,
                                GROUP + ".range": 1, GROUP + ".around": 35})
        text = panel.rebuild()
        self.assertEqual(text, "Manny_Rig: CoM weighed again - 83 L over 74 bones")
        self.assertEqual(self.calls, [("untrack", "UU-OLD"),
                                      ("remove", GROUP, "open"),
                                      ("create", "Manny_Rig", "open"),
                                      ("track", NEW)])
        self.assertEqual({a: self.cmds.attrs[NEW + "." + a]
                          for a in ("trail", "floor", "range", "around")},
                         {"trail": 0, "floor": 1, "range": 1, "around": 35})
        self.assertEqual(self.cmds.chunks, [("open", "skeldarComRebuild"), ("close", None)])

    def test_rebuild_with_no_com_adds_one(self):
        self.groups["group"] = None
        self.assertTrue(panel.rebuild().startswith("Manny_Rig: CoM added"))

    def test_select_com_selects_the_handle_and_says_how_to_drag(self):
        text = panel.select_com()
        self.assertEqual(self.cmds.selected, [(GROUP + "|COM_handle", True)])
        self.assertEqual(text, "Manny_Rig: drag the CoM - Shift on the floor, "
                               "Ctrl up and down")

    def test_select_com_with_no_com_asks_for_one(self):
        self.groups["group"] = None
        self.assertEqual(panel.select_com(), "Manny_Rig has no CoM - Add CoM first")
        self.assertEqual(self.cmds.selected, [])

    def test_the_status_reaches_the_hub_s_message_line(self):
        told = []
        self.patch(hubstyle, "tell", lambda control, text, viewport=False:
                   told.append((control, text, viewport)))
        panel.status("hello")
        self.assertEqual(told, [(panel.STATUS, "hello", False)])
        del self.cmds.labels[panel.STATUS]                    # the card is closed
        self.assertEqual(panel.status("unheard"), "unheard")
        self.assertEqual(len(told), 1)


class Settings(PanelCase):

    def test_the_trail_chip_writes_the_group_and_follows(self):
        self.cmds.values[panel.TRAIL] = False
        panel._trail_changed()
        self.assertEqual(self.cmds.sets, [(GROUP + ".trail", 0)])
        self.assertEqual(self.calls, [("track", GROUP)])

    def test_the_floor_chip(self):
        self.cmds.values[panel.FLOOR] = True
        panel._floor_changed(True)
        self.assertEqual(self.cmds.sets, [(GROUP + ".floor", 1)])

    def test_each_range_segment_sets_its_own_mode(self):
        panel._range_changed(1)()
        panel._range_changed(0)("on")
        self.assertEqual(self.cmds.sets, [(GROUP + ".range", 1), (GROUP + ".range", 0)])

    def test_around_is_at_least_one_frame(self):
        self.cmds.values[panel.AROUND] = 0
        panel._around_changed()
        self.cmds.values[panel.AROUND] = 35
        panel._around_changed()
        self.assertEqual(self.cmds.sets, [(GROUP + ".around", 1), (GROUP + ".around", 35)])

    def test_with_no_com_a_chip_writes_nothing(self):
        self.groups["group"] = None
        panel._trail_changed()
        self.assertEqual((self.cmds.sets, self.calls), ([], []))

    def test_refresh_shows_the_character_and_its_settings(self):
        self.cmds.labels[panel.SUBTITLE] = ""
        self.cmds.attrs.update({GROUP + ".volume": 83.3, GROUP + ".trail": 0,
                                GROUP + ".floor": 1, GROUP + ".range": 1,
                                GROUP + ".around": 12})
        panel.refresh()
        self.assertEqual(self.cmds.labels[panel.SUBTITLE], "Manny_Rig - 83 L over 74 bones")
        self.assertIn(("checkBox", panel.TRAIL, False), self.cmds.edits)
        self.assertIn(("checkBox", panel.FLOOR, True), self.cmds.edits)
        self.assertIn(("segment", panel.RANGE_SEG[1], True), self.cmds.edits)
        self.assertIn(("intField", panel.AROUND, 12), self.cmds.edits)

    def test_refresh_that_cannot_read_the_character_leaves_the_card(self):
        self.cmds.labels[panel.SUBTITLE] = "as it was"
        self.patch(network, "character", mock.Mock(side_effect=RuntimeError("tab closed")))
        panel.refresh()
        self.assertEqual(self.cmds.labels[panel.SUBTITLE], "as it was")

    def test_refresh_with_no_character_shows_the_refusal(self):
        self.cmds.labels[panel.SUBTITLE] = ""
        self.character[0] = (None, network.NO_CHARACTER)
        panel.refresh()
        self.assertEqual(self.cmds.labels[panel.SUBTITLE], network.NO_CHARACTER)


class Build(PanelCase):
    """The built card's controls run the presses."""

    def setUp(self):
        super(Build, self).setUp()
        self.patch(panel, "start", lambda: None)
        self.patch(panel, "refresh", lambda *_: None)
        self.patch(hubstyle, "_SKINNING", [False])           # the classic card's words
        self.addCleanup(hubstyle.take_marks)
        pressed = self.pressed = []
        for name in ("add", "rebuild", "remove", "select_com"):
            self.patch(panel, name, lambda n=name: pressed.append(n) or n)
        panel.build_panel()

    def made(self, command):
        return [m for m in self.cmds.made if m[0] == command]

    def test_the_four_buttons_press_add_rebuild_remove_and_select(self):
        buttons = self.made("button")
        self.assertEqual([b[1] for b in buttons],
                         ["Add CoM", "Rebuild", "Remove", "Select CoM"])
        for _command, _label, kw in buttons:
            kw["command"]()
        self.assertEqual(self.pressed, ["add", "rebuild", "remove", "select_com"])

    def test_the_chips_and_the_frames_field_carry_their_callbacks(self):
        chips = {name: kw for _c, name, kw in self.made("checkBox")}
        self.assertIs(chips[panel.TRAIL]["changeCommand"], panel._trail_changed)
        self.assertIs(chips[panel.FLOOR]["changeCommand"], panel._floor_changed)
        field = self.made("intField")[0]
        self.assertIs(field[2]["changeCommand"], panel._around_changed)

    def test_the_range_segments_set_playback_and_around(self):
        segments = self.made("segment")
        self.assertEqual([s[1] for s in segments], list(panel.RANGE_SEG))
        self.assertEqual([s[2]["select"] for s in segments], [True, False])
        segments[1][2]["onCommand"]()
        segments[0][2]["onCommand"](True)
        self.assertEqual(self.cmds.sets, [(GROUP + ".range", 1), (GROUP + ".range", 0)])

    def test_the_classic_card_names_the_frames_field(self):
        texts = [kw["label"] for _c, _n, kw in self.made("text")]
        self.assertIn("frames", texts)


class SeenOnly(object):
    def __init__(self):
        self.asked = []

    def seen_only(self, name, fn):
        self.asked.append((name, fn))
        return ("seen", name, fn)


class Start(PanelCase):

    def setUp(self):
        super(Start, self).setUp()
        self.order = []
        self.patch(engine, "start", lambda: self.order.append("engine"))
        self.patch(drag, "start", lambda: self.order.append("drag"))
        self.hubqt = SeenOnly()
        module = types.ModuleType("maya_hubqt")
        module.seen_only = self.hubqt.seen_only
        swap_module(self, "maya_hubqt", module)
        self.patch(panel, "JOB", {})
        self.live = []
        self.patch(hubcopy, "live", lambda: list(self.live))

    def test_start_runs_the_engine_and_the_tool_then_hangs_the_refresh(self):
        panel.start()
        self.assertEqual(self.order, ["engine", "drag"])
        (job, (event, fn, parent)), = self.cmds.jobs.items()
        self.assertEqual((event, parent), ("SelectionChanged", panel.STATUS))
        self.assertEqual(fn, ("seen", panel.STATUS, panel.refresh))
        self.assertEqual(panel.JOB, {"": job})

    def test_a_second_start_of_the_same_card_replaces_its_job(self):
        panel.start()
        first = panel.JOB[""]
        panel.start()
        self.assertEqual(self.cmds.killed, [first])
        self.assertEqual(list(panel.JOB), [""])
        self.assertNotEqual(panel.JOB[""], first)

    def test_a_popup_copy_keeps_its_own_job_beside_the_hub_s(self):
        panel.start()
        copy = hubcopy.Scope("hubcopy9")
        self.live.append(copy)
        with hubcopy.entered(copy):
            self.assertEqual(panel._card_key(), "hubcopy9")
            panel.start()
        self.assertEqual(sorted(panel.JOB), ["", "hubcopy9"])
        self.assertEqual(self.cmds.killed, [])

    def test_an_old_job_maya_cannot_kill_does_not_stop_the_start(self):
        panel.JOB[""] = 4242
        self.cmds.jobs[4242] = None
        self.cmds.scriptJob = mock.Mock(side_effect=[True, RuntimeError("busy"), 801])
        panel.start()
        self.assertEqual(panel.JOB, {"": 801})

    def test_a_closed_copy_s_entry_is_forgotten(self):
        panel.JOB["hubcopyGone"] = 9999
        panel.start()
        self.assertNotIn("hubcopyGone", panel.JOB)

    def test_a_failing_engine_still_hangs_the_card_s_refresh(self):
        self.patch(engine, "start", mock.Mock(side_effect=RuntimeError("no API")))
        with mock.patch("builtins.print") as printed:
            panel.start()
        self.assertIn("RuntimeError: no API", printed.call_args[0][0])
        self.assertEqual(len(self.cmds.jobs), 1)

    def test_the_hub_s_card_key_is_empty(self):
        self.assertEqual(panel._card_key(), "")


class Opening(PanelCase):

    def test_is_open_while_the_status_line_stands(self):
        self.assertTrue(panel.is_open())
        del self.cmds.labels[panel.STATUS]
        self.assertFalse(panel.is_open())

    def test_show_window_opens_the_hub_on_this_section(self):
        hub = types.ModuleType("maya_hub")
        hub.show = mock.Mock(return_value="shown")
        swap_module(self, "maya_hub", hub)
        self.assertEqual(panel.show_window(), "shown")
        hub.show.assert_called_once_with("com")


if __name__ == "__main__":
    unittest.main()
