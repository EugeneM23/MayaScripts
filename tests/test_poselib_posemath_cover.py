"""posemath, the guards `test_poselib_posemath` leaves out: a zero direction, a blend between two
quaternions of opposite sign, a skeleton with no bones (no root, no frame, no transfer), a size
that cannot be measured, a bone pairing the lengths skip and an alignment with no direction.

Built on the synthetic skeleton of `test_poselib_posemath`; no Maya scene.
"""
import math
import unittest

import maya.api.OpenMaya as om

from maya_poselib import posemath as pm
from tests.test_poselib_posemath import rootless, skeleton, trs


def turn(degrees, axis):
    return om.MQuaternion(math.radians(degrees), om.MVector(*axis).normal()).asMatrix()


class Directions(unittest.TestCase):

    def test_a_zero_direction_makes_no_angle(self):
        self.assertEqual(pm.direction_angle((0, 0, 0), (1, 0, 0)), 0.0)
        self.assertEqual(pm.direction_angle((0, 1, 0), (0, 0, 0)), 0.0)
        self.assertEqual(pm.direction_angle((0, 0, 0), (0, 0, 0)), 0.0)

    def test_two_directions_make_the_angle_between_them(self):
        self.assertAlmostEqual(pm.direction_angle((1, 0, 0), (0, 1, 0)), 90.0, 9)
        self.assertAlmostEqual(pm.direction_angle((1, 0, 0), (-1, 0, 0)), 180.0, 9)


class BlendShortWay(unittest.TestCase):

    def test_two_turns_whose_quaternions_have_opposite_sign_blend_the_short_way(self):
        a, b = turn(180, (1, -0.9, 0)), turn(180, (-0.9, 1, 0))
        qa, qb = pm._quaternion(a), pm._quaternion(b)
        self.assertLess(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w, 0.0)
        half = pm.angle(a, b) / 2.0
        mid = pm.blend(a, b, 0.5)
        self.assertAlmostEqual(pm.angle(mid, a), half, 6)
        self.assertAlmostEqual(pm.angle(mid, b), half, 6)

    def test_the_ends_are_the_matrices_exactly_and_the_translation_is_lerped(self):
        a, b = trs((0, 0, 0), (0, 10, 0)), trs((10, 20, 30), (0, 50, 0))
        self.assertEqual(pm.flat(pm.blend(a, b, 0.0)), pm.flat(a))
        self.assertEqual(pm.flat(pm.blend(a, b, 1.0)), pm.flat(b))
        self.assertEqual(pm.flat(pm.blend(a, b, -3.0)), pm.flat(a))
        self.assertEqual(pm.flat(pm.blend(a, b, 7.0)), pm.flat(b))
        mid = pm.blend(a, b, 0.25)
        self.assertAlmostEqual(pm.position(mid).x, 2.5, 9)
        self.assertAlmostEqual(pm.angle(mid, trs((2.5, 5, 7.5), (0, 20, 0))), 0.0, 6)


class Names(unittest.TestCase):

    def test_a_namespace_is_kept_and_a_centre_bone_has_no_opposite(self):
        self.assertEqual(pm.opposite("Manny_Rig1:hand_l"), "Manny_Rig1:hand_r")
        self.assertIsNone(pm.opposite("Manny_Rig1:spine_01"))

    def test_nothing_has_no_opposite(self):
        self.assertIsNone(pm.opposite(None))
        self.assertIsNone(pm.opposite(""))


class NoBones(unittest.TestCase):

    def test_no_bones_have_no_root(self):
        self.assertIsNone(pm.root_of({}))
        self.assertIsNone(pm.root_of(None))

    def test_no_bones_have_the_identity_for_a_root_frame_twice(self):
        pose, rest = pm.root_frame({})
        self.assertEqual(pm.flat(pose), pm.flat(om.MMatrix()))
        self.assertEqual(pm.flat(rest), pm.flat(om.MMatrix()))

    def test_a_clip_of_no_bones_has_the_identity_for_a_root_frame_each_frame(self):
        worlds = [pm.flat(trs((i, 0, 0))) for i in range(3)]
        out = pm.clip_roots({}, worlds)
        self.assertEqual([pm.flat(m) for m in out], [pm.flat(om.MMatrix())] * 3)

    def test_a_transfer_onto_no_bones_poses_nothing_and_stands_nowhere(self):
        source = skeleton()
        transfer = pm.Transfer(source, {}, {}, ["hand_l"])
        self.assertEqual(transfer.frame(), {})
        self.assertEqual(transfer.kept_now(), {})
        self.assertEqual(pm.flat(transfer.place()), pm.flat(om.MMatrix()))

    def test_a_transfer_from_no_bones_leaves_every_target_bone_where_it_stands(self):
        target = skeleton({"hand_l": (0, 0, 30)})
        transfer = pm.Transfer({}, target, {}, [])
        out = transfer.frame()
        self.assertEqual(sorted(out), sorted(target))
        for leaf, bone in target.items():
            self.assertLess(pm.angle(out[leaf], pm.matrix(bone["world"])), 1e-9, leaf)
        self.assertEqual(pm.flat(transfer.place()), pm.flat(om.MMatrix()))

    def test_a_member_with_no_partner_on_the_source_is_turned_by_nothing(self):
        target = skeleton()
        transfer = pm.Transfer(skeleton(), target, {}, ["hand_l"])
        out = transfer.frame()
        self.assertLess(pm.angle(out["hand_l"], pm.matrix(target["hand_l"]["world"])), 1e-9)


class TransferGuards(unittest.TestCase):

    def test_a_top_bone_that_is_not_the_root_stays_where_it_stands(self):
        target = skeleton()
        target["zz_top"] = {"parent": None, "canonical": None, "rest": pm.flat(trs((5, 6, 7))),
                            "world": pm.flat(trs((5, 6, 7)))}
        self.assertEqual(pm.root_of(target), "root")
        source = skeleton({"hand_l": (0, 0, 30)})
        out = pm.Transfer(source, target, pm.pairs(source, target), ["hand_l"]).frame()
        self.assertEqual(pm.flat(out["zz_top"]), pm.flat(trs((5, 6, 7))))

    def test_a_member_whose_partner_the_source_does_not_hold_stands_where_it_stands(self):
        source, target = skeleton({"hand_l": (0, 0, 30)}), skeleton()
        pairs = pm.pairs(source, target)
        pairs["hand_l"] = "not_on_the_source"
        out = pm.Transfer(source, target, pairs, ["hand_l"]).frame()
        self.assertLess(pm.angle(out["hand_l"], pm.matrix(target["hand_l"]["world"])), 1e-6)

    def test_a_kept_bone_the_target_lacks_or_with_no_parent_there_keeps_nothing(self):
        source, target = skeleton(), skeleton()
        transfer = pm.Transfer(source, target, pm.pairs(source, target), ["hand_l"],
                               kept=["ghost", "root", "spine_01"])
        self.assertEqual(sorted(transfer.kept_now()), ["spine_01"])

    def test_a_kept_bone_missing_from_the_target_asked_about_keeps_nothing(self):
        source, target = skeleton(), skeleton()
        transfer = pm.Transfer(source, target, pm.pairs(source, target), ["hand_l"],
                               kept=["spine_01"])
        self.assertEqual(sorted(transfer.kept_now(target)), ["spine_01"])
        without_spine = dict((k, v) for k, v in target.items() if k != "spine_01")
        self.assertEqual(transfer.kept_now(without_spine), {})
        without_parent = dict((k, v) for k, v in target.items() if k != "pelvis")
        self.assertEqual(transfer.kept_now(without_parent), {})

    def test_a_frame_whose_source_lacks_a_bone_leaves_its_partner_where_it_stands(self):
        source, target = skeleton({"hand_l": (0, 0, 30)}), skeleton()
        transfer = pm.Transfer(source, target, pm.pairs(source, target), ["hand_l"])
        partial = dict((k, v) for k, v in source.items() if k != "hand_l")
        out = transfer.frame(source=partial)
        self.assertLess(pm.angle(out["hand_l"], pm.matrix(target["hand_l"]["world"])), 1e-6)

    def test_a_source_with_no_bones_has_the_identity_for_a_root_frame(self):
        transfer = pm.Transfer({}, skeleton(), {}, [])
        self.assertEqual(pm.flat(transfer._source_root_pose({})), pm.flat(om.MMatrix()))

    def test_a_steady_heading_is_asked_only_of_a_rootless_source_that_holds_its_root(self):
        source, target = skeleton(), skeleton()
        rooted = pm.Transfer(source, target, pm.pairs(source, target), ["hand_l"])
        self.assertIsNone(rooted._steadied(source, om.MMatrix()))
        loose = rootless(skeleton())
        transfer = pm.Transfer(loose, target, pm.pairs(loose, target), ["hand_l"])
        self.assertTrue(transfer.source_rootless)
        self.assertIsNone(transfer._steadied({}, om.MMatrix()))
        self.assertIsNone(pm.Transfer({}, target, {}, [])._steadied({}, om.MMatrix()))

    def test_a_steady_heading_that_agrees_with_the_frame_s_own_is_none_and_one_that_differs_a_turn(self):
        target = skeleton()
        loose = rootless(skeleton())
        transfer = pm.Transfer(loose, target, pm.pairs(loose, target), ["hand_l"])
        own = pm.root_frame(loose)[0]
        self.assertIsNone(transfer._steadied(loose, own))
        turned = transfer._steadied(loose, pm.matrix(own) * trs((0, 0, 0), (0, 40, 0)))
        self.assertIsNotNone(turned)
        self.assertAlmostEqual(pm.angle(turned, om.MMatrix()), 40.0, 4)


class Size(unittest.TestCase):

    def ratio(self, source, target):
        return pm.scale_between(source, target, pm.pairs(source, target))

    def test_a_bigger_body_is_the_ratio_of_the_pelvis_heights(self):
        self.assertAlmostEqual(self.ratio(skeleton(), skeleton(scale=1.5)), 1.5, 9)

    def test_within_two_percent_is_the_same_size(self):
        self.assertEqual(self.ratio(skeleton(), skeleton(scale=1.01)), 1.0)
        self.assertEqual(self.ratio(skeleton(), skeleton(scale=0.99)), 1.0)

    def test_a_pelvis_lower_than_a_centimetre_over_its_root_says_nothing_of_size(self):
        self.assertEqual(self.ratio(skeleton(), skeleton(scale=0.005)), 1.0)
        self.assertEqual(self.ratio(skeleton(scale=0.005), skeleton()), 1.0)

    def test_a_target_with_no_pelvis_or_a_source_not_pairing_it_is_the_same_size(self):
        no_pelvis = dict((k, v) for k, v in skeleton(scale=2.0).items() if k != "pelvis")
        self.assertEqual(self.ratio(skeleton(), no_pelvis), 1.0)
        source = dict((k, v) for k, v in skeleton().items() if k != "pelvis")
        self.assertEqual(self.ratio(source, skeleton(scale=2.0)), 1.0)


class Lengths(unittest.TestCase):

    def rows(self, source, target, pairs=None):
        return pm._lengths(pm.pairs(source, target) if pairs is None else pairs, source, target)

    def test_every_paired_bone_with_a_paired_ancestor_gives_a_row(self):
        rows = self.rows(skeleton(), skeleton(scale=2.0))
        self.assertTrue(rows)
        for source_length, target_length in rows:
            self.assertAlmostEqual(target_length, 2.0 * source_length, 6)

    def test_a_bone_with_no_paired_ancestor_gives_none(self):
        self.assertEqual(self.rows(skeleton(), skeleton(), {"spine_01": "spine_01"}), [])

    def test_a_partner_that_is_not_an_ancestor_of_the_partner_is_skipped(self):
        source = skeleton()
        whole = len(self.rows(source, skeleton()))
        source["hand_l"]["parent"] = "pelvis"
        self.assertEqual(len(self.rows(source, skeleton())), whole - 1)

    def test_a_bone_the_source_does_not_hold_is_skipped(self):
        source = skeleton()
        whole = len(self.rows(source, skeleton()))
        pairs = pm.pairs(source, skeleton())
        pairs["hand_l"] = "not_on_the_source"
        self.assertEqual(len(self.rows(source, skeleton(), pairs)), whole - 1)


class Alignment(unittest.TestCase):

    def test_a_direction_of_no_length_has_no_alignment(self):
        source, target = skeleton(), skeleton()
        pairs = pm.pairs(source, target)
        source["middle_01_l"]["world"] = source["hand_l"]["world"]
        self.assertIsNone(pm._alignment(source, target, pairs, "hand_l", "middle_01_l"))

    def test_a_direction_read_from_the_rests_when_the_source_bones_do_not_stand_one_in_the_other(self):
        source, target = skeleton(), skeleton()
        pairs = pm.pairs(source, target)
        source["middle_01_l"]["parent"] = "pelvis"
        source["middle_01_l"]["rest"] = source["hand_l"]["rest"]
        self.assertIsNone(pm._alignment(source, target, pairs, "hand_l", "middle_01_l"))

    def test_two_parallel_directions_align_by_nothing(self):
        source, target = skeleton(), skeleton()
        pairs = pm.pairs(source, target)
        align = pm._alignment(source, target, pairs, "hand_l", "middle_01_l")
        self.assertLess(pm.angle(align, om.MMatrix()), 1e-6)


class Twin(unittest.TestCase):

    def test_a_skeleton_is_the_twin_of_a_copy_of_itself_and_not_of_a_bigger_one(self):
        source = skeleton()
        self.assertTrue(pm.twin(pm.pairs(source, skeleton()), source, skeleton()))
        self.assertFalse(pm.twin(pm.pairs(source, skeleton(scale=2.0)), source, skeleton(scale=2.0)))

    def test_two_skeletons_with_nothing_paired_are_no_twins(self):
        self.assertFalse(pm.twin({}, skeleton(), skeleton()))


class OppositePartners(unittest.TestCase):

    def test_a_bone_with_no_canonical_name_finds_its_other_side_by_its_leaf(self):
        bones = {"Hand_L": {"parent": None}, "Hand_R": {"parent": None}, "Head": {"parent": None}}
        self.assertEqual(pm._opposites(bones), {"Hand_L": "Hand_R", "Hand_R": "Hand_L"})

    def test_a_canonical_name_wins_over_the_leaf(self):
        bones = {"arm_a": {"canonical": "hand_l"}, "arm_b": {"canonical": "hand_r"},
                 "Hand_L": {}, "Hand_R": {}}
        out = pm._opposites(bones)
        self.assertEqual((out["arm_a"], out["arm_b"]), ("arm_b", "arm_a"))

    def test_a_bone_whose_other_side_is_missing_has_no_partner(self):
        self.assertEqual(pm._opposites({"hand_l": {"canonical": "hand_l"}}), {})


if __name__ == "__main__":
    unittest.main()
