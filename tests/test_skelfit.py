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


def compose_world(template, channels):
    """World matrices rebuilt from the solver's channels alone -- the same
    product the DAG will consume (rotateAxis and jointOrient are zero off
    root, ssc off), so agreement here is agreement in Maya."""
    import maya.api.OpenMaya as om
    jm = sf.joint_map(template)
    kids = sf.children_map(template)
    worlds = {}
    def euler_matrix(deg):
        return om.MEulerRotation(*[math.radians(v) for v in deg]).asMatrix()

    queue = [j["name"] for j in template["joints"] if j["parent"] is None]
    while queue:
        name = queue.pop(0)
        ch = channels[name]
        # the DAG's local product: rotate * jointOrient (rotateAxis is zero)
        local = euler_matrix(ch["rotate"]) * euler_matrix(jm[name]["jointOrient"])
        tm = om.MTransformationMatrix(local)
        tm.setTranslation(om.MVector(*ch["translate"]), om.MSpace.kTransform)
        local = tm.asMatrix()
        parent = jm[name]["parent"]
        worlds[name] = local * worlds[parent] if parent else local
        queue.extend(kids[name])
    return worlds


def _bend_elbow(t, positions, degrees=40.0):
    """Swing everything below the elbow rigidly, the way the fit itself
    moves chains: by the roll-free minimal rotation (roll about the bone is
    unobservable from positions, so only roll-free rigid motions can keep
    subtree locals exactly)."""
    import maya.api.OpenMaya as om
    jm = sf.joint_map(t)
    elbow = positions["lowerarm_l"]
    u = om.MVector(*[a - b for a, b in zip(jm["hand_l"]["world_position"],
                                           jm["lowerarm_l"]["world_position"])])
    turned = u.rotateBy(om.MQuaternion(math.radians(degrees),
                                       om.MVector(0, 0, 1)))
    quat = sf.swing_quat([u.x, u.y, u.z], [turned.x, turned.y, turned.z])
    for name in sf.arm_chain(t, "l"):
        if name not in ("upperarm_l", "lowerarm_l",
                        "upperarm_twist_01_l", "upperarm_twist_02_l"):
            positions[name] = sf.rotate_about(positions[name], elbow, quat)
    return elbow, quat


class TestSolveChannels(unittest.TestCase):

    def test_identity_positions_reproduce_the_template_channels(self):
        t = template()
        positions = {j["name"]: list(j["world_position"]) for j in t["joints"]}
        channels = sf.solve_channels(t, positions)
        for j in t["joints"]:
            got = channels[j["name"]]
            for a, b in zip(got["translate"], j["translate"]):
                self.assertAlmostEqual(a, b, 4, msg=j["name"])
            # trap 31, full form: the template stores unwound eulers
            # (428 deg on ik_hand_gun) and alternate triples (pelvis);
            # the same ROTATION is what matters, so compare matrices
            import maya.api.OpenMaya as om
            want = om.MEulerRotation(
                *[math.radians(v) for v in j["rotate"]]).asMatrix()
            have = om.MEulerRotation(
                *[math.radians(v) for v in got["rotate"]]).asMatrix()
            for k in range(16):
                self.assertAlmostEqual(have[k], want[k], 5, msg=j["name"])

    def test_channels_compose_back_to_the_fitted_positions(self):
        t = template()
        jm = sf.joint_map(t)
        shoulder = jm["upperarm_l"]["world_position"]
        tip = t["landmarks"]["tip_l"]
        reach = math.dist(shoulder, tip)

        def to_t_pose(p):
            if p[0] > 40:
                return [shoulder[0] + reach, p[1] - tip[1] + shoulder[1], shoulder[2]]
            if p[0] < -40:
                return [-(shoulder[0] + reach), p[1] - tip[1] + shoulder[1], shoulder[2]]
            return p

        positions, _, _ = sf.fit_positions(t, synthetic_points(t, to_t_pose))
        channels = sf.solve_channels(t, positions)
        worlds = compose_world(t, channels)
        for name, want in positions.items():
            got = [worlds[name].getElement(3, axis) for axis in range(3)]
            for a, b in zip(got, want):
                self.assertAlmostEqual(a, b, 6, msg=name)

    def test_swing_carries_the_old_bone_axis_onto_the_new_direction(self):
        import maya.api.OpenMaya as om
        t = template()
        jm = sf.joint_map(t)
        positions = {j["name"]: list(j["world_position"]) for j in t["joints"]}
        elbow, quat = _bend_elbow(t, positions)
        channels = sf.solve_channels(t, positions)
        worlds = compose_world(t, channels)
        # the lowerarm's world frame now aims its old bone axis at the hand
        old_dir = om.MVector(*[a - b for a, b in zip(
            jm["hand_l"]["world_position"], jm["lowerarm_l"]["world_position"])])
        local = old_dir * om.MMatrix(jm["lowerarm_l"]["world_matrix"]).inverse()
        new_dir = (local * worlds["lowerarm_l"]).normal()
        want = om.MVector(*[a - b for a, b in zip(
            positions["hand_l"], positions["lowerarm_l"])]).normal()
        for axis in range(3):
            self.assertAlmostEqual(new_dir[axis], want[axis], 6)

    def test_rigid_subtree_keeps_its_template_locals(self):
        t = template()
        positions = {j["name"]: list(j["world_position"]) for j in t["joints"]}
        _bend_elbow(t, positions)
        channels = sf.solve_channels(t, positions)
        jm = sf.joint_map(t)
        import maya.api.OpenMaya as om
        for name in ("middle_01_l", "middle_02_l", "thumb_02_l", "pinky_03_l"):
            want = om.MEulerRotation(
                *[math.radians(v) for v in jm[name]["rotate"]]).asMatrix()
            have = om.MEulerRotation(
                *[math.radians(v) for v in channels[name]["rotate"]]).asMatrix()
            for k in range(16):
                self.assertAlmostEqual(have[k], want[k], 5, msg=name)


class TestChooseMesh(unittest.TestCase):

    def test_the_selection_wins(self):
        name, reason = sf.choose_mesh(["|Sword"], ["|Sword", "|Body"])
        self.assertEqual(name, "|Sword")

    def test_two_selected_meshes_are_refused(self):
        name, reason = sf.choose_mesh(["|A", "|B"], ["|A", "|B"])
        self.assertIsNone(name)
        self.assertIn("ONE", reason)

    def test_a_lone_scene_mesh_answers_with_no_selection(self):
        name, reason = sf.choose_mesh([], ["|Body"])
        self.assertEqual(name, "|Body")

    def test_two_scene_meshes_and_no_selection_is_refused(self):
        name, reason = sf.choose_mesh([], ["|A", "|B"])
        self.assertIsNone(name)

    def test_an_empty_scene_is_refused(self):
        name, reason = sf.choose_mesh([], [])
        self.assertIsNone(name)


class TestFinalizePositions(unittest.TestCase):

    def _current(self, t):
        return {j["name"]: list(j["world_position"]) for j in t["joints"]}

    def test_the_edited_side_is_the_one_that_moved(self):
        t = template()
        reference = self._current(t)
        current = self._current(t)
        current["hand_l"][1] += 7.0
        side, moved = sf.edited_side(reference, current)
        self.assertEqual(side, "l")
        self.assertAlmostEqual(moved, 7.0, 6)

    def test_mirror_copies_the_edited_side_onto_the_other(self):
        t = template()
        current = self._current(t)
        current["hand_l"] = [40.0, 110.0, 20.0]
        result = sf.finalize_positions(t, current, "l")
        self.assertEqual(result["hand_l"], [40.0, 110.0, 20.0])
        self.assertEqual(result["hand_r"], [-40.0, 110.0, 20.0])

    def test_midline_joints_snap_to_x_zero_keeping_their_edits(self):
        t = template()
        current = self._current(t)
        current["spine_03"] = [1.5, 120.0, 3.0]
        result = sf.finalize_positions(t, current, "l")
        self.assertEqual(result["spine_03"], [0.0, 120.0, 3.0])

    def test_ik_followers_land_on_their_targets(self):
        t = template()
        current = self._current(t)
        current["hand_l"] = [40.0, 110.0, 20.0]
        result = sf.finalize_positions(t, current, "l")
        self.assertEqual(result["ik_hand_l"], result["hand_l"])
        self.assertEqual(result["ik_hand_gun"], result["hand_r"])

    def test_weapons_are_left_exactly_where_they_are(self):
        t = template()
        current = self._current(t)
        current["weapon_r"] = [-40.0, 100.0, 25.0]
        result = sf.finalize_positions(t, current, "r")
        self.assertEqual(result["weapon_r"], [-40.0, 100.0, 25.0])
        jm = sf.joint_map(t)
        self.assertEqual(result["weapon_l"], jm["weapon_l"]["world_position"])


class TestPoses(unittest.TestCase):

    def test_every_pose_names_real_template_joints(self):
        names = {j["name"] for j in template()["joints"]}
        for pose, deltas in sf.POSES.items():
            for joint, delta in deltas.items():
                self.assertIn(joint, names, msg=pose)
                self.assertEqual(len(delta), 3, msg=pose)

    def test_poses_touch_only_weighted_or_parent_bones(self):
        """A pose on a bone nothing is weighted to (ik_*, camera_*) would
        show nothing and read as a broken skin."""
        t = template()
        allowed = set(sf.bind_influences(t)) | {"upperarm_l", "upperarm_r",
                                                "thigh_l", "thigh_r",
                                                "spine_05"}
        for pose, deltas in sf.POSES.items():
            for joint in deltas:
                self.assertIn(joint, allowed, msg=pose)


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
