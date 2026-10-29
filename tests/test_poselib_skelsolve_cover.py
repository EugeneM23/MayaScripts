"""`skelsolve.solve` on a bare skeleton, the cases `test_poselib_solve` leaves out: members the
skeleton does not hold, a root named among the members without the travel, a rotate channel
that is locked, a pelvis whose translate is locked, and a placed member's translate (a twin's
card): written when it moved, kept when it did not, written always for a steady frame.
"""
import unittest

import maya.api.OpenMaya as om

from maya_poselib import skelsolve
from tests.test_poselib_solve import SkeletonCmds, SkeletonFake, euler, placed


def bone(path, parent, canonical=None):
    return {"path": path, "parent": parent, "canonical": canonical, "world": list(om.MMatrix()),
            "rotateOrder": 0, "jointOrient": (0.0, 0.0, 0.0), "rotateAxis": (0.0, 0.0, 0.0)}


BONES = {"root": bone("|root", None, "root"), "pelvis": bone("|root|pelvis", "root", "pelvis"),
         "hand_l": bone("|root|pelvis|hand_l", "pelvis", "hand_l")}
REF = type("Ref", (), {"root": "|root"})()


class Solve(SkeletonFake):

    def solve(self, wanted, members, locked=(), values=None, **kwargs):
        self.use(SkeletonCmds(values=values), locked)
        return skelsolve.solve(REF, BONES, wanted, members, **kwargs)

    def test_the_names_of_many_members_the_skeleton_lacks_are_cut_short(self):
        gone = ["gone_%d" % i for i in range(6)]
        solution = self.solve({}, ["hand_l"] + gone)
        self.assertEqual(solution.notes,
                         ["6 member(s) not in the skeleton: gone_0, gone_1, gone_2, gone_3 and 2 more"])

    def test_a_few_members_the_skeleton_lacks_are_all_named(self):
        solution = self.solve({}, ["hand_l", "a", "b"])
        self.assertEqual(solution.notes, ["2 member(s) not in the skeleton: a, b"])

    def test_a_skeleton_that_holds_all_its_members_has_no_note(self):
        self.assertEqual(self.solve({}, ["hand_l"]).notes, [])

    def test_the_root_among_the_members_is_left_where_it_stands_without_a_word(self):
        wanted = {"root": placed(euler((0, 30, 0)), (5, 0, 7)), "hand_l": euler((0, 0, 20))}
        solution = self.solve(wanted, ["root", "hand_l"])
        self.assertEqual([p for p in solution.values if p.startswith("|root.")], [])
        self.assertEqual(solution.skipped, {})
        self.assertEqual(solution.notes, [])
        self.assertIn("|root|pelvis|hand_l.rotateZ", solution.values)

    def test_a_locked_rotate_skips_that_member_and_names_the_channel(self):
        wanted = {"hand_l": euler((0, 0, 20)), "pelvis": euler((0, 10, 0))}
        solution = self.solve(wanted, ["pelvis", "hand_l"], locked=["|root|pelvis|hand_l.rotateY"])
        self.assertEqual(solution.skipped, {"hand_l": "rotateY locked"})
        self.assertEqual([p for p in solution.values if p.startswith("|root|pelvis|hand_l.")], [])
        self.assertIn("|root|pelvis.rotateY", solution.values)

    def test_a_pelvis_with_a_locked_translate_keeps_its_rotation_and_names_the_translate(self):
        solution = self.solve({"pelvis": placed(euler((0, 10, 0)), (0, 96, 0))}, ["pelvis"],
                              locked=["|root|pelvis.translateY"])
        self.assertEqual(solution.skipped, {"pelvis": "translateY locked"})
        self.assertAlmostEqual(solution.values["|root|pelvis.rotateY"], 10.0, 6)
        self.assertNotIn("|root|pelvis.translateY", solution.values)

    def test_a_pelvis_with_locked_rotate_and_translate_names_both(self):
        solution = self.solve({"pelvis": placed(euler((0, 10, 0)), (0, 96, 0))}, ["pelvis"],
                              locked=["|root|pelvis.rotateX", "|root|pelvis.translateZ"])
        self.assertEqual(solution.skipped, {"pelvis": "rotateX locked; translateZ locked"})
        self.assertEqual(solution.values, {})

    def test_a_pelvis_writes_its_translate_against_its_parent(self):
        solution = self.solve({"pelvis": placed(om.MMatrix(), (1, 96, -2))}, ["pelvis"])
        got = [solution.values["|root|pelvis.translate" + axis] for axis in "XYZ"]
        for value, want in zip(got, (1.0, 96.0, -2.0)):
            self.assertAlmostEqual(value, want, 6)


class PlacedMembers(SkeletonFake):

    HAND = "|root|pelvis|hand_l"

    def solve(self, at, now=(0.0, 0.0, 0.0), locked=(), steady=False, members_placed=("hand_l",)):
        values = dict((self.HAND + ".translate" + axis, v) for axis, v in zip("XYZ", now))
        self.use(SkeletonCmds(values=values), locked)
        wanted = {"hand_l": placed(om.MMatrix(), at)}
        return skelsolve.solve(REF, BONES, wanted, ["hand_l"], placed=members_placed, steady=steady)

    def test_a_placed_member_that_moved_has_its_translate_written(self):
        solution = self.solve((3.0, 0.0, 0.0))
        self.assertAlmostEqual(solution.values[self.HAND + ".translateX"], 3.0, 6)

    def test_a_placed_member_within_the_tolerance_keeps_its_translate(self):
        solution = self.solve((skelsolve.PLACE_TOL / 10.0, 0.0, 0.0))
        self.assertNotIn(self.HAND + ".translateX", solution.values)

    def test_a_steady_frame_writes_the_translate_whatever_it_differs_by(self):
        solution = self.solve((0.0, 0.0, 0.0), steady=True)
        self.assertEqual([solution.values[self.HAND + ".translate" + axis] for axis in "XYZ"],
                         [0.0, 0.0, 0.0])

    def test_a_translate_that_cannot_be_written_keeps_the_joints_own_quietly(self):
        solution = self.solve((3.0, 0.0, 0.0), locked=[self.HAND + ".translateY"])
        self.assertNotIn(self.HAND + ".translateX", solution.values)
        self.assertEqual(solution.skipped, {})

    def test_a_member_not_placed_never_has_its_translate_written(self):
        solution = self.solve((3.0, 0.0, 0.0), members_placed=())
        self.assertNotIn(self.HAND + ".translateX", solution.values)


if __name__ == "__main__":
    unittest.main()
