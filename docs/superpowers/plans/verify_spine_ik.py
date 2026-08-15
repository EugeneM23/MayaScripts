"""Live checks for the spine IK: three controls, driving, zero drift.

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


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset -------------------------------------------------------------------
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
all_joints = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap]
cmds.cutKey(all_joints, clear=True)

baseline = len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])
print("baseline non-anim nodes: %d\n" % baseline)

# Real animation on the torso.
cmds.setKeyframe(smap["spine_03"], attribute="rotateZ", time=0, value=0)
cmds.setKeyframe(smap["spine_03"], attribute="rotateZ", time=30, value=25)
cmds.setKeyframe(smap["pelvis"], attribute="rotateY", time=0, value=0)
cmds.setKeyframe(smap["pelvis"], attribute="rotateY", time=30, value=15)

chest_ref = snap("spine_05")
pelvis_ref = snap("pelvis")
head_ref = snap("head")

# --- build spine IK ----------------------------------------------------------
result = builder.build(smap, only=["spine"])
print("build spine IK:", result.message, "\n")
check("spine reported built", result.built == ["spine"], str(result.built))
check("spine is a built limb now", "spine" in builder.built_limbs(),
      str(builder.built_limbs()))

top = builder.ik_control("spine", "end")
mid = builder.ik_control("spine", "pole")
bot = builder.ik_control("spine", "base")
check("top control found (IK_feet)", bool(top), str(top))
check("centre control found (IK_knee)", bool(mid), str(mid))
check("bottom control found (IK_strech_gr)", bool(bot), str(bot))

check("chest animation survived the build",
      drift_of("spine_05", chest_ref) < 0.5,
      "%.3f cm" % drift_of("spine_05", chest_ref))
check("pelvis animation survived the build",
      drift_of("pelvis", pelvis_ref) < 0.5,
      "%.3f cm" % drift_of("pelvis", pelvis_ref))

# --- the controls actually drive ----------------------------------------------
cmds.currentTime(0)
chest_before = wpos(smap["spine_05"])
cmds.setAttr(top + ".translateY", cmds.getAttr(top + ".translateY") + 10)
chest_moved = sum((a - b) ** 2 for a, b in
                  zip(chest_before, wpos(smap["spine_05"]))) ** 0.5
cmds.setAttr(top + ".translateY", cmds.getAttr(top + ".translateY") - 10)
check("top control moves the chest", chest_moved > 3,
      "%.2f cm" % chest_moved)

pelvis_before = wpos(smap["pelvis"])
mid_before = wpos(smap["spine_03"])
cmds.setAttr(bot + ".translateX", cmds.getAttr(bot + ".translateX") + 10)
pelvis_moved = sum((a - b) ** 2 for a, b in
                   zip(pelvis_before, wpos(smap["pelvis"]))) ** 0.5
cmds.setAttr(bot + ".translateX", cmds.getAttr(bot + ".translateX") - 10)
check("bottom control moves the pelvis", pelvis_moved > 3,
      "%.2f cm" % pelvis_moved)

cmds.setAttr(mid + ".translateZ", cmds.getAttr(mid + ".translateZ") + 15)
mid_moved = sum((a - b) ** 2 for a, b in
                zip(mid_before, wpos(smap["spine_03"]))) ** 0.5
cmds.setAttr(mid + ".translateZ", cmds.getAttr(mid + ".translateZ") - 15)
check("centre control bends the middle", mid_moved > 0.5,
      "%.2f cm" % mid_moved)

# --- picker resolution sees the three circles ---------------------------------
resolution = window._resolution()
check("picker: spine_ik_top resolves", "spine_ik_top" in resolution)
check("picker: spine_ik_mid resolves", "spine_ik_mid" in resolution)
check("picker: spine_ik_bot resolves", "spine_ik_bot" in resolution)
check("picker: FK spine buttons dimmed", "spine_03" not in resolution)

# --- bake back -----------------------------------------------------------------
result = builder.bake_limbs(smap, ["spine"])
print("\nbake back:", result.message)
now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene back to baseline", now == baseline, "%d -> %d" % (baseline, now))
check("chest animation on the bones at the end",
      drift_of("spine_05", chest_ref) < 0.5,
      "%.3f cm" % drift_of("spine_05", chest_ref))
check("head follows again", drift_of("head", head_ref) < 0.7,
      "%.3f cm" % drift_of("head", head_ref))

cmds.currentTime(0)
cmds.cutKey(all_joints, clear=True)
cmds.select(clear=True)
print("\n%s" % ("SPINE IK WORKS" if not failures
                else "FAILURES: %s" % failures))
