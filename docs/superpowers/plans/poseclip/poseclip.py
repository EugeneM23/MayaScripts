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
