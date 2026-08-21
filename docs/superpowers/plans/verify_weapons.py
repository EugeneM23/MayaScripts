"""Live proof for maya_scenesetup, run through the command port.

Bind explicitly rather than trusting whatever the panel last did: the user
works in the scene between runs. The script leaves the scene as it found it --
if no weapon was attached when it started, none is attached when it ends.

Since 2026-08-21 the drive is inverted: the sword parents under the HAND and
`weapon_r` is parent-constrained to it (mo=False). The gates here prove the
whole story: placement, the transfer of the bone's animation onto the sword,
the bone following the sword 1:1, the replace round-trip keeping the motion,
and detach putting it all back.

Never cmds.undo() from a bridge script: the whole script is one command, and
undo reverts a chunk of prior work instead.
"""

import maya.cmds as cmds
import maya.mel as mel

from maya_overrig import aimrig

from maya_scenesetup import attach
from maya_scenesetup import bonedrive
from maya_scenesetup import catalog
from maya_scenesetup import connect as linking
from maya_scenesetup import skeleton
from maya_scenesetup import window

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


def marked_under(node):
    return [child for child
            in cmds.listRelatives(node, children=True, type="transform",
                                  fullPath=True) or []
            if cmds.attributeQuery(attach.MARKER, node=child, exists=True)]


entry = catalog.by_key("LongSword_02")

# --- the file and the character ------------------------------------------
check("model file is on disk", catalog.missing(entry) == "", entry.path)

root = skeleton.current_root()
check("a character was resolved", root is not None, str(root))

bone = skeleton.resolve_bone(root, entry.bone)
check("weapon_r resolved inside that character", bone is not None, str(bone))
check("the bone belongs to the bound character",
      bool(bone) and bone.startswith(root.rsplit("|", 1)[0]), str(bone))

hand = attach.parent_bone(bone)
check("the drive bone has a parent to hang the weapon on", hand is not None,
      str(hand))

was_attached = bool(attach.find_attached(hand)
                    or attach.find_attached(bone))

# Every attach below REPLACES what is in the hand, and replacing deletes the
# marked node whole. Once the arms ride the weapon the IK hand controls are its
# DAG children and an aim's locators drive its geometry -- so a run in that
# scene state would take the animator's rig down unbaked. The window refuses
# the same two cases on the same grounds; a proof script has no business being
# braver than the button it proves.
_standing = attach.find_attached(hand) or attach.find_attached(bone)
_refusal = ""
if linking.linked_weapon():
    _refusal = "the arms are connected to a weapon - press Disconnect first"
elif _standing and aimrig.aim_for(attach.model_root(_standing)):
    _refusal = "the weapon has an aim - Bake+Delete it in the picker first"
if _refusal:
    print("ABORT  " + _refusal)
    print("\n0/{0} checks passed (nothing was touched)".format(len(RESULTS)))
    raise RuntimeError(_refusal)

# --- animation on the drive bone -------------------------------------------
# The transfer is the point of the redesign, so the bone must carry motion.
# A clean bone gets two synthetic keys, keyed OFF THE VALUES IT HOLDS (trap
# 30: a literal on this skeleton bends it) and cut again at the end; a bone
# that already moves is used as it is, with a note -- attach will transfer
# and detach will bake back, which keeps the motion but re-times the keys.
start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
restore_time = cmds.currentTime(query=True)
mid = (start + end) // 2

synthetic_keys = False
bone_was_animated = bonedrive.moves(bone)
if bone_was_animated:
    print("NOTE  weapon_r already carries animation; attach will move it "
          "onto the sword and any detach bakes it back - same motion, "
          "denser keys")
else:
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        held_rz = cmds.getAttr(bone + ".rotateZ")
        held_tx = cmds.getAttr(bone + ".translateX")
        if (not cmds.listConnections(bone + ".rotateZ", source=True,
                                     destination=False)
                and not cmds.listConnections(bone + ".translateX",
                                             source=True, destination=False)):
            cmds.setKeyframe(bone, attribute="rotateZ", time=start,
                             value=held_rz)
            cmds.setKeyframe(bone, attribute="rotateZ", time=end,
                             value=held_rz + 40.0)
            cmds.setKeyframe(bone, attribute="translateX", time=start,
                             value=held_tx)
            cmds.setKeyframe(bone, attribute="translateX", time=end,
                             value=held_tx + 6.0)
            synthetic_keys = True
    finally:
        cmds.autoKeyframe(state=autokey)
check("the drive bone moves, so the transfer is provable",
      bonedrive.moves(bone), "synthetic" if synthetic_keys else "the scene's")

# The truth the whole attach must preserve: where the bone is over time.
bone_track = {}
for frame in (start, mid, end):
    cmds.currentTime(frame)
    bone_track[frame] = world_matrix(bone)
cmds.currentTime(restore_time)

# --- attach ---------------------------------------------------------------
# The FBX import mode is one global setting for the session. Put it where the
# UE bridge leaves it -- `exmerge`, which matches names and creates nothing --
# so this proves the case that actually broke rather than a clean-room one.
if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
    cmds.loadPlugin("fbxmaya", quiet=True)
mel.eval("FBXImportMode -v exmerge")

assemblies_before = set(cmds.ls(assemblies=True) or [])
weapon, note = attach.attach(entry, hand, bone)
print("attach note: " + (note or "(none)"))
check("imports even with the plugin left in exmerge",
      bool(cmds.listRelatives(weapon, allDescendents=True, type="mesh")))
check("and puts the session's import mode back",
      mel.eval("FBXImportMode -q") == "exmerge",
      repr(mel.eval("FBXImportMode -q")))
check("the weapon is a child of the HAND, not the weapon bone",
      weapon.startswith(hand + "|") and not weapon.startswith(bone + "|"),
      weapon)
check("weapon is marked",
      cmds.attributeQuery(attach.MARKER, node=weapon, exists=True))
check("marker holds the catalog key",
      cmds.getAttr(weapon + "." + attach.MARKER) == entry.key)

# --- no group of ours (2026-08-20) ---------------------------------------
check("the marked node holds a mesh itself, so one click selects it",
      bool(cmds.listRelatives(weapon, children=True, type="mesh")),
      "shapes: {0}".format(cmds.listRelatives(weapon, children=True,
                                              shapes=True)))
check("model_root answers the marked node itself",
      attach.model_root(weapon) == weapon, attach.model_root(weapon))
check("exactly one node of ours under the hand",
      len(marked_under(hand)) == 1,
      "{0} marked children".format(len(marked_under(hand))))
leftovers = sorted(set(cmds.ls(assemblies=True) or []) - assemblies_before)
check("nothing from the import was left at world level", not leftovers,
      ", ".join(leftovers[:4]))

# --- the inverted drive -----------------------------------------------------
check("weapon_r is driven by the marked node",
      bonedrive.driving_weapon(bone) == weapon,
      str(bonedrive.driving_weapon(bone)))

# The transfer: the sword now plays what the bone played, and the bone -
# riding the sword - still stands where it stood, frame by frame.
worst_bone = 0.0
worst_pair = 0.0
for frame in (start, mid, end):
    cmds.currentTime(frame)
    worst_bone = max(worst_bone,
                     biggest_difference(world_matrix(bone),
                                        bone_track[frame]))
    worst_pair = max(worst_pair,
                     biggest_difference(world_matrix(bone),
                                        world_matrix(weapon)))
cmds.currentTime(restore_time)
check("the bone's world motion survived the transfer", worst_bone < 1e-3,
      "worst {0:.7f} over 3 frames".format(worst_bone))
check("the bone lives in the sword's frame (mo=False)", worst_pair < 1e-3,
      "worst {0:.7f}".format(worst_pair))
check("the sword's channels carry the animation now",
      attach.is_animated(weapon))

# --- the bone follows a dragged sword --------------------------------------
# The grip fields are quiet while the sword is animated, so the drag is a
# direct channel write with autoKey off, put back afterwards (trap 14).
autokey = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
cmds.currentTime(mid)
before_bone = world_matrix(bone)
plug = weapon + ".translateY"
driven = cmds.listConnections(plug, source=True, destination=False)
if driven:
    # Baked curves own the channel: prove the follow through a keyed poke
    # on the sword's own curve instead, value over value (flat-safe).
    held = cmds.getAttr(plug)
    cmds.setKeyframe(weapon, attribute="translateY", time=mid,
                     value=held + 10.0)
    cmds.currentTime(start)
    cmds.currentTime(mid)
    moved = biggest_difference(world_matrix(bone), before_bone)
    cmds.setKeyframe(weapon, attribute="translateY", time=mid, value=held)
else:
    held = cmds.getAttr(plug)
    cmds.setAttr(plug, held + 10.0)
    moved = biggest_difference(world_matrix(bone), before_bone)
    cmds.setAttr(plug, held)
cmds.currentTime(start)
cmds.currentTime(mid)
restored = biggest_difference(world_matrix(bone), before_bone)
cmds.autoKeyframe(state=autokey)
cmds.currentTime(restore_time)
check("dragging the sword drags weapon_r with it", moved > 9.0,
      "moved {0:.3f}".format(moved))
check("and the drag was put back", restored < 1e-4,
      "worst {0:.7f}".format(restored))

# --- replace keeps the animation -------------------------------------------
weapon, note = attach.attach(entry, hand, bone)
print("replace note: " + (note or "(none)"))
check("a second Add leaves exactly one weapon",
      len(marked_under(hand)) == 1 and not marked_under(bone),
      "{0} under the hand".format(len(marked_under(hand))))
worst_replace = 0.0
for frame in (start, mid, end):
    cmds.currentTime(frame)
    worst_replace = max(worst_replace,
                        biggest_difference(world_matrix(bone),
                                           bone_track[frame]))
cmds.currentTime(restore_time)
check("the bone's motion survived the replace round-trip",
      worst_replace < 1e-3, "worst {0:.7f}".format(worst_replace))

# --- a path pasted into the FBX field (2026-08-20) ------------------------
custom = window.chosen_entry(entry.path, entry)
check("a pasted path becomes an entry of its own",
      custom.path == entry.path and custom.scale == 1.0,
      "{0} scale {1}".format(custom.key, custom.scale))
check("its key is a legal Maya name",
      custom.key == catalog.node_key(custom.key), custom.key)

custom_weapon, _custom_note = attach.attach(custom, hand, bone)
check("the pasted path attaches under the hand",
      custom_weapon.startswith(hand + "|"), custom_weapon)
check("and the marker holds the derived key",
      cmds.getAttr(custom_weapon + "." + attach.MARKER) == custom.key,
      cmds.getAttr(custom_weapon + "." + attach.MARKER))
check("an empty field falls back to the dropdown",
      window.chosen_entry("", entry) is entry)

# --- detach gives the bone its animation back -------------------------------
removed = attach.detach(hand, bone)
check("detach removed the weapon", removed is not None
      and attach.find_attached(hand) is None
      and attach.find_attached(bone) is None, str(removed))
check("and the constraint went with it",
      bonedrive.driving_weapon(bone) is None
      and not cmds.listRelatives(bone, children=True, type="constraint"))
worst_back = 0.0
for frame in (start, mid, end):
    cmds.currentTime(frame)
    worst_back = max(worst_back,
                     biggest_difference(world_matrix(bone),
                                        bone_track[frame]))
cmds.currentTime(restore_time)
check("the bone plays its animation again, off the sword", worst_back < 1e-3,
      "worst {0:.7f} over 3 frames".format(worst_back))

# --- leave the scene as we found it ---------------------------------------
if synthetic_keys:
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        cmds.cutKey(bone, attribute=("rotateZ", "translateX",
                                     "rotateX", "rotateY",
                                     "translateY", "translateZ"), clear=True)
        cmds.setAttr(bone + ".rotateZ", held_rz)
        cmds.setAttr(bone + ".translateX", held_tx)
    finally:
        cmds.autoKeyframe(state=autokey)
    check("synthetic keys removed, the bone back at rest",
          not bonedrive.moves(bone))

if was_attached:
    print("NOTE  the scene had a weapon attached before this run; it was "
          "replaced and then removed - press Add to put it back")

passed = sum(1 for _name, ok, _detail in RESULTS if ok)
print("\n{0}/{1} checks passed".format(passed, len(RESULTS)))
