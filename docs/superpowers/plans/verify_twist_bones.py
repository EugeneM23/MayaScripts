"""Live proof that the twist joints distribute their segment's roll.

Sent through the command port against the scene holding the skeleton. Two
phases, and the split is deliberate:

  phase A -- a SANDBOX chain this script builds and deletes: three joints on
             +X with twist children at known fractions. Poking a sandbox is
             free, so this is where the exact numbers are measured (22.5 of a
             90 roll, zero cross-talk from a 60 bend) and where the analytic
             claims live. It needs no OverRig and no rig on the character, so
             it proves the mathematics on its own.
  phase B -- the REAL skeleton: which joints got rigged and on which channel,
             the network's output against the same twist recomputed from
             world matrices in plain Python, idempotence, the bake, and the
             claim that Switch FK/IK never has to touch any of it.

Gates:

 1. a pure roll of the driver lands on every twist joint at its measured
    fraction;
 2. a pure BEND of the driver puts NOTHING on the twist joints -- the gate
    that separates this design from a two-target orientConstraint, which
    reads bend as twist;
 3. a counter joint's net world roll is `t` x its parent's, which is the
    anatomical claim, not just its channel value;
 4. a roll past 90 stays continuous (no quaternion flip at 170 degrees);
 5. an unanimated channel bakes to a plain value, not to a key per frame;
 6. the bake leaves the joint reading what the network read, and no node of
    ours behind;
 7. on the real skeleton, the network's value equals `rest + weight * theta`
    with theta recomputed independently -- the check that would fail if
    quatToEuler did not need its quaternion normalised;
 8. a second build does not double the network;
 9. the driver bones do not move over the whole timeline (world MATRICES,
    never euler channels -- trap 31);
10. after Switch FK/IK there and back, the networks and their values are
    untouched.

Never `cmds.undo()`: the whole bridge script is one command, so an undo here
reverts a prior chunk. Poked values are read first and written back, and a
channel carrying real animation is sampled instead of poked.
"""

import math
import sys
from contextlib import contextmanager

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO not in sys.path:
    sys.path.append(REPO)
for _name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[_name]

import maya.cmds as cmds
import maya.api.OpenMaya as om

from maya_overrig import bodymap, builder, fkcontrols, naming, overrig, twist

failures = []


def check(label, condition, detail=""):
    print("%-58s %s %s" % (label, "PASS" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def wiggle():
    """Settle the DG. Reads after a bare setAttr mix stale and fresh values
    across nodes until time moves (trap 14)."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, edit=True)
    cmds.currentTime(now, edit=True)


@contextmanager
def poked(deltas):
    """Add to plugs, yield, put back exactly what was there."""
    was = [(plug, cmds.getAttr(plug)) for plug, _delta in deltas]
    try:
        for plug, delta in deltas:
            cmds.setAttr(plug, cmds.getAttr(plug) + delta)
        wiggle()
        yield
    finally:
        for plug, value in was:
            cmds.setAttr(plug, value)
        wiggle()


def moving_curve(node):
    """True when the node carries an animCurve whose VALUES change.

    "The bone has animCurves" is not "the animator has animation" (trap 30).
    """
    for curve in cmds.listConnections(node, type="animCurve") or []:
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        if values and (max(values) - min(values)) > 1e-4:
            return True
    return False


def world(node):
    return om.MMatrix(cmds.xform(node, query=True, worldSpace=True,
                                 matrix=True))


def worst(a, b):
    return max(abs(a[i] - b[i]) for i in range(16))


def roll_about(matrix, axis):
    """The twist of a rotation matrix about a unit axis, in degrees."""
    quat = om.MTransformationMatrix(matrix).rotation(asQuaternion=True)
    vector = om.MVector(quat.x, quat.y, quat.z)
    return math.degrees(2.0 * math.atan2(vector * axis, quat.w))


# ---------------------------------------------------------------------------
# what the rig says about itself: every twist network, read as data
# ---------------------------------------------------------------------------

def source_of(plug):
    """The node feeding a plug, or None."""
    found = cmds.listConnections(plug, source=True, destination=False) or []
    return found[0] if found else None


def upstream(plug):
    """The node feeding `plug`, stepping over any unitConversion.

    Maya splices one in wherever a unitless double meets an angle, so this
    walk hits two of them: in front of the joint's rotate channel, and in
    front of the weight multiplier. They are part of the rig and are returned
    so the teardown gate can insist they are gone too.
    """
    conversions = []
    node = source_of(plug)
    while node and cmds.objectType(node) == "unitConversion":
        conversions.append(node)
        node = source_of(node + ".input")
    return node, conversions


def networks():
    """[{joint, plug, driver, weight, rest, axis, m0inv, nodes}] for the rig.

    Started from the manifest's recorded plugs and walked back along
    CONNECTIONS -- never assembled from node names, because Maya uniquifies a
    colliding name and a by-name lookup would then read a neighbour's node and
    prove nothing.
    """
    found = []
    for limb in twist.built_limbs():
        for plug in twist.driven_plugs(limb):
            if not cmds.objExists(plug):
                continue
            total, spliced = upstream(plug)
            if not total:
                continue
            scaled, more = upstream(total + ".input1")
            spliced.extend(more)
            angle, more = upstream(scaled + ".input1")
            spliced.extend(more)
            norm = source_of(angle + ".inputQuatX")
            dot = source_of(norm + ".inputQuatX")
            quat = source_of(dot + ".input1X")
            delta = source_of(quat + ".inputMatrix")
            driver = source_of(delta + ".matrixIn[1]")
            found.append({
                "limb": limb,
                "joint": plug.split(".")[0],
                "plug": plug,
                "driver": driver,
                "weight": cmds.getAttr(scaled + ".input2"),
                "rest": cmds.getAttr(total + ".input2"),
                "axis": om.MVector(cmds.getAttr(dot + ".input2")[0]),
                "m0inv": om.MMatrix(cmds.getAttr(delta + ".matrixIn[0]")),
                "nodes": [delta, quat, dot, norm, angle, scaled,
                          total] + spliced,
            })
    return found


def expected_value(net):
    """`rest + weight * theta`, with theta recomputed from scratch."""
    now = om.MMatrix(cmds.getAttr(net["driver"] + ".matrix"))
    return net["rest"] + net["weight"] * roll_about(net["m0inv"] * now,
                                                    net["axis"])


# ---------------------------------------------------------------------------
# the bound skeleton, resolved the way the panel does
# ---------------------------------------------------------------------------

root = None
try:
    from maya_overrig import picker_window
    root = picker_window.bound_root()
except Exception as _exc:                                    # no picker open
    print("picker not available: %s" % _exc)
if not root:
    roots = builder.character_roots()
    root = roots[0] if len(roots) == 1 else None
if not root:
    raise SystemExit("cannot bind: %s" % builder.character_roots())

mapping = naming.hierarchy_map(root)
prefix = naming.detect_prefix(list(mapping), {b.joint for b in bodymap.BUTTONS})
SCENE = naming.strip_prefix(mapping, prefix)
frame = cmds.currentTime(query=True)
start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
print("root %s, %d joints, prefix %r, timeline %d..%d, frame %s"
      % (root, len(SCENE), prefix, start, end, frame))

auto_key = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
selection = cmds.ls(selection=True, long=True)

# Start from a clean slate, whatever the last run left.
if twist.has_twist():
    print("standing twist rig baked: %s" % (twist.bake_all(),))

# ---------------------------------------------------------------------------
# phase A -- the sandbox
# ---------------------------------------------------------------------------
print()
print("=== phase A: sandbox chain ===")

SBX = []
try:
    cmds.select(clear=True)
    up = cmds.createNode("joint", name="tw_sbx_upperarm_l", skipSelect=True)
    low = cmds.createNode("joint", name="tw_sbx_lowerarm_l", parent=up,
                          skipSelect=True)
    hand = cmds.createNode("joint", name="tw_sbx_hand_l", parent=low,
                           skipSelect=True)
    ut1 = cmds.createNode("joint", name="tw_sbx_upperarm_twist_01_l",
                          parent=up, skipSelect=True)
    lt1 = cmds.createNode("joint", name="tw_sbx_lowerarm_twist_01_l",
                          parent=low, skipSelect=True)
    lt2 = cmds.createNode("joint", name="tw_sbx_lowerarm_twist_02_l",
                          parent=low, skipSelect=True)
    cmds.setAttr(low + ".tx", 20.0)
    cmds.setAttr(hand + ".tx", 20.0)
    cmds.setAttr(ut1 + ".tx", 5.0)     # t = 0.25 -> counter weight -0.75
    cmds.setAttr(lt1 + ".tx", 5.0)     # t = 0.25 -> follow weight +0.25
    cmds.setAttr(lt2 + ".tx", 15.0)    # t = 0.75 -> follow weight +0.75
    SBX = [cmds.ls(n, long=True)[0] for n in (up,)]

    box = {"upperarm_l": cmds.ls(up, long=True)[0],
           "lowerarm_l": cmds.ls(low, long=True)[0],
           "hand_l": cmds.ls(hand, long=True)[0]}
    rigged, message = twist.build(box, ["arm_l"])
    print("sandbox build: %d rigged -- %s" % (rigged, message))
    check("A0 three sandbox joints rigged", rigged == 3)

    by_joint = {n["joint"].split("|")[-1]: n for n in networks()}
    check("A0b every sandbox joint has a network", len(by_joint) == 3,
          sorted(by_joint))
    for leaf, want in (("tw_sbx_upperarm_twist_01_l", -0.75),
                       ("tw_sbx_lowerarm_twist_01_l", 0.25),
                       ("tw_sbx_lowerarm_twist_02_l", 0.75)):
        got = by_joint[leaf]["weight"] if leaf in by_joint else None
        check("A0c %s weight %+0.2f" % (leaf, want),
              got is not None and abs(got - want) < 1e-9, "got %s" % got)

    rest = {leaf: cmds.getAttr(net["plug"]) for leaf, net in by_joint.items()}

    # gate 1 -- a pure roll, split by the measured fractions
    with poked([(hand + ".rx", 90.0)]):
        for leaf, want in (("tw_sbx_lowerarm_twist_01_l", 22.5),
                           ("tw_sbx_lowerarm_twist_02_l", 67.5)):
            got = cmds.getAttr(by_joint[leaf]["plug"]) - rest[leaf]
            check("1 %s takes %.1f of a 90 roll" % (leaf, want),
                  abs(got - want) < 1e-4, "got %.6f" % got)

    # gate 2 -- a pure bend leaves the twist alone
    with poked([(hand + ".rz", 60.0), (low + ".rz", -35.0)]):
        for leaf in ("tw_sbx_lowerarm_twist_01_l",
                     "tw_sbx_lowerarm_twist_02_l"):
            got = cmds.getAttr(by_joint[leaf]["plug"]) - rest[leaf]
            check("2 %s ignores a 60 bend" % leaf, abs(got) < 1e-4,
                  "got %.9f" % got)
    with poked([(up + ".rz", 60.0)]):
        leaf = "tw_sbx_upperarm_twist_01_l"
        got = cmds.getAttr(by_joint[leaf]["plug"]) - rest[leaf]
        check("2b %s ignores a 60 bend" % leaf, abs(got) < 1e-4,
              "got %.9f" % got)

    # gate 3 -- the counter joint's NET world roll is t x the parent's
    leaf = "tw_sbx_upperarm_twist_01_l"
    joint = by_joint[leaf]["joint"]
    axis = om.MVector(1.0, 0.0, 0.0)
    before = world(joint)
    with poked([(up + ".rx", 90.0)]):
        channel = cmds.getAttr(by_joint[leaf]["plug"]) - rest[leaf]
        net_roll = roll_about(before.inverse() * world(joint), axis)
        check("3 counter channel gives back 67.5 of 90",
              abs(channel + 67.5) < 1e-4, "got %.6f" % channel)
        check("3b counter joint nets 22.5 of a 90 parent roll",
              abs(net_roll - 22.5) < 1e-3, "got %.6f" % net_roll)

    # gate 4 -- continuity past 90
    with poked([(hand + ".rx", 170.0)]):
        leaf = "tw_sbx_lowerarm_twist_02_l"
        got = cmds.getAttr(by_joint[leaf]["plug"]) - rest[leaf]
        check("4 a 170 roll stays continuous", abs(got - 127.5) < 1e-4,
              "got %.6f" % got)

    # gates 5 and 6 -- the bake
    live = {net["plug"]: cmds.getAttr(net["plug"])
            for net in by_joint.values()}
    nodes = [n for net in by_joint.values() for n in net["nodes"]]
    baked, message = twist.bake(["arm_l"])
    print("sandbox bake: %s" % message)
    check("6 every joint baked", baked == 3, "baked %d" % baked)
    check("6b no node of ours survives",
          not any(cmds.objExists(n) for n in nodes),
          [n for n in nodes if cmds.objExists(n)])
    check("6c the manifest is gone",
          not cmds.objExists(twist.twist_set("arm_l")))
    for plug, value in live.items():
        got = cmds.getAttr(plug)
        check("6d %s kept its value" % plug.split("|")[-1],
              abs(got - value) < 1e-4, "%.6f vs %.6f" % (got, value))
    for plug in live:
        keys = cmds.keyframe(plug, query=True, keyframeCount=True) or 0
        check("5 %s collapsed instead of keying" % plug.split("|")[-1],
              keys == 0, "%d keys" % keys)
finally:
    for node in SBX:
        if cmds.objExists(node):
            cmds.delete(node)
    if cmds.objExists(twist.twist_set("arm_l")):
        cmds.delete(twist.twist_set("arm_l"))

# ---------------------------------------------------------------------------
# phase B -- the real skeleton
# ---------------------------------------------------------------------------
print()
print("=== phase B: the character ===")

DRIVERS = [SCENE[s.driver] for s in twist.segments(SCENE)]
DRIVERS = [d for d in dict.fromkeys(DRIVERS) if cmds.objExists(d)]
FRAMES = sorted(set([start, end] + [start + (end - start) * i // 4
                                    for i in range(5)]))
BEFORE = {}
for f in FRAMES:
    cmds.currentTime(f, edit=True)
    BEFORE[f] = {d: cmds.xform(d, query=True, worldSpace=True, matrix=True)
                 for d in DRIVERS}
cmds.currentTime(frame, edit=True)

rigged, message = twist.build(SCENE)
print("build: %s" % message)
check("B0 something got rigged", rigged > 0, "%d joints" % rigged)

print()
print("%-30s %-4s %-8s %s" % ("joint", "chan", "weight", "driver"))
for net in sorted(networks(), key=lambda n: n["joint"]):
    print("%-30s %-4s %+8.4f %s" % (net["joint"].split("|")[-1],
                                    net["plug"].split(".")[-1],
                                    net["weight"],
                                    (net["driver"] or "?").split("|")[-1]))

# gate 7 -- the DG against the same twist computed in plain Python
animated = [d for d in DRIVERS if moving_curve(d)]
print("drivers carrying real animation: %d" % len(animated))
worst_gap = 0.0
if animated:
    for f in FRAMES:
        cmds.currentTime(f, edit=True)
        for net in networks():
            gap = abs(cmds.getAttr(net["plug"]) - expected_value(net))
            worst_gap = max(worst_gap, gap)
    cmds.currentTime(frame, edit=True)
    check("7 network == recomputed twist over %d frames" % len(FRAMES),
          worst_gap < 1e-4, "worst %.9f deg" % worst_gap)
else:
    pokes = []
    for joint, channel, delta in (("hand_l", "rx", 40.0),
                                  ("hand_l", "rz", 25.0),
                                  ("upperarm_l", "rx", 30.0),
                                  ("lowerarm_l", "rz", 35.0),
                                  ("foot_l", "rx", -30.0),
                                  ("thigh_l", "rx", 25.0)):
        if joint in SCENE and cmds.objExists(SCENE[joint]):
            pokes.append(("{0}.{1}".format(SCENE[joint], channel), delta))
    with poked(pokes):
        for net in networks():
            gap = abs(cmds.getAttr(net["plug"]) - expected_value(net))
            worst_gap = max(worst_gap, gap)
        check("7 network == recomputed twist in a mixed pose",
              worst_gap < 1e-4, "worst %.9f deg" % worst_gap)
        moved = [net["joint"].split("|")[-1] for net in networks()
                 if abs(cmds.getAttr(net["plug"]) - net["rest"]) > 0.1]
        check("7b the pose actually moved the twists", len(moved) >= 2,
              "%d moved" % len(moved))

# gate 8 -- idempotence
was = {net["plug"]: cmds.getAttr(net["plug"]) for net in networks()}
count = len(networks())
again, message = twist.build(SCENE)
print("second build: %s" % message)
check("8 the same joint count", len(networks()) == count,
      "%d then %d" % (count, len(networks())))
check("8b every value unchanged",
      all(abs(cmds.getAttr(p) - v) < 1e-6 for p, v in was.items()
          if cmds.objExists(p)))
check("8c the message says it replaced the old one", "replaced" in message,
      message)

# gate 9 -- the drivers did not move
worst_drift = 0.0
for f in FRAMES:
    cmds.currentTime(f, edit=True)
    for driver, matrix in BEFORE[f].items():
        worst_drift = max(worst_drift, worst(
            cmds.xform(driver, query=True, worldSpace=True, matrix=True),
            matrix))
cmds.currentTime(frame, edit=True)
check("9 driver bones unmoved over the timeline", worst_drift < 1e-6,
      "worst %.9f" % worst_drift)

# gate 10 -- a build and a switch leave the networks alone
before_nodes = sorted(n for net in networks() for n in net["nodes"])
before_values = {net["plug"]: cmds.getAttr(net["plug"]) for net in networks()}
message = fkcontrols.rebuild(SCENE)
print("rebuild: %s" % message)
if overrig.NOT_LOADED_MESSAGE in message:
    print("SKIPPED gate 10 -- OverRig is not available: %s" % message)
else:
    check("10 the twist rig survives a full Build",
          len(networks()) == len(before_values),
          "%d then %d" % (len(before_values), len(networks())))
    if "arm_l" in builder.built_limbs():
        print("switch to FK: %s" % fkcontrols.switch_limbs(SCENE,
                                                           ["arm_l"])[2])
        print("switch to IK: %s" % fkcontrols.switch_limbs(SCENE,
                                                           ["arm_l"])[2])
        now_nodes = sorted(n for net in networks() for n in net["nodes"])
        check("10b Switch FK/IK touches no twist node",
              now_nodes == before_nodes,
              "%d then %d" % (len(before_nodes), len(now_nodes)))
        gap = max([abs(cmds.getAttr(p) - v)
                   for p, v in before_values.items()
                   if cmds.objExists(p)] or [0.0])
        check("10c and no twist value", gap < 1e-3, "worst %.6f" % gap)

cmds.autoKeyframe(state=auto_key)
if selection:
    cmds.select([s for s in selection if cmds.objExists(s)], replace=True)
else:
    cmds.select(clear=True)
cmds.currentTime(frame, edit=True)

print()
print("=== %d gate(s) failed ===" % len(failures))
for label in failures:
    print("  FAIL %s" % label)
