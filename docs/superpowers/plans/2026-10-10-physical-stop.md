# Physical Stop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone Maya script that builds a physical stop between an object's last two keys - the path
with an overshoot, the top lagging behind the bottom, a sink and a sway - from a model fitted to the
animator's cube.

**Architecture:** One file, `docs/superpowers/plans/physstop/skeldar_physstop.py`, in four layers: the model
(stdlib `math`: the path, three springs, the settle and the fade), the geometry (`maya.api.OpenMaya` math
classes: up axis, bottom point, the transform composed and decomposed with pivots), the scene (`cmds`: the
two keys, the marker, writing and restoring keys), the window (`cmds`). A calibration script fits the
model's constants to `cube_reference.json`; a mayapy standalone verify rebuilds the cube from two keys.

**Tech Stack:** Maya 2027 mayapy (Python 3), `maya.cmds`, `maya.api.OpenMaya`, stdlib `unittest`; numpy only
in the calibration script.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-10-physical-stop-design.md`.
- The script is NOT in `SkeldarAnim/` and nothing in the plugin changes.
- Units: frames (the scene's rate), cm, degrees. Maya matrices are row-vector (`p * M`).
- The model section imports nothing but stdlib; `maya.cmds` and `maya.api.OpenMaya` are imported inside
  functions, so the model is testable with no Maya and the module loads in a plain mayapy.
- Keys on every frame on translate/rotate XYZ, auto tangents; one undo chunk per press.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_physstop -v` from the
  repo root (no system Python).
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; write them to a file and
  `git commit -F` (PowerShell here-strings mangle quotes).

---

### Task 1: The model - path, springs, settle, fade

**Files:**
- Create: `docs/superpowers/plans/physstop/skeldar_physstop.py`
- Test: `tests/test_physstop.py`

**Interfaces:**
- Produces: `params(**given) -> dict` (keys `amplitude, overlap, weight, swing, sway`), `damping(weight) -> float`,
  `Path(t_a, t_b, amplitude, swing, zeta)` with `.at(t) -> (p, dp)`, `.overshoot`, `.clamped`;
  `solve(t_a, t_b, reach, lateral, height, given=None) -> Transition` with `.rows` (list of `Row(t, p, tilt,
  sink, sway, yaw)` - tilt/yaw deg, sink/sway cm), `.end`, `.peak_tilt`, `.peak_sink`, `.peak_sway`,
  `.overshoot`, `.clamped`, `.params`.

- [ ] **Step 1: Write the failing tests**

```python
"""The physical stop: the model, the geometry and the cube it was fitted to."""

import importlib.util
import json
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(os.path.dirname(HERE), "docs", "superpowers", "plans", "physstop")
SCRIPT = os.path.join(FOLDER, "skeldar_physstop.py")


def load():
    spec = importlib.util.spec_from_file_location("skeldar_physstop_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ps = load()


class PathTests(unittest.TestCase):

    def path(self, amplitude=4.5, swing=4.75, weight=1.0, t_a=0.0, t_b=9.0):
        return ps.Path(t_a, t_b, amplitude, swing, ps.damping(weight))

    def test_starts_at_rest_and_passes_b_at_its_key(self):
        path = self.path()
        self.assertEqual(path.at(0.0), (0.0, 0.0))
        p, _ = path.at(9.0)
        self.assertAlmostEqual(p, 1.0, places=12)

    def test_velocity_is_continuous_at_b(self):
        path = self.path()
        _, before = path.at(9.0 - 1e-7)
        _, after = path.at(9.0 + 1e-7)
        self.assertAlmostEqual(before, after, places=5)
        self.assertGreater(before, 0.0)

    def test_first_overshoot_is_the_amplitude(self):
        path = self.path(amplitude=4.5)
        peak = max(path.at(9.0 + i / 100.0)[0] for i in range(1, 1000))
        self.assertAlmostEqual(peak - 1.0, 0.045, places=4)
        self.assertAlmostEqual(path.overshoot, 0.045, places=9)
        self.assertFalse(path.clamped)

    def test_swing_time_is_half_a_period(self):
        path = self.path(swing=5.0)
        crests = []
        prev = path.at(9.0)[1]
        for i in range(1, 4000):
            t = 9.0 + i / 100.0
            v = path.at(t)[1]
            if prev > 0 >= v or prev < 0 <= v:
                crests.append(t)
            prev = v
        self.assertAlmostEqual(crests[1] - crests[0], 5.0, places=1)
        self.assertAlmostEqual(crests[2] - crests[1], 5.0, places=1)

    def test_heavier_rings_longer(self):
        def swings(weight):
            path = self.path(weight=weight)
            first = path.at(9.0 + math.atan2(path.w, path.sigma) / path.w)[0] - 1.0
            later = path.at(9.0 + math.atan2(path.w, path.sigma) / path.w + 2 * math.pi / path.w)[0] - 1.0
            return later / first
        self.assertGreater(swings(2.0), swings(1.0))
        self.assertGreater(swings(1.0), swings(0.5))

    def test_never_overshoots_on_the_way(self):
        path = self.path(amplitude=20.0, t_b=2.0)
        self.assertTrue(path.clamped)
        values = [path.at(i / 100.0)[0] for i in range(0, 201)]
        self.assertTrue(all(b >= a - 1e-12 for a, b in zip(values, values[1:])))
        self.assertLessEqual(max(values), 1.0 + 1e-12)

    def test_no_amplitude_no_overshoot(self):
        path = self.path(amplitude=0.0)
        self.assertEqual(path.at(15.0), (1.0, 0.0))


class ParamTests(unittest.TestCase):

    def test_defaults_and_clamping(self):
        p = ps.params()
        self.assertEqual(sorted(p), ["amplitude", "overlap", "swing", "sway", "weight"])
        self.assertEqual(ps.params(weight=99.0)["weight"], ps.RANGES["weight"][1])
        self.assertEqual(ps.params(swing=0.0)["swing"], ps.RANGES["swing"][0])

    def test_damping_follows_weight(self):
        self.assertAlmostEqual(ps.damping(1.0), ps.ZETA)
        self.assertAlmostEqual(ps.damping(2.0), ps.ZETA / 2.0)
        self.assertEqual(ps.damping(0.01), 0.9)


class SolveTests(unittest.TestCase):

    def solve(self, **given):
        return ps.solve(0.0, 9.0, 32.36 / 11.645, 32.36 / 11.645, 11.645, given)

    def test_rows_cover_a_to_the_end_frame_by_frame(self):
        tr = self.solve()
        times = [r.t for r in tr.rows]
        self.assertEqual(times[0], 0.0)
        self.assertEqual(times, [float(i) for i in range(len(times))])
        self.assertEqual(times[-1], tr.end)
        self.assertGreater(tr.end, 9.0)

    def test_ends_exactly_on_b(self):
        last = self.solve().rows[-1]
        self.assertEqual((last.p, last.tilt, last.sink, last.sway, last.yaw), (1.0, 0.0, 0.0, 0.0, 0.0))

    def test_starts_exactly_on_a(self):
        first = self.solve().rows[0]
        self.assertEqual((first.p, first.tilt, first.sink, first.sway, first.yaw), (0.0, 0.0, 0.0, 0.0, 0.0))

    def test_signs_the_top_lags_it_sinks_down_and_sways_left(self):
        tr = self.solve()
        mid = [r for r in tr.rows if r.t == 5.0][0]
        self.assertGreater(mid.tilt, 0.0)
        self.assertGreater(mid.sink, 0.0)
        self.assertGreater(mid.sway, 0.0)
        self.assertGreater(mid.yaw, 0.0)
        left = self.solve(sway=-1.0)
        self.assertLess([r for r in left.rows if r.t == 5.0][0].sway, 0.0)

    def test_controls_scale_what_they_name(self):
        base = self.solve()
        self.assertGreater(self.solve(overlap=2.0).peak_tilt, 1.5 * base.peak_tilt)
        self.assertGreater(self.solve(weight=2.0).peak_sink, 1.5 * base.peak_sink)
        self.assertEqual(self.solve(overlap=0.0).peak_tilt, 0.0)
        self.assertEqual(self.solve(sway=0.0).peak_sway, 0.0)

    def test_heavier_settles_later(self):
        self.assertGreater(self.solve(weight=2.0).end, self.solve(weight=1.0).end)
        self.assertGreater(self.solve(weight=1.0).end, self.solve(weight=0.5).end)

    def test_no_travel_no_springs(self):
        tr = ps.solve(0.0, 9.0, 0.0, 0.0, 10.0, None)
        self.assertEqual(tr.peak_tilt + tr.peak_sink + tr.peak_sway, 0.0)

    def test_fractional_keys(self):
        tr = ps.solve(0.5, 9.25, 2.0, 2.0, 10.0, None)
        self.assertEqual(tr.rows[0].t, 0.5)
        self.assertEqual(tr.rows[1].t, 1.0)
        self.assertEqual(tr.rows[-1].t, tr.end)
        self.assertEqual(tr.end, int(tr.end))
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_physstop -v`
Expected: ERROR - `FileNotFoundError` for `skeldar_physstop.py`.

- [ ] **Step 3: Write the model**

```python
"""Physical stop - a pose-to-pose transition that stops like a physical object.

Select objects whose LAST TWO KEYS are the pose they leave (A) and the pose they come to (B), and press
Apply: the object leaves A from rest, passes B at B's key with speed, overshoots and settles into B, its top
lagging behind its bottom, sinking under its weight and swaying aside - a model fitted to the animator's
cube (docs/superpowers/specs/2026-10-10-physical-stop-design.md).

Drop this file into a Maya viewport to open the window, or exec it in the Script Editor.
"""

import json
import math

# ---------------------------------------------------------------------------------------------------------
# 1. The model (stdlib)
# ---------------------------------------------------------------------------------------------------------

# The cube's rule, fitted by calibrate_physstop.py against cube_reference.json.
ZETA = 0.32          # damping of every swing at weight 1
K_TILT = 45.4        # deg of tilt per object height per frame of speed, at overlap 1
K_SINK = 0.51        # sink, in heights, per object height per frame of speed, at weight 1
K_SWAY = 0.21        # sway, in heights, per object height per frame of speed, at sway 1
SWAY_RATE = 0.74     # the sway's frequency against the other springs'
K_YAW = 52.0         # deg of yaw per object height of sway

TILT_LIMIT = 80.0    # deg: the tilt's drive saturates here (tanh), whatever the speed
DRIFT_LIMIT = 0.5    # heights: the sink's and the sway's drives saturate here
SUBSTEPS = 16        # integration steps per frame
SETTLE_SHARE = 0.02  # settled when every component stays within this share of its own peak
FADE_SHARE = 0.3     # the last share of the settle fades every residual to 0
MAX_TAIL = 400       # frames simulated after B at most
FALLBACK_HEIGHT = 10.0

DEFAULTS = (("amplitude", 4.5), ("overlap", 1.0), ("weight", 1.0), ("swing", 4.75), ("sway", 1.0))
RANGES = {
    "amplitude": (0.0, 20.0),   # the first overshoot, % of the path
    "overlap": (0.0, 3.0),      # the top's lag
    "weight": (0.2, 5.0),       # how long it rings, how deep it sinks
    "swing": (1.0, 20.0),       # frames of one swing
    "sway": (-3.0, 3.0),        # sideways drift and yaw; + is left of the motion
}


def params(**given):
    """The five controls, defaults filled in, each clamped to its range."""
    out = {}
    for name, default in DEFAULTS:
        low, high = RANGES[name]
        value = given.get(name)
        out[name] = min(high, max(low, float(default if value is None else value)))
    return out


def damping(weight):
    """A heavier object rings longer: the damping falls with the weight."""
    return min(0.9, max(0.05, ZETA / max(weight, 1e-6)))


class Path(object):
    """The progress p(t) from A (0) to B (1): an ease that passes B at t_b with speed, then a swing."""

    def __init__(self, t_a, t_b, amplitude, swing, zeta):
        self.t_a = float(t_a)
        self.t_b = float(t_b)
        span = self.t_b - self.t_a
        self.w = math.pi / swing
        self.sigma = zeta * self.w / math.sqrt(1.0 - zeta * zeta)
        tau = math.atan2(self.w, self.sigma) / self.w        # the first crest after B
        crest = math.exp(-self.sigma * tau) * math.sin(self.w * tau)
        slope = amplitude / 100.0 * self.w / crest * span
        self.clamped = slope > 3.0                            # past 3 the ease would overshoot on the way
        self.m = min(slope, 3.0)
        self.v_b = self.m / span
        self.overshoot = self.v_b / self.w * crest

    def at(self, t):
        """(p, dp/dt) at frame t."""
        if t <= self.t_a:
            return 0.0, 0.0
        if t <= self.t_b:
            span = self.t_b - self.t_a
            u = (t - self.t_a) / span
            p = 3.0 * u * u - 2.0 * u ** 3 + self.m * (u ** 3 - u * u)
            v = (6.0 * u - 6.0 * u * u + self.m * (3.0 * u * u - 2.0 * u)) / span
            return p, v
        if self.v_b == 0.0:
            return 1.0, 0.0
        tau = t - self.t_b
        fade = math.exp(-self.sigma * tau)
        k = self.v_b / self.w
        s, c = math.sin(self.w * tau), math.cos(self.w * tau)
        return 1.0 + k * fade * s, k * fade * (self.w * c - self.sigma * s)


class Row(object):
    __slots__ = ("t", "p", "tilt", "sink", "sway", "yaw")

    def __init__(self, t, p, tilt, sink, sway, yaw):
        self.t, self.p, self.tilt, self.sink, self.sway, self.yaw = t, p, tilt, sink, sway, yaw


class Transition(object):
    """Every frame from A to the settle: the path's progress, the tilt (deg, + = the top behind the
    motion), the sink (cm, down), the sway (cm, + = left of the motion) and the yaw (deg, about up)."""

    def __init__(self, rows, end, path, given):
        self.rows = rows
        self.end = end
        self.overshoot = path.overshoot
        self.clamped = path.clamped
        self.params = given
        self.peak_tilt = max(abs(r.tilt) for r in rows)
        self.peak_sink = max(abs(r.sink) for r in rows)
        self.peak_sway = max(abs(r.sway) for r in rows)


def _frames(t_a, end):
    """t_a, then every whole frame after it up to `end`."""
    out = [float(t_a)]
    f = math.floor(t_a) + 1
    while f <= end + 1e-9:
        out.append(float(f))
        f += 1
    return out


def _step(state, drive, omega, zeta, dt):
    x, v = state
    v += (omega * omega * (drive - x) - 2.0 * zeta * omega * v) * dt
    state[0], state[1] = x + v * dt, v


def simulate(path, end, reach, lateral, given, zeta):
    """(t, p, tilt deg, sink heights, sway heights) on every frame from A to `end`. The bottom's speed in
    heights per frame drives three springs at rest at A: the tilt by the horizontal speed, the sink by the
    speed, the sway (slower) by the horizontal speed."""
    omega = path.w / math.sqrt(1.0 - zeta * zeta)
    slow = omega * SWAY_RATE
    tilt, sink, sway = [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]
    out = []
    t = path.t_a
    for f in _frames(path.t_a, end):
        steps = int(math.ceil((f - t) * SUBSTEPS - 1e-9)) if f > t else 0
        if steps:
            dt = (f - t) / steps
            for i in range(steps):
                _, v = path.at(t + dt * (i + 0.5))
                ahead = v * lateral
                speed = abs(v)
                _step(tilt, TILT_LIMIT * math.tanh(K_TILT * given["overlap"] * ahead / TILT_LIMIT),
                      omega, zeta, dt)
                _step(sink, DRIFT_LIMIT * math.tanh(K_SINK * given["weight"] * speed * reach / DRIFT_LIMIT),
                      omega, zeta, dt)
                _step(sway, DRIFT_LIMIT * math.tanh(K_SWAY * given["sway"] * abs(ahead) / DRIFT_LIMIT),
                      slow, zeta, dt)
            t = f
        out.append((f, path.at(f)[0], tilt[0], sink[0], sway[0]))
    return out


def settle_frame(raw, t_b):
    """The first whole frame after B from which every component stays within SETTLE_SHARE of its peak."""
    residual = [((r[1] - 1.0) if r[0] >= t_b else 0.0, r[2], r[3], r[4]) for r in raw]
    peaks = [max(abs(c[k]) for c in residual) for k in range(4)]
    last = None
    for row, comps in zip(raw, residual):
        if row[0] > t_b and any(p > 1e-9 and abs(c) > SETTLE_SHARE * p for c, p in zip(comps, peaks)):
            last = row[0]
    first_after = math.floor(t_b) + 1.0 if t_b != math.floor(t_b) else t_b
    return max(first_after, (last + 1.0) if last is not None else first_after)


def _smoothstep(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def solve(t_a, t_b, reach, lateral, height, given=None):
    """The transition between keys at t_a and t_b. reach: the bottom's travel A->B in object heights;
    lateral: its horizontal part; height: the object's height in cm."""
    given = params(**(given or {}))
    zeta = damping(given["weight"])
    path = Path(t_a, t_b, given["amplitude"], given["swing"], zeta)
    raw = simulate(path, math.floor(t_b) + MAX_TAIL, reach, lateral, given, zeta)
    end = settle_frame(raw, t_b)
    start = max(t_b, end - max(2.0, FADE_SHARE * (end - t_b)))
    rows = []
    for t, p, tilt, sink, sway in raw:
        if t > end + 1e-9:
            break
        keep = 1.0
        if t >= start and end > start:
            keep = 1.0 - _smoothstep((t - start) / (end - start))
        if t >= t_b:
            p = 1.0 + (p - 1.0) * keep
        tilt, sink, sway = tilt * keep, sink * keep, sway * keep
        rows.append(Row(t, p, tilt, sink * height, sway * height, K_YAW * sway))
    rows[-1] = Row(end, 1.0, 0.0, 0.0, 0.0, 0.0)
    return Transition(rows, end, path, given)


if __name__ == "__main__":
    pass
```

- [ ] **Step 4: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_physstop -v`
Expected: every test in `PathTests`, `ParamTests`, `SolveTests` passes.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/physstop/skeldar_physstop.py tests/test_physstop.py
git commit -F msg.txt   # "feat(physstop): the model - path, springs, settle and fade"
```

---

### Task 2: The geometry - up axis, bottom, the transform both ways, the secondary motion

**Files:**
- Modify: `docs/superpowers/plans/physstop/skeldar_physstop.py` (a section after the model)
- Test: `tests/test_physstop.py`

**Interfaces:**
- Consumes: `Transition.rows` (Task 1).
- Produces: `UP`, `AXES`, `IDENTITY_FIXED` (dict: `scale, shear, scalePivot, scalePivotTranslate, rotatePivot,
  rotatePivotTranslate, rotateAxis`, each a 3-tuple), `up_axis(rows, choice="Auto") -> (index, sign)`,
  `bottom_and_height(box_min, box_max, index, sign, rows) -> ((x, y, z), height)`,
  `local_matrix(translate, rotate, order, fixed) -> MMatrix`,
  `channels_from_local(matrix, order, fixed, near) -> ((tx, ty, tz), (rx, ry, rz))`,
  `secondary(bottom, heading, tilt, yaw, sink, sway) -> MMatrix`,
  `channel_frames(transition, pose_a, pose_b, order, fixed, parent_at, bottom, heading) -> [(t, (t3), (r3))]`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_physstop.py`)

```python
try:
    import maya.api.OpenMaya as om
except ImportError:   # pragma: no cover
    om = None


def close(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


class AxisTests(unittest.TestCase):

    def test_auto_picks_the_axis_nearest_world_up_with_its_sign(self):
        rows = ((1, 0, 0), (0, 0, -1), (0, 1, 0))          # local Z points up
        self.assertEqual(ps.up_axis(rows), (2, 1.0))
        rows = ((1, 0, 0), (0, -1, 0), (0, 0, 1))          # local Y points down
        self.assertEqual(ps.up_axis(rows), (1, -1.0))

    def test_override(self):
        self.assertEqual(ps.up_axis(((1, 0, 0), (0, 1, 0), (0, 0, 1)), "-X"), (0, -1.0))

    def test_bottom_is_the_low_end_and_height_is_world(self):
        rows = ((4.0, 0, 0), (0, 11.0, 0), (0, 0, 3.0))
        bottom, height = ps.bottom_and_height((-0.5, -0.5, -0.5), (0.5, 0.5, 0.5), 1, 1.0, rows)
        self.assertEqual(bottom, (0.0, -0.5, 0.0))
        self.assertAlmostEqual(height, 11.0)
        bottom, _ = ps.bottom_and_height((-0.5, -0.5, -0.5), (0.5, 0.5, 0.5), 1, -1.0, rows)
        self.assertEqual(bottom, (0.0, 0.5, 0.0))


@unittest.skipIf(om is None, "needs maya.api.OpenMaya")
class TransformTests(unittest.TestCase):

    FIXED = {
        "scale": (4.1, 11.6, 3.9), "shear": (0.1, 0.0, 0.05), "scalePivot": (-0.2, 0.3, 0.1),
        "scalePivotTranslate": (0.05, 0.1, 0.0), "rotatePivot": (0.1, -0.5, 0.2),
        "rotatePivotTranslate": (0.3, 0.0, -0.1), "rotateAxis": (5.0, -7.0, 12.0)}

    def test_round_trip_in_every_rotate_order(self):
        for order in range(6):
            m = ps.local_matrix((1.0, 2.0, -3.0), (10.0, -20.0, 30.0), order, self.FIXED)
            t, r = ps.channels_from_local(m, order, self.FIXED, (10.0, -20.0, 30.0))
            self.assertTrue(close(t, (1.0, 2.0, -3.0), 1e-9), (order, t))
            self.assertTrue(close(r, (10.0, -20.0, 30.0), 1e-9), (order, r))

    def test_euler_stays_near_its_neighbour(self):
        m = ps.local_matrix((0, 0, 0), (0.0, 370.0, 0.0), 0, ps.IDENTITY_FIXED)
        _, r = ps.channels_from_local(m, 0, ps.IDENTITY_FIXED, (0.0, 369.0, 0.0))
        self.assertTrue(close(r, (0.0, 370.0, 0.0), 1e-9), r)

    def test_tilt_moves_the_top_back_against_the_motion(self):
        heading = om.MVector(0, 0, -1)
        g = ps.secondary(om.MPoint(0, 0, 0), heading, 30.0, 0.0, 0.0, 0.0)
        top = om.MPoint(0, 10, 0) * g
        self.assertAlmostEqual(top.z, 10 * math.sin(math.radians(30)))
        self.assertAlmostEqual((om.MPoint(0, 0, 0) * g).z, 0.0)   # the bottom stays

    def test_sink_is_down_and_sway_is_left(self):
        heading = om.MVector(0, 0, -1)                  # facing -Z with Y up, left is -X
        g = ps.secondary(om.MPoint(0, 0, 0), heading, 0.0, 0.0, 2.0, 1.5)
        p = om.MPoint(0, 0, 0) * g
        self.assertTrue(close((p.x, p.y, p.z), (-1.5, -2.0, 0.0), 1e-12))

    def test_yaw_is_about_world_up_through_the_bottom(self):
        g = ps.secondary(om.MPoint(5, 0, 0), om.MVector(0, 0, -1), 0.0, 90.0, 0.0, 0.0)
        p = om.MPoint(6, 0, 0) * g
        self.assertTrue(close((p.x, p.y, p.z), (5.0, 0.0, -1.0), 1e-12))

    def test_no_heading_no_tilt_but_still_a_sink(self):
        g = ps.secondary(om.MPoint(0, 0, 0), None, 30.0, 20.0, 1.0, 1.0)
        p = om.MPoint(0, 10, 0) * g
        self.assertTrue(close((p.x, p.y, p.z), (0.0, 9.0, 0.0), 1e-12))

    def test_channel_frames_start_on_a_and_end_on_b(self):
        tr = ps.solve(0.0, 9.0, 2.0, 2.0, 10.0, None)
        pose_a = ((0.0, 5.0, 0.0), (0.0, 0.0, 0.0))
        pose_b = ((0.0, 5.0, -20.0), (3.0, 0.0, 0.0))
        parent = om.MMatrix()
        frames = ps.channel_frames(tr, pose_a, pose_b, 0, ps.IDENTITY_FIXED, lambda t: parent,
                                   (0.0, -0.5, 0.0), om.MVector(0, 0, -1))
        self.assertTrue(close(frames[0][1] + frames[0][2], pose_a[0] + pose_a[1], 1e-9))
        self.assertTrue(close(frames[-1][1] + frames[-1][2], pose_b[0] + pose_b[1], 1e-9))
        self.assertEqual([f[0] for f in frames], [r.t for r in tr.rows])
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_physstop -v`
Expected: `AttributeError: module ... has no attribute 'up_axis'`.

- [ ] **Step 3: Write the geometry** (insert before `if __name__ == "__main__":`)

```python
# ---------------------------------------------------------------------------------------------------------
# 2. The geometry (maya.api.OpenMaya math only)
# ---------------------------------------------------------------------------------------------------------

UP = (0.0, 1.0, 0.0)
AXES = ("Auto", "+X", "-X", "+Y", "-Y", "+Z", "-Z")
IDENTITY_FIXED = {
    "scale": (1.0, 1.0, 1.0), "shear": (0.0, 0.0, 0.0), "scalePivot": (0.0, 0.0, 0.0),
    "scalePivotTranslate": (0.0, 0.0, 0.0), "rotatePivot": (0.0, 0.0, 0.0),
    "rotatePivotTranslate": (0.0, 0.0, 0.0), "rotateAxis": (0.0, 0.0, 0.0)}


def _om():
    import maya.api.OpenMaya as om
    return om


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _length(a):
    return math.sqrt(_dot(a, a))


def up_axis(rows, choice="Auto"):
    """(index, sign) of the object's axis that points up: rows are its three axes in world."""
    if choice and choice != "Auto":
        return "XYZ".index(choice[1]), (1.0 if choice[0] == "+" else -1.0)
    best = max(range(3), key=lambda i: abs(_dot(rows[i], UP)) / max(_length(rows[i]), 1e-12))
    return best, (1.0 if _dot(rows[best], UP) >= 0.0 else -1.0)


def bottom_and_height(box_min, box_max, index, sign, rows):
    """The bottom point in object space (the box's centre at its low end) and the height in world units."""
    centre = [(a + b) / 2.0 for a, b in zip(box_min, box_max)]
    centre[index] = box_min[index] if sign > 0 else box_max[index]
    return tuple(float(c) for c in centre), (box_max[index] - box_min[index]) * _length(rows[index])


def _translation(v):
    om = _om()
    return om.MMatrix(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (v[0], v[1], v[2], 1)))


def local_matrix(translate, rotate, order, fixed):
    """The transform's matrix from its channels, as Maya composes it (pivots, shear, rotate axis)."""
    om = _om()
    space = om.MSpace.kTransform
    tm = om.MTransformationMatrix()
    tm.setScale(fixed["scale"], space)
    tm.setShear(fixed["shear"], space)
    tm.setScalePivot(om.MPoint(fixed["scalePivot"]), space, False)
    tm.setScalePivotTranslation(om.MVector(fixed["scalePivotTranslate"]), space)
    tm.setRotatePivot(om.MPoint(fixed["rotatePivot"]), space, False)
    tm.setRotatePivotTranslation(om.MVector(fixed["rotatePivotTranslate"]), space)
    tm.setRotationOrientation(
        om.MEulerRotation([math.radians(a) for a in fixed["rotateAxis"]]).asQuaternion())
    tm.setRotation(om.MEulerRotation([math.radians(a) for a in rotate], order))
    tm.setTranslation(om.MVector(translate), space)
    return tm.asMatrix()


def channels_from_local(matrix, order, fixed, near):
    """translate and rotate (deg, the euler nearest `near`) that give `matrix`, the rest fixed.
    Maya's matrix is X . R . Tr(rp + rpt + t) with X the part before the rotation, so
    X^-1 . matrix holds R and rp + rpt + t."""
    om = _om()
    pivot = om.MVector(fixed["rotatePivot"]) + om.MVector(fixed["rotatePivotTranslate"])
    head = local_matrix((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), order, fixed) * _translation(-pivot)
    tm = om.MTransformationMatrix(head.inverse() * matrix)
    move = tm.translation(om.MSpace.kTransform) - pivot
    euler = tm.rotation(asQuaternion=True).asEulerRotation()
    euler.reorderIt(order)
    euler = euler.closestSolution(om.MEulerRotation([math.radians(a) for a in near], order))
    return (move.x, move.y, move.z), tuple(math.degrees(a) for a in (euler.x, euler.y, euler.z))


def secondary(bottom, heading, tilt, yaw, sink, sway):
    """The world motion on top of the path: tilt (deg) about the bottom against `heading`, yaw (deg) about
    world up through the bottom, sink (cm) down, sway (cm) to the left. No heading: the sink alone."""
    om = _om()
    up = om.MVector(UP)
    spin = om.MMatrix()
    move = up * -sink
    if heading is not None:
        spin = (om.MQuaternion(math.radians(tilt), heading ^ up).asMatrix()
                * om.MQuaternion(math.radians(yaw), up).asMatrix())
        move = move + (up ^ heading) * sway
    b = om.MVector(bottom.x, bottom.y, bottom.z)
    return _translation(-b) * spin * _translation(b + move)


def _lerp(a, b, p):
    return tuple(x + (y - x) * p for x, y in zip(a, b))


def channel_frames(transition, pose_a, pose_b, order, fixed, parent_at, bottom, heading):
    """Every frame's (t, translate, rotate): the path's pose (channels lerped by p, past B on the
    overshoot), in world, moved by the secondary motion about its bottom, back into the channels."""
    om = _om()
    out = []
    for row in transition.rows:
        move = _lerp(pose_a[0], pose_b[0], row.p)
        turn = _lerp(pose_a[1], pose_b[1], row.p)
        parent = parent_at(row.t)
        world = local_matrix(move, turn, order, fixed) * parent
        base = om.MPoint(bottom) * world
        world = world * secondary(base, heading, row.tilt, row.yaw, row.sink, row.sway)
        t, r = channels_from_local(world * parent.inverse(), order, fixed, turn)
        out.append((row.t, t, r))
    return out
```

- [ ] **Step 4: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_physstop -v`
Expected: all pass, including `TransformTests` (mayapy imports `maya.api.OpenMaya` with no standalone).

- [ ] **Step 5: Commit** - "feat(physstop): the geometry - up axis, bottom, the transform both ways"

---

### Task 3: Calibrate the constants against the cube

**Files:**
- Create: `docs/superpowers/plans/physstop/calibrate_physstop.py`
- Modify: the constants block of `skeldar_physstop.py` (`ZETA`, `K_TILT`, `K_SINK`, `K_SWAY`, `SWAY_RATE`,
  `K_YAW`, the `amplitude` and `swing` defaults) to what the script prints
- Test: `tests/test_physstop.py` (`CubeTests`)

**Interfaces:**
- Consumes: `solve`, `params` (Task 1); `cube_reference.json` (`wm`: 31 row-major 4x4 world matrices).
- Produces: `cube_components(data) -> dict` of per-frame lists `travel, tilt, sink, sway, yaw, t_b, reach, height`
  (in the test file, pure Python), used by the test and the verify.

- [ ] **Step 1: Write the failing test** (append)

```python
def _mul(p, m):
    return tuple(sum(p[k] * m[k][j] for k in range(4)) for j in range(4))


def cube_components(data):
    """The cube decomposed as the model describes it: the bottom's progress along its path, the long
    axis's tilt back (minus pose B's own 2.9 deg lean, carried by the path), the bottom's sink and sway
    (+ = left = -X), the yaw of its local X about world up."""
    mats = [[m[i * 4:(i + 1) * 4] for i in range(4)] for m in data["wm"]]
    bottom = [_mul((0, -0.5, 0, 1), m) for m in mats]
    top = [_mul((0, 0.5, 0, 1), m) for m in mats]
    height = math.dist(bottom[0][:3], top[0][:3])
    start, finish = bottom[0][2], bottom[-1][2]
    travel = [(b[2] - start) / (finish - start) for b in bottom]
    lean = math.degrees(math.atan2(top[-1][2] - bottom[-1][2], top[-1][1] - bottom[-1][1]))
    tilt = [math.degrees(math.atan2(t[2] - b[2], t[1] - b[1])) - lean * max(0.0, p)
            for b, t, p in zip(bottom, top, travel)]
    sink = [bottom[0][1] - b[1] for b in bottom]
    sway = [-b[0] for b in bottom]
    yaw = []
    for m in mats:
        x = m[0][:3]
        yaw.append(math.degrees(math.atan2(-x[2], x[0])))
    t_b = next(i + (1 - travel[i]) / (travel[i + 1] - travel[i]) for i in range(30)
               if travel[i] < 1 <= travel[i + 1])
    return {"travel": travel, "tilt": tilt, "sink": sink, "sway": sway, "yaw": yaw, "t_b": t_b,
            "reach": abs(finish - start) / height, "height": height}


def rms(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


class CubeTests(unittest.TestCase):
    """The defaults ARE the cube: the model run between the cube's own A and the frame it passes B."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FOLDER, "cube_reference.json")) as f:
            cls.cube = cube_components(json.load(f))
        c = cls.cube
        tr = ps.solve(0.0, c["t_b"], c["reach"], c["reach"], c["height"], None)
        rows = {r.t: r for r in tr.rows}
        last = tr.rows[-1]
        cls.model = {k: [] for k in ("travel", "tilt", "sink", "sway", "yaw")}
        for f in range(31):
            r = rows.get(float(f), last)
            cls.model["travel"].append(r.p)
            cls.model["tilt"].append(r.tilt)
            cls.model["sink"].append(r.sink)
            cls.model["sway"].append(r.sway)
            cls.model["yaw"].append(r.yaw)
        cls.end = tr.end

    def test_the_cube_passes_b_at_frame_nine(self):
        self.assertAlmostEqual(self.cube["t_b"], 9.1, places=1)

    def test_travel(self):
        self.assertLess(rms(self.model["travel"], self.cube["travel"]) * 32.36, 0.5)

    def test_tilt(self):
        self.assertLess(rms(self.model["tilt"], self.cube["tilt"]), 2.5)

    def test_sink(self):
        self.assertLess(rms(self.model["sink"], self.cube["sink"]), 0.2)

    def test_sway(self):
        self.assertLess(rms(self.model["sway"], self.cube["sway"]), 0.3)

    def test_yaw(self):
        self.assertLess(rms(self.model["yaw"], self.cube["yaw"]), 1.2)

    def test_settles_where_the_cube_does(self):
        self.assertTrue(24 <= self.end <= 36, self.end)
```

- [ ] **Step 2: Run** - Expected: the cube tests pass or fail by a margin; record the numbers.

- [ ] **Step 3: Write the calibration script**

```python
"""Fit the physical stop's constants to the animator's cube (mayapy, numpy).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/physstop/calibrate_physstop.py

Prints the constants block for skeldar_physstop.py and the fit per component.
"""
import importlib.util
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "tests"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ps = load("skeldar_physstop_fit", os.path.join(HERE, "skeldar_physstop.py"))
tests = load("physstop_tests_fit", os.path.join(REPO, "tests", "test_physstop.py"))
with open(os.path.join(HERE, "cube_reference.json")) as f:
    cube = tests.cube_components(json.load(f))
TARGET = {k: np.array(cube[k]) for k in ("travel", "tilt", "sink", "sway", "yaw")}
SCALE = {"travel": 32.36, "tilt": 1.0, "sink": 1.0, "sway": 1.0, "yaw": 1.0}
WEIGHT = {"travel": 1 / 0.3, "tilt": 1 / 2.0, "sink": 1 / 0.15, "sway": 1 / 0.25, "yaw": 1 / 1.0}


def run(amplitude, swing):
    tr = ps.solve(0.0, cube["t_b"], cube["reach"], cube["reach"], cube["height"],
                  {"amplitude": amplitude, "swing": swing})
    rows = {r.t: r for r in tr.rows}
    last = tr.rows[-1]
    pick = [rows.get(float(f), last) for f in range(31)]
    return {"travel": np.array([r.p for r in pick]), "tilt": np.array([r.tilt for r in pick]),
            "sink": np.array([r.sink for r in pick]), "sway": np.array([r.sway for r in pick]),
            "yaw": np.array([r.yaw for r in pick])}, tr.end


def error(model, key):
    return float(np.sqrt(np.mean((model[key] - TARGET[key]) ** 2))) * SCALE[key]


def gain(model, key, current):
    """Least-squares rescale of a component that is (nearly) linear in its constant."""
    m = model[key]
    if not np.any(m):
        return current
    return current * float(np.dot(m, TARGET[key]) / np.dot(m, m))


best = None
for zeta, swing, amplitude in itertools.product(np.linspace(0.2, 0.45, 11), np.linspace(4.0, 6.0, 9),
                                                np.linspace(2.0, 7.0, 11)):
    ps.ZETA = zeta
    ps.K_TILT, ps.K_SINK = 45.4, 0.51
    for _ in range(3):                      # the drives saturate softly: iterate the linear rescale
        model, _ = run(amplitude, swing)
        ps.K_TILT = gain(model, "tilt", ps.K_TILT)
        ps.K_SINK = gain(model, "sink", ps.K_SINK)
    model, _ = run(amplitude, swing)
    score = sum(error(model, k) * WEIGHT[k] for k in ("travel", "tilt", "sink"))
    if best is None or score < best[0]:
        best = (score, zeta, swing, amplitude, ps.K_TILT, ps.K_SINK)

_, ps.ZETA, swing, amplitude, ps.K_TILT, ps.K_SINK = best
sway_best = None
for rate in np.linspace(0.4, 1.2, 33):
    ps.SWAY_RATE = rate
    ps.K_SWAY = 0.21
    for _ in range(3):
        model, _ = run(amplitude, swing)
        ps.K_SWAY = gain(model, "sway", ps.K_SWAY)
    model, _ = run(amplitude, swing)
    e = error(model, "sway")
    if sway_best is None or e < sway_best[0]:
        sway_best = (e, rate, ps.K_SWAY)
_, ps.SWAY_RATE, ps.K_SWAY = sway_best
ps.K_YAW = 52.0
for _ in range(3):
    model, end = run(amplitude, swing)
    ps.K_YAW = gain(model, "yaw", ps.K_YAW)
model, end = run(amplitude, swing)

print("ZETA = %.3f" % ps.ZETA)
print("K_TILT = %.2f" % ps.K_TILT)
print("K_SINK = %.3f" % ps.K_SINK)
print("K_SWAY = %.3f" % ps.K_SWAY)
print("SWAY_RATE = %.3f" % ps.SWAY_RATE)
print("K_YAW = %.1f" % ps.K_YAW)
print('DEFAULTS amplitude %.2f, swing %.2f' % (amplitude, swing))
for k in ("travel", "tilt", "sink", "sway", "yaw"):
    print("%-6s rms %.3f   (range %.2f)" % (k, error(model, k), float(np.ptp(TARGET[k])) * SCALE[k]))
print("settles at frame %d" % end)
```

- [ ] **Step 4: Run it, paste its constants into `skeldar_physstop.py`, run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/physstop/calibrate_physstop.py`
then the unit tests. Expected: `CubeTests` all pass with the fitted constants (tighten a threshold only if
the fit is far inside it).

- [ ] **Step 5: Commit** - "feat(physstop): the constants fitted to the cube"

---

### Task 4: The scene - the two keys, apply, re-apply, restore

**Files:**
- Modify: `skeldar_physstop.py` (section 3)
- Create: `docs/superpowers/plans/physstop/verify_physstop.py`

**Interfaces:**
- Consumes: `solve`, `params`, `up_axis`, `bottom_and_height`, `local_matrix`, `channel_frames` (Tasks 1-2).
- Produces: `CHANNELS`, `MARKER = "skeldarPhysStop"`, `class Refusal(Exception)`, `key_times(node)`,
  `source(node) -> (t_a, t_b, b_time)`, `plan(node, given=None, axis="Auto") -> Plan` (`.node, .t_a, .t_b,
  .transition, .frames, .notes, .height`), `apply(nodes, given=None, axis="Auto") -> [str]`,
  `restore(nodes) -> [str]`, `selected()`.

- [ ] **Step 1: Write the scene section** (insert before `if __name__ == "__main__":`)

```python
# ---------------------------------------------------------------------------------------------------------
# 3. The scene (maya.cmds)
# ---------------------------------------------------------------------------------------------------------

CHANNELS = ("translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ")
MARKER = "skeldarPhysStop"
FOREVER = 1e7


class Refusal(Exception):
    pass


def _cmds():
    import maya.cmds as cmds
    return cmds


def _short(node):
    return node.split("|")[-1]


def key_times(node):
    """Every key time on translate/rotate, merged."""
    cmds = _cmds()
    times = set()
    for ch in CHANNELS:
        for t in cmds.keyframe(node + "." + ch, query=True, timeChange=True) or []:
            times.add(round(t, 4))
    return sorted(times)


def remembered(node):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=node, exists=True):
        return None
    try:
        return json.loads(cmds.getAttr(node + "." + MARKER) or "")
    except ValueError:
        return None


def source(node):
    """(t_a, t_b, b_time): the keys the transition runs between, and where pose B is read. A transition
    this script wrote (the marker, its last key unmoved) is re-run from its own keys, B read at its end -
    so editing that last key edits pose B; otherwise the last two key times."""
    times = key_times(node)
    memo = remembered(node)
    if memo and times and abs(times[-1] - memo["tE"]) < 1e-3:
        return float(memo["tA"]), float(memo["tB"]), float(memo["tE"])
    if len(times) < 2:
        raise Refusal("%s: needs two keys on translate/rotate - has %d" % (_short(node), len(times)))
    t_a, t_b = times[-2], times[-1]
    if t_b - t_a < 1.0 - 1e-6:
        raise Refusal("%s: the last two keys are less than a frame apart" % _short(node))
    return t_a, t_b, t_b


def pose_at(node, t):
    cmds = _cmds()
    values = [cmds.getAttr(node + "." + ch, time=t) for ch in CHANNELS]
    return tuple(values[:3]), tuple(values[3:])


def blocked(node):
    """Channels this script must not write: locked, or driven by anything but a plain curve."""
    cmds = _cmds()
    out = []
    for ch in CHANNELS:
        plug = node + "." + ch
        if cmds.getAttr(plug, lock=True):
            out.append(ch)
            continue
        src = cmds.listConnections(plug, source=True, destination=False, skipConversionNodes=True) or []
        if src and not cmds.ls(src[0], type="animCurve"):
            out.append(ch)
    return out


def fixed_parts(node):
    cmds = _cmds()
    fixed = {name: tuple(cmds.getAttr(node + "." + name)[0]) for name in IDENTITY_FIXED}
    return fixed, cmds.getAttr(node + ".rotateOrder")


def object_box(node):
    """The object-space box of every visible shape under the node (corners carried in), or None."""
    cmds = _cmds()
    om = _om()
    inverse = om.MMatrix(cmds.getAttr(node + ".worldInverseMatrix[0]"))
    low, high = [float("inf")] * 3, [float("-inf")] * 3
    for shape in cmds.listRelatives(node, allDescendents=True, fullPath=True, type="shape") or []:
        if cmds.getAttr(shape + ".intermediateObject"):
            continue
        owner = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
        into = om.MMatrix(cmds.getAttr(owner + ".worldMatrix[0]")) * inverse
        a = cmds.getAttr(shape + ".boundingBoxMin")[0]
        b = cmds.getAttr(shape + ".boundingBoxMax")[0]
        for corner in ((x, y, z) for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])):
            p = om.MPoint(corner) * into
            for i, v in enumerate((p.x, p.y, p.z)):
                low[i], high[i] = min(low[i], v), max(high[i], v)
    return (tuple(low), tuple(high)) if low[0] <= high[0] else None


class Plan(object):
    def __init__(self, node, t_a, t_b, transition, frames, height, notes):
        self.node, self.t_a, self.t_b = node, t_a, t_b
        self.transition, self.frames, self.height, self.notes = transition, frames, height, notes


def plan(node, given=None, axis="Auto"):
    """Everything a press writes on `node`, computed and nothing touched."""
    cmds = _cmds()
    om = _om()
    if cmds.referenceQuery(node, isNodeReferenced=True):
        raise Refusal("%s: referenced - not touched" % _short(node))
    t_a, t_b, b_time = source(node)
    pose_a, pose_b = pose_at(node, t_a), pose_at(node, b_time)
    fixed, order = fixed_parts(node)

    def parent_at(t):
        return om.MMatrix(cmds.getAttr(node + ".parentMatrix[0]", time=t))

    world_a = local_matrix(pose_a[0], pose_a[1], order, fixed) * parent_at(t_a)
    world_b = local_matrix(pose_b[0], pose_b[1], order, fixed) * parent_at(t_b)
    rows = tuple(tuple(world_b.getElement(i, j) for j in range(3)) for i in range(3))
    index, sign = up_axis(rows, axis)
    notes = []
    box = object_box(node)
    if box:
        bottom, height = bottom_and_height(box[0], box[1], index, sign, rows)
    else:
        bottom, height = fixed["rotatePivot"], 0.0
    if height < 1e-6:
        height = FALLBACK_HEIGHT
        notes.append("no geometry - its pivot taken as the bottom, %g cm as the height" % FALLBACK_HEIGHT)
    up = om.MVector(UP)
    travel = om.MPoint(bottom) * world_b - om.MPoint(bottom) * world_a
    flat = travel - up * (travel * up)
    heading = flat.normal() if flat.length() > 1e-4 else None
    if heading is None and travel.length() > 1e-4:
        notes.append("no horizontal travel - no overlap or sway")
    transition = solve(t_a, t_b, travel.length() / height, flat.length() / height, height, given)
    if transition.clamped:
        notes.append("overshoot held to %.1f %% - the move is too short for more" % (100 * transition.overshoot))
    frames = channel_frames(transition, pose_a, pose_b, order, fixed, parent_at, bottom, heading)
    return Plan(node, t_a, t_b, transition, frames, height, notes)


def _write(p, skip, axis):
    cmds = _cmds()
    a = p.frames[0]
    for i, ch in enumerate(CHANNELS):
        if ch in skip:
            continue
        values = [f[1][i] if i < 3 else f[2][i - 3] for f in p.frames]
        if not cmds.keyframe(p.node + "." + ch, query=True, time=(p.t_a, p.t_a)):
            cmds.setKeyframe(p.node, attribute=ch, time=p.t_a, value=values[0])
        cmds.keyTangent(p.node, attribute=ch, time=(p.t_a, p.t_a), outTangentType="auto")
        cmds.cutKey(p.node, attribute=ch, time=(p.t_a + 1e-3, FOREVER), clear=True)
        for f, v in zip(p.frames[1:], values[1:]):
            cmds.setKeyframe(p.node, attribute=ch, time=f[0], value=v,
                             inTangentType="auto", outTangentType="auto")
    if not cmds.attributeQuery(MARKER, node=p.node, exists=True):
        cmds.addAttr(p.node, longName=MARKER, dataType="string")
    memo = {"tA": p.t_a, "tB": p.t_b, "tE": p.transition.end, "params": p.transition.params, "axis": axis}
    cmds.setAttr(p.node + "." + MARKER, json.dumps(memo), type="string")
    del a


def describe(p, skip):
    tr = p.transition
    text = "%s: frames %g-%g, tilt up to %.1f deg, sink %.2f cm, sway %.2f cm, settles %g frames after B" % (
        _short(p.node), p.t_a, tr.end, tr.peak_tilt, tr.peak_sink, tr.peak_sway, tr.end - p.t_b)
    notes = list(p.notes)
    if skip:
        notes.append("not written (locked or driven): %s" % ", ".join(skip))
    return text + ("" if not notes else " | " + "; ".join(notes))


def _chunk(name):
    cmds = _cmds()

    class Chunk(object):
        def __enter__(self):
            cmds.undoInfo(openChunk=True, chunkName=name)

        def __exit__(self, *exc):
            cmds.undoInfo(closeChunk=True)
            return False
    return Chunk()


def apply(nodes, given=None, axis="Auto"):
    """Build the transition on every node; one undo step. Returns one line per node."""
    lines = []
    with _chunk("skeldarPhysStop"):
        for node in nodes:
            try:
                p = plan(node, given, axis)
                skip = blocked(node)
                if len(skip) == len(CHANNELS):
                    raise Refusal("%s: every translate/rotate channel is locked or driven" % _short(node))
                _write(p, skip, axis)
                lines.append(describe(p, skip))
            except Refusal as refusal:
                lines.append(str(refusal))
    return lines


def restore(nodes):
    """Back to the two keys the transition was built from; the marker removed."""
    cmds = _cmds()
    lines = []
    with _chunk("skeldarPhysStopRestore"):
        for node in nodes:
            memo = remembered(node)
            times = key_times(node)
            if not memo or not times or abs(times[-1] - memo["tE"]) > 1e-3:
                lines.append("%s: no transition of this script to restore" % _short(node))
                continue
            pose_b = pose_at(node, memo["tE"])
            for i, ch in enumerate(CHANNELS):
                if ch in blocked(node):
                    continue
                cmds.cutKey(node, attribute=ch, time=(memo["tA"] + 1e-3, FOREVER), clear=True)
                value = pose_b[0][i] if i < 3 else pose_b[1][i - 3]
                cmds.setKeyframe(node, attribute=ch, time=memo["tB"], value=value,
                                 inTangentType="auto", outTangentType="auto")
            cmds.deleteAttr(node + "." + MARKER)
            lines.append("%s: back to its keys at %g and %g" % (_short(node), memo["tA"], memo["tB"]))
    return lines


def selected():
    """The selected transforms (a selected shape names its transform), in selection order."""
    cmds = _cmds()
    out = []
    for node in cmds.ls(selection=True, long=True) or []:
        if cmds.objectType(node, isAType="shape"):
            node = cmds.listRelatives(node, parent=True, fullPath=True)[0]
        if cmds.objectType(node, isAType="transform") and node not in out:
            out.append(node)
    return out
```

- [ ] **Step 2: Write the standalone verify**

```python
"""verify_physstop.py - the physical stop in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/physstop/verify_physstop.py
"""
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.api.OpenMaya as om

ps = load("skeldar_physstop", os.path.join(HERE, "skeldar_physstop.py"))
tests = load("physstop_tests", os.path.join(REPO, "tests", "test_physstop.py"))
with open(os.path.join(HERE, "cube_reference.json")) as f:
    REF = json.load(f)
cube = tests.cube_components(REF)
FAILED = []


def gate(n, ok, text):
    print("gate %2d %s  %s" % (n, "ok  " if ok else "FAIL", text))
    if not ok:
        FAILED.append(n)


def world_points(node, frames):
    out = []
    for f in frames:
        m = om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]", time=f))
        out.append((om.MPoint(0, -0.5, 0) * m, om.MPoint(0, 0.5, 0) * m))
    return out


cmds.currentUnit(time="film")
cmds.undoInfo(state=True, infinity=True)
# The animator's cube: A at f0, B keyed at f9 (it passes its target at f9.1) with the cube's own rest pose.
cube_node = cmds.polyCube(width=1, height=1, depth=1, name="cube")[0]
cmds.setAttr(cube_node + ".scale", 4.131199784, 11.644606338, 3.883901969, type="double3")
A = (0.0, 5.837090, 0.0, 0.0, 0.0, 0.0)
B = (0.0, 5.829040, -32.065960, 2.906870, 0.0, 0.0)
for ch, a, b in zip(ps.CHANNELS, A, B):
    cmds.setKeyframe(cube_node, attribute=ch, time=0, value=a)
    cmds.setKeyframe(cube_node, attribute=ch, time=9, value=b)

lines = ps.apply([cube_node])
print(lines)
p = ps.plan(cube_node)
times = ps.key_times(cube_node)
gate(1, times == [float(i) for i in range(int(p.transition.end) + 1)], "a key on every frame 0..%g" % p.transition.end)
first = ps.pose_at(cube_node, 0)
last = ps.pose_at(cube_node, times[-1])
gate(2, max(abs(x - y) for x, y in zip(first[0] + first[1], A)) < 1e-6, "frame 0 is pose A")
gate(3, max(abs(x - y) for x, y in zip(last[0] + last[1], B)) < 1e-6, "the last key is pose B")
pts = world_points(cube_node, range(31))
expected_b9 = om.MPoint(0, -0.5, 0) * ps.local_matrix(B[:3], B[3:], 0, ps.fixed_parts(cube_node)[0])
gate(4, abs(pts[9][0].z - expected_b9.z) < 1e-4, "the bottom is at B's place along the path at f9: %.5f / %.5f"
     % (pts[9][0].z, expected_b9.z))

# Against the cube frame by frame (the cube is the reference, B keyed at f9 against its f9.1).
mats = [[m[i * 4:(i + 1) * 4] for i in range(4)] for m in REF["wm"]]
ref_bottom = [tests._mul((0, -0.5, 0, 1), m) for m in mats]
ref_top = [tests._mul((0, 0.5, 0, 1), m) for m in mats]
end = len(times) - 1
def at(f):
    return pts[min(f, end)] if f < len(pts) else pts[-1]
eb = math.sqrt(sum((at(f)[0].x - ref_bottom[f][0]) ** 2 + (at(f)[0].y - ref_bottom[f][1]) ** 2
                   + (at(f)[0].z - ref_bottom[f][2]) ** 2 for f in range(31)) / 31)
et = math.sqrt(sum((at(f)[1].x - ref_top[f][0]) ** 2 + (at(f)[1].y - ref_top[f][1]) ** 2
                   + (at(f)[1].z - ref_top[f][2]) ** 2 for f in range(31)) / 31)
gate(5, eb < 1.0, "the bottom against the cube: rms %.3f cm over 31 frames (32 cm of travel)" % eb)
gate(6, et < 1.5, "the top against the cube: rms %.3f cm" % et)
peak = max(range(31), key=lambda f: math.degrees(math.atan2(at(f)[1].z - at(f)[0].z, at(f)[1].y - at(f)[0].y)))
gate(7, 6 <= peak <= 10, "the tilt peaks at frame %d (the cube: 8)" % peak)

# Re-apply with other numbers: the same two keys, a longer settle.
end1 = ps.key_times(cube_node)[-1]
ps.apply([cube_node], {"weight": 2.0})
end2 = ps.key_times(cube_node)[-1]
memo = ps.remembered(cube_node)
gate(8, memo["tA"] == 0 and memo["tB"] == 9 and end2 > end1, "re-applied from the same keys, heavier settles later: %g -> %g" % (end1, end2))
# Editing the last key edits pose B.
cmds.setKeyframe(cube_node, attribute="translateX", time=end2, value=10.0)
ps.apply([cube_node])
gate(9, abs(cmds.getAttr(cube_node + ".translateX", time=ps.key_times(cube_node)[-1]) - 10.0) < 1e-6,
     "the edited last key became pose B")
# Undo: one Ctrl+Z puts the previous transition back.
before = ps.key_times(cube_node)[-1]
cmds.undo()
gate(10, ps.key_times(cube_node)[-1] == end2 and abs(cmds.getAttr(cube_node + ".translateX", time=end2) - 10.0) < 1e-6,
     "one undo = one press")
cmds.redo()
# Restore keys.
ps.restore([cube_node])
gate(11, ps.key_times(cube_node) == [0.0, 9.0] and not cmds.attributeQuery(ps.MARKER, node=cube_node, exists=True),
     "Restore keys: back to two keys, marker gone")
gate(12, abs(cmds.getAttr(cube_node + ".translateX", time=9) - 10.0) < 1e-6, "  ... with pose B as it was last")

# A parented, pivoted, zxy object: its world is the model's at every frame.
grp = cmds.group(empty=True, name="holder")
cmds.setAttr(grp + ".translate", 5, 2, -3, type="double3")
cmds.setAttr(grp + ".rotate", 0, 35, 0, type="double3")
cmds.setAttr(grp + ".scale", 1.5, 1.5, 1.5, type="double3")
box = cmds.polyCube(width=2, height=6, depth=1, name="prop")[0]
cmds.parent(box, grp, relative=True)
cmds.setAttr(box + ".rotateOrder", 2)
cmds.setAttr(box + ".rotatePivot", 0.3, -3.0, 0.1, type="double3")
cmds.setAttr(box + ".scalePivot", 0.3, -3.0, 0.1, type="double3")
cmds.setAttr(box + ".rotateAxis", 0, 15, 0, type="double3")
for ch, a, b in zip(ps.CHANNELS, (0, 3, 0, 0, 10, 0), (12, 3, 8, 0, 40, 5)):
    cmds.setKeyframe(box, attribute=ch, time=10, value=a)
    cmds.setKeyframe(box, attribute=ch, time=20, value=b)
pb = ps.plan(box)
ps.apply([box])
worst = 0.0
fixed, order = ps.fixed_parts(box)
for t, tr, ro in pb.frames:
    want = ps.local_matrix(tr, ro, order, fixed) * om.MMatrix(cmds.getAttr(box + ".parentMatrix[0]", time=t))
    have = om.MMatrix(cmds.getAttr(box + ".worldMatrix[0]", time=t))
    worst = max(worst, max(abs(want.getElement(i, j) - have.getElement(i, j)) for i in range(4) for j in range(4)))
gate(13, worst < 1e-6, "pivots, rotate axis, zxy, a turned scaled parent: world = model to %.2e" % worst)
row9 = [r for r in pb.transition.rows if r.t == 15.0][0]
gate(14, row9.tilt > 0 and pb.transition.peak_tilt > 1.0, "the prop tilts back while it travels (%.1f deg)" % pb.transition.peak_tilt)

# Euler continuity: a 350 -> 370 yaw stays near 360, never jumps a turn.
spin = cmds.polyCube(name="spin")[0]
for ch, a, b in zip(ps.CHANNELS, (0, 0.5, 0, 0, 350, 0), (0, 0.5, -10, 0, 370, 0)):
    cmds.setKeyframe(spin, attribute=ch, time=0, value=a)
    cmds.setKeyframe(spin, attribute=ch, time=8, value=b)
ps.apply([spin])
ys = [cmds.getAttr(spin + ".rotateY", time=t) for t in ps.key_times(spin)]
gate(15, max(abs(b - a) for a, b in zip(ys, ys[1:])) < 30 and abs(ys[-1] - 370) < 1e-6, "no euler jumps (rotateY %.1f..%.1f)" % (min(ys), max(ys)))

# Refusals.
lone = cmds.polyCube(name="lone")[0]
cmds.setKeyframe(lone, attribute="translateX", time=0, value=0)
gate(16, ps.apply([lone])[0].endswith("needs two keys on translate/rotate - has 1"), "one key: refused by name")
locked = cmds.polyCube(name="locked")[0]
for t, v in ((0, 0), (8, -20)):
    cmds.setKeyframe(locked, attribute="translateZ", time=t, value=v)
cmds.setAttr(locked + ".rotateX", lock=True)
line = ps.apply([locked])[0]
gate(17, "not written (locked or driven): rotateX" in line, "a locked channel is named: " + line)

print("%d gates, %s" % (17, "all passed" if not FAILED else "FAILED: %s" % FAILED))
maya.standalone.uninitialize()
```

- [ ] **Step 3: Run the verify**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/physstop/verify_physstop.py`
Expected: `17 gates, all passed`. A failing gate is a bug in the script (or a wrong expectation - say which,
with the numbers), never a threshold to loosen silently.

- [ ] **Step 4: Run the unit tests again, commit** - "feat(physstop): apply, re-apply and restore on the scene"

---

### Task 5: The window, the drop handler, the record

**Files:**
- Modify: `skeldar_physstop.py` (section 4 and the module's end)
- Modify: `CLAUDE.md` (a section), memory (`MEMORY.md` + one file)
- Test: `tests/test_physstop.py` (`WindowTests` on a recording fake `cmds`)

**Interfaces:**
- Consumes: `apply`, `restore`, `selected`, `remembered`, `params`, `RANGES`, `DEFAULTS`, `AXES` (Tasks 1-4).
- Produces: `show()`, `onMayaDroppedPythonFile(*args)`, `WINDOW = "skeldarPhysStopWindow"`.

- [ ] **Step 1: Write the failing test** (append)

```python
class FakeCmds(object):
    """Just enough of maya.cmds for the window: records controls, answers queries."""

    def __init__(self):
        self.values = {}
        self.vars = {}
        self.created = []
        self.selection = []

    def window(self, name, exists=False, **kw):
        if exists:
            return False
        self.created.append(("window", name))
        return name

    def windowPref(self, name, exists=False, remove=False):
        return False

    def deleteUI(self, name):
        pass

    def columnLayout(self, *a, **kw):
        return "col"

    def rowLayout(self, *a, **kw):
        return "row"

    def setParent(self, *a):
        pass

    def showWindow(self, name):
        self.created.append(("show", name))

    def text(self, name=None, edit=False, label=None, **kw):
        if edit:
            self.values[name] = label
        return name

    def button(self, *a, **kw):
        self.created.append(("button", kw.get("label")))

    def floatSliderGrp(self, name, query=False, value=None, edit=False, **kw):
        if query:
            return self.values[name]
        self.values[name] = value
        if not edit:
            self.created.append(("slider", name, kw.get("changeCommand")))
        return name

    def optionMenu(self, name, query=False, value=None, edit=False, **kw):
        if query:
            return self.values.get(name, "Auto")
        if value is not None:
            self.values[name] = value
        return name

    def menuItem(self, **kw):
        pass

    def optionVar(self, exists=None, q=None, floatValue=None, stringValue=None, query=None):
        if exists is not None:
            return exists in self.vars
        if q is not None or query is not None:
            return self.vars[q or query]
        name, value = floatValue or stringValue
        self.vars[name] = value

    def ls(self, selection=False, long=False):
        return list(self.selection)


class WindowTests(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        self.real = ps._cmds
        ps._cmds = lambda: self.fake
        self.calls = []
        self.apply = ps.apply
        ps.apply = lambda nodes, given=None, axis="Auto": self.calls.append((nodes, given, axis)) or ["done"]
        self.selected = ps.selected
        ps.selected = lambda: list(self.fake.selection)
        self.memo = ps.remembered
        ps.remembered = lambda node: {"tE": 1} if node.endswith("applied") else None

    def tearDown(self):
        ps._cmds, ps.apply, ps.selected, ps.remembered = self.real, self.apply, self.selected, self.memo

    def test_window_has_the_five_sliders_with_defaults(self):
        ps.show()
        sliders = [c[1] for c in self.fake.created if c[0] == "slider"]
        self.assertEqual(sliders, [ps._control(n) for n, _ in ps.DEFAULTS])
        for name, default in ps.DEFAULTS:
            self.assertEqual(self.fake.values[ps._control(name)], default)

    def test_remembered_values_come_back(self):
        self.fake.vars[ps.OPTION + "weight"] = 2.5
        ps.show()
        self.assertEqual(self.fake.values[ps._control("weight")], 2.5)

    def test_apply_reads_the_sliders(self):
        ps.show()
        self.fake.values[ps._control("overlap")] = 1.7
        self.fake.selection = ["|cube"]
        ps.press_apply()
        nodes, given, axis = self.calls[-1]
        self.assertEqual(nodes, ["|cube"])
        self.assertEqual(given["overlap"], 1.7)
        self.assertEqual(axis, "Auto")

    def test_a_slider_re_applies_only_what_already_carries_a_transition(self):
        ps.show()
        self.fake.selection = ["|cube"]
        ps.slider_changed()
        self.assertEqual(self.calls, [])
        self.fake.selection = ["|cube_applied"]
        ps.slider_changed()
        self.assertEqual(self.calls[-1][0], ["|cube_applied"])

    def test_nothing_selected_says_so(self):
        ps.show()
        ps.press_apply()
        self.assertEqual(self.calls, [])
        self.assertIn("Select", self.fake.values[ps.STATUS])

    def test_reset_puts_the_defaults_back(self):
        ps.show()
        self.fake.values[ps._control("swing")] = 9.0
        ps.press_reset()
        self.assertEqual(self.fake.values[ps._control("swing")], dict(ps.DEFAULTS)["swing"])
```

- [ ] **Step 2: Run them to see them fail** - Expected: `AttributeError: ... '_control'`.

- [ ] **Step 3: Write the window and the drop handler** (replace `if __name__ == "__main__": pass`)

```python
# ---------------------------------------------------------------------------------------------------------
# 4. The window (maya.cmds)
# ---------------------------------------------------------------------------------------------------------

WINDOW = "skeldarPhysStopWindow"
STATUS = "skeldarPhysStopStatus"
AXIS_MENU = "skeldarPhysStopAxis"
OPTION = "skeldarPhysStop_"
LABELS = {
    "amplitude": ("Overshoot %", 0.1, "How far it flies past B on the first swing, % of the path"),
    "overlap": ("Overlap", 0.05, "How far the top lags behind the bottom (1 = the cube)"),
    "weight": ("Weight", 0.05, "Heavier rings longer and sinks deeper (1 = the cube)"),
    "swing": ("Swing (frames)", 0.25, "Frames of one swing past B and back"),
    "sway": ("Sway", 0.05, "Sideways drift and yaw; + is left of the motion, 0 is off (1 = the cube)"),
}


def _control(name):
    return "skeldarPhysStop_" + name + "Slider"


def _stored(name, default):
    cmds = _cmds()
    key = OPTION + name
    return cmds.optionVar(q=key) if cmds.optionVar(exists=key) else default


def _given():
    cmds = _cmds()
    return {name: cmds.floatSliderGrp(_control(name), query=True, value=True) for name, _ in DEFAULTS}


def _axis():
    return _cmds().optionMenu(AXIS_MENU, query=True, value=True)


def _remember():
    cmds = _cmds()
    for name, value in _given().items():
        cmds.optionVar(floatValue=(OPTION + name, value))
    cmds.optionVar(stringValue=(OPTION + "axis", _axis()))


def _say(lines):
    _cmds().text(STATUS, edit=True, label="\n".join(lines))


def press_apply(*_):
    _remember()
    nodes = selected()
    if not nodes:
        _say(["Select objects whose last two keys are the poses to go from and to."])
        return
    _say(apply(nodes, _given(), _axis()))


def slider_changed(*_):
    """A released slider re-runs what already carries a transition; anything else waits for Apply."""
    _remember()
    nodes = selected()
    if nodes and all(remembered(n) for n in nodes):
        _say(apply(nodes, _given(), _axis()))
    elif nodes:
        _say(["Press Apply to build the transition."])


def press_restore(*_):
    nodes = selected()
    _say(restore(nodes) if nodes else ["Select the objects to restore."])


def press_reset(*_):
    cmds = _cmds()
    for name, default in DEFAULTS:
        cmds.floatSliderGrp(_control(name), edit=True, value=default)
    cmds.optionMenu(AXIS_MENU, edit=True, value="Auto")
    slider_changed()


def show():
    """The window: five controls, the up axis, Apply / Restore keys / Reset, a status line."""
    cmds = _cmds()
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    if cmds.windowPref(WINDOW, exists=True):
        cmds.windowPref(WINDOW, remove=True)
    cmds.window(WINDOW, title="Physical Stop", sizeable=True, widthHeight=(400, 330))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4, columnAttach=("both", 8))
    cmds.text(label="Select objects whose last two keys are the poses to go from and to, then Apply.",
              align="left", wordWrap=True, height=36)
    for name, default in DEFAULTS:
        low, high = RANGES[name]
        label, step, tip = LABELS[name]
        cmds.floatSliderGrp(_control(name), label=label, field=True, minValue=low, maxValue=high,
                            fieldMinValue=low, fieldMaxValue=high, step=step, precision=2,
                            value=_stored(name, default), columnWidth3=(100, 60, 200),
                            annotation=tip, changeCommand=slider_changed)
    cmds.optionMenu(AXIS_MENU, label="Up axis", annotation="The object's axis that points up",
                    changeCommand=slider_changed)
    for axis in AXES:
        cmds.menuItem(label=axis)
    cmds.optionMenu(AXIS_MENU, edit=True, value=_stored("axis", "Auto"))
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1, columnAttach3=("both", "both", "both"))
    cmds.button(label="Apply", height=30, command=press_apply)
    cmds.button(label="Restore keys", height=30, command=press_restore)
    cmds.button(label="Reset", height=30, command=press_reset)
    cmds.setParent("..")
    cmds.text(STATUS, label="", align="left", wordWrap=True, height=80)
    cmds.showWindow(WINDOW)


def onMayaDroppedPythonFile(*args):
    """Maya's viewport drop imports this file once and keeps it: reload it, so a changed file runs."""
    import importlib
    import sys
    importlib.reload(sys.modules[__name__]).show()


if __name__ == "__main__":
    show()
```

Note the window tests' fake: `FakeCmds.optionMenu(..., value=...)` on a non-edit call stores the label; the
real `optionMenu` create call takes no `value`, so `show()` sets it by an edit after the items exist.

- [ ] **Step 4: Run all physstop tests, then the whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_physstop -v`, then
`$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
Expected: all pass (the new module touches nothing else).

- [ ] **Step 5: The record** - a CLAUDE.md section "Physical stop (2026-10-10)" with what the cube is, the
model in five lines, where the script lives and how to run it, the verify's numbers, what is not built; a
memory file for anything non-obvious learned on the way. Commit - "feat(physstop): the window and the drop
handler; docs".
