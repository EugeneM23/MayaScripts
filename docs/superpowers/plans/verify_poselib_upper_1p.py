"""Pose Library > 1P upper body, standalone (2026-10-21).

    mayapy verify_poselib_upper_1p.py <UE5 clip .fbx> <animation card .anim> [pose card .pose]

A Manny_Rig takes the clip through the Retarget button, then Tools > 1P Setup (the animator's tab
2), a Long Sword in its right hand; the card (the animator's tab 1, saved as an animation card) is
pasted with Replace all:

- with 1P upper body off (the control): the lower body moves - what the animator met;
- with it on: the pelvis, the legs, the root and spine_01..03 stay where they stood (0.0); both
  1P layers' curves untouched; every upper bone, the camera and weapon_r stand relative to
  spine_03 as the card's do relative to its spine_03; one undo;
- the pose card the same at the current frame.
"""

import math
import os
import sys

import maya.standalone
maya.standalone.initialize()

import maya.api.OpenMaya as om  # noqa: E402
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

REPO = os.environ.get("PLUGIN", "C:/!!!Work/MayaScripts/SkeldarAnim")
sys.path.insert(0, REPO)
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
CLIP = sys.argv[1].replace("\\", "/")
CARD = sys.argv[2]
POSE = sys.argv[3] if len(sys.argv) > 3 else None

from maya_scenesetup import catalog, character, equip  # noqa: E402
from maya_tools import firstperson as fp  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_poselib import animapply, animdata, apply as ap, store, upper  # noqa: E402

FAILS = []
COUNT = [0]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    if not ok:
        FAILS.append(msg)


def wm(n):
    return om.MMatrix(cmds.xform(n, query=True, matrix=True, worldSpace=True))


def apart(a, b):
    d = max(abs(a[12 + i] - b[12 + i]) for i in range(3))
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    r = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    dot = min(1.0, abs(q.x * r.x + q.y * r.y + q.z * r.z + q.w * r.w))
    return d, math.degrees(2 * math.acos(dot))


def track(nodes, frames):
    out = {}
    for f in frames:
        cmds.currentTime(f)
        out[f] = dict((n, wm(n)) for n in nodes)
    return out


def worst(a, b, nodes):
    cm = deg = 0.0
    for f in a:
        for n in nodes:
            d, g = apart(a[f][n], b[f][n])
            cm, deg = max(cm, d), max(deg, g)
    return cm, deg


def curves_of(layer):
    out = {}
    for plug in cmds.animLayer(layer, query=True, attribute=True) or []:
        c = cmds.animLayer(layer, query=True, findCurveForPlug=plug) or []
        for curve in c:
            out[plug] = tuple(cmds.keyframe(curve, query=True, valueChange=True) or ())
    return out


# ------------------------------------------------------------------ tab 2, rebuilt
cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
character.add_character(catalog.character_by_key("Manny_Rig"))
rig = maya_rigs.rigs()[0]
N = lambda leaf: cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]  # noqa: E731
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
before = set(cmds.ls(type="joint", long=True))
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
kt = cmds.keyframe(new, query=True, timeChange=True)
header = store.read(CARD)
frames_data = store.read_frames(CARD)
first, last = 0, int(header.get("end") or 42)
cmds.playbackOptions(min=first, max=last, ast=first, aet=last)
cmds.select(N("Main"), src)
ok, text = rr.run_retarget()
cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
cmds.playbackOptions(min=first, max=last, ast=first, aet=last)
gate(ok, "clip retargeted onto Manny_Rig")
cmds.currentTime(first)
sword = catalog.by_key("LongSword_02") or catalog.WEAPONS[0]
print("   ", equip.to_hand(N("root"), "R", sword))
cmds.select(N("FKElbow_R"))
print("   ", fp.setup())
LOWER, UPPER_L = fp.setup_layers(rig.namespace)[0], None
for layer in fp.setup_layers(rig.namespace):
    if layer.startswith(fp.LOWER):
        LOWER = layer
    if layer.startswith(fp.UPPER):
        UPPER_L = layer
lower_curves = curves_of(LOWER)
upper_curves = curves_of(UPPER_L)

STAY = ["root", "pelvis", "spine_01", "spine_02", "spine_03", "thigh_l", "calf_l", "foot_l",
        "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r"]
UP = ["spine_05", "neck_01", "head", "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
      "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r", "index_02_l", "camera_root",
      "camera_bone", "weapon_r"]
frames = list(range(first, last + 1, 3))
nodes = [N(b) for b in STAY + UP]
stood = track(nodes, frames)


def card_rel(frame_index, leaf):
    bones = animdata.bones_at(header, frames_data, frame_index)
    return om.MMatrix(bones[leaf]["world"]) * om.MMatrix(bones["spine_03"]["world"]).inverse()


def paste(data):
    cmds.currentTime(first)
    cmds.select(N("FKWrist_R"))
    return animapply.apply(data, frames_data, selection=cmds.ls(selection=True),
                           options=animdata.Options(mode="replace_all", keys="every"))


SNAP = os.path.join(os.environ.get("TEMP", "."), "verify_poselib_upper_1p.ma").replace("\\", "/")
cmds.file(rename=SNAP)
cmds.file(save=True, type="mayaAscii", force=True)


def reopen():
    """The scene as 1P Setup left it (a time walk between a press and its undo would undo the
    walk instead - trap 222)."""
    cmds.file(SNAP, open=True, force=True)
    cmds.undoInfo(state=True, infinity=True)


# ------------------------------------------------------------------ the control: off
ok, text = paste(header)
print("    off:", text[:200])
after = track(nodes, frames)
cm, _deg = worst(stood, after, [N(b) for b in ("foot_l", "foot_r", "calf_l")])
gate(cm > 5.0, "off (the control): the feet move %.2f cm - what the animator met" % cm)

# ------------------------------------------------------------------ on
reopen()
cut, note = upper.restrict(header)
gate(cut is not None and "thigh_l" not in cut["members"] and "spine_03" not in cut["members"]
     and "hand_r" in cut["members"] and "camera_root" in cut["members"], "restrict: %s" % note)
ok, text = paste(cut)
cmds.undo()
gate(worst(stood, track(nodes, frames), nodes)[0] < 1e-4, "one undo puts it all back")
reopen()
lower_curves = curves_of(LOWER)        # as the file reads back (an .ma rounds its values)
upper_curves = curves_of(UPPER_L)
ok, text = paste(cut)
print("    on:", text[:300])
gate(ok, "pasted with 1P upper body")
after = track(nodes, frames)
cm, deg = worst(stood, after, [N(b) for b in STAY])
gate(cm < 1e-3 and deg < 1e-3, "the pelvis, legs, root and spine_01..03 kept: %.5f cm %.5f deg"
     % (cm, deg))
for layer, was in ((LOWER, lower_curves), (UPPER_L, upper_curves)):
    now_c = curves_of(layer)
    changed = sorted(p for p in set(was) | set(now_c) if was.get(p) != now_c.get(p))
    gate(not changed, "%s's curves untouched%s" % (layer, (" - changed: %s" % changed[:6])
                                                   if changed else ""))
fails = []
for leaf in UP:
    w = (0.0, 0.0)
    for f in frames:
        i = f - first
        rel = after[f][N(leaf)] * after[f][N("spine_03")].inverse()
        d = apart(rel, card_rel(i, leaf))
        w = (max(w[0], d[0]), max(w[1], d[1]))
    print("    %-12s on the chest as the card's: %.4f cm %.4f deg" % (leaf, w[0], w[1]))
    if w[0] > 0.1 or w[1] > 0.5:
        fails.append(leaf)
gate(not fails, "every upper bone, the camera and weapon_r on spine_03 as the card's%s"
     % (" - off: %s" % fails if fails else ""))

# ------------------------------------------------------------------ a pose card
if POSE:
    reopen()
    data = store.read(POSE)
    cut, note = upper.restrict(data)
    cmds.currentTime(first + 10)
    here = dict((n, wm(n)) for n in nodes)
    cmds.select(N("FKWrist_R"))
    ok, text = ap.apply(cut, selection=cmds.ls(selection=True))
    print("    pose:", text[:200])
    now = dict((n, wm(n)) for n in nodes)
    cm = max(apart(here[N(b)], now[N(b)])[0] for b in STAY)
    bones = data["bones"]
    chest = om.MMatrix(bones["spine_03"]["world"]).inverse()
    rel = [apart(now[N(l)] * now[N("spine_03")].inverse(), om.MMatrix(bones[l]["world"]) * chest)
           for l in ("hand_r", "hand_l", "head", "camera_bone", "weapon_r") if l in bones]
    off_cm, off = max(r[0] for r in rel), max(r[1] for r in rel)
    gate(ok and cm < 1e-3 and off < 0.5 and off_cm < 0.1,
         "pose card: the lower body kept %.5f cm; hands, head, camera, weapon_r on the chest "
         "%.4f cm %.4f deg" % (cm, off_cm, off))

print("\n%d of %d gates failed" % (len(FAILS), COUNT[0]))
