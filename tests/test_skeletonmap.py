"""maya_skeletonmap: every convention's names onto ours, pure."""

import os
import subprocess
import sys
import unittest

import maya_skeletonmap as sm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skeleton_conventions as fixtures  # noqa: E402


def recognise(convention, with_positions=True, **kwargs):
    rows, expected = fixtures.build(convention)
    paths = fixtures.paths(rows)
    positions = dict((paths[n], pos) for n, _p, pos in rows) if with_positions else None
    result = sm.recognize(list(paths.values()), positions, **kwargs)
    expected = dict((ours, paths[src]) for ours, src in expected.items())
    return result, expected, paths


class TestStdlibOnly(unittest.TestCase):

    def test_imports_no_maya(self):
        script = ("import sys\nimport maya_skeletonmap\n"
                  "print(';'.join(m for m in sys.modules if m.startswith('maya.')"
                  " or m == 'maya' or m.startswith('PySide')))\n")
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "SkeldarAnim")
        result = subprocess.run([sys.executable, "-c", script], cwd=plugin,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")


class TestTokens(unittest.TestCase):

    def test_conventions_come_apart(self):
        self.assertEqual(sm.tokens("mixamorig:LeftUpLeg"), ["left", "up", "leg"])
        self.assertEqual(sm.tokens("Bip001 L UpperArm"), ["bip", "001", "l", "upper", "arm"])
        self.assertEqual(sm.tokens("DEF-upper_arm.L.001"), ["def", "upper", "arm", "l", "001"])
        self.assertEqual(sm.tokens("lShldrBend"), ["l", "shldr", "bend"])
        self.assertEqual(sm.tokens("LHipJoint"), ["l", "hip", "joint"])
        self.assertEqual(sm.tokens("|ns:root|ns:CC_Base_L_Upperarm"),
                         ["cc", "base", "l", "upperarm"])

    def test_parse_reads_side_anywhere(self):
        for name in ("LeftArm", "upperarm_l", "J_Bip_L_UpperArm", "Bip001_L_UpperArm",
                     "DEF-upper_arm.L", "lShldrBend", "arm_stretch.l", "LeftUpperArm"):
            info = sm.parse(name)
            self.assertEqual((info.kind, info.side), ("upperarm", "l"), name)

    def test_twist_roll_end_ik_are_never_mapped(self):
        for name in ("upperarm_twist_01_l", "LeftArmRoll", "HeadTop_End", "ik_hand_gun",
                     "Bip001_L_Toe0Nub", "weapon_r", "camera_root", "lShldrTwist"):
            self.assertEqual(sm.parse(name).kind, "ignore", name)

    def test_character_creator_neck_twists_are_the_neck(self):
        self.assertEqual(sm.parse("CC_Base_NeckTwist01").kind, "neck")

    def test_a_sided_hip_is_an_offset_bone(self):
        self.assertIsNone(sm.parse("LHipJoint").kind)
        self.assertIsNone(sm.parse("DEF-pelvis.L").kind)
        self.assertEqual(sm.parse("CC_Base_Hip").kind, "hips")

    def test_biped_two_digit_finger_numbers(self):
        info = sm.parse("Bip001_L_Finger01", "3dsmax_biped")
        self.assertEqual((info.finger, info.segment), ("thumb", 2))
        info = sm.parse("Bip001_R_Finger2", "3dsmax_biped")
        self.assertEqual((info.finger, info.segment, info.side), ("middle", 1, "r"))

    def test_rigify_numbers_its_spine(self):
        self.assertEqual(sm.parse("DEF-spine", "blender_rigify").kind, "hips")
        self.assertEqual(sm.parse("DEF-spine.003", "blender_rigify").kind, "spine")
        self.assertEqual(sm.parse("DEF-spine.005", "blender_rigify").kind, "neck")
        self.assertEqual(sm.parse("DEF-spine.006", "blender_rigify").kind, "head")

    def test_maya_sanitised_names(self):
        # Maya has no '.' or '-' in a node name: an FBX import writes '_'
        self.assertEqual(sm.parse("DEF_spine_005", "blender_rigify").kind, "neck")
        self.assertEqual(sm.parse("DEF_spine", "blender_rigify").kind, "hips")
        self.assertEqual(sm.convention_of(["|root_x", "|root_x|spine_01_x",
                                           "|root_x|thigh_stretch_l"]), "blender_autorigpro")
        self.assertEqual(sm.convention_of(["|DEF_spine", "|DEF_spine|DEF_thigh_L"]),
                         "blender_rigify")
        rows, _expected = fixtures.build("rigify")
        clean = [(n.replace("-", "_").replace(".", "_"), p and p.replace("-", "_").replace(".", "_"), x)
                 for n, p, x in rows]
        paths = fixtures.paths(clean)
        result = sm.recognize(list(paths.values()),
                              dict((paths[n], pos) for n, _p, pos in clean))
        self.assertEqual(result.refusal, "")
        self.assertEqual(sm.leaf(result.mapping["head"]), "DEF_spine_006")
        self.assertEqual(sm.leaf(result.mapping["neck_02"]), "DEF_spine_005")

    def test_ue_core_by_name_and_not_by_one_shared_name(self):
        ue5 = [n for n, _p, _x in fixtures.build("ue5")[0]]
        self.assertTrue(sm.covers_ue_core(ue5))
        self.assertTrue(sm.covers_ue_core([n for n in ue5 if n != "head"]))   # a 1P clip
        arp = [n.replace(".", "_") for n, _p, _x in fixtures.build("arp")[0]]
        self.assertIn("hand_r", arp)
        self.assertFalse(sm.covers_ue_core(arp))
        self.assertFalse(sm.covers_ue_core([n for n, _p, _x in fixtures.build("daz")[0]]))

    def test_xsens_spine(self):
        for name in ("L5", "L3", "T12", "T8"):
            self.assertEqual(sm.parse(name).kind, "spine")


class TestDistribute(unittest.TestCase):

    def test_mixamo_three_onto_five_is_the_old_rule(self):
        self.assertEqual(sm.distribute("abc", sm.TARGET_SPINE),
                         {"spine_01": "a", "spine_03": "b", "spine_05": "c"})

    def test_more_sources_keep_both_ends(self):
        out = sm.distribute(["s1", "s2", "s3", "s4", "s5", "s6", "s7"], ("A", "B", "C"))
        self.assertEqual(out, {"A": "s1", "B": "s4", "C": "s7"})

    def test_one_neck_onto_two(self):
        self.assertEqual(sm.distribute(["n"], sm.TARGET_NECK), {"neck_01": "n"})

    def test_empty(self):
        self.assertEqual(sm.distribute([], sm.TARGET_NECK), {})


class TestEveryConvention(unittest.TestCase):
    """Each fixture's own expectation: every bone it names, found."""

    def check(self, convention, with_positions=True):
        result, expected, _paths = recognise(convention, with_positions)
        self.assertEqual(result.refusal, "", (convention, result.refusal))
        for ours, src in expected.items():
            self.assertEqual(result.mapping.get(ours), src,
                             "%s: %s -> %s, expected %s" % (convention, ours,
                                                            result.mapping.get(ours), src))
        extra = sorted(set(result.mapping) - set(expected))
        self.assertEqual(extra, [], "%s maps more than it should: %s" % (
            convention, [(k, result.mapping[k]) for k in extra]))
        return result

    def test_each(self):
        names = {"ue5": "unreal_ue5", "ue4": "unreal_ue4", "mixamo": "mixamo",
                 "hik": "motionbuilder_hik", "unity": "unity_mecanim", "vrm": "vrm",
                 "rigify": "blender_rigify", "arp": "blender_autorigpro",
                 "biped": "3dsmax_biped", "cc": "character_creator", "daz": "daz_genesis",
                 "cmu": "cmu_bvh", "xsens": "xsens", "synty": "synty"}
        for convention, label in names.items():
            with self.subTest(convention=convention):
                result = self.check(convention)
                self.assertEqual(result.convention, label)
                self.assertGreaterEqual(result.confidence, 0.99)

    def test_names_alone_without_positions(self):
        for convention in ("ue5", "mixamo", "rigify", "cc", "daz", "synty", "vrm"):
            with self.subTest(convention=convention):
                result, expected, _p = recognise(convention, with_positions=False)
                self.assertEqual(result.refusal, "")
                for ours in sm.CORE:
                    self.assertEqual(result.mapping[ours], expected[ours])

    def test_no_twist_end_or_helper_is_mapped(self):
        for convention in fixtures.CONVENTIONS:
            result, _e, _p = recognise(convention)
            for ours, src in result.mapping.items():
                if ours.startswith(("spine", "neck", "head")):
                    continue                     # Rigify numbers its spine .001...
                for word in ("twist", "Roll", "_End", "Nub", "ik_", ".001"):
                    self.assertNotIn(word, sm.leaf(src), (convention, ours, src))

    def test_biped_centre_of_mass_is_no_root(self):
        result, _e, _p = recognise("biped")
        self.assertNotIn("root", result.mapping)
        self.assertTrue(any("hips' height" in n for n in result.notes))

    def test_biped_hips_is_the_pelvis_though_the_thighs_hang_off_the_spine(self):
        result, _e, paths = recognise("biped")
        self.assertEqual(sm.leaf(result.mapping["pelvis"]), "Bip001_Pelvis")
        self.assertEqual(sm.leaf(result.mapping["clavicle_l"]), "Bip001_L_Clavicle")

    def test_hik_shoulder_is_a_clavicle_synty_shoulder_an_upper_arm(self):
        hik, _e, _p = recognise("hik")
        self.assertEqual(sm.leaf(hik.mapping["clavicle_l"]), "Character1_LeftShoulder")
        synty, _e, _p = recognise("synty")
        self.assertEqual(sm.leaf(synty.mapping["upperarm_l"]), "Shoulder_L")
        self.assertEqual(sm.leaf(synty.mapping["clavicle_l"]), "Clavicle_L")

    def test_chains_carry_the_source_spine(self):
        result, _e, _p = recognise("daz")
        self.assertEqual([sm.leaf(p) for p in result.chains["spine"]],
                         ["abdomenLower", "abdomenUpper", "chestLower", "chestUpper"])
        self.assertEqual([sm.leaf(p) for p in result.chains["neck"]], ["neckLower", "neckUpper"])

    def test_other_spine_targets(self):
        result, _e, _p = recognise("daz", spine_targets=("spine_01", "spine_02", "spine_03",
                                                         "spine_05"))
        self.assertEqual(sm.leaf(result.mapping["spine_05"]), "chestUpper")
        self.assertNotIn("spine_04", result.mapping)


class TestStructural(unittest.TestCase):

    def test_no_names_at_all(self):
        result, expected, _p = recognise("obfuscated")
        self.assertEqual(result.refusal, "", result.refusal)
        self.assertEqual(result.confidence, 0.6)
        for ours in sm.CORE:
            self.assertEqual(result.mapping[ours], expected[ours], ours)

    def test_no_names_and_no_positions_is_refused(self):
        result, _e, _p = recognise("obfuscated", with_positions=False)
        self.assertTrue(result.refusal)
        self.assertIn("Hips", result.refusal + sm.WORDS["pelvis"])

    def test_a_non_humanoid_is_refused_by_name(self):
        rows = [("body", None, (0, 50, 0))]
        rows += [("leg%d" % i, "body", (i * 10, 0, 0)) for i in range(4)]
        rows += [("tail%d" % i, "body" if i == 0 else "tail%d" % (i - 1), (0, 50, -10 * i))
                 for i in range(1, 6)]
        paths = fixtures.paths(rows)
        positions = dict((paths[n], pos) for n, _p, pos in rows)
        result = sm.recognize(list(paths.values()), positions)
        self.assertTrue(result.refusal)
        self.assertIn("no ", result.refusal)


class TestRestChoice(unittest.TestCase):

    def positions(self, convention, pose=None):
        result, _e, paths = recognise(convention)
        rows = dict((paths[n], pos) for n, _p, pos in fixtures.build(convention)[0])
        return dict((ours, rows[src]) for ours, src in result.mapping.items())

    def test_same_pose_scores_zero_and_is_facing_blind(self):
        ours = self.positions("ue5")
        self.assertAlmostEqual(sm.rest_score(ours, ours), 0.0, places=4)
        turned = dict((k, (-v[2], v[1], v[0])) for k, v in ours.items())   # 90 deg about Y
        self.assertAlmostEqual(sm.rest_score(ours, turned), 0.0, places=4)

    def test_t_pose_against_an_a_pose_scores_the_arm(self):
        a_pose = self.positions("ue5")
        t_pose = self.positions("mixamo")
        score = sm.rest_score(a_pose, t_pose)
        self.assertGreater(score, 4 * 40.0)

    def test_choose_rest_takes_the_closest(self):
        a_pose = self.positions("ue5")
        name, scores = sm.choose_rest({"jointOrient": self.positions("mixamo"),
                                       "firstFrame": a_pose}, a_pose)
        self.assertEqual(name, "firstFrame")
        self.assertLess(scores["firstFrame"], scores["jointOrient"])

    def test_canonical_parents(self):
        result, _e, paths = recognise("cmu")
        parents = sm.parent_map(list(paths.values()))
        canon = sm.canonical_parents(result.mapping, parents)
        self.assertEqual(canon["thigh_l"], "pelvis")        # past LHipJoint
        self.assertEqual(canon["hand_l"], "lowerarm_l")
        self.assertEqual(canon["index_01_l"], "index_metacarpal_l")

    def test_scale_ratio(self):
        self.assertAlmostEqual(sm.scale_ratio(96.0, 0.96), 100.0)
        self.assertEqual(sm.scale_ratio(96.0, 0.0), 1.0)


if __name__ == "__main__":
    unittest.main()
