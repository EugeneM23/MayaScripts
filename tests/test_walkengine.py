"""The walk engine's knobs added for the editable gait model (2026-10-26, maya_walk.model): each defaults to no
change, and each moves exactly what it names - on the synthetic walker of tests/test_walkmodel.py."""

import math
import unittest

import numpy as np

from tests import test_walkmodel as tw

wm = tw.wm


def apart(a, b):
    return float(np.abs(np.asarray(a.worlds) - np.asarray(b.worlds)).max())


def trunk_lean(w, r):
    """The neck_01 - pelvis line's mean angle from up, toward the body's front (degrees)."""
    v = r.worlds[w.index["neck_01"], :-1, 3, :3] - r.worlds[w.index["pelvis"], :-1, 3, :3]
    return float(np.degrees(np.arctan2(v @ w.ahead, v @ w.up)).mean())


class EngineKnobTests(unittest.TestCase):

    def test_the_engine_only_knobs_follow_the_card_s(self):
        self.assertEqual(wm.LEGACY[-1], "exaggeration")
        self.assertEqual(set(wm.LEGACY) | set(wm.ENGINE_ONLY), set(wm.DEFAULTS))
        self.assertFalse(set(wm.LEGACY) & set(wm.ENGINE_ONLY))

    def test_new_engine_knobs_default_to_no_change(self):
        w = tw.walk()
        base = w.evaluate({})
        again = w.evaluate(dict((k, wm.DEFAULTS[k]) for k in wm.ENGINE_ONLY))
        self.assertLess(apart(base, again), 1e-9)

    def test_lean_add_leans_the_trunk(self):
        w = tw.walk()
        a, b = w.evaluate({}), w.evaluate({"lean_add": 10.0})
        self.assertAlmostEqual(trunk_lean(w, b) - trunk_lean(w, a), 10.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
