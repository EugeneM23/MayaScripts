import unittest

from maya_overrig import bodymap, fkcontrols


class TestControllerName(unittest.TestCase):

    def test_suffixes_the_joint(self):
        self.assertEqual(fkcontrols.controller_name("upperarm_l"),
                         "upperarm_l_FK_ctrl")

    def test_names_are_unique_across_the_body_map(self):
        names = {fkcontrols.controller_name(b.joint) for b in bodymap.BUTTONS}
        self.assertEqual(len(names), len(bodymap.BUTTONS))


class TestColourFor(unittest.TestCase):

    def test_left_and_right_differ(self):
        self.assertNotEqual(fkcontrols.colour_for("arm_l"),
                            fkcontrols.colour_for("arm_r"))

    def test_left_regions_share_one_colour(self):
        self.assertEqual(fkcontrols.colour_for("arm_l"),
                         fkcontrols.colour_for("leg_l"))
        self.assertEqual(fkcontrols.colour_for("arm_l"),
                         fkcontrols.colour_for("hand_l"))

    def test_centre_regions_share_one_colour(self):
        self.assertEqual(fkcontrols.colour_for("root"),
                         fkcontrols.colour_for("spine"))
        self.assertEqual(fkcontrols.colour_for("root"),
                         fkcontrols.colour_for("head"))

    def test_every_body_map_region_has_a_colour(self):
        for region in bodymap.REGIONS:
            colour = fkcontrols.colour_for(region)
            self.assertEqual(len(colour), 3, region)
            for channel in colour:
                self.assertGreaterEqual(channel, 0.0)
                self.assertLessEqual(channel, 1.0)


class TestRollup(unittest.TestCase):

    PARENT_OF = {
        "root": None,
        "pelvis": "root",
        "thigh_l": "pelvis",
        "thigh_twist_01_l": "thigh_l",
        "calf_l": "thigh_l",
        "calf_twist_01_l": "calf_l",
        "stray": None,
    }
    TARGETS = {"root", "pelvis", "thigh_l", "calf_l"}

    def roll(self, influences):
        return fkcontrols.rollup(influences, self.TARGETS, self.PARENT_OF)

    def test_targeted_joint_maps_to_itself(self):
        self.assertEqual(self.roll(["calf_l"])["calf_l"], "calf_l")

    def test_twist_maps_to_its_targeted_parent(self):
        """Without this upperarm_l and thigh_l collect no vertices at all."""
        self.assertEqual(self.roll(["thigh_twist_01_l"])["thigh_twist_01_l"],
                         "thigh_l")

    def test_walks_more_than_one_level(self):
        parent_of = dict(self.PARENT_OF)
        parent_of["deep"] = "thigh_twist_01_l"
        found = fkcontrols.rollup(["deep"], self.TARGETS, parent_of)
        self.assertEqual(found["deep"], "thigh_l")

    def test_joint_with_no_targeted_ancestor_maps_to_none(self):
        self.assertIsNone(self.roll(["stray"])["stray"])

    def test_unknown_joint_maps_to_none(self):
        self.assertIsNone(self.roll(["never_heard_of_it"])["never_heard_of_it"])

    def test_every_influence_appears_in_the_result(self):
        influences = ["root", "thigh_twist_01_l", "stray"]
        self.assertEqual(sorted(self.roll(influences)), sorted(influences))


class TestStagger(unittest.TestCase):

    def test_alternates(self):
        self.assertEqual(fkcontrols.stagger(0), 1.0)
        self.assertEqual(fkcontrols.stagger(2), 1.0)
        self.assertNotEqual(fkcontrols.stagger(1), fkcontrols.stagger(0))

    def test_never_grows_a_ring(self):
        for index in range(8):
            self.assertLessEqual(fkcontrols.stagger(index), 1.0)

    def test_stays_visible(self):
        """A stagger that shrank a ring to nothing would defeat the point."""
        for index in range(8):
            self.assertGreater(fkcontrols.stagger(index), 0.5)


class TestRadiusFrom(unittest.TestCase):

    def test_takes_the_percentile_and_applies_the_margin(self):
        distances = [float(n) for n in range(1, 101)]
        found = fkcontrols.radius_from(distances, percentile=0.85, margin=1.0)
        self.assertAlmostEqual(found, 86.0, places=6)

    def test_defaults_stay_below_the_raw_maximum(self):
        """A percentile, not the maximum, so one seam vertex cannot inflate it."""
        distances = [1.0] * 99 + [100.0]
        self.assertLess(fkcontrols.radius_from(distances), 10.0)

    def test_margin_scales_the_result(self):
        distances = [10.0] * 10
        self.assertAlmostEqual(
            fkcontrols.radius_from(distances, margin=1.5), 15.0, places=6)

    def test_single_distance(self):
        self.assertAlmostEqual(
            fkcontrols.radius_from([4.0], margin=1.0), 4.0, places=6)

    def test_empty_input_gives_zero(self):
        self.assertEqual(fkcontrols.radius_from([]), 0.0)

    def test_unsorted_input_is_handled(self):
        self.assertAlmostEqual(
            fkcontrols.radius_from([9.0, 1.0, 5.0], percentile=0.0, margin=1.0),
            1.0, places=6)

    def test_percentile_of_one_takes_the_largest(self):
        self.assertAlmostEqual(
            fkcontrols.radius_from([1.0, 2.0, 9.0], percentile=1.0, margin=1.0),
            9.0, places=6)


if __name__ == "__main__":
    unittest.main()
