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


def foot_world(side, phi, travel, stance=0.6, lift=10.0):
    offset, x = (0.0, 10.0) if side == "l" else (0.5, -10.0)
    rel = phi - offset
    k = math.floor(rel)
    r = rel - k
    step = lambda i: np.array([x, 8.0, travel * (i + offset + stance / 2.0)])
    if r <= stance:
        return np.eye(3), step(k)
    u = (r - stance) / (1.0 - stance)
    s = u * u * (3.0 - 2.0 * u)
    return rot_x(-20 * math.sin(math.pi * s)), step(k) * (1 - s) + step(k + 1) * s + UP * lift * math.sin(math.pi * s)


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


def synthetic(P=24, travel=120.0):
    """A walker built the way the model reads one: feet planted in stance, legs by IK, the rest FK."""
    names = [b[0] for b in BONES]
    parents = [names.index(b[1]) if b[1] else -1 for b in BONES]
    local = dict((b[0], b[2]) for b in BONES)
    worlds = np.zeros((len(names), P + 1, 4, 4))
    for f in range(P + 1):
        phi = f / float(P)
        w = 2.0 * math.pi * phi
        W = {}
        W["root"] = mat(np.eye(3), [2 * math.sin(w), 0.0, travel * phi + 2 * math.sin(2 * w)])
        W["pelvis"] = mat(rot_y(5 * math.sin(w)) @ rot_x(2 * math.sin(2 * w)) @ rot_z(3 * math.sin(w)),
                          [2 * math.sin(w), 90 + 3 * math.cos(2 * w + 0.3), travel * phi + 2 * math.sin(2 * w)])
        for name in UPPER:
            parent = BONES[names.index(name)][1]
            W[name] = mat(upper_rot(name, phi), local[name]) @ W[parent]
        for side in "lr":
            pelvis = W["pelvis"]
            hip = np.array(local["thigh_" + side], float) @ pelvis[:3, :3] + pelvis[3, :3]
            foot_rot, ankle = foot_world(side, phi, travel)
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
    key = tuple(sorted(kw.items()))
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
        self.assertEqual((lag["spine_01"], lag["hand_l"], lag["index_01_l"], lag["thigh_l"]), (0.2, 1.0, 1.0, 0.0))
        follows = dict((w.names[h], w.names[b]) for h, (b, rel) in w.follows.items())
        self.assertEqual(follows["ik_foot_l"], "foot_l")
        self.assertEqual(follows["camera_root"], "root")
        order = [w.names[j] for j in w.order]
        self.assertLess(order.index("pelvis"), order.index("thigh_l"))
        self.assertLess(order.index("hand_r"), order.index("index_01_r"))
        self.assertEqual(set(order[-4:]), {"ik_foot_root", "ik_foot_l", "ik_foot_r", "camera_root"})


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

    def test_the_defaults_give_the_source_back(self):
        w, c = walk(), clip()
        r = w.evaluate()
        self.assertEqual(r.frames, 24)
        self.assertEqual(r.worlds.shape, c.worlds.shape)
        self.assertLess(float(np.abs(r.worlds - c.worlds).max()), 1e-6)
        self.assertEqual(r.info["lowered"], 0.0)
        self.assertEqual(r.info["short"], 0.0)
        self.assertIn("24 frames, stride 60.0 cm, 1.50 m/s", wm.describe(r))


class StepTests(unittest.TestCase):

    def test_stride_moves_the_footprints_and_keeps_the_stance_foot_still(self):
        w = walk()
        r = w.evaluate({"stride": 1.3})
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

    def test_width_moves_the_feet_apart(self):
        w = walk()
        r = w.evaluate({"width": 10.0})
        src = clip().worlds
        mid_l, mid_r = int(round(w.feet["l"].mid)) % 24, int(round(w.feet["r"].mid)) % 24
        self.assertAlmostEqual(positions(r, "foot_l", w)[mid_l, 0] - src[w.index["foot_l"], mid_l, 3, 0], 5.0)
        self.assertAlmostEqual(positions(r, "foot_r", w)[mid_r, 0] - src[w.index["foot_r"], mid_r, 3, 0], -5.0)

    def test_a_long_stride_on_a_flat_pelvis_lowers_it_to_reach(self):
        w = walk()
        r = w.evaluate({"stride": 1.6, "bob": 0.0})
        self.assertGreater(r.info["lowered"], 1.0)
        self.assertLess(r.info["short"], 1e-6)
        for side in "lr":
            d = np.linalg.norm(positions(r, "foot_" + side, w) - positions(r, "thigh_" + side, w), axis=1)
            self.assertLessEqual(float(d.max()), w.reach[side] * (L1 + L2) + 1e-6)
        self.assertIn("pelvis lowered", wm.describe(r))

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
        dev = self.pelvis(r, w)[:24, 1] - w.pelvis_mean[2] + r.info["lowered"]
        self.assertTrue(np.allclose(dev, 2.0 * (src - src.mean()), atol=1e-6))

    def test_sway_zero_holds_the_pelvis_on_its_line(self):
        w = walk()
        side = self.pelvis(w.evaluate({"sway": 0.0}), w)[:, 0]
        self.assertLess(float(np.ptp(side)), 1e-9)

    def test_arms_scale_their_local_swing(self):
        w, c = walk(), clip()
        still = w.evaluate({"arms": 0.0})
        firsts = [local_rot(still, "upperarm_l", w, f) for f in range(25)]
        self.assertLess(max(angle(m @ firsts[0].T) for m in firsts), 1e-6)
        double = w.evaluate({"arms": 2.0})
        j = w.index["upperarm_l"]
        mean = w.lmean[j]
        for f in (3, 9, 15):
            src = c.worlds[j, f, :3, :3] @ c.worlds[w.parents[j], f, :3, :3].T
            self.assertAlmostEqual(angle(local_rot(double, "upperarm_l", w, f) @ mean.T),
                                   2.0 * angle(src @ mean.T), places=6)

    def test_head_zero_holds_the_head_steady_in_the_world(self):
        w = walk()
        heads = rotations(w.evaluate({"head": 0.0}), "head", w)
        self.assertLess(float(np.abs(heads - heads[0]).max()), 1e-9)

    def test_overlap_delays_the_hand_by_its_share(self):
        w, c = walk(), clip()
        r = w.evaluate({"overlap": 2.0})
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
        w = walk()
        r = w.evaluate({"exaggeration": 0.0})
        pel = r.worlds[w.index["pelvis"]]
        self.assertLess(float(np.abs(pel[:, :3, :3] - pel[0, :3, :3]).max()), 1e-9)
        self.assertLess(float(np.ptp(pel[:, 3, 1])), 1e-9)
        spine = [local_rot(r, "spine_02", w, f) for f in range(25)]
        self.assertLess(max(angle(m @ spine[0].T) for m in spine), 1e-6)
        left = w.feet["l"]
        foot = positions(r, "foot_l", w)[[left.on + i for i in range(left.length + 1)]]
        self.assertLess(float(np.ptp(foot, axis=0).max()), 1e-9)


if __name__ == "__main__":
    unittest.main()
