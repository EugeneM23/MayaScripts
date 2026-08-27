"""Live proof of maya_skelfit, run through the bridge in the test scene.

The scene holds Manny's own body mesh (Skin_3p, 48705 verts) and NO joints,
which makes it the identity case: the fitted skeleton must land on the
template's own joint positions. Gates:

 1. build succeeds and reports 93 joints
 2. every template joint exists, exactly once, with the template parent
 3. positions land on the template (identity mesh; symmetrize tolerance)
 4. anatomical L/R symmetry is exact
 5. root sits at the origin
 6. channel conventions: jointOrient zero off-root, rotateOrder xyz, ssc off
 7. world orientation matches the template frames (through the real DAG)
 8. a second build refuses
 9. bind succeeds through geomBind (voxel), not the fallback
10. the skin's influence list is exactly bind_influences (74)
11. every vertex weight sum == 1, measured max influences <= 8
12. elbows pose moves the left forearm skin and not the right
13. restore_pose puts every vertex back exactly
14. screenshots captured (front/persp bind pose, front elbows pose)

A skeleton left by a previous run of THIS script (recognised by the
skelfitReference attr) is torn down first; the scene had no joints before.
"""
import json
import math
import os

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

import maya_skelfit as sf

SHOTS = os.environ.get("SKELFIT_SHOTS") or (
    "C:/Users/MYPC~1/AppData/Local/Temp/claude/C-----Work-MayaScripts/"
    "6c6a4a38-3f95-4219-b238-a61b7dd36826/scratchpad")

failed = []
gate_no = [0]


def gate(name, ok, detail=""):
    gate_no[0] += 1
    line = "GATE %2d %-4s %s" % (gate_no[0], "ok" if ok else "FAIL", name)
    if detail:
        line += " -- " + detail
    print(line)
    if not ok:
        failed.append(name)


def settle():
    cmds.currentTime(cmds.currentTime(query=True), update=True)
    cmds.refresh(force=True)


def points_of(mesh):
    sel = om.MSelectionList()
    sel.add(mesh)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)


template = sf.load_template()
jm = sf.joint_map(template)

# ---------------------------------------------------------------- cleanup
if cmds.objExists("root") and cmds.attributeQuery(
        sf.REFERENCE_ATTR, node="root", exists=True):
    for mesh_t in sf.scene_mesh_transforms():
        for skin in cmds.ls(cmds.listHistory(mesh_t) or [],
                            type="skinCluster"):
            cmds.skinCluster(skin, edit=True, unbind=True)
    stray = cmds.ls(type="dagPose") or []
    if stray:
        cmds.delete(stray)
    cmds.delete("root")
    print("cleanup: previous run's skeleton removed")

mesh, reason = sf.target_mesh()
if mesh is None:
    raise RuntimeError("no target mesh: " + reason)
rest_points = points_of(mesh)

# ------------------------------------------------------------ build gates
status = sf.build()
gate("build reports 93 joints", "93 joints" in status, status)

names = [j["name"] for j in template["joints"]]
existing = {n: cmds.ls(n, long=True) or [] for n in names}
gate("every joint exists exactly once",
     all(len(v) == 1 for v in existing.values()),
     ", ".join(n for n, v in existing.items() if len(v) != 1)[:120])

bad_parent = []
for j in template["joints"]:
    parent = cmds.listRelatives(j["name"], parent=True)
    parent = parent[0] if parent else None
    if parent != j["parent"]:
        bad_parent.append("%s under %s" % (j["name"], parent))
gate("hierarchy matches the template", not bad_parent,
     "; ".join(bad_parent[:4]))

worst_pos, worst_name = 0.0, ""
for j in template["joints"]:
    got = cmds.xform(j["name"], q=True, ws=True, translation=True)
    d = math.dist(got, j["world_position"])
    if d > worst_pos:
        worst_pos, worst_name = d, j["name"]
gate("positions land on the template (identity mesh)", worst_pos < 0.2,
     "worst %.4f cm on %s" % (worst_pos, worst_name))

worst_sym, worst_sym_name = 0.0, ""
for j in template["joints"]:
    name = j["name"]
    if sf.side_of(name) != "l" or name in sf.IK_FOLLOWS \
            or name in sf.ASYMMETRIC:
        continue
    a = cmds.xform(name, q=True, ws=True, translation=True)
    b = cmds.xform(sf.pair_name(name), q=True, ws=True, translation=True)
    d = max(abs(a[0] + b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))
    if d > worst_sym:
        worst_sym, worst_sym_name = d, name
gate("L/R symmetry is exact", worst_sym < 1e-4,
     "worst %.7f on %s" % (worst_sym, worst_sym_name))

root_pos = cmds.xform("root", q=True, ws=True, translation=True)
gate("root at the origin", max(abs(v) for v in root_pos) < 0.05,
     "(%.4f %.4f %.4f)" % tuple(root_pos))

bad_conv = []
for j in template["joints"]:
    name = j["name"]
    if name != "root":
        jo = cmds.getAttr(name + ".jointOrient")[0]
        if max(abs(v) for v in jo) > 1e-7:
            bad_conv.append(name + " jointOrient")
    if cmds.getAttr(name + ".rotateOrder") != 0:
        bad_conv.append(name + " rotateOrder")
    if cmds.getAttr(name + ".segmentScaleCompensate"):
        bad_conv.append(name + " ssc")
gate("channel conventions", not bad_conv, "; ".join(bad_conv[:5]))

worst_rot, worst_rot_name = 0.0, ""
for j in template["joints"]:
    want = om.MTransformationMatrix(om.MMatrix(j["world_matrix"])).rotation(
        asQuaternion=True)
    have_m = om.MMatrix(cmds.getAttr(j["name"] + ".worldMatrix[0]"))
    have = om.MTransformationMatrix(have_m).rotation(asQuaternion=True)
    delta = have * want.inverse()
    angle = math.degrees(2.0 * math.atan2(
        math.sqrt(delta.x ** 2 + delta.y ** 2 + delta.z ** 2), abs(delta.w)))
    if angle > worst_rot:
        worst_rot, worst_rot_name = angle, j["name"]
gate("world orientation on the template frames", worst_rot < 0.5,
     "worst %.4f deg on %s" % (worst_rot, worst_rot_name))

second = sf.build()
gate("second build refuses", second.startswith("refused"), second[:90])

# --------------------------------------------------------- finalize gates
# simulate the user dragging the left hand, then mirror it across
prior_hand = cmds.xform("hand_l", q=True, ws=True, translation=True)
nudged = [prior_hand[0] + 2.0, prior_hand[1] + 3.0, prior_hand[2] + 1.0]
cmds.xform("hand_l", ws=True, translation=nudged)
status = sf.finalize()
hand_r_now = cmds.xform("hand_r", q=True, ws=True, translation=True)
mirror_err = max(abs(hand_r_now[0] + nudged[0]),
                 abs(hand_r_now[1] - nudged[1]),
                 abs(hand_r_now[2] - nudged[2]))
gate("finalize detects the edit and mirrors it",
     "side 'l'" in status and mirror_err < 1e-4,
     "%s; mirror err %.6f" % (status[:80], mirror_err))

middle_r = cmds.xform("middle_01_r", q=True, ws=True, translation=True)
middle_l = cmds.xform("middle_01_l", q=True, ws=True, translation=True)
finger_err = max(abs(middle_r[0] + middle_l[0]),
                 abs(middle_r[1] - middle_l[1]),
                 abs(middle_r[2] - middle_l[2]))
gate("the dragged hand's fingers mirrored with it", finger_err < 1e-4,
     "err %.6f" % finger_err)

# undo the edit the same way the user would, and re-finalize
cmds.xform("hand_l", ws=True, translation=prior_hand)
sf.finalize(side="l")
worst_back_fit, worst_back_name = 0.0, ""
for j in template["joints"]:
    got = cmds.xform(j["name"], q=True, ws=True, translation=True)
    d = math.dist(got, j["world_position"])
    if d > worst_back_fit:
        worst_back_fit, worst_back_name = d, j["name"]
gate("undoing the edit and re-finalizing returns to the fit",
     worst_back_fit < 0.2,
     "worst %.4f cm on %s" % (worst_back_fit, worst_back_name))

# ------------------------------------------------------------- bind gates
status = sf.bind()
gate("voxel bind succeeds", "voxel-bound" in status, status)

skins = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster")
skin = skins[0] if skins else None
if skin:
    influences = sorted(cmds.skinCluster(skin, q=True, influence=True) or [])
    gate("influence list is exactly the weighted set",
         influences == sorted(sf.bind_influences(template)),
         "%d influences" % len(influences))

    sel = om.MSelectionList()
    sel.add(mesh)
    dag = sel.getDagPath(0)
    sel2 = om.MSelectionList()
    sel2.add(skin)
    fn = oma.MFnSkinCluster(sel2.getDependNode(0))
    comp_fn = om.MFnSingleIndexedComponent()
    comp = comp_fn.create(om.MFn.kMeshVertComponent)
    comp_fn.setCompleteData(om.MFnMesh(dag).numVertices)
    weights, count = fn.getWeights(dag, comp)
    n_verts = len(weights) // count
    worst_sum, live_max = 1.0, 0
    for v in range(n_verts):
        row = weights[v * count:(v + 1) * count]
        s = sum(row)
        if abs(s - 1.0) > abs(worst_sum - 1.0):
            worst_sum = s
        live_max = max(live_max, sum(1 for w in row if w > 1e-6))
    gate("every vertex sums to 1", abs(worst_sum - 1.0) < 1e-6,
         "worst sum %.9f" % worst_sum)
    gate("max influences per vertex <= 8", live_max <= 8,
         "measured %d" % live_max)
else:
    gate("influence list is exactly the weighted set", False, "no skinCluster")
    gate("every vertex sums to 1", False, "no skinCluster")
    gate("max influences per vertex <= 8", False, "no skinCluster")

# ------------------------------------------------------ deformation gates
shots = []
shot = os.path.join(SHOTS, "skelfit_bindpose_front.png")
shots.append(sf.screenshot(shot, view="front"))
shot = os.path.join(SHOTS, "skelfit_bindpose_persp.png")
shots.append(sf.screenshot(shot, view="persp"))


def region(center, radius):
    c = om.MPoint(*center)
    return [i for i, p in enumerate(rest_points)
            if p.distanceTo(c) < radius]


elbow_l = cmds.xform("lowerarm_l", q=True, ws=True, translation=True)
hand_l = cmds.xform("hand_l", q=True, ws=True, translation=True)
mid_l = [(a + b) / 2.0 for a, b in zip(elbow_l, hand_l)]
mid_r = [-mid_l[0], mid_l[1], mid_l[2]]
left_forearm = region(mid_l, 6.0)
right_forearm = region(mid_r, 6.0)

status = sf.pose_test("elbows")
settle()
posed_points = points_of(mesh)
moved_left = max(rest_points[i].distanceTo(posed_points[i])
                 for i in left_forearm) if left_forearm else 0.0
moved_right = max(rest_points[i].distanceTo(posed_points[i])
                  for i in right_forearm) if right_forearm else 99.0
gate("elbows pose moves the left forearm skin",
     "applied" in status and moved_left > 1.0,
     "%s; left moved %.3f cm (%d verts)" % (status, moved_left,
                                            len(left_forearm)))
# both elbows bend in this pose; the RIGHT forearm must move only as the
# mirror of the left, so compare its travel to the left's, not to zero
gate("right forearm moves like the left (mirrored pose)",
     abs(moved_left - moved_right) < 1.0,
     "left %.3f right %.3f" % (moved_left, moved_right))

shot = os.path.join(SHOTS, "skelfit_elbows_front.png")
shots.append(sf.screenshot(shot, view="front"))

sf.restore_pose()
settle()

# isolation: ONE elbow bent by hand, the other forearm must stand still --
# weight bleed across the body would show here and nowhere else
was_auto = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
prior = cmds.getAttr("lowerarm_l.rotate")[0]
try:
    cmds.setAttr("lowerarm_l.rotate", prior[0], prior[1], prior[2] - 40.0,
                 type="double3")
    settle()
    lone_points = points_of(mesh)
    lone_left = max(rest_points[i].distanceTo(lone_points[i])
                    for i in left_forearm) if left_forearm else 0.0
    lone_right = max(rest_points[i].distanceTo(lone_points[i])
                     for i in right_forearm) if right_forearm else 99.0
finally:
    cmds.setAttr("lowerarm_l.rotate", *prior, type="double3")
    cmds.autoKeyframe(state=was_auto)
settle()
gate("weights are isolated (lone left elbow leaves the right arm still)",
     lone_left > 1.0 and lone_right < 0.01,
     "left %.3f right %.6f" % (lone_left, lone_right))

back_points = points_of(mesh)
worst_back = max(rest_points[i].distanceTo(back_points[i])
                 for i in range(len(rest_points)))
gate("restore_pose puts every vertex back exactly", worst_back < 1e-5,
     "worst %.9f cm" % worst_back)

gate("screenshots captured",
     all(isinstance(s, str) and os.path.exists(s) for s in shots),
     "; ".join(str(s) for s in shots))

print("\n%d of %d gates failed" % (len(failed), gate_no[0]))
for name in failed:
    print("  FAILED: " + name)
