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
