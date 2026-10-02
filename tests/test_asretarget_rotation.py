"""The rotation-only retarget (2026-09-24, the Creep rig).

The animator: «ретаргет не должен учитывать растяжение костей (привязываем только по
ротейшенам)». A rig whose group carries `skeldarRetarget = "rotation"` takes every FK
control's ROTATION only; its IK ends and poles follow the rig's OWN FK joints (a
rotation-only retarget has no source position to give an IK hand); Main and RootX_M still
carry the root motion and the hips. Every other rig keeps the twin behaviour.
"""
import unittest

import maya_asretarget as ar
import maya_rigs

from tests.test_asretarget import BONES, CONTROLS

MIXAMO_BONES = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"]
for _s in ("Left", "Right"):
    MIXAMO_BONES += [_s + b for b in ("Shoulder", "Arm", "ForeArm", "Hand", "UpLeg", "Leg", "Foot", "ToeBase")]


class TestRotationPlan(unittest.TestCase):

    def setUp(self):
        self.drives, self.missing = ar.drive_plan(CONTROLS, BONES, ar.UE5, rotation=True)
        self.by = dict((d.control, d) for d in self.drives)

    def test_nothing_is_missing(self):
        self.assertEqual(self.missing, [])

    def test_every_fk_control_takes_rotation_only(self):
        fk = [d for d in self.drives if d.control.startswith("FK")]
        self.assertEqual(len(fk), len([c for c in CONTROLS if c.startswith("FK")]))
        self.assertTrue(all(d.rotate and not d.translate and not d.own for d in fk))

    def test_root_motion_and_the_hips_still_travel(self):
        self.assertEqual((self.by["Main"].bone, self.by["Main"].translate, self.by["Main"].rotate), ("root", True, True))
        self.assertEqual((self.by["RootX_M"].bone, self.by["RootX_M"].translate, self.by["RootX_M"].rotate),
                         ("pelvis", True, True))
        self.assertFalse(self.by["Main"].own or self.by["RootX_M"].own)

    def test_the_ik_ends_follow_our_own_fk_joints(self):
        for side in ("_L", "_R"):
            self.assertEqual(self.by["IKArm" + side][1:], ("FKXWrist" + side, True, True, True))
            self.assertEqual(self.by["IKLeg" + side][1:], ("FKXAnkle" + side, True, True, True))
            self.assertEqual(self.by["IKToes" + side][1:], ("FKXToes" + side, False, True, True))

    def test_the_poles_follow_the_fk_limb(self):
        for side in ("_L", "_R"):
            self.assertEqual(self.by["PoleArm" + side][1:], ("FKXElbow" + side, True, False, True))
            self.assertEqual(self.by["PoleLeg" + side][1:], ("FKXKnee" + side, True, False, True))

    def test_no_ik_or_pole_drive_names_a_source_bone(self):
        for d in self.drives:
            if d.control.startswith(("IK", "Pole")):
                self.assertNotIn(d.bone, BONES)

    def test_a_source_without_hands_still_drives_the_ik_arms_from_our_fk(self):
        drives, missing = ar.drive_plan(CONTROLS, [b for b in BONES if not b.startswith("hand_")], ar.UE5, rotation=True)
        by = dict((d.control, d) for d in drives)
        self.assertIn("IKArm_L", by)
        self.assertIn(("FKWrist_L", "hand_l"), missing)

    def test_the_twin_default_keeps_its_fk_position_and_its_ik_follows_our_fk(self):
        drives, _ = ar.drive_plan(CONTROLS, BONES)
        by = dict((d.control, d) for d in drives)
        self.assertEqual(by["IKArm_L"][1:], ("FKXWrist_L", True, True, True))
        self.assertTrue(by["FKShoulder_L"].translate)
        self.assertTrue(all(d.own for d in drives if d.control.startswith(("IK", "Pole"))))

    def test_a_mixamo_source_gets_the_same_ik_rule(self):
        drives, _ = ar.drive_plan(CONTROLS, MIXAMO_BONES, ar.MIXAMO, rotation=True)
        by = dict((d.control, d) for d in drives)
        self.assertEqual(by["IKLeg_R"][1:], ("FKXAnkle_R", True, True, True))
        self.assertTrue(all(not d.translate for d in drives if d.control.startswith("FK")))


class TestPoleJoints(unittest.TestCase):

    def test_a_pole_names_its_fk_limb(self):
        self.assertEqual(ar.pole_joints("PoleLeg_R"), ("FKXHip_R", "FKXKnee_R", "FKXAnkle_R"))
        self.assertEqual(ar.pole_joints("PoleArm_L"), ("FKXShoulder_L", "FKXElbow_L", "FKXWrist_L"))


class FakeModeCmds(object):
    def __init__(self, attrs):
        self.attrs = attrs

    def objExists(self, name):
        return name.split(".")[0] in ("|Group", "|Creep_Rig:Group")

    def attributeQuery(self, attr, node=None, exists=False):
        return (node, attr) in self.attrs

    def getAttr(self, plug):
        node, attr = plug.split(".")
        return self.attrs[(node, attr)]


class TestRigMode(unittest.TestCase):

    def setUp(self):
        self.real = ar.cmds

    def tearDown(self):
        ar.cmds = self.real

    def test_the_mode_is_read_off_the_rigs_group(self):
        ar.cmds = FakeModeCmds({("|Group", "skeldarRetarget"): "rotation"})
        rig = maya_rigs.Rig("", "ControlSet", "|Group|MotionSystem|MainSystem|Main", "|Group", "|root")
        self.assertTrue(ar.rotation_mode(rig))

    def test_a_namespaced_rig_reads_its_own_group(self):
        ar.cmds = FakeModeCmds({("|Creep_Rig:Group", "skeldarRetarget"): "rotation"})
        rig = maya_rigs.Rig("Creep_Rig", "Creep_Rig:ControlSet", "|Creep_Rig:Group|Creep_Rig:Main",
                            "|Creep_Rig:Group", "|Creep_Rig:root")
        self.assertTrue(ar.rotation_mode(rig))

    def test_an_unmarked_rig_is_a_twin_rig(self):
        ar.cmds = FakeModeCmds({})
        rig = maya_rigs.Rig("", "ControlSet", "|Group|Main", "|Group", "|root")
        self.assertFalse(ar.rotation_mode(rig))

    def test_another_value_is_not_rotation_only(self):
        ar.cmds = FakeModeCmds({("|Group", "skeldarRetarget"): "twin"})
        rig = maya_rigs.Rig("", "ControlSet", "|Group|Main", "|Group", "|root")
        self.assertFalse(ar.rotation_mode(rig))

    def test_no_rig_is_not_rotation_only(self):
        self.assertFalse(ar.rotation_mode(None))


class TestRotationNote(unittest.TestCase):

    def test_the_note_names_the_lengths_kept_and_the_ik_rule(self):
        note = ar.rotation_note({"arm": 1.262, "leg": 1.0})
        self.assertIn("rotations only", note)
        self.assertIn("arm is +26.2%", note)
        self.assertNotIn("leg", note)
        self.assertIn("own FK", note)

    def test_equal_proportions_still_say_what_the_mode_is(self):
        self.assertIn("rotations only", ar.rotation_note({"arm": 1.0}))


if __name__ == "__main__":
    unittest.main()
