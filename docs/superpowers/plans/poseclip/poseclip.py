"""poseclip - our poses onto a locomotion clip (a stop first): the model. numpy and the copied posemath
(maya.api.OpenMaya) - no maya.cmds.

The animator (2026-10-14): «Давай попробуем сделать инструмент который будет насаживать наши позы на
локомоушен циклы такие как вот стоп.» Walk Builder's pose machinery for a clip that is not a cycle: the pose
takes the place of the clip's REFERENCE (its still stretch - a stop's idle), the clip's motion about the
reference rides on top (the torso and head in world axes, the arms in locals), and the constraints are solved
again - each planted foot moved by one rigid motion of space (the stop's last contacts onto the pose's
stance), the legs by IK, the pelvis's height in proportion, sunk where a planted foot is out of reach, and
carried so the centre of mass keeps its place over the feet.

Row vectors (`world = local . parent`), centimetres, Y up.
Spec: docs/superpowers/specs/2026-10-14-pose-on-clip-design.md
"""
import math

import numpy as np

UP = np.array([0.0, 1.0, 0.0])
SIDES = ("l", "r")

STILL_SPEED = 1.5      # cm a frame: every body bone slower than this - the body stands still (the reference)
STILL_MIN = 8          # frames: the least still stretch that is a reference
FOOT_STILL = 2.0       # cm a frame: the ankle or the ball slower than this - the foot is planted
FOOT_NEAR = 4.0        # cm: the ankle or the ball this near its level in the reference - the foot is down
SETTLE = 10            # frames: two feet that stay down hand the weight over to half each in this long
GRIP_DIST = 30.0       # cm: a pose's hands this near each other hold one thing together
REACH = 0.995          # a planted leg never straighter than this share of its length (or the clip's own)
REACH_SIGMA = 3.0      # frames: the reach's sink blurred over this
CARRY_TOL = 0.005      # cm: the balance's carry stops this near the target
CARRY_STEPS = 8

PARTS = ("torso", "pelvis", "knees", "arms", "feet")

# de Leva's table as one weight a joint (Walk Builder's): the trunk at the thirds of pelvis..neck_01
TRUNK_MASS = (11.17, 16.33, 15.96)
HEAD_MASS = 6.94
LIMB_MASS = (("upperarm", "lowerarm", 2.71, 0.5772), ("lowerarm", "hand", 1.62, 0.4574),
             ("thigh", "calf", 14.16, 0.4095), ("calf", "foot", 4.33, 0.4459), ("foot", "ball", 1.37, 0.4415))
HAND_MASS = (0.61, 0.5)

HELPER_PREFIXES = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass", "attach", "poi", "props_")
ARM_STEMS = ("clavicle", "upperarm", "lowerarm", "hand")


class Refusal(Exception):
    """A clip or a pose this tool does not read; the message says why."""


# ---- rotations (Walk Builder's, maya_walk/model.py) ----

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


def toward(mean, target, alpha):
    """`mean` turned the share `alpha` of the way to `target`: exp(alpha . log(target . mean^-1)) . mean."""
    if alpha <= 0.0:
        return mean
    return exp_rot(alpha * log_rot(target @ mean.T)) @ mean


def power(r, k):
    """The rotation r to the power k: the same axis, k times the angle."""
    if k == 1.0:
        return r
    return exp_rot(k * log_rot(r))


def slerp(a, b, w):
    """From a (w 0) to b (w 1)."""
    if w <= 0.0:
        return a
    if w >= 1.0:
        return b
    return a @ exp_rot(w * log_rot(a.T @ b))


def blend_matrix(a, b, alpha):
    """Between two rigid 4x4s: the rotation `toward`, the translation lerped; 0 is `a`, 1 is `b`."""
    if alpha <= 0.0:
        return a
    out = np.eye(4)
    out[:3, :3] = toward(orthonormal(a[:3, :3]), orthonormal(b[:3, :3]), alpha)
    out[3, :3] = (1.0 - alpha) * np.asarray(a)[3, :3] + alpha * np.asarray(b)[3, :3]
    return out


def turned_about(v, axis, angle):
    """The vector `v` turned `angle` radians about the unit `axis` (right hand; Rodrigues)."""
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * float(np.dot(axis, v)) * (1.0 - c)


def matrix(rot, pos):
    out = np.eye(4)
    out[:3, :3] = rot
    out[3, :3] = pos
    return out


def yaw(angle):
    """The turn about up by `angle` radians."""
    return exp_rot([0.0, angle, 0.0])


def yaw_of(r):
    """A rotation's heading about up: where its forward (+Z) points on the floor (radians, 0 = +Z, + toward +X)."""
    fwd = np.asarray(r)[2]
    return math.atan2(float(fwd[0]), float(fwd[2]))


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


def _frame3(u, n):
    return np.stack([u, n, np.cross(u, n)])


def align(u_src, n_src, u_new, n_new):
    """The rotation taking the frame (u_src, n_src) onto (u_new, n_new): v . align = v'.
    Each n must be perpendicular to its u."""
    return _frame3(u_src, n_src).T @ _frame3(u_new, n_new)


# ---- the clip ----

class Clip(object):
    """A clip: every joint's world (J, F, 4, 4) on every frame, its names and parents (-1 for the top)."""

    def __init__(self, names, parents, worlds, fps=30.0, name="clip"):
        self.names = [str(n) for n in names]
        self.parents = [int(p) for p in parents]
        self.worlds = np.asarray(worlds, float)
        self.J, self.F = self.worlds.shape[:2]
        self.fps, self.name = float(fps), name
        self.index = dict((n, i) for i, n in enumerate(self.names))
        depth = [0] * self.J
        for j in range(self.J):
            k, d = j, 0
            while self.parents[k] >= 0:
                k = self.parents[k]
                d += 1
            depth[j] = d
        self.order = sorted(range(self.J), key=lambda j: (depth[j], j))


def _stem_side(name):
    for side in SIDES:
        if name.endswith("_" + side):
            return name[:-2], side
    return name, None


def kinds(clip):
    """Each joint's kind, by its UE leaf name: root, pelvis, torso, leg (thigh / calf / foot - by IK), toe
    (ball), legtwist, arm (clavicle to hand and their twists), finger (under a hand), helper (everything
    else: ik_, camera_, weapon_, interaction, ...)."""
    out = []
    for j, name in enumerate(clip.names):
        stem, side = _stem_side(name)
        if clip.parents[j] < 0:
            kind = "root"
        elif name == "pelvis":
            kind = "pelvis"
        elif name.startswith(HELPER_PREFIXES):
            kind = "helper"
        elif name.startswith(("spine_", "neck_")) or name == "head":
            kind = "torso"
        elif side and stem in ("thigh", "calf", "foot"):
            kind = "leg"
        elif side and stem == "ball":
            kind = "toe"
        elif side and stem.startswith(("thigh_twist", "calf_twist")):
            kind = "legtwist"
        elif side and (stem in ARM_STEMS or stem.startswith(("upperarm_twist", "lowerarm_twist"))):
            kind = "arm"
        else:
            kind = None
        out.append(kind)
    for j in clip.order:                       # under a hand and nothing above: a finger
        if out[j] is None:
            p = clip.parents[j]
            under_hand = p >= 0 and (clip.names[p].startswith("hand_") or out[p] == "finger")
            out[j] = "finger" if under_hand else "helper"
    return out


def runs(mask):
    """The runs of True in `mask`: inclusive (a, b)."""
    out, start = [], None
    for f, value in enumerate(np.asarray(mask, bool)):
        if value and start is None:
            start = f
        elif not value and start is not None:
            out.append((start, f - 1))
            start = None
    if start is not None:
        out.append((start, len(mask) - 1))
    return out


def contacts(still, merge=1, least=2):
    """A foot's contacts: the runs of `still`, two closer than `merge` frames apart merged, runs shorter than
    `least` frames dropped."""
    merged = []
    for a, b in runs(still):
        if merged and a - merged[-1][1] - 1 <= merge:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return [(a, b) for a, b in merged if b - a + 1 >= least]


def still_run(speeds, threshold=STILL_SPEED, least=STILL_MIN):
    """The longest run of frames slower than `threshold` (ties: the later), at least `least` long; else None."""
    best = None
    for a, b in runs(np.asarray(speeds) < threshold):
        if b - a + 1 >= least and (best is None or b - a >= best[1] - best[0]):
            best = (a, b)
    return best


def cover(need, sigma):
    """A smooth curve lying over `need` (one value a frame) with its ends held: `need` widened by its largest
    neighbour within `sigma` frames, blurred with a Gaussian of `sigma` frames (the ends padded with their own
    values), then scaled by the least factor that covers every frame's need. Walk Builder's smooth_cover for a
    clip that is not a cycle."""
    need = np.asarray(need, float)
    n = len(need)
    if n == 0 or need.max() <= 0.0:
        return np.zeros(n)
    reach = int(round(sigma))
    padded = np.concatenate([np.full(reach, need[0]), need, np.full(reach, need[-1])])
    wide = np.max([padded[s:s + n] for s in range(2 * reach + 1)], axis=0)
    half = max(int(math.ceil(3.0 * sigma)), 1)
    kernel = np.exp(-0.5 * (np.arange(-half, half + 1) / max(sigma, 1e-6)) ** 2)
    kernel /= kernel.sum()
    blur = np.convolve(np.concatenate([np.full(half, wide[0]), wide, np.full(half, wide[-1])]), kernel, "valid")
    wanted = need > 1e-9
    return np.maximum(blur * float((need[wanted] / np.maximum(blur[wanted], 1e-12)).max()), 0.0)


def foot_weights(down_l, down_r, settle=SETTLE):
    """(F, 2) the share of the weight on the left and the right foot: a foot alone takes it all; while both are
    down the weight goes over linearly from the foot that was alone before to the one that stays alone after,
    and - with nobody lifting after (an idle) - to half each in `settle` frames (mirrored before a lift with
    nobody alone before); with no foot down a row of NaN (the support is interpolated across it)."""
    down = np.stack([np.asarray(down_l, bool), np.asarray(down_r, bool)], axis=1)
    F = len(down)
    w = np.full((F, 2), np.nan)
    alone = {}
    for f in range(F):
        if down[f].sum() == 1:
            w[f] = down[f].astype(float)
            alone[f] = w[f].copy()
    half = np.array([0.5, 0.5])
    for a, b in runs(down.all(axis=1)):
        before, after = alone.get(a - 1), alone.get(b + 1)
        for f in range(a, b + 1):
            if before is not None and after is not None:
                u = (f - (a - 1)) / float(b + 1 - (a - 1))
                w[f] = (1.0 - u) * before + u * after
            elif before is not None:
                u = min(1.0, (f - (a - 1)) / float(settle))
                w[f] = (1.0 - u) * before + u * half
            elif after is not None:
                u = min(1.0, ((b + 1) - f) / float(settle))
                w[f] = (1.0 - u) * after + u * half
            else:
                w[f] = half
    return w


def support_path(weights, pivots):
    """(F, 3) the centre of the load on the floor: each foot's pivot by its weight, interpolated linearly
    across the frames no foot is down (held before the first and after the last), y 0."""
    F = len(weights)
    out = np.full((F, 3), np.nan)
    for f in range(F):
        if not np.isnan(weights[f, 0]):
            out[f] = weights[f, 0] * pivots["l"][f] + weights[f, 1] * pivots["r"][f]
    known = np.nonzero(~np.isnan(out[:, 0]))[0]
    if len(known) == 0:
        return np.zeros((F, 3))
    for axis in range(3):
        out[:, axis] = np.interp(np.arange(F), known, out[known, axis])
    out[:, 1] = 0.0
    return out


def _masses(clip, kind, pos):
    """De Leva's table as one weight a joint (Walk Builder's `_masses`), summing to 1; the trunk spread along
    pelvis..neck_01 at its thirds, read where the joints stand in `pos` (J, 3)."""
    idx, mass = clip.index, np.zeros(clip.J)
    if "neck_01" not in idx or "pelvis" not in idx:
        raise Refusal("the clip's skeleton has no pelvis..neck_01 chain to weigh the trunk by")
    chain = [idx["neck_01"]]
    while chain[-1] != idx["pelvis"]:
        if clip.parents[chain[-1]] < 0:
            raise Refusal("neck_01 is not under the pelvis")
        chain.append(clip.parents[chain[-1]])
    chain.reverse()
    lengths = np.linalg.norm(np.diff(pos[chain], axis=0), axis=1)
    ends = np.concatenate([[0.0], np.cumsum(lengths)])
    for share, part in zip(TRUNK_MASS, (1.0 / 6.0, 0.5, 5.0 / 6.0)):
        at = part * ends[-1]
        i = min(int(np.searchsorted(ends, at, side="right")) - 1, len(lengths) - 1)
        t = (at - ends[i]) / lengths[i] if lengths[i] > 1e-9 else 0.0
        mass[chain[i]] += share * (1.0 - t)
        mass[chain[i + 1]] += share * t
    mass[idx.get("head", chain[-1])] += HEAD_MASS
    for side in SIDES:
        for a, b, share, t in LIMB_MASS:
            if a + "_" + side in idx and b + "_" + side in idx:
                mass[idx[a + "_" + side]] += share * (1.0 - t)
                mass[idx[b + "_" + side]] += share * t
        hand = idx.get("hand_" + side)
        if hand is not None:
            share, t = HAND_MASS
            if "middle_01_" + side in idx:
                fingers = [idx["middle_01_" + side]]
            else:
                fingers = [j for j, p in enumerate(clip.parents) if p == hand and kind[j] == "finger"]
            mass[hand] += share * (1.0 - t if fingers else 1.0)
            for j in fingers:
                mass[j] += share * t / len(fingers)
    return mass / mass.sum()


def _batch_orthonormal(m):
    u, _, vt = np.linalg.svd(m)
    r = u @ vt
    bad = np.linalg.det(r) < 0.0
    if np.any(bad):
        u = u.copy()
        u[bad, :, -1] *= -1.0
        r = u @ vt
    return r


def _speeds(path):
    """(F,) how far a point moves into each frame (the first frame: into the second)."""
    step = np.linalg.norm(np.diff(path, axis=0), axis=1)
    return np.concatenate([step[:1], step])


class Analysis(object):
    """A clip read once: its heading, each bone's relative world rotation, local rotation and offset in its
    parent's rigid frame on every frame, the reference (its still stretch) and what stands there, the feet's
    contacts, the masses, the centre of mass and the support under it."""

    def __init__(self, clip, reference=None):
        self.clip = clip
        J, F = clip.J, clip.F
        self.kind = kinds(clip)
        idx = clip.index
        for need in ("pelvis",) + tuple("%s_%s" % (b, s) for s in SIDES for b in ("thigh", "calf", "foot", "ball")):
            if need not in idx:
                raise Refusal("the clip's skeleton has no %s" % need)
        self.pos = clip.worlds[:, :, 3, :3].copy()
        self.rot = _batch_orthonormal(clip.worlds[:, :, :3, :3])
        root = clip.order[0]
        self.root = root
        # the reference first (its heading is the zero of every heading below)
        body = [j for j, k in enumerate(self.kind) if k not in ("helper", "finger")]
        step = np.linalg.norm(np.diff(self.pos[body], axis=1), axis=2)            # (B, F-1)
        self.speeds = np.concatenate([step[:, :1], step], axis=1).max(axis=0)     # (F,)
        if reference is None:
            reference = still_run(self.speeds) or (0, F - 1)
        self.reference = (int(reference[0]), int(reference[1]))
        a, b = self.reference
        self.mid = (a + b) // 2
        turn = self.rot[root, self.mid].T @ self.rot[root]                         # (F, 3, 3)
        self.heading = np.array([yaw(yaw_of(t)) for t in turn])
        self.rel = self.rot @ np.swapaxes(self.heading, -1, -2)[None]
        self.local = np.empty_like(self.rot)
        self.offset = np.empty_like(self.pos)
        for j in range(J):
            p = clip.parents[j]
            if p < 0:
                self.local[j], self.offset[j] = self.rot[j], self.pos[j]
            else:
                self.local[j] = self.rot[j] @ np.swapaxes(self.rot[p], -1, -2)
                self.offset[j] = np.einsum("fi,fji->fj", self.pos[j] - self.pos[p], self.rot[p])
        self.rel_ref = np.array([mean_rot(self.rel[j, a:b + 1]) for j in range(J)])
        self.local_ref = np.array([mean_rot(self.local[j, a:b + 1]) for j in range(J)])
        self.feet = {}
        for side in SIDES:
            ankle, ball = self.pos[idx["foot_" + side]], self.pos[idx["ball_" + side]]
            lvl_ankle, lvl_ball = float(ankle[a:b + 1, 1].mean()), float(ball[a:b + 1, 1].mean())
            speed = np.minimum(_speeds(ankle), _speeds(ball))
            down = (ankle[:, 1] - lvl_ankle < FOOT_NEAR) | (ball[:, 1] - lvl_ball < FOOT_NEAR)
            still = (speed < FOOT_STILL) & down
            th, ca, fo = (idx["%s_%s" % (n, side)] for n in ("thigh", "calf", "foot"))
            self.feet[side] = {
                "ankle": ankle, "ball": ball, "level": (lvl_ankle, lvl_ball), "down": down, "still": still,
                "contacts": contacts(still), "pivot": 0.5 * (ankle + ball),
                "lengths": np.stack([np.linalg.norm(self.offset[ca], axis=1),
                                     np.linalg.norm(self.offset[fo], axis=1)], axis=1),
                "joints": (th, ca, fo),
            }
        self.floor = min(self.feet[s]["level"][1] for s in SIDES)
        self.pelvis = idx["pelvis"]
        self.h_ref = float(self.pos[self.pelvis, a:b + 1, 1].mean()) - self.floor
        self.masses = _masses(clip, self.kind, self.pos[:, self.mid])
        self.com = np.tensordot(self.masses, self.pos, axes=(0, 0))                # (F, 3)
        self.weights = foot_weights(self.feet["l"]["down"], self.feet["r"]["down"])
        self.support = support_path(self.weights, dict((s, self.feet[s]["pivot"]) for s in SIDES))
        off = self.com - self.support
        off[:, 1] = 0.0
        self.ref_offset = off[a:b + 1].mean(axis=0) @ self.heading[self.mid].T    # in the reference's heading
        # each helper follows the body bone whose relation to it holds best over the clip
        self.follows = {}
        bodies = [j for j, k in enumerate(self.kind) if k != "helper"]
        for h, kind in enumerate(self.kind):
            if kind != "helper":
                continue
            best = None
            for j in bodies:
                rel = clip.worlds[h] @ np.linalg.inv(clip.worlds[j])
                err = float(np.abs(rel - rel[self.mid]).max())
                if best is None or err < best[0] - 1e-9:
                    best = (err, j)
            self.follows[h] = best[1]


# ---- the pose against the reference ----

def _np4(m):
    return np.array([float(v) for v in m]).reshape(4, 4) if len(m) == 16 else np.array(m, float).reshape(4, 4)


def _bend(hip, knee, ankle):
    e = _unit(ankle - hip)
    b = (knee - hip) - np.dot(knee - hip, e) * e
    return _unit(b) if np.linalg.norm(b) > 1e-6 else None


def _wrapped(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def _flat_heading(v):
    """A floor direction's heading about up in the reference frame (0 = +Z, + toward +X)."""
    return math.atan2(float(v[0]), float(v[2]))


def _leg_lengths(bones, leaves):
    th, ca, fo = (_np4(bones[leaf]["rest"])[3, :3] for leaf in leaves)
    return float(np.linalg.norm(ca - th)), float(np.linalg.norm(fo - ca))


def prepare(analysis, statics, pose_bones):
    """The pose read against the clip's reference (the spec's "The pose"): `statics` the clip's skeleton
    {leaf: {"parent", "canonical", "rest"}}, `pose_bones` the pose's {leaf: {"parent", "canonical", "rest",
    "world"}} (16 floats each). Carried by posemath.Transfer onto the clip's skeleton placed on the root at the
    reference's middle frame - the legs' ratio for the size, 1 for a twin."""
    import posemath as pm
    clip, a = analysis.clip, analysis
    target_rest = {}
    first = {}
    for leaf, bone in statics.items():
        if leaf not in clip.index:
            continue
        rest = dict(bone)
        rest["world"] = list(bone["rest"])
        target_rest[leaf] = rest
        now = dict(bone)
        now["world"] = [float(v) for v in clip.worlds[clip.index[leaf], a.mid].reshape(16)]
        first[leaf] = now
    pairs = pm.pairs(pose_bones, target_rest)
    members = set(s for t, s in pairs.items() if not pm.is_helper(t))
    legs = ("thigh", "calf", "foot")
    missing = [n for n in ("pelvis",) + tuple("%s_%s" % (b, s) for s in SIDES for b in legs) if n not in pairs]
    if missing:
        raise Refusal("the pose's skeleton has nothing for the clip's %s" % ", ".join(missing))
    ratios = []
    for side in SIDES:
        mine = tuple("%s_%s" % (b, side) for b in legs)
        theirs = tuple(pairs[leaf] for leaf in mine)
        ratios.append(sum(_leg_lengths(target_rest, mine)) / max(sum(_leg_lengths(pose_bones, theirs)), 1e-9))
    ratio = float(np.mean(ratios))
    scale = 1.0 if (pm.twin(pairs, pose_bones, target_rest) and abs(ratio - 1.0) <= 0.01) else ratio
    transfer = pm.Transfer(pose_bones, target_rest, pairs, members, scale=scale)
    out = transfer.frame(root_world=transfer.place(first))
    world = {}
    for leaf, m in out.items():
        if leaf in clip.index:
            world[clip.index[leaf]] = np.array(pm.flat(m)).reshape(4, 4)
    rot = dict((j, orthonormal(m[:3, :3])) for j, m in world.items())
    pos = dict((j, m[3, :3].copy()) for j, m in world.items())
    heading = a.heading[a.mid]                       # the identity: the reference's heading is the zero
    rel = dict((j, r @ heading.T) for j, r in rot.items())
    local = {}
    for j, r in rot.items():
        p = clip.parents[j]
        if p >= 0 and p in rot:
            local[j] = r @ rot[p].T
    idx = clip.index
    feet = dict((s, idx["foot_" + s]) for s in SIDES)
    balls = dict((s, idx["ball_" + s]) for s in SIDES)
    floor = min(float(pos[balls[s]][1]) for s in SIDES)
    height = float(pos[a.pelvis][1]) - floor
    # the stance about the reference's midpoint between its ankles
    ra, rb = a.reference
    mid_ref = 0.5 * (a.feet["l"]["ankle"][ra:rb + 1].mean(axis=0) + a.feet["r"]["ankle"][ra:rb + 1].mean(axis=0))
    mid_pose = 0.5 * (pos[feet["l"]] + pos[feet["r"]])
    targets = {}
    for s in SIDES:
        place = pos[feet[s]] - mid_pose + mid_ref
        place[1] = float(pos[feet[s]][1]) - floor + a.floor
        targets[s] = matrix(rot[feet[s]], place)
    ball_local = dict((s, rot[balls[s]] @ rot[feet[s]].T) for s in SIDES)
    # the knees' bend: the pose's heading against the reference's
    knee_turn = {}
    for s in SIDES:
        th, ca, fo = a.feet[s]["joints"]
        pose_bend = _bend(pos[th], pos[ca], pos[fo])
        bends = [b for b in (_bend(a.pos[th, f], a.pos[ca, f], a.pos[fo, f]) for f in range(ra, rb + 1))
                 if b is not None]
        if pose_bend is None or not bends:
            knee_turn[s] = 0.0
        else:
            knee_turn[s] = _wrapped(_flat_heading(pose_bend) - _flat_heading(np.mean(bends, axis=0)))
    side_axis = np.array([1.0, 0.0, 0.0])
    width = float(np.dot(pos[feet["l"]] - pos[feet["r"]], side_axis)) - float(np.dot(
        a.feet["l"]["ankle"][ra:rb + 1].mean(axis=0) - a.feet["r"]["ankle"][ra:rb + 1].mean(axis=0), side_axis))
    # the hands and the weapon bones, read off the pose's own bones (their translations at the clip's size)
    grip, grip_rel, holds = False, None, {}
    hands = [pairs.get("hand_" + s) for s in SIDES]
    if all(h in pose_bones for h in hands):
        wl, wr = (_np4(pose_bones[h]["world"]) for h in hands)
        if float(np.linalg.norm(wl[3, :3] - wr[3, :3])) * scale < GRIP_DIST * scale:
            grip = True
            grip_rel = wl @ np.linalg.inv(wr)
            grip_rel[:3, :3] = orthonormal(grip_rel[:3, :3])
            grip_rel[3, :3] *= scale
    for h, body in a.follows.items():
        name, body_name = clip.names[h], clip.names[body]
        if name.startswith("weapon_") and pairs.get(name) in pose_bones and pairs.get(body_name) in pose_bones:
            held = _np4(pose_bones[pairs[name]]["world"]) @ np.linalg.inv(_np4(pose_bones[pairs[body_name]]["world"]))
            held[:3, :3] = orthonormal(held[:3, :3])
            held[3, :3] *= scale
            holds[h] = held
    # the balance: the pose's centre of mass against the centre of its two feet
    com = sum(a.masses[j] * pos[j] for j in pos)
    support = 0.5 * sum(0.5 * (pos[feet[s]] + pos[balls[s]]) for s in SIDES)
    offset = com - support
    offset[1] = 0.0
    return {"rel": rel, "local": local, "height": height, "feet": targets, "ball": ball_local,
            "knee_turn": knee_turn, "grip": grip, "grip_rel": grip_rel, "holds": holds, "offset": offset,
            "width": width, "scale": scale, "world": world}


# ---- the synthesis ----

def _smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


class Result(object):
    def __init__(self, worlds, info):
        self.worlds, self.info = worlds, info


class _Motions(object):
    """Each foot's rigid motion of space a frame: (Q, c, d) - x' = (x - c) . Q + c + d - and how far it is on its
    way to the final stance (0..1)."""

    def __init__(self, analysis, pose, share, feet_on):
        a = analysis
        F = a.clip.F
        self.Q = dict((s, np.tile(np.eye(3), (F, 1, 1))) for s in SIDES)
        self.c = dict((s, np.zeros((F, 3))) for s in SIDES)
        self.d = dict((s, np.zeros((F, 3))) for s in SIDES)
        self.final = dict((s, np.zeros(F)) for s in SIDES)
        self.final_contact = dict((s, None) for s in SIDES)
        self.moved = dict((s, 0) for s in SIDES)
        if pose is None or share <= 0.0 or not feet_on:
            return
        ra, rb = a.reference
        for s in SIDES:
            foot = a.feet[s]
            cts = foot["contacts"]
            if not cts:
                continue
            fo = foot["joints"][2]
            sign = 1.0 if s == "l" else -1.0
            last = len(cts) - 1 if cts[-1][1] >= ra else None
            self.final_contact[s] = last
            motions = []
            for k, (c0, c1) in enumerate(cts):
                ankle = foot["ankle"][c0:c1 + 1].mean(axis=0)
                if k == last:
                    wc = mean_rot(a.rot[fo, c0:c1 + 1])
                    target = pose["feet"][s]
                    q = power(wc.T @ target[:3, :3], share)
                    d = share * (target[3, :3] - ankle)
                else:
                    side_axis = np.array([1.0, 0.0, 0.0]) @ a.heading[(c0 + c1) // 2]
                    q = np.eye(3)
                    d = share * 0.5 * pose["width"] * sign * side_axis
                motions.append((q, ankle, d))
                if np.linalg.norm(d) > 1e-6 or np.abs(q - np.eye(3)).max() > 1e-9:
                    self.moved[s] += 1
            for f in range(F):
                k = None
                for i, (c0, c1) in enumerate(cts):
                    if c0 <= f <= c1:
                        k = i
                        break
                if k is not None:
                    q, c, d = motions[k]
                    w_final = 1.0 if k == last else 0.0
                else:
                    before = [i for i, (c0, c1) in enumerate(cts) if c1 < f]
                    after = [i for i, (c0, c1) in enumerate(cts) if c0 > f]
                    if not before:
                        q, c, d = motions[after[0]]
                        w_final = 1.0 if after[0] == last else 0.0
                    elif not after:
                        q, c, d = motions[before[-1]]
                        w_final = 1.0 if before[-1] == last else 0.0
                    else:
                        i, k2 = before[-1], after[0]
                        w = _smooth((f - cts[i][1]) / float(cts[k2][0] - cts[i][1]))
                        q = slerp(motions[i][0], motions[k2][0], w)
                        c = (1.0 - w) * motions[i][1] + w * motions[k2][1]
                        d = (1.0 - w) * motions[i][2] + w * motions[k2][2]
                        w_final = (w if k2 == last else 0.0) + ((1.0 - w) if i == last else 0.0)
                self.Q[s][f], self.c[s][f], self.d[s][f], self.final[s][f] = q, c, d, w_final

    def apply(self, s, f, point):
        return (point - self.c[s][f]) @ self.Q[s][f] + self.c[s][f] + self.d[s][f]


class _Plan(object):
    """Everything a frame's synthesis takes that does not depend on the frame."""

    def __init__(self, analysis, pose, share, motion, parts):
        a = analysis
        clip = a.clip
        self.a, self.pose, self.share, self.motion = a, pose, share, motion
        parts = set(parts)
        on = pose is not None and share > 0.0
        self.parts = parts
        self.target_rel = a.rel_ref.copy()
        self.target_local = a.local_ref.copy()
        for j, kind in enumerate(a.kind):
            if not on:
                continue
            if (kind == "torso" and "torso" in parts) or (kind == "pelvis" and "pelvis" in parts):
                if j in pose["rel"]:
                    self.target_rel[j] = toward(a.rel_ref[j], pose["rel"][j], share)
            if kind in ("arm", "finger") and "arms" in parts and j in pose["local"]:
                self.target_local[j] = toward(a.local_ref[j], pose["local"][j], share)
        self.grip = on and "arms" in parts and pose.get("grip")
        self.arm_gain = motion * ((1.0 - share) if self.grip else 1.0)
        self.h_target = a.h_ref + (share * (pose["height"] - a.h_ref) if on and "pelvis" in parts else 0.0)
        self.knee_turn = dict((s, share * pose["knee_turn"][s] if on and "knees" in parts else 0.0) for s in SIDES)
        self.ball_target = dict((s, pose["ball"][s] if on and "feet" in parts else None) for s in SIDES)
        self.holds = pose["holds"] if on and "arms" in parts else {}
        self.motions = _Motions(a, pose, share, "feet" in parts)
        # the balance's target: the clip's centre of mass moved with the support, and by the pose's own
        F = clip.F
        new_pivots = dict((s, np.array([self.motions.apply(s, f, a.feet[s]["pivot"][f]) for f in range(F)]))
                          for s in SIDES)
        support_new = support_path(a.weights, new_pivots)
        shift = (pose["offset"] - a.ref_offset) * share if on else np.zeros(3)
        self.com_target = a.com + (support_new - a.support) + np.einsum("i,fij->fj", shift, a.heading)
        self.com_target[:, 1] = np.nan
        self.support_new = support_new
        self.ball_index = dict((s, clip.index["ball_" + s]) for s in SIDES)
        self.legs = set(j for s in SIDES for j in a.feet[s]["joints"])
        self.helpers = [j for j in clip.order if a.kind[j] == "helper"]
        self.hand = dict((s, clip.index.get("hand_" + s)) for s in SIDES)
        self.upperarm_l = clip.index.get("upperarm_l")
        self.lowerarm_l = clip.index.get("lowerarm_l")


def _frame(plan, f, carry, drop):
    """One frame's worlds (J, 4, 4) and how far each planted foot fell short {side: cm}."""
    a, clip = plan.a, plan.a.clip
    J = clip.J
    rots, poss = np.zeros((J, 3, 3)), np.zeros((J, 3))
    done = np.zeros(J, bool)
    H = a.heading[f]
    short = {}
    for j in clip.order:
        if done[j]:
            continue
        kind, p = a.kind[j], clip.parents[j]
        if kind == "helper":
            continue
        if kind == "root":
            rots[j], poss[j] = a.rot[j, f], a.pos[j, f]
        elif kind in ("pelvis", "torso"):
            g = plan.a.rel_ref[j].T @ a.rel[j, f]
            rots[j] = plan.target_rel[j] @ power(g, plan.motion) @ H
            if kind == "pelvis":
                h = a.pos[j, f, 1] - a.floor
                height = plan.h_target * (1.0 + plan.motion * (h / a.h_ref - 1.0))
                base = a.pos[j, f].copy()
                base[1] = a.floor + height - drop
                poss[j] = base + carry
            else:
                poss[j] = a.offset[j, f] @ rots[p] + poss[p]
        elif kind in ("arm", "finger"):
            d = a.local[j, f] @ a.local_ref[j].T
            gain = plan.arm_gain if kind == "arm" or plan.grip else plan.motion
            rots[j] = power(d, gain) @ plan.target_local[j] @ rots[p]
            poss[j] = a.offset[j, f] @ rots[p] + poss[p]
        elif kind == "leg":
            side = clip.names[j][-1]
            if j == a.feet[side]["joints"][0]:
                short[side] = _leg(plan, side, f, rots, poss)
                for k in a.feet[side]["joints"]:
                    done[k] = True
        elif kind == "toe":
            side = clip.names[j][-1]
            d = a.local[j, f] @ a.local_ref[j].T
            target = a.local_ref[j]
            if plan.ball_target[side] is not None:
                target = toward(a.local_ref[j], plan.ball_target[side], plan.share * plan.motions.final[side][f])
            rots[j] = d @ target @ rots[p]
            poss[j] = a.offset[j, f] @ rots[p] + poss[p]
        else:                                             # legtwist and anything else: the clip's local
            rots[j] = a.local[j, f] @ rots[p]
            poss[j] = a.offset[j, f] @ rots[p] + poss[p]
        done[j] = True
    if plan.grip and plan.upperarm_l is not None:
        _hold(plan, f, rots, poss)
    for h in plan.helpers:
        body = a.follows[h]
        rel = clip.worlds[h, f] @ np.linalg.inv(clip.worlds[body, f])
        if h in plan.holds:
            rel = blend_matrix(rel, plan.holds[h], plan.share)
        m = rel @ matrix(rots[body], poss[body])
        rots[h], poss[h] = orthonormal(m[:3, :3]), m[3, :3]
    out = np.tile(np.eye(4), (J, 1, 1))
    out[:, :3, :3], out[:, 3, :3] = rots, poss
    return out, short


def _leg(plan, side, f, rots, poss):
    """Thigh, calf and foot by IK from the new hip to the foot the contact's rigid motion puts there; each bone
    turned by the rotation taking its clip (direction, leg plane) onto the new one. Returns how far the foot
    fell short."""
    a = plan.a
    th, ca, fo = a.feet[side]["joints"]
    pelvis = a.clip.parents[th]
    l1, l2 = a.feet[side]["lengths"][f]
    h0, k0, a0 = a.pos[th, f], a.pos[ca, f], a.pos[fo, f]
    hip = a.offset[th, f] @ rots[pelvis] + poss[pelvis]
    ankle = plan.motions.apply(side, f, a0)
    foot_rot = a.rot[fo, f] @ plan.motions.Q[side][f]
    e0 = _unit(a0 - h0)
    bend0 = _bend(h0, k0, a0)
    if bend0 is None:
        fwd = np.array([0.0, 0.0, 1.0]) @ a.heading[f]
        bend0 = _unit(fwd - np.dot(fwd, e0) * e0)
    e1 = _unit(ankle - hip)
    bend = bend0 if not plan.knee_turn[side] else turned_about(bend0, -e1, plan.knee_turn[side])
    own = float(np.linalg.norm(a0 - h0)) / (l1 + l2)
    reach = min(max(REACH, own), 1.0)
    knee, reached, short = two_bone(hip, ankle, l1, l2, bend, reach)
    e2 = _unit(reached - hip)
    b2 = _unit((knee - hip) - np.dot(knee - hip, e2) * e2)
    n_src, n_new = _unit(np.cross(e0, bend0)), _unit(np.cross(e2, b2))
    rots[th] = a.rot[th, f] @ align(_unit(k0 - h0), n_src, _unit(knee - hip), n_new)
    rots[ca] = a.rot[ca, f] @ align(_unit(a0 - k0), n_src, _unit(reached - knee), n_new)
    rots[fo] = foot_rot
    poss[th], poss[ca], poss[fo] = hip, knee, reached
    return short


def _hold(plan, f, rots, poss):
    """Hands that hold one thing together: the left hand put back on its relation to the right one by
    two-bone IK of the left arm (the elbow on its own plane), then everything under the left upper arm again."""
    a, clip = plan.a, plan.a.clip
    up, low, hand = plan.upperarm_l, plan.lowerarm_l, plan.hand["l"]
    if low is None or hand is None or plan.hand["r"] is None:
        return
    goal = plan.pose["grip_rel"] @ matrix(rots[plan.hand["r"]], poss[plan.hand["r"]])
    goal = blend_matrix(matrix(rots[hand], poss[hand]), goal, plan.share)
    shoulder, elbow, wrist = poss[up], poss[low], poss[hand]
    l1, l2 = float(np.linalg.norm(a.offset[low, f])), float(np.linalg.norm(a.offset[hand, f]))
    bend = _bend(shoulder, elbow, wrist)
    if bend is None:
        bend = np.array([0.0, -1.0, 0.0])
    e0 = _unit(wrist - shoulder)
    knee, reached, _ = two_bone(shoulder, goal[3, :3], l1, l2, bend, 1.0)
    e2 = _unit(reached - shoulder)
    b2 = _unit((knee - shoulder) - np.dot(knee - shoulder, e2) * e2)
    n_src, n_new = _unit(np.cross(e0, bend)), _unit(np.cross(e2, b2))
    rots[up] = rots[up] @ align(_unit(elbow - shoulder), n_src, _unit(knee - shoulder), n_new)
    rots[low] = rots[low] @ align(_unit(wrist - elbow), n_src, _unit(reached - knee), n_new)
    rots[hand] = orthonormal(goal[:3, :3])
    poss[low], poss[hand] = knee, reached
    # everything else under the upper arm (its twists, the fingers) again on its new parents
    for j in clip.order:
        p = clip.parents[j]
        if j in (up, low, hand) or a.kind[j] == "helper" or not _under(clip, j, up):
            continue
        d = a.local[j, f] @ a.local_ref[j].T
        rots[j] = power(d, plan.arm_gain) @ plan.target_local[j] @ rots[p]
        poss[j] = a.offset[j, f] @ rots[p] + poss[p]


def _under(clip, j, top):
    p = clip.parents[j]
    while p >= 0:
        if p == top:
            return True
        p = clip.parents[p]
    return False


def _com(plan, worlds):
    return np.tensordot(plan.a.masses, worlds[:, 3, :3], axes=(0, 0))


def _balanced(plan, f, drop):
    """The frame with the pelvis carried horizontally until the centre of mass stands on its target (secant
    steps; the legs follow by IK). Returns (worlds, carry, short)."""
    target = plan.com_target[f]
    carry = np.zeros(3)
    worlds, short = _frame(plan, f, carry, drop)
    err = target - _com(plan, worlds)
    err[1] = 0.0
    gain = 0.85
    for _ in range(CARRY_STEPS):
        if np.linalg.norm(err) < CARRY_TOL:
            break
        step = err / gain
        carry = carry + step
        worlds, short = _frame(plan, f, carry, drop)
        new = target - _com(plan, worlds)
        new[1] = 0.0
        moved = err - new
        denominator = float(np.dot(step, step))
        if denominator > 1e-12:
            gain = min(max(float(np.dot(moved, step)) / denominator, 0.3), 1.2)
        err = new
    return worlds, carry, short


def _need(plan, f, worlds):
    """How far the pelvis must sink this frame for every foot that is down to be reached (cm)."""
    a = plan.a
    need = 0.0
    for s in SIDES:
        if not a.feet[s]["down"][f]:
            continue
        th, ca, fo = a.feet[s]["joints"]
        l1, l2 = a.feet[s]["lengths"][f]
        own = float(np.linalg.norm(a.pos[fo, f] - a.pos[th, f])) / (l1 + l2)
        limit = min(max(REACH, own), 1.0) * (l1 + l2)
        hip = worlds[th, 3, :3]
        ankle = plan.motions.apply(s, f, a.pos[fo, f])
        v = hip - ankle
        flat = float(np.hypot(v[0], v[2]))
        if float(np.linalg.norm(v)) <= limit:
            continue
        need = max(need, float(v[1]) - math.sqrt(max(limit * limit - flat * flat, 0.0)))
    return need


def evaluate(analysis, pose=None, share=1.0, motion=1.0, parts=PARTS):
    """The clip with the pose: Result(worlds (J, F, 4, 4), info). `pose` is `prepare`'s (None: the clip with
    its own motion scaled by `motion`)."""
    a = analysis
    plan = _Plan(a, pose, float(share), float(motion), parts)
    F = a.clip.F
    needs = np.zeros(F)
    for f in range(F):
        worlds, carry, short = _balanced(plan, f, 0.0)
        needs[f] = _need(plan, f, worlds)
    drop = cover(needs, REACH_SIGMA) if needs.max() > 1e-4 else np.zeros(F)
    out = np.zeros((a.clip.J, F, 4, 4))
    carries, shorts = np.zeros(F), np.zeros(F)
    for f in range(F):
        worlds, carry, short = _balanced(plan, f, float(drop[f]))
        out[:, f] = worlds
        carries[f] = float(np.linalg.norm(carry))
        shorts[f] = max([v for s, v in short.items() if a.feet[s]["down"][f]] or [0.0])
    info = {"carry": float(carries.max()), "drop": float(drop.max()), "short": float(shorts.max()),
            "moved": dict(plan.motions.moved), "final": dict(plan.motions.final_contact),
            "reference": a.reference, "share": share, "motion": motion, "parts": tuple(parts),
            "grip": bool(plan.grip), "scale": None if pose is None else pose["scale"]}
    return Result(out, info)
