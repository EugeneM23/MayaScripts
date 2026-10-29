"""pending - what is picked in the Connections card but not applied yet.

The animator's ask (2026-10-29): «предложи несколько вариантов более удобного
разсположения инструментов в вкладке connections и нужно сделать консистентно
что бы перепекание происходило по нажатию кнопки а не по разному в каждом
разделе». Every row of the card records a pick; the row's check button, or the
tab's one Apply all, is what bakes.

This module is that record, stdlib only (a test pins it): the keys, the store
-- ONE set per RIG, not per card, so the hub's card and a popup copy of it
show the same picks -- what a press counts as one change, and the line the
status says. The resolution between a limb's mode and its W is in
`connections.py`, where both states are already read.

Spec: docs/superpowers/specs/2026-10-29-connections-pick-then-apply-design.md
"""

SPINE = "spine"
AIM = "aim"
CAMERA = "camera"
CAMERA_POSITION = "camera:position"
CAMERA_AIM = "camaim"

LIMB = "limb:"
WORLD = "world:"
PARENT = "parent:"

#  which picks belong to which tab of the card
TAB = {"body": (LIMB, WORLD, SPINE),
       "weapon": (PARENT, AIM),
       "camera": (CAMERA, CAMERA_POSITION, CAMERA_AIM)}

#  the order the status names them in, and the order inside each kind
_RANK = (LIMB, WORLD, SPINE, PARENT, AIM, CAMERA, CAMERA_POSITION, CAMERA_AIM)
_KIND_RANK = ("Arm", "Leg")
_SIDE_RANK = ("R", "L")
_ROW_RANK = ("R", "L", "W")

ROW_WORD = {"R": "the right hand", "L": "the left hand", "W": "the weapon"}

#  rig key -> {pick key: value}
PICKS = {}


# ------------------------------------------------------------------- keys

def limb_key(kind, side):
    """The pick of the limb of `kind` ('Arm' / 'Leg') on `side`: FK or IK."""
    return "%s%s:%s" % (LIMB, kind, side)


def world_key(kind, side):
    """The pick of that limb's W: True into world, False out of it."""
    return "%s%s:%s" % (WORLD, kind, side)


def parent_key(row):
    """The pick of the weapon tab's row R / L / W."""
    return "%s%s" % (PARENT, row)


# ------------------------------------------------------------------ store

def for_rig(key):
    """The picks standing for the rig `key` ('' is the root-namespace rig), a
    copy: a caller edits its own dict and hands it back to `set_for`."""
    return dict(PICKS.get(key, {}))


def set_for(key, picks):
    """Keep `picks` for the rig `key`; an empty set forgets the rig."""
    if picks:
        PICKS[key] = dict(picks)
    else:
        PICKS.pop(key, None)
    return for_rig(key)


def only(key):
    """Keep the picks of the rig `key` alone - another character's picks mean
    nothing on this one (the card drops them when it reads another rig)."""
    for other in [k for k in PICKS if k != key]:
        del PICKS[other]


def clear():
    PICKS.clear()


# ------------------------------------------------------------------- pure

def record(picks, pick, value, state):
    """A new dict with `pick` wanting `value` while the scene shows `state` -
    and with the pick dropped when it IS the state (a pick is a change)."""
    out = dict(picks)
    if value == state:
        out.pop(pick, None)
    else:
        out[pick] = value
    return out


def without(picks, *drop):
    """A new dict without the keys named (one that is not there is no error)."""
    return dict((k, v) for k, v in picks.items() if k not in drop)


def of_tab(picks, tab):
    """The picks of one tab of the card."""
    wants = TAB.get(tab, ())
    out = {}
    for key, value in picks.items():
        for want in wants:
            if key == want or (want.endswith(":") and key.startswith(want)):
                out[key] = value
                break
    return out


def units(picks):
    """The picks grouped into what one press does: a limb's mode and its W are
    one change (one `switch_limb`), the camera's parent and its Position only
    are one (one `camera_parent`)."""
    seen = []
    for key in sorted(picks, key=_rank):
        unit = key
        if key.startswith(LIMB) or key.startswith(WORLD):
            unit = LIMB + key.split(":", 1)[1]
        elif key == CAMERA_POSITION:
            unit = CAMERA
        if unit not in seen:
            seen.append(unit)
    return seen


def count(picks):
    """How many changes a press would make - the number on Apply all."""
    return len(units(picks))


def phrase(pick, value):
    """One pick in words, as the status says it."""
    if pick.startswith(LIMB):
        _, kind, side = pick.split(":")
        return "%s %s to %s" % (kind, side, value)
    if pick.startswith(WORLD):
        _, kind, side = pick.split(":")
        return "%s %s %s world" % (kind, side, "into" if value else "out of")
    if pick.startswith(PARENT):
        return "%s to %s" % (ROW_WORD.get(pick.split(":")[1], pick),
                             str(value).replace("_", " "))
    if pick == SPINE:
        return "the spine to %s" % value
    if pick == AIM:
        return "the weapon's aim %s" % ("on" if value else "off")
    if pick == CAMERA:
        return "the camera to %s" % value
    if pick == CAMERA_POSITION:
        return "the camera's follow %s" % ("position only" if value else "whole")
    if pick == CAMERA_AIM:
        return "the camera's aim %s" % ("on" if value else "off")
    return "%s to %s" % (pick, value)


def text(picks):
    """Every pick as one line, in a stable order: «Arm R to FK, Leg L to IK»."""
    return ", ".join(phrase(key, picks[key]) for key in sorted(picks, key=_rank))


def _rank(key):
    """(the pick's place in _RANK, the kind's, the side's) - a stable order."""
    for index, prefix in enumerate(_RANK):
        if key == prefix:
            return (index, 0, 0)
        if prefix.endswith(":") and key.startswith(prefix):
            parts = key.split(":")
            if prefix == PARENT:
                return (index, 0, _place(_ROW_RANK, parts[1]))
            return (index, _place(_KIND_RANK, parts[1]),
                    _place(_SIDE_RANK, parts[2]))
    return (len(_RANK), 0, 0)


def _place(order, value):
    return order.index(value) if value in order else len(order)
