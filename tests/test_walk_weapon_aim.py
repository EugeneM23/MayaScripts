"""Walk Builder's Aim target: the weapon's tip keeps less of the animation (2026-11-10).

The spec: docs/superpowers/specs/2026-11-10-walk-weapon-aim-target-design.md. The animator's example: the
weapon in Aim Mode with its aim target's keys thinned out, so the grip plays the whole run and the blade
points at a target that plays less of it. The knob: 1 the whole animation, 0 the target static.

The synthetic walker is tests.test_walkmodel's, under its two-handed pose (a_grip) with a blade in the
right hand: its chest turns and bobs, so the target the blade aims at moves and every gate below can fail.
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T

wm = T.wm
gait = T.load("gait")

GRIP = np.array([0.0, -2.0, 3.0])                 # in the right hand's own frame
TIP = np.array([0.0, -2.0, 103.0])                # a metre of blade along the hand's Z
HELD = {"r": {"grip": tuple(GRIP), "tip": tuple(TIP)}}
AIM = GRIP + (TIP - GRIP) * wm.AIM_REACH          # the aim target, past the tip as Aim Mode puts it
KNOBS = {"pose": 1.0, "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0, "balance": 0.0, "in_place": 0.0}


def place(local, mats):
    """A point of a joint's own frame in the world, per frame (row vectors)."""
    return np.array([np.asarray(local, float) @ m[:3, :3] + m[3, :3] for m in mats])


def run(walk, pose="grip", weapons=HELD, share=1.0, **over):
    ks = dict(KNOBS, pose=share)
    for name, value in over.items():              # a sided knob on both sides too (trap 317)
        ks[name] = value
        if name in wm.SIDED:
            ks[name + "_l"] = ks[name + "_r"] = value
    return walk.evaluate(ks, T.a_grip(walk) if pose == "grip" else pose, weapons=weapons)


def still(points):
    """A cycle of points with its linear travel out: (n, 3), the closing frame dropped."""
    n = len(points) - 1
    per = (points[n] - points[0]) / float(n)
    return np.array([points[f] - per * f for f in range(n)])


def hand(result, walk, side="r"):
    return np.asarray(result.worlds[walk.index["hand_" + side]], float)


def miss(mats, targets, grip=GRIP, aim=AIM):
    """How far the blade's own line passes from its target, the worst frame (cm): the blade runs from the
    grip through its aim point (both in the frame `mats` is, per frame), the target is a world point a
    frame. An aim constraint's promise - the target itself is not ON the blade's aim point, the grip being
    free to come nearer or go further."""
    G, P = place(grip, mats), place(aim, mats)
    worst = 0.0
    for f in range(len(mats)):
        u = (P[f] - G[f]) / np.linalg.norm(P[f] - G[f])
        to = targets[f] - G[f]
        if float(np.dot(to, u)) <= 0.0:
            return float("inf")
        worst = max(worst, float(np.linalg.norm(np.cross(u, to))))
    return worst


def target_of(base_mats, keep, aim=AIM):
    """The damped target a blade is promised to aim at: the base run's own aim point, keeping `keep`."""
    return wm.damped_points(place(aim, base_mats), keep)


class DampedPointsTests(unittest.TestCase):
    """model.damped_points: a cycle of points with its own motion scaled about its mean, the travel kept."""

    def cycle(self, n=12, travel=(0.0, 0.0, 60.0)):
        per = np.array(travel, float) / n
        return np.array([[5.0 * math.sin(2 * math.pi * (f % n) / n), 3.0 * math.cos(4 * math.pi * (f % n) / n),
                          2.0 * math.sin(6 * math.pi * (f % n) / n)] + per * f + np.array([7.0, 100.0, -4.0])
                         for f in range(n + 1)])

    def test_one_gives_the_input_back(self):
        pts = self.cycle()
        self.assertTrue(np.array_equal(wm.damped_points(pts, 1.0), pts))

    def test_zero_is_the_mean_riding_the_travel(self):
        pts = self.cycle()
        got = wm.damped_points(pts, 0.0)
        flat = still(got)
        self.assertLess(float(np.ptp(flat, axis=0).max()), 1e-12)
        self.assertTrue(np.allclose(flat[0], still(pts).mean(axis=0), atol=1e-12))

    def test_a_half_keeps_half_of_the_motion(self):
        pts = self.cycle()
        got, mean = still(wm.damped_points(pts, 0.5)), still(pts).mean(axis=0)
        self.assertTrue(np.allclose(got - mean, 0.5 * (still(pts) - mean), atol=1e-12))

    def test_the_result_is_a_cycle_again(self):
        pts = self.cycle()
        for k in (0.0, 0.3, 1.0):
            got = wm.damped_points(pts, k)
            self.assertTrue(np.allclose(got[-1] - got[0], pts[-1] - pts[0], atol=1e-12), k)


class KnobTests(unittest.TestCase):

    def test_the_knob_is_declared_sided_at_one(self):
        self.assertEqual(wm.DEFAULTS["weapon_aim"], 1.0)
        self.assertEqual(wm.RANGES["weapon_aim"], (0.0, 1.0))
        self.assertIn("weapon_aim", wm.SIDED)

    def test_one_is_the_walk_itself_matrix_for_matrix(self):
        walk = T.walk()
        self.assertTrue(np.array_equal(run(walk).worlds, run(walk, weapon_aim=1.0).worlds))

    def test_the_walker_s_target_moves_at_all(self):
        walk = T.walk()
        self.assertGreater(float(np.ptp(still(place(AIM, hand(run(walk), walk))), axis=0).max()), 2.0)


class AimTests(unittest.TestCase):
    """The pass on the walker: a two-handed pose, a blade in the right hand."""

    def setUp(self):
        self.walk = T.walk()
        self.base = run(self.walk)

    def test_zero_aims_at_a_target_standing_still_at_its_own_mean(self):
        target = target_of(hand(self.base, self.walk), 0.0)
        self.assertLess(float(np.ptp(still(target), axis=0).max()), 1e-9)          # it IS static
        self.assertGreater(miss(hand(self.base, self.walk), target), 1.0)          # the control
        self.assertLess(miss(hand(run(self.walk, weapon_aim=0.0), self.walk), target), 1e-6)

    def test_the_grip_plays_the_whole_animation(self):
        got = place(GRIP, hand(run(self.walk, weapon_aim=0.0), self.walk))
        was = place(GRIP, hand(self.base, self.walk))
        self.assertLess(float(np.abs(got - was).max()), 1e-6)

    def test_the_blade_turns_to_get_there(self):
        aimed = hand(run(self.walk, weapon_aim=0.0), self.walk)
        was = hand(self.base, self.walk)
        turn = max(math.degrees(float(np.linalg.norm(wm.log_rot(was[f, :3, :3].T @ aimed[f, :3, :3]))))
                   for f in range(len(was)))
        self.assertGreater(turn, 0.5)

    def test_a_half_keeps_half_of_the_target_s_motion(self):
        target = target_of(hand(self.base, self.walk), 0.5)
        self.assertGreater(miss(hand(self.base, self.walk), target), 0.5)
        self.assertLess(miss(hand(run(self.walk, weapon_aim=0.5), self.walk), target), 1e-6)

    def test_two_hands_keep_their_hold(self):
        aimed = run(self.walk, weapon_aim=0.0)
        for f in range(aimed.worlds.shape[1]):
            got = hand(aimed, self.walk, "l")[f] @ np.linalg.inv(hand(aimed, self.walk, "r")[f])
            was = hand(self.base, self.walk, "l")[f] @ np.linalg.inv(hand(self.base, self.walk, "r")[f])
            self.assertLess(float(np.abs(got - was).max()), 1e-6, f)

    def test_the_arms_keep_their_bones(self):
        aimed = run(self.walk, weapon_aim=0.0)
        for side in "lr":
            for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_")):
                d = np.linalg.norm(T.positions(aimed, b + side, self.walk) - T.positions(aimed, a + side, self.walk),
                                   axis=1)
                self.assertLess(float(np.ptp(d)), 1e-6, (side, a))

    def test_the_loop_closes(self):
        aimed = hand(run(self.walk, weapon_aim=0.0), self.walk)
        base = hand(self.base, self.walk)
        self.assertLess(float(np.abs((aimed[-1] - aimed[0]) - (base[-1] - base[0])).max()), 1e-6)

    def test_it_needs_no_hold(self):
        base = run(self.walk, weapon_hold=0.0)
        target = target_of(hand(base, self.walk), 0.0)
        self.assertGreater(miss(hand(base, self.walk), target), 1.0)
        self.assertLess(miss(hand(run(self.walk, weapon_hold=0.0, weapon_aim=0.0), self.walk), target), 1e-6)

    @unittest.skip("the old rule (no pose: nothing; the pose's share blends it in) reversed 2026-11-11 - to be rewritten")
    def test_the_pose_s_share_blends_it_in(self):
        """At half the pose's share a static target keeps half of its motion."""
        base = run(self.walk, share=0.5)
        target = target_of(hand(base, self.walk), 0.5)
        self.assertLess(miss(hand(run(self.walk, share=0.5, weapon_aim=0.0), self.walk), target), 1e-6)

    @unittest.skip("the old rule (no pose: nothing; the pose's share blends it in) reversed 2026-11-11 - to be rewritten")
    def test_no_pose_no_aim(self):
        base = run(self.walk, pose=None)
        self.assertTrue(np.array_equal(run(self.walk, pose=None, weapon_aim=0.0).worlds, base.worlds))

    def test_an_arm_out_of_the_pose_is_left_alone(self):
        pose = dict(T.a_grip(self.walk), arm_sides=["l"], grip=False, grip_sides=())
        base = run(self.walk, pose=pose)
        self.assertTrue(np.array_equal(run(self.walk, pose=pose, weapon_aim=0.0).worlds, base.worlds))

    def test_one_side_alone(self):
        """A one-handed pose, a blade in each hand: the side dialled is aimed, the other is not."""
        pose = dict(T.a_grip(self.walk), grip=False, grip_sides=())
        both = {"r": HELD["r"], "l": HELD["r"]}
        base = run(self.walk, pose=pose, weapons=both)
        ks = dict(KNOBS, weapon_aim_r=0.0)
        got = self.walk.evaluate(ks, pose, weapons=both)
        self.assertLess(miss(hand(got, self.walk, "r"), target_of(hand(base, self.walk, "r"), 0.0)), 1e-6)
        self.assertTrue(np.array_equal(hand(got, self.walk, "l"), hand(base, self.walk, "l")))


def with_weapon_bone(walk_clip):
    """The synthetic clip with a `weapon_r` riding hand_r rigidly: turned, a little off the hand."""
    names = list(walk_clip.names) + ["weapon_r"]
    hand_j = walk_clip.names.index("hand_r")
    parents = list(walk_clip.parents) + [hand_j]
    rel = T.mat(T.rot_x(20.0) @ T.rot_y(-35.0), [-6.0, 1.0, 2.0])
    extra = np.array([rel @ m for m in walk_clip.worlds[hand_j]])
    worlds = np.concatenate([walk_clip.worlds, extra[None]], axis=0)
    return wm.Clip(names, parents, worlds, fps=30.0, up=(0, 1, 0), name="synthetic"), rel


class LeverTests(unittest.TestCase):
    """With no weapon in the scene the right hand's weapon bone stands for one."""

    def test_the_weapon_bone_is_the_lever(self):
        clip, rel = with_weapon_bone(T.clip())
        walk = wm.analyse(clip)
        base = run(walk, weapons=None)
        aimed = run(walk, weapons=None, weapon_aim=0.0)
        bone = walk.index["weapon_r"]
        tip = np.array([0.0, 0.0, wm.AIM_BLADE * wm.AIM_REACH])     # along the bone's own Z
        target = target_of(base.worlds[bone], 0.0, aim=tip)
        self.assertGreater(miss(base.worlds[bone], target, grip=np.zeros(3), aim=tip), 1.0)
        self.assertLess(miss(aimed.worlds[bone], target, grip=np.zeros(3), aim=tip), 1e-6)
        self.assertLess(float(np.abs(aimed.worlds[bone][:, 3, :3] - base.worlds[bone][:, 3, :3]).max()), 1e-6)
        self.assertEqual(aimed.info["arms"]["overlap"]["aim"]["lever"], {"r": "bone"})

    def test_a_scene_weapon_wins_over_the_bone(self):
        clip, rel = with_weapon_bone(T.clip())
        walk = wm.analyse(clip)
        aimed = run(walk, weapon_aim=0.0)
        self.assertLess(miss(hand(aimed, walk), target_of(hand(run(walk), walk), 0.0)), 1e-6)
        self.assertEqual(aimed.info["arms"]["overlap"]["aim"]["lever"], {"r": "weapon"})

    def test_no_weapon_and_no_bone_is_nothing_to_aim(self):
        walk = T.walk()
        base = run(walk, weapons=None)
        aimed = run(walk, weapons=None, weapon_aim=0.0)
        self.assertTrue(np.array_equal(aimed.worlds, base.worlds))
        self.assertEqual(aimed.info["arms"]["overlap"]["aim"]["lever"], {})


class GaitTests(unittest.TestCase):
    """The card's parameter."""

    def setUp(self):
        self.walk = T.walk()
        self.own = gait.own(self.walk)

    def test_it_is_a_sided_share_of_the_weapon_tab_at_one(self):
        p = gait.P["weapon_aim"]
        self.assertEqual(p.group, gait.WEAPON)
        self.assertEqual(p.label, "Aim target")
        self.assertEqual(p.kind, "added")
        self.assertTrue(p.sided)
        self.assertEqual(p.default, 1.0)
        self.assertEqual(p.rule(0.0, 80.0), (0.0, 1.0))
        self.assertTrue(p.tip)

    def test_it_stands_after_overlap(self):
        names = [p.name for p in gait.PARAMS if p.group == gait.WEAPON]
        self.assertEqual(names[names.index("weapon_overlap"):][:2], ["weapon_overlap", "weapon_aim"])

    def test_its_own_value_is_one_and_its_range_zero_to_one(self):
        self.assertEqual(gait.own_value(self.own, "weapon_aim"), 1.0)
        rng = gait.ranges(self.own, 90.0, self.walk)
        for key in ("weapon_aim", "weapon_aim_l", "weapon_aim_r"):
            self.assertEqual(rng[key], (0.0, 1.0), key)

    def test_the_engine_takes_it_per_side(self):
        e = gait.engine_knobs(self.walk, self.own, dict(self.own, weapon_aim_r=0.25), pins={"weapon_aim_r"},
                              physics=False)
        self.assertAlmostEqual(e["weapon_aim_r"], 0.25, places=9)
        self.assertAlmostEqual(e["weapon_aim_l"], 1.0, places=9)

    def test_the_card_s_road_reaches_the_blade(self):
        asked = dict(self.own, weapon_aim=0.0, weapon_aim_l=0.0, weapon_aim_r=0.0)
        e = gait.engine_knobs(self.walk, self.own, asked, pins={"weapon_aim"}, physics=False)
        knobs = dict(e, pose=1.0, in_place=0.0)
        got = self.walk.evaluate(knobs, T.a_grip(self.walk), weapons=HELD)
        base = self.walk.evaluate(dict(knobs, weapon_aim=1.0, weapon_aim_l=1.0, weapon_aim_r=1.0),
                                  T.a_grip(self.walk), weapons=HELD)
        target = target_of(hand(base, self.walk), 0.0)
        self.assertGreater(miss(hand(base, self.walk), target), 1.0)
        self.assertLess(miss(hand(got, self.walk), target), 1e-6)


class LineTests(unittest.TestCase):

    def setUp(self):
        self.walk = T.walk()

    def test_the_default_says_nothing(self):
        self.assertNotIn("aims at", wm.describe(run(self.walk)))

    def test_an_aimed_blade_is_named_with_its_share(self):
        text = wm.describe(run(self.walk, weapon_aim=0.3))
        self.assertIn("the blade aims at a target keeping 30 % of its motion", text)
        self.assertIn("swung up to", text)

    def test_a_static_target_is_named_so(self):
        self.assertIn("the blade aims at a static target", wm.describe(run(self.walk, weapon_aim=0.0)))

    def test_no_lever_is_said(self):
        text = wm.describe(run(self.walk, weapons=None, weapon_aim=0.0))
        self.assertIn("no weapon in the hand and no weapon bone: Aim target does nothing", text)


if __name__ == "__main__":
    unittest.main()
