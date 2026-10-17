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
from collections import OrderedDict

import numpy as np

G = 980.0                  # cm / s^2
MUSCLE_GAIN = 8.0          # Strength 1 = this many times the torque gravity puts on the joint
RADIUS_PERCENTILE = 50.0   # of the skinned points' distance from a body's axis (70 read the
                           # Creep's right calf 14.5 cm against its left 8.7)
RADIUS_SHARE = 0.12        # a body with no skinned point: this share of its length
MIN_RADIUS = 1.0           # cm
HINGE_BENT = 10.0          # degrees: a knee or elbow bent less reads as straight
HINGE_FLEX = 145.0         # the hinge's whole range from straight (the elbow's, AAOS 0-150)
HINGE_SLACK = 2.0          # degrees past straight a hinge may go
HINGE_SIDE = 5.0           # a hinge's other two axes, each way
#  per hinge (flexion from straight, hyperextension), AAOS norms: elbow 0-150 (a few degrees of
#  hyperextension are common), knee 0-135 (none to speak of)
HINGE_RANGE = {"elbow": (145.0, 5.0), "knee": (135.0, 2.0)}

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

#  A ball joint's range, degrees, about the ANATOMICAL NEUTRAL (standing, arms hanging, feet forward),
#  from the human norms (AAOS / Kendall; the thoracolumbar spine's 80 / 25 / 35 / 45 split between the
#  ragdoll's two spine joints), a little inside the active range: a ragdoll's joints are passive.
#  (neutral direction, flexion toward, twist each way, (adduction, abduction), (extension, flexion))
#  - the neutral and the flexion are words read on the body's rest facing (`anatomical_frame`).
ANATOMY = {
    "spine": ("up", "forward", 20.0, (20.0, 20.0), (15.0, 40.0)),
    "neck": ("up", "forward", 60.0, (40.0, 40.0), (45.0, 45.0)),
    "shoulder": ("down", "forward", 80.0, (40.0, 150.0), (60.0, 170.0)),
    "hip": ("down", "forward", 45.0, (30.0, 45.0), (30.0, 120.0)),
    "wrist": ("parent", "forward", 80.0, (25.0, 25.0), (70.0, 80.0)),
    "ankle": ("foot", "parent", 15.0, (25.0, 25.0), (20.0, 50.0)),
}
#  Maya's SixDOF2 composes Rz . Ry . Rx: its middle axis (Y, here abduction) must stay inside +-90
MIDDLE_LIMIT = 85.0
LIMIT_GRACE = 1.0          # degrees a joint may always move each way, whatever the pose now
CONE_SLACK = 10.0          # degrees a corner of Bullet's box may reach past the cone
CONE_SHRINK_MIN = 0.5      # the least a box's swing sides are shrunk to
HINGES = ("elbow", "knee")
#  kept for a scene whose rest cannot be read: (twist, swing) about the pose now
BALL = {
    "spine": (15.0, 25.0),
    "neck": (40.0, 40.0),
    "shoulder": (60.0, 85.0),
    "wrist": (40.0, 60.0),
    "hip": (30.0, 70.0),
    "ankle": (15.0, 35.0),
}

#  Self-collision. Maya's Bullet filters collisions on 16 bits (measured 2026-10-16: a group of 1<<17
#  fell through the floor), so the 16 bodies share 12 groups - a limb's first body alone, the rest of
#  the limb together (they are jointed or near enough to never meet). Two groups do not collide when
#  any of their bodies are jointed or already touch at the fall's first frame: Bullet pushes touching
#  capsules apart on its first step, and a hand resting on a thigh threw the Creep's pelvis 1.6 cm
#  in one frame (0.6 with the pair left apart, as the clip moves).
WORLD_BIT = 1
COLLISION_GROUPS = ("pelvis", "spine_lo", "spine_hi", "head", "upperarm_l", "forearm_l",
                    "upperarm_r", "forearm_r", "thigh_l", "shin_l", "thigh_r", "shin_r")
WEAPON_BIT = 1 << (len(COLLISION_GROUPS) + 1)
OVERLAP_SHARE = 0.0        # of the thinner radius: any touch
#  Bullet's own ragdoll demo damps 0.05 / 0.85; a body's soft tissue takes energy - ours a little
#  less, so a fall still reads as a fall
LINEAR_DAMPING = 0.05
ANGULAR_DAMPING = 0.6
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
        flex, slack = HINGE_RANGE.get(kind, (HINGE_FLEX, HINGE_SLACK))
        lo = (-bend - slack, -HINGE_SIDE, -HINGE_SIDE)
        hi = (max(flex - bend, LIMIT_GRACE), HINGE_SIDE, HINGE_SIDE)
    else:
        x = child_dir
        y = perpendicular(x, child_y)
        twist, swing = BALL[kind]
        lo, hi = (-twist, -swing, -swing), (twist, swing, swing)
    return frame(np.array([x, y, np.cross(x, y)]), anchor), lo, hi


def side_of(key):
    """+1 a left body, -1 a right one, 0 the midline."""
    return 1 if key.endswith("_l") else -1 if key.endswith("_r") else 0


def turn_between(a, b):
    """The least 3x3 row-vector turn taking direction `a` onto `b` (`a @ R` along `b`)."""
    a, b = _unit(a), _unit(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.identity(3)
        p = perpendicular(a, (0.0, 1.0, 0.0))          # a half turn about any square axis
        return 2.0 * np.outer(p, p) - np.identity(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    col = np.identity(3) + k + k @ k * (1.0 / (1.0 + c))   # column form: col @ a = b
    return col.T


def euler_xyz(m):
    """Bullet's X, Y, Z angles (degrees) of a 3x3 COLUMN rotation `m` (the child's axes in the
    joint's frame) - each positive a right-handed turn of the child about the joint's axis. Maya's
    SixDOF2 composes them as m = Rz . Ry . Rx (measured 2026-10-16: a joint locked at (30, 20, 10)
    settled on that product to 0.0000, every other order 0.05-0.19 off); Y is the middle axis."""
    y = math.asin(float(np.clip(-m[2, 0], -1.0, 1.0)))
    x = math.atan2(m[2, 1], m[2, 2])
    z = math.atan2(m[1, 0], m[0, 0])
    return np.degrees([x, y, z])


def anatomical_frame(kind, key, facing_rest, parent_dir_rest):
    """3x3 rows of a ball joint's NEUTRAL frame at the rest pose: X the child's neutral direction
    (its twist), Z the flexion axis - a positive turn about it takes the child toward its flexion -
    Y = Z x X, so a positive turn about Y takes the child toward -Z: toward the body's LEFT for a
    leg or an arm (abduction of a left limb, adduction of a right one)."""
    left, up, forward = facing_rest
    neutral, toward = ANATOMY[kind][0], ANATOMY[kind][1]
    words = {"up": up, "down": -up, "forward": forward, "parent": _unit(parent_dir_rest)}
    if neutral == "foot":
        n = perpendicular(parent_dir_rest, forward)
    else:
        n = _unit(words[neutral])
    f = words[toward]
    z = np.cross(n, f)
    if np.linalg.norm(z) < 1e-6:
        z = np.cross(n, left)
    z = _unit(z)
    return np.array([n, np.cross(z, n), z])


def axis_turn(axis, degrees):
    """A 3x3 COLUMN rotation of `degrees` about the joint's X (0), Y (1) or Z (2)."""
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    i, j = [(1, 2), (2, 0), (0, 1)][axis]
    m = np.identity(3)
    m[i, i], m[i, j], m[j, i], m[j, j] = c, -s, s, c
    return m


def anatomical_range(kind, key):
    """((min xyz), (max xyz)) degrees of a ball joint about its neutral (`ANATOMY`), mirrored for a
    right limb: the abduction axis turns a limb toward the body's LEFT when positive."""
    _n, _f, twist, (add, abd), (ext, flex) = ANATOMY[kind]
    y_lo, y_hi = (-abd, add) if side_of(key) < 0 else (-add, abd)
    return np.array([-twist, y_lo, -ext]), np.array([twist, y_hi, flex])


def anatomical_limits(kind, key, offset):
    """((min xyz), (max xyz)) degrees for Bullet. `offset` is the 3x3 COLUMN turn the joint stands at
    from neutral now: Bullet's zero is the pose now and its frame the child's, so a turn `m` of
    Bullet's is the anatomical `offset . m` - Bullet's X the limb's own twist. Along each of Bullet's
    axes the limit is how far a turn about that axis alone keeps the joint inside its swing-twist
    cone (`cone_excess`; a pose already past it is never snapped back, only kept from going further),
    at least LIMIT_GRACE each way, the middle axis inside +-MIDDLE_LIMIT; then the box's corners are
    brought inside the cone (`_inside_cone`)."""
    cap = (179.0, MIDDLE_LIMIT, 179.0)

    def inside(axis, degrees):
        swing, twist = cone_excess(kind, key, offset @ axis_turn(axis, degrees), offset)
        return swing <= 1e-6 and twist <= 1e-6

    lo, hi = [], []
    for axis in range(3):
        ends = []
        for sign in (-1, 1):
            reach = 0.0
            while reach < cap[axis] and inside(axis, sign * (reach + 1.0)):
                reach += 1.0
            ends.append(max(reach, LIMIT_GRACE) * sign)
        lo.append(float(ends[0]))
        hi.append(float(ends[1]))
    lo, hi = _inside_cone(kind, key, offset, lo, hi)
    return tuple(lo), tuple(hi)


def _inside_cone(kind, key, offset, lo, hi):
    """Bullet limits each axis on its own, so its box of swings reaches past the joint's cone at the
    box's corners (a wrist bent fully forward AND fully sideways). Only the swing is held to the cone
    here: Bullet's two swings carry a twist of their own (up to ~15 degrees at a big shoulder's
    corner), and shrinking for it would leave a hip 60 of its 120 degrees of flexion. The two half-sides that make a
    corner past the cone (by more than CONE_SLACK) are shrunk, 5 % a pass - the sideways (Y) one
    first, then the flexion (Z) one - until every corner keeps inside it - each half-side at least CONE_SHRINK_MIN of its reach and LIMIT_GRACE."""
    ends = {(1, 0): lo[1], (1, 1): hi[1], (2, 0): lo[2], (2, 1): hi[2]}
    k = dict((e, 1.0) for e in ends)
    for _pass in range(2 * int((1.0 - CONE_SHRINK_MIN) / 0.05) + 1):
        failing = []
        for iy in (0, 1):
            for iz in (0, 1):
                y, z = ends[(1, iy)] * k[(1, iy)], ends[(2, iz)] * k[(2, iz)]
                turn = offset @ axis_turn(2, z) @ axis_turn(1, y)
                if cone_excess(kind, key, turn, offset)[0] > CONE_SLACK:
                    failing.append(((1, iy), (2, iz)))
        if not failing:
            break
        for side_y, side_z in failing:          # the sideways swing gives way first: a fall
            if k[side_y] > CONE_SHRINK_MIN + 1e-9:  # flings the limbs forward and back
                k[side_y] = max(CONE_SHRINK_MIN, k[side_y] - 0.05)
            else:
                k[side_z] = max(CONE_SHRINK_MIN, k[side_z] - 0.05)
    lo, hi = list(lo), list(hi)
    for axis in (1, 2):
        lo[axis] = min(ends[(axis, 0)] * k[(axis, 0)], -LIMIT_GRACE)
        hi[axis] = max(ends[(axis, 1)] * k[(axis, 1)], LIMIT_GRACE)
    return lo, hi


def anatomical_joint(kind, key, anchor, rest, now, facing_rest):
    """(4x4 world frame, (min), (max), offset angles) of a ball joint read from the anatomy: `rest`
    and `now` are (parent 4x4, child 4x4, parent axis direction, child axis direction) of its two
    bodies at the bind and at the fall's first frame (`now` the first two only). The parent's
    neutral frame rides the parent; the child's own neutral frame is that frame turned the least onto
    its rest direction, riding the child; their difference now is how far the joint stands from
    neutral. The joint's frame is the CHILD's: Bullet's X is then the limb's own axis, a twist in
    Bullet a twist of the limb (in the parent's frame a Bullet twist turned a hand already bent 20
    degrees into a swing 30 past its range)."""
    p_rest, c_rest, p_dir_rest, c_dir_rest = rest
    p_now, c_now = now[0], now[1]
    neutral = anatomical_frame(kind, key, facing_rest, p_dir_rest)
    child_neutral = neutral @ turn_between(neutral[0], c_dir_rest)
    jp = neutral @ rot(p_rest).T @ rot(p_now)
    jc = child_neutral @ rot(c_rest).T @ rot(c_now)
    offset = jp @ jc.T
    lo, hi = anatomical_limits(kind, key, offset)
    return frame(jc, anchor), lo, hi, euler_xyz(offset)


def swing_twist(m):
    """(swing about Y, swing about Z, twist about X), degrees, of a joint's 3x3 COLUMN turn `m` (the
    child's axes in the joint's frame): the swing is the least turn taking the joint's X onto the
    child's X, as a rotation vector - no gimbal, the measure PhysX's and Unreal's cones use - the
    twist what is left about the child's own axis."""
    d = _unit(m[:, 0])
    phi = math.degrees(math.acos(float(np.clip(d[0], -1.0, 1.0))))
    axis = np.array([0.0, -d[2], d[1]])
    n = np.linalg.norm(axis)
    if n < 1e-9:
        sy = sz = 0.0
        swing = np.identity(3)
    else:
        axis = axis / n
        sy, sz = phi * axis[1], phi * axis[2]
        swing = turn_between(np.array([1.0, 0, 0]), d).T              # column form
    rest = swing.T @ m
    twist = math.degrees(math.atan2(rest[2, 1], rest[1, 1]))
    return sy, sz, twist


def cone_excess(kind, key, m, start=None):
    """(swing, twist) degrees a ball joint's turn `m` stands past its human range, read as a
    swing-twist cone: the swing against the ellipse its abduction and flexion ranges make in that
    direction, the twist against its twist range - each less what `start` (the turn at the fall)
    already stood past it."""
    lo, hi = anatomical_range(kind, key)

    def past(turn):
        sy, sz, tw = swing_twist(turn)
        p = math.hypot(sy, sz)
        swing = 0.0
        if p > 1e-9:
            ay, az = sy / p, sz / p
            ly = hi[1] if ay > 0 else -lo[1]
            lz = hi[2] if az > 0 else -lo[2]
            swing = p - 1.0 / math.sqrt((ay / ly) ** 2 + (az / lz) ** 2)
        return max(0.0, swing), max(0.0, tw - hi[0], lo[0] - tw)

    swing, twist = past(m)
    if start is not None:
        swing0, twist0 = past(start)
        swing, twist = max(0.0, swing - swing0), max(0.0, twist - twist0)
    return swing, twist


# ------------------------------------------------------------------ self-collision

def collision_group(key):
    """The collision group a body is in (`COLLISION_GROUPS`)."""
    if key.startswith(("lowerarm", "hand")):
        return "forearm_" + key[-1]
    if key.startswith(("calf", "foot")):
        return "shin_" + key[-1]
    return key


def group_bit(group):
    return 1 << (COLLISION_GROUPS.index(group) + 1)


def segment_distance(p1, q1, p2, q2):
    """The least distance between segments p1-q1 and p2-q2 (Ericson's closest points)."""
    p1, q1, p2, q2 = (np.asarray(v, dtype=float) for v in (p1, q1, p2, q2))
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = float(d1 @ d1), float(d2 @ d2), float(d2 @ r)
    if a <= 1e-12 and e <= 1e-12:
        return float(np.linalg.norm(r))
    if a <= 1e-12:
        s, t = 0.0, float(np.clip(f / e, 0.0, 1.0))
    else:
        c = float(d1 @ r)
        if e <= 1e-12:
            t, s = 0.0, float(np.clip(-c / a, 0.0, 1.0))
        else:
            b = float(d1 @ d2)
            denom = a * e - b * b
            s = float(np.clip((b * f - c * e) / denom, 0.0, 1.0)) if denom > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t, s = 0.0, float(np.clip(-c / a, 0.0, 1.0))
            elif t > 1.0:
                t, s = 1.0, float(np.clip((b - c) / a, 0.0, 1.0))
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))


def penetration(axis_a, ra, axis_b, rb):
    """How deep two capsules overlap (cm, 0 apart) - each its axis segment (start, end) and radius.
    The capsule's tips reach half a radius past each end (`capsule_length`), so the centres of its
    caps stand half a radius INSIDE them."""
    def grown(axis, r):
        a, b = (np.asarray(v, dtype=float) for v in axis)
        span = float(np.linalg.norm(b - a))
        if span <= r:
            mid = (a + b) * 0.5
            return mid, mid
        d = (b - a) / span
        return a + d * r * 0.5, b - d * r * 0.5
    pa, qa = grown(axis_a, ra)
    pb, qb = grown(axis_b, rb)
    return max(0.0, ra + rb - segment_distance(pa, qa, pb, qb))


def collision_filters(axes, radii, keys=None, poses=()):
    """({body: (group bits, mask bits)}, [(group, group) pairs left apart and why]): every body
    collides with the world and with every other body's group but its own, its jointed neighbours'
    and those it already touches (deeper than OVERLAP_SHARE of the thinner radius). `axes` {body:
    (start, end)} and `radii` {body: cm} at the fall's first frame; `poses`, more {body: (start,
    end)} the bodies take (a Blend's take over its span) - a pair touching in any is left apart."""
    keys = [k for k in (keys or [r[0] for r in BODIES]) if k in axes]
    parent = dict((r[0], r[2]) for r in BODIES)
    apart = {}
    for k in keys:
        p = parent.get(k)
        if p in keys:
            pair = tuple(sorted((collision_group(k), collision_group(p))))
            if pair[0] != pair[1]:
                apart.setdefault(pair, "jointed")
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ga, gb = collision_group(a), collision_group(b)
            if ga == gb:
                continue
            pair = tuple(sorted((ga, gb)))
            if pair in apart:
                continue
            depth = max(penetration(pose[a], radii[a], pose[b], radii[b])
                        for pose in [axes] + list(poses))
            if depth > OVERLAP_SHARE * min(radii[a], radii[b]) + 1e-9:
                apart[pair] = "overlap %s-%s %.1f cm" % (a, b, depth)
    out = {}
    for k in keys:
        g = collision_group(k)
        mask = WORLD_BIT
        for other in COLLISION_GROUPS:
            if other != g and tuple(sorted((g, other))) not in apart:
                mask |= group_bit(other)
        out[k] = (group_bit(g), mask)
    return out, sorted(apart.items())


def world_mask():
    """The floor's and the colliders' mask: every body group, the weapon and the world."""
    mask = WORLD_BIT | WEAPON_BIT
    for g in COLLISION_GROUPS:
        mask |= group_bit(g)
    return mask


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


# ---------------------------------------------------------------- blend (2026-10-17)

#  Blend: the take and the ragdoll mixed. Six zones, each Anim (on the take at full strength,
#  baked as the take), Follow (pulled toward the take at its own strength) or Free (pulled only
#  during the blends)
ZONES = ("torso", "head", "arm_l", "arm_r", "leg_l", "leg_r")
ZONE_LABEL = {"torso": "Torso", "head": "Head", "arm_l": "Arm L", "arm_r": "Arm R",
              "leg_l": "Leg L", "leg_r": "Leg R"}
STATES = ("anim", "follow", "free")
STATE_LABEL = {"anim": "Anim", "follow": "Follow", "free": "Free"}
#  {name: {zone: (state, strength)}}
PRESETS = OrderedDict((
    ("hit", ("Hit reaction", dict(
        [("leg_l", ("anim", 1.0)), ("leg_r", ("anim", 1.0))]
        + [(z, ("follow", 0.5)) for z in ("torso", "head", "arm_l", "arm_r")]))),
    ("overlap", ("Arm overlap", dict(
        [("arm_l", ("follow", 0.3)), ("arm_r", ("follow", 0.3))]
        + [(z, ("anim", 1.0)) for z in ("torso", "head", "leg_l", "leg_r")]))),
    ("follow", ("All follow", dict((z, ("follow", 0.6)) for z in ZONES))),
))
DEFAULT_PRESET = "hit"
def zone_of(key):
    """The zone a body belongs to."""
    if key in ("pelvis", "spine_lo", "spine_hi"):
        return "torso"
    if key == "head":
        return "head"
    side = key.rsplit("_", 1)[-1]
    if key.startswith(("upperarm", "lowerarm", "hand")):
        return "arm_" + side
    return "leg_" + side


def zones(given=None):
    """{zone: [state, strength]} - the default preset's, overlaid by `given` (anything broken is
    left at the default)."""
    out = OrderedDict((z, list(PRESETS[DEFAULT_PRESET][1][z])) for z in ZONES)
    for zone, value in (given or {}).items():
        if zone not in out:
            continue
        try:
            state, strength = value[0], float(value[1])
        except (TypeError, ValueError, IndexError):
            continue
        if state in STATES:
            out[zone] = [state, max(0.0, min(strength, 1.0))]
    return out


def body_states(zones_given, keys):
    """({body: state}, {body: strength}) from the zones - but the pelvis plays the take whenever a
    leg does: planted legs hold the hips, or the hips would tear off them."""
    z = zones(zones_given)
    state = dict((k, z[zone_of(k)][0]) for k in keys)
    strength = dict((k, float(z[zone_of(k)][1])) for k in keys)
    if "pelvis" in state and "anim" in (z["leg_l"][0], z["leg_r"][0]):
        state["pelvis"], strength["pelvis"] = "anim", 1.0
    return state, strength


def preset(name):
    """{zone: [state, strength]} of a preset."""
    return OrderedDict((z, list(PRESETS[name][1][z])) for z in ZONES)


def smoothstep(u):
    u = max(0.0, min(1.0, float(u)))
    return u * u * (3.0 - 2.0 * u)


def blend_strength(t, a, b, blend_in, blend_out, strength):
    """A follow spring's strength at frame `t` of the span `a`..`b`: 1 (the take) at `a`, easing to
    the zone's `strength` over `blend_in` frames, held, easing back to 1 over the last `blend_out`."""
    s = float(strength)
    out = s
    if blend_in > 0 and t < a + blend_in:
        out = 1.0 + (s - 1.0) * smoothstep((t - a) / float(blend_in))
    if blend_out > 0 and t > b - blend_out:
        back = smoothstep((t - (b - blend_out)) / float(blend_out))
        out = out + (1.0 - out) * back
    return out


def layer_weight_keys(a, b, blend_out):
    """[(time, weight)] of the Blend layer: 0 before the span, 1 from `a`, easing to 0 over the
    last `blend_out` frames (0 at `b`)."""
    keys = [(a - 1, 0.0), (a, 1.0)]
    out = max(0, int(round(blend_out)))
    if out <= 0:
        return keys + [(b, 1.0), (b + 1, 0.0)]
    start = max(a, b - out)
    for t in range(start, b + 1):
        keys.append((t, 1.0 - smoothstep((t - start) / float(max(1, b - start)))))
    return keys


def capsule_inertia(mass, length, radius):
    """(about its axis, across, across) of a capsule body `length` cm tip to tip along its X: Bullet's
    own - a box of length x 2r x 2r (measured: 416.7 for 5 kg, 30 x 5, against 406 for a solid
    cylinder)."""
    m = float(mass)
    w = 2.0 * float(radius)
    along = m / 12.0 * (w * w + w * w)
    across = m / 12.0 * (float(length) ** 2 + w * w)
    return along, across, across


def servo(before, now, target, fps, strength, mass, inertia, gravity=G):
    """(J kg*cm/s, torque kg*cm^2*rad/s), both world: the kick that turns a body standing at `now`
    (4x4; at `before` a frame earlier) toward where it must be a frame later (`target`), taking
    `strength` of the way (1: there, if nothing stands in its way; 0: nothing). `inertia` its
    (along, across, across) about its own X, Y, Z. Gravity's pull over the frame is paid for."""
    s = max(0.0, min(1.0, float(strength)))
    if s <= 0.0:
        return np.zeros(3), np.zeros(3)
    dt = 1.0 / float(fps)
    v_now, w_now = velocities(before, now, fps)
    v_now = v_now - np.array([0.0, gravity * dt * 0.5, 0.0])    # the frame's end, not its middle
    v_want, w_want = velocities(now, target, fps)
    v_want = v_want + np.array([0.0, gravity * dt * 0.5, 0.0])
    j = float(mass) * s * (v_want - v_now)
    dw = np.radians(s * (w_want - w_now))
    r = rot(now)
    torque = r.T @ (np.asarray(inertia, dtype=float) * (r @ dw))
    return j, torque


# A Follow zone is a spring with weight: its strength sets how fast the body comes back to the
# take (a frequency between these, log-spaced), how much of gravity's pull the muscles carry, and
# the spring rings a little (FOLLOW_DAMPING under 1). Measured 2026-10-17: a share-of-the-way kick
# each frame (servo below 1) lagged a fast take and snapped back - a twitch, no weight.
FOLLOW_SOFT_HZ = 0.5
FOLLOW_FIRM_HZ = 6.0
FOLLOW_DAMPING = 0.4


def follow_spring(strength):
    """(omega rad/s, damping ratio, the share of gravity carried: strength^2) of a Follow at `strength`."""
    s = max(0.0, min(1.0, float(strength)))
    hz = FOLLOW_SOFT_HZ * (FOLLOW_FIRM_HZ / FOLLOW_SOFT_HZ) ** s
    return 2.0 * math.pi * hz, FOLLOW_DAMPING, s * s


def spring_step(e0, v0, omega, zeta, dt):
    """A damped spring's error a time `dt` on, from error `e0` and its rate `v0` (any shape)."""
    e0 = np.asarray(e0, dtype=float)
    v0 = np.asarray(v0, dtype=float)
    decay = math.exp(-zeta * omega * dt)
    if zeta < 1.0:
        wd = omega * math.sqrt(1.0 - zeta * zeta)
        return decay * (e0 * math.cos(wd * dt) + (v0 + zeta * omega * e0) / wd * math.sin(wd * dt))
    return decay * (e0 + (v0 + omega * e0) * dt)


def rotvec(m3):
    """The rotation vector (radians, world axis) of a world turn (3x3 rows, as world_turn gives)."""
    m = np.asarray(m3, dtype=float).T
    c = float(np.clip((np.trace(m) - 1.0) * 0.5, -1.0, 1.0))
    theta = math.acos(c)
    if theta < 1e-9:
        return np.zeros(3)
    if math.pi - theta < 1e-6:
        return np.zeros(3)
    axis = np.array([m[2, 1] - m[1, 2], m[0, 2] - m[2, 0], m[1, 0] - m[0, 1]]) / (2 * math.sin(theta))
    return axis * theta


def from_rotvec(v):
    """The world turn (3x3 rows) of a rotation vector (radians)."""
    v = np.asarray(v, dtype=float)
    theta = float(np.linalg.norm(v))
    if theta < 1e-12:
        return np.identity(3)
    axis = v / theta
    kx = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    col = np.identity(3) + math.sin(theta) * kx + (1.0 - math.cos(theta)) * (kx @ kx)
    return col.T


def follow(before, now, target_before, target_now, target_next, fps, strength, mass, inertia,
           gravity=G):
    """(J, torque) of a Follow body: the body standing at `now` (`before` a frame earlier) is off the
    take (`target_now`, `target_before` a frame earlier) by an error that a damped spring
    (`follow_spring`) carries on for a frame; the kick lands it at `target_next` plus that error.
    The muscles carry strength^2 of gravity, the rest of it sags the body. Strength 1 is `servo`."""
    s = max(0.0, min(1.0, float(strength)))
    if s >= 1.0:
        return servo(before, now, target_next, fps, 1.0, mass, inertia, gravity)
    if s <= 0.0:
        return np.zeros(3), np.zeros(3)
    omega, zeta, carried_share = follow_spring(s)
    dt = 1.0 / float(fps)
    v_now, w_now = velocities(before, now, fps)
    v_take, w_take = velocities(target_before, target_now, fps)
    e1 = spring_step(pos(now) - pos(target_now), v_now - v_take, omega, zeta, dt)
    v_want = (pos(target_next) + e1 - pos(now)) * fps
    lift = np.array([0.0, gravity * dt * 0.5, 0.0])
    j = float(mass) * ((v_want + carried_share * lift) - (v_now - lift))
    r1 = spring_step(rotvec(world_turn(target_now, now)), np.radians(w_now - w_take), omega, zeta, dt)
    want_rot = rot(target_next) @ from_rotvec(r1)
    _v, w_want = velocities(now, frame(want_rot, pos(now)), fps)
    dw = np.radians(w_want - w_now)
    r = rot(now)
    torque = r.T @ (np.asarray(inertia, dtype=float) * (r @ dw))
    return j, torque


def hit_torque(point, j):
    """The torque (world) of an impulse `j` struck `point` (world, from the body's centre) away."""
    return np.cross(np.asarray(point, dtype=float), np.asarray(j, dtype=float))


def swung(take_body, sim_body):
    """The take's body turned only as far as the ragdoll SWUNG its axis (its X): a capsule is round
    about its axis, so the roll the ragdoll gives it is no physics - the take's roll is kept (a UE
    upper arm rolls up to 80 degrees a frame in a sword attack, past what a body can follow)."""
    x_take, x_sim = rot(take_body)[0], rot(sim_body)[0]
    return frame(rot(take_body) @ turn_between(x_take, x_sim), pos(sim_body))


def carried_by(take_bone, take_body, sim_body):
    """A bone's world when its body moved from where the take put it to where the ragdoll did."""
    return take_bone @ np.linalg.inv(take_body) @ sim_body


def sole_heights(points, body_then, bodies):
    """The lowest of a foot's skinned `points` (n x 3 world, read with its body at `body_then`) on
    each of `bodies` (4x4): where its sole stands frame by frame. No points: nothing."""
    if points is None or not len(points):
        return []
    p = np.asarray(points, dtype=float)
    local = np.hstack([p, np.ones((len(p), 1))]) @ np.linalg.inv(body_then)
    return [float(np.min((local @ m)[:, 1])) for m in bodies]


# the linear room a Blend joint gets beyond what the take itself does (cm)
LINEAR_MARGIN = 0.3


def joint_travel(joint, child_anchor, parents_now, children_now, margin=LINEAR_MARGIN):
    """((min xyz), (max xyz)) cm: how far the take moves a joint's child anchor off the joint as its
    parent body carries it - `joint` and `child_anchor` read at the first frame (4x4, 3), then each
    frame's parent and child bodies. A rigid joint (a hip) gets the margin only; a shoulder carried
    by a shrugging clavicle the clavicle's reach - so the joint holds the chain together without
    fighting the take."""
    joint = np.asarray(joint, dtype=float)
    p0, c0 = parents_now[0], children_now[0]
    on_parent = joint @ np.linalg.inv(p0)
    local = np.append(np.asarray(child_anchor, dtype=float), 1.0) @ np.linalg.inv(c0)
    lo, hi = np.zeros(3), np.zeros(3)
    for p, c in zip(parents_now, children_now):
        a = on_parent @ p
        d = ((local @ c)[:3] - pos(a)) @ rot(a).T
        lo, hi = np.minimum(lo, d), np.maximum(hi, d)
    return tuple(float(v) for v in lo - margin), tuple(float(v) for v in hi + margin)


# a limb's bend plane decides its roll from this bend up (sine of the angle); below BEND_LOOSE the
# roll is carried on from the frame before
BEND_LOOSE, BEND_FIRM = math.sin(math.radians(3.0)), math.sin(math.radians(15.0))
#  each limb body: (upper body, lower body) whose axes make its bend plane
BEND_PAIRS = {}
for _s in ("l", "r"):
    for _up, _lo in (("upperarm_", "lowerarm_"), ("thigh_", "calf_")):
        BEND_PAIRS[_up + _s] = BEND_PAIRS[_lo + _s] = (_up + _s, _lo + _s)


def blend_bodies(worlds_seq, keys):
    """[{body: 4x4}] for each pose of `worlds_seq`: `body_frame`, but an upper or lower limb rolls
    with its bend plane (Y along upper x lower) - the roll a hinge needs - rather than with its bone,
    which a UE clip spins up to 80 deg a frame; a limb near straight carries its roll on from the
    frame before."""
    out, prev = [], {}
    for worlds in worlds_seq:
        bodies = dict((k, body_frame(k, worlds)) for k in keys)
        for key in keys:
            pair = BEND_PAIRS.get(key)
            if pair is None:
                continue
            x = rot(bodies[key])[0]
            n = np.cross(rot(bodies[pair[0]])[0], rot(bodies[pair[1]])[0])
            size = float(np.linalg.norm(n))
            w = smoothstep((size - BEND_LOOSE) / (BEND_FIRM - BEND_LOOSE))
            n = n / size if size > 1e-9 else rot(bodies[key])[1]
            if key in prev:
                carried = prev[key][1] @ turn_between(prev[key][0], x)
                if np.dot(n, carried) < 0:          # the plane's side carries on: an elbow
                    n = -n                          # straightening past 0 is not a half roll
                hint = w * n + (1.0 - w) * carried
            else:
                hint = n if w > 0 else rot(bodies[key])[1]
            y = perpendicular(x, hint)
            bodies[key] = frame(np.array([x, y, np.cross(x, y)]), pos(bodies[key]))
            prev[key] = (x, y)
        out.append(bodies)
    return out


# the angular room a Blend joint gets beyond what the take itself does (degrees); Bullet's middle axis
# stays inside MIDDLE_MAX
ANGULAR_MARGIN, MIDDLE_MAX = 3.0, 85.0


def joint_angles(joint, parents_now, children_now):
    """[(x, y, z)] Bullet's angles of a joint at each pose (`euler_xyz` of the child's axes in the
    joint's frame as the parent carries it), zero at the first."""
    joint = np.asarray(joint, dtype=float)
    on_parent = rot(joint) @ rot(parents_now[0]).T
    on_child = rot(joint) @ rot(children_now[0]).T
    out = []
    for p, c in zip(parents_now, children_now):
        ra, rb = on_parent @ rot(p), on_child @ rot(c)
        out.append(euler_xyz(ra @ rb.T))
    return out


def widened(lo, hi, angles, margin=ANGULAR_MARGIN):
    """(lo, hi) degrees grown to hold every one of `angles` (and the margin past it) - a Blend joint
    never fights the take it follows; the middle axis kept inside MIDDLE_MAX."""
    a = np.asarray(angles, dtype=float).reshape(-1, 3)
    lo = np.minimum(np.asarray(lo, dtype=float), a.min(axis=0) - margin)
    hi = np.maximum(np.asarray(hi, dtype=float), a.max(axis=0) + margin)
    lo[1], hi[1] = max(lo[1], -MIDDLE_MAX), min(hi[1], MIDDLE_MAX)
    return tuple(float(v) for v in lo), tuple(float(v) for v in hi)


def world_turn(before, now):
    """The world turn W (3x3 rows) taking `before`'s rotation onto `now`'s: rot(now) = rot(before) W."""
    return rot(before).T @ rot(now)


def turn_power(w, k):
    """The world turn `w` (3x3) taken `k` times (k fractional, negative: back) about its own axis."""
    m = np.asarray(w, dtype=float).T                   # column form
    c = float(np.clip((np.trace(m) - 1.0) * 0.5, -1.0, 1.0))
    theta = math.acos(c)
    if theta < 1e-9 or math.pi - theta < 1e-6:
        return np.identity(3)
    axis = np.array([m[2, 1] - m[1, 2], m[0, 2] - m[2, 0], m[1, 0] - m[0, 1]]) / (2 * math.sin(theta))
    a = theta * float(k)
    kx = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    col = np.identity(3) + math.sin(a) * kx + (1.0 - math.cos(a)) * (kx @ kx)
    return col.T


def aimed(target, drift, k):
    """`target` (4x4) turned back by `k` of `drift` (a world turn the last frame's step landed off
    its aim): Bullet's spinning bodies precess, the same way on the next frame."""
    return frame(rot(target) @ turn_power(drift, -k), pos(target))
