"""Live proof for Connect / Disconnect Arms, run through the command port.

The claim the whole feature rests on is that nothing moves: the weapon leaves
the skeleton, the hands change what they hang on, and the animation on screen
is the same frame for frame. So the hands' world matrices are sampled across
the timeline before the first press and compared after every step.

Bind explicitly; the user works in the scene between runs. Never cmds.undo()
from a bridge script -- the whole script is one command.
"""

import maya.cmds as cmds

from maya_overrig import builder
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


def sample_hands(hands, frames):
    """World matrix of each hand bone at each frame."""
    restore = cmds.currentTime(query=True)
    samples = []
    for frame in frames:
        cmds.currentTime(frame)
        samples.append([world_matrix(hand) for hand in hands])
    cmds.currentTime(restore)
    return samples


def worst_drift(before, after):
    return max(biggest_difference(one, two)
               for frame_a, frame_b in zip(before, after)
               for one, two in zip(frame_a, frame_b))


entry = catalog.by_key("LongSword_02")
root = skeleton.current_root()
scene_map = skeleton.scene_map(root)
bone = skeleton.resolve_bone(root, entry.bone)
check("a character with a weapon bone", bool(root and bone), str(bone))
hand_bone = attach.parent_bone(bone)
check("the weapon bone has a parent to live under", hand_bone is not None,
      str(hand_bone))

hands = [scene_map[name] for name in ("hand_l", "hand_r") if name in scene_map]
check("both hand bones resolved", len(hands) == 2, str(len(hands)))

start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
frames = sorted(set([start, (start + end) // 2, end]))

# --- the weapon has to be in the hand to begin with -----------------------
weapon = (attach.find_attached(hand_bone) or attach.find_attached(bone)
          or linking.linked_weapon())
if weapon is None:
    weapon, _note = attach.attach(entry, hand_bone, bone)
    print("NOTE  no weapon was attached; this run added one")
if linking.linked_weapon():
    linking.disconnect(linking.linked_weapon(), hand_bone)
    print("NOTE  the arms were already connected; this run disconnected first")

weapon = attach.find_attached(hand_bone) or attach.find_attached(bone)
check("starting with the weapon in the hand", weapon is not None, str(weapon))

before = sample_hands(hands, frames)

# --- connect --------------------------------------------------------------
message = linking.connect(weapon, scene_map)
print("connect said:", message)

weapon = linking.linked_weapon()
check("the link is found from the hand control", weapon is not None,
      str(weapon))
check("the weapon left the skeleton",
      weapon is not None
      and not cmds.listRelatives(weapon, parent=True, fullPath=True),
      "parent: {0}".format(
          cmds.listRelatives(weapon, parent=True, fullPath=True)
          if weapon else "?"))
check("the weapon carries its own animation", attach.is_animated(weapon))

built = builder.built_limbs()
check("both arms are IK",
      "arm_l" in built and "arm_r" in built, str(sorted(built)))

geometry = attach.model_root(weapon)
check("the weapon has geometry to hang on", geometry is not None, str(geometry))
if geometry == weapon:
    print("NOTE  the marked node IS the geometry (single mesh, 2026-08-20) - "
          "the normal case")

for limb in linking.ARMS:
    node = builder.ik_control(limb, "end")
    inside = bool(node) and builder._is_inside(
        cmds.ls(node, long=True)[0], geometry)
    check("{0} hand control rides the GEOMETRY".format(limb), inside,
          str(node))

drift = worst_drift(before, sample_hands(hands, frames))
check("the hands did not move", drift < 1e-4,
      "worst world-matrix element {0:.9f} over frames {1}".format(
          drift, frames))

# --- and the point of the whole feature ----------------------------------
# Nesting and stillness are not the claim. The claim is that dragging the
# sword drags the hands, and the first version of this script never moved
# anything -- which is how the hands ended up hung beside the sword instead
# of on it. The geometry carries no keys of its own, so it can be turned and
# put back.
plug = geometry + ".translateX"
autokey = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
poke_frame = int(cmds.currentTime(query=True))
driven = bool(cmds.listConnections(plug, source=True, destination=False))
if driven:
    # Since 2026-08-20 the marked node IS the geometry, and parent_out
    # bakes the world motion onto its own channels - so after Connect this
    # plug is ALWAYS driven. Poke through the curve, value over value: the
    # read value keyed back over itself restores the measured frame
    # exactly.
    print("NOTE  the sword's channels are baked (normal after Connect); "
          "the drag goes through a key")
rest = cmds.getAttr(plug)
still = [world_matrix(hand) for hand in hands]
bone_still = world_matrix(bone)
try:
    if driven:
        cmds.setKeyframe(geometry, attribute="translateX", time=poke_frame,
                         value=rest + 50.0)
        cmds.currentTime(poke_frame)  # settle (trap 14)
    else:
        cmds.setAttr(plug, rest + 50.0)
    moved = [world_matrix(hand) for hand in hands]
    bone_moved = biggest_difference(world_matrix(bone), bone_still)
finally:
    if driven:
        cmds.setKeyframe(geometry, attribute="translateX", time=poke_frame,
                         value=rest)
        cmds.currentTime(poke_frame)
    else:
        cmds.setAttr(plug, rest)
    cmds.autoKeyframe(state=autokey)

travel = [biggest_difference(one, two) for one, two in zip(still, moved)]
check("dragging the sword drags both hands",
      all(distance > 1.0 for distance in travel),
      "hand travel: {0}".format(
          ", ".join("{0:.3f}".format(d) for d in travel)))
check("weapon_r rode the drag too (the constraint survived parent_out)",
      bone_moved > 1.0, "bone travel: {0:.3f}".format(bone_moved))
check("and putting it back puts them back",
      worst_drift([still], [[world_matrix(hand) for hand in hands]]) < 1e-6)

# --- pressing it twice ----------------------------------------------------
again = linking.connect(weapon, scene_map)
print("second press said:", again)
check("a second Connect hangs nothing new", "0 hand(s)" in again, again)
check("and still nothing moved",
      worst_drift(before, sample_hands(hands, frames)) < 1e-4)

# --- disconnect -----------------------------------------------------------
message = linking.disconnect(weapon, hand_bone)
print("disconnect said:", message)

back = attach.find_attached(hand_bone)
check("the weapon is back under the HAND bone", back is not None, str(back))
check("nothing reports a link any more", linking.linked_weapon() is None)

def parent_of(node):
    found = cmds.listRelatives(node, parent=True, fullPath=True) if node else None
    return found[0] if found else None


# "Back where it belongs" is not "under the root controller": a rig built by
# Switch after a full bake has no root controller to hang on and stands in
# world, all three groups together. The invariant that holds either way is
# that the end group ends up beside the two that never moved.
print("root controller present:", bool(cmds.ls("root_FK_ctrl")))
for limb in linking.ARMS:
    end_parent = parent_of(builder.ik_control(limb, "end"))
    base_parent = parent_of(builder.ik_control(limb, "base"))
    check("{0} hand control is back beside its own IK groups".format(limb),
          end_parent == base_parent,
          "end: {0}, base: {1}".format(end_parent, base_parent))

drift = worst_drift(before, sample_hands(hands, frames))
check("the hands still did not move", drift < 1e-4,
      "worst world-matrix element {0:.9f}".format(drift))

passed = sum(1 for _name, ok, _detail in RESULTS if ok)
print("\n{0}/{1} checks passed".format(passed, len(RESULTS)))
