"""Live proof that the fingers are posed on the BONES.

Finger FK controllers stopped being built on 2026-08-18 at the user's call
("буду анимировать на костях"). What has to hold, in the animator's own scene:

  1. neither build mode creates a finger controller or a finger manifest;
  2. the finger bones stay clean -- no constraint, no rig curve -- and take
     keys directly;
  3. the IK hand anchor, which existed only to carry finger chains, is no
     longer built for nothing;
  4. the picker's 38 finger buttons are LIVE and select those bones, while a
     controller, where one exists, still wins;
  5. a finger bone in the selection resolves to nothing in Switch and in
     Bake+Delete -- the safe direction of failure is "nothing happens";
  6. an arm Switch and a full Bake+Delete are unchanged, and the finger bones
     ride the hand through both;
  7. a scene rigged BEFORE the change still comes apart: the finger chains are
     still in `CHAINS`, so a Build bakes yesterday's finger rig back on the
     way past. Proved by building one finger chain through a patched
     `BUILDABLE` and then tearing it down through the shipping code.

Run inside Maya through the bridge runner (its explicit globals dict is what
lets these helpers see module-level names -- trap 17). Binds explicitly.

House rules this script obeys, each paid for once already: no `cmds.undo()`
(the whole bridge script is one command, so undo reverts a prior chunk);
autoKey off around every poke (trap 14); values read before they are written
back, never written as literals; keyed channels left alone; and the skeleton's
animation is only cut when NO bone carries anything that moves (trap 30).
"""

import sys
from contextlib import contextmanager

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO not in sys.path:
    sys.path.append(REPO)

for _name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[_name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import bodymap, builder, fkchains, fkcontrols, overrig
from maya_overrig import pickerstate

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


def wiggle():
    """Settle the DAG: a read straight after setAttr returns stale mixtures."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, edit=True)
    cmds.currentTime(now, edit=True)


@contextmanager
def pushed(plug, value):
    """Set a plug, yield, put back what was there. Never on a keyed channel."""
    was = cmds.getAttr(plug)
    try:
        cmds.setAttr(plug, value)
        wiggle()
        yield
    finally:
        cmds.setAttr(plug, was)
        wiggle()


def moving_curve(node):
    """True when the node carries an animCurve whose VALUES change.

    "The bone has animCurves" is not "the animator has animation": every build
    leaves constant baked curves behind, and a reset guarded on mere existence
    reads an idle skeleton as precious for ever (trap 30).
    """
    for curve in cmds.listConnections(node, type="animCurve") or []:
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        if values and (max(values) - min(values)) > 1e-4:
            return True
    return False


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

auto_key = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
selection = cmds.ls(selection=True, long=True)
frame = cmds.currentTime(query=True)

gate = overrig.mel_gate()
if gate:
    print("REFUSED before starting:", gate)
    print("\nFAILURES: ['blocked before the first build']")
    raise SystemExit

window = maya_overrig.show_picker()
roots = builder.character_roots()
if not roots:
    print("no skeleton in the scene")
    raise SystemExit
# More than one candidate: take the one actually called `root` rather than
# whichever Maya listed first (a built rig reports a dozen "skeletons" --
# trap 1 -- and this script may arrive on a rigged scene).
named = [r for r in roots if r.split("|")[-1].split(":")[-1] == "root"]
cmds.select((named or roots)[0], replace=True)
window.connect_to_selection()
smap = window._scene_map
print("bound to %s, %d joints" % (window.bound_root(), len(smap)))
if not smap:
    print("the picker did not bind; nothing to verify")
    raise SystemExit

FINGERS = [j for j in fkcontrols.FINGER_JOINTS if j in smap]
FINGER_CTRLS = [fkcontrols.controller_name(j) for j in fkcontrols.FINGER_JOINTS]
BUILD_JOINTS = [j for name, chain in fkcontrols.CHAINS
                if name in fkcontrols.BUILDABLE for j in chain if j in smap]
print("%d finger bones, %d buildable bones" % (len(FINGERS),
                                               len(BUILD_JOINTS)))


def live_finger_ctrls():
    return [c for c in FINGER_CTRLS if cmds.objExists(c)]


def recorded_finger_chains():
    return [c for c in fkcontrols.FINGER_CHAINS if fkcontrols.chain_members(c)]


def constrained_fingers():
    return [j for j in FINGERS
            if cmds.listRelatives(smap[j], children=True, type="constraint")]


def anchor_of(limb):
    """The recorded anchor, WITHOUT creating one -- `_limb_anchor` would."""
    return fkcontrols._anchor_in(builder.limb_set(limb), limb + "_IK_anchor")


# --- reset from any state --------------------------------------------------
was_ik = builder.built_limbs()
was_fk = fkcontrols.built_fk_chains()
print("scene arrived with IK %s, FK %s" % (was_ik, was_fk))

if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())

bones = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap
         and cmds.objExists(smap[b.joint])]
stuck = [b for b in bones
         if cmds.listRelatives(b, children=True, type="constraint")]
if stuck:
    print("reset: sweeping %d constrained bones" % len(stuck))
    overrig.fast_bake(stuck)
    overrig.delete_constraint_attributes(stuck)
    for bone in stuck:
        for con in cmds.listRelatives(bone, children=True, type="constraint",
                                      fullPath=True) or []:
            if cmds.objExists(con):
                cmds.delete(con)
for s in cmds.ls("RigPicker_*", type="objectSet") or []:
    if not overrig.set_members(s):
        cmds.delete(s)

virgin = not any(moving_curve(b) for b in bones)
print("skeleton carries real animation: %s" % (not virgin))
if virgin:
    # A bake walked the timeline; come back before cutting or every bone
    # freezes on the last baked pose -- and the next Build bakes THAT as the
    # build pose (the tell is the ring-guess count jumping).
    cmds.currentTime(frame, edit=True)
    cmds.cutKey(bones, clear=True)
    cmds.currentTime(frame, edit=True)

baseline = node_count()
print("baseline non-anim nodes: %d\n" % baseline)

cmds.currentTime(frame, edit=True)
FINGER_REST = {j: wpos(smap[j]) for j in FINGERS}
hand_rest = {side: wpos(smap["hand_" + side]) for side in ("l", "r")}

# ---------------------------------------------------------------------------
# section 1: the hybrid build creates nothing for the fingers
# ---------------------------------------------------------------------------

print("=== 1. hybrid build ===")
print(fkcontrols.rebuild(smap, fk_limbs=False), "\n")

check("four IK limbs built",
      builder.built_limbs() == ["arm_l", "arm_r", "leg_l", "leg_r"],
      str(builder.built_limbs()))
check("FK on the hybrid chains only",
      sorted(fkcontrols.built_fk_chains())
      == sorted(fkcontrols.HYBRID_FK_CHAINS),
      str(sorted(fkcontrols.built_fk_chains())))
check("NO FINGER CONTROLLER EXISTS", not live_finger_ctrls(),
      str(live_finger_ctrls()[:3]))
check("no finger chain is recorded", not recorded_finger_chains(),
      str(recorded_finger_chains()))
check("finger bones carry no constraint", not constrained_fingers(),
      str(constrained_fingers()[:3]))
for limb in ("arm_l", "arm_r"):
    check("no IK hand anchor built for nothing: " + limb,
          not anchor_of(limb), str(anchor_of(limb)))

drift = max(dist(FINGER_REST[j], wpos(smap[j])) for j in FINGERS)
check("finger bones did not move through the build", drift < 0.05,
      "worst %.5f cm" % drift)

# ---------------------------------------------------------------------------
# section 2: the finger bones are animatable, directly
# ---------------------------------------------------------------------------

print("\n=== 2. the bones take the animation ===")
probe = "index_02_l" if "index_02_l" in smap else FINGERS[0]
tip = "index_03_l" if "index_03_l" in smap else probe
plug = smap[probe] + ".rotateZ"

check("the finger bone's rotate is settable",
      cmds.getAttr(plug, settable=True), plug)
check("nothing is driving it",
      not (cmds.listConnections(plug, source=True, destination=False) or []),
      str(cmds.listConnections(plug, source=True, destination=False)))

if cmds.listConnections(smap[probe], type="animCurve"):
    # Any curve at all, not just a moving one: a setAttr against a constant
    # curve is silently overridden on the next evaluation, so the poke would
    # measure zero and the gate would fail for the wrong reason.
    print("NOTE  %s carries curves; the poke is skipped" % probe)
else:
    tip_before = wpos(smap[tip])
    base = cmds.getAttr(plug)
    with pushed(plug, base + 35.0):
        moved = dist(tip_before, wpos(smap[tip]))
    check("TURNING THE BONE MOVES THE FINGER", moved > 0.5,
          "%.3f cm on 35 deg" % moved)
    check("and it comes back", dist(tip_before, wpos(smap[tip])) < 0.001,
          "%.6f cm" % dist(tip_before, wpos(smap[tip])))

# ---------------------------------------------------------------------------
# section 3: the picker's finger buttons select those bones
# ---------------------------------------------------------------------------

print("\n=== 3. the picker ===")
resolution = window._resolution()

missing = [j for j in FINGERS if j not in resolution]
check("every finger button resolves", not missing, str(missing[:4]))
wrong = [j for j in FINGERS if resolution.get(j) != smap[j]]
check("EVERY FINGER BUTTON POINTS AT ITS BONE", not wrong, str(wrong[:3]))
check("a torso button still points at its controller",
      resolution.get("spine_03") == cmds.ls(
          fkcontrols.controller_name("spine_03"), long=True)[0],
      str(resolution.get("spine_03")))
check("an IK limb's FK button stays dim", "upperarm_l" not in resolution)
check("the IK circles are live", "arm_l_ik_end" in resolution
      and "leg_r_ik_pole" in resolution)

# Selecting the bone in the viewport must light the button.
cmds.select(smap[probe], replace=True)
window.sync_from_scene()
lit = pickerstate.selected_ids(window._resolution(),
                               set(cmds.ls(selection=True, long=True) or []))
check("selecting the bone lights its button", lit == [probe], str(lit))

# The controller still wins where one exists -- the pure rule, checked on
# data so no rig has to be built to prove it.
both = pickerstate.resolve({probe: "|" + probe + "_FK_ctrl"}, {},
                           {probe: smap[probe]})
check("a controller would still win over the bone",
      both[probe] == "|" + probe + "_FK_ctrl", both[probe])

# ---------------------------------------------------------------------------
# section 4: a finger bone resolves to nothing dangerous
# ---------------------------------------------------------------------------

print("\n=== 4. Switch and Bake+Delete with a finger bone selected ===")
cmds.select([smap[j] for j in FINGERS], replace=True)
ik_hit, fk_hit = fkcontrols.bake_targets(smap)
check("BAKE+DELETE RESOLVES 38 FINGER BONES TO NOTHING",
      (ik_hit, fk_hit) == ([], []), "%s %s" % (ik_hit, fk_hit))
owner = fkcontrols.switchable_bones(smap)
check("no finger bone is switchable",
      not [j for j in FINGERS if smap[j] in owner])

# ---------------------------------------------------------------------------
# section 5: an arm switch, both ways
# ---------------------------------------------------------------------------

print("\n=== 5. arm switch ===")
cmds.select(builder.ik_control("arm_l", "end"), replace=True)
done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("to FK:", message)
check("arm_l switched to FK", done == ["arm_l -> FK"], str(done))
check("no finger controller appeared", not live_finger_ctrls(),
      str(live_finger_ctrls()[:3]))
check("finger bones still ride the hand bone",
      is_under(smap["index_metacarpal_l"], smap["hand_l"])
      if "index_metacarpal_l" in smap
      else is_under(smap["index_01_l"], smap["hand_l"]))

done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("back to IK:", message)
check("arm_l switched back to IK", "arm_l" in builder.built_limbs(),
      str(builder.built_limbs()))
check("still no finger controller", not live_finger_ctrls())
check("still no anchor built", not anchor_of("arm_l"), str(anchor_of("arm_l")))
cmds.currentTime(frame, edit=True)
check("the hand did not drift through the round trip",
      dist(hand_rest["l"], wpos(smap["hand_l"])) < 0.05,
      "%.5f cm" % dist(hand_rest["l"], wpos(smap["hand_l"])))

# ---------------------------------------------------------------------------
# section 6: FK Limbs on -- still no fingers
# ---------------------------------------------------------------------------

print("\n=== 6. full FK build ===")
print(fkcontrols.rebuild(smap, fk_limbs=True), "\n")
check("no IK left", not builder.built_limbs(), str(builder.built_limbs()))
check("every buildable chain is FK",
      sorted(fkcontrols.built_fk_chains()) == sorted(fkcontrols.BUILDABLE),
      str(sorted(fkcontrols.built_fk_chains())))
check("STILL NO FINGER CONTROLLER WITH FK LIMBS ON",
      not live_finger_ctrls(), str(live_finger_ctrls()[:3]))
built = [j for j in BUILD_JOINTS
         if cmds.objExists(fkcontrols.controller_name(j))]
check("one controller per buildable bone (%d)" % len(BUILD_JOINTS),
      len(built) == len(BUILD_JOINTS),
      "%d of %d" % (len(built), len(BUILD_JOINTS)))

# ---------------------------------------------------------------------------
# section 7: a scene rigged BEFORE the change still comes apart
# ---------------------------------------------------------------------------
#
# The reason the finger chains stay in CHAINS. Build one through a patched
# BUILDABLE -- which is exactly what an older version of this tool did -- then
# put the real table back and let the shipping teardown deal with it.

print("\n=== 7. a legacy finger rig still bakes back ===")
LEGACY = "index_l"
chain = dict(fkcontrols.CHAINS)[LEGACY]
tip_bone = fkcontrols.chain_tip(chain, smap)
legacy_rest = wpos(smap[tip_bone])

real_buildable = fkchains.BUILDABLE
patched = tuple(list(real_buildable) + [LEGACY])
fkchains.BUILDABLE = patched
fkcontrols.BUILDABLE = patched
try:
    count, message = fkcontrols.build_fk(smap, only=[LEGACY])
    print("legacy build:", message)
finally:
    fkchains.BUILDABLE = real_buildable
    fkcontrols.BUILDABLE = real_buildable

legacy_ctrl = fkcontrols.chain_root_control(chain, smap)
check("the legacy finger rig was built",
      bool(fkcontrols.chain_members(LEGACY))
      and cmds.objExists(legacy_ctrl), str(legacy_ctrl))
check("the shipping table refuses it again",
      fkcontrols.build_targets([LEGACY]) == [], LEGACY)

print("rebuild over it:", fkcontrols.rebuild(smap, fk_limbs=False), "\n")
check("THE LEGACY FINGER RIG IS GONE",
      not fkcontrols.chain_members(LEGACY)
      and not cmds.objExists(legacy_ctrl))
check("its manifest set went too",
      not cmds.objExists(fkcontrols.chain_set(LEGACY)),
      fkcontrols.chain_set(LEGACY))
check("no finger controller survived it", not live_finger_ctrls(),
      str(live_finger_ctrls()[:3]))
check("the finger bone is unconstrained again",
      tip_bone not in constrained_fingers())
cmds.currentTime(frame, edit=True)
check("the finger bone did not drift through all of it",
      dist(legacy_rest, wpos(smap[tip_bone])) < 0.2,
      "%.5f cm" % dist(legacy_rest, wpos(smap[tip_bone])))

# ---------------------------------------------------------------------------
# section 8: teardown
# ---------------------------------------------------------------------------

print("\n=== 8. teardown ===")
if fkcontrols.has_fk():
    print(fkcontrols.bake_fk(smap)[1])
if builder.has_build():
    print(builder.bake_limbs(smap, builder.built_limbs()).message)

check("nothing recorded", not fkcontrols.has_fk() and not builder.has_build())
check("no controller left anywhere", not cmds.ls("*_FK_ctrl"),
      str(cmds.ls("*_FK_ctrl") or [])[:70])
now = node_count()
check("scene no dirtier than the baseline", now <= baseline,
      "%d -> %d" % (baseline, now))

cmds.currentTime(frame, edit=True)
worst = max(dist(FINGER_REST[j], wpos(smap[j])) for j in FINGERS)
check("EVERY FINGER BONE IS WHERE IT STARTED", worst < 0.2,
      "worst %.5f cm over %d bones" % (worst, len(FINGERS)))

if virgin:
    cmds.currentTime(frame, edit=True)
    cmds.cutKey(bones, clear=True)
    cmds.currentTime(frame, edit=True)

# Leave the animator the rig they had, if they had one.
if was_ik or was_fk:
    print("\nrestoring the hybrid rig:",
          fkcontrols.rebuild(smap, fk_limbs=False))
else:
    print("\nscene left unrigged, as it arrived")

cmds.autoKeyframe(state=auto_key)
cmds.currentTime(frame, edit=True)
if selection:
    cmds.select([s for s in selection if cmds.objExists(s)], replace=True)
else:
    cmds.select(clear=True)

print("\n%s" % ("FINGERS ON BONES: ALL GREEN" if not failures
                else "FAILURES: %s" % failures))
