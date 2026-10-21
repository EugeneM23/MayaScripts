"""Pose Library onto a rig in 3P and in 1P - bones first, the upper body stabilized (2026-10-21).

    mayapy verify_poselib_1p_transfer.py <source UE5 clip .fbx> <target UE5 clip .fbx>

In a GUI Maya the same file runs over the command port (it opens new scenes - only in a Maya
given for it): set `ARGS = [source, target]` in the globals it is exec'd with.

A: a Manny_Rig takes the source clip (the Retarget button), then Tools > 1P Setup - its chest
stabilized (Upper muted). Off A three cards are saved as the window saves them: the whole body
(Main selected), the upper body as an animator selects it in 1P (every visible upper control,
Chest_1P_ctrl, Camera_ctrl), and Chest_1P_ctrl alone. B: a second Manny_Rig takes the target
clip, a combo whose torso twists - kept in 3P, and set up for 1P. Gates:

- the saves: Chest_1P_ctrl is the rig's (a character card of spine_03, no object), the upper
  selection names the chest, the arms, the head and the camera bones, nothing below the chest;
- every card onto B in 3P and in 1P: an upper-body card (the whole card cut by 1P upper body, the
  upper selection with the option OFF, an upper pose) keeps the card's chest against the ROOT on
  every frame - stabilized - with everything above on its parent as the card's, the camera on the
  chest, the lower body untouched; the whole card OFF on the card relative to the root;
- B in 3P and B in 1P land the same bones; Selected only with FKSpine3_M selected in 1P keys the
  chest (through Chest_1P_ctrl); one undo puts a press back.
"""

import math
import os
import sys

import maya.cmds as cmds  # noqa: E402

if not hasattr(cmds, "file"):                     # mayapy: no Maya yet
    import maya.standalone
    maya.standalone.initialize()

import maya.api.OpenMaya as om  # noqa: E402
import maya.mel as mel  # noqa: E402

REPO = os.environ.get("PLUGIN", "C:/!!!Work/MayaScripts/SkeldarAnim")
if REPO not in sys.path:
    sys.path.insert(0, REPO)
for _p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_p, quiet=True)
    except Exception:
        pass
_ARGS = globals().get("ARGS") or sys.argv[1:3]
SRC_CLIP, TGT_CLIP = (a.replace("\\", "/") for a in _ARGS)
TMP = os.path.join(os.environ.get("TEMP", "."), "verify_poselib_1p_transfer").replace("\\", "/")
if not os.path.isdir(TMP):
    os.makedirs(TMP)

from maya_scenesetup import catalog, character  # noqa: E402
from maya_tools import firstperson as fp  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_poselib import animapply, animcapture, animdata, apply as ap, capture, upper  # noqa

FAILS, COUNT = [], [0]
TOL_DEG, TOL_CM = 0.01, 0.01
FIRST, LAST = 0, 40
UPPER_LEAVES = ["spine_03", "spine_04", "spine_05", "neck_01", "head", "clavicle_r",
                "upperarm_r", "lowerarm_r", "hand_r", "clavicle_l", "upperarm_l", "lowerarm_l",
                "hand_l", "camera_root"]
LOWER_LEAVES = ["root", "pelvis", "spine_01", "spine_02", "thigh_l", "calf_l", "foot_l",
                "thigh_r", "calf_r", "foot_r"]
ON_CHEST = ["spine_04", "head", "hand_r", "hand_l", "camera_root"]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    if not ok:
        FAILS.append(msg)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def ang(a, b):
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    r = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(min(1.0, abs(q.x * r.x + q.y * r.y + q.z * r.z + q.w * r.w))))


def dist(a, b):
    return math.sqrt(sum((a[12 + i] - b[12 + i]) ** 2 for i in range(3)))


def rel(w, leaf, anchor):
    return w[leaf] * w[anchor].inverse()


def rigs_ab():
    found = maya_rigs.rigs()
    a = [r for r in found if r.namespace == "Manny_Rig"][0]
    b = [r for r in found if r.namespace != "Manny_Rig"][0]
    return a, b


def node(rig, leaf):
    return cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]


def bone(rig, leaf):
    joints = [rig.skeleton_root] + (cmds.listRelatives(rig.skeleton_root, allDescendents=True,
                                                       type="joint", fullPath=True) or [])
    return [j for j in joints if j.split("|")[-1].split(":")[-1] == leaf][0]


def take(rig, clip):
    cmds.namespace(add="clip")
    cmds.namespace(set=":clip")
    mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
    before = set(cmds.ls(type="joint", long=True))
    mel.eval('FBXImport -f "%s";' % clip)
    cmds.namespace(set=":")
    new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
              key=lambda j: j.count("|"))
    keys = cmds.keyframe(src, query=True, timeChange=True) or [LAST]
    cmds.playbackOptions(min=FIRST, max=LAST, ast=FIRST, aet=LAST)
    cmds.select(node(rig, "Main"), src)
    ok, _text = rr.run_retarget()
    cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
    cmds.playbackOptions(min=FIRST, max=LAST, ast=FIRST, aet=LAST)
    return ok, keys


def setup_1p(rig):
    cmds.currentTime(FIRST)
    cmds.select(node(rig, "FKElbow_R"))
    return fp.setup()


def frames_of(rig, leaves, frames):
    out = {}
    for f in frames:
        cmds.currentTime(f)
        out[f] = dict((leaf, wm(bone(rig, leaf))) for leaf in leaves)
    return out


def card_at(header, frames, i):
    b = animdata.bones_at(header, frames, i)
    return dict((leaf, om.MMatrix(b[leaf]["world"])) for leaf in b)


def reopen(path):
    """The snapshot opened - in a GUI Maya past Scene Tabs' Open check, which would send a scene
    opened beside a non-empty one into a tab (`scope.decided`, the plugin's own opens' road)."""
    try:
        from maya_scenetabs import scope
        guard = scope.decided()
    except Exception:
        import contextlib
        guard = contextlib.nullcontext()
    with guard:
        cmds.file(path, open=True, force=True)
    cmds.undoInfo(state=True, infinity=True)


# ---------------------------------------------------------------- the scene
cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
character.add_character(catalog.character_by_key("Manny_Rig"))
A = maya_rigs.rigs()[0]
ok, keys = take(A, SRC_CLIP)
LAST = min(LAST, int(max(keys)))
cmds.playbackOptions(min=FIRST, max=LAST, ast=FIRST, aet=LAST)
FRAMES = list(range(FIRST, LAST + 1))
gate(ok, "the source clip retargeted onto Manny_Rig (%d-%d)" % (FIRST, LAST))
print("   ", setup_1p(A)[:160])
A, _ = rigs_ab() if len(maya_rigs.rigs()) > 1 else (maya_rigs.rigs()[0], None)
chest_a = fp.chest_of(A)
camera_a = fp.camera_control(bone(A, "camera_root"))

# ---------------------------------------------------------------- the cards, as the window saves
cmds.select(node(A, "Main"))
FULL, FULL_FRAMES, _n = animcapture.build_animation(selection=cmds.ls(sl=True), start=FIRST,
                                                    end=LAST)
# what an animator selects in 1P: every control drawn in the 1P upper display layer (the lower
# one is hidden) - a marquee over the body
upper_layer = [layer for layer in fp.display_layers_of(A.namespace)
               if layer.endswith(fp.UPPER_CONTROLS)][0]
UP_SEL = []
for shape in cmds.editDisplayLayerMembers(upper_layer, query=True, fullNames=True) or []:
    for parent in cmds.listRelatives(shape, parent=True, fullPath=True) or []:
        if parent not in UP_SEL:
            UP_SEL.append(parent)
gate(chest_a in UP_SEL and camera_a in UP_SEL,
     "the 1P upper display layer draws %d controls, Chest_1P_ctrl and Camera_ctrl among them"
     % len(UP_SEL))
SEL, SEL_FRAMES, sel_note = animcapture.build_animation(selection=UP_SEL, start=FIRST, end=LAST)
cmds.currentTime(FIRST + 10)
POSE, _why = capture.build_pose(selection=UP_SEL)
ALONE, ALONE_FRAMES, alone_note = animcapture.build_animation(selection=[chest_a], start=FIRST,
                                                              end=LAST)
print("    upper selection:", sel_note[:200])
print("    chest alone:", alone_note[:200])

card = [card_at(FULL, FULL_FRAMES, i) for i in range(len(FRAMES))]
still = max(ang(rel(c, "spine_03", "root"), rel(card[0], "spine_03", "root")) for c in card)
twist = max(ang(rel(c, "spine_03", "spine_02"), rel(card[0], "spine_03", "spine_02"))
            for c in card)
gate(still < TOL_DEG and twist > 10.0,
     "the card's chest stands still against its root (%.4f deg) while its spine_02 turns under "
     "it (%.1f deg)" % (still, twist))
gate(ALONE and ALONE.get("kind") == "character" and "spine_03" in ALONE["members"] and
     not ALONE.get("objects"),
     "Chest_1P_ctrl alone saves a character card of spine_03, no object (%s, members %s)"
     % (ALONE and ALONE.get("kind"), ALONE and ALONE.get("members")))
need = set(["spine_03", "spine_04", "spine_05", "upperarm_r", "upperarm_l", "hand_r", "head",
            "neck_01", "camera_root", "camera_bone"])
low = set(["pelvis", "spine_01", "spine_02", "thigh_l", "foot_r"])
gate(SEL.get("kind") == "character" and need <= set(SEL["members"]) and
     not (low & set(SEL["members"])) and not SEL.get("objects"),
     "the 1P upper selection names the chest, arms, head and camera, nothing below the chest, "
     "no object (missing %s, below %s, objects %s)" % (
         sorted(need - set(SEL["members"])), sorted(low & set(SEL["members"])),
         [o.get("name") for o in SEL.get("objects") or []]))
gate(POSE and "spine_03" in POSE["members"], "the upper pose card holds the chest")

# ---------------------------------------------------------------- B, in 3P and in 1P
character.add_character(catalog.character_by_key("Manny_Rig"))
A, B = rigs_ab()
ok, _keys = take(B, TGT_CLIP)
gate(ok, "the target clip retargeted onto %s" % B.namespace)
SNAP_3P = TMP + "/b_3p.ma"
cmds.file(rename=SNAP_3P)
cmds.file(save=True, type="mayaAscii", force=True)
A, B = rigs_ab()
print("   ", setup_1p(B)[:160])
SNAP_1P = TMP + "/b_1p.ma"
cmds.file(rename=SNAP_1P)
cmds.file(save=True, type="mayaAscii", force=True)


def press(data, frames, on, frame=FIRST, only=False, select=None):
    if on:
        data, _note = upper.restrict(data)
    _a, b = rigs_ab()
    cmds.currentTime(frame)
    cmds.select(select or node(b, "FKWrist_R"))
    if frames is None:
        return ap.apply(data, selection=cmds.ls(sl=True), only=only)
    return animapply.apply(data, frames, selection=cmds.ls(sl=True), only=bool(only),
                           options=animdata.Options(mode="replace_all", keys="every"))


def judge(name, cards, before, after, frames, upper_card=True):
    """The chest against the root as the card's (an upper-body card) or every UPPER bone against
    the root (a whole card); above the chest on its parent; the lower body as it stood."""
    chest = above = lower = whole = 0.0
    above_cm = 0.0
    for i, f in enumerate(frames):
        c, w = cards[i], after[f]
        chest = max(chest, ang(rel(w, "spine_03", "root"), rel(c, "spine_03", "root")))
        for leaf in ON_CHEST:
            above = max(above, ang(rel(w, leaf, "spine_03"), rel(c, leaf, "spine_03")))
            above_cm = max(above_cm, dist(rel(w, leaf, "spine_03"), rel(c, leaf, "spine_03")))
        if upper_card:
            lower = max([lower] + [max(dist(before[f][leaf], w[leaf]),
                                       ang(before[f][leaf], w[leaf])) for leaf in LOWER_LEAVES])
        else:
            whole = max([whole] + [max(dist(rel(w, leaf, "root"), rel(c, leaf, "root")),
                                       ang(rel(w, leaf, "root"), rel(c, leaf, "root")))
                                   for leaf in UPPER_LEAVES + LOWER_LEAVES[1:]])
    gate(chest < TOL_DEG, "%s: the chest against the root as the card's: %.5f deg" % (name, chest))
    gate(above < TOL_DEG and above_cm < TOL_CM,
         "%s: spine_04, head, hands, camera on the chest as the card's: %.5f cm %.5f deg"
         % (name, above_cm, above))
    if upper_card:
        gate(lower < 1e-3, "%s: the lower body as it stood: %.6f" % (name, lower))
    else:
        gate(whole < TOL_CM, "%s: every bone on the card against the root: %.5f" % (name, whole))


results = {}
for mode, snap in (("3P", SNAP_3P), ("1P", SNAP_1P)):
    for key, data, frames, on, upper_card in (
            ("whole cut ON", FULL, FULL_FRAMES, True, True),
            ("upper selection OFF", SEL, SEL_FRAMES, False, True),
            ("whole OFF", FULL, FULL_FRAMES, False, False)):
        reopen(snap)
        _a, b = rigs_ab()
        before = frames_of(b, UPPER_LEAVES + LOWER_LEAVES, FRAMES)
        ok, text = press(data, frames, on)
        name = "B %s, %s" % (mode, key)
        print("    %s: %s" % (name, text[:220]))
        gate(ok and "not posed" not in text, "%s: pasted, nothing «not posed»" % name)
        after = frames_of(b, UPPER_LEAVES + LOWER_LEAVES, FRAMES)
        cards = [card_at(data, frames, i) for i in range(len(FRAMES))]
        judge(name, cards, before, after, FRAMES, upper_card)
        results[(mode, key)] = after
    # an upper pose card, OFF
    reopen(snap)
    _a, b = rigs_ab()
    at = FIRST + 10
    before = frames_of(b, UPPER_LEAVES + LOWER_LEAVES, [at])
    ok, text = press(POSE, None, False, frame=at)
    print("    B %s, upper pose: %s" % (mode, text[:200]))
    after = frames_of(b, UPPER_LEAVES + LOWER_LEAVES, [at])
    pose_card = dict((leaf, om.MMatrix(POSE["bones"][leaf]["world"])) for leaf in POSE["bones"])
    judge("B %s, upper pose" % mode, [pose_card], before, after, [at])
    results[(mode, "pose")] = after

for key in ("whole cut ON", "upper selection OFF", "whole OFF", "pose"):
    worst = 0.0
    for f in results[("3P", key)]:
        for leaf in UPPER_LEAVES:
            worst = max(worst, dist(results[("3P", key)][f][leaf], results[("1P", key)][f][leaf]),
                        ang(results[("3P", key)][f][leaf], results[("1P", key)][f][leaf]))
    gate(worst < TOL_CM, "B in 3P and in 1P land the same bones, %s: %.5f" % (key, worst))

# Selected only in 1P: FKSpine3_M selected - the chest keyed through Chest_1P_ctrl
reopen(SNAP_1P)
_a, b = rigs_ab()
before = frames_of(b, UPPER_LEAVES + LOWER_LEAVES, FRAMES)
ok, text = press(FULL, FULL_FRAMES, True, only=True, select=node(b, "FKSpine3_M"))
print("    Selected only FKSpine3_M:", text[:200])
after = frames_of(b, UPPER_LEAVES + LOWER_LEAVES, FRAMES)
chest = max(ang(rel(after[f], "spine_03", "root"), rel(card[i], "spine_03", "root"))
            for i, f in enumerate(FRAMES))
gate(ok and chest < TOL_DEG,
     "Selected only with FKSpine3_M in 1P keys the chest (through Chest_1P_ctrl): %.5f deg"
     % chest)

# one undo - standalone only: a script sent over a GUI Maya's port is one command, and an undo
# inside it undoes whatever chunk came last (CLAUDE.md, bridge-script hygiene)
if cmds.about(batch=True):
    reopen(SNAP_1P)
    _a, b = rigs_ab()
    stood = frames_of(b, UPPER_LEAVES + LOWER_LEAVES, [FIRST])
    press(FULL, FULL_FRAMES, True)
    cmds.undo()
    back = frames_of(b, UPPER_LEAVES + LOWER_LEAVES, [FIRST])
    worst = max(dist(stood[FIRST][leaf], back[FIRST][leaf])
                for leaf in UPPER_LEAVES + LOWER_LEAVES)
    gate(worst < 1e-4, "one undo puts the paste back: %.6f cm" % worst)
else:
    print("     (one undo: standalone only, skipped in a GUI Maya)")

print("\n%d of %d gates failed" % (len(FAILS), COUNT[0]))
