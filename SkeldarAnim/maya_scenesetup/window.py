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
(`_entry`), so Add, Remove and the offset fields all follow it without a
line of their own, and the path itself is remembered too.

Since 2026-09-07 the character is the one the SELECTION names -- any control
of the AdvancedSkeleton rig, or a joint -- then the rig, then the sole
skeleton (`skeleton.current_root`); the picker's Connect is off the shelf.
Connect Arms, Disconnect Arms, Add Aim and Camera Setup left the panel the
same day; the camera setup happens inside the retarget's Bake.
"""

import traceback

import maya.cmds as cmds

from maya_overrig import aimrig

from maya_scenesetup import attach
from maya_scenesetup import bonedrive
from maya_scenesetup import camera
from maya_scenesetup import catalog
from maya_scenesetup import character
from maya_scenesetup import colour as colouring
from maya_scenesetup import connect as linking
from maya_scenesetup import skeleton

HUB_SECTION = "characters"    # the Characters section of the SkeldarAnim hub
HUB_WEAPONS = "weapons"       # the Weapons section (2026-09-17, «декомпозируем»)
_MENU = "mayaSceneSetupMenu"
_ROTATE = "mayaSceneSetupRotate"
_TRANSLATE = "mayaSceneSetupTranslate"
_STATUS = "mayaSceneSetupStatus"                    # the Weapons line
_CHARACTER_STATUS = "mayaSceneSetupCharacterStatus"  # the Characters line
_BOUND = "mayaSceneSetupBound"
_CUSTOM = "mayaSceneSetupCustomFbx"
_CHARACTER = "mayaSceneSetupCharacter"
_CHARACTER_COLOUR = "mayaSceneSetupCharacterColour"
_WEAPON_COLOUR = "mayaSceneSetupWeaponColour"

# The grip is BONE-relative (2026-08-25, the user's ruling): zeros mean the
# sword exactly on weapon_r, and the numbers survive any reparenting. That
# is the pre-2026-08-21 meaning, so the two old names read back verbatim --
# the grip dialled before the inverted drive returns. The under-hand name
# from the four days in between (`mayaSceneSetup_grip_*`) is deliberately
# never read: its numbers mean nothing in the bone space, and applying them
# is what put the sword at the HAND («оружие подставляется в позицию
# кисти»).
_OPTIONVAR = "mayaSceneSetup_offset_{0}"
_LEGACY_OPTIONVAR = "mayaWeapons_offset_{0}"
_CUSTOM_OPTIONVAR = "mayaSceneSetup_custom_fbx"
_CHARACTER_OPTIONVAR = "mayaSceneSetup_character"

NO_CHARACTER = ("no character - select any control or joint of it (with one "
                "rig in the scene nothing needs selecting)")
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
NO_COLOUR_TARGET = ("nothing to recolour - the swatch is the colour the "
                    "next Add will bring")


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


def bound_message(root, rig=False):
    """The header: which character the presses act on, and what it is."""
    if not root:
        return "no character"
    return "Character: {0} ({1})".format(root.split("|")[-1],
                                         "rig" if rig else "skeleton")


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


def recoloured_message(what, rgb):
    return "{0} is now {1}".format(what.split("|")[-1],
                                   colouring.colour_name(rgb))


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


def _swatch(control):
    return tuple(cmds.colorSliderGrp(control, query=True, rgbValue=True))


def _set_swatch(control, rgb):
    cmds.colorSliderGrp(control, edit=True,
                        rgbValue=(rgb[0], rgb[1], rgb[2]))


def _advance_swatch(control):
    """Put the next free colour in a swatch.

    Done when the window opens and after every successful Add -- never in
    `refresh`. That is the whole rule that keeps the swatch honest: it means
    ONE thing, "the colour the next Add will bring", and a `refresh` fired by
    a dropdown change must not throw away the colour the animator just
    picked. Advancing after a press is what stops two presses in a row
    handing out the same colour when nobody touches the control.

    A first version had the swatch show the CONNECTED character's colour and
    repaint on change; the animator reversed it («цвет будем задавать перед
    созданием персонажа или оружия в сцене»), and the Recolour button beside
    it is what took over the repaint.
    """
    _set_swatch(control, colouring.free_colour().rgb)


def _remembered(entry):
    """The remembered grip for this weapon: bone-relative, read verbatim.

    Both names hold the same space (the legacy one predates the
    weapons->scenesetup rename), so the first that exists wins and no
    composition is needed -- the numbers mean "offset from weapon_r"
    whether they were dialled yesterday or before the inverted drive.
    """
    for name in (optionvar_name(entry.key),
                 _LEGACY_OPTIONVAR.format(entry.key)):
        if cmds.optionVar(exists=name):
            return unpack_offsets(cmds.optionVar(query=name))
    return unpack_offsets(None)


def _remembered_path():
    """The FBX path this window was last pointed at, or ""."""
    if cmds.optionVar(exists=_CUSTOM_OPTIONVAR):
        return cmds.optionVar(query=_CUSTOM_OPTIONVAR) or ""
    return ""


def _remember(entry, rotate, translate):
    name = optionvar_name(entry.key)
    cmds.optionVar(clearArray=name)
    for value in pack_offsets(rotate, translate):
        cmds.optionVar(floatValueAppend=(name, value))


def _status(message, control=_STATUS):
    """The Weapons section's line by default; character presses name
    theirs. Two sections, two lines (2026-09-17)."""
    cmds.text(control, edit=True, label=message)


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

    # Out in world since a Connect: the OverRig-rig kind hangs the IK hands
    # under the marked node (`linking`), the AdvancedSkeleton kind
    # (`connections`, 2026-09-18) leaves the weapon driving `weapon_r` from
    # world space -- so the drive bone still knows it.
    linked = linking.linked_weapon() or bonedrive.driving_weapon(bone)
    return root, hand, bone, linked, linked is not None


def _bound_root():
    """The character, with the header label refreshed to match."""
    root = skeleton.current_root()
    rig = bool(root) and root == skeleton.rig_root()
    cmds.text(_BOUND, edit=True, label=bound_message(root, rig))
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

def _run(action, status=_STATUS):
    """Run a callback, and put anything it throws on its section's line."""
    try:
        action()
    except Exception:
        _status(traceback.format_exc().strip().splitlines()[-1], status)
        raise


def refresh():
    """Re-read the scene: which character, and what the fields should show.

    The fields always show the GRIP -- bone-relative, zeros meaning exactly
    on weapon_r -- never the animation: an animated weapon's values are
    frame values, and showing those as offsets is how a re-Add once saved
    them over the remembered grip. A clean attached weapon is measured
    against the bone (`bonedrive.measured_grip`), so a sword nudged by hand
    in the viewport reads back honestly.
    """
    entry = _entry()
    root, hand, bone, weapon, linked = _attached(entry)

    # The swatches are deliberately NOT touched here. They hold the colour
    # the next Add will bring, and `refresh` runs on every dropdown change
    # and at the front of every press -- overwriting them would discard the
    # colour the animator just picked. They are filled once on open and
    # advanced after each Add (`_advance_swatch`).

    if weapon:
        if bone and not attach.is_animated(weapon):
            _set_fields(*bonedrive.measured_grip(weapon, bone))
        else:
            _set_fields(*_remembered(entry))
        _status(linked_message(entry) if linked
                else attached_message(entry, hand or bone))
        return

    _set_fields(*_remembered(entry))
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


def chosen_character():
    """The catalog entry the dropdown names, or the default. Never None.

    A remembered label that the table no longer carries falls back rather
    than raising: a scene file outlives a rename of a row.
    """
    label = ""
    if cmds.optionMenu(_CHARACTER, exists=True):
        label = cmds.optionMenu(_CHARACTER, query=True, value=True) or ""
    # The fallback is the RIG (2026-09-07, «Add character теперь должен
    # добавлять наш адванцед скелетон риг»): the row the dropdown opens on.
    return (catalog.character_by_label(label)
            or catalog.default_rig())


def remembered_character():
    """The label stored from the last session, or ""."""
    if cmds.optionVar(exists=_CHARACTER_OPTIONVAR):
        return cmds.optionVar(query=_CHARACTER_OPTIONVAR) or ""
    return ""


def character_changed():
    """Remember the choice. Nothing else: the press is what imports."""
    entry = chosen_character()
    cmds.optionVar(stringValue=(_CHARACTER_OPTIONVAR, entry.label))
    _status("Add Character will import: {0}".format(entry.label),
            _CHARACTER_STATUS)


def add_character():
    """Import the chosen character into the scene, then catch the UI up.

    The status is written LAST: `refresh` ends by writing its own line, and
    the outcome of the press must be what stays on screen. The refresh is
    what flips the header to the new character -- a lone skeleton binds
    through `skeleton.current_root` with no press of anything.

    The colour comes from the SWATCH (2026-09-03, the animator's ruling:
    «цвет будем задавать перед созданием персонажа или оружия в сцене»), and
    the swatch is advanced to the next free colour afterwards -- so choosing
    is optional and two presses in a row still never collide. The advance
    comes after `refresh`, which does not touch the swatches at all.
    """
    message = character.add_character(chosen_character(),
                                      _swatch(_CHARACTER_COLOUR))
    refresh()
    _advance_swatch(_CHARACTER_COLOUR)
    _status(message, _CHARACTER_STATUS)


def camera_span(bone):
    """Playback range and the bone's own keys, whole frames."""
    keys = cmds.keyframe(bone, query=True, timeChange=True) or []
    start, end = bonedrive.union_range(cmds.playbackOptions(query=True, min=True),
                                       cmds.playbackOptions(query=True, max=True),
                                       keys)
    return start, end


def camera_setup():
    """Camera Setup on the character's camera_root (2026-09-18, the
    animator: «в наш риг нужно добавить камеру так же, как мы делаем при
    ретаргете, только camera root»): the bone's animation baked onto a
    camera, the bone driven by it from then on. A second press bakes the
    bone back and removes the camera - the retarget's own step, by hand."""
    root = _bound_root()
    if not root:
        _status(NO_CHARACTER, _CHARACTER_STATUS)
        return
    bone = skeleton.resolve_bone(root, camera.BONE)
    if not bone:
        _status(missing_bone_message(root, camera.BONE), _CHARACTER_STATUS)
        return
    start, end = camera_span(bone)
    if camera.camera_for(bone):
        camera.teardown(bone, start, end)
        _status("camera removed - %s baked back and free" % camera.leaf(bone),
                _CHARACTER_STATUS)
        return
    _status(camera.setup(bone, start, end), _CHARACTER_STATUS)


def recolour_character():
    """Put the swatch's colour on the connected character.

    The CONNECTED one, not the last added: the rig, the bridge and this
    window have all been scoped to the connected character since
    2026-09-01, and a colour picking a different one would be the only
    thing here that did.

    Its own button rather than the swatch's changeCommand, so that dialling
    a colour for the NEXT character cannot repaint the current one on the
    way past.
    """
    root = _bound_root()
    shapes = colouring.character_meshes(root)
    rgb = _swatch(_CHARACTER_COLOUR)
    if not shapes:
        _status(NO_COLOUR_TARGET, _CHARACTER_STATUS)
        return
    cmds.undoInfo(openChunk=True)
    try:
        colouring.paint(shapes, rgb, root.split("|")[-1])
    finally:
        cmds.undoInfo(closeChunk=True)
    _status(recoloured_message(root, rgb), _CHARACTER_STATUS)


def recolour_weapon():
    """Put the swatch's colour on the attached weapon, wherever it is -- in
    the hand or out in world after Connect. A shading assignment survives
    re-parenting."""
    entry = _entry()
    _root, _hand, _bone, weapon, _linked = _attached(entry)
    rgb = _swatch(_WEAPON_COLOUR)
    if not weapon:
        _status(NO_COLOUR_TARGET)
        return
    cmds.undoInfo(openChunk=True)
    try:
        colouring.paint_nodes([weapon], rgb, entry.key)
    finally:
        cmds.undoInfo(closeChunk=True)
    _status(recoloured_message(entry.label, rgb))


def add_weapon():
    """Put the chosen weapon into the hand, replacing what we put there before.

    The fields are re-read first: they were last filled by some earlier
    refresh, and the scene may have moved since (a weapon nudged by hand, a
    character bound from the picker). Anything the user typed survives the
    re-read: typing fired `offsets_changed`, which remembered it.
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
    rgb = _swatch(_WEAPON_COLOUR)
    _weapon, note = attach.attach(entry, hand, bone, rotate, translate, rgb)
    _remember(entry, rotate, translate)
    _advance_swatch(_WEAPON_COLOUR)

    message = added_message(entry, hand) + " - " + colouring.colour_name(rgb)
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


# Connect Arms To Weapon, Disconnect Arms, Add Aim and Camera Setup left
# this panel on 2026-09-07 with the move to the AdvancedSkeleton rig
# (`maya_scenesetup.connect`, `aim` and `camera` stay as modules: the
# retarget's Bake runs the camera setup, and the guards above still protect
# a file rigged before that day). Their callbacks are gone, not disabled --
# a hotkey row pressing a button that is not there would fail at the worst
# moment, and `maya_hotkeys` lost those rows the same day.


# ------------------------------------------------------------------ window

def is_open():
    """True while our section is built in the hub (read by maya_hotkeys)."""
    return bool(cmds.control(_STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on the Characters section.

    A `cmds` control has one name per Maya session, so the panel lives in
    the hub or in a window of its own, never both - since 2026-09-17 it is
    the hub (`maya_hub`), which also closes the standalone window an older
    build may have left open. Scene Setup is two sections there, Characters
    and Weapons (the animator's ask the same evening: «декомпозируем
    scenesetup на characters и weapons»); this module stays one, because
    the two halves share `refresh`, the character resolution and the
    colour scan.
    """
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def show_weapons():
    """Open the SkeldarAnim hub on the Weapons section."""
    import maya_hub
    return maya_hub.show(HUB_WEAPONS)


def build_characters_panel():
    """The Characters section: which character, the colour, Add Character."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", 8))

    cmds.text(_BOUND, label="", align="left")

    cmds.optionMenu(_CHARACTER, label="Character",
                    annotation="What Add Character puts into the scene. "
                               "Manny [rig] is the AdvancedSkeleton rig "
                               "(one per scene) - the character the UE "
                               "Bridge retargets onto. The [skeleton] rows "
                               "are bare skeletons: Manny UE5 with geometry "
                               "and a camera bone, and the 68-bone UE4 "
                               "Mannequin the Longsword/SwordAnimsetPro "
                               "packs animate (no weapon_r, no camera_bone).",
                    changeCommand=lambda *_args: _run(character_changed,
                                                      _CHARACTER_STATUS))
    for label in catalog.character_labels():
        cmds.menuItem(label=label)

    # The swatch and its Recolour button share a row: the button acts on the
    # swatch beside it, and a full-width button of its own would read as a
    # step in the sequence rather than as that swatch's verb.
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4)])
    cmds.colorSliderGrp(_CHARACTER_COLOUR, label="Colour",
                        columnWidth3=(50, 50, 70),
                        rgbValue=colouring.PALETTE[0].rgb,
                        annotation="The colour the next Add Character will "
                                   "bring. It is refilled with the next "
                                   "unused colour after every press, so two "
                                   "characters never arrive the same even if "
                                   "you never touch it.")
    cmds.button(label="Recolour", width=90,
                annotation="Put this colour on the character that is "
                           "CONNECTED now, instead of on the next one added.",
                command=lambda *_a: _run(recolour_character,
                                         _CHARACTER_STATUS))
    cmds.setParent("..")

    cmds.button(label="Add Character", height=30,
                annotation="Import the chosen rig or skeleton into this "
                           "scene -- no manual open. Skeletons as many as "
                           "you like; the rig once per scene.",
                command=lambda *_args: _run(add_character,
                                            _CHARACTER_STATUS))
    cmds.button(label="Camera Setup", height=24,
                annotation="A camera on the character's camera_root, the "
                           "bone's animation baked onto it, the bone driven "
                           "by the camera from then on - what the retarget "
                           "does at its end. A second press bakes the bone "
                           "back and removes the camera.",
                command=lambda *_args: _run(camera_setup, _CHARACTER_STATUS))
    cmds.text(_CHARACTER_STATUS, label="", align="left", wordWrap=True,
              height=36)

    cmds.setParent("..")
    # The remembered skeleton, restored before anything reads the menu. A
    # label the table no longer carries is simply not selected, so the menu
    # stays on Manny -- the default anyone who never opens the list gets.
    remembered = remembered_character()
    if remembered and remembered in catalog.character_labels():
        cmds.optionMenu(_CHARACTER, edit=True, value=remembered)
    _run(_bound_root, _CHARACTER_STATUS)
    # The swatch opens on the colour the next Add would bring, read from
    # THIS scene. A remembered optionVar would be wrong here -- a colour
    # saved yesterday may be worn by somebody in the file opened today.
    _run(lambda: _advance_swatch(_CHARACTER_COLOUR), _CHARACTER_STATUS)
    return column


def build_weapons_panel():
    """The Weapons section: which weapon, Add / Remove, the grip, the colour.

    Built AFTER the Characters section (hub order), and `refresh` - which
    writes the Characters header - runs from here, so both sections exist
    by the time it does.
    """
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", 8))

    cmds.optionMenu(_MENU, label="Weapon",
                    changeCommand=lambda *_args: _run(refresh))
    for label in catalog.labels():
        cmds.menuItem(label=label)

    cmds.textFieldGrp(_CUSTOM, label="FBX", text=_remembered_path(),
                      columnWidth2=(60, 150), adjustableColumn=2,
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
                       columnWidth4=(60, 75, 75, 75),
                       annotation="Grip rotation relative to the weapon "
                                  "bone. Zeros put the weapon exactly on "
                                  "weapon_r.",
                       changeCommand=lambda *_args: _run(offsets_changed))
    cmds.floatFieldGrp(_TRANSLATE, numberOfFields=3, label="Translate",
                       value1=0.0, value2=0.0, value3=0.0, precision=3,
                       columnWidth4=(60, 75, 75, 75),
                       annotation="Grip position relative to the weapon "
                                  "bone. Zeros put the weapon exactly on "
                                  "weapon_r.",
                       changeCommand=lambda *_args: _run(offsets_changed))
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4)])
    cmds.colorSliderGrp(_WEAPON_COLOUR, label="Colour",
                        columnWidth3=(50, 50, 70),
                        rgbValue=colouring.PALETTE[0].rgb,
                        annotation="The colour the next Add will give the "
                                   "weapon. One palette for characters and "
                                   "weapons together, so a sword never "
                                   "arrives the colour of the hand holding "
                                   "it.")
    cmds.button(label="Recolour", width=90,
                annotation="Put this colour on the weapon already attached, "
                           "instead of on the next one added.",
                command=lambda *_a: _run(recolour_weapon))
    cmds.setParent("..")

    #  wordWrap: a long refusal must not widen the hub's whole column;
    #  two lines tall, or the wrapped second line is clipped (hub, 2026-09-17).
    cmds.text(_STATUS, label="", align="left", wordWrap=True, height=36)

    cmds.setParent("..")
    _run(refresh)
    # After refresh, which does not touch it: the swatch opens on the
    # colour the next Add would bring, read from THIS scene.
    _run(lambda: _advance_swatch(_WEAPON_COLOUR))
    return column
