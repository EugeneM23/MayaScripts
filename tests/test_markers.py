"""maya_markers (2026-10-27): our marked nodes kept between asks - the scene combed
again only after it changed (a node added or removed, an undo, a scene, one of ours
marked) - resolved by UUID at each ask, a node that lost its marker left out."""
import sys
import types
import unittest

try:
    import maya.cmds  # noqa: F401
except ImportError:
    maya = types.ModuleType("maya")
    maya.cmds = types.ModuleType("maya.cmds")
    sys.modules.setdefault("maya", maya)
    sys.modules.setdefault("maya.cmds", maya.cmds)

import maya_markers  # noqa: E402


class FakeScene(object):
    """Nodes as {uuid: (path, {attributes})}."""

    def __init__(self):
        self.nodes = {"U1": ["|grp|a", {"skeldarDynChain"}],
                      "U2": ["|b", {"skeldarDynChain"}],
                      "U3": ["|c", set()]}
        self.scans = 0

    def ls(self, *args, **kw):
        if args and isinstance(args[0], str) and args[0].startswith("*."):
            self.scans += 1
            marker = args[0][2:]
            return [p for p, attrs in self.nodes.values() if marker in attrs]
        names = list(args[0]) if args else []
        if kw.get("uuid"):
            return [u for u in sorted(self.nodes) for n in names if self.nodes[u][0] == n]
        out = []
        for name in names:
            if name in self.nodes:                         # a uuid
                out.append(self.nodes[name][0])
            elif "." in name:                              # node.attribute
                node, attr = name.rsplit(".", 1)
                if any(p == node and attr in attrs for p, attrs in self.nodes.values()):
                    out.append(node)
        return out


class Markers(unittest.TestCase):

    def setUp(self):
        self.saved = (maya_markers.cmds, maya_markers._install, dict(maya_markers._state()))
        self.scene = FakeScene()
        maya_markers.cmds = self.scene
        maya_markers._install = lambda: True
        state = maya_markers._state()
        state["found"], state["gen"] = {}, 0

    def tearDown(self):
        maya_markers.cmds, maya_markers._install, state = self.saved
        maya_markers._state().clear()
        maya_markers._state().update(state)

    def test_a_second_ask_combs_nothing(self):
        first = maya_markers.find("skeldarDynChain")
        second = maya_markers.find("skeldarDynChain")
        self.assertEqual(first, ["|b", "|grp|a"])
        self.assertEqual(second, first)
        self.assertEqual(self.scene.scans, 1)

    def test_a_change_combs_again(self):
        maya_markers.find("skeldarDynChain")
        self.scene.nodes["U3"][1].add("skeldarDynChain")
        maya_markers.touch()
        self.assertEqual(maya_markers.find("skeldarDynChain"), ["|b", "|c", "|grp|a"])
        self.assertEqual(self.scene.scans, 2)

    def test_a_renamed_node_is_found_where_it_is_now(self):
        maya_markers.find("skeldarDynChain")
        self.scene.nodes["U1"][0] = "|grp|renamed"
        self.assertEqual(maya_markers.find("skeldarDynChain"), ["|b", "|grp|renamed"])
        self.assertEqual(self.scene.scans, 1)

    def test_a_node_that_lost_its_marker_is_left_out(self):
        maya_markers.find("skeldarDynChain")
        self.scene.nodes["U2"][1].discard("skeldarDynChain")
        self.assertEqual(maya_markers.find("skeldarDynChain"), ["|grp|a"])

    def test_nothing_found_is_kept_too(self):
        self.assertEqual(maya_markers.find("skeldarDynWind"), [])
        self.assertEqual(maya_markers.find("skeldarDynWind"), [])
        self.assertEqual(self.scene.scans, 1)

    def test_markers_and_types_are_kept_apart(self):
        maya_markers.find("skeldarDynChain")
        maya_markers.find("skeldarDynChain", "transform")
        maya_markers.find("skeldarDynWind")
        self.assertEqual(self.scene.scans, 3)

    def test_another_cmds_is_asked_every_time(self):
        other = FakeScene()
        maya_markers.find("skeldarDynChain", commands=other)
        maya_markers.find("skeldarDynChain", commands=other)
        self.assertEqual(other.scans, 2)
        self.assertEqual(self.scene.scans, 0)

    def test_without_the_scene_s_callbacks_every_ask_combs(self):
        maya_markers._install = lambda: False
        maya_markers.find("skeldarDynChain")
        maya_markers.find("skeldarDynChain")
        self.assertEqual(self.scene.scans, 2)


class Writers(unittest.TestCase):
    """Every writer of a marker the index answers for touches it."""

    def read(self, rel):
        import os
        path = os.path.join(os.path.dirname(maya_markers.__file__), rel)
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_the_writers_touch(self):
        self.assertIn("maya_markers.touch()", self.read("maya_dynamics/setup.py"))
        self.assertIn("maya_markers.touch()", self.read("maya_com/network.py"))
        self.assertIn("maya_markers.touch()", self.read("maya_ragdoll/impulse.py"))

    def test_it_ships(self):
        self.assertIn('"maya_markers.py"', self.read("install.py"))


if __name__ == "__main__":
    unittest.main()
