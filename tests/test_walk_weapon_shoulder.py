"""Walk Builder's Shoulder: the clavicle follows the hand, so the elbow is not overstretched (2026-11-10).

The animator, a walker on port 7005: «перерастягивается локоть при текущих настройках. Нужно сделать доводчик
плеча которые будет подкручивать плече что бы мы избавились от перерастяжения. Сделай пока ручку в weapon».
Hold / Overlap / Inherit / Aim target move the hand against the chest and the elbow alone paid for every
change of the arm's reach. Shoulder is the share of those changes the clavicle takes: 0 nothing, 1 all of
it - the arm keeps one reach and the elbow one bend.

The synthetic walker is tests.test_walkmodel's, under its two-handed pose (a_grip) with the hands read late
(Overlap), so the reach changes over the cycle and every gate below can fail.
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T

wm = T.wm
gait = T.load("gait")

KNOBS = {"pose": 1.0, "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0, "balance": 0.0, "in_place": 0.0,
         "weapon_overlap": 1.0, "weapon_overlap_l": 1.0, "weapon_overlap_r": 1.0}     # under the free turn


def run(walk, pose="grip", share=1.0, **over):
    ks = dict(KNOBS, pose=share)
    for name, value in over.items():              # a sided knob on both sides too (trap 317)
        ks[name] = value
        if name in wm.SIDED:
            ks[name + "_l"] = ks[name + "_r"] = value
    return walk.evaluate(ks, T.a_grip(walk) if pose == "grip" else pose)


def place(result, walk, name):
    return np.asarray(result.worlds[walk.index[name], :, 3, :3], float)


def reach(result, walk, side):
    """The shoulder-to-hand distance on every frame."""
    return np.linalg.norm(place(result, walk, "hand_" + side) - place(result, walk, "upperarm_" + side), axis=1)


def turned(a, b, walk, name):
    j = walk.index[name]
    return max(math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(a.worlds[j, f, :3, :3]).T
                                                           @ wm.orthonormal(b.worlds[j, f, :3, :3])))))
               for f in range(a.worlds.shape[1]))


class KnobTests(unittest.TestCase):

    def test_the_knob_is_declared_sided_at_zero(self):
        self.assertEqual(wm.DEFAULTS["weapon_shoulder"], 0.0)
        self.assertEqual(wm.RANGES["weapon_shoulder"], (0.0, 1.0))
        self.assertIn("weapon_shoulder", wm.SIDED)

    def test_zero_is_the_walk_itself_matrix_for_matrix(self):
        walk = T.walk()
        self.assertTrue(np.array_equal(run(walk).worlds, run(walk, weapon_shoulder=0.0).worlds))

    def test_the_reach_changes_at_all_on_this_fixture(self):
        walk = T.walk()
        for side in "lr":
            self.assertGreater(float(np.ptp(reach(run(walk), walk, side))), 0.3, side)


class ShoulderTests(unittest.TestCase):

    def setUp(self):
        self.walk = T.walk()
        self.base = run(self.walk)
        self.full = run(self.walk, weapon_shoulder=1.0)

    def test_at_one_the_arm_keeps_one_reach(self):
        for side in "lr":
            was, got = reach(self.base, self.walk, side), reach(self.full, self.walk, side)
            self.assertLess(float(np.ptp(got)), 1e-6, side)
            self.assertAlmostEqual(float(got[0]), float(was[:-1].mean()), places=6)     # ...the cycle's mean

    def test_a_half_leaves_half_of_the_change(self):
        half = run(self.walk, weapon_shoulder=0.5)
        for side in "lr":
            was, got = reach(self.base, self.walk, side), reach(half, self.walk, side)
            mean = float(was[:-1].mean())
            self.assertLess(float(np.abs((got - mean) - 0.5 * (was - mean)).max()), 1e-6, side)

    def test_the_hands_stay_where_the_tab_put_them(self):
        for side in "lr":
            j = self.walk.index["hand_" + side]
            self.assertLess(float(np.abs(self.full.worlds[j] - self.base.worlds[j]).max()), 1e-9, side)

    def test_the_clavicle_turns_about_its_own_pivot(self):
        for side in "lr":
            name = "clavicle_" + side
            self.assertLess(float(np.abs(place(self.full, self.walk, name) - place(self.base, self.walk, name)).max()),
                            1e-9, side)
            self.assertGreater(turned(self.base, self.full, self.walk, name), 0.5, side)

    def test_every_bone_keeps_its_length(self):
        for side in "lr":
            for a, b in (("clavicle_", "upperarm_"), ("upperarm_", "lowerarm_"), ("lowerarm_", "hand_"),
                         ("hand_", "index_01_")):
                d = np.linalg.norm(place(self.full, self.walk, b + side) - place(self.full, self.walk, a + side), axis=1)
                was = np.linalg.norm(place(self.base, self.walk, b + side) - place(self.base, self.walk, a + side), axis=1)
                self.assertLess(float(np.abs(d - was).max()), 1e-6, (side, a))

    def test_the_body_is_untouched(self):
        for name in ("pelvis", "spine_02", "neck_01", "head", "foot_l"):
            j = self.walk.index[name]
            self.assertTrue(np.array_equal(self.full.worlds[j], self.base.worlds[j]), name)

    def test_the_loop_closes(self):
        n = self.full.frames
        loop = (self.full.worlds[:, n] - self.full.worlds[:, 0]) - (self.base.worlds[:, n] - self.base.worlds[:, 0])
        self.assertLess(float(np.abs(loop).max()), 1e-9)

    def test_one_side_alone(self):
        got = self.walk.evaluate(dict(KNOBS, weapon_shoulder_l=1.0), T.a_grip(self.walk))
        self.assertLess(float(np.ptp(reach(got, self.walk, "l"))), 1e-6)
        for name in ("clavicle_r", "upperarm_r", "lowerarm_r", "hand_r"):
            j = self.walk.index[name]
            self.assertTrue(np.array_equal(got.worlds[j], self.base.worlds[j]), name)

    def test_it_needs_no_hold(self):
        base = run(self.walk, weapon_hold=0.0, arm_overlap=1.0)
        got = run(self.walk, weapon_hold=0.0, arm_overlap=1.0, weapon_shoulder=1.0)
        self.assertGreater(float(np.ptp(reach(base, self.walk, "r"))), 0.05)
        self.assertLess(float(np.ptp(reach(got, self.walk, "r"))), 1e-6)

    def test_the_pose_s_share_blends_it_in(self):
        base = run(self.walk, share=0.5)
        got = run(self.walk, share=0.5, weapon_shoulder=1.0)
        was, now = reach(base, self.walk, "r"), reach(got, self.walk, "r")
        mean = float(was[:-1].mean())
        self.assertLess(float(np.abs((now - mean) - 0.5 * (was - mean)).max()), 1e-6)

    def test_no_pose_nothing(self):
        base = run(self.walk, pose=None)
        self.assertTrue(np.array_equal(run(self.walk, pose=None, weapon_shoulder=1.0).worlds, base.worlds))

    def test_an_arm_out_of_the_pose_is_left_alone(self):
        pose = dict(T.a_grip(self.walk), grip=False, grip_sides=(), arm_sides=("r",))
        base = self.walk.evaluate(dict(KNOBS), pose)
        got = self.walk.evaluate(dict(KNOBS, weapon_shoulder=1.0, weapon_shoulder_l=1.0, weapon_shoulder_r=1.0), pose)
        for name in ("clavicle_l", "upperarm_l", "lowerarm_l", "hand_l"):
            j = self.walk.index[name]
            self.assertTrue(np.array_equal(got.worlds[j], base.worlds[j]), name)
        self.assertLess(float(np.ptp(reach(got, self.walk, "r"))), 1e-6)

    def test_the_clavicle_never_turns_past_its_limit(self):
        """A hand thrown far (a whole-cycle lag on a damped chest): the turn eases into the limit."""
        got = run(self.walk, weapon_overlap=9.0, weapon_inherit=0.0, weapon_shoulder=1.0)
        base = run(self.walk, weapon_overlap=9.0, weapon_inherit=0.0)
        for side in "lr":
            self.assertLessEqual(turned(base, got, self.walk, "clavicle_" + side), wm.SHOULDER_MAX_DEG + 1e-6)

    def test_the_info_carries_what_it_did(self):
        self.assertEqual(self.base.info["arms"]["overlap"]["shoulder"]["share"], {})
        did = self.full.info["arms"]["overlap"]["shoulder"]
        self.assertEqual(did["share"], {"l": 1.0, "r": 1.0})
        self.assertGreater(did["deg"], 0.5)
        for side in "lr":
            before, after = did["reach"][side]
            self.assertLess(after, before)


class GaitTests(unittest.TestCase):

    def setUp(self):
        self.walk = T.walk()
        self.own = gait.own(self.walk)

    def test_it_is_a_sided_share_of_the_weapon_tab_at_zero(self):
        p = gait.P["weapon_shoulder"]
        self.assertEqual(p.group, gait.WEAPON)
        self.assertEqual(p.label, "Shoulder")
        self.assertEqual(p.kind, "added")
        self.assertTrue(p.sided)
        self.assertEqual(p.default, 0.0)
        self.assertEqual(p.rule(0.0, 80.0), (0.0, 1.0))
        self.assertTrue(p.tip)

    def test_the_weapon_tab_s_order(self):
        names = [p.name for p in gait.PARAMS if p.group == gait.WEAPON]
        self.assertEqual(names, ["weapon_hold", "weapon_inherit", "weapon_overlap", "weapon_aim", "weapon_shoulder"])

    def test_its_own_value_is_zero(self):
        self.assertEqual(gait.own_value(self.own, "weapon_shoulder"), 0.0)
        rng = gait.ranges(self.own, 90.0, self.walk)
        for key in ("weapon_shoulder", "weapon_shoulder_l", "weapon_shoulder_r"):
            self.assertEqual(rng[key], (0.0, 1.0), key)

    def test_the_engine_takes_it_per_side(self):
        e = gait.engine_knobs(self.walk, self.own, dict(self.own, weapon_shoulder_r=0.75),
                              pins={"weapon_shoulder_r"}, physics=False)
        self.assertAlmostEqual(e["weapon_shoulder_r"], 0.75, places=9)
        self.assertAlmostEqual(e["weapon_shoulder_l"], 0.0, places=9)

    def test_the_own_knobs_change_nothing(self):
        e = gait.engine_knobs(self.walk, self.own, dict(self.own), pins=set(), physics=False)
        self.assertEqual(e["weapon_shoulder_l"], 0.0)
        self.assertEqual(e["weapon_shoulder_r"], 0.0)


class LineTests(unittest.TestCase):

    def test_the_default_says_nothing(self):
        self.assertNotIn("shoulder takes", wm.describe(run(T.walk())))

    def test_a_share_is_named(self):
        text = wm.describe(run(T.walk(), weapon_shoulder=0.5))
        self.assertIn("the shoulder takes 50 % of the arm's reach (the clavicle turns up to", text)
        self.assertIn("the arm stretched", text)


if __name__ == "__main__":
    unittest.main()
