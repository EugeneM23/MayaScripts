"""The 3ds Max "Base Human" Biped convention (2026-11-01, the Swordman).

The animator's character came in on a Biped named `Base Human Pelvis`,
`Base Human LCollarbone` and so on -- a space, which an FBX escapes as
`FBXASC032`. The tokeniser already read those names and got the SIDES right;
three words were wrong, and each test here fails on the map as it was:

  * `collarbone` is one token, and `parse` looked for `collar`, so a clavicle
    read as nothing;
  * `palm` is 3ds Max's name for the HAND, while our map reads it as a
    metacarpal and drops it from the arm chain -- so the forearm became the
    hand and every arm was off by one joint;
  * Biped's `UpVectorNode` and `Platform` helpers read as limbs.

Without them the structural fallback still mapped the skeleton, and mapped it
wrong: left and right swapped, and the 26 cm collarbone taken for the upper
arm.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim"))

import maya_skeletonmap as sm

P = "BaseFBXASC032Human"


class Words(unittest.TestCase):
    def test_a_collarbone_is_a_clavicle(self):
        self.assertEqual(sm.parse(P + "LCollarbone").kind, "clavicle")
        self.assertEqual(sm.parse(P + "LCollarbone").side, "l")

    def test_the_side_is_read_through_the_fbx_space_escape(self):
        self.assertEqual(sm.parse(P + "RForearm").side, "r")
        self.assertEqual(sm.parse(P + "RForearm").kind, "lowerarm")

    def test_bipeds_up_vector_helper_is_ignored(self):
        self.assertEqual(sm.parse(P + "LUpVectorNode").kind, "ignore")

    def test_bipeds_foot_platform_is_ignored(self):
        self.assertEqual(sm.parse(P + "LPlatform").kind, "ignore")


def _skeleton():
    """His hierarchy and bind positions, measured over the port 2026-11-01."""
    parent = {
        "Pelvis": None, "Spine1": "Pelvis", "Spine2": "Spine1", "Spine3": "Spine2",
        "Spine4": "Spine3", "Ribcage": "Spine4", "Neck1": "Ribcage",
        "Neck2": "Neck1", "Head": "Neck2",
        "LCollarbone": "Ribcage", "LUpperarm": "LCollarbone",
        "LForearm": "LUpperarm", "LPalm": "LForearm",
        "RCollarbone": "Ribcage", "RUpperarm": "RCollarbone",
        "RForearm": "RUpperarm", "RPalm": "RForearm",
        "LThigh": "Pelvis", "LCalf": "LThigh", "LFoot": "LCalf",
        "RThigh": "Pelvis", "RCalf": "RThigh", "RFoot": "RCalf",
        "LUpVectorNode": "Pelvis", "RUpVectorNode": "Pelvis",
    }
    pos = {
        "Pelvis": (0.0, 83.473, -7.065), "Spine1": (0.0, 87.971, -7.424),
        "Spine2": (0.0, 101.028, -2.979), "Spine3": (0.0, 112.776, -2.813),
        "Spine4": (0.0, 125.266, -4.661), "Ribcage": (0.0, 142.280, -4.556),
        "Neck1": (0.0, 142.356, -4.923), "Neck2": (0.0, 150.652, -3.542),
        "Head": (0.0, 158.852, -1.568),
        "LCollarbone": (2.964, 140.571, 5.436), "LUpperarm": (25.714, 137.040, -6.867),
        "LForearm": (32.044, 108.145, -8.346), "LPalm": (42.197, 86.376, -0.768),
        "RCollarbone": (-2.964, 140.571, 5.436), "RUpperarm": (-25.714, 137.040, -6.867),
        "RForearm": (-32.044, 108.145, -8.346), "RPalm": (-42.197, 86.376, -0.768),
        "LThigh": (8.659, 85.184, -2.449), "LCalf": (13.463, 40.844, -2.105),
        "LFoot": (13.884, 2.228, -8.796),
        "RThigh": (-8.659, 85.184, -2.449), "RCalf": (-13.464, 40.844, -2.105),
        "RFoot": (-13.889, 2.229, -8.800),
        "LUpVectorNode": (1.0, 83.0, -7.0), "RUpVectorNode": (-1.0, 83.0, -7.0),
    }

    def path(name):
        chain, cur = [], name
        while cur:
            chain.append(P + cur)
            cur = parent[cur]
        return "|" + "|".join(reversed(chain))

    return [path(n) for n in parent], {path(n): pos[n] for n in parent}


class Recognise(unittest.TestCase):
    def setUp(self):
        paths, pos = _skeleton()
        self.out = sm.recognize(paths, pos)

    def test_it_is_read_by_name_not_by_shape(self):
        self.assertEqual(self.out.refusal, "")
        self.assertGreaterEqual(self.out.confidence, 0.8)

    def test_the_sides_are_not_swapped(self):
        self.assertTrue(self.out.mapping["thigh_l"].endswith(P + "LThigh"))
        self.assertTrue(self.out.mapping["thigh_r"].endswith(P + "RThigh"))
        self.assertTrue(self.out.mapping["foot_l"].endswith(P + "LFoot"))

    def test_the_palm_is_the_hand_not_the_forearm(self):
        self.assertTrue(self.out.mapping["hand_l"].endswith(P + "LPalm"))
        self.assertTrue(self.out.mapping["hand_r"].endswith(P + "RPalm"))

    def test_the_arm_is_not_off_by_one_joint(self):
        self.assertTrue(self.out.mapping["lowerarm_l"].endswith(P + "LForearm"))
        self.assertTrue(self.out.mapping["upperarm_l"].endswith(P + "LUpperarm"))
        self.assertTrue(self.out.mapping["lowerarm_r"].endswith(P + "RForearm"))
        self.assertTrue(self.out.mapping["upperarm_r"].endswith(P + "RUpperarm"))

    def test_the_collarbone_is_the_clavicle(self):
        self.assertTrue(self.out.mapping["clavicle_l"].endswith(P + "LCollarbone"))
        self.assertTrue(self.out.mapping["clavicle_r"].endswith(P + "RCollarbone"))

    def test_the_head_is_the_head_and_not_the_second_neck(self):
        self.assertTrue(self.out.mapping["head"].endswith(P + "Head"))

    def test_his_five_spine_joints_land_on_our_five(self):
        for ours, his in (("spine_01", "Spine1"), ("spine_02", "Spine2"),
                          ("spine_03", "Spine3"), ("spine_04", "Spine4"),
                          ("spine_05", "Ribcage")):
            self.assertTrue(self.out.mapping[ours].endswith(P + his),
                            "%s -> %s" % (ours, self.out.mapping.get(ours)))

    def test_the_up_vector_helpers_are_never_mapped(self):
        for got in self.out.mapping.values():
            self.assertNotIn("UpVectorNode", got)


if __name__ == "__main__":
    unittest.main()
