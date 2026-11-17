"""A spine numbered differently on the clip and the target (the Fighter's spine_01..04 under a
five-joint clip, 2026-11-17): chain onto chain, the chest on the clip's chest."""
import unittest

import maya_skeletonmap as skelmap
from maya_uebridge import skeletonimport as si

UE5 = ["root", "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05",
       "neck_01", "neck_02", "head", "hand_r"]
FIGHTER = ["root", "pelvis", "spine_01", "spine_02", "spine_03", "spine_04",
           "neck_01", "neck_02", "head", "hand_r", "helm"]


class ChainPairs(unittest.TestCase):

    def test_four_under_five_keeps_both_ends(self):
        self.assertEqual(skelmap.chain_pairs(UE5, FIGHTER),
                         {"spine_01": "spine_01", "spine_02": "spine_02",
                          "spine_03": "spine_04", "spine_04": "spine_05"})

    def test_the_same_count_is_left_to_the_names(self):
        self.assertEqual(skelmap.chain_pairs(UE5, UE5), {})

    def test_numbered_chain_orders_by_number(self):
        self.assertEqual(skelmap.numbered_chain(["spine_10", "spine_02", "spine_x"], "spine_"),
                         ["spine_02", "spine_10"])


class SkeletonImport(unittest.TestCase):

    def test_the_fighter_chest_takes_the_clip_chest(self):
        pairs = si.pair_bones(UE5, FIGHTER)
        self.assertEqual(pairs["spine_04"], "spine_05")
        self.assertEqual(pairs["spine_03"], "spine_04")
        self.assertEqual(pairs["neck_01"], "neck_01")
        self.assertEqual(pairs["hand_r"], "hand_r")
        self.assertNotIn("helm", pairs)

    def test_a_ue4_target_keeps_its_own_map(self):
        ue4 = ["pelvis", "spine_01", "spine_02", "spine_03"]
        self.assertEqual(si.pair_bones(UE5, ue4)["spine_03"], "spine_05")


class RigDrives(unittest.TestCase):

    def test_the_fighter_rig_fk_spine_takes_the_chain(self):
        import maya_asretarget as ar
        drives = [ar.Drive("FKSpine%d_M" % i, "spine_0%d" % i, False, True) for i in (1, 2, 3, 4)]
        drives.append(ar.Drive("FKHead_M", "head", False, True))
        drives.append(ar.Drive("IKArm_R", "FKXWrist_R", False, True, True))
        ours = dict(("FKSpine%d_M" % i, "spine_0%d" % i) for i in (1, 2, 3, 4))
        ours["FKHead_M"] = "head"
        got = ar.chain_drives(drives, ours, dict((n, n) for n in UE5),
                              dict((n, n) for n in FIGHTER), ar.UE5)
        bones = dict((d.control, d.bone) for d in got)
        self.assertEqual(bones["FKSpine3_M"], "spine_04")
        self.assertEqual(bones["FKSpine4_M"], "spine_05")
        self.assertEqual(bones["FKSpine1_M"], "spine_01")
        self.assertEqual(bones["FKHead_M"], "head")
        self.assertEqual(bones["IKArm_R"], "FKXWrist_R")

    def test_a_rig_numbered_as_the_clip_is_untouched(self):
        import maya_asretarget as ar
        drives = [ar.Drive("FKSpine%d_M" % i, "spine_0%d" % i, False, True) for i in range(1, 6)]
        ours = dict(("FKSpine%d_M" % i, "spine_0%d" % i) for i in range(1, 6))
        self.assertEqual(ar.chain_drives(drives, ours, dict((n, n) for n in UE5),
                                         dict((n, n) for n in UE5), ar.UE5), drives)


class PoseLibrary(unittest.TestCase):

    def test_a_card_pairs_the_chest_onto_the_chest(self):
        from maya_poselib import posemath
        got = posemath._by_leaf(dict((n, n) for n in UE5), dict((n, n) for n in FIGHTER))
        self.assertEqual(got["spine_04"], "spine_05")


if __name__ == "__main__":
    unittest.main()
