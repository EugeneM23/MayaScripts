"""maya_dynamics.run - the press's range, Loop's input, the colliders' and the wind's input and
the line (2026-10-26). The bake itself is proven by docs/superpowers/plans/verify_dynamics.py."""

import math
import sys
import types
import unittest
from unittest import mock

import numpy as np

try:
    import maya.cmds  # noqa: F401
except ImportError:
    maya = types.ModuleType("maya")
    maya.cmds = types.ModuleType("maya.cmds")
    sys.modules.setdefault("maya", maya)
    sys.modules.setdefault("maya.cmds", maya.cmds)

from maya_dynamics import model  # noqa: E402
from maya_dynamics import run  # noqa: E402
from maya_dynamics import setup  # noqa: E402


def swinging(T, travel=0.0, n=4, extra=1):
    """Frames over T + extra samples of a chain hanging from a root swinging with period T and
    walking `travel` cm a frame along Z: (frames (n, F, 4, 4), carrier (F, 3)) - the carrier
    walks the straight line, as a character's Main does under its swinging body."""
    t = np.arange(T + extra)
    carrier = np.stack([np.zeros(len(t)), np.zeros(len(t)), travel * t], axis=1)
    root = carrier + np.stack([10.0 * np.sin(2 * math.pi * t / T), np.zeros(len(t)),
                               np.zeros(len(t))], axis=1)
    frames = np.zeros((n, len(t), 4, 4))
    frames[:, :, :3, :3] = np.eye(3)
    for i in range(n):
        frames[i, :, 3, :3] = root + (0.0, -6.0 * i, 0.0)
    frames[:, :, 3, 3] = 1.0
    return frames, carrier


class Range(unittest.TestCase):

    def test_the_window_adds_the_next_cycle_s_first_frame_in_a_loop(self):
        self.assertEqual(run.window(0, 4, False), [0, 1, 2, 3, 4])
        self.assertEqual(run.window(0, 4, True), [0, 1, 2, 3, 4, 5])

    def test_a_highlight_is_its_frames(self):
        self.assertEqual(run.frame_range((10.0, 21.0)), (10, 20, True))


class LoopInput(unittest.TestCase):

    def test_a_range_that_closes_on_itself_drops_the_frame_after_it(self):
        # range 0..40 whose frame 40 is frame 0 (a closed cycle): the frame read after it, 41, goes
        frames, root = swinging(40, extra=2)
        out, carriers, closes = run.loop_inputs([frames], [root])
        self.assertTrue(closes)
        self.assertEqual(out[0].shape[1], 41)
        np.testing.assert_allclose(out[0][:, -1], frames[:, 0], atol=1e-9)

    def test_cycled_curves_keep_the_frame_after_the_range(self):
        # range 0..39, its frame 40 read after it is frame 0 again (a cycle infinity), walking on
        frames, root = swinging(40, travel=2.0, extra=1)
        out, carriers, closes = run.loop_inputs([frames], [root])
        self.assertFalse(closes)
        np.testing.assert_allclose(out[0], frames)
        np.testing.assert_allclose(carriers[0], root)

    def test_an_uncycled_range_gets_its_first_frame_moved_on_by_its_travel(self):
        frames, root = swinging(40, travel=2.0, extra=1)
        frames[:, -1, 3, 0] += 5.0                            # frame 40 is not frame 0 again
        out, carriers, closes = run.loop_inputs([frames], [root])
        self.assertFalse(closes)
        np.testing.assert_allclose(out[0][:, -1, 3, :3] - out[0][:, 0, 3, :3],
                                   np.tile((0.0, 0.0, 80.0), (4, 1)), atol=1e-9)
        self.assertTrue(model.repeats_first(out, carriers[0]))

    def test_the_chains_share_one_decision(self):
        closed, root = swinging(40, extra=2)
        cycled, root2 = swinging(41, extra=1)                 # its frame 41 is its frame 0
        out, carriers, closes = run.loop_inputs([closed, cycled], [root, root2])
        self.assertEqual(len(set(f.shape[1] for f in out)), 1)


class Inputs(unittest.TestCase):

    def test_a_capsule_runs_along_its_local_x_scaled(self):
        m = np.tile(np.eye(4), (3, 1, 1))
        m[:, 0, :3] = (2.0, 0.0, 0.0)                         # X scaled 2: the segment twice as long
        m[:, 1, :3] = (0.0, 3.0, 0.0)
        m[:, 2, :3] = (0.0, 0.0, 1.0)
        m[:, 3, :3] = (5.0, 1.0, 0.0)
        c = run.collider_input("capsule", m, np.ones(3, bool), 2.0, 10.0)
        self.assertEqual(c.kind, "capsule")
        np.testing.assert_allclose(c.a[0], (-5.0, 1.0, 0.0))
        np.testing.assert_allclose(c.b[0], (15.0, 1.0, 0.0))
        np.testing.assert_allclose(c.radius, 4.0)            # 2 x the mean of 3 and 1

    def test_a_sphere_and_a_plane(self):
        m = np.tile(np.eye(4), (2, 1, 1))
        m[:, 3, :3] = (0.0, -3.0, 0.0)
        sphere = run.collider_input("sphere", m, None, 5.0, 0.0)
        self.assertEqual(sphere.kind, "sphere")
        np.testing.assert_allclose(sphere.a, sphere.b)
        plane = run.collider_input("plane", m, None, 0.0, 0.0)
        np.testing.assert_allclose(plane.normal[0], (0, 1, 0))
        np.testing.assert_allclose(plane.a[0], (0, -3, 0))

    def test_the_wind_blows_along_the_arrow_s_z(self):
        m = np.tile(np.eye(4), (2, 1, 1))
        m[:, 2, :3] = (1.0, 0.0, 0.0)
        reading = dict(matrix=m, strength=np.full(2, 0.5), turbulence=np.zeros(2),
                       gust=np.zeros(2), frequency=np.ones(2), seed=3)
        w = run.wind_input(reading)
        np.testing.assert_allclose(w.direction[0], (1, 0, 0))
        self.assertEqual(w.seed, 3)
        self.assertIsNone(run.wind_input(None))


class Line(unittest.TestCase):

    def test_the_line_names_what_was_baked(self):
        with mock.patch.object(setup, "root_of", lambda chain: "|r|" + chain.strip("|")):
            one = run.message(["hair_01"], 6, 0, 60, 4, 3, True, ["Dynamics_hair_01"],
                              {"cycles": 3, "settled": True, "ignored": 0}, True, [])
            two = run.message(["a", "b"], 8, 0, 10, 4, 0, False, ["Dynamics_a", "Dynamics_b"],
                              {"cycles": 8, "settled": False, "ignored": 2}, True, ["x"])
        self.assertEqual(one, "hair_01: 6 joints, frames 0-60, 4 substeps, 3 colliders, wind - "
                              "Dynamics_hair_01 | Loop settled in 3 cycles")
        self.assertIn("2 chains (a, b)", two)
        self.assertIn("did not settle in 8 cycles", two)
        self.assertIn("2 joint-collider pairs", two)
        self.assertTrue(two.endswith("| x"))


class Reading(unittest.TestCase):

    def test_the_reading_is_dropped_by_a_scene_change_but_not_while_we_write(self):
        state = run._state()
        state["cache"] = ("key", "reading")
        state["writing"] = True
        run._bump()
        self.assertEqual(state["cache"], ("key", "reading"))
        state["writing"] = False
        run._bump()
        self.assertIsNone(state["cache"])


if __name__ == "__main__":
    unittest.main()
