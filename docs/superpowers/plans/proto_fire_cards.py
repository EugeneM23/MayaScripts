"""PROTOTYPE - character cards that catch fire under the mouse (2026-10-02).

The animator: «Когда навожу мышкой на карточку то хочу что бы на заднем фоне в
карточке загорался огонь летели искры и она немного увеличивалась в размере.
попробуй сделать визуальный прототип но в плагин пока не вставляй».

Nothing of the plugin is changed: this reads the shipped portraits and the
hub's colours (maya_hubstyle.TOKENS, maya_charlook's grid) and draws with the
same Qt (PySide6 6.8, QPainter) the hub's Characters grid uses, so what is seen
here is what the plugin could draw.

    mayapy proto_fire_cards.py                 a window on the desktop
    mayapy proto_fire_cards.py --frames DIR    a scripted hover, rendered
                                               offscreen to DIR (+ flipbook)

The effect, per card:
  - a heat field (64 x 72 cells, numpy) - fire rising from the card's bottom
    edge, tongues shaped by a cooling map that scrolls up with the flames,
    swayed by a slow wind - mapped through a palette and drawn additively,
    upscaled, BEHIND the portrait (the portraits carry alpha);
  - sparks: particles born in the flames, buoyant, turbulent, cooling from
    white-yellow to red; a burst when the card catches; a quarter of them fly
    in FRONT of the character; they leave the card and fly on over the grid;
  - the character lit by its fire: a warm rim on the silhouette's edge and
    firelight from below, flickering with the flames' own heat;
  - the card grows 7 % on a spring (a touch of overshoot), drawn over its
    neighbours, with an outer glow and a hot ring;
  - the mouse off: the source dies, the flames finish rising and burn out, the
    sparks live out their lives, the card settles back.
"""

import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
sys.path.insert(0, PLUGIN)

import maya_hubstyle                                          # noqa: E402

TOK = maya_hubstyle.TOKENS
PORTRAITS = os.path.join(PLUGIN, "assets", "character_portraits")

#  (key, label, kinds) - catalog.MODELS and kinds_of, without importing Maya
MODELS = [("Manny", "Manny", ("rig", "skeleton")),
          ("Creep", "Creep", ("rig", "skeleton")),
          ("Orc_D", "Orc D", ("rig",)),
          ("UE4_Mannequin", "UE4 Mannequin", ("skeleton",))]

GAP, NAME_H, RADIUS = 6, 18, 6          # maya_charlook's, logical px
SIZES = {"Hub": (72, 120), "Large": (150, 230)}   # (cell min, cell max)
GROW = 0.07                              # the hovered card grows by this
SIM_HZ = 80.0                            # heat-field steps a second

#  Palettes: (heat, (r, g, b), alpha). "ember" is the hub's accent family.
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
}
PER_CHARACTER = {"Manny": "ember", "Creep": "spectral", "Orc_D": "toxic",
                 "UE4_Mannequin": "ember"}


# ------------------------------------------------------------ palettes

def palette_rgba(name, t):
    """(r, g, b, a 0..1) of palette `name` at heat t, interpolated."""
    stops = PALETTES[name]
    t = min(1.0, max(0.0, t))
    for (t0, c0, a0), (t1, c1, a1) in zip(stops, stops[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            c = tuple(c0[i] + (c1[i] - c0[i]) * u for i in range(3))
            return c + (a0 + (a1 - a0) * u,)
    c, a = stops[-1][1], stops[-1][2]
    return tuple(c) + (a,)


def palette_lut(name):
    """256 x 4 uint8, premultiplied B G R A (QImage ARGB32_Premultiplied)."""
    lut = np.zeros((256, 4), np.uint8)
    for i in range(256):
        r, g, b, a = palette_rgba(name, i / 255.0)
        lut[i] = (int(b * a), int(g * a), int(r * a), int(255 * a))
    return lut


def blur_wrap(a, n=1):
    for _ in range(n):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0)
             + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5.0
    return a


# ---------------------------------------------------------------- fire

class Fire(object):
    """The heat field: rows top to bottom, the source the bottom row."""

    COLS, ROWS = 80, 90

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        c, r = self.COLS, self.ROWS
        self.heat = np.zeros((r, c), np.float32)
        cmap = self.rng.random((r * 3, c)).astype(np.float32)
        cmap = blur_wrap(cmap, 3)
        cmap = (cmap - cmap.min()) / (cmap.max() - cmap.min())
        self.cmap = (cmap ** 2.0).astype(np.float32)
        self.offset = 0
        self.src = self.rng.random(c).astype(np.float32)
        self.t = 0.0
        x = np.linspace(-1.0, 1.0, c, dtype=np.float32)
        self.taper = (0.72 + 0.28 * np.cos(x * math.pi * 0.5)).astype(
            np.float32)
        self.rows = np.arange(r - 1)
        #  more cooling toward the top: the tongues taper and die there
        y = np.linspace(0.0, 1.0, r - 1, dtype=np.float32)[:, None]
        self.lid = (0.012 * (1.0 - y) ** 2).astype(np.float32)
        self.buf = None

    def step(self, power):
        h = self.heat
        self.t += 1.0 / SIM_HZ
        # the source: per-column noise, smoothed in time and across
        self.src += (self.rng.random(self.COLS).astype(np.float32)
                     - self.src) * 0.35
        s = self.src
        for _ in range(2):
            s = (np.roll(s, 1) + 2 * s + np.roll(s, -1)) * 0.25
        src = power * self.taper * np.clip(0.62 + 0.62 * s, 0.0, 1.15)
        # rise one row, sway, diffuse, cool by the map scrolling with it
        b1 = h[1:]
        b2 = np.concatenate([h[2:], h[-1:]], 0)
        left = np.concatenate([b1[:, :1], b1[:, :-1]], 1)
        right = np.concatenate([b1[:, 1:], b1[:, -1:]], 1)
        wind = 0.09 * math.sin(self.t * 1.3) + 0.05 * math.sin(self.t * 3.7)
        avg = (b1 * 0.36 + left * (0.17 + wind) + right * (0.17 - wind)
               + b2 * 0.30)
        # half of each cell from ONE random neighbour below (the classic
        # "fire" trick): flickering, ragged tongue edges instead of a blur
        pick = self.rng.integers(0, 3, b1.shape)
        ragged = np.where(pick == 0, left, np.where(pick == 1, b1, right))
        avg = avg * 0.55 + ragged * 0.45
        cool = self.cmap[(self.rows + self.offset) % self.cmap.shape[0]]
        noise = self.rng.random(b1.shape, dtype=np.float32) * 0.008
        h[:-1] = np.clip(avg - (0.032 * cool + self.lid + noise),
                         0.0, 1.2)
        h[-1] = src
        self.offset = (self.offset + 1) % self.cmap.shape[0]

    def warmth(self):
        """How hot the fire is right now, 0..1 (the light it throws)."""
        return float(min(1.0, self.heat[-20:].mean() * 1.7))

    def cold(self):
        return float(self.heat.max()) < 0.01

    def image(self, QtGui, lut, width, height):
        """The field at `width` x `height`: the HEAT is interpolated and the
        palette applied after, so the flames keep crisp edges at any size."""
        width, height = max(2, int(width)), max(2, int(height))
        key = (width, height)
        if getattr(self, "_grid_key", None) != key:
            xs = np.linspace(0, self.COLS - 1, width, dtype=np.float32)
            ys = np.linspace(0, self.ROWS - 1, height, dtype=np.float32)
            x0 = np.floor(xs).astype(np.int32)
            y0 = np.floor(ys).astype(np.int32)
            self._g = (x0, np.minimum(x0 + 1, self.COLS - 1), xs - x0,
                       y0, np.minimum(y0 + 1, self.ROWS - 1),
                       (ys - y0)[:, None])
            self._grid_key = key
        x0, x1, wx, y0, y1, wy = self._g
        h = self.heat
        top = h[y0][:, x0] * (1 - wx) + h[y0][:, x1] * wx
        bot = h[y1][:, x0] * (1 - wx) + h[y1][:, x1] * wx
        field = top * (1 - wy) + bot * wy
        idx = np.clip(field * 255.0, 0, 255).astype(np.uint8)
        self.buf = np.ascontiguousarray(lut[idx])
        return QtGui.QImage(self.buf.data, width, height, width * 4,
                            QtGui.QImage.Format_ARGB32_Premultiplied)


# -------------------------------------------------------------- sparks

class Sparks(object):
    """Particles in card units (0..1, y down)."""

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
        self.pos = np.concatenate([self.pos, np.stack([x, y], 1)
                                   .astype(np.float32)])
        self.vel = np.concatenate([self.vel, np.stack([vx, vy], 1)
                                   .astype(np.float32)])
        self.age = np.concatenate([self.age, np.zeros(n, np.float32)])
        self.life = np.concatenate([self.life, g.uniform(
            0.6, 1.25 if burst else 1.6, n).astype(np.float32)])
        self.size = np.concatenate([self.size, g.uniform(
            0.016, 0.034, n).astype(np.float32)])
        self.phase = np.concatenate([self.phase, g.uniform(
            0, 2 * math.pi, n).astype(np.float32)])
        self.front = np.concatenate([self.front, g.random(n) < 0.25])

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
            for name in ("pos", "vel", "age", "life", "size", "phase",
                         "front"):
                setattr(self, name, getattr(self, name)[keep])
        if not len(self.age):
            return
        sway = np.sin(self.t * 7.0 + self.phase) * 0.9
        jitter = self.rng.normal(0.0, 0.6, len(self.age))
        self.vel[:, 0] += (sway + jitter) * dt * 0.6
        self.vel[:, 1] -= 0.10 * dt                      # buoyancy
        self.vel *= math.exp(-0.9 * dt)                  # air
        self.pos += self.vel * dt

    def alive(self):
        return bool(len(self.age))


# --------------------------------------------------------------- a card

class CardFx(object):
    def __init__(self, key, seed):
        self.key = key
        self.fire = Fire(seed)
        self.sparks = Sparks(seed + 101)
        self.hover = False
        self.power = 0.0
        self.grow, self.grow_v = 0.0, 0.0
        self.flash = 0.0
        self.warm = 0.0
        self.acc = 0.0

    def set_hover(self, on):
        if on and not self.hover:
            self.sparks.spawn(24, burst=True)
            self.flash = 1.0
        self.hover = on

    def step(self, dt):
        target = 1.0 if self.hover else 0.0
        rate = 6.0 if self.hover else 9.0
        self.power += (target - self.power) * (1.0 - math.exp(-rate * dt))
        if self.power < 1e-3 and not self.hover:
            self.power = 0.0
        # the grow: a spring, a little under critical
        k, zeta = 300.0, 0.55
        c = 2.0 * zeta * math.sqrt(k)
        self.grow_v += (k * (target - self.grow) - c * self.grow_v) * dt
        self.grow += self.grow_v * dt
        self.acc += dt
        steps = 0
        while self.acc >= 1.0 / SIM_HZ and steps < 6:
            self.fire.step(self.power + 0.35 * self.flash)
            self.acc -= 1.0 / SIM_HZ
            steps += 1
        self.sparks.step(dt, 30.0 * self.power)
        self.flash *= math.exp(-5.0 * dt)
        self.warm = self.fire.warmth()

    def active(self):
        return (self.hover or self.power > 0 or not self.fire.cold()
                or self.sparks.alive() or abs(self.grow) > 1e-3
                or abs(self.grow_v) > 1e-3)


# ------------------------------------------------------------------ Qt

def build(QtCore, QtGui, QtWidgets):
    Qt = QtCore.Qt
    Plus = QtGui.QPainter.CompositionMode_Plus

    def qc(name, alpha=255):
        c = QtGui.QColor(TOK[name])
        c.setAlpha(alpha)
        return c

    def mix(a, b, u):
        u = min(1.0, max(0.0, u))
        return QtGui.QColor(
            int(a.red() + (b.red() - a.red()) * u),
            int(a.green() + (b.green() - a.green()) * u),
            int(a.blue() + (b.blue() - a.blue()) * u),
            int(a.alpha() + (b.alpha() - a.alpha()) * u))

    def pal(name, t, alpha=1.0):
        r, g, b, a = palette_rgba(name, t)
        return QtGui.QColor(int(r), int(g), int(b),
                            int(255 * min(1.0, a * alpha)))

    def sprite(name, t):
        size = 64
        img = QtGui.QImage(size, size,
                           QtGui.QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        g = QtGui.QRadialGradient(size / 2.0, size / 2.0, size / 2.0)
        g.setColorAt(0.0, pal(name, min(1.0, t + 0.2)))
        g.setColorAt(0.16, pal(name, t))
        g.setColorAt(0.42, pal(name, t - 0.2, 0.32))
        g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p = QtGui.QPainter(img)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(0, 0, size, size)
        p.end()
        return img

    class Looks(object):
        """What a palette draws with, made once."""

        def __init__(self, name):
            self.name = name
            self.lut = palette_lut(name)
            self.sprites = [sprite(name, t) for t in (0.62, 0.78, 0.95)]
            self.rim = pal(name, 0.84)
            self.light = pal(name, 0.50)
            self.ring = pal(name, 0.78)
            self.glow = pal(name, 0.50)
            r, g, b, _a = palette_rgba(name, 0.20)
            self.bg_hot = QtGui.QColor(int(r * 0.30 + 16), int(g * 0.30 + 14),
                                       int(b * 0.30 + 15))
            self.base = pal(name, 0.34)

    LOOKS = {}

    def looks(name):
        if name not in LOOKS:
            LOOKS[name] = Looks(name)
        return LOOKS[name]

    def lit_images(pixmap, side, look):
        """(shade, rim, firelight) for a portrait drawn `side` px square, in the
        palette's colours: the rim is the inside of the silhouette's edge,
        the firelight the silhouette lit from below."""
        img = pixmap.toImage().scaled(
            side, side, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        ).convertToFormat(QtGui.QImage.Format_ARGB32)
        ptr = img.constBits()
        arr = np.frombuffer(ptr, np.uint8).reshape(side, img.bytesPerLine())
        alpha = arr[:, :side * 4].reshape(side, side, 4)[:, :, 3].astype(
            np.float32) / 255.0
        radius = max(1, int(side * 0.018))
        blurred = alpha.copy()
        for _ in range(3):                       # a box blur, three times
            #  "edge": where the body meets the picture's frame is no edge
            pad = np.pad(blurred, radius, mode="edge")
            cs = np.cumsum(np.cumsum(pad, 0), 1)
            cs = np.pad(cs, ((1, 0), (1, 0)))
            n = 2 * radius + 1
            blurred = (cs[n:, n:] - cs[:-n, n:] - cs[n:, :-n]
                       + cs[:-n, :-n]) / float(n * n)
        rim = np.clip((alpha - blurred) * 2.6, 0.0, 1.0) * alpha
        # the rim stronger toward the top and the sides (backlight)
        yy = np.linspace(0.0, 1.0, side, dtype=np.float32)[:, None]
        rim *= (1.15 - 0.55 * yy)
        light = alpha * np.clip(1.3 * yy - 0.45, 0.0, 1.0) ** 1.8

        def tinted(mask, colour):
            out = np.zeros((side, side, 4), np.uint8)
            m = np.clip(mask, 0.0, 1.0)
            out[:, :, 0] = (colour.blue() * m).astype(np.uint8)
            out[:, :, 1] = (colour.green() * m).astype(np.uint8)
            out[:, :, 2] = (colour.red() * m).astype(np.uint8)
            out[:, :, 3] = (255 * m).astype(np.uint8)
            q = QtGui.QImage(out.data, side, side, side * 4,
                             QtGui.QImage.Format_ARGB32_Premultiplied)
            return q.copy()

        return (tinted(alpha, QtGui.QColor(0, 0, 0)), tinted(rim, look.rim),
                tinted(light, look.light))

    class Grid(QtWidgets.QWidget):
        def __init__(self, k, parent=None):
            QtWidgets.QWidget.__init__(self, parent)
            self.k = k
            self.kind = "rig"
            self.selected = "Manny"
            self.size_mode = "Hub"
            self.fire_mode = "Hub orange"
            self.pixmaps = {}
            for key, _label, _kinds in MODELS:
                path = os.path.join(PORTRAITS, key + ".png")
                if os.path.isfile(path):
                    self.pixmaps[key] = QtGui.QPixmap(path)
            self.fx = {key: CardFx(key, 7 + 31 * i)
                       for i, (key, _l, _k) in enumerate(MODELS)}
            self.hover = None
            self.lit_cache = {}
            self.paint_ms = 0.0
            self.on_stats = None
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(16)
            self.timer.timeout.connect(self.tick)
            self.clock = time.perf_counter()
            self.setMouseTracking(True)
            self.setCursor(Qt.PointingHandCursor)

        # ------------------------------------------------- layout
        def pads(self, cell):
            return (int(cell * 0.04), int(cell * 0.22), int(cell * 0.05))

        def layout_rects(self, width=None):
            k = self.k
            width = self.width() if width is None else width
            low, high = SIZES[self.size_mode]
            gap, name = GAP * k, NAME_H * k
            count = len(MODELS)
            side, top, bottom = self.pads(high * k)
            inner = max(1.0, width - 2 * side)
            cols = max(1, min(count, int((inner + gap) // (low * k + gap))))
            cell = max(1.0, min(high * k, (inner - gap * (cols - 1)) / cols))
            side, top, bottom = self.pads(cell)
            used = cols * cell + (cols - 1) * gap
            left = (width - used) / 2.0
            rects = []
            for i in range(count):
                row, col = divmod(i, cols)
                rects.append(QtCore.QRectF(left + col * (cell + gap),
                                           top + row * (cell + name + gap),
                                           cell, cell))
            rows = int(math.ceil(count / float(cols)))
            height = int(top + rows * (cell + name) + (rows - 1) * gap
                         + bottom)
            return rects, height

        def resizeEvent(self, event):                        # noqa: N802
            want = self.layout_rects(event.size().width())[1]
            if self.height() != want:
                self.setFixedHeight(want)
            QtWidgets.QWidget.resizeEvent(self, event)

        def refit(self):
            self.setFixedHeight(self.layout_rects()[1])
            self.lit_cache.clear()
            self.update()

        def available(self, key):
            return self.kind in dict((m[0], m[2]) for m in MODELS)[key]

        def model_at(self, x, y):
            rects, _h = self.layout_rects()
            for (key, _l, _k), r in zip(MODELS, rects):
                tile = r.adjusted(0, 0, 0, NAME_H * self.k)
                if tile.contains(QtCore.QPointF(x, y)):
                    return key
            return None

        # ------------------------------------------------ the loop
        def set_hover(self, key):
            if key is not None and not self.available(key):
                key = None
            if key == self.hover:
                return
            self.hover = key
            for k_, fx in self.fx.items():
                fx.set_hover(k_ == key)
            self.wake()

        def wake(self):
            if not self.timer.isActive():
                self.clock = time.perf_counter()
                self.timer.start()

        def advance(self, dt):
            for fx in self.fx.values():
                if fx.active():
                    fx.step(dt)

        def tick(self):
            now = time.perf_counter()
            dt = min(0.05, now - self.clock)
            self.clock = now
            t0 = time.perf_counter()
            self.advance(dt)
            self.sim_ms = (time.perf_counter() - t0) * 1000.0
            if not any(fx.active() for fx in self.fx.values()):
                self.timer.stop()
            self.update()

        # ----------------------------------------------- the mouse
        def mouseMoveEvent(self, event):                     # noqa: N802
            pos = event.position()
            self.set_hover(self.model_at(pos.x(), pos.y()))

        def leaveEvent(self, _event):                        # noqa: N802
            self.set_hover(None)

        def mousePressEvent(self, event):                    # noqa: N802
            pos = event.position()
            key = self.model_at(pos.x(), pos.y())
            if key and self.available(key):
                self.selected = key
                self.fx[key].sparks.spawn(30, burst=True)
                self.fx[key].flash = 1.0
                self.wake()
                self.update()

        # ----------------------------------------------- painting
        def palette_for(self, key):
            if self.fire_mode == "Per character":
                return PER_CHARACTER[key]
            return "ember"

        def lit_for(self, key, side, look):
            cache_key = (key, side, look.name)
            if cache_key not in self.lit_cache:
                pixmap = self.pixmaps.get(key)
                if pixmap is None or pixmap.isNull():
                    return None
                self.lit_cache[cache_key] = lit_images(pixmap, side, look)
            return self.lit_cache[cache_key]

        def draw_sparks(self, p, box, fx, look, front):
            s = fx.sparks
            if not len(s.age):
                return
            side = box.width()
            p.setCompositionMode(Plus)
            for i in range(len(s.age)):
                if bool(s.front[i]) != front:
                    continue
                left = 1.0 - s.age[i] / s.life[i]
                twinkle = 0.72 + 0.28 * math.sin(s.t * 26.0 + s.phase[i])
                alpha = min(1.0, left * 2.6) * twinkle
                x = box.left() + s.pos[i, 0] * side
                y = box.top() + s.pos[i, 1] * side
                d = side * s.size[i] * (0.55 + 0.45 * left)
                if front:
                    d *= 0.8
                img = look.sprites[2 if left > 0.66 else
                                   (1 if left > 0.33 else 0)]
                # a short streak: where it was a moment ago
                vx = s.vel[i, 0] * side * 0.05
                vy = s.vel[i, 1] * side * 0.05
                head = QtCore.QPointF(x, y)
                tail = QtCore.QPointF(x - vx, y - vy)
                grad = QtGui.QLinearGradient(head, tail)
                grad.setColorAt(0.0, pal(look.name, 0.5 + 0.4 * left,
                                         0.65 * alpha))
                grad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
                pen = QtGui.QPen(QtGui.QBrush(grad), max(1.0, d * 0.28))
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.drawLine(head, tail)
                p.setOpacity(alpha)
                p.drawImage(QtCore.QRectF(x - d, y - d, 2 * d, 2 * d), img)
                p.setOpacity(1.0)
            p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)

        def paint_card(self, p, key, label, box, fx):
            k = self.k
            radius = RADIUS * k
            look = looks(self.palette_for(key))
            available = self.available(key)
            selected = key == self.selected
            hot = fx.power
            heat = fx.warm
            grow = 1.0 + GROW * fx.grow
            centre = box.center()
            p.save()
            p.translate(centre)
            p.scale(grow, grow)
            p.translate(-centre)
            shape = QtGui.QPainterPath()
            shape.addRoundedRect(box, radius, radius)

            # the outer glow, behind the card
            glow_a = 0.55 * hot + 0.35 * heat + 0.3 * fx.flash
            if glow_a > 0.01:
                rings = 9
                step = 1.6 * k
                p.setBrush(Qt.NoBrush)
                for i in range(rings, 0, -1):
                    c = QtGui.QColor(look.glow)
                    c.setAlphaF(min(1.0, glow_a * 0.22
                                    * (1.0 - (i - 1) / float(rings)) ** 1.6))
                    p.setPen(QtGui.QPen(c, step * 1.4))
                    grow_r = box.adjusted(-i * step, -i * step,
                                          i * step, i * step)
                    p.drawRoundedRect(grow_r, radius + i * step,
                                      radius + i * step)

            # the face
            if selected:
                base = qc("card_active")
            elif self.hover == key and available:
                base = qc("hover")
            else:
                base = qc("field")
            p.fillPath(shape, mix(base, look.bg_hot,
                                  min(1.0, 0.35 * hot + 0.75 * heat)))

            pixmap = self.pixmaps.get(key)
            side = int(round(box.width()))
            p.save()
            p.setClipPath(shape)
            if hot > 0.002 or heat > 0.002:
                # the embers' glow at the bottom
                g = QtGui.QRadialGradient(
                    QtCore.QPointF(centre.x(), box.bottom() + box.height()
                                   * 0.15), box.width() * 0.95)
                c = QtGui.QColor(look.base)
                c.setAlphaF(min(1.0, 0.30 * heat + 0.20 * fx.flash))
                g.setColorAt(0.0, c)
                g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
                # the top falls into darkness: depth behind the fire
                v = QtGui.QLinearGradient(box.topLeft(), box.bottomLeft())
                v.setColorAt(0.0, QtGui.QColor(0, 0, 0, int(150 * hot)))
                v.setColorAt(0.6, QtGui.QColor(0, 0, 0, 0))
                p.fillRect(box, QtGui.QBrush(v))
                p.setCompositionMode(Plus)
                p.fillRect(box, QtGui.QBrush(g))
                # the flames
                p.drawImage(box.adjusted(-box.width() * 0.03, 0,
                                         box.width() * 0.03,
                                         box.height() * 0.02),
                            fx.fire.image(QtGui, look.lut,
                                          box.width() * 1.06,
                                          box.height() * 1.02))
                p.setCompositionMode(
                    QtGui.QPainter.CompositionMode_SourceOver)
                self.draw_sparks(p, box, fx, look, front=False)
            p.setOpacity(0.28 if not available else 1.0)
            if pixmap is not None and not pixmap.isNull():
                p.drawPixmap(box, pixmap, QtCore.QRectF(pixmap.rect()))
            p.setOpacity(1.0)
            if available and (hot > 0.002 or heat > 0.002):
                lit = self.lit_for(key, side, look)
                if lit:
                    shade, rim, light = lit
                    flicker = 0.82 + 0.18 * math.sin(fx.fire.t * 17.0) \
                        * math.sin(fx.fire.t * 5.3)
                    #  backlit: the body a little darker, its edge lit
                    p.setOpacity(0.30 * hot)
                    p.drawImage(box, shade)
                    p.setCompositionMode(Plus)
                    p.setOpacity(min(1.0, (0.20 + 0.60 * heat) * hot
                                     * flicker))
                    p.drawImage(box, rim)
                    p.setOpacity(min(1.0, 0.26 * heat * flicker
                                     + 0.18 * fx.flash))
                    p.drawImage(box, light)
                    p.setOpacity(1.0)
                    p.setCompositionMode(
                        QtGui.QPainter.CompositionMode_SourceOver)
                self.draw_sparks(p, box, fx, look, front=True)
            p.restore()

            # the ring
            if selected:
                ring, width = qc("accent"), max(1.5, 2 * k)
            elif self.hover == key and available:
                ring, width = qc("text2"), max(1.0, k)
            else:
                ring, width = qc("line"), max(1.0, k)
            if hot > 0.01:
                hot_ring = QtGui.QColor(look.ring)
                ring = mix(ring, hot_ring, min(1.0, hot * 0.6 + heat * 0.5))
                width = max(width, (1.0 + 1.2 * hot) * k)
            p.setPen(QtGui.QPen(ring, width))
            p.setBrush(Qt.NoBrush)
            half = width / 2.0
            p.drawRoundedRect(box.adjusted(half, half, -half, -half),
                              radius, radius)

            if not available:
                pad = 4 * k
                tag = QtCore.QRectF(box.left() + pad,
                                    box.bottom() - pad - 16 * k,
                                    box.width() - 2 * pad, 16 * k)
                p.setPen(Qt.NoPen)
                p.setBrush(qc("status"))
                p.drawRoundedRect(tag, 4 * k, 4 * k)
                f = QtGui.QFont()
                f.setPixelSize(int(10.5 * k))
                p.setFont(f)
                p.setPen(qc("faint"))
                p.drawText(tag, Qt.AlignCenter, "no " + self.kind)

            # the name
            f = QtGui.QFont()
            f.setPixelSize(int(11.5 * k))
            f.setBold(selected or hot > 0.5)
            p.setFont(f)
            if not available:
                colour = qc("faint")
            else:
                colour = mix(qc("text") if selected else qc("text2"),
                             look.ring, hot * 0.85)
            p.setPen(colour)
            name = QtCore.QRectF(box.left() - 20 * k, box.bottom(),
                                 box.width() + 40 * k, NAME_H * k)
            text = QtGui.QFontMetrics(f).elidedText(label, Qt.ElideRight,
                                                    int(box.width()))
            p.drawText(name, Qt.AlignHCenter | Qt.AlignVCenter, text)
            p.restore()
            return shape, grow, look

        def paintEvent(self, _event):                        # noqa: N802
            t0 = time.perf_counter()
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            rects, _h = self.layout_rects()
            order = sorted(range(len(MODELS)),
                           key=lambda i: self.fx[MODELS[i][0]].grow)
            for i in order:
                key, label, _kinds = MODELS[i]
                box = rects[i]
                fx = self.fx[key]
                shape, grow, look = self.paint_card(p, key, label, box, fx)
                # sparks that left their card fly on over the grid
                if fx.sparks.alive():
                    p.save()
                    centre = box.center()
                    p.translate(centre)
                    p.scale(grow, grow)
                    p.translate(-centre)
                    outside = QtGui.QPainterPath()
                    outside.addRect(QtCore.QRectF(-1e4, -1e4, 2e4, 2e4))
                    p.setClipPath(outside.subtracted(shape))
                    self.draw_sparks(p, box, fx, look, front=False)
                    self.draw_sparks(p, box, fx, look, front=True)
                    p.restore()
            p.end()
            self.paint_ms = (time.perf_counter() - t0) * 1000.0
            if self.on_stats:
                self.on_stats()

    class Window(QtWidgets.QWidget):
        def __init__(self, k):
            QtWidgets.QWidget.__init__(self)
            self.k = k
            self.setWindowTitle("Fire cards - prototype (not in the plugin)")
            px = lambda n: int(round(n * k))                  # noqa: E731
            self.setStyleSheet("""
                QWidget#root {{ background: {panel}; }}
                QFrame#card {{ background: {card}; border-radius: {r8}px; }}
                QLabel {{ color: {text}; font-size: {f}px; }}
                QLabel#heading {{ font-weight: bold; }}
                QLabel#muted {{ color: {muted}; font-size: {fs}px; }}
                QPushButton {{ background: {field}; color: {text2};
                    border: none; border-radius: {r6}px; padding: {p4}px;
                    font-size: {f}px; }}
                QPushButton:checked {{ background: {line}; color: {text}; }}
                QPushButton:hover:!checked {{ background: {field_hover}; }}
            """.format(r8=px(8), r6=px(6), p4=px(4), f=px(10.7),
                       fs=px(9.5), **TOK))
            self.setObjectName("root")
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(px(10), px(10), px(10), px(10))
            card = QtWidgets.QFrame()
            card.setObjectName("card")
            outer.addWidget(card)
            outer.addStretch(1)
            col = QtWidgets.QVBoxLayout(card)
            col.setContentsMargins(px(10), px(10), px(10), px(10))
            col.setSpacing(px(6))
            heading = QtWidgets.QLabel("Characters")
            heading.setObjectName("heading")
            col.addWidget(heading)
            self.grid = Grid(k)
            col.addLayout(self.segments(
                ["Rig", "Skeleton"], "Rig",
                lambda v: self.set_kind(v.lower())))
            col.addWidget(self.grid)
            row = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel("Tiles")
            label.setObjectName("muted")
            row.addWidget(label)
            row.addLayout(self.segments(["Hub", "Large"], "Hub",
                                        self.set_size), 1)
            col.addLayout(row)
            row = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel("Fire")
            label.setObjectName("muted")
            row.addWidget(label)
            row.addLayout(self.segments(["Hub orange", "Per character"],
                                        "Hub orange", self.set_fire), 1)
            col.addLayout(row)
            self.stats = QtWidgets.QLabel("")
            self.stats.setObjectName("muted")
            col.addWidget(self.stats)
            self.grid.on_stats = self.show_stats
            self.resize(px(380), px(440))

        def segments(self, names, current, changed):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(0)
            group = QtWidgets.QButtonGroup(self)
            group.setExclusive(True)
            for name in names:
                b = QtWidgets.QPushButton(name)
                b.setCheckable(True)
                b.setChecked(name == current)
                b.clicked.connect(lambda _c=False, n=name: changed(n))
                group.addButton(b)
                row.addWidget(b, 1)
            return row

        def set_kind(self, kind):
            self.grid.kind = kind
            self.grid.set_hover(None)
            self.grid.update()

        def set_size(self, mode):
            self.grid.size_mode = mode
            if mode == "Large":
                self.resize(max(self.width(), int(700 * self.k)),
                            self.height())
            self.grid.refit()

        def set_fire(self, mode):
            self.grid.fire_mode = mode
            self.grid.lit_cache.clear()
            self.grid.update()

        def show_stats(self):
            burning = sum(1 for fx in self.grid.fx.values() if fx.active())
            self.stats.setText(
                "paint {0:.1f} ms  ·  sim {1:.1f} ms  ·  {2} card(s) "
                "animating".format(self.grid.paint_ms,
                                   getattr(self.grid, "sim_ms", 0.0),
                                   burning))

    return Window


# --------------------------------------------------------------- main

def flipbook(frames_dir, names, fps):
    """An HTML page playing the rendered frames, for a look without Maya."""
    import base64
    data = []
    for name in names:
        with open(os.path.join(frames_dir, name), "rb") as f:
            data.append(base64.b64encode(f.read()).decode("ascii"))
    html = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fire Cards Prototype</title>
<style>
:root {{ --bg: #1f2023; --text: #c9cacf; --muted: #9a9ca3; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #1f2023; }} }}
:root[data-theme="dark"] {{ --bg: #1f2023; }}
body {{ margin: 0; background: var(--bg); color: var(--text);
  font: 13px system-ui, sans-serif; display: flex; flex-direction: column;
  align-items: center; gap: 10px; padding: 16px; }}
img {{ max-width: 100%; height: auto; image-rendering: auto; }}
p {{ color: var(--muted); margin: 0; text-align: center; }}
button {{ background: #2a2c30; color: var(--text); border: 1px solid #45474d;
  border-radius: 6px; padding: 4px 12px; cursor: pointer; }}
</style></head><body>
<img id="f" alt="fire cards">
<p>Rendered by the prototype's own Qt drawing (offscreen, 30 fps): the mouse
over Creep, then Orc D, then off the grid.</p>
<button id="b">Pause</button>
<script>
const F = {frames};
const img = document.getElementById('f');
let i = 0, run = true;
document.getElementById('b').onclick = e => {{ run = !run;
  e.target.textContent = run ? 'Pause' : 'Play'; }};
function show() {{ img.src = 'data:image/jpeg;base64,' + F[i]; }}
show();
setInterval(() => {{ if (run) {{ i = (i + 1) % F.length; show(); }} }},
  {ms});
</script></body></html>""".format(frames="[" + ",".join(
        '"%s"' % d for d in data) + "]", ms=int(1000 / fps))
    path = os.path.join(frames_dir, "fire_cards_flipbook.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main(argv):
    frames = None
    if "--frames" in argv:
        frames = argv[argv.index("--frames") + 1]
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    #  Maya draws in PHYSICAL pixels (trap 98); so does this
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    from PySide6 import QtCore, QtGui, QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(argv)
    if frames:
        k = 1.5
    else:
        k = max(1.0, app.primaryScreen().logicalDotsPerInch() / 96.0)
    Window = build(QtCore, QtGui, QtWidgets)
    win = Window(k)
    if not frames:
        win.show()
        return app.exec()

    os.makedirs(frames, exist_ok=True)
    if "--large" in argv:
        win.set_size("Large")
        win.resize(int(700 * k), int(560 * k))
    else:
        win.resize(int(380 * k), int(410 * k))
    win.show()
    app.processEvents()
    grid = win.grid
    grid.timer.stop()
    fps = 30
    script = {6: "Creep", 58: "Orc_D", 96: None}
    names = []
    for f in range(130):
        if f in script:
            grid.set_hover(script[f])
            grid.timer.stop()
        grid.advance(1.0 / fps)
        app.processEvents()
        name = "frame_%03d.jpg" % f
        win.grab().save(os.path.join(frames, name), "JPG", 90)
        names.append(name)
    print("frames:", len(names), "->", frames)
    print("flipbook:", flipbook(frames, names, fps))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
