"""Standalone gates for the Connections FK / IK switch (2026-09-30).

    mayapy verify_fkik_switch.py <UE5 clip .fbx> [rig keys, default Manny_Rig,Creep_Rig,Orc_D_Rig]

mayapy STANDALONE, an empty scene per rig (spec docs/superpowers/specs/2026-09-30-connections-fkik-switch-design.md).
Each rig added through Add Character, the clip retargeted onto it through the Retarget button, the
source deleted. Measuring the UE bones (upperarm, lowerarm, hand, a finger) frame by frame:

- the retargeted take as it comes: FK -> IK keeps every joint's PLACE and the hand's turn; the
  forearm twist the clip put on the FK elbow (an IK elbow is a hinge) is measured and said, not
  gated; the blend unkeyed at 10, the FK keys untouched; IK -> FK then reproduces the IK exactly;
- then the FK arm EDITED the ways an IK arm can hold (the shoulder turned, the elbow bent about ITS
  HINGE - the FKX elbow's Z in the control's axes, not a channel: the Orc's rotateZ stands 1.3 deg
  off it - the wrist turned), so FK and IK no longer agree - a plain blend flip is measured to
  jump, the positive control - and on it:
- FK -> IK over the whole take keeps every UE bone; the blend unkeyed at 10; the FK keys untouched;
- IK -> FK back over the whole take keeps it; the blend at 0;
- a RANGE (a highlight) to IK: inside and outside kept, the blend keyed a-1/a/b/b+1 stepped, the
  keys outside the range untouched;
- from that MIXED take, the whole take to IK keeps it and unkeys the blend;
- one Ctrl+Z undoes a switch whole;
- Connections: Hand_L -> Weapon on an FK arm no longer jumps (the arm is switched first), FK on
  that following hand releases it and keeps it, "already FK", a standing retarget, a foreign
  constraint and a keyed swivel inside a range are refused, a keyed swivel over the whole take is
  reset and named.
"""
import math
import sys
import time

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
CLIP = sys.argv[1].replace("\\", "/")
RIGS = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["Manny_Rig", "Creep_Rig", "Orc_D_Rig"])

from maya_scenesetup import attach, catalog, character, connections as cx, fkik  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402

FAILS = []
COUNT = [0]
KEPT_CM, KEPT_DEG = 0.01, 0.05


def gate(ok, msg):
    COUNT[0] += 1
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append((RIG_KEY, COUNT[0]))


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def ang(a, b):
    qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    q = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def pos(m):
    return om.MVector(m[12], m[13], m[14])


def track(nodes, frames):
    out = {}
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = [wm(n) for n in nodes]
    return out


def diff(a, b, frames=None):
    cm = deg = 0.0
    at = None
    for f in frames or sorted(a):
        for x, y in zip(a[f], b[f]):
            d_cm, d_deg = (pos(x) - pos(y)).length(), ang(x, y)
            if d_cm > cm:
                at = f
            cm, deg = max(cm, d_cm), max(deg, d_deg)
    return cm, deg, at


def fmt(d):
    return "%.5f cm, %.4f deg (frame %s)" % d


def curves_of(nodes):
    """{plug: [(time, value)]} of every keyed t/r channel."""
    out = {}
    for n in nodes:
        for ch in fkik.CHANNELS:
            plug = n + "." + ch
            times = cmds.keyframe(plug, query=True, timeChange=True) or []
            values = cmds.keyframe(plug, query=True, valueChange=True) or []
            out[plug] = list(zip(times, values))
    return out


def same_curves(a, b, outside=None):
    """Worst value change of keys present in both, at times outside `outside` (a, b)."""
    worst = 0.0
    for plug, keys in a.items():
        other = dict(b.get(plug, []))
        for t, v in keys:
            if outside and outside[0] <= t <= outside[1]:
                continue
            if t not in other:
                return float("inf")
            worst = max(worst, abs(other[t] - v))
    return worst


def blend_keys(arm):
    times = cmds.keyframe(arm.blend, query=True, timeChange=True) or []
    values = cmds.keyframe(arm.blend, query=True, valueChange=True) or []
    return list(zip(times, values))


t_all = time.time()
for RIG_KEY in RIGS:
    print("=" * 30, RIG_KEY)
    t0 = time.time()
    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    text = character.add_character(catalog.character_by_key(RIG_KEY))
    rig = maya_rigs.rigs()[0]
    N = lambda leaf: cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]  # noqa: E731
    # the clip, retargeted through the button, the source deleted
    cmds.namespace(add="clip")
    cmds.namespace(set=":clip")
    mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
    before = set(cmds.ls(type="joint", long=True))
    mel.eval('FBXImport -f "%s";' % CLIP)
    cmds.namespace(set=":")
    new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
              key=lambda j: j.count("|"))
    keys = cmds.keyframe(new, query=True, timeChange=True) or [0, 24]
    first, last = int(min(keys)), int(max(keys))
    last = min(last, first + 60)                       # enough frames, a quick run
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    cmds.select(N("Main"), src)
    ok, rtext = rr.run_retarget()
    cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    frames = list(range(first, last + 1))
    R, L = fkik.limb(rig, "R")[0], fkik.limb(rig, "L")[0]
    gate(ok and R is not None and L is not None and fkik.state(rig, "R") == fkik.FK,
         "%s added, the clip retargeted (%d..%d), the arms FK: %s" % (text.split(" - ")[0], first, last,
                                                                    rtext.splitlines()[0][:80]))
    bones = {side: [N(b + "_" + side.lower()) for b in ("upperarm", "lowerarm", "hand", "middle_01")]
             for side in ("R", "L")}

    # ---------------------------------------------- the retargeted take, as it comes
    raw = track(bones["R"], frames)
    cmds.setAttr(R.blend, 10)
    flip = diff(raw, track(bones["R"], frames))
    cmds.setAttr(R.blend, 0)
    print("    the retarget's own IK stands off its FK by %s - what a plain flip (Connections "
          "before today) showed" % fmt(flip))
    fk_keys = curves_of(R.fk)
    t1 = time.time()
    text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
    took = time.time() - t1
    after = track(bones["R"], frames)
    places = max((pos(x) - pos(y)).length() for f in frames for x, y in zip(raw[f], after[f]))
    hand = max(ang(raw[f][2], after[f][2]) for f in frames)
    roll = max(ang(raw[f][i], after[f][i]) for f in frames for i in (0, 1))
    gate(places < fkik.TOLERANCE_CM and hand < KEPT_DEG and ("kept" in text),
         "FK -> IK on the retargeted take: every joint in place to %.5f cm, the hand to %.4f deg; "
         "the arm's roll %.2f deg, said: %s (%.1f s)" % (places, hand, roll, text, took))
    gate(not blend_keys(R) and cmds.getAttr(R.blend) == 10.0 and fkik.state(rig, "R") == fkik.IK
         and same_curves(fk_keys, curves_of(R.fk)) < 1e-9 and cmds.keyframe(R.ik, query=True, keyframeCount=True),
         "the blend unkeyed at 10, the IK control keyed, the FK keys untouched")
    ik_shown = after
    text = cx.switch_arm("R", fkik.FK, rig=rig, highlight=False)
    d = diff(ik_shown, track(bones["R"], frames))
    gate(d[0] < KEPT_CM and d[1] < KEPT_DEG and "the arm kept" in text and fkik.state(rig, "R") == fkik.FK
         and not blend_keys(R),
         "IK -> FK reproduces the IK exactly (every UE bone): %s | %s" % (fmt(d), text))

    # ---------------------------------------------- an FK take an IK arm can hold, edited
    #  the left arm made so too: through IK and back
    cx.switch_arm("L", fkik.IK, rig=rig, highlight=False)
    cx.switch_arm("L", fkik.FK, rig=rig, highlight=False)
    mid = (first + 8, last - 8)
    hinges = []
    for side, arm in (("R", R), ("L", L)):
        #  the elbow bent about ITS HINGE exactly - the FKX elbow's Z (an IK
        #  elbow turns about Z only; FK came from IK, so FKX is the IK chain)
        #  in the control's own axes; a control channel can stand off it (the
        #  Orc's rotateZ 1.3 deg), and that would be a twist no IK can hold
        cmds.currentTime(first, update=True)
        hinge = (om.MVector(0, 0, 1) * fkik.rotation_only(wm(arm.fkx[1]) * wm(arm.fk[1]).inverse())).normal()
        hinges.append("%s (%.3f %.3f %.3f)" % (side, hinge.x, hinge.y, hinge.z))
        order = cmds.getAttr(arm.fk[1] + ".rotateOrder")
        bend = om.MQuaternion(math.radians(15.0), hinge).asMatrix()
        for f in range(mid[0] + 1, mid[1]):
            old = [cmds.getAttr(arm.fk[1] + "." + ch, time=f) for ch in fkik.ROTATE]
            rot = om.MEulerRotation(*[math.radians(v) for v in old] + [order]).asMatrix()
            _t, new = fkik.local_channels(bend * rot, order, old)
            for ch, v in zip(fkik.ROTATE, new):
                cmds.setKeyframe(arm.fk[1], attribute=ch, time=f, value=v)
        for node, channel, delta in ((arm.fk[0], "rotateY", 12.0), (arm.fk[2], "rotateX", 20.0)):
            plug = node + "." + channel
            if not cmds.keyframe(plug, query=True, keyframeCount=True):
                cmds.setKeyframe(plug, time=first)
            cmds.setKeyframe(plug, time=mid[0], insert=True)
            cmds.setKeyframe(plug, time=mid[1], insert=True)
            cmds.keyframe(plug, edit=True, relative=True, valueChange=delta, time=(mid[0] + 1, mid[1] - 1))
    shown = track(bones["R"], frames)
    cmds.setAttr(R.blend, 10)
    jump = diff(shown, track(bones["R"], frames))
    cmds.setAttr(R.blend, 0)
    gate(jump[0] > 1.0, "the FK arm edited (shoulder, the elbow about its hinge: %s, wrist): a plain "
         "blend flip jumps it by %s (the positive control)" % (", ".join(hinges), fmt(jump)))

    fk_keys = curves_of(R.fk)
    text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
    d = diff(shown, track(bones["R"], frames))
    gate(d[0] < KEPT_CM and d[1] < KEPT_DEG and "the arm kept" in text
         and same_curves(fk_keys, curves_of(R.fk)) < 1e-9 and not blend_keys(R),
         "FK -> IK over the whole take keeps every UE bone: %s | %s" % (fmt(d), text))
    text = cx.switch_arm("R", fkik.FK, rig=rig, highlight=False)
    d = diff(shown, track(bones["R"], frames))
    gate(d[0] < KEPT_CM and d[1] < KEPT_DEG and fkik.state(rig, "R") == fkik.FK,
         "IK -> FK back over the whole take keeps it: %s | %s" % (fmt(d), text))

    # ---------------------------------------------------------- a range to IK
    a, b = first + 15, first + 30
    fk_keys, ik_keys = curves_of(R.fk), curves_of([R.ik, R.pole])
    text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=(float(a), float(b + 1)))
    after = track(bones["R"], frames)
    d_in, d_out = diff(shown, after, range(a, b + 1)), diff(shown, after, [f for f in frames if f < a or f > b])
    keys = blend_keys(R)
    steps = [cmds.keyTangent(R.blend, query=True, time=(t, t), outTangentType=True)[0] for t, _v in keys]
    gate(d_in[0] < KEPT_CM and d_out[0] < KEPT_CM and d_in[1] < KEPT_DEG and d_out[1] < KEPT_DEG
         and "over the range %d..%d" % (a, b) in text,
         "a range %d..%d to IK: inside %s, outside %s" % (a, b, fmt(d_in), fmt(d_out)))
    gate(keys == [(a - 1, 0.0), (a, 10.0), (b, 10.0), (b + 1, 0.0)] and steps[0] == "step" and steps[2] == "step"
         and same_curves(fk_keys, curves_of(R.fk)) < 1e-9
         and same_curves(ik_keys, curves_of([R.ik, R.pole]), outside=(a, b)) < 1e-9
         and fkik.state(rig, "R") is None,
         "the blend keyed %s, stepped %s; FK keys and IK keys outside kept; the arm reads mixed" % (keys, steps))

    # ---------------------------------------------------------- from the mixed take, whole to IK
    text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
    d = diff(shown, track(bones["R"], frames))
    gate(d[0] < KEPT_CM and d[1] < KEPT_DEG and not blend_keys(R) and fkik.state(rig, "R") == fkik.IK,
         "from the mixed take the whole take to IK keeps it and unkeys the blend: %s" % fmt(d))

    # ---------------------------------------------------------- one undo
    ik_now = curves_of([R.ik])
    cx.switch_arm("R", fkik.FK, rig=rig, highlight=False)
    cmds.undo()
    d = diff(shown, track(bones["R"], frames))
    gate(fkik.state(rig, "R") == fkik.IK and same_curves(ik_now, curves_of([R.ik])) < 1e-9 and d[0] < KEPT_CM,
         "one Ctrl+Z undoes a switch whole (IK again, its keys as they were): %s" % fmt(d))

    # ---------------------------------------------------------- Connections
    hand_r, bone_r = cx.bones_of(rig)["R"]
    weapon, _note = attach.attach(catalog.by_key("LongSword_02"), hand_r, bone_r)
    shown_l = track(bones["L"], frames)
    text = cx.apply({"L": cx.FOLLOWS, "R": cx.HOLDS}, rig=rig)
    d = diff(shown_l, track(bones["L"], frames))
    gate(cx.read_scheme(rig) == {"L": cx.FOLLOWS, "R": cx.HOLDS} and "Arm_L to IK" in text
         and d[0] < KEPT_CM and d[1] < KEPT_DEG,
         "Hand_L -> Weapon on the edited FK arm: switched first, no jump: %s | %s" % (fmt(d), text[-90:]))
    text = cx.switch_arm("L", fkik.IK, rig=rig, highlight=False)
    gate("already IK (it follows" in text, "IK on the following hand: %s" % text)
    text = cx.switch_arm("L", fkik.FK, rig=rig, highlight=False)
    d = diff(shown_l, track(bones["L"], frames))
    gate(text.startswith("Hand_L released from") and cx.read_scheme(rig) == {"L": None, "R": cx.HOLDS}
         and not cx.proxies() and fkik.state(rig, "L") == fkik.FK and d[0] < KEPT_CM and d[1] < KEPT_DEG,
         "FK on the following hand: released, then FK, the arm kept: %s | %s" % (fmt(d), text[:120]))

    # ---------------------------------------------------------- refusals
    text = cx.switch_arm("L", fkik.FK, rig=rig, highlight=False)
    gate(text == "Arm_L is already FK", "again: %s" % text)
    holder = cmds.createNode("transform", name=maya_rigs.node(rig, "MoCapConstraints"))
    text = cx.switch_arm("L", fkik.IK, rig=rig, highlight=False)
    cmds.delete(holder)
    gate(text == cx.RETARGETING, "a standing retarget: %s" % text)
    #  a constraint on a keyed channel splices a pairBlend: undo it, never delete
    loc = cmds.spaceLocator()[0]
    cmds.orientConstraint(loc, R.fk[2], maintainOffset=True)
    text = cx.switch_arm("R", fkik.FK, rig=rig, highlight=False)
    cmds.undo()
    cmds.delete(loc)
    gate("is driven by" in text and "FKWrist_R.rotate" in text,
         "somebody's constraint on an FK control (the arm in IK): %s" % text)
    text = cx.switch_arm("R", fkik.FK, rig=rig, highlight=False)
    gate("kept" in text and not cmds.listConnections(R.fk[2] + ".rotateX", source=True, type="pairBlend"),
         "then the right arm to FK, no pairBlend left: %s" % text[:70])
    loc = cmds.spaceLocator()[0]
    cmds.orientConstraint(loc, R.ik, maintainOffset=True)
    text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
    cmds.undo()
    cmds.delete(loc)
    gate("is driven by" in text and "IKArm_R.rotate" in text,
         "somebody's constraint on the IK control: %s" % text)
    swivel = R.ik + ".swivel"
    cmds.setKeyframe(swivel, time=first, value=0)
    cmds.setKeyframe(swivel, time=last, value=30)
    text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=(float(a), float(b + 1)))
    gate("swivel not at the default" in text, "a keyed swivel inside a range: %s" % text)
    text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
    d = diff(shown, track(bones["R"], frames))
    gate("swivel reset to 0" in text and not cmds.keyframe(swivel, query=True, keyframeCount=True)
         and d[0] < KEPT_CM, "over the whole take it is reset and named, the arm kept: %s | %s" % (fmt(d), text[-60:]))
    print("   %s took %.1f s" % (RIG_KEY, time.time() - t0))

print("=" * 30)
print("%d gates, %d failed %s (%.0f s)" % (COUNT[0], len(FAILS), FAILS, time.time() - t_all))
