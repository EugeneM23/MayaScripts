"""maya_walk.wholeclip at a fast stride (a Box clip's turn, 2026-11-19, review note F): the phase runs through the
strikes as a C1 curve, and the walk's change keeps its own accelerations where the clip's stride runs faster than
its walking pace - its motion about the cycle mean let go as (pace / rate)^2, its posture whole. Runs under mayapy."""
import math
import unittest

import numpy as np

from maya_startstop import model as ss
from maya_walk import wholeclip as wcl
from tests.test_walk_wholeclip import P, TRAVEL, loop_clip
from tests.test_walkmodel import rot_y


def strided(lengths, before=12):
    """A clip of the loop's strides, stride k lasting lengths[k] frames (the loop resampled), standing first."""
    loop = loop_clip()
    cycle = ss.Cycle(loop)
    frames = [cycle.sample(0.0)] * before
    for k, n in enumerate(lengths):
        for i in range(n):
            frames.append(cycle.sample(k * P + i * P / float(n)))
    frames.append(cycle.sample(len(lengths) * P))
    return ss.Clip(loop.names, loop.parents, np.stack(frames, axis=1), 30.0, "raw")


def swinging(loop, name="upperarm_l", deg=25.0):
    """The loop with `name` swung deg * sin(phase) more about up in its own frame, its children carried: a change
    that is all motion (its cycle mean is nothing)."""
    w = loop.worlds.copy()
    j = loop.index[name]
    for f in range(loop.F):
        before = w[:, f].copy()
        new = before[j].copy()
        new[:3, :3] = rot_y(deg * math.sin(2.0 * math.pi * f / float(P))) @ before[j][:3, :3]
        changed = {j: new}
        for i in loop.order:
            q = loop.parents[i]
            if i != j and q in changed:
                changed[i] = before[i] @ np.linalg.inv(before[q]) @ changed[q]
        for i, m in changed.items():
            w[i, f] = m
    return ss.Clip(loop.names, loop.parents, w, loop.fps, "swing")


def change_accel(out, raw, name):
    """(F-2,) the second difference of what the change did to `name`'s place (the result less the clip)."""
    j = raw.index[name]
    d = out[j, :, 3, :3] - raw.worlds[j, :, 3, :3]
    return np.linalg.norm(np.diff(d, 2, axis=0), axis=1)


class Monotone(unittest.TestCase):
    def test_through_the_knots_rising_and_c1(self):
        x = np.array([0.0, 24.0, 40.0, 64.0, 88.0])
        y = np.array([0.0, 24.0, 48.0, 72.0, 96.0])
        at = np.arange(-10.0, 100.0, 0.25)
        v = wcl.monotone(x, y, at)
        np.testing.assert_allclose(wcl.monotone(x, y, x), y, atol=1e-12)
        self.assertTrue(np.all(np.diff(v) > 0.0))
        slope = np.diff(v) / 0.25
        self.assertLess(float(np.abs(np.diff(slope)).max()), 0.1)        # no jump in the rate anywhere
        np.testing.assert_allclose(slope[:30], 1.0, atol=1e-9)          # the end secant carried on

    def test_a_straight_line_stays_straight(self):
        x = np.array([0.0, 10.0, 25.0, 40.0])
        np.testing.assert_allclose(wcl.monotone(x, 2.0 * x + 1.0, np.arange(-5.0, 45.0)),
                                   2.0 * np.arange(-5.0, 45.0) + 1.0, atol=1e-12)


class Share(unittest.TestCase):
    def test_a_stride_a_little_faster_than_the_pace_takes_the_whole_change(self):
        phases = np.concatenate([np.arange(0.0, 24.0), 24.0 + 1.08 * np.arange(22), 47.76 + np.arange(24)])
        self.assertTrue(np.all(wcl.change_share(phases, [(0, 24), (24, 46), (46, 69)]) == 1.0))

    def test_all_of_the_change_at_the_clips_pace_and_less_past_it(self):
        phases = np.concatenate([np.arange(0.0, 24.0), 24.0 + 1.5 * np.arange(16), 48.0 + np.arange(24)])
        walking = [(0, 24), (24, 40), (40, 63)]
        share = wcl.change_share(phases, walking)
        self.assertTrue(np.all(share[2:22] == 1.0))
        np.testing.assert_allclose(share[27:37], (wcl.RATE_FREE / 1.5) ** 2, atol=1e-9)

    def test_a_clip_slower_than_its_loop_takes_the_whole_change(self):
        phases = 0.8 * np.arange(60.0)
        self.assertTrue(np.all(wcl.change_share(phases, [(0, 30), (30, 59)]) == 1.0))

    def test_the_pace_is_the_clips_own_walking_pace(self):
        phases = 1.3 * np.arange(80.0)                       # every stride 30 % faster than the loop: nothing let go
        self.assertTrue(np.all(wcl.change_share(phases, [(0, 20), (20, 40), (40, 60)]) == 1.0))


class FastStride(unittest.TestCase):
    LENGTHS = (P, P, 16, P, P)

    def setUp(self):
        self.raw = strided(self.LENGTHS)
        self.loop = loop_clip()

    def test_the_walks_own_values_give_the_clip_back(self):
        out, info = wcl.build(self.raw, self.loop, self.loop)
        self.assertLess(float(info["change_share"].min()), 0.9)
        np.testing.assert_allclose(out[:, :, 3, :3], self.raw.worlds[:, :, 3, :3], atol=1e-6)
        np.testing.assert_allclose(out[:, :, :3, :3], self.raw.worlds[:, :, :3, :3], atol=1e-6)

    def test_the_phase_hits_every_strike_and_its_rate_has_no_jump(self):
        _out, info = wcl.build(self.raw, self.loop, self.loop)
        phases = info["phases"]
        walking = info["walking"]
        for i, (t0, _t1) in enumerate(walking):
            self.assertAlmostEqual(phases[t0] - phases[walking[0][0]], i * P, places=9)
        rate = np.diff(phases)
        self.assertLess(float(np.abs(np.diff(rate)).max()), 0.15)

    def test_the_change_is_no_sharper_at_the_fast_stride(self):
        out, info = wcl.build(self.raw, self.loop, swinging(self.loop))
        acc = change_accel(out, self.raw, "hand_l")
        fast = [s for s in info["walking"] if s[1] - s[0] < P - 2][0]
        inside = acc[fast[0]:fast[1] - 2].max()
        normal = max(acc[t0:t1 - 2].max() for t0, t1 in info["walking"] if t1 - t0 >= P - 2)
        self.assertLess(inside, 1.1 * normal)
        # before: laid at the stride's own rate (24 / 16), its accelerations x2.25
        old = wcl.walk_difference(self.raw, ss.Cycle(self.loop), ss.Cycle(swinging(self.loop)), info["phases"],
                                  self.raw.names, self.loop.names)
        whole = np.stack([wcl._fk(self.raw, old[0][:, f], old[1][:, f], wcl._scales(self.raw.worlds[:, f]))
                          for f in range(self.raw.F)], axis=1)
        self.assertGreater(change_accel(whole, self.raw, "hand_l")[fast[0]:fast[1] - 2].max(), 1.5 * normal)

    def test_the_changes_posture_stays_whole(self):
        loop = self.loop
        posed = swinging(loop, deg=0.0)
        w = posed.worlds.copy()
        j = loop.index["upperarm_l"]
        for f in range(loop.F):                              # a constant 15 deg: all posture, no motion
            before = w[:, f].copy()
            new = before[j].copy()
            new[:3, :3] = rot_y(15.0) @ before[j][:3, :3]
            changed = {j: new}
            for i in loop.order:
                q = loop.parents[i]
                if i != j and q in changed:
                    changed[i] = before[i] @ np.linalg.inv(before[q]) @ changed[q]
            for i, m in changed.items():
                w[i, f] = m
        out, _info = wcl.build(self.raw, loop, ss.Clip(loop.names, loop.parents, w, 30.0, "posed"))
        q = self.raw.parents[j]
        for f in range(self.raw.F):
            got = ss.orthonormal(out[j, f]) @ ss.orthonormal(out[q, f]).T
            had = ss.orthonormal(self.raw.worlds[j, f]) @ ss.orthonormal(self.raw.worlds[q, f]).T
            angle = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(got @ had.T) - 1.0) / 2.0))))
            self.assertAlmostEqual(angle, 15.0, places=4)


if __name__ == "__main__":
    unittest.main()
