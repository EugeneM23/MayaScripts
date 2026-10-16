"""maya_walk.model - the parametric walk's model: a walk cycle read once, rebuilt from knobs.

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
    ("in_place", 0.0, 0.0, 1.0),
    ("foot_placement", 1.0, 0.0, 1.0),
    ("ground_time", 1.0, 0.7, 1.8),
    ("stance", 1.0, 0.0, 2.5),
    ("swing_out", 0.0, -30.0, 40.0),
    ("leg_match", 1.0, 0.0, 1.0),
    ("leg_turn", 1.0, 0.0, 2.0),
    ("knee_foot", 0.5, 0.0, 1.0),
    ("foot_lag", 0.0, 0.0, 6.0),
    ("foot_flex", 1.0, 0.0, 3.0),
    ("bob", 1.0, 0.0, 3.0),
    ("sway", 1.0, 0.0, 3.0),
    ("surge", 1.0, 0.0, 3.0),
    ("root_sway", 0.0, 0.0, 1.0),
    ("pelvis_height", 0.0, -40.0, 40.0),
    ("pelvis_forward", 0.0, -30.0, 30.0),
    ("pelvis_rot", 1.0, 0.0, 3.0),
    ("pelvis_twist", 5.0, -5.0, 40.0),
    ("pelvis_list", 4.0, -5.0, 10.0),
    ("spine", 1.0, 0.0, 3.0),
    ("chest_twist", 7.0, -5.0, 60.0),
    ("chest_sway", 5.0, -5.0, 15.0),
    ("gait_lean", 1.0, 0.0, 1.0),
    ("torso_drag", 1.5, 0.0, 8.0),
    ("torso_bounce", 0.2, 0.0, 1.0),
    ("arms", 1.0, 0.0, 3.0),
    ("elbow", 1.0, 0.0, 3.0),
    ("arm_drag", 1.5, 0.0, 8.0),
    ("arm_bounce", 0.3, 0.0, 1.0),
    ("head", 1.0, 0.0, 3.0),
    ("head_drag", 2.0, 0.0, 8.0),
    ("overlap", 0.0, 0.0, 6.0),
    ("weight", 0.0, -1.0, 2.0),
    ("balance", 1.0, 0.0, 1.0),
    ("exaggeration", 1.0, 0.0, 2.0),
)
DEFAULTS = dict((k[0], k[1]) for k in KNOBS)
RANGES = dict((k[0], (k[2], k[3])) for k in KNOBS)
#  The knobs of a body part that has two sides (2026-10-13: «режим в котором левая и правая сторона станут
#  раздельными»): "<name>_l" / "<name>_r" set that side alone; without them both sides take "<name>".
SIDED = ("stance", "lift", "swing_out", "leg_turn", "knee_foot", "foot_lag", "foot_flex", "ground_time",
         "arms", "elbow", "arm_drag", "arm_bounce")
SIDE_KNOBS = dict(("%s_%s" % (name, side), name) for name in SIDED for side in ("l", "r"))

WEIGHT_BOB_DOWN = 0.5     # the bob's low half x (1 + this . weight)
WEIGHT_BOB_UP = 0.15      # its high half x max(0, 1 - this . weight)
WEIGHT_WARP = 0.3         # the bob's clock: beta = this . weight
WEIGHT_WARP_AFTER = 0.05  # slowest this share of a cycle after each low
WEIGHT_LAG = 1.0          # frames of overlap per unit of weight
LOWER_BLUR = 0.06         # the reach's drop of the pelvis, smoothed over this share of a cycle (sigma)

# the legs and the pelvis (docs/superpowers/specs/2026-10-12-walk-legs-design.md)
TWIST_FREE_DEG = 15.0     # the shin's own twist a knee may keep against its foot; past it they meet (Knee <-> foot)
SWING_EASE = 0.25         # the swinging foot hangs off its shin from this share of the swing to this share before it
BALL_LAG = 1.5            # the toes lag the shin this many times the foot's lag
STEP_REF = 0.8            # a normal step, in legs: Twist is the pelvis's twist at it, growing with the step
LIST_PEAK = 0.17          # the standing hip highest this share of a cycle after its heel strike (the norm)
AIR_STEPS = 64            # a foot's flight found to 1/this of a frame
COUNTER_SHARES = (0.4, 0.35, 0.25)   # spine_01..03 take the pelvis's added twist and drop back, these shares
CHEST_SHARES = (0.25, 0.35, 0.4)     # the top three spine joints take the chest's added twist and sway, these shares
CHEST_STILL = 0.5                    # degrees: a walk's own chest turn below this has no shape of its own
# Leg match (docs/superpowers/specs/2026-10-14-walk-sprint-legs-and-body-design.md): a pose's stance (its splay and
# width) kept 1 / (1 + Fr / GAIT_FROUDE) by a gait of Froude number Fr = v^2 / (g L) - a walk keeps most of it,
# a sprint little: a fast leg swings in the line of travel
GAIT_FROUDE = 1.0
# Gait lean: under a pose's torso the walk's own forward lean over its rest is put back, in the room the pose leaves
# to this lean of the trunk (degrees from up; the stop builder's rule, docs/superpowers/specs/2026-10-14-pose-on-clip)
LEAN_LIMIT = 90.0

# the arms follow the body with inertia (docs/superpowers/specs/2026-10-12-walk-upper-body-design.md)
ARM_SUBSTEPS = 4          # the arms' motion integrated at least this many steps a frame
ARM_CYCLES = 8            # at most this many cycles run to settle the arms' periodic motion
ARM_SETTLED = 1e-5        # radians: settled when a cycle's start moves less than this from the last's
ARM_INERTIA = 1.0         # x the shoulder's (elbow's, wrist's) acceleration felt by the limb below it
ARM_HARMONICS = 6         # the shoulder's path the arms feel: its first this many harmonics a stride (the body's motion)
ACCEL_HZ = 8.0            # ...and none faster than this many a second: a sprint's stride is 15 frames, and 6 harmonics of
                          # it reached a 2.5-frame period - the frames' own noise (AGS_Sprint, 2026-10-14)
# the trunk and the head on springs (docs/superpowers/specs/2026-10-14-walk-sprint-legs-and-body-design.md)
BODY_INERTIA = 1.0        # x the pivot's acceleration felt by the trunk on its lever
HEAD_INERTIA = 0.3        # ...and by the head on the neck: a head is held - at 1 a sprint's steps bobbed it 12 deg off
                          # its gaze, noisier than the clip; at 0.3 it is calmer than the clip (AGS_Sprint, 2026-10-14)
HEAD_LIFT = 0.5           # the head's mass point: past the head joint by this share of the neck's length
NECK_SHARES = (0.3, 0.55) # the neck joints take these shares of the head's turn (the head all of it)
GRIP_DIST = 30.0          # cm (the walk's size): a pose's hands this near each other hold one thing together

# Foot placement: a planted foot never slides, one foot always on the ground
# (docs/superpowers/specs/2026-10-12-walk-foot-placement-design.md)
CONTACT_TOL = 1.5         # cm: the heel (ankle) or the ball this near its own lowest is planted
DOUBLE_SUPPORT = 0.08     # both feet down at least this share of the cycle at every step (a walk: ~8-10 %)
RUN_FLIGHT = 0.05         # both feet up longer than this share of a stride at a handoff: a run - its flight is kept
LOCK_STEPS = 16           # the contacts found and the lock integrated at 1/this of a frame
HELD_SHARE = 1.0         # a contact grows past its step only while its down point moves slower than the walk travels
HEEL_BACK = 0.25          # the heel's ground point: under the ankle, this share of the foot (to the ball) back
EXTEND_MAX = 0.5          # the contacts take at most this share of a foot's swing
GROUND_ROOM = 0.6         # Ground time: a longer stance takes at most this share of its swing's time
STRETCH_REACH = 0.96      # Ground time past 1: the legs straighten at most this far (of their length)...
GROUND_STRETCH = 0.15     # ...all of it at Ground time 1 + this
ROLL_RELEASE = 0.1        # the heel's roll eases down over this share of a stride after its peak
LEG_MARGIN = 0.008        # the legs held this share of their length short of their reach once they fall short...
MARGIN_FULL = 2.0         # ...all of it once they fall this many cm short (from nothing at 0)
ROLL_RATE = 100.0         # degrees a stride: a roll changes no faster (rate_limited) - the pelvis sinks the rest
ROLL_BALL = 30.0          # degrees: a foot on its ball alone may roll this much further (heel up) for its leg's reach
ROLL_HEEL = 15.0          # degrees: a foot on its heel alone may roll this much further (toes up)
ROLL_COST = 25.0          # cm^2: a radian of roll weighs as much as 5 cm of the leg falling short (_roll_cost)
ROLL_GRID = 32            # the roll's cost searched on this grid, then refined
ROLL_SOFT = 1.0           # cm: the shortfall's weight eases in over this much (_roll_cost)
ROLL_SENSE = 0.3          # the roll changes from the heel to the ball over this much of the foot's pivot weight
SOLE_HEEL_UP = 65.0       # degrees: no roll stands a sole steeper than this off the ground, heel up
SOLE_TOES_UP = 30.0       # degrees: nor toes up
SOLE_EASE = 15.0          # degrees: a roll eases into those limits over this much
AIR_HOLD = 2.0            # cm: a foot just off the ground may hold the pelvis down this much (_just_off)
GROWTH_SAMPLES = 12       # the lift-off and the swing's start tested at this many steps (_growth)

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
    """The defaults with `given` on top, each clamped to its range; an unknown name raises ValueError. A side's
    own value of a SIDED knob ("lift_l") is kept when given (clamped to the knob's range)."""
    unknown = sorted(set(given) - set(DEFAULTS) - set(SIDE_KNOBS))
    if unknown:
        raise ValueError("unknown knob(s): " + ", ".join(unknown))
    out = dict(DEFAULTS)
    for name, value in given.items():
        if value is None:
            continue
        low, high = RANGES[SIDE_KNOBS.get(name, name)]
        out[name] = min(max(float(value), low), high)
    return out


def sided(k):
    """{side: the knobs that side walks with}: each SIDED knob the side's own value where one is set, else
    the knob's."""
    return dict((side, dict((name, k.get("%s_%s" % (name, side), value) if name in SIDED else value)
                            for name, value in k.items() if name in DEFAULTS))
                for side in ("l", "r"))


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


def _exp3(w):
    """exp_rot for one rotation vector, in plain floats (the arms' integration takes thousands)."""
    x, y, z = float(w[0]), float(w[1]), float(w[2])
    th = math.sqrt(x * x + y * y + z * z)
    if th < 1e-12:
        return np.eye(3)
    x, y, z = x / th, y / th, z / th
    s, c = math.sin(th), math.cos(th)
    t = 1.0 - c
    return np.array([[c + x * x * t, z * s + x * y * t, -y * s + x * z * t],
                     [-z * s + x * y * t, c + y * y * t, x * s + y * z * t],
                     [y * s + x * z * t, -x * s + y * z * t, c + z * z * t]])


def _log3(r):
    """log_rot for one rotation, in plain floats."""
    tr = (float(r[0, 0]) + float(r[1, 1]) + float(r[2, 2]) - 1.0) / 2.0
    th = math.acos(min(max(tr, -1.0), 1.0))
    v = np.array([float(r[1, 2]) - float(r[2, 1]), float(r[2, 0]) - float(r[0, 2]), float(r[0, 1]) - float(r[1, 0])])
    s = math.sin(th)
    if s > 1e-7:
        return v * (th / (2.0 * s))
    if th < 1.0:
        return v * 0.5
    return log_rot(r)


def _cross3(a, b):
    return np.array([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]])


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


def _batch_rot(m):
    """The rotations nearest a stack of matrices' 3x3 parts (scale and shear stripped): (..., 3, 3)."""
    u, _, vt = np.linalg.svd(np.asarray(m, float)[..., :3, :3])
    flip = np.linalg.det(u @ vt) < 0.0
    if np.any(flip):
        u = u.copy()
        u[flip, :, -1] *= -1.0
    return u @ vt


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


def warp(phi, beta, phi0, strides=1):
    """The bob's clock: slowest (slope 1 - beta) a quarter and three quarters of a stride after phi0 (a cycle
    of `strides` strides)."""
    return phi + beta / (4.0 * math.pi * strides) * math.sin(4.0 * math.pi * strides * (phi - phi0))


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


def rate_limited(roll, step):
    """A periodic signed roll curve (one value a frame) changing no more than `step` a frame, by taking roll
    away only: heel up and toes up each the largest curve under it that moves `step` a frame at most (its lower
    envelope), so a flip from one to the other passes through zero (a step on each side of it)."""
    roll = np.asarray(roll, float)
    n = len(roll)
    if n == 0:
        return roll
    offsets = np.arange(n)
    distance = np.minimum(offsets, n - offsets) * step
    out = np.zeros(n)
    for part, sign in ((np.maximum(roll, 0.0), 1.0), (np.maximum(-roll, 0.0), -1.0)):
        if part.any():
            env = np.min([np.roll(part, s) + distance[s] for s in range(n)], axis=0)
            out += sign * np.minimum(env, part)
    return out


def released(roll, frames):
    """A periodic roll curve (one value a frame; + heel up) whose heel-up part lets go gradually: each frame
    the most of the heel-up rolls of the `frames` frames before it, each eased down by a smoothstep over that
    distance - never above zero earlier than the roll itself, the toes-up part (-) untouched."""
    roll = np.asarray(roll, float)
    up = np.maximum(roll, 0.0)
    if not up.any() or frames < 1.0:
        return roll
    out = up.copy()
    for k in range(1, int(math.ceil(frames)) + 1):
        u = min(k / float(frames), 1.0)
        out = np.maximum(out, np.roll(up, k) * (1.0 - u * u * (3.0 - 2.0 * u)))
    return np.where(roll < 0.0, roll, out)


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


def meet(knee, foot, lead):
    """A knee's and its foot's turns about up (radians) after they meet: the knee may stand TWIST_FREE_DEG
    against the foot (a shin twists that far); past it the excess is shared - `lead` 0 turns the knee to the
    foot, 1 the foot to the knee, 0.5 half way."""
    free = math.radians(TWIST_FREE_DEG)
    d = knee - foot
    excess = d - min(max(d, -free), free)
    if excess == 0.0:
        return knee, foot
    return knee - (1.0 - lead) * excess, foot + lead * excess


def _runs(mask):
    """Every stretch of True in a cyclic mask, (start index, length) sorted by start; [] when it holds no
    True, [(0, n)] when it holds nothing else."""
    n = len(mask)
    if not mask.any():
        return []
    if mask.all():
        return [(0, n)]
    start = int(np.nonzero(~mask)[0][0])
    out, run, on = [], 0, 0
    for step in range(1, n + 1):
        i = (start + step) % n
        if mask[i]:
            if run == 0:
                on = i
            run += 1
        elif run:
            out.append((on, run))
            run = 0
    if run:
        out.append((on, run))
    return sorted(out)


def _longest_run(mask):
    """The longest stretch of True in a cyclic mask: (start index, length); the mask holds both values."""
    n = len(mask)
    start = int(np.nonzero(~mask)[0][0])
    best, run = (0, 0), 0
    for step in range(1, n + 1):
        i = (start + step) % n
        if mask[i]:
            run += 1
            if run > best[1]:
                best = ((i - run + 1) % n, run)
        else:
            run = 0
    return best


def _hermite(x, length, rise, m0, m1):
    """The cubic on [0, length] from 0 to `rise` with slopes m0, m1 at its ends, at x."""
    t = x / length
    t2, t3 = t * t, t * t * t
    return (t3 - 2.0 * t2 + t) * length * m0 + (3.0 * t2 - 2.0 * t3) * rise + (t3 - t2) * length * m1


def swing_weight(s):
    """How far a swinging foot hangs off its shin at swing progress s (0 at the takeoff, 1 at the landing):
    0 on the ground, eased in over SWING_EASE of the swing and out over the last SWING_EASE."""
    ease = lambda x: (lambda c: c * c * (3.0 - 2.0 * c))(min(max(x, 0.0), 1.0))
    return ease(s / SWING_EASE) * ease((1.0 - s) / SWING_EASE)


def _frame(u, n):
    return np.stack([u, n, np.cross(u, n)])


def align(u_src, n_src, u_new, n_new):
    """The rotation taking the frame (u_src, n_src) onto (u_new, n_new): v . align = v'.
    Each n must be perpendicular to its u (a leg plane's normal against a bone in the plane)."""
    return _frame(u_src, n_src).T @ _frame(u_new, n_new)


SIDES = ("l", "r")
OTHER = {"l": "r", "r": "l"}
SIDE_WORD = {"l": "left", "r": "right"}
LEG = ("thigh", "calf", "foot")
HELPER_PREFIXES = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass")
ARM_STEMS = ("clavicle", "upperarm", "lowerarm", "hand")
#  Overlap's shares: the arms only since 2026-10-14 - the spine's and the head's overlap is Torso drag / Head drag (a
#  time shift of a world-held head read as a strange lag)
LAG = {"clavicle": 0.6, "upperarm": 0.8, "lowerarm": 1.0, "hand": 1.0}
CONTACT_SHARE = 0.2      # in stance the ankle or the ball moves less than this share of the travel a frame
MERGE_HIGH = 4.0         # cm: two stances of a foot are one while its heel or ball stays this near its lowest between
FOLLOW_TOL = 1e-3        # a helper follows a bone when helper . bone^-1 holds within this (matrix elements)
LOOP_TOL = (0.1, 0.002)  # cm and rotation elements: the last frame against the first moved by the travel
STRAIGHTEN_MAX = 15.0    # degrees: a cycle travelling this little off its root's facing is turned onto it
DUP_TOL = (1e-3, 1e-5)   # cm, rotation elements: two frames this alike are one frame written twice


def _stem(name):
    m = re.match(r"([a-z]+)(_twist_\d+)?_[lr]$", name)
    return m.group(1) if m else None


def _wrapped(angle):
    """An angle (radians) brought into [-pi, pi)."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


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
    """A foot's step: stance from frame `on` for `length` frames more, mid-stance at `mid`, the footprint's
    coordinates (along, aside, up) against the travel line there."""

    def __init__(self, side, on, length, mid, coords):
        self.side, self.on, self.length, self.mid, self.coords = side, on, length, mid, coords


def trimmed(clip):
    """(clip, how many frames dropped): a cycle whose last frame repeats the one before it - or whose first the
    one after it - is one frame written twice (an export's closing frame keyed again). With the copy in, every
    joint stood still a frame a cycle and every place carried a sawtooth of a frame's travel against the
    travel line, which the arms' springs and Balance took as a jolt: AGS_Sprint's forearms flipped 128 deg at
    the seam (2026-10-14). A walk's root travels, so two equal frames are never motion."""
    worlds = clip.worlds
    same = lambda a, b: (float(np.abs(worlds[:, a, 3, :3] - worlds[:, b, 3, :3]).max()) <= DUP_TOL[0] and
                         float(np.abs(worlds[:, a, :3, :3] - worlds[:, b, :3, :3]).max()) <= DUP_TOL[1])
    lo, hi = 0, worlds.shape[1] - 1
    while hi - lo > 9 and same(hi, hi - 1):
        hi -= 1
    while hi - lo > 9 and same(lo, lo + 1):
        lo += 1
    dropped = lo + (worlds.shape[1] - 1 - hi)
    if not dropped:
        return clip, 0
    return Clip(clip.names, clip.parents, worlds[:, lo:hi + 1], clip.fps, clip.up, clip.name), dropped


def straightened(clip):
    """(clip, degrees): a cycle whose travel runs a few degrees off its root's facing turned, about up through
    the root's first place, onto the root's horizontal axis nearest the travel - every joint's place and
    every joint's turn but the root's own, so the body faces and goes where the root faces (a walk saved a
    little askew drifts sideways on any skeleton it is put on: the target's root faces its own way and the
    travel is carried in the root's axes). Past STRAIGHTEN_MAX (a strafe, a turned clip) or with no root it
    is left as it is: (clip, 0.0)."""
    if "root" not in clip.names:
        return clip, 0.0
    r = clip.names.index("root")
    worlds, up = clip.worlds, clip.up
    travel = worlds[r, -1, 3, :3] - worlds[r, 0, 3, :3]
    flat = travel - np.dot(travel, up) * up
    if np.linalg.norm(flat) < 1.0:
        return clip, 0.0
    flat = _unit(flat)
    best = None
    for axis in orthonormal(worlds[r, 0, :3, :3]):
        for a in (axis, -axis):
            a = a - np.dot(a, up) * up
            if np.linalg.norm(a) < 0.5:
                continue
            a = _unit(a)
            angle = math.atan2(float(np.dot(np.cross(flat, a), up)), float(np.dot(flat, a)))
            if best is None or abs(angle) < abs(best):
                best = angle
    if best is None or abs(best) < 1e-9 or abs(best) > math.radians(STRAIGHTEN_MAX):
        return clip, 0.0
    turn = exp_rot(up * best)
    if np.dot(flat @ turn, np.cross(up, flat)) * best < 0.0:      # the turn goes the way the angle says
        turn = turn.T
    centre = worlds[r, 0, 3, :3]
    out = np.array(worlds, float)
    out[:, :, 3, :3] = (worlds[:, :, 3, :3] - centre) @ turn + centre
    keep = np.array(worlds[r, :, :3, :3])
    out[:, :, :3, :3] = worlds[:, :, :3, :3] @ turn
    out[r, :, :3, :3] = keep
    return Clip(clip.names, clip.parents, out, clip.fps, clip.up, clip.name), math.degrees(best)


def analyse(clip):
    """The clip read once (refusals by name); evaluate() rebuilds it from knobs."""
    return Walk(clip)


class Walk(object):

    def __init__(self, clip):
        clip, self.dropped = trimmed(clip)
        clip, self.turned = straightened(clip)
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
        # the body's own left and front: the walk's side and forward when it walks forward, both turned round
        # when it walks backward (its left hip on the travel's right) - a knee turned out, a hip dropped, a
        # trunk leant forward are the body's, whichever way it travels (2026-10-16: a backward walk under a
        # pose had both knees turned 40-50 deg in and its hip drop reversed)
        hips = (pos[self.index["thigh_l"], :P] - pos[self.index["thigh_r"], :P]).mean(axis=0)
        self.left = 1.0 if float(np.dot(hips, self.side)) >= 0.0 else -1.0
        self.lside, self.ahead = self.left * self.side, self.left * self.fwd
        # the body's own left-right, flat: its mean hip line - what Stance and a pose's width spread the feet along
        # (across the travel line a diagonal walk's feet stand 55 deg off it, and a side-on pose's width read +64 cm
        # on one of a mirror pair and -41 on the other, 2026-10-16)
        flat_hips = hips - float(np.dot(hips, self.up)) * self.up
        self.across = _unit(flat_hips) if np.linalg.norm(flat_hips) > 1e-9 else self.lside
        steps = np.arange(P) / float(P)
        self.origin = pos[root, 0] + (pos[root, :P] - pos[root, 0] - np.outer(steps, travel)).mean(axis=0)
        self.rot, self.pos = rot[:, :P], pos[:, :P]
        self.pdev = self.pos - (self.origin + np.outer(steps, travel))[None]
        self.wmean = np.stack([mean_rot(self.rot[j]) for j in range(count)])
        self.wlog = log_rot(self.rot @ np.swapaxes(self.wmean, -1, -2)[:, None])
        self._locals()
        self._kinds()
        # a cycle may hold several steps of each foot: every per-foot quantity is a list, one entry a step
        self.steps = dict((s, self._steps(s)) for s in SIDES)
        if len(self.steps["l"]) != len(self.steps["r"]):
            raise Refusal("the left foot steps %d times a cycle and the right %d: a walk alternates its feet"
                          % (len(self.steps["l"]), len(self.steps["r"])))
        self.strides = len(self.steps["l"])
        self.feet = dict((s, max(self.steps[s], key=lambda foot: foot.length)) for s in SIDES)   # the longest
        self.reach = dict((s, self._reach(s)) for s in SIDES)
        self.follows = self._helpers()
        self.world_arms = set(self.index[n] for n in ("upperarm_l", "upperarm_r") if n in self.index)
        self.root_mean = (self.pdev[root] @ self.basis.T).mean(axis=0)
        self.pelvis_mean = (self.pdev[self.index["pelvis"]] @ self.basis.T).mean(axis=0)
        bob = self.pdev[self.index["pelvis"]] @ self.up - self.pelvis_mean[2]
        self.low_phase = float(np.argmin(bob)) / P
        self.balance_note = ""
        # the legs' share of the animator's correction of the walk's mean pose (maya_walk.meanpose: the upper
        # body's is in the clip's frames already): the pelvis raised, the feet's spread, each knee's and foot's
        # turn about up - added where a pose's are, giving way to a pose's own at the Pose share
        self.fix = {"height": 0.0, "width": 0.0, "knee": {"l": 0.0, "r": 0.0}, "toe": {"l": 0.0, "r": 0.0}}
        self._masses()
        self._grounds()
        self._legs_and_pelvis()
        self._chest()
        self._placement()
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
        stance = " ".join("%s %d %%" % (s.upper(), round(100.0 * sum(f.length + 1 for f in self.steps[s]) / self.P))
                          for s in SIDES)
        text = "%s: cycle %d frames (%.2f s), stride %.1f cm, %.2f m/s, stance %s" % (
            self.clip.name, self.P, self.P / self.fps, np.linalg.norm(flat) / (2.0 * self.strides),
            np.linalg.norm(flat) / (self.P / self.fps) / 100.0, stance)
        if self.strides > 1:
            text += " | %d steps of each foot a cycle" % self.strides
        if abs(self.turned) >= 0.05:
            text += " | turned %.1f deg onto its root's facing" % self.turned
        if self.dropped:
            text += " | %d repeated frame%s dropped" % (self.dropped, "" if self.dropped == 1 else "s")
        return text

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
        self.forearms = set(j for j, n in enumerate(self.names) if _stem(n) == "lowerarm")

    def _steps(self, side):
        """Every stance of the foot in the cycle, sorted by its start (a cycle may hold several steps of each
        foot): the runs where the slower of its ankle and ball moves less than CONTACT_SHARE of the travel a
        frame; two runs merged when the foot's heel or ball stays within MERGE_HIGH of its lowest across the
        frames between them (a stance sliding a little faster for a while); a run whose middle stands higher
        than that is no stance. Each a Foot."""
        P = self.P
        speeds, low = [], np.zeros(P, bool)
        for name in ("foot_" + side, "ball_" + side):
            p = self.pos[self.index[name]]
            ahead = np.vstack([p[1:], p[:1] + self.travel])
            behind = np.vstack([p[-1:] - self.travel, p[:-1]])
            speeds.append(np.linalg.norm(ahead - behind, axis=1) / 2.0)
            h = p @ self.up
            low |= h <= h.min() + MERGE_HIGH
        slow = np.minimum(speeds[0], speeds[1]) < np.linalg.norm(self.travel) / P * CONTACT_SHARE
        if slow.all():
            raise Refusal("the %s foot never leaves the ground" % SIDE_WORD[side])
        if not slow.any():
            raise Refusal("the %s foot never stops: no contact to plant it on" % SIDE_WORD[side])
        runs = _runs(slow)
        merged = True
        while merged and len(runs) > 1:
            merged = False
            for i, (a, la) in enumerate(runs):
                b, lb = runs[(i + 1) % len(runs)]
                gap = (b - a - la) % P
                if all(low[(a + la + g) % P] for g in range(gap)):
                    runs = [r for m, r in enumerate(runs) if m not in (i, (i + 1) % len(runs))]
                    runs = sorted(runs + [(a, la + gap + lb)])
                    merged = True
                    break
        runs = [(on, n) for on, n in runs if low[(on + n // 2) % P]]
        if not runs:
            raise Refusal("the %s foot never stops near the ground: no contact to plant it on" % SIDE_WORD[side])
        out = []
        for on, n in runs:
            length = n - 1
            mid = on + length / 2.0
            coords = periodic_cr(self.pdev[self.index["foot_" + side]], mid) @ self.basis.T
            out.append(Foot(side, on, length, mid, coords))
        return out

    def _step_at(self, side, tau):
        """The step whose stance or the swing after it source time tau is in: (its index, the cycle k, how far
        past its start)."""
        best = None
        for i, foot in enumerate(self.steps[side]):
            k = math.floor((tau - foot.on) / self.P)
            r = tau - foot.on - k * self.P
            if best is None or r < best[2]:
                best = (i, k, r)
        return best

    def side_print(self, side):
        """The foot's footprints' mean place across the travel line (cm, + to the walk's left)."""
        return float(np.mean([foot.coords[1] for foot in self.steps[side]]))

    def print_across(self, step):
        """A footprint's place across the BODY (cm along `across`, + to the body's left)."""
        return float(step.coords[0] * np.dot(self.fwd, self.across) + step.coords[1] * np.dot(self.side, self.across))

    def body_print(self, side):
        """The foot's footprints' mean place across the body (cm along `across`)."""
        return float(np.mean([self.print_across(foot) for foot in self.steps[side]]))

    def stride_phase(self, tau):
        """The stride's phase at source time tau, radians: 2 pi a stride, running linearly between the left
        foot's strikes (its steps' starts) - for one stride a cycle 2 pi (tau - the left strike) / P."""
        ons = [foot.on for foot in self.steps["l"]]
        n, P = len(ons), float(self.P)
        k = math.floor((tau - ons[0]) / P)
        x = tau - k * P
        knots = ons + [ons[0] + P]
        m = max(i for i in range(n) if knots[i] <= x + 1e-12)
        u = (x - knots[m]) / (knots[m + 1] - knots[m])
        return 2.0 * math.pi * (k * n + m + u)

    def _legs_and_pelvis(self):
        """What the legs' and the pelvis's knobs read: each foot's turn in its calf (a mean and logs), the balls,
        the twist's shape (the feet's fore-aft split, demeaned, peak 1) and the hip drop's (a cosine peaking
        LIST_PEAK after the left heel strike), the twist's growth with the step, this walk's own twist and drop
        on those shapes (own_knobs) and the lumbar joints that take the pelvis's added turn back."""
        P, idx = self.P, self.index
        self.foot_rel = {}
        for side in SIDES:
            rel = self.rot[idx["foot_" + side]] @ np.swapaxes(self.rot[idx["calf_" + side]], -1, -2)
            mean = mean_rot(rel)
            self.foot_rel[side] = (mean, log_rot(rel @ mean.T))
        self.balls = dict((idx["ball_" + side], side) for side in SIDES)
        self.air = dict((side, self._air(side)) for side in SIDES)
        sep = (self.pos[idx["foot_l"]] - self.pos[idx["foot_r"]]) @ self.fwd
        sep = sep - sep.mean()
        self.split_shape = sep / max(float(np.abs(sep).max()), 1e-9)
        self.list_shape = np.array([self.list_at(float(f)) for f in range(P)])
        flat = self.travel - np.dot(self.travel, self.up) * self.up
        leg = np.mean([np.linalg.norm(self.lt[idx["calf_" + s]], axis=1).mean() +
                       np.linalg.norm(self.lt[idx["foot_" + s]], axis=1).mean() for s in SIDES])
        self.leg_length = float(leg)          # thigh + calf, both sides' mean (Leg match's Froude number)
        self.twist_gain = float(np.linalg.norm(flat)) / (2.0 * self.strides) / float(leg) / STEP_REF
        self.own_twist = self.own_list = 0.0
        twist, drop = self.pelvis_fit(self.clip.worlds)
        self.own_twist, self.own_list = twist / self.twist_gain, drop
        spine = sorted((int(m.group(1)), j) for j, n in enumerate(self.names)
                       for m in [re.match(r"spine_(\d+)$", n)] if m and idx["pelvis"] in self._ancestors(j))
        lumbar = [j for _, j in spine[:len(COUNTER_SHARES)]]
        total = sum(COUNTER_SHARES[:len(lumbar)])
        self.counter = dict((j, share / total) for j, share in zip(lumbar, COUNTER_SHARES))

    def _air(self, side):
        """The foot's flights: [(where it leaves the ground, how long it is off it)], source time to
        1/AIR_STEPS of a frame - every stretch of at least a frame with neither its heel nor its toe near the
        ground (not down); a cycle of several steps flies once a step."""
        count = self.P * AIR_STEPS
        down = np.array([self.down(side, i / float(AIR_STEPS)) for i in range(count)])
        out = []
        for on, run in _runs(~down):
            if run + 1 < AIR_STEPS:
                continue
            out.append((((on - 1) % count) / float(AIR_STEPS), (run + 1) / float(AIR_STEPS)))
        return out

    def air_progress(self, side, tau):
        """How far through its flight the foot is at source time tau (0 where it leaves the ground, 1 where it
        lands); None while it is down."""
        if self.down(side, tau):
            return None
        for start, length in self.air[side]:
            r = (tau - start) % self.P
            if r < length:
                return r / length
        return None

    def list_at(self, tau):
        """The hip drop's shape at source time tau: 1 with the left hip highest, -1 the right - LIST_PEAK of a
        stride after the left heel strike, once a stride."""
        return math.cos(self.stride_phase(tau) - 2.0 * math.pi * LIST_PEAK)

    def own_knobs(self):
        """The knobs that give this walk back (the defaults are physiological): its own Twist and Hip drop, no
        Foot placement (its own feet, slides and all), its root weaving as it does, its own Chest twist and
        sway, and no Arm, Torso or Head drag (its body as it moves, without the inertia on top)."""
        return {"pelvis_twist": self.own_twist, "pelvis_list": self.own_list, "foot_placement": 0.0,
                "root_sway": 1.0, "chest_twist": self.own_chest_twist, "chest_sway": self.own_chest_sway,
                "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0}

    def pelvis_fit(self, worlds):
        """The hip line's twist and drop amplitudes (degrees) in a cycle of world matrices (J, n+1, 4, 4): each
        fitted on its shape (least squares, demeaned). The twist turns the forward leg's hip forward, the drop
        lifts the standing hip."""
        n = worlds.shape[1] - 1
        taus = [f * self.P / float(n) for f in range(n)]
        d = worlds[self.index["thigh_l"], :n, 3, :3] - worlds[self.index["thigh_r"], :n, 3, :3]
        across = np.linalg.norm(d - np.outer(d @ self.up, self.up), axis=1)
        twist = np.degrees(np.arctan2(d @ self.fwd, d @ self.lside))
        drop = np.degrees(np.arctan2(d @ self.up, across))
        split = np.array([float(periodic_cr(self.split_shape, t)) for t in taus])
        lists = np.array([self.list_at(t) for t in taus])

        def fit(y, x):
            y, x = y - y.mean(), x - x.mean()
            return float(np.dot(y, x) / np.dot(x, x)) if float(np.dot(x, x)) > 1e-12 else 0.0
        return fit(twist, split), fit(drop, lists)

    def _chest(self):
        """What the chest's knobs read: the shoulder line's turn about up (twist) and its tilt (sway) in the walk,
        each's first harmonic - its amplitude (degrees; the twist per step gain, as Twist's) and its shape (a
        cosine at the walk's own phase; a walk whose chest hardly turns takes the pelvis's shapes, opposite) -
        and the top spine joints that take the chest's added turn (CHEST_SHARES)."""
        idx, P = self.index, self.P
        self.chest_shape, self.own_chest_twist, self.own_chest_sway, self.chest_share = None, 0.0, 0.0, {}
        if "upperarm_l" not in idx or "upperarm_r" not in idx:
            return
        d = self.pos[idx["upperarm_l"]] - self.pos[idx["upperarm_r"]]
        across = np.linalg.norm(d - np.outer(d @ self.up, self.up), axis=1)
        yaw = np.degrees(np.arctan2(d @ self.fwd, d @ self.lside))
        tilt = np.degrees(np.arctan2(d @ self.up, across))
        phase = np.array([self.stride_phase(float(f)) for f in range(P)])     # once a stride

        def harmonic(x):
            x = x - x.mean()
            c = 2.0 / P * float(np.dot(x, np.cos(phase)))
            s = 2.0 / P * float(np.dot(x, np.sin(phase)))
            return math.hypot(c, s), math.atan2(s, c)
        twist, sway = harmonic(yaw), harmonic(tilt)
        if twist[0] < CHEST_STILL:          # no turn of its own: against the pelvis's twist (the feet's split)
            twist = (twist[0], harmonic(-np.array([float(periodic_cr(self.split_shape, f)) for f in range(P)]))[1])
        if sway[0] < CHEST_STILL:
            sway = (sway[0], harmonic(-self.list_shape)[1])
        self.chest_shape = (twist[1], sway[1])
        # the walk's own amplitudes as chest_fit reads a cycle (least squares on the shapes): with strides of
        # uneven length the projection above is not that fit, and own_knobs() must give the walk back exactly
        fitted = self.chest_fit(self.clip.worlds)
        self.own_chest_twist, self.own_chest_sway = fitted[0] / self.twist_gain, fitted[1]
        spine = sorted((int(m.group(1)), j) for j, n in enumerate(self.names)
                       for m in [re.match(r"spine_(\d+)$", n)] if m and idx["pelvis"] in self._ancestors(j))
        top = [j for _, j in spine[-len(CHEST_SHARES):]]
        shares = CHEST_SHARES[-len(top):] if top else ()
        total = sum(shares)
        self.chest_share = dict((j, share / total) for j, share in zip(top, shares))

    def chest_shapes(self, tau):
        """(twist, sway) shapes at source time tau: 1 at the walk's own peak, -1 half a stride on."""
        a = self.stride_phase(tau)
        return math.cos(a - self.chest_shape[0]), math.cos(a - self.chest_shape[1])

    def chest_targets(self, k, ex):
        """(twist, sway) the shoulders turn each way at these knobs, degrees: Chest twist at a normal step x
        the step's gain (as Twist's), Chest sway - both x Spine x Exaggeration."""
        gain = k["spine"] * ex
        return gain * self.twist_gain * k["chest_twist"] * k["stride"], gain * k["chest_sway"]

    def chest_extra(self, tau, k, ex, own=None):
        """The chest's added turn at source time tau (a world rotation vector, None when nothing is added): the
        shoulders brought from their own turn (`own`: (twist, sway) degrees as they stand under these knobs and
        pose - _chest_own; else the walk's own x Spine) to Chest twist and sway, on their shapes."""
        if self.chest_shape is None or own == "off":
            return None
        target = self.chest_targets(k, ex)
        if own is None:
            gain = k["spine"] * ex
            own = (gain * self.twist_gain * self.own_chest_twist, gain * self.own_chest_sway)
        twist, sway = target[0] - own[0], target[1] - own[1]
        if abs(twist) < 1e-9 and abs(sway) < 1e-9:
            return None
        a, b = self.chest_shapes(tau)
        return self.left * (math.radians(twist) * a * -self.up + math.radians(sway) * b * self.fwd)

    def _chest_own(self, times, ctx):
        """(twist, sway): how far the shoulders turn each way under these knobs and pose with nothing added
        (a pose's bent spine turns them otherwise than the walk does), the spine and shoulders alone built
        over the cycle; None without a chest."""
        if self.chest_shape is None:
            return None
        only = set()
        for name in ("upperarm_l", "upperarm_r"):
            j = self.index[name]
            only.update([j] + self._ancestors(j))
        n = len(times) - 1
        worlds = np.tile(np.eye(4), (len(self.names), n + 1, 1, 1))
        ctx["chest_own"] = "off"
        for f, (phi, tau) in enumerate(times):
            worlds[:, f] = self._frame(phi, tau, ctx, 0.0, None, only)[0]
        own = self.chest_fit(worlds)
        # once more with the turn added: a bent spine does not take a world turn one for one - what it misses
        # of the target is asked for again
        ctx["chest_own"] = own
        for f, (phi, tau) in enumerate(times):
            worlds[:, f] = self._frame(phi, tau, ctx, 0.0, None, only)[0]
        got, target = self.chest_fit(worlds), self.chest_targets(ctx["k"], ctx["ex"])
        ctx["chest_own"] = None
        return own[0] + got[0] - target[0], own[1] + got[1] - target[1]

    def chest_fit(self, worlds):
        """The shoulder line's twist and sway amplitudes (degrees) in a cycle of world matrices (J, n+1, 4, 4),
        each fitted on its shape (least squares, demeaned)."""
        n = worlds.shape[1] - 1
        d = worlds[self.index["upperarm_l"], :n, 3, :3] - worlds[self.index["upperarm_r"], :n, 3, :3]
        across = np.linalg.norm(d - np.outer(d @ self.up, self.up), axis=1)
        yaw = np.degrees(np.arctan2(d @ self.fwd, d @ self.lside))
        tilt = np.degrees(np.arctan2(d @ self.up, across))
        shapes = np.array([self.chest_shapes(f * self.P / float(n)) for f in range(n)])

        def fit(y, x):
            y, x = y - y.mean(), x - x.mean()
            return float(np.dot(y, x) / np.dot(x, x)) if float(np.dot(x, x)) > 1e-12 else 0.0
        return fit(yaw, shapes[:, 0]), fit(tilt, shapes[:, 1])

    def pelvis_extra(self, tau, k, ex):
        """The pelvis's added turn at source time tau (a world rotation vector, None when nothing is added):
        Twist and Hip drop against this walk's own, on their shapes, x Pelvis motion x Exaggeration."""
        gain = k["pelvis_rot"] * ex
        twist = self.twist_gain * (k["pelvis_twist"] * k["stride"] - self.own_twist)
        drop = k["pelvis_list"] - self.own_list
        if gain == 0.0 or (twist == 0.0 and drop == 0.0):
            return None
        return gain * self.left * (math.radians(twist) * float(periodic_cr(self.split_shape, tau)) * -self.up
                                   + math.radians(drop) * self.list_at(tau) * self.fwd)

    def _spine_map(self, pose, alpha):
        """Under a pose that bends the spine: per spine joint the matrix taking its turn's axis (in its own
        frame) to the axis that turns about the same WORLD axis as in the walk - a hunched spine still twists
        and sways about the walk's vertical, so the chest keeps counter-turning against the pelvis. The walk's
        and the pose's mean frames: chains of mean locals from the mean pelvis. {} without a bent spine."""
        if pose is None or not pose.get("spine"):
            return {}
        pelvis = self.index["pelvis"]
        src = {pelvis: self.wmean[pelvis]}
        new = {pelvis: self.wmean[pelvis] if "pelvis" not in pose else toward(self.wmean[pelvis], pose["pelvis"], alpha)}
        out = {}
        for j in self.order:
            p = self.parents[j]
            if self.kind[j] != "spine" or p not in src:
                continue
            centre = self.lmean[j] if j not in pose["spine"] else toward(self.lmean[j], pose["spine"][j], alpha)
            src[j], new[j] = self.lmean[j] @ src[p], centre @ new[p]
            out[j] = src[j] @ new[j].T
        return out

    # -- Leg match: a pose's stance against the gait --

    def _heading(self, v):
        """A direction's heading about up (radians): from the walk's forward toward its side axis (its left)."""
        return math.atan2(float(np.dot(v, self.side)), float(np.dot(v, self.fwd)))

    def knee_headings(self):
        """{side: the walk's mean knee heading (radians)} - each frame's knee bend off the hip-ankle line,
        averaged over the cycle."""
        out = {}
        for side in SIDES:
            bends = []
            for f in range(self.P):
                hip, knee, ankle = (self.pos[self.index["%s_%s" % (b, side)]][f] for b in LEG)
                e = _unit(ankle - hip)
                bend = (knee - hip) - np.dot(knee - hip, e) * e
                if np.linalg.norm(bend) > 1e-9:
                    bends.append(_unit(bend))
            out[side] = self._heading(np.mean(bends, axis=0)) if bends else 0.0
        return out

    def toe_headings(self):
        """{side: the walk's toe heading (radians)} - ankle to ball at the foot's longest stance's middle."""
        out = {}
        for side in SIDES:
            mid = self.feet[side].mid
            out[side] = self._heading(self.wpos(self.index["ball_" + side], mid) -
                                      self.wpos(self.index["foot_" + side], mid))
        return out

    def gait_keep(self, k, n):
        """(keep, Fr): how much of a pose's stance a gait at these knobs keeps, 1 / (1 + Fr / GAIT_FROUDE) -
        Fr = v^2 / (g L), the Froude number of the new cycle (its speed after Stride and Tempo, `n` frames; L
        the legs' thigh + calf)."""
        flat = self.travel * k["stride"]
        flat = flat - np.dot(flat, self.up) * self.up
        speed = float(np.linalg.norm(flat)) / (n / self.fps)
        froude = speed * speed / (GRAVITY * self.leg_length)
        return 1.0 / (1.0 + froude / GAIT_FROUDE), froude

    def matched_pose(self, pose, m, keep):
        """The pose (as prepare hands it) with its legs matched to the gait at Leg match `m` (0: as it is, 1:
        matched) - the spec's section 2. A pose standing side-on gives its turn about up (`hips_yaw`) back from
        the pelvis and the lumbar spine takes it (the chest keeps the pose's facing); the knees' and the toes'
        turns are re-read against the pose's own hips, outward, and only their symmetric part (a front and a
        back foot are a stance) is kept, over the walk's own, x `keep`; the width x `keep`."""
        if pose is None or m <= 0.0:
            return pose
        out = dict(pose)
        yaw = float(pose.get("hips_yaw", 0.0))
        if yaw and "pelvis" in pose:
            out["pelvis"] = pose["pelvis"] @ exp_rot(self.up * (-m * yaw))
            if pose.get("spine"):
                out["spine"] = self._spine_takes(pose, m * yaw)
        sign = {"l": 1.0, "r": -1.0}
        # the headings read from the body's own front (a backward walk's knees point near 180 deg off its travel,
        # where the angle wraps: a knee turned out read as turned in, 2026-10-16) - the same turn of the frame
        # about up, so the pose's turns (differences) and the yaw stand as they are
        front = 0.0 if self.left > 0.0 else math.pi
        for key, own in (("knee_turn", self.knee_headings()), ("toe", self.toe_headings())):
            turns = pose.get(key)
            if not turns or any(s not in turns for s in SIDES):
                continue
            own = dict((s, _wrapped(own[s] - front)) for s in SIDES)
            outward = sum(sign[s] * _wrapped(turns[s] + own[s] - yaw) for s in SIDES) / 2.0
            splay = outward - sum(sign[s] * own[s] for s in SIDES) / 2.0
            out[key] = dict((s, (1.0 - m) * turns[s] + m * sign[s] * keep * splay) for s in SIDES)
        if "width" in pose:
            out["width"] = pose["width"] * ((1.0 - m) + m * keep)
        return out

    def _spine_takes(self, pose, yaw):
        """The pose's spine locals once its pelvis has given `yaw` (radians, about up) back: the
        lumbar joints (Twist's counter joints) turn it back in their shares, so every joint above them keeps the
        pose's world turn."""
        cum, done = {}, 0.0
        for j in sorted(self.counter, key=lambda j: len(self._ancestors(j))):
            done += self.counter[j]
            cum[j] = done
        pel = self.index["pelvis"]
        turn = lambda j: exp_rot(self.up * (-yaw * (1.0 - min(cum.get(j, 0.0 if j == pel else 1.0), 1.0))))
        return self._torso_turned(pose, turn)[1]

    def _torso_turned(self, pose, turn):
        """(pelvis, spine locals) of the pose with each of its torso bones' WORLD rotation turned by `turn(j)` (a
        world rotation post-multiplied) - the pelvis (the walk's mean when the pose has none) and every spine
        joint; a joint the pose gives no local for stands on the walk's mean local."""
        pel = self.index["pelvis"]
        given = pose.get("spine") or {}
        base = pose["pelvis"] if "pelvis" in pose else self.wmean[pel]
        old, new, spine = {pel: base}, {pel: base @ turn(pel)}, dict(given)
        for j in self.order:
            p = self.parents[j]
            if self.kind[j] != "spine" or p not in old:
                continue
            old[j] = given.get(j, self.lmean[j]) @ old[p]
            new[j] = old[j] @ turn(j)
            local = new[j] @ new[p].T
            if j in given or float(np.abs(local - old[j] @ old[p].T).max()) > 1e-12:
                spine[j] = local
        return new[pel], spine

    def leaned_pose(self, pose, gain):
        """The pose with the walk's own forward lean put back on its torso (Gait lean `gain`): each torso bone the
        pose replaces turned forward about the walk's side axis by the walk's mean pitch over its rest
        (`gait_lean`, from prepare) - a forward one x `lean_room` (the room the pose leaves to LEAN_LIMIT), a
        backward one as it is. A pose without its pelvis stands on the walk's, which leans already: its spine
        takes only its own lean over the pelvis's."""
        if pose is None or gain <= 0.0 or not pose.get("gait_lean"):
            return pose
        thetas, room = pose["gait_lean"], float(pose.get("lean_room", 1.0))
        lean = lambda j: gain * (thetas.get(j, 0.0) * (room if thetas.get(j, 0.0) > 0.0 else 1.0))
        pel, head = self.index["pelvis"], self.index.get("head")
        out = dict(pose)
        if "pelvis" in pose or pose.get("spine"):
            own = "pelvis" in pose
            under = 0.0 if own else lean(pel)
            turn = lambda j: exp_rot(self.lside * ((lean(pel) if own else 0.0) if j == pel else lean(j) - under))
            pelvis, spine = self._torso_turned(pose, turn)
            if own:
                out["pelvis"] = pelvis
            if pose.get("spine"):
                out["spine"] = spine
        if "head" in pose and head is not None:
            out["head"] = pose["head"] @ exp_rot(self.lside * lean(head))
        return out

    def _placement(self):
        """What Foot placement reads, per foot a list - one contact a step (in source time, hs in [0, P), to = hs
        + its length): the stretch around the step with its heel (the ankle) or its ball within CONTACT_TOL of
        that step's own low, at least the step itself; the pivot's weight there (0 the heel, 1 the ball:
        whichever is down alone, a smoothstep where both are); the other foot's strike it hands over to (the
        nearest to its lift-off) and the double support there; how much longer the foot stays down at its
        lift-off (rolling over its ball) for both feet to be down DOUBLE_SUPPORT of a stride at every step, at
        most EXTEND_MAX of the swing after it. Per foot, from its longest contact: the heel's ground point in
        the foot's frame (under the ankle at the ball's height, HEEL_BACK of the foot behind), the foot's side
        and its sole's up. And the joints below each thigh, which ride their foot's clock."""
        P, G, idx = self.P, LOCK_STEPS, self.index
        cells = P * G
        grid = np.arange(cells) / float(G)
        self.contact, self.pivot, self.heel_loc, self.placement_note = {}, {}, {}, ""
        self.foot_side, self.sole_up, self.swing_len, self.handoff = {}, {}, {}, {}
        self.extend = dict((side, [{"hs": 0.0, "to": 0.0} for _ in self.steps[side]]) for side in SIDES)
        self.double_src = {}
        self.leg_side = {}
        for j, kind in enumerate(self.kind):
            for side in SIDES:
                if kind not in ("leg", "helper") and idx["thigh_" + side] in self._ancestors(j):
                    self.leg_side[j] = side
        for side in SIDES:
            heights = [np.array([float(periodic_cr(self.pos[idx[name]] @ self.up, t)) for t in grid])
                       for name in ("foot_" + side, "ball_" + side)]
            # how fast the heel (the ankle) and the ball move along the ground there, cm a frame: a point near
            # the floor that travels is skimming, not planted
            speeds = []
            for name in ("foot_" + side, "ball_" + side):
                flat_dev = self.pdev[idx[name]] - np.outer(self.pdev[idx[name]] @ self.up, self.up)
                ground = self.travel - np.dot(self.travel, self.up) * self.up
                moved = np.array([periodic_cr(flat_dev, t + 0.5 / G) - periodic_cr(flat_dev, t - 0.5 / G)
                                  for t in grid]) * G + ground / P
                speeds.append(np.linalg.norm(moved, axis=1))
            held_speed = HELD_SHARE * float(np.linalg.norm(self.travel - np.dot(self.travel, self.up) * self.up)) / P
            steps = self.steps[side]
            contacts, pivots, anywhere = [], [], np.zeros(cells, bool)
            for foot in steps:
                window = [int(round(foot.on * G)) + c for c in range(int(round(foot.length * G)) + 1)]
                downs = []
                for h in heights:
                    low = min(float(h[c % cells]) for c in window)
                    downs.append(h <= low + CONTACT_TOL)
                either = downs[0] | downs[1]
                anywhere |= either
                # the contact grows out of its step only while the point that is down is held there
                held = ((downs[0] & (speeds[0] <= held_speed)) | (downs[1] & (speeds[1] <= held_speed)))
                c0 = int(round(foot.mid * G))
                left, right = c0 - window[0], window[-1] - c0
                if either[c0 % cells]:            # out along the stretch down, never into another step
                    i = steps.index(foot)
                    before, after = steps[i - 1], steps[(i + 1) % len(steps)]
                    lo = int(round((before.on + before.length) * G))
                    while lo > window[0]:
                        lo -= cells
                    hi = int(round(after.on * G))
                    while hi <= window[-1]:
                        hi += cells
                    a = 0
                    while c0 - a - 1 > lo and held[(c0 - a - 1) % cells] and a < cells:
                        a += 1
                    b = 0
                    while c0 + b + 1 < hi and held[(c0 + b + 1) % cells] and b < cells:
                        b += 1
                    left, right = max(left, a), max(right, b)
                start, length = c0 - left, left + right + 1
                hs = (start % cells) / float(G)
                contacts.append((hs, hs + (length - 1) / float(G)))
                spans = []
                for down in downs:
                    on = [i for i in range(length) if down[(start + i) % cells]]
                    spans.append((on[0] / float(G), on[-1] / float(G)) if on else None)
                heel, ball = spans
                lam_in = 0.0 if ball is None or (heel is not None and heel[0] <= ball[0]) else 1.0
                lam_out = 1.0 if heel is None or (ball is not None and ball[1] >= heel[1]) else 0.0
                both = (max(heel[0], ball[0]), min(heel[1], ball[1])) if heel and ball else (0.0, 0.0)
                pivots.append((lam_in, lam_out, both[0], max(both[1], both[0])))
            if anywhere.all():
                self.placement_note = "the %s foot never lifts" % SIDE_WORD[side]
                return
            self.contact[side], self.pivot[side] = contacts, pivots
            self.swing_len[side] = [(contacts[(i + 1) % len(contacts)][0] - to) % P or float(P)
                                    for i, (hs, to) in enumerate(contacts)]
            hs, to = max(contacts, key=lambda c: c[1] - c[0])
            mid = 0.5 * (hs + to)
            rot = self.wrot(idx["foot_" + side], mid)
            reach = self.wpos(idx["ball_" + side], mid) - self.wpos(idx["foot_" + side], mid)
            rise = float(np.dot(reach, self.up))
            self.heel_loc[side] = (rise * self.up - HEEL_BACK * (reach - rise * self.up)) @ rot.T
            # the flat foot's side and its sole's up, in the foot's own frame: the roll turns about the foot's
            # own side (a near-vertical foot's flat direction is no axis: it flips as the foot passes upright)
            self.foot_side[side] = _unit(np.cross(self.up, reach - rise * self.up)) @ rot.T
            self.sole_up[side] = self.up @ rot.T
        wrap = lambda d: (d + 0.5 * P) % P - 0.5 * P
        stride = P / float(self.strides)
        for s, o in (("l", "r"), ("r", "l")):     # the trailing foot stays longer: it can roll over its ball
            self.handoff[s], self.double_src[s] = [], []
            for i, (hs, to) in enumerate(self.contact[s]):
                j = min(range(len(self.contact[o])), key=lambda m: abs(wrap(to - self.contact[o][m][0])))
                ds = wrap(to - self.contact[o][j][0])
                self.handoff[s].append(j)
                self.double_src[s].append(ds)
                # a run's flight (both feet up) is its gait, not a gap to close: its contacts are not grown
                # (grown to a walk's double support, HavyRun's 6-frame stances took 8 frames more - its swings
                # crushed into the rest, a swinging foot grazed the floor and the pelvis sank 64 cm, 2026-10-13)
                self.extend[s][i]["to"] = 0.0 if self.is_flight(ds) else max(0.0, DOUBLE_SUPPORT * stride - ds)
        for side in SIDES:
            for i, ext in enumerate(self.extend[side]):
                grow, room = ext["hs"] + ext["to"], EXTEND_MAX * self.swing_len[side][i]
                if grow > room:
                    self.extend[side][i] = dict((end, v * room / grow) for end, v in ext.items())

    def is_flight(self, ds):
        """Whether a handoff's double support `ds` (source frames; negative: both feet up) is a run's flight."""
        return ds < -RUN_FLIGHT * self.P / float(self.strides)

    def _contact_at(self, side, t):
        """The contact foot time t is in, or the swing after it: (its index, how far past its strike)."""
        best = None
        for i, (hs, to) in enumerate(self.contact[side]):
            r = (t - hs) % self.P
            if best is None or r < best[1]:
                best = (i, r)
        return best

    def placed_contact(self, side, placement, grown=None):
        """The foot's contacts [(strike, lift-off)] in the new cycle's own time (source frames) at Foot
        placement `placement`: grown at their ends - by `grown` ({side: [{"hs", "to"} a contact]}, source
        frames: an evaluate's), else by the walk's own targets x `placement`."""
        out = []
        for i, (hs, to) in enumerate(self.contact[side]):
            if grown is not None:
                g = grown[side][i]
                out.append((hs - g["hs"], to + g["to"]))
            else:
                ext = self.extend[side][i]
                out.append((hs - placement * ext["hs"], to + placement * ext["to"]))
        return out

    def double_support(self, placement, grown=None):
        """Both feet down at each step, frames of the source's length: {"l": from the left's lift-off back to
        the right's strike it hands over to, "r": the other} - the least of a foot's steps (negative: a
        flight)."""
        P, out = float(self.P), {}
        for s, o in (("l", "r"), ("r", "l")):
            mine, theirs = self.placed_contact(s, placement, grown), self.placed_contact(o, placement, grown)
            out[s] = min((to - theirs[j][0] + 0.5 * P) % P - 0.5 * P
                         for (hs, to), j in zip(mine, self.handoff[s]))
        return out

    def foot_time(self, side, tau, placement, grown=None):
        """The foot's own source time at body time tau. Without Foot placement the walk's own; with it each
        contact plays over its placed_contact (slower) and the swings quicken: a periodic monotone C1 cubic
        through every (strike', strike) and (lift-off', lift-off), each knot's slope the harmonic mean of its
        two stretches'."""
        if self.placement_note or (placement <= 0.0 and grown is None):
            return tau
        contacts, placed = self.contact[side], self.placed_contact(side, placement, grown)
        if all(a == b for a, b in zip(contacts, placed)):
            return tau
        P = float(self.P)
        xs = [x for c in placed for x in c]
        ys = [y for c in contacts for y in c]
        xs.append(xs[0] + P)
        ys.append(ys[0] + P)
        n = len(xs) - 1
        d = [(ys[m + 1] - ys[m]) / (xs[m + 1] - xs[m]) for m in range(n)]
        slope = [2.0 * d[m - 1] * d[m] / (d[m - 1] + d[m]) for m in range(n)]
        slope.append(slope[0])
        k = math.floor((tau - xs[0]) / P)
        x = tau - k * P
        m = max(i for i in range(n) if xs[i] <= x + 1e-12)
        value = ys[m] + _hermite(x - xs[m], xs[m + 1] - xs[m], ys[m + 1] - ys[m], slope[m], slope[m + 1])
        return k * P + value

    def planted(self, side, t, ctx):
        """Whether the foot holds the pelvis down at foot time t: in a contact under Foot placement (the lock's
        window), else on or near the ground (down)."""
        if ctx["placement"] <= 0.0:
            return self.down(side, t)
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        return r <= to - hs

    def _just_off(self, side, t, ctx):
        """Whether the foot (foot time t) has just left the ground under Foot placement: in the first
        SWING_EASE of a swing. Its leg, straight at the lift-off of a contact held longer, would stop dead at
        its reach as the body moves on; such a foot holds the pelvis down a little (AIR_HOLD), so the leg
        straightens into the lift-off and bends out of it."""
        if ctx["placement"] <= 0.0:
            return False
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        r -= to - hs
        return 0.0 < r <= SWING_EASE * self.swing_len[side][i]

    def _clock(self, side, tau, ctx):
        """The foot's own source time at body time tau in this cycle (Foot placement's clock)."""
        return self.foot_time(side, tau, ctx["placement"], ctx.get("grown"))

    def _growth(self, ctx):
        """How much longer each foot stays down in this cycle at each lift-off (source frames, a contact): the
        walk's own target (DOUBLE_SUPPORT of a stride at every step) x Foot placement, cut back to as long as
        the trailing leg - rolled over its ball - still reaches the hip (the knobs' own, before Balance carries
        it) at its lift-off AND over the first SWING_EASE of its swing - a foot held longer leaves from further
        behind and its swing starts there - as well as it does in the walk's own (AIR_HOLD more: a foot just
        off the ground holds the pelvis down that much); never so short that both feet are off the ground (at
        least a frame of the new cycle with both down), at most EXTEND_MAX of its swing."""
        P, v = float(self.P), ctx["placement"]
        plain = dict(ctx, balance=0.0)        # the knobs' own hip: Balance never retimes the feet
        grown = {}
        ctx["ground"] = {}
        for side in SIDES:
            th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
            out, asked = [], []
            ground = (ctx["ks"][side] if "ks" in ctx else ctx["k"])["ground_time"]
            for i, (hs, to) in enumerate(self.contact[side]):
                ds = self.double_src[side][i]
                room = EXTEND_MAX * self.swing_len[side][i]
                least = 0.0 if self.is_flight(ds) else min(room, v * max(0.0, ctx["frame"] - ds))
                most = max(least, min(room, v * self.extend[side][i]["to"]))
                window = SWING_EASE * self.swing_len[side][i]

                def short(e):
                    test = {side: [{"hs": 0.0, "to": e if m == i else 0.0} for m in range(len(self.contact[side]))],
                            OTHER[side]: [{"hs": 0.0, "to": 0.0} for _ in self.contact[OTHER[side]]]}
                    worst = -1e9
                    for k in range(GROWTH_SAMPLES + 1):
                        tau = to + e + window * k / float(GROWTH_SAMPLES)
                        t = self.foot_time(side, tau, v, test)
                        rot, ankle = self._foot_free(side, t, ctx)
                        ankle = ankle + self._lock_at(side, t, ctx)
                        limit = ctx.get("reach", self.reach)[side] * (np.linalg.norm(self.lt_at(ca, t)) + np.linalg.norm(self.lt_at(fo, t)))
                        pelvis_rot, pelvis_pos = self._body(tau / P, tau, plain)["pelvis"]
                        hip = self.lt_at(th, tau) @ pelvis_rot + pelvis_pos
                        rolled = self._rolled(side, t, rot, ankle, hip, limit, ctx)[1]
                        worst = max(worst, float(np.linalg.norm(rolled - hip)) - limit)
                    return worst
                allowed = max(0.0, short(0.0)) + 1e-6
                if short(most) <= allowed:
                    e = most
                elif short(least) > allowed:
                    e = least
                else:                                 # the longest that still reaches: bisected to 1/LOCK_STEPS
                    lo, hi = least, most
                    while hi - lo > 1.0 / LOCK_STEPS:
                        mid = 0.5 * (lo + hi)
                        lo, hi = (mid, hi) if short(mid) <= allowed else (lo, mid)
                    e = lo
                # Ground time: the contact this many times as long, its lift-off moved past what Foot placement
                # grew - asked for, so not cut back to the walk's reach: the trailing leg stretches, the foot
                # rolls further onto its toes (_roll_cost) and the pelvis sinks where even that falls short. A
                # longer stance takes its swing's time, at most GROUND_ROOM of it; a shorter one keeps half its
                # contact and, at Foot placement, a frame of both feet down.
                length, own = to - hs + 1.0, e
                ask = (ground - 1.0) * length
                if ask > 0.0:
                    e = max(e, min(GROUND_ROOM * self.swing_len[side][i], e + ask))
                elif ask < 0.0:
                    floor = -0.5 * (to - hs)
                    if v > 0.0:
                        floor = floor if self.is_flight(ds) else max(floor, ctx["frame"] - ds)
                    e = max(floor, min(e, e + ask))
                out.append({"hs": 0.0, "to": e})
                asked.append((ground, 1.0 + (e - own) / length))     # asked, held (x the contact)
            grown[side] = out
            ctx["ground"][side] = asked
        return grown

    def _pivot_weight(self, side, i, r):
        """How far the planted foot has rolled onto its ball, r frames into its contact i (0 the heel, 1 the
        ball)."""
        lam_in, lam_out, a, b = self.pivot[side][i]
        if r <= a or b <= a:
            return lam_in if r <= a else lam_out
        if r >= b:
            return lam_out
        u = (r - a) / (b - a)
        return lam_in + (lam_out - lam_in) * u * u * (3.0 - 2.0 * u)

    def _pivots(self, side, t, ctx):
        """The planted foot's heel and ball ground points at foot time t (the foot as the new cycle has it)."""
        rot, ankle = self._foot_free(side, t, ctx)
        ball = self.lt_at(self.index["ball_" + side], t) @ rot + ankle
        return ankle + self.heel_loc[side] @ rot, ball

    def _locks(self, ctx):
        """Per foot and contact the lock, in foot time: the ankle's shift along the ground that holds the foot's
        pivot (the heel rolling onto the ball) still across the contact, held where the walk's weight on it
        sits on average (zero on the load-weighted mean); across the swing after it a cubic from its
        lift-off's shift to the next contact's strike's whose end slopes cancel the pivot's own speed there, so
        the foot lifts and lands without sliding. Scaled by Foot placement. Returns ({side: [(hs, A, offsets,
        shifts, slope at its lift-off, slope at its strike)] a contact}, the longest slide held, cm)."""
        flat = lambda v: v - np.dot(v, self.up) * self.up
        G, v = LOCK_STEPS, ctx["placement"]
        locks, slide = {}, 0.0
        for side in SIDES:
            locks[side] = []
            for c, (hs, to) in enumerate(self.contact[side]):
                A = to - hs
                inside = [i / float(G) - hs for i in range(int(math.floor(hs * G)) + 1, int(math.ceil(to * G)))]
                offs = [0.0] + [r for r in inside if 1e-9 < r < A - 1e-9] + [A]
                points = [self._pivots(side, hs + r, ctx) for r in offs]
                lams = [self._pivot_weight(side, c, r) for r in offs]
                shifts = [np.zeros(3)]
                for i in range(len(offs) - 1):
                    lm = 0.5 * (lams[i] + lams[i + 1])
                    moved = (1.0 - lm) * (points[i + 1][0] - points[i][0]) + lm * (points[i + 1][1] - points[i][1])
                    shifts.append(shifts[-1] - flat(moved))
                shifts = np.array(shifts)
                slide = max(slide, float(np.linalg.norm(shifts, axis=1).max()))
                # held where the walk's weight on the foot sits on average: the pressure (and Balance) stay the walk's
                load = np.array([max(float(periodic_cr(self.ground["foot_" + side], hs + r)),
                                     float(periodic_cr(self.ground["ball_" + side], hs + r))) for r in offs])
                span = np.gradient(np.array(offs)) * np.clip(load, 0.0, 1.0)
                shifts -= (span[:, None] * shifts).sum(axis=0) / max(float(span.sum()), 1e-9)
                h = 1.0 / G
                speed = []
                for r, lam in ((0.0, lams[0]), (A - h, lams[-1])):
                    (h0, b0), (h1, b1) = self._pivots(side, hs + r, ctx), self._pivots(side, hs + r + h, ctx)
                    speed.append(flat((1.0 - lam) * (h1 - h0) + lam * (b1 - b0)) / h)
                locks[side].append((hs, A, np.array(offs), v * shifts, -v * speed[1], -v * speed[0]))
        return locks, slide

    def _lock_at(self, side, t, ctx):
        """The lock's shift of the ankle at foot time t (zero without Foot placement)."""
        locks = ctx["locks"].get(side)
        if not locks:
            return 0.0
        i, r = self._contact_at(side, t)
        hs, A, offs, shifts, out, _ = locks[i]
        if r <= A:
            return np.array([np.interp(r, offs, shifts[:, c]) for c in range(3)])
        after = locks[(i + 1) % len(locks)]
        length = self.swing_len[side][i]
        u = (r - A) / length
        start, end, back = shifts[-1], after[3][0], after[5]
        return (start + (3.0 * u * u - 2.0 * u ** 3) * (end - start)
                + (u ** 3 - 2.0 * u * u + u) * length * out + (u ** 3 - u * u) * length * back)

    def _foot_free(self, side, t, ctx):
        """The new foot at foot time t before the lock: foot_target and the pose's toe-out."""
        k = ctx["ks"][side] if "ks" in ctx else ctx["k"]
        rot, ankle = self.foot_target(side, t, k["stride"], k["stance"], ctx["spread"], k["lift"] * ctx["ex"],
                                      k["swing_out"])
        toe = ctx["turns"][side][1]
        return (rot @ exp_rot(self.up * toe) if toe else rot), ankle

    def _foot(self, side, tau, ctx):
        """The new foot at body time tau: (world rotation, ankle, the foot's own time)."""
        t = self._clock(side, tau, ctx)
        rot, ankle = self._foot_free(side, t, ctx)
        return rot, ankle + self._lock_at(side, t, ctx), t

    def _roll_frame(self, side, t, rot, ankle, sense):
        """The roll's geometry for the foot (rot, ankle) at foot time t: (pivot, the turn's axis) - over its
        ball (sense +1, heel up) or back on its heel (sense -1, toes up); None for a foot pointing straight
        down."""
        pivot = (self.lt_at(self.index["ball_" + side], t) @ rot + ankle if sense > 0.0
                 else ankle + self.heel_loc[side] @ rot)
        axis = self.foot_side[side] @ rot             # the foot's own side, level
        axis = axis - np.dot(axis, self.up) * self.up
        if np.linalg.norm(axis) < 1e-6:
            return None
        return pivot, _unit(axis)

    def _sole_lift(self, side, rot, axis, sense):
        """(how far the foot (rot) already stands off the ground about its side `axis` in the roll's sense -
        heel up for +1, toes up for -1 - and the sole's limit there), radians."""
        n = self.sole_up[side] @ rot
        n = n - np.dot(n, axis) * axis
        heel_up = math.atan2(float(np.dot(n, np.cross(axis, self.up))), float(np.dot(n, self.up)))
        return (heel_up, math.radians(SOLE_HEEL_UP)) if sense > 0.0 else (-heel_up, math.radians(SOLE_TOES_UP))

    def _sole_room(self, side, rot, axis, sense):
        """How much further (radians) the foot (rot) may roll about its side `axis` before its sole stands
        SOLE_HEEL_UP off the ground (heel up, sense +1) or SOLE_TOES_UP (toes up, -1)."""
        lift, limit = self._sole_lift(side, rot, axis, sense)
        return max(0.0, limit - lift)

    def _sole_eased(self, side, rot, axis, sense, angle):
        """The roll `angle` eased into the sole's limit: the sole's lift after the roll saturates smoothly
        (the last SOLE_EASE degrees below the limit approach it exponentially), so a roll running into the
        limit slows down rather than stopping dead."""
        lift, limit = self._sole_lift(side, rot, axis, sense)
        width = math.radians(SOLE_EASE)
        knee = limit - width
        x = lift + angle
        if x > knee:
            x = knee + width * (1.0 - math.exp(-(x - knee) / width))
        return max(0.0, x - lift)

    def _roll_cost(self, side, t, rot, ankle, hip, limit, ctx, sense):
        """The roll about the ball (sense +1, heel up, up to ROLL_BALL) or the heel (-1, toes up, up to
        ROLL_HEEL) that best trades its angle against how far the leg falls short of the hip: the least of
        ROLL_COST . angle^2 + shortfall^2 (radians). Unlike the least roll that reaches, it moves smoothly as
        the foot moves - where rolling barely helps, the least reaching roll leapt from 0 to 12 deg for a
        3 mm shortfall; this one stays small and the pelvis covers the rest."""
        geometry = self._roll_frame(side, t, rot, ankle, sense)
        if geometry is None:
            return 0.0
        pivot, axis = geometry
        # Ground time past 1 stretches the trailing leg: its foot may stand that much higher on its toes
        knob = ((ctx.get("ks") or {}).get(side) or ctx.get("k") or DEFAULTS)["ground_time"]
        stretch = max(1.0, knob) if sense > 0.0 else 1.0
        cap = math.radians(ROLL_BALL * stretch if sense > 0.0 else ROLL_HEEL) * ctx["placement"]
        most = min(2.0 * cap, self._sole_room(side, rot, axis, sense))     # searched past the cap, eased into it
        if most <= 0.0 or cap <= 0.0:
            return 0.0
        f = np.cross(axis, self.up)
        a = ankle - pivot
        x, y = float(np.dot(a, f)), float(np.dot(a, self.up))
        lat = a - x * f - y * self.up
        p = x * f + y * self.up
        q = sense * (y * f - x * self.up)            # where the ankle goes as the foot rolls (heel up / toes up)
        c0 = pivot + lat - hip
        # |ankle(th) - hip|^2 = |c0|^2 + |p|^2 + alpha cos th + beta sin th
        base = float(np.dot(c0, c0) + np.dot(p, p))
        alpha, beta = 2.0 * float(np.dot(c0, p)), 2.0 * float(np.dot(c0, q))

        def cost(th):
            reach = np.sqrt(np.maximum(base + alpha * np.cos(th) + beta * np.sin(th), 0.0))
            short = np.maximum(reach - limit, 0.0)       # eased in over ROLL_SOFT: a roll starts and ends gently
            short = np.where(short < ROLL_SOFT, short * short / (2.0 * ROLL_SOFT), short - 0.5 * ROLL_SOFT)
            return ROLL_COST * th * th + short * short
        grid = np.linspace(0.0, most, ROLL_GRID + 1)
        k = int(np.argmin(cost(grid)))
        lo, hi = grid[max(k - 1, 0)], grid[min(k + 1, ROLL_GRID)]
        for _ in range(24):                          # golden section in the bracket
            m1, m2 = hi - 0.618034 * (hi - lo), lo + 0.618034 * (hi - lo)
            lo, hi = (lo, m2) if cost(m1) <= cost(m2) else (m1, hi)
        best, knee = 0.5 * (lo + hi), 0.6 * cap      # eased into the cap: a roll running into it slows down
        if best > knee:
            best = knee + (cap - knee) * (1.0 - math.exp(-(best - knee) / (cap - knee)))
        return float(best)

    def _roll_need(self, side, t, rot, ankle, hip, limit, ctx):
        """How far the foot rolls for its leg to reach the hip, signed radians: + over its ball (heel up), -
        back on its heel (toes up). Smooth over the walk: within its contact the two blend by how far the foot
        has rolled onto its ball (ROLL_SENSE about the middle); off the ground it fades out over GROUND_TOL
        of height (its lift-off's or its strike's); a leg that reaches needs none."""
        if ctx["placement"] <= 0.0 or np.linalg.norm(ankle - hip) <= limit * (1.0 + 1e-9):
            return 0.0
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        A = to - hs
        if r <= A:
            lam, held = self._pivot_weight(side, i, r), 1.0
        else:                                         # just off the ground: its lift-off's or the next strike's
            after = r - A
            leaving = after < self.swing_len[side][i] - after
            lam = (self.pivot[side][i][1] if leaving else self.pivot[side][(i + 1) % len(self.contact[side])][0])
            if leaving:
                # a foot leaving the ground keeps its roll and lets it go over the first SWING_EASE of its
                # swing: faded by the foot's height (2.5 cm, half a frame at toe-off) it turned back about its
                # ball at once - the ankle dropped behind, the leg snapped straight, the knee clicked (a
                # Ground time's long stance rolls the foot 28 deg, 2026-10-13)
                held = 1.0 - min(after / (SWING_EASE * self.swing_len[side][i]), 1.0)
            else:
                ground = max(float(periodic_cr(self.ground["foot_" + side], t)),
                             float(periodic_cr(self.ground["ball_" + side], t)))
                held = min(max(ground / (1.0 - CONTACT_TOL / GROUND_TOL), 0.0), 1.0)
            held = held * held * (3.0 - 2.0 * held)
            if held <= 0.0:
                return 0.0
        u = min(max((lam - 0.5) / ROLL_SENSE + 0.5, 0.0), 1.0)
        ball = u * u * (3.0 - 2.0 * u)
        out = 0.0
        if ball > 0.0:
            out += ball * self._roll_cost(side, t, rot, ankle, hip, limit, ctx, 1.0)
        if ball < 1.0:
            out -= (1.0 - ball) * self._roll_cost(side, t, rot, ankle, hip, limit, ctx, -1.0)
        return held * out

    def _roll_turn(self, side, t, rot, ankle, roll):
        """The foot (rot, ankle) rolled `roll` radians: + about its ball (heel up), - about its heel (toes up),
        eased into the sole's limit; the point it rolls on stays where it is. Returns (rotation, ankle, the
        world turn about the ball or None)."""
        sense = 1.0 if roll > 0.0 else -1.0
        geometry = None if roll == 0.0 else self._roll_frame(side, t, rot, ankle, sense)
        if geometry is None:
            return rot, ankle, None
        pivot, axis = geometry
        angle = self._sole_eased(side, rot, axis, sense, abs(roll))
        if angle <= 0.0:
            return rot, ankle, None
        turn = exp_rot(axis * sense * angle)             # heel up about the ball (+), toes up about the heel (-)
        return rot @ turn, pivot + (ankle - pivot) @ turn, (turn if sense > 0.0 else None)

    def _rolled(self, side, t, rot, ankle, hip, limit, ctx):
        """Foot placement's reach at one instant: the foot rolled as far as _roll_need says. Returns
        (rotation, ankle, the world turn about the ball or None)."""
        return self._roll_turn(side, t, rot, ankle, self._roll_need(side, t, rot, ankle, hip, limit, ctx))

    def _roll_of(self, side, tau, ctx):
        """The signed roll (radians) the foot takes at body time tau: the one _lowering found for the frame
        (the evaluate's own frames - every leg solve of the frame takes the same), else 0."""
        rolls = ctx.get("rolls")
        if not rolls:
            return 0.0
        f = int(round(tau * (len(rolls[side]) - 1) / float(self.P)))
        return float(rolls[side][f % len(rolls[side])])

    def swing_at(self, side, tau):
        """How far the foot hangs off its shin at source time tau: swing_weight of its flight's progress (0 on
        every frame it is down, so a foot on the ground is never turned by its shin)."""
        s = self.air_progress(side, tau)
        return 0.0 if s is None else swing_weight(s)

    def foot_in_calf(self, side, tau, gain=1.0):
        mean, logs = self.foot_rel[side]
        return exp_rot(gain * periodic_cr(logs, tau)) @ mean

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
        """Each foot point's floor a source frame (`floor`, cm up): its lowest within the step it stands in, and
        across a swing the two steps' floors blended (a foot may stand a little higher at one step than at
        another - one step a cycle: its own lowest); and its ground contact (`ground`): 1 on its floor, 0
        GROUND_TOL above it."""
        self.floor, self.ground = {}, {}
        P = self.P
        for side in SIDES:
            steps = self.steps[side]
            for name in ("foot_" + side, "ball_" + side):
                h = self.pos[self.index[name]] @ self.up
                lows = [float(min(h[(foot.on + i) % P] for i in range(foot.length + 1))) for foot in steps]
                floor = np.zeros(P)
                for f in range(P):
                    i, k, r = self._step_at(side, float(f))
                    foot = steps[i]
                    if r <= foot.length:
                        floor[f] = lows[i]
                    else:
                        after = steps[(i + 1) % len(steps)]
                        gap = (after.on - foot.on) % P or P
                        u = (r - foot.length) / max(gap - foot.length, 1e-9)
                        floor[f] = (1.0 - u) * lows[i] + u * lows[(i + 1) % len(steps)]
                self.floor[name] = floor
                self.ground[name] = np.clip(1.0 - (h - floor) / GROUND_TOL, 0.0, 1.0)

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
        # each foot loaded as in the walk (Foot placement's longer push-off rolls off a foot the weight has left)
        cop = self.pressure(dict((name, worlds[self.index[name], :, 3, :3]) for name in self.ground), taus)
        cop_dev = ((cop - line) @ self.basis.T)[:, :2]
        l_new = pendulum(cop_dev, n / self.fps, m_dev[:, 2].mean())
        l_src = np.array([periodic_cr(self.l_dev, tau) for tau in taus])
        gain = self.follow * np.array([k["surge"] * ctx["ex"], k["sway"] * ctx["ex"]])
        swing = gain * ((l_new - l_new.mean(axis=0)) - (l_src - l_src.mean(axis=0)))
        mean = ((cop_dev.mean(axis=0) - self.cop_dev.mean(axis=0))
                - (m_dev[:, :2].mean(axis=0) - self.s_dev[:, :2].mean(axis=0)))
        if k["pelvis_forward"]:
            # Pelvis forward is asked for: Balance keeps the shift of the centre of mass it makes (the body over
            # the hips moved with them, the legs re-solved) and does not carry the hips back over the feet
            back = -k["pelvis_forward"] * self.fwd
            without = np.array([self._moved_com(bases[f], tau, ctx, back, {})
                                for f, (_, tau) in enumerate(times[:-1])])
            mean = mean + ((own - without) @ self.basis.T)[:, :2].mean(axis=0)
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
            before, turned = poss[fo], rots[fo]
            self._leg(side, tau, rots, poss, ctx, cache)
            turn = turned.T @ rots[fo]             # a swinging foot turns with its shin
            for j in below:
                poss[j] = (poss[j] - before) @ turn + poss[fo]
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
        """The cycle rebuilt from knobs (the spec's model); own_knobs() give the source back. `pose` (from
        walkpose.prepare: {"spine": {joint: local 3x3}, "head": 3x3, "pelvis": 3x3, "height": cm over the
        travel line, "knee_turn": {side: radians}}) replaces the mean pose the knob `pose`'s share."""
        k = knobs(**(given or {}))
        P = self.P
        n = max(int(round(k["tempo"])), 4) if k["tempo"] >= 1.0 else P
        ctx = {"k": k, "ex": k["exaggeration"], "travel2": self.travel * k["stride"],
               "lag": max(0.0, k["overlap"] + WEIGHT_LAG * k["weight"]) * P / float(n),
               "beta": min(max(WEIGHT_WARP * k["weight"], -0.9), 0.9),
               "phi0": self.low_phase + (WEIGHT_WARP_AFTER - 0.25) / self.strides,
               "pose": pose if (pose and k["pose"] > 0.0) else None, "alpha": k["pose"],
               "balance": 0.0 if self.balance_note else k["balance"], "carry": None}
        # Leg match: the pose's stance read against its own hips and the gait (matched_pose)
        keep, froude = self.gait_keep(k, n)
        match = k["leg_match"] if ctx["pose"] is not None else 0.0
        yaw = float(ctx["pose"].get("hips_yaw", 0.0)) if ctx["pose"] is not None else 0.0
        ctx["leg_match"] = {"on": match > 0.0, "keep": keep, "froude": froude,
                            "hips_deg": math.degrees(match * yaw) if "pelvis" in (ctx["pose"] or {}) else 0.0}
        ctx["pose"] = self.leaned_pose(self.matched_pose(ctx["pose"], match, keep), k["gait_lean"])
        fix = self.fix
        if ctx["pose"] and "width" in ctx["pose"]:      # a pose's width replaces the corrected walk's at its share
            ctx["spread"] = ctx["alpha"] * ctx["pose"]["width"] + (1.0 - ctx["alpha"]) * fix["width"]
        else:
            ctx["spread"] = fix["width"]
        ctx["ks"] = ks = sided(k)
        ctx["foot_lag"] = dict((side, ks[side]["foot_lag"] * P / float(n)) for side in SIDES)
        ctx["spine_map"] = self._spine_map(ctx["pose"], ctx["alpha"])
        ctx["turns"] = {}
        for side in SIDES:             # the pose's knee heading and toe-out, met (Knee <-> foot)
            pose, knee_turn, toe = ctx["pose"], 0.0, 0.0
            if pose is not None:
                turn = ctx["alpha"] * ks[side]["leg_turn"]
                knee_turn = turn * pose["knee_turn"][side] if "knee_turn" in pose else 0.0
                toe = turn * pose["toe"][side] if "toe" in pose else 0.0
                knee_turn, toe = meet(knee_turn, toe, ks[side]["knee_foot"])
            # the correction's turns, giving way to a pose's own at its share (Pose over the corrected walk)
            own_k = (1.0 - ctx["alpha"]) if pose is not None and "knee_turn" in pose else 1.0
            own_t = (1.0 - ctx["alpha"]) if pose is not None and "toe" in pose else 1.0
            ctx["turns"][side] = (knee_turn + own_k * fix["knee"][side], toe + own_t * fix["toe"][side])
        ctx["placement"] = 0.0 if self.placement_note else k["foot_placement"]
        # Ground time past 1 holds the trailing leg longer: it ends its stance straight on its toes, and a
        # knee near straight turns tens of degrees for millimetres of reach - so it is kept STRETCH_REACH of
        # its length at most and the pelvis sinks the rest (at 0.993, the walk's own straightest, it clicked:
        # 2026-10-13)
        stretch = dict((s, min(1.0, max(0.0, ks[s]["ground_time"] - 1.0) / GROUND_STRETCH)) for s in SIDES)
        ctx["reach"] = dict((s, r + (min(r, STRETCH_REACH) - r) * stretch[s]) for s, r in self.reach.items())
        ctx["frame"], ctx["grown"] = P / float(n), None
        ctx["locks"], held = self._locks(ctx) if ctx["placement"] > 0.0 else ({}, 0.0)
        ctx["ground"] = {}
        timed = any(ks[s]["ground_time"] != 1.0 for s in SIDES)
        if not self.placement_note and (ctx["placement"] > 0.0 or timed):
            ctx["grown"] = self._growth(ctx)        # Ground time retimes the feet with or without Foot placement
        times = [(f / float(n), f * P / float(n)) for f in range(n + 1)]
        ctx["chest_own"] = self._chest_own(times, ctx)
        drop = self._lowering(times, ctx)
        balance = {"carry": 0.0, "residual": 0.0, "note": self.balance_note if k["balance"] > 0.0 else ""}
        if ctx["balance"] > 0.0:
            only = self._com_joints()
            bases = [self._frame(phi, tau, ctx, drop[f], None, only)[0] for f, (phi, tau) in enumerate(times[:-1])]
            swinging = (any(ks[s]["arm_drag"] > 0.0 for s in SIDES) and bool(self._arm_chains())) or self._bodies_on(k)
            still = list(bases)

            def armed(carry):
                """The bases with the arms' inertia as they move under `carry` (the carry itself not in them:
                _moved_com adds it) - the carry balances the arms as they move, inertia and all."""
                frames = np.stack(still + [still[0]], axis=1)
                frames[:, n, 3, :3] += ctx["travel2"]
                rigid = self._carry_parts()[0]
                if carry is not None:
                    frames[rigid, :, 3, :3] += carry[None]
                self._body_dynamics(frames, n, ctx, only)
                self._arm_dynamics(frames, n, ctx, only)
                if carry is not None:
                    frames[rigid, :, 3, :3] -= carry[None]
                return [frames[:, f] for f in range(n)]
            if swinging:
                bases = armed(None)
            target, said = self._balance_target(times, ctx, bases)
            need = said.pop("need")
            balance.update(said)
            caches, first, carry = [dict() for _ in bases], np.array(drop), np.zeros((n + 1, 3))
            for round_ in range(BALANCE_ROUNDS if need >= CARRY_TOL else 0):   # nothing to carry at the defaults     # the carry, then the reach's drop with it, till the drop holds
                ctx["carry"] = carry = self._carry(times, ctx, bases, np.array(drop) - first, target, carry, caches)
                again = self._lowering(times, ctx)
                settled = float(np.abs(np.array(again) - np.array(drop)).max()) < CARRY_TOL
                drop = again
                if swinging:                  # the arms trail the carried body too: balance them again
                    bases = armed(carry)
                if settled and (not swinging or round_ > 0):
                    break
            balance["carry"] = float(np.linalg.norm(carry, axis=1).max()) if ctx["carry"] is not None else 0.0
        worlds = np.tile(np.eye(4), (len(self.names), n + 1, 1, 1))
        short, ctx["swing_in"] = 0.0, 0.0
        for f, (phi, tau) in enumerate(times):
            carry = None if ctx["carry"] is None else ctx["carry"][f]
            worlds[:, f], frame_short = self._frame(phi, tau, ctx, drop[f], carry)
            short = max(short, frame_short)
        body = self._body_dynamics(worlds, n, ctx)
        arms = self._arm_dynamics(worlds, n, ctx)
        if not self.balance_note:
            line = np.array([self.origin + ctx["travel2"] * phi for phi, _ in times[:-1]])
            dev = (self.com(worlds[:, :n]) - line) @ self.basis.T
            balance["sway"], balance["forward"] = float(np.ptp(dev[:, 1])), float(np.ptp(dev[:, 0]))
            balance["source_sway"] = float(np.ptp(self.s_dev[:, 1]))
            balance["follow"] = [float(v) for v in self.follow]
            if ctx["balance"] > 0.0:
                balance["residual"] = float(np.abs((self.com(worlds[:, :n]) - target) @ self.basis[:2].T).max())
        if k["in_place"] > 0.0:          # after everything the walk itself measures: it walks, then stays
            self._in_place(worlds, times, ctx)
        flat = ctx["travel2"] - np.dot(ctx["travel2"], self.up) * self.up
        info = {"frames": n, "stride_cm": float(np.linalg.norm(flat)) / (2.0 * self.strides),
                "speed": float(np.linalg.norm(flat)) / (n / self.fps) / 100.0, "lowered": float(max(drop)),
                "drop": [float(d) for d in drop], "short": short, "swing_in": ctx["swing_in"],
                "lag": ctx["lag"] * n / float(P), "knobs": k, "ground": ctx["ground"],
                "placement": {"on": ctx["placement"] > 0.0, "slide": held, "note": self.placement_note,
                              "planted": dict((side, [self.planted(side, self._clock(side, tau, ctx), ctx)
                                                      for _, tau in times[:-1]]) for side in SIDES),
                              "double": dict((s, d * n / float(P)) for s, d in
                                             (self.double_support(ctx["placement"], ctx["grown"]).items()
                                              if not self.placement_note else []))},
                "pelvis": (k["pelvis_rot"] * ctx["ex"] * k["pelvis_twist"] * k["stride"] * self.twist_gain,
                           k["pelvis_rot"] * ctx["ex"] * k["pelvis_list"]),
                "chest": self.chest_targets(k, ctx["ex"]) if self.chest_shape is not None else None,
                "arms": arms, "body": body, "leg_match": ctx["leg_match"],
                "balance": balance, "in_place": k["in_place"]}
        return Result(worlds, n, info)

    def _in_place(self, worlds, times, ctx):
        """In place (on `worlds`, (J, n+1, 4, 4)): every joint moved back by the root's progress along the
        walk - the travel line's and the root's own surge along it - and by the line's climb, x In place. The root
        stays where frame 0 has it but for its weave aside (Root sway) and its own height; the body moves about it,
        the planted feet slide back at the walk's speed, the last frame is the first."""
        root = self.index["root"]
        along = (worlds[root, :, 3, :3] - worlds[root, 0, 3, :3]) @ self.fwd
        climb = float(np.dot(ctx["travel2"], self.up)) * np.array([phi for phi, _ in times])
        shift = np.outer(along, self.fwd) + np.outer(climb, self.up)
        worlds[:, :, 3, :3] -= ctx["k"]["in_place"] * shift[None]

    def foot_target(self, side, tau, stride, stance=1.0, spread=0.0, lift=1.0, swing_out=0.0):
        """The new foot at source time tau: (world rotation, ankle position). Stance: the source's foot
        moved with its step's footprint - across the travel line, the walk's half-spread about the middle of
        its prints plus half the pose's `spread`, all x `stance`; swing: the source's swing between the new
        footprints of its step and the next, its lift scaled, bowed `swing_out` cm out (+) or in along
        sin(pi s) of its flight (from where it leaves the ground to where it lands: a foot that is down never
        slides)."""
        steps, j, P = self.steps[side], self.index["foot_" + side], self.P
        rot, src = self.wrot(j, tau), self.wpos(j, tau)
        travel2 = self.travel * stride
        i, k, r = self._step_at(side, tau)
        foot = steps[i]
        sign = 1.0 if side == "l" else -1.0
        middle = 0.5 * (self.body_print("l") + self.body_print("r"))

        def shift(step, cycle):
            half = self.print_across(step) - middle
            across = stance * (half + sign * spread / 2.0) - half
            return ((travel2 - self.travel) * ((step.mid + cycle * P) / P)
                    + (stride - 1.0) * step.coords[0] * self.fwd + across * self.across)
        here = shift(foot, k)
        if r <= foot.length + 1e-9:
            return rot, src + here
        nxt = (i + 1) % len(steps)
        k_on = k + (1 if nxt == 0 else 0)
        after = steps[nxt]
        t_off, t_on = foot.on + foot.length + k * P, after.on + k_on * P
        p_off, p_on = self.wpos(j, t_off), self.wpos(j, t_on)
        x, x_off, x_on = (float(np.dot(p, self.fwd)) for p in (src, p_off, p_on))
        s = (x - x_off) / (x_on - x_off) if abs(x_on - x_off) > 1e-9 else (tau - t_off) / (t_on - t_off)
        lift_up = float(np.dot(src - (1.0 - s) * p_off - s * p_on, self.up))
        flight = self.air_progress(side, tau) if swing_out else None
        bow = 0.0 if flight is None else sign * swing_out * math.sin(math.pi * flight) * self.lside
        return rot, src + (1.0 - s) * here + s * shift(after, k_on) + (lift - 1.0) * lift_up * self.up + bow

    def _body(self, phi, tau, ctx, drop=0.0, carry=None):
        """The root's and the pelvis's new (rotation, position); the pelvis `drop` cm lower for the reach and
        `carry` (a world vector) along for the balance. Balance takes over the pelvis's forward swing from the
        stride: it scales by (1 - Balance) x Stride + Balance and the pendulum brings what the step changes."""
        k, ex = ctx["k"], ctx["ex"]
        line2 = self.origin + ctx["travel2"] * phi
        extra = self.pelvis_extra(tau, k, ex)
        out = {"extra": extra}
        for name, mean in (("root", self.root_mean), ("pelvis", self.pelvis_mean)):
            j = self.index[name]
            dev = periodic_cr(self.pdev[j], tau) @ self.basis.T
            scale = k["stride"] if name == "root" else (1.0 - ctx["balance"]) * k["stride"] + ctx["balance"]
            # Surge: x the pelvis's forward and back - Bob's partner along the walk (the root keeps its own)
            surge = k["surge"] if name == "pelvis" else 1.0
            along = mean[0] + surge * scale * ex * (dev[0] - mean[0])
            if name == "pelvis":         # Pelvis forward: the hips ahead of (+) or behind (-) the feet
                along += k["pelvis_forward"]
            # the root runs straight down the travel line at Root sway 0 (a root weaving with the hips weaves
            # the capsule a game moves by it); the pelvis sways
            gain = k["root_sway"] if name == "root" else k["sway"] * ex
            aside = mean[1] + gain * (dev[1] - mean[1])
            if name == "pelvis":
                pose, a = ctx["pose"], ctx["alpha"]
                v = float(periodic_cr(self.pdev[j], warp(phi, ctx["beta"], ctx["phi0"], self.strides) * self.P) @ self.up) - mean[2]
                own = mean[2] + self.fix["height"]          # the corrected walk's mean height
                base = own if pose is None or "height" not in pose else (1.0 - a) * own + a * pose["height"]
                # Pelvis height raises or lowers it over the feet (the reach's drop still holds the legs)
                height = base + k["pelvis_height"] + k["bob"] * ex * shape_bob(v, k["weight"]) - drop
                centre = self.wmean[j] if pose is None or "pelvis" not in pose else toward(self.wmean[j], pose["pelvis"], a)
                turn = periodic_cr(self.wlog[j], tau)
                if centre is not self.wmean[j]:     # a tilted pelvis turns about the walk's world axes
                    turn = turn @ self.wmean[j] @ centre.T
                rot = exp_rot(k["pelvis_rot"] * ex * turn) @ centre
                if extra is not None:      # Twist and Hip drop: a turn in the world about the pelvis
                    rot = rot @ exp_rot(extra)
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
        n = len(times) - 1
        need, legs = np.zeros(n), []
        needs = dict((side, np.zeros(n)) for side in SIDES)
        for f, (phi, tau) in enumerate(times[:-1]):
            carry = None if ctx["carry"] is None else ctx["carry"][f]
            pelvis_rot, pelvis_pos = self._body(phi, tau, ctx, 0.0, carry)["pelvis"]
            legs.append({})
            for side in SIDES:
                t = self._clock(side, tau, ctx)
                th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
                hip = self.lt_at(th, tau) @ pelvis_rot + pelvis_pos
                rot, ankle = self._foot(side, tau, ctx)[:2]
                limit = ctx.get("reach", self.reach)[side] * (np.linalg.norm(self.lt_at(ca, t)) + np.linalg.norm(self.lt_at(fo, t)))
                needs[side][f] = self._roll_need(side, t, rot, ankle, hip, limit, ctx)
                legs[f][side] = (t, rot, ankle, hip, limit)
        # the heel's roll lets go gradually: never earlier than a frame needs it, and after its peak it eases
        # down over ROLL_RELEASE of a stride. Taken frame by frame it fell 20 deg in two frames as a Ground
        # time's long stance ended - the heel dropped, the ankle jumped back and the knee clicked (2026-10-13)
        # Under Ground time past 1 the stance ends with a large roll that rises as fast (2 -> 20 deg in two
        # frames): there the whole curve is a smooth cover over the frames' needs, heel up and toes up apart
        # A stance leg short of its reach (a raised pelvis) rolls toes up over its heel from the strike, then heel
        # up over its ball: taken frame by frame the toes-up roll came in 10-15 deg in one frame at the strike and
        # flipped to heel up 15-22 deg in one frame at the heel-to-ball handoff, and the near-straight knee
        # snapped (2026-10-16) - so the roll changes no faster than ROLL_RATE; where that leaves the leg short
        # the pelvis's drop (a smooth cover below) takes the rest. Only ever less roll: a roll where the frame
        # asked for none would move the foot's still point
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        for side in SIDES:
            if ks[side]["ground_time"] > 1.0:
                up, back = np.maximum(needs[side], 0.0), np.maximum(-needs[side], 0.0)
                sigma = LOWER_BLUR * n / self.strides
                needs[side] = smooth_cover(up, sigma) - smooth_cover(back, sigma)
            needs[side] = released(needs[side], ROLL_RELEASE * n / self.strides)
            if ks[side]["ground_time"] <= 1.0:
                needs[side] = rate_limited(needs[side], math.radians(ROLL_RATE) * self.strides / float(n))
        ctx["rolls"] = (dict((side, np.append(needs[side], needs[side][0])) for side in SIDES)
                        if ctx["placement"] > 0.0 else None)
        # Near straight a knee turns tens of degrees for a millimetre of reach, so a leg held exactly at its
        # limit by the drop's cover, or a swinging leg clamped there, snaps (2026-10-16, a raised pelvis): once
        # the legs fall short anywhere (by MARGIN_FULL cm, eased in from nothing - so the defaults are untouched)
        # they are held LEG_MARGIN of their length short of the limit, and a swinging foot past it is drawn in
        # toward its hip on a smooth curve rather than clamped
        def needs_for(margin):
            held, aloft = dict((side, np.zeros(n)) for side in SIDES), dict((side, np.zeros(n)) for side in SIDES)
            for f, (phi, tau) in enumerate(times[:-1]):
                for side in SIDES:
                    t, rot, ankle, hip, limit = legs[f][side]
                    limit *= 1.0 - margin
                    down = self.planted(side, t, ctx)
                    # with the margin a swinging foot holds the pelvis as far as it cannot be drawn in: fully
                    # as it comes down to its print, not at all mid-swing (swing_weight, the draw-in's own)
                    share = 0.0 if down or self._just_off(side, t, ctx) or margin <= 0.0 else 1.0 - self.swing_at(side, t)
                    if not down and share <= 0.0 and not self._just_off(side, t, ctx):
                        continue
                    ankle = self._roll_turn(side, t, rot, ankle, self._roll_of(side, tau, ctx))[1]
                    q = ankle - hip
                    if np.linalg.norm(q) <= limit * (1.0 + 1e-9):
                        continue
                    qu = float(np.dot(q, self.up))
                    disc = qu * qu - (float(np.dot(q, q)) - limit * limit)
                    if disc >= 0.0:
                        if share > 0.0:      # (the margin's pass only, so only once the stance legs fall short)
                            held[side][f] = share * (-qu - math.sqrt(disc))
                        else:
                            (held if down else aloft)[side][f] = -qu - math.sqrt(disc)
            out = np.zeros(n)
            for side in SIDES:     # a foot just off the ground holds the pelvis no lower than its stance did...
                cap = held[side].max()
                if (ctx.get("ks") or {}).get(side, ctx["k"])["ground_time"] > 1.0:
                    cap = np.inf   # ...unless Ground time held it longer: its swing leaves from further behind
                out = np.maximum(out, np.maximum(held[side], np.minimum(aloft[side], cap)))
            return out
        need = needs_for(0.0)
        weight = min(1.0, float(need.max()) / MARGIN_FULL)        # the stance legs short: the margin comes in
        if weight > 0.0:
            need = np.maximum(need, weight * needs_for(LEG_MARGIN))
        drop = smooth_cover(need, LOWER_BLUR * len(need) / self.strides)     # LOWER_BLUR of a stride
        ctx["reel"] = None
        short = self._swing_excess(times, legs, ctx, drop, 0.0).max()
        if weight > 0.0 or short > 0.0:          # a swing past its reach (or near it, with the margin): drawn in
            margin = weight * LEG_MARGIN
            reel = {}
            for side in SIDES:
                excess = self._swing_excess(times, legs, ctx, drop, margin, side)
                reel[side] = smooth_cover(excess, LOWER_BLUR * n / self.strides)
                reel[side] = np.append(reel[side], reel[side][0])
            ctx["reel"] = reel
        return np.append(drop, drop[0])

    def _swing_excess(self, times, legs, ctx, drop, margin, only=None):
        """How far (cm, a frame) a swinging foot's ankle lies past its leg's reach (less `margin` of it) from the
        hip lowered by `drop` (None: not lowered); the most of both feet, or `only` that side's."""
        n = len(times) - 1
        out = np.zeros(n)
        for f, (phi, tau) in enumerate(times[:-1]):
            for side in SIDES if only is None else (only,):
                t, rot, ankle, hip, limit = legs[f][side]
                if self.planted(side, t, ctx) or self._just_off(side, t, ctx) or self.swing_at(side, t) <= 0.0:
                    continue
                if drop is not None:
                    hip = hip - self.up * drop[f]
                ankle = self._roll_turn(side, t, rot, ankle, self._roll_of(side, tau, ctx))[1]
                out[f] = max(out[f], float(np.linalg.norm(ankle - hip)) - limit * (1.0 - margin))
        return np.maximum(out, 0.0)

    def _reel_of(self, side, tau, ctx):
        """How far (cm) the swinging foot is drawn in toward its hip at body time tau (_lowering's), else 0."""
        reel = ctx.get("reel")
        if not reel:
            return 0.0
        f = int(round(tau * (len(reel[side]) - 1) / float(self.P)))
        return float(reel[side][f % len(reel[side])])

    def _frame(self, phi, tau, ctx, drop=0.0, carry=None, only=None):
        """Every joint's new world at one frame (parents first, helpers last) - or only the joints in `only`
        (closed under their parents; the rest stay identity); and how far a foot that is down fell short (a
        foot in the air that cannot reach its path: ctx["swing_in"], the most it passes closer)."""
        k, ex = ctx["k"], ctx["ex"]
        rots, poss = [None] * len(self.names), [None] * len(self.names)
        body = self._body(phi, tau, ctx, drop, carry)
        chest = self.chest_extra(tau, k, ex, ctx.get("chest_own"))
        ks = ctx.get("ks") or {"l": k, "r": k}
        gains = {"spine": k["spine"] * ex}
        feet = dict((side, self._clock(side, tau, ctx)) for side in SIDES)
        rolls = {}
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
                missed = self._leg(name[-1], tau, rots, poss, ctx, None, rolls)
                if self.planted(name[-1], feet[name[-1]], ctx):
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
                clock = feet[self.leg_side[j]] if j in self.leg_side else tau     # below a thigh: its foot's
                t = clock - self.lag[j] * ctx["lag"]
                pose, a = ctx["pose"], ctx["alpha"]
                if kind == "head":
                    centre = self.wmean[j] if pose is None or "head" not in pose else toward(self.wmean[j], pose["head"], a)
                    rots[j] = exp_rot(k["head"] * ex * periodic_cr(self.wlog[j], t)) @ centre
                elif j in self.world_arms and (pose is None or "arms" not in pose):
                    # the upper arm hangs and swings in the world
                    arms = ks[self._side(j)]["arms"]
                    rots[j] = exp_rot(arms * ex * periodic_cr(self.wlog[j], t)) @ self.wmean[j]
                else:
                    centre = self.lmean[j]
                    gain = ks[self._side(j)]["arms"] * ex if kind == "arm" else gains.get(kind, 1.0)
                    if pose is not None:
                        if j in pose.get("spine", {}):
                            centre = toward(centre, pose["spine"][j], a)
                        if "arms" in pose and kind in ("arm", "finger"):
                            # the pose's arms are the mean the walk's swing runs about; hands that hold one
                            # thing together HOLD it - its swing fades, the thing sways (_arm_dynamics)
                            if j in pose["arms"]:
                                centre = toward(centre, pose["arms"][j], a)
                            if pose.get("grip"):
                                gain *= 1.0 - a
                    if j in self.forearms:
                        gain *= ks[self._side(j)]["elbow"]
                    turn = periodic_cr(self.llog[j], t)
                    if j in ctx["spine_map"]:      # about the world axis it turns about in the walk
                        turn = turn @ ctx["spine_map"][j]
                    local = exp_rot(gain * turn) @ centre
                    if j in self.balls:        # the toes trail the swinging shin with the foot
                        hang = self.swing_at(self.balls[j], clock)
                        toe_side = self.balls[j]
                        lag, flex = ctx["foot_lag"][toe_side], ks[toe_side]["foot_flex"]
                        if hang > 0.0 and (lag > 0.0 or flex != 1.0):
                            late = exp_rot(flex * periodic_cr(self.llog[j], clock - BALL_LAG * lag))
                            local = toward(local, late @ centre, hang)
                    rots[j] = local @ rots[p]
                    if j in self.balls and self.balls[j] in rolls:       # the toes stay down as the foot rolls
                        rots[j] = rots[j] @ rolls[self.balls[j]].T
                    if j in self.counter and body["extra"] is not None:
                        rots[j] = rots[j] @ exp_rot(-self.counter[j] * body["extra"])
                    if j in self.chest_share and chest is not None:
                        rots[j] = rots[j] @ exp_rot(self.chest_share[j] * chest)
                poss[j] = self.lt_at(j, t) @ rots[p] + poss[p]
        out = np.tile(np.eye(4), (len(self.names), 1, 1))
        for j in range(len(self.names)):
            if rots[j] is not None:
                out[j, :3, :3], out[j, 3, :3] = rots[j], poss[j]
        return out, short

    # -- the trunk and the head: two bodies on springs over the frames --

    def _bodies_on(self, k):
        """Whether Torso drag or Head drag moves anything (a walk with a spine above its pelvis)."""
        return (k["torso_drag"] > 0.0 or k["head_drag"] > 0.0) and self._trunk_chains() is not None

    def _trunk_chains(self):
        """(the spine joints from the pelvis up to the chest, the neck joints, the head or None) - each the one
        child of its kind (spine_NN, then neck_NN, then head) of the joint before; None without a spine."""
        if getattr(self, "_trunk", 0) == 0:
            def climb(j, pattern):
                out = []
                while True:
                    kids = [c for c, p in enumerate(self.parents) if p == j and re.match(pattern, self.names[c])]
                    if not kids:
                        return out
                    j = kids[0]
                    out.append(j)
            spine = climb(self.index["pelvis"], r"spine_\d+$")
            necks = climb(spine[-1], r"neck_\d+$") if spine else []
            top = (necks or spine or [None])[-1]
            head = next((c for c, p in enumerate(self.parents) if top is not None and p == top
                         and self.names[c] == "head"), None)
            self._trunk = (spine, necks, head) if spine else None
        return self._trunk

    def _body_motion(self, kin_rot, pivot, lever, n, drag, bounce, inertia=1.0):
        """One rigid body's world rotation (n+1, 3, 3), following `kin_rot` (n+1, 3, 3) through a damped spring
        `drag` frames late (zeta = 1 - 0.75 bounce, the arms' spring) and feeling the acceleration of its pivot's
        path `pivot` (n, 3, the travel out) on its `lever` (in the body's frame) - a rod about its end. Integrated
        periodic as the arms are, the seam spread."""
        zeta = 1.0 - 0.75 * bounce
        w0 = 2.0 * zeta / drag
        S = max(ARM_SUBSTEPS, int(math.ceil(4.0 * w0)))
        dt = 1.0 / S
        target = self._resampled(kin_rot, n, S)
        accel = self._smooth_accel(pivot, n, S)
        kk, cc = w0 * w0, 2.0 * zeta * w0
        R, w = kin_rot[0].copy(), np.zeros(3)
        record = np.zeros((n, 3, 3))
        for cycle in range(ARM_CYCLES):
            first = R.copy()
            for step in range(n * S):
                if step % S == 0:
                    record[step // S] = R
                alpha = -kk * _log3(target[step].T @ R) - cc * w
                r = lever @ R
                length2 = float(r @ r)
                if length2 > 1e-12:
                    alpha = alpha + inertia * 0.75 / length2 * _cross3(r, -accel[step])
                w = w + alpha * dt
                R = R @ _exp3(w * dt)
            if float(np.linalg.norm(_log3(first.T @ R))) < ARM_SETTLED:
                break
        miss = _log3(record[0].T @ R)
        series = np.array([record[f] @ _exp3(-miss * f / float(n)) for f in range(n)])
        return np.concatenate([series, series[:1]])

    def _spread_turn(self, worlds, kin, joints, shares, turn):
        """`joints` (a chain, parents first) turned in the world by `turn` (n+1, 3 rotation vectors) x their
        `shares`, each on its offset in its parent as `kin` had it (in place on worlds); returns the new
        {joint: (n+1, 4, 4)}."""
        n1 = worlds.shape[1]
        new = {}
        for j, share in zip(joints, shares):
            p = self.parents[j]
            back = np.swapaxes(_batch_rot(kin[p]), -1, -2)
            offset = np.einsum("fi,fij->fj", kin[j, :, 3, :3] - kin[p, :, 3, :3], back)
            m = np.tile(np.eye(4), (n1, 1, 1))
            m[:, :3, :3] = _batch_rot(kin[j]) @ exp_rot(share * turn)
            m[:, 3, :3] = np.einsum("fi,fij->fj", offset, _batch_rot(worlds[p])) + worlds[p, :, 3, :3]
            worlds[j] = m
            new[j] = m
        return new

    def _body_dynamics(self, worlds, n, ctx, only=None):
        """The trunk and the head on springs, in place on `worlds` (J, n+1, 4, 4), before the arms (they hang on
        the moving chest). The trunk: the chest's world turn follows the frames' through Torso drag's spring and
        feels the first spine joint's acceleration on the upper body's centre of mass; the difference spread up
        the spine (each joint by its place). The head: its world turn - the gaze the frames give it - through
        Head drag's spring, feeling the first neck joint's acceleration; the neck takes NECK_SHARES of the
        difference. Everything above re-attached as the frames had it. Returns {"torso", "head": the most either
        turned off its frames (deg), "drag": (torso, head)}."""
        k = ctx["k"]
        out = {"torso": 0.0, "head": 0.0, "drag": (k["torso_drag"], k["head_drag"])}
        chains = self._trunk_chains()
        if chains is None or not self._bodies_on(k):
            return out
        spine, necks, head = chains
        travel = (worlds[spine[0], n, 3, :3] - worlds[spine[0], 0, 3, :3]) / float(n)
        flat = lambda path: path[:n] - np.outer(np.arange(n), travel)
        gaze = _batch_rot(worlds[head]) if head is not None else None
        if k["torso_drag"] > 0.0:
            kin = worlds.copy()
            chest = _batch_rot(kin[spine[-1]])
            upper = [j for j in range(len(self.names)) if self.mass[j] > 0.0 and j != spine[0]
                     and self.kind[j] in ("spine", "head", "arm", "finger") and (only is None or j in only)]
            base = kin[spine[0], :n, 3, :3]
            if upper and float(self.mass[upper].sum()) > 0.0:
                com = np.tensordot(self.mass[upper] / self.mass[upper].sum(), kin[upper, :n, 3, :3], axes=(0, 0))
            else:
                com = kin[spine[-1], :n, 3, :3]
            lever = np.einsum("fi,fij->fj", com - base, np.swapaxes(chest[:n], -1, -2)).mean(axis=0)
            dyn = self._body_motion(chest, flat(kin[spine[0], :, 3, :3]), lever, n, k["torso_drag"],
                                    k["torso_bounce"], BODY_INERTIA)
            turn = log_rot(np.swapaxes(chest, -1, -2) @ dyn)
            new = self._spread_turn(worlds, kin, spine, [(i + 1.0) / len(spine) for i in range(len(spine))], turn)
            # the upper arms the frames hang in the world (no pose's arms) keep hanging there on the moving chest
            held = self.world_arms if (ctx["pose"] is None or "arms" not in ctx["pose"]) else ()
            self._reattach(worlds, kin, new, only, held)
            out["torso"] = math.degrees(float(np.linalg.norm(turn, axis=1).max()))
        if head is not None and (k["head_drag"] > 0.0 or k["torso_drag"] > 0.0):
            kin = worlds.copy()
            carried = _batch_rot(kin[head])
            if k["head_drag"] > 0.0:
                pivot = necks[0] if necks else self.parents[head]
                reach = np.einsum("fi,fij->fj", kin[head, :n, 3, :3] - kin[pivot, :n, 3, :3],
                                  np.swapaxes(gaze[:n], -1, -2)).mean(axis=0)
                dyn = self._body_motion(gaze, flat(kin[pivot, :, 3, :3]), reach * (1.0 + HEAD_LIFT), n,
                                        k["head_drag"], k["torso_bounce"], HEAD_INERTIA)
            else:
                dyn = gaze             # Head drag 0: the head keeps the gaze the frames give it, the neck takes it
            turn = log_rot(np.swapaxes(carried, -1, -2) @ dyn)
            shares = [NECK_SHARES[min(i, len(NECK_SHARES) - 1)] for i in range(len(necks))] + [1.0]
            new = self._spread_turn(worlds, kin, necks + [head], shares, turn)
            self._reattach(worlds, kin, new, only)
            if k["head_drag"] > 0.0:
                out["head"] = math.degrees(float(np.linalg.norm(log_rot(np.swapaxes(gaze, -1, -2) @ dyn),
                                                                axis=1).max()))
        return out

    # -- the arms: the body's inertia on top of their motion --

    def _side(self, j):
        """"l" or "r": the side a joint's name says (UE names end in _l / _r), else "l" (a middle joint)."""
        name = self.names[j]
        return "r" if name.endswith("_r") else "l"

    def _arm_chains(self):
        """{side: [upperarm, lowerarm, hand] indices} and each chain's parent (the clavicle, else what holds the
        upper arm); sides missing a joint are left out."""
        out = {}
        for side in SIDES:
            names = ["%s_%s" % (b, side) for b in ("upperarm", "lowerarm", "hand")]
            if all(n in self.index for n in names):
                out[side] = [self.index[n] for n in names]
        return out

    def _arm_dynamics(self, worlds, n, ctx, only=None):
        """The arms following the body with inertia (in place on `worlds`, (J, n+1, 4, 4)). What the frames
        give them is their TARGET; each limb (upper arm, forearm, hand) turns toward its target - its own
        motion on the joint above as that joint actually moves - through a damped spring, and feels the
        acceleration of the point it hangs from: the arms trail the body's bob, sway and twist and whip through
        (Arm drag: the spring's delay in frames; Arm bounce: how far it overshoots). Hands that hold one thing
        together (a pose's grip) keep holding it: the thing sways and trails as one body and the arms reach it
        by IK. Integrated ARM_SUBSTEPS a frame, cycle after cycle until a cycle starts where the last did, the
        seam closed. Returns what it did (info["arms"])."""
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        chains = self._arm_chains()
        pose = ctx["pose"]
        grip = bool(pose and pose.get("grip") and ctx["alpha"] > 0.0 and len(chains) == 2)
        # each arm its own side's drag and bounce; hands holding one thing move as one: the two sides' mean
        own = dict((side, (ks[side]["arm_drag"], ks[side]["arm_bounce"])) for side in chains)
        if grip:
            own = dict((side, (sum(d for d, _ in own.values()) / 2.0, sum(b for _, b in own.values()) / 2.0))
                       for side in own)
        drag = max([d for d, _ in own.values()] or [0.0])
        out = {"drag": drag, "bounce": max([b for _, b in own.values()] or [0.0]), "grip": grip, "cycles": 0}
        if drag <= 0.0 or not chains:
            out["drag"] = 0.0
            return out

        def spring(d, b):
            zeta = 1.0 - 0.75 * b
            w0 = 2.0 * zeta / d                   # per frame: a damped spring lags 2 zeta / w0 behind its target
            return w0, zeta, max(ARM_SUBSTEPS, int(math.ceil(4.0 * w0)))   # w0 dt <= 1/4: the integration stays true
        kin = worlds.copy()
        if grip:
            new, cycles = self._grip_motion(kin, n, chains, *spring(*own["r"]))
        else:
            new, cycles = {}, 0
            for side, chain in chains.items():
                if own[side][0] <= 0.0:           # this arm as the frames put it
                    continue
                got, used = self._limb_motion(kin, n, chain, *spring(*own[side]))
                new.update(got)
                cycles = max(cycles, used)
        out["cycles"] = cycles
        self._reattach(worlds, kin, new, only)
        return out

    def _resampled(self, rots, n, S):
        """A rotation series (n+1, 3, 3) (the last the first) at every 1/S frame of the cycle, slerped:
        (n * S, 3, 3)."""
        steps = np.arange(n * S) / float(S)
        f = np.floor(steps).astype(int)
        frac = steps - f
        logs = log_rot(np.swapaxes(rots[:-1], -1, -2) @ rots[1:])
        return rots[f] @ exp_rot(frac[:, None] * logs[f])

    def _hand_lever(self, j):
        """A hand's lever for its inertia: where its farthest finger joint stands in it (the walk's own, mean
        over the cycle), or None without fingers. The whole hand swings; its metacarpals' bases (4 cm) made it
        a stiff little pendulum that shook with every jolt of the wrist."""
        below, todo = [], [j]
        while todo:
            p = todo.pop()
            kids = [c for c in range(len(self.names)) if self.parents[c] == p and self.kind[c] == "finger"]
            below += kids
            todo += kids
        if not below:
            return None
        back = np.swapaxes(self.rot[j], -1, -2)
        reach = [np.einsum("fi,fij->fj", self.pos[c] - self.pos[j], back).mean(axis=0) for c in below]
        return max(reach, key=lambda v: float(np.linalg.norm(v)))

    def _smooth_accel(self, path, n, S):
        """A periodic path's acceleration (per frame squared) at every 1/S frame, of its first ARM_HARMONICS
        harmonics a stride, none faster than ACCEL_HZ: (n * S, 3)."""
        coeffs = np.fft.rfft(path, axis=0) / float(n)
        u = np.arange(n * S) / float(S)
        out = np.zeros((n * S, 3))
        top = min(ARM_HARMONICS * self.strides, int(ACCEL_HZ * n / self.fps), (n - 1) // 2)
        for k in range(1, top + 1):
            w = 2.0 * math.pi * k / float(n)
            out += 2.0 * np.real(np.outer(np.exp(1j * w * u), coeffs[k])) * -(w * w)
        return out

    def _limb_motion(self, kin, n, chain, w0, zeta, S):
        """One arm's chain under inertia: {joint: (n+1, 4, 4) worlds}, the cycles it took."""
        dt = 1.0 / S
        top, base = chain[0], self.parents[chain[0]]
        rot = lambda j: np.array([orthonormal(kin[j, f, :3, :3]) for f in range(n + 1)])
        R = dict((j, rot(j)) for j in chain + [base])
        rel = dict((j, np.array([R[j][f] @ R[self.parents[j]][f].T for f in range(n + 1)])) for j in chain)
        # the bones' offsets in their parents (the arm's lengths) and each limb's lever for its inertia
        offset = dict((j, self.lt[j].mean(axis=0)) for j in chain[1:])     # the walk's own: a pose turns
        lever = dict((chain[i], offset[chain[i + 1]]) for i in range(len(chain) - 1))   # bones, not lengthens
        reach = self._hand_lever(chain[-1])
        if reach is not None:
            lever[chain[-1]] = reach
        # the shoulder's acceleration per substep, the travel taken out (it does not accelerate): of the path's
        # first ARM_HARMONICS harmonics a stride - the body's bob, sway and twist; a second difference of the frames
        # would hand the arms the frames' own noise, and the hand (the shortest lever) shook with it
        travel = (kin[top, n, 3, :3] - kin[top, 0, 3, :3]) / float(n)
        path = np.array([kin[top, f, 3, :3] - travel * f for f in range(n)])
        a_shoulder = self._smooth_accel(path, n, S)
        base_rot = self._resampled(R[base], n, S)
        rel_s = dict((j, self._resampled(rel[j], n, S)) for j in chain)
        levers = [lever.get(j) for j in chain]
        state, spin = [], []
        parent = base_rot[0]
        for j in chain:
            state.append(rel_s[j][0] @ parent)
            spin.append(np.zeros(3))
            parent = state[-1]
        record = np.zeros((len(chain), n, 3, 3))
        used = 0
        kk, cc = w0 * w0, 2.0 * zeta * w0
        for cycle in range(ARM_CYCLES):
            used = cycle + 1
            first = [r.copy() for r in state]
            for step in range(n * S):
                if step % S == 0:
                    for i in range(len(chain)):
                        record[i, step // S] = state[i]
                parent = base_rot[step]
                a_pivot = a_shoulder[step]
                for i, j in enumerate(chain):
                    Rj, w = state[i], spin[i]
                    target = rel_s[j][step] @ parent
                    e = _log3(target.T @ Rj)
                    alpha = -kk * e - cc * w
                    r = levers[i] @ Rj if levers[i] is not None else None
                    if r is not None:
                        length2 = float(r @ r)
                        if length2 > 1e-12:
                            alpha = alpha + 1.5 * ARM_INERTIA / length2 * _cross3(r, -a_pivot)
                    w = w + alpha * dt
                    Rj = Rj @ _exp3(w * dt)
                    state[i], spin[i] = Rj, w
                    if r is not None:
                        a_pivot = a_pivot + _cross3(alpha, r) + _cross3(w, _cross3(w, r))
                    parent = Rj
            if max(float(np.linalg.norm(_log3(first[i].T @ state[i]))) for i in range(len(chain))) < ARM_SETTLED:
                break
        out = {}
        rots = {}
        for i, j in enumerate(chain):          # the seam: what the last cycle missed of closing, spread over it
            miss = _log3(record[i, 0].T @ state[i])
            series = np.array([record[i, f] @ _exp3(-miss * f / float(n)) for f in range(n)])
            rots[j] = np.concatenate([series, series[:1]])
        for i, j in enumerate(chain):
            m = np.tile(np.eye(4), (n + 1, 1, 1))
            m[:, :3, :3] = rots[j]
            if i == 0:
                m[:, 3, :3] = kin[j, :, 3, :3]
            else:
                p = chain[i - 1]
                m[:, 3, :3] = out[p][:, 3, :3] + np.einsum("i,fij->fj", offset[j], rots[p])
            out[j] = m
        return out, used

    def _grip_motion(self, kin, n, chains, w0, zeta, S):
        """Two hands holding one thing: the right hand carries it - its world turn and place trail their
        target through the same spring (the travel taken out); the left keeps its hold on the right; both arms
        reach their hands by IK (the elbows bend the way the frames bend them, the bones keep their lengths)."""
        dt = 1.0 / S
        hold = chains["r"][-1]
        R = np.array([orthonormal(kin[hold, f, :3, :3]) for f in range(n + 1)])
        travel = (kin[hold, n, 3, :3] - kin[hold, 0, 3, :3]) / float(n)
        path = np.array([kin[hold, f, 3, :3] - travel * f for f in range(n + 1)])
        path[n] = path[0]
        steps = np.arange(n * S) / float(S)
        f0 = np.floor(steps).astype(int)
        frac = (steps - f0)[:, None]
        target_x = (1.0 - frac) * path[f0] + frac * path[f0 + 1]
        target_r = self._resampled(R, n, S)
        state_r, w = R[0].copy(), np.zeros(3)
        x, v = path[0].copy(), np.zeros(3)
        rec_r, rec_x = np.zeros((n, 3, 3)), np.zeros((n, 3))
        kk, cc = w0 * w0, 2.0 * zeta * w0
        used = 0
        for cycle in range(ARM_CYCLES):
            used = cycle + 1
            first = (state_r.copy(), x.copy())
            for step in range(n * S):
                if step % S == 0:
                    rec_r[step // S], rec_x[step // S] = state_r, x
                e = _log3(target_r[step].T @ state_r)
                w = w + (-kk * e - cc * w) * dt
                state_r = state_r @ _exp3(w * dt)
                v = v + (-kk * (x - target_x[step]) - cc * v) * dt
                x = x + v * dt
            if float(np.linalg.norm(_log3(first[0].T @ state_r))) < ARM_SETTLED and \
                    float(np.linalg.norm(first[1] - x)) < ARM_SETTLED * 100.0:
                break
        miss_r, miss_x = _log3(rec_r[0].T @ state_r), x - rec_x[0]
        held = np.tile(np.eye(4), (n + 1, 1, 1))
        for f in range(n + 1):
            g = f % n
            held[f, :3, :3] = rec_r[g] @ _exp3(-miss_r * g / float(n))
            held[f, 3, :3] = rec_x[g] - miss_x * g / float(n) + travel * f
        out = {}
        for side, chain in chains.items():
            up_j, low_j, hand_j = chain
            l1, l2 = (float(np.linalg.norm(self.lt[j].mean(axis=0))) for j in (low_j, hand_j))
            mu, ml, mh = (np.tile(np.eye(4), (n + 1, 1, 1)) for _ in range(3))
            for f in range(n + 1):
                hand = kin[hand_j, f] @ np.linalg.inv(kin[hold, f]) @ held[f]
                sh, el, wr = kin[up_j, f, 3, :3], kin[low_j, f, 3, :3], kin[hand_j, f, 3, :3]
                e = _unit(wr - sh)
                bend = (el - sh) - np.dot(el - sh, e) * e
                bend = _unit(bend) if np.linalg.norm(bend) > 1e-4 else _any_perpendicular(e)
                knee, reached, _ = two_bone(sh, hand[3, :3], l1, l2, bend, 1.0)
                e2 = _unit(reached - sh)
                bend2 = _unit((knee - sh) - np.dot(knee - sh, e2) * e2)
                normal, normal2 = _unit(np.cross(e, bend)), _unit(np.cross(e2, bend2))
                mu[f, :3, :3] = orthonormal(kin[up_j, f, :3, :3]) @ align(_unit(el - sh), normal, _unit(knee - sh), normal2)
                ml[f, :3, :3] = orthonormal(kin[low_j, f, :3, :3]) @ align(_unit(wr - el), normal,
                                                                          _unit(reached - knee), normal2)
                mu[f, 3, :3], ml[f, 3, :3] = sh, knee
                mh[f, :3, :3], mh[f, 3, :3] = hand[:3, :3], reached
            out[up_j], out[low_j], out[hand_j] = mu, ml, mh
        return out, used

    def _reattach(self, worlds, kin, new, only=None, held=()):
        """`new` ({joint: (n+1, 4, 4)}) into `worlds`; every joint hanging off a changed one (its DAG children,
        the helpers that follow it) carried along as the frames had it on its anchor (of `only`, when given) -
        a joint in `held` keeps the world turn the frames give it (it hangs in the world), its place carried."""
        changed = set(new)
        for j, m in new.items():
            worlds[j] = m
        for j in self.order:
            if j in changed or (only is not None and j not in only):
                continue
            p = self.parents[j]
            anchor = p if p in changed else None
            if anchor is None and j in self.follows and self.follows[j][0] in changed:
                anchor = self.follows[j][0]
            if anchor is None:
                continue
            worlds[j] = np.einsum("fij,fjk->fik", np.einsum("fij,fjk->fik", kin[j], np.linalg.inv(kin[anchor])),
                                  worlds[anchor])
            if j in held:
                worlds[j, :, :3, :3] = kin[j, :, :3, :3]
            changed.add(j)

    def _leg_source(self, side, tau, ctx):
        """What a leg's solve takes from the source and the knobs at tau - all of it independent of the hip."""
        k = ctx["k"]
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        foot_rot, ankle, t = self._foot(side, tau, ctx)      # the leg at its foot's own time (Foot placement)
        knee_turn = ctx["turns"][side][0]
        l1, l2 = float(np.linalg.norm(self.lt_at(ca, t))), float(np.linalg.norm(self.lt_at(fo, t)))
        h, kn, a = self.wpos(th, t), self.wpos(ca, t), self.wpos(fo, t)
        e = _unit(a - h)
        bend = (kn - h) - np.dot(kn - h, e) * e
        bend = _unit(bend) if np.linalg.norm(bend) > 1e-6 else _unit(self.fwd - np.dot(self.fwd, e) * e)
        knee_bend = turned_about(bend, -e, knee_turn) if knee_turn else bend      # turned about the leg
        hang = self.swing_at(side, t)
        return {"joints": (th, ca, fo), "t": t, "hip": self.lt_at(th, tau), "foot_rot": foot_rot, "ankle": ankle,
                "lengths": (l1, l2), "dirs": (_unit(kn - h), _unit(a - kn)), "normal": _unit(np.cross(e, bend)),
                "bend": knee_bend, "wrot": (self.wrot(th, t), self.wrot(ca, t)), "hang": hang,
                "in_calf": (self.foot_in_calf(side, t - ctx["foot_lag"][side], ctx["ks"][side]["foot_flex"])
                            if hang > 0.0 else None)}

    def _leg(self, side, tau, rots, poss, ctx, cache=None, rolls=None):
        """Thigh, calf and foot by IK from the new hip to the new foot; each bone turned by the rotation
        taking its source (direction, leg plane) onto the new one. Returns how far the foot fell short.
        `cache` ({side: _leg_source}) spares the source half when only the hip moves; `rolls` takes the foot's
        roll over its ball ({side: world turn}), which its toes take back."""
        src = None if cache is None else cache.get(side)
        if src is None:
            src = self._leg_source(side, tau, ctx)
            if cache is not None:
                cache[side] = src
        th, ca, fo = src["joints"]
        pelvis = self.parents[th]
        hip = src["hip"] @ rots[pelvis] + poss[pelvis]
        foot_rot, ankle, turn = self._roll_turn(side, src["t"], src["foot_rot"], src["ankle"],
                                                self._roll_of(side, tau, ctx))
        if turn is not None and rolls is not None:
            rolls[side] = turn
        reel = self._reel_of(side, tau, ctx) * self.swing_at(side, src["t"])     # in the air only
        if reel > 0.0:
            reach = ankle - hip
            d = float(np.linalg.norm(reach))
            ankle = hip + reach * max(0.0, 1.0 - reel / d) if d > 1e-9 else ankle
        knee, reached, short = two_bone(hip, ankle, src["lengths"][0], src["lengths"][1], src["bend"],
                                        ctx.get("reach", self.reach)[side])
        e2 = _unit(reached - hip)
        bend2 = _unit((knee - hip) - np.dot(knee - hip, e2) * e2)
        n_new = _unit(np.cross(e2, bend2))
        rots[th] = src["wrot"][0] @ align(src["dirs"][0], src["normal"], _unit(knee - hip), n_new)
        rots[ca] = src["wrot"][1] @ align(src["dirs"][1], src["normal"], _unit(reached - knee), n_new)
        rots[fo] = foot_rot if src["hang"] <= 0.0 else toward(foot_rot, src["in_calf"] @ rots[ca], src["hang"])
        poss[th], poss[ca], poss[fo] = hip, knee, reached
        return short


class Result(object):
    """The new cycle: world matrices (J, N+1, 4, 4) in the source's world, N, and what happened."""

    def __init__(self, worlds, frames, info):
        self.worlds, self.frames, self.info = worlds, frames, info


def describe(result):
    info = result.info
    text = "%d frames, stride %.1f cm, %.2f m/s" % (info["frames"], info["stride_cm"], info["speed"])
    if info.get("in_place", 0.0) > 0.0:
        text += " in place" if info["in_place"] >= 1.0 else " (%.0f %% in place)" % (100.0 * info["in_place"])
    if info["lowered"] > 0.05:
        text += " | pelvis lowered up to %.1f cm at the contacts for the reach" % info["lowered"]
    if info["short"] > 0.005:
        text += " | a foot falls %.1f cm short of its step" % info["short"]
    if info.get("swing_in", 0.0) > 0.5:
        text += " | the swinging foot passes up to %.1f cm nearer the body" % info["swing_in"]
    turn = lambda v: "+-%.1f%s" % (abs(v), " reversed" if v < 0.0 else "")
    if "pelvis" in info:
        text += " | pelvis twists %s deg, the hips %s" % tuple(turn(v) for v in info["pelvis"])
    if info.get("chest"):
        text += " | chest twists %s deg, sways %s" % tuple(turn(v) for v in info["chest"])
    body = info.get("body") or {}
    drags = [(name, d) for name, d in (("the trunk", body.get("drag", (0.0, 0.0))[0]),
                                       ("the head", body.get("drag", (0.0, 0.0))[1])) if d > 0.0]
    if drags:
        text += " | %s frames behind" % " and ".join("%s %.1f" % (name, d) for name, d in drags)
    if info.get("arms") and info["arms"].get("drag"):
        a = info["arms"]
        text += " | %s %.1f frames behind the body%s" % (
            "the held weapon trails" if a["grip"] else "the arms trail", a["drag"],
            ", bouncing" if a["bounce"] > 0.05 else "")
    return text + placement_line(info) + balance_line(info)


def placement_line(info):
    """What Foot placement did, for a status line ("" when it is off)."""
    placed = info.get("placement") or {}
    if placed.get("note") and info["knobs"]["foot_placement"] > 0.0:
        return " | no foot placement: " + placed["note"]
    if not placed.get("on"):
        return ""
    both = " / ".join("%.1f" % placed["double"][s] for s in SIDES if s in placed["double"])
    return " | feet planted (slides of up to %.1f cm held), both feet down %s frames a step" % (placed["slide"], both)


def balance_line(info):
    """What Balance did, for a status line ("" when nothing worth saying)."""
    balance = info.get("balance") or {}
    if balance.get("note"):
        return " | no balance: " + balance["note"]
    if balance.get("carry", 0.0) > 0.1:
        return (" | balance: the pelvis carried up to %.1f cm over the feet (the CoM sways %.1f cm, the source's "
                "%.1f)" % (balance["carry"], balance.get("sway", 0.0), balance.get("source_sway", 0.0)))
    return ""
