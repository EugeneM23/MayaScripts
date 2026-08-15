"""Build OverRig setups on the skeleton the picker is bound to.

This module holds the policy -- which joints make up a limb, what gets
recorded, what a rebuild removes. All MEL knowledge lives in overrig.py.
"""

from collections import namedtuple

import maya.cmds as cmds

from maya_overrig import naming, overrig

BUILD_SET_PREFIX = "RigPicker_build_"

# Three joints per limb, in the order OverRig's IK proc requires:
# root, middle, end. Any other order produces a wrong chain.
#
# The spine deliberately uses the same 3-joint form on (pelvis, spine_03,
# spine_05): that keeps the rebike proc on the branch whose output is the
# three named controls -- <root>_IK_strech_gr (bottom), <middle>_IK_knee
# (centre), <end>_IK_feet (top). Selecting the whole spine instead would take
# the >3 "spider" branch, which builds per-vertebra twist controls -- a
# different tool. spine_01/02/04 keep their baked animation and ride on
# whichever driven joint is their ancestor.
LIMBS = (
    ("arm_l", ("upperarm_l", "lowerarm_l", "hand_l")),
    ("arm_r", ("upperarm_r", "lowerarm_r", "hand_r")),
    ("leg_l", ("thigh_l", "calf_l", "foot_l")),
    ("leg_r", ("thigh_r", "calf_r", "foot_r")),
    ("spine", ("pelvis", "spine_03", "spine_05")),
)

# What the default (hybrid) Build creates as IK. The spine stays FK until the
# user switches it -- part 4 of the request is explicit about the torso.
DEFAULT_IK = ("arm_l", "arm_r", "leg_l", "leg_r")

# How apply_rebike_3_or_more_object_to_IK names its three outputs, read
# verbatim from the MEL's rename lines. Role -> leaf-name mark.
IK_ROLES = {"end": "_IK_feet", "pole": "_IK_knee", "base": "_IK_strech_gr"}

BuildResult = namedtuple("BuildResult", "built skipped created removed message")


def limb_joints(scene_map):
    """Limbs whose joints all exist, as (limb name, [three long DAG paths]).

    `scene_map` is the picker's binding map, so prefixes and namespaces are
    already resolved by the time we get here.
    """
    resolved = []
    for name, joints in LIMBS:
        if all(joint in scene_map for joint in joints):
            resolved.append((name, [scene_map[joint] for joint in joints]))
    return resolved


def missing_limbs(scene_map):
    """Names of limbs that cannot be built because a joint is absent."""
    return [name for name, joints in LIMBS
            if not all(joint in scene_map for joint in joints)]


def limb_set(limb):
    """Name of the object set recording one limb's created nodes."""
    return BUILD_SET_PREFIX + limb


def ik_control(limb, role):
    """The IK control of a built limb for a role, through its manifest.

    Roles come from IK_ROLES: `end` is the control at the chain tip, `pole`
    the middle target, `base` the group at the chain root. Never found by
    bare scene name -- OverRig suffixes renames on collision, so the search
    space is the limb's own recorded nodes.
    """
    mark = IK_ROLES[role]
    for member in overrig.set_members(limb_set(limb)):
        if not cmds.objExists(member):
            continue
        if mark in member.split("|")[-1] and cmds.objectType(member) in (
                "transform", "joint"):
            return member
    return None


def resolve_limbs(nodes, limb_members, scene_map):
    """Which limbs the given nodes touch, in LIMBS order.

    A node counts for a limb when it is one of that limb's recorded nodes, a
    descendant of one, or one of the limb's three source joints. That last
    route is what lets the picker's own limb buttons drive a bake.

    Pure on purpose: `limb_members` is a {limb: [paths]} mapping supplied by
    the caller, so all of this is testable without Maya.
    """
    owner_of_joint = {}
    for name, joints in LIMBS:
        for joint in joints:
            path = scene_map.get(joint)
            if path:
                owner_of_joint[path] = name

    hit = set()
    for node in nodes:
        if node in owner_of_joint:
            hit.add(owner_of_joint[node])
            continue
        for name, members in limb_members.items():
            if any(node == m or node.startswith(m + "|") for m in members):
                hit.add(name)
                break

    return [name for name, _ in LIMBS if name in hit]


def built_limbs():
    """Limbs that currently have nodes recorded against them."""
    return [name for name, _ in LIMBS
            if overrig.set_members(limb_set(name))]


def limbs_in_selection(scene_map):
    """Limbs touched by the current Maya selection."""
    members = {name: overrig.set_members(limb_set(name))
               for name, _ in LIMBS}
    selected = cmds.ls(selection=True, long=True) or []
    return resolve_limbs(selected, members, scene_map)


def character_roots():
    """Skeleton roots that are characters, not rig helpers.

    Anything OverRig created is skipped. Its IK groups contain joints of their
    own, and without this a scene with a build in it reports a dozen skeletons
    instead of one, so the picker refuses to auto-connect.
    """
    return naming.find_skeleton_roots(
        exclude_under=overrig.set_members(overrig.KNOT_SET))


def top_level(path):
    """Outermost DAG ancestor of a path: '|a|b|c' -> '|a'."""
    return "|" + path.lstrip("|").split("|")[0]


def unrecorded_rig_roots(driver_paths, overrig_made):
    """Rig roots among the drivers' top-level ancestors that OverRig created.

    `overrig_made` is OverRig's own `OverRig_knots` membership, and it is what
    keeps this safe: a constraint the user set up by hand has no ancestor in
    that set, so it is never a candidate for deletion.
    """
    made = set(overrig_made)
    return sorted({top_level(path) for path in driver_paths} & made)


def _is_inside(path, container):
    """Whether `path` is a DAG descendant of `container`.

    The separator matters: `|foot_l_IK_feet_extra` is a different node, not a
    child of `|foot_l_IK_feet`.
    """
    return path.startswith(container + "|")


def order_by_nesting(limbs, limb_members):
    """Requested limbs plus any recorded limb nested inside them, innermost first.

    Animators park one control under another -- the hand's IK control hung off
    the foot's, so the arm follows the leg. Baking the outer limb destroys the
    inner limb's rig with it, and if the inner limb was not baked first its
    animation goes too.

    Pure: `limb_members` is a {limb: [paths]} mapping supplied by the caller.
    """
    contains = {name: set() for name in limb_members}
    for outer, outer_paths in limb_members.items():
        for inner, inner_paths in limb_members.items():
            if inner == outer:
                continue
            if any(_is_inside(path, container)
                   for container in outer_paths for path in inner_paths):
                contains[outer].add(inner)

    wanted = []
    frontier = list(limbs)
    while frontier:
        limb = frontier.pop(0)
        if limb in wanted:
            continue
        wanted.append(limb)
        frontier.extend(sorted(contains.get(limb, ())))

    ordered = []
    remaining = list(wanted)
    while remaining:
        free = [limb for limb in remaining
                if not (contains.get(limb, set()) & set(remaining))]
        if not free:
            # A DAG hierarchy cannot contain a cycle; bail out rather than loop.
            ordered.extend(remaining)
            break
        for limb in sorted(free):
            ordered.append(limb)
            remaining.remove(limb)
    return ordered


def foreign_knots_inside(rig_paths, our_paths, overrig_made):
    """OverRig knots sitting inside these rigs that belong to no recorded limb.

    Such a knot is a child of something we are about to delete, so leaving it
    alone is not physically available -- removing the parent takes it. Reporting
    it lets the caller refuse rather than destroy work the user built by hand.
    """
    ours = set(our_paths)
    found = set()
    for knot in overrig_made:
        if knot in ours:
            continue
        if any(_is_inside(knot, container) for container in rig_paths):
            found.add(knot)
    return sorted(found)


def _scene_nodes():
    return set(cmds.ls(long=True) or [])


def _recordable(node):
    """Whether a node that appeared during a build is ours to delete later.

    animCurves are excluded on purpose: baking transfers the animation into
    animCurves on the source joints, and those have to outlive the rig.
    Everything else OverRig conjures up -- the IK groups, the locators driving
    them, the constraint and blend nodes it leaves on the source joints -- is
    ours to clean up.

    The manifest cannot be built from OverRig's own `OverRig_knots` set: that
    records only the three renamed groups per limb, so the locators and the
    first layer of constraints are invisible to it. Baking a limb then left a
    live constraint behind, driven by a locator nothing knew about.
    """
    if not cmds.objExists(node):
        return False
    return not cmds.objectType(node).startswith("animCurve")


def _ensure_limb_set(limb):
    name = limb_set(limb)
    if not cmds.objExists(name):
        cmds.sets(name=name, empty=True)
    return name


def has_build():
    """True when this tool has anything recorded in the scene."""
    return bool(built_limbs())


def _rig_closure(seed_roots, overrig_made):
    """Grow seed rig roots into every OverRig root wired into the same setup.

    Walking out from a joint's constraints only reaches the part of the rig that
    drives the joint directly -- the `_IK_strech_gr` group. The `_IK_feet` and
    `_IK_knee` controls drive the IK handle instead, so they are never reached
    that way and would be left behind as stray locators.

    The walk only follows a node whose own top-level ancestor is something
    OverRig created, which is what stops it at the skeleton: the character's
    joints belong to no OverRig root, so it cannot cross through them into a
    neighbouring limb's rig.
    """
    made = set(overrig_made)
    found = set(seed_roots) & made
    frontier = list(found)

    while frontier:
        root = frontier.pop()
        for node in cmds.ls(root, dagObjects=True, long=True) or []:
            connected = cmds.listConnections(node, source=True,
                                             destination=True) or []
            for other in connected:
                paths = cmds.ls(other, long=True) or []
                if not paths:
                    continue
                candidate = top_level(paths[0])
                if candidate in made and candidate not in found:
                    found.add(candidate)
                    frontier.append(candidate)

    return sorted(found)


def _reclaim(joint_paths):
    """Free joints from an OverRig rig this tool never recorded.

    The manifest only covers builds made by the current code. A rig built by an
    older version, or one whose manifest set was lost, would otherwise keep the
    joints constrained forever with no way to remove it through the panel.

    Walking out from the limb's own joints bounds this: it can only ever reach a
    rig that actually drives this limb. Returns (nodes removed, names left
    alone).
    """
    made = overrig.set_members(overrig.KNOT_SET)

    doomed_roots = set()
    doomed_constraints = []
    foreign = []

    for path in joint_paths:
        if not cmds.objExists(path):
            continue
        for con in cmds.listRelatives(path, children=True, type="constraint",
                                      fullPath=True) or []:
            drivers = [t for t in
                       (cmds.listConnections(con + ".target", source=True,
                                             destination=False) or [])
                       if cmds.objExists(t)]
            drivers = [cmds.ls(t, long=True)[0] for t in set(drivers)]
            roots = unrecorded_rig_roots(drivers, made)
            if roots:
                doomed_roots.update(roots)
                doomed_constraints.append(con)
            else:
                foreign.append(con.split("|")[-1])

    # A joint's constraints only lead to the part of the rig driving it; expand
    # to the whole setup so its controls do not survive as stray locators.
    if doomed_roots:
        doomed_roots = set(_rig_closure(doomed_roots, made))

    alive_roots = [r for r in sorted(doomed_roots) if cmds.objExists(r)]
    if alive_roots:
        cmds.delete(alive_roots)

    # The constraint sits under the source joint, so it outlives its driver --
    # which is exactly what left joints "freed" but still constrained.
    alive_constraints = [c for c in doomed_constraints if cmds.objExists(c)]
    if alive_constraints:
        cmds.delete(alive_constraints)

    return len(alive_roots) + len(alive_constraints), foreign


def bake_limbs(scene_map, limbs):
    """Bake the given limbs back to FK and remove their OverRig setup.

    Uses OverRig's own selection-scoped primitives, so its structures come
    apart the way it expects. Limbs that were not asked for are never touched,
    and barn_fast_bake_source_obj_and_delete_knots() is never called -- that one
    is scene-global and would take the user's hand-made setups with it.
    """
    members_by_limb = {name: overrig.set_members(limb_set(name))
                       for name, _ in LIMBS}

    # A rig parked inside another must be baked before its container is
    # deleted, or its animation goes with the parent.
    limbs = order_by_nesting(limbs, members_by_limb)

    doomed = [path for limb in limbs for path in members_by_limb.get(limb, [])]
    ours = [path for paths in members_by_limb.values() for path in paths]
    intruders = foreign_knots_inside(doomed, ours,
                                     overrig.set_members(overrig.KNOT_SET))
    if intruders:
        return BuildResult(
            [], list(limbs), 0, 0,
            "Aborted - {0} holds OverRig node(s) we did not build: {1}. "
            "Move them out first.".format(
                ", ".join(limbs),
                ", ".join(n.split("|")[-1] for n in intruders[:4])))

    resolved = dict(limb_joints(scene_map))
    baked = []
    skipped = []
    removed = 0
    reclaimed = 0
    left_alone = []

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker bake")
    try:
        for limb in limbs:
            members = [m for m in overrig.set_members(limb_set(limb))
                       if cmds.objExists(m)]
            joints = [j for j in resolved.get(limb, []) if cmds.objExists(j)]
            if not members and not joints:
                skipped.append(limb)
                continue

            if joints:
                overrig.fast_bake(joints)
                overrig.delete_constraint_attributes(joints)
            if members:
                cmds.delete(members)
                removed += len(members)
            if cmds.objExists(limb_set(limb)):
                cmds.delete(limb_set(limb))

            # Anything still driving these joints was built outside our
            # bookkeeping -- an older version, or a manifest that got lost.
            if joints:
                extra, left = _reclaim(joints)
                reclaimed += extra
                left_alone.extend(left)

            baked.append(limb)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Baked {0} - {1} node(s) removed".format(
        ", ".join(baked) if baked else "nothing", removed)
    if reclaimed:
        message += ", {0} unrecorded".format(reclaimed)
    if skipped:
        message += ". Nothing recorded for: " + ", ".join(skipped)
    if left_alone:
        message += ". Left alone (not OverRig's): " + ", ".join(sorted(
            set(left_alone))[:4])
    return BuildResult(baked, skipped, 0, removed + reclaimed, message)


def teardown(scene_map):
    """Bake and remove every limb this tool built."""
    return bake_limbs(scene_map, built_limbs())


def build(scene_map, only=None):
    """Build IK on every resolvable limb, replacing any previous build.

    `only` restricts the build (and the replace pass) to the named limbs --
    the Switch feature converts one limb without touching the rest.
    """
    if not overrig.ensure_loaded():
        return BuildResult(
            [], [], 0, 0,
            "OverRig is not loaded - press the OverRig shelf button "
            "(looked for {0})".format(overrig.MEL_PATH))

    resolvable = limb_joints(scene_map)
    if only is not None:
        resolvable = [(name, joints) for name, joints in resolvable
                      if name in only]
    if not resolvable:
        return BuildResult([], [name for name, _ in LIMBS], 0, 0,
                           "No limb joints found on the bound skeleton")

    start, end = overrig.frame_range()
    warning = ""
    if end - start < 1:
        warning = "  (timeline is a single frame - nothing to bake over)"

    built = []
    created = []
    removed = 0

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker build")
    try:
        if only is not None:
            rebuilt = [l for l in only if l in built_limbs()]
            if rebuilt:
                removed = bake_limbs(scene_map, rebuilt).removed
        elif has_build():
            removed = teardown(scene_map).removed

        for name, joints in resolvable:
            before = _scene_nodes()
            overrig.build_ik(joints)
            after = _scene_nodes()

            fresh = sorted(n for n in (after - before) if _recordable(n))
            if fresh:
                cmds.sets(fresh, addElement=_ensure_limb_set(name))
                created.extend(fresh)
            built.append(name)
    finally:
        cmds.undoInfo(closeChunk=True)

    skipped = missing_limbs(scene_map)
    message = "Built {0} limb(s), {1} node(s) created".format(
        len(built), len(created))
    if removed:
        message += ", {0} replaced".format(removed)
    if skipped:
        message += ". Skipped: " + ", ".join(skipped)
    return BuildResult(built, skipped, len(created), removed, message + warning)
