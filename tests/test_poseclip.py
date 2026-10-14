"""poseclip (docs/superpowers/plans/poseclip): our poses onto a locomotion clip - the model.

Spec: docs/superpowers/specs/2026-10-14-pose-on-clip-design.md. The model is numpy + the copied posemath
(maya.api.OpenMaya), so these run under mayapy."""
import json
import math
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.normpath(os.path.join(HERE, "..", "docs", "superpowers", "plans", "poseclip"))
if FOLDER not in sys.path:
    sys.path.insert(0, FOLDER)

import poseclip as pc  # noqa: E402

RNG = np.random.default_rng(7)


def random_rot():
    return pc.exp_rot(RNG.normal(size=3) * 1.2)


class Toolkit(unittest.TestCase):
    def test_exp_log_round_trip(self):
        for _ in range(20):
            r = random_rot()
            np.testing.assert_allclose(pc.exp_rot(pc.log_rot(r)), r, atol=1e-9)

    def test_toward_ends(self):
        a, b = random_rot(), random_rot()
        self.assertIs(pc.toward(a, b, 0.0), a)
        np.testing.assert_allclose(pc.toward(a, b, 1.0), b, atol=1e-9)

    def test_power(self):
        r = random_rot()
        np.testing.assert_allclose(pc.power(r, 0.0), np.eye(3), atol=1e-12)
        np.testing.assert_allclose(pc.power(r, 1.0), r, atol=1e-9)
        np.testing.assert_allclose(pc.power(r, 0.5) @ pc.power(r, 0.5), r, atol=1e-9)

    def test_slerp(self):
        a, b = random_rot(), random_rot()
        np.testing.assert_allclose(pc.slerp(a, b, 0.0), a, atol=1e-9)
        np.testing.assert_allclose(pc.slerp(a, b, 1.0), b, atol=1e-9)

    def test_two_bone_reaches_and_falls_short(self):
        hip = np.array([0.0, 90.0, 0.0])
        knee, reached, short = pc.two_bone(hip, np.array([5.0, 20.0, 10.0]), 45.0, 42.0,
                                           np.array([0.0, 0.0, 1.0]), 0.995)
        np.testing.assert_allclose(reached, [5.0, 20.0, 10.0], atol=1e-9)
        self.assertAlmostEqual(float(np.linalg.norm(knee - hip)), 45.0, places=9)
        self.assertAlmostEqual(float(np.linalg.norm(reached - knee)), 42.0, places=9)
        self.assertEqual(short, 0.0)
        far = np.array([0.0, 0.0, 0.0])
        knee, reached, short = pc.two_bone(hip, far, 45.0, 42.0, np.array([0.0, 0.0, 1.0]), 0.95)
        self.assertAlmostEqual(short, 90.0 - 0.95 * 87.0, places=9)

    def test_align(self):
        u, n = np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
        r = random_rot()
        u2, n2 = u @ r, n @ r
        m = pc.align(u, n, u2, n2)
        np.testing.assert_allclose(u @ m, u2, atol=1e-12)
        np.testing.assert_allclose(n @ m, n2, atol=1e-12)

    def test_yaw(self):
        r = pc.exp_rot([0.0, 0.7, 0.0])
        self.assertAlmostEqual(pc.yaw_of(r), 0.7, places=12)
        np.testing.assert_allclose(pc.yaw(pc.yaw_of(r)), r, atol=1e-12)
        tilted = pc.exp_rot([0.3, 0.0, 0.0]) @ r
        self.assertAlmostEqual(pc.yaw_of(tilted), 0.7, places=6)


if __name__ == "__main__":
    unittest.main()
