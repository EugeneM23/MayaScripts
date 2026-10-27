"""The Pose Library's paste, faster (2026-10-27): inside one press `keys.writable` answers a
plug once and a plug is added to a layer once (`keys.pressing`); the solve's session records a
channel it leaves as it stands without writing it and gives back only what it changed; and
under DG the matrices are read off the DAG path. On a fake `cmds`."""
import unittest

import maya.api.OpenMaya as om

from maya_poselib import keys
from maya_poselib import rigsolve


class Cmds(object):
    """getAttr / setAttr / listConnections / animLayer / ls, counted."""

    def __init__(self, values=None, locked=()):
        self.values = dict(values or {})
        self.locked = set(locked)
        self.calls = []

    def getAttr(self, plug, lock=False):
        self.calls.append(("getAttr", plug, lock))
        if lock:
            return plug in self.locked
        return self.values.get(plug, 0.0)

    def setAttr(self, plug, value):
        self.calls.append(("setAttr", plug, value))
        self.values[plug] = value

    def listConnections(self, plug, **kw):
        self.calls.append(("listConnections", plug))
        return []

    def attributeQuery(self, *a, **kw):
        return False

    def connectionInfo(self, plug, **kw):
        return False

    def animLayer(self, name, edit=False, attribute=None, **kw):
        self.calls.append(("animLayer", name, attribute))

    def ls(self, path):
        self.calls.append(("ls", path))
        return [path.split("|")[-1]]

    def count(self, kind):
        return sum(1 for call in self.calls if call[0] == kind)


class Pressing(unittest.TestCase):

    def setUp(self):
        self.cmds = Cmds(locked={"a.tx"})
        self.saved = keys.cmds
        keys.cmds = self.cmds

    def tearDown(self):
        keys.cmds = self.saved
        del keys._PRESS[:]

    def test_outside_a_press_every_ask_reads_the_scene(self):
        keys.writable("b.tx")
        keys.writable("b.tx")
        self.assertEqual(self.cmds.count("listConnections"), 2)

    def test_inside_a_press_a_plug_is_asked_once(self):
        with keys.pressing():
            self.assertEqual(keys.writable("b.tx"), (True, ""))
            self.assertEqual(keys.writable("b.tx"), (True, ""))
            self.assertEqual(keys.writable("a.tx"), (False, "locked"))
            self.assertEqual(keys.writable("a.tx"), (False, "locked"))
        self.assertEqual(self.cmds.count("listConnections"), 1)
        self.assertEqual(sum(1 for c in self.cmds.calls if c[0] == "getAttr" and c[1] == "a.tx"), 1)

    def test_the_memo_goes_with_the_press(self):
        with keys.pressing():
            keys.writable("b.tx")
        self.assertIsNone(keys.memo("writable"))
        keys.writable("b.tx")
        self.assertEqual(self.cmds.count("listConnections"), 2)

    def test_a_nested_press_shares_the_outer_memo(self):
        with keys.pressing():
            keys.writable("b.tx")
            with keys.pressing():
                keys.writable("b.tx")
            keys.writable("b.tx")
        self.assertEqual(self.cmds.count("listConnections"), 1)

    def test_a_raising_block_still_ends_the_press(self):
        with self.assertRaises(ZeroDivisionError):
            with keys.pressing():
                1 / 0
        self.assertEqual(keys._PRESS, [])

    def test_a_plug_is_added_to_its_layer_once_a_press(self):
        layer = keys.Layer("AnimLayer1", False, True, False, False, False, 1.0)
        saved_key = keys._key
        keys._key = lambda plug, value, frame, layer: 1
        try:
            with keys.pressing():
                for frame in (0, 1, 2):
                    written = keys.write({"b.tx": 1.0, "b.ty": 2.0}, frame, layer)
                    self.assertEqual(written.plugs, ["b.tx", "b.ty"])
            self.assertEqual(self.cmds.count("animLayer"), 2)
            keys.write({"b.tx": 1.0}, 3, layer)
            self.assertEqual(self.cmds.count("animLayer"), 3)
        finally:
            keys._key = saved_key


class Session(unittest.TestCase):

    def setUp(self):
        self.cmds = Cmds({"c.tx": 4.0, "c.ty": 5.0})
        self.saved = rigsolve.cmds
        rigsolve.cmds = self.cmds

    def tearDown(self):
        rigsolve.cmds = self.saved

    def test_keep_records_the_value_without_writing_it(self):
        session = rigsolve._Session()
        session.keep("c.tx")
        self.assertEqual(dict(session.last), {"c.tx": 4.0})
        self.assertEqual(self.cmds.count("setAttr"), 0)

    def test_keep_after_a_set_keeps_the_set_value(self):
        session = rigsolve._Session()
        session.set("c.tx", 9.0)
        session.keep("c.tx")
        self.assertEqual(session.last["c.tx"], 9.0)
        self.assertEqual(session.original["c.tx"], 4.0)

    def test_restore_gives_back_only_what_changed(self):
        session = rigsolve._Session()
        session.set("c.tx", 9.0)
        session.keep("c.ty")
        session.set("c.tx", 4.0)              # back to what it held: nothing to give back
        session.set("c.ty", 6.0)
        del self.cmds.calls[:]
        session.restore()
        self.assertEqual(self.cmds.calls, [("setAttr", "c.ty", 5.0)])
        self.assertEqual(self.cmds.values, {"c.tx": 4.0, "c.ty": 5.0})


class Names(unittest.TestCase):

    def setUp(self):
        self.cmds = Cmds()
        self.saved = rigsolve.cmds
        rigsolve.cmds = self.cmds

    def tearDown(self):
        rigsolve.cmds = self.saved
        del keys._PRESS[:]

    def test_a_path_is_spelled_once_a_press(self):
        with keys.pressing():
            self.assertEqual(rigsolve._name("|g|FKWrist_R"), "FKWrist_R")
            self.assertEqual(rigsolve._name("|g|FKWrist_R"), "FKWrist_R")
        self.assertEqual(self.cmds.count("ls"), 1)
        rigsolve._name("|g|FKWrist_R")
        self.assertEqual(self.cmds.count("ls"), 2)


class DagReads(unittest.TestCase):
    """`_world` / `_parent_world` read off the DAG path only while a `_fresh` block reads under
    DG; elsewhere (and for a node the path cannot be had for) through getAttr."""

    class Path(object):
        def inclusiveMatrix(self):
            return om.MMatrix([2.0] * 16)

        def exclusiveMatrix(self):
            return om.MMatrix([3.0] * 16)

    def setUp(self):
        self.saved = (rigsolve.cmds, rigsolve._dag_path)
        self.cmds = Cmds({"n.worldMatrix[0]": [1.0] * 16, "n.parentMatrix[0]": [1.0] * 16})
        rigsolve.cmds = self.cmds

    def tearDown(self):
        rigsolve.cmds, rigsolve._dag_path = self.saved
        del rigsolve._DAG[:]

    def test_outside_dg_the_attribute_is_read(self):
        self.assertEqual(rigsolve._world("n"), om.MMatrix([1.0] * 16))
        self.assertEqual(rigsolve._parent_world("n"), om.MMatrix([1.0] * 16))

    def test_under_dg_the_path_is_read(self):
        rigsolve._dag_path = lambda node: self.Path()
        self.assertEqual(rigsolve._world("n"), om.MMatrix([2.0] * 16))
        self.assertEqual(rigsolve._parent_world("n"), om.MMatrix([3.0] * 16))
        self.assertEqual(self.cmds.count("getAttr"), 0)

    def test_no_path_outside_a_dg_block(self):
        rigsolve._dag_path = self.saved[1]
        self.assertIsNone(rigsolve._dag_path("n"))
        rigsolve._DAG.append(None)                       # a block under parallel evaluation
        self.assertIsNone(rigsolve._dag_path("n"))

    def test_a_node_without_a_path_falls_back_to_its_attribute(self):
        class Selection(object):                         # no OpenMaya selection outside Maya
            def add(self, node):
                raise RuntimeError("no such node")
        fake = type("om", (), {"MSelectionList": Selection, "MMatrix": om.MMatrix})
        rigsolve._dag_path = self.saved[1]
        saved_om, rigsolve.om = rigsolve.om, fake
        try:
            rigsolve._DAG.append({})
            self.assertIsNone(rigsolve._dag_path("|no|such|node"))
            self.assertEqual(rigsolve._world("n"), om.MMatrix([1.0] * 16))
        finally:
            rigsolve.om = saved_om

    def test_a_fake_cmds_never_reads_a_path(self):
        self.assertFalse(rigsolve._live())

    def test_fresh_reads_off_the_path_only_under_dg(self):
        class Em(Cmds):
            def __init__(self, mode):
                Cmds.__init__(self)
                self.mode = mode

            def evaluationManager(self, query=False, mode=None):
                if query:
                    return [self.mode]
                self.mode = mode

        for mode, expected in (("off", None), ("parallel", None)):   # a fake: never a path
            rigsolve.cmds = Em(mode)
            saved_tweaks = rigsolve.keys.Tweaks
            rigsolve.keys.Tweaks = lambda: type("T", (), {"restore": lambda self, skip: None})()
            try:
                with rigsolve._fresh():
                    self.assertEqual(rigsolve._DAG[-1], expected)
                    self.assertEqual(rigsolve.cmds.mode, "off")
                self.assertEqual(rigsolve._DAG, [])
                self.assertEqual(rigsolve.cmds.mode, mode)
            finally:
                rigsolve.keys.Tweaks = saved_tweaks


if __name__ == "__main__":
    unittest.main()
