"""Gait Builder's CAT presets as clips (docs/superpowers/plans/gaitbuilder/gaitgen.py): each one analyses as a
cycle that closes, and measures the step and the ground time the preset asks. numpy only."""

import unittest

import numpy as np

from tests.test_gait_model import load

gm = load("gaitmodel")
asp = load("aspects")
gen = load("gaitgen")


class Presets(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cm = gen._catmodel()
        cls.cm = cm
        cls.leg = cm.Skeleton.from_template(gen.template()).leg
        cls.made = dict((name, gen.preset_clip(name, 30.0, gm)) for name in gen.PRESETS)

    def test_every_preset_closes(self):
        for name, (clip, statics) in self.made.items():
            w = np.asarray(clip.worlds)
            travel = w[0, -1, 3, :3] - w[0, 0, 3, :3]
            seam = np.abs(w[:, -1, 3, :3] - w[:, 0, 3, :3] - travel).max()
            self.assertLess(seam, 1e-6, name)
            self.assertEqual(set(statics), set(clip.names))

    def test_measures_the_preset_s_step_and_ground_time(self):
        for name, (clip, _) in self.made.items():
            walk = gm.analyse(clip)
            m = asp.measure(walk, clip.worlds)
            k = self.cm.preset(name, 30.0)
            self.assertAlmostEqual(m["step"], k["stride"] * self.leg, delta=0.1, msg=name)
            # a foot's contact read off its height lands within a frame of the preset's stance
            self.assertLess(abs(m["duty"] - 100.0 * k["duty"]), 100.0 / walk.P, name)

    def test_a_preset_is_a_source(self):
        gl = load("gaitload")
        kept = gl.DISK
        try:
            gl.DISK = None
            src = gl.from_preset("Walk", 30.0)
            self.assertEqual(src.label, "CAT Walk")
            self.assertTrue(src.ident)
        finally:
            gl.DISK = kept


if __name__ == "__main__":
    unittest.main()
