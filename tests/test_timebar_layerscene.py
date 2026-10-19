"""The layer panel's reads and writes (2026-10-18) on a fake cmds.
Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md"""
import unittest

from maya_timebar import layerscene as S


class FakeCmds(object):
    """Just enough of maya.cmds for animation and display layers."""

    def __init__(self):
        self.attrs = {"BaseAnimation.mute": False, "BaseAnimation.lock": False,
                      "A.mute": False, "A.solo": False, "A.lock": False, "A.weight": 0.5, "A.override": False,
                      "B.mute": True, "B.solo": False, "B.lock": False, "B.weight": 1.0, "B.override": True,
                      "lay1.visibility": True, "lay1.hideOnPlayback": False, "lay1.displayType": 1,
                      "lay1.color": 13, "lay1.overrideRGBColors": False, "lay1.displayOrder": 1}
        self.selected = {"A": False, "B": True}
        self.selection = ["cube"]
        self.chunks = []
        self.calls = []
        self.root = "BaseAnimation"
        self.tree = {"BaseAnimation": ["A", "B"]}
        self.colour = [1.0, 0.0, 0.0]

    def animLayer(self, name=None, q=False, e=False, **kw):
        self.calls.append(("animLayer", name, kw))
        if q and kw.get("root"):
            return self.root
        if q and kw.get("children"):
            return self.tree.get(name, [])
        if q and kw.get("selected"):
            return self.selected.get(name, False)
        if q and kw.get("attribute"):
            return ["cube.translateX"] if name in ("A", "B") else []
        if q and "findCurveForPlug" in kw:
            if name == "BaseAnimation":
                return {"cube.translateX": ["base_tx"]}.get(kw["findCurveForPlug"])
            return {"A": ["A_tx"], "B": ["B_tx"]}.get(name)
        if e and "selected" in kw:
            self.selected[name] = kw["selected"]
        return name or kw.get("name")

    def getAttr(self, plug):
        return self.attrs[plug]

    def setAttr(self, plug, value):
        self.calls.append(("setAttr", plug, value))
        self.attrs[plug] = value

    #  the base layer's graph (2026-10-18 final review): (source node, destination plug)
    edges = ()
    kinds = {}

    def listConnections(self, objs, source=True, destination=False, type=None, connections=False, plugs=False):
        self.calls.append(("listConnections", objs, type, connections))
        objs = [objs] if isinstance(objs, str) else list(objs)
        out = []
        for src, dst in self.edges:
            node = dst.split(".")[0]
            if dst not in objs and node not in objs:
                continue
            kind = self.kinds.get(src, "")
            if type == "animCurve" and not kind.startswith("animCurve"):
                continue
            if type == "animBlendNodeBase" and not kind.startswith("animBlendNode"):
                continue
            out.extend([dst, src] if connections else [src])
        return out

    def ls(self, *a, **kw):
        if isinstance(kw.get("type"), (list, tuple)):
            return [n for n in (a[0] if a else []) if self.kinds.get(n) in kw["type"]]
        if kw.get("type") == "displayLayer":
            return ["defaultLayer", "lay1"]
        if kw.get("selection"):
            return list(self.selection)
        return []

    def colorIndex(self, index, q=False):
        return self.colour

    def keyframe(self, curve, q=True, timeChange=True):
        times = {"A_tx": [0.0, 10.0], "B_tx": [5.0], "base_tx": [0.0, 20.0], "base_ty": [3.0],
                 "driven": [-1.0]}
        if isinstance(curve, (list, tuple)):
            return [t for c in curve for t in times.get(c, [])]
        return times.get(curve, [])

    def undoInfo(self, **kw):
        self.chunks.append(kw)

    def delete(self, *nodes):
        self.calls.append(("delete", nodes))

    def select(self, *a, **kw):
        self.calls.append(("select", a, kw))

    def attributeQuery(self, attr, node=None, exists=False):
        return (node + "." + attr) in self.attrs


class Reads(unittest.TestCase):

    def setUp(self):
        self.cmds = FakeCmds()
        self.old = S.cmds
        S.cmds = self.cmds
        self.addCleanup(setattr, S, "cmds", self.old)

    def test_animation_layers_newest_first_base_last(self):
        rows = S.anim_layers()
        self.assertEqual([r["name"] for r in rows], ["B", "A", "BaseAnimation"])
        b, a, base = rows
        self.assertEqual((b["mode"], b["mute"], b["active"]), ("ovr", True, True))
        self.assertEqual((a["mode"], a["weight"]), ("add", 0.5))
        self.assertTrue(base["base"])

    def test_a_tab_root_is_the_root_and_reads_base_animation(self):
        self.cmds.root = "BaseAnimation"
        self.cmds.tree = {"BaseAnimation": ["tab_x:AnimLayerRoot"], "tab_x:AnimLayerRoot": ["A", "B"]}
        self.cmds.attrs["tab_x:AnimLayerRoot.mute"] = False
        self.cmds.attrs["tab_x:AnimLayerRoot.lock"] = False
        rows = S.anim_layers()
        self.assertEqual([r["name"] for r in rows], ["B", "A", "tab_x:AnimLayerRoot"])
        self.assertEqual(rows[-1]["label"], "BaseAnimation")
        self.assertTrue(rows[-1]["base"])
        self.assertTrue(S.set_flag("tab_x:AnimLayerRoot", "mute", True)[0])
        self.assertFalse(S.set_flag("tab_x:AnimLayerRoot", "solo", True)[0])

    def test_display_layers_without_the_default(self):
        rows = S.display_layers()
        self.assertEqual([r["name"] for r in rows], ["lay1"])
        self.assertEqual((rows[0]["visible"], rows[0]["playback"], rows[0]["type"]), (True, True, 1))
        self.assertEqual(rows[0]["colour"], "#ff0000")

    def test_an_unknown_index_colour_reads_empty(self):
        self.cmds.colour = None
        self.assertEqual(S.display_layers()[0]["colour"], "")

    def test_keys_of_the_selection_in_each_layer(self):
        self.assertEqual(S.keys_by_layer(["A", "B"]), {"A": [0.0, 10.0], "B": [5.0]})

    def test_the_base_layer_s_keys_in_a_few_calls(self):
        """2026-10-18 final review: the base layer's curves gathered with listConnections
        over the selection (an unlayered channel's own curve; a layered channel's base
        curve through the root, one findCurveForPlug per LAYERED channel, never per
        keyable attribute) and read with one keyframe call; a driven key is no time."""
        c = self.cmds
        c.kinds = {"base_ty": "animCurveTL", "driven": "animCurveUL", "base_tx": "animCurveTL",
                   "A_tx": "animCurveTL", "B_tx": "animCurveTL",
                   "blendA": "animBlendNodeAdditiveDL", "blendB": "animBlendNodeAdditiveDL"}
        c.edges = (("base_ty", "cube.translateY"), ("driven", "cube.translateZ"),
                   ("blendB", "cube.translateX"), ("blendA", "blendB.inputA"), ("B_tx", "blendB.inputB"),
                   ("base_tx", "blendA.inputA"), ("A_tx", "blendA.inputB"))
        keys = S.keys_by_layer(["BaseAnimation"])
        self.assertEqual(keys, {"BaseAnimation": [0.0, 3.0, 20.0]})
        finds = [e for e in c.calls if e[0] == "animLayer" and "findCurveForPlug" in e[2]]
        self.assertEqual([e[2]["findCurveForPlug"] for e in finds], ["cube.translateX"])
        self.assertEqual(len([e for e in c.calls if e[0] == "listConnections"]), 2)


class Writes(Reads):

    def test_a_flag_is_one_undo_chunk(self):
        ok, _msg = S.set_flag("A", "mute", True)
        self.assertTrue(ok)
        self.assertTrue(self.cmds.attrs["A.mute"])
        self.assertEqual([c.get("openChunk") or c.get("closeChunk") for c in self.cmds.chunks], [True, True])

    def test_base_animation_has_no_solo_and_no_delete(self):
        self.assertFalse(S.set_flag("BaseAnimation", "solo", True)[0])
        self.assertFalse(S.delete_anim("BaseAnimation")[0])

    def test_nothing_to_merge_into_the_base(self):
        ok, msg = S.merge_down("A")
        self.assertFalse(ok)
        self.assertIn("nothing to merge into", msg)

    def test_a_second_begin_weight_closes_the_first_chunk(self):
        S._WEIGHT["open"] = False
        S.begin_weight()
        S.begin_weight()
        S.end_weight()
        opens = [bool(c.get("openChunk")) for c in self.cmds.chunks]
        self.assertEqual(opens, [True, False, True, False])

    def test_display_flags(self):
        S.set_display("lay1", "playback", False)
        self.assertTrue(self.cmds.attrs["lay1.hideOnPlayback"])
        S.set_display("lay1", "type", 2)
        self.assertEqual(self.cmds.attrs["lay1.displayType"], 2)


if __name__ == "__main__":
    unittest.main()
