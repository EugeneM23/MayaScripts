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
ZETA = 0.30          # damping of every swing at weight 1
K_TILT = 44.83       # deg of tilt per object height per frame of speed, at overlap 1
K_SINK = 0.526       # sink, in heights, per object height per frame of speed, at weight 1
K_SWAY = 0.212       # sway, in heights, per object height per frame of speed, at sway 1
SWAY_RATE = 0.75     # the sway's frequency against the other springs'
K_YAW = 51.9         # deg of yaw per object height of sway

TILT_LIMIT = 80.0    # deg: the tilt's drive saturates here (tanh), whatever the speed
DRIFT_LIMIT = 0.5    # heights: the sink's and the sway's drives saturate here
SUBSTEPS = 16        # integration steps per frame
SETTLE_SHARE = 0.02  # settled when every component stays within this share of its own peak
FADE_SHARE = 0.3     # the last share of the settle fades every residual to 0
MAX_TAIL = 400       # frames simulated after B at most
FALLBACK_HEIGHT = 10.0

DEFAULTS = (("amplitude", 4.5), ("overlap", 1.0), ("weight", 1.0), ("swing", 5.0), ("sway", 1.0))
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


if __name__ == "__main__":
    pass
