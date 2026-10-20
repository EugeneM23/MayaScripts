"""Our Channel Box as plain values (stdlib only - a test pins it): how a value reads,
what a typed value means, a channel's state, the hairlines between groups, where each
part of a row stands, the selection a click makes, the virtual slider's step.

The motion numbers are the Time Bar's (maya_timebar.look, maya_timebar.bar).
Spec: docs/superpowers/specs/2026-10-18-channel-box-rows-design.md
"""

import math

from maya_timebar import look as _bar

# -- the Time Bar's motion (docs/interface-motion.md) --------------------------------
HOVER_MS = 110          # bar.HOVER_MS: a lift under the mouse
FLASH_MS = 120          # bar.FLASH_MS: a press
POP_MS = 200            # bar.POP_MS: a toggle
KEY_FADE_MS = 600       # bar.KEY_FADE_MS: a key the playhead reached
LIFT = 0.10             # bar.LIFT
SET_GLOW = 44           # bar.SET_GLOW: logical px, a key set's flash
EFFECT_MS = {"set": _bar.EFFECT_MS["set"], "delete": _bar.EFFECT_MS["delete"]}
FRAME_MS = 16
approach = _bar.approach
back_out = _bar.back_out
passed = _bar.passed
flash = _bar.flash
delete_plan = _bar.delete_plan
shards = _bar.shards
SHARD_SPEED, SHARD_FALL = _bar.SHARD_SPEED, _bar.SHARD_FALL

# -- colours that mean something (beside the hub's TOKENS) ---------------------------
BREAKDOWN = "#6fb7c9"
DRIVEN = "#7fa9e6"
MUTED = "#9b7a63"
RIM = "#fff1e2"

# -- the layout, logical px ----------------------------------------------------------
HEAD_H = 30             # the object, +N, the layer chip
ROW_H = 22
SECTION_H = 22
RULE_H = 7              # a hairline between groups, its room
PAD = 6                 # the canvas's inner margin left and right
MARK_W = 18             # the key cell's column
GAP = 6
VALUE_W = 84            # the value well
CELL_W, CELL_H = 7, 13  # the key cell itself
VALUE_H = 18

STATES = ("onkey", "onbd", "keyed", "driven", "locked", "plain")


def fmt(value, kind="double", precision=3, names=None):
    """A value as the box shows it: on / off, an enum's name, a number rounded to
    `precision` places with its trailing zeros dropped (never "-0")."""
    if value is None:
        return ""
    if kind == "bool":
        return "on" if value else "off"
    if kind == "enum":
        try:
            return names[int(value)]
        except (TypeError, IndexError, ValueError):
            return str(int(value))
    if kind in ("long", "short", "byte", "char"):
        return str(int(round(value)))
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    precision = max(0, min(10, int(precision)))
    if abs(v) < 0.5 * 10 ** (-precision):
        return "0"
    text = ("%." + str(precision) + "f") % v
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def typed(text, old, kind="double"):
    """What a typed entry sets, or None when it means nothing: a number, or relative
    to `old` - `+=5`, `-=2`, `*=2`, `/=4` (Maya's own Channel Box reads these); a
    bool also reads on / off / yes / no."""
    t = (text or "").strip().lower()
    if not t:
        return None
    if kind == "bool":
        if t in ("on", "yes", "true", "1"):
            return 1
        if t in ("off", "no", "false", "0"):
            return 0
    op = t[:2] if t[:2] in ("+=", "-=", "*=", "/=") else ""
    try:
        number = float(t[2:] if op else t)
    except ValueError:
        return None
    if not op:
        value = number
    else:
        base = float(old or 0.0)
        if op == "+=":
            value = base + number
        elif op == "-=":
            value = base - number
        elif op == "*=":
            value = base * number
        else:
            if number == 0:
                return None
            value = base / number
    if kind in ("bool", "long", "short", "byte", "char", "enum"):
        return int(round(value))
    return value


def state_of(channel):
    """(state, muted, changed) of a channel dict - its keys: locked, muted, source
    ('curve' / 'layer' / 'driven' / None), on_key, breakdown, keys, changed."""
    muted = bool(channel.get("muted"))
    changed = bool(channel.get("changed"))
    if channel.get("locked"):
        return "locked", muted, False
    source = channel.get("source")
    if source == "driven":
        return "driven", muted, False
    if source in ("curve", "layer") or channel.get("keys"):
        if channel.get("on_key"):
            return ("onbd" if channel.get("breakdown") else "onkey"), muted, changed
        return "keyed", muted, changed
    return "plain", muted, False


def group_of(attr):
    """The hairline group an attribute belongs to."""
    a = attr.lower()
    if a.startswith("translate"):
        return "t"
    if a.startswith("rotate") and not a.startswith("rotateorder") and not a.startswith("rotateaxis"):
        return "r"
    if a.startswith("scale"):
        return "s"
    if a == "visibility":
        return "v"
    return "c"


def rows(sections, opened=()):
    """The box's rows top down from `sections` - [{'key', 'kind' ('main' / 'shapes' /
    'inputs' / 'outputs'), 'label', 'channels': [channel]}]: the main section's
    channels first with a rule between groups, then each other section as a header
    and, when its key is in `opened`, its channels. Each row a dict: kind 'channel'
    (with its channel), 'rule' or 'section'."""
    out = []
    for section in sections:
        if section.get("kind") != "main":
            out.append({"kind": "section", "key": section["key"], "label": section.get("label", ""),
                        "title": section.get("title", ""), "open": section["key"] in opened})
            if section["key"] not in opened:
                continue
        last = None
        for channel in section.get("channels", []):
            g = group_of(channel.get("attr", ""))
            if last is not None and g != last and section.get("kind") == "main":
                out.append({"kind": "rule"})
            last = g
            out.append({"kind": "channel", "channel": channel, "section": section["key"]})
    return out


def layout(rows_, width, ui=1.0):
    """Each row's rects, physical px: [(y, h, parts)] with parts a dict of
    (x, y, w, h) - 'mark', 'name', 'value' for a channel, 'row' for all. Returns
    (placed, total height)."""
    ui = float(ui or 1.0)
    pad, gap = PAD * ui, GAP * ui
    placed, y = [], 2 * ui
    for row in rows_:
        h = (ROW_H if row["kind"] == "channel" else SECTION_H if row["kind"] == "section"
             else RULE_H) * ui
        parts = {"row": (pad * 0.5, y, width - pad, h)}
        if row["kind"] == "channel":
            mw, vw = MARK_W * ui, VALUE_W * ui
            vx = width - pad - vw
            parts["mark"] = (pad, y, mw, h)
            parts["value"] = (vx, y + (h - VALUE_H * ui) / 2.0, vw, VALUE_H * ui)
            nx = pad + mw + gap
            parts["name"] = (nx, y, max(0.0, vx - gap - nx), h)
        placed.append((y, h, parts))
        y += h
    return placed, y + 4 * ui


def cell_rect(mark, ui=1.0):
    """The key cell (x, y, w, h) centred in its mark column."""
    x, y, w, h = mark
    cw, ch = CELL_W * ui, CELL_H * ui
    return x + (w - cw) / 2.0, y + (h - ch) / 2.0, cw, ch


def hit(placed, rows_, x, y):
    """(index, part) under (x, y): part 'mark' / 'value' / 'name' / 'row' / 'section';
    (None, None) off every row."""
    for i, (ry, rh, parts) in enumerate(placed):
        if ry <= y < ry + rh:
            kind = rows_[i]["kind"]
            if kind == "section":
                return i, "section"
            if kind != "channel":
                return None, None
            for part in ("mark", "value", "name"):
                px, py, pw, ph = parts[part]
                if px <= x < px + pw:
                    return i, part
            return i, "row"
    return None, None


def select(order, selected, anchor, clicked, ctrl=False, shift=False):
    """(selected set, anchor) after a click on `clicked` (a channel key) among
    `order`: alone, Ctrl toggling it, Shift adding the run from the anchor."""
    selected = set(selected)
    if ctrl:
        if clicked in selected:
            selected.discard(clicked)
        else:
            selected.add(clicked)
        return selected, clicked
    if shift and anchor in order and clicked in order:
        a, b = order.index(anchor), order.index(clicked)
        lo, hi = min(a, b), max(a, b)
        selected.update(order[lo:hi + 1])
        return selected, anchor
    return {clicked}, clicked


def sweep(order, base, start, end):
    """The selection a drag down the rows from `start` to `end` (channel keys)
    leaves: the run between them, added to `base` (the selection Ctrl kept)."""
    selected = set(base)
    if start in order and end in order:
        a, b = order.index(start), order.index(end)
        selected.update(order[min(a, b):max(a, b) + 1])
    elif start in order:
        selected.add(start)
    return selected


TYPE_KEYS = "0123456789.-+=*/"


def starts_typing(text):
    """True when a key's text begins a value the way Maya's Channel Box takes it."""
    return bool(text) and len(text) == 1 and text in TYPE_KEYS


STEP = {"distance": 0.1, "angle": 1.0, "scale": 0.01, "number": 0.1, "int": 0.2}


def step_kind(attr, kind):
    """Which slider step an attribute takes."""
    a = attr.lower()
    if kind in ("long", "short", "byte", "char", "enum", "bool"):
        return "int"
    if kind == "doubleAngle" or a.startswith("rotate"):
        return "angle"
    if a.startswith("scale"):
        return "scale"
    if kind == "doubleLinear" or a.startswith("translate"):
        return "distance"
    return "number"


def per_px(attr, kind, speed=1.0, lo=None, hi=None):
    """How far one physical px of the virtual slider moves a value: Maya's channel
    speed times the kind's step, or a 200th of a bounded range."""
    speed = float(speed or 1.0)
    if lo is not None and hi is not None and hi > lo and kind not in ("bool", "enum"):
        return (hi - lo) / 200.0 * speed
    return STEP[step_kind(attr, kind)] * speed


def modifier(shift=False, ctrl=False):
    """The slider's multiplier: Shift x5, Ctrl x0.2."""
    return 5.0 if shift else 0.2 if ctrl else 1.0


def scrubbed(start, dx, step, lo=None, hi=None, kind="double"):
    """A value `dx` px along the slider from `start`, kept in [lo, hi]."""
    value = float(start) + float(dx) * float(step)
    if lo is not None:
        value = max(float(lo), value)
    if hi is not None:
        value = min(float(hi), value)
    if kind in ("bool", "long", "short", "byte", "char", "enum"):
        return int(round(value))
    return value


def key_moves(before, after, frame):
    """What a refresh on one frame did to the keys there: (set, removed) channel keys
    - a key that came onto the frame, and a key that left it (fewer keys than before:
    a key moved away by a drag elsewhere is not a deletion here). A channel only in
    one of them (the selection changed) is neither. `before` / `after`:
    {key: (on_key, keys_count)}. A key set again over one that stood changes neither
    and flashes from the press that set it."""
    set_, removed = [], []
    for k, now in after.items():
        was = before.get(k)
        if was is None:
            continue
        if now[0] and not was[0]:
            set_.append(k)
        elif was[0] and not now[0] and now[1] < was[1]:
            removed.append(k)
    return set_, removed


def head_text(lead, others):
    """The head's name and the +N pill's text ('' with one object)."""
    name = (lead or "").split("|")[-1]
    return name, ("+%d" % others) if others > 0 else ""


def ensure_finite(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0
