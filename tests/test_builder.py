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


if __name__ == "__main__":
    unittest.main()
