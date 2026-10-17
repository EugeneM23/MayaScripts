"""A portrait dropped on a character swaps it (2026-10-17): the pure halves of `swap`.

The scene half is proved by docs/superpowers/plans/verify_character_swap.py in mayapy
standalone."""

import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    maya.cmds = cmds
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds


_install_fake_maya()

from maya_scenesetup import swap  # noqa: E402


class Pure(unittest.TestCase):

    def test_the_take_range_covers_playback_animation_and_keys(self):
        self.assertEqual(swap.take_range((10, 40), (0, 50), [-3.5, 61.2]), (-4.0, 62.0))
        self.assertEqual(swap.take_range((10, 40), (0, 50), []), (0.0, 50.0))

    def test_the_nearest_bone_within_the_limit(self):
        bones = {"hand_r": (0, 0, 0), "lowerarm_r": (20, 0, 0)}
        self.assertEqual(swap.nearest((1, 0, 0), bones), "hand_r")
        self.assertIsNone(swap.nearest((10, 0, 0), bones))

    def test_a_bone_maps_by_its_leaf_same_kind(self):
        new = {"hand_r": "|Manny_Rig:root|...|Manny_Rig:hand_r"}
        self.assertEqual(swap.map_target("bone", "|root|pelvis|hand_r", "rig", new, {}),
                         (new["hand_r"], True))
        self.assertEqual(swap.map_target("bone", "|root|tail_01", "rig", new, {}), (None, False))

    def test_a_control_onto_a_rig_by_leaf_onto_a_skeleton_by_its_nearest_bone(self):
        bones = {"hand_r": "|root|hand_r"}
        controls = {"FKWrist_R": "Creep_Rig:FKWrist_R"}
        self.assertEqual(swap.map_target("control", "Manny_Rig:FKWrist_R", "rig", bones, controls),
                         ("Creep_Rig:FKWrist_R", True))
        self.assertEqual(swap.map_target("control", "Manny_Rig:FKWrist_R", "skeleton", bones, {},
                                         near_bone="hand_r"), ("|root|hand_r", False))
        self.assertEqual(swap.map_target("control", "Manny_Rig:PoleArm_R", "skeleton", bones, {}),
                         (None, False))

    def test_a_carried_weapon_maps_onto_its_new_node(self):
        self.assertEqual(swap.map_target("weapon", "|old|Sword", "rig", {}, {},
                                         weapons={"|old|Sword": "|new|Sword"}),
                         ("|new|Sword", True))
        self.assertEqual(swap.map_target("other", "|old|knot", "rig", {}, {}), (None, False))

    def test_the_line_names_what_was_carried_rebound_and_baked(self):
        line = swap.swap_line("root (skeleton)", "Manny_Rig", "stretch - twin", ["Long Sword"],
                              ["cube"], ["knotted"], "Deleted root - 900 nodes.")
        self.assertEqual(line, "root (skeleton) swapped for Manny_Rig  |  stretch - twin  |  "
                               "carried: Long Sword  |  re-bound to it: cube  |  "
                               "baked in place: knotted  |  Deleted root - 900 nodes.")
        self.assertEqual(swap.swap_caption("root", "Creep [rig]"), "swap root for Creep [rig]")


if __name__ == "__main__":
    unittest.main()
