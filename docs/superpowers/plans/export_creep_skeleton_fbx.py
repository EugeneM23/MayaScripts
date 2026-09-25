"""The Creep's clean skeleton with its geometry, as an FBX: the skeletal mesh on its own.

    mayapy export_creep_skeleton_fbx.py [<out .fbx>] [--overwrite]

2026-09-24, the animator: «выгрузи мне куда-то чистый скелет крипа с геометрией» -- «в fbx».
mayapy STANDALONE: `assets/Creep_Skeleton.ma` imported into an empty scene (plain names, as Add
Character brings it), `|root` (91 joints) and `|Creep` (the five skinned meshes) exported with their
skins at the bind -- SKM_Manny_Simple's pose -- and the meshes' normals, with smoothing groups (Unreal
warns about an FBX without them).  Then read back in a fresh scene: joints, skins, every vertex where
the asset has it, the normals.  Maya's importer brings the normals back UNLOCKED and recomputed, and
they match the asset's to a median of 0.0001-0.0007 deg -- except on the body's one pair of
coincident faces (336 and 27584 share vertices 44, 47, 1655: a defect of the source model, two
back-to-back triangles of 0.07 cm2), where which face gets which normal is a coin toss on import;
such pairs are found and named, not failed on.  (58 pairs on the body, 2 on the back; only 336/27584 came
back visibly different.)  Elsewhere the smoothing-group recompute leaves them within 0.22 deg.

The same evening the animator: «скелет выгрузился без групп сглаживания на геометрии».  The file
did carry a smoothing layer per mesh -- of zeros: every edge of the Creep meshes was HARD in Maya
(already in the animator's creature scene, under locked normals, which is why nothing looked
wrong there), and an FBX's smoothing layer is the edge flags.  The assets carry the source FBX's
smoothing since (`repair_creep_assets.py`; hard = the seams where the normals split, and the
borders), and the read-back now checks it: the edges come back hard exactly where the asset has
them, a mesh with every edge hard is a failure.  `--overwrite` replaces an existing file.

Since 2026-09-25 in CASCADEUR'S LAYOUT, as every export of ours (maya_uebridge.fbxlayout): the
skeleton under a Null rotated -90 X, `root` with no orientation of its own, the meshes at
world level beside it -- the file Cascadeur itself writes for this creature (its Null is
`SKM_Manny_Simple` there). The Null is `Armature` since the evening («появилось требование чтобы
верхняя группа называлась Armature»; it was `Creep` that morning).

And ONE material on all five meshes since the same evening («нужно на все наши модели и риги
настроить единый шейдер ... сейчас при экспорте в каскадер модель выглядит темной и на модели
много материалов»): the export carried three -- a grey blinn at 0.4 effective on the arms and face,
a red one on the back and FBX's `Default_Material` on the body, which wore none -- every one with
a ReflectionFactor of 0.5. Now the one shader (maya_scenesetup.colour: SHADER wearing LOOK, the
values Cascadeur writes in its own FBX) in a light neutral grey, NEUTRAL, and the read-back checks
it: one material, on all five, phong, diffuse 1, specular 0.2, no reflection.
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
ASSET = os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim", "assets", "Creep_Skeleton.ma")).replace("\\", "/")
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = (ARGS[0] if ARGS else "C:/!!!Work/Animations/Rigs/Characters/Creep_Skeleton.fbx").replace("\\", "/")
OVERWRITE = "--overwrite" in sys.argv
MESHES = ("Creep_Body", "Creep_Back", "Creep_Arm_L", "Creep_Arm_R", "Creep_Face")


def shown(name):
    tr = cmds.ls(name, "*:" + name, type="transform", long=True)[0]
    live = [s for s in cmds.listRelatives(tr, shapes=True, fullPath=True) if not cmds.getAttr(s + ".intermediateObject")][0]
    sel = om.MSelectionList(); sel.add(live)
    fn = om.MFnMesh(sel.getDagPath(0))
    counts, ids = fn.getNormalIds()
    normals = fn.getNormals(om.MSpace.kWorld)
    locked = sum(1 for i in range(fn.numNormals) if fn.isNormalLocked(i))
    return fn.getPoints(om.MSpace.kWorld), [om.MVector(normals[i]) for i in ids], locked


def hard_edges(name):
    tr = cmds.ls(name, "*:" + name, type="transform", long=True)[0]
    live = [s for s in cmds.listRelatives(tr, shapes=True, fullPath=True) if not cmds.getAttr(s + ".intermediateObject")][0]
    sel = om.MSelectionList(); sel.add(live)
    fn = om.MFnMesh(sel.getDagPath(0))
    return sum(1 for e in range(fn.numEdges) if not fn.isEdgeSmooth(e)), fn.numEdges


cmds.file(new=True, force=True)
cmds.file(ASSET, i=True, executeScriptNodes=False)
joints = cmds.ls("|root", dag=True, type="joint", long=True)
before = dict((m, shown(m)) for m in MESHES)
hard_before = dict((m, hard_edges(m)) for m in MESHES)
print("the asset's smoothing (hard, edges):", hard_before)
if any(h == n for h, n in hard_before.values()):
    raise RuntimeError("a mesh has every edge hard -- no smoothing to export (repair_creep_assets.py)")
# our own bookkeeping stays home: the colour marker on the material would ride into the FBX as a user
# property (and the importer then warns about it)
for mat in cmds.ls(materials=True):
    if cmds.attributeQuery("skeldarColour", node=mat, exists=True):
        cmds.deleteAttr(mat + ".skeldarColour")
print("asset: %d joints, %d skins" % (len(joints), len(cmds.ls(type="skinCluster"))))

if os.path.exists(OUT) and not OVERWRITE:
    raise RuntimeError("%s exists -- not overwriting it (--overwrite)" % OUT)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))
from maya_uebridge import fbxlayout
from maya_scenesetup import colour
# the one shader on every mesh, one material for the whole character; its marker stays home too
NEUTRAL = (0.8, 0.8, 0.8)                  # Cascadeur's own default base colour
material, engine = colour.make_material(NEUTRAL, "Creep")
cmds.sets([s for m in MESHES for s in cmds.listRelatives(cmds.ls(m, type="transform", long=True)[0], shapes=True, fullPath=True)
           if not cmds.getAttr(s + ".intermediateObject")], edit=True, forceElement=engine)
cmds.deleteAttr(material + "." + colour.MARKER)
material = cmds.rename(material, "Creep_Mat")
# the meshes to world level beside the skeleton, as in Cascadeur's file; the emptied |Creep group
# goes (it would also take the wrapper's name)
for m in MESHES:
    tr = cmds.ls(m, type="transform", long=True)[0]
    if cmds.listRelatives(tr, parent=True):
        cmds.parent(tr, world=True)
if cmds.objExists("|Creep") and not cmds.listRelatives("|Creep", children=True):
    cmds.delete("|Creep")
mesh_nodes = [cmds.ls(m, type="transform", long=True)[0] for m in MESHES]
folder = os.path.dirname(OUT)
if not os.path.isdir(folder):
    os.makedirs(folder)
mel.eval("FBXResetExport")
for option in ("FBXExportSkins -v true", "FBXExportShapes -v true", "FBXExportSmoothingGroups -v true", "FBXExportHardEdges -v false",
               "FBXExportSmoothMesh -v false", "FBXExportTangents -v false", "FBXExportInputConnections -v false",
               "FBXExportConstraints -v false", "FBXExportCameras -v false", "FBXExportLights -v false",
               "FBXExportBakeComplexAnimation -v false", "FBXExportEmbeddedTextures -v false",
               "FBXExportSkeletonDefinitions -v true", "FBXExportUpAxis y", "FBXExportInAscii -v false"):
    mel.eval(option)
with fbxlayout.wrapped("|root", fbxlayout.WRAPPER_NAME) as (wrapper, note):
    assert wrapper, note
    # the wrapper is part of the skeleton's hierarchy now, and the exporter drops the bind pose
    # whole over a node missing from it (trap 79; measured again: «Unable to find the bind pose
    # for : / Creep»): the pose is saved again over the wrapper and every joint, the skins moved
    # onto it -- in this throwaway scene only
    members = [wrapper] + cmds.ls(wrapper, dag=True, type="joint", long=True)
    pose = cmds.dagPose(members, save=True, bindPose=True, name="exportBindPose")
    pose = pose[0] if isinstance(pose, (list, tuple)) else pose
    strays = [m for m in cmds.ls(cmds.dagPose(pose, q=True, members=True) or [], long=True)
              if m not in members]
    if strays:
        cmds.dagPose(strays, remove=True, name=pose)
    for sc in cmds.ls(type="skinCluster"):
        cmds.connectAttr(pose + ".message", sc + ".bindPose", force=True)
    cmds.select([wrapper] + mesh_nodes, replace=True)
    mel.eval('FBXExport -f "%s" -s' % OUT)
print("exported %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))

# read back
cmds.file(new=True, force=True)
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % OUT)
back_joints = cmds.ls(type="joint")
skins = cmds.ls(type="skinCluster")
back_root = cmds.ls("root", type="joint", long=True)[0]
wrapper_back = cmds.listRelatives(back_root, parent=True, fullPath=True) or []
print("read back: root under %s turned %s, root jointOrient %s" % (
    wrapper_back, [round(v, 3) for v in cmds.getAttr(wrapper_back[0] + ".rotate")[0]] if wrapper_back else None,
    [round(v, 4) for v in cmds.getAttr(back_root + ".jointOrient")[0]]))
assert wrapper_back == ["|" + fbxlayout.WRAPPER_NAME], "the skeleton is not under the %s Null" % fbxlayout.WRAPPER_NAME
assert max(abs(v) for v in cmds.getAttr(back_root + ".jointOrient")[0]) < 1e-3, "root carries an orientation"

worst_p = worst_n = 0.0
for m in MESHES:
    pts, nrm, locked = shown(m)
    p0, n0, _ = before[m]
    print("   %-12s normals locked on the way back: %d of %d" % (m, locked, len(nrm)))
    worst_p = max(worst_p, max(a.distanceTo(b) for a, b in zip(pts, p0)))
    # faces standing on the same vertices as another face (coincident duplicates) are skipped, and named
    tr = cmds.ls(m, type="transform", long=True)[0]
    live = [x for x in cmds.listRelatives(tr, shapes=True, fullPath=True) if not cmds.getAttr(x + ".intermediateObject")][0]
    sel = om.MSelectionList(); sel.add(live)
    counts, verts = om.MFnMesh(sel.getDagPath(0)).getVertices()
    owner, seen, k = [], {}, 0
    for f, c in enumerate(counts):
        key = tuple(sorted(verts[k:k + c]))
        seen.setdefault(key, []).append(f)
        owner += [key] * c
        k += c
    doubled = set(key for key, fs in seen.items() if len(fs) > 1)
    if doubled:
        print("   %-12s coincident faces (the model's own), skipped: %s" % (m, [seen[key] for key in doubled]))
    worst_n = max(worst_n, max(math.degrees(a.angle(b)) for a, b, o in zip(nrm, n0, owner)
                               if o not in doubled and a.length() > 1e-9 and b.length() > 1e-9))
print("read back: %d joints, %d skins, the meshes %s" % (len(back_joints), len(skins), [m for m in MESHES if cmds.objExists(m)]))
print("every vertex where the asset has it: worst %.2e cm; normals the asset's: worst %.4f deg" % (worst_p, worst_n))
hard_back = dict((m, hard_edges(m)) for m in MESHES)
print("smoothing read back (hard, edges):", hard_back)
assert hard_back == hard_before, "the smoothing did not survive the round trip"
# one material on all five meshes, wearing the one shader's look
worn = {}
for m in MESHES:
    tr = cmds.ls(m, type="transform", long=True)[0]
    live = [x for x in cmds.listRelatives(tr, shapes=True, fullPath=True) if not cmds.getAttr(x + ".intermediateObject")][0]
    for sg in set(cmds.listConnections(live, type="shadingEngine") or []):
        for mat in cmds.listConnections(sg + ".surfaceShader") or []:
            worn.setdefault(mat, []).append(m)
look = dict((a, cmds.getAttr(list(worn)[0] + "." + a)) for a in ("color", "diffuse", "specularColor", "cosinePower", "reflectivity")
            if len(worn) == 1 and cmds.attributeQuery(a, node=list(worn)[0], exists=True))
print("materials read back: %s | %s %s" % (dict((k, len(v)) for k, v in worn.items()),
                                           cmds.nodeType(list(worn)[0]) if worn else None, look))
assert len(worn) == 1 and sorted(list(worn.values())[0]) == sorted(MESHES), "not ONE material on all five meshes"
assert cmds.nodeType(list(worn)[0]) == colour.SHADER, "the material came back as %s" % cmds.nodeType(list(worn)[0])
# 0.5 deg: the importer recomputes the normals through the smoothing groups (measured worst 0.22)
assert len(back_joints) == len(joints) and len(skins) == 5 and worst_p < 1e-3 and worst_n < 0.5
print("OK")
