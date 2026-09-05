import unittest

import maya_asretarget as ar
import maya_pmretarget as pm
import maya_rig_retarget as rr

OWN = ["Root", "Hip", "Spine1", "Spine2", "Spine3", "Spine4", "Neck", "Head", "Right_Arm", "Left_Hand", "Right_Toes"]
UE5 = ["root", "pelvis", "spine_01", "spine_05", "upperarm_l", "hand_r", "ball_l", "neck_01", "head"]
UE4 = ["root", "pelvis", "spine_01", "spine_03", "upperarm_l", "hand_r", "ball_l", "neck_01", "head"]


class TestPick(unittest.TestCase):

    def test_the_lugal_rig_goes_to_the_playermale_module(self):
        self.assertEqual(rr.pick(OWN), (pm, ""))

    def test_the_manny_rig_goes_to_the_manny_module_whether_ue5_or_ue4(self):
        self.assertEqual(rr.pick(UE5), (ar, ""))
        self.assertEqual(rr.pick(UE4), (ar, ""))

    def test_an_unknown_skeleton_is_refused_by_name(self):
        mod, why = rr.pick(["hips", "chest", "l_arm"], "|hips")
        self.assertIsNone(mod)
        self.assertIn("|hips", why)
        self.assertIn("Manny", why)
        self.assertIn("Lugal", why)

    def test_every_forwarder_exists_on_both_modules(self):
        for name in ("report", "connect", "bake", "disconnect"):
            self.assertTrue(callable(getattr(rr, name)))
            self.assertTrue(callable(getattr(ar, name)), name)
            self.assertTrue(callable(getattr(pm, name)), name)


class TestMannyBake(unittest.TestCase):

    def test_the_manny_module_bakes_through_the_vendor_too(self):
        with open(ar.__file__.replace(".pyc", ".py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("bakeResults", src)
        self.assertIn("asMoCapMatcherBake", src)
        self.assertIn("NOTHING", ar.disconnect.__doc__)


if __name__ == "__main__":
    unittest.main()
