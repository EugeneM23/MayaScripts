"""The second Creep's skeleton and skin, prepared for its AdvancedSkeleton rig.

    mayapy make_creep2_source.py C:/!!!Work/MayaScripts/sources/creep2/SK_Creep_skinned.FBX <out .mb>

mayapy STANDALONE.  2026-10-27, the animator, with `Downloads/SK_Creep_skinned.FBX` imported into
a Maya on port 7003: «новый крип его нужно встроить в наш пайплайн, риг скелет, карточки»; asked,
a SECOND Creep beside the shipped one, in a palette colour (its textures are not on this machine).
Measured first: an Unreal export (materials MI_Creep_Body / _Chainmail / _Head, their normal maps
on a colleague's `C:/Users/User/Downloads/creep_textures/`), 91 joints on Manny's names and
hierarchy under a -90 X wrapper (the Creep's own Cascadeur layout: root at (0.0017, -2.4012, 0)),
one skinned mesh of 102822 vertices.  NOT the shipped Creep re-posed: the pelvis 5.3 cm lower,
the calves 3.3 and the forearms 2.2 cm shorter, the hands 1.8 cm longer -- its own body.  So it
gets its own rig, the Orc's road (make_orc_source.py):

- **the skeleton at world level in Manny's shape**: the wrapper out, its turn in root's
  jointOrient, root's rotate zero; every joint's world matrix recorded by UUID and checked after;
  the mesh's too, written through the importer's locks (trap 51), renamed `Creep2_Body`;
- **camera_root / camera_bone** (Manny has them, this file does not) on Manny's own local values
  from `manny_skeleton_template.json`; weapon_r / weapon_l are the file's own, turned a quarter
  about their own X into UE's socket (2026-09-30's standard: the grip line along +-Z; the file
  holds it along +Y, the shipped Creep's convention before make_creep_weapon_sockets.py);
- the user attributes Unreal carried on the joints deleted (they ride into every export);
- the dead-path normal maps dropped, the three materials kept (Add paints a palette colour);
- the bind pose saved again, whole, over every joint (trap 79), the joints in a display layer
  `Creep2_Skeleton`.

Refuses (raises) if the skin is off its bind, the mesh moved, or a joint moved.
"""
import json
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim", "assets", "manny_skeleton_template.json"))
SRC = sys.argv[1].replace("\\", "/")
OUT = os.path.abspath(sys.argv[2]).replace("\\", "/")
WRAPPER = "|SK_Creep_skinned"
MESH = "Creep2_Body"
LAYER = "Creep2_Skeleton"
HELPERS = ("camera_root", "camera_bone")   # parents first
JOINTS = 93


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def points(shape):
    sel = om.MSelectionList(); sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)


def hard_edges(shape):
    sel = om.MSelectionList(); sel.add(shape)
    fn = om.MFnMesh(sel.getDagPath(0))
    return sum(1 for e in range(fn.numEdges) if not fn.isEdgeSmooth(e))


def bind_error():
    worst = 0.0
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
                worst = max(worst, mdiff(m, om.MMatrix()))
    return worst


def unlock_all(node):
    locked = [a for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz") if cmds.getAttr(node + "." + a, lock=True)]
    for a in locked:
        cmds.setAttr(node + "." + a, lock=False)
    return locked


def turn(a, b):
    qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(min(1.0, abs((qa.inverse() * qb).w))))


cmds.loadPlugin("fbxmaya", quiet=True)
cmds.file(new=True, force=True)
mel.eval("FBXResetImport")
mel.eval("FBXImportMode -v add")
mel.eval('FBXImport -f "%s"' % SRC)

assert cmds.objExists(WRAPPER), cmds.ls(assemblies=True)
meshes = [cmds.listRelatives(s, parent=True, fullPath=True)[0]
          for s in cmds.ls(WRAPPER, dag=True, type="mesh", long=True, noIntermediate=True)]
assert len(meshes) == 1, meshes
mesh = meshes[0]
mesh_uid = cmds.ls(mesh, uuid=True)[0]
shape0 = cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True)[0]
skin0 = cmds.ls(cmds.listHistory(shape0, pruneDagObjects=True), type="skinCluster")[0]
print("imported: assemblies %s, display layers %s" % (cmds.ls(assemblies=True), cmds.ls(type="displayLayer")))

joints = cmds.ls(WRAPPER, dag=True, type="joint", long=True)
rest = dict((cmds.ls(j, uuid=True)[0], wm(j)) for j in joints)
mesh_before = points(shape0)
edges_before = hard_edges(shape0)
print("imported: %d joints, %d verts, %d hard edges, max %d influences; bind off by %.2e"
      % (len(joints), len(mesh_before), edges_before, cmds.getAttr(skin0 + ".maxInfluences"), bind_error()))

# --- the skeleton and the mesh out of the wrapper (Manny's shape: root's jointOrient holds the turn)
root = cmds.ls(WRAPPER + "|root", long=True)[0]
root_uid = cmds.ls(root, uuid=True)[0]
W = wm(root)
mesh_w = cmds.xform(mesh, q=True, ws=True, matrix=True)
cmds.parent(root, world=True)
root = cmds.ls(root_uid, long=True)[0]
e = om.MTransformationMatrix(W).rotation(asQuaternion=False)
cmds.setAttr(root + ".rotate", 0, 0, 0)
cmds.setAttr(root + ".jointOrient", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
cmds.setAttr(root + ".translate", W.getElement(3, 0), W.getElement(3, 1), W.getElement(3, 2))
cmds.parent(cmds.ls(mesh_uid, long=True)[0], world=True)
mesh = cmds.ls(mesh_uid, long=True)[0]
locks = unlock_all(mesh)
cmds.xform(mesh, ws=True, matrix=mesh_w)
for a in locks:
    cmds.setAttr(mesh + "." + a, lock=True)
cmds.delete(WRAPPER)
cmds.rename(mesh, MESH)
mesh = cmds.ls(mesh_uid, long=True)[0]
for s in cmds.listRelatives(mesh, shapes=True, fullPath=True) or []:
    cmds.rename(s, MESH + ("ShapeOrig" if cmds.getAttr(s + ".intermediateObject") else "Shape"))
cmds.rename(skin0, MESH + "_skinCluster")
shape0 = cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True)[0]

drift = max(mdiff(wm(cmds.ls(u, long=True)[0]), m) for u, m in rest.items())
mesh_after = points(shape0)
moved = max(mesh_before[i].distanceTo(mesh_after[i]) for i in range(len(mesh_before)))
root = cmds.ls(root_uid, long=True)[0]
print("flattened: root %s jointOrient %s; joints drift %.2e, mesh moved %.2e cm"
      % (root, [round(v, 4) for v in cmds.getAttr(root + ".jointOrient")[0]], drift, moved))
if drift > 1e-4 or moved > 1e-3:
    raise RuntimeError("the flatten moved something: joints %.2e, mesh %.2e" % (drift, moved))

tmpl = dict((j["name"], j) for j in json.load(open(TEMPLATE))["joints"])


def bone(name):
    found = [j for j in cmds.ls(root, dag=True, type="joint", long=True) if j.split("|")[-1] == name]
    return found[0] if found else None


for name in HELPERS:
    if bone(name):
        continue
    t = tmpl[name]
    parent = bone(t["parent"])
    j = cmds.ls(cmds.createNode("joint", name=name, parent=parent, skipSelect=True), long=True)[0]
    cmds.setAttr(j + ".rotateOrder", t["rotateOrder"])
    cmds.setAttr(j + ".translate", *t["translate"])
    cmds.setAttr(j + ".rotate", *t["rotate"])
    cmds.setAttr(j + ".jointOrient", *t["jointOrient"])
    cmds.setAttr(j + ".radius", t["radius"])
    cmds.setAttr(j + ".segmentScaleCompensate", t["segmentScaleCompensate"])
    mine = wm(j) * wm(parent).inverse()
    manny = om.MMatrix(t["world_matrix"]) * om.MMatrix(tmpl[t["parent"]]["world_matrix"]).inverse()
    print("  %-12s added under %-12s at %s (relative to the parent as on Manny to %.2e)"
          % (name, t["parent"], [round(v, 2) for v in cmds.xform(j, q=True, ws=True, t=True)], mdiff(mine, manny)))

# the weapon bones in their hands against Manny's (the socket standard), the hands against Manny's
for b, p in (("weapon_r", "hand_r"), ("weapon_l", "hand_l")):
    mine = wm(bone(b)) * wm(bone(p)).inverse()
    manny = om.MMatrix(tmpl[b]["world_matrix"]) * om.MMatrix(tmpl[p]["world_matrix"]).inverse()
    print("  %s in %s: %.3f cm, %.3f deg from Manny's" % (
        b, p, (om.MVector(mine.getElement(3, 0), mine.getElement(3, 1), mine.getElement(3, 2)) -
               om.MVector(manny.getElement(3, 0), manny.getElement(3, 1), manny.getElement(3, 2))).length(),
        turn(mine, manny)))


def grip(side, frame):
    """The fist's grip line pinky_01 -> index_01 in the axes of `frame`."""
    v = (om.MVector(cmds.xform(bone("index_01_" + side), q=True, ws=True, t=True)) -
         om.MVector(cmds.xform(bone("pinky_01_" + side), q=True, ws=True, t=True))).normal()
    m = om.MTransformationMatrix(frame)
    m.setTranslation(om.MVector(), om.MSpace.kTransform)
    return v * m.asMatrix().inverse()


# The weapon sockets in UE's convention (2026-09-30, one socket for every rig): the grip line along
# +Z in weapon_r, -Z in weapon_l. This file's hold it along +Y - the shipped Creep's convention before
# make_creep_weapon_sockets.py turned them - so each bone is turned a quarter about its own X (new
# local = Rx . old local), the bone's place unchanged. Both are zero-weight influences of the skin:
# their bindPreMatrix is re-expressed as the new WM^-1, no vertex moves.
WANT = {"r": 1.0, "l": -1.0}
for side in ("r", "l"):
    w = bone("weapon_" + side)
    k = grip(side, wm(w))
    assert max(abs(v) for v in cmds.getAttr(w + ".jointOrient")[0]) < 1e-9 and cmds.getAttr(w + ".rotateOrder") == 0, w
    if abs(k.z) > 0.9 and k.z * WANT[side] > 0:
        print("  weapon_%s already in UE's convention (grip line %s)" % (side, [round(c, 3) for c in k]))
        continue
    if abs(k.y) <= 0.9:
        raise RuntimeError("weapon_%s: the grip line %s lies along neither +-Y nor +-Z" % (side, list(k)))
    place = om.MVector(cmds.xform(w, q=True, ws=True, t=True))
    local = om.MMatrix(cmds.xform(w, q=True, matrix=True, objectSpace=True))
    for degrees in (-90.0, 90.0):
        q = om.MEulerRotation(math.radians(degrees), 0, 0).asMatrix()
        new = om.MTransformationMatrix(q * local)
        e = new.rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
        cmds.setAttr(w + ".rotate", *[math.degrees(v) for v in (e.x, e.y, e.z)], type="double3")
        after = grip(side, wm(w))
        if after.z * WANT[side] > 0.9:
            break
    else:
        raise RuntimeError("weapon_%s: no quarter turn about X brings %s onto Z" % (side, list(k)))
    assert (om.MVector(cmds.xform(w, q=True, ws=True, t=True)) - place).length() < 1e-6, w
    for sc in sorted(set(cmds.listConnections(w + ".worldMatrix", type="skinCluster") or [])):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False) or []
            if src and cmds.ls(src[0], long=True)[0] == w:
                cmds.setAttr("%s.bindPreMatrix[%d]" % (sc, idx), list(wm(w).inverse()), type="matrix")
    print("  weapon_%s turned %+.0f about its X: grip line %s -> %s" % (
        side, degrees, [round(c, 3) for c in k], [round(c, 3) for c in after]))
for h in ("hand_r", "hand_l"):
    d = (om.MVector(cmds.xform(bone(h), q=True, ws=True, t=True)) - om.MVector(tmpl[h]["world_position"])).length()
    print("  %s against Manny's: %.3f cm, %.3f deg" % (h, d, turn(wm(bone(h)), om.MMatrix(tmpl[h]["world_matrix"]))))
# the ik helpers: Manny's layout is ik_hand_gun ON hand_r, ik_hand_r on it, ik_hand_l on hand_l
for helper, hand in (("ik_hand_gun", "hand_r"), ("ik_hand_r", "hand_r"), ("ik_hand_l", "hand_l"),
                     ("ik_foot_l", "foot_l"), ("ik_foot_r", "foot_r")):
    print("  %-11s from %-6s %.3f cm, %.3f deg" % (helper, hand, (
        om.MVector(cmds.xform(bone(helper), q=True, ws=True, t=True)) -
        om.MVector(cmds.xform(bone(hand), q=True, ws=True, t=True))).length(), turn(wm(bone(helper)), wm(bone(hand)))))

for seg, end, tw in (("upperarm", "lowerarm", ("upperarm_twist_01", "upperarm_twist_02")),
                     ("lowerarm", "hand", ("lowerarm_twist_02", "lowerarm_twist_01")),
                     ("thigh", "calf", ("thigh_twist_01", "thigh_twist_02")),
                     ("calf", "foot", ("calf_twist_02", "calf_twist_01"))):
    for s in ("_r", "_l"):
        A = om.MVector(cmds.xform(bone(seg + s), q=True, ws=True, t=True))
        E = om.MVector(cmds.xform(bone(end + s), q=True, ws=True, t=True))
        L = E - A
        fr = [((om.MVector(cmds.xform(bone(t + s), q=True, ws=True, t=True)) - A) * L) / (L * L) for t in tw]
        print("  twists %-10s %s" % (seg + s, ["%.4f" % f for f in fr]))

MAYA_OWN = ("filmboxTypeID", "lockInfluenceWeights")
stripped = {}
for j in cmds.ls(root, dag=True, type="joint", long=True):
    for a in cmds.listAttr(j, userDefined=True) or []:
        if a not in MAYA_OWN and cmds.attributeQuery(a, node=j, exists=True):
            cmds.setAttr(j + "." + a, lock=False)
            cmds.deleteAttr(j + "." + a)
            stripped[a] = stripped.get(a, 0) + 1
print("  user attributes off the joints: %s" % stripped)

for f in cmds.ls(type="file"):
    print("  dropped texture %s (%s)" % (f, cmds.getAttr(f + ".fileTextureName")))
    helpers = (cmds.listConnections(f, type="place2dTexture") or []) + (cmds.listConnections(f, type="bump2d") or [])
    cmds.delete([n for n in sorted(set([f] + helpers)) if cmds.objExists(n)])
for lay in cmds.ls(type="displayLayer"):
    if lay != "defaultLayer" and cmds.objExists(lay):
        cmds.delete(lay)

all_joints = cmds.ls(root, dag=True, type="joint", long=True)
old = set(p for sc in cmds.ls(type="skinCluster") for p in cmds.listConnections(sc + ".bindPose", s=True, d=False) or []
          if cmds.objectType(p) == "dagPose")
new = cmds.dagPose(all_joints, save=True, bindPose=True, name="skeldarBindPose_new")
new = new[0] if isinstance(new, (list, tuple)) else new
strays = [m for m in cmds.ls(cmds.dagPose(new, q=True, members=True) or [], long=True) if cmds.objectType(m) != "joint"]
if strays:
    cmds.dagPose(strays, remove=True, name=new)
for sc in cmds.ls(type="skinCluster"):
    cmds.connectAttr(new + ".message", sc + ".bindPose", force=True)
for pose in old:
    if cmds.objExists(pose):
        cmds.delete(pose)
for pose in cmds.ls(type="dagPose"):
    if pose != new:
        cmds.delete(pose)
new = cmds.rename(new, "bindPose1")
lay = cmds.createDisplayLayer(name=LAYER, empty=True)
cmds.editDisplayLayerMembers(lay, all_joints, noRecurse=True)

hard = hard_edges(shape0)
print("joints %d, bind pose %s with %d members, skin off its bind %.2e, hard edges %d (was %d)"
      % (len(all_joints), new, len(cmds.dagPose(new, q=True, members=True) or []), bind_error(), hard, edges_before))
print("materials:", [m for m in cmds.ls(materials=True) if m not in ("lambert1", "standardSurface1", "particleCloud1", "openPBR_shader1")])
if bind_error() > 1e-3 or hard != edges_before or len(all_joints) != JOINTS:
    raise RuntimeError("the source is not clean")
print("assemblies:", cmds.ls(assemblies=True))
if not os.path.isdir(os.path.dirname(OUT)):
    os.makedirs(os.path.dirname(OUT))
cmds.file(rename=OUT)
cmds.file(save=True, type="mayaBinary", force=True)
print("saved", OUT, "%.1f MB" % (os.path.getsize(OUT) / 1e6))
