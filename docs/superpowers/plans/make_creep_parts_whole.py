"""Creep 2's right arm and head on the character's whole skeleton (Manny's 93 bones).

    mayapy make_creep_parts_whole.py <rig|skeleton> <arm|head>

mayapy STANDALONE, one asset per process (trap 122). It edits `assets/<Model>_<Rig|Skeleton>.ma` in
place:
- the joints the part lacks are copied from the shipped `Creep2_Skeleton.ma` under their parents with
  Creep 2's own locals. The part's root stands where Creep 2's does, so they land on Creep 2's bind;
- the part's top joint (`clavicle_r` / `neck_01`) goes under `spine_05`;
- on a rig, the top joint's point / orient / scale constraints are made again `-mo` (a point
  constraint's offset lives in the parent's space) and `spine_05` follows `Root_M` `-mo`. Every
  other added bone carries nothing and stands at the bind under `root`;
- one bind pose is saved over every joint.

Nothing of the rig is rebuilt and no control is added. Every part joint keeps its world matrix and
the mesh its points. Idempotent: an asset already whole is left alone. See
`docs/superpowers/specs/2026-10-27-creep-parts-manny-skeleton-design.md`.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim", "assets"))
MODEL = {"arm": "Creep2_ArmR", "head": "Creep2_Head"}
TOP = {"arm": "clavicle_r", "head": "neck_01"}
ANCHOR = "spine_05"
WHOLE = 93
TOL = 1e-4
LOCALS = ("translate", "rotate", "jointOrient", "rotateAxis")
SCALARS = ("rotateOrder", "segmentScaleCompensate", "radius")
BANNED = ("createNode script", "vaccine", "breed_gene", "C:/", "C:\\\\", "E:/", "Downloads", "MY PC")

KIND, PART = sys.argv[1], sys.argv[2]
OUT = os.path.join(ASSETS, "%s_%s.ma" % (MODEL[PART], "Rig" if KIND == "rig" else "Skeleton"))
ROOT = "|Armature|root"


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def joints_under(root):
    return cmds.ls(root, dag=True, type="joint", long=True) or []


def world(path):
    return cmds.xform(path, q=True, ws=True, m=True)


def far(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def copy_locals(src, dst):
    for attr in LOCALS:
        cmds.setAttr(dst + "." + attr, *cmds.getAttr(src + "." + attr)[0], type="double3")
    for attr in SCALARS:
        cmds.setAttr(dst + "." + attr, cmds.getAttr(src + "." + attr))


def constraints_of(joint):
    """[(command, [targets])] of the constraints driving `joint` (its constraint children)."""
    out = []
    for c in cmds.listRelatives(joint, children=True, type="constraint", fullPath=True) or []:
        kind = cmds.nodeType(c)
        cmd = getattr(cmds, kind)
        out.append((kind, cmd(c, q=True, targetList=True) or [], c))
    return out


def whole_bind_pose(joints):
    skins = cmds.ls(type="skinCluster") or []
    old = set(cmds.ls(type="dagPose") or [])
    new = cmds.dagPose(joints, save=True, bindPose=True, name="skeldarBindPose_new")
    new = new[0] if isinstance(new, (list, tuple)) else new
    strays = [m for m in cmds.ls(cmds.dagPose(new, q=True, members=True) or [], long=True)
              if cmds.objectType(m) != "joint"]
    if strays:
        cmds.dagPose(strays, remove=True, name=new)
    for sc in skins:
        cmds.connectAttr(new + ".message", sc + ".bindPose", force=True)
    for pose in old:
        if cmds.objExists(pose):
            cmds.delete(pose)
    new = cmds.rename(new, "bindPose1")
    return new, len(cmds.dagPose(new, q=True, members=True) or [])


def save_checked(path):
    cmds.file(rename=path.replace("\\", "/"))
    cmds.file(save=True, type="mayaAscii", force=True)
    with open(path, encoding="utf-8", errors="surrogateescape") as fh:
        lines = fh.readlines()
    kept, skipping, cut = [], False, 0
    for line in lines:
        if line.startswith("createNode script "):
            skipping, cut = True, cut + 1
            continue
        if skipping and line[:1] not in ("\t", " "):
            skipping = False
        if not skipping:
            kept.append(line)
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.writelines(kept)
    bad = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            bad += [(n, w) for w in BANNED if w in line]
    if bad:
        raise RuntimeError("banned content in %s: %s" % (path, bad[:10]))
    return cut


cmds.file(OUT, open=True, force=True, executeScriptNodes=False)
assert cmds.objExists(ROOT), "no %s in %s" % (ROOT, OUT)
MARK = "skeldarPartAnchor"     # on a part SKELETON's root: the bone that takes the clip's place


def mark_root():
    """A part skeleton's root names its anchor bone; True when it was not marked yet."""
    if KIND != "skeleton" or cmds.attributeQuery(MARK, node=ROOT, exists=True):
        return False
    cmds.addAttr(ROOT, longName=MARK, dataType="string")
    cmds.setAttr(ROOT + "." + MARK, ANCHOR, type="string")
    return True


if len(joints_under(ROOT)) == WHOLE:
    if mark_root():
        print("marked %s.%s, saved, script nodes cut %d" % (ROOT, MARK, save_checked(OUT)))
    else:
        print("already whole: %s" % OUT)
    sys.exit(0)
mark_root()
before = {leaf(j): world(j) for j in joints_under(ROOT)}
verts = {}
for shape in cmds.ls(type="mesh", noIntermediate=True, long=True):
    verts[shape] = cmds.xform(shape + ".vtx[*]", q=True, ws=True, t=True)
layer = (cmds.listConnections(ROOT, type="displayLayer") or [None])[0]
cmds.currentTime(0)

cmds.file(os.path.join(ASSETS, "Creep2_Skeleton.ma"), i=True, namespace="src",
          executeScriptNodes=False)
src_root = cmds.ls("src:root", type="joint", long=True)[0]
assert far(world(src_root), world(ROOT)) < TOL, "the part's root is not Creep 2's"

top = TOP[PART]
top_path = cmds.ls(ROOT, dag=True, type="joint", long=True)
top_path = [j for j in top_path if leaf(j) == top][0]
remade = constraints_of(top_path) if KIND == "rig" else []
for _, _, node in remade:
    cmds.delete(node)

part_names = set(before)
made = []
for src in joints_under(src_root)[1:]:                 # parents before children
    name = leaf(src)
    parent = leaf(cmds.listRelatives(src, parent=True, fullPath=True)[0])
    dst_parent = [j for j in joints_under(ROOT) if leaf(j) == parent][0]
    if name in part_names and name != top:
        continue
    if name == top:
        path = [j for j in joints_under(ROOT) if leaf(j) == top][0]
        path = cmds.parent(path, dst_parent)[0]
        path = cmds.ls(path, long=True)[0]
    else:
        path = cmds.createNode("joint", name=name, parent=dst_parent, skipSelect=True)
        path = cmds.ls(path, long=True)[0]
        made.append(path)
    copy_locals(src, path)

all_joints = joints_under(ROOT)
assert len(all_joints) == WHOLE, len(all_joints)
worst_part = max(far(before[leaf(j)], world(j)) for j in all_joints if leaf(j) in before)
worst_new = max(far(world(j), world(cmds.ls("src:" + leaf(j), long=True)[0])) for j in all_joints)
for j in all_joints[1:]:
    mine = leaf(cmds.listRelatives(j, parent=True)[0])
    theirs = leaf(cmds.listRelatives(cmds.ls("src:" + leaf(j), long=True)[0], parent=True)[0])
    assert mine == theirs, (leaf(j), mine, theirs)
assert worst_part < TOL and worst_new < TOL, (worst_part, worst_new)

if KIND == "rig":
    top_path = [j for j in all_joints if leaf(j) == top][0]
    for kind, targets, _ in remade:
        getattr(cmds, kind)(targets, top_path, maintainOffset=True)
    anchor = [j for j in all_joints if leaf(j) == ANCHOR][0]
    assert cmds.objExists("Root_M"), "no Root_M"
    cmds.parentConstraint("Root_M", anchor, maintainOffset=True)
    cmds.dgdirty(allPlugs=True)
    cmds.currentTime(1)
    cmds.currentTime(0)
    worst_part = max(far(before[leaf(j)], world(j)) for j in all_joints if leaf(j) in before)
    assert worst_part < TOL, worst_part

if layer:
    cmds.editDisplayLayerMembers(layer, made, noRecurse=True)
pose, members = whole_bind_pose(all_joints)
for node in cmds.ls("src:*") or []:
    try:
        cmds.lockNode(node, lock=False)
    except Exception:
        pass
try:
    cmds.namespace(removeNamespace="src", deleteNamespaceContent=True)
except RuntimeError:
    # trap 158: an import can make the scene's own managers inside its namespace
    for node in cmds.ls("src:*") or []:
        try:
            cmds.delete(node)
        except Exception:
            pass
    left = cmds.ls("src:*") or []
    cmds.namespace(removeNamespace="src", mergeNamespaceWithRoot=True)
    print("left by the import, moved to the root namespace: %s" % left)
worst_vert = 0.0
for shape, pts in verts.items():
    now = cmds.xform(shape + ".vtx[*]", q=True, ws=True, t=True)
    worst_vert = max(worst_vert, far(pts, now))
assert worst_vert < TOL, worst_vert
cut = save_checked(OUT)
print("saved %s: %d joints, %d added, bind pose %d members, part joints moved %.2e, new on Creep 2 "
      "%.2e, vertices %.2e, script nodes cut %d"
      % (OUT, len(all_joints), len(made), members, worst_part, worst_new, worst_vert, cut))
