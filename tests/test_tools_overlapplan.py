"""maya_tools.overlapplan: the Tools card's Overlap model (2026-10-13) - OverRig's overlapper
computed from sampled frames. numpy, no Maya.

Spec: docs/superpowers/specs/2026-10-13-tools-aim-overlap-design.md
"""

import math
import os
import subprocess
import sys
import unittest

import numpy as np

from maya_tools import overlapplan as plan

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "SkeldarAnim")


def _frame(angle_z=0.0, position=(0.0, 0.0, 0.0)):
    out = np.eye(4)
    out[:3, :3] = plan.matrix_from_euler((0.0, 0.0, angle_z), 0)
    out[3, :3] = position
    return out


def _chain(angles, members=4, length=10.0):
    """A straight chain along the root's X, the root turning about Z by `angles` (one per frame)
    in place, the others rigidly attached under it."""
    frames = np.zeros((members, len(angles), 4, 4))
    for t, angle in enumerate(angles):
        root = _frame(angle)
        frames[0, t] = root
        for index in range(1, members):
            place = np.eye(4)
            place[3, 0] = length * index
            frames[index, t] = place @ root
    return frames


def _z_angle(rotation):
    """The heading of a rotation's X axis about Z, degrees."""
    return math.degrees(math.atan2(rotation[0][1], rotation[0][0]))


def _sweep(count=49, amplitude=40.0, period=48.0):
    return [amplitude * math.sin(2.0 * math.pi * t / period) for t in range(count)]


class Rotations(unittest.TestCase):

    def test_both_ways_in_every_order(self):
        rng = np.random.RandomState(3)
        for order in range(6):
            for _ in range(20):
                angles = tuple(rng.uniform(-170, 170, 3))
                m = plan.matrix_from_euler(angles, order)
                back = plan.euler_from_matrix(m, order)
                self.assertTrue(np.allclose(plan.matrix_from_euler(back, order), m, atol=1e-9),
                                (order, angles, back))

    def test_the_gimbal(self):
        for order, name in enumerate(plan.ORDERS):
            middle = "xyz".index(name[1])
            for sign in (1.0, -1.0):
                angles = [25.0, -40.0, 60.0]
                angles[middle] = 90.0 * sign
                m = plan.matrix_from_euler(angles, order)
                back = plan.euler_from_matrix(m, order)
                self.assertTrue(np.allclose(plan.matrix_from_euler(back, order), m, atol=1e-9),
                                (name, sign))

    def test_mayas_convention(self):
        """Row vectors: +90 about X takes Y to Z; the first letter of the order applies first."""
        m = plan.matrix_from_euler((90.0, 0.0, 0.0), 0)
        self.assertTrue(np.allclose(np.array([0.0, 1.0, 0.0]) @ m, [0.0, 0.0, 1.0], atol=1e-12))
        xyz = plan.matrix_from_euler((30.0, 40.0, 0.0), "xyz")
        self.assertTrue(np.allclose(xyz, plan.axis_matrix(0, 30.0) @ plan.axis_matrix(1, 40.0)))

    def test_against_openmaya(self):
        try:
            import maya.api.OpenMaya as om
        except ImportError:
            self.skipTest("no OpenMaya")
        rng = np.random.RandomState(7)
        for order in range(6):
            angles = tuple(rng.uniform(-170, 170, 3))
            euler = om.MEulerRotation(*[math.radians(a) for a in angles], order=order)
            theirs = np.array(list(euler.asMatrix())).reshape(4, 4)[:3, :3]
            self.assertTrue(np.allclose(plan.matrix_from_euler(angles, order), theirs,
                                        atol=1e-9), plan.ORDERS[order])

    def test_nearest_rotation_takes_scale_out(self):
        m = plan.matrix_from_euler((10.0, 20.0, 30.0), 0)
        self.assertTrue(np.allclose(plan.nearest_rotation(m * 2.5), m, atol=1e-12))

    def test_inverse_frames(self):
        f = _frame(35.0, (1.0, 2.0, 3.0))
        self.assertTrue(np.allclose(f @ plan.inverse_frames(f), np.eye(4), atol=1e-12))


class Model(unittest.TestCase):

    def test_lag_zero_gives_the_frames_back(self):
        frames = _chain(_sweep())
        out = plan.simulate(frames, frames[:, 0], 0.0, 2.0)
        self.assertTrue(np.allclose(out, frames, atol=1e-9))

    def test_a_root_turning_in_place_is_delayed_by_the_lag(self):
        """Its target lies on its own X, read `lag` frames earlier: aiming at it from the same
        place turns the root exactly as it turned then."""
        angles = _sweep()
        frames = _chain(angles)
        out = plan.simulate(frames, frames[:, 0], 2.0, 2.0)
        for t in range(2, len(angles)):
            self.assertAlmostEqual(_z_angle(out[0, t, :3, :3]), angles[t - 2], places=6)
        self.assertAlmostEqual(_z_angle(out[0, 0, :3, :3]), angles[0], places=6)

    def test_a_fractional_lag_falls_between_the_frames(self):
        angles = _sweep()
        frames = _chain(angles)
        out = plan.simulate(frames, frames[:, 0], 0.5, 2.0)
        for t in range(2, len(angles) - 1):
            expected = 40.0 * math.sin(2.0 * math.pi * (t - 0.5) / 48.0)
            self.assertAlmostEqual(_z_angle(out[0, t, :3, :3]), expected, delta=0.05)

    def test_the_tip_trails_the_root(self):
        angles = _sweep(97, period=48.0)
        frames = _chain(angles)
        out = plan.simulate(frames, frames[:, 0], 1.0, 2.0)
        root = [_z_angle(out[0, t, :3, :3]) for t in range(97)]
        tip = [_z_angle(out[3, t, :3, :3]) for t in range(97)]
        late = lambda series: int(np.argmax(series[48:97])) + 48
        self.assertGreater(late(tip), late(root))
        self.assertGreater(max(abs(a - b) for a, b in zip(root, tip)), 1.0)

    def test_softness_softens(self):
        angles = _sweep()
        frames = _chain(angles)
        swing = []
        for softness in (1.0, 4.0):
            out = plan.simulate(frames, frames[:, 0], 2.0, softness)
            swing.append(max(abs(_z_angle(out[3, t, :3, :3]) - _z_angle(out[0, t, :3, :3]))
                             for t in range(49)))
        self.assertGreater(swing[0], swing[1])

    def test_cycled_wraps_round_the_take(self):
        angles = _sweep(49, period=48.0)        # sample 48 is sample 0 again
        frames = _chain(angles)
        out = plan.simulate(frames, frames[:, 0], 2.0, 2.0, cycled=True)
        self.assertAlmostEqual(_z_angle(out[0, 0, :3, :3]), angles[46], places=6)
        self.assertAlmostEqual(_z_angle(out[0, 1, :3, :3]), angles[47], places=6)
        self.assertTrue(np.allclose(out[:, 0], out[:, 48], atol=1e-9))

    def test_easing_calms_a_jitter(self):
        angles = [a + (1.5 if t % 2 else -1.5) for t, a in enumerate(_sweep())]
        frames = _chain(angles)
        jitter = []
        for easing in (0.0, 1.0):
            out = plan.simulate(frames, frames[:, 0], 1.0, 2.0, easing=easing)
            series = np.array([_z_angle(out[0, t, :3, :3]) for t in range(49)])
            jitter.append(float(np.abs(np.diff(series, 2)).mean()))
        self.assertLess(jitter[1], jitter[0] * 0.3)

    def test_two_members_in_one_place_are_refused(self):
        frames = _chain(_sweep(5), members=3)
        frames[1, :, 3, :3] = frames[0, :, 3, :3]
        with self.assertRaises(ValueError) as caught:
            plan.rest(frames[:, 0])
        self.assertEqual(caught.exception.args[0], 0)

    def test_the_rest_geometry(self):
        rest = plan.rest(_chain([30.0], members=3)[:, 0])
        d, distance, u = rest[0]
        self.assertTrue(np.allclose(d, [1.0, 0.0, 0.0]))
        self.assertAlmostEqual(distance, 10.0)
        self.assertAlmostEqual(float(np.dot(d, u)), 0.0)
        d_last, distance_last, _u = rest[2]
        self.assertTrue(np.allclose(d_last, [1.0, 0.0, 0.0]))     # the line continued
        self.assertAlmostEqual(distance_last, 10.0)

    def test_lookup_ends_and_wrap(self):
        track = np.array([[0.0], [1.0], [2.0], [3.0]])
        self.assertTrue(np.allclose(plan.lookup(track, [-2.0, 1.0, 9.0]), [[0.0], [1.0], [3.0]]))
        cycle = np.array([[0.0], [1.0], [2.0], [0.0]])             # period 3
        self.assertTrue(np.allclose(plan.lookup(cycle, [-1.0, 4.0], cycled=True), [[2.0], [1.0]]))


class Channels(unittest.TestCase):

    def test_rotate_values_undo_the_axes_and_the_orient(self):
        ra = plan.matrix_from_euler((10.0, 0.0, 5.0), 0)
        jo = plan.matrix_from_euler((0.0, 30.0, -20.0), 0)
        rotate = plan.matrix_from_euler((12.0, -7.0, 44.0), 0)
        parent = np.eye(4)
        parent[:3, :3] = plan.matrix_from_euler((5.0, 15.0, 25.0), 0) * 2.0   # scaled
        world = ra @ rotate @ jo @ plan.nearest_rotation(parent[:3, :3])
        self.assertTrue(np.allclose(plan.rotate_values(world, parent, ra, jo), rotate))
        self.assertTrue(np.allclose(plan.rotate_values(ra @ rotate, np.eye(4), ra), rotate))

    def test_eulers_stand_nearest_the_base(self):
        m = plan.matrix_from_euler((0.0, 0.0, 170.0), 0)
        row = plan.eulers([m], 0, [(0.0, 0.0, -185.0)])[0]
        self.assertAlmostEqual(row[2], -190.0, places=6)

    def test_translate_delta(self):
        pivot = np.array([[1.0, 2.0, 3.0]])
        parent = np.eye(4)[None]
        self.assertTrue(np.allclose(plan.translate_delta(pivot, parent, pivot, parent), 0.0))
        moved = parent.copy()
        moved[0, 3, :3] = (0.0, 5.0, 0.0)
        self.assertTrue(np.allclose(plan.translate_delta(pivot, parent, pivot + [0, 5, 0], moved),
                                    0.0))
        self.assertTrue(np.allclose(plan.translate_delta(pivot, parent, pivot + [2, 0, 0], parent),
                                    [[2.0, 0.0, 0.0]]))

    def test_carried_keeps_the_place_under_the_member(self):
        before = _frame(0.0, (0.0, 0.0, 0.0))[None]
        after = _frame(90.0, (0.0, 0.0, 0.0))[None]
        parent = np.eye(4)[None]
        parent[0, 3, :3] = (10.0, 0.0, 0.0)
        moved = plan.carried(parent, before, after)
        self.assertTrue(np.allclose(moved[0, 3, :3], [0.0, 10.0, 0.0], atol=1e-12))

    def test_edge_weights(self):
        w = plan.edge_weights(51)
        self.assertEqual(w[0], 0.0)
        self.assertEqual(w[-1], 0.0)
        self.assertEqual(w[25], 1.0)
        self.assertEqual(w[10], 1.0)
        self.assertTrue(all(b >= a for a, b in zip(w[:11], w[1:11])))
        self.assertTrue(np.allclose(plan.edge_weights(2), [1.0, 1.0]))

    def test_total_lag_and_the_pad(self):
        settings = plan.DEFAULTS._replace(lag=3.0, total=True)
        self.assertAlmostEqual(plan.link_lag(settings, 6), 0.5)
        self.assertAlmostEqual(plan.link_lag(plan.DEFAULTS, 6), 1.0)
        self.assertEqual(plan.pad(1.0, 4), 7)
        self.assertEqual(plan.pad(-1.0, 4), 7)


class Lines(unittest.TestCase):

    def test_settings_refusals(self):
        self.assertIn("Softness", plan.settings_refusal(plan.DEFAULTS._replace(softness=0.0)))
        self.assertIn("Lag", plan.settings_refusal(plan.DEFAULTS._replace(lag=0.0)))
        self.assertIn("Easing", plan.settings_refusal(plan.DEFAULTS._replace(easing=-1.0)))
        self.assertEqual(plan.settings_refusal(plan.DEFAULTS), "")

    def test_alone(self):
        self.assertIn("Hierarchy off", plan.alone_refusal("tail_01", True))
        self.assertIn("Hierarchy on", plan.alone_refusal("tail_01", False))

    def test_the_message(self):
        line = plan.overlap_message([["|a|tail_01", "|a|tail_01|tail_02"]],
                                    plan.DEFAULTS._replace(cycled=True), 1.0, 0, 48, False,
                                    "Overlap", True, ["tail_02 branches (2) - its chain stops "
                                                      "there"])
        for word in ("tail_01 > tail_02 (2 links)", "softness 2", "lag 1 fr", "over 0-48",
                     "cycled", "layer Overlap", "replaced", "branches"):
            self.assertIn(word, line)
        two = plan.overlap_message([["|a", "|a|b"], ["|c", "|c|d", "|c|d|e"]], plan.DEFAULTS,
                                   1.0, 10, 20, True, "Overlap1", False, [])
        self.assertIn("2 chains (5 links)", two)
        self.assertIn("the highlight", two)


class Purity(unittest.TestCase):

    def test_no_maya_is_imported(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_tools.overlapplan; "
                "print(sorted(m for m in sys.modules if m == 'maya' or m.startswith('maya.')))"
                % PLUGIN)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN)
        self.assertEqual(out.decode().strip().splitlines()[-1], "[]")


if __name__ == "__main__":
    unittest.main()
