"""Snapshot of a skinned mesh in its current pose.

Test-mode tool, deliberately minimal (the project's spec/TDD pipeline is
skipped on purpose): select one or more deformed meshes, press Snapshot,
and each gets a clean static copy frozen in the pose of the CURRENT
frame - duplicated, unhooked from the skeleton (no history, no skin, no
intermediate shapes), parented to the world, transforms frozen, pivot
centred, dropped out of display layers so nothing hides it. The source
mesh and its rig are never touched. The copy is named
<mesh>_snap_f<frame> and selected afterwards, ready for modelling
manipulation.

Run:
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_meshsnap; maya_meshsnap.show()
"""

import maya.cmds as cmds

WINDOW = "meshSnapWindow"

_status = None


def selected_mesh_transforms():
    """Transforms of the selected meshes (shapes or transforms alike,
    components folded to their object)."""
    out = []
    for node in cmds.ls(selection=True, long=True, objectsOnly=True) or []:
        if cmds.objectType(node, isAType="mesh"):
            parent = cmds.listRelatives(node, parent=True,
                                        fullPath=True)
            node = parent[0] if parent else node
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True,
                                    type="mesh") or []
        if any(not cmds.getAttr(s + ".intermediateObject")
               for s in shapes):
            if node not in out:
                out.append(node)
    return out


def snapshot(transforms):
    """A frozen posed copy per mesh; returns the new transforms."""
    frame = int(round(cmds.currentTime(query=True)))
    out = []
    for src in transforms:
        dup = cmds.duplicate(src, returnRootsOnly=True,
                             name="%s_snap_f%d"
                             % (src.split("|")[-1], frame))[0]
        dup = cmds.ls(dup, long=True)[0]
        # Unlock BEFORE the world re-parent: with locked channels the
        # parent command cannot compensate, and a rotated container
        # (the FBX-style -90 X group) silently falls out of the copy -
        # the snapshot ends up face down.
        for ch in ("tx", "ty", "tz", "rx", "ry", "rz",
                   "sx", "sy", "sz", "v",
                   "shearXY", "shearXZ", "shearYZ"):
            try:
                cmds.setAttr(dup + "." + ch, lock=False)
            except RuntimeError:
                pass
        if cmds.listRelatives(dup, parent=True):
            dup = cmds.ls(cmds.parent(dup, world=True)[0],
                          long=True)[0]
        cmds.setAttr(dup + ".visibility", 1)
        cmds.delete(dup, constructionHistory=True)
        for sh in cmds.listRelatives(dup, shapes=True,
                                     fullPath=True) or []:
            if cmds.getAttr(sh + ".intermediateObject"):
                cmds.delete(sh)
        try:
            cmds.editDisplayLayerMembers("defaultLayer", dup)
        except RuntimeError:
            pass
        cmds.makeIdentity(dup, apply=True, translate=True, rotate=True,
                          scale=True, normal=0)
        cmds.xform(dup, centerPivots=True)
        out.append(cmds.ls(dup, long=True)[0])
    return out


def _say(message):
    if _status and cmds.text(_status, exists=True):
        cmds.text(_status, edit=True, label=message)
    print("meshsnap: " + message)


def _snap_pressed(*_):
    try:
        meshes = selected_mesh_transforms()
        if not meshes:
            _say("Select a mesh first.")
            return
        cmds.undoInfo(openChunk=True)
        try:
            snaps = snapshot(meshes)
        finally:
            cmds.undoInfo(closeChunk=True)
        cmds.select(snaps)
        _say("Snapshot: %s." % ", ".join(s.split("|")[-1]
                                         for s in snaps))
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def show():
    global _status
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="Mesh Snapshot", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))
    cmds.text(label="Select a skinned mesh, press Snapshot: a frozen "
                    "copy in the pose of",
              align="left")
    cmds.text(label="the current frame - no history, no skin, clean "
                    "transforms.",
              align="left")
    cmds.button(label="Snapshot", height=34, command=_snap_pressed)
    _status = cmds.text(label="", align="left")
    cmds.separator(height=4, style="none")
    cmds.showWindow(WINDOW)
