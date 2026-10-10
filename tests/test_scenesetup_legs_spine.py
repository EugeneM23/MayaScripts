"""The pure halves of the FK / IK switch of the legs and the spine (2026-10-10).

The scene-touching paths are proved by docs/superpowers/plans/verify_fkik_legs.py and
verify_fkik_spine.py (mayapy standalone); these are the arithmetic and the wording.
"""
import math
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import fkik
from maya_scenesetup import fkikspine

IDENTITY = om.MMatrix()


def turn_z(degrees):
    return om.MEulerRotation(0.0, 0.0, math.radians(degrees)).asMatrix()


class Rotation(unittest.TestCase):
    def test_no_turn_is_no_vector(self):
        self.assertAlmostEqual(fkik.rotation_vector(IDENTITY, IDENTITY).length(), 0.0)

    def test_a_quarter_turn_about_z_is_a_quarter_radian_pi_over_two(self):
        vector = fkik.rotation_vector(turn_z(90.0), IDENTITY)
        self.assertAlmostEqual(vector.length(), math.pi / 2, places=6)
        self.assertAlmostEqual(abs(vector.z), math.pi / 2, places=6)
        self.assertAlmostEqual(vector.x, 0.0, places=6)

    def test_joint_residual_is_zero_for_equal_matrices(self):
        out = fkik.joint_residual([turn_z(20.0), IDENTITY], [turn_z(20.0), IDENTITY])
        self.assertEqual(len(out), 12)
        self.assertTrue(all(abs(v) < 1e-9 for v in out))

    def test_joint_residual_weighs_a_turn_by_the_orient_weight(self):
        out = fkik.joint_residual([IDENTITY], [turn_z(90.0)])
        self.assertAlmostEqual(abs(out[5]), math.pi / 2 * fkik.ORIENT_WEIGHT, places=5)


class LinearAlgebra(unittest.TestCase):
    def test_solve3_recovers_the_coefficients(self):
        columns = [om.MVector(1, 0, 0), om.MVector(0, 2, 0), om.MVector(0, 0, 4)]
        x = fkik.solve3(columns, om.MVector(1, 2, 4))
        for got, want in zip(x, (1.0, 1.0, 1.0)):
            self.assertAlmostEqual(got, want)

    def test_solve3_refuses_degenerate_columns(self):
        columns = [om.MVector(1, 0, 0), om.MVector(1, 0, 0), om.MVector(0, 0, 1)]
        self.assertIsNone(fkik.solve3(columns, om.MVector(1, 1, 1)))

    def test_solve_linear_two_by_two(self):
        x = fkik.solve_linear([[2.0, 1.0], [1.0, 3.0]], [3.0, 5.0])
        self.assertAlmostEqual(x[0], 0.8)
        self.assertAlmostEqual(x[1], 1.4)

    def test_solve_linear_refuses_a_singular_system(self):
        self.assertIsNone(fkik.solve_linear([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0]))

    def test_gauss_newton_step_solves_a_one_dimensional_fit(self):
        # residual -1 and -2 against a Jacobian of 1 and 2: the step that zeroes it is 1
        dx = fkik.gauss_newton_step([[1.0], [2.0]], [-1.0, -2.0], damp=1e-9)
        self.assertAlmostEqual(dx[0], 1.0, places=6)

    def test_the_spine_uses_the_limbs_helpers(self):
        self.assertIs(fkikspine.solve_linear, fkik.solve_linear)
        self.assertIs(fkikspine.gauss_newton_step, fkik.gauss_newton_step)


class BendPlane(unittest.TestCase):
    def test_a_straight_leg_has_no_bend_to_read(self):
        self.assertIsNone(fkik.bend_side(om.MVector(0, 0, 0), om.MVector(0, 5, 0),
                                         om.MVector(0, 10, 0)))

    def test_a_bent_knee_gives_the_unit_side_it_bends_to(self):
        side = fkik.bend_side(om.MVector(0, 0, 0), om.MVector(3, 5, 0), om.MVector(0, 10, 0))
        self.assertAlmostEqual(side.length(), 1.0, places=9)
        self.assertAlmostEqual(side.x, 1.0, places=6)
        self.assertAlmostEqual(side.y, 0.0, places=6)

    def test_the_pole_stands_on_the_bend_side_a_limb_out(self):
        s, e, w = om.MVector(0, 0, 0), om.MVector(3, 5, 0), om.MVector(0, 10, 0)
        pole = fkik.pole_on_side(s, e, w, fkik.bend_side(s, e, w))
        self.assertGreater(pole.x, 0.0)
        self.assertAlmostEqual(pole.z, 0.0, places=9)
        # the knee's own distance from the line is well inside the pole's reach
        self.assertGreater(pole.x, 3.0)


class Measure(unittest.TestCase):
    def test_a_turned_toes_joint_is_the_end_not_a_roll(self):
        before = {0: [IDENTITY, IDENTITY, IDENTITY, IDENTITY]}
        after = {0: [IDENTITY, IDENTITY, IDENTITY, turn_z(10.0)]}
        m = fkik.measure(before, after)
        self.assertAlmostEqual(m.hand, 10.0, places=4)
        self.assertAlmostEqual(m.roll, 0.0, places=6)
        self.assertAlmostEqual(m.cm, 0.0, places=9)


class Wording(unittest.TestCase):
    def test_every_kind_has_its_label_and_its_words(self):
        self.assertEqual(set(fkik.LABEL), {fkik.ARM, fkik.LEG, fkik.SPINE})
        self.assertEqual(set(fkik.ROLL_WORDS), {fkik.ARM, fkik.LEG, fkik.SPINE})

    def test_a_leg_is_named_as_a_leg(self):
        m = fkik.Measure(0.0, 0, 0.0, 0.0, 0)
        text = fkik.switched_message("R", fkik.IK, (0, 24, False), m, [], kind=fkik.LEG)
        self.assertTrue(text.startswith("Leg_R to IK over 0..24"), text)
        self.assertIn("the leg kept to 0.0000 cm", text)

    def test_a_knee_roll_is_said_as_the_knees_not_the_forearms(self):
        m = fkik.Measure(0.0, 0, 0.0, 84.0, 12)
        text = fkik.switched_message("R", fkik.IK, (0, 24, False), m, [], kind=fkik.LEG)
        self.assertIn("the knee's roll differs", text)
        self.assertNotIn("forearm", text)

    def test_an_arm_keeps_its_forearm_words(self):
        m = fkik.Measure(0.0, 0, 0.0, 59.0, 12)
        text = fkik.switched_message("R", fkik.IK, (0, 24, False), m, [])
        self.assertIn("the FK forearm twist is lost", text)
        self.assertTrue(text.startswith("Arm_R to IK"), text)


class LimbShape(unittest.TestCase):
    def test_a_limb_is_an_arm_unless_it_says_otherwise(self):
        arm = fkik.Limb("R", "b", [], [], [], [], "ik", "pole", "align", "root", (1.0,))
        self.assertEqual(arm.kind, fkik.ARM)
        self.assertIsNone(arm.tip)

    def test_the_toes_are_a_tip_of_the_leg(self):
        leg = fkik.Limb("R", "b", [], [], [], [], "ik", "pole", "align", "root", (1.0,),
                        fkik.LEG, fkik.Tip("ik_toes", "align_toes"))
        self.assertEqual(fkik._ik_controls(leg), ["ik", "pole", "ik_toes"])


class Spine(unittest.TestCase):
    def test_the_spine_has_five_joints_of_which_four_are_blended(self):
        self.assertEqual(fkikspine.BLENDED, 4)
        self.assertEqual(len(fkikspine.DEFORM), 5)
        self.assertEqual(len(fkikspine.IKX), 4)
        self.assertEqual(len(fkikspine.CV_CONTROLS), 5)

    def test_the_fit_moves_the_cv_translates_and_the_two_end_turns(self):
        sp = fkikspine.Spine("blend", [], [], [], [], list(fkikspine.CV_CONTROLS), "M",
                             fkik.SPINE)
        plugs = fkikspine._cv_plugs(sp)
        self.assertEqual(len(plugs), 15 + 6)
        turns = [(node, ch) for node, ch in plugs if ch.startswith("rotate")]
        self.assertEqual(sorted(set(node for node, _ch in turns)),
                         sorted([fkikspine.CV_CONTROLS[0], fkikspine.CV_CONTROLS[-1]]))


if __name__ == "__main__":
    unittest.main()
