"""Override mode (2026-11-02): the chest carries the weapon with a strength per half
and a lag in milliseconds.

The formula's claims are measured here; `enter` / `leave` over a real rig belong to
docs/superpowers/plans/verify_weapon_override.py. Run in mayapy - the formula is
OpenMaya, as `aimcore`'s pure half is.

Spec: docs/superpowers/specs/2026-11-02-connections-2h-and-override-design.md
"""
import math
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import weaponoverride as wo


def xform(rotate, place):
    tm = om.MTransformationMatrix()
    tm.setRotation(om.MEulerRotation(*[math.radians(v) for v in rotate]))
    tm.setTranslation(om.MVector(*place), om.MSpace.kTransform)
    return tm.asMatrix()


def worst(a, b):
    return max(abs(a[i] - b[i]) for i in range(16))


def scale_of(matrix):
    return om.MTransformationMatrix(om.MMatrix(matrix)).scale(om.MSpace.kTransform)


class Formula(unittest.TestCase):
    def setUp(self):
        self.ref = wo.rigid(xform((0, 10, 0), (0, 100, 0)))
        self.late = wo.rigid(xform((5, 40, -3), (12, 104, 6)))
        self.own = xform((20, 0, 0), (30, 120, 10))

    def test_full_strength_is_the_parents_own_matrix(self):
        g = wo.scaled(self.ref, self.late, 1.0, 1.0)
        self.assertEqual(worst(g, self.ref.inverse() * self.late), 0.0)

    def test_the_identity_leaves_the_weapon_where_it_was(self):
        #  rotation 1, position 1, lag 0: the chest read at f IS the chest at f
        g = wo.scaled(self.ref, self.late, 1.0, 1.0)
        out = wo.result(self.own, self.late, self.ref, g)
        self.assertLess(worst(out, self.own), 1e-12)

    def test_no_strength_freezes_the_chest_at_its_reference(self):
        g = wo.scaled(self.ref, self.late, 0.0, 0.0)
        out = wo.result(self.own, self.late, self.ref, g)
        want = om.MMatrix(self.own) * self.late.inverse() * self.ref
        self.assertLess(worst(out, want), 1e-12)

    def test_the_scaled_delta_keeps_no_scale(self):
        g = wo.scaled(self.ref, self.late, 0.5, 0.5)
        self.assertAlmostEqual(max(abs(v - 1.0) for v in scale_of(g)), 0.0, places=12)

    def test_half_the_position_is_half_the_travel(self):
        half = wo.scaled(self.ref, self.late, 0.0, 0.5)
        full = wo.scaled(self.ref, self.late, 0.0, 1.0)
        self.assertAlmostEqual(half[13] * 2.0, full[13], places=9)

    def test_no_rotation_leaves_the_turn_alone(self):
        g = wo.scaled(self.ref, self.late, 0.0, 1.0)
        turn = om.MTransformationMatrix(g).rotation(asQuaternion=True)
        self.assertAlmostEqual(abs(turn.w), 1.0, places=12)

    def test_half_the_rotation_is_half_the_angle(self):
        full = om.MTransformationMatrix(
            wo.scaled(self.ref, self.late, 1.0, 0.0)).rotation(asQuaternion=True)
        half = om.MTransformationMatrix(
            wo.scaled(self.ref, self.late, 0.5, 0.0)).rotation(asQuaternion=True)
        angle = lambda q: math.degrees(2.0 * math.acos(min(1.0, abs(q.w))))
        self.assertAlmostEqual(angle(half) * 2.0, angle(full), places=6)

    def test_rigid_drops_a_chest_scale_and_keeps_its_place(self):
        tm = om.MTransformationMatrix(xform((0, 30, 0), (1, 2, 3)))
        tm.setScale([2.0, 2.0, 2.0], om.MSpace.kTransform)
        out = wo.rigid(tm.asMatrix())
        self.assertAlmostEqual(max(abs(v - 1.0) for v in scale_of(out)), 0.0, places=12)
        self.assertEqual([out[12], out[13], out[14]], [1.0, 2.0, 3.0])


class Lag(unittest.TestCase):
    def test_ms_into_frames(self):
        self.assertAlmostEqual(wo.lag_frames(100.0, 30.0), 3.0)
        self.assertAlmostEqual(wo.lag_frames(100.0, 24.0), 2.4)

    def test_a_whole_frame_is_that_frames_matrix(self):
        mats = {1: xform((0, 0, 0), (1, 0, 0)), 2: xform((0, 0, 0), (2, 0, 0))}
        self.assertEqual(wo.sampled(mats, 2)[12], 2.0)

    def test_a_fraction_lerps_the_place(self):
        mats = {1: xform((0, 0, 0), (1, 0, 0)), 2: xform((0, 0, 0), (3, 0, 0))}
        self.assertAlmostEqual(wo.sampled(mats, 1.5)[12], 2.0, places=9)

    def test_a_fraction_slerps_the_turn(self):
        mats = {1: xform((0, 0, 0), (0, 0, 0)), 2: xform((0, 90, 0), (0, 0, 0))}
        middle = om.MTransformationMatrix(wo.sampled(mats, 1.5)).rotation()
        self.assertAlmostEqual(math.degrees(middle.y), 45.0, places=6)

    def test_before_the_first_frame_it_holds(self):
        mats = {5: xform((0, 0, 0), (7, 0, 0)), 6: xform((0, 0, 0), (9, 0, 0))}
        self.assertEqual(wo.sampled(mats, 2.0)[12], 7.0)

    def test_past_the_last_frame_it_holds(self):
        mats = {5: xform((0, 0, 0), (7, 0, 0)), 6: xform((0, 0, 0), (9, 0, 0))}
        self.assertEqual(wo.sampled(mats, 99.0)[12], 9.0)

    def test_one_frame_is_all_it_has(self):
        mats = {4: xform((0, 0, 0), (2, 0, 0))}
        self.assertEqual(wo.sampled(mats, 1.5)[12], 2.0)


class Values(unittest.TestCase):
    def test_the_identity_is_full_strength_and_no_lag(self):
        self.assertTrue(wo.is_identity(wo.Settings(1.0, 1.0, 0.0)))
        self.assertFalse(wo.is_identity(wo.Settings(1.0, 1.0, 80.0)))
        self.assertFalse(wo.is_identity(wo.Settings(0.5, 1.0, 0.0)))
        self.assertFalse(wo.is_identity(wo.Settings(1.0, 0.0, 0.0)))

    def test_the_settings_round_trip_through_their_string(self):
        s = wo.Settings(0.5, 0.25, 120.0)
        self.assertEqual(wo.parse(wo.unparse(s)), s)

    def test_a_broken_string_is_no_settings(self):
        self.assertIsNone(wo.parse(""))
        self.assertIsNone(wo.parse(None))
        self.assertIsNone(wo.parse("1 1"))
        self.assertIsNone(wo.parse("on 1 80"))

    def test_a_turned_knob_is_a_pick_while_the_mode_stands(self):
        card = wo.Settings(1.0, 1.0, 160.0)
        standing = wo.Settings(1.0, 1.0, 80.0)
        self.assertNotEqual(wo.pick_value(True, card),
                            wo.state_value(standing, card))

    def test_a_turned_knob_is_no_pick_while_the_mode_is_off(self):
        card = wo.Settings(1.0, 1.0, 160.0)
        self.assertEqual(wo.pick_value(False, card), wo.state_value(None, card))

    def test_the_mode_standing_with_those_numbers_is_no_pick(self):
        card = wo.Settings(0.5, 1.0, 80.0)
        self.assertEqual(wo.pick_value(True, card), wo.state_value(card, card))

    def test_a_value_is_on_and_three_numbers(self):
        self.assertEqual(wo.pick_value(True, wo.Settings(0.5, 1.0, 40.0)),
                         (True, 0.5, 1.0, 40.0))
