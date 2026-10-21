"""Pose Library onto a rig after Tools > 1P Setup, standalone (2026-10-21).

    mayapy verify_poselib_upper_1p.py <UE5 clip .fbx> <animation card .anim> [pose card .pose]

A Manny_Rig takes the clip through the Retarget button, a Long Sword in its right hand, then
Tools > 1P Setup (the animator's tab). Each card is pasted (Replace all) twice:

- **1P upper body off** - the whole card: every member bone stands on its parent as the card's
  does (the chest included: 1P Setup's chest knot `Chest_1P_ctrl` is what the solve writes); the
  camera rides the chest as before; nothing "not posed";
- **1P upper body on** - the root, the pelvis, spine_01/02 and the legs exactly where they stood,
  both 1P layers' curves untouched; the chest against the ROOT as the card's (2026-10-21, the
  torso rule: stabilized whatever the target's lower spine does - it was gated on its parent
  spine_02, the rule the animator found wrong) and everything above it on its parent as the
  card's; camera_root, camera_bone and weapon_r on the chest as the card's;
- one undo takes a press back.

An animation card is gated on EVERY frame of the clip (2026-10-21): a paste that left a placed
bone unkeyed on the frames it already stood right was off only between the every-sixth-frame
samples (`animapply._Target.key` keys every planned plug on every frame since).
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
CARDS = sys.argv[2:]

from maya_scenesetup import catalog, character, equip  # noqa: E402
from maya_tools import firstperson as fp  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_poselib import animapply, animdata, apply as ap, store, upper  # noqa: E402

FAILS = []
COUNT = [0]
TOL_CM, TOL_DEG = 0.1, 0.5


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


def curves_of(layer):
    out = {}
    for plug in cmds.animLayer(layer, query=True, attribute=True) or []:
        for curve in cmds.animLayer(layer, query=True, findCurveForPlug=plug) or []:
            out[plug] = tuple(round(v, 6) for v in
                              cmds.keyframe(curve, query=True, valueChange=True) or ())
    return out


# ------------------------------------------------------------------ the 1P rig, rebuilt
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
first, last = 0, 42
cmds.playbackOptions(min=first, max=last, ast=first, aet=last)
cmds.select(N("Main"), src)
ok, _text = rr.run_retarget()
cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
cmds.playbackOptions(min=first, max=last, ast=first, aet=last)
gate(ok, "clip retargeted onto Manny_Rig")
cmds.currentTime(first)
print("   ", equip.to_hand(N("root"), "R", catalog.by_key("LongSword_02")))
cmds.select(N("FKElbow_R"))
print("   ", fp.setup())
LAYERS = fp.setup_layers(rig.namespace)
SNAP = os.path.join(os.environ.get("TEMP", "."), "verify_poselib_upper_1p.ma").replace("\\", "/")
cmds.file(rename=SNAP)
cmds.file(save=True, type="mayaAscii", force=True)


def reopen():
    """The scene as 1P Setup left it (a time walk between a press and its undo would undo the
    walk instead - trap 222)."""
    cmds.file(SNAP, open=True, force=True)
    cmds.undoInfo(state=True, infinity=True)


LOWER = ["root", "pelvis", "spine_01", "spine_02", "thigh_l", "calf_l", "foot_l", "ball_l",
         "thigh_r", "calf_r", "foot_r", "ball_r"]
ON_CHEST = ["camera_root", "camera_bone", "weapon_r"]


def press(path, on, frame):
    data = store.read(path)
    if on:
        data, _note = upper.restrict(data)
    cmds.currentTime(frame)
    cmds.select(N("FKWrist_R"))
    if store.is_anim(path):
        return data, animapply.apply(data, store.read_frames(path), selection=cmds.ls(sl=True),
                                     options=animdata.Options(mode="replace_all", keys="every"))
    return data, ap.apply(data, selection=cmds.ls(sl=True))


def card_bones(path, data, index):
    if store.is_anim(path):
        return animdata.bones_at(data, store.read_frames(path), index)
    return data["bones"]


def on_parent(bones, leaf, world_of):
    parent = bones[leaf].get("parent")
    return world_of(leaf) * world_of(parent).inverse()


def is_torso(leaf):
    return leaf == "pelvis" or leaf.startswith("spine_")


def torso_anchor(bones, leaf, members):
    """The torso rule (2026-10-21, `posemath.Transfer._torso_anchor`): a posed torso bone turns
    against the nearest torso bone below it the card poses, else against the root."""
    node = bones[leaf].get("parent")
    while node in bones:
        if node == "root" or (is_torso(node) and node in members):
            return node
        node = bones[node].get("parent")
    return "root"


def check(path, on):
    name = os.path.basename(path) + (" ON" if on else " OFF")
    anim = store.is_anim(path)
    # EVERY frame of an animation: a frame the paste left unkeyed was off only between the
    # samples - Combo_3.anim's clavicle 3.1 cm at frame 16, 0.56 at 12 (2026-10-21)
    frames = list(range(first, last + 1)) if anim else [first + 10]
    reopen()
    stood = {}
    for f in frames:
        cmds.currentTime(f)
        stood[f] = dict((b, wm(N(b))) for b in LOWER + ["spine_03"] + ON_CHEST)
    layer_curves = dict((l, curves_of(l)) for l in LAYERS)
    # one undo, right after the press
    data, (ok, text) = press(path, on, frames[0])
    print("    %s: %s" % (name, text[:260]))
    gate(ok and "not posed" not in text, "%s: pasted, nothing «not posed»" % name)
    cmds.undo()
    cmds.currentTime(frames[0])
    back = max(apart(stood[frames[0]][b], wm(N(b)))[0] for b in LOWER + ["spine_03"])
    gate(back < 1e-4, "%s: one undo puts it back (%.6f cm)" % (name, back))
    reopen()
    data, (ok, text) = press(path, on, frames[0])
    members = [m for m in data["members"] if m in data["bones"] and not upper._bare(m) in
               upper.CAMERA and cmds.ls(maya_rigs.node(rig, m))]
    worst_local, worst_chest, worst_low = (0.0, 0.0, ""), (0.0, 0.0, ""), (0.0, 0.0, "")
    for i, f in enumerate(frames):
        cmds.currentTime(f)
        card = card_bones(path, data, f - first if anim else 0)
        cw = lambda leaf, c=card: om.MMatrix(c[leaf]["world"])  # noqa: E731
        tw = lambda leaf: wm(N(leaf))  # noqa: E731
        posed = set(members)
        for leaf in members:
            if leaf in ("root",) or card[leaf].get("parent") not in card:
                continue
            if is_torso(leaf):
                # a torso bone's TURN against its torso anchor, its place on its parent
                anchor = torso_anchor(card, leaf, posed)
                d = (apart(on_parent(card, leaf, tw), on_parent(card, leaf, cw))[0],
                     apart(tw(leaf) * tw(anchor).inverse(), cw(leaf) * cw(anchor).inverse())[1])
            else:
                d = apart(on_parent(card, leaf, tw), on_parent(card, leaf, cw))
            if d[1] > worst_local[1] or d[0] > worst_local[0]:
                worst_local = (max(d[0], worst_local[0]), max(d[1], worst_local[1]), leaf)
        if on:
            for leaf in ON_CHEST:
                d = apart(tw(leaf) * tw("spine_03").inverse(),
                          cw(leaf) * cw("spine_03").inverse())
                if d[0] > worst_chest[0] or d[1] > worst_chest[1]:
                    worst_chest = (max(d[0], worst_chest[0]), max(d[1], worst_chest[1]), leaf)
            for leaf in LOWER:
                d = apart(stood[f][leaf], tw(leaf))
                if d[0] > worst_low[0] or d[1] > worst_low[1]:
                    worst_low = (max(d[0], worst_low[0]), max(d[1], worst_low[1]), leaf)
        else:
            # the camera rides the chest as 1P Setup hung it
            for leaf in ("camera_root",):
                d = apart(tw(leaf) * tw("spine_03").inverse(),
                          stood[f][leaf] * stood[f]["spine_03"].inverse())
                if d[0] > worst_chest[0] or d[1] > worst_chest[1]:
                    worst_chest = (max(d[0], worst_chest[0]), max(d[1], worst_chest[1]), leaf)
    # every card here is a twin of the target: its bone PLACES come too, a pose's and an
    # animation's alike (152124b)
    gate(worst_local[0] < TOL_CM and worst_local[1] < TOL_DEG,
         "%s: every member on its parent as the card's (the torso against its torso anchor): "
         "%.4f cm %.4f deg (%s)" % ((name,) + worst_local))
    if on:
        gate(worst_low[0] < 1e-3 and worst_low[1] < 1e-3,
             "%s: root, pelvis, spine_01/02 and legs kept: %.5f cm %.5f deg (%s)"
             % ((name,) + worst_low))
        changed = [l for l in LAYERS if l.startswith(fp.LOWER) and
                   curves_of(l) != layer_curves[l]]
        gate(not changed, "%s: the lower layer's curves untouched%s" % (name, changed or ""))
        gate(worst_chest[0] < TOL_CM and worst_chest[1] < TOL_DEG,
             "%s: camera and weapon_r on the chest as the card's: %.4f cm %.4f deg (%s)"
             % ((name,) + worst_chest))
    else:
        gate(worst_chest[0] < 1e-3 and worst_chest[1] < 1e-3,
             "%s: the camera still rides the chest: %.5f cm %.5f deg" % ((name,) +
                                                                          worst_chest[:2]))


for card_path in CARDS:
    for on in (False, True):
        check(card_path, on)

print("\n%d of %d gates failed" % (len(FAILS), COUNT[0]))
