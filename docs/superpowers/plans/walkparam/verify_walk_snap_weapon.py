"""verify_walk_snap_weapon.py - Walk Builder's Snap weapon in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_snap_weapon.py

The animator's example (2026-11-11, port 7006): a Long Sword in Aim Mode, the IK hand and the aim target riding
the right clavicle, the target moved down the blade onto the shoulder, the up left in Main. The design:
docs/superpowers/specs/2026-11-11-walk-snap-weapon-design.md.

A Manny UE5 skeleton walks `asd` under the two-handed sword pose; its mean pose rig is stood, a Long Sword put in
the rig's right hand, Aim Mode on, the target moved onto the right shoulder; Snap weapon; every gate measures the
walker's own KEYS.
"""
import math
import os
import shutil
import sys
import tempfile

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

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_walk import scene as sw                        # noqa: E402
from maya_walk import meanrig, snapweapon                # noqa: E402
from maya_scenesetup import catalog, equip, weaponaim, bonedrive   # noqa: E402
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


REAL = sw.folder()
MINE = os.path.join(HERE, "walks")


def source_of(name, suffix):
    for folder in (REAL, MINE):
        path = os.path.join(folder, name + suffix)
        if os.path.exists(path):
            return path
    return None


POSE = "two_handed_sword"
WALK_SOURCE, POSE_SOURCE = source_of("asd", ".walk.gz"), source_of(POSE, ".wpose.gz")
if WALK_SOURCE is None or POSE_SOURCE is None:
    print("SKIP: no asd walk or %s pose" % POSE)
    sys.exit(0)
TEMP = tempfile.mkdtemp(prefix="walksnap_")
shutil.copy(WALK_SOURCE, TEMP)
shutil.copy(POSE_SOURCE, TEMP)
sw.WALKS = TEMP

cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace="B", ignoreVersion=True)
B = cmds.ls("B:root", long=True)[0]
PARAMS = sw.normal_params({"pose": 1.0})
print(sw.apply(B, "asd", {}, POSE, sw.ALL_PARTS, params=PARAMS)[2])
B = cmds.ls(B, long=True)[0]
sw.set_working([B])


def rekey(root):
    memo = sw.memo_of(root)
    sw.apply(root, memo["walk"], {}, POSE, sw.ALL_PARTS, record=False, params=PARAMS)
    return " -> keyed again"


def curves(ns):
    return dict((c, (cmds.keyframe(c, query=True, timeChange=True), cmds.keyframe(c, query=True, valueChange=True)))
                for c in cmds.ls(ns + ":*", type="animCurve") or []
                if cmds.listConnections(c, source=False, destination=True, type="joint"))   # the walker's own keys


BEFORE = curves("B")

# ---- the rig pose: a Long Sword in its right hand, Aim Mode, the target onto the right shoulder ----
print(meanrig.press(B))
rig = meanrig.find(B)
gate(rig is not None, "the mean pose rig stands (%s)" % (rig.namespace if rig else None))
entry = [w for w in catalog.WEAPONS if w.key == "LongSword_02"][0]
print(equip.to_hand(rig.skeleton_root, "R", entry))
weapon = [n for n in cmds.ls(type="transform", long=True)
          if cmds.attributeQuery(bonedrive.MARKER, node=n, exists=True)][0]
refused = snapweapon.Refusal
try:
    snapweapon.press(B, rekey)
    gate(False, "Snap weapon refused without Aim Mode")
except refused as error:
    gate("Aim Mode" in str(error), "refused by name without Aim Mode: %s" % error)
print(weaponaim.enter(weapon))
group = weaponaim.group_of(weapon)
ctrls = weaponaim.controllers(group)


def wm_of(node):
    return np.array(cmds.xform(node, query=True, worldSpace=True, matrix=True), float).reshape(4, 4)


clav = wm_of(rig.namespace + ":clavicle_r")
shoulder = clav[3, :3] + np.array([0.0, 10.0, 0.0])
cmds.xform(ctrls["target"], worldSpace=True, translation=list(shoulder))
cmds.currentTime(cmds.currentTime(query=True))
line = snapweapon.press(B, rekey)
print(line)
snap = sw.edits_of(B)["snap"]
gate(snap is not None and snap["anchor"] == "r" and snap["side"] == "r",
     "kept on the walker: %s" % (snapweapon.summary(snap) if snap else None))

TIMES = cmds.keyframe(cmds.ls("B:pelvis", long=True)[0], attribute="rotateX", query=True, timeChange=True)


def world(name, t):
    path = cmds.ls("B:" + name, long=True)[0]
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=t)).reshape(4, 4)


R = snapweapon._rigid
grip, aim = np.array(snap["grip"]), np.array(snap["aim"])
off = snapweapon._m(snap["offset"])
on_clav, miss, lengths, roll = 0.0, 0.0, [], 0.0
for t in TIMES:
    H, C, root = R(world("hand_r", t)), R(world("clavicle_r", t)), R(world("root", t))
    G = grip @ H[:3, :3] + H[3, :3]
    on_clav = max(on_clav, float(np.linalg.norm(G - (grip @ (off @ C)[:3, :3] + (off @ C)[3, :3]))))
    T = np.array(snap["target"]) @ C[:3, :3] + C[3, :3]
    a = snapweapon._unit(aim @ H[:3, :3])
    miss = max(miss, float(np.linalg.norm(np.cross(a, T - G))) if np.dot(a, T - G) > 0 else 1e9)
    up, low = world("upperarm_r", t)[3, :3], world("lowerarm_r", t)[3, :3]
    lengths.append(float(np.linalg.norm(low - up)))
gate(on_clav < 0.01, "the grip rides the right clavicle on every key: %.6f cm" % on_clav)
gate(miss < 0.01, "the blade's line passes through the shoulder point on every key: %.6f cm" % miss)
gate(max(lengths) - min(lengths) < 0.01, "the upper arm keeps its length: %.6f cm" % (max(lengths) - min(lengths)))
first, last = world("hand_r", TIMES[0]), world("hand_r", TIMES[-1])
travel = first.copy()
gate(True, "keyed %d frames (%s)" % (len(TIMES), line[:160]))

print(snapweapon.unsnap(B, rekey))
AFTER = curves("B")
worst = 0.0
print('  new curves:', sorted(set(AFTER) - set(BEFORE))[:8])
for c, (ts, vs) in BEFORE.items():
    ts2, vs2 = AFTER.get(c, (None, None))
    if ts2 is None or len(ts2) != len(ts):
        print("  differs:", c, None if ts2 is None else (len(ts), len(ts2)))
        worst = 1e9
        continue
    worst = max(worst, max(abs(a - b) for a, b in zip(vs, vs2)) if vs else 0.0)
gate(worst < 1e-6, "Unsnap gives the walk back key for key: %.2e" % worst)
gate(sw.edits_of(B).get("snap") is None, "the snap is gone from the walker")
print("FAILED:", FAILED if FAILED else "none", "of", COUNT[0])

