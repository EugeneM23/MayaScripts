"""The fire on the Characters cards, as numbers (2026-10-02).

The animator: «Когда навожу мышкой на карточку то хочу что бы на заднем фоне в
карточке загорался огонь летели искры и она немного увеличивалась в размере»,
and after the prototype: «У каждого персонажа свой цвет огня». This module is
the simulation and the colours; `maya_chargrid` paints what it says. numpy and
the stdlib only (a subprocess test pins it), fixed-step and seeded, so every
number is tested without Qt or Maya.

    PALETTES         heat -> colour per fire (catalog.Model.fire names one)
    palette_lut      256 premultiplied B G R A rows, what a QImage reads
    Fire             the heat field behind the character; field() is it at
                     a size, through a palette
    Sparks           particles in card units (0..1, y down)
    CardFx           one card's life: the hover, the power, the grow spring,
                     the flash
    lit_masks        a portrait's alpha -> (shade, rim, firelight)

Spec: docs/superpowers/specs/2026-10-02-character-card-fire-design.md
"""

import math

import numpy as np

GROW = 0.07                 # the burning card grows by this
SIM_HZ = 80.0               # the heat field's steps a second
CATCH_SPARKS = 24           # the burst when a card catches
CLICK_SPARKS = 30           # ... and when it is clicked
SPARK_RATE = 30.0           # sparks a second while it burns

#  Every character its own fire («У каждого персонажа свой цвет огня»), by
#  catalog.Model key. A model not here has none: the old hover. A new
#  character row wants a fire here (a test pins it).
FIRES = {"Manny": "ember", "Creep": "spectral", "Orc_D": "toxic",
         "UE4_Mannequin": "arcane",
         #  the unknown rig or skeleton (the «?» card) burns as Manny's does
         #  («сделаем так же как и карточка менни»; a black fire was tried
         #  first and dropped the same evening)
         "Auto": "ember"}


def fire_of(model):
    """The fire of catalog model `model` (a key), or "" for none."""
    return FIRES.get(model, "")


#  (heat, (r, g, b), alpha) stops; the low heats almost transparent, so the
#  flames keep edges. "ember" is the hub's accent family.
PALETTES = {
    "ember": [(0.00, (0, 0, 0), 0.0), (0.14, (80, 10, 4), 0.04),
              (0.24, (150, 28, 6), 0.55), (0.36, (214, 70, 18), 0.88),
              (0.52, (240, 128, 40), 1.0), (0.70, (252, 186, 84), 1.0),
              (0.86, (255, 226, 150), 1.0), (1.00, (255, 248, 224), 1.0)],
    "spectral": [(0.00, (0, 0, 0), 0.0), (0.14, (6, 12, 60), 0.04),
                 (0.24, (16, 46, 150), 0.55), (0.36, (34, 100, 222), 0.88),
                 (0.52, (64, 158, 250), 1.0), (0.70, (120, 206, 255), 1.0),
                 (0.86, (188, 236, 255), 1.0), (1.00, (240, 252, 255), 1.0)],
    "toxic": [(0.00, (0, 0, 0), 0.0), (0.14, (10, 40, 6), 0.04),
              (0.24, (30, 96, 12), 0.55), (0.36, (66, 160, 24), 0.88),
              (0.52, (116, 210, 44), 1.0), (0.70, (168, 238, 86), 1.0),
              (0.86, (214, 252, 150), 1.0), (1.00, (242, 255, 222), 1.0)],
    "arcane": [(0.00, (0, 0, 0), 0.0), (0.14, (40, 8, 60), 0.04),
               (0.24, (96, 20, 150), 0.55), (0.36, (150, 50, 220), 0.88),
               (0.52, (190, 100, 250), 1.0), (0.70, (220, 160, 255), 1.0),
               (0.86, (240, 210, 255), 1.0), (1.00, (252, 244, 255), 1.0)],
}


# ------------------------------------------------------------ palettes

def palette_rgba(name, t):
    """(r, g, b 0..255, alpha 0..1) of fire `name` at heat t (clamped)."""
    stops = PALETTES[name]
    t = min(1.0, max(0.0, float(t)))
    for (t0, c0, a0), (t1, c1, a1) in zip(stops, stops[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            colour = tuple(c0[i] + (c1[i] - c0[i]) * u for i in range(3))
            return colour + (a0 + (a1 - a0) * u,)
    colour, alpha = stops[-1][1], stops[-1][2]
    return tuple(float(c) for c in colour) + (alpha,)


def palette_lut(name):
    """256 x 4 uint8, premultiplied B G R A (QImage ARGB32_Premultiplied's
    memory order on a little-endian machine)."""
    lut = np.zeros((256, 4), np.uint8)
    for i in range(256):
        r, g, b, a = palette_rgba(name, i / 255.0)
        lut[i] = (int(b * a), int(g * a), int(r * a), int(round(255 * a)))
    return lut


def _blur_wrap(a, n=1):
    for _ in range(n):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0)
             + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5.0
    return a


# ---------------------------------------------------------------- fire

class Fire(object):
    """The heat field, rows top to bottom, its source the bottom row. Each
    step the heat rises a row, sways with a slow wind, takes half of each cell
    from one random neighbour below (ragged tongues), and cools by a map that
    scrolls up with it (the tongues keep their shapes) and more toward the
    top (they taper and die there)."""

    COLS, ROWS = 80, 90

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        cols, rows = self.COLS, self.ROWS
        self.heat = np.zeros((rows, cols), np.float32)
        cmap = self.rng.random((rows * 3, cols)).astype(np.float32)
        cmap = _blur_wrap(cmap, 3)
        cmap = (cmap - cmap.min()) / (cmap.max() - cmap.min())
        self.cmap = (cmap ** 2.0).astype(np.float32)
        self.offset = 0
        self.src = self.rng.random(cols).astype(np.float32)
        self.t = 0.0
        x = np.linspace(-1.0, 1.0, cols, dtype=np.float32)
        self.taper = (0.72 + 0.28 * np.cos(x * math.pi * 0.5)).astype(
            np.float32)
        self.rows = np.arange(rows - 1)
        y = np.linspace(0.0, 1.0, rows - 1, dtype=np.float32)[:, None]
        self.lid = (0.012 * (1.0 - y) ** 2).astype(np.float32)
        self._grid = None

    def step(self, power):
        h = self.heat
        self.t += 1.0 / SIM_HZ
        # the source: per-column noise, smoothed in time and across
        self.src += (self.rng.random(self.COLS).astype(np.float32)
                     - self.src) * 0.35
        s = self.src
        for _ in range(2):
            s = (np.roll(s, 1) + 2 * s + np.roll(s, -1)) * 0.25
        source = power * self.taper * np.clip(0.62 + 0.62 * s, 0.0, 1.15)
        below = h[1:]
        below2 = np.concatenate([h[2:], h[-1:]], 0)
        left = np.concatenate([below[:, :1], below[:, :-1]], 1)
        right = np.concatenate([below[:, 1:], below[:, -1:]], 1)
        wind = 0.09 * math.sin(self.t * 1.3) + 0.05 * math.sin(self.t * 3.7)
        avg = (below * 0.36 + left * (0.17 + wind) + right * (0.17 - wind)
               + below2 * 0.30)
        pick = self.rng.integers(0, 3, below.shape)
        ragged = np.where(pick == 0, left, np.where(pick == 1, below, right))
        avg = avg * 0.55 + ragged * 0.45
        cool = self.cmap[(self.rows + self.offset) % self.cmap.shape[0]]
        noise = self.rng.random(below.shape, dtype=np.float32) * 0.008
        h[:-1] = np.clip(avg - (0.032 * cool + self.lid + noise), 0.0, 1.2)
        h[-1] = source
        self.offset = (self.offset + 1) % self.cmap.shape[0]

    def warmth(self):
        """How hot the fire is right now, 0..1: the light it throws."""
        return float(min(1.0, self.heat[-20:].mean() * 1.7))

    def cold(self):
        return float(self.heat.max()) < 0.01

    def field(self, lut, width, height):
        """The field at `width` x `height` through `lut`: (height, width, 4)
        uint8, C-contiguous. The HEAT is interpolated and the palette applied
        after, so the flames keep crisp edges at any size."""
        width, height = max(2, int(width)), max(2, int(height))
        if self._grid is None or self._grid[0] != (width, height):
            xs = np.linspace(0, self.COLS - 1, width, dtype=np.float32)
            ys = np.linspace(0, self.ROWS - 1, height, dtype=np.float32)
            x0 = np.floor(xs).astype(np.int32)
            y0 = np.floor(ys).astype(np.int32)
            self._grid = ((width, height), x0,
                          np.minimum(x0 + 1, self.COLS - 1), xs - x0, y0,
                          np.minimum(y0 + 1, self.ROWS - 1),
                          (ys - y0)[:, None])
        _size, x0, x1, wx, y0, y1, wy = self._grid
        h = self.heat
        top = h[y0][:, x0] * (1 - wx) + h[y0][:, x1] * wx
        bottom = h[y1][:, x0] * (1 - wx) + h[y1][:, x1] * wx
        heat = top * (1 - wy) + bottom * wy
        index = np.clip(heat * 255.0, 0, 255).astype(np.uint8)
        return np.ascontiguousarray(lut[index])


# -------------------------------------------------------------- sparks

class Sparks(object):
    """Particles in card units (0..1, y down): born in the flames, buoyant,
    swaying, slowed by the air; a quarter fly in front of the character."""

    NAMES = ("pos", "vel", "age", "life", "size", "phase", "front")

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.pos = np.zeros((0, 2), np.float32)
        self.vel = np.zeros((0, 2), np.float32)
        self.age = np.zeros(0, np.float32)
        self.life = np.zeros(0, np.float32)
        self.size = np.zeros(0, np.float32)
        self.phase = np.zeros(0, np.float32)
        self.front = np.zeros(0, bool)
        self.carry = 0.0
        self.t = 0.0

    def spawn(self, n, burst=False):
        if n <= 0:
            return
        g = self.rng
        x = g.uniform(0.06, 0.94, n)
        y = g.uniform(0.86, 1.0, n) if burst else g.uniform(0.70, 1.0, n)
        if burst:
            vx, vy = g.uniform(-0.38, 0.38, n), -g.uniform(0.55, 1.35, n)
        else:
            vx, vy = g.uniform(-0.12, 0.12, n), -g.uniform(0.30, 0.80, n)
        add = dict(
            pos=np.stack([x, y], 1).astype(np.float32),
            vel=np.stack([vx, vy], 1).astype(np.float32),
            age=np.zeros(n, np.float32),
            life=g.uniform(0.6, 1.25 if burst else 1.6, n).astype(np.float32),
            size=g.uniform(0.016, 0.034, n).astype(np.float32),
            phase=g.uniform(0, 2 * math.pi, n).astype(np.float32),
            front=g.random(n) < 0.25)
        for name in self.NAMES:
            setattr(self, name, np.concatenate([getattr(self, name),
                                                add[name]]))

    def step(self, dt, rate):
        self.t += dt
        self.carry += rate * dt
        n = int(self.carry)
        self.carry -= n
        self.spawn(n)
        if not len(self.age):
            return
        self.age += dt
        keep = self.age < self.life
        if not keep.all():
            for name in self.NAMES:
                setattr(self, name, getattr(self, name)[keep])
        if not len(self.age):
            return
        sway = np.sin(self.t * 7.0 + self.phase) * 0.9
        jitter = self.rng.normal(0.0, 0.6, len(self.age))
        self.vel[:, 0] += ((sway + jitter) * dt * 0.6).astype(np.float32)
        self.vel[:, 1] -= 0.10 * dt                       # buoyancy
        self.vel *= math.exp(-0.9 * dt)                   # the air
        self.pos += self.vel * dt

    def alive(self):
        return bool(len(self.age))


# --------------------------------------------------------------- a card

class CardFx(object):
    """One card's fire: the hover lights it (`power` follows in ~0.2 s), the
    grow springs to 1 with a touch of overshoot, a flash on catching; the
    mouse off, the source dies and the rest burns out on its own."""

    STIFFNESS = 300.0
    DAMPING = 0.55          # of critical: a touch of overshoot

    def __init__(self, seed):
        self.fire = Fire(seed)
        self.sparks = Sparks(seed + 101)
        self.hover = False
        self.power = 0.0
        self.grow = 0.0
        self.grow_v = 0.0
        self.flash = 0.0
        self.warm = 0.0
        self._acc = 0.0

    def set_hover(self, on):
        if on and not self.hover:
            self.sparks.spawn(CATCH_SPARKS, burst=True)
            self.flash = 1.0
        self.hover = bool(on)

    def burst(self):
        """A click: more sparks and a flash."""
        self.sparks.spawn(CLICK_SPARKS, burst=True)
        self.flash = 1.0

    def step(self, dt):
        target = 1.0 if self.hover else 0.0
        rate = 6.0 if self.hover else 9.0
        self.power += (target - self.power) * (1.0 - math.exp(-rate * dt))
        if self.power < 1e-3 and not self.hover:
            self.power = 0.0
        damping = 2.0 * self.DAMPING * math.sqrt(self.STIFFNESS)
        self.grow_v += (self.STIFFNESS * (target - self.grow)
                        - damping * self.grow_v) * dt
        self.grow += self.grow_v * dt
        self._acc += dt
        steps = 0
        while self._acc >= 1.0 / SIM_HZ and steps < 6:
            self.fire.step(self.power + 0.35 * self.flash)
            self._acc -= 1.0 / SIM_HZ
            steps += 1
        if steps == 6:
            self._acc = 0.0
        self.sparks.step(dt, SPARK_RATE * self.power)
        self.flash *= math.exp(-5.0 * dt)
        if self.flash < 1e-3:
            self.flash = 0.0
        self.warm = self.fire.warmth()

    def shown_grow(self):
        """The grow as drawn: the spring may dip below rest, the card not."""
        return max(0.0, self.grow)

    def active(self):
        return bool(self.hover or self.power > 0 or self.flash > 0
                    or not self.fire.cold() or self.sparks.alive()
                    or abs(self.grow) > 1e-3 or abs(self.grow_v) > 1e-3)


# ---------------------------------------------------------------- light

def _box_blur(a, radius):
    """A box blur, the edges extended ("edge"): where the body meets the
    picture's frame is no edge."""
    pad = np.pad(a, radius, mode="edge")
    cs = np.cumsum(np.cumsum(pad, 0), 1)
    cs = np.pad(cs, ((1, 0), (1, 0)))
    n = 2 * radius + 1
    return (cs[n:, n:] - cs[:-n, n:] - cs[n:, :-n]
            + cs[:-n, :-n]) / float(n * n)


#  A portrait at least this opaque hides the fire behind it whole (the «?»
#  card's faint silhouette is 0.30): «чтобы огонь как и на других карточках
#  горел за силуэтом».
BODY_ALPHA = 0.25


def body_mask(alpha):
    """Where a portrait hides the fire behind it, 0..1: its silhouette as
    if it were opaque (alpha BODY_ALPHA and up), its edges still soft."""
    alpha = np.asarray(alpha, np.float32)
    return np.clip(alpha / BODY_ALPHA, 0.0, 1.0).astype(np.float32)


def lit_masks(alpha):
    """(shade, rim, light) float32 masks 0..1 from a portrait's alpha (a
    square float array): the silhouette (darkened, backlit), the inside of
    its edge (stronger toward the top), and the firelight from below."""
    alpha = np.asarray(alpha, np.float32)
    side = alpha.shape[0]
    radius = max(1, int(side * 0.018))
    blurred = alpha
    for _ in range(3):
        blurred = _box_blur(blurred, radius)
    rim = np.clip((alpha - blurred) * 2.6, 0.0, 1.0) * alpha
    yy = np.linspace(0.0, 1.0, side, dtype=np.float32)[:, None]
    rim = np.clip(rim * (1.15 - 0.55 * yy), 0.0, 1.0)
    light = alpha * np.clip(1.3 * yy - 0.45, 0.0, 1.0) ** 1.8
    return (alpha.copy(), rim.astype(np.float32),
            np.clip(light, 0.0, 1.0).astype(np.float32))
