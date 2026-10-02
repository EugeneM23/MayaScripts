"""The IK limbs take the FK limbs' shape (maya_ikmatch, 2026-10-02).

The animator: «анимация IK должна соответствовать анимации FK это обязательное условие» - after
a squash & stretch take the FK limbs carried the clip's lengths and an IK limb showed the rig's
own. The pure halves: the Lenght that makes an IK segment as long as the FK one, a point in a
parent's space, a node moved onto a point whatever its pivot, a series collapsed to its rest or
one value, one frame's values for an arm and a leg, the status words - and the plans that make
every IK end and pole follow the rig's own FK.

Spec: docs/superpowers/specs/2026-10-02-ik-follows-fk-design.md
"""

import math
import os
import unittest

import maya.api.OpenMaya as om

import maya_asretarget as ar
import maya_ikmatch as ikm
from maya_scenesetup import fkik

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def matrix(rx=0.0, ry=0.0, rz=0.0, t=(0.0, 0.0, 0.0), scale=1.0):
    tm = om.MTransformationMatrix(om.MEulerRotation(
        math.radians(rx), math.radians(ry), math.radians(rz)).asMatrix())
    tm.setScale((scale, scale, scale), om.MSpace.kTransform)
    tm.setTranslation(om.MVector(*t), om.MSpace.kTransform)
    return tm.asMatrix()


def close(a, b, tol=1e-9):
    return all(abs(p - q) <= tol for p, q in zip(a, b))


class Lenght(unittest.TestCase):

    def test_the_fk_segment_over_the_ik_rest(self):
        # the Creep's upper arm: 34.8148 at rest, the clip's 27.771
        self.assertAlmostEqual(ikm.lenght((0, 0, 0), (27.771, 0, 0), 34.8148, 1.0),
                               27.771 / 34.8148, places=12)

    def test_the_left_sides_negative_rest_reads_as_its_length(self):
        # AdvancedSkeleton's left chain runs down -X: input2X is negative there
        self.assertAlmostEqual(ikm.lenght((0, 0, 0), (-20.0, 0, 0), -25.0, 1.0), 0.8, places=12)

    def test_a_scaled_rig_divides_by_its_scale(self):
        # Main at 2: the rest 25 in the chain is 50 in the world (the vendor divides by
        # MainScaleMultiplyDivide the same way)
        self.assertAlmostEqual(ikm.lenght((0, 0, 0), (0, 40.0, 0), 25.0, 2.0), 0.8, places=12)

    def test_no_unit_no_lenght(self):
        self.assertIsNone(ikm.lenght((0, 0, 0), (1, 0, 0), None, 1.0))
        self.assertIsNone(ikm.lenght((0, 0, 0), (1, 0, 0), 0.0, 1.0))

    def test_the_scale_is_the_first_rows_length(self):
        self.assertAlmostEqual(ikm.scale_of(matrix(30, 10, 5, (1, 2, 3), 1.7)), 1.7, places=12)


class Points(unittest.TestCase):

    def test_a_world_point_in_a_turned_parent(self):
        parent = matrix(0, 0, 90, (10, 0, 0))
        # row vectors: world = local * parent; local x along the parent's X = world +Y
        self.assertTrue(close(ikm.local_point((10, 5, 0), parent), (5, 0, 0), 1e-9))

    def test_a_move_lands_the_node_on_the_point_whatever_its_pivot(self):
        parent = matrix(20, -35, 50, (3, 4, 5), 1.3)
        local = (1.0, 2.0, 3.0)
        # the node's own point stands somewhere its translate alone does not say (a pivot)
        now = om.MVector(7.0, -2.0, 4.0)
        wanted = om.MVector(9.5, 1.0, 2.0)
        moved = ikm.moved_local(local, now, wanted, parent)
        # moving by (moved - local) in the parent's space moves the point onto `wanted`
        step = (om.MVector(*moved) - om.MVector(*local)) * parent
        self.assertTrue(close(now + step, wanted, 1e-9))


class Series(unittest.TestCase):

    def test_every_value_at_rest_is_the_rest(self):
        self.assertEqual(ikm.plan_series([1.0, 1.0 + 1e-7, 1.0 - 1e-7], 1.0), ("rest", 1.0))

    def test_one_value_off_its_rest_is_a_value(self):
        kind, value = ikm.plan_series([0.798, 0.798 + 2e-7], 1.0)
        self.assertEqual(kind, "value")
        self.assertAlmostEqual(value, 0.798 + 1e-7, places=12)

    def test_a_moving_series_is_keys(self):
        self.assertEqual(ikm.plan_series([0.99, 1.0, 1.01], 1.0), ("keys", [0.99, 1.0, 1.01]))

    def test_the_tolerance_is_the_callers(self):
        self.assertEqual(ikm.plan_series([1.0, 1.000005], 1.0, ikm.TOL_RATIO)[0], "rest")
        self.assertEqual(ikm.plan_series([1.0, 1.000005], 1.0, 1e-7)[0], "keys")

    def test_the_bakes_frames(self):
        self.assertEqual(ikm.frames_of(3, 6), [3.0, 4.0, 5.0, 6.0])
        self.assertEqual(ikm.frames_of(0, 0), [0.0])


ARM = ikm.Limb("arm_r", "IKArm_R", ["FKXShoulder_R", "FKXElbow_R", "FKXWrist_R"],
               ["IKXShoulder_R", "IKXElbow_R", "IKXWrist_R"], "IKXOffsetShoulder_R",
               (30.0, 28.0), None)
LEG = ikm.Limb("leg_l", "IKLeg_L", ["FKXHip_L", "FKXKnee_L", "FKXAnkle_L"],
               ["IKXHip_L", "IKXKnee_L", "IKXAnkle_L"], "IKXOffsetHip_L", (-43.0, -42.0),
               ikm.Foot("FKXToes_L", "IKXToes_L", "IKAnkleHandle_L", "IKOffsetToes_L"))


class FrameValues(unittest.TestCase):

    def test_an_arm_stretched_and_slid(self):
        # the FK shoulder slid 2 cm off the clavicle's end, its segments 24 and 21 long
        sample = {"fkx": [matrix(t=(2, 150, 0)), matrix(t=(26, 150, 0)), matrix(t=(26, 129, 0))],
                  "root_parent": matrix(0, 0, 0, (0, 150, 0))}
        values = ikm.frame_values(ARM, sample)
        self.assertTrue(close(values[("IKXShoulder_R", "translate")], (2, 0, 0)))
        self.assertAlmostEqual(values[("IKArm_R", "Lenght1")], 24.0 / 30.0, places=12)
        self.assertAlmostEqual(values[("IKArm_R", "Lenght2")], 21.0 / 28.0, places=12)
        self.assertEqual(len(values), 3)

    def test_a_rig_without_lenght_moves_only_the_root(self):
        bare = ARM._replace(units=(None, None))
        sample = {"fkx": [matrix(t=(2, 150, 0)), matrix(t=(26, 150, 0)), matrix(t=(26, 129, 0))],
                  "root_parent": matrix(0, 0, 0, (0, 150, 0))}
        self.assertEqual(list(ikm.frame_values(bare, sample)), [("IKXShoulder_R", "translate")])

    def test_a_leg_puts_the_ball_handle_and_toe_pivot_on_the_fk_ball(self):
        ankle = matrix(0, 30, 0, (10, 8, 0))
        ball = (10.0, 1.0, 14.0)
        handle_parent = matrix(0, 0, 15, (9, 0, 12))
        offset_parent = matrix(10, 0, 0, (11, 0, 13), 1.0)
        sample = {"fkx": [matrix(t=(10, 90, 0)), matrix(t=(10, 50, 0)), ankle],
                  "root_parent": matrix(t=(10, 90, 0)),
                  "toes": matrix(t=ball),
                  "IKAnkleHandle_L": (matrix(t=(10, 1.5, 12.5)), handle_parent, (0.4, 0.5, 0.6)),
                  "IKOffsetToes_L": (matrix(t=(10, 1.5, 12.5)), offset_parent, (0.1, 0.2, 0.3))}
        values = ikm.frame_values(LEG, sample)
        # the toes joint holds the ball in the FK ankle
        toes = om.MPoint(*values[("IKXToes_L", "translate")]) * ankle
        self.assertTrue(close((toes.x, toes.y, toes.z), ball, 1e-9))
        for node, parent, local in (("IKAnkleHandle_L", handle_parent, (0.4, 0.5, 0.6)),
                                    ("IKOffsetToes_L", offset_parent, (0.1, 0.2, 0.3))):
            step = (om.MVector(*values[(node, "translate")]) - om.MVector(*local)) * parent
            self.assertTrue(close(om.MVector(10, 1.5, 12.5) + step, ball, 1e-9), node)
        self.assertAlmostEqual(values[("IKLeg_L", "Lenght1")], 40.0 / 43.0, places=12)


class Summary(unittest.TestCase):

    def test_names_the_lengths_and_what_moved(self):
        series = {("IKArm_R", "Lenght1"): [0.7977, 0.7977], ("IKArm_R", "Lenght2"): [0.7576, 0.7576],
                  ("IKXShoulder_R", "translate"): [(0.91, 0, 0), (0.91, 0, 0)]}
        text = ikm.summary("arm_r", series, ARM)
        self.assertEqual(text, "arm_r lengths x0.798/0.758, the shoulder moved 0.91 cm")

    def test_a_limb_at_rest_says_nothing(self):
        series = {("IKArm_R", "Lenght1"): [1.0], ("IKArm_R", "Lenght2"): [1.0],
                  ("IKXShoulder_R", "translate"): [(0.001, 0, 0)]}
        self.assertEqual(ikm.summary("arm_r", series, ARM), "")

    def test_the_ball_against_its_own_rest(self):
        series = {("IKLeg_L", "Lenght1"): [1.0], ("IKLeg_L", "Lenght2"): [1.0],
                  ("IKXHip_L", "translate"): [(0, 0, 0)],
                  ("IKXToes_L", "translate"): [(7.49, 17.16, 0.0)]}
        text = ikm.summary("leg_l", series, LEG, {"IKXToes_L": (7.49, 15.02, 0.0)})
        self.assertEqual(text, "leg_l the ball moved 2.14 cm")


class Plans(unittest.TestCase):
    """Every version's IK ends and poles ride our own FKX joints."""

    CONTROLS = [c for c in ar.candidates(ar.UE5)]
    BONES = [ar.bone_name(b, s, ar.UE5) for _, b in ar.ROWS for _, s in ar.SIDES] + ["root", "pelvis"]

    def test_every_version(self):
        for kwargs in ({}, {"rotation": True}, {"scaled": True}, {"keep_lengths": True}):
            drives, _ = ar.drive_plan(self.CONTROLS, self.BONES, ar.UE5, **kwargs)
            ik = [d for d in drives if d.control.startswith(("IK", "Pole"))]
            self.assertEqual(len(ik), 10, kwargs)
            self.assertTrue(all(d.own and d.bone.startswith("FKX") for d in ik), kwargs)

    def test_the_fk_takes_position_for_a_twin_and_a_stretch_only(self):
        for kwargs, expected in (({}, True), ({"scaled": True}, True),
                                 ({"rotation": True}, False), ({"keep_lengths": True}, False)):
            drives, _ = ar.drive_plan(self.CONTROLS, self.BONES, ar.UE5, **kwargs)
            fk = [d for d in drives if d.control.startswith("FK")]
            self.assertTrue(all(d.translate == expected for d in fk), kwargs)


class Switch(unittest.TestCase):
    """The Connections FK / IK switch carries the shown arm's shape into the IK."""

    def test_the_lengths_are_targets_not_resets(self):
        self.assertNotIn("Lenght1", fkik.IK_SOLVE)
        self.assertNotIn("Lenght2", fkik.IK_SOLVE)
        self.assertIn("stretchy", fkik.IK_SOLVE)

    def test_to_ik_keys_the_lenghts_and_the_chains_root(self):
        arm = fkik.Limb("R", "FKIKArm_R.FKIKBlend", [], ["FKShoulder_R"], [], ["IKXShoulder_R"],
                        "IKArm_R", "PoleArm_R", "AlignIKToWrist_R", "IKXOffsetShoulder_R",
                        (30.0, 28.0))
        targets = dict(fkik.targets(arm, fkik.IK))
        self.assertEqual(targets["IKArm_R"], fkik.CHANNELS + ("Lenght1", "Lenght2"))
        self.assertEqual(targets["IKXShoulder_R"], fkik.TRANSLATE)
        self.assertEqual(fkik.targets(arm._replace(units=(None, None)), fkik.IK)[0][1], fkik.CHANNELS)


class Boundary(unittest.TestCase):

    def test_it_ships(self):
        import install
        self.assertIn("maya_ikmatch.py", install.payload())

    def test_no_qt_and_no_advancedskeleton_procedure(self):
        with open(os.path.join(PLUGIN, "maya_ikmatch.py"), encoding="utf-8") as handle:
            source = handle.read()
        for banned in ("PySide", "shiboken", "mel.eval", "import maya.mel"):
            self.assertNotIn(banned, source)

    def test_both_retargets_restore_it_in_their_reset_and_carry_it_in_their_bake(self):
        for name in ("maya_asretarget.py", "maya_pmretarget.py"):
            with open(os.path.join(PLUGIN, name), encoding="utf-8") as handle:
                source = handle.read()
            reset = source.split("def reset_build_pose(")[1].split("\ndef ")[0]
            bake = source.split("\ndef bake(")[1].split("\ndef ")[0]
            self.assertIn("ikmatch.restore(rig)", reset, name)
            self.assertIn("ikmatch.carry(rig", bake, name)


if __name__ == "__main__":
    unittest.main()
