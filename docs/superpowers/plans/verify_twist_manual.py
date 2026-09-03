"""Live proof for the manual twist controls -- 2026-09-03.

Spec: docs/superpowers/specs/2026-09-03-twist-manual-control-design.md

Runs a REAL `twist.build` end to end. It does so in **mayapy standalone on a
skeleton it builds itself**, never in the animator's scene: this feature
creates rings, attributes and nodes, and a read-only walk cannot prove any of
it -- while building for real beside the animator's rig is exactly what
verify_two_characters.py refuses to do. Standalone needs no UI: nothing here
touches OverRig, MEL, Qt or a shelf.

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' \\
        docs/superpowers/plans/verify_twist_manual.py

The skeleton is a clean X-axis chain with rotate order xyz, so every bone's
own X is its bone axis and `rotateX` is the innermost channel -- which makes
the expected distribution exact rather than approximate.
"""

import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                    "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, REPO)

import maya.standalone                                          # noqa: E402
maya.standalone.initialize(name="python")

import maya.cmds as cmds                                        # noqa: E402

# Measured: mayapy standalone does NOT auto-load these, and without them
# `quatNormalize` and `decomposeMatrix` come back as unknown node types and
# the wiring dies on a missing destination attribute. Interactive Maya loads
# them for you, which is why the module needs no guard of its own.
for _plugin in ("matrixNodes", "quatNodes"):
    if not cmds.pluginInfo(_plugin, query=True, loaded=True):
        cmds.loadPlugin(_plugin, quiet=True)

from maya_overrig import bodymap, manifest, naming, twist        # noqa: E402

failures = []
checked = 0


def gate(name, ok, detail=""):
    global checked
    checked += 1
    print("  %-4s %-56s %s" % ("ok" if ok else "FAIL", name, detail))
    if not ok:
        failures.append(name)


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def hdr(text):
    print("")
    print("=" * 80)
    print(text)
    print("=" * 80)


# ---------------------------------------------------------------------------
# the skeleton: prefixed, so nothing can ever collide with a real character
# ---------------------------------------------------------------------------
PREFIX = "zzv_"

# (leaf, parent leaf, length along X)  -- twist joints get their own entries
CHAIN = [
    ("root", None, 0.0),
    ("pelvis", "root", 10.0),
    ("spine_01", "pelvis", 10.0),
    ("spine_02", "spine_01", 10.0),
    ("spine_03", "spine_02", 10.0),
    ("spine_04", "spine_03", 10.0),
    ("spine_05", "spine_04", 10.0),
    ("neck_01", "spine_05", 8.0),
    ("head", "neck_01", 8.0),
]
for side in ("l", "r"):
    CHAIN += [
        ("clavicle_%s" % side, "spine_05", 12.0),
        ("upperarm_%s" % side, "clavicle_%s" % side, 30.0),
        ("upperarm_twist_01_%s" % side, "upperarm_%s" % side, 10.0),
        ("upperarm_twist_02_%s" % side, "upperarm_%s" % side, 20.0),
        ("lowerarm_%s" % side, "upperarm_%s" % side, 30.0),
        ("lowerarm_twist_01_%s" % side, "lowerarm_%s" % side, 8.0),
        ("lowerarm_twist_02_%s" % side, "lowerarm_%s" % side, 16.0),
        ("hand_%s" % side, "lowerarm_%s" % side, 24.0),
        ("thigh_%s" % side, "pelvis", 40.0),
        ("thigh_twist_01_%s" % side, "thigh_%s" % side, 13.333333),
        ("thigh_twist_02_%s" % side, "thigh_%s" % side, 26.666667),
        ("calf_%s" % side, "thigh_%s" % side, 40.0),
        ("calf_twist_01_%s" % side, "calf_%s" % side, 6.666667),
        ("calf_twist_02_%s" % side, "calf_%s" % side, 13.333333),
        ("foot_%s" % side, "calf_%s" % side, 20.0),
    ]

paths = {}
cmds.currentUnit(linear="cm", time="ntsc")
cmds.playbackOptions(edit=True, minTime=0, maxTime=30,
                     animationStartTime=0, animationEndTime=30)
cmds.currentTime(0)
cmds.autoKeyframe(state=False)

for leaf, parent, offset in CHAIN:
    name = PREFIX + leaf
    if parent is None:
        cmds.select(clear=True)
    else:
        cmds.select(paths[parent], replace=True)          # LONG path, trap 47
    joint = cmds.joint(name=name, position=(0, 0, 0), relative=False)
    joint = cmds.ls(joint, long=True)[0]
    cmds.setAttr(joint + ".rotateOrder", 0)               # xyz: X is innermost
    if parent is not None:
        cmds.setAttr(joint + ".translate", offset, 0.0, 0.0, type="double3")
        cmds.setAttr(joint + ".jointOrient", 0.0, 0.0, 0.0, type="double3")
    paths[leaf] = joint

ROOT = paths["root"]
print("built %d joints under %s" % (len(paths), ROOT))

# The refused segment: roll the right upper arm well past 180 degrees.
cmds.setKeyframe(paths["upperarm_r"] + ".rotateX", time=0, value=0.0)
cmds.setKeyframe(paths["upperarm_r"] + ".rotateX", time=30, value=300.0)
# and a modest, safe roll on the left, to prove auto still runs
cmds.setKeyframe(paths["upperarm_l"] + ".rotateX", time=0, value=0.0)
cmds.setKeyframe(paths["upperarm_l"] + ".rotateX", time=30, value=60.0)
cmds.currentTime(0)

# Exactly how picker_window builds it: one prefix for the whole skeleton,
# so the body map's plain UE5 names line up (trap 2).
raw = naming.hierarchy_map(ROOT)
known = [b.joint for b in bodymap.BUTTONS]
PREFIX_FOUND = naming.detect_prefix(raw, known)
scene_map = naming.strip_prefix(raw, PREFIX_FOUND)

hdr("THE SCENE MAP")
print("  detected prefix: %r" % PREFIX_FOUND)
gate("the prefix our own skeleton carries is detected",
     PREFIX_FOUND == PREFIX, "%r vs %r" % (PREFIX_FOUND, PREFIX))
gate("the prefix is detected, so canonical names resolve",
     "upperarm_l" in scene_map and "upperarm_twist_01_r" in scene_map,
     "%d entries" % len(scene_map))
gate("segments() finds all eight", len(twist.segments(scene_map)) == 8,
     "%d" % len(twist.segments(scene_map)))

# ---------------------------------------------------------------------------
hdr("THE BUILD")
rigged, message = twist.build(scene_map)
print("  %s" % message)
gate("joints were rigged", rigged > 0, "%d" % rigged)
gate("the message names the manual-only segment",
     "MANUAL ONLY" in message and "upperarm_r" in message)

table = manifest.records()

# ---------------------------------------------------------------------------
hdr("ONE RING PER SEGMENT")
rings = {}
for segment in twist.segments(scene_map):
    ring = twist.find_ring(scene_map[segment.bone], segment.limb, table=table)
    rings[segment.bone] = ring
    gate("%s has a control, found by ATTRIBUTE" % segment.bone,
         bool(ring), (ring or "").split("|")[-1])

gate("eight controls, one per segment",
     len([r for r in rings.values() if r]) == 8)
gate("no two segments share a control",
     len({r for r in rings.values() if r}) == 8)

hdr("WHERE THE RING SITS AND WHAT IT MAY DO")
for bone in ("upperarm_l", "lowerarm_r", "thigh_l"):
    ring = rings[bone]
    parent = (cmds.listRelatives(ring, parent=True, fullPath=True)
              or [None])[0]
    gate("%s control is a DAG child of its BONE" % bone,
         parent == scene_map[bone], (parent or "").split("|")[-1])
    # the midpoint, in the bone's own frame
    tip = {"upperarm_l": "lowerarm_l", "lowerarm_r": "hand_r",
           "thigh_l": "calf_l"}[bone]
    length = cmds.getAttr(scene_map[tip] + ".translateX")
    offset = cmds.getAttr(ring + ".translate")[0]
    gate("%s control sits at the bone midpoint" % bone,
         close(offset[0], length / 2.0, 1e-4)
         and close(offset[1], 0.0) and close(offset[2], 0.0),
         "%.4f vs %.4f" % (offset[0], length / 2.0))
    gate("%s control has an identity rotation" % bone,
         all(close(v, 0.0) for v in cmds.getAttr(ring + ".rotate")[0]))
    locked = [c for c in twist.LOCKED_CHANNELS
              if cmds.getAttr(ring + "." + c, lock=True)]
    gate("%s control locks every channel but rotateX" % bone,
         len(locked) == len(twist.LOCKED_CHANNELS),
         "%d of %d" % (len(locked), len(twist.LOCKED_CHANNELS)))
    gate("%s control's rotateX is free and keyable" % bone,
         not cmds.getAttr(ring + ".rotateX", lock=True)
         and cmds.getAttr(ring + ".rotateX", keyable=True))

hdr("THE AUTO DIAL EXISTS ONLY WHERE THERE IS AUTO")
for bone, wanted in (("upperarm_l", True), ("lowerarm_l", True),
                     ("thigh_r", True), ("upperarm_r", False)):
    has = cmds.attributeQuery(twist.AUTO_ATTR, node=rings[bone], exists=True)
    gate("%s: autoTwist %s" % (bone, "present" if wanted else "ABSENT"),
         has == wanted)
    if has:
        gate("%s: autoTwist defaults to 1" % bone,
             close(cmds.getAttr(rings[bone] + "." + twist.AUTO_ATTR), 1.0))

hdr("THE MANUAL TERM: ONE RING, THE MEASURED FRACTIONS")
# upperarm_l is a COUNTER segment: joints at 1/3 and 2/3 take -2/3 and -1/3
before = {leaf: cmds.getAttr(scene_map[leaf] + ".rotateX")
          for leaf in ("upperarm_twist_01_l", "upperarm_twist_02_l")}
cmds.setAttr(rings["upperarm_l"] + ".rotateX", 30.0)
after = {leaf: cmds.getAttr(scene_map[leaf] + ".rotateX")
         for leaf in ("upperarm_twist_01_l", "upperarm_twist_02_l")}
moved = {leaf: after[leaf] - before[leaf] for leaf in before}
gate("the near joint takes -2/3 of a +30 ring",
     close(moved["upperarm_twist_01_l"], -20.0, 1e-4),
     "%.6f, wanted -20" % moved["upperarm_twist_01_l"])
gate("the far joint takes -1/3 of a +30 ring",
     close(moved["upperarm_twist_02_l"], -10.0, 1e-4),
     "%.6f, wanted -10" % moved["upperarm_twist_02_l"])
gate("the two shares sum to the whole ring, signed",
     close(moved["upperarm_twist_01_l"] + moved["upperarm_twist_02_l"],
           -30.0, 1e-4))
cmds.setAttr(rings["upperarm_l"] + ".rotateX", 0.0)

# A FOLLOW segment takes the same fractions with the opposite sign. The
# expectation is COMPUTED from the geometry the run actually measured -- a
# number written in by hand fails on correct code the moment the fixture
# moves, which is how the first version of this gate failed.
LENGTH = cmds.getAttr(scene_map["hand_l"] + ".translateX")
for leaf in ("lowerarm_twist_01_l", "lowerarm_twist_02_l"):
    fraction = cmds.getAttr(scene_map[leaf] + ".translateX") / LENGTH
    wanted = 30.0 * fraction
    before = cmds.getAttr(scene_map[leaf] + ".rotateX")
    cmds.setAttr(rings["lowerarm_l"] + ".rotateX", 30.0)
    moved = cmds.getAttr(scene_map[leaf] + ".rotateX") - before
    cmds.setAttr(rings["lowerarm_l"] + ".rotateX", 0.0)
    gate("a follow joint at t=%.3f takes +t of a +30 ring" % fraction,
         close(moved, wanted, 1e-4),
         "%.6f, wanted %.6f" % (moved, wanted))

hdr("THE AUTO DIAL")
cmds.currentTime(30)                       # upperarm_l has rolled 60 degrees
auto_on = cmds.getAttr(scene_map["upperarm_twist_01_l"] + ".rotateX")
cmds.setAttr(rings["upperarm_l"] + "." + twist.AUTO_ATTR, 0.0)
auto_off = cmds.getAttr(scene_map["upperarm_twist_01_l"] + ".rotateX")
gate("auto=1 gives the counter joint its share of the 60 deg roll",
     abs(auto_on) > 1.0, "%.6f" % auto_on)
gate("auto=0 removes the automatic contribution entirely",
     close(auto_off, 0.0, 1e-4), "%.9f" % auto_off)
cmds.setAttr(rings["upperarm_l"] + ".rotateX", 15.0)
manual_only_value = cmds.getAttr(scene_map["upperarm_twist_01_l"] + ".rotateX")
gate("with auto=0 the ring still drives the joint",
     close(manual_only_value, -10.0, 1e-4),
     "%.6f, wanted -2/3 x 15" % manual_only_value)
cmds.setAttr(rings["upperarm_l"] + ".rotateX", 0.0)
cmds.setAttr(rings["upperarm_l"] + "." + twist.AUTO_ATTR, 1.0)
cmds.currentTime(0)

hdr("THE REFUSED SEGMENT IS MANUAL ONLY, NOT SKIPPED")
# From the REAL path, so the names carry the skeleton's prefix. The first
# version asked for the unprefixed names, which do not exist either way --
# a gate that cannot fail.
names = twist.node_names(scene_map["upperarm_twist_01_r"])
left = twist.node_names(scene_map["upperarm_twist_01_l"])
gate("CONTROL: the LEFT arm's automatic chain DOES exist",
     all(cmds.objExists(left[role])
         for role in ("delta", "quat", "dot", "norm", "angle", "weight")),
     ", ".join(role for role in ("delta", "quat", "dot", "norm", "angle",
                                 "weight") if not cmds.objExists(left[role]))
     or "all six present")
gate("CONTROL: the LEFT arm has an auto gate", cmds.objExists(left["gate"]))
gate("no automatic chain was created",
     not any(cmds.objExists(names[role])
             for role in ("delta", "quat", "dot", "norm", "angle", "weight")),
     ", ".join(role for role in ("delta", "quat", "dot", "norm", "angle",
                                 "weight") if cmds.objExists(names[role]))
     or "none of the six")
gate("no auto gate was created", not cmds.objExists(names["gate"]))
gate("the manual term WAS created", cmds.objExists(names["manual"]))
gate("the channel is driven", bool(cmds.listConnections(
    scene_map["upperarm_twist_01_r"] + ".rotateX", source=True,
    destination=False)))
before = cmds.getAttr(scene_map["upperarm_twist_01_r"] + ".rotateX")
cmds.setAttr(rings["upperarm_r"] + ".rotateX", 30.0)
after = cmds.getAttr(scene_map["upperarm_twist_01_r"] + ".rotateX")
gate("its ring drives it by the same measured fraction",
     close(after - before, -20.0, 1e-4), "%.6f, wanted -20" % (after - before))
cmds.setAttr(rings["upperarm_r"] + ".rotateX", 0.0)
# The driver rolls 0 -> 300 over the range. With no automatic term the
# joint must not move with it at all; the left arm, which HAS one, must.
still = [cmds.getAttr(scene_map["upperarm_twist_01_r"] + ".rotateX",
                      time=frame) for frame in range(0, 31, 5)]
moving = [cmds.getAttr(scene_map["upperarm_twist_01_l"] + ".rotateX",
                       time=frame) for frame in range(0, 31, 5)]
gate("the refused joint does not follow its driver's 300 deg roll",
     max(still) - min(still) < 1e-6,
     "range %.9f over 7 frames" % (max(still) - min(still)))
gate("CONTROL: the left joint DOES follow its driver's 60 deg roll",
     max(moving) - min(moving) > 1.0,
     "range %.6f" % (max(moving) - min(moving)))

hdr("THE RINGS ARE MANIFEST MEMBERS")
for segment in twist.segments(scene_map):
    members = manifest.members(manifest.KIND_TWIST, segment.limb, table=table)
    gate("%s control is recorded in %s" % (segment.bone, segment.limb),
         rings[segment.bone] in members
         or any(m.endswith(rings[segment.bone].split("|")[-1])
                for m in members))

hdr("THE BAKE FLATTENS THE SUM AND TAKES THE RINGS DOWN")
cmds.setAttr(rings["upperarm_l"] + ".rotateX", 12.0)
sampled = [cmds.getAttr(scene_map["upperarm_twist_01_l"] + ".rotateX",
                        time=frame) for frame in range(0, 31, 5)]
baked, bake_message = twist.bake()
print("  %s" % bake_message)
gate("the bake reports joints", baked > 0, "%d" % baked)
after_bake = [cmds.getAttr(scene_map["upperarm_twist_01_l"] + ".rotateX",
                           time=frame) for frame in range(0, 31, 5)]
worst = max(abs(a - b) for a, b in zip(sampled, after_bake))
gate("every sampled frame survives the bake", worst < 1e-4,
     "worst %.9f deg over 7 frames" % worst)
gate("the manual ring's 12 deg is IN the baked values",
     any(abs(v) > 1.0 for v in after_bake),
     "%s" % ", ".join("%.2f" % v for v in after_bake[:4]))
gate("every control is gone", not any(
    cmds.objExists(r) for r in rings.values() if r),
    "%d left" % sum(1 for r in rings.values() if r and cmds.objExists(r)))
gate("no twist network node survives",
     not cmds.ls("*_tw_*") or all("_twist_" in n for n in cmds.ls("*_tw_*")),
     str(cmds.ls("*_tw_delta") or "none"))
gate("the channel is free again after the bake",
     not cmds.listConnections(
         scene_map["upperarm_twist_01_l"] + ".rotateX",
         source=True, destination=False, type="multDoubleLinear"))

hdr("RESULT")
print("  %d of %d gates failed" % (len(failures), checked))
for name in failures:
    print("    FAILED: %s" % name)

try:
    maya.standalone.uninitialize()
except Exception:
    pass
sys.exit(1 if failures else 0)
