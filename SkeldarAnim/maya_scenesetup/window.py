"""The Characters and Weapons cards of the hub: pick, press Add, or drag.

Two habits from the rest of this repo are load-bearing. Every callback goes
through `_run`, which puts the failure on the status line: an exception
escaping a UI callback lands in the Script Editor and the panel just looks
dead. And the grips shown are read back from the scene whenever they might
have gone stale, so the numbers on screen are never a lie about the scene.

The Weapons card IS the inventory since 2026-09-30 (the animator: «когда я
открываю вкладку weapon то у меня ... открывается наш сетчатый инвентарь с
оружием, но не в отдельном окне а как часть нашего меню»; `maya_inventory`
laid over the `_INVENTORY` placeholder): the two hands, each with its grip
as a Channel Box column, the grid, Add / Remove. A click picks a weapon or a
hand (remembered), Add puts the one into the other through `equip`, the
inventory's own path; the grips are remembered per weapon and per hand
(`grips`). No colour in it (the Colour section paints a selected weapon), no
custom FBX («кастомное оружие по указанию пути давай пока уберем совсем»).

The Characters card is a grid of portraits since 2026-09-30 (the animator:
«переделаем наше меню на сетку с портретами»; `maya_chargrid`): a
[Rig | Skeleton] switch, one portrait per model, Add Character, Camera Setup.
Its colour row went to the Colour section the same day («все что касается
покраски вынесем из меню, будем красить в меню с красками»).

Since 2026-09-07 the character is the one the SELECTION names -- any control
of the AdvancedSkeleton rig, or a joint -- then the rig, then the sole
skeleton (`skeleton.current_root`); the picker's Connect is off the shelf.
Connect Arms, Disconnect Arms, Add Aim and Camera Setup left the panel the
same day; the camera setup happens inside the retarget's Bake.
"""

import traceback

import maya.cmds as cmds

import maya_charlook as charlook
import maya_hubstyle as hubstyle
import maya_rigs
from maya_overrig import aimrig

from maya_scenesetup import attach
from maya_scenesetup import bonedrive
from maya_scenesetup import camera
from maya_scenesetup import catalog
from maya_scenesetup import character
from maya_scenesetup import connect as linking
from maya_scenesetup import connections
from maya_scenesetup import equip
from maya_scenesetup import grips
from maya_scenesetup import skeleton

HUB_SECTION = "characters"    # the Characters section of the SkeldarAnim hub
HUB_WEAPONS = "weapons"       # the Weapons section (2026-09-17, «декомпозируем»)
_STATUS = "mayaSceneSetupStatus"                    # the Weapons line
_CHARACTER_STATUS = "mayaSceneSetupCharacterStatus"  # the Characters line
_BOUND = "mayaSceneSetupBound"
_WEAPONS_BOUND = "mayaSceneSetupWeaponsBound"   # the Weapons card's subtitle
# The dropdown of every character row: only where the portrait grid cannot
# stand (no Qt) since 2026-09-30.
_CHARACTER = "mayaSceneSetupCharacter"
_PORTRAITS = "mayaSceneSetupPortraits"          # the grid is laid over it
_KIND = "mayaSceneSetupCharacterKind"           # the [Rig | Skeleton] segments
# The inventory is laid over it (2026-09-30); without Qt a weapon dropdown
# and the Hand segments stand in its place.
_INVENTORY = "mayaSceneSetupInventory"
_WEAPON_MENU = "mayaSceneSetupWeaponMenu"
_WEAPON_OPTIONVAR = "mayaSceneSetup_weapon"     # the weapon picked in the grid
# Which hand Add and Remove act on (2026-09-29, two weapons per character):
# the hand card clicked last since 2026-09-30, remembered.
_HAND = "mayaSceneSetupHand"
_HAND_OPTIONVAR = "mayaSceneSetup_hand"
HAND_LABEL = {"R": "Right", "L": "Left"}
SIDE_LABEL = {"R": "right hand", "L": "left hand"}

_CHARACTER_OPTIONVAR = "mayaSceneSetup_character"     # the old dropdown's label
_MODEL_OPTIONVAR = "mayaSceneSetup_characterModel"  # the portrait picked
_KIND_OPTIONVAR = "mayaSceneSetup_characterKind"    # rig or skeleton
KIND_LABEL = {"rig": "Rig", "skeleton": "Skeleton"}

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


# ------------------------------------------------------------------ policy

# The grip memory is `grips`' since 2026-09-29 (per weapon AND per hand, the
# left one mirrored from the right); the inventory reads it too.
optionvar_name = grips.optionvar_name
pack_offsets = grips.pack
unpack_offsets = grips.unpack


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


def missing_file_message(path):
    return "file not found: " + path


def linked_message(entry):
    return "{0} drives the arms".format(entry.label)


def attached_message(entry, bone):
    return "{0} on {1}".format(entry.label, bone.split("|")[-1])


def in_world_message(entry, bone):
    """A weapon out in world - on the floor, or lifted in Connections -
    driving this hand's bone (2026-09-29)."""
    return "{0} out in world - {1} follows it".format(entry.label,
                                                      bone.split("|")[-1])


def hand_segment(key):
    """The fallback Hand row's segment for side `key` ("R" / "L")."""
    return "{0}_{1}".format(_HAND, key)


def hand_follows_message(key, label):
    return ("the {0} follows the {1} - release it in Connections first"
            .format(SIDE_LABEL[key], label))


def pick_text(label, key):
    """What the line says when a weapon is picked in the grid. Pure."""
    return "{0} - press Add to put it into the {1}, or drag it".format(
        label, SIDE_LABEL[key])


def hand_pick_text(key, picked, held):
    """What the line says when a hand is picked: what Add and Remove will do
    there. `held` is the label of what that hand holds, "" when free. Pure."""
    if held:
        return ("the {0} holds {1} - Add replaces it with {2}, Remove takes "
                "it off".format(SIDE_LABEL[key], held, picked))
    return "the {0} is free - Add puts {1} into it".format(SIDE_LABEL[key],
                                                           picked)


def grip_note(label, key, where):
    """What an edit of a hand's grip answers when there is nothing to move
    live. `where`: "floor", "animated" or "" (an empty hand). Pure."""
    if where == "floor":
        return ("{0} lies on the floor - the grip applies in the {1}"
                .format(label, SIDE_LABEL[key]))
    if where == "animated":
        return LINKED_NO_OFFSETS
    return ("{0}'s grip in the {1} remembered - the next Add brings it"
            .format(label, SIDE_LABEL[key]))


# ------------------------------------------------------------------- state

def _stored(name):
    if cmds.optionVar(exists=name):
        return cmds.optionVar(query=name) or ""
    return ""


def chosen_weapon():
    """The weapon picked in the grid (remembered), else the catalog's first
    row - a key the catalog no longer carries falls back rather than
    raising: a preference outlives a rename of a row."""
    return catalog.by_key(_stored(_WEAPON_OPTIONVAR)) or catalog.WEAPONS[0]


def side():
    """The hand Add and Remove act on: the one picked last, else "R"."""
    value = _stored(_HAND_OPTIONVAR)
    return value if value in catalog.SIDES else "R"


def picked():
    """(weapon key, side) the card has picked - the inventory paints them."""
    return chosen_weapon().key, side()


def _bone_name(entry, key=None):
    """The drive bone of `entry` for a hand (weapon_r / weapon_l)."""
    return catalog.side_bone(entry.bone, key or side())


def _held_entry(weapon, entry):
    """The catalog row of the weapon IN the hand (its marker key), else
    `entry` - the grid names the next Add, and the hand often holds another
    weapon: its messages and its grip memory are that weapon's own."""
    key = ""
    if weapon and cmds.objExists(weapon) and cmds.attributeQuery(
            attach.MARKER, node=weapon, exists=True):
        key = cmds.getAttr(weapon + "." + attach.MARKER) or ""
    return catalog.by_key(key) or entry


def _status(message, control=_STATUS):
    """The Weapons section's line by default; character presses name
    theirs. Two sections, two lines (2026-09-17)."""
    cmds.text(control, edit=True, label=message)


def _attached(entry, key=None):
    """Root, hand, drive bone, weapon, and whether it drives the arms - for
    hand `key` (the picked one by default).

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
    bone = skeleton.resolve_bone(root, _bone_name(entry, key))
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
        return root, hand, bone, world, bool(connections.followers_of(world))
    return root, hand, bone, None, False


def _subtitle(control, text):
    """A card's subtitle; a card not built (yet) has none to write."""
    try:
        cmds.text(control, edit=True, label=text)
    except RuntimeError:
        pass


def _bound_root():
    """The character, with both cards' subtitles refreshed to match."""
    root = skeleton.current_root()
    rig = bool(root) and root == skeleton.rig_root()
    text = bound_message(root, rig)
    _subtitle(_BOUND, text)
    _subtitle(_WEAPONS_BOUND, text)
    return root


def current_character():
    """The character the presses act on (the inventory asks this)."""
    return _bound_root()


def _locate(entry, key=None):
    """Root, hand, bone, weapon and link state, or None with the status set.

    The shared front half of every weapon callback: no character, a missing
    bone and a parentless bone end the press the same way everywhere.
    """
    root, hand, bone, weapon, linked = _attached(entry, key)
    if not root:
        _status(NO_CHARACTER)
        return None
    if not bone:
        _status(missing_bone_message(root, _bone_name(entry, key)))
        return None
    if not hand:
        _status(missing_parent_message(_bone_name(entry, key)))
        return None
    return root, hand, bone, weapon, linked


def _follows(root, key):
    """The weapon hand `key`'s IK rides (Connections), or None."""
    rig = maya_rigs.rig_of(root, maya_rigs.rigs()) if root else None
    return connections.following(rig, key) if rig is not None else None


def _hand_grip(root, key, entry):
    """(rotate, translate, editable): what hand `key`'s column shows.

    Always the GRIP -- bone-relative, zeros meaning exactly on the hand's
    weapon bone -- never the animation: an animated weapon's values are
    frame values, and showing those as offsets is how a re-Add once saved
    them over the remembered grip. A clean held weapon is measured against
    the bone (`bonedrive.measured_grip`), so a sword nudged by hand in the
    viewport reads back honestly; in the socket standard (2026-09-30) - a
    weapon added before the socket turn keeps its old frame on the node and
    reads the same way. An empty hand shows the grip the PICKED weapon would
    take there: what Add or a drag would apply.
    """
    hand, bone = equip.bones(root, key) if root else (None, None)
    if not bone or not hand:
        rotate, translate = grips.for_hand(entry, key, None)
        return rotate, translate, False
    weapon, _where = equip.occupant(root, key)
    if weapon is None:
        rotate, translate = grips.for_hand(entry, key, root)
        return rotate, translate, not _follows(root, key)
    own = _held_entry(weapon, entry)
    if bonedrive.is_held(weapon) and not attach.is_animated(weapon):
        rotate, translate = bonedrive.measured_grip(weapon, bone)
        rotate, translate = grips.standard(rotate, translate,
                                           bonedrive.frame_of(weapon), own)
        return rotate, translate, True
    rotate, translate = grips.for_hand(own, key, root)
    return rotate, translate, True


def hand_grips(root):
    """{side: (rotate, translate, editable)} for the inventory's columns."""
    entry = chosen_weapon()
    return dict((key, _hand_grip(root, key, entry)) for key in catalog.SIDES)


def set_hand_grip(key, rotate, translate):
    """A hand's six values typed: remember them and, for a clean weapon held
    there, move it to the new grip. Returns (and writes) the line.

    The weapon IN the hand owns the numbers when there is one (with two
    weapons the grid may have another picked), else the picked weapon - the
    next Add of it into this hand wants them. Through `bonedrive.regrip`,
    never a plain channel write: the bone plays its own animation through
    the constraint's captured offset, and writing the weapon's channels
    under a live constraint would drag the bone along by the OLD offset.
    """
    root = skeleton.current_root()
    entry = chosen_weapon()
    hand, bone = equip.bones(root, key) if root else (None, None)
    weapon, where = equip.occupant(root, key) if bone else (None, None)
    own = _held_entry(weapon, entry) if weapon else entry
    grips.remember(own.key, key, rotate, translate)
    if weapon is None:
        text = grip_note(own.label, key, "")
    elif where == "floor":
        text = grip_note(own.label, key, "floor")
    elif not bonedrive.is_held(weapon):
        text = in_world_message(own, bone) + " - the grip applies in the hand"
    elif attach.is_animated(weapon):
        text = grip_note(own.label, key, "animated")
    else:
        # the numbers speak the standard; an older node dials in its own frame
        bonedrive.regrip(weapon, bone, *grips.on_node(
            rotate, translate, bonedrive.frame_of(weapon), own))
        text = attached_message(own, hand or bone)
    _status(text)
    return text


def say_weapon(text):
    """The Weapons card's line (the inventory writes through it too)."""
    _status(text)


def select_weapon(key):
    """A weapon picked in the grid: remember it, say what Add will do."""
    entry = catalog.by_key(key)
    if entry is None:
        return ""
    cmds.optionVar(stringValue=(_WEAPON_OPTIONVAR, entry.key))
    text = pick_text(entry.label, side())
    _status(text)
    return text


def select_hand(key):
    """A hand picked: remember it, say what Add and Remove will do there."""
    if key not in catalog.SIDES:
        return ""
    cmds.optionVar(stringValue=(_HAND_OPTIONVAR, key))
    root = skeleton.current_root()
    weapon = equip.occupant(root, key)[0] if root else None
    held = connections.weapon_label(weapon) if weapon else ""
    text = hand_pick_text(key, chosen_weapon().label, held)
    _status(text)
    return text


def _inventory():
    """The inventory standing in the card, or None."""
    try:
        import maya_inventory
        return maya_inventory.live(_INVENTORY)
    except Exception:                                        # noqa: BLE001
        return None


def _refresh_inventory():
    """The inventory re-read after a press changed the hands. Its scriptJobs
    are not enough: an import changes the selection MIDWAY, and the refresh
    they queue can run then and show a half-attached weapon's grip (measured
    live 2026-09-30, the left column read zeros under a mirrored grip)."""
    panel = _inventory()
    if panel is not None:
        panel.refresh()


# --------------------------------------------------------------- callbacks

def _run(action, status=_STATUS):
    """Run a callback, and put anything it throws on its section's line."""
    try:
        action()
    except Exception:
        _status(traceback.format_exc().strip().splitlines()[-1], status)
        raise


def refresh():
    """Re-read the scene: the character, the inventory, and the picked hand's
    state on the Weapons line."""
    entry = chosen_weapon()
    root, hand, bone, weapon, linked = _attached(entry)
    panel = _inventory()
    if panel is not None:
        panel.refresh()
    if weapon:
        own = _held_entry(weapon, entry)
        if linked:
            _status(linked_message(own))
        elif bonedrive.is_held(weapon):
            _status(attached_message(own, hand or bone))
        else:
            _status(in_world_message(own, bone))
    elif not root:
        _status(NO_CHARACTER)
    elif not bone:
        _status(missing_bone_message(root, _bone_name(entry)))
    elif not hand:
        _status(missing_parent_message(_bone_name(entry)))
    else:
        _status(pick_text(entry.label, side()))


def kind_segment(kind):
    """The [Rig | Skeleton] row's segment for `kind`."""
    return "{0}_{1}".format(_KIND, kind)


def choice_from(model, kind, label):
    """(model, kind) the card opens on: the stored pair, else the row the old
    dropdown remembered (its label), else the default rig. Pure. A stored
    model the catalog no longer carries falls back rather than raising: a
    preference outlives a rename of a row."""
    fallback = catalog.character_by_label(label or "") or catalog.default_rig()
    if catalog.model_by_key(model or "") is None:
        model = fallback.model
    if kind not in catalog.KINDS:
        kind = fallback.kind
    return model, kind


def remembered_choice():
    """The (model, kind) picked last, from the optionVars."""
    return choice_from(_stored(_MODEL_OPTIONVAR), _stored(_KIND_OPTIONVAR),
                       remembered_character())


def chosen_character():
    """The catalog row Add Character imports.

    From the old dropdown where it stands (the grid could not be built: no
    Qt) -- its label, or the default rig (2026-09-07, «Add character теперь
    должен добавлять наш адванцед скелетон риг»). Otherwise the chosen model
    in the chosen kind, which is None when the model has no such row (Orc D
    has no skeleton, the UE4 Mannequin no rig): Add refuses it by name.
    """
    if cmds.optionMenu(_CHARACTER, exists=True):
        label = cmds.optionMenu(_CHARACTER, query=True, value=True) or ""
        return catalog.character_by_label(label) or catalog.default_rig()
    model, kind = remembered_choice()
    return catalog.character_for(model, kind)


def _absent_choice():
    model, kind = remembered_choice()
    return charlook.absent_text(catalog.model_by_key(model).label, kind)


def say_character(text):
    """The Characters card's line (the grid writes through it too)."""
    _status(text, _CHARACTER_STATUS)


def _say_choice():
    entry = chosen_character()
    say_character(charlook.import_text(entry.label) if entry
                  else _absent_choice())


def select_model(model):
    """A portrait clicked: remember it, say what Add will import."""
    cmds.optionVar(stringValue=(_MODEL_OPTIONVAR, model))
    _say_choice()


def _grid():
    """The portrait grid standing in the card, or None."""
    try:
        import maya_chargrid
        return maya_chargrid.live(_PORTRAITS)
    except Exception:                                        # noqa: BLE001
        return None


def kind_changed(kind):
    """A Rig / Skeleton segment's onCommand: remember it, dim the grid."""
    def go(*_args):
        cmds.optionVar(stringValue=(_KIND_OPTIONVAR, kind))
        grid = _grid()
        if grid is not None:
            grid.set_kind(kind)
        _run(_say_choice, _CHARACTER_STATUS)
    return go


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
    """Import the chosen character at the origin, then catch the UI up.

    The status is written LAST: `refresh` ends by writing its own line, and
    the outcome of the press must be what stays on screen. The refresh is
    what flips the header to the new character -- a lone skeleton binds
    through `skeleton.current_root` with no press of anything.

    No colour is passed since 2026-09-30 («все что касается покраски
    вынесем из меню, будем красить в меню с красками»): the character
    arrives in the next free palette colour, so two presses in a row never
    collide, and the Colour section repaints the selection -- Add leaves the
    new rig's Main selected. A model without a row of the chosen kind is
    refused by name, nothing imported.
    """
    entry = chosen_character()
    if entry is None:
        say_character(_absent_choice())
        return
    message = character.add_character(entry)
    refresh()
    say_character(message)


def place_character(model, kind, point):
    """A portrait dropped on the floor (2026-09-30, «зажать на портрете и
    перетащить его в сцену»): the character added standing at `point`.
    Returns what the line says -- the grid shows it too."""
    entry = catalog.character_for(model, kind)
    if entry is None:
        found = catalog.model_by_key(model)
        text = charlook.absent_text(found.label if found else model, kind)
        say_character(text)
        return text
    message = character.add_character(entry, at=point)
    try:
        refresh()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    say_character(message)
    return message


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


def _weapon_front(key, linked_text):
    """(root, weapon in the hand) for Add / Remove on hand `key`, or None
    with the refusal on the line - the character, the bone, its parent, the
    legacy OverRig link, an aim on the weapon standing there."""
    entry = chosen_weapon()
    located = _locate(entry, key)
    if located is None:
        return None
    root, _hand, _bone, weapon, _linked = located
    if linking.linked_weapon():
        # The OverRig-rig kind: the IK hand controls are the weapon's DAG
        # children, so replacing or removing it would take both arm rigs
        # down unbaked.
        _status(linked_text)
        return None
    if weapon and aimrig.aim_for(attach.model_root(weapon)):
        # The aim's locators drive the geometry: replacing it leaves them
        # pointing at a deleted node.
        _status(AIMED_NO_ADD)
        return None
    return root, weapon


def add_weapon():
    """The weapon picked in the grid into the picked hand, replacing what
    that hand held - the inventory's own path (`equip.to_hand`): the grip
    that hand remembers for that weapon, whatever the hand held or its bone
    followed taken off first, one undo chunk. No colour is chosen here since
    2026-09-30: the weapon arrives in the next free one, and the Colour
    section repaints a selected weapon."""
    key = side()
    front = _weapon_front(key, LINKED_NO_ADD)
    if front is None:
        return
    root, _weapon = front
    text = equip.to_hand(root, key, chosen_weapon())
    _refresh_inventory()
    _status(text)


def remove_weapon():
    """Take the picked hand's weapon off: the bone gets its animation back,
    the weapon goes (`equip.take_off`).

    Forced by the inverted drive: deleting the sword by hand would lose the
    bone's animation (it lives on the sword) and leave an orphaned
    constraint under the bone (trap 4).
    """
    key = side()
    front = _weapon_front(key, LINKED_NO_REMOVE)
    if front is None:
        return
    root, _weapon = front
    text = equip.take_off(root, key)
    _refresh_inventory()
    _status(text)


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


def _kind_row(kind):
    """`[Rig | Skeleton]`: which kind a portrait brings (2026-09-30). Segments
    like the Hand row; the choice is remembered."""
    segments = cmds.rowLayout(numberOfColumns=2,
                              columnAttach=[(1, "both", 1), (2, "both", 1)])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(_KIND)
    for each in catalog.KINDS:
        hubstyle.mark(cmds.iconTextRadioButton(
            kind_segment(each), style="textOnly", label=KIND_LABEL[each],
            height=22, select=each == kind,
            annotation=("The portraits bring the AdvancedSkeleton rig - what "
                        "the UE Bridge retargets onto" if each == "rig" else
                        "The portraits bring the bare skeleton"),
            onCommand=kind_changed(each)), "segment")
    cmds.setParent("..")


def _attach_grid(model, kind):
    """The portrait grid laid over the placeholder; False where it cannot
    stand (no Qt) - the card then shows the old dropdown."""
    try:
        import maya_chargrid
        return maya_chargrid.attach(_PORTRAITS, kind=kind,
                                    selected=model) is not None
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return False


def _character_dropdown():
    """Every character row in one dropdown: the card without Qt."""
    cmds.optionMenu(_CHARACTER,
                    annotation="What Add Character puts into the scene. "
                               "The [rig] rows are AdvancedSkeleton rigs - "
                               "the characters the UE Bridge retargets onto; "
                               "the [skeleton] rows are bare skeletons.",
                    changeCommand=lambda *_args: _run(character_changed,
                                                      _CHARACTER_STATUS))
    for label in catalog.character_labels():
        cmds.menuItem(label=label)
    # A label the table no longer carries is simply not selected, so the
    # menu stays on the rig -- the default anyone who never opens it gets.
    remembered = remembered_character()
    if remembered and remembered in catalog.character_labels():
        cmds.optionMenu(_CHARACTER, edit=True, value=remembered)


def build_characters_panel():
    """The Characters section: which character, the portraits, Add Character.

    2026-09-30 («сетка с портретами, как меню выбора героев в Mortal Kombat
    или Dota 2»): a [Rig | Skeleton] switch over one square portrait per
    model (`maya_chargrid`, laid over the `_PORTRAITS` placeholder); a click
    picks, Add Character imports, a portrait dragged into a viewport adds
    the character where it lands. No colour here: the Colour section paints.
    The character line is the card's subtitle (2026-09-28).
    """
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))

    hubstyle.mark(cmds.text(_BOUND, label="", align="left"), "subtitle")

    model, kind = remembered_choice()
    _kind_row(kind)
    cmds.columnLayout(_PORTRAITS, adjustableColumn=True)
    cmds.setParent("..")
    if not _attach_grid(model, kind):
        _character_dropdown()

    hubstyle.mark(cmds.button(
        label="Add Character", height=32,
        annotation="Import the picked rig or skeleton into this scene, at "
                   "the origin -- or drag its portrait into a viewport to "
                   "stand it where it lands. As many as you like, each rig "
                   "in its own namespace; the Colour section repaints it.",
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
    _run(_bound_root, _CHARACTER_STATUS)
    _run(_say_choice, _CHARACTER_STATUS)
    return column


def _attach_inventory():
    """The inventory laid over the placeholder; False where it cannot stand
    (no Qt) - the card then shows a weapon dropdown and the Hand row."""
    try:
        import maya_inventory
        return maya_inventory.attach(_INVENTORY) is not None
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return False


def weapon_menu_changed(*_args):
    """The fallback dropdown: the weapon it names is the picked one."""
    entry = catalog.by_label(cmds.optionMenu(_WEAPON_MENU, query=True,
                                             value=True) or "")
    if entry is not None:
        select_weapon(entry.key)


def hand_changed(key):
    """A fallback Hand segment's onCommand: the hand it names is picked."""
    def go(*_args):
        _run(lambda: select_hand(key))
    return go


def _weapon_fallback():
    """Without Qt: the weapon as a dropdown and `Hand [Right | Left]`, both
    writing the choice the inventory would, so Add and Remove still work."""
    cmds.optionMenu(_WEAPON_MENU, annotation="The weapon Add brings",
                    changeCommand=lambda *_a: _run(weapon_menu_changed))
    for label in catalog.labels():
        cmds.menuItem(label=label)
    cmds.optionMenu(_WEAPON_MENU, edit=True, value=chosen_weapon().label)
    start = side()
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
            annotation="Add and Remove act on the {0}".format(SIDE_LABEL[key]),
            onCommand=hand_changed(key)), "segment")
    cmds.setParent("..")
    cmds.setParent("..")


def build_weapons_panel():
    """The Weapons section: the inventory, Add / Remove, the line.

    2026-09-30 («сам выбор оружия превратим в наш инвентарь ... не в
    отдельном окне а как часть нашего меню»): the two hands, each with its
    grip as a Channel Box column, and the grid (`maya_inventory`, laid over
    the `_INVENTORY` placeholder); a click picks a weapon or a hand, Add puts
    the one into the other, a drag does it too - onto a hand in the viewport
    or the floor. Built AFTER the Characters section (hub order); its
    `refresh` writes both cards' subtitles.
    """
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))

    hubstyle.mark(cmds.text(_WEAPONS_BOUND, label="", align="left"),
                  "subtitle")
    cmds.columnLayout(_INVENTORY, adjustableColumn=True)
    cmds.setParent("..")
    if not _attach_inventory():
        _weapon_fallback()

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "left", 4)])
    hubstyle.mark(cmds.button(
        label="Add", height=32,
        annotation="Put the weapon picked in the grid into the picked hand, "
                   "at the grip that hand's column shows, move any "
                   "weapon-bone animation onto it and drive the bone from "
                   "the weapon. Replaces what that hand held, animation "
                   "preserved.",
        command=lambda *_args: _run(add_weapon)), "primary", "plus")
    hubstyle.mark(cmds.button(
        label="Remove Weapon", height=32, width=130,
        annotation="Bake the picked hand's weapon-bone animation back from "
                   "its weapon, then delete the weapon and its constraint. "
                   "Deleting the sword by hand instead loses that animation.",
        command=lambda *_args: _run(remove_weapon)), "danger", "trash")
    cmds.setParent("..")

    #  wordWrap: a long refusal must not widen the hub's whole column;
    #  two lines tall, or the wrapped second line is clipped (hub, 2026-09-17).
    hubstyle.mark(cmds.text(_STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")

    cmds.setParent("..")
    _run(refresh)
    return column
