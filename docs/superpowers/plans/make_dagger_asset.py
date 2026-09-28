"""make_dagger_asset.py - the animator's Dagger.fbx onto the sword's axes,
exported as SkeldarAnim/assets/Dagger_01.fbx. mayapy STANDALONE:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_dagger_asset.py

Spec: docs/superpowers/specs/2026-09-17-dagger-weapon-design.md. The source
file is never written; the asset is rebuilt from it on every run.

Measured on the source (2026-09-17): one mesh `|Dagger`, 7292 vertices,
identity transform, pivot at the origin, long axis **Z** (114.3 cm,
−84.24..+30.02). Sliced along Z: the **tip is at −Z** (blade from −84 to
about −27, 8–21 cm wide in Y and 1–2 cm thin in X), the guard around
−27..+1.5 (5.7 cm thick, 21 cm wide), the grip +1.5..+20 (5 × 3.5 cm), the
pommel +20..+30. The origin sits between guard and grip - where the sword's
sits. The sword's frame: blade along +Y with the tip at +Y, the grip going
−Y, the guard's width on X, the thickness on Z.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)
cmds.loadPlugin("fbxmaya", quiet=True)

from maya_scenesetup import attach  # noqa: E402

SOURCE = "C:/!!!Work/MayaScripts/sources/weapons/Dagger.fbx"
TARGET = PLUGIN + "/assets/Dagger_01.fbx"
MESH_NAME = "DaggerMesh"
MATERIAL = "Dagger_01_material"

# The turn, as the images of the source's basis vectors (Maya row vectors:
# world = local . M). Source Z (the blade axis, tip at -Z) goes to -Y so the
# tip lands at +Y and the grip at -Y; source Y (the blade's width) goes to
# -X; source X (the thickness) goes to +Z. Determinant +1 - a rotation, not
# a mirror (Y -> +X with the other two would be one).
ROWS = ((0.0, 0.0, 1.0),      # source X -> +Z
        (-1.0, 0.0, 0.0),     # source Y -> -X
        (0.0, -1.0, 0.0))     # source Z -> -Y
GRIP_Y = (-19.0, -2.0)        # the grip after the turn (source Z +2..+19)


def points(shape):
    sel = om.MSelectionList()
    sel.add(shape)
    fn = om.MFnMesh(sel.getDagPath(0))
    return [(p.x, p.y, p.z) for p in fn.getPoints(om.MSpace.kObject)]


def det3(rows):
    (a, b, c), (d, e, f), (g, h, i) = rows
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def extents(shape):
    pts = points(shape)
    return ([min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)], pts)


def main():
    assert abs(det3(ROWS) - 1.0) < 1e-9, "the turn must be a rotation"
    cmds.file(new=True, force=True)
    roots = attach.import_model(SOURCE)
    meshes = attach.mesh_transforms(roots)
    assert len(meshes) == 1, meshes
    mesh = meshes[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True,
                               noIntermediate=True)[0]
    lo, hi, _ = extents(shape)
    print("source extents  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))

    # 1. the turn, written as the transform's matrix and frozen into the mesh
    matrix = [ROWS[0][0], ROWS[0][1], ROWS[0][2], 0.0,
              ROWS[1][0], ROWS[1][1], ROWS[1][2], 0.0,
              ROWS[2][0], ROWS[2][1], ROWS[2][2], 0.0,
              0.0, 0.0, 0.0, 1.0]
    cmds.xform(mesh, matrix=matrix, objectSpace=True)
    cmds.makeIdentity(mesh, apply=True, translate=True, rotate=True,
                      scale=True, normal=0)
    lo, hi, pts = extents(shape)
    print("turned extents  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))

    # 2. the grip centred on the origin transversely (the sword's is), the
    #    origin's HEIGHT left where the model's author put it
    grip = [p for p in pts if GRIP_Y[0] < p[1] < GRIP_Y[1]]
    cx = sum(p[0] for p in grip) / len(grip)
    cz = sum(p[2] for p in grip) / len(grip)
    print("grip centroid before: x %.3f z %.3f (%d verts)" % (cx, cz, len(grip)))
    cmds.xform(mesh, translation=(-cx, 0.0, -cz), objectSpace=True)
    cmds.makeIdentity(mesh, apply=True, translate=True, rotate=True,
                      scale=True, normal=0)
    lo, hi, pts = extents(shape)
    grip = [p for p in pts if GRIP_Y[0] < p[1] < GRIP_Y[1]]
    print("grip centroid after:  x %.4f z %.4f" % (
        sum(p[0] for p in grip) / len(grip), sum(p[2] for p in grip) / len(grip)))
    cmds.xform(mesh, pivots=(0.0, 0.0, 0.0), objectSpace=True)
    cmds.delete(mesh, constructionHistory=True)

    # 3. a plain material: the source's openPBRSurface has no textures and
    #    is a node type an older Maya may not have; Add recolours anyway
    old = set()
    for sg in set(cmds.listConnections(shape, type="shadingEngine") or []):
        old.update(cmds.listConnections(sg + ".surfaceShader") or [])
    material = cmds.shadingNode("lambert", asShader=True, name=MATERIAL)
    cmds.setAttr(material + ".color", 0.55, 0.55, 0.58, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                   name=MATERIAL + "SG")
    cmds.connectAttr(material + ".outColor", sg + ".surfaceShader", force=True)
    cmds.sets(shape, edit=True, forceElement=sg)
    for node in old:
        if cmds.objExists(node) and node not in cmds.ls(defaultNodes=True):
            cmds.delete(node)

    mesh = cmds.rename(mesh, MESH_NAME)
    print("final extents   X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))

    # 4. export the mesh alone
    if os.path.exists(TARGET):
        os.remove(TARGET)
    mel.eval("FBXResetExport")
    mel.eval("FBXExportInputConnections -v false")
    mel.eval("FBXExportSmoothingGroups -v true")
    mel.eval("FBXExportInAscii -v false")
    cmds.select(mesh, replace=True)
    mel.eval('FBXExport -f "%s" -s' % TARGET)
    print("wrote", TARGET, os.path.getsize(TARGET), "bytes")

    # 5. read it back
    cmds.file(new=True, force=True)
    roots = attach.import_model(TARGET)
    meshes = attach.mesh_transforms(roots)
    shape = cmds.listRelatives(meshes[0], shapes=True, fullPath=True,
                               noIntermediate=True)[0]
    lo, hi, _ = extents(shape)
    print("re-import:", meshes, "extents  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    size = [hi[i] - lo[i] for i in range(3)]
    assert size[1] > size[0] > size[2], "blade on Y, width on X, thickness on Z"
    assert hi[1] > -lo[1], "tip at +Y"
    print("dagger asset OK")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            maya.standalone.uninitialize()
        except Exception:
            pass
