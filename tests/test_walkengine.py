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


def pitches(w, r, side):
    """The foot's sole pitch on each frame of a result, degrees (+ heel up, - toes up)."""
    fo = w.index["foot_" + side]
    return np.array([math.degrees(w.sole_pitch(side, r.worlds[fo, f, :3, :3])) for f in range(r.frames)])


def added_near(w, a, b, side, at, before, after):
    """The most the foot's pitch changes from result a to result b (b - a, signed by the larger) on the frames
    from `before` frames before each contact's `at` ("hs" / "to") to `after` after it, the mean over the
    contacts, degrees."""
    pa, pb, n = pitches(w, a, side), pitches(w, b, side), a.frames
    out = []
    for hs, to in b.info["contacts"][side]:
        c = int(round(hs if at == "hs" else to))
        d = [pb[(c + i) % n] - pa[(c + i) % n] for i in range(-before, after + 1)]
        out.append(max(d, key=abs))
    return float(np.mean(out))


class TimingTests(unittest.TestCase):

    def test_contacts_are_reported_in_the_new_cycle_s_frames(self):
        w = tw.walk()
        r = w.evaluate({"tempo": 48})
        self.assertEqual(r.frames, 48)
        for side in "lr":
            self.assertEqual(len(r.info["contacts"][side]), len(w.contact[side]))
            for hs, to in r.info["contacts"][side]:
                self.assertGreater(to, hs)

    def test_duty_sets_each_contact_directly(self):
        w = tw.walk()
        r = w.evaluate({"duty": 0.68})
        stride = r.frames / float(w.strides)
        for side in "lr":
            for hs, to in r.info["contacts"][side]:
                self.assertAlmostEqual((to - hs) / stride, 0.68, delta=1e-6)
            self.assertAlmostEqual(r.info["ground"][side][0][1], 0.68, delta=1e-6)

    def test_duty_shortens_too(self):
        w = tw.walk()
        r = w.evaluate({"duty": 0.55})
        stride = r.frames / float(w.strides)
        for side in "lr":
            for hs, to in r.info["contacts"][side]:
                self.assertAlmostEqual((to - hs) / stride, 0.55, delta=1e-6)

    def test_duty_per_side(self):
        w = tw.walk()
        r = w.evaluate({"duty_l": 0.7})
        stride = r.frames / float(w.strides)
        own = w.evaluate({})
        for (hs, to), (hs0, to0) in zip(r.info["contacts"]["r"], own.info["contacts"]["r"]):
            self.assertAlmostEqual(to - hs, to0 - hs0, delta=1e-6)
        self.assertAlmostEqual((r.info["contacts"]["l"][0][1] - r.info["contacts"]["l"][0][0]) / stride, 0.7,
                               delta=1e-6)

    def test_push_lifts_the_heel_at_the_toe_off(self):
        w = tw.walk()
        a, b = w.evaluate({}), w.evaluate({"push": 15.0})
        self.assertAlmostEqual(added_near(w, a, b, "l", "to", 2, 1), 15.0, delta=0.5)

    def test_push_keeps_the_ball_on_the_ground(self):
        w = tw.walk()
        b = w.evaluate({"push": 20.0})
        a = w.evaluate({})
        ball = w.index["ball_l"]
        for hs, to in b.info["contacts"]["l"]:
            f = int(math.floor(to)) % b.frames
            ha = a.worlds[ball, f, 3, :3] @ w.up
            hb = b.worlds[ball, f, 3, :3] @ w.up
            self.assertLess(abs(hb - ha), 0.05)

    def test_heel_strike_lifts_the_toes_at_the_contact(self):
        w = tw.walk()
        a, b = w.evaluate({}), w.evaluate({"heel_strike": 10.0})
        self.assertAlmostEqual(-added_near(w, a, b, "r", "hs", 1, 1), 10.0, delta=0.5)

    def test_heel_strike_is_gone_by_the_foot_flat(self):
        w = tw.walk()
        a, b = w.evaluate({}), w.evaluate({"heel_strike": 10.0})
        pa, pb = pitches(w, a, "r"), pitches(w, b, "r")
        n = a.frames
        for hs, to in b.info["contacts"]["r"]:
            mid = int(round(0.5 * (hs + to))) % n
            self.assertLess(abs(pb[mid] - pa[mid]), 0.05)

    def test_slap_slows_the_toes_coming_down(self):
        w = tw.walk()
        fast = pitches(w, w.evaluate({"heel_strike": 10.0}), "r")
        slow = pitches(w, w.evaluate({"heel_strike": 10.0, "slap": 4.0}), "r")
        base = pitches(w, w.evaluate({}), "r")
        hs = int(round(w.evaluate({}).info["contacts"]["r"][0][0]))
        n = len(base)
        later = sum(-(slow[(hs + d) % n] - base[(hs + d) % n]) for d in range(1, 6))
        sooner = sum(-(fast[(hs + d) % n] - base[(hs + d) % n]) for d in range(1, 6))
        self.assertGreater(later, sooner + 1.0)

    def test_rolls_work_without_foot_placement(self):
        w = tw.walk()
        a = w.evaluate({"foot_placement": 0.0})
        b = w.evaluate({"foot_placement": 0.0, "push": 15.0})
        self.assertAlmostEqual(added_near(w, a, b, "l", "to", 2, 1), 15.0, delta=0.5)


def world_rots(r, j):
    return [r.worlds[j, f, :3, :3] for f in range(r.frames)]


def local_rots(w, r, name):
    j = w.index[name]
    p = w.parents[j]
    return [r.worlds[j, f, :3, :3] @ r.worlds[p, f, :3, :3].T for f in range(r.frames)]


def shifted_by(a, b, frames):
    """The most rotation b[f] differs from a[f - frames], degrees."""
    n = len(a)
    return max(tw.angle(a[(f - frames) % n].T @ b[f]) for f in range(n))


def low_time(w, r):
    """When the pelvis height's regular part is lowest, frames of the result (on a fine grid)."""
    y = pelvis_height(w, r)
    n = len(y)
    _, coef = w.regular_fit(y, np.arange(n) * w.P / float(n))
    fine = np.arange(n * 64) * w.P / float(n * 64)
    return float(np.argmin(w.harmonic_basis(fine) @ coef)) / 64.0


class LagTests(unittest.TestCase):

    def test_lag_knobs_default_to_none(self):
        w = tw.walk()
        self.assertEqual(w.lags(wm.DEFAULTS, {"l": wm.DEFAULTS, "r": wm.DEFAULTS}, 1.0), {})

    def test_arm_lag_shifts_the_arm_exactly(self):
        w = tw.walk()
        own = still(w)
        a, b = w.evaluate(own), w.evaluate(dict(own, arm_lag=2.0))
        self.assertLess(shifted_by(world_rots(a, w.index["upperarm_l"]), world_rots(b, w.index["upperarm_l"]), 2), 0.05)
        self.assertLess(shifted_by(world_rots(a, w.index["lowerarm_r"]), world_rots(b, w.index["lowerarm_r"]), 2), 0.05)

    def test_arm_lag_per_side(self):
        w = tw.walk()
        own = still(w)
        a, b = w.evaluate(own), w.evaluate(dict(own, arm_lag_l=3.0))
        self.assertLess(shifted_by(world_rots(a, w.index["upperarm_l"]), world_rots(b, w.index["upperarm_l"]), 3), 0.05)
        right = w.index["upperarm_r"]
        self.assertLess(float(np.abs(a.worlds[right, :, :3, :3] - b.worlds[right, :, :3, :3]).max()), 1e-9)

    def test_elbow_lag_shifts_the_forearm_in_the_upper_arm(self):
        w = tw.walk()
        own = still(w)
        a, b = w.evaluate(own), w.evaluate(dict(own, elbow_lag=2.0))
        self.assertLess(shifted_by(local_rots(w, a, "lowerarm_l"), local_rots(w, b, "lowerarm_l"), 2), 0.05)
        up = w.index["upperarm_l"]
        self.assertLess(float(np.abs(a.worlds[up, :, :3, :3] - b.worlds[up, :, :3, :3]).max()), 1e-9)

    def test_torso_lag_shifts_the_neck_and_not_spine_01(self):
        w = tw.walk()
        own = still(w)
        a, b = w.evaluate(own), w.evaluate(dict(own, torso_lag=2.0))
        self.assertLess(shifted_by(local_rots(w, a, "neck_01"), local_rots(w, b, "neck_01"), 2), 0.05)
        levels = w.lags(dict(wm.DEFAULTS, torso_lag=1.0), {"l": wm.DEFAULTS, "r": wm.DEFAULTS}, 1.0)
        self.assertNotIn(w.index["spine_01"], levels)
        self.assertAlmostEqual(levels[w.index["neck_01"]], 1.0)

    def test_head_lag_shifts_the_head_s_world_turn(self):
        w = tw.walk()
        own = still(w)
        a, b = w.evaluate(own), w.evaluate(dict(own, head_lag=2.0))
        self.assertLess(shifted_by(world_rots(a, w.index["head"]), world_rots(b, w.index["head"]), 2), 0.05)

    def test_bob_shift_moves_the_low_point(self):
        w = tw.walk()
        own = still(w)
        step = w.P / (2.0 * w.strides)           # the bob is lowest once a step
        moved = (low_time(w, w.evaluate(dict(own, bob_shift=2.0))) - low_time(w, w.evaluate(own))) % step
        self.assertAlmostEqual(moved, 2.0, delta=0.05)

    def test_double_bounce_adds_two_lows_a_step(self):
        w = tw.walk()
        flat = dict(still(w), g_bob=0.0)
        y = pelvis_height(w, w.evaluate(dict(flat, double_bounce=3.0)))
        self.assertAlmostEqual(regular_p2p(w, y), 3.0, delta=0.05)
        n = len(y)
        _, coef = w.regular_fit(y, np.arange(n) * w.P / float(n))
        fine = w.harmonic_basis(np.arange(n * 16) * w.P / float(n * 16)) @ coef
        lows = sum(1 for i in range(len(fine)) if fine[i] < fine[i - 1] and fine[i] < fine[(i + 1) % len(fine)])
        self.assertEqual(lows, 4 * w.strides)

    def test_chest_phase_turns_the_chest_s_twist_later(self):
        w = tw.walk()
        own = still(w)

        def phase(r):
            ul, ur = w.index["upperarm_l"], w.index["upperarm_r"]
            d = r.worlds[ul, :-1, 3, :3] - r.worlds[ur, :-1, 3, :3]
            yaw = np.degrees(np.arctan2(d @ w.fwd, d @ w.lside))
            a = np.array([w.stride_phase(f * w.P / float(len(yaw))) for f in range(len(yaw))])
            yaw = yaw - yaw.mean()
            return math.degrees(math.atan2(float(np.dot(yaw, np.sin(a))), float(np.dot(yaw, np.cos(a)))))
        # later by about the asked phase: the spine takes a share of a world turn (maya_walk.gait reads it back)
        base = phase(w.evaluate(own))
        later = (phase(w.evaluate(dict(own, chest_phase=60.0))) - base + 180.0) % 360.0 - 180.0
        sooner = (phase(w.evaluate(dict(own, chest_phase=-60.0))) - base + 180.0) % 360.0 - 180.0
        self.assertGreater(later, 30.0)
        self.assertLess(later, 70.0)
        self.assertLess(sooner, -30.0)


def arm_forward(w, r, side="l"):
    """The upper arm's forward angle a frame (degrees): its direction forward of hanging."""
    a = r.worlds[w.index["lowerarm_" + side], :-1, 3, :3] - r.worlds[w.index["upperarm_" + side], :-1, 3, :3]
    a = a / np.linalg.norm(a, axis=1, keepdims=True)
    return np.degrees(np.arctan2(a @ w.ahead, -(a @ w.up)))


def first_harmonic(w, y):
    """(amplitude, time of its peak in frames) of a cycle's first stride harmonic."""
    n = len(y)
    a = np.array([w.stride_phase(f * w.P / float(n)) for f in range(n)])
    y = y - y.mean()
    c, s = 2.0 / n * float(np.dot(y, np.cos(a))), 2.0 / n * float(np.dot(y, np.sin(a)))
    return math.hypot(c, s), math.atan2(s, c) / (2.0 * math.pi) * n / w.strides


class WhipTests(unittest.TestCase):

    def test_spring_comp_keeps_the_stride_swing(self):
        w = tw.walk()
        own = still(w)
        bare = first_harmonic(w, arm_forward(w, w.evaluate(own)))
        plain = first_harmonic(w, arm_forward(w, w.evaluate(dict(own, arm_drag=1.5, arm_bounce=0.3))))
        kept = first_harmonic(w, arm_forward(w, w.evaluate(dict(own, arm_drag=1.5, arm_bounce=0.3, spring_comp=1.0))))
        self.assertLess(abs(kept[0] / bare[0] - 1.0), 0.05)
        self.assertLess(abs(kept[1] - bare[1]), 0.3)
        self.assertGreater(abs(plain[1] - bare[1]), 0.5)          # a plain spring lags it

    def test_spring_comp_on_the_trunk(self):
        w = tw.walk()
        own = still(w)
        r = w.evaluate(dict(own, torso_drag=1.5, head_drag=2.0, spring_comp=1.0))
        self.assertTrue(np.all(np.isfinite(r.worlds)))


if __name__ == "__main__":
    unittest.main()
