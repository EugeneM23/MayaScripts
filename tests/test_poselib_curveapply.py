"""maya_poselib.curveapply - the paste of a card's original curves (spec 2026-10-28, «Paste»).
The scene halves stand on seams (module attributes rebound per test); the whole press is the
mayapy verify's (`verify_poselib_curves.py`)."""

import unittest
from collections import OrderedDict

from maya_poselib import animdata
from maya_poselib import curveapply as ca
from maya_poselib import curvedata

BASE = curvedata.layer_record(curvedata.BASE, base=True)
ADD = curvedata.layer_record("AnimLayer1")
HEADER = {"name": "Walk", "start": 0.0, "end": 10.0, "key_times": [0.0, 10.0],
          "character": {"model": "Manny", "kind": "rig"},
          "curves": curvedata.summary([BASE, ADD], 1)}
KEYED = {"keys": [[0.0, 1.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0],
                  [10.0, 3.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0]],
         "weighted": False, "breakdown": [], "pre": "constant", "post": "cycle"}


class Ref(object):
    def __init__(self, model="Manny", kind="rig"):
        self.model, self.kind = model, kind


class Matches(unittest.TestCase):

    def test_the_same_model_and_kind(self):
        self.assertTrue(ca.matches(HEADER, Ref()))
        self.assertFalse(ca.matches(HEADER, Ref("Creep")))
        self.assertFalse(ca.matches(HEADER, Ref(kind="skeleton")))
        self.assertFalse(ca.matches({"character": {}}, Ref()))


class Planned(unittest.TestCase):

    def test_the_chosen_layers_clipped_and_moved_to_the_paste(self):
        plan = animdata.paste_plan(0, 10, [0, 10], animdata.Options(), 20)
        groups = [("Manny_Rig1", "controls",
                   OrderedDict([("c.rx", {curvedata.BASE: KEYED, "AnimLayer1": {"static": 2.0}})]),
                   [])]
        planned = ca._planned(groups, ["AnimLayer1"], plan)
        self.assertEqual(list(planned), [(0, "c.rx")])
        stored, weighted, breaks, pre, post = planned[(0, "c.rx")]["AnimLayer1"]
        self.assertEqual(stored, [[20.0, 2.0]])
        planned = ca._planned(groups, [curvedata.BASE], plan)
        stored, _w, _b, pre, post = planned[(0, "c.rx")][curvedata.BASE]
        self.assertEqual([key[:2] for key in stored], [[20.0, 1.0], [30.0, 3.0]])
        self.assertEqual((pre, post), ("constant", "cycle"))


class Refusals(unittest.TestCase):

    def seam(self, name, value):
        owner, attr = name
        self.addCleanup(setattr, owner, attr, getattr(owner, attr))
        setattr(owner, attr, value)

    def test_no_layer_picked(self):
        self.assertEqual(ca.paste(HEADER, [], animdata.Options(layers=("Gone",))),
                         (False, ca.NO_LAYER))

    def test_a_locked_namesake_refuses_before_anything_is_written(self):
        self.seam((ca.aa, "_plan"), lambda header, options: animdata.paste_plan(
            0, 10, [], options, 0))
        self.seam((ca.keys, "existing_layers"), lambda: [
            {"name": "AnimLayer1", "override": False, "rotation": "component", "locked": True}])
        ok, line = ca.paste(HEADER, [], animdata.Options())
        self.assertFalse(ok)
        self.assertIn("AnimLayer1 is locked", line)


class FakeCmds(object):
    def __init__(self, locked=False):
        self.locked, self.edits, self.muted = locked, [], False

    def animLayer(self, *args, **kwargs):
        if kwargs.get("mute"):
            return self.muted
        if kwargs.get("root"):
            return "BaseAnimation"
        return self.locked if kwargs.get("lock") else None

    def keyframe(self, curve, **kwargs):
        self.edits.append(kwargs["time"])

    def getAttr(self, plug, time=None):
        return 0.0


class FixRound(unittest.TestCase):

    seam = Refusals.seam

    def test_a_locked_base_refuses_before_anything_is_written(self):
        self.seam((ca.aa, "_plan"), lambda header, options: animdata.paste_plan(
            0, 10, [], options, 0))
        self.seam((ca.keys, "existing_layers"), lambda: [])
        self.seam((ca, "cmds"), FakeCmds(locked=True))
        ok, line = ca.paste(HEADER, [], animdata.Options(layers=(curvedata.BASE,)))
        self.assertFalse(ok)
        self.assertIn("BaseAnimation is locked", line)

    def test_connect_moves_only_the_pasted_keys(self):
        fake = FakeCmds()
        self.seam((ca, "cmds"), fake)
        self.seam((ca.keys, "curve_for"), lambda plug, layer: "curve")
        self.seam((ca.keys, "_weight"), lambda layer: 1.0)
        plan = animdata.paste_plan(0, 10, [0, 10], animdata.Options(), 20)
        planned = OrderedDict([((0, "c.rx"), {"AnimLayer1": ([[20.0, 2.0], [30.0, 3.0]],
                                                              False, [], None, None)})])
        ca._connect(planned, {"c.rx": 5.0}, plan, "AnimLayer1", ADD)
        self.assertEqual(fake.edits, [(20.0, 20.0), (30.0, 30.0)])


class MutedConnect(unittest.TestCase):

    seam = Refusals.seam

    def test_connect_skips_a_muted_target_layer(self):
        fake = FakeCmds()
        fake.muted = True
        self.seam((ca, "cmds"), fake)
        self.seam((ca.keys, "curve_for"), lambda plug, layer: "curve")
        self.seam((ca.keys, "_weight"), lambda layer: 1.0)
        plan = animdata.paste_plan(0, 10, [0, 10], animdata.Options(), 20)
        planned = OrderedDict([((0, "c.rx"), {"AnimLayer1": ([[20.0, 2.0]], False, [], None, None)})])
        notes = ca._connect(planned, {"c.rx": 5.0}, plan, "AnimLayer1", ADD)
        self.assertEqual(fake.edits, [])
        self.assertEqual(notes, [ca.CONNECT_MUTED % "AnimLayer1"])


class LayersText(unittest.TestCase):

    def test_made_layers_are_said(self):
        text = ca._layers_text([curvedata.BASE, "AnimLayer1"],
                               {curvedata.BASE: None, "AnimLayer1": "AnimLayer2"}, ["AnimLayer2"])
        self.assertEqual(text, "BaseAnimation + AnimLayer2 (made)")

    def test_a_scene_tabs_root_is_said_as_the_base(self):
        text = ca._layers_text([curvedata.BASE], {curvedata.BASE: "skeldarTabsLayerRoot"}, [])
        self.assertEqual(text, "BaseAnimation")


class StackCmds(object):
    """`cmds` over a layer stack: {layer: (override, muted, {plug: [key times]})}."""

    def __init__(self, layers, root="BaseAnimation"):
        self.layers, self.root, self.dirtied = layers, root, []

    def animLayer(self, name=None, query=False, root=False, override=False, mute=False,
                  parent=False):
        if parent:
            return self.root
        if root:
            return self.root
        if override:
            return self.layers[name][0]
        if mute:
            return self.layers[name][1]
        return None

    def keyframe(self, curve, query=False, timeChange=False):
        layer, plug = curve
        return list(self.layers[layer][2].get(plug) or [])

    def getAttr(self, plug):
        return 1

    def dgdirty(self, nodes):
        self.dirtied.extend(nodes)


class Seams(unittest.TestCase):

    seam = Refusals.seam

    def stack(self, layers):
        fake = StackCmds(layers)
        self.seam((ca, "cmds"), fake)
        self.seam((ca.keys, "cmds"), fake)
        self.seam((ca.keys, "layer_stack"), lambda: [fake.root] + list(layers))
        self.seam((ca.keys, "layer_plugs"), lambda name: set(fake.layers[name][2]))
        self.seam((ca.keys, "curve_for"), lambda plug, layer: (layer, plug) if layer in
                  fake.layers and fake.layers[layer][2].get(plug) else None)
        return fake


class Others(Seams):
    """2026-10-29: the target's own keys on its layers twisted the pasted controls 70 deg."""

    GROUPS = [("Manny_Rig1", "controls",
               OrderedDict([("c.rx", {curvedata.BASE: KEYED, "AnimLayer1": KEYED}),
                            ("c.ry", {curvedata.BASE: KEYED})]), [])]
    RECORDS = {curvedata.BASE: BASE, "AnimLayer1": ADD}

    def test_a_namesake_clears_what_its_card_layer_does_not_hold(self):
        self.stack(OrderedDict([("AnimLayer1", (False, False, {"c.rx": [0], "c.ry": [0]}))]))
        others = ca._others(self.GROUPS, ["AnimLayer1"], self.RECORDS,
                            {"AnimLayer1": "AnimLayer1"}, [])
        self.assertEqual(others, OrderedDict([("AnimLayer1", ["c.ry"])]))

    def test_with_the_base_pasted_every_other_layer_holding_a_card_channel(self):
        self.stack(OrderedDict([("Mine", (False, False, {"c.rx": [0], "other.tx": [0]})),
                                ("Quiet", (False, True, {"c.ry": [0]})),
                                ("Made", (False, False, {"c.rx": [0]}))]))
        others = ca._others(self.GROUPS, [curvedata.BASE], self.RECORDS,
                            {curvedata.BASE: "BaseAnimation"}, ["Made"])
        self.assertEqual(others, OrderedDict([("Mine", ["c.rx"])]))

    def test_without_the_base_another_layer_is_the_animators(self):
        self.stack(OrderedDict([("Mine", (False, False, {"c.rx": [0]}))]))
        self.assertEqual(ca._others(self.GROUPS, ["AnimLayer1"], self.RECORDS,
                                    {"AnimLayer1": "AnimLayer2"}, ["AnimLayer2"]), {})


class ClearOthers(Seams):

    def test_merge_and_an_override_layer_are_said_and_left(self):
        self.stack(OrderedDict([("Over", (True, False, {"c.rx": [0]})),
                                ("Mine", (False, False, {"c.rx": [0]}))]))
        cleared = []
        self.seam((ca, "_clear"), lambda plug, layer, plan, scale: cleared.append(layer))
        plan = animdata.paste_plan(0, 10, [], animdata.Options(mode="merge"), 0)
        notes, _reached = ca._clear_others(OrderedDict([("Over", ["c.rx"]), ("Mine", ["c.rx"])]),
                                           plan, "merge")
        self.assertEqual(notes, [ca.OVERRIDES % ("Over", 1), ca.MERGE_KEPT % ("Mine", 1)])
        self.assertEqual(cleared, [])

    def test_replace_cuts_then_clears_and_says_how_many(self):
        self.stack(OrderedDict([("Mine", (False, False, {"c.rx": [0, 5]}))]))
        ops = []
        self.seam((ca.aa, "_ops"), lambda o, plugs, layer: ops.append((o, plugs, layer)) or [2])
        self.seam((ca, "_clear"), lambda plug, layer, plan, scale: plug == "c.ry")
        plan = animdata.paste_plan(0, 10, [], animdata.Options(), 0)
        notes, reached = ca._clear_others(OrderedDict([("Mine", ["c.rx", "c.ry", "c.rz"])]),
                                          plan, "replace")
        self.assertEqual(ops, [([("cut", 0, 10)], ["c.rx", "c.ry", "c.rz"], "Mine")])
        self.assertEqual(reached, [2])
        self.assertEqual(notes, [ca.CLEARED % ("Mine", 0, 10, 2)])


class Pinned(Seams):

    PLAN = animdata.paste_plan(0, 10, [], animdata.Options(), 0)
    KEYS = [[2.0, 1.0], [8.0, 3.0]]

    def test_a_target_key_outside_pins_the_ends(self):
        self.stack(OrderedDict([("AnimLayer1", (False, False, {"c.rx": [-5.0, 20.0]}))]))
        stored, pre, post = ca._pinned("c.rx", "AnimLayer1", self.KEYS, self.PLAN, None, None,
                                       "BaseAnimation")
        self.assertEqual([key[0] for key in stored], [0.0, 2.0, 8.0, 10.0])

    def test_a_cycling_curve_is_left(self):
        self.stack(OrderedDict([("AnimLayer1", (False, False, {"c.rx": [-5.0, 20.0]}))]))
        stored, _pre, post = ca._pinned("c.rx", "AnimLayer1", self.KEYS, self.PLAN, "cycle",
                                        "cycle", "BaseAnimation")
        self.assertEqual(stored, self.KEYS)
        self.assertEqual(post, "cycle")

    def test_a_made_curve_adds_nothing_where_the_channel_moves_outside(self):
        fake = self.stack(OrderedDict([("AnimLayer1", (False, False, {}))]))
        fake.layers["BaseAnimation"] = (False, False, {"c.rx": [-10.0, 30.0]})
        stored, pre, post = ca._pinned("c.rx", "AnimLayer1", self.KEYS, self.PLAN, "cycle",
                                       None, "BaseAnimation")
        self.assertEqual([key[0] for key in stored], [-1.0, 0.0, 2.0, 8.0, 10.0, 11.0])
        self.assertEqual(stored[-1][1], 0.0)
        self.assertEqual((pre, post), ("constant", "constant"))

    def test_a_made_curve_on_a_still_target_is_the_cards(self):
        fake = self.stack(OrderedDict([("AnimLayer1", (False, False, {}))]))
        fake.layers["BaseAnimation"] = (False, False, {"c.rx": [0.0, 10.0]})
        self.assertEqual(ca._pinned("c.rx", "AnimLayer1", self.KEYS, self.PLAN, None, None,
                                    "BaseAnimation")[0], self.KEYS)


class Clear(unittest.TestCase):
    """A layer cleared on a channel adds nothing over the range, and only there."""

    seam = Refusals.seam
    PLAN = animdata.paste_plan(0, 10, [], animdata.Options(), 20)

    def keys_seams(self, curve=None, static=None):
        written = []
        self.seam((ca.keys, "curve_for"), lambda plug, layer: curve)
        self.seam((ca.keys, "layer_static"), lambda plug, layer: static)
        self.seam((ca.keys, "write_raw"), lambda plug, layer, stored: written.append(
            (plug, layer, stored)) or type("W", (), {"plugs": [plug]})())
        return written

    def test_a_curve_is_keyed_flat_at_identity_at_both_ends(self):
        written = self.keys_seams(curve="c_rotateX_Mine")
        self.assertTrue(ca._clear("c.rotateX", "Mine", self.PLAN, "multiply"))
        self.assertEqual(written, [("c.rotateX", "Mine", [[20.0, 0.0, "flat", "flat"],
                                                          [30.0, 0.0, "flat", "flat"]])])

    def test_a_scale_by_multiply_is_cleared_to_one(self):
        written = self.keys_seams(curve="c_scaleX_Mine")
        ca._clear("c.scaleX", "Mine", self.PLAN, "multiply")
        self.assertEqual([key[1] for key in written[0][2]], [1.0, 1.0])

    def test_a_static_off_identity_stands_outside_the_range(self):
        written = self.keys_seams(static=12.0)
        self.assertTrue(ca._clear("c.rotateX", "Mine", self.PLAN, "multiply"))
        self.assertEqual([key[:2] for key in written[0][2]],
                         [[19.0, 12.0], [20.0, 0.0], [30.0, 0.0], [31.0, 12.0]])

    def test_a_static_at_identity_or_none_is_nothing_to_clear(self):
        written = self.keys_seams(static=0.0)
        self.assertFalse(ca._clear("c.rotateX", "Mine", self.PLAN, "multiply"))
        written = self.keys_seams(static=None)
        self.assertFalse(ca._clear("c.rotateX", "Mine", self.PLAN, "multiply"))
        self.assertEqual(written, [])


class Layers(unittest.TestCase):

    seam = Refusals.seam

    def test_made_bottom_to_top_and_the_base_the_root_after_them(self):
        made_now = []
        fake = FakeCmds()
        self.seam((ca, "cmds"), fake)
        self.seam((ca.keys, "make_layer"), lambda record: made_now.append(record["name"]) or
                  record["name"] + "1")
        where = OrderedDict([(curvedata.BASE, ("base", None)), ("Fix", ("make", None)),
                             ("AnimLayer1", ("layer", "AnimLayer1"))])
        records = {curvedata.BASE: BASE, "Fix": curvedata.layer_record("Fix"), "AnimLayer1": ADD}
        made = []
        out = ca._layers(where, records, made)
        self.assertEqual(out, {curvedata.BASE: "BaseAnimation", "Fix": "Fix1",
                               "AnimLayer1": "AnimLayer1"})
        self.assertEqual((made_now, made), (["Fix"], ["Fix1"]))


class Channels(unittest.TestCase):
    """The card's nodes paired with the target's by leaf, kept to what the card holds for the
    target's members, Selected only and In place applied."""

    seam = Refusals.seam

    class Cmds(object):
        def __init__(self, attrs):
            self.attrs = attrs

        def sets(self, name, query=False):
            return ["ns:FKWrist_R", "ns:Main", "ns:FKElbow_R"]

        def ls(self, names, long=False, dag=False, type=None):
            if dag:
                return ["|root", "|root|pelvis"]
            return ["|r|" + name for name in names]

        def attributeQuery(self, attr, node=None, exists=False):
            return attr in self.attrs

    def setUp(self):
        rig = type("Rig", (), {"control_set": "ns:ControlSet"})()
        self.ref = type("Ref", (), {"kind": "rig", "rig": rig, "root": "|root"})()
        self.seam((ca, "cmds"), self.Cmds({"rotateX"}))
        self.seam((ca.scene, "skeleton"), lambda ref, skip: ({}, None))
        self.seam((ca.curvecapture, "character_nodes"), lambda ref, bones, members: [
            "|r|ns:FKWrist_R", "|r|ns:Main"])
        self.seam((ca.aa, "_main_of"), lambda ref: "|r|ns:Main")
        self.seam((ca.ap, "target_label"), lambda ref: "ns")
        self.curves = {"nodes": [
            {"name": "FKWrist_R", "attrs": {"rotateX": {curvedata.BASE: KEYED},
                                            "twist": {curvedata.BASE: KEYED}}},
            {"name": "Main", "attrs": {"rotateX": {curvedata.BASE: KEYED}}},
            {"name": "FKElbow_R", "attrs": {"rotateX": {curvedata.BASE: KEYED}}},
            {"name": "Gone_ctrl", "attrs": {"rotateX": {curvedata.BASE: KEYED}}}]}

    def test_paired_kept_and_named(self):
        channels, notes = ca.character_channels({"members": []}, self.curves, self.ref)
        self.assertEqual(list(channels), ["|r|ns:FKWrist_R.rotateX", "|r|ns:Main.rotateX"])
        self.assertEqual(len(notes), 2)
        self.assertIn("Gone_ctrl", notes[0])
        self.assertIn("FKWrist_R.twist", notes[1])

    def test_in_place_leaves_main_and_selected_only_keeps_the_selected(self):
        channels, _notes = ca.character_channels({}, self.curves, self.ref, in_place=True)
        self.assertEqual(list(channels), ["|r|ns:FKWrist_R.rotateX"])
        channels, _notes = ca.character_channels({}, self.curves, self.ref,
                                                 only=["|r|ns:Main"])
        self.assertEqual(list(channels), ["|r|ns:Main.rotateX"])

    def test_a_skeleton_pairs_its_joints_and_keeps_its_root_in_place(self):
        skeleton = type("Ref", (), {"kind": "skeleton", "rig": None, "root": "|root"})()
        self.assertEqual(ca.target_nodes(skeleton), ["|root", "|root|pelvis"])
        self.seam((ca.skelsolve, "root_leaf"), lambda ref, bones: "root")
        self.assertEqual(ca._root_node(skeleton, {"root": {"path": "|root"}}), "|root")
        self.assertEqual(ca._root_node(self.ref, {}), "|r|ns:Main")

    def test_objects_take_their_layers(self):
        layered = dict(KEYED, layers={curvedata.BASE: KEYED, "PropLayer": {"static": 0.0}})
        self.seam((ca.aa, "_object_channels"), lambda matched: (
            OrderedDict([("|prop.tx", KEYED), ("|prop.rx", layered)]), ["note"], ["|prop"]))
        channels, notes, paths = ca.objects_channels([({}, "|prop")])
        self.assertEqual(channels["|prop.tx"], {curvedata.BASE: KEYED})
        self.assertEqual(sorted(channels["|prop.rx"]), [curvedata.BASE, "PropLayer"])
        self.assertEqual((notes, paths), (["note"], ["|prop"]))


class Refresh(unittest.TestCase):
    """2026-10-29: after an Insert the current frame stood 77 deg off until the time moved."""

    seam = Refusals.seam

    def test_every_node_feeding_the_plug_is_dirtied(self):
        links = {"c.rx": "c_rotate_Top.outputX", "c_rotate_Top.inputBX": "c_rx_Top.output",
                 "c_rotate_Top.inputAX": "c_rotate_Add.outputX",
                 "c_rotate_Add.inputAX": "c_rotateX.output"}
        types = {"c_rotate_Top": "animBlendNodeAdditiveRotation",
                 "c_rotate_Add": "animBlendNodeAdditiveRotation", "c_rotateX": "animCurveTA"}

        class Cmds(object):
            dirtied = []

            def listConnections(self, plug, **kwargs):
                return [links[plug]] if plug in links else []

            def nodeType(self, node):
                return types.get(node, "animCurveTA")

            def dgdirty(self, nodes):
                self.dirtied.extend(nodes)
        fake = Cmds()
        self.seam((ca, "cmds"), fake)
        self.seam((ca.keys, "cmds"), fake)
        ca._refresh(["c.rx", "c.free"])
        self.assertEqual(fake.dirtied, ["c_rotate_Top", "c_rx_Top", "c_rotate_Add", "c_rotateX"])


class ConnectBounds(unittest.TestCase):

    seam = Refusals.seam

    def test_connect_leaves_the_bounds_outside_the_range(self):
        fake = FakeCmds()
        self.seam((ca, "cmds"), fake)
        self.seam((ca.keys, "curve_for"), lambda plug, layer: "curve")
        self.seam((ca.keys, "_weight"), lambda layer: 1.0)
        plan = animdata.paste_plan(0, 10, [0, 10], animdata.Options(), 20)
        planned = OrderedDict([((0, "c.rx"), {"AnimLayer1": (
            [[19.0, 0.0], [20.0, 2.0], [30.0, 3.0], [31.0, 0.0]], False, [], None, None)})])
        ca._connect(planned, {"c.rx": 5.0}, plan, "AnimLayer1", ADD)
        self.assertEqual(fake.edits, [(20.0, 20.0), (30.0, 30.0)])


if __name__ == "__main__":
    unittest.main()
