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
from maya_weapons import attach
from maya_weapons import catalog
from maya_weapons import connect as linking
from maya_weapons import skeleton

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

hands = [scene_map[name] for name in ("hand_l", "hand_r") if name in scene_map]
check("both hand bones resolved", len(hands) == 2, str(len(hands)))

start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
frames = sorted(set([start, (start + end) // 2, end]))

# --- the weapon has to be in the hand to begin with -----------------------
carrier = attach.find_attached(bone) or linking.linked_carrier()
if carrier is None:
    carrier = attach.attach(entry, bone)
    print("NOTE  no weapon was attached; this run added one")
if linking.linked_carrier():
    linking.disconnect(linking.linked_carrier(), bone)
    print("NOTE  the arms were already connected; this run disconnected first")

carrier = attach.find_attached(bone)
check("starting with the weapon in the hand", carrier is not None, str(carrier))

before = sample_hands(hands, frames)

# --- connect --------------------------------------------------------------
message = linking.connect(carrier, scene_map)
print("connect said:", message)

carrier = linking.linked_carrier()
check("the link is found from the hand control", carrier is not None,
      str(carrier))
check("the weapon left the skeleton",
      carrier is not None
      and not cmds.listRelatives(carrier, parent=True, fullPath=True),
      "parent: {0}".format(
          cmds.listRelatives(carrier, parent=True, fullPath=True)
          if carrier else "?"))
check("the weapon carries its own animation", attach.is_animated(carrier))

built = builder.built_limbs()
check("both arms are IK",
      "arm_l" in built and "arm_r" in built, str(sorted(built)))

for limb in linking.ARMS:
    node = builder.ik_control(limb, "end")
    inside = bool(node) and builder._is_inside(
        cmds.ls(node, long=True)[0], carrier)
    check("{0} hand control rides the weapon".format(limb), inside,
          str(node))

drift = worst_drift(before, sample_hands(hands, frames))
check("the hands did not move", drift < 1e-4,
      "worst world-matrix element {0:.9f} over frames {1}".format(
          drift, frames))

# --- pressing it twice ----------------------------------------------------
again = linking.connect(carrier, scene_map)
print("second press said:", again)
check("a second Connect hangs nothing new", "0 hand(s)" in again, again)
check("and still nothing moved",
      worst_drift(before, sample_hands(hands, frames)) < 1e-4)

# --- disconnect -----------------------------------------------------------
message = linking.disconnect(carrier, bone)
print("disconnect said:", message)

back = attach.find_attached(bone)
check("the weapon is back in the hand", back is not None, str(back))
check("nothing reports a link any more", linking.linked_carrier() is None)

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
