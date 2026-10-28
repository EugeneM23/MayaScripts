"""Connections' Camera tab - parents, Position only, Aim Mode - standalone (2026-10-28).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_camera_tab.py [out.txt] [rig key]

The animator: «Во вкладке конекшен нужно добавить раздел для камер. В разделе для камеры нужно
реализовать такой же aim как для оружия, и возможность переподвязывания камеры к разным
контроллерам. Подвязывание должно быть с опцией которая может привязать только позицию как поинт
констрейн».

A Manny_Rig (default) whose Main, Root_ctrl, spine, neck and head are keyed on 0 / 10 / 20; 1P Setup
(which makes the camera, its control under the chest), both layers on; the control sent to Main and
keyed on 0 / 10 / 20 with a motion of its own (moved and turned).

  aim enter / leave / undo   Aim Mode on the keyed control: the camera on its keys to 1e-6, the
                             controllers keyed on exactly 0 / 10 / 20, one Ctrl+Z; Default back to
                             1e-4 on every frame; one Ctrl+Z of a parent press.
  parents                    Main -> Head -> Head (position) -> Root (position) -> Chest (position)
                             -> World -> Main: the camera's world matrix on every frame 0..20 to
                             1e-4 cm / deg; Position only rotates with Main; the follow group gone.
  direct move                1P's own `move_control(control, chest, "Chest")` out of a follow group.
  aim + parent               Aim Mode (the control re-keyed 0 / 10 / 20), then Main -> Head -> Head
                             (position) -> Main: still aimed, the group beside the control, the
                             camera on every key where it was; the controllers keep their key times
                             plus only fill keys; every frame 0..20 within 0.1 deg of before the move.
  chest gone                 a camera following the chest's position, the chest baked off.
  pose card                  a fresh rig: a whole-body card from frame 10 applied with the camera on
                             Head, in Position only on Head, in Aim Mode under Main - camera_root on
                             the card's place (and in Aim Mode in Position only on Head).

Spec: docs/superpowers/specs/2026-10-28-connections-camera-tab-design.md
"""
import io
import math
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.api.OpenMaya as om  # noqa: E402
import maya.cmds as cmds  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("CAMTAB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_rigs  # noqa: E402
from maya_scenesetup import aimcore, camera, cameraaim, catalog, character, rootcontrol  # noqa: E402
from maya_tools import firstperson as fp, knots  # noqa: E402
from maya_poselib import apply, capture, scene  # noqa: E402
from maya_poselib import posemath as pm  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RIG_KEY = sys.argv[2] if len(sys.argv) > 2 else "Manny_Rig"
RESULTS = []
TOL = 1e-4
TIGHT = 1e-6
KEYS = (0, 10, 20)
FRAMES = list(range(0, 21))
#  aim + parent between the keys: the controllers are keyed again on their own key times in the new
#  parent's space and filled where the control turns more than aimcore.TOLERANCE (0.1 deg) or moves
#  more than aimcore.FILL_CM off its track from before the move. The camera stands in the control at
#  a pure turn (camera.AXIS_OFFSET), so it turns by the control's angle and moves with its place:
#  the fill's own bounds, plus 1e-5 deg for this script's acos-based measure (floor ~3e-6 deg)
BETWEEN_DEG = aimcore.TOLERANCE + 1e-5
BETWEEN_CM = aimcore.FILL_CM
FILLS = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))
    return bool(ok)


def W(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def go(t):
    cmds.currentTime(t, update=True)


def evaluate(t):
    go(t + 1)
    go(t)


def euler(m):
    r = om.MTransformationMatrix(m).rotation()
    return [math.degrees(v) for v in (r.x, r.y, r.z)]


def turn(a, b):
    return aimcore.turn_between(euler(a), euler(b))


def fine_turn(a, b):
    """Degrees between two matrices' rotations without acos's floor near 1 (~1.7e-6 deg), for the
    1e-6 gate."""
    qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    d = qa.inverse() * qb
    v = math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    return math.degrees(2.0 * math.atan2(v, abs(d.w)))


def moved(a, b):
    return max(abs(a[12 + i] - b[12 + i]) for i in range(3))


def parent_of(n):
    p = cmds.listRelatives(n, parent=True, fullPath=True)
    return p[0] if p else None


def key_times(node, attrs):
    times = set()
    for a in attrs:
        for t in cmds.keyframe(node + "." + a, query=True, timeChange=True) or []:
            times.add(round(t, 4))
    return sorted(times)


def curves(node, attrs):
    out = {}
    for a in attrs:
        out[a] = list(zip(cmds.keyframe(node + "." + a, query=True, timeChange=True) or [],
                          cmds.keyframe(node + "." + a, query=True, valueChange=True) or []))
    return out


ROT = ("rotateX", "rotateY", "rotateZ")
TR = ("translateX", "translateY", "translateZ")


def follow_groups():
    return cmds.ls("*." + camera.FOLLOW_MARKER, recursive=True, objectsOnly=True, long=True) or []


def aim_groups():
    return aimcore.groups(cameraaim.KIND)


def key_body(rig):
    deltas = {"Main": (("translateX", (0, 30, 60)), ("translateZ", (0, 10, -20)),
                       ("rotateY", (0, 25, -15))),
              "FKSpine1_M": (("rotateX", (0, 10, -8)),),
              "FKNeck_M": (("rotateY", (0, 20, -25)),),
              "FKHead_M": (("rotateX", (0, 15, -10)), ("rotateZ", (0, -12, 18)))}
    for leaf_name, chans in deltas.items():
        node = maya_rigs.node(rig, leaf_name)
        if not cmds.objExists(node):
            say("   (no %s)" % leaf_name)
            continue
        for attr, values in chans:
            base = cmds.getAttr(node + "." + attr)
            for t, d in zip(KEYS, values):
                cmds.setKeyframe(node, attribute=attr, time=t, value=base + d)
    rc = rootcontrol.ensure(rig)[0]
    for attr, values in (("translateX", (0, 5, -4)), ("translateZ", (0, 8, 3))):
        base = cmds.getAttr(rc + "." + attr)
        for t, d in zip(KEYS, values):
            cmds.setKeyframe(rc, attribute=attr, time=t, value=base + d)


def key_camera(control):
    """The control's own motion on 0 / 10 / 20 (moved and turned), its old keys cut."""
    go(0)
    base = dict((a, cmds.getAttr(control + "." + a)) for a in TR + ROT)
    for a in TR + ROT:
        cmds.cutKey(control + "." + a, clear=True)
    values = {0: ((0, 0, 0), (0, 0, 0)), 10: ((12, -6, 20), (15, -25, 8)),
              20: ((-8, 10, 35), (-10, 30, -12))}
    for t, (tr, ro) in values.items():
        for a, v in zip(TR, tr):
            cmds.setKeyframe(control, attribute=a, time=t, value=base[a] + v)
        for a, v in zip(ROT, ro):
            cmds.setKeyframe(control, attribute=a, time=t, value=base[a] + v)


def add_rig():
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(RIG_KEY))
    cmds.select(clear=True)
    return [r for r in maya_rigs.rigs() if r.namespace not in before][0]


def cam_of(bone):
    return camera.camera_for(bone)


def track(bone, frames=FRAMES):
    out = {}
    for t in frames:
        evaluate(t)
        out[t] = W(cam_of(bone))
    return out


def worst(a, b):
    cm = deg = 0.0
    for t in a:
        cm = max(cm, moved(a[t], b[t]))
        deg = max(deg, turn(a[t], b[t]))
    return cm, deg


def part_a():
    cmds.file(new=True, force=True)
    cmds.playbackOptions(minTime=0, maxTime=20, animationStartTime=0, animationEndTime=20)
    rig = add_rig()
    key_body(rig)
    bone = cmds.ls(maya_rigs.node(rig, "camera_root"), long=True)[0]
    main = cmds.ls(rig.main, long=True)[0]

    go(5)
    cmds.select(maya_rigs.node(rig, "FKElbow_R"))
    say("   1P Setup:", fp.setup())
    for layer in fp.setup_layers(rig.namespace):
        cmds.setAttr(layer + ".mute", 0)
    chest = fp.chest_of(rig)
    gate("scene: 1P Setup made the chest and a camera under it",
         bool(chest) and parent_of(camera.control_for(bone)) == chest, chest)
    say("   ", camera.set_parent(bone, "Main"))
    control = camera.control_for(bone)
    key_camera(control)
    control = camera.control_for(bone)
    gate("scene: the control under Main keyed on exactly 0/10/20",
         parent_of(control) == main and key_times(control, TR + ROT) == list(KEYS),
         key_times(control, TR + ROT))

    # ---------------------------------------------------------------- 3 aim enter (+ undo, 8)
    keyed = track(bone, KEYS)
    rot_curves = curves(control, ROT)
    say("   enter:", cameraaim.enter(control))
    cmds.undo()
    control = camera.control_for(bone)
    gate("undo: one Ctrl+Z of Aim Mode gives the rotate curves back, no aim",
         not cameraaim.is_aimed(control) and not aim_groups()
         and curves(control, ROT) == rot_curves)
    line = cameraaim.enter(control)
    say("   enter:", line)
    control = camera.control_for(bone)
    group = cameraaim.group_of(control)
    made = cameraaim.controllers(group) if group else {}
    gate("aim enter: aimed, a group beside the control with two controllers",
         cameraaim.is_aimed(control) and group and parent_of(group) == parent_of(control)
         and sorted(made) == ["target", "up"], sorted(made))
    gate("aim enter: the controllers' translate keys exactly 0/10/20",
         all(key_times(c, TR) == list(KEYS) for c in made.values()),
         [key_times(c, TR) for c in made.values()])
    now = track(bone, KEYS)
    cm = max(moved(now[t], keyed[t]) for t in KEYS)
    deg = max(fine_turn(now[t], keyed[t]) for t in KEYS)
    gate("aim enter: the camera on its keys to 1e-6", cm < TIGHT and deg < TIGHT,
         "%.2e cm %.2e deg" % (cm, deg))
    gate("aim enter: the control's rotate driven, not keyed",
         not key_times(control, ROT) and bool(cmds.listConnections(
             control + ".rotateX", source=True, destination=False)))
    say("   kind of the target:", scene._kind(made.get("target")),
        "of the up:", scene._kind(made.get("up")))
    gate("kind: the camera aim controllers are CAMERA",
         scene._kind(made["target"]) == scene.CAMERA and scene._kind(made["up"]) == scene.CAMERA)

    # ---------------------------------------------------------------- 4 aim leave
    aimed = track(bone)
    say("   leave:", cameraaim.leave(control))
    control = camera.control_for(bone)
    cm, deg = worst(aimed, track(bone))
    gate("aim leave: every frame 0..20 as Aim Mode showed it", cm < TOL and deg < TOL,
         "%.2e cm %.2e deg" % (cm, deg))
    gate("aim leave: nothing of the aim left", not aim_groups() and not cameraaim.is_aimed(control)
         and not cmds.ls(type="aimConstraint"))

    # ---------------------------------------------------------------- 8 undo of a parent press
    raw = track(bone)
    curv = curves(control, TR + ROT)
    say("   ", camera.set_parent(bone, "Head", True))
    cmds.undo()
    control = camera.control_for(bone)
    gate("undo: one Ctrl+Z of Head (position) puts the control back under Main",
         parent_of(control) == main and not follow_groups() and not camera.is_position_only(control)
         and camera.parent_choice(control) == "Main" and curves(control, TR + ROT) == curv)

    # ---------------------------------------------------------------- 1 parents, 2 follow
    head = cmds.ls(maya_rigs.node(rig, "FKHead_M"), long=True)[0]
    rc = cmds.ls(rootcontrol.find(rig), long=True)[0]
    for bone_choice, position in (("Main", False), ("Head", False), ("Head", True),
                                  ("Root", True), ("Chest", True), ("World", False),
                                  ("Main", False)):
        line = camera.set_parent(bone, bone_choice, position)
        control = camera.control_for(bone)
        follow = camera.follow_of(control)
        want = {"Main": main, "Head": head, "Root": rc, "Chest": chest}.get(bone_choice)
        if position:
            cons = cmds.listRelatives(follow, children=True, type="pointConstraint",
                                      fullPath=True) or [] if follow else []
            targets = [cmds.ls(t, long=True)[0] for t in
                       cmds.pointConstraint(cons[0], query=True, targetList=True)] if cons else []
            placed = bool(follow) and parent_of(follow) == main and targets == [want] \
                and camera.is_position_only(control)
        elif bone_choice == "World":
            placed = parent_of(control) != main and not follow
        else:
            placed = parent_of(control) == want and not follow \
                and not camera.is_position_only(control)
        cm, deg = worst(raw, track(bone))
        gate("parents: %s%s - placed, the camera kept on every frame" % (
             bone_choice, " (position)" if position else ""),
             placed and camera.parent_choice(control) == bone_choice and cm < TOL and deg < TOL,
             "%.2e cm %.2e deg | %s" % (cm, deg, line))
        if position and bone_choice == "Head":
            cons = cmds.listRelatives(follow, children=True, type="pointConstraint",
                                      fullPath=True) or []
            rel_worst = 0.0
            for t in FRAMES:
                evaluate(t)
                local = om.MMatrix(cmds.xform(control, query=True, matrix=True, objectSpace=True))
                rel_worst = max(rel_worst, turn(W(control), local * W(main)))
            gate("follow: Camera_follow under Main, one pointConstraint, the control turning "
                 "with Main", len(follow_groups()) == 1 and len(cons) == 1 and rel_worst < TOL,
                 "%.2e deg" % rel_worst)
        if bone_choice == "World":
            gate("follow: after World no follow group", not follow_groups(), follow_groups())

    # ---------------------------------------------------------------- direct move_control
    say("   ", camera.set_parent(bone, "Head", True))
    control = camera.control_for(bone)
    control = camera.move_control(control, chest, "Chest")
    cm, deg = worst(raw, track(bone))
    gate("direct move: 1P's move_control out of a follow group drops it",
         not follow_groups() and not camera.is_position_only(control)
         and parent_of(control) == chest and cm < TOL and deg < TOL,
         "%.2e cm %.2e deg" % (cm, deg))
    say("   ", camera.set_parent(bone, "Main"))

    # ---------------------------------------------------------------- 5 aim + parent
    control = camera.control_for(bone)
    key_camera(control)         # the parent moves above baked it on every frame: keys 0/10/20 again
    say("   enter:", cameraaim.enter(control))
    aimed = track(bone)
    made = cameraaim.controllers(cameraaim.group_of(control))
    before = dict((role, key_times(c, TR)) for role, c in made.items())
    gate("aim + parent: the controllers keyed on exactly 0/10/20 before the moves",
         all(v == list(KEYS) for v in before.values()), before)
    previous = aimed
    held = before
    for bone_choice, position in (("Head", False), ("Head", True), ("Main", False)):
        label = "%s%s" % (bone_choice, " (position)" if position else "")
        line = camera.set_parent(bone, bone_choice, position)
        control = camera.control_for(bone)
        group = cameraaim.group_of(control)
        made = cameraaim.controllers(group) if group else {}
        after = dict((role, key_times(c, TR)) for role, c in made.items())
        now = track(bone)
        cm, deg = worst(dict((t, aimed[t]) for t in KEYS), dict((t, now[t]) for t in KEYS))
        gate("aim + parent: %s - still aimed, the group beside the control, the camera on "
             "every key" % label,
             cameraaim.is_aimed(control) and bool(group) and parent_of(group) == parent_of(control)
             and cm < TOL and deg < TOL,
             "%.2e cm %.2e deg | %s" % (cm, deg, line))
        extra = dict((r, [t for t in v if t not in held[r]]) for r, v in after.items())
        fills = extra.get("target", [])
        gate("aim + parent: %s - the controllers keep their key times, plus only fill keys"
             % label,
             sorted(after) == ["target", "up"]
             and all(set(held[r]) <= set(after[r]) for r in held)
             and extra.get("up") == fills
             and all(t == int(t) and 0 < t < 20 and t not in KEYS for t in fills),
             "%d fill keys %s | %s -> %s" % (len(fills), fills,
                                             dict((r, len(v)) for r, v in held.items()),
                                             dict((r, len(v)) for r, v in after.items())))
        FILLS.append((label, len(fills)))
        held = after
        cm, deg = worst(aimed, now)
        step_cm, step_deg = worst(previous, now)
        gate("aim + parent: %s - every frame 0..20 within %g deg / %g cm of before this move"
             % (label, BETWEEN_DEG, BETWEEN_CM), step_cm < BETWEEN_CM and step_deg < BETWEEN_DEG,
             "this move %.2e cm %.2e deg (since before the first move %.2e cm %.2e deg)"
             % (step_cm, step_deg, cm, deg))
        previous = now
        if position:
            follow = camera.follow_of(control)
            gate("aim + parent: the aim group under Camera_follow",
                 bool(follow) and parent_of(group) == follow, parent_of(group))
            say("   kind of the follow group:", scene._kind(follow))
            gate("kind: the follow group is CAMERA", scene._kind(follow) == scene.CAMERA)
    say("   leave:", cameraaim.leave(camera.control_for(bone)))

    # ---------------------------------------------------------------- 6 chest gone
    say("   ", camera.set_parent(bone, "Chest", True))
    raw = track(bone)
    say("   bake:", knots.bake([chest]))
    control = camera.control_for(bone)
    cm, deg = worst(raw, track(bone))
    gate("chest gone: the control back under Main, no follow group, motion kept",
         not fp.chest_of(rig) and parent_of(control) == main and not follow_groups()
         and not camera.is_position_only(control) and cm < TOL and deg < TOL,
         "%.2e cm %.2e deg" % (cm, deg))


def part_b():
    cmds.file(new=True, force=True)
    cmds.playbackOptions(minTime=0, maxTime=20, animationStartTime=0, animationEndTime=20)
    rig = add_rig()
    key_body(rig)
    root = rig.skeleton_root
    bone = cmds.ls(maya_rigs.node(rig, "camera_root"), long=True)[0]
    say("   setup:", camera.setup(bone, 0, 20))
    key_camera(camera.control_for(bone))
    say("   ", camera.set_parent(bone, "Head"))
    evaluate(10)
    card, note = capture.build_pose([root], frame=10)
    gate("pose: a whole card saved at 10 with the camera on Head", card is not None, note)
    truth = pm.rigid(W(bone)) * pm.rigid(W(root)).inverse()

    def place():
        return pm.rigid(W(bone)) * pm.rigid(W(root)).inverse()

    for label, frame, prepare in (
            ("on Head", 15, lambda: None),
            ("Position only on Head", 5, lambda: say("   ", camera.set_parent(bone, "Head", True))),
            ("Aim Mode under Main", 18, lambda: (say("   ", camera.set_parent(bone, "Main")),
                                                say("   enter:", cameraaim.enter(
                                                    camera.control_for(bone))))),
            ("Aim Mode in Position only on Head", 12,
             lambda: say("   ", camera.set_parent(bone, "Head", True)))):
        prepare()
        evaluate(frame)
        before = place()
        ok, text = apply.apply_onto(card, root)
        say("   apply %s at %d: %s" % (label, frame, text))
        evaluate(frame)
        got = place()
        cm, deg = moved(got, truth), turn(got, truth)
        gate("pose: %s - camera_root on the card's place" % label,
             ok and moved(before, truth) > 1.0 and cm < TOL and deg < TOL,
             "%.2e cm %.2e deg (off %.1f cm before)" % (cm, deg, moved(before, truth)))
    control = camera.control_for(bone)
    gate("pose: still Aim Mode after the card", cameraaim.is_aimed(control))


try:
    part_a()
except Exception:                                            # noqa: BLE001
    say(traceback.format_exc())
    RESULTS.append(False)
try:
    part_b()
except Exception:                                            # noqa: BLE001
    say(traceback.format_exc())
    RESULTS.append(False)
say("   fill keys per move:", FILLS)
say("%d/%d" % (RESULTS.count(True), len(RESULTS)))
if OUT is not None:
    OUT.close()
os._exit(0)
