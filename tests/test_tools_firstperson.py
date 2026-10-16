"""Tools > 1P Setup: the split of a rig's controls and the line (2026-10-16)."""

import sys
import types
import unittest

try:
    import maya.cmds  # noqa: F401
except ImportError:
    maya = types.ModuleType("maya")
    maya.cmds = types.ModuleType("maya.cmds")
    sys.modules.setdefault("maya", maya)
    sys.modules.setdefault("maya.cmds", maya.cmds)

from maya_tools import firstperson as fp  # noqa: E402


MANNY = ["Main", "RootX_M", "FKRoot_M", "HipSwinger_M", "FKSpine1_M", "FKSpine2_M",
         "FKSpine3_M", "FKSpine4_M", "FKSpine5_M", "FKNeck_M", "FKHead_M", "FKScapula_R",
         "FKShoulder_R", "FKElbow_R", "FKWrist_R", "FKIndexFinger1_R", "IKArm_R", "PoleArm_R",
         "FKIKArm_R", "Fingers_R", "FKHip_L", "FKKnee_L", "FKAnkle_L", "FKToes_L", "IKLeg_L",
         "PoleLeg_L", "IKToes_L", "RollHeel_L", "RollToesEnd_L", "FKIKLeg_L", "IKSpine1_M",
         "FKIKSpine_M"]


class Split(unittest.TestCase):
    def test_lower_and_upper(self):
        paths = ["|Manny_Rig_Character|Manny_Rig:Group|x|Manny_Rig:" + n for n in MANNY]
        lower, upper = fp.split(paths)
        low = [fp.leaf(p) for p in lower]
        up = [fp.leaf(p) for p in upper]
        self.assertEqual(low, ["Main", "RootX_M", "FKRoot_M", "HipSwinger_M", "FKSpine1_M",
                               "FKSpine2_M", "FKHip_L", "FKKnee_L", "FKAnkle_L", "FKToes_L",
                               "IKLeg_L", "PoleLeg_L", "IKToes_L", "RollHeel_L",
                               "RollToesEnd_L", "FKIKLeg_L", "IKSpine1_M", "FKIKSpine_M"])
        self.assertEqual(up, ["FKSpine4_M", "FKSpine5_M", "FKNeck_M", "FKHead_M",
                              "FKScapula_R", "FKShoulder_R", "FKElbow_R", "FKWrist_R",
                              "FKIndexFinger1_R", "IKArm_R", "PoleArm_R", "FKIKArm_R",
                              "Fingers_R"])

    def test_the_knotted_control_is_in_neither(self):
        lower, upper = fp.split(["a:FKSpine3_M", "a:FKSpine4_M"])
        self.assertEqual((lower, upper), ([], ["a:FKSpine4_M"]))

    def test_layer_names_do_not_start_with_a_digit(self):
        """Maya turns `3P_Lower_Body` into `P_Lower_Body`."""
        for name in (fp.LOWER, fp.UPPER):
            self.assertFalse(name[0].isdigit())
            self.assertIn("3P_", name)


class Line(unittest.TestCase):
    def test_message(self):
        text = fp.message("Manny_Rig", "on", 18, 1, "camera c in the knot", ["n"])
        self.assertEqual(text, "1P Setup on Manny_Rig | 1P mesh on | FKSpine3_M on a knot | "
                               "_3P_Lower_Body: 18 controls + the knot's travel | "
                               "_3P_Upper_Body: 1 control + the knot's turn | "
                               "camera c in the knot | n")
        self.assertIn("no 1P mesh", fp.message("Creep_Rig", "none", 1, 1, "", []))


if __name__ == "__main__":
    unittest.main()
