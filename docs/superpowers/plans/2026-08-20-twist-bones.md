# Twist bones Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the skeleton's UE twist joints distribute their segment's roll automatically, built and torn down with the rest of the rig.

**Architecture:** A new `maya_overrig/twist.py` — pure resolution above a `# scene` banner, scene work below — builds a seven-node DG network per twist joint that computes the exact swing–twist of a driver bone about the measured bone axis and writes a fraction of it into one rotate channel. It reads **bones**, so Switch FK/IK needs no handling. `fkcontrols.rebuild` builds it; `fkcontrols.bake_selection` and `rebuild`'s teardown bake it down to curves and delete it.

**Tech Stack:** Python 3 for Maya 2027, `maya.cmds`, `maya.api.OpenMaya`, stdlib `unittest` under `mayapy`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-20-twist-bones-design.md`. Read it first.
- Tests run with `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`. No `pip install` into the Maya tree, no pytest.
- In PowerShell never pipe `mayapy` through `2>&1`; write git commit messages to a file and use `git commit -F`.
- Layering: `twist.py` may import `maya.cmds`, `maya.api.OpenMaya`, `naming`, `builder`, `overrig`. It must NOT import `fkcontrols` (that direction is a cycle).
- Manifest name: `RigPicker_twist_<limb>` where limb is one of `arm_l arm_r leg_l leg_r`. `builder.recorded_members()` picks it up by the `RigPicker_*` prefix automatically — do not add it anywhere by hand.
- Never write a literal rest value into an animated channel, and disable autoKey around any poke (trap 14).
- Angles are degrees everywhere (Maya's default unit); the plan's numbers assume it.

---

### Task 1: The pure half — table, joint discovery, fractions, axis choice

**Files:**
- Create: `maya_overrig/twist.py`
- Test: `tests/test_twist.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `FOLLOW = "follow"`, `COUNTER = "counter"`
  - `Segment = namedtuple("Segment", "limb bone tip driver kind")`
  - `SEGMENTS` — tuple of 8 `Segment`
  - `SET_PREFIX = "RigPicker_twist_"`, `twist_set(limb) -> str`
  - `segments(scene_map) -> [Segment]`
  - `twist_joints(children) -> [str]` (leaf names, index order)
  - `weights(names, positions, kind) -> [float]`
  - `AxisChoice = namedtuple("AxisChoice", "channel sign reason")`
  - `axis_choice(local_axes, bone_dir, rotate_order) -> AxisChoice`
  - `ROTATE_ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")`
  - `_WEIGHT = {}` — per-joint override table

- [ ] **Step 1: Write the failing tests**

`tests/test_twist.py`:

```python
"""Tests for the twist-bone resolution.

The network itself is proved by docs/superpowers/plans/verify_twist_bones.py.
What is testable here is every decision made before a node is created: which
segments a skeleton has, which of a bone's children are twist joints, what
fraction each one takes, and which channel may be written at all.
"""

import unittest

from maya_overrig import twist


class TestSegments(unittest.TestCase):

    def test_eight_segments_two_per_limb(self):
        self.assertEqual(len(twist.SEGMENTS), 8)
        for limb in ("arm_l", "arm_r", "leg_l", "leg_r"):
            kinds = sorted(s.kind for s in twist.SEGMENTS if s.limb == limb)
            self.assertEqual(kinds, [twist.COUNTER, twist.FOLLOW])

    def test_follow_drives_from_the_far_end(self):
        table = {(s.limb, s.kind): s for s in twist.SEGMENTS}
        arm = table[("arm_l", twist.FOLLOW)]
        self.assertEqual((arm.bone, arm.tip, arm.driver),
                         ("lowerarm_l", "hand_l", "hand_l"))
        leg = table[("leg_r", twist.FOLLOW)]
        self.assertEqual((leg.bone, leg.tip, leg.driver),
                         ("calf_r", "foot_r", "foot_r"))

    def test_counter_drives_from_the_bone_itself(self):
        table = {(s.limb, s.kind): s for s in twist.SEGMENTS}
        arm = table[("arm_l", twist.COUNTER)]
        self.assertEqual((arm.bone, arm.tip, arm.driver),
                         ("upperarm_l", "lowerarm_l", "upperarm_l"))
        leg = table[("leg_l", twist.COUNTER)]
        self.assertEqual((leg.bone, leg.tip, leg.driver),
                         ("thigh_l", "calf_l", "thigh_l"))

    def test_segments_needs_bone_tip_and_driver(self):
        full = {"upperarm_l": "|a", "lowerarm_l": "|b", "hand_l": "|c"}
        names = [(s.bone, s.kind) for s in twist.segments(full)]
        self.assertIn(("upperarm_l", twist.COUNTER), names)
        self.assertIn(("lowerarm_l", twist.FOLLOW), names)
        self.assertEqual(len(names), 2)

    def test_a_missing_tip_drops_the_segment(self):
        """A UE4-schema arm with no hand cannot have a forearm twist."""
        partial = {"upperarm_l": "|a", "lowerarm_l": "|b"}
        names = [(s.bone, s.kind) for s in twist.segments(partial)]
        self.assertEqual(names, [("upperarm_l", twist.COUNTER)])

    def test_empty_map_gives_nothing(self):
        self.assertEqual(twist.segments({}), [])

    def test_set_name_is_per_limb(self):
        self.assertEqual(twist.twist_set("arm_l"), "RigPicker_twist_arm_l")


class TestTwistJoints(unittest.TestCase):

    def test_picks_the_twist_children_only(self):
        children = ["lowerarm_twist_01_l", "hand_l", "lowerarm_twist_02_l"]
        self.assertEqual(twist.twist_joints(children),
                         ["lowerarm_twist_01_l", "lowerarm_twist_02_l"])

    def test_sorted_by_index_not_by_string(self):
        children = ["x_twist_10_l", "x_twist_02_l", "x_twist_1_l"]
        self.assertEqual(twist.twist_joints(children),
                         ["x_twist_1_l", "x_twist_02_l", "x_twist_10_l"])

    def test_a_prefixed_skeleton_still_matches(self):
        """Per-joint prefixes are normal on this rig; the match is an infix."""
        self.assertEqual(twist.twist_joints(["ue5:MyChar_lowerarm_twist_01_l"]),
                         ["ue5:MyChar_lowerarm_twist_01_l"])

    def test_case_insensitive(self):
        self.assertEqual(twist.twist_joints(["Lowerarm_Twist_01_L"]),
                         ["Lowerarm_Twist_01_L"])

    def test_no_twists_is_empty(self):
        self.assertEqual(twist.twist_joints(["hand_l", "ik_hand_gun"]), [])

    def test_the_word_twist_without_separators_does_not_match(self):
        """`twistybone` is somebody else's joint, not a UE twist joint."""
        self.assertEqual(twist.twist_joints(["twistybone", "twist"]), [])


class TestWeights(unittest.TestCase):

    def test_follow_takes_its_measured_fraction(self):
        self.assertEqual(twist.weights(["a", "b"], [0.25, 0.75],
                                       twist.FOLLOW), [0.25, 0.75])

    def test_counter_gives_back_what_it_inherited(self):
        """A joint at the shoulder counters everything, one at the elbow none."""
        self.assertEqual(twist.weights(["a", "b"], [0.0, 1.0],
                                       twist.COUNTER), [-1.0, 0.0])

    def test_counter_at_a_quarter_counters_three_quarters(self):
        self.assertEqual(twist.weights(["a"], [0.25], twist.COUNTER), [-0.75])

    def test_two_joints_at_the_same_place_split_evenly(self):
        """Positions that carry no information are replaced, not trusted:
        two joints in one spot would otherwise take identical fractions."""
        self.assertEqual(twist.weights(["a", "b"], [0.0, 0.0],
                                       twist.FOLLOW),
                         [1.0 / 3.0, 2.0 / 3.0])

    def test_a_single_joint_at_the_origin_falls_back_to_half(self):
        self.assertEqual(twist.weights(["a"], [0.0], twist.FOLLOW), [0.5])

    def test_a_single_joint_with_a_real_position_is_trusted(self):
        self.assertEqual(twist.weights(["a"], [0.4], twist.FOLLOW), [0.4])

    def test_positions_are_clamped_to_the_bone(self):
        """A twist joint measured past the far end, or behind the origin,
        would otherwise ask for more twist than exists."""
        self.assertEqual(twist.weights(["a", "b"], [-0.2, 1.4],
                                       twist.FOLLOW), [0.0, 1.0])

    def test_the_override_table_wins(self):
        twist._WEIGHT["lowerarm_twist_01_l"] = 0.9
        try:
            self.assertEqual(
                twist.weights(["lowerarm_twist_01_l"], [0.4], twist.FOLLOW),
                [0.9])
        finally:
            del twist._WEIGHT["lowerarm_twist_01_l"]

    def test_the_override_is_matched_on_the_leaf_name(self):
        twist._WEIGHT["lowerarm_twist_01_l"] = -0.25
        try:
            self.assertEqual(
                twist.weights(["ns:Char_lowerarm_twist_01_l"], [0.4],
                              twist.FOLLOW), [-0.25])
        finally:
            del twist._WEIGHT["lowerarm_twist_01_l"]

    def test_no_joints_is_no_weights(self):
        self.assertEqual(twist.weights([], [], twist.FOLLOW), [])


class TestAxisChoice(unittest.TestCase):

    IDENT = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0),
             "z": (0.0, 0.0, 1.0)}

    def test_x_along_the_bone_with_rotate_order_xyz(self):
        got = twist.axis_choice(self.IDENT, (1.0, 0.0, 0.0), 0)
        self.assertEqual((got.channel, got.sign, got.reason), ("x", 1.0, None))

    def test_a_flipped_axis_is_taken_with_a_negative_sign(self):
        got = twist.axis_choice(self.IDENT, (-1.0, 0.0, 0.0), 0)
        self.assertEqual((got.channel, got.sign, got.reason), ("x", -1.0, None))

    def test_y_along_the_bone_needs_a_y_first_rotate_order(self):
        got = twist.axis_choice(self.IDENT, (0.0, 1.0, 0.0), 1)   # yzx
        self.assertEqual((got.channel, got.sign, got.reason), ("y", 1.0, None))

    def test_the_bone_axis_must_be_first_in_the_rotate_order(self):
        """Adding to a channel that is not innermost rotates about the parent,
        not about the bone: it would bend where it should roll."""
        got = twist.axis_choice(self.IDENT, (0.0, 1.0, 0.0), 0)   # xyz
        self.assertIsNone(got.channel)
        self.assertIn("rotate order", got.reason)

    def test_an_axis_off_the_bone_is_refused(self):
        skew = {"x": (0.7, 0.7, 0.0), "y": (-0.7, 0.7, 0.0),
                "z": (0.0, 0.0, 1.0)}
        got = twist.axis_choice(skew, (1.0, 0.0, 0.0), 0)
        self.assertIsNone(got.channel)
        self.assertIn("off the bone", got.reason)

    def test_a_small_misalignment_is_accepted(self):
        """Nothing in a real skeleton is exact; 5 degrees is not a refusal."""
        near = {"x": (0.9962, 0.0872, 0.0), "y": (-0.0872, 0.9962, 0.0),
                "z": (0.0, 0.0, 1.0)}
        got = twist.axis_choice(near, (1.0, 0.0, 0.0), 0)
        self.assertEqual(got.channel, "x")

    def test_a_zero_bone_direction_is_refused(self):
        got = twist.axis_choice(self.IDENT, (0.0, 0.0, 0.0), 0)
        self.assertIsNone(got.channel)
        self.assertIn("zero", got.reason)

    def test_every_rotate_order_names_a_real_channel(self):
        self.assertEqual(len(twist.ROTATE_ORDERS), 6)
        for order in twist.ROTATE_ORDERS:
            self.assertEqual(sorted(order), ["x", "y", "z"])
```

- [ ] **Step 2: Run them and watch them fail**

```bash
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_twist -v
```

Expected: `ModuleNotFoundError: No module named 'maya_overrig.twist'`.

- [ ] **Step 3: Write the pure half**

`maya_overrig/twist.py` — module docstring, imports, then:

```python
import re
from collections import namedtuple

import maya.cmds as cmds
import maya.api.OpenMaya as om

from maya_overrig import builder, naming, overrig

SET_PREFIX = "RigPicker_twist_"

FOLLOW = "follow"
COUNTER = "counter"

Segment = namedtuple("Segment", "limb bone tip driver kind")

SEGMENTS = (
    Segment("arm_l", "upperarm_l", "lowerarm_l", "upperarm_l", COUNTER),
    Segment("arm_l", "lowerarm_l", "hand_l", "hand_l", FOLLOW),
    Segment("arm_r", "upperarm_r", "lowerarm_r", "upperarm_r", COUNTER),
    Segment("arm_r", "lowerarm_r", "hand_r", "hand_r", FOLLOW),
    Segment("leg_l", "thigh_l", "calf_l", "thigh_l", COUNTER),
    Segment("leg_l", "calf_l", "foot_l", "foot_l", FOLLOW),
    Segment("leg_r", "thigh_r", "calf_r", "thigh_r", COUNTER),
    Segment("leg_r", "calf_r", "foot_r", "foot_r", FOLLOW),
)

LIMBS = tuple(dict.fromkeys(s.limb for s in SEGMENTS))

_WEIGHT = {}

ROTATE_ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")
_AXIS_TOLERANCE = 0.9848   # cos(10 degrees)
_PATTERN = re.compile(r"_twist_(\d+)(?:_|$)", re.IGNORECASE)


def twist_set(limb):
    return SET_PREFIX + limb


def segments(scene_map):
    return [s for s in SEGMENTS
            if s.bone in scene_map and s.tip in scene_map
            and s.driver in scene_map]


def twist_joints(children):
    hits = [(int(_PATTERN.search(c).group(1)), c) for c in children
            if _PATTERN.search(c)]
    return [name for _index, name in sorted(hits)]


def weights(names, positions, kind):
    if not names:
        return []
    spread = max(positions) - min(positions)
    if max(positions) < 1e-3 or (len(positions) > 1 and spread < 1e-3):
        positions = [(i + 1.0) / (len(positions) + 1.0)
                     for i in range(len(positions))]
    out = []
    for name, position in zip(names, positions):
        position = min(1.0, max(0.0, position))
        weight = position if kind == FOLLOW else -(1.0 - position)
        out.append(_WEIGHT.get(naming.leaf(name), weight))
    return out


AxisChoice = namedtuple("AxisChoice", "channel sign reason")


def axis_choice(local_axes, bone_dir, rotate_order):
    direction = om.MVector(bone_dir)
    if direction.length() < 1e-9:
        return AxisChoice(None, 0.0, "the bone direction is zero")
    direction.normalize()

    best = None
    for channel, vector in local_axes.items():
        axis = om.MVector(vector)
        if axis.length() < 1e-9:
            continue
        axis.normalize()
        dot = axis * direction
        if best is None or abs(dot) > abs(best[1]):
            best = (channel, dot)
    if best is None:
        return AxisChoice(None, 0.0, "the joint has no usable axes")

    channel, dot = best
    if abs(dot) < _AXIS_TOLERANCE:
        return AxisChoice(None, 0.0,
                          "no local axis runs along the bone (best is "
                          "{0}, {1:.1f} deg off the bone)".format(
                              channel, math.degrees(math.acos(min(
                                  1.0, abs(dot))))))
    innermost = ROTATE_ORDERS[rotate_order][0]
    if channel != innermost:
        return AxisChoice(None, 0.0,
                          "the bone axis is {0} but the rotate order is {1} "
                          "- {2} is not the innermost channel".format(
                              channel, ROTATE_ORDERS[rotate_order].upper(),
                              channel))
    return AxisChoice(channel, 1.0 if dot > 0 else -1.0, None)
```

Add `import math` to the imports.

- [ ] **Step 4: Run the tests and watch them pass**

```bash
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_twist -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/twist.py tests/test_twist.py
git commit -F <message file>
```

---

### Task 2: The network — build, record, refuse

**Files:**
- Modify: `maya_overrig/twist.py` (append the `# scene` half)
- Test: `tests/test_twist.py` (append `TestNetworkNames`)

**Interfaces:**
- Consumes: everything from Task 1.
- Produces:
  - `node_names(joint) -> dict` with keys `delta quat dot norm angle weight rest`
  - `build(scene_map, limbs=None) -> (int, str)` — (joints rigged, message)
  - `built_limbs() -> [str]`
  - `has_twist() -> bool`
  - `driven_plugs(limb) -> [str]`

- [ ] **Step 1: Write the failing test for the one testable piece**

Append to `tests/test_twist.py`:

```python
class TestNodeNames(unittest.TestCase):

    def test_seven_distinct_names_derived_from_the_joint(self):
        names = twist.node_names("|root|lowerarm_twist_01_l")
        self.assertEqual(len(set(names.values())), 7)
        for name in names.values():
            self.assertTrue(name.startswith("lowerarm_twist_01_l_tw"))

    def test_the_dag_path_never_reaches_the_node_name(self):
        """A node name with a pipe in it is not a legal Maya name."""
        for name in twist.node_names("|a|b|thigh_twist_01_r").values():
            self.assertNotIn("|", name)

    def test_a_namespace_never_reaches_the_node_name(self):
        for name in twist.node_names("|ns:calf_twist_02_l").values():
            self.assertNotIn(":", name)
```

- [ ] **Step 2: Run and watch it fail**

Expected: `AttributeError: module 'maya_overrig.twist' has no attribute 'node_names'`.

- [ ] **Step 3: Write the scene half**

```python
# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

_ROLES = ("delta", "quat", "dot", "norm", "angle", "weight", "rest")


def node_names(joint):
    stem = naming.leaf(joint).split(":")[-1]
    return {role: "{0}_tw_{1}".format(stem, role) for role in _ROLES}


def built_limbs():
    return [limb for limb in LIMBS if overrig.set_members(twist_set(limb))]


def has_twist():
    return bool(built_limbs())


def driven_plugs(limb):
    """The channels this limb's networks drive, read back from the rig."""
    plugs = []
    for member in overrig.set_members(twist_set(limb)):
        if not cmds.objExists(member):
            continue
        if cmds.objectType(member) != "addDoubleLinear":
            continue
        for plug in cmds.listConnections(member + ".output", source=False,
                                         destination=True, plugs=True) or []:
            plugs.append(plug)
    return plugs


def _axis_for(joint, direction):
    matrix = cmds.getAttr(joint + ".worldMatrix")
    axes = {"x": matrix[0:3], "y": matrix[4:7], "z": matrix[8:11]}
    return axis_choice(axes, direction, cmds.getAttr(joint + ".rotateOrder"))


def _world_point(node):
    matrix = cmds.getAttr(node + ".worldMatrix")
    return om.MVector(matrix[12], matrix[13], matrix[14])


def _clear_channel(plug):
    """Free a twist channel for our network, or say why we cannot have it.

    An animCurve is animation we supersede -- deleted, because an orphan
    curve is a trap for whoever reads the file next, and Bake+Delete writes
    a fresh one from our network. Anything else driving the channel is
    somebody's work: refused by name rather than taken over silently.
    """
    if cmds.getAttr(plug, lock=True):
        return "the channel is locked"
    inputs = cmds.listConnections(plug, source=True, destination=False) or []
    curves = [n for n in inputs if cmds.objectType(n).startswith("animCurve")]
    if len(curves) != len(inputs):
        return "the channel is already driven by {0}".format(
            ", ".join(sorted({cmds.objectType(n) for n in inputs
                              if n not in curves})))
    if curves:
        cmds.delete(curves)
    return None


def _network(joint, driver, axis, weight, direction):
    """Seven nodes computing weight * the driver's twist about `direction`."""
    names = node_names(joint)
    rest = om.MMatrix(cmds.getAttr(driver + ".matrix")).inverse()

    delta = cmds.createNode("multMatrix", name=names["delta"], skipSelect=True)
    cmds.setAttr(delta + ".matrixIn[0]", list(rest), type="matrix")
    cmds.connectAttr(driver + ".matrix", delta + ".matrixIn[1]")

    quat = cmds.createNode("decomposeMatrix", name=names["quat"],
                           skipSelect=True)
    cmds.connectAttr(delta + ".matrixSum", quat + ".inputMatrix")

    dot = cmds.createNode("vectorProduct", name=names["dot"], skipSelect=True)
    cmds.setAttr(dot + ".operation", 1)              # dot product
    cmds.setAttr(dot + ".normalizeOutput", 0)
    for channel in "XYZ":
        cmds.connectAttr(quat + ".outputQuat" + channel,
                         dot + ".input1" + channel)
    cmds.setAttr(dot + ".input2", direction.x, direction.y, direction.z,
                 type="double3")

    # quatToEuler assumes a UNIT quaternion: (v.a, 0, 0, w) is not one, and
    # feeding it raw turns the angle into atan2(2wx, 1-2x^2), which is only
    # the twist when x^2 + w^2 == 1.
    norm = cmds.createNode("quatNormalize", name=names["norm"],
                           skipSelect=True)
    cmds.connectAttr(dot + ".outputX", norm + ".inputQuatX")
    cmds.connectAttr(quat + ".outputQuatW", norm + ".inputQuatW")

    angle = cmds.createNode("quatToEuler", name=names["angle"],
                            skipSelect=True)
    cmds.setAttr(angle + ".inputRotateOrder", 0)     # XYZ: rx == 2*atan2(x, w)
    cmds.connectAttr(norm + ".outputQuatX", angle + ".inputQuatX")
    cmds.connectAttr(norm + ".outputQuatW", angle + ".inputQuatW")

    scaled = cmds.createNode("multDoubleLinear", name=names["weight"],
                             skipSelect=True)
    cmds.connectAttr(angle + ".outputRotateX", scaled + ".input1")
    cmds.setAttr(scaled + ".input2", weight)

    total = cmds.createNode("addDoubleLinear", name=names["rest"],
                            skipSelect=True)
    cmds.connectAttr(scaled + ".output", total + ".input1")
    return [delta, quat, dot, norm, angle, scaled, total]


def build(scene_map, limbs=None):
    """Build the twist networks. Returns (joints rigged, message).

    Reads the pose it is called in: the fraction's zero is the driver's
    local matrix now, and the channel keeps the value it holds now, so
    nothing moves at the build frame. Build in the bind pose.
    """
    wanted = list(LIMBS if limbs is None else limbs)
    standing = [limb for limb in wanted if overrig.set_members(twist_set(limb))]
    replaced = 0
    if standing:
        replaced, _message = bake(standing)

    rigged = 0
    skipped = []
    animated = []
    for segment in segments(scene_map):
        if segment.limb not in wanted:
            continue
        bone = scene_map[segment.bone]
        tip = scene_map[segment.tip]
        driver = scene_map[segment.driver]

        children = cmds.listRelatives(bone, children=True, type="joint",
                                      fullPath=True) or []
        leaves = {naming.leaf(path): path for path in children}
        joints = [leaves[name] for name in twist_joints(sorted(leaves))]
        if not joints:
            continue

        bone_vector = _world_point(tip) - _world_point(bone)
        length = bone_vector.length()
        if length < 1e-6:
            skipped.append("{0} (zero length)".format(naming.leaf(bone)))
            continue
        along = bone_vector / length
        positions = [(_world_point(j) - _world_point(bone)) * along / length
                     for j in joints]
        fractions = weights(joints, positions, segment.kind)

        # The axis is measured against the DRIVER's parent frame, which is
        # the frame the delta operates in: the segment bone for a follow
        # joint, its parent for a counter joint.
        frame = cmds.listRelatives(driver, parent=True, fullPath=True)
        frame = frame[0] if frame else None
        local = _to_frame(along, frame)

        created = []
        for joint, weight in zip(joints, fractions):
            choice = _axis_for(joint, along)
            if choice.channel is None:
                skipped.append("{0} ({1})".format(naming.leaf(joint),
                                                  choice.reason))
                continue
            plug = "{0}.r{1}".format(joint, choice.channel)
            refusal = _clear_channel(plug)
            if refusal:
                skipped.append("{0} ({1})".format(naming.leaf(joint),
                                                  refusal))
                continue
            nodes = _network(joint, driver, choice.channel,
                             weight * choice.sign, local)
            cmds.setAttr(nodes[-1] + ".input2", cmds.getAttr(plug))
            cmds.connectAttr(nodes[-1] + ".output", plug, force=True)
            created.extend(nodes)
            rigged += 1
        if created:
            cmds.sets(created, addElement=_ensure_set(segment.limb))
        if not _is_constant(driver):
            animated.append(naming.leaf(driver))

    return rigged, _message_for(rigged, replaced, skipped, animated)
```

Helpers used above, written in the same task:

```python
def _ensure_set(limb):
    name = twist_set(limb)
    if not cmds.objExists(name):
        cmds.sets(name=name, empty=True)
    return name


def _to_frame(vector, frame):
    """A world vector expressed in `frame`'s local space; world if None."""
    if frame is None:
        return om.MVector(vector)
    inverse = om.MMatrix(cmds.getAttr(frame + ".worldInverseMatrix"))
    return (om.MVector(vector) * inverse).normal()


def _is_constant(node):
    """Whether the node's animation actually moves (trap 30)."""
    for curve in cmds.listConnections(node, source=True, destination=False,
                                      type="animCurve") or []:
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        if values and (max(values) - min(values)) > 1e-6:
            return False
    return True


def _message_for(rigged, replaced, skipped, animated):
    if not rigged and not skipped:
        return "no twist joints on this skeleton"
    message = "{0} twist joint(s) rigged".format(rigged)
    if replaced:
        message += ", {0} replaced".format(replaced)
    if skipped:
        message += ". Skipped: " + "; ".join(skipped[:4])
    if animated:
        message += ". Twist zero taken from this pose ({0} carries "
        message = message.format(", ".join(sorted(set(animated))[:3]))
    return message
```

- [ ] **Step 4: Run the whole suite**

```bash
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: every test green, count up by the new ones.

- [ ] **Step 5: Commit**

---

### Task 3: The bake — sample, disconnect, key, delete

**Files:**
- Modify: `maya_overrig/twist.py`
- Test: `tests/test_twist.py` (append `TestSampleCollapse`)

**Interfaces:**
- Consumes: `built_limbs`, `driven_plugs`, `twist_set` from Task 2.
- Produces:
  - `collapses(values) -> bool` (pure)
  - `bake(limbs=None) -> (int, str)`
  - `bake_all() -> (int, str)`

- [ ] **Step 1: Write the failing test**

```python
class TestCollapses(unittest.TestCase):

    def test_a_still_channel_needs_no_keys(self):
        self.assertTrue(twist.collapses([12.5, 12.5, 12.5]))

    def test_a_moving_channel_needs_keys(self):
        self.assertFalse(twist.collapses([12.5, 12.5, 12.6]))

    def test_one_sample_collapses(self):
        self.assertTrue(twist.collapses([3.0]))

    def test_nothing_collapses(self):
        self.assertTrue(twist.collapses([]))
```

- [ ] **Step 2: Run and watch it fail**

- [ ] **Step 3: Implement the bake**

```python
def collapses(values):
    """Whether a sampled channel is still enough to be a plain value.

    A rig on an unanimated skeleton would otherwise leave 61 identical keys
    on every twist joint.
    """
    return not values or (max(values) - min(values)) <= 1e-9


def bake(limbs=None):
    """Bake the twist networks onto the joints and remove them.

    Sampled with `getAttr(time=...)` and keyed by hand rather than through
    `bakeResults`: the channel's input is our own DG network, not a
    constraint, and this way the disconnect, the values and the keys are all
    ours to order. Reads the playback range, never the time slider's
    highlight, so it needs no highlight guard of its own.
    """
    wanted = [limb for limb in (LIMBS if limbs is None else limbs)
              if overrig.set_members(twist_set(limb))]
    if not wanted:
        return 0, "no twist rig to bake"

    start, end = overrig.frame_range()
    frames = [start + i for i in range(int(end - start) + 1)]

    baked = 0
    removed = 0
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        for limb in wanted:
            plugs = [p for p in driven_plugs(limb) if cmds.objExists(p)]
            samples = {plug: [cmds.getAttr(plug, time=frame)
                              for frame in frames] for plug in plugs}
            members = [m for m in overrig.set_members(twist_set(limb))
                       if cmds.objExists(m)]
            if members:
                cmds.delete(members)
                removed += len(members)
            for plug, values in samples.items():
                if not cmds.objExists(plug):
                    continue
                if collapses(values):
                    cmds.setAttr(plug, values[0] if values
                                 else cmds.getAttr(plug))
                else:
                    for frame, value in zip(frames, values):
                        cmds.setKeyframe(plug, time=frame, value=value)
                baked += 1
            # Maya deletes an objectSet with its last member (trap 18).
            if cmds.objExists(twist_set(limb)):
                cmds.delete(twist_set(limb))
    finally:
        cmds.autoKeyframe(state=autokey)

    return baked, "{0} twist joint(s) baked, {1} node(s) removed".format(
        baked, removed)


def bake_all():
    return bake(built_limbs())
```

Note the ORDER inside the loop: sample every frame first, then delete the
network (which frees the channels), then write. Writing before the delete is
impossible — the channel still has an input — and deleting before sampling
loses the values.

- [ ] **Step 4: Run the suite**

- [ ] **Step 5: Commit**

---

### Task 4: Wire it into Build and Bake+Delete

**Files:**
- Modify: `maya_overrig/fkcontrols.py` — `rebuild` (teardown + build), `bake_selection`
- Test: `tests/test_fkcontrols.py` (append `TestTwistWiring`)

**Interfaces:**
- Consumes: `twist.build`, `twist.bake`, `twist.has_twist`, `twist.built_limbs`.
- Produces: no new names; behaviour changes only.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fkcontrols.py`:

```python
class TestTwistWiring(unittest.TestCase):
    """The twist rig comes down with a bake and up with a build.

    Both entry points are wired through the module attribute, so a fake
    stands in for the whole scene half.
    """

    class FakeTwist(object):
        LIMBS = ("arm_l", "arm_r", "leg_l", "leg_r")

        def __init__(self, standing=()):
            self.standing = list(standing)
            self.built = []
            self.baked = []

        def has_twist(self):
            return bool(self.standing)

        def built_limbs(self):
            return list(self.standing)

        def build(self, scene_map, limbs=None):
            self.built.append(limbs)
            return 2, "2 twist joint(s) rigged"

        def bake(self, limbs=None):
            self.baked.append(list(limbs) if limbs is not None else None)
            return 2, "2 twist joint(s) baked, 14 node(s) removed"

    def setUp(self):
        self.real = fkcontrols.twist
        self.fake = self.FakeTwist(standing=["arm_l"])
        fkcontrols.twist = self.fake

    def tearDown(self):
        fkcontrols.twist = self.real

    def test_bake_selection_bakes_the_twist_of_the_limbs_it_bakes(self):
        baked = fkcontrols.twist_limbs_for(["arm_l"], ["leg_r"],
                                           ["arm_l", "leg_r", "spine"])
        self.assertEqual(baked, ["arm_l", "leg_r"])

    def test_a_spine_bake_leaves_the_twist_alone(self):
        self.assertEqual(
            fkcontrols.twist_limbs_for([], ["spine"], ["arm_l"]), [])

    def test_only_limbs_that_have_a_twist_rig_are_baked(self):
        self.assertEqual(
            fkcontrols.twist_limbs_for(["arm_l", "arm_r"], [], ["arm_l"]),
            ["arm_l"])
```

`twist_limbs_for(ik_limbs, fk_chains, standing)` is the pure resolution the
wiring needs; put it in `fkcontrols` next to `bake_selection`.

- [ ] **Step 2: Run and watch it fail**

- [ ] **Step 3: Wire it up**

In `fkcontrols.py`, add `twist` to the `maya_overrig` import line, then:

```python
def twist_limbs_for(ik_limbs, fk_chains, standing):
    """Limbs whose twist rig must come down with this bake.

    A limb name means the same thing in both manifests, so an arm baked as
    IK and an arm baked as FK chains resolve alike. Pure.
    """
    asked = set(ik_limbs) | set(fk_chains)
    return [limb for limb in standing if limb in asked]
```

In `bake_selection`, inside the undo chunk and BEFORE the limb and chain
bakes (the bones' motion is unchanged by a bake either way, and taking the
twist down first keeps the sampling clear of half-removed rigs):

```python
        twist_limbs = twist_limbs_for(ik_limbs, fk_chains,
                                      twist.built_limbs())
        if twist_limbs:
            _count, message = twist.bake(twist_limbs)
            messages.append(message)
```

In `rebuild`, in the teardown block, before the FK bake:

```python
        if twist.has_twist():
            _count, message = twist.bake()
            messages.append(message)
```

and as the last step of both build branches (hybrid and full FK), after the
IK groups are hung:

```python
        _count, message = twist.build(scene_map)
        messages.append(message)
```

Place the `twist.build` call after the `if fk_limbs: ... else: ...` block so
one call serves both modes.

- [ ] **Step 4: Run the whole suite**

- [ ] **Step 5: Commit**

---

### Task 5: Live proof and the working notes

**Files:**
- Create: `docs/superpowers/plans/verify_twist_bones.py`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a script meant to be sent through the command port, printing one
  `PASS`/`FAIL` line per gate and a final tally.

- [ ] **Step 1: Write the verification script**

Structure, following `verify_control_axes.py`:

- bind to the skeleton the way the picker does (`picker_window.bound_root()`,
  else `builder.character_roots()`), build the hierarchy map through
  `naming.hierarchy_map` + `detect_prefix`;
- record the driver bones' world matrices across the timeline BEFORE anything
  is built, for gate 6;
- `fkcontrols.rebuild(scene_map)`;
- gates:
  1. **fractions**: for each rigged twist joint, roll its driver about the
     measured bone axis by +90° (with autoKey off, restoring the value that
     was there — `pushed` context manager), read the joint's channel delta,
     and compare with `weight * 90` to 1e-3;
  2. **no cross-talk**: bend the elbow and the wrist 60° about an axis
     PERPENDICULAR to the bone, with no roll; every twist channel delta must
     be 0 to 1e-4;
  3. **switch**: `fkcontrols.switch_limbs(scene_map, ["arm_l"])` twice; the
     twist network's node count and every channel value are unchanged;
  4. **bake**: `twist.bake(["arm_l"])`; the baked curve value at each of five
     sampled frames matches what the live network read to 1e-4, and no node
     from `node_names` survives;
  5. **idempotence**: `twist.build(scene_map)` twice; the second call reports
     the first's joints as replaced and the node count is identical;
  6. **no drift**: every driver bone's world matrix on every frame matches the
     pre-build recording to 1e-6 — matrices, never euler channels (trap 31).
- never `cmds.undo()` (the whole script is one command), never write a literal
  rest value into a keyed channel.

- [ ] **Step 2: Send it through the command port and read the output file**

Runner pattern from `CLAUDE.md`: write the payload without a BOM, an idempotent
runner that touches `<out>.ran` first, poll for the output file.

- [ ] **Step 3: Fix whatever it finds, re-run until every gate is PASS**

- [ ] **Step 4: Write the working notes**

In `CLAUDE.md`: a `twist.py` row in the `maya_overrig` architecture table, a
**Twist bones** section under "What the tool does today" (the two kinds, the
measured axis and fractions, why Switch needs nothing, what Bake+Delete does,
the UE-bridge interaction), and any new trap the live run turns up.

- [ ] **Step 5: Commit**

---

## Self-review

**Spec coverage:** kinds and fractions → Task 1; the seven-node network and the
exact `atan2` → Task 2; measured axis with both refusals → Task 1 (pure) + Task 2
(`_axis_for`); discovery by name pattern → Task 1; manifest per limb → Task 2;
build on Build, nothing on Switch, bake on Bake+Delete → Task 4; the
`_WEIGHT` override → Task 1; the animated-driver warning → Task 2
(`_is_constant`); clean-bones bake → Task 3; UE-bridge note → Task 5 (docs; no
code change, the trap-37 guard is untouched by design); all six gates → Task 5.

**Placeholders:** none — every step carries the code or the exact command.

**Type consistency:** `build`/`bake` both return `(int, str)` and every call
site in Task 4 unpacks two values. `weights(names, positions, kind)` takes long
paths in Task 2 and leaf names in Task 1's tests, which is why the override
lookup goes through `naming.leaf`. `axis_choice` always returns an `AxisChoice`,
never None, and callers test `choice.channel is None`.
