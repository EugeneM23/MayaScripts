"""Tests for picking the character and finding the bone inside it.

The decision itself is a pure function over data -- what the selection
means, whether a rig stands, which scene roots exist -- so it is exercised
without Maya. The thin wrappers that read those things out of the scene are
proved live by docs/superpowers/plans/verify_weapons.py and, since
2026-09-07, by verify_rig_pipeline.py.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let skeleton import without Maya. See CLAUDE.md on rebinding.

    Real modules win when they are importable -- under mayapy they always
    are. Guarding on `"maya.cmds" in sys.modules` alone is not enough: run
    first, this module would install a fake `maya` that is not a package and
    shadow the real one for every test module loaded after it.
    """
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import skeleton  # noqa: E402

MANNY = "|SKM_Manny|root"
SUIT = "|Mesh_protective_suit|root"
RIG = "|root"                 # the game skeleton the AdvancedSkeleton rig drives
GROUP = "|Group"              # the rig's own top group
CLIP = "|clip:root"           # an imported clip's skeleton

JOINTS = {
    "|clip:root|clip:pelvis": CLIP,
    "|clip:root": CLIP,
    "|root|pelvis|spine_01": RIG,
    "|SKM_Manny|root|pelvis": MANNY,
}


def top_joint(path):
    """The injected scene question: a joint's topmost joint, else None."""
    return JOINTS.get(path)


class SelectionRoots(unittest.TestCase):
    """What a selected path means (2026-09-07: «достаточно выделить любой
    контрол персонажа»)."""

    def test_a_control_means_the_rigs_skeleton(self):
        roots = skeleton.selection_roots(
            ["|Group|MotionSystem|FKSystem|FKWrist_R"], GROUP, RIG, top_joint)
        self.assertEqual(roots, [RIG])

    def test_the_group_itself_means_the_rigs_skeleton(self):
        self.assertEqual(skeleton.selection_roots([GROUP], GROUP, RIG,
                                                  top_joint), [RIG])

    def test_a_joint_means_its_top_joint(self):
        roots = skeleton.selection_roots(["|clip:root|clip:pelvis"], GROUP,
                                         RIG, top_joint)
        self.assertEqual(roots, [CLIP])

    def test_the_rigs_own_joint_means_the_rig_too(self):
        roots = skeleton.selection_roots(["|root|pelvis|spine_01"], GROUP,
                                         RIG, top_joint)
        self.assertEqual(roots, [RIG])

    def test_a_mesh_or_a_locator_means_nothing(self):
        roots = skeleton.selection_roots(["|Skin_3p", "|locator1"], GROUP,
                                         RIG, top_joint)
        self.assertEqual(roots, [None, None])

    def test_a_group_that_merely_shares_the_prefix_is_not_inside(self):
        """`|Group1|...` is not under `|Group`: the separator counts."""
        roots = skeleton.selection_roots(["|Group1|thing"], GROUP, RIG,
                                         top_joint)
        self.assertEqual(roots, [None])

    def test_without_a_rig_a_control_path_is_nothing(self):
        roots = skeleton.selection_roots(
            ["|Group|MotionSystem|FKSystem|FKWrist_R"], None, None, top_joint)
        self.assertEqual(roots, [None])

    def test_inside_is_the_separator_aware_prefix_test(self):
        self.assertTrue(skeleton.inside("|Group|a", "|Group"))
        self.assertTrue(skeleton.inside("|Group", "|Group"))
        self.assertFalse(skeleton.inside("|Group1|a", "|Group"))
        self.assertFalse(skeleton.inside("|Group|a", None))
        self.assertFalse(skeleton.inside("|Group|a", ""))


class ChooseRoot(unittest.TestCase):
    """Selection, then the rig, then the only skeleton. Pure."""

    def test_selection_wins_over_the_rig(self):
        self.assertEqual(skeleton.choose_root([CLIP], RIG, [RIG, CLIP]), CLIP)

    def test_several_paths_of_one_character_are_one_answer(self):
        self.assertEqual(
            skeleton.choose_root([RIG, RIG, RIG], RIG, [RIG, CLIP]), RIG)

    def test_two_characters_selected_is_no_answer(self):
        self.assertIsNone(skeleton.choose_root([RIG, CLIP], RIG, [RIG, CLIP]))

    def test_the_rig_answers_with_nothing_selected(self):
        """Two skeletons in the scene -- the rig's and a clip's -- and no
        hint: the rig, because that is the character being worked on."""
        self.assertEqual(skeleton.choose_root([], RIG, [RIG, CLIP]), RIG)

    def test_a_lone_skeleton_answers_without_a_rig(self):
        self.assertEqual(skeleton.choose_root([], None, [MANNY]), MANNY)

    def test_two_skeletons_no_rig_and_no_hint_is_no_answer(self):
        self.assertIsNone(skeleton.choose_root([], None, [MANNY, SUIT]))

    def test_an_empty_scene_is_no_answer(self):
        self.assertIsNone(skeleton.choose_root([], None, []))

    def test_selection_outside_any_skeleton_is_ignored(self):
        """A mesh or locator selected beside a lone skeleton still resolves
        to that skeleton -- the selection said nothing, not "no"."""
        self.assertEqual(skeleton.choose_root([None, None], None, [MANNY]),
                         MANNY)
        self.assertEqual(skeleton.choose_root([None], RIG, [RIG]), RIG)


class BoneIn(unittest.TestCase):

    def test_finds_the_bone(self):
        hierarchy = {"root": "|SKM_Manny|root",
                     "weapon_r": "|SKM_Manny|root|pelvis|weapon_r"}
        self.assertEqual(skeleton.bone_in(hierarchy, "weapon_r"),
                         "|SKM_Manny|root|pelvis|weapon_r")

    def test_is_none_when_the_skeleton_has_no_such_bone(self):
        hierarchy = {"root": "|SKM_Manny|root"}
        self.assertIsNone(skeleton.bone_in(hierarchy, "weapon_r"))

    def test_reads_a_namespaced_hierarchy(self):
        hierarchy = {"weapon_r": "|suit:root|suit:weapon_r"}
        self.assertEqual(skeleton.bone_in(hierarchy, "weapon_r"),
                         "|suit:root|suit:weapon_r")


if __name__ == "__main__":
    unittest.main()
