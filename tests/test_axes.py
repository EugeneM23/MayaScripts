import math
import unittest

import maya.api.OpenMaya as om

from maya_overrig import axes


def _rot(x, y, z):
    """A rotation matrix from degrees, XYZ order."""
    return om.MEulerRotation(math.radians(x), math.radians(y),
                             math.radians(z)).asMatrix()


def _close(a, b, tol=1e-9):
    return max(abs(a[i] - b[i]) for i in range(16)) < tol


class TestFrameOffset(unittest.TestCase):

    def test_offset_maps_the_knot_frame_onto_the_bone(self):
        knot = _rot(10.0, 20.0, 30.0)
        bone = _rot(-5.0, 45.0, 12.0)
        offset = axes.frame_offset(bone, knot)
        self.assertTrue(_close(offset * knot, bone))

    def test_identical_frames_give_identity(self):
        frame = _rot(3.0, 4.0, 5.0)
        self.assertTrue(_close(axes.frame_offset(frame, frame), om.MMatrix()))

    def test_translation_is_ignored(self):
        knot = _rot(10.0, 20.0, 30.0)
        bone = _rot(-5.0, 45.0, 12.0)
        moved = om.MMatrix(bone)
        moved[12], moved[13], moved[14] = 100.0, -50.0, 7.0
        self.assertTrue(_close(axes.frame_offset(moved, knot),
                               axes.frame_offset(bone, knot)))


class TestRetarget(unittest.TestCase):

    def test_reference_frame_retargets_to_identity(self):
        """At the reference pose the controller reads zero."""
        reference = _rot(11.0, -22.0, 33.0)
        offset = _rot(90.0, 0.0, 0.0)
        self.assertTrue(_close(axes.retarget(reference, offset, reference),
                               om.MMatrix()))

    def test_world_is_preserved(self):
        """rotateAxis * retargeted * jointOrient == the original rotation.

        This identity is the whole safety argument: nothing in the scene can
        move, because the product the DAG consumes is unchanged.
        """
        offset = _rot(90.0, 15.0, -40.0)
        reference = _rot(11.0, -22.0, 33.0)
        rotate_axis, joint_orient = axes.orient_values(offset, reference)
        for pose in (_rot(0.0, 0.0, 0.0), _rot(5.0, 0.0, 0.0),
                     _rot(-30.0, 60.0, 120.0), reference):
            retargeted = axes.retarget(pose, offset, reference)
            self.assertTrue(
                _close(rotate_axis * retargeted * joint_orient, pose),
                "world moved for a pose")

    def test_identity_offset_is_a_plain_rebase(self):
        pose = _rot(10.0, 0.0, 0.0)
        reference = _rot(4.0, 0.0, 0.0)
        self.assertTrue(_close(
            axes.retarget(pose, om.MMatrix(), reference),
            pose * reference.inverse()))


class TestOrientValues(unittest.TestCase):

    def test_rotate_axis_is_the_inverse_offset(self):
        offset = _rot(90.0, 15.0, -40.0)
        rotate_axis, _ = axes.orient_values(offset, om.MMatrix())
        self.assertTrue(_close(rotate_axis, offset.inverse()))

    def test_joint_orient_carries_the_reference(self):
        offset = _rot(90.0, 15.0, -40.0)
        reference = _rot(11.0, -22.0, 33.0)
        _, joint_orient = axes.orient_values(offset, reference)
        self.assertTrue(_close(joint_orient, offset * reference))


class TestEulerDegrees(unittest.TestCase):

    def test_round_trips_a_rotation(self):
        values = axes.euler_degrees(_rot(10.0, 20.0, 30.0))
        for got, want in zip(values, (10.0, 20.0, 30.0)):
            self.assertAlmostEqual(got, want, places=6)

    def test_identity_is_zero(self):
        for value in axes.euler_degrees(om.MMatrix()):
            self.assertAlmostEqual(value, 0.0, places=9)

    def test_stays_near_the_previous_value(self):
        """A baked curve must not flip by 360 between neighbouring keys."""
        near = axes.euler_degrees(_rot(170.0, 0.0, 0.0),
                                  previous=(530.0, 0.0, 0.0))
        self.assertAlmostEqual(near[0], 530.0, places=6)

    def test_the_flipped_solution_describes_the_same_rotation(self):
        matrix = _rot(170.0, 0.0, 0.0)
        near = axes.euler_degrees(matrix, previous=(530.0, 0.0, 0.0))
        self.assertTrue(_close(_rot(*near), matrix, tol=1e-6))


class TestMirrorSigns(unittest.TestCase):

    IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

    def test_behaviour_mirror_reads_all_negative(self):
        """What the UE skeleton uses: mirror, then negate every axis."""
        right = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
        self.assertEqual(axes.mirror_signs(self.IDENTITY, right),
                         (-1, -1, -1))

    def test_the_convention_our_knots_used_to_have(self):
        right = ((-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0))
        self.assertEqual(axes.mirror_signs(self.IDENTITY, right), (1, -1, 1))

    def test_unrelated_frames_give_none(self):
        right = ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        self.assertIsNone(axes.mirror_signs(self.IDENTITY, right))

    def test_tolerates_a_small_measurement_error(self):
        right = ((0.999, 0.01, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
        self.assertEqual(axes.mirror_signs(self.IDENTITY, right),
                         (-1, -1, -1))

    def test_skewed_frames_are_handled(self):
        """Real bones are not axis-aligned; the measure must not assume it."""
        left = ((0.576, -0.817, 0.023), (-0.033, -0.052, -0.998),
                (0.817, 0.574, -0.056))
        right = tuple(tuple(-c for c in (-a[0], a[1], a[2])) for a in left)
        self.assertEqual(axes.mirror_signs(left, right), (-1, -1, -1))


if __name__ == "__main__":
    unittest.main()
