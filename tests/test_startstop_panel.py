"""Start/Stop Builder (maya_startstop.panel): the hub card on a fake cmds - the knobs' memory (a side's own values,
each pose's Share x its parts), the run mode, the wells' cards, the presses on the working list, the build.

Spec: docs/superpowers/specs/2026-11-17-start-stop-builder-design.md"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

from maya_startstop import model, panel, scene  # noqa: E402
from maya_poselib import store                  # noqa: E402


class FakeCmds(object):
    """Just enough of maya.cmds for the card: records controls and their values, answers queries."""

    def __init__(self):
        self.vars = {}
        self.controls = {}          # name -> {"kind", values...}
        self.managed = {}
        self.selection = []
        self.uuids = {}
        self.jobs = 0
        self.list_rows = []
        self.list_picked = []

    # -- optionVar --
    def optionVar(self, exists=None, query=None, remove=None, floatValue=None, stringValue=None, intValue=None):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars.get(query, 0)
        if remove is not None:
            self.vars.pop(remove, None)
            return None
        for pair in (floatValue, stringValue, intValue):
            if pair is not None:
                self.vars[pair[0]] = pair[1]
        return None

    # -- controls --
    def _control(self, kind, name, exists, edit, query, kw):
        if exists:
            return name in self.controls
        if query:
            for key in ("value", "select", "label"):
                if kw.get(key):
                    return self.controls[name].get(key)
            return None
        if edit:
            self.controls[name].update(dict((k, v) for k, v in kw.items() if v is not None))
            return name
        record = dict(kind=kind)
        record.update(kw)
        self.controls[name or "%s%d" % (kind, len(self.controls))] = record
        return name

    def floatSliderGrp(self, name=None, exists=False, edit=False, query=False, **kw):
        return self._control("floatSliderGrp", name, exists, edit, query, kw)

    def checkBox(self, name=None, exists=False, edit=False, query=False, **kw):
        return self._control("checkBox", name, exists, edit, query, kw)

    def iconTextRadioButton(self, name=None, exists=False, edit=False, query=False, **kw):
        return self._control("iconTextRadioButton", name, exists, edit, query, kw)

    def text(self, name=None, exists=False, edit=False, query=False, **kw):
        return self._control("text", name, exists, edit, query, kw)

    def button(self, name=None, exists=False, edit=False, query=False, **kw):
        return self._control("button", name, exists, edit, query, kw)

    def columnLayout(self, name=None, exists=False, edit=False, manage=None, **kw):
        if exists:
            return name in self.managed
        if name:
            self.managed[name] = True if manage is None else manage
        return name or "column"

    def rowLayout(self, *a, **kw):
        return "row"

    def iconTextRadioCollection(self, *a, **kw):
        return a[0] if a else "collection"

    def setParent(self, *a, **kw):
        return None

    def popupMenu(self, *a, **kw):
        return "popup"

    def menuItem(self, *a, **kw):
        return "item"

    def textScrollList(self, name=None, exists=False, edit=False, query=False, removeAll=False, append=None,
                       selectIndexedItem=None, **kw):
        if exists:
            return name in self.controls
        if query:
            return list(self.list_picked)
        if edit:
            if removeAll:
                self.list_rows = []
            if append is not None:
                self.list_rows.append(append)
            if selectIndexedItem is not None:
                self.list_picked = list(selectIndexedItem)
            return name
        self.controls[name] = dict(kind="textScrollList")
        return name

    def scriptJob(self, *a, **kw):
        self.jobs += 1
        return self.jobs

    def ls(self, *names, **kw):
        if kw.get("selection"):
            return list(self.selection)
        flat = []
        for n in names:
            flat.extend([n] if isinstance(n, str) else list(n))
        if kw.get("uuid"):
            return [self.uuids.setdefault(n, "uuid-" + n) for n in flat]
        out = []
        for n in flat:
            for path, uuid in self.uuids.items():
                if n in (uuid, path):
                    out.append(path)
        return out

    def listRelatives(self, node, parent=False, **kw):
        if parent and node.count("|") > 1:
            return [node.rsplit("|", 1)[0]]
        return []

    def select(self, *a, **kw):
        return None

    def about(self, batch=False):
        return True

    def mayaDpiSetting(self, **kw):
        return 1.0


class Base(unittest.TestCase):
    def setUp(self):
        self.cmds = FakeCmds()
        self.patches = [mock.patch.object(panel, "_cmds", lambda: self.cmds),
                        mock.patch.object(scene, "_cmds", lambda: self.cmds)]
        for p in self.patches:
            p.start()
        scene._state()["working"] = []
        scene._state()["cycle"] = None
        self.said = []
        self.patches.append(mock.patch.object(panel, "_say", lambda text: self.said.append(text) or text))
        self.patches[-1].start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()


class Memory(Base):
    def test_the_defaults_are_the_models(self):
        k = panel.values()
        for name in panel.knob_names():
            self.assertEqual(k[name], model.DEFAULTS[name], name)
        for prefix in ("share", "start"):
            for part, _label in panel.PART_LABELS:
                self.assertEqual(k["%s_%s" % (prefix, part)], 1.0)

    def test_every_knob_of_the_card_is_the_models(self):
        self.assertEqual(sorted(panel.knob_names()),
                         sorted(n for n in model.DEFAULTS if not n.startswith(("share_", "start_"))))

    def test_a_poses_share_goes_to_its_lit_parts_only(self):
        panel._remember("standShare", 0.6)
        panel._remember("part_stand_arms", 0.0)
        panel._remember("runShare", 0.25)
        panel._remember("part_run_feet", 0.0)
        k = panel.values()
        self.assertAlmostEqual(k["share_torso"], 0.6)
        self.assertEqual(k["share_arms"], 0.0)
        self.assertAlmostEqual(k["start_pelvis"], 0.25)
        self.assertEqual(k["start_feet"], 0.0)

    def test_a_side_keeps_its_own_value_and_both_links_them_again(self):
        self.cmds.controls[panel._slider("lift")] = {"kind": "floatSliderGrp", "value": 2.5}
        panel._remember("side", "l")
        panel.knob_changed("lift")()
        k = model.sided(panel.values())
        self.assertAlmostEqual(k["l"]["lift"], 2.5)
        self.assertAlmostEqual(k["r"]["lift"], model.DEFAULTS["lift"])
        panel.show_side("both")
        self.assertTrue(self.cmds.controls[panel._slider("lift")]["label"].endswith("*"))
        self.cmds.controls[panel._slider("lift")]["value"] = 1.5
        panel.knob_changed("lift")()
        k = model.sided(panel.values())
        self.assertAlmostEqual(k["l"]["lift"], 1.5)
        self.assertAlmostEqual(k["r"]["lift"], 1.5)
        self.assertFalse(self.cmds.optionVar(exists=panel.OPTION + "lift_l"))

    def test_the_hold_chip_is_a_check_box_per_side(self):
        self.assertIn("weapon", [key for key, _label, _rows in panel.GROUPS])
        self.cmds.controls[panel._slider("weapon_hold")] = {"kind": "checkBox", "value": False}
        panel._remember("side", "r")
        panel.knob_changed("weapon_hold")()
        k = model.sided(panel.values())
        self.assertEqual(k["r"]["weapon_hold"], 0.0)
        self.assertEqual(k["l"]["weapon_hold"], 1.0)
        panel.show_side("both")
        self.assertTrue(self.cmds.controls[panel._slider("weapon_hold")]["label"].endswith("*"))
        panel.press_reset()
        self.assertTrue(self.cmds.controls[panel._slider("weapon_hold")]["value"])

    def test_reset_puts_every_knob_back_and_links_the_sides(self):
        panel._remember("bob", 2.0)
        panel._remember("lift_r", 2.0)
        panel._remember("standShare", 0.3)
        panel.press_reset()
        k = panel.values()
        self.assertEqual(k["bob"], model.DEFAULTS["bob"])
        self.assertFalse(self.cmds.optionVar(exists=panel.OPTION + "lift_r"))
        self.assertAlmostEqual(k["share_torso"], 0.3)        # the poses kept


class RunMode(Base):
    def test_the_run_mode_is_remembered_and_shows_the_run_well_for_a_card(self):
        self.assertEqual(panel.run_mode(), "stand")
        self.cmds.managed[panel.RUN_COLUMN] = False
        panel.run_changed("card")()
        self.assertEqual(panel.run_mode(), "card")
        self.assertTrue(self.cmds.managed[panel.RUN_COLUMN])
        panel.run_changed("clip")()
        self.assertFalse(self.cmds.managed[panel.RUN_COLUMN])
        panel._remember("runMode", "nonsense")
        self.assertEqual(panel.run_mode(), "stand")


class Wells(Base):
    def setUp(self):
        super(Wells, self).setUp()
        self.library = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.library, True)
        eye = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
        bones = {"root": {"parent": None, "canonical": "root", "rest": eye, "world": eye},
                 "pelvis": {"parent": "root", "canonical": "pelvis", "rest": eye, "world": eye}}
        data = {"format": store.FORMAT, "kind": "character", "bones": bones, "character": {"label": "x"},
                "members": sorted(bones), "objects": []}
        self.card = store.write(self.library, "", "goblin", data)
        self.anim = store.write(self.library, "", "walk", dict(data, format=store.ANIM_FORMAT))

    def test_a_card_dropped_into_a_well_is_its_active_pose(self):
        panel.take_card("stand", self.card)
        self.assertEqual(panel.chosen_card("stand"), self.card)
        self.assertEqual(panel.card_list("stand"), [self.card])
        self.assertIsNone(panel.chosen_card("run"))
        rows = panel.well_rows("stand")
        self.assertEqual(rows[0][0], self.card)
        self.assertTrue(rows[0][4])

    def test_a_card_in_the_run_well_makes_the_run_pose_the_card(self):
        panel.take_card("run", self.card)
        self.assertEqual(panel.run_mode(), "card")
        self.assertEqual(panel.chosen_card("run"), self.card)

    def test_an_animation_card_is_refused(self):
        panel.take_card("stand", self.anim)
        self.assertIsNone(panel.chosen_card("stand"))
        self.assertIn("animation card", self.said[-1])

    def test_removing_the_active_card_moves_on(self):
        panel.take_card("stand", self.card)
        panel.remove_card("stand", self.card)
        self.assertIsNone(panel.chosen_card("stand"))
        self.assertEqual(panel.card_list("stand"), [])

    def test_a_well_scene_answers_for_its_own_pose(self):
        stand, run = panel.WellScene("stand"), panel.WellScene("run")
        stand.take(self.card)
        self.assertEqual(len(stand.cards()), 1)
        self.assertEqual(run.cards(), [])


class Presses(Base):
    def test_apply_keys_the_selected_skeletons_and_makes_them_working(self):
        calls = []
        self.cmds.selection = ["|A_Character|root|pelvis"]
        with mock.patch.object(scene, "selected_tops", lambda: ["|A_Character|root"]), \
                mock.patch.object(scene, "apply", lambda *a: calls.append(a) or "keyed"), \
                mock.patch.object(scene, "built", lambda: []):
            panel._remember("standCard", "C:/lib/goblin.pose")
            panel._remember("runMode", "clip")
            line = panel.press_apply()
        self.assertEqual(line, "keyed")
        root, k, stand, mode, run = calls[0]
        self.assertEqual((root, stand, mode, run), ("|A_Character|root", "C:/lib/goblin.pose", "clip", None))
        self.assertEqual(k["bob"], model.DEFAULTS["bob"])
        self.assertEqual(panel.working(), ["|A_Character|root"])

    def test_a_knob_keys_the_working_ones_with_nothing_selected(self):
        calls = []
        self.cmds.uuids["|B_Character|root"] = "uuid-B"
        scene._state()["working"] = ["uuid-B"]
        self.cmds.controls[panel._slider("bob")] = {"kind": "floatSliderGrp", "value": 1.7}
        with mock.patch.object(scene, "apply", lambda *a: calls.append(a) or "rekeyed"), \
                mock.patch.object(scene, "built", lambda: []):
            line = panel.knob_changed("bob")()
        self.assertEqual(calls[0][0], "|B_Character|root")
        self.assertAlmostEqual(calls[0][1]["bob"], 1.7)
        self.assertIn("rekeyed", line)

    def test_a_refusal_lands_on_the_line(self):
        def refuse(*a):
            raise scene.Refusal("Run pose is Card: drop a pose card into the run well")
        with mock.patch.object(scene, "selected_tops", lambda: ["|A_Character|root"]), \
                mock.patch.object(scene, "apply", refuse), mock.patch.object(scene, "built", lambda: []):
            line = panel.press_apply()
        self.assertTrue(line.startswith("A: "), line)              # the skeleton's label, its character group
        self.assertIn("run well", line)

    def test_restore_gives_the_keys_back_and_leaves_the_list(self):
        restored = []
        self.cmds.uuids["|A_Character|root"] = "uuid-A"
        scene._state()["working"] = ["uuid-A"]
        with mock.patch.object(scene, "selected_tops", lambda: ["|A_Character|root"]), \
                mock.patch.object(scene, "has_source", lambda r: True), \
                mock.patch.object(scene, "restore", lambda r: restored.append(r) or "back"), \
                mock.patch.object(scene, "built", lambda: []):
            line = panel.press_restore()
        self.assertEqual(restored, ["|A_Character|root"])
        self.assertEqual(line, "back")
        self.assertEqual(panel.working(), [])

    def test_nothing_selected_and_nobody_working(self):
        with mock.patch.object(scene, "selected_tops", lambda: []):
            self.assertIn("Select", panel.press_apply())


class Build(Base):
    def test_the_card_builds_every_control(self):
        from maya_walk import posewell
        with mock.patch.object(posewell, "attach", lambda *a, **kw: None), \
                mock.patch.object(panel, "start", lambda: None), \
                mock.patch.object(scene, "selected_tops", lambda: []), \
                mock.patch.object(scene, "built", lambda: []):
            panel.build_panel()
        made = self.cmds.controls
        for name in (panel.SUBTITLE, panel.STATUS, panel.CYCLE_TEXT, panel.APPLY_BTN, panel.RESTORE_BTN,
                     panel.RESET_BTN, panel.CYCLE_BTN, panel.CLEAR_BTN, panel.LIST):
            self.assertIn(name, made, name)
        for name in panel.knob_names():
            self.assertIn(panel._slider(name), made, name)
        for which, _p, _w, _h in panel.POSES:
            self.assertIn(panel._share_slider(which), made)
            self.assertIn(panel._well_text(which), made)          # no Qt: the well's line
            for part, _l in panel.PART_LABELS:
                self.assertIn(panel._part_box(which, part), made)
        for key, _t, _r in panel.GROUPS:
            self.assertIn(panel._group_tab(key), made)
        self.assertFalse(self.cmds.managed[panel.RUN_COLUMN])      # Stand by default: no run well
        self.assertEqual(sum(1 for k in self.cmds.managed if k.startswith("skeldarStartStopGroup_") and
                             self.cmds.managed[k]), 1)             # one group shown
        self.assertIn("No cycle", made[panel.CYCLE_TEXT]["label"])

    def test_one_group_shown_at_a_time_and_remembered(self):
        for key, _t, _r in panel.GROUPS:
            self.cmds.managed[panel._group_column(key)] = True
        panel.show_group("arms")
        self.assertEqual([k for k, _t, _r in panel.GROUPS if self.cmds.managed[panel._group_column(k)]], ["arms"])
        self.assertEqual(panel._stored("group", ""), "arms")


class Hub(unittest.TestCase):
    def test_the_section_and_the_hotkey_rows(self):
        import maya_hub
        import maya_hotkeys
        sec = maya_hub.section("startstop")
        self.assertEqual((sec.label, sec.module, sec.group), ("Start/Stop Builder", "maya_startstop.panel",
                                                              "animation"))
        keys = [row[0] for row in maya_hotkeys._OURS]
        self.assertIn("window.startstop", keys)
        self.assertIn("startstop.apply", keys)

    def test_the_package_ships(self):
        import install
        self.assertIn("maya_startstop", install.payload())


if __name__ == "__main__":
    unittest.main()
