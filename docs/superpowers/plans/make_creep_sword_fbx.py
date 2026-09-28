"""SkeldarAnim/assets/Creep_Sword.fbx -- the Creep's WHOLE sword, in its own axes.

    mayapy make_creep_sword_fbx.py <a scene holding the Creep's original swords on weapon_test>

2026-09-24, the animator, with a test take on the rig: «меч хантера почему-то оказался без
рукоятки, мы где-то её потеряли, и он повёрнут на 45 градусов; при повороте меча 0 0 0 он должен
встать так, как сейчас».  Two things were wrong with the first export (make_creep_sword_asset.py):

- **the handle was left out.**  The creature's sword is TWO meshes riding weapon_test --
  `SwordPacked` (10890 vertices: blade, guard, pommel) and `Sword_Low.001` (1170 vertices: the
  grip, -7.3..+13.6 along the bone) -- and the first export took the first alone (the second was
  described as "a second grip piece" when the animator was asked; it is THE grip).  Both are taken
  now and united into one mesh: a catalog weapon IS one geometry (attach.mesh_transforms).
- **the grip.**  In the animator's scene the sword stood right with the Weapons grip Rotate at
  (0, 45, 0) (read off the scene: the sword 45 deg about weapon_r's Y, translate 0).  The first
  fix baked that turn into the POINTS, and the animator saw the node's axes stand on the bone
  while the guard stood 45 off them («сейчас у меча развёрнута геометрия, а оси стоят ровно ...
  чтобы оси соответствовали направлению геометрии, но при этом меч сохранил свою позу в руке»).
  So the points are the model's own again -- expressed in weapon_r's frame (FLIP_Z times
  weapon_test's, as `weapon_bones` built the bone): blade +Y, guard X, thickness Z -- and the 45
  is the catalog row's FRAME (`catalog.Weapon.frame`, `bonedrive.FRAME_ROTATE`): zero grip
  stands the NODE turned by it on weapon_r, its axes on the geometry, the blade where the 45
  put it.

2026-09-25, the animator: «наш меч крипа стал меньше чем был изначально, нужно вернуть прежний
размер».  In the creature's own file (`creep_T-pose_draft (1).fbx`, Cascadeur's, and the animator's
scene before any of our work) `lowerarm_r` carries a scale of 1.32, and the sword -- a plain child of
weapon_test, not skinned -- inherits it: **124.02 cm** from pommel to tip.  The first morning's
joint-scale removal kept every skinned vertex where it was (`BPM' = BPM·WM_old·WM_new⁻¹`) and had no
such rule for an unskinned child, so from then on the sword stood **93.95 cm** -- 1/1.32 -- and every
asset since was cut from that.  So the source is the creature's ORIGINAL file again, and the frame
the sword is expressed in is weapon_test's RIGID frame (its scale stripped): the scale the chain
gave the sword stays in its points, the model at the size the creature holds it.  Read back, the
sword is the asset it replaces times the chain's scale, about weapon_r's origin (the grip).

mayapy STANDALONE, the source opened with its script nodes not executed and never saved.  The fbx
is read back the way Add reads it (attach.import_model -> one mesh), checked on the catalog's
convention (blade +Y, tip +Y), checked against the asset it replaces (the turned one, turned
back; a re-run's, unchanged; or the shrunk one, at the chain's scale), and its handle checked to
be there.

    mayapy make_creep_sword_fbx.py "C:/!!!Work/MayaScripts/sources/creep/creep_T-pose_draft.fbx"
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim", "assets"))
SWORD = os.path.join(ASSETS, "Creep_Sword.fbx").replace("\\", "/")
SRC = sys.argv[1].replace("\\", "/")
PIECES = ("SwordPacked", "Sword_LowFBXASC046001", "Hunter_Sword", "Hunter_Sword_Low")   # the file's names, or the rig's
GRIP_ROTATE = (0.0, 45.0, 0.0)          # the animator's grip, read off the scene 2026-09-24 --
                                        # the catalog row's frame now, NOT in the points
FLIP_Z = om.MMatrix([-1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])   # weapon_test -> weapon_r (weapon_bones)
MESH = "CreepSwordMesh"


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def rigid(m):
    """`m` with its scale and shear stripped: the frame a bone stands in, whatever its parents scale."""
    t = om.MTransformationMatrix(m)
    out = om.MTransformationMatrix()
    out.setRotation(t.rotation(asQuaternion=True))
    out.setTranslation(t.translation(om.MSpace.kWorld), om.MSpace.kWorld)
    return out.asMatrix()


def uniform_scale(m):
    s = [om.MVector(m.getElement(i, 0), m.getElement(i, 1), m.getElement(i, 2)).length() for i in range(3)]
    if max(s) - min(s) > 1e-4:
        raise RuntimeError("weapon_test is scaled unevenly %s: the sword's size is not one number" % s)
    return sum(s) / 3.0


def points(shape, space=om.MSpace.kObject):
    sel = om.MSelectionList(); sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(space)


def fbx_points(path):
    """The first mesh of an fbx, read the way Add reads it."""
    cmds.file(new=True, force=True)
    sys.path.insert(0, os.path.abspath(os.path.join(ASSETS, "..")))
    from maya_scenesetup import attach
    roots = attach.import_model(path)
    meshes = attach.mesh_transforms(roots)
    shape = cmds.listRelatives(meshes[0], shapes=True, fullPath=True, noIntermediate=True)[0]
    return meshes, points(shape, om.MSpace.kWorld)


grip = om.MEulerRotation(*[math.radians(v) for v in GRIP_ROTATE]).asMatrix()
_, old = fbx_points(SWORD)                          # the old asset, for the comparison below

cmds.file(SRC, open=True, force=True, executeScriptNodes=False)
bone = cmds.ls("weapon_test", "*:weapon_test", type="joint", long=True)
if len(bone) != 1:
    raise RuntimeError("expected one weapon_test, found %s" % bone)
# weapon_r's frame, where the catalog's weapons live -- RIGID: the creature's lowerarm_r scales its
# hand by 1.32, and that scale is the sword's size, not part of the frame (2026-09-25)
chain_scale = uniform_scale(wm(bone[0]))
frame = FLIP_Z * rigid(wm(bone[0]))
print("weapon_test %s, the chain's scale on it %.4f" % (bone[0], chain_scale))
found = [t for t in cmds.ls(PIECES, type="transform", long=True)]
blade = [t for t in found if t.split("|")[-1] in ("SwordPacked", "Hunter_Sword")]
handle = [t for t in found if t.split("|")[-1] in ("Sword_LowFBXASC046001", "Hunter_Sword_Low")]
if len(blade) != 1 or len(handle) != 1:
    raise RuntimeError("expected the blade and the handle once each, found %s" % found)
dups = []
for src in (blade[0], handle[0]):
    dup = cmds.duplicate(src, name=src.split("|")[-1] + "_bake")[0]
    dup = cmds.ls(cmds.parent(dup, world=True)[0], long=True)[0]
    for c in cmds.listRelatives(dup, children=True, type="constraint", fullPath=True) or []:
        cmds.delete(c)
    for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(dup + "." + a, lock=False)
    cmds.xform(dup, worldSpace=True, matrix=list(wm(src) * frame.inverse()))
    cmds.makeIdentity(dup, apply=True, translate=True, rotate=True, scale=True, normal=0)
    dups.append(dup)
n_blade = len(points(cmds.listRelatives(dups[0], shapes=True, fullPath=True, noIntermediate=True)[0]))
n_handle = len(points(cmds.listRelatives(dups[1], shapes=True, fullPath=True, noIntermediate=True)[0]))
united = cmds.polyUnite(dups, name=MESH, constructionHistory=False, mergeUVSets=1)[0]
united = cmds.ls(united, long=True)[0]
for d in dups:
    if cmds.objExists(d):
        cmds.delete(d)
cmds.xform(united, pivots=(0.0, 0.0, 0.0), objectSpace=True)
cmds.delete(united, constructionHistory=True)
shape = cmds.listRelatives(united, shapes=True, fullPath=True, noIntermediate=True)[0]
mat = cmds.shadingNode("lambert", asShader=True, name="CreepSwordMat")
cmds.setAttr(mat + ".color", 0.55, 0.55, 0.58, type="double3")
sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="CreepSwordMatSG")
cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader", force=True)
cmds.sets(shape, edit=True, forceElement=sg)
if os.path.exists(SWORD):
    os.remove(SWORD)
mel.eval("FBXResetExport")
mel.eval("FBXExportInputConnections -v false")
mel.eval("FBXExportSmoothingGroups -v true")
mel.eval("FBXExportInAscii -v false")
cmds.select(united, replace=True)
mel.eval('FBXExport -f "%s" -s' % SWORD)
print("exported %s: %d + %d vertices" % (SWORD, n_blade, n_handle))

# read back the way Add reads it
meshes, pts = fbx_points(SWORD)
e = [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in range(3)]
print("re-import: %s, %d verts, X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (meshes, len(pts), e[0][0], e[0][1], e[1][0], e[1][1], e[2][0], e[2][1]))
assert len(meshes) == 1 and len(pts) == n_blade + n_handle, "one mesh, blade and handle"
size = [e[i][1] - e[i][0] for i in range(3)]
assert size[1] == max(size) and e[1][1] > -e[1][0], "not on the convention (blade +Y)"
print("the sword %.3f cm from pommel to tip (the source's chain scale %.4f)" % (size[1], chain_scale))
# against the asset it replaces: the first export (the blade alone) must come out unchanged on its
# vertices; the whole sword with the grip in its points must come out turned back; a re-run unchanged
if len(old) == n_blade:
    refs = [([om.MPoint(p) for p in old], "the blade-only asset, unchanged")]
elif len(old) == n_blade + n_handle:
    refs = [([om.MPoint(p) * grip.inverse() for p in old], "the grip-in-its-points asset, turned back"),
            ([om.MPoint(p) for p in old], "a re-run's asset, unchanged"),
            ([om.MPoint(om.MVector(p) * chain_scale) for p in old],
             "the shrunk asset at the chain's scale x%.4f" % chain_scale)]
else:
    raise RuntimeError("the existing asset has %d vertices: neither the blade (%d) nor the whole sword" % (len(old), n_blade))
best = min((max(pts[i].distanceTo(ref[i]) for i in range(min(len(ref), len(pts)))), what) for ref, what in refs)
assert best[0] < 1e-3, "the sword matches none of %s: %.4f" % ([w for _, w in refs], best[0])
print("the sword = %s to %.2e cm" % (best[1], best[0]))
# the axes on the geometry: the guard (the widest part across the blade) lies along X, not X+Z
across = [(abs(p.x), abs(p.z)) for p in pts]
print("across the blade: X %.2f  Z %.2f" % (max(a for a, _ in across), max(b for _, b in across)))
assert max(a for a, _ in across) > 2 * max(b for _, b in across), "the guard is not on X"
# the handle: along the bone around the origin, inside the blade's width
hy = [pts[i].y for i in range(n_blade, len(pts))]
print("the handle Y %.2f..%.2f" % (min(hy), max(hy)))
print("DONE: %.2f MB fbx" % (os.path.getsize(SWORD) / 1e6))
