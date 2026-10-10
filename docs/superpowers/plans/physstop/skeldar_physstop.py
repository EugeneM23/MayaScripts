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
K_TILT = 47.10       # deg of tilt per object height per frame of speed, at overlap 1
K_SINK = 0.526       # sink, in heights, per object height per frame of speed, at weight 1
K_SWAY = 0.217       # sway, in heights, per object height per frame of speed, at sway 1
SWAY_RATE = 0.75     # the sway's frequency against the other springs'
K_YAW = 51.9         # deg of yaw per object height of sway

TILT_LIMIT = 40.0    # deg: the tilt's drive saturates here (tanh) - a small object flying far stays sane
SINK_LIMIT = 0.5     # heights: the sink's drive saturates here
SWAY_LIMIT = 0.25    # heights: the sway's drive saturates here (the yaw follows it)
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
                _step(sink, SINK_LIMIT * math.tanh(K_SINK * given["weight"] * speed * reach / SINK_LIMIT),
                      omega, zeta, dt)
                _step(sway, SWAY_LIMIT * math.tanh(K_SWAY * given["sway"] * abs(ahead) / SWAY_LIMIT),
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
    """What a press writes on one node: the keys A and B, the transition, every frame's channels."""

    def __init__(self, node, t_a, t_b, transition, frames, height, notes):
        self.node, self.t_a, self.t_b = node, t_a, t_b
        self.transition, self.frames, self.height, self.notes = transition, frames, height, notes


def plan(node, given=None, axis="Auto"):
    """Everything a press writes on `node`, computed, nothing touched."""
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
        notes.append("overshoot held to %.1f %% - a slow move cannot arrive faster" % (100 * transition.overshoot))
    frames = channel_frames(transition, pose_a, pose_b, order, fixed, parent_at, bottom, heading)
    return Plan(node, t_a, t_b, transition, frames, height, notes)


def _write(p, skip, axis):
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
    memo = {"tA": p.t_a, "tB": p.t_b, "tE": p.transition.end, "params": p.transition.params, "axis": axis}
    cmds.setAttr(p.node + "." + MARKER, json.dumps(memo), type="string")


def describe(p, skip):
    tr = p.transition
    text = "%s: frames %g-%g, tilt up to %.1f deg, sink %.2f cm, sway %.2f cm, settles %g frames after B" % (
        _short(p.node), p.t_a, tr.end, tr.peak_tilt, tr.peak_sink, tr.peak_sway, tr.end - p.t_b)
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


def apply(nodes, given=None, axis="Auto"):
    """Build the transition on every node; one undo step. Returns one line per node."""
    lines = []
    with _Chunk("skeldarPhysStop"):
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
    with _Chunk("skeldarPhysStopRestore"):
        for node in nodes:
            memo = remembered(node)
            times = key_times(node)
            if not memo or not times or abs(times[-1] - memo["tE"]) > 1e-3:
                lines.append("%s: no transition of this script to restore" % _short(node))
                continue
            pose_b = pose_at(node, memo["tE"])
            skip = blocked(node)
            for i, ch in enumerate(CHANNELS):
                if ch in skip:
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


if __name__ == "__main__":
    pass
