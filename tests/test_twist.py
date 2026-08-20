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
        self.assertEqual(twist.twist_set("arm_l"), "RigPicker_twist_arm_l")

    def test_the_set_name_carries_the_shared_prefix(self):
        """builder.recorded_members() finds it by the RigPicker_ prefix, so
        the twist rig is shielded from _reclaim like every other manifest."""
        self.assertTrue(twist.twist_set("leg_r").startswith("RigPicker_"))


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
