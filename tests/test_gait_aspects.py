"""Gait Builder's aspects (docs/superpowers/plans/gaitbuilder/aspects.py): a cycle measured in units, on the
synthetic walker of tests/test_walkmodel.py whose motion is known. numpy only."""

import math
import unittest

import numpy as np

from tests import test_walkmodel as tw
from tests.test_gait_model import load

gm = load("gaitmodel")
asp = load("aspects")


def fork_walk(**kw):
    c = tw.clip(**kw)
    return gm.analyse(gm.Clip(c.names, c.parents, c.worlds.copy(), c.fps, c.up, c.name))


class HarmonicTests(unittest.TestCase):

    def test_reads_amplitude_at_its_order(self):
        phase = np.linspace(0, 2 * math.pi, 40, endpoint=False)
        y = 3.0 * np.cos(2 * phase + 0.4) + 1.5 * np.sin(phase) + 7.0
        self.assertAlmostEqual(asp.harmonic(y, phase, 2)[0], 3.0, places=9)
        self.assertAlmostEqual(asp.harmonic(y, phase, 1)[0], 1.5, places=9)


class MeasureTests(unittest.TestCase):
    """The synthetic walker: travel 120 cm a cycle of 24 frames at 30 fps, the pelvis bobbing 3 cm twice a
    stride, swaying 2 cm and surging 2 cm, feet 20 cm apart lifting 10 cm, each down 60 % of the cycle."""

    @classmethod
    def setUpClass(cls):
        cls.walk = fork_walk()
        cls.m = asp.measure(cls.walk, cls.walk.clip.worlds)

    def test_timing(self):
        self.assertAlmostEqual(self.m["step"], 60.0, places=6)
        self.assertAlmostEqual(self.m["cadence"], 150.0, places=6)
        self.assertAlmostEqual(self.m["speed"], 1.5, places=6)

    def test_duty_within_a_frame(self):
        self.assertLess(abs(self.m["duty"] - 60.0), 100.0 / 24 + 1e-9)

    def test_duty_is_finer_than_a_frame(self):
        # the contact's ends are found between frames: a foot down 60 % of the cycle reads it closer than a
        # frame's share on any cycle length (a 26-frame run is 3.8 % a frame)
        for P in (17, 24, 31):
            walk = fork_walk(P=P)
            m = asp.measure(walk, walk.clip.worlds)
            self.assertLess(abs(m["duty"] - 60.0), 0.5 * 100.0 / P, msg=P)

    def test_pelvis_swings(self):
        self.assertAlmostEqual(self.m["bob"], 3.0, places=6)
        self.assertAlmostEqual(self.m["sway"], 2.0, places=6)
        self.assertAlmostEqual(self.m["surge"], 2.0, places=6)

    def test_feet(self):
        self.assertAlmostEqual(self.m["width"], 20.0, places=6)
        for s in "lr":
            self.assertAlmostEqual(self.m["lift"][s], 10.0, delta=0.05)
            self.assertAlmostEqual(self.m["toe_out"][s], 0.0, places=6)
            self.assertAlmostEqual(self.m["swing_out"][s], 0.0, places=6)

    def test_arms_mirror(self):
        # the elbows are mirrored exactly; the upper arms' world angles within the twisting chest's share
        for key in ("elbow", "elbow_swing"):
            self.assertAlmostEqual(self.m[key]["l"], self.m[key]["r"], delta=1e-6, msg=key)
        for key in ("arm_swing", "arm_out"):
            self.assertAlmostEqual(self.m[key]["l"], self.m[key]["r"], delta=1.5, msg=key)
        self.assertGreater(self.m["elbow"]["l"], 5.0)
        self.assertGreater(self.m["arm_swing"]["l"], 10.0)

    def test_two_strides_read_the_same_pelvis(self):
        walk = fork_walk(strides=2, spans=tw.TWO_STEPS)
        m = asp.measure(walk, walk.clip.worlds)
        self.assertAlmostEqual(m["bob"], 3.0, places=4)
        self.assertAlmostEqual(m["sway"], 2.0, places=4)


class MappingTests(unittest.TestCase):
    """The animator's units into the model's knobs, relative to the walk: its own values change nothing."""

    @classmethod
    def setUpClass(cls):
        cls.walk = fork_walk()
        cls.base = asp.measure(cls.walk, cls.walk.evaluate(asp.base_engine(cls.walk)).worlds)

    def test_own_values_are_the_walk(self):
        a = self.walk.evaluate(asp.base_engine(self.walk)).worlds
        b = self.walk.evaluate(asp.engine_knobs(self.walk, self.base, {})).worlds
        self.assertLess(float(np.abs(a - b).max()), 1e-9)
        own = asp.defaults(self.base)
        c = self.walk.evaluate(asp.engine_knobs(self.walk, self.base, own)).worlds
        self.assertLess(float(np.abs(a - c).max()), 1e-9)

    def test_speed_keeps_the_walk_ratio(self):
        base = {"step": 60.0, "cadence": 150.0}
        step, cadence = asp.speed_law(base, 3.0)
        self.assertAlmostEqual(step, 60.0 * math.sqrt(2.0), places=9)
        self.assertAlmostEqual(cadence, 150.0 * math.sqrt(2.0), places=9)
        step, cadence = asp.speed_law(base, 6.0, (30.0, 96.0))
        self.assertAlmostEqual(step, 96.0, places=9)
        self.assertAlmostEqual(step * cadence / 6000.0, 6.0, places=9)

    def test_speed_sets_stride_and_tempo(self):
        e = asp.engine_knobs(self.walk, self.base, {"speed": self.base["speed"] * 2.0})
        self.assertAlmostEqual(e["stride"], math.sqrt(2.0), places=9)
        self.assertEqual(e["tempo"], float(round(self.walk.P / math.sqrt(2.0))))

    def test_weight_spreads(self):
        e = asp.engine_knobs(self.walk, self.base, {"weight": 1.0})
        self.assertAlmostEqual(e["weight"], asp.WEIGHT_GAIN)
        self.assertAlmostEqual(e["torso_drag"], 1.5)          # Weight does not drag (Follow-through does)
        self.assertEqual(e["weight_lag"], 0.0)
        self.assertEqual(e["weight_dip"], asp.WEIGHT_DIP)         # the pelvis sinks into each step...
        for s in "lr":
            self.assertEqual(e["knee_bend_" + s], 0.0)            # ...and Knee bend's cap is left to Knee bend

    def test_a_side_alone(self):
        e = asp.engine_knobs(self.walk, self.base, {"arm_swing_l": self.base["arm_swing"]["l"] + 10.0})
        self.assertAlmostEqual(e["arm_swing_add_l"], 10.0)
        self.assertAlmostEqual(e["arm_swing_add_r"], 0.0)

    def test_the_hip_drop_follows_the_hips(self):
        e = asp.engine_knobs(self.walk, self.base, {"hips": 2.0 * self.base["hips"]})
        self.assertAlmostEqual(e["pelvis_list"], self.walk.own_list + self.base["hip_drop"], places=9)
        e = asp.engine_knobs(self.walk, self.base, {"hips": 2.0 * self.base["hips"], "hip_drop": 1.0})
        self.assertAlmostEqual(e["pelvis_list"], self.walk.own_list + 1.0 - self.base["hip_drop"], places=9)

    def test_a_response_curve_is_inverted(self):
        base = dict(self.base)
        # duty: 0.8 measured a unit upward; downward 0.5 a unit to -3, then nothing (a floor)
        base["_curve"] = {"duty": {"": asp._monotone([(-10.0, -3.0), (-6.0, -3.0), (0.0, 0.0), (5.0, 4.0)])},
                          "elbow": {"l": [(-4.0, -4.0), (0.0, 0.0), (12.0, 6.0)], "r": [(0.0, 0.0), (12.0, 12.0)]}}
        up = asp.engine_knobs(self.walk, base, {"duty": base["duty"] + 4.0})
        self.assertAlmostEqual(up["ground_time"], 1.0 + 5.0 / base["duty"], places=9)
        down = asp.engine_knobs(self.walk, base, {"duty": base["duty"] - 1.5})
        self.assertAlmostEqual(down["ground_time"], 1.0 - 3.0 / base["duty"], places=9)
        floor = asp.engine_knobs(self.walk, base, {"duty": base["duty"] - 3.0})
        self.assertAlmostEqual(floor["ground_time"], 1.0 - 6.0 / base["duty"], places=9)      # the first that reaches
        e = asp.engine_knobs(self.walk, base, {"elbow_l": base["elbow"]["l"] + 3.0})
        self.assertAlmostEqual(e["elbow_add_l"], 6.0, places=9)
        lo, hi = asp.ranges(base, self.walk.leg_length)["duty"]
        self.assertAlmostEqual(lo, base["duty"] - 3.0, places=9)                        # cut to the floor

    def test_monotone_never_turns_back(self):
        pts = asp._monotone([(-6.0, -1.0), (-3.0, -2.0), (0.0, 0.0), (2.0, -0.5), (6.0, 3.0)])
        self.assertEqual(pts, [(-6.0, -2.0), (-3.0, -2.0), (0.0, 0.0), (2.0, 0.0), (6.0, 3.0)])

    def test_every_knob_has_a_range(self):
        r = asp.ranges(self.base, self.walk.leg_length)
        for k in asp.KNOBS:
            lo, hi = r[k.name]
            self.assertLess(lo, hi, k.name)
            if k.kind == "measured":
                own = asp.defaults(self.base)[k.name]
                own = [own] if not isinstance(own, dict) else own.values()
                for v in own:
                    self.assertTrue(lo - 1e-6 <= v <= hi + 1e-6 or k.sided, "%s %s %s" % (k.name, v, (lo, hi)))


class CalibrationTests(unittest.TestCase):
    """A walk probed once: the calibrated knobs then read back what is asked under the physics."""

    @classmethod
    def setUpClass(cls):
        cls.walk = fork_walk()
        cls.base = asp.measure(cls.walk, cls.walk.evaluate(asp.base_engine(cls.walk)).worlds)
        cls.gains = asp.calibrate(cls.walk, cls.base, lambda g: cls.walk.evaluate(
            asp.engine_knobs(cls.walk, cls.base, g)))                 # the response curves

    def test_the_elbow_swing_range_stops_at_the_bend(self):
        r = asp.ranges(self.base, self.walk.leg_length)
        self.assertLessEqual(r["elbow_swing"][1], min(self.base["elbow"].values()) + 1e-9)

    def test_gains_kept_for_every_calibrated_knob(self):
        for group in asp.CALIBRATED:
            for name in group:
                self.assertIn(name, self.gains)

    def test_reads_back(self):
        # (not Elbow swing: the walker's elbows are bent 12 deg, so a swing folds through straight - its range is
        # capped there, aspects.ranges)
        for name, change in (("duty", 4.0), ("duty", -4.0), ("elbow", 8.0), ("elbow", -4.0)):
            own = asp.defaults(self.base)[name]
            own = 0.5 * (own["l"] + own["r"]) if isinstance(own, dict) else own
            m = asp.measure(self.walk, self.walk.evaluate(asp.engine_knobs(
                self.walk, self.base, {name: own + change})).worlds)
            got = m[name]
            got = 0.5 * (got["l"] + got["r"]) if isinstance(got, dict) else got
            self.assertLess(abs(got - own - change), max(0.15 * abs(change), 1.0), msg=(name, change, got - own))


if __name__ == "__main__":
    unittest.main()
