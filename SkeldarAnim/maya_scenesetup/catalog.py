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
import string

Weapon = collections.namedtuple("Weapon", "key label path bone scale")

_LEGAL = frozenset(string.ascii_letters + string.digits + "_")

# Two dirnames up from this file is the container that holds both the
# packages and assets/ -- true in the repo and in an installed copy alike.
_CONTAINER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_LEGACY_SWORD = "C:/!!!Work/Animations/Sources/LongSword_02.fbx"

# The user's original file, spelling and all: the fallback has to match what
# is actually on that disk. Our shipped copy fixes the typo.
_LEGACY_CHARACTER = ("C:/!!!Work/Animations/Rigs/Characters/"
                     "Manny_Sckeleton.ma")


def character_path():
    """The working character scene: the shipped copy first, legacy second.

    Same rule as the sword, but resolved at call time -- there is no table
    row to freeze it into, and a copy that appears in assets/ mid-session
    (a colleague re-running the installer) should win immediately.
    """
    local = os.path.join(_CONTAINER, "assets",
                         "Manny_Skeleton.ma").replace("\\", "/")
    return local if os.path.isfile(local) else _LEGACY_CHARACTER


def _sword_path():
    """The shipped copy first, the legacy absolute path as fallback.

    Computed once at import: the table keeps holding a plain absolute
    path, so missing(), attach and the offset optionVars never learn
    that anything changed.
    """
    local = os.path.join(_CONTAINER, "assets",
                         "LongSword_02.fbx").replace("\\", "/")
    return local if os.path.isfile(local) else _LEGACY_SWORD


WEAPONS = [
    Weapon("LongSword_02", "Long Sword 02", _sword_path(), "weapon_r", 1.0),
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


def node_key(text):
    """`text` reduced to a legal Maya node name.

    The key is not only a string in an attribute: it names the aim manifest
    (`RigPicker_aim_<key>` reaches `cmds.sets`) and an optionVar. A space, a
    dot or a leading digit there is a traceback later, on a press that has
    nothing to do with this one.
    """
    safe = "".join(c if c in _LEGAL else "_" for c in text)
    if not safe:
        return "weapon"
    return "_" + safe if safe[0].isdigit() else safe


def entry_for_path(path, bone):
    """An entry for a file the table knows nothing about.

    The key and the label come from the file's stem, so the offsets dialled
    in for it are remembered the way any weapon's are. The bone is the
    caller's -- the dropdown's, in the window -- and the scale is 1.0 rather
    than that entry's: a size correction is a fact about one known model, and
    quietly applying the sword's to somebody else's file is a surprise.
    """
    stem = os.path.splitext(os.path.basename(path.replace("\\", "/")))[0]
    key = node_key(stem)
    return Weapon(key, key, path, bone, 1.0)
