import unittest

from maya_overrig import bodymap, builder


class TestLimbTable(unittest.TestCase):

    def test_five_limbs(self):
        self.assertEqual(len(builder.LIMBS), 5)

    def test_names_are_the_picker_regions_plus_spine(self):
        self.assertEqual([name for name, _ in builder.LIMBS],
                         ["arm_l", "arm_r", "leg_l", "leg_r", "spine"])

    def test_three_joints_each(self):
        for name, joints in builder.LIMBS:
            self.assertEqual(len(joints), 3, name)

    def test_fifteen_distinct_joints(self):
        every = [j for _, joints in builder.LIMBS for j in joints]
        self.assertEqual(len(every), 15)
        self.assertEqual(len(set(every)), 15)

    def test_every_joint_exists_in_the_body_map(self):
        known = {b.joint for b in bodymap.BUTTONS}
        for name, joints in builder.LIMBS:
            for joint in joints:
                self.assertIn(joint, known, "{0}: {1}".format(name, joint))

    def test_order_is_root_middle_end(self):
        table = dict(builder.LIMBS)
        self.assertEqual(table["leg_l"], ("thigh_l", "calf_l", "foot_l"))
        self.assertEqual(table["arm_r"], ("upperarm_r", "lowerarm_r", "hand_r"))

    def test_spine_runs_pelvis_to_chest(self):
        """Root, middle, end -- the same 3-joint form the limbs use, so the
        rebike proc takes the branch whose output is the three named controls
        the user asked for: bottom, centre, top."""
        table = dict(builder.LIMBS)
        self.assertEqual(table["spine"], ("pelvis", "spine_03", "spine_05"))


class TestDefaultIk(unittest.TestCase):

    def test_arms_and_legs_only(self):
        self.assertEqual(builder.DEFAULT_IK,
                         ("arm_l", "arm_r", "leg_l", "leg_r"))

    def test_subset_of_the_limb_table(self):
        names = {name for name, _ in builder.LIMBS}
        self.assertTrue(set(builder.DEFAULT_IK) < names)


class TestIkRoles(unittest.TestCase):

    def test_three_roles(self):
        self.assertEqual(set(builder.IK_ROLES), {"end", "pole", "base"})

    def test_marks_are_distinct_overrig_suffixes(self):
        marks = list(builder.IK_ROLES.values())
        self.assertEqual(len(marks), len(set(marks)))
        for mark in marks:
            self.assertTrue(mark.startswith("_IK_"))

    def test_marks_match_what_the_rebike_rename_produces(self):
        """rename lines in apply_rebike_3_or_more_object_to_IK, read verbatim:
        <root>_IK_strech_gr, <end>_IK_feet, <middle>_IK_knee."""
        self.assertEqual(builder.IK_ROLES["end"], "_IK_feet")
        self.assertEqual(builder.IK_ROLES["pole"], "_IK_knee")
        self.assertEqual(builder.IK_ROLES["base"], "_IK_strech_gr")


class TestLimbJoints(unittest.TestCase):

    @staticmethod
    def _full_map():
        return {j: "|rig|" + j
                for _, joints in builder.LIMBS for j in joints}

    def test_resolves_all_five_limbs(self):
        resolved = builder.limb_joints(self._full_map())
        self.assertEqual(len(resolved), 5)

    def test_keeps_joint_order(self):
        resolved = dict(builder.limb_joints(self._full_map()))
        self.assertEqual(resolved["leg_l"],
                         ["|rig|thigh_l", "|rig|calf_l", "|rig|foot_l"])

    def test_maps_through_the_scene_map(self):
        """Prefixed and namespaced paths come straight from the binding."""
        scene_map = self._full_map()
        scene_map["foot_l"] = "|hero:rig|hero:prefix_foot_l"
        resolved = dict(builder.limb_joints(scene_map))
        self.assertEqual(resolved["leg_l"][2], "|hero:rig|hero:prefix_foot_l")

    def test_skips_a_limb_with_a_missing_joint(self):
        scene_map = self._full_map()
        del scene_map["calf_r"]
        resolved = dict(builder.limb_joints(scene_map))
        self.assertNotIn("leg_r", resolved)
        self.assertIn("leg_l", resolved)

    def test_empty_map_resolves_nothing(self):
        self.assertEqual(builder.limb_joints({}), [])


class TestMissingLimbs(unittest.TestCase):

    def test_nothing_missing_on_a_full_skeleton(self):
        scene_map = {j: "|rig|" + j
                     for _, joints in builder.LIMBS for j in joints}
        self.assertEqual(builder.missing_limbs(scene_map), [])

    def test_reports_the_incomplete_limb(self):
        scene_map = {j: "|rig|" + j
                     for _, joints in builder.LIMBS for j in joints}
        del scene_map["hand_l"]
        self.assertEqual(builder.missing_limbs(scene_map), ["arm_l"])

    def test_empty_map_misses_everything(self):
        self.assertEqual(builder.missing_limbs({}),
                         ["arm_l", "arm_r", "leg_l", "leg_r", "spine"])


class TestLimbSet(unittest.TestCase):

    def test_name_is_prefixed(self):
        self.assertEqual(builder.limb_set("leg_l"), "RigPicker_build_leg_l")

    def test_every_limb_gets_a_distinct_set(self):
        names = [builder.limb_set(name) for name, _ in builder.LIMBS]
        self.assertEqual(len(set(names)), len(builder.LIMBS))


class TestResolveLimbs(unittest.TestCase):

    SCENE_MAP = {
        "upperarm_l": "|rig|upperarm_l", "lowerarm_l": "|rig|lowerarm_l",
        "hand_l": "|rig|hand_l",
        "upperarm_r": "|rig|upperarm_r", "lowerarm_r": "|rig|lowerarm_r",
        "hand_r": "|rig|hand_r",
        "thigh_l": "|rig|thigh_l", "calf_l": "|rig|calf_l",
        "foot_l": "|rig|foot_l",
        "thigh_r": "|rig|thigh_r", "calf_r": "|rig|calf_r",
        "foot_r": "|rig|foot_r",
    }

    MEMBERS = {
        "leg_l": ["|thigh_l_IK_strech_gr", "|foot_l_IK_feet",
                  "|calf_l_IK_knee"],
        "leg_r": ["|thigh_r_IK_strech_gr", "|foot_r_IK_feet",
                  "|calf_r_IK_knee"],
    }

    def resolve(self, nodes):
        return builder.resolve_limbs(nodes, self.MEMBERS, self.SCENE_MAP)

    def test_recorded_node_resolves(self):
        self.assertEqual(self.resolve(["|foot_l_IK_feet"]), ["leg_l"])

    def test_descendant_of_a_recorded_node_resolves(self):
        self.assertEqual(
            self.resolve(["|thigh_l_IK_strech_gr|base_IK_strech3|fin_jnt11"]),
            ["leg_l"])

    def test_shape_under_a_control_resolves(self):
        self.assertEqual(
            self.resolve(["|foot_l_IK_feet|foot_l_IK_feetShape"]), ["leg_l"])

    def test_source_joint_resolves(self):
        """Lets the picker's own limb buttons drive the bake."""
        self.assertEqual(self.resolve(["|rig|calf_l"]), ["leg_l"])

    def test_source_joint_resolves_without_any_manifest(self):
        self.assertEqual(
            builder.resolve_limbs(["|rig|hand_r"], {}, self.SCENE_MAP),
            ["arm_r"])

    def test_unrelated_node_resolves_to_nothing(self):
        self.assertEqual(self.resolve(["|persp"]), [])

    def test_two_limbs_give_both(self):
        self.assertEqual(
            self.resolve(["|foot_l_IK_feet", "|foot_r_IK_feet"]),
            ["leg_l", "leg_r"])

    def test_duplicates_collapse(self):
        self.assertEqual(
            self.resolve(["|foot_l_IK_feet", "|calf_l_IK_knee",
                          "|rig|thigh_l"]),
            ["leg_l"])

    def test_results_come_back_in_limb_table_order(self):
        found = self.resolve(["|foot_r_IK_feet", "|rig|hand_l",
                              "|foot_l_IK_feet"])
        self.assertEqual(found, ["arm_l", "leg_l", "leg_r"])

    def test_a_prefix_that_is_not_a_path_boundary_does_not_match(self):
        """`|foot_l_IK_feet_extra` is a different node, not a descendant."""
        self.assertEqual(self.resolve(["|foot_l_IK_feet_extra"]), [])

    def test_empty_selection_resolves_to_nothing(self):
        self.assertEqual(self.resolve([]), [])


class TestTopLevel(unittest.TestCase):

    def test_nested_path_reduces_to_its_outermost_ancestor(self):
        self.assertEqual(
            builder.top_level("|foot_l_IK_feet|base_IK_strech3|locator19"),
            "|foot_l_IK_feet")

    def test_already_top_level_is_unchanged(self):
        self.assertEqual(builder.top_level("|foot_l_IK_feet"),
                         "|foot_l_IK_feet")

    def test_path_without_a_leading_separator(self):
        self.assertEqual(builder.top_level("group|child"), "|group")

    def test_bare_name(self):
        self.assertEqual(builder.top_level("locator19"), "|locator19")


class TestUnrecordedRigRoots(unittest.TestCase):

    MADE = ["|foot_l_IK_feet", "|calf_l_IK_knee", "|thigh_l_IK_strech_gr"]

    def test_driver_nested_under_a_known_root_resolves_to_it(self):
        self.assertEqual(
            builder.unrecorded_rig_roots(
                ["|foot_l_IK_feet|base_IK_strech3|locator19"], self.MADE),
            ["|foot_l_IK_feet"])

    def test_driver_that_is_itself_the_root_resolves_to_itself(self):
        self.assertEqual(
            builder.unrecorded_rig_roots(["|calf_l_IK_knee"], self.MADE),
            ["|calf_l_IK_knee"])

    def test_driver_under_something_unknown_yields_nothing(self):
        """A constraint the user set up by hand must survive."""
        self.assertEqual(
            builder.unrecorded_rig_roots(["|my_own_group|my_locator"],
                                         self.MADE),
            [])

    def test_duplicates_collapse(self):
        self.assertEqual(
            builder.unrecorded_rig_roots(
                ["|foot_l_IK_feet|a|loc1", "|foot_l_IK_feet|b|loc2"],
                self.MADE),
            ["|foot_l_IK_feet"])

    def test_results_are_sorted(self):
        found = builder.unrecorded_rig_roots(
            ["|thigh_l_IK_strech_gr|x", "|calf_l_IK_knee|y"], self.MADE)
        self.assertEqual(found, ["|calf_l_IK_knee", "|thigh_l_IK_strech_gr"])

    def test_no_drivers_yields_nothing(self):
        self.assertEqual(builder.unrecorded_rig_roots([], self.MADE), [])

    def test_nothing_known_yields_nothing(self):
        self.assertEqual(
            builder.unrecorded_rig_roots(["|foot_l_IK_feet|a"], []), [])


class TestOrderByNesting(unittest.TestCase):

    FLAT = {
        "arm_l": ["|hand_l_IK_feet", "|upperarm_l_IK_strech_gr"],
        "leg_l": ["|foot_l_IK_feet", "|thigh_l_IK_strech_gr"],
        "leg_r": ["|foot_r_IK_feet"],
    }

    # The reported failure: the arm's control parked under the leg's.
    NESTED = {
        "arm_l": ["|foot_l_IK_feet|hand_l_IK_feet",
                  "|upperarm_l_IK_strech_gr"],
        "leg_l": ["|foot_l_IK_feet", "|thigh_l_IK_strech_gr"],
        "leg_r": ["|foot_r_IK_feet"],
    }

    def test_nothing_nested_returns_the_request(self):
        self.assertEqual(builder.order_by_nesting(["leg_l"], self.FLAT),
                         ["leg_l"])

    def test_nested_limb_is_added_and_comes_first(self):
        self.assertEqual(builder.order_by_nesting(["leg_l"], self.NESTED),
                         ["arm_l", "leg_l"])

    def test_requesting_the_inner_limb_does_not_drag_in_its_container(self):
        self.assertEqual(builder.order_by_nesting(["arm_l"], self.NESTED),
                         ["arm_l"])

    def test_three_deep_chain_comes_out_innermost_first(self):
        chain = {
            "leg_r": ["|foot_r_IK_feet"],
            "leg_l": ["|foot_r_IK_feet|foot_l_IK_feet"],
            "arm_l": ["|foot_r_IK_feet|foot_l_IK_feet|hand_l_IK_feet"],
        }
        self.assertEqual(builder.order_by_nesting(["leg_r"], chain),
                         ["arm_l", "leg_l", "leg_r"])

    def test_two_independent_nestings_both_resolve(self):
        both = {
            "leg_l": ["|foot_l_IK_feet"],
            "arm_l": ["|foot_l_IK_feet|hand_l_IK_feet"],
            "leg_r": ["|foot_r_IK_feet"],
            "arm_r": ["|foot_r_IK_feet|hand_r_IK_feet"],
        }
        found = builder.order_by_nesting(["leg_l", "leg_r"], both)
        self.assertLess(found.index("arm_l"), found.index("leg_l"))
        self.assertLess(found.index("arm_r"), found.index("leg_r"))

    def test_limb_without_a_manifest_survives_the_call(self):
        self.assertEqual(builder.order_by_nesting(["leg_r"], {}), ["leg_r"])

    def test_shared_prefix_without_a_separator_is_not_nesting(self):
        lookalike = {
            "leg_l": ["|foot_l_IK_feet"],
            "arm_l": ["|foot_l_IK_feet_extra"],
        }
        self.assertEqual(builder.order_by_nesting(["leg_l"], lookalike),
                         ["leg_l"])


class TestForeignKnotsInside(unittest.TestCase):

    DOOMED = ["|foot_l_IK_feet", "|thigh_l_IK_strech_gr"]
    OURS = ["|foot_l_IK_feet", "|thigh_l_IK_strech_gr",
            "|foot_l_IK_feet|hand_l_IK_feet"]

    def test_foreign_knot_inside_is_reported(self):
        made = ["|foot_l_IK_feet", "|foot_l_IK_feet|my_spine_knot"]
        self.assertEqual(
            builder.foreign_knots_inside(self.DOOMED, self.OURS, made),
            ["|foot_l_IK_feet|my_spine_knot"])

    def test_our_own_nested_limb_is_not_foreign(self):
        made = ["|foot_l_IK_feet", "|foot_l_IK_feet|hand_l_IK_feet"]
        self.assertEqual(
            builder.foreign_knots_inside(self.DOOMED, self.OURS, made), [])

    def test_knot_outside_the_doomed_rigs_is_ignored(self):
        made = ["|somewhere_else|my_knot"]
        self.assertEqual(
            builder.foreign_knots_inside(self.DOOMED, self.OURS, made), [])

    def test_a_rig_root_is_not_nested_inside_itself(self):
        made = ["|foot_l_IK_feet"]
        self.assertEqual(
            builder.foreign_knots_inside(self.DOOMED, [], made), [])

    def test_results_are_sorted_and_deduplicated(self):
        made = ["|foot_l_IK_feet|b_knot", "|foot_l_IK_feet|a_knot",
                "|foot_l_IK_feet|b_knot"]
        self.assertEqual(
            builder.foreign_knots_inside(self.DOOMED, [], made),
            ["|foot_l_IK_feet|a_knot", "|foot_l_IK_feet|b_knot"])


if __name__ == "__main__":
    unittest.main()
