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


def synthetic_points(template, transform=None):
    """A minimal point cloud whose landmarks equal the template's own:
    ground and crown on the midline, a little cluster around each arm tip.
    `transform` maps every point (fit inputs are plain world positions)."""
    lm = template["landmarks"]
    pts = [
        [0.0, lm["ground_y"], 0.0],
        [0.0, lm["ground_y"] + lm["height"], 5.0],
        [2.0, lm["ground_y"] + lm["height"] * 0.5, 0.0],
    ]
    for tip in (lm["tip_l"], lm["tip_r"]):
        for dy in (-0.5, 0.0, 0.5):
            pts.append([tip[0], tip[1] + dy, tip[2]])
    if transform:
        pts = [transform(p) for p in pts]
    return pts


class TestMeshLandmarks(unittest.TestCase):

    def test_reproduces_the_template_landmarks_on_the_synthetic_cloud(self):
        t = template()
        lm = sf.mesh_landmarks(synthetic_points(t))
        self.assertAlmostEqual(lm["ground_y"], t["landmarks"]["ground_y"], 6)
        self.assertAlmostEqual(lm["height"], t["landmarks"]["height"], 6)
        for axis in range(3):
            self.assertAlmostEqual(lm["tip_l"][axis],
                                   t["landmarks"]["tip_l"][axis], 4)
            self.assertAlmostEqual(lm["tip_r"][axis],
                                   t["landmarks"]["tip_r"][axis], 4)


class TestSwing(unittest.TestCase):

    def test_maps_u_onto_v(self):
        q = sf.swing_quat([1, 0, 0], [0, 1, 0])
        got = sf.rotate_about([2, 0, 0], [0, 0, 0], q)
        for a, b in zip(got, [0, 2, 0]):
            self.assertAlmostEqual(a, b, 9)

    def test_parallel_is_identity(self):
        q = sf.swing_quat([0, 3, 0], [0, 1, 0])
        got = sf.rotate_about([1, 2, 3], [0, 0, 0], q)
        for a, b in zip(got, [1, 2, 3]):
            self.assertAlmostEqual(a, b, 9)

    def test_antiparallel_still_maps_u_onto_v(self):
        q = sf.swing_quat([1, 0, 0], [-1, 0, 0])
        got = sf.rotate_about([5, 0, 0], [0, 0, 0], q)
        for a, b in zip(got, [-5, 0, 0]):
            self.assertAlmostEqual(a, b, 6)

    def test_rotation_is_about_the_pivot(self):
        q = sf.swing_quat([1, 0, 0], [0, 0, 1])
        got = sf.rotate_about([11, 0, 0], [10, 0, 0], q)
        for a, b in zip(got, [10, 0, 1]):
            self.assertAlmostEqual(a, b, 9)


class TestFitPositions(unittest.TestCase):

    def test_identity_on_the_templates_own_landmarks(self):
        t = template()
        positions, notes, scale = sf.fit_positions(t, synthetic_points(t))
        self.assertAlmostEqual(scale, 1.0, 6)
        for j in t["joints"]:
            for a, b in zip(positions[j["name"]], j["world_position"]):
                self.assertAlmostEqual(a, b, delta=0.05, msg=j["name"])

    def test_half_size_cloud_halves_every_position(self):
        t = template()
        pts = synthetic_points(t, lambda p: [c * 0.5 for c in p])
        positions, notes, scale = sf.fit_positions(t, pts)
        self.assertAlmostEqual(scale, 0.5, 6)
        for j in t["joints"]:
            for a, b in zip(positions[j["name"]], j["world_position"]):
                self.assertAlmostEqual(a, b * 0.5, delta=0.05, msg=j["name"])

    def test_t_pose_tips_swing_the_arm_chain_rigidly(self):
        t = template()
        jm = sf.joint_map(t)
        shoulder = jm["upperarm_l"]["world_position"]
        tip = t["landmarks"]["tip_l"]
        reach = math.dist(shoulder, tip)

        def to_t_pose(p):
            if p[0] > 40:  # the left tip cluster
                return [shoulder[0] + reach, p[1] - tip[1] + shoulder[1], shoulder[2]]
            if p[0] < -40:
                return [-(shoulder[0] + reach), p[1] - tip[1] + shoulder[1], shoulder[2]]
            return p

        positions, notes, scale = sf.fit_positions(
            t, synthetic_points(t, to_t_pose))
        # the shoulder itself stays, the hand comes up to shoulder height
        for a, b in zip(positions["upperarm_l"], shoulder):
            self.assertAlmostEqual(a, b, delta=0.01)
        self.assertAlmostEqual(positions["hand_l"][1],
                               shoulder[1], delta=6.0)
        # rigid: bone lengths inside the chain survive the swing
        for child, parent in (("lowerarm_l", "upperarm_l"),
                              ("hand_l", "lowerarm_l"),
                              ("middle_01_l", "middle_metacarpal_l")):
            self.assertAlmostEqual(
                math.dist(positions[child], positions[parent]),
                math.dist(jm[child]["world_position"],
                          jm[parent]["world_position"]), delta=0.01)

    def test_output_is_exactly_symmetric_even_off_symmetric_input(self):
        t = template()

        def lopsided(p):
            if p[0] > 40:
                return [p[0] + 1.5, p[1] + 2.0, p[2]]
            return p

        positions, notes, scale = sf.fit_positions(
            t, synthetic_points(t, lopsided))
        jm = sf.joint_map(t)
        for j in t["joints"]:
            name = j["name"]
            if name in sf.IK_FOLLOWS:  # they sit ON their target, verbatim
                for a, b in zip(positions[name],
                                positions[sf.IK_FOLLOWS[name]]):
                    self.assertAlmostEqual(a, b, 9, msg=name)
                continue
            if name in sf.ASYMMETRIC:  # attachment points, left alone
                continue
            other = sf.pair_name(name)
            if not other:
                if abs(jm[name]["world_position"][0]) < 0.1:
                    self.assertAlmostEqual(positions[name][0], 0.0, 9)
                continue
            a, b = positions[name], positions[other]
            self.assertAlmostEqual(a[0], -b[0], 9, msg=name)
            self.assertAlmostEqual(a[1], b[1], 9, msg=name)
            self.assertAlmostEqual(a[2], b[2], 9, msg=name)


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
