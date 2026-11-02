"""verify_walk_one_arm.py - one arm out of Walk Builder's additive pose, playing the cycle, in mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_one_arm.py

The animator (2026-11-02): «еще нам нужен инструмент который позводит исключить одну из рук из адетивной позы и
оставить анимации цикла». The design: docs/superpowers/specs/2026-11-02-walk-one-arm-out-of-the-pose-design.md.

Four Manny UE5 skeletons walk `asd` under the two-handed sword pose at share 1 - the pose that stills BOTH arms
today - with the pose's parts differing per skeleton:

  A  every part            B  no Arm L            C  neither arm            D  no Arm R
  E  the legacy list («arms», as a walker keyed before the split carries it)

Every gate measures the skeletons' own keys. Rotations are compared in the WORLD: the skeletons stand apart on
X, and a translation does not turn a bone.
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

for plugin in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except RuntimeError:
        pass

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
from maya_walk import scene as sw                        # noqa: E402
from maya_walk import pose as wp                         # noqa: E402
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
    return math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(np.asarray(r, float))))))


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha1(handle.read()).hexdigest()


# ---- the walks folder: the animator's asd and its sword pose, copied ----
REAL = sw.folder()
MINE = os.path.join(HERE, "walks")
POSE = "two_handed_sword"


def source_of(name, suffix):
    for folder in (REAL, MINE):
        path = os.path.join(folder, name + suffix)
        if os.path.exists(path):
            return path
    return None


WALK_SOURCE, POSE_SOURCE = source_of("asd", ".walk.gz"), source_of(POSE, ".wpose.gz")
if WALK_SOURCE is None or POSE_SOURCE is None:
    print("SKIP: no asd walk or %s pose in %s / %s" % (POSE, REAL, MINE))
    sys.exit(0)
TEMP = tempfile.mkdtemp(prefix="walkonearm_")
shutil.copy(WALK_SOURCE, TEMP)
shutil.copy(POSE_SOURCE, TEMP)
sw.WALKS = TEMP
WALK_FILE = os.path.join(TEMP, "asd.walk.gz")
FILE_HASH = digest(WALK_FILE)

ALL = tuple(sw.ALL_PARTS)
WITHOUT = lambda *out: tuple(p for p in ALL if p not in out)
CASES = (("A", ALL), ("B", WITHOUT("arm_l")), ("C", WITHOUT("arm_l", "arm_r")), ("D", WITHOUT("arm_r")),
         ("E", ("torso", "pelvis", "knees", "arms", "feet")))

cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
PARAMS = sw.normal_params({"pose": 1.0})
LINES = {}
started = time.time()
for i, (ns, parts) in enumerate(CASES):
    cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace=ns, ignoreVersion=True)
    root = cmds.ls(ns + ":root", long=True)[0]
    cmds.xform(root, worldSpace=True, translation=(300.0 * i, 0.0, 0.0))
    LINES[ns] = sw.apply(root, "asd", {}, POSE, parts, params=PARAMS)[2]
    print(LINES[ns])
print("(%.1f s)" % (time.time() - started))

TIMES = cmds.keyframe(cmds.ls("A:pelvis", long=True)[0], attribute="rotateX", query=True, timeChange=True)
N = len(TIMES)


def world(ns, name, f):
    path = cmds.ls("%s:%s" % (ns, name), long=True)[0]
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=TIMES[f])).reshape(4, 4)


def rot(ns, name, f):
    return wm.orthonormal(world(ns, name, f)[:3, :3])


def local(ns, name, f, walk):
    parent = walk.names[walk.parents[walk.index[name]]]
    return rot(ns, name, f) @ rot(ns, parent, f).T


ARM = ("upperarm", "lowerarm", "hand", "index_01")
WALK = sw.load_walk("asd")[0]


def arm_apart(a, b, side, bones=ARM):
    """The worst turn between two skeletons' arm bones, over every frame."""
    worst = 0.0
    for bone in bones:
        name = "%s_%s" % (bone, side)
        if name not in WALK.index:
            continue
        worst = max([worst] + [deg(rot(a, name, f) @ rot(b, name, f).T) for f in range(N)])
    return worst


def swing(ns, name):
    """How far a bone turns over the cycle in the world (its own swing)."""
    return max(deg(rot(ns, name, f) @ rot(ns, name, 0).T) for f in range(N))


gate(abs(float(sw.memo_of(cmds.ls("A:root", long=True)[0])["params"]["pose"]) - 1.0) < 1e-9
     and "pose two_handed_sword x1.00" in LINES["A"],
     "all five walk asd under the %s pose at share 1" % POSE)

# ---- the pose does move both arms (so an exclusion is visible at all) ----
gate(arm_apart("A", "C", "l") > 1.0 and arm_apart("A", "C", "r") > 1.0,
     "the pose moves both arms: left %.1f deg, right %.1f deg against the walk with no pose arms"
     % (arm_apart("A", "C", "l"), arm_apart("A", "C", "r")))

# ---- Arm L off: the left arm plays the cycle, the right one is untouched ----
# the arm's own mixing is exact (tests/test_walk_one_arm.py measures it with the springs and the carry off);
# in the whole rig what is left is the body under it - Balance carries the hips differently once an arm swings,
# and the chest's own fit follows the shoulder line (gate 12 measures that body)
left_cycle = arm_apart("B", "C", "l")
gate(left_cycle < 2.0, "Arm L off: its left arm plays the cycle to %.3f deg (against 138 deg of pose) - what is "
     "left is the body under it" % left_cycle)
gate(arm_apart("B", "A", "l") > 1.0, "and that is not what the pose asked: %.1f deg from it"
     % arm_apart("B", "A", "l"))
right_kept = arm_apart("B", "A", "r")
right_cycle = arm_apart("B", "C", "r")
gate(right_kept < 12.0 and right_cycle > 100.0,
     "the right arm still stands in the pose: %.1f deg from the walk's own, %.1f deg from A - the pose's mean "
     "and its stilling are kept, the two-handed carry is off (one hand cannot hold a thing with two)"
     % (right_cycle, right_kept))

b_swing, a_swing, c_swing = swing("B", "upperarm_l"), swing("A", "upperarm_l"), swing("C", "upperarm_l")
gate(abs(b_swing - c_swing) < 2.0 and b_swing - a_swing > 1.0,
     "its left upper arm hangs and swings in the world again: %.2f deg over the cycle (the cycle's own %.2f, "
     "the pose's %.2f)" % (b_swing, c_swing, a_swing))

# ---- the weapon stays in the hand the pose put it in ----
def grip_of(ns):
    out = []
    for f in range(N):
        hand = world(ns, "hand_r", f)
        out.append(world(ns, "weapon_r", f) @ np.linalg.inv(hand))
    return out


kept = max(deg(b[:3, :3] @ np.linalg.inv(a[:3, :3])) for a, b in zip(grip_of("A"), grip_of("B")))
moved = max(float(np.linalg.norm(b[3, :3] - a[3, :3])) for a, b in zip(grip_of("A"), grip_of("B")))
gate(kept < 0.05 and moved < 0.05, "the right hand keeps the weapon exactly as the pose holds it: %.4f deg, "
     "%.4f cm in the hand's own frame" % (kept, moved))

# ---- Arm R off: the mirror ----
gate(arm_apart("D", "C", "r") < 2.0 and arm_apart("D", "C", "l") > 100.0,
     "Arm R off is the mirror: its right arm plays the cycle (%.3f deg) and its left stands in the pose "
     "(%.1f deg from the walk's own, %.1f from A)"
     % (arm_apart("D", "C", "r"), arm_apart("D", "C", "l"), arm_apart("D", "A", "l")))

# ---- the line says it ----
gate("left arm out of the pose" in LINES["B"] and "right arm out of the pose" in LINES["D"]
     and "out of the pose" not in LINES["A"] and "out of the pose" not in LINES["C"],
     "the Pick line names the arm left out, and says nothing when none or both are")

# ---- a walker keyed before the split keeps both arms ----
gate(arm_apart("E", "A", "l") < 0.05 and arm_apart("E", "A", "r") < 0.05,
     "a stored «arms» means both arms on the next press: %.4f / %.4f deg from A"
     % (arm_apart("E", "A", "l"), arm_apart("E", "A", "r")))
memo = sw.memo_of(cmds.ls("E:root", long=True)[0])
gate(tuple(memo.get("parts") or ()) == ALL, "and the memo is written with this build's names: %s"
     % (memo.get("parts"),))

# ---- the body under the arms: the legs and the pelvis are the pose's in every case ----
body = dict((name, max(max(deg(rot(ns, name, f) @ rot("A", name, f).T) for f in range(N))
                       for ns in ("B", "C", "D")))
            for name in ("pelvis", "spine_01", "spine_03", "thigh_l", "foot_r"))
gate(max(body.values()) < 4.0, "the body under them is the pose's throughout: %s - what moves is Balance's own "
     "carry (an arm that swings moves the centre of mass) and the chest's fit, which follows the shoulder line"
     % ", ".join("%s %.2f deg" % (n, v) for n, v in sorted(body.items())))

# ---- nothing of the library's ----
beside = [f for f in os.listdir(TEMP) if f.endswith((".walkkeys.json", ".walkfix.json"))]
gate(digest(WALK_FILE) == FILE_HASH and not beside,
     "the library's walk file is unchanged and nothing was written beside it (%s)" % (beside or "nothing"))

print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": %s" % FAILED) if FAILED else ""))
shutil.rmtree(TEMP, ignore_errors=True)
sys.exit(1 if FAILED else 0)
