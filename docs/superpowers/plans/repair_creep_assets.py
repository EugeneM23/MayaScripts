"""The shipped Creep assets made export-clean, in place: the meshes' smoothing and the bind pose whole.

    mayapy repair_creep_assets.py <asset .ma> [<asset .ma> ...]

2026-09-24, the animator, on the skeletal mesh exported from Creep_Skeleton.ma: «скелет
выгрузился без групп сглаживания на геометрии».  Measured: the FBX DID carry a smoothing layer
per mesh -- of zeros, every edge hard.  Every edge of all five Creep meshes was HARD in Maya, and
already so in the animator's own creature scene before any of our work (`creep_T-pose_MIX_06_skin
.mb`: an arm 2949 hard of 2949, the body 43992 of 43992), under normals that were all LOCKED: a
locked normal wins over the edge flags in Maya, so the viewport looked right, while an FBX's
smoothing layer IS the edge flags.  The creature's source FBX (`creep_T-pose_draft (1).fbx`, the
same meshes) has the real flags, and they are exactly the edges whose two faces' normals differ
at an end, plus the borders -- so they are derived from the normals the meshes already carry
(`rebind_creep_pose.soft_edges` / `set_edges`, which the rebind pipeline now runs too).

And the same export's log: «Unable to find the bind pose for: / root / ik_foot_root / ik_foot_l.
No bind poses in the hierarchy containing the object will be exported» -- bindPose1 held 87 of the
91 bones (not root, weapon_l, interaction, center_of_mass) and three members named their parent
through the parent node rather than its slot in the pose, so the FBX went out with NO bind pose
and Unreal would take time 0 and warn.  The pose is saved again over every joint where it stands,
which is the bind (`rebind_creep_pose.whole_bind_pose`, run by the rebind too).

mayapy STANDALONE, the asset opened with its script nodes NOT executed.  Checked before saving:
the shown normals and points of every mesh unchanged (face-vertex by face-vertex), every normal
still locked, the skins still at their bind; then saved as .ma in place and Maya's own
ui/scene-configuration script nodes cut out of the text (trap 74), the way the asset scripts do.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.api.OpenMaya as om

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rebind_creep_pose as rb

for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
MESHES = ("Creep_Body", "Creep_Back", "Creep_Arm_L", "Creep_Arm_R", "Creep_Face")


def shown(name):
    """The shown shape's world points, face-vertex normals, locked count, hard-edge count."""
    _, live, _ = rb._mesh(name)
    sel = om.MSelectionList(); sel.add(live)
    fn = om.MFnMesh(sel.getDagPath(0))
    normals = fn.getNormals(om.MSpace.kWorld)
    counts, ids = fn.getNormalIds()
    locked = sum(1 for i in range(fn.numNormals) if fn.isNormalLocked(i))
    hard = sum(1 for e in range(fn.numEdges) if not fn.isEdgeSmooth(e))
    return fn.getPoints(om.MSpace.kWorld), [om.MVector(normals[i]) for i in ids], locked, fn.numNormals, hard


def cut_script_nodes(path):
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
    return cut


for asset in [a.replace("\\", "/") for a in sys.argv[1:]]:
    cmds.file(asset, open=True, force=True, executeScriptNodes=False)
    before = dict((m, shown(m)) for m in MESHES)
    edges = rb.set_edges(MESHES)
    print("   bind pose made again over every joint (pose, members):", rb.whole_bind_pose("|root"))
    cmds.dgdirty(allPlugs=True)
    worst_p = worst_n = 0.0
    for m in MESHES:
        pts, nrm, locked, nn, hard = shown(m)
        p0, n0, _, _, _ = before[m]
        worst_p = max(worst_p, max(a.distanceTo(b) for a, b in zip(pts, p0)))
        worst_n = max(worst_n, max(math.degrees(a.angle(b)) for a, b in zip(nrm, n0)
                                   if a.length() > 1e-9 and b.length() > 1e-9))
        print("   %-12s edges %6d, hard %6d -> %6d on the shown shape; normals locked %d of %d"
              % (m, edges[m][0], before[m][4], hard, locked, nn))
        assert hard == edges[m][1], "%s: the shown shape did not take the Orig's flags (%d vs %d)" % (m, hard, edges[m][1])
        assert locked == nn, "%s: normals no longer all locked" % m
    bind = 0.0
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                prod = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * om.MMatrix(cmds.getAttr(src[0] + ".worldMatrix[0]"))
                bind = max(bind, max(abs(a - b) for a, b in zip(list(prod), list(om.MMatrix()))))
    print("%s: points unchanged to %.2e cm, normals to %.4f deg, skins at bind %.2e" % (os.path.basename(asset), worst_p, worst_n, bind))
    # 0.01 deg: the same normals, read back through the skin (float noise measured 0.0011)
    assert worst_p < 1e-6 and worst_n < 0.01 and bind < 1e-4, "the asset changed beyond its edge flags"
    cmds.file(rename=asset)
    cmds.file(save=True, type="mayaAscii", force=True)
    cut = cut_script_nodes(asset)
    with open(asset, encoding="utf-8", errors="replace") as fh:
        assert "createNode script" not in fh.read()
    print("saved %s (%.1f MB), %d script node(s) cut from the text" % (asset, os.path.getsize(asset) / 1e6, cut))
print("DONE")
