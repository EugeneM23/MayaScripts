"""maya_channelbox.scene on a fake cmds (2026-10-18): what a channel reads as - keyed,
on a key, a breakdown, changed, muted (through Maya's mute node), driven - and the
targets an edit reaches on every selected object."""

import unittest

from maya_channelbox import scene


class FakeCmds(object):
    def __init__(self):
        self.t = 12.0
        self.sel = ["|IKLeg_R", "|IKLeg_L"]
        self.attrs = {"|IKLeg_L": ["translateX", "translateY", "rotateX", "swivel"],
                      "|IKLeg_R": ["translateX", "translateY", "rotateX"]}
        self.values = {"translateX": 4.8, "translateY": 9.4, "rotateX": -18.5, "swivel": 3.0}
        self.sources = {"|IKLeg_L.translateX": "tx_curve", "|IKLeg_L.translateY": "ty_mute",
                        "ty_mute.input": "ty_curve", "|IKLeg_L.swivel": "pc1"}
        self.types = {"tx_curve": "animCurveTL", "ty_mute": "mute", "ty_curve": "animCurveTL",
                      "pc1": "parentConstraint"}
        self.keys = {"|IKLeg_L.translateX": ([0.0, 12.0, 24.0], [12.0], 4.5),
                     "|IKLeg_L.translateY": ([0.0, 6.0], [], 9.4)}
        self.muted = {"|IKLeg_L.translateY"}
        self.edits = []

    def ls(self, **kw):
        return list(self.sel)

    def listAttr(self, node, keyable=False, channelBox=False):
        return list(self.attrs.get(node, [])) if keyable else []

    def getAttr(self, plug, type=False, lock=False):             # noqa: A002
        if type:
            return "doubleLinear" if ".translate" in plug else "double"
        if lock:
            return False
        return self.values[plug.split(".")[-1]]

    def attributeName(self, plug, nice=False):
        return plug.split(".")[-1].title()

    def attributeQuery(self, attr, node=None, **kw):
        if kw.get("exists"):
            return attr in self.attrs.get(node, [])
        return False

    def listConnections(self, plug, **kw):
        src = self.sources.get(plug)
        return [src] if src else []

    def nodeType(self, node):
        return self.types[node]

    def mute(self, plug, q=False, **kw):
        return plug in self.muted

    def keyframe(self, plug, q=True, timeChange=False, breakdown=False, eval=False, time=None):  # noqa: A002
        times, bds, curve = self.keys.get(plug, ([], [], None))
        if timeChange:
            return list(times)
        if breakdown:
            return list(bds)
        if eval:
            return [curve]
        return []

    def currentTime(self, q=True):
        return self.t

    def channelBox(self, name, **kw):
        if kw.get("exists"):
            return True
        if kw.get("edit"):
            self.edits.append(kw)
            return None
        if kw.get("shapeObjectList"):
            return ["|IKLeg_L|IKLeg_LShape"]
        return []

    def objExists(self, node):
        return True


class SceneTests(unittest.TestCase):

    def setUp(self):
        self.saved = scene.cmds
        self.fake = FakeCmds()
        scene.cmds = self.fake

    def tearDown(self):
        scene.cmds = self.saved

    def test_the_snapshot_reads_each_state(self):
        snap = scene.snapshot()
        self.assertEqual(snap["lead"], "|IKLeg_L")
        main = dict((c["attr"], c) for c in snap["sections"][0]["channels"])
        tx = main["translateX"]
        self.assertEqual((tx["source"], tx["on_key"], tx["breakdown"], tx["changed"]),
                         ("curve", True, True, True))
        ty = main["translateY"]
        self.assertTrue(ty["muted"])
        self.assertEqual(ty["source"], "curve")                 # looked through the mute node
        self.assertFalse(ty["on_key"])
        self.assertEqual(main["swivel"]["source"], "driven")
        self.assertIsNone(main["rotateX"]["source"])

    def test_an_edit_reaches_every_selected_object_that_has_the_channel(self):
        main = dict((c["attr"], c) for c in scene.snapshot()["sections"][0]["channels"])
        self.assertEqual(main["translateX"]["targets"], ["|IKLeg_R.translateX", "|IKLeg_L.translateX"])
        self.assertEqual(main["swivel"]["targets"], ["|IKLeg_L.swivel"])

    def test_shapes_come_closed_and_open_on_request(self):
        snap = scene.snapshot()
        shapes = snap["sections"][1]
        self.assertEqual((shapes["kind"], shapes["title"], shapes["channels"]), ("shapes", "SHAPES", []))
        self.fake.attrs["|IKLeg_L|IKLeg_LShape"] = ["translateX"]
        opened = scene.snapshot(opened=(shapes["key"],))
        self.assertEqual(len(opened["sections"][1]["channels"]), 1)

    def test_the_selection_is_written_into_maya_s_channel_box(self):
        self.assertTrue(scene.sync_selection(["|IKLeg_L.translateX"]))
        self.assertEqual(self.fake.edits[-1]["select"], ["|IKLeg_L.translateX"])

    def test_visibility_stands_after_the_scales_as_in_maya(self):
        self.assertEqual(scene.ordered(["visibility", "translateX", "rotateX", "scaleX", "swivel"]),
                         ["translateX", "rotateX", "scaleX", "visibility", "swivel"])
        self.assertEqual(scene.ordered(["swivel"]), ["swivel"])

    def test_nothing_selected(self):
        self.fake.sel = []
        self.assertEqual(scene.snapshot()["sections"], [])


if __name__ == "__main__":
    unittest.main()
