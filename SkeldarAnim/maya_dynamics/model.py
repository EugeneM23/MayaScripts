"""Dynamics' solver (2026-10-26): joint chains that swing after their animation.

The model the known spring-bone systems share (VRM SpringBone, Dynamic Bone, Kawaii Physics; the
research: docs/superpowers/specs/2026-10-26-bone-dynamics-research.md). Every joint's TAIL - the next
member's pivot, the last member's a virtual tip past it - is a point that keeps its velocity (less the
Damping), feels gravity and the wind, is pulled back toward where the animation points the bone
(Stiffness, a spring) and kept within a cone about it (Limit), then stands on the bone's length again,
root to tip, and is pushed out of the colliders. The root's pivot is the animation's. A member's new
rotation is its animated one turned by the least rotation from its animated direction onto its
simulated one, so the twist about the bone stays the animation's and the lengths the animation's.

Units cm, s, degrees; gravity and wind strength in g (1 = 980 cm/s^2). Row vectors, as Maya's: a
frame's rotation in rows 0-2, its pivot in row 3, `v' = v @ T`. numpy and the stdlib only (a test pins
it). Spec: docs/superpowers/specs/2026-10-26-bone-dynamics-design.md
"""

import collections
import functools
import math

import numpy as np

G = 980.0                     # cm / s^2
FPS_REF = 30.0                # Damping is the share of a tail's velocity lost every 1/30 s
F_SOFT = 0.3                  # Stiffness 0..1: a spring of F_SOFT..F_FIRM Hz, log-spaced (0: none)
F_FIRM = 6.0
SETTLE_CM = 0.01              # Loop: the tails at the cycle's start move less than this between cycles
MAX_CYCLES = 8
MIN_CYCLES = 2
PASSES = 3                    # push out + length again, each tail each substep
RELAX = 4                     # equal-mass length passes before the exact projection, each substep
MAX_SUBSTEPS = 16
MAX_PREROLL = 600
WIND_SPEED = 300.0            # cm/s: gusts sweep along the wind
SLOW_SHARE = 0.2              # the gusts' swell at a fifth of the turbulence's frequency
HARMONICS = 24                # the most harmonics a noise channel sums
MIN_FREQUENCY = 0.05          # Hz
EPS = 1e-12

#  (key, low, high, default, the tip's default - None: one value down the chain)
KNOBS = (
    ("stiffness", 0.0, 1.0, 0.3, 0.5),
    ("damping", 0.0, 1.0, 0.2, 1.0),
    ("limit", 0.0, 180.0, 180.0, 1.0),
    ("gravity", -2.0, 4.0, 1.0, None),
    ("inertia", 0.0, 1.0, 0.0, None),
    ("wind", 0.0, 4.0, 1.0, 1.5),
    ("radius", 0.0, 50.0, 1.0, 1.0),
    ("friction", 0.0, 1.0, 0.3, None),
)
TIP_LOW, TIP_HIGH = 0.0, 4.0
#  (key, low, high, default) whole numbers
OPTIONS = (("substeps", 1, MAX_SUBSTEPS, 4), ("preroll", 0, MAX_PREROLL, 30))
FLAGS = (("tip", True), ("loop", False))

PRESETS = collections.OrderedDict([
    ("hair", {"stiffness": 0.35, "stiffness_tip": 0.5, "damping": 0.15, "damping_tip": 1.0,
              "limit": 180.0, "gravity": 1.0, "inertia": 0.0, "wind": 1.0, "wind_tip": 1.5,
              "radius": 1.0, "radius_tip": 0.8, "friction": 0.3}),
    ("cloth", {"stiffness": 0.2, "stiffness_tip": 0.6, "damping": 0.25, "damping_tip": 1.0,
               "limit": 90.0, "gravity": 1.0, "inertia": 0.0, "wind": 1.5, "wind_tip": 1.3,
               "radius": 2.0, "radius_tip": 1.0, "friction": 0.5}),
    ("chain", {"stiffness": 0.0, "stiffness_tip": 1.0, "damping": 0.05, "damping_tip": 1.0,
               "limit": 180.0, "gravity": 1.5, "inertia": 0.0, "wind": 0.2, "wind_tip": 1.0,
               "radius": 1.0, "radius_tip": 1.0, "friction": 0.2}),
    ("tail", {"stiffness": 0.6, "stiffness_tip": 0.4, "damping": 0.3, "damping_tip": 1.0,
              "limit": 60.0, "limit_tip": 1.0, "gravity": 0.3, "inertia": 0.0, "wind": 0.5,
              "wind_tip": 1.0, "radius": 2.0, "radius_tip": 0.6, "friction": 0.3}),
    ("stiff", {"stiffness": 0.85, "stiffness_tip": 0.8, "damping": 0.4, "damping_tip": 1.0,
               "limit": 30.0, "limit_tip": 1.0, "gravity": 0.5, "inertia": 0.0, "wind": 0.3,
               "wind_tip": 1.0, "radius": 1.0, "radius_tip": 1.0, "friction": 0.3}),
])
PRESET_LABELS = {"hair": "Hair", "cloth": "Cloth", "chain": "Chain", "tail": "Tail",
                 "stiff": "Stiff"}


# ------------------------------------------------------------------ settings

def _clamp(value, low, high):
    return min(high, max(low, value))


def _number(value, fallback):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if math.isfinite(number) else fallback


def _normal(s):
    out = {}
    for key, low, high, default, tip in KNOBS:
        out[key] = _clamp(_number(s.get(key), default), low, high)
        if tip is not None:
            out[key + "_tip"] = _clamp(_number(s.get(key + "_tip"), tip), TIP_LOW, TIP_HIGH)
    for key, low, high, default in OPTIONS:
        out[key] = int(round(_clamp(_number(s.get(key), default), low, high)))
    for key, default in FLAGS:
        value = s.get(key, default)
        out[key] = bool(value) if isinstance(value, (bool, int, float)) else default
    return out


DEFAULTS = _normal({})


def settings(given=None):
    """A chain's settings: `given` over the defaults, each knob clamped into its range, unknown keys
    dropped."""
    s = dict(DEFAULTS)
    s.update(dict((k, v) for k, v in (given or {}).items() if k in DEFAULTS))
    return _normal(s)


def ramp(root, tip, n):
    """A knob down a chain of `n` joints: `root` at the first, `root * tip` at the last, linear
    between."""
    if n <= 1:
        return np.array([float(root)])
    i = np.arange(n) / float(n - 1)
    return float(root) * (1.0 + (float(tip) - 1.0) * i)


def spring_k(stiffness):
    """The spring of Stiffness `stiffness` (0..1), (2 pi f)^2 in 1/s^2; 0 is none."""
    if stiffness <= 0.0:
        return 0.0
    f = F_SOFT * (F_FIRM / F_SOFT) ** float(stiffness)
    return (2.0 * math.pi * f) ** 2


def joint_values(s, n):
    """Every knob of settings `s` down a chain of `n` joints: {key: (n,)}."""
    out = {}
    for key, _low, _high, _default, tip in KNOBS:
        out[key] = ramp(s[key], s[key + "_tip"] if tip is not None else 1.0, n)
    return out


# ------------------------------------------------------------------ geometry

def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, EPS)


def perpendicular(axis):
    """A unit vector square to each `axis` (..., 3)."""
    axis = np.asarray(axis, float)
    hint = np.where(np.abs(axis[..., :1]) < 0.9, np.array([1.0, 0.0, 0.0]),
                    np.array([0.0, 1.0, 0.0]))
    return _unit(np.cross(axis, hint))


def _skew(v):
    z = np.zeros(v.shape[:-1])
    return np.stack([np.stack([z, -v[..., 2], v[..., 1]], -1),
                     np.stack([v[..., 2], z, -v[..., 0]], -1),
                     np.stack([-v[..., 1], v[..., 0], z], -1)], -2)


def turn_between(a, b):
    """The row-vector rotations (..., 3, 3) taking unit `a` onto unit `b` the least way
    (`a @ T == b`); a half turn about a square axis when they are opposite."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    v = np.cross(a, b)
    c = np.sum(a * b, axis=-1)
    k = _skew(v)
    eye = np.broadcast_to(np.eye(3), k.shape)
    opposite = c < -1.0 + 1e-9
    denominator = np.where(opposite, 1.0, 1.0 + c)
    column = eye + k + (k @ k) / denominator[..., None, None]
    if np.any(opposite):
        u = perpendicular(a)
        half = 2.0 * u[..., :, None] * u[..., None, :] - eye
        column = np.where(opposite[..., None, None], half, column)
    return np.swapaxes(column, -1, -2)


def turned(v, a, b):
    """`v` (..., 3) turned by the least rotation taking unit `a` onto unit `b` - `turn_between`'s
    rotation applied without building it (Rodrigues with the unnormalised axis `a x b`)."""
    k = np.cross(a, b)
    c = np.sum(a * b, axis=-1, keepdims=True)
    out = c * v + np.cross(k, v) + k * (np.sum(k * v, axis=-1, keepdims=True)
                                        / np.maximum(1.0 + c, EPS))
    opposite = c[..., 0] < -1.0 + 1e-9
    if np.any(opposite):
        u = perpendicular(a)
        half = 2.0 * u * np.sum(u * v, axis=-1, keepdims=True) - v
        out = np.where(opposite[..., None], half, out)
    return out


def rotate_by(v, rotvec):
    """`v` (..., 3) turned by the rotation vectors `rotvec` (..., 3) (Rodrigues)."""
    v = np.asarray(v, float)
    rotvec = np.asarray(rotvec, float)
    angle = np.linalg.norm(rotvec, axis=-1, keepdims=True)
    axis = rotvec / np.maximum(angle, EPS)
    cos, sin = np.cos(angle), np.sin(angle)
    return (v * cos + np.cross(axis, v) * sin
            + axis * np.sum(axis * v, axis=-1, keepdims=True) * (1.0 - cos))


def rotvec_between(a, b):
    """The rotation vectors (..., 3) taking unit `a` onto unit `b` the least way."""
    axis = np.cross(a, b)
    s = np.linalg.norm(axis, axis=-1, keepdims=True)
    c = np.sum(a * b, axis=-1, keepdims=True)
    angle = np.arctan2(s, c)
    fallback = perpendicular(a)
    unit_axis = np.where(s > 1e-12, axis / np.maximum(s, EPS), fallback)
    return unit_axis * angle


def clamp_cone(d, axis, limit):
    """Unit directions `d` kept within `limit` radians of `axis` (both (..., 3))."""
    d = np.asarray(d, float)
    axis = np.asarray(axis, float)
    limit = np.asarray(limit, float)
    c = np.clip(np.sum(d * axis, axis=-1), -1.0, 1.0)
    over = np.arccos(c) > limit + 1e-12
    if not np.any(over):
        return d
    perp = d - axis * c[..., None]
    size = np.linalg.norm(perp, axis=-1, keepdims=True)
    perp = np.where(size > 1e-9, perp / np.maximum(size, EPS), perpendicular(axis))
    edge = axis * np.cos(limit)[..., None] + perp * np.sin(limit)[..., None]
    return np.where(over[..., None], edge, d)


def sphere_push(p, r, centre, cr):
    """Points `p` (m, 3) of radii `r` (m,) out of spheres at `centre` of radius `cr`:
    (pushed, touching (m,), normal (m, 3))."""
    p = np.asarray(p, float)
    d = p - np.asarray(centre, float)
    dist = np.linalg.norm(d, axis=-1)
    n = np.where(dist[..., None] > 1e-9, d / np.maximum(dist, EPS)[..., None],
                 np.array([0.0, 1.0, 0.0]))
    depth = dist - (np.asarray(r, float) + cr)
    touching = depth < 0.0
    return np.where(touching[..., None], p - n * depth[..., None], p), touching, n


def capsule_push(p, r, a, b, cr):
    """Points out of a capsule round the segment a-b (the nearest point on it)."""
    p = np.asarray(p, float)
    a = np.asarray(a, float)
    ab = np.asarray(b, float) - a
    span = float(np.dot(ab, ab)) or 1.0
    t = np.clip(((p - a) @ ab) / span, 0.0, 1.0)
    return sphere_push(p, r, a + t[..., None] * ab, cr)


def plane_push(p, r, origin, normal):
    """Points held above a plane by their radius."""
    p = np.asarray(p, float)
    n = _unit(normal)
    depth = (p - np.asarray(origin, float)) @ n - np.asarray(r, float)
    touching = depth < 0.0
    return (np.where(touching[..., None], p - n * depth[..., None], p), touching,
            np.broadcast_to(n, p.shape))


# --------------------------------------------------------------------- noise

@functools.lru_cache(maxsize=256)
def _harmonics(freq, period, seed, channel):
    low = max(1, int(math.ceil(0.5 * freq * period)))
    high = max(low, int(math.floor(2.0 * freq * period)))
    ks = np.arange(low, high + 1)
    if len(ks) > HARMONICS:
        ks = np.unique(np.round(np.linspace(low, high, HARMONICS)).astype(int))
    rng = np.random.default_rng([abs(int(seed)), int(channel)])
    amp = rng.normal(size=len(ks))
    amp /= math.sqrt(float(np.sum(amp ** 2)) / 2.0) or 1.0
    phase = rng.uniform(0.0, 2.0 * math.pi, len(ks))
    return ks.astype(float), amp, phase


def noise(t, freq, period, seed, channel):
    """A smooth seeded noise of unit RMS at times `t` (s, any shape), periodic over `period` s: a
    sum of its harmonics from half to twice `freq` Hz."""
    ks, amp, phase = _harmonics(round(max(MIN_FREQUENCY, float(freq)), 4), round(float(period), 6),
                                int(seed), int(channel))
    x = (2.0 * math.pi / period) * np.asarray(t, float)[..., None] * ks + phase
    return np.sum(np.sin(x) * amp, axis=-1)


# --------------------------------------------------------------------- input

ChainInput = collections.namedtuple("ChainInput", "frames carrier settings")
ChainInput.__doc__ = """A chain to simulate: its members' world frames (n, T, 4, 4) - rotation rows,
the pivot in row 3 - root first; its carrier's world positions (T, 3) (what Inertia ignores the travel
of); its `settings` (`settings()`). In a loop T is the cycle's frames plus one: the last is the next
cycle's first."""

Collider = collections.namedtuple("Collider", "kind a b radius normal enabled")
Collider.__new__.__defaults__ = (None, None)
Collider.__doc__ = """A collider over the frames: "sphere" (centre `a`), "capsule" (segment `a`-`b`),
each (T, 3), radius (T,); or "plane" (a point `a` on it and its `normal`, (T, 3)). `enabled` (T,) or
None: always."""

WindInput = collections.namedtuple("WindInput",
                                   "direction strength turbulence gust frequency seed")
WindInput.__doc__ = """The wind arrow over the frames: its direction (T, 3), strength in g,
turbulence, gust (T,), frequency Hz (T,; their mean is used), a seed."""


def repeats_first(frames_list, carrier, tol=1e-3):
    """True when the last frame of every chain's frames repeats its first, less the carrier's travel
    between them (a range whose last frame closes the cycle)."""
    carrier = np.asarray(carrier, float)
    travel = carrier[-1] - carrier[0]
    for frames in frames_list:
        frames = np.asarray(frames, float)
        if frames.shape[1] < 2:
            return False
        if np.abs(frames[:, -1, :3, :3] - frames[:, 0, :3, :3]).max() > tol:
            return False
        if np.abs(frames[:, -1, 3, :3] - travel - frames[:, 0, 3, :3]).max() > tol:
            return False
    return True


# ------------------------------------------------------------------ the solver

class _Prepared(object):
    """Every chain's joints flattened into one array (chains contiguous), the colliders and the wind
    as arrays over the frames."""

    def __init__(self, chains, colliders, wind, fps, loop):
        self.fps = float(fps)
        self.loop = bool(loop)
        self.chains = list(chains)
        self.substeps = max(int(c.settings["substeps"]) for c in self.chains)
        self.preroll = 0 if loop else max(int(c.settings["preroll"]) for c in self.chains)
        self.frames_in = int(np.asarray(self.chains[0].frames).shape[1])
        self.frames_out = self.frames_in - 1 if loop else self.frames_in
        pivots, tails, carriers, values, firsts, owner, members = [], [], [], [], [], [], []
        self.layout = []
        offset = 0
        for c, chain in enumerate(self.chains):
            f = np.asarray(chain.frames, float)
            n = f.shape[0]
            if n < 2:
                raise ValueError("a chain needs two members")
            tip = bool(chain.settings["tip"])
            m = n if tip else n - 1
            piv = f[:, :, 3, :3]
            tail = np.empty((m, f.shape[1], 3))
            tail[:min(m, n - 1)] = piv[1:min(m, n - 1) + 1]
            if tip:
                local = (piv[n - 1, 0] - piv[n - 2, 0]) @ f[n - 1, 0, :3, :3].T
                tail[n - 1] = piv[n - 1] + np.einsum("i,tij->tj", local, f[n - 1, :, :3, :3])
            pivots.append(piv[:m])
            tails.append(tail)
            carriers.append(np.repeat(np.asarray(chain.carrier, float)[None], m, axis=0))
            values.append(joint_values(chain.settings, m))
            firsts.extend([True] + [False] * (m - 1))
            owner.extend([c] * m)
            members.extend(range(m))
            self.layout.append((offset, m, n))
            offset += m
        self.J = offset
        self.member = np.array(members)
        # the joints of every chain at member index m, solved root to tip one index at a time
        self.by_member = [np.nonzero(self.member == m)[0] for m in range(int(self.member.max()) + 1)]
        self.piv = np.swapaxes(np.concatenate(pivots, 0), 0, 1)          # (F, J, 3)
        self.tail = np.swapaxes(np.concatenate(tails, 0), 0, 1)
        self.carrier = np.swapaxes(np.concatenate(carriers, 0), 0, 1)
        bone = self.tail - self.piv
        self.length = np.linalg.norm(bone, axis=-1)                       # (F, J)
        if (self.length < 1e-6).any():
            raise ValueError("a member stands on the next - a chain needs length")
        self.dir = bone / self.length[..., None]
        self.firsts = np.array(firsts)
        self.owner = np.array(owner)
        self.start = np.array([self.layout[c][0] for c in owner])
        v = dict((key, np.concatenate([vals[key] for vals in values])) for key in values[0])
        self.k = np.array([spring_k(s) for s in v["stiffness"]])
        self.damping = v["damping"]
        self.limit = np.radians(v["limit"])
        self.gravity = v["gravity"]
        self.inertia = v["inertia"]
        self.wind_gain = v["wind"]
        self.radius = v["radius"]
        self.friction = v["friction"]
        self.dt = 1.0 / (self.fps * self.substeps)
        self.keep = (1.0 - self.damping) ** (FPS_REF * self.dt)
        self.share = 1.0 - np.exp(-self.k * self.dt * self.dt)
        self.no_limit = bool((self.limit >= math.pi - 1e-9).all())
        self._colliders(colliders)
        self._wind(wind)
        if self.loop:
            # the state wraps from the next cycle's first frame onto this cycle's: each joint moves
            # back by its chain root's travel over the cycle
            self.travel = (self.piv[-1] - self.piv[0])[self.start]
        else:
            self.travel = np.zeros((self.J, 3))

    # -------------------------------------------------------------- inputs

    def _colliders(self, colliders):
        colliders = [c for c in (colliders or []) if c is not None]
        self.K = len(colliders)
        if not self.K:
            return
        F = self.frames_in

        def track(value, width):
            if value is None:
                return np.zeros((F, width)) if width else np.zeros(F)
            value = np.asarray(value, float)
            return value if value.ndim > 1 or not width else np.tile(value, (F, 1))

        self.ca = np.stack([track(c.a, 3) for c in colliders], axis=1)            # (F, K, 3)
        self.cb = np.stack([track(c.b if c.b is not None else c.a, 3) for c in colliders], 1)
        self.cr = np.stack([track(c.radius, 0) for c in colliders], axis=1)        # (F, K)
        normals = []
        for c in colliders:
            normals.append(_unit(track(c.normal, 3)) if c.kind == "plane" else np.zeros((F, 3)))
        self.cn = np.stack(normals, axis=1)
        self.plane = np.array([c.kind == "plane" for c in colliders])
        self.enabled = np.stack([np.ones(F, bool) if c.enabled is None
                                 else np.asarray(c.enabled, bool) for c in colliders], axis=1)
        depth, _n, _near = self._depths(self.tail[0], self.radius, self.ca[0], self.cb[0],
                                        self.cr[0], self.cn[0])
        self.ignored = depth < 0.0                                                 # (J, K)

    def _wind(self, wind):
        self.wind = wind
        if wind is None:
            return
        self.wdir = _unit(np.asarray(wind.direction, float))
        self.wstrength = np.asarray(wind.strength, float)
        self.wturb = np.asarray(wind.turbulence, float)
        self.wgust = np.asarray(wind.gust, float)
        self.wfreq = max(MIN_FREQUENCY, float(np.mean(np.asarray(wind.frequency, float))))
        self.wseed = int(wind.seed)
        cycle = self.frames_out if self.loop else self.preroll + self.frames_out
        self.period = max(cycle, 1) / self.fps
        rng = np.random.default_rng([abs(self.wseed), 99])
        jitter = rng.uniform(0.0, 1.0 / self.wfreq, self.J)
        self.wdelay = (self.tail[0] @ self.wdir[0]) / WIND_SPEED + jitter              # (J,)

    def _depths(self, p, radius, a, b, r, n):
        """(depth (m, K), normal (m, K, 3), nearest point (m, K, 3)) of points `p` (m, 3) of radii
        `radius` (m,) against every collider at one moment: its ends `a`, `b` (K, 3), radius `r`
        (K,), a plane's normal `n` (its nearest point: a point on it)."""
        ab = b - a
        span = np.maximum(np.sum(ab * ab, axis=-1), EPS)
        rel = p[:, None, :] - a[None]
        t = np.clip(np.einsum("jki,ki->jk", rel, ab) / span, 0.0, 1.0)
        d = rel - t[..., None] * ab[None]
        dist = np.linalg.norm(d, axis=-1)
        normal = np.where(dist[..., None] > 1e-9, d / np.maximum(dist, EPS)[..., None],
                          np.array([0.0, 1.0, 0.0]))
        depth = dist - (radius[:, None] + r[None])
        flat = np.einsum("jki,ki->jk", rel, n) - radius[:, None]
        depth = np.where(self.plane[None], flat, depth)
        normal = np.where(self.plane[None, :, None], n[None], normal)
        near = a[None] + t[..., None] * ab[None]
        return depth, normal, near

    def _onto(self, p, above, length, radius, near, normal, deepest, plane):
        """The point at `length` from `above` on the surface it is inside of, nearest `p`: where the
        bone's sphere meets the collider's sphere round `near` (a capsule's or a sphere's nearest
        axis point, grown by the joint's `radius`) or its plane - the circle of both, its nearest
        point. A parent inside the collider has no such point: the plain push then."""
        L = length[:, None]
        rr = np.linalg.norm(p - near, axis=-1, keepdims=True) - deepest[:, None]   # surface radius
        u = near - above
        D = np.linalg.norm(u, axis=-1, keepdims=True)
        u = np.where(plane[:, None], -normal, u / np.maximum(D, EPS))
        # along u from `above`: a sphere's circle at a, a plane's at its offset plane
        a = np.where(plane[:, None], np.sum((p - above) * u, axis=-1, keepdims=True) + deepest[:, None],
                     (L * L - rr * rr + D * D) / (2.0 * np.maximum(D, EPS)))
        h2 = L * L - a * a
        w = (p - above) - u * np.sum((p - above) * u, axis=-1, keepdims=True)
        size = np.linalg.norm(w, axis=-1, keepdims=True)
        w = np.where(size > 1e-9, w / np.maximum(size, EPS), perpendicular(u))
        exact = above + u * a + w * np.sqrt(np.maximum(h2, 0.0))
        fine = (h2[:, 0] >= 0.0) & ((D[:, 0] > 1e-9) | plane)
        return np.where(fine[:, None], exact, p - normal * deepest[:, None])

    @staticmethod
    def _at(track, fa, fb, s):
        return track[fa] + (track[fb] - track[fa]) * s

    def _wind_at(self, t, fa, fb, s):
        """The wind's acceleration on every tail at time `t` (s), before its exposure: (J, 3)."""
        direction = _unit(self._at(self.wdir, fa, fb, s))
        strength = float(self._at(self.wstrength, fa, fb, s))
        if strength == 0.0:
            return np.zeros((self.J, 3)), direction
        turb = float(self._at(self.wturb, fa, fb, s))
        gust = float(self._at(self.wgust, fa, fb, s))
        tt = t - self.wdelay
        along = 1.0 + gust * noise(tt, self.wfreq * SLOW_SHARE, self.period, self.wseed, 0)
        lateral = np.stack([noise(tt, self.wfreq, self.period, self.wseed, ch)
                            for ch in (1, 2, 3)], axis=-1)
        lateral = lateral - direction * (lateral @ direction)[:, None]
        accel = strength * G * (direction * along[:, None] + turb * lateral)
        return accel * self.wind_gain[:, None], direction

    # ---------------------------------------------------------------- step

    def parents_of(self, points, piv):
        out = np.empty_like(points)
        out[1:] = points[:-1]
        out[self.firsts] = piv[self.firsts]
        return out

    def rebuild(self, dirs, length, piv):
        steps = dirs * length[:, None]
        sums = np.cumsum(steps, axis=0)
        before = sums[self.start] - steps[self.start]
        return piv[self.start] + sums - before

    def relax(self, q, length, piv):
        """`RELAX` Gauss-Seidel passes over the bones, root to tip, each tail and its parent's
        sharing the correction (the root's pivot pinned): what an even chain's lengths would do to
        the points. Alone, the exact projection after it moves only the child of every bone - a
        parent too heavy to feel it - which gains energy at fine substeps and makes the answer
        depend on them."""
        q = q.copy()
        for _pass in range(RELAX):
            for m, idx in enumerate(self.by_member):
                above = piv[idx] if m == 0 else q[idx - 1]
                diff = q[idx] - above
                dist = np.linalg.norm(diff, axis=-1, keepdims=True)
                fix = (dist - length[idx, None]) * diff / np.maximum(dist, EPS)
                if m == 0:
                    q[idx] -= fix
                else:
                    q[idx] -= 0.5 * fix
                    q[idx - 1] += 0.5 * fix
        return q

    def project(self, q, anim, length, piv, pull, hits=None):
        """Follow the leader, root to tip one member index at a time: each tail pulled toward where
        its animation points it from its parent's new place (`pull`: the Stiffness share), kept in
        its cone, put on its length from that place, then pushed out of the colliders (`hits`: the
        moment's colliders) and put on its length again, `PASSES` times - its parent fixed by then,
        so a push the length takes back is pushed again. (pos, dirs, the joints that touched,
        their surfaces' normals)."""
        pos = np.empty_like(q)
        dirs = np.empty_like(q)
        touched = np.zeros(self.J, bool)
        normals = np.zeros((self.J, 3))
        for m, idx in enumerate(self.by_member):
            if m == 0:
                above = piv[idx]
                goal = anim[idx]
            else:
                above = pos[idx - 1]
                goal = turned(anim[idx], anim[idx - 1], dirs[idx - 1])
            point = q[idx]
            point = point + (above + goal * length[idx, None] - point) * pull[idx, None]
            d = _unit(point - above)
            if not self.no_limit:
                d = clamp_cone(d, goal, self.limit[idx])
            p = above + d * length[idx, None]
            if hits is not None:
                ca, cb, cr, cn, active = hits
                rows = np.arange(len(idx))
                for _pass in range(PASSES):
                    depth, normal, near = self._depths(p, self.radius[idx], ca, cb, cr, cn)
                    depth = np.where(active[idx], depth, np.inf)
                    pick = np.argmin(depth, axis=1)
                    deepest = depth[rows, pick]
                    touching = deepest < -1e-9
                    if not touching.any():
                        break
                    n = normal[rows, pick]
                    touched[idx[touching]] = True
                    normals[idx[touching]] = n[touching]
                    deepest = np.where(touching, deepest, 0.0)
                    onto = self._onto(p, above, length[idx], self.radius[idx], near[rows, pick], n,
                                      deepest, self.plane[pick])
                    p = np.where(touching[:, None], onto, p)
                    d = _unit(p - above)
                    if not self.no_limit:
                        d = clamp_cone(d, goal, self.limit[idx])
                    p = above + d * length[idx, None]
            dirs[idx] = d
            pos[idx] = p
        return pos, dirs, touched, normals

    def substep(self, state, fa, fb, s0, s1, t):
        p, prev = state
        piv = self._at(self.piv, fa, fb, s1)
        length = self._at(self.length, fa, fb, s1)
        anim = _unit(self._at(self.tail, fa, fb, s1) - piv)
        moved = self._at(self.carrier, fa, fb, s1) - self._at(self.carrier, fa, fb, s0)
        velocity = (p - prev) * self.keep[:, None]
        base = p + self.inertia[:, None] * moved
        accel = np.zeros((self.J, 3))
        accel[:, 1] = -G * self.gravity
        if self.wind is not None:
            gust, direction = self._wind_at(t, fa, fb, s1)
            bone = _unit(base - self.parents_of(base, piv))
            exposure = 1.0 - np.abs(bone @ direction)
            accel = accel + gust * exposure[:, None]
        q = base + velocity + accel * (self.dt * self.dt)
        q = self.relax(q, length, piv)
        hits = None
        if self.K:
            enabled = self.enabled[fb] if s1 > 0.5 else self.enabled[fa]
            hits = (self._at(self.ca, fa, fb, s1), self._at(self.cb, fa, fb, s1),
                    self._at(self.cr, fa, fb, s1),
                    _unit(self._at(self.cn, fa, fb, s1)) * self.plane[:, None],
                    enabled[None] & ~self.ignored)
        pos, dirs, touched, normals = self.project(q, anim, length, piv, self.share, hits)
        back = base
        if touched.any():
            # friction: a tail on a surface keeps less of its slide along it
            slide = pos - back
            along = slide - normals * np.sum(slide * normals, axis=-1, keepdims=True)
            back = np.where(touched[:, None], back + along * self.friction[:, None], back)
        return (pos, back), dirs

    def start_state(self, frame=0):
        p = self.tail[frame].copy()
        return (p, p.copy()), self.dir[frame].copy()


def _run(prep):
    """Without a loop: the pre-roll holding the first frame, then the range. (dirs, pos) (T, J, 3)."""
    T, S, P = prep.frames_out, prep.substeps, prep.preroll
    sequence = [0] * P + list(range(T))
    dirs_out = np.empty((T, prep.J, 3))
    pos_out = np.empty((T, prep.J, 3))
    state, dirs = prep.start_state(0)
    if P == 0:
        dirs_out[0], pos_out[0] = dirs, state[0]
    for k in range(1, len(sequence)):
        fa, fb = sequence[k - 1], sequence[k]
        for s in range(1, S + 1):
            t = (k - 1 - P + s / float(S)) / prep.fps
            state, dirs = prep.substep(state, fa, fb, (s - 1) / float(S), s / float(S), t)
        if k >= P:
            dirs_out[sequence[k]] = dirs
            pos_out[sequence[k]] = state[0]
    return dirs_out, pos_out, {"cycles": 0, "settled": True}


def _run_loop(prep):
    """A loop: the cycle again and again from the animated pose until its start settles, the last
    cycle recorded and its seam spread over it."""
    T, S = prep.frames_out, prep.substeps
    state, dirs = prep.start_state(0)
    settled = False
    cycles = 0
    for cycle in range(MAX_CYCLES):
        cycles = cycle + 1
        p0, b0 = state[0].copy(), state[1].copy()
        dirs_out = np.empty((T, prep.J, 3))
        for f in range(T):
            dirs_out[f] = dirs
            for s in range(1, S + 1):
                t = (f + s / float(S)) / prep.fps
                state, dirs = prep.substep(state, f, f + 1, (s - 1) / float(S), s / float(S), t)
        p, back = state
        state = (p - prep.travel, back - prep.travel)
        moved = max(float(np.abs(state[0] - p0).max()), float(np.abs(state[1] - b0).max()))
        if cycles >= MIN_CYCLES and moved < SETTLE_CM:
            settled = True
            break
    miss = rotvec_between(dirs_out[0], dirs)                                     # (J, 3)
    shares = (np.arange(T) / float(T))[:, None, None]
    dirs_out = _unit(rotate_by(dirs_out, -miss[None] * shares))
    pos_out = np.empty_like(dirs_out)
    for f in range(T):
        pos_out[f] = prep.rebuild(dirs_out[f], prep.length[f], prep.piv[f])
    return dirs_out, pos_out, {"cycles": cycles, "settled": settled}


def simulate(chains, colliders=(), wind=None, fps=30.0, loop=False):
    """Every chain's new member frames, solved together: ([(n, T, 4, 4)], info).

    `chains` [ChainInput]; `colliders` [Collider]; `wind` a WindInput or None; `loop`: the frames are
    one cycle plus the next cycle's first, and the answer is that cycle, settled and closed. The
    substeps and pre-roll are the most any chain asks for. info: {"cycles", "settled", "ignored" -
    the joint-collider pairs left alone because the joint started inside}."""
    prep = _Prepared(chains, colliders, wind, fps, loop)
    dirs, pos, info = (_run_loop if loop else _run)(prep)
    info["ignored"] = int(prep.ignored.sum()) if prep.K else 0
    T = prep.frames_out
    turns = turn_between(prep.dir[:T], dirs)                                     # (T, J, 3, 3)
    outs = []
    for c, chain in enumerate(prep.chains):
        offset, m, n = prep.layout[c]
        f = np.asarray(chain.frames, float)[:, :T]
        new = f.copy()
        for i in range(n):
            joint = offset + min(i, m - 1)
            new[i, :, :3, :3] = np.einsum("tij,tjk->tik", f[i, :, :3, :3], turns[:, joint])
            if i > 0:
                new[i, :, 3, :3] = pos[:, offset + i - 1]
        outs.append(new)
    return outs, info
