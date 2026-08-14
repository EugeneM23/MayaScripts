"""Live checks for the OverRig picker. Run inside Maya."""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import bodymap, naming
from maya_overrig.picker_view import MODE_REPLACE

failures = []


def check(label, condition, detail=""):
    print("%-46s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


resolved = naming.resolve_many([b.joint for b in bodymap.BUTTONS])
check("all 64 joints resolve in this scene", len(resolved) == 64,
      "resolved %d" % len(resolved))
check("hand_l does not resolve to ik_hand_l",
      resolved.get("hand_l", "").endswith("|hand_l"),
      resolved.get("hand_l", "<missing>"))

jobs_before = len(cmds.scriptJob(listJobs=True))
window = maya_overrig.show_picker()
check("window opened", window.isVisible())

cmds.select(clear=True)
window.apply_selection(["thigh_l"], MODE_REPLACE)
selection = cmds.ls(selection=True, long=True) or []
check("click selects the right joint",
      len(selection) == 1 and naming.leaf(selection[0]) == "thigh_l",
      str(selection))

window.apply_selection(list(bodymap.group_members("hand_r")), MODE_REPLACE)
check("hand group selects 19 joints",
      len(cmds.ls(selection=True) or []) == 19,
      str(len(cmds.ls(selection=True) or [])))

cmds.select("spine_03", replace=True)
window.sync_from_scene()
check("scene selection syncs back to the picker",
      window.view.items_by_id["spine_03"].state == "selected")

check("no button left dimmed on a full skeleton",
      all(i.available for i in window.view.items_by_id.values()))

window.close()
jobs_after = len(cmds.scriptJob(listJobs=True))
check("scriptJob cleaned up on close", jobs_after == jobs_before,
      "before %d after %d" % (jobs_before, jobs_after))

cmds.select(clear=True)
print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: %s" % failures))
