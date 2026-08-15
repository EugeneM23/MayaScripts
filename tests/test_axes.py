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


if __name__ == "__main__":
    unittest.main()
