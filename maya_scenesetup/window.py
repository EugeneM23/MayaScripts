"""The window: pick a weapon, press Add, dial in the grip.

Plain `maya.cmds` -- a dropdown, a button and two float rows need no Qt.

Two habits from the rest of this repo are load-bearing. Every callback goes
through `_run`, which puts the failure on the status line: an exception
escaping a UI callback lands in the Script Editor and the panel just looks
dead. And the offset fields are read back from the scene whenever they might
have gone stale, so the numbers on screen are never a lie about the scene.

The offsets are remembered per weapon in an optionVar. A grip dialled in once
should not be retyped tomorrow, and a sword and a shield want different ones.

Beside the dropdown there is an FBX field: paste a path and it wins over the
list, for any file the table knows nothing about. It resolves in ONE place
(`_entry`), so Add, the offset fields, Connect and Add Aim all follow it
without a line of their own, and the path itself is remembered too.
"""

import traceback

import maya.cmds as cmds

from maya_overrig import aimrig

from maya_scenesetup import aim as weaponaim
from maya_scenesetup import attach
from maya_scenesetup import bonedrive
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
_CUSTOM = "mayaSceneSetupCustomFbx"

# The grip in its 2026-08-21 space: raw channels under the HAND. The two
# older names lived under weapon_r and are read only to migrate -- writing
# an old-space triple as under-hand channels puts the sword at the hand
# origin, so a new space needed a new name.
_GRIP_OPTIONVAR = "mayaSceneSetup_grip_{0}"
_OPTIONVAR = "mayaSceneSetup_offset_{0}"
_LEGACY_OPTIONVAR = "mayaWeapons_offset_{0}"
_CUSTOM_OPTIONVAR = "mayaSceneSetup_custom_fbx"

NO_CHARACTER = ("no character - open the picker and press Connect, "
                "or select a joint")
NOT_ATTACHED = "nothing attached yet - press Add"
NO_WEAPON = "no weapon in the hand - press Add first"
NOT_CONNECTED = "not connected - the hands are not on the weapon"
ALREADY_CONNECTED = "already connected"
LINKED_NO_ADD = ("the hands ride this weapon - press Disconnect Arms before "
                 "replacing it")
LINKED_NO_REMOVE = ("the hands ride this weapon - press Disconnect Arms "
                    "before removing it")
AIMED_NO_ADD = "the weapon has an aim - Bake+Delete in the picker first"
LINKED_NO_OFFSETS = ("the weapon is animated - the grip is saved and "
                     "applies on the next Add or clip import")


# ------------------------------------------------------------------ policy

def optionvar_name(key):
    return _OPTIONVAR.format(key)


def grip_optionvar_name(key):
    return _GRIP_OPTIONVAR.format(key)


def grip_values(new_era, old_era, bone_local, compose):
    """Which grip the fields show, and in which space. Pure.

    New-era saves are raw under-hand channels. Everything else goes through
    the composition against the drive bone's local matrix: an old-era save
    lived under weapon_r, and NO save composes zeros -- which lands the sword
    exactly on the bone, the game's own grip. With no bone to compose against
    zeros stand in; old-space numbers are never displayed as if they were
    new-space.
    """
    if new_era is not None:
        return unpack_offsets(new_era)
    if bone_local is not None:
        rotate, translate = unpack_offsets(old_era)
        return compose(rotate, translate, bone_local)
    return unpack_offsets(None)


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


def chosen_entry(field_text, entry):
    """The entry a press uses: the FBX field wins when it holds a path.

    Whitespace-only text counts as empty, or a stray space would silently
    redirect Add at a file called " ". Double quotes are stripped because that
    is how Windows Explorer copies a path.
    """
    text = (field_text or "").strip().strip('"').strip()
    if not text:
        return entry
    return catalog.entry_for_path(text, entry.bone)


def bound_message(root):
    return "no character bound" if not root else root.split("|")[-1]


def missing_bone_message(root, bone):
    return "{0} has no bone '{1}'".format(root.split("|")[-1], bone)


def missing_parent_message(bone):
    return ("'{0}' has no parent bone - nothing to hang the weapon on"
            .format(bone))


def removed_message(entry):
    return "{0} removed - the bone keeps the animation".format(entry.label)


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
    """The entry every callback works on: the FBX field, else the dropdown.

    One place, so Add, the offset fields, Connect, Add Aim and refresh all
    follow the field without a line of their own.
    """
    return chosen_entry(
        cmds.textFieldGrp(_CUSTOM, query=True, text=True),
        catalog.by_label(cmds.optionMenu(_MENU, query=True, value=True)))


def _fields():
    rotate = cmds.floatFieldGrp(_ROTATE, query=True, value=True)[:3]
    translate = cmds.floatFieldGrp(_TRANSLATE, query=True, value=True)[:3]
    return tuple(rotate), tuple(translate)


def _set_fields(rotate, translate):
    cmds.floatFieldGrp(_ROTATE, edit=True, value1=rotate[0], value2=rotate[1],
                       value3=rotate[2])
    cmds.floatFieldGrp(_TRANSLATE, edit=True, value1=translate[0],
                       value2=translate[1], value3=translate[2])


def _remembered(entry, bone_local=None):
    """The grip for this weapon as under-hand channels.

    A grip dialled in yesterday is worth more than a tidy prefix, so both
    pre-2026-08-21 names are still read -- but their numbers lived under
    weapon_r, so they only reach the fields composed with the drive bone's
    local matrix (`grip_values` holds the policy).
    """
    new_era = None
    name = grip_optionvar_name(entry.key)
    if cmds.optionVar(exists=name):
        new_era = cmds.optionVar(query=name)
    old_era = None
    for old in (optionvar_name(entry.key),
                _LEGACY_OPTIONVAR.format(entry.key)):
        if cmds.optionVar(exists=old):
            old_era = cmds.optionVar(query=old)
            break
    return grip_values(new_era, old_era, bone_local, bonedrive.composed_grip)


def _remembered_path():
    """The FBX path this window was last pointed at, or ""."""
    if cmds.optionVar(exists=_CUSTOM_OPTIONVAR):
        return cmds.optionVar(query=_CUSTOM_OPTIONVAR) or ""
    return ""


def _remember(entry, rotate, translate):
    name = grip_optionvar_name(entry.key)
    cmds.optionVar(clearArray=name)
    for value in pack_offsets(rotate, translate):
        cmds.optionVar(floatValueAppend=(name, value))


def _status(message):
    cmds.text(_STATUS, edit=True, label=message)


def _attached(entry):
    """Root, hand, drive bone, weapon, and whether it drives the arms.

    All five are returned so callers can tell "no character" from "character
    has no such bone" from "the bone is bare"; each says something different
    on the status line. `hand` is the drive bone's own DAG parent -- where
    the weapon lives since 2026-08-21.

    The weapon is looked for under the hand first, under the drive bone
    second (the legacy home of files attached by the old version), and
    through the link last: once connected it lives out in world space and
    neither bone knows anything about it any more.
    """
    root = _bound_root()
    if not root:
        return None, None, None, None, False
    bone = skeleton.resolve_bone(root, entry.bone)
    if not bone:
        return root, None, None, None, False
    hand = attach.parent_bone(bone)

    in_hand = attach.find_attached(hand) if hand else None
    attached_now = in_hand or attach.find_attached(bone)
    if attached_now:
        return root, hand, bone, attached_now, False

    linked = linking.linked_weapon()
    return root, hand, bone, linked, linked is not None


def _bound_root():
    """The character, with the header label refreshed to match."""
    root = skeleton.current_root()
    cmds.text(_BOUND, edit=True, label=bound_message(root))
    return root


def _locate(entry):
    """Root, hand, bone, weapon and link state, or None with the status set.

    The shared front half of every weapon callback: no character, a missing
    bone and a parentless bone end the press the same way everywhere.
    """
    root, hand, bone, weapon, linked = _attached(entry)
    if not root:
        _status(NO_CHARACTER)
        return None
    if not bone:
        _status(missing_bone_message(root, entry.bone))
        return None
    if not hand:
        _status(missing_parent_message(entry.bone))
        return None
    return root, hand, bone, weapon, linked


# --------------------------------------------------------------- callbacks

def _run(action):
    """Run a callback, and put anything it throws on the status line."""
    try:
        action()
    except Exception:
        _status(traceback.format_exc().strip().splitlines()[-1])
        raise


def refresh():
    """Re-read the scene: which character, and what the fields should show.

    The fields always show the GRIP, never the animation: an animated
    weapon's channels are frame values, and showing those as offsets is how
    a re-Add once saved them over the remembered grip. A clean weapon's
    channels ARE the grip, so there the scene is the truth.
    """
    entry = _entry()
    root, hand, bone, weapon, linked = _attached(entry)
    bone_local = (bonedrive.local_matrix(bone, hand)
                  if bone and hand else None)

    if weapon:
        if attach.is_animated(weapon):
            _set_fields(*_remembered(entry, bone_local))
        else:
            _set_fields(*attach.read_offsets(weapon))
        _status(linked_message(entry) if linked
                else attached_message(entry, hand or bone))
        return

    _set_fields(*_remembered(entry, bone_local))
    if not root:
        _status(NO_CHARACTER)
    elif not bone:
        _status(missing_bone_message(root, entry.bone))
    elif not hand:
        _status(missing_parent_message(entry.bone))
    else:
        _status(NOT_ATTACHED)


def custom_changed():
    """Remember the pasted path, then reload the fields for its key.

    The grip is remembered per weapon, and a custom file is a weapon like any
    other -- so the numbers on screen have to follow the field.
    """
    cmds.optionVar(stringValue=(_CUSTOM_OPTIONVAR,
                                cmds.textFieldGrp(_CUSTOM, query=True,
                                                  text=True) or ""))
    refresh()


def add_weapon():
    """Put the chosen weapon into the hand, replacing what we put there before.

    The fields are re-read from the scene first: they were last filled by
    some earlier refresh, and a character bound SINCE then (the picker's
    Connect does not reach into this window) leaves them showing the
    unbound zeros -- which this press would then apply and remember over
    the real grip. Anything the user typed survives the re-read: typing
    fired `offsets_changed`, which remembered it.
    """
    refresh()
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    _root, hand, bone, attached_now, linked = located
    if linked:
        # Replacing deletes the weapon, and the IK hand controls are its DAG
        # children: this press would take both arm rigs down unbaked.
        _status(LINKED_NO_ADD)
        return
    if attached_now and aimrig.aim_for(attach.model_root(attached_now)):
        # Same shape of problem: the aim's locators drive the geometry, so
        # replacing it leaves them pointing at a deleted node.
        _status(AIMED_NO_ADD)
        return

    absent = catalog.missing(entry)
    if absent:
        _status(missing_file_message(absent))
        return

    rotate, translate = _fields()
    _weapon, note = attach.attach(entry, hand, bone, rotate, translate)
    _remember(entry, rotate, translate)
    message = added_message(entry, hand)
    _status(message + " - " + note if note else message)


def remove_weapon():
    """Take the weapon off: the bone gets its animation back, the sword goes.

    Forced by the inverted drive: deleting the sword by hand would lose the
    bone's animation (it lives on the sword) and leave an orphaned
    constraint under the bone (trap 4).
    """
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    _root, hand, bone, weapon, linked = located
    if linked:
        _status(LINKED_NO_REMOVE)
        return
    if not weapon:
        _status(NOT_ATTACHED)
        return
    if aimrig.aim_for(attach.model_root(weapon)):
        _status(AIMED_NO_ADD)
        return
    removed = attach.detach(hand, bone)
    _status(removed_message(entry) if removed else NOT_ATTACHED)


def offsets_changed():
    """Live edit: move the weapon to the new grip, and remember it.

    Through `bonedrive.regrip`, never a plain channel write: the bone plays
    its own animation through the constraint's captured offset, and writing
    the sword's channels under a live constraint would drag the bone along
    by the OLD offset. Regrip rehooks the constraint around the write, so
    the sword moves and the bone does not.
    """
    entry = _entry()
    rotate, translate = _fields()
    _remember(entry, rotate, translate)  # the next Add still wants them

    _root, hand, bone, weapon, _linked = _attached(entry)
    if not weapon:
        _status(NOT_ATTACHED)
        return
    if attach.is_animated(weapon):
        _status(LINKED_NO_OFFSETS)
        return
    bonedrive.regrip(weapon, bone, rotate, translate)
    _status(attached_message(entry, hand or bone))


def connect_arms():
    """Hand the arms over to the weapon: both to IK, hands onto the prop."""
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    root, _hand, _bone, weapon, linked = located
    if linked:
        _status(ALREADY_CONNECTED)
        return
    if not weapon:
        _status(NO_WEAPON)
        return
    _status(linking.connect(weapon, skeleton.scene_map(root)))


def add_aim():
    """Put OverRig's aim on the attached weapon, both locators placed for you.

    Works wherever the weapon is -- in the hand or out in world after Connect.
    The user's call: the button does not check and does not care.
    """
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    _root, _hand, _bone, weapon, _linked = located
    if not weapon:
        _status(NO_WEAPON)
        return
    _status(weaponaim.add_aim(entry, weapon))


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
    _root, hand, _bone, weapon, linked = located
    if not linked:
        _status(NOT_CONNECTED)
        return
    _status(linking.disconnect(weapon, hand))


# ------------------------------------------------------------------ window

def show_window():
    """Open the window, replacing one left from a previous call."""
    for name in (WINDOW, _LEGACY_WINDOW):
        if cmds.window(name, exists=True):
            cmds.deleteUI(name)

    cmds.window(WINDOW, title="Scene Setup", widthHeight=(420, 370),
                sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 8))

    cmds.text(_BOUND, label="", align="left")

    cmds.optionMenu(_MENU, label="Weapon",
                    changeCommand=lambda *_args: _run(refresh))
    for label in catalog.labels():
        cmds.menuItem(label=label)

    cmds.textFieldGrp(_CUSTOM, label="FBX", text=_remembered_path(),
                      annotation="Paste the path to any .fbx to attach it "
                                 "instead of the weapon in the dropdown. The "
                                 "bone comes from the dropdown; the scale is "
                                 "1. Clear the field to go back to the list.",
                      changeCommand=lambda *_args: _run(custom_changed))

    cmds.button(label="Add", height=30,
                annotation="Import the weapon under the hand bone, move any "
                           "weapon-bone animation onto it, and drive the "
                           "bone from the weapon. Replaces what a previous "
                           "Add put there, animation preserved.",
                command=lambda *_args: _run(add_weapon))
    cmds.button(label="Remove Weapon", height=24,
                annotation="Bake the weapon bone's animation back from the "
                           "weapon, then delete the weapon and its "
                           "constraint. Deleting the sword by hand instead "
                           "loses that animation.",
                command=lambda *_args: _run(remove_weapon))

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
    cmds.button(label="Add Aim", height=28,
                annotation="OverRig's aim on the weapon: one locator a little "
                           "past the tip, one out to the side at the same "
                           "distance. Drag them to aim the blade. Remove it "
                           "with Bake+Delete in the picker.",
                command=lambda *_args: _run(add_aim))

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
