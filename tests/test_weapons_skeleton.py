"""Tests for picking the character and finding the bone inside it.

The decision itself is a pure function over data -- which picker binding,
which selection, which scene roots -- so it is exercised without Maya. The
thin wrappers that read those three things out of the scene are proved live by
docs/superpowers/plans/verify_weapons.py.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let skeleton import without Maya. See CLAUDE.md on rebinding."""
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

from maya_weapons import skeleton  # noqa: E402

MANNY = "|SKM_Manny|root"
SUIT = "|Mesh_protective_suit|root"


class ChooseRoot(unittest.TestCase):

    def test_the_picker_wins_when_it_is_bound(self):
        """The point of the module: the same character the picker drives."""
        self.assertEqual(
            skeleton.choose_root(MANNY, [SUIT], [MANNY, SUIT]), MANNY)

    def test_selection_answers_when_the_picker_is_closed(self):
        self.assertEqual(
            skeleton.choose_root(None, [SUIT], [MANNY, SUIT]), SUIT)

    def test_several_joints_of_one_character_are_one_answer(self):
        """find_root maps every selected bone to the same root."""
        self.assertEqual(
            skeleton.choose_root(None, [MANNY, MANNY, MANNY], [MANNY, SUIT]),
            MANNY)

    def test_two_characters_selected_is_no_answer(self):
        """Arming the wrong character in silence is worse than saying no."""
        self.assertIsNone(
            skeleton.choose_root(None, [MANNY, SUIT], [MANNY, SUIT]))

    def test_a_lone_skeleton_answers_with_nothing_selected(self):
        self.assertEqual(skeleton.choose_root(None, [], [MANNY]), MANNY)

    def test_two_skeletons_and_no_hint_is_no_answer(self):
        self.assertIsNone(skeleton.choose_root(None, [], [MANNY, SUIT]))

    def test_an_empty_scene_is_no_answer(self):
        self.assertIsNone(skeleton.choose_root(None, [], []))

    def test_selection_outside_any_skeleton_is_ignored(self):
        """naming.find_root returns None for a light or a mesh."""
        self.assertEqual(skeleton.choose_root(None, [None, None], [MANNY]),
                         MANNY)


class BoneIn(unittest.TestCase):

    def test_finds_the_bone(self):
        hierarchy = {"root": MANNY, "weapon_r": MANNY + "|weapon_r"}
        self.assertEqual(skeleton.bone_in(hierarchy, "weapon_r"),
                         MANNY + "|weapon_r")

    def test_is_none_when_the_skeleton_has_no_such_bone(self):
        """A UE4-schema rig may carry no weapon bone at all."""
        self.assertIsNone(skeleton.bone_in({"root": MANNY}, "weapon_r"))

    def test_reads_a_namespaced_hierarchy(self):
        """hierarchy_map strips namespaces from the keys, not the values."""
        hierarchy = {"weapon_r": "|hero:root|hero:weapon_r"}
        self.assertEqual(skeleton.bone_in(hierarchy, "weapon_r"),
                         "|hero:root|hero:weapon_r")
