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


class FakeCmds(object):
    """Just enough of `cmds` for the parked base: attributes, connections, values."""

    def __init__(self):
        self.attrs = {}          # "node.attr" -> value
        self.added = []          # (node, longName, kind)
        self.connections = {}    # "node.attr" -> "curve.output"
        self.cut = []
        self.deleted = []

    def objExists(self, path):
        #  a node exists; a plug exists when it was added
        return path in self.attrs or "." not in path

    def attributeQuery(self, name, node=None, exists=False):
        return (node + "." + name) in self.attrs

    def addAttr(self, node, longName=None, dataType=None, attributeType=None,
                keyable=None):
        self.added.append((node, longName, dataType or attributeType))
        self.attrs[node + "." + longName] = "" if dataType == "string" else 0.0

    def deleteAttr(self, plug):
        self.attrs.pop(plug, None)

    def getAttr(self, plug, **kwargs):
        if kwargs.get("lock"):
            return False
        return self.attrs.get(plug, 0.0)

    def setAttr(self, plug, *values, **kwargs):
        self.attrs[plug] = values[0]

    def listConnections(self, plug, **kwargs):
        found = self.connections.get(plug)
        if not found:
            return []
        return [found if kwargs.get("plugs") else found.split(".")[0]]

    def connectAttr(self, source, target, force=False):
        self.connections[target] = source

    def disconnectAttr(self, source, target):
        self.connections.pop(target, None)

    def cutKey(self, plug, **kwargs):
        self.cut.append(plug)
        self.connections.pop(plug, None)

    def delete(self, *nodes):
        self.deleted.extend(nodes)

    def ls(self, *args, **kwargs):
        return [args[0]] if args and args[0] else []


class FakeScene(unittest.TestCase):
    def setUp(self):
        self.fake = FakeCmds()
        self.weapon = "|Sword"
        for channel in wo.CHANNELS:
            self.fake.attrs[self.weapon + "." + channel] = 0.0
        self.old, wo.cmds = wo.cmds, self.fake

    def tearDown(self):
        wo.cmds = self.old


class ParkedBase(FakeScene):
    def setUp(self):
        FakeScene.setUp(self)
        #  a curve on rotateY, a plain value on translateX
        self.fake.connections[self.weapon + ".rotateY"] = "swingCurve.output"
        self.fake.attrs[self.weapon + ".translateX"] = 7.5

    def test_park_takes_the_curve_off_the_weapon(self):
        wo.park(self.weapon)
        self.assertNotIn(self.weapon + ".rotateY", self.fake.connections)
        self.assertEqual(self.fake.connections[self.weapon + ".skeldarOverrideBaseRotateY"],
                         "swingCurve.output")

    def test_park_copies_a_plain_value(self):
        wo.park(self.weapon)
        self.assertEqual(self.fake.attrs[self.weapon + ".skeldarOverrideBaseTranslateX"], 7.5)

    def test_a_rotate_is_parked_as_an_angle_and_a_translate_as_a_length(self):
        #  trap 42: a plain double would have Maya splice a unitConversion in
        wo.park(self.weapon)
        kinds = dict((name, kind) for _n, name, kind in self.fake.added)
        self.assertEqual(kinds["skeldarOverrideBaseRotateY"], "doubleAngle")
        self.assertEqual(kinds["skeldarOverrideBaseTranslateX"], "doubleLinear")

    def test_unpark_puts_the_curve_back_and_leaves_nothing(self):
        wo.park(self.weapon)
        wo.unpark(self.weapon)
        self.assertEqual(self.fake.connections[self.weapon + ".rotateY"], "swingCurve.output")
        self.assertEqual(self.fake.attrs[self.weapon + ".translateX"], 7.5)
        self.assertNotIn(self.weapon + ".skeldarOverrideBaseRotateY", self.fake.attrs)

    def test_unpark_cuts_the_overrides_own_curve_first(self):
        #  trap 210: an emptied curve node goes with the cut
        wo.park(self.weapon)
        self.fake.connections[self.weapon + ".rotateY"] = "overrideCurve.output"
        wo.unpark(self.weapon)
        self.assertIn(self.weapon + ".rotateY", self.fake.cut)
        self.assertEqual(self.fake.connections[self.weapon + ".rotateY"], "swingCurve.output")

    def test_unpark_with_nothing_parked_says_so(self):
        self.assertFalse(wo.unpark(self.weapon))

    def test_park_again_takes_whatever_stands_on_the_weapon(self):
        #  park's own rule: the base is what the weapon carries NOW, and what was
        #  parked before is deleted with its curves
        wo.park(self.weapon)
        self.fake.connections[self.weapon + ".rotateY"] = "overrideCurve.output"
        wo.park(self.weapon)
        self.assertIn("swingCurve", self.fake.deleted)
        self.assertEqual(self.fake.connections[self.weapon + ".skeldarOverrideBaseRotateY"],
                         "overrideCurve.output")

    def test_unpark_then_park_keeps_the_original_base(self):
        #  the re-write's order (`enter`): the base reconnected, then parked again - so
        #  a knob turned re-reads the weapon's ORIGINAL animation, never its own result
        wo.park(self.weapon)
        self.fake.connections[self.weapon + ".rotateY"] = "overrideCurve.output"
        wo.unpark(self.weapon)
        wo.park(self.weapon)
        self.assertEqual(self.fake.connections[self.weapon + ".skeldarOverrideBaseRotateY"],
                         "swingCurve.output")

    def test_drop_deletes_the_parked_curves(self):
        wo.park(self.weapon)
        wo.drop(self.weapon)
        self.assertIn("swingCurve", self.fake.deleted)
        self.assertNotIn(self.weapon + ".skeldarOverrideBaseRotateY", self.fake.attrs)


class State(FakeScene):
    def test_no_marker_is_no_state(self):
        self.assertIsNone(wo.state(self.weapon))
        self.assertFalse(wo.is_overridden(self.weapon))

    def test_the_marker_reads_back_its_numbers(self):
        self.fake.attrs[self.weapon + "." + wo.MARKER] = "0.5 0.25 120"
        self.assertEqual(wo.state(self.weapon), wo.Settings(0.5, 0.25, 120.0))
        self.assertTrue(wo.is_overridden(self.weapon))

    def test_a_broken_marker_is_no_state(self):
        self.fake.attrs[self.weapon + "." + wo.MARKER] = "oops"
        self.assertIsNone(wo.state(self.weapon))

    def test_a_weapon_that_is_gone_is_no_state(self):
        self.assertIsNone(wo.state("|Gone"))
        self.assertIsNone(wo.state(None))


class Words(unittest.TestCase):
    def test_entered_names_the_keys_the_chest_and_the_numbers(self):
        line = wo.entered_message("Sword", [0.0, 12.0, 24.0],
                                  wo.Settings(1.0, 1.0, 80.0), "spine_03", None)
        self.assertIn("3 keys", line)
        self.assertIn("spine_03", line)
        self.assertIn("80", line)

    def test_entered_says_when_the_numbers_change_nothing(self):
        line = wo.entered_message("Sword", [0.0], wo.IDENTITY, "spine_03", None)
        self.assertIn("the identity", line)

    def test_entered_does_not_cry_identity_for_a_lag(self):
        line = wo.entered_message("Sword", [0.0], wo.Settings(1.0, 1.0, 80.0),
                                  "spine_03", None)
        self.assertNotIn("the identity", line)

    def test_entered_warns_about_a_held_weapon(self):
        line = wo.entered_message("Sword", [0.0], wo.Settings(1.0, 1.0, 80.0),
                                  "spine_03", "R")
        self.assertIn("slides in the grip", line)
        self.assertIn("right", line)

    def test_entered_says_when_it_has_no_keys_of_its_own(self):
        line = wo.entered_message("Sword", [], wo.Settings(1.0, 1.0, 80.0), "spine_03", None)
        self.assertIn("no keys of its own", line)

    def test_left_names_the_weapon(self):
        self.assertIn("Sword", wo.left_message("Sword"))
