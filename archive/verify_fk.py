"""Live checks for the FK selection markers. Run inside Maya."""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import bodymap, fkcontrols

failures = []


def check(label, condition, detail=""):
    print("%-52s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map
if "upperarm_l" not in smap:
    print("ABORT: binding failed -", window.status.currentMessage())
    raise SystemExit

fkcontrols.remove_fk()
base_nodes = len(cmds.ls(long=True))

count, message = fkcontrols.build_fk(smap)
print("\nbuild:", message, "\n")

check("64 markers created", count == 64, str(count))
check("manifest set exists", fkcontrols.has_fk())

members = cmds.ls(cmds.sets(fkcontrols.FK_SET, query=True) or [], long=True)
check("set holds 64 members", len(members) == 64, str(len(members)))

radii = {}
for button in bodymap.BUTTONS:
    ctrl = fkcontrols.controller_name(button.joint)
    if not cmds.objExists(ctrl):
        continue
    shape = cmds.listRelatives(ctrl, shapes=True, fullPath=True)[0]
    box = cmds.exactWorldBoundingBox(shape)
    radii[button.joint] = max(box[3] - box[0], box[4] - box[1],
                              box[5] - box[2]) / 2.0

check("every marker exists", len(radii) == 64, str(len(radii)))
check("no degenerate rings", all(r > 0.05 for r in radii.values()),
      str(sorted(radii.items(), key=lambda kv: kv[1])[:3]))
check("fingers are smaller than the pelvis",
      radii["index_03_l"] < radii["pelvis"],
      "%.2f vs %.2f" % (radii["index_03_l"], radii["pelvis"]))
check("hand is smaller than the chest",
      radii["hand_l"] < radii["spine_03"],
      "%.2f vs %.2f" % (radii["hand_l"], radii["spine_03"]))
check("root ring is the largest",
      radii["root"] == max(radii.values()), "%.2f" % radii["root"])

parents = [cmds.listRelatives(fkcontrols.controller_name(b.joint),
                              parent=True)[0] for b in bodymap.BUTTONS
           if cmds.objExists(fkcontrols.controller_name(b.joint))]
check("each marker is parented under its joint",
      all(cmds.objectType(p) == "joint" for p in parents))

left = cmds.getAttr(cmds.listRelatives(
    "hand_l_FK_ctrl", shapes=True, fullPath=True)[0] + ".overrideColorRGB")[0]
right = cmds.getAttr(cmds.listRelatives(
    "hand_r_FK_ctrl", shapes=True, fullPath=True)[0] + ".overrideColorRGB")[0]
check("left and right are coloured differently", left != right,
      "%s vs %s" % (left, right))

check("markers drive nothing",
      not (cmds.listConnections("hand_l_FK_ctrl", source=False,
                                destination=True, type="constraint") or []))

again, _ = fkcontrols.build_fk(smap)
check("rebuild leaves 64, not 128", again == 64, str(again))
check("set still holds 64",
      len(cmds.ls(cmds.sets(fkcontrols.FK_SET, query=True) or [])) == 64)

removed = fkcontrols.remove_fk()
check("removal took them all", removed == 64, str(removed))
check("scene back to its node count", len(cmds.ls(long=True)) == base_nodes,
      "%d -> %d" % (base_nodes, len(cmds.ls(long=True))))

print("\nradius sample:")
for joint in ("root", "pelvis", "spine_03", "head", "upperarm_l", "lowerarm_l",
              "hand_l", "thumb_01_l", "index_03_l", "thigh_l", "calf_l",
              "foot_l", "ball_l", "neck_01"):
    if joint in radii:
        print("   %-14s %6.2f" % (joint, radii[joint]))

print("\n%s" % ("FK MARKERS WORK" if not failures
                else "FAILURES: %s" % failures))
