"""Live proof that the Manny -> suit retarget transfers motion exactly.

Send through the command port. Bridge hygiene (CLAUDE.md): never cmds.undo()
here, disable autoKey around pokes, wiggle time before reading, and restore
what was read rather than writing literal rest values.

The predicates are exact, not approximate, which is what makes this worth
running:

  offset mode    orientConstraint(mo=True) holds W_target = O * W_source with a
                 constant O, and Maya's row-vector convention puts a
                 left-multiplied O in the bone's OWN frame - the correction
                 rides along with the source instead of staying pinned in
                 world. So the invariant is the delta taken in that order:

                     W_rest^-1 * W_now  identical for source and target

                 (W_now * W_rest^-1 is NOT invariant - it comes out conjugated
                 by O, which is exactly how a wrong order shows itself: bones
                 with a near-zero rest offset still agree, every limb bone
                 does not.)
  absolute mode  target_world == source_world outright.
  no arc         with Manny turned 90 degrees on the spot, the suit's pelvis
                 keeps the UNROTATED world offset. This is the whole reason
                 pelvis uses point+orient instead of parentConstraint.
"""
import math
from contextlib import contextmanager

import maya.cmds as cmds
import maya.api.OpenMaya as om

NS = "Mesh_protective_suit:"
RETARGET_SET = "retarget_manny_to_suit"
TOL_DEG = 0.01
TOL_CM = 0.01

results = []


def check(label, ok, detail):
    results.append((label, ok, detail))
    print("%-42s %s  %s" % (label, "PASS" if ok else "FAIL", detail))


def wmat(obj):
    sel = om.MSelectionList()
    sel.add(obj)
    return sel.getDagPath(0).inclusiveMatrix()


def rot_only(m):
    t = om.MTransformationMatrix(m)
    t.setTranslation(om.MVector(0, 0, 0), om.MSpace.kTransform)
    t.setScale([1, 1, 1], om.MSpace.kTransform)
    return t.asMatrix()


def angle_between(a, b):
    d = rot_only(a).inverse() * rot_only(b)
    tr = d[0] + d[5] + d[10]
    return math.degrees(math.acos(max(-1.0, min(1.0, (tr - 1.0) / 2.0))))


def settle():
    """Interactive reads lie without a time change (CLAUDE.md trap 14)."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, update=True)
    cmds.currentTime(now, update=True)
    cmds.refresh()


@contextmanager
def posed(pokes):
    """Apply {node.attr: delta}, restore exactly what was read. autoKey off."""
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    before = {}
    try:
        for attr, delta in pokes.items():
            before[attr] = cmds.getAttr(attr)
            cmds.setAttr(attr, before[attr] + delta)
        settle()
        yield
    finally:
        for attr, value in before.items():
            cmds.setAttr(attr, value)
        settle()
        cmds.autoKeyframe(state=auto)


OFFSET_BONES = ["pelvis", "spine_03", "clavicle_l", "upperarm_l", "lowerarm_l",
                "hand_l", "thigh_r", "calf_r", "foot_r", "head", "neck_01"]
FINGER_BONES = ["index_01_r", "index_02_r", "thumb_01_l", "pinky_03_r",
                "middle_02_l"]
# suit bone -> Manny bone, where the two differ (the semantic spine map)
MAP = {"spine_03": "spine_05"}

POKES = {
    "pelvis.rotateY": 12.0,
    "spine_02.rotateZ": 9.0,
    "spine_04.rotateZ": 11.0,
    "clavicle_l.rotateY": 8.0,
    "upperarm_l.rotateZ": 25.0,
    "lowerarm_l.rotateZ": -30.0,
    "thigh_r.rotateZ": 18.0,
    "calf_r.rotateZ": -22.0,
    "neck_01.rotateZ": 7.0,
    "index_01_r.rotateZ": 20.0,
    "thumb_01_l.rotateY": 15.0,
}

print("=== RETARGET VERIFY ===")
if not cmds.objExists(RETARGET_SET):
    print("FAIL: no retarget rig in the scene - run build_retarget() first")
else:
    settle()
    rest = {}
    for bone in OFFSET_BONES:
        rest[bone] = (wmat(MAP.get(bone, bone)), wmat(NS + bone))

    with posed(POKES):
        print()
        print("--- offset mode: world rotation DELTA must transfer exactly ---")
        for bone in OFFSET_BONES:
            src_rest, tgt_rest = rest[bone]
            src_now, tgt_now = wmat(MAP.get(bone, bone)), wmat(NS + bone)
            src_delta = rot_only(src_rest).inverse() * rot_only(src_now)
            tgt_delta = rot_only(tgt_rest).inverse() * rot_only(tgt_now)
            err = angle_between(src_delta, tgt_delta)
            check("delta  %s" % bone, err < TOL_DEG, "err %.5f deg" % err)

        print()
        print("--- absolute mode: fingers must match Manny outright ---")
        for bone in FINGER_BONES:
            err = angle_between(wmat(bone), wmat(NS + bone))
            check("absolute  %s" % bone, err < TOL_DEG, "err %.5f deg" % err)

        print()
        print("--- pelvis translation follows ---")
        pm = cmds.xform("pelvis", q=True, ws=True, t=True)
        ps = cmds.xform(NS + "pelvis", q=True, ws=True, t=True)
        off = cmds.getAttr(RETARGET_SET + ".retargetSideOffset")
        dx = ps[0] - pm[0]
        check("pelvis side offset held", abs(dx - off) < TOL_CM,
              "dx %.4f vs %.4f" % (dx, off))

    print()
    print("--- no arc: a 90 deg turn on the spot must not orbit the suit ---")
    with posed({"pelvis.rotateY": 90.0}):
        pm = cmds.xform("pelvis", q=True, ws=True, t=True)
        ps = cmds.xform(NS + "pelvis", q=True, ws=True, t=True)
        off = cmds.getAttr(RETARGET_SET + ".retargetSideOffset")
        check("suit stays beside, not orbiting",
              abs(ps[0] - pm[0] - off) < TOL_CM,
              "dx %.4f vs %.4f" % (ps[0] - pm[0], off))

    print()
    print("--- back at rest: nothing drifted ---")
    settle()
    for bone in ("pelvis", "hand_l", "foot_r"):
        src_rest, tgt_rest = rest.get(bone, (None, None))
        now = wmat(NS + bone)
        if tgt_rest is None:
            tgt_rest = now
        err = angle_between(tgt_rest, now)
        check("rest  %s" % bone, err < TOL_DEG, "err %.5f deg" % err)

    print()
    failed = [r for r in results if not r[1]]
    print("=== %d/%d PASS ===" % (len(results) - len(failed), len(results)))
    for label, _, detail in failed:
        print("  FAILED:", label, detail)
