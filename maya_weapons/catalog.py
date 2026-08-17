"""The weapon table: what can be attached, and where it goes.

The target bone is a property of the entry rather than a constant in the code,
so a shield later is one line with `weapon_l` and no logic to touch. `scale` is
here for the same reason: a model that arrives at the wrong size is a fact
about that model, not something the animator should retype every time.

Paths are written with forward slashes. The FBX plugin is driven through MEL,
where a backslash starts an escape.
"""

import collections
import os

Weapon = collections.namedtuple("Weapon", "key label path bone scale")

WEAPONS = [
    Weapon("LongSword_02", "Long Sword 02",
           "C:/!!!Work/Animations/Sources/LongSword_02.fbx", "weapon_r", 1.0),
]


def labels():
    """Dropdown labels, in table order."""
    return [entry.label for entry in WEAPONS]


def by_label(label):
    for entry in WEAPONS:
        if entry.label == label:
            return entry
    return None


def by_key(key):
    for entry in WEAPONS:
        if entry.key == key:
            return entry
    return None


def missing(entry):
    """The entry's path if the file is not on disk, "" if it is."""
    return "" if os.path.isfile(entry.path) else entry.path
