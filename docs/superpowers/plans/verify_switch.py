"""Live checks for Switch FK/IK. Run inside Maya."""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import bodymap, builder, fkcontrols

failures = []


def check(label, condition, detail=""):
    print("%-58s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def wpos(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def drift_of(joint, ref):
    worst = 0.0
    for frame, pos in ref.items():
        cmds.currentTime(frame)
        now = wpos(smap[joint])
        worst = max(worst, sum((a - b) ** 2
                               for a, b in zip(pos, now)) ** 0.5)
    return worst


def snap(joint):
    out = {}
    for frame in (0, 15, 30):
        cmds.currentTime(frame)
        out[frame] = wpos(smap[joint])
    return out


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset: absorbs the legacy flat-set FK currently in the scene ----------
if fkcontrols.has_fk():
    removed, message = fkcontrols.bake_fk(smap)
    print("reset:", message)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
all_joints = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap]
cmds.cutKey(all_joints, clear=True)
check("legacy flat set absorbed", not cmds.objExists("RigPicker_fk"))

baseline = len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])
print("baseline non-anim nodes: %d\n" % baseline)

# Real animation.
cmds.setKeyframe(smap["spine_03"], attribute="rotateZ", time=0, value=0)
cmds.setKeyframe(smap["spine_03"], attribute="rotateZ", time=30, value=20)
cmds.setKeyframe(smap["upperarm_l"], attribute="rotateZ", time=0, value=0)
cmds.setKeyframe(smap["upperarm_l"], attribute="rotateZ", time=30, value=-35)

hand_ref = snap("hand_l")
foot_ref = snap("foot_l")
finger_ref = snap("index_03_l")

count, message = fkcontrols.build_fk(smap)
print("build FK:", message, "\n")
check("full FK built", count == 64, str(count))

# --- switch a leg to IK -----------------------------------------------------
cmds.select("foot_l_FK_ctrl", replace=True)
done, skipped, message = fkcontrols.switch_limbs(
    smap, ["leg_l"])
print("switch leg:", message)
check("leg reported switched to IK", done == ["leg_l -> IK"], str(done))
check("leg is IK now", builder.built_limbs() == ["leg_l"],
      str(builder.built_limbs()))
check("leg FK chain gone", not fkcontrols.chain_members("leg_l"))
check("arm FK still present", bool(fkcontrols.chain_members("arm_l")))
check("foot animation survived leg switch", drift_of("foot_l", foot_ref) < 0.5,
      "%.3f cm" % drift_of("foot_l", foot_ref))

# --- and back to FK ----------------------------------------------------------
done, skipped, message = fkcontrols.switch_limbs(smap, ["leg_l"])
print("\nswitch leg back:", message)
check("leg reported switched to FK", done == ["leg_l -> FK"], str(done))
check("no IK left", builder.built_limbs() == [], str(builder.built_limbs()))
check("leg FK chain recorded again", bool(fkcontrols.chain_members("leg_l")))
check("leg coupled to the pelvis control",
      "uncoupled" not in message, message)
check("foot animation survived the round trip",
      drift_of("foot_l", foot_ref) < 0.5,
      "%.3f cm" % drift_of("foot_l", foot_ref))

# --- switch an arm: fingers must survive -------------------------------------
finger_ctrls = [fkcontrols.controller_name(dict(fkcontrols.CHAINS)[c][0])
                for c in fkcontrols.finger_chains_for("arm_l")]
done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("\nswitch arm:", message)
check("arm reported switched to IK", done == ["arm_l -> IK"], str(done))
alive = [c for c in finger_ctrls if cmds.objExists(c)]
check("all five finger controls survived", len(alive) == 5, str(len(alive)))

ik_hand = fkcontrols._ik_hand_control("arm_l")
check("IK hand control found", bool(ik_hand), str(ik_hand))
under = [c for c in alive
         if cmds.ls(c, long=True)[0].startswith(
             cmds.ls(ik_hand, long=True)[0] + "|")]
check("fingers hang under the IK hand", len(under) == 5, str(len(under)))
check("hand animation survived the arm switch",
      drift_of("hand_l", hand_ref) < 0.5,
      "%.3f cm" % drift_of("hand_l", hand_ref))
check("finger animation survived too",
      drift_of("index_03_l", finger_ref) < 0.5,
      "%.3f cm" % drift_of("index_03_l", finger_ref))

# Fingers follow the IK hand.
cmds.currentTime(0)
tip_before = wpos(smap["index_03_l"])
cmds.setAttr(ik_hand + ".translateY",
             cmds.getAttr(ik_hand + ".translateY") + 10)
tip_moved = sum((a - b) ** 2
                for a, b in zip(tip_before, wpos(smap["index_03_l"]))) ** 0.5
cmds.setAttr(ik_hand + ".translateY",
             cmds.getAttr(ik_hand + ".translateY") - 10)
check("fingers follow the IK hand", tip_moved > 5, "%.2f cm" % tip_moved)

# --- arm back to FK -----------------------------------------------------------
done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("\nswitch arm back:", message)
check("arm back to FK", done == ["arm_l -> FK"], str(done))
fk_hand = fkcontrols.controller_name("hand_l")
under = [c for c in finger_ctrls
         if cmds.objExists(c) and cmds.ls(c, long=True)[0].startswith(
             cmds.ls(fk_hand, long=True)[0] + "|")]
check("fingers hang under the FK hand again", len(under) == 5, str(len(under)))
check("hand animation intact after both switches",
      drift_of("hand_l", hand_ref) < 0.5,
      "%.3f cm" % drift_of("hand_l", hand_ref))

# --- full bake back ----------------------------------------------------------
removed, message = fkcontrols.bake_fk(smap)
print("\nfinal bake:", message)
check("nothing recorded", not fkcontrols.has_fk() and not builder.has_build())
now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene back to baseline", now == baseline,
      "%d -> %d" % (baseline, now))
check("hand animation on the bones at the end",
      drift_of("hand_l", hand_ref) < 0.5,
      "%.3f cm" % drift_of("hand_l", hand_ref))

cmds.currentTime(0)
cmds.cutKey(all_joints, clear=True)
cmds.select(clear=True)
print("\n%s" % ("SWITCH FK/IK WORKS" if not failures
                else "FAILURES: %s" % failures))
