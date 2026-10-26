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


def bumped(height=1.0, at=6.0, width=1.2):
    """The synthetic walker with a bump in its body: the pelvis and everything above it (not the legs) raised by
    a narrow bell at frame `at` - a motion the stride harmonics cannot hold (the residual)."""
    c = tw.clip()
    legs = set(i for i, n in enumerate(c.names) if n.split("_")[0] in ("thigh", "calf", "foot", "ball", "ik"))
    up = set()
    pel = c.names.index("pelvis")
    for j in range(len(c.names)):
        p = j
        while p >= 0 and p != pel:
            p = c.parents[p]
        if p == pel and j not in legs:
            up.add(j)
    frames = c.worlds.shape[1]
    for f in range(frames):
        g = f % (frames - 1)
        dy = height * math.exp(-((g - at) / width) ** 2)
        for j in up:
            c.worlds[j, f, 3, 1] += dy
    return wm.analyse(c)


def still(w):
    """The walk's own knobs with Balance off: no physics moving the body (exact gates)."""
    return dict(w.own_knobs(), balance=0.0)


def regular_p2p(w, y, n=None):
    """Peak to peak of the regular part (the stride harmonics) of a cycle's samples `y` (n frames of a result:
    source times f P / n), read on a fine grid."""
    n = len(y) if n is None else n
    taus = np.arange(n) * w.P / float(n)
    fit, coef = w.regular_fit(np.asarray(y, float), taus)
    fine = np.arange(n * 8) * w.P / float(n * 8)
    return float(np.ptp(w.harmonic_basis(fine) @ coef))


def residual_rms(w, y):
    n = len(y)
    fit, _ = w.regular_fit(np.asarray(y, float), np.arange(n) * w.P / float(n))
    return float(np.sqrt(np.mean((np.asarray(y) - fit) ** 2)))


def pelvis_height(w, r):
    return r.worlds[w.index["pelvis"], :-1, 3, :3] @ w.up


class DecompositionTests(unittest.TestCase):

    def test_regular_plus_residual_is_the_series(self):
        w = tw.walk(strides=2, spans=tw.TWO_STEPS)
        self.assertTrue(w.decomposed)
        for (series, j), (reg, res, mean) in w.decomposed.items():
            src = getattr(w, series)[j]
            self.assertLess(float(np.abs(reg + res - src).max()), 1e-9, (series, w.names[j]))

    def test_the_residual_is_orthogonal_to_the_harmonics(self):
        w = tw.walk(strides=2, spans=tw.TWO_STEPS)
        B = w.harmonic_basis()
        for (series, j), (reg, res, mean) in w.decomposed.items():
            self.assertLess(float(np.abs(B.T @ res).max()), 1e-6, (series, w.names[j]))

    def test_the_legs_and_the_helpers_are_not_decomposed(self):
        w = tw.walk()
        names = set(w.names[j] for _, j in w.decomposed)
        for name in ("thigh_l", "calf_r", "foot_l", "ball_r", "ik_foot_l", "camera_root"):
            self.assertNotIn(name, names)
        for name in ("pelvis", "spine_01", "head", "upperarm_l", "lowerarm_r", "index_01_l"):
            self.assertIn(name, names)

    def test_detail_one_and_gains_one_change_nothing(self):
        w = tw.walk()
        base = w.evaluate({})
        same = w.evaluate({"detail": 1.0, "g_bob": 1.0, "g_arm": 1.0, "g_spine": 1.0})
        self.assertLess(apart(base, same), 1e-9)

    def test_g_bob_scales_the_regular_bob_exactly(self):
        w = tw.walk()
        own = still(w)
        a = regular_p2p(w, pelvis_height(w, w.evaluate(own)))
        b = regular_p2p(w, pelvis_height(w, w.evaluate(dict(own, g_bob=0.5))))
        self.assertAlmostEqual(b, 0.5 * a, delta=1e-3 * a)

    def test_g_sway_scales_the_regular_sway_exactly(self):
        w = tw.walk()
        own = still(w)
        side = lambda r: r.worlds[w.index["pelvis"], :-1, 3, :3] @ w.lside
        a = regular_p2p(w, side(w.evaluate(own)))
        b = regular_p2p(w, side(w.evaluate(dict(own, g_sway=0.5))))
        self.assertAlmostEqual(b, 0.5 * a, delta=1e-3 * a)

    def test_detail_zero_leaves_the_regular_part(self):
        w = bumped()
        own = still(w)
        y0 = pelvis_height(w, w.evaluate(own))
        y1 = pelvis_height(w, w.evaluate(dict(own, detail=0.0)))
        self.assertGreater(residual_rms(w, y0), 0.01)
        self.assertLess(residual_rms(w, y1), 0.1 * residual_rms(w, y0))

    def test_g_arm_scales_one_arm(self):
        w = tw.walk()
        own = still(w)
        up = w.index["upperarm_l"]
        rot = lambda r, j: np.array([wm.log_rot(r.worlds[j, f, :3, :3] @ r.worlds[j, 0, :3, :3].T) for f in range(24)])
        a, b = w.evaluate(own), w.evaluate(dict(own, g_arm_l=0.0))
        self.assertLess(float(np.abs(rot(b, up)).max()), 0.05 * float(np.abs(rot(a, up)).max()) + 1e-3)
        right = w.index["upperarm_r"]
        self.assertLess(float(np.abs(a.worlds[right] - b.worlds[right]).max()), 1e-6)

    def test_bob_add_where_there_is_none(self):
        w = tw.walk()
        own = still(w)
        flat = dict(own, g_bob=0.0)
        y = pelvis_height(w, w.evaluate(dict(flat, bob_add=4.0)))
        self.assertAlmostEqual(regular_p2p(w, y), 4.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
