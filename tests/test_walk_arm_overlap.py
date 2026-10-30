"""Walk Builder's Arm overlap: the time shift, the IK rebuild it feeds, and the pass on the cycle."""

import math
import unittest

import numpy as np

from tests.test_walkmodel import load, positions, rot_y, walk, wm

gait = load("gait")


def cycle(n=8, travel=(0.0, 0.0, 80.0)):
    """A cycle of world matrices (n+1, 4, 4): a full turn about Y, a circle in place, and a travel - the last
    frame the first moved by the travel, as every cycle of the model is."""
    out = np.tile(np.eye(4), (n + 1, 1, 1))
    per = np.array(travel, float) / float(n)
    for f in range(n + 1):
        a = 360.0 * (f % n) / float(n)
        out[f, :3, :3] = rot_y(a)
        out[f, 3, :3] = np.array([10.0 * math.cos(math.radians(a)), 3.0 * math.sin(math.radians(a)),
                                  0.0]) + per * f
    return out


def rel(mats, f, per):
    """A frame's place with the travel taken out."""
    return mats[f, 3, :3] - per * f


class ShiftedCycleTests(unittest.TestCase):

    def test_no_lag_gives_the_input_back(self):
        mats = cycle()
        self.assertTrue(np.array_equal(wm.shifted_cycle(mats, 0.0), mats))

    def test_a_whole_lag_is_the_frame_that_many_earlier(self):
        mats, n = cycle(), 8
        per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
        got = wm.shifted_cycle(mats, 2.0)
        for f in range(n + 1):
            was = (f - 2) % n
            self.assertTrue(np.allclose(got[f, :3, :3], mats[was, :3, :3], atol=1e-9), f)
            self.assertTrue(np.allclose(rel(got, f, per), rel(mats, was, per), atol=1e-9), f)

    def test_a_fractional_lag_falls_between_the_two_frames(self):
        mats = cycle()
        half = wm.shifted_cycle(mats, 2.5)
        early, late = wm.shifted_cycle(mats, 3.0), wm.shifted_cycle(mats, 2.0)
        turn = lambda a, b: math.degrees(float(np.linalg.norm(wm.log_rot(a[:3, :3].T @ b[:3, :3]))))
        self.assertAlmostEqual(turn(early[4], half[4]), turn(half[4], late[4]), places=6)
        self.assertTrue(np.allclose(half[4, 3, :3], 0.5 * (early[4, 3, :3] + late[4, 3, :3]), atol=1e-9))

    def test_the_result_is_a_cycle_again(self):
        mats, n = cycle(), 8
        travel = mats[n, 3, :3] - mats[0, 3, :3]
        for lag in (1.0, 2.5, -3.0):
            got = wm.shifted_cycle(mats, lag)
            self.assertTrue(np.allclose(got[n, :3, :3], got[0, :3, :3], atol=1e-9), lag)
            self.assertTrue(np.allclose(got[n, 3, :3] - got[0, 3, :3], travel, atol=1e-9), lag)

    def test_a_negative_lag_runs_the_other_way(self):
        mats, n = cycle(), 8
        per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
        got = wm.shifted_cycle(mats, -2.0)
        self.assertTrue(np.allclose(rel(got, 0, per), rel(mats, 2, per), atol=1e-9))


class LateBendTests(unittest.TestCase):
    """The bend plane a chain gives `lag` frames earlier - the hint the cascade's elbow rides."""

    def chain(self, n=8, travel=(0.0, 0.0, 80.0)):
        """Three cycles: a shoulder in place, a wrist out along +X, and an elbow whose offset from that line
        turns about X with the phase - so the bend plane is a different one at every frame."""
        up, low, hand = (np.tile(np.eye(4), (n + 1, 1, 1)) for _ in range(3))
        per = np.array(travel, float) / float(n)
        for f in range(n + 1):
            a = math.radians(360.0 * (f % n) / float(n))
            up[f, 3, :3] = per * f
            hand[f, 3, :3] = np.array([20.0, 0.0, 0.0]) + per * f
            low[f, 3, :3] = np.array([10.0, 4.0 * math.cos(a), 4.0 * math.sin(a)]) + per * f
        return up, low, hand

    def test_no_lag_is_the_frames_own_plane(self):
        up, low, hand = self.chain()
        got = wm.late_bend(up, low, hand, 0.0)
        for f in range(got.shape[0]):
            want = low[f, 3, :3] - up[f, 3, :3]
            e = wm._unit(hand[f, 3, :3] - up[f, 3, :3])
            want = wm._unit(want - np.dot(want, e) * e)
            self.assertTrue(np.allclose(got[f], want, atol=1e-9), f)

    def test_a_lag_is_the_plane_that_many_frames_earlier(self):
        up, low, hand = self.chain()
        got, now = wm.late_bend(up, low, hand, 2.0), wm.late_bend(up, low, hand, 0.0)
        n = up.shape[0] - 1
        for f in range(n):
            self.assertTrue(np.allclose(got[f], now[(f - 2) % n], atol=1e-9), f)

    def test_the_travel_does_not_enter_it(self):
        """The hint is read from differences at ONE frame, so a travelling cycle gives the same planes as a
        cycle standing still."""
        moving = wm.late_bend(*self.chain(), lag=2.5)
        still = self.chain(travel=(0.0, 0.0, 0.0))
        self.assertTrue(np.allclose(moving, wm.late_bend(still[0], still[1], still[2], 2.5), atol=1e-9))

    def test_every_hint_is_a_unit_vector(self):
        got = wm.late_bend(*self.chain(), lag=1.5)
        for f in range(got.shape[0]):
            self.assertAlmostEqual(float(np.linalg.norm(got[f])), 1.0, places=9, msg=f)


class KnobTests(unittest.TestCase):

    def test_the_engine_carries_a_sided_arm_overlap_knob(self):
        self.assertEqual(wm.DEFAULTS["arm_overlap"], 0.0)
        self.assertEqual(wm.RANGES["arm_overlap"], (-120.0, 120.0))
        self.assertIn("arm_overlap", wm.SIDED)
        self.assertEqual(wm.SIDE_KNOBS["arm_overlap_l"], "arm_overlap")
        self.assertIn("arm_overlap", wm.ENGINE_ONLY)
        k = wm.knobs(arm_overlap_l=3.0)
        self.assertEqual(wm.sided(k)["l"]["arm_overlap"], 3.0)
        self.assertEqual(wm.sided(k)["r"]["arm_overlap"], 0.0)

    def test_the_engine_carries_the_two_cascade_knobs(self):
        """Elbow overlap and Hand overlap (2026-10-30): the same shape as the arm's, their own 0."""
        for name in ("elbow_overlap", "hand_overlap"):
            self.assertEqual(wm.DEFAULTS[name], 0.0, name)
            self.assertEqual(wm.RANGES[name], (-120.0, 120.0), name)
            self.assertIn(name, wm.SIDED, name)
            self.assertEqual(wm.SIDE_KNOBS[name + "_l"], name)
            self.assertIn(name, wm.ENGINE_ONLY, name)
            k = wm.knobs(**{name + "_l": 3.0})
            self.assertEqual(wm.sided(k)["l"][name], 3.0, name)
            self.assertEqual(wm.sided(k)["r"][name], 0.0, name)


class ArmToHandTests(unittest.TestCase):
    """The shared two-bone IK rebuild: an arm taken to a wanted hand from the current shoulder."""

    def setUp(self):
        self.w = walk()
        self.r = self.w.evaluate({"balance": 0.0})
        self.kin = np.array(self.r.worlds)
        self.n = self.r.frames
        self.chains = self.w._arm_chains()

    def test_the_arms_own_hands_give_the_arms_back(self):
        hands = dict((side, np.array(self.kin[chain[-1]])) for side, chain in self.chains.items())
        got = self.w._arm_to_hand(self.kin, self.n, self.chains, hands)
        self.assertEqual(len(got), 3 * len(self.chains))
        for j, m in got.items():
            self.assertTrue(np.allclose(m[:, 3, :3], self.kin[j][:, 3, :3], atol=1e-6), self.w.names[j])
            self.assertTrue(np.allclose(m[:, :3, :3], self.kin[j][:, :3, :3], atol=1e-6), self.w.names[j])

    def test_a_moved_hand_is_reached_and_the_bones_keep_their_lengths(self):
        """A hand moved 2 cm toward its shoulder - the synthetic walker's arm hangs 98.6 .. 100.0 % extended,
        so a hand moved outward is past its reach and clamped (that is the test below)."""
        side = sorted(self.chains)[0]
        up_j, low_j, hand_j = self.chains[side]
        want = np.array(self.kin[hand_j])
        toward = self.kin[up_j][:, 3, :3] - self.kin[hand_j][:, 3, :3]
        want[:, 3, :3] += 2.0 * toward / np.linalg.norm(toward, axis=1)[:, None]
        got = self.w._arm_to_hand(self.kin, self.n, self.chains, {side: want})
        self.assertNotIn(self.chains["r" if side == "l" else "l"][0], got)
        self.assertTrue(np.allclose(got[hand_j][:, 3, :3], want[:, 3, :3], atol=1e-6))
        for a, b in ((up_j, low_j), (low_j, hand_j)):
            was = np.linalg.norm(self.kin[b][:, 3, :3] - self.kin[a][:, 3, :3], axis=1)
            now = np.linalg.norm(got[b][:, 3, :3] - got[a][:, 3, :3], axis=1)
            self.assertLess(float(np.abs(now - was).max()), 1e-6, (a, b))

    def test_a_hand_past_the_arms_reach_is_clamped_on_its_line(self):
        side = sorted(self.chains)[0]
        up_j, _, hand_j = self.chains[side]
        want = np.array(self.kin[hand_j])
        want[:, 3, 0] += 500.0
        got = self.w._arm_to_hand(self.kin, self.n, self.chains, {side: want})
        low_j = self.chains[side][1]
        l1 = float(np.linalg.norm(self.w.lt[low_j].mean(axis=0)))
        l2 = float(np.linalg.norm(self.w.lt[hand_j].mean(axis=0)))
        reach = np.linalg.norm(got[hand_j][:, 3, :3] - got[up_j][:, 3, :3], axis=1)
        self.assertLess(float(np.abs(reach - (l1 + l2)).max()), 1e-6, "clamped at the arm's own length")
        for f in range(self.n):
            to_want = want[f, 3, :3] - got[up_j][f, 3, :3]
            to_got = got[hand_j][f, 3, :3] - got[up_j][f, 3, :3]
            cos = float(np.dot(to_want, to_got) / (np.linalg.norm(to_want) * np.linalg.norm(to_got)))
            self.assertGreater(cos, 1.0 - 1e-9, f)      # clamped along the line to the wanted hand

    def test_a_hint_bends_the_elbow_its_way_and_keeps_the_hand_and_the_bones(self):
        """Elbow overlap's road: the bend plane is sent somewhere else and nothing else gives."""
        side = sorted(self.chains)[0]
        up_j, low_j, hand_j = self.chains[side]
        hands = dict((s, np.array(self.kin[c[-1]])) for s, c in self.chains.items())
        hint = wm.late_bend(self.kin[up_j], self.kin[low_j], self.kin[hand_j], 2.0)
        got = self.w._arm_to_hand(self.kin, self.n, self.chains, hands, {side: hint})
        self.assertTrue(np.allclose(got[hand_j][:, 3, :3], hands[side][:, 3, :3], atol=1e-6))
        self.assertTrue(np.allclose(got[up_j][:, 3, :3], self.kin[up_j][:, 3, :3], atol=1e-9))
        for a, b in ((up_j, low_j), (low_j, hand_j)):
            was = np.linalg.norm(self.kin[b][:, 3, :3] - self.kin[a][:, 3, :3], axis=1)
            now = np.linalg.norm(got[b][:, 3, :3] - got[a][:, 3, :3], axis=1)
            self.assertLess(float(np.abs(now - was).max()), 1e-6, (a, b))
        self.assertGreater(float(np.abs(got[low_j][:, 3, :3] - self.kin[low_j][:, 3, :3]).max()), 1e-3,
                           "the elbow orbited")
        other = self.chains["r" if side == "l" else "l"]
        self.assertTrue(np.allclose(got[other[1]][:, 3, :3], self.kin[other[1]][:, 3, :3], atol=1e-6),
                        "the other side took no hint")

    def test_the_frames_own_hint_changes_nothing(self):
        hands = dict((s, np.array(self.kin[c[-1]])) for s, c in self.chains.items())
        plain = self.w._arm_to_hand(self.kin, self.n, self.chains, hands)
        hints = dict((s, wm.late_bend(self.kin[c[0]], self.kin[c[1]], self.kin[c[2]], 0.0))
                     for s, c in self.chains.items())
        same = self.w._arm_to_hand(self.kin, self.n, self.chains, hands, hints)
        for j in plain:
            self.assertTrue(np.allclose(plain[j], same[j], atol=1e-9), self.w.names[j])

    def test_the_springs_grip_still_reaches_its_hands(self):
        """_grip_motion keeps working through the shared rebuild: an arm drag with a grip runs and the bones
        keep their lengths (the grip itself is proven on the real cycle by verify_walk_arm_overlap.py)."""
        r = self.w.evaluate({"arm_drag": 2.0, "balance": 0.0})
        for side, chain in self.chains.items():
            for a, b in zip(chain, chain[1:]):
                d = np.linalg.norm(positions(r, self.w.names[b], self.w)
                                   - positions(r, self.w.names[a], self.w), axis=1)
                self.assertLess(float(np.ptp(d)), 1e-9, (side, a, b))


def body_frame(result, w, f):
    """The root's world matrix at frame f - the body's own space."""
    return result.worlds[w.index["root"], f]


def in_body(result, w, leaf, f):
    """A joint's place in the body's own space at frame f."""
    m = body_frame(result, w, f)
    return (result.worlds[w.index[leaf], f, 3, :3] - m[3, :3]) @ m[:3, :3].T


class OverlapPassTests(unittest.TestCase):
    """The pass itself on the synthetic walker (the grip is proven on the animator's cycle by the verify)."""

    def test_no_overlap_leaves_every_joint_untouched(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        same = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 0.0})
        self.assertTrue(np.array_equal(plain.worlds, same.worlds))
        self.assertEqual(same.info["arms"]["overlap"]["frames"], 0.0)

    def test_the_hand_walks_the_lag_0_path_that_many_frames_earlier(self):
        """The hand stands where the lag-0 hand stood two frames earlier (the travel out and back), clamped
        onto the arm's own reach: the direction from the shoulder is exact and the distance is the wanted one
        or the arm's length. The synthetic walker's arm hangs 98.6 .. 100.0 % extended, so a late hand asks
        for up to 58 cm of its 54 and the clamp bites on half the frames - the direction is what carries the
        promise, and it is exact."""
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        late = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 2.0})
        n = plain.frames
        self.assertEqual(late.info["arms"]["overlap"]["frames"], 2.0)
        self.assertFalse(late.info["arms"]["overlap"]["grip"])
        worst_dir, worst_reach, moved = 0.0, 0.0, 0.0
        for side in "lr":
            chain = w._arm_chains()[side]
            reach = sum(float(np.linalg.norm(w.lt[j].mean(axis=0))) for j in chain[1:])
            was_path = positions(plain, "hand_" + side, w)
            per = (was_path[n] - was_path[0]) / float(n)
            for f in range(n):
                early = (f - 2) % n
                want = was_path[early] - per * early + per * f
                sh = positions(late, "upperarm_" + side, w)[f]
                got = positions(late, "hand_" + side, w)[f]
                uw, ug = want - sh, got - sh
                rw, rg = float(np.linalg.norm(uw)), float(np.linalg.norm(ug))
                cos = float(np.dot(uw, ug) / (rw * rg))
                worst_dir = max(worst_dir, math.degrees(math.acos(min(1.0, max(-1.0, cos)))))
                worst_reach = max(worst_reach, abs(rg - min(rw, reach)))
                moved = max(moved, float(np.linalg.norm(got - was_path[f])))
        self.assertLess(worst_dir, 1e-4, "the late hand is on the line to where it stood two frames earlier")
        self.assertLess(worst_reach, 1e-6, "at the wanted distance, or at the arm's length where it clamps")
        self.assertGreater(moved, 1.0, "and it did move")

    def test_the_shoulder_does_not_move_and_the_bones_keep_their_lengths(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        late = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 3.0})
        for side in "lr":
            self.assertTrue(np.allclose(positions(late, "upperarm_" + side, w),
                                        positions(plain, "upperarm_" + side, w), atol=1e-9), side)
            for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_")):
                was = np.linalg.norm(positions(plain, b + side, w) - positions(plain, a + side, w), axis=1)
                now = np.linalg.norm(positions(late, b + side, w) - positions(late, a + side, w), axis=1)
                self.assertLess(float(np.abs(now - was).max()), 1e-6, (side, a, b))

    def test_the_cycle_is_still_a_loop(self):
        w = walk()
        r = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 2.5})
        moved = r.worlds[:, -1] - r.worlds[:, 0]
        self.assertLess(float(np.abs(moved[:, :3, :3]).max()), 1e-9)
        self.assertLess(float(np.abs(moved[:, 3, :3] - [0.0, 0.0, 120.0]).max()), 1e-6)

    def test_one_side_alone(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        late = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap_l": 3.0})
        self.assertGreater(float(np.abs(positions(late, "hand_l", w) - positions(plain, "hand_l", w)).max()), 1.0)
        self.assertTrue(np.allclose(positions(late, "hand_r", w), positions(plain, "hand_r", w), atol=1e-9))

    def test_a_lead_puts_the_hand_as_far_the_other_way(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        late = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 2.0})
        lead = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": -2.0})
        back = float(np.abs(positions(late, "hand_l", w) - positions(plain, "hand_l", w)).max())
        ahead = float(np.abs(positions(lead, "hand_l", w) - positions(plain, "hand_l", w)).max())
        self.assertAlmostEqual(back, ahead, delta=0.25 * back)

    def test_whip_takes_the_late_arm_as_its_target(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        lag = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 2.0})
        whip = w.evaluate({"arm_drag": 2.0, "arm_bounce": 0.0, "balance": 0.0})
        both = w.evaluate({"arm_drag": 2.0, "arm_bounce": 0.0, "balance": 0.0, "arm_overlap": 2.0})
        off = lambda r: float(np.abs(positions(r, "hand_l", w) - positions(plain, "hand_l", w)).max())
        self.assertGreater(off(both), off(lag))
        self.assertGreater(off(both), off(whip))

    def test_balance_sees_the_overlap_with_no_whip(self):
        """Balance swings the arms before it carries the body - with an overlap set and Arm drag 0 the arms
        still move, so the pass must run inside its rounds too (its `swinging`)."""
        w = walk()
        calls = []
        real = wm.Walk._arm_overlap

        def counted(self, worlds, n, ctx, only=None):
            calls.append(1)
            return real(self, worlds, n, ctx, only)
        wm.Walk._arm_overlap = counted
        try:
            w.evaluate({"arm_drag": 0.0, "balance": 1.0, "arm_overlap": 3.0})
        finally:
            wm.Walk._arm_overlap = real
        self.assertGreater(len(calls), 1, "the pass runs inside Balance's rounds and on the final frames")


class ParameterTests(unittest.TestCase):
    """Arm overlap as the animator's parameter: milliseconds in, frames of the new cycle out."""

    def setUp(self):
        self.w = walk()
        self.own = gait.own(self.w)

    def test_it_is_a_sided_arms_parameter_in_ms(self):
        """It lives with the other arm knobs, where an animator looks for it (2026-10-29: the animator turned
        Elbow lag / Hand lag / Arm out in the Arms tab and reported the feature dead, while the slider sat at
        0 in Main)."""
        p = gait.P["arm_overlap"]
        self.assertEqual((p.group, p.label, p.unit, p.kind, p.sided), (gait.ARMS, "Arm overlap", "ms",
                                                                       "added", True))
        self.assertIn("arm_overlap", gait.keys())
        self.assertIn("arm_overlap_l", gait.keys())
        names = [q.name for q in gait.PARAMS if q.group == gait.ARMS]
        self.assertEqual(names[names.index("arm_overlap") + 1], "elbow_lag")
        self.assertEqual(names[names.index("arm_overlap") - 1], "shoulders")
        self.assertNotIn("arm_overlap", [q.name for q in gait.PARAMS if q.group == gait.MAIN])

    def test_nothing_was_deleted(self):
        for name in ("arm_lag", "elbow_lag", "hand_lag", "elbow", "arms_forward", "shoulders"):
            self.assertIn(name, gait.P, name)

    def test_its_own_is_zero_and_the_slider_reaches_half_the_cycle(self):
        self.assertEqual(gait.own_value(self.own, "arm_overlap"), 0.0)
        self.assertEqual(gait.own_value(self.own, "arm_overlap_l"), 0.0)
        #  the synthetic walker: 24 frames at 24 fps, so half the cycle is 500 ms
        half = 1000.0 * self.w.P / self.w.fps / 2.0
        self.assertAlmostEqual(gait.overlap_cap(self.w), half, places=6)
        got = gait.ranges(self.own, self.w.leg_length, self.w)
        for key in ("arm_overlap", "arm_overlap_l", "arm_overlap_r"):
            self.assertEqual(got[key], (-half, half), key)
        #  without the walk the slider is the outer bound, and the engine's knob never clamps the cap
        self.assertEqual(gait.ranges(self.own, self.w.leg_length)["arm_overlap"],
                         (-gait.OVERLAP_MAX, gait.OVERLAP_MAX))
        for fps in (24.0, 30.0, 60.0):
            frames = gait.OVERLAP_MAX * fps / 1000.0
            self.assertLessEqual(frames, wm.RANGES["arm_overlap"][1], fps)

    def test_a_short_cycle_keeps_a_usable_slider(self):
        class Short(object):
            P, fps = 6, 30.0
        self.assertAlmostEqual(gait.overlap_cap(Short()), gait.OVERLAP_FLOOR, places=6)

    def test_a_long_cycle_is_capped_at_the_outer_bound(self):
        class Long(object):
            P, fps = 600, 30.0
        self.assertAlmostEqual(gait.overlap_cap(Long()), gait.OVERLAP_MAX, places=6)

    def test_an_offset_change_is_the_value_asked(self):
        vals = gait.values(self.own, {"arm_overlap": ("offset", 150.0)})
        self.assertAlmostEqual(vals["arm_overlap"], 150.0)
        self.assertAlmostEqual(vals["arm_overlap_l"], 150.0)
        self.assertAlmostEqual(vals["arm_overlap_r"], 150.0)
        self.assertEqual(gait.stored_change(gait.P["arm_overlap"], 0.0, 150.0), ("offset", 150.0))

    def test_ms_become_frames_at_the_output_rate(self):
        vals = gait.values(self.own, {"arm_overlap": ("offset", 150.0)})
        at30 = gait.engine_knobs(self.w, self.own, vals, fps_out=30.0)
        at24 = gait.engine_knobs(self.w, self.own, vals, fps_out=24.0)
        self.assertAlmostEqual(at30["arm_overlap_l"], 4.5, places=6)
        self.assertAlmostEqual(at30["arm_overlap_r"], 4.5, places=6)
        self.assertAlmostEqual(at24["arm_overlap_l"], 3.6, places=6)

    def test_with_no_rate_given_the_walks_own_is_used(self):
        vals = gait.values(self.own, {"arm_overlap": ("offset", 100.0)})
        e = gait.engine_knobs(self.w, self.own, vals)
        self.assertAlmostEqual(e["arm_overlap_l"], 100.0 * self.w.fps / 1000.0, places=6)

    def test_one_side_alone(self):
        vals = gait.values(self.own, {"arm_overlap_l": ("offset", 90.0)})
        e = gait.engine_knobs(self.w, self.own, vals, fps_out=30.0)
        self.assertAlmostEqual(e["arm_overlap_l"], 2.7, places=6)
        self.assertAlmostEqual(e["arm_overlap_r"], 0.0, places=6)

    def test_zero_asks_the_engine_for_nothing(self):
        e = gait.engine_knobs(self.w, self.own, gait.values(self.own, {}), fps_out=30.0)
        self.assertAlmostEqual(e.get("arm_overlap_l", 0.0), 0.0)
