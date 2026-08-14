"""Live checks for FK-through-knots. Run inside Maya.

Keys real animation on a bone first, so the transfer onto the controllers and
the bake back are proven on motion, not on a static pose.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import bodymap, builder, fkcontrols

failures = []


def check(label, condition, detail=""):
    print("%-56s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def real_nodes():
    """Node count ignoring animCurves -- baking legitimately creates those."""
    return len([n for n in (cmds.ls(long=True) or [])
                if not cmds.objectType(n).startswith("animCurve")])


def hand_pos_at(frame):
    cmds.currentTime(frame)
    return cmds.xform(smap["hand_l"], query=True, worldSpace=True,
                      translation=True)


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map
if "upperarm_l" not in smap:
    print("ABORT: binding failed -", window.status.currentMessage())
    raise SystemExit

# --- reset to a known state ---------------------------------------------
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
all_joints = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap]
cmds.cutKey(all_joints, clear=True)

# Real animation on one bone.
cmds.setKeyframe(smap["upperarm_l"], attribute="rotateZ", time=0, value=0)
cmds.setKeyframe(smap["upperarm_l"], attribute="rotateZ", time=30, value=40)
pose_before = hand_pos_at(30)

baseline = real_nodes()
print("baseline real nodes: %d\n" % baseline)

# --- build ----------------------------------------------------------------
count, message = fkcontrols.build_fk(smap)
print("build:", message, "\n")

check("64 controllers created", count == 64, str(count))
ctrls = [fkcontrols.controller_name(b.joint) for b in bodymap.BUTTONS]
missing = [c for c in ctrls if not cmds.objExists(c)]
check("every controller exists by name", not missing, str(missing[:4]))

ringed = [c for c in ctrls if cmds.objExists(c) and any(
    cmds.objectType(s) == "nurbsCurve"
    for s in cmds.listRelatives(c, shapes=True, fullPath=True) or [])]
check("every controller carries a ring shape", len(ringed) == 64,
      str(len(ringed)))

check("controller took over the animation",
      (cmds.keyframe("upperarm_l_FK_ctrl", query=True,
                     keyframeCount=True) or 0) > 0)

pose_after = hand_pos_at(30)
drift = sum((a - b) ** 2 for a, b in zip(pose_before, pose_after)) ** 0.5
check("hand pose at frame 30 preserved through the transfer",
      drift < 0.5, "drift %.3f cm" % drift)

# --- chain FK: rotating the pelvis control must carry spine_05 -----------
cmds.currentTime(0)
tip_before = cmds.xform(smap["spine_05"], query=True, worldSpace=True,
                        translation=True)
cmds.setAttr("pelvis_FK_ctrl.rotateZ", 25)
tip_after = cmds.xform(smap["spine_05"], query=True, worldSpace=True,
                       translation=True)
moved = sum((a - b) ** 2 for a, b in zip(tip_before, tip_after)) ** 0.5
check("pelvis control carries spine_05 (chain FK)", moved > 3.0,
      "%.2f cm" % moved)
cmds.setAttr("pelvis_FK_ctrl.rotateZ", 0)

# --- guards ----------------------------------------------------------------
window.build_rig()
check("Build IK refused while FK exists", not builder.has_build(),
      window.status.currentMessage())

# --- rebuild does not grow the scene --------------------------------------
before_rebuild = real_nodes()
count2, message2 = fkcontrols.build_fk(smap)
print("\nrebuild:", message2, "\n")
check("rebuild still yields 64", count2 == 64, str(count2))
check("rebuild did not grow the scene",
      abs(real_nodes() - before_rebuild) <= 2,
      "%d -> %d" % (before_rebuild, real_nodes()))

# --- bake back -------------------------------------------------------------
removed, bake_message = fkcontrols.bake_fk(smap)
print("bake:", bake_message, "\n")

check("no FK recorded any more", not fkcontrols.has_fk())
check("no controllers left",
      not [c for c in ctrls if cmds.objExists(c)])
check("bone got its animation back",
      (cmds.keyframe(smap["upperarm_l"], query=True,
                     keyframeCount=True) or 0) > 0)
pose_final = hand_pos_at(30)
drift = sum((a - b) ** 2 for a, b in zip(pose_before, pose_final)) ** 0.5
check("hand pose at frame 30 survived the round trip",
      drift < 0.5, "drift %.3f cm" % drift)
check("real node count back to baseline", real_nodes() == baseline,
      "%d -> %d" % (baseline, real_nodes()))

# --- leave the scene unanimated, as it was --------------------------------
cmds.currentTime(0)
cmds.cutKey(all_joints, clear=True)
cmds.select(clear=True)
print("\n%s" % ("FK THROUGH KNOTS WORKS" if not failures
                else "FAILURES: %s" % failures))
