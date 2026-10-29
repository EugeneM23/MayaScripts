"""What is picked in the Connections card but not applied yet (2026-10-29).

The animator: «нужно сделать консистентно что бы перепекание происходило по
нажатию кнопки а не по разному в каждом разделе». Pure: the keys, the store
per rig, what a press counts as one change, and the line the status says.

Spec: docs/superpowers/specs/2026-10-29-connections-pick-then-apply-design.md
"""

import os
import subprocess
import sys
import unittest

from maya_scenesetup import pending

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")


class Keys(unittest.TestCase):

    def test_the_keys_are_spelled_once(self):
        self.assertEqual(pending.limb_key("Arm", "R"), "limb:Arm:R")
        self.assertEqual(pending.world_key("Leg", "L"), "world:Leg:L")
        self.assertEqual(pending.parent_key("W"), "parent:W")
        self.assertEqual((pending.SPINE, pending.AIM, pending.CAMERA,
                          pending.CAMERA_POSITION, pending.CAMERA_AIM),
                         ("spine", "aim", "camera", "camera:position", "camaim"))


class Record(unittest.TestCase):

    def test_a_pick_is_kept_and_the_dict_given_back_is_new(self):
        picks = {}
        out = pending.record(picks, "limb:Arm:R", "FK", "IK")
        self.assertEqual(out, {"limb:Arm:R": "FK"})
        self.assertEqual(picks, {})

    def test_a_pick_that_is_already_the_state_is_no_pick(self):
        out = pending.record({"limb:Arm:R": "FK"}, "limb:Arm:R", "IK", "IK")
        self.assertEqual(out, {})

    def test_a_pick_over_a_pick_replaces_it(self):
        out = pending.record({"limb:Arm:R": "FK"}, "limb:Arm:R", "IK", "FK")
        self.assertEqual(out, {"limb:Arm:R": "IK"})

    def test_a_false_pick_against_a_true_state_is_kept(self):
        #  W off while the limb IS in world: False is a pick, not an absence
        out = pending.record({}, "world:Arm:R", False, True)
        self.assertEqual(out, {"world:Arm:R": False})

    def test_without_drops_the_keys_named(self):
        out = pending.without({"a": 1, "b": 2, "c": 3}, "b", "zz")
        self.assertEqual(out, {"a": 1, "c": 3})


class Store(unittest.TestCase):

    def setUp(self):
        pending.clear()
        self.addCleanup(pending.clear)

    def test_one_set_per_rig(self):
        pending.set_for("Manny_Rig", {"spine": "IK"})
        pending.set_for("Creep_Rig", {"aim": True})
        self.assertEqual(pending.for_rig("Manny_Rig"), {"spine": "IK"})
        self.assertEqual(pending.for_rig("Creep_Rig"), {"aim": True})
        self.assertEqual(pending.for_rig("nobody"), {})

    def test_for_rig_hands_back_a_copy(self):
        pending.set_for("", {"spine": "IK"})
        got = pending.for_rig("")
        got["spine"] = "FK"
        self.assertEqual(pending.for_rig(""), {"spine": "IK"})

    def test_an_empty_set_forgets_the_rig(self):
        pending.set_for("Manny_Rig", {"spine": "IK"})
        pending.set_for("Manny_Rig", {})
        self.assertEqual(pending.for_rig("Manny_Rig"), {})

    def test_only_keeps_one_rig_s_picks(self):
        pending.set_for("Manny_Rig", {"spine": "IK"})
        pending.set_for("Creep_Rig", {"aim": True})
        pending.only("Creep_Rig")
        self.assertEqual(pending.for_rig("Manny_Rig"), {})
        self.assertEqual(pending.for_rig("Creep_Rig"), {"aim": True})


class Units(unittest.TestCase):
    """What a press does: a limb's mode and its W are ONE change."""

    def test_a_limb_s_mode_and_its_world_count_once(self):
        picks = {"limb:Arm:R": "IK", "world:Arm:R": True}
        self.assertEqual(pending.count(picks), 1)

    def test_the_camera_s_parent_and_its_position_count_once(self):
        picks = {"camera": "Chest", "camera:position": True}
        self.assertEqual(pending.count(picks), 1)

    def test_every_other_pick_counts_on_its_own(self):
        picks = {"limb:Arm:R": "FK", "limb:Leg:L": "IK", "spine": "IK",
                 "parent:L": "Weapon", "aim": True}
        self.assertEqual(pending.count(picks), 5)


class Tabs(unittest.TestCase):

    def test_each_tab_sees_only_its_own_picks(self):
        picks = {"limb:Arm:R": "FK", "world:Leg:L": True, "spine": "IK",
                 "parent:W": "Hand_L", "aim": True,
                 "camera": "Chest", "camera:position": True, "camaim": False}
        self.assertEqual(sorted(pending.of_tab(picks, "body")),
                         ["limb:Arm:R", "spine", "world:Leg:L"])
        self.assertEqual(sorted(pending.of_tab(picks, "weapon")),
                         ["aim", "parent:W"])
        self.assertEqual(sorted(pending.of_tab(picks, "camera")),
                         ["camaim", "camera", "camera:position"])
        self.assertEqual(pending.of_tab(picks, "object"), {})


class Text(unittest.TestCase):

    def test_a_phrase_a_pick(self):
        self.assertEqual(pending.phrase("limb:Arm:R", "FK"), "Arm R to FK")
        self.assertEqual(pending.phrase("world:Leg:L", True), "Leg L into world")
        self.assertEqual(pending.phrase("world:Leg:L", False), "Leg L out of world")
        self.assertEqual(pending.phrase("spine", "IK"), "the spine to IK")
        self.assertEqual(pending.phrase("parent:L", "Weapon"),
                         "the left hand to Weapon")
        self.assertEqual(pending.phrase("parent:W", "Hand_L"),
                         "the weapon to Hand L")
        self.assertEqual(pending.phrase("aim", True), "the weapon's aim on")
        self.assertEqual(pending.phrase("camera", "Chest"), "the camera to Chest")
        self.assertEqual(pending.phrase("camera:position", True),
                         "the camera's follow position only")
        self.assertEqual(pending.phrase("camaim", False), "the camera's aim off")

    def test_the_line_is_in_a_stable_order(self):
        picks = {"spine": "IK", "limb:Leg:L": "IK", "aim": True,
                 "limb:Arm:R": "FK"}
        self.assertEqual(pending.text(picks),
                         "Arm R to FK, Leg L to IK, the spine to IK, "
                         "the weapon's aim on")

    def test_no_picks_no_line(self):
        self.assertEqual(pending.text({}), "")


class MayaFreeBoundary(unittest.TestCase):
    """pending must stay importable with no Maya and no Qt loaded.

    Checked in a fresh interpreter: by the time the rest of the suite has run,
    maya.cmds is already in this process's sys.modules.
    """

    def test_importing_pending_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "from maya_scenesetup import pending\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide6')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PLUGIN, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing pending leaked: " + result.stdout.strip())
