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

    def margin(self, side):
        """(n,) how far the foot is inside "on the ground" (> 0 down): its heel (the ankle) or its ball near its
        LOCAL lowest (within half a stride either side: a walk's stances may stand at different heights, dw's
        2-3 cm apart) and slow - each test's margin over its own threshold, the point down if both hold."""
        leg = self.walk.leg_length
        speed = self.flat / self.n
        n = self.n
        half = max(1, int(round(n / (2.0 * self.walk.strides) / 2.0)))
        tol, slow_at = CONTACT_H * leg, max(CONTACT_SLOW * speed, 0.01 * leg)
        out = np.full(n, -1e9)
        for name in ("foot_" + side, "ball_" + side):
            p = self.worlds[self.walk.index[name], :, 3, :3]
            h = p[:n] @ self.up
            low = np.array([min(h[(f + d) % n] for d in range(-half, half + 1)) for f in range(n)])
            step = p[1:] - p[:-1]
            step = step - np.outer(step @ self.up, self.up)
            high = (low + tol - h) / tol
            slow = (slow_at - np.linalg.norm(step, axis=1)) / slow_at
            out = np.maximum(out, np.minimum(high, slow))
        return out

    def down(self, side):
        """(n,) bool: the foot is on the ground (margin > 0)."""
        return self.margin(side) > 0.0

    def down_share(self, side):
        """The share of the cycle the foot is down, to a fraction of a frame: a frame counts whole, less or more
        where its margin crosses 0 between it and the next (a run of 26 frames is 3.8 % a frame)."""
        m = self.margin(side)
        n = self.n
        d = m > 0.0
        total = float(d.sum())
        for f in range(n):
            g = (f + 1) % n
            if d[f] != d[g]:
                x = float(m[f] / (m[f] - m[g]))          # the crossing, between f (0) and the next (1)
                total += (x - 0.5) if d[f] else (0.5 - x)
        return total / n


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
    """(n,) a joint's world turn about the body's side axis against its mean, radians (forward down +). In the
    WORLD: r = mean . E (row vectors, E applied after the mean), so E = mean^T . r; `r . mean^T` is the turn in
    the mean's own axes, and on a UE spine joint (its axes far from the world's) a pitch then read ~0."""
    r = c.rot[j]
    mean = _mean_rot(r)
    rel = mean.T @ r
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
    out["duty"] = 100.0 * float(np.mean([c.down_share(s) for s in SIDES]))
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


def _flights(down):
    """(start, length) of each run of frames the foot is up, the cycle wrapped (a run over the end starts in
    the cycle and runs past n)."""
    n = len(down)
    runs, start = [], None
    for i in range(2 * n):
        if not down[i % n] and start is None:
            start = i
        if down[i % n] and start is not None:
            if start < n:
                runs.append((start, i - start))
            start = None
    return runs


def lift_scale(profile, change):
    """The model's lift L that raises the swing's highest point `change` cm (gaitmodel.Walk.lift_profile: each
    swinging frame's height h over the ground and its lift_up over the take-off / landing line, the frame at
    h + (L - 1) . lift_up): max over the swing is convex in L and grows with it where the peak's lift_up > 0 -
    bisected."""
    if not profile or abs(change) < 1e-9:
        return 1.0
    h = np.array([p[0] for p in profile])
    over = np.array([p[1] for p in profile])
    top = float(h.max())
    asked = top + change

    def at(L):
        return float((h + (L - 1.0) * over).max())
    if change > 0.0:
        lo, hi = 1.0, 2.0
        while at(hi) < asked and hi < 64.0:
            lo, hi = hi, 2.0 * hi
    else:
        if at(0.0) > asked:
            return 0.0                               # lower than the flattest swing: as flat as it goes
        lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if at(mid) < asked:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _swing_bow(c, ank, down, sign):
    """The swinging ankle's bow out to its side (+) at mid-flight against the straight line between where it
    leaves the ground and where it lands, cm - the longest flight's."""
    n = c.n
    runs = _flights(down)
    if not runs:
        return 0.0
    s0, length = max(runs, key=lambda r: r[1])
    a = ank[(s0 - 1) % n]
    b = ank[(s0 + length) % n]
    mid = ank[(s0 + length // 2) % n]
    t = (length // 2 + 1) / float(length + 1)
    line = a + (b - a) * t
    return float((mid - line) @ (sign * c.lside))


# ---- the knobs ----

class Knob(object):
    """One knob of the window. `kind`: "measured" (its default is the walk's own value, `measure`'s key `key`),
    "added" (a fixed default: a change the walk itself does not measure), "toggle" (on / off). `rule(base, L)`
    answers its range (low, high) from the walk's measured values and its leg length. `sided`: Both / Left /
    Right, the measured value one a side."""

    def __init__(self, name, group, label, unit, kind, default=None, rule=None, sided=False, key=None, tip=""):
        self.name, self.group, self.label, self.unit, self.kind = name, group, label, unit, kind
        self.default, self.rule, self.sided, self.key, self.tip = default, rule, sided, key or name, tip


def _around(low_share, high_share, floor=None, ceil=None):
    """A range as shares of the walk's own value (`floor` / `ceil`: at least this wide)."""
    def rule(b, L):
        lo, hi = b * low_share, b * high_share
        if floor is not None:
            lo = min(lo, floor)
        if ceil is not None:
            hi = max(hi, ceil)
        return lo, hi
    return rule


def _offset(below, above, lo_cap=None, hi_cap=None):
    """A range about the walk's own value: `below` under it to `above` over it (held within the caps)."""
    def rule(b, L):
        lo, hi = b - below, b + above
        if lo_cap is not None:
            lo = max(lo, lo_cap)
        if hi_cap is not None:
            hi = min(hi, hi_cap)
        return lo, hi
    return rule


def _fixed(lo, hi):
    return lambda b, L: (lo, hi)


MAIN = "Main"
KNOBS = (
    Knob("speed", MAIN, "Speed", "m/s", "measured", rule=_around(0.4, 2.0),
         tip="The walk's speed: step length and cadence grow together, keeping the walk's own ratio of the two; "
             "past the longest step the cadence grows alone"),
    Knob("step", MAIN, "Step length", "cm", "measured", rule=_around(0.5, 1.6),
         tip="One step's length at the same cadence (the speed follows)"),
    Knob("duty", MAIN, "Ground time", "%", "measured", rule=lambda b, L: (max(15.0, 0.7 * b), min(85.0, 1.45 * b)),
         tip="How much of a cycle each foot is on the ground; under 50 % both feet leave it at once - a run"),
    Knob("weight", MAIN, "Weight", "", "added", 0.0, _fixed(-1.0, 1.0),
         tip="Light (-1) to heavy (+1): a deeper bob and lower body, the knees bent on the load, a slower strike"),
    Knob("bob", MAIN, "Bounce", "cm", "measured", rule=lambda b, L: (0.0, max(3.0 * b, 0.08 * L)),
         tip="The pelvis's bob, up and down twice a stride"),
    Knob("hips", MAIN, "Hips", "deg", "measured", rule=lambda b, L: (min(-5.0, b - 5.0), max(25.0, 2.5 * abs(b))),
         tip="The pelvis's twist each way with the legs (at the walk's own step; it grows with the step); the hip "
             "drop follows it as the walk has them"),
    Knob("lean", MAIN, "Lean", "deg", "measured", rule=_offset(30.0, 30.0, -25.0, 75.0),
         tip="The trunk forward (+) over the hips; the head keeps its gaze"),
    Knob("arm_swing", MAIN, "Arm swing", "deg", "measured", sided=True,
         rule=lambda b, L: (0.0, max(80.0, 2.0 * b)), tip="The upper arms' swing each way"),
    Knob("width", MAIN, "Width", "cm", "measured", rule=lambda b, L: (0.0, max(3.0 * b, 0.4 * L)),
         tip="How far apart the feet stand on the ground"),
    Knob("lift", MAIN, "Foot lift", "cm", "measured", sided=True, rule=lambda b, L: (0.2 * b, max(3.0 * b, 0.3 * L)),
         tip="How high the swinging foot rises over its path"),
    Knob("energy", MAIN, "Energy", "%", "added", 100.0, _fixed(0.0, 200.0),
         tip="Every motion about the walk's mean pose: 0 stands still, 200 doubles it"),
    # the pelvis
    Knob("height", "Pelvis", "Height", "cm", "added", 0.0, _fixed(-40.0, 40.0),
         tip="The pelvis raised (+) or lowered (-) over the feet; the legs never straighten past the walk's own"),
    Knob("forward", "Pelvis", "Forward", "cm", "added", 0.0, _fixed(-30.0, 30.0),
         tip="The hips ahead of (+) or behind (-) the feet, the body over them going with them"),
    Knob("sway", "Pelvis", "Sway", "cm", "measured", rule=lambda b, L: (0.0, max(3.0 * b, 0.12 * L)),
         tip="The pelvis side to side, once a stride"),
    Knob("surge", "Pelvis", "Surge", "cm", "measured", rule=lambda b, L: (0.0, max(3.0 * b, 0.08 * L)),
         tip="The pelvis forward and back as it walks, twice a stride"),
    Knob("hip_drop", "Pelvis", "Hip drop", "deg", "measured", rule=_fixed(-5.0, 15.0),
         tip="The standing leg's hip up and the swinging leg's down, each way"),
    Knob("root_line", "Pelvis", "Root on line", "", "toggle", 1.0,
         tip="On: the root runs straight down the walk's line (a game's capsule); off: it weaves with the hips"),
    Knob("in_place", "Pelvis", "In place", "", "toggle", 0.0,
         tip="On: the walk on the spot - the root stays where the first frame has it, the planted feet slide back"),
    # the legs and feet
    Knob("toe_out", "Legs", "Toe out", "deg", "measured", sided=True, rule=_offset(30.0, 40.0),
         tip="The planted foot turned out (+) or in (-)"),
    Knob("swing_out", "Legs", "Swing out", "cm", "measured", sided=True, rule=_offset(20.0, 30.0),
         tip="The swinging foot's path bowed out to its side (+) or in mid-flight"),
    Knob("knee_bend", "Legs", "Knee bend on stance", "deg", "measured", sided=True,
         rule=lambda b, L: (b, max(b + 1.0, 70.0)),
         tip="A planted knee is never straighter than this: the pelvis sinks where it would be (and a knee held "
             "off straight never clicks); the walk's own straightest is the least"),
    Knob("foot_lag", "Legs", "Foot lag", "fr", "added", 0.0, _fixed(0.0, 6.0), sided=True,
         tip="Frames the swinging foot trails its shin: it flicks through after it leaves the ground"),
    Knob("ankle_flex", "Legs", "Ankle flex", "%", "added", 100.0, _fixed(0.0, 300.0), sided=True,
         tip="How far the swinging foot turns in its ankle, against the walk's own"),
    # the trunk and the head
    Knob("chest_twist", "Trunk", "Chest twist", "deg", "measured", rule=lambda b, L: (0.0, max(40.0, 2.5 * b)),
         tip="The shoulders turn each way against the hips (at the walk's own step; it grows with the step)"),
    Knob("chest_sway", "Trunk", "Chest sway", "deg", "measured", rule=lambda b, L: (0.0, max(15.0, 2.5 * b)),
         tip="The shoulder line tilts each way over the steps"),
    Knob("chest_bounce", "Trunk", "Chest bounce", "deg", "measured", rule=lambda b, L: (0.0, max(10.0, 3.0 * b)),
         tip="The chest pitches forward and back twice a stride"),
    Knob("head_steady", "Trunk", "Head steady", "%", "added", 0.0, _fixed(0.0, 100.0),
         tip="0: the head moves as in the walk; 100: its gaze held still in the world"),
    Knob("nod", "Trunk", "Nod", "deg", "added", 0.0, _fixed(-30.0, 30.0), tip="The head forward (+) or back"),
    # the arms
    Knob("elbow", "Arms", "Elbow", "deg", "measured", sided=True, rule=_offset(30.0, 90.0, 0.0, 150.0),
         tip="The elbows' bend"),
    Knob("elbow_swing", "Arms", "Elbow swing", "deg", "measured", sided=True,
         rule=lambda b, L: (0.0, max(30.0, 2.5 * b)), tip="The elbows' bend swinging with the arm"),
    Knob("arms_forward", "Arms", "Arms forward", "deg", "measured", sided=True, rule=_offset(40.0, 40.0),
         tip="The upper arms held forward (+) or back"),
    Knob("arm_out", "Arms", "Arm out", "deg", "measured", sided=True, rule=_offset(20.0, 40.0),
         tip="The upper arms held out to their sides"),
    Knob("shoulders", "Arms", "Shoulders", "deg", "added", 0.0, _fixed(-20.0, 25.0), sided=True,
         tip="The shoulders raised (+) or dropped"),
    # the helpers
    Knob("placement", "Physics", "Foot placement", "", "toggle", 1.0,
         tip="On: a planted foot never slides and one foot is always down (a walk); off: the walk's own feet"),
    Knob("balance", "Physics", "Balance", "%", "added", 100.0, _fixed(0.0, 100.0),
         tip="The centre of mass carried over the feet as the steps and the pose change"),
    Knob("follow", "Physics", "Follow-through", "fr", "added", 1.5, _fixed(0.0, 4.0),
         tip="The trunk, the head and the arms follow the body with weight, about this many frames late"),
    Knob("whip", "Physics", "Whip", "", "added", 0.3, _fixed(0.0, 0.6),
         tip="How far they overshoot as they catch up: 0 settles, 0.6 whips through"),
)
BY_NAME = dict((k.name, k) for k in KNOBS)
GROUPS = []
for _knob in KNOBS:
    if _knob.group not in GROUPS:
        GROUPS.append(_knob.group)
# Weight +1 sinks the pelvis into each step (the model's weight_dip, a share of the leg x the model's weight); it
# used to raise a planted knee's straightest by 6-12 deg - Knee bend's own mechanism: 0.86 on dw at 12, 0.99 on asd
# under the goblin at 6 (a crouch has little bob of its own, so the knees were all Weight did)
WEIGHT_DIP = 0.01          # of the leg x the model weight: Weight +1 (2.0) sinks the pelvis 2 % of the leg, swept 1-3 % (2026-10-26)
WEIGHT_GAIN = 2.0         # the model's weight at Weight +1 (1.5 moved dw's and the CAT walk's legs 4 deg: unseen)
HEAD_DRAG = 4.0 / 3.0     # the head's spring x Follow-through (Walk Builder's 2.0 over 1.5)
TORSO_WHIP = 2.0 / 3.0    # the trunk's bounce x Whip (Walk Builder's 0.2 over 0.3)
# A leg straightened past the source eases into its limit from this share below it (the model's knee_soft): a
# corner at the limit is a knee click - a grown lift-off, a long step's swing, the pelvis's cover (asd step high
# 27.8 deg/frame^2, duty low 20.8 -> 3.5, lift high 19.5 -> 2.9)
KNEE_SOFT = 0.04


def base_engine(walk):
    """The model's knobs that give the walk as it is, the helpers on: Walk Builder's defaults with the walk's own
    hip twist and drop and chest twist and sway (Walk Builder's defaults set them to people's)."""
    out = {"pelvis_twist": walk.own_twist, "pelvis_list": walk.own_list, "knee_soft": KNEE_SOFT,
           "weight_dip": WEIGHT_DIP}
    if getattr(walk, "chest_shape", None) is not None:
        out["chest_twist"], out["chest_sway"] = walk.own_chest_twist, walk.own_chest_sway
    return out


def defaults(base):
    """{knob: value} of a walk whose measure (at base_engine) is `base`: a measured knob its value (a sided one
    {"l", "r"}), the rest their defaults."""
    out = {}
    for k in KNOBS:
        if k.kind == "measured":
            v = base[k.key]
            out[k.name] = dict(v) if isinstance(v, dict) else v
        else:
            out[k.name] = k.default
    return out


def ranges(base, leg):
    """{knob: (low, high)} for the walk measured `base` (a sided knob's range from its two sides' mean)."""
    out = {}
    for k in KNOBS:
        if k.kind == "toggle":
            out[k.name] = (0.0, 1.0)
            continue
        b = base.get(k.key, k.default) if k.kind == "measured" else k.default
        if isinstance(b, dict):
            b = 0.5 * (b["l"] + b["r"])
        out[k.name] = k.rule(b, leg)
    # an elbow swings at most as far as it is bent: past it the bend folds back through straight (an angle is
    # unsigned) and the swing reads less, not more
    bend = base.get("elbow") or {}
    if bend and "elbow_swing" in out:
        lo, hi = out["elbow_swing"]
        own = max((base.get("elbow_swing") or {"": 0.0}).values())
        out["elbow_swing"] = (lo, max(lo + 1.0, own, min(hi, min(bend.values()))))
    # a calibrated knob's range cut to what the walk reaches (a walk's duty above Foot placement's double support,
    # a run's elbow swing that the springs keep)
    for group in CALIBRATED:
        for name in group:
            got = reach(base, name)
            if got is None or got[1] - got[0] < REACH_MIN:
                continue
            k = BY_NAME[name]
            own = base[k.key]
            own = 0.5 * (own["l"] + own["r"]) if isinstance(own, dict) else own
            lo, hi = out[name]
            lo, hi = max(lo, own + got[0]), min(hi, own + got[1])
            if hi - lo > REACH_MIN:
                out[name] = (lo, hi)
    # a step and a ground time the legs reach without a lunge (DROP_MAX of the leg down), never under a tenth past
    # the walk's own: a walk already crouched keeps a little room
    for name in DROP_CUT:
        points = base.get("_curve", {}).get("_drop_" + name, {}).get("")
        if not points or name not in out:
            continue
        top = drop_top(points, DROP_MAX * leg)
        if top is None:
            continue
        own = base[BY_NAME[name].key]
        lo, hi = out[name]
        out[name] = (lo, max(min(hi, own + top), min(hi, own + 0.1 * abs(own))))
    return out


def value(gait, base, name, side=None):
    """The asked value of knob `name` (a side's own, else the knob's for both, else the walk's own)."""
    k = BY_NAME[name]
    if side and k.sided:
        if name + "_" + side in gait:
            return float(gait[name + "_" + side])
        if name in gait and not isinstance(gait[name], dict):
            return float(gait[name])
    elif name in gait and not isinstance(gait[name], dict):
        return float(gait[name])
    if k.kind == "measured":
        b = base[k.key]
        return float(b[side]) if isinstance(b, dict) else float(b)
    return float(k.default)


def speed_law(base, speed, step_range=None):
    """(step cm, cadence steps/min) for `speed` m/s keeping the walk's own walk ratio (step over cadence): both
    grow as the root of the speed; past the step's range the cadence takes the rest."""
    ratio = base["step"] / base["cadence"]
    product = 6000.0 * speed                       # cm a minute
    step = math.sqrt(product * ratio)
    if step_range is not None:
        step = min(max(step, step_range[0]), step_range[1])
    return step, product / step


def timing(gait, base):
    """(step cm, cadence steps/min) asked: Speed sets both by the law (unless Step length is also asked, then
    the cadence carries the speed), Step length alone keeps the cadence."""
    step_range = BY_NAME["step"].rule(base["step"], 0.0)
    if "speed" in gait:
        if "step" in gait:
            step = float(gait["step"])
            return step, 6000.0 * float(gait["speed"]) / step
        return speed_law(base, float(gait["speed"]), step_range)
    return float(gait.get("step", base["step"])), base["cadence"]


# The knobs whose engine change does not give their unit 1:1 on a walk, so each walk is probed once out to its
# range's ends and each knob's response kept as a curve (asked change -> measured change): Ground time (Walk
# Builder's ground_time lengthens a contact by its own length, capped by its swing's room; a walk's duty cannot
# fall below what Foot placement's double support leaves - asd's 53 %), Knee bend (the pelvis's cover), Elbow and
# Elbow swing (the arms' springs: a run's elbow swing barely shrinks, HavyRun), Bounce (the legs' reach). The asked change goes through the
# curve's inverse, and the range is cut to what the walk reaches. Probes in groups whose parts do not touch each
# other (the legs' timing with the arms' swing, the stance with the arms' mean).
CALIBRATED = (("duty", "elbow_swing"), ("knee_bend", "elbow"), ("bob",))
PROBES = (-1.0, -0.35, 0.35, 1.0)    # shares of the way from the walk's own value to the range's end
# Knee bend's response is steep near the walk's own: a toe-off knee 20 deg from straight bends 7 deg more for 0.6 cm
# more of the pelvis's drop (dw; a knee near straight is the root of its reach) - a small probe first
KNOB_PROBES = {"knee_bend": (0.12, 0.35, 1.0),
               # Bounce up is held by the legs' soft reach at the stance's ends (a run's push-off: HavyRun read 2.65
               # of +4.22 cm once the planted legs stop at the soft limit's start); down is free
               "bob": (-1.0, 0.35, 1.0)}
REACH_MIN = 1e-3                     # a reach this small each way: the knob is left its range (nothing to cut to)
# A step or a ground time the legs take only by sinking the pelvis far is a lunge, and its swinging knee snaps (the
# hip falls 4 cm a frame at the contact: asd at 1.4 legs a step, 19 cm down, 14 deg/frame^2; dw at 1.2, 30 cm, 21;
# asd's top Ground time 75 cm down): their ranges stop where the pelvis is down this share of the leg, probed
DROP_MAX = 0.15
DROP_CUT = ("step", "duty", "speed")    # (a walk at twice its speed: asd 3.4 m/s, 19 cm down, 26 deg/frame^2)
DROP_PROBES = ("step", "speed")      # probed for it here (Ground time's drop comes with its own probes)
STEP_PROBES = (0.5, 1.0)             # shares of the way from the walk's own value to the rule's top


def _own(base, name, side):
    v = base[BY_NAME[name].key]
    return float(v[side]) if isinstance(v, dict) else float(v)


def annotate(walk, base, result):
    """What the knobs need of the model's own evaluation of the walk (`result`, at base_engine) beside the base's
    measure: each planted knee's straightest over the frames the MODEL holds planted (the lock's window, wider
    than measure's "down": a run's push-off) - Knee bend caps from there, so asking just past the walk's own
    changes the knee a little, not by the push-off frame's 5-7 deg at once (HavyRun's left)."""
    planted = ((result.info.get("placement") or {}).get("planted") or {})
    c = Cycle(walk, result.worlds)
    own = {}
    for s in SIDES:
        mask = np.array(planted.get(s) or [], bool)
        if len(mask) != c.n or not mask.any():
            continue
        own[s] = min(float(_knee_bend(c, s)[mask].min()), float(base["knee_bend"][s]))
    base["_knee_planted"] = own
    base["_lowered"] = float(result.info.get("lowered", 0.0))
    return own


def calibrate(walk, base, run):
    """Probe the CALIBRATED knobs on the walk measured `base` (at base_engine) and keep each one's response in
    base["_curve"] = {knob: {side or "": [(asked change, measured change), ...] by asked, (0, 0) included}};
    `run(gait)` evaluates the animator's units (the pose the base was measured under included) into a Result (or
    its world matrices). Also the pelvis's drop at the duty probes and at STEP_PROBES of the step and the
    speed: kept as "_drop_<knob>" curves {"": [(asked change, cm down)]} (ranges cut them there). Sixteen
    evaluations."""
    base.pop("_curve", None)
    rng = ranges(base, walk.leg_length)
    curves = {}
    drops = dict((name, [(0.0, float(base.get("_lowered", 0.0)))]) for name in DROP_CUT)
    for group in CALIBRATED:
        for share in sorted(set(s for name in group for s in KNOB_PROBES.get(name, PROBES))):
            gait, asked = {}, {}
            for name in group:
                if share not in KNOB_PROBES.get(name, PROBES):
                    continue
                k = BY_NAME[name]
                lo, hi = rng[name]
                sides = SIDES if k.sided else ("",)
                mean = float(np.mean([_own(base, name, s or None) for s in sides]))
                d = share * ((hi - mean) if share > 0 else (mean - lo))
                if abs(d) < 1e-3:
                    continue
                for s in sides:
                    gait[name + "_" + s if s else name] = _own(base, name, s or None) + d
                    asked[(name, s)] = d
            if not gait:
                continue
            res = run(gait)
            m = measure(walk, getattr(res, "worlds", res))
            for (name, s), d in asked.items():
                if name in drops and hasattr(res, "info"):
                    drops[name].append((d, float(res.info.get("lowered", 0.0))))
                got = m[BY_NAME[name].key]
                got = float(got[s]) if s else float(got)
                curves.setdefault(name, {}).setdefault(s, [(0.0, 0.0)]).append((d, got - _own(base, name, s or None)))
    for name in DROP_PROBES:
        own = base[BY_NAME[name].key]
        for share in STEP_PROBES:
            d = share * (rng[name][1] - own)
            if d < 1e-3:
                continue
            res = run({name: own + d})
            if hasattr(res, "info"):
                drops[name].append((d, float(res.info.get("lowered", 0.0))))
    for name, sides in curves.items():
        for s, points in sides.items():
            sides[s] = _monotone(sorted(points))
    for name, points in drops.items():
        if len(points) > 1:
            curves["_drop_" + name] = {"": sorted(set(points))}
    base["_curve"] = curves
    return curves


def drop_top(points, most):
    """The asked change (above the walk's own) at which the pelvis's drop `points` [(asked, cm down)] first
    reaches `most` cm, linear between the probes; None when it never does."""
    up = sorted(p for p in points if p[0] >= 0.0)
    for (a0, g0), (a1, g1) in zip(up, up[1:]):
        if g1 >= most > g0 - 1e-12 or (g0 >= most and a0 == 0.0):
            if g0 >= most:
                return a0
            return a0 + (most - g0) * (a1 - a0) / (g1 - g0)
    return None


def _monotone(points):
    """The curve made to grow away from (0, 0) each way (a probe that moved less than the one before it, or the
    wrong way, stands where that one did): a reach the walk has, never a turn back."""
    neg = [p for p in points if p[0] < 0.0][::-1]
    pos = [p for p in points if p[0] > 0.0]
    out_pos, top = [], 0.0
    for a, g in pos:
        top = max(top, g)
        out_pos.append((a, top))
    out_neg, bottom = [], 0.0
    for a, g in neg:
        bottom = min(bottom, g)
        out_neg.append((a, bottom))
    return out_neg[::-1] + [(0.0, 0.0)] + out_pos


def _inverse(points, delta):
    """The asked change that measures `delta` on the response `points` (_monotone's): piecewise linear, the first
    asked reaching it where the curve is flat; past the reach, the first asked that reaches as far as the walk
    goes - not the curve's end: a knob that turns back past a point (a run's elbow swing grows again once the
    springs' phase leaves the added swing behind, HavyRun) would be asked its range's end and go the wrong way."""
    side = [p for p in points if (p[0] >= 0.0 if delta > 0 else p[0] <= 0.0)]
    side = side if delta > 0 else side[::-1]                    # from (0, 0) outward
    for (a0, g0), (a1, g1) in zip(side, side[1:]):
        if abs(delta) <= abs(g1) + 1e-12 and abs(g1 - g0) > 1e-12:
            return a0 + (delta - g0) * (a1 - a0) / (g1 - g0)
    far = side[-1][1]
    return next(a for a, g in side if abs(g - far) <= 1e-12)


def _calibrated(base, name, side, delta):
    """The asked change `delta` of knob `name` turned into the engine's, through its response on this walk."""
    points = base.get("_curve", {}).get(name, {}).get(side or "")
    if not points or not delta:
        return delta
    return _inverse(points, delta)


def _calibrated_sides(base, name, deltas):
    """{side: engine change} for a sided knob asked {side: change}: the same change both sides (Both) through the
    sides' mean response, one engine change for both - the probes moved them together, and the sides are not
    apart: the legs share the pelvis (HavyRun's knees, the left asked more as it bends less, its pelvis drop bent
    the right 50 % past its own curve); apart, each side through its own."""
    curves = base.get("_curve", {}).get(name, {})
    if (abs(deltas["l"] - deltas["r"]) < 1e-9 and "l" in curves and "r" in curves
            and [a for a, _ in curves["l"]] == [a for a, _ in curves["r"]]):
        mean = _monotone([(a, 0.5 * (gl + gr)) for (a, gl), (_, gr) in zip(curves["l"], curves["r"])])
        d = _inverse(mean, deltas["l"]) if deltas["l"] else 0.0
        return {"l": d, "r": d}
    return dict((s, _calibrated(base, name, s, deltas[s])) for s in SIDES)


def reach(base, name):
    """(most below, most above) the walk's own value the calibrated knob `name` measured (its sides' mean), or
    None when not calibrated."""
    sides = base.get("_curve", {}).get(name)
    if not sides:
        return None
    lows = [min(g for _, g in pts) for pts in sides.values()]
    highs = [max(g for _, g in pts) for pts in sides.values()]
    return float(np.mean(lows)), float(np.mean(highs))


def engine_knobs(walk, base, gait):
    """The model's knobs for the asked `gait` ({knob: value}, a sided knob also "<name>_l" / "_r"; a knob not in
    it is the walk's own) of the walk measured `base` at base_engine(walk). Relative to the walk: every knob at
    its own value gives base_engine exactly."""
    e = dict(base_engine(walk))
    step, cadence = timing(gait, base)
    e["stride"] = step / base["step"]
    if abs(cadence - base["cadence"]) > 1e-9:
        e["tempo"] = float(max(4, int(round(walk.P * base["cadence"] / cadence))))
    if "duty" in gait:
        e["ground_time"] = 1.0 + _calibrated(base, "duty", None, float(gait["duty"]) - base["duty"]) / base["duty"]
    weight = value(gait, base, "weight")
    if weight:
        e["weight"] = weight * (WEIGHT_GAIN if weight > 0 else 1.0)
    e["bob_add"] = _calibrated(base, "bob", None, value(gait, base, "bob") - base["bob"])
    hips = value(gait, base, "hips")
    gain = walk.twist_gain
    e["pelvis_twist"] = walk.own_twist + (hips - base["hips"]) / gain
    if "hip_drop" in gait:
        drop = value(gait, base, "hip_drop")
    elif "hips" in gait and abs(base["hips"]) > 0.5:        # the drop follows the twist as the walk has them
        drop = base["hip_drop"] * hips / base["hips"]
    else:
        drop = base["hip_drop"]
    e["pelvis_list"] = walk.own_list + (drop - base["hip_drop"])
    e["lean_add"] = value(gait, base, "lean") - base["lean"]
    width = value(gait, base, "width")
    if abs(width - base["width"]) > 1e-9:
        e["stance"] = width / base["width"] if base["width"] > 1.0 else 1.0
    e["exaggeration"] = value(gait, base, "energy") / 100.0
    e["pelvis_height"] = value(gait, base, "height")
    e["pelvis_forward"] = value(gait, base, "forward")
    e["sway_add"] = value(gait, base, "sway") - base["sway"]
    e["surge_add"] = value(gait, base, "surge") - base["surge"]
    e["root_sway"] = 0.0 if value(gait, base, "root_line") >= 0.5 else 1.0
    e["in_place"] = 1.0 if value(gait, base, "in_place") >= 0.5 else 0.0
    if getattr(walk, "chest_shape", None) is not None:
        e["chest_twist"] = walk.own_chest_twist + (value(gait, base, "chest_twist") - base["chest_twist"]) / gain
        e["chest_sway"] = walk.own_chest_sway + (value(gait, base, "chest_sway") - base["chest_sway"])
    e["chest_bounce_add"] = value(gait, base, "chest_bounce") - base["chest_bounce"]
    e["head"] = 1.0 - value(gait, base, "head_steady") / 100.0
    e["nod_add"] = value(gait, base, "nod")
    e["foot_placement"] = 1.0 if value(gait, base, "placement") >= 0.5 else 0.0
    e["balance"] = value(gait, base, "balance") / 100.0
    e["weight_lag"] = 0.0                                  # Weight is not Follow-through (gaitmodel)
    follow = value(gait, base, "follow")
    whip = value(gait, base, "whip")
    e.update({"torso_drag": follow, "head_drag": HEAD_DRAG * follow, "arm_drag": follow,
              "torso_bounce": TORSO_WHIP * whip, "arm_bounce": whip})
    def changes(name):
        own = base[BY_NAME[name].key]
        return dict((s, value(gait, base, name, s) - own[s]) for s in SIDES if s in own)
    knee_d = _calibrated_sides(base, "knee_bend", changes("knee_bend"))
    arm_d = {}
    for name in ("elbow", "elbow_swing"):
        d = changes(name)
        arm_d[name] = _calibrated_sides(base, name, d) if len(d) == 2 else d
    for side in SIDES:
        sfx = "_" + side
        # the engine scales the lift over the take-off / landing line (foot_target's lift_up), not the height
        # over the ground (a run's heel is already up when the foot leaves it): solved on the walk's own swing
        change = value(gait, base, "lift", side) - base["lift"][side]
        if abs(change) > 1e-9:
            e["lift" + sfx] = lift_scale(walk.lift_profile(side), change)
        e["arm_swing_add" + sfx] = value(gait, base, "arm_swing", side) - base["arm_swing"].get(side, 0.0)
        e["toe_add" + sfx] = value(gait, base, "toe_out", side) - base["toe_out"][side]
        e["swing_out" + sfx] = value(gait, base, "swing_out", side) - base["swing_out"][side]
        # the cap from the straightest knee over the model's planted frames (annotate), the asked change from the
        # walk's own straightest as measured
        own_knee = base["knee_bend"][side]
        cap_own = base.get("_knee_planted", {}).get(side, own_knee)
        asked = cap_own + knee_d[side]
        e["knee_bend" + sfx] = asked if asked > cap_own + 0.25 else 0.0
        e["foot_lag" + sfx] = value(gait, base, "foot_lag", side)
        e["foot_flex" + sfx] = value(gait, base, "ankle_flex", side) / 100.0
        for name, key in (("elbow", "elbow_add"), ("elbow_swing", "elbow_swing_add")):
            if side in arm_d[name]:
                e[key + sfx] = arm_d[name][side]
        for name, key in (("arms_forward", "arm_fwd_add"), ("arm_out", "arm_out_add")):
            if side in base[name]:
                e[key + sfx] = value(gait, base, name, side) - base[name][side]
        e["shoulder_add" + sfx] = value(gait, base, "shoulders", side)
    return e
