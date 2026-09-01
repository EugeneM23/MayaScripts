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

from maya_overrig import manifest, naming, overrig

SET_PREFIX = manifest.TWIST_PREFIX

# The driven channels, recorded on the manifest as "<uuid>.<attr>" -- see
# driven_plugs for why neither walk of the rig itself is safe.
PLUGS_ATTR = "rigPickerTwistPlugs"

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

def twist_set_name(limb):
    """The readable name a NEW twist manifest gets. Pure."""
    return SET_PREFIX + limb


def twist_set(limb, table=None):
    """The ACTIVE character's twist manifest for one limb.

    Falls back to the readable name when this character has none, so
    `set_members` reads empty and `objExists` reads False exactly as they
    did before manifests carried a character tag.
    """
    return (manifest.find(manifest.KIND_TWIST, limb, table=table)
            or twist_set_name(limb))


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


# ---------------------------------------------------------------------------
# scene
#
# Undo chunks belong to the callers: every entry point that reaches here --
# fkcontrols.rebuild, fkcontrols.bake_selection -- already opens one around a
# whole build or bake, and a half-built network must undo with the rest of it.
# ---------------------------------------------------------------------------

_ROLES = ("delta", "quat", "dot", "norm", "angle", "weight", "rest")


def node_names(joint):
    """Names for one joint's seven nodes, from its leaf name.

    Never from the DAG path or the namespace: neither is a legal node name,
    and the leaf is already unique among the twist joints.
    """
    stem = naming.leaf(joint)
    return {role: "{0}_tw_{1}".format(stem, role) for role in _ROLES}


def built_limbs():
    """Limbs the ACTIVE character has twist networks recorded against."""
    table = manifest.records()
    return [limb for limb in LIMBS
            if manifest.members(manifest.KIND_TWIST, limb, table=table)]


def has_twist():
    """True when this tool has a twist network in the scene."""
    return bool(built_limbs())


def split_plugs(text):
    """The recorded plug list, as [(uuid, channel)]. Pure.

    Blanks are dropped rather than raising: the attribute is written by us,
    but an animator can edit anything in a scene file.
    """
    found = []
    for token in (text or "").split():
        if "." not in token:
            continue
        uuid, _dot, channel = token.partition(".")
        if uuid and channel:
            found.append((uuid, channel))
    return found


def driven_plugs(limb):
    """The channels this limb's networks drive.

    Read from an attribute on the manifest rather than by walking the rig,
    and both of the obvious walks are booby-trapped. `cmds.objectType` on an
    addDoubleLinear answers **"addDL"**, not the type name you created it
    with, so filtering the members by type finds nothing at all (measured --
    it made the bake a silent no-op that deleted the network and the values
    with it). And there is no direct connection to walk to anyway: Maya
    splices a **unitConversion** between our unitless output and the angle
    channel, so `.output` leads to that node, not to the joint.

    UUIDs, so a renamed or reparented joint still resolves and a deleted one
    quietly drops out.
    """
    name = twist_set(limb)
    if not cmds.objExists(name):
        return []
    if not cmds.attributeQuery(PLUGS_ATTR, node=name, exists=True):
        return []
    plugs = []
    for uuid, channel in split_plugs(cmds.getAttr(
            "{0}.{1}".format(name, PLUGS_ATTR))):
        paths = cmds.ls(uuid, long=True) or []
        if paths:
            plugs.append("{0}.{1}".format(paths[0], channel))
    return list(dict.fromkeys(plugs))


def _record_plugs(limb, pairs):
    """Add (joint, channel) pairs to the limb's manifest record."""
    name = _ensure_set(limb)
    if not cmds.attributeQuery(PLUGS_ATTR, node=name, exists=True):
        cmds.addAttr(name, longName=PLUGS_ATTR, dataType="string")
    plug = "{0}.{1}".format(name, PLUGS_ATTR)
    text = cmds.getAttr(plug) or ""
    tokens = text.split()
    for joint, channel in pairs:
        uuid = cmds.ls(joint, uuid=True)
        if uuid:
            token = "{0}.{1}".format(uuid[0], channel)
            if token not in tokens:
                tokens.append(token)
    cmds.setAttr(plug, " ".join(tokens), type="string")


def _world_matrix(node):
    return om.MMatrix(cmds.xform(node, query=True, worldSpace=True,
                                 matrix=True))


def _world_point(node):
    matrix = _world_matrix(node)
    return om.MVector(matrix[12], matrix[13], matrix[14])


def _local_axes(node):
    """The node's own axes, in world."""
    matrix = _world_matrix(node)
    return {"x": (matrix[0], matrix[1], matrix[2]),
            "y": (matrix[4], matrix[5], matrix[6]),
            "z": (matrix[8], matrix[9], matrix[10])}


def _to_frame(vector, frame):
    """A world direction expressed in `frame`'s local space; world if None."""
    if frame is None:
        return om.MVector(vector).normal()
    return (om.MVector(vector) * _world_matrix(frame).inverse()).normal()


def _parent_of(node):
    found = cmds.listRelatives(node, parent=True, fullPath=True) or []
    return found[0] if found else None


def _local_matrix_inverse(node):
    """Inverse of the node's local matrix right now -- the twist's zero."""
    return om.MMatrix(cmds.getAttr(node + ".matrix")).inverse()


def _is_constant(node):
    """Whether the node's animation actually MOVES.

    "It has animCurves" is not "the animator has animation": every build
    leaves the bones carrying constant baked curves (trap 30).
    """
    for curve in cmds.listConnections(node, source=True, destination=False,
                                      type="animCurve") or []:
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        if values and (max(values) - min(values)) > 1e-6:
            return False
    return True


def _clear_channel(plug):
    """Free a twist channel for our network, or say why we cannot have it.

    An animCurve is animation we supersede -- deleted, because an orphan
    curve is a trap for whoever reads the file next, and Bake+Delete writes
    a fresh one from our network. Anything else driving the channel is
    work somebody did by hand: refused by name, never taken over silently.
    """
    if cmds.getAttr(plug, lock=True):
        return "the channel is locked"
    inputs = cmds.listConnections(plug, source=True, destination=False) or []
    curves = [n for n in inputs if cmds.objectType(n).startswith("animCurve")]
    strangers = sorted({cmds.objectType(n) for n in inputs
                        if n not in curves})
    if strangers:
        return "the channel is already driven by " + ", ".join(strangers)
    if curves:
        cmds.delete(curves)
    return None


def _network(joint, driver, weight, direction):
    """Seven nodes computing `weight` x the driver's twist about `direction`.

    `direction` is the bone axis in the DRIVER'S PARENT frame, which is the
    frame the delta operates in. Returns the created nodes, the last of them
    the addDoubleLinear whose output is meant for the joint's channel.
    """
    names = node_names(joint)
    rest = _local_matrix_inverse(driver)

    delta = cmds.createNode("multMatrix", name=names["delta"], skipSelect=True)
    cmds.setAttr(delta + ".matrixIn[0]", [rest[i] for i in range(16)],
                 type="matrix")
    cmds.connectAttr(driver + ".matrix", delta + ".matrixIn[1]")

    quat = cmds.createNode("decomposeMatrix", name=names["quat"],
                           skipSelect=True)
    cmds.connectAttr(delta + ".matrixSum", quat + ".inputMatrix")

    dot = cmds.createNode("vectorProduct", name=names["dot"], skipSelect=True)
    cmds.setAttr(dot + ".operation", 1)             # dot product
    cmds.setAttr(dot + ".normalizeOutput", 0)
    for channel in "XYZ":
        cmds.connectAttr(quat + ".outputQuat" + channel,
                         dot + ".input1" + channel)
    cmds.setAttr(dot + ".input2", direction.x, direction.y, direction.z,
                 type="double3")

    # quatToEuler assumes a UNIT quaternion, and (v.a, 0, 0, w) is not one --
    # its euler X is atan2(2wx, 1 - 2x^2), which equals the twist only when
    # x^2 + w^2 == 1. Normalising first is what makes the angle exact.
    norm = cmds.createNode("quatNormalize", name=names["norm"],
                           skipSelect=True)
    cmds.connectAttr(dot + ".outputX", norm + ".inputQuatX")
    cmds.connectAttr(quat + ".outputQuatW", norm + ".inputQuatW")

    angle = cmds.createNode("quatToEuler", name=names["angle"],
                            skipSelect=True)
    cmds.setAttr(angle + ".inputRotateOrder", 0)    # XYZ: rx = 2*atan2(x, w)
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


def _spliced_conversions(nodes):
    """unitConversion nodes Maya spliced into our own wiring.

    Every place a unitless double meets an angle -- quatToEuler's output into
    a multDoubleLinear, and our sum into the joint's rotate channel -- Maya
    inserts one of these silently. They are ours as much as the nodes we
    created: left out of the manifest, one survives the bake still connected
    to the channel, and the channel is then driven by a node with no input
    and nothing can key it.
    """
    found = []
    for node in nodes:
        for other in cmds.listConnections(node, source=True, destination=True,
                                          type="unitConversion") or []:
            if other not in found and other not in nodes:
                found.append(other)
    return found


def _ensure_set(limb):
    """This character's twist manifest, created and tagged if absent."""
    return manifest.ensure(manifest.KIND_TWIST, limb)


def build(scene_map, limbs=None):
    """Build the twist networks. Returns (joints rigged, message).

    The pose this is called in is the twist ZERO: the driver local matrix is
    measured now and the channel keeps the value it holds now, so nothing
    moves at the build frame. Build in the bind pose -- and when a driver
    carries animation that actually moves, the message says so.

    Rebuilds: any network already recorded for the limbs asked for is baked
    and removed first, so a second press cannot double it.
    """
    manifest.activate(scene_map)
    wanted = list(LIMBS if limbs is None else limbs)
    table = manifest.records()
    standing = [limb for limb in wanted
                if manifest.members(manifest.KIND_TWIST, limb, table=table)]
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
        leaves = {}
        for path in children:
            leaves[naming.leaf(path)] = path
        joints = [leaves[name] for name in twist_joints(sorted(leaves))]
        if not joints:
            continue

        span = _world_point(tip) - _world_point(bone)
        length = span.length()
        if length < 1e-6:
            skipped.append("{0} (the bone has no length)".format(
                naming.leaf(bone)))
            continue
        along = span / length
        origin = _world_point(bone)
        positions = [(_world_point(j) - origin) * along / length
                     for j in joints]
        fractions = weights(joints, positions, segment.kind)
        local = _to_frame(along, _parent_of(driver))

        created = []
        driven = []
        for joint, weight in zip(joints, fractions):
            choice = axis_choice(_local_axes(joint), along,
                                 cmds.getAttr(joint + ".rotateOrder"))
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
            nodes = _network(joint, driver, weight * choice.sign, local)
            cmds.setAttr(nodes[-1] + ".input2", cmds.getAttr(plug))
            cmds.connectAttr(nodes[-1] + ".output", plug, force=True)
            created.extend(nodes + _spliced_conversions(nodes))
            driven.append((joint, "r" + choice.channel))
            rigged += 1
        if created:
            cmds.sets(created, addElement=_ensure_set(segment.limb))
            _record_plugs(segment.limb, driven)
        if not _is_constant(driver):
            animated.append(naming.leaf(driver))

    return rigged, _message_for(rigged, replaced, skipped, animated)


def _message_for(rigged, replaced, skipped, animated):
    if not rigged and not skipped:
        return "no twist joints on this skeleton"
    message = "{0} twist joint(s) rigged".format(rigged)
    if replaced:
        message += ", {0} replaced".format(replaced)
    if skipped:
        message += ". Skipped: " + "; ".join(skipped[:4])
    if animated:
        message += (". Twist zero is this pose - {0} carries animation"
                    .format(", ".join(sorted(set(animated))[:3])))
    return message


def collapses(values):
    """Whether a sampled channel is still enough to be a plain value.

    Without this, a rig on an unanimated skeleton leaves a key on every
    frame of every twist joint for nothing at all.
    """
    return not values or (max(values) - min(values)) <= 1e-9


def bake(limbs=None):
    """Bake the twist networks onto the joints and remove them.

    Sampled with `getAttr(time=...)` and keyed by hand rather than through
    `bakeResults`: the channel input is our own DG network, not a constraint,
    and this way the sampling, the disconnect and the keys are ours to order
    -- and the order is the whole trick. Sample every frame FIRST, then
    delete the network (which frees the channels), then write. Writing before
    the delete is impossible, the channel still has an input; deleting before
    sampling loses the values.

    Reads the playback range, never the time slider highlight, so it needs no
    highlight guard of its own.
    """
    table = manifest.records()
    wanted = [limb for limb in (LIMBS if limbs is None else limbs)
              if manifest.members(manifest.KIND_TWIST, limb, table=table)]
    if not wanted:
        return 0, "no twist rig to bake"

    start, end = overrig.frame_range()
    frames = [start + step for step in range(int(end - start) + 1)]

    baked = 0
    removed = 0
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        for limb in wanted:
            # Re-resolved per limb: the previous iteration's delete may
            # have taken a manifest with it (trap 18), which invalidates
            # any snapshot taken before the loop.
            set_name = twist_set(limb)
            plugs = [p for p in driven_plugs(limb) if cmds.objExists(p)]
            samples = {}
            for plug in plugs:
                samples[plug] = [cmds.getAttr(plug, time=frame)
                                 for frame in frames]

            members = [m for m in overrig.set_members(set_name)
                       if cmds.objExists(m)]
            if members:
                cmds.delete(members)
                removed += len(members)

            for plug, values in samples.items():
                if not cmds.objExists(plug.split(".")[0]):
                    continue
                if collapses(values):
                    if values:
                        cmds.setAttr(plug, values[0])
                else:
                    for frame, value in zip(frames, values):
                        cmds.setKeyframe(plug, time=frame, value=value)
                baked += 1

            # Maya deletes an objectSet together with its last member (trap
            # 18), so by now the set may be gone.
            if cmds.objExists(set_name):
                cmds.delete(set_name)
    finally:
        cmds.autoKeyframe(state=autokey)

    return baked, "{0} twist joint(s) baked, {1} node(s) removed".format(
        baked, removed)


def bake_all():
    """Bake every twist network in the scene."""
    return bake(built_limbs())
