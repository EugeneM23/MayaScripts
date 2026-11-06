"""maya_idle.model - an idle clip read once and rebuilt from knobs (2026-11-06, a draft).

Every joint's local rotation is split into its MEAN over the clip and its motion about that mean, in the
bone's own axes (`R(t) = D(t) . M`, row vectors). The rebuild puts the motion back, scaled per body part
(`gain`), on a mean pulled toward a pose card's (`share`), resampled in time (`tempo`), smoothed and with
its seam closed. The pelvis's place over the root is split the same way. The legs are then solved by
two-bone IK onto the feet: each ankle where the clip puts it about its own mean, that mean pulled toward the
pose's, so a pose's stance comes in while the clip's own small weight shifts stay. A helper bone that rides
a body bone rigidly in the clip (ik_foot_l on foot_l) rides it again.

numpy only. The clip comes in as locals (J, N, 4, 4), row vectors, Maya's convention.
"""
import math

import numpy as np

PARTS = ("torso", "head", "arms", "fingers", "legs", "pelvis")
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
HELPER_WORDS = ("ik_", "weapon", "camera", "interaction", "center_of_mass", "attach", "socket")

DEFAULTS = {
    "share": 1.0,       # how far each mean is pulled toward the pose card's
    "motion": 1.0,      # every gain at once
    "torso": 1.0, "head": 1.0, "arms": 1.0, "fingers": 1.0, "pelvis": 1.0, "feet": 1.0,
    "tempo": 1.0,       # x the clip's speed
    "smooth": 0.0,      # frames of Gaussian over the motion
    "height": 0.0,      # cm added to the pelvis
    "seam": 0.0,        # frames at the end eased onto the first frame
    "hold_l": 1.0, "hold_r": 1.0,    # Weapon: the hand rides the chest at its mean offset (where the pose holds the arm)
    "overlap_l": 0.0, "overlap_r": 0.0,   # Weapon: ms the chest it rides is late
    "fps": 30.0,        # the output rate (ms into frames)
}
RANGES = {
    "share": (0.0, 1.0), "motion": (0.0, 3.0),
    "torso": (0.0, 3.0), "head": (0.0, 3.0), "arms": (0.0, 3.0), "fingers": (0.0, 3.0),
    "pelvis": (0.0, 3.0), "feet": (0.0, 3.0),
    "tempo": (0.25, 3.0), "smooth": (0.0, 10.0), "height": (-30.0, 30.0), "seam": (0.0, 60.0),
    "hold_l": (0.0, 1.0), "hold_r": (0.0, 1.0), "overlap_l": (-1000.0, 1000.0), "overlap_r": (-1000.0, 1000.0),
    "fps": (1.0, 240.0),
}
ALL_PARTS = ("torso", "head", "arms", "legs", "pelvis")      # what of the pose comes in (chips)
RIGID_CM = 0.05
RIGID_DEG = 0.2


class Refusal(Exception):
    pass


def knobs(given=None):
    out = dict(DEFAULTS)
    for k, v in (given or {}).items():
        if k in out:
            lo, hi = RANGES[k]
            out[k] = min(max(float(v), lo), hi)
    return out


def group_of(name):
    n = name.lower()
    if n == "root":
        return "root"
    if any(w in n for w in HELPER_WORDS):
        return "helper"
    if n == "pelvis":
        return "pelvis"
    if n.startswith("spine"):
        return "torso"
    if n.startswith("neck") or n == "head":
        return "head"
    if n.startswith(FINGERS):
        return "fingers"
    if n.startswith(("clavicle", "upperarm", "lowerarm", "hand")):
        return "arms"
    if n.startswith(("thigh", "calf", "foot", "ball")):
        return "legs"
    return "other"


# ---- rotations (3x3, row vectors) ----

def orthonormal(m):
    u, _s, vt = np.linalg.svd(m)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    return r


def log_rot(r):
    """Rotation vector of a 3x3 (or a stack (..., 3, 3)), the axis in the matrix's own row convention."""
    r = np.asarray(r, float)
    tr = np.clip((np.trace(r, axis1=-2, axis2=-1) - 1.0) * 0.5, -1.0, 1.0)
    ang = np.arccos(tr)
    v = np.stack([r[..., 1, 2] - r[..., 2, 1], r[..., 2, 0] - r[..., 0, 2], r[..., 0, 1] - r[..., 1, 0]], -1)
    s = np.sin(ang)
    k = np.where(s > 1e-9, ang / (2.0 * np.where(s > 1e-9, s, 1.0)), 0.5)
    return v * k[..., None]


def exp_rot(v):
    v = np.asarray(v, float)
    ang = np.linalg.norm(v, axis=-1)
    safe = np.where(ang > 1e-12, ang, 1.0)
    a = v / safe[..., None]
    x, y, z = a[..., 0], a[..., 1], a[..., 2]
    c, s = np.cos(ang), np.sin(ang)
    C = 1.0 - c
    # the transpose of Rodrigues' column matrix: row vectors turn the same way about the axis
    m = np.stack([
        np.stack([c + x * x * C, x * y * C + z * s, x * z * C - y * s], -1),
        np.stack([y * x * C - z * s, c + y * y * C, y * z * C + x * s], -1),
        np.stack([z * x * C + y * s, z * y * C - x * s, c + z * z * C], -1)], -2)
    return np.where((ang > 1e-12)[..., None, None], m, np.eye(3))


def slerp(a, b, t):
    return exp_rot(log_rot(b @ a.T) * t) @ a


def between(u, v):
    """The row-vector rotation taking direction u onto v (the shortest)."""
    u = u / max(np.linalg.norm(u), 1e-12)
    v = v / max(np.linalg.norm(v), 1e-12)
    axis = np.cross(u, v)
    s = np.linalg.norm(axis)
    c = float(np.dot(u, v))
    if s < 1e-12:
        return np.eye(3)
    return exp_rot(axis / s * math.atan2(s, c))


# ---- the clip ----

class Clip(object):
    """names, parents (index or -1), locals (J, N, 4, 4), the top joint's parent world (4x4)."""

    def __init__(self, names, parents, locals_, top_parent):
        self.names = list(names)
        self.parents = list(parents)
        self.locals = np.asarray(locals_, float)
        self.top_parent = np.asarray(top_parent, float)
        self.index = dict((n, i) for i, n in enumerate(self.names))
        self.n = self.locals.shape[1]


def fk(clip_names, parents, locals_, top_parent):
    J, N = locals_.shape[:2]
    w = np.empty_like(locals_)
    for j in range(J):
        p = parents[j]
        base = w[p] if p >= 0 else np.broadcast_to(top_parent, (N, 4, 4))
        w[j] = locals_[j] @ base
    return w


class Idle(object):
    """The clip read: means and motion per joint."""

    def __init__(self, clip):
        self.clip = clip
        L = clip.locals
        J, N = L.shape[:2]
        self.groups = [group_of(n) for n in clip.names]
        self.rot_mean = np.empty((J, 3, 3))
        self.rot_dev = np.empty((J, N, 3))
        for j in range(J):
            R = L[j, :, :3, :3]
            M = orthonormal(R.sum(0))
            self.rot_mean[j] = M
            self.rot_dev[j] = log_rot(R @ M.T)
        self.trans = L[:, :, 3, :3].copy()
        self.worlds = fk(clip.names, clip.parents, L, clip.top_parent)
        ix = clip.index
        self.pelvis = ix.get("pelvis")
        self.root = ix.get("root", 0)
        if self.pelvis is not None:
            self.pelvis_mean = self.trans[self.pelvis].mean(0)
        self.legs = {}
        for s in ("l", "r"):
            names = ("thigh_" + s, "calf_" + s, "foot_" + s)
            if all(n in ix for n in names):
                th, ca, fo = (ix[n] for n in names)
                rel = self.worlds[fo] @ np.linalg.inv(self.worlds[self.root])     # the foot over the root
                pos = rel[:, 3, :3]
                rot = rel[:, :3, :3]
                F = orthonormal(rot.sum(0))
                self.legs[s] = dict(th=th, ca=ca, fo=fo, pos_mean=pos.mean(0), pos_dev=pos - pos.mean(0),
                                    rot_mean=F, rot_dev=log_rot(np.einsum("ij,njk->nik", F.T, rot)))
        self.followers = self._followers()
        self.loops = bool(self.pelvis is not None and np.linalg.norm(self.worlds[self.pelvis, 0, 3, :3] - self.worlds[self.pelvis, -1, 3, :3]) < 0.5)

    def _followers(self):
        """{helper index: (body index, the helper's world over the body's)} for helpers riding a bone rigidly."""
        out = {}
        W = self.worlds
        body = [j for j, g in enumerate(self.groups) if g not in ("helper", "root")]
        for h, g in enumerate(self.groups):
            if g != "helper":
                continue
            best = None
            for b in body:
                rel = W[h] @ np.linalg.inv(W[b])
                tstd = float(np.linalg.norm(rel[:, 3, :3].std(0)))
                m = orthonormal(rel[:, :3, :3].sum(0))
                rdev = float(np.degrees(np.linalg.norm(log_rot(rel[:, :3, :3] @ m.T), axis=-1).max()))
                if tstd < RIGID_CM and rdev < RIGID_DEG:
                    score = tstd + rdev * 0.01
                    if best is None or score < best[0]:
                        rm = np.eye(4)
                        rm[:3, :3] = m
                        rm[3, :3] = rel[:, 3, :3].mean(0)
                        best = (score, b, rm)
            if best is not None:
                out[h] = (best[1], best[2])
        return out


# ---- the pose ----

def pose_targets(idle, out):
    """From a pose carried onto the skeleton ({leaf: 4x4 world}): each joint's local rotation, the pelvis's
    local place, each foot over the root."""
    clip = idle.clip
    rot, pelvis, feet = {}, None, {}
    for j, name in enumerate(clip.names):
        if name not in out:
            continue
        p = clip.parents[j]
        parent = out.get(clip.names[p]) if p >= 0 else None
        if p >= 0 and parent is None:
            continue
        local = out[name] @ np.linalg.inv(parent) if parent is not None else out[name] @ np.linalg.inv(clip.top_parent)
        rot[j] = orthonormal(local[:3, :3])
        if j == idle.pelvis:
            pelvis = local[3, :3].copy()
    root = out.get(clip.names[idle.root])
    if root is not None:
        for s, leg in idle.legs.items():
            fo = clip.names[leg["fo"]]
            if fo in out:
                rel = out[fo] @ np.linalg.inv(root)
                feet[s] = (rel[3, :3].copy(), orthonormal(rel[:3, :3]))
    return rot, pelvis, feet


# ---- the rebuild ----

def _resample(arr, times):
    """arr (N, ...) read at fractional frames `times`, linear."""
    N = arr.shape[0]
    t = np.clip(times, 0.0, N - 1)
    i0 = np.floor(t).astype(int)
    i1 = np.minimum(i0 + 1, N - 1)
    f = (t - i0).reshape((-1,) + (1,) * (arr.ndim - 1))
    return arr[i0] * (1.0 - f) + arr[i1] * f


def _blur(arr, sigma):
    if sigma <= 1e-6:
        return arr
    r = int(math.ceil(sigma * 3))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.concatenate([arr[r:0:-1], arr, arr[-2:-r - 2:-1]], 0) if arr.shape[0] > r + 1 else arr
    if pad is arr:
        return arr
    out = np.zeros_like(arr)
    for i, w in enumerate(k):
        out += w * pad[i:i + arr.shape[0]]
    return out


def _seam(arr, frames):
    """The last `frames` eased so the last frame equals the first."""
    n = arr.shape[0]
    s = int(round(frames))
    if s < 1 or n < 3:
        return arr
    s = min(s, n - 1)
    err = arr[-1] - arr[0]
    out = arr.copy()
    for i in range(n - s - 1, n):
        u = (i - (n - s - 1)) / float(s)
        w = u * u * (3.0 - 2.0 * u)
        out[i] = out[i] - err * w
    return out


def _two_bone(hip, knee_hint, ankle, l1, l2):
    d = ankle - hip
    D = float(np.linalg.norm(d))
    D = min(max(D, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    dn = d / max(np.linalg.norm(d), 1e-12)
    side = knee_hint - hip
    perp = side - dn * float(np.dot(side, dn))
    if np.linalg.norm(perp) < 1e-9:
        perp = np.cross(dn, (0.0, 0.0, 1.0)) if abs(dn[2]) < 0.9 else np.cross(dn, (1.0, 0.0, 0.0))
    perp = perp / np.linalg.norm(perp)
    x = (l1 * l1 - l2 * l2 + D * D) / (2.0 * D)
    y = math.sqrt(max(l1 * l1 - x * x, 0.0))
    return hip + dn * x + perp * y, hip + dn * D


def evaluate(idle, given=None, pose=None, parts=ALL_PARTS):
    """(the new locals (J, N', 4, 4), info). `pose` = pose_targets(...) or None."""
    k = knobs(given)
    clip = idle.clip
    J = len(clip.names)
    N = clip.n
    tempo = k["tempo"]
    n_out = max(2, int(round((N - 1) / tempo)) + 1)
    times = np.arange(n_out) * tempo
    parts = set(parts or ())
    share = k["share"] if pose else 0.0
    rot_t, pelvis_t, feet_t = pose if pose else ({}, None, {})

    def gain(g):
        if g in ("root", "helper", "other"):
            return 1.0
        if g == "legs":
            return k["motion"]
        return k[g] * k["motion"]

    def part_share(g):
        if g == "fingers":
            g = "arms"
        if g == "pelvis" and "torso" not in parts:
            return 0.0
        return share if g in parts else 0.0

    def motion(arr):
        a = _resample(arr, times)
        a = _blur(a, k["smooth"])
        return _seam(a, k["seam"])

    L = np.zeros((J, n_out, 4, 4))
    L[:, :, 3, 3] = 1.0
    for j in range(J):
        g = idle.groups[j]
        dev = motion(idle.rot_dev[j]) * gain(g)
        M = idle.rot_mean[j]
        s = part_share(g)
        if s > 0 and j in rot_t:
            M = slerp(M, rot_t[j], s)
        L[j, :, :3, :3] = exp_rot(dev) @ M
        L[j, :, 3, :3] = motion(idle.trans[j])
    if idle.pelvis is not None:
        p = idle.pelvis
        mean = idle.pelvis_mean.copy()
        s = share if "pelvis" in parts else 0.0
        if s > 0 and pelvis_t is not None:
            mean = mean * (1.0 - s) + pelvis_t * s
        dev = motion(idle.trans[p] - idle.pelvis_mean) * (k["pelvis"] * k["motion"])
        up_world = np.array([0.0, 1.0, 0.0])
        root_rot = idle.worlds[idle.root, 0, :3, :3]
        up_local = up_world @ root_rot.T          # a world vector into the root's frame (row vectors)
        L[p, :, 3, :3] = mean + dev + up_local * k["height"]

    W = fk(clip.names, clip.parents, L, clip.top_parent)
    info = {"frames": n_out, "short": {}}
    # the legs onto their feet
    root_w = W[idle.root]
    for s, leg in idle.legs.items():
        th, ca, fo = leg["th"], leg["ca"], leg["fo"]
        pos_mean, F = leg["pos_mean"], leg["rot_mean"]
        sl = share if "legs" in parts else 0.0
        if sl > 0 and s in feet_t:
            pos_mean = pos_mean * (1.0 - sl) + feet_t[s][0] * sl
            F = slerp(F, feet_t[s][1], sl)
        fg = k["feet"] * k["motion"]
        pos = pos_mean + motion(leg["pos_dev"]) * fg
        rot = F[None] @ exp_rot(motion(leg["rot_dev"]) * fg)
        l1 = np.linalg.norm(L[ca, :, 3, :3], axis=-1)
        l2 = np.linalg.norm(L[fo, :, 3, :3], axis=-1)
        worst = 0.0
        for t in range(n_out):
            rw = root_w[t]
            ankle = np.append(pos[t], 1.0) @ rw
            ankle = ankle[:3]
            hip = W[th, t, 3, :3]
            knee_fk = W[ca, t, 3, :3]
            knee, reach = _two_bone(hip, knee_fk, ankle, l1[t], l2[t])
            worst = max(worst, float(np.linalg.norm(reach - ankle)))
            tw = W[th, t].copy()
            tw[:3, :3] = tw[:3, :3] @ between(knee_fk - hip, knee - hip)
            cw = L[ca, t] @ tw
            ankle_fk = (L[fo, t] @ cw)[3, :3]
            cw[:3, :3] = cw[:3, :3] @ between(ankle_fk - knee, reach - knee)
            fw = np.eye(4)
            fw[:3, :3] = rot[t] @ rw[:3, :3]
            parent = W[clip.parents[th], t]
            L[th, t, :3, :3] = orthonormal((tw @ np.linalg.inv(parent))[:3, :3])
            L[ca, t, :3, :3] = orthonormal((cw @ np.linalg.inv(tw))[:3, :3])
            L[fo, t, :3, :3] = orthonormal((fw @ np.linalg.inv(cw))[:3, :3])
        info["short"][s] = worst
    W = fk(clip.names, clip.parents, L, clip.top_parent)
    info["held"] = _weapon_hold(idle, L, W, k, share if "arms" in parts else 0.0, idle.loops or k["seam"] >= 1.0)
    W = fk(clip.names, clip.parents, L, clip.top_parent)
    # helpers riding a bone ride it again
    for h, (b, rel) in sorted(idle.followers.items()):
        hw = rel[None] @ W[b]
        p = clip.parents[h]
        base = W[p] if p >= 0 else np.broadcast_to(clip.top_parent, hw.shape)
        L[h] = hw @ np.linalg.inv(base)
        W = fk(clip.names, clip.parents, L, clip.top_parent)
    info["followers"] = len(idle.followers)
    return L, info


# ---- Weapon: the hands on the chest, late (Walk Builder's Weapon tab) ----

def _chest(idle):
    ix = idle.clip.index
    for name in ("spine_05", "spine_04", "spine_03"):
        if name in ix:
            return ix[name]
    spines = [j for j, g in enumerate(idle.groups) if g == "torso"]
    return spines[-1] if spines else None


def _late(mats, lag, cyclic):
    """(N, 4, 4) read `lag` frames earlier: places lerped, turns slerped; a loop wraps, else the ends hold."""
    n = mats.shape[0]
    out = np.empty_like(mats)
    period = n - 1 if cyclic and n > 2 else None
    for t in range(n):
        u = t - lag
        if period:
            u = u % period
        else:
            u = min(max(u, 0.0), n - 1)
        i0 = int(math.floor(u))
        i1 = min(i0 + 1, n - 1)
        f = u - i0
        m = np.eye(4)
        m[:3, :3] = slerp(mats[i0, :3, :3], mats[i1, :3, :3], f)
        m[3, :3] = mats[i0, 3, :3] * (1.0 - f) + mats[i1, 3, :3] * f
        out[t] = m
    return out


def _weapon_hold(idle, L, W, k, alpha, cyclic):
    """Each held hand rides the chest rigidly at its own mean offset, the chest read `overlap` ms late; the
    arm (upperarm, lowerarm) solved onto it by two-bone IK, the hand's turn set. Only where the pose holds the
    arms (`alpha`, the pose's share on Arms). Answers {side: cm the hand moved at most}."""
    out = {}
    chest = _chest(idle)
    if chest is None or alpha <= 0.0:
        return out
    ix = idle.clip.index
    names = idle.clip.names
    parents = idle.clip.parents
    C = W[chest]
    for s in ("l", "r"):
        hold = k["hold_" + s]
        if hold < 0.5:
            continue
        chain = ("upperarm_" + s, "lowerarm_" + s, "hand_" + s)
        if not all(n in ix for n in chain):
            continue
        up, lo, ha = (ix[n] for n in chain)
        H = W[ha].copy()
        rel = H @ np.linalg.inv(C)
        A = np.eye(4)
        A[:3, :3] = orthonormal(rel[:, :3, :3].sum(0))
        A[3, :3] = rel[:, 3, :3].mean(0)
        lag = k["overlap_" + s] * k["fps"] / 1000.0
        want = A[None] @ _late(C, lag, cyclic)
        n_out = H.shape[0]
        worst = 0.0
        for t in range(n_out):
            target = np.eye(4)
            target[:3, :3] = slerp(H[t, :3, :3], want[t, :3, :3], alpha)
            target[3, :3] = H[t, 3, :3] * (1.0 - alpha) + want[t, 3, :3] * alpha
            worst = max(worst, float(np.linalg.norm(target[3, :3] - H[t, 3, :3])))
            pw = W[parents[up], t]
            uw = L[up, t] @ pw
            shoulder = uw[3, :3]
            elbow_fk = (L[lo, t] @ uw)[3, :3]
            l1 = float(np.linalg.norm(L[lo, t, 3, :3]))
            l2 = float(np.linalg.norm(L[ha, t, 3, :3]))
            elbow, reach = _two_bone(shoulder, elbow_fk, target[3, :3], l1, l2)
            uw[:3, :3] = uw[:3, :3] @ between(elbow_fk - shoulder, elbow - shoulder)
            lw = L[lo, t] @ uw
            wrist_fk = (L[ha, t] @ lw)[3, :3]
            lw[:3, :3] = lw[:3, :3] @ between(wrist_fk - elbow, reach - elbow)
            hw = np.eye(4)
            hw[:3, :3] = target[:3, :3]
            L[up, t, :3, :3] = orthonormal((uw @ np.linalg.inv(pw))[:3, :3])
            L[lo, t, :3, :3] = orthonormal((lw @ np.linalg.inv(uw))[:3, :3])
            L[ha, t, :3, :3] = orthonormal((hw @ np.linalg.inv(lw))[:3, :3])
        out[s] = worst
        W[:] = fk(names, parents, L, idle.clip.top_parent)
    return out
