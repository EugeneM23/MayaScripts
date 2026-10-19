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


# 2026-10-02: a character's outliner group above the rig's own AdvancedSkeleton group.
G = "|Manny_Rig2_Character"
C = Rig("Manny_Rig2", "Manny_Rig2:ControlSet",
        G + "|Manny_Rig2:Group|Manny_Rig2:MotionSystem|Manny_Rig2:MainSystem|Manny_Rig2:Main",
        G + "|Manny_Rig2:Group", G + "|Manny_Rig2:root", G)


class CharacterGroup(unittest.TestCase):

    def test_the_rigs_group_is_the_one_below_the_character_group(self):
        self.assertEqual(maya_rigs.top_below(C.main, {G}), G + "|Manny_Rig2:Group")

    def test_with_no_character_group_it_is_top_of(self):
        self.assertEqual(maya_rigs.top_below(A.main, {G}), "|Manny_Rig:Group")
        self.assertEqual(maya_rigs.top_below(A.main, set()), maya_rigs.top_of(A.main))

    def test_a_group_that_merely_shares_the_prefix_is_not_it(self):
        self.assertEqual(maya_rigs.top_below("|Manny_Rig2_CharacterX|a", {G}),
                         "|Manny_Rig2_CharacterX")

    def test_a_rig_made_before_has_no_character(self):
        self.assertEqual(A.character, "")
        self.assertEqual(Rig("", "ControlSet", "|Group|Main", "|Group", "|root").character, "")

    def test_the_character_group_and_its_loose_parts_are_the_rigs(self):
        rigs = [A, C]
        self.assertIs(maya_rigs.rig_of(G, rigs), C)
        self.assertIs(maya_rigs.rig_of(G + "|SceneSetup_camera", rigs), C)
        self.assertIs(maya_rigs.rig_of(G + "|Manny_Rig2:root|Manny_Rig2:pelvis", rigs), C)

    def test_another_characters_group_is_not_this_rigs(self):
        self.assertIsNone(maya_rigs.rig_of("|Manny_Skeleton_Character|root", [A, C]))

    def test_the_rig_group_is_still_outside_the_skeleton(self):
        self.assertFalse(maya_rigs.under(C.skeleton_root, C.group))
        self.assertTrue(maya_rigs.under(C.skeleton_root, C.character))


class SkeletonRootKept(unittest.TestCase):
    """2026-10-17, the performance pass: the root found once is checked, not looked for again -
    listing a rig's ~330 joints cost 3 ms a rig on every `rigs()`."""

    class Scene(object):
        def __init__(self, joints, constrained):
            self.joints = list(joints)
            self.constrained = set(constrained)
            self.scans = 0

        def ls(self, what, type=None, long=False, **_kw):     # noqa: A002
            if isinstance(what, str):                         # a namespace pattern: a scan
                self.scans += 1
                return list(self.joints)
            return [p for p in what if p in self.joints]

        def objExists(self, path):                            # noqa: N802
            return path in self.joints

        def objectType(self, path):                           # noqa: N802
            return "joint"

        def listRelatives(self, path, children=False, type=None, **_kw):   # noqa: A002
            return ["c"] if path in self.constrained else []

    ROOT = "|Manny_Rig_Character|Manny_Rig:root"
    PELVIS = ROOT + "|Manny_Rig:pelvis"
    GROUP = "|Manny_Rig_Character|Manny_Rig:Group"

    def setUp(self):
        self.saved = maya_rigs.cmds
        self.scene = self.Scene([self.ROOT, self.PELVIS, self.GROUP + "|Manny_Rig:Root_M"],
                                [self.ROOT, self.PELVIS])
        maya_rigs.cmds = self.scene
        maya_rigs._SKELETON_ROOTS.clear()

    def tearDown(self):
        maya_rigs.cmds = self.saved
        maya_rigs._SKELETON_ROOTS.clear()

    def test_the_root_is_found_once_and_then_kept(self):
        for _ in range(3):
            self.assertEqual(maya_rigs.skeleton_root_of("Manny_Rig", self.GROUP), self.ROOT)
        self.assertEqual(self.scene.scans, 1)

    def test_a_root_gone_or_no_longer_constrained_is_looked_for_again(self):
        maya_rigs.skeleton_root_of("Manny_Rig", self.GROUP)
        self.scene.constrained.discard(self.ROOT)
        self.assertEqual(maya_rigs.skeleton_root_of("Manny_Rig", self.GROUP), self.PELVIS)
        self.scene.joints.remove(self.ROOT)
        self.scene.joints.remove(self.PELVIS)
        self.assertEqual(maya_rigs.skeleton_root_of("Manny_Rig", self.GROUP), "")
        self.assertEqual(self.scene.scans, 3)

    def test_a_joint_of_the_rig_above_the_kept_root_is_looked_for_again(self):
        top = "|Manny_Rig:top"
        root = top + "|Manny_Rig:root"
        self.scene.joints = [root, root + "|Manny_Rig:pelvis"]
        self.scene.constrained = {root, top}
        self.assertEqual(maya_rigs.skeleton_root_of("Manny_Rig", self.GROUP), root)
        self.assertTrue(maya_rigs._still_root(root, "Manny_Rig", self.GROUP))
        self.scene.joints.insert(0, top)               # a constrained joint of the rig above it
        self.assertFalse(maya_rigs._still_root(root, "Manny_Rig", self.GROUP))
        self.assertEqual(maya_rigs.skeleton_root_of("Manny_Rig", self.GROUP), top)


class MarkedNearTop(unittest.TestCase):
    """2026-10-17: the marker groups near the top found with one `ls` of plugs and one
    listRelatives a level, not an attributeQuery a node."""

    class Scene(object):
        def __init__(self, children, marked):
            self.children = children          # path -> [child paths]
            self.marked = set(marked)
            self.calls = []

        def ls(self, what=None, assemblies=False, long=False, objectsOnly=False, **_kw):  # noqa: N803
            self.calls.append("ls")
            if assemblies:
                return list(self.children.get("", []))
            return [plug.rsplit(".", 1)[0] for plug in what if plug.rsplit(".", 1)[0] in self.marked]

        def listRelatives(self, nodes, children=False, type=None, fullPath=False):   # noqa: A002,N802
            self.calls.append("listRelatives")
            out = []
            for node in nodes:
                out += self.children.get(node, [])
            return out

        def attributeQuery(self, *a, **k):                    # noqa: N802
            raise AssertionError("one ls a level, not an attributeQuery a node")

    def setUp(self):
        self.saved = maya_rigs.cmds
        top = "|Manny_Rig_Character"
        group = top + "|Manny_Rig:Group"
        self.scene = self.Scene({"": [top, "|ArmorSpaces"],
                                 top: [group, top + "|Manny_Rig:root"],
                                 group: [group + "|ArmorSpaces", group + "|Manny_Rig:Geometry"],
                                 group + "|ArmorSpaces": [group + "|ArmorSpaces|deeper"]},
                                {"|ArmorSpaces", group + "|ArmorSpaces", group + "|ArmorSpaces|deeper"})
        maya_rigs.cmds = self.scene

    def tearDown(self):
        maya_rigs.cmds = self.saved

    def test_three_levels_two_calls_each(self):
        found = maya_rigs.marked_near_top("mayaArmorSpaces")
        self.assertEqual(found, ["|ArmorSpaces", "|Manny_Rig_Character|Manny_Rig:Group|ArmorSpaces"])
        self.assertEqual(self.scene.calls.count("listRelatives"), 2)
        self.assertEqual(self.scene.calls.count("ls"), 4)          # the assemblies + one a level

    def test_depth_two_stops_a_level_higher(self):
        self.assertEqual(maya_rigs.marked_near_top("m", depth=2), ["|ArmorSpaces"])


if __name__ == "__main__":
    unittest.main()
