"""The parametric walk's model (walkmodel.py) on a synthetic walker: numpy only, no Maya."""

import importlib.util
import math
import os
import subprocess
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(os.path.dirname(HERE), "docs", "superpowers", "plans", "walkparam")


def load(name):
    spec = importlib.util.spec_from_file_location(name + "_under_test", os.path.join(FOLDER, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wm = load("walkmodel")


def rot_x(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]])


def rot_y(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])


def angle(r):
    return math.degrees(float(np.linalg.norm(wm.log_rot(r))))


class PurityTests(unittest.TestCase):

    def test_imports_nothing_of_maya(self):
        code = ("import importlib.util, sys; s = importlib.util.spec_from_file_location('m', %r); "
                "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "print(sorted(k for k in sys.modules if k.startswith('maya')))"
                % os.path.join(FOLDER, "walkmodel.py"))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


class RotationTests(unittest.TestCase):

    def test_exp_is_a_row_vector_turn_about_the_axis(self):
        self.assertTrue(np.allclose(wm.exp_rot([math.radians(30), 0, 0]), rot_x(30)))
        self.assertTrue(np.allclose(wm.exp_rot([0, math.radians(-40), 0]), rot_y(-40)))
        self.assertTrue(np.allclose(wm.exp_rot([0, 0, math.radians(75)]), rot_z(75)))
        self.assertTrue(np.allclose(wm.exp_rot([0.0, 0.0, 0.0]), np.eye(3)))

    def test_log_inverts_exp_up_to_pi(self):
        rng = np.random.default_rng(3)
        for _ in range(200):
            w = rng.normal(size=3)
            w *= rng.uniform(0.0, 3.1) / np.linalg.norm(w)
            self.assertTrue(np.allclose(wm.log_rot(wm.exp_rot(w)), w, atol=1e-9))
        r = wm.exp_rot([math.pi, 0.0, 0.0])
        self.assertTrue(np.allclose(wm.exp_rot(wm.log_rot(r)), r, atol=1e-9))

    def test_batched(self):
        w = np.array([[0.1, 0.2, 0.3], [0.0, 0.0, 0.0], [1.0, -0.5, 0.2]])
        self.assertTrue(np.allclose(wm.log_rot(wm.exp_rot(w)), w))

    def test_mean_of_a_symmetric_pair_is_the_middle(self):
        m = wm.mean_rot(np.stack([rot_x(10) @ rot_y(20), rot_x(-10) @ rot_y(20)]))
        self.assertLess(angle(m @ rot_y(20).T), 0.5)

    def test_orthonormal_strips_scale(self):
        self.assertTrue(np.allclose(wm.orthonormal(rot_z(30) * 1.02), rot_z(30)))


class SamplerTests(unittest.TestCase):

    def test_exact_on_whole_frames_and_periodic(self):
        x = np.array([[math.sin(2 * math.pi * f / 12.0), f % 3] for f in range(12)])
        for f in range(12):
            self.assertTrue(np.allclose(wm.periodic_cr(x, float(f)), x[f]))
            self.assertTrue(np.allclose(wm.periodic_cr(x, float(f + 12)), x[f]))
            self.assertTrue(np.allclose(wm.periodic_cr(x, float(f - 24)), x[f]))

    def test_between_frames_follows_a_smooth_signal(self):
        x = np.array([math.sin(2 * math.pi * f / 24.0) for f in range(24)])
        for tau in (0.5, 5.25, 17.75, 23.5):
            self.assertAlmostEqual(float(wm.periodic_cr(x, tau)), math.sin(2 * math.pi * tau / 24.0), places=3)

    def test_warp_keeps_the_cycle_and_never_runs_back(self):
        for beta in (-0.9, -0.3, 0.0, 0.3, 0.6, 0.9):
            self.assertAlmostEqual(wm.warp(1.0, beta, 0.17) - wm.warp(0.0, beta, 0.17), 1.0, places=12)
            values = [wm.warp(f / 400.0, beta, 0.17) for f in range(401)]
            self.assertTrue(all(b > a for a, b in zip(values, values[1:])))
        self.assertEqual(wm.warp(0.3, 0.0, 0.1), 0.3)

    def test_warp_is_slowest_a_quarter_after_phi0(self):
        h = 1e-5
        slope = lambda p: (wm.warp(p + h, 0.5, 0.1) - wm.warp(p - h, 0.5, 0.1)) / (2 * h)
        self.assertAlmostEqual(slope(0.35), 0.5, places=4)
        self.assertAlmostEqual(slope(0.85), 0.5, places=4)
        self.assertAlmostEqual(slope(0.1), 1.5, places=4)

    def test_shape_bob(self):
        self.assertEqual(wm.shape_bob(-2.0, 0.0), -2.0)
        self.assertEqual(wm.shape_bob(3.0, 0.0), 3.0)
        self.assertAlmostEqual(wm.shape_bob(-2.0, 1.0), -2.0 * (1 + wm.WEIGHT_BOB_DOWN))
        self.assertAlmostEqual(wm.shape_bob(3.0, 1.0), 3.0 * (1 - wm.WEIGHT_BOB_UP))
        self.assertEqual(wm.shape_bob(3.0, 100.0), 0.0)


class LegTests(unittest.TestCase):

    def test_two_bone_keeps_lengths_and_bends_toward_bend(self):
        hip, ankle = np.array([0.0, 90.0, 0.0]), np.array([5.0, 10.0, 20.0])
        knee, reached, short = wm.two_bone(hip, ankle, 48.0, 47.0, np.array([0.0, 0.0, 1.0]), 0.99)
        self.assertAlmostEqual(np.linalg.norm(knee - hip), 48.0, places=9)
        self.assertAlmostEqual(np.linalg.norm(reached - knee), 47.0, places=9)
        self.assertTrue(np.allclose(reached, ankle))
        self.assertEqual(short, 0.0)
        e = (ankle - hip) / np.linalg.norm(ankle - hip)
        off = (knee - hip) - np.dot(knee - hip, e) * e
        self.assertGreater(np.dot(off, [0.0, 0.0, 1.0]), 0.0)

    def test_two_bone_never_straighter_than_reach(self):
        hip, ankle = np.array([0.0, 100.0, 0.0]), np.array([0.0, 0.0, 0.0])
        knee, reached, short = wm.two_bone(hip, ankle, 48.0, 47.0, np.array([0.0, 0.0, 1.0]), 0.95)
        self.assertAlmostEqual(np.linalg.norm(reached - hip), 0.95 * 95.0, places=9)
        self.assertAlmostEqual(short, 100.0 - 0.95 * 95.0, places=9)

    def test_align_takes_one_frame_onto_another(self):
        u, n = np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])
        r = rot_y(30) @ rot_z(-50)
        a = wm.align(u, n, u @ r, n @ r)
        self.assertTrue(np.allclose(a, r))
        self.assertTrue(np.allclose(wm.align(u, n, u, n), np.eye(3)))


class KnobTests(unittest.TestCase):

    def test_defaults_clamping_and_unknown(self):
        k = wm.knobs()
        self.assertEqual(k, wm.DEFAULTS)
        self.assertEqual(wm.knobs(stride=9.0)["stride"], wm.RANGES["stride"][1])
        self.assertEqual(wm.knobs(weight=-5)["weight"], -1.0)
        self.assertEqual(wm.knobs(arms=None)["arms"], 1.0)
        with self.assertRaises(ValueError):
            wm.knobs(strid=1.0)

    def test_every_knob_named_in_the_spec(self):
        self.assertEqual([k[0] for k in wm.KNOBS],
                         ["stride", "tempo", "lift", "width", "bob", "sway", "pelvis_rot", "spine", "arms",
                          "head", "overlap", "weight", "exaggeration"])


if __name__ == "__main__":
    unittest.main()
