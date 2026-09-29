"""Two hands (2026-09-29): which bone a hand drives, the left grip as the
mirror of the right through the rig's own sockets, the grip remembered per
hand, and the Weapons section's `Hand [Right | Left]`.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import math
import random
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import bonedrive
from maya_scenesetup import catalog

MX = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
MZ = om.MMatrix(bonedrive.MODEL_MIRROR)
F = om.MMatrix(bonedrive.BEHAVIOUR_MIRROR)


def m(rotate, translate):
    return om.MMatrix(bonedrive.matrix_of(rotate, translate))


def close(a, b, tol=1e-9):
    return max(abs(x - y) for x, y in zip(a, b)) <= tol


class SideBone(unittest.TestCase):

    def test_the_right_hand_keeps_the_rows_bone(self):
        self.assertEqual(catalog.side_bone("weapon_r", "R"), "weapon_r")

    def test_the_left_hand_takes_the_twin(self):
        self.assertEqual(catalog.side_bone("weapon_r", "L"), "weapon_l")

    def test_a_left_row_answers_its_right_twin(self):
        self.assertEqual(catalog.side_bone("weapon_l", "R"), "weapon_r")

    def test_a_bone_without_a_side_is_its_own_twin(self):
        self.assertEqual(catalog.side_bone("prop", "L"), "prop")

    def test_the_sides(self):
        self.assertEqual(catalog.SIDES, ("R", "L"))


class MirrorGrip(unittest.TestCase):
    """G_l . Fr . B_l == Mz . G_r . Fr . B_r . Mx for behaviour-mirrored
    hands, whatever the sockets are."""

    def _check(self, rotate, translate, frame_rotate, s_r, s_l):
        hand_r = m((-67.77, 1.47, 1.85), (-47.77, 104.47, 15.70))
        hand_l = F * hand_r * MX
        left = bonedrive.mirror_grip(rotate, translate, frame_rotate,
                                     tuple(s_r), tuple(s_l))
        fr = m(frame_rotate, (0, 0, 0))
        w_r = m(rotate, translate) * fr * s_r * hand_r
        w_l = m(*left) * fr * s_l * hand_l
        self.assertTrue(close(w_l, MZ * w_r * MX, 1e-7),
                        (list(w_l), list(MZ * w_r * MX)))
        return left

    def test_mannys_sockets(self):
        """weapon_r at (-6.62, -1.69, 0.98) turned 1.6 deg, weapon_l at
        (0, 3.4, 0) - measured on Manny_Rig.ma 2026-09-29."""
        s_r = m((-1.3928, -0.4914, 1.5764), (-6.6212, -1.6945, 0.9776))
        s_l = m((0, 0, 0), (0, 3.4, 0))
        self._check((0, 0, 0), (0, 0, 0), (0, 0, 0), s_r, s_l)
        self._check((10, -20, 35), (1.5, -2.0, 4.0), (0, 45, 0), s_r, s_l)

    def test_the_zero_right_grip_turns_the_left_blade_round_on_manny(self):
        """At zero grip the left blade points backwards (-0.9993 measured):
        the mirror grip is a half turn there, not the identity."""
        s_r = m((-1.3928, -0.4914, 1.5764), (-6.6212, -1.6945, 0.9776))
        s_l = m((0, 0, 0), (0, 3.4, 0))
        rotate, _ = bonedrive.mirror_grip((0, 0, 0), (0, 0, 0), (0, 0, 0),
                                          tuple(s_r), tuple(s_l))
        turned = om.MEulerRotation(*[math.radians(v) for v in rotate])
        angle = turned.asQuaternion().asAxisAngle()[1]
        self.assertGreater(math.degrees(angle), 170.0)

    def test_a_geometric_mirror_pair_needs_no_correction(self):
        """The Creep's weapon_l is the geometric mirror of weapon_r (+1.0000
        measured): zero right grip -> zero left grip."""
        s_r = m((92.87, -14.60, -21.18), (-9.80, -4.61, 1.01))
        s_l = MZ * s_r * F
        rotate, translate = self._check((0, 0, 0), (0, 0, 0), (0, 0, 0),
                                        s_r, s_l)
        self.assertTrue(close(rotate, (0, 0, 0), 1e-6), rotate)
        self.assertTrue(close(translate, (0, 0, 0), 1e-6), translate)

    def test_random_grips_frames_and_sockets(self):
        rng = random.Random(7)

        def r():
            return tuple(rng.uniform(-180, 180) for _ in range(3))

        def t():
            return tuple(rng.uniform(-20, 20) for _ in range(3))
        for _ in range(20):
            self._check(r(), t(), r(), m(r(), t()), m(r(), t()))
