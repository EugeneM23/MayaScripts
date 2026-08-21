"""Live checks for the single Build button: hybrid default, FK Limbs toggle.

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

# --- reset ---------------------------------------------------------------------
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
all_joints = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap]
cmds.cutKey(all_joints, clear=True)

baseline = len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])
print("baseline non-anim nodes: %d\n" % baseline)

cmds.setKeyframe(smap["upperarm_l"], attribute="rotateZ", time=0, value=0)
cmds.setKeyframe(smap["upperarm_l"], attribute="rotateZ", time=30, value=-30)
cmds.setKeyframe(smap["spine_03"], attribute="rotateZ", time=0, value=0)
cmds.setKeyframe(smap["spine_03"], attribute="rotateZ", time=30, value=20)

hand_ref = snap("hand_l")
foot_ref = snap("foot_l")
chest_ref = snap("spine_05")
finger_ref = snap("index_03_l")

# --- hybrid build (the default) --------------------------------------------------
message = fkcontrols.rebuild(smap, fk_limbs=False)
print("hybrid build:", message, "\n")

check("four IK limbs, no spine IK",
      builder.built_limbs() == ["arm_l", "arm_r", "leg_l", "leg_r"],
      str(builder.built_limbs()))
fk_chains = fkcontrols.built_fk_chains()
check("FK on the hybrid chains only",
      sorted(fk_chains) == sorted(fkcontrols.HYBRID_FK_CHAINS),
      str(sorted(fk_chains)))

# Fingers are posed on the BONES: no controller, no manifest, and nothing
# hanging under the IK hand for them (2026-08-18).
finger_ctrls = [fkcontrols.controller_name(j)
                for j in fkcontrols.FINGER_JOINTS]
built_finger_ctrls = [c for c in finger_ctrls if cmds.objExists(c)]
check("no finger controller exists", not built_finger_ctrls,
      str(built_finger_ctrls[:3]))
check("no finger chain is recorded",
      not [c for c in fkcontrols.FINGER_CHAINS
           if fkcontrols.chain_members(c)])
constrained_fingers = [j for j in fkcontrols.FINGER_JOINTS if j in smap
                       and cmds.listRelatives(smap[j], children=True,
                                              type="constraint")]
check("finger bones carry no constraint", not constrained_fingers,
      str(constrained_fingers[:3]))
check("no IK hand anchor built for nothing",
      not fkcontrols._anchor_in(builder.limb_set("arm_l"),
                                "arm_l_IK_anchor"))

check("hand animation survived", drift_of("hand_l", hand_ref) < 0.5,
      "%.3f cm" % drift_of("hand_l", hand_ref))
check("chest animation survived", drift_of("spine_05", chest_ref) < 0.5,
      "%.3f cm" % drift_of("spine_05", chest_ref))
check("finger animation survived", drift_of("index_03_l", finger_ref) < 0.7,
      "%.3f cm" % drift_of("index_03_l", finger_ref))

# Picker resolution: FK torso live, FK limbs dimmed, IK circles live.
resolution = window._resolution()
check("picker: spine FK button live", "spine_03" in resolution)
check("picker: limb FK button dimmed", "upperarm_l" not in resolution)
check("picker: clavicle live (own chain since 2026-08-21)",
      "clavicle_l" in resolution)
check("picker: leg IK circle live", "leg_l_ik_end" in resolution)
check("picker: arm pole circle live", "arm_r_ik_pole" in resolution)
check("picker: finger button live and pointing at the BONE",
      resolution.get("index_03_l") == smap["index_03_l"],
      str(resolution.get("index_03_l")))
check("picker: every finger button resolves",
      all(j in resolution for j in fkcontrols.FINGER_JOINTS if j in smap))

# --- the clavicles: own always-FK chains over the IK arms (2026-08-21) -----------
def wmatrix(node):
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def matrix_delta(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


clav_ctrl = fkcontrols.controller_name("clavicle_l")
spine_tip = fkcontrols.chain_tip(dict(fkcontrols.CHAINS)["spine"], smap)
tip_ctrl = fkcontrols.controller_name(spine_tip)
check("clavicle controller exists in hybrid", cmds.objExists(clav_ctrl))
check("clavicle chain recorded",
      bool(fkcontrols.chain_members("clavicle_l"))
      and bool(fkcontrols.chain_members("clavicle_r")))
clav_path = cmds.ls(clav_ctrl, long=True)[0] if cmds.objExists(clav_ctrl) else ""
tip_path = cmds.ls(tip_ctrl, long=True)[0] if cmds.objExists(tip_ctrl) else "?"
check("clavicle control hangs inside the spine-tip control",
      clav_path.startswith(tip_path + "|"), clav_path)

# We only DRIVE the bone (nothing was re-hung on the control - the user's
# call), but OverRig's IK follows the chain's parent bone on its own:
# measured 2026-08-21, poking the clavicle control moved the upperarm 1.223
# while the earlier root-bone measurement moved it not at all. So the true
# behaviour is the classic clavicle-over-IK: the shoulder leads the arm
# base, the IK hand stays planted, the elbow re-solves. Poke through the
# CTRL (the bone itself is constraint-driven), on its flat baked curve:
# read the value the curve holds, key the poke over it, and key the same
# value back - rewriting one key of a flat run with the value it already
# had damages nothing.
autokey_was = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
cmds.currentTime(15)
clav_before = wmatrix(smap["clavicle_l"])
upper_before = wmatrix(smap["upperarm_l"])
hand_before = wmatrix(smap["hand_l"])
held = cmds.getAttr(clav_ctrl + ".rotateZ")
cmds.setKeyframe(clav_ctrl, attribute="rotateZ", time=15, value=held + 25.0)
cmds.currentTime(0)
cmds.currentTime(15)  # settle (trap 14)
check("clavicle control turns the clavicle bone",
      matrix_delta(wmatrix(smap["clavicle_l"]), clav_before) > 0.05,
      "%.6f" % matrix_delta(wmatrix(smap["clavicle_l"]), clav_before))
check("the shoulder leads the IK arm base (OverRig's own follow)",
      matrix_delta(wmatrix(smap["upperarm_l"]), upper_before) > 0.05,
      "%.6f" % matrix_delta(wmatrix(smap["upperarm_l"]), upper_before))
check("the IK hand stays planted while the clavicle turns",
      matrix_delta(wmatrix(smap["hand_l"]), hand_before) < 1e-3,
      "%.9f" % matrix_delta(wmatrix(smap["hand_l"]), hand_before))
cmds.setKeyframe(clav_ctrl, attribute="rotateZ", time=15, value=held)
cmds.currentTime(0)
cmds.currentTime(15)
check("clavicle poke restored",
      matrix_delta(wmatrix(smap["clavicle_l"]), clav_before) < 1e-4,
      "%.9f" % matrix_delta(wmatrix(smap["clavicle_l"]), clav_before))
cmds.autoKeyframe(state=autokey_was)
cmds.currentTime(0)

# The headline of the split: an arm switch no longer eats the clavicle.
fkcontrols.switch_limbs(smap, ["arm_l"])   # IK -> FK
check("clavicle control survives arm -> FK",
      cmds.objExists(clav_ctrl)
      and bool(fkcontrols.chain_members("clavicle_l")))
upper_ctrl = fkcontrols.controller_name("upperarm_l")
upper_path = (cmds.ls(upper_ctrl, long=True) or [""])[0]
check("FK arm coupled inside the clavicle control",
      upper_path.startswith(cmds.ls(clav_ctrl, long=True)[0] + "|")
      if cmds.objExists(clav_ctrl) and upper_path else False, upper_path)
fkcontrols.switch_limbs(smap, ["arm_l"])   # FK -> IK again
check("clavicle control survives arm -> IK",
      cmds.objExists(clav_ctrl)
      and bool(fkcontrols.chain_members("clavicle_l")))
check("hand animation survived both switches",
      drift_of("hand_l", hand_ref) < 0.5,
      "%.3f cm" % drift_of("hand_l", hand_ref))

# --- FK Limbs toggle: full FK from this dirty state ------------------------------
message = fkcontrols.rebuild(smap, fk_limbs=True)
print("\nfull FK build:", message, "\n")
check("no IK left", builder.built_limbs() == [], str(builder.built_limbs()))
check("every buildable chain is FK",
      sorted(fkcontrols.built_fk_chains()) == sorted(fkcontrols.BUILDABLE),
      str(sorted(fkcontrols.built_fk_chains())))
check("still no finger controller with FK Limbs on",
      not [c for c in finger_ctrls if cmds.objExists(c)])
check("hand animation survived the flip",
      drift_of("hand_l", hand_ref) < 0.5,
      "%.3f cm" % drift_of("hand_l", hand_ref))

resolution = window._resolution()
check("picker: limb FK buttons live now", "upperarm_l" in resolution)
check("picker: IK circles dimmed now", "leg_l_ik_end" not in resolution)

# --- and back to hybrid, then to baseline ----------------------------------------
message = fkcontrols.rebuild(smap, fk_limbs=False)
print("\nhybrid again:", message, "\n")
check("hybrid restored",
      builder.built_limbs() == ["arm_l", "arm_r", "leg_l", "leg_r"]
      and sorted(fkcontrols.built_fk_chains())
      == sorted(fkcontrols.HYBRID_FK_CHAINS))
check("foot animation intact after three builds",
      drift_of("foot_l", foot_ref) < 0.5,
      "%.3f cm" % drift_of("foot_l", foot_ref))

fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene no dirtier than the baseline", now <= baseline,
      "%d -> %d" % (baseline, now))
check("hand animation on the bones at the end",
      drift_of("hand_l", hand_ref) < 0.5,
      "%.3f cm" % drift_of("hand_l", hand_ref))

cmds.currentTime(0)
cmds.cutKey(all_joints, clear=True)
cmds.select(clear=True)
print("\n%s" % ("HYBRID BUILD WORKS" if not failures
                else "FAILURES: %s" % failures))
