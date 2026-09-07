import math
import unittest

import maya.api.OpenMaya as om

import maya_asretarget as ar

# The rig, measured 2026-09-04: 79 deform joints, and these are the controls
# that exist for them.  The sides are the rig's own and NOT symmetric -- the
# midline joints exist as _M only and the limbs as _L/_R only, so a fixture that
# offers all three sides for every base is more symmetric than the skeleton and
# would let a bug through (CLAUDE.md's own lesson, in miniature).
MIDLINE_BASES = ["Spine1", "Spine2", "Spine3", "Spine4", "Spine5",
                 "Neck", "NeckPart1", "Head"]
LIMB_BASES = ["Scapula", "Shoulder", "Elbow", "Wrist", "Hip", "Knee", "Ankle",
              "Toes", "ThumbFinger1", "ThumbFinger2", "ThumbFinger3"]
for _f in ("Index", "Middle", "Ring", "Pinky"):
    for _i in (0, 1, 2, 3):
        LIMB_BASES.append("%sFinger%d" % (_f, _i))

CONTROLS = ["Main", "RootX_M"]
for _b in MIDLINE_BASES:
    CONTROLS.append("FK" + _b + "_M")
for _b in LIMB_BASES:
    for _s in ("_L", "_R"):
        CONTROLS.append("FK" + _b + _s)
for _s in ("_L", "_R"):
    CONTROLS += ["IKArm" + _s, "IKLeg" + _s, "IKToes" + _s,
                 "PoleArm" + _s, "PoleLeg" + _s]

# A full UE5 Manny's leaf names.
BONES = ["root", "pelvis", "neck_01", "neck_02", "head"]
BONES += ["spine_0%d" % i for i in range(1, 6)]
for _s in ("l", "r"):
    BONES += ["clavicle_" + _s, "upperarm_" + _s, "lowerarm_" + _s, "hand_" + _s,
              "thigh_" + _s, "calf_" + _s, "foot_" + _s, "ball_" + _s]
    for _f in ("index", "middle", "ring", "pinky"):
        BONES.append("%s_metacarpal_%s" % (_f, _s))
        BONES += ["%s_0%d_%s" % (_f, i, _s) for i in (1, 2, 3)]
    BONES += ["thumb_0%d_%s" % (i, _s) for i in (1, 2, 3)]


class TestDrivePlan(unittest.TestCase):

    def setUp(self):
        self.drives, self.missing = ar.drive_plan(CONTROLS, BONES)
        self.by_control = dict((d.control, d) for d in self.drives)

    def test_nothing_is_missing_on_a_full_rig_and_a_full_skeleton(self):
        self.assertEqual(self.missing, [])

    def test_every_control_is_driven_once(self):
        self.assertEqual(len(self.by_control), len(self.drives))

    def test_a_twins_fk_controls_take_position_as_well_as_rotation(self):
        # Measured 2026-09-05 on the animator's Longsword clip: a UE5 twin's
        # bones carry TRANSLATION animation (clavicles sliding 3.65 cm, the neck
        # base 3.67, spine_05 2.52, the thighs 0.81 over the take), and a
        # rotation-only drive lost every centimetre of it -- 6.35 cm at the
        # hands.  The same rig's bones are ours to place, so place them.
        d = self.by_control["FKShoulder_L"]
        self.assertEqual((d.bone, d.translate, d.rotate),
                         ("upperarm_l", True, True))
        fk = [d for d in self.drives if d.control.startswith("FK")]
        self.assertEqual(len(fk), 62)
        self.assertTrue(all(d.translate and d.rotate for d in fk))

    def test_the_spine_is_one_to_one(self):
        for i in range(1, 6):
            self.assertEqual(self.by_control["FKSpine%d_M" % i].bone, "spine_0%d" % i)

    def test_the_neck_inbetween_takes_the_second_neck_bone(self):
        self.assertEqual(self.by_control["FKNeckPart1_M"].bone, "neck_02")

    def test_the_metacarpals_are_mapped(self):
        self.assertEqual(self.by_control["FKIndexFinger0_R"].bone, "index_metacarpal_r")

    def test_root_motion_goes_to_main(self):
        d = self.by_control["Main"]
        self.assertEqual((d.bone, d.translate, d.rotate),
                         ("root", True, True))

    def test_the_pelvis_control_is_rootx_and_not_an_fk_control(self):
        d = self.by_control["RootX_M"]
        self.assertEqual((d.bone, d.translate, d.rotate),
                         ("pelvis", True, True))
        self.assertNotIn("FKRoot_M", self.by_control)

    def test_the_ik_ends_take_position_and_rotation(self):
        self.assertEqual(self.by_control["IKLeg_R"].bone, "foot_r")
        for name in ("IKArm_L", "IKLeg_L"):
            d = self.by_control[name]
            self.assertEqual((d.translate, d.rotate), (True, True))

    def test_the_toe_control_takes_rotation_only(self):
        d = self.by_control["IKToes_L"]
        self.assertEqual((d.bone, d.translate, d.rotate),
                         ("ball_l", False, True))

    def test_the_poles_ride_the_upper_bone_by_position(self):
        self.assertEqual(self.by_control["PoleLeg_L"].bone, "thigh_l")
        self.assertEqual(self.by_control["PoleArm_R"].bone, "upperarm_r")
        d = self.by_control["PoleLeg_R"]
        self.assertEqual((d.translate, d.rotate), (True, False))

    def test_the_twist_joints_are_never_driven(self):
        for d in self.drives:
            self.assertNotIn("Part1", d.control.replace("NeckPart1", ""))
            self.assertNotIn("Part2", d.control)
            self.assertNotIn("twist", d.bone)

    def test_a_missing_source_bone_is_reported_and_skipped(self):
        bones = [b for b in BONES if b != "index_metacarpal_l"]
        drives, missing = ar.drive_plan(CONTROLS, bones)
        self.assertEqual(missing, [("FKIndexFinger0_L", "index_metacarpal_l")])
        self.assertNotIn("FKIndexFinger0_L", [d.control for d in drives])

    def test_a_missing_control_is_silently_skipped(self):
        controls = [c for c in CONTROLS if c != "FKNeckPart1_M"]
        drives, missing = ar.drive_plan(controls, BONES)
        self.assertEqual(missing, [])
        self.assertNotIn("FKNeckPart1_M", [d.control for d in drives])

    def test_a_ue4_schema_source_loses_only_what_it_lacks(self):
        # No metacarpals, spine stops at 03, no neck_02: the UE4 mannequin.
        bones = [b for b in BONES
                 if "metacarpal" not in b and b not in ("spine_04", "spine_05", "neck_02")]
        drives, missing = ar.drive_plan(CONTROLS, bones)
        names = [d.control for d in drives]
        self.assertIn("FKSpine3_M", names)
        self.assertNotIn("FKSpine4_M", names)
        self.assertEqual(len(missing), 8 + 2 + 1)


# The animator's Mixamo clip, measured 2026-09-05: 65 joints under
# `mixamorig:Hips`, the side a PREFIX, no metacarpals, three spine joints, one
# neck joint, and a fourth (end) joint on every finger.
MIXAMO_BONES = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "HeadTop_End"]
for _s in ("Left", "Right"):
    MIXAMO_BONES += [_s + n for n in ("UpLeg", "Leg", "Foot", "ToeBase", "Toe_End",
                                      "Shoulder", "Arm", "ForeArm", "Hand")]
    for _f in ("Index", "Middle", "Ring", "Pinky", "Thumb"):
        MIXAMO_BONES += ["%sHand%s%d" % (_s, _f, i) for i in (1, 2, 3, 4)]


class TestSchemas(unittest.TestCase):

    def test_the_fixture_matches_the_measured_clip(self):
        self.assertEqual(len(MIXAMO_BONES), 65)

    def test_a_ue5_side_is_a_suffix_and_a_mixamo_side_a_prefix(self):
        self.assertEqual(ar.bone_name("upperarm", "_l", ar.UE5), "upperarm_l")
        self.assertEqual(ar.bone_name("UpLeg", "Left", ar.MIXAMO), "LeftUpLeg")
        self.assertEqual(ar.bone_name("Hips", "", ar.MIXAMO), "Hips")

    def test_each_schema_is_detected_by_its_own_bones(self):
        self.assertEqual(ar.detect_schema(BONES)[0].name, "ue5")
        self.assertEqual(ar.detect_schema(MIXAMO_BONES)[0].name, "mixamo")

    def test_a_skeleton_that_is_neither_is_refused_rather_than_guessed(self):
        schema, score = ar.detect_schema(["Bip01", "Bip01_Spine", "Bip01_L_Hand"])
        self.assertIsNone(schema)
        self.assertEqual(score, 0)

    def test_the_twin_needs_no_alignment_and_mixamo_does(self):
        self.assertFalse(ar.UE5.align)
        self.assertTrue(ar.MIXAMO.align)
        self.assertEqual(ar.UE5.rest, "live")
        self.assertEqual(ar.MIXAMO.rest, "jointOrient")

    def test_only_mixamo_lacks_a_root_bone(self):
        self.assertEqual(ar.UE5.root_bone, "root")
        self.assertIsNone(ar.MIXAMO.root_bone)

    def test_only_the_ue5_source_is_a_twin_of_our_own_skeleton(self):
        # one fact with two consequences: a twin's FK controls are driven in
        # position, and its position drives keep our sub-millimetre rest offset
        self.assertTrue(ar.UE5.twin)
        self.assertFalse(ar.MIXAMO.twin)
        self.assertTrue(ar.keeps_position("FKScapula_L", ar.UE5))
        self.assertFalse(ar.keeps_position("FKScapula_L", ar.MIXAMO))

    def test_a_pole_always_keeps_its_standoff_whatever_the_schema(self):
        for schema in ar.SCHEMAS:
            self.assertTrue(ar.keeps_position("PoleLeg_L", schema))
        self.assertTrue(ar.keeps_position("IKArm_L", ar.UE5))
        self.assertFalse(ar.keeps_position("IKArm_L", ar.MIXAMO))

    def test_our_own_bone_is_always_the_ue5_one(self):
        ours = ar.our_bone_map()
        self.assertEqual(ours["FKShoulder_L"], "upperarm_l")
        self.assertEqual(ours["IKLeg_R"], "foot_r")
        self.assertEqual(ours["PoleArm_L"], "upperarm_l")
        self.assertEqual(ours["RootX_M"], "pelvis")
        self.assertEqual(ours["Main"], "root")


class TestMixamoPlan(unittest.TestCase):

    def setUp(self):
        self.drives, self.missing = ar.drive_plan(CONTROLS, MIXAMO_BONES, ar.MIXAMO)
        self.by_control = dict((d.control, d) for d in self.drives)

    def test_nothing_is_missing_on_a_full_mixamo_skeleton(self):
        self.assertEqual(self.missing, [])

    def test_the_limbs_map_to_mixamo_names(self):
        self.assertEqual(self.by_control["FKShoulder_L"].bone, "LeftArm")
        self.assertEqual(self.by_control["FKElbow_R"].bone, "RightForeArm")
        self.assertEqual(self.by_control["FKHip_L"].bone, "LeftUpLeg")
        self.assertEqual(self.by_control["FKAnkle_R"].bone, "RightFoot")
        self.assertEqual(self.by_control["FKToes_L"].bone, "LeftToeBase")

    def test_the_three_mixamo_spine_joints_take_ours_1_3_and_5(self):
        self.assertEqual(self.by_control["FKSpine1_M"].bone, "Spine")
        self.assertEqual(self.by_control["FKSpine3_M"].bone, "Spine1")
        self.assertEqual(self.by_control["FKSpine5_M"].bone, "Spine2")
        for gap in ("FKSpine2_M", "FKSpine4_M"):
            self.assertNotIn(gap, self.by_control)

    def test_the_fk_controls_take_rotation_only_because_the_proportions_are_not_ours(self):
        # placing our controls on Mixamo's joints would hand the rig Mixamo's
        # proportions (its arm is 16.5% shorter than ours); a twin gets position
        fk = [d for d in self.drives if d.control.startswith("FK")]
        self.assertTrue(fk)
        self.assertTrue(all(d.rotate and not d.translate for d in fk))

    def test_the_neck_inbetween_is_left_undriven_so_the_neck_smooths_itself(self):
        self.assertEqual(self.by_control["FKNeck_M"].bone, "Neck")
        self.assertEqual(self.by_control["FKHead_M"].bone, "Head")
        self.assertNotIn("FKNeckPart1_M", self.by_control)

    def test_the_metacarpals_are_left_undriven_because_mixamo_has_none(self):
        for control in ("FKIndexFinger0_L", "FKMiddleFinger0_R"):
            self.assertNotIn(control, self.by_control)
        self.assertEqual(self.by_control["FKIndexFinger1_L"].bone, "LeftHandIndex1")
        self.assertEqual(self.by_control["FKThumbFinger3_R"].bone, "RightHandThumb3")

    def test_main_is_not_driven_because_mixamo_has_no_root_bone(self):
        self.assertNotIn("Main", self.by_control)
        self.assertEqual(self.by_control["RootX_M"].bone, "Hips")

    def test_the_ik_ends_and_poles_follow_the_mixamo_names(self):
        self.assertEqual(self.by_control["IKLeg_L"].bone, "LeftFoot")
        self.assertEqual(self.by_control["IKArm_R"].bone, "RightHand")
        self.assertEqual(self.by_control["IKToes_L"].bone, "LeftToeBase")
        self.assertEqual(self.by_control["PoleLeg_R"].bone, "RightUpLeg")
        self.assertEqual(self.by_control["PoleArm_L"].bone, "LeftArm")

    def test_a_clip_without_fingers_loses_only_the_fingers(self):
        bones = [b for b in MIXAMO_BONES if "Hand" not in b or b.endswith("Hand")]
        drives, missing = ar.drive_plan(CONTROLS, bones, ar.MIXAMO)
        self.assertEqual(len(missing), 30)
        self.assertIn("FKWrist_L", [d.control for d in drives])


class TestAlignment(unittest.TestCase):

    IDENT = list(om.MMatrix())

    def matrix(self, x, y, z):
        m = list(om.MMatrix())
        m[12], m[13], m[14] = x, y, z
        return m

    def test_a_rotation_angle_is_read_off_the_matrix(self):
        turn = list(om.MEulerRotation(0.0, 0.0, math.radians(30.0)).asMatrix())
        self.assertAlmostEqual(ar.rotation_angle(turn), 30.0, places=6)
        self.assertAlmostEqual(ar.rotation_angle(self.IDENT), 0.0, places=9)

    def test_a_direction_comes_from_two_rest_positions(self):
        rest = {"a": self.matrix(0, 0, 0), "b": self.matrix(0, 10, 0)}
        self.assertEqual(tuple(round(v, 6) for v in ar.direction(rest, "a", "b")),
                         (0.0, 1.0, 0.0))

    def test_a_zero_length_bone_has_no_direction(self):
        rest = {"a": self.matrix(1, 2, 3), "b": self.matrix(1, 2, 3)}
        self.assertIsNone(ar.direction(rest, "a", "b"))
        self.assertIsNone(ar.direction(rest, "a", "missing"))

    def test_the_alignment_turns_our_direction_onto_the_sources(self):
        ours = om.MVector(1, 0, 0)
        theirs = om.MVector(0, 1, 0)
        turned = ours * om.MMatrix(ar.align_rotation(ours, theirs))
        for got, want in zip((turned.x, turned.y, turned.z), (0.0, 1.0, 0.0)):
            self.assertAlmostEqual(got, want, places=9)

    def test_equal_directions_align_to_the_identity(self):
        v = om.MVector(0.3, -0.9, 0.1).normal()
        self.assertTrue(ar.is_identity(ar.align_rotation(v, v), tol=1e-9))

    def test_depth_and_descent_walk_the_parent_map(self):
        parents = {"root": None, "pelvis": "root", "spine_01": "pelvis",
                   "spine_02": "spine_01"}
        self.assertEqual(ar.depth_of("spine_02", parents), 3)
        self.assertEqual(ar.descends("spine_02", "pelvis", parents), 2)
        self.assertEqual(ar.descends("pelvis", "spine_02", parents), 0)

    def test_a_bone_with_no_mapped_child_inherits_its_parents_alignment(self):
        # our arm hangs down, the source's points sideways: a 90 deg alignment,
        # and the hand, having no mapped child, must inherit it
        rig_rest = {"upperarm_l": self.matrix(0, 100, 0),
                    "lowerarm_l": self.matrix(0, 70, 0),
                    "hand_l": self.matrix(0, 40, 0)}
        src_rest = {"Arm": self.matrix(0, 100, 0), "ForeArm": self.matrix(30, 100, 0),
                    "Hand": self.matrix(60, 100, 0)}
        triples = [("FKShoulder_L", "upperarm_l", "Arm"),
                   ("FKElbow_L", "lowerarm_l", "ForeArm"),
                   ("FKWrist_L", "hand_l", "Hand")]
        rig_parents = {"upperarm_l": None, "lowerarm_l": "upperarm_l",
                       "hand_l": "lowerarm_l"}
        src_parents = {"Arm": None, "ForeArm": "Arm", "Hand": "ForeArm"}
        align = ar.alignments(triples, rig_rest, src_rest, rig_parents, src_parents)
        self.assertAlmostEqual(ar.rotation_angle(align["FKShoulder_L"]), 90.0, places=4)
        self.assertAlmostEqual(ar.rotation_angle(align["FKElbow_L"]), 90.0, places=4)
        # the wrist has no mapped child: it takes the elbow's answer verbatim
        self.assertEqual(align["FKWrist_L"], align["FKElbow_L"])

    def test_a_hand_points_along_the_middle_finger_and_not_the_thumb(self):
        # the thumb is a hand's NEAREST mapped child and the one finger that does
        # not continue it: taking it rolled the wrist by a measured 30.77 deg
        rig_rest = {"hand_l": self.matrix(0, 0, 0),
                    "thumb_01_l": self.matrix(0, -3, 4),      # off across the palm
                    "middle_01_l": self.matrix(10, 0, 0)}     # along the hand
        src_rest = {"Hand": self.matrix(0, 0, 0),
                    "HandThumb1": self.matrix(0, -3, 4),
                    "HandMiddle1": self.matrix(0, 10, 0)}
        triples = [("FKWrist_L", "hand_l", "Hand"),
                   ("FKThumbFinger1_L", "thumb_01_l", "HandThumb1"),
                   ("FKMiddleFinger1_L", "middle_01_l", "HandMiddle1")]
        rig_parents = {"hand_l": None, "thumb_01_l": "hand_l",
                       "middle_01_l": "hand_l"}
        src_parents = {"Hand": None, "HandThumb1": "Hand", "HandMiddle1": "Hand"}
        align = ar.alignments(triples, rig_rest, src_rest, rig_parents, src_parents)
        # +X onto +Y is 90 deg; the thumb pair would have aligned to the identity
        self.assertAlmostEqual(ar.rotation_angle(align["FKWrist_L"]), 90.0, places=4)

    def test_the_reference_keeps_our_position_or_takes_the_sources(self):
        control = self.matrix(10, 20, 30)
        source = self.matrix(-5, 0, 5)
        kept = ar.reference_matrix(control, self.IDENT, source, True)
        moved = ar.reference_matrix(control, self.IDENT, source, False)
        self.assertEqual(tuple(round(v, 6) for v in ar.position(kept)), (10.0, 20.0, 30.0))
        self.assertEqual(tuple(round(v, 6) for v in ar.position(moved)), (-5.0, 0.0, 5.0))

    def test_the_reference_applies_the_alignment_as_a_world_rotation(self):
        control = list(om.MMatrix())
        align = list(om.MEulerRotation(0.0, 0.0, math.radians(45.0)).asMatrix())
        ref = ar.reference_matrix(control, align, self.IDENT, True)
        self.assertAlmostEqual(ar.rotation_angle(ref), 45.0, places=6)

    def test_the_euler_offset_round_trips_through_the_rotate_order(self):
        turn = list(om.MEulerRotation(math.radians(10.0), math.radians(-20.0),
                                      math.radians(35.0)).asMatrix())
        for order in range(6):
            got = ar.euler_offset(turn, order)
            back = om.MEulerRotation([math.radians(v) for v in got], order).asMatrix()
            for a, b in zip(list(back), turn):
                self.assertAlmostEqual(a, b, places=6, msg="rotate order %d" % order)


class TestSourceRoot(unittest.TestCase):

    # The animator's scene: our rigged skeleton at |root, the AS rig under
    # |Group, and an imported clip whose top node Maya renamed.
    JOINTS = [
        "|root", "|root|pelvis", "|root|pelvis|spine_01",
        "|Group|MotionSystem|FKSystem|FKXSpine5_M",
        "|Manny_Skeleton_root", "|Manny_Skeleton_root|pelvis",
        "|Manny_Skeleton_root|pelvis|spine_01",
    ]
    RIG = ["|root", "|root|pelvis", "|root|pelvis|spine_01",
           "|Group|MotionSystem|FKSystem|FKXSpine5_M"]

    def test_the_top_joint_of_a_path_is_the_shallowest_joint_prefix(self):
        self.assertEqual(
            ar.top_joint("|Manny_Skeleton_root|pelvis|spine_01", self.JOINTS),
            "|Manny_Skeleton_root")

    def test_a_group_above_the_skeleton_is_not_the_top_joint(self):
        joints = ["|grp|root", "|grp|root|pelvis"]
        self.assertEqual(ar.top_joint("|grp|root|pelvis", joints), "|grp|root")

    def test_a_path_holding_no_joint_has_no_top_joint(self):
        self.assertIsNone(ar.top_joint("|persp", self.JOINTS))

    def test_any_joint_of_the_source_resolves_to_its_root(self):
        root, refusal = ar.source_root_of(
            ["|Manny_Skeleton_root|pelvis|spine_01"], self.JOINTS, self.RIG)
        self.assertEqual((root, refusal), ("|Manny_Skeleton_root", ""))

    def test_a_namespaced_source_works_the_same(self):
        joints = ["|clip:root", "|clip:root|clip:pelvis"]
        root, refusal = ar.source_root_of(["|clip:root|clip:pelvis"], joints, self.RIG)
        self.assertEqual((root, refusal), ("|clip:root", ""))

    def test_an_empty_selection_is_refused(self):
        root, refusal = ar.source_root_of([], self.JOINTS, self.RIG)
        self.assertEqual(root, "")
        self.assertIn("select", refusal.lower())

    def test_a_selection_with_no_joint_is_refused(self):
        root, refusal = ar.source_root_of(["|persp"], self.JOINTS, self.RIG)
        self.assertEqual(root, "")
        self.assertIn("joint", refusal.lower())

    def test_our_own_rigged_skeleton_is_refused_by_name(self):
        root, refusal = ar.source_root_of(["|root|pelvis"], self.JOINTS, self.RIG)
        self.assertEqual(root, "")
        self.assertIn("|root", refusal)

    def test_the_rigs_own_internals_are_refused(self):
        root, refusal = ar.source_root_of(
            ["|Group|MotionSystem|FKSystem|FKXSpine5_M"], self.JOINTS, self.RIG)
        self.assertEqual(root, "")
        self.assertTrue(refusal)

    def test_two_different_sources_at_once_are_refused_and_both_named(self):
        joints = self.JOINTS + ["|second_root", "|second_root|pelvis"]
        root, refusal = ar.source_root_of(
            ["|Manny_Skeleton_root|pelvis", "|second_root|pelvis"], joints, self.RIG)
        self.assertEqual(root, "")
        self.assertIn("Manny_Skeleton_root", refusal)
        self.assertIn("second_root", refusal)


class TestOffsetLocal(unittest.TestCase):

    IDENT = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def test_equal_frames_give_the_identity(self):
        m = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 5, 6, 7, 1]
        self.assertTrue(ar.is_identity(ar.offset_local(m, m)))

    def test_the_offset_reproduces_the_control_when_the_bone_stands_at_rest(self):
        # control 90 deg about Z at (1,2,3); bone unrotated at (1,2,3)
        ctrl = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 1, 2, 3, 1]
        bone = self.IDENT[:12] + [1, 2, 3, 1]
        local = ar.offset_local(ctrl, bone)
        self.assertFalse(ar.is_identity(local))
        # local * bone == ctrl  (row-vector: world = local * parent)
        got = list(om.MMatrix(local) * om.MMatrix(bone))
        for a, b in zip(got, ctrl):
            self.assertAlmostEqual(a, b, places=9)

    def test_a_scale_on_either_input_does_not_reach_the_offset(self):
        # the rig's own scale chain leaves ~4e-7 on a bone, and 85 cm out at a
        # pole that came back as 33 microns of error until both sides were made
        # rigid
        ctrl = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 1, 2, 3, 1]
        bone = self.IDENT[:12] + [1, 2, 3, 1]
        scaled = [v * 1.0000004 for v in bone[:12]] + bone[12:]
        clean = ar.offset_local(ctrl, bone)
        got = ar.offset_local(ctrl, scaled)
        for a, b in zip(got, clean):
            self.assertAlmostEqual(a, b, places=9)

    def test_it_is_not_the_other_order(self):
        ctrl = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 1, 2, 3, 1]
        bone = [1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 4, 0, 0, 1]
        wrong = list(om.MMatrix(bone) * om.MMatrix(ar.offset_local(ctrl, bone)))
        self.assertFalse(all(abs(a - b) < 1e-9 for a, b in zip(wrong, ctrl)))


class TestNeedsOffset(unittest.TestCase):

    IDENT = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def test_the_translation_row_is_what_rotation_only_drops(self):
        m = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 5, 6, 7, 1]
        self.assertEqual(ar.rotation_only(m), m[:12] + [0.0, 0.0, 0.0, 1])

    def test_equal_frames_need_no_offset(self):
        self.assertFalse(ar.needs_offset(self.IDENT, True))
        self.assertFalse(ar.needs_offset(self.IDENT, False))

    def test_a_control_standing_off_its_bone_needs_one_only_when_position_is_driven(self):
        # what the IK end controls measure: 0.0095 cm off the bone, frames equal
        off = self.IDENT[:12] + [0.0095, 0.0, 0.0, 1]
        self.assertTrue(ar.needs_offset(off, True))
        self.assertFalse(ar.needs_offset(off, False))

    def test_a_turned_frame_needs_one_either_way(self):
        turned = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        self.assertTrue(ar.needs_offset(turned, True))
        self.assertTrue(ar.needs_offset(turned, False))

    def test_the_aligned_controls_measured_residual_is_not_an_offset(self):
        # the FK controls measure ~1e-7 against their bones after the axis work
        tiny = [1, 1e-7, 0, 0, -1e-7, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        self.assertFalse(ar.needs_offset(tiny, False))


class TestParentOffsets(unittest.TestCase):
    """A parentConstraint's target offsets carry a rigid rest offset exactly.

    Measured 2026-09-05 on sandbox transforms over all six rotate orders:
    `targetOffsetTranslate` = the offset's translation and `targetOffsetRotate`
    = its euler in the CONSTRAINED node's rotate order reproduce
    W_control = O * W_source to 4.6e-14, and `-mo` stores those very numbers.
    Read in xyz for any other order the follow is wrong by up to 1.47.
    """

    def test_the_identity_offset_is_all_zeros(self):
        translate, rotate = ar.parent_offsets(list(om.MMatrix()), 3)
        self.assertEqual(tuple(translate), (0.0, 0.0, 0.0))
        self.assertEqual(tuple(rotate), (0.0, 0.0, 0.0))

    def test_the_translation_is_the_matrix_row_untouched(self):
        m = list(om.MMatrix())
        m[12], m[13], m[14] = 4.0, -5.0, 6.5
        translate, rotate = ar.parent_offsets(m, 0)
        self.assertEqual(tuple(translate), (4.0, -5.0, 6.5))
        self.assertEqual(tuple(rotate), (0.0, 0.0, 0.0))

    def test_the_rotation_round_trips_through_the_controls_rotate_order(self):
        for order in range(6):
            tm = om.MTransformationMatrix()
            tm.setRotation(om.MEulerRotation(math.radians(30.0), math.radians(-70.0),
                                             math.radians(115.0), order))
            tm.setTranslation(om.MVector(1.0, 2.0, 3.0), om.MSpace.kWorld)
            m = list(tm.asMatrix())
            translate, rotate = ar.parent_offsets(m, order)
            back = om.MEulerRotation([math.radians(v) for v in rotate],
                                     order).asMatrix()
            for i in range(3):
                for j in range(3):
                    self.assertAlmostEqual(back.getElement(i, j), m[i * 4 + j],
                                           places=9, msg="order %d" % order)
            self.assertEqual(tuple(round(v, 9) for v in translate), (1.0, 2.0, 3.0))

    def test_it_agrees_with_the_orient_constraints_euler(self):
        tm = om.MTransformationMatrix()
        tm.setRotation(om.MEulerRotation(0.4, -1.1, 2.0, 5))
        m = list(tm.asMatrix())
        _, rotate = ar.parent_offsets(m, 5)
        self.assertEqual(tuple(rotate), tuple(ar.euler_offset(m, 5)))


class TestProportions(unittest.TestCase):

    def matrix(self, x, y, z):
        m = list(om.MMatrix())
        m[12], m[13], m[14] = x, y, z
        return m

    def test_the_ratio_is_measured_through_the_schemas_own_map(self):
        # our arm 30 + 30, the source's 20 + 20 -- names that share nothing
        rig_rest = {"upperarm_l": self.matrix(0, 0, 0),
                    "lowerarm_l": self.matrix(30, 0, 0),
                    "hand_l": self.matrix(60, 0, 0),
                    "thigh_l": self.matrix(0, 0, 0), "calf_l": self.matrix(0, -40, 0),
                    "foot_l": self.matrix(0, -80, 0)}
        src_rest = {"LeftArm": self.matrix(0, 0, 0),
                    "LeftForeArm": self.matrix(20, 0, 0),
                    "LeftHand": self.matrix(40, 0, 0),
                    "LeftUpLeg": self.matrix(0, 0, 0), "LeftLeg": self.matrix(0, -40, 0),
                    "LeftFoot": self.matrix(0, -80, 0)}
        ratios = ar.limb_ratios(rig_rest, src_rest, ar.MIXAMO)
        self.assertAlmostEqual(ratios["arm"], 1.5, places=6)
        self.assertAlmostEqual(ratios["leg"], 1.0, places=6)

    def test_matching_proportions_say_nothing(self):
        self.assertEqual(ar.proportion_note({"arm": 1.0, "leg": 1.005}), "")

    def test_a_difference_names_both_modes_rather_than_refusing(self):
        note = ar.proportion_note({"arm": 1.165, "leg": 0.974})
        self.assertIn("arm", note)
        self.assertIn("16.5", note)
        self.assertIn("FK", note)
        self.assertIn("IK", note)
        self.assertNotIn("refus", note.lower())


class TestScaleWarning(unittest.TestCase):

    def test_identical_proportions_warn_about_nothing(self):
        lengths = {"thigh_l": 40.0, "calf_l": 40.0, "upperarm_l": 30.0}
        self.assertEqual(ar.scale_warning(lengths, lengths), "")

    def test_a_two_percent_difference_is_tolerated(self):
        rig = {"thigh_l": 40.0}
        self.assertEqual(ar.scale_warning({"thigh_l": 40.6}, rig), "")

    def test_a_bigger_difference_names_the_segment_and_both_numbers(self):
        rig = {"thigh_l": 40.0, "calf_l": 40.0}
        msg = ar.scale_warning({"thigh_l": 50.0, "calf_l": 40.0}, rig)
        self.assertIn("thigh_l", msg)
        self.assertIn("50.0", msg)
        self.assertIn("40.0", msg)
        self.assertNotIn("calf_l", msg)

    def test_a_segment_the_source_lacks_is_not_a_warning(self):
        self.assertEqual(ar.scale_warning({}, {"thigh_l": 40.0}), "")

    def test_segment_lengths_come_from_positions(self):
        pos = {"thigh_l": (0.0, 0.0, 0.0), "calf_l": (0.0, -40.0, 0.0),
               "foot_l": (0.0, -40.0, 30.0)}
        lengths = ar.segment_lengths(pos)
        self.assertAlmostEqual(lengths["thigh_l"], 40.0, places=6)
        self.assertAlmostEqual(lengths["calf_l"], 30.0, places=6)


class FakeCmds(object):
    """Only what source_bones and rig_paths ask for."""

    def __init__(self, joints, relatives, constrained=()):
        self._joints = joints
        self._relatives = relatives
        self._constrained = set(constrained)

    def ls(self, *args, **kwargs):
        if kwargs.get("type") == "joint":
            return list(self._joints)
        return []

    def listRelatives(self, node, **kwargs):
        if kwargs.get("type") == "constraint":
            return ["c1"] if node in self._constrained else []
        return list(self._relatives.get(node, []))

    def objExists(self, node):
        return node in self._joints


class TestSourceBones(unittest.TestCase):

    def setUp(self):
        self._real = ar.cmds
        joints = ["|clip:root", "|clip:root|clip:pelvis",
                  "|clip:root|clip:pelvis|clip:spine_01"]
        ar.cmds = FakeCmds(joints, {"|clip:root": joints[1:]})

    def tearDown(self):
        ar.cmds = self._real

    def test_the_leaf_name_drops_the_namespace(self):
        bones = ar.source_bones("|clip:root")
        self.assertEqual(sorted(bones), ["pelvis", "root", "spine_01"])
        self.assertEqual(bones["pelvis"], "|clip:root|clip:pelvis")


class TestRigPaths(unittest.TestCase):

    def setUp(self):
        self._real = ar.cmds
        joints = ["|root", "|root|pelvis", "|Group|MotionSystem|FKXSpine5_M",
                  "|clip:root", "|clip:root|clip:pelvis"]
        ar.cmds = FakeCmds(joints, {}, constrained=["|root", "|root|pelvis"])

    def tearDown(self):
        ar.cmds = self._real

    def test_constrained_joints_and_the_rigs_internals_are_the_rig(self):
        self.assertEqual(sorted(ar.rig_paths()),
                         ["|Group|MotionSystem|FKXSpine5_M", "|root", "|root|pelvis"])

    def test_the_ue_skeleton_root_is_the_shallowest_path_outside_group(self):
        self.assertEqual(ar.rig_skeleton_root(ar.rig_paths()), "|root")


class TestNames(unittest.TestCase):

    def test_the_holder_and_switch_are_advancedskeletons_own_spelling(self):
        self.assertEqual(ar.HOLDER, "MoCapConstraints")
        self.assertEqual(ar.SWITCH, "disableConstraints")

    def test_the_only_bake_is_the_vendors_contract(self):
        # Until 2026-09-07 the bake was the vendor's MEL, pressed from here; a
        # second implementation "would drift from the vendor's".  It is ours
        # now -- `vendor_bake`, the vendor's proc read whole and replicated
        # flag for flag -- because the bridge's IMPORT and a colleague's fresh
        # Maya have no AdvancedSkeleton sourced.  The drift argument still
        # holds for everything else: `bakeResults` appears in that one
        # function and nowhere else, and no MEL is evaluated at all.
        with open(ar.__file__.replace(".pyc", ".py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertTrue(callable(ar.bake))
        self.assertEqual(src.count("cmds.bakeResults("), 1)
        self.assertIn("cmds.bakeResults(", src.split("def vendor_bake")[1]
                      .split("\ndef ")[0])
        self.assertNotIn("mel.eval(", src)

    def test_the_neck_note_only_reports_and_the_setter_only_sets(self):
        # a function whose name says "note" must not change the animator's rig:
        # the bias is theirs, and it decides how baked neck keys distribute
        with open(ar.__file__.replace(".pyc", ".py")) as handle:
            source = handle.read()
        note = source.split("def neck_note()")[1].split("\ndef ")[0]
        self.assertNotIn("setAttr", note)
        self.assertIn("setAttr", source.split("def set_exact_neck()")[1].split("\ndef ")[0])

    def test_the_neck_bias_is_the_measured_pair(self):
        # measured 2026-09-04: bias 0 -> in-between weight 0.5, bias 10 -> 1.0
        self.assertEqual(ar.NECK_BIAS, ("FKNeck_M", "bias", 10.0))

    def test_the_neck_twist_share_is_the_measured_knob(self):
        # measured 2026-09-05: NeckPart1_M's orientConstraint.offsetX is DRIVEN by
        # the head's twist times this multiplier (0.5 in the rig); at 0 neck_02
        # lands exactly on every frame, at 0.5 it rolled 24.24 deg off the source
        self.assertEqual(ar.NECK_TWIST, ("twistAmountDivideNeckPart1_M", "input2", 0.0))
        # both knobs are what "exact neck" means, and the setter names both
        with open(ar.__file__.replace(".pyc", ".py")) as handle:
            source = handle.read()
        setter = source.split("def set_exact_neck()")[1].split("\ndef ")[0]
        self.assertIn("NECK_TWIST", setter)
        self.assertIn("NECK_BIAS", setter)

    def test_no_qt(self):
        with open(ar.__file__.replace(".pyc", ".py")) as handle:
            source = handle.read()
        for banned in ("PySide", "shiboken", "QtWidgets"):
            self.assertNotIn(banned, source)


class FakeBakeCmds(object):
    """Just enough of cmds for vendor_bake: the holder's switch fans out to
    three constraints, two of which drive the same control."""

    def __init__(self):
        self.calls = []
        self.driven = {"c1": ["FKWrist_R"], "c2": ["IKArm_L"], "c3": ["FKWrist_R"]}

    def objExists(self, name):
        return True

    def attributeQuery(self, *args, **kwargs):
        return True

    def getAttr(self, plug):
        return "|clip:root"

    def listConnections(self, plug, **kwargs):
        node, attr = plug.split(".")
        if attr == ar.SWITCH:
            return ["c1", "c2", "c3"]
        if attr == "constraintParentInverseMatrix":
            return self.driven[node]
        return []

    def bakeResults(self, *objs, **kwargs):
        self.calls.append(("bakeResults", objs, kwargs))

    def delete(self, *objs, **kwargs):
        self.calls.append(("delete", objs, kwargs))


class TestVendorBake(unittest.TestCase):
    """The vendor's `asMoCapMatcherBake`, read whole and replicated in cmds
    (2026-09-07), so a session that never sourced AdvancedSkeleton bakes."""

    def setUp(self):
        self.real = ar.cmds
        self.fake = FakeBakeCmds()
        ar.cmds = self.fake

    def tearDown(self):
        ar.cmds = self.real

    def test_every_driven_object_is_baked_once(self):
        self.assertEqual(ar.vendor_bake(3.0, 41.0), ["FKWrist_R", "IKArm_L"])

    def test_the_bake_carries_the_vendors_flags(self):
        ar.vendor_bake(3.0, 41.0)
        name, objs, k = self.fake.calls[0]
        self.assertEqual((name, objs), ("bakeResults", ("FKWrist_R", "IKArm_L")))
        self.assertEqual(k["time"], (3.0, 41.0))
        for flag, value in (("simulation", True), ("sampleBy", 1),
                            ("disableImplicitControl", True),
                            ("preserveOutsideKeys", False),
                            ("sparseAnimCurveBake", False),
                            ("removeBakedAttributeFromLayer", False),
                            ("bakeOnOverrideLayer", False),
                            ("controlPoints", False), ("shape", False)):
            self.assertEqual(k[flag], value, flag)

    def test_static_channels_are_deleted_the_vendors_way(self):
        ar.vendor_bake(3.0, 41.0)
        name, objs, k = self.fake.calls[1]
        self.assertEqual((name, objs), ("delete", ("FKWrist_R", "IKArm_L")))
        self.assertEqual(
            (k["staticChannels"], k["unitlessAnimationCurves"], k["hierarchy"],
             k["controlPoints"], k["shape"]),
            (True, False, "none", False, True))

    def test_nothing_registered_bakes_nothing(self):
        self.fake.listConnections = lambda plug, **k: []
        self.assertEqual(ar.vendor_bake(0.0, 1.0), [])
        self.assertEqual(self.fake.calls, [])

    def test_connected_source_reads_the_holder(self):
        self.assertEqual(ar.connected_source(), "|clip:root")
        self.fake.objExists = lambda name: False
        self.assertIsNone(ar.connected_source())
