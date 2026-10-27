"""maya_dynamics.setup - the chains, colliders and wind arrow kept in the scene (2026-10-26).

The scene behaviour is proven by docs/superpowers/plans/verify_dynamics.py; these pin the rules
and the drawings on a fake cmds."""

import json
import sys
import types
import unittest
from unittest import mock

import numpy as np

try:
    import maya.cmds  # noqa: F401
except ImportError:
    maya = types.ModuleType("maya")
    maya.cmds = types.ModuleType("maya.cmds")
    sys.modules.setdefault("maya", maya)
    sys.modules.setdefault("maya.cmds", maya.cmds)

from maya_dynamics import model  # noqa: E402
from maya_dynamics import setup  # noqa: E402


class FakeAttrs(object):
    """Nodes with string / number attributes."""

    def __init__(self):
        self.values = {}

    def objExists(self, node):
        return True

    def attributeQuery(self, attr, node=None, exists=False):
        return (node, attr) in self.values

    def addAttr(self, node, longName=None, **kw):
        self.values[(node, longName)] = None

    def setAttr(self, plug, value=None, type=None, **kw):
        node, attr = plug.split(".", 1)
        self.values[(node, attr)] = value

    def getAttr(self, plug):
        node, attr = plug.split(".", 1)
        return self.values[(node, attr)]


class Settings(unittest.TestCase):

    def test_settings_round_trip_through_the_node(self):
        fake = FakeAttrs()
        with mock.patch.object(setup, "cmds", fake):
            setup.write_settings("|g|hair_dyn", {"stiffness": 0.8, "loop": True, "junk": 3})
            s = setup.read_settings("|g|hair_dyn")
        self.assertEqual(s["stiffness"], 0.8)
        self.assertTrue(s["loop"])
        self.assertNotIn("junk", s)
        self.assertEqual(set(s), set(model.DEFAULTS))

    def test_broken_json_reads_the_defaults(self):
        fake = FakeAttrs()
        fake.values[("c", setup.SETTINGS)] = "{not json"
        with mock.patch.object(setup, "cmds", fake):
            self.assertEqual(setup.read_settings("c"), model.DEFAULTS)


class Members(unittest.TestCase):

    def test_members_come_back_root_first_and_a_gone_one_is_none(self):
        fake = FakeAttrs()
        fake.values[("c", setup.MEMBERS)] = json.dumps(["u1", "u2", "u3"])
        fake.ls = lambda uuid, long=False, **kw: {"u1": ["|a"], "u3": ["|a|b|c"]}.get(uuid, [])
        with mock.patch.object(setup, "cmds", fake):
            self.assertEqual(setup.members("c"), ["|a", None, "|a|b|c"])


class PlanChains(unittest.TestCase):

    def plan(self, roots, existing, chains_of):
        from maya_tools import overlap
        with mock.patch.object(overlap, "chain_from", lambda root: (chains_of[root], "")):
            return setup.plan_chains(roots, existing)

    def test_a_new_root_makes_its_chain(self):
        new, picked, notes, refusal = self.plan(["|h1"], {}, {"|h1": ["|h1", "|h1|h2", "|h1|h2|h3"]})
        self.assertEqual((new, picked, refusal), ([["|h1", "|h1|h2", "|h1|h2|h3"]], [], ""))

    def test_a_root_already_in_a_chain_picks_that_chain(self):
        new, picked, _notes, refusal = self.plan(["|h1|h2"], {"|h1": "|g|h1_dyn",
                                                              "|h1|h2": "|g|h1_dyn"}, {})
        self.assertEqual((new, picked, refusal), ([], ["|g|h1_dyn"], ""))

    def test_a_lone_node_is_refused(self):
        _new, _picked, _notes, refusal = self.plan(["|x"], {}, {"|x": ["|x"]})
        self.assertIn("needs two members", refusal)

    def test_a_chain_under_or_over_a_standing_one_is_refused(self):
        existing = {"|a|b": "|g|b_dyn", "|a|b|c": "|g|b_dyn"}
        _n, _p, _notes, under = self.plan(["|a|b|c|d"], existing,
                                          {"|a|b|c|d": ["|a|b|c|d", "|a|b|c|d|e"]})
        self.assertIn("chains on chains", under)
        _n, _p, _notes, over = self.plan(["|a"], existing, {"|a": ["|a", "|a|z"]})
        self.assertIn("chains on chains", over)

    def test_two_roots_of_one_chain_make_one_chain(self):
        chains = {"|a": ["|a", "|a|b", "|a|b|c"], "|a|b": ["|a|b", "|a|b|c"]}
        new, _p, _notes, refusal = self.plan(["|a", "|a|b"], {}, chains)
        self.assertEqual((new, refusal), ([chains["|a"]], ""))


class Shapes(unittest.TestCase):

    def test_a_capsule_from_a_bone_runs_along_it_and_is_centred(self):
        matrix, radius, length = setup.default_shape("capsule", np.array([0.0, 20.0, 0.0]))
        self.assertAlmostEqual(length, 20.0)
        self.assertAlmostEqual(radius, 5.0)
        np.testing.assert_allclose(matrix[0, :3], (0, 1, 0), atol=1e-12)
        np.testing.assert_allclose(matrix[3, :3], (0, 10, 0), atol=1e-12)
        np.testing.assert_allclose(matrix[:3, :3] @ matrix[:3, :3].T, np.eye(3), atol=1e-12)

    def test_a_sphere_sits_on_the_bone_and_a_bone_with_no_child_gets_the_default(self):
        matrix, radius, length = setup.default_shape("sphere", np.array([10.0, 0, 0]))
        np.testing.assert_allclose(matrix, np.eye(4))
        self.assertEqual((radius, length), (4.0, 0.0))
        _m, radius, length = setup.default_shape("capsule", None)
        self.assertEqual((radius, length), (setup.DEFAULT_RADIUS, 2 * setup.DEFAULT_RADIUS))

    def test_the_radius_is_kept_in_range(self):
        _m, small, _l = setup.default_shape("capsule", np.array([0.5, 0, 0]))
        _m, big, _l = setup.default_shape("capsule", np.array([500.0, 0, 0]))
        self.assertEqual((small, big), (setup.MIN_RADIUS, setup.MAX_RADIUS))

    def test_a_segment_frame_is_a_rotation_with_x_along_it_whatever_the_hint(self):
        for a, b in (((0, 0, 0), (0, 5, 0)), ((1, 2, 3), (4, -2, 0)), ((0, 0, 0), (0, 0, -9))):
            m = setup.segment_frame(a, b)
            x = (np.array(b, float) - a) / np.linalg.norm(np.array(b, float) - a)
            np.testing.assert_allclose(m[0, :3], x, atol=1e-12)
            np.testing.assert_allclose(m[:3, :3] @ m[:3, :3].T, np.eye(3), atol=1e-12)
            self.assertAlmostEqual(np.linalg.det(m[:3, :3]), 1.0)

    def test_rigid_drops_scale(self):
        m = np.diag([2.0, 3.0, 0.5, 1.0])
        m[3, :3] = (1, 2, 3)
        r = setup.rigid(m)
        np.testing.assert_allclose(r[:3, :3], np.eye(3), atol=1e-12)
        np.testing.assert_allclose(r[3, :3], (1, 2, 3))


class Drawings(unittest.TestCase):

    def test_a_capsule_s_drawing_lies_on_its_surface(self):
        r, L = 3.0, 10.0
        for line in setup.capsule_lines(r, L):
            for x, y, z in line:
                along = min(max(x, -L / 2), L / 2)
                self.assertAlmostEqual(np.linalg.norm((x - along, y, z)), r, places=9)

    def test_a_sphere_is_three_great_circles(self):
        lines = setup.capsule_lines(2.0, 0.0)
        self.assertEqual(len(lines), 3)
        for line in lines:
            for p in line:
                self.assertAlmostEqual(np.linalg.norm(p), 2.0, places=9)

    def test_the_floor_and_the_wind_arrow(self):
        square, tick = setup.floor_lines(10.0)
        self.assertEqual(square[0], square[-1])
        self.assertTrue(all(p[1] == 0.0 for p in square))
        shaft = setup.wind_lines(60.0)[0]
        self.assertEqual(shaft, [(0.0, 0.0, 0.0), (0.0, 0.0, 60.0)])


class Names(unittest.TestCase):

    def test_every_marker_and_attribute_is_ours(self):
        for name in (setup.GROUP_MARKER, setup.CHAIN_MARKER, setup.MEMBERS, setup.SETTINGS,
                     setup.CARRIER, setup.COLLIDER_MARKER, setup.AUTO_MARKER, setup.SPACE_MARKER,
                     setup.SPACES_MARKER, setup.WIND_MARKER, setup.LAYER_MARKER):
            self.assertTrue(name.startswith("skeldar"), name)

    def test_the_layer_is_named_for_the_root(self):
        with mock.patch.object(setup, "root_of", lambda chain: "|r|hair_01"):
            self.assertEqual(setup.layer_name("|g|hair_01_dyn"), "Dynamics_hair_01")


if __name__ == "__main__":
    unittest.main()


class ReadingMemo(unittest.TestCase):
    """2026-10-27: a marker lookup scans the whole scene (~12 ms with three rigs); inside
    `setup.reading()` each marker is looked up once, outside it every call looks again."""

    class Ls(object):
        def __init__(self):
            self.asked = []

        def ls(self, pattern, **kw):
            self.asked.append(pattern)
            return ["|a|" + pattern.split(".")[1]]

        def nodeType(self, node):
            return "transform"

    def test_inside_one_lookup_a_marker_outside_every_time(self):
        fake = self.Ls()
        with mock.patch.object(setup, "cmds", fake), \
                mock.patch.object(setup.scope, "active_only", lambda found, cmds: list(found)):
            with setup.reading():
                first = setup.chains()
                second = setup.chains()
                setup.wind()
                setup.wind()
            self.assertEqual(first, second)
            self.assertEqual(sorted(fake.asked), sorted(["*." + setup.CHAIN_MARKER,
                                                         "*." + setup.WIND_MARKER]))
            setup.chains()
            setup.chains()
            self.assertEqual(len(fake.asked), 4)

    def test_nested_passes_share_the_outer_memo(self):
        fake = self.Ls()
        with mock.patch.object(setup, "cmds", fake), \
                mock.patch.object(setup.scope, "active_only", lambda found, cmds: list(found)):
            with setup.reading():
                setup.chains()
                with setup.reading():
                    setup.chains()
            self.assertEqual(len(fake.asked), 1)
            self.assertEqual(setup._MEMO, [])

    def test_a_returned_list_is_the_caller_s_own(self):
        fake = self.Ls()
        with mock.patch.object(setup, "cmds", fake), \
                mock.patch.object(setup.scope, "active_only", lambda found, cmds: list(found)):
            with setup.reading():
                setup._marked("m").append("junk")
                self.assertEqual(setup._marked("m"), ["|a|m"])
