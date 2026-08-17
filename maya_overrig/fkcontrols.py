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

import maya.cmds as cmds
import maya.mel as mel

from maya_overrig import bodymap, builder, overrig
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
from maya_overrig.fkalign import (  # noqa: F401 -- fkcontrols is the API
    merge_key_times, is_constant, orient_controllers, align_controllers,
    _euler_matrix, _ROTATE_CHANNELS)


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
