import os
import subprocess
import sys
import unittest

from maya_overrig import bodymap


class TestMayaFreeBoundary(unittest.TestCase):
    """bodymap must stay importable with no Maya and no Qt loaded.

    Checked in a fresh interpreter because by the time the rest of the suite
    has run, maya.cmds and Qt are already in this process's sys.modules.
    """

    def test_importing_bodymap_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "from maya_overrig import bodymap\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide6')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        repo_root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing bodymap leaked: " + result.stdout.strip())


class TestBodyMap(unittest.TestCase):

    def test_has_exactly_64_buttons(self):
        self.assertEqual(len(bodymap.BUTTONS), 64)

    def test_ids_are_unique(self):
        ids = [b.id for b in bodymap.BUTTONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_region_is_known(self):
        for b in bodymap.BUTTONS:
            self.assertIn(b.region, bodymap.REGIONS, b.id)

    def test_no_rectangles_overlap(self):
        for i, a in enumerate(bodymap.BUTTONS):
            for b in bodymap.BUTTONS[i + 1:]:
                overlap_x = a.x < b.x + b.w and b.x < a.x + a.w
                overlap_y = a.y < b.y + b.h and b.y < a.y + a.h
                self.assertFalse(
                    overlap_x and overlap_y,
                    "{0} overlaps {1}".format(a.id, b.id))

    def test_all_buttons_inside_canvas(self):
        for b in bodymap.BUTTONS:
            self.assertGreaterEqual(b.x, 0, b.id)
            self.assertGreaterEqual(b.y, 0, b.id)
            self.assertLessEqual(b.x + b.w, bodymap.CANVAS_W, b.id)
            self.assertLessEqual(b.y + b.h, bodymap.CANVAS_H, b.id)

    def test_sides_are_mirrored(self):
        by_id = {b.id: b for b in bodymap.BUTTONS}
        left = [b for b in bodymap.BUTTONS if b.id.endswith("_l")]
        self.assertTrue(left)
        for lb in left:
            rb = by_id[lb.id[:-2] + "_r"]
            self.assertEqual(rb.w, lb.w)
            self.assertEqual(rb.h, lb.h)
            self.assertEqual(rb.y, lb.y)
            self.assertEqual(rb.x, bodymap.CANVAS_W - lb.x - lb.w)

    def test_character_left_is_drawn_on_viewer_right(self):
        by_id = {b.id: b for b in bodymap.BUTTONS}
        self.assertGreater(by_id["hand_l"].x, bodymap.CANVAS_W / 2)
        self.assertLess(by_id["hand_r"].x, bodymap.CANVAS_W / 2)

    def test_group_all_covers_every_button_of_both_kinds(self):
        self.assertEqual(len(bodymap.group_members("all")),
                         len(bodymap.BUTTONS) + len(bodymap.IK_BUTTONS))

    def test_group_main_excludes_fingers(self):
        main = bodymap.group_members("main")
        self.assertEqual(
            len(main),
            26 + len(bodymap.IK_BUTTONS))  # no IK button sits on a hand
        regions = {b.id: b.region for b in bodymap.BUTTONS}
        regions.update({b.id: b.region for b in bodymap.IK_BUTTONS})
        for bid in main:
            self.assertNotIn(regions[bid], ("hand_l", "hand_r"))

    def test_finger_groups_hold_19_each(self):
        self.assertEqual(len(bodymap.group_members("hand_l")), 19)
        self.assertEqual(len(bodymap.group_members("hand_r")), 19)

    def test_button_by_id_round_trips(self):
        self.assertEqual(bodymap.button_by_id("head").joint, "head")

    def test_button_by_id_rejects_unknown(self):
        with self.assertRaises(KeyError):
            bodymap.button_by_id("no_such_button")

    def test_group_members_rejects_unknown(self):
        with self.assertRaises(KeyError):
            bodymap.group_members("no_such_group")

    def test_joint_names_match_ue5_convention(self):
        names = {b.joint for b in bodymap.BUTTONS}
        for expected in ("root", "pelvis", "spine_01", "spine_05", "neck_01",
                         "head", "clavicle_l", "upperarm_r", "lowerarm_l",
                         "hand_r", "thigh_l", "calf_r", "foot_l", "ball_r",
                         "index_metacarpal_l", "index_03_r", "thumb_01_l",
                         "pinky_metacarpal_r"):
            self.assertIn(expected, names)

    def test_ue_helper_joints_are_absent(self):
        names = {b.joint for b in bodymap.BUTTONS}
        for forbidden in ("ik_foot_root", "ik_foot_l", "ik_hand_root",
                          "ik_hand_gun", "ik_hand_l", "interaction",
                          "center_of_mass", "camera_root", "camera_bone",
                          "weapon_l", "lowerarm_twist_01_l", "calf_twist_02_r"):
            self.assertNotIn(forbidden, names)


class TestIkButtons(unittest.TestCase):

    def test_eight_buttons(self):
        """End + pole per limb. No spine circles: the spline-IK spine was
        removed at the user's call (2026-08-15); git history has it."""
        self.assertEqual(len(bodymap.IK_BUTTONS), 8)

    def test_ids_unique_and_disjoint_from_fk(self):
        ids = [b.id for b in bodymap.IK_BUTTONS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & {b.id for b in bodymap.BUTTONS})

    def test_roles_are_known(self):
        for b in bodymap.IK_BUTTONS:
            self.assertIn(b.role, ("end", "pole", "base"), b.id)

    def test_limbs_and_roles_cover_the_ik_table(self):
        self.assertEqual(
            {(b.limb, b.role) for b in bodymap.IK_BUTTONS},
            {("arm_l", "end"), ("arm_l", "pole"),
             ("arm_r", "end"), ("arm_r", "pole"),
             ("leg_l", "end"), ("leg_l", "pole"),
             ("leg_r", "end"), ("leg_r", "pole")})

    def test_right_side_mirrors_the_left(self):
        by_id = {b.id: b for b in bodymap.IK_BUTTONS}
        left = [b for b in bodymap.IK_BUTTONS if b.limb.endswith("_l")]
        self.assertTrue(left)
        for lb in left:
            rb = by_id[lb.id.replace("_l_", "_r_")]
            self.assertEqual(rb.limb, lb.limb[:-2] + "_r", lb.id)
            self.assertEqual(rb.x, bodymap.CANVAS_W - lb.x - lb.w, lb.id)
            self.assertEqual((rb.y, rb.w, rb.h), (lb.y, lb.w, lb.h), lb.id)

    def test_regions_are_known(self):
        for b in bodymap.IK_BUTTONS:
            self.assertIn(b.region, bodymap.REGIONS, b.id)

    def test_stay_on_the_canvas(self):
        for b in bodymap.IK_BUTTONS:
            self.assertGreaterEqual(b.x, 0, b.id)
            self.assertGreaterEqual(b.y, 0, b.id)
            self.assertLessEqual(b.x + b.w, bodymap.CANVAS_W, b.id)
            self.assertLessEqual(b.y + b.h, bodymap.CANVAS_H, b.id)

    def test_never_overlap_fk_buttons(self):
        for ik in bodymap.IK_BUTTONS:
            for fk in bodymap.BUTTONS:
                clear = (ik.x + ik.w <= fk.x or fk.x + fk.w <= ik.x
                         or ik.y + ik.h <= fk.y or fk.y + fk.h <= ik.y)
                self.assertTrue(clear, "{0} overlaps {1}".format(ik.id, fk.id))

    def test_never_overlap_each_other(self):
        for i, a in enumerate(bodymap.IK_BUTTONS):
            for b in bodymap.IK_BUTTONS[i + 1:]:
                clear = (a.x + a.w <= b.x or b.x + b.w <= a.x
                         or a.y + a.h <= b.y or b.y + b.h <= a.y)
                self.assertTrue(clear, "{0} overlaps {1}".format(a.id, b.id))

    def test_ik_button_by_id_round_trips(self):
        button = bodymap.ik_button_by_id("leg_l_ik_end")
        self.assertEqual((button.limb, button.role), ("leg_l", "end"))

    def test_ik_button_by_id_rejects_unknown(self):
        with self.assertRaises(KeyError):
            bodymap.ik_button_by_id("pelvis")

    def test_groups_include_ik_ids(self):
        self.assertIn("leg_l_ik_end", bodymap.group_members("leg_l"))
        self.assertIn("arm_r_ik_pole", bodymap.group_members("arm_r"))
        self.assertIn("leg_r_ik_pole", bodymap.group_members("main"))
        self.assertIn("arm_l_ik_end", bodymap.group_members("all"))


if __name__ == "__main__":
    unittest.main()
