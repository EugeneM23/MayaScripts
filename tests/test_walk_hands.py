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
