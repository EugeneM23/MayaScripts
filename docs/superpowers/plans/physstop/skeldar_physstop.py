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
