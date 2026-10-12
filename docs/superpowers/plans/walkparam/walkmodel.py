"""walkmodel.py - the parametric walk's model: a walk cycle read once, rebuilt from knobs.

numpy only, no Maya (tests/test_walkmodel.py runs it on a synthetic walker). Maya's row vectors
throughout: a world matrix is local . parent, a position its row 3, a rotation turns a row vector v as
v . R. The design: docs/superpowers/specs/2026-10-12-parametric-walk-design.md.
"""
import math
import re

import numpy as np

VERSION = 1

# name, default, low, high - tempo 0 means the source's own cycle length
KNOBS = (
    ("pose", 0.0, 0.0, 1.0),
    ("stride", 1.0, 0.4, 1.8),
    ("tempo", 0.0, 0.0, 2000.0),
    ("lift", 1.0, 0.0, 3.0),
    ("width", 0.0, -15.0, 25.0),
    ("bob", 1.0, 0.0, 3.0),
    ("sway", 1.0, 0.0, 3.0),
    ("pelvis_rot", 1.0, 0.0, 3.0),
    ("spine", 1.0, 0.0, 3.0),
    ("arms", 1.0, 0.0, 3.0),
    ("head", 1.0, 0.0, 3.0),
    ("overlap", 0.0, 0.0, 6.0),
    ("weight", 0.0, -1.0, 2.0),
    ("exaggeration", 1.0, 0.0, 2.0),
)
DEFAULTS = dict((k[0], k[1]) for k in KNOBS)
RANGES = dict((k[0], (k[2], k[3])) for k in KNOBS)

WEIGHT_BOB_DOWN = 0.5     # the bob's low half x (1 + this . weight)
WEIGHT_BOB_UP = 0.15      # its high half x max(0, 1 - this . weight)
WEIGHT_WARP = 0.3         # the bob's clock: beta = this . weight
WEIGHT_WARP_AFTER = 0.05  # slowest this share of a cycle after each low
WEIGHT_LAG = 1.0          # frames of overlap per unit of weight
LOWER_BLUR = 0.06         # the reach's drop of the pelvis, smoothed over this share of a cycle (sigma)


class Refusal(Exception):
    """A clip the model does not read; the message says why, in the animator's terms."""


def knobs(**given):
    """The defaults with `given` on top, each clamped to its range; an unknown name raises ValueError."""
    unknown = sorted(set(given) - set(DEFAULTS))
    if unknown:
        raise ValueError("unknown knob(s): " + ", ".join(unknown))
    out = dict(DEFAULTS)
    for name, value in given.items():
        if value is None:
            continue
        low, high = RANGES[name]
        out[name] = min(max(float(value), low), high)
    return out


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
    """`mean` turned the share `alpha` of the way to `target` (row-vector rotations; 0 is `mean`, 1 is
    `target`): exp(alpha . log(target . mean^-1)) . mean."""
    if alpha <= 0.0:
        return mean
    return exp_rot(alpha * log_rot(target @ mean.T)) @ mean


def turned_about(v, axis, angle):
    """The vector `v` turned `angle` radians about the unit `axis` (right hand; Rodrigues)."""
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * float(np.dot(axis, v)) * (1.0 - c)


def matrix(rot, pos):
    out = np.eye(4)
    out[:3, :3] = rot
    out[3, :3] = pos
    return out


def periodic_cr(x, tau):
    """Periodic Catmull-Rom through x[0..P-1] (period P) at any real tau; exact on whole frames."""
    p = x.shape[0]
    i = int(math.floor(tau))
    u = tau - i
    p1 = x[i % p]
    if u < 1e-12:
        return np.array(p1, float)
    p0, p2, p3 = x[(i - 1) % p], x[(i + 1) % p], x[(i + 2) % p]
    return 0.5 * (2.0 * p1 + (p2 - p0) * u + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * u * u
                  + (3.0 * p1 - p0 - 3.0 * p2 + p3) * u ** 3)


def warp(phi, beta, phi0):
    """The bob's clock: slowest (slope 1 - beta) a quarter and three quarters of a cycle after phi0."""
    return phi + beta / (4.0 * math.pi) * math.sin(4.0 * math.pi * (phi - phi0))


def smooth_cover(need, sigma):
    """A smooth periodic curve lying over `need` (one value a frame, periodic): `need` widened by its
    largest neighbour within `sigma` frames (so a narrow peak is not blurred away), blurred with a Gaussian
    of `sigma` frames, then scaled by the least factor that covers every frame's need."""
    need = np.asarray(need, float)
    n = len(need)
    if n == 0 or need.max() <= 0.0:
        return np.zeros(n)
    reach = int(round(sigma))
    wide = np.max([np.roll(need, s) for s in range(-reach, reach + 1)], axis=0)
    offsets = np.arange(n)
    distance = np.minimum(offsets, n - offsets)
    kernel = np.exp(-0.5 * (distance / max(sigma, 1e-6)) ** 2)
    blur = np.real(np.fft.ifft(np.fft.fft(wide) * np.fft.fft(kernel / kernel.sum())))
    wanted = need > 1e-9
    return np.maximum(blur * float((need[wanted] / np.maximum(blur[wanted], 1e-12)).max()), 0.0)


def shape_bob(v, weight):
    """The weight on one bob sample about its mean: the low half deeper, the high half flatter."""
    if v < 0.0:
        return v * (1.0 + WEIGHT_BOB_DOWN * weight)
    return v * max(0.0, 1.0 - WEIGHT_BOB_UP * weight)


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


def _frame(u, n):
    return np.stack([u, n, np.cross(u, n)])


def align(u_src, n_src, u_new, n_new):
    """The rotation taking the frame (u_src, n_src) onto (u_new, n_new): v . align = v'.
    Each n must be perpendicular to its u (a leg plane's normal against a bone in the plane)."""
    return _frame(u_src, n_src).T @ _frame(u_new, n_new)


SIDES = ("l", "r")
SIDE_WORD = {"l": "left", "r": "right"}
LEG = ("thigh", "calf", "foot")
HELPER_PREFIXES = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass")
ARM_STEMS = ("clavicle", "upperarm", "lowerarm", "hand")
LAG = {"spine_01": 0.2, "spine_02": 0.3, "spine_03": 0.4, "spine_04": 0.5, "spine_05": 0.6,
       "neck_01": 0.7, "neck_02": 0.8, "head": 0.9,
       "clavicle": 0.6, "upperarm": 0.8, "lowerarm": 1.0, "hand": 1.0}
CONTACT_SHARE = 0.2      # in stance the ankle or the ball moves less than this share of the travel a frame
FOLLOW_TOL = 1e-3        # a helper follows a bone when helper . bone^-1 holds within this (matrix elements)
LOOP_TOL = (0.1, 0.002)  # cm and rotation elements: the last frame against the first moved by the travel


def _stem(name):
    m = re.match(r"([a-z]+)(_twist_\d+)?_[lr]$", name)
    return m.group(1) if m else None


class Clip(object):
    """A walk cycle as data: joint names, parent indices (-1: none), world matrices (J, P+1, 4, 4) on the
    clip's whole frames (the last the first moved by the travel), frames a second, the world's up."""

    def __init__(self, names, parents, worlds, fps=30.0, up=(0.0, 1.0, 0.0), name="walk"):
        self.names = list(names)
        self.parents = [int(p) for p in parents]
        self.worlds = np.asarray(worlds, float)
        self.fps = float(fps)
        self.up = _unit(up)
        self.name = name


class Foot(object):
    """A foot's contact: stance from frame `on` for `length` frames more, mid-stance at `mid`, the
    footprint's coordinates (along, aside, up) against the travel line there."""

    def __init__(self, side, on, length, mid, coords):
        self.side, self.on, self.length, self.mid, self.coords = side, on, length, mid, coords


def analyse(clip):
    """The clip read once (refusals by name); evaluate() rebuilds it from knobs."""
    return Walk(clip)


class Walk(object):

    def __init__(self, clip):
        self.clip = clip
        self.names, self.parents = clip.names, clip.parents
        self.index = dict((n, i) for i, n in enumerate(self.names))
        need = ["root", "pelvis"] + ["%s_%s" % (b, s) for s in SIDES for b in LEG + ("ball",)]
        missing = [n for n in need if n not in self.index]
        if missing:
            raise Refusal("not a skeleton this model reads (UE names): no " + ", ".join(missing))
        count, frames = clip.worlds.shape[:2]
        if frames < 9:
            raise Refusal("%d frames: too short for a walk cycle" % frames)
        self.P = P = frames - 1
        self.fps, self.up = clip.fps, clip.up
        rot = clip.worlds[:, :, :3, :3]
        rot = rot / np.linalg.norm(rot, axis=-1, keepdims=True)
        pos = clip.worlds[:, :, 3, :3]
        root = self.index["root"]
        travel = pos[root, P] - pos[root, 0]
        climb = float(np.dot(travel, self.up))
        flat = travel - climb * self.up
        if abs(climb) > 0.5:
            raise Refusal("the root climbs %.1f cm a cycle: a walk on flat ground only" % climb)
        if np.linalg.norm(flat) < 1.0:
            raise Refusal("the root travels %.2f cm a cycle: an in-place walk is not read yet (the root must "
                          "carry the travel)" % np.linalg.norm(flat))
        moved = float(np.abs(pos[:, P] - pos[:, 0] - travel).max())
        turned = float(np.abs(rot[:, P] - rot[:, 0]).max())
        if moved > LOOP_TOL[0] or turned > LOOP_TOL[1]:
            raise Refusal("not a closed loop: the last frame stands %.3f cm / %.4f off the first moved by the "
                          "travel - the cycle must end on its first pose" % (moved, turned))
        self.travel = travel
        self.fwd = _unit(flat)
        self.side = _unit(np.cross(self.up, self.fwd))
        self.basis = np.stack([self.fwd, self.side, self.up])     # travel coordinates: v . basis.T
        steps = np.arange(P) / float(P)
        self.origin = pos[root, 0] + (pos[root, :P] - pos[root, 0] - np.outer(steps, travel)).mean(axis=0)
        self.rot, self.pos = rot[:, :P], pos[:, :P]
        self.pdev = self.pos - (self.origin + np.outer(steps, travel))[None]
        self.wmean = np.stack([mean_rot(self.rot[j]) for j in range(count)])
        self.wlog = log_rot(self.rot @ np.swapaxes(self.wmean, -1, -2)[:, None])
        self._locals()
        self._kinds()
        self.feet = dict((s, self._contact(s)) for s in SIDES)
        self.reach = dict((s, self._reach(s)) for s in SIDES)
        self.follows = self._helpers()
        self.world_arms = set(self.index[n] for n in ("upperarm_l", "upperarm_r") if n in self.index)
        self.root_mean = (self.pdev[root] @ self.basis.T).mean(axis=0)
        self.pelvis_mean = (self.pdev[self.index["pelvis"]] @ self.basis.T).mean(axis=0)
        bob = self.pdev[self.index["pelvis"]] @ self.up - self.pelvis_mean[2]
        self.low_phase = float(np.argmin(bob)) / P

    # -- the source, sampled at any source time tau (whole frames exact) --

    def line(self, tau):
        return self.origin + self.travel * (tau / float(self.P))

    def wrot(self, j, tau, gain=1.0):
        return exp_rot(gain * periodic_cr(self.wlog[j], tau)) @ self.wmean[j]

    def wpos(self, j, tau):
        return periodic_cr(self.pdev[j], tau) + self.line(tau)

    def lrot_at(self, j, tau, gain=1.0):
        return exp_rot(gain * periodic_cr(self.llog[j], tau)) @ self.lmean[j]

    def lt_at(self, j, tau):
        return periodic_cr(self.lt[j], tau)

    def source_world(self, j, tau):
        return matrix(self.wrot(j, tau), self.wpos(j, tau))

    def summary(self):
        flat = self.travel - np.dot(self.travel, self.up) * self.up
        stance = " ".join("%s %d %%" % (s.upper(), round(100.0 * (self.feet[s].length + 1) / self.P))
                          for s in SIDES)
        return "%s: cycle %d frames (%.2f s), stride %.1f cm, %.2f m/s, stance %s" % (
            self.clip.name, self.P, self.P / self.fps, np.linalg.norm(flat) / 2.0,
            np.linalg.norm(flat) / (self.P / self.fps) / 100.0, stance)

    # -- the analysis --

    def _locals(self):
        count = len(self.names)
        self.lt = np.zeros_like(self.pos)
        self.lmean = np.tile(np.eye(3), (count, 1, 1))
        self.llog = np.zeros_like(self.pos)
        for j, p in enumerate(self.parents):
            if p < 0:
                continue
            back = np.swapaxes(self.rot[p], -1, -2)
            lrot = self.rot[j] @ back
            self.lt[j] = np.einsum("fi,fij->fj", self.pos[j] - self.pos[p], back)
            self.lmean[j] = mean_rot(lrot)
            self.llog[j] = log_rot(lrot @ self.lmean[j].T)

    def _ancestors(self, j):
        out = []
        p = self.parents[j]
        while p >= 0:
            out.append(p)
            p = self.parents[p]
        return out

    def _kinds(self):
        legs = set("%s_%s" % (b, s) for s in SIDES for b in LEG)
        self.kind, self.lag = [], []
        for j, name in enumerate(self.names):
            above = [self.names[a] for a in self._ancestors(j)]
            if name in ("root", "pelvis"):
                kind = name
            elif name in legs:
                kind = "leg"
            elif name.startswith(HELPER_PREFIXES) or any(a.startswith(HELPER_PREFIXES) for a in above):
                kind = "helper"
            elif re.match(r"(spine|neck)_\d+$", name):
                kind = "spine"
            elif name == "head":
                kind = "head"
            elif _stem(name) in ARM_STEMS:
                kind = "arm"
            elif "hand_l" in above or "hand_r" in above:
                kind = "finger"
            elif self.parents[j] < 0:
                kind = "world"
            else:
                kind = "local"
            self.kind.append(kind)
            self.lag.append(LAG.get(name, LAG.get(_stem(name), 1.0 if kind == "finger" else 0.0)))
        kids = dict((j, []) for j in range(len(self.names)))
        for j, p in enumerate(self.parents):
            if p >= 0:
                kids[p].append(j)
        bfs, queue = [], [j for j, p in enumerate(self.parents) if p < 0]
        while queue:
            j = queue.pop(0)
            bfs.append(j)
            queue.extend(kids[j])
        self.order = [j for j in bfs if self.kind[j] != "helper"] + [j for j in bfs if self.kind[j] == "helper"]

    def _contact(self, side):
        P = self.P
        speeds = []
        for name in ("foot_" + side, "ball_" + side):
            p = self.pos[self.index[name]]
            ahead = np.vstack([p[1:], p[:1] + self.travel])
            behind = np.vstack([p[-1:] - self.travel, p[:-1]])
            speeds.append(np.linalg.norm(ahead - behind, axis=1) / 2.0)
        slow = np.minimum(speeds[0], speeds[1]) < np.linalg.norm(self.travel) / P * CONTACT_SHARE
        if slow.all():
            raise Refusal("the %s foot never leaves the ground" % SIDE_WORD[side])
        if not slow.any():
            raise Refusal("the %s foot never stops: no contact to plant it on" % SIDE_WORD[side])
        start = int(np.nonzero(~slow)[0][0])
        best, run, run_on = (0, 0), 0, 0
        for step in range(1, P + 1):
            i = (start + step) % P
            if slow[i]:
                if run == 0:
                    run_on = i
                run += 1
                if run > best[1]:
                    best = (run_on, run)
            else:
                run = 0
        on, length = best[0], best[1] - 1
        mid = on + length / 2.0
        coords = periodic_cr(self.pdev[self.index["foot_" + side]], mid) @ self.basis.T
        return Foot(side, on, length, mid, coords)

    def _reach(self, side):
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        d = np.linalg.norm(self.pos[fo] - self.pos[th], axis=1)
        return float((d / (np.linalg.norm(self.lt[ca], axis=1) + np.linalg.norm(self.lt[fo], axis=1))).max())

    def _helpers(self):
        worlds = self.clip.worlds[:, :self.P]
        body = [j for j, k in enumerate(self.kind) if k != "helper"]
        follows = {}
        for h, kind in enumerate(self.kind):
            if kind != "helper":
                continue
            best = None
            for b in body:
                rel = worlds[h] @ np.linalg.inv(worlds[b])
                err = float(np.abs(rel - rel[0]).max())
                if err < FOLLOW_TOL:
                    key = (len(self._ancestors(b)), err)
                    if best is None or key < best[0]:
                        best = (key, b, rel[0])
            if best is not None:
                follows[h] = (best[1], best[2])
        return follows

    # -- the new cycle --
    def evaluate(self, given=None, pose=None):
        """The cycle rebuilt from knobs (the spec's model); the defaults give the source back. `pose` (from
        walkpose.prepare: {"spine": {joint: local 3x3}, "head": 3x3, "pelvis": 3x3, "height": cm over the
        travel line, "knee_turn": {side: radians}}) replaces the mean pose the knob `pose`'s share."""
        k = knobs(**(given or {}))
        P = self.P
        n = max(int(round(k["tempo"])), 4) if k["tempo"] >= 1.0 else P
        ctx = {"k": k, "ex": k["exaggeration"], "travel2": self.travel * k["stride"],
               "lag": max(0.0, k["overlap"] + WEIGHT_LAG * k["weight"]) * P / float(n),
               "beta": min(max(WEIGHT_WARP * k["weight"], -0.9), 0.9),
               "phi0": self.low_phase + WEIGHT_WARP_AFTER - 0.25,
               "pose": pose if (pose and k["pose"] > 0.0) else None, "alpha": k["pose"]}
        times = [(f / float(n), f * P / float(n)) for f in range(n + 1)]
        drop = self._lowering(times, ctx)
        worlds = np.tile(np.eye(4), (len(self.names), n + 1, 1, 1))
        short = 0.0
        for f, (phi, tau) in enumerate(times):
            worlds[:, f], frame_short = self._frame(phi, tau, ctx, drop[f])
            short = max(short, frame_short)
        flat = ctx["travel2"] - np.dot(ctx["travel2"], self.up) * self.up
        info = {"frames": n, "stride_cm": float(np.linalg.norm(flat)) / 2.0,
                "speed": float(np.linalg.norm(flat)) / (n / self.fps) / 100.0, "lowered": float(max(drop)),
                "drop": [float(d) for d in drop], "short": short, "lag": ctx["lag"] * n / float(P), "knobs": k}
        return Result(worlds, n, info)

    def foot_target(self, side, tau, stride, width, lift):
        """The new foot at source time tau: (world rotation, ankle position). Stance: the source's foot
        moved with its footprint; swing: the source's swing between the new footprints, its lift scaled."""
        foot, j, P = self.feet[side], self.index["foot_" + side], self.P
        rot, src = self.wrot(j, tau), self.wpos(j, tau)
        travel2 = self.travel * stride
        k = math.floor((tau - foot.on) / P)
        r = tau - foot.on - k * P
        sign = 1.0 if side == "l" else -1.0
        shift = ((travel2 - self.travel) * ((foot.mid + k * P) / P)
                 + (stride - 1.0) * foot.coords[0] * self.fwd + sign * width / 2.0 * self.side)
        if r <= foot.length + 1e-9:
            return rot, src + shift
        t_off, t_on = foot.on + foot.length + k * P, foot.on + (k + 1) * P
        p_off, p_on = self.wpos(j, t_off), self.wpos(j, t_on)
        x, x_off, x_on = (float(np.dot(p, self.fwd)) for p in (src, p_off, p_on))
        s = (x - x_off) / (x_on - x_off) if abs(x_on - x_off) > 1e-9 else (r - foot.length) / (P - foot.length)
        print_k = self.wpos(j, foot.mid + k * P)
        base = (1.0 - s) * (p_off - print_k) + s * (p_on - print_k - self.travel)
        lift_up = float(np.dot(src - print_k - s * self.travel - base, self.up))
        return rot, src + shift + s * (travel2 - self.travel) + (lift - 1.0) * lift_up * self.up

    def _body(self, phi, tau, ctx, drop=0.0):
        """The root's and the pelvis's new (rotation, position); the pelvis `drop` cm lower for the reach."""
        k, ex = ctx["k"], ctx["ex"]
        line2 = self.origin + ctx["travel2"] * phi
        out = {}
        for name, mean in (("root", self.root_mean), ("pelvis", self.pelvis_mean)):
            j = self.index[name]
            dev = periodic_cr(self.pdev[j], tau) @ self.basis.T
            along = mean[0] + k["stride"] * ex * (dev[0] - mean[0])
            aside = mean[1] + k["sway"] * ex * (dev[1] - mean[1])
            if name == "pelvis":
                pose, a = ctx["pose"], ctx["alpha"]
                v = float(periodic_cr(self.pdev[j], warp(phi, ctx["beta"], ctx["phi0"]) * self.P) @ self.up) - mean[2]
                base = mean[2] if pose is None else (1.0 - a) * mean[2] + a * pose["height"]
                height = base + k["bob"] * ex * shape_bob(v, k["weight"]) - drop
                centre = self.wmean[j] if pose is None else toward(self.wmean[j], pose["pelvis"], a)
                rot = exp_rot(k["pelvis_rot"] * ex * periodic_cr(self.wlog[j], tau)) @ centre
            else:
                height, rot = dev[2], self.wrot(j, tau)
            out[name] = (rot, line2 + np.array([along, aside, height]) @ self.basis)
        return out

    def _lowering(self, times, ctx):
        """The pelvis's drop on every frame (the last = the first): each frame needs the least drop that lets
        both legs reach without straightening past the source's straightest; the drop is a smooth periodic
        curve over those needs (smooth_cover), so a long stride sinks the contacts, not the whole cycle."""
        k = ctx["k"]
        need = np.zeros(len(times) - 1)
        for f, (phi, tau) in enumerate(times[:-1]):
            pelvis_rot, pelvis_pos = self._body(phi, tau, ctx)["pelvis"]
            for side in SIDES:
                th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
                hip = self.lt_at(th, tau) @ pelvis_rot + pelvis_pos
                ankle = self.foot_target(side, tau, k["stride"], k["width"], k["lift"] * ctx["ex"])[1]
                limit = self.reach[side] * (np.linalg.norm(self.lt_at(ca, tau)) + np.linalg.norm(self.lt_at(fo, tau)))
                q = ankle - hip
                if np.linalg.norm(q) <= limit * (1.0 + 1e-9):
                    continue
                qu = float(np.dot(q, self.up))
                disc = qu * qu - (float(np.dot(q, q)) - limit * limit)
                if disc >= 0.0:
                    need[f] = max(need[f], -qu - math.sqrt(disc))
        drop = smooth_cover(need, LOWER_BLUR * len(need))
        return np.append(drop, drop[0])

    def _frame(self, phi, tau, ctx, drop=0.0):
        """Every joint's new world at one frame (parents first, helpers last); and how far a foot fell short."""
        k, ex = ctx["k"], ctx["ex"]
        rots, poss = [None] * len(self.names), [None] * len(self.names)
        body = self._body(phi, tau, ctx, drop)
        gains = {"spine": k["spine"] * ex, "arm": k["arms"] * ex}
        short = 0.0
        for j in self.order:
            if rots[j] is not None:
                continue
            kind, name, p = self.kind[j], self.names[j], self.parents[j]
            if kind in ("root", "pelvis"):
                rots[j], poss[j] = body[name]
            elif kind == "world":
                rots[j], poss[j] = self.wrot(j, tau), self.wpos(j, tau) + (ctx["travel2"] - self.travel) * phi
            elif kind == "leg":
                short = max(short, self._leg(name[-1], tau, rots, poss, ctx))
            elif kind == "helper" and j in self.follows:
                b, rel = self.follows[j]
                m = rel @ matrix(rots[b], poss[b])
                rots[j], poss[j] = m[:3, :3], m[3, :3]
            else:
                t = tau - self.lag[j] * ctx["lag"]
                pose, a = ctx["pose"], ctx["alpha"]
                if kind == "head":
                    centre = self.wmean[j] if pose is None else toward(self.wmean[j], pose["head"], a)
                    rots[j] = exp_rot(k["head"] * ex * periodic_cr(self.wlog[j], t)) @ centre
                elif j in self.world_arms:      # the upper arm hangs and swings in the world
                    rots[j] = exp_rot(k["arms"] * ex * periodic_cr(self.wlog[j], t)) @ self.wmean[j]
                else:
                    centre = self.lmean[j]
                    if pose is not None and j in pose["spine"]:
                        centre = toward(centre, pose["spine"][j], a)
                    rots[j] = exp_rot(gains.get(kind, 1.0) * periodic_cr(self.llog[j], t)) @ centre @ rots[p]
                poss[j] = self.lt_at(j, t) @ rots[p] + poss[p]
        out = np.tile(np.eye(4), (len(self.names), 1, 1))
        for j in range(len(self.names)):
            out[j, :3, :3], out[j, 3, :3] = rots[j], poss[j]
        return out, short

    def _leg(self, side, tau, rots, poss, ctx):
        """Thigh, calf and foot by IK from the new hip to the new foot; each bone turned by the rotation
        taking its source (direction, leg plane) onto the new one. Returns how far the foot fell short."""
        k = ctx["k"]
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        pelvis = self.parents[th]
        hip = self.lt_at(th, tau) @ rots[pelvis] + poss[pelvis]
        foot_rot, ankle = self.foot_target(side, tau, k["stride"], k["width"], k["lift"] * ctx["ex"])
        l1, l2 = float(np.linalg.norm(self.lt_at(ca, tau))), float(np.linalg.norm(self.lt_at(fo, tau)))
        h, kn, a = self.wpos(th, tau), self.wpos(ca, tau), self.wpos(fo, tau)
        e = _unit(a - h)
        bend = (kn - h) - np.dot(kn - h, e) * e
        bend = _unit(bend) if np.linalg.norm(bend) > 1e-6 else _unit(self.fwd - np.dot(self.fwd, e) * e)
        knee_bend = bend
        if ctx["pose"] is not None:     # the pose's knee heading: the bend turned about the leg (-e: up it)
            knee_bend = turned_about(bend, -e, ctx["alpha"] * ctx["pose"]["knee_turn"][side])
        knee, reached, short = two_bone(hip, ankle, l1, l2, knee_bend, self.reach[side])
        e2 = _unit(reached - hip)
        bend2 = _unit((knee - hip) - np.dot(knee - hip, e2) * e2)
        n_src, n_new = _unit(np.cross(e, bend)), _unit(np.cross(e2, bend2))
        rots[th] = self.wrot(th, tau) @ align(_unit(kn - h), n_src, _unit(knee - hip), n_new)
        rots[ca] = self.wrot(ca, tau) @ align(_unit(a - kn), n_src, _unit(reached - knee), n_new)
        rots[fo] = foot_rot
        poss[th], poss[ca], poss[fo] = hip, knee, reached
        return short


class Result(object):
    """The new cycle: world matrices (J, N+1, 4, 4) in the source's world, N, and what happened."""

    def __init__(self, worlds, frames, info):
        self.worlds, self.frames, self.info = worlds, frames, info


def describe(result):
    info = result.info
    text = "%d frames, stride %.1f cm, %.2f m/s" % (info["frames"], info["stride_cm"], info["speed"])
    if info["lowered"] > 0.05:
        text += " | pelvis lowered up to %.1f cm at the contacts for the reach" % info["lowered"]
    if info["short"] > 0.005:
        text += " | a foot falls %.1f cm short of its step" % info["short"]
    return text
