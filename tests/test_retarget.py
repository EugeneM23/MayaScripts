import unittest

import maya_retarget as mr

# The real scene, measured 2026-08-15. Suit joints under Mesh_protective_suit:root.
SUIT = [
    "ik_foot_root", "ik_foot_l", "ik_foot_r",
    "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r",
    "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head",
    "thigh_l", "thigh_twist_01_l", "calf_l", "calf_twist_01_l", "foot_l", "ball_l",
    "thigh_r", "thigh_twist_01_r", "calf_r", "calf_twist_01_r", "foot_r", "ball_r",
    "clavicle_l", "upperarm_l", "upperarm_twist_01_l", "lowerarm_l",
    "lowerarm_twist_01_l", "hand_l",
    "clavicle_r", "upperarm_r", "upperarm_twist_01_r", "lowerarm_r",
    "lowerarm_twist_01_r", "hand_r",
]
for _side in ("l", "r"):
    for _f in ("thumb", "index", "middle", "ring", "pinky"):
        for _i in ("01", "02", "03"):
            SUIT.append("%s_%s_%s" % (_f, _i, _side))

MANNY = SUIT + [
    "root", "camera_root", "camera_bone", "center_of_mass", "interaction",
    "spine_04", "spine_05", "neck_02", "weapon_l", "weapon_r",
    "thigh_twist_02_l", "thigh_twist_02_r", "calf_twist_02_l", "calf_twist_02_r",
    "upperarm_twist_02_l", "upperarm_twist_02_r",
    "lowerarm_twist_02_l", "lowerarm_twist_02_r",
    "index_metacarpal_l", "index_metacarpal_r",
    "middle_metacarpal_l", "middle_metacarpal_r",
    "ring_metacarpal_l", "ring_metacarpal_r",
    "pinky_metacarpal_l", "pinky_metacarpal_r",
]


class TestFixtures(unittest.TestCase):

    def test_the_fixtures_match_the_measured_scene(self):
        self.assertEqual(len(SUIT), 67)
        self.assertEqual(len(MANNY), 93)


class TestIsFinger(unittest.TestCase):

    def test_finger_bones_are_fingers(self):
        for name in ("thumb_01_l", "index_02_r", "middle_03_l",
                     "ring_01_r", "pinky_03_l"):
            self.assertTrue(mr.is_finger(name), name)

    def test_metacarpals_are_not_fingers(self):
        for name in ("index_metacarpal_l", "pinky_metacarpal_r"):
            self.assertFalse(mr.is_finger(name), name)

    def test_body_bones_are_not_fingers(self):
        for name in ("hand_l", "spine_01", "ball_r", "upperarm_twist_01_l"):
            self.assertFalse(mr.is_finger(name), name)


class TestBuildBoneMap(unittest.TestCase):

    def setUp(self):
        self.mapping, self.unmatched = mr.build_bone_map(SUIT, MANNY)

    def test_every_suit_bone_is_matched(self):
        self.assertEqual(self.unmatched, [])

    def test_ik_helpers_are_not_in_the_mapping(self):
        for name in mr.IK_HELPERS:
            self.assertNotIn(name, self.mapping)

    def test_mapping_covers_the_sixty_body_joints(self):
        self.assertEqual(len(self.mapping), 60)

    def test_spine_uses_the_semantic_map_not_the_name(self):
        self.assertEqual(self.mapping["spine_01"][0], "spine_02")
        self.assertEqual(self.mapping["spine_02"][0], "spine_04")
        self.assertEqual(self.mapping["spine_03"][0], "spine_05")

    def test_non_spine_bones_map_to_their_name_twin(self):
        for name in ("pelvis", "head", "hand_l", "ball_r", "clavicle_l"):
            self.assertEqual(self.mapping[name][0], name)

    def test_fingers_default_to_absolute(self):
        self.assertEqual(self.mapping["index_01_r"][1], "absolute")
        self.assertEqual(self.mapping["thumb_03_l"][1], "absolute")

    def test_body_bones_are_offset_mode(self):
        for name in ("pelvis", "spine_03", "hand_l", "foot_r"):
            self.assertEqual(self.mapping[name][1], "offset")

    def test_finger_mode_offset_switches_all_thirty_fingers(self):
        mapping, _ = mr.build_bone_map(SUIT, MANNY, finger_mode="offset")
        fingers = [n for n in mapping if mr.is_finger(n)]
        self.assertEqual(len(fingers), 30)
        for name in fingers:
            self.assertEqual(mapping[name][1], "offset")

    def test_an_unmatched_target_is_reported_not_mapped(self):
        mapping, unmatched = mr.build_bone_map(["pelvis", "tail_01"], MANNY)
        self.assertEqual(unmatched, ["tail_01"])
        self.assertNotIn("tail_01", mapping)

    def test_a_missing_spine_twin_is_reported(self):
        mapping, unmatched = mr.build_bone_map(["spine_02"], ["spine_02"])
        self.assertEqual(unmatched, ["spine_02"])

    def test_an_unknown_finger_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            mr.build_bone_map(SUIT, MANNY, finger_mode="sideways")


class TestIkTable(unittest.TestCase):

    def test_ik_driven_pairs_stay_inside_the_suit(self):
        self.assertEqual(mr.IK_DRIVEN, (
            ("ik_foot_l", "foot_l"),
            ("ik_foot_r", "foot_r"),
            ("ik_hand_gun", "hand_r"),
            ("ik_hand_l", "hand_l"),
        ))

    def test_ik_hand_r_is_not_driven_it_inherits(self):
        driven = [name for name, _ in mr.IK_DRIVEN]
        self.assertNotIn("ik_hand_r", driven)
