"""The Swordman's sword and shield as catalog weapons.

    mayapy make_swordman_weapons.py

Reads  sources/swordman/Swordman_Source.mb
Writes SkeldarAnim/assets/Swordman_Sword.fbx  (weapon_r)
       SkeldarAnim/assets/Swordman_Shield.fbx (weapon_l)

`bonedrive` places a weapon at `world = grip . frame . bone`, and a catalog
row's default frame makes that `R(SOCKET_TURN) . W_bone` at zero grip. So each
prop is exported with its points expressed in THAT seat: Add Weapon at zero
grip then puts each back in his fist exactly where he holds it, and the rows
need no stored grip and no frame of their own.

The points carry his 2.54 (trap 86): the sword is a 117 cm blade, not the
46 cm its own geometry reads.
"""
import os
import shutil
import sys
import tempfile

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_scenesetup import bonedrive                              # noqa: E402

SRC = os.path.join(REPO, "sources", "swordman", "Swordman_Source.mb")
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")

# (the source's mesh, its bone, the exported file, the exported mesh name)
PROPS = [("Swordman_Sword", "weapon_r", "Swordman_Sword.fbx", "Swordman_SwordMesh"),
         ("Swordman_Shield", "weapon_l", "Swordman_Shield.fbx", "Swordman_ShieldMesh")]
TOL = 1e-4


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def one(pattern, **kw):
    hits = cmds.ls("*" + pattern, long=True, **kw) or []
    if len(hits) != 1:
        raise RuntimeError("%s: expected one, found %d" % (pattern, len(hits)))
    return hits[0]


def shape_of(transform):
    return cmds.listRelatives(transform, shapes=True, fullPath=True,
                              noIntermediate=True)[0]


def points_of(path, space=om.MSpace.kWorld):
    """Fresh MPoints: the MPointArray's own memory dangles once it is collected."""
    got = om.MFnMesh(om.MSelectionList().add(path).getDagPath(0)).getPoints(space)
    return [om.MPoint(p.x, p.y, p.z) for p in got]


def seat_of(bone):
    """Where zero grip stands a weapon of the default frame on `bone`.

    Through bonedrive's own `socket_frame` and `framed`, so this can never
    drift from what Add Weapon actually does.
    """
    frame = bonedrive.socket_frame()
    return om.MMatrix(bonedrive.framed(frame, cmds.getAttr(bone + ".worldMatrix[0]")))


def span(points):
    return max((om.MVector(a - b).length() for a in points for b in points), default=0.0)


def longest_axis(points):
    extents = []
    for axis in range(3):
        values = [p[axis] for p in points]
        extents.append((max(values) - min(values), "xyz"[axis]))
    extents.sort(reverse=True)
    return extents[0]


def export(mesh_name, bone_name, file_name, out_name):
    cmds.file(SRC, open=True, force=True, executeScriptNodes=False, prompt=False)
    mesh = one(mesh_name, type="transform")
    bone = one(bone_name, type="joint")

    his = points_of(shape_of(mesh))
    seat = seat_of(bone)
    local = [om.MPoint(p) * seat.inverse() for p in his]

    # keep this one prop, nothing else
    # `parent -world` answers None for a node already at world level
    moved = cmds.parent(mesh, world=True) if mesh.count("|") > 1 else None
    keep = cmds.ls(moved[0] if moved else mesh, long=True)[0]
    for top in cmds.ls(assemblies=True, long=True) or []:
        if top != keep and leaf(top) not in ("persp", "top", "front", "side"):
            cmds.delete(top)
    keep = cmds.ls("*" + mesh_name, long=True, type="transform")[0]
    for attr, value in (("translate", (0, 0, 0)), ("rotate", (0, 0, 0)),
                        ("scale", (1, 1, 1)), ("shear", (0, 0, 0)),
                        ("rotateAxis", (0, 0, 0))):
        cmds.setAttr(keep + "." + attr, *value)
    shape = shape_of(keep)
    om.MFnMesh(om.MSelectionList().add(shape).getDagPath(0)).setPoints(
        om.MPointArray(local), om.MSpace.kObject)

    # a plain lambert: the atlas arrives through the catalog row's `texture`,
    # and openPBR_shader1 is a node type not every Maya has.
    for engine in cmds.listConnections(shape, type="shadingEngine") or []:
        cmds.sets(shape, edit=True, forceElement="initialShadingGroup")
    material = cmds.shadingNode("lambert", asShader=True, name=out_name + "_Mat")
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                      name=material + "SG")
    cmds.connectAttr(material + ".outColor", group + ".surfaceShader", force=True)
    cmds.sets(shape, edit=True, forceElement=group)
    keep = cmds.ls(cmds.rename(keep, out_name), long=True)[0]

    out = os.path.join(ASSETS, file_name)
    work = os.path.join(tempfile.gettempdir(), "swordman_weapons_work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    tmp = os.path.join(work, file_name).replace("\\", "/")
    cmds.loadPlugin("fbxmaya", quiet=True)
    mel.eval("FBXResetExport")
    mel.eval("FBXExportSmoothingGroups -v true")
    mel.eval("FBXExportSkins -v false")
    mel.eval("FBXExportShapes -v false")
    mel.eval("FBXExportInputConnections -v false")
    mel.eval('FBXExport -f "%s"' % tmp)
    if not os.path.exists(tmp):
        raise RuntimeError("the exporter wrote nothing to %s" % tmp)

    check(tmp, out_name, his, seat, file_name)
    shutil.move(tmp, out)
    return out


def check(path, out_name, his_world, seat, file_name):
    """Read it back the way Add Weapon does and seat it at zero grip."""
    cmds.file(new=True, force=True)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval('FBXImport -f "%s"' % path.replace("\\", "/"))
    mesh = one(out_name, type="transform")
    shape = shape_of(mesh)
    back = points_of(shape, om.MSpace.kObject)
    if len(back) != len(his_world):
        raise RuntimeError("%s: %d points went out, %d came back"
                           % (file_name, len(his_world), len(back)))
    placed = [om.MPoint(p) * seat for p in back]
    worst = max((om.MVector(a - b).length() for a, b in zip(placed, his_world)),
                default=0.0)
    if worst > TOL:
        raise RuntimeError("%s lands %.6f cm off his own hold" % (file_name, worst))
    length, axis = longest_axis(back)
    uvs = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
    print("  %-22s %3d verts, %6.1f cm along its own %s, span %.1f, uv %s"
          % (file_name, len(back), length, axis, span(back), uvs))
    print("  %-22s lands %.2e cm off his hold at zero grip" % ("", worst))


def main():
    os.chdir(tempfile.gettempdir())
    print("exporting in the seat `R(SOCKET_TURN) . W_bone`, which is where a")
    print("default catalog row stands a weapon at zero grip:")
    for mesh_name, bone, file_name, out_name in PROPS:
        got = export(mesh_name, bone, file_name, out_name)
        print("  wrote %s (%.1f KB)" % (got, os.path.getsize(got) / 1024.0))


if __name__ == "__main__":
    main()
    maya.standalone.uninitialize()
