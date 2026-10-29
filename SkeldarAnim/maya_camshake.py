"""maya_camshake - the Camera Shake card: handheld filming and an impact, keyed on a layer of their own.

Select a camera (nothing selected: our SceneSetup_camera when there is exactly one), highlight a stretch of
the time slider, set the controls and press Apply:
- Handheld: an operator holding the camera - a slow sway, the hands' tremor, a little drift.
- Impact: a jolt from a chosen side whose waves die by the end of the range, a fine rattle on top.
- Bobbing (2026-10-28): a walk's or a run's steps - the gait's shape, sizes from the gait guide's formula.
Every press is an additive layer (its weight is a strength dial, Mute turns it off) and it REPLACES the
shake of the same mode those cameras had: a camera keeps one layer of each mode. After Apply
a released slider re-keys that shake. docs/superpowers/specs/2026-10-13-camera-shake-design.md.

Built as a standalone script (docs/superpowers/plans/camshake/, 2026-10-13) and moved into the plugin the
same day («Давай встроим скрипт камеры в наш плагин»): its window is the hub's Camera Shake card now.
Sections 1-2 are numpy only; 3 the scene (cmds); 4 the card (cmds + the hub's marks).
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
MODES = ("handheld", "impact", "bobbing")
LOOP_MODES = ("handheld", "bobbing")   # Loop (2026-10-29): the range one cycle, the layer cycling past it
DIRECTIONS = ("Random", "Below", "Above", "Left", "Right", "Front")

# (name, label, default, low, high)
CONTROLS = {
    "handheld": (
        ("sway", "Sway, deg", 1.0, 0.0, 6.0),
        ("speed", "Speed", 1.0, 0.25, 4.0),
        ("jitter", "Jitter, deg", 0.12, 0.0, 1.5),
        ("jitter_hz", "Jitter, Hz", 7.0, 1.0, 15.0),
        ("roll", "Roll", 0.4, 0.0, 1.0),
        ("drift", "Drift, cm", 1.5, 0.0, 15.0),
        ("ease", "Ease, fr", 6.0, 0.0, 60.0),
    ),
    "impact": (
        ("strength", "Strength, deg", 4.0, 0.0, 25.0),
        ("push", "Push, cm", 2.0, 0.0, 30.0),
        ("wave", "Wave, fr", 8.0, 2.5, 60.0),
        ("rattle", "Rattle, deg", 1.0, 0.0, 6.0),
        ("rattle_hz", "Rattle, Hz", 11.0, 2.0, 15.0),
        ("roll", "Roll", 0.4, 0.0, 1.0),
        ("length", "Length, fr", 24.0, 2.0, 240.0),
    ),
}
DECAYS = ("Exponential", "Linear", "Smooth", "Sharp")
AXES = (("tilt_on", "Tilt"), ("pan_on", "Pan"), ("roll_on", "Roll"))   # rotation about X, Y, Z
PRESETS = {
    "handheld": (
        ("Calm", {"sway": 2.57, "speed": 0.49, "jitter": 0.07, "jitter_hz": 2.71, "roll": 0.38, "drift": 6.04,
                  "ease": 0.0}),
        ("Handheld", {"sway": 1.0, "speed": 1.0, "jitter": 0.12, "jitter_hz": 7.0, "roll": 0.4, "drift": 1.5}),
        ("Nervous", {"sway": 1.8, "speed": 1.8, "jitter": 0.3, "jitter_hz": 9.5, "roll": 0.5, "drift": 3.0}),
    ),
    "impact": (
        ("Light", {"strength": 2.0, "push": 1.0, "wave": 6.0, "decay": "Exponential", "rattle": 0.6,
                   "rattle_hz": 12.0, "roll": 0.4}),
        ("Hit", {"strength": 4.0, "push": 2.0, "wave": 8.0, "decay": "Exponential", "rattle": 1.0,
                 "rattle_hz": 11.0, "roll": 0.4}),
        ("Heavy", {"strength": 6.0, "push": 4.0, "wave": 10.0, "decay": "Linear", "rattle": 1.6,
                   "rattle_hz": 10.0, "roll": 0.5}),
        ("Explosion", {"strength": 9.0, "push": 8.0, "wave": 12.0, "decay": "Smooth", "rattle": 3.0,
                       "rattle_hz": 8.0, "roll": 0.6, "direction": "Below"}),
        ("Recoil", {"strength": 3.0, "push": 2.0, "wave": 6.0, "decay": "Sharp", "rattle": 0.4,
                    "rattle_hz": 12.0, "roll": 0.2, "direction": "Front"}),
    ),
}
DEFAULT_PRESET = {"handheld": "Handheld", "impact": "Hit"}


def settings(mode, given=None):
    """The mode's controls, defaults filled in and each clamped to its range; the seed (an int, 0 or more);
    the axes switched on; for an impact, the direction and the decay."""
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
    for key, _ in AXES:
        out[key] = bool(given.get(key, True))
    if mode == "impact":
        direction = given.get("direction", "Random")
        out["direction"] = direction if direction in DIRECTIONS else "Random"
        decay = given.get("decay", DECAYS[0])
        out["decay"] = decay if decay in DECAYS else DECAYS[0]
    if mode == "bobbing":
        gait = given.get("gait", "Walk")
        out["gait"] = gait if gait in ("Walk", "Run") else "Walk"
        foot = given.get("foot", "Left")
        out["foot"] = foot if foot in ("Left", "Right") else "Left"
    if mode in LOOP_MODES:
        out["loop"] = bool(given.get("loop", False))
    return out


def preset(mode, name, current=None):
    """`current` with the preset's values on top: the seed, Length and the axes are kept, and Ease and an
    impact's direction too unless the preset names them (Calm names Ease 0); a bobbing preset keeps the
    first foot, the first contact and Ease."""
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
LOOP_KNOTS = 3          # a looped noise's fewest knots a cycle: one slower than the cycle swings once in it


def loop_knots(period, hz):
    """How many knots a noise at `hz` holds in a cycle of `period` seconds: whole, so the spline closes."""
    return max(LOOP_KNOTS, int(round(float(period) * float(hz) * KNOTS_PER_CYCLE)))


def noise(seconds, seed, stream, hz, period=None):
    """A smooth random signal of unit RMS swinging about `hz` times a second (2 hz zero crossings, as a
    sine): Gaussian knots through a cubic B-spline (C2, no overshoot). Still when hz is 0. With a `period`
    (seconds) it repeats every period: a whole number of knots in it (`loop_knots`, the rate a little off),
    their indices wrapped - the spline closes C2 across the seam."""
    s = np.atleast_1d(np.asarray(seconds, float))
    if hz <= 0.0 or s.size == 0:
        return np.zeros_like(s)
    if period:
        count = loop_knots(period, hz)
        u = s / float(period) * count
        i = np.floor(u).astype(int)
        knots = _knots(seed, stream, 0, count - 1)
        index = (i[:, None] - 1 + np.arange(4)[None, :]) % count
        return np.sum(_basis(u - i) * knots[index], axis=1) / math.sqrt(MEAN_VARIANCE)
    u = s * float(hz) * KNOTS_PER_CYCLE
    i = np.floor(u).astype(int)
    first = int(i.min()) - 1
    knots = _knots(seed, stream, first, int(i.max()) + 2)
    index = (i - 1 - first)[:, None] + np.arange(4)[None, :]
    return np.sum(_basis(u - i) * knots[index], axis=1) / math.sqrt(MEAN_VARIANCE)


def fractal(seconds, seed, stream, hz, octaves, gain=0.5, fps=None, period=None):
    """Octaves of `noise` at hz x 2^k with amplitude gain^k, back to unit RMS; capped by the frame rate.
    Every octave repeats every `period` seconds when one is given."""
    s = np.atleast_1d(np.asarray(seconds, float))
    total = np.zeros_like(s)
    norm = 0.0
    for k in range(octaves):
        rate = hz * 2.0 ** k
        if fps:
            rate = capped(rate, fps)
        amplitude = gain ** k
        total += amplitude * noise(s, seed, stream * 16 + k, rate, period)
        norm += amplitude * amplitude
    return total / math.sqrt(norm) if norm else total


def whole_cycles(hz, period, fps=None):
    """The rate nearest `hz` that swings a whole number of times (at least once) in `period` seconds - kept
    under the frame rate's cap when `fps` is given."""
    period = float(period)
    cycles = max(1, int(round(float(hz) * period)))
    if fps:
        while cycles > 1 and cycles / period > NYQUIST_SHARE * float(fps) + 1e-9:
            cycles -= 1
    return cycles / period


TREMOR_SWELL = 0.45      # how far a tremor's amplitude swells and fades about 1 (RMS)
TREMOR_WANDER = 0.6      # radians its phase wanders (RMS)


def tremor(seconds, seed, stream, hz, period=None):
    """A narrow-band shake of unit RMS: a sine at `hz` whose amplitude swells and fades and whose phase
    wanders, both slowly - a hand's tremor is a rhythm, not a hiss. Measured, a broad-band noise sampled once
    a frame cannot swing more than a quarter of the frame rate (white noise: 7.5 Hz at 30 fps); a sine shows
    its own rate up to the frame rate's limit. With a `period` (seconds) it repeats every period: the sine
    swings a whole number of times in it (`whole_cycles`), the swell and the wander repeat too."""
    s = np.atleast_1d(np.asarray(seconds, float))
    if hz <= 0.0 or s.size == 0:
        return np.zeros_like(s)
    if period:
        hz = whole_cycles(hz, period)
    slow = max(hz / 7.0, 0.1)
    base = 100000 + 4 * int(stream)
    swell = 1.0 + TREMOR_SWELL * noise(s, seed, base + 1, slow, period)
    wander = TREMOR_WANDER * noise(s, seed, base + 2, 0.5 * slow, period)
    start = np.random.default_rng([int(seed), base + 3]).uniform(0.0, 2.0 * math.pi)
    return swell * np.sin(2.0 * math.pi * hz * s + wander + start) / math.sqrt(
        (1.0 + TREMOR_SWELL ** 2) / 2.0)


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
DRIFT_HZ = 0.2           # the camera's own travel, x Speed
SWAY_AXES = (0.75, 1.0, 1.0)     # tilt, pan, roll (roll x Roll): an operator aims better up-down
DRIFT_AXES = (0.7, 1.0, 0.4)     # side, bob, push


def loop_period(a, b, fps, s):
    """Seconds of one cycle when the shake loops (frames a..b, the last showing the first), else None."""
    return (b - a) / float(fps) if s.get("loop") and b > a else None


def ease_of(f, a, b, s):
    """The ends' fade, (n, 1): none in a loop - it has no ends."""
    if s.get("loop"):
        return np.ones((len(f), 1))
    return eased(f, a, b, s["ease"])[:, None]


def handheld(frames, a, b, fps, s, index=0):
    """An operator holding the camera: (rotation (n, 3) deg about the camera's X, Y, Z - tilt, pan, roll;
    offset (n, 3) cm along them - side, bob, push) on each frame of a..b. Looped, every noise repeats over
    a..b (frame b shows frame a) and nothing fades in or out."""
    f = np.asarray(frames, float)
    sec = (f - a) / float(fps)
    period = loop_period(a, b, fps, s)
    seed, k = s["seed"], _streams(index)
    speed = s["speed"]
    sway_hz = capped(SWAY_HZ * speed, fps)
    jitter_hz = capped(s["jitter_hz"], fps)       # its own rate: Speed is the body's, not the hands'
    if period:
        jitter_hz = whole_cycles(jitter_hz, period, fps)
    drift_hz = capped(DRIFT_HZ * speed, fps)
    roll = (1.0, 1.0, s["roll"])
    rot = np.zeros((len(f), 3))
    off = np.zeros((len(f), 3))
    for axis in range(3):
        sway = SWAY_AXES[axis] * 0.5 * s["sway"] * fractal(sec, seed, k + axis + 1, sway_hz, 3, fps=fps,
                                                             period=period)
        jitter = 0.5 * s["jitter"] * tremor(sec, seed, k + axis + 4, jitter_hz, period)
        rot[:, axis] = roll[axis] * (sway + jitter)
        off[:, axis] = DRIFT_AXES[axis] * 0.5 * s["drift"] * fractal(sec, seed, k + axis + 7, drift_hz, 2,
                                                                       fps=fps, period=period)
    envelope = ease_of(f, a, b, s)
    return rot * envelope * axis_mask(s), off * envelope


def axis_mask(s):
    """1 for each rotation (tilt, pan, roll) switched on, 0 for each switched off."""
    return np.array([1.0 if s.get(key, True) else 0.0 for key, _ in AXES])


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


EXPONENTIAL_RATE = 4.0   # Exponential: e^(-4u), brought to 0 at the end - a fast fall and a long thin tail
SHARP_POWER = 6.0        # Sharp: (1-u)^6 - gone within the first waves
MIN_WAVE = 1.0 / NYQUIST_SHARE   # frames: a shorter wave aliases into a slow wobble


def envelope(u, decay):
    """How the hit dies over its range (u from 0 at the hit to 1 at the end): 1 at the hit, 0 at the end,
    never rising."""
    u = np.clip(np.asarray(u, float), 0.0, 1.0)
    if decay == "Linear":
        return 1.0 - u
    if decay == "Smooth":       # holds its strength, then fades softly
        return 1.0 - u * u * (3.0 - 2.0 * u)
    if decay == "Sharp":
        return (1.0 - u) ** SHARP_POWER
    tail = math.exp(-EXPONENTIAL_RATE)
    return (np.exp(-EXPONENTIAL_RATE * u) - tail) / (1.0 - tail)


def waves(tau, wave, span, decay, rate=1.0):
    """The hit's waves over tau frames: a sine from the hit, `wave` frames crest to crest (over `rate`, never
    shorter than MIN_WAVE), under the decay's envelope across `span` frames; 1 at its first crest."""
    t = np.asarray(tau, float)
    period = max(float(wave) / rate, MIN_WAVE)
    span = max(float(span), 1e-6)

    def raw(x):
        return np.sin(2.0 * math.pi * x / period) * envelope(x / span, decay)

    probe = np.linspace(0.0, period / 2.0, 401)
    best = int(np.argmax(raw(probe)))
    low, high = probe[max(best - 1, 0)], probe[min(best + 1, len(probe) - 1)]
    for _ in range(80):                       # the first lobe is one hump: close in on its top
        left, right = low + (high - low) / 3.0, high - (high - low) / 3.0
        if raw(left) < raw(right):
            low = left
        else:
            high = right
    crest = float(raw(0.5 * (low + high)))
    return np.where(t > 0.0, raw(np.maximum(t, 0.0)) / crest, 0.0)


def impact(frames, a, b, fps, s, index=0):
    """A hit at frame a, still again at b: a kick that swings back and forth `wave` frames a swing and dies
    by the decay's shape, a perpendicular wobble, a rattle that dies faster (the envelope squared). The same
    two arrays as `handheld`."""
    f = np.asarray(frames, float)
    tau = f - a
    span = float(b - a)
    u = np.clip(tau / span, 0.0, 1.0)
    seed, k = s["seed"], _streams(index)
    h = hit_vector(s["direction"], seed, index)
    r = picture_direction(h)
    rng = np.random.default_rng([int(seed), k + 21])
    wobble_sign = 1.0 if rng.uniform() < 0.5 else -1.0
    roll_side = 1.0 if rng.uniform() < 0.5 else -1.0
    roll_dir = -h[0] if abs(h[0]) >= 0.2 else 0.5 * roll_side
    strength = s["strength"]
    main = waves(tau, s["wave"], span, s["decay"])
    wobble = WOBBLE_SHARE * wobble_sign * waves(tau, s["wave"], span, s["decay"], WOBBLE_RATE)
    rot = np.zeros((len(f), 3))
    # The view (-Z) turned toward r across the picture: about (r_y, -r_x, 0); the wobble across that.
    rot[:, 0] = strength * (main * r[1] + wobble * r[0])
    rot[:, 1] = strength * (-main * r[0] + wobble * r[1])
    rot[:, 2] = strength * s["roll"] * roll_dir * main
    off = (s["push"] * main)[:, None] * h[None, :]
    sec = tau / float(fps)
    rattle_hz = capped(s["rattle_hz"], fps)
    trauma = envelope(u, s["decay"]) ** 2 * np.clip(tau, 0.0, 1.0)
    roll = (1.0, 1.0, s["roll"])
    for axis in range(3):
        rot[:, axis] += roll[axis] * 0.5 * s["rattle"] * trauma * tremor(sec, seed, k + axis + 11, rattle_hz)
    still = (tau <= 0.0) | (u >= 1.0)
    rot[still] = 0.0
    off[still] = 0.0
    return rot * axis_mask(s), off


#  Bobbing (2026-10-28): a walk's or a run's steps in the camera, a procedural cycle whose shape is the gait's
#  physics and whose sizes come from the gait guide's measurements (docs/superpowers/plans/gaitguide/research;
#  docs/superpowers/specs/2026-10-28-camera-bobbing-design.md).

GAITS = ("Walk", "Run")
FEET = ("Left", "Right")
WALK_RUN = 2.1           # m/s: the walk-run transition (Hansen 2017, 2.14)
#  (speed m/s, value): np.interp holds the ends
WALK_TEMPO = ((0.5, 72.0), (1.04, 101.0), (1.32, 116.0), (1.62, 128.0), (2.1, 147.0))   # Winiarski 2019
WALK_BOB = ((0.5, 2.28), (0.7, 2.74), (1.6, 4.83), (2.1, 5.99))                          # Orendurff 2004
WALK_SIDE = ((0.5, 7.7), (0.7, 6.99), (1.6, 3.85), (2.1, 2.1))                           # Orendurff 2004
WALK_SOFT = ((1.04, 58.0), (1.62, 47.0))     # double stance 29 / 23 % of a step (Winiarski) over 0.5
WALK_NOD = 3.58 / 5.43   # deg of head pitch a cm of C7 bob (Peters, NASA, 1.8 m/s)
WALK_TURN = 2.85         # deg of head yaw (Peters)
RUN_TEMPO = ((2.1, 141.0), (2.5, 162.0), (2.9, 172.6), (3.5, 171.4), (4.5, 183.5), (12.0, 262.0))
RUN_BOB = ((2.5, 8.9), (2.9, 8.7), (3.5, 8.8), (4.5, 8.0), (12.0, 4.9))   # Fukuchi, Heiderscheit, Coh
RUN_SOFT = ((2.5, 78.3), (3.5, 62.7), (4.5, 58.7), (12.14, 12.3))         # stance 2 x duty, as 0.3 + 0.6 s
RUN_SIDE = ((2.5, 3.0), (10.0, 1.5))         # an estimate: the guide has no running number
RUN_NOD = 0.35           # deg a cm of bob - an estimate
RUN_TURN = 6.1           # deg of head yaw (Pontzer 2009)
PENDULUM = math.radians(30.0)   # the walk's half sweep: a cos arc, fast into the down, slow over the up
WALK_LOW = 0.1           # the walk's low, a share of a step after the contact (~5 % of the stride)
WALK_SIDE_PEAK = 0.5     # the walk's sway over the stance foot
SAMPLES = 512            # a step's shape is tabled this finely
FOOT_WAVE_S = 0.2        # the footfall's wave, crest to crest
FOOT_SPAN_S = 0.5        # and how long it rings (never past the next step)
FOOT_CM_PER_DEG = 0.5    # the footfall drops the camera half as many cm as it pitches degrees


def _at(table, speed):
    xs, ys = zip(*table)
    return float(np.interp(speed, xs, ys))


def from_speed(speed):
    """The gait's knobs at a speed (m/s), from the guide's measurements: the gait, Tempo, Bob, Sway (`side`),
    Nod, Turn, Softness. Footfall, Roll and Variation are style and are not here."""
    speed = float(speed)
    if speed < WALK_RUN:
        bob = _at(WALK_BOB, speed)
        out = {"gait": "Walk", "tempo": _at(WALK_TEMPO, speed), "bob": bob,
               "side": max(2.0, _at(WALK_SIDE, speed)), "nod": WALK_NOD * bob, "turn": WALK_TURN,
               "softness": _at(WALK_SOFT, speed)}
    else:
        bob = _at(RUN_BOB, speed)
        out = {"gait": "Run", "tempo": _at(RUN_TEMPO, speed), "bob": bob, "side": _at(RUN_SIDE, speed),
               "nod": RUN_NOD * bob, "turn": RUN_TURN, "softness": _at(RUN_SOFT, speed)}
    out = {key: (round(value, 2) if isinstance(value, float) else value) for key, value in out.items()}
    out["pace"] = round(speed, 2)
    return out


def _styled(speed, style=None, **scale):
    """A preset: the formula at a speed, some of it scaled, the style's own values on top."""
    values = from_speed(speed)
    for key, factor in scale.items():
        values[key] = round(values[key] * factor, 2)
    values.update(style or {})
    return values


_WALK = from_speed(1.3)
CONTROLS["bobbing"] = (
    ("pace", "Speed, m/s", _WALK["pace"], 0.5, 10.0),
    ("tempo", "Tempo, steps/min", _WALK["tempo"], 50.0, 300.0),
    ("bob", "Bob, cm", _WALK["bob"], 0.0, 20.0),
    ("side", "Sway, cm", _WALK["side"], 0.0, 15.0),
    ("nod", "Nod, deg", _WALK["nod"], 0.0, 10.0),
    ("turn", "Turn, deg", _WALK["turn"], 0.0, 15.0),
    ("lean", "Roll, deg", 1.0, 0.0, 10.0),
    ("footfall", "Footfall, deg", 0.3, 0.0, 5.0),
    ("softness", "Softness, %", _WALK["softness"], 0.0, 100.0),
    ("variation", "Variation, %", 10.0, 0.0, 50.0),
    ("contact", "First contact, fr", 0.0, 0.0, 60.0),
    ("ease", "Ease, fr", 6.0, 0.0, 60.0),
)
PRESETS["bobbing"] = (
    ("Slow walk", _styled(1.0, {"footfall": 0.2, "lean": 1.0, "variation": 10.0})),
    ("Walk", _styled(1.3, {"footfall": 0.3, "lean": 1.0, "variation": 10.0})),
    ("Fast walk", _styled(1.6, {"footfall": 0.4, "lean": 0.8, "variation": 10.0})),
    ("Jog", _styled(2.5, {"footfall": 0.6, "lean": 1.0, "variation": 10.0})),
    ("Run", _styled(3.5, {"footfall": 0.8, "lean": 1.2, "variation": 10.0})),
    ("Sprint", _styled(7.0, {"footfall": 1.0, "lean": 1.5, "variation": 10.0})),
    ("Sneak", _styled(0.8, {"footfall": 0.0, "lean": 0.5, "variation": 10.0, "softness": 90.0},
                      bob=0.4, nod=0.3, side=0.6, tempo=0.85)),
    ("Heavy", _styled(1.1, {"footfall": 1.5, "lean": 1.5, "variation": 12.0, "softness": 30.0},
                      tempo=0.9, bob=1.2, side=1.5)),
    ("Tired", _styled(1.0, {"footfall": 0.6, "lean": 1.8, "variation": 30.0},
                      tempo=0.9, bob=1.3, side=1.6, nod=1.8)),
)
DEFAULT_PRESET["bobbing"] = "Walk"


def _normalised(y):
    """1 peak to peak about a zero mean."""
    y = np.asarray(y, float) - float(np.mean(y))
    span = float(y.max() - y.min())
    return y / span if span > 1e-12 else np.zeros_like(y)


def _blurred(y, sigma):
    """A periodic Gaussian blur, sigma in samples."""
    if sigma < 0.5:
        return y
    k = np.fft.rfftfreq(len(y))
    return np.fft.irfft(np.fft.rfft(y) * np.exp(-2.0 * (math.pi * k * sigma) ** 2), len(y))


def stance_share(softness):
    """A run's stance as a share of a step, from Softness (0..1)."""
    return 0.3 + 0.6 * float(softness)


def step_curve(gait, softness):
    """One step's up-down from a contact (u = 0) to the next, tabled on SAMPLES points, 1 peak to peak about
    a zero mean. Walk: an inverted pendulum's arc, low WALK_LOW after the contact (a cusp rounded over the
    double support, 0.5 x softness of a step), high at passing. Run: a spring down in the stance (low at
    mid-stance), a ballistic flight up (high mid-flight), leaving and landing at the stance's speed."""
    u = np.arange(SAMPLES) / float(SAMPLES)
    softness = min(1.0, max(0.0, float(softness)))
    if gait == "Run":
        c = stance_share(softness)
        f = 1.0 - c
        v0 = math.pi / c
        g = 2.0 * v0 / f
        tau = u - c
        y = np.where(u < c, -np.sin(math.pi * u / c), v0 * tau - 0.5 * g * tau * tau)
        return _normalised(y)
    swung = (u - WALK_LOW) % 1.0
    y = np.cos(PENDULUM * (2.0 * swung - 1.0))
    return _normalised(_blurred(y, 0.5 * softness * SAMPLES / 4.0))


def step_shape(gait, softness, u):
    """The step curve at u (shares of a step, any real: periodic)."""
    table = step_curve(gait, softness)
    x = (np.asarray(u, float) % 1.0) * SAMPLES
    return np.interp(x, np.arange(SAMPLES + 1), np.append(table, table[0]))


def loop_tempo(tempo, frames, fps):
    """(the tempo nearest `tempo` that fits a whole number of strides - two steps, at least one - in a
    cycle of `frames` frames, how many strides)."""
    stride = 2.0 * float(fps) * 60.0 / float(tempo)
    strides = max(1, int(round(float(frames) / stride)))
    return 120.0 * strides * float(fps) / float(frames), strides


def tempo_of(a, b, fps, s):
    """The steps a minute a bobbing walks at: its Tempo, or in a loop the nearest that closes the cycle."""
    return loop_tempo(s["tempo"], b - a, fps)[0] if loop_period(a, b, fps, s) else s["tempo"]


def bobbing(frames, a, b, fps, s, index=0):
    """A walk's or a run's steps: (rotation (n, 3) deg about the camera's X, Y, Z - nod, turn, roll; offset
    (n, 3) cm - side, up, forward, along the camera's heading and its parent's up) on each frame of a..b.
    The first contact is `contact` frames after a, on the first foot; a stride is two steps. Looped, the
    tempo is the nearest that fits whole strides in a..b (`loop_tempo`), the variation repeats over it and
    nothing fades in or out: frame b shows frame a."""
    f = np.asarray(frames, float)
    period = loop_period(a, b, fps, s)
    tempo = tempo_of(a, b, fps, s)
    step = fps * 60.0 / tempo                      # frames a step
    q = (f - a - s["contact"]) / step              # steps since the first contact
    softness = s["softness"] / 100.0
    run = s["gait"] == "Run"
    up = step_shape(s["gait"], softness, q)
    first = -1.0 if s["foot"] == "Left" else 1.0   # the camera's -X is the left
    peak = 0.5 * stance_share(softness) if run else WALK_SIDE_PEAK
    lateral = first * np.cos(math.pi * (q - peak))  # -1 over the left foot, +1 over the right
    seed, k = s["seed"], _streams(index)
    sec = (f - a) / float(fps)
    vary = 1.0 + s["variation"] / 100.0 * noise(sec, seed, k + 31, capped(0.5 * tempo / 60.0, fps), period)
    vary = np.maximum(vary, 0.0)
    rot = np.zeros((len(f), 3))
    off = np.zeros((len(f), 3))
    off[:, 0] = 0.5 * s["side"] * vary * lateral
    off[:, 1] = s["bob"] * vary * up
    rot[:, 0] = -s["nod"] * vary * up              # the head pitched down as the body rises
    rot[:, 1] = -0.5 * s["turn"] * first * np.cos(math.pi * q)   # toward the striking foot at each contact
    rot[:, 2] = -0.5 * s["lean"] * vary * lateral  # the top toward the stance foot
    if s["footfall"] > 0.0 and len(f):
        contacts = np.arange(math.floor(q.min()) - 2, math.floor(q.max()) + 1)
        tau = (q[:, None] - contacts[None, :]) * step
        span = min(FOOT_SPAN_S * fps, step)
        jolt = waves(tau, FOOT_WAVE_S * fps, span, "Sharp").sum(axis=1) * vary
        rot[:, 0] -= s["footfall"] * jolt
        off[:, 1] -= FOOT_CM_PER_DEG * s["footfall"] * jolt
    envelope = ease_of(f, a, b, s)
    return rot * envelope * axis_mask(s), off * envelope


def shake(mode, frames, a, b, fps, s, index=0):
    work = {"handheld": handheld, "impact": impact, "bobbing": bobbing}[mode]
    return work(frames, a, b, fps, s, index)


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


def along_heading(offset, base_deg, order, rotate_axis_deg=(0.0, 0.0, 0.0),
                  joint_orient_deg=(0.0, 0.0, 0.0)):
    """An offset (side, up, back) along the node's HEADING in its parent's space: side its own X flattened,
    up the parent's Y, back their cross - so a camera looking down still bobs straight up and down. A node
    whose X stands near upright (rolled 90 deg) keeps its own axes."""
    frame = (euler_matrix(np.radians(np.asarray(rotate_axis_deg, float)), "xyz")
             @ euler_matrix(np.radians(np.asarray(base_deg, float)), order)
             @ euler_matrix(np.radians(np.asarray(joint_orient_deg, float)), "xyz"))
    side = np.array([frame[0, 0], 0.0, frame[0, 2]])
    length = float(np.linalg.norm(side))
    if length < 0.2:
        return np.asarray(offset, float) @ frame
    side /= length
    up = np.array([0.0, 1.0, 0.0])
    return np.asarray(offset, float) @ np.array([side, up, np.cross(side, up)])


def deltas(rot, off, base, order, rotate_axis=(0.0, 0.0, 0.0), joint_orient=(0.0, 0.0, 0.0), heading=False):
    """What an additive layer adds to the node's rotate (deg) and translate on each frame, so that it shows
    the shake on top of `base` (deg). `heading`: the offset along the heading and the parent's up."""
    move = along_heading if heading else along_axes
    rot = np.asarray(rot, float)
    off = np.asarray(off, float)
    base = np.asarray(base, float)
    dr = np.zeros_like(rot)
    dt = np.zeros_like(off)
    for i in range(len(rot)):
        if np.any(rot[i]):
            dr[i] = shaken(base[i], order, rot[i], rotate_axis) - base[i]
        if np.any(off[i]):
            dt[i] = move(off[i], base[i], order, rotate_axis, joint_orient)
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


# ---------------------------------------------------------------------------------------------------------
# 3. The scene (cmds)
# ---------------------------------------------------------------------------------------------------------

LAYER_MARKER = "skeldarCamShake"        # on our layers: the shake's record (JSON)
OUR_CAMERA = "mayaSceneSetupCamera"     # the plugin's Camera Setup marks its camera with this
OUR_CONTROL = "mayaSceneSetupCameraControl"   # and the control it stands in (since 2026-10-21)
UNDO = "skeldarCamShake"
STATE = "_skeldar_camshake"             # on sys: a re-dropped script still knows the picked shake
ROTATE = ("rotateX", "rotateY", "rotateZ")
TRANSLATE = ("translateX", "translateY", "translateZ")
SIDES = {"Random": "a random side", "Below": "below", "Above": "above", "Left": "the left",
         "Right": "the right", "Front": "the front"}


class Refused(Exception):
    """A press that changed nothing, and says why."""


def frame_rate():
    import maya.api.OpenMaya as om
    return 1.0 / om.MTime(1.0, om.MTime.uiUnit()).asUnits(om.MTime.kSeconds)


def cm_to_ui():
    import maya.api.OpenMaya as om
    return om.MDistance(1.0, om.MDistance.kCentimeters).asUnits(om.MDistance.uiUnit())


def deg_to_ui():
    return 1.0 if cmds.currentUnit(query=True, angle=True).startswith("deg") else math.pi / 180.0


def leaf(path):
    return path.split("|")[-1]


def highlight():
    """The time slider's highlighted frames (first, last), or None."""
    if cmds.about(batch=True):
        return None
    timebar = sys.modules.get("maya_timebar")            # the Time Bar's own highlight (2026-10-16)
    if timebar is not None:
        try:
            if timebar.active():
                found = timebar.highlight()
                return (int(found[0]), int(found[1]) - 1) if found else None
        except Exception:                                # noqa: BLE001 - Maya's slider then
            pass
    try:
        import maya.mel as mel
        slider = mel.eval("$gPlayBackSlider=$gPlayBackSlider")    # the plugin's own way (overrig.py)
        if not cmds.timeControl(slider, query=True, rangeVisible=True):
            return None
        start, end = cmds.timeControl(slider, query=True, rangeArray=True)
    except Exception:
        return None
    first, last = int(round(start)), int(round(end)) - 1
    return (first, last) if last > first else None


def frames_for(mode, s, given=None):
    """(first, last, where they came from) for a new shake: given, the highlight, else the playback range
    (handheld) or the current frame and Length (impact)."""
    if given is not None:
        a, b, where = int(given[0]), int(given[1]), ""
    else:
        found = highlight()
        if found:
            (a, b), where = found, "the highlight"
        elif mode in ("handheld", "bobbing"):
            a = int(math.floor(cmds.playbackOptions(query=True, minTime=True) + 1e-6))
            b = int(math.ceil(cmds.playbackOptions(query=True, maxTime=True) - 1e-6))
            where = "the playback range"
        else:
            a = int(round(cmds.currentTime(query=True)))
            b = a + int(round(s["length"]))
            where = "the current frame + Length"
    if b <= a:
        raise Refused("frames %d-%d: a shake needs at least 2 frames" % (a, b))
    return a, b, where


def carrier(node):
    """What a shake keys for a node: the Camera Setup camera's control when it stands under one (since
    2026-10-21 the camera itself is locked in it), else the node."""
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    if (parents and cmds.attributeQuery(OUR_CAMERA, node=node, exists=True)
            and cmds.attributeQuery(OUR_CONTROL, node=parents[0], exists=True)):
        return parents[0]
    return node


def our_cameras():
    """Every camera the plugin's Camera Setup made, found by its marker - its control when it has one."""
    found = []
    for shape in cmds.ls(type="camera", long=True) or []:
        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        if parents and cmds.attributeQuery(OUR_CAMERA, node=parents[0], exists=True):
            node = carrier(parents[0])
            if node not in found:
                found.append(node)
    return found


def targets(selection=None):
    """What a new shake shakes: the selected transforms (a shape counts as its transform); nothing
    selected, our camera when there is exactly one."""
    if selection is None:
        names = cmds.ls(selection=True, long=True) or []
    else:
        names = (cmds.ls(selection, long=True) or []) if selection else []
    found = []
    for node in names:
        if cmds.objectType(node, isAType="shape"):
            node = (cmds.listRelatives(node, parent=True, fullPath=True) or [None])[0]
        if node and cmds.objectType(node, isAType="transform"):
            node = carrier(node)
            if node not in found:
                found.append(node)
    if found:
        return found
    ours = our_cameras()
    if len(ours) == 1:
        return ours
    if ours:
        raise Refused("%d cameras of ours (%s) - select the one to shake"
                      % (len(ours), ", ".join(leaf(camera) for camera in ours)))
    raise Refused("select a camera to shake")


def _sources(node, owner=None):
    """What feeds a node; a layer's rotation blend reads its channel's owner's rotateOrder, which is not
    a driver, so the owner is left out."""
    found = cmds.listConnections(node, source=True, destination=False, skipConversionNodes=True) or []
    if owner is None:
        return found
    return [source for source in found if (cmds.ls(source, long=True) or [source])[0] != owner]


def _channel_sources(node, attr):
    found = []
    for plug in ("%s.%s" % (node, attr), "%s.%s" % (node, attr[:-1])):   # rotateX, and rotate
        found += cmds.listConnections(plug, source=True, destination=False, skipConversionNodes=True) or []
    return found


def foreign_driver(node, attr):
    """What drives a channel besides time curves and animation layers, or None."""
    todo, seen = _channel_sources(node, attr), set()
    while todo:
        source = todo.pop()
        if source in seen:
            continue
        seen.add(source)
        kind = cmds.nodeType(source)
        if kind.startswith("animCurveT") or kind == "animLayer":
            continue
        if kind.startswith("animBlendNode"):
            todo += _sources(source, node)
            continue
        return source
    return None


def _driver_message(node, attr, driver):
    text = "%s.%s is driven by %s (%s)" % (leaf(node), attr, leaf(driver), cmds.nodeType(driver))
    if cmds.objectType(driver, isAType="constraint"):
        for source in _sources(driver):
            path = (cmds.ls(source, long=True) or [source])[0]
            if (path != node and cmds.objectType(path, isAType="transform")
                    and cmds.listRelatives(path, shapes=True, type="camera")):
                return text + " - select %s, which drives it" % leaf(path)
    return text + " - a shake needs channels that are keyed or free"


def _upstream_curves(node, attrs):
    """Every curve feeding the channels, through the layers' blend nodes and the layers' weights."""
    curves, todo, seen = [], [], set()
    for attr in attrs:
        todo += _channel_sources(node, attr)
    while todo:
        source = todo.pop()
        if source in seen:
            continue
        seen.add(source)
        kind = cmds.nodeType(source)
        if kind.startswith("animCurve"):
            curves.append(source)
        elif kind.startswith("animBlendNode") or kind == "animLayer":
            todo += _sources(source, node)
    return curves


def _find_curve(layer, plug):
    try:
        return (cmds.animLayer(layer, query=True, findCurveForPlug=plug) or [None])[0]
    except RuntimeError:     # no layers at all
        return None


def _curve_values(curve, frames):
    return np.array([cmds.keyframe(curve, query=True, eval=True, time=(float(f), float(f)))[0]
                     for f in frames], float)


def _layer_share(layer, node, attr, frames):
    """This layer's own share of a channel on each frame: its curve times its weight, 0 when muted."""
    zero = np.zeros(len(frames))
    if not layer or not cmds.objExists(layer) or cmds.animLayer(layer, query=True, mute=True):
        return zero
    curve = _find_curve(layer, "%s.%s" % (node, attr))
    if not curve:
        return zero
    weight = cmds.listConnections(layer + ".weight", source=True, destination=False, type="animCurve") or []
    weights = (_curve_values(weight[0], frames) if weight
               else np.full(len(frames), cmds.getAttr(layer + ".weight")))
    return _curve_values(curve, frames) * weights


def base_rotations(node, layer, frames):
    """What the node's rotate shows on each frame without this layer (deg). Read through every layer, the
    curves upstream dirtied first - a read at another time keeps a stale value per time otherwise - and
    this layer's own share taken off."""
    curves = _upstream_curves(node, ROTATE)
    if curves:
        cmds.dgdirty(curves)
    shown = np.array([cmds.getAttr(node + ".rotate", time=float(f))[0] for f in frames], float)
    for axis, attr in enumerate(ROTATE):
        shown[:, axis] -= _layer_share(layer, node, attr, frames)
    return shown / deg_to_ui()


def _static(node):
    """Its rotate order, rotate axis (deg) and a joint's orient (deg)."""
    unit = deg_to_ui()
    order = ORDERS[cmds.getAttr(node + ".rotateOrder")]
    axis = np.array(cmds.getAttr(node + ".rotateAxis")[0], float) / unit
    orient = (np.array(cmds.getAttr(node + ".jointOrient")[0], float) / unit
              if cmds.nodeType(node) == "joint" else np.zeros(3))
    lens = _lens_turn(node)
    if lens is not None:       # a Camera Setup control: shaken in its camera's axes, the turn between on the left
        m = lens @ euler_matrix(np.radians(axis), "xyz")
        axis = np.degrees(np.array(matrix_eulers(m, "xyz")[0]))
    return order, axis, orient


def _lens_turn(node):
    """For a Camera Setup control: its camera's local rotation (row vectors), else None."""
    if not cmds.attributeQuery(OUR_CONTROL, node=node, exists=True):
        return None
    for child in cmds.listRelatives(node, children=True, type="transform", fullPath=True) or []:
        if cmds.attributeQuery(OUR_CAMERA, node=child, exists=True):
            m = np.array(cmds.xform(child, query=True, matrix=True, objectSpace=True), float).reshape(4, 4)[:3, :3]
            return m / np.linalg.norm(m, axis=1)[:, None]
    return None


def shakes():
    """Every shake of ours in the scene: its layer."""
    return [layer for layer in cmds.ls(type="animLayer") or []
            if cmds.attributeQuery(LAYER_MARKER, node=layer, exists=True)]


def record(layer):
    """A shake's record, or None."""
    if not layer or not cmds.objExists(layer) or not cmds.attributeQuery(LAYER_MARKER, node=layer,
                                                                          exists=True):
        return None
    return parse_record(cmds.getAttr(layer + "." + LAYER_MARKER))


def _uuid(node):
    return cmds.ls(node, uuid=True)[0]


def _node(uuid):
    found = cmds.ls(uuid, long=True) or []
    return found[0] if found else None


def _channels(node, mode, s, layer):
    """(the channels a shake keys on a node, the locked ones skipped): rotate, and translate when it moves
    the camera or the layer holds it already. Refused, by name, when one is driven."""
    attrs = list(ROTATE)
    moves = {"handheld": lambda: s["drift"], "impact": lambda: s["push"],
             "bobbing": lambda: s["bob"] + s["side"] + s["footfall"]}[mode]() > 0.0
    if moves or (layer and any(_find_curve(layer, "%s.%s" % (node, a)) for a in TRANSLATE)):
        attrs += list(TRANSLATE)
    keep, locked = [], []
    for attr in attrs:
        if cmds.getAttr("%s.%s" % (node, attr), lock=True):
            locked.append(attr)
            continue
        driver = foreign_driver(node, attr)
        if driver:
            raise Refused(_driver_message(node, attr, driver))
        keep.append(attr)
    if not [attr for attr in keep if attr in ROTATE]:
        raise Refused("%s's rotate is locked" % leaf(node))
    return keep, locked


def _values(node, index, mode, s, a, b, layer, attrs):
    """(the frames, {channel: what the layer adds on each}) for one node."""
    frames = np.arange(a, b + 1)
    rot, off = shake(mode, frames, a, b, frame_rate(), s, index)
    base = base_rotations(node, layer, frames)
    order, axis, orient = _static(node)
    dr, dt = deltas(rot, off * cm_to_ui(), base, order, axis, orient, heading=mode == "bobbing")
    unit = deg_to_ui()
    table = {}
    for i, attr in enumerate(ROTATE):
        table[attr] = dr[:, i] * unit
    for i, attr in enumerate(TRANSLATE):
        table[attr] = dt[:, i]
    return frames, {attr: table[attr] for attr in attrs}


def _layer_curve(layer, node, attr, first):
    plug = "%s.%s" % (node, attr)
    curve = _find_curve(layer, plug)
    if not curve:
        cmds.setKeyframe(node, attribute=attr, animLayer=layer, time=first, identity=True)
        curve = _find_curve(layer, plug)
    return curve


CONSTANT, CYCLE = 0, 3        # an animCurve's pre / post infinity


def seam_slope(values):
    """A loop's slope at its seam, units a frame: the chord across it (its last frame is its first)."""
    v = np.asarray(values, float)
    return float(v[1] - v[-2]) / 2.0 if len(v) >= 3 else 0.0


def _key(curve, frames, values, loop=False):
    """Keys on every frame (spline), 0 a frame outside each end (flat), and nothing between: the first
    key's in-tangent and the last's out-tangent are straight lines from and to 0. Looped: the frames are one
    cycle (the last shows the first), nothing outside, the curve cycling past them, and both end keys fixed
    on the chord across the seam - a spline's end key takes the slope of one side only (measured in 2027:
    0.77 against 1.29 on either side of a seam, the chord 1.03); a fixed angle's tangent is the slope in
    the curve's units a frame, at film, ntsc and 60 fps alike."""
    a, b = int(frames[0]), int(frames[-1])
    if loop:
        for frame in (a - 1, b + 1):                 # an earlier press's zeros
            cmds.cutKey(curve, time=(frame, frame), clear=True)
    for frame, value in zip(frames, values):
        cmds.setKeyframe(curve, time=int(frame), value=float(value), inTangentType="spline",
                         outTangentType="spline")
    infinity = CYCLE if loop else CONSTANT
    cmds.setAttr(curve + ".preInfinity", infinity)
    cmds.setAttr(curve + ".postInfinity", infinity)
    if loop:
        angle = math.degrees(math.atan(seam_slope(values)))
        for frame in (a, b):
            cmds.keyTangent(curve, time=(frame, frame), lock=False)
            cmds.keyTangent(curve, time=(frame, frame), inTangentType="fixed", outTangentType="fixed",
                            inAngle=angle, outAngle=angle)
        return
    for frame in (a - 1, b + 1):
        cmds.setKeyframe(curve, time=frame, value=0.0, inTangentType="flat", outTangentType="flat")
    for frame, side in ((a, "inTangentType"), (b, "outTangentType")):
        cmds.keyTangent(curve, time=(frame, frame), lock=False)
        cmds.keyTangent(curve, time=(frame, frame), **{side: "linear"})


def _new_layer(mode, a, b):
    name, count = layer_name(mode, a, b), 1
    while cmds.objExists(name):      # Maya would bump the last frame's digits: 0_60 -> 0_101
        count += 1
        name = "%s_v%d" % (layer_name(mode, a, b), count)
    layer = cmds.animLayer(name)
    cmds.setAttr(layer + ".rotationAccumulationMode", 0)      # by component: the eulers add up
    cmds.addAttr(layer, longName=LAYER_MARKER, dataType="string")
    return layer


SEAM_TOLERANCE = 1e-4           # deg / cm: a looped layer's last frame closer to its first than this closes


def seam_gap(values, attrs, unit_deg=1.0, unit_cm=1.0):
    """(deg, cm): how far a looped layer's last frame is from its first - not 0 only when the node's own
    animation does not repeat over the range (the shake does: what the layer adds depends on the turn under
    it)."""
    deg = max([abs(float(values[a][-1] - values[a][0])) / unit_deg for a in attrs if a in ROTATE] or [0.0])
    cm = max([abs(float(values[a][-1] - values[a][0])) / unit_cm for a in attrs if a in TRANSLATE] or [0.0])
    return deg, cm


def seam_text(seams, a, b):
    """The line's word on nodes whose own animation does not loop over a..b."""
    if not seams:
        return ""
    deg = max(d for d, _ in seams.values())
    cm = max(c for _, c in seams.values())
    jump = ", ".join(text for value, text in ((deg, "%.2f deg" % deg), (cm, "%.2f cm" % cm))
                     if value >= SEAM_TOLERANCE)
    return " | %s's own animation differs at frames %d and %d: the loop's seam jumps %s - loop it over the " \
           "range too" % (", ".join(leaf(node) for node in seams), a, b, jump)


def _write(layer, mode, s, a, b, nodes, plans, lock):
    """Every node's keys on the layer; unlocked while writing, then locked (`lock`) or as it was. A loop
    answers {node: (deg, cm)} of the nodes whose seam does not close (`seam_gap`), else {}."""
    seams = {}
    loop = bool(s.get("loop"))
    was = cmds.animLayer(layer, query=True, lock=True)
    if was:
        cmds.animLayer(layer, edit=True, lock=False)
    try:
        for index, (node, attrs) in enumerate(zip(nodes, plans)):
            missing = ["%s.%s" % (node, attr) for attr in attrs
                       if not _find_curve(layer, "%s.%s" % (node, attr))]
            if missing:
                cmds.animLayer(layer, edit=True, attribute=missing)
            frames, values = _values(node, index, mode, s, a, b, layer, attrs)
            for attr in attrs:
                _key(_layer_curve(layer, node, attr, a), frames, values[attr], loop=loop)
            if loop:
                gap = seam_gap(values, attrs, deg_to_ui(), cm_to_ui())
                if max(gap) >= SEAM_TOLERANCE:
                    seams[node] = gap
    finally:
        cmds.animLayer(layer, edit=True, lock=bool(was if lock is None else lock))
    return seams


def _chunk(work):
    """One undo chunk; a failure inside takes back what it did."""
    cmds.undoInfo(openChunk=True, chunkName=UNDO)
    failed = False
    try:
        return work()
    except Exception:
        failed = True
        raise
    finally:
        cmds.undoInfo(closeChunk=True)
        if failed and cmds.undoInfo(query=True, state=True):
            try:
                cmds.undo()
            except Exception:
                pass


def replaced(mode, uuids):
    """The shakes an Apply in `mode` on these cameras replaces: every shake of that mode holding any of
    them - a camera has one handheld layer and one impact layer. [(layer, its record)]."""
    found = []
    for layer in shakes():
        data = record(layer)
        if data and data["mode"] == mode and set(data["targets"]) & set(uuids):
            found.append((layer, data))
    return found


def apply_targets(mode, selection=None):
    """What an Apply shakes: the selection; nothing selected, the cameras of the picked shake when it is
    of this mode, else what `targets` takes."""
    if selection is None and not (cmds.ls(selection=True) or []):
        layer = picked()
        data = record(layer)
        if data and data["mode"] == mode:
            nodes = [_node(uuid) for uuid in data["targets"]]
            if None not in nodes:
                return nodes
    return targets(selection)


def _layer_plugs(layer):
    try:
        return list(cmds.animLayer(layer, query=True, attribute=True) or [])
    except Exception:                                        # noqa: BLE001
        return []


def _delete_layer(layer):
    """The layer gone, and the unkeyed channels it held standing where they stand without it: deleted, a
    layer leaves the value its blend last evaluated in what fed it - a static channel's base, or the base
    of the layer above - so the shake at the current frame stays behind for good (measured in 2027: -15
    left at -13.03, and -19.41 in the layer above). Muted and evaluated first, it leaves the stack without
    it. Giving a camera's channels back (`removeAttribute`) leaves none (measured)."""
    plugs = _layer_plugs(layer)
    if plugs:
        cmds.animLayer(layer, edit=True, mute=True)
        for plug in plugs:
            try:
                cmds.getAttr(plug)
            except Exception:                                # noqa: BLE001 - a plug gone
                pass
    cmds.delete(layer)


def _take_off(old, uuids):
    """The replaced shakes go: a layer holding only these cameras is deleted, one holding others too
    loses these cameras' channels and keeps shaking the rest. Answers the names, for the line."""
    names = []
    for layer, data in old:
        rest = [uuid for uuid in data["targets"] if uuid not in uuids]
        if not rest:
            if picked() == layer:
                pick(None)
            _delete_layer(layer)
            names.append(layer)
            continue
        plugs = []
        for uuid in data["targets"]:
            node = _node(uuid)
            if uuid in uuids and node:
                plugs += ["%s.%s" % (node, attr) for attr in ROTATE + TRANSLATE
                          if _find_curve(layer, "%s.%s" % (node, attr))]
        was = cmds.animLayer(layer, query=True, lock=True)
        cmds.animLayer(layer, edit=True, lock=False)
        try:
            if plugs:
                cmds.animLayer(layer, edit=True, removeAttribute=plugs)
        finally:
            cmds.animLayer(layer, edit=True, lock=bool(was))
        a, b = data["frames"]
        cmds.setAttr(layer + "." + LAYER_MARKER, record_text(data["mode"], data["settings"], a, b, rest),
                     type="string")
        names.append("%s (other cameras kept)" % layer)
    return names


def loop_text(mode, s, a, b, fps):
    """What a loop says on the line: the cycle, and a bobbing's tempo and strides fitted to it."""
    if not s.get("loop"):
        return ""
    text = " | looped: frame %d shows frame %d, the layer cycles past them" % (b, a)
    if mode == "bobbing" and fps:
        tempo, strides = loop_tempo(s["tempo"], b - a, fps)
        text += " | %d stride%s in the loop" % (strides, "" if strides == 1 else "s")
        if abs(tempo - s["tempo"]) > 0.05:
            text += " at %g steps/min (Tempo %g)" % (round(tempo, 1), round(s["tempo"], 1))
    return text


def describe(mode, s, a, b, nodes, layer, where="", locked=(), fps=None):
    names = ", ".join(leaf(node) for node in nodes)
    if mode == "handheld":
        what = "Handheld: sway %.2f deg, jitter %.2f deg at %g Hz, drift %.1f cm" % (
            s["sway"], s["jitter"], s["jitter_hz"], s["drift"])
    elif mode == "bobbing":
        what = "Bobbing: %s at %g steps/min, bob %.1f cm, sway %.1f cm, nod %.1f deg, %s foot first" % (
            s["gait"].lower(), round(s["tempo"], 1), s["bob"], s["side"], s["nod"], s["foot"].lower())
    else:
        what = "Impact from %s: %.1f deg, waves of %g fr, %s decay, push %.1f cm, rattle %.2f deg at %g Hz" % (
            SIDES[s["direction"]], s["strength"], s["wave"], s["decay"].lower(), s["push"], s["rattle"],
            s["rattle_hz"])
    off = [label.lower() for key, label in AXES if not s.get(key, True)]
    if off:
        what += " (no %s)" % ", ".join(off)
    text = "%s on %s, frames %d-%d%s | layer %s, its weight is the strength" % (
        what, names, a, b, " (%s)" % where if where else "", layer)
    text += loop_text(mode, s, a, b, fps)
    skipped = sorted({attr for attrs in locked for attr in attrs})
    if skipped:
        text += " | locked, not shaken: " + ", ".join(skipped)
    return text


def apply(mode, given=None, selection=None, frames=None):
    """A new shake on the selection over the highlight, in a new layer; the shake of the same mode those
    cameras had is taken off first (a camera keeps one handheld layer and one impact layer, each its own).
    Picked. (layer, message)."""
    s = settings(mode, given)
    nodes = apply_targets(mode, selection)
    a, b, where = frames_for(mode, s, frames)
    uuids = [_uuid(node) for node in nodes]
    old = replaced(mode, uuids)
    plans = [_channels(node, mode, s, None) for node in nodes]
    gone, seams = [], {}

    def work():
        gone.extend(_take_off(old, uuids))
        target = _new_layer(mode, a, b)
        seams.update(_write(target, mode, s, a, b, nodes, [plan[0] for plan in plans], lock=True))
        cmds.setAttr(target + "." + LAYER_MARKER, record_text(mode, s, a, b, uuids), type="string")
        return target

    made = _chunk(work)
    pick(made)
    text = describe(mode, s, a, b, nodes, made, where, [plan[1] for plan in plans], frame_rate())
    text += seam_text(seams, a, b)
    if gone:
        text += " | replaced " + ", ".join(gone)
    return made, text


def retune(layer, given):
    """The shake re-keyed with new settings on its own cameras and frames; the layer, its weight and its
    lock kept."""
    found = record(layer)
    if found is None:
        raise Refused("%s is not a shake of ours" % layer)
    mode = found["mode"]
    s = settings(mode, given)
    a, b = found["frames"]
    nodes = [_node(uuid) for uuid in found["targets"]]
    if None in nodes:
        raise Refused("a camera of %s is gone - delete the shake" % layer)
    plans = [_channels(node, mode, s, layer) for node in nodes]
    seams = {}

    def work():
        seams.update(_write(layer, mode, s, a, b, nodes, [plan[0] for plan in plans], lock=None))
        cmds.setAttr(layer + "." + LAYER_MARKER, record_text(mode, s, a, b, found["targets"]),
                     type="string")

    _chunk(work)
    return describe(mode, s, a, b, nodes, layer, "", [plan[1] for plan in plans], frame_rate()) + \
        seam_text(seams, a, b)


def delete(layer):
    if record(layer) is None:
        raise Refused("pick a shake to delete")
    name = layer
    if picked() == layer:
        pick(None)
    _chunk(lambda: _delete_layer(layer))
    return "deleted %s" % name


def _state():
    state = getattr(sys, STATE, None)
    if state is None:
        state = {"picked": None}
        setattr(sys, STATE, state)
    return state


def picked():
    """The shake the window edits, or None."""
    uuid = _state().get("picked")
    layer = (cmds.ls(uuid) or [None])[0] if uuid else None
    return layer if record(layer) else None


def pick(layer):
    _state()["picked"] = _uuid(layer) if layer else None


def editor_pick():
    """The shake of ours selected in the Anim Layer Editor, when exactly one is."""
    chosen = [layer for layer in shakes() if cmds.animLayer(layer, query=True, selected=True)]
    return chosen[0] if len(chosen) == 1 else None


# ---------------------------------------------------------------------------------------------------------
# 4. The hub card (cmds) - Camera Shake
# ---------------------------------------------------------------------------------------------------------

HUB_SECTION = "camshake"
SUBTITLE = "skeldarCamShakeSubtitle"
STATUS = "skeldarCamShakeStatus"
SHAKE_MENU = "skeldarCamShakeShake"
DELETE_BTN = "skeldarCamShakeDelete"
MODE_TABS = "skeldarCamShakeModes"
PRESET_MENU = "skeldarCamShakePreset"
DIRECTION_MENU = "skeldarCamShakeDirection"
DECAY_MENU = "skeldarCamShakeDecay"
GAIT_MENU = "skeldarCamShakeGait"
FOOT_MENU = "skeldarCamShakeFoot"
SEED_FIELD = "skeldarCamShakeSeed"
SEED_BTN = "skeldarCamShakeNewSeed"
APPLY_BTN = "skeldarCamShakeApply"
NEW = "+ New shake"
PRESET_PROMPT = "Presets..."
#  The memory keeps the standalone script's names (2026-10-13): what the animator set there comes back.
OPTION = "skeldarCamShake_"          # + mode: that mode's settings (JSON); + "mode": the last mode
TIPS = {
    "sway": "The body's slow drift and the hands' corrections, degrees at the extremes",
    "speed": "Calm to nervous: how fast the sway and the drift wander",
    "jitter": "The hands' tremor, degrees",
    "jitter_hz": "The tremor's rate, up to 0.42 of the frame rate (12.6 Hz at 30 fps)",
    "roll": "How much of the turning rolls the horizon",
    "drift": "The camera's own travel, cm",
    "ease": "Frames to fade the shake in and out at the range's ends (0: a cut)",
    "strength": "How far the first swing turns the view, degrees",
    "push": "How far the hit knocks the camera, cm",
    "wave": "Frames from crest to crest of the hit's swings",
    "rattle": "A fast fine vibration on top, degrees - it dies before the swings do",
    "rattle_hz": "The rattle's rate, up to 0.42 of the frame rate",
    "length": "Frames the hit takes to settle when no range is highlighted",
    "shake": "+ New shake: Apply makes one, replacing the shake of the same mode on those cameras. A shake of ours: the controls re-key it as they change",
    "delete": "Delete the picked shake's layer (one undo)",
    "preset": "Fill the controls with a preset (the seed, ease, length and axes are kept)",
    "direction": "Where the hit comes from: the camera is knocked the other way",
    "decay": "How the swings die by the end of the range",
    "axes": "Tilt: up-down, Pan: left-right, Roll: the horizon. Off removes that turn whole",
    "seed": "Another shake of the same kind",
    "apply": "A new shake on the selected camera over the highlighted frames, on a layer of its own",
    "pace": "Fills the gait, Tempo, Bob, Sway, Nod, Turn and Softness from the gait guide's measurements at this speed - then tune them",
    "tempo": "Steps a minute: walking 100-130, running 160-185, a sprint up to ~260",
    "bob": "Up and down, cm from the lowest to the highest - twice a stride",
    "side": "Side to side toward the foot on the ground, cm - once a stride",
    "nod": "The head pitched down as the body rises, degrees",
    "turn": "The head's turn toward the striking foot, degrees - once a stride",
    "lean": "The horizon tilted toward the foot on the ground, degrees",
    "footfall": "A short jolt down at every contact, degrees (and half as many cm)",
    "softness": "Walk: the low rounded over the double support. Run: a longer stance, a shorter flight",
    "variation": "Each step a little different in size, % (the seed picks how)",
    "contact": "Frames after the range's start of the first contact",
    "gait": "Walk: low just after each contact, high when passing. Run: low mid-stance, high in the flight",
    "foot": "The foot of the first contact: sway, roll and turn go toward it first",
    "loop": "The range is one cycle: its last frame shows what its first does, and the layer cycles past it. "
            "The noise fits it whole; a bobbing's tempo is the nearest that fits whole strides. No Ease. "
            "Loop the camera's own animation too, or the seam shows its jump",
}
STEPS = {"jitter_hz": 0.5, "rattle_hz": 0.5, "ease": 1.0, "length": 1.0, "wave": 0.5, "tempo": 1.0,
         "softness": 1.0, "variation": 1.0, "contact": 1.0, "pace": 0.1}
NOTHING = "Select a camera - Apply shakes it over the highlighted frames"
#  The refresh jobs of each card standing: '' the hub's, a popup copy's tag its own (the 2026-10-09 rule:
#  closing a popup kills only its own jobs).
JOB = {}
_QUIET = [False]                     # filling controls from code must not run their commands


def _mode_tab(mode):
    return "skeldarCamShakeMode_" + mode


def _mode_column(mode):
    return "skeldarCamShakeColumn_" + mode


def _slider(mode, name):
    return "%s%s_%s" % (OPTION, mode, name)


def _axis_chip(key):
    return "skeldarCamShakeAxis_" + key


def _loop_chip(mode):
    return "skeldarCamShakeLoop_" + mode


def remembered(mode):
    key = OPTION + mode
    try:
        return settings(mode, json.loads(cmds.optionVar(query=key)) if cmds.optionVar(exists=key) else None)
    except (TypeError, ValueError):
        return settings(mode)


def remember(mode, s):
    cmds.optionVar(stringValue=(OPTION + mode, json.dumps(s, sort_keys=True)))


def _remembered_mode():
    key = OPTION + "mode"
    mode = cmds.optionVar(query=key) if cmds.optionVar(exists=key) else None
    return mode if mode in MODES else MODES[0]


def current_mode():
    """The mode the card shows, else the one remembered."""
    for mode in MODES:
        if cmds.iconTextRadioButton(_mode_tab(mode), exists=True) and \
                cmds.iconTextRadioButton(_mode_tab(mode), query=True, select=True):
            return mode
    return _remembered_mode()


def _read(mode):
    """The mode's settings as the card shows them; with the card closed, as remembered."""
    if not cmds.floatSliderGrp(_slider(mode, CONTROLS[mode][0][0]), exists=True):
        return remembered(mode)
    given = {name: cmds.floatSliderGrp(_slider(mode, name), query=True, value=True)
             for name, _, _, _, _ in CONTROLS[mode]}
    given["seed"] = cmds.intField(SEED_FIELD, query=True, value=True)
    for key, _ in AXES:
        given[key] = bool(cmds.checkBox(_axis_chip(key), query=True, value=True))
    if mode == "impact":
        given["direction"] = cmds.optionMenu(DIRECTION_MENU, query=True, value=True)
        given["decay"] = cmds.optionMenu(DECAY_MENU, query=True, value=True)
    if mode == "bobbing":
        given["gait"] = cmds.optionMenu(GAIT_MENU, query=True, value=True)
        given["foot"] = cmds.optionMenu(FOOT_MENU, query=True, value=True)
    if mode in LOOP_MODES:
        given["loop"] = bool(cmds.checkBox(_loop_chip(mode), query=True, value=True))
    return settings(mode, given)


def values(mode=None):
    """The settings a press uses: the card's (remembered) where it stands, else the remembered ones - so a
    hotkey row presses with the card closed."""
    mode = mode or current_mode()
    s = _read(mode)
    remember(mode, s)
    return s


def _quietly(work):
    _QUIET[0] = True
    try:
        work()
    finally:
        _QUIET[0] = False


def _show_settings(mode, s):
    def work():
        for name, _, _, _, _ in CONTROLS[mode]:
            cmds.floatSliderGrp(_slider(mode, name), edit=True, value=s[name])
        cmds.intField(SEED_FIELD, edit=True, value=s["seed"])
        for key, _ in AXES:
            cmds.checkBox(_axis_chip(key), edit=True, value=bool(s[key]))
        if mode == "impact":
            cmds.optionMenu(DIRECTION_MENU, edit=True, value=s["direction"])
            cmds.optionMenu(DECAY_MENU, edit=True, value=s["decay"])
        if mode == "bobbing":
            cmds.optionMenu(GAIT_MENU, edit=True, value=s["gait"])
            cmds.optionMenu(FOOT_MENU, edit=True, value=s["foot"])
        if mode in LOOP_MODES:
            cmds.checkBox(_loop_chip(mode), edit=True, value=bool(s["loop"]))
            _show_loop(mode, s["loop"])
    if cmds.intField(SEED_FIELD, exists=True):
        _quietly(work)


def _show_loop(mode, loop):
    """A loop has no ends to fade: its Ease is dimmed."""
    cmds.floatSliderGrp(_slider(mode, "ease"), edit=True, enable=not loop)


def _fill_menu(menu, labels, selected):
    for item in cmds.optionMenu(menu, query=True, itemListLong=True) or []:
        cmds.deleteUI(item, menuItem=True)
    for label in labels:
        cmds.menuItem(label=label, parent=menu)
    cmds.optionMenu(menu, edit=True, value=selected)


def _show_mode(mode):
    """The card on a mode: its tab lit, its column shown, its presets in the list."""
    def work():
        cmds.iconTextRadioButton(_mode_tab(mode), edit=True, select=True)
        for each in MODES:
            cmds.columnLayout(_mode_column(each), edit=True, manage=each == mode)
        _fill_menu(PRESET_MENU, [PRESET_PROMPT] + [label for label, _ in PRESETS[mode]], PRESET_PROMPT)
    if cmds.iconTextRadioButton(_mode_tab(mode), exists=True):
        _quietly(work)
    cmds.optionVar(stringValue=(OPTION + "mode", mode))


def status(text):
    """The card's line - and the hub's one message line. Answers the text, so a hotkey row can show it when
    the card is closed."""
    import maya_hubstyle as hubstyle
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
        hubstyle.tell(STATUS, text)
    return text


def _press(action):
    try:
        message = action()
    except Refused as refusal:
        message = str(refusal)
    except Exception as error:                               # noqa: BLE001 - the card stays usable
        import traceback
        print(traceback.format_exc())
        message = "Camera Shake failed: %s" % error
    refresh()
    return status(message)


def _node_names(found):
    return ", ".join(leaf(_node(uuid) or "?") for uuid in found["targets"])


def _label(layer):
    found = record(layer)
    return "%s - %s" % (layer, _node_names(found)) if found else layer


def selection_line():
    """The card's subtitle: the shake it edits, else what Apply would take."""
    layer = picked()
    if layer:
        found = record(layer)
        return "Editing %s: %s, frames %d-%d%s" % (layer, _node_names(found), found["frames"][0],
                                                   found["frames"][1],
                                                   ", looped" if found["settings"].get("loop") else "")
    mode = current_mode()
    try:
        nodes = apply_targets(mode)
        s = _read(mode)
        a, b, where = frames_for(mode, s)
    except Refused as refusal:
        return NOTHING if "select a camera" in str(refusal) else str(refusal)
    text = "New %s%s shake on %s, frames %d-%d (%s)" % ("looped " if s.get("loop") else "", mode,
                                                         ", ".join(leaf(n) for n in nodes), a, b, where)
    old = replaced(mode, [_uuid(node) for node in nodes])
    if old:
        text += " - replaces " + ", ".join(layer for layer, _ in old)
    return text


def refresh(*_):
    """The subtitle and the list of shakes."""
    if not cmds.text(SUBTITLE, exists=True):
        return
    try:
        layer = picked()
        labels = [_label(each) for each in shakes()]
        _quietly(lambda: _fill_menu(SHAKE_MENU, [NEW] + labels, _label(layer) if layer else NEW))
        cmds.text(SUBTITLE, edit=True, label=selection_line())
    except Exception:                                        # noqa: BLE001 - a refresh never raises
        return


def _load(layer):
    """The card shows a shake: its mode and settings."""
    found = record(layer)
    if found:
        _show_mode(found["mode"])
        _show_settings(found["mode"], found["settings"])
        remember(found["mode"], found["settings"])


def _changed(mode):
    """A control moved: the picked shake re-keyed with it, else the next Apply set up."""
    def run():
        s = values(mode)
        layer = picked()
        if layer and record(layer)["mode"] == mode:
            return retune(layer, s)
        return "Set for the next Apply."
    return _press(run)


def slider_changed(mode):
    def go(*_):
        if not _QUIET[0]:
            _changed(mode)
    return go


def pace_changed(*_):
    """Speed let go: the gait's knobs filled from the guide's formula at that speed, the style kept."""
    if _QUIET[0]:
        return
    s = _read("bobbing")
    s.update(from_speed(s["pace"]))
    _show_settings("bobbing", settings("bobbing", s))
    _changed("bobbing")


def preset_changed(*_):
    if _QUIET[0]:
        return
    name = cmds.optionMenu(PRESET_MENU, query=True, value=True)
    if name == PRESET_PROMPT:
        return
    mode = current_mode()
    _show_settings(mode, preset(mode, name, _read(mode)))
    _quietly(lambda: cmds.optionMenu(PRESET_MENU, edit=True, value=PRESET_PROMPT))
    _changed(mode)


def mode_changed(mode):
    def go(*_):
        if _QUIET[0]:
            return
        pick(None)
        _show_mode(mode)
        _show_settings(mode, remembered(mode))
        refresh()
    return go


def shake_changed(*_):
    if _QUIET[0]:
        return
    label = cmds.optionMenu(SHAKE_MENU, query=True, value=True)
    layer = next((each for each in shakes() if _label(each) == label), None)
    pick(layer)
    if layer:
        _load(layer)
    refresh()


def press_delete(*_):
    layer = picked()
    if not layer:
        return status("Pick a shake to delete.")
    return _press(lambda: delete(layer))


def press_new_seed(*_):
    mode = current_mode()
    s = _read(mode)
    s["seed"] = int(np.random.default_rng().integers(1, 100000))
    _show_settings(mode, s)
    remember(mode, s)
    return _changed(mode)


def press_apply(*_):
    """Apply: a new shake on the selection over the highlighted frames, in the card's mode."""
    mode = current_mode()
    return _press(lambda: apply(mode, values(mode))[1])


def _editor_memo():
    return _state().setdefault("editor", {})


def from_editor(*_):
    """A shake of ours newly selected in the Anim Layer Editor is the one this card edits; the same one
    still selected there does not take the card back from + New shake."""
    layer = editor_pick()
    memo = _editor_memo()
    if memo.get(_card_key()) == layer:
        return
    memo[_card_key()] = layer
    if layer and layer != picked():
        pick(layer)
        _load(layer)
        refresh()


def after_undo(*_):
    """An undo or a redo can change the picked shake's settings under the card: show them again."""
    layer = picked()
    if layer:
        _load(layer)
    refresh()


def _menu_row(menu, label, command, tip, button=None):
    """A word, a dropdown, and an optional tool button (the Walk Builder's row)."""
    import maya_hubstyle as hubstyle
    cmds.rowLayout(numberOfColumns=3 if button else 2, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 3)] + ([(3, "left", 3)] if button else []))
    cmds.text(label=label, width=hubstyle.pick(52, 56), align="left")
    cmds.optionMenu(menu, changeCommand=command, annotation=tip)
    if button:
        name, text, icon, tool_tip, press = button
        hubstyle.mark(cmds.button(name, label=hubstyle.tool_label(text), width=hubstyle.tool_width(56),
                                  height=hubstyle.height("field", 24), annotation=tool_tip,
                                  command=lambda *_: press()), "tool", icon)
    cmds.setParent("..")


def _sliders(mode, s):
    import maya_hubstyle as hubstyle
    for name, label, _, low, high in CONTROLS[mode]:
        cmds.floatSliderGrp(_slider(mode, name), label=label, field=True, minValue=low, maxValue=high,
                            fieldMinValue=low, fieldMaxValue=high, step=STEPS.get(name, 0.05), precision=2,
                            value=s[name], columnWidth3=hubstyle.pick((92, 44, 100), (100, 50, 150)),
                            adjustableColumn=3, height=hubstyle.height("small", 22), annotation=TIPS[name],
                            changeCommand=pace_changed if name == "pace" else slider_changed(mode))


def build_panel():
    """The card into the current layout: what Apply would take (or the shake edited); the shake list and
    Delete; Handheld | Impact; the presets; the axes; the mode's controls; the seed; Apply; the status."""
    import maya_hubstyle as hubstyle
    shown = _remembered_mode()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label=NOTHING, align="left"), "subtitle")
    _menu_row(SHAKE_MENU, "Shake", shake_changed, TIPS["shake"],
              (DELETE_BTN, "Delete", "trash", TIPS["delete"], press_delete))
    cmds.menuItem(label=NEW, parent=SHAKE_MENU)
    segments = cmds.rowLayout(numberOfColumns=len(MODES), columnAttach=[(i + 1, "both", 1)
                                                                        for i in range(len(MODES))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(MODE_TABS)
    for mode in MODES:
        hubstyle.mark(cmds.iconTextRadioButton(
            _mode_tab(mode), style="textOnly", label=mode.capitalize(), height=hubstyle.height("segment", 24),
            select=mode == shown, collection=MODE_TABS,
            annotation="Handheld: an operator holding the camera. Impact: a hit that dies by the range's end. "
                       "Bobbing: a walk's or a run's steps",
            onCommand=mode_changed(mode)), "segment")
    cmds.setParent("..")
    _menu_row(PRESET_MENU, "Preset", preset_changed, TIPS["preset"])
    cmds.menuItem(label=PRESET_PROMPT, parent=PRESET_MENU)
    stored = remembered(shown)

    def chip(key, label):
        hubstyle.mark(cmds.checkBox(_axis_chip(key), label=label, value=bool(stored[key]),
                                    annotation=TIPS["axes"], changeCommand=lambda *_: _chip_changed()), "chip")
    if hubstyle.skinning():
        hubstyle.mark(cmds.flowLayout(wrap=True, columnSpacing=3), "flow", layout=True)
    else:
        cmds.rowLayout(numberOfColumns=len(AXES))
    for key, label in AXES:
        chip(key, label)
    cmds.setParent("..")
    for mode in MODES:
        cmds.columnLayout(_mode_column(mode), adjustableColumn=True, rowSpacing=hubstyle.row_spacing(2),
                          manage=mode == shown)
        s = remembered(mode)
        if mode == "impact":
            _menu_row(DIRECTION_MENU, "Hit from", slider_changed("impact"), TIPS["direction"])
            for direction in DIRECTIONS:
                cmds.menuItem(label=direction, parent=DIRECTION_MENU)
            _menu_row(DECAY_MENU, "Decay", slider_changed("impact"), TIPS["decay"])
            for decay in DECAYS:
                cmds.menuItem(label=decay, parent=DECAY_MENU)
        if mode == "bobbing":
            _menu_row(GAIT_MENU, "Gait", slider_changed("bobbing"), TIPS["gait"])
            for gait in GAITS:
                cmds.menuItem(label=gait, parent=GAIT_MENU)
            _menu_row(FOOT_MENU, "First foot", slider_changed("bobbing"), TIPS["foot"])
            for foot in FEET:
                cmds.menuItem(label=foot, parent=FOOT_MENU)
        if mode in LOOP_MODES:
            if hubstyle.skinning():
                hubstyle.mark(cmds.flowLayout(wrap=True, columnSpacing=3), "flow", layout=True)
            else:
                cmds.rowLayout(numberOfColumns=1)
            hubstyle.mark(cmds.checkBox(_loop_chip(mode), label="Loop", value=bool(s["loop"]),
                                        annotation=TIPS["loop"], changeCommand=loop_changed(mode)), "chip")
            cmds.setParent("..")
        _sliders(mode, s)
        if mode in LOOP_MODES:
            _show_loop(mode, s["loop"])
        cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 3), (3, "left", 3)])
    cmds.text(label="Seed", width=hubstyle.pick(52, 56), align="left")
    cmds.intField(SEED_FIELD, value=stored["seed"], minValue=0, height=hubstyle.height("field", 24),
                  annotation=TIPS["seed"], changeCommand=lambda *_: _chip_changed())
    hubstyle.mark(cmds.button(SEED_BTN, label=hubstyle.tool_label("New seed"), width=hubstyle.tool_width(70),
                              height=hubstyle.height("field", 24), annotation=TIPS["seed"],
                              command=lambda *_: press_new_seed()), "tool", "refresh")
    cmds.setParent("..")
    hubstyle.mark(cmds.rowLayout(numberOfColumns=1, adjustableColumn=1, columnAttach=[(1, "both", 0)]),
                  "fill", layout=True)
    hubstyle.mark(cmds.button(APPLY_BTN, label="Apply", height=hubstyle.height("button", 28),
                              annotation=TIPS["apply"], command=lambda *_: press_apply()), "primary", "video")
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    cmds.setParent("..")
    _show_mode(shown)
    _show_settings(shown, stored)
    start()
    _editor_memo()[_card_key()] = editor_pick()
    refresh()
    return column


def _chip_changed():
    if not _QUIET[0]:
        _changed(current_mode())


def loop_changed(mode):
    """The Loop chip: Ease dimmed while it is on, the picked shake re-keyed (else the next Apply set up)."""
    def go(*_):
        if _QUIET[0]:
            return
        _show_loop(mode, bool(cmds.checkBox(_loop_chip(mode), query=True, value=True)))
        _changed(mode)
    return go


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    """This card's own jobs: the selection, the Anim Layer Editor, undo and redo (per card: a popup copy's
    jobs die with the copy and leave the hub's)."""
    import maya_hubcopy as hubcopy
    standing = set(scope.tag for scope in hubcopy.live())
    for key in [k for k in JOB if k and k not in standing]:
        del JOB[key]
    for old in JOB.pop(_card_key(), []):
        try:
            if cmds.scriptJob(exists=old):
                cmds.scriptJob(kill=old, force=True)
        except Exception:                                    # noqa: BLE001
            pass
    import maya_hubqt
    jobs = []
    #  a hidden card refreshes when it is next shown (2026-10-17, maya_hubqt.when_seen); the
    #  editor's pick is followed whatever shows - the next Apply acts on it
    for event, work in (("SelectionChanged", maya_hubqt.seen_only(STATUS, refresh)),
                        ("animLayerRefresh", from_editor),
                        ("Undo", maya_hubqt.seen_only(STATUS, after_undo)),
                        ("Redo", maya_hubqt.seen_only(STATUS, after_undo))):
        try:
            jobs.append(cmds.scriptJob(event=[event, work], parent=STATUS))
        except Exception:                                    # noqa: BLE001 - an event this Maya lacks
            pass
    JOB[_card_key()] = jobs


def is_open():
    return bool(cmds.text(STATUS, exists=True))


def show_window():
    """The hub, on the Camera Shake section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
