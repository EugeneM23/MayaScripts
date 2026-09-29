"""Where a weapon dragged out of the inventory lands (2026-09-29): the hand
under the cursor, else the floor under it and the character nearest to that.

The choice is pure (screen-space figures in, a target out); the viewport half
(the panel under the cursor, the projection, the camera ray) is proved in a
live Maya by docs/superpowers/plans/verify_inventory_live.py.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import unittest

from maya_scenesetup import droptarget as dt


def figure(key, x0, hands, depth=10.0):
    """A stick figure standing at x0, 100 px tall, arms out at y = 70."""
    segments = [((x0, 0.0), (x0, 100.0)), ((x0 - 30.0, 70.0), (x0 + 30.0, 70.0))]
    return dt.Figure(key, segments, hands, depth)


class Choose(unittest.TestCase):

    def test_on_the_figure_the_nearer_hand(self):
        f = figure("A", 100.0, {"R": (70.0, 70.0), "L": (130.0, 70.0)})
        self.assertEqual(dt.choose((125.0, 60.0), [f], 16), ("hand", "A", "L"))
        self.assertEqual(dt.choose((95.0, 30.0), [f], 16), ("hand", "A", "R"))

    def test_off_the_figure_nothing(self):
        f = figure("A", 100.0, {"R": (70.0, 70.0), "L": (130.0, 70.0)})
        self.assertIsNone(dt.choose((300.0, 60.0), [f], 16))

    def test_the_radius_grows_with_the_figure_on_screen(self):
        """8 % of its projected height: a character filling the view is
        'under the cursor' further from its bones than a distant one."""
        big = dt.Figure("A", [((0.0, 0.0), (0.0, 1000.0))], {"R": (0.0, 700.0)}, 1.0)
        self.assertEqual(dt.choose((70.0, 500.0), [big], 16), ("hand", "A", "R"))
        self.assertIsNone(dt.choose((90.0, 500.0), [big], 16))

    def test_the_nearest_figure_wins(self):
        a = figure("A", 100.0, {"R": (70.0, 70.0)})
        b = figure("B", 140.0, {"R": (110.0, 70.0)})
        self.assertEqual(dt.choose((136.0, 40.0), [a, b], 16)[1], "B")

    def test_a_tie_goes_to_the_one_nearer_the_camera(self):
        a = figure("A", 100.0, {"R": (70.0, 70.0)}, depth=500.0)
        b = figure("B", 100.0, {"R": (70.0, 70.0)}, depth=200.0)
        self.assertEqual(dt.choose((100.0, 50.0), [a, b], 16)[1], "B")

    def test_a_missing_hand_is_skipped(self):
        f = figure("A", 100.0, {"R": None, "L": (130.0, 70.0)})
        self.assertEqual(dt.choose((75.0, 70.0), [f], 16), ("hand", "A", "L"))

    def test_a_figure_without_hands_is_no_target(self):
        f = figure("A", 100.0, {"R": None, "L": None})
        self.assertIsNone(dt.choose((100.0, 50.0), [f], 16))

    def test_a_point_on_a_bone_is_distance_zero(self):
        self.assertEqual(dt.seg_distance((5.0, 0.0), (0.0, 0.0), (10.0, 0.0)), 0.0)
        self.assertEqual(dt.seg_distance((15.0, 0.0), (0.0, 0.0), (10.0, 0.0)), 5.0)
        self.assertEqual(dt.seg_distance((3.0, 4.0), (0.0, 0.0), (0.0, 0.0)), 5.0)


class Floor(unittest.TestCase):

    def test_a_ray_down_meets_the_floor(self):
        self.assertEqual(dt.floor_hit((0.0, 100.0, 50.0), (0.0, -100.0, -50.0)),
                         (0.0, 0.0, 0.0))

    def test_a_ray_up_misses(self):
        self.assertIsNone(dt.floor_hit((0.0, 10.0, 0.0), (0.0, 20.0, 5.0)))

    def test_a_level_ray_misses(self):
        self.assertIsNone(dt.floor_hit((0.0, 10.0, 0.0), (5.0, 10.0, 5.0)))

    def test_the_owner_is_the_nearest_on_the_floor(self):
        roots = {"A": (0.0, 0.0, 0.0), "B": (300.0, 90.0, 0.0)}
        self.assertEqual(dt.owner((250.0, 0.0, 10.0), roots), "B")
        self.assertEqual(dt.owner((20.0, 0.0, 10.0), roots), "A")
        self.assertIsNone(dt.owner((0.0, 0.0, 0.0), {}))

    def test_the_caption_names_the_bone_the_drop_would_take(self):
        self.assertEqual(dt.floor_text("Manny_Rig1", "weapon_l"),
                         "floor · Manny_Rig1 · weapon_l")
        self.assertEqual(dt.hand_text("Manny_Rig", "L"),
                         "Manny_Rig · left hand")
