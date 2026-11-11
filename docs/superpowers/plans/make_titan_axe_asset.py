"""make_titan_axe_asset.py - the Fighter's Titan Axe as SkeldarAnim/assets/Titan_Axe.fbx.

    mayapy docs/superpowers/plans/make_titan_axe_asset.py

mayapy STANDALONE, 2026-11-11 (spec: docs/superpowers/specs/2026-11-11-fighter-design.md). The source
`sources/fighter/TitanAxe_2H_01.fbx` (the animator's Downloads) is never written.

Measured on it: one mesh `|TitanAxe`, 1041 vertices, identity transform, 175.5 cm. It already lies in
our weapon convention - the head along +Y (y 30..120, the blade on -X, a spike on +X), the haft down
to -64, width on X, thickness on Z - and its origin is on the haft 30 cm under the head, where it is
gripped. So nothing is turned: the haft is centred on the axis (its centroid read off y -40..-5), the
material whose textures were on a drive not here becomes a plain lambert, the keys (none expected) are
cut, and it is exported with no animation (trap 326) and read back.
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

SOURCE = "C:/!!!Work/MayaScripts/sources/fighter/TitanAxe_2H_01.fbx"
TARGET = PLUGIN + "/assets/Titan_Axe.fbx"
MESH_NAME = "TitanAxeMesh"
MATERIAL = "Titan_Axe_material"
HAFT_Y = (-40.0, -5.0)


def points(shape):
    sel = om.MSelectionList()
    sel.add(shape)
    return [(p.x, p.y, p.z) for p in om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kObject)]


def extents(shape):
    pts = points(shape)
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)], pts


def main():
    cmds.file(new=True, force=True)
    roots = attach.import_model(SOURCE)
    meshes = attach.mesh_transforms(roots)
    assert len(meshes) == 1, meshes
    mesh = meshes[0]
    if cmds.listRelatives(mesh, parent=True):
        mesh = cmds.parent(mesh, world=True)[0]
    curves = cmds.ls(type="animCurve")
    if curves:
        cmds.delete(curves)
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True)[0]
    cmds.makeIdentity(mesh, apply=True, translate=True, rotate=True, scale=True, normal=0)
    lo, hi, pts = extents(shape)
    print("source extents  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    size = [hi[i] - lo[i] for i in range(3)]
    assert size[1] > size[0] > size[2], "head along Y, width on X, thickness on Z"
    assert hi[1] > -lo[1], "the head at +Y"
    haft = [p for p in pts if HAFT_Y[0] < p[1] < HAFT_Y[1]]
    cx = sum(p[0] for p in haft) / len(haft)
    cz = sum(p[2] for p in haft) / len(haft)
    print("haft centroid before: x %.3f z %.3f (%d verts)" % (cx, cz, len(haft)))
    cmds.xform(mesh, translation=(-cx, 0.0, -cz), objectSpace=True)
    cmds.makeIdentity(mesh, apply=True, translate=True, rotate=True, scale=True, normal=0)
    cmds.xform(mesh, pivots=(0.0, 0.0, 0.0), objectSpace=True)
    cmds.delete(mesh, constructionHistory=True)

    old = set()
    for sg in set(cmds.listConnections(shape, type="shadingEngine") or []):
        old.update(cmds.listConnections(sg + ".surfaceShader") or [])
        if sg != "initialShadingGroup":
            old.add(sg)
    material = cmds.shadingNode("lambert", asShader=True, name=MATERIAL)
    cmds.setAttr(material + ".color", 0.5, 0.5, 0.52, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=MATERIAL + "SG")
    cmds.connectAttr(material + ".outColor", sg + ".surfaceShader", force=True)
    cmds.sets(shape, edit=True, forceElement=sg)
    for node in old:
        if cmds.objExists(node) and node not in cmds.ls(defaultNodes=True):
            cmds.delete(node)
    for f in cmds.ls(type="file") + cmds.ls(type="bump2d") + cmds.ls(type="place2dTexture"):
        cmds.delete(f)
    mesh = cmds.rename(mesh, MESH_NAME)
    lo, hi, _ = extents(cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True)[0])
    print("final extents   X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))

    if os.path.exists(TARGET):
        os.remove(TARGET)
    mel.eval("FBXResetExport")
    mel.eval("FBXExportInputConnections -v false")
    mel.eval("FBXExportSmoothingGroups -v true")
    mel.eval("FBXExportInAscii -v false")
    mel.eval('FBXProperty "Export|IncludeGrp|Animation" -v false')
    cmds.select(mesh, replace=True)
    mel.eval('FBXExport -f "%s" -s' % TARGET)
    print("wrote", TARGET, os.path.getsize(TARGET), "bytes")

    cmds.file(new=True, force=True)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval('FBXImport -f "%s"' % TARGET)
    meshes = [cmds.listRelatives(s, parent=True, fullPath=True)[0] for s in cmds.ls(type="mesh", noIntermediate=True)]
    assert len(meshes) == 1, meshes
    lo, hi, pts = extents(cmds.listRelatives(meshes[0], shapes=True, fullPath=True, noIntermediate=True)[0])
    haft = [p for p in pts if HAFT_Y[0] < p[1] < HAFT_Y[1]]
    print("re-import: %s, %d animCurves, files %s, extents X %.2f..%.2f Y %.2f..%.2f Z %.2f..%.2f, haft x %.4f z %.4f"
          % (meshes, len(cmds.ls(type="animCurve")), [cmds.getAttr(f + ".fileTextureName") for f in cmds.ls(type="file")],
             lo[0], hi[0], lo[1], hi[1], lo[2], hi[2],
             sum(p[0] for p in haft) / len(haft), sum(p[2] for p in haft) / len(haft)))
    assert not cmds.ls(type="animCurve"), "the file carries animation"
    assert not cmds.ls(type="file"), "the file names a texture"
    print("titan axe asset OK")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            maya.standalone.uninitialize()
        except Exception:
            pass
