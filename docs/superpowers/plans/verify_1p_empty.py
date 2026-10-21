"""1P Setup and the camera on a rig with NO keys (2026-10-21), mayapy standalone.

    mayapy verify_1p_empty.py [rig key, default Manny_Rig]

The animator: «скрипт сейчас работает по разному когда есть анимация и когда ее нету. Если делаю
наши действия на пустом риге без ключей то много чего не работает». A rig just added, nothing
keyed; the right arm switched to IK; a sword in the right hand in Aim Mode; then every press:
Camera Setup, the camera's four parents, 1P Setup, the chest's layers and display layers, the
IK arms in the chest, Aim Mode after 1P, the chest baked off, Camera Setup's teardown - each
must work and leave the rig standing where it stood.
"""

import math
import sys
import traceback

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
RIG_KEY = sys.argv[1] if len(sys.argv) > 1 else "Manny_Rig"

from maya_scenesetup import (bonedrive, camera, catalog, character, connections as cx,  # noqa
                             equip, fkik, rootcontrol, weaponaim)
from maya_tools import firstperson as fp, knots  # noqa: E402
import maya_rigs  # noqa: E402

FAILS = []
COUNT = [0]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    if not ok:
        FAILS.append(msg)


def wm(n):
    return om.MMatrix(cmds.xform(n, query=True, matrix=True, worldSpace=True))


def apart(a, b):
    d = max(abs(a[12 + i] - b[12 + i]) for i in range(3))
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    r = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    dot = min(1.0, abs(q.x * r.x + q.y * r.y + q.z * r.z + q.w * r.w))
    return d, math.degrees(2 * math.acos(dot))


def press(name, fn):
    try:
        out = fn()
        print("    %s: %s" % (name, out))
        return out
    except Exception:
        traceback.print_exc()
        gate(False, "%s raised" % name)
        return None


def parent_of(n):
    p = cmds.listRelatives(n, parent=True, fullPath=True)
    return p[0] if p else None


cmds.file(new=True, force=True)
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)
cmds.playbackOptions(min=0, max=30, animationStartTime=0, animationEndTime=30)
character.add_character(catalog.character_by_key(RIG_KEY))
rig = maya_rigs.rigs()[0]
N = lambda leaf: cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]  # noqa: E731
BODY = ["pelvis", "spine_03", "head", "hand_r", "hand_l", "foot_l", "camera_root"]
BODY = [b for b in BODY if cmds.ls(maya_rigs.node(rig, b))]


def pose():
    cmds.currentTime(10)
    return dict((b, wm(N(b))) for b in BODY)


def same(a, b, what, tol=0.05):
    cm = max(apart(a[k], b[k])[0] for k in a)
    deg = max(apart(a[k], b[k])[1] for k in a)
    gate(cm < tol and deg < tol * 2, "%s: the rig stands where it stood (%.4f cm, %.4f deg)"
         % (what, cm, deg))


gate(not cmds.keyframe(cmds.sets(rig.control_set, q=True) or [], query=True, keyframeCount=True),
     "the rig has no keys")
P0 = pose()
gate(bool(rootcontrol.find(rig)), "Root_ctrl made on Add")

r = press("FK->IK", lambda: cx.switch_arm("R", fkik.IK, rig=rig, highlight=False))
same(P0, pose(), "after the arm to IK")
r = press("equip", lambda: equip.to_hand(rig.skeleton_root, "R", catalog.by_key("LongSword_02")))
sword = bonedrive.driving_weapon(N("weapon_r"))
gate(bool(sword), "a sword in the hand")
P1 = pose()

BONE = N("camera_root") if "camera_root" in BODY else None
if BONE:
    press("Camera Setup", lambda: camera.setup(BONE, 0, 30))
    gate(bool(camera.control_for(BONE)), "Camera Setup: a control")
    same(P1, pose(), "after Camera Setup")
    for choice in ("Root", "World", "Main"):
        line = press("parent " + choice, lambda: camera.set_parent(BONE, choice))
        gate(bool(line) and "follows %s" % choice in line, "the camera follows %s" % choice)
        same(P1, pose(), "after the camera to %s" % choice)
    press("teardown", lambda: camera.teardown(BONE, 0, 30))
    same(P1, pose(), "after Camera Setup's teardown")

line = press("Aim Mode", lambda: weaponaim.enter(sword))
gate(weaponaim.is_aimed(sword), "Aim Mode on the still sword")
same(P1, pose(), "after Aim Mode")

cmds.select(N("FKElbow_R"))
line = press("1P Setup", fp.setup)
chest = fp.chest_of(rig)
gate(bool(chest) and len(fp.setup_layers(rig.namespace)) == 2
     and len(fp.display_layers_of(rig.namespace)) == 2, "1P Setup made the chest, two layers, "
     "two display layers")
for l in fp.setup_layers(rig.namespace):
    cmds.setAttr(l + ".mute", 0)
same(P1, pose(), "after 1P Setup, both layers on")
upper = [l for l in fp.setup_layers(rig.namespace) if l.startswith(fp.UPPER)]
if upper:
    cmds.setAttr(upper[0] + ".mute", 1)
    same(P1, pose(), "after 1P Setup, Upper muted (a still rig: no difference)")
    cmds.setAttr(upper[0] + ".mute", 0)
riders = [k for k in knots.knots() if parent_of(k) == chest]
gate(len(fp.arm_constraints(chest)) == 4 and not riders, "the IK arms and poles follow the chest, no knot for them")
group = weaponaim.group_of(sword)
gate(bool(group) and parent_of(group) == chest, "the aim group in the chest")
if BONE:
    ctrl = camera.control_for(BONE)
    gate(bool(ctrl) and parent_of(ctrl) == chest, "the camera control in the chest")
#  the chest moves the arms, the camera and the aim with it
cmds.currentTime(10)
h0, t0 = wm(N("IKArm_R")), wm(weaponaim.controllers(group)["target"])
cmds.setAttr(chest + ".rotateY", lock=False)
was = cmds.getAttr(chest + ".translateY")
cmds.setKeyframe(chest, attribute="translateY", time=10, value=was + 5)
cmds.currentTime(11)
cmds.currentTime(10)
dh = wm(N("IKArm_R"))[13] - h0[13]
print("    hand_r moved", wm(N("hand_r"))[13])
dt = wm(weaponaim.controllers(group)["target"])[13] - t0[13]
r1 = press("FK in 1P", lambda: cx.switch_arm("R", fkik.FK, rig=rig, highlight=False))
r1b = press("IK in 1P", lambda: cx.switch_arm("R", fkik.IK, rig=rig, highlight=False))
gate(fkik.state(rig, "R") == fkik.IK, "on the still 1P rig the arm switches FK and back to IK")
gate(abs(dh - 5) < 0.01 and abs(dt - 5) < 0.01, "the chest +5 up: IKArm_R %.3f, the aim %.3f"
     % (dh, dt))
cmds.cutKey(chest, attribute="translateY", time=(10, 10))
cmds.setAttr(chest + ".translateY", was)

press("Default", lambda: weaponaim.leave(sword))
line = press("Aim Mode after 1P", lambda: weaponaim.enter(sword))
group = weaponaim.group_of(sword)
gate(bool(group) and parent_of(group) == chest, "Aim Mode after 1P: in the chest")
same(P1, pose(), "after Aim Mode in 1P")

press("Bake the chest", lambda: knots.bake([chest]))
gate(not fp.chest_of(rig) and not knots.knots() and not fp.arm_constraints(), "the chest and its knots baked off, the arms let go")
r2 = press("FK->IK again", lambda: cx.switch_arm("L", fkik.IK, rig=rig, highlight=False))
gate(fkik.state(rig, "L") == fkik.IK, "the left arm switches to IK after")
same(P1, pose(), "after the chest's Bake")

print("%d gates, %d failed" % (COUNT[0], len(FAILS)))
for f in FAILS:
    print("  FAIL:", f)
