import sys
import types
import unittest


class FakeCmds(object):
    """A tiny DAG model standing in for maya.cmds.

    Nodes are long paths. Anything listed in `joints` reports as a joint;
    anything in `transforms` reports as a transform. UUIDs are faked as
    "uuid-of:<path>" so the round trip can be exercised.
    """

    def __init__(self, joints=(), transforms=()):
        self._joints = list(joints)
        self._transforms = list(transforms)

    def _all(self):
        return self._joints + self._transforms

    def objectType(self, node):
        return "joint" if node in self._joints else "transform"

    def listRelatives(self, node, parent=False, type=None, fullPath=False,
                      **kwargs):
        if not parent:
            return None
        head = node.rsplit("|", 1)[0]
        if not head:
            return None
        if type == "joint" and head not in self._joints:
            return None
        if head not in self._all():
            return None
        return [head]

    def ls(self, *args, **kwargs):
        if kwargs.get("uuid"):
            return ["uuid-of:" + args[0]] if args else []

        if args and str(args[0]).startswith("uuid-of:"):
            target = str(args[0])[len("uuid-of:"):]
            return [target] if target in self._all() else []

        pool = self._joints if kwargs.get("type") == "joint" else self._all()

        if args and kwargs.get("dagObjects"):
            root = args[0]
            return [n for n in pool if n == root or n.startswith(root + "|")]

        if args:
            return [n for n in pool if n == args[0]]

        return list(pool)


ONE_CHARACTER = FakeCmds(
    joints=[
        "|SKM_Manny|root",
        "|SKM_Manny|root|pelvis",
        "|SKM_Manny|root|pelvis|spine_01",
        "|SKM_Manny|root|ik_hand_root",
        "|SKM_Manny|root|ik_hand_root|ik_hand_l",
    ],
    transforms=["|SKM_Manny"],
)

TWO_CHARACTERS = FakeCmds(
    joints=[
        "|SKM_Manny|root",
        "|SKM_Manny|root|pelvis",
        "|SKM_Manny|root|pelvis|spine_03",
        "|hero:SKM_Manny|hero:root",
        "|hero:SKM_Manny|hero:root|hero:pelvis",
        "|hero:SKM_Manny|hero:root|hero:pelvis|hero:spine_03",
    ],
    transforms=["|SKM_Manny", "|hero:SKM_Manny"],
)


def use(fake):
    """Point naming.py at a fake cmds and hand the module back."""
    if "maya.cmds" not in sys.modules:
        maya_pkg = types.ModuleType("maya")
        maya_pkg.cmds = fake
        sys.modules["maya"] = maya_pkg
        sys.modules["maya.cmds"] = fake
    from maya_overrig import naming
    naming.cmds = fake
    return naming


class TestLeaf(unittest.TestCase):

    def setUp(self):
        self.naming = use(ONE_CHARACTER)

    def test_strips_dag_path(self):
        self.assertEqual(self.naming.leaf("|root|pelvis|spine_01"), "spine_01")

    def test_strips_namespace(self):
        self.assertEqual(self.naming.leaf("|char:root|char:hand_l"), "hand_l")

    def test_plain_name_survives(self):
        self.assertEqual(self.naming.leaf("head"), "head")


class TestFindRoot(unittest.TestCase):

    def setUp(self):
        self.naming = use(ONE_CHARACTER)

    def test_root_resolves_to_itself(self):
        self.assertEqual(self.naming.find_root("|SKM_Manny|root"),
                         "|SKM_Manny|root")

    def test_any_joint_in_the_chain_walks_up_to_the_root(self):
        self.assertEqual(
            self.naming.find_root("|SKM_Manny|root|pelvis|spine_01"),
            "|SKM_Manny|root")

    def test_enclosing_group_finds_the_skeleton_under_it(self):
        self.assertEqual(self.naming.find_root("|SKM_Manny"), "|SKM_Manny|root")

    def test_node_with_no_skeleton_gives_none(self):
        empty = FakeCmds(joints=[], transforms=["|just_a_group"])
        naming = use(empty)
        self.assertIsNone(naming.find_root("|just_a_group"))


class TestFindRootNamespaced(unittest.TestCase):

    def setUp(self):
        self.naming = use(TWO_CHARACTERS)

    def test_namespaced_joint_walks_up_to_its_own_root(self):
        self.assertEqual(
            self.naming.find_root("|hero:SKM_Manny|hero:root|hero:pelvis"),
            "|hero:SKM_Manny|hero:root")

    def test_plain_joint_walks_up_to_its_own_root(self):
        self.assertEqual(
            self.naming.find_root("|SKM_Manny|root|pelvis"),
            "|SKM_Manny|root")


class TestHierarchyMap(unittest.TestCase):

    def test_maps_leaf_names_to_full_paths(self):
        naming = use(ONE_CHARACTER)
        mapping = naming.hierarchy_map("|SKM_Manny|root")
        self.assertEqual(mapping["spine_01"],
                         "|SKM_Manny|root|pelvis|spine_01")

    def test_includes_the_root_itself(self):
        naming = use(ONE_CHARACTER)
        mapping = naming.hierarchy_map("|SKM_Manny|root")
        self.assertEqual(mapping["root"], "|SKM_Manny|root")

    def test_strips_namespaces_from_the_keys(self):
        naming = use(TWO_CHARACTERS)
        mapping = naming.hierarchy_map("|hero:SKM_Manny|hero:root")
        self.assertEqual(mapping["spine_03"],
                         "|hero:SKM_Manny|hero:root|hero:pelvis|hero:spine_03")

    def test_scoped_to_one_character_only(self):
        """The whole point: the other character must not leak in."""
        naming = use(TWO_CHARACTERS)
        mapping = naming.hierarchy_map("|hero:SKM_Manny|hero:root")
        self.assertEqual(len(mapping), 3)
        for path in mapping.values():
            self.assertTrue(path.startswith("|hero:"), path)

    def test_ue_helper_joints_keep_their_own_names(self):
        naming = use(ONE_CHARACTER)
        mapping = naming.hierarchy_map("|SKM_Manny|root")
        self.assertIn("ik_hand_l", mapping)
        self.assertNotIn("hand_l", mapping)


PREFIXED = FakeCmds(
    joints=[
        "|SKM_Manny|prefix_root",
        "|SKM_Manny|prefix_root|prefix_pelvis",
        "|SKM_Manny|prefix_root|prefix_pelvis|prefix_spine_01",
        "|SKM_Manny|prefix_root|prefix_ik_hand_root",
        "|SKM_Manny|prefix_root|prefix_ik_hand_root|prefix_ik_hand_l",
        "|SKM_Manny|prefix_root|prefix_pelvis|prefix_hand_l",
    ],
    transforms=["|SKM_Manny"],
)

# Stand-in for the body map's joint names.
KNOWN = ("root", "pelvis", "spine_01", "hand_l", "head", "thigh_l")


class TestDetectPrefix(unittest.TestCase):

    def setUp(self):
        self.naming = use(ONE_CHARACTER)

    def test_finds_the_prefix_shared_by_the_skeleton(self):
        names = ["prefix_root", "prefix_pelvis", "prefix_spine_01",
                 "prefix_hand_l"]
        self.assertEqual(self.naming.detect_prefix(names, KNOWN), "prefix_")

    def test_unprefixed_skeleton_gets_no_prefix(self):
        names = ["root", "pelvis", "spine_01", "hand_l"]
        self.assertEqual(self.naming.detect_prefix(names, KNOWN), "")

    def test_ik_helper_cannot_pose_as_a_prefix(self):
        """`ik_hand_l` ends with `hand_l`, but plain names already match more."""
        names = ["root", "pelvis", "spine_01", "hand_l",
                 "ik_hand_l", "ik_hand_root"]
        self.assertEqual(self.naming.detect_prefix(names, KNOWN), "")

    def test_prefixed_skeleton_with_ik_helpers_still_finds_the_real_prefix(self):
        names = ["prefix_root", "prefix_pelvis", "prefix_spine_01",
                 "prefix_hand_l", "prefix_ik_hand_l"]
        self.assertEqual(self.naming.detect_prefix(names, KNOWN), "prefix_")

    def test_nothing_recognisable_gives_no_prefix(self):
        self.assertEqual(self.naming.detect_prefix(["a", "b"], KNOWN), "")

    def test_empty_input_gives_no_prefix(self):
        self.assertEqual(self.naming.detect_prefix([], KNOWN), "")


class TestStripPrefix(unittest.TestCase):

    def setUp(self):
        self.naming = use(ONE_CHARACTER)

    def test_rekeys_the_mapping(self):
        mapping = {"prefix_root": "|a|prefix_root",
                   "prefix_hand_l": "|a|prefix_hand_l"}
        stripped = self.naming.strip_prefix(mapping, "prefix_")
        self.assertEqual(stripped,
                         {"root": "|a|prefix_root",
                          "hand_l": "|a|prefix_hand_l"})

    def test_empty_prefix_is_identity(self):
        mapping = {"root": "|a|root"}
        self.assertEqual(self.naming.strip_prefix(mapping, ""), mapping)

    def test_names_without_the_prefix_are_left_alone(self):
        mapping = {"prefix_root": "|a|prefix_root", "stray": "|a|stray"}
        stripped = self.naming.strip_prefix(mapping, "prefix_")
        self.assertEqual(stripped["root"], "|a|prefix_root")
        self.assertEqual(stripped["stray"], "|a|stray")

    def test_ik_helper_keeps_its_own_identity_after_stripping(self):
        """The whole reason prefix detection is skeleton-wide rather than
        per-name: `prefix_ik_hand_l` must become `ik_hand_l`, never `hand_l`."""
        mapping = {"prefix_hand_l": "|a|prefix_hand_l",
                   "prefix_ik_hand_l": "|a|prefix_ik_hand_l"}
        stripped = self.naming.strip_prefix(mapping, "prefix_")
        self.assertEqual(stripped["hand_l"], "|a|prefix_hand_l")
        self.assertEqual(stripped["ik_hand_l"], "|a|prefix_ik_hand_l")


class TestPrefixedHierarchyEndToEnd(unittest.TestCase):

    def test_prefixed_skeleton_lines_up_with_known_names(self):
        naming = use(PREFIXED)
        raw = naming.hierarchy_map("|SKM_Manny|prefix_root")
        prefix = naming.detect_prefix(raw, KNOWN)
        mapping = naming.strip_prefix(raw, prefix)

        self.assertEqual(prefix, "prefix_")
        self.assertEqual(mapping["root"], "|SKM_Manny|prefix_root")
        self.assertEqual(mapping["hand_l"],
                         "|SKM_Manny|prefix_root|prefix_pelvis|prefix_hand_l")
        self.assertEqual(
            mapping["ik_hand_l"],
            "|SKM_Manny|prefix_root|prefix_ik_hand_root|prefix_ik_hand_l")

    def test_unprefixed_skeleton_is_untouched(self):
        naming = use(ONE_CHARACTER)
        raw = naming.hierarchy_map("|SKM_Manny|root")
        prefix = naming.detect_prefix(raw, KNOWN)
        self.assertEqual(prefix, "")
        self.assertEqual(naming.strip_prefix(raw, prefix), raw)


# A character plus the joints OverRig's IK leaves inside the groups it builds.
WITH_IK_RIG = FakeCmds(
    joints=[
        "|SKM_Manny|root",
        "|SKM_Manny|root|pelvis",
        "|thigh_l_IK_strech_gr|base_IK_strech3|fin_jnt11",
        "|thigh_l_IK_strech_gr|base_IK_strech3|fin_jnt21",
        "|thigh_l_IK_strech_gr|base_IK_strech3|soft_knee_gr3|knee_ctrl3",
    ],
    transforms=["|SKM_Manny", "|thigh_l_IK_strech_gr"],
)


class TestSkeletonRoots(unittest.TestCase):

    def test_finds_one_root_per_skeleton(self):
        naming = use(TWO_CHARACTERS)
        self.assertEqual(sorted(naming.find_skeleton_roots()),
                         ["|SKM_Manny|root", "|hero:SKM_Manny|hero:root"])

    def test_single_character_scene_gives_one(self):
        naming = use(ONE_CHARACTER)
        self.assertEqual(naming.find_skeleton_roots(), ["|SKM_Manny|root"])

    def test_empty_scene_gives_nothing(self):
        naming = use(FakeCmds())
        self.assertEqual(naming.find_skeleton_roots(), [])

    def test_rig_helper_joints_look_like_extra_skeletons(self):
        """Documents the trap: OverRig's IK joints have no joint parent."""
        naming = use(WITH_IK_RIG)
        self.assertEqual(len(naming.find_skeleton_roots()), 4)

    def test_excluding_the_rig_leaves_only_the_character(self):
        naming = use(WITH_IK_RIG)
        roots = naming.find_skeleton_roots(
            exclude_under=["|thigh_l_IK_strech_gr"])
        self.assertEqual(roots, ["|SKM_Manny|root"])

    def test_excluding_an_absent_node_changes_nothing(self):
        naming = use(ONE_CHARACTER)
        self.assertEqual(naming.find_skeleton_roots(exclude_under=["|nope"]),
                         ["|SKM_Manny|root"])

    def test_empty_exclusion_behaves_as_before(self):
        naming = use(ONE_CHARACTER)
        self.assertEqual(naming.find_skeleton_roots(exclude_under=[]),
                         ["|SKM_Manny|root"])

    def test_an_excluded_node_that_is_itself_a_joint_is_dropped(self):
        naming = use(WITH_IK_RIG)
        roots = naming.find_skeleton_roots(
            exclude_under=["|thigh_l_IK_strech_gr|base_IK_strech3|fin_jnt11"])
        self.assertNotIn("|thigh_l_IK_strech_gr|base_IK_strech3|fin_jnt11",
                         roots)


class TestUuidBinding(unittest.TestCase):

    def setUp(self):
        self.naming = use(ONE_CHARACTER)

    def test_uuid_round_trips_back_to_the_path(self):
        uuid = self.naming.uuid_of("|SKM_Manny|root")
        self.assertEqual(self.naming.path_from_uuid(uuid), "|SKM_Manny|root")

    def test_missing_uuid_gives_none(self):
        self.assertIsNone(self.naming.path_from_uuid("uuid-of:|gone"))

    def test_uuid_of_missing_node_gives_none(self):
        self.assertIsNone(self.naming.uuid_of(""))


if __name__ == "__main__":
    unittest.main()
