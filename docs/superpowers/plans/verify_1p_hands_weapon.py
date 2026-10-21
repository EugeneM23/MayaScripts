"""1P Setup: the IK arms and the weapon in the chest control (2026-10-21), mayapy standalone.

    mayapy verify_1p_hands_weapon.py <UE5 clip .fbx> [rig key, default Manny_Rig]

The animator: «в режиме 1P IK руки и оружие находились в паренте нашего Chest контрола. Это
правило работает и для aim системы оружия».

A rig, a clip retargeted, the right arm switched to IK, a Long Sword in the right hand in Aim
Mode, a Dagger in the left hand lifted OUT of it into the world (a weapon Connections lifted, its
bone following it) with a motion of its own. Then 1P Setup:
- the IK arm controls each ride an Across knot inside Chest_1P_ctrl;
- the dagger is a child of the chest, the sword's aim group too; the sword stays in its hand;
- with both layers on (the take): the hands, both weapons, weapon_r / weapon_l and the aim
  controllers where they were on every frame;
- Upper muted (stabilized): hand_r, the dagger and the aim controllers keep their place relative
  to the chest as in the take;
- one undo takes it all back; then the chest baked off (Tools > Bake): the aim controllers and
  the dagger out of it with their motion.
"""

import math
import sys

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
RIG_KEY = sys.argv[2] if len(sys.argv) > 2 else "Manny_Rig"

from maya_scenesetup import (bonedrive, catalog, character, connections as cx, equip,  # noqa
                             fkik, weaponaim, weaponspace)
from maya_tools import firstperson as fp, knots  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402

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


def track(getters, frames):
    out = {}
    for f in frames:
        cmds.currentTime(f)
        out[f] = dict((k, wm(g())) for k, g in getters.items())
    return out


def worst(a, b, keys=None):
    """Places and turns; the aim controllers by their place alone (their turn is locked, a
    parent turns their drawing and nothing else)."""
    cm = deg = 0.0
    by = {}
    for f in a:
        for k in (keys or a[f]):
            d, g = apart(a[f][k], b[f][k])
            if k in ("target", "up", "pole_r", "pole_l"):
                g = 0.0
            by[k] = max(by.get(k, (0, 0))[0], d), max(by.get(k, (0, 0))[1], g)
            cm, deg = max(cm, d), max(deg, g)
    if cm > 0.05 or deg > 0.1:
        print("    worst by node:", dict((k, ("%.3f" % v[0], "%.3f" % v[1])) for k, v in by.items()))
    return cm, deg


def parent_of(n):
    p = cmds.listRelatives(n, parent=True, fullPath=True)
    return p[0] if p else None


cmds.file(new=True, force=True)
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)
character.add_character(catalog.character_by_key(RIG_KEY))
rig = maya_rigs.rigs()[0]
N = lambda leaf: cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]  # noqa: E731

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
last = min(last, first + 36)
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(N("Main"), src)
ok, _t = rr.run_retarget()
cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
gate(ok, "clip retargeted (%d..%d)" % (first, last))

print("   ", cx.switch_arm("R", fkik.IK, rig=rig, highlight=False))
gate(fkik.state(rig, "R") == fkik.IK, "the right arm in IK")
ROOT = rig.skeleton_root
print("   ", equip.to_hand(ROOT, "R", catalog.by_key("LongSword_02")))
print("   ", equip.to_hand(ROOT, "L", catalog.by_key("Dagger_01")))
SWORD = bonedrive.driving_weapon(N("weapon_r"))
DAGGER = bonedrive.driving_weapon(N("weapon_l"))
gate(bool(SWORD) and bool(DAGGER), "a sword in the right hand, a dagger in the left")
print("   ", weaponaim.enter(SWORD))
gate(weaponaim.is_aimed(SWORD), "the sword in Aim Mode")
#  the dagger lifted out of the hand into the world (Connections' World state), keyed
dag_uuid = cmds.ls(DAGGER, uuid=True)[0]
loc = cmds.spaceLocator()[0]
con = cmds.parentConstraint(DAGGER, loc)[0]
cmds.bakeResults(loc, time=(first, last), simulation=True)
cmds.delete(con)
cmds.parent(DAGGER, rig.character)
DAGGER = cmds.ls(dag_uuid, long=True)[0]
con = cmds.parentConstraint(loc, DAGGER)[0]
cmds.bakeResults(DAGGER, time=(first, last), simulation=True,
                 attribute=["tx", "ty", "tz", "rx", "ry", "rz"])
cmds.delete(con, loc)
for f in range(first, last + 1, 4):
    v = cmds.getAttr(DAGGER + ".translateY", time=f)
    cmds.setKeyframe(DAGGER, attribute="translateY", time=f, value=v + 8 * math.sin(f * 0.5))
gate(not weaponspace.holding_hand(DAGGER), "the dagger out of the hand, its bone following it")
gate(parent_of(weaponaim.group_of(SWORD)) == N("Main"), "the sword in a hand: its aim under Main")
print("   ", weaponaim.enter(DAGGER))
gate(parent_of(weaponaim.group_of(DAGGER)) == parent_of(DAGGER),
     "the dagger out in the world: its aim repeats the dagger's parent (%s)"
     % (parent_of(DAGGER) or "").split("|")[-1])
#  the dagger moved under Main by hand (a parent change), its aim follows it, motion kept
dctl = lambda: weaponaim.controllers(weaponaim.group_of(cmds.ls(dag_uuid, long=True)[0]))  # noqa
probe = list(range(first, last + 1, 5))
before_t = {}
for f_ in probe:
    cmds.currentTime(f_)
    before_t[f_] = cmds.xform(dctl()["target"], q=True, ws=True, t=True)
loc2 = cmds.spaceLocator()[0]
c2 = cmds.parentConstraint(cmds.ls(dag_uuid, long=True)[0], loc2)[0]
cmds.bakeResults(loc2, time=(first, last), simulation=True)
cmds.delete(c2)
cmds.parent(cmds.ls(dag_uuid, long=True)[0], N("Main"))
c2 = cmds.pointConstraint(loc2, cmds.ls(dag_uuid, long=True)[0])[0]
cmds.bakeResults(cmds.ls(dag_uuid, long=True)[0], time=(first, last), simulation=True,
                 attribute=["tx", "ty", "tz"])
cmds.delete(c2, loc2)
print("   ", weaponaim.rehome(cmds.ls(dag_uuid, long=True)[0]))
moved = 0.0
for f_ in probe:
    cmds.currentTime(f_)
    t = cmds.xform(dctl()["target"], q=True, ws=True, t=True)
    moved = max(moved, max(abs(a - b) for a, b in zip(t, before_t[f_])))
gate(parent_of(weaponaim.group_of(cmds.ls(dag_uuid, long=True)[0])) == N("Main") and moved < 0.01,
     "rehome: the dagger under Main, its aim follows, the target where it was (%.4f cm)" % moved)
cmds.parent(cmds.ls(dag_uuid, long=True)[0], rig.character)
weaponaim.rehome(cmds.ls(dag_uuid, long=True)[0])
DAGGER = cmds.ls(dag_uuid, long=True)[0]

aim = weaponaim.controllers(weaponaim.group_of(SWORD))
G = {"hand_r": lambda: N("hand_r"), "pole_r": lambda: N("PoleArm_R"), "pole_l": lambda: N("PoleArm_L"), "elbow_r": lambda: N("lowerarm_r"), "elbow_l": lambda: N("lowerarm_l"), "hand_l": lambda: N("hand_l"),
     "weapon_r": lambda: N("weapon_r"), "weapon_l": lambda: N("weapon_l"),
     "sword": lambda: bonedrive.driving_weapon(N("weapon_r")),
     "dagger": lambda: cmds.ls(dag_uuid, long=True)[0],
     "target": lambda: weaponaim.controllers(weaponaim.group_of(
         bonedrive.driving_weapon(N("weapon_r"))))["target"],
     "up": lambda: weaponaim.controllers(weaponaim.group_of(
         bonedrive.driving_weapon(N("weapon_r"))))["up"],
     "spine": lambda: N("spine_03")}
frames = list(range(first, last + 1, 3))
raw = track(G, frames)

cmds.currentTime(first + 4)
LOCS = set(cmds.ls(type="locator", long=True))
cmds.select(N("FKElbow_R"))
line = fp.setup()
print("   ", line)
chest = fp.chest_of(rig)
cmds.undo()
print("    after undo: chest", fp.chest_of(rig), "dagger parent", parent_of(G["dagger"]()),
      "aim parent", parent_of(weaponaim.group_of(G["sword"]())), "char", rig.character)
gate(not fp.chest_of(rig) and parent_of(G["dagger"]()) == rig.character
     and parent_of(weaponaim.group_of(G["sword"]())) != chest,
     "one undo: no chest, the dagger and the aim group back where they were")
cmds.redo()
chest = fp.chest_of(rig)
gate(bool(chest) and parent_of(G["dagger"]()) == chest, "redo: back in the chest")
chest = fp.chest_of(rig)
gate(bool(chest), "1P Setup made the chest")
cons = fp.arm_constraints(chest)
held = sorted(fp._arm_parts(c)[1].split(":")[-1] for c in cons)
gate(held == ["IKArm_L", "IKArm_R", "PoleArm_L", "PoleArm_R"],
     "the IK arms' and the poles' Extra groups follow the chest: %s" % held)
gate(not [c for c in cons if not fp._arm_parts(c)[0].split(":")[-1].startswith(("IKExtraArm", "PoleExtraArm"))],
     "the constraints sit on the Extra groups, the controls themselves are free")
gate(not (set(cmds.ls(type="locator", long=True)) - LOCS),
     "no locator left in the scene: %s" % sorted(set(cmds.ls(type="locator", long=True)) - LOCS))
gate(parent_of(G["dagger"]()) == chest, "the dagger is a child of the chest")
gate(parent_of(weaponaim.group_of(G["sword"]())) == chest, "the sword's aim group in the chest")
gate(weaponspace.holding_hand(G["sword"]()) is not None, "the sword still in its hand")

upper = [l for l in fp.setup_layers(rig.namespace) if l.startswith(fp.UPPER)][0]
cmds.setAttr(upper + ".mute", 0)
both = track(G, frames)
cm, deg = worst(raw, both)
gate(cm < 0.05 and deg < 0.1, "both layers on: hands, weapons, bones, aim as before (%.4f cm, "
     "%.4f deg)" % (cm, deg))


def rel(t, a):
    out = {}
    for f in t:
        m = t[f][a] * t[f]["spine"].inverse()
        if a in ("target", "up"):
            m = om.MMatrix([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, m[12], m[13], m[14], 1])
        out[f] = {"x": m}
    return out


cmds.setAttr(upper + ".mute", 1)
muted = track(G, frames)
f0 = frames[0]
first_rel = rel(dict((f, raw[f0]) for f in frames), "hand_r")
cm, deg = worst(first_rel, rel(muted, "hand_r"))
gate(cm < 0.6 and deg < 0.6, "Upper muted: hand_r holds the take's first pose on the chest "
     "(%.4f cm, %.4f deg)" % (cm, deg))
for name in ("pole_r", "pole_l"):
    cm, deg = worst(rel(dict((f, raw[f0]) for f in frames), name), rel(muted, name))
    gate(cm < 0.6, "Upper muted: %s holds the take's first place on the chest (%.4f cm)" % (name, cm))
for name in ("dagger", "target", "up"):
    cm, deg = worst(rel(raw, name), rel(muted, name))
    gate(cm < 0.6 and deg < 0.6, "Upper muted: %s keeps its place on the chest (%.4f cm, %.4f deg)"
         % (name, cm, deg))
#  something moved at all (a stabilized chest is still, the hand rides it)
moved = max(apart(raw[f]["hand_r"], muted[f]["hand_r"])[0] for f in frames)
gate(moved > 1.0, "the stabilized hand is not where the 3P take had it (%.2f cm)" % moved)
cmds.setAttr(upper + ".mute", 0)

for l in fp.setup_layers(rig.namespace):
    cmds.setAttr(l + ".mute", 0)

#  the bug (2026-10-21): «руки не переключаются в IK после перехода в режим 1P»
before_sw = track(G, frames)
t1 = cx.switch_arm("R", fkik.FK, rig=rig, highlight=False)
print("   ", t1)
t2 = cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)
print("   ", t2)
gate(fkik.state(rig, "R") == fkik.IK and "to IK" in t2 and "to FK" in t1,
     "in 1P the right arm switches to FK and back to IK")
cm, deg = worst(before_sw, track(G, frames), ["hand_r", "weapon_r"])
gate(cm < 0.1 and deg < 0.2, "the hand kept through FK and back (%.4f cm, %.4f deg)" % (cm, deg))
t3 = cx.switch_arm("L", fkik.IK, rig=rig, highlight=False)
print("   ", t3)
gate(fkik.state(rig, "L") == fkik.IK, "the left arm switches to IK in 1P")
raw = track(G, frames)

#  the other order: Aim Mode entered on a rig already in 1P («мы можем сперва создать эйм а потом
#  нажать на 1p setup» - and the other way round)
sword_raw = track({"sword": G["sword"]}, frames)
print("   ", weaponaim.leave(G["sword"]()))
gate(not weaponaim.is_aimed(G["sword"]()), "Default: the sword out of Aim Mode on the 1P rig")
line = weaponaim.enter(G["sword"]())
print("   ", line)
group = weaponaim.group_of(G["sword"]())
gate(bool(group) and parent_of(group) == chest and "1P" in line,
     "Aim Mode entered AFTER 1P Setup: its group in the chest")
cm, deg = worst(sword_raw, track({"sword": G["sword"]}, frames))
gate(cm < 0.05 and deg < 0.1, "the sword stands as before (%.4f cm, %.4f deg)" % (cm, deg))
again = track(G, frames)
upper_l = [l for l in fp.setup_layers(rig.namespace) if l.startswith(fp.UPPER)][0]
cmds.setAttr(upper_l + ".mute", 1)
muted2 = track(G, frames)
for name in ("target", "up"):
    cm, deg = worst(rel(again, name), rel(muted2, name))
    gate(cm < 0.6, "Upper muted: the new %s keeps its place on the chest (%.4f cm)" % (name, cm))
cmds.setAttr(upper_l + ".mute", 0)
raw = again
print("   ", knots.bake([chest]))
gate(not fp.chest_of(rig) and not knots.knots() and not fp.arm_constraints() and parent_of(G["dagger"]()) != chest
     and cmds.objExists(weaponaim.group_of(G["sword"]())),
     "the chest baked off, the IK arms' knots in it with it")
gate(parent_of(weaponaim.group_of(G["sword"]())) == weaponaim.home_of(G["sword"]())
     == N("Main"), "the aim group back under Main")
gate(parent_of(weaponaim.group_of(G["dagger"]())) == parent_of(G["dagger"]()) == rig.character,
     "the world dagger and its aim back in the character group")
cm, deg = worst(raw, track(G, frames), ["dagger", "target", "up", "weapon_l", "hand_r"])
gate(cm < 0.05 and deg < 0.1, "after the Bake: dagger, aim, hand_r as before (%.4f cm, %.4f deg)"
     % (cm, deg))

print("%d gates, %d failed" % (COUNT[0], len(FAILS)))
for f in FAILS:
    print("  FAIL:", f)
