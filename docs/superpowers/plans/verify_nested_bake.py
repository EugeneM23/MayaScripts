"""Live check: baking a limb must bake whatever is nested inside it first.

Recreates the reported failure -- the arm's IK control parented under the leg's
-- and requires the arm to come out baked and free rather than constrained to a
rig that no longer exists.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import builder, overrig

failures = []


def check(label, condition, detail=""):
    print("%-56s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def constraints_on(path):
    return cmds.listRelatives(path, children=True, type="constraint") or []


window = maya_overrig.show_picker()

# Bind explicitly: a scene littered with rig leftovers can defeat auto-connect.
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map
if "upperarm_l" not in smap:
    print("ABORT: binding failed -", window.status.currentMessage())
    raise SystemExit

if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
strays = [k for k in overrig.set_members(overrig.KNOT_SET)
          if cmds.objExists(k)]
if strays:
    cmds.delete(strays)

base_nodes = len(cmds.ls(long=True))
base_locators = len(cmds.ls(type="locator") or [])
print("clean baseline: %d nodes, %d locators\n" % (base_nodes, base_locators))

builder.build(smap)

arm_l = [smap[j] for j in ("upperarm_l", "lowerarm_l", "hand_l")]
leg_l = [smap[j] for j in ("thigh_l", "calf_l", "foot_l")]
leg_r = [smap[j] for j in ("thigh_r", "calf_r", "foot_r")]

arm_ctrl = [m for m in overrig.set_members(builder.limb_set("arm_l"))
            if m.count("|") == 1 and "_IK_feet" in m][0]
leg_ctrl = [m for m in overrig.set_members(builder.limb_set("leg_l"))
            if m.count("|") == 1 and "_IK_feet" in m][0]
cmds.parent(arm_ctrl, leg_ctrl)
print("nested %s under %s\n" % (arm_ctrl.split("|")[-1],
                                leg_ctrl.split("|")[-1]))

check("both limbs are IK-driven before the bake",
      all(constraints_on(p) for p in arm_l + leg_l))

ordered = builder.order_by_nesting(
    ["leg_l"], {name: overrig.set_members(builder.limb_set(name))
                for name, _ in builder.LIMBS})
check("ordering puts the nested arm before the leg",
      ordered == ["arm_l", "leg_l"], str(ordered))

res = builder.bake_limbs(smap, ["leg_l"])
print("\nbake leg_l:", res.message, "\n")

check("both limbs reported baked", sorted(res.built) == ["arm_l", "leg_l"],
      str(res.built))
check("arm freed of constraints",
      all(not constraints_on(p) for p in arm_l),
      str([constraints_on(p) for p in arm_l]))
check("arm kept its animation",
      all(cmds.keyframe(p, query=True, keyframeCount=True) > 0 for p in arm_l))
check("leg freed of constraints",
      all(not constraints_on(p) for p in leg_l))
check("right leg untouched, still IK-driven",
      all(constraints_on(p) for p in leg_r))
check("neither limb still recorded",
      not ({"arm_l", "leg_l"} & set(builder.built_limbs())),
      str(builder.built_limbs()))

builder.bake_limbs(smap, builder.built_limbs())
check("scene returned to its node count",
      len(cmds.ls(long=True)) == base_nodes,
      "%d -> %d" % (base_nodes, len(cmds.ls(long=True))))
check("locators returned to baseline",
      len(cmds.ls(type="locator") or []) == base_locators,
      "%d -> %d" % (base_locators, len(cmds.ls(type="locator") or [])))

cmds.select(clear=True)
print("\n%s" % ("NESTED BAKE WORKS" if not failures
                else "FAILURES: %s" % failures))
