"""Standalone gates for the keys-only FK / IK switch (2026-10-08).

    mayapy verify_fkik_keys.py

mayapy STANDALONE, an empty scene per case (spec
docs/superpowers/specs/2026-10-08-fkik-keys-only-design.md). Hand keys, as an animator sets them:

A  Manny_Rig, BLOCKING (stepped): the right FK arm keyed on 0, 12, 24, the clavicle on 0 and 6, Main
   on 0 and 18; the left arm on 3 and 9, the right leg on 15, a right finger on 21 - none of them
   upstream of the right arm. FK -> IK keys the IK control on exactly 0, 6, 12, 18, 24, stepped,
   and the arm stands where it stood on EVERY frame (stepped holds); the FK keys untouched. IK -> FK
   keys the FK controls on the same five, stepped, every frame kept.
B  Creep_Rig, AUTO tangents: the FK arm on 0, 10, 20, 30, 40, the clavicle (linear) on 0 and 25. A
   range 8..32 to IK keys 8, 10, 20, 25, 30, 32 (the keys inside and the range's ends), the arm
   kept on those, auto where the arm had auto, linear on the clavicle's own frame, the blend stepped
   7/8/32/33. From that mixed take the whole take to IK keys the union of both chains, the
   clavicle and the blend, kept on every one. Back to FK on the same frames. An additive layer's
   key on the wrist (36) is counted.
C  Manny_Rig, NOTHING keyed (a pose set by hand): FK -> IK writes plain values, no key, the arm
   kept; the line says so.
"""
import math
import sys
import time

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

from maya_scenesetup import catalog, character, connections as cx, fkik  # noqa: E402
import maya_rigs  # noqa: E402

FAILS = []
COUNT = [0]
KEPT_CM, KEPT_DEG = 0.01, 0.05
CASE = ["-"]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append((CASE[0], COUNT[0]))


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
    for f in frames if frames is not None else sorted(a):
        for x, y in zip(a[f], b[f]):
            d_cm, d_deg = (pos(x) - pos(y)).length(), ang(x, y)
            if d_cm > cm:
                at = f
            cm, deg = max(cm, d_cm), max(deg, d_deg)
    return cm, deg, at


def fmt(d):
    return "%.5f cm, %.4f deg (frame %s)" % d


def times(nodes):
    out = set()
    for n in nodes:
        out.update(round(t, 4) for t in cmds.keyframe(n, query=True, timeChange=True) or [])
    return sorted(out)


def out_types(plug):
    return cmds.keyTangent(plug, query=True, outTangentType=True) or []


def curves_of(nodes):
    out = {}
    for n in nodes:
        for ch in fkik.CHANNELS:
            plug = n + "." + ch
            ts = cmds.keyframe(plug, query=True, timeChange=True) or []
            vs = cmds.keyframe(plug, query=True, valueChange=True) or []
            out[plug] = list(zip(ts, vs))
    return out


def add(key):
    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(min=0, max=48, animationStartTime=0, animationEndTime=48)
    cmds.currentTime(0)
    text = character.add_character(catalog.character_by_key(key))
    rig = maya_rigs.rigs()[0]
    return rig, text


def node(rig, leaf):
    return cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]


def key(n, attr, t, v, itt=None, ott=None):
    flags = {}
    if itt:
        flags["inTangentType"] = itt
    if ott:
        flags["outTangentType"] = ott
    cmds.setKeyframe(n, attribute=attr, time=t, value=v, **flags)


def key_arm(arm, frames, poses, itt=None, ott=None):
    """The FK arm keyed on `frames`: (shoulder rx/ry/rz, elbow bend about its HINGE, wrist rx/ry/rz)
    per frame - the elbow about the FKX elbow's Z in the control's axes, the bend an IK arm holds."""
    cmds.currentTime(frames[0], update=True)
    hinge = (om.MVector(0, 0, 1) * fkik.rotation_only(wm(arm.fkx[1]) * wm(arm.fk[1]).inverse())).normal()
    order = cmds.getAttr(arm.fk[1] + ".rotateOrder")
    for f, (shoulder, bend, wrist) in zip(frames, poses):
        for ch, v in zip(fkik.ROTATE, shoulder):
            key(arm.fk[0], ch, f, v, itt, ott)
        _t, r = fkik.local_channels(om.MQuaternion(math.radians(bend), hinge).asMatrix(), order,
                                    (0.0, 0.0, 0.0))
        for ch, v in zip(fkik.ROTATE, r):
            key(arm.fk[1], ch, f, v, itt, ott)
        for ch, v in zip(fkik.ROTATE, wrist):
            key(arm.fk[2], ch, f, v, itt, ott)


t_all = time.time()

# ------------------------------------------------------------------ A: blocking, stepped
CASE[0] = "A"
print("=" * 30, "A  Manny_Rig, blocking (stepped)")
rig, text = add("Manny_Rig")
R, L = fkik.limb(rig, "R")[0], fkik.limb(rig, "L")[0]
ub = [node(rig, b + "_r") for b in ("upperarm", "lowerarm", "hand", "middle_01")]
frames = list(range(0, 31))
key_arm(R, [0, 12, 24], [((0, 0, 0), 5, (0, 0, 0)), ((10, -25, 20), 40, (25, 10, -15)),
                         ((-15, 20, -10), 70, (-20, -15, 30))], itt="clamped", ott="step")
scap, main = node(rig, "FKScapula_R"), node(rig, "Main")
key(scap, "rotateZ", 0, 0.0, "clamped", "step")
key(scap, "rotateZ", 6, 12.0, "clamped", "step")
key(main, "translateX", 0, 0.0, "clamped", "step")
key(main, "translateX", 18, 30.0, "clamped", "step")
key(L.fk[0], "rotateY", 3, 15.0)                         # not upstream of the right arm
key(L.fk[0], "rotateY", 9, -15.0)
key(node(rig, "IKLeg_R"), "translateY", 15, 4.0)
key(node(rig, "FKMiddleFinger1_R"), "rotateZ", 21, 30.0)
expected = [0.0, 6.0, 12.0, 18.0, 24.0]
shown = track(ub, frames)
curves = fkik.driving_curves(*fkik.sources(R, fkik.FK)[:2])
gate(fkik.key_frames([t for c in curves for t in cmds.keyframe(c, query=True, timeChange=True)],
                     (0, 48, False)) == expected,
     "the walk from the FK arm finds the arm's, the clavicle's and Main's curves only: %s"
     % sorted(c.split("|")[-1] for c in curves))
fk_keys = curves_of(R.fk)
t0 = time.time()
text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
took = time.time() - t0
got = times([R.ik, R.pole])
d = diff(shown, track(ub, frames))
gate(got == expected and "on 5 keys (0..24)" in text,
     "FK -> IK keys the IK control and the pole on exactly %s: %s | %s (%.2f s)" % (expected, got, text, took))
gate(d[0] < KEPT_CM and d[1] < KEPT_DEG,
     "stepped: the arm where it stood on EVERY frame 0..30: %s" % fmt(d))
gate(set(out_types(R.ik + ".rotateX")) == {"step"} and set(out_types(R.pole + ".translateX")) == {"step"},
     "the new keys stepped as the arm's: %s" % out_types(R.ik + ".rotateX"))
same = all(fk_keys[p] == v for p, v in curves_of(R.fk).items())
gate(same and not cmds.keyframe(R.blend, query=True, keyframeCount=True) and cmds.getAttr(R.blend) == 10.0,
     "the FK keys untouched, the blend unkeyed at 10")
text = cx.switch_arm("R", fkik.FK, rig=rig, highlight=False)
got = times(R.fk)
d = diff(shown, track(ub, frames))
gate(got == expected and d[0] < KEPT_CM and d[1] < KEPT_DEG and set(out_types(R.fk[1] + ".rotateX")) == {"step"},
     "IK -> FK keys the FK controls on the same five, stepped, every frame kept: %s, %s | %s"
     % (got, fmt(d), text))

# ------------------------------------------------------------------ B: auto tangents, a range, mixed, a layer
CASE[0] = "B"
print("=" * 30, "B  Creep_Rig, auto tangents")
rig, text = add("Creep_Rig")
R = fkik.limb(rig, "R")[0]
ub = [node(rig, b + "_r") for b in ("upperarm", "lowerarm", "hand", "middle_01")]
frames = list(range(0, 48))
key_arm(R, [0, 10, 20, 30, 40], [((0, 0, 0), 5, (0, 0, 0)), ((10, -25, 20), 40, (25, 10, -15)),
                                 ((-15, 20, -10), 70, (-20, -15, 30)), ((5, 10, 25), 25, (10, 20, 5)),
                                 ((0, -10, 0), 55, (-5, 0, 0))], itt="auto", ott="auto")
scap = node(rig, "FKScapula_R")
key(scap, "rotateZ", 0, 0.0, "linear", "linear")
key(scap, "rotateZ", 25, 10.0, "linear", "linear")
shown = track(ub, frames)
a, b = 8, 32
text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=(float(a), float(b + 1)))
got = times([R.ik, R.pole])
inside = [8.0, 10.0, 20.0, 25.0, 30.0, 32.0]
after = track(ub, frames)
d_keys = diff(shown, after, [int(f) for f in inside])
d_between = diff(shown, after, [f for f in range(a, b + 1) if f not in inside])
d_out = diff(shown, after, [f for f in frames if f < a or f > b])
gate(got == inside and "over the range 8..32 on 6 keys" in text,
     "a range 8..32 to IK keys the keys inside and its ends: %s | %s" % (got, text))
gate(d_keys[0] < KEPT_CM and d_keys[1] < KEPT_DEG and d_out[0] < KEPT_CM,
     "kept on those keys %s, outside %s; between keys each chain its own way: %s"
     % (fmt(d_keys), fmt(d_out), fmt(d_between)))
tangent = dict(zip(cmds.keyframe(R.ik + ".rotateX", query=True, timeChange=True),
                   zip(cmds.keyTangent(R.ik + ".rotateX", query=True, inTangentType=True),
                       out_types(R.ik + ".rotateX"))))
gate(all(tangent[f] == ("auto", "auto") for f in (10.0, 20.0, 30.0)) and tangent[25.0] == ("linear", "linear"),
     "auto where the arm had auto, linear on the clavicle's own frame: %s" % tangent)
blend = list(zip(cmds.keyframe(R.blend, query=True, timeChange=True),
                 cmds.keyframe(R.blend, query=True, valueChange=True)))
gate(blend == [(7.0, 0.0), (8.0, 10.0), (32.0, 10.0), (33.0, 0.0)], "the blend stepped around it: %s" % blend)

mixed_frames = [0.0, 7.0, 8.0, 10.0, 20.0, 25.0, 30.0, 32.0, 33.0, 40.0]
shown_mixed = after
text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
got = times([R.ik, R.pole])
d = diff(shown_mixed, track(ub, frames), [int(f) for f in mixed_frames])
gate(got == mixed_frames and d[0] < KEPT_CM and d[1] < KEPT_DEG
     and not cmds.keyframe(R.blend, query=True, keyframeCount=True),
     "from the mixed take the whole take to IK keys both chains', the clavicle's and the blend's "
     "frames %s, kept on them: %s | %s" % (got, fmt(d), text))
shown_ik = track(ub, frames)
text = cx.switch_arm("R", fkik.FK, rig=rig, highlight=False)
got = times(R.fk)
d = diff(shown_ik, track(ub, frames), [int(f) for f in mixed_frames])
gate(got == mixed_frames and d[0] < KEPT_CM and d[1] < KEPT_DEG,
     "back to FK on the same frames %s, kept: %s" % (got, fmt(d)))
layer = cmds.animLayer("verifyLayer")
cmds.animLayer(layer, edit=True, attribute=[R.fk[2] + ".rotateX"])
cmds.setKeyframe(R.fk[2], attribute="rotateX", time=36, value=15.0, animLayer=layer)
text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
got = times([R.ik])
gate(36.0 in got and got == sorted(set(mixed_frames) | {36.0}),
     "a key on an animation layer (36) counts: %s | %s" % (got, text))

# ------------------------------------------------------------------ C: nothing keyed
CASE[0] = "C"
print("=" * 30, "C  Manny_Rig, nothing keyed")
rig, text = add("Manny_Rig")
R = fkik.limb(rig, "R")[0]
ub = [node(rig, b + "_r") for b in ("upperarm", "lowerarm", "hand", "middle_01")]
cmds.setAttr(R.fk[0] + ".rotateY", -20)
cmds.setAttr(R.fk[2] + ".rotateX", 25)
cmds.currentTime(5, update=True)
shown = track(ub, [5, 30])
text = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
d = diff(shown, track(ub, [5, 30]))
gate(not times([R.ik, R.pole]) and d[0] < KEPT_CM and d[1] < KEPT_DEG
     and "no keys - nothing keyed moves the arm" in text,
     "nothing keyed: plain values, no key, the arm kept: %s | %s" % (fmt(d), text))

print("=" * 30)
print("%d gates, %d failed %s (%.0f s)" % (COUNT[0], len(FAILS), FAILS, time.time() - t_all))
