"""1P upper body (2026-10-21): a card cut to the bones above its chest, the camera on the chest."""

import unittest

from maya_poselib import upper


def _bone(parent, canonical=None):
    out = {"parent": parent}
    if canonical:
        out["canonical"] = canonical
    return out


BONES = {
    "root": _bone(None), "pelvis": _bone("root"), "spine_01": _bone("pelvis"),
    "spine_02": _bone("spine_01"), "spine_03": _bone("spine_02", "spine_03"),
    "spine_04": _bone("spine_03"), "spine_05": _bone("spine_04"), "neck_01": _bone("spine_05"),
    "head": _bone("neck_01"), "clavicle_r": _bone("spine_05"), "upperarm_r": _bone("clavicle_r"),
    "hand_r": _bone("upperarm_r"), "weapon_r": _bone("hand_r"), "thigh_l": _bone("pelvis"),
    "foot_l": _bone("thigh_l"), "camera_root": _bone("root"), "camera_bone": _bone("camera_root"),
}
MEMBERS = ["pelvis", "spine_01", "spine_03", "spine_04", "spine_05", "head", "clavicle_r",
           "upperarm_r", "hand_r", "thigh_l", "foot_l"]


class Restrict(unittest.TestCase):
    def test_only_the_bones_above_the_chest_stay_members(self):
        card, note = upper.restrict({"kind": "character", "bones": BONES, "members": MEMBERS})
        kept = [m for m in card["members"] if m not in upper.CAMERA]
        # the card's own selection first, then every other bone above the chest it holds (the
        # neck was not selected: a card holds every bone); the weapon bone comes with the hand
        self.assertEqual(kept, ["spine_03", "spine_04", "spine_05", "head", "clavicle_r",
                                "upperarm_r", "hand_r", "neck_01"])
        self.assertIn("8 bones", note)

    def test_the_camera_comes_anchored_on_the_chest(self):
        card, _note = upper.restrict({"kind": "character", "bones": BONES, "members": MEMBERS})
        self.assertIn("camera_root", card["members"])
        self.assertIn("camera_bone", card["members"])
        self.assertEqual(upper.anchors_for(card["bones"], card["members"]),
                         {"camera_root": "spine_03"})

    def test_the_card_itself_is_not_changed(self):
        data = {"kind": "character", "bones": BONES, "members": list(MEMBERS)}
        card, _note = upper.restrict(data)
        self.assertEqual(data["members"], MEMBERS)
        self.assertNotIn("anchors", data)
        self.assertNotIn("anchors", card)       # derived at every press (`anchors_for`)

    def test_no_chest_and_nothing_above_it_are_refused(self):
        bones = dict(BONES)
        bones.pop("spine_03")
        bones["spine_04"] = _bone("spine_02")
        self.assertEqual(upper.restrict({"bones": bones, "members": MEMBERS}),
                         (None, upper.NO_CHEST))
        self.assertEqual(upper.restrict({"bones": BONES, "members": ["thigh_l", "pelvis"]}),
                         (None, upper.NO_UPPER))

    def test_an_objects_card_is_left_alone(self):
        data = {"kind": "objects", "objects": []}
        self.assertEqual(upper.restrict(data), (data, ""))

    def test_the_chest_is_found_by_its_canonical_name_first(self):
        bones = {"Hips": _bone(None), "Chest": _bone("Hips", "spine_03"),
                 "spine_03": _bone("Hips")}
        self.assertEqual(upper.chest_of(bones), "Chest")


FULL_TORSO = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "head",
              "camera_root", "camera_bone"]


class AnchorsFor(unittest.TestCase):
    """2026-10-21: the camera rides the chest whenever the chest stands on the target's own spine
    - any card that poses its chest but not the whole torso under it, cut by 1P upper body or saved
    so - not only a card the option cut."""

    def test_an_upper_body_card_hangs_the_camera_on_its_chest(self):
        self.assertEqual(upper.anchors_for(BONES, ["spine_03", "spine_04", "head", "camera_root"]),
                         {"camera_root": "spine_03"})

    def test_a_gap_in_the_torso_under_the_chest_hangs_it_there_too(self):
        # the pelvis and the chest posed, spine_02 not (the animator's DG_Idle_1P)
        self.assertEqual(upper.anchors_for(BONES, ["pelvis", "spine_01", "spine_03", "camera_root"]),
                         {"camera_root": "spine_03"})

    def test_a_whole_torso_keeps_the_camera_on_its_root(self):
        self.assertEqual(upper.anchors_for(BONES, FULL_TORSO), {})

    def test_no_chest_posed_anchors_nothing(self):
        self.assertEqual(upper.anchors_for(BONES, ["head", "hand_r", "camera_root"]), {})
        self.assertEqual(upper.anchors_for({"root": _bone(None)}, ["root"]), {})


class TargetAnchors(unittest.TestCase):
    def test_source_anchors_map_onto_the_target_through_the_pairs(self):
        pairs = {"ns:camera_root": "camera_root", "ns:spine_03": "spine_03"}
        self.assertEqual(upper.target_anchors({"camera_root": "spine_03"}, pairs),
                         {"ns:camera_root": "ns:spine_03"})
        self.assertEqual(upper.target_anchors(None, pairs), {})
        self.assertEqual(upper.target_anchors({"camera_root": "spine_03"}, {}), {})


try:
    import maya.api.OpenMaya as om
    from maya_poselib import posemath as pm
except ImportError:                                   # plain Python: the pure half only
    om = None


@unittest.skipIf(om is None, "needs maya.api.OpenMaya")
class AnchoredTransfer(unittest.TestCase):
    """An anchored member keeps its place and turn on the anchor - not on its own parent."""

    def _skeleton(self, chest_y, camera_y):
        def at(x, y, z):
            return pm.flat(om.MMatrix([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1]))
        world = {"root": at(0, 0, 0), "spine_03": at(0, chest_y, 0),
                 "camera_root": at(0, camera_y, 5)}
        parents = {"root": None, "spine_03": "root", "camera_root": "root"}
        rest = {"root": at(0, 0, 0), "spine_03": at(0, 100, 0), "camera_root": at(0, 160, 5)}
        return dict((leaf, {"parent": parents[leaf], "world": world[leaf], "rest": rest[leaf],
                            "canonical": leaf}) for leaf in world)

    PAIRS = {"root": "root", "spine_03": "spine_03", "camera_root": "camera_root"}

    def test_the_camera_rides_the_target_chest(self):
        source = self._skeleton(chest_y=100, camera_y=180)     # the card's camera 80 over its chest
        target = self._skeleton(chest_y=90, camera_y=150)      # the target's chest stands lower
        out = pm.Transfer(source, target, self.PAIRS, ["camera_root"],
                          anchors={"camera_root": "spine_03"}).frame()
        self.assertAlmostEqual(pm.position(out["camera_root"]).y, 170.0, places=4)   # 90 + 80
        self.assertAlmostEqual(pm.position(out["camera_root"]).z, 5.0, places=4)

    def test_without_the_anchor_it_rides_its_parent(self):
        # its rest local (160 over the root) plus the card's move from its rest (+20): the root's
        # rule, the chest's 10 cm drop not followed
        source = self._skeleton(chest_y=100, camera_y=180)
        target = self._skeleton(chest_y=90, camera_y=150)
        out = pm.Transfer(source, target, self.PAIRS, ["camera_root"]).frame()
        self.assertAlmostEqual(pm.position(out["camera_root"]).y, 180.0, places=4)


if __name__ == "__main__":
    unittest.main()
