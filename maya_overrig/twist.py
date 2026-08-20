"""Twist distribution on the skeleton's driven twist joints.

A UE skeleton carries twist joints -- `upperarm_twist_*`, `lowerarm_twist_*`,
`thigh_twist_*`, `calf_twist_*` -- whose whole job is to spread one segment's
roll along its length so the skin shears gradually instead of pinching at one
joint. In Unreal the engine's twist correction drives them at runtime; in a
Maya file they hang rigidly off their parent and do nothing at all.

This module drives them, exactly: the swing-twist decomposition of a driver
bone's rotation about the measured bone axis, a fraction of it written into one
rotate channel through seven stock nodes. It reads BONES, never controllers,
which is why Switch FK/IK needs no handling here -- a hand is a hand whichever
rig drives it.

Design: docs/superpowers/specs/2026-08-20-twist-bones-design.md
"""

import math
import re
from collections import namedtuple

import maya.cmds as cmds
import maya.api.OpenMaya as om

from maya_overrig import naming, overrig

SET_PREFIX = "RigPicker_twist_"

# The two kinds, and the sign of the fraction is their whole difference.
FOLLOW = "follow"     # the roll arrives from the far end: take +t of it
COUNTER = "counter"   # the roll is inherited from the parent: give -(1-t) back

Segment = namedtuple("Segment", "limb bone tip driver kind")

# `bone` owns the twist joints (they are its children), `tip` is the bone at
# its far end -- which measures the direction and the length -- and `driver`
# is whose roll gets distributed.
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

# Per-joint corrections, by leaf name -- the escape hatch fkrings._BORROW and
# _SCALE already are for ring sizes. Empty until an animator asks.
_WEIGHT = {}

# Maya's rotate orders, in attribute-value order. The FIRST channel of an
# order is the innermost one: changing it turns the joint about its own axis,
# which is the only way a rotate channel can produce a twist about the bone.
ROTATE_ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")

_AXIS_TOLERANCE = 0.9848             # cos(10 degrees)
_PATTERN = re.compile(r"_twist_(\d+)(?:_|$)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# pure
# ---------------------------------------------------------------------------

def twist_set(limb):
    """Name of the object set recording one limb's twist networks."""
    return SET_PREFIX + limb


def segments(scene_map):
    """Segments this skeleton can carry, as data.

    All three bones must exist: without the tip there is no direction and no
    length to measure the fractions against, and a UE4-schema arm with no
    hand has nothing to distribute.
    """
    return [s for s in SEGMENTS
            if s.bone in scene_map and s.tip in scene_map
            and s.driver in scene_map]


def twist_joints(children):
    """The twist joints among a bone's children, in index order.

    Matched on the `_twist_<nn>` infix rather than tabulated, so a rig with
    one twist joint per segment and a rig with three are one code path, and
    a per-joint prefix or a namespace changes nothing. Pure: `children` is
    a list of names.
    """
    hits = []
    for name in children:
        found = _PATTERN.search(name)
        if found:
            hits.append((int(found.group(1)), name))
    return [name for _index, name in sorted(hits)]


def weights(names, positions, kind):
    """Signed fraction of the driver's roll for each twist joint.

    `positions` are the joints' measured places along the parent bone, 0 at
    its origin and 1 at its far end, in the same order as `names`.

    A FOLLOW joint takes `+t`: the roll enters at the far end, so skin near
    the origin must stay put and skin at the end must follow. A COUNTER joint
    takes `-(1 - t)`: it is a DAG child of the rolling bone and inherits all
    of the roll already, so what it needs is to give some back -- everything
    at the shoulder, nothing at the elbow.

    Positions that carry no information are replaced by an even split: every
    joint sitting on the parent's origin, or two joints in the same spot,
    which cannot be what a rigger who authored two of them meant. A measured
    position is otherwise trusted, clamped to the bone's ends.
    """
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
    """Which rotate channel of a twist joint is a twist about its bone.

    `local_axes` maps "x"/"y"/"z" to the joint's own axes, and `bone_dir` is
    the bone's direction, both in one common frame. Returns the channel and
    the sign the fraction needs, or a channel of None and a reason.

    Two refusals, both deliberate. An axis that does not run along the bone
    means this joint is not oriented the way a twist joint has to be. And a
    channel that is not innermost in the rotate order turns the joint about
    its PARENT's axis, so writing a twist there would bend the joint where it
    should roll -- a candy wrapper traded for something worse. Pure.
    """
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
        off = math.degrees(math.acos(min(1.0, abs(dot))))
        return AxisChoice(None, 0.0,
                          "no local axis runs along the bone - the closest, "
                          "{0}, is {1:.1f} deg off".format(channel, off))

    innermost = ROTATE_ORDERS[rotate_order][0]
    if channel != innermost:
        return AxisChoice(
            None, 0.0,
            "the bone axis is {0} but the rotate order is {1}, so {0} is not "
            "the innermost channel".format(channel,
                                           ROTATE_ORDERS[rotate_order].upper()))
    return AxisChoice(channel, 1.0 if dot > 0 else -1.0, None)
