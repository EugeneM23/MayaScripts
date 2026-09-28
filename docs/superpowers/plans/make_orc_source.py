"""The Orc Marauder's skeleton and skin, prepared for its AdvancedSkeleton rig.

    mayapy make_orc_source.py C:/!!!Work/MayaScripts/sources/orc/SK_Orc_Marauder_F.FBX <out .mb>

mayapy STANDALONE.  2026-09-25, the animator: «В открытом проекте в Unreal есть персонаж
SK_Orc_Marauder_F его скелет совпадает с нашим manny rig ... добавим к нам в проект еще один
риг "ORC"».  The FBX is the animator's own export of `/Game/Orc_Marauder/Meshes/SK_Orc_Marauder_F`
(MyProject2): 91 joints on Manny's names and hierarchy (AB_Armor_Shoulder_L/R extra, the four
helper bones missing), one skin in five LODs, 56 morph targets.  What this makes of it:

- **LOD0 only**, as `|Orc_Body` at world level: an animator needs one mesh, and the LODs are
  Unreal's business.  LOD1-4 go with their skins and blendShapes; the 280 morph-target meshes
  the importer laid out at world level go too -- LOD0's blendShape keeps its 56 targets (52
  ARKit face shapes, 4 elbow correctives) as deltas, weights at 0, nothing driving them.
- **The skeleton at world level in Manny's shape**: the importer's wrapper (rotateX -90, the
  Z-up turn) out, its turn in root's jointOrient, root's rotate zero -- Manny_Rig.ma's and
  Creep_Rig.ma's shape.  Every joint's world matrix is recorded by UUID and checked after; the
  mesh's too, written through the importer's locks (CLAUDE.md trap 51).
- **The four helper bones Manny has and the orc lacks** (the animator's call: «все четыре»):
  camera_root / camera_bone under root, weapon_r under hand_r, weapon_l under hand_l, each
  with Manny's own LOCAL values from `manny_skeleton_template.json` -- where Manny's bone
  stands relative to its parent, so every catalog weapon sits in the orc's hand as in Manny's.
  Not skin influences.
- AB_Armor_Shoulder_L/R stay as they are, under the clavicles (the animator: they ride the
  clavicle, no control).
- The bind pose saved again, whole, over all 95 joints (trap 79), the joints in a display
  layer `Orc_Skeleton`, the dead-path normal map (D:/Characters/ORC/...) dropped, and the
  Blender (Auto-Rig Pro) properties the joints carried through Unreal deleted -- they rode
  into every animation export.

Refuses (raises) if the skin is off its bind, the mesh moved, or a joint moved.
"""
import json
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim", "assets", "manny_skeleton_template.json"))
SRC = sys.argv[1].replace("\\", "/")
OUT = os.path.abspath(sys.argv[2]).replace("\\", "/")
MESH = "Orc_Body"
LAYER = "Orc_Skeleton"
HELPERS = ("camera_root", "camera_bone", "weapon_r", "weapon_l")   # parents first


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


for p in ("fbxmaya",):
    cmds.loadPlugin(p, quiet=True)
cmds.file(new=True, force=True)
mel.eval("FBXResetImport")
mel.eval("FBXImportMode -v add")
mel.eval('FBXImport -f "%s"' % SRC)

wrapper = "|SK_Orc_Marauder_F"
lod0 = [t for t in cmds.ls("SK_Orc_Marauder_F_LOD0", long=True, type="transform")]
assert cmds.objExists(wrapper) and len(lod0) == 1, (cmds.ls(assemblies=True)[:5], lod0)
lod0 = lod0[0]
shape0 = cmds.listRelatives(lod0, shapes=True, fullPath=True, noIntermediate=True)[0]
skin0 = cmds.ls(cmds.listHistory(shape0, pruneDagObjects=True), type="skinCluster")[0]
bs0 = cmds.ls(cmds.listHistory(shape0, pruneDagObjects=True), type="blendShape")[0]
mesh_uid = cmds.ls(lod0, uuid=True)[0]

# --- what goes: the LODs past 0 with their deformers, the morph-target meshes at world level
keep_assemblies = {wrapper, "|persp", "|top", "|front", "|side"}
targets = [a for a in cmds.ls(assemblies=True, long=True) if a not in keep_assemblies]
lods = [t for t in cmds.ls("SK_Orc_Marauder_F_LOD*", long=True, type="transform") if t != lod0]
other_deformers = []
for t in lods:
    for s in cmds.listRelatives(t, shapes=True, fullPath=True) or []:
        other_deformers += cmds.ls(cmds.listHistory(s, pruneDagObjects=True) or [], type=("skinCluster", "blendShape"))
n_targets = len(cmds.blendShape(bs0, q=True, target=True) or [])
cmds.delete(sorted(set(other_deformers)))
cmds.delete(lods + targets)
# the blendShape keeps its targets as deltas once their meshes are gone -- measured below
assert len(cmds.blendShape(bs0, q=True, weight=True) or []) == n_targets, "the blendShape lost its targets"

# --- the rest pose, recorded by UUID before anything is re-parented (trap 16)
joints = cmds.ls(wrapper, dag=True, type="joint", long=True)
rest = dict((cmds.ls(j, uuid=True)[0], wm(j)) for j in joints)
mesh_before = points(shape0)
edges_before = hard_edges(shape0)
print("imported: %d joints, LOD0 %d verts, %d morph targets, %d hard edges; bind off by %.2e"
      % (len(joints), len(mesh_before), n_targets, edges_before, bind_error()))

# --- the skeleton and the mesh out of the wrapper (Manny's shape: root's jointOrient holds the turn)
root = cmds.ls(wrapper + "|root", long=True)[0]
root_uid = cmds.ls(root, uuid=True)[0]
W = wm(root)
mesh_w = cmds.xform(lod0, q=True, ws=True, matrix=True)
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
cmds.delete(wrapper)
mesh = cmds.rename(mesh, MESH)
mesh = cmds.ls(mesh_uid, long=True)[0]
for s in cmds.listRelatives(mesh, shapes=True, fullPath=True) or []:
    cmds.rename(s, MESH + ("ShapeOrig" if cmds.getAttr(s + ".intermediateObject") else "Shape"))
cmds.rename(skin0, MESH + "_skinCluster")
cmds.rename(bs0, MESH + "_blendShapes")
shape0 = cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True)[0]

drift = max(mdiff(wm(cmds.ls(u, long=True)[0]), m) for u, m in rest.items())
mesh_after = points(shape0)
moved = max(mesh_before[i].distanceTo(mesh_after[i]) for i in range(len(mesh_before)))
root = cmds.ls(root_uid, long=True)[0]
print("flattened: root %s jointOrient %s rotate %s; joints drift %.2e, mesh moved %.2e cm"
      % (root, [round(v, 4) for v in cmds.getAttr(root + ".jointOrient")[0]],
         [round(v, 4) for v in cmds.getAttr(root + ".rotate")[0]], drift, moved))
if drift > 1e-4 or moved > 1e-3:
    raise RuntimeError("the flatten moved something: joints %.2e, mesh %.2e" % (drift, moved))

# --- the four helper bones, on Manny's local values
tmpl = dict((j["name"], j) for j in json.load(open(TEMPLATE))["joints"])


def bone(name):
    found = [j for j in cmds.ls(root, dag=True, type="joint", long=True) if j.split("|")[-1] == name]
    return found[0] if found else None


for name in HELPERS:
    if bone(name):
        continue
    t = tmpl[name]
    parent = bone(t["parent"])
    j = cmds.createNode("joint", name=name, parent=parent, skipSelect=True)
    j = cmds.ls(j, long=True)[0]
    cmds.setAttr(j + ".rotateOrder", t["rotateOrder"])
    cmds.setAttr(j + ".translate", *t["translate"])
    cmds.setAttr(j + ".rotate", *t["rotate"])
    cmds.setAttr(j + ".jointOrient", *t["jointOrient"])
    cmds.setAttr(j + ".radius", t["radius"])
    cmds.setAttr(j + ".segmentScaleCompensate", t["segmentScaleCompensate"])
    # Manny's own relation to the parent, compared world-to-world
    mine = wm(j) * wm(parent).inverse()
    manny = om.MMatrix(t["world_matrix"]) * om.MMatrix(tmpl[t["parent"]]["world_matrix"]).inverse()
    print("  %-12s under %-12s at %s  (relative to the parent as on Manny to %.2e)"
          % (name, t["parent"], [round(v, 2) for v in cmds.xform(j, q=True, ws=True, t=True)], mdiff(mine, manny)))

# the orc's hands against Manny's, for the weapon bones' sake
for h in ("hand_r", "hand_l"):
    q1 = om.MTransformationMatrix(wm(bone(h))).rotation(asQuaternion=True)
    q2 = om.MTransformationMatrix(om.MMatrix(tmpl[h]["world_matrix"])).rotation(asQuaternion=True)
    a = math.degrees(2 * math.acos(min(1.0, abs((q1.inverse() * q2).w))))
    d = (om.MVector(cmds.xform(bone(h), q=True, ws=True, t=True)) - om.MVector(tmpl[h]["world_position"])).length()
    print("  %s against Manny's: %.4f cm, %.4f deg" % (h, d, a))

# --- the twist bones' fractions along their segments (AdvancedSkeleton's Part joints take one step each)
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

# --- Blender's Auto-Rig Pro properties, carried on the joints through Unreal's FBX (root: flip_fluid,
# set, binded, arp_rig_name; 11 helpers: ori_name).  The FBX exporter writes a joint's user attributes
# into every animation file (measured: `Orc|root.flip_fluid` in the first export of this rig), and
# Unreal reads the root's properties as the game's own data (trap 40).  The two attributes Maya and
# its FBX plugin put on every joint themselves stay.
MAYA_OWN = ("filmboxTypeID", "lockInfluenceWeights")
stripped = {}
for j in cmds.ls(root, dag=True, type="joint", long=True):
    for a in cmds.listAttr(j, userDefined=True) or []:
        if a not in MAYA_OWN and cmds.attributeQuery(a, node=j, exists=True):
            cmds.setAttr(j + "." + a, lock=False)
            cmds.deleteAttr(j + "." + a)
            stripped[a] = stripped.get(a, 0) + 1
print("  Blender's properties off the joints: %s" % stripped)

# --- the texture whose path is dead on every machine but the author's
for f in cmds.ls(type="file"):
    print("  dropped texture %s (%s)" % (f, cmds.getAttr(f + ".fileTextureName")))
    helpers = (cmds.listConnections(f, type="place2dTexture") or []) + (cmds.listConnections(f, type="bump2d") or [])
    cmds.delete([n for n in sorted(set([f] + helpers)) if cmds.objExists(n)])

# --- the bind pose, whole (trap 79), and the layer
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
new = cmds.rename(new, "bindPose1")
lay = cmds.createDisplayLayer(name=LAYER, empty=True)
cmds.editDisplayLayerMembers(lay, all_joints, noRecurse=True)

# --- the blendShape still carries its shapes: one target at weight 1 must move vertices
bs = MESH + "_blendShapes"
cmds.setAttr(bs + ".weight[%d]" % 0, 1.0)
cmds.dgdirty(shape0)
bent = points(shape0)
cmds.setAttr(bs + ".weight[%d]" % 0, 0.0)
cmds.dgdirty(shape0)
shift = max(bent[i].distanceTo(mesh_after[i]) for i in range(len(bent)))
alias = cmds.aliasAttr(bs, q=True) or []
print("blendShape %s: %d targets, target 0 (%s) moves the mesh up to %.3f cm"
      % (bs, n_targets, alias[0] if alias else "?", shift))
if shift < 1e-3:
    raise RuntimeError("the blendShape lost its target data with the target meshes")

hard = hard_edges(shape0)
print("joints %d, bind pose %s with %d members, skin off its bind %.2e, hard edges %d (was %d)"
      % (len(all_joints), new, len(cmds.dagPose(new, q=True, members=True) or []), bind_error(), hard, edges_before))
if bind_error() > 1e-4 or hard != edges_before or len(all_joints) != 95:
    raise RuntimeError("the source is not clean")
print("assemblies:", cmds.ls(assemblies=True))
if not os.path.isdir(os.path.dirname(OUT)):
    os.makedirs(os.path.dirname(OUT))
cmds.file(rename=OUT)
cmds.file(save=True, type="mayaBinary", force=True)
print("saved", OUT, "%.1f MB" % (os.path.getsize(OUT) / 1e6))
