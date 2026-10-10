"""Standalone gates for the Connections FK / IK switch of the SPINE (2026-10-10).

    mayapy verify_fkik_spine.py [rig .ma, default assets/Manny_Rig.ma] [namespace, default Manny_Rig]

mayapy STANDALONE, an empty scene. The shipped rig is imported into a namespace and a synthetic
FK spine pose is keyed on the FK controls FKSpine2..4 over frames 0..24 (each on the channel
that swings the top most - `pick_swing`). The switch (`fkikspine.switch`) fits the IK spline to
the shown FK spine; the deform joints Spine1..5 are read at the keys before and after.

Gates (the switch keys the source's keys only, so it is judged at the keys):
- the refusal is empty and the blend reads FK;
- FK -> IK: the blended joints Spine1..4 stand where the FK spine stood (the spline fit, within
  FIT_GATE_CM); Spine4 and Spine5 do not move (they follow the FK chain whatever the blend);
- the blend reads IK and the spline's controls carry keys;
- the root (Root_M: the pelvis and both legs hang from it) does not move, either way - the
  spline's hip control IS the IK root (the addendum: the first switch moved it, the feet 2 cm);
- IK -> FK over the whole take brings the spine back to its FK pose;
- a range FK -> IK keeps the blended joints at its keys.
The orientation of the spline's joints is not fitted: its turn is measured and printed.

Spec: docs/superpowers/specs/2026-10-10-legs-spine-fkik-design.md
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except Exception:
        pass

from maya_scenesetup import fkik, fkikspine  # noqa: E402
import maya_rigs  # noqa: E402

RIG_FILE = (sys.argv[1] if len(sys.argv) > 1 else REPO + "/SkeldarAnim/assets/Manny_Rig.ma")
NS = sys.argv[2] if len(sys.argv) > 2 else "Manny_Rig"
DEFORM = ("Spine1_M", "Spine2_M", "Spine3_M", "Spine4_M", "Spine5_M")
BLENDED = DEFORM[:4]
TOP = ("FKXSpine5_M",)
POSED = ("FKSpine2_M", "FKSpine3_M", "FKSpine4_M")
POSES = {12: (15.0, 10.0, -8.0), 24: (-10.0, 20.0, 12.0)}
LAST = 24
GATE_KEYS = (0, 12, 24)
FIT_GATE_CM = 0.5
TOLERANCE_CM = 0.05
ROOT_CM, ROOT_DEG = 0.001, 0.001
FAILS = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", COUNT[0], text))
    sys.stdout.flush()
    if not ok:
        FAILS.append(COUNT[0])


def node(leaf):
    found = cmds.ls(NS + ":" + leaf, long=True) or []
    return found[0] if len(found) == 1 else None


def world(path):
    return om.MMatrix(cmds.getAttr(path + ".worldMatrix[0]"))


def pos(m):
    return om.MVector(m[12], m[13], m[14])


def sample(frames, joints):
    out = {}
    for frame in frames:
        cmds.currentTime(frame, update=True)
        out[frame] = [world(j) for j in joints]
    return out


def root_moved(before, after):
    """The worst move of a single joint across the frames: (cm, deg)."""
    cm = max((pos(before[f][0]) - pos(after[f][0])).length() for f in before)
    deg = max(fkik.angle(before[f][0], after[f][0]) for f in before)
    return cm, deg


def pick_swing(leaf):
    """The rotate channel of the FK control whose 15 deg turn moves the top most."""
    ctl = node(leaf)
    top = node(TOP[0])
    rest = pos(world(top))
    best = None
    for attr in ("rotateX", "rotateY", "rotateZ"):
        cmds.setAttr(ctl + "." + attr, 15.0)
        cmds.currentTime(cmds.currentTime(query=True), update=True)
        moved = (pos(world(top)) - rest).length()
        cmds.setAttr(ctl + "." + attr, 0.0)
        cmds.currentTime(cmds.currentTime(query=True), update=True)
        if best is None or moved > best[0]:
            best = (moved, attr)
    print("   swing %s: %s (moves the top %.3f cm)" % (leaf, best[1], best[0]))
    return best[1]


def key_pose(swings, last=LAST):
    for i, leaf in enumerate(POSED):
        ctl = node(leaf)
        for frame in (0, 12, 24):
            if frame > last:
                cmds.cutKey(ctl + "." + swings[leaf], time=(frame, frame), clear=True)
                continue
            value = 0.0 if frame == 0 else POSES[frame][i]
            cmds.setKeyframe(ctl, attribute=swings[leaf], time=frame, value=value)


def at(frames, data):
    return dict((f, data[f]) for f in frames)


def main():
    cmds.file(new=True, force=True)
    cmds.file(RIG_FILE, i=True, namespace=NS, returnNewNodes=True,
              executeScriptNodes=False, preserveReferences=False)
    rig = maya_rigs.find(NS)
    gate(rig is not None, "the rig %s is found" % NS)
    sp, text = fkikspine.spine(rig)
    gate(sp is not None, "the spine nodes resolve (%s)" % text)
    if sp is None:
        return
    swings = dict((leaf, pick_swing(leaf)) for leaf in POSED)
    key_pose(swings)
    span = (0, LAST, False)
    frames = list(range(0, LAST + 1))
    joints = [node(j) for j in DEFORM]
    root = [node("Root_M")]
    before = sample(frames, joints)
    root_before = sample(frames, root)
    gate(fkik.mode_of(fkik.blend_values(sp)) == fkik.FK, "the spine starts in FK")
    gate(fkikspine.refusal(sp, fkik.IK, span) == "", "FK -> IK is not refused")

    message = fkikspine.switch(sp, fkik.IK, span)
    print("   ", message)
    gate(fkik.mode_of(fkik.blend_values(sp)) == fkik.IK, "the blend reads IK")
    after = sample(frames, joints)
    keyed = (at(GATE_KEYS, before), at(GATE_KEYS, after))
    m = fkik.measure(*keyed)
    print("    FK->IK at the keys: deform joints %.4f cm (frame %s), top %.4f deg, roll %.3f deg"
          % (m.cm, m.cm_frame, m.hand, m.roll))
    for f in GATE_KEYS:
        row = []
        for j, name in enumerate(DEFORM):
            a, b = before[f][j], after[f][j]
            row.append("%s %.3fcm %.2fdeg" % (name[:6], (pos(a) - pos(b)).length(),
                                            fkik.angle(a, b)))
        print("     frame %2d | %s" % (f, " | ".join(row)))
    blended_cm = max((pos(before[f][j]) - pos(after[f][j])).length()
                     for f in GATE_KEYS for j in range(4))
    top_cm = max((pos(before[f][j]) - pos(after[f][j])).length()
                 for f in GATE_KEYS for j in (4,))
    gate(blended_cm <= FIT_GATE_CM,
         "FK -> IK puts the blended joints Spine1..4 where the FK spine stood (%.4f cm)"
         % blended_cm)
    gate(top_cm <= TOLERANCE_CM,
         "Spine5 does not move - the top follows the FK chain, which follows Spine4 (%.4f cm)" % top_cm)
    ik_keys = sum(len(cmds.keyframe(c, query=True, timeChange=True) or []) for c in sp.cv)
    gate(ik_keys > 0, "the spline controls carry keys (%d)" % ik_keys)
    cm, deg = root_moved(root_before, sample(frames, root))
    gate(cm <= ROOT_CM and deg <= ROOT_DEG,
         "FK -> IK: the root - the pelvis and the legs - does not move, every frame (%.5f cm, "
         "%.5f deg)" % (cm, deg))

    back = fkikspine.switch(sp, fkik.FK, span)
    print("   ", back)
    gate(fkik.mode_of(fkik.blend_values(sp)) == fkik.FK, "the blend reads FK again")
    again = sample(frames, joints)
    m2 = fkik.measure(at(GATE_KEYS, before), at(GATE_KEYS, again))
    print("    IK->FK at the keys: %.4f cm, %.3f deg" % (m2.cm, m2.hand))
    gate(m2.cm <= TOLERANCE_CM, "IK -> FK brings the spine back to its FK pose (%.4f cm)" % m2.cm)
    cm, deg = root_moved(root_before, sample(frames, root))
    gate(cm <= ROOT_CM and deg <= ROOT_DEG,
         "IK -> FK: the root does not move, every frame (%.5f cm, %.5f deg)" % (cm, deg))

    for leaf in POSED:
        cmds.cutKey(node(leaf), clear=True)
    key_pose(swings, last=12)
    span2 = (0, 12, True)
    frames2 = list(range(0, 13))
    before2 = sample(frames2, joints)
    root_before2 = sample(frames2, root)
    fkikspine.switch(sp, fkik.IK, span2)
    after2 = sample(frames2, joints)
    worst = max((pos(before2[f][j]) - pos(after2[f][j])).length()
                for f in (0, 12) for j in range(4))
    gate(worst <= FIT_GATE_CM, "a range FK -> IK keeps the blended joints at the keys (%.4f cm)"
         % worst)
    cm, deg = root_moved(root_before2, sample(frames2, root))
    gate(cm <= ROOT_CM and deg <= ROOT_DEG,
         "a range FK -> IK: the root does not move, every frame (%.5f cm, %.5f deg)" % (cm, deg))


try:
    main()
except Exception as exc:  # noqa: BLE001 - report, do not hide
    import traceback
    traceback.print_exc()
    FAILS.append("exception: %s" % exc)
print("RESULT: %d gates, %d failed %s" % (COUNT[0], len(FAILS), FAILS))
sys.stdout.flush()
os._exit(0 if not FAILS else 1)
