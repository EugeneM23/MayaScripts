"""Tail Builder - the hub card that builds a physical stop through three poses (2026-10-12).

The animator: «Давай добавим в наш плагин вкладку с этим инструментом ... Tail Builder» - the physical
stop, a standalone script until now (docs/superpowers/plans/physstop/, 2026-10-10), moves into the plugin.

Select objects whose LAST THREE KEYS are the pose they leave (A), a breakdown (M) and the pose they come to
(B), and press Apply. The bottom of the object travels an arc through all three - M sets how it comes in,
from above, from below or from the side - stands in pose M at M's frame, passes B at B's frame with speed,
overshoots along the arc and settles into B; its top lags behind as far, and in the direction, the
breakdown shows. A model fitted to the animator's cube: docs/superpowers/specs/2026-10-10-physical-stop-
design.md and 2026-10-12-physical-stop-three-poses-design.md.

Four layers: the model (stdlib), the geometry (OpenMaya math), the scene (cmds), the hub card (cmds and the
hub's style). maya.cmds and OpenMaya are imported inside functions, so the model is testable anywhere.
"""

import bisect
import json
import math
import traceback

# ---------------------------------------------------------------------------------------------------------
# 1. The model (stdlib)
# ---------------------------------------------------------------------------------------------------------

# The cube's rule, fitted by calibrate_physstop.py against cube_reference.json.
ZETA = 0.32          # damping of every swing at weight 1
K_TILT = 47.10       # deg of tilt per object height per frame of speed: the lag's SHAPE (the breakdown scales it)

TILT_LIMIT = 40.0    # deg: the tilt's drive saturates here (tanh) - a small object flying far stays sane
LAG_READABLE = 0.15  # the tilt spring must bend this share of its peak at M for M's lag to scale it there
SUBSTEPS = 16        # integration steps per frame
SETTLE_SHARE = 0.02  # settled when every component stays within this share of its own peak
FADE_SHARE = 0.3     # the last share of the settle fades every residual to 0
MAX_TAIL = 400       # frames simulated after B at most
FALLBACK_HEIGHT = 10.0
ARC_SAMPLES = 256

# The controls, in the window's order (the cube's values).
DEFAULTS = (("overshoot", 3.0), ("swing", 5.0), ("weight", 1.0))
RANGES = {
    "overshoot": (0.0, 20.0),   # the first swing past B, % of the path
    "swing": (1.0, 20.0),       # frames of one swing
    "weight": (0.2, 5.0),       # how long it rings
}


def params(**given):
    """The controls, defaults filled in, each clamped to its range."""
    out = {}
    for name, default in DEFAULTS:
        low, high = RANGES[name]
        value = given.get(name)
        out[name] = min(high, max(low, float(default if value is None else value)))
    return out


def damping(weight):
    """A heavier object rings longer: the damping falls with the weight."""
    return min(0.9, max(0.05, ZETA / max(weight, 1e-6)))


def _hermite(u, y0, y1, m0, m1, h):
    """(value, d/dt) of the cubic Hermite segment at u in [0, 1] over h frames."""
    u2, u3 = u * u, u * u * u
    value = ((2 * u3 - 3 * u2 + 1) * y0 + (u3 - 2 * u2 + u) * h * m0
             + (-2 * u3 + 3 * u2) * y1 + (u3 - u2) * h * m1)
    rate = ((6 * u2 - 6 * u) * y0 + (3 * u2 - 4 * u + 1) * h * m0
            + (-6 * u2 + 6 * u) * y1 + (3 * u2 - 2 * u) * h * m1) / h
    return value, rate


class Path(object):
    """The progress p(t) along the arc: from A (0) at rest, through the breakdown (s_m) at t_m, through B
    (1) at t_b with speed, then a swing about B that dies. A clamped cubic spline (curvature continuous at
    the breakdown) whose slopes are held to three times each stretch's average, so it never runs back."""

    def __init__(self, t_a, t_m, t_b, s_m, overshoot, swing, zeta):
        self.t_a, self.t_m, self.t_b = float(t_a), float(t_m), float(t_b)
        self.s_m = min(1.0, max(0.0, float(s_m)))
        self.w = math.pi / swing
        self.sigma = zeta * self.w / math.sqrt(1.0 - zeta * zeta)
        tau = math.atan2(self.w, self.sigma) / self.w        # the first crest after B
        crest = math.exp(-self.sigma * tau) * math.sin(self.w * tau)
        h1, h2 = self.t_m - self.t_a, self.t_b - self.t_m
        d1, d2 = self.s_m / h1, (1.0 - self.s_m) / h2
        wanted = overshoot / 100.0 * self.w / crest
        self.clamped = wanted > 3.0 * d2 + 1e-12
        self.v_b = max(0.0, min(wanted, 3.0 * d2))
        v_m = (3.0 * (h2 * d1 + h1 * d2) - h1 * self.v_b) / (2.0 * (h1 + h2))
        self.v_m = max(0.0, min(v_m, 3.0 * min(d1, d2)))
        self.overshoot = self.v_b / self.w * crest

    def at(self, t):
        """(p, dp/dt) at frame t."""
        if t <= self.t_a:
            return 0.0, 0.0
        if t <= self.t_m:
            h = self.t_m - self.t_a
            return _hermite((t - self.t_a) / h, 0.0, self.s_m, 0.0, self.v_m, h)
        if t <= self.t_b:
            h = self.t_b - self.t_m
            return _hermite((t - self.t_m) / h, self.s_m, 1.0, self.v_m, self.v_b, h)
        if self.v_b == 0.0:
            return 1.0, 0.0
        tau = t - self.t_b
        fade = math.exp(-self.sigma * tau)
        k = self.v_b / self.w
        s, c = math.sin(self.w * tau), math.cos(self.w * tau)
        return 1.0 + k * fade * s, k * fade * (self.w * c - self.sigma * s)


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _scaled(a, k):
    return tuple(x * k for x in a)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _length(a):
    return math.sqrt(_dot(a, a))


class Arc(object):
    """The bottom's path: the parabola C(u) = A + u V + u^2 Q through A, the breakdown M (at u = tau, the
    chords' share) and B, measured along its length; s is the share of that length. Past B it runs on along
    its tangent there, so the overshoot leaves the way the arc arrived."""

    def __init__(self, a, m, b):
        self.a, self.m, self.b = (tuple(float(x) for x in p) for p in (a, m, b))
        e, f = _sub(self.b, self.a), _sub(self.m, self.a)
        first, second = _length(f), _length(_sub(self.b, self.m))
        self.tau = first / (first + second) if first + second > 1e-12 else 0.5
        if 1e-9 < self.tau < 1.0 - 1e-9:
            self.q = _scaled(_sub(_scaled(e, self.tau), f), 1.0 / (self.tau * (1.0 - self.tau)))
        else:
            self.q = (0.0, 0.0, 0.0)
        self.v = _sub(e, self.q)
        self.us = [i / float(ARC_SAMPLES) for i in range(ARC_SAMPLES + 1)]
        points = [self._at_u(u) for u in self.us]
        run = [0.0]
        for p0, p1 in zip(points, points[1:]):
            run.append(run[-1] + _length(_sub(p1, p0)))
        self.length = run[-1]
        self.ss = [r / self.length for r in run] if self.length > 1e-12 else list(self.us)
        self.s_m = self._s_of_u(self.tau)
        tangent = _add(self.v, _scaled(self.q, 2.0))
        size = _length(tangent)
        if size < 1e-12:
            tangent, size = e, _length(e)
        self.tangent = _scaled(tangent, 1.0 / size) if size > 1e-12 else (0.0, 0.0, 0.0)

    def _at_u(self, u):
        return _add(self.a, _add(_scaled(self.v, u), _scaled(self.q, u * u)))

    @staticmethod
    def _interp(xs, ys, x):
        i = min(max(bisect.bisect_right(xs, x), 1), len(xs) - 1)
        x0, x1 = xs[i - 1], xs[i]
        if x1 - x0 < 1e-15:
            return ys[i]
        return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - x0) / (x1 - x0)

    def _s_of_u(self, u):
        return self._interp(self.us, self.ss, u)

    def at(self, s):
        """The point at arc share s (past 1: on along the tangent at B)."""
        if s >= 1.0:
            return _add(self.b, _scaled(self.tangent, (s - 1.0) * self.length))
        if s <= 0.0:
            return self.a
        if abs(s - self.s_m) < 1e-12:
            return self.m
        return self._at_u(self._interp(self.ss, self.us, s))

    def bend(self):
        """How far the breakdown stands off the straight line A-B."""
        e = _sub(self.b, self.a)
        f = _sub(self.m, self.a)
        size = _length(e)
        if size < 1e-12:
            return _length(f)
        along = _dot(f, e) / size
        return math.sqrt(max(0.0, _dot(f, f) - along * along))


def _smoothstep(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def pin_weight(t, t_a, t_m, t_b):
    """0 at A, rising smoothly to 1 at the breakdown, falling smoothly to 0 at B, 0 outside."""
    if t <= t_a or t >= t_b:
        return 0.0
    if t <= t_m:
        return _smoothstep((t - t_a) / (t_m - t_a))
    return _smoothstep((t_b - t) / (t_b - t_m))


class Row(object):
    __slots__ = ("t", "p", "tilt")

    def __init__(self, t, p, tilt):
        self.t, self.p, self.tilt = t, p, tilt


class Transition(object):
    """Every frame from A to the settle (plus the breakdown's own time): the arc share and the tilt spring
    (deg - the lag's shape). Nothing else moves the bottom: it stays on the arc through A, M and B."""

    def __init__(self, rows, end, path, given):
        self.rows = rows
        self.end = end
        self.t_a, self.t_m, self.t_b = path.t_a, path.t_m, path.t_b
        self.overshoot = path.overshoot
        self.clamped = path.clamped
        self.params = given
        self.peak_tilt = max(abs(r.tilt) for r in rows)
        peak_row = max(rows, key=lambda r: abs(r.tilt))
        self.tilt_peak = peak_row.tilt
        self.tilt_m = self.row_at(self.t_m).tilt
        self.readable = self.peak_tilt > 1e-9 and abs(self.tilt_m) >= LAG_READABLE * self.peak_tilt

    def row_at(self, t):
        for row in self.rows:
            if abs(row.t - t) < 1e-6:
                return row
        raise KeyError(t)

    def lag_share(self, tilt):
        """How much of the breakdown's lag the top carries at a frame whose tilt spring reads `tilt`: 1 at
        the breakdown - or, where the spring barely bends there, 1 at its peak."""
        if self.readable:
            return tilt / self.tilt_m
        if self.peak_tilt > 1e-9:
            return tilt / self.tilt_peak
        return 0.0


def _frames(t_a, end, extras=()):
    """t_a, every whole frame after it up to `end`, and the extra times in between."""
    out = {float(t_a)}
    f = math.floor(t_a) + 1
    while f <= end + 1e-9:
        out.add(float(f))
        f += 1
    for x in extras:
        if t_a < x <= end + 1e-9:
            out.add(float(x))
    return sorted(out)


def _step(state, drive, omega, zeta, dt):
    x, v = state
    v += (omega * omega * (drive - x) - 2.0 * zeta * omega * v) * dt
    state[0], state[1] = x + v * dt, v


def simulate(path, end, reach, zeta):
    """(t, p, tilt deg) on every frame from A to `end` and at the breakdown. The bottom's speed along the
    arc in heights per frame drives the tilt spring, at rest at A: the lag's shape in time."""
    omega = path.w / math.sqrt(1.0 - zeta * zeta)
    tilt = [0.0, 0.0]
    out = []
    t = path.t_a
    for f in _frames(path.t_a, end, (path.t_m,)):
        steps = int(math.ceil((f - t) * SUBSTEPS - 1e-9)) if f > t else 0
        if steps:
            dt = (f - t) / steps
            for i in range(steps):
                _, v = path.at(t + dt * (i + 0.5))
                _step(tilt, TILT_LIMIT * math.tanh(K_TILT * v * reach / TILT_LIMIT), omega, zeta, dt)
            t = f
        out.append((f, path.at(f)[0], tilt[0]))
    return out


def settle_frame(raw, t_b):
    """The first whole frame after B from which every component stays within SETTLE_SHARE of its peak."""
    residual = [((r[1] - 1.0) if r[0] >= t_b else 0.0, r[2]) for r in raw]
    peaks = [max(abs(c[k]) for c in residual) for k in range(2)]
    last = None
    for row, comps in zip(raw, residual):
        if row[0] > t_b and any(p > 1e-9 and abs(c) > SETTLE_SHARE * p for c, p in zip(comps, peaks)):
            last = row[0]
    first_after = math.floor(t_b) + 1.0 if t_b != math.floor(t_b) else t_b
    return max(first_after, (last + 1.0) if last is not None else first_after)


def solve(t_a, t_m, t_b, s_m, reach, given=None):
    """The transition through keys at t_a, t_m (arc share s_m) and t_b. reach: the arc's length in object
    heights."""
    given = params(**(given or {}))
    zeta = damping(given["weight"])
    path = Path(t_a, t_m, t_b, s_m, given["overshoot"], given["swing"], zeta)
    raw = simulate(path, math.floor(t_b) + MAX_TAIL, reach, zeta)
    end = settle_frame(raw, t_b)
    start = max(t_b, end - max(2.0, FADE_SHARE * (end - t_b)))
    rows = []
    for t, p, tilt in raw:
        if t > end + 1e-9:
            break
        keep = 1.0
        if t >= start and end > start:
            keep = 1.0 - _smoothstep((t - start) / (end - start))
        if t >= t_b:
            p = 1.0 + (p - 1.0) * keep
        rows.append(Row(t, p, tilt * keep))
    rows[-1] = Row(end, 1.0, 0.0)
    return Transition(rows, end, path, given)


# ---------------------------------------------------------------------------------------------------------
# 2. The geometry (maya.api.OpenMaya math only)
# ---------------------------------------------------------------------------------------------------------

UP = (0.0, 1.0, 0.0)
IDENTITY_FIXED = {
    "scale": (1.0, 1.0, 1.0), "shear": (0.0, 0.0, 0.0), "scalePivot": (0.0, 0.0, 0.0),
    "scalePivotTranslate": (0.0, 0.0, 0.0), "rotatePivot": (0.0, 0.0, 0.0),
    "rotatePivotTranslate": (0.0, 0.0, 0.0), "rotateAxis": (0.0, 0.0, 0.0)}


def _om():
    import maya.api.OpenMaya as om
    return om


def up_axis(rows):
    """(index, sign) of the object's axis nearest world up: rows are its three axes in world."""
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


def secondary(bottom, lag):
    """The lag (a quaternion) as a world turn about the bottom: the top swings, the bottom stays."""
    b = _om().MVector(bottom.x, bottom.y, bottom.z)
    return _translation(-b) * lag.asMatrix() * _translation(b)


def _lerp(a, b, p):
    return tuple(x + (y - x) * p for x, y in zip(a, b))


class Setup(object):
    """One object's three poses (channels) and times, and what places it: rotate order, the fixed parts of
    its transform, its parent's world matrix at a frame, its bottom (object space), the arc, the heading."""

    def __init__(self, poses, times, order, fixed, parent_at, bottom, arc, heading):
        self.pose_a, self.pose_m, self.pose_b = poses
        self.t_a, self.t_m, self.t_b = times
        self.order, self.fixed, self.parent_at = order, fixed, parent_at
        self.bottom, self.arc, self.heading = bottom, arc, heading

    def world(self, pose, t):
        return local_matrix(pose[0], pose[1], self.order, self.fixed) * self.parent_at(t)


def path_world(setup, t, p):
    """The path's own pose at a frame: channels lerped A to B by p, moved so its bottom stands on the arc.
    Returns the world matrix and the lerped rotate (the euler the frame's keys stay near)."""
    om = _om()
    move = _lerp(setup.pose_a[0], setup.pose_b[0], p)
    turn = _lerp(setup.pose_a[1], setup.pose_b[1], p)
    world = local_matrix(move, turn, setup.order, setup.fixed) * setup.parent_at(t)
    base = om.MPoint(setup.bottom) * world
    goal = om.MPoint(*setup.arc.at(p))
    return world * _translation(goal - base), turn


def _rotation(matrix):
    om = _om()
    return om.MTransformationMatrix(matrix).rotation(asQuaternion=True)


def _direction(lag, heading):
    """Which way the lag swings the top, in words: back / forward / left / right, or both."""
    om = _om()
    up = om.MVector(UP)
    if heading is None:
        return "aside"
    moved = up * lag.asMatrix() - up
    left = up ^ heading
    along, side = moved * heading, moved * left
    words = []
    if abs(along) >= 0.35 * max(abs(along), abs(side)) and abs(along) > 1e-9:
        words.append("back" if along < 0 else "forward")
    if abs(side) >= 0.35 * max(abs(along), abs(side)) and abs(side) > 1e-9:
        words.append("left" if side > 0 else "right")
    return "-".join(words) if words else "none"


def _entry(arc, heading):
    """How the arc brings the object in, in words: which way the breakdown stands off the line A-B."""
    e, f = _sub(arc.b, arc.a), _sub(arc.m, arc.a)
    size = _dot(e, e)
    off = _sub(f, _scaled(e, _dot(f, e) / size)) if size > 1e-12 else f
    if _length(off) < 0.05:
        return "straight in"
    rise = off[1]
    if heading is None:
        side, aside = 0.0, math.hypot(off[0], off[2])
    else:
        side = off[0] * heading.z - off[2] * heading.x         # (up x heading) . off: + is left
        aside = abs(side)
    words = []
    if abs(rise) >= 0.35 * max(abs(rise), aside) and abs(rise) > 1e-9:
        words.append("up" if rise > 0 else "down")
    if aside >= 0.35 * max(abs(rise), aside) and aside > 1e-9:
        words.append("aside" if heading is None else ("left" if side > 0 else "right"))
    return "arc bends %.1f cm %s" % (_length(off), "-".join(words))


def compose(transition, setup):
    """Every frame's (t, translate, rotate), and what was read off the breakdown. The path's pose (its
    bottom on the arc), the lag about the bottom (the breakdown's turn against the path there, spread in
    time by the tilt spring); then the rest of the way to pose M at M's frame, pinned with a bump that is 0
    at A and B. Back into the channels through the parent."""
    om = _om()
    row_m = transition.row_at(setup.t_m)
    target_m = setup.world(setup.pose_m, setup.t_m)
    path_m, _ = path_world(setup, row_m.t, row_m.p)
    lag_m = _rotation(path_m.inverse() * target_m)
    axis, angle = lag_m.asAxisAngle()
    if angle > math.pi:
        axis, angle = -axis, 2.0 * math.pi - angle

    def placed(row):
        world, turn = path_world(setup, row.t, row.p)
        base = om.MPoint(setup.bottom) * world
        share = transition.lag_share(row.tilt)
        lag = om.MQuaternion(angle * share, axis) if angle > 1e-12 else om.MQuaternion()
        world = world * secondary(base, lag)
        return world, turn

    worlds = [placed(row) for row in transition.rows]
    world_m = worlds[transition.rows.index(row_m)][0]
    rest = world_m.inverse() * target_m
    centre = om.MPoint(setup.bottom) * world_m
    rest_axis, rest_angle = _rotation(rest).asAxisAngle()
    rest_move = centre * rest - centre

    frames = []
    for row, (world, turn) in zip(transition.rows, worlds):
        weight = pin_weight(row.t, setup.t_a, setup.t_m, setup.t_b)
        if abs(row.t - setup.t_m) < 1e-6:
            world, turn = target_m, setup.pose_m[1]
        elif weight > 0.0:
            c = om.MVector(om.MPoint(setup.bottom) * world)
            pin = (_translation(-c) * om.MQuaternion(rest_angle * weight, rest_axis).asMatrix()
                   * _translation(c + rest_move * weight))
            world = world * pin
        if row.t == transition.rows[0].t:
            turn = setup.pose_a[1]
        parent = setup.parent_at(row.t)
        t, r = channels_from_local(world * parent.inverse(), setup.order, setup.fixed, turn)
        frames.append((row.t, t, r))
    info = {"lag_deg": math.degrees(angle), "lag_dir": _direction(lag_m, setup.heading),
            "bend": setup.arc.bend(), "entry": _entry(setup.arc, setup.heading),
            "readable": transition.readable}
    return frames, info


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
    """What this script wrote on the node last (JSON on its MARKER attribute), or None."""
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=node, exists=True):
        return None
    try:
        return json.loads(cmds.getAttr(node + "." + MARKER) or "")
    except ValueError:
        return None


def _ours(memo, times):
    """A transition this script wrote, its last key unmoved."""
    return bool(memo) and bool(times) and abs(times[-1] - memo.get("tE", float("nan"))) < 1e-3


def source(node):
    """(t_a, t_m, t_b, b_time): the keys the transition runs through, and where pose B is read. A
    transition this script wrote is re-run from its own keys - M read at its frame (the key there is pose
    M), B at the last key, so editing that key edits pose B; otherwise the last three key times."""
    times = key_times(node)
    memo = remembered(node)
    if _ours(memo, times):
        if "tM" not in memo:
            raise Refusal("%s: carries a two-pose transition of an earlier version - Restore keys first"
                          % _short(node))
        return float(memo["tA"]), float(memo["tM"]), float(memo["tB"]), float(memo["tE"])
    if len(times) < 3:
        raise Refusal("%s: needs three keys on translate/rotate - from, breakdown, to - has %d"
                      % (_short(node), len(times)))
    t_a, t_m, t_b = times[-3:]
    if min(t_m - t_a, t_b - t_m) < 1.0 - 1e-6:
        raise Refusal("%s: the last three keys are less than a frame apart" % _short(node))
    return t_a, t_m, t_b, t_b


def pose_at(node, t):
    """(translate, rotate) of the node's channels at frame t, read off their curves."""
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
    """The transform's parts this script never writes (scale, shear, pivots, rotate axis) and its order."""
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
    """What a press writes on one node: the keys, the transition, every frame's channels, what M showed."""

    def __init__(self, node, times, transition, frames, info, height, notes):
        self.node = node
        self.t_a, self.t_m, self.t_b = times
        self.transition, self.frames, self.info = transition, frames, info
        self.height, self.notes = height, notes


def plan(node, given=None):
    """Everything a press writes on `node`, computed, nothing touched."""
    cmds = _cmds()
    om = _om()
    if cmds.referenceQuery(node, isNodeReferenced=True):
        raise Refusal("%s: referenced - not touched" % _short(node))
    t_a, t_m, t_b, b_time = source(node)
    poses = (pose_at(node, t_a), pose_at(node, t_m), pose_at(node, b_time))
    fixed, order = fixed_parts(node)

    def parent_at(t):
        return om.MMatrix(cmds.getAttr(node + ".parentMatrix[0]", time=t))

    worlds = [local_matrix(p[0], p[1], order, fixed) * parent_at(t) for p, t in zip(poses, (t_a, t_m, t_b))]
    rows = tuple(tuple(worlds[2].getElement(i, j) for j in range(3)) for i in range(3))
    index, sign = up_axis(rows)
    notes = []
    box = object_box(node)
    if box:
        bottom, height = bottom_and_height(box[0], box[1], index, sign, rows)
    else:
        bottom, height = fixed["rotatePivot"], 0.0
    if height < 1e-6:
        height = FALLBACK_HEIGHT
        notes.append("no geometry - its pivot taken as the bottom, %g cm as the height" % FALLBACK_HEIGHT)
    bases = [om.MPoint(bottom) * w for w in worlds]
    arc = Arc(*[(b.x, b.y, b.z) for b in bases])
    up = om.MVector(UP)
    chord = bases[2] - bases[0]
    flat = chord - up * (chord * up)
    heading = flat.normal() if flat.length() > 1e-4 else None
    transition = solve(t_a, t_m, t_b, arc.s_m, arc.length / height, given)
    if transition.clamped:
        notes.append("overshoot held to %.1f %% - the last stretch is too slow for more"
                     % (100 * transition.overshoot))
    setup = Setup(poses, (t_a, t_m, t_b), order, fixed, parent_at, bottom, arc, heading)
    frames, info = compose(transition, setup)
    if info["lag_deg"] > 0.05 and not info["readable"]:
        notes.append("the breakdown sits where the top barely lags - its lag taken as the peak")
    return Plan(node, (t_a, t_m, t_b), transition, frames, info, height, notes)


def _write(p, skip):
    """Keys on every frame of the plan; the A key kept (its out tangent made auto), the marker set."""
    cmds = _cmds()
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
    memo = {"tA": p.t_a, "tM": p.t_m, "tB": p.t_b, "tE": p.transition.end, "params": p.transition.params}
    cmds.setAttr(p.node + "." + MARKER, json.dumps(memo), type="string")


def describe(p, skip):
    tr, info = p.transition, p.info
    lag = ("lag %.1f deg %s" % (info["lag_deg"], info["lag_dir"])) if info["lag_deg"] > 0.05 else "no lag"
    text = ("%s: frames %g-%g | breakdown at %g: %s, %s | settles %g frames after B"
            % (_short(p.node), p.t_a, tr.end, p.t_m, lag, info["entry"], tr.end - p.t_b))
    notes = list(p.notes)
    if skip:
        notes.append("not written (locked or driven): %s" % ", ".join(skip))
    return text + ("" if not notes else " | " + "; ".join(notes))


class _Chunk(object):
    """One undo step for a press."""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        _cmds().undoInfo(openChunk=True, chunkName=self.name)

    def __exit__(self, *exc):
        _cmds().undoInfo(closeChunk=True)
        return False


def apply(nodes, given=None):
    """Build the transition on every node; one undo step. Returns one line per node."""
    lines = []
    with _Chunk("skeldarPhysStop"):
        for node in nodes:
            try:
                p = plan(node, given)
                skip = blocked(node)
                if len(skip) == len(CHANNELS):
                    raise Refusal("%s: every translate/rotate channel is locked or driven" % _short(node))
                _write(p, skip)
                lines.append(describe(p, skip))
            except Refusal as refusal:
                lines.append(str(refusal))
    return lines


def restore(nodes):
    """Back to the keys the transition was built from (A, the breakdown, B); the marker removed."""
    cmds = _cmds()
    lines = []
    with _Chunk("skeldarPhysStopRestore"):
        for node in nodes:
            memo = remembered(node)
            if not _ours(memo, key_times(node)):
                lines.append("%s: no transition of this script to restore" % _short(node))
                continue
            keys = []
            if "tM" in memo:
                keys.append((memo["tM"], pose_at(node, memo["tM"])))
            keys.append((memo["tB"], pose_at(node, memo["tE"])))
            skip = blocked(node)
            for i, ch in enumerate(CHANNELS):
                if ch in skip:
                    continue
                cmds.cutKey(node, attribute=ch, time=(memo["tA"] + 1e-3, FOREVER), clear=True)
                for t, pose in keys:
                    value = pose[0][i] if i < 3 else pose[1][i - 3]
                    cmds.setKeyframe(node, attribute=ch, time=t, value=value,
                                     inTangentType="auto", outTangentType="auto")
            cmds.deleteAttr(node + "." + MARKER)
            lines.append("%s: back to its keys at %s" % (
                _short(node), ", ".join("%g" % t for t in [memo["tA"]] + [k[0] for k in keys])))
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


# ---------------------------------------------------------------------------------------------------------
# 4. The hub card (maya.cmds) - Tail Builder
# ---------------------------------------------------------------------------------------------------------

HUB_SECTION = "tailbuilder"
SUBTITLE = "skeldarTailBuilderSubtitle"
STATUS = "skeldarTailBuilderStatus"
APPLY_BTN = "skeldarTailBuilderApply"
RESTORE_BTN = "skeldarTailBuilderRestore"
RESET_BTN = "skeldarTailBuilderReset"
#  The sliders' memory keeps the prototype's names (2026-10-10): the values the animator set there come
#  back in the card.
OPTION = "skeldarPhysStop_"
LABELS = {
    "overshoot": ("Overshoot, %", 0.1,
                  "How far past B the first swing goes, in % of the path (the cube: 3)"),
    "swing": ("Swing length, fr", 0.25,
              "Frames of one swing past B and back (the cube: 5)"),
    "weight": ("Weight", 0.05,
               "Heavier swings more times before it stops (the cube: 1)"),
}
INTRO = ("Select objects whose last three keys are the poses to go from (A), through (M) and to (B), "
         "then Apply. The path arcs through M: raise, lower or move M aside to bring the object in from "
         "above, below or the side; tilt it at M to set how far its top lags.")
TIPS = {
    "restore": "Back to the three keys the tail was built from (A, M, B as they are now)",
    "reset": "The three controls back to the cube's values; a selected tail is built again with them",
}
NOTHING = "Select objects with three keys: from, breakdown, to"
#  The refresh job of each card standing: '' the hub's, a popup copy's tag its own (the 2026-10-09 rule:
#  closing a popup kills only its own job).
JOB = {}


def _control(name):
    return OPTION + name + "Slider"


def _stored(name, default):
    cmds = _cmds()
    key = OPTION + name
    return cmds.optionVar(q=key) if cmds.optionVar(exists=key) else default


def values():
    """The three controls: the card's sliders where the card stands (and remembered), else what was
    remembered - so a hotkey row presses with the card closed."""
    cmds = _cmds()
    out = {}
    for name, default in DEFAULTS:
        if cmds.floatSliderGrp(_control(name), exists=True):
            out[name] = float(cmds.floatSliderGrp(_control(name), query=True, value=True))
            cmds.optionVar(floatValue=(OPTION + name, out[name]))
        else:
            out[name] = float(_stored(name, default))
    return params(**out)


def selection_line(nodes):
    """The card's subtitle: what Apply would take."""
    if not nodes:
        return NOTHING
    if len(nodes) > 1:
        return "%d objects selected" % len(nodes)
    node = nodes[0]
    try:
        t_a, t_m, t_b, b_time = source(node)
    except Refusal as refusal:
        return str(refusal)
    except Exception:                                        # noqa: BLE001
        return _short(node)
    if b_time != t_b:
        return "%s: a tail %g-%g, M at %g, B at %g" % (_short(node), t_a, b_time, t_m, t_b)
    return "%s: A at %g, M at %g, B at %g" % (_short(node), t_a, t_m, t_b)


def status(lines):
    """The card's line - and the hub's one message line. Answers the text, so a hotkey row can show it
    when the card is closed."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    message = "\n".join(lines) if isinstance(lines, (list, tuple)) else lines
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=message)
        hubstyle.tell(STATUS, message)
    return message


def refresh(*_):
    """The subtitle, from the selection."""
    cmds = _cmds()
    if not cmds.text(SUBTITLE, exists=True):
        return
    try:
        line = selection_line(selected())
    except Exception:                                        # noqa: BLE001
        return
    cmds.text(SUBTITLE, edit=True, label=line)


def _press(action):
    try:
        lines = action()
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        lines = ["Tail Builder failed: %s" % exc]
    refresh()
    return status(lines)


def press_apply(*_):
    """Apply: the tail on every selected object."""
    def run():
        nodes = selected()
        return apply(nodes, values()) if nodes else [NOTHING]
    return _press(run)


def slider_changed(*_):
    """A released slider re-runs what already carries a tail; anything else waits for Apply."""
    def run():
        given = values()
        nodes = selected()
        if nodes and all(remembered(n) for n in nodes):
            return apply(nodes, given)
        return ["Press Apply to build the tail."] if nodes else [NOTHING]
    return _press(run)


def press_restore(*_):
    def run():
        nodes = selected()
        return restore(nodes) if nodes else ["Select the objects to put back on their three keys."]
    return _press(run)


def press_reset(*_):
    cmds = _cmds()
    for name, default in DEFAULTS:
        if cmds.floatSliderGrp(_control(name), exists=True):
            cmds.floatSliderGrp(_control(name), edit=True, value=default)
        cmds.optionVar(floatValue=(OPTION + name, default))
    return slider_changed()


def _button(name, label, role, icon, tip, press):
    import maya_hubstyle as hubstyle
    return hubstyle.mark(_cmds().button(name, label=label, annotation=tip,
                                        height=hubstyle.height("button", 28),
                                        command=lambda *_: press()), role, icon)


def build_panel():
    """The card into the current layout: what the selection holds, the three controls, Apply / Restore
    keys / Reset, the status line."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="", align="left"), "subtitle")
    defaults = dict(DEFAULTS)
    for name, _ in DEFAULTS:
        low, high = RANGES[name]
        label, step, tip = LABELS[name]
        cmds.floatSliderGrp(_control(name), label=label, field=True, minValue=low, maxValue=high,
                            fieldMinValue=low, fieldMaxValue=high, step=step, precision=2,
                            value=float(_stored(name, defaults[name])),
                            columnWidth3=hubstyle.pick((100, 46, 110), (100, 50, 150)), adjustableColumn=3,
                            height=hubstyle.height("small", 22), annotation=tip,
                            changeCommand=slider_changed)
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4), (3, "both", 4)])
    _button(APPLY_BTN, "Apply", "primary", "wave-sine", INTRO, press_apply)
    _button(RESTORE_BTN, "Restore keys", "secondary", "arrow-back-up", TIPS["restore"], press_restore)
    _button(RESET_BTN, "Reset", "secondary", "refresh", TIPS["reset"], press_reset)
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    cmds.setParent("..")
    start()
    refresh()
    return column


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    """This card's own refresh on every selection change (per card: a popup copy's job dies with the
    copy and leaves the hub's)."""
    import maya_hubcopy as hubcopy
    cmds = _cmds()
    standing = set(scope.tag for scope in hubcopy.live())
    for key in [k for k in JOB if k and k not in standing]:
        del JOB[key]
    old = JOB.pop(_card_key(), None)
    if old is not None:
        try:
            if cmds.scriptJob(exists=old):
                cmds.scriptJob(kill=old, force=True)
        except Exception:                                    # noqa: BLE001
            pass
    import maya_hubqt
    #  a hidden card refreshes when it is next shown (2026-10-17, maya_hubqt.when_seen)
    JOB[_card_key()] = cmds.scriptJob(event=["SelectionChanged", maya_hubqt.seen_only(STATUS, refresh)],
                                      parent=STATUS)


def is_open():
    return bool(_cmds().text(STATUS, exists=True))


def show_window():
    """The hub, on the Tail Builder section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
