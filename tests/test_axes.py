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


def _trans(x, y, z):
    """A translation matrix -- what a child's local offset from its knot is."""
    matrix = om.MTransformationMatrix()
    matrix.setTranslation(om.MVector(x, y, z), om.MSpace.kTransform)
    return matrix.asMatrix()


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


class TestTotalRotation(unittest.TestCase):

    def test_composes_in_the_order_maya_consumes(self):
        rotate_axis, rotate, joint_orient = (_rot(5.0, 0.0, 0.0),
                                             _rot(0.0, 10.0, 0.0),
                                             _rot(0.0, 0.0, 15.0))
        self.assertTrue(_close(
            axes.total_rotation(rotate_axis, rotate, joint_orient),
            rotate_axis * rotate * joint_orient))


class TestRealignAnAlignedController(unittest.TestCase):
    """The controller may already carry a rotateAxis and a jointOrient -- from
    an earlier alignment, or from the rig it came out of. Working from the
    total rotation rather than the rotate channel alone keeps the world
    preserved in that case too, and makes a second pass a no-op."""

    def setUp(self):
        self.offset = _rot(90.0, 15.0, -40.0)
        self.rotate_axis = _rot(7.0, -3.0, 21.0)
        self.joint_orient = _rot(-12.0, 40.0, 4.0)

    def _total(self, rotate):
        return axes.total_rotation(self.rotate_axis, rotate, self.joint_orient)

    def test_world_is_preserved_over_a_prior_orientation(self):
        reference = self._total(_rot(11.0, -22.0, 33.0))
        new_axis, new_orient = axes.orient_values(self.offset, reference)
        for pose in (_rot(0.0, 0.0, 0.0), _rot(-30.0, 60.0, 120.0)):
            total = self._total(pose)
            retargeted = axes.retarget(total, self.offset, reference)
            self.assertTrue(_close(new_axis * retargeted * new_orient, total),
                            "world moved for a pose")

    def test_a_second_pass_changes_nothing(self):
        reference = self._total(_rot(11.0, -22.0, 33.0))
        first_axis, first_orient = axes.orient_values(self.offset, reference)
        pose = axes.retarget(self._total(_rot(-30.0, 60.0, 120.0)),
                             self.offset, reference)

        again_reference = axes.total_rotation(
            first_axis, axes.retarget(reference, self.offset, reference),
            first_orient)
        second_axis, second_orient = axes.orient_values(self.offset,
                                                        again_reference)
        self.assertTrue(_close(second_axis, first_axis))
        self.assertTrue(_close(second_orient, first_orient))
        self.assertTrue(_close(
            axes.retarget(axes.total_rotation(first_axis, pose, first_orient),
                          self.offset, again_reference),
            pose))


class TestAngleOf(unittest.TestCase):

    def test_identity_is_zero(self):
        self.assertAlmostEqual(axes.angle_of(om.MMatrix()), 0.0, places=9)

    def test_a_quarter_turn_reads_ninety(self):
        self.assertAlmostEqual(axes.angle_of(_rot(0.0, 90.0, 0.0)), 90.0,
                               places=6)

    def test_the_axis_does_not_matter(self):
        self.assertAlmostEqual(axes.angle_of(_rot(30.0, 0.0, 0.0)),
                               axes.angle_of(_rot(0.0, 0.0, 30.0)), places=6)

    def test_a_half_turn_does_not_overflow_the_arccos(self):
        self.assertAlmostEqual(axes.angle_of(_rot(180.0, 0.0, 0.0)), 180.0,
                               places=4)


class TestTurningAKnotOntoItsBone(unittest.TestCase):
    """The knot turns in place onto the bone's frame; its children stay.

    What the animator reads off a controller -- the rotate manipulator, the
    local rotation axes -- is the controller's own frame, and OverRig leaves it
    rolled about 90 degrees about the bone. Turning the knot is the only way to
    move it; counter-rotating the children is what keeps the bone still, since
    the bone is driven from a locator hanging under the knot.
    """

    def setUp(self):
        self.parent = _rot(15.0, -8.0, 40.0)    # the knot's parent world
        self.axis = _rot(90.0, -2.3, 0.4)       # rotateAxis, OverRig's roll
        self.pose = _rot(-12.0, 30.0, 5.0)      # rotate
        self.orient = _rot(4.0, -70.0, 11.0)    # jointOrient
        self.offset = _rot(-88.0, 6.0, -3.0)    # C, knot frame -> bone frame

    def _world(self, axis, orient=None, parent=None):
        return axes.total_rotation(
            axis, self.pose,
            self.orient if orient is None else orient) * (
                self.parent if parent is None else parent)

    def test_the_knot_lands_on_its_bone(self):
        bone = self.offset * self._world(self.axis)
        turned = axes.axis_on_bone(self.axis, self.offset)
        self.assertTrue(_close(self._world(turned), bone))

    def test_a_child_does_not_move(self):
        child = _rot(30.0, 10.0, -60.0)
        before = child * self._world(self.axis)
        after = (axes.child_held_still(child, self.offset)
                 * self._world(axes.axis_on_bone(self.axis, self.offset)))
        self.assertTrue(_close(before, after))

    def test_a_child_does_not_swing_off_its_place(self):
        """A child sits at an offset from the knot, so the knot's turn swings
        it somewhere else entirely. Correcting the child's rotation alone
        leaves it facing the right way in the wrong place -- which reads in a
        scene as the whole character coming apart.
        """
        local = _rot(30.0, 10.0, -60.0) * _trans(12.0, -3.0, 0.5)
        parent = self._world(self.axis)
        before = local * parent

        turned_parent = self._world(axes.axis_on_bone(self.axis, self.offset))
        held = (axes.child_held_still(_rot(30.0, 10.0, -60.0), self.offset)
                * _trans(*axes.child_position_held_still((12.0, -3.0, 0.5),
                                                         self.offset)))
        self.assertTrue(_close(held * turned_parent, before))

    def test_a_child_on_the_knot_itself_does_not_move(self):
        """The offset is turned, not translated: a child sitting exactly on
        its knot stays there."""
        held = axes.child_position_held_still((0.0, 0.0, 0.0), self.offset)
        for value in held:
            self.assertAlmostEqual(value, 0.0, places=12)

    def test_the_offset_keeps_its_length(self):
        held = axes.child_position_held_still((3.0, -4.0, 12.0), self.offset)
        self.assertAlmostEqual(sum(v * v for v in held) ** 0.5, 13.0,
                               places=9)

    def test_an_aligned_controller_ends_with_no_rotate_axis(self):
        """The alignment step leaves rotateAxis holding C inverse, so turning
        the knot onto its bone cancels it exactly -- a clean control."""
        self.assertTrue(_close(
            axes.axis_on_bone(self.offset.inverse(), self.offset),
            om.MMatrix()))

    def test_a_second_pass_changes_nothing(self):
        """Once the knot stands on the bone the measured offset is identity."""
        turned = axes.axis_on_bone(self.axis, self.offset)
        self.assertTrue(_close(axes.axis_on_bone(turned, om.MMatrix()),
                               turned))

    def test_the_rotate_channel_still_acts_in_the_bone_axes(self):
        """The frame the channels act in is jointOrient * parent, and neither
        is touched -- so this cannot spend what the alignment bought."""
        turned = axes.axis_on_bone(self.axis, self.offset)
        self.assertTrue(_close(self.orient * self.parent,
                               self.orient * self.parent))
        self.assertTrue(_close(self._world(turned),
                               self.offset * self._world(self.axis)))


class TestTurningAWholeChain(unittest.TestCase):
    """Two knots, each driving a bone through a locator of its own.

    The child knot is corrected twice: once as its parent's child (so it does
    not follow the parent's turn) and once on its own account. Both have to
    land, or a chain comes out right at the root and wrong further down.
    """

    def setUp(self):
        self.root_parent = _rot(0.0, 0.0, 0.0)
        self.first = dict(axis=_rot(90.0, 0.0, 0.0), pose=_rot(3.0, 0.0, 7.0),
                          orient=_rot(-85.0, 23.0, -0.5),
                          locator=_rot(-90.0, 0.0, 0.0),
                          offset=_rot(-90.0, 1.0, 0.0))
        self.second = dict(axis=_rot(85.2, 0.0, 0.0), pose=_rot(0.0, 4.0, 0.0),
                           orient=_rot(-85.1, 12.5, 1.1),
                           locator=_rot(-85.2, 0.0, 0.0),
                           offset=_rot(-85.0, 0.0, 2.0))

    @staticmethod
    def _local(knot):
        return axes.total_rotation(knot["axis"], knot["pose"], knot["orient"])

    def test_both_knots_land_and_neither_locator_moves(self):
        first_world = self._local(self.first) * self.root_parent
        second_world = self._local(self.second) * first_world
        bones = (self.first["offset"] * first_world,
                 self.second["offset"] * second_world)
        locators = (self.first["locator"] * first_world,
                    self.second["locator"] * second_world)

        # The root knot turns; everything hanging under it is held still.
        first_axis = axes.axis_on_bone(self.first["axis"], self.first["offset"])
        first_turned = axes.total_rotation(
            first_axis, self.first["pose"],
            self.first["orient"]) * self.root_parent
        second_orient = axes.child_held_still(self.second["orient"],
                                              self.first["offset"])
        first_locator = axes.child_held_still(self.first["locator"],
                                              self.first["offset"])

        # Then the child knot turns on its own account.
        second_axis = axes.axis_on_bone(self.second["axis"],
                                        self.second["offset"])
        second_turned = axes.total_rotation(
            second_axis, self.second["pose"], second_orient) * first_turned
        second_locator = axes.child_held_still(self.second["locator"],
                                               self.second["offset"])

        self.assertTrue(_close(first_turned, bones[0]), "root knot")
        self.assertTrue(_close(second_turned, bones[1]), "child knot")
        self.assertTrue(_close(first_locator * first_turned, locators[0]),
                        "root locator moved")
        self.assertTrue(_close(second_locator * second_turned, locators[1]),
                        "child locator moved")


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
