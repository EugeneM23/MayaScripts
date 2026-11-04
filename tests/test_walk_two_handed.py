"""A two-handed hold is 2H, not the pose (2026-11-04).

The spec: docs/superpowers/specs/2026-11-04-walk-two-handed-not-the-pose-design.md. The animator: «Наши
ручки не должны зависит от позы» - a pose whose hands are apart must read as a two-handed one once 2H says
the hold is two-handed. The synthetic walker is tests.test_walkmodel's, as the one-arm tests use it.
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T
from tests.test_walk_one_arm import deg, local_of, prepared

wm = T.wm
wp = T.load("pose")

SWORD = {"grip": (2.0, -3.0, 1.0), "tip": (2.0, -3.0, 116.0)}      # the scene's weapon, in the hand's frame


def ctx_of(pose=None, alpha=1.0, weapons=None, **given):
    """The few fields held_together reads, as evaluate builds them."""
    k = wm.knobs(**given)
    return {"k": k, "ks": wm.sided(k), "pose": pose, "alpha": alpha, "weapons": dict(weapons or {})}


class RuleTests(unittest.TestCase):
    """held_together: who holds one thing, and which hand carries it."""

    def setUp(self):
        self.walk, self.raw = prepared()
        self.plain = wp.filtered(self.raw, wp.ALL_PARTS)                       # hands apart: no grip
        self.grip = wp.filtered(dict(self.raw, grip=True), wp.ALL_PARTS)
        self.assertFalse(self.plain["grip"], "the walker's own hands are apart - the dagger case")
        self.assertTrue(self.grip["grip"])

    def test_no_pose_and_no_weapon_hold_nothing(self):
        self.assertEqual(self.walk.held_together(ctx_of()), (set(), "r"))

    def test_a_pose_s_own_grip_holds_both_sides(self):
        sides, carrier = self.walk.held_together(ctx_of(self.grip))
        self.assertEqual(sides, {"l", "r"})
        self.assertEqual(carrier, "r", "a pose's grip is carried by the right hand, as it always was")

    def test_a_pose_whose_hands_are_apart_holds_nothing(self):
        self.assertEqual(self.walk.held_together(ctx_of(self.plain))[0], set())

    def test_one_arm_out_of_the_pose_leaves_the_other_holding(self):
        one = wp.filtered(dict(self.raw, grip=True), [p for p in wp.ALL_PARTS if p != "arm_l"])
        self.assertEqual(self.walk.held_together(ctx_of(one))[0], {"r"})

    def test_a_pose_from_before_the_sides_were_recorded_holds_both(self):
        old = dict(self.grip)
        old.pop("grip_sides", None)
        self.assertEqual(self.walk.held_together(ctx_of(old))[0], {"l", "r"})

    def test_2h_with_a_weapon_in_the_right_hand_holds_both(self):
        sides, carrier = self.walk.held_together(
            ctx_of(self.plain, weapons={"r": SWORD}, weapon_hold=1.0))
        self.assertEqual(sides, {"l", "r"}, "the hold the card declares, with no grip in the pose")
        self.assertEqual(carrier, "r")

    def test_2h_with_the_weapon_in_the_left_hand_is_carried_by_the_left(self):
        sides, carrier = self.walk.held_together(
            ctx_of(self.plain, weapons={"l": SWORD}, weapon_hold=1.0))
        self.assertEqual(sides, {"l", "r"})
        self.assertEqual(carrier, "l")

    def test_2h_with_no_weapon_in_the_scene_holds_nothing(self):
        self.assertEqual(self.walk.held_together(ctx_of(self.plain, weapon_hold=1.0))[0], set())

    def test_a_weapon_with_2h_off_holds_nothing(self):
        self.assertEqual(self.walk.held_together(ctx_of(self.plain, weapons={"r": SWORD}))[0], set())

    def test_a_weapon_in_each_hand_binds_nobody(self):
        """Neither hand is free, so there is nothing for 2H to bind - each holds its own."""
        sides = self.walk.held_together(
            ctx_of(self.plain, weapons={"l": SWORD, "r": SWORD}, weapon_hold=1.0))[0]
        self.assertEqual(sides, set())

    def test_2h_cannot_bind_an_arm_the_pose_s_chip_leaves_out(self):
        one = wp.filtered(self.raw, [p for p in wp.ALL_PARTS if p != "arm_l"])
        self.assertEqual(self.walk.held_together(
            ctx_of(one, weapons={"r": SWORD}, weapon_hold=1.0))[0], set())

    def test_2h_works_with_no_pose_at_all(self):
        """It is a knob, not a pose: a cycle with no pose carries a two-handed weapon as one body."""
        self.assertEqual(self.walk.held_together(
            ctx_of(None, weapons={"r": SWORD}, weapon_hold=1.0))[0], {"l", "r"})

    def test_a_pose_at_share_0_holds_nothing_but_2h_still_does(self):
        self.assertEqual(self.walk.held_together(ctx_of(self.grip, alpha=0.0))[0], set())
        self.assertEqual(self.walk.held_together(
            ctx_of(self.grip, alpha=0.0, weapons={"r": SWORD}, weapon_hold=1.0))[0], {"l", "r"})

    def test_evaluate_works_it_out_once(self):
        k = dict(KNOBS, weapon_hold=1.0)
        res = self.walk.evaluate(k, self.plain, weapons={"r": SWORD})
        self.assertTrue(res.info["arms"]["grip"], "the one-body spring is on under 2H")


KNOBS = {"pose": 1.0, "balance": 0.0, "torso_drag": 0.0, "head_drag": 0.0,
         "arm_overlap": 0.0, "elbow_overlap": 0.0, "hand_overlap": 0.0, "weapon_overlap": 0.0}
FRAMES = (0, 5, 11, 17)


class ModelTests(unittest.TestCase):
    """The two readers: the frame walk's stilling and the one-body spring. With every overlap knob at 0 the
    overlap pass does the same thing either way (2H's own binding of the free hand), so a pose whose hands
    are apart with 2H on must come out matrix for matrix as a two-handed pose with 2H on."""

    def setUp(self):
        self.walk, self.raw = prepared()
        self.plain = wp.filtered(self.raw, wp.ALL_PARTS)
        self.grip = wp.filtered(dict(self.raw, grip=True), wp.ALL_PARTS)
        self.held = {"r": SWORD}

    def run_it(self, pose, hold):
        return self.walk.evaluate(dict(KNOBS, weapon_hold=hold), pose, weapons=self.held)

    def fingers(self, side):
        return [j for j, kind in enumerate(self.walk.kind)
                if kind == "finger" and self.walk.names[j].endswith("_" + side)]

    def finger_turn(self, result, side):
        """The most any finger of that side turns on its own parent: the stilling's own measure."""
        out = 0.0
        for j in self.fingers(side):
            name = self.walk.names[j]
            for f in FRAMES[1:]:
                out = max(out, deg(local_of(result, name, self.walk, f)
                                   @ local_of(result, name, self.walk, 0).T))
        return out

    def test_2h_reads_exactly_as_a_two_handed_pose(self):
        """The headline: the same knobs, two poses, one answer."""
        apart = self.run_it(self.plain, 1.0)
        both = self.run_it(self.grip, 1.0)
        worst = float(np.max(np.abs(apart.worlds - both.worlds)))
        self.assertLess(worst, 1e-9, "worst matrix element %.3e" % worst)

    def test_and_the_control_is_the_same_pose_without_2h(self):
        apart = self.run_it(self.plain, 0.0)
        both = self.run_it(self.grip, 1.0)
        worst = float(np.max(np.abs(apart.worlds - both.worlds)))
        self.assertGreater(worst, 1e-3, "2H is what makes the difference, so without it they differ")

    def test_2h_stills_the_fingers(self):
        """The binding never touches a finger's own local, so this is the stilling alone."""
        if not self.fingers("r"):
            self.skipTest("the fixture has no fingers")
        loose = self.finger_turn(self.run_it(self.plain, 0.0), "r")
        held = self.finger_turn(self.run_it(self.plain, 1.0), "r")
        self.assertGreater(loose, 1.0, "the cycle does flex them")
        self.assertLess(held, 1e-6, "a hand holding a thing does not flex: %.4f deg" % held)

    def test_a_pose_grip_is_untouched_by_the_change(self):
        """With no weapon in the scene 2H binds nobody, so a two-handed pose reads as it always did."""
        a = self.walk.evaluate(dict(KNOBS, weapon_hold=1.0), self.grip)
        b = self.walk.evaluate(dict(KNOBS, weapon_hold=0.0), self.grip)
        self.assertTrue(np.array_equal(a.worlds, b.worlds))

    def test_the_one_body_spring_follows_the_knob(self):
        self.assertTrue(self.run_it(self.plain, 1.0).info["arms"]["grip"])
        self.assertFalse(self.run_it(self.plain, 0.0).info["arms"]["grip"])
        self.assertTrue(self.walk.evaluate(KNOBS, self.grip).info["arms"]["grip"])

    def test_a_weapon_in_the_left_hand_is_carried_by_the_left(self):
        """The carrier reaches _grip_motion: with the weapon on the left, the LEFT hand is the one whose own
        track the spring follows - the right keeps its hold on it."""
        seen = {}
        real = self.walk._grip_motion

        def spy(kin, n, chains, w0, zeta, S, hold_side="r"):
            seen["side"] = hold_side
            return real(kin, n, chains, w0, zeta, S, hold_side=hold_side)
        self.walk._grip_motion = spy
        try:
            self.walk.evaluate(dict(KNOBS, weapon_hold=1.0), self.plain, weapons={"l": SWORD})
        finally:
            del self.walk._grip_motion
        self.assertEqual(seen.get("side"), "l")

    def test_hands_still_scales_what_is_left(self):
        """The knobs built this morning are not replaced: at 0 % the fingers stand still either way."""
        if not self.fingers("r"):
            self.skipTest("the fixture has no fingers")
        r = self.walk.evaluate(dict(KNOBS, weapon_hold=0.0, hands=0.0), self.plain, weapons=self.held)
        self.assertLess(self.finger_turn(r, "r"), 1e-6)

    def test_the_arms_still_move_as_one_body(self):
        """Not a no-op: the spring under 2H is a different arm motion from two loose ones."""
        drag = dict(KNOBS, arm_drag=2.0)
        one = self.walk.evaluate(dict(drag, weapon_hold=1.0), self.plain, weapons=self.held)
        two = self.walk.evaluate(dict(drag, weapon_hold=1.0, arm_drag_l=2.0), self.plain)
        j = self.walk.index["hand_r"]
        apart = max(float(np.linalg.norm(one.worlds[j, f, 3, :3] - two.worlds[j, f, 3, :3]))
                    for f in range(self.walk.P))
        self.assertGreater(apart, 0.01, "the hand moves differently: %.4f cm" % apart)


class LineTests(unittest.TestCase):
    """What the status line says: the held weapon trails, as it does under a pose's own grip."""

    def test_the_line_names_the_held_weapon(self):
        walk, raw = prepared()
        plain = wp.filtered(raw, wp.ALL_PARTS)
        res = walk.evaluate(dict(KNOBS, weapon_hold=1.0, arm_drag=2.0), plain, weapons={"r": SWORD})
        self.assertIn("the held weapon trails", wm.describe(res))


if __name__ == "__main__":
    unittest.main()
