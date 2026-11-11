"""verify_walk_head_aim.py - Walk Builder's Head aim in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_head_aim.py

The animator (2026-11-11): «для головы сделаем такую-же систему фиксации как и для оружия ... создавать голове аим и
контролировать ручкой насколько она смотрит туда». The design: docs/superpowers/specs/2026-11-11-walk-head-aim-design.md.

A Manny UE5 skeleton walks `asd` under the two-handed sword pose; its mean pose rig is stood; Head aim makes the
target on the rig; the target is moved 40 cm to the left and 20 down; Update reads it; every gate measures the
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
from maya_walk import meanrig, headaim                   # noqa: E402
import maya_rigs                                         # noqa: E402
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
TEMP = tempfile.mkdtemp(prefix="walkhead_")
shutil.copy(WALK_SOURCE, TEMP)
shutil.copy(POSE_SOURCE, TEMP)
sw.WALKS = TEMP

cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace="B", ignoreVersion=True)
B = cmds.ls("B:root", long=True)[0]
SHARE = [1.0]


def params():
    changes = {} if SHARE[0] >= 1.0 else {"head_aim": ("offset", SHARE[0] - 1.0)}
    return sw.normal_params({"pose": 1.0, "changes": changes})


print(sw.apply(B, "asd", {}, POSE, sw.ALL_PARTS, params=params())[2])
B = cmds.ls(B, long=True)[0]
sw.set_working([B])


def rekey(root):
    memo = sw.memo_of(root)
    print("   ", sw.apply(root, memo["walk"], {}, POSE, sw.ALL_PARTS, record=False, params=params())[2][-220:])
    return " -> keyed again"


def curves(ns):
    return dict((c, (cmds.keyframe(c, query=True, timeChange=True), cmds.keyframe(c, query=True, valueChange=True)))
                for c in cmds.ls(ns + ":*", type="animCurve") or []
                if cmds.listConnections(c, source=False, destination=True, type="joint"))


BEFORE = curves("B")
TIMES = cmds.keyframe(cmds.ls("B:pelvis", long=True)[0], attribute="rotateX", query=True, timeChange=True)


def world(name, t):
    path = cmds.ls("B:" + name, long=True)[0]
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=t)).reshape(4, 4)


def angle(a, b):
    a, b = headaim._unit(a), headaim._unit(b)
    return math.degrees(math.acos(min(max(float(np.dot(a, b)), -1.0), 1.0)))


def miss(aimed):
    """The most the head's look misses the target over the keys, in degrees."""
    worst = 0.0
    for t in TIMES:
        H, R = headaim._rigid(world("head", t)), headaim._rigid(world("root", t))
        T = headaim._point_of(aimed["target"], R)
        worst = max(worst, angle(np.asarray(aimed["aim"]) @ H[:3, :3], T - H[3, :3]))
    return worst


print(meanrig.press(B))
rig = meanrig.find(B)
gate(rig is not None, "the mean pose rig stands (%s)" % (rig.namespace if rig else None))
line = headaim.press(B, rekey)
print(line)
target = headaim.target_of(rig)
gate(target is not None and cmds.listRelatives(target, parent=True, fullPath=True)[0] == cmds.ls(rig.main, long=True)[0],
     "the head target stands under the rig's Main: %s" % target)
aimed = sw.edits_of(B)["head"]
gate(aimed is not None, "kept on the walker: %s" % (headaim.summary(aimed) if aimed else None))
walked = miss(aimed)
gate(walked < 0.01, "the head looks at the target on every key: %.5f deg" % walked)

# the target moved on the rig, Update reads it
rig_head = np.array(cmds.xform(maya_rigs.node(rig, "head"), query=True, worldSpace=True, translation=True))
old = np.array(cmds.xform(target, query=True, worldSpace=True, translation=True))
cmds.xform(target, worldSpace=True, translation=list(old + np.array([40.0, -20.0, 0.0])))
cmds.currentTime(cmds.currentTime(query=True))
print(meanrig.update(rekey))
aimed2 = sw.edits_of(B)["head"]
moved = float(np.linalg.norm(np.array(aimed2["target"]) - np.array(aimed["target"])))
gate(abs(moved - math.hypot(40.0, 20.0)) < 0.01, "Update takes the target moved on the rig: %.3f cm" % moved)
after = miss(aimed2)
gate(after < 0.01, "after Update the head looks at the new point on every key: %.5f deg" % after)
turned = max(angle(np.asarray(aimed["aim"]) @ headaim._rigid(world("head", t))[:3, :3],
                   np.asarray(aimed2["aim"]) @ headaim._rigid(world("head", t))[:3, :3]) for t in TIMES)
look_now = [np.asarray(aimed2["aim"]) @ headaim._rigid(world("head", t))[:3, :3] for t in TIMES]

# the parameter: half way
SHARE[0] = 0.0
rekey(B)
own = [np.asarray(aimed2["aim"]) @ headaim._rigid(world("head", t))[:3, :3] for t in TIMES]
SHARE[0] = 0.5
rekey(B)
half = [np.asarray(aimed2["aim"]) @ headaim._rigid(world("head", t))[:3, :3] for t in TIMES]
off = max(abs(angle(o, h) - 0.5 * angle(o, w)) for o, h, w in zip(own, half, look_now))
gate(off < 0.05, "Head aim 0.5 turns the head half way on every key: %.4f deg off" % off)
far = max(angle(o, w) for o, w in zip(own, look_now))
gate(far > 5.0, "Head aim 0 is the walk's own head, %.1f deg off the target" % far)
SHARE[0] = 1.0

print(headaim.remove(B, rekey))
gate(headaim.target_of(rig) is None, "Remove deletes the rig's target")
AFTER = curves("B")
worst = 0.0
for c, (ts, vs) in BEFORE.items():
    ts2, vs2 = AFTER.get(c, (None, None))
    if ts2 is None or len(ts2) != len(ts):
        worst = 1e9
        continue
    worst = max(worst, max(abs(a - b) for a, b in zip(vs, vs2)) if vs else 0.0)
gate(worst < 1e-6, "Remove gives the walk back key for key: %.2e" % worst)
gate(sw.edits_of(B).get("head") is None, "the head aim is gone from the walker")
print("FAILED:", FAILED if FAILED else "none", "of", COUNT[0])
