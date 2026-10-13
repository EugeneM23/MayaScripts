"""Camera Shake - handheld filming and an impact, keyed on an animation layer of their own.

Select a camera (nothing selected: our SceneSetup_camera when there is exactly one), highlight a stretch of
the time slider, set the controls and press Apply:
- Handheld: an operator holding the camera - a slow sway, the hands' tremor, a little drift.
- Impact: a jolt from a chosen side, a spring back with an overshoot and a fine rattle, still by the end.
Every press is an additive layer of its own (its weight is a strength dial, Mute turns it off); after Apply
a released slider re-keys that shake. docs/superpowers/specs/2026-10-13-camera-shake-design.md.

Drop this file into a Maya viewport to open the window, or exec it in the Script Editor.
"""

import json
import math
import sys

import numpy as np

try:
    import maya.cmds as cmds
except ImportError:          # the model and the algebra are tested without Maya
    cmds = None

# ---------------------------------------------------------------------------------------------------------
# 1. The model (numpy)
# ---------------------------------------------------------------------------------------------------------

VERSION = 1
MODES = ("handheld", "impact")
DIRECTIONS = ("Random", "Below", "Above", "Left", "Right", "Front")

# (name, label, default, low, high)
CONTROLS = {
    "handheld": (
        ("sway", "Sway, deg", 1.0, 0.0, 6.0),
        ("speed", "Speed", 1.0, 0.25, 4.0),
        ("jitter", "Jitter, deg", 0.12, 0.0, 1.5),
        ("roll", "Roll", 0.4, 0.0, 1.0),
        ("drift", "Drift, cm", 1.5, 0.0, 15.0),
        ("ease", "Ease, fr", 6.0, 0.0, 60.0),
    ),
    "impact": (
        ("strength", "Strength, deg", 4.0, 0.0, 25.0),
        ("push", "Push, cm", 2.0, 0.0, 30.0),
        ("swing", "Swing, fr", 4.0, 1.0, 20.0),
        ("bounce", "Bounce", 0.5, 0.0, 1.0),
        ("rattle", "Rattle, deg", 1.0, 0.0, 6.0),
        ("roll", "Roll", 0.4, 0.0, 1.0),
        ("length", "Length, fr", 24.0, 2.0, 240.0),
    ),
}
PRESETS = {
    "handheld": (
        ("Calm", {"sway": 0.4, "speed": 0.6, "jitter": 0.05, "roll": 0.3, "drift": 0.6}),
        ("Handheld", {"sway": 1.0, "speed": 1.0, "jitter": 0.12, "roll": 0.4, "drift": 1.5}),
        ("Nervous", {"sway": 1.8, "speed": 1.8, "jitter": 0.3, "roll": 0.5, "drift": 3.0}),
    ),
    "impact": (
        ("Light", {"strength": 2.0, "push": 1.0, "swing": 3.0, "bounce": 0.5, "rattle": 0.6, "roll": 0.4}),
        ("Hit", {"strength": 4.0, "push": 2.0, "swing": 4.0, "bounce": 0.5, "rattle": 1.0, "roll": 0.4}),
        ("Heavy", {"strength": 6.0, "push": 4.0, "swing": 4.0, "bounce": 0.55, "rattle": 1.6, "roll": 0.5}),
        ("Explosion", {"strength": 9.0, "push": 8.0, "swing": 6.0, "bounce": 0.4, "rattle": 3.0,
                       "roll": 0.6, "direction": "Below"}),
        ("Recoil", {"strength": 3.0, "push": 2.0, "swing": 3.0, "bounce": 0.3, "rattle": 0.4,
                    "roll": 0.2, "direction": "Front"}),
    ),
}
DEFAULT_PRESET = {"handheld": "Handheld", "impact": "Hit"}


def settings(mode, given=None):
    """The mode's controls, defaults filled in and each clamped to its range; plus the seed (an int, 0 or
    more) and, for an impact, the direction."""
    given = given or {}
    out = {}
    for name, _, default, low, high in CONTROLS[mode]:
        value = given.get(name)
        try:
            value = float(default if value is None else value)
        except (TypeError, ValueError):
            value = float(default)
        out[name] = min(high, max(low, value))
    try:
        out["seed"] = max(0, int(given.get("seed", 1)))
    except (TypeError, ValueError):
        out["seed"] = 1
    if mode == "impact":
        direction = given.get("direction", "Random")
        out["direction"] = direction if direction in DIRECTIONS else "Random"
    return out


def preset(mode, name, current=None):
    """`current` with the preset's values on top: the seed, Ease and Length are kept, and an impact's
    direction too unless the preset names one."""
    values = dict(current or {})
    for label, table in PRESETS[mode]:
        if label == name:
            values.update(table)
            return settings(mode, values)
    raise ValueError("no %s preset %r" % (mode, name))


NYQUIST_SHARE = 0.42   # every frequency stays below this share of the frame rate
BLOCK = 64             # knots come in blocks, each from a generator seeded by its index


def capped(hz, fps):
    """A frequency the frame rate can show: above ~half of it a shake aliases into a slow wobble."""
    return min(float(hz), NYQUIST_SHARE * float(fps))


def _basis(frac):
    """The uniform cubic B-spline's weights of the four knots around each fraction: (n, 4)."""
    t = np.asarray(frac, float)
    t2 = t * t
    t3 = t2 * t
    return np.stack([(1.0 - t) ** 3, 3.0 * t3 - 6.0 * t2 + 4.0, -3.0 * t3 + 3.0 * t2 + 3.0 * t + 1.0, t3],
                    axis=-1) / 6.0


def _mean_variance():
    weights = _basis(np.linspace(0.0, 1.0, 4000, endpoint=False))
    return float(np.mean(np.sum(weights * weights, axis=1)))


MEAN_VARIANCE = _mean_variance()   # of a spline through unit Gaussian knots, over a knot interval


def _knots(seed, stream, first, last):
    """Knot values first..last (inclusive), the same whatever range asks for them."""
    low, high = first // BLOCK, last // BLOCK
    values = np.concatenate([
        np.random.default_rng([int(seed), int(stream), block + 2 ** 20]).standard_normal(BLOCK)
        for block in range(low, high + 1)])
    return values[first - low * BLOCK: last - low * BLOCK + 1]


KNOTS_PER_CYCLE = 5.57  # measured: a spline through white knots crosses zero 0.359 times a knot


def noise(seconds, seed, stream, hz):
    """A smooth random signal of unit RMS swinging about `hz` times a second (2 hz zero crossings, as a
    sine): Gaussian knots through a cubic B-spline (C2, no overshoot). Still when hz is 0."""
    s = np.atleast_1d(np.asarray(seconds, float))
    if hz <= 0.0 or s.size == 0:
        return np.zeros_like(s)
    u = s * float(hz) * KNOTS_PER_CYCLE
    i = np.floor(u).astype(int)
    first = int(i.min()) - 1
    knots = _knots(seed, stream, first, int(i.max()) + 2)
    index = (i - 1 - first)[:, None] + np.arange(4)[None, :]
    return np.sum(_basis(u - i) * knots[index], axis=1) / math.sqrt(MEAN_VARIANCE)


def fractal(seconds, seed, stream, hz, octaves, gain=0.5, fps=None):
    """Octaves of `noise` at hz x 2^k with amplitude gain^k, back to unit RMS; capped by the frame rate."""
    s = np.atleast_1d(np.asarray(seconds, float))
    total = np.zeros_like(s)
    norm = 0.0
    for k in range(octaves):
        rate = hz * 2.0 ** k
        if fps:
            rate = capped(rate, fps)
        amplitude = gain ** k
        total += amplitude * noise(s, seed, stream * 16 + k, rate)
        norm += amplitude * amplitude
    return total / math.sqrt(norm) if norm else total


def smootherstep(x):
    """0 below 0, 1 above 1, C2 between."""
    x = np.clip(np.asarray(x, float), 0.0, 1.0)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def eased(frames, a, b, ease):
    """1 inside, rising from 0 at a over `ease` frames and falling back to 0 at b; ease 0 is 1 throughout."""
    f = np.asarray(frames, float)
    if ease <= 0.0:
        return np.ones_like(f)
    span = min(float(ease), (b - a) / 2.0)
    return smootherstep((f - a) / span) * smootherstep((b - f) / span)


def _streams(index):
    """Each camera of a press has its own noise."""
    return 1000 * int(index)


SWAY_HZ = 0.25           # the body's drift and the hands' corrections, x Speed
JITTER_HZ = 7.0          # the hands' tremor, x sqrt(Speed)
DRIFT_HZ = 0.2           # the camera's own travel, x Speed
SWAY_AXES = (0.75, 1.0, 1.0)     # tilt, pan, roll (roll x Roll): an operator aims better up-down
DRIFT_AXES = (0.7, 1.0, 0.4)     # side, bob, push


def handheld(frames, a, b, fps, s, index=0):
    """An operator holding the camera: (rotation (n, 3) deg about the camera's X, Y, Z - tilt, pan, roll;
    offset (n, 3) cm along them - side, bob, push) on each frame of a..b."""
    f = np.asarray(frames, float)
    sec = (f - a) / float(fps)
    seed, k = s["seed"], _streams(index)
    speed = s["speed"]
    sway_hz = capped(SWAY_HZ * speed, fps)
    jitter_hz = capped(JITTER_HZ * math.sqrt(speed), fps)
    drift_hz = capped(DRIFT_HZ * speed, fps)
    roll = (1.0, 1.0, s["roll"])
    rot = np.zeros((len(f), 3))
    off = np.zeros((len(f), 3))
    for axis in range(3):
        sway = SWAY_AXES[axis] * 0.5 * s["sway"] * fractal(sec, seed, k + axis + 1, sway_hz, 3, fps=fps)
        jitter = 0.5 * s["jitter"] * noise(sec, seed, k + axis + 4, jitter_hz)
        rot[:, axis] = roll[axis] * (sway + jitter)
        off[:, axis] = DRIFT_AXES[axis] * 0.5 * s["drift"] * fractal(sec, seed, k + axis + 7, drift_hz, 2,
                                                                       fps=fps)
    envelope = eased(f, a, b, s["ease"])[:, None]
    return rot * envelope, off * envelope


RATTLE_HZ = 11.0         # the rattle's top octave, below the frame rate's limit
WOBBLE_RATE = 1.37       # the perpendicular wobble against the kick
WOBBLE_SHARE = 0.25
HITS = {"Below": (0.0, 1.0, 0.0), "Above": (0.0, -1.0, 0.0), "Left": (1.0, 0.0, 0.0),
        "Right": (-1.0, 0.0, 0.0), "Front": (0.0, 0.0, 1.0)}


def hit_vector(direction, seed, index=0):
    """Where the camera is knocked TO, in its own axes (x right, y up, z back): away from the hit.
    Random is a seeded direction in the picture's plane."""
    if direction in HITS:
        return np.array(HITS[direction], float)
    angle = np.random.default_rng([int(seed), _streams(index) + 20]).uniform(0.0, 2.0 * math.pi)
    return np.array([math.cos(angle), math.sin(angle), 0.0])


def picture_direction(h):
    """The way the view is kicked across the picture (x right, y up); straight up for a hit from the front."""
    r = np.array([h[0], h[1]], float)
    length = math.hypot(r[0], r[1])
    return r / length if length >= 0.2 else np.array([0.0, 1.0])


def damping(bounce):
    return 0.08 + 0.72 * (1.0 - float(bounce))


def kick(tau, swing, bounce, rate=1.0):
    """An underdamped spring's impulse response over tau frames: 0 at 0, 1 at its first crest, the next
    swing `swing` frames later (over `rate`)."""
    t = np.asarray(tau, float)
    w = math.pi / float(swing) * rate
    zeta = damping(bounce)
    sigma = zeta * w / math.sqrt(1.0 - zeta * zeta)
    crest_at = math.atan2(w, sigma) / w
    crest = math.exp(-sigma * crest_at) * math.sin(w * crest_at)
    return np.where(t > 0.0, np.exp(-sigma * np.maximum(t, 0.0)) * np.sin(w * t) / crest, 0.0)


def impact(frames, a, b, fps, s, index=0):
    """A hit at frame a, still again at b: a kick that springs back, a perpendicular wobble, a rattle that
    fades as trauma squared. The same two arrays as `handheld`."""
    f = np.asarray(frames, float)
    tau = f - a
    u = np.clip(tau / float(b - a), 0.0, 1.0)
    seed, k = s["seed"], _streams(index)
    h = hit_vector(s["direction"], seed, index)
    r = picture_direction(h)
    rng = np.random.default_rng([int(seed), k + 21])
    wobble_sign = 1.0 if rng.uniform() < 0.5 else -1.0
    roll_side = 1.0 if rng.uniform() < 0.5 else -1.0
    roll_dir = -h[0] if abs(h[0]) >= 0.2 else 0.5 * roll_side
    strength = s["strength"]
    main = kick(tau, s["swing"], s["bounce"])
    wobble = WOBBLE_SHARE * wobble_sign * kick(tau, s["swing"], s["bounce"], WOBBLE_RATE)
    taper = 1.0 - smootherstep((u - 0.5) / 0.5)
    rot = np.zeros((len(f), 3))
    # The view (-Z) turned toward r across the picture: about (r_y, -r_x, 0); the wobble across that.
    rot[:, 0] = strength * (main * r[1] + wobble * r[0])
    rot[:, 1] = strength * (-main * r[0] + wobble * r[1])
    rot[:, 2] = strength * s["roll"] * roll_dir * main
    rot *= taper[:, None]
    off = (s["push"] * main * taper)[:, None] * h[None, :]
    sec = tau / float(fps)
    rattle_hz = capped(RATTLE_HZ, fps)
    trauma = (1.0 - u) ** 2 * np.clip(tau, 0.0, 1.0)
    roll = (1.0, 1.0, s["roll"])
    for axis in range(3):
        rot[:, axis] += roll[axis] * 0.5 * s["rattle"] * trauma * fractal(
            sec, seed, k + axis + 11, rattle_hz / 2.0, 2, fps=fps)
    still = (tau <= 0.0) | (u >= 1.0)
    rot[still] = 0.0
    off[still] = 0.0
    return rot, off


def shake(mode, frames, a, b, fps, s, index=0):
    return (handheld if mode == "handheld" else impact)(frames, a, b, fps, s, index)


# ---------------------------------------------------------------------------------------------------------
# 2. The rotation algebra (numpy, Maya's row vectors: a point is p . M, a node's world is local . parent)
# ---------------------------------------------------------------------------------------------------------

ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")   # Maya's rotateOrder enum


def axis_matrix(axis, angle):
    """A turn about one axis (0 x, 1 y, 2 z), radians, as Maya writes it for row vectors."""
    c, s = math.cos(angle), math.sin(angle)
    m = np.eye(3)
    i1, i2 = (axis + 1) % 3, (axis + 2) % 3
    m[i1, i1] = c
    m[i1, i2] = s
    m[i2, i1] = -s
    m[i2, i2] = c
    return m


def euler_matrix(radians, order):
    """Maya's rotation for eulers (x, y, z) in a rotate order, its first axis innermost."""
    m = np.eye(3)
    for letter in order:
        axis = "xyz".index(letter)
        m = m @ axis_matrix(axis, radians[axis])
    return m


def matrix_eulers(m, order):
    """Both euler solutions (radians, (x, y, z)) of a rotation in a rotate order. The order's axes are
    permuted onto x, y, z (an odd permutation turns every angle the other way) and read as xyz."""
    axes = ["xyz".index(letter) for letter in order]
    p = np.asarray(m, float)[np.ix_(axes, axes)]
    sign = 1.0 if order in ("xyz", "yzx", "zxy") else -1.0
    sb = max(-1.0, min(1.0, -p[0, 2]))
    if abs(sb) < 1.0 - 1e-12:
        first = (math.atan2(p[1, 2], p[2, 2]), math.asin(sb), math.atan2(p[0, 1], p[0, 0]))
    else:   # gimbal: the outer angle is free, the inner carries the turn
        first = (math.atan2(p[1, 0] * sb, p[1, 1]), math.copysign(math.pi / 2.0, sb), 0.0)
    second = (first[0] + math.pi, math.pi - first[1], first[2] + math.pi)
    out = []
    for solution in (first, second):
        e = [0.0, 0.0, 0.0]
        for slot, axis in enumerate(axes):
            e[axis] = sign * solution[slot]
        out.append(tuple(e))
    return out


def closest(solutions, near):
    """The solution, each angle moved by whole turns, nearest `near` (radians)."""
    best, best_distance = None, None
    for solution in solutions:
        e = [v + 2.0 * math.pi * round((n - v) / (2.0 * math.pi)) for v, n in zip(solution, near)]
        distance = sum(abs(v - n) for v, n in zip(e, near))
        if best_distance is None or distance < best_distance:
            best, best_distance = e, distance
    return np.array(best)


def rotation_from_vector(v):
    """A turn about the vector's direction by its length (radians), right-handed, for row vectors."""
    v = np.asarray(v, float)
    angle = float(np.linalg.norm(v))
    if angle < 1e-15:
        return np.eye(3)
    x, y, z = v / angle
    k = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    column = np.eye(3) + math.sin(angle) * k + (1.0 - math.cos(angle)) * (k @ k)
    return column.T


def shaken(base_deg, order, rotvec_deg, rotate_axis_deg=(0.0, 0.0, 0.0)):
    """The euler (deg) nearest the base that turns the node by `rotvec` about its OWN axes: its frame
    RA . R(e) [. JO] becomes S . RA . R(e) [. JO], so R(e') = RA^-1 . S . RA . R(e) (a joint orient on the
    right cancels)."""
    base = np.radians(np.asarray(base_deg, float))
    axis = euler_matrix(np.radians(np.asarray(rotate_axis_deg, float)), "xyz")
    turn = rotation_from_vector(np.radians(np.asarray(rotvec_deg, float)))
    m = axis.T @ turn @ axis @ euler_matrix(base, order)
    return np.degrees(closest(matrix_eulers(m, order), base))


def along_axes(offset, base_deg, order, rotate_axis_deg=(0.0, 0.0, 0.0), joint_orient_deg=(0.0, 0.0, 0.0)):
    """An offset along the node's own axes, in its parent's space (where its translate lives)."""
    frame = (euler_matrix(np.radians(np.asarray(rotate_axis_deg, float)), "xyz")
             @ euler_matrix(np.radians(np.asarray(base_deg, float)), order)
             @ euler_matrix(np.radians(np.asarray(joint_orient_deg, float)), "xyz"))
    return np.asarray(offset, float) @ frame


def deltas(rot, off, base, order, rotate_axis=(0.0, 0.0, 0.0), joint_orient=(0.0, 0.0, 0.0)):
    """What an additive layer adds to the node's rotate (deg) and translate on each frame, so that it shows
    the shake on top of `base` (deg)."""
    rot = np.asarray(rot, float)
    off = np.asarray(off, float)
    base = np.asarray(base, float)
    dr = np.zeros_like(rot)
    dt = np.zeros_like(off)
    for i in range(len(rot)):
        if np.any(rot[i]):
            dr[i] = shaken(base[i], order, rot[i], rotate_axis) - base[i]
        if np.any(off[i]):
            dt[i] = along_axes(off[i], base[i], order, rotate_axis, joint_orient)
    return dr, dt


def _frame_tag(frame):
    frame = int(frame)
    return "m%d" % -frame if frame < 0 else str(frame)


def layer_name(mode, a, b):
    return "CamShake_%s_%s_%s" % (mode.capitalize(), _frame_tag(a), _frame_tag(b))


def record_text(mode, s, a, b, targets):
    """What a shake's layer remembers about itself."""
    return json.dumps({"version": VERSION, "mode": mode, "settings": s, "frames": [int(a), int(b)],
                       "targets": list(targets)}, sort_keys=True)


def parse_record(text):
    """The record, or None when it is not one of ours."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("version") != VERSION or data.get("mode") not in MODES:
        return None
    frames, targets = data.get("frames"), data.get("targets")
    if not (isinstance(frames, list) and len(frames) == 2 and isinstance(targets, list)):
        return None
    data["settings"] = settings(data["mode"], data.get("settings") or {})
    return data
