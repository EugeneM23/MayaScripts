import unittest

from maya_overrig import bodymap, fkcontrols


class TestChains(unittest.TestCase):

    def test_chains_cover_the_body_map_exactly_once(self):
        chained = [j for _, chain in fkcontrols.CHAINS for j in chain]
        self.assertEqual(len(chained), len(set(chained)))
        self.assertEqual(set(chained), {b.joint for b in bodymap.BUTTONS})

    def test_root_is_a_single_knot_chain(self):
        table = dict(fkcontrols.CHAINS)
        self.assertEqual(table["root"], ("root",))

    def test_pelvis_is_its_own_single_knot_chain(self):
        """The pelvis controller must survive a spine switch untouched, so
        it cannot share a chain (and a manifest) with the spine."""
        table = dict(fkcontrols.CHAINS)
        self.assertEqual(table["pelvis"], ("pelvis",))

    def test_eighteen_chains(self):
        self.assertEqual(len(fkcontrols.CHAINS), 18)

    def test_chain_names_are_unique(self):
        names = [name for name, _ in fkcontrols.CHAINS]
        self.assertEqual(len(names), len(set(names)))

    def test_spine_chain_is_the_five_spine_bones(self):
        table = dict(fkcontrols.CHAINS)
        self.assertEqual(table["spine"],
                         ("spine_01", "spine_02", "spine_03",
                          "spine_04", "spine_05"))

    def test_leg_chains_include_the_ball(self):
        table = dict(fkcontrols.CHAINS)
        self.assertEqual(table["leg_l"][-1], "ball_l")
        self.assertEqual(table["leg_r"][-1], "ball_r")


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


class TestChainSet(unittest.TestCase):

    def test_name_is_prefixed(self):
        self.assertEqual(fkcontrols.chain_set("arm_l"), "RigPicker_fk_arm_l")

    def test_distinct_per_chain(self):
        names = {fkcontrols.chain_set(name) for name, _ in fkcontrols.CHAINS}
        self.assertEqual(len(names), len(fkcontrols.CHAINS))

    def test_differs_from_the_legacy_flat_set(self):
        for name, _ in fkcontrols.CHAINS:
            self.assertNotEqual(fkcontrols.chain_set(name), fkcontrols.FK_SET)


class TestFingerChainsFor(unittest.TestCase):

    def test_left_arm_owns_five_finger_chains(self):
        found = fkcontrols.finger_chains_for("arm_l")
        self.assertEqual(sorted(found),
                         ["index_l", "middle_l", "pinky_l", "ring_l",
                          "thumb_l"])

    def test_right_arm_owns_the_right_side(self):
        found = fkcontrols.finger_chains_for("arm_r")
        self.assertTrue(all(c.endswith("_r") for c in found))
        self.assertEqual(len(found), 5)

    def test_legs_own_nothing(self):
        self.assertEqual(fkcontrols.finger_chains_for("leg_l"), [])
        self.assertEqual(fkcontrols.finger_chains_for("leg_r"), [])

    def test_unknown_limb_owns_nothing(self):
        self.assertEqual(fkcontrols.finger_chains_for("spine"), [])


class TestSwitchable(unittest.TestCase):

    def test_limbs_plus_spine(self):
        self.assertEqual(fkcontrols.SWITCHABLE,
                         ("arm_l", "arm_r", "leg_l", "leg_r", "spine"))

    def test_starts_with_the_limb_chains(self):
        self.assertEqual(fkcontrols.SWITCHABLE[:len(fkcontrols.LIMB_CHAINS)],
                         fkcontrols.LIMB_CHAINS)


class TestDependentChains(unittest.TestCase):

    def test_finds_chains_rooted_inside_the_containers(self):
        ctrls = {"neck": "|spine_05_FK_ctrl|neck_01_FK_ctrl",
                 "arm_l": "|spine_05_FK_ctrl|clavicle_l_FK_ctrl",
                 "leg_l": "|pelvis_FK_ctrl|thigh_l_FK_ctrl",
                 "arm_r": "|clavicle_r_FK_ctrl"}
        found = fkcontrols.dependent_chains(
            ctrls, ["|spine_05_FK_ctrl", "|pelvis_FK_ctrl"])
        self.assertEqual(found, ["neck", "arm_l", "leg_l"])

    def test_results_come_back_in_chain_table_order(self):
        ctrls = {"leg_r": "|pelvis_FK_ctrl|thigh_r_FK_ctrl",
                 "neck": "|spine_05_FK_ctrl|neck_01_FK_ctrl"}
        found = fkcontrols.dependent_chains(
            ctrls, ["|spine_05_FK_ctrl", "|pelvis_FK_ctrl"])
        self.assertEqual(found, ["neck", "leg_r"])

    def test_separator_matters(self):
        """`|spine_05_FK_ctrl_extra` is a different node, not a container."""
        ctrls = {"neck": "|spine_05_FK_ctrl_extra|neck_01_FK_ctrl"}
        self.assertEqual(
            fkcontrols.dependent_chains(ctrls, ["|spine_05_FK_ctrl"]), [])

    def test_a_container_itself_is_not_its_own_dependent(self):
        ctrls = {"spine": "|spine_top_gr|pelvis_FK_ctrl"}
        self.assertEqual(
            fkcontrols.dependent_chains(ctrls, ["|spine_top_gr"]), ["spine"])

    def test_missing_controllers_are_skipped(self):
        self.assertEqual(fkcontrols.dependent_chains({}, ["|x"]), [])

    def test_none_controller_is_skipped(self):
        self.assertEqual(
            fkcontrols.dependent_chains({"neck": None}, ["|x"]), [])


class TestHybridFkChains(unittest.TestCase):

    def test_everything_but_the_switchable_limbs(self):
        names = [name for name, _ in fkcontrols.CHAINS]
        expected = tuple(n for n in names
                         if n not in fkcontrols.LIMB_CHAINS)
        self.assertEqual(fkcontrols.HYBRID_FK_CHAINS, expected)

    def test_torso_and_fingers_stay_fk(self):
        self.assertIn("root", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("pelvis", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("spine", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("neck", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("index_l", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("thumb_r", fkcontrols.HYBRID_FK_CHAINS)

    def test_no_limb_chain_slips_in(self):
        for name in fkcontrols.LIMB_CHAINS:
            self.assertNotIn(name, fkcontrols.HYBRID_FK_CHAINS)

    def test_fourteen_chains(self):
        """18 chains minus the four IK limbs."""
        self.assertEqual(len(fkcontrols.HYBRID_FK_CHAINS), 14)


class TestSwitchableBones(unittest.TestCase):

    def test_every_switchable_chain_bone_resolves(self):
        scene_map = {j: "|rig|" + j for _, chain in fkcontrols.CHAINS
                     for j in chain}
        owner = fkcontrols.switchable_bones(scene_map)
        self.assertEqual(owner["|rig|clavicle_l"], "arm_l")
        self.assertEqual(owner["|rig|calf_r"], "leg_r")
        self.assertEqual(owner["|rig|ball_l"], "leg_l")
        self.assertEqual(owner["|rig|spine_02"], "spine")

    def test_non_switchable_bones_stay_out(self):
        scene_map = {j: "|rig|" + j for _, chain in fkcontrols.CHAINS
                     for j in chain}
        owner = fkcontrols.switchable_bones(scene_map)
        self.assertNotIn("|rig|pelvis", owner)
        self.assertNotIn("|rig|head", owner)
        self.assertNotIn("|rig|index_01_l", owner)

    def test_missing_joints_are_skipped(self):
        self.assertEqual(fkcontrols.switchable_bones({}), {})


class TestInnermostOwner(unittest.TestCase):
    """The bug this guards: FK controllers nest, so 'descendant of any
    member' resolved a hand-controller click into root, pelvis, spine AND
    the arm at once -- and Bake+Delete wiped the whole FK rig."""

    CANDIDATES = [
        ("|root_FK_ctrl", "fk", "root"),
        ("|root_FK_ctrl|pelvis_FK_ctrl", "fk", "pelvis"),
        ("|root_FK_ctrl|pelvis_FK_ctrl|spine_01_FK_ctrl", "fk", "spine"),
        ("|root_FK_ctrl|pelvis_FK_ctrl|spine_01_FK_ctrl|spine_05_FK_ctrl"
         "|clavicle_l_FK_ctrl", "fk", "arm_l"),
        ("|hand_l_IK_feet", "ik", "arm_l"),
        ("|hand_l_IK_feet|arm_l_IK_anchor|index_metacarpal_l_FK_ctrl",
         "fk", "index_l"),
    ]

    def test_deep_arm_controller_resolves_to_the_arm_only(self):
        node = ("|root_FK_ctrl|pelvis_FK_ctrl|spine_01_FK_ctrl"
                "|spine_05_FK_ctrl|clavicle_l_FK_ctrl|upperarm_l_FK_ctrl")
        self.assertEqual(fkcontrols.innermost_owner(node, self.CANDIDATES),
                         ("fk", "arm_l"))

    def test_spine_controller_resolves_to_the_spine(self):
        node = "|root_FK_ctrl|pelvis_FK_ctrl|spine_01_FK_ctrl|spine_03_FK_ctrl"
        self.assertEqual(fkcontrols.innermost_owner(node, self.CANDIDATES),
                         ("fk", "spine"))

    def test_finger_inside_the_ik_anchor_is_the_finger_not_the_arm(self):
        node = ("|hand_l_IK_feet|arm_l_IK_anchor|index_metacarpal_l_FK_ctrl"
                "|index_01_l_FK_ctrl")
        self.assertEqual(fkcontrols.innermost_owner(node, self.CANDIDATES),
                         ("fk", "index_l"))

    def test_ik_control_resolves_to_the_ik_limb(self):
        self.assertEqual(
            fkcontrols.innermost_owner("|hand_l_IK_feet|hand_l_IK_feetShape",
                                       self.CANDIDATES),
            ("ik", "arm_l"))

    def test_unrelated_node_resolves_to_nothing(self):
        self.assertIsNone(fkcontrols.innermost_owner("|persp",
                                                     self.CANDIDATES))


class TestResolveChains(unittest.TestCase):

    BONES = {"|rig|neck_01": "neck", "|rig|spine_03": "spine"}
    MEMBERS = {"neck": ["|neck_01_FK_ctrl"],
               "index_l": ["|hand_l_FK_ctrl|index_metacarpal_l_FK_ctrl"]}

    def test_bone_resolves_its_chain(self):
        self.assertEqual(
            fkcontrols.resolve_chains(["|rig|spine_03"], self.MEMBERS,
                                      self.BONES),
            ["spine"])

    def test_member_and_descendant_resolve(self):
        found = fkcontrols.resolve_chains(
            ["|neck_01_FK_ctrl|neck_01_FK_ctrlShape",
             "|hand_l_FK_ctrl|index_metacarpal_l_FK_ctrl"],
            self.MEMBERS, self.BONES)
        self.assertEqual(found, ["neck", "index_l"])

    def test_results_in_chain_table_order(self):
        found = fkcontrols.resolve_chains(
            ["|hand_l_FK_ctrl|index_metacarpal_l_FK_ctrl", "|rig|neck_01"],
            self.MEMBERS, self.BONES)
        self.assertEqual(found, ["neck", "index_l"])

    def test_unrelated_nodes_resolve_nothing(self):
        self.assertEqual(
            fkcontrols.resolve_chains(["|persp"], self.MEMBERS, self.BONES),
            [])


class TestSpineRehang(unittest.TestCase):

    def test_only_the_chest_re_hangs(self):
        """The pelvis keeps its own FK controller through a spine switch, so
        the thigh chains never move; only chains on spine_05 re-hang, onto
        the top IK node."""
        self.assertEqual(fkcontrols.SPINE_REHANG, {"spine_05": "end"})


class TestSpineDependentChains(unittest.TestCase):
    """The bug this guards: dependent_chains alone catches every chain whose
    controller sits ANYWHERE inside the spine containers -- including finger
    chains riding inside an FK arm. Lifting those to world detached them from
    the hand: moving the spine IK moved everything except the fingers."""

    PARENT_OF = {
        "root": None, "pelvis": "root",
        "spine_01": "pelvis", "spine_02": "spine_01", "spine_03": "spine_02",
        "spine_04": "spine_03", "spine_05": "spine_04",
        "neck_01": "spine_05", "clavicle_l": "spine_05",
        "upperarm_l": "clavicle_l", "lowerarm_l": "upperarm_l",
        "hand_l": "lowerarm_l", "index_metacarpal_l": "hand_l",
        "thigh_l": "pelvis",
    }

    CTRLS = {
        "neck": "|spine_01_FK_ctrl|spine_05_FK_ctrl|neck_01_FK_ctrl",
        "arm_l": "|spine_01_FK_ctrl|spine_05_FK_ctrl|clavicle_l_FK_ctrl",
        "index_l": "|spine_01_FK_ctrl|spine_05_FK_ctrl|clavicle_l_FK_ctrl"
                   "|hand_l_FK_ctrl|index_metacarpal_l_FK_ctrl",
        "leg_l": "|pelvis_FK_ctrl|thigh_l_FK_ctrl",
    }

    def find(self, containers):
        targeted = set(self.PARENT_OF)
        return fkcontrols.spine_dependent_chains(
            self.CTRLS, containers, self.PARENT_OF, targeted)

    def test_chest_chains_are_lifted(self):
        found = self.find(["|spine_01_FK_ctrl"])
        self.assertIn("neck", found)
        self.assertIn("arm_l", found)

    def test_fingers_ride_their_arm_and_are_left_alone(self):
        found = self.find(["|spine_01_FK_ctrl"])
        self.assertNotIn("index_l", found)

    def test_thighs_stay_on_the_pelvis_controller(self):
        found = self.find(["|spine_01_FK_ctrl", "|pelvis_FK_ctrl"])
        self.assertNotIn("leg_l", found)

    def test_nothing_inside_no_containers(self):
        self.assertEqual(self.find(["|elsewhere"]), [])


class TestAttachParent(unittest.TestCase):

    PARENT_OF = {
        "root": None,
        "pelvis": "root",
        "spine_05": "spine_04",
        "clavicle_l": "spine_05",
        "thigh_l": "pelvis",
        "index_metacarpal_l": "hand_l",
        "neck_01": "spine_05",
        "oddball": "some_twist",
        "some_twist": "spine_05",
    }
    TARGETED = {"root", "pelvis", "spine_05", "hand_l", "clavicle_l",
                "thigh_l", "neck_01", "index_metacarpal_l"}

    def find(self, joint):
        return fkcontrols.attach_parent(joint, self.PARENT_OF, self.TARGETED)

    def test_arm_hangs_from_the_spine_top(self):
        self.assertEqual(self.find("clavicle_l"), "spine_05")

    def test_leg_hangs_from_the_pelvis(self):
        self.assertEqual(self.find("thigh_l"), "pelvis")

    def test_finger_hangs_from_the_hand(self):
        self.assertEqual(self.find("index_metacarpal_l"), "hand_l")

    def test_spine_hangs_from_root(self):
        self.assertEqual(self.find("pelvis"), "root")

    def test_root_hangs_from_nothing(self):
        self.assertIsNone(self.find("root"))

    def test_walks_through_untargeted_ancestors(self):
        self.assertEqual(self.find("oddball"), "spine_05")


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


class TestApplySizeRules(unittest.TestCase):

    def test_spine_05_borrows_from_its_neighbour(self):
        """It measures ~4 in a 16-wide chest, which buries it in the geometry."""
        found = fkcontrols.apply_size_rules({"spine_05": 3.9, "spine_04": 16.3})
        self.assertGreater(found["spine_05"], 16.3)

    def test_feet_are_halved(self):
        found = fkcontrols.apply_size_rules({"foot_l": 12.3, "foot_r": 12.3})
        self.assertAlmostEqual(found["foot_l"], 6.15, places=6)
        self.assertAlmostEqual(found["foot_r"], 6.15, places=6)

    def test_untouched_joints_pass_through(self):
        found = fkcontrols.apply_size_rules({"hand_l": 5.5, "pelvis": 15.9})
        self.assertEqual(found["hand_l"], 5.5)
        self.assertEqual(found["pelvis"], 15.9)

    def test_borrowing_uses_the_measured_value_not_a_corrected_one(self):
        """Rules must not chain, or one correction would feed another."""
        found = fkcontrols.apply_size_rules({"spine_05": 3.9, "spine_04": 10.0,
                                             "foot_l": 12.0})
        self.assertAlmostEqual(found["spine_05"], 10.5, places=6)

    def test_missing_source_leaves_the_joint_alone(self):
        found = fkcontrols.apply_size_rules({"spine_05": 3.9})
        self.assertEqual(found["spine_05"], 3.9)

    def test_the_input_is_not_mutated(self):
        original = {"foot_l": 12.0}
        fkcontrols.apply_size_rules(original)
        self.assertEqual(original["foot_l"], 12.0)

    def test_empty_input(self):
        self.assertEqual(fkcontrols.apply_size_rules({}), {})


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


class TestMergeKeyTimes(unittest.TestCase):

    def test_union_of_channels_sorted(self):
        self.assertEqual(
            fkcontrols.merge_key_times([[3.0, 1.0], [2.0], [1.0]]),
            [1.0, 2.0, 3.0])

    def test_duplicates_collapse(self):
        self.assertEqual(
            fkcontrols.merge_key_times([[1.0, 2.0], [1.0, 2.0]]),
            [1.0, 2.0])

    def test_empty_channels_are_skipped(self):
        self.assertEqual(fkcontrols.merge_key_times([[], None, [5.0]]), [5.0])

    def test_no_keys_at_all(self):
        self.assertEqual(fkcontrols.merge_key_times([None, None]), [])


class TestIsSquare(unittest.TestCase):

    def test_pelvis_draws_as_a_square(self):
        self.assertTrue(fkcontrols.is_square("pelvis"))

    def test_every_other_bone_stays_a_ring(self):
        for button in bodymap.BUTTONS:
            if button.joint == "pelvis":
                continue
            self.assertFalse(fkcontrols.is_square(button.joint), button.joint)


class TestSquarePoints(unittest.TestCase):

    def test_closed_with_four_corners(self):
        points = fkcontrols.square_points(2.0)
        self.assertEqual(len(points), 5)
        self.assertEqual(points[0], points[-1])
        self.assertEqual(len(set(points)), 4)

    def test_corners_sit_on_the_plane_diagonals(self):
        """Corners at (0, +-r, +-r): sides face the local axes, so on the
        pelvis they run front/back and side to side, not diagonally."""
        radius = 1.5
        corners = set(fkcontrols.square_points(radius)[:4])
        self.assertEqual(corners, {(0.0, radius, radius),
                                   (0.0, radius, -radius),
                                   (0.0, -radius, -radius),
                                   (0.0, -radius, radius)})

    def test_sides_match_the_ring_diameter(self):
        radius = 2.5
        points = fkcontrols.square_points(radius)
        for a, b in zip(points, points[1:]):
            length = sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5
            self.assertAlmostEqual(length, radius * 2.0, places=6)


if __name__ == "__main__":
    unittest.main()
