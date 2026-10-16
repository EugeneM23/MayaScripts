"""The ragdoll's pure half (2026-10-16): which bones make which body, where a body's capsule runs,
how heavy it is, how its joint to its parent is framed and limited, how strong its muscles are,
how fast it starts, and where every game bone stands once the bodies have moved. numpy only.

Matrices are Maya's: 4x4, ROW vectors, `world = local . parent`, the translation in the last row.
A flat 16-float list (`cmds.getAttr(... .worldMatrix[0])`) is `mat(flat)`.

The body table is UE's names - every rig of ours (Manny, Creep, Orc D) carries them. A bone the
table names and the skeleton lacks is left out of its body; a body whose FIRST bone is missing is
refused by name (`missing_bodies`).

Measured (mayapy, 2026-10-16) and relied on here:
- Bullet's angular limits are DEGREES, in the constraint transform's frame; a SixDOF2 constraint
  (type 5) takes angular springs whose rest is the pose at the start; stiffness ~8 x m g L holds
  a limb, ~0.1 x does nothing.
- a body's `initialVelocity` is cm per second, `initialAngularVelocity` DEGREES per second, both
  in world axes; the solver must step one frame at a time.
- the solver's gravity is metres (-9.8): a cm scene wants -980.
"""

import math

import numpy as np

G = 980.0                  # cm / s^2
MUSCLE_GAIN = 8.0          # Strength 1 = this many times the torque gravity puts on the joint
RADIUS_PERCENTILE = 50.0   # of the skinned points' distance from a body's axis (70 read the
                           # Creep's right calf 14.5 cm against its left 8.7)
RADIUS_SHARE = 0.12        # a body with no skinned point: this share of its length
MIN_RADIUS = 1.0           # cm
HINGE_BENT = 10.0          # degrees: a knee or elbow bent less reads as straight
HINGE_FLEX = 150.0         # the hinge's whole range from straight
HINGE_SLACK = 2.0          # degrees past straight a hinge may go
HINGE_SIDE = 5.0           # a hinge's other two axes, each way

#  (key, bones, parent body, joint kind, mass share, axis start, axis end)
#  an axis end is a bone, or ("extend", a, b, k): b + (b - a) * k
#  de Leva's male segment masses: the trunk split into pelvis / abdomen / thorax
BODIES = (
    ("pelvis", ("pelvis",), None, None, 0.1117, "thigh_l", "thigh_r"),
    ("spine_lo", ("spine_01", "spine_02"), "pelvis", "spine", 0.1633, "spine_01", "spine_03"),
    ("spine_hi", ("spine_03", "spine_04", "spine_05", "clavicle_l", "clavicle_r"), "spine_lo",
     "spine", 0.1596, "spine_03", "neck_01"),
    ("head", ("neck_01", "neck_02", "head"), "spine_hi", "neck", 0.0694, "neck_01",
     ("extend", "neck_01", "head", 1.4)),
)
for _s in ("l", "r"):
    BODIES += (
        ("upperarm_" + _s, ("upperarm_" + _s,), "spine_hi", "shoulder", 0.0271,
         "upperarm_" + _s, "lowerarm_" + _s),
        ("lowerarm_" + _s, ("lowerarm_" + _s,), "upperarm_" + _s, "elbow", 0.0162,
         "lowerarm_" + _s, "hand_" + _s),
        ("hand_" + _s, ("hand_" + _s,), "lowerarm_" + _s, "wrist", 0.0061, "hand_" + _s,
         ("extend", "hand_" + _s, "middle_01_" + _s, 0.9)),
        ("thigh_" + _s, ("thigh_" + _s,), "pelvis", "hip", 0.1416, "thigh_" + _s, "calf_" + _s),
        ("calf_" + _s, ("calf_" + _s,), "thigh_" + _s, "knee", 0.0433, "calf_" + _s,
         "foot_" + _s),
        ("foot_" + _s, ("foot_" + _s, "ball_" + _s), "calf_" + _s, "ankle", 0.0137,
         "foot_" + _s, ("extend", "foot_" + _s, "ball_" + _s, 0.35)),
    )
del _s

#  (twist, swing) each way, degrees, about the pose at the fall's first frame
BALL = {
    "spine": (15.0, 25.0),
    "neck": (40.0, 40.0),
    "shoulder": (60.0, 85.0),
    "wrist": (40.0, 60.0),
    "hip": (30.0, 70.0),
    "ankle": (15.0, 35.0),
}
HINGES = ("elbow", "knee")
#  a hand's axis falls back to the forearm's direction when the skeleton has no middle finger
HAND_FALLBACK = 0.45


# ------------------------------------------------------------------ matrices

def mat(flat):
    return np.array(flat, dtype=float).reshape(4, 4)


def flat(m):
    return [float(v) for v in np.asarray(m).reshape(16)]


def pos(m):
    return np.array(m[3, :3], dtype=float)


def rot(m):
    """The 3x3 rotation rows of `m`, orthonormalised (scale and shear dropped)."""
    x = _unit(m[0, :3])
    y = m[1, :3] - np.dot(m[1, :3], x) * x
    y = _unit(y)
    return np.array([x, y, np.cross(x, y)])


def rigid(m):
    out = np.identity(4)
    out[:3, :3] = rot(m)
    out[3, :3] = pos(m)
    return out


def frame(rows, origin):
    out = np.identity(4)
    out[:3, :3] = rows
    out[3, :3] = origin
    return out


def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def perpendicular(axis, hint):
    """A unit vector square to `axis`, as near `hint` as can be (any square one when `hint` runs
    along the axis)."""
    axis = _unit(axis)
    for candidate in (hint, (0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)):
        c = np.asarray(candidate, dtype=float)
        v = c - np.dot(c, axis) * axis
        if np.linalg.norm(v) > 1e-6:
            return _unit(v)
    return np.array([0.0, 1.0, 0.0])


def angle(u, v):
    """Degrees between two directions."""
    c = float(np.clip(np.dot(_unit(u), _unit(v)), -1.0, 1.0))
    return math.degrees(math.acos(c))


# ------------------------------------------------------------------ the bodies

def missing_bodies(names):
    """The bodies whose first bone `names` (a skeleton's leaves) lacks, or whose axis cannot be
    read - in table order. Empty: the skeleton makes a whole ragdoll."""
    names = set(names)
    out = []
    for key, bones, _parent, _kind, _share, start, end in BODIES:
        need = [bones[0], start]
        if not key.startswith("hand"):              # a hand falls back to its forearm
            need += list(end[1:3]) if isinstance(end, tuple) else [end]
        if any(n not in names for n in need):
            out.append(key)
    return out


def body_of_bone():
    """{bone: body key} of every bone the table names."""
    out = {}
    for key, bones, *_rest in BODIES:
        for bone in bones:
            out[bone] = key
    return out


def riders(parents):
    """{bone: body key} of EVERY bone that moves with a body: the table's bones, and every other
    bone under one of them (fingers, twist, helpers, weapon) with its nearest grouped ancestor's.
    A bone above the pelvis (the root, the root's ik helpers) is in no body. `parents`
    {bone: parent bone or None}."""
    grouped = body_of_bone()
    out = {}
    for bone in parents:
        walk = bone
        while walk is not None:
            if walk in grouped:
                out[bone] = grouped[walk]
                break
            walk = parents.get(walk)
    return out


def axis_points(key, worlds):
    """(start, end) world points of a body's capsule axis at one pose: `worlds` {bone: 4x4}."""
    row = [r for r in BODIES if r[0] == key][0]
    start, end = row[5], row[6]
    a = pos(worlds[start])
    if isinstance(end, tuple):
        _kind, p, q, k = end
        if q in worlds and p in worlds:
            b = pos(worlds[q]) + (pos(worlds[q]) - pos(worlds[p])) * k
        else:                       # a hand with no middle finger: the forearm, carried on
            fore = key.replace("hand", "lowerarm")
            b = a + (a - pos(worlds[fore])) * HAND_FALLBACK
    else:
        b = pos(worlds[end])
    return a, b


def body_frame(key, worlds):
    """The body's frame at one pose: the capsule's centre, X down its axis (start to end), Y as
    near the first bone's own Y as is square to it."""
    a, b = axis_points(key, worlds)
    x = _unit(b - a)
    first = [r for r in BODIES if r[0] == key][0][1][0]
    y = perpendicular(x, rot(worlds[first])[1])
    return frame(np.array([x, y, np.cross(x, y)]), (a + b) * 0.5)


def radius(points, a, b, length):
    """The capsule's radius from the skinned `points` (n x 3) heaviest on the body: the
    RADIUS_PERCENTILE of their distance from the segment a-b; none - a share of its length."""
    if points is None or len(points) == 0:
        return max(MIN_RADIUS, RADIUS_SHARE * length)
    pts = np.asarray(points, dtype=float)
    d = b - a
    span = float(np.dot(d, d)) or 1.0
    t = np.clip(((pts - a) @ d) / span, 0.0, 1.0)
    near = a + t[:, None] * d
    dist = np.linalg.norm(pts - near, axis=1)
    return max(MIN_RADIUS, float(np.percentile(dist, RADIUS_PERCENTILE)))


def capsule_length(length, r):
    """Bullet's capsule `length` runs TIP TO TIP, caps included (measured 2026-10-16: a capsule given
    the cylinder's length rested a cap's worth into the floor wherever it lay tilted). The capsule
    reaches half a radius past each end of its segment - the bodies touch at the joints."""
    return length + r


def masses(total, keys):
    """{body: kg}: `total` shared by de Leva's shares, renormalised over the bodies present."""
    share = dict((r[0], r[4]) for r in BODIES if r[0] in keys)
    whole = sum(share.values()) or 1.0
    return dict((k, total * s / whole) for k, s in share.items())


def children(keys):
    """{body: [child bodies]} of the table among `keys`."""
    out = dict((k, []) for k in keys)
    for key, _b, parent, *_rest in BODIES:
        if key in keys and parent in out:
            out[parent].append(key)
    return out


def subtree(key, kids):
    out, todo = [], [key]
    while todo:
        k = todo.pop()
        out.append(k)
        todo.extend(kids.get(k, ()))
    return out


def stiffness(strength, carried, lever):
    """A joint's spring stiffness: `strength` x MUSCLE_GAIN x the torque gravity puts on the mass
    it carries at its lever."""
    return max(0.0, strength) * MUSCLE_GAIN * carried * G * max(lever, 1.0)


def carried(anchor, key, kids, mass, centres):
    """(kg the joint at `anchor` carries - its child body and everything below - and that mass's
    lever: the distance from the anchor to its centre)."""
    keys = subtree(key, kids)
    m = sum(mass[k] for k in keys)
    if m <= 0:
        return 0.0, 0.0
    com = sum(mass[k] * centres[k] for k in keys) / m
    return m, float(np.linalg.norm(com - anchor))


# ------------------------------------------------------------------ the joints

def facing(worlds):
    """(left, up, forward) of the body at one pose: left from the right hip to the left, up from
    the pelvis to the chest, forward their cross product (Maya: +X left, +Y up, +Z forward)."""
    left = _unit(pos(worlds["thigh_l"]) - pos(worlds["thigh_r"]))
    chest = pos(worlds.get("spine_03", worlds["pelvis"]))
    up = perpendicular(left, chest - pos(worlds["pelvis"]))
    return left, up, np.cross(left, up)


def hinge_axis(kind, parent_dir, child_dir, forward):
    """(axis, bend): the hinge's axis - flexing turns the child about it by a POSITIVE angle - and
    its bend now (degrees). Bent past HINGE_BENT: the normal of the two bones' plane. Straight: a
    knee flexes the shin backward, an elbow the forearm forward."""
    bend = angle(parent_dir, child_dir)
    if bend > HINGE_BENT:
        return _unit(np.cross(parent_dir, child_dir)), bend
    toward = -forward if kind == "knee" else forward
    side = perpendicular(parent_dir, toward)
    return _unit(np.cross(parent_dir, side)), bend


def joint_frame(kind, anchor, parent_dir, child_dir, forward, child_y):
    """(4x4 world frame of the joint, (min xyz), (max xyz) degrees). A hinge: X its axis, Y down the
    child, limits HINGE_FLEX from straight on X and HINGE_SIDE on the others. A ball: X down the
    child (its twist), Y as near the child's own Y as is square, limits BALL[kind] about the pose
    now."""
    child_dir = _unit(child_dir)
    if kind in HINGES:
        x, bend = hinge_axis(kind, parent_dir, child_dir, forward)
        y = perpendicular(x, child_dir)
        lo = (-bend - HINGE_SLACK, -HINGE_SIDE, -HINGE_SIDE)
        hi = (HINGE_FLEX - bend, HINGE_SIDE, HINGE_SIDE)
    else:
        x = child_dir
        y = perpendicular(x, child_y)
        twist, swing = BALL[kind]
        lo, hi = (-twist, -swing, -swing), (twist, swing, swing)
    return frame(np.array([x, y, np.cross(x, y)]), anchor), lo, hi


# ------------------------------------------------------------------ the start

def velocities(before, now, fps):
    """(linear cm/s, angular deg/s) of a body that stood at `before` one frame before `now` (4x4
    world frames): Bullet's initialVelocity and initialAngularVelocity, both world axes."""
    linear = (pos(now) - pos(before)) * fps
    # row vectors: R_now = R_before . D, D the world turn of the frame
    d = rot(before).T @ rot(now)
    m = d.T                                            # column-vector form
    c = float(np.clip((np.trace(m) - 1.0) * 0.5, -1.0, 1.0))
    theta = math.acos(c)
    if theta < 1e-9:
        return linear, np.zeros(3)
    if math.pi - theta < 1e-6:                         # a half turn in one frame: no direction
        return linear, np.zeros(3)
    axis = np.array([m[2, 1] - m[1, 2], m[0, 2] - m[2, 0], m[1, 0] - m[0, 1]]) / (2 * math.sin(theta))
    return linear, axis * math.degrees(theta) * fps


def fade_keys(start, fade, value):
    """[(time, stiffness)] of a muscle that holds `value` at `start` and lets go by `start + fade`
    (fade 0: no muscle at all)."""
    if fade <= 0 or value <= 0:
        return [(start, 0.0)]
    return [(start, value), (start + fade, 0.0)]


# ------------------------------------------------------------------ the bake

def offsets(worlds, bodies_now, rider_of):
    """{bone: (body, 4x4 local in it)} of every riding bone at the fall's first frame: `worlds`
    {bone: 4x4}, `bodies_now` {body: 4x4}, `rider_of` {bone: body}."""
    out = {}
    for bone, body in rider_of.items():
        if bone in worlds and body in bodies_now:
            out[bone] = (body, rigid(worlds[bone]) @ np.linalg.inv(bodies_now[body]))
    return out


def bone_worlds(local, bodies, fixed):
    """{bone: 4x4 world} at one frame: each riding bone's `local` (from `offsets`) carried by its
    body's world now (`bodies` {body: 4x4}); every other bone where it stood (`fixed`)."""
    out = dict(fixed)
    for bone, (body, m) in local.items():
        out[bone] = m @ bodies[body]
    return out


def floor_height(skinned, capsules):
    """The floor under the feet at the fall: the lowest skinned point of the two feet (their soles),
    else - no skin - the lowest (y - radius) of the foot capsules' axis ends. `skinned` [n x 3 or
    None per foot], `capsules` [(start, end, radius) per foot]."""
    lows = [float(np.min(np.asarray(p)[:, 1])) for p in skinned if p is not None and len(p)]
    if lows:
        return min(lows)
    return min(min(a[1], b[1]) - r for a, b, r in capsules)


def span(highlight, current, length):
    """(a, b): the time slider's highlight ([start, end) - its last whole frame is end - 1), else
    the current frame for `length` frames; whole frames."""
    if highlight:
        a, b = int(round(highlight[0])), int(round(highlight[1])) - 1
    else:
        a = int(round(current))
        b = a + int(round(length))
    return a, b


# ---------------------------------------------------------------- impulses (2026-10-16)

SHAFT_CM = 6.0             # an impulse arrow's shaft: this many cm a m/s of its speed


def _segment_distance(p, a, b):
    ab = b - a
    t = float(np.clip(np.dot(p - a, ab) / max(float(np.dot(ab, ab)), 1e-12), 0.0, 1.0))
    return float(np.linalg.norm(p - (a + ab * t)))


def nearest_body(point, axes):
    """The body whose capsule axis passes nearest `point`: `axes` {key: (start, end)}."""
    p = np.asarray(point, dtype=float)
    return min(axes, key=lambda k: (_segment_distance(p, *axes[k]), k))


def in_body(arrow, body):
    """(tip, direction) of an arrow (4x4, its +Z the direction, its origin the tip) in a body's
    frame (4x4): what rides the body as it moves."""
    local = rigid(arrow) @ np.linalg.inv(body)
    return pos(local), _unit(rot(local)[2])


def hit_frame(frame, a, b):
    """The step an arrow at `frame` hits on, or None: at or before the fall's first frame, the
    first step (`a + 1`); after its last, none."""
    f = int(round(frame))
    if f > b:
        return None
    return max(f, a + 1)


def impulse(mass, speed, tip, direction, body):
    """(J, point): the impulse (kg*cm/s, world) knocking a body of `mass` kg at `speed` m/s along
    `direction`, and its point as Bullet takes it - an offset from the body's centre in world axes.
    `tip` / `direction` in the body's frame, `body` its 4x4 now."""
    d = _unit(np.asarray(direction, dtype=float) @ rot(body))
    tip_w = np.append(np.asarray(tip, dtype=float), 1.0) @ body
    return d * (float(mass) * float(speed) * 100.0), tip_w[:3] - pos(body)
