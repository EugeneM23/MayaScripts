"""Tests for the twist-bone resolution.

The network itself is proved by docs/superpowers/plans/verify_twist_bones.py.
What is testable here is every decision made before a node is created: which
segments a skeleton has, which of a bone's children are twist joints, what
fraction each one takes, and which channel may be written at all.
"""

import unittest

from maya_overrig import twist


class TestSegments(unittest.TestCase):

    def test_eight_segments_two_per_limb(self):
        self.assertEqual(len(twist.SEGMENTS), 8)
        for limb in ("arm_l", "arm_r", "leg_l", "leg_r"):
            kinds = sorted(s.kind for s in twist.SEGMENTS if s.limb == limb)
            self.assertEqual(kinds, [twist.COUNTER, twist.FOLLOW])

    def test_follow_drives_from_the_far_end(self):
        table = {(s.limb, s.kind): s for s in twist.SEGMENTS}
        arm = table[("arm_l", twist.FOLLOW)]
        self.assertEqual((arm.bone, arm.tip, arm.driver),
                         ("lowerarm_l", "hand_l", "hand_l"))
        leg = table[("leg_r", twist.FOLLOW)]
        self.assertEqual((leg.bone, leg.tip, leg.driver),
                         ("calf_r", "foot_r", "foot_r"))

    def test_counter_drives_from_the_bone_itself(self):
        table = {(s.limb, s.kind): s for s in twist.SEGMENTS}
        arm = table[("arm_l", twist.COUNTER)]
        self.assertEqual((arm.bone, arm.tip, arm.driver),
                         ("upperarm_l", "lowerarm_l", "upperarm_l"))
        leg = table[("leg_l", twist.COUNTER)]
        self.assertEqual((leg.bone, leg.tip, leg.driver),
                         ("thigh_l", "calf_l", "thigh_l"))

    def test_segments_needs_bone_tip_and_driver(self):
        full = {"upperarm_l": "|a", "lowerarm_l": "|b", "hand_l": "|c"}
        names = [(s.bone, s.kind) for s in twist.segments(full)]
        self.assertIn(("upperarm_l", twist.COUNTER), names)
        self.assertIn(("lowerarm_l", twist.FOLLOW), names)
        self.assertEqual(len(names), 2)

    def test_a_missing_tip_drops_the_segment(self):
        """A UE4-schema arm with no hand cannot have a forearm twist."""
        partial = {"upperarm_l": "|a", "lowerarm_l": "|b"}
        names = [(s.bone, s.kind) for s in twist.segments(partial)]
        self.assertEqual(names, [("upperarm_l", twist.COUNTER)])

    def test_empty_map_gives_nothing(self):
        self.assertEqual(twist.segments({}), [])

    def test_limbs_are_the_four_of_the_body(self):
        self.assertEqual(twist.LIMBS, ("arm_l", "arm_r", "leg_l", "leg_r"))

    def test_set_name_is_per_limb(self):
        self.assertEqual(twist.twist_set_name("arm_l"),
                         "RigPicker_twist_arm_l")

    def test_the_set_name_carries_the_shared_prefix(self):
        """builder.recorded_members() finds it by the RigPicker_ prefix, so
        the twist rig is shielded from _reclaim like every other manifest."""
        self.assertTrue(twist.twist_set_name("leg_r").startswith(
            "RigPicker_"))


class TestTwistJoints(unittest.TestCase):

    def test_picks_the_twist_children_only(self):
        children = ["lowerarm_twist_01_l", "hand_l", "lowerarm_twist_02_l"]
        self.assertEqual(twist.twist_joints(children),
                         ["lowerarm_twist_01_l", "lowerarm_twist_02_l"])

    def test_sorted_by_index_not_by_string(self):
        children = ["x_twist_10_l", "x_twist_02_l", "x_twist_1_l"]
        self.assertEqual(twist.twist_joints(children),
                         ["x_twist_1_l", "x_twist_02_l", "x_twist_10_l"])

    def test_a_prefixed_skeleton_still_matches(self):
        """Per-joint prefixes are normal on this rig; the match is an infix."""
        self.assertEqual(twist.twist_joints(["ue5:MyChar_lowerarm_twist_01_l"]),
                         ["ue5:MyChar_lowerarm_twist_01_l"])

    def test_case_insensitive(self):
        self.assertEqual(twist.twist_joints(["Lowerarm_Twist_01_L"]),
                         ["Lowerarm_Twist_01_L"])

    def test_no_twists_is_empty(self):
        self.assertEqual(twist.twist_joints(["hand_l", "ik_hand_gun"]), [])

    def test_the_word_twist_without_an_index_does_not_match(self):
        """`twistybone` is somebody else's joint, not a UE twist joint."""
        self.assertEqual(twist.twist_joints(["twistybone", "twist",
                                             "roll_twist_l"]), [])


class TestWeights(unittest.TestCase):

    def test_follow_takes_its_measured_fraction(self):
        self.assertEqual(twist.weights(["a", "b"], [0.25, 0.75],
                                       twist.FOLLOW), [0.25, 0.75])

    def test_counter_gives_back_what_it_inherited(self):
        """A joint at the shoulder counters everything, one at the elbow none."""
        self.assertEqual(twist.weights(["a", "b"], [0.0, 1.0],
                                       twist.COUNTER), [-1.0, 0.0])

    def test_counter_at_a_quarter_counters_three_quarters(self):
        self.assertEqual(twist.weights(["a"], [0.25], twist.COUNTER), [-0.75])

    def test_two_joints_at_the_same_place_split_evenly(self):
        """Positions that carry no information are replaced, not trusted:
        two joints in one spot would otherwise take identical fractions."""
        self.assertEqual(twist.weights(["a", "b"], [0.0, 0.0],
                                       twist.FOLLOW),
                         [1.0 / 3.0, 2.0 / 3.0])

    def test_a_single_joint_at_the_origin_falls_back_to_half(self):
        self.assertEqual(twist.weights(["a"], [0.0], twist.FOLLOW), [0.5])

    def test_a_single_joint_with_a_real_position_is_trusted(self):
        self.assertEqual(twist.weights(["a"], [0.4], twist.FOLLOW), [0.4])

    def test_positions_are_clamped_to_the_bone(self):
        """A twist joint measured past the far end, or behind the origin,
        would otherwise ask for more twist than exists."""
        self.assertEqual(twist.weights(["a", "b"], [-0.2, 1.4],
                                       twist.FOLLOW), [0.0, 1.0])

    def test_the_override_table_wins(self):
        twist._WEIGHT["lowerarm_twist_01_l"] = 0.9
        try:
            self.assertEqual(
                twist.weights(["lowerarm_twist_01_l"], [0.4], twist.FOLLOW),
                [0.9])
        finally:
            del twist._WEIGHT["lowerarm_twist_01_l"]

    def test_the_override_is_matched_on_the_leaf_name(self):
        twist._WEIGHT["lowerarm_twist_01_l"] = -0.25
        try:
            self.assertEqual(
                twist.weights(["|root|ns:lowerarm_twist_01_l"], [0.4],
                              twist.FOLLOW), [-0.25])
        finally:
            del twist._WEIGHT["lowerarm_twist_01_l"]

    def test_no_joints_is_no_weights(self):
        self.assertEqual(twist.weights([], [], twist.FOLLOW), [])


class TestAxisChoice(unittest.TestCase):

    IDENT = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0),
             "z": (0.0, 0.0, 1.0)}

    def test_x_along_the_bone_with_rotate_order_xyz(self):
        got = twist.axis_choice(self.IDENT, (1.0, 0.0, 0.0), 0)
        self.assertEqual((got.channel, got.sign, got.reason), ("x", 1.0, None))

    def test_a_flipped_axis_is_taken_with_a_negative_sign(self):
        got = twist.axis_choice(self.IDENT, (-1.0, 0.0, 0.0), 0)
        self.assertEqual((got.channel, got.sign, got.reason), ("x", -1.0, None))

    def test_an_unnormalised_bone_direction_is_fine(self):
        got = twist.axis_choice(self.IDENT, (7.5, 0.0, 0.0), 0)
        self.assertEqual(got.channel, "x")

    def test_y_along_the_bone_needs_a_y_first_rotate_order(self):
        got = twist.axis_choice(self.IDENT, (0.0, 1.0, 0.0), 1)   # yzx
        self.assertEqual((got.channel, got.sign, got.reason), ("y", 1.0, None))

    def test_the_bone_axis_must_be_first_in_the_rotate_order(self):
        """Adding to a channel that is not innermost rotates about the parent,
        not about the bone: it would bend where it should roll."""
        got = twist.axis_choice(self.IDENT, (0.0, 1.0, 0.0), 0)   # xyz
        self.assertIsNone(got.channel)
        self.assertIn("rotate order", got.reason)

    def test_an_axis_off_the_bone_is_refused(self):
        skew = {"x": (0.7071, 0.7071, 0.0), "y": (-0.7071, 0.7071, 0.0),
                "z": (0.0, 0.0, 1.0)}
        got = twist.axis_choice(skew, (1.0, 0.0, 0.0), 0)
        self.assertIsNone(got.channel)
        self.assertIn("along the bone", got.reason)

    def test_a_small_misalignment_is_accepted(self):
        """Nothing in a real skeleton is exact; 5 degrees is not a refusal."""
        near = {"x": (0.9962, 0.0872, 0.0), "y": (-0.0872, 0.9962, 0.0),
                "z": (0.0, 0.0, 1.0)}
        got = twist.axis_choice(near, (1.0, 0.0, 0.0), 0)
        self.assertEqual(got.channel, "x")

    def test_a_zero_bone_direction_is_refused(self):
        got = twist.axis_choice(self.IDENT, (0.0, 0.0, 0.0), 0)
        self.assertIsNone(got.channel)
        self.assertIn("zero", got.reason)

    def test_every_rotate_order_names_a_real_channel(self):
        self.assertEqual(len(twist.ROTATE_ORDERS), 6)
        for order in twist.ROTATE_ORDERS:
            self.assertEqual(sorted(order), ["x", "y", "z"])


class TestNodeNames(unittest.TestCase):

    def test_seven_distinct_names_derived_from_the_joint(self):
        names = twist.node_names("|root|lowerarm_twist_01_l")
        self.assertEqual(len(set(names.values())), 7)
        for name in names.values():
            self.assertTrue(name.startswith("lowerarm_twist_01_l_tw"))

    def test_the_dag_path_never_reaches_the_node_name(self):
        """A node name with a pipe in it is not a legal Maya name."""
        for name in twist.node_names("|a|b|thigh_twist_01_r").values():
            self.assertNotIn("|", name)

    def test_a_namespace_never_reaches_the_node_name(self):
        for name in twist.node_names("|ns:calf_twist_02_l").values():
            self.assertNotIn(":", name)

    def test_two_joints_never_collide(self):
        left = set(twist.node_names("lowerarm_twist_01_l").values())
        right = set(twist.node_names("lowerarm_twist_01_r").values())
        self.assertEqual(left & right, set())


class TestCollapses(unittest.TestCase):

    def test_a_still_channel_needs_no_keys(self):
        self.assertTrue(twist.collapses([12.5, 12.5, 12.5]))

    def test_a_moving_channel_needs_keys(self):
        self.assertFalse(twist.collapses([12.5, 12.5, 12.6]))

    def test_one_sample_collapses(self):
        self.assertTrue(twist.collapses([3.0]))

    def test_nothing_collapses(self):
        self.assertTrue(twist.collapses([]))


class SplitPlugs(unittest.TestCase):
    """The driven channels are recorded on the manifest, because neither walk
    of the rig itself is safe: cmds.objectType on an addDoubleLinear answers
    "addDL", and Maya splices a unitConversion in front of the channel."""

    def test_parses_a_pair(self):
        self.assertEqual(twist.split_plugs("ABC123.rx"), [("ABC123", "rx")])

    def test_parses_several(self):
        self.assertEqual(twist.split_plugs("A.rx B.ry"),
                         [("A", "rx"), ("B", "ry")])

    def test_nothing_is_empty(self):
        self.assertEqual(twist.split_plugs(""), [])
        self.assertEqual(twist.split_plugs(None), [])

    def test_a_token_with_no_channel_is_dropped(self):
        self.assertEqual(twist.split_plugs("A.rx broken B.ry"),
                         [("A", "rx"), ("B", "ry")])

    def test_extra_whitespace_is_harmless(self):
        self.assertEqual(twist.split_plugs("  A.rx   B.ry  "),
                         [("A", "rx"), ("B", "ry")])


class TestLift(unittest.TestCase):
    """The quaternion a matrix decomposes to is sign-ambiguous, so a raw roll
    reading can differ from its neighbour by 360 degrees for no physical
    reason. Carrying the sign forward is what makes the sequence mean
    anything. See docs/superpowers/specs/2026-09-03-twist-roll-limit-design.md
    """

    def test_a_continuous_sequence_is_left_alone(self):
        self.assertEqual(twist.lift([0.0, 10.0, 20.0]), [0.0, 10.0, 20.0])

    def test_nothing_is_empty(self):
        self.assertEqual(twist.lift([]), [])
        self.assertEqual(twist.lift(None), [])

    def test_one_sample_is_itself(self):
        self.assertEqual(twist.lift([170.0]), [170.0])

    def test_a_wrap_upward_is_lifted(self):
        # the measured shape: +164.86 then a wrap to -170.39
        lifted = twist.lift([164.86, -170.39])
        self.assertAlmostEqual(lifted[0], 164.86, places=6)
        self.assertAlmostEqual(lifted[1], 189.61, places=6)

    def test_a_wrap_downward_is_lifted(self):
        lifted = twist.lift([-164.86, 170.39])
        self.assertAlmostEqual(lifted[1], -189.61, places=6)

    def test_the_lift_accumulates_across_several_wraps(self):
        lifted = twist.lift([170.0, -170.0, -150.0, -130.0])
        self.assertAlmostEqual(lifted[-1], 230.0, places=6)

    def test_the_lift_takes_the_SHORT_way_between_neighbours(self):
        # 190 then 170 is a 20 degree step back, not a 340 degree climb --
        # which is exactly why excursion must not lift again.
        lifted = twist.lift([170.0, -170.0, 170.0])
        self.assertAlmostEqual(lifted[1], 190.0, places=6)
        self.assertAlmostEqual(lifted[2], 170.0, places=6)

    def test_the_anchor_is_the_first_sample(self):
        self.assertEqual(twist.lift([-170.0])[0], -170.0)

    def test_real_motion_under_180_is_not_mistaken_for_a_wrap(self):
        # 179 degrees of genuine travel in one step stays as it is
        lifted = twist.lift([0.0, 179.0])
        self.assertAlmostEqual(lifted[1], 179.0, places=6)


class TestExcursion(unittest.TestCase):
    """How far the roll leaves the window quatToEuler can express. Measured:
    the node wraps into (-180, +180], so a roll outside that arrives as a
    360-degree step in one frame."""

    def test_inside_the_window_is_zero(self):
        self.assertEqual(twist.excursion([0.0, 90.0, -90.0]), 0.0)

    def test_nothing_is_zero(self):
        self.assertEqual(twist.excursion([]), 0.0)
        self.assertEqual(twist.excursion(None), 0.0)

    def test_the_window_edge_is_inside(self):
        self.assertEqual(twist.excursion([0.0, 180.0, -180.0]), 0.0)

    def test_past_the_top_edge(self):
        self.assertAlmostEqual(twist.excursion([0.0, 200.0]), 20.0, places=6)

    def test_past_the_bottom_edge(self):
        self.assertAlmostEqual(twist.excursion([0.0, -200.0]), 20.0, places=6)

    def test_the_worse_of_the_two_edges_is_reported(self):
        self.assertAlmostEqual(twist.excursion([-190.0, -250.0]), 70.0,
                               places=6)

    def test_raw_wrapped_readings_must_be_lifted_first(self):
        # raw readings, already wrapped by the node: the true roll went past
        # +180 and came back as a negative number. Judged raw they look like
        # a tame -170..165; lifted, they are the 189.61 they really are.
        raw = [164.86, -170.39]
        self.assertEqual(twist.excursion(raw), 0.0)
        self.assertGreater(twist.excursion(twist.lift(raw)), 0.0)

    def test_the_measured_right_upper_arm_is_outside(self):
        # upperarm_r, measured 2026-09-03: a 516 degree continuous span
        self.assertGreater(twist.excursion([-309.6, 206.6]), 0.0)

    def test_the_measured_left_upper_arm_is_inside(self):
        # upperarm_l, measured the same day: -40.3 .. +34.6, 139.7 of headroom
        self.assertEqual(twist.excursion([-40.3, 34.6]), 0.0)

    def test_a_span_wider_than_the_whole_window_is_outside(self):
        # wherever the zero sits, a span past 360 wraps somewhere
        self.assertGreater(twist.excursion([-10.0, 355.0]), 0.0)

    def test_the_window_is_a_parameter(self):
        self.assertEqual(twist.excursion([0.0, 100.0], window=180.0), 0.0)
        self.assertAlmostEqual(twist.excursion([0.0, 100.0], window=90.0),
                               10.0, places=6)


class TestSampledRolls(unittest.TestCase):
    """The roll per sampled delta matrix, lifted. OpenMaya only, so it is
    testable with no scene -- the way axes.py is."""

    @staticmethod
    def _identity():
        return [1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0]

    @staticmethod
    def _roll_matrix(degrees, axis=(1.0, 0.0, 0.0)):
        import math

        import maya.api.OpenMaya as om
        q = om.MQuaternion(math.radians(degrees), om.MVector(*axis))
        m = q.asMatrix()
        return [m[i] for i in range(16)]

    def test_the_build_pose_reads_zero(self):
        rolls = twist.sampled_rolls([self._identity()], (1.0, 0.0, 0.0))
        self.assertAlmostEqual(rolls[0], 0.0, places=6)

    def test_nothing_is_empty(self):
        self.assertEqual(twist.sampled_rolls([], (1.0, 0.0, 0.0)), [])

    def test_a_pure_roll_reads_its_own_angle(self):
        rolls = twist.sampled_rolls([self._roll_matrix(30.0)],
                                    (1.0, 0.0, 0.0))
        self.assertAlmostEqual(rolls[0], 30.0, places=4)

    def test_a_negative_roll_reads_negative(self):
        rolls = twist.sampled_rolls([self._roll_matrix(-45.0)],
                                    (1.0, 0.0, 0.0))
        self.assertAlmostEqual(rolls[0], -45.0, places=4)

    def test_a_roll_about_another_axis_reads_zero_on_ours(self):
        rolls = twist.sampled_rolls(
            [self._roll_matrix(60.0, axis=(0.0, 1.0, 0.0))],
            (1.0, 0.0, 0.0))
        self.assertAlmostEqual(rolls[0], 0.0, places=4)

    def test_a_sequence_past_180_comes_back_lifted_not_wrapped(self):
        matrices = [self._roll_matrix(d) for d in (170.0, 190.0, 210.0)]
        rolls = twist.sampled_rolls(matrices, (1.0, 0.0, 0.0))
        self.assertAlmostEqual(rolls[0], 170.0, places=3)
        self.assertAlmostEqual(rolls[1], 190.0, places=3)
        self.assertAlmostEqual(rolls[2], 210.0, places=3)

    def test_that_sequence_is_reported_outside_the_window(self):
        matrices = [self._roll_matrix(d) for d in (0.0, 170.0, 190.0)]
        self.assertGreater(twist.excursion(
            twist.sampled_rolls(matrices, (1.0, 0.0, 0.0))), 0.0)

    def test_the_axis_need_not_arrive_normalised(self):
        rolls = twist.sampled_rolls([self._roll_matrix(30.0)],
                                    (2.0, 0.0, 0.0))
        self.assertAlmostEqual(rolls[0], 30.0, places=4)


class TestRollRefusal(unittest.TestCase):
    """The message a refused segment gets. Pure, so the wording is pinned."""

    def test_a_segment_inside_the_window_is_not_refused(self):
        self.assertIsNone(twist.roll_refusal([0.0, 90.0]))

    def test_nothing_is_not_refused(self):
        self.assertIsNone(twist.roll_refusal([]))
        self.assertIsNone(twist.roll_refusal(None))

    def test_a_segment_outside_the_window_is_refused(self):
        self.assertIsNotNone(twist.roll_refusal([-309.6, 206.6]))

    def test_the_refusal_names_the_number(self):
        reason = twist.roll_refusal([0.0, 207.0])
        self.assertIn("207", reason)

    def test_the_refusal_says_what_the_limit_is(self):
        reason = twist.roll_refusal([0.0, 207.0])
        self.assertIn("180", reason)


class TestAnchored(unittest.TestCase):
    """The lift anchors on its first sample, and that offset is only known up
    to a multiple of 360. The BUILD frame is what fixes it: there the delta is
    the identity and the roll is exactly zero."""

    def test_the_named_sample_becomes_zero(self):
        self.assertEqual(twist.anchored([10.0, 20.0, 30.0], 1),
                         [-10.0, 0.0, 10.0])

    def test_the_first_sample_may_be_the_anchor(self):
        self.assertEqual(twist.anchored([5.0, 7.0], 0), [0.0, 2.0])

    def test_nothing_is_empty(self):
        self.assertEqual(twist.anchored([], 0), [])
        self.assertEqual(twist.anchored(None, 0), [])

    def test_an_index_off_the_end_leaves_the_sequence_alone(self):
        # no anchor to be had; the span check needs none anyway
        self.assertEqual(twist.anchored([10.0, 20.0], 9), [10.0, 20.0])

    def test_a_negative_index_leaves_the_sequence_alone(self):
        self.assertEqual(twist.anchored([10.0, 20.0], -1), [10.0, 20.0])

    def test_shifting_does_not_change_the_span(self):
        values = [-309.6, 206.6]
        shifted = twist.anchored(values, 0)
        self.assertAlmostEqual(max(shifted) - min(shifted),
                               max(values) - min(values), places=9)

    def test_the_measured_right_upper_arm_stays_refused_after_anchoring(self):
        # 516 degrees of span wraps wherever the zero sits
        shifted = twist.anchored([-309.6, 0.0, 206.6], 1)
        self.assertGreater(twist.excursion(shifted), 0.0)
