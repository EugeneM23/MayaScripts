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
    ("balance", 1.0, 0.0, 1.0),
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

# the balance: the centre of mass a pendulum over the feet's pressure (the walks are in centimetres - UE's)
GRAVITY = 981.0            # cm / s^2
GROUND_TOL = 2.5           # cm: a foot point this near its own lowest is on the ground
HEEL_SHARE = 0.4           # the heel point: the ankle this share of the foot (ankle to ball) further back
TOE_SHARE = 0.4            # the toe point: the ball this share of the foot further forward
FOLLOW_RANGE = (0.25, 1.25)  # how strongly the walk's own CoM follows its pendulum, fitted per axis, clamped
CARRY_STEPS = 5            # secant steps of the pelvis carry a frame
CARRY_TOL = 1e-4           # cm: a frame's CoM this near its target is done
BALANCE_ROUNDS = 4         # the carry and the reach's drop solved in turn at most this often
# de Leva (1996): % of the body and the centre's share from the proximal joint
TRUNK_MASS = (11.17, 16.33, 15.96)   # lower, middle, upper trunk: at the thirds of the pelvis..neck_01 chain
HEAD_MASS = 6.94                     # on the head joint
LIMB_MASS = (("upperarm", "lowerarm", 2.71, 0.5772), ("lowerarm", "hand", 1.62, 0.4574),
             ("thigh", "calf", 14.16, 0.4095), ("calf", "foot", 4.33, 0.4459), ("foot", "ball", 1.37, 0.4415))
HAND_MASS = (0.61, 0.5)              # half way from the wrist to middle_01 (else the hand's fingers' mean)


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


def pendulum(cop, seconds, height):
    """The centre of mass of a linear inverted pendulum, x'' = (g / height)(x - p), over one cycle of
    `seconds`: the pressure p (F samples a cycle, any columns) followed per harmonic k by w^2 / (w^2 + w_k^2),
    w^2 = g / height, w_k = 2 pi k / seconds - exactly at the mean, less the faster it swings."""
    cop = np.asarray(cop, float)
    frames = cop.shape[0]
    omega2 = GRAVITY / max(float(height), 1e-6)
    k = np.arange(frames // 2 + 1)
    gain = omega2 / (omega2 + (2.0 * math.pi * k / float(seconds)) ** 2)
    return np.fft.irfft(np.fft.rfft(cop, axis=0) * gain.reshape((-1,) + (1,) * (cop.ndim - 1)), n=frames, axis=0)


def _fill_periodic(values, known):
    """Rows of `values` not `known` filled by the periodic straight line between the known around them."""
    frames = len(values)
    have = np.nonzero(known)[0]
    out = np.array(values, float)
    for i in np.nonzero(~np.asarray(known))[0]:
        before = have[have < i][-1] if np.any(have < i) else have[-1] - frames
        after = have[have > i][0] if np.any(have > i) else have[0] + frames
        u = (i - before) / float(after - before)
        out[i] = (1.0 - u) * values[before % frames] + u * values[after % frames]
    return out


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
        self.balance_note = ""
        self._masses()
        self._grounds()
        self._own_pendulum()

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

    # -- the balance: the centre of mass and the feet's pressure --

    def _masses(self):
        """`self.mass`: de Leva's table as one weight a joint (each mass point a fixed blend of two joints),
        summing to 1; the trunk spread along pelvis..neck_01 at its thirds. A walk without that chain gets no
        masses and `balance_note` says why."""
        idx, mass = self.index, np.zeros(len(self.names))
        self.mass = mass
        if "neck_01" not in idx:
            self.balance_note = "no neck_01: Balance weighs the trunk from the pelvis to neck_01"
            return
        chain = [idx["neck_01"]]
        while chain[-1] != idx["pelvis"]:
            if self.parents[chain[-1]] < 0:
                self.balance_note = "neck_01 is not under the pelvis: Balance weighs the trunk along that chain"
                return
            chain.append(self.parents[chain[-1]])
        chain.reverse()
        lengths = np.linalg.norm(np.diff(self.pos[chain, 0], axis=0), axis=1)
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
                    fingers = [j for j, p in enumerate(self.parents) if p == hand and self.kind[j] == "finger"]
                mass[hand] += share * (1.0 - t if fingers else 1.0)
                for j in fingers:
                    mass[j] += share * t / len(fingers)
        self.mass = mass / mass.sum()

    def com(self, worlds):
        """The centre of mass of world matrices (J, F, 4, 4) -> (F, 3), or one frame's (J, 4, 4) -> (3,)."""
        return np.tensordot(self.mass, np.asarray(worlds)[..., 3, :3], axes=(0, 0))

    def _grounds(self):
        """Each foot point's ground contact a source frame: 1 at its own lowest, 0 GROUND_TOL above it."""
        self.ground = {}
        for side in SIDES:
            for name in ("foot_" + side, "ball_" + side):
                h = self.pos[self.index[name]] @ self.up
                self.ground[name] = np.clip(1.0 - (h - h.min()) / GROUND_TOL, 0.0, 1.0)

    def pressure(self, points, taus):
        """The centre of pressure (F, 3, on the up = 0 plane through the world) where `points` ({foot_l,
        ball_l, foot_r, ball_r: (F, 3)}) put the feet at source times `taus`: per foot a heel point and a toe
        point, each loaded by its source contact at that phase (so a swinging foot never presses); None when
        no frame has a foot down. A frame between two steps takes the straight line between its neighbours."""
        frames = len(taus)
        num, den = np.zeros((frames, 3)), np.zeros(frames)
        flat = lambda p: np.asarray(p, float) - np.outer(np.asarray(p, float) @ self.up, self.up)
        for side in SIDES:
            ankle, ball = flat(points["foot_" + side]), flat(points["ball_" + side])
            heel, toe = ankle + HEEL_SHARE * (ankle - ball), ball + TOE_SHARE * (ball - ankle)
            g_heel = np.clip([float(periodic_cr(self.ground["foot_" + side], t)) for t in taus], 0.0, 1.0)
            g_toe = np.clip([float(periodic_cr(self.ground["ball_" + side], t)) for t in taus], 0.0, 1.0)
            load = np.maximum(g_heel, g_toe)
            point = (g_heel[:, None] * heel + g_toe[:, None] * toe) / np.maximum(g_heel + g_toe, 1e-9)[:, None]
            num += load[:, None] * point
            den += load
        known = den > 1e-6
        if not known.any():
            return None
        return _fill_periodic(num / np.maximum(den, 1e-9)[:, None], known)

    def _own_pendulum(self):
        """The source's CoM, its pressure and its pendulum against its travel line (fwd, side[, up]); how
        strongly its CoM follows the pendulum per axis (`follow`, fitted, clamped to FOLLOW_RANGE)."""
        if self.balance_note:
            return
        P = self.P
        cop = self.pressure(dict((n, self.pos[self.index[n]]) for n in self.ground), np.arange(P, dtype=float))
        if cop is None:
            self.balance_note = "no foot is ever on the ground: Balance needs a walk's contacts"
            return
        line = self.origin + np.outer(np.arange(P) / float(P), self.travel)
        self.s_dev = np.tensordot(self.mass, self.pdev, axes=(0, 0)) @ self.basis.T
        self.cop_dev = ((cop - line) @ self.basis.T)[:, :2]
        self.l_dev = pendulum(self.cop_dev, P / self.fps, self.s_dev[:, 2].mean())
        follow = []
        for axis in (0, 1):
            a = self.s_dev[:, axis] - self.s_dev[:, axis].mean()
            b = self.l_dev[:, axis] - self.l_dev[:, axis].mean()
            fit = float(np.dot(a, b) / np.dot(b, b)) if float(np.dot(b, b)) > 1e-12 else 1.0
            follow.append(min(max(fit, FOLLOW_RANGE[0]), FOLLOW_RANGE[1]))
        self.follow = np.array(follow)

    def _balance_target(self, times, ctx, bases):
        """Where the new cycle's centre of mass belongs, a frame (world, 0..n-1): its own (the knobs' walk,
        nothing carried) moved by Balance x [the pendulum's change (the new pressure and tempo against the
        source's) about its mean, x the walk's follow, forward x Exaggeration, sideways x Sway x Exaggeration;
        plus the mean's: the new pressure's mean change minus the CoM's own]."""
        k, b, n = ctx["k"], ctx["balance"], len(times) - 1
        worlds = np.swapaxes(np.array(bases), 0, 1)
        own = self.com(worlds)
        line = np.array([self.origin + ctx["travel2"] * phi for phi, _ in times[:-1]])
        m_dev = (own - line) @ self.basis.T
        taus = [tau for _, tau in times[:-1]]
        cop = self.pressure(dict((name, worlds[self.index[name], :, 3, :3]) for name in self.ground), taus)
        cop_dev = ((cop - line) @ self.basis.T)[:, :2]
        l_new = pendulum(cop_dev, n / self.fps, m_dev[:, 2].mean())
        l_src = np.array([periodic_cr(self.l_dev, tau) for tau in taus])
        gain = self.follow * np.array([ctx["ex"], k["sway"] * ctx["ex"]])
        swing = gain * ((l_new - l_new.mean(axis=0)) - (l_src - l_src.mean(axis=0)))
        mean = ((cop_dev.mean(axis=0) - self.cop_dev.mean(axis=0))
                - (m_dev[:, :2].mean(axis=0) - self.s_dev[:, :2].mean(axis=0)))
        delta = b * (swing + mean)
        return own + delta @ self.basis[:2], {"source_sway": float(np.ptp(self.s_dev[:, 1])),
                                              "mean": [float(v) for v in b * mean],
                                              "need": float(np.abs(delta).max())}

    def _com_joints(self):
        """The joints a centre of mass needs: every weighed joint and its ancestors."""
        if getattr(self, "_com_set", None) is None:
            need = set()
            for j in np.nonzero(self.mass)[0]:
                need.add(int(j))
                need.update(self._ancestors(int(j)))
            self._com_set = need
        return self._com_set

    def _carry_parts(self):
        """The CoM's joints a pelvis carry moves rigidly (the pelvis and the body over it, not the legs), and
        per leg (thigh, calf, foot, the CoM's joints under the foot)."""
        if getattr(self, "_parts", None) is None:
            only, pelvis = self._com_joints(), self.index["pelvis"]
            legs, in_legs = {}, set()
            for side in SIDES:
                th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
                below = [j for j in only if fo in self._ancestors(j)]
                legs[side] = (th, ca, fo, below)
                in_legs.update([th, ca, fo] + below)
            rigid = [j for j in only if j not in in_legs and (j == pelvis or pelvis in self._ancestors(j))]
            self._parts = (rigid, legs)
        return self._parts

    def _moved_com(self, base, tau, ctx, delta, cache):
        """The centre of mass of a base frame (J, 4, 4) with the pelvis moved by `delta` (world): the body over
        it moved rigidly, the legs re-solved to the same feet (exactly what the frame itself would give)."""
        rigid, legs = self._carry_parts()
        rots, poss = list(base[:, :3, :3]), list(base[:, 3, :3])
        for j in rigid:
            poss[j] = poss[j] + delta
        for side in SIDES:
            th, ca, fo, below = legs[side]
            before = poss[fo]
            self._leg(side, tau, rots, poss, ctx, cache)
            for j in below:
                poss[j] = poss[j] + (poss[fo] - before)
        return np.tensordot(self.mass, np.array(poss), axes=(0, 0))

    def _carry(self, times, ctx, bases, sink, target, start, caches):
        """The pelvis's horizontal carry a frame putting the frame's CoM on `target` (secant steps), the pelvis
        `sink` cm lower than in its base frame; from `start`. Returns the carry (n+1, 3), the last the first's."""
        flat = lambda v: v - np.dot(v, self.up) * self.up
        out = np.array(start, float)
        for f, (phi, tau) in enumerate(times[:-1]):
            s, down = out[f].copy(), -sink[f] * self.up
            com = self._moved_com(bases[f], tau, ctx, s + down, caches[f])
            miss, rate = flat(target[f] - com), 0.8
            for _ in range(CARRY_STEPS):
                if np.linalg.norm(miss) < CARRY_TOL:
                    break
                step = miss / rate
                s = s + step
                moved = self._moved_com(bases[f], tau, ctx, s + down, caches[f])
                rate = min(max(float(np.dot(flat(moved - com), step) / np.dot(step, step)), 0.2), 1.5)
                com, miss = moved, flat(target[f] - moved)
            out[f] = s
        out[-1] = out[0]
        return out

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
               "pose": pose if (pose and k["pose"] > 0.0) else None, "alpha": k["pose"],
               "balance": 0.0 if self.balance_note else k["balance"], "carry": None}
        ctx["width"] = k["width"] + (ctx["alpha"] * ctx["pose"]["width"] if ctx["pose"] and "width" in ctx["pose"] else 0.0)
        times = [(f / float(n), f * P / float(n)) for f in range(n + 1)]
        drop = self._lowering(times, ctx)
        balance = {"carry": 0.0, "residual": 0.0, "note": self.balance_note if k["balance"] > 0.0 else ""}
        if ctx["balance"] > 0.0:
            only = self._com_joints()
            bases = [self._frame(phi, tau, ctx, drop[f], None, only)[0] for f, (phi, tau) in enumerate(times[:-1])]
            target, said = self._balance_target(times, ctx, bases)
            need = said.pop("need")
            balance.update(said)
            caches, first, carry = [dict() for _ in bases], np.array(drop), np.zeros((n + 1, 3))
            for _ in range(BALANCE_ROUNDS if need >= CARRY_TOL else 0):   # nothing to carry at the defaults     # the carry, then the reach's drop with it, till the drop holds
                ctx["carry"] = carry = self._carry(times, ctx, bases, np.array(drop) - first, target, carry, caches)
                again = self._lowering(times, ctx)
                settled = float(np.abs(np.array(again) - np.array(drop)).max()) < CARRY_TOL
                drop = again
                if settled:
                    break
            balance["carry"] = float(np.linalg.norm(carry, axis=1).max()) if ctx["carry"] is not None else 0.0
        worlds = np.tile(np.eye(4), (len(self.names), n + 1, 1, 1))
        short, ctx["swing_in"] = 0.0, 0.0
        for f, (phi, tau) in enumerate(times):
            carry = None if ctx["carry"] is None else ctx["carry"][f]
            worlds[:, f], frame_short = self._frame(phi, tau, ctx, drop[f], carry)
            short = max(short, frame_short)
        if not self.balance_note:
            line = np.array([self.origin + ctx["travel2"] * phi for phi, _ in times[:-1]])
            dev = (self.com(worlds[:, :n]) - line) @ self.basis.T
            balance["sway"], balance["forward"] = float(np.ptp(dev[:, 1])), float(np.ptp(dev[:, 0]))
            balance["source_sway"] = float(np.ptp(self.s_dev[:, 1]))
            balance["follow"] = [float(v) for v in self.follow]
            if ctx["balance"] > 0.0:
                balance["residual"] = float(np.abs((self.com(worlds[:, :n]) - target) @ self.basis[:2].T).max())
        flat = ctx["travel2"] - np.dot(ctx["travel2"], self.up) * self.up
        info = {"frames": n, "stride_cm": float(np.linalg.norm(flat)) / 2.0,
                "speed": float(np.linalg.norm(flat)) / (n / self.fps) / 100.0, "lowered": float(max(drop)),
                "drop": [float(d) for d in drop], "short": short, "swing_in": ctx["swing_in"],
                "lag": ctx["lag"] * n / float(P), "knobs": k,
                "balance": balance}
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

    def _body(self, phi, tau, ctx, drop=0.0, carry=None):
        """The root's and the pelvis's new (rotation, position); the pelvis `drop` cm lower for the reach and
        `carry` (a world vector) along for the balance. Balance takes over the pelvis's forward swing from the
        stride: it scales by (1 - Balance) x Stride + Balance and the pendulum brings what the step changes."""
        k, ex = ctx["k"], ctx["ex"]
        line2 = self.origin + ctx["travel2"] * phi
        out = {}
        for name, mean in (("root", self.root_mean), ("pelvis", self.pelvis_mean)):
            j = self.index[name]
            dev = periodic_cr(self.pdev[j], tau) @ self.basis.T
            scale = k["stride"] if name == "root" else (1.0 - ctx["balance"]) * k["stride"] + ctx["balance"]
            along = mean[0] + scale * ex * (dev[0] - mean[0])
            aside = mean[1] + k["sway"] * ex * (dev[1] - mean[1])
            if name == "pelvis":
                pose, a = ctx["pose"], ctx["alpha"]
                v = float(periodic_cr(self.pdev[j], warp(phi, ctx["beta"], ctx["phi0"]) * self.P) @ self.up) - mean[2]
                base = mean[2] if pose is None or "height" not in pose else (1.0 - a) * mean[2] + a * pose["height"]
                height = base + k["bob"] * ex * shape_bob(v, k["weight"]) - drop
                centre = self.wmean[j] if pose is None or "pelvis" not in pose else toward(self.wmean[j], pose["pelvis"], a)
                rot = exp_rot(k["pelvis_rot"] * ex * periodic_cr(self.wlog[j], tau)) @ centre
            else:
                height, rot = dev[2], self.wrot(j, tau)
            out[name] = (rot, line2 + np.array([along, aside, height]) @ self.basis)
        if carry is not None:
            rot, pos = out["pelvis"]
            out["pelvis"] = (rot, pos + carry)
        return out

    def down(self, side, tau):
        """Whether the foot is on or near the ground at source time tau (its heel or toe within GROUND_TOL of
        its own lowest in the source)."""
        return max(float(periodic_cr(self.ground["foot_" + side], tau)),
                   float(periodic_cr(self.ground["ball_" + side], tau))) > 1e-6

    def _lowering(self, times, ctx):
        """The pelvis's drop on every frame (the last = the first): each frame needs the least drop that lets
        the legs whose feet are down reach without straightening past the source's straightest (a foot in the
        air that cannot reach passes closer to the body instead); the drop is a smooth periodic curve over those
        needs (smooth_cover), so a long stride sinks the contacts, not the whole cycle."""
        k = ctx["k"]
        need = np.zeros(len(times) - 1)
        for f, (phi, tau) in enumerate(times[:-1]):
            carry = None if ctx["carry"] is None else ctx["carry"][f]
            pelvis_rot, pelvis_pos = self._body(phi, tau, ctx, 0.0, carry)["pelvis"]
            for side in SIDES:
                if not self.down(side, tau):
                    continue
                th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
                hip = self.lt_at(th, tau) @ pelvis_rot + pelvis_pos
                ankle = self.foot_target(side, tau, k["stride"], ctx["width"], k["lift"] * ctx["ex"])[1]
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

    def _frame(self, phi, tau, ctx, drop=0.0, carry=None, only=None):
        """Every joint's new world at one frame (parents first, helpers last) - or only the joints in `only`
        (closed under their parents; the rest stay identity); and how far a foot that is down fell short (a
        foot in the air that cannot reach its path: ctx["swing_in"], the most it passes closer)."""
        k, ex = ctx["k"], ctx["ex"]
        rots, poss = [None] * len(self.names), [None] * len(self.names)
        body = self._body(phi, tau, ctx, drop, carry)
        gains = {"spine": k["spine"] * ex, "arm": k["arms"] * ex}
        short = 0.0
        for j in self.order:
            if rots[j] is not None or (only is not None and j not in only):
                continue
            kind, name, p = self.kind[j], self.names[j], self.parents[j]
            if kind in ("root", "pelvis"):
                rots[j], poss[j] = body[name]
            elif kind == "world":
                rots[j], poss[j] = self.wrot(j, tau), self.wpos(j, tau) + (ctx["travel2"] - self.travel) * phi
            elif kind == "leg":
                missed = self._leg(name[-1], tau, rots, poss, ctx)
                if self.down(name[-1], tau):
                    short = max(short, missed)
                else:
                    ctx["swing_in"] = max(ctx.get("swing_in", 0.0), missed)
            elif kind == "helper" and j in self.follows:
                b, rel = self.follows[j]
                pose = ctx["pose"]
                if pose is not None and j in pose.get("weapons", {}):     # the weapon where the pose holds it
                    rel = blend_matrix(rel, pose["weapons"][j], ctx["alpha"])
                m = rel @ matrix(rots[b], poss[b])
                rots[j], poss[j] = m[:3, :3], m[3, :3]
            else:
                t = tau - self.lag[j] * ctx["lag"]
                pose, a = ctx["pose"], ctx["alpha"]
                if kind == "head":
                    centre = self.wmean[j] if pose is None or "head" not in pose else toward(self.wmean[j], pose["head"], a)
                    rots[j] = exp_rot(k["head"] * ex * periodic_cr(self.wlog[j], t)) @ centre
                elif j in self.world_arms and (pose is None or "arms" not in pose):
                    # the upper arm hangs and swings in the world
                    rots[j] = exp_rot(k["arms"] * ex * periodic_cr(self.wlog[j], t)) @ self.wmean[j]
                else:
                    centre, gain = self.lmean[j], gains.get(kind, 1.0)
                    if pose is not None:
                        if j in pose.get("spine", {}):
                            centre = toward(centre, pose["spine"][j], a)
                        if "arms" in pose and kind in ("arm", "finger"):
                            # the pose's arms are HELD: they ride the chest, their swing fades with the pose
                            if j in pose["arms"]:
                                centre = toward(centre, pose["arms"][j], a)
                            gain *= 1.0 - a
                    rots[j] = exp_rot(gain * periodic_cr(self.llog[j], t)) @ centre @ rots[p]
                poss[j] = self.lt_at(j, t) @ rots[p] + poss[p]
        out = np.tile(np.eye(4), (len(self.names), 1, 1))
        for j in range(len(self.names)):
            if rots[j] is not None:
                out[j, :3, :3], out[j, 3, :3] = rots[j], poss[j]
        return out, short

    def _leg_source(self, side, tau, ctx):
        """What a leg's solve takes from the source and the knobs at tau - all of it independent of the hip."""
        k = ctx["k"]
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        foot_rot, ankle = self.foot_target(side, tau, k["stride"], ctx["width"], k["lift"] * ctx["ex"])
        if ctx["pose"] is not None and "toe" in ctx["pose"]:     # the pose's toe-out: the foot turned about up
            foot_rot = foot_rot @ exp_rot(self.up * ctx["alpha"] * ctx["pose"]["toe"][side])
        l1, l2 = float(np.linalg.norm(self.lt_at(ca, tau))), float(np.linalg.norm(self.lt_at(fo, tau)))
        h, kn, a = self.wpos(th, tau), self.wpos(ca, tau), self.wpos(fo, tau)
        e = _unit(a - h)
        bend = (kn - h) - np.dot(kn - h, e) * e
        bend = _unit(bend) if np.linalg.norm(bend) > 1e-6 else _unit(self.fwd - np.dot(self.fwd, e) * e)
        knee_bend = bend
        if ctx["pose"] is not None and "knee_turn" in ctx["pose"]:   # the pose's knee heading: turned about the leg
            knee_bend = turned_about(bend, -e, ctx["alpha"] * ctx["pose"]["knee_turn"][side])
        return {"joints": (th, ca, fo), "hip": self.lt_at(th, tau), "foot_rot": foot_rot, "ankle": ankle,
                "lengths": (l1, l2), "dirs": (_unit(kn - h), _unit(a - kn)), "normal": _unit(np.cross(e, bend)),
                "bend": knee_bend, "wrot": (self.wrot(th, tau), self.wrot(ca, tau))}

    def _leg(self, side, tau, rots, poss, ctx, cache=None):
        """Thigh, calf and foot by IK from the new hip to the new foot; each bone turned by the rotation
        taking its source (direction, leg plane) onto the new one. Returns how far the foot fell short.
        `cache` ({side: _leg_source}) spares the source half when only the hip moves."""
        src = None if cache is None else cache.get(side)
        if src is None:
            src = self._leg_source(side, tau, ctx)
            if cache is not None:
                cache[side] = src
        th, ca, fo = src["joints"]
        pelvis = self.parents[th]
        hip = src["hip"] @ rots[pelvis] + poss[pelvis]
        knee, reached, short = two_bone(hip, src["ankle"], src["lengths"][0], src["lengths"][1], src["bend"],
                                        self.reach[side])
        e2 = _unit(reached - hip)
        bend2 = _unit((knee - hip) - np.dot(knee - hip, e2) * e2)
        n_new = _unit(np.cross(e2, bend2))
        rots[th] = src["wrot"][0] @ align(src["dirs"][0], src["normal"], _unit(knee - hip), n_new)
        rots[ca] = src["wrot"][1] @ align(src["dirs"][1], src["normal"], _unit(reached - knee), n_new)
        rots[fo] = src["foot_rot"]
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
    if info.get("swing_in", 0.0) > 0.5:
        text += " | the swinging foot passes up to %.1f cm nearer the body" % info["swing_in"]
    return text + balance_line(info)


def balance_line(info):
    """What Balance did, for a status line ("" when nothing worth saying)."""
    balance = info.get("balance") or {}
    if balance.get("note"):
        return " | no balance: " + balance["note"]
    if balance.get("carry", 0.0) > 0.1:
        return (" | balance: the pelvis carried up to %.1f cm over the feet (the CoM sways %.1f cm, the source's "
                "%.1f)" % (balance["carry"], balance.get("sway", 0.0), balance.get("source_sway", 0.0)))
    return ""
