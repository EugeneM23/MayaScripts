"""Live proof for the weapon aim, run through the command port.

Three claims carry the feature, and each gets measured rather than argued:

1. building the aim does not move the sword -- world matrices compared
   element-wise across EVERY frame of the range, including the first and last,
   because an edge-clipping bake is exactly what trap 12 was and only a
   full-range comparison sees it;
2. the aim actually aims -- dragging `_top` turns the BLADE toward it, not the
   local +X, and dragging `_side` rolls the blade about it;
3. Bake+Delete on the sword or a locator takes the aim and nothing else: the
   sword keeps its animation, the character's FK/IK manifests are untouched,
   and an arm control never resolves to the aim.

Bridge hygiene, all of it load-bearing here: never `cmds.undo()` (the whole
script is one command, so an undo reverts a prior chunk), autoKey off around
every poke (trap 14), time wiggled before measuring, and the scene left as it
was found -- the sword's own channels are restored ONLY if this run found them
unanimated, because "it has animCurves" is not "the animator has animation"
(trap 30) and the reverse mistake is worse.
"""

import math
import sys

import maya.api.OpenMaya as om
import maya.cmds as cmds

# The session has the previous versions of these modules cached, and this proof
# is about code that did not exist then. Parent packages go too: dropping only
# `pkg.module` leaves the stale object bound as an attribute of `pkg`, so the
# next `from pkg import module` hands the old one straight back.
for _name in [n for n in list(sys.modules)
              if n == "maya_overrig" or n.startswith("maya_overrig.")
              or n == "maya_scenesetup" or n.startswith("maya_scenesetup.")]:
    del sys.modules[_name]

from maya_overrig import aimrig, builder, fkcontrols
from maya_scenesetup import aim as weaponaim
from maya_scenesetup import attach
from maya_scenesetup import catalog
from maya_scenesetup import connect as linking
from maya_scenesetup import skeleton

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              "  " + detail if detail else ""))


def world_matrix(node):
    return cmds.xform(node, query=True, matrix=True, worldSpace=True)


def biggest_difference(left, right):
    return max(abs(a - b) for a, b in zip(left, right))


def sample(node, frames):
    """World matrix of one node at each frame, current time restored."""
    restore = cmds.currentTime(query=True)
    out = []
    for frame in frames:
        cmds.currentTime(frame)
        out.append(world_matrix(node))
    cmds.currentTime(restore)
    return out


def worst_drift(before, after):
    return max(biggest_difference(one, two)
               for one, two in zip(before, after))


def world_point(node):
    return om.MVector(*cmds.xform(node, query=True, worldSpace=True,
                                  translation=True))


def axis_direction(node, axis):
    """World direction of one of `node`'s local axes, normalised."""
    matrix = om.MMatrix(world_matrix(node))
    local = [0.0, 0.0, 0.0]
    local[axis] = 1.0
    turned = om.MVector(local[0], local[1], local[2]).rotateBy(
        om.MTransformationMatrix(matrix).rotation(asQuaternion=True))
    return turned.normal()


def angle_between(one, two):
    """Degrees between two vectors, clamped against float noise."""
    dot = max(-1.0, min(1.0, one.normal() * two.normal()))
    return math.degrees(math.acos(dot))


def points_at(node, axis, target):
    """Degrees between `node`'s local `axis` and the direction to `target`."""
    return angle_between(axis_direction(node, axis),
                         world_point(target) - world_point(node))


def unkey_and_move(locator, offset):
    """Drag a locator: drop its baked curves, then set the value.

    The curves have to go first or the next time change restores the old
    position -- and these locators are ours and about to be deleted, so
    cutting them costs nothing. autoKey off regardless (trap 14).
    """
    state = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        cmds.cutKey(locator, clear=True, attribute=["translateX", "translateY",
                                                    "translateZ"])
        was = cmds.xform(locator, query=True, worldSpace=True,
                         translation=True)
        cmds.xform(locator, worldSpace=True,
                   translation=(was[0] + offset[0], was[1] + offset[1],
                                was[2] + offset[2]))
    finally:
        cmds.autoKeyframe(state=state)


def manifest_state():
    """The character's rig, as counts nothing here should change."""
    return (sorted(builder.built_limbs()),
            sorted(fkcontrols.built_fk_chains()),
            sum(len(overrig_members(builder.limb_set(name)))
                for name, _ in builder.LIMBS))


def overrig_members(set_name):
    from maya_overrig import overrig
    return overrig.set_members(set_name)


# --- baseline -------------------------------------------------------------

selection_at_start = cmds.ls(selection=True, long=True) or []
autokey_at_start = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)

entry = catalog.by_key("LongSword_02")
root = skeleton.current_root()
scene_map = skeleton.scene_map(root)
bone = skeleton.resolve_bone(root, entry.bone)
check("a character with a weapon bone", bool(root and bone), str(bone))

weapon = attach.find_attached(bone) or linking.linked_weapon()
if weapon is None:
    weapon, _note = attach.attach(entry, bone)
    print("NOTE  no weapon was attached; this run added one")
check("a weapon to aim", weapon is not None, str(weapon))

model = attach.model_root(weapon)
check("the weapon has geometry", model != weapon, str(model))

start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
every_frame = list(range(start, end + 1))
build_frame = cmds.currentTime(query=True)

CHANNELS = ["translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ"]
model_was_animated = bool(
    cmds.listConnections(model, source=True, destination=False,
                         type="animCurve"))
model_rest = {c: cmds.getAttr(model + "." + c) for c in CHANNELS}
print("NOTE  model animated before this run:", model_was_animated)

# Any aim left by a previous run goes first, or "already" refuses everything.
for stale in aimrig.aim_sets():
    print("NOTE  removing a stale aim:", stale, aimrig.bake_aims([stale]))

extents = weaponaim.local_extents(model)
check("the model measures", extents is not None, str(extents))
blade_axis = sorted(range(3),
                    key=lambda a: (-(extents[1][a] - extents[0][a]), a))[0]
side_axis = sorted(range(3),
                   key=lambda a: (-(extents[1][a] - extents[0][a]), a))[1]
top_offset, side_offset = weaponaim.placement(*extents)
print("NOTE  blade axis {0}, side axis {1}, top {2}, side {3}".format(
    "XYZ"[blade_axis], "XYZ"[side_axis], top_offset, side_offset))

rig_before = manifest_state()
sword_before = sample(model, every_frame)

# --- gate 1: build the aim, and nothing moves -----------------------------

message = weaponaim.add_aim(entry, weapon)
print("Add Aim said:", message)
check("the press reported an aim", "Aim on" in message, message)

sets = aimrig.aim_sets()
check("exactly one aim manifest", len(sets) == 1, str(sets))
manifest = sets[0] if sets else None

cmds.currentTime(build_frame)
drift = worst_drift(sword_before, sample(model, every_frame))
check("the sword did not move when the aim was built", drift < 1e-3,
      "worst world-matrix element {0:.9f} over {1} frames".format(
          drift, len(every_frame)))

# --- gate 2: the locators landed where placement said ---------------------

members = overrig_members(manifest) if manifest else []
locators = [m for m in members
            if cmds.listRelatives(m, children=True, type="locator")]
tops = [m for m in locators if m.endswith("_top")]
sides = [m for m in locators if m.endswith("_side")]
check("two locators, one top and one side",
      len(tops) == 1 and len(sides) == 1,
      "{0} locator(s): {1}".format(len(locators),
                                   [m.split("|")[-1] for m in locators]))

if tops and sides:
    top, side = tops[0], sides[0]
    matrix = om.MMatrix(world_matrix(model))
    for label, node, offset in (("top", top, top_offset),
                                ("side", side, side_offset)):
        want = om.MPoint(offset[0], offset[1], offset[2]) * matrix
        got = world_point(node)
        gap = (om.MVector(want[0], want[1], want[2]) - got).length()
        check("the {0} locator is where placement said".format(label),
              gap < 1e-3, "{0:.6f} cm off".format(gap))

    check("the top locator clears the tip",
          abs(top_offset[blade_axis]) > abs(extents[1][blade_axis]),
          "{0:.3f} vs tip {1:.3f}".format(top_offset[blade_axis],
                                          extents[1][blade_axis]))

# --- gate 5: what the manifest holds, and what it must not ---------------

if manifest:
    constraints = [m for m in members if cmds.objectType(m, isAType="constraint")]
    check("the manifest holds the aim constraint", bool(constraints),
          str([c.split("|")[-1] for c in constraints]))
    check("the manifest does NOT hold the sword", model not in members)
    check("the manifest does NOT hold the weapon", weapon not in members)
    handles = aimrig.aim_handles(manifest)
    check("the sword and the weapon are handles",
          model in handles and weapon in handles,
          str([h.split("|")[-1] for h in handles]))
    check("the source resolves back to the sword",
          aimrig.aim_source(manifest) == model,
          str(aimrig.aim_source(manifest)))

# --- gate 9: a second press changes nothing ------------------------------

again = weaponaim.add_aim(entry, weapon)
check("a second press refuses", again == weaponaim.ALREADY_MESSAGE, again)
check("and left exactly one aim", len(aimrig.aim_sets()) == 1,
      str(aimrig.aim_sets()))

# --- gate 8: an arm control never resolves to the aim --------------------

arm_control = builder.ik_control("arm_r", "end")
if not arm_control:
    chain = dict(fkcontrols.CHAINS).get("arm_r", ())
    arm_control = fkcontrols.chain_root_control(chain, scene_map)
if arm_control and cmds.objExists(arm_control):
    cmds.select(arm_control, replace=True)
    check("an arm control does not resolve to the aim",
          aimrig.aim_targets() == [], str(arm_control))
else:
    print("NOTE  no arm rig in the scene; the arm-control gate is skipped")

# --- gate 3 and 4: the aim aims -----------------------------------------

if tops and sides:
    cmds.currentTime(build_frame)
    blade_gap_before = points_at(model, blade_axis, top)
    side_gap_before = points_at(model, side_axis, side)
    check("the blade starts pointing at the top locator",
          blade_gap_before < 2.0,
          "{0:.4f} deg".format(blade_gap_before))
    check("the side axis starts pointing at the side locator",
          side_gap_before < 2.0, "{0:.4f} deg".format(side_gap_before))

    before_drag = world_matrix(model)
    unkey_and_move(top, (60.0, 0.0, 60.0))
    cmds.currentTime(build_frame + 1)
    cmds.currentTime(build_frame)
    turned = biggest_difference(before_drag, world_matrix(model))
    blade_gap = points_at(model, blade_axis, top)
    check("dragging top turned the sword", turned > 1e-3,
          "worst world-matrix element {0:.6f}".format(turned))
    check("the BLADE still points at the top locator", blade_gap < 2.0,
          "{0:.4f} deg (local +X is at {1:.2f} deg)".format(
              blade_gap, points_at(model, 0, top)))

    before_roll = world_matrix(model)
    unkey_and_move(side, (0.0, 90.0, 0.0))
    cmds.currentTime(build_frame + 1)
    cmds.currentTime(build_frame)
    rolled = biggest_difference(before_roll, world_matrix(model))
    check("dragging side rolled the sword", rolled > 1e-3,
          "worst world-matrix element {0:.6f}".format(rolled))
    check("the blade still points at the top locator after the roll",
          points_at(model, blade_axis, top) < 2.0,
          "{0:.4f} deg".format(points_at(model, blade_axis, top)))
    check("the side axis follows the side locator",
          points_at(model, side_axis, side) < 2.0,
          "{0:.4f} deg".format(points_at(model, side_axis, side)))

# --- gate 6: Bake+Delete with the sword selected ------------------------

posed = sample(model, every_frame)
cmds.select(model, replace=True)
targets = aimrig.aim_targets()
check("selecting the sword resolves to the aim", targets == [manifest],
      str(targets))

print("bake said:", aimrig.bake_aims(targets))
check("the aim manifest is gone", not aimrig.aim_sets(),
      str(aimrig.aim_sets()))
check("the locators are gone",
      not any(cmds.objExists(m) for m in locators))
check("the sword has no constraint left",
      not (cmds.listRelatives(model, children=True, type="constraint") or []))

kept = worst_drift(posed, sample(model, every_frame))
check("the sword kept its animation through the bake", kept < 1e-3,
      "worst world-matrix element {0:.9f} over {1} frames".format(
          kept, len(every_frame)))
check("the character's rig is untouched", manifest_state() == rig_before,
      "{0} -> {1}".format(rig_before, manifest_state()))

# --- gate 7 and 10: round trip, this time removed from a locator --------

round_trip_before = sample(model, every_frame)
message = weaponaim.add_aim(entry, weapon)
check("the aim can be rebuilt after a bake", "Aim on" in message, message)

sets = aimrig.aim_sets()
manifest = sets[0] if sets else None
members = overrig_members(manifest) if manifest else []
locators = [m for m in members
            if cmds.listRelatives(m, children=True, type="locator")]

if locators:
    cmds.select(locators[0], replace=True)
    targets = aimrig.aim_targets()
    check("selecting a locator resolves to the aim", targets == [manifest],
          str(targets))
    print("bake said:", aimrig.bake_aims(targets))
    check("the aim is gone again", not aimrig.aim_sets(),
          str(aimrig.aim_sets()))

trip = worst_drift(round_trip_before, sample(model, every_frame))
check("the round trip left the sword where it was", trip < 1e-3,
      "worst world-matrix element {0:.9f}".format(trip))

# --- leave the scene as we found it -------------------------------------

if not model_was_animated:
    cmds.cutKey(model, clear=True, attribute=CHANNELS)
    for channel, value in model_rest.items():
        cmds.setAttr(model + "." + channel, value)
    print("NOTE  the sword's channels were restored to what this run found")
else:
    print("NOTE  the sword was animated before this run; its curves are left "
          "as the bake wrote them")

cmds.currentTime(build_frame)
if selection_at_start:
    cmds.select([s for s in selection_at_start if cmds.objExists(s)],
                replace=True)
else:
    cmds.select(clear=True)
cmds.autoKeyframe(state=autokey_at_start)

passed = sum(1 for _, ok, _ in RESULTS if ok)
print("\n{0}/{1} green".format(passed, len(RESULTS)))
for name, ok, detail in RESULTS:
    if not ok:
        print("  FAILED: {0}  {1}".format(name, detail))
