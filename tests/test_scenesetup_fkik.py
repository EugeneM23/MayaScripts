"""FK / IK for the arms of an AdvancedSkeleton rig (2026-09-30).

The pure halves: which mode the blend is in, which span a press covers, the
blend's keys for a range, the pole, the channels of a target world matrix,
the messages - and the boundary: AdvancedSkeleton's own procedures are
replicated, never called.

Spec: docs/superpowers/specs/2026-09-30-connections-fkik-switch-design.md
"""

import ast
import math
import os
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import fkik

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")


def euler_matrix(x, y, z, order=om.MEulerRotation.kXYZ):
    return om.MEulerRotation(math.radians(x), math.radians(y), math.radians(z),
                             order).asMatrix()


def moved(matrix, x, y, z):
    tm = om.MTransformationMatrix(matrix)
    tm.setTranslation(om.MVector(x, y, z), om.MSpace.kTransform)
    return tm.asMatrix()


def close(a, b, tol=1e-9):
    return all(abs(p - q) <= tol for p, q in zip(list(a), list(b)))


class Mode(unittest.TestCase):

    def test_zero_is_fk_ten_is_ik(self):
        self.assertEqual(fkik.mode_of([0.0]), fkik.FK)
        self.assertEqual(fkik.mode_of([10.0]), fkik.IK)

    def test_every_key_at_one_end_is_that_mode(self):
        self.assertEqual(fkik.mode_of([10.0, 10.0, 10.0]), fkik.IK)
        self.assertEqual(fkik.mode_of([0.0, 0.0]), fkik.FK)

    def test_anything_else_is_mixed(self):
        self.assertIsNone(fkik.mode_of([0.0, 10.0]))
        self.assertIsNone(fkik.mode_of([5.0]))
        self.assertIsNone(fkik.mode_of([]))


class Span(unittest.TestCase):

    def test_no_highlight_is_the_whole_take(self):
        self.assertEqual(fkik.span_for(None, (0.0, 120.0)), (0, 120, False))

    def test_a_highlight_is_its_frames_the_end_exclusive(self):
        """`timeControl -rangeArray` answers [start, end+1)."""
        self.assertEqual(fkik.span_for((30.0, 51.0), (0.0, 120.0)), (30, 50, True))

    def test_the_whole_take_snaps_outward(self):
        self.assertEqual(fkik.span_for(None, (0.4, 88.792)), (0, 89, False))


class KeyFrames(unittest.TestCase):
    """Keys-only (2026-10-08): the frames something that moves the arm is
    keyed on, never every frame of the take."""

    def test_the_whole_take_is_every_key_time_once(self):
        self.assertEqual(fkik.key_frames([24.0, 0.0, 12.0, 12.0, 6.0], (0, 120, False)),
                         [0.0, 6.0, 12.0, 24.0])

    def test_keys_outside_the_playback_range_count_over_the_whole_take(self):
        self.assertEqual(fkik.key_frames([-5.0, 130.0], (0, 120, False)), [-5.0, 130.0])

    def test_a_fraction_of_a_frame_apart_is_one_key(self):
        self.assertEqual(fkik.key_frames([10.0, 10.00001, 10.5], (0, 20, False)), [10.0, 10.5])

    def test_nothing_keyed_is_no_frame(self):
        self.assertEqual(fkik.key_frames([], (0, 120, False)), [])

    def test_a_range_is_its_keys_and_its_two_ends(self):
        """The blend steps on the range's ends: the new mode must stand on the
        shown pose there whatever the keys."""
        self.assertEqual(fkik.key_frames([0.0, 6.0, 12.0, 24.0, 40.0], (10, 30, True)),
                         [10.0, 12.0, 24.0, 30.0])

    def test_a_key_on_a_ranges_end_is_not_doubled(self):
        self.assertEqual(fkik.key_frames([10.0, 30.0], (10, 30, True)), [10.0, 30.0])

    def test_a_one_frame_range(self):
        self.assertEqual(fkik.key_frames([], (7, 7, True)), [7.0])


class Tangents(unittest.TestCase):

    def test_the_arms_own_keys_decide(self):
        own = [("clamped", "step"), ("clamped", "step")]
        every = own + [("auto", "auto")]
        self.assertEqual(fkik.tangent_for(own, every), ("clamped", "step"))

    def test_with_no_own_key_on_the_frame_every_curve_decides(self):
        self.assertEqual(fkik.tangent_for([], [("linear", "linear")] * 3), ("linear", "linear"))

    def test_a_type_is_used_only_where_they_agree(self):
        self.assertEqual(fkik.tangent_for([("auto", "step"), ("linear", "step")], []),
                         (None, "step"))

    def test_fixed_never_crosses_over(self):
        """A fixed tangent's angle belongs to the other curve."""
        self.assertEqual(fkik.tangent_for([("fixed", "fixed")], []), (None, None))

    def test_nothing_on_the_frame_is_mayas_default(self):
        self.assertEqual(fkik.tangent_for([], []), (None, None))


class Walk(unittest.TestCase):
    """What the upstream walk follows on a transform: what moves its matrix."""

    def test_the_transform_channels_long_and_short(self):
        for attr in ("translateX", "rotate", "rz", "jointOrientY", "rotateAxis",
                     "rotatePivotTranslate", "offsetParentMatrix", "scaleZ", "shearXY",
                     "inverseScale", "rotateOrder"):
            self.assertTrue(fkik.moves_matrix(attr), attr)

    def test_a_custom_attribute_or_visibility_is_not(self):
        for attr in ("Lenght1", "FKIKBlend", "follow", "visibility", "v", "swivel"):
            self.assertFalse(fkik.moves_matrix(attr), attr)

    def test_an_indexed_or_child_plug_reads_its_root(self):
        self.assertEqual(fkik.attr_root("node.worldMatrix[0]"), "worldMatrix")
        self.assertEqual(fkik.attr_root("|a|b.translate.translateX"), "translate")
        self.assertTrue(fkik.matrix_output("worldMatrix"))
        self.assertTrue(fkik.matrix_output("parentMatrix"))
        self.assertTrue(fkik.matrix_output("translateY"))
        self.assertFalse(fkik.matrix_output("Lenght2"))


class Sources(unittest.TestCase):
    """The nodes the walk starts from: what the arm shows."""

    def setUp(self):
        self.arm = fkik.Limb("R", "|FKIKArm_R.FKIKBlend", ["d0", "d1", "d2"],
                             ["fk0", "fk1", "fk2"], ["fkx0", "fkx1", "fkx2"],
                             ["ikx0", "ikx1", "ikx2"], "ik", "pole", "align", "rp", (1, 1))

    def test_an_fk_arm_is_its_fkx_chain(self):
        nodes, plugs, own = fkik.sources(self.arm, fkik.FK)
        self.assertEqual(nodes, ["fkx0", "fkx1", "fkx2"])
        self.assertEqual(plugs, [])
        self.assertEqual(own, ["fk0", "fk1", "fk2"])

    def test_an_ik_arm_is_its_ikx_chain_the_control_and_the_pole(self):
        nodes, plugs, own = fkik.sources(self.arm, fkik.IK)
        self.assertEqual(nodes, ["ikx0", "ikx1", "ikx2", "ik", "pole"])
        self.assertEqual(own, ["ik", "pole"])

    def test_a_mixed_take_is_both_and_the_blend(self):
        nodes, plugs, own = fkik.sources(self.arm, None)
        self.assertEqual(nodes, ["fkx0", "fkx1", "fkx2", "ikx0", "ikx1", "ikx2", "ik", "pole"])
        self.assertEqual(plugs, ["|FKIKArm_R.FKIKBlend"])
        self.assertEqual(own, ["fk0", "fk1", "fk2", "ik", "pole"])


class BlendKeys(unittest.TestCase):

    def test_a_range_is_stepped_in_and_out(self):
        """Inserted (shape kept) one frame outside, the target on both ends,
        stepped out of the frame before and out of the last frame."""
        self.assertEqual(fkik.blend_keys(30, 50, 10.0),
                         [(29, None, True), (30, 10.0, False),
                          (50, 10.0, True), (51, None, False)])

    def test_a_one_frame_range(self):
        self.assertEqual(fkik.blend_keys(7, 7, 0.0),
                         [(6, None, True), (7, 0.0, True), (8, None, False)])


class Channels(unittest.TestCase):

    def test_translate_and_rotate_in_the_controls_order(self):
        order = om.MEulerRotation.kZYX
        m = moved(euler_matrix(10, 20, 30, order), 1, 2, 3)
        t, r = fkik.local_channels(m, 5, (0.0, 0.0, 0.0))
        self.assertTrue(close(t, (1, 2, 3)))
        self.assertTrue(close(r, (10, 20, 30), 1e-7))

    def test_the_euler_nearest_the_frame_before(self):
        """190 deg is -170 deg; the curve must not jump 360 (trap 108)."""
        m = euler_matrix(0, 0, 190)
        _t, r = fkik.local_channels(m, 0, (0.0, 0.0, 185.0))
        self.assertAlmostEqual(r[2], 190.0, places=6)
        _t, r = fkik.local_channels(m, 0, (0.0, 0.0, -175.0))
        self.assertAlmostEqual(r[2], -170.0, places=6)


class FkLocals(unittest.TestCase):
    """Each FK control's local, from the shown joints and the rig's rigid
    offsets: the control over its FKX joint, the chain from the upper joint
    to the next control's parent."""

    def test_the_fkx_chain_lands_on_the_shown_joints(self):
        shown = [moved(euler_matrix(10, 0, 5), 0, 150, 0),
                 moved(euler_matrix(20, 30, 0), 25, 150, 0),
                 moved(euler_matrix(0, 45, 10), 50, 150, 3)]
        fkx_in_ctrl = [euler_matrix(180, 0, 0), euler_matrix(180, 0, 0),
                       euler_matrix(174, 2, 0)]
        chain = [None, moved(euler_matrix(0, 0, 3), 25, 0, 0),
                 moved(euler_matrix(1, 0, 0), 25, 0, 0)]
        parent = moved(euler_matrix(0, 0, 90), 0, 140, 0)
        locals_ = fkik.fk_locals(shown, parent, chain, fkx_in_ctrl)
        # rebuild the FK chain from those locals, as the DAG would
        world = parent
        for i, local in enumerate(locals_):
            if i:
                world = chain[i] * fkx
            ctrl = local * world
            fkx = fkx_in_ctrl[i] * ctrl
            self.assertTrue(close(fkx, shown[i], 1e-9), i)


class Pole(unittest.TestCase):

    def setUp(self):
        self.s = om.MVector(0, 0, 0)
        self.w = om.MVector(50, 0, 0)
        self.rot = om.MMatrix()

    def test_a_bent_arm_puts_the_pole_on_its_bend(self):
        e = om.MVector(25, 0, -10)
        side = fkik.pole_side(om.MVector(25, 0, -60), self.s, e, self.w, self.rot)
        pole = fkik.pole_point(self.s, e, self.w, self.rot, side)
        base = om.MVector(25, 0, 0)
        direction = (pole - base).normal()
        self.assertAlmostEqual(direction.y, 0.0, places=9)     # in the bend plane
        self.assertLess(direction.z, -0.99)

    def test_a_straight_arm_takes_the_side_from_the_elbows_frame(self):
        """No bend to read: the nudge, turned with the elbow, decides."""
        e = om.MVector(25, 0, 0)
        side = om.MVector(0, 0, -1)
        turned = euler_matrix(90, 0, 0)      # the elbow rolled a quarter about X
        pole = fkik.pole_point(self.s, e, self.w, turned, side)
        direction = (pole - e).normal()
        self.assertAlmostEqual(abs(direction.y), 1.0, places=6)

    def test_the_side_is_read_off_the_line(self):
        e = om.MVector(25, 0, -10)
        side = fkik.pole_side(om.MVector(40, 0, -60), self.s, e, self.w, self.rot)
        self.assertAlmostEqual(side.x, 0.0, places=9)          # along-line part gone
        self.assertAlmostEqual(side.z, -1.0, places=9)

    def test_a_pole_on_a_straight_line_has_no_side(self):
        e = om.MVector(25, 0, 0)
        self.assertIsNone(fkik.pole_side(om.MVector(80, 0, 0), self.s, e, self.w,
                                         self.rot))


class SolveAttributes(unittest.TestCase):

    def test_off_default_or_moving_keys_are_named(self):
        attrs = {"swivel": (0.0, [], 0.0), "lock": (0.0, [0.0, 5.0], 0.0),
                 "Lenght1": (1.2, [], 1.0), "antiPop": (0.0, [0.0, 0.0], 0.0)}
        self.assertEqual(fkik.off_default(attrs), ["Lenght1", "lock"])


class Blend(unittest.TestCase):
    """What the arm shows: the FKX and IKX chains blended as the rig does."""

    def setUp(self):
        self.fk = moved(euler_matrix(0, 0, 0), 0, 0, 0)
        self.ik = moved(euler_matrix(0, 0, 90), 10, 0, 0)

    def test_the_ends_are_the_chains_themselves(self):
        self.assertTrue(close(fkik.blended(self.fk, self.ik, 0.0), self.fk))
        self.assertTrue(close(fkik.blended(self.fk, self.ik, 1.0), self.ik))

    def test_half_way_is_half_the_turn_and_half_the_way(self):
        half = fkik.blended(self.fk, self.ik, 0.5)
        self.assertAlmostEqual(fkik.angle(half, self.fk), 45.0, places=6)
        self.assertAlmostEqual(fkik.position(half).x, 5.0, places=9)

    def test_the_short_way_round(self):
        """q and -q are one rotation; the blend must not go the long way."""
        other = moved(euler_matrix(0, 0, 350), 0, 0, 0)
        half = fkik.blended(self.fk, other, 0.5)
        self.assertAlmostEqual(fkik.angle(half, self.fk), 5.0, places=6)


class Measured(unittest.TestCase):

    def test_places_hand_and_roll_are_told_apart(self):
        same = [moved(euler_matrix(0, 0, 0), 0, 0, 0)] * 3
        rolled = [moved(euler_matrix(30, 0, 0), 0, 0, 0), same[1],
                  moved(euler_matrix(0, 2, 0), 0, 0.5, 0)]
        m = fkik.measure({4: same, 5: same}, {4: same, 5: rolled})
        self.assertAlmostEqual(m.cm, 0.5)
        self.assertEqual(m.cm_frame, 5)
        self.assertAlmostEqual(m.hand, 2.0, places=6)
        self.assertAlmostEqual(m.roll, 30.0, places=6)
        self.assertEqual(m.roll_frame, 5)


class Messages(unittest.TestCase):

    def test_switched_names_the_span_and_the_measure(self):
        text = fkik.switched_message("R", fkik.IK, (0, 120, False),
                                     fkik.Measure(0.0004, 3, 0.001, 0.0, None),
                                     ["swivel reset to 0"])
        self.assertIn("Arm_R to IK over 0..120", text)
        self.assertIn("kept to 0.0004 cm, 0.001 deg", text)
        self.assertIn("swivel reset to 0", text)

    def test_a_range_is_named_as_one(self):
        text = fkik.switched_message("L", fkik.FK, (30, 50, True),
                                     fkik.Measure(0.0, None, 0.0, 0.0, None), [])
        self.assertIn("Arm_L to FK over the range 30..50", text)

    def test_the_roll_an_ik_arm_cannot_hold_is_said(self):
        text = fkik.switched_message("R", fkik.IK, (0, 60, False),
                                     fkik.Measure(0.004, 3, 0.0, 59.04, 32), [])
        self.assertIn("hand and elbow kept to 0.004 cm", text)
        self.assertIn("the FK forearm twist is lost, up to 59 deg at frame 32", text)
        self.assertIn("(an IK elbow does not twist)", text)

    def test_keys_only_names_how_many_keys(self):
        held = fkik.Measure(0.0, None, 0.0, 0.0, None)
        text = fkik.switched_message("R", fkik.IK, (0, 120, False), held, [],
                                     keys=[0.0, 6.0, 12.0, 24.0])
        self.assertIn("Arm_R to IK on 4 keys (0..24)", text)
        self.assertIn("the arm kept", text)
        text = fkik.switched_message("L", fkik.FK, (0, 120, False), held, [], keys=[12.0])
        self.assertIn("Arm_L to FK on 1 key (12)", text)

    def test_keys_only_in_a_range(self):
        text = fkik.switched_message("R", fkik.IK, (30, 50, True),
                                     fkik.Measure(0.0, None, 0.0, 0.0, None), [],
                                     keys=[30.0, 41.0, 50.0])
        self.assertIn("Arm_R to IK over the range 30..50 on 3 keys", text)

    def test_nothing_keyed_is_said(self):
        text = fkik.switched_message("R", fkik.IK, (0, 120, False),
                                     fkik.Measure(0.0, None, 0.0, 0.0, None), [], keys=[])
        self.assertIn("Arm_R to IK, no keys - nothing keyed moves the arm", text)

    def test_a_fraction_of_a_frame_is_shown_as_it_is(self):
        text = fkik.switched_message("R", fkik.IK, (0, 10, False),
                                     fkik.Measure(0.0, None, 0.0, 0.0, None), [],
                                     keys=[2.5, 8.0])
        self.assertIn("on 2 keys (2.5..8)", text)

    def test_a_moved_arm_is_said_with_the_number(self):
        text = fkik.switched_message("R", fkik.IK, (0, 10, False),
                                     fkik.Measure(1.25, 7, 3.0, 0.0, None), [])
        self.assertIn("moved up to 1.25 cm (frame 7), the hand 3 deg", text)


class Boundaries(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(PLUGIN, "maya_scenesetup", "fkik.py"), encoding="utf-8") as f:
            self.source = f.read()
        self.tree = ast.parse(self.source)

    def _calls(self):
        out = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else \
                    getattr(func, "id", "")
                out.append(name)
        return out

    def _imports(self):
        imports = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                imports.add(node.module)
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
        return imports

    def test_advancedskeleton_is_replicated_not_called(self):
        """No MEL at all: a colleague's Maya has no AdvancedSkeleton to call."""
        self.assertNotIn("eval", self._calls())
        self.assertNotIn("maya.mel", self._imports())
        self.assertNotIn("mel", self._imports())

    def test_it_imports_no_panel_and_no_overrig(self):
        for banned in ("connections", "overrig", "maya_overrig", "maya_hub"):
            self.assertNotIn(banned, self._imports())


if __name__ == "__main__":
    unittest.main()
