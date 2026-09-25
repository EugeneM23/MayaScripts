"""Standalone gates: the shipped Creep -- rig and clean skeleton -- stands in SKM_Manny_Simple's pose.

    mayapy verify_creep_bind_pose.py [<old Creep_Rig.ma, for the weapon-grip comparison>]

2026-09-24, the animator: «исходная поза у рига Creep_Rig:Group и у скелета этого рига не должна
никак отличаться от позы скелета SKM_Manny_Simple ... текущая поза SKM_Manny_Simple должна стать
байнд позой для Creep_Rig:root».  The pose and the five meshes as SKM's skin deforms them there
are in `creep_bind_pose.json.gz` (dumped read-only from the animator's scene).  mayapy
STANDALONE, an empty scene, the catalog's own Add Character:

- the rig: added, its controls at default, every bone the pose names on the pose's world matrix
  (scale stripped -- the original's 1.12-1.32 are not ours), the helpers on their rules, every
  mesh vertex on SKM's deformed vertex, the skin at its bind;
- a positive control: a control turned moves the hand and the mesh, turned back returns them;
- the clean skeleton row: the same bones and the same mesh;
- the weapon bones: weapon_r / weapon_l keep their place IN THE HAND against the old asset (the
  Creep Sword was exported in that frame), when the old asset is given;
- the normals (gates 10, 11): the shown face-vertex normals are SKM's in the pose
  (`creep_bind_normals.json.gz`), and the hand meshes' sit on their surface.
"""
import gzip
import json
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.api.OpenMaya as om

sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))    # rebind_creep_pose, for the smoothing rule
for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(gzip.open(os.path.join(HERE, "creep_bind_pose.json.gz"), "rt", encoding="utf-8"))
NORMALS = json.load(gzip.open(os.path.join(HERE, "creep_bind_normals.json.gz"), "rt", encoding="utf-8"))
OLD = sys.argv[1] if len(sys.argv) > 1 else ""
RULED = ("ik_hand_gun", "ik_hand_r", "ik_hand_l", "ik_foot_r", "ik_foot_l", "weapon_r", "weapon_l", "weapon_test")
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def unscaled(m):
    m = om.MMatrix(m)
    rows = []
    for r in range(3):
        v = om.MVector(m.getElement(r, 0), m.getElement(r, 1), m.getElement(r, 2)).normal()
        rows += [v.x, v.y, v.z, 0.0]
    return om.MMatrix(rows + [m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2), 1.0])


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def angle(a, b):
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True).inverse() * \
        om.MTransformationMatrix(b).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def bones(root):
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    return dict((p.split("|")[-1].split(":")[-1], p) for p in paths)


def pose_error(b):
    """(worst matrix element, worst angle deg, worst bone) over the bones the pose decides."""
    worst = (0.0, 0.0, None)
    for leaf, path in b.items():
        if leaf in DATA["joints"] and leaf not in RULED:
            goal = unscaled(DATA["joints"][leaf])
            e = mdiff(wm(path), goal)
            if e > worst[0]:
                worst = (e, angle(wm(path), goal), leaf)
    return worst


def mesh_points(name):
    tr = cmds.ls(name, "*:" + name, type="transform", long=True)[0]
    live = [s for s in cmds.listRelatives(tr, shapes=True, fullPath=True) if not cmds.getAttr(s + ".intermediateObject")][0]
    sel = om.MSelectionList(); sel.add(live)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)


def mesh_error():
    worst = (0.0, None)
    for name, goal in DATA["meshes"].items():
        pts = mesh_points(name)
        e = max(abs(p.x - g[0]) + abs(p.y - g[1]) + abs(p.z - g[2]) for p, g in zip(pts, goal))
        if e > worst[0]:
            worst = (e, name)
    return worst


def normals_error():
    """(worst angle deg between each shown face-vertex normal and SKM's, the hand meshes' median angle
    between the stored normal and the surface).  2026-09-24: the rebind had left the T-pose's LOCKED
    normals on the moved points -- the hands 55-59 deg median off their surface, shading dark."""
    worst, hands = 0.0, []
    for name, world in NORMALS["normals"].items():
        tr = cmds.ls(name, "*:" + name, type="transform", long=True)[0]
        live = [s for s in cmds.listRelatives(tr, shapes=True, fullPath=True) if not cmds.getAttr(s + ".intermediateObject")][0]
        sel = om.MSelectionList(); sel.add(live)
        dag = sel.getDagPath(0)
        fn = om.MFnMesh(dag)
        shown = fn.getNormals(om.MSpace.kWorld)
        counts, ids = fn.getNormalIds()
        for i, n in zip(ids, world):
            a, b = om.MVector(shown[i]), om.MVector(n[0], n[1], n[2])
            if a.length() > 1e-9 and b.length() > 1e-9:
                worst = max(worst, math.degrees(a.angle(b)))
        if name.startswith("Creep_Arm"):
            stored = fn.getVertexNormals(False, om.MSpace.kObject)
            geo = [om.MVector() for _ in range(fn.numVertices)]
            it = om.MItMeshPolygon(dag)
            while not it.isDone():
                nn = it.getNormal(om.MSpace.kObject) * it.getArea(om.MSpace.kObject)
                for vv in it.getVertices():
                    geo[vv] += nn
                it.next()
            dev = sorted(math.degrees(om.MVector(stored[k]).angle(geo[k])) for k in range(fn.numVertices) if geo[k].length() > 1e-12)
            hands.append(dev[len(dev) // 2])
    return worst, max(hands)


# the smoothing the creature's source FBX (`creep_T-pose_draft (1).fbx`) carries, measured
# 2026-09-24: its hard edges per mesh -- the seams where the normals split, and the borders
SOURCE_HARD = {"Creep_Arm_L": 618, "Creep_Arm_R": 618, "Creep_Back": 2832, "Creep_Body": 10833, "Creep_Face": 1284}


def edges_state():
    """{mesh: (hard edges on the shown shape, edges breaking the rule)}: an edge must be soft
    exactly where its two faces carry the same normal at both ends (rebind_creep_pose.soft_edges).
    Every edge was HARD before 2026-09-24's fix, so every FBX export carried no smoothing."""
    import rebind_creep_pose as rb
    out = {}
    for name in SOURCE_HARD:
        _, live, _ = rb._mesh(name)
        fn = rb._fn(live)
        rule = rb.soft_edges(live)
        out[name] = (sum(1 for e in range(fn.numEdges) if not fn.isEdgeSmooth(e)),
                     sum(1 for e in range(fn.numEdges) if fn.isEdgeSmooth(e) != rule[e]))
    return out


def bind_pose_state(root):
    """(bones not in the skins' bind pose, members whose parent link skips the pose, skins not on
    it): Maya's FBX exporter drops the bind pose whole on either of the first two (2026-09-24)."""
    joints = cmds.ls(root, dag=True, type="joint", long=True)
    poses = set()
    for sc in cmds.ls(type="skinCluster"):
        poses.update(cmds.listConnections(sc + ".bindPose", s=True, d=False) or [])
    if len(poses) != 1:
        return joints, [], sorted(poses)
    dp = poses.pop()
    members = set(cmds.ls(cmds.dagPose(dp, q=True, members=True) or [], long=True))
    loose = []
    for idx in cmds.getAttr(dp + ".members", multiIndices=True) or []:
        par = cmds.listConnections("%s.parents[%d]" % (dp, idx), s=True, d=False, plugs=True) or []
        if par and not (par[0].startswith(dp + ".members[") or par[0] == dp + ".world"):
            loose.append(idx)
    return [j for j in joints if j not in members], loose, []


def edges_ok(state):
    return all(state[m][0] == SOURCE_HARD[m] and state[m][1] == 0 for m in SOURCE_HARD)


def bind_error():
    worst = 0.0
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(cmds.ls(src[0], long=True)[0])
                worst = max(worst, mdiff(m, om.MMatrix()))
    return worst


def in_hand(b, bone, hand):
    return wm(b[bone]) * wm(b[hand]).inverse()


from maya_scenesetup import catalog, character
import maya_rigs

# -------------------------------------------------------------------- the rig
cmds.file(new=True, force=True)
text = character.add_character(catalog.character_by_key("Creep_Rig"))
rig = maya_rigs.rigs()[0]
B = bones(rig.skeleton_root)
off = []
for c in cmds.sets(maya_rigs.node(rig, "ControlSet"), q=True) or []:
    for a in ("tx", "ty", "tz", "rx", "ry", "rz"):
        if cmds.attributeQuery(a, node=c, exists=True) and cmds.getAttr(c + "." + a, settable=True) \
                and abs(cmds.getAttr(c + "." + a)) > 1e-5:
            off.append(c + "." + a)
gate(1, rig.namespace == "Creep_Rig" and not off and len(B) == 91, "%s | controls off default: %s | %d bones" % (text[:50], off[:4], len(B)))
e, a, leaf = pose_error(B)
gate(2, e < 1e-4, "the rig at zero: every bone on SKM_Manny_Simple's pose, worst element %.2e (%.5f deg, %s)" % (e, a, leaf))
me, mn = mesh_error()
gate(3, me < 1e-3, "every mesh vertex on SKM's deformed vertex: worst %.2e cm (%s)" % (me, mn))
gate(4, bind_error() < 1e-4, "the zero pose IS the bind: |BPM*WM - I| worst %.2e" % bind_error())
nw, nh = normals_error()
gate(10, nw < 0.01 and nh < 10, "the shown normals are SKM's to %.4f deg; the hand meshes' normals sit a median %.1f deg off their surface "
     "(55-59 before the fix: dark hands)" % (nw, nh))
bp = bind_pose_state(B["root"])
gate(14, not any(bp), "the rig's bind pose: every bone in it, every parent link through it, every skin on it: missing %s, loose %s, other poses %s"
     % ([j.split("|")[-1] for j in bp[0]], bp[1], bp[2]))
es = edges_state()
gate(12, edges_ok(es), "the rig's smoothing: hard edges %s (the source FBX's %s), edges off the normals' rule %s"
     % (dict((m, es[m][0]) for m in es), SOURCE_HARD, dict((m, es[m][1]) for m in es)))
helpers = (mdiff(unscaled(wm(B["ik_hand_r"])), unscaled(wm(B["hand_r"]))),
           mdiff(unscaled(wm(B["ik_hand_l"])), unscaled(wm(B["hand_l"]))),
           max(abs(v) for v in cmds.getAttr(B["ik_hand_gun"] + ".t")[0] + cmds.getAttr(B["ik_hand_gun"] + ".r")[0]))
gate(5, max(helpers) < 1e-4, "ik_hand_r / ik_hand_l on the hands, ik_hand_gun at zero: %s" % ["%.1e" % h for h in helpers])
ctrl = maya_rigs.node(rig, "FKShoulder_R")
h0, m0 = wm(B["hand_r"]), mesh_points("Creep_Arm_R")
cmds.setAttr(ctrl + ".rz", 30)
moved_h = (om.MVector([wm(B["hand_r"]).getElement(3, i) for i in range(3)]) -
           om.MVector([h0.getElement(3, i) for i in range(3)])).length()
moved_m = max(p.distanceTo(q) for p, q in zip(mesh_points("Creep_Arm_R"), m0))
cmds.setAttr(ctrl + ".rz", 0)
back = mesh_error()[0]
gate(6, moved_h > 5 and moved_m > 5 and back < 1e-3,
     "positive control: FKShoulder_R rz 30 moves hand_r %.1f cm and the arm mesh %.1f cm; back at 0 the mesh is on the pose to %.1e"
     % (moved_h, moved_m, back))
grips = {}
for bone, hand in (("weapon_r", "hand_r"), ("weapon_l", "hand_l")):
    grips[bone] = in_hand(B, bone, hand)

# -------------------------------------------------------------- the clean skeleton
cmds.file(new=True, force=True)
text = character.add_character(catalog.character_by_key("Creep"))
root = [j for j in cmds.ls("root", type="joint", long=True) if not cmds.listRelatives(j, parent=True)][0]
S = bones(root)
e, a, leaf = pose_error(S)
me, mn = mesh_error()
nw, nh = normals_error()
gate(11, nw < 0.01 and nh < 10, "Creep [skeleton]: normals SKM's to %.4f deg, hands %.1f deg off their surface" % (nw, nh))
bp = bind_pose_state(root)
gate(15, not any(bp), "Creep [skeleton]'s bind pose: missing %s, loose %s, other poses %s"
     % ([j.split("|")[-1] for j in bp[0]], bp[1], bp[2]))
es = edges_state()
gate(13, edges_ok(es), "Creep [skeleton]'s smoothing: hard edges %s, edges off the normals' rule %s"
     % (dict((m, es[m][0]) for m in es), dict((m, es[m][1]) for m in es)))
gate(7, e < 1e-4 and me < 1e-3 and bind_error() < 1e-4 and len(S) == 91,
     "Creep [skeleton]: bones on the pose to %.2e (%s), mesh to %.2e (%s), skin at bind %.2e, %d bones" % (e, leaf, me, mn, bind_error(), len(S)))
gate(8, all(mdiff(in_hand(S, bone, hand), grips[bone]) < 1e-4 for bone, hand in (("weapon_r", "hand_r"), ("weapon_l", "hand_l"))),
     "the skeleton's weapon bones sit in the hands exactly as the rig's")

# --------------------------------------------------- the weapon bones against the old asset
if OLD:
    cmds.file(new=True, force=True)
    cmds.file(OLD, i=True, namespace="old", executeScriptNodes=False)
    O = bones([j for j in cmds.ls("old:root", type="joint", long=True) if not cmds.listRelatives(j, parent=True)][0])
    d = [mdiff(in_hand(O, bone, hand), grips[bone]) for bone, hand in (("weapon_r", "hand_r"), ("weapon_l", "hand_l"))]
    gate(9, max(d) < 1e-4, "weapon_r / weapon_l keep their place in the hand against the old asset: %s (the Creep Sword's frame)"
         % ["%.1e" % x for x in d])
print("RESULT: %d gates failed %s" % (len(FAILS), FAILS))
