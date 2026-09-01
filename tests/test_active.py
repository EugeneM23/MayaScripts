"""Tests for the active-character context.

`root_of` is the whole reason no signature had to change: a binding map
carries its own root, so an entry point can adopt the character its
`scene_map` came from without being told. If it ever answered the wrong
joint, every manifest in the build would land on the wrong character.
"""

import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_overrig import active  # noqa: E402


class RootOf(unittest.TestCase):

    def test_the_shallowest_joint_is_the_root(self):
        scene_map = {"pelvis": "|root|pelvis",
                     "root": "|root",
                     "spine_01": "|root|pelvis|spine_01"}
        self.assertEqual(active.root_of(scene_map), "|root")

    def test_a_grouped_character_answers_the_joint_not_the_group(self):
        """The map is built from hierarchy_map(root), so the group is not
        in it -- the shallowest JOINT is the answer."""
        scene_map = {"root": "|hero_grp|root",
                     "pelvis": "|hero_grp|root|pelvis"}
        self.assertEqual(active.root_of(scene_map), "|hero_grp|root")

    def test_a_rig_without_a_root_joint_answers_its_own_top(self):
        """UE4-schema rigs have no `root`; the pelvis is the top."""
        scene_map = {"pelvis": "|pelvis",
                     "spine_01": "|pelvis|spine_01"}
        self.assertEqual(active.root_of(scene_map), "|pelvis")

    def test_a_second_character_answers_its_own_root(self):
        scene_map = {"root": "|root1", "pelvis": "|root1|pelvis"}
        self.assertEqual(active.root_of(scene_map), "|root1")

    def test_a_namespaced_skeleton_answers_its_own_root(self):
        scene_map = {"root": "|hero:root", "pelvis": "|hero:root|hero:pelvis"}
        self.assertEqual(active.root_of(scene_map), "|hero:root")

    def test_an_empty_map_answers_none(self):
        self.assertIsNone(active.root_of({}))
        self.assertIsNone(active.root_of(None))

    def test_none_values_are_ignored(self):
        self.assertEqual(active.root_of({"root": None, "pelvis": "|root|p"}),
                         "|root|p")

    def test_ties_break_by_path_so_the_answer_never_moves(self):
        """A map spanning two subtrees cannot come out of hierarchy_map,
        but a caller can hand us anything -- and dict order must not
        decide which character a build lands on."""
        one = {"a": "|zeta", "b": "|alpha"}
        two = {"b": "|alpha", "a": "|zeta"}
        self.assertEqual(active.root_of(one), active.root_of(two))
        self.assertEqual(active.root_of(one), "|alpha")


class Context(unittest.TestCase):
    """The setter/getter pair, with the scene faked out."""

    def setUp(self):
        self.real_naming = active.naming
        self.real_cmds = active.cmds
        active.clear()

    def tearDown(self):
        active.naming = self.real_naming
        active.cmds = self.real_cmds
        active.clear()

    class FakeNaming(object):
        def __init__(self, table):
            self.table = table          # {path: uuid}

        def uuid_of(self, node):
            return self.table.get(node)

        def path_from_uuid(self, uuid):
            for path, value in self.table.items():
                if value == uuid:
                    return path
            return None

    class FakeCmds(object):
        def __init__(self, live):
            self.live = set(live)       # the uuids still in the scene

        def ls(self, *args, **kwargs):
            return [args[0]] if args and args[0] in self.live else []

    def _use(self, table, live=None):
        active.naming = self.FakeNaming(table)
        active.cmds = self.FakeCmds(
            list(table.values()) if live is None else live)

    def test_set_root_remembers_the_uuid_not_the_path(self):
        self._use({"|root": "UUID-A"})
        self.assertEqual(active.set_root("|root"), "UUID-A")
        self.assertEqual(active.root_uuid(), "UUID-A")

    def test_the_path_is_re_resolved_so_a_rename_does_not_break_it(self):
        table = {"|root": "UUID-A"}
        self._use(table)
        active.set_root("|root")
        del table["|root"]
        table["|hero_grp|root"] = "UUID-A"
        self.assertEqual(active.root(), "|hero_grp|root")

    def test_a_deleted_character_stops_being_active(self):
        """The animator can delete the character with the panel open, and
        every lookup must then resolve to nothing rather than to somebody
        else's rig."""
        self._use({"|root": "UUID-A"})
        active.set_root("|root")
        active.cmds = self.FakeCmds([])
        self.assertIsNone(active.root_uuid())

    def test_set_root_of_nothing_clears(self):
        self._use({"|root": "UUID-A"})
        active.set_root("|root")
        self.assertIsNone(active.set_root(None))
        self.assertIsNone(active.root_uuid())

    def test_clear_clears(self):
        self._use({"|root": "UUID-A"})
        active.set_root("|root")
        active.clear()
        self.assertIsNone(active.root_uuid())

    def test_adopt_takes_the_character_a_binding_map_came_from(self):
        self._use({"|root1": "UUID-B", "|root1|pelvis": "UUID-P"})
        self.assertEqual(
            active.adopt({"root": "|root1", "pelvis": "|root1|pelvis"}),
            "UUID-B")

    def test_adopting_an_empty_map_clears(self):
        self._use({"|root": "UUID-A"})
        active.set_root("|root")
        self.assertIsNone(active.adopt({}))
        self.assertIsNone(active.root_uuid())


if __name__ == "__main__":
    unittest.main()
