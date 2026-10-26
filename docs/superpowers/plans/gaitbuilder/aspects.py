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
         tip="Light (-1) to heavy (+1): a deeper bob and lower body, the knees bent on the load, a slower strike, "
             "more follow-through"),
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
    Knob("arm_timing", "Arms", "Arm timing", "fr", "added", 0.0, _fixed(-6.0, 6.0), sided=True,
         tip="The arms' motion later (+) or earlier, in frames"),
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
WEIGHT_KNEE = 12.0        # deg: Weight +1 bends a planted knee this much more than the walk's own straightest
WEIGHT_FOLLOW = 1.0       # frames: Weight +1 adds this much follow-through (-1 takes it off)
WEIGHT_GAIN = 1.5         # the model's weight at Weight +1
HEAD_DRAG = 4.0 / 3.0     # the head's spring x Follow-through (Walk Builder's 2.0 over 1.5)
TORSO_WHIP = 2.0 / 3.0    # the trunk's bounce x Whip (Walk Builder's 0.2 over 0.3)


def base_engine(walk):
    """The model's knobs that give the walk as it is, the helpers on: Walk Builder's defaults with the walk's own
    hip twist and drop and chest twist and sway (Walk Builder's defaults set them to people's)."""
    out = {"pelvis_twist": walk.own_twist, "pelvis_list": walk.own_list}
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
        e["ground_time"] = float(gait["duty"]) / base["duty"]
    weight = value(gait, base, "weight")
    if weight:
        e["weight"] = weight * (WEIGHT_GAIN if weight > 0 else 1.0)
    e["bob_add"] = value(gait, base, "bob") - base["bob"]
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
    if getattr(walk, "chest_shape", None) is not None:
        e["chest_twist"] = walk.own_chest_twist + (value(gait, base, "chest_twist") - base["chest_twist"]) / gain
        e["chest_sway"] = walk.own_chest_sway + (value(gait, base, "chest_sway") - base["chest_sway"])
    e["chest_bounce_add"] = value(gait, base, "chest_bounce") - base["chest_bounce"]
    e["head"] = 1.0 - value(gait, base, "head_steady") / 100.0
    e["nod_add"] = value(gait, base, "nod")
    e["foot_placement"] = 1.0 if value(gait, base, "placement") >= 0.5 else 0.0
    e["balance"] = value(gait, base, "balance") / 100.0
    follow = max(0.0, value(gait, base, "follow") + WEIGHT_FOLLOW * weight)
    whip = value(gait, base, "whip")
    e.update({"torso_drag": follow, "head_drag": HEAD_DRAG * follow, "arm_drag": follow,
              "torso_bounce": TORSO_WHIP * whip, "arm_bounce": whip})
    for side in SIDES:
        sfx = "_" + side
        e["lift" + sfx] = value(gait, base, "lift", side) / base["lift"][side] if base["lift"][side] > 0.5 else 1.0
        e["arm_swing_add" + sfx] = value(gait, base, "arm_swing", side) - base["arm_swing"].get(side, 0.0)
        e["toe_add" + sfx] = value(gait, base, "toe_out", side) - base["toe_out"][side]
        e["swing_out" + sfx] = value(gait, base, "swing_out", side) - base["swing_out"][side]
        own_knee = base["knee_bend"][side]
        knee = max(value(gait, base, "knee_bend", side), own_knee + WEIGHT_KNEE * max(weight, 0.0))
        e["knee_bend" + sfx] = knee if knee > own_knee + 0.25 else 0.0
        e["foot_lag" + sfx] = value(gait, base, "foot_lag", side)
        e["foot_flex" + sfx] = value(gait, base, "ankle_flex", side) / 100.0
        for name, key in (("elbow", "elbow_add"), ("elbow_swing", "elbow_swing_add"),
                          ("arms_forward", "arm_fwd_add"), ("arm_out", "arm_out_add")):
            if side in base[name]:
                e[key + sfx] = value(gait, base, name, side) - base[name][side]
        e["shoulder_add" + sfx] = value(gait, base, "shoulders", side)
        e["arm_lag_add" + sfx] = value(gait, base, "arm_timing", side)
    return e
