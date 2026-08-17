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

from maya_scenesetup import attach
from maya_scenesetup import camera as camerarig
from maya_scenesetup import catalog
from maya_scenesetup import connect as linking
from maya_scenesetup import skeleton

WINDOW = "mayaSceneSetupWindow"
_LEGACY_WINDOW = "mayaWeaponsWindow"  # left open across the rename
_MENU = "mayaSceneSetupMenu"
_ROTATE = "mayaSceneSetupRotate"
_TRANSLATE = "mayaSceneSetupTranslate"
_STATUS = "mayaSceneSetupStatus"
_BOUND = "mayaSceneSetupBound"

_OPTIONVAR = "mayaSceneSetup_offset_{0}"
_LEGACY_OPTIONVAR = "mayaWeapons_offset_{0}"

NO_CHARACTER = ("no character - open the picker and press Connect, "
                "or select a joint")
NOT_ATTACHED = "nothing attached yet - press Add"
NO_WEAPON = "no weapon in the hand - press Add first"
NOT_CONNECTED = "not connected - the hands are not on the weapon"
ALREADY_CONNECTED = "already connected"
LINKED_NO_ADD = ("the hands ride this weapon - press Disconnect Arms before "
                 "replacing it")
LINKED_NO_OFFSETS = "the weapon is animated - its offsets are baked in"


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


def linked_message(entry):
    return "{0} drives the arms".format(entry.label)


def attached_message(entry, bone):
    return "{0} on {1}".format(entry.label, bone.split("|")[-1])


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
    """The grip remembered for this weapon, reading through the old name.

    The optionVar was called `mayaWeapons_offset_*` before this module became
    SceneSetup. A grip dialled in yesterday is worth more than a tidy prefix,
    so the old name is still read; only the new one is written.
    """
    for name in (optionvar_name(entry.key),
                 _LEGACY_OPTIONVAR.format(entry.key)):
        if cmds.optionVar(exists=name):
            return unpack_offsets(cmds.optionVar(query=name))
    return unpack_offsets(None)


def _remember(entry, rotate, translate):
    name = optionvar_name(entry.key)
    cmds.optionVar(clearArray=name)
    for value in pack_offsets(rotate, translate):
        cmds.optionVar(floatValueAppend=(name, value))


def _status(message):
    cmds.text(_STATUS, edit=True, label=message)


def _carrier(entry):
    """Root, bone, carrier, and whether that carrier drives the arms.

    All four are returned so callers can tell "no character" from "character
    has no such bone" from "the bone is bare"; each says something different
    on the status line.

    The carrier is looked for in the bone first and through the link second:
    once connected it lives out in world space and the bone knows nothing
    about it any more.
    """
    root = _bound_root()
    if not root:
        return None, None, None, False
    bone = skeleton.resolve_bone(root, entry.bone)
    if not bone:
        return root, None, None, False

    in_hand = attach.find_attached(bone)
    if in_hand:
        return root, bone, in_hand, False

    linked = linking.linked_carrier()
    return root, bone, linked, linked is not None


def _bound_root():
    """The character, with the header label refreshed to match."""
    root = skeleton.current_root()
    cmds.text(_BOUND, edit=True, label=bound_message(root))
    return root


def _locate(entry):
    """Root, bone, carrier and link state, or None with the status set.

    The shared front half of every weapon callback: no character and a
    missing bone end the press the same way everywhere.
    """
    root, bone, carrier, linked = _carrier(entry)
    if not root:
        _status(NO_CHARACTER)
        return None
    if not bone:
        _status(missing_bone_message(root, entry.bone))
        return None
    return root, bone, carrier, linked


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
    root, bone, carrier, linked = _carrier(entry)

    if carrier:
        rotate, translate = attach.read_offsets(carrier)
        _set_fields(rotate, translate)
        _status(linked_message(entry) if linked
                else attached_message(entry, bone))
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
    located = _locate(entry)
    if located is None:
        return
    _root, bone, _carrier_now, linked = located
    if linked:
        # Replacing deletes the carrier, and the IK hand controls are its DAG
        # children: this press would take both arm rigs down unbaked.
        _status(LINKED_NO_ADD)
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
    _remember(entry, rotate, translate)  # the next Add still wants them

    _root, bone, carrier, _linked = _carrier(entry)
    if not carrier:
        _status(NOT_ATTACHED)
        return
    if attach.is_animated(carrier):
        _status(LINKED_NO_OFFSETS)
        return
    attach.write_offsets(carrier, rotate, translate)
    _status(attached_message(entry, bone))


def connect_arms():
    """Hand the arms over to the weapon: both to IK, hands onto the prop."""
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    root, _bone, carrier, linked = located
    if linked:
        _status(ALREADY_CONNECTED)
        return
    if not carrier:
        _status(NO_WEAPON)
        return
    _status(linking.connect(carrier, skeleton.scene_map(root)))


def camera_setup():
    """Bake the camera bone onto a camera, then drive the bone from it.

    No character needs to be bound: the camera bone often sits outside the
    skeleton's own subtree, so the resolver falls back to the scene.
    """
    root = _bound_root()

    bone, problem = camerarig.resolve_bone(skeleton.scene_map(root))
    if problem:
        _status(problem)
        return

    start = cmds.playbackOptions(query=True, minTime=True)
    end = cmds.playbackOptions(query=True, maxTime=True)
    _status(camerarig.setup(bone, start, end))


def disconnect_arms():
    """Hands back on the root control, weapon back in the hand."""
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    _root, bone, carrier, linked = located
    if not linked:
        _status(NOT_CONNECTED)
        return
    _status(linking.disconnect(carrier, bone))


# ------------------------------------------------------------------ window

def show_window():
    """Open the window, replacing one left from a previous call."""
    for name in (WINDOW, _LEGACY_WINDOW):
        if cmds.window(name, exists=True):
            cmds.deleteUI(name)

    cmds.window(WINDOW, title="Scene Setup", widthHeight=(380, 330),
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

    cmds.separator(height=8, style="in")
    cmds.button(label="Connect Arms To Weapon", height=28,
                annotation="Both arms to IK, the weapon out to world, and the "
                           "IK hands hung on it. Animation is re-baked at "
                           "every step.",
                command=lambda *_args: _run(connect_arms))
    cmds.button(label="Disconnect Arms", height=24,
                annotation="Hands back on the root control, weapon back in "
                           "the hand. The weapon keeps its animation.",
                command=lambda *_args: _run(disconnect_arms))

    cmds.separator(height=8, style="in")
    cmds.button(label="Camera Setup", height=28,
                annotation="Make a camera on camera_bone, bake the bone's "
                           "animation onto it, and drive the bone from the "
                           "camera. The camera lands in the bone's transform; "
                           "only the axes differ (the measured turn).",
                command=lambda *_args: _run(camera_setup))

    cmds.text(_STATUS, label="", align="left")

    cmds.setParent("..")
    cmds.showWindow(WINDOW)

    _run(refresh)
    return WINDOW
