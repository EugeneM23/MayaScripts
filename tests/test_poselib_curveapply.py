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
