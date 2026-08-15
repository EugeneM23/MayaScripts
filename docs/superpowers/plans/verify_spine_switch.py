"""Live checks for Switch FK/IK on the spine: dependents survive and follow.

Run inside Maya through the bridge. Binds explicitly to `root`.
"""

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


def snap(joint):
    out = {}
    for frame in (0, 15, 30):
        cmds.currentTime(frame)
        out[frame] = wpos(smap[joint])
    return out


def drift_of(joint, ref):
    worst = 0.0
    for frame, pos in ref.items():
        cmds.currentTime(frame)
        now = wpos(smap[joint])
        worst = max(worst, sum((a - b) ** 2
                               for a, b in zip(pos, now)) ** 0.5)
    return worst


def is_under(child, parent):
    if not (child and parent and cmds.objExists(child)
            and cmds.objExists(parent)):
        return False
    return cmds.ls(child, long=True)[0].startswith(
        cmds.ls(parent, long=True)[0] + "|")


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset ------------------------------------------------------------------
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
all_joints = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap]
cmds.cutKey(all_joints, clear=True)

baseline = len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])
print("baseline non-anim nodes: %d\n" % baseline)

cmds.setKeyframe(smap["spine_03"], attribute="rotateZ", time=0, value=0)
cmds.setKeyframe(smap["spine_03"], attribute="rotateZ", time=30, value=25)
cmds.setKeyframe(smap["upperarm_l"], attribute="rotateZ", time=0, value=0)
cmds.setKeyframe(smap["upperarm_l"], attribute="rotateZ", time=30, value=-30)

hand_ref = snap("hand_l")
head_ref = snap("head")
thigh_ref = snap("thigh_l")
chest_ref = snap("spine_05")

# --- full FK, then switch the spine to IK ------------------------------------
count, message = fkcontrols.build_fk(smap)
print("build FK:", message, "\n")
check("full FK built", count == 64, str(count))

cmds.select(fkcontrols.controller_name("spine_03"), replace=True)
done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("switch spine:", message, "\n")
check("spine reported switched to IK", done == ["spine -> IK"], str(done))
check("spine is IK now", builder.built_limbs() == ["spine"],
      str(builder.built_limbs()))
check("spine FK chain gone", not fkcontrols.chain_members("spine"))

top = builder.ik_control("spine", "end")
bot = builder.ik_control("spine", "base")
neck_ctrl = fkcontrols.controller_name("neck_01")
clav_l = fkcontrols.controller_name("clavicle_l")
clav_r = fkcontrols.controller_name("clavicle_r")
thigh_l = fkcontrols.controller_name("thigh_l")
thigh_r = fkcontrols.controller_name("thigh_r")

for label, ctrl in (("neck control", neck_ctrl),
                    ("left clavicle control", clav_l),
                    ("right clavicle control", clav_r),
                    ("left thigh control", thigh_l),
                    ("right thigh control", thigh_r)):
    check(label + " survived", cmds.objExists(ctrl), ctrl)

check("neck hangs on the top control", is_under(neck_ctrl, top))
check("clavicles hang on the top control",
      is_under(clav_l, top) and is_under(clav_r, top))
check("thighs hang on the base group",
      is_under(thigh_l, bot) and is_under(thigh_r, bot))

check("head animation survived the switch",
      drift_of("head", head_ref) < 0.7,
      "%.3f cm" % drift_of("head", head_ref))
check("hand animation survived the switch",
      drift_of("hand_l", hand_ref) < 0.7,
      "%.3f cm" % drift_of("hand_l", hand_ref))
check("thigh animation survived the switch",
      drift_of("thigh_l", thigh_ref) < 0.5,
      "%.3f cm" % drift_of("thigh_l", thigh_ref))

# Dependents follow the spine IK live.
cmds.currentTime(0)
head_before = wpos(smap["head"])
cmds.setAttr(top + ".translateY", cmds.getAttr(top + ".translateY") + 10)
head_moved = sum((a - b) ** 2 for a, b in
                 zip(head_before, wpos(smap["head"]))) ** 0.5
cmds.setAttr(top + ".translateY", cmds.getAttr(top + ".translateY") - 10)
check("head follows the top control", head_moved > 3, "%.2f cm" % head_moved)

# --- switch back to FK ---------------------------------------------------------
done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("\nswitch spine back:", message, "\n")
check("spine reported switched to FK", done == ["spine -> FK"], str(done))
check("no IK left", builder.built_limbs() == [], str(builder.built_limbs()))
check("spine FK chain recorded again",
      bool(fkcontrols.chain_members("spine")))

spine05_ctrl = fkcontrols.controller_name("spine_05")
pelvis_ctrl = fkcontrols.controller_name("pelvis")
check("neck back on the spine_05 control", is_under(neck_ctrl, spine05_ctrl))
check("clavicles back on the spine_05 control",
      is_under(clav_l, spine05_ctrl) and is_under(clav_r, spine05_ctrl))
check("thighs back on the pelvis control",
      is_under(thigh_l, pelvis_ctrl) and is_under(thigh_r, pelvis_ctrl))
check("chest animation survived the round trip",
      drift_of("spine_05", chest_ref) < 0.5,
      "%.3f cm" % drift_of("spine_05", chest_ref))

# --- bake everything back --------------------------------------------------------
removed, message = fkcontrols.bake_fk(smap)
print("\nfinal bake:", message)
check("nothing recorded",
      not fkcontrols.has_fk() and not builder.has_build())
now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene back to baseline", now == baseline, "%d -> %d" % (baseline, now))
check("head animation on the bones at the end",
      drift_of("head", head_ref) < 0.7,
      "%.3f cm" % drift_of("head", head_ref))

cmds.currentTime(0)
cmds.cutKey(all_joints, clear=True)
cmds.select(clear=True)
print("\n%s" % ("SPINE SWITCH WORKS" if not failures
                else "FAILURES: %s" % failures))
