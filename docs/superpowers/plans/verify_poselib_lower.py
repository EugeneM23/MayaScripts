"""Pose Library: 1P lower body, standalone (2026-10-22).

    mayapy verify_poselib_lower.py <walk clip .fbx> <other clip .fbx>

Rig A (Manny_Rig) takes the WALK through the Retarget button and gives a pose card and an
animation card of its whole body. Rig B (a second Manny_Rig) carries the OTHER clip. Each card
is pressed onto B with 1P lower body on (`lower.restrict`):

- **3P**: the pelvis, spine_01/02 and the legs on their parents as the card's (the torso against
  its torso anchor), an animation's root on the card's travel; the CHEST kept stable - its turn
  against B's root as it stood before the press, its place on its old local on the NEW spine_02;
  the spine above it, the neck, the clavicles and the FK arms on the chest as before; one undo;
- **1P** (B after Tools > 1P Setup): the same, the camera on the chest as before, the upper
  layer's curves untouched;
- **a bare Manny UE5 skeleton**: the pose card, the same rules.

An animation is gated on EVERY pasted frame (Replace, keys on every frame).
"""

import math
import os
import sys
import tempfile

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
WALK = sys.argv[1].replace("\\", "/")
OTHER = sys.argv[2].replace("\\", "/")

from maya_scenesetup import catalog, character  # noqa: E402
from maya_tools import firstperson as fp  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_poselib import animapply, animcapture, animdata, apply as ap, capture, lower  # noqa: E402

FAILS = []
COUNT = [0]
TOL_CM, TOL_DEG = 0.1, 0.5
FIRST, LAST = 0, 24

LOWER_BONES = ["pelvis", "spine_01", "spine_02", "thigh_l", "calf_l", "foot_l", "ball_l",
               "thigh_r", "calf_r", "foot_r", "ball_r"]
ON_CHEST = ["spine_04", "spine_05", "neck_01", "clavicle_l", "clavicle_r", "upperarm_l",
            "upperarm_r", "lowerarm_l", "lowerarm_r", "hand_l", "hand_r"]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(msg)


def wm(n):
    return om.MMatrix(cmds.xform(n, query=True, matrix=True, worldSpace=True))


def rot(m):
    return om.MTransformationMatrix(om.MMatrix(m)).rotation(asQuaternion=True).asMatrix()


def pos(m):
    m = om.MMatrix(m)
    return om.MVector(m[12], m[13], m[14])


def apart(a, b):
    d = (pos(a) - pos(b)).length()
    q = om.MTransformationMatrix(om.MMatrix(a)).rotation(asQuaternion=True)
    r = om.MTransformationMatrix(om.MMatrix(b)).rotation(asQuaternion=True)
    dot = min(1.0, abs(q.x * r.x + q.y * r.y + q.z * r.z + q.w * r.w))
    return d, math.degrees(2 * math.acos(dot))


def worse(old, d, leaf):
    """The worst (cm, deg, where) so far: each the largest seen, `where` the bone furthest past
    the tolerances."""
    score = max(d[0] / TOL_CM, d[1] / TOL_DEG)
    was = max(old[0] / TOL_CM, old[1] / TOL_DEG) if old[2] else -1.0
    return (max(old[0], d[0]), max(old[1], d[1]), leaf if score > was else old[2])


def curves_of(layer):
    out = {}
    for plug in cmds.animLayer(layer, query=True, attribute=True) or []:
        for curve in cmds.animLayer(layer, query=True, findCurveForPlug=plug) or []:
            out[plug] = tuple(round(v, 6) for v in
                              cmds.keyframe(curve, query=True, valueChange=True) or ())
    return out


def retarget(rig, clip, ns):
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
    before = set(cmds.ls(type="joint", long=True))
    mel.eval('FBXImport -f "%s";' % clip)
    cmds.namespace(set=":")
    new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
              key=lambda j: j.count("|"))
    cmds.playbackOptions(min=FIRST, max=LAST, ast=FIRST, aet=LAST)
    ok, text = rr.run_retarget(source_root=src, rig=rig)
    cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
    cmds.playbackOptions(min=FIRST, max=LAST, ast=FIRST, aet=LAST)
    return ok, text


# ------------------------------------------------------------------ the scene
cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
character.add_character(catalog.character_by_key("Manny_Rig"))
character.add_character(catalog.character_by_key("Manny_Rig"))
rigs = sorted(maya_rigs.rigs(), key=lambda r: r.namespace)
A, B = rigs[0], rigs[1]
cmds.xform(maya_rigs.node(B, "Main"), translation=(150, 0, 0), worldSpace=True)
ok, text = retarget(A, WALK, "walk")
gate(ok, "the walk retargeted onto %s" % A.namespace)
ok, text = retarget(B, OTHER, "other")
gate(ok, "the other clip retargeted onto %s" % B.namespace)

cmds.currentTime(FIRST + 7)
pose, note = capture.build_pose([maya_rigs.node(A, "Main")], frame=FIRST + 7)
print("    pose card:", note)
header, frames, note = animcapture.build_animation([maya_rigs.node(A, "Main")], start=FIRST,
                                                   end=LAST)
print("    animation card:", note)
gate(pose is not None and header is not None, "both cards of %s built" % A.namespace)
POSE, POSE_NOTE = lower.restrict(pose)
ANIM, ANIM_NOTE = lower.restrict(header)
print("   ", POSE_NOTE)
gate(POSE is not None and "spine_03" not in POSE["members"] and POSE["keep"] == ["spine_03"],
     "the pose card cut to its lower body, the chest kept: %d members" % len(POSE["members"]))

SNAP = os.path.join(tempfile.gettempdir(), "verify_poselib_lower_%d.ma" % os.getpid()) \
    .replace("\\", "/")
cmds.file(rename=SNAP)
cmds.file(save=True, type="mayaAscii", force=True)


def reopen():
    cmds.file(SNAP, open=True, force=True)
    cmds.undoInfo(state=True, infinity=True)


def is_torso(leaf):
    return leaf == "pelvis" or leaf.startswith("spine_")


def torso_anchor(bones, leaf, members):
    node = bones[leaf].get("parent")
    while node in bones:
        if node == "root" or (is_torso(node) and node in members):
            return node
        node = bones[node].get("parent")
    return "root"


def card_bones(anim, index):
    if anim:
        return animdata.bones_at(ANIM, frames, index)
    return POSE["bones"]


def check(label, node_of, anim, before_press=None, layers=None, camera=None):
    """`node_of(leaf)` the target's game bone; `before_press()` runs on the reopened scene
    before anything is read (1P Setup); `camera` - what camera_root rides: "root" (3P: the
    camera control under Main), "chest" (1P: under Chest_1P_ctrl), None (no camera)."""
    data = ANIM if anim else POSE
    times = list(range(FIRST, LAST + 1)) if anim else [FIRST + 12]
    reopen()
    if before_press:
        before_press()
    probe = LOWER_BONES + ["root", "spine_03", "head"] + ON_CHEST + \
        (["camera_root"] if camera else [])
    stood = {}
    for t in times:
        cmds.currentTime(t)
        stood[t] = dict((b, wm(node_of(b))) for b in probe)
    kept_layers = dict((l, curves_of(l)) for l in (layers or ()))
    snap2 = SNAP.replace(".ma", "_b.ma")
    cmds.file(rename=snap2)
    cmds.file(save=True, type="mayaAscii", force=True)
    sel = [node_of("pelvis")]

    def press():
        cmds.currentTime(times[0])
        cmds.select(sel)
        if anim:
            return animapply.apply(data, frames, selection=cmds.ls(sl=True),
                                   options=animdata.Options(mode="replace", keys="every"))
        return ap.apply(data, selection=cmds.ls(sl=True))

    ok, text = press()
    print("    %s: %s" % (label, text[:300]))
    gate(ok and "not posed" not in text, "%s: pressed, nothing «not posed»" % label)
    cmds.undo()
    cmds.currentTime(times[0])
    back = max(apart(stood[times[0]][b], wm(node_of(b)))[0] for b in probe)
    gate(back < 1e-3, "%s: one undo puts it back (%.6f cm)" % (label, back))
    cmds.file(snap2, open=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    ok, text = press()
    members = set(m for m in data["members"] if m in data["bones"])
    low, chest, ride, head, travel, cam = ((0.0, 0.0, ""),) * 6
    for i, t in enumerate(times):
        cmds.currentTime(t)
        card = card_bones(anim, t - FIRST if anim else 0)
        cw = lambda leaf, c=card: om.MMatrix(c[leaf]["world"])  # noqa: E731
        tw = lambda leaf: wm(node_of(leaf))  # noqa: E731
        old = stood[t]
        for leaf in LOWER_BONES:
            if is_torso(leaf):
                anchor = torso_anchor(card, leaf, members)
                d = (apart(tw(leaf) * tw(card[leaf]["parent"]).inverse(),
                           cw(leaf) * cw(card[leaf]["parent"]).inverse())[0],
                     apart(tw(leaf) * tw(anchor).inverse(), cw(leaf) * cw(anchor).inverse())[1])
            else:
                parent = card[leaf]["parent"]
                d = apart(tw(leaf) * tw(parent).inverse(), cw(leaf) * cw(parent).inverse())
            low = worse(low, d, "%s@%s" % (leaf, t))
        if anim:
            card0 = card_bones(True, 0)
            want = (cw("root") * om.MMatrix(card0["root"]["world"]).inverse()) * \
                stood[times[0]]["root"]
            travel = worse(travel, apart(tw("root"), want), "root@%s" % t)
        # the chest: its turn against the root as it stood, its place on the new spine_02
        turn = rot(rot(old["spine_03"]) * rot(old["root"]).inverse() * rot(tw("root")))
        local = pos(old["spine_03"] * old["spine_02"].inverse())
        place = om.MVector(om.MPoint(local) * tw("spine_02"))
        got = tw("spine_03")
        chest = worse(chest, ((pos(got) - place).length(),
                              apart(rot(got), turn)[1]), "spine_03@%s" % t)
        for leaf in ON_CHEST:
            d = apart(tw(leaf) * tw("spine_03").inverse(), old[leaf] * old["spine_03"].inverse())
            ride = worse(ride, d, "%s@%s" % (leaf, t))
        if camera:
            on = "spine_03" if camera == "chest" else "root"
            d = apart(tw("camera_root") * tw(on).inverse(),
                      old["camera_root"] * old[on].inverse())
            cam = worse(cam, d, "camera_root@%s" % t)
        on_chest = apart(tw("head") * tw("spine_03").inverse(),
                         old["head"] * old["spine_03"].inverse())
        in_world = apart(rot(tw("head")) * rot(tw("root")).inverse(),
                         rot(old["head"]) * rot(old["root"]).inverse())
        head = worse(head, min(on_chest, in_world, key=lambda d: d[1]), "head@%s" % t)
    gate(low[0] < TOL_CM and low[1] < TOL_DEG,
         "%s: pelvis, spine_01/02 and legs as the card's: %.4f cm %.4f deg (%s)"
         % ((label,) + low))
    if anim:
        gate(travel[0] < TOL_CM and travel[1] < TOL_DEG,
             "%s: the root on the card's travel: %.4f cm %.4f deg (%s)" % ((label,) + travel))
    gate(chest[0] < TOL_CM and chest[1] < TOL_DEG,
         "%s: the chest kept - its turn against the root, on the new spine: %.4f cm %.4f deg "
         "(%s)" % ((label,) + chest))
    gate(ride[0] < TOL_CM and ride[1] < TOL_DEG,
         "%s: spine_04/05, neck, arms on the chest as before: %.4f cm %.4f deg (%s)"
         % ((label,) + ride))
    if camera:
        gate(cam[0] < TOL_CM and cam[1] < TOL_DEG,
             "%s: camera_root on the %s as before: %.4f cm %.4f deg (%s)"
             % ((label, "chest" if camera == "chest" else "root") + cam))
    gate(head[1] < TOL_DEG, "%s: the head on the chest (or held in world) as before: %.4f deg "
         "(%s)" % (label, head[1], head[2]))
    for layer, before in kept_layers.items():
        gate(curves_of(layer) == before, "%s: %s's curves untouched" % (label, layer))


NB = lambda leaf: cmds.ls(maya_rigs.node(B, leaf), long=True)[0]  # noqa: E731


def one_p():
    cmds.select(NB("FKElbow_R"))
    print("    1P Setup:", fp.setup()[:200])


check("3P pose", NB, False, camera="root")
check("3P animation", NB, True, camera="root")
check("1P pose", NB, False, before_press=one_p, layers=[fp.UPPER], camera="chest")
check("1P animation", NB, True, before_press=one_p, layers=[fp.UPPER], camera="chest")


SKEL = {}


def skeleton_node(leaf):
    if "root" not in SKEL:
        roots = [r for r in cmds.ls("root", long=True, type="joint") if ":" not in r]
        SKEL["root"] = roots[0]
    found = [n for n in cmds.ls(leaf, long=True, type="joint")
             if n.startswith(SKEL["root"] + "|") or n == SKEL["root"]]
    return found[0]


def skel_pose(label):
    reopen()
    character.add_character(catalog.character_by_key("Manny"))
    SKEL.clear()
    for j in ("spine_03", "upperarm_l", "clavicle_r"):
        cmds.setAttr(skeleton_node(j) + ".rotateY", cmds.getAttr(skeleton_node(j) +
                                                                   ".rotateY") + 15)
    snap = SNAP.replace(".ma", "_skel.ma")
    cmds.file(rename=snap)
    cmds.file(save=True, type="mayaAscii", force=True)
    globals()["SNAP_SKEL"] = snap


skel_pose("skeleton")


def skel_reopen():
    cmds.file(globals()["SNAP_SKEL"], open=True, force=True)
    SKEL.clear()


_reopen = reopen
reopen = skel_reopen
check("skeleton pose", skeleton_node, False)
reopen = _reopen

print("\n%d of %d gates failed" % (len(FAILS), COUNT[0]))
