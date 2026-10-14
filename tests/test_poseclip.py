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


def synthetic_stop(frames=50, wide=0.0, lean_end=0.0, drop_end=0.0):
    """Manny's skeleton doing a small stop in place: the pelvis low, swaying and dipping, the spine
    leaning and the left arm swinging until frame ~29, then standing still at its bind (30..). The right
    foot planted throughout; the left planted 10 cm behind (0..9), stepping to its bind (9..15) and planted
    there (15..). Legs by IK. `wide` cm moves both feet outward (a wider stance throughout); `lean_end` (radians)
    and `drop_end` (cm) lean the spine and lower the pelvis in the still part (a pose)."""
    names, parents, rest = _template()
    J = len(names)
    ix = dict((n, i) for i, n in enumerate(names))
    local = np.array([rest[j] @ np.linalg.inv(rest[parents[j]]) if parents[j] >= 0 else rest[j] for j in range(J)])
    order = sorted(range(J), key=lambda j: (_depth(parents, j), j))
    worlds = np.zeros((J, frames, 4, 4))
    for f in range(frames):
        s = _smoothstep((f - 22) / 8.0)
        bump = math.sin(math.pi * min(f, 29) / 29.0) if f <= 29 else 0.0
        offset = np.array([2.0 * math.sin(2 * math.pi * f / 29.0) * (1 - s),
                           -6.0 * (1 - s) - 4.0 * bump - drop_end * s, 3.0 * bump])
        lean = 0.35 * bump + lean_end * s
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


def statics_of(clip):
    names, parents, rest = _template()
    out = {}
    for j, name in enumerate(names):
        p = parents[j]
        out[name] = {"parent": names[p] if p >= 0 else None, "canonical": name,
                     "rest": [float(v) for v in rest[j].reshape(16)]}
    return out


def pose_from(clip, frame):
    """A pose: the clip's skeleton standing as at `frame` (the template's rest as its rest)."""
    statics = statics_of(clip)
    bones = {}
    for leaf, bone in statics.items():
        b = dict(bone)
        b["world"] = [float(v) for v in clip.worlds[clip.index[leaf], frame].reshape(16)]
        bones[leaf] = b
    return bones


def _length(worlds, a, b):
    return np.linalg.norm(worlds[a, :, 3, :3] - worlds[b, :, 3, :3], axis=1)


class Pose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = synthetic_stop()
        cls.a = pc.Analysis(cls.clip)
        cls.statics = statics_of(cls.clip)

    def test_the_reference_as_a_pose_reads_as_the_reference(self):
        pose = pc.prepare(self.a, self.statics, pose_from(self.clip, self.clip.F - 1))
        pelvis = self.clip.index["pelvis"]
        np.testing.assert_allclose(pose["rel"][pelvis], self.a.rel_ref[pelvis], atol=1e-6)
        spine = self.clip.index["spine_03"]
        np.testing.assert_allclose(pose["rel"][spine], self.a.rel_ref[spine], atol=1e-6)
        self.assertAlmostEqual(pose["height"], self.a.h_ref, places=4)
        self.assertAlmostEqual(pose["width"], 0.0, places=4)
        for side in pc.SIDES:
            self.assertAlmostEqual(pose["knee_turn"][side], 0.0, places=4)
            ankle = self.a.feet[side]["ankle"][self.clip.F - 1]
            np.testing.assert_allclose(pose["feet"][side][3, :3], ankle, atol=1e-4)
        np.testing.assert_allclose(pose["offset"], self.a.ref_offset, atol=1e-4)
        self.assertEqual(pose["scale"], 1.0)
        self.assertFalse(pose["grip"])

    def test_a_lower_wider_pose(self):
        other = synthetic_stop(wide=8.0, drop_end=12.0, lean_end=0.4)
        pose = pc.prepare(self.a, self.statics, pose_from(other, other.F - 1))
        self.assertAlmostEqual(pose["height"], self.a.h_ref - 12.0, places=3)
        self.assertAlmostEqual(pose["width"], 16.0, places=3)


class Synthesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = synthetic_stop()
        cls.a = pc.Analysis(cls.clip)
        cls.statics = statics_of(cls.clip)
        cls.other = synthetic_stop(wide=8.0, drop_end=12.0, lean_end=0.4)
        cls.pose = pc.prepare(cls.a, cls.statics, pose_from(cls.other, cls.other.F - 1))
        cls.full = pc.evaluate(cls.a, cls.pose, share=1.0, motion=1.0)

    def test_share_zero_is_the_clip(self):
        result = pc.evaluate(self.a, self.pose, share=0.0, motion=1.0)
        np.testing.assert_allclose(result.worlds, self.clip.worlds, atol=1e-4)
        self.assertLess(result.info["carry"], 1e-3)
        self.assertEqual(result.info["drop"], 0.0)

    def test_share_one_motion_zero_stands_in_the_pose_in_the_reference(self):
        result = pc.evaluate(self.a, self.pose, share=1.0, motion=0.0)
        f = self.clip.F - 1
        ix = self.clip.index
        for name in ("pelvis", "spine_01", "spine_03", "neck_01", "head", "upperarm_l", "hand_r"):
            j = ix[name]
            np.testing.assert_allclose(result.worlds[j, f, :3, :3], self.other.worlds[j, f, :3, :3], atol=1e-5,
                                       err_msg=name)
        pelvis = ix["pelvis"]
        self.assertAlmostEqual(float(result.worlds[pelvis, f, 3, 1]), float(self.other.worlds[pelvis, f, 3, 1]), places=4)
        for side in pc.SIDES:
            j = ix["foot_" + side]
            np.testing.assert_allclose(result.worlds[j, f, 3, :3], self.other.worlds[j, f, 3, :3], atol=1e-4)
        # the balance puts the pelvis where the pose has it over its feet
        np.testing.assert_allclose(result.worlds[pelvis, f, 3, [0, 2]], self.other.worlds[pelvis, f, 3, [0, 2]],
                                   atol=0.05)

    def test_planted_feet_stay_planted(self):
        for side in pc.SIDES:
            j = self.clip.index["foot_" + side]
            new = self.full.worlds[j, :, 3, :3]
            old = self.clip.worlds[j, :, 3, :3]
            for c0, c1 in self.a.feet[side]["contacts"]:
                for f in range(c0 + 1, c1 + 1):
                    moved = float(np.linalg.norm(new[f] - new[f - 1]))
                    own = float(np.linalg.norm(old[f] - old[f - 1]))
                    self.assertLessEqual(moved, own + 1e-4, "%s frame %d" % (side, f))

    def test_bone_lengths_are_the_clips(self):
        ix = self.clip.index
        for a, b in (("thigh_l", "calf_l"), ("calf_r", "foot_r"), ("spine_03", "spine_04"), ("upperarm_l", "lowerarm_l"),
                     ("foot_l", "ball_l")):
            np.testing.assert_allclose(_length(self.full.worlds, ix[a], ix[b]), _length(self.clip.worlds, ix[a], ix[b]),
                                       atol=1e-6, err_msg=a + "-" + b)

    def test_the_balance(self):
        a = self.a
        plan_offset = (self.pose["offset"] - a.ref_offset)
        com = np.tensordot(a.masses, self.full.worlds[:, :, 3, :3], axes=(0, 0))
        pivots = dict((s, 0.5 * (self.full.worlds[self.clip.index["foot_" + s], :, 3, :3]
                                  + self.full.worlds[self.clip.index["ball_" + s], :, 3, :3])) for s in pc.SIDES)
        support = pc.support_path(a.weights, pivots)
        new = com - support
        old = a.com - a.support + a.stillness[:, None] * plan_offset
        for f in range(self.clip.F):
            if a.feet["l"]["down"][f] or a.feet["r"]["down"][f]:
                self.assertLess(float(np.linalg.norm((new[f] - old[f])[[0, 2]])), 0.05, "frame %d" % f)

    def test_the_final_stance_and_the_height_rule(self):
        f = self.clip.F - 1
        ix = self.clip.index
        for side in pc.SIDES:
            j = ix["foot_" + side]
            np.testing.assert_allclose(self.full.worlds[j, f, 3, :3], self.pose["feet"][side][3, :3], atol=1e-4)
        pelvis = ix["pelvis"]
        height = self.full.worlds[pelvis, :, 3, 1] - self.a.floor
        expect = self.pose["height"] * (self.a.pos[pelvis, :, 1] - self.a.floor) / self.a.h_ref
        self.assertTrue(np.all(height <= expect + 1e-4))
        np.testing.assert_allclose(height[self.a.reference[0]:], expect[self.a.reference[0]:], atol=1e-3)

    def test_motion_zero_stills_the_torso(self):
        result = pc.evaluate(self.a, self.pose, share=1.0, motion=0.0)
        j = self.clip.index["spine_02"]
        rel = result.worlds[j, :, :3, :3] @ np.swapaxes(self.a.heading, -1, -2)
        spread = max(float(np.abs(rel[f] - rel[0]).max()) for f in range(self.clip.F))
        self.assertLess(spread, 1e-6)

class Rules(unittest.TestCase):
    """The rules that came from the real stop (the spec's addendum)."""

    def test_stillness_is_one_standing_and_falls_with_speed(self):
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        self.assertTrue(np.all((a.stillness >= 0.0) & (a.stillness <= 1.0)))
        self.assertAlmostEqual(float(a.stillness[-1]), 1.0, places=6)

    def test_the_forward_lean_takes_the_room_the_pose_leaves(self):
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        bent = synthetic_stop(lean_end=0.6)
        pose = pc.prepare(a, statics_of(clip), pose_from(bent, bent.F - 1))
        plan = pc._Plan(a, pose, 1.0, 1.0, pc.PARTS)
        expect = (pc.LEAN_LIMIT - pose["lean"]) / (pc.LEAN_LIMIT - a.lean_ref)
        self.assertAlmostEqual(plan.forward, expect, places=9)
        self.assertLess(plan.forward, 1.0)
        none = pc._Plan(a, pose, 0.0, 1.0, pc.PARTS)
        self.assertEqual(none.forward, 1.0)

    def test_a_backward_lean_is_not_scaled(self):
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        bent = synthetic_stop(lean_end=0.6)
        pose = pc.prepare(a, statics_of(clip), pose_from(bent, bent.F - 1))
        result = pc.evaluate(a, pose, 1.0, 1.0)
        j = clip.index["spine_01"]
        # the synthetic clip leans spine_01 forward (+ about its local X, which in Manny's bind is the world's -X):
        # whatever its sign, the posed spine's deviation from its target is the clip's, scaled by 1 or by `forward`
        plan = pc._Plan(a, pose, 1.0, 1.0, pc.PARTS)
        for f in range(clip.F):
            w = pc.log_rot(a.rel_ref[j].T @ a.rel[j, f])
            got = pc.log_rot(plan.target_rel[j].T @ (result.worlds[j, f, :3, :3] @ a.heading[f].T))
            k = plan.forward if w[0] > 0.0 else 1.0
            np.testing.assert_allclose(got, [w[0] * k, w[1], w[2]], atol=1e-6, err_msg="frame %d" % f)


if __name__ == "__main__":
    unittest.main()
