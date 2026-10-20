"""maya_radial_rules - the radial menu's pure half (2026-10-15).

Spec: docs/superpowers/specs/2026-10-15-radial-menu-design.md.

COUNT slots on one ring (2..12, eight by default - `skeldarRadialCount`, 2026-10-16), clockwise
from north. A slot holds an ITEM: a section of the hub (`"section:<key>"`, its popup opens by the
cursor) or one of our hotkey rows (`"cmd:<row key>"`, the function runs). The slots are remembered
in one optionVar as a JSON list of MAX_SLOTS: the menu shows the first COUNT, so a smaller count
and back loses nothing.

Stdlib only: maya_radial (Qt + cmds) and the tests import it.
"""

import json
import math

SLOTS = 8                 # the default count
MIN_SLOTS = 2
MAX_SLOTS = 12
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
SLOTS_VAR = "skeldarRadialSlots"
COUNT_VAR = "skeldarRadialCount"

DEAD = 28                 # logical px: the centre where no slot is chosen
TAP_S = 0.25              # a release this soon after the press, in the centre, keeps the menu up
RADIUS = 112              # logical px: the ring the pills stand on (eight slots or fewer)

SECTION = "section:"
COMMAND = "cmd:"
CAMERA = "camera:"           # the Space menu's items (2026-10-20): a camera to look through

# The set a first press finds (the animator's ask: sections and single functions alike).
DEFAULTS = (
    "section:characters",      # N
    "section:tools",           # NE
    "cmd:tools.aim",           # E
    "cmd:tools.knot",          # SE
    "section:poses",           # S
    "cmd:tools.bake_layer",    # SW
    "section:connections",     # W
    "cmd:graph.overlay",       # NW
)

# The rows that wait for a second press: (module, the function asking whether it waits, the tool's
# name). The second press of the same row is the Finish.
TWO_STEP = {
    "tools.knot_offset": ("maya_tools.knots", "waiting", "Knot Offset"),
    "tools.aim": ("maya_tools.knots", "aims_waiting", "Aim"),
}

# What `release_action` answers.
RUN, KEEP, CLOSE = "run", "keep", "close"


def parse(item):
    """("section", key) / ("cmd", key) / (None, None) for an empty or unknown item."""
    item = item or ""
    if item.startswith(SECTION) and len(item) > len(SECTION):
        return "section", item[len(SECTION):]
    if item.startswith(COMMAND) and len(item) > len(COMMAND):
        return "cmd", item[len(COMMAND):]
    if item.startswith(CAMERA) and len(item) > len(CAMERA):
        return "camera", item[len(CAMERA):]
    return None, None


def section_item(key):
    return SECTION + key


def command_item(key):
    return COMMAND + key


def encode(slots):
    """The optionVar's text for MAX_SLOTS items."""
    return json.dumps(list(normalised(slots)))


def normalised(slots):
    """Exactly MAX_SLOTS items, each a string ("" for empty); anything else empty."""
    out = []
    for item in list(slots or [])[:MAX_SLOTS]:
        out.append(item if isinstance(item, str) and parse(item)[0] else "")
    return tuple(out + [""] * (MAX_SLOTS - len(out)))


def decode(text):
    """The MAX_SLOTS items the optionVar holds (an older list of eight padded); the defaults for
    no text or a broken one."""
    if not text:
        return normalised(DEFAULTS)
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return normalised(DEFAULTS)
    if not isinstance(value, list):
        return normalised(DEFAULTS)
    return normalised(value)


def clamp_count(value):
    """A slot count the menu can show: MIN_SLOTS..MAX_SLOTS, SLOTS for anything unreadable."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return SLOTS
    if value <= 0:
        return SLOTS
    return max(MIN_SLOTS, min(MAX_SLOTS, value))


def step(count=SLOTS):
    """Degrees between two slots."""
    return 360.0 / clamp_count(count)


def slot_at(dx, dy, dead=DEAD, count=SLOTS):
    """The slot the cursor offset (dx right, dy DOWN, screen pixels) points at, or None inside
    the dead zone. Slot 0 is north, then clockwise, each 360/count degrees wide."""
    if math.hypot(dx, dy) < dead:
        return None
    width = step(count)
    angle = math.degrees(math.atan2(dx, -dy)) % 360.0     # 0 north, clockwise
    return int(((angle + width / 2.0) % 360.0) // width) % clamp_count(count)


def ring_radius(count=SLOTS, radius=RADIUS):
    """The ring a count of slots stands on: RADIUS up to eight, wider past it so the pills keep
    the room between them that eight have."""
    return radius * max(1.0, clamp_count(count) / 8.0)


def slot_position(index, radius=RADIUS, count=SLOTS):
    """(dx, dy) of slot `index`'s centre from the menu's centre, dy down."""
    angle = math.radians(index * step(count))
    return (radius * math.sin(angle), -radius * math.cos(angle))


def pill_anchor(index, count=SLOTS):
    """Where a slot's label stands on its point, as the share of its width left of it: the east
    slots grow outward to the right (0), the west ones to the left (1), north and south are
    centred (0.5) - Maya's marking menu, so a long name never crosses the centre."""
    dx, _dy = slot_position(index, 1.0, count)
    if abs(dx) < 1e-6:
        return 0.5
    return 0.0 if dx > 0 else 1.0


def direction(index, count=SLOTS):
    """A slot's name in the editor: the compass point when it stands on one of the eight, else
    its angle clockwise from north ("30 deg")."""
    angle = (index * step(count)) % 360.0
    eighth = angle / 45.0
    if abs(eighth - round(eighth)) < 1e-6:
        return COMPASS[int(round(eighth)) % 8]
    return "{0:g} deg".format(round(angle, 1))


def release_action(slot, filled, elapsed, tap=TAP_S):
    """What a release of the menu's key does: RUN the slot pointed at (when it holds an item),
    KEEP the menu up for a click when the key was tapped in the centre, else CLOSE."""
    if slot is not None:
        return RUN if filled else CLOSE
    return KEEP if elapsed < tap else CLOSE


def finish_label(label):
    return "Finish " + label


# ------------------------------------------------------------------ the motion (2026-10-16)
#
# «элементы появлялись с анимацией из центра ... подсвечивались и увеличивались немного в размере
# ... скрывались анимацией как бы съезжаясь в центр». Times in milliseconds since the menu opened
# (or began to close); spec docs/superpowers/specs/2026-10-16-radial-menu-motion-design.md.

RING_MS = 160             # the ring and the centre grow
OPEN_MS = 200             # one pill out of the centre
OPEN_STEP_MS = 18         # the wave: slot i starts i steps after slot 0, clockwise from north
CLOSE_MS = 140            # one pill back into the centre
CLOSE_STEP_MS = 12        # the last slot first
HOVER_MS = 110            # the lift under the mouse, 0 -> 1 (and back)
FLASH_MS = 120            # a chosen pill flashes, then the menu closes and the item runs
HOVER_SCALE = 1.10        # a lit pill's size
START_SCALE = 0.3         # a pill's size at the centre
OVERSHOOT = 1.02          # ease_out_back's c1: a peak about 1.07


def _clamped(t):
    return min(1.0, max(0.0, float(t)))


def ease_out(t):
    t = _clamped(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in(t):
    t = _clamped(t)
    return t * t * t


def ease_out_back(t, c1=OVERSHOOT):
    """Past 1 a little, then back: the pill lands with a small bounce."""
    t = _clamped(t)
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def open_total(count=SLOTS):
    return OPEN_MS + (clamp_count(count) - 1) * OPEN_STEP_MS


def close_total(count=SLOTS):
    return CLOSE_MS + (clamp_count(count) - 1) * CLOSE_STEP_MS


def opened(elapsed, count=SLOTS):
    return elapsed >= max(open_total(count), RING_MS)


def closed(elapsed, count=SLOTS):
    return elapsed >= close_total(count)


def item_open(elapsed, index, count=SLOTS):
    """How far slot `index` is out of the centre `elapsed` ms after the menu opened (0..~1.07)."""
    return ease_out_back((elapsed - index * OPEN_STEP_MS) / float(OPEN_MS))


def item_close(elapsed, index, count=SLOTS):
    """How far slot `index` still is out `elapsed` ms after the menu began to close (1 -> 0)."""
    rank = clamp_count(count) - 1 - index
    return 1.0 - ease_in((elapsed - rank * CLOSE_STEP_MS) / float(CLOSE_MS))


def ring_open(elapsed):
    return ease_out(elapsed / float(RING_MS))


def ring_close(elapsed, count=SLOTS):
    return 1.0 - ease_in(elapsed / float(close_total(count)))


def pose(u):
    """(the share of the way from the centre, the size, the opacity) of a pill at progress `u`."""
    grown = max(0.0, u)
    return (u, START_SCALE + (1.0 - START_SCALE) * min(grown, 1.0), _clamped(1.4 * grown))


def approach(current, target, dt_ms, ms=HOVER_MS):
    """A lift moved toward `target` by `dt_ms` of the `ms` the whole way takes."""
    step = float(dt_ms) / float(ms)
    if target > current:
        return min(target, current + step)
    return max(target, current - step)


def lifted_scale(lift):
    return 1.0 + (HOVER_SCALE - 1.0) * ease_out(lift)


# ------------------------------------------------------- the camera menu (2026-10-20)
#
# «В мае при нажатии на пробел вылазит круговое меню. Давай его заменим на такое же как у нас ...
# Пока в этом меню давай сделаем только переключения между камерами». Variant B of the mockups:
# one ring of eight, Maya's four views on the compass points, the scene's own cameras on the
# diagonals (Camera Setup's first), an empty diagonal a dot.

CAMERA_SLOTS = 8
VIEW_SLOTS = (("top", 0), ("side", 2), ("front", 4), ("persp", 6))   # (startup camera, slot)
SCENE_SLOTS = (1, 3, 5, 7)
VIEW_LABELS = {"persp": "Persp", "top": "Top", "front": "Front", "side": "Side"}


def camera_item(path):
    return CAMERA + path


def camera_slots(views, scene):
    """The eight items: `views` {startup name: path} on the compass points, `scene` (paths, in
    order) on the diagonals, at most four; "" where nothing stands."""
    items = [""] * CAMERA_SLOTS
    for name, slot in VIEW_SLOTS:
        if views.get(name):
            items[slot] = camera_item(views[name])
    for slot, path in zip(SCENE_SLOTS, list(scene)[:len(SCENE_SLOTS)]):
        items[slot] = camera_item(path)
    return items


def scene_order(cameras, marked):
    """The scene's cameras in the menu's order: those Camera Setup made first, then by name."""
    marked = set(marked)
    return sorted(cameras, key=lambda c: (c not in marked, c.rsplit("|", 1)[-1].lower(), c))


def axes_seen(matrix):
    """The world axes as a camera sees them: {"x": (sx, sy), ...}, screen units (y down), from
    its 16-number world matrix (row vectors: row 0 its right, row 1 its up)."""
    right, up = matrix[0:3], matrix[4:7]
    def unit(v):
        n = math.sqrt(sum(c * c for c in v)) or 1.0
        return [c / n for c in v]
    right, up = unit(right), unit(up)
    out = {}
    for name, axis in (("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
        out[name] = (sum(a * b for a, b in zip(axis, right)),
                     -sum(a * b for a, b in zip(axis, up)))
    return out


def camera_release(slot, filled, elapsed, tap=TAP_S):
    """What letting Space go does: RUN the camera pointed at, TAP (Maya's single / four views)
    for a quick press in the centre, else CLOSE."""
    if slot is not None:
        return RUN if filled else CLOSE
    return TAP if elapsed < tap else CLOSE


TAP = "tap"
