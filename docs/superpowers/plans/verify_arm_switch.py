"""Live checks for arm switching: no leftovers, no carnage, no finger tear.

The user's reported flow: hybrid build -> switch the right arm to FK ->
pieces of IK remained; switching the left arm afterwards deleted the whole
rig except that arm. Also: overpulling an IK arm tore the fingers off the
hand. This script resets the scene from ANY state, then walks the exact
flow with assertions at every step.

Run inside Maya through the bridge. Binds explicitly to `root`. No undo.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import bodymap, builder, fkcontrols, overrig

failures = []


def check(label, condition, detail=""):
    print("%-58s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def wpos(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def is_under(child, parent):
    if not (child and parent and cmds.objExists(child)
            and cmds.objExists(parent)):
        return False
    return cmds.ls(child, long=True)[0].startswith(
        cmds.ls(parent, long=True)[0] + "|")


def node_count():
    return len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])


def stray_ik_roots():
    return [n.split("|")[-1] for n in
            (cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                     "|IKSpine_gr*", long=True) or [])]


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset from ANY state ------------------------------------------------------
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
bones = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap
         and cmds.objExists(smap[b.joint])]
constrained = [b for b in bones
               if cmds.listRelatives(b, children=True, type="constraint")]
if constrained:
    print("reset: sweeping %d constrained bones" % len(constrained))
    overrig.fast_bake(constrained)
    overrig.delete_constraint_attributes(constrained)
    for b in constrained:
        for con in cmds.listRelatives(b, children=True, type="constraint",
                                      fullPath=True) or []:
            if cmds.objExists(con):
                cmds.delete(con)
for s in cmds.ls("RigPicker_*", type="objectSet") or []:
    if not overrig.set_members(s):
        cmds.delete(s)
for n in cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                 "|IKSpine_gr*", long=True) or []:
    print("reset: deleting stray", n)
    cmds.delete(n)

baseline = node_count()
print("baseline non-anim nodes: %d\n" % baseline)

# --- hybrid build ---------------------------------------------------------------
print(fkcontrols.rebuild(smap, fk_limbs=False), "\n")
torso_ctrls = [fkcontrols.controller_name(j)
               for j in ("root", "pelvis", "spine_03", "spine_05",
                         "neck_01")]

# --- overpull: fingers must stay on the hand, bones must not stretch -------------
cmds.currentTime(0)
ik_hand = builder.ik_control("arm_r", "end")
rest_hm = dist(wpos(smap["hand_r"]), wpos(smap["index_metacarpal_r"]))
rest_up = dist(wpos(smap["upperarm_r"]), wpos(smap["lowerarm_r"]))
rest = cmds.getAttr(ik_hand + ".translate")[0]
cmds.setAttr(ik_hand + ".translate", rest[0], rest[1] - 40, rest[2])
hm = dist(wpos(smap["hand_r"]), wpos(smap["index_metacarpal_r"]))
up = dist(wpos(smap["upperarm_r"]), wpos(smap["lowerarm_r"]))
cmds.setAttr(ik_hand + ".translate", *rest)
check("FINGERS STAY ON THE HAND under a 40cm overpull",
      hm < rest_hm + 2.0, "%.2f cm (rest %.2f, was 33)" % (hm, rest_hm))
check("the limb itself does not stretch", abs(up - rest_up) < 0.5,
      "%.2f vs %.2f" % (up, rest_up))

anchor = fkcontrols._limb_anchor(smap, "arm_r")
index_r = fkcontrols.controller_name("index_metacarpal_r")
check("fingers hang on the hand-bone anchor", is_under(index_r, anchor),
      str(anchor))

# --- switch arm_r to FK -----------------------------------------------------------
cmds.select(ik_hand, replace=True)
done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_r"])
print("\nswitch arm_r:", message)
check("arm_r reported switched", done == ["arm_r -> FK"], str(done))
check("arm_r IK manifest gone",
      not overrig.set_members(builder.limb_set("arm_r")))
arm_r_strays = [n for n in stray_ik_roots()
                if n.startswith(("hand_r_", "lowerarm_r_", "upperarm_r_"))]
check("no right-arm IK strays (legs and left arm stay IK)",
      not arm_r_strays, str(arm_r_strays))
check("FK arm built", bool(fkcontrols.chain_members("arm_r")))
check("fingers on the FK hand",
      is_under(index_r, fkcontrols.controller_name("hand_r")))
check("torso controllers untouched",
      all(cmds.objExists(c) for c in torso_ctrls))

# --- switch arm_l to FK: the carnage scenario --------------------------------------
before = node_count()
cmds.select(builder.ik_control("arm_l", "end"), replace=True)
done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("\nswitch arm_l:", message)
check("arm_l reported switched", done == ["arm_l -> FK"], str(done))
check("TORSO SURVIVED THE SECOND SWITCH",
      all(cmds.objExists(c) for c in torso_ctrls),
      str([c for c in torso_ctrls if not cmds.objExists(c)]))
check("legs still IK",
      set(builder.built_limbs()) == {"leg_l", "leg_r"},
      str(builder.built_limbs()))
check("right arm FK still alive",
      bool(fkcontrols.chain_members("arm_r"))
      and cmds.objExists(fkcontrols.controller_name("hand_r")))
check("left fingers on the left FK hand",
      is_under(fkcontrols.controller_name("index_metacarpal_l"),
               fkcontrols.controller_name("hand_l")))

# --- both arms back to IK -----------------------------------------------------------
done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l", "arm_r"])
print("\nswitch both back:", message)
check("both arms IK again",
      set(builder.built_limbs()) == {"arm_l", "arm_r", "leg_l", "leg_r"},
      str(builder.built_limbs()))
check("right fingers on the anchor again",
      is_under(index_r, fkcontrols._limb_anchor(smap, "arm_r")))
check("torso still fine",
      all(cmds.objExists(c) for c in torso_ctrls))

# --- full teardown -------------------------------------------------------------------
fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
now = node_count()
check("scene no dirtier than the baseline", now <= baseline,
      "%d -> %d" % (baseline, now))
check("no strays at the end", not stray_ik_roots(), str(stray_ik_roots()))

cmds.currentTime(0)
cmds.select(clear=True)
print("\n%s" % ("ARM SWITCH WORKS" if not failures
                else "FAILURES: %s" % failures))
