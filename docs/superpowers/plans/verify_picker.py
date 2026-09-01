"""Live checks for the Rig Picker. Run inside Maya.

Part of this builds a temporary second character under a `hero:` namespace to
prove the picker binds to one skeleton and stays there. It is removed again in
the finally block, and the joint count is compared before and after.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
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
    print("%-52s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def make_second_character():
    """Duplicate the skeleton into a `hero:` namespace. Returns its group."""
    if not cmds.namespace(exists="hero"):
        cmds.namespace(addNamespace="hero")
    dup = cmds.duplicate("|SKM_Manny_Simple|root", returnRootsOnly=True)[0]
    dup_long = cmds.ls(dup, long=True)[0]
    dup_long = cmds.ls(cmds.parent(dup_long, world=True)[0], long=True)[0]

    nodes = cmds.ls(dup_long, dagObjects=True, long=True) or []
    for node in sorted(nodes, key=lambda n: -n.count("|")):
        short = node.split("|")[-1]
        if ":" not in short:
            cmds.rename(node, "hero:" + short)

    # duplicate() suffixes the top node (root -> root1). Put the name back, or
    # this character would have nothing for the picker's `root` button to match.
    top = min(cmds.ls("hero:*", long=True, type="joint"),
              key=lambda n: n.count("|"))
    cmds.rename(top, "hero:root")
    return cmds.ls("hero:root", long=True)[0]


joints_before = len(cmds.ls(type="joint"))
jobs_before = len(cmds.scriptJob(listJobs=True))
hero_root = None

try:
    # --- one character -----------------------------------------------------
    check("one skeleton root in the untouched scene",
          len(naming.find_skeleton_roots()) == 1,
          str(naming.find_skeleton_roots()))

    window = maya_overrig.show_picker()
    check("window opened", window.isVisible())
    check("auto-connected to the only character",
          window.bound_root() == "|SKM_Manny_Simple|root",
          str(window.bound_root()))
    check("all 64 buttons matched",
          sum(1 for b in bodymap.BUTTONS if b.joint in window._scene_map) == 64)
    check("hand_l maps to hand_l, not ik_hand_l",
          window._scene_map["hand_l"].endswith("|hand_l"))

    cmds.select(clear=True)
    window.apply_selection(["thigh_l"], MODE_REPLACE)
    selection = cmds.ls(selection=True, long=True) or []
    check("click selects the right joint",
          selection == ["|SKM_Manny_Simple|root|pelvis|thigh_l"], str(selection))

    # --- second character --------------------------------------------------
    hero_root = make_second_character()
    print("\n  built temporary second character: %s\n" % hero_root)

    check("two skeleton roots now visible",
          len(naming.find_skeleton_roots()) == 2,
          str(len(naming.find_skeleton_roots())))

    check("picker still bound to the original after the duplicate appeared",
          window.bound_root() == "|SKM_Manny_Simple|root",
          str(window.bound_root()))

    cmds.select(clear=True)
    window.apply_selection(["spine_03"], MODE_REPLACE)
    selection = cmds.ls(selection=True, long=True) or []
    check("click still lands on the original, not the duplicate",
          selection and selection[0].startswith("|SKM_Manny_Simple|"),
          str(selection))

    # The old bug: selecting the other character used to light our buttons.
    cmds.select("hero:spine_03", replace=True)
    window.sync_from_scene()
    check("other character's selection does NOT light our buttons",
          window.view.items_by_id["spine_03"].state == "neutral")

    # --- rebind to the duplicate ------------------------------------------
    cmds.select("hero:pelvis", replace=True)
    window.connect_to_selection()
    check("Connect from a mid-chain joint found the duplicate's root",
          window.bound_root() == hero_root, str(window.bound_root()))
    check("all 64 buttons matched on the namespaced character",
          sum(1 for b in bodymap.BUTTONS if b.joint in window._scene_map) == 64)

    cmds.select(clear=True)
    window.apply_selection(["foot_r"], MODE_REPLACE)
    selection = cmds.ls(selection=True, long=True) or []
    check("click now lands on the namespaced character",
          selection and "hero:foot_r" in selection[0], str(selection))

    cmds.select("hero:spine_03", replace=True)
    window.sync_from_scene()
    check("bound character's selection does light our buttons",
          window.view.items_by_id["spine_03"].state == "selected")

    # --- binding survives a rename ----------------------------------------
    cmds.rename("hero:root", "hero:root_renamed")
    check("binding survives renaming the root",
          window.bound_root() == cmds.ls("hero:root_renamed", long=True)[0],
          str(window.bound_root()))

finally:
    cmds.select(clear=True)
    try:
        window.close()
    except Exception:
        pass
    if hero_root is not None:
        for node in ("hero:root_renamed", "hero:root"):
            if cmds.objExists(node):
                cmds.delete(node)
    if cmds.namespace(exists="hero"):
        cmds.namespace(removeNamespace="hero", deleteNamespaceContent=True)

joints_after = len(cmds.ls(type="joint"))
jobs_after = len(cmds.scriptJob(listJobs=True))

print()
check("scene restored - joint count unchanged", joints_after == joints_before,
      "before %d after %d" % (joints_before, joints_after))
check("hero namespace removed", not cmds.namespace(exists="hero"))
check("scriptJob cleaned up on close", jobs_after == jobs_before,
      "before %d after %d" % (jobs_before, jobs_after))

print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: %s" % failures))
