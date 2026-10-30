"""maya_walk.gait - Walk Builder's parameters: the walk as named quantities in units, edited (2026-10-26).

A parameter is one measured feature of a gait - the bounce in cm, the arms' lag in frames, the heel up at the
toe-off in degrees. `measure` reads every parameter off any closed cycle the same way (the clip and the result
alike), and `engine_knobs` turns the asked values into maya_walk.model's engine knobs so a value asked reads back
wherever physics did not have to give way. A parameter is stored as a change from the cycle's own value (a ratio
for a size, an offset for a posture or a timing), so one card drives several walkers, each from its own walk.

numpy only, no Maya. Design: docs/superpowers/specs/2026-10-26-walk-builder-editable-model-design.md (the
parameters, the helpers, the Diagnosis); Gait Builder's aspects.py measured the same way first.
"""
import math

import numpy as np

SIDES = ("l", "r")
QUIET = {"cm": 0.5, "deg": 1.0}           # an amplitude under this of its own is stored and mapped as an offset
ARM_QUIET = 2.0                           # deg: an arm's own swing under this takes an added swing (the engine's)
FLAT_TOL = 3.0                            # deg: a sole this near the floor is flat (Foot flat)
TOE_FLAT = 20.0                           # deg: Toe out is read on the planted frames the sole stands this flat (a
#                                           foot standing on its toes reads its yaw off a short, turning toe line)
KNEE_SOFT = 0.04                          # a leg eases into its reach from this share below it (the engine's knee_soft)
WHIP_DRAG = 1.5                           # frames: the arms' and the trunk's springs under Whip
WHIP_HEAD = 2.0                           # frames: the head's
# the physics' links (the guide's sections 2 and 12): a longer step rolls further over the ball and the heel; the
# arms swing with the speed (50-53 deg at 1.43 m/s, 60-65 at 1.75)
PUSH_PER_STEP = 40.0                      # deg of Push-off per +100 % of the step
HEEL_PER_STEP = 25.0                      # deg of Heel strike per +100 % of the step
ARM_PER_SPEED = 1.0                       # the arm swing x (speed ratio) ^ this
ARM_LINK = (0.5, 2.0)                     # at most this far either way
# Arm overlap's slider (ms): half the source cycle either way - past half a cycle a lag of a periodic signal
# comes back on itself (measured 2026-10-29: the hand 25.8 cm late at a quarter of the cycle, 22.9 with a
# spring on top). Never narrower than the floor, so a very short cycle keeps a usable slider
OVERLAP_MAX = 2000.0
OVERLAP_FLOOR = 250.0
# the Weight macro at +1 (the guide's sections 3, 5, 10); negative: the reverse, halved
WEIGHT = {"bounce": ("ratio", 1.6), "low_point": ("offset", 8.0), "knee_bend": ("offset", 4.0),
          "foot_flat": ("offset", 1.5), "arm_lag": ("offset", 1.5), "torso_lag": ("offset", 1.0),
          "tempo": ("ratio", 1.05)}
# The characters: deltas from the clip (the guide's section 10 and the emotions), each x Strength
CHARACTERS = (
    ("Natural", {}),
    ("Bouncy", {"bounce": ("ratio", 1.8), "foot_lift": ("ratio", 1.3), "arm_swing": ("ratio", 1.2),
                "push": ("offset", 8.0), "tempo": ("ratio", 0.95)}),
    ("Double bounce", {"double_bounce": ("offset", 3.0), "bounce": ("ratio", 0.6)}),
    ("March", {"foot_lift": ("ratio", 1.8), "arm_swing": ("ratio", 1.4), "heel_strike": ("offset", 6.0),
               "lean": ("offset", -3.0), "tempo": ("ratio", 0.9), "head_motion": ("ratio", 0.6)}),
    ("Stroll", {"tempo": ("ratio", 1.15), "step": ("ratio", 0.9), "arm_swing": ("ratio", 0.8),
                "bounce": ("ratio", 0.8), "lean": ("offset", -2.0), "hips_twist": ("ratio", 1.1)}),
    ("Tired", {"tempo": ("ratio", 1.2), "step": ("ratio", 0.85), "lean": ("offset", 8.0), "nod": ("offset", 10.0),
               "arm_swing": ("ratio", 0.5), "foot_lift": ("ratio", 0.6), "bounce": ("ratio", 0.7),
               "arm_lag": ("offset", 2.0), "torso_lag": ("offset", 1.0)}),
    ("Heavy", {"bounce": ("ratio", 1.5), "low_point": ("offset", 8.0), "knee_bend": ("offset", 6.0),
               "tempo": ("ratio", 1.1), "width": ("ratio", 1.2), "sway": ("ratio", 1.3), "foot_flat": ("offset", 2.0)}),
    ("Sneak", {"tempo": ("ratio", 1.4), "step": ("ratio", 0.7), "height": ("offset", -12.0), "lean": ("offset", 12.0),
               "foot_lift": ("ratio", 1.3), "arm_swing": ("ratio", 0.3), "arms_forward": ("offset", 20.0),
               "elbow": ("offset", 30.0)}),
    ("Angry", {"tempo": ("ratio", 0.85), "step": ("ratio", 1.1), "lean": ("offset", 6.0), "arm_swing": ("ratio", 1.3),
               "elbow": ("offset", 20.0), "heel_strike": ("offset", 5.0), "shoulders": ("offset", 5.0),
               "nod": ("offset", 5.0)}),
    ("Happy", {"tempo": ("ratio", 0.9), "bounce": ("ratio", 1.4), "arm_swing": ("ratio", 1.3), "lean": ("offset", -3.0),
               "nod": ("offset", -5.0), "foot_lift": ("ratio", 1.2), "push": ("offset", 6.0)}),
    ("Sad", {"tempo": ("ratio", 1.12), "step": ("ratio", 0.9), "nod": ("offset", 15.0), "lean": ("offset", 8.0),
             "arm_swing": ("ratio", 0.6), "sway": ("ratio", 1.2)}),
    ("Afraid", {"tempo": ("ratio", 0.9), "step": ("ratio", 0.75), "height": ("offset", -8.0), "lean": ("offset", 5.0),
                "arm_swing": ("ratio", 0.4), "elbow": ("offset", 25.0), "arms_forward": ("offset", 10.0),
                "shoulders": ("offset", 8.0), "width": ("ratio", 1.15)}),
)
CHARACTER = dict(CHARACTERS)
FROUDE_TEMPO = 1.15                       # the guide's step time: 1.15 f sqrt(h / g) Fr^-0.2 (Diagnosis, a walk)


# ---- the parameters ----

class Param(object):
    """One parameter. `kind`: "size" (stored as a ratio of the walk's own, an offset where its own is quiet),
    "offset" (stored as an offset), "added" (not measured: its own is `default`, stored as an offset), "toggle"
    (on / off). `rule(own, leg)` its range from the walk's own value (a sided one's mean) and its leg length."""

    def __init__(self, name, group, label, unit, kind, sided=False, rule=None, default=0.0, tip=""):
        self.name, self.group, self.label, self.unit, self.kind = name, group, label, unit, kind
        self.sided, self.rule, self.default, self.tip = sided, rule, default, tip

    def store(self, own):
        """How a change of this parameter from `own` is stored: "ratio" or "offset"."""
        if self.kind != "size":
            return "offset"
        return "ratio" if abs(own) >= QUIET.get(self.unit, 1e-6) else "offset"


def _share(lo, hi, floor=None, ceil=None):
    def rule(b, leg):
        a, z = b * lo, b * hi
        if floor is not None:
            a = min(a, floor)
        if ceil is not None:
            z = max(z, ceil(leg) if callable(ceil) else ceil)
        return a, z
    return rule


def _about(below, above, lo_cap=None, hi_cap=None):
    def rule(b, leg):
        a, z = b - below, b + above
        return (max(a, lo_cap) if lo_cap is not None else a), (min(z, hi_cap) if hi_cap is not None else z)
    return rule


def _fixed(lo, hi):
    return lambda b, leg: (lo, hi)


MAIN, TIMING, PELVIS, LEGS, TRUNK, HEAD, ARMS, WEAPON, PHYSICS = (
    "main", "timing", "pelvis", "legs", "trunk", "head", "arms", "weapon", "physics")
GROUPS = (MAIN, TIMING, PELVIS, LEGS, TRUNK, HEAD, ARMS, WEAPON, PHYSICS)
GROUP_LABELS = {MAIN: "Main", TIMING: "Timing", PELVIS: "Pelvis", LEGS: "Legs", TRUNK: "Trunk", HEAD: "Head",
                ARMS: "Arms", WEAPON: "Weapon", PHYSICS: "Physics"}
PARAMS = (
    Param("tempo", MAIN, "Tempo", "fr", "size", rule=_share(0.5, 2.0),
          tip="Frames a step: fewer is quicker (the steps a minute and the speed beside it)"),
    Param("step", MAIN, "Step", "cm", "size", rule=_share(0.5, 1.6),
          tip="One step's length at the same tempo (the speed follows)"),
    Param("width", MAIN, "Width", "cm", "size", rule=lambda b, leg: (0.0, max(3.0 * b, 0.4 * leg)),
          tip="How far apart the feet stand on the ground, across the body"),
    Param("bounce", MAIN, "Bounce", "cm", "size", rule=lambda b, leg: (0.0, max(3.0 * b, 0.1 * leg)),
          tip="The pelvis's bob, up and down twice a stride (peak to peak)"),
    Param("low_point", MAIN, "Low point", "%", "offset", rule=_about(40.0, 40.0),
          tip="Where the bob is lowest, % of a step after the heel strike: mocap ~10, the classic down pose ~25"),
    Param("lean", MAIN, "Lean", "deg", "offset", rule=_about(30.0, 30.0, -25.0, 75.0),
          tip="The trunk forward (+) over the hips; the head keeps its gaze"),
    Param("arm_swing", MAIN, "Arm swing", "deg", "size", sided=True, rule=lambda b, leg: (0.0, max(90.0, 2.0 * b)),
          tip="The upper arms' swing forward and back (peak to peak); unset, it follows the speed"),
    Param("arm_lag", MAIN, "Arm lag", "fr", "offset", sided=True, rule=_about(8.0, 8.0),
          tip="Frames the arm's forward swing comes after the other foot's heel strike (overlap as a time shift)"),
    Param("detail", MAIN, "Detail", "", "added", rule=_fixed(0.0, 1.0), default=1.0,
          tip="1 keeps the clip's own handwriting (what the stride's harmonics leave), 0 the clean model"),
    # the timing
    Param("ground_time", TIMING, "Ground time", "%", "offset", sided=True,
          rule=lambda b, leg: (max(15.0, b - 25.0), min(90.0, b + 25.0)),
          tip="How much of a stride each foot is on the ground; under 50 % both feet leave it at once - a run"),
    Param("push", TIMING, "Push-off", "deg", "offset", sided=True,
          rule=lambda b, leg: (b, max(b + 1.0, min(b + 40.0, 80.0))),
          tip="The heel up at the toe-off: the trailing foot rolls over its ball; unset, it follows the step"),
    Param("heel_strike", TIMING, "Heel strike", "deg", "offset", sided=True,
          rule=lambda b, leg: (b, max(b + 1.0, min(b + 30.0, 45.0))),
          tip="The toes up at the contact: the leading foot lands on its heel; unset, it follows the step"),
    Param("foot_flat", TIMING, "Foot flat", "fr", "offset", sided=True,
          rule=lambda b, leg: (b, b) if b < 0.25 else (max(b - 5.0, 0.0), b + 10.0),
          tip="Frames from the heel strike to a flat foot: how fast a heel strike's toes come down"),
    # the pelvis
    Param("height", PELVIS, "Height", "cm", "offset", rule=_about(40.0, 40.0),
          tip="The pelvis over the feet; the legs never straighten past the walk's own"),
    Param("forward", PELVIS, "Forward", "cm", "offset", rule=_about(30.0, 30.0),
          tip="The hips ahead of (+) or behind (-) the feet, the body over them going with them"),
    Param("sway", PELVIS, "Sway", "cm", "size", rule=lambda b, leg: (0.0, max(3.0 * b, 0.12 * leg)),
          tip="The pelvis side to side (peak to peak); unset, the balance sets it from the width and the tempo"),
    Param("surge", PELVIS, "Surge", "cm", "size", rule=lambda b, leg: (0.0, max(3.0 * b, 0.08 * leg)),
          tip="The pelvis forward and back as it walks (peak to peak); unset, the balance sets it"),
    Param("double_bounce", PELVIS, "Double bounce", "cm", "offset", rule=lambda b, leg: (b, b + 0.08 * leg),
          tip="A second bob twice a step, its lows at each strike and each passing (peak to peak)"),
    Param("hips_twist", PELVIS, "Hips twist", "deg", "size", rule=lambda b, leg: (0.0, max(25.0, 2.5 * abs(b))),
          tip="The pelvis's turn each way with the legs; unset, it grows with the step"),
    Param("hip_drop", PELVIS, "Hip drop", "deg", "offset", rule=_about(10.0, 15.0),
          tip="The standing leg's hip up and the swinging leg's down, each way"),
    Param("root_on_line", PELVIS, "Root on line", "", "toggle", default=1.0,
          tip="On: the root runs straight down the walk's line (a game's capsule); off: it weaves with the hips"),
    # the legs
    Param("foot_lift", LEGS, "Foot lift", "cm", "size", sided=True, rule=lambda b, leg: (0.2 * b, max(3.0 * b, 0.3 * leg)),
          tip="How high the swinging foot rises over its path"),
    Param("toe_out", LEGS, "Toe out", "deg", "offset", sided=True, rule=_about(30.0, 40.0),
          tip="The planted foot turned out (+) or in (-)"),
    Param("swing_out", LEGS, "Swing out", "cm", "offset", sided=True, rule=_about(20.0, 30.0),
          tip="The swinging foot's path bowed out to its side (+) or in, mid-flight"),
    Param("knee_bend", LEGS, "Knee bend", "deg", "offset", sided=True, rule=lambda b, leg: (b, max(b + 1.0, 70.0)),
          tip="A planted knee is never straighter than this: the pelvis sinks where it would be"),
    Param("leg_match", LEGS, "Leg match", "", "added", rule=_fixed(0.0, 1.0), default=1.0,
          tip="Running, a side-on pose's hips face the run and its knees keep their splay x 1 / (1 + Fr)"),
    Param("leg_turn", LEGS, "Leg turn", "x", "added", sided=True, rule=_fixed(0.0, 2.0), default=1.0,
          tip="A pose's knee and toe turns"),
    Param("knee_foot", LEGS, "Knee <-> foot", "", "added", sided=True, rule=_fixed(0.0, 1.0), default=0.5,
          tip="Past 15 deg of knee against toe: 0 the knee to the foot, 1 the foot to the knee"),
    # the trunk
    Param("chest_twist", TRUNK, "Chest twist", "deg", "size", rule=lambda b, leg: (0.0, max(40.0, 2.5 * b)),
          tip="The shoulders turn each way against the hips; unset, it grows with the step"),
    Param("chest_sway", TRUNK, "Chest sway", "deg", "size", rule=lambda b, leg: (0.0, max(15.0, 2.5 * b)),
          tip="The shoulder line tilts each way over the steps"),
    Param("chest_timing", TRUNK, "Chest timing", "deg", "offset", rule=_about(120.0, 120.0),
          tip="The shoulders' turn against the hips', degrees of phase: 180 turns them exactly against, ~150 a "
              "walk's, under 90 with the hips"),
    Param("chest_bounce", TRUNK, "Chest bounce", "deg", "size", rule=lambda b, leg: (0.0, max(10.0, 3.0 * b)),
          tip="The chest pitches forward and back twice a stride"),
    Param("torso_lag", TRUNK, "Torso lag", "fr", "added", rule=_fixed(-5.0, 8.0),
          tip="Frames the spine's motion comes later, bottom up: none at the pelvis, all of it at the chest"),
    Param("gait_lean", TRUNK, "Gait lean", "", "added", rule=_fixed(0.0, 1.0), default=1.0,
          tip="A pose's trunk takes the walk's own forward lean"),
    # the head
    Param("head_motion", HEAD, "Head motion", "deg", "size", rule=lambda b, leg: (0.0, max(20.0, 2.5 * b)),
          tip="The head's pitch over the steps (peak to peak); 0 holds its gaze still"),
    Param("nod", HEAD, "Nod", "deg", "added", rule=_fixed(-30.0, 30.0), tip="The head forward (+) or back"),
    Param("head_lag", HEAD, "Head lag", "fr", "added", rule=_fixed(-5.0, 8.0),
          tip="Frames the head's motion comes after the chest's"),
    # the arms
    Param("arms_forward", ARMS, "Arms forward", "deg", "offset", sided=True, rule=_about(40.0, 40.0),
          tip="The upper arms held forward (+) or back"),
    Param("elbow", ARMS, "Elbow", "deg", "offset", sided=True, rule=_about(30.0, 90.0, 0.0, 150.0),
          tip="The elbows' bend"),
    Param("elbow_swing", ARMS, "Elbow swing", "deg", "size", sided=True, rule=lambda b, leg: (0.0, max(40.0, 2.5 * b)),
          tip="The elbows' bend swinging with the arm (peak to peak)"),
    Param("arm_out", ARMS, "Arm out", "deg", "offset", sided=True, rule=_about(20.0, 40.0),
          tip="The upper arms held out to their sides"),
    Param("shoulders", ARMS, "Shoulders", "deg", "added", sided=True, rule=_fixed(-20.0, 25.0),
          tip="The shoulders raised (+) or dropped"),
    Param("arm_overlap", ARMS, "Arm overlap", "ms", "added", sided=True,
          rule=_fixed(-OVERLAP_MAX, OVERLAP_MAX),
          tip="The whole arm late by this many milliseconds - its own swing and everything it takes from the "
              "body (the chest's turn, the shoulder's bob); a hand holding a weapon takes the weapon with it. "
              "The slider reaches half the cycle either way - past that a lag comes back on itself"),
    Param("elbow_overlap", ARMS, "Elbow overlap", "ms", "added", sided=True,
          rule=_fixed(-OVERLAP_MAX, OVERLAP_MAX),
          tip="The elbow's orbit about the shoulder-wrist line late by this many milliseconds, on top of Arm "
              "overlap - the hand stays where Arm overlap puts it and the bones keep their lengths, so this "
              "is a late orbit of the elbow, not a late bend. It works under a two-handed grip too: it moves "
              "no hand"),
    Param("hand_overlap", ARMS, "Hand overlap", "ms", "added", sided=True,
          rule=_fixed(-OVERLAP_MAX, OVERLAP_MAX),
          tip="The hand's own turn late by this many milliseconds, on top of Arm overlap - its place stays "
              "where Arm overlap puts it, so this is the wrist breaking late. Under a two-handed grip it is "
              "the weapon's own turn that lags its travel, and the hold is kept"),
    Param("elbow_lag", ARMS, "Elbow lag", "fr", "offset", sided=True, rule=_about(6.0, 8.0),
          tip="Frames the elbow's bend comes after the arm's forward swing"),
    Param("hand_lag", ARMS, "Hand lag", "fr", "added", sided=True, rule=_fixed(-5.0, 8.0),
          tip="Frames the hand comes after the forearm"),
    # the weapon
    Param("weapon_overlap", WEAPON, "Weapon overlap", "ms", "added", sided=True,
          rule=_fixed(-OVERLAP_MAX, OVERLAP_MAX),
          tip="The weapon in the hands swung about its grip so its blade points at its own tip this many "
              "milliseconds ago - the sword's tip trails and the blade leads back to it, with the hands "
              "holding it turning along (a two-handed hold is kept). It needs a weapon in a hand: the "
              "Inventory's Equip puts one there. The slider reaches half the cycle either way"),
    # the physics
    Param("whip", PHYSICS, "Whip", "", "added", rule=_fixed(0.0, 1.0), default=0.3,
          tip="The arms, the trunk and the head overshoot as they catch up with the body (springs whose stride "
              "swing is kept): 0 none"),
    Param("foot_placement", PHYSICS, "Foot placement", "", "toggle", default=1.0,
          tip="On: a planted foot never slides and one foot is always down; off: the walk's own feet"),
    Param("balance", PHYSICS, "Balance", "", "toggle", default=1.0,
          tip="On: the centre of mass is carried over the feet as the steps and the pose change"),
)
P = dict((p.name, p) for p in PARAMS)
SIZE_OFFSETS = ("sway", "surge")          # sizes the physics moves: set, the balance's term on that axis is off


def keys():
    """Every parameter's keys: a sided one's "<name>", "<name>_l", "<name>_r"."""
    out = []
    for p in PARAMS:
        out.append(p.name)
        if p.sided:
            out.extend(p.name + "_" + s for s in SIDES)
    return out


def param_of(key):
    """The Param of a key ("arm_swing_l" -> arm_swing) and its side or None."""
    if key in P:
        return P[key], None
    if key[-2:] in ("_l", "_r") and key[:-2] in P and P[key[:-2]].sided:
        return P[key[:-2]], key[-1]
    raise KeyError(key)


# ---- measuring ----

def _unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n > 1e-12, n, 1.0)


def _mean_rot(rs):
    u, _, vt = np.linalg.svd(np.sum(rs, axis=0))
    m = u @ vt
    if np.linalg.det(m) < 0:
        u[:, -1] *= -1.0
        m = u @ vt
    return m


def _log_rot(r):
    """rotation vectors of row-vector rotations (..., 3, 3) (maya_walk.model's exp_rot convention)"""
    c = np.swapaxes(r, -1, -2)
    th = np.arccos(np.clip((np.trace(c, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0))
    v = np.stack([c[..., 2, 1] - c[..., 1, 2], c[..., 0, 2] - c[..., 2, 0], c[..., 1, 0] - c[..., 0, 1]], -1)
    s = np.sin(th)
    k = np.where(s > 1e-7, th / (2.0 * np.where(s > 1e-7, s, 1.0)), 0.5)
    return v * k[..., None]


def harmonic(y, phase, order):
    """(amplitude, phase) of the series `y` on cos / sin(order . phase): its least-squares fit, demeaned."""
    y = np.asarray(y, float) - float(np.mean(y))
    c, s = np.cos(order * phase), np.sin(order * phase)
    c, s = c - c.mean(), s - s.mean()
    a = np.array([[c @ c, c @ s], [c @ s, s @ s]])
    if abs(np.linalg.det(a)) < 1e-12:
        return 0.0, 0.0
    x = np.linalg.solve(a, np.array([c @ y, s @ y]))
    return float(math.hypot(x[0], x[1])), float(math.atan2(x[1], x[0]))


class Cycle(object):
    """A closed cycle laid on a walk: world matrices (J, n+1, 4, 4) of the walk's joints, sample f at the walk's
    source time f . P / n, and its contacts {side: [(strike, lift-off)]} in its own frames."""

    FINE = 8                                  # a regular part read on this many samples a frame

    def __init__(self, walk, worlds, contacts):
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
        self.taus = np.arange(n) * walk.P / float(n)
        self.fine_taus = np.arange(n * self.FINE) * walk.P / float(n * self.FINE)
        self.phase = np.array([walk.stride_phase(float(t)) for t in self.taus])
        self.up = np.asarray(walk.up, float)
        self.ahead, self.lside = np.asarray(walk.ahead, float), np.asarray(walk.lside, float)
        self.basis = np.asarray(walk.basis, float)
        self.across = np.asarray(getattr(walk, "across", walk.lside), float)
        flat = self.travel - float(self.travel @ self.up) * self.up
        self.flat = float(np.linalg.norm(flat))
        self.seconds = n / float(walk.fps)
        self.stride = n / float(walk.strides)                 # frames a stride
        self.step = 0.5 * self.stride
        self.contacts = dict((s, [(float(a), float(b)) for a, b in (contacts or {}).get(s, [])]) for s in SIDES)
        self._fine = self._coarse = None

    def p(self, name):
        return self.pos[self.walk.index[name]]

    def has(self, *names):
        return all(name in self.walk.index for name in names)

    def regular(self, y):
        """The series' regular part (its mean and the stride harmonics) on the fine grid (n x FINE samples)."""
        if self._fine is None:
            self._coarse = self.walk.harmonic_basis(self.taus)
            self._fine = self.walk.harmonic_basis(self.fine_taus)
        coef = np.linalg.lstsq(self._coarse, np.asarray(y, float).reshape(-1), rcond=None)[0]
        return self._fine @ coef

    def p2p(self, y):
        return float(np.ptp(self.regular(y)))

    def down(self, side):
        """(n,) bool: the foot in one of its contacts on frame f."""
        out = np.zeros(self.n, bool)
        for hs, to in self.contacts[side]:
            for f in range(self.n):
                if (f - hs) % self.n <= (to - hs) + 1e-9:
                    out[f] = True
        return out

    def at(self, y, t):
        """The series `y` (n,) at fractional frame t (linear, wrapped)."""
        f = math.floor(t)
        u = t - f
        return float((1.0 - u) * y[int(f) % self.n] + u * y[int(f + 1) % self.n])

    def extremes(self, y, highest=True):
        """The times (frames) the series' regular part is at a local maximum (or minimum)."""
        r = self.regular(y) * (1.0 if highest else -1.0)
        m = len(r)
        out = []
        for i in range(m):
            if r[i] > r[i - 1] and r[i] >= r[(i + 1) % m]:
                # a parabola through the neighbours for the sub-sample peak
                a, b, c = r[i - 1], r[i], r[(i + 1) % m]
                den = a - 2.0 * b + c
                d = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
                out.append(((i + d) / float(self.FINE)) % self.n)
        return out

    def wrapped(self, d, period):
        """d wrapped into (-period / 2, period / 2]."""
        return (d + 0.5 * period) % period - 0.5 * period


def _knee_bend(c, side):
    h, k, a = c.p("thigh_" + side), c.p("calf_" + side), c.p("foot_" + side)
    u, v = _unit(k - h), _unit(a - k)
    return np.degrees(np.arccos(np.clip(np.sum(u * v, axis=1), -1.0, 1.0)))


def _arm(c, side):
    """(forward angle, out angle, elbow bend) series of an arm (degrees)."""
    sign = 1.0 if side == "l" else -1.0
    a = _unit(c.p("lowerarm_" + side) - c.p("upperarm_" + side))
    b = _unit(c.p("hand_" + side) - c.p("lowerarm_" + side))
    fwd = np.degrees(np.arctan2(a @ c.ahead, -(a @ c.up)))
    out = np.degrees(np.arcsin(np.clip(a @ (sign * c.lside), -1.0, 1.0)))
    bend = np.degrees(np.arccos(np.clip(np.sum(a * b, axis=1), -1.0, 1.0)))
    return fwd, out, bend


def _pitch_series(c, j):
    """(n,) a joint's world turn about the body's side axis against its mean, degrees (forward down +)."""
    r = c.rot[j]
    rel = _mean_rot(r).T @ r
    return np.degrees(_log_rot(rel) @ c.lside)


def _sole_pitch(c, side):
    """(n,) the foot's sole pitch a frame, degrees (+ heel up, - toes up)."""
    w, fo = c.walk, c.walk.index["foot_" + side]
    return np.array([math.degrees(w.sole_pitch(side, c.rot[fo, f])) for f in range(c.n)])


def _swing_bow(c, ank, down, sign):
    """The swinging ankle's bow out to its side at mid-flight against the line from its lift-off to its landing,
    cm - the longest flight's."""
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
    a, b = ank[(s0 - 1) % n], ank[(s0 + length) % n]
    mid = ank[(s0 + length // 2) % n]
    t = (length // 2 + 1) / float(length + 1)
    return float((mid - (a + (b - a) * t)) @ (sign * c.lside))


def _sided(out, name, values):
    out[name + "_l"], out[name + "_r"] = float(values["l"]), float(values["r"])
    out[name] = 0.5 * (out[name + "_l"] + out[name + "_r"])


def measure(walk, worlds, contacts):
    """Every parameter of the cycle `worlds` (J, n+1, 4, 4) of `walk`'s skeleton with its `contacts` ({side:
    [(strike, lift-off)]} in its frames): {key: value} in the parameters' units (a sided one also per side), the
    "added" and toggle parameters not (their own is their default), plus "speed" (m/s), "cadence" (steps a
    minute) and "frames" (the cycle's)."""
    c = Cycle(walk, worlds, contacts)
    idx = walk.index
    out = {"frames": float(c.n), "speed": c.flat / c.seconds / 100.0,
           "cadence": 2.0 * walk.strides / c.seconds * 60.0}
    out["tempo"] = c.step
    out["step"] = c.flat / (2.0 * walk.strides)
    # the pelvis against the root's straight line, in the walk's own axes
    pel = c.dev[idx["pelvis"]]
    height = pel @ c.basis[2]
    out["bounce"] = c.p2p(height)
    out["sway"] = c.p2p(pel @ c.basis[1])
    out["surge"] = c.p2p(pel @ c.basis[0])
    out["double_bounce"] = 2.0 * harmonic(height, c.phase, 4)[0]
    # the bob's lowest from the strike: its twice-a-stride harmonic's low, the stride phase 0 at the left strike and
    # a step half a stride (a time shift of the bob moves it one for one; an uneven walk's lows read on average)
    amp, ph = harmonic(height, c.phase, 2)
    low = ((ph + math.pi) / 2.0) % math.pi / math.pi            # share of a step, the low after a strike
    out["low_point"] = 100.0 * (((low + 0.5) % 1.0) - 0.5) if amp > 1e-6 else 0.0
    downs = dict((s, c.down(s)) for s in SIDES)
    ankle_h = np.concatenate([(c.pos[idx["foot_" + s]] @ c.up)[downs[s]] for s in SIDES if downs[s].any()]
                             or [c.pos[idx["foot_l"]] @ c.up])
    out["height"] = float((c.pos[idx["pelvis"]] @ c.up).mean() - ankle_h.mean())
    out["forward"] = float((pel @ c.basis[0]).mean())
    twist, drop = walk.pelvis_fit(c.worlds)
    out["hips_twist"], out["hip_drop"] = twist, drop
    if getattr(walk, "chest_shape", None) is not None:
        out["chest_twist"], out["chest_sway"] = walk.chest_fit(c.worlds)
    else:
        out["chest_twist"] = out["chest_sway"] = 0.0
    out["chest_timing"] = _chest_timing(c)
    spine = [n for n in ("spine_05", "spine_04", "spine_03", "spine_02") if n in idx]
    top = spine[0] if spine else "pelvis"
    out["chest_bounce"] = harmonic(_pitch_series(c, idx[top]), c.phase, 2)[0]
    neck = "neck_01" if "neck_01" in idx else top
    trunk = c.p(neck) - c.p("pelvis")
    out["lean"] = float(np.degrees(np.arctan2(trunk @ c.ahead, trunk @ c.up)).mean())
    out["head_motion"] = c.p2p(_pitch_series(c, idx["head"])) if "head" in idx else 0.0
    # the feet
    across = {}
    sided = dict((name, {}) for name in ("ground_time", "push", "heel_strike", "foot_flat", "foot_lift", "toe_out",
                                         "swing_out", "knee_bend", "arm_swing", "arm_lag", "arms_forward", "arm_out",
                                         "elbow", "elbow_swing", "elbow_lag"))
    for s in SIDES:
        sign = 1.0 if s == "l" else -1.0
        down = downs[s]
        ank = c.dev[idx["foot_" + s]]
        across[s] = float(((ank[down] if down.any() else ank) @ c.across).mean())
        cs = c.contacts[s]
        sided["ground_time"][s] = (100.0 * float(np.mean([(to - hs) / c.stride for hs, to in cs])) if cs else 0.0)
        pitch = _sole_pitch(c, s) if s in getattr(walk, "sole_up", {}) else np.zeros(c.n)
        sided["push"][s] = float(np.mean([c.at(pitch, to) for _, to in cs])) if cs else 0.0
        sided["heel_strike"][s] = float(np.mean([-c.at(pitch, hs) for hs, _ in cs])) if cs else 0.0
        sided["foot_flat"][s] = float(np.mean([_flat_after(c, pitch, hs, to) for hs, to in cs])) if cs else 0.0
        h = ank @ c.up
        ground = float(h[down].mean()) if down.any() else float(h.min())
        sided["foot_lift"][s] = float(h[~down].max() - ground) if (~down).any() else 0.0
        toe = c.p("ball_" + s) - c.p("foot_" + s)
        toe = toe - np.outer(toe @ c.up, c.up)
        yaw = np.degrees(np.arctan2(toe @ (sign * c.lside), toe @ c.ahead))
        flat = down & (np.abs(pitch) < TOE_FLAT) if (down & (np.abs(pitch) < TOE_FLAT)).any() else down
        sided["toe_out"][s] = float(np.median(yaw[flat])) if flat.any() else float(np.median(yaw))
        sided["swing_out"][s] = _swing_bow(c, ank, down, sign)
        bend = _knee_bend(c, s)
        sided["knee_bend"][s] = float(bend[down].min()) if down.any() else float(bend.min())
        if c.has("upperarm_" + s, "lowerarm_" + s, "hand_" + s):
            fwd, side_out, bend_a = _arm(c, s)
            sided["arm_swing"][s] = c.p2p(fwd)
            sided["arms_forward"][s] = float(fwd.mean())
            sided["arm_out"][s] = float(side_out.mean())
            sided["elbow"][s] = float(bend_a.mean())
            sided["elbow_swing"][s] = c.p2p(bend_a)
            other = [hs for hs, _ in c.contacts["r" if s == "l" else "l"]]
            sided["arm_lag"][s] = _lag(c, fwd, other)
            sided["elbow_lag"][s] = (_lag(c, bend_a, None, fwd) if sided["elbow_swing"][s] >= ARM_QUIET else 0.0)
        else:
            for name in ("arm_swing", "arms_forward", "arm_out", "elbow", "elbow_swing", "arm_lag", "elbow_lag"):
                sided[name][s] = 0.0
    out["width"] = across["l"] - across["r"]
    for name, values in sided.items():
        _sided(out, name, values)
    return out


def _flat_after(c, pitch, hs, to):
    """Frames from the strike `hs` to the first moment the sole lies within FLAT_TOL of the floor (the crossing
    between frames interpolated); the contact's least pitch's moment where it never does."""
    tol = FLAT_TOL
    prev = None
    steps = int(math.ceil((to - hs) * 4)) + 1
    for i in range(steps):
        r = i / 4.0
        v = abs(c.at(pitch, hs + r))
        if v <= tol:
            if prev is None:
                return 0.0
            r0, v0 = prev
            return r0 + (v0 - tol) / max(v0 - v, 1e-9) * (r - r0)
        prev = (r, v)
    best = min(range(steps), key=lambda i: abs(c.at(pitch, hs + i / 4.0)))
    return best / 4.0


def _lag(c, y, refs=None, against=None):
    """How late the series `y` swings (frames, wrapped to a stride): its first stride harmonic's peak after
    each of the strikes `refs` (their mean), or after the first harmonic's peak of the series `against`. A time
    shift of the series shifts it one for one; a second peak a stride does not confuse it."""
    amp, p = harmonic(y, c.phase, 1)
    if amp < 1e-9:
        return 0.0
    turn = lambda a: (a + math.pi) % (2.0 * math.pi) - math.pi
    if against is not None:
        amp2, q = harmonic(against, c.phase, 1)
        return turn(p - q) / (2.0 * math.pi) * c.stride if amp2 > 1e-9 else 0.0
    if not refs:
        return 0.0
    w = c.walk
    out = [turn(p - w.stride_phase(r * w.P / float(c.n))) / (2.0 * math.pi) * c.stride for r in refs]
    return float(np.mean(out))


def _chest_timing(c):
    """The shoulders' turn against the hips', degrees of phase in [0, 360): each line's yaw (its first stride
    harmonic) and the difference - 180 turns them exactly against each other."""
    w, idx = c.walk, c.walk.index
    if not c.has("upperarm_l", "upperarm_r", "thigh_l", "thigh_r"):
        return 180.0

    def yaw(a, b):
        d = c.p(a) - c.p(b)
        return np.degrees(np.arctan2(d @ c.ahead, d @ c.lside))
    sa, sp = harmonic(yaw("upperarm_l", "upperarm_r"), c.phase, 1)
    ha, hp = harmonic(yaw("thigh_l", "thigh_r"), c.phase, 1)
    if sa < 1e-6 or ha < 1e-6:
        return 180.0
    return math.degrees(sp - hp) % 360.0


def own(walk):
    """The clip's own parameters (measure of the walk's source cycle on its own contacts)."""
    kept = getattr(walk, "_gait_own", None)
    if kept is None:
        kept = walk._gait_own = measure(walk, walk.clip.worlds, walk.contact)
    return dict(kept)


def of_result(walk, result):
    """A result's parameters (measure on the result's own contacts). An In place result walks at the speed and the
    step its info keeps: the travel is off its keys, not out of the walk (measured on the keys it read 7.5e-18 m/s,
    2026-10-27)."""
    info = result.info or {}
    out = measure(walk, result.worlds, info.get("contacts") or _contacts_scaled(walk, result.frames))
    if float(info.get("in_place", 0.0) or 0.0) > 0.0:
        if "speed" in info:
            out["speed"] = float(info["speed"])
        if "stride_cm" in info:
            out["step"] = float(info["stride_cm"])
    return out


def _contacts_scaled(walk, n):
    return dict((s, [(a * n / float(walk.P), b * n / float(walk.P)) for a, b in walk.contact.get(s, [])])
                for s in SIDES)


# ---- stored changes, pins, links, macros ----

def stored_change(param, own_value, value):
    """(kind, x) of `value` against the walk's own: ("ratio", value / own) for a size whose own is not quiet,
    else ("offset", value - own)."""
    if param.store(own_value) == "ratio":
        return ("ratio", value / own_value)
    return ("offset", value - own_value)


def apply_change(param, own_value, change):
    """The value a stored change gives on a walk whose own is `own_value`."""
    kind, x = change
    if kind == "ratio":
        if param.store(own_value) == "ratio":
            return own_value * x
        return own_value                    # a ratio on a quiet own moves nothing
    return own_value + x


def own_value(own_values, key):
    """The walk's own value of a key: measured, else the parameter's default."""
    if key in own_values:
        return float(own_values[key])
    p, side = param_of(key)
    if side is not None and p.name in own_values:
        return float(own_values[p.name])
    return float(p.default)


def _weighted(effect, w):
    kind, x = effect
    if w < 0.0:
        w = 0.5 * w                          # light: the reverse, halved
    return ("ratio", x ** w) if kind == "ratio" else ("offset", x * w)


def macro_effects(macros, character=None, strength=1.0):
    """{param: [(kind, x)]} the macros and the character move (Speed is applied in values: it needs the walk)."""
    out = {}
    w = float((macros or {}).get("weight", 0.0) or 0.0)
    if w:
        for name, effect in WEIGHT.items():
            out.setdefault(name, []).append(_weighted(effect, w))
    if character and character in CHARACTER and strength:
        for name, (kind, x) in CHARACTER[character].items():
            out.setdefault(name, []).append(("ratio", x ** strength) if kind == "ratio" else ("offset", x * strength))
    return out


def values(own_values, changes, pins=(), macros=None, character=None, strength=1.0):
    """{key: value}: every parameter's value - the hand's change on the walk's own where there is one, the
    macros and the character on the others, then the physics' links on what nobody set (Arm swing with the
    speed, Push-off and Heel strike with the step)."""
    changes, pins = dict(changes or {}), set(pins or ())
    effects = macro_effects(macros, character, strength)
    out = {}
    for key in keys():
        p, side = param_of(key)
        base = own_value(own_values, key)
        if key in changes:
            out[key] = apply_change(p, base, changes[key])
            continue
        if side is not None and p.name in changes:
            out[key] = apply_change(p, base, changes[p.name])
            continue
        v = base
        for kind, x in effects.get(p.name, ()):
            v = apply_change(p, v, (kind, x)) if kind == "ratio" else v + x
        out[key] = v
    speed = (macros or {}).get("speed")
    own_speed = float(own_values.get("speed", 0.0) or 0.0)
    if speed and own_speed > 0.0:              # the walk's own walk ratio: step and cadence both as the root
        for key, power in (("step", 0.5), ("tempo", -0.5)):
            if key not in changes:
                out[key] = out[key] * (float(speed) / own_speed) ** power
    set_by_hand = lambda key: key in changes or key in pins or (param_of(key)[1] and param_of(key)[0].name in changes)
    step_ratio = out["step"] / own_value(own_values, "step") if own_value(own_values, "step") else 1.0
    tempo_ratio = out["tempo"] / own_value(own_values, "tempo") if own_value(own_values, "tempo") else 1.0
    speed_ratio = step_ratio / tempo_ratio if tempo_ratio else 1.0
    for key in keys():
        p, side = param_of(key)
        if set_by_hand(key) or set_by_hand(p.name):
            continue
        if p.name == "arm_swing":
            out[key] *= min(max(speed_ratio ** ARM_PER_SPEED, ARM_LINK[0]), ARM_LINK[1])
        elif p.name == "push":
            out[key] += PUSH_PER_STEP * max(step_ratio - 1.0, 0.0)
        elif p.name == "heel_strike":
            out[key] += HEEL_PER_STEP * max(step_ratio - 1.0, 0.0)
    for p in PARAMS:                         # a sided parameter's own key: its sides' mean
        if p.sided:
            out[p.name] = 0.5 * (out[p.name + "_l"] + out[p.name + "_r"])
    return out


# ---- onto the engine ----

def _side_value(vals, name, side):
    key = name + "_" + side
    return float(vals[key]) if key in vals else float(vals[name])


def _ratio(asked, base, quiet):
    """asked / base where the base is not quiet, else None."""
    return asked / base if abs(base) >= quiet else None


def engine_knobs(walk, own_values, asked, pins=(), physics=True, lift_scale=None, fps_out=None):
    """maya_walk.model's knobs for the parameters `asked` ({key: value}, a missing key the walk's own) of the walk
    whose own parameters are `own_values`. `pins`: the parameters the animator set (a pinned Sway or Surge holds
    its value, the balance's term on its axis off; a pinned twist holds its degrees at any step). `physics`: Foot
    placement, the balance, the knees' soft limit and Whip's springs as asked - off, the walk's own helpers
    (identity: the own values give the clip back). `fps_out`: frames a second the new cycle's keys land at (the
    scene's rate), which Arm overlap's milliseconds are turned into frames with; None takes the walk's own."""
    pins = set(pins or ())
    get = lambda key: float(asked[key]) if key in asked else own_value(own_values, key)
    own_of = lambda key: own_value(own_values, key)
    e = {"pelvis_twist": walk.own_twist, "pelvis_list": walk.own_list}
    if getattr(walk, "chest_shape", None) is not None:
        e["chest_twist"], e["chest_sway"] = walk.own_chest_twist, walk.own_chest_sway
    # the timing
    stride = get("step") / own_of("step") if own_of("step") else 1.0
    e["stride"] = stride
    tempo = get("tempo")
    frames = int(round(2.0 * walk.strides * tempo))
    if abs(tempo - own_of("tempo")) > 1e-9 and frames != walk.P:
        e["tempo"] = float(max(4, frames))
    n_new = e.get("tempo", float(walk.P))
    step_new = n_new / (2.0 * walk.strides)
    # Main
    if own_of("width") > 1.0 and abs(get("width") - own_of("width")) > 1e-9:
        e["stance"] = get("width") / own_of("width")
    g = _ratio(get("bounce"), own_of("bounce"), QUIET["cm"])
    if g is not None:
        e["g_bob"] = g
    else:
        e["bob_add"] = get("bounce") - own_of("bounce")
    e["bob_shift"] = (get("low_point") - own_of("low_point")) / 100.0 * step_new
    e["lean_add"] = get("lean") - own_of("lean")
    e["detail"] = min(max(get("detail"), 0.0), 1.0)
    # the pelvis
    e["pelvis_height"] = get("height") - own_of("height")
    e["pelvis_forward"] = get("forward") - own_of("forward")
    for name, knob, axis in (("sway", "g_sway", "balance_sway"), ("surge", "g_surge", "balance_surge")):
        g = _ratio(get(name), own_of(name), QUIET["cm"])
        if g is not None and abs(g - 1.0) > 1e-12:
            e[knob] = g
        if name in pins:
            e[axis] = 0.0
    e["double_bounce"] = max(0.0, get("double_bounce") - own_of("double_bounce"))
    gain = walk.twist_gain
    if "hips_twist" in pins and gain > 1e-9:
        e["pelvis_twist"] = get("hips_twist") / (gain * stride)
    elif abs(own_of("hips_twist")) >= QUIET["deg"]:
        e["pelvis_twist"] = walk.own_twist * get("hips_twist") / own_of("hips_twist")
    elif gain > 1e-9:
        e["pelvis_twist"] = walk.own_twist + (get("hips_twist") - own_of("hips_twist")) / (gain * stride)
    e["pelvis_list"] = walk.own_list + (get("hip_drop") - own_of("hip_drop")) / _list_take(walk)
    # the trunk
    if getattr(walk, "chest_shape", None) is not None:
        if "chest_twist" in pins and gain > 1e-9:
            e["chest_twist"] = get("chest_twist") / (gain * stride)
        elif abs(own_of("chest_twist")) >= QUIET["deg"]:
            e["chest_twist"] = walk.own_chest_twist * get("chest_twist") / own_of("chest_twist")
        elif gain > 1e-9:
            e["chest_twist"] = walk.own_chest_twist + (get("chest_twist") - own_of("chest_twist")) / (gain * stride)
        e["chest_sway"] = walk.own_chest_sway + (get("chest_sway") - own_of("chest_sway"))
    e["chest_phase"] = (get("chest_timing") - own_of("chest_timing") + 180.0) % 360.0 - 180.0
    e["chest_bounce_add"] = get("chest_bounce") - own_of("chest_bounce")
    e["torso_lag"] = get("torso_lag")
    e["gait_lean"] = get("gait_lean")
    # the head
    g = _ratio(get("head_motion"), own_of("head_motion"), QUIET["deg"])
    if g is not None:
        e["g_head"] = g
    e["nod_add"] = get("nod")
    e["head_lag"] = get("head_lag")
    e["leg_match"] = get("leg_match")
    # per side: the timing, the legs, the arms
    scale = lift_scale or _lift_scale
    fps = float(fps_out or getattr(walk, "fps", 30.0) or 30.0)
    for s in SIDES:
        sfx = "_" + s
        sv = lambda name: _side_value(asked, name, s) if (name + sfx) in asked or name in asked else own_of(name + sfx)
        so = lambda name: own_of(name + sfx)
        if abs(sv("ground_time") - so("ground_time")) > 1e-9:
            e["duty" + sfx] = min(max(sv("ground_time") / 100.0, 0.01), 0.95)
        e["push" + sfx] = max(0.0, sv("push") - so("push"))
        e["heel_strike" + sfx] = max(0.0, sv("heel_strike") - so("heel_strike"))
        e["slap" + sfx] = (sv("foot_flat") - so("foot_flat")) * walk.P / float(n_new)
        change = sv("foot_lift") - so("foot_lift")
        if abs(change) > 1e-9:
            e["lift" + sfx] = scale(walk.lift_profile(s), change)
        e["toe_add" + sfx] = sv("toe_out") - so("toe_out")
        e["swing_out" + sfx] = sv("swing_out") - so("swing_out")
        knee = sv("knee_bend")
        e["knee_bend" + sfx] = _knee_cap(walk, s, knee) if knee > so("knee_bend") + 0.25 else 0.0
        e["leg_turn" + sfx] = sv("leg_turn")
        e["knee_foot" + sfx] = sv("knee_foot")
        g = _ratio(sv("arm_swing"), so("arm_swing"), ARM_QUIET)
        if g is not None:
            e["g_arm" + sfx] = _solved_gain(walk, "arm", s, sv("arm_swing"), e["detail"], g)
        else:
            e["arm_swing_add" + sfx] = sv("arm_swing") - so("arm_swing")
        e["arm_lag" + sfx] = sv("arm_lag") - so("arm_lag")
        e["arm_overlap" + sfx] = sv("arm_overlap") * fps / 1000.0      # ms -> frames of the new cycle (own 0)
        e["elbow_overlap" + sfx] = sv("elbow_overlap") * fps / 1000.0  # the cascade, on top of that L (own 0)
        e["hand_overlap" + sfx] = sv("hand_overlap") * fps / 1000.0
        e["weapon_overlap" + sfx] = sv("weapon_overlap") * fps / 1000.0   # the weapon's aim, ms -> frames
        e["arm_fwd_add" + sfx] = sv("arms_forward") - so("arms_forward")
        e["arm_out_add" + sfx] = sv("arm_out") - so("arm_out")
        e["elbow_add" + sfx] = _solved_elbow(walk, s, sv("elbow"), sv("elbow") - so("elbow"))
        g = _ratio(sv("elbow_swing"), so("elbow_swing"), ARM_QUIET)
        if g is not None:
            e["g_elbow" + sfx] = _solved_gain(walk, "elbow", s, sv("elbow_swing"), e["detail"], g)
        else:
            e["elbow_swing_add" + sfx] = sv("elbow_swing") - so("elbow_swing")
        e["elbow_lag" + sfx] = sv("elbow_lag") - so("elbow_lag")
        e["hand_lag" + sfx] = sv("hand_lag")
        e["shoulder_add" + sfx] = sv("shoulders")
    # the helpers
    if physics:
        e["foot_placement"] = 1.0 if get("foot_placement") >= 0.5 else 0.0
        e["balance"] = 1.0 if get("balance") >= 0.5 else 0.0
        e["knee_soft"] = KNEE_SOFT
        e["lock_skim"] = 1.0
        e["balance_reach"] = 1.0
        e["double_force"] = 0.0
        e["height_step"] = 0.0 if "step" in pins else 1.0       # Height shortens a step nobody set
        e["root_sway"] = 0.0 if get("root_on_line") >= 0.5 else 1.0
        whip = min(max(get("whip"), 0.0), 1.0)
        on = 1.0 if whip > 0.0 else 0.0
        e.update({"arm_drag": WHIP_DRAG * on, "torso_drag": WHIP_DRAG * on, "head_drag": WHIP_HEAD * on,
                  "arm_bounce": whip, "torso_bounce": (2.0 / 3.0) * whip, "spring_comp": on})
    else:
        e.update({"foot_placement": 0.0, "balance": 0.0, "root_sway": 1.0, "arm_drag": 0.0, "torso_drag": 0.0,
                  "head_drag": 0.0})
    return e


def _swing_of(walk, kind, side, gain, detail):
    """The peak to peak (deg) of an arm's regular swing at a regular gain, from the walk's own series: "arm" the
    upper arm's forward angle (its world turn and the forearm's offset in it), "elbow" the elbow's bend (the
    forearm's local turn and the hand's offset). None where the walk does not decompose that joint."""
    idx = walk.index
    names = ("upperarm_" + side, "lowerarm_" + side, "hand_" + side)
    if not all(n in idx for n in names):
        return None
    up, low, hand = (idx[n] for n in names)
    m = _model()
    if kind == "arm":
        got = walk.decomposed.get(("wlog", up))
        if got is None:
            return None
        reg, res, mean = got
        rot = m.exp_rot(mean + gain * (reg - mean) + detail * res) @ walk.wmean[up]
        a = np.einsum("fi,fij->fj", walk.lt[low], rot)
        y = np.degrees(np.arctan2(a @ np.asarray(walk.ahead), -(a @ np.asarray(walk.up))))
    else:
        got = walk.decomposed.get(("llog", low))
        if got is None:
            return None
        reg, res, mean = got
        local = m.exp_rot(mean + gain * (reg - mean) + detail * res) @ walk.lmean[low]
        b = _unit(np.einsum("fi,fij->fj", walk.lt[hand], local))
        a = _unit(walk.lt[low])
        y = np.degrees(np.arccos(np.clip(np.sum(a * b, axis=1), -1.0, 1.0)))
    _, coef = walk.regular_fit(y)
    fine = walk.__dict__.get("_gait_fine")
    if fine is None:                       # measure's own fine grid (Cycle.FINE a frame)
        fine = walk._gait_fine = walk.harmonic_basis(np.arange(walk.P * Cycle.FINE) / float(Cycle.FINE))
    return float(np.ptp(fine @ coef))


GAIN_SCAN = 37                            # the regular gain's samples from 0 to the engine's most


def _gain_branch(walk, kind, side, detail):
    """(the gains, the swings) of an arm's ("arm") or elbow's ("elbow") regular gain from 0 up its rising branch
    (_swing_of): a wide swing turned further wraps back past its widest. None without the joint."""
    kept = walk.__dict__.setdefault("_gait_gain_branch", {})
    key = (kind, side, round(float(detail), 6))
    if key in kept:
        return kept[key]
    if _swing_of(walk, kind, side, 1.0, detail) is None:
        kept[key] = None
        return None
    top = float(_model().RANGES["g_" + kind][1])            # the engine lets no more through
    gains = sorted(set(np.linspace(0.0, top, GAIN_SCAN).tolist() + [1.0]))
    swings = [_swing_of(walk, kind, side, g, detail) for g in gains]
    end = gains.index(1.0)
    while end + 1 < len(gains) and swings[end + 1] > swings[end]:
        end += 1
    kept[key] = (gains[:end + 1], swings[:end + 1])
    return kept[key]


def _solved_gain(walk, kind, side, asked, detail, guess):
    """The regular gain giving an arm's swing `asked` deg peak to peak (_swing_of, bisected on its rising branch -
    _gain_branch), else `guess`: the engine scales the turn exactly, the angle the animator reads bends with it (a
    run's arm swings back past horizontal and out to its side). Past the branch's widest: its widest."""
    if abs(guess - 1.0) < 1e-12 and detail == 1.0:
        return 1.0                            # the walk's own swing
    kept = walk.__dict__.setdefault("_gait_gains", {})
    key = (kind, side, round(float(asked), 6), round(float(detail), 6))
    if key in kept:
        return kept[key]
    branch = _gain_branch(walk, kind, side, detail)
    if branch is None:
        return guess
    gains, swings = branch
    if asked >= swings[-1]:
        kept[key] = float(gains[-1])
        return kept[key]
    i = int(np.searchsorted(swings, asked))
    if i == 0:
        kept[key] = float(gains[0])
        return kept[key]
    lo, hi = gains[i - 1], gains[i]
    at = lambda g: _swing_of(walk, kind, side, g, detail)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if at(mid) < asked else (lo, mid)
    kept[key] = 0.5 * (lo + hi)
    return kept[key]


def _list_take(walk):
    """How much of the engine's added hip drop the measure reads (deg a deg): the drop turns the pelvis about the
    walk's forward and the hip line, twisted with the step, takes it times the cosine of its turn (dw's 18 deg of
    twist read 0.89 of it). Read off the walk's own hip line, the drop's shape applied as the engine applies it."""
    kept = walk.__dict__.get("_gait_list_take")
    if kept is not None:
        return kept
    idx, m = walk.index, _model()
    take = 1.0
    if "thigh_l" in idx and "thigh_r" in idx:
        P = walk.P
        W = walk.clip.worlds[:, :P]
        d = W[idx["thigh_l"], :, 3, :3] - W[idx["thigh_r"], :, 3, :3]
        up, fwd = np.asarray(walk.up), np.asarray(walk.fwd)
        lists = np.array([walk.list_at(float(t)) for t in range(P)])
        moved = np.array([d[t] @ m.exp_rot(walk.left * math.radians(1.0) * lists[t] * fwd) for t in range(P)])

        def drop(v):
            across = np.linalg.norm(v - np.outer(v @ up, up), axis=1)
            return np.degrees(np.arctan2(v @ up, across))
        y, x = drop(moved) - drop(d), lists - lists.mean()
        y = y - y.mean()
        got = float(np.dot(y, x) / np.dot(x, x)) if float(np.dot(x, x)) > 1e-12 else 1.0
        take = got if 0.3 <= got <= 1.5 else 1.0
    walk._gait_list_take = take
    return take


def _elbow_of(walk, side, add):
    """The mean elbow bend (deg, as measure reads it) of the walk's own arm with `add` deg turned in about the
    engine's hinge (maya_walk.model.Walk.aspect_turns: the forearm's local turned about the hinge in its upper
    arm), or None without the arm."""
    idx, m = walk.index, _model()
    names = ("upperarm_" + side, "lowerarm_" + side, "hand_" + side)
    if not all(n in idx for n in names):
        return None
    up, low, hand = (idx[n] for n in names)
    hinge = getattr(walk, "hinge", {}).get(low)
    if hinge is None:
        return None
    W = walk.clip.worlds[:, :walk.P]
    Ru, Rl = W[up, :, :3, :3], W[low, :, :3, :3]
    a = _unit(W[low, :, 3, :3] - W[up, :, 3, :3])
    turn = m.exp_rot(math.radians(add) * np.asarray(hinge))
    local = np.einsum("fij,fkj->fik", Rl, Ru)                      # the forearm in its upper arm (Rl Ru^T)
    b = _unit(np.einsum("fi,fij->fj", walk.lt[hand], np.einsum("fij,jk,fkl->fil", local, turn, Ru)))
    return float(np.degrees(np.arccos(np.clip(np.sum(a * b, axis=1), -1.0, 1.0))).mean())


ELBOW_STEP = 2.0                          # deg: the Elbow offset's scan for its branch


def _elbow_branch(walk, side):
    """(the offsets, the mean bends) of an arm along the branch its own bend lies on: from the offset that
    straightens it most (a rolled forearm's bend leaves the hinge's plane, so it straightens only so far and then
    bends again) to the engine's most - mean bends rising. None without the arm."""
    kept = walk.__dict__.setdefault("_gait_elbow_branch", {})
    if side in kept:
        return kept[side]
    lo, hi = _model().RANGES["elbow_add"]
    if _elbow_of(walk, side, 0.0) is None:
        kept[side] = None
        return None
    xs = np.arange(0.0, lo - 1e-9, -ELBOW_STEP)[::-1].tolist() + np.arange(ELBOW_STEP, hi + 1e-9, ELBOW_STEP).tolist()
    ys = [_elbow_of(walk, side, x) for x in xs]
    zero = xs.index(0.0)
    start = zero
    while start > 0 and ys[start - 1] < ys[start]:
        start -= 1
    end = zero
    while end + 1 < len(xs) and ys[end + 1] > ys[end]:
        end += 1
    kept[side] = (xs[start:end + 1], ys[start:end + 1])
    return kept[side]


def elbow_reach(walk, side):
    """(the straightest, the most bent) mean bend an arm's Elbow offset gives (deg), or None."""
    branch = _elbow_branch(walk, side)
    return None if branch is None else (float(branch[1][0]), float(branch[1][-1]))


def _solved_elbow(walk, side, asked, guess):
    """The engine's Elbow offset (deg) that gives the mean bend `asked` on the walk's own arm (_elbow_of,
    bisected on its branch - _elbow_branch): a bend measured off the hinge's plane (a rolled forearm) takes less
    than the degrees asked, and straightens only so far. Past the branch's end its end; `guess` without the arm
    or with nothing asked."""
    if abs(guess) < 1e-9:
        return 0.0
    branch = _elbow_branch(walk, side)
    if branch is None:
        return guess
    xs, ys = branch
    if asked <= ys[0]:
        return float(xs[0])
    if asked >= ys[-1]:
        return float(xs[-1])
    i = int(np.searchsorted(ys, asked))
    a, b = xs[i - 1], xs[i]
    for _ in range(30):
        mid = 0.5 * (a + b)
        a, b = (mid, b) if _elbow_of(walk, side, mid) < asked else (a, mid)
    return 0.5 * (a + b)


def swing_reach(walk, kind, side):
    """The widest swing (deg, peak to peak) an arm's ("arm") or elbow's ("elbow") regular gain gives on the walk's
    own series (its rising branch's end) - or None."""
    branch = _gain_branch(walk, kind, side, 1.0)
    return None if branch is None else float(branch[1][-1])


def lift_floor(walk, side):
    """The lowest Foot lift (cm) the swing can take: its path's highest point with the engine's lift at 0 (the
    straight blend between the prints - an uneven walk's floating prints hold it up)."""
    profile = walk.lift_profile(side) if hasattr(walk, "lift_profile") else None
    if not profile:
        return 0.0
    return max(0.0, float(max(h - over for h, over in profile)))


def _knee_cap(walk, side, bend):
    """The engine's knee cap that leaves a planted knee bent `bend` degrees: the legs held their margin
    (maya_walk.model LEG_MARGIN) short of the cap once they fall short, so the cap a little straighter."""
    parts = getattr(walk, "leg_parts", {}).get(side)
    margin = getattr(_model(), "LEG_MARGIN", 0.0)
    if not parts or margin <= 0.0:
        return bend
    l1, l2 = parts
    length = lambda deg: math.sqrt(l1 * l1 + l2 * l2 + 2.0 * l1 * l2 * math.cos(math.radians(deg)))
    want = length(bend) / (1.0 - margin)
    if want >= l1 + l2:
        return 0.0
    cos = (want * want - l1 * l1 - l2 * l2) / (2.0 * l1 * l2)
    return math.degrees(math.acos(min(max(cos, -1.0), 1.0)))


def _model():
    from . import model
    return model


def _lift_scale(profile, change):
    """The engine's lift L that raises the swing's highest point `change` cm (maya_walk.model.Walk.lift_profile:
    each swinging frame at h + (L - 1) . lift_up over the ground) - bisected."""
    if not profile or abs(change) < 1e-9:
        return 1.0
    h = np.array([p[0] for p in profile])
    over = np.array([p[1] for p in profile])
    asked = float(h.max()) + change

    def at(L):
        return float((h + (L - 1.0) * over).max())
    top = float(_model().RANGES["lift"][1])                  # the engine lets no more through
    if change > 0.0:
        lo, hi = 1.0, 2.0
        while at(hi) < asked and hi < top:
            lo, hi = hi, min(2.0 * hi, top)
    else:
        if at(0.0) > asked:
            return 0.0
        lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if at(mid) < asked else (lo, mid)
    return 0.5 * (lo + hi)


STEP_SINK = 0.08                          # the Step's range ends where its geometry alone sinks the hips this share
#                                           of the leg at the double support (a lunge, and its knee clicks)


def step_top(own_values, leg):
    """The longest step whose double support the legs span with the hips sunk at most STEP_SINK of the leg: the
    clip's legs reach sqrt(h^2 + (s / 2)^2) there (h the pelvis over the feet, s the step); None without them."""
    h, s = own_value(own_values, "height"), own_value(own_values, "step")
    if h <= 1.0 or s <= 1.0 or leg <= 1.0:
        return None
    reach = math.hypot(h, 0.5 * s)
    low = h - STEP_SINK * leg
    return 2.0 * math.sqrt(max(reach * reach - low * low, 0.0)) if low > 0.0 else None


FLAT_REACH = 0.5                          # Foot flat comes within this share of the foot's shortest contact
REACHED = ("foot_lift", "elbow", "elbow_swing", "arm_swing", "foot_flat")    # what a walk's body bounds


def reach(walk, key):
    """(low, high) a walk's own body reaches for the parameter key `key`, None where it sets no bound: Foot lift
    no lower than its swing takes (lift_floor), the Elbow no straighter than its hinge brings it nor more bent
    than the engine turns it (elbow_reach), the arm's and the elbow's swing no wider than their gain turns them
    (swing_reach), Foot flat within FLAT_REACH of the foot's shortest contact. A two-sided parameter's own key:
    its sides' mean."""
    p, side = param_of(key)
    if p.name not in REACHED:
        return None, None
    if side is None and p.sided:
        got = [reach(walk, p.name + "_" + s) for s in SIDES]
        mean = lambda i: (sum(g[i] for g in got) / 2.0) if all(g[i] is not None for g in got) else None
        return mean(0), mean(1)
    if p.name == "foot_lift":
        return lift_floor(walk, side), None
    if p.name == "elbow":
        return elbow_reach(walk, side) or (None, None)
    if p.name in ("elbow_swing", "arm_swing"):
        return None, swing_reach(walk, "arm" if p.name == "arm_swing" else "elbow", side)
    contact = (getattr(walk, "contact", {}) or {}).get(side)
    return None, (FLAT_REACH * min(b - a for a, b in contact) if contact else None)


def overlap_cap(walk):
    """How far Arm overlap's slider reaches either way (ms): half the walk's own cycle - past half a cycle a
    lag of a periodic signal comes back on itself - never under OVERLAP_FLOOR nor over OVERLAP_MAX."""
    fps = float(getattr(walk, "fps", 30.0) or 30.0)
    half = 1000.0 * float(getattr(walk, "P", 0) or 0) / fps / 2.0
    return float(min(OVERLAP_MAX, max(OVERLAP_FLOOR, half)))


def ranges(own_values, leg, walk=None):
    """{key: (low, high)}: each parameter's range from the walk's own value and its leg - a two-sided one's own
    keys from each side's own value, its own key from their mean; with the `walk`, no further than its body
    reaches (Foot lift no lower than its swing takes, the Elbow no straighter than its hinge brings it, the arm's
    and the elbow's swing no wider than their gain turns them, Foot flat within half the foot's shortest
    contact) and Arm overlap half the cycle either way."""
    out = {}
    for p in PARAMS:
        if p.kind == "toggle":
            rng = (0.0, 1.0)
        else:
            rng = p.rule(own_value(own_values, p.name), leg)
        out[p.name] = (float(min(rng)), float(max(rng)))
        if p.sided:
            for s in SIDES:
                rng = (0.0, 1.0) if p.kind == "toggle" else p.rule(own_value(own_values, p.name + "_" + s), leg)
                out[p.name + "_" + s] = (float(min(rng)), float(max(rng)))
    if walk is not None:              # what the walk's own body reaches: each side's, the sides' mean
        for name in REACHED:
            for key in [name + "_" + s for s in SIDES] + [name]:
                lo, hi = out[key]
                a, b = reach(walk, key)
                lo = max(lo, a) if a is not None else lo
                hi = min(hi, b) if b is not None else hi
                out[key] = (min(lo, hi), hi)
        cap = overlap_cap(walk)       # Arm overlap, its cascade and the weapon's: half the cycle either way
        for name in ("arm_overlap", "elbow_overlap", "hand_overlap", "weapon_overlap"):
            for key in [name + "_" + s for s in SIDES] + [name]:
                out[key] = (-cap, cap)
    top = step_top(own_values, leg)
    if top is not None:
        lo, hi = out["step"]
        own_step = own_value(own_values, "step")
        out["step"] = (lo, max(min(hi, top), 1.05 * own_step))
    return out


# ---- the Diagnosis ----

class Finding(object):
    """One line of the Diagnosis: its key, the text (the number and the guide's norm) and the fix ({key:
    value}, visible parameters, set pinned)."""

    def __init__(self, key, text, fix):
        self.key, self.text, self.fix = key, text, dict(fix)

    def __repr__(self):
        return "Finding(%r, %r, %r)" % (self.key, self.text, self.fix)


FROUDE_MIN_SPEED = 0.1    # m/s: under it a body stands rather than walks, and Fr^-0.2 runs away (110 million frames)


def froude_tempo(leg, fps, speed):
    """The guide's step time for a body of leg length `leg` (cm) at `speed` (m/s), frames:
    1.15 . f . sqrt(h / g) . Fr^-0.2; 0 for a body under FROUDE_MIN_SPEED."""
    if leg <= 0.0 or speed < FROUDE_MIN_SPEED:
        return 0.0
    h = leg / 100.0
    fr = speed * speed / (9.81 * h)
    return FROUDE_TEMPO * fps * math.sqrt(h / 9.81) * fr ** -0.2


def is_run(measured):
    """A run: each foot down under half a stride (both feet up at a handoff)."""
    return float(measured.get("ground_time", 60.0)) < 50.0


def diagnose(measured, own_values=None, info=None, run=None, leg=0.0, fps=30.0):
    """The Diagnosis of a cycle measured `measured` (its result's `info` for the physics): [Finding]."""
    m, info = measured, info or {}
    run = is_run(m) if run is None else run
    out = []
    if not run:
        lags = [m.get("arm_lag_l", 0.0), m.get("arm_lag_r", 0.0)]
        if max(abs(x) for x in lags) < 1.0:
            out.append(Finding("arms_in_step", "Arms in step with the legs: arm lag %.1f fr (a walk's: 2-5)"
                               % max(lags, key=abs), {"arm_lag": 3.0}))
        if m.get("head_motion", 0.0) > 5.0:
            out.append(Finding("head_pecks", "The head pecks: it pitches %.1f deg a step (steady under 5)"
                               % m["head_motion"], {"head_motion": 0.5 * m["head_motion"]}))
        if m.get("bounce", 0.0) < 2.0:
            out.append(Finding("flat", "A flat path: the pelvis bobs %.1f cm (a walk's: 3-6)" % m.get("bounce", 0.0),
                               {"bounce": 4.0}))
        if (m.get("chest_timing", 180.0) % 360.0) < 90.0 or (m.get("chest_timing", 180.0) % 360.0) > 270.0:
            out.append(Finding("chest_with_hips", "The chest turns with the hips: %.0f deg of phase (against "
                               "them: ~150)" % m["chest_timing"], {"chest_timing": 150.0}))
        speed = m.get("speed", 0.0)
        norm = froude_tempo(leg, fps, speed)
        if norm > 0.0 and abs(m.get("tempo", norm) - norm) > 0.4 * norm:
            out.append(Finding("tempo_size", "The tempo is not the body's: %.1f fr a step, %.1f for its size"
                               % (m["tempo"], norm), {"tempo": round(norm, 1)}))
    pushes = [m.get("push_l", 0.0), m.get("push_r", 0.0)]
    if min(pushes) < 10.0:
        out.append(Finding("no_push", "No push-off: the heel up %.0f deg at the toe-off (over 10)" % min(pushes),
                           {"push": max(20.0, max(pushes))}))
    sw = [m.get("arm_swing_l", 0.0), m.get("arm_swing_r", 0.0)]
    al = [m.get("arm_lag_l", 0.0), m.get("arm_lag_r", 0.0)]
    if max(sw) > 2.0 and abs(sw[0] - sw[1]) <= 0.01 * max(sw) and abs(al[0] - al[1]) < 0.1:
        out.append(Finding("mirror", "The second step is an exact mirror: both arms swing %.1f deg" % sw[0],
                           {"arm_swing_l": sw[0] * 1.03, "arm_swing_r": sw[1] * 0.97,
                            "arm_lag_l": al[0] + 0.5, "arm_lag_r": al[1] - 0.5}))
    if m.get("hips_twist", 0.0) < -1.0:
        out.append(Finding("hips_reversed", "The hips turn the wrong way: %.1f deg (toward the trailing leg)"
                           % m["hips_twist"], {"hips_twist": abs(m["hips_twist"])}))
    lowered = float(info.get("lowered", 0.0) or 0.0)
    if lowered > 2.0:
        out.append(Finding("physics", "Physics gave way: the pelvis lowered %.1f cm for the legs' reach - the "
                           "step, the ground time or the height asked more than the legs reach" % lowered, {}))
    knees = [m.get("knee_bend_l", 90.0), m.get("knee_bend_r", 90.0)]
    if min(knees) < 5.0:
        out.append(Finding("straight_knee", "A planted knee within %.1f deg of straight (a click waits there)"
                           % min(knees), {"knee_bend": 6.0}))
    if float(info.get("short", 0.0) or 0.0) > 0.5:
        out.append(Finding("foot_short", "A planted foot falls %.1f cm short of its print" % info["short"], {}))
    return out


# ---- from the old knobs ----

LEGACY_RATIOS = (("stride", "step"), ("bob", "bounce"), ("sway", "sway"), ("surge", "surge"), ("head", "head_motion"),
                 ("stance", "width"), ("lift", "foot_lift"))


def from_legacy(walk, knobs, own_values=None):
    """(changes, pins, macros) of a version 2 memo's knobs (maya_walk.model's legacy knobs): the step, the
    bounce, the sway and surge, the head, the width and the foot lift as ratios; the tempo, the twists and the
    chest in their units; overlap as the arm lag (its upper arm's share); the drags as Whip; the weight as the
    Weight macro; the rest as they are. Only the knobs the memo holds."""
    own_values = own_values if own_values is not None else own(walk)
    changes, pins, macros = {}, set(), {}

    def put(key, change):
        changes[key] = change
        pins.add(key)
    for knob, name in LEGACY_RATIOS:
        for key, sfx in ((knob, ""), (knob + "_l", "_l"), (knob + "_r", "_r")):
            if key in knobs and abs(float(knobs[key]) - 1.0) > 1e-12:
                if sfx and not P[name].sided:
                    continue
                p = P[name]
                base = own_value(own_values, name + sfx)
                put(name + sfx, ("ratio", float(knobs[key])) if p.store(base) == "ratio"
                    else ("offset", 0.0))
    for knob, name in (("arms", "arm_swing"), ("elbow", "elbow_swing")):
        for key, sfx in ((knob, ""), (knob + "_l", "_l"), (knob + "_r", "_r")):
            if key in knobs and abs(float(knobs[key]) - 1.0) > 1e-12:
                put(name + sfx, ("ratio", float(knobs[key])))
    if float(knobs.get("tempo", 0.0) or 0.0) > 0.0:
        put("tempo", ("ratio", float(knobs["tempo"]) / float(walk.P)))
    stride = float(knobs.get("stride", 1.0))
    gain = walk.twist_gain
    for knob, name, own_knob in (("pelvis_twist", "hips_twist", walk.own_twist),
                                 ("chest_twist", "chest_twist", getattr(walk, "own_chest_twist", 0.0))):
        if knob in knobs and abs(float(knobs[knob]) - own_knob) > 1e-9:
            put(name, ("offset", gain * stride * float(knobs[knob]) - own_value(own_values, name)))
    for knob, name, own_knob in (("pelvis_list", "hip_drop", walk.own_list),
                                 ("chest_sway", "chest_sway", getattr(walk, "own_chest_sway", 0.0))):
        if knob in knobs and abs(float(knobs[knob]) - own_knob) > 1e-9:
            put(name, ("offset", float(knobs[knob]) - own_knob))
    if float(knobs.get("overlap", 0.0) or 0.0):
        put("arm_lag", ("offset", 0.8 * float(knobs["overlap"])))   # the upper arm's share of Overlap
    for knob, name in (("pelvis_height", "height"), ("pelvis_forward", "forward")):
        if float(knobs.get(knob, 0.0) or 0.0):
            put(name, ("offset", float(knobs[knob])))
    for knob, name in (("swing_out", "swing_out"),):
        for key, sfx in ((knob, ""), (knob + "_l", "_l"), (knob + "_r", "_r")):
            if float(knobs.get(key, 0.0) or 0.0):
                put(name + sfx, ("offset", float(knobs[key])))
    for knob in ("leg_match", "gait_lean"):
        if knob in knobs and float(knobs[knob]) != P[knob].default:
            put(knob, ("offset", float(knobs[knob]) - P[knob].default))
    for knob in ("leg_turn", "knee_foot"):
        for key in (knob, knob + "_l", knob + "_r"):
            if key in knobs and float(knobs[key]) != P[knob].default:
                put(key, ("offset", float(knobs[key]) - P[knob].default))
    for knob, name in (("foot_placement", "foot_placement"), ("balance", "balance")):
        if knob in knobs and float(knobs[knob]) < 0.5:
            put(name, ("offset", -1.0))
    if "root_sway" in knobs and float(knobs["root_sway"]) >= 0.5:
        put("root_on_line", ("offset", -1.0))
    drags = [float(knobs.get(k, 0.0) or 0.0) for k in ("arm_drag", "torso_drag", "head_drag")
             if k in knobs]
    if drags and max(drags) <= 1e-9:
        put("whip", ("offset", -P["whip"].default))
    elif "arm_bounce" in knobs and abs(float(knobs["arm_bounce"]) - P["whip"].default) > 1e-9:
        put("whip", ("offset", float(knobs["arm_bounce"]) - P["whip"].default))
    if float(knobs.get("weight", 0.0) or 0.0):
        macros["weight"] = float(knobs["weight"])
    return changes, pins, macros
