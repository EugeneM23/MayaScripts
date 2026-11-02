"""A straight stance leg at the passing phase (docs/superpowers/specs/2026-11-02-walk-straight-passing-leg-design.md):
the pure helpers, the lift, Leg stretch, and the parameters. numpy only, no Maya."""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T

wm, walk, clip, load, L1, L2 = T.wm, T.walk, T.clip, T.load, T.L1, T.L2

gait = load("gait")


class HelperTests(unittest.TestCase):
    """straight_ratio / knee_bend_at / passing_share / smooth_under / lift_to."""

    def test_a_bend_and_its_ratio_round_trip(self):
        for bend in (0.0, 2.5, 5.0, 12.0, 30.0, 90.0):
            r = wm.straight_ratio(bend, L1, L2)
            self.assertAlmostEqual(wm.knee_bend_at(r, L1, L2), bend, places=6)

    def test_a_straight_knee_is_the_whole_leg(self):
        self.assertAlmostEqual(wm.straight_ratio(0.0, L1, L2), 1.0, places=12)
        self.assertAlmostEqual(wm.knee_bend_at(1.0, L1, L2), 0.0, places=6)

    def test_a_straighter_knee_is_a_longer_leg(self):
        self.assertGreater(wm.straight_ratio(5.0, L1, L2), wm.straight_ratio(20.0, L1, L2))

    def test_five_degrees_is_a_centimetre_of_hip_on_an_eighty_six_cm_leg(self):
        # the lever the whole feature rests on (the spec's finding 2): near straight the knee is a square root
        # of its reach, so a centimetre of hip is fifteen degrees of knee
        l1 = l2 = 42.8
        d20 = wm.straight_ratio(20.0, l1, l2) * (l1 + l2)
        d5 = wm.straight_ratio(5.0, l1, l2) * (l1 + l2)
        self.assertAlmostEqual(d5 - d20, 1.24, places=1)

    def test_the_window_is_zero_at_the_strike_and_the_lift_off(self):
        self.assertEqual(wm.passing_share(0.0, 10.0), 0.0)
        self.assertEqual(wm.passing_share(10.0, 10.0), 0.0)
        self.assertEqual(wm.passing_share(-1.0, 10.0), 0.0)
        self.assertEqual(wm.passing_share(11.0, 10.0), 0.0)

    def test_the_window_is_whole_across_the_middle(self):
        self.assertAlmostEqual(wm.passing_share(5.0, 10.0), 1.0, places=12)
        self.assertAlmostEqual(wm.passing_share(4.0, 10.0), 1.0, places=12)
        self.assertAlmostEqual(wm.passing_share(6.0, 10.0), 1.0, places=12)

    def test_the_window_rises_and_falls_smoothly(self):
        xs = np.linspace(0.0, 10.0, 201)
        ys = np.array([wm.passing_share(x, 10.0) for x in xs])
        self.assertTrue(np.all(np.diff(ys[:60]) >= -1e-12))      # in
        self.assertTrue(np.all(np.diff(ys[-60:]) <= 1e-12))      # out
        self.assertLess(float(np.abs(np.diff(ys)).max()), 0.05)  # no step

    def test_the_window_of_a_contact_too_short_to_have_a_middle(self):
        self.assertEqual(wm.passing_share(0.0, 0.0), 0.0)
        self.assertGreaterEqual(wm.passing_share(0.5, 1.0), 0.0)

    def test_smooth_under_lies_under_its_room(self):
        rng = np.random.default_rng(5)
        for _ in range(20):
            room = np.abs(rng.normal(size=31)) * 3.0
            out = wm.smooth_under(room, 2.0)
            self.assertEqual(len(out), 31)
            self.assertTrue(np.all(out <= room + 1e-9))
            self.assertTrue(np.all(out >= -1e-12))

    def test_smooth_under_is_zero_where_the_room_is_zero(self):
        room = np.ones(30) * 4.0
        room[10] = 0.0
        out = wm.smooth_under(room, 2.0)
        self.assertEqual(out[10], 0.0)
        self.assertLess(out[11], 2.0)          # its neighbours give way too
        self.assertGreater(out[20], 2.0)       # far away it keeps the room

    def test_smooth_under_ramps_where_a_clamp_would_step(self):
        room = np.zeros(40) + 0.2
        room[12:28] = 5.0                      # a square room: a clamped curve steps 4.8 cm in one frame
        out = wm.smooth_under(room, 3.0)
        self.assertTrue(np.all(out <= room + 1e-9))
        self.assertGreater(out[19], 3.0)       # the middle of the room is used
        step = float(np.abs(np.diff(out, prepend=out[-1])).max())
        self.assertLess(step, 0.5 * (5.0 - 0.2))
        ramp = int(np.sum((out > 0.3) & (out < 4.0)))
        self.assertGreaterEqual(ramp, 6)       # it ramps over several frames, on both sides

    def test_smooth_under_is_periodic(self):
        room = np.zeros(24) + 1.0
        room[0] = 0.0
        out = wm.smooth_under(room, 2.0)
        self.assertLess(out[23], 1.0)          # the frame before the gap gives way, the wrap counted
        self.assertLess(out[1], 1.0)

    def test_smooth_under_of_nothing(self):
        self.assertEqual(len(wm.smooth_under(np.zeros(0), 2.0)), 0)
        self.assertTrue(np.all(wm.smooth_under(np.zeros(10), 2.0) == 0.0))

    def test_the_lift_that_reaches_a_target(self):
        up = np.array([0.0, 1.0, 0.0])
        q = np.array([0.0, -80.0, 0.0])        # the ankle 80 cm under the hip
        self.assertAlmostEqual(wm.lift_to(q, up, 85.0), 5.0, places=9)
        self.assertAlmostEqual(wm.lift_to(q, up, 80.0), 0.0, places=9)
        # a target shorter than the leg stands: the hip must come down (a negative lift)
        self.assertLess(wm.lift_to(q, up, 70.0), 0.0)

    def test_the_lift_with_the_ankle_aside(self):
        up = np.array([0.0, 1.0, 0.0])
        q = np.array([0.0, -60.0, 40.0])       # 72.111 cm away, 40 of it along the walk
        x = wm.lift_to(q, up, 80.0)
        self.assertAlmostEqual(float(np.linalg.norm(q - x * up)), 80.0, places=9)
        self.assertGreater(x, 0.0)

    def test_no_lift_reaches_a_target_shorter_than_the_ankle_is_aside(self):
        up = np.array([0.0, 1.0, 0.0])
        q = np.array([0.0, -10.0, 40.0])
        self.assertIsNone(wm.lift_to(q, up, 30.0))


if __name__ == "__main__":
    unittest.main()
