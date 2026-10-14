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
        plan = pc._Plan(a, pose, pc.knobs())
        expect = (pc.LEAN_LIMIT - pose["lean"]) / (pc.LEAN_LIMIT - a.lean_ref)
        self.assertAlmostEqual(plan.forward(0), expect, places=9)
        self.assertLess(plan.forward(0), 1.0)
        none = pc._Plan(a, pose, pc.knobs_from(0.0))
        self.assertEqual(none.forward(0), 1.0)

    def test_a_backward_lean_is_not_scaled(self):
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        bent = synthetic_stop(lean_end=0.6)
        pose = pc.prepare(a, statics_of(clip), pose_from(bent, bent.F - 1))
        result = pc.evaluate(a, pose, k=pc.knobs_from(1.0))
        j = clip.index["spine_01"]
        # the synthetic clip leans spine_01 forward (+ about its local X, which in Manny's bind is the world's -X):
        # whatever its sign, the posed spine's deviation from its target is the clip's, scaled by 1 or by `forward`
        plan = pc._Plan(a, pose, pc.knobs())
        for f in range(clip.F):
            w = pc.log_rot(a.rel_ref[j].T @ a.rel[j, f])
            got = pc.log_rot(plan.final.rel[j].T @ (result.worlds[j, f, :3, :3] @ a.heading[f].T))
            k = plan.forward(f) if w[0] > 0.0 else 1.0
            np.testing.assert_allclose(got, [w[0] * k, w[1], w[2]], atol=1e-6, err_msg="frame %d" % f)


class TwoPoses(unittest.TestCase):
    """A start pose on the run, the final as the body stops (spec addendum 3)."""

    @classmethod
    def setUpClass(cls):
        cls.clip = synthetic_stop()
        cls.a = pc.Analysis(cls.clip)
        statics = statics_of(cls.clip)
        cls.low = pc.prepare(cls.a, statics, pose_from(synthetic_stop(drop_end=12.0, lean_end=0.4), 49))
        cls.wide = pc.prepare(cls.a, statics, pose_from(synthetic_stop(wide=8.0), 49))

    def test_the_same_pose_twice_is_one_pose(self):
        k = pc.knobs(torso_drag=0, head_drag=0, arm_drag=0, from_cycle=0)
        one = pc.evaluate(self.a, self.low, k=k)
        two = pc.evaluate(self.a, self.low, k=k, start=self.low)
        np.testing.assert_allclose(two.worlds, one.worlds, atol=1e-9)

    def test_the_targets_go_from_the_start_to_the_final_as_the_body_stops(self):
        k = pc.knobs(final_speed=60.0)
        plan = pc._Plan(self.a, self.low, k, start=self.wide)
        e = plan.e
        self.assertEqual(float(e[-1]), 1.0)
        moving = [f for f in range(self.clip.F) if 0.05 < e[f] < 0.95]
        self.assertTrue(moving, "some frames between the two poses")
        spine = self.clip.index["spine_03"]
        for f in moving + [self.clip.F - 1]:
            np.testing.assert_allclose(plan.rel(spine, f), pc.slerp(plan.start.rel[spine], plan.final.rel[spine], e[f]),
                                       atol=1e-12)
            self.assertAlmostEqual(plan.height(f), (1 - e[f]) * plan.start.height + e[f] * plan.final.height, places=9)

    def test_with_no_start_pose_every_frame_is_the_final(self):
        plan = pc._Plan(self.a, self.low, pc.knobs())
        self.assertTrue(np.all(plan.e == 1.0))
        self.assertIsNone(plan.start)

    def test_the_frames_the_start_holds(self):
        self.assertEqual(pc._start_frames(np.array([0.0, 0.2, 0.49, 0.5, 0.9, 1.0])), (0, 2))
        self.assertIsNone(pc._start_frames(np.ones(5)))
        result = pc.evaluate(self.a, self.low, k=pc.knobs(final_speed=30.0, **STILL), start=self.wide)
        first, last = result.info["start_frames"]
        e = self.a.stillness_at(30.0)
        self.assertTrue(np.all(e[first:last + 1][[0, -1]] < 0.5) and e[last + 1] >= 0.5)
        self.assertIsNone(pc.evaluate(self.a, self.low, k=pc.knobs(**STILL)).info["start_frames"])


class Overlap(unittest.TestCase):
    """Walk Builder's springs, forward from the first frame at rest."""

    def test_a_still_clip_stays_still(self):
        clip = synthetic_stop()
        still = pc.Clip(clip.names, clip.parents, clip.worlds[:, 32:], 30.0, "still")
        a = pc.Analysis(still)
        out, info = pc.overlap(a, still.worlds, pc.knobs())
        np.testing.assert_allclose(out, still.worlds, atol=1e-4)

    def test_the_springs_trail_keep_the_bones_and_start_on_the_frames(self):
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        out, info = pc.overlap(a, clip.worlds, pc.knobs(torso_drag=3.0, arm_drag=3.0, head_drag=3.0))
        np.testing.assert_allclose(out[:, 0], clip.worlds[:, 0], atol=1e-4)
        self.assertGreater(info["arms"], 0.5)
        self.assertGreater(info["torso"], 0.05)
        ix = clip.index
        for child, parent in (("lowerarm_l", "upperarm_l"), ("hand_l", "lowerarm_l"), ("spine_04", "spine_03"),
                              ("head", "neck_02")):
            new = np.linalg.norm(out[ix[child], :, 3, :3] - out[ix[parent], :, 3, :3], axis=1)
            old = np.linalg.norm(clip.worlds[ix[child], :, 3, :3] - clip.worlds[ix[parent], :, 3, :3], axis=1)
            np.testing.assert_allclose(new, old, atol=1e-4, err_msg=child)
        # the legs are the frames' (the springs are the trunk's, the head's and the arms')
        for name in ("thigh_l", "calf_r", "foot_l"):
            np.testing.assert_allclose(out[ix[name]], clip.worlds[ix[name]], atol=1e-9)


class CycleStart(unittest.TestCase):
    """The stop starting exactly on a frame of a cycle."""

    def test_a_cycle_that_is_the_stop_moved_aside_lands_on_the_stop(self):
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        moved = clip.worlds[:, :20].copy()
        moved[:, :, 3, :3] += np.array([40.0, 0.0, -25.0])
        cycle = pc.Cycle(pc.Clip(clip.names, clip.parents, moved, 30.0, "cycle"))
        out, info = pc.start_on_cycle(a, clip.worlds, cycle, pc.knobs(from_cycle=8))
        self.assertAlmostEqual(info["phase"], 0.0)
        np.testing.assert_allclose(out, clip.worlds, atol=1e-5)

    def test_the_first_frame_is_the_cycles_and_the_rest_the_stops(self):
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        other = synthetic_stop(lean_end=0.3, drop_end=5.0)
        cycle = pc.Cycle(pc.Clip(other.names, other.parents, other.worlds[:, 30:50], 30.0, "cycle"))
        out, info = pc.start_on_cycle(a, clip.worlds, cycle, pc.knobs(from_cycle=6))
        aligned = cycle.sample(info["phase"]) @ info["place"]
        np.testing.assert_allclose(out[:, 0], aligned, atol=1e-6)
        np.testing.assert_allclose(out[:, 6:], clip.worlds[:, 6:], atol=1e-12)
        self.assertEqual(info["frames"], 6)

    def test_a_repeated_end_frame_is_dropped(self):
        clip = synthetic_stop()
        frames = np.concatenate([clip.worlds[:, :20], clip.worlds[:, 19:20]], axis=1)
        cycle = pc.Cycle(pc.Clip(clip.names, clip.parents, frames, 30.0, "cycle"))
        self.assertEqual(cycle.frames.shape[1], 20)


# ---- Walk Builder's tools and the cycle's posture as the start (spec addendum 4) ----

STILL = dict(torso_drag=0.0, head_drag=0.0, arm_drag=0.0, from_cycle=0.0)


def turned_pose(clip, frame, angle):
    """A pose standing as `clip` at `frame`, everything below the root turned `angle` radians about up through
    the pelvis - a pose standing side-on."""
    bones = pose_from(clip, frame)
    pivot = clip.worlds[clip.index["pelvis"], frame, 3, :3]
    turn = pc.matrix(pc.yaw(angle), pivot - pivot @ pc.yaw(angle))
    for leaf, bone in bones.items():
        if clip.parents[clip.index[leaf]] < 0:
            continue
        bone["world"] = [float(v) for v in (np.array(bone["world"]).reshape(4, 4) @ turn).reshape(16)]
    return bones


class Knobs(unittest.TestCase):
    def test_sides_and_names(self):
        k = pc.knobs(arms_l=0.0, arms=2.0, stance_r=5.0)
        self.assertEqual(k["arms"], 2.0)
        self.assertEqual(k["arms_l"], 0.0)
        self.assertEqual(k["stance_r"], 2.5)                   # clamped to the knob's range
        ks = pc.sided(k)
        self.assertEqual(ks["l"]["arms"], 0.0)
        self.assertEqual(ks["r"]["arms"], 2.0)
        self.assertEqual(ks["r"]["stance"], 2.5)
        self.assertEqual(ks["l"]["stance"], 1.0)
        with self.assertRaises(pc.Refusal):
            pc.knobs(width=1.0)                                # Width is Stance now
        with self.assertRaises(pc.Refusal):
            pc.knobs(spine_l=1.0)                              # the spine has no sides

    def test_knobs_from_is_the_first_version(self):
        k = pc.knobs_from(0.5, 0.25, parts=("torso", "arms"))
        self.assertEqual(k["share_torso"], 0.5)
        self.assertEqual(k["share_pelvis"], 0.0)
        for name in ("spine", "pelvis_rot", "bob", "head", "arms"):
            self.assertEqual(k[name], 0.25, name)
        self.assertEqual(k["leg_match"], 0.0)
        for name in pc.OVERLAP:
            self.assertEqual(k[name], 0.0, name)


class WalkBuilderTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = synthetic_stop()
        cls.a = pc.Analysis(cls.clip)
        cls.statics = statics_of(cls.clip)
        cls.pose = pc.prepare(cls.a, cls.statics, pose_from(synthetic_stop(drop_end=10.0, lean_end=0.3), 49))

    def evaluate(self, **given):
        knobs = dict(STILL)
        knobs.update(given)
        return pc.evaluate(self.a, self.pose, k=pc.knobs(**knobs))

    def test_the_knee_meets_its_foot(self):
        knee, foot = pc.meet(np.array([0.7]), np.array([0.0]), 0.5)
        free = math.radians(pc.TWIST_FREE_DEG)
        self.assertAlmostEqual(float(knee[0]), 0.7 - 0.5 * (0.7 - free), places=12)
        self.assertAlmostEqual(float(foot[0]), 0.5 * (0.7 - free), places=12)
        knee, foot = pc.meet(np.array([0.1]), np.array([0.0]), 0.5)
        self.assertAlmostEqual(float(knee[0]), 0.1, places=12)            # inside the free twist: as they are

    def test_a_knee_turned_past_its_foot_meets_it_and_the_planted_foot_stays(self):
        pose = dict(self.pose)
        pose["knee_turn"] = {"l": 0.7, "r": 0.0}
        k = pc.knobs(leg_match=0.0, **STILL)
        plan = pc._Plan(self.a, pose, k)
        free = math.radians(pc.TWIST_FREE_DEG)
        f = self.clip.F - 1
        self.assertAlmostEqual(plan.knee(f=f, side="l"), 0.7 - 0.5 * (0.7 - free), places=3)
        self.assertAlmostEqual(float(plan.toe_turn["l"][f]), 0.5 * (0.7 - free), places=3)
        result = pc.evaluate(self.a, pose, k=k)
        ix = self.clip.index
        c0, c1 = self.a.feet["l"]["contacts"][-1]
        for name in ("foot_l", "ball_l"):
            path = result.worlds[ix[name], c0:c1 + 1, 3, :3]
            self.assertLess(float(np.abs(path - path[0]).max()), 1e-6, name)   # turned, and planted

    def test_a_turned_foot_rolling_onto_its_ball_does_not_slide(self):
        # the left foot's last contact rolls onto its ball (its heel up 25 deg by the end): the toes' turn is a
        # rigid motion of the whole foot about the contact's point, so the ball stays where the clip keeps it
        clip = synthetic_stop()
        worlds = clip.worlds.copy()
        ix = clip.index
        below = sorted(pc._subtree(clip, ix["foot_l"]) | {ix["foot_l"]})
        for f in range(36, clip.F):
            angle = math.radians(25.0) * _smoothstep((f - 36) / 10.0)
            pivot = worlds[ix["ball_l"], f, 3, :3].copy()
            turn = pc.matrix(pc.exp_rot([-angle, 0.0, 0.0]), np.zeros(3))      # heel up: about the side axis
            for j in below:
                m = worlds[j, f].copy()
                m[3, :3] -= pivot
                worlds[j, f] = m @ turn
                worlds[j, f, 3, :3] += pivot
        rolled = pc.Clip(clip.names, clip.parents, worlds, 30.0, "rolled")
        a = pc.Analysis(rolled)
        pose = dict(pc.prepare(a, statics_of(rolled), pose_from(synthetic_stop(drop_end=10.0, lean_end=0.3), 49)))
        pose["knee_turn"] = {"l": 0.7, "r": 0.0}
        result = pc.evaluate(a, pose, k=pc.knobs(leg_match=0.0, knee_foot=1.0, **STILL))
        c0, c1 = a.feet["l"]["contacts"][-1]
        self.assertLessEqual(c0, 36)
        self.assertGreater(float(np.abs(result.worlds[ix["foot_l"], c1, 3, 1] - result.worlds[ix["foot_l"], c0, 3, 1])),
                           1.0)                                       # the heel did rise
        ball = result.worlds[ix["ball_l"], c0:c1 + 1, 3, :3]
        self.assertLess(float(np.abs(ball - ball[0]).max()), 1e-6)

    def test_a_foot_in_the_air_turns_about_itself(self):
        # half way between two contacts the toes' turn turns the foot where it is - about the contact's point a foot
        # far from it would swing wide
        pose = dict(self.pose)
        pose["knee_turn"] = {"l": 0.7, "r": 0.0}
        plan = pc._Plan(self.a, pose, pc.knobs(leg_match=0.0, knee_foot=1.0, **STILL))
        (_c0, off), (on, _c1) = self.a.feet["l"]["contacts"][:2]
        mid = (off + on) // 2
        self.assertAlmostEqual(float(plan.pivot_w["l"][mid]), math.sin(math.pi * (mid - off) / float(on - off)))
        self.assertGreater(abs(float(plan.toe_extra["l"][mid])), 0.05)
        fo = self.a.feet["l"]["joints"][2]
        bare = plan.motions.apply("l", mid, self.a.pos[fo, mid]) + plan.lift_off["l"][mid]
        about_contact = np.linalg.norm((bare - plan.toe_pivot["l"][mid]) @ (pc.yaw(float(plan.toe_extra["l"][mid])) -
                                                                             np.eye(3)))
        moved = float(np.linalg.norm(plan.ankle("l", mid) - bare))
        self.assertLessEqual(moved, (1.0 - float(plan.pivot_w["l"][mid])) * about_contact + 1e-9)
        self.assertEqual(float(plan.pivot_w["l"][self.a.feet["l"]["contacts"][-1][0] + 2]), 0.0)

    def test_leg_turn_scales_the_knees(self):
        pose = dict(self.pose)
        pose["knee_turn"] = {"l": 0.2, "r": -0.1}
        f = self.clip.F - 1
        for turn in (0.0, 1.0, 2.0):
            plan = pc._Plan(self.a, pose, pc.knobs(leg_turn=turn, leg_match=0.0, knee_foot=1.0, **STILL))
            self.assertAlmostEqual(plan.knee("l", f), 0.2 * turn, places=9)
            self.assertAlmostEqual(plan.knee("r", f), -0.1 * turn, places=9)
        plan = pc._Plan(self.a, pose, pc.knobs(leg_turn_l=0.0, leg_match=0.0, knee_foot=1.0, **STILL))
        self.assertAlmostEqual(plan.knee("l", f), 0.0, places=9)
        self.assertAlmostEqual(plan.knee("r", f), -0.1, places=9)

    def test_foot_lift_and_swing_out(self):
        ix = self.clip.index
        base = self.evaluate()
        high = self.evaluate(lift_l=2.0)
        out = self.evaluate(swing_out_l=10.0)
        plan = pc._Plan(self.a, self.pose, pc.knobs(lift_l=2.0, **STILL))
        u, ends = pc.gaps(self.a.feet["l"]["contacts"], self.clip.F)
        middle = int(np.nanargmin(np.abs(u - 0.5)))
        t_off, t_on = ends[middle]
        clip_ankle = self.a.feet["l"]["ankle"]
        over = float(clip_ankle[middle, 1] - ((1 - u[middle]) * clip_ankle[t_off, 1] + u[middle] * clip_ankle[t_on, 1]))
        self.assertGreater(over, 3.0)
        lifted = high.worlds[ix["foot_l"], middle, 3, :3] - base.worlds[ix["foot_l"], middle, 3, :3]
        self.assertAlmostEqual(float(lifted[1]), over, delta=0.05)          # twice as high over its line
        aside = out.worlds[ix["foot_l"], middle, 3, :3] - base.worlds[ix["foot_l"], middle, 3, :3]
        self.assertAlmostEqual(float(aside[0]), 10.0 * math.sin(math.pi * u[middle]), delta=0.05)
        for result in (high, out):                                        # the contacts do not move
            for c0, c1 in self.a.feet["l"]["contacts"]:
                np.testing.assert_allclose(result.worlds[ix["foot_l"], c0:c1 + 1, 3, :3],
                                           base.worlds[ix["foot_l"], c0:c1 + 1, 3, :3], atol=1e-6)
        self.assertTrue(np.all(np.isnan(plan.gap_u["r"])))                 # the right foot never leaves

    def test_foot_lag_hangs_the_foot_in_its_shin_late(self):
        ix = self.clip.index
        lag = 2.0
        result = self.evaluate(foot_lag_l=lag)
        plan = pc._Plan(self.a, self.pose, pc.knobs(foot_lag_l=lag, **STILL))
        air = plan.air_u["l"]
        flying = [f for f in range(self.clip.F) if not np.isnan(air[f]) and pc.swing_weight(air[f]) > 0.999]
        self.assertTrue(flying)
        fo, ca = ix["foot_l"], ix["calf_l"]
        for f in flying:
            local = pc.orthonormal(result.worlds[fo, f, :3, :3]) @ pc.orthonormal(result.worlds[ca, f, :3, :3]).T
            np.testing.assert_allclose(local, plan.local_at(fo, f - lag), atol=1e-6)

    def test_gait_lean_drops_the_clips_forward_lean(self):
        k = pc.knobs(gait_lean=0.0, **STILL)
        result = pc.evaluate(self.a, self.pose, k=k)
        plan = pc._Plan(self.a, self.pose, k)
        a = self.a
        for j in (self.clip.index["spine_01"], self.clip.index["spine_03"]):
            for f in range(0, 30, 3):
                w = pc.log_rot(a.rel_ref[j].T @ a.rel[j, f])
                got = pc.log_rot(plan.rel(j, f).T @ (result.worlds[j, f, :3, :3] @ a.heading[f].T))
                expect = np.array([min(w[0], 0.0), w[1], w[2]])
                np.testing.assert_allclose(got, expect, atol=1e-5)

    def test_head_zero_keeps_the_poses_gaze(self):
        result = self.evaluate(head=0.0)
        plan = pc._Plan(self.a, self.pose, pc.knobs(head=0.0, **STILL))
        head = self.clip.index["head"]
        for f in range(self.clip.F):
            np.testing.assert_allclose(result.worlds[head, f, :3, :3] @ self.a.heading[f].T, plan.rel(head, f), atol=1e-6)

    def test_exaggeration_zero_is_every_motion_zero(self):
        one = self.evaluate(exaggeration=0.0)
        other = self.evaluate(spine=0.0, pelvis_rot=0.0, bob=0.0, head=0.0, arms=0.0)
        np.testing.assert_allclose(one.worlds, other.worlds, atol=1e-9)

    def test_an_arm_a_side(self):
        ix = self.clip.index
        result = self.evaluate(arms_l=0.0)
        plan = pc._Plan(self.a, self.pose, pc.knobs(arms_l=0.0, **STILL))
        up = ix["upperarm_l"]
        for f in range(0, 30, 4):
            local = result.worlds[up, f, :3, :3] @ np.linalg.inv(result.worlds[ix["clavicle_l"], f, :3, :3])
            np.testing.assert_allclose(pc.orthonormal(local), plan.local(up, f), atol=1e-6)
        gains = plan.arm_gains(0)
        self.assertEqual(gains[ix["upperarm_l"]], 0.0)
        self.assertEqual(gains[ix["upperarm_r"]], 1.0)
        plan = pc._Plan(self.a, self.pose, pc.knobs(elbow=0.5, arms=2.0, **STILL))
        gains = plan.arm_gains(0)
        self.assertEqual(gains[ix["lowerarm_l"]], 1.0)
        self.assertEqual(gains[ix["upperarm_l"]], 2.0)

    def test_balance_zero_carries_nothing(self):
        self.assertGreater(self.evaluate().info["carry"], 0.01)
        self.assertLess(self.evaluate(balance=0.0).info["carry"], 1e-9)

    def test_stance_a_side(self):
        ix = self.clip.index
        wide = pc.prepare(self.a, self.statics, pose_from(synthetic_stop(wide=8.0), 49))
        k = pc.knobs(stance_l=2.0, **STILL)
        base = pc.evaluate(self.a, wide, k=pc.knobs(**STILL))
        result = pc.evaluate(self.a, wide, k=k)
        f = self.clip.F - 1
        mid = wide["mid"]
        for side, factor in (("l", 2.0), ("r", 1.0)):
            got = result.worlds[ix["foot_" + side], f, 3, 0] - mid[0]
            was = base.worlds[ix["foot_" + side], f, 3, 0] - mid[0]
            self.assertAlmostEqual(got, was * factor, places=3, msg=side)


class StraightLimb(unittest.TestCase):
    def test_a_limb_stretched_past_its_reach_keeps_its_plane(self):
        # the left hand held 10 cm past the left arm's reach about frames 20..30 (the grip's spring can carry the held
        # hand there): the arm straightens on the reach line, its plane still the elbow's - no frame-to-frame flip
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        ix = clip.index
        kin = clip.worlds.copy()
        below = sorted(pc._subtree(clip, ix["hand_l"]))
        for f in range(16, 35):                   # eased in over 16..20 and out over 30..34 (no jump of its own)
            amount = 10.0 * _smoothstep(min((f - 16) / 4.0, (34 - f) / 4.0, 1.0))
            push = amount * pc._unit(kin[ix["hand_l"], f, 3, :3] - kin[ix["upperarm_l"], f, 3, :3])
            kin[below, f, 3, :3] += push
        chains = dict((s, [ix["%s_%s" % (b, s)] for b in ("upperarm", "lowerarm", "hand")]) for s in pc.SIDES)
        out = pc._grip_motion(a, kin, chains, pc.knobs(arm_drag=0.5, arm_bounce=0.0))
        up = pc._batch_orthonormal(out[ix["upperarm_l"]][:, :3, :3])
        turns = [math.degrees(float(np.linalg.norm(pc._log3(up[f - 1].T @ up[f])))) for f in range(19, 33)]
        self.assertLess(max(turns), 30.0, [round(t, 1) for t in turns])    # the old plane rule: 155-177 deg
        for f in range(21, 30):                   # straight: the elbow on the line, the arm's plane the hint's
            sh, el = out[ix["upperarm_l"]][f, 3, :3], out[ix["lowerarm_l"]][f, 3, :3]
            hand = out[ix["hand_l"]][f, 3, :3]
            line = pc._unit(hand - sh)
            self.assertLess(float(np.linalg.norm((el - sh) - np.dot(el - sh, line) * line)), 1e-6)

    def test_the_bend_side_is_the_hints_off_the_line(self):
        e = np.array([0.0, -1.0, 0.0])
        np.testing.assert_allclose(pc.bend_side(np.array([0.3, -0.5, 1.0]), e), pc._unit(np.array([0.3, 0.0, 1.0])))
        side = pc.bend_side(e * 2.0, e)                         # a hint along the line: any perpendicular
        self.assertAlmostEqual(float(np.dot(side, e)), 0.0, places=12)
        self.assertAlmostEqual(float(np.linalg.norm(side)), 1.0, places=12)


class LegMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = synthetic_stop()
        cls.a = pc.Analysis(cls.clip)
        cls.statics = statics_of(cls.clip)
        cls.angle = math.radians(30.0)
        cls.pose = pc.prepare(cls.a, cls.statics, turned_pose(cls.clip, 49, cls.angle))

    def test_prepare_reads_the_hips_and_toes_turn(self):
        self.assertAlmostEqual(self.pose["hips_yaw"], self.angle, places=3)
        for side in pc.SIDES:
            self.assertAlmostEqual(self.pose["toe"][side], self.angle, places=3)
        straight = pc.prepare(self.a, self.statics, pose_from(self.clip, 49))
        self.assertAlmostEqual(straight["hips_yaw"], 0.0, places=4)

    def test_running_the_hips_give_their_turn_to_the_spine(self):
        k = pc.knobs(stance_speed=30.0, **STILL)
        plan = pc._Plan(self.a, self.pose, k)
        still = self.a.stillness_at(30.0)
        np.testing.assert_allclose(plan.hips_turn, (1.0 - still) * self.angle, atol=1e-3)
        moving = int(np.argmin(still))
        self.assertGreater(plan.hips_turn[moving], 0.1)
        self.assertLess(abs(plan.hips_turn[-1]), 1e-9)                   # standing: the pose as it is
        ix = self.clip.index
        theta = plan.hips_turn[moving]
        for name, back in (("pelvis", 1.0), ("spine_01", 0.6), ("spine_02", 0.25), ("spine_03", 0.0)):
            j = ix[name]
            turned = pc.yaw_of(plan.rel(j, moving)) - pc.yaw_of(plan.final.rel[j])
            self.assertAlmostEqual(turned, -theta * back, places=2, msg=name)
        unmatched = pc._Plan(self.a, self.pose, pc.knobs(stance_speed=30.0, leg_match=0.0, **STILL))
        self.assertTrue(np.all(unmatched.hips_turn == 0.0))


class CyclePostureStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = synthetic_stop()
        cls.a = pc.Analysis(cls.clip)
        cls.statics = statics_of(cls.clip)

    def test_a_cycle_that_is_the_clip_gives_the_reference(self):
        cycle = pc.Cycle(pc.Clip(self.clip.names, self.clip.parents, self.clip.worlds, 30.0, "self"))
        posture = pc.CyclePosture(self.a, self.statics, cycle, self.statics)
        weights = np.zeros(self.clip.F)
        weights[:cycle.period] = 1.0            # the frames the cycle averages (it drops the clip's repeated last)
        t = posture.targets(self.a, pc.knobs(), weights)
        for name in ("pelvis", "spine_01", "spine_03", "head"):
            j = self.clip.index[name]
            np.testing.assert_allclose(t["rel"][j], self.a.rel_ref[j], atol=1e-6, err_msg=name)
        j = self.clip.index["upperarm_l"]
        np.testing.assert_allclose(t["local"][j], self.a.local_ref[j], atol=1e-6)
        self.assertAlmostEqual(t["height"], self.a.h_ref, places=4)
        # the gait's turns: the stop's read on its steps at speed, the cycle's over its whole loop - near, not equal
        self.assertAlmostEqual(t["hips_yaw"], 0.0, delta=0.01)
        for side in pc.SIDES:
            self.assertAlmostEqual(t["knee_turn"][side], 0.0, delta=0.01)
            self.assertAlmostEqual(t["toe"][side], 0.0, delta=0.01)

    def test_the_gait_is_read_on_the_ground_against_the_travel(self):
        clip = self.clip
        ones = np.ones(clip.F)
        base = pc.gait(clip, ones)
        # the whole clip turned 40 deg about up, read against a travel turned the same: the same gait
        turn = pc.matrix(pc.yaw(math.radians(40.0)), np.zeros(3))
        turned = pc.Clip(clip.names, clip.parents, clip.worlds @ turn, 30.0, "turned")
        again = pc.gait(turned, ones, math.radians(40.0))
        for side in pc.SIDES:
            self.assertAlmostEqual(again["toe"][side], base["toe"][side], places=6)
            self.assertAlmostEqual(again["knee_turn"][side], base["knee_turn"][side], places=6)
        self.assertAlmostEqual(again["hips_yaw"], base["hips_yaw"], places=6)
        self.assertAlmostEqual(again["height"], base["height"], places=6)
        # the left foot turned out 20 deg about its ankle on every frame: its toe line reads 20 deg more, outward
        worlds = clip.worlds.copy()
        ix = clip.index
        below = sorted(pc._subtree(clip, ix["foot_l"]))
        for f in range(clip.F):
            pivot = worlds[ix["foot_l"], f, 3, :3].copy()
            out = pc.matrix(pc.yaw(math.radians(20.0)), np.zeros(3))
            for j in below:
                m = worlds[j, f].copy()
                m[3, :3] -= pivot
                worlds[j, f] = m @ out
                worlds[j, f, 3, :3] += pivot
        splayed = pc.gait(pc.Clip(clip.names, clip.parents, worlds, 30.0, "splayed"), ones)
        self.assertAlmostEqual(math.degrees(pc._wrapped(splayed["toe"]["l"] - base["toe"]["l"])), 20.0, places=4)
        self.assertAlmostEqual(splayed["toe"]["r"], base["toe"]["r"], places=9)

    def test_a_lower_leaning_cycle_lowers_and_leans_the_start(self):
        other = synthetic_stop(drop_end=12.0, lean_end=0.4)
        still = pc.Clip(other.names, other.parents, other.worlds[:, 32:], 30.0, "crouch")
        posture = pc.CyclePosture(self.a, self.statics, pc.Cycle(still), self.statics)
        weights = np.zeros(self.clip.F)
        weights[32:] = 1.0                                          # the clip's own still part, against the crouch
        t = posture.targets(self.a, pc.knobs(), weights)
        self.assertAlmostEqual(t["height"], self.a.h_ref - 12.0, delta=0.05)
        spine = self.clip.index["spine_01"]
        angle = math.degrees(np.linalg.norm(pc.log_rot(self.a.rel_ref[spine].T @ t["rel"][spine])))
        self.assertAlmostEqual(angle, math.degrees(0.4), delta=0.5)

    def test_the_start_from_the_cycle_end_to_end(self):
        cycle = pc.Cycle(pc.Clip(self.clip.names, self.clip.parents, self.clip.worlds[:, :30], 30.0, "run"))
        posture = pc.CyclePosture(self.a, self.statics, cycle, self.statics)
        pose = pc.prepare(self.a, self.statics, pose_from(synthetic_stop(drop_end=10.0), 49))
        result = pc.evaluate(self.a, pose, k=pc.knobs(final_speed=30.0, **STILL), start=posture)
        self.assertEqual(result.info["start_kind"], "cycle")
        self.assertTrue(np.all(np.isfinite(result.worlds)))
        with self.assertRaises(pc.Refusal):
            posture.targets(self.a, pc.knobs(), np.zeros(self.clip.F))

    def test_mean_posture_is_the_frame_for_one_frame(self):
        weights = np.zeros(self.clip.F)
        weights[10] = 1.0
        bones = pc.mean_posture(self.clip, weights, self.statics)
        for name in ("pelvis", "hand_l", "foot_r"):
            np.testing.assert_allclose(np.array(bones[name]["world"]).reshape(4, 4)[:3, :3],
                                       self.clip.worlds[self.clip.index[name], 10, :3, :3], atol=1e-5)
        root = self.clip.index["root"]
        offset = self.clip.worlds[self.clip.index["hand_l"], 10, 3, :3] - self.clip.worlds[root, 10, 3, :3]
        np.testing.assert_allclose(np.array(bones["hand_l"]["world"]).reshape(4, 4)[3, :3], offset, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
