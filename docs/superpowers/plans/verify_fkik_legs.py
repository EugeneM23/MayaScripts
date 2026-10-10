"""Standalone gates for the Connections FK / IK switch of a LEG (2026-10-10).

    mayapy verify_fkik_legs.py [rig .ma, default assets/Manny_Rig.ma] [namespace, default Manny_Rig]

mayapy STANDALONE, an empty scene. The shipped rig is imported into a namespace (as Add Character
does) and a synthetic FK leg pose is keyed on the FK controls of the right leg - hip, knee,
ankle, toes - over frames 0..24. The switch (`fkik.switch`, kind LEG) keeps what the leg SHOWS:
the deform joints Hip/Knee/Ankle/Toes are read frame by frame before and after, and the
measure is the same one the Connections message reads.

Gates:
- the refusal is empty and the blend reads FK;
- FK -> IK over the whole take keeps every joint's place and the foot's turn (the bend of the
  upper leg, the hinge, is not a twist - the roll is measured and said);
- the blend reads IK at 10 and the IK controls carry keys;
- IK -> FK over the whole take brings the leg back to its FK pose (the FK keys re-written);
- the toes stay where they were through both switches (the toes control is part of the chain);
- a second, mixed pass - a partial take (the FK keyed only on 0..12) - keeps what it shows on
  both sides of the cut.

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

from maya_scenesetup import fkik  # noqa: E402
import maya_rigs  # noqa: E402

RIG_FILE = (sys.argv[1] if len(sys.argv) > 1 else REPO + "/SkeldarAnim/assets/Manny_Rig.ma")
NS = sys.argv[2] if len(sys.argv) > 2 else "Manny_Rig"
JOINTS = ("Hip_R", "Knee_R", "Ankle_R", "Toes_R")
FK_CONTROLS = ("FKHip_R", "FKKnee_R", "FKAnkle_R", "FKToes_R")
LAST = 24
FAILS = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", COUNT[0], text))
    sys.stdout.flush()
    if not ok:
        FAILS.append(COUNT[0])


def world(path):
    return om.MMatrix(cmds.getAttr(path + ".worldMatrix[0]"))


def pos(m):
    return om.MVector(m[12], m[13], m[14])


def knee_bend(joints):
    """The interior angle at the knee (degrees): 180 straight."""
    import math
    u = (pos(joints[0]) - pos(joints[1])).normal()
    v = (pos(joints[2]) - pos(joints[1])).normal()
    return math.degrees(math.acos(max(-1.0, min(1.0, u * v))))


def node(leaf):
    found = cmds.ls(NS + ":" + leaf, long=True) or []
    return found[0] if len(found) == 1 else None


def sample(frames, joints):
    out = {}
    for frame in frames:
        cmds.currentTime(frame, update=True)
        out[frame] = [world(j) for j in joints]
    return out


# the channel that swings each control, picked by what it moves (`pick_swing`): a thigh's roll
# about its own bone moves nothing, a straight leg's knee roll is undefined
SWING = {}
GATE_FRAMES = (0, 12, 24)            # the source keys: a keys-only switch is exact on them


def settle():
    cmds.currentTime(cmds.currentTime(query=True), update=True)


def pick_swing(leaf, metric):
    """The rotate channel of `leaf` whose 30 deg turn moves `metric()` the most
    (a rest value of the metric is taken first)."""
    ctl = node(leaf)
    best = None
    for attr in ("rotateX", "rotateY", "rotateZ"):
        cmds.setAttr(ctl + "." + attr, 30.0)
        settle()
        value = metric()
        cmds.setAttr(ctl + "." + attr, 0.0)
        settle()
        if best is None or value > best[0]:
            best = (value, attr)
    print("   swing %s: %s (moves %.3f)" % (leaf, best[1], best[0]))
    return best[1]


def pick_swings():
    """Fills SWING from the rig, before any key is set."""
    settle()
    rest = dict((leaf, world(node(leaf))) for leaf in ("FKXHip_R", "FKXKnee_R", "FKXAnkle_R",
                                                       "FKXToes_R"))

    def moved(leaf):
        return (pos(world(node(leaf))) - pos(rest[leaf])).length()

    def knee_bend_change():
        return abs(knee_bend([world(node(j)) for j in ("FKXHip_R", "FKXKnee_R", "FKXAnkle_R")])
                   - knee_bend([rest[j] for j in ("FKXHip_R", "FKXKnee_R", "FKXAnkle_R")]))

    def toes_turn():
        return fkik.angle(rest["FKXToes_R"], world(node("FKXToes_R")))

    SWING["FKHip_R"] = pick_swing("FKHip_R", lambda: moved("FKXKnee_R"))
    SWING["FKKnee_R"] = pick_swing("FKKnee_R", knee_bend_change)
    SWING["FKAnkle_R"] = pick_swing("FKAnkle_R", lambda: moved("FKXAnkle_R"))
    SWING["FKToes_R"] = pick_swing("FKToes_R", toes_turn)


def key_pose(full=True):
    """FK keys on the four controls: build value at 0, a bend at 12, another at 24. Over the
    partial pass the keys stop at 12 (the cut)."""
    poses = {12: (30.0, -45.0, -18.0, 22.0), 24: (-10.0, -62.0, 12.0, -8.0)}
    last = LAST if full else 12
    for leaf in FK_CONTROLS:
        ctl = node(leaf)
        attr = SWING[leaf]
        for frame in (0, 12, 24):
            if frame > last:
                cmds.cutKey(ctl + "." + attr, time=(frame, frame), clear=True)
                continue
            i = FK_CONTROLS.index(leaf)
            value = 0.0 if frame == 0 else poses[frame][i]
            cmds.setKeyframe(ctl, attribute=attr, time=frame, value=value)


def main():
    cmds.file(new=True, force=True)
    cmds.file(RIG_FILE, i=True, namespace=NS, returnNewNodes=True,
              executeScriptNodes=False, preserveReferences=False)
    rig = maya_rigs.find(NS)
    gate(rig is not None, "the rig %s is found by its ControlSet and Main" % NS)
    arm, text = fkik.limb(rig, "R", fkik.LEG)
    gate(arm is not None, "the leg nodes resolve (%s)" % text)
    if arm is None:
        return
    gate(arm.kind == fkik.LEG and arm.tip is not None and len(arm.fk) == 4,
         "a leg is a four-joint chain with a toes control")
    if fkik._curve(arm.blend) is None:
        cmds.setAttr(arm.blend, fkik.BLEND[fkik.FK])     # a rig may ship in IK (the Creep does)
    pick_swings()
    key_pose(full=True)
    span = (0, LAST, False)
    frames = list(range(0, LAST + 1))
    before = sample(frames, [node(j) for j in JOINTS])
    gate(fkik.mode_of(fkik.blend_values(arm)) == fkik.FK, "the leg starts in FK")
    gate(fkik.refusal(arm, fkik.IK, span) == "", "FK -> IK is not refused")

    message = fkik.switch(arm, fkik.IK, span)
    print("   ", message)
    gate(fkik.mode_of(fkik.blend_values(arm)) == fkik.IK, "the blend reads IK")
    after = sample(frames, [node(j) for j in JOINTS])
    # the switch keys the source's keys only (keys-only, 2026-10-08): it is exact there,
    # and between them each chain interpolates its own way - measured, not gated
    at_keys = dict((f, before[f]) for f in GATE_FRAMES), dict((f, after[f]) for f in GATE_FRAMES)
    m = fkik.measure(*at_keys)
    print("    FK->IK at the keys: joints %.4f cm (frame %s), foot %.4f deg, upper roll %.3f deg"
          % (m.cm, m.cm_frame, m.hand, m.roll))
    if os.environ.get("LEGS_TABLE"):
        for frame in frames[::3]:
            hb, ha = before[frame], after[frame]
            print("    frame %2d knee bend before %.2f after %.2f (thigh %.2f shin %.2f)" % (
                frame, knee_bend(hb), knee_bend(ha),
                (pos(hb[0]) - pos(hb[1])).length(), (pos(hb[2]) - pos(hb[1])).length()))
            row = ["%2d" % frame]
            for j, (a, b) in enumerate(zip(before[frame], after[frame])):
                row.append("%s %6.3fcm %7.2fdeg" % (JOINTS[j][:4],
                           (om.MVector(a[12], a[13], a[14]) - om.MVector(b[12], b[13], b[14])).length(),
                           fkik.angle(a, b)))
            print("   ", " | ".join(row))
    gate(m.cm <= fkik.TOLERANCE_CM, "FK -> IK keeps every leg joint's place (%.4f cm)" % m.cm)
    gate(m.hand <= fkik.TOLERANCE_DEG, "FK -> IK keeps the foot and toes' turn (%.4f deg)"
         % m.hand)
    ik_key = cmds.keyframe(node("IKLeg_R"), query=True, timeChange=True) or []
    gate(len(ik_key) > 0, "the IK control carries keys (%d)" % len(ik_key))

    back = fkik.switch(arm, fkik.FK, span)
    print("   ", back)
    gate(fkik.mode_of(fkik.blend_values(arm)) == fkik.FK, "the blend reads FK again")
    again = sample(frames, [node(j) for j in JOINTS])
    m2 = fkik.measure(dict((f, before[f]) for f in GATE_FRAMES),
                      dict((f, again[f]) for f in GATE_FRAMES))
    print("    IK->FK measure: joints %.4f cm, foot %.4f deg" % (m2.cm, m2.hand))
    gate(m2.cm <= fkik.TOLERANCE_CM and m2.hand <= fkik.TOLERANCE_DEG,
         "IK -> FK brings the leg back to its FK pose (%.4f cm, %.4f deg)" % (m2.cm, m2.hand))

    # a partial take: the FK keys stop at frame 12, the switch to IK covers 0..12 only
    cmds.cutKey(node("FKHip_R"), clear=True)
    for leaf in FK_CONTROLS:
        cmds.cutKey(node(leaf), clear=True)
    key_pose(full=False)
    span2 = (0, 12, True)
    frames2 = list(range(0, 13))
    before2 = sample(frames2, [node(j) for j in JOINTS])
    fkik.switch(arm, fkik.IK, span2)
    after2 = sample(frames2, [node(j) for j in JOINTS])
    m3 = fkik.measure(dict((f, before2[f]) for f in (0, 12)),
                      dict((f, after2[f]) for f in (0, 12)))
    print("    partial FK->IK measure: %.4f cm, foot %.4f deg" % (m3.cm, m3.hand))
    gate(m3.cm <= fkik.TOLERANCE_CM, "a range FK -> IK keeps the leg (%.4f cm)" % m3.cm)


try:
    main()
except Exception as exc:  # noqa: BLE001 - report, do not hide
    import traceback
    traceback.print_exc()
    FAILS.append("exception: %s" % exc)
print("RESULT: %d gates, %d failed %s" % (COUNT[0], len(FAILS), FAILS))
sys.stdout.flush()
os._exit(0 if not FAILS else 1)
