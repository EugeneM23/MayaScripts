"""Put a weapon model into a bone, and move it once it is there.

Attachment is a plain DAG parent: the model hangs under the bone and inherits
its motion. What the animator adjusts is the CARRIER -- a transform of ours
between the bone and the imported model -- so the offsets live on a node this
module owns and the imported geometry keeps whatever the artist authored.

The carrier is found by a string attribute, never by name. Maya uniquifies
imported names, the animator may rename anything, and every tool in this repo
that identified a node by name has paid for it.
"""

import maya.cmds as cmds

MARKER = "mayaWeapon"

# Everything that can hold an offset between a node and its parent. Zeroing
# translate and rotate is not enough: a group's pivot sits at the centre of
# what it holds, and parenting compensates for it in rotatePivotTranslate --
# so the carrier reads t=0 r=0 and hangs 28 cm off the bone. Measured.
_SEATED_AT_ZERO = ("translate", "rotate", "shear",
                   "rotatePivot", "rotatePivotTranslate",
                   "scalePivot", "scalePivotTranslate", "rotateAxis")


def carrier_name(key):
    return "{0}_weapon".format(key)


def seat(carrier, scale=1.0):
    """Put `carrier` exactly on its parent: local matrix identity, then scale."""
    for channel in _SEATED_AT_ZERO:
        cmds.setAttr("{0}.{1}".format(carrier, channel), 0.0, 0.0, 0.0,
                     type="double3")
    cmds.setAttr(carrier + ".scale", scale, scale, scale, type="double3")


def outermost(paths):
    """The paths with no ancestor among the others.

    The trailing separator is the whole test: `|swordExtra` is not a child of
    `|sword`, and a plain startswith would swallow it.
    """
    return [path for path in paths
            if not any(path.startswith(other + "|")
                       for other in paths if other != path)]


def find_attached(bone):
    """The carrier this module put in `bone`, or None."""
    children = cmds.listRelatives(bone, children=True, type="transform",
                                  fullPath=True) or []
    for child in children:
        if cmds.attributeQuery(MARKER, node=child, exists=True):
            return child
    return None


def remove_attached(bone):
    """Delete our carrier under `bone`. Returns what was removed, or None."""
    carrier = find_attached(bone)
    if carrier:
        cmds.delete(carrier)
    return carrier


def import_model(path):
    """Import `path` and return the transforms that arrived at world level.

    `cmds.file` rather than the plugin's `FBXImport`, which is the opposite of
    what the UE bridge does and is deliberate: trap 22 is about losing
    animation curves, and there is no animation in a weapon model, while
    `returnNewNodes` gives the exact node list `FBXImport` cannot report at all.
    """
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya", quiet=True)

    new = cmds.file(path, i=True, type="FBX", returnNewNodes=True,
                    ignoreVersion=True) or []
    return outermost(cmds.ls(new, long=True, type="transform") or [])


def write_offsets(carrier, rotate, translate):
    """Set the carrier's local rotate and translate.

    autoKey is off for the duration. The carrier carries no curves, so it
    would not fire -- but the user works with autoKey ON and this repo has
    already paid for assuming a scripted poke is harmless.
    """
    state = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        for axis, value in zip("XYZ", rotate):
            cmds.setAttr("{0}.rotate{1}".format(carrier, axis), value)
        for axis, value in zip("XYZ", translate):
            cmds.setAttr("{0}.translate{1}".format(carrier, axis), value)
    finally:
        cmds.autoKeyframe(state=state)


def read_offsets(carrier):
    """The carrier's local rotate and translate, as two triples."""
    rotate = tuple(cmds.getAttr("{0}.rotate{1}".format(carrier, axis))
                   for axis in "XYZ")
    translate = tuple(cmds.getAttr("{0}.translate{1}".format(carrier, axis))
                      for axis in "XYZ")
    return rotate, translate


def attach(entry, bone, rotate=(0.0, 0.0, 0.0), translate=(0.0, 0.0, 0.0)):
    """Put `entry`'s model into `bone` and return the carrier's long path.

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

        # Built empty and filled, rather than grouping the model: a group made
        # around geometry takes that geometry's pivot with it, and the pivot
        # then has to be undone on the other side.
        carrier = cmds.group(empty=True, world=True,
                             name=carrier_name(entry.key))
        cmds.addAttr(carrier, longName=MARKER, dataType="string")
        cmds.setAttr(carrier + "." + MARKER, entry.key, type="string")
        cmds.parent(roots, carrier)

        carrier = cmds.ls(cmds.parent(carrier, bone)[0], long=True)[0]
        seat(carrier, entry.scale)
        write_offsets(carrier, rotate, translate)
        return carrier
    finally:
        cmds.undoInfo(closeChunk=True)
