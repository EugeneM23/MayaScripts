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


class Parts(unittest.TestCase):
    """A part row dropped on a character keeps it (2026-10-27)."""

    def test_a_part_caption_names_the_body_part_and_keeps_the_character(self):
        self.assertEqual(swap.swap_caption("Manny_Rig", "Creep 2 Arm R [rig]", "spine_05"),
                         "Creep 2 Arm R [rig] onto Manny_Rig's right arm - Manny_Rig kept")
        self.assertIn("head", swap.swap_caption("root", "Creep 2 Head [skeleton]", "spine_05"))

    def test_the_part_line_never_says_deleted(self):
        line = swap.part_line("Creep2_Rig", "Creep2_Head_Rig", "rotations")
        self.assertEqual(line, "Creep2_Head_Rig on Creep2_Rig's head  |  rotations  |  "
                               "Creep2_Rig kept")

    def test_a_rig_line_reads_the_body_part_off_the_row(self):
        line = swap.part_line("Manny_Rig", "Creep2_ArmR_Rig1", "", "Creep 2 Arm R [rig]")
        self.assertTrue(line.startswith("Creep2_ArmR_Rig1 on Manny_Rig's right arm"))

    def test_a_part_skeleton_is_known_by_its_label(self):
        from maya_uebridge import skeletonimport
        self.assertTrue(skeletonimport._is_part("Creep 2 Head [skeleton] (root)"))
        self.assertFalse(skeletonimport._is_part("Manny UE5 [skeleton]"))

    def test_a_part_entry_never_reaches_the_delete(self):
        import inspect
        src = inspect.getsource(swap.swap)
        self.assertLess(src.index("attach_part"), src.index("deletion.execute"))
        self.assertNotIn("deletion", inspect.getsource(swap.attach_part))


if __name__ == "__main__":
    unittest.main()
