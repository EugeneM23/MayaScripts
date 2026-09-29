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

import maya_hubstyle as hubstyle
import maya_rigs
from maya_overrig import aimrig

from maya_scenesetup import attach
from maya_scenesetup import bonedrive
from maya_scenesetup import camera
from maya_scenesetup import catalog
from maya_scenesetup import character
from maya_scenesetup import colour as colouring
from maya_scenesetup import connect as linking
from maya_scenesetup import grips
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
_CHARACTER_DOT = "mayaSceneSetupCharDot{0}"     # the palette dots (2026-09-28)
_WEAPON_DOT = "mayaSceneSetupWeaponDot{0}"
_BROWSE = "mayaSceneSetupBrowseFbx"
# Which hand the Weapons presses act on (2026-09-29, two weapons per
# character): a segment row under the weapon list, remembered.
_HAND = "mayaSceneSetupHand"
_HAND_OPTIONVAR = "mayaSceneSetup_hand"
HAND_LABEL = {"R": "Right", "L": "Left"}
SIDE_LABEL = {"R": "right hand", "L": "left hand"}

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

# The grip memory is `grips`' since 2026-09-29 (per weapon AND per hand, the
# left one mirrored from the right); the inventory reads it too.
optionvar_name = grips.optionvar_name
pack_offsets = grips.pack
unpack_offsets = grips.unpack


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
    #  No "Character:" prefix since 2026-09-28: in the skin this line is the
    #  subtitle of a card that already says Characters.
    return "{0} ({1})".format(root.split("|")[-1],
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


def appearance(entry, rgb, switched):
    """What an Add says the weapon arrived wearing: its colour's name, or
    «textured» for a row that arrives in its image (2026-09-28), with the
    viewport's Textures named when this press turned them on. Pure."""
    if not getattr(entry, "texture", ""):
        return colouring.colour_name(rgb)
    if switched:
        return "textured (viewport textures on)"
    return "textured"


def linked_message(entry):
    return "{0} drives the arms".format(entry.label)


def attached_message(entry, bone):
    return "{0} on {1}".format(entry.label, bone.split("|")[-1])


def in_world_message(entry, bone):
    """A weapon out in world - on the floor, or lifted in Connections -
    driving this hand's bone (2026-09-29)."""
    return "{0} out in world - {1} follows it".format(entry.label,
                                                      bone.split("|")[-1])


def recoloured_message(what, rgb):
    return "{0} is now {1}".format(what.split("|")[-1],
                                   colouring.colour_name(rgb))


def hand_segment(key):
    """The Hand row's segment for side `key` ("R" / "L")."""
    return "{0}_{1}".format(_HAND, key)


def hand_follows_message(key, label):
    return ("the {0} follows the {1} - release it in Connections first"
            .format(SIDE_LABEL[key], label))


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


def side():
    """The hand the Weapons presses act on: the segment picked, else "R"."""
    chosen = (cmds.iconTextRadioCollection(_HAND, query=True, select=True)
              or "").split("|")[-1]
    for key in catalog.SIDES:
        if chosen == hand_segment(key):
            return key
    return "R"


def _remembered_side():
    if cmds.optionVar(exists=_HAND_OPTIONVAR):
        value = cmds.optionVar(query=_HAND_OPTIONVAR)
        if value in catalog.SIDES:
            return value
    return "R"


def _bone_name(entry):
    """The drive bone of `entry` for the chosen hand (weapon_r / weapon_l)."""
    return catalog.side_bone(entry.bone, side())


def _remembered(entry, root):
    """The grip the chosen hand gives this weapon: dialled, or - the left
    hand - the right one's mirror (`grips.for_hand`). Bone-relative."""
    return grips.for_hand(entry, side(), root)


def _remembered_path():
    """The FBX path this window was last pointed at, or ""."""
    if cmds.optionVar(exists=_CUSTOM_OPTIONVAR):
        return cmds.optionVar(query=_CUSTOM_OPTIONVAR) or ""
    return ""


def _remember(entry, rotate, translate):
    grips.remember(entry.key, side(), rotate, translate)


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
    bone = skeleton.resolve_bone(root, _bone_name(entry))
    if not bone:
        return root, None, None, None, False
    hand = attach.parent_bone(bone)

    in_hand = attach.find_attached(hand) if hand else None
    attached_now = in_hand or attach.find_attached(bone)
    if attached_now:
        return root, hand, bone, attached_now, False

    # Out in world: the OverRig-rig kind hangs the IK hands under the marked
    # node (`linking`) - the hands ride it; the AdvancedSkeleton kind
    # (`connections`, 2026-09-18) and a weapon on the floor (2026-09-29) leave
    # it driving the bone from world. That one is "linked" - refused by Add
    # and Remove - only while a hand's IK actually rides it: one nothing
    # rides is this hand's weapon to replace or take off.
    legacy = linking.linked_weapon()
    if legacy:
        return root, hand, bone, legacy, True
    world = bonedrive.driving_weapon(bone)
    if world:
        from maya_scenesetup import connections
        return root, hand, bone, world, bool(connections.followers_of(world))
    return root, hand, bone, None, False


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
        _status(missing_bone_message(root, _bone_name(entry)))
        return None
    if not hand:
        _status(missing_parent_message(_bone_name(entry)))
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
        held = bonedrive.is_held(weapon)
        if bone and held and not attach.is_animated(weapon):
            _set_fields(*bonedrive.measured_grip(weapon, bone))
        else:
            _set_fields(*_remembered(entry, root))
        if linked:
            _status(linked_message(entry))
        elif held:
            _status(attached_message(entry, hand or bone))
        else:
            _status(in_world_message(entry, bone))
        return

    _set_fields(*_remembered(entry, root))
    if not root:
        _status(NO_CHARACTER)
    elif not bone:
        _status(missing_bone_message(root, _bone_name(entry)))
    elif not hand:
        _status(missing_parent_message(_bone_name(entry)))
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
    entry = chosen_character()
    message = character.add_character(entry, _swatch(_CHARACTER_COLOUR))
    refresh()
    if not getattr(entry, "textured", False):
        # A textured row (2026-09-28, the Orc D) used no colour, so the one
        # picked is still the next coloured Add's -- Weapons > Add's rule.
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
    root, hand, bone, attached_now, linked = located
    if linked:
        # Replacing deletes the weapon, and the IK hand controls are its DAG
        # children: this press would take both arm rigs down unbaked.
        _status(LINKED_NO_ADD)
        return
    rides = _rides(root)
    if rides:
        # A hand holds XOR follows (2026-09-29): a weapon hung in a hand whose
        # IK rides another weapon could close a loop with the other hand.
        _status(rides)
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
    switched = []
    if getattr(entry, "texture", ""):
        # No colour was used, so the swatch stays; and a textured material
        # reads flat grey until the viewport shows textures.
        switched = colouring.show_textures()
    else:
        _advance_swatch(_WEAPON_COLOUR)

    message = added_message(entry, hand) + " - " + appearance(entry, rgb,
                                                              switched)
    _status(message + " - " + note if note else message)


def _rides(root):
    """The refusal when the chosen hand's IK rides a weapon, else ""."""
    rig = maya_rigs.rig_of(root, maya_rigs.rigs()) if root else None
    if rig is None:
        return ""
    from maya_scenesetup import connections
    weapon = connections.following(rig, side())
    if not weapon:
        return ""
    return hand_follows_message(side(), connections.weapon_label(weapon))


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
    if not bonedrive.is_held(weapon):
        # On the floor (2026-09-29): no grip to dial - the numbers wait for
        # the next time this weapon goes into this hand.
        _status(in_world_message(entry, bone) + " - the grip applies in the hand")
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


def browse_fbx():
    """The folder button beside the weapon list: pick any .fbx and it goes
    into the FBX field, exactly as a pasted path would. Cancel: nothing."""
    picked = cmds.fileDialog2(fileMode=1, caption="Attach an FBX",
                              fileFilter="FBX (*.fbx *.FBX)")
    if not picked:
        return None
    cmds.textFieldGrp(_CUSTOM, edit=True, text=picked[0])
    custom_changed()
    return picked[0]


def pick_dot(slider, rgb):
    """A palette dot pressed: its colour into the swatch beside it -- the
    colour of the next Add. Nothing in the scene changes."""
    _set_swatch(slider, rgb)
    return rgb


def _colour_row(slider, dot_name, annotation, recolour, recolour_note,
                status):
    """The palette as eight dots, the swatch, the brush that Recolours.

    One row: the dots choose the next Add's colour, the swatch shows it (and
    opens Maya's chooser for any other), the brush puts it on what is in the
    scene. The skin shows the swatch alone (`swatchonly`); the classic hub
    keeps the swatch's slider.
    """
    count = len(colouring.PALETTE)
    attach_ = [(i + 1, "left", 2) for i in range(count)]
    attach_ += [(count + 1, "left", 6), (count + 2, "right", 0)]
    cmds.rowLayout(numberOfColumns=count + 2, adjustableColumn=count + 1,
                   columnAttach=attach_)
    for index, entry in enumerate(colouring.PALETTE):
        hubstyle.swatch(cmds.button(
            dot_name.format(index), label="", width=18, height=18,
            backgroundColor=entry.rgb,
            annotation="the next Add brings " + entry.name,
            command=lambda *_a, rgb=entry.rgb: _run(
                lambda: pick_dot(slider, rgb), status)), entry.rgb)
    #  the skin hides the slider, so it gets no width there: the row has to
    #  fit a 360 px dock (measured 2026-09-28, 29 px too wide with it)
    hubstyle.mark(cmds.colorSliderGrp(
        slider, label="", columnWidth3=hubstyle.pick((1, 30, 1), (1, 34, 60)),
        rgbValue=colouring.PALETTE[0].rgb, annotation=annotation),
        "swatchonly")
    hubstyle.mark(cmds.button(
        label=hubstyle.tool_label("Recolour"),
        width=hubstyle.tool_width(80), height=24, annotation=recolour_note,
        command=lambda *_a: _run(recolour, status)), "tool", "brush")
    cmds.setParent("..")


def build_characters_panel():
    """The Characters section: which character, the colour, Add Character.

    2026-09-28 (the skin): the character line is the card's subtitle, the
    dropdown needs no label under a card called Characters, the palette is
    eight dots, and Add Character is the section's one primary action.
    """
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))

    hubstyle.mark(cmds.text(_BOUND, label="", align="left"), "subtitle")

    cmds.optionMenu(_CHARACTER,
                    annotation="What Add Character puts into the scene. "
                               "The [rig] rows are AdvancedSkeleton rigs - "
                               "the characters the UE Bridge retargets onto; "
                               "the [skeleton] rows are bare skeletons.",
                    changeCommand=lambda *_args: _run(character_changed,
                                                      _CHARACTER_STATUS))
    for label in catalog.character_labels():
        cmds.menuItem(label=label)

    _colour_row(_CHARACTER_COLOUR, _CHARACTER_DOT,
                "The colour the next Add Character will bring. It is "
                "refilled with the next unused colour after every press, so "
                "two characters never arrive the same even if you never "
                "touch it.",
                recolour_character,
                "Recolour: put this colour on the character that is "
                "CONNECTED now, instead of on the next one added.",
                _CHARACTER_STATUS)

    hubstyle.mark(cmds.button(
        label="Add Character", height=32,
        annotation="Import the chosen rig or skeleton into this scene -- no "
                   "manual open. As many as you like, each rig in its own "
                   "namespace.",
        command=lambda *_args: _run(add_character, _CHARACTER_STATUS)),
        "primary", "plus")
    hubstyle.mark(cmds.button(
        label="Camera Setup", height=26,
        annotation="A camera on the character's camera_root, the bone's "
                   "animation baked onto it, the bone driven by the camera "
                   "from then on - what the retarget does at its end. A "
                   "second press bakes the bone back and removes the camera.",
        command=lambda *_args: _run(camera_setup, _CHARACTER_STATUS)),
        "secondary", "camera")
    hubstyle.mark(cmds.text(_CHARACTER_STATUS, label="", align="left",
                            wordWrap=True, height=36), "status")

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


def open_inventory():
    """The weapon inventory window (maya_inventory), over Maya."""
    import maya_inventory
    maya_inventory.show()


def hand_changed(key):
    """A Hand segment's onCommand: remember the hand, re-read the fields."""
    def go(*_args):
        cmds.optionVar(stringValue=(_HAND_OPTIONVAR, key))
        _run(refresh)
    return go


def _hand_row():
    """`Hand [Right | Left]`: which hand Add, Remove, the grip fields and
    Recolour act on (2026-09-29, two weapons per character). Segments, like
    Connections' rows; the choice is remembered."""
    start = _remembered_side()
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(64, 120),
                   columnAttach=[(1, "left", 0), (2, "both", 4)])
    cmds.text(label="Hand", align="left")
    segments = cmds.rowLayout(numberOfColumns=2,
                              columnAttach=[(1, "both", 1), (2, "both", 1)])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(_HAND)
    for key in catalog.SIDES:
        hubstyle.mark(cmds.iconTextRadioButton(
            hand_segment(key), style="textOnly", label=HAND_LABEL[key],
            height=22, select=key == start,
            annotation="Add, Remove, the grip and Recolour act on the {0}"
                       .format(SIDE_LABEL[key]),
            onCommand=hand_changed(key)), "segment")
    cmds.setParent("..")
    cmds.setParent("..")


def build_weapons_panel():
    """The Weapons section: which weapon, Add / Remove, the grip, the colour.

    Built AFTER the Characters section (hub order), and `refresh` - which
    writes the Characters header - runs from here, so both sections exist
    by the time it does. 2026-09-28 (the skin): a folder button picks any
    FBX, Add and Remove share a row, the palette is dots.
    """
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "left", 4)])
    cmds.optionMenu(_MENU, annotation="The weapon Add brings, and the bone "
                                      "it drives",
                    changeCommand=lambda *_args: _run(refresh))
    for label in catalog.labels():
        cmds.menuItem(label=label)
    hubstyle.mark(cmds.button(
        _BROWSE, label=hubstyle.tool_label("FBX..."),
        width=hubstyle.tool_width(50), height=24,
        annotation="Pick any .fbx to attach instead of the weapon in the "
                   "list",
        command=lambda *_args: _run(browse_fbx)), "tool", "folder")
    cmds.setParent("..")

    _hand_row()

    cmds.textFieldGrp(_CUSTOM, label="FBX", text=_remembered_path(),
                      columnWidth2=(40, 150), adjustableColumn=2,
                      annotation="Paste the path to any .fbx to attach it "
                                 "instead of the weapon in the dropdown. The "
                                 "bone comes from the dropdown; the scale is "
                                 "1. Clear the field to go back to the list.",
                      changeCommand=lambda *_args: _run(custom_changed))

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "left", 4)])
    hubstyle.mark(cmds.button(
        label="Add", height=32,
        annotation="Import the weapon into the hand, move any weapon-bone "
                   "animation onto it, and drive the bone from the weapon. "
                   "Replaces what a previous Add put there, animation "
                   "preserved.",
        command=lambda *_args: _run(add_weapon)), "primary", "plus")
    hubstyle.mark(cmds.button(
        label="Remove Weapon", height=32, width=130,
        annotation="Bake the weapon bone's animation back from the weapon, "
                   "then delete the weapon and its constraint. Deleting the "
                   "sword by hand instead loses that animation.",
        command=lambda *_args: _run(remove_weapon)), "danger", "trash")
    cmds.setParent("..")

    hubstyle.mark(cmds.button(
        label="Inventory", height=28,
        annotation="The weapon inventory: drag a weapon onto a hand in the "
                   "viewport, or onto the floor (2026-09-29)",
        command=lambda *_args: _run(open_inventory)), "secondary", "backpack")

    cmds.floatFieldGrp(_ROTATE, numberOfFields=3, label="Rotate",
                       value1=0.0, value2=0.0, value3=0.0, precision=3,
                       columnWidth4=(64, 70, 70, 70),
                       annotation="Grip rotation relative to the weapon "
                                  "bone. Zeros put the weapon exactly on "
                                  "the hand's weapon bone (weapon_r / weapon_l).",
                       changeCommand=lambda *_args: _run(offsets_changed))
    cmds.floatFieldGrp(_TRANSLATE, numberOfFields=3, label="Translate",
                       value1=0.0, value2=0.0, value3=0.0, precision=3,
                       columnWidth4=(64, 70, 70, 70),
                       annotation="Grip position relative to the weapon "
                                  "bone. Zeros put the weapon exactly on "
                                  "the hand's weapon bone (weapon_r / weapon_l).",
                       changeCommand=lambda *_args: _run(offsets_changed))

    _colour_row(_WEAPON_COLOUR, _WEAPON_DOT,
                "The colour the next Add will give the weapon. One palette "
                "for characters and weapons together, so a sword never "
                "arrives the colour of the hand holding it.",
                recolour_weapon,
                "Recolour: put this colour on the weapon already attached, "
                "instead of on the next one added.",
                _STATUS)

    #  wordWrap: a long refusal must not widen the hub's whole column;
    #  two lines tall, or the wrapped second line is clipped (hub, 2026-09-17).
    hubstyle.mark(cmds.text(_STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")

    cmds.setParent("..")
    _run(refresh)
    # After refresh, which does not touch it: the swatch opens on the
    # colour the next Add would bring, read from THIS scene.
    _run(lambda: _advance_swatch(_WEAPON_COLOUR))
    return column
