"""Gait Builder's knees (docs/superpowers/plans/gaitbuilder): the soft limit that eases a leg into its reach
(gaitmodel.knee_soft), and the ranges that stop where the walk becomes a lunge (aspects.DROP_MAX). numpy only."""

import unittest

import numpy as np

from tests import test_walkmodel as tw
from tests.test_gait_model import load, apart

gm = load("gaitmodel")
asp = load("aspects")

QUIET = {"balance": 0.0, "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0, "foot_placement": 0.0}


def walk():
    c = tw.clip()
    return gm.analyse(gm.Clip(c.names, c.parents, c.worlds.copy(), c.fps, c.up, c.name))


class SoftReach(unittest.TestCase):

    def test_itself_below_the_start(self):
        for d in (10.0, 80.0, 90.0):
            self.assertEqual(gm.soft_reach(d, 90.0, 95.0), d)

    def test_eases_in_with_no_corner_and_never_past_the_limit(self):
        h = 1e-6
        slope = (gm.soft_reach(90.0 + h, 90.0, 95.0) - gm.soft_reach(90.0, 90.0, 95.0)) / h
        self.assertAlmostEqual(slope, 1.0, places=4)
        last = 90.0
        for d in np.linspace(90.0, 200.0, 50):
            got = gm.soft_reach(d, 90.0, 95.0)
            self.assertLess(got, 95.0)
            self.assertGreaterEqual(got, last - 1e-12)
            last = got

    def test_a_start_at_the_limit_is_the_hard_limit(self):
        self.assertEqual(gm.soft_reach(100.0, 95.0, 95.0), 95.0)
        self.assertEqual(gm.soft_reach(100.0, 96.0, 95.0), 95.0)

    def test_the_two_bone_leg(self):
        hip, bend = np.zeros(3), np.array([0.0, 0.0, 1.0])
        hard = gm.two_bone(hip, np.array([0.0, -85.0, 0.0]), 45.0, 45.0, bend, 0.99)
        soft = gm.two_bone(hip, np.array([0.0, -85.0, 0.0]), 45.0, 45.0, bend, 0.99, 0.95)
        self.assertLess(np.abs(hard[1] - soft[1]).max(), 1e-12)          # 85 under the start (85.5): itself
        far = gm.two_bone(hip, np.array([0.0, -95.0, 0.0]), 45.0, 45.0, bend, 0.99, 0.95)
        d = float(np.linalg.norm(far[1] - hip))
        self.assertTrue(0.95 * 90.0 < d < 0.99 * 90.0, d)


class SoftKnees(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w = walk()

    def test_the_walk_s_own_legs_are_untouched(self):
        a = self.w.evaluate(dict(QUIET))
        b = self.w.evaluate(dict(QUIET, knee_soft=0.04))
        self.assertLess(apart(a.worlds, b.worlds)[0], 1e-9)

    def test_a_long_stride_stays_further_from_the_limit(self):
        # (the walker's pelvis drop keeps its legs 0.8 % short of their reach, so it never meets the clamp the
        # soft limit is for - the knee clicks are gated on real walks, gates.py clicks)
        ix = dict((n, i) for i, n in enumerate(self.w.names))

        def most(r):
            w = np.asarray(r.worlds)
            out = 0.0
            for s in "lr":
                h, k, a = (w[ix[b + "_" + s], :-1, 3, :3] for b in ("thigh", "calf", "foot"))
                L = np.linalg.norm(k - h, axis=1) + np.linalg.norm(a - k, axis=1)
                out = max(out, float((np.linalg.norm(a - h, axis=1) / L).max()))
            return out
        hard = most(self.w.evaluate({"stride": 1.4}))
        soft = most(self.w.evaluate({"stride": 1.4, "knee_soft": 0.04}))
        self.assertLess(soft, hard)
        self.assertLess(hard, self.w.reach["l"] + 1e-9)


class WeightDip(unittest.TestCase):
    """A heavy walker's pelvis sinks into each step (gaitmodel weight_dip), in the bob's low half."""

    @classmethod
    def setUpClass(cls):
        cls.w = walk()
        cls.pelvis = cls.w.index["pelvis"]

    def heights(self, **knobs):
        r = self.w.evaluate(dict(QUIET, **knobs))
        return np.asarray(r.worlds)[self.pelvis, :-1, 3, :3] @ self.w.up

    def test_nothing_at_weight_naught_or_light_or_off(self):
        plain = self.heights()
        self.assertLess(np.abs(self.heights(weight_dip=0.05) - plain).max(), 1e-9)
        light, light_dip = self.heights(weight=-1.0), self.heights(weight=-1.0, weight_dip=0.05)
        self.assertLess(np.abs(light_dip - light).max(), 1e-9)
        heavy, heavy_dip = self.heights(weight=1.0), self.heights(weight=1.0, weight_dip=0.0)
        self.assertLess(np.abs(heavy - heavy_dip).max(), 1e-9)         # Walk Builder's own weight: no dip

    def test_heavy_sinks_where_the_bob_is_low_never_where_it_is_high(self):
        heavy = self.heights(weight=1.0)
        sunk = self.heights(weight=1.0, weight_dip=0.05)
        dip = heavy - sunk
        self.assertGreaterEqual(dip.min(), -1e-6)                        # never raised
        self.assertGreater(dip.max(), 0.04 * self.w.leg_length)         # the low half: most of the share asked
        self.assertLess(dip[int(np.argmax(heavy))], 0.25 * dip.max())  # the high half: little or none


class DropTop(unittest.TestCase):

    def test_between_the_probes(self):
        points = [(0.0, 1.0), (10.0, 6.0), (20.0, 21.0)]
        self.assertAlmostEqual(asp.drop_top(points, 11.0), 10.0 + 10.0 * 5.0 / 15.0)
        self.assertAlmostEqual(asp.drop_top(points, 3.5), 5.0)

    def test_never_and_already(self):
        self.assertIsNone(asp.drop_top([(0.0, 1.0), (10.0, 6.0)], 12.8))
        self.assertEqual(asp.drop_top([(0.0, 14.0), (10.0, 30.0)], 12.8), 0.0)

    def test_the_step_s_range_stops_there(self):
        w = walk()
        base = asp.measure(w, w.evaluate(asp.base_engine(w)).worlds)
        free = asp.ranges(base, w.leg_length)["step"]
        limit = asp.DROP_MAX * w.leg_length
        base["_curve"] = {"_drop_step": {"": [(0.0, 0.0), (0.4 * base["step"], 2.0 * limit)]}}
        cut = asp.ranges(base, w.leg_length)["step"]
        self.assertEqual(cut[0], free[0])
        self.assertAlmostEqual(cut[1], 1.2 * base["step"])       # half way to the probe
        base["_curve"] = {"_drop_step": {"": [(0.0, 2.0 * limit), (0.2 * base["step"], 3.0 * limit)]}}
        self.assertAlmostEqual(asp.ranges(base, w.leg_length)["step"][1], 1.1 * base["step"])   # the floor


if __name__ == "__main__":
    unittest.main()
