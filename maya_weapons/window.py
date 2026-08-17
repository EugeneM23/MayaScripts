"""The window: pick a weapon, press Add, dial in the grip.

Plain `maya.cmds` -- a dropdown, a button and two float rows need no Qt.

Two habits from the rest of this repo are load-bearing. Every callback goes
through `_run`, which puts the failure on the status line: an exception
escaping a UI callback lands in the Script Editor and the panel just looks
dead. And the offset fields are read back from the scene whenever they might
have gone stale, so the numbers on screen are never a lie about the scene.

The offsets are remembered per weapon in an optionVar. A grip dialled in once
should not be retyped tomorrow, and a sword and a shield want different ones.
"""

import traceback

import maya.cmds as cmds

from maya_weapons import attach
from maya_weapons import catalog
from maya_weapons import skeleton

WINDOW = "mayaWeaponsWindow"
_MENU = "mayaWeaponsMenu"
_ROTATE = "mayaWeaponsRotate"
_TRANSLATE = "mayaWeaponsTranslate"
_STATUS = "mayaWeaponsStatus"
_BOUND = "mayaWeaponsBound"

_OPTIONVAR = "mayaWeapons_offset_{0}"

NO_CHARACTER = ("no character - open the picker and press Connect, "
                "or select a joint")
NOT_ATTACHED = "nothing attached yet - press Add"


# ------------------------------------------------------------------ policy

def optionvar_name(key):
    return _OPTIONVAR.format(key)


def pack_offsets(rotate, translate):
    return [float(value) for value in tuple(rotate) + tuple(translate)]


def unpack_offsets(values):
    """Six stored numbers -> (rotate, translate). Anything else -> zeros.

    Maya answers a missing optionVar with 0 or an empty list, and a stored
    value of the wrong length can only come from an older version of this
    tool; half a grip is worse than none.
    """
    zeros = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    try:
        numbers = [float(value) for value in values]
    except (TypeError, ValueError):
        return zeros
    if len(numbers) != 6:
        return zeros
    return tuple(numbers[:3]), tuple(numbers[3:])


def bound_message(root):
    return "no character bound" if not root else root.split("|")[-1]


def missing_bone_message(root, bone):
    return "{0} has no bone '{1}'".format(root.split("|")[-1], bone)


def missing_file_message(path):
    return "file not found: " + path


def added_message(entry, bone):
    return "{0} added to {1}".format(entry.label, bone.split("|")[-1])


# ------------------------------------------------------------------- state

def _entry():
    """The catalog entry the dropdown is showing."""
    return catalog.by_label(cmds.optionMenu(_MENU, query=True, value=True))


def _fields():
    rotate = cmds.floatFieldGrp(_ROTATE, query=True, value=True)[:3]
    translate = cmds.floatFieldGrp(_TRANSLATE, query=True, value=True)[:3]
    return tuple(rotate), tuple(translate)


def _set_fields(rotate, translate):
    cmds.floatFieldGrp(_ROTATE, edit=True, value1=rotate[0], value2=rotate[1],
                       value3=rotate[2])
    cmds.floatFieldGrp(_TRANSLATE, edit=True, value1=translate[0],
                       value2=translate[1], value3=translate[2])


def _remembered(entry):
    name = optionvar_name(entry.key)
    if not cmds.optionVar(exists=name):
        return unpack_offsets(None)
    return unpack_offsets(cmds.optionVar(query=name))


def _remember(entry, rotate, translate):
    name = optionvar_name(entry.key)
    cmds.optionVar(clearArray=name)
    for value in pack_offsets(rotate, translate):
        cmds.optionVar(floatValueAppend=(name, value))


def _status(message):
    cmds.text(_STATUS, edit=True, label=message)


def _carrier(entry):
    """Root, bone and carrier for `entry` on the bound character.

    All three are returned so callers can tell "no character" from "character
    has no such bone" from "the bone is bare"; each says something different
    on the status line.
    """
    root = skeleton.current_root()
    cmds.text(_BOUND, edit=True, label=bound_message(root))
    if not root:
        return None, None, None
    bone = skeleton.resolve_bone(root, entry.bone)
    if not bone:
        return root, None, None
    return root, bone, attach.find_attached(bone)


# --------------------------------------------------------------- callbacks

def _run(action):
    """Run a callback, and put anything it throws on the status line."""
    try:
        action()
    except Exception:
        _status(traceback.format_exc().strip().splitlines()[-1])
        raise


def refresh():
    """Re-read the scene: which character, and what the fields should show."""
    entry = _entry()
    root, bone, carrier = _carrier(entry)

    if carrier:
        rotate, translate = attach.read_offsets(carrier)
        _set_fields(rotate, translate)
        _status("{0} on {1}".format(entry.label, bone.split("|")[-1]))
        return

    _set_fields(*_remembered(entry))
    if not root:
        _status(NO_CHARACTER)
    elif not bone:
        _status(missing_bone_message(root, entry.bone))
    else:
        _status(NOT_ATTACHED)


def add_weapon():
    """Put the chosen weapon into its bone, replacing what we put there before."""
    entry = _entry()
    root, bone, _carrier_now = _carrier(entry)
    if not root:
        _status(NO_CHARACTER)
        return
    if not bone:
        _status(missing_bone_message(root, entry.bone))
        return

    absent = catalog.missing(entry)
    if absent:
        _status(missing_file_message(absent))
        return

    rotate, translate = _fields()
    attach.attach(entry, bone, rotate, translate)
    _remember(entry, rotate, translate)
    _status(added_message(entry, bone))


def offsets_changed():
    """Live edit: write the fields into the attached weapon, and remember them."""
    entry = _entry()
    rotate, translate = _fields()
    _remember(entry, rotate, translate)

    _root, bone, carrier = _carrier(entry)
    if not carrier:
        _status(NOT_ATTACHED)
        return
    attach.write_offsets(carrier, rotate, translate)
    _status("{0} on {1}".format(entry.label, bone.split("|")[-1]))


# ------------------------------------------------------------------ window

def show_window():
    """Open the window, replacing one left from a previous call."""
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)

    cmds.window(WINDOW, title="Weapons", widthHeight=(380, 190),
                sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 8))

    cmds.text(_BOUND, label="", align="left")

    cmds.optionMenu(_MENU, label="Weapon",
                    changeCommand=lambda *_args: _run(refresh))
    for label in catalog.labels():
        cmds.menuItem(label=label)

    cmds.button(label="Add", height=30,
                command=lambda *_args: _run(add_weapon))

    cmds.floatFieldGrp(_ROTATE, numberOfFields=3, label="Rotate",
                       value1=0.0, value2=0.0, value3=0.0, precision=3,
                       changeCommand=lambda *_args: _run(offsets_changed))
    cmds.floatFieldGrp(_TRANSLATE, numberOfFields=3, label="Translate",
                       value1=0.0, value2=0.0, value3=0.0, precision=3,
                       changeCommand=lambda *_args: _run(offsets_changed))

    cmds.text(_STATUS, label="", align="left")

    cmds.setParent("..")
    cmds.showWindow(WINDOW)

    _run(refresh)
    return WINDOW
