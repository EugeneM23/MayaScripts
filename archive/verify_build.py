"""Live checks for Build. Run inside Maya.

Creates a decoy OverRig knot outside our manifest and proves a rebuild leaves
it alone -- that is the check that justifies not using OverRig's global
teardown.
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
    print("%-54s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


check("OverRig available", overrig.ensure_loaded())

window = maya_overrig.show_picker()
check("picker bound", bool(window._scene_map), str(window.bound_root()))

joints_before = len(cmds.ls(type="joint"))

# A knot the user "made by hand", deliberately outside our manifest.
decoy = cmds.spaceLocator(name="decoy_manual_knot")[0]
if not cmds.objExists(overrig.KNOT_SET):
    cmds.sets(name=overrig.KNOT_SET, empty=True)
cmds.sets(decoy, addElement=overrig.KNOT_SET)

result = builder.build(window._scene_map)
print("\n  build says: %s\n" % result.message)

check("all four limbs built",
      sorted(result.built) == ["arm_l", "arm_r", "leg_l", "leg_r"],
      str(result.built))
check("nodes were created", result.created > 0, str(result.created))
check("manifest set exists", cmds.objExists(builder.BUILD_SET))

manifest = overrig.set_members(builder.BUILD_SET)
check("manifest is not empty", len(manifest) > 0, str(len(manifest)))
check("decoy is NOT in our manifest",
      not any(decoy in m for m in manifest))

for suffix in ("_IK_feet", "_IK_knee"):
    hits = cmds.ls("*" + suffix, long=True) or []
    check("created %s nodes" % suffix, len(hits) >= 4, "%d found" % len(hits))

first_count = len(cmds.ls(long=True))
second = builder.build(window._scene_map)
print("\n  rebuild says: %s\n" % second.message)
check("second Build rebuilt rather than doubled",
      second.removed > 0, "removed %d" % second.removed)
check("node count did not run away",
      abs(len(cmds.ls(long=True)) - first_count) < 5,
      "%d -> %d" % (first_count, len(cmds.ls(long=True))))
check("decoy survived the rebuild", cmds.objExists(decoy))

builder.teardown(window._scene_map)
check("teardown removed the manifest set",
      not cmds.objExists(builder.BUILD_SET))
check("decoy still alive after teardown", cmds.objExists(decoy))

if cmds.objExists(decoy):
    cmds.delete(decoy)
if cmds.objExists(overrig.KNOT_SET) and not (
        cmds.sets(overrig.KNOT_SET, query=True) or []):
    cmds.delete(overrig.KNOT_SET)

check("joint count unchanged", len(cmds.ls(type="joint")) == joints_before,
      "before %d after %d" % (joints_before, len(cmds.ls(type="joint"))))

window.close()
print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: %s" % failures))
