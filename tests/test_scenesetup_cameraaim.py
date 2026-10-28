"""The camera's Aim Mode (2026-10-28): the pure halves. The scene half is
docs/superpowers/plans/verify_camera_tab.py."""

import unittest

from maya_scenesetup import aimcore
from maya_scenesetup import cameraaim as ca


class Pure(unittest.TestCase):

    def test_the_view_is_the_camera_s_minus_z_in_the_control_s_frame(self):
        aim_v, up_v, d_aim, d_up = ca.camera_vectors()
        # AXIS_OFFSET's rows: (-1,0,0), (0,0,1), (0,1,0): -Z goes to -Y, +Y to +Z
        self.assertEqual(aim_v, (0.0, -1.0, 0.0))
        self.assertEqual(up_v, (0.0, 0.0, 1.0))
        self.assertEqual((d_aim, d_up), (ca.AIM_DISTANCE, ca.UP_DISTANCE))

    def test_an_identity_offset_aims_down_minus_z(self):
        identity = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
        aim_v, up_v, _d, _du = ca.camera_vectors(identity)
        self.assertEqual(aim_v, (0.0, 0.0, -1.0))
        self.assertEqual(up_v, (0.0, 1.0, 0.0))

    def test_the_up_is_across_the_view(self):
        aim_v, up_v, _d, _du = ca.camera_vectors()
        self.assertEqual(aimcore.up_axis(aim_v, up_v), up_v)

    def test_the_kind_has_names_of_its_own(self):
        self.assertEqual(ca.KIND.marker, "skeldarCameraAim")
        self.assertEqual(ca.KIND.group_name.format("Camera_ctrl"), "Camera_ctrl_aim")
        self.assertNotEqual(ca.KIND.ctrl_marker, "skeldarWeaponAimCtrl")


class Refusals(unittest.TestCase):

    def test_no_camera(self):
        saved = ca.cmds
        try:
            class Fake(object):
                @staticmethod
                def objExists(_n):
                    return False
            ca.cmds = Fake
            self.assertEqual(ca.refusal("|nothing"), ca.NO_CAMERA)
            self.assertEqual(ca.refusal(None), ca.NO_CAMERA)
        finally:
            ca.cmds = saved


if __name__ == "__main__":
    unittest.main()
