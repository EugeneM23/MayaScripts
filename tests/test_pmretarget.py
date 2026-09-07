import math
import os
import unittest

import maya.api.OpenMaya as om

import maya_pmretarget as pm

# The PlayerMale rig's controls (measured 2026-09-05: 56 deform joints, 176 controls --
# these are the ones the tables can drive).  Midline bases exist as _M only, the eyes and
# the limbs as _L/_R only: a fixture offering every side for every base would be more
# symmetric than the rig and would let a bug through.
MIDLINE = ["Spine1", "Spine2", "Spine3", "Chest", "Neck", "Head", "Jaw"]
SIDED = ["Eye", "Scapula", "Shoulder", "Elbow", "Wrist", "Hip", "Knee", "Ankle", "Toes"]
for _f in ("Index", "Middle", "Ring", "Pinky", "Thumb"):
    SIDED += ["%sFinger%d" % (_f, i) for i in (1, 2, 3)]
CONTROLS = ["Main", "RootX_M"] + ["FK%s_M" % b for b in MIDLINE]
for _b in SIDED:
    CONTROLS += ["FK%s_L" % _b, "FK%s_R" % _b]
for _s in ("_L", "_R"):
    CONTROLS += ["IKArm" + _s, "IKLeg" + _s, "IKToes" + _s, "PoleArm" + _s, "PoleLeg" + _s]

# The PlayerMale skeleton's 57 leaf names.
OWN_BONES = ["Root", "Hip", "Spine1", "Spine2", "Spine3", "Spine4", "Neck", "Head", "Jaw"]
for _s in ("Right_", "Left_"):
    OWN_BONES += [_s + n for n in ("Eye", "Shoulder", "Arm", "ForeArm", "Hand", "Thigh", "Knee", "Ankle", "Toes")]
    for _f in ("Finger", "Middle", "Ring", "Pinky", "Thumb"):
        OWN_BONES += ["%s%s%d" % (_s, _f, i) for i in (1, 2, 3)]

# A full UE5 Manny's leaf names, and the UE4 mannequin's.
UE5_BONES = ["root", "pelvis", "neck_01", "neck_02", "head"] + ["spine_0%d" % i for i in range(1, 6)]
for _s in ("l", "r"):
    UE5_BONES += ["clavicle_" + _s, "upperarm_" + _s, "lowerarm_" + _s, "hand_" + _s,
                  "thigh_" + _s, "calf_" + _s, "foot_" + _s, "ball_" + _s]
    for _f in ("index", "middle", "ring", "pinky"):
        UE5_BONES.append("%s_metacarpal_%s" % (_f, _s))
        UE5_BONES += ["%s_0%d_%s" % (_f, i, _s) for i in (1, 2, 3)]
    UE5_BONES += ["thumb_0%d_%s" % (i, _s) for i in (1, 2, 3)]
UE4_BONES = [b for b in UE5_BONES if b not in ("spine_04", "spine_05", "neck_02") and "metacarpal" not in b]

MIXAMO_BONES = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "HeadTop_End", "LeftEye", "RightEye"]
for _s in ("Left", "Right"):
    MIXAMO_BONES += [_s + n for n in ("Shoulder", "Arm", "ForeArm", "Hand", "UpLeg", "Leg", "Foot", "ToeBase", "Toe_End")]
    for _f in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        MIXAMO_BONES += ["%sHand%s%d" % (_s, _f, i) for i in (1, 2, 3, 4)]


def rest_of(**positions):
    """{name: world matrix} standing at the given positions, unrotated."""
    out = {}
    for name, (x, y, z) in positions.items():
        m = list(om.MMatrix())
        m[12], m[13], m[14] = x, y, z
        out[name] = m
    return out


class TestOurRig(unittest.TestCase):

    def test_every_control_stands_on_a_playermale_bone(self):
        for control in CONTROLS:
            self.assertIn(pm.our_bone(control), OWN_BONES, control)

    def test_the_side_is_a_prefix_and_chest_is_spine4(self):
        self.assertEqual(pm.our_bone("FKChest_M"), "Spine4")
        self.assertEqual(pm.our_bone("FKWrist_R"), "Right_Hand")
        self.assertEqual(pm.our_bone("FKIndexFinger2_L"), "Left_Finger2")
        self.assertEqual(pm.our_bone("IKLeg_L"), "Left_Ankle")
        self.assertEqual(pm.our_bone("PoleArm_R"), "Right_Arm")
        self.assertEqual(pm.our_bone("Main"), "Root")
        self.assertEqual(pm.our_bone("RootX_M"), "Hip")

    def test_a_control_the_rig_does_not_have_stands_nowhere(self):
        self.assertIsNone(pm.our_bone("FKNeckPart1_M"))
        self.assertIsNone(pm.our_bone("HipSwinger_M"))


class TestSchemas(unittest.TestCase):

    def test_each_source_is_detected_by_its_own_bones(self):
        self.assertIs(pm.detect_schema(OWN_BONES), pm.OWN)
        self.assertIs(pm.detect_schema(UE5_BONES), pm.UE5)
        self.assertIs(pm.detect_schema(UE4_BONES), pm.UE4)
        self.assertIs(pm.detect_schema(MIXAMO_BONES), pm.MIXAMO)

    def test_ue4_is_ue5_without_spine_05_and_not_the_other_way_round(self):
        self.assertIs(pm.detect_schema(UE5_BONES + ["extra"]), pm.UE5)
        self.assertIs(pm.detect_schema([b for b in UE5_BONES if b != "spine_05"]), pm.UE4)

    def test_a_skeleton_that_is_none_of_them_is_refused_rather_than_guessed(self):
        self.assertIsNone(pm.detect_schema(["root", "hips", "chest", "l_arm"]))
        self.assertIsNone(pm.detect_schema([]))

    def test_the_rest_comes_from_where_each_skeleton_keeps_it(self):
        self.assertEqual(pm.OWN.rest, "ours")
        self.assertEqual(pm.UE5.rest, "template")
        self.assertEqual(pm.UE4.rest, "template")
        self.assertEqual(pm.MIXAMO.rest, "jointOrient")

    def test_only_the_own_skeleton_needs_no_alignment(self):
        self.assertEqual([s.align for s in pm.SCHEMAS], [False, True, True, True])

    def test_only_mixamo_lacks_a_root_bone(self):
        self.assertEqual([s.root_bone for s in pm.SCHEMAS], ["Root", "root", "root", None])

    def test_sides_are_a_prefix_for_own_and_mixamo_and_a_suffix_for_unreal(self):
        self.assertEqual(pm.bone_name("Arm", "Right_", pm.OWN), "Right_Arm")
        self.assertEqual(pm.bone_name("upperarm", "_r", pm.UE5), "upperarm_r")
        self.assertEqual(pm.bone_name("Arm", "Left", pm.MIXAMO), "LeftArm")

    def test_the_shipped_templates_exist_and_describe_the_bind_pose(self):
        for schema, count, pelvis_y in ((pm.UE5, 93, 96.75), (pm.UE4, 68, 96.75)):
            path = os.path.join(pm.ASSETS, schema.template)
            self.assertTrue(os.path.exists(path), path)
            rest = pm.template_rest(schema.template)
            self.assertEqual(len(rest), count)
            self.assertEqual(len(rest["pelvis"]), 16)
            self.assertAlmostEqual(pm.position(rest["pelvis"])[1], pelvis_y, delta=1.0)
            self.assertAlmostEqual(pm.position(rest["root"])[1], 0.0, delta=1e-6)
            for name in schema.required:
                self.assertIn(name, rest)

    def test_every_ue_row_has_a_bone_in_its_template(self):
        for schema in (pm.UE5, pm.UE4):
            rest = pm.template_rest(schema.template)
            for base, bone in schema.rows:
                for _, side in schema.sides[1:] if base not in ("Spine1", "Spine2", "Spine3", "Chest", "Neck", "Head") else [(None, "")]:
                    self.assertIn(pm.bone_name(bone, side, schema), rest, (schema.name, base))


class TestDrivePlan(unittest.TestCase):

    def plan(self, bones, schema):
        drives, missing = pm.drive_plan(CONTROLS, bones, schema)
        return dict((d.control, d) for d in drives), missing

    def test_a_full_ue5_source_drives_everything_it_can_and_misses_nothing(self):
        by, missing = self.plan(UE5_BONES, pm.UE5)
        self.assertEqual(missing, [])
        self.assertEqual(len(by), 2 + 6 + 2 * 23 + 6 + 4)      # Main, RootX; 6 midline FK; 23 sided FK x2; 6 IK; 4 poles

    def test_fk_controls_take_rotation_only_whatever_the_source(self):
        for bones, schema in ((OWN_BONES, pm.OWN), (UE5_BONES, pm.UE5), (UE4_BONES, pm.UE4), (MIXAMO_BONES, pm.MIXAMO)):
            by, _ = self.plan(bones, schema)
            kinds = set(d.kind for c, d in by.items() if c.startswith("FK"))
            self.assertEqual(kinds, set(["fk"]), schema.name)

    def test_the_ue5_chest_is_spine_05_and_spine_04_is_left_alone(self):
        by, _ = self.plan(UE5_BONES, pm.UE5)
        self.assertEqual(by["FKChest_M"].source, "spine_05")
        self.assertEqual(by["FKSpine3_M"].source, "spine_03")
        self.assertNotIn("spine_04", [d.source for d in by.values()])

    def test_the_ue4_chest_is_spine_03_and_our_spine3_is_left_alone(self):
        by, missing = self.plan(UE4_BONES, pm.UE4)
        self.assertEqual(missing, [])
        self.assertEqual(by["FKChest_M"].source, "spine_03")
        self.assertNotIn("FKSpine3_M", by)

    def test_the_mixamo_chest_is_spine2_and_the_eyes_are_driven(self):
        by, missing = self.plan(MIXAMO_BONES, pm.MIXAMO)
        self.assertEqual(missing, [])
        self.assertEqual(by["FKChest_M"].source, "Spine2")
        self.assertEqual(by["FKSpine2_M"].source, "Spine1")
        self.assertEqual(by["FKEye_L"].source, "LeftEye")
        self.assertNotIn("FKJaw_M", by)

    def test_the_own_skeleton_maps_name_to_name(self):
        by, missing = self.plan(OWN_BONES, pm.OWN)
        self.assertEqual(missing, [])
        for control, d in by.items():
            if d.kind in ("fk", "main", "pelvis"):
                self.assertEqual(d.source, pm.our_bone(control), control)

    def test_unreal_has_no_jaw_or_eyes_and_that_is_not_missing(self):
        by, missing = self.plan(UE5_BONES, pm.UE5)
        self.assertNotIn("FKJaw_M", by)
        self.assertNotIn("FKEye_R", by)
        self.assertEqual(missing, [])

    def test_root_motion_goes_to_main_from_the_root_bone_scaled(self):
        for bones, schema, root in ((UE5_BONES, pm.UE5, "root"), (OWN_BONES, pm.OWN, "Root")):
            by, _ = self.plan(bones, schema)
            self.assertEqual(by["Main"], pm.Drive("Main", root, "main"))

    def test_mixamo_main_takes_the_hips_ground_travel(self):
        by, _ = self.plan(MIXAMO_BONES, pm.MIXAMO)
        self.assertEqual(by["Main"], pm.Drive("Main", "Hips", "ground"))

    def test_the_pelvis_control_follows_the_pelvis_in_rotation_and_scaled_position(self):
        by, _ = self.plan(UE5_BONES, pm.UE5)
        self.assertEqual(by["RootX_M"], pm.Drive("RootX_M", "pelvis", "pelvis"))
        by, _ = self.plan(MIXAMO_BONES, pm.MIXAMO)
        self.assertEqual(by["RootX_M"], pm.Drive("RootX_M", "Hips", "pelvis"))

    def test_the_ik_ends_and_poles_follow_our_own_fk_joints_whatever_the_source(self):
        for bones, schema in ((UE5_BONES, pm.UE5), (MIXAMO_BONES, pm.MIXAMO), (OWN_BONES, pm.OWN)):
            by, _ = self.plan(bones, schema)
            self.assertEqual(by["IKArm_R"], pm.Drive("IKArm_R", "FKXWrist_R", "ik"))
            self.assertEqual(by["IKLeg_L"], pm.Drive("IKLeg_L", "FKXAnkle_L", "ik"))
            self.assertEqual(by["IKToes_R"], pm.Drive("IKToes_R", "FKXToes_R", "iktoes"))
            self.assertEqual(by["PoleArm_L"], pm.Drive("PoleArm_L", "FKXElbow_L", "pole"))
            self.assertEqual(by["PoleLeg_R"], pm.Drive("PoleLeg_R", "FKXKnee_R", "pole"))

    def test_a_missing_source_bone_is_reported_and_skipped(self):
        by, missing = self.plan([b for b in UE5_BONES if b != "thumb_02_l"], pm.UE5)
        self.assertIn(("FKThumbFinger2_L", "thumb_02_l"), missing)
        self.assertNotIn("FKThumbFinger2_L", by)

    def test_a_missing_control_is_silently_skipped(self):
        drives, missing = pm.drive_plan([c for c in CONTROLS if c != "FKHead_M"], UE5_BONES, pm.UE5)
        self.assertNotIn("FKHead_M", [d.control for d in drives])
        self.assertEqual(missing, [])

    def test_every_control_is_driven_once(self):
        drives, _ = pm.drive_plan(CONTROLS, UE5_BONES, pm.UE5)
        self.assertEqual(len(set(d.control for d in drives)), len(drives))


class TestScale(unittest.TestCase):

    def test_the_same_skeleton_scales_by_one(self):
        rest = rest_of(Root=(0, 0, 0), Hip=(0, 11.2, 0))
        self.assertAlmostEqual(pm.scale_factor(rest, rest, pm.OWN), 1.0)

    def test_a_ue_source_is_scaled_by_the_pelvis_heights_above_the_roots(self):
        ours = rest_of(Root=(0, 0, 0), Hip=(0, 11.2074, 0))
        theirs = rest_of(root=(0, 0, 0), pelvis=(0, 96.75, -1.0))
        self.assertAlmostEqual(pm.scale_factor(ours, theirs, pm.UE5), 11.2074 / 96.75)

    def test_a_source_standing_off_the_ground_is_measured_from_its_own_root(self):
        ours = rest_of(Root=(0, 0, 0), Hip=(0, 10.0, 0))
        theirs = rest_of(root=(30, 5, 0), pelvis=(30, 105, 0))
        self.assertAlmostEqual(pm.scale_factor(ours, theirs, pm.UE5), 0.1)

    def test_mixamo_measures_its_hips_from_the_ground(self):
        ours = rest_of(Root=(0, 0, 0), Hip=(0, 10.0, 0))
        theirs = rest_of(Hips=(0, 100.0, 0))
        self.assertAlmostEqual(pm.scale_factor(ours, theirs, pm.MIXAMO), 0.1)

    def test_a_missing_pelvis_scales_by_one_rather_than_dividing_by_nothing(self):
        self.assertEqual(pm.scale_factor(rest_of(Root=(0, 0, 0)), rest_of(root=(0, 0, 0)), pm.UE5), 1.0)


class TestProportions(unittest.TestCase):

    def test_the_ratio_takes_the_overall_size_out(self):
        ours = rest_of(Root=(0, 0, 0), Hip=(0, 10, 0), Left_Arm=(2, 16, 0), Left_ForeArm=(4, 16, 0), Left_Hand=(6, 16, 0))
        theirs = rest_of(root=(0, 0, 0), pelvis=(0, 100, 0), upperarm_l=(20, 160, 0), lowerarm_l=(40, 160, 0), hand_l=(60, 160, 0))
        ratios = pm.limb_ratios(ours, theirs, pm.UE5)
        self.assertAlmostEqual(ratios["arm"], 1.0)
        self.assertNotIn("leg", ratios)

    def test_a_longer_source_arm_is_named_with_the_size_taken_out(self):
        ours = rest_of(Root=(0, 0, 0), Hip=(0, 10, 0), Left_Arm=(2, 16, 0), Left_ForeArm=(4, 16, 0), Left_Hand=(6, 16, 0))
        theirs = rest_of(root=(0, 0, 0), pelvis=(0, 100, 0), upperarm_l=(20, 160, 0), lowerarm_l=(45, 160, 0), hand_l=(70, 160, 0))
        note = pm.proportion_note(pm.limb_ratios(ours, theirs, pm.UE5))
        self.assertIn("arm is -20.0%", note)
        self.assertIn("OUR limbs", note)

    def test_matching_proportions_say_nothing(self):
        self.assertEqual(pm.proportion_note({"arm": 1.01, "leg": 0.99}), "")


class TestAlignment(unittest.TestCase):

    def test_the_alignment_turns_our_direction_onto_the_sources(self):
        ours, theirs = om.MVector(1, 0, 0), om.MVector(0, 1, 0)
        m = om.MMatrix(pm.align_rotation(ours, theirs))
        turned = ours * m
        self.assertAlmostEqual((turned - theirs).length(), 0.0, places=9)
        self.assertAlmostEqual(pm.rotation_angle(list(m)), 90.0, places=6)

    def test_equal_directions_align_to_the_identity(self):
        self.assertTrue(pm.is_identity(pm.align_rotation(om.MVector(0, 0, 1), om.MVector(0, 0, 1))))

    def test_a_missing_direction_aligns_to_the_identity(self):
        self.assertTrue(pm.is_identity(pm.align_rotation(None, om.MVector(0, 0, 1))))

    def test_a_hand_points_along_the_middle_finger_and_not_the_thumb(self):
        # our hand -> middle finger along +X; the source's hand -> its middle finger along +Y;
        # both thumbs go somewhere else entirely
        rig_rest = rest_of(Right_Hand=(0, 0, 0), Right_Middle1=(1, 0, 0), Right_Thumb1=(0.5, 0.5, 0))
        src_rest = rest_of(hand_r=(0, 0, 0), middle_01_r=(0, 1, 0), thumb_01_r=(0.7, 0.7, 0))
        triples = [("FKWrist_R", "Right_Hand", "hand_r"), ("FKMiddleFinger1_R", "Right_Middle1", "middle_01_r"),
                   ("FKThumbFinger1_R", "Right_Thumb1", "thumb_01_r")]
        rig_parents = {"Right_Hand": None, "Right_Middle1": "Right_Hand", "Right_Thumb1": "Right_Hand"}
        src_parents = {"hand_r": None, "middle_01_r": "hand_r", "thumb_01_r": "hand_r"}
        out = pm.alignments(triples, rig_rest, src_rest, rig_parents, src_parents)
        self.assertAlmostEqual(pm.rotation_angle(out["FKWrist_R"]), 90.0, places=6)
        # the finger roots have no mapped child and inherit the hand's alignment
        self.assertAlmostEqual(pm.rotation_angle(out["FKMiddleFinger1_R"]), 90.0, places=6)

    def test_the_reference_applies_the_alignment_as_a_world_rotation_and_drops_the_position(self):
        control = list(om.MMatrix())
        control[12] = 5.0
        align = list(om.MEulerRotation(0, 0, math.radians(30)).asMatrix())
        ref = pm.reference_rotation(control, align)
        self.assertEqual(pm.position(ref), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(pm.rotation_angle(ref), 30.0, places=6)


class TestOffsets(unittest.TestCase):

    def frames(self):
        c = om.MTransformationMatrix()
        c.setRotation(om.MEulerRotation(0.3, -0.7, 1.1))
        c.setTranslation(om.MVector(1, 2, 3), om.MSpace.kWorld)
        b = om.MTransformationMatrix()
        b.setRotation(om.MEulerRotation(-1.0, 0.2, 0.4))
        b.setTranslation(om.MVector(4, 5, 6), om.MSpace.kWorld)
        return list(c.asMatrix()), list(b.asMatrix())

    def test_equal_frames_give_the_identity(self):
        c, _ = self.frames()
        self.assertTrue(pm.is_identity(pm.offset_local(c, c)))

    def test_the_offset_reproduces_the_control_when_the_bone_stands_at_rest(self):
        c, b = self.frames()
        back = om.MMatrix(pm.offset_local(c, b)) * om.MMatrix(b)
        self.assertLess(max(abs(x - y) for x, y in zip(list(back), c)), 1e-9)

    def test_a_scale_on_either_input_does_not_reach_the_offset(self):
        c, b = self.frames()
        scaled = list(om.MMatrix(b) * om.MMatrix([2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1]))
        self.assertLess(max(abs(x - y) for x, y in zip(pm.offset_local(c, scaled), pm.offset_local(c, pm.rigid(scaled)))), 1e-9)

    def test_the_euler_offset_round_trips_through_every_rotate_order(self):
        c, _ = self.frames()
        rot = pm.rotation_only(c)
        for order in range(6):
            e = pm.euler_offset(rot, order)
            back = om.MEulerRotation([math.radians(v) for v in e], order).asMatrix()
            self.assertLess(max(abs(x - y) for x, y in zip(list(back), rot)), 1e-9, order)

    def test_parent_offsets_split_the_translation_row_from_the_rotation(self):
        c, b = self.frames()
        local = pm.offset_local(c, b)
        move, turn = pm.parent_offsets(local, 0)
        self.assertEqual(move, pm.position(local))
        self.assertEqual(turn, pm.euler_offset(pm.rotation_only(local), 0))

    def test_rotation_only_zeroes_exactly_the_translation_row(self):
        c, _ = self.frames()
        r = pm.rotation_only(c)
        self.assertEqual(pm.position(r), (0.0, 0.0, 0.0))
        self.assertEqual(r[:12], c[:12])


class TestSourceRoot(unittest.TestCase):

    JOINTS = ["|Root", "|Root|Hip", "|Root|Hip|Spine1", "|clip:Root", "|clip:Root|clip:Hip", "|grp|Root1", "|grp|Root1|Hip",
              "|Group|DeformationSystem|Root_M"]
    RIG = ["|Root", "|Root|Hip", "|Root|Hip|Spine1", "|Group|DeformationSystem|Root_M"]

    def test_any_joint_of_a_source_resolves_to_its_root(self):
        self.assertEqual(pm.source_root_of(["|clip:Root|clip:Hip"], self.JOINTS, self.RIG), ("|clip:Root", ""))
        self.assertEqual(pm.source_root_of(["|grp|Root1|Hip"], self.JOINTS, self.RIG), ("|grp|Root1", ""))

    def test_our_own_rigged_skeleton_and_the_rigs_internals_are_refused(self):
        self.assertIn("rig's own", pm.source_root_of(["|Root|Hip"], self.JOINTS, self.RIG)[1])
        self.assertIn("rig's own", pm.source_root_of(["|Group|DeformationSystem|Root_M"], self.JOINTS, self.RIG)[1])

    def test_an_empty_or_jointless_selection_is_refused(self):
        self.assertIn("nothing selected", pm.source_root_of([], self.JOINTS, self.RIG)[1])
        self.assertIn("no joint", pm.source_root_of(["|Body"], self.JOINTS, self.RIG)[1])

    def test_two_sources_at_once_are_refused_and_both_named(self):
        refusal = pm.source_root_of(["|clip:Root", "|grp|Root1|Hip"], self.JOINTS, self.RIG)[1]
        self.assertIn("Root", refusal)
        self.assertIn("Root1", refusal)

    def test_the_leaf_name_drops_the_namespace(self):
        self.assertEqual(pm.leaf("|clip:Root|clip:Hip"), "Hip")
        self.assertEqual(pm.leaf("|grp|Root1"), "Root1")


class TestNames(unittest.TestCase):

    def test_the_holder_and_switch_are_advancedskeletons_own_spelling(self):
        self.assertEqual(pm.HOLDER, "MoCapConstraints")
        self.assertEqual(pm.SWITCH, "disableConstraints")

    def test_our_helpers_wear_a_prefix_the_manny_module_does_not(self):
        import maya_asretarget as ar
        for prefix in (pm.FOLLOW_PREFIX, pm.SCALED_PREFIX, pm.OFFSET_PREFIX, pm.POLE_BASE_PREFIX, pm.POLE_FRAME_PREFIX,
                       pm.POLE_NUDGE_PREFIX, pm.POLE_PREFIX, pm.SCALE_GROUP):
            self.assertTrue(prefix.startswith("pmrt"), prefix)
            self.assertNotEqual(prefix, ar.DRIVER_PREFIX)
            self.assertNotEqual(prefix, ar.TARGET_PREFIX)

    def test_a_pole_is_placed_from_its_whole_fk_limb_about_the_mid_joint(self):
        self.assertEqual(dict(pm.POLE_FOLLOW), {"PoleArm": "FKXElbow", "PoleLeg": "FKXKnee"})
        self.assertEqual(pm.pole_joints("PoleArm_R"), ("FKXShoulder_R", "FKXElbow_R", "FKXWrist_R"))
        self.assertEqual(pm.pole_joints("PoleLeg_L"), ("FKXHip_L", "FKXKnee_L", "FKXAnkle_L"))
        for base, mid in pm.POLE_FOLLOW:
            self.assertEqual(pm.POLE_CHAIN[base][1], mid)
        self.assertTrue(0 < pm.NUDGE < 0.1)

    def test_the_only_bake_is_the_vendors_contract_and_no_qt(self):
        # Since 2026-09-07 the bake is `vendor_bake` -- the vendor's proc in
        # cmds, flag for flag -- and nothing else in the module bakes or
        # evaluates MEL, so a session without AdvancedSkeleton sourced works.
        with open(pm.__file__.replace(".pyc", ".py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count("cmds.bakeResults("), 1)
        self.assertIn("cmds.bakeResults(", src.split("def vendor_bake")[1]
                      .split("\ndef ")[0])
        self.assertNotIn("mel.eval(", src)
        self.assertNotIn("PySide", src)
        self.assertNotIn("import maya_asretarget", src)      # a copy, not a coupling

    def test_bake_exists_and_disconnect_alone_says_it_keeps_nothing(self):
        self.assertTrue(callable(pm.bake))
        self.assertIn("NOTHING", pm.disconnect.__doc__)
        self.assertIn("bake()", pm.disconnect.__doc__)

    def test_candidates_cover_the_rig_and_nothing_twice(self):
        for schema in pm.SCHEMAS:
            names = pm.candidates(schema)
            self.assertEqual(len(names), len(set(names)))
            self.assertIn("Main", names)
            self.assertIn("IKArm_R", names)
            self.assertIn("PoleLeg_L", names)


class FakeBakeCmds(object):
    """Just enough of cmds for vendor_bake: the holder's switch fans out to
    two constraints, each resolving to the object it drives."""

    def __init__(self):
        self.calls = []
        self.driven = {"c1": ["FKWrist_R"], "c2": ["IKArm_L"], "c3": ["FKWrist_R"]}

    def objExists(self, name):
        return True

    def attributeQuery(self, *args, **kwargs):
        return True

    def getAttr(self, plug):
        return "|clip:Root"

    def listConnections(self, plug, **kwargs):
        node, attr = plug.split(".")
        if attr == pm.SWITCH:
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
        self.real = pm.cmds
        self.fake = FakeBakeCmds()
        pm.cmds = self.fake

    def tearDown(self):
        pm.cmds = self.real

    def test_every_driven_object_is_baked_once(self):
        self.assertEqual(pm.vendor_bake(3.0, 41.0), ["FKWrist_R", "IKArm_L"])

    def test_the_bake_carries_the_vendors_flags(self):
        pm.vendor_bake(3.0, 41.0)
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
        pm.vendor_bake(3.0, 41.0)
        name, objs, k = self.fake.calls[1]
        self.assertEqual((name, objs), ("delete", ("FKWrist_R", "IKArm_L")))
        self.assertEqual(
            (k["staticChannels"], k["unitlessAnimationCurves"], k["hierarchy"],
             k["controlPoints"], k["shape"]),
            (True, False, "none", False, True))

    def test_nothing_registered_bakes_nothing(self):
        self.fake.listConnections = lambda plug, **k: []
        self.assertEqual(pm.vendor_bake(0.0, 1.0), [])
        self.assertEqual(self.fake.calls, [])

    def test_connected_source_reads_the_holder(self):
        self.assertEqual(pm.connected_source(), "|clip:Root")
        self.fake.objExists = lambda name: False
        self.assertIsNone(pm.connected_source())


class TestAssets(unittest.TestCase):
    """The module moved into the plugin on 2026-09-07; its templates sit
    beside it now, not one folder down as when it lived at the repo root."""

    def test_assets_sit_beside_the_module(self):
        self.assertEqual(
            os.path.normcase(pm.ASSETS),
            os.path.normcase(os.path.join(
                os.path.dirname(os.path.abspath(pm.__file__)), "assets")))

    def test_both_templates_are_there(self):
        for name in ("manny_skeleton_template.json",
                     "ue4_mannequin_template.json"):
            self.assertTrue(os.path.isfile(os.path.join(pm.ASSETS, name)),
                            name)


if __name__ == "__main__":
    unittest.main()


class TestResetBuildPose(unittest.TestCase):
    """The sibling's reset, copied (this module imports nothing from it)."""

    class Fake(object):
        def __init__(self):
            self.deleted, self.set = [], []
            self.values = {"FKWrist_R.tx": 0.0, "FKElbow_R.rx": 25.0}

        def sets(self, name, **kwargs):
            return ["FKWrist_R", "FKElbow_R"]

        def listConnections(self, node, **kwargs):
            return {"FKWrist_R": ["FKWrist_R_rotateY", "SDK_curve"]}.get(node, [])

        def objectType(self, node):
            return "animCurveUA" if node.startswith("SDK") else "animCurveTL"

        def delete(self, nodes):
            self.deleted.extend(nodes)

        def objExists(self, plug):
            return plug in self.values

        def getAttr(self, plug, **kwargs):
            return True if kwargs.get("settable") else self.values[plug]

        def setAttr(self, plug, value):
            self.set.append((plug, value))

    def test_curves_go_driven_keys_stay_free_channels_zero(self):
        real, fake = pm.cmds, self.Fake()
        pm.cmds = fake
        try:
            self.assertEqual(pm.reset_build_pose(), (1, 1))
        finally:
            pm.cmds = real
        self.assertEqual(fake.deleted, ["FKWrist_R_rotateY"])
        self.assertEqual(fake.set, [("FKElbow_R.rx", 0.0)])
