"""verify_walk_meanpose.py - Walk Builder's Mean pose rig, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_meanpose.py

The animator (2026-10-15): «кнопочку которая рядом с нашей походкой будет создавать manny rig на котором будет наша
средняя поза и меняя анимацию на этом риге мы будем менять нашу позу для всего цикла». The walk asd (walks/, git-
ignored) in a temporary walks folder; the plugin's Manny skeleton as the target; the Mean pose rig added by the
press and its controls moved as the animator would - the update read by hand (the watch's timer needs a GUI).
"""
import math
import os
import shutil
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
ORIGINAL = os.path.join(HERE, "walks", "asd.walk.gz")

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except RuntimeError:
        pass

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
from maya_walk import scene as sw                        # noqa: E402
from maya_walk import meanrig, meanpose as mp            # noqa: E402
import maya_rigs                                         # noqa: E402
wm = sw.wm
FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def deg(r):
    return math.degrees(float(np.linalg.norm(wm.log_rot(r))))


if not os.path.exists(ORIGINAL):
    print("SKIP: the fixture is not here (%s)" % ORIGINAL)
    sys.exit(0)

TEMP = tempfile.mkdtemp(prefix="walkmean_")
shutil.copy(ORIGINAL, TEMP)
sw.WALKS = TEMP
FIX = mp.path_for(os.path.join(TEMP, "asd.walk.gz"))

cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace="M", ignoreVersion=True)
target = cmds.ls("M:root", long=True)[0]
_, info, line = sw.apply(target, "asd", {})
print(line)


def target_frames(name):
    """{frame: 4x4 world} of the target's bone `name` over the cycle."""
    path = cmds.ls("M:" + name, long=True)[0]
    times = cmds.keyframe(cmds.ls("M:pelvis", long=True)[0], attribute="rotateX", query=True, timeChange=True)
    return np.array([np.array(cmds.getAttr(path + ".worldMatrix[0]", time=t)).reshape(4, 4) for t in times])


def mean_local(name):
    w = sw.load_walk("asd", {})[0]
    parent = target_frames(w.names[w.parents[w.index[name]]])
    child = target_frames(name)
    return wm.mean_rot(child[:, :3, :3] @ np.swapaxes(parent[:, :3, :3], -1, -2))


before_arm = mean_local("upperarm_l")
before_pelvis = target_frames("pelvis")[:, 3, 1].mean()

# ---- the press: a Manny rig in the mean pose ----
started = time.time()
text = meanrig.press("asd")
print(text)
rig = meanrig.find()
gate(rig is not None and rig.namespace.startswith("Manny_Rig"), "the press added a Manny rig, marked (%s)" %
     (rig.namespace if rig else None))
x, _, z = cmds.xform(rig.main, query=True, worldSpace=True, translation=True)
tx, _, tz = cmds.xform(target, query=True, worldSpace=True, translation=True)
gate(abs(x - tx - meanrig.OFFSET) < 1e-3 and abs(z - tz) < 1e-3, "it stands 150 cm beside the target (%.1f, %.1f)" % (x, z))
walk, statics = sw.load_walk("asd", {})[:2]
shown = mp.measure(meanrig._read(rig, walk, statics), walk)
want = mp.measure(mp.mean_pose(walk), walk)
worst = max(deg(shown["local"][n] @ want["local"][n].T) for n in want["local"])
gate(worst < 0.05, "the rig's game skeleton stands in the walk's mean pose: every upper bone's local to %.4f deg" % worst)
gate(abs(shown["height"] - want["height"]) < 0.05, "the pelvis's height to %.4f cm" % abs(shown["height"] - want["height"]))
controls = meanrig._controls(rig)
keyed = [c for c in controls if cmds.listConnections(c, source=True, destination=False, type="animCurveTA")]
gate(not keyed, "no control is keyed (%d of %d)" % (len(keyed), len(controls)))
gate(meanrig.update() is None and not os.path.exists(FIX), "an untouched rig reads no change, writes nothing")
print("press %.1f s" % (time.time() - started))

# ---- an arm turned on the rig: the walk's mean for the whole cycle ----
ns = rig.namespace + ":"
cmds.setAttr(ns + "FKShoulder_L.rotateZ", cmds.getAttr(ns + "FKShoulder_L.rotateZ") + 20.0)
started = time.time()
text = meanrig.update()
print(text, "(%.1f s)" % (time.time() - started))
fix = mp.load(FIX)
gate(os.path.exists(FIX) and "upperarm_l" in fix["rot"], "the turn is written beside the walk: %s" % mp.summary(fix))
turned = deg(fix["rot"].get("upperarm_l", np.eye(3)))
gate(abs(turned - 20.0) < 0.5, "upperarm_l's correction %.2f deg (20 asked)" % turned)
gate(text is not None and "keyed again" in text, "the target is keyed again")
after_arm = mean_local("upperarm_l")
gate(abs(deg(after_arm @ before_arm.T) - turned) < 0.5,
     "the target's upperarm_l mean over the cycle turned %.2f deg" % deg(after_arm @ before_arm.T))
gate(meanrig.update() is None, "read again with nothing moved: no change")

# ---- the pelvis lowered: the walk's pelvis for the whole cycle ----
cmds.setAttr(ns + "RootX_M.translateY", cmds.getAttr(ns + "RootX_M.translateY") - 5.0)
text = meanrig.update()
print(text)
fix = mp.load(FIX)
gate(abs(fix["height"] + 5.0) < 0.3, "the pelvis's correction %.2f cm (-5 asked)" % fix["height"])
drop = target_frames("pelvis")[:, 3, 1].mean() - before_pelvis
gate(abs(drop - fix["height"]) < 1.0, "the target's pelvis %.2f cm lower on average" % -drop)
gate(abs(deg(fix["rot"]["upperarm_l"]) - turned) < 0.01, "the arm's correction is kept (%.2f deg)" % deg(fix["rot"]["upperarm_l"]))

# ---- undo on the rig: the walk follows back ----
undo_on = cmds.undoInfo(query=True, state=True)
if undo_on:
    cmds.undo()                      # the pelvis's setAttr (the update itself left no undo step)
    text = meanrig.update()
    print(text)
    fix = mp.load(FIX)
    gate(abs(fix["height"]) < 0.3, "Ctrl+Z on the rig puts the pelvis's correction back (%.2f cm)" % fix["height"])
else:
    print("(undo is off in this mayapy - the undo gate skipped)")

# ---- a knee turned (the leg to IK, its pole moved) ----
cmds.setAttr(ns + "FKIKLeg_L.FKIKBlend", 10.0)       # the rig stands its legs in FK; its IK was solved to match
text = meanrig.update()
print(text)
fix = mp.load(FIX)
gate(abs(math.degrees(fix["knee"]["l"])) < 0.5 and abs(fix["height"]) < 0.3,
     "the leg switched to IK reads (almost) no change: knee %.2f deg" % math.degrees(fix["knee"]["l"]))
pole = ns + "PoleLeg_L"
cmds.setAttr(pole + ".translateX", cmds.getAttr(pole + ".translateX") + 25.0)
text = meanrig.update()
print(text)
fix = mp.load(FIX)
gate(abs(fix["knee"]["l"]) > math.radians(2.0), "the knee's correction %.1f deg" % math.degrees(fix["knee"]["l"]))

# ---- the foot turned (its IK control about up) ----
feet_before = target_frames("foot_l")[:, 3, :3]
ik = ns + "IKLeg_L"
cmds.rotate(0.0, 15.0, 0.0, ik, relative=True, worldSpace=True)
text = meanrig.update()
print(text)
fix = mp.load(FIX)
gate(abs(abs(math.degrees(fix["toe"]["l"])) - 15.0) < 1.0, "the foot's correction %.1f deg (15 asked about the "
     "world's up)" % math.degrees(fix["toe"]["l"]))

# ---- the pelvis turned: the legs solved again, the feet where the walk plants them ----
cmds.setAttr(ns + "RootX_M.rotateX", cmds.getAttr(ns + "RootX_M.rotateX") + 8.0)
text = meanrig.update()
print(text)
fix = mp.load(FIX)
gate("pelvis" in fix["rot"] and abs(deg(fix["rot"]["pelvis"]) - 8.0) < 1.0,
     "the pelvis's turn %.2f deg (8 asked)" % deg(fix["rot"].get("pelvis", np.eye(3))))
w3 = sw.load_walk("asd", {})[0]
hip = w3.clip.worlds[w3.index["thigh_l"], :, 3, :3]
knee = w3.clip.worlds[w3.index["calf_l"], :, 3, :3]
ankle = w3.clip.worlds[w3.index["foot_l"], :, 3, :3]
walk_path = os.path.join(TEMP, "asd.walk.gz")
#  the plain cycle read the same way - the analysis turns a walk onto its root's facing (asd: 2.7 deg)
plain = wm.analyse(sw._cleaned(walk_path, os.path.getmtime(walk_path), sw.wf.load(walk_path), {})[0]).clip
p_hip, p_knee, p_ankle = (plain.worlds[plain.names.index(n), :, 3, :3] for n in ("thigh_l", "calf_l", "foot_l"))
thigh = float(np.abs(np.linalg.norm(knee - hip, axis=1) - np.linalg.norm(p_knee - p_hip, axis=1)).max())
shin = np.linalg.norm(ankle - knee, axis=1) - np.linalg.norm(p_ankle - p_knee, axis=1)
planted = float(np.abs(ankle - p_ankle).max())
gate(thigh < 1e-4 and planted < 1e-4 and float(shin.min()) > -1e-4,
     "the corrected cycle's ankles where the walk plants them (%.6f cm), the thighs their length (%.6f cm), a shin "
     "stretched where a raised hip falls short (%d frames, %.2f cm at most)"
     % (planted, thigh, int((shin > 1e-4).sum()), float(shin.max())))
feet_after = target_frames("foot_l")[:, 3, :3]
shift = np.linalg.norm(feet_after - feet_before, axis=1)
gate(float(np.median(shift)) < 3.0, "the target's left foot stays about where it walked (median %.2f cm, the toe "
     "turn and the pelvis in it)" % float(np.median(shift)))

# ---- the walk read again, and Reset ----
walk2 = sw.load_walk("asd", {})[0]
gate(abs(walk2.fix["knee"]["l"] - fix["knee"]["l"]) < 1e-9, "the walk read again carries the legs' correction")
r = walk2.evaluate(walk2.own_knobs())
gate(np.isfinite(r.worlds).all(), "the corrected walk evaluates")
text = meanrig.reset("asd")
print(text)
gate(not os.path.exists(FIX) and meanrig.update() is None, "Reset drops the file; the rig back in the mean pose reads none")
back_arm = mean_local("upperarm_l")
gate(deg(back_arm @ before_arm.T) < 0.05, "the target walks the plain walk again (%.4f deg)" % deg(back_arm @ before_arm.T))

meanrig.stop()
shutil.rmtree(TEMP, ignore_errors=True)
print("FAILED gates: %s" % FAILED if FAILED else "every gate passed (%d)" % COUNT[0])
