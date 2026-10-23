"""Our CAT: a walk / run cycle synthesised from parameters on any UE-convention skeleton.

numpy only (a test pins it). The scene half is skeldar_cat.py; the design is
docs/superpowers/specs/2026-10-23-catwalk-design.md.

Matrices are Maya's: 4x4, row vectors (a point is `p @ M`), rows 0..2 the axes, row 3 the place.
A rotation applied in WORLD axes at a joint's own pivot is a column-form 3x3 `Q`
(`v' = Q v`): the joint's rows become `R @ Q.T`.

The character frame is read off the rest: up +Y, `left` the thighs' flat difference,
`fwd = left x up`. Lengths in the knobs are shares of the leg (thigh + calf, CATMotion's CATUnits),
angles are degrees, times frames, phases shares of the cycle (one cycle = two steps)."""

import math

import numpy as np

UP = np.array([0.0, 1.0, 0.0])

# (name, default, low, high, group, label)
KNOBS = (
    ("step_time", 16.0, 4.0, 60.0, "Timing", "Step time, fr"),
    ("stride", 0.78, 0.0, 2.5, "Timing", "Stride, x leg"),
    ("direction", 0.0, -180.0, 180.0, "Timing", "Direction, deg"),
    ("gradient", 0.0, -30.0, 30.0, "Timing", "Gradient, deg"),
    ("on_spot", 0.0, 0.0, 1.0, "Timing", "On spot"),
    ("cycle_offset", 0.0, -60.0, 60.0, "Timing", "Cycle offset, fr"),
    ("duty", 0.62, 0.2, 0.85, "Feet", "Ground time"),
    ("lift", 0.13, 0.0, 0.6, "Feet", "Foot lift, x leg"),
    ("lift_peak", 0.35, 0.1, 0.9, "Feet", "Lift peak"),
    ("lift_late", 0.0, -0.1, 0.4, "Feet", "Late lift, x leg"),
    ("step_shape", 0.5, -1.0, 1.0, "Feet", "Step shape (- fast start, + ease)"),
    ("foot_push", 0.0, -0.2, 0.3, "Feet", "Foot push, x leg"),
    ("swerve", 0.0, -0.15, 0.15, "Feet", "Swerve, x leg"),
    ("stance", 1.0, 0.0, 2.5, "Feet", "Stance width, x"),
    ("toe_out", 6.0, -20.0, 40.0, "Feet", "Toe out, deg"),
    ("heel_strike", 18.0, 0.0, 45.0, "Feet", "Heel strike, deg"),
    ("toe_off", 30.0, 0.0, 70.0, "Feet", "Toe off, deg"),
    ("toe_hold", 0.6, 0.2, 0.95, "Feet", "Heel-up hold, swing"),
    ("swing_toes", 0.0, -20.0, 50.0, "Feet", "Toes up late swing, deg"),
    ("swing_reach", 0.0, -0.1, 0.4, "Feet", "Reach past the print, x leg"),
    ("stance_center", 0.5, 0.15, 0.85, "Feet", "Under the hip at, stance"),
    ("foot_height", 0.0, -0.08, 0.08, "Feet", "Foot height, x leg"),
    ("crouch", 0.03, -0.1, 0.4, "Pelvis", "Crouch, x leg"),
    ("bob", 0.025, 0.0, 0.12, "Pelvis", "Bob (lift), x leg"),
    ("bob_phase", 0.12, 0.0, 1.0, "Pelvis", "Bob low point, step"),
    ("push", 0.01, -0.06, 0.06, "Pelvis", "Push, x leg"),
    ("weight_shift", 0.025, -0.1, 0.1, "Pelvis", "Weight shift, x leg"),
    ("twist", 6.0, -30.0, 30.0, "Pelvis", "Twist, deg"),
    ("roll", 4.0, -20.0, 20.0, "Pelvis", "Roll, deg"),
    ("lean", 3.0, -30.0, 45.0, "Pelvis", "Lean, deg"),
    ("pitch", 1.0, -10.0, 10.0, "Pelvis", "Pitch, deg"),
    ("knee_drive", 0.0, 0.0, 1.0, "Knees", "Pelvis from knees (retarget)"),
    ("knee_plant", 25.0, 0.0, 90.0, "Knees", "Knee at plant, deg"),
    ("knee_load", 30.0, 0.0, 90.0, "Knees", "Knee at load, deg"),
    ("knee_mid", 15.0, 0.0, 90.0, "Knees", "Knee mid-stance, deg"),
    ("knee_lift", 40.0, 0.0, 120.0, "Knees", "Knee at lift, deg"),
    ("swing_knee", 0.0, 0.0, 60.0, "Knees", "Knee before the strike, deg"),
    ("counter", 0.8, 0.0, 2.0, "Spine & Head", "Chest counter-twist"),
    ("roll_cancel", 1.0, 0.0, 1.5, "Spine & Head", "Shoulders level"),
    ("spine_lean", 2.0, -30.0, 45.0, "Spine & Head", "Spine lean, deg"),
    ("head_stabilize", 0.8, 0.0, 1.0, "Spine & Head", "Head stabilize"),
    ("nod", 0.0, -30.0, 30.0, "Spine & Head", "Head nod, deg"),
    ("arm_out", 10.0, 0.0, 60.0, "Arms", "Arm out, deg"),
    ("swing", 20.0, 0.0, 70.0, "Arms", "Swing, deg"),
    ("arm_forward", 0.0, -40.0, 40.0, "Arms", "Arms forward, deg"),
    ("cross_swing", 8.0, -30.0, 30.0, "Arms", "Cross swing, deg"),
    ("arm_lag", 0.05, -0.25, 0.25, "Arms", "Arm lag"),
    ("elbow", 15.0, 0.0, 140.0, "Arms", "Elbow, deg"),
    ("elbow_swing", 15.0, 0.0, 60.0, "Arms", "Elbow swing, deg"),
    ("clavicle", 3.0, 0.0, 20.0, "Arms", "Clavicle, deg"),
    ("hand_flop", 8.0, 0.0, 40.0, "Arms", "Hand flop, deg"),
    ("forearm_in", 0.0, -40.0, 60.0, "Arms", "Forearms in, deg"),
    ("hand_bend", 0.0, -60.0, 60.0, "Arms", "Wrist bend, deg"),
    ("knuckle_curl", 0.0, -30.0, 90.0, "Fingers", "Knuckles curl, deg"),
    ("finger_curl", 0.0, -30.0, 110.0, "Fingers", "Fingers curl, deg"),
    ("tip_curl", 0.0, -30.0, 90.0, "Fingers", "Tips curl, deg"),
    ("curl_fan", 0.0, -1.0, 1.0, "Fingers", "More toward the pinky"),
    ("finger_flop", 0.0, 0.0, 30.0, "Fingers", "Fingers flop, deg"),
    ("thumb_01", 0.0, -60.0, 60.0, "Fingers", "Thumb base, deg"),
    ("thumb_02", 0.0, -60.0, 60.0, "Fingers", "Thumb curl, deg"),
    ("shoulders", 0.0, -30.0, 30.0, "Posture", "Shoulders up, deg"),
    ("bend_spine_01", 0.0, -40.0, 40.0, "Posture", "Spine 1 bend, deg"),
    ("bend_spine_02", 0.0, -40.0, 40.0, "Posture", "Spine 2 bend, deg"),
    ("bend_spine_03", 0.0, -40.0, 40.0, "Posture", "Spine 3 bend, deg"),
    ("bend_spine_04", 0.0, -40.0, 40.0, "Posture", "Spine 4 bend, deg"),
    ("bend_spine_05", 0.0, -40.0, 40.0, "Posture", "Spine 5 bend, deg"),
    ("bend_neck", 0.0, -40.0, 40.0, "Posture", "Neck bend, deg"),
    ("phase_l", 0.0, -0.25, 0.25, "Phases", "Left leg phase"),
    ("phase_r", 0.0, -0.25, 0.25, "Phases", "Right leg phase"),
)
DEFAULTS = dict((k[0], k[1]) for k in KNOBS)
RANGES = dict((k[0], (k[2], k[3])) for k in KNOBS)
GROUPS = []
for _k in KNOBS:
    if _k[4] not in GROUPS:
        GROUPS.append(_k[4])

# a preset: the knobs it changes, its step time in SECONDS (turned into frames at the scene's rate)
PRESETS = {
    # the default walk: catmatch.fit on the animator's reference walk (2026-10-23; 31 frames at 30 fps, 87 cm a
    # step, its posture), the pelvis by crouch / bob / bob_phase and the knees by IK, the reference's place on the
    # scene left out; fitted with the ground time 0.52 and the legs in even phase (the reference's 0.4923 and
    # -0.0161 have both feet down only by half a frame of rounding, and a frame in the air at 60 fps)
    "Walk": {"step_s": 0.5167, "stride": 1.0123, "duty": 0.52, "lift": 0.0628, "lift_peak": 0.2541,
             "lift_late": 0.0143, "step_shape": 0.1989, "foot_push": 0.0, "swerve": 0.0, "stance": 0.5849,
             "toe_out": -5.8526, "heel_strike": 1.0025, "toe_off": 61.1942, "toe_hold": 0.7301, "swing_toes": 32.9958,
             "swing_reach": 0.3934, "stance_center": 0.3915, "foot_height": 0.0209, "crouch": 0.0407, "bob": 0.0415,
             "bob_phase": 0.9514, "push": 0.0123, "weight_shift": 0.0246, "twist": 5.8784, "roll": 1.2013,
             "lean": -1.9094, "pitch": 0.4878, "knee_drive": 0.0, "knee_plant": 32.5394, "knee_load": 34.6189,
             "knee_mid": 16.952, "knee_lift": 39.9946, "swing_knee": 12.2372, "counter": 0.5464,
             "roll_cancel": 0.9618, "spine_lean": 0.0, "head_stabilize": 0.8, "nod": 5.9234, "arm_out": 15.6903,
             "swing": 21.9548, "arm_forward": -7.644, "cross_swing": 8.0, "arm_lag": -0.0388, "elbow": 21.5249,
             "elbow_swing": 28.3598, "clavicle": 3.0, "hand_flop": 8.0, "forearm_in": 11.0282, "hand_bend": 6.5959,
             "knuckle_curl": 21.8283, "finger_curl": 55.7345, "tip_curl": 0.0, "curl_fan": 0.1588,
             "finger_flop": 7.0263, "thumb_01": 16.2089, "thumb_02": -11.8245, "shoulders": -8.3901,
             "bend_spine_01": -12.3424, "bend_spine_02": 0.0, "bend_spine_03": 17.1067, "bend_spine_04": 0.0,
             "bend_spine_05": 12.8231, "bend_neck": -7.8304, "phase_l": 0.0, "phase_r": 0.0},
    "Jog": {"step_s": 0.38, "stride": 1.0, "duty": 0.42, "lift": 0.22, "lift_peak": 0.4, "step_shape": 0.3,
            "crouch": 0.06, "bob": 0.03, "bob_phase": 0.42, "weight_shift": 0.012, "twist": 8.0, "roll": 3.0,
            "lean": 7.0, "pitch": 1.5, "counter": 1.0, "spine_lean": 4.0, "heel_strike": 10.0, "toe_off": 38.0,
            "arm_out": 12.0, "swing": 32.0, "cross_swing": 12.0, "elbow": 70.0, "clavicle": 4.0},
    "Run": {"step_s": 0.32, "stride": 1.4, "duty": 0.34, "lift": 0.32, "lift_peak": 0.45, "step_shape": 0.15,
            "crouch": 0.08, "bob": 0.035, "bob_phase": 0.34, "push": 0.015, "weight_shift": 0.008, "twist": 10.0,
            "roll": 2.0, "lean": 12.0, "pitch": 2.0, "counter": 1.1, "spine_lean": 6.0, "heel_strike": 6.0,
            "toe_off": 45.0, "arm_out": 14.0, "swing": 45.0, "cross_swing": 15.0, "elbow": 85.0, "clavicle": 6.0,
            "hand_flop": 6.0},
    "Sneak": {"step_s": 0.75, "stride": 0.55, "duty": 0.72, "lift": 0.10, "lift_peak": 0.3, "step_shape": 0.8,
              "crouch": 0.18, "bob": 0.012, "bob_phase": 0.2, "twist": 4.0, "roll": 2.0, "lean": 14.0,
              "counter": 0.5, "spine_lean": 12.0, "head_stabilize": 1.0, "nod": -10.0, "heel_strike": 8.0,
              "toe_off": 20.0, "arm_out": 22.0, "swing": 8.0, "elbow": 50.0, "elbow_swing": 8.0},
    "Strafe L": {"step_s": 0.5, "direction": 90.0, "stride": 0.5, "stance": 1.3, "twist": 2.0, "swing": 8.0,
                 "heel_strike": 6.0, "toe_off": 18.0},
    "Strafe R": {"step_s": 0.5, "direction": -90.0, "stride": 0.5, "stance": 1.3, "twist": 2.0, "swing": 8.0,
                 "heel_strike": 6.0, "toe_off": 18.0},
    "Backward": {"step_s": 0.6, "direction": 180.0, "stride": 0.55, "lean": -1.0, "heel_strike": 2.0,
                 "toe_off": 12.0, "swing": 14.0},
}
PRESET_ORDER = ("Walk", "Jog", "Run", "Sneak", "Strafe L", "Strafe R", "Backward")

REACH = 0.99        # a leg is held this share of its length short of straight
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
FAN = {"index": -1.0, "middle": -1.0 / 3.0, "ring": 1.0 / 3.0, "pinky": 1.0}     # where a finger stands in the fan
ARM_ROLES = ("clavicle", "upperarm", "lowerarm", "hand")
LEG_ROLES = ("thigh", "calf", "foot", "ball")
SIDES = (("l", 1.0), ("r", -1.0))


def knobs(given=None):
    """The defaults with `given` over them, each held inside its range; an unknown name raises."""
    out = dict(DEFAULTS)
    for name, value in (given or {}).items():
        if name not in DEFAULTS:
            raise KeyError("unknown knob %r" % name)
        lo, hi = RANGES[name]
        out[name] = min(hi, max(lo, float(value)))
    return out


def preset(name, fps):
    """The knobs of a preset at `fps` frames a second."""
    data = dict(PRESETS[name])
    seconds = data.pop("step_s", 0.53)
    data["step_time"] = max(4.0, round(seconds * fps * 2.0) / 2.0)      # a cycle (two steps) of whole frames
    return knobs(data)


# ---- small algebra ----

def unit(v):
    v = np.asarray(v, dtype=float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v * 0.0


def flat(v):
    v = np.asarray(v, dtype=float)
    return v - UP * float(np.dot(v, UP))


def rot(axis, degrees):
    """Column-form rotation about `axis` (right-handed), Rodrigues."""
    a = unit(axis)
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    x, y, z = a
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def between(a, b):
    """The least rotation (column form) taking direction `a` onto `b`."""
    a, b = unit(a), unit(b)
    axis = np.cross(a, b)
    s = float(np.linalg.norm(axis))
    c = float(np.dot(a, b))
    if s < 1e-9:
        if c > 0:
            return np.eye(3)
        other = np.cross(a, [1.0, 0.0, 0.0])
        if np.linalg.norm(other) < 1e-6:
            other = np.cross(a, [0.0, 0.0, 1.0])
        return rot(other, 180.0)
    return rot(axis, math.degrees(math.atan2(s, c)))


def scaled(q, share):
    """The rotation `q` taken `share` of the way from the identity (its angle scaled)."""
    angle = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(q) - 1.0) / 2.0))))
    if angle < 1e-7:
        return np.eye(3)
    axis = np.array([q[2, 1] - q[1, 2], q[0, 2] - q[2, 0], q[1, 0] - q[0, 1]])
    if np.linalg.norm(axis) < 1e-9:          # a half turn: any perpendicular axis of its fixed line
        w, v = np.linalg.eigh((q + q.T) / 2.0)
        axis = v[:, int(np.argmax(w))]
    return rot(axis, angle * share)


def turned(m, q):
    """The 4x4 `m` turned by the world rotation `q` about its own place."""
    out = m.copy()
    out[:3, :3] = m[:3, :3] @ q.T
    return out


def smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def wrap(x):
    return x - math.floor(x)


# ---- the skeleton ----

class Skeleton(object):
    """The rest of a skeleton and its roles.

    `bones` {leaf: {"parent": leaf or None, "canonical": name or "", "rest": 16 floats (world)}}.
    Roles are read by canonical name (Unreal's: pelvis, spine_01.., thigh_l..), else by leaf."""

    def __init__(self, bones):
        self.bones = bones
        self.rest = dict((leaf, np.array(b["rest"], dtype=float).reshape(4, 4)) for leaf, b in bones.items())
        self.parent = dict((leaf, b.get("parent") if b.get("parent") in bones else None) for leaf, b in bones.items())
        depth = {}

        def deep(leaf):
            if leaf not in depth:
                p = self.parent[leaf]
                depth[leaf] = 0 if p is None else deep(p) + 1
            return depth[leaf]

        self.order = sorted(bones, key=lambda leaf: (deep(leaf), leaf))
        self.local = {}
        for leaf in self.order:
            p = self.parent[leaf]
            self.local[leaf] = self.rest[leaf] if p is None else self.rest[leaf] @ np.linalg.inv(self.rest[p])
        by_name = {}
        for leaf, b in bones.items():
            by_name.setdefault((b.get("canonical") or "").lower() or leaf.lower(), leaf)
            by_name.setdefault(leaf.lower(), leaf)
        self.by_name = by_name
        missing = [n for n in ("pelvis", "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r")
                   if n not in by_name]
        if missing:
            raise ValueError("not a skeleton this tool knows: no %s" % ", ".join(missing))
        self.spine = [by_name[n] for n in sorted(by_name) if n.startswith("spine_")]
        self.head = by_name.get("head")
        self.neck = by_name.get("neck_01")
        self.canonical = dict((leaf, (b.get("canonical") or leaf).lower()) for leaf, b in bones.items())
        # the phalanges: {leaf: (finger, joint 1..3, side)} (metacarpals are not curled)
        self.fingers = {}
        for leaf, name in self.canonical.items():
            parts = name.split("_")
            if (len(parts) == 3 and parts[0] in FINGERS and parts[1] in ("01", "02", "03")
                    and parts[2] in ("l", "r")):
                self.fingers[leaf] = (parts[0], int(parts[1]), parts[2])
        self.root = by_name.get("root")
        self.pelvis = by_name["pelvis"]
        self.legs, self.arms = {}, {}
        for side, _ in SIDES:
            self.legs[side] = dict((r, by_name.get("%s_%s" % (r, side))) for r in LEG_ROLES)
            arm = dict((r, by_name.get("%s_%s" % (r, side))) for r in ARM_ROLES)
            self.arms[side] = arm if arm["upperarm"] and arm["lowerarm"] and arm["hand"] else None
        pos = dict((leaf, m[3, :3]) for leaf, m in self.rest.items())
        self.pos = pos
        self.left = unit(flat(pos[self.legs["l"]["thigh"]] - pos[self.legs["r"]["thigh"]]))
        self.fwd = unit(np.cross(self.left, UP))
        self.lengths = {}
        for side, _ in SIDES:
            leg = self.legs[side]
            self.lengths[side] = (float(np.linalg.norm(pos[leg["calf"]] - pos[leg["thigh"]])),
                                  float(np.linalg.norm(pos[leg["foot"]] - pos[leg["calf"]])))
        self.leg = sum(a + b for a, b in self.lengths.values()) / 2.0
        feet = [pos[self.legs[s]["ball"] or self.legs[s]["foot"]][1] for s, _ in SIDES]
        if self.root is not None and pos[self.root][1] <= min(feet) + 1e-6:
            self.ground = float(pos[self.root][1])
        else:
            self.ground = float(min(feet) - 0.04 * self.leg)
        # helpers standing on a body bone at rest keep that relation
        self.helpers = {}
        body = [l for l in self.order if not l.lower().startswith(("ik_", "weapon", "camera", "interaction",
                                                                    "center_of_mass"))]
        for leaf in self.order:
            if not leaf.lower().startswith("ik_"):
                continue
            near = [b for b in body if np.linalg.norm(pos[b] - pos[leaf]) < 1.0]
            if near:
                carrier = max(near, key=lambda b: (b.startswith(("hand", "foot")), -len(b)))
                self.helpers[leaf] = (carrier, self.rest[leaf] @ np.linalg.inv(self.rest[carrier]))

    @classmethod
    def from_template(cls, joints):
        """From the plugin's skeleton template ({name: {"parent", "world_matrix"}})."""
        return cls(dict((n, {"parent": j.get("parent"), "canonical": n, "rest": j["world_matrix"]})
                        for n, j in joints.items()))


# ---- the cycle ----

def _lift_shape(w, peak):
    k = math.log(0.5) / math.log(min(0.95, max(0.05, peak)))
    return math.sin(math.pi * (w ** k))


def step_progress(w, shape):
    """How far a swinging foot has gone (0..1) at swing share `w`: `shape` > 0 eases in and out
    (CAT's StepShape), < 0 starts fast and settles (the foot thrown forward off the toes)."""
    if shape >= 0:
        return (1.0 - shape) * w + shape * smoothstep(w)
    return (1.0 + shape) * w - shape * (1.0 - (1.0 - w) ** 2)


def foot_pitch(t, duty, heel_strike, toe_off, hold=0.6, toes=0.0):
    """The foot's pitch (degrees, toes up +) at leg phase `t`; its stance is [0, duty). In the swing the
    heel-up lets go over `hold` of it and the toes come up by `toes` before the strike."""
    if t < duty:
        s = t / duty
        if s < 0.18:
            return heel_strike * (1.0 - smoothstep(s / 0.18))
        if s > 0.55:
            return -toe_off * smoothstep((s - 0.55) / 0.45)
        return 0.0
    w = (t - duty) / (1.0 - duty)
    late = 0.0 if w <= 0.35 else math.sin(math.pi * (w - 0.35) / 0.65)
    return (-toe_off * (1.0 - smoothstep(w / hold)) + heel_strike * smoothstep((w - 0.4) / 0.6)
            + toes * late)


KNEE_KNOTS = ((0.0, "knee_plant"), (0.2, "knee_load"), (0.55, "knee_mid"), (1.0, "knee_lift"))


def knee_target(k, s):
    """The planted knee's flexion (degrees) at stance share `s`, through the four knee knobs."""
    for (s0, a), (s1, b) in zip(KNEE_KNOTS, KNEE_KNOTS[1:]):
        if s <= s1:
            return k[a] + (k[b] - k[a]) * smoothstep((s - s0) / (s1 - s0))
    return k[KNEE_KNOTS[-1][1]]


def _knee_lift(skel, k, plans, shares, T):
    """How far up (cm, a frame) the pelvis goes so the planted knee bends as the knee knobs say (x knee_drive):
    each planted leg's hip height for its target flexion, the planting leg first, frames with no foot down
    filled in between, then cut to the cycle's low harmonics - at a contact the planting leg takes over within
    a frame, and its height is no jolt of the body's."""
    if k["knee_drive"] <= 0:
        return [0.0] * T
    want = []
    for f in range(T):
        total, weight = 0.0, 0.0
        for side, _ in SIDES:
            s = shares[f][side]
            if s is None:
                continue
            hip, ankle = plans[f][3][side][0], plans[f][3][side][1]
            l1, l2 = skel.lengths[side]
            theta = math.radians(knee_target(k, s))
            reach = math.sqrt(l1 * l1 + l2 * l2 + 2 * l1 * l2 * math.cos(theta))
            h = float(np.linalg.norm(flat(ankle - hip)))
            y = ankle[1] + math.sqrt(reach * reach - h * h) if h < reach else ankle[1]
            # CAT's LegWeight: with both feet down the planting leg has the priority
            w = max(1e-4, 1.0 - s) ** 8
            total += w * (y - hip[1])
            weight += w
        want.append(total / weight if weight > 0 else None)
    known = [i for i, v in enumerate(want) if v is not None]
    if not known:
        return [0.0] * T
    filled = []
    for i in range(T):
        if want[i] is not None:
            filled.append(want[i])
            continue
        before = max([j for j in known if j < i], default=known[-1] - T)
        after = min([j for j in known if j > i], default=known[0] + T)
        a, b = want[before % T], want[after % T]
        t = (i - before) / float(after - before)
        filled.append(a + (b - a) * smoothstep(t))
    smooth = _low_pass(filled)
    return [k["knee_drive"] * v for v in smooth]


def _blur(values, sigma):
    n = len(values)
    radius = int(3 * sigma) + 1
    weights = [math.exp(-0.5 * (i / sigma) ** 2) for i in range(-radius, radius + 1)]
    total = sum(weights)
    return [sum(w * values[(i + j - radius) % n] for j, w in enumerate(weights)) / total for i in range(n)]


# the harmonics of the cycle a body's height may carry: kept whole up to the 2nd (one bob a step), faded
# out by the 5th
BOB_KEEP, BOB_GONE = 2.0, 5.0


def _low_pass(values, keep=BOB_KEEP, gone=BOB_GONE):
    """A periodic curve cut to its low harmonics (of the whole cycle, so at any frame rate): harmonic k kept
    whole up to `keep`, faded out with a raised cosine by `gone`."""
    spec = np.fft.rfft(np.asarray(values, dtype=float))
    for i in range(1, len(spec)):
        if i >= gone:
            spec[i] = 0.0
        elif i > keep:
            spec[i] *= 0.5 * (1.0 + math.cos(math.pi * (i - keep) / (gone - keep)))
    return [float(v) for v in np.fft.irfft(spec, len(values))]


def _cover(need, sigma):
    """A smooth periodic curve over `need` (never under it), local: a deficit is spread over its own
    neighbourhood (max-filtered, then blurred), never over the whole cycle."""
    n = len(need)
    if n == 0 or max(need) <= 0.0:
        return [0.0] * n
    if sigma <= 0:
        return list(need)
    reach = max(1, int(round(sigma)))
    out = [0.0] * n
    for _ in range(12):
        deficit = [max(0.0, need[i] - out[i]) for i in range(n)]
        if max(deficit) < 1e-4:
            break
        wide = [max(deficit[(i + j) % n] for j in range(-reach, reach + 1)) for i in range(n)]
        add = _blur(wide, sigma)
        out = [out[i] + add[i] for i in range(n)]
    return [max(out[i], need[i]) for i in range(n)]


class Cycle(object):
    """What `generate` answers: `frames` [{leaf: 4x4}] for frames 0..T (T = two steps), the travel of a
    cycle, and the numbers the status line says."""

    def __init__(self, frames, travel, info):
        self.frames = frames
        self.travel = travel
        self.info = info


def generate(skel, given=None, fps=30.0, place=None):
    """The cycle of `skel` under the knobs `given` (see KNOBS). `place` (4x4, rows) carries the whole
    result to where the character stands (applied last)."""
    k = knobs(given)
    L = skel.leg
    T = max(8, int(round(2 * k["step_time"])))
    stride = k["stride"] * L
    duty = k["duty"]
    grad = math.radians(k["gradient"])
    direction = rot(UP, k["direction"]) @ skel.fwd
    v = 2.0 * stride / T                                     # along the slope, a frame
    step_h = direction * v * math.cos(grad)
    step_v = UP * v * math.sin(grad)
    fwd, left = skel.fwd, skel.left
    phases = {"l": wrap(0.0 + k["phase_l"]), "r": wrap(0.5 + k["phase_r"])}
    pelvis0 = skel.rest[skel.pelvis]
    centre = flat(pelvis0[3, :3])
    normal = UP * math.cos(grad) - direction * math.sin(grad)
    slope = between(UP, normal)

    def travel(f):
        return step_h * f + step_v * f

    def ground_at(point):
        return skel.ground + math.tan(grad) * float(np.dot(flat(point) - centre, direction))

    feet = {}
    for side, sign in SIDES:
        leg = skel.legs[side]
        a0 = skel.pos[leg["foot"]].copy()
        lateral = float(np.dot(flat(a0) - centre, left))
        a_lay = a0 + left * lateral * (k["stance"] - 1.0)
        yaw = rot(UP, sign * k["toe_out"])
        ball0 = skel.pos[leg["ball"]] if leg["ball"] else a0 + fwd * 0.12 * L
        heel = np.array([a0[0], skel.ground, a0[2]])
        ball_ground = np.array(ball0, dtype=float)      # the toes roll about the ball joint itself
        feet[side] = dict(a0=a0, a_lay=a_lay, yaw=yaw, plat=slope @ yaw, heel=heel, ball=ball_ground,
                          height=float(a0[1] - skel.ground), lateral=unit(left * lateral) if abs(lateral) > 1e-6
                          else left * sign)

    def footprint(side, index):
        info = feet[side]
        mid = (index + phases[side] + duty * k["stance_center"]) * T
        place_ = info["a_lay"] + travel(mid)
        place_[1] = ground_at(place_) + info["height"] + k["foot_height"] * L
        return place_

    def platform(side, f):
        """(B: where the flat ankle stands, pitch degrees, stance?, swing share or None)."""
        u = f / float(T)
        t_raw = u - phases[side]
        index = math.floor(t_raw)
        t = t_raw - index
        a = foot_pitch(t, duty, k["heel_strike"], k["toe_off"], k["toe_hold"], k["swing_toes"])
        if t < duty:
            return footprint(side, index), a, True, None
        w = (t - duty) / (1.0 - duty)
        b0, b1 = footprint(side, index), footprint(side, index + 1)
        h = step_progress(w, k["step_shape"])
        bump = math.sin(math.pi * w)
        b = (b0 + (b1 - b0) * h + UP * k["lift"] * L * _lift_shape(w, k["lift_peak"])
             + direction * k["foot_push"] * L * bump + feet[side]["lateral"] * k["swerve"] * L * bump
             + direction * k["swing_reach"] * L * _lift_shape(w, 0.7)
             + UP * k["lift_late"] * L * _lift_shape(w, 0.85))
        return b, a, False, w

    def foot_pose(side, b, a, w):
        """(ankle place, foot rotation Q, ball rotation Q) of a foot whose flat ankle stands at `b`."""
        info = feet[side]
        plat = info["plat"]

        def carried(p):
            return plat @ (p - info["a0"]) + b

        axis = plat @ left
        pitch = rot(axis, -a)
        pivot = carried(info["heel"]) if a > 0 else carried(info["ball"])
        ankle = pivot + pitch @ (carried(info["a0"]) - pivot)
        if a > 0:
            toe = a
        elif w is None:
            toe = 0.0
        else:
            toe = a * smoothstep(w / 0.5)
        return ankle, pitch @ plat, rot(axis, -toe) @ plat

    def pelvis_motion(f):
        u = f / float(T)
        q = wrap(2.0 * u)
        pl = phases["l"]
        bob = -k["bob"] * L * math.cos(2 * math.pi * (q - k["bob_phase"]))
        push = k["push"] * L * math.sin(2 * math.pi * (q - k["bob_phase"]))
        shift = k["weight_shift"] * L * math.cos(2 * math.pi * (u - pl - duty / 2.0))
        twist = -k["twist"] * math.cos(2 * math.pi * (u - pl))
        roll = k["roll"] * math.cos(2 * math.pi * (u - pl - duty / 2.0))
        osc = k["pitch"] * math.cos(2 * math.pi * (q - k["bob_phase"]))
        place_ = (pelvis0[3, :3] + travel(f) + UP * (bob - k["crouch"] * L) + direction * push + left * shift)
        q_rot = rot(UP, twist) @ rot(fwd, roll) @ rot(left, k["lean"] + osc)
        return place_, q_rot, dict(twist=twist, roll=roll, osc=osc)

    # pass 1: where the hips are with no drop
    plans, stance_share = [], []
    for f in range(T):
        place_, q_rot, motion = pelvis_motion(f)
        pw = turned(pelvis0, q_rot)
        pw[3, :3] = place_
        legs, shares = {}, {}
        for side, _ in SIDES:
            leg = skel.legs[side]
            hip = (skel.rest[leg["thigh"]] @ np.linalg.inv(pelvis0) @ pw)[3, :3]
            b, a, stance, w = platform(side, f)
            ankle, qf, qb = foot_pose(side, b, a, w)
            legs[side] = (hip, ankle, qf, qb, stance)
            shares[side] = wrap(f / float(T) - phases[side]) / duty if stance else None
        plans.append((place_, q_rot, motion, legs))
        stance_share.append(shares)
    # the pelvis set by the planted legs' knee angles (CAT's retargeting), then lowered where a planted
    # leg still falls short
    lift = _knee_lift(skel, k, plans, stance_share, T)
    need = []
    for f in range(T):
        most = 0.0
        for side, _ in SIDES:
            hip, ankle, _, _, stance = plans[f][3][side]
            # a planted foot must be reached; so must one about to land (the last quarter of its swing)
            swing_w = (wrap(f / float(T) - phases[side]) - duty) / (1.0 - duty)
            weight = 1.0 if stance else smoothstep((swing_w - 0.75) / 0.25)
            reach = REACH * sum(skel.lengths[side])
            r = ankle - (hip + UP * lift[f])
            if weight > 0 and np.linalg.norm(r) > reach:
                ru = float(np.dot(r, UP))
                disc = ru * ru - float(np.dot(r, r)) + reach * reach
                most = max(most, weight * (-ru - math.sqrt(disc) if disc >= 0 else -ru))
        need.append(most)
    drop = _cover(need, T / 16.0)
    rise = [lift[f] - drop[f] for f in range(T)]          # the pelvis's vertical move a frame
    # a swinging foot further from its hip than a knee bent by `swing_knee` allows is drawn in toward the
    # hip (smoothly, and less and less toward the strike, where it must land on its print)
    reel = dict((side, [0.0] * T) for side, _ in SIDES)
    if k["swing_knee"] > 0:
        for side, _ in SIDES:
            l1, l2 = skel.lengths[side]
            bend = math.radians(k["swing_knee"])
            room = math.sqrt(l1 * l1 + l2 * l2 + 2 * l1 * l2 * math.cos(bend))
            excess = []
            for f in range(T):
                hip, ankle, _, _, stance = plans[f][3][side]
                gap = float(np.linalg.norm(ankle - (hip + UP * rise[f]))) - room
                excess.append(0.0 if stance else max(0.0, gap))
            covered = _cover(excess, max(1.0, T / 24.0))
            for f in range(T):
                if plans[f][3][side][4]:
                    continue
                swing_w = (wrap(f / float(T) - phases[side]) - duty) / (1.0 - duty)
                reel[side][f] = covered[f] * (1.0 - smoothstep((swing_w - 0.8) / 0.2))

    # pass 2: the whole skeleton by FK, the overrides at their bones
    frames, flight, double = [], 0, 0
    for f in range(T + 1):
        place_, q_rot, motion, legs = plans[f % T]
        shift = travel(f) - travel(f % T)
        place_ = place_ + shift + UP * rise[f % T]
        world, scratch = {}, {}
        stances = sum(1 for side, _ in SIDES if legs[side][4])
        if f < T:
            flight += stances == 0
            double += stances == 2
        u = f / float(T)
        for leaf in skel.order:
            p = skel.parent[leaf]
            m = skel.local[leaf] @ world[p] if p is not None else skel.rest[leaf].copy()
            if leaf == skel.root:
                m = skel.rest[leaf].copy()
                m[3, :3] = m[3, :3] + travel(f)
            elif leaf == skel.pelvis:
                m = turned(pelvis0, q_rot)
                m[3, :3] = place_
            elif leaf in skel.spine:
                n = float(len(skel.spine))
                bend = k.get("bend_" + skel.canonical.get(leaf, ""), 0.0)
                m = turned(m, rot(UP, -(1.0 + k["counter"]) * motion["twist"] / n)
                           @ rot(fwd, -k["roll_cancel"] * motion["roll"] / n)
                           @ rot(left, (k["spine_lean"] - motion["osc"]) / n + bend))
            elif leaf == skel.neck and k["bend_neck"]:
                m = turned(m, rot(left, k["bend_neck"]))
            elif leaf == skel.head and k["head_stabilize"] > 0:
                target = turned(skel.rest[leaf], rot(left, k["nod"]))
                q = target[:3, :3].T @ m[:3, :3]
                m = turned(m, scaled(q, k["head_stabilize"]))
            m = _leg_override(skel, leaf, m, scratch, legs, shift,
                              dict((side, reel[side][f % T]) for side, _ in SIDES))
            m = _arm_override(skel, k, leaf, m, world, scratch, u, phases)
            if leaf in skel.fingers:
                m = curled(m, finger_curl(k, skel.fingers[leaf], u, phases))
            if leaf in skel.helpers:
                carrier, rel = skel.helpers[leaf]
                if carrier in world:
                    m = rel @ world[carrier]
            world[leaf] = m
        frames.append(world)
    if k["on_spot"] >= 0.5:
        for f, world in enumerate(frames):
            back = travel(f)
            for m in world.values():
                m[3, :3] -= back
    offset = int(round(k["cycle_offset"])) % T
    if offset:
        # the cycle started `offset` frames later (CAT's Start): frame f plays the cycle's frame f + offset,
        # moved back so the character still starts where it stands
        whole = travel(T) if k["on_spot"] < 0.5 else np.zeros(3)
        start = travel(offset) if k["on_spot"] < 0.5 else np.zeros(3)
        shifted = []
        for f in range(T + 1):
            g = f + offset
            move = whole * (g // T) - start
            world = {}
            for leaf, m in frames[g % T].items():
                m = m.copy()
                m[3, :3] += move
                world[leaf] = m
            shifted.append(world)
        frames = shifted
    if place is not None:
        for world in frames:
            for leaf in list(world):
                world[leaf] = world[leaf] @ place
    cycle_travel = np.zeros(3) if k["on_spot"] >= 0.5 else travel(T)
    seconds = T / float(fps)
    info = dict(frames=T, speed=0.0 if seconds <= 0 else float(np.linalg.norm(travel(T))) / seconds,
                stride=stride, drop=max(drop) if drop else 0.0, flight=flight, double=double,
                leg=L)
    return Cycle(frames, cycle_travel, info)


def _leg_override(skel, leaf, m, world, legs, shift, reel=None):
    for side, sign in SIDES:
        leg = skel.legs[side]
        if leaf not in (leg["thigh"], leg["calf"], leg["foot"], leg["ball"]):
            continue
        hip0, ankle, qf, qb, stance = legs[side]
        ankle = ankle + shift
        l1, l2 = skel.lengths[side]
        if leaf == leg["thigh"]:
            hip = m[3, :3]
            pull = (reel or {}).get(side, 0.0)
            if pull > 0:
                ankle = ankle + unit(hip - ankle) * pull
            knee, ankle_ = _two_bone(hip, ankle, l1, l2, _hint(skel, sign, qf))
            world["_knee_" + side] = knee
            world["_ankle_" + side] = ankle_
            return _aimed(skel, leaf, leg["calf"], m, knee - hip, _hint(skel, sign, qf))
        if leaf == leg["calf"]:
            knee = world["_knee_" + side]
            return _aimed(skel, leaf, leg["foot"], m, world["_ankle_" + side] - knee, _hint(skel, sign, qf))
        if leaf == leg["foot"]:
            out = m.copy()
            out[:3, :3] = skel.rest[leaf][:3, :3] @ qf.T
            return out
        if leaf == leg["ball"]:
            out = m.copy()
            out[:3, :3] = skel.rest[leaf][:3, :3] @ qb.T
            return out
    return m


def _hint(skel, sign, qf):
    """Where the knee points: the foot's forward, flattened."""
    h = flat(qf @ skel.fwd)
    return unit(h) if np.linalg.norm(h) > 1e-6 else skel.fwd


def _aimed(skel, leaf, child, m, direction, hint):
    """The bone `leaf` (its FK world `m`) turned so its child lies along `direction`, its bend plane
    turned with the hint: the rest's (bone, hint) frame carried onto the new one."""
    a0 = unit(skel.pos[child] - skel.pos[leaf])
    n0 = unit(np.cross(a0, skel.fwd))
    if np.linalg.norm(n0) < 1e-6:
        n0 = unit(np.cross(a0, skel.left))
    a = unit(direction)
    n = unit(np.cross(a, hint))
    if np.linalg.norm(n) < 1e-6:
        n = n0
    f0 = np.column_stack([a0, n0, np.cross(a0, n0)])
    f1 = np.column_stack([a, n, np.cross(a, n)])
    q = f1 @ f0.T
    out = m.copy()
    out[:3, :3] = skel.rest[leaf][:3, :3] @ q.T
    return out


def _two_bone(hip, target, l1, l2, hint):
    """(knee, ankle) of a two-bone chain reaching for `target`, bent toward `hint`."""
    r = target - hip
    d = float(np.linalg.norm(r))
    d = min(max(d, abs(l1 - l2) + 1e-4), (l1 + l2) * 0.99999)
    a = unit(r)
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
    perp = unit(hint - a * float(np.dot(hint, a)))
    knee = hip + a * l1 * cos_a + perp * l1 * sin_a
    return knee, hip + a * d


def finger_curl(k, finger, u, phases):
    """A phalanx's curl (degrees about its own Z, inward on both UE hands - CAT's DigitCurl): the knuckle,
    middle and tip curls, more toward the pinky by `curl_fan`, the thumb by its own two knobs; the finger
    joints flop with their arm's swing."""
    name, joint, side = finger
    if name == "thumb":
        return {1: k["thumb_01"], 2: k["thumb_02"]}.get(joint, 0.0)
    base = {1: k["knuckle_curl"], 2: k["finger_curl"], 3: k["tip_curl"]}[joint]
    base *= 1.0 + k["curl_fan"] * FAN[name]
    if k["finger_flop"] and joint in (1, 2):
        other = "r" if side == "l" else "l"
        base += k["finger_flop"] * math.cos(2 * math.pi * (u - phases[other] - k["arm_lag"] - 0.25))
    return base


def curled(m, degrees):
    """The bone `m` turned about its own Z by `degrees`, at its own place."""
    if not degrees:
        return m
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    out = m.copy()
    out[:3, :3] = np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]]) @ m[:3, :3]
    return out


def _arm_override(skel, k, leaf, m, world, scratch, u, phases):
    for side, sign in SIDES:
        arm = skel.arms[side]
        if arm is None or leaf not in arm.values():
            continue
        other = "r" if side == "l" else "l"
        ph = phases[other] + k["arm_lag"]
        forward = math.cos(2 * math.pi * (u - ph))
        cross_axis = rot(UP, -sign * k["cross_swing"]) @ skel.left
        if leaf == arm["clavicle"]:
            return turned(m, rot(UP, -sign * k["clavicle"] * forward) @ rot(skel.fwd, sign * k["shoulders"]))
        if leaf == arm["upperarm"]:
            low = (skel.local[arm["lowerarm"]] @ m)[3, :3]
            down = rot(skel.fwd, sign * k["arm_out"]) @ (-UP)
            target = rot(cross_axis, -(k["swing"] * forward + k["arm_forward"])) @ down
            out = turned(m, between(low - m[3, :3], target))
            scratch["upper_" + side] = target
            return out
        if leaf == arm["lowerarm"]:
            hand = (skel.local[arm["hand"]] @ m)[3, :3]
            upper = scratch.get("upper_" + side, unit(m[3, :3] - world[arm["upperarm"]][3, :3]))
            inward = rot(upper, sign * k["forearm_in"])
            hinge = inward @ unit(cross_axis - upper * float(np.dot(cross_axis, upper)))
            bend = k["elbow"] + k["elbow_swing"] * (forward + 1.0) / 2.0
            target = rot(hinge, -bend) @ upper
            scratch["hinge_" + side] = hinge
            return turned(m, between(hand - m[3, :3], target))
        if leaf == arm["hand"]:
            hinge = scratch.get("hinge_" + side, skel.left)
            flop = k["hand_flop"] * math.cos(2 * math.pi * (u - ph - 0.15))
            return turned(m, rot(hinge, -(flop + k["hand_bend"])))
    return m
