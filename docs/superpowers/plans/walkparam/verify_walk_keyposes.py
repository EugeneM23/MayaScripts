"""verify_walk_keyposes.py - Walk Builder's key poses on four rigs, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_keyposes.py

The animator (2026-10-26): «Мы находим в нашем цикле 4 ключевые позы через которые строится походка или бег,
выносим эти позы каждую на свой риг и изменяя риги контролируем весь наш цикл а умные обработчики нам помогают».
The walk asd (walks/, git-ignored) in a temporary walks folder; the plugin's Manny skeleton the walker; Create key
poses adds four Manny rigs; their controls are moved as the animator would and Update pressed by hand.
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
from maya_walk import keyrig, keyposes as kp, meanpose as mp, meanrig   # noqa: E402
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

TEMP = tempfile.mkdtemp(prefix="walkkeys_")
shutil.copy(ORIGINAL, TEMP)
sw.WALKS = TEMP
KEYS = kp.path_for(os.path.join(TEMP, "asd.walk.gz"))

cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace="M", ignoreVersion=True)
target = cmds.ls("M:root", long=True)[0]
_, info, line = sw.apply(target, "asd", {})
print(line)
TIMES = cmds.keyframe(cmds.ls("M:pelvis", long=True)[0], attribute="rotateX", query=True, timeChange=True)


def world(name, f):
    path = cmds.ls("M:" + name, long=True)[0]
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=TIMES[f])).reshape(4, 4)


def local(name, f):
    walk = sw.load_walk("asd", {})[0]
    parent = walk.names[walk.parents[walk.index[name]]]
    return wm.orthonormal(world(name, f)[:3, :3]) @ wm.orthonormal(world(parent, f)[:3, :3]).T


def up_of(name, f):
    return float(world(name, f)[3, 1])


walk = sw.load_walk("asd", {})[0]
steps = walk.key_steps
FR = kp.frames_of(steps, walk.P)
OTHER = dict((k, [s for s in steps if s["side"] != kp.REF_SIDE][0][k] % walk.P) for k in kp.KEYS)
print("key frames %s, the right foot's %s" % (FR, OTHER))
before = {"arm_contact": local("upperarm_l", FR["contact"]), "arm_down": local("upperarm_l", FR["down"]),
          "arm_r_contact": local("upperarm_r", OTHER["contact"]),
          "pelvis_down": up_of("pelvis", FR["down"]), "pelvis_passing": up_of("pelvis", FR["passing"]),
          "foot_r_passing": up_of("foot_r", FR["passing"]), "foot_l_other": up_of("foot_l", OTHER["passing"])}

# ---- the press: four Manny rigs in the key poses ----
started = time.time()
text = keyrig.press("asd")
print(text, "(%.1f s)" % (time.time() - started))
rigs = keyrig.rigs("asd")
gate(len(rigs) == 4 and [keyrig.memo_of(r)["key"] for r in rigs] == list(kp.KEYS),
     "Create key poses added four rigs, Contact Down Passing Up (%s)" % ", ".join(r.namespace for r in rigs))
tx, _, tz = cmds.xform(target, query=True, worldSpace=True, translation=True)
places = [cmds.xform(r.main, query=True, worldSpace=True, translation=True) for r in rigs]
gate(all(abs(p[0] - (tx - keyrig.OFFSET - keyrig.GAP * i)) < 1e-3 and abs(p[2] - tz) < 1e-3
         for i, p in enumerate(places)), "they stand in a row beside the walker (x %s)" % [round(p[0], 1) for p in places])
statics = sw.load_walk("asd", {})[1]
worst_turn, worst_pelvis = 0.0, 0.0
for rig in rigs:
    key = keyrig.memo_of(rig)["key"]
    shown = kp.measure(meanrig._read(rig, walk, statics), walk)
    want = kp.measure(dict((n, walk.clip.worlds[j, FR[key]]) for j, n in enumerate(walk.names)), walk)
    worst_turn = max([worst_turn] + [deg(shown["local"][n] @ want["local"][n].T) for n in want["local"]])
    worst_pelvis = max(worst_pelvis, float(np.linalg.norm(shown["pelvis"] - want["pelvis"])))
gate(worst_turn < 0.05 and worst_pelvis < 0.05, "each rig's game skeleton stands in its key's frame: every upper "
     "bone's local to %.4f deg, the pelvis to %.4f cm" % (worst_turn, worst_pelvis))
controls = [c for r in rigs for c in meanrig._controls(r)]
keyed = [c for c in controls if cmds.listConnections(c, source=True, destination=False, type="animCurveTA")]
gate(not keyed, "no control is keyed (%d of %d)" % (len(keyed), len(controls)))
gate(keyrig.update() == keyrig.NOTHING_MOVED and not os.path.exists(KEYS), "untouched rigs read no change, write nothing")

by_key = dict((keyrig.memo_of(r)["key"], r.namespace + ":") for r in rigs)

# ---- the left arm turned on the Contact rig ----
ns = by_key["contact"]
cmds.setAttr(ns + "FKShoulder_L.rotateZ", cmds.getAttr(ns + "FKShoulder_L.rotateZ") + 20.0)
started = time.time()
text = keyrig.update()
print(text, "(%.1f s)" % (time.time() - started))
keys = kp.load(KEYS)
turned = deg(keys.get("contact", kp.empty_key())["rot"].get("upperarm_l", np.eye(3)))
gate(abs(turned - 20.0) < 0.5, "the turn goes into the Contact key: upperarm_l %.2f deg (20 asked)" % turned)
gate("keyed again" in text, "the walker is keyed again")
walk_path = os.path.join(TEMP, "asd.walk.gz")
plain = wm.analyse(sw._cleaned(walk_path, os.path.getmtime(walk_path), sw.wf.load(walk_path), {})[0]).clip
corrected = sw.load_walk("asd", {})[0].clip


def cycle_turn(name, f):
    """How far the corrected cycle turns `name` (its local) at frame f against the plain cycle."""
    j = plain.names.index(name)
    p = plain.parents[j]
    lo = lambda c: wm.orthonormal(c.worlds[j, f, :3, :3]) @ wm.orthonormal(c.worlds[p, f, :3, :3]).T
    return deg(lo(corrected) @ lo(plain).T)


in_cycle = (cycle_turn("upperarm_l", FR["contact"]), cycle_turn("upperarm_l", FR["down"]),
            cycle_turn("upperarm_r", OTHER["contact"]), cycle_turn("upperarm_l", OTHER["contact"]))
gate(abs(in_cycle[0] - turned) < 0.01 and in_cycle[1] < 0.01 and abs(in_cycle[2] - turned) < 0.01
     and in_cycle[3] < 0.01, "the cycle: upperarm_l turned %.3f deg at the contact, %.3f at the Down; at the right "
     "foot's contact upperarm_r %.3f (the mirror), upperarm_l %.3f" % in_cycle)
at_key = deg(local("upperarm_l", FR["contact"]) @ before["arm_contact"].T)
mirrored = deg(local("upperarm_r", OTHER["contact"]) @ before["arm_r_contact"].T)
gate(at_key > 0.6 * turned and abs(mirrored - at_key) < 1.0,
     "the walker: upperarm_l %.2f deg at the contact, upperarm_r %.2f at the right foot's (its arms' inertia smooths "
     "the edit)" % (at_key, mirrored))
gate(keyrig.update() == keyrig.NOTHING_MOVED, "read again with nothing moved: no change")

# ---- the pelvis lowered on the Down rig ----
ns = by_key["down"]
cmds.setAttr(ns + "RootX_M.translateY", cmds.getAttr(ns + "RootX_M.translateY") - 4.0)
text = keyrig.update()
print(text)
keys = kp.load(KEYS)
pelvis = keys["down"]["pelvis"]
gate(abs(pelvis[2] + 4.0) < 0.3, "the Down key's pelvis %.2f cm (-4 asked)" % pelvis[2])
drop_key = up_of("pelvis", FR["down"]) - before["pelvis_down"]
drop_passing = up_of("pelvis", FR["passing"]) - before["pelvis_passing"]
gate(drop_key < -2.5 and abs(drop_passing) < 1.0, "the walker's pelvis %.2f cm at the Down, %.2f at the Passing"
     % (drop_key, drop_passing))
corrected = sw.load_walk("asd", {})[0].clip
feet = [corrected.names.index(n) for n in ("foot_l", "ball_l", "foot_r", "ball_r")]
planted = float(np.abs(corrected.worlds[feet, :, 3, :3] - plain.worlds[feet, :, 3, :3]).max())
gate(planted < 1e-4, "the corrected cycle's feet where the walk plants them (%.6f cm)" % planted)

# ---- the swinging foot lifted on the Passing rig; the standing foot moved (not taken) ----
ns = by_key["passing"]
cmds.setAttr(ns + "FKIKLeg_R.FKIKBlend", 10.0)
cmds.setAttr(ns + "FKIKLeg_L.FKIKBlend", 10.0)
text = keyrig.update()
print("legs to IK:", text)
cmds.move(0.0, 6.0, 0.0, ns + "IKLeg_R", relative=True, worldSpace=True)
cmds.move(5.0, 0.0, 0.0, ns + "IKLeg_L", relative=True, worldSpace=True)
text = keyrig.update()
print(text)
keys = kp.load(KEYS)
lift = keys["passing"]["foot"]["r"]["t"]
gate(abs(lift[2] - 6.0) < 0.6, "the Passing key's right foot up %.2f cm (6 asked)" % lift[2])
gate("not taken" in text and "foot_l" in text and float(np.abs(keys["passing"]["foot"]["l"]["t"]).max()) < 1e-6,
     "the standing left foot's move is not taken, and said")
raised = up_of("foot_r", FR["passing"]) - before["foot_r_passing"]
gate(raised > 3.0, "the walker's right foot %.2f cm higher at the Passing" % raised)
raised_other = up_of("foot_l", OTHER["passing"]) - before["foot_l_other"]
gate(raised_other > 3.0, "the left foot %.2f cm higher at the right foot's Passing, the mirror" % raised_other)
rig_shown = kp.measure(meanrig._read(keyrig.find("asd", "passing"), sw.load_walk("asd", {})[0], statics),
                       sw.load_walk("asd", {})[0])
cycle = sw.load_walk("asd", {})[0]
want = kp.measure(dict((n, cycle.clip.worlds[j, FR["passing"]]) for j, n in enumerate(cycle.names)), cycle)
off = float(np.linalg.norm(rig_shown["foot"]["l"][0] - want["foot"]["l"][0]))
gate(off < 0.5, "the Passing rig stood again in what the cycle does: its left foot back where it stands (%.2f cm)"
     % off)

# ---- Reset and Delete ----
text = keyrig.reset("asd")
print(text)
gate(not os.path.exists(KEYS) and keyrig.update() == keyrig.NOTHING_MOVED, "Reset drops the edits; the rigs read none")
back = deg(local("upperarm_l", FR["contact"]) @ before["arm_contact"].T)
gate(back < 0.1, "the walker walks the plain walk again (%.4f deg)" % back)
spaces = [r.namespace for r in rigs]
text = keyrig.delete("asd")
print(text)
gate(not keyrig.rigs() and not any(cmds.namespace(exists=":" + n) for n in spaces), "Delete takes the four rigs out")
try:
    keyrig.update()
    gate(False, "Update with no key rig refuses")
except keyrig.Refusal as refusal:
    gate(str(refusal) == keyrig.NO_RIG, "Update with no key rig refuses: %s" % refusal)
shutil.rmtree(TEMP, ignore_errors=True)
print("FAILED gates: %s" % FAILED if FAILED else "every gate passed (%d)" % COUNT[0])
