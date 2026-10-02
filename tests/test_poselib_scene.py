"""The pose library's reading of the scene - the pure halves, on skeletons as data.

`scene` answers which character a selection names, reads its skeleton as `{leaf: bone}` and
says which bones a selection means (spec 2026-10-02-pose-library-design.md, "Save"): on a rig a
CONTROL names its bones (`maya_asretarget.our_bone_map`, an IK end / a pole / an FK-IK switch the
whole limb, `Fingers_<side>` the hand's fingers, `Main` the whole body), a game bone names
itself, an AS deformation joint its game bone; on a skeleton a joint names itself; a mesh, a
group or the root the whole body. Helper bones are never members on their own, twist bones ride
with their limb. `capture` narrows members to the region chips and settles the thumbnail.

The fixture is the shipped UE5 Manny skeleton's own hierarchy (`assets/manny_skeleton_template.json`,
93 joints) plus a Mixamo-like one whose names are NOT Unreal's (canonical names given, a twist and
the end joints unnamed), so the region and limb rules are proven on both roads.
"""

import json
import os
import unittest

from maya_poselib import capture
from maya_poselib import scene

_TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "SkeldarAnim", "assets", "manny_skeleton_template.json")


def manny():
    """{leaf: {"parent", "canonical"}} of the 93-joint Manny, in the template's (parents-first)
    order; canonical None everywhere - a UE-named skeleton reads its names off its leaves."""
    with open(_TEMPLATE) as handle:
        joints = json.load(handle)["joints"]
    return dict((j["name"], {"parent": j["parent"], "canonical": None}) for j in joints)


MIXAMO_CHAIN = [
    ("Hips", None, "pelvis"), ("Spine", "Hips", "spine_01"), ("Spine1", "Spine", "spine_03"),
    ("Spine2", "Spine1", "spine_05"), ("Neck", "Spine2", "neck_01"), ("Head", "Neck", "head"),
    ("HeadTop_End", "Head", None),
    ("LeftShoulder", "Spine2", "clavicle_l"), ("LeftArm", "LeftShoulder", "upperarm_l"),
    ("LeftArmTwist", "LeftArm", None), ("LeftForeArm", "LeftArm", "lowerarm_l"),
    ("LeftHand", "LeftForeArm", "hand_l"), ("LeftHandIndex1", "LeftHand", "index_01_l"),
    ("LeftHandIndex4", "LeftHandIndex1", None),
    ("LeftUpLeg", "Hips", "thigh_l"), ("LeftLeg", "LeftUpLeg", "calf_l"),
    ("LeftFoot", "LeftLeg", "foot_l"), ("LeftToeBase", "LeftFoot", "ball_l"),
    ("LeftToe_End", "LeftToeBase", None),
]


def mixamo():
    return dict((name, {"parent": parent, "canonical": canonical})
                for name, parent, canonical in MIXAMO_CHAIN)


RIG = scene.CharacterRef("rig", "|Manny_Rig1_Character|Manny_Rig1:root", None, "Manny [rig]",
                         "Manny_Rig", "Manny", "Manny_Rig1")
SKELETON = scene.CharacterRef("skeleton", "|Manny_Skeleton_Character|root", None,
                              "Manny UE5 [skeleton]", "Manny", "Manny", "")

LEFT_ARM = ["upperarm_l", "lowerarm_l", "hand_l", "lowerarm_twist_01_l", "lowerarm_twist_02_l",
            "upperarm_twist_01_l", "upperarm_twist_02_l"]
LEFT_LEG = ["thigh_l", "calf_l", "calf_twist_01_l", "calf_twist_02_l", "foot_l", "ball_l",
            "thigh_twist_01_l", "thigh_twist_02_l"]
LEFT_FINGERS = ["index_metacarpal_l", "index_01_l", "index_02_l", "index_03_l",
                "middle_metacarpal_l", "middle_01_l", "middle_02_l", "middle_03_l",
                "pinky_metacarpal_l", "pinky_01_l", "pinky_02_l", "pinky_03_l",
                "ring_metacarpal_l", "ring_01_l", "ring_02_l", "ring_03_l",
                "thumb_01_l", "thumb_02_l", "thumb_03_l"]
HELPERS = ["camera_root", "camera_bone", "center_of_mass", "ik_foot_root", "ik_foot_l",
           "ik_foot_r", "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r", "interaction",
           "weapon_l", "weapon_r"]


class Names(unittest.TestCase):

    def test_leaf_strips_the_path_and_the_namespace(self):
        self.assertEqual(scene.leaf("|Manny_Rig1_Character|Manny_Rig1:root|Manny_Rig1:pelvis"),
                         "pelvis")
        self.assertEqual(scene.leaf("Manny_Rig1:FKWrist_L"), "FKWrist_L")
        self.assertEqual(scene.leaf("clip:mixamorig:Hips"), "Hips")
        self.assertEqual(scene.leaf("pCube1"), "pCube1")

    def test_row_key_drops_the_namespace_number(self):
        self.assertEqual(scene.row_key("Manny_Rig1"), "Manny_Rig")
        self.assertEqual(scene.row_key("Manny_Rig"), "Manny_Rig")
        self.assertEqual(scene.row_key("Orc_D_Rig12"), "Orc_D_Rig")
        self.assertEqual(scene.row_key(""), "")

    def test_canonical_names_invert_the_recognised_mapping(self):
        paths = ["|root", "|root|pelvis", "|root|pelvis|spine_01", "|root|pelvis|upperarm_twist"]
        mapping = {"root": "|root", "pelvis": "|root|pelvis", "spine_01": "|root|pelvis|spine_01"}
        self.assertEqual(scene.canonical_names(paths, mapping, refused=False),
                         {"|root": "root", "|root|pelvis": "pelvis",
                          "|root|pelvis|spine_01": "spine_01", "|root|pelvis|upperarm_twist": None})

    def test_a_bone_playing_root_and_pelvis_is_the_pelvis(self):
        # Mixamo's Hips is both its top joint and its pelvis
        paths = ["|Hips", "|Hips|Spine"]
        mapping = {"root": "|Hips", "pelvis": "|Hips", "spine_01": "|Hips|Spine"}
        names = scene.canonical_names(paths, mapping, refused=False)
        self.assertEqual(names["|Hips"], "pelvis")

    def test_a_refusal_keeps_ue_leaves_and_names_nothing_else(self):
        ue = ["|r:root"] + ["|r:root|r:" + name for name in (
            "pelvis", "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r",
            "upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r", "hand_r")]
        names = scene.canonical_names(ue, {}, refused=True)
        self.assertEqual(names["|r:root|r:hand_l"], "hand_l")
        self.assertEqual(names["|r:root"], "root")
        other = ["|Hips", "|Hips|LeftArm"]
        self.assertEqual(scene.canonical_names(other, {}, refused=True),
                         {"|Hips": None, "|Hips|LeftArm": None})


class Regions(unittest.TestCase):

    def test_ue_bones_take_their_region_from_their_leaf(self):
        regions = scene.bone_regions(manny())
        self.assertEqual(regions["hand_l"], "Hand L")
        self.assertEqual(regions["index_02_l"], "Hand L")
        self.assertEqual(regions["upperarm_twist_01_r"], "Arm R")
        self.assertEqual(regions["clavicle_l"], "Arm L")
        self.assertEqual(regions["calf_twist_02_l"], "Leg L")
        self.assertEqual(regions["neck_02"], "Head")
        self.assertEqual(regions["spine_04"], "Spine")
        self.assertEqual(regions["pelvis"], "Pelvis")
        self.assertIsNone(regions["root"])
        self.assertIsNone(regions["ik_hand_gun"])
        self.assertIsNone(regions["weapon_l"])

    def test_an_unnamed_bone_takes_its_nearest_named_ancestors_region(self):
        regions = scene.bone_regions(mixamo())
        self.assertEqual(regions["LeftArmTwist"], "Arm L")
        self.assertEqual(regions["LeftHandIndex4"], "Hand L")
        self.assertEqual(regions["LeftToe_End"], "Leg L")
        self.assertEqual(regions["HeadTop_End"], "Head")
        self.assertEqual(regions["Hips"], "Pelvis")

    def test_regions_of_members_in_card_order(self):
        self.assertEqual(scene.regions_of(manny(), ["index_01_l", "hand_l", "upperarm_l",
                                                    "head"]),
                         ["Head", "Arm L", "Hand L"])
        self.assertEqual(scene.regions_of(manny(), []), [])


class WholeBody(unittest.TestCase):

    def test_every_bone_but_the_helpers_and_the_root(self):
        bones = manny()
        body = scene.whole_body(bones)
        self.assertEqual(len(body), 93 - len(HELPERS) - 1)
        for name in HELPERS + ["root"]:
            self.assertNotIn(name, body)
        for name in ("pelvis", "upperarm_twist_01_l", "thumb_03_r", "ball_r", "head"):
            self.assertIn(name, body)

    def test_in_skeleton_order(self):
        bones = manny()
        body = scene.whole_body(bones)
        self.assertEqual(body, [b for b in bones if b in set(body)])

    def test_a_skeleton_whose_top_joint_is_its_pelvis_keeps_it(self):
        # Mixamo's Hips: dropping "the root" would drop the hips' turn from every pose
        body = scene.whole_body(mixamo())
        self.assertIn("Hips", body)
        self.assertEqual(len(body), len(MIXAMO_CHAIN))


class Limbs(unittest.TestCase):

    def test_the_arm_is_upperarm_to_hand_with_twists_and_no_clavicle(self):
        self.assertEqual(sorted(scene.limb_bones(manny(), "arm", "l")), sorted(LEFT_ARM))

    def test_the_leg_is_thigh_to_ball_with_twists(self):
        self.assertEqual(sorted(scene.limb_bones(manny(), "leg", "l")), sorted(LEFT_LEG))

    def test_the_hand_is_the_hand_its_fingers_and_metacarpals(self):
        hand = scene.limb_bones(manny(), "hand", "r")
        self.assertEqual(sorted(hand),
                         sorted(["hand_r"] + [b[:-1] + "r" for b in LEFT_FINGERS]))
        self.assertNotIn("weapon_r", hand)

    def test_the_fingers_leave_the_hand_out(self):
        self.assertEqual(sorted(scene.limb_bones(manny(), "fingers", "l")),
                         sorted(LEFT_FINGERS))

    def test_limbs_on_a_skeleton_not_named_by_unreal(self):
        bones = mixamo()
        self.assertEqual(sorted(scene.limb_bones(bones, "arm", "l")),
                         sorted(["LeftArm", "LeftArmTwist", "LeftForeArm", "LeftHand"]))
        self.assertEqual(sorted(scene.limb_bones(bones, "hand", "l")),
                         sorted(["LeftHand", "LeftHandIndex1", "LeftHandIndex4"]))
        self.assertEqual(sorted(scene.limb_bones(bones, "leg", "l")),
                         sorted(["LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
                                 "LeftToe_End"]))
        self.assertEqual(scene.limb_bones(bones, "arm", "r"), [])

    def test_an_unknown_limb_raises(self):
        with self.assertRaises(ValueError):
            scene.limb_bones(manny(), "tail", "l")


class MembersOnARig(unittest.TestCase):

    def members(self, *selection):
        return scene.members_from_selection(RIG, list(selection), manny())

    def test_an_fk_control_names_its_bone(self):
        self.assertEqual(self.members(("Manny_Rig1:FKWrist_L", "transform")), ["hand_l"])

    def test_an_fk_control_brings_the_twists_that_ride_its_bone(self):
        self.assertEqual(sorted(self.members(("Manny_Rig1:FKShoulder_L", "transform"))),
                         ["upperarm_l", "upperarm_twist_01_l", "upperarm_twist_02_l"])

    def test_an_extra_group_names_what_its_control_does(self):
        self.assertEqual(self.members(("Manny_Rig1:FKExtraWrist_L", "transform")), ["hand_l"])

    def test_an_ik_end_a_pole_and_the_switch_name_the_whole_arm(self):
        for name in ("IKArm_L", "PoleArm_L", "FKIKArm_L", "IKExtraArm_L", "PoleExtraArm_L"):
            self.assertEqual(sorted(self.members(("Manny_Rig1:" + name, "transform"))),
                             sorted(LEFT_ARM), name)

    def test_the_leg_controls_name_the_whole_leg(self):
        for name in ("IKLeg_R", "PoleLeg_R", "FKIKLeg_R"):
            self.assertEqual(sorted(self.members(("Manny_Rig1:" + name, "transform"))),
                             sorted(b[:-1] + "r" for b in LEFT_LEG), name)

    def test_the_toe_control_names_the_ball(self):
        self.assertEqual(self.members(("Manny_Rig1:IKToes_L", "transform")), ["ball_l"])

    def test_the_fingers_control_names_the_hands_fingers(self):
        self.assertEqual(sorted(self.members(("Manny_Rig1:Fingers_L", "transform"))),
                         sorted(LEFT_FINGERS))

    def test_main_names_the_whole_body(self):
        self.assertEqual(self.members(("Manny_Rig1:Main", "transform")),
                         scene.whole_body(manny()))

    def test_rootx_names_the_pelvis(self):
        self.assertEqual(self.members(("Manny_Rig1:RootX_M", "transform")), ["pelvis"])

    def test_the_spine_switch_names_the_spine(self):
        self.assertEqual(self.members(("Manny_Rig1:FKIKSpine_M", "transform")),
                         ["spine_01", "spine_02", "spine_03", "spine_04", "spine_05"])

    def test_a_game_bone_names_itself(self):
        path = "|Manny_Rig1_Character|Manny_Rig1:root|Manny_Rig1:pelvis|" \
               "Manny_Rig1:spine_01|Manny_Rig1:hand_l"
        self.assertEqual(self.members((path, "joint")), ["hand_l"])

    def test_a_twist_bone_names_the_bone_it_rides(self):
        self.assertEqual(sorted(self.members(("Manny_Rig1:lowerarm_twist_02_l", "joint"))),
                         ["lowerarm_l", "lowerarm_twist_01_l", "lowerarm_twist_02_l"])

    def test_a_deformation_joint_names_its_game_bone(self):
        self.assertEqual(self.members(("Manny_Rig1:Wrist_L", "joint")), ["hand_l"])
        self.assertEqual(self.members(("Manny_Rig1:Root_M", "joint")), ["pelvis"])
        self.assertEqual(self.members(("Manny_Rig1:NeckPart1_M", "joint")), ["neck_02"])
        self.assertEqual(self.members(("Manny_Rig1:Toes_R", "joint")), ["ball_r"])

    def test_the_fk_and_ik_joints_and_the_part_joints_name_their_bone(self):
        self.assertEqual(sorted(self.members(("Manny_Rig1:FKXElbow_L", "joint"))),
                         ["lowerarm_l", "lowerarm_twist_01_l", "lowerarm_twist_02_l"])
        self.assertEqual(self.members(("Manny_Rig1:IKXWrist_R", "joint")), ["hand_r"])
        self.assertEqual(sorted(self.members(("Manny_Rig1:ShoulderPart1_L", "joint"))),
                         ["upperarm_l", "upperarm_twist_01_l", "upperarm_twist_02_l"])

    def test_an_unknown_joint_of_the_rig_names_the_whole_body(self):
        self.assertEqual(self.members(("Manny_Rig1:Heel_L", "joint")), scene.whole_body(manny()))

    def test_an_unknown_control_a_group_and_a_mesh_name_the_whole_body(self):
        body = scene.whole_body(manny())
        self.assertEqual(self.members(("Manny_Rig1:HipSwinger_M", "transform")), body)
        self.assertEqual(self.members(("Manny_Rig1:Group", "transform")), body)
        self.assertEqual(self.members(("Manny_Rig1:SKM_Manny_Simple", "mesh")), body)

    def test_the_whole_body_swallows_the_rest(self):
        self.assertEqual(self.members(("Manny_Rig1:FKWrist_L", "transform"),
                                      ("Manny_Rig1:Main", "transform")),
                         scene.whole_body(manny()))

    def test_a_helper_bone_is_never_a_member_on_its_own(self):
        self.assertEqual(self.members(("Manny_Rig1:weapon_r", "joint"),
                                      ("Manny_Rig1:FKWrist_L", "transform")), ["hand_l"])
        # alone it names nothing, and nothing means the whole body
        self.assertEqual(self.members(("Manny_Rig1:ik_hand_gun", "joint")),
                         scene.whole_body(manny()))

    def test_an_accessory_names_the_character_but_no_bone(self):
        self.assertEqual(self.members(("LongSwordMesh", "accessory"),
                                      ("Manny_Rig1:FKWrist_R", "transform")), ["hand_r"])
        self.assertEqual(self.members(("LongSwordMesh", "accessory")), scene.whole_body(manny()))

    def test_several_controls_union_in_skeleton_order(self):
        self.assertEqual(self.members(("Manny_Rig1:FKWrist_L", "transform"),
                                      ("Manny_Rig1:FKHead_M", "transform"),
                                      ("Manny_Rig1:FKWrist_L", "transform")),
                         ["hand_l", "head"])

    def test_the_root_joint_names_the_whole_body(self):
        self.assertEqual(self.members(("Manny_Rig1:root", "joint")), scene.whole_body(manny()))


class MembersOnASkeleton(unittest.TestCase):

    def members(self, *selection):
        return scene.members_from_selection(SKELETON, list(selection), manny())

    def test_a_joint_names_itself(self):
        self.assertEqual(self.members(("|Manny_Skeleton_Character|root|pelvis|thigh_r", "joint")),
                         ["thigh_r", "thigh_twist_01_r", "thigh_twist_02_r"])
        self.assertEqual(self.members(("index_03_l", "joint")), ["index_03_l"])

    def test_control_names_mean_nothing_on_a_skeleton(self):
        # a transform called FKWrist_L in a skeleton's group is not a control of ours
        self.assertEqual(self.members(("FKWrist_L", "transform")), scene.whole_body(manny()))

    def test_a_mesh_the_group_and_the_root_name_the_whole_body(self):
        body = scene.whole_body(manny())
        self.assertEqual(self.members(("SKM_Manny_Simple", "mesh")), body)
        self.assertEqual(self.members(("Manny_Skeleton_Character", "transform")), body)
        self.assertEqual(self.members(("root", "joint")), body)

    def test_a_joint_the_skeleton_does_not_hold_names_the_whole_body(self):
        self.assertEqual(self.members(("stray_joint", "joint")), scene.whole_body(manny()))

    def test_an_unnamed_bone_rides_with_its_named_ancestor(self):
        bones = mixamo()
        ref = SKELETON._replace(key=None, model=None, label="Mixamo")
        self.assertEqual(scene.members_from_selection(ref, [("LeftHandIndex1", "joint")], bones),
                         ["LeftHandIndex1", "LeftHandIndex4"])
        self.assertEqual(scene.members_from_selection(ref, [("LeftArmTwist", "joint")], bones),
                         ["LeftArm", "LeftArmTwist"])


class Describe(unittest.TestCase):

    def test_what_the_save_panel_says_about_the_selection(self):
        self.assertEqual(scene.describe([RIG], []), "Manny [rig] (Manny_Rig1)")
        self.assertEqual(scene.describe([SKELETON], ["|pCube1"]), "Manny UE5 [skeleton] (root)")
        self.assertEqual(scene.describe([RIG, SKELETON], []),
                         "2 characters selected - pick one character for a pose")
        self.assertEqual(scene.describe([], ["|pCube1", "|pCube2"]), "2 objects")
        self.assertEqual(scene.describe([], ["|pCube1"]), "1 object")
        self.assertEqual(scene.describe([], []), "nothing selected")


class RegionMembers(unittest.TestCase):

    def test_no_regions_keeps_the_members(self):
        self.assertEqual(capture.region_members(manny(), ["hand_l", "head"], None),
                         ["hand_l", "head"])

    def test_regions_narrow_the_members(self):
        bones = manny()
        hand = capture.region_members(bones, scene.whole_body(bones), ["Hand L"])
        self.assertEqual(sorted(hand), sorted(["hand_l"] + LEFT_FINGERS))

    def test_a_region_the_members_do_not_touch_comes_in_whole(self):
        # the save panel's chips: one turned ON that the selection did not light
        bones = manny()
        got = capture.region_members(bones, ["hand_l"], ["Hand L", "Head"])
        self.assertEqual(got, ["hand_l", "neck_01", "neck_02", "head"])

    def test_an_empty_region_list_leaves_nothing(self):
        self.assertEqual(capture.region_members(manny(), ["hand_l"], []), [])

    def test_in_skeleton_order_and_without_helpers(self):
        bones = manny()
        got = capture.region_members(bones, ["hand_r"], ["Arm R"])
        self.assertEqual(got, [b for b in bones if b in set(got)])
        self.assertNotIn("weapon_r", got)
        self.assertNotIn("hand_r", got)      # the hand is Hand R, not Arm R
        self.assertIn("clavicle_r", got)     # a region is wider than a limb


class Thumbnail(unittest.TestCase):

    def test_the_centred_square(self):
        self.assertEqual(capture.square(1600, 900), (350, 0, 900))
        self.assertEqual(capture.square(500, 800), (0, 150, 500))
        self.assertEqual(capture.square(1601, 900), (350, 0, 900))
        self.assertEqual(capture.square(640, 640), (0, 0, 640))

    def settle(self, pictures, least=3, most=5):
        shots, pumps = list(pictures), []
        taken = []

        def blast():
            taken.append(shots.pop(0))
            return taken[-1]

        result = capture.settle(blast, lambda: pumps.append(1), least=least, most=most)
        return result, len(taken), len(pumps)

    def test_two_equal_blasts_after_at_least_three_settle_it(self):
        (picture, count, settled), taken, pumps = self.settle([b"a", b"b", b"b", b"x"])
        self.assertEqual((picture, count, settled, taken), (b"b", 3, True, 3))
        self.assertEqual(pumps, 2)            # idle pumped BETWEEN blasts

    def test_equal_first_two_still_take_a_third(self):
        # trap 120: two early blasts can agree on a half-loaded texture
        (picture, count, settled), taken, _ = self.settle([b"a", b"a", b"a", b"x"])
        self.assertEqual((picture, count, settled), (b"a", 3, True))

    def test_a_later_settle(self):
        (picture, count, settled), _, _ = self.settle([b"a", b"b", b"c", b"c", b"x"])
        self.assertEqual((picture, count, settled), (b"c", 4, True))

    def test_never_settling_gives_the_last_after_five(self):
        (picture, count, settled), taken, _ = self.settle([b"a", b"b", b"c", b"d", b"e", b"f"])
        self.assertEqual((picture, count, settled, taken), (b"e", 5, False, 5))


class SquareJpg(unittest.TestCase):
    """The thumbnail's Qt half on a picture made here: a QImage needs no QApplication, so this
    runs headless (the playblast half needs a viewport and is proven in the GUI verify)."""

    def setUp(self):
        import tempfile
        import maya_hubqt
        self.qt = maya_hubqt.qt()
        if self.qt is None:
            self.skipTest("no Qt")
        self.dir = tempfile.mkdtemp(prefix="poselib_thumb_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def picture(self, width, height):
        """`width` x `height`, blue outside the centred square, red inside."""
        gui = self.qt.QtGui
        image = gui.QImage(width, height, gui.QImage.Format_RGB32)
        image.fill(gui.QColor(0, 0, 255))
        x, y, side = capture.square(width, height)
        painter = gui.QPainter(image)
        painter.fillRect(x, y, side, side, gui.QColor(255, 0, 0))
        painter.end()
        path = os.path.join(self.dir, "raw.png")
        self.assertTrue(image.save(path, "PNG"))
        return path

    def test_the_centre_square_scaled_and_written_whole(self):
        source, target = self.picture(800, 450), os.path.join(self.dir, "thumbnail.jpg")
        self.assertEqual(capture.square_jpg(self.qt, source, target, 320), (True, ""))
        image = self.qt.QtGui.QImage(target)
        self.assertEqual((image.width(), image.height()), (320, 320))
        for x, y in ((2, 2), (317, 2), (2, 317), (317, 317), (160, 160)):
            colour = image.pixelColor(x, y)
            self.assertGreater(colour.red(), 200, (x, y))     # nothing of the blue margins
            self.assertLess(colour.blue(), 60, (x, y))
        self.assertEqual(sorted(os.listdir(self.dir)), ["raw.png", "thumbnail.jpg"])  # no .part

    def test_a_picture_that_cannot_be_read_writes_nothing(self):
        target = os.path.join(self.dir, "thumbnail.jpg")
        ok, note = capture.square_jpg(self.qt, os.path.join(self.dir, "missing.jpg"), target)
        self.assertFalse(ok)
        self.assertIn("nothing readable", note)
        self.assertFalse(os.path.exists(target))


if __name__ == "__main__":
    unittest.main()
