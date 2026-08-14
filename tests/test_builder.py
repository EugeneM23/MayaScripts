import unittest

from maya_overrig import bodymap, builder


class TestLimbTable(unittest.TestCase):

    def test_four_limbs(self):
        self.assertEqual(len(builder.LIMBS), 4)

    def test_names_are_the_picker_regions(self):
        self.assertEqual([name for name, _ in builder.LIMBS],
                         ["arm_l", "arm_r", "leg_l", "leg_r"])

    def test_three_joints_each(self):
        for name, joints in builder.LIMBS:
            self.assertEqual(len(joints), 3, name)

    def test_twelve_distinct_joints(self):
        every = [j for _, joints in builder.LIMBS for j in joints]
        self.assertEqual(len(every), 12)
        self.assertEqual(len(set(every)), 12)

    def test_every_joint_exists_in_the_body_map(self):
        known = {b.joint for b in bodymap.BUTTONS}
        for name, joints in builder.LIMBS:
            for joint in joints:
                self.assertIn(joint, known, "{0}: {1}".format(name, joint))

    def test_order_is_root_middle_end(self):
        table = dict(builder.LIMBS)
        self.assertEqual(table["leg_l"], ("thigh_l", "calf_l", "foot_l"))
        self.assertEqual(table["arm_r"], ("upperarm_r", "lowerarm_r", "hand_r"))


class TestLimbJoints(unittest.TestCase):

    @staticmethod
    def _full_map():
        return {j: "|rig|" + j
                for _, joints in builder.LIMBS for j in joints}

    def test_resolves_all_four_limbs(self):
        resolved = builder.limb_joints(self._full_map())
        self.assertEqual(len(resolved), 4)

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
                         ["arm_l", "arm_r", "leg_l", "leg_r"])


class TestLimbSet(unittest.TestCase):

    def test_name_is_prefixed(self):
        self.assertEqual(builder.limb_set("leg_l"), "RigPicker_build_leg_l")

    def test_every_limb_gets_a_distinct_set(self):
        names = [builder.limb_set(name) for name, _ in builder.LIMBS]
        self.assertEqual(len(set(names)), 4)


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


if __name__ == "__main__":
    unittest.main()
