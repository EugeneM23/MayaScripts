"""Walk Builder's Inherit: how much of the chest's motion a held hand takes (2026-11-10).

The spec: docs/superpowers/specs/2026-11-10-walk-weapon-hold-inherit-design.md. The animator: «ручку которая
будет контролировать процент холда 1 - 100% наследования как сейчас 0 - 0 процентов полная статика». Hold
parents the hand to the chest; Inherit is that parent's weight - 1 rides the chest as it does today, 0
stands still in the frame the cycle travels in.

The synthetic walker is tests.test_walkmodel's, under its two-handed pose (a_grip): its chest turns and
bobs, so a hand riding it moves and every gate below can fail.
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T

wm = T.wm
gait = T.load("gait")

KNOBS = {"pose": 1.0, "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0, "balance": 0.0, "in_place": 0.0}


def run(walk, pose="grip", share=1.0, **over):
    ks = dict(KNOBS, pose=share)
    for name, value in over.items():              # a sided knob on both sides too (trap 317)
        ks[name] = value
        if name in wm.SIDED:
            ks[name + "_l"] = ks[name + "_r"] = value
    return walk.evaluate(ks, T.a_grip(walk) if pose == "grip" else pose)


def hand(result, walk, side="r"):
    return np.asarray(result.worlds[walk.index["hand_" + side]], float)


def chest(result, walk):
    return np.asarray(result.worlds[walk._chest_joint()], float)


def promised(walk, base, keep, lag=0.0, side="r"):
    """What Inherit promises the hand: its own constant offset from the chest (read off the run at 1, where
    the hand rides the chest rigidly) on the chest's cycle keeping `keep` of its motion, `lag` frames old."""
    C = chest(base, walk)
    H = hand(base, walk, side)
    offset = H[0] @ np.linalg.inv(C[0])
    carrier = wm.shifted_cycle(walk.steady_chest(C, keep, keep), lag)
    return np.array([offset @ carrier[f] for f in range(len(C))])


def wander(mats):
    """How far a cycle of matrices moves with its linear travel out: (cm, deg), the worst frame against the
    first."""
    n = len(mats) - 1
    per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
    cm = max(float(np.linalg.norm((mats[f, 3, :3] - per * f) - mats[0, 3, :3])) for f in range(n + 1))
    deg = max(math.degrees(float(np.linalg.norm(wm.log_rot(mats[0, :3, :3].T @ mats[f, :3, :3]))))
              for f in range(n + 1))
    return cm, deg


class KnobTests(unittest.TestCase):

    def test_the_knob_is_declared_sided_at_one(self):
        self.assertEqual(wm.DEFAULTS["weapon_inherit"], 1.0)
        self.assertEqual(wm.RANGES["weapon_inherit"], (0.0, 1.0))
        self.assertIn("weapon_inherit", wm.SIDED)

    def test_one_is_the_walk_itself_matrix_for_matrix(self):
        walk = T.walk()
        self.assertTrue(np.array_equal(run(walk).worlds, run(walk, weapon_inherit=1.0).worlds))

    def test_the_held_hand_moves_with_the_chest_at_all(self):
        walk = T.walk()
        cm, deg = wander(hand(run(walk), walk))
        self.assertGreater(cm, 1.0)
        self.assertGreater(deg, 1.0)


class InheritTests(unittest.TestCase):

    def setUp(self):
        self.walk = T.walk()
        self.base = run(self.walk)

    def test_at_one_the_hand_rides_the_chest_rigidly(self):
        """The fixture's own ground: the offset read at frame 0 holds on every frame."""
        want = promised(self.walk, self.base, 1.0)
        self.assertLess(float(np.abs(hand(self.base, self.walk) - want).max()), 1e-6)

    def test_zero_is_full_statics(self):
        got = hand(run(self.walk, weapon_inherit=0.0), self.walk)
        cm, deg = wander(got)
        self.assertLess(cm, 1e-6)
        self.assertLess(deg, 1e-6)

    def test_zero_stands_at_the_hand_s_place_on_the_chest_s_mean(self):
        got = hand(run(self.walk, weapon_inherit=0.0), self.walk)
        self.assertLess(float(np.abs(got - promised(self.walk, self.base, 0.0)).max()), 1e-6)

    def test_a_half_takes_half_of_the_chest_s_motion(self):
        got = hand(run(self.walk, weapon_inherit=0.5), self.walk)
        self.assertLess(float(np.abs(got - promised(self.walk, self.base, 0.5)).max()), 1e-6)
        cm, deg = wander(got)
        full = wander(hand(self.base, self.walk))
        self.assertLess(cm, full[0])
        self.assertGreater(cm, 0.1 * full[0])

    def test_overlap_reads_that_chest_late(self):
        base = run(self.walk, weapon_overlap=3.0)
        got = hand(run(self.walk, weapon_overlap=3.0, weapon_inherit=0.5), self.walk)
        self.assertLess(float(np.abs(got - promised(self.walk, self.base, 0.5, lag=3.0)).max()), 1e-6)
        self.assertGreater(float(np.abs(got - hand(base, self.walk)).max()), 0.1)

    def test_two_hands_keep_their_hold(self):
        still = run(self.walk, weapon_inherit=0.0)
        for f in range(still.worlds.shape[1]):
            got = hand(still, self.walk, "l")[f] @ np.linalg.inv(hand(still, self.walk, "r")[f])
            was = hand(self.base, self.walk, "l")[f] @ np.linalg.inv(hand(self.base, self.walk, "r")[f])
            self.assertLess(float(np.abs(got - was).max()), 1e-6, f)

    def test_the_arms_keep_their_bones(self):
        still = run(self.walk, weapon_inherit=0.0)
        for side in "lr":
            for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_")):
                d = np.linalg.norm(T.positions(still, b + side, self.walk) - T.positions(still, a + side, self.walk),
                                   axis=1)
                self.assertLess(float(np.ptp(d)), 1e-6, (side, a))

    def test_the_body_is_untouched(self):
        still = run(self.walk, weapon_inherit=0.0)
        for name in ("pelvis", "spine_02", "head", "foot_l", "clavicle_r"):
            j = self.walk.index[name]
            self.assertTrue(np.array_equal(still.worlds[j], self.base.worlds[j]), name)

    def test_one_side_alone(self):
        """A one-handed pose: the side dialled stands still, the other rides the chest as before."""
        pose = dict(T.a_grip(self.walk), grip=False, grip_sides=())
        base = self.walk.evaluate(dict(KNOBS), pose)
        got = self.walk.evaluate(dict(KNOBS, weapon_inherit_r=0.0), pose)
        cm, deg = wander(hand(got, self.walk, "r"))
        self.assertLess(max(cm, deg), 1e-6)
        self.assertTrue(np.array_equal(hand(got, self.walk, "l"), hand(base, self.walk, "l")))

    def test_hold_off_inherit_does_nothing(self):
        base = run(self.walk, weapon_hold=0.0)
        self.assertTrue(np.array_equal(run(self.walk, weapon_hold=0.0, weapon_inherit=0.0).worlds, base.worlds))

    def test_no_pose_nothing(self):
        base = run(self.walk, pose=None)
        self.assertTrue(np.array_equal(run(self.walk, pose=None, weapon_inherit=0.0).worlds, base.worlds))

    def test_the_info_carries_the_share(self):
        self.assertEqual(self.base.info["arms"]["overlap"]["inherit"], 1.0)
        self.assertEqual(run(self.walk, weapon_inherit=0.25).info["arms"]["overlap"]["inherit"], 0.25)


class GaitTests(unittest.TestCase):

    def setUp(self):
        self.walk = T.walk()
        self.own = gait.own(self.walk)

    def test_it_is_a_sided_share_of_the_weapon_tab_at_one(self):
        p = gait.P["weapon_inherit"]
        self.assertEqual(p.group, gait.WEAPON)
        self.assertEqual(p.label, "Inherit")
        self.assertEqual(p.kind, "added")
        self.assertTrue(p.sided)
        self.assertEqual(p.default, 1.0)
        self.assertEqual(p.rule(0.0, 80.0), (0.0, 1.0))
        self.assertTrue(p.tip)

    def test_the_weapon_tab_s_order(self):
        names = [p.name for p in gait.PARAMS if p.group == gait.WEAPON]
        self.assertEqual(names, ["weapon_hold", "weapon_inherit", "weapon_overlap", "weapon_aim"])

    def test_its_own_value_is_one_and_its_range_zero_to_one(self):
        self.assertEqual(gait.own_value(self.own, "weapon_inherit"), 1.0)
        rng = gait.ranges(self.own, 90.0, self.walk)
        for key in ("weapon_inherit", "weapon_inherit_l", "weapon_inherit_r"):
            self.assertEqual(rng[key], (0.0, 1.0), key)

    def test_the_engine_takes_it_per_side(self):
        e = gait.engine_knobs(self.walk, self.own, dict(self.own, weapon_inherit_r=0.25),
                              pins={"weapon_inherit_r"}, physics=False)
        self.assertAlmostEqual(e["weapon_inherit_r"], 0.25, places=9)
        self.assertAlmostEqual(e["weapon_inherit_l"], 1.0, places=9)

    def test_the_card_s_road_stills_the_hand(self):
        asked = dict(self.own, weapon_inherit=0.0, weapon_inherit_l=0.0, weapon_inherit_r=0.0)
        e = gait.engine_knobs(self.walk, self.own, asked, pins={"weapon_inherit"}, physics=False)
        got = self.walk.evaluate(dict(e, pose=1.0, in_place=0.0), T.a_grip(self.walk))
        cm, deg = wander(hand(got, self.walk))
        self.assertLess(max(cm, deg), 1e-6)


class LineTests(unittest.TestCase):

    def setUp(self):
        self.walk = T.walk()

    def test_the_default_says_what_it_said(self):
        text = wm.describe(run(self.walk))
        self.assertIn("both hands ride the chest", text)
        self.assertNotIn("of its motion", text)
        self.assertNotIn("stand still", text)

    def test_a_share_is_named(self):
        self.assertIn("both hands ride the chest at 30 % of its motion",
                      wm.describe(run(self.walk, weapon_inherit=0.3)))

    def test_zero_is_named_as_standing_still(self):
        text = wm.describe(run(self.walk, weapon_inherit=0.0))
        self.assertIn("both hands stand still: none of the chest's motion", text)
        self.assertNotIn("ride the chest", text)


if __name__ == "__main__":
    unittest.main()
