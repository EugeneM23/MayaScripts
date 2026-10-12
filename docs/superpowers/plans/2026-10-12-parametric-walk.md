# Parametric Walk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read a walk cycle once, rebuild it from knobs (stride, tempo, lift, width, pelvis, upper body,
overlap, weight, exaggeration), and key the result onto a copy beside the source.

**Architecture:** `walkmodel.py` (numpy, no Maya) holds the analysis (cycle, travel line, contacts,
footprints, means and deviations, helper follow relations) and `Walk.evaluate(knobs)` -> world matrices.
`skeldar_walk.py` reads the scene's skeleton into a `Clip`, duplicates it, converts the model's worlds into
joint channels and writes them through `MFnAnimCurve.addKeys`; it also holds the window. `verify_walk.py`
proves it in mayapy standalone on the animator's clip.

**Tech Stack:** Python 3 (mayapy 2027), numpy, maya.cmds, maya.api.OpenMaya / OpenMayaAnim, unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-12-parametric-walk-design.md` — every formula there is binding.
- Files live in `docs/superpowers/plans/walkparam/`; nothing in `SkeldarAnim/` changes.
- `walkmodel.py` imports numpy and the stdlib only (a test pins it).
- Maya row vectors: world = local . parent, position = row 3, a rotation turns v as v . R.
- At default knobs the copy equals the source on every joint and frame (model 1e-6, Maya 1e-4 cm / 1e-3).
- The source cycle is never modified; the animator's open Maya is never written to by a verify.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel -v`
  from the repo root (no system Python; it hangs).
- Commit only this feature's files: `git add <paths> && git commit -m ... -- <paths>` (peers share `main`).

---

### Task 1: The model's math — rotations, the periodic sampler, IK, alignment, knobs

**Files:**
- Create: `docs/superpowers/plans/walkparam/walkmodel.py`
- Test: `tests/test_walkmodel.py`

**Interfaces:**
- Produces: `exp_rot(w) -> (...,3,3)`, `log_rot(r) -> (...,3)`, `mean_rot(rs) -> (3,3)`,
  `orthonormal(m) -> (3,3)`, `matrix(rot, pos) -> (4,4)`, `periodic_cr(x, tau)`,
  `warp(phi, beta, phi0) -> float`, `shape_bob(v, weight) -> float`,
  `two_bone(hip, ankle, l1, l2, bend, reach) -> (knee, ankle_reached, short)`,
  `align(u_src, n_src, u_new, n_new) -> (3,3)`, `knobs(**given) -> dict`, `KNOBS`, `DEFAULTS`,
  `RANGES`, `Refusal`.

- [ ] **Step 1: Write the failing tests** — `tests/test_walkmodel.py` (the loader, the row-vector
  rotation helpers the synthetic walker will also use, and the math tests):

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel -v`
Expected: FAIL — `FileNotFoundError` for `walkmodel.py`.

- [ ] **Step 3: Write the minimal implementation** — `walkmodel.py` (the header and the math):

```python
"""walkmodel.py - the parametric walk's model: a walk cycle read once, rebuilt from knobs.

numpy only, no Maya (tests/test_walkmodel.py runs it on a synthetic walker). Maya's row vectors
throughout: a world matrix is local . parent, a position its row 3, a rotation turns a row vector v as
v . R. The design: docs/superpowers/specs/2026-10-12-parametric-walk-design.md.
"""
import math
import re

import numpy as np

VERSION = 1

# name, default, low, high - tempo 0 means the source's own cycle length
KNOBS = (
    ("stride", 1.0, 0.4, 1.8),
    ("tempo", 0.0, 0.0, 2000.0),
    ("lift", 1.0, 0.0, 3.0),
    ("width", 0.0, -15.0, 25.0),
    ("bob", 1.0, 0.0, 3.0),
    ("sway", 1.0, 0.0, 3.0),
    ("pelvis_rot", 1.0, 0.0, 3.0),
    ("spine", 1.0, 0.0, 3.0),
    ("arms", 1.0, 0.0, 3.0),
    ("head", 1.0, 0.0, 3.0),
    ("overlap", 0.0, 0.0, 6.0),
    ("weight", 0.0, -1.0, 2.0),
    ("exaggeration", 1.0, 0.0, 2.0),
)
DEFAULTS = dict((k[0], k[1]) for k in KNOBS)
RANGES = dict((k[0], (k[2], k[3])) for k in KNOBS)

WEIGHT_BOB_DOWN = 0.5     # the bob's low half x (1 + this . weight)
WEIGHT_BOB_UP = 0.15      # its high half x max(0, 1 - this . weight)
WEIGHT_WARP = 0.3         # the bob's clock: beta = this . weight
WEIGHT_WARP_AFTER = 0.05  # slowest this share of a cycle after each low
WEIGHT_LAG = 1.0          # frames of overlap per unit of weight


class Refusal(Exception):
    """A clip the model does not read; the message says why, in the animator's terms."""


def knobs(**given):
    """The defaults with `given` on top, each clamped to its range; an unknown name raises ValueError."""
    unknown = sorted(set(given) - set(DEFAULTS))
    if unknown:
        raise ValueError("unknown knob(s): " + ", ".join(unknown))
    out = dict(DEFAULTS)
    for name, value in given.items():
        if value is None:
            continue
        low, high = RANGES[name]
        out[name] = min(max(float(value), low), high)
    return out


def _unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v * 0.0


def _any_perpendicular(e):
    return _unit(np.cross(e, np.eye(3)[int(np.argmin(np.abs(e)))]))


def _skew(w):
    z = np.zeros(w.shape[:-1])
    return np.stack([np.stack([z, -w[..., 2], w[..., 1]], -1),
                     np.stack([w[..., 2], z, -w[..., 0]], -1),
                     np.stack([-w[..., 1], w[..., 0], z], -1)], -2)


def exp_rot(w):
    """The row-vector rotation by |w| radians about w (right hand); w may be (..., 3)."""
    w = np.asarray(w, float)
    th = np.linalg.norm(w, axis=-1)[..., None, None]
    small = th < 1e-12
    k = _skew(w) / np.where(small, 1.0, th)
    eye = np.broadcast_to(np.eye(3), k.shape)
    column = eye + np.sin(th) * k + (1.0 - np.cos(th)) * (k @ k)
    return np.swapaxes(np.where(small, eye, column), -1, -2)


def log_rot(r):
    """The rotation vector w (|w| <= pi) with exp_rot(w) == r; r may be (..., 3, 3)."""
    c = np.swapaxes(np.asarray(r, float), -1, -2)
    th = np.arccos(np.clip((np.trace(c, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0))
    v = np.stack([c[..., 2, 1] - c[..., 1, 2], c[..., 0, 2] - c[..., 2, 0], c[..., 1, 0] - c[..., 0, 1]], -1)
    sin = np.sin(th)
    ok = sin > 1e-7
    w = v * np.where(ok, th / (2.0 * np.where(ok, sin, 1.0)), 0.5)[..., None]
    near_pi = (~ok) & (th > 1.0)
    if np.any(near_pi):
        flat_c, flat_w = c.reshape(-1, 3, 3), np.array(w).reshape(-1, 3)
        flat_th = np.broadcast_to(th, near_pi.shape).reshape(-1)
        for i in np.nonzero(near_pi.reshape(-1))[0]:
            m = (flat_c[i] + np.eye(3)) / 2.0
            flat_w[i] = _unit(m[:, int(np.argmax(np.diag(m)))]) * flat_th[i]
        w = flat_w.reshape(w.shape)
    return w


def _proper(u, vt):
    m = u @ vt
    if np.linalg.det(m) < 0.0:
        u = u.copy()
        u[:, -1] *= -1.0
        m = u @ vt
    return m


def mean_rot(rs):
    """The chordal mean of rotations (n, 3, 3)."""
    u, _, vt = np.linalg.svd(np.sum(np.asarray(rs, float), axis=0))
    return _proper(u, vt)


def orthonormal(m):
    """The rotation nearest m's 3x3 part (scale and shear stripped)."""
    u, _, vt = np.linalg.svd(np.asarray(m, float)[:3, :3])
    return _proper(u, vt)


def matrix(rot, pos):
    out = np.eye(4)
    out[:3, :3] = rot
    out[3, :3] = pos
    return out


def periodic_cr(x, tau):
    """Periodic Catmull-Rom through x[0..P-1] (period P) at any real tau; exact on whole frames."""
    p = x.shape[0]
    i = int(math.floor(tau))
    u = tau - i
    p1 = x[i % p]
    if u < 1e-12:
        return np.array(p1, float)
    p0, p2, p3 = x[(i - 1) % p], x[(i + 1) % p], x[(i + 2) % p]
    return 0.5 * (2.0 * p1 + (p2 - p0) * u + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * u * u
                  + (3.0 * p1 - p0 - 3.0 * p2 + p3) * u ** 3)


def warp(phi, beta, phi0):
    """The bob's clock: slowest (slope 1 - beta) a quarter and three quarters of a cycle after phi0."""
    return phi + beta / (4.0 * math.pi) * math.sin(4.0 * math.pi * (phi - phi0))


def shape_bob(v, weight):
    """The weight on one bob sample about its mean: the low half deeper, the high half flatter."""
    if v < 0.0:
        return v * (1.0 + WEIGHT_BOB_DOWN * weight)
    return v * max(0.0, 1.0 - WEIGHT_BOB_UP * weight)


def two_bone(hip, ankle, l1, l2, bend, reach):
    """The knee of a hip-knee-ankle chain bending toward `bend`, the leg never straighter than
    reach . (l1 + l2). Returns (knee, the ankle it reaches, how far it falls short)."""
    v = np.asarray(ankle, float) - hip
    d = float(np.linalg.norm(v))
    e = v / d if d > 1e-9 else np.array([0.0, -1.0, 0.0])
    d_eff = max(min(d, reach * (l1 + l2)), abs(l1 - l2) + 1e-6)
    p = bend - np.dot(bend, e) * e
    p = _unit(p) if np.linalg.norm(p) > 1e-9 else _any_perpendicular(e)
    along = (l1 * l1 - l2 * l2 + d_eff * d_eff) / (2.0 * d_eff)
    height = math.sqrt(max(0.0, l1 * l1 - along * along))
    return hip + along * e + height * p, hip + d_eff * e, max(0.0, d - d_eff)


def _frame(u, n):
    return np.stack([u, n, np.cross(u, n)])


def align(u_src, n_src, u_new, n_new):
    """The rotation taking the frame (u_src, n_src) onto (u_new, n_new): v . align = v'.
    Each n must be perpendicular to its u (a leg plane's normal against a bone in the plane)."""
    return _frame(u_src, n_src).T @ _frame(u_new, n_new)
```

- [ ] **Step 4: Run the tests** — same command. Expected: all 15 PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/walkparam/walkmodel.py tests/test_walkmodel.py && git commit -m "feat(walk): the model's math - rotations, the periodic sampler, IK, alignment, knobs" -- docs/superpowers/plans/walkparam/walkmodel.py tests/test_walkmodel.py
```

### Task 2: The analysis — Clip, Walk, contacts, reach, helpers, refusals

**Files:**
- Modify: `docs/superpowers/plans/walkparam/walkmodel.py` (append)
- Test: `tests/test_walkmodel.py` (append the synthetic walker and the analysis tests)

**Interfaces:**
- Consumes: Task 1.
- Produces: `Clip(names, parents, worlds, fps=30.0, up=(0,1,0), name="walk")`; `analyse(clip) -> Walk`;
  `Walk` attributes `P, fps, up, fwd, side, travel, origin, names, parents, index, kind, lag, order,
  feet{side: Foot(on, length, mid, coords)}, reach{side: float}, follows{h: (bone, rel 4x4)}`;
  methods `line(tau)`, `wrot(j, tau, gain=1)`, `wpos(j, tau)`, `lrot_at(j, tau, gain=1)`,
  `lt_at(j, tau)`, `source_world(j, tau)`, `summary() -> str`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_walkmodel.py` (before `if __name__`):

```python
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
```

- [ ] **Step 2: Run to verify it fails** — `AttributeError: module has no attribute 'Clip'`.

- [ ] **Step 3: Append the implementation** to `walkmodel.py`:

```python
SIDES = ("l", "r")
SIDE_WORD = {"l": "left", "r": "right"}
LEG = ("thigh", "calf", "foot")
HELPER_PREFIXES = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass")
ARM_STEMS = ("clavicle", "upperarm", "lowerarm", "hand")
LAG = {"spine_01": 0.2, "spine_02": 0.3, "spine_03": 0.4, "spine_04": 0.5, "spine_05": 0.6,
       "neck_01": 0.7, "neck_02": 0.8, "head": 0.9,
       "clavicle": 0.6, "upperarm": 0.8, "lowerarm": 1.0, "hand": 1.0}
CONTACT_SHARE = 0.2      # in stance the ankle or the ball moves less than this share of the travel a frame
FOLLOW_TOL = 1e-3        # a helper follows a bone when helper . bone^-1 holds within this (matrix elements)
LOOP_TOL = (0.1, 0.002)  # cm and rotation elements: the last frame against the first moved by the travel


def _stem(name):
    m = re.match(r"([a-z]+)(_twist_\d+)?_[lr]$", name)
    return m.group(1) if m else None


class Clip(object):
    """A walk cycle as data: joint names, parent indices (-1: none), world matrices (J, P+1, 4, 4) on the
    clip's whole frames (the last the first moved by the travel), frames a second, the world's up."""

    def __init__(self, names, parents, worlds, fps=30.0, up=(0.0, 1.0, 0.0), name="walk"):
        self.names = list(names)
        self.parents = [int(p) for p in parents]
        self.worlds = np.asarray(worlds, float)
        self.fps = float(fps)
        self.up = _unit(up)
        self.name = name


class Foot(object):
    """A foot's contact: stance from frame `on` for `length` frames more, mid-stance at `mid`, the
    footprint's coordinates (along, aside, up) against the travel line there."""

    def __init__(self, side, on, length, mid, coords):
        self.side, self.on, self.length, self.mid, self.coords = side, on, length, mid, coords


def analyse(clip):
    """The clip read once (refusals by name); evaluate() rebuilds it from knobs."""
    return Walk(clip)


class Walk(object):

    def __init__(self, clip):
        self.clip = clip
        self.names, self.parents = clip.names, clip.parents
        self.index = dict((n, i) for i, n in enumerate(self.names))
        need = ["root", "pelvis"] + ["%s_%s" % (b, s) for s in SIDES for b in LEG + ("ball",)]
        missing = [n for n in need if n not in self.index]
        if missing:
            raise Refusal("not a skeleton this model reads (UE names): no " + ", ".join(missing))
        count, frames = clip.worlds.shape[:2]
        if frames < 9:
            raise Refusal("%d frames: too short for a walk cycle" % frames)
        self.P = P = frames - 1
        self.fps, self.up = clip.fps, clip.up
        rot = clip.worlds[:, :, :3, :3]
        rot = rot / np.linalg.norm(rot, axis=-1, keepdims=True)
        pos = clip.worlds[:, :, 3, :3]
        root = self.index["root"]
        travel = pos[root, P] - pos[root, 0]
        climb = float(np.dot(travel, self.up))
        flat = travel - climb * self.up
        if abs(climb) > 0.5:
            raise Refusal("the root climbs %.1f cm a cycle: a walk on flat ground only" % climb)
        if np.linalg.norm(flat) < 1.0:
            raise Refusal("the root travels %.2f cm a cycle: an in-place walk is not read yet (the root must "
                          "carry the travel)" % np.linalg.norm(flat))
        moved = float(np.abs(pos[:, P] - pos[:, 0] - travel).max())
        turned = float(np.abs(rot[:, P] - rot[:, 0]).max())
        if moved > LOOP_TOL[0] or turned > LOOP_TOL[1]:
            raise Refusal("not a closed loop: the last frame stands %.3f cm / %.4f off the first moved by the "
                          "travel - the cycle must end on its first pose" % (moved, turned))
        self.travel = travel
        self.fwd = _unit(flat)
        self.side = _unit(np.cross(self.up, self.fwd))
        self.basis = np.stack([self.fwd, self.side, self.up])     # travel coordinates: v . basis.T
        steps = np.arange(P) / float(P)
        self.origin = pos[root, 0] + (pos[root, :P] - pos[root, 0] - np.outer(steps, travel)).mean(axis=0)
        self.rot, self.pos = rot[:, :P], pos[:, :P]
        self.pdev = self.pos - (self.origin + np.outer(steps, travel))[None]
        self.wmean = np.stack([mean_rot(self.rot[j]) for j in range(count)])
        self.wlog = log_rot(self.rot @ np.swapaxes(self.wmean, -1, -2)[:, None])
        self._locals()
        self._kinds()
        self.feet = dict((s, self._contact(s)) for s in SIDES)
        self.reach = dict((s, self._reach(s)) for s in SIDES)
        self.follows = self._helpers()
        self.root_mean = (self.pdev[root] @ self.basis.T).mean(axis=0)
        self.pelvis_mean = (self.pdev[self.index["pelvis"]] @ self.basis.T).mean(axis=0)
        bob = self.pdev[self.index["pelvis"]] @ self.up - self.pelvis_mean[2]
        self.low_phase = float(np.argmin(bob)) / P

    # -- the source, sampled at any source time tau (whole frames exact) --

    def line(self, tau):
        return self.origin + self.travel * (tau / float(self.P))

    def wrot(self, j, tau, gain=1.0):
        return exp_rot(gain * periodic_cr(self.wlog[j], tau)) @ self.wmean[j]

    def wpos(self, j, tau):
        return periodic_cr(self.pdev[j], tau) + self.line(tau)

    def lrot_at(self, j, tau, gain=1.0):
        return exp_rot(gain * periodic_cr(self.llog[j], tau)) @ self.lmean[j]

    def lt_at(self, j, tau):
        return periodic_cr(self.lt[j], tau)

    def source_world(self, j, tau):
        return matrix(self.wrot(j, tau), self.wpos(j, tau))

    def summary(self):
        flat = self.travel - np.dot(self.travel, self.up) * self.up
        stance = " ".join("%s %d %%" % (s.upper(), round(100.0 * (self.feet[s].length + 1) / self.P))
                          for s in SIDES)
        return "%s: cycle %d frames (%.2f s), stride %.1f cm, %.2f m/s, stance %s" % (
            self.clip.name, self.P, self.P / self.fps, np.linalg.norm(flat) / 2.0,
            np.linalg.norm(flat) / (self.P / self.fps) / 100.0, stance)

    # -- the analysis --

    def _locals(self):
        count = len(self.names)
        self.lt = np.zeros_like(self.pos)
        self.lmean = np.tile(np.eye(3), (count, 1, 1))
        self.llog = np.zeros_like(self.pos)
        for j, p in enumerate(self.parents):
            if p < 0:
                continue
            back = np.swapaxes(self.rot[p], -1, -2)
            lrot = self.rot[j] @ back
            self.lt[j] = np.einsum("fi,fij->fj", self.pos[j] - self.pos[p], back)
            self.lmean[j] = mean_rot(lrot)
            self.llog[j] = log_rot(lrot @ self.lmean[j].T)

    def _ancestors(self, j):
        out = []
        p = self.parents[j]
        while p >= 0:
            out.append(p)
            p = self.parents[p]
        return out

    def _kinds(self):
        legs = set("%s_%s" % (b, s) for s in SIDES for b in LEG)
        self.kind, self.lag = [], []
        for j, name in enumerate(self.names):
            above = [self.names[a] for a in self._ancestors(j)]
            if name in ("root", "pelvis"):
                kind = name
            elif name in legs:
                kind = "leg"
            elif name.startswith(HELPER_PREFIXES) or any(a.startswith(HELPER_PREFIXES) for a in above):
                kind = "helper"
            elif re.match(r"(spine|neck)_\d+$", name):
                kind = "spine"
            elif name == "head":
                kind = "head"
            elif _stem(name) in ARM_STEMS:
                kind = "arm"
            elif "hand_l" in above or "hand_r" in above:
                kind = "finger"
            elif self.parents[j] < 0:
                kind = "world"
            else:
                kind = "local"
            self.kind.append(kind)
            self.lag.append(LAG.get(name, LAG.get(_stem(name), 1.0 if kind == "finger" else 0.0)))
        kids = dict((j, []) for j in range(len(self.names)))
        for j, p in enumerate(self.parents):
            if p >= 0:
                kids[p].append(j)
        bfs, queue = [], [j for j, p in enumerate(self.parents) if p < 0]
        while queue:
            j = queue.pop(0)
            bfs.append(j)
            queue.extend(kids[j])
        self.order = [j for j in bfs if self.kind[j] != "helper"] + [j for j in bfs if self.kind[j] == "helper"]

    def _contact(self, side):
        P = self.P
        speeds = []
        for name in ("foot_" + side, "ball_" + side):
            p = self.pos[self.index[name]]
            ahead = np.vstack([p[1:], p[:1] + self.travel])
            behind = np.vstack([p[-1:] - self.travel, p[:-1]])
            speeds.append(np.linalg.norm(ahead - behind, axis=1) / 2.0)
        slow = np.minimum(speeds[0], speeds[1]) < np.linalg.norm(self.travel) / P * CONTACT_SHARE
        if slow.all():
            raise Refusal("the %s foot never leaves the ground" % SIDE_WORD[side])
        if not slow.any():
            raise Refusal("the %s foot never stops: no contact to plant it on" % SIDE_WORD[side])
        start = int(np.nonzero(~slow)[0][0])
        best, run, run_on = (0, 0), 0, 0
        for step in range(1, P + 1):
            i = (start + step) % P
            if slow[i]:
                if run == 0:
                    run_on = i
                run += 1
                if run > best[1]:
                    best = (run_on, run)
            else:
                run = 0
        on, length = best[0], best[1] - 1
        mid = on + length / 2.0
        coords = periodic_cr(self.pdev[self.index["foot_" + side]], mid) @ self.basis.T
        return Foot(side, on, length, mid, coords)

    def _reach(self, side):
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        d = np.linalg.norm(self.pos[fo] - self.pos[th], axis=1)
        return float((d / (np.linalg.norm(self.lt[ca], axis=1) + np.linalg.norm(self.lt[fo], axis=1))).max())

    def _helpers(self):
        worlds = self.clip.worlds[:, :self.P]
        body = [j for j, k in enumerate(self.kind) if k != "helper"]
        follows = {}
        for h, kind in enumerate(self.kind):
            if kind != "helper":
                continue
            best = None
            for b in body:
                rel = worlds[h] @ np.linalg.inv(worlds[b])
                err = float(np.abs(rel - rel[0]).max())
                if err < FOLLOW_TOL:
                    key = (len(self._ancestors(b)), err)
                    if best is None or key < best[0]:
                        best = (key, b, rel[0])
            if best is not None:
                follows[h] = (best[1], best[2])
        return follows
```

- [ ] **Step 4: Run the tests** — Expected: all PASS (Task 1's and the 8 new).

- [ ] **Step 5: Commit** — the same two paths, message `feat(walk): the analysis - travel, contacts, reach, helpers, refusals`.

### Task 3: Evaluate — the new cycle from knobs

**Files:**
- Modify: `docs/superpowers/plans/walkparam/walkmodel.py` (append `Result`, `describe`, and `Walk`
  methods `evaluate`, `foot_target`, `_body`, `_lowering`, `_frame`, `_leg`)
- Test: `tests/test_walkmodel.py` (append)

**Interfaces:**
- Consumes: Task 2.
- Produces: `Walk.evaluate(given=None) -> Result` with `worlds (J, N+1, 4, 4)` in the source's world,
  `frames` (= N) and `info {"frames", "stride_cm", "speed", "lowered", "short", "lag", "knobs"}`;
  `Walk.foot_target(side, tau, stride, width, lift) -> (rot, ankle)`; `describe(result) -> str`.

- [ ] **Step 1: Write the failing tests** — append:

```python
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
```

- [ ] **Step 2: Run to verify it fails** — `AttributeError: 'Walk' object has no attribute 'evaluate'`.

- [ ] **Step 3: Append the implementation** — module level `Result`/`describe` and these `Walk` methods:

```python
class Result(object):
    """The new cycle: world matrices (J, N+1, 4, 4) in the source's world, N, and what happened."""

    def __init__(self, worlds, frames, info):
        self.worlds, self.frames, self.info = worlds, frames, info


def describe(result):
    info = result.info
    text = "%d frames, stride %.1f cm, %.2f m/s" % (info["frames"], info["stride_cm"], info["speed"])
    if info["lowered"] > 0.005:
        text += " | pelvis lowered %.1f cm for the reach" % info["lowered"]
    if info["short"] > 0.005:
        text += " | a foot falls %.1f cm short of its step" % info["short"]
    return text
```

```python
    # (methods of Walk)

    def evaluate(self, given=None):
        """The cycle rebuilt from knobs (the spec's model); the defaults give the source back."""
        k = knobs(**(given or {}))
        P = self.P
        n = max(int(round(k["tempo"])), 4) if k["tempo"] >= 1.0 else P
        ctx = {"k": k, "ex": k["exaggeration"], "travel2": self.travel * k["stride"],
               "lag": max(0.0, k["overlap"] + WEIGHT_LAG * k["weight"]) * P / float(n),
               "beta": min(max(WEIGHT_WARP * k["weight"], -0.9), 0.9),
               "phi0": self.low_phase + WEIGHT_WARP_AFTER - 0.25, "delta": 0.0}
        times = [(f / float(n), f * P / float(n)) for f in range(n + 1)]
        ctx["delta"] = self._lowering(times, ctx)
        worlds = np.tile(np.eye(4), (len(self.names), n + 1, 1, 1))
        short = 0.0
        for f, (phi, tau) in enumerate(times):
            worlds[:, f], frame_short = self._frame(phi, tau, ctx)
            short = max(short, frame_short)
        flat = ctx["travel2"] - np.dot(ctx["travel2"], self.up) * self.up
        info = {"frames": n, "stride_cm": float(np.linalg.norm(flat)) / 2.0,
                "speed": float(np.linalg.norm(flat)) / (n / self.fps) / 100.0, "lowered": ctx["delta"],
                "short": short, "lag": ctx["lag"] * n / float(P), "knobs": k}
        return Result(worlds, n, info)

    def foot_target(self, side, tau, stride, width, lift):
        """The new foot at source time tau: (world rotation, ankle position). Stance: the source's foot
        moved with its footprint; swing: the source's swing between the new footprints, its lift scaled."""
        foot, j, P = self.feet[side], self.index["foot_" + side], self.P
        rot, src = self.wrot(j, tau), self.wpos(j, tau)
        travel2 = self.travel * stride
        k = math.floor((tau - foot.on) / P)
        r = tau - foot.on - k * P
        sign = 1.0 if side == "l" else -1.0
        shift = ((travel2 - self.travel) * ((foot.mid + k * P) / P)
                 + (stride - 1.0) * foot.coords[0] * self.fwd + sign * width / 2.0 * self.side)
        if r <= foot.length + 1e-9:
            return rot, src + shift
        t_off, t_on = foot.on + foot.length + k * P, foot.on + (k + 1) * P
        p_off, p_on = self.wpos(j, t_off), self.wpos(j, t_on)
        x, x_off, x_on = (float(np.dot(p, self.fwd)) for p in (src, p_off, p_on))
        s = (x - x_off) / (x_on - x_off) if abs(x_on - x_off) > 1e-9 else (r - foot.length) / (P - foot.length)
        print_k = self.wpos(j, foot.mid + k * P)
        base = (1.0 - s) * (p_off - print_k) + s * (p_on - print_k - self.travel)
        lift_up = float(np.dot(src - print_k - s * self.travel - base, self.up))
        return rot, src + shift + s * (travel2 - self.travel) + (lift - 1.0) * lift_up * self.up

    def _body(self, phi, tau, ctx):
        """The root's and the pelvis's new (rotation, position)."""
        k, ex = ctx["k"], ctx["ex"]
        line2 = self.origin + ctx["travel2"] * phi
        out = {}
        for name, mean in (("root", self.root_mean), ("pelvis", self.pelvis_mean)):
            j = self.index[name]
            dev = periodic_cr(self.pdev[j], tau) @ self.basis.T
            along = mean[0] + k["stride"] * ex * (dev[0] - mean[0])
            aside = mean[1] + k["sway"] * ex * (dev[1] - mean[1])
            if name == "pelvis":
                v = float(periodic_cr(self.pdev[j], warp(phi, ctx["beta"], ctx["phi0"]) * self.P) @ self.up) - mean[2]
                height = mean[2] + k["bob"] * ex * shape_bob(v, k["weight"]) - ctx["delta"]
                rot = self.wrot(j, tau, k["pelvis_rot"] * ex)
            else:
                height, rot = dev[2], self.wrot(j, tau)
            out[name] = (rot, line2 + np.array([along, aside, height]) @ self.basis)
        return out

    def _lowering(self, times, ctx):
        """The one drop of the pelvis that lets every frame's legs reach without straightening past the
        source's straightest (0 when nothing needs it)."""
        k, drop = ctx["k"], 0.0
        for phi, tau in times:
            pelvis_rot, pelvis_pos = self._body(phi, tau, ctx)["pelvis"]
            for side in SIDES:
                th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
                hip = self.lt_at(th, tau) @ pelvis_rot + pelvis_pos
                ankle = self.foot_target(side, tau, k["stride"], k["width"], k["lift"] * ctx["ex"])[1]
                limit = self.reach[side] * (np.linalg.norm(self.lt_at(ca, tau)) + np.linalg.norm(self.lt_at(fo, tau)))
                q = ankle - hip
                if np.linalg.norm(q) <= limit * (1.0 + 1e-9):
                    continue
                qu = float(np.dot(q, self.up))
                disc = qu * qu - (float(np.dot(q, q)) - limit * limit)
                if disc >= 0.0:
                    drop = max(drop, -qu - math.sqrt(disc))
        return max(drop, 0.0)

    def _frame(self, phi, tau, ctx):
        """Every joint's new world at one frame (parents first, helpers last); and how far a foot fell short."""
        k, ex = ctx["k"], ctx["ex"]
        rots, poss = [None] * len(self.names), [None] * len(self.names)
        body = self._body(phi, tau, ctx)
        gains = {"spine": k["spine"] * ex, "arm": k["arms"] * ex}
        short = 0.0
        for j in self.order:
            if rots[j] is not None:
                continue
            kind, name, p = self.kind[j], self.names[j], self.parents[j]
            if kind in ("root", "pelvis"):
                rots[j], poss[j] = body[name]
            elif kind == "world":
                rots[j], poss[j] = self.wrot(j, tau), self.wpos(j, tau) + (ctx["travel2"] - self.travel) * phi
            elif kind == "leg":
                short = max(short, self._leg(name[-1], tau, rots, poss, ctx))
            elif kind == "helper" and j in self.follows:
                b, rel = self.follows[j]
                m = rel @ matrix(rots[b], poss[b])
                rots[j], poss[j] = m[:3, :3], m[3, :3]
            else:
                t = tau - self.lag[j] * ctx["lag"]
                if kind == "head":
                    rots[j] = self.wrot(j, t, k["head"] * ex)
                else:
                    rots[j] = self.lrot_at(j, t, gains.get(kind, 1.0)) @ rots[p]
                poss[j] = self.lt_at(j, t) @ rots[p] + poss[p]
        out = np.tile(np.eye(4), (len(self.names), 1, 1))
        for j in range(len(self.names)):
            out[j, :3, :3], out[j, 3, :3] = rots[j], poss[j]
        return out, short

    def _leg(self, side, tau, rots, poss, ctx):
        """Thigh, calf and foot by IK from the new hip to the new foot; each bone turned by the rotation
        taking its source (direction, leg plane) onto the new one. Returns how far the foot fell short."""
        k = ctx["k"]
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        pelvis = self.parents[th]
        hip = self.lt_at(th, tau) @ rots[pelvis] + poss[pelvis]
        foot_rot, ankle = self.foot_target(side, tau, k["stride"], k["width"], k["lift"] * ctx["ex"])
        l1, l2 = float(np.linalg.norm(self.lt_at(ca, tau))), float(np.linalg.norm(self.lt_at(fo, tau)))
        h, kn, a = self.wpos(th, tau), self.wpos(ca, tau), self.wpos(fo, tau)
        e = _unit(a - h)
        bend = (kn - h) - np.dot(kn - h, e) * e
        bend = _unit(bend) if np.linalg.norm(bend) > 1e-6 else _unit(self.fwd - np.dot(self.fwd, e) * e)
        knee, reached, short = two_bone(hip, ankle, l1, l2, bend, self.reach[side])
        e2 = _unit(reached - hip)
        bend2 = _unit((knee - hip) - np.dot(knee - hip, e2) * e2)
        n_src, n_new = _unit(np.cross(e, bend)), _unit(np.cross(e2, bend2))
        rots[th] = self.wrot(th, tau) @ align(_unit(kn - h), n_src, _unit(knee - hip), n_new)
        rots[ca] = self.wrot(ca, tau) @ align(_unit(a - kn), n_src, _unit(reached - knee), n_new)
        rots[fo] = foot_rot
        poss[th], poss[ca], poss[fo] = hip, knee, reached
        return short
```

- [ ] **Step 4: Run the tests** — Expected: all PASS.

- [ ] **Step 5: Commit** — message `feat(walk): evaluate - the new cycle from the knobs`.

### Task 4: Maya — read the cycle, the copy, the keys; the standalone verify on the animator's clip

**Files:**
- Create: `docs/superpowers/plans/walkparam/skeldar_walk.py`
- Create: `docs/superpowers/plans/walkparam/verify_walk.py`

**Interfaces:**
- Consumes: `walkmodel` (Tasks 1-3), loaded by path as `skeldar_walkmodel`.
- Produces: `source_root_of(node) -> (root, copy_or_None)`, `walk_for(root) -> (Walk, Source)`,
  `update(root, given=None, offset=None) -> (copy, Result, line)`, `copies_of(uuid)`, `delete_copies(root)`,
  `read_source(root) -> (Clip, Source)`; constants `MARKER = "skeldarWalk"`, `SUFFIX = "_walk"`.

- [ ] **Step 1: Write `verify_walk.py`** (the failing proof): mayapy standalone, a temp copy of
  `C:/Users/MY PC/Desktop/Walk_01.fbx` imported with `FBXImport` into an ntsc scene; gates — the analysis
  (31 frames, stride 88.5 cm, stance found for both feet); the defaults equal the source on every joint
  and frame (copy world minus the offset, 1e-3); stride 0.7 / 1.3: travel = k . 176.95, stance feet still
  (no worse than the source's own slide), bone lengths, loop seam; tempo 25 / 40: N+1 keys and the seam;
  lift 2; width 10; bob 0 / 2; sway 0; arms 0 / 2; head 0; overlap 3 (the hand's peak 3 frames later);
  weight 1 (pelvis lower, knees bent more at contact); exaggeration 0; the source's curves unchanged
  (values sampled before and after); one Ctrl+Z puts the previous keys back. Every gate prints its number.
- [ ] **Step 2: Run it** — `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk.py`
  — expected: FAIL (`skeldar_walk.py` missing).
- [ ] **Step 3: Write `skeldar_walk.py`** — `read_source` (joints parents first, curves per channel, the
  key range whole, worlds by `getAttr(worldMatrix, time=)`, fps from the time unit, the top's world;
  refuses non-cm scenes and a moving top), `source_root_of`, `copies_of` (walks transforms, asks
  `attributeQuery` — never `ls("*.attr")`, trap 70), `make_copy` (`duplicate` of the top, or of the root
  into a new group when it stands at world level; the marker; placed `offset` along `side`),
  `channel_values` (local = W . W_parent^-1, the parent the source top's world for the root;
  `R = RA^-1 . L . JO^-1`; `MEulerRotation.decompose(m, order)` then `closestSolution` of the previous
  frame), `write_curves` (old input curves deleted with cmds, a new `animCurveTL/TA` created and connected
  with cmds, keys through `MFnAnimCurve.addKeys` with auto tangents — measured 0.05 s for 540 curves,
  Ctrl+Z removes them), `update` (one undo chunk; the marker = JSON {source, knobs, offset, version}).
- [ ] **Step 4: Run the verify until every gate passes**; record the numbers for the docs.
- [ ] **Step 5: Commit** both files — message `feat(walk): the copy in Maya and the verify on Walk_01`.

### Task 5: The window and the drop handler

**Files:**
- Modify: `docs/superpowers/plans/walkparam/skeldar_walk.py` (append the window)
- Test: `tests/test_walkmodel.py` — a `WindowTests` class on a recording fake `cmds` (sliders named for
  every knob with the spec's ranges; the tempo slider's range P/2..2P set by Analyse).

- [ ] **Step 1: Write the failing window test** (fake cmds records `floatSliderGrp`/`intSliderGrp`
  creations by name; `show()` builds one per knob; `given_from_window()` maps them back to knob names).
- [ ] **Step 2: Run it** — FAIL (`show` missing).
- [ ] **Step 3: Write the window** — groups Step / Pelvis / Upper body / Weight, sliders with
  `changeCommand=slider_changed` (a released slider updates the copy), Offset field, Analyse / Update /
  Reset / Delete copy, the status line; Analyse reads the selection (a copy restores its knobs into the
  sliders); every press goes through `_run` (a Refusal or an exception lands on the status line);
  `onMayaDroppedPythonFile` reloads this module and the model and shows the window (trap 220).
- [ ] **Step 4: Run the whole suite** — `mayapy -m unittest tests.test_walkmodel -v` — PASS; re-run
  `verify_walk.py` — PASS.
- [ ] **Step 5: Commit** — message `feat(walk): the window and the drop handler`.

### Task 6: Docs

**Files:**
- Modify: `CLAUDE.md` (a section «Parametric walk» after «Physical stop»: what, where, the measured clip,
  the model, the knobs, the proof numbers, the traps met)
- Modify: `docs/superpowers/specs/2026-10-12-parametric-walk-design.md` (an addendum with the verify's
  numbers and anything the build changed)

- [ ] **Step 1: Write both.**
- [ ] **Step 2: Commit only this feature's hunks** (CLAUDE.md may hold a peer's edits: stage
  `HEAD:CLAUDE.md` + this section through `git hash-object -w` / `git update-index --cacheinfo`, commit
  in the same command, check `git show --stat`).
