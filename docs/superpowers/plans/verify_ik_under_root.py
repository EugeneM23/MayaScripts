"""Live checks: IK rigs ride the root control, carrying the finger bones.

Since 2026-08-18 the fingers have no controllers -- they are posed on the
bones -- so what this script proves about them changed shape: not "the finger
ring is visible on the IK hand" (trap 15) but "the finger BONE travels with the
root control and survives a root bake untouched". The bone is the better probe
of the two anyway: it is what the animator actually keys.


Run inside Maya through the bridge runner (see the plan; the runner's
explicit globals dict is what lets these helpers see module-level names).
Binds explicitly to `root`, resets the scene from ANY state, then walks the
flow with assertions at every step. No cmds.undo -- the whole script is one
command, and undoing reverts a prior chunk. Values are read before they are
written back; autoKey is off throughout.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
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


def visible(node):
    """Effective visibility: the node's flag and every ancestor's."""
    if not cmds.objExists(node):
        return False
    path = cmds.ls(node, long=True)[0]
    while path:
        if not cmds.getAttr(path + ".visibility"):
            return False
        path = path.rsplit("|", 1)[0]
    return True


def wiggle():
    """Settle the DAG -- reads straight after a setAttr return stale mixtures."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, edit=True)
    cmds.currentTime(now, edit=True)


def stray_ik_roots():
    return [n.split("|")[-1] for n in
            (cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                     long=True) or [])]


def node_count():
    return len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])


FINGER_CTRLS = [fkcontrols.controller_name(j)
                for j in fkcontrols.FINGER_JOINTS]

auto_key = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)

window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset from ANY state ---------------------------------------------------
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
                 long=True) or []:
    print("reset: deleting stray", n)
    cmds.delete(n)

baseline = node_count()
print("baseline non-anim nodes: %d\n" % baseline)

# --- hybrid build -----------------------------------------------------------
print(fkcontrols.rebuild(smap, fk_limbs=False), "\n")

# --- section 1: the fingers are bones, and nothing was built for them -------
live_fingers = [c for c in FINGER_CTRLS if cmds.objExists(c)]
check("no finger controller exists", not live_fingers, str(live_fingers[:3]))
check("no finger chain is recorded",
      not [c for c in fkcontrols.FINGER_CHAINS
           if fkcontrols.chain_members(c)])

for limb in ("arm_l", "arm_r"):
    # `_anchor_in`, not `_limb_anchor`: the latter CREATES the locator, which
    # would make this gate prove its own opposite.
    check("no IK hand anchor built for nothing: " + limb,
          not fkcontrols._anchor_in(builder.limb_set(limb),
                                    limb + "_IK_anchor"))
    side = limb[-1]
    check("finger bones ride the hand bone: " + limb,
          is_under(smap["index_metacarpal_" + side], smap["hand_" + side]))
    check("finger bones are unconstrained: " + limb,
          not [j for j in fkcontrols.FINGER_JOINTS
               if j.endswith("_" + side) and j in smap
               and cmds.listRelatives(smap[j], children=True,
                                      type="constraint")])
    check("the IK hand control is visible: " + limb,
          visible(builder.ik_control(limb, "end")))

# --- section 2: every IK group rides the root control -----------------------
root_ctrl = fkcontrols.controller_name("root")
check("root controller exists", cmds.objExists(root_ctrl))
for limb in builder.DEFAULT_IK:
    for role in fkcontrols.IK_TOP_ROLES:
        node = builder.ik_control(limb, role)
        check("%s %s rides the root control" % (limb, role),
              is_under(node, root_ctrl), str(node))

# The whole character must travel with the root control: bones and IK controls
# alike, the finger bones at the far end of the chain included. Read the value
# first, then put it back.
cmds.currentTime(0)
probes = {"upperarm_l bone": smap["upperarm_l"],
          "hand_l bone": smap["hand_l"],
          "foot_r bone": smap["foot_r"],
          "arm_l IK end": builder.ik_control("arm_l", "end"),
          "leg_r IK pole": builder.ik_control("leg_r", "pole"),
          "index_l finger bone": smap["index_03_l"]}
before_move = {k: wpos(v) for k, v in probes.items()}
rest = cmds.getAttr(root_ctrl + ".translate")[0]
cmds.setAttr(root_ctrl + ".translateX", rest[0] + 50.0)
wiggle()
after_move = {k: wpos(v) for k, v in probes.items()}
cmds.setAttr(root_ctrl + ".translate", *rest)
wiggle()
for name in sorted(probes):
    moved = dist(after_move[name], before_move[name])
    check("MOVES WITH THE ROOT CONTROL: " + name, abs(moved - 50.0) < 0.5,
          "%.3f cm" % moved)
for name in sorted(probes):
    back = dist(wpos(probes[name]), before_move[name])
    check("returns to rest: " + name, back < 0.01, "%.4f cm" % back)

# --- section 3: Bake+Delete on root lifts the IK rigs, does not kill them ---
cmds.currentTime(0)
hand_before = wpos(smap["hand_l"])
foot_before = wpos(smap["foot_r"])
cmds.select(root_ctrl, replace=True)
ik_hit, fk_hit = fkcontrols.bake_targets(smap)
check("root selection resolves to the root chain only",
      (ik_hit, fk_hit) == ([], ["root"]), "%s %s" % (ik_hit, fk_hit))
print(fkcontrols.bake_selection(smap, ik_hit, fk_hit), "\n")
wiggle()

check("root controller is gone", not cmds.objExists(root_ctrl))
check("ALL FOUR IK LIMBS SURVIVED",
      set(builder.built_limbs()) == set(builder.DEFAULT_IK),
      str(builder.built_limbs()))
for limb in builder.DEFAULT_IK:
    node = builder.ik_control(limb, "end")
    check("%s IK end is back in world" % limb,
          bool(node) and not cmds.listRelatives(node, parent=True),
          str(node))
# The finger bones hang off the hand bone, which the lifted IK still drives --
# containment through a surviving rig is not ownership, so a root bake must
# leave the hands working. When the fingers had controllers, baking them away
# here orphaned those controllers unrecorded and made the next bake_limbs
# refuse ("holds OverRig nodes we did not build"). Nothing of ours is on them
# now, so the gate is that nothing has appeared and nothing has moved.
for limb in ("arm_l", "arm_r"):
    side = limb[-1]
    finger = smap["index_metacarpal_" + side]
    check("NO FINGER RIG APPEARED FROM THE ROOT BAKE: " + limb,
          not fkcontrols.chain_members("index_" + side)
          and not cmds.objExists(
              fkcontrols.controller_name("index_metacarpal_" + side)))
    check("finger bones still ride the hand bone: " + limb,
          is_under(finger, smap["hand_" + side]))
    check("finger bones still unconstrained: " + limb,
          not cmds.listRelatives(finger, children=True, type="constraint"))
check("torso FK is gone with the root",
      not any(cmds.objExists(fkcontrols.controller_name(j))
              for j in ("pelvis", "spine_03", "neck_01")))

check("hand_l did not drift", dist(wpos(smap["hand_l"]), hand_before) < 0.05,
      "%.4f cm" % dist(wpos(smap["hand_l"]), hand_before))
check("foot_r did not drift", dist(wpos(smap["foot_r"]), foot_before) < 0.05,
      "%.4f cm" % dist(wpos(smap["foot_r"]), foot_before))

# The lifted rig must still DRIVE its bone.
ik_end = builder.ik_control("arm_l", "end")
rest_end = cmds.getAttr(ik_end + ".translate")[0]
cmds.setAttr(ik_end + ".translateY", rest_end[1] - 10.0)
wiggle()
moved_hand = dist(wpos(smap["hand_l"]), hand_before)
cmds.setAttr(ik_end + ".translate", *rest_end)
wiggle()
check("LIFTED IK STILL DRIVES THE HAND", moved_hand > 5.0,
      "%.3f cm" % moved_hand)
check("hand returns to rest after the poke",
      dist(wpos(smap["hand_l"]), hand_before) < 0.05)

# --- section 4: regressions the old traps left behind -----------------------
# Rebuild the hybrid rig -- this also exercises the FK-first teardown over
# the lifted IK rigs from section 3.
print(fkcontrols.rebuild(smap, fk_limbs=False), "\n")
root_ctrl = fkcontrols.controller_name("root")
check("rebuild restored the root controller", cmds.objExists(root_ctrl))
check("rebuild re-hung every IK limb",
      all(is_under(builder.ik_control(limb, role), root_ctrl)
          for limb in builder.DEFAULT_IK
          for role in fkcontrols.IK_TOP_ROLES),
      str(builder.built_limbs()))

# Overpull: fingers must stay on the hand even with the rig under root.
cmds.currentTime(0)
ik_hand = builder.ik_control("arm_r", "end")
rest_hm = dist(wpos(smap["hand_r"]), wpos(smap["index_metacarpal_r"]))
rest_up = dist(wpos(smap["upperarm_r"]), wpos(smap["lowerarm_r"]))
rest = cmds.getAttr(ik_hand + ".translate")[0]
cmds.setAttr(ik_hand + ".translate", rest[0], rest[1] - 40, rest[2])
wiggle()
hm = dist(wpos(smap["hand_r"]), wpos(smap["index_metacarpal_r"]))
up = dist(wpos(smap["upperarm_r"]), wpos(smap["lowerarm_r"]))
cmds.setAttr(ik_hand + ".translate", *rest)
wiggle()
check("FINGERS STAY ON THE HAND under a 40cm overpull",
      hm < rest_hm + 2.0, "%.2f cm (rest %.2f, was 33)" % (hm, rest_hm))
check("the limb itself does not stretch", abs(up - rest_up) < 0.5,
      "%.2f vs %.2f" % (up, rest_up))

# Switch there and back: IK -> FK -> IK must end hung on the root again.
done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("\nswitch arm_l to FK:", message)
check("arm_l switched to FK", done == ["arm_l -> FK"], str(done))
check("torso survived the switch",
      all(cmds.objExists(fkcontrols.controller_name(j))
          for j in ("root", "pelvis", "spine_03", "neck_01")))
check("left fingers on the FK hand",
      is_under(fkcontrols.controller_name("index_metacarpal_l"),
               fkcontrols.controller_name("hand_l")))

done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("switch arm_l back to IK:", message)
check("arm_l is IK again", "arm_l" in builder.built_limbs(),
      str(builder.built_limbs()))
check("SWITCHED LIMB IS HUNG ON THE ROOT AGAIN",
      all(is_under(builder.ik_control("arm_l", role), root_ctrl)
          for role in fkcontrols.IK_TOP_ROLES))
check("left fingers visible again",
      visible(fkcontrols.controller_name("index_metacarpal_l")))

# --- full teardown ----------------------------------------------------------
fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
now = node_count()
check("scene no dirtier than the baseline", now <= baseline,
      "%d -> %d" % (baseline, now))
check("no strays at the end", not stray_ik_roots(), str(stray_ik_roots()))
check("no rig nodes left on the bones",
      not [b for b in bones
           if cmds.listRelatives(b, children=True, type="constraint")])

cmds.currentTime(0)
cmds.select(clear=True)
cmds.autoKeyframe(state=auto_key)
print("\n%s" % ("IK UNDER ROOT WORKS" if not failures
                else "FAILURES: %s" % failures))
