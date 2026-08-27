import copy
import json
import math
import unittest

import maya_skelfit as sf


def template():
    """The real committed template -- it is data, like bodymap's table."""
    if not hasattr(template, "_cache"):
        template._cache = sf.load_template()
    return copy.deepcopy(template._cache)


class TestLoadTemplate(unittest.TestCase):

    def test_loads_93_joints_with_single_root(self):
        t = template()
        self.assertEqual(len(t["joints"]), 93)
        roots = [j for j in t["joints"] if j["parent"] is None]
        self.assertEqual([j["name"] for j in roots], ["root"])

    def test_duplicate_names_are_refused(self):
        t = template()
        t["joints"][5]["name"] = t["joints"][4]["name"]
        with self.assertRaises(ValueError):
            sf.validate_template(t)

    def test_unknown_parent_is_refused(self):
        t = template()
        t["joints"][10]["parent"] = "no_such_bone"
        with self.assertRaises(ValueError):
            sf.validate_template(t)

    def test_missing_channel_key_is_refused(self):
        t = template()
        del t["joints"][3]["rotate"]
        with self.assertRaises(ValueError):
            sf.validate_template(t)


class TestMaps(unittest.TestCase):

    def test_joint_map_indexes_by_name(self):
        m = sf.joint_map(template())
        self.assertEqual(m["pelvis"]["parent"], "root")

    def test_children_of_pelvis(self):
        kids = sf.children_map(template())["pelvis"]
        for name in ("spine_01", "thigh_l", "thigh_r"):
            self.assertIn(name, kids)

    def test_leaf_has_no_children(self):
        kids = sf.children_map(template())
        self.assertEqual(kids.get("thumb_03_l", []), [])


class TestSides(unittest.TestCase):

    def test_side_suffixes(self):
        self.assertEqual(sf.side_of("hand_l"), "l")
        self.assertEqual(sf.side_of("upperarm_twist_01_r"), "r")
        self.assertIsNone(sf.side_of("pelvis"))

    def test_pair_name_swaps_the_suffix(self):
        self.assertEqual(sf.pair_name("hand_l"), "hand_r")
        self.assertEqual(sf.pair_name("ik_foot_r"), "ik_foot_l")
        self.assertIsNone(sf.pair_name("spine_03"))

    def test_every_sided_joint_has_its_pair_in_the_template(self):
        names = {j["name"] for j in template()["joints"]}
        for name in names:
            if sf.side_of(name):
                self.assertIn(sf.pair_name(name), names)

    def test_center_names_have_no_side(self):
        centers = sf.center_names(template())
        self.assertIn("pelvis", centers)
        self.assertIn("spine_03", centers)
        self.assertNotIn("hand_l", centers)


class TestBindInfluences(unittest.TestCase):

    def test_comes_from_the_biggest_mesh_and_matches_manny_reality(self):
        infl = sf.bind_influences(template())
        self.assertEqual(len(infl), 74)
        self.assertIn("thigh_twist_01_l", infl)
        self.assertIn("pelvis", infl)
        # zero-weight in Manny's own skin: the segments ride their twists
        self.assertNotIn("thigh_l", infl)
        self.assertNotIn("upperarm_r", infl)
        self.assertNotIn("ik_foot_l", infl)
        self.assertNotIn("root", infl)


if __name__ == "__main__":
    unittest.main()
