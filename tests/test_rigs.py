"""Tests for maya_rigs: which rig, decided over data.

The scene half (`rigs()`, `rig_paths`, `current_rig`) is proved by
docs/superpowers/plans/verify_many_rigs.py in mayapy standalone; the
decisions are pure and live here.
"""

import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    maya.cmds = cmds
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds


_install_fake_maya()

import maya_rigs  # noqa: E402
from maya_rigs import Rig  # noqa: E402

LEGACY = Rig("", "ControlSet", "|Group|MotionSystem|MainSystem|Main", "|Group", "|root")
A = Rig("Manny_Rig", "Manny_Rig:ControlSet",
        "|Manny_Rig:Group|Manny_Rig:MotionSystem|Manny_Rig:MainSystem|Manny_Rig:Main",
        "|Manny_Rig:Group", "|Manny_Rig:root")
B = Rig("Manny_Rig1", "Manny_Rig1:ControlSet",
        "|Manny_Rig1:Group|Manny_Rig1:MotionSystem|Manny_Rig1:MainSystem|Manny_Rig1:Main",
        "|Manny_Rig1:Group", "|Manny_Rig1:root")


class NamespaceOf(unittest.TestCase):

    def test_a_namespaced_path(self):
        self.assertEqual(maya_rigs.namespace_of(A.main), "Manny_Rig")

    def test_the_root_namespace_is_empty(self):
        self.assertEqual(maya_rigs.namespace_of("|Group|Main"), "")
        self.assertEqual(maya_rigs.namespace_of("ControlSet"), "")

    def test_a_nested_namespace_is_kept_whole(self):
        self.assertEqual(maya_rigs.namespace_of("|clip:mixamorig:Hips|clip:mixamorig:Spine"),
                         "clip:mixamorig")

    def test_only_the_leaf_decides(self):
        """A plain node under a namespaced parent is in the root namespace."""
        self.assertEqual(maya_rigs.namespace_of("|a:root|pelvis"), "")


class Node(unittest.TestCase):

    def test_a_rigs_node_wears_its_namespace(self):
        self.assertEqual(maya_rigs.node(A, "FKWrist_R"), "Manny_Rig:FKWrist_R")

    def test_the_root_namespace_rig_keeps_plain_names(self):
        """The identity case: every legacy scene, and every name the modules
        used before rigs had namespaces."""
        self.assertEqual(maya_rigs.node(LEGACY, "MoCapConstraints"), "MoCapConstraints")

    def test_a_bare_namespace_string_works_too(self):
        self.assertEqual(maya_rigs.node("x", "Main"), "x:Main")
        self.assertEqual(maya_rigs.node("", "Main"), "Main")
        self.assertEqual(maya_rigs.node(None, "Main"), "Main")


class Label(unittest.TestCase):

    def test_a_namespace_names_the_rig(self):
        self.assertEqual(maya_rigs.label(A), "Manny_Rig")

    def test_the_legacy_rig_is_named_by_its_group(self):
        self.assertEqual(maya_rigs.label(LEGACY), "Group")


class RigOf(unittest.TestCase):
    RIGS = [LEGACY, A, B]

    def test_a_control_by_namespace(self):
        self.assertIs(maya_rigs.rig_of("|Manny_Rig1:Group|Manny_Rig1:FKWrist_R", self.RIGS), B)

    def test_a_mesh_of_a_namespaced_rig_counts(self):
        """The namespace is the mark; a mesh has it as much as a control does."""
        self.assertIs(maya_rigs.rig_of("|Manny_Rig:SKM_Manny_Simple|Manny_Rig:Skin_3p", self.RIGS), A)

    def test_a_bone_of_the_game_skeleton(self):
        self.assertIs(maya_rigs.rig_of("|Manny_Rig:root|Manny_Rig:pelvis", self.RIGS), A)

    def test_the_legacy_rig_by_group_and_by_skeleton(self):
        self.assertIs(maya_rigs.rig_of("|Group|MotionSystem|MainSystem|Main", self.RIGS), LEGACY)
        self.assertIs(maya_rigs.rig_of("|root|pelvis|spine_01", self.RIGS), LEGACY)
        self.assertIs(maya_rigs.rig_of("|Group", self.RIGS), LEGACY)

    def test_a_legacy_mesh_is_nobodys(self):
        self.assertIsNone(maya_rigs.rig_of("|SKM_Manny_Simple|Skin_3p", self.RIGS))

    def test_a_clips_skeleton_is_nobodys(self):
        self.assertIsNone(maya_rigs.rig_of("|clip:root|clip:pelvis", self.RIGS))
        self.assertIsNone(maya_rigs.rig_of("|root1|pelvis", self.RIGS))

    def test_a_group_that_merely_shares_the_prefix_is_not_inside(self):
        self.assertIsNone(maya_rigs.rig_of("|Group_extra|thing", self.RIGS))

    def test_no_rigs_no_answer(self):
        self.assertIsNone(maya_rigs.rig_of(A.main, []))


class ChooseRig(unittest.TestCase):

    def test_the_selections_rig_wins(self):
        self.assertEqual(maya_rigs.choose_rig([B, None, B], [A, B]), (B, ""))

    def test_the_sole_rig_answers_with_nothing_selected(self):
        self.assertEqual(maya_rigs.choose_rig([None], [A]), (A, ""))
        self.assertEqual(maya_rigs.choose_rig([], [A]), (A, ""))

    def test_two_rigs_selected_is_no_answer(self):
        rig, why = maya_rigs.choose_rig([A, B], [A, B])
        self.assertIsNone(rig)
        self.assertIn("Manny_Rig, Manny_Rig1", why)

    def test_several_rigs_and_nothing_selected_names_them(self):
        rig, why = maya_rigs.choose_rig([None], [LEGACY, A])
        self.assertIsNone(rig)
        self.assertIn("2 rigs", why)
        self.assertIn("Group, Manny_Rig", why)
        self.assertIn("select", why)

    def test_no_rig_at_all_is_the_standing_message(self):
        self.assertEqual(maya_rigs.choose_rig([], []), (None, maya_rigs.NO_RIG))
        self.assertIn("ControlSet/Main", maya_rigs.NO_RIG)


class Shallowest(unittest.TestCase):

    def test_topmost_then_by_name(self):
        self.assertEqual(maya_rigs.shallowest(["|b|c", "|a|x", "|a"]), "|a")
        self.assertEqual(maya_rigs.shallowest(["|b", "|a"]), "|a")

    def test_nothing_is_empty(self):
        self.assertEqual(maya_rigs.shallowest([]), "")

    def test_top_of(self):
        self.assertEqual(maya_rigs.top_of(A.main), "|Manny_Rig:Group")
        self.assertEqual(maya_rigs.top_of("|Group"), "|Group")


if __name__ == "__main__":
    unittest.main()
