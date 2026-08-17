"""Tests for the aim manifest.

The scene-touching half is proved by docs/superpowers/plans/verify_weapon_aim.py.
What is testable here is the resolution: which aim a selection means, and what
it must never mean.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let aimrig import without a Maya session.

    Real modules win when they are importable -- under mayapy they always are,
    and aimrig reaches maya_overrig.builder, which needs maya.api.OpenMaya as
    well. The fakes below are only for an interpreter with no Maya at all.
    """
    try:
        import maya.api.OpenMaya  # noqa: F401
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass

    maya = types.ModuleType("maya")
    api = types.ModuleType("maya.api")
    openmaya = types.ModuleType("maya.api.OpenMaya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    maya.api = api
    api.OpenMaya = openmaya
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.api"] = api
    sys.modules["maya.api.OpenMaya"] = openmaya
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_overrig import aimrig  # noqa: E402


class Naming(unittest.TestCase):

    def test_the_set_is_prefixed(self):
        self.assertTrue(
            aimrig.set_name("LongSword_02").startswith(aimrig.SET_PREFIX))

    def test_the_key_is_in_the_name(self):
        self.assertIn("LongSword_02", aimrig.set_name("LongSword_02"))


class Normalise(unittest.TestCase):
    """A viewport click on the sword gives its transform; the outliner can give
    the shape. Both have to mean the same aim."""

    def test_a_shape_becomes_its_transform(self):
        self.assertEqual(
            aimrig.normalise(["|carrier|sword|swordShape"],
                             {"|carrier|sword|swordShape": "|carrier|sword"}),
            ["|carrier|sword"])

    def test_a_transform_is_left_alone(self):
        self.assertEqual(aimrig.normalise(["|carrier|sword"], {}),
                         ["|carrier|sword"])

    def test_duplicates_collapse(self):
        self.assertEqual(aimrig.normalise(["|a|s", "|a"], {"|a|s": "|a"}),
                         ["|a"])

    def test_order_is_kept(self):
        self.assertEqual(aimrig.normalise(["|b", "|a"], {}), ["|b", "|a"])

    def test_empty(self):
        self.assertEqual(aimrig.normalise([], {}), [])


class SetsHit(unittest.TestCase):
    """Exact match, never a descendant walk.

    After Connect the IK hand controls are DAG children of the sword geometry,
    so "descendant of the source" would resolve a hand-control click into the
    aim and Bake+Delete would take the wrong rig. That is trap 34 from a third
    side, and the safe direction of failure here is "nothing happens".
    """

    TABLE = [("RigPicker_aim_LongSword_02",
              ["|c|sword", "|c"],
              ["|sword_top", "|sword_side", "|c|sword|aimConstraint1"])]

    def test_the_source_hits(self):
        self.assertEqual(aimrig.sets_hit(["|c|sword"], self.TABLE),
                         ["RigPicker_aim_LongSword_02"])

    def test_the_carrier_hits(self):
        self.assertEqual(aimrig.sets_hit(["|c"], self.TABLE),
                         ["RigPicker_aim_LongSword_02"])

    def test_a_locator_hits(self):
        self.assertEqual(aimrig.sets_hit(["|sword_top"], self.TABLE),
                         ["RigPicker_aim_LongSword_02"])

    def test_the_constraint_hits(self):
        self.assertEqual(
            aimrig.sets_hit(["|c|sword|aimConstraint1"], self.TABLE),
            ["RigPicker_aim_LongSword_02"])

    def test_an_ik_hand_riding_the_sword_does_not_hit(self):
        self.assertEqual(
            aimrig.sets_hit(["|c|sword|hand_r_IK_feet"], self.TABLE), [])

    def test_an_unrelated_node_does_not_hit(self):
        self.assertEqual(aimrig.sets_hit(["|root|pelvis"], self.TABLE), [])

    def test_a_name_that_merely_starts_the_same_does_not_hit(self):
        """|c|swordExtra is not |c|sword, and never a child of it either."""
        self.assertEqual(aimrig.sets_hit(["|c|swordExtra"], self.TABLE), [])

    def test_two_aims_stay_apart(self):
        table = self.TABLE + [("RigPicker_aim_LongSword_021",
                               ["|c2|sword", "|c2"], ["|sword_top1"])]
        self.assertEqual(aimrig.sets_hit(["|sword_top1"], table),
                         ["RigPicker_aim_LongSword_021"])

    def test_one_selection_can_hit_both(self):
        table = self.TABLE + [("RigPicker_aim_LongSword_021",
                               ["|c2|sword", "|c2"], ["|sword_top1"])]
        self.assertEqual(aimrig.sets_hit(["|c|sword", "|sword_top1"], table),
                         ["RigPicker_aim_LongSword_02",
                          "RigPicker_aim_LongSword_021"])

    def test_nothing_selected_hits_nothing(self):
        self.assertEqual(aimrig.sets_hit([], self.TABLE), [])

    def test_no_aims_in_the_scene(self):
        self.assertEqual(aimrig.sets_hit(["|c|sword"], []), [])


if __name__ == "__main__":
    unittest.main()
