"""Walk Builder's Arms % and Hands %: each part's share of the cycle's own animation (2026-11-04).

The spec: docs/superpowers/specs/2026-11-04-walk-hands-from-the-cycle-design.md. The synthetic walker is
tests.test_walkmodel's: its upper arm turns 25.000 deg on its own, its forearm 8.000, its hand 5.000 and
its one finger 5.000, so every gate below can fail.
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T

wm = T.wm
gait = T.load("gait")


def own_turn(result, walk, name):
    """A joint's own local rotation over the cycle (deg, the most it stands off its mean).

    Row vectors: the local is w[j] @ w[parent].T, never the other way round (trap 225) - written
    backwards a constant local on a moving parent reads as degrees of motion that are not there."""
    j = walk.index[name]
    p = walk.parents[j]
    R = result.worlds[:, :, :3, :3]
    rots = [wm.orthonormal(R[j, f]) @ wm.orthonormal(R[p, f]).T
            for f in range(result.worlds.shape[1])]
    mean = wm.orthonormal(np.mean(rots, axis=0))
    return max(math.degrees(float(np.linalg.norm(wm.log_rot(mean.T @ r)))) for r in rots)


def world_turn(result, walk, name):
    """A joint's WORLD rotation over the cycle (deg off its mean).

    The frame the upper arm must be judged in with no pose: it is world-held by design ("the upper arm
    hangs and swings in the world"), so Arms 0 % freezes its world rotation (measured: 27.119 -> 0.000
    deg) while its LOCAL still reads the clavicle's own motion under it (4.837 deg)."""
    j = walk.index[name]
    R = result.worlds[:, :, :3, :3]
    rots = [wm.orthonormal(R[j, f]) for f in range(result.worlds.shape[1])]
    mean = wm.orthonormal(np.mean(rots, axis=0))
    return max(math.degrees(float(np.linalg.norm(wm.log_rot(mean.T @ r)))) for r in rots)


def run(walk, **over):
    """The walker's own cycle with `over` on top, travelling (In place off, so nothing hides a turn)."""
    return walk.evaluate(dict(walk.own_knobs(), in_place=0.0, **over), None)


class KnobTests(unittest.TestCase):
    """The engine knob itself."""

    def test_the_hands_knob_is_declared_sided_at_one(self):
        self.assertEqual(wm.DEFAULTS["hands"], 1.0)
        self.assertEqual(wm.RANGES["hands"], (0.0, 3.0))
        self.assertIn("hands", wm.SIDED)
        self.assertEqual(wm.SIDE_KNOBS["hands_l"], "hands")
        self.assertEqual(wm.SIDE_KNOBS["hands_r"], "hands")

    def test_it_is_not_a_legacy_knob_and_not_an_aspect(self):
        self.assertNotIn("hands", wm.LEGACY)
        self.assertNotIn("hands", wm.ASPECT_KNOBS)

    def test_the_hand_bones_are_found(self):
        walk = T.walk()
        self.assertEqual(sorted(walk.names[j] for j in walk.hand_bones), ["hand_l", "hand_r"])

    def test_its_own_value_changes_nothing_matrix_for_matrix(self):
        walk = T.walk()
        plain = run(walk)
        same = run(walk, hands=1.0, hands_l=1.0, hands_r=1.0)
        self.assertTrue(np.array_equal(plain.worlds, same.worlds))


class HandsTests(unittest.TestCase):
    """Hands %: the hand bone and every finger, per side."""

    def setUp(self):
        self.walk = T.walk()
        self.plain = run(self.walk)

    def test_the_walker_s_hand_and_finger_move_at_all(self):
        self.assertAlmostEqual(own_turn(self.plain, self.walk, "hand_l"), 5.0, delta=0.5)
        self.assertAlmostEqual(own_turn(self.plain, self.walk, "index_01_l"), 5.0, delta=0.5)

    def test_zero_stills_the_hand_and_its_finger(self):
        res = run(self.walk, hands=0.0, hands_l=0.0, hands_r=0.0)
        for name in ("hand_l", "index_01_l", "hand_r", "index_01_r"):
            self.assertLess(own_turn(res, self.walk, name), 1e-6, msg=name)

    def test_one_side_alone_leaves_the_other_untouched(self):
        res = run(self.walk, hands_l=0.0)
        self.assertLess(own_turn(res, self.walk, "hand_l"), 1e-6)
        self.assertLess(own_turn(res, self.walk, "index_01_l"), 1e-6)
        self.assertAlmostEqual(own_turn(res, self.walk, "hand_r"),
                               own_turn(self.plain, self.walk, "hand_r"), places=6)
        self.assertAlmostEqual(own_turn(res, self.walk, "index_01_r"),
                               own_turn(self.plain, self.walk, "index_01_r"), places=6)

    def test_half_keeps_half_of_the_finger_s_turn(self):
        res = run(self.walk, hands=0.5, hands_l=0.5, hands_r=0.5)
        self.assertAlmostEqual(own_turn(res, self.walk, "index_01_l"),
                               0.5 * own_turn(self.plain, self.walk, "index_01_l"), delta=0.05)

    def test_it_leaves_the_upper_arm_and_the_forearm_alone(self):
        res = run(self.walk, hands=0.0, hands_l=0.0, hands_r=0.0)
        for name in ("upperarm_l", "lowerarm_l", "upperarm_r", "lowerarm_r"):
            self.assertAlmostEqual(own_turn(res, self.walk, name),
                                   own_turn(self.plain, self.walk, name), places=6, msg=name)


class ArmsTests(unittest.TestCase):
    """Arms %: the knob that was already there, and what it reaches."""

    def setUp(self):
        self.walk = T.walk()
        self.plain = run(self.walk)

    def test_zero_stills_the_upper_arm_in_the_world_and_the_forearm_in_its_parent(self):
        res = run(self.walk, arms=0.0, arms_l=0.0, arms_r=0.0)
        for name in ("upperarm_l", "upperarm_r"):       # world-held with no pose: see world_turn
            self.assertLess(world_turn(res, self.walk, name), 1e-6, msg=name)
        for name in ("clavicle_l", "lowerarm_l", "clavicle_r", "lowerarm_r"):
            self.assertLess(own_turn(res, self.walk, name), 1e-6, msg=name)

    def test_it_reaches_the_hand_bone_but_not_the_fingers(self):
        res = run(self.walk, arms=0.0, arms_l=0.0, arms_r=0.0)
        self.assertLess(own_turn(res, self.walk, "hand_l"), 1e-6)
        self.assertAlmostEqual(own_turn(res, self.walk, "index_01_l"),
                               own_turn(self.plain, self.walk, "index_01_l"), places=6)

    def test_one_side_alone_leaves_the_other_untouched(self):
        res = run(self.walk, arms_l=0.0)
        self.assertLess(world_turn(res, self.walk, "upperarm_l"), 1e-6)
        self.assertAlmostEqual(world_turn(res, self.walk, "upperarm_r"),
                               world_turn(self.plain, self.walk, "upperarm_r"), places=6)


class ParamTests(unittest.TestCase):
    """The card's two parameters and their mapping onto the engine."""

    def setUp(self):
        self.walk = T.walk()
        self.own = gait.own(self.walk)

    def param(self, name):
        return dict((p.name, p) for p in gait.PARAMS)[name]

    def test_both_are_a_percent_added_sided_at_a_hundred(self):
        for name, label in (("arms", "Arms"), ("hands", "Hands")):
            p = self.param(name)
            self.assertEqual(p.group, gait.ARMS, msg=name)
            self.assertEqual(p.label, label)
            self.assertEqual(p.unit, "%", msg=name)
            self.assertEqual(p.kind, "added", msg=name)
            self.assertTrue(p.sided, msg=name)
            self.assertEqual(p.default, 100.0, msg=name)
            self.assertEqual(p.rule(0.0, 80.0), (0.0, 100.0), msg=name)
            self.assertTrue(p.tip, msg=name)

    def test_they_come_first_in_the_arms_group(self):
        names = [p.name for p in gait.PARAMS if p.group == gait.ARMS]
        self.assertEqual(names[:2], ["arms", "hands"])

    def test_their_own_value_is_a_hundred(self):
        #  gait.own() carries no "added" parameter at all (detail, arm_drag and arm_overlap are all
        #  absent from it); own_value falls back to the Param's default, which is what engine_knobs
        #  reads. So ask own_value, never own[...] - that would KeyError.
        for name in ("arms", "hands"):
            self.assertEqual(gait.own_value(self.own, name), 100.0, msg=name)
            for side in ("l", "r"):
                self.assertEqual(gait.own_value(self.own, name + "_" + side), 100.0, msg=name + side)

    def test_a_legacy_memo_s_engine_arms_still_becomes_an_arm_swing_ratio(self):
        """from_legacy is deliberately unchanged: a pre-2026-10-26 memo's `arms` is an Arm swing ratio,
        not the new Arms % parameter (the spec's reason - every walker it concerns was translated in
        October, and changing it would move them)."""
        changes, pins, macros = gait.from_legacy(self.walk, {"arms": 0.5})   # it returns a 3-tuple
        self.assertEqual(changes.get("arm_swing"), ("ratio", 0.5))
        self.assertNotIn("arms", changes)
        self.assertIn("arm_swing", pins)

    def test_the_own_values_write_no_engine_knob(self):
        e = gait.engine_knobs(self.walk, self.own, self.own, pins=set(), physics=False)
        for key in ("arms", "arms_l", "arms_r", "hands", "hands_l", "hands_r"):
            self.assertNotIn(key, e, msg=key)

    def test_a_percent_becomes_a_share_on_both_sides(self):
        asked = dict(self.own, arms=25.0, arms_l=25.0, arms_r=25.0,
                     hands=0.0, hands_l=0.0, hands_r=0.0)
        e = gait.engine_knobs(self.walk, self.own, asked, pins={"arms", "hands"}, physics=False)
        self.assertAlmostEqual(e["arms_l"], 0.25, places=9)
        self.assertAlmostEqual(e["arms_r"], 0.25, places=9)
        self.assertAlmostEqual(e["hands_l"], 0.0, places=9)
        self.assertAlmostEqual(e["hands_r"], 0.0, places=9)

    def test_one_side_asked_leaves_the_other_at_its_own(self):
        asked = dict(self.own, hands_l=0.0)
        e = gait.engine_knobs(self.walk, self.own, asked, pins={"hands_l"}, physics=False)
        self.assertAlmostEqual(e["hands_l"], 0.0, places=9)
        self.assertNotIn("hands_r", e)

    def test_the_card_s_road_stills_the_fingers(self):
        """The whole way through: a percent asked of the parameter layer reaches the frame walk."""
        asked = dict(self.own, hands=0.0, hands_l=0.0, hands_r=0.0)
        e = gait.engine_knobs(self.walk, self.own, asked, pins={"hands"}, physics=False)
        res = self.walk.evaluate(dict(e, in_place=0.0), None)
        self.assertLess(own_turn(res, self.walk, "index_01_l"), 1e-6)
        self.assertLess(own_turn(res, self.walk, "index_01_r"), 1e-6)
