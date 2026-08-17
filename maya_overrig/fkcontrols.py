"""FK controllers on every animator bone, built through OverRig knots.

Each chain is run through OverRig's `apply_ForwHierarhy`, so the knots form a
real FK hierarchy within the chain and the bones' existing animation is baked
onto the controllers -- adjusting a ring adjusts the bone without losing the
motion that was already there. Chains are deliberately independent of each
other (the user's call): rotating the spine does not carry the arms, and any
specific coupling can be made with OverRig's own "parent inside".

Ring sizing comes from the skinned mesh rather than from bone length. On this
skeleton bone length is meaningless: `pelvis` measures 3.68 because its first
child sits on top of it, `lowerarm_l` measures 9.08 because its first child is a
twist joint, and `head` measures 0 for having no children at all.
"""

import contextlib
import math

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

from maya_overrig import axes, bodymap, builder, naming, overrig
from maya_overrig.fkchains import (  # noqa: F401 -- fkcontrols is the API
    FK_SET, FK_SET_PREFIX, SUFFIX, LIMB_CHAINS, SWITCHABLE, _finger_chains,
    CHAINS, HYBRID_FK_CHAINS, controller_name, chain_set, finger_chains_for,
    chain_root, chain_tip, chain_root_control, switchable_bones,
    innermost_owner, dependent_chains, limbs_riding_inside, attach_parent)
from maya_overrig.fkrings import (  # noqa: F401 -- fkcontrols is the API
    colour_for, rollup, apply_size_rules, stagger, radius_from, is_square,
    square_points, _skin_data, _parent_map, _vertex_buckets, _radius_for,
    _style_curve, _make_ring, _make_square, _final_radii, _bone_knot_map,
    _hide_native_shapes, _hide_rig_machinery, _dress_knots, _BORROW, _SCALE,
    _SQUARE)


def merge_key_times(per_channel):
    """Sorted union of key times across channels.

    All three rotate channels are rewritten together -- a value is only
    meaningful as part of a whole rotation -- so they need one shared list of
    times. `cmds.keyframe` returns None for an unkeyed channel.
    """
    times = set()
    for channel in per_channel:
        times.update(channel or ())
    return sorted(times)


def is_constant(values, tolerance=1e-6):
    """True when a baked curve never actually changes.

    A driver locator's rotation is the fixed offset between its knot and the
    bone it drives, so OverRig's bake writes the same value into every one of
    its keys (measured: spread 0.000000 over 62). Spotting that turns a
    per-key rewrite into one call per channel.
    """
    if not values:
        return True
    return (max(values) - min(values)) <= tolerance


# ---------------------------------------------------------------------------
# scene side
# ---------------------------------------------------------------------------

def chain_members(chain):
    """Long paths recorded against one chain, [] if none."""
    return overrig.set_members(chain_set(chain))


def built_fk_chains():
    """Chains that currently have nodes recorded against them."""
    return [name for name, _ in CHAINS if chain_members(name)]


def _legacy_members():
    return overrig.set_members(FK_SET)


def has_fk():
    """True when any FK is recorded — per-chain sets or the legacy flat one."""
    return bool(built_fk_chains() or _legacy_members())


def _ensure_chain_set(chain):
    name = chain_set(chain)
    if not cmds.objExists(name):
        cmds.sets(name=name, empty=True)
    return name


def _record_into(set_name, before):
    """Record (and visually mute) everything created since `before`.

    `before` is a UUID snapshot: re-parented nodes must NOT read as fresh,
    or a chain's manifest swallows another chain's controllers.
    """
    fresh = [n for n in builder._fresh_paths(before, builder._scene_nodes())
             if builder._recordable(n)]
    if fresh:
        cmds.sets(fresh, addElement=set_name)
        _hide_rig_machinery(fresh)
    return fresh


def _record_fresh(chain, before):
    """Record everything created since `before` against one FK chain."""
    return _record_into(_ensure_chain_set(chain), before)


_ROTATE_CHANNELS = ("rotateX", "rotateY", "rotateZ")
_TRANSLATE_CHANNELS = ("translateX", "translateY", "translateZ")


def _world_rotation(node):
    """A node's world rotation, translation dropped."""
    return axes._rotation_only(
        om.MMatrix(cmds.xform(node, query=True, worldSpace=True, matrix=True)))


def _euler_matrix(values, order=0):
    return om.MEulerRotation([math.radians(v) for v in values],
                             order).asMatrix()


def _local_total(node, rotate_values=None):
    """The local rotation the DAG consumes: rotateAxis * rotate * jointOrient.

    Working from the whole product rather than the rotate channel alone means
    a controller that already carries an orientation is handled correctly, and
    running the alignment twice changes nothing.
    """
    order = cmds.getAttr(node + ".rotateOrder")
    if rotate_values is None:
        rotate_values = cmds.getAttr(node + ".rotate")[0]
    return axes.total_rotation(
        _euler_matrix(cmds.getAttr(node + ".rotateAxis")[0]),
        _euler_matrix(rotate_values, order),
        _euler_matrix(cmds.getAttr(node + ".jointOrient")[0]))


@contextlib.contextmanager
def _unlocked(node, attr):
    """Unlock a rotation triple for the duration of a write, then re-lock it.

    OverRig locks `jointOrient` on its knots. Unlocking before anything is
    written means a refused write cannot leave a controller carrying half a
    change -- and half a change moves the bone.
    """
    locked = [plug for plug in
              ("{0}.{1}{2}".format(node, attr, axis) for axis in "XYZ")
              if cmds.getAttr(plug, lock=True)]
    for plug in locked:
        cmds.setAttr(plug, lock=False)
    try:
        yield
    finally:
        for plug in locked:
            cmds.setAttr(plug, lock=True)


def _plugs(node, attr):
    return ["{0}.{1}{2}".format(node, attr, axis) for axis in "XYZ"]


def _settable(node, attr):
    """True when a rotation triple can be written outright."""
    return not any(cmds.getAttr(plug, lock=True)
                   or cmds.listConnections(plug, source=True,
                                           destination=False)
                   for plug in _plugs(node, attr))


def _curves_on(node, attr):
    """{channel: animCurve} for a triple, or None when something else drives it.

    An empty mapping means the triple is plain static values.
    """
    curves = {}
    for axis in "XYZ":
        plug = "{0}.{1}{2}".format(node, attr, axis)
        if cmds.getAttr(plug, lock=True):
            return None
        sources = cmds.listConnections(plug, source=True,
                                       destination=False) or []
        animated = [s for s in sources
                    if cmds.objectType(s).startswith("animCurve")]
        if len(animated) != len(sources):
            return None  # driven by a constraint, an expression, a pairBlend
        if animated:
            curves[attr + axis] = animated[0]
    if curves and len(curves) != 3:
        return None  # half-keyed; no single value can stand in for a curve
    return curves


def _hold_still_by_orient(child, offset):
    """Writer that absorbs the correction into a child knot's jointOrient."""
    if any(cmds.listConnections(plug, source=True, destination=False)
           for plug in _plugs(child, "jointOrient")):
        return None
    current = cmds.getAttr(child + ".jointOrient")[0]
    held = axes.euler_degrees(
        axes.child_held_still(_euler_matrix(current), offset),
        previous=current)

    def write():
        with _unlocked(child, "jointOrient"):
            cmds.setAttr(child + ".jointOrient", *held)
    return write


def _rewrite_triple(node, channels, convert):
    """Writer putting `convert(values, previous)` on a triple, or None.

    Covers the three ways OverRig leaves a channel. Plain static values are
    set outright. A baked curve that never actually changes -- every driver
    locator, whose rotation is the fixed knot-to-bone offset -- is rewritten
    with one call per channel. A curve that really varies is walked key by
    key, nearest-solution, so nothing flips by 360 between two keys.
    """
    attr = channels[0][:-1]
    curves = _curves_on(node, attr)
    if curves is None:
        return None

    if not curves:
        held = convert(cmds.getAttr(node + "." + attr)[0], None)
        return lambda: cmds.setAttr(node + "." + attr, *held)

    per_channel = {name: cmds.keyframe(curve, query=True, valueChange=True)
                   or [] for name, curve in curves.items()}
    if all(is_constant(values) for values in per_channel.values()):
        held = convert([per_channel[name][0] for name in channels], None)

        def write_flat():
            for name, value in zip(channels, held):
                cmds.keyframe(node, attribute=name, valueChange=value,
                              absolute=True)
        return write_flat

    times = merge_key_times([
        cmds.keyframe(curve, query=True, timeChange=True)
        for curve in curves.values()])
    poses = []
    for time in times:
        values = [cmds.keyframe(node, attribute=name, query=True,
                                time=(time, time), valueChange=True)
                  for name in channels]
        if any(not v for v in values):
            return None  # a channel is missing this key
        poses.append((time, [v[0] for v in values]))

    retimed = []
    previous = None
    for time, values in poses:
        previous = convert(values, previous)
        retimed.append((time, previous))

    def write_keys():
        for time, values in retimed:
            for name, value in zip(channels, values):
                cmds.keyframe(node, attribute=name, time=(time, time),
                              valueChange=value, absolute=True)
    return write_keys


def _hold_still(child, offset):
    """Writer keeping `child` where it is while its knot turns, or None.

    Two corrections, and both are needed: the rotation keeps the child facing
    the same way, the translation keeps it in the same place. A child sits at
    an offset from its knot, so a turn swings it somewhere else entirely --
    correcting only the rotation moved bones by 21 cm in a live run.

    None means this child cannot be held still, and then the knot must not
    turn at all.
    """
    if cmds.attributeQuery("jointOrient", node=child, exists=True):
        turn = _hold_still_by_orient(child, offset)
    else:
        # The driver locator has no `jointOrient` to hide a correction in, so
        # the correction goes into its rotate -- which OverRig has baked.
        order = cmds.getAttr(child + ".rotateOrder")
        turn = _rewrite_triple(
            child, _ROTATE_CHANNELS,
            lambda values, previous: axes.euler_degrees(
                axes.child_held_still(_euler_matrix(values, order), offset),
                order, values if previous is None else previous))
    if turn is None:
        return None

    swing = _rewrite_triple(
        child, _TRANSLATE_CHANNELS,
        lambda values, _previous: axes.child_position_held_still(values,
                                                                 offset))
    if swing is None:
        return None

    def write():
        turn()
        swing()
    return write


# Degrees. A knot closer than this to its bone's frame is already there, which
# is what makes the step idempotent and what skips `root` and `pelvis`.
_ON_BONE = 1e-4


def _turn_onto_bone(ctrl, offset):
    """Turn one knot in place onto its bone's frame. True when changed.

    The knot's own frame is the only part of a controller an animator can
    read -- the rotate manipulator, the local rotation axes, the way a dragged
    handle turns -- and OverRig leaves it rolled about 90 degrees about the
    bone. `rotateAxis` carries the turn; every DAG child is counter-rotated so
    that the driver locator, and therefore the bone, does not move with it.

    Everything that can refuse is decided before anything is written: a knot
    turned with one child left behind drags the bone with it.
    """
    if axes.angle_of(offset) <= _ON_BONE:
        return False
    if not _settable(ctrl, "rotateAxis"):
        return False

    writers = []
    for child in cmds.listRelatives(ctrl, children=True, fullPath=True,
                                    type="transform") or []:
        # A constraint node parks under the object it constrains and never
        # reads its own transform. OverRig leaves a dead aimConstraint under
        # every knot it builds.
        if cmds.objectType(child).endswith("Constraint"):
            continue
        writer = _hold_still(child, offset)
        if writer is None:
            return False
        writers.append(writer)

    for writer in writers:
        writer()
    cmds.setAttr(ctrl + ".rotateAxis", *axes.euler_degrees(
        axes.axis_on_bone(_euler_matrix(cmds.getAttr(ctrl + ".rotateAxis")[0]),
                          offset)))
    return True


def orient_controllers(scene_map, only=None):
    """Turn every built FK controller onto its bone's frame. Bones do not move.

    The half of "on the bone's axes" that `align_controllers` cannot buy: it
    puts the rotate CHANNELS in the bone's axes but has to leave the knot's own
    frame where OverRig put it, about 90 degrees rolled about the bone (about
    180 on the right hand). This turns the knot itself, so what the animator
    grabs matches what the finger does.

    Every offset is measured before anything is written -- a knot's world is
    unchanged by its parent's turn, so the readings stay good, and no
    measurement can be taken from a half-written scene.
    """
    plan = []
    for chain_name, chain in CHAINS:
        if only is not None and chain_name not in only:
            continue
        for joint in chain:
            ctrl = controller_name(joint)
            bone = scene_map.get(joint)
            if not (cmds.objExists(ctrl) and bone and cmds.objExists(bone)):
                continue
            plan.append((ctrl, axes.frame_offset(_world_rotation(bone),
                                                 _world_rotation(ctrl))))

    turned = 0
    for ctrl, offset in plan:
        if _turn_onto_bone(ctrl, offset):
            turned += 1
    return turned


def _align_one(ctrl, bone):
    """Re-express one controller in its bone's axes. True when changed.

    `rotateAxis` takes the inverse of the knot-to-bone offset, `jointOrient`
    takes what the controller holds at the build pose, and every rotate key is
    conjugated into the new frame. The product the DAG consumes --
    rotateAxis * rotate * jointOrient -- is unchanged by construction, so
    nothing in the scene moves.
    """
    # A plain transform has no jointOrient, and rotateAxis alone cannot carry
    # the change: the leftover would have to vary with time. The `root`
    # controller is the only one -- built by apply_parentConstrAnim rather
    # than ForwHierarhy -- and being a lone centre control it has no mirror
    # partner to be symmetric with anyway.
    if not cmds.attributeQuery("jointOrient", node=ctrl, exists=True):
        return False

    offset = axes.frame_offset(_world_rotation(bone), _world_rotation(ctrl))
    reference = _local_total(ctrl)
    rotate_axis, joint_orient = axes.orient_values(offset, reference)
    order = cmds.getAttr(ctrl + ".rotateOrder")

    times = merge_key_times([
        cmds.keyframe(ctrl, attribute=attr, query=True, timeChange=True)
        for attr in _ROTATE_CHANNELS])

    # Read every key before writing any: the curves are the input.
    poses = []
    for time in times:
        values = [cmds.keyframe(ctrl, attribute=attr, query=True,
                                time=(time, time), valueChange=True)
                  for attr in _ROTATE_CHANNELS]
        if any(not v for v in values):
            return False  # a channel is missing this key; leave it alone
        poses.append((time, _local_total(ctrl, [v[0] for v in values])))

    retargeted = []
    previous = None
    for time, total in poses:
        previous = axes.euler_degrees(
            axes.retarget(total, offset, reference), order, previous)
        retargeted.append((time, previous))

    # OverRig locks jointOrient on its knots. Unlock before touching anything,
    # so a refused write cannot leave a controller carrying half the change --
    # a rotateAxis without its jointOrient moves the bone it drives.
    with _unlocked(ctrl, "jointOrient"):
        cmds.setAttr(ctrl + ".rotateAxis", *axes.euler_degrees(rotate_axis))
        cmds.setAttr(ctrl + ".jointOrient", *axes.euler_degrees(joint_orient))
        for time, values in retargeted:
            for attr, value in zip(_ROTATE_CHANNELS, values):
                cmds.keyframe(ctrl, attribute=attr, time=(time, time),
                              valueChange=value, absolute=True)
        if not times:
            cmds.setAttr(ctrl + ".rotate", *axes.euler_degrees(
                axes.retarget(reference, offset, reference), order))
    return True


def align_controllers(scene_map, only=None):
    """Re-express every built FK controller in its bone's axes. Nothing moves.

    Puts the controllers on the skeleton's own mirror convention, so a
    mirrored pose reads as equal channel values on both sides -- which is what
    Animbot's mirror and plain copy-paste between sides both need.

    Order does not matter: every input is read from world transforms this
    operation provably leaves alone.
    """
    aligned = 0
    for chain_name, chain in CHAINS:
        if only is not None and chain_name not in only:
            continue
        for joint in chain:
            ctrl = controller_name(joint)
            bone = scene_map.get(joint)
            if not (cmds.objExists(ctrl) and bone and cmds.objExists(bone)):
                continue
            if _align_one(ctrl, bone):
                aligned += 1
    return aligned


def _attach_chain(chain, scene_map, parent_of, targeted):
    """Hang one chain's root controller off its parent bone's controller.

    OverRig's apply_Parent_in does the heavy lifting: the child knot becomes a
    DAG child of the parent knot and its animation is re-baked into the new
    local space, so world motion is unchanged (verified: zero drift). Selection
    order is child first, parent last. Returns True when coupled.

    The chain starts at the first bone the skeleton HAS, so a rig without
    metacarpals still hangs its fingers off the hand.
    """
    first = chain_root(chain, scene_map)
    if first is None:
        return False
    parent = attach_parent(first, parent_of, targeted)
    if parent is None:
        return False
    child_ctrl = controller_name(first)
    parent_ctrl = controller_name(parent)
    if not (cmds.objExists(child_ctrl) and cmds.objExists(parent_ctrl)):
        return False
    overrig.parent_in(child_ctrl, parent_ctrl)
    return True


def _bake_fk_chains(scene_map, chains=None):
    """Bake FK chains back onto the bones and remove their nodes. No undo chunk.

    `chains=None` means everything recorded, including the legacy flat set.
    The requested list is expanded with chains nested inside it, order does not
    matter beyond that: bones are baked while the knots still drive, then every
    doomed node goes at once.
    """
    def read_manifests():
        """The recorded state, freshly resolved. Paths, so re-read after any
        re-parenting: a stale path deletes nothing and leaks a live rig."""
        members = {name: chain_members(name) for name, _ in CHAINS}
        if chains is None:
            return (members,
                    [name for name, _ in CHAINS if members[name]],
                    [m for m in _legacy_members() if cmds.objExists(m)])
        return members, [c for c in chains if members.get(c)], []

    members_by_chain, wanted, legacy = read_manifests()
    if not wanted and not legacy:
        return 0, []

    # IK limbs hang on the root controller. Anything about to be deleted that
    # contains one must let it go first: apply_Parent_out re-bakes the rig
    # into world space, so the limb keeps working and only its container
    # dies. Without this a Bake+Delete on root -- and the FK-first teardown
    # inside every full Build -- deletes four IK rigs unbaked.
    #
    # Lifting BEFORE the nesting expansion is what keeps the fingers alive: a
    # finger chain sits inside the root controller only by way of the IK hand,
    # and that hand survives. Expanding first would bake fingers the animator
    # never selected -- containment through a surviving rig is not ownership
    # (the same over-lift that once tore the fingers off a switching arm).
    doomed_preview = list(legacy)
    for c in wanted:
        doomed_preview.extend(members_by_chain[c])
    limb_members = {name: overrig.set_members(builder.limb_set(name))
                    for name, _ in builder.LIMBS}
    riding = limbs_riding_inside(limb_members, doomed_preview)
    for limb in riding:
        lift_ik_off_root(limb)
    if riding:
        # Every recorded path under a lifted rig just changed.
        members_by_chain, wanted, legacy = read_manifests()

    wanted = [c for c in builder.order_by_nesting(wanted, members_by_chain)
              if members_by_chain.get(c)]
    if not wanted and not legacy:
        return 0, []

    table = dict(CHAINS)
    if legacy:
        joints = [scene_map[j] for _, chain in CHAINS for j in chain
                  if j in scene_map and cmds.objExists(scene_map[j])]
    else:
        joints = [scene_map[j] for c in wanted for j in table[c]
                  if j in scene_map and cmds.objExists(scene_map[j])]
    constrained = [j for j in dict.fromkeys(joints)
                   if cmds.listRelatives(j, children=True, type="constraint")]
    if constrained:
        overrig.fast_bake(constrained)
        overrig.delete_constraint_attributes(constrained)

    doomed = list(legacy)
    for c in wanted:
        doomed.extend(members_by_chain[c])
    doomed = [d for d in doomed if cmds.objExists(d)]
    if doomed:
        cmds.delete(doomed)
    for c in wanted:
        if cmds.objExists(chain_set(c)):
            cmds.delete(chain_set(c))
    if legacy and cmds.objExists(FK_SET):
        cmds.delete(FK_SET)

    removed = len(doomed)
    if constrained:
        extra, _foreign = builder._reclaim(constrained)
        removed += extra
    return removed, wanted


def _mel_gate():
    """The refusal every MEL entry point shares, or None to proceed.

    Two guards in this order. The toolset must be in the session: without
    this the first Build of a fresh Maya threw "Cannot find procedure" out
    of the Qt slot, where nobody saw it, and the panel looked dead (trap
    20). And the time slider must not carry a multi-frame highlight:
    OverRig bakes across it before the playback range, so a capture or
    teardown bake under one silently clips to the highlighted frames and
    freezes the rest (trap 36).
    """
    if not overrig.ensure_loaded():
        return overrig.NOT_LOADED_MESSAGE
    selection = overrig.slider_selection()
    if selection:
        return overrig.slider_message(selection)
    return None


def bake_fk(scene_map, chains=None):
    """Bake FK back to the bones -- everything, or just the given chains."""
    message = _mel_gate()
    if message:
        return 0, message
    cmds.undoInfo(openChunk=True, chunkName="Rig Picker FK bake")
    try:
        removed, wanted = _bake_fk_chains(scene_map, chains)
    finally:
        cmds.undoInfo(closeChunk=True)
    what = ", ".join(wanted) if wanted else "FK"
    return removed, "{0} baked back - {1} node(s) removed".format(what, removed)


def build_fk(scene_map, only=None):
    """Build FK controllers through OverRig knots. Returns (count, message).

    `only` restricts the build to the named chains (used by Switch); None
    builds all 17. A previous build of the affected chains is baked back
    first. The caller guards against an existing IK build on the same bones.
    """
    if not any(j in scene_map for _, chain in CHAINS for j in chain):
        return 0, "Not connected to a skeleton"
    message = _mel_gate()
    if message:
        return 0, message

    region_of = {b.joint: b.region for b in bodymap.BUTTONS}
    parent_of = _parent_map()
    # Only bones this skeleton has can be an attach target: a chain hangs
    # from the nearest ancestor that gets a controller, and one that is
    # missing gets none.
    targeted = {j for _, chain in CHAINS for j in chain if j in scene_map}

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker FK")
    try:
        if only is None:
            replaced = _bake_fk_chains(scene_map)[0] if has_fk() else 0
        else:
            existing = [c for c in only if chain_members(c)]
            replaced = (_bake_fk_chains(scene_map, existing)[0]
                        if existing else 0)

        radii, guessed, skinned = _final_radii(scene_map)

        # Everything whose animation the capture can read must ride the
        # doubled time together: the whole skeleton, and any rig already
        # driving part of it (a restricted build runs while other chains'
        # rigs play). A chain captured against an unscaled parent records a
        # mixture of two timelines.
        scale_nodes = [p for p in scene_map.values() if cmds.objExists(p)]
        for name, _ in CHAINS:
            scale_nodes.extend(chain_members(name))
        scale_nodes.extend(_legacy_members())
        for name, _ in builder.LIMBS:
            scale_nodes.extend(overrig.set_members(builder.limb_set(name)))

        created = 0
        recorded = 0
        attached = 0
        with overrig.full_rate_capture(scale_nodes):
            for chain_name, chain in CHAINS:
                if only is not None and chain_name not in only:
                    continue
                paths = [scene_map[j] for j in chain
                         if j in scene_map and cmds.objExists(scene_map[j])]
                if not paths:
                    continue

                before = builder._scene_nodes()
                before_knots = set(overrig.set_members(overrig.KNOT_SET))

                cmds.select(paths, replace=True)
                with overrig.padded_range():
                    if len(paths) == 1:
                        mel.eval("apply_parentConstrAnim(1)")
                    else:
                        mel.eval("apply_ForwHierarhy(1)")

                fresh_knots = [k for k in
                               overrig.set_members(overrig.KNOT_SET)
                               if k not in before_knots]
                created += _dress_knots(fresh_knots, paths, radii, region_of)

                # Couple inside the same diff window so the coupling nodes
                # land in this chain's manifest -- and inside the doubled
                # time, so the re-bake reads one consistent timeline.
                # Parents precede children in CHAINS, so a full build always
                # finds its target; a restricted build couples only if the
                # target controller happens to exist.
                if _attach_chain(chain, scene_map, parent_of, targeted):
                    attached += 1

                recorded += len(_record_fresh(chain_name, before))

        # Last, once every chain is built and coupled: put the controllers on
        # the bones' axes. Two steps, and both are needed -- the first puts
        # the rotate CHANNELS in the bone's axes, the second turns the knot's
        # own frame onto the bone so the manipulator agrees with them. Neither
        # creates a node, so both stay out of the manifests.
        aligned = align_controllers(scene_map, only)
        turned = orient_controllers(scene_map, only)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Built {0} FK controller(s), {1} chain(s) coupled, " \
              "{2} node(s) recorded, {3} on bone axes, {4} frame(s) " \
              "turned".format(created, attached, recorded, aligned, turned)
    if replaced:
        message += ", previous FK baked back"
    if not skinned:
        message += " - no skinCluster, ring sizes are guesses"
    elif guessed:
        message += " - {0} ring(s) sized from neighbours".format(len(guessed))
    return created, message


def bake_targets(scene_map):
    """(ik_limbs, fk_chains) the current selection touches.

    One resolution across BOTH kinds of manifest, innermost owner winning:
    a hand controller inside the spine's controllers belongs to the arm, a
    finger controller inside the IK hand anchor belongs to the finger --
    never to everything on the way up. Bones resolve to whichever
    representation their chain currently has.
    """
    selected = cmds.ls(selection=True, long=True) or []

    candidates = []
    for name, _ in builder.LIMBS:
        for m in overrig.set_members(builder.limb_set(name)):
            candidates.append((m, "ik", name))
    for name, _ in CHAINS:
        for m in chain_members(name):
            candidates.append((m, "fk", name))

    bone_names = {}
    for name, chain in CHAINS:
        for joint in chain:
            path = scene_map.get(joint)
            if path:
                bone_names[path] = name
    built = set(builder.built_limbs())

    ik_hit = set()
    fk_hit = set()
    for node in selected:
        if node in bone_names:
            name = bone_names[node]
            if name in built:
                ik_hit.add(name)
            elif chain_members(name):
                fk_hit.add(name)
            continue
        owner = innermost_owner(node, candidates)
        if owner is None:
            continue
        (ik_hit if owner[0] == "ik" else fk_hit).add(owner[1])

    return ([name for name, _ in builder.LIMBS if name in ik_hit],
            [name for name, _ in CHAINS if name in fk_hit])


def bake_selection(scene_map, ik_limbs, fk_chains):
    """Bake exactly what the selection touches back to clean bones.

    Everything else in the scene stays rigged. An IK limb takes its riding
    FK chains (fingers on the hand anchor) down with it -- they cannot
    outlive their container, and they belong to the limb from the
    animator's point of view. The one exception is the pelvis controller
    riding an IK spine: the general pelvis control survives, re-hung on
    the root controller. FK chains bake per chain; _bake_fk_chains expands
    each to whatever rides inside it.
    """
    message = _mel_gate()
    if message:
        return message

    messages = []
    cmds.undoInfo(openChunk=True, chunkName="Rig Picker bake")
    try:
        for limb in ik_limbs:
            members = overrig.set_members(builder.limb_set(limb))
            root_ctrls = {}
            for chain_name, chain in CHAINS:
                ctrl = chain_root_control(chain, scene_map)
                paths = (cmds.ls(ctrl, long=True) or []) if ctrl else []
                root_ctrls[chain_name] = paths[0] if paths else None
            riders = dependent_chains(root_ctrls, members)
            riders = [c for c in riders if chain_members(c)]
            if riders:
                _bake_fk_chains(scene_map, riders)
                messages.append("{0} riders baked with {1}".format(
                    len(riders), limb))

        if ik_limbs:
            result = builder.bake_limbs(scene_map, ik_limbs)
            messages.append(result.message)

        remaining = [c for c in fk_chains if chain_members(c)]
        if remaining:
            removed, wanted = _bake_fk_chains(scene_map, remaining)
            messages.append("{0} baked back - {1} node(s) removed".format(
                ", ".join(wanted), removed))
    finally:
        cmds.undoInfo(closeChunk=True)
    return " | ".join(messages) if messages else "Nothing to bake"


def rebuild(scene_map, fk_limbs=False):
    """One Build entry point: tear down whatever exists, then build fresh.

    `fk_limbs=False` (the default) builds the hybrid rig -- IK arms and legs,
    FK everything else, finger chains hung on the IK hand controls.
    `fk_limbs=True` builds full FK on all 17 chains.

    FK is baked back before IK on purpose: finger controls can hang inside IK
    hand controls after a Switch, and the reverse order would delete them
    with the arm's rig before they were baked.
    """
    if not any(j in scene_map for _, chain in CHAINS for j in chain):
        return "Not connected to a skeleton"
    # Checked before the teardown, not just inside build_fk: Fast_Bake reads
    # the highlight too, and a teardown under one loses everything outside it.
    message = _mel_gate()
    if message:
        return message

    table = dict(CHAINS)
    messages = []
    cmds.undoInfo(openChunk=True, chunkName="Rig Picker build")
    try:
        if has_fk():
            removed, _ = _bake_fk_chains(scene_map)
            messages.append("FK baked back ({0} nodes)".format(removed))
        if builder.has_build():
            result = builder.bake_limbs(scene_map, builder.built_limbs())
            if result.message.startswith("Aborted"):
                # Something we did not build sits inside the old rig; refuse
                # to stack a new rig on top of a half-removed one.
                return result.message
            messages.append("IK baked back ({0} nodes)".format(result.removed))

        if fk_limbs:
            _count, message = build_fk(scene_map)
            messages.append(message)
        else:
            _count, message = build_fk(scene_map, only=HYBRID_FK_CHAINS)
            messages.append(message)
            result = builder.build(scene_map,
                                   only=list(builder.DEFAULT_IK))
            messages.append(result.message)

            # The IK rigs are anchored in world; hang them on the root
            # controller so the root carries the whole character.
            hung_ik = sum(hang_ik_on_root(limb) for limb in result.built)
            if hung_ik:
                messages.append(
                    "{0} IK group(s) on the root control".format(hung_ik))
            elif result.built and "root" not in scene_map:
                # Say it rather than leave it a mystery: with no root bone
                # there is no whole-character control to carry the IK, so it
                # stays anchored in world.
                messages.append("no root bone - IK limbs stay in world")

            # Fingers must follow the IK hands -- via the hand-bone anchor,
            # never the control: past full extension the control keeps
            # travelling while the bone stops, and fingers riding the
            # control tear off the hand.
            hung = 0
            for limb in ("arm_l", "arm_r"):
                target = (_limb_anchor(scene_map, limb)
                          or builder.ik_control(limb, "end"))
                if not target:
                    continue
                for chain in finger_chains_for(limb):
                    # The chain's own top controller, which on a skeleton
                    # without metacarpals is the one on <finger>_01_<side>.
                    ctrl = chain_root_control(table[chain], scene_map)
                    if (chain_members(chain) and ctrl
                            and cmds.objExists(ctrl)):
                        _parent_in(ctrl, target, _ensure_chain_set(chain))
                        hung += 1
            if hung:
                messages.append(
                    "{0} finger chain(s) on the IK hands".format(hung))
    finally:
        cmds.undoInfo(closeChunk=True)
    return " | ".join(messages)


# ---------------------------------------------------------------------------
# Switch FK/IK
# ---------------------------------------------------------------------------

def _parent_out(ctrl, set_name):
    """Lift a nested knot to world through OverRig, animation re-baked."""
    before = builder._scene_nodes()
    overrig.parent_out(ctrl)
    _record_into(set_name, before)


def _parent_in(child_ctrl, parent_ctrl, set_name):
    """Hang a knot inside another through OverRig, animation re-baked.

    Selection order is child first, parent last -- verified by experiment.
    """
    before = builder._scene_nodes()
    overrig.parent_in(child_ctrl, parent_ctrl)
    _record_into(set_name, before)


def _anchor_in(set_name, mark):
    """A named helper inside a manifest set, exact leaf match."""
    for member in overrig.set_members(set_name):
        if not cmds.objExists(member):
            continue
        leaf = member.split("|")[-1]
        if leaf == mark or (leaf.startswith(mark)
                            and leaf[len(mark):].isdigit()):
            return member
    return None


def _mute_anchor(loc):
    """Hide the anchor's SHAPE and keep its transform visible.

    Finger controllers are DAG children of this locator and visibility
    inherits down a transform: hiding the transform made every finger ring on
    an IK arm invisible in the viewport while the picker still selected it
    happily. Repairing on every lookup heals scenes rigged by the old code.
    """
    for plug, value in [(loc + ".visibility", 1)] + [
            (shape + ".visibility", 0) for shape in
            cmds.listRelatives(loc, shapes=True, fullPath=True) or []]:
        try:
            cmds.setAttr(plug, value)
        except RuntimeError:
            pass  # connected or locked display attr -- cosmetics, skip


def _limb_anchor(scene_map, limb):
    """What finger chains hang on: a locator riding the limb's end BONE.

    Never the IK control itself: past full extension the control keeps
    travelling while the bone stops, and fingers riding the control tear
    off the hand (measured live: hand-to-metacarpal 33 cm on a 40 cm
    overpull, rest 4.2 -- "the fingers stretch"). Created on demand,
    recorded into the limb's manifest, parented under the IK end control
    so it lives and dies with the rig.
    """
    mark = limb + "_IK_anchor"
    existing = _anchor_in(builder.limb_set(limb), mark)
    if existing:
        _mute_anchor(existing)
        return existing
    ctrl = builder.ik_control(limb, "end")
    end_bone = scene_map.get(dict(builder.LIMBS)[limb][-1])
    if not (ctrl and end_bone and cmds.objExists(end_bone)):
        return None
    loc = cmds.spaceLocator(name=mark)[0]
    cmds.xform(loc, worldSpace=True, translation=cmds.xform(
        end_bone, query=True, worldSpace=True, translation=True))
    loc = cmds.parent(loc, ctrl)[0]
    cmds.parentConstraint(end_bone, loc, maintainOffset=True)
    _mute_anchor(loc)
    cmds.sets(loc, addElement=builder.limb_set(limb))
    return cmds.ls(loc, long=True)[0]


# The three groups apply_rebike_3_or_more_object_to_IK leaves at world root.
IK_TOP_ROLES = ("base", "pole", "end")


def hang_ik_on_root(limb):
    """Hang a limb's three IK top groups under the root controller.

    All three, machinery included. Measured on a live build: the IK rig is
    anchored in world end to end -- moving the root BONE moved neither the
    controls nor the upperarm bone. Parenting only the two animator controls
    would carry the effector targets while the chain base stayed pinned, and
    the shoulder tears off the body.

    apply_Parent_in re-bakes the animation into the new local space, so
    nothing moves. Fresh nodes go into the LIMB manifest: the coupling lives
    and dies with the IK rig, not with the root chain.

    Returns the number of groups moved. Zero when there is no root controller
    -- IK built by Switch after a full bake stays in world, and the next
    Build re-hangs it.
    """
    root_ctrl = controller_name("root")
    if not cmds.objExists(root_ctrl):
        return 0
    root_path = cmds.ls(root_ctrl, long=True)[0]
    hung = 0
    for role in IK_TOP_ROLES:
        node = builder.ik_control(limb, role)
        if not node or not cmds.objExists(node):
            continue
        if builder._is_inside(cmds.ls(node, long=True)[0], root_path):
            continue  # already there; the operation is idempotent
        _parent_in(node, root_ctrl, builder._ensure_limb_set(limb))
        hung += 1
    return hung


def lift_ik_off_root(limb):
    """Lift a limb's IK top groups back to world, animation re-baked.

    Run before whatever they hang inside is deleted: the rig keeps working
    and only its container dies.
    """
    lifted = 0
    for role in IK_TOP_ROLES:
        node = builder.ik_control(limb, role)
        if not node or not cmds.objExists(node):
            continue
        if not cmds.listRelatives(node, parent=True):
            continue  # already in world
        _parent_out(node, builder._ensure_limb_set(limb))
        lifted += 1
    return lifted


def hang_ik_end_on(limb, target):
    """Hang a limb's IK end group on `target`, animation re-baked.

    The end group is where the animator's hand control lives, and it is the
    only one that rides a prop: the pole keeps answering to the body, and
    hanging the chain base on a prop pins the shoulder to it.

    A knot that already has a parent -- and after a build every IK group hangs
    on the root controller -- is lifted to world first. Re-parenting one in
    place is not a path this repo has measured; lift-then-hang is what
    `switch_limbs` already does with its rider chains.
    """
    node = builder.ik_control(limb, "end")
    if not node or not cmds.objExists(node):
        return False

    target_path = cmds.ls(target, long=True)[0]
    if builder._is_inside(cmds.ls(node, long=True)[0], target_path):
        return False  # already there; the operation is idempotent

    set_name = builder._ensure_limb_set(limb)
    if cmds.listRelatives(node, parent=True, fullPath=True):
        _parent_out(node, set_name)
        # The path moved, and set_members resolves paths at call time.
        node = builder.ik_control(limb, "end")
        if not node or not cmds.objExists(node):
            return False
    _parent_in(node, target_path, set_name)
    return True


def lift_ik_end(limb):
    """Lift a limb's IK end group back to world, animation re-baked."""
    node = builder.ik_control(limb, "end")
    if not node or not cmds.objExists(node):
        return False
    if not cmds.listRelatives(node, parent=True, fullPath=True):
        return False
    _parent_out(node, builder._ensure_limb_set(limb))
    return True


def _rehang_riders(scene_map, limb, riders, now_ik):
    """Hang lifted rider chains back onto whatever the limb offers now.

    Used both by the normal switch tail and by the abort path -- a refused
    bake must not leave the riders parked in world.
    """
    table = dict(CHAINS)
    if now_ik:
        target = _limb_anchor(scene_map, limb) or builder.ik_control(limb, "end")
    else:
        tip = chain_tip(table[limb], scene_map)
        target = controller_name(tip) if tip else None
    for chain in riders:
        ctrl = chain_root_control(table[chain], scene_map)
        if (target and ctrl and cmds.objExists(ctrl)
                and cmds.objExists(target)):
            _parent_in(ctrl, target, _ensure_chain_set(chain))


def switch_limbs(scene_map, limbs):
    """Convert each limb to the opposite rig type, animation re-baked.

    FK becomes IK, IK becomes FK. Fingers riding on an arm's hand are lifted to
    world before the arm converts and hung back on the new hand control after
    -- they are DAG children of what gets deleted, so anything less loses them.
    """
    message = _mel_gate()
    if message:
        return [], list(limbs), message

    table = dict(CHAINS)
    done = []
    skipped = []
    notes = []

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker switch")
    try:
        for limb in limbs:
            if limb not in SWITCHABLE:
                skipped.append(limb)
                continue
            is_ik = limb in builder.built_limbs()
            is_fk = bool(chain_members(limb))
            if not is_ik and not is_fk:
                # Nothing on the chain yet: the first Switch press builds
                # its IK; the next press converts to FK as usual.
                builder.build(scene_map, only=[limb])
                hang_ik_on_root(limb)
                done.append(limb + " -> IK (built)")
                continue

            riders = [c for c in finger_chains_for(limb)
                      if chain_members(c)]
            for chain in riders:
                ctrl = chain_root_control(table[chain], scene_map)
                if ctrl and cmds.objExists(ctrl):
                    _parent_out(ctrl, _ensure_chain_set(chain))

            if is_fk:
                _bake_fk_chains(scene_map, [limb])
                builder.build(scene_map, only=[limb])
                hang_ik_on_root(limb)
                done.append(limb + " -> IK")
                now_ik = True
            else:
                bake = builder.bake_limbs(scene_map, [limb])
                if bake.message.startswith("Aborted"):
                    # Building FK over a live IK is exactly how "leftover
                    # IK pieces" happen. Refuse the limb, surface the
                    # reason, and put the riders back where they were.
                    skipped.append(limb)
                    notes.append(bake.message)
                    _rehang_riders(scene_map, limb, riders, now_ik=True)
                    continue
                _count, build_message = build_fk(scene_map, only=[limb])
                if "0 chain(s) coupled" in build_message:
                    notes.append(limb + " uncoupled (no parent control)")
                done.append(limb + " -> FK")
                now_ik = False

            _rehang_riders(scene_map, limb, riders, now_ik=now_ik)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Switched: " + ", ".join(done) if done else "Nothing to switch"
    if skipped:
        message += ". No rig on: " + ", ".join(skipped)
    if notes:
        message += ". " + "; ".join(notes)
    return done, skipped, message
