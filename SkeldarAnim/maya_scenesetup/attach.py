"""Put a weapon model into the hand, and drive its export bone from it.

**The weapon is the geometry** -- the mesh transform itself is what gets
parented, marked and offset, so one click in the viewport selects the thing
that moves. A file that arrives wrapped in a null loses the null; that null
is exactly the group the animator asked not to have.

Since 2026-08-21 the drive is inverted: the mesh parents under the drive
bone's own PARENT (hand_r on Manny), any moving animation `weapon_r` carried
is baked onto the mesh (with the dialled grip kept on top), and the bone is
then parent-constrained to it (`bonedrive.link`, mo=True -- the captured
offset is the grip's inverse, so the bone keeps playing its ORIGINAL
animation while the sword sits at the grip; the user's 2026-08-25 ruling).
It has to be the hand: a node cannot both parent the weapon and follow it,
that is a cycle. The animator animates the sword; the export bone follows
at the grip's inverse, so what exports is the clip the scene came with plus
whatever the animator does to the sword -- never the grip itself.

A file holding no mesh, or several, keeps a group of ours instead: two meshes
cannot both be the node the offsets live on, and one click cannot select both.

**Since 2026-09-24 the weapon is not inside the skeleton at all** («не нарушали
иерархию нашего скелета»): it is a child of the hand's WEAPON SPACE
(`weaponspace`), a transform outside the skeleton parent-constrained to the
hand with no offset. The space stands exactly where the hand does, so the
weapon's channels still mean "relative to the hand" and nothing else in this
design changed -- while an export of the skeleton no longer carries the
weapon's mesh (it did: 10890 vertices and a material in an animation FBX). A
weapon a file from before holds directly under the hand is still found and
still comes off.

Either way there is exactly ONE marked node per bone, and it is found by a
string attribute, never by name. Maya uniquifies imported names, the animator
may rename anything, and every tool in this repo that identified a node by
name has paid for it.
"""

import maya.cmds as cmds

from maya_scenesetup import bonedrive
from maya_scenesetup import colour as colouring
from maya_scenesetup import fbximport
from maya_scenesetup import weaponspace

# The marker moved into bonedrive (the leaf) so the bridge can read it
# without importing this module; every existing reader of attach.MARKER
# keeps working through this re-export.
MARKER = bonedrive.MARKER

# The file a weapon came from, on the marked node (2026-09-29): the inventory
# puts the same weapon into another hand by importing it again, and a custom
# FBX has no catalog row to find it by.
SOURCE = "mayaWeaponSource"

# The nodes the last `import_model` brought (2026-10-01): the weapon records them for
# Characters > Delete -- its FBX materials the palette unassigns are connected to nothing of it.
_LAST_IMPORT = []

# Everything that can hold an offset between a node and its parent. Zeroing
# translate and rotate is not enough: a pivot sits at the centre of the
# geometry, and parenting compensates for it in rotatePivotTranslate -- so the
# node reads t=0 r=0 and hangs 28 cm off the bone. Measured.
#
# Seating the geometry means the artist's own transform on the model root goes
# too. One node cannot both hold our offsets and preserve theirs, and offsets
# that are not the node's own channels would make the fields on screen a lie
# about the scene. The grip is dialled once and remembered in an optionVar.
_SEATED_AT_ZERO = ("translate", "rotate", "shear",
                   "rotatePivot", "rotatePivotTranslate",
                   "scalePivot", "scalePivotTranslate", "rotateAxis")


def group_name(key):
    """Name for the fallback group, used only when no single mesh arrived."""
    return "{0}_weapon".format(key)


def seat(node, scale=1.0):
    """Put `node` exactly on its parent: local matrix identity, then scale."""
    for channel in _SEATED_AT_ZERO:
        cmds.setAttr("{0}.{1}".format(node, channel), 0.0, 0.0, 0.0,
                     type="double3")
    cmds.setAttr(node + ".scale", scale, scale, scale, type="double3")


def outermost(paths):
    """The paths with no ancestor among the others.

    The trailing separator is the whole test: `|swordExtra` is not a child of
    `|sword`, and a plain startswith would swallow it.
    """
    return [path for path in paths
            if not any(path.startswith(other + "|")
                       for other in paths if other != path)]


def mesh_transforms(paths):
    """The transforms at or below `paths` that hold a mesh shape.

    Deduplicated, in order. This is the decision that says whether Add needs
    a group at all: exactly one mesh transform is the weapon itself, and
    everything else the file brought is scaffolding.
    """
    found = []
    for path in paths:
        candidates = [path] + (cmds.listRelatives(
            path, allDescendents=True, type="transform", fullPath=True) or [])
        for candidate in candidates:
            if (candidate not in found
                    and cmds.listRelatives(candidate, children=True,
                                           type="mesh")):
                found.append(candidate)
    return found


def _marked_child(node):
    for child in cmds.listRelatives(node, children=True, type="transform",
                                    fullPath=True) or []:
        if cmds.attributeQuery(MARKER, node=child, exists=True):
            return child
    return None


def find_attached(bone):
    """The weapon this module put in `bone`'s hand, or None: the marked child
    of the space that follows `bone`, else -- a file from before 2026-09-24 --
    a marked child of the bone itself."""
    space = weaponspace.space_of(bone)
    if space:
        found = _marked_child(space)
        if found:
            return found
    return _marked_child(bone)


def parent_bone(bone):
    """The bone the weapon parents under: the drive bone's own DAG parent.

    On Manny that is hand_r -- and resolving it as "weapon_r's parent" rather
    than by name keeps a UE4-schema rig, a prefix or a weapon_l entry working
    with no new table.
    """
    parents = cmds.listRelatives(bone, parent=True, fullPath=True) or []
    return parents[0] if parents else None


def detach(parent_bone_path, drive_bone):
    """Take off the weapon this hand holds or this bone follows, and give the
    bone its animation back.

    Unlink FIRST: the bone's motion lives on the weapon while the link
    stands, and deleting the weapon first would take it away (the camera's
    second press, same order). Looked for in the hand's space, under the bone
    (a sword parented under weapon_r by the old version), and -- since
    2026-09-29 -- as the node driving the bone from world: a weapon on the
    floor, or lifted in Connections. One that PARKED the bone's own track (a
    floor drop, `bonedrive.park`) hands it back verbatim instead of a bake.
    The caller refuses a weapon hands ride before calling this.
    """
    weapon = find_attached(parent_bone_path) or find_attached(drive_bone)
    held = bool(weapon)
    if not weapon:
        weapon = bonedrive.driving_weapon(drive_bone)
        if not weapon:
            return None
    space = weaponspace.space_of(parent_bone_path) if held else None
    if not held and bonedrive.is_parked(weapon):
        bonedrive.unpark(weapon, drive_bone)
    else:
        bonedrive.unlink(drive_bone)
    cmds.delete(weapon)
    if space:
        weaponspace.prune(space)
    return weapon


def import_model(path):
    """Import `path` and return the transforms that arrived at world level.

    The import itself is `fbximport.import_nodes`, which owns the mode guard
    (trap 33) -- Add Character needs the identical thing for the UE4
    mannequin, and a fix for a silent failure must not exist twice.
    """
    new = fbximport.import_nodes(path)
    _LAST_IMPORT[:] = cmds.ls(new or [], uuid=True) or []   # by UUID: the weapon is re-parented
    return outermost(cmds.ls(new, long=True, type="transform") or [])


def model_root(weapon):
    """The geometry of an attached weapon -- what the animator grabs.

    Usually `weapon` itself now, and that question is asked FIRST: a mesh the
    animator parented under the sword by hand would otherwise outrank the
    sword. Only a fallback group has to be looked inside.

    It matters because anything riding the prop has to ride the geometry.
    Measured with the hands hung on the group instead: dragging the sword
    moved it 32.840 and the hands 0.000, which is the sword coming out of the
    hands. Controls already hung here are skipped by asking for a mesh rather
    than for any shape -- an IK control is a locator, and locators have shapes
    too.
    """
    if cmds.listRelatives(weapon, children=True, type="mesh"):
        return weapon
    for child in cmds.listRelatives(weapon, children=True, type="transform",
                                    fullPath=True) or []:
        if cmds.listRelatives(child, allDescendents=True, type="mesh"):
            return child
    return weapon


def is_animated(node):
    """Whether any offset channel of `node` is driven by an animation curve.

    A weapon that has been out in the world comes back with baked curves, and
    `setAttr` on a connected channel raises. Asking first is what keeps a
    traceback off the status line.
    """
    if not node:
        return False
    for channel in ("translate", "rotate"):
        for axis in "XYZ":
            plug = "{0}.{1}{2}".format(node, channel, axis)
            if cmds.listConnections(plug, source=True, destination=False,
                                    type="animCurve"):
                return True
    return False


def attach(entry, parent_bone_path, drive_bone, rotate=None, translate=None,
           rgb=None):
    """Put `entry`'s model into the hand, driving `drive_bone` from it.

    One mesh in the file and that mesh IS the weapon: parented under
    `parent_bone_path` (the drive bone's own parent), marked, seated, with
    whatever scaffolding the file came wrapped in deleted afterwards. Zero
    meshes or several keep a group of ours, and the note says so -- two
    meshes cannot both be the node the offsets live on, and one click cannot
    select both.

    Then the drive inverts: the weapon is snapped onto `drive_bone`, the
    grip is written (sword to its dialled pose -- and remembered on the
    node), any moving animation the bone carried is baked onto the weapon's
    channels WITH that offset kept (`bonedrive.link`, mo=True on the
    transfer), and the bone is parent-constrained to the weapon -- mo=True,
    capturing the grip's inverse, so the bone keeps playing exactly the
    animation it always had («в исходном виде», the user's 2026-08-25
    ruling) while the sword visibly sits at the grip. So the grip shapes
    the sword whether or not the bone brought animation, and never leaks
    into the export bone; grip-after-link was the same day's first report,
    every Add in a scene with a UE clip silently dropping the offsets. On
    an animated weapon the FIELDS stay quiet (`is_animated`) -- the grip
    they saved still applied.

    Whatever this module attached before is removed first WITH its animation
    (`detach` bakes the bone back off the old weapon before deleting it). All
    of it is one undo chunk -- a half-undone import leaves geometry with no
    home -- and runs with autoKey off (trap 14).
    """
    cmds.undoInfo(openChunk=True)
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        detach(parent_bone_path, drive_bone)

        # The hand's space, outside the skeleton (2026-09-24): it stands
        # exactly on the hand, so everything below reads as it did when the
        # weapon hung under the hand bone itself.
        home = weaponspace.ensure_space(parent_bone_path)
        weapon, note = import_weapon(entry, home, rgb)

        # Onto the drive bone exactly, in the model's own frame (the
        # catalog's `frame`, stored on the node by `import_weapon`), the grip
        # on top (BONE-relative: zeros mean exactly on weapon_r), then invert
        # the drive -- the transfer keeps the sword's offset from the bone,
        # so the grip rides the clip instead of being flattened by it. No
        # grip given (None) means "leave it on the bone", same place as zeros
        # but with nothing stored.
        if rotate is not None and translate is not None:
            bonedrive.apply_grip(weapon, drive_bone, rotate, translate)
        else:
            bonedrive.place_at_grip(weapon, drive_bone, (0.0, 0.0, 0.0),
                                    (0.0, 0.0, 0.0))
        frames = bonedrive.link(weapon, drive_bone)
        if frames:
            moved = ("{0} frame(s) moved from the bone onto the weapon"
                     .format(frames))
            note = note + " - " + moved if note else moved
        return weapon, note
    finally:
        cmds.autoKeyframe(state=autokey)
        cmds.undoInfo(closeChunk=True)


def _home(node, parent):
    """`node` under `parent`, or at world level with no parent; its long path."""
    if parent:
        return cmds.ls(cmds.parent(node, parent)[0], long=True)[0]
    if cmds.listRelatives(node, parent=True):
        node = cmds.parent(node, world=True)[0]
    return cmds.ls(node, long=True)[0]


def import_weapon(entry, parent=None, rgb=None):
    """`entry`'s model in the scene as OUR weapon. Returns (weapon, note).

    Imported; one mesh in the file and that mesh IS the weapon, parented
    under `parent` (a weapon space) or at world level (a weapon on the floor,
    2026-09-29), whatever scaffolding it came wrapped in deleted; zero meshes
    or several keep a group of ours, and the note says so. Then marked with
    its key and its source file, seated, dressed (its colour, or its image)
    and its own frame stored. The caller holds the undo chunk and autoKey.
    """
    del _LAST_IMPORT[:]
    roots = import_model(entry.path)
    if not roots:
        raise RuntimeError("nothing came out of " + entry.path)
    brought = list(_LAST_IMPORT)

    meshes = mesh_transforms(roots)
    note = ""
    if len(meshes) == 1:
        weapon = _home(meshes[0], parent)
        # Only the leftover TRANSFORMS: the shading network arrived in the
        # same import and the mesh still needs it.
        leftovers = [path for path in cmds.ls(roots, long=True) or []
                     if cmds.objExists(path) and path != weapon]
        if leftovers:
            cmds.delete(leftovers)
    else:
        # Built empty and filled, rather than grouping the model: a group
        # made around geometry takes that geometry's pivot with it, and the
        # pivot then has to be undone on the other side.
        group = cmds.group(empty=True, world=True, name=group_name(entry.key))
        cmds.parent(roots, group)
        weapon = _home(group, parent)
        note = "{0} mesh(es) in the file - kept in a group".format(len(meshes))

    # The marker after the parent, and `seat` after both: parenting is what
    # leaves the pivot compensation `seat` exists to clear.
    cmds.addAttr(weapon, longName=MARKER, dataType="string")
    cmds.setAttr(weapon + "." + MARKER, entry.key, type="string")
    cmds.addAttr(weapon, longName=SOURCE, dataType="string")
    cmds.setAttr(weapon + "." + SOURCE, entry.path, type="string")
    seat(weapon, entry.scale)

    # The colour comes from the same scan the characters use, so a sword in a
    # red character's hand arrives orange -- telling those two apart is half
    # of what the colour is for. A textured row (2026-09-28, Spear 03)
    # arrives in its image and the swatch's colour is not used: «это должно
    # выдаваться сразу с текстурой». `weapon` rather than `model_root`: a
    # file that kept a group of ours holds several meshes, all the weapon.
    texture = getattr(entry, "texture", "")
    if texture:
        colouring.paint_texture_nodes([weapon], texture, entry.key)
    else:
        if rgb is None:
            rgb = colouring.free_colour().rgb
        colouring.paint_nodes([weapon], rgb, entry.key)

    # the row's own frame, then the socket turn into a UE weapon bone
    # (2026-09-30): zero grip is the weapon in the fist on every rig
    bonedrive.store_frame(weapon, bonedrive.socket_frame(
        getattr(entry, "frame", (0.0, 0.0, 0.0))))
    if brought:
        from maya_scenesetup import deletion
        deletion.record_on(weapon, brought)
    return weapon, note
