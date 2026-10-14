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


def _template():
    with open(os.path.join(FOLDER, "manny_skeleton_template.json")) as handle:
        joints = json.load(handle)["joints"]
    names = [j["name"] for j in joints]
    index = dict((n, i) for i, n in enumerate(names))
    parents = [index.get(j.get("parent"), -1) for j in joints]
    rest = np.array([np.array(j["world_matrix"], float).reshape(4, 4) for j in joints])
    return names, parents, rest


def _smoothstep(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def synthetic_stop(frames=50, wide=0.0):
    """Manny's skeleton doing a small stop in place: the pelvis low, swaying and dipping, the spine
    leaning and the left arm swinging until frame ~29, then standing still at its bind (30..). The right
    foot planted throughout; the left planted 10 cm behind (0..9), stepping to its bind (9..15) and planted
    there (15..). Legs by IK. `wide` cm moves both feet outward (a wider stance throughout)."""
    names, parents, rest = _template()
    J = len(names)
    ix = dict((n, i) for i, n in enumerate(names))
    local = np.array([rest[j] @ np.linalg.inv(rest[parents[j]]) if parents[j] >= 0 else rest[j] for j in range(J)])
    order = sorted(range(J), key=lambda j: (_depth(parents, j), j))
    worlds = np.zeros((J, frames, 4, 4))
    for f in range(frames):
        s = _smoothstep((f - 22) / 8.0)
        bump = math.sin(math.pi * min(f, 29) / 29.0) if f <= 29 else 0.0
        offset = np.array([2.0 * math.sin(2 * math.pi * f / 29.0) * (1 - s), -6.0 * (1 - s) - 4.0 * bump, 3.0 * bump])
        lean = 0.35 * bump
        swing = 0.5 * math.sin(2 * math.pi * f / 14.0) * (1 - s)
        ankles = {"r": rest[ix["foot_r"], 3, :3] + np.array([-wide, 0.0, 0.0]),
                  "l": rest[ix["foot_l"], 3, :3] + np.array([wide, 0.0, 0.0])}
        if f < 9:
            ankles["l"] = ankles["l"] + np.array([0.0, 0.0, -10.0])
        elif f < 15:
            u = _smoothstep((f - 9) / 6.0)
            ankles["l"] = ankles["l"] + np.array([0.0, 8.0 * math.sin(math.pi * (f - 9) / 6.0), -10.0 * (1 - u)])
        w = worlds[:, f]
        for j in order:
            name, p = names[j], parents[j]
            if p < 0:
                w[j] = rest[j]
                continue
            if name in ("calf_l", "calf_r", "foot_l", "foot_r"):
                continue                     # set by the leg's IK at its thigh
            m = local[j].copy()
            if name == "spine_01":
                m[:3, :3] = pc.exp_rot([lean, 0.0, 0.0]) @ m[:3, :3]
            if name == "upperarm_l":
                m[:3, :3] = pc.exp_rot([0.0, 0.0, swing]) @ m[:3, :3]
            w[j] = m @ w[p]
            if name == "pelvis":
                w[j, 3, :3] = rest[j, 3, :3] + offset
            if name in ("thigh_l", "thigh_r"):
                side = name[-1]
                th, ca, fo = ix["thigh_" + side], ix["calf_" + side], ix["foot_" + side]
                hip = w[j, 3, :3]
                l1, l2 = np.linalg.norm(local[ca, 3, :3]), np.linalg.norm(local[fo, 3, :3])
                knee, reached, _ = pc.two_bone(hip, ankles[side], l1, l2, np.array([0.0, 0.0, 1.0]), 1.0)
                u0 = pc._unit(rest[ca, 3, :3] - rest[th, 3, :3])
                v0 = pc._unit(rest[fo, 3, :3] - rest[ca, 3, :3])
                n0 = pc._unit(np.cross(pc._unit(rest[fo, 3, :3] - rest[th, 3, :3]), u0))
                n1 = pc._unit(np.cross(pc._unit(reached - hip), pc._unit(knee - hip)))
                w[j] = pc.matrix(rest[th, :3, :3] @ pc.align(u0, n0, pc._unit(knee - hip), n1), hip)
                w[ca] = pc.matrix(rest[ca, :3, :3] @ pc.align(v0, n0, pc._unit(reached - knee), n1), knee)
                w[fo] = pc.matrix(rest[fo, :3, :3], reached)
    return pc.Clip(names, parents, worlds, 30.0, "synthetic_stop")


def _depth(parents, j):
    d = 0
    while parents[j] >= 0:
        j = parents[j]
        d += 1
    return d


class Analysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = synthetic_stop()
        cls.a = pc.Analysis(cls.clip)

    def test_kinds(self):
        kinds = dict(zip(self.clip.names, pc.kinds(self.clip)))
        self.assertEqual(kinds["root"], "root")
        self.assertEqual(kinds["pelvis"], "pelvis")
        for n in ("spine_01", "spine_05", "neck_01", "neck_02", "head"):
            self.assertEqual(kinds[n], "torso", n)
        for n in ("thigh_l", "calf_r", "foot_l"):
            self.assertEqual(kinds[n], "leg", n)
        self.assertEqual(kinds["ball_r"], "toe")
        self.assertEqual(kinds["thigh_twist_01_l"], "legtwist")
        for n in ("clavicle_l", "upperarm_r", "lowerarm_l", "hand_r", "upperarm_twist_01_l", "lowerarm_twist_02_r"):
            self.assertEqual(kinds[n], "arm", n)
        for n in ("index_01_l", "thumb_03_r", "pinky_metacarpal_l"):
            self.assertEqual(kinds[n], "finger", n)
        for n in ("ik_foot_l", "ik_hand_gun", "camera_bone", "weapon_r", "interaction", "center_of_mass"):
            self.assertEqual(kinds[n], "helper", n)

    def test_reference_is_the_still_end(self):
        a, b = self.a.reference
        self.assertEqual(b, self.clip.F - 1)
        self.assertLessEqual(a, 32)
        self.assertGreaterEqual(a, 20)

    def test_still_run(self):
        speeds = np.array([5, 5, 0.1, 0.2, 0.1, 5, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 5])
        self.assertEqual(pc.still_run(speeds, 1.5, 8), (6, 13))
        self.assertIsNone(pc.still_run(speeds, 1.5, 9))

    def test_contacts(self):
        still = np.array([1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1], bool)
        self.assertEqual(pc.contacts(still, merge=1, least=2), [(0, 5), (9, 13)])
        self.assertEqual(pc.contacts(still, merge=0, least=2), [(0, 2), (4, 5), (9, 11)])
        self.assertEqual(pc.runs(still), [(0, 2), (4, 5), (9, 11), (13, 13)])

    def test_feet_contacts_in_the_clip(self):
        left, right = self.a.feet["l"]["contacts"], self.a.feet["r"]["contacts"]
        self.assertEqual(right, [(0, self.clip.F - 1)])
        self.assertEqual(left[0][0], 0)
        self.assertGreaterEqual(left[0][1], 8)
        self.assertLessEqual(left[0][1], 10)
        self.assertGreaterEqual(left[-1][0], 14)
        self.assertLessEqual(left[-1][0], 16)
        self.assertEqual(left[-1][1], self.clip.F - 1)

    def test_foot_weights(self):
        down_l = np.array([1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1], bool)
        down_r = np.array([0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1], bool)
        w = pc.foot_weights(down_l, down_r, settle=4)
        np.testing.assert_allclose(w[0], [1, 0])
        np.testing.assert_allclose(w[4], [0, 1])
        self.assertTrue(np.all(np.isnan(w[5])))
        # both down 2..3 between left alone (1) and right alone (4): a linear hand-over
        np.testing.assert_allclose(w[2], [2 / 3, 1 / 3])
        np.testing.assert_allclose(w[3], [1 / 3, 2 / 3])
        # both down 8.. to the end after left alone at 7: toward half each over `settle` frames, then held
        np.testing.assert_allclose(w[8], [1 - 0.5 / 4, 0.5 / 4])
        np.testing.assert_allclose(w[11], [0.5, 0.5])
        rows = ~np.isnan(w[:, 0])
        np.testing.assert_allclose(w[rows].sum(axis=1), 1.0)

    def test_support_path_interpolates_a_flight(self):
        w = np.array([[1, 0], [np.nan, np.nan], [np.nan, np.nan], [0, 1]], float)
        pivots = {"l": np.array([[0, 0, 0]] * 4, float), "r": np.array([[30, 0, 0]] * 4, float)}
        s = pc.support_path(w, pivots)
        np.testing.assert_allclose(s[:, 0], [0, 10, 20, 30])

    def test_cover_lies_over_and_holds_its_ends(self):
        need = np.zeros(40)
        need[0], need[20], need[39] = 2.0, 3.0, 1.0
        c = pc.cover(need, 3.0)
        self.assertTrue(np.all(c >= need - 1e-9))
        self.assertGreater(c[1], 0.5)
        self.assertLess(c[10], 0.5 * c.max())

    def test_reference_quantities(self):
        a = self.a
        pelvis = self.clip.index["pelvis"]
        _, b = a.reference
        np.testing.assert_allclose(a.rel_ref[pelvis], a.rel[pelvis, b], atol=1e-9)
        ra, rb = a.reference
        self.assertAlmostEqual(a.h_ref, float(np.mean(a.pos[pelvis, ra:rb + 1, 1])) - a.floor, places=9)
        np.testing.assert_allclose(a.heading[0], np.eye(3), atol=1e-12)
        self.assertAlmostEqual(float(a.masses.sum()), 1.0, places=9)
        # the reference stands with both feet down, half the weight on each
        np.testing.assert_allclose(a.weights[b], [0.5, 0.5])


if __name__ == "__main__":
    unittest.main()
