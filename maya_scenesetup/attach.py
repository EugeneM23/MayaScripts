"""Put a weapon model into a bone, and move it once it is there.

Attachment is a plain DAG parent: the model hangs under the bone and inherits
its motion. **The weapon is the geometry** -- the mesh transform itself is
what gets parented, marked and offset, so one click in the viewport selects
the thing that moves. A file that arrives wrapped in a null loses the null;
that null is exactly the group the animator asked not to have.

A file holding no mesh, or several, keeps a group of ours instead: two meshes
cannot both be the node the offsets live on, and one click cannot select both.

Either way there is exactly ONE marked node per bone, and it is found by a
string attribute, never by name. Maya uniquifies imported names, the animator
may rename anything, and every tool in this repo that identified a node by
name has paid for it.
"""

import maya.cmds as cmds
import maya.mel as mel

MARKER = "mayaWeapon"

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


def find_attached(bone):
    """The weapon this module put in `bone`, or None."""
    children = cmds.listRelatives(bone, children=True, type="transform",
                                  fullPath=True) or []
    for child in children:
        if cmds.attributeQuery(MARKER, node=child, exists=True):
            return child
    return None


def remove_attached(bone):
    """Delete our weapon under `bone`. Returns what was removed, or None."""
    weapon = find_attached(bone)
    if weapon:
        cmds.delete(weapon)
    return weapon


def import_model(path):
    """Import `path` and return the transforms that arrived at world level.

    `cmds.file` rather than the plugin's `FBXImport`, which is the opposite of
    what the UE bridge does and is deliberate: trap 22 is about losing
    animation curves, and there is no animation in a weapon model, while
    `returnNewNodes` gives the exact node list `FBXImport` cannot report at all.
    """
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya", quiet=True)

    # The plugin's import mode is one global setting that lives for the whole
    # Maya session, and it DOES reach cmds.file even though the curve-related
    # settings do not (trap 22, from the other side). maya_uebridge leaves it
    # on `exmerge`, where the importer matches names against the scene and
    # creates nothing at all -- so after any animation import from Unreal, the
    # weapon silently stopped arriving. Set it for every import, inherit never.
    previous = mel.eval("FBXImportMode -q")
    mel.eval("FBXImportMode -v add")
    try:
        new = cmds.file(path, i=True, type="FBX", returnNewNodes=True,
                        ignoreVersion=True) or []
    finally:
        if previous:
            mel.eval("FBXImportMode -v {0}".format(previous))

    return outermost(cmds.ls(new, long=True, type="transform") or [])


def write_offsets(weapon, rotate, translate):
    """Set the weapon's local rotate and translate.

    autoKey is off for the duration. A weapon in the hand carries no curves,
    so it would not fire -- but the user works with autoKey ON and this repo
    has already paid for assuming a scripted poke is harmless.
    """
    state = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        for axis, value in zip("XYZ", rotate):
            cmds.setAttr("{0}.rotate{1}".format(weapon, axis), value)
        for axis, value in zip("XYZ", translate):
            cmds.setAttr("{0}.translate{1}".format(weapon, axis), value)
    finally:
        cmds.autoKeyframe(state=state)


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


def read_offsets(weapon):
    """The weapon's local rotate and translate, as two triples."""
    rotate = tuple(cmds.getAttr("{0}.rotate{1}".format(weapon, axis))
                   for axis in "XYZ")
    translate = tuple(cmds.getAttr("{0}.translate{1}".format(weapon, axis))
                      for axis in "XYZ")
    return rotate, translate


def attach(entry, bone, rotate=(0.0, 0.0, 0.0), translate=(0.0, 0.0, 0.0)):
    """Put `entry`'s model into `bone`. Returns (attached long path, note).

    One mesh in the file and that mesh IS the weapon: parented into the bone,
    marked, seated, holding the grip on its own channels, with whatever
    scaffolding the file came wrapped in deleted afterwards. Zero meshes or
    several keep a group of ours, and the note says so -- two meshes cannot
    both be the node the offsets live on, and one click cannot select both.

    Whatever this module attached there before is removed first: one weapon per
    bone, so the offset fields always have exactly one thing to move. All of it
    is one undo chunk -- a half-undone import leaves geometry with no home.
    """
    cmds.undoInfo(openChunk=True)
    try:
        remove_attached(bone)

        roots = import_model(entry.path)
        if not roots:
            raise RuntimeError("nothing came out of " + entry.path)

        meshes = mesh_transforms(roots)
        note = ""
        if len(meshes) == 1:
            weapon = cmds.ls(cmds.parent(meshes[0], bone)[0], long=True)[0]
            # Only the leftover TRANSFORMS: the shading network arrived in the
            # same import and the mesh still needs it.
            leftovers = [path for path in cmds.ls(roots, long=True) or []
                         if cmds.objExists(path) and path != weapon]
            if leftovers:
                cmds.delete(leftovers)
        else:
            # Built empty and filled, rather than grouping the model: a group
            # made around geometry takes that geometry's pivot with it, and
            # the pivot then has to be undone on the other side.
            group = cmds.group(empty=True, world=True,
                               name=group_name(entry.key))
            cmds.parent(roots, group)
            weapon = cmds.ls(cmds.parent(group, bone)[0], long=True)[0]
            note = "{0} mesh(es) in the file - kept in a group".format(
                len(meshes))

        # The marker after the parent, and `seat` after both: parenting is
        # what leaves the pivot compensation `seat` exists to clear.
        cmds.addAttr(weapon, longName=MARKER, dataType="string")
        cmds.setAttr(weapon + "." + MARKER, entry.key, type="string")
        seat(weapon, entry.scale)
        write_offsets(weapon, rotate, translate)
        return weapon, note
    finally:
        cmds.undoInfo(closeChunk=True)
