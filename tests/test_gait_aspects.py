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


if __name__ == "__main__":
    unittest.main()
