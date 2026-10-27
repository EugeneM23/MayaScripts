"""verify_walk_working.py - Walk Builder's working walkers, their own edits, every rig control read, the smart split
and the knee pop fix, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_working.py

The animator (2026-10-27): «когда мы нажимаем pick ... все наши изменения попадут на нее в независимости от
выделения ... Текущая походка загруженная из библиотеки не должна пострадать ... наша анимация реагирует на
изменения всех контроллеров риг поз ... инструмент который будет чинить щелчки в колене ... наш цикл должен
измениться по умному». The design: docs/superpowers/specs/2026-10-27-walk-builder-working-walkers-design.md.
The walks asd and HavyRun (the animator's walks folder, read only) copied into a temporary walks folder; two Manny
skeletons walk asd, B the working one; four key rigs and a mean pose rig for B, their controls moved as the
animator moves them, Update pressed by hand.
"""
import hashlib
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
from maya_walk import keyrig, keyposes as kp, meanrig, target as wt   # noqa: E402
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


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha1(handle.read()).hexdigest()


REAL = sw.folder()
ORIGINAL = os.path.join(REAL, "asd.walk.gz")
if not os.path.exists(ORIGINAL):
    print("SKIP: no asd walk in %s" % REAL)
    sys.exit(0)
TEMP = tempfile.mkdtemp(prefix="walkworking_")
for name in ("asd", "HavyRun"):
    if os.path.exists(os.path.join(REAL, name + ".walk.gz")):
        shutil.copy(os.path.join(REAL, name + ".walk.gz"), TEMP)
sw.WALKS = TEMP
WALK_FILE = os.path.join(TEMP, "asd.walk.gz")
FILE_HASH = digest(WALK_FILE)

cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
roots = {}
for ns, x in (("A", 0.0), ("B", 400.0)):
    cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace=ns, ignoreVersion=True)
    root = cmds.ls(ns + ":root", long=True)[0]
    cmds.xform(root, worldSpace=True, translation=(x, 0.0, 0.0))
    roots[ns] = root
PARAMS = sw.normal_params({})
for ns in ("A", "B"):
    print(sw.apply(roots[ns], "asd", {}, params=PARAMS)[2])
sw.set_working([roots["B"]])
A, B = (cmds.ls(roots[n], long=True)[0] for n in ("A", "B"))
gate(sw.working() == [B], "B is the working walker (%s)" % [sw.walker_label(r) for r in sw.working()])


def curves_of(ns):
    out = {}
    for curve in cmds.ls(ns + ":*", type="animCurve") or []:
        out[curve] = cmds.keyframe(curve, query=True, valueChange=True)
    return out


A_BEFORE = curves_of("A")


def times(ns):
    return cmds.keyframe(cmds.ls(ns + ":pelvis", long=True)[0], attribute="rotateX", query=True, timeChange=True)


def world(ns, name, f):
    path = cmds.ls("%s:%s" % (ns, name), long=True)[0]
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=times(ns)[f])).reshape(4, 4)


def local(ns, name, f, walk):
    parent = walk.names[walk.parents[walk.index[name]]]
    return wm.orthonormal(world(ns, name, f)[:3, :3]) @ wm.orthonormal(world(ns, parent, f)[:3, :3]).T


# ---- the key rigs: B's, standing in B's animation ----
started = time.time()
print(keyrig.press(B), "(%.1f s)" % (time.time() - started))
rigs = keyrig.rigs(B)
gate(len(rigs) == 4 and all(keyrig.memo_of(r).get("walker") == meanrig.uuid_of(B) for r in rigs),
     "Create key poses added four rigs, each B's (%s)" % ", ".join(r.namespace for r in rigs))
anim = sw.walker_animation(B)
FR = kp.frames_of(anim.steps, anim.rw.P)
worst_turn, worst_pelvis = 0.0, 0.0
for rig in rigs:
    memo = keyrig.memo_of(rig)
    shown = kp.measure(meanrig._read(rig, anim.walk, anim.statics, memo), anim.rw)
    want = kp.measure(dict((n, anim.moving[j, memo["frame"]]) for j, n in enumerate(anim.walk.names)), anim.rw)
    worst_turn = max([worst_turn] + [deg(shown["local"][n] @ want["local"][n].T) for n in want["local"]])
    worst_pelvis = max(worst_pelvis, float(np.linalg.norm(shown["pelvis"] - want["pelvis"])))
gate(worst_turn < 0.05 and worst_pelvis < 0.05, "each rig stands in B's own animation at its key: upper locals "
     "%.4f deg, the pelvis %.4f cm" % (worst_turn, worst_pelvis))
gate(keyrig.update() == keyrig.NOTHING_MOVED, "untouched rigs read no change")
by_key = dict((keyrig.memo_of(r)["key"], r) for r in rigs)
ns = lambda key: by_key[key].namespace + ":"

# ---- Main moved is no pose change ----
contact_main = by_key["contact"].main
cmds.setAttr(contact_main + ".translateX", cmds.getAttr(contact_main + ".translateX") + 30.0)
cmds.setAttr(contact_main + ".rotateY", 25.0)
gate(keyrig.update() == keyrig.NOTHING_MOVED, "Main moved 30 cm and turned 25 deg on the Contact rig: no edit")

# ---- an arm turned on Contact, exact on B, A untouched, the library's file untouched ----
before = local("B", "upperarm_l", FR["contact"], anim.walk)
before_down = local("B", "upperarm_l", FR["down"], anim.walk)
cmds.setAttr(ns("contact") + "FKShoulder_L.rotateZ", cmds.getAttr(ns("contact") + "FKShoulder_L.rotateZ") + 20.0)
started = time.time()
line = keyrig.update()
print(line, "(%.1f s)" % (time.time() - started))
edits = sw.edits_of(B)
turned = deg(edits["keys"].get("contact", kp.empty_key())["rot"].get("upperarm_l", np.eye(3)))
gate(abs(turned - 20.0) < 0.5, "the turn is B's own edit: upperarm_l %.2f deg (20 asked)" % turned)
anim = sw.walker_animation(B)
FR2 = kp.frames_of(anim.steps, anim.rw.P)
at_key = deg(local("B", "upperarm_l", FR2["contact"], anim.walk) @ before.T)
at_down = deg(local("B", "upperarm_l", FR2["down"], anim.walk) @ before_down.T)
gate(abs(at_key - 20.0) < 0.3 and at_down < 0.3, "B shows it exactly at the contact (%.2f deg) and not at the "
     "Down (%.2f deg) - put on its animation after the physics" % (at_key, at_down))
gate(curves_of("A") == A_BEFORE, "A (not working) is untouched, key for key")
gate(digest(WALK_FILE) == FILE_HASH and not [f for f in os.listdir(TEMP) if f.endswith((".walkkeys.json",
                                                                                      ".walkfix.json"))],
     "the library's walk file is unchanged, nothing written beside it")

# ---- a rig an older build stood (no walker, no Main frame): stood again, nothing read ----
old = by_key["passing"]
memo = keyrig.memo_of(old)
keyrig._set_memo(old, dict((k, v) for k, v in memo.items() if k not in ("walker", "main0", "root0", "poles")))
plug = old.namespace + ":RootX_M.translateY"
stood_y = cmds.getAttr(plug)
cmds.setAttr(plug, stood_y + 7.0)
keys_before = kp.dumps(sw.edits_of(B)["keys"])
line = keyrig.update()
print(line)
memo = keyrig.memo_of(old)
gate("older build" in line and kp.dumps(sw.edits_of(B)["keys"]) == keys_before and memo.get("main0")
     and memo.get("walker") == meanrig.uuid_of(B) and abs(cmds.getAttr(plug) - stood_y) < 0.05,
     "a rig an older build stood is B's, stood again (RootX_M %+.2f from its stand), nothing read - said"
     % (cmds.getAttr(plug) - stood_y))

# ---- the pelvis raised alike on all four: Height, as far as the legs reach ----
def mean_pelvis():
    return float(np.mean([world("B", "pelvis", f)[3, 1] for f in range(len(times("B")) - 1)]))


def moved_feet(keys):
    prints = kp.stance_prints(keys)
    feet = [float(np.linalg.norm(entry["foot"][s]["t"])) for entry in keys.values() for s in "lr"]
    return max([float(np.linalg.norm(prints[s]["t"])) for s in "lr"] + [abs(prints[s]["yaw"]) for s in "lr"]
               + feet + [0.0])


pelvis_before = mean_pelvis()
feet_before = moved_feet(sw.edits_of(B)["keys"])
for key in kp.KEYS:
    plug = ns(key) + "RootX_M.translateY"
    cmds.setAttr(plug, cmds.getAttr(plug) + 5.0)
line = keyrig.update()
print(line)
params = sw.memo_params(B, sw.memo_of(B), translate=False)
height = params["changes"].get("height")
gate(height is not None and abs(height[1] - 5.0) < 0.6 and "height" in params["pins"],
     "the pelvis +5 on all four is the walk's Height: %s, pinned" % (height,))
risen = mean_pelvis() - pelvis_before
said = "reach no further" in line
gate(risen > 0.3 and (risen > 4.0 or said), "B walks higher, as far as its legs reach: the pelvis %+.2f cm on "
     "average%s" % (risen, " - the line says the legs reach no further" if said else ""))
gate(moved_feet(sw.edits_of(B)["keys"]) - feet_before < 1e-6 and "pulled straight" in line,
     "the legs the raise pulled straight: their feet and toes not taken, said")
gate(keyrig.update() == keyrig.NOTHING_MOVED, "the rigs stood again in what B now does")

# ---- the pelvis lowered alike on all four: B walks lower by as much ----
for key in kp.KEYS:
    plug = ns(key) + "RootX_M.translateY"
    cmds.setAttr(plug, cmds.getAttr(plug) - 10.0)
line = keyrig.update()
print(line)
height = sw.memo_params(B, sw.memo_of(B), translate=False)["changes"].get("height")
lowered = mean_pelvis() - pelvis_before
gate(height is not None and abs(height[1] + 5.0) < 0.6 and abs(lowered + 5.0) < 1.0,
     "the pelvis -10 on all four from there: Height %+.2f, B %+.2f cm on average against before the raise"
     % (height[1] if height else 0.0, lowered))
gate(keyrig.update() == keyrig.NOTHING_MOVED, "the rigs stood again in the lowered walk")

# ---- a planted foot moved: its print for the whole stance ----
anim = sw.walker_animation(B)
FR3 = kp.frames_of(anim.steps, anim.rw.P)
down = by_key["down"]
foot = cmds.ls(down.namespace + ":foot_l", long=True)[0]
start_foot = np.array(cmds.xform(foot, query=True, worldSpace=True, translation=True))
stance = kp.stance_weights(anim.rw, "l", anim.rw.P + 1)
held = [f for f in range(anim.rw.P) if stance[f] >= 1.0]
before_feet = np.array([world("B", "foot_l", f)[3, :3] for f in held])
ik = down.namespace + ":IKLeg_L"
for axis in ("translateX", "translateY", "translateZ"):
    pass
cmds.setAttr(ik + ".translateZ", cmds.getAttr(ik + ".translateZ") + 6.0)
moved = np.array(cmds.xform(foot, query=True, worldSpace=True, translation=True)) - start_foot
line = keyrig.update()
print(line)
prints = kp.stance_prints(sw.edits_of(B)["keys"])
gate(np.linalg.norm(prints["l"]["t"][:2]) > 3.0, "the planted left foot moved %.1f cm on the Down rig is its print "
     "(%s)" % (float(np.linalg.norm(moved)), np.round(prints["l"]["t"], 2)))
after_feet = np.array([world("B", "foot_l", f)[3, :3] for f in held])
shift = after_feet - before_feet
gate(float(np.ptp(np.linalg.norm(shift, axis=1))) < 0.3 and float(np.linalg.norm(shift.mean(axis=0))) > 3.0,
     "B's left foot stands %.2f cm away for its whole stance, held still (spread %.3f cm)"
     % (float(np.linalg.norm(shift.mean(axis=0))), float(np.ptp(np.linalg.norm(shift, axis=1)))))

# ---- a straightened leg's knee flip is not read ----
up = by_key["up"]
plug = up.namespace + ":RootX_M.translateY"
cmds.setAttr(plug, cmds.getAttr(plug) + 25.0)
knees_before = dict(sw.edits_of(B)["keys"].get("up", kp.empty_key())["knee"])
line = keyrig.update()
print(line)
knees_after = sw.edits_of(B)["keys"].get("up", kp.empty_key())["knee"]
flip = max(abs(knees_after[s] - knees_before[s]) for s in "lr")
gate(math.degrees(flip) < 20.0, "the Up rig's legs pulled straight: no knee flip read (%.1f deg taken)%s"
     % (math.degrees(flip), " - said" if "straight" in line or "flipped" in line else ""))

# ---- the mean pose rig: B's correction, the file untouched ----
print(meanrig.press(B))
mean = meanrig.find(B)
gate(mean is not None and meanrig.memo_of(mean).get("walker") == meanrig.uuid_of(B), "the mean pose rig is B's")
plug = mean.namespace + ":FKSpine2_M.rotateX"
if cmds.objExists(plug):
    cmds.setAttr(plug, cmds.getAttr(plug) + 10.0)
line = meanrig.update()
print(line)
gate(not sw.mp.is_empty(sw.edits_of(B)["fix"]) and digest(WALK_FILE) == FILE_HASH,
     "the mean pose's turn is B's correction; the walk's file unchanged")

# ---- Reset key poses: B's key edits gone ----
print(keyrig.reset(B))
gate(kp.is_empty(sw.edits_of(B)["keys"]), "Reset key poses drops B's key edits")
print(keyrig.delete(B))
print(meanrig.delete(B))
gate(not keyrig.rigs() and not meanrig.rigs(), "Delete takes the rigs out")

# ---- the knee pop fix on a run ----
if os.path.exists(os.path.join(TEMP, "HavyRun.walk.gz")):
    cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace="R", ignoreVersion=True)
    run = cmds.ls("R:root", long=True)[0]
    result, info, line = sw.apply(run, "HavyRun", {}, params=sw.normal_params({"knee_pops": False}))
    rough = info["pops"]
    result, info, line = sw.apply(run, "HavyRun", {}, params=sw.normal_params({}))
    print(line)

    def bends():
        out = {}
        for side in "lr":
            vals = []
            for t in times("R")[:-1]:
                P = lambda n: np.array(cmds.getAttr("R:%s_%s.worldMatrix[0]" % (n, side), time=t)).reshape(4, 4)[3, :3]
                h, k, a = P("thigh"), P("calf"), P("foot")
                vals.append(wt._angle(k - h, a - k))
            out[side] = np.array(vals)
        return out
    left = wt.pops(bends())
    gate(info["pops"]["fixed"] >= 1 and not any(left.values()),
         "HavyRun's knee pops smoothed: %s; none left in the keys" % wt.pops_line(info["pops"]))

shutil.rmtree(TEMP, ignore_errors=True)
print("%s (%d)" % ("every gate passed" if not FAILED else "FAILED gates: %s" % FAILED, COUNT[0]))
