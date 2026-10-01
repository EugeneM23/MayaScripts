"""The CoM tool's maths, pure."""

import unittest

from maya_com import dragmath as dm


class Rays(unittest.TestCase):

    def test_a_ray_meets_a_plane(self):
        p = dm.ray_plane((0, 10, 0), (0, -1, 0), (0, 2, 0), (0, 1, 0))
        self.assertEqual(tuple(round(x, 9) for x in p), (0, 2, 0))

    def test_a_ray_parallel_to_the_plane_meets_nothing(self):
        self.assertIsNone(dm.ray_plane((0, 10, 0), (1, 0, 0), (0, 2, 0), (0, 1, 0)))

    def test_the_closest_point_of_a_line_to_a_ray(self):
        #  ray along +X at height 5, the line is the vertical through (3, 0, 0)
        p = dm.ray_line_closest((0, 5, 0), (1, 0, 0), (3, 0, 0), (0, 1, 0))
        self.assertEqual(tuple(round(x, 9) for x in p), (3, 5, 0))


class Modes(unittest.TestCase):

    def test_modifiers(self):
        self.assertEqual(dm.mode_for("none"), "view")
        self.assertEqual(dm.mode_for("shift"), "floor")
        self.assertEqual(dm.mode_for("ctrl"), "vertical")
        self.assertEqual(dm.mode_for("ctrl+shift"), "vertical")

    def test_the_view_mode_drags_in_the_plane_facing_the_camera(self):
        com = (0, 100, 0)
        p = dm.drag_point("view", ((0, 120, 500), (0, 0, -1)), com, (0, 0, -1))
        self.assertEqual(tuple(round(x, 9) for x in p), (0, 120, 0))

    def test_the_floor_mode_keeps_the_height(self):
        com = (0, 100, 0)
        ray = ((0, 300, 300), (0, -1, -1))
        p = dm.drag_point("floor", ray, com, (0, 0, -1))
        self.assertAlmostEqual(p[1], 100.0)
        self.assertAlmostEqual(p[2], 100.0)

    def test_the_vertical_mode_moves_up_only(self):
        com = (10, 100, 0)
        p = dm.drag_point("vertical", ((0, 130, 500), (0, 0, -1)), com, (0, 0, -1))
        self.assertEqual(tuple(round(x, 9) for x in p), (10, 130, 0))

    def test_a_view_ray_along_the_floor_falls_back_to_the_view_plane(self):
        """Shift with the camera level with the CoM: the floor plane is seen
        edge on, so the drag stays in the view plane rather than flying off."""
        com = (0, 100, 0)
        p = dm.drag_point("floor", ((0, 100, 500), (0, 0, -1)), com, (0, 0, -1))
        self.assertIsNotNone(p)


class Apply(unittest.TestCase):

    def test_every_driver_takes_its_share_of_d(self):
        plan = {"RootX_M": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                "PoleLeg_L": ((0.5, 0, 0), (0, 0.5, 0), (0, 0, 0.5))}
        start = {"RootX_M": (1, 2, 3), "PoleLeg_L": (0, 0, 0)}
        out = dm.apply(plan, start, (2, 4, 6))
        self.assertEqual(out["RootX_M"], (3, 6, 9))
        self.assertEqual(out["PoleLeg_L"], (1, 2, 3))

    def test_solve_local_turns_a_world_shortfall_into_the_parent_s_space(self):
        #  the parent is turned 90 degrees about Z (row-vector): local X is world Y
        parent = ((0, 1, 0), (-1, 0, 0), (0, 0, 1))
        delta = dm.solve_local((1, 0, 0), (0, 0, 0), parent)
        self.assertEqual(tuple(round(x, 9) for x in delta), (0, -1, 0))


class AutoKey(unittest.TestCase):

    def test_autokey_keys_the_channels_that_have_curves(self):
        moved = [("RootX_M", "tx"), ("RootX_M", "ty"), ("IKLeg_L", "tx")]
        curves = {("RootX_M", "tx"), ("IKLeg_L", "tx")}
        self.assertEqual(dm.autokey_channels(moved, curves, True),
                         [("RootX_M", "tx"), ("IKLeg_L", "tx")])

    def test_no_keys_with_autokey_off(self):
        self.assertEqual(dm.autokey_channels([("RootX_M", "tx")],
                                             {("RootX_M", "tx")}, False), [])


class Drivers(unittest.TestCase):

    def test_main_is_never_a_driver(self):
        self.assertNotIn("Main", dm.RIG_DRIVERS)
        self.assertNotIn("root", dm.SKELETON_DRIVERS)

    def test_rootx_goes_first(self):
        self.assertEqual(dm.RIG_DRIVERS[0], "RootX_M")


if __name__ == "__main__":
    unittest.main()
