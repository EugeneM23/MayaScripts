"""Tools > 1P Setup: the split of a rig's controls and the line (2026-10-16); the chest control,
the curves, the camera's control and the Root control (2026-10-21)."""

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
from maya_scenesetup import curvectrl  # noqa: E402


MANNY = ["Main", "Root_ctrl", "RootX_M", "FKRoot_M", "HipSwinger_M", "FKSpine1_M", "FKSpine2_M",
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
        self.assertEqual(low, ["Main", "Root_ctrl", "RootX_M", "FKRoot_M", "HipSwinger_M",
                               "FKSpine1_M", "FKSpine2_M", "FKHip_L", "FKKnee_L", "FKAnkle_L",
                               "FKToes_L", "IKLeg_L", "PoleLeg_L", "IKToes_L", "RollHeel_L",
                               "RollToesEnd_L", "FKIKLeg_L", "IKSpine1_M", "FKIKSpine_M"])
        self.assertEqual(up, ["FKSpine4_M", "FKSpine5_M", "FKNeck_M", "FKHead_M",
                              "FKScapula_R", "FKShoulder_R", "FKElbow_R", "FKWrist_R",
                              "FKIndexFinger1_R", "IKArm_R", "PoleArm_R", "FKIKArm_R",
                              "Fingers_R"])

    def test_the_knotted_control_is_in_neither(self):
        lower, upper = fp.split(["a:FKSpine3_M", "a:FKSpine4_M"])
        self.assertEqual((lower, upper), ([], ["a:FKSpine4_M"]))

    def test_every_spine_ik_control_and_the_lower_controls_extra_groups_are_lower(self):
        # 2026-10-21: IKhybridSpine / IKcvSpine / IKExtraSpine read as upper - drawn in the 1P
        # upper display layer, a marquee over the 1P body took them, and a card saved so named
        # the whole spine and the pelvis (FKExtraRoot_M, RootExtraX_M)
        names = ["IKhybridSpine1_M", "IKhybridExtraSpine2_M", "IKcvSpine3_M", "IKcvExtraSpine1_M",
                 "IKExtraSpine2_M", "IKSpine3_M", "FKExtraRoot_M", "FKExtraSpine1_M",
                 "FKExtraSpine2_M", "RootExtraX_M", "IKExtraLeg_L", "PoleExtraLeg_R"]
        for name in names:
            self.assertTrue(fp.is_lower("Manny_Rig:" + name), name)
        for name in ("FKExtraSpine4_M", "IKExtraArm_R", "PoleExtraArm_L", "FKExtraShoulder_R",
                     "FKExtraNeck_M", "FKSpine5_M"):
            self.assertFalse(fp.is_lower("Manny_Rig:" + name), name)

    def test_layer_names_do_not_start_with_a_digit(self):
        """Maya turns `3P_Lower_Body` into `P_Lower_Body`."""
        for name in (fp.LOWER, fp.UPPER):
            self.assertFalse(name[0].isdigit())
            self.assertIn("3P_", name)


class Line(unittest.TestCase):
    def test_message(self):
        text = fp.message("Manny_Rig", "on", 18, 1, "camera c on the chest", ["n"])
        self.assertEqual(text, "1P Setup on Manny_Rig | 1P mesh on | FKSpine3_M on "
                               "Chest_1P_ctrl | _3P_Lower_Body: 18 controls + the chest's "
                               "travel | _3P_Upper_Body: 1 control + the chest's turn | "
                               "camera c on the chest | n")
        self.assertIn("no 1P mesh", fp.message("Creep_Rig", "none", 1, 1, "", []))


class ChestSquare(unittest.TestCase):
    """«нормального контроллера (квадратной формы красного цвета)»."""

    def test_a_closed_square_in_the_drawing_s_widest_plane(self):
        box = ((-1.0, -10.0, -14.0), (1.0, 10.0, 14.0))   # thin along X: the chest's ring
        points = fp.chest_square(box)
        self.assertEqual(points[0], points[-1])
        self.assertEqual(len(points), 5)
        self.assertTrue(all(abs(p[0]) < 1e-9 for p in points))       # in YZ
        half = 14.0 * fp.CHEST_GROW
        self.assertAlmostEqual(max(abs(p[1]) for p in points), half)
        self.assertAlmostEqual(max(abs(p[2]) for p in points), half)  # a SQUARE

    def test_about_the_drawing_s_centre(self):
        box = ((-1.0, 0.0, 10.0), (1.0, 20.0, 30.0))
        points = fp.chest_square(box)
        ys = [p[1] for p in points]
        zs = [p[2] for p in points]
        self.assertAlmostEqual((max(ys) + min(ys)) / 2, 10.0)
        self.assertAlmostEqual((max(zs) + min(zs)) / 2, 20.0)

    def test_without_a_drawing_a_plain_square(self):
        points = fp.chest_square(None)
        self.assertAlmostEqual(max(abs(p[0]) for p in points), fp.CHEST_LEAST)
        self.assertTrue(all(p[1] == 0 for p in points))

    def test_red(self):
        r, g, b = curvectrl.RED
        self.assertGreater(r, 0.8)
        self.assertLess(max(g, b), 0.3)


class Curves(unittest.TestCase):

    def test_plane_of(self):
        self.assertEqual(curvectrl.plane_of((1, 5, 3)), ("y", "z"))
        self.assertEqual(curvectrl.plane_of((9, 1, 3)), ("x", "z"))

    def test_square_on_axes(self):
        pts = curvectrl.square(2.0, ("x", "y"), (1, 1, 1))
        self.assertTrue(all(p[2] == 1 for p in pts))
        self.assertEqual(sorted(set(p[0] for p in pts)), [-1.0, 3.0])

    def test_root_arrow_lies_on_the_floor_and_points_forward(self):
        pts = curvectrl.root_arrow(10.0)
        self.assertEqual(pts[0], pts[-1])
        self.assertTrue(all(p[1] == 0 for p in pts))
        self.assertEqual(max(p[2] for p in pts), 20.0)

    def test_camera_looks_down_minus_z(self):
        pts = curvectrl.camera_body(10.0)
        self.assertLess(min(p[2] for p in pts), -10.0)       # the lens out in front
        self.assertLess(max(p[2] for p in pts), 10.0)

    def test_transformed_is_row_vector(self):
        m = (0, 1, 0, 0,  -1, 0, 0, 0,  0, 0, 1, 0,  5, 0, 0, 1)    # 90 about Z, then +5 X
        self.assertEqual(curvectrl.transformed([(1, 0, 0)], m), [(5, 1, 0)])


class CameraControl(unittest.TestCase):

    def test_the_control_name_is_in_the_bone_s_namespace(self):
        from maya_scenesetup import camera
        self.assertEqual(camera.control_name_for("|g|Manny_Rig:root|Manny_Rig:camera_root"),
                         "Manny_Rig:Camera_ctrl")
        self.assertEqual(camera.control_name_for("|root|camera_root"), "Camera_ctrl")

    def test_the_parents(self):
        from maya_scenesetup import camera
        self.assertEqual(camera.PARENTS, ("Main", "Root", "Chest", "World"))
        self.assertTrue(camera.is_main("|a|Manny_Rig:Main"))
        self.assertFalse(camera.is_main("|a|Manny_Rig:MainSystem"))

    def test_the_control_draws_the_camera_through_the_axis_turn(self):
        """The camera stands in the control at AXIS_OFFSET: its lens (-Z) is the control's -Y."""
        from maya_scenesetup import camera
        pts = camera._control_points(10.0)
        self.assertLess(min(p[1] for p in pts), -10.0)
        self.assertLess(max(abs(p[2]) for p in pts), 10.0)


class DisplayLayers(unittest.TestCase):
    """«слои отображения с контроллерами верхней и нижней части тела» (2026-10-21)."""

    def test_names(self):
        self.assertEqual(fp.display_layer_names("Manny_Rig"),
                         ("Manny_Rig_1P_Lower_Controls", "Manny_Rig_1P_Upper_Controls"))
        self.assertEqual(fp.display_layer_names("tab_a:Creep_Rig")[0],
                         "Creep_Rig_1P_Lower_Controls")

    def test_the_colour_an_override_shows(self):
        self.assertIsNone(fp.override_rgb(False, False, (1, 0, 0), 13))
        self.assertEqual(fp.override_rgb(True, True, (0.2, 0.3, 0.4), 13), (0.2, 0.3, 0.4))
        self.assertEqual(fp.override_rgb(True, False, (0, 0, 0), 13), (1.0, 0.0, 0.0))
        self.assertIsNone(fp.override_rgb(True, False, (0, 0, 0), 0))     # Maya's default
        self.assertEqual(fp.override_rgb(True, False, (0, 0, 0), 17, (1, 1, 0.5)), (1, 1, 0.5))

    def test_invert_finds_the_colour_a_view_transform_shows(self):
        view = lambda c: [v ** (1 / 2.2) for v in c]       # noqa: E731
        target = (0.05, 0.255, 0.6)
        got = fp.invert(view, target)
        for a, b in zip(view(got), target):
            self.assertAlmostEqual(a, b, 5)

    def test_the_line_says_it_is_stabilized(self):
        self.assertEqual(fp.DEFAULTS_WORDS % (fp.UPPER, "M_1P_Lower_Controls"),
                         "stabilized: _3P_Upper_Body muted, M_1P_Lower_Controls hidden")


class HandsInTheChest(unittest.TestCase):
    """«в режиме 1P IK руки и оружие находились в паренте нашего Chest контрола» (2026-10-21)."""

    def test_the_ik_arm_controls(self):
        self.assertEqual(fp.IK_ARMS, ("IKArm_R", "IKArm_L"))

    def test_the_ik_arms_are_upper_body(self):
        lower, upper = fp.split(["a:" + n for n in fp.IK_ARMS])
        self.assertEqual(lower, [])


class RootControl(unittest.TestCase):

    def test_names(self):
        from maya_scenesetup import rootcontrol
        self.assertEqual(rootcontrol.NAME, "Root_ctrl")
        self.assertTrue(fp.is_lower("ns:" + rootcontrol.NAME))

    def test_the_modules_ship(self):
        import install
        payload = install.payload()
        self.assertIn("maya_scenesetup", payload)


if __name__ == "__main__":
    unittest.main()
