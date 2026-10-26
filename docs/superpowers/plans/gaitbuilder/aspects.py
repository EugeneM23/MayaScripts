"""aspects - Gait Builder's aspects: a walk cycle measured in units (cm, degrees, %, m/s), the knob table, and the
animator's units turned into the model's knobs. numpy only.

An aspect is one measurable feature of a gait: the bob in cm, the hip twist in degrees, the share of a cycle a
foot is down. `measure` reads them off any closed cycle the same way - the clip, and the result - so every knob
reads back. Design: docs/superpowers/specs/2026-10-26-gait-builder-design.md.
"""
import math

import numpy as np

SIDES = ("l", "r")
CONTACT_H = 0.02          # x the leg: a heel or ball this near its own lowest...
CONTACT_SLOW = 0.35       # ...and moving slower than this share of the body's travel a frame is down
BEND_ZERO = 1e-9


def _unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n > 1e-12, n, 1.0)


def harmonic(y, phase, order):
    """(amplitude, phase) of the series `y` on cos / sin(order . phase): its least-squares fit, demeaned.
    `phase` (radians, 2 pi a stride) one per sample."""
    y = np.asarray(y, float) - float(np.mean(y))
    c, s = np.cos(order * phase), np.sin(order * phase)
    c, s = c - c.mean(), s - s.mean()
    a = np.array([[c @ c, c @ s], [c @ s, s @ s]])
    if abs(np.linalg.det(a)) < 1e-12:
        return 0.0, 0.0
    x = np.linalg.solve(a, np.array([c @ y, s @ y]))
    return float(math.hypot(x[0], x[1])), float(math.atan2(x[1], x[0]))


class Cycle(object):
    """A closed cycle laid on a walk's strides: world matrices (J, n+1, 4, 4) of `walk`'s joints, sample f at
    the walk's source time f . P / n."""

    def __init__(self, walk, worlds):
        self.walk = walk
        self.worlds = np.asarray(worlds, float)
        self.n = n = self.worlds.shape[1] - 1
        self.pos = self.worlds[:, :n, 3, :3]
        self.rot = self.worlds[:, :n, :3, :3]
        root = walk.index["root"]
        self.travel = self.worlds[root, n, 3, :3] - self.worlds[root, 0, 3, :3]
        t = np.arange(n) / float(n)
        line = self.worlds[root, 0, 3, :3][None] + np.outer(t, self.travel)
        self.dev = self.pos - line[None]                      # every joint against the root's straight line
        self.phase = np.array([walk.stride_phase(f * walk.P / float(n)) for f in range(n)])
        up = np.asarray(walk.up, float)
        self.up, self.ahead, self.lside = up, np.asarray(walk.ahead, float), np.asarray(walk.lside, float)
        flat = self.travel - float(self.travel @ up) * up
        self.flat = float(np.linalg.norm(flat))
        self.seconds = n / float(walk.fps)

    def p(self, name):
        return self.pos[self.walk.index[name]]

    def has(self, *names):
        return all(name in self.walk.index for name in names)

    def down(self, side):
        """(n,) bool: the foot is on the ground - its heel (the ankle) or its ball near its LOCAL lowest (within
        half a stride either side: a walk's stances may stand at different heights, dw's 2-3 cm apart) and slow."""
        leg = self.walk.leg_length
        speed = self.flat / self.n
        n = self.n
        half = max(1, int(round(n / (2.0 * self.walk.strides) / 2.0)))
        out = np.zeros(n, bool)
        for name in ("foot_" + side, "ball_" + side):
            p = self.worlds[self.walk.index[name], :, 3, :3]
            h = p[:n] @ self.up
            low = np.array([min(h[(f + d) % n] for d in range(-half, half + 1)) for f in range(n)])
            step = p[1:] - p[:-1]
            step = step - np.outer(step @ self.up, self.up)
            slow = np.linalg.norm(step, axis=1) < max(CONTACT_SLOW * speed, 0.01 * leg)
            out |= (h < low + CONTACT_H * leg) & slow
        return out


def _knee_bend(c, side):
    """(n,) the knee's bend, degrees (0 straight)."""
    h, k, a = c.p("thigh_" + side), c.p("calf_" + side), c.p("foot_" + side)
    u, v = _unit(k - h), _unit(a - k)
    return np.degrees(np.arccos(np.clip(np.sum(u * v, axis=1), -1.0, 1.0)))


def _arm(c, side):
    """(forward angle, out angle, elbow bend) series of an arm (degrees): the upper arm's direction forward of
    hanging and out to its side, the bend between it and the forearm."""
    sign = 1.0 if side == "l" else -1.0
    a = _unit(c.p("lowerarm_" + side) - c.p("upperarm_" + side))
    b = _unit(c.p("hand_" + side) - c.p("lowerarm_" + side))
    fwd = np.degrees(np.arctan2(a @ c.ahead, -(a @ c.up)))
    out = np.degrees(np.arcsin(np.clip(a @ (sign * c.lside), -1.0, 1.0)))     # out of the body's front plane
    bend = np.degrees(np.arccos(np.clip(np.sum(a * b, axis=1), -1.0, 1.0)))
    return fwd, out, bend


def _pitch_series(c, j):
    """(n,) a joint's world turn about the body's side axis against its mean, radians (forward down +)."""
    r = c.rot[j]
    mean = _mean_rot(r)
    rel = r @ mean.T
    w = _log_rot(rel)
    return w @ c.lside


def _mean_rot(rs):
    u, _, vt = np.linalg.svd(np.sum(rs, axis=0))
    m = u @ vt
    if np.linalg.det(m) < 0:
        u[:, -1] *= -1.0
        m = u @ vt
    return m


def _log_rot(r):
    """rotation vectors of row-vector rotations (..., 3, 3) (the fork's convention: exp_rot(w) turns v . R)"""
    c = np.swapaxes(r, -1, -2)
    th = np.arccos(np.clip((np.trace(c, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0))
    v = np.stack([c[..., 2, 1] - c[..., 1, 2], c[..., 0, 2] - c[..., 2, 0], c[..., 1, 0] - c[..., 0, 1]], -1)
    s = np.sin(th)
    k = np.where(s > 1e-7, th / (2.0 * np.where(s > 1e-7, s, 1.0)), 0.5)
    return v * k[..., None]


def measure(walk, worlds):
    """The cycle `worlds` (J, n+1, 4, 4) of `walk`'s skeleton in units - see the module's knob table:
    speed m/s, step cm, cadence steps/min, duty %, bob / sway / surge cm, hips / hip_drop / lean / chest_twist /
    chest_sway / chest_bounce deg, width cm, and per side ({"l", "r"}) arm_swing / arms_forward / arm_out /
    elbow / elbow_swing / toe_out deg, lift / swing_out cm, knee_bend deg."""
    c = Cycle(walk, worlds)
    idx = walk.index
    out = {"speed": c.flat / c.seconds / 100.0, "step": c.flat / (2.0 * walk.strides),
           "cadence": 2.0 * walk.strides / c.seconds * 60.0}
    downs = dict((s, c.down(s)) for s in SIDES)
    out["duty"] = 100.0 * float(np.mean([downs[s].mean() for s in SIDES]))
    # the pelvis against the travel line, in the body's frame
    pel = c.dev[idx["pelvis"]]
    out["bob"] = harmonic(pel @ c.up, c.phase, 2)[0]
    out["sway"] = harmonic(pel @ c.lside, c.phase, 1)[0]
    out["surge"] = harmonic(pel @ c.ahead, c.phase, 2)[0]
    twist, drop = walk.pelvis_fit(c.worlds)
    out["hips"], out["hip_drop"] = twist, drop
    if getattr(walk, "chest_shape", None) is not None:
        out["chest_twist"], out["chest_sway"] = walk.chest_fit(c.worlds)
    else:
        out["chest_twist"] = out["chest_sway"] = 0.0
    spine = [n for n in ("spine_05", "spine_04", "spine_03", "spine_02") if n in idx]
    top = spine[0] if spine else "pelvis"
    out["chest_bounce"] = math.degrees(harmonic(_pitch_series(c, idx[top]), c.phase, 2)[0])
    neck = "neck_01" if "neck_01" in idx else top
    trunk = c.p(neck) - c.p("pelvis")
    out["lean"] = float(np.degrees(np.arctan2(trunk @ c.ahead, trunk @ c.up)).mean())
    # the feet
    mids = {}
    for s in SIDES:
        down = downs[s]
        ank = c.dev[idx["foot_" + s]]
        rest = ank[down] if down.any() else ank
        mids[s] = float((rest @ c.lside).mean())
    out["width"] = mids["l"] - mids["r"]
    for key in ("arm_swing", "arms_forward", "arm_out", "elbow", "elbow_swing", "toe_out", "lift", "swing_out",
                "knee_bend"):
        out[key] = {}
    for s in SIDES:
        sign = 1.0 if s == "l" else -1.0
        down = downs[s]
        ank = c.dev[idx["foot_" + s]]
        h = ank @ c.up
        ground = float(h[down].mean()) if down.any() else float(h.min())
        out["lift"][s] = float(h[~down].max() - ground) if (~down).any() else 0.0
        toe = c.p("ball_" + s) - c.p("foot_" + s)
        toe = toe - np.outer(toe @ c.up, c.up)
        yaw = np.degrees(np.arctan2(toe @ (sign * c.lside), toe @ c.ahead))
        out["toe_out"][s] = float(yaw[down].mean()) if down.any() else float(yaw.mean())
        out["swing_out"][s] = _swing_bow(c, ank, down, sign)
        bend = _knee_bend(c, s)
        out["knee_bend"][s] = float(bend[down].min()) if down.any() else float(bend.min())
        if c.has("upperarm_" + s, "lowerarm_" + s, "hand_" + s):
            fwd, side_out, bend_a = _arm(c, s)
            out["arm_swing"][s] = harmonic(fwd, c.phase, 1)[0]
            out["arms_forward"][s] = float(fwd.mean())
            out["arm_out"][s] = float(side_out.mean())
            out["elbow"][s] = float(bend_a.mean())
            out["elbow_swing"][s] = harmonic(bend_a, c.phase, 1)[0]
    return out


def _swing_bow(c, ank, down, sign):
    """The swinging ankle's bow out to its side (+) at mid-flight against the straight line between where it
    leaves the ground and where it lands, cm - the longest flight's."""
    n = c.n
    runs, start = [], None
    for i in range(2 * n):
        if not down[i % n] and start is None:
            start = i
        if down[i % n] and start is not None:
            if start < n:
                runs.append((start, i - start))
            start = None
    if not runs:
        return 0.0
    s0, length = max(runs, key=lambda r: r[1])
    a = ank[(s0 - 1) % n]
    b = ank[(s0 + length) % n]
    mid = ank[(s0 + length // 2) % n]
    t = (length // 2 + 1) / float(length + 1)
    line = a + (b - a) * t
    return float((mid - line) @ (sign * c.lside))
