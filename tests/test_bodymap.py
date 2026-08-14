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
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    def test_group_all_covers_every_button(self):
        self.assertEqual(len(bodymap.group_members("all")), 64)

    def test_group_main_excludes_fingers(self):
        main = bodymap.group_members("main")
        self.assertEqual(len(main), 26)
        by_id = {b.id: b for b in bodymap.BUTTONS}
        for bid in main:
            self.assertNotIn(by_id[bid].region, ("hand_l", "hand_r"))

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


if __name__ == "__main__":
    unittest.main()
