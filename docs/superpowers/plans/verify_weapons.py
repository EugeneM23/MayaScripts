"""Live proof for maya_scenesetup, run through the command port.

Bind explicitly rather than trusting whatever the panel last did: the user
works in the scene between runs. The script leaves the scene as it found it --
if no weapon was attached when it started, none is attached when it ends.

Never cmds.undo() from a bridge script: the whole script is one command, and
undo reverts a chunk of prior work instead.
"""

import maya.cmds as cmds
import maya.mel as mel

from maya_scenesetup import attach
from maya_scenesetup import catalog
from maya_scenesetup import skeleton

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              "  " + detail if detail else ""))


def world_matrix(node):
    return cmds.xform(node, query=True, matrix=True, worldSpace=True)


def local_matrix(node):
    return cmds.xform(node, query=True, matrix=True, objectSpace=True)


def biggest_difference(left, right):
    return max(abs(a - b) for a, b in zip(left, right))


entry = catalog.by_key("LongSword_02")

# --- the file and the character ------------------------------------------
check("model file is on disk", catalog.missing(entry) == "", entry.path)

root = skeleton.current_root()
check("a character was resolved", root is not None, str(root))

bone = skeleton.resolve_bone(root, entry.bone)
check("weapon_r resolved inside that character", bone is not None, str(bone))
check("the bone belongs to the bound character",
      bool(bone) and bone.startswith(root.rsplit("|", 1)[0]), str(bone))

was_attached = attach.find_attached(bone) is not None

# --- attach with no offsets ----------------------------------------------
# The FBX import mode is one global setting for the session. Put it where the
# UE bridge leaves it -- `exmerge`, which matches names and creates nothing --
# so this proves the case that actually broke rather than a clean-room one.
if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
    cmds.loadPlugin("fbxmaya", quiet=True)
mel.eval("FBXImportMode -v exmerge")

weapon, _note = attach.attach(entry, bone)
check("imports even with the plugin left in exmerge",
      bool(cmds.listRelatives(weapon, allDescendents=True, type="mesh")))
check("and puts the session's import mode back",
      mel.eval("FBXImportMode -q") == "exmerge",
      repr(mel.eval("FBXImportMode -q")))
check("weapon is a child of the bone",
      weapon.startswith(bone + "|"), weapon)
check("weapon is marked",
      cmds.attributeQuery(attach.MARKER, node=weapon, exists=True))
check("marker holds the catalog key",
      cmds.getAttr(weapon + "." + attach.MARKER) == entry.key)
check("the model came in with it",
      bool(cmds.listRelatives(weapon, allDescendents=True, type="mesh")))

gap = biggest_difference(world_matrix(weapon), world_matrix(bone))
check("with zero offsets it sits exactly on the bone", gap < 1e-4,
      "worst matrix element {0:.7f}".format(gap))

# --- offsets --------------------------------------------------------------
attach.write_offsets(weapon, (0.0, 90.0, 0.0), (5.0, 0.0, 0.0))
rotate, translate = attach.read_offsets(weapon)
check("offsets read back as written",
      max(abs(rotate[1] - 90.0), abs(translate[0] - 5.0)) < 1e-4,
      "{0} {1}".format(rotate, translate))

moved = biggest_difference(world_matrix(weapon), world_matrix(bone))
check("a non-zero offset actually moves it", moved > 1.0,
      "worst matrix element {0:.4f}".format(moved))

# --- one weapon per bone --------------------------------------------------
attach.attach(entry, bone)
marked = [child for child
          in cmds.listRelatives(bone, children=True, type="transform",
                                fullPath=True) or []
          if cmds.attributeQuery(attach.MARKER, node=child, exists=True)]
check("a second Add leaves exactly one weapon", len(marked) == 1,
      "{0} marked children".format(len(marked)))

weapon = marked[0]
attach.write_offsets(weapon, (0.0, 30.0, 0.0), (2.0, 1.0, 0.0))

# --- it rides the arm -----------------------------------------------------
start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
restore = cmds.currentTime(query=True)

frames = sorted(set([start, (start + end) // 2, end]))
locals_over_time = []
bone_over_time = []
for frame in frames:
    cmds.currentTime(frame)
    locals_over_time.append(local_matrix(weapon))
    bone_over_time.append(world_matrix(bone))
cmds.currentTime(restore)

drift = max(biggest_difference(locals_over_time[0], sample)
            for sample in locals_over_time)
check("the weapon holds its offset over the range", drift < 1e-6,
      "worst {0:.9f} over frames {1}".format(drift, frames))

travel = max(biggest_difference(bone_over_time[0], sample)
             for sample in bone_over_time)
if travel < 1e-4:
    print("NOTE  the arm does not move over {0}-{1}, so the frames above "
          "prove nothing about the carry; the poke below does".format(
              start, end))


def free_channel(plug):
    """A channel we may write and put back: not driven, not locked."""
    if cmds.listConnections(plug, source=True, destination=False):
        return False
    return not cmds.getAttr(plug, lock=True)


def pokeable(joint):
    """A rotate channel that would move `joint` and is ours to write.

    The bone itself once the character is bare; once a rig is built its
    rotates are driven by a pairBlend, so the FK controller is asked next.
    Baked curves count as driven -- rewriting the animator's curves to prove
    a point is not on the table.
    """
    candidates = [joint]
    controller = cmds.ls(joint.split("|")[-1] + "_FK_ctrl", long=True) or []
    candidates.extend(controller)
    for node in candidates:
        for axis in "ZXY":
            plug = "{0}.rotate{1}".format(node, axis)
            if free_channel(plug):
                return plug
    return None


# Turning the arm is the only direct proof that the weapon rides it. The
# channel is read first and written back afterwards -- never a literal rest
# value -- and autoKey is off, or the poke would key the animator's rig.
elbow = cmds.listRelatives(bone, parent=True, fullPath=True)[0]
elbow = cmds.listRelatives(elbow, parent=True, fullPath=True)[0]
plug = pokeable(elbow)

if plug is None:
    print("NOTE  nothing on {0} is free to turn -- a rig drives it and its "
          "curves are the animator's. The carry is unmeasured in this scene "
          "state; what stands is that the weapon is a DAG child of the bone "
          "with a constant local matrix, checked above.".format(
              elbow.split("|")[-1]))
else:
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    rest = cmds.getAttr(plug)
    before_bone = world_matrix(bone)
    before_weapon = world_matrix(weapon)
    before_local = local_matrix(weapon)
    try:
        cmds.setAttr(plug, rest + 25.0)
        after_bone = world_matrix(bone)
        after_weapon = world_matrix(weapon)
        after_local = local_matrix(weapon)
    finally:
        cmds.setAttr(plug, rest)
        cmds.autoKeyframe(state=autokey)

    bone_moved = biggest_difference(before_bone, after_bone)
    weapon_moved = biggest_difference(before_weapon, after_weapon)
    check("turning {0} moves the weapon with it".format(
        plug.split("|")[-1]),
        bone_moved > 1e-3 and weapon_moved > 1e-3,
        "bone {0:.3f}, weapon {1:.3f}".format(bone_moved, weapon_moved))

    slip = biggest_difference(before_local, after_local)
    check("and the grip does not slip", slip < 1e-9,
          "worst {0:.12f}".format(slip))

    restored = biggest_difference(before_bone, world_matrix(bone))
    check("the arm was put back exactly", restored < 1e-9,
          "worst {0:.12f}".format(restored))

# --- leave the scene as we found it ---------------------------------------
if not was_attached:
    attach.remove_attached(bone)
    check("cleaned up after itself", attach.find_attached(bone) is None)

passed = sum(1 for _name, ok, _detail in RESULTS if ok)
print("\n{0}/{1} checks passed".format(passed, len(RESULTS)))
