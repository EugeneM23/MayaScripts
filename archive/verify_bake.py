"""Live checks for per-limb baking. Run inside Maya."""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import builder, overrig
from maya_overrig.picker_view import MODE_REPLACE

failures = []


def check(label, condition, detail=""):
    print("%-54s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def constraints_on(joint):
    return cmds.listRelatives(joint, children=True, type="constraint") or []


# Clear the stale flat set from the previous design.
if cmds.objExists("RigPicker_build"):
    cmds.delete("RigPicker_build")
    print("  removed the stale flat RigPicker_build set\n")

window = maya_overrig.show_picker()
check("picker bound", bool(window._scene_map), str(window.bound_root()))

# Start from a known state: everything on IK.
if builder.has_build():
    builder.teardown(window._scene_map)
result = builder.build(window._scene_map)
check("four limbs built", len(result.built) == 4, str(result.built))
check("four manifest sets exist", len(builder.built_limbs()) == 4,
      str(builder.built_limbs()))

leg_l = [window._scene_map[j] for j in ("thigh_l", "calf_l", "foot_l")]
leg_r = [window._scene_map[j] for j in ("thigh_r", "calf_r", "foot_r")]

check("left leg is IK-driven before baking",
      any(constraints_on(j) for j in leg_l))

# --- bake ONE limb by selecting one of its recorded nodes ---------------
# Picked by manifest membership, not by name: OverRig suffixes its renames
# when a name is taken, so `foot_l_IK_feet` can come back as
# `foot_l_IK_feet1` and a name filter silently matches nothing.
members = overrig.set_members(builder.limb_set("leg_l"))
cmds.select(members[0], replace=True)
found = builder.limbs_in_selection(window._scene_map)
check("selecting the IK control resolves to leg_l", found == ["leg_l"],
      str(found))

baked = builder.bake_limbs(window._scene_map, found)
print("\n  bake says: %s\n" % baked.message)

check("leg_l reported baked", baked.built == ["leg_l"], str(baked.built))
check("leg_l set is gone", not cmds.objExists(builder.limb_set("leg_l")))
check("leg_l joints freed of constraints",
      all(not constraints_on(j) for j in leg_l))
check("leg_l kept its animation",
      all(cmds.keyframe(j, query=True, keyframeCount=True) > 0 for j in leg_l))
check("the other three limbs remain", len(builder.built_limbs()) == 3,
      str(builder.built_limbs()))
check("right leg still IK-driven", any(constraints_on(j) for j in leg_r))

# --- the picker's own limb button as the selector ------------------------
window.apply_selection(["thigh_r", "calf_r", "foot_r"], MODE_REPLACE)
found = builder.limbs_in_selection(window._scene_map)
check("selecting source joints resolves to leg_r", found == ["leg_r"],
      str(found))

# --- and an irrelevant selection must do nothing ------------------------
cmds.select("persp", replace=True)
check("irrelevant selection resolves to nothing",
      builder.limbs_in_selection(window._scene_map) == [])

# --- bake the rest ------------------------------------------------------
rest = builder.built_limbs()
final = builder.bake_limbs(window._scene_map, rest)
print("\n  final bake says: %s\n" % final.message)
check("no manifest sets left", builder.built_limbs() == [],
      str(builder.built_limbs()))
check("no build recorded", not builder.has_build())
check("every limb freed of constraints",
      all(not constraints_on(j) for j in leg_l + leg_r))

cmds.select(clear=True)
window.close()
print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: %s" % failures))
