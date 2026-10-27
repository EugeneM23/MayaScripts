"""maya_dynamics.panel - the Dynamics card beyond its knobs (tests/test_dynamics_panel.py): the
chains list and what picking a row does, the subtitle, the presses (+ Chain, Remove, Auto body,
+ Sphere / + Capsule / + Floor / + Wind), the collider and wind fields, the refresh, the build's
callbacks and the card's jobs. On a fake cmds that keeps controls by name; `setup` and `run` stubbed
where they touch the scene (their own tests and verify_dynamics.py prove that half)."""

import contextlib
import io
import json
import sys
import unittest

import maya_hubcopy as hubcopy
import maya_hubstyle as hubstyle
from maya_dynamics import model
from maya_dynamics import panel
from maya_dynamics import run
from maya_dynamics import setup


class Ui(object):
    """Controls by name; a textScrollList keeps its rows and a 1-based pick."""

    CONTROLS = ("text", "button", "floatSliderGrp", "floatField", "intField", "checkBox",
                "textScrollList", "rowLayout", "columnLayout")

    def __init__(self):
        self.controls = {}
        self.order = []
        self.optionvars = {}
        self.calls = []
        self.jobs = {}
        self.killed = []
        self.selection = []
        self.selected = []
        self.attrs = {}
        self.keys = {}
        self.existing = set()

    def _control(self, kind):
        def call(*args, **kw):
            name = args[0] if args else None
            if kw.get("exists"):
                return name in self.controls
            if kw.get("query"):
                item = self.controls[name]
                for flag in ("value", "selectIndexedItem", "label", "enable"):
                    if kw.get(flag):
                        return item.get(flag)
                return None
            if kw.get("edit"):
                item = self.controls[name]
                if kw.get("removeAll"):
                    item["rows"] = []
                    item["selectIndexedItem"] = []
                if "append" in kw:
                    item.setdefault("rows", []).append(kw["append"])
                if "selectIndexedItem" in kw:
                    item.setdefault("selectIndexedItem", []).append(kw["selectIndexedItem"])
                for flag in ("value", "label", "enable"):
                    if flag in kw:
                        item[flag] = kw[flag]
                return name
            name = name or "%s%d" % (kind, len(self.order))
            self.controls[name] = dict(kw, kind=kind)
            self.order.append(name)
            return name
        return call

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
        name, value = kw["stringValue"]
        self.optionvars[name] = value

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

    def select(self, nodes, replace=False):
        self.selected.append(list(nodes) if isinstance(nodes, (list, tuple)) else [nodes])

    def objExists(self, node):                              # noqa: N802
        return node in self.existing

    def objectType(self, node, isAType=None):               # noqa: N802
        return not node.endswith("Shape")

    def getAttr(self, plug):                                # noqa: N802
        return self.attrs[plug]

    def setAttr(self, plug, value):                         # noqa: N802
        self.attrs[plug] = value
        self.calls.append(("setAttr", (plug, value), {}))

    def keyframe(self, plug, query=False, keyframeCount=False):
        return self.keys.get(plug, 0)

    def setKeyframe(self, node, attribute=None, value=None):   # noqa: N802
        self.calls.append(("setKeyframe", (node, attribute, value), {}))


class Base(unittest.TestCase):

    def setUp(self):
        self.ui = Ui()
        self.patch(panel, "cmds", self.ui)
        self.saved_state = (dict(panel.JOB), dict(panel._PICKED), dict(panel._ROWS),
                            getattr(sys, "_skeldar_hubcopy", None))
        panel.JOB.clear()
        panel._PICKED.clear()
        panel._ROWS.clear()
        sys._skeldar_hubcopy = {"stack": [], "counter": 0, "scopes": {}, "installed": False}
        self.addCleanup(self._put_back)
        #  the scene, as setup and run answer it
        self.uuids = {"|g|hair_dyn": "U1", "|g|tail_dyn": "U2", "|g|cape_dyn": "U3"}
        self.roots = {"|g|hair_dyn": "|g|Rig:hair_01", "|g|tail_dyn": "|g|Rig:tail_01",
                      "|g|cape_dyn": "|g|Rig:cape_01"}
        self.ui.existing.update(self.uuids)
        self.stored = dict((c, model.settings({})) for c in self.uuids)
        self.layers = {}
        self.readings = []
        self.patch(setup, "_uuid", lambda node: self.uuids.get(node))
        self.patch(setup, "_by_uuid", lambda uuid: dict((v, k) for k, v in
                                                        self.uuids.items()).get(uuid))
        self.patch(setup, "chains", lambda: sorted(self.uuids))
        self.patch(setup, "root_of", lambda chain: self.roots.get(chain))
        self.patch(setup, "label", lambda chain: "%s · 6" % setup.leaf(self.roots[chain]))
        self.patch(setup, "read_settings", lambda chain: dict(self.stored[chain]))
        self.patch(setup, "write_settings",
                   lambda chain, s: self.stored.__setitem__(chain, dict(s)))
        self.patch(setup, "layer_of", lambda chain: self.layers.get(chain))
        self.patch(setup, "wind", lambda: None)
        self.patch(setup, "is_collider", lambda node: node.endswith("_col"))
        self.patch(setup, "kind_of", lambda node: "sphere" if "sphere" in node else "capsule")
        self.patch(setup, "_has", lambda node, attr: (node + "." + attr) in self.ui.attrs)
        self.patch(setup, "reading", self._reading)
        self.targets = []
        self.patch(run, "targets", lambda selection=None: list(self.targets))
        self.patch(run, "_highlight", lambda highlight: None)
        self.patch(run, "frame_range", lambda highlight: (0, 48, False))
        hubstyle.take_marks()

    def patch(self, owner, name, value):
        saved = getattr(owner, name)
        setattr(owner, name, value)
        self.addCleanup(setattr, owner, name, saved)

    def _put_back(self):
        job, picked, rows, copies = self.saved_state
        panel.JOB.clear()
        panel.JOB.update(job)
        panel._PICKED.clear()
        panel._PICKED.update(picked)
        panel._ROWS.clear()
        panel._ROWS.update(rows)
        if copies is None:
            del sys._skeldar_hubcopy
        else:
            sys._skeldar_hubcopy = copies
        hubstyle.take_marks()

    @contextlib.contextmanager
    def _reading(self):
        self.readings.append("in")
        yield
        self.readings.append("out")

    def build(self):
        panel.build_panel()
        return hubstyle.take_marks()

    def control(self, name):
        return self.ui.controls[name]

    def status(self):
        return self.control(panel.STATUS).get("label")


class Chains(Base):

    def test_picked_drops_chains_gone_from_the_scene(self):
        panel._PICKED[""] = ["U1", "U9", "U2"]
        self.ui.existing.discard("|g|tail_dyn")
        self.assertEqual(panel.picked(), ["|g|hair_dyn"])

    def test_picked_is_none_with_the_card_closed(self):
        self.assertEqual(panel.picked(), [])

    def test_set_picked_keeps_uuids(self):
        panel._set_picked(["|g|tail_dyn", None, "|g|hair_dyn"])
        self.assertEqual(panel._PICKED[""], ["U2", "U1"])

    def test_acting_is_the_picked_else_run_s_targets(self):
        self.targets = ["|g|cape_dyn"]
        self.assertEqual(panel.acting(), ["|g|cape_dyn"])
        panel._set_picked(["|g|hair_dyn"])
        self.assertEqual(panel.acting(), ["|g|hair_dyn"])

    def test_the_subtitle_names_the_chains_and_the_frames(self):
        self.assertEqual(panel.subtitle(), run.NOTHING)
        self.targets = ["|g|hair_dyn", "|g|tail_dyn"]
        self.assertEqual(panel.subtitle(), "Simulate: hair_01, tail_01 over 0-48")

    def test_more_than_four_chains_are_counted(self):
        names = ["|g|c%d_dyn" % i for i in range(6)]
        self.targets = names
        self.patch(setup, "root_of", lambda chain: None)
        self.assertEqual(panel.subtitle(),
                         "Simulate: c0_dyn, c1_dyn, c2_dyn, c3_dyn and 2 more over 0-48")

    def test_no_time_slider_drops_the_frames(self):
        def broken(highlight):
            raise RuntimeError("no slider")
        self.patch(run, "frame_range", broken)
        self.targets = ["|g|hair_dyn"]
        self.assertEqual(panel.subtitle(), "Simulate: hair_01")


class ChainList(Base):

    def setUp(self):
        Base.setUp(self)
        self.build()

    def test_the_list_lists_every_chain_and_lights_the_picked(self):
        panel._set_picked(["|g|tail_dyn"])
        panel._fill_list()
        item = self.control(panel.CHAINS)
        self.assertEqual(item["rows"], ["cape_01 · 6", "hair_01 · 6", "tail_01 · 6"])
        self.assertEqual(item["selectIndexedItem"], [3])
        self.assertEqual(panel._ROWS[""], ["|g|cape_dyn", "|g|hair_dyn", "|g|tail_dyn"])

    def test_no_list_fills_nothing(self):
        del self.ui.controls[panel.CHAINS]
        panel._ROWS.clear()
        panel._fill_list()
        self.assertNotIn("", panel._ROWS)

    def test_picking_rows_selects_their_roots_and_shows_the_first_one_s_knobs(self):
        self.stored["|g|hair_dyn"]["damping"] = 0.77
        self.stored["|g|hair_dyn"]["loop"] = True
        self.stored["|g|hair_dyn"]["substeps"] = 9
        self.control(panel.CHAINS)["selectIndexedItem"] = [2, 3, 7]
        panel.list_picked()
        self.assertEqual(panel.picked(), ["|g|hair_dyn", "|g|tail_dyn"])
        self.assertEqual(self.ui.selected[-1], ["|g|Rig:hair_01", "|g|Rig:tail_01"])
        self.assertEqual(self.control(panel._slider("damping"))["value"], 0.77)
        self.assertTrue(self.control(panel.LOOP_CHIP)["value"])
        self.assertEqual(self.control(panel.SUBSTEPS)["value"], 9)
        self.assertEqual(self.control(panel.SUBTITLE)["label"],
                         "Simulate: hair_01, tail_01 over 0-48")

    def test_picking_nothing_selects_nothing(self):
        self.control(panel.CHAINS)["selectIndexedItem"] = []
        panel.list_picked()
        self.assertEqual(self.ui.selected, [])
        self.assertEqual(panel.picked(), [])

    def test_a_bake_option_is_written_into_the_picked_chains(self):
        panel._set_picked(["|g|hair_dyn"])
        self.control(panel.PREROLL)["value"] = 12
        self.assertEqual(panel.option_changed("preroll"), "Set on 1 chain - press Simulate")
        self.assertEqual(self.stored["|g|hair_dyn"]["preroll"], 12)
        self.assertEqual(self.stored["|g|tail_dyn"]["preroll"], model.DEFAULTS["preroll"])
        self.assertEqual(json.loads(self.ui.optionvars[panel.OPTION])["preroll"], 12)

    def test_nothing_picked_only_remembers(self):
        self.control(panel.LOOP_CHIP)["value"] = True
        line = panel.option_changed("loop")
        self.assertIn("Set for the next chain", line)
        self.assertTrue(json.loads(self.ui.optionvars[panel.OPTION])["loop"])
        self.assertFalse(any(s["loop"] for s in self.stored.values()))


class Presses(Base):

    def setUp(self):
        Base.setUp(self)
        self.build()

    def test_add_chain_picks_what_it_made_with_the_card_s_settings(self):
        given = []
        self.control(panel._slider("gravity"))["value"] = 2.5
        self.patch(setup, "add_chains", lambda selection, s: (
            given.append(s) or (["|g|hair_dyn", "|g|tail_dyn"], ["joint_09 ends at a branch"],
                                None)))
        line = panel.press_add_chain()
        self.assertEqual(line, "Chains: hair_01, tail_01 - press Simulate | joint_09 ends at "
                               "a branch")
        self.assertEqual(given[0]["gravity"], 2.5)
        self.assertEqual(panel.picked(), ["|g|hair_dyn", "|g|tail_dyn"])
        self.assertEqual(self.status(), line)

    def test_add_chain_with_the_card_closed_takes_the_memory(self):
        self.ui.optionvars[panel.OPTION] = json.dumps({"gravity": -1.5})
        del self.ui.controls[panel.STATUS]
        given = []
        self.patch(setup, "add_chains", lambda selection, s: (given.append(s)
                                                              or (["|g|hair_dyn"], [], None)))
        self.assertEqual(panel.press_add_chain(), "Chains: hair_01 - press Simulate")
        self.assertEqual(given[0]["gravity"], -1.5)

    def test_a_refused_chain_is_the_line_and_picks_nothing(self):
        self.patch(setup, "add_chains", lambda selection, s: ([], [], setup.NOTHING))
        self.assertEqual(panel.press_add_chain(), setup.NOTHING)
        self.assertEqual(panel.picked(), [])

    def test_a_failing_press_says_which(self):
        def boom(selection, s):
            raise RuntimeError("no joint")
        self.patch(setup, "add_chains", boom)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(panel.press_add_chain(), "+ Chain failed: no joint")

    def test_remove_takes_the_picked_and_forgets_them(self):
        removed = []
        self.patch(run, "remove", lambda chains: removed.append(list(chains)) or "removed 1")
        panel._set_picked(["|g|cape_dyn"])
        self.assertEqual(panel.press_remove(), "removed 1")
        self.assertEqual(removed, [["|g|cape_dyn"]])
        self.assertEqual(panel.picked(), [])

    def test_auto_body(self):
        self.ui.selection = ["|Manny_Rig:Main"]
        asked = []
        self.patch(setup, "auto_body", lambda selection: (asked.append(selection)
                                                          or (["c"] * 12, None)))
        self.assertEqual(panel.press_auto_body(), "Auto body: 12 colliders")
        self.assertEqual(asked, [["|Manny_Rig:Main"]])
        self.patch(setup, "auto_body", lambda selection: ([], "select a character"))
        self.assertEqual(panel.press_auto_body(), "select a character")

    def test_a_sphere_and_a_capsule_on_each_selected_bone(self):
        made = []
        self.patch(setup, "add_collider", lambda kind, node: (
            made.append((kind, node)) or node + "_" + kind + "_col"))
        self.ui.selection = ["|r|hand_r", "|r|bodyShape", "|r|hand_l"]
        self.assertEqual(panel.press_sphere(), "Sphere: hand_r_sphere_col, hand_l_sphere_col")
        self.assertEqual(made, [("sphere", "|r|hand_r"), ("sphere", "|r|hand_l")])
        self.assertEqual(self.ui.selected[-1], ["|r|hand_r_sphere_col", "|r|hand_l_sphere_col"])
        self.assertEqual(panel.press_capsule(), "Capsule: hand_r_capsule_col, hand_l_capsule_col")

    def test_no_bone_selected_says_so(self):
        self.ui.selection = ["|r|bodyShape"]
        self.assertEqual(panel.press_sphere(), "select a bone for the sphere")
        self.ui.selection = []
        self.assertEqual(panel.press_capsule(), "select a bone for the capsule")

    def test_a_floor_under_the_selection_else_at_zero(self):
        asked = []
        self.patch(setup, "add_floor", lambda node, height=None: (
            asked.append((node, height)) or "|Manny_Rig_Character|Dynamics|Floor"))
        self.ui.selection = ["|Manny_Rig:root", "|x"]
        self.assertEqual(panel.press_floor(), "Floor: Floor")
        self.ui.selection = []
        panel.press_floor()
        self.assertEqual(asked, [("|Manny_Rig:root", None), (None, 0.0)])
        self.assertEqual(self.ui.selected[-1], ["|Manny_Rig_Character|Dynamics|Floor"])

    def test_wind_names_its_strength(self):
        self.patch(setup, "add_wind", lambda: "|Wind")
        self.ui.attrs["|Wind.strength"] = 0.3
        self.assertEqual(panel.press_wind(), "Wind: the arrow's +Z blows - strength 0.30 g")
        self.assertEqual(self.ui.selected[-1], ["|Wind"])

    def test_simulate_from_its_button_reads_afresh(self):
        forgot, solved = [], []
        self.patch(run, "forget", lambda: forgot.append(1))
        self.patch(run, "simulate", lambda chains, **kw: solved.append(chains) or "baked")
        self.targets = ["|g|tail_dyn"]
        self.control(panel.SIMULATE_BTN)["command"]()
        self.assertEqual((forgot, solved, self.status()), ([1], [["|g|tail_dyn"]], "baked"))


class Fields(Base):

    def setUp(self):
        Base.setUp(self)
        self.build()
        self.redrawn = []
        self.patch(setup, "redraw", self.redrawn.append)

    def test_a_radius_onto_every_selected_collider(self):
        self.ui.attrs.update({"|a_sphere_col.radius": 5.0, "|b_capsule_col.radius": 3.0})
        self.ui.selection = ["|a_sphere_col", "|b_capsule_col", "|bone"]
        self.control(panel.COLLIDER_RADIUS)["value"] = 7.5
        line = panel.collider_changed("radius")
        self.assertEqual(line, "a_sphere_col, b_capsule_col radius = 7.50")
        self.assertEqual(self.ui.attrs["|a_sphere_col.radius"], 7.5)
        self.assertEqual(self.redrawn, ["|a_sphere_col", "|b_capsule_col"])

    def test_a_length_never_below_zero_and_only_where_there_is_one(self):
        self.ui.attrs.update({"|a_sphere_col.radius": 5.0, "|b_capsule_col.length": 10.0})
        self.ui.selection = ["|a_sphere_col", "|b_capsule_col"]
        self.control(panel.COLLIDER_LENGTH)["value"] = -3.0
        self.assertTrue(panel.collider_changed("length").startswith("b_capsule_col length"))
        self.assertEqual(self.ui.attrs["|b_capsule_col.length"], 0.0)
        self.assertNotIn("|a_sphere_col.length", self.ui.attrs)

    def test_no_collider_selected(self):
        self.ui.selection = ["|bone"]
        self.assertEqual(panel.collider_changed("radius"), "select a collider")

    def test_the_fields_follow_the_selected_collider(self):
        self.ui.attrs.update({"|a_sphere_col.radius": 4.0, "|a_sphere_col.length": 0.0,
                              "|b_capsule_col.radius": 2.0, "|b_capsule_col.length": 12.0})
        self.ui.selection = ["|a_sphere_col"]
        panel._collider_fields()
        radius, length = self.control(panel.COLLIDER_RADIUS), self.control(panel.COLLIDER_LENGTH)
        self.assertEqual((radius["enable"], radius["value"]), (True, 4.0))
        self.assertFalse(length["enable"])                    # a sphere has no length
        self.ui.selection = ["|b_capsule_col"]
        panel._collider_fields()
        self.assertEqual((length["enable"], length["value"]), (True, 12.0))
        self.ui.selection = ["|bone"]
        panel._collider_fields()
        self.assertFalse(radius["enable"])
        self.assertFalse(length["enable"])

    def test_wind_needs_its_arrow(self):
        self.assertEqual(panel.wind_changed("gust"), "press + Wind first")

    def test_a_wind_channel_is_keyed_where_it_has_keys(self):
        self.patch(setup, "wind", lambda: "|Wind")
        self.control(panel._wind_slider("gust"))["value"] = 0.8
        self.control(panel._wind_slider("strength"))["value"] = 2.0
        self.ui.keys["|Wind.gust"] = 3
        self.assertEqual(panel.wind_changed("gust"), "Wind gust 0.80")
        self.assertEqual(panel.wind_changed("strength"), "Wind strength 2.00")
        self.assertIn(("setKeyframe", ("|Wind", "gust", 0.8), {}), self.ui.calls)
        self.assertEqual(self.ui.attrs["|Wind.strength"], 2.0)
        self.assertNotIn("|Wind.gust", self.ui.attrs)

    def test_the_wind_sliders_follow_the_arrow(self):
        panel._wind_sliders()
        for attr, *_rest in setup.WIND_CHANNELS:
            self.assertFalse(self.control(panel._wind_slider(attr))["enable"])
        self.patch(setup, "wind", lambda: "|Wind")
        for attr, default, _low, _high in setup.WIND_CHANNELS:
            self.ui.attrs["|Wind." + attr] = default * 2
        panel._wind_sliders()
        for attr, default, _low, _high in setup.WIND_CHANNELS:
            item = self.control(panel._wind_slider(attr))
            self.assertEqual((item["enable"], item["value"]), (True, default * 2))


class Refresh(Base):

    def test_a_refresh_reads_once_inside_one_pass(self):
        self.build()
        self.readings[:] = []
        self.targets = ["|g|hair_dyn"]
        panel.refresh()
        self.assertEqual(self.readings, ["in", "out"])
        self.assertEqual(self.control(panel.SUBTITLE)["label"], "Simulate: hair_01 over 0-48")
        self.assertEqual(len(self.control(panel.CHAINS)["rows"]), 3)

    def test_a_closed_card_refreshes_nothing(self):
        panel.refresh()
        self.assertEqual(self.readings, [])


class BuildCallbacks(Base):
    """Every control's own callback reaches its press."""

    def setUp(self):
        Base.setUp(self)
        self.marks = self.build()
        self.pressed = []
        for name in ("knob_changed", "tip_changed", "apply_preset", "collider_changed",
                     "wind_changed", "option_changed"):
            self.patch(panel, name, lambda arg, n=name: self.pressed.append((n, arg)))

    def test_a_knob_slider_and_its_tip_field(self):
        for key, _low, _high, _default, tip in model.KNOBS:
            self.control(panel._slider(key))["changeCommand"]()
            if tip is not None:
                self.control(panel._tip(key))["changeCommand"]()
        knobs = [arg for n, arg in self.pressed if n == "knob_changed"]
        tips = [arg for n, arg in self.pressed if n == "tip_changed"]
        self.assertEqual(knobs, [k for k, *_r in model.KNOBS])
        self.assertEqual(tips, [k for k, _l, _h, _d, t in model.KNOBS if t is not None])

    def test_the_presets_fields_and_options(self):
        for name in model.PRESETS:
            self.control(panel._preset(name))["command"]()
        self.control(panel.COLLIDER_RADIUS)["changeCommand"]()
        self.control(panel.COLLIDER_LENGTH)["changeCommand"]()
        for attr, *_rest in setup.WIND_CHANNELS:
            self.control(panel._wind_slider(attr))["changeCommand"]()
        for name in (panel.LOOP_CHIP, panel.PREROLL, panel.SUBSTEPS):
            self.control(name)["changeCommand"]()
        self.assertEqual(self.pressed,
                         [("apply_preset", n) for n in model.PRESETS]
                         + [("collider_changed", "radius"), ("collider_changed", "length")]
                         + [("wind_changed", a) for a, *_r in setup.WIND_CHANNELS]
                         + [("option_changed", "loop"), ("option_changed", "preroll"),
                            ("option_changed", "substeps")])

    def test_the_list_and_the_buttons(self):
        self.assertIs(self.control(panel.CHAINS)["selectCommand"], panel.list_picked)
        self.assertIs(self.control(panel.ADD_BTN)["command"], panel.press_add_chain)
        self.assertIs(self.control(panel.REMOVE_BTN)["command"], panel.press_remove)
        commands = [self.ui.controls[n].get("command") for n in self.ui.order
                    if self.ui.controls[n]["kind"] == "button"]
        for press in (panel.press_auto_body, panel.press_sphere, panel.press_capsule,
                      panel.press_floor, panel.press_wind, panel.press_simulate):
            self.assertIn(press, commands)
        roles = dict((m.name, m.role) for m in self.marks)
        self.assertEqual(roles[panel.REMOVE_BTN], "danger")
        self.assertEqual(roles[panel.ADD_BTN], "secondary")


class Jobs(Base):

    def test_three_jobs_on_the_status_line(self):
        self.build()
        jobs = panel.JOB[""]
        events = [self.ui.jobs[j][0] for j in jobs]
        self.assertEqual([e[0] for e in events], ["SelectionChanged", "Undo", "Redo"])
        self.assertTrue(all(e[1]._skeldar_seen == (panel.STATUS, panel.refresh) for e in events))
        self.assertTrue(all(self.ui.jobs[j][1] == panel.STATUS for j in jobs))
        self.assertTrue(panel.is_open())

    def test_a_rebuild_kills_the_old_ones_and_a_copy_has_its_own(self):
        self.build()
        first = list(panel.JOB[""])
        self.build()
        self.assertEqual(self.ui.killed, first)
        scope = hubcopy.new_scope("dynamics")
        with hubcopy.entered(scope):
            self.assertEqual(panel._card_key(), scope.tag)
            panel.start()
            panel._set_picked(["|g|hair_dyn"])
        self.assertEqual(len(panel.JOB[scope.tag]), 3)
        self.assertEqual(panel.picked(), [])            # the hub's card picks nothing
        hubcopy.close(scope, cmds=self.ui)
        panel.start()
        self.assertNotIn(scope.tag, panel.JOB)

    def test_a_job_maya_will_not_kill_does_not_stop_the_start(self):
        self.build()

        def stubborn(*args, **kw):
            if kw.get("exists") is not None:
                raise RuntimeError("no")
            return 7
        self.ui.scriptJob = stubborn
        panel.start()
        self.assertEqual(panel.JOB[""], [7, 7, 7])


class Edges(Base):

    def test_a_broken_memory_is_the_defaults(self):
        self.ui.optionvars[panel.OPTION] = "{broken"
        self.assertEqual(panel.remembered(), model.settings({}))
        self.ui.optionvars[panel.OPTION] = json.dumps([1, 2])
        self.assertEqual(panel.remembered(), model.settings({}))

    def test_a_card_without_the_collider_fields_skips_them(self):
        self.build()
        del self.ui.controls[panel.COLLIDER_RADIUS]
        self.ui.attrs.update({"|b_capsule_col.radius": 2.0, "|b_capsule_col.length": 12.0})
        self.ui.selection = ["|b_capsule_col"]
        panel._collider_fields()
        self.assertEqual(self.control(panel.COLLIDER_LENGTH)["value"], 12.0)

    def test_jobs_maya_will_not_make_leave_none(self):
        def refused(*args, **kw):
            if kw.get("exists") is not None:
                return False
            raise RuntimeError("no UI")
        self.ui.scriptJob = refused
        self.build()
        self.assertEqual(panel.JOB[""], [])


class Window(unittest.TestCase):

    def test_show_window_opens_the_hub_on_dynamics(self):
        import maya_hub
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key) or "hub"
        try:
            self.assertEqual(panel.show_window(), "hub")
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["dynamics"])


if __name__ == "__main__":
    unittest.main()
