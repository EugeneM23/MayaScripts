"""Walk Builder's Arm overlap: the time shift, the IK rebuild it feeds, and the pass on the cycle."""

import math
import unittest

import numpy as np

from tests.test_walkmodel import positions, rot_y, walk, wm


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


class KnobTests(unittest.TestCase):

    def test_the_engine_carries_a_sided_arm_overlap_knob(self):
        self.assertEqual(wm.DEFAULTS["arm_overlap"], 0.0)
        self.assertEqual(wm.RANGES["arm_overlap"], (-20.0, 60.0))
        self.assertIn("arm_overlap", wm.SIDED)
        self.assertEqual(wm.SIDE_KNOBS["arm_overlap_l"], "arm_overlap")
        self.assertIn("arm_overlap", wm.ENGINE_ONLY)
        k = wm.knobs(arm_overlap_l=3.0)
        self.assertEqual(wm.sided(k)["l"]["arm_overlap"], 3.0)
        self.assertEqual(wm.sided(k)["r"]["arm_overlap"], 0.0)


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

    def test_the_springs_grip_still_reaches_its_hands(self):
        """_grip_motion keeps working through the shared rebuild: an arm drag with a grip runs and the bones
        keep their lengths (the grip itself is proven on the real cycle by verify_walk_arm_overlap.py)."""
        r = self.w.evaluate({"arm_drag": 2.0, "balance": 0.0})
        for side, chain in self.chains.items():
            for a, b in zip(chain, chain[1:]):
                d = np.linalg.norm(positions(r, self.w.names[b], self.w)
                                   - positions(r, self.w.names[a], self.w), axis=1)
                self.assertLess(float(np.ptp(d)), 1e-9, (side, a, b))
