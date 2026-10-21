"""Connections' weapon Aim Mode and Default, and the Pose Library onto either (2026-10-21) - mayapy
standalone.

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_weapon_aim_mode.py [out.txt]

A Manny_Rig whose right shoulder turns over 0..20 (keys 0, 20) with a Long Sword in its right
hand keyed on 0, 8, 20 (translate and rotate).

  enter    Aim Mode: the sword on its own place and turn on its keys, the controllers keyed on
           exactly 0, 8, 20, the sword's rotate driven, one Ctrl+Z giving its curves back.
  target   the target moved: the blade points at it.
  leave    Default: the rotate keyed on 0, 8, 20 again, the sword where Aim Mode showed it on the
           keys, nothing of the aim left.
  pose     a whole card saved in Default loads in Aim Mode (weapon_r on the card's place in the
           hand), one saved in Aim Mode loads in Default; an animation card of 0..20 onto a
           second rig in Aim Mode on every frame.

Not here: a parent change in Aim Mode (OverRig's parent_in/out need a GUI Maya).
Spec: docs/superpowers/specs/2026-10-21-connections-weapon-aim-design.md
"""
import io
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.api.OpenMaya as om  # noqa: E402
import maya.cmds as cmds  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("AIM_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_rigs  # noqa: E402
from maya_scenesetup import bonedrive, catalog, character, connections, equip  # noqa: E402
from maya_scenesetup import weaponaim  # noqa: E402
from maya_poselib import animapply, animcapture, apply, capture  # noqa: E402
from maya_poselib import posemath as pm  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []
TOL = 1e-3
KEYS = (0, 8, 20)


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


def off(a, b):
    return max((pm.position(a) - pm.position(b)).length(), pm.angle(a, b))


def rel(a, b):
    return pm.rigid(a) * pm.rigid(b).inverse()


def add(key):
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    return [r for r in maya_rigs.rigs() if r.namespace not in before][0]


def bone(root, name):
    for j in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or []):
        if j.split("|")[-1].split(":")[-1] == name:
            return j
    return None


def key_times(node, attrs):
    times = set()
    for a in attrs:
        for t in cmds.keyframe(node + "." + a, query=True, timeChange=True) or []:
            times.add(round(t, 4))
    return sorted(times)


def make_rig(sword_key="LongSword_02"):
    rig = add("Manny_Rig")
    root = rig.skeleton_root
    say(equip.to_hand(root, "R", catalog.by_key(sword_key)))
    sword = bonedrive.driving_weapon(bone(root, "weapon_r"))
    shoulder = maya_rigs.node(rig, "FKShoulder_R")
    base = cmds.getAttr(shoulder + ".rotateZ")
    cmds.setKeyframe(shoulder, attribute="rotateZ", time=0, value=base)
    cmds.setKeyframe(shoulder, attribute="rotateZ", time=20, value=base + 35)
    return rig, root, sword


def key_sword(sword):
    for ch in ("translate", "rotate"):
        for a in "XYZ":
            cmds.cutKey(sword + "." + ch + a, clear=True)
    values = {0: ((0, 0, 0), (0, 0, 0)), 8: ((3, -2, 1), (25, -10, 15)), 20: ((-2, 1, 4), (-20, 30, 5))}
    for t, (tr, ro) in values.items():
        for a, v in zip("XYZ", tr):
            cmds.setKeyframe(sword, attribute="translate" + a, time=t, value=v)
        for a, v in zip("XYZ", ro):
            cmds.setKeyframe(sword, attribute="rotate" + a, time=t, value=v)


def worlds(node, frames):
    out = {}
    for t in frames:
        evaluate(t)
        out[t] = W(node)
    return out


def main():
    cmds.playbackOptions(minTime=0, maxTime=20, animationStartTime=0, animationEndTime=20)
    rig, root, sword = make_rig()
    key_sword(sword)
    go(5)
    before = worlds(sword, KEYS)
    rot_keys = key_times(sword, ("rotateX", "rotateY", "rotateZ"))

    # ---- enter (its undo straight after the press: a time change is an undo step, trap 222)
    connections.aim_mode(rig, sword, on=True)
    cmds.undo()
    gate("enter: one Ctrl+Z gives the rotate curves back, no aim",
         weaponaim.group_of(sword) is None and
         key_times(sword, ("rotateX", "rotateY", "rotateZ")) == rot_keys)
    text = connections.aim_mode(rig, sword, on=True)
    say("   enter:", text)
    group = weaponaim.group_of(sword)
    gate("enter: an aim group with two controllers", group and
         sorted(weaponaim.controllers(group)) == ["target", "up"])
    made = weaponaim.controllers(group)
    gate("enter: the controllers keyed on the sword's own keys",
         key_times(made["target"], ("translateX", "translateY", "translateZ")) == list(KEYS),
         key_times(made["target"], ("translateX", "translateY", "translateZ")))
    worst = max(off(W_, before[t]) for t, W_ in worlds(sword, KEYS).items())
    gate("enter: the sword stands where it stood on every key", worst < TOL, "%.2e" % worst)
    gate("enter: the sword's rotate driven, no rotate keys",
         not key_times(sword, ("rotateX", "rotateY", "rotateZ")) and
         bool(cmds.listConnections(sword + ".rotateX", source=True, destination=False)))
    gate("enter: the group under the rig's Main (2026-10-21)",
         cmds.listRelatives(group, parent=True, fullPath=True)[0] == weaponaim.home_of(sword),
         group)
    gate("enter: the sword's frame said in the card", weaponaim.is_aimed(sword))
    ctrls = weaponaim.controllers(weaponaim.group_of(sword))
    gate("enter: no lines (2026-10-21), both controllers diamonds",
         not [c for c in cmds.listRelatives(weaponaim.group_of(sword), children=True,
                                            fullPath=True) or []
              if cmds.attributeQuery(weaponaim.LINE_MARKER, node=c, exists=True)]
         and all(len(cmds.getAttr(cmds.listRelatives(c, shapes=True, fullPath=True)[0]
                                  + ".cv[*]")) == len(weaponaim.diamond(1.0))
                 for c in ctrls.values()))
    #  Main moved: the controllers ride it
    evaluate(8)
    main = weaponaim.home_of(sword)
    t0 = cmds.xform(ctrls["target"], query=True, worldSpace=True, translation=True)
    was = cmds.getAttr(main + ".translateX")
    cmds.setAttr(main + ".translateX", was + 10)
    evaluate(8)
    t1 = cmds.xform(ctrls["target"], query=True, worldSpace=True, translation=True)
    cmds.setAttr(main + ".translateX", was)
    evaluate(8)
    gate("enter: Main +10 moves the target 10", abs(t1[0] - t0[0] - 10) < 1e-3,
         "%.4f" % (t1[0] - t0[0]))
    up_local = om.MPoint(*cmds.xform(ctrls["up"], query=True, worldSpace=True,
                                     translation=True)) * W(sword).inverse()
    gate("enter: the up close beside the sword",
         om.MVector(up_local).length() < 0.3 * weaponaim.stored_vectors(
             weaponaim.group_of(sword))[2] + TOL, "%.1f cm" % om.MVector(up_local).length())
    gate("enter: a second press refused", "already" in connections.aim_mode(rig, sword, on=True))
    made = weaponaim.controllers(weaponaim.group_of(sword))

    # ---- target
    aim_v, up_v, d_aim, d_up = weaponaim.stored_vectors(weaponaim.group_of(sword))
    evaluate(8)
    p = cmds.xform(made["target"], query=True, worldSpace=True, translation=True)
    cmds.setKeyframe(made["target"], attribute="translateY", time=8, value=cmds.getAttr(
        made["target"] + ".translateY") + 15)
    evaluate(8)
    w = W(sword)
    axis = om.MVector(*aim_v) * w
    tgt = om.MVector(*cmds.xform(made["target"], query=True, worldSpace=True, translation=True))
    to = tgt - om.MVector(pm.position(w))
    import math
    angle = math.degrees(axis.angle(to))
    gate("target: the blade points at the moved target", angle < 0.01, "%.4f deg" % angle)
    aimed_now = worlds(sword, KEYS)

    # ---- leave
    text = connections.aim_mode(rig, sword, on=False)
    say("   leave:", text)
    gate("leave: nothing of the aim left", weaponaim.group_of(sword) is None and
         not cmds.ls(type="aimConstraint"))
    gate("leave: the rotate keyed on the controllers' keys",
         key_times(sword, ("rotateX", "rotateY", "rotateZ")) == list(KEYS),
         key_times(sword, ("rotateX", "rotateY", "rotateZ")))
    worst = max(off(W_, aimed_now[t]) for t, W_ in worlds(sword, KEYS).items())
    gate("leave: the sword as Aim Mode showed it on every key", worst < TOL, "%.2e" % worst)

    # ---- pose: saved in Default, loaded in Aim Mode
    hand = bone(root, "hand_r")
    wr = bone(root, "weapon_r")
    evaluate(8)
    card, note = capture.build_pose([root], frame=8)
    gate("pose: a whole card saved in Default", card is not None, note)
    truth = rel(W(wr), W(hand))
    cmds.setKeyframe(sword, attribute="rotateX", time=8, value=cmds.getAttr(sword + ".rotateX")
                     + 40)
    connections.aim_mode(rig, sword, on=True)
    evaluate(8)
    gate("pose: the scene moved off the card first", off(rel(W(wr), W(hand)), truth) > 1.0)
    ok, text = apply.apply_onto(card, root)
    say("   apply in Aim Mode:", text)
    evaluate(8)
    worst = off(rel(W(wr), W(hand)), truth)
    gate("pose: Default card in Aim Mode - weapon_r on the card's place", ok and worst < TOL,
         "%.2e" % worst)
    gate("pose: still Aim Mode, the controllers keyed", weaponaim.is_aimed(sword))

    # saved in Aim Mode, loaded in Default
    card2, note = capture.build_pose([root], frame=8)
    truth2 = rel(W(wr), W(hand))
    connections.aim_mode(rig, sword, on=False)
    cmds.setKeyframe(sword, attribute="rotateY", time=8, value=cmds.getAttr(sword + ".rotateY")
                     - 50)
    evaluate(8)
    ok, text = apply.apply_onto(card2, root)
    say("   apply in Default:", text)
    evaluate(8)
    worst = off(rel(W(wr), W(hand)), truth2)
    gate("pose: Aim Mode card in Default - weapon_r on the card's place", ok and worst < TOL,
         "%.2e" % worst)

    # ---- an animation saved in Default onto a second rig in Aim Mode
    header, frames, note = animcapture.build_animation([root], start=0, end=20)
    gate("anim: card saved", header is not None, note)
    src = dict((t, rel(W(wr), W(hand))) for t in range(0, 21) if evaluate(t) is None)
    rig2, root2, sword2 = make_rig("LongSword_02")
    key_sword(sword2)
    connections.aim_mode(rig2, sword2, on=True)
    go(0)
    ok, text = animapply.apply_onto(header, frames, root2)
    say("   anim in Aim Mode:", text)
    wr2, hand2 = bone(root2, "weapon_r"), bone(root2, "hand_r")
    worst = 0.0
    for t in range(0, 21):
        evaluate(t)
        worst = max(worst, off(rel(W(wr2), W(hand2)), src[t]))
    gate("anim: weapon_r on the card's on every frame, in Aim Mode", ok and worst < TOL,
         "%.2e" % worst)
    gate("anim: still Aim Mode", weaponaim.is_aimed(sword2))
    # and back to Default: the take kept on its keys
    kept = worlds(sword2, range(0, 21))
    connections.aim_mode(rig2, sword2, on=False)
    worst = max(off(W_, kept[t]) for t, W_ in worlds(sword2, range(0, 21)).items())
    gate("anim: Default after it keeps the take on every key (keyed on every frame)",
         worst < TOL, "%.2e" % worst)


try:
    main()
except Exception:                                            # noqa: BLE001
    say(traceback.format_exc())
    RESULTS.append(False)
say("%d of %d gates failed" % (RESULTS.count(False), len(RESULTS)))
os._exit(0)
