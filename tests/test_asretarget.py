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

    def test_the_fk_controls_take_rotation_only_and_need_no_offset(self):
        d = self.by_control["FKShoulder_L"]
        self.assertEqual((d.bone, d.translate, d.rotate, d.offset),
                         ("upperarm_l", False, True, False))

    def test_the_spine_is_one_to_one(self):
        for i in range(1, 6):
            self.assertEqual(self.by_control["FKSpine%d_M" % i].bone, "spine_0%d" % i)

    def test_the_neck_inbetween_takes_the_second_neck_bone(self):
        self.assertEqual(self.by_control["FKNeckPart1_M"].bone, "neck_02")

    def test_the_metacarpals_are_mapped(self):
        self.assertEqual(self.by_control["FKIndexFinger0_R"].bone, "index_metacarpal_r")

    def test_root_motion_goes_to_main_with_an_offset(self):
        d = self.by_control["Main"]
        self.assertEqual((d.bone, d.translate, d.rotate, d.offset),
                         ("root", True, True, True))

    def test_the_pelvis_control_is_rootx_and_not_an_fk_control(self):
        d = self.by_control["RootX_M"]
        self.assertEqual((d.bone, d.translate, d.rotate, d.offset),
                         ("pelvis", True, True, True))
        self.assertNotIn("FKRoot_M", self.by_control)

    def test_the_ik_ends_take_position_and_rotation_without_an_offset(self):
        self.assertEqual(self.by_control["IKLeg_R"].bone, "foot_r")
        for name in ("IKArm_L", "IKLeg_L"):
            d = self.by_control[name]
            self.assertEqual((d.translate, d.rotate, d.offset), (True, True, False))

    def test_the_toe_control_takes_rotation_only(self):
        d = self.by_control["IKToes_L"]
        self.assertEqual((d.bone, d.translate, d.rotate, d.offset),
                         ("ball_l", False, True, False))

    def test_the_poles_ride_the_upper_bone_by_position_through_an_offset(self):
        self.assertEqual(self.by_control["PoleLeg_L"].bone, "thigh_l")
        self.assertEqual(self.by_control["PoleArm_R"].bone, "upperarm_r")
        d = self.by_control["PoleLeg_R"]
        self.assertEqual((d.translate, d.rotate, d.offset), (True, False, True))

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

    def test_it_is_not_the_other_order(self):
        ctrl = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 1, 2, 3, 1]
        bone = [1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 4, 0, 0, 1]
        wrong = list(om.MMatrix(bone) * om.MMatrix(ar.offset_local(ctrl, bone)))
        self.assertFalse(all(abs(a - b) < 1e-9 for a, b in zip(wrong, ctrl)))


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

    def test_no_bake_of_our_own(self):
        # The bake is AdvancedSkeleton's button; a second implementation would
        # drift from it.  Deliberately absent.
        self.assertFalse(hasattr(ar, "bake"))

    def test_no_qt(self):
        source = open(ar.__file__.replace(".pyc", ".py")).read()
        for banned in ("PySide", "shiboken", "QtWidgets"):
            self.assertNotIn(banned, source)
