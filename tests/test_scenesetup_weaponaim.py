"""Connections' weapon Aim Mode (2026-10-21): the pure halves, the [Body | Weapon] tabs and the
Aim presses. The scene half is docs/superpowers/plans/verify_weapon_aim_mode.py."""

import unittest

from maya_scenesetup import connections as cx
from maya_scenesetup import weaponaim as wa

from tests.test_scenesetup_connections import FakeMenuCmds


class Pure(unittest.TestCase):

    def test_vectors_aim_down_the_blade_and_up_across_it(self):
        # a sword: the blade on +Y to 100, the guard on X +-15, thin on Z; the up on the other
        # side of the guard (2026-10-21), opposite the blade's middle, half the target's distance
        # out (2026-10-23: beside the grip it crashed Maya)
        aim_v, up_v, d_aim, d_up = wa.vectors((-15, -20, -2), (15, 100, 2))
        self.assertEqual(aim_v, (0.0, 1.0, 0.0))
        self.assertAlmostEqual(d_aim, 115.0)
        point = [v * d_up for v in up_v]
        self.assertAlmostEqual(point[0], -115.0 * wa.UP_SHARE)
        self.assertAlmostEqual(point[1], 100.0 * wa.UP_ALONG)
        self.assertAlmostEqual(point[2], 0.0)

    def test_the_constraint_s_up_axis_is_across_the_blade(self):
        aim_v, up_v, _d, _du = wa.vectors((-15, -20, -2), (15, 100, 2))
        for got, want in zip(wa.up_axis(aim_v, up_v), (-1.0, 0.0, 0.0)):
            self.assertAlmostEqual(got, want)

    def test_the_up_stands_well_off_the_blade_s_line(self):
        aim_v, up_v, _d, _du = wa.vectors((-15, -20, -2), (15, 100, 2))
        self.assertLess(sum(a * u for a, u in zip(aim_v, up_v)), 0.75)

    def test_a_blade_down_minus_y_aims_down(self):
        aim_v, _up, _d, _du = wa.vectors((-15, -100, -2), (15, 20, 2))
        self.assertEqual(aim_v, (0.0, -1.0, 0.0))

    def test_nothing_to_measure_is_none(self):
        self.assertIsNone(wa.vectors((0, 0, 0), (0, 0, 0)))

    def test_the_angle_between_two_rotations_ignores_how_euler_writes_them(self):
        self.assertAlmostEqual(wa.turn_between((10, 20, 30), (10, 20, 30)), 0.0, 4)
        self.assertAlmostEqual(wa.turn_between((173.45, -49.15, 96.29), (-186.55, -49.15, 96.29)), 0.0, 4)
        self.assertAlmostEqual(wa.turn_between((0, 0, 0), (0, 90, 0)), 90.0, 4)
        self.assertAlmostEqual(wa.turn_between((0, 0, 0), (0, 0, 10), order=3), 10.0, 4)

    def test_only_the_frames_the_bake_missed_get_a_key(self):
        # 2026-10-26, «при запіканні на дефолт змінюється позиція ножа»: keyed on the controllers' keys
        # alone, frame 22 between 21 and 23 turned 27 degrees off the aim
        aimed = {21: (-162.99, -41.47, 85.79), 22: (-162.87, -6.29, 83.84), 23: (-127.58, 66.1, 124.45),
                 24: (-82.11, 71.33, 167.82)}
        baked = {22: (-148.38, 12.79, 98.28), 24: (-82.13, 71.33, 167.80)}
        self.assertEqual(wa.frames_off(aimed, baked, tolerance=0.1), [22])
        self.assertEqual(wa.frames_off(aimed, {}, tolerance=0.1), [])

    def test_an_aim_without_its_controllers_or_constraint_is_broken(self):
        # 2026-10-27, «Aim не працює»: an empty group left in a tab made Aim Mode refuse
        both = {"target": "|g|t", "up": "|g|u"}
        self.assertFalse(wa.broken(both, "|w|con"))
        self.assertTrue(wa.broken({}, None))
        self.assertTrue(wa.broken(both, None))
        self.assertTrue(wa.broken({"target": "|g|t"}, "|w|con"))

    def test_point_of_reads_the_frame(self):
        # a frame turned 90 about Z and moved: its +X is world +Y
        m = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 10, 20, 30, 1]
        x, y, z = wa.point_of(m, (1, 0, 0), 5)
        self.assertAlmostEqual(x, 10)
        self.assertAlmostEqual(y, 25)
        self.assertAlmostEqual(z, 30)

    def test_messages_count_the_keys(self):
        self.assertIn("on 3 keys (0..20)", wa.entered_message("Sword", [0, 8, 20]))
        self.assertIn("current frame", wa.entered_message("Sword", []))
        self.assertIn("on 1 key (4..4)", wa.left_message("Sword", [4]))

    def test_the_diamond_reaches_its_radius_on_every_point(self):
        points = wa.diamond(2.0)
        self.assertTrue(all(max(abs(c) for c in p) == 2.0 for p in points))


class Tabs(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.hubstyle.take_marks()
        cx.build_panel()
        self.marks = dict((m.name, m) for m in cx.hubstyle.take_marks())

    def tearDown(self):
        cx.cmds, cx.refresh = self.real

    def _column_calls(self, name):
        return [c for c in self.fake.calls if c[0] == "columnLayout" and c[1] == (name,)]

    def test_three_tab_segments_body_first(self):
        self.assertEqual([label for _n, label in self.fake.segments[cx.TAB_COLLECTION]],
                         ["Body", "Weapon", "Camera"])
        self.assertEqual(self.marks[cx.tab_segment("body")].role, "segment")

    def test_the_weapon_tab_holds_the_parent_rows_and_the_aim(self):
        order = [c[1][0] if c[1] else c[2].get("label") for c in self.fake.calls
                 if c[0] in ("columnLayout", "text", "button", "iconTextRadioCollection")
                 and not c[2].get("edit")]
        weapon = order.index(cx.TAB_COLUMN["weapon"])
        body = order.index(cx.TAB_COLUMN["body"])
        self.assertLess(body, order.index(cx.CAPTION["limbs"]))
        self.assertLess(order.index("BakeAcross"), weapon)
        for item in (cx.MENU["R"], cx.MENU["W"], "Apply all", cx.CAPTION["aim"], cx.AIM_BUTTON,
                     cx.DEFAULT_BUTTON):
            self.assertLess(weapon, order.index(item), item)

    def test_aim_mode_is_the_aim_sections_primary(self):
        self.assertEqual((self.marks[cx.AIM_BUTTON].role, self.marks[cx.AIM_BUTTON].icon),
                         ("primary", "target"))
        self.assertEqual(self.marks[cx.DEFAULT_BUTTON].role, "secondary")

    def test_the_presses_go_through_aim_mode(self):
        asked = []
        saved = cx.aim_mode
        cx.aim_mode = lambda rig=None, weapon=None, on=True: asked.append(on) or "done"
        try:
            cx._press_aim_mode()
            cx._press_aim_default()
        finally:
            cx.aim_mode = saved
        self.assertEqual(asked, [True, False])


class AimRefusals(unittest.TestCase):

    def test_no_weapon(self):
        saved = wa.cmds
        try:
            class Fake(object):
                @staticmethod
                def objExists(_n):
                    return False
            wa.cmds = Fake
            self.assertEqual(wa.refusal("|nothing"), wa.NO_WEAPON)
        finally:
            wa.cmds = saved


if __name__ == "__main__":
    unittest.main()
