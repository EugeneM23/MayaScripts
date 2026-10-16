"""The parametric walk's model (walkmodel.py) on a synthetic walker: numpy only, no Maya."""

import importlib
import math
import os
import subprocess
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
FOLDER = os.path.join(os.path.dirname(HERE), "docs", "superpowers", "plans", "walkparam")   # its dev tools
#  The tool's old module names (2026-10-12) -> the plugin package's (2026-10-13, maya_walk)
MODULES = {"walkmodel": "model", "walkfile": "files", "walktarget": "target", "walkpose": "pose",
           "skeldar_walk": "scene", "panel": "panel"}


def load(name):
    """A module of the plugin's maya_walk package, by the tool's old name."""
    if PLUGIN not in sys.path:
        sys.path.insert(0, PLUGIN)
    return importlib.import_module("maya_walk." + MODULES.get(name, name))


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
                % os.path.join(PLUGIN, "maya_walk", "model.py"))
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

    def test_smooth_cover_lies_over_the_need_and_is_periodic(self):
        need = np.zeros(30)
        need[5:9] = [1.0, 4.0, 3.0, 0.5]
        need[20] = 2.0
        cover = wm.smooth_cover(need, 2.0)
        self.assertTrue(np.all(cover >= need - 1e-12))
        self.assertLess(cover[13], 0.5)
        self.assertLess(cover[0], 0.5)
        self.assertTrue(np.allclose(wm.smooth_cover(np.roll(need, 7), 2.0), np.roll(cover, 7)))
        self.assertTrue(np.allclose(wm.smooth_cover(np.zeros(12), 2.0), 0.0))
        steps = np.abs(np.diff(np.append(cover, cover[0])))
        self.assertLess(float(steps.max()), float(np.abs(np.diff(np.append(need, need[0]))).max()))
        self.assertLess(float(cover.max()), 1.25 * float(need.max()))

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
                         ["pose", "stride", "tempo", "lift", "in_place", "foot_placement", "ground_time", "stance", "swing_out", "leg_match", "leg_turn", "knee_foot", "foot_lag",
                          "foot_flex", "foot_flat", "bob", "sway", "surge", "root_sway", "pelvis_height", "pelvis_forward", "pelvis_rot", "pelvis_twist", "pelvis_list",
                          "spine", "chest_twist", "chest_sway", "gait_lean", "torso_drag", "torso_bounce", "arms", "elbow",
                          "arm_drag", "arm_bounce", "head", "head_drag", "overlap", "weight", "balance", "exaggeration"])
        self.assertEqual(wm.DEFAULTS["pose"], 0.0)
        self.assertEqual((wm.DEFAULTS["balance"], wm.RANGES["balance"]), (1.0, (0.0, 1.0)))
        self.assertEqual((wm.DEFAULTS["stance"], wm.DEFAULTS["swing_out"], wm.DEFAULTS["knee_foot"]), (1.0, 0.0, 0.5))
        self.assertEqual((wm.DEFAULTS["foot_lag"], wm.DEFAULTS["foot_flex"]), (0.0, 1.0))
        self.assertEqual((wm.DEFAULTS["pelvis_twist"], wm.DEFAULTS["pelvis_list"]), (5.0, 4.0))
        self.assertEqual((wm.DEFAULTS["leg_match"], wm.RANGES["leg_match"]), (1.0, (0.0, 1.0)))
        self.assertEqual((wm.DEFAULTS["in_place"], wm.RANGES["in_place"]), (0.0, (0.0, 1.0)))

    def test_the_meeting_of_a_knee_and_its_foot(self):
        free = math.radians(wm.TWIST_FREE_DEG)
        self.assertEqual(wm.meet(0.1, 0.05, 0.5), (0.1, 0.05))          # within the free twist: as given
        knee, foot = wm.meet(math.radians(40.0), 0.0, 0.5)              # 25 deg past it, shared half and half
        self.assertAlmostEqual(math.degrees(knee), 27.5, places=9)
        self.assertAlmostEqual(math.degrees(foot), 12.5, places=9)
        self.assertAlmostEqual(knee - foot, free, places=12)
        self.assertAlmostEqual(math.degrees(wm.meet(math.radians(40.0), 0.0, 0.0)[0]), 15.0, places=9)   # knee to foot
        self.assertAlmostEqual(math.degrees(wm.meet(math.radians(40.0), 0.0, 1.0)[1]), 25.0, places=9)   # foot to knee
        knee, foot = wm.meet(0.0, math.radians(-30.0), 0.5)
        self.assertAlmostEqual(math.degrees(knee - foot), 15.0, places=9)
        self.assertAlmostEqual(math.degrees(knee), -7.5, places=9)

    def test_the_swing_weight_is_zero_on_the_ground_and_one_mid_swing(self):
        self.assertEqual(wm.swing_weight(0.0), 0.0)
        self.assertEqual(wm.swing_weight(1.0), 0.0)
        self.assertEqual(wm.swing_weight(0.5), 1.0)
        self.assertAlmostEqual(wm.swing_weight(0.125), 0.5, places=12)
        values = [wm.swing_weight(s / 100.0) for s in range(101)]
        self.assertTrue(all(0.0 <= v <= 1.0 for v in values))


UP = np.array([0.0, 1.0, 0.0])
FWD = np.array([0.0, 0.0, 1.0])
L1, L2 = 48.0, 47.0
UPPER = ("spine_01", "spine_02", "neck_01", "head", "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
         "index_01_l", "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r", "index_01_r")
BONES = [  # name, parent, local translation (None: the generator places it)
    ("root", None, None), ("pelvis", "root", None),
    ("spine_01", "pelvis", (0, 10, 0)), ("spine_02", "spine_01", (0, 15, 0)),
    ("neck_01", "spine_02", (0, 22, 0)), ("head", "neck_01", (0, 9, 0)),
    ("clavicle_l", "spine_02", (4, 18, 0)), ("upperarm_l", "clavicle_l", (14, 0, 0)),
    ("lowerarm_l", "upperarm_l", (28, 0, 0)), ("hand_l", "lowerarm_l", (26, 0, 0)),
    ("index_01_l", "hand_l", (9, 0, 0)),
    ("clavicle_r", "spine_02", (-4, 18, 0)), ("upperarm_r", "clavicle_r", (-14, 0, 0)),
    ("lowerarm_r", "upperarm_r", (-28, 0, 0)), ("hand_r", "lowerarm_r", (-26, 0, 0)),
    ("index_01_r", "hand_r", (-9, 0, 0)),
    ("thigh_l", "pelvis", (9, -5, 0)), ("calf_l", "thigh_l", None), ("foot_l", "calf_l", None),
    ("ball_l", "foot_l", (0, -6, 12)), ("thigh_twist_01_l", "thigh_l", (24, 0, 0)),
    ("thigh_r", "pelvis", (-9, -5, 0)), ("calf_r", "thigh_r", None), ("foot_r", "calf_r", None),
    ("ball_r", "foot_r", (0, -6, 12)), ("thigh_twist_01_r", "thigh_r", (24, 0, 0)),
    ("ik_foot_root", "root", (0, 0, 0)), ("ik_foot_l", "ik_foot_root", None),
    ("ik_foot_r", "ik_foot_root", None), ("camera_root", "root", (0, 160, 0)),
]


def mat(rot, pos):
    out = np.eye(4)
    out[:3, :3] = rot
    out[3, :3] = pos
    return out


def upper_rot(name, phi):
    w = 2.0 * math.pi * phi
    s = math.sin
    return {
        "spine_01": rot_y(-4 * s(w)) @ rot_x(2 * s(2 * w)),
        "spine_02": rot_y(-3 * s(w + 0.3)),
        "neck_01": rot_x(3 * s(2 * w + 0.5)),
        "head": rot_y(2 * s(w)),
        "clavicle_l": rot_z(3 * s(w + 0.4)), "clavicle_r": rot_z(-3 * s(w + 0.4)),
        "upperarm_l": rot_y(25 * s(w + math.pi)) @ rot_z(-80), "upperarm_r": rot_y(25 * s(w)) @ rot_z(80),
        "lowerarm_l": rot_z(-10 - 8 * s(w + math.pi)), "lowerarm_r": rot_z(10 + 8 * s(w)),
        "hand_l": rot_x(5 * s(w)), "hand_r": rot_x(-5 * s(w)),
        "index_01_l": rot_z(-10 - 5 * s(w)), "index_01_r": rot_z(10 + 5 * s(w)),
    }[name]


def foot_world(side, phi, travel, stance=0.6, lift=10.0, slip=0.0):
    """A foot planted for `stance` of the cycle (sliding `slip` cm forward over it), its swing between."""
    offset, x = (0.0, 10.0) if side == "l" else (0.5, -10.0)
    rel = phi - offset
    k = math.floor(rel)
    r = rel - k
    step = lambda i: np.array([x, 8.0, travel * (i + offset + stance / 2.0)])
    if r <= stance:
        return np.eye(3), step(k) + FWD * slip * (r / stance - 0.5)
    u = (r - stance) / (1.0 - stance)
    s = u * u * (3.0 - 2.0 * u)
    start, end = step(k) + FWD * slip / 2.0, step(k + 1) - FWD * slip / 2.0
    return rot_x(-20 * math.sin(math.pi * s)), start * (1 - s) + end * s + UP * lift * math.sin(math.pi * s)


def leg(hip, ankle):
    v = ankle - hip
    d = np.linalg.norm(v)
    e = v / d
    bend = FWD - np.dot(FWD, e) * e
    bend /= np.linalg.norm(bend)
    along = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    knee = hip + along * e + math.sqrt(L1 * L1 - along * along) * bend
    n = np.cross(e, bend)
    n /= np.linalg.norm(n)
    frame = lambda u: np.stack([u / np.linalg.norm(u), n, np.cross(u / np.linalg.norm(u), n)])
    return knee, frame(knee - hip), frame(ankle - knee)


# two steps of each foot a cycle, uneven: (strike, lift-off) as shares of the cycle (a long and a short stance)
TWO_STEPS = {"l": ((0.00, 0.30), (0.50, 0.65)), "r": ((0.25, 0.55), (0.62, 1.02))}


def foot_world_steps(side, phi, travel, spans, lift=10.0, slip=0.0):
    """A foot planted over each of its `spans` (sliding `slip` cm forward over each), its print under the body's
    mean place at the span's middle; its swing between one print and the next."""
    x = 10.0 if side == "l" else -10.0
    best = None
    for i, (on, off) in enumerate(spans):
        k = math.floor(phi - on)
        r = phi - on - k
        if best is None or r < best[2]:
            best = (i, k, r)
    i, k, r = best
    on, off = spans[i]
    at = lambda j, kk: np.array([x, 8.0, travel * (0.5 * (spans[j][0] + spans[j][1]) + kk)])
    if r <= off - on:
        return np.eye(3), at(i, k) + FWD * slip * (r / (off - on) - 0.5)
    j = (i + 1) % len(spans)
    kj = k + (1 if j == 0 else 0)
    u = (phi - (off + k)) / (spans[j][0] + kj - (off + k))
    s = u * u * (3.0 - 2.0 * u)
    start, end = at(i, k) + FWD * slip / 2.0, at(j, kj) - FWD * slip / 2.0
    return rot_x(-20 * math.sin(math.pi * s)), start * (1 - s) + end * s + UP * lift * math.sin(math.pi * s)


def synthetic(P=24, travel=120.0, stance=0.6, lift=10.0, slip=0.0, strides=1, spans=None):
    """A walker built the way the model reads one: feet planted in stance, legs by IK, the rest FK; `strides`
    strides a cycle (the body's motion that many times), its feet on `spans` ({side: ((strike, lift-off), ...)},
    shares of the cycle) when given."""
    names = [b[0] for b in BONES]
    parents = [names.index(b[1]) if b[1] else -1 for b in BONES]
    local = dict((b[0], b[2]) for b in BONES)
    worlds = np.zeros((len(names), P + 1, 4, 4))
    for f in range(P + 1):
        phi = f / float(P)
        w = 2.0 * math.pi * phi * strides
        W = {}
        W["root"] = mat(np.eye(3), [2 * math.sin(w), 0.0, travel * phi + 2 * math.sin(2 * w)])
        W["pelvis"] = mat(rot_y(5 * math.sin(w)) @ rot_x(2 * math.sin(2 * w)) @ rot_z(3 * math.sin(w)),
                          [2 * math.sin(w), 90 + 3 * math.cos(2 * w + 0.3), travel * phi + 2 * math.sin(2 * w)])
        for name in UPPER:
            parent = BONES[names.index(name)][1]
            W[name] = mat(upper_rot(name, phi * strides), local[name]) @ W[parent]
        for side in "lr":
            pelvis = W["pelvis"]
            hip = np.array(local["thigh_" + side], float) @ pelvis[:3, :3] + pelvis[3, :3]
            foot_rot, ankle = (foot_world(side, phi, travel, stance, lift, slip) if spans is None
                               else foot_world_steps(side, phi, travel, spans[side], lift, slip))
            knee, thigh_rot, calf_rot = leg(hip, ankle)
            W["thigh_" + side] = mat(thigh_rot, hip)
            W["calf_" + side] = mat(calf_rot, knee)
            W["foot_" + side] = mat(foot_rot, ankle)
            W["ball_" + side] = mat(np.eye(3), local["ball_" + side]) @ W["foot_" + side]
            W["thigh_twist_01_" + side] = mat(np.eye(3), local["thigh_twist_01_" + side]) @ W["thigh_" + side]
            W["ik_foot_" + side] = W["foot_" + side].copy()
        W["ik_foot_root"] = W["root"].copy()
        W["camera_root"] = mat(np.eye(3), local["camera_root"]) @ W["root"]
        for j, name in enumerate(names):
            worlds[j, f] = W[name]
    return names, parents, worlds


_CACHE = {}


def clip(**kw):
    key = tuple(sorted((k, repr(v)) for k, v in kw.items()))
    if key not in _CACHE:
        _CACHE[key] = synthetic(**kw)
    names, parents, worlds = _CACHE[key]
    return wm.Clip(names, parents, worlds.copy(), fps=30.0, up=(0, 1, 0), name="synthetic")


def walk(**kw):
    return wm.analyse(clip(**kw))


class AnalysisTests(unittest.TestCase):

    def test_cycle_travel_and_summary(self):
        w = walk()
        self.assertEqual(w.P, 24)
        self.assertTrue(np.allclose(w.travel, [0.0, 0.0, 120.0]))
        self.assertTrue(np.allclose(w.fwd, FWD) and np.allclose(w.side, [1.0, 0.0, 0.0]))
        self.assertIn("cycle 24 frames", w.summary())
        self.assertIn("stride 60.0 cm", w.summary())
        self.assertIn("1.50 m/s", w.summary())

    def test_the_sampler_gives_the_source_back_on_whole_frames(self):
        w, c = walk(), clip()
        for j in range(len(c.names)):
            for f in (0, 5, 13, 23, 24):
                self.assertTrue(np.allclose(w.source_world(j, float(f)), c.worlds[j, f], atol=1e-9),
                                (c.names[j], f))

    def test_stance_is_found_around_mid_stance(self):
        w = walk()
        left, right = w.feet["l"], w.feet["r"]
        self.assertAlmostEqual(left.mid % 24, 7.0, delta=1.0)
        self.assertAlmostEqual(right.mid % 24, 19.0, delta=1.0)
        self.assertTrue(10 <= left.length <= 15 and 10 <= right.length <= 15)
        self.assertAlmostEqual(left.coords[1], 10.0, delta=0.01)    # aside: the left foot +10
        self.assertAlmostEqual(right.coords[1], -10.0, delta=0.01)

    def test_reach_is_the_straightest_leg(self):
        w, c = walk(), clip()
        i = dict((n, k) for k, n in enumerate(c.names))
        d = np.linalg.norm(c.worlds[i["foot_l"], :, 3, :3] - c.worlds[i["thigh_l"], :, 3, :3], axis=1)
        self.assertAlmostEqual(w.reach["l"], float(d.max()) / (L1 + L2), places=9)

    def test_kinds_lags_and_helpers(self):
        w = walk()
        kind = dict(zip(w.names, w.kind))
        self.assertEqual([kind[n] for n in ("root", "pelvis", "thigh_l", "spine_02", "head", "upperarm_l",
                                            "index_01_l", "ball_l", "thigh_twist_01_l", "ik_foot_l")],
                         ["root", "pelvis", "leg", "spine", "head", "arm", "finger", "local", "local", "helper"])
        lag = dict(zip(w.names, w.lag))
        self.assertEqual((lag["spine_01"], lag["head"], lag["hand_l"], lag["index_01_l"], lag["thigh_l"]),
                         (0.0, 0.0, 1.0, 1.0, 0.0))        # Overlap: the arms only (the trunk and the head: their drags)
        follows = dict((w.names[h], w.names[b]) for h, (b, rel) in w.follows.items())
        self.assertEqual(follows["ik_foot_l"], "foot_l")
        self.assertEqual(follows["camera_root"], "root")
        order = [w.names[j] for j in w.order]
        self.assertLess(order.index("pelvis"), order.index("thigh_l"))
        self.assertLess(order.index("hand_r"), order.index("index_01_r"))
        self.assertEqual(set(order[-4:]), {"ik_foot_root", "ik_foot_l", "ik_foot_r", "camera_root"})


class TrimTests(unittest.TestCase):
    """A frame written twice (AGS_Sprint's last, 2026-10-14) is one frame: the cycle is read without the copy."""

    def test_a_repeated_last_frame_is_dropped(self):
        c = clip()
        dup = wm.Clip(c.names, c.parents, np.concatenate([c.worlds, c.worlds[:, -1:]], axis=1), c.fps, c.up, c.name)
        w = wm.analyse(dup)
        self.assertEqual((w.P, w.dropped), (24, 1))
        r = w.evaluate(w.own_knobs())
        self.assertLess(float(np.abs(r.worlds - c.worlds).max()), 1e-6)
        self.assertIn("1 repeated frame dropped", w.summary())

    def test_a_repeated_first_frame_is_dropped(self):
        c = clip()
        dup = wm.Clip(c.names, c.parents, np.concatenate([c.worlds[:, :1], c.worlds], axis=1), c.fps, c.up, c.name)
        w = wm.analyse(dup)
        self.assertEqual((w.P, w.dropped), (24, 1))
        self.assertLess(float(np.abs(w.evaluate(w.own_knobs()).worlds - c.worlds).max()), 1e-6)

    def test_a_clean_cycle_drops_nothing(self):
        self.assertEqual(walk().dropped, 0)
        self.assertNotIn("repeated", walk().summary())


class RefusalTests(unittest.TestCase):

    def test_open_loop(self):
        c = clip()
        c.worlds[1:, -1, 3, 0] += 5.0     # the pose, not the travel: the root stays
        with self.assertRaises(wm.Refusal) as caught:
            wm.analyse(c)
        self.assertIn("closed loop", str(caught.exception))

    def test_in_place(self):
        with self.assertRaises(wm.Refusal) as caught:
            walk(travel=0.0)
        self.assertIn("in-place", str(caught.exception))

    def test_missing_leg_bone(self):
        c = clip()
        keep = [i for i, n in enumerate(c.names) if n != "ball_r"]
        remap = dict((old, new) for new, old in enumerate(keep))
        names = [c.names[i] for i in keep]
        parents = [remap.get(c.parents[i], -1) for i in keep]
        with self.assertRaises(wm.Refusal) as caught:
            wm.analyse(wm.Clip(names, parents, c.worlds[keep]))
        self.assertIn("ball_r", str(caught.exception))


def positions(result, name, w):
    return result.worlds[w.index[name], :, 3, :3]


def rotations(result, name, w):
    return result.worlds[w.index[name], :, :3, :3]


def local_rot(result, name, w, f):
    j = w.index[name]
    return result.worlds[j, f, :3, :3] @ result.worlds[w.parents[j], f, :3, :3].T


class IdentityTests(unittest.TestCase):

    def test_the_walks_own_knobs_give_the_source_back(self):
        w, c = walk(), clip()
        r = w.evaluate(w.own_knobs())
        self.assertEqual(r.frames, 24)
        self.assertEqual(r.worlds.shape, c.worlds.shape)
        self.assertLess(float(np.abs(r.worlds - c.worlds).max()), 1e-6)
        self.assertEqual(r.info["lowered"], 0.0)
        self.assertEqual(r.info["short"], 0.0)
        self.assertIn("24 frames, stride 60.0 cm, 1.50 m/s", wm.describe(r))

    def test_the_defaults_are_physiological_not_the_source(self):
        """The pelvis's twist and hip drop come from their degree knobs; the walk's own read differently."""
        w, c = walk(), clip()
        own = w.own_knobs()
        self.assertEqual(sorted(own), ["arm_drag", "chest_sway", "chest_twist", "foot_placement", "head_drag",
                                       "pelvis_list", "pelvis_twist", "root_sway", "torso_drag"])
        self.assertNotAlmostEqual(own["pelvis_list"], wm.DEFAULTS["pelvis_list"], places=1)
        r = w.evaluate()
        self.assertGreater(float(np.abs(r.worlds - c.worlds).max()), 1e-3)
        self.assertIn("pelvis twists", wm.describe(r))


def held(w, side, f):
    """Whether frame f lies in one of the foot's contacts (Foot placement's: down AND held still)."""
    return any((f - hs) % w.P <= to - hs for hs, to in w.contact[side])


class StepTests(unittest.TestCase):

    def test_stride_moves_the_footprints_and_keeps_the_stance_foot_still(self):
        """The walker's own feet (Foot placement may roll a stance foot about its heel or ball: FootPlacementTests)."""
        w = walk()
        r = w.evaluate({"stride": 1.3, "foot_placement": 0.0})
        foot = positions(r, "foot_l", w)
        left = w.feet["l"]
        stance = [left.on + i for i in range(left.length + 1)]
        self.assertLess(float(np.ptp(foot[stance], axis=0).max()), 1e-9)
        right = w.feet["r"]
        mid_l, mid_r = int(round(left.mid)) % 24, int(round(right.mid)) % 24
        gap = positions(r, "foot_r", w)[mid_r, 2] - foot[mid_l, 2]
        src = clip().worlds
        src_gap = src[w.index["foot_r"], mid_r, 3, 2] - src[w.index["foot_l"], mid_l, 3, 2]
        self.assertAlmostEqual(gap, 1.3 * src_gap, places=6)

    def test_stride_keeps_bone_lengths_and_the_loop(self):
        w = walk()
        r = w.evaluate({"stride": 1.3})
        for side in "lr":
            hip, knee, ankle = (positions(r, b + "_" + side, w) for b in ("thigh", "calf", "foot"))
            self.assertLess(float(np.abs(np.linalg.norm(knee - hip, axis=1) - L1).max()), 1e-9)
            self.assertLess(float(np.abs(np.linalg.norm(ankle - knee, axis=1) - L2).max()), 1e-9)
        moved = r.worlds[:, -1, 3, :3] - r.worlds[:, 0, 3, :3]
        self.assertLess(float(np.abs(moved - [0.0, 0.0, 156.0]).max()), 1e-6)
        self.assertLess(float(np.abs(r.worlds[:, -1, :3, :3] - r.worlds[:, 0, :3, :3]).max()), 1e-9)
        self.assertAlmostEqual(r.info["stride_cm"], 78.0)

    def test_tempo_resamples_the_cycle(self):
        w = walk()
        r = w.evaluate({"tempo": 30})
        self.assertEqual(r.frames, 30)
        self.assertEqual(r.worlds.shape[1], 31)
        moved = r.worlds[:, -1, 3, :3] - r.worlds[:, 0, 3, :3]
        self.assertLess(float(np.abs(moved - [0.0, 0.0, 120.0]).max()), 1e-6)
        self.assertAlmostEqual(r.info["speed"], 1.2)

    def test_lift_scales_the_swing_above_the_straight_blend(self):
        w = walk()
        r = w.evaluate({"lift": 2.0})
        src = clip().worlds[w.index["foot_l"], 19, 3, 1]
        self.assertGreater(src - 8.0, 5.0)
        self.assertAlmostEqual(positions(r, "foot_l", w)[19, 1] - 8.0, 2.0 * (src - 8.0), places=6)

    def test_stance_scales_the_spread_about_the_middle_of_the_prints(self):
        """The walker's prints stand at +10 / -10 across the line: Stance scales both about their middle."""
        w = walk()
        mid_l, mid_r = int(round(w.feet["l"].mid)) % 24, int(round(w.feet["r"].mid)) % 24
        for stance in (0.0, 0.5, 1.5):
            r = w.evaluate({"stance": stance})
            self.assertAlmostEqual(positions(r, "foot_l", w)[mid_l, 0], 10.0 * stance, places=9)
            self.assertAlmostEqual(positions(r, "foot_r", w)[mid_r, 0], -10.0 * stance, places=9)
            left = w.feet["l"]
            prints = positions(r, "foot_l", w)[[left.on + i for i in range(left.length + 1)]]
            self.assertLess(float(np.ptp(prints, axis=0).max()), 1e-6)     # the lock's own integration

    def test_swing_out_bows_the_swinging_foot_across(self):
        """+ cm out along sin(pi s) of the foot's flight (s 0 where it leaves the ground, 1 where it lands); a foot
        that is down never moves across."""
        w = walk()
        for out in (6.0, -4.0):
            r = w.evaluate({"swing_out": out})
            for f in range(24):
                s = w.air_progress("l", float(f))
                if s is None and not held(w, "l", f):
                    continue          # near the floor but still flying in at 10 cm a frame: no contact yet
                want = 0.0 if s is None else out * math.sin(math.pi * s)
                self.assertAlmostEqual(positions(r, "foot_l", w)[f, 0] - 10.0, want, places=6)
            self.assertTrue(any(w.air_progress("l", float(f)) is not None and 0.4 < w.air_progress("l", float(f)) < 0.6
                                for f in range(24)))
        r = w.evaluate({"swing_out": 6.0})
        for f in range(24):                      # the right foot: out is -side for it
            s = w.air_progress("r", float(f))
            if s is None and not held(w, "r", f):
                continue
            want = 0.0 if s is None else -6.0 * math.sin(math.pi * s)
            self.assertAlmostEqual(positions(r, "foot_r", w)[f, 0] + 10.0, want, places=6)

    def test_the_flight_never_touches_the_ground(self):
        """A foot near the ground is never in its flight (its interpolated contact may flicker just after it
        leaves: the flight is the longest stretch off the ground)."""
        w = walk()
        for side in "lr":
            flying = 0
            for i in range(24 * 8):
                tau = i / 8.0
                if w.down(side, tau):
                    self.assertIsNone(w.air_progress(side, tau), (side, tau))
                flying += w.air_progress(side, tau) is not None
            self.assertGreater(flying, 24 * 8 * 0.15, side)

    def test_a_long_stride_on_a_flat_pelvis_lowers_it_to_reach(self):
        w = walk()
        r = w.evaluate({"stride": 1.6, "bob": 0.0})
        self.assertGreater(r.info["lowered"], 1.0)
        self.assertEqual(len(r.info["drop"]), 25)
        self.assertAlmostEqual(r.info["lowered"], max(r.info["drop"]))
        self.assertLess(min(r.info["drop"]), 0.5 * r.info["lowered"])   # deepest at the contacts only
        self.assertLess(r.info["short"], 1e-6)
        for side in "lr":
            d = np.linalg.norm(positions(r, "foot_" + side, w) - positions(r, "thigh_" + side, w), axis=1)
            self.assertLessEqual(float(d.max()), w.reach[side] * (L1 + L2) + 1e-6)
        self.assertIn("pelvis lowered", wm.describe(r))

    def test_a_foot_is_down_in_stance_and_up_in_swing(self):
        w = walk()
        left = w.feet["l"]
        self.assertTrue(w.down("l", left.mid))
        self.assertFalse(w.down("l", (2 * left.on + left.length + 24) / 2.0))     # mid-swing

    def test_a_foot_in_the_air_passes_nearer_rather_than_lowering_the_pelvis(self):
        """Only feet that are down hold the pelvis down: a swing path out of reach is cut short instead."""
        w = walk()
        target = w.foot_target

        def far_in_the_air(side, tau, *rest):
            rot, ankle = target(side, tau, *rest)
            return rot, (ankle if w.down(side, tau) else ankle + 60.0 * w.side * (1.0 if side == "l" else -1.0))

        plain = w.evaluate({"balance": 0.0})
        w.foot_target = far_in_the_air
        r = w.evaluate({"balance": 0.0})
        self.assertAlmostEqual(r.info["lowered"], plain.info["lowered"], places=9)
        self.assertEqual(r.info["short"], 0.0)
        self.assertGreater(r.info["swing_in"], 10.0)
        self.assertIn("nearer the body", wm.describe(r))

    def test_helpers_keep_following(self):
        w = walk()
        r = w.evaluate({"stride": 1.2, "arms": 2.0})
        self.assertLess(float(np.abs(r.worlds[w.index["ik_foot_l"]] - r.worlds[w.index["foot_l"]]).max()), 1e-9)
        cam = positions(r, "camera_root", w) - positions(r, "root", w)
        self.assertTrue(np.allclose(cam, [0.0, 160.0, 0.0]))


class BodyTests(unittest.TestCase):

    def pelvis(self, r, w):
        return positions(r, "pelvis", w)

    def test_bob_scales_the_pelvis_about_its_mean(self):
        w, src = walk(), clip().worlds[1, :24, 3, 1]
        flat = self.pelvis(walk().evaluate({"bob": 0.0}), w)[:, 1]
        self.assertLess(float(np.ptp(flat)), 1e-9)
        r = w.evaluate({"bob": 2.0})
        dev = self.pelvis(r, w)[:24, 1] - w.pelvis_mean[2] + np.array(r.info["drop"][:24])
        self.assertTrue(np.allclose(dev, 2.0 * (src - src.mean()), atol=1e-6))

    def test_sway_zero_holds_the_pelvis_on_its_line(self):
        """The knob alone (Balance 0; with Balance the mean's correction may carry the line a constant)."""
        w = walk()
        side = self.pelvis(w.evaluate({"sway": 0.0, "balance": 0.0}), w)[:, 0]
        self.assertLess(float(np.ptp(side)), 1e-9)

    def test_arms_scale_their_swing_in_the_world(self):
        """The upper arm hangs and swings in the world: Arms 0 holds it still there, Arms 2 doubles its
        world swing; the forearm stays on it."""
        w, c = walk(), clip()
        still = rotations(w.evaluate({"arms": 0.0, "arm_drag": 0.0}), "upperarm_l", w)
        self.assertLess(max(angle(m @ still[0].T) for m in still), 1e-6)
        double = rotations(w.evaluate({"arms": 2.0, "arm_drag": 0.0}), "upperarm_l", w)
        j = w.index["upperarm_l"]
        mean = w.wmean[j]
        for f in (3, 9, 15):
            self.assertAlmostEqual(angle(double[f] @ mean.T), 2.0 * angle(c.worlds[j, f, :3, :3] @ mean.T), places=6)

    def test_upper_arms_do_not_turn_with_the_chest(self):
        w, c = walk(), clip()
        r = w.evaluate({"spine": 2.5, "arm_drag": 0.0})
        for name in ("upperarm_l", "upperarm_r"):
            j = w.index[name]
            self.assertLess(float(np.abs(rotations(r, name, w) - c.worlds[j, :, :3, :3]).max()), 1e-9)
        bent = local_rot(r, "spine_02", w, 6) @ local_rot(walk().evaluate(), "spine_02", w, 6).T
        self.assertGreater(angle(bent), 0.5)

    def test_head_zero_holds_the_head_steady_in_the_world(self):
        w = walk()
        heads = rotations(w.evaluate({"head": 0.0, "head_drag": 0.0}), "head", w)     # no motion, no overlap
        self.assertLess(float(np.abs(heads - heads[0]).max()), 1e-9)

    def test_overlap_delays_the_hand_by_its_share(self):
        w, c = walk(), clip()
        r = w.evaluate({"overlap": 2.0, "arm_drag": 0.0})
        j = w.index["hand_l"]
        for f in (2, 7, 20):
            src = c.worlds[j, f - 2, :3, :3] @ c.worlds[w.parents[j], f - 2, :3, :3].T
            self.assertLess(angle(local_rot(r, "hand_l", w, f) @ src.T), 1e-6)

    def test_weight_sinks_the_low_poses(self):
        w = walk()
        src = clip().worlds[1, :24, 3, 1]
        heavy = self.pelvis(w.evaluate({"weight": 1.0}), w)[:24, 1]
        self.assertLess(heavy.min(), src.min() - 0.3 * (src.mean() - src.min()))

    def test_exaggeration_zero_stills_the_body_but_not_the_feet(self):
        """(Without Foot placement: a planted foot may need the reach's drop, which is not the body's motion.)"""
        w = walk()
        r = w.evaluate({"exaggeration": 0.0, "foot_placement": 0.0, "torso_drag": 0.0, "head_drag": 0.0})
        pel = r.worlds[w.index["pelvis"]]
        self.assertLess(float(np.abs(pel[:, :3, :3] - pel[0, :3, :3]).max()), 1e-9)
        self.assertLess(float(np.ptp(pel[:, 3, 1])), 1e-9)
        spine = [local_rot(r, "spine_02", w, f) for f in range(25)]
        self.assertLess(max(angle(m @ spine[0].T) for m in spine), 1e-6)
        left = w.feet["l"]
        foot = positions(r, "foot_l", w)[[left.on + i for i in range(left.length + 1)]]
        self.assertLess(float(np.ptp(foot, axis=0).max()), 1e-6)


class PelvisTests(unittest.TestCase):
    """Twist and Hip drop: degree knobs on the hip line, the lumbar spine taking them back."""

    def test_the_hip_line_reads_the_knobs(self):
        w = walk()
        own = w.pelvis_fit(clip().worlds)
        self.assertAlmostEqual(own[0], w.own_knobs()["pelvis_twist"] * w.twist_gain, places=9)
        self.assertAlmostEqual(own[1], w.own_knobs()["pelvis_list"], places=9)
        for given, stride in (({"pelvis_twist": 8.0, "pelvis_list": 6.0}, 1.0),
                              ({"pelvis_twist": 2.0, "pelvis_list": 0.0}, 1.0),
                              ({"pelvis_twist": 8.0, "pelvis_list": 6.0, "stride": 1.4}, 1.4)):
            r = w.evaluate(dict(given, balance=0.0))
            twist, drop = w.pelvis_fit(r.worlds)
            self.assertAlmostEqual(twist, given["pelvis_twist"] * w.twist_gain * stride, delta=0.2, msg=given)
            self.assertAlmostEqual(drop, given["pelvis_list"], delta=0.2, msg=given)

    def test_the_twist_turns_the_forward_legs_hip_forward_and_the_standing_hip_up(self):
        w = walk()
        r = w.evaluate({"pelvis_twist": 12.0, "pelvis_list": 8.0, "balance": 0.0})
        base = w.evaluate(dict(w.own_knobs(), balance=0.0))
        d, d0 = (positions(x, "thigh_l", w) - positions(x, "thigh_r", w) for x in (r, base))
        split = w.split_shape
        f = int(np.argmax(split))                              # the left foot furthest ahead
        self.assertGreater(float(np.dot(d[f] - d0[f], w.fwd)), 0.5)
        f = int(round(w.feet["l"].on + wm.LIST_PEAK * 24)) % 24   # the left hip's highest
        self.assertGreater(float(np.dot(d[f] - d0[f], w.up)), 0.5)

    def test_the_chest_keeps_its_turn(self):
        """The lumbar spine takes the extra back: the top of the spine turns in the world as at the walk's own."""
        w = walk()
        own = w.evaluate(dict(w.own_knobs(), balance=0.0))
        more = w.evaluate({"pelvis_twist": 12.0, "pelvis_list": 9.0, "balance": 0.0, "arm_drag": 0.0,
                           "torso_drag": 0.0, "head_drag": 0.0,
                           "chest_twist": w.own_chest_twist, "chest_sway": w.own_chest_sway})
        chest = w.index["spine_02"]
        self.assertLess(float(np.abs(more.worlds[chest, :, :3, :3] - own.worlds[chest, :, :3, :3]).max()), 1e-9)
        pelvis = w.index["pelvis"]
        self.assertGreater(float(np.abs(more.worlds[pelvis, :, :3, :3] - own.worlds[pelvis, :, :3, :3]).max()), 0.05)

    def test_pelvis_motion_zero_holds_it_still(self):
        w = walk()
        pel = w.evaluate({"pelvis_rot": 0.0})
        rot = pel.worlds[w.index["pelvis"], :, :3, :3]
        self.assertLess(float(np.abs(rot - rot[0]).max()), 1e-9)

    def test_the_status_says_the_degrees(self):
        w = walk()
        text = wm.describe(w.evaluate({"pelvis_twist": 6.0, "pelvis_list": 3.0}))
        self.assertIn("pelvis twists +-%.1f deg, the hips +-3.0" % (6.0 * w.twist_gain), text)


def contact_frames(r, w, side):
    """The result's frames whose ankle stands within the model's contact tolerance of its own lowest."""
    h = positions(r, "foot_" + side, w)[:r.frames] @ w.up
    return h <= h.min() + wm.CONTACT_TOL


def cyclic_runs(mask):
    """The lengths of the runs of True in a cyclic mask (a run across the seam counts once, whole)."""
    mask = list(mask)
    if all(mask):
        return [len(mask)]
    start = mask.index(False)
    runs, run = [], 0
    for value in mask[start:] + mask[:start] + [False]:
        if value:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    return runs


class FootPlacementTests(unittest.TestCase):
    """Foot placement: a planted foot never slides, and one foot is always on the ground."""

    def test_the_knob_and_the_walks_own(self):
        self.assertEqual((wm.DEFAULTS["foot_placement"], wm.RANGES["foot_placement"]), (1.0, (0.0, 1.0)))
        self.assertEqual(walk().own_knobs()["foot_placement"], 0.0)

    def test_the_clock_is_the_walks_without_placement(self):
        w = walk(stance=0.4, lift=40.0)
        for side in "lr":
            for tau in (0.0, 3.25, 11.5, 23.9, 30.0, -4.0):
                self.assertAlmostEqual(w.foot_time(side, tau, 0.0), tau, places=9)

    def test_the_clock_lands_on_the_new_contacts_and_never_runs_back(self):
        w = walk(stance=0.4, lift=40.0)
        for side in "lr":
            (hs, to), = w.contact[side]                # one step of each foot a cycle: one contact
            (hs2, to2), = w.placed_contact(side, 1.0)
            self.assertLessEqual(hs2, hs)            # the trailing foot stays longer; the strike keeps its time
            self.assertGreater(to2, to)
            self.assertAlmostEqual(w.foot_time(side, hs2, 1.0), hs, places=9)
            self.assertAlmostEqual(w.foot_time(side, to2, 1.0), to, places=9)
            times = [w.foot_time(side, i / 16.0, 1.0) for i in range(-24 * 16, 48 * 16)]
            self.assertTrue(all(b > a for a, b in zip(times, times[1:])), side)
            self.assertAlmostEqual(w.foot_time(side, 7.3 + 24, 1.0), w.foot_time(side, 7.3, 1.0) + 24, places=9)

    def test_a_planted_foot_never_slides(self):
        """The walker's stance foot slides 6 cm forward: placed, it stands still for its whole contact."""
        w = walk(slip=6.0)
        on = w.evaluate({"balance": 0.0})
        off = w.evaluate({"foot_placement": 0.0, "balance": 0.0})
        unwrapped = lambda r, side, frames: np.array([positions(r, "foot_" + side, w)[f % 24] + (f // 24) * w.travel
                                                      for f in frames])
        for side in "lr":
            foot = w.feet[side]
            stance = [foot.on + i for i in range(foot.length + 1)]
            self.assertLess(float(np.ptp(unwrapped(on, side, stance), axis=0).max()), 1e-6, side)
            self.assertGreater(float(np.ptp(unwrapped(off, side, stance), axis=0).max()), 4.0, side)

    def test_one_foot_is_always_on_the_ground(self):
        """The walker leaves the ground with both feet between its steps; placed, both are down at every step
        (at least a frame of the new cycle - as long as the trailing leg reaches) and never both up."""
        w = walk(stance=0.4, lift=40.0)
        for knob, both_up in ((0.0, True), (1.0, False)):
            r = w.evaluate({"foot_placement": knob, "tempo": 96, "balance": 0.0})
            down = {s: contact_frames(r, w, s) for s in "lr"}
            neither = int(np.sum(~down["l"] & ~down["r"]))
            self.assertEqual(neither > 0, both_up, knob)
        runs = cyclic_runs(down["l"] & down["r"])
        self.assertEqual(len(runs), 2)                 # one at each step
        self.assertGreaterEqual(min(runs), 1)
        for side in "lr":
            self.assertGreaterEqual(r.info["placement"]["double"][side], 1.0 - 1e-6)

    def test_a_short_step_stays_down_the_whole_double_support(self):
        """Where the trailing leg reaches, both feet are down DOUBLE_SUPPORT of the cycle at every step."""
        w = walk(stance=0.4, lift=40.0)
        r = w.evaluate({"stride": 0.6, "tempo": 96, "balance": 0.0})
        for side in "lr":
            self.assertGreater(r.info["placement"]["double"][side], wm.DOUBLE_SUPPORT * 96 - 1e-6)
        down = {s: contact_frames(r, w, s) for s in "lr"}
        self.assertGreaterEqual(min(cyclic_runs(down["l"] & down["r"])), wm.DOUBLE_SUPPORT * 96 - 1)

    def test_the_status_says_the_feet_are_planted(self):
        w = walk(stance=0.4, lift=40.0)
        self.assertIn("feet planted", wm.describe(w.evaluate({"balance": 0.0})))
        self.assertNotIn("feet planted", wm.describe(w.evaluate({"foot_placement": 0.0, "balance": 0.0})))


class FootOverlapTests(unittest.TestCase):
    """Foot lag and Foot flex: the swinging foot in its calf, late and stronger; the ground untouched."""

    def test_foot_lag_delays_the_swinging_foot_in_its_calf(self):
        w, c = walk(), clip()
        r = w.evaluate(dict(w.own_knobs(), foot_lag=2.0))
        fo, ca = w.index["foot_l"], w.index["calf_l"]
        local = r.worlds[fo, 19, :3, :3] @ r.worlds[ca, 19, :3, :3].T
        late = c.worlds[fo, 17, :3, :3] @ c.worlds[ca, 17, :3, :3].T
        self.assertLess(angle(local @ late.T), 1e-6)
        left = w.feet["l"]
        stance = [left.on + i for i in range(left.length + 1)]
        self.assertLess(float(np.abs(r.worlds[fo, stance] - c.worlds[fo, stance]).max()), 1e-9)

    def test_foot_flex_scales_its_turn_in_the_calf(self):
        w, c = walk(), clip()
        r = w.evaluate(dict(w.own_knobs(), foot_flex=2.0))
        fo, ca = w.index["foot_l"], w.index["calf_l"]
        mean = w.lmean[fo]
        local = r.worlds[fo, 19, :3, :3] @ r.worlds[ca, 19, :3, :3].T
        source = c.worlds[fo, 19, :3, :3] @ c.worlds[ca, 19, :3, :3].T
        self.assertGreater(angle(source @ mean.T), 3.0)
        self.assertAlmostEqual(angle(local @ mean.T), 2.0 * angle(source @ mean.T), places=6)

    def test_the_defaults_leave_the_foot_on_its_walk(self):
        w, c = walk(), clip()
        r = w.evaluate(w.own_knobs())
        fo = w.index["foot_l"]
        self.assertLess(float(np.abs(r.worlds[fo] - c.worlds[fo]).max()), 1e-6)


def a_pose(w):
    """A hunch for the synthetic walker, as walkpose.prepare hands it to the model."""
    j = w.index
    return {"spine": {j["spine_01"]: rot_x(35) @ w.lmean[j["spine_01"]],
                      j["spine_02"]: rot_x(20) @ rot_y(10) @ w.lmean[j["spine_02"]],
                      j["neck_01"]: rot_x(-15) @ w.lmean[j["neck_01"]]},
            "head": rot_x(-25) @ w.wmean[j["head"]],
            "pelvis": rot_x(15) @ rot_z(5) @ w.wmean[j["pelvis"]],
            "height": 70.0,
            "knee_turn": {"l": math.radians(30.0), "r": math.radians(-20.0)}}


def knee_heading(r, w, side, f):
    hip, knee, ankle = (positions(r, b + "_" + side, w)[f] for b in ("thigh", "calf", "foot"))
    e = (ankle - hip) / np.linalg.norm(ankle - hip)
    b = (knee - hip) - np.dot(knee - hip, e) * e
    return math.degrees(math.atan2(np.dot(b, w.side), np.dot(b, w.fwd)))


class PoseTests(unittest.TestCase):

    def test_pose_zero_is_the_walk(self):
        w = walk()
        self.assertLess(float(np.abs(w.evaluate({"pose": 0.0}, a_pose(w)).worlds - w.evaluate().worlds).max()), 1e-12)
        self.assertLess(float(np.abs(w.evaluate({"pose": 1.0}).worlds - w.evaluate().worlds).max()), 1e-12)

    def test_with_the_motion_off_the_body_stands_in_the_pose(self):
        w = walk()
        pose = a_pose(w)
        r = w.evaluate({"pose": 1.0, "exaggeration": 0.0, "torso_drag": 0.0, "head_drag": 0.0}, pose)
        for j, want in pose["spine"].items():
            name = w.names[j]
            for f in (0, 7, 18):
                self.assertLess(angle(local_rot(r, name, w, f) @ want.T), 1e-6, name)
        for f in (0, 11):
            self.assertLess(angle(rotations(r, "head", w)[f] @ pose["head"].T), 1e-6)
            self.assertLess(angle(rotations(r, "pelvis", w)[f] @ pose["pelvis"].T), 1e-6)
        height = positions(r, "pelvis", w)[:, 1] + np.array(r.info["drop"])
        self.assertTrue(np.allclose(height, 70.0, atol=1e-6))

    def test_half_a_pose_is_half_way(self):
        w = walk()
        pose = a_pose(w)
        r = w.evaluate({"pose": 0.5, "exaggeration": 0.0, "torso_drag": 0.0, "head_drag": 0.0}, pose)
        j = w.index["spine_01"]
        self.assertAlmostEqual(angle(local_rot(r, "spine_01", w, 4) @ w.lmean[j].T), 17.5, places=6)
        height = positions(r, "pelvis", w)[:, 1] + np.array(r.info["drop"])
        self.assertTrue(np.allclose(height, 0.5 * (70.0 + w.pelvis_mean[2] + w.origin[1]), atol=1e-6))

    def test_the_knees_turn_by_the_pose(self):
        """The turn alone (Balance 0: Balance carries the hunched pelvis back, tilting the legs' lines); with
        Knee <-> foot 1 the foot turns to the knee, so the knee keeps the pose's whole turn."""
        w = walk()
        pose = a_pose(w)
        plain = w.evaluate({"balance": 0.0})
        posed = w.evaluate({"pose": 1.0, "balance": 0.0, "knee_foot": 1.0, "leg_match": 0.0}, pose)
        for side, turn in (("l", 30.0), ("r", -20.0)):
            f = int(round(w.feet[side].mid)) % 24
            self.assertAlmostEqual(knee_heading(posed, w, side, f) - knee_heading(plain, w, side, f), turn, delta=1.0)
            hip, knee = positions(posed, "thigh_" + side, w), positions(posed, "calf_" + side, w)
            self.assertLess(float(np.abs(np.linalg.norm(knee - hip, axis=1) - L1).max()), 1e-9)

    def test_a_knee_and_its_foot_meet_half_way(self):
        """A knee turned 30 deg in against an unturned foot: 15 deg of it stays in the shin, the rest is shared -
        the knee 22.5, the foot 7.5 (the right: -20 -> -17.5 and -2.5)."""
        w, c = walk(), clip()
        plain, posed = w.evaluate({"balance": 0.0}), w.evaluate({"pose": 1.0, "balance": 0.0, "leg_match": 0.0}, a_pose(w))
        for side, knee_turn, foot_turn in (("l", 22.5, 7.5), ("r", -17.5, -2.5)):
            f = int(round(w.feet[side].mid)) % 24
            self.assertAlmostEqual(knee_heading(posed, w, side, f) - knee_heading(plain, w, side, f), knee_turn,
                                   delta=1.0)
            j = w.index["foot_" + side]
            self.assertTrue(np.allclose(c.worlds[j, f, :3, :3].T @ posed.worlds[j, f, :3, :3], rot_y(foot_turn),
                                        atol=1e-9), side)

    def test_leg_turn_scales_the_poses_turns(self):
        """Leg turn x the pose's knee and toe turns, before they meet: 0 is the walk's own knees and feet."""
        w, c = walk(), clip()
        pose = {"knee_turn": {"l": math.radians(10.0), "r": math.radians(-8.0)},
                "toe": {"l": math.radians(6.0), "r": math.radians(-4.0)}}
        plain = w.evaluate({"balance": 0.0})
        for turn in (0.0, 0.5):
            r = w.evaluate({"pose": 1.0, "balance": 0.0, "leg_turn": turn, "leg_match": 0.0}, pose)
            for side, knee_deg, toe_deg in (("l", 10.0, 6.0), ("r", -8.0, -4.0)):
                f = int(round(w.feet[side].mid)) % 24
                self.assertAlmostEqual(knee_heading(r, w, side, f) - knee_heading(plain, w, side, f), turn * knee_deg,
                                       delta=0.5)
                j = w.index["foot_" + side]
                self.assertTrue(np.allclose(c.worlds[j, f, :3, :3].T @ r.worlds[j, f, :3, :3], rot_y(turn * toe_deg),
                                            atol=1e-9))

    def test_a_foot_on_the_ground_never_hangs_off_its_shin(self):
        """Only a foot in the air follows its shin: on the ground (heel or toe down) it keeps its planted turn,
        so Balance moving the hips never slides a planted toe."""
        w = walk()
        for side in "lr":
            for f in range(24):
                if w.down(side, float(f)):
                    self.assertEqual(w.swing_at(side, float(f)), 0.0, (side, f))
            self.assertTrue(any(w.swing_at(side, float(f)) == 1.0 for f in range(24)), side)
        pose = a_pose(w)
        on, off = w.evaluate({"pose": 1.0, "stance": 2.0}, pose), w.evaluate({"pose": 1.0, "stance": 2.0, "balance": 0.0}, pose)
        self.assertGreater(on.info["balance"]["carry"], 1.0)
        for side in "lr":
            down = [f for f in range(24) if w.down(side, float(f))]
            for name in ("foot_" + side, "ball_" + side):
                self.assertLess(float(np.abs(positions(on, name, w)[down] - positions(off, name, w)[down]).max()), 1e-9)

    def test_the_swinging_foot_follows_its_shin(self):
        """Mid-swing the foot hangs in its calf as the walk's does, whatever turned the knee."""
        w, c = walk(), clip()
        pose = {"knee_turn": {"l": math.radians(30.0), "r": 0.0}}
        r = w.evaluate({"pose": 1.0, "knee_foot": 1.0, "balance": 0.0}, pose)
        fo, ca = w.index["foot_l"], w.index["calf_l"]
        mid_swing = 19          # stance 0..14, the swing 14..24: half way in time
        local = r.worlds[fo, mid_swing, :3, :3] @ r.worlds[ca, mid_swing, :3, :3].T
        source = c.worlds[fo, mid_swing, :3, :3] @ c.worlds[ca, mid_swing, :3, :3].T
        self.assertLess(angle(local @ source.T), 1e-6)
        world = r.worlds[fo, mid_swing, :3, :3] @ c.worlds[fo, mid_swing, :3, :3].T
        self.assertGreater(angle(world), 5.0)     # it turned with the shin

    def test_a_bent_body_turns_about_the_walks_world_axes(self):
        """The hunch tilts the pelvis and bends the spine; their walk turns stay about the walk's world axes, so
        the chest keeps counter-turning against the pelvis about the vertical: from the first frame each turns
        in the world exactly as the walk's does."""
        w = walk()
        w.chest_shape = None            # the chest's turn left alone (ChestTests bring it to Chest twist)
        base = dict(w.own_knobs(), balance=0.0)
        plain, posed = w.evaluate(base), w.evaluate(dict(base, pose=1.0), a_pose(w))
        for name in ("pelvis", "spine_01", "spine_02"):
            a, b = rotations(posed, name, w), rotations(plain, name, w)
            for f in (5, 11, 17):
                self.assertLess(float(np.abs(a[0].T @ a[f] - b[0].T @ b[f]).max()), 1e-9, (name, f))

    def test_the_feet_stay_planted_under_a_pose(self):
        w = walk()
        r = w.evaluate({"pose": 1.0}, a_pose(w))
        left = w.feet["l"]
        foot = positions(r, "foot_l", w)[[left.on + i for i in range(left.length + 1)]]
        self.assertLess(float(np.ptp(foot, axis=0).max()), 1e-6)
        moved = r.worlds[:, -1, 3, :3] - r.worlds[:, 0, 3, :3]
        self.assertLess(float(np.abs(moved - [0.0, 0.0, 120.0]).max()), 1e-6)


def turned_pose(w, yaw=30.0):
    """A pose standing side-on: the whole body turned `yaw` deg about up (the pelvis, the spine as the walk's
    mean on it), as prepare hands it."""
    j = w.index
    return {"pelvis": w.wmean[j["pelvis"]] @ rot_y(yaw),
            "spine": dict((j[n], w.lmean[j[n]]) for n in ("spine_01", "spine_02", "neck_01")),
            "hips_yaw": math.radians(yaw)}


class LegMatchTests(unittest.TestCase):
    """Leg match (2026-10-14): a pose's stance read against its own hips and faded by the gait - the hips face
    the walk, the shoulders keep the pose's facing, the knees and toes the symmetric splay x keep."""

    def test_the_gait_keeps_less_of_a_stance_the_faster_it_goes(self):
        w = walk()
        v = 120.0 / (24 / 30.0)
        self.assertAlmostEqual(w.leg_length, L1 + L2, places=6)
        keep, froude = w.gait_keep(wm.knobs(), 24)
        self.assertAlmostEqual(froude, v * v / (981.0 * (L1 + L2)), places=9)
        self.assertAlmostEqual(keep, 1.0 / (1.0 + froude), places=12)
        self.assertAlmostEqual(w.gait_keep(wm.knobs(stride=1.5), 24)[1], 2.25 * froude, places=9)
        self.assertAlmostEqual(w.gait_keep(wm.knobs(), 12)[1], 4.0 * froude, places=9)

    def test_the_hips_face_the_walk_and_the_shoulders_keep_the_pose(self):
        w = walk()
        pel, top = w.index["pelvis"], w.index["spine_02"]
        still = {"pose": 1.0, "exaggeration": 0.0, "balance": 0.0}
        matched = w.evaluate(dict(still, leg_match=1.0), turned_pose(w))
        raw = w.evaluate(dict(still, leg_match=0.0), turned_pose(w))
        chest = w.lmean[top] @ w.lmean[w.index["spine_01"]] @ w.wmean[pel] @ rot_y(30.0)
        for f in (0, 9, 17):
            self.assertLess(angle(rotations(matched, "pelvis", w)[f] @ w.wmean[pel].T), 1e-6)
            self.assertLess(angle(rotations(matched, "spine_02", w)[f] @ chest.T), 1e-6)
            self.assertLess(angle(rotations(raw, "pelvis", w)[f] @ (w.wmean[pel] @ rot_y(30.0)).T), 1e-6)

    def test_the_knees_and_toes_keep_the_symmetric_splay_faded(self):
        """A stance 20 deg side-on, its knees 15 deg out against its own hips (the right more: one foot back) -
        the left read 35 against the walk, the right -10: matched, each side the mean splay over the walk's own
        x keep, outward."""
        w = walk()
        knees, toes = w.knee_headings(), w.toe_headings()
        d = math.radians(20.0)
        out = {"l": math.radians(5.0), "r": math.radians(25.0)}      # outward against the pose's hips
        sign = {"l": 1.0, "r": -1.0}
        pose = {"hips_yaw": d,
                "knee_turn": dict((s, d + sign[s] * out[s] - knees[s]) for s in "lr"),
                "toe": dict((s, d + sign[s] * out[s] - toes[s]) for s in "lr"), "width": 12.0}
        keep = 0.4
        got = w.matched_pose(pose, 1.0, keep)
        for key, own in (("knee_turn", knees), ("toe", toes)):
            splay = math.radians(15.0) - 0.5 * (own["l"] - own["r"])
            for s in "lr":
                self.assertAlmostEqual(got[key][s], sign[s] * keep * splay, places=12, msg=(key, s))
        self.assertAlmostEqual(got["width"], 12.0 * keep, places=12)
        half = w.matched_pose(pose, 0.5, keep)
        self.assertAlmostEqual(half["knee_turn"]["l"], 0.5 * (pose["knee_turn"]["l"] + got["knee_turn"]["l"]), places=12)
        self.assertIs(w.matched_pose(pose, 0.0, keep), pose)

    def test_leg_match_zero_is_the_pose_as_it_was_read(self):
        w = walk()
        pose = dict(a_pose(w), hips_yaw=math.radians(25.0), width=10.0,
                    toe={"l": math.radians(12.0), "r": math.radians(-30.0)})
        legacy = dict(pose)
        legacy.pop("hips_yaw")
        a = w.evaluate({"pose": 1.0, "leg_match": 0.0}, pose).worlds
        b = w.evaluate({"pose": 1.0, "leg_match": 0.0}, legacy).worlds
        self.assertLess(float(np.abs(a - b).max()), 1e-12)

    def test_a_fast_gait_runs_on_its_own_legs(self):
        """The same splayed stance on the walker sped up four times: matched, the knees turn a quarter as far
        (Froude x16 against x1) - the leg swings in the line of travel."""
        w = walk()
        pose = {"hips_yaw": 0.0, "knee_turn": dict((s, s == "l" and math.radians(30.0) or math.radians(-30.0))
                                                   for s in "lr")}
        slow = w.evaluate({"pose": 1.0, "balance": 0.0, "knee_foot": 1.0}, pose)
        fast = w.evaluate({"pose": 1.0, "balance": 0.0, "knee_foot": 1.0, "tempo": 6.0}, pose)
        self.assertGreater(slow.info["leg_match"]["keep"], 3.0 * fast.info["leg_match"]["keep"])
        self.assertTrue(slow.info["leg_match"]["on"])


class GaitLeanTests(unittest.TestCase):
    """Gait lean (2026-10-14, the stop builder's idea): a pose's torso replaces the walk's mean, and the walk's
    own forward lean over its rest (a run leans into it) went with it - it is put back on the pose's bones, a
    forward lean in the room the pose leaves to horizontal."""

    def leaned(self, w):
        pose = a_pose(w)
        j = w.index
        pose["gait_lean"] = {j["pelvis"]: math.radians(10.0), j["spine_01"]: math.radians(14.0),
                             j["spine_02"]: math.radians(20.0), j["neck_01"]: math.radians(-6.0),
                             j["head"]: math.radians(8.0)}
        pose["lean_room"] = 0.5
        return pose

    def test_each_bone_takes_its_lean_on_the_pose_forward_in_the_room(self):
        w = walk()
        pose = self.leaned(w)
        still = {"pose": 1.0, "exaggeration": 0.0, "balance": 0.0}
        r = w.evaluate(dict(still, gait_lean=1.0), pose)
        plain = w.evaluate(dict(still, gait_lean=0.0), pose)
        for name, deg in (("pelvis", 5.0), ("spine_01", 7.0), ("spine_02", 10.0), ("neck_01", -6.0)):
            for f in (0, 13):
                want = rotations(plain, name, w)[f] @ wm.exp_rot(w.side * math.radians(deg))
                self.assertLess(angle(rotations(r, name, w)[f] @ want.T), 1e-6, (name, f))
        want = rotations(plain, "head", w)[0] @ wm.exp_rot(w.side * math.radians(4.0))
        self.assertLess(angle(rotations(r, "head", w)[0] @ want.T), 1e-6)

    def test_zero_or_no_lean_is_the_pose_as_it_stood(self):
        w = walk()
        a = w.evaluate({"pose": 1.0, "gait_lean": 0.0}, self.leaned(w)).worlds
        b = w.evaluate({"pose": 1.0}, a_pose(w)).worlds
        self.assertLess(float(np.abs(a - b).max()), 1e-12)
        self.assertEqual(wm.DEFAULTS["gait_lean"], 1.0)


def a_grip(w):
    """Arms held: both upper arms forward and the forearms bent in, the walker's own fingers."""
    j = w.index
    arms = {}
    for side, sign in (("l", 1.0), ("r", -1.0)):
        arms[j["upperarm_" + side]] = rot_y(sign * 60.0) @ w.lmean[j["upperarm_" + side]]
        arms[j["lowerarm_" + side]] = rot_z(sign * -70.0) @ w.lmean[j["lowerarm_" + side]]
    return {"arms": arms, "grip": True}


class PosePartsTests(unittest.TestCase):

    def test_held_arms_keep_the_hands_together(self):
        """Arms in the pose at 1, holding: the arms ride the chest, no swing - the two hands keep one relation
        (with Arm drag too: the held thing trails as one, ArmTests)."""
        w = walk()
        r = w.evaluate({"pose": 1.0, "arm_drag": 0.0}, a_grip(w))
        hands = [r.worlds[w.index["hand_l"], f] @ np.linalg.inv(r.worlds[w.index["hand_r"], f]) for f in range(25)]
        self.assertLess(float(np.abs(np.array(hands) - hands[0]).max()), 1e-9)
        j = w.index["lowerarm_l"]
        self.assertLess(angle(local_rot(r, "lowerarm_l", w, 7) @ a_grip(w)["arms"][j].T), 1e-9)
        plain = w.evaluate()
        loose = [plain.worlds[w.index["hand_l"], f] @ np.linalg.inv(plain.worlds[w.index["hand_r"], f]) for f in range(25)]
        self.assertGreater(float(np.abs(np.array(loose) - loose[0]).max()), 1.0)

    def test_half_held_arms_swing_half(self):
        w = walk()
        r = w.evaluate({"pose": 0.5, "exaggeration": 1.0, "arm_drag": 0.0}, a_grip(w))
        j = w.index["hand_l"]
        mean = w.lmean[j]
        swing = max(angle(local_rot(r, "hand_l", w, f) @ mean.T) for f in range(24))
        source = max(angle(local_rot(w.evaluate({"arm_drag": 0.0}), "hand_l", w, f) @ mean.T) for f in range(24))
        self.assertAlmostEqual(swing, 0.5 * source, places=6)

    def test_the_feet_set_wider_and_turn_out(self):
        """Knee <-> foot 0: the knees turn to the feet, the feet keep the pose's turn on the ground."""
        w, c = walk(), clip()
        pose = {"width": 12.0, "toe": {"l": math.radians(20.0), "r": math.radians(-30.0)}}
        r = w.evaluate({"pose": 1.0, "knee_foot": 0.0, "foot_placement": 0.0, "leg_match": 0.0}, pose)   # the walk's own feet
        ml, mr = int(round(w.feet["l"].mid)) % 24, int(round(w.feet["r"].mid)) % 24
        gap = lambda m, a, b: float(np.dot(m[w.index["foot_l"], a, 3, :3] - m[w.index["foot_r"], b, 3, :3], w.side))
        self.assertAlmostEqual(gap(r.worlds, ml, mr) - gap(c.worlds, ml, mr), 12.0, places=6)
        narrow = w.evaluate({"pose": 1.0, "stance": 0.5, "foot_placement": 0.0, "leg_match": 0.0}, pose)
        self.assertAlmostEqual(gap(narrow.worlds, ml, mr), 0.5 * (gap(c.worlds, ml, mr) + 12.0), places=6)
        for side, deg in (("l", 20.0), ("r", -30.0)):
            j = w.index["foot_" + side]
            foot = w.feet[side]
            for f in [(foot.on + i) % 24 for i in range(0, foot.length + 1, 4)]:
                turn = c.worlds[j, f, :3, :3].T @ r.worlds[j, f, :3, :3]
                self.assertTrue(np.allclose(turn, rot_y(deg), atol=1e-9), (side, f))
        left = w.feet["l"]
        foot = positions(r, "ball_l", w)[[left.on + i for i in range(left.length + 1)]]
        self.assertLess(float(np.ptp(foot, axis=0).max()), 1e-9)


class MassTests(unittest.TestCase):
    """de Leva's segment table as one weight a joint: the centre of mass is a weighted sum of joints."""

    def test_the_weights_sum_to_one_and_helpers_weigh_nothing(self):
        w = walk()
        self.assertEqual(w.balance_note, "")
        self.assertAlmostEqual(float(w.mass.sum()), 1.0, places=12)
        self.assertTrue(np.all(w.mass >= 0.0))
        for name in ("root", "ik_foot_root", "ik_foot_l", "camera_root", "thigh_twist_01_l"):
            self.assertEqual(w.mass[w.index[name]], 0.0, name)

    def test_the_legs_weigh_de_levas_share(self):
        w = walk()
        legs = sum(w.mass[w.index["%s_%s" % (b, s)]] for s in "lr" for b in ("thigh", "calf", "foot", "ball"))
        self.assertAlmostEqual(legs, 2 * (14.16 + 4.33 + 1.37) / 100.0, places=9)
        self.assertAlmostEqual(w.mass[w.index["thigh_l"]], 0.1416 * (1 - 0.4095), places=9)
        self.assertAlmostEqual(w.mass[w.index["ball_r"]], 0.0137 * 0.4415, places=9)
        self.assertAlmostEqual(w.mass[w.index["index_01_l"]], 0.0061 * 0.5, places=9)   # the hand's fingers

    def test_the_trunk_spreads_along_the_chain_and_the_head_sits_on_its_joint(self):
        w = walk()
        trunk = sum(w.mass[w.index[n]] for n in ("pelvis", "spine_01", "spine_02", "neck_01"))
        self.assertAlmostEqual(trunk, (11.17 + 16.33 + 15.96) / 100.0, places=9)
        self.assertAlmostEqual(w.mass[w.index["head"]], 0.0694, places=9)

    def test_the_centre_of_mass_is_the_weighted_joints(self):
        w, c = walk(), clip()
        com = w.com(c.worlds)
        self.assertEqual(com.shape, (25, 3))
        manual = sum(w.mass[j] * c.worlds[j, 6, 3, :3] for j in range(len(w.names)))
        self.assertTrue(np.allclose(com[6], manual, atol=1e-12))
        self.assertTrue(np.allclose(w.com(c.worlds[:, 6]), manual, atol=1e-12))
        self.assertGreater(com[6, 1], c.worlds[w.index["thigh_l"], 6, 3, 1])

    def test_a_walker_without_a_neck_keeps_its_walk_and_says_why(self):
        c = clip()
        names = ["neckbone" if n == "neck_01" else n for n in c.names]
        w = wm.analyse(wm.Clip(names, c.parents, c.worlds, 30.0, (0, 1, 0), "no neck"))
        self.assertIn("neck_01", w.balance_note)
        r, r0 = w.evaluate({"stance": 1.75}), w.evaluate({"stance": 1.75, "balance": 0.0})
        self.assertLess(float(np.abs(r.worlds - r0.worlds).max()), 1e-12)
        self.assertIn("neck_01", wm.describe(r))


class PendulumTests(unittest.TestCase):
    """x'' = (g / h)(x - p) over one cycle: each harmonic of the pressure followed by w^2 / (w^2 + w_k^2)."""

    def test_a_still_pressure_holds_the_centre_over_it(self):
        cop = np.tile([3.0, -2.0], (20, 1))
        self.assertTrue(np.allclose(wm.pendulum(cop, 1.0, 90.0), cop, atol=1e-12))

    def test_a_harmonic_follows_by_its_gain_in_phase(self):
        frames, seconds, height = 30, 1.2, 95.0
        t = np.arange(frames) / float(frames)
        omega2 = wm.GRAVITY / height
        for k in (1, 2, 3):
            cop = np.stack([5.0 * np.cos(2 * math.pi * k * t), 3.0 * np.sin(2 * math.pi * k * t)], -1)
            gain = omega2 / (omega2 + (2 * math.pi * k / seconds) ** 2)
            self.assertTrue(np.allclose(wm.pendulum(cop, seconds, height), gain * cop, atol=1e-9), k)

    def test_lower_and_slower_follow_more(self):
        t = np.arange(30) / 30.0
        cop = np.stack([np.zeros(30), 6.0 * np.sin(2 * math.pi * t)], -1)
        amp = lambda seconds, height: float(np.ptp(wm.pendulum(cop, seconds, height)[:, 1]))
        self.assertGreater(amp(1.0, 60.0), amp(1.0, 95.0))
        self.assertGreater(amp(1.5, 95.0), amp(1.0, 95.0))
        self.assertLess(amp(1.0, 95.0), 12.0)


def com_dev(r, w, stride=1.0):
    """The result's centre of mass against its own travel line, (fwd, side, up) a frame (the seam dropped)."""
    n = r.frames
    line = w.origin + np.outer(np.arange(n) / float(n), w.travel * stride)
    return (w.com(r.worlds)[:n] - line) @ w.basis.T


class BalanceTests(unittest.TestCase):
    """The pendulum on top of the style: what the changes bring, nothing at the defaults."""

    def test_the_source_reads_its_own_pendulum(self):
        w = walk()
        self.assertEqual(w.cop_dev.shape, (24, 2))
        self.assertTrue(all(wm.FOLLOW_RANGE[0] <= f <= wm.FOLLOW_RANGE[1] for f in w.follow))
        f = int(round(w.feet["l"].mid)) % 24     # mid-stance on the left foot: the pressure under it (+side)
        self.assertGreater(w.cop_dev[f, 1], 5.0)

    def test_balance_changes_nothing_at_the_walks_own_knobs(self):
        w = walk()
        r1, r0 = w.evaluate(dict(w.own_knobs(), balance=1.0)), w.evaluate(dict(w.own_knobs(), balance=0.0))
        self.assertLess(float(np.abs(r1.worlds - r0.worlds).max()), 1e-6)
        self.assertLess(r1.info["balance"]["carry"], 1e-6)

    def test_wider_feet_sway_the_centre_more_toward_the_standing_foot(self):
        w = walk()
        wide1, wide0 = w.evaluate({"stance": 2.0}), w.evaluate({"stance": 2.0, "balance": 0.0})
        d1, d0 = com_dev(wide1, w), com_dev(wide0, w)
        self.assertGreater(float(np.ptp(d1[:, 1])), float(np.ptp(d0[:, 1])) + 1.0)
        for side, sign in (("l", 1.0), ("r", -1.0)):
            f = int(round(w.feet[side].mid)) % 24
            self.assertGreater(sign * (d1[f, 1] - d0[f, 1]), 0.5, side)
        self.assertLess(wide1.info["balance"]["residual"], 0.05)
        self.assertGreater(wide1.info["balance"]["carry"], 0.5)
        self.assertIn("balance", wm.describe(wide1))

    def test_the_feet_stay_planted_and_the_loop_closes_under_balance(self):
        """The walker's own feet (Foot placement may roll a stance foot about its heel or ball: FootPlacementTests)."""
        w = walk()
        r = w.evaluate({"stance": 2.0, "stride": 1.3, "foot_placement": 0.0})
        for side in "lr":
            foot = w.feet[side]
            prints = positions(r, "foot_" + side, w)[[(foot.on + i) % 24 for i in range(foot.length + 1)
                                                      if foot.on + i < 24]]
            self.assertLess(float(np.ptp(prints, axis=0).max()), 1e-9, side)
            hip, knee = positions(r, "thigh_" + side, w), positions(r, "calf_" + side, w)
            self.assertLess(float(np.abs(np.linalg.norm(knee - hip, axis=1) - L1).max()), 1e-9)
        moved = r.worlds[:, -1, 3, :3] - r.worlds[:, 0, 3, :3]
        self.assertLess(float(np.abs(moved - [0.0, 0.0, 156.0]).max()), 1e-6)

    def test_slower_sways_more_faster_less(self):
        w = walk()
        for tempo, sign in ((36, 1.0), (16, -1.0)):
            r1, r0 = w.evaluate({"tempo": tempo}), w.evaluate({"tempo": tempo, "balance": 0.0})
            more = float(np.ptp(com_dev(r1, w)[:, 1])) - float(np.ptp(com_dev(r0, w)[:, 1]))
            self.assertGreater(sign * more, 0.2, tempo)
            self.assertLess(r1.info["balance"]["residual"], 0.05)

    def test_a_leaning_pose_keeps_the_centre_over_the_feet(self):
        """Over the walk's own CoM: the feet press where the walk's do (Knee <-> foot 0 - the knees turn to the
        feet, so no foot turns and the pressure stays; a turned foot moves it, and the CoM with it)."""
        w = walk()
        pose = a_pose(w)
        source = float(com_dev(w.evaluate(dict(w.own_knobs(), balance=0.0)), w)[:, 0].mean())
        leaned = w.evaluate({"pose": 1.0, "balance": 0.0, "knee_foot": 0.0}, pose)
        held = w.evaluate({"pose": 1.0, "knee_foot": 0.0}, pose)
        self.assertGreater(float(com_dev(leaned, w)[:, 0].mean()) - source, 2.0)
        self.assertLess(abs(float(com_dev(held, w)[:, 0].mean()) - source), 0.05)
        back = (positions(held, "pelvis", w) - positions(leaned, "pelvis", w))[:24] @ w.fwd
        self.assertLess(float(back.mean()), -2.0)

    def test_sway_zero_still_holds_the_pelvis_on_its_line(self):
        w = walk()
        side = positions(w.evaluate({"sway": 0.0, "stance": 1.75}), "pelvis", w)[:, 0]
        self.assertLess(float(np.ptp(side)), 0.05)

    def test_balance_zero_keeps_the_stride_guess(self):
        w, c = walk(), clip()
        r = w.evaluate({"stride": 1.5, "balance": 0.0})
        j = w.index["pelvis"]
        line = lambda s: w.origin + np.outer(np.arange(24) / 24.0, w.travel * s)
        new = (positions(r, "pelvis", w)[:24] - line(1.5)) @ w.fwd - w.pelvis_mean[0]
        src = (c.worlds[j, :24, 3, :3] - line(1.0)) @ w.fwd - w.pelvis_mean[0]
        self.assertTrue(np.allclose(new, 1.5 * src, atol=1e-9))
        self.assertEqual(r.info["balance"]["carry"], 0.0)

    def test_every_knob_sits_in_one_window_group(self):
        panel = load("panel")      # the card: Pose under the pose's dropdown, In place a chip, the rest in groups
        everything = dict(wm.DEFAULTS, **load("clean").DEFAULTS)       # the model's and the clean's
        grouped = ["pose"] + list(panel.CHECKS) + [name for _, _, names in panel.GROUPS for name in names]
        self.assertEqual(sorted(grouped), sorted(everything))
        self.assertEqual(len(grouped), len(set(grouped)))
        self.assertEqual(sorted(panel.LABELS), sorted(everything))

    def test_a_long_stride_balances_forward(self):
        w = walk()
        r = w.evaluate({"stride": 1.5})
        self.assertGreater(r.info["balance"]["carry"], 0.1)
        self.assertLess(r.info["balance"]["residual"], 0.05)

def skewed(degrees):
    """The synthetic walker turned `degrees` about up through its root's first place - every joint's place and
    turn but the root's own: it travels that far off its root's facing."""
    c = clip()
    w = c.worlds.copy()
    r = c.names.index("root")
    centre = w[r, 0, 3, :3].copy()
    turn = rot_y(degrees)
    keep = w[r, :, :3, :3].copy()
    w[:, :, 3, :3] = (w[:, :, 3, :3] - centre) @ turn + centre
    w[:, :, :3, :3] = w[:, :, :3, :3] @ turn
    w[r, :, :3, :3] = keep
    return wm.Clip(c.names, c.parents, w, fps=30.0, up=(0, 1, 0), name="skewed")


class RootTests(unittest.TestCase):

    def test_a_walk_travelling_off_its_roots_facing_is_turned_onto_it(self):
        """A cycle saved a few degrees askew drifts sideways on any skeleton (the target's root faces its own
        way, the travel is carried in the root's axes): it is turned onto the root's facing - exactly the
        straight walker again."""
        straight = walk()
        for degrees in (3.0, -7.0):
            w = wm.analyse(skewed(degrees))
            self.assertAlmostEqual(abs(w.turned), abs(degrees), places=6)
            self.assertTrue(np.allclose(w.travel, [0.0, 0.0, 120.0], atol=1e-9))
            self.assertIn("turned %.1f deg onto its root's facing" % w.turned, w.summary())
            a, b = w.evaluate(w.own_knobs()), straight.evaluate(straight.own_knobs())
            self.assertLess(float(np.abs(a.worlds - b.worlds).max()), 1e-6, degrees)
        self.assertEqual(straight.turned, 0.0)
        self.assertNotIn("turned", straight.summary())

    def test_a_strafe_is_left_as_it_is(self):
        w = wm.analyse(skewed(40.0))
        self.assertEqual(w.turned, 0.0)

    def test_the_root_runs_straight_and_root_sway_weaves_it_with_the_hips(self):
        w, c = walk(), clip()
        root = w.index["root"]
        straight = w.evaluate()
        side = straight.worlds[root, :, 3, 0]
        self.assertLess(float(np.ptp(side)), 1e-9)
        own = w.evaluate({"root_sway": 1.0})
        weave = own.worlds[root, :, 3, 0]
        self.assertGreater(float(np.ptp(weave)), 3.9)          # the walker's root sways +-2 with its pelvis
        pelvis = w.index["pelvis"]          # the root sway moves the root only
        self.assertLess(float(np.abs(own.worlds[pelvis] - straight.worlds[pelvis]).max()), 1e-9)


TWO = dict(P=48, travel=200.0, strides=2, spans=TWO_STEPS)


def still_point_slide(r, w, side):
    """The planted foot's slide, cm a frame: the slower of its heel and ball points along the ground over every
    frame it is planted (and the next)."""
    n, up = r.frames, w.up
    m = r.worlds
    heel = m[w.index["foot_" + side], :n + 1, 3, :3] + np.einsum("i,fij->fj", w.heel_loc[side],
                                                                 m[w.index["foot_" + side], :n + 1, :3, :3])
    ball = m[w.index["ball_" + side], :n + 1, 3, :3]
    flat = lambda v: v - np.outer(v @ up, up)
    speed = np.minimum(np.linalg.norm(flat(np.diff(heel, axis=0)), axis=1),
                       np.linalg.norm(flat(np.diff(ball, axis=0)), axis=1))
    planted = np.array(r.info["placement"]["planted"][side])
    held = planted & np.roll(planted, -1)
    return float(speed[held].max()) if held.any() else 0.0


class ManyStepsTests(unittest.TestCase):
    """A cycle holding two steps of each foot, a long stance and a short one (dw, 2026-10-13): every per-foot
    quantity is a list, one entry a step."""

    def test_every_step_of_each_foot_is_found(self):
        w = walk(**TWO)
        self.assertEqual(w.strides, 2)
        for side in "lr":
            self.assertEqual(len(w.steps[side]), 2, side)
            self.assertEqual(len(w.contact[side]), 2, side)
            self.assertEqual(len(w.air[side]), 2, side)
            for foot, (on, off) in zip(w.steps[side], TWO_STEPS[side]):
                self.assertLessEqual(abs((foot.on - on * 48 + 24) % 48 - 24), 1.5, (side, foot.on))
                # a stance's edge frames read a swing's speed (the speed is a central difference)
                self.assertLessEqual(abs(foot.length - (off - on) * 48), 3.0, (side, foot.length))
        self.assertEqual(w.feet["l"].length, max(f.length for f in w.steps["l"]))     # the longest
        self.assertIn("2 steps of each foot a cycle", w.summary())

    def test_its_own_knobs_give_it_back(self):
        w, c = walk(**TWO), clip(**TWO)
        r = w.evaluate(w.own_knobs())
        self.assertLess(float(np.abs(r.worlds - c.worlds).max()), 1e-4)

    def test_foot_placement_holds_every_stance(self):
        """Its feet slide 6 cm over every stance: placed, each foot stands still over both of its contacts (one
        step a cycle used to hold only the longest), and one foot is always on the ground."""
        w = walk(slip=6.0, **TWO)
        own = w.evaluate(dict(w.own_knobs(), balance=0.0))
        r = w.evaluate({"balance": 0.0})
        for side in "lr":
            self.assertGreater(still_point_slide(own, w, side), 0.15, side)
            self.assertLess(still_point_slide(r, w, side), 0.02, side)
            planted = np.array(r.info["placement"]["planted"][side])
            for hs, to in w.contact[side]:          # every contact planted
                mid = int(round(0.5 * (hs + to))) % r.frames
                self.assertTrue(planted[mid], (side, hs, to))
        both_moving = ~np.array(r.info["placement"]["planted"]["l"]) & ~np.array(r.info["placement"]["planted"]["r"])
        self.assertFalse(both_moving.any())

    def test_a_step_not_a_cycle(self):
        """The step's length is the travel over two steps a stride, the hip drop and the chest turn once a
        stride: the standing hip highest LIST_PEAK of a stride after each left strike."""
        w, one = walk(**TWO), walk()
        self.assertAlmostEqual(w.twist_gain, 200.0 / 4.0 / (L1 + L2) / wm.STEP_REF, delta=0.02)
        self.assertAlmostEqual(w.evaluate({"balance": 0.0}).info["stride_cm"], 50.0, places=6)
        ons = [f.on for f in w.steps["l"]] + [w.steps["l"][0].on + 48]
        for a, b in zip(ons, ons[1:]):
            self.assertAlmostEqual(w.list_at(a + wm.LIST_PEAK * (b - a)), 1.0, places=9)
            self.assertAlmostEqual(w.list_at(a + (wm.LIST_PEAK + 0.5) * (b - a)), -1.0, places=9)
        self.assertAlmostEqual(w.stride_phase(ons[0] + 48.0) - w.stride_phase(ons[0]), 4.0 * math.pi, places=9)
        self.assertAlmostEqual(one.stride_phase(one.feet["l"].on + 24.0) - one.stride_phase(one.feet["l"].on),
                               2.0 * math.pi, places=9)

    def test_the_feet_must_alternate(self):
        spans = {"l": TWO_STEPS["l"], "r": ((0.25, 0.95),)}
        with self.assertRaises(wm.Refusal) as caught:
            wm.analyse(clip(P=48, travel=80.0, strides=2, spans=spans))
        self.assertIn("the left foot steps 2 times a cycle and the right 1", str(caught.exception))


class PelvisHeightTests(unittest.TestCase):
    """Pelvis height: the pelvis this many cm over the feet, the legs following; never past their reach."""

    def test_it_raises_and_lowers_the_pelvis_over_still_feet(self):
        """(Foot placement off: with it a lower pelvis lets the trailing foot stay down longer - its timing
        follows the reach.)"""
        w = walk()
        base = w.evaluate({"balance": 0.0, "foot_placement": 0.0})
        pelvis = w.index["pelvis"]
        for cm in (-12.0, -4.0):
            r = w.evaluate({"balance": 0.0, "foot_placement": 0.0, "pelvis_height": cm})
            lift = r.worlds[pelvis, :, 3, 1] - base.worlds[pelvis, :, 3, 1]
            self.assertLess(float(np.abs(lift - cm).max()), 0.05 + float(max(base.info["drop"])), cm)
            for side in "lr":          # the feet where they were
                foot = w.index["foot_" + side]
                self.assertLess(float(np.abs(r.worlds[foot, :, 3, :3] - base.worlds[foot, :, 3, :3]).max()), 1e-6)

    def test_a_pelvis_raised_past_the_legs_reach_stays_on_them(self):
        w = walk()
        r = w.evaluate({"balance": 0.0, "pelvis_height": 40.0})
        for side in "lr":
            th, ca, fo = (w.index["%s_%s" % (b, side)] for b in ("thigh", "calf", "foot"))
            length = np.linalg.norm(w.lt[ca], axis=1).mean() + np.linalg.norm(w.lt[fo], axis=1).mean()
            reach = np.linalg.norm(r.worlds[fo, :, 3, :3] - r.worlds[th, :, 3, :3], axis=1) / length
            self.assertLess(float(reach.max()), w.reach[side] + 1e-3, side)
        self.assertGreater(max(r.info["drop"]), 30.0)            # the reach's drop takes most of it back

    def rolls(self, w, knobs):
        """The feet's roll curves (ctx["rolls"], radians a frame) of one evaluate."""
        box, low = {}, w._lowering

        def keep(times, ctx):
            out = low(times, ctx)
            box["rolls"] = ctx["rolls"]
            return out
        w._lowering = keep
        try:
            w.evaluate(knobs)
        finally:
            del w._lowering
        return box["rolls"]

    def test_a_raised_pelvis_keeps_the_legs_off_their_limit(self):
        """Raised past the legs' reach, every leg - planted, landing or swinging - is held LEG_MARGIN short of its
        limit: a knee held there by the drop's cover, or a swinging leg clamped at it, snapped straight and back
        (2026-10-16; near straight a millimetre of reach is degrees of knee)."""
        for kw in ({}, {"slip": 6.0}, {"stance": 0.5, "lift": 20.0}):
            w = walk(**kw)
            for knobs in ({"balance": 0.0, "pelvis_height": 12.0}, {"pelvis_height": 10.0, "stride": 1.2}):
                r = w.evaluate(knobs)
                self.assertLess(r.info["short"], 1e-6)
                for side in "lr":
                    th, ca, fo = (w.index["%s_%s" % (b, side)] for b in ("thigh", "calf", "foot"))
                    length = np.linalg.norm(w.lt[ca], axis=1).mean() + np.linalg.norm(w.lt[fo], axis=1).mean()
                    ext = np.linalg.norm(r.worlds[fo, :, 3, :3] - r.worlds[th, :, 3, :3], axis=1) / length
                    self.assertLess(float(ext.max()), w.reach[side] * (1.0 - wm.LEG_MARGIN) + 1e-4, (kw, knobs, side))

    def test_foot_flat_keeps_a_landed_foot_flat_on_the_ground(self):
        """Foot flat (2026-10-16, «носки дергаются и немного торчат вверх»): a leg short of its reach after the strike
        rocked the foot back on its heel, toes up, by as much as ROLL_HEEL - at 1 it never does (the pelvis sinks
        instead, the leg still reaching), at 0 it does, and each side takes its own."""
        w = walk()
        knobs = {"balance": 0.0, "pelvis_height": 8.0}
        rocked = self.rolls(w, dict(knobs, foot_flat=0.0))
        flat = self.rolls(w, dict(knobs))
        for side in "lr":
            self.assertLess(float(rocked[side].min()), math.radians(-5.0), side)     # toes up without it
            self.assertGreaterEqual(float(flat[side].min()), 0.0, side)             # never with it
        r = w.evaluate(dict(knobs))
        self.assertLess(r.info["short"], 1e-6)
        one = self.rolls(w, dict(knobs, foot_flat_l=0.0))
        self.assertLess(float(one["l"].min()), math.radians(-5.0))
        self.assertGreaterEqual(float(one["r"].min()), 0.0)

    def test_a_raised_pelvis_rolls_the_feet_without_a_flip(self):
        """Pelvis height past what the stance legs reach (2026-10-16, «сильно дергаются колени»): the foot rolled
        toes up over its heel, then heel up over its ball, flipping 15-22 deg in one frame at the heel-to-ball
        handoff - the ankle jumped and the near-straight knee snapped. The roll passes the handoff smoothly."""
        for kw in ({}, {"slip": 6.0}, {"stance": 0.5, "lift": 20.0}):
            w = walk(**kw)
            for cm in (6.0, 12.0):
                for knobs in ({"balance": 0.0, "pelvis_height": cm}, {"pelvis_height": cm, "stride": 1.2}):
                    rolls = self.rolls(w, knobs)
                    for side in "lr":
                        step = math.degrees(float(np.abs(np.diff(rolls[side])).max()))
                        self.assertLess(step, 2.0 * wm.ROLL_RATE * w.strides / 24.0 + 1e-6, (kw, knobs, side))  # a flip: a step each side of 0


class PelvisForwardTests(unittest.TestCase):
    """Pelvis forward: the hips this many cm ahead of (or behind) the feet, the body over them with them, the
    legs following; Balance keeps the shift it makes."""

    def ahead(self, w, r):
        pelvis = w.index["pelvis"]
        n = r.frames
        line = np.array([w.origin + w.travel * r.info["knobs"]["stride"] * f / float(n) for f in range(n)])
        return (r.worlds[pelvis, :n, 3, :3] - line) @ w.fwd

    def test_it_moves_the_pelvis_along_the_walk_over_still_feet(self):
        w = walk()
        off = {"balance": 0.0, "foot_placement": 0.0, "torso_drag": 0.0, "head_drag": 0.0}
        base = w.evaluate(off)
        for cm in (-8.0, 6.0):
            r = w.evaluate(dict(off, pelvis_forward=cm))
            self.assertLess(float(np.abs(self.ahead(w, r) - self.ahead(w, base) - cm).max()), 1e-6, cm)
            head = w.index["head"]                       # the body over the hips goes with them
            moved = (r.worlds[head, :, 3, :3] - base.worlds[head, :, 3, :3]) @ w.fwd
            self.assertLess(float(np.abs(moved - cm).max()), 1e-6)
            for side in "lr":
                foot = w.index["foot_" + side]
                self.assertLess(float(np.abs(r.worlds[foot, :, 3, :3] - base.worlds[foot, :, 3, :3]).max()), 1e-6)

    def test_balance_does_not_carry_it_back(self):
        """Balance puts the centre of mass over the feet - but the shift Pelvis forward asks for stays."""
        w = walk()
        base, r = w.evaluate({}), w.evaluate({"pelvis_forward": 6.0})
        shift = float((self.ahead(w, r) - self.ahead(w, base)).mean())
        self.assertGreater(shift, 5.0)
        self.assertLess(r.info["balance"]["residual"], 0.05)

    def test_zero_is_the_walk(self):
        w = walk()
        own = w.own_knobs()
        a, b = w.evaluate(own), w.evaluate(dict(own, pelvis_forward=0.0))
        self.assertTrue(np.array_equal(a.worlds, b.worlds))


class RunTests(unittest.TestCase):
    """A run (both feet up between the steps: HavyRun, 2026-10-13): Foot placement keeps its flight - it plants
    the stances and grows nothing (grown to a walk's double support, the run's swings were crushed, a swinging
    foot grazed the floor and the pelvis sank 64 cm)."""

    RUN = dict(stance=0.2, travel=200.0, lift=20.0)

    def test_a_run_s_handoffs_are_flights_and_are_not_grown(self):
        w = walk(**self.RUN)
        for side in "lr":
            self.assertTrue(all(w.is_flight(ds) for ds in w.double_src[side]), side)
            self.assertEqual([e["to"] for e in w.extend[side]], [0.0] * len(w.extend[side]))
        walker = walk()                                  # a walk: its handoffs are double support
        self.assertFalse(any(walker.is_flight(ds) for s in "lr" for ds in walker.double_src[s]))

    def test_foot_placement_plants_a_run_s_stances_and_keeps_its_flight(self):
        w = walk(**self.RUN)
        own, placed = w.evaluate({"foot_placement": 0.0}), w.evaluate({})
        p = placed.info["placement"]["planted"]
        self.assertGreater(int(np.sum(~np.array(p["l"]) & ~np.array(p["r"]))), 0)       # both feet up, between
        for side in "lr":
            self.assertGreater(still_point_slide(own, w, side), 1.0, side)       # the run's own feet slide
            self.assertLess(still_point_slide(placed, w, side), 0.05, side)
        self.assertLess(placed.info["lowered"], 1.0)
        self.assertLess(placed.info["placement"]["double"]["l"], 0.0)            # a flight, frames


class SideKnobTests(unittest.TestCase):
    """A leg or arm knob set for one side alone ("lift_l"): that side walks with it, the other with the knob."""

    def test_knobs_take_a_side_s_own_value_and_refuse_unknown_ones(self):
        k = wm.knobs(lift_l=2.5, arms_r=9.0)
        self.assertEqual((k["lift"], k["lift_l"], k["arms_r"]), (1.0, 2.5, 3.0))     # clamped to the knob's range
        ks = wm.sided(k)
        self.assertEqual((ks["l"]["lift"], ks["r"]["lift"], ks["l"]["arms"], ks["r"]["arms"]), (2.5, 1.0, 1.0, 3.0))
        self.assertNotIn("lift_l", ks["l"])
        with self.assertRaises(ValueError):
            wm.knobs(bob_l=2.0)                       # the pelvis has no sides

    def test_a_side_s_own_lift_lifts_that_foot_alone(self):
        w = walk()
        both, left = w.evaluate({}), w.evaluate({"lift_l": 2.0})
        height = lambda r, side: float(r.worlds[w.index["foot_" + side], :, 3, 1].max())
        self.assertGreater(height(left, "l"), height(both, "l") + 1.0)
        self.assertAlmostEqual(height(left, "r"), height(both, "r"), places=4)

    def test_a_side_s_own_arms_still_that_arm_alone(self):
        w = walk()
        still = w.evaluate({"arms_l": 0.0, "arm_drag": 0.0, "balance": 0.0})
        swing = lambda r, side: float(np.ptp(r.worlds[w.index["hand_" + side], :, 3, :3] @ w.fwd
                                             - r.worlds[w.index["upperarm_" + side], :, 3, :3] @ w.fwd))
        both = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        self.assertLess(swing(still, "l"), 0.5 * swing(both, "l"))
        self.assertAlmostEqual(swing(still, "r"), swing(both, "r"), places=4)

    def test_both_sides_set_alike_are_the_knob(self):
        w = walk()
        a = w.evaluate({"lift": 1.4, "foot_lag": 2.0})
        b = w.evaluate({"lift_l": 1.4, "lift_r": 1.4, "foot_lag_l": 2.0, "foot_lag_r": 2.0})
        self.assertLess(float(np.abs(a.worlds - b.worlds).max()), 1e-9)


class SurgeTests(unittest.TestCase):
    """Surge: x the pelvis's forward and back as it walks (Bob's partner along the walk)."""

    def along(self, w, r):
        pelvis, n = w.index["pelvis"], r.frames
        line = np.array([w.origin + w.travel * f / float(n) for f in range(n)])
        return (r.worlds[pelvis, :n, 3, :3] - line) @ w.fwd

    def test_it_scales_the_pelvis_s_forward_and_back(self):
        w = walk()
        plain = self.along(w, w.evaluate({"balance": 0.0, "foot_placement": 0.0}))
        for g in (0.0, 2.0):
            got = self.along(w, w.evaluate({"balance": 0.0, "foot_placement": 0.0, "surge": g}))
            want = plain.mean() + g * (plain - plain.mean())
            self.assertLess(float(np.abs(got - want).max()), 0.05 + 1e-6, g)

    def test_one_is_the_walk(self):
        w = walk()
        a, b = w.evaluate({}), w.evaluate({"surge": 1.0})
        self.assertTrue(np.array_equal(a.worlds, b.worlds))


class GroundTimeTests(unittest.TestCase):
    """Ground time: each foot's contact this many times as long (its lift-off moved), the swing quicker; past
    what a stretched leg on its toes reaches, the pelvis sinks at the push-off."""

    def planted(self, r):
        return dict((s, np.array(r.info["placement"]["planted"][s])) for s in "lr")

    def test_a_longer_ground_time_holds_each_foot_down_longer_without_a_slide(self):
        w = walk()
        base = w.evaluate({})
        held = w.evaluate({"ground_time": 1.3})
        for side in "lr":
            more = int(self.planted(held)[side].sum()) - int(self.planted(base)[side].sum())
            hs, to = w.contact[side][0]
            asked, got = held.info["ground"][side][0]
            self.assertEqual(asked, 1.3)
            # all of it, or as much as GROUND_ROOM of the swing leaves (this walker's swing is short)
            room = 1.0 + (wm.GROUND_ROOM * w.swing_len[side][0]) / (to - hs + 1.0)
            self.assertGreater(got, min(1.3, room) - 0.15, side)
            self.assertLessEqual(got, 1.3 + 1e-9, side)
            self.assertGreaterEqual(more, int((got - 1.0) * (to - hs + 1.0)) - 1, side)
            self.assertLess(still_point_slide(held, w, side), 0.05, side)
        p = self.planted(held)
        self.assertFalse(np.any(~p["l"] & ~p["r"]))               # one foot always down
        self.assertGreater(held.info["lowered"], base.info["lowered"])   # the stretched stance sinks the body

    def test_the_trailing_leg_stretches_onto_its_toes_first(self):
        """Up to a straight leg on its toes the stance lengthens with the pelvis where it was."""
        w = walk()
        base, held = w.evaluate({}), w.evaluate({"ground_time": 1.05})
        for side in "lr":
            th, ca, fo = (w.index["%s_%s" % (b, side)] for b in ("thigh", "calf", "foot"))
            length = np.linalg.norm(w.lt[ca], axis=1).mean() + np.linalg.norm(w.lt[fo], axis=1).mean()
            reach = np.linalg.norm(held.worlds[fo, :, 3, :3] - held.worlds[th, :, 3, :3], axis=1) / length
            self.assertLess(float(reach.max()), wm.STRETCH_REACH + 1e-3, side)
            self.assertGreater(float(reach.max()), w.reach[side] - 1e-3, side)

    def test_a_shorter_ground_time_lifts_sooner_but_never_both_feet(self):
        w = walk()
        base, quick = w.evaluate({}), w.evaluate({"ground_time": 0.8})
        p = self.planted(quick)
        self.assertLess(int(p["l"].sum()), int(self.planted(base)["l"].sum()))
        self.assertFalse(np.any(~p["l"] & ~p["r"]))

    def test_it_works_on_every_step_of_a_cycle_of_several(self):
        w = walk(**TWO)
        held = w.evaluate({"ground_time": 1.2})
        self.assertEqual([len(held.info["ground"][s]) for s in "lr"], [2, 2])
        for side in "lr":
            self.assertLess(still_point_slide(held, w, side), 0.05, side)

    def test_one_is_the_walk(self):
        w = walk()
        a, b = w.evaluate({}), w.evaluate({"ground_time": 1.0})
        self.assertTrue(np.array_equal(a.worlds, b.worlds))


class RollTests(unittest.TestCase):

    def roll_case(self, w, ctx, hip_shift):
        """The left foot planted at its source mid-contact, the hip moved back by `hip_shift` cm until the leg
        falls short: (the cost roll over the ball, the least reaching roll of before)."""
        side, t = "l", 0.5 * sum(w.contact["l"][0])
        rot, ankle = w.wrot(w.index["foot_l"], t), w.wpos(w.index["foot_l"], t)
        hip = w.wpos(w.index["thigh_l"], t) - hip_shift * w.fwd
        limit = w.reach[side] * (np.linalg.norm(w.lt_at(w.index["calf_l"], t)) +
                                 np.linalg.norm(w.lt_at(w.index["foot_l"], t)))
        return w._roll_cost(side, t, rot, ankle, hip, limit, ctx, 1.0)

    def test_the_roll_grows_smoothly_with_the_shortfall(self):
        """The roll weighs its angle against how far the leg falls short (ROLL_COST): a short leg rolls a
        little, a shorter one more, never in a leap."""
        w = walk(stance=0.4, lift=40.0)
        ctx = {"placement": 1.0}
        rolls = [self.roll_case(w, ctx, d) for d in np.linspace(0.0, 40.0, 161)]
        self.assertAlmostEqual(rolls[0], 0.0, places=6)
        steps = np.abs(np.diff(rolls))
        self.assertLess(math.degrees(float(steps.max())), 1.0)
        self.assertTrue(all(b >= a - 1e-9 for a, b in zip(rolls, rolls[1:])))

    def test_a_rolling_foot_turns_without_a_jolt(self):
        """At a quarter frame the foot's turning speed never leaps: the roll trades its angle against the
        shortfall smoothly, eases into its limits and fades off the ground (the least reaching roll of before
        leapt 13.2 deg a quarter frame on this walker at stride 1.3, 9.5 on the sliding one)."""
        for kw, knobs in (({}, {"tempo": 96, "stride": 1.3}), ({"slip": 6.0}, {"tempo": 96})):
            w = walk(**kw)
            r = w.evaluate(knobs)
            rot = r.worlds[w.index["foot_l"], :, :3, :3]
            speed = np.array([angle(rot[i].T @ rot[i + 1]) for i in range(r.frames)])
            self.assertLess(float(np.abs(np.diff(speed)).max()), 7.0, kw)


class ChestTests(unittest.TestCase):

    def test_chest_twist_and_sway_are_the_shoulders_turn_in_degrees(self):
        """The shoulder line turns each way as Chest twist says (x the step's gain, as Twist) and tilts as Chest
        sway says - under a hunched pose too, which turns the walk's own chest otherwise."""
        w = walk()
        for knobs, pose, tol in (({"chest_twist": 12.0, "chest_sway": 8.0}, None, 0.05),
                                 ({"chest_twist": 3.0, "chest_sway": 1.0}, None, 0.05),
                                 ({"chest_twist": 12.0, "chest_sway": 8.0, "pose": 1.0}, a_pose(w), 0.5)):
            r = w.evaluate(dict(knobs, balance=0.0, arm_drag=0.0, torso_drag=0.0, head_drag=0.0), pose)
            twist, sway = w.chest_fit(r.worlds)
            self.assertAlmostEqual(twist, knobs["chest_twist"] * w.twist_gain, delta=tol)
            self.assertAlmostEqual(sway, knobs["chest_sway"], delta=tol)
            self.assertIn("chest twists +-%.1f deg, sways +-%.1f" % (knobs["chest_twist"] * w.twist_gain,
                                                                    knobs["chest_sway"]), wm.describe(r))

    def test_the_walks_own_chest_is_its_own(self):
        w, c = walk(), clip()
        own = w.chest_fit(c.worlds)
        self.assertAlmostEqual(own[0], w.own_chest_twist * w.twist_gain, places=6)
        self.assertAlmostEqual(own[1], w.own_chest_sway, places=6)

    def test_the_chest_turns_alone(self):
        """Chest twist turns the chest, not the pelvis; the head keeps its own turn in the world."""
        w = walk()
        off = {"balance": 0.0, "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0}
        a = w.evaluate(dict(off, chest_twist=0.0))
        b = w.evaluate(dict(off, chest_twist=15.0))
        for name, same in (("pelvis", True), ("head", True), ("spine_02", False)):
            diff = float(np.abs(rotations(a, name, w) - rotations(b, name, w)).max())
            self.assertTrue(diff < 1e-9 if same else diff > 0.05, (name, diff))


def shake(r, w, name, above=6):
    """How much a joint shakes: its angular velocity (deg a frame, world) above harmonic `above` of the cycle, rms."""
    R = r.worlds[w.index[name], :, :3, :3]
    om = np.array([wm.log_rot(wm.orthonormal(R[f + 1]) @ wm.orthonormal(R[f]).T) for f in range(r.frames)])
    power = (np.abs(np.fft.rfft(om, axis=0)) ** 2).sum(axis=1)
    return math.degrees(math.sqrt(2.0 * power[above + 1:].sum()) / r.frames)


def swing_phase(r, w, a, b):
    """The fore-aft swing of the segment a -> b: (amplitude deg, the frame its first harmonic peaks)."""
    d = r.worlds[w.index[b], :r.frames, 3, :3] - r.worlds[w.index[a], :r.frames, 3, :3]
    d = d / np.linalg.norm(d, axis=1)[:, None]
    x = np.degrees(np.arcsin(np.clip(d @ w.fwd, -1.0, 1.0)))
    x = x - x.mean()
    t = np.arange(r.frames) / float(r.frames)
    c, s = 2.0 / r.frames * float(np.dot(x, np.cos(2 * math.pi * t))), 2.0 / r.frames * float(np.dot(x, np.sin(2 * math.pi * t)))
    return math.hypot(c, s), math.atan2(s, c) / (2.0 * math.pi) * r.frames


class ArmTests(unittest.TestCase):
    """The arms' inertia (Arm drag, Arm bounce): the frames are the target, the limbs follow it with weight."""

    def test_drag_lags_the_arms_and_keeps_them_whole(self):
        w = walk()
        target = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        r = w.evaluate({"arm_drag": 2.0, "arm_bounce": 0.0, "balance": 0.0})
        self.assertGreater(r.info["arms"]["cycles"], 1)
        for side in "lr":
            amp0, peak0 = swing_phase(target, w, "lowerarm_" + side, "hand_" + side)
            amp1, peak1 = swing_phase(r, w, "lowerarm_" + side, "hand_" + side)
            late = (peak1 - peak0 + 12.0) % 24.0 - 12.0
            self.assertGreater(late, 1.5, side)          # the hand swings later than its target
            self.assertLess(late, 6.0, side)
            for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_"), ("hand_", "index_01_")):
                d = np.linalg.norm(positions(r, b + side, w) - positions(r, a + side, w), axis=1)
                self.assertLess(float(np.ptp(d)), 1e-9, (side, a, b))
        moved = r.worlds[:, -1] - r.worlds[:, 0]
        self.assertLess(float(np.abs(moved[:, :3, :3]).max()), 1e-9)      # the loop closes
        self.assertLess(float(np.abs(moved[:, 3, :3] - [0.0, 0.0, 120.0]).max()), 1e-6)
        self.assertIn("the arms trail 2.0 frames behind the body", wm.describe(r))

    def test_bounce_whips_the_forearm_through(self):
        w = walk()
        settle = w.evaluate({"arm_drag": 2.0, "arm_bounce": 0.0, "balance": 0.0})
        whip = w.evaluate({"arm_drag": 2.0, "arm_bounce": 0.8, "balance": 0.0})
        self.assertGreater(swing_phase(whip, w, "lowerarm_l", "hand_l")[0],
                           1.15 * swing_phase(settle, w, "lowerarm_l", "hand_l")[0])

    def test_the_body_swings_still_arms(self):
        """Arms 0 holds the arms' own swing; with drag they still trail the body's own motion (its bob, sway and
        twist move the shoulders) - against the chest they move, without it they hang still in the world."""
        w = walk()
        still = w.evaluate({"arms": 0.0, "arm_drag": 0.0, "balance": 0.0})
        moved = w.evaluate({"arms": 0.0, "arm_drag": 3.0, "arm_bounce": 0.5, "balance": 0.0})
        j = w.index["lowerarm_l"]
        off = float(np.linalg.norm(moved.worlds[w.index["hand_l"], :, 3, :3] - still.worlds[w.index["hand_l"], :, 3, :3],
                                   axis=1).max())
        self.assertGreater(off, 0.5)

    def test_drag_zero_is_the_frames(self):
        w = walk()
        a = w.evaluate({"arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0})
        b = w.evaluate(dict(w.own_knobs(), pelvis_twist=5.0, pelvis_list=4.0,
                                                            foot_placement=1.0, root_sway=0.0,
                                                            chest_twist=7.0, chest_sway=5.0))
        self.assertLess(float(np.abs(a.worlds - b.worlds).max()), 1e-9)
        self.assertEqual(a.info["arms"]["drag"], 0.0)

    def test_a_held_thing_trails_as_one(self):
        """Hands holding one thing together keep their hold through the drag: the thing trails the chest as one
        body and the arms reach it, their bones whole."""
        w = walk()
        target = w.evaluate({"pose": 1.0, "arm_drag": 0.0, "balance": 0.0}, a_grip(w))
        r = w.evaluate({"pose": 1.0, "arm_drag": 3.0, "arm_bounce": 0.5, "balance": 0.0}, a_grip(w))
        self.assertTrue(r.info["arms"]["grip"])
        hands = [r.worlds[w.index["hand_l"], f] @ np.linalg.inv(r.worlds[w.index["hand_r"], f]) for f in range(25)]
        held = [target.worlds[w.index["hand_l"], f] @ np.linalg.inv(target.worlds[w.index["hand_r"], f]) for f in range(25)]
        self.assertLess(float(np.abs(np.array(hands) - held[0]).max()), 1e-6)
        trail = float(np.linalg.norm(positions(r, "hand_r", w) - positions(target, "hand_r", w), axis=1).max())
        self.assertGreater(trail, 0.3)
        for side in "lr":
            for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_")):
                d = np.linalg.norm(positions(r, b + side, w) - positions(r, a + side, w), axis=1)
                self.assertLess(float(np.ptp(d)), 1e-6, (side, a))
        self.assertIn("the held weapon trails", wm.describe(r))

    def test_balance_holds_the_centre_with_the_arms_moving(self):
        w = walk()
        r = w.evaluate({"arm_drag": 3.0, "arm_bounce": 0.6, "stance": 2.0})
        self.assertLess(r.info["balance"]["residual"], 0.05)

    def test_the_hand_swings_whole(self):
        """The hand's inertia acts on the whole hand: its lever reaches its farthest finger joint (index_02, 4 cm
        past index_01), not the first knuckle."""
        c = clip()
        j = c.names.index("index_01_l")
        tip = np.einsum("ij,fjk->fik", mat(np.eye(3), (4.0, 0.0, 0.0)), c.worlds[j])
        w = wm.analyse(wm.Clip(c.names + ["index_02_l"], c.parents + [j], np.concatenate([c.worlds, tip[None]]),
                               fps=30.0, up=(0, 1, 0), name="synthetic"))
        reach = float(np.linalg.norm(w._hand_lever(w.index["hand_l"])))
        self.assertGreater(reach, 12.8)
        self.assertLess(reach, 13.0 + 1e-9)
        self.assertIsNone(w._hand_lever(w.index["head"]))           # nothing below it is a finger

    def test_frame_noise_in_the_shoulder_does_not_shake_the_arm(self):
        """The arms feel the body's motion - its bob, sway and twist - not the frames' own noise: the left arm
        jolted 0.5 cm up and down on alternate frames (a rigid shift, its turns unchanged) swings its hand as
        smoothly as without the jolt. Taken from every harmonic (as the frames' second difference was), it shook."""
        c = clip()
        jolted = c.worlds.copy()
        arm = [c.names.index(n) for n in ("clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "index_01_l")]
        for f in range(jolted.shape[1]):
            jolted[arm, f, 3, 1] += 0.5 if f % 2 else -0.5
        w = wm.analyse(wm.Clip(c.names, c.parents, jolted, fps=30.0, up=(0, 1, 0), name="synthetic"))
        knobs = {"arm_drag": 2.0, "arm_bounce": 0.3, "balance": 0.0}
        calm = shake(w.evaluate(knobs), w, "hand_l")
        saved = wm.ARM_HARMONICS, wm.ACCEL_HZ
        wm.ARM_HARMONICS, wm.ACCEL_HZ = 1000, 1000.0
        try:
            shaken = shake(w.evaluate(knobs), w, "hand_l")
        finally:
            wm.ARM_HARMONICS, wm.ACCEL_HZ = saved
        smooth = shake(walk().evaluate(knobs), walk(), "hand_l")
        self.assertLess(calm, smooth + 0.01, (calm, smooth))
        self.assertGreater(shaken, 2.0 * calm, (shaken, calm))


def jolted_clip(names, amp=1.5):
    """The synthetic walker with `names` (each a joint and everything under it) turned amp deg about the walk's
    side axis through the joint, on alternate frames one way and the other - a corner at every frame."""
    c = clip()
    worlds = c.worlds.copy()
    for name in names:
        top = c.names.index(name)
        below = [top] + [j for j in range(len(c.names)) if top in _ancestors_of(c, j)]
        for f in range(worlds.shape[1]):
            turn = mat(rot_x(amp if f % 2 else -amp), [0.0, 0.0, 0.0])
            pivot = worlds[top, f, 3, :3].copy()
            for j in below:
                m = worlds[j, f].copy()
                m[3, :3] -= pivot
                m = m @ turn
                m[3, :3] += pivot
                worlds[j, f] = m
    worlds[:, -1] = worlds[:, 0]
    worlds[:, -1, 3, :3] += c.worlds[:, -1, 3, :3] - c.worlds[:, 0, 3, :3]      # the loop: the first moved
    return wm.Clip(c.names, c.parents, worlds, fps=30.0, up=(0, 1, 0), name="synthetic")


def _ancestors_of(c, j):
    out, p = [], c.parents[j]
    while p >= 0:
        out.append(p)
        p = c.parents[p]
    return out


class BodyDynamicsTests(unittest.TestCase):
    """The trunk and the head on springs (2026-10-14): each follows what the frames give it through a damped
    spring that feels its pivot's acceleration - a lagging, overshooting overlap, the frames' corners filtered."""

    still = {"balance": 0.0, "arm_drag": 0.0}

    def test_the_drags_zero_are_the_frames(self):
        w = walk()
        own = w.own_knobs()
        self.assertEqual((own["torso_drag"], own["head_drag"]), (0.0, 0.0))
        r = w.evaluate(dict(self.still, torso_drag=0.0, head_drag=0.0))
        self.assertEqual((r.info["body"]["torso"], r.info["body"]["head"]), (0.0, 0.0))

    def test_a_jittering_spine_leaves_the_chest_smoother(self):
        """spine_01 jolted 1.5 deg each way on alternate frames: the chest (and the head on it, its gaze its own)
        shakes a fraction of what the frames give it."""
        w = wm.analyse(jolted_clip(["spine_01"]))
        frames = w.evaluate(dict(self.still, torso_drag=0.0, head_drag=0.0))
        sprung = w.evaluate(dict(self.still, torso_drag=2.0, torso_bounce=0.2, head_drag=0.0))
        a, b = shake(frames, w, "spine_02"), shake(sprung, w, "spine_02")
        self.assertGreater(a, 1.0)
        self.assertLess(b, 0.35 * a, (a, b))

    def test_the_chest_lags_the_frames_by_about_its_drag(self):
        """The chest's world turn about up over the cycle (the walk's twist) runs about Torso drag late."""
        w = walk()
        heading = lambda r: np.array([math.degrees(math.atan2(*(lambda v: (float(np.dot(v, w.side)),
                                                                          float(np.dot(v, w.fwd))))(
            r.worlds[w.index["spine_02"], f, 2, :3]))) for f in range(r.frames)])
        frames = heading(w.evaluate(dict(self.still, torso_drag=0.0, head_drag=0.0)))
        for drag in (2.0, 4.0):
            sprung = heading(w.evaluate(dict(self.still, torso_drag=drag, torso_bounce=0.0, head_drag=0.0)))
            fine = np.linspace(0.0, 8.0, 161)
            spline = lambda x, s: np.interp((np.arange(len(x)) - s) % len(x), np.arange(len(x) + 1),
                                            np.append(x, x[0]))
            best = fine[int(np.argmin([np.abs(spline(frames, s) - sprung).max() for s in fine]))]
            self.assertAlmostEqual(best, drag, delta=0.75)

    def test_the_head_smooths_its_own_jitter_and_keeps_its_gaze(self):
        w = wm.analyse(jolted_clip(["head"], amp=2.0))
        frames = w.evaluate(dict(self.still, torso_drag=0.0, head_drag=0.0))
        sprung = w.evaluate(dict(self.still, torso_drag=0.0, head_drag=2.5))
        self.assertLess(shake(sprung, w, "head"), 0.35 * shake(frames, w, "head"))
        mean = lambda r: wm.mean_rot(r.worlds[w.index["head"], :r.frames, :3, :3])
        self.assertLess(angle(mean(sprung) @ mean(frames).T), 1.0)          # it looks where it looked
        self.assertGreater(sprung.info["body"]["head"], 0.0)

    def test_bones_keep_their_lengths_and_the_loop_closes(self):
        w = walk()
        r = w.evaluate({"torso_drag": 3.0, "torso_bounce": 0.5, "head_drag": 3.0})
        for name in ("spine_02", "neck_01", "head", "clavicle_l", "hand_r"):
            j, p = w.index[name], w.parents[w.index[name]]
            d = np.linalg.norm(r.worlds[j, :, 3, :3] - r.worlds[p, :, 3, :3], axis=1)
            self.assertLess(float(np.ptp(d)), 1e-6, name)
        moved = r.worlds[:, -1, 3, :3] - r.worlds[:, 0, 3, :3]
        self.assertLess(float(np.abs(moved - [0.0, 0.0, 120.0]).max()), 1e-6)
        self.assertLess(float(np.abs(r.worlds[:, -1, :3, :3] - r.worlds[:, 0, :3, :3]).max()), 1e-6)

    def test_balance_holds_the_centre_with_the_bodies_moving(self):
        w = walk()
        r = w.evaluate({"torso_drag": 3.0, "torso_bounce": 0.6, "head_drag": 3.0, "stance": 2.0})
        self.assertLess(r.info["balance"]["residual"], 0.05)

    def test_the_status_says_the_overlap(self):
        r = walk().evaluate({"torso_drag": 2.0, "head_drag": 2.5})
        self.assertIn("the trunk 2.0 and the head 2.5 frames behind", wm.describe(r))


class InPlaceTests(unittest.TestCase):
    """In place (2026-10-14): the root's progress along the walk taken off every joint - the root stays where frame
    0 has it (weaving only with Root sway), the body moves about it."""

    def test_the_root_stays_and_the_body_moves_about_it(self):
        w = walk()
        moving, still = w.evaluate({}), w.evaluate({"in_place": 1.0})
        root = positions(still, "root", w)
        self.assertLess(float(np.abs(root - root[0]).max()), 1e-9)       # the walker's root surges +-2 cm too
        for name in w.names:
            rel = positions(still, name, w) - root
            self.assertLess(float(np.abs(rel - (positions(moving, name, w) - positions(moving, "root", w))).max()),
                            1e-9, name)
        self.assertTrue(np.array_equal(still.worlds[:, :, :3, :3], moving.worlds[:, :, :3, :3]))
        self.assertLess(float(np.abs(still.worlds[:, -1] - still.worlds[:, 0]).max()), 1e-9)   # the loop, in place
        for key in ("stride_cm", "speed"):                                  # the status says the walk's
            self.assertEqual(still.info[key], moving.info[key])
        self.assertEqual(still.info["balance"], moving.info["balance"])
        left = w.feet["l"]
        foot = positions(still, "foot_l", w)[[left.on + i for i in range(left.length + 1)]]
        self.assertLess(float((foot[-1] - foot[0]) @ w.fwd), -40.0)        # a planted foot slides back
        self.assertIn("in place", wm.describe(still))
        self.assertNotIn("in place", wm.describe(moving))

    def test_root_sway_still_weaves_it(self):
        w = walk()
        moving = w.evaluate({"root_sway": 1.0})
        still = w.evaluate({"root_sway": 1.0, "in_place": 1.0})
        root, root0 = positions(still, "root", w), positions(moving, "root", w)
        self.assertLess(float(np.abs((root - root[0]) @ w.fwd).max()), 1e-9)
        self.assertLess(float(np.abs((root - root0) @ w.side).max()), 1e-9)
        self.assertGreater(float(np.ptp(root @ w.side)), 3.9)


class SceneTests(unittest.TestCase):
    """The Maya half (maya_walk.scene) on fakes: the session cache, the layers' base input."""

    def setUp(self):
        self.sw = load("skeldar_walk")
        self.saved = self.sw._cmds

    def tearDown(self):
        self.sw._cmds = self.saved

    def test_a_reloaded_package_forgets_what_its_old_model_read(self):
        """The session's cache lives on sys (an install purges and reloads the package and the target must
        survive); the walks in it were analysed by the model loaded then, and an old Walk's evaluate() does
        not take the new one's arguments (measured: 'evaluate() takes from 1 to 2 positional arguments but 3
        were given' in the animator's Maya) - a cache filled by another model starts afresh, the target kept."""
        state = self.sw._state()
        saved = dict(state)
        try:
            state["loaded"]["a walk"] = "read by the old model"
            state["target"] = "the target's uuid"
            state["model"] = object()            # another load of the model filled it
            self.assertNotIn("a walk", self.sw._state()["loaded"])
            self.assertEqual(self.sw._state()["target"], "the target's uuid")
            self.sw._state()["loaded"]["b walk"] = "read by this model"
            self.assertIn("b walk", self.sw._state()["loaded"])
        finally:
            state.clear()
            state.update(saved)

    def test_the_walks_live_outside_the_plugin_folder(self):
        """An install replaces the plugin folder: the walks go to <userAppDir>/SkeldarWalks, an optionVar
        overrides it, and the module's WALKS (a verify's temporary folder) overrides both."""
        class Fake(object):
            vars = {}

            def optionVar(self, exists=None, query=None):
                return exists in self.vars if exists is not None else self.vars[query]

            def internalVar(self, userAppDir=False):
                return "C:/Users/someone/Documents/maya/"
        fake = Fake()
        self.sw._cmds = lambda: fake
        saved = self.sw.WALKS
        try:
            self.sw.WALKS = None
            self.assertEqual(os.path.normpath(self.sw.folder()),
                             os.path.normpath("C:/Users/someone/Documents/maya/SkeldarWalks"))
            fake.vars[self.sw.FOLDER_OPTIONVAR] = "D:/walks"
            self.assertEqual(self.sw.folder(), "D:/walks")
            self.sw.WALKS = "T:/tmp"
            self.assertEqual(self.sw.folder(), "T:/tmp")
        finally:
            self.sw.WALKS = saved
        self.assertFalse(self.sw.folder.__module__.startswith("docs"))
        self.assertTrue(os.path.exists(self.sw.TEMPLATE), self.sw.TEMPLATE)

    def test_the_standalone_tool_is_gone(self):
        # the plugin is its home now: one copy of the model
        for name in ("skeldar_walk.py", "walkmodel.py", "walkfile.py", "walkpose.py", "walktarget.py"):
            self.assertFalse(os.path.exists(os.path.join(FOLDER, name)), name)

    def test_the_walk_rekeys_the_base_layer_under_animation_layers(self):
        """A channel under animation layers (an animator's correction keyed on a layer) is re-keyed at the bottom
        of its blend chain - the base layer's input - so the layer stays on top; a constrained channel is
        refused by name (wiring as Maya 2027 makes it, measured)."""
        wiring = {"j.rotateX": "j_rotate_Fix2.outputX", "j_rotate_Fix2.inputAX": "j_rotate_Fix1.outputX",
                  "j_rotate_Fix1.inputAX": "j_rotateX.output", "j.translateY": "j_translateY_Fix1.output",
                  "j_translateY_Fix1.inputA": None, "j.rotateZ": "j_rotateZ.output", "j.rotateY": None,
                  "j.translateX": "j_parentConstraint1.constraintTranslateX"}
        kinds = {"j_rotate_Fix2": "animBlendNodeAdditiveRotation", "j_rotate_Fix1": "animBlendNodeAdditiveRotation",
                 "j_rotateX": "animCurveTA", "j_translateY_Fix1": "animBlendNodeAdditiveDL", "j_rotateZ": "animCurveTA",
                 "j_parentConstraint1": "parentConstraint"}

        class Wired(object):
            def listConnections(self, plug, **kw):
                return [wiring[plug]] if wiring.get(plug) else []

            def nodeType(self, node):
                return kinds[node]
        self.sw._cmds = lambda: Wired()
        self.assertEqual(self.sw.base_input("j.rotateX"), ("j_rotate_Fix1.inputAX", "j_rotateX"))
        self.assertEqual(self.sw.base_input("j.translateY"), ("j_translateY_Fix1.inputA", None))
        self.assertEqual(self.sw.base_input("j.rotateZ"), ("j.rotateZ", "j_rotateZ"))
        self.assertEqual(self.sw.base_input("j.rotateY"), ("j.rotateY", None))
        with self.assertRaises(self.sw.Refusal) as said:
            self.sw.base_input("j.translateX")
        self.assertIn("parentConstraint", str(said.exception))
        # a weapon's link on weapon_r (2026-10-15): the re-key leaves that channel to its driver, not the walk
        written, held = self.sw.write_curves({"j": {"translateX": [0.0, 1.0]}}, {}, 0)
        self.assertEqual(written, 0)
        self.assertEqual(list(held), ["j"])


if __name__ == "__main__":
    unittest.main()


def backward_walk():
    """The synthetic walker played backward: a walk that travels the way its back faces."""
    c = clip()
    c.worlds = c.worlds[:, ::-1].copy()
    return wm.analyse(c)


class BackwardTests(unittest.TestCase):
    """A backward walk (2026-10-16): its body's left is the travel's right. A pose put its knees 40-50 deg in
    (Leg match read their heading across the +-180 wrap) and its hip twist was fitted across the same wrap."""

    def test_the_body_left_is_read_off_the_hips(self):
        self.assertEqual(walk().left, 1.0)
        w = backward_walk()
        self.assertEqual(w.left, -1.0)
        self.assertTrue(np.allclose(w.lside, -w.side) and np.allclose(w.ahead, -w.fwd))

    def test_own_knobs_give_a_backward_walk_back(self):
        w = backward_walk()
        r = w.evaluate(w.own_knobs())
        got = r.worlds[:, :w.P, 3, :3]
        self.assertLess(float(np.abs(got - w.clip.worlds[:, :w.P, 3, :3]).max()), 1e-6)

    def test_leg_match_turns_its_knees_out_as_a_forward_walk_does(self):
        pose = {"knee_turn": {"l": 0.3, "r": -0.3}, "toe": {"l": 0.2, "r": -0.2}, "hips_yaw": 0.0}
        ahead, back = walk(), backward_walk()
        a, b = ahead.matched_pose(pose, 1.0, 1.0), back.matched_pose(pose, 1.0, 1.0)
        for key in ("knee_turn", "toe"):
            for s in "lr":
                self.assertAlmostEqual(a[key][s], b[key][s], places=6, msg=(key, s))
            self.assertGreater(b[key]["l"], 0.0)       # out: toward the body's left for the left leg
            self.assertLess(b[key]["r"], 0.0)

    def test_the_hip_drop_lifts_the_same_hip_either_way(self):
        """Hip drop's added turn lifts the standing hip by the body's left and right, whichever way it walks."""
        for w in (walk(), backward_walk()):
            base = dict(w.own_knobs(), balance=0.0)
            more = w.evaluate(dict(base, pelvis_list=base["pelvis_list"] + 6.0))
            d = positions(more, "thigh_l", w) - positions(more, "thigh_r", w)
            across = np.linalg.norm(d - np.outer(d @ w.up, w.up), axis=1)
            got = np.degrees(np.arctan2(d @ w.up, across))
            lists = np.array([w.list_at(f * w.P / float(more.frames)) for f in range(more.frames + 1)])
            self.assertGreater(float(np.corrcoef(got, lists)[0, 1]), 0.9)


class SkimTests(unittest.TestCase):

    def test_a_foot_near_the_floor_still_flying_in_is_no_contact(self):
        """The synthetic foot comes down within CONTACT_TOL at frame 23 still moving 10 cm a frame (twice the
        walk's travel): its contact starts once it is held, not where it first nears the floor - a backward
        walk's foot skimming 40 cm along the floor after its step was planted there and sank the pelvis 20 cm."""
        w = walk()
        hs, _ = w.contact["l"][0]
        self.assertGreater(hs % w.P, 23.0)
