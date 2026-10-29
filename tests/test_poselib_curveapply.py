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
        self.locked, self.edits = locked, []

    def animLayer(self, *args, **kwargs):
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


class LayersText(unittest.TestCase):

    def test_made_layers_are_said(self):
        text = ca._layers_text([curvedata.BASE, "AnimLayer1"],
                               {curvedata.BASE: None, "AnimLayer1": "AnimLayer2"}, ["AnimLayer2"])
        self.assertEqual(text, "BaseAnimation + AnimLayer2 (made)")


if __name__ == "__main__":
    unittest.main()
