"""maya_ragdoll.panel - the Ragdoll card beyond its subtitle (tests/test_ragdoll_panel.py): what it
builds, what it reads back, the presets, the mode switch, the presses and their failures, the
impulse press, its jobs. On a fake cmds that keeps controls by name (created, edited, queried); the
scene half is docs/superpowers/plans/verify_ragdoll.py and verify_ragdoll_blend.py."""

import contextlib
import io
import json
import sys
import unittest

import maya_hubcopy as hubcopy
import maya_hubstyle as hubstyle
from maya_ragdoll import fall as rd
from maya_ragdoll import impulse
from maya_ragdoll import panel


class Ui(object):
    """Controls by name; a radio button belongs to the collection made last (or named)."""

    CONTROLS = ("text", "button", "floatSliderGrp", "floatField", "intField", "checkBox",
                "textScrollList", "iconTextRadioButton", "iconTextRadioCollection",
                "columnLayout", "rowLayout", "flowLayout")

    def __init__(self):
        self.controls = {}
        self.order = []
        self.optionvars = {}
        self.calls = []
        self.jobs = {}
        self.killed = []
        self.collection = None
        self.selection = ["|Manny_Rig_Character|Manny_Rig:Group|Manny_Rig:Main"]
        self.time = 10.0
        self.enabled = {}

    def _control(self, kind):
        def call(*args, **kw):
            name = args[0] if args else None
            if kw.get("exists"):
                return name in self.controls
            if kw.get("query") or kw.get("q"):
                item = self.controls[name]
                if kind == "iconTextRadioCollection" and kw.get("select"):
                    return item.get("selected")
                for flag in ("value", "select", "label", "manage", "enable"):
                    if kw.get(flag):
                        return item.get(flag)
                return None
            if kw.get("edit") or kw.get("e"):
                item = self.controls[name]
                for key, value in kw.items():
                    if key not in ("edit", "e"):
                        item[key] = value
                if kind == "iconTextRadioButton" and kw.get("select"):
                    self._lit(name)
                return name
            name = name or "%s%d" % (kind, len(self.order))
            item = dict(kw, kind=kind)
            self.controls[name] = item
            self.order.append(name)
            if kind == "iconTextRadioCollection":
                self.collection = name
            if kind == "iconTextRadioButton":
                item["collection"] = kw.get("collection", self.collection)
                item["select"] = False
                if kw.get("select"):
                    self._lit(name)
            return name
        return call

    def _lit(self, name):
        collection = self.controls[name]["collection"]
        for other, item in self.controls.items():
            if item.get("kind") == "iconTextRadioButton" and item.get("collection") == collection:
                item["select"] = other == name
        if collection in self.controls:
            self.controls[collection]["selected"] = name

    def __getattr__(self, name):
        if name in Ui.CONTROLS:
            return self._control(name)

        def other(*args, **kw):
            self.calls.append((name, args, kw))
            return None
        return other

    def optionVar(self, **kw):                              # noqa: N802
        if "exists" in kw:
            return kw["exists"] in self.optionvars
        if "query" in kw:
            return self.optionvars.get(kw["query"])
        for flag in ("stringValue", "intValue", "floatValue"):
            if flag in kw:
                name, value = kw[flag]
                self.optionvars[name] = value
        return None

    def scriptJob(self, event=None, parent=None, exists=None, kill=None, force=False):  # noqa: N802
        if exists is not None:
            return exists in self.jobs
        if kill is not None:
            self.killed.append(kill)
            self.jobs.pop(kill, None)
            return None
        number = len(self.jobs) + len(self.killed) + 1
        self.jobs[number] = (event, parent)
        return number

    def ls(self, selection=False, long=False, **_kw):
        return list(self.selection)

    def currentTime(self, query=False, **_kw):              # noqa: N802
        return self.time

    def getAttr(self, plug):                                # noqa: N802
        return self.enabled.get(plug.rsplit(".", 1)[0], True)

    def setParent(self, *args, **kw):                       # noqa: N802
        return None


class Ref(object):
    label = "Manny_Rig"
    rig = "Manny_Rig"


class Base(unittest.TestCase):
    """The panel on a fake: the scene the subtitle reads stubbed, the module's own state saved."""

    def setUp(self):
        self.ui = Ui()
        self.saved = (panel.cmds, rd._ref, rd._highlight, impulse.arrows, dict(panel.JOB),
                      dict(panel._DESCRIBED), getattr(sys, "_skeldar_hubcopy", None))
        panel.cmds = self.ui
        rd._ref = lambda selection: Ref()
        rd._highlight = lambda: None
        impulse.arrows = lambda rig: []
        panel.JOB.clear()
        panel._DESCRIBED.clear()
        sys._skeldar_hubcopy = {"stack": [], "counter": 0, "scopes": {}, "installed": False}
        hubstyle.take_marks()

    def tearDown(self):
        (panel.cmds, rd._ref, rd._highlight, impulse.arrows, job, described, copies) = self.saved
        panel.JOB.clear()
        panel.JOB.update(job)
        panel._DESCRIBED.clear()
        panel._DESCRIBED.update(described)
        if copies is None:
            del sys._skeldar_hubcopy
        else:
            sys._skeldar_hubcopy = copies
        hubstyle.take_marks()

    def build(self):
        panel.build_panel()
        return hubstyle.take_marks()

    def label(self, name):
        return self.ui.controls[name].get("label")


class Names(unittest.TestCase):

    def test_every_control_name_is_its_own(self):
        names = [panel._slider(k) for k, *_r in panel.ALL_SLIDERS]
        names += [panel._tab(k) for k, _l in panel.LAYERS]
        names += [panel._mode(k) for k, _l in panel.MODES]
        for zone in rd.plan.ZONES:
            names.append(panel._zone_tabs(zone))
            names.append(panel._zone_strength(zone))
            names += [panel._zone_seg(zone, s) for s in rd.plan.STATES]
        names += [panel._preset_btn(n) for n in rd.plan.PRESETS]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(n.startswith("skeldarRagdoll") for n in names))

    def test_the_impulse_button_is_no_name_the_scene_uses(self):
        self.assertNotEqual(panel.IMPULSE_BTN, impulse.MARKER)


class Memory(Base):

    def test_nothing_remembered_is_the_defaults(self):
        s = panel.remembered()
        self.assertEqual(s["mode"], "fall")
        self.assertEqual(s["length"], rd.DEFAULTS["length"])
        self.assertEqual(sorted(s["zones"]), sorted(rd.plan.ZONES))

    def test_a_broken_memory_is_the_defaults(self):
        self.ui.optionvars[panel.OPTION] = "{not json"
        self.assertEqual(panel.remembered()["length"], rd.DEFAULTS["length"])

    def test_the_memory_comes_back_cleaned(self):
        self.ui.optionvars[panel.OPTION] = json.dumps({"length": 90, "mode": "blend",
                                                       "layer": "nonsense", "junk": 1})
        s = panel.remembered()
        self.assertEqual((s["length"], s["mode"], s["layer"]), (90, "blend", "new"))
        self.assertNotIn("junk", s)

    def test_values_with_the_card_closed_are_the_memory_and_written_back(self):
        self.ui.optionvars[panel.OPTION] = json.dumps({"length": 33})
        s = panel.values()
        self.assertEqual(s["length"], 33)
        self.assertEqual(json.loads(self.ui.optionvars[panel.OPTION])["length"], 33)


class Built(Base):

    def setUp(self):
        Base.setUp(self)
        self.ui.optionvars[panel.OPTION] = json.dumps({"length": 45, "mass": 90,
                                                       "drop_weapon": False, "layer": "base"})
        self.marks = self.build()

    def test_every_slider_shows_the_memory(self):
        for key, label, low, high, step in panel.ALL_SLIDERS:
            item = self.ui.controls[panel._slider(key)]
            self.assertEqual(item["label"], label)
            self.assertEqual((item["minValue"], item["maxValue"]), (low, high))
            self.assertEqual(item["precision"], 0 if step >= 1 else 2)
            self.assertIs(item["changeCommand"], panel._changed)
            self.assertEqual(item["annotation"], panel.TIPS[key])
        self.assertEqual(self.ui.controls[panel._slider("length")]["value"], 45.0)
        self.assertEqual(self.ui.controls[panel._slider("mass")]["value"], 90.0)

    def test_the_chip_and_the_segments_show_the_memory(self):
        self.assertFalse(self.ui.controls[panel.DROP_CHIP]["value"])
        self.assertTrue(self.ui.controls[panel._tab("base")]["select"])
        self.assertFalse(self.ui.controls[panel._tab("new")]["select"])
        self.assertTrue(self.ui.controls[panel._mode("fall")]["select"])

    def test_six_zone_rows_each_three_states_and_a_strength(self):
        zones = rd.plan.zones(None)
        for zone in rd.plan.ZONES:
            state, strength = zones[zone]
            for name in rd.plan.STATES:
                self.assertEqual(self.ui.controls[panel._zone_seg(zone, name)]["select"],
                                 name == state, (zone, name))
                self.assertEqual(self.ui.controls[panel._zone_seg(zone, name)]["collection"],
                                 panel._zone_tabs(zone))
            self.assertEqual(self.ui.controls[panel._zone_strength(zone)]["value"],
                             float(strength))

    def test_a_preset_button_each_and_its_press(self):
        for name, (label, _zones) in rd.plan.PRESETS.items():
            self.assertEqual(self.label(panel._preset_btn(name)), label)
        pressed = []
        saved = panel.apply_preset
        panel.apply_preset = pressed.append
        try:
            self.ui.controls[panel._preset_btn("overlap")]["command"]()
        finally:
            panel.apply_preset = saved
        self.assertEqual(pressed, ["overlap"])

    def test_the_three_buttons_and_their_presses(self):
        marks = dict((m.name, (m.role, m.icon)) for m in self.marks)
        self.assertEqual(marks[panel.FALL_BTN], ("primary", "skull"))
        self.assertEqual(marks[panel.BLEND_BTN], ("primary", "wave-sine"))
        self.assertEqual(marks[panel.IMPULSE_BTN], ("secondary", "plus"))
        self.assertEqual(marks[panel.SUBTITLE][0], "subtitle")
        self.assertEqual(marks[panel.STATUS][0], "status")
        pressed = []
        saved = (panel.press_fall, panel.press_blend, panel.press_impulse)
        panel.press_fall = lambda: pressed.append("fall")
        panel.press_blend = lambda: pressed.append("blend")
        panel.press_impulse = lambda: pressed.append("impulse")
        try:
            for name in (panel.FALL_BTN, panel.BLEND_BTN, panel.IMPULSE_BTN):
                self.ui.controls[name]["command"]()
        finally:
            panel.press_fall, panel.press_blend, panel.press_impulse = saved
        self.assertEqual(pressed, ["fall", "blend", "impulse"])

    def test_fall_mode_shows_fall_s_rows_and_button_only(self):
        self.assertTrue(self.ui.controls[panel.FALL_BOX]["manage"])
        self.assertFalse(self.ui.controls[panel.BLEND_BOX]["manage"])
        self.assertTrue(self.ui.controls[panel.FALL_BTN]["manage"])
        self.assertFalse(self.ui.controls[panel.BLEND_BTN]["manage"])

    def test_the_subtitle_says_what_fall_does_now(self):
        self.assertEqual(self.label(panel.SUBTITLE), "Manny_Rig falls from frame 10 to 55")
        self.assertTrue(panel.is_open())

    def test_two_jobs_on_the_status_line_selection_and_time(self):
        jobs = panel.JOB[""]
        events = [self.ui.jobs[j][0] for j in jobs]
        self.assertEqual([e[0] for e in events], ["SelectionChanged", "timeChanged"])
        self.assertEqual(events[0][1]._skeldar_seen, (panel.STATUS, panel.refresh))
        self.assertEqual(events[1][1]._skeldar_seen, (panel.STATUS, panel.refresh_time))
        self.assertTrue(all(self.ui.jobs[j][1] == panel.STATUS for j in jobs))

    def test_a_rebuild_kills_the_card_s_old_jobs(self):
        first = list(panel.JOB[""])
        self.build()
        self.assertEqual(self.ui.killed, first)
        self.assertEqual(len(panel.JOB[""]), 2)


class ReadBack(Base):

    def setUp(self):
        Base.setUp(self)
        self.build()

    def test_values_read_every_control_and_remember_them(self):
        ui = self.ui.controls
        ui[panel._slider("length")]["value"] = 120.0
        ui[panel._slider("blend_out")]["value"] = 4.0
        ui[panel.DROP_CHIP]["value"] = False
        self.ui.controls[panel._tab("base")]["select"] = True        # through the fake's edit
        self.ui._lit(panel._tab("base"))
        self.ui._lit(panel._mode("blend"))
        self.ui._lit(panel._zone_seg("arm_l", "free"))
        ui[panel._zone_strength("arm_l")]["value"] = 0.25
        s = panel.values()
        self.assertEqual((s["length"], s["blend_out"], s["drop_weapon"], s["layer"], s["mode"]),
                         (120.0, 4.0, False, "base", "blend"))
        self.assertEqual(list(s["zones"]["arm_l"]), ["free", 0.25])
        stored = json.loads(self.ui.optionvars[panel.OPTION])
        self.assertEqual((stored["length"], stored["mode"], stored["zones"]["arm_l"]),
                         (120.0, "blend", ["free", 0.25]))

    def test_a_mode_switch_shows_blend_s_rows_and_says_blend(self):
        self.ui._lit(panel._mode("blend"))
        panel._changed()
        self.assertFalse(self.ui.controls[panel.FALL_BOX]["manage"])
        self.assertTrue(self.ui.controls[panel.BLEND_BOX]["manage"])
        self.assertFalse(self.ui.controls[panel.FALL_BTN]["manage"])
        self.assertTrue(self.ui.controls[panel.BLEND_BTN]["manage"])
        self.assertEqual(self.label(panel.SUBTITLE),
                         "Manny_Rig blends with physics from frame 10 to 70")

    def test_a_preset_lights_its_zones_and_says_them(self):
        line = panel.apply_preset("overlap")
        for zone in rd.plan.ZONES:
            state, strength = rd.plan.PRESETS["overlap"][1][zone]
            self.assertTrue(self.ui.controls[panel._zone_seg(zone, state)]["select"], zone)
            self.assertEqual(self.ui.controls[panel._zone_strength(zone)]["value"], strength)
        self.assertEqual(line, "Arm overlap: Torso Anim, Head Anim, Arm L Follow 0.3, "
                               "Arm R Follow 0.3, Leg L Anim, Leg R Anim")
        self.assertEqual(self.label(panel.STATUS), line)
        stored = json.loads(self.ui.optionvars[panel.OPTION])["zones"]
        self.assertEqual(stored["arm_r"], ["follow", 0.3])

    def test_a_preset_with_the_card_closed_is_remembered(self):
        closed = Ui()
        panel.cmds = closed
        panel.apply_preset("follow")
        stored = json.loads(closed.optionvars[panel.OPTION])["zones"]
        self.assertEqual(set(tuple(v) for v in stored.values()), {("follow", 0.6)})

    def test_zones_text_names_a_follow_s_strength_only(self):
        zones = dict((z, ["anim", 1.0]) for z in rd.plan.ZONES)
        zones["head"] = ["free", 0.7]
        zones["leg_r"] = ["follow", 0.4]
        text = panel.zones_text(zones)
        self.assertIn("Head Free,", text)
        self.assertTrue(text.endswith("Leg R Follow 0.4"), text)
        self.assertNotIn("Anim 1.0", text)


class Presses(Base):

    def setUp(self):
        Base.setUp(self)
        self.build()
        self.ran = []
        import maya_ragdoll.blend as blend
        self.blend = blend
        self.saved_runs = (rd.fall, blend.blend, panel._progress)
        rd.fall = lambda given=None, progress=None: (self.ran.append(("fall", dict(given),
                                                                      progress)) or (True, "fell"))
        blend.blend = lambda given=None, progress=None: (self.ran.append(("blend", dict(given),
                                                                          progress))
                                                         or (True, "blended"))
        panel._progress = lambda name, s: None

    def tearDown(self):
        rd.fall, self.blend.blend, panel._progress = self.saved_runs
        Base.tearDown(self)

    def test_main_presses_fall_in_fall_mode_with_the_card_s_settings(self):
        self.ui.controls[panel._slider("length")]["value"] = 77.0
        self.assertEqual(panel.press_main(), "fell")
        kind, given, progress = self.ran[-1]
        self.assertEqual((kind, given["length"], progress), ("fall", 77.0, None))
        self.assertEqual(self.label(panel.STATUS), "fell")

    def test_main_presses_blend_in_blend_mode(self):
        self.ui._lit(panel._mode("blend"))
        self.assertEqual(panel.press_main(), "blended")
        self.assertEqual(self.ran[-1][0], "blend")
        self.assertEqual(self.ran[-1][1]["mode"], "blend")

    def test_a_refusal_is_the_line(self):
        def refuse(given=None, progress=None):
            raise rd.Refused("Fall drops one rig at a time - 2 are selected")
        rd.fall = refuse
        self.assertEqual(panel.press_fall(), "Fall drops one rig at a time - 2 are selected")

    def test_a_failure_says_which_press_failed(self):
        def boom(given=None, progress=None):
            raise RuntimeError("solver gone")
        self.blend.blend = boom
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(panel.press_blend(), "Ragdoll Blend failed: solver gone")
        rd.fall = boom
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(panel.press_fall(), "Ragdoll failed: solver gone")

    def test_a_press_refreshes_the_subtitle(self):
        self.ui.selection = []

        def refuse(selection):
            raise rd.Refused(rd.NOTHING)
        rd._ref = refuse
        panel.press_fall()
        self.assertEqual(self.label(panel.SUBTITLE), rd.NOTHING)

    def test_the_progress_window_steps_every_frame(self):
        stepped = []

        class Progress(object):
            def __enter__(self):
                stepped.append("open")
                return self

            def __exit__(self, *exc):
                stepped.append("closed")
                return False

            def step(self, text):
                stepped.append(text)
                return True

        panel._progress = lambda name, s: (stepped.append((name, s["length"])) or Progress())

        def fall(given=None, progress=None):
            progress(11)
            progress(12)
            return True, "fell"
        rd.fall = fall
        panel.press_fall()
        self.assertEqual(stepped, [("Ragdoll", rd.DEFAULTS["length"]), "open", "frame 11",
                                   "frame 12", "closed"])
        stepped[:] = []

        def blend(given=None, progress=None):
            progress(3)
            return True, "blended"
        self.blend.blend = blend
        panel.press_blend()
        self.assertEqual(stepped[0][0], "Ragdoll Blend")
        self.assertEqual(stepped[1:], ["open", "frame 3", "closed"])

    def test_no_progress_window_without_a_ui(self):
        saved = panel._progress
        panel._progress = self.saved_runs[2]
        try:
            from maya_poselib import timewalk
            real = timewalk.Progress

            def broken(*args, **kw):
                raise RuntimeError("no UI")
            timewalk.Progress = broken
            try:
                self.assertIsNone(panel._progress("Ragdoll", {"length": 10}))
            finally:
                timewalk.Progress = real
            made = panel._progress("Ragdoll", {"length": 10})
            self.assertEqual((made.title, made.total), ("Ragdoll", 11))
        finally:
            panel._progress = saved


class ImpulsePress(Base):

    def setUp(self):
        Base.setUp(self)
        self.saved_create = impulse.create

    def tearDown(self):
        impulse.create = self.saved_create
        Base.tearDown(self)

    def test_the_arrow_s_line(self):
        impulse.create = lambda: ("|Manny_Rig:impulse1", "Impulse on the head - Frame 10")
        self.build()
        self.assertEqual(panel.press_impulse(), "Impulse on the head - Frame 10")
        self.assertEqual(self.label(panel.STATUS), "Impulse on the head - Frame 10")

    def test_a_refusal_and_a_failure(self):
        def refuse():
            raise rd.Refused("select a part of a rig")
        impulse.create = refuse
        self.assertEqual(panel.press_impulse(), "select a part of a rig")

        def boom():
            raise ValueError("no body")
        impulse.create = boom
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(panel.press_impulse(), "+ Impulse failed: no body")
        self.assertFalse(panel.is_open())             # closed card: the text is still answered


class Described(Base):

    def test_enabled_impulses_are_counted(self):
        impulse.arrows = lambda rig: ["|a1", "|a2", "|a3"]
        self.ui.enabled["|a2"] = False
        self.assertEqual(panel.described(), {"label": "Manny_Rig", "tail": ", 2 impulses"})
        self.ui.enabled["|a3"] = False
        self.assertEqual(panel.described()["tail"], ", 1 impulse")

    def test_arrows_that_cannot_be_read_count_none(self):
        def broken(rig):
            raise RuntimeError("gone")
        impulse.arrows = broken
        self.assertEqual(panel.described(), {"label": "Manny_Rig", "tail": ""})

    def test_any_other_failure_is_the_nothing_line(self):
        def broken(selection):
            raise KeyError("x")
        rd._ref = broken
        self.assertEqual(panel.described(), {"text": rd.NOTHING})

    def test_the_subtitle_carries_the_impulses_and_the_highlight(self):
        impulse.arrows = lambda rig: ["|a1"]
        rd._highlight = lambda: (20.0, 31.0)
        self.assertEqual(panel.subtitle(), "Manny_Rig falls from frame 20 to 30, 1 impulse")

    def test_a_refresh_with_no_card_reads_nothing(self):
        reads = []
        rd._ref = lambda selection: reads.append(1) or Ref()
        panel.refresh()
        panel.refresh_time()
        self.assertEqual(reads, [])


class Copies(Base):

    def test_a_popup_copy_keeps_its_own_jobs_and_described(self):
        self.build()
        hub_jobs = list(panel.JOB[""])
        scope = hubcopy.new_scope("ragdoll")
        with hubcopy.entered(scope):
            self.assertEqual(panel._card_key(), scope.tag)
            panel.start()
            panel.refresh()
            self.assertIn(scope.tag, panel._DESCRIBED)
        self.assertEqual(panel.JOB[""], hub_jobs)
        self.assertEqual(len(panel.JOB[scope.tag]), 2)
        self.assertEqual(self.ui.killed, [])

    def test_a_closed_copy_s_jobs_are_forgotten_on_the_next_start(self):
        self.build()
        scope = hubcopy.new_scope("ragdoll")
        with hubcopy.entered(scope):
            panel.start()
        hubcopy.close(scope, cmds=self.ui)
        panel.start()
        self.assertNotIn(scope.tag, panel.JOB)
        self.assertIn("", panel.JOB)

    def test_a_job_maya_will_not_kill_does_not_stop_the_start(self):
        self.build()

        def stubborn(*args, **kw):
            if kw.get("exists") is not None:
                raise RuntimeError("Maya says no")
            return 99
        self.ui.scriptJob = stubborn
        panel.start()
        self.assertEqual(panel.JOB[""], [99, 99])


class Edges(Base):

    def test_the_skin_lays_the_drop_chip_in_a_flow(self):
        hubstyle.set_skinning(True)
        try:
            marks = self.build()
        finally:
            hubstyle.set_skinning(False)
        roles = [m.role for m in marks]
        self.assertIn("flow", roles)
        self.assertEqual(dict((m.name, m.role) for m in marks)[panel.DROP_CHIP], "chip")

    def test_a_zone_row_missing_keeps_the_zone_as_remembered(self):
        self.build()
        del self.ui.controls[panel._zone_strength("head")]
        self.ui._lit(panel._zone_seg("torso", "free"))
        s = panel.values()
        self.assertEqual(s["zones"]["head"], rd.plan.zones(None)["head"])
        self.assertEqual(s["zones"]["torso"][0], "free")

    def test_jobs_maya_will_not_make_leave_none(self):
        def refused(*args, **kw):
            if kw.get("exists") is not None:
                return False
            raise RuntimeError("no UI")
        self.ui.scriptJob = refused
        self.build()
        self.assertEqual(panel.JOB[""], [])


class Window(unittest.TestCase):

    def test_show_window_opens_the_hub_on_ragdoll(self):
        import maya_hub
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key) or "hub"
        try:
            self.assertEqual(panel.show_window(), "hub")
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["ragdoll"])


if __name__ == "__main__":
    unittest.main()
