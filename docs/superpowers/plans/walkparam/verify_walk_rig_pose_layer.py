"""verify_walk_rig_pose_layer.py - Walk Builder's rig pose built on the additive pose and acting on the whole
animation as a top layer, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_rig_pose_layer.py

The animator (2026-11-02, port 7002): «Давай сделаем так что бы наша риг поза в walk builder строилась с учетом
адитивной позы и влияла на всю анимайию как верхний слой». The design:
docs/superpowers/specs/2026-11-02-walk-rig-pose-top-layer-design.md.

The case is the one today's build reads as nothing: a walker carrying a pose card at **share 1**. Two Manny UE5
skeletons walk the cycle `asd` under the two-handed sword pose, B the working one; its mean pose rig is stood,
its controls moved as the animator moves them, Update pressed by hand, and every gate measures B's own KEYS.

Gate 5 carries the control that names the defect: the same correction put the OLD way (in the cycle's frames,
`edits["fix"]`) reaches the walker by almost nothing at share 1.
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
from maya_walk import keyrig, keyposes as kp, meanpose as mp, meanrig    # noqa: E402
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
TEMP = tempfile.mkdtemp(prefix="walkrigpose_")
shutil.copy(WALK_SOURCE, TEMP)
shutil.copy(POSE_SOURCE, TEMP)
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
PARAMS = sw.normal_params({"pose": 1.0})
started = time.time()
for ns in ("A", "B"):
    print(sw.apply(roots[ns], "asd", {}, POSE, sw.ALL_PARTS, params=PARAMS)[2])
print("(%.1f s)" % (time.time() - started))
A, B = (cmds.ls(roots[n], long=True)[0] for n in ("A", "B"))
sw.set_working([B])


def curves_of(ns):
    out = {}
    for curve in cmds.ls(ns + ":*", type="animCurve") or []:
        out[curve] = cmds.keyframe(curve, query=True, valueChange=True)
    return out


A_BEFORE = curves_of("A")


def times(ns):
    return cmds.keyframe(cmds.ls(ns + ":pelvis", long=True)[0], attribute="rotateX", query=True, timeChange=True)


TIMES = times("B")


def world(ns, name, f):
    path = cmds.ls("%s:%s" % (ns, name), long=True)[0]
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=TIMES[f])).reshape(4, 4)


def local(ns, name, f, walk):
    parent = walk.names[walk.parents[walk.index[name]]]
    return wm.orthonormal(world(ns, name, f)[:3, :3]) @ wm.orthonormal(world(ns, parent, f)[:3, :3]).T


def every_frame(ns, name, walk):
    return [local(ns, name, f, walk) for f in range(len(TIMES))]


def heights(ns, name):
    return [float(world(ns, name, f)[3, 1]) for f in range(len(TIMES))]


def places(ns, name):
    return [world(ns, name, f)[3, :3].copy() for f in range(len(TIMES))]


ANIM = sw.walker_animation(B)
WALK = ANIM.walk
gate(abs(float(ANIM.knobs.get("pose", 0.0)) - 1.0) < 1e-9 and ANIM.pose is not None,
     "B walks asd under the %s pose at share %.1f" % (POSE, float(ANIM.knobs.get("pose", 0.0))))

# ---- the rig stands in the mean pose of the RESULT, not of the cycle ----
started = time.time()
print(meanrig.press(B), "(%.1f s)" % (time.time() - started))
rig = meanrig.find(B)
gate(rig is not None and meanrig.memo_of(rig).get("walker") == meanrig.uuid_of(B),
     "Create rig pose added %s, B's own" % (rig.namespace if rig else "-"))
anim = sw.walker_animation(B)
memo = meanrig.memo_of(rig)
rw = kp.result_walk(anim.walk, anim.moving)          # the frames the walker shows, read as a walk
shown = kp.measure(meanrig._read(rig, anim.walk, anim.statics, memo), rw)
want = kp.measure(mp.mean_pose(rw), rw)
plain = kp.measure(mp.mean_pose(anim.walk), rw)
worst = max(deg(shown["local"][n] @ want["local"][n].T) for n in want["local"])
apart = max(deg(want["local"][n] @ plain["local"][n].T) for n in plain["local"])
gate(worst < 0.05, "it stands in the mean pose of what B SHOWS: worst upper local %.4f deg" % worst)
gate(apart > 5.0, "and that is not the cycle's own mean pose: they stand %.1f deg apart (the pose at share 1)"
     % apart)
gate(meanrig.update() == meanrig.NOTHING_MOVED, "an untouched rig reads no change")

# ---- an arm turned on the rig: on EVERY frame of the walker ----
plug = rig.namespace + ":FKShoulder_L.rotateZ"
before = every_frame("B", "upperarm_l", WALK)
cmds.setAttr(plug, cmds.getAttr(plug) + 20.0)
started = time.time()
line = meanrig.update()
print(line, "(%.1f s)" % (time.time() - started))
entry = (sw.edits_of(B)["keys"] or {}).get(kp.CYCLE) or kp.empty_key()
asked = deg(entry["rot"].get("upperarm_l", np.eye(3)))
gate(abs(asked - 20.0) < 0.5, "the turn is B's whole-cycle entry: upperarm_l %.2f deg (20 asked)" % asked)
after = every_frame("B", "upperarm_l", WALK)
turns = [deg(a @ b.T) for a, b in zip(after, before)]
gate(max(abs(t - 20.0) for t in turns) < 1.0,
     "B shows it on EVERY frame: %.2f..%.2f deg over %d frames" % (min(turns), max(turns), len(turns)))

# the control: the same correction put the OLD way (in the cycle's frames) at share 1
edits = sw.edits_of(B)
kept_keys = kp.dumps(edits["keys"])
old = dict(edits)
old["keys"] = kp.empty()
fix = mp.empty()
fix["rot"]["upperarm_l"] = np.asarray(entry["rot"]["upperarm_l"], float)
old["fix"] = fix
sw.set_edits(B, old)
meanrig.rekey_root(B)
old_turns = [deg(a @ b.T) for a, b in zip(every_frame("B", "upperarm_l", WALK), before)]
gate(max(old_turns) < 3.0, "the control - the same 20 deg put the OLD way, in the cycle's frames: the walker "
     "turns %.2f deg at most (the additive pose washes it out)" % max(old_turns))
back = dict(sw.edits_of(B))
back["fix"] = mp.empty()
back["keys"] = kp.loads(kept_keys)
sw.set_edits(B, back)
meanrig.rekey_root(B)
again = [deg(a @ b.T) for a, b in zip(every_frame("B", "upperarm_l", WALK), before)]
gate(max(abs(t - 20.0) for t in again) < 1.0, "the layer put back: %.2f..%.2f deg again"
     % (min(again), max(again)))

# ---- the rig stood again stands in the new result, and reads nothing ----
print(meanrig.press(B))
gate(meanrig.update() == meanrig.NOTHING_MOVED, "stood again in the corrected result, it reads nothing: the "
     "round trip closes")

# ---- the pelvis raised: on every frame, the planted feet still ----
hips_before = heights("B", "pelvis")
feet_before = places("B", "foot_l")
plug = rig.namespace + ":RootX_M.translateY"
cmds.setAttr(plug, cmds.getAttr(plug) + 3.0)
print(meanrig.update())
risen = [b - a for a, b in zip(hips_before, heights("B", "pelvis"))]
gate(min(risen) > 1.5, "the hips rise on every frame: %+.2f..%+.2f cm (3 asked; the legs' reach pays the rest)"
     % (min(risen), max(risen)))
planted = [f for f in range(len(TIMES)) if max(kp.ground(rw, "l", f)) > 0.9]
slid = max(float(np.linalg.norm(places("B", "foot_l")[f] - feet_before[f])) for f in planted) if planted else 0.0
gate(slid < 1.0, "the planted left foot stays: %.3f cm at most over its %d standing frames" % (slid, len(planted)))

# ---- a foot turned on the rig: its print, every stance ----
# the rig's legs stand in FK (the shipped Manny rig's FKIKBlend is 0), so the foot's own control is FKAnkle;
# its rotateX yaws the foot (measured: 15 deg of control, 15 of yaw)
foot_before = [deg(world("B", "foot_l", f)[:3, :3]) for f in range(len(TIMES))]
plug = rig.namespace + ":FKAnkle_L.rotateX"
cmds.setAttr(plug, cmds.getAttr(plug) + 15.0)
print(meanrig.update())
entry = (sw.edits_of(B)["keys"] or {}).get(kp.CYCLE) or kp.empty_key()
printed = abs(math.degrees(float(entry["print"]["l"]["yaw"])))
free = float(np.linalg.norm(entry["foot"]["l"]["t"]))
gate(printed > 5.0 and free < 0.5, "the foot's turn is its print, not a free move: %.1f deg out, %.3f cm free"
     % (printed, free))
turned_feet = [abs(a - b) for a, b in zip([deg(world("B", "foot_l", f)[:3, :3]) for f in range(len(TIMES))],
                                          foot_before)]
gate(max(turned_feet) > 1.0, "and the walker's own foot took it: up to %.1f deg of world turn" % max(turned_feet))

# ---- the key poses stand on top of it ----
# the mean correction is put on a MIDDLE bone here (the head): a key pose's edit mirrors across the walk's middle
# on the other foot's step, so a correction on an arm would legitimately meet its own mirror
print(meanrig.press(B))
head_before = every_frame("B", "head", WALK)
plug = rig.namespace + ":FKHead_M.rotateZ"
cmds.setAttr(plug, cmds.getAttr(plug) + 10.0)
print(meanrig.update())
head_turns = [deg(a @ b.T) for a, b in zip(every_frame("B", "head", WALK), head_before)]
gate(max(abs(t - 10.0) for t in head_turns) < 1.0, "the head turned 10 deg on the rig: %.2f..%.2f deg on every "
     "frame of the walker" % (min(head_turns), max(head_turns)))
print(keyrig.press(B))
rigs = keyrig.rigs(B)
by_key = dict((keyrig.memo_of(r)["key"], r) for r in rigs)
anim = sw.walker_animation(B)
FR = kp.frames_of(anim.steps, anim.rw.P)
arm_before = every_frame("B", "upperarm_r", WALK)
plug = by_key["contact"].namespace + ":FKShoulder_R.rotateZ"
cmds.setAttr(plug, cmds.getAttr(plug) + 15.0)
print(keyrig.update())
keys = sw.edits_of(B)["keys"]
at_key = deg(local("B", "upperarm_r", FR["contact"], WALK) @ arm_before[FR["contact"]].T)
gate(abs(at_key - 15.0) < 1.5 and not kp.key_empty(keys.get(kp.CYCLE) or kp.empty_key()),
     "a key pose's edit lands on top of the standing mean correction: %.2f deg at the contact (15 asked), the "
     "cycle entry still there" % at_key)
mean_turns = [deg(a @ b.T) for a, b in zip(every_frame("B", "head", WALK), head_before)]
gate(max(abs(t - 10.0) for t in mean_turns) < 1.5, "and the mean correction still holds the head on every "
     "frame under it: %.2f..%.2f deg" % (min(mean_turns), max(mean_turns)))

# ---- the two Resets ----
line = keyrig.reset(B)
print(line)
keys = sw.edits_of(B)["keys"]
gate(not kp.key_empty(keys.get(kp.CYCLE) or kp.empty_key()) and all(kp.key_empty(keys[k]) for k in kp.KEYS
                                                                    if k in keys),
     "Reset key poses drops the four keys and keeps the mean pose correction")
line = meanrig.reset(B)
print(line)
keys = sw.edits_of(B)["keys"]
gate(kp.is_empty(keys) and mp.is_empty(sw.edits_of(B)["fix"]), "Reset rig pose drops the correction whole")
plain_turns = [deg(a @ b.T) for a, b in zip(every_frame("B", "upperarm_l", WALK), before)]
gate(max(plain_turns) < 1.0, "and B plays the plain cycle again: %.2f deg at most" % max(plain_turns))

# ---- nothing of A's, nothing of the library's ----
gate(curves_of("A") == A_BEFORE, "A (not working) is untouched, key for key")
beside = [f for f in os.listdir(TEMP) if f.endswith((".walkkeys.json", ".walkfix.json"))]
gate(digest(WALK_FILE) == FILE_HASH and not beside,
     "the library's walk file is unchanged and nothing was written beside it (%s)" % (beside or "nothing"))

print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": %s" % FAILED) if FAILED else ""))
shutil.rmtree(TEMP, ignore_errors=True)
sys.exit(1 if FAILED else 0)
