"""maya_poselib.curvecapture - a card's original curves read off the scene (spec
2026-10-28-pose-library-curves-and-layers-design.md, «Which channels»). `keys` and `cmds` are
faked as the module attributes (CLAUDE.md's rule); `copy` is the caller's (`animcapture._copied`)."""

import unittest
from collections import OrderedDict

from maya_poselib import curvecapture as cc
from maya_poselib import curvedata


class FakeKeys(object):
    """`keys` as curvecapture asks it."""

    _INFINITY = {0: "constant", 1: "linear", 3: "cycle", 4: "cycleRelative", 5: "oscillate"}
    NAMED = 4

    def __init__(self, stack=(), holds=None, curves=None, feeds=None, statics=None):
        self.stack = list(stack)
        self.holds = dict(holds or {})
        self.curves = dict(curves or {})
        self.feeds = dict(feeds or {})
        self.statics = dict(statics or {})
        self.asked = []

    def layer_stack(self):
        return list(self.stack)

    def layer_record(self, name, base=False):
        return curvedata.layer_record(name, base=base)

    def layer_plugs(self, name):
        return set(self.holds.get(name, ()))

    def curve_for(self, plug, layer):
        self.asked.append((layer, plug))
        return self.curves.get((layer, plug))

    def feed_of(self, plug):
        return self.feeds.get(plug, ("curve", None))

    def layer_static(self, plug, layer):
        return self.statics.get((layer, plug))


class FakeCmds(object):

    def __init__(self, values=None, infinity=None):
        self.values = dict(values or {})
        self.infinity = dict(infinity or {})

    def getAttr(self, plug):
        node, _dot, attr = plug.rpartition(".")
        if attr in ("preInfinity", "postInfinity"):
            return self.infinity.get(node, (0, 0))[attr == "postInfinity"]
        return self.values[plug]


def copy(curve, start, end):
    return {"keys": [[float(start), 1.0], [float(end), 2.0]], "weighted": False,
            "breakdown": [], "from": curve}


class Case(unittest.TestCase):

    def use(self, keys=None, cmds=None):
        for name, fake in (("keys", keys), ("cmds", cmds)):
            if fake is not None:
                self.addCleanup(setattr, cc, name, getattr(cc, name))
                setattr(cc, name, fake)


class Stack(Case):

    def test_no_layers_is_the_base_alone_on_the_plain_curves(self):
        self.use(FakeKeys())
        self.assertEqual(cc.stack(), [(None, curvedata.layer_record(curvedata.BASE, base=True))])

    def test_the_root_is_the_base_whatever_its_name(self):
        self.use(FakeKeys(stack=["skeldarTabsLayerRoot", "AnimLayer1"]))
        names = [(scene, record["name"]) for scene, record in cc.stack()]
        self.assertEqual(names, [("skeldarTabsLayerRoot", curvedata.BASE),
                                 ("AnimLayer1", "AnimLayer1")])


class ChannelCurves(Case):

    def test_a_layered_channel_keeps_each_layers_curve_with_its_infinity(self):
        keys = FakeKeys(stack=["BaseAnimation", "AnimLayer1"],
                        holds={"AnimLayer1": ["a.rx"]},
                        curves={("BaseAnimation", "a.rx"): "c0", ("AnimLayer1", "a.rx"): "c1",
                                ("BaseAnimation", "a.tx"): "c2"},
                        feeds={"a.rx": ("layer", "blend")})
        self.use(keys, FakeCmds(infinity={"c1": (0, 3)}))
        layers = cc.stack()
        found, driven = cc.channel_curves(["a.rx", "a.tx"], 0, 10, copy, layers)
        self.assertEqual(driven, [])
        self.assertEqual(list(found["a.rx"]), [curvedata.BASE, "AnimLayer1"])
        self.assertEqual(found["a.rx"]["AnimLayer1"]["from"], "c1")
        self.assertEqual((found["a.rx"]["AnimLayer1"]["pre"], found["a.rx"]["AnimLayer1"]["post"]),
                         ("constant", "cycle"))
        self.assertEqual(list(found["a.tx"]), [curvedata.BASE])
        self.assertNotIn(("AnimLayer1", "a.tx"), keys.asked)     # the layer does not hold it

    def test_a_layer_holding_a_channel_without_a_curve_keeps_its_static(self):
        # 2026-10-29: Add Selected Objects on an override layer froze the unkeyed channels there;
        # the card dropped them and the paste showed the base under them
        keys = FakeKeys(stack=["BaseAnimation", "Over"], holds={"Over": ["a.rx", "a.ry"]},
                        curves={("BaseAnimation", "a.rx"): "c0", ("Over", "a.rx"): "c1"},
                        statics={("Over", "a.ry"): 33.0, ("BaseAnimation", "a.ry"): 5.0},
                        feeds={"a.rx": ("layer", "blend"), "a.ry": ("layer", "blend")})
        self.use(keys, FakeCmds())
        found, _driven = cc.channel_curves(["a.rx", "a.ry"], 0, 10, copy, cc.stack())
        self.assertEqual(found["a.ry"], {curvedata.BASE: {"static": 5.0}, "Over": {"static": 33.0}})
        self.assertEqual(found["a.rx"]["Over"]["from"], "c1")

    def test_a_layer_answering_no_static_adds_nothing(self):
        keys = FakeKeys(stack=["BaseAnimation", "Add"], holds={"Add": ["a.rx"]},
                        curves={("BaseAnimation", "a.rx"): "c0"},
                        feeds={"a.rx": ("layer", "blend")})
        self.use(keys, FakeCmds())
        found, _driven = cc.channel_curves(["a.rx"], 0, 10, copy, cc.stack())
        self.assertEqual(list(found["a.rx"]), [curvedata.BASE])

    def test_a_free_channel_is_a_static_on_the_base(self):
        self.use(FakeKeys(feeds={"a.ry": ("free", None)}), FakeCmds(values={"a.ry": 7.0}))
        found, _driven = cc.channel_curves(["a.ry"], 0, 10, copy, cc.stack())
        self.assertEqual(found["a.ry"], {curvedata.BASE: {"static": 7.0}})

    def test_a_driven_channel_keeps_no_curve_and_is_named(self):
        self.use(FakeKeys(feeds={"a.rz": ("driven", "orient1")}))
        found, driven = cc.channel_curves(["a.rz"], 0, 10, copy, cc.stack())
        self.assertEqual((dict(found), driven), ({}, ["a.rz"]))
        self.assertIn("1 channel", cc.driven_note(driven))
        self.assertEqual(cc.driven_note([]), "")


class NodeCurves(Case):

    def test_each_nodes_channels_by_leaf_in_the_nodes_order(self):
        keys = FakeKeys(feeds={"|a|ns:b.ry": ("driven", "orient1")},
                        curves={(None, "|a|ns:b.rx"): "c0", (None, "|c.tx"): "c1"})
        self.use(keys, FakeCmds())
        saved = cc.objs.channel_names
        self.addCleanup(setattr, cc.objs, "channel_names", saved)
        cc.objs.channel_names = lambda path, cmds: {"|a|ns:b": ["rx", "ry"], "|c": ["tx"],
                                                    "|d": []}[path]
        found, driven = cc.node_curves(["|c", "|a|ns:b", "|d"], 0, 10, copy, cc.stack())
        self.assertEqual([node["name"] for node in found], ["c", "b"])
        self.assertEqual(found[1]["attrs"]["rx"][curvedata.BASE]["from"], "c0")
        self.assertEqual(driven, ["|a|ns:b.ry"])

    def test_a_control_naming_the_whole_body_is_whole(self):
        saved = cc.scene._control_bones
        self.addCleanup(setattr, cc.scene, "_control_bones", saved)
        cc.scene._control_bones = lambda leaf, bones: cc.scene._WHOLE if leaf == "Main" else [
            "hand_l"]
        self.assertEqual(cc._named("Main", {}), curvedata.WHOLE)
        self.assertEqual(cc._named("FKWrist_L", {}), ["hand_l"])


class UsedRecords(Case):

    def test_the_base_first_then_the_used_layers_in_stack_order(self):
        self.use(FakeKeys(stack=["Root", "A", "B", "C"]))
        layers = cc.stack()
        used = cc.used_records(layers, [{"C": {}}, {"A": {}}])
        self.assertEqual([r["name"] for r in used], [curvedata.BASE, "A", "C"])


class CharacterNodes(Case):

    def test_a_skeleton_keeps_its_member_joints(self):
        ref = type("Ref", (), {"kind": "skeleton", "rig": None})()
        bones = OrderedDict([("pelvis", {"path": "|root|pelvis"}),
                             ("hand_l", {"path": "|root|pelvis|hand_l"})])
        self.assertEqual(cc.character_nodes(ref, bones, ["hand_l"]), ["|root|pelvis|hand_l"])

    def test_a_rig_keeps_the_controls_whose_bones_meet_the_members(self):
        rig = type("Rig", (), {"control_set": "Manny_Rig1:ControlSet"})()
        ref = type("Ref", (), {"kind": "rig", "rig": rig})()

        class Cmds(object):
            def sets(self, name, query=False):
                return ["Manny_Rig1:FKWrist_L", "Manny_Rig1:FKWrist_R", "Manny_Rig1:Main"]

            def ls(self, names, long=False):
                return ["|r|" + name for name in names]
        self.use(cmds=Cmds())
        saved = cc._named
        self.addCleanup(setattr, cc, "_named", saved)
        cc._named = lambda leaf, bones: {"FKWrist_L": ["hand_l"], "FKWrist_R": ["hand_r"]}.get(
            leaf, curvedata.WHOLE)
        saved_whole = cc.scene.whole_body
        self.addCleanup(setattr, cc.scene, "whole_body", saved_whole)
        cc.scene.whole_body = lambda bones: ["pelvis", "hand_l", "hand_r"]
        self.assertEqual(cc.character_nodes(ref, {}, ["hand_l"]), ["|r|Manny_Rig1:FKWrist_L"])
        self.assertEqual(cc.character_nodes(ref, {}, ["pelvis", "hand_l", "hand_r"]),
                         ["|r|Manny_Rig1:FKWrist_L", "|r|Manny_Rig1:FKWrist_R",
                          "|r|Manny_Rig1:Main"])


if __name__ == "__main__":
    unittest.main()
