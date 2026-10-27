"""Characters > Delete, batched (2026-10-27): the marker reads, the locks and the
standing paths each asked in ONE Maya command where they were asked a node at a time.

The scene half is proved by docs/superpowers/plans/verify_delete_character.py; here
the batched helpers answer what the per-node queries answered, on a fake `cmds`."""
import types
import unittest

from maya_scenesetup import deletion


class FakeCmds(object):
    """Nodes by long path: attributes, locks, types and children."""

    def __init__(self, nodes):
        self.nodes = nodes                    # path -> {"attrs": {...}, "locked": bool}
        self.calls = []

    def ls(self, items=None, long=False, objectsOnly=False, type=None, **kw):
        self.calls.append(("ls", len(items or [])))
        out = []
        for item in items or []:
            node, _, attr = item.partition(".")
            info = self.nodes.get(node)
            if info is None:
                continue
            if attr and attr not in info.get("attrs", {}):
                continue
            if type and info.get("type", "transform") != type:
                continue
            if node not in out:
                out.append(node)
        return out

    def lockNode(self, paths, query=False, lock=None):
        if query:
            self.calls.append(("lockNode -q", len(paths if isinstance(paths, list) else [paths])))
            paths = paths if isinstance(paths, list) else [paths]
            return [self.nodes[p].get("locked", False) for p in paths]
        self.calls.append(("lockNode", tuple(paths)))
        for path in paths:
            self.nodes[path]["locked"] = lock

    def getAttr(self, plug):
        node, _, attr = plug.partition(".")
        return self.nodes[node]["attrs"][attr]

    def listRelatives(self, parts, allDescendents=False, type=None, fullPath=False):
        out = []
        for part in parts:
            out += [p for p in self.nodes if p.startswith(part + "|")]
        return out


class Batched(unittest.TestCase):

    def setUp(self):
        self.saved = deletion.cmds
        self.cmds = FakeCmds({
            "|grp": {"attrs": {}},
            "|grp|sword": {"attrs": {"mayaWeapon": "", "mayaArmorNamespace": ""}},
            "|grp|shield": {"attrs": {"mayaArmor": "", "mayaArmorNamespace": "Tech_Limb"}},
            "|grp|cam": {"attrs": {"mayaSceneSetupCamera": ""}, "locked": True},
            "|grp|com": {"attrs": {deletion.COM_MARKER: ""}},
            "|grp|com2": {"attrs": {deletion.COM_MARKER: ""}},
            "|grp|rec": {"attrs": {deletion.RECORD_NODES: "a b"}, "locked": True},
        })
        deletion.cmds = self.cmds

    def tearDown(self):
        deletion.cmds = self.saved

    def test_having_answers_the_nodes_carrying_the_attribute_in_one_query(self):
        found = deletion._having(list(self.cmds.nodes), deletion.COM_MARKER)
        self.assertEqual(found, {"|grp|com", "|grp|com2"})
        self.assertEqual([c for c in self.cmds.calls if c[0] == "ls"], [("ls", 7)])

    def test_having_of_nothing_asks_nothing(self):
        self.assertEqual(deletion._having([None, ""], "mayaWeapon"), set())
        self.assertEqual(self.cmds.calls, [])

    def test_the_summary_counts_every_marker_once(self):
        from maya_scenesetup import armor, bonedrive, camera
        self.assertEqual((bonedrive.MARKER, armor.MARKER, camera.MARKER),
                         ("mayaWeapon", "mayaArmor", "mayaSceneSetupCamera"))
        char = types.SimpleNamespace(parts=["|grp"])
        self.assertEqual(deletion._summary(char),
                         ["1 weapon", "1 armor piece", "camera", "centre of mass"])

    def test_the_armor_namespaces_come_from_the_marked_transforms(self):
        self.assertEqual(deletion._armor_namespaces(list(self.cmds.nodes)), ["Tech_Limb"])

    def test_the_locked_are_unlocked_with_one_query(self):
        deletion._unlock(list(self.cmds.nodes))
        self.assertFalse(any(info.get("locked") for info in self.cmds.nodes.values()))
        self.assertIn(("lockNode", ("|grp|cam", "|grp|rec")), self.cmds.calls)
        self.assertEqual([c for c in self.cmds.calls if c[0] == "lockNode -q"],
                         [("lockNode -q", 7)])

    def test_a_query_answering_another_length_is_asked_a_node_at_a_time(self):
        real = self.cmds.lockNode

        def short(paths, query=False, lock=None):
            if query and isinstance(paths, list) and len(paths) > 1:
                return [True]
            return real(paths, query=query, lock=lock)
        self.cmds.lockNode = short
        deletion._unlock(["|grp|sword", "|grp|cam"])
        self.assertFalse(self.cmds.nodes["|grp|cam"]["locked"])

    def test_existing_keeps_the_standing_in_their_order(self):
        del self.cmds.nodes["|grp|sword"]
        self.assertEqual(deletion._existing(["|grp|cam", "|grp|sword", "|grp"]), ["|grp|cam", "|grp"])
        self.assertEqual(deletion._existing([]), [])


if __name__ == "__main__":
    unittest.main()
