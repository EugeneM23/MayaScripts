"""1P lower body (2026-10-22): a card cut to the bones under its chest, the target's chest kept."""

import math
import unittest

from maya_poselib import lower
from maya_poselib import upper


def _bone(parent, canonical=None):
    out = {"parent": parent}
    if canonical:
        out["canonical"] = canonical
    return out


BONES = {
    "root": _bone(None), "pelvis": _bone("root"), "spine_01": _bone("pelvis"),
    "spine_02": _bone("spine_01"), "spine_03": _bone("spine_02", "spine_03"),
    "spine_04": _bone("spine_03"), "neck_01": _bone("spine_04"), "head": _bone("neck_01"),
    "clavicle_r": _bone("spine_04"), "hand_r": _bone("clavicle_r"), "weapon_r": _bone("hand_r"),
    "thigh_l": _bone("pelvis"), "thigh_twist_01_l": _bone("thigh_l"), "calf_l": _bone("thigh_l"),
    "foot_l": _bone("calf_l"), "ball_l": _bone("foot_l"), "ik_foot_root": _bone("root"),
    "ik_foot_l": _bone("ik_foot_root"), "camera_root": _bone("root"),
    "camera_bone": _bone("camera_root"), "center_of_mass": _bone("root"),
}
MEMBERS = ["pelvis", "spine_03", "head", "hand_r", "thigh_l", "calf_l"]


class Restrict(unittest.TestCase):
    def test_every_bone_under_the_chest_is_a_member(self):
        card, note = lower.restrict({"kind": "character", "bones": BONES, "members": MEMBERS})
        # the card's own selection first, then every other bone under the chest it holds; no
        # helper, no camera, nothing of the chest and above
        self.assertEqual(card["members"], ["pelvis", "thigh_l", "calf_l", "root", "spine_01",
                                           "spine_02", "thigh_twist_01_l", "foot_l", "ball_l"])
        self.assertEqual(card["keep"], ["spine_03"])
        self.assertTrue(card["lower_1p"])
        self.assertIn("9 bones", note)

    def test_the_card_itself_is_not_changed(self):
        data = {"kind": "character", "bones": BONES, "members": list(MEMBERS)}
        lower.restrict(data)
        self.assertEqual(data["members"], MEMBERS)
        self.assertNotIn("keep", data)

    def test_no_chest_and_nothing_under_it_are_refused(self):
        bones = dict(BONES)
        bones.pop("spine_03")
        bones["spine_04"] = _bone("spine_02")
        self.assertEqual(lower.restrict({"bones": bones, "members": MEMBERS}),
                         (None, lower.NO_CHEST))
        self.assertEqual(lower.restrict({"bones": BONES, "members": ["hand_r", "head"]}),
                         (None, lower.NO_LOWER))

    def test_an_objects_card_is_left_alone(self):
        data = {"kind": "objects", "objects": []}
        self.assertEqual(lower.restrict(data), (data, ""))

    def test_an_upper_cut_and_a_lower_cut_share_nothing_but_the_camera_rule(self):
        up, _note = upper.restrict({"kind": "character", "bones": BONES, "members": MEMBERS})
        down, _note = lower.restrict({"kind": "character", "bones": BONES, "members": MEMBERS})
        self.assertFalse(set(up["members"]) & set(down["members"]))


class KeepFor(unittest.TestCase):
    def test_the_card_chest_maps_onto_the_target_through_the_pairs(self):
        pairs = {"ns:spine_03": "spine_03", "ns:pelvis": "pelvis"}
        self.assertEqual(lower.target_keep(["spine_03"], pairs, {}), ["ns:spine_03"])

    def test_an_unpaired_chest_is_the_target_s_own(self):
        target = {"Hips": _bone(None), "Chest": _bone("Hips", "spine_03")}
        self.assertEqual(lower.target_keep(["spine_03"], {}, target), ["Chest"])

    def test_nothing_kept_without_a_keep(self):
        self.assertEqual(lower.target_keep(None, {"a": "a"}, BONES), [])


try:
    import maya.api.OpenMaya as om
    from maya_poselib import posemath as pm
except ImportError:                                   # plain Python: the pure half only
    om = None


def _trs(t=(0, 0, 0), r=(0, 0, 0)):
    tm = om.MTransformationMatrix()
    tm.setRotation(om.MEulerRotation(*[math.radians(v) for v in r]))
    tm.setTranslation(om.MVector(*t), om.MSpace.kTransform)
    return tm.asMatrix()


CHAIN = [("root", None, (0, 0, 0)), ("pelvis", "root", (0, 95, 0)),
         ("spine_02", "pelvis", (0, 20, 0)), ("spine_03", "spine_02", (0, 12, 0)),
         ("head", "spine_03", (0, 50, 0)), ("thigh_l", "pelvis", (10, -5, 0))]


def _skeleton(locals_=None, place=None):
    """{leaf: bone}: world from local (translate, rotate degrees) per bone; rest at zero turns."""
    locals_ = locals_ or {}
    place = om.MMatrix() if place is None else place
    worlds, rests, out = {}, {}, {}
    for name, parent, t in CHAIN:
        rests[name] = _trs(t) * (rests[parent] if parent else om.MMatrix())
        worlds[name] = _trs(t, locals_.get(name, (0, 0, 0))) * \
            (worlds[parent] if parent else place)
        out[name] = {"parent": parent, "canonical": name, "rest": pm.flat(rests[name]),
                     "world": pm.flat(worlds[name])}
    return out


PAIRS = dict((name, name) for name, _p, _t in CHAIN)


@unittest.skipIf(om is None, "needs maya.api.OpenMaya")
class KeptTransfer(unittest.TestCase):
    """A kept bone keeps its turn against the root frame and rides its parent's result."""

    def test_the_chest_keeps_its_world_turn_under_a_turned_spine(self):
        source = _skeleton({"pelvis": (30, 0, 0)})              # the card bends forward
        target = _skeleton({"spine_03": (0, 25, 0)})            # the target's chest twisted
        out = pm.Transfer(source, target, PAIRS, ["pelvis", "spine_02"],
                          kept=["spine_03"]).frame()
        # its turn as it stood: 25 about Y, the card's 30 about X not come up into it
        self.assertAlmostEqual(pm.angle(out["spine_03"], target["spine_03"]["world"]), 0.0, 6)
        # its place on the end of the NEW spine_02: 12 along spine_02's turned Y
        end = om.MPoint(0, 12, 0) * pm.matrix(out["spine_02"])
        self.assertAlmostEqual((pm.position(out["spine_03"]) - om.MVector(end)).length(), 0.0, 6)
        # the head, no member, rides the kept chest as it rode it
        local = pm.matrix(target["head"]["world"]) * pm.matrix(target["spine_03"]["world"]).inverse()
        self.assertAlmostEqual(pm.angle(out["head"], local * out["spine_03"]), 0.0, 6)

    def test_not_kept_the_chest_rides_the_new_spine(self):
        source = _skeleton({"pelvis": (30, 0, 0)})
        target = _skeleton()
        out = pm.Transfer(source, target, PAIRS, ["pelvis", "spine_02"]).frame()
        self.assertAlmostEqual(pm.angle(out["spine_03"], _trs(r=(30, 0, 0))), 0.0, 6)

    def test_the_kept_turn_goes_with_a_moved_root_frame(self):
        source = _skeleton()
        target = _skeleton({"spine_03": (0, 25, 0)})
        root = _trs((50, 0, 20), (0, 90, 0))                     # a travel turned the root
        out = pm.Transfer(source, target, PAIRS, ["pelvis", "spine_02"],
                          kept=["spine_03"]).frame(root_world=root)
        self.assertAlmostEqual(pm.angle(out["spine_03"], _trs(r=(0, 115, 0))), 0.0, 6)

    def test_kept_read_before_replaces_what_the_target_shows_now(self):
        source = _skeleton()
        before = _skeleton({"spine_03": (0, 25, 0)})
        now = _skeleton({"spine_03": (0, -60, 0)})               # the chest's curve cut since
        transfer = pm.Transfer(source, now, PAIRS, ["pelvis", "spine_02"], kept=["spine_03"])
        read = transfer.kept_now(before)
        out = transfer.frame(target=now, kept=read)
        self.assertAlmostEqual(pm.angle(out["spine_03"], before["spine_03"]["world"]), 0.0, 6)

    def test_a_kept_bone_the_card_poses_is_posed_by_the_card(self):
        source = _skeleton({"spine_03": (0, 40, 0)})
        target = _skeleton({"spine_03": (0, 25, 0)})
        out = pm.Transfer(source, target, PAIRS, ["pelvis", "spine_02", "spine_03"],
                          kept=["spine_03"]).frame()
        self.assertAlmostEqual(pm.angle(out["spine_03"], source["spine_03"]["world"]), 0.0, 6)


if __name__ == "__main__":
    unittest.main()
