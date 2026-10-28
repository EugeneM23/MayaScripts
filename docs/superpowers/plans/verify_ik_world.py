"""Standalone gates for Connections' World: an IK hand or foot on a world control (2026-10-28).

    mayapy verify_ik_world.py

mayapy STANDALONE, an empty scene per case, the plugin's Manny_Rig (spec
docs/superpowers/specs/2026-10-28-connections-ik-world-design.md):

A  two Manny_Rigs, the right FK arm keyed alike on 0, 12, 24 under Main travelling 60 cm; the
   first to plain IK, the second to IK with World: a Double knot World on IKArm_R in the
   character's Knots group, keyed on exactly 0, 12, 24, the arm where the plain IK has it on them
   (and the hand where FK had it - an IK elbow does not twist, so the arm's roll is not asked); Main moved 3 cm more and the hand stays, the shoulder goes; the Move
   control moved 2 cm moves the hand 2 cm; one Ctrl+Z takes the press back, redo gives it again; a
   second press refused, plain IK names the W; the W back in Main's space on the same keys, the
   arm kept; W on that IK arm with no switch; FK from world keyed on the keys, the control gone.
   The world control is CONTROLS (2026-10-28): curves, no locator - a Move box, Rotate rings.
B  the right leg switched to IK, its IK control keyed on 0, 12, 24: World on it - no switch, the
   leg where it stood on the keys, the foot stays when Main moves.
C  a highlight 8..16: the switch over the range, the world control ranged (attach 0 / 1 / 1 / 0
   at 7, 8, 16, 17), keyed on 8, 12, 16; FK over the whole take takes it off.
"""
import math
import sys

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

from maya_scenesetup import catalog, character, connections as cx, fkik, ikworld  # noqa: E402
from maya_tools import knots  # noqa: E402
import maya_rigs  # noqa: E402

FAILS = []
COUNT = [0]
KEPT_CM, KEPT_DEG = 0.05, 0.05
CASE = ["-"]
KEYS = [0.0, 12.0, 24.0]


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
    for f in frames if frames is not None else sorted(a):
        for x, y in zip(a[f], b[f]):
            cm, deg = max(cm, (pos(x) - pos(y)).length()), max(deg, ang(x, y))
    return cm, deg


def times(nodes, attrs=None):
    out = set()
    for n in nodes:
        for a in attrs or [None]:
            plug = n + "." + a if a else n
            out.update(round(t, 4) for t in cmds.keyframe(plug, query=True, timeChange=True) or [])
    return sorted(out)


def add(new=True):
    if not new:
        before = set(r.namespace for r in maya_rigs.rigs())
        character.add_character(catalog.character_by_key("Manny_Rig"))
        cmds.select(clear=True)
        return [r for r in maya_rigs.rigs() if r.namespace not in before][0]
    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(min=0, max=24, animationStartTime=0, animationEndTime=24)
    cmds.currentTime(0)
    character.add_character(catalog.character_by_key("Manny_Rig"))
    rig = maya_rigs.rigs()[0]
    cmds.select(clear=True)
    return rig


def node(rig, leaf):
    return cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]


def key(n, attr, t, v):
    cmds.setKeyframe(n, attribute=attr, time=t, value=v)


def keyed_arm(rig):
    """The right FK arm keyed on 0, 12, 24; Main travelling 60 cm forward (keyed on 0 and 24)."""
    for leaf, values in (("FKShoulder_R", ((0, 0, 0), (-20, 30, 40), (10, -15, 70))),
                         ("FKElbow_R", ((0, 0, 0), (0, -50, 0), (0, -80, 0))),
                         ("FKWrist_R", ((0, 0, 0), (20, 10, -15), (-10, 25, 5)))):
        n = node(rig, leaf)
        for t, v in zip(KEYS, values):
            for axis, value in zip("XYZ", v):
                key(n, "rotate" + axis, t, value)
    main = node(rig, "Main")
    key(main, "translateZ", 0, 0.0)
    key(main, "translateZ", 24, 60.0)


def shift_main(rig, cm):
    cmds.keyframe(node(rig, "Main") + ".translateZ", edit=True, relative=True, valueChange=cm)


def knot_ok(top, frames, label, still_turn=False):
    inner = [n for n in knots.nodes_of(top) if n != top]
    gate(knots.kind_of(top) == "double_world" and len(inner) == 1,
         "%s: a Double knot World, Move + Rotate (%s)" % (label, top.split("|")[-1]))
    gate("|Knots|" in top, "%s: in the character's Knots group (%s)" % (label, top))
    t_keys = times([top], ["translateX", "translateY", "translateZ"])
    r_keys = times(inner, ["rotateX", "rotateY", "rotateZ"])
    #  a channel still over the whole take is a plain value, as the switch writes it
    gate(t_keys == frames and r_keys == ([] if still_turn else frames),
         "%s: keyed on exactly %s (Move %s, Rotate %s)" % (label, frames, t_keys, r_keys))
    gate(not times([top], ["rotateX", "rotateY", "rotateZ"]),
         "%s: the Move control carries no rotation" % label)
    shapes = [cmds.nodeType(sh) for n in (top, inner[0])
              for sh in cmds.listRelatives(n, shapes=True, fullPath=True) or []]
    gate(shapes == ["nurbsCurve", "nurbsCurve"] and top.endswith("_worldMove_ctrl")
         and inner[0].endswith("_worldRotate_ctrl"),
         "%s: two controls, curves and no locator (%s, %s: %s)" % (
             label, top.split("|")[-1], inner[0].split("|")[-1], shapes))
    return inner[0]


def case_a():
    CASE[0] = "A"
    print("--- A: the arm")
    plain_rig = add()
    rig = add(new=False)
    keyed_arm(plain_rig)
    keyed_arm(rig)
    arm = fkik.limb(rig, "R")[0]
    plain_arm = fkik.limb(plain_rig, "R")[0]
    before = track(arm.deform, KEYS)
    print("    plain:", cx.switch_arm("R", "IK", rig=plain_rig, highlight=False, world=False))
    plain = track(plain_arm.deform, KEYS)
    cmds.currentTime(0)
    text = cx.switch_arm("R", "IK", rig=rig, highlight=False, world=True)
    print("   ", text)
    #  one Ctrl+Z, before any time change (trap 222)
    cmds.undo()
    gate(fkik.mode_of(fkik.blend_values(arm)) == fkik.FK and not ikworld.limb_knot(arm),
         "one Ctrl+Z takes the World press back (FK, no world control)")
    cmds.redo()
    top = ikworld.limb_knot(arm)
    gate(fkik.mode_of(fkik.blend_values(arm)) == fkik.IK and bool(top),
         "redo gives it again: IK on a world control")
    knot_ok(top, KEYS, "A")
    gate("in world on IKArm_R_worldMove_ctrl, 3 keys (0..24)" in text,
         "the line says it: " + text)
    world = track(arm.deform, KEYS)
    cm, deg = diff(plain, world)
    gate(cm <= 1e-4 and deg <= 1e-3,
         "on the keys the arm stands where the plain IK has it: %.6f cm, %.5f deg" % (cm, deg))
    hand_cm = max((pos(before[f][2]) - pos(world[f][2])).length() for f in KEYS)
    hand_deg = max(ang(before[f][2], world[f][2]) for f in KEYS)
    gate(hand_cm <= 0.06 and hand_deg <= KEPT_DEG,
         "the hand where FK had it: %.4f cm, %.4f deg" % (hand_cm, hand_deg))
    hand = node(rig, "hand_r")
    shoulder = node(rig, "upperarm_r")
    still = track([hand, shoulder], KEYS)
    shift_main(rig, 3.0)
    moved = track([hand, shoulder], KEYS)
    shift_main(rig, -3.0)
    hand_cm = max((pos(still[f][0]) - pos(moved[f][0])).length() for f in KEYS)
    shoulder_cm = min((pos(still[f][1]) - pos(moved[f][1])).length() for f in KEYS)
    gate(hand_cm <= KEPT_CM and shoulder_cm >= 2.5,
         "Main 3 cm on: the hand stays (%.4f cm), the shoulder goes (%.3f cm)" % (hand_cm,
                                                                               shoulder_cm))
    cmds.keyframe(top + ".translateX", edit=True, time=(12, 12), relative=True, valueChange=2.0)
    nudged = track([hand], [12.0])
    cmds.keyframe(top + ".translateX", edit=True, time=(12, 12), relative=True, valueChange=-2.0)
    d = pos(nudged[12.0][0]) - pos(still[12.0][0])
    gate(abs(d.x - 2.0) <= 0.05 and abs(d.y) + abs(d.z) <= 0.05,
         "the Move control +2 cm in X moves the hand (%.4f, %.4f, %.4f)" % (d.x, d.y, d.z))
    again = cx.switch_arm("R", "IK", rig=rig, highlight=False, world=True)
    gate(again == "Arm_R is already IK in world (IKArm_R_worldMove_ctrl)",
         "a second press: " + again)
    plain_ik = cx.switch_arm("R", "IK", rig=rig, highlight=False)
    gate(plain_ik == "Arm_R is already IK, in world - W takes it back into Main's space",
         "plain IK on it names the W: " + plain_ik)
    back = cx.toggle_world("R", rig=rig, highlight=False)
    print("   ", back)
    ik = node(rig, "IKArm_R")
    gate(not ikworld.limb_knot(arm) and not cmds.objExists(top),
         "IK without World: the world control gone")
    gate(times([ik], ["translateX", "rotateX"]) == KEYS,
         "IKArm_R keyed on the world control's keys %s" % times([ik], ["translateX", "rotateX"]))
    cm, deg = diff(world, track(arm.deform, KEYS))
    gate(cm <= KEPT_CM and deg <= KEPT_DEG and "back from world on 3 keys" in back,
         "back in Main's space, the arm kept: %.5f cm, %.4f deg" % (cm, deg))
    gate(not cmds.ls("*_world*_ctrl", long=True), "no world control left")
    text = cx.toggle_world("R", rig=rig, highlight=False)
    print("   ", text)
    top = ikworld.limb_knot(arm)
    gate(bool(top) and "to IK" not in text, "World on an IK arm: a world control, no switch")
    knot_ok(top, KEYS, "A2")
    world = track(arm.deform, KEYS)
    text = cx.switch_arm("R", "FK", rig=rig, highlight=False)
    print("   ", text)
    gate(fkik.mode_of(fkik.blend_values(arm)) == fkik.FK and not ikworld.limb_knot(arm),
         "FK from world: FK, the world control gone")
    fk_keys = times([node(rig, "FKShoulder_R")], ["rotateX"])
    gate(fk_keys == KEYS, "FK keyed on %s" % fk_keys)
    cm, deg = diff(world, track(arm.deform, KEYS))
    gate(cm <= KEPT_CM and deg <= KEPT_DEG, "FK keeps what the world control showed: "
                                            "%.5f cm, %.4f deg" % (cm, deg))


def case_b():
    CASE[0] = "B"
    print("--- B: the leg")
    rig = add()
    leg = fkik.limb(rig, "R", fkik.LEG)[0]
    print("   ", cx.switch_limb("R", "IK", rig=rig, highlight=False, kind=fkik.LEG, world=False))
    gate(fkik.mode_of(fkik.blend_values(leg)) == fkik.IK, "the leg in plain IK")
    ik = node(rig, "IKLeg_R")
    #  in WORLD terms: the IK foot carries its bone's axes (CustomOrient), so its own Y is no "up"
    for t, (up, ahead) in zip(KEYS, ((0.0, 0.0), (15.0, 10.0), (5.0, 5.0))):
        cmds.currentTime(t)
        for ch in ("translateX", "translateY", "translateZ"):
            cmds.setAttr(ik + "." + ch, 0.0)
        cmds.move(0.0, up, ahead, ik, relative=True, worldSpace=True)
        cmds.setKeyframe(ik, attribute=["translateX", "translateY", "translateZ"], time=t)
    key(node(rig, "Main"), "translateZ", 0, 0.0)
    key(node(rig, "Main"), "translateZ", 24, 30.0)
    before = track(leg.deform, KEYS)
    text = cx.switch_limb("R", "IK", rig=rig, highlight=False, kind=fkik.LEG, world=True)
    print("   ", text)
    top = ikworld.limb_knot(leg)
    gate(bool(top) and "to IK" not in text, "World on the IK leg: no switch, a world control")
    knot_ok(top, KEYS, "B", still_turn=True)
    cm, deg = diff(before, track(leg.deform, KEYS))
    gate(cm <= KEPT_CM and deg <= KEPT_DEG, "the leg kept on the keys: %.5f cm, %.4f deg" % (cm,
                                                                                       deg))
    #  frame 12, the foot lifted and the knee bent: at rest (frame 0) the leg is straight and
    #  no IK keeps a foot on its place while the hip goes away from it
    foot = node(rig, "foot_r")
    still = track([foot], [12.0])
    shift_main(rig, 3.0)
    moved = track([foot], [12.0])
    foot_cm = (pos(still[12.0][0]) - pos(moved[12.0][0])).length()
    gate(foot_cm <= KEPT_CM, "Main 3 cm on: the lifted foot stays (%.4f cm)" % foot_cm)
    text = cx.switch_arm("R", "IK", rig=rig, highlight=False)
    print("    the arm, World off:", text)
    gate(not ikworld.limb_knot(fkik.limb(rig, "R")[0]), "World off: the arm in plain IK")
    worlds = []
    cx._limb_modes(rig, fkik.LEG, worlds)
    gate(worlds == ["R"], "the card lights the right leg's W (%s)" % worlds)


def case_c():
    CASE[0] = "C"
    print("--- C: a range")
    plain_rig = add()
    rig = add(new=False)
    keyed_arm(plain_rig)
    keyed_arm(rig)
    arm = fkik.limb(rig, "R")[0]
    cx.switch_arm("R", "IK", rig=plain_rig, highlight=(8.0, 17.0), world=False)
    before = track(fkik.limb(plain_rig, "R")[0].deform, [8.0, 12.0, 16.0])
    cmds.currentTime(0)
    text = cx.switch_arm("R", "IK", rig=rig, highlight=(8.0, 17.0), world=True)
    print("   ", text)
    top = ikworld.limb_knot(arm)
    gate(bool(top) and knots.span_of(top) == (7.0, 17.0, True),
         "the world control ranged over 7..17 (%s)" % (knots.span_of(top),))
    attach = list(zip(cmds.keyframe(top + ".attach", query=True, timeChange=True) or [],
                      cmds.keyframe(top + ".attach", query=True, valueChange=True) or []))
    gate([(round(t), round(v, 3)) for t, v in attach] == [(7, 0.0), (8, 1.0), (16, 1.0), (17, 0.0)],
         "attach 0 / 1 / 1 / 0 at 7, 8, 16, 17 (%s)" % attach)
    knot_ok(top, [8.0, 12.0, 16.0], "C")
    cm, deg = diff(before, track(arm.deform, [8.0, 12.0, 16.0]))
    gate(cm <= 1e-4 and deg <= 1e-3, "inside the range the arm where the plain IK has it: "
                                      "%.6f cm, %.5f deg" % (cm, deg))
    blend = cmds.keyframe(arm.blend, query=True, valueChange=True) or []
    gate(blend and min(blend) == 0.0 and max(blend) == 10.0, "the blend IK only in the range")
    text = cx.switch_arm("R", "FK", rig=rig, highlight=False)
    print("   ", text)
    gate(not ikworld.limb_knot(arm) and fkik.mode_of(fkik.blend_values(arm)) == fkik.FK,
         "FK over the whole take: FK, the world control gone")


for case in (case_a, case_b, case_c):
    try:
        case()
    except Exception:
        import traceback
        traceback.print_exc()
        FAILS.append((CASE[0], "raised"))
print("%d gates, %d failed: %s" % (COUNT[0], len(FAILS), FAILS))
