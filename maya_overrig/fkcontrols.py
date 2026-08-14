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
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

from maya_overrig import bodymap, builder, naming, overrig

FK_SET = "RigPicker_fk"
SUFFIX = "_FK_ctrl"


def _finger_chains():
    chains = []
    for side in ("l", "r"):
        for finger in ("index", "middle", "ring", "pinky"):
            joints = tuple(["{0}_metacarpal_{1}".format(finger, side)]
                           + ["{0}_{1:02d}_{2}".format(finger, i, side)
                              for i in (1, 2, 3)])
            chains.append(("{0}_{1}".format(finger, side), joints))
        chains.append(("thumb_" + side,
                       tuple("thumb_{0:02d}_{1}".format(i, side)
                             for i in (1, 2, 3))))
    return chains


# Selection order for apply_ForwHierarhy IS the chain order, root first.
# Chains are independent of each other on purpose.
CHAINS = tuple([
    ("root", ("root",)),
    ("spine", ("pelvis", "spine_01", "spine_02", "spine_03",
               "spine_04", "spine_05")),
    ("neck", ("neck_01", "neck_02", "head")),
    ("arm_l", ("clavicle_l", "upperarm_l", "lowerarm_l", "hand_l")),
    ("arm_r", ("clavicle_r", "upperarm_r", "lowerarm_r", "hand_r")),
    ("leg_l", ("thigh_l", "calf_l", "foot_l", "ball_l")),
    ("leg_r", ("thigh_r", "calf_r", "foot_r", "ball_r")),
] + _finger_chains())

# Rigging convention, matching the picker so the two share one language.
_LEFT = (0.25, 0.55, 1.0)
_RIGHT = (1.0, 0.30, 0.30)
_CENTRE = (1.0, 0.85, 0.25)

_REGION_COLOURS = {
    "root": _CENTRE, "spine": _CENTRE, "head": _CENTRE,
    "arm_l": _LEFT, "leg_l": _LEFT, "hand_l": _LEFT,
    "arm_r": _RIGHT, "leg_r": _RIGHT, "hand_r": _RIGHT,
}

_DOMINANT_FLOOR = 0.2   # weight a vertex needs before it counts for anyone
_SHARED_FLOOR = 0.08    # second pass, for joints that never dominate
_SECTIONS = 16
_LINE_WIDTH = 2.0


def controller_name(joint):
    """Name of the controller for a joint."""
    return joint + SUFFIX


def colour_for(region):
    """RGB for a body region, by side."""
    return _REGION_COLOURS[region]


def attach_parent(chain_first, parent_of, targeted):
    """The bone whose controller a chain should hang from.

    Walks up from the chain's first bone to the nearest ancestor that carries a
    controller: clavicle_l -> spine_05, thigh_l -> pelvis, index_metacarpal_l
    -> hand_l, pelvis -> root. Returns None at the top (root stays in world).

    Pure -- `parent_of` is a plain {joint: parent} mapping.
    """
    node = parent_of.get(chain_first)
    seen = set()
    while node is not None and node not in seen:
        if node in targeted:
            return node
        seen.add(node)
        node = parent_of.get(node)
    return None


def rollup(influences, targets, parent_of):
    """Map each influence to the nearest ancestor that gets a controller.

    Driven joints have to be attributed to the bone they follow, or the bone
    collects nothing: `upperarm_l` and `thigh_l` split their weight with their
    twist joints and never dominate a single vertex on their own.

    Pure -- `parent_of` is a plain {joint: parent} mapping.
    """
    owner = {}
    for influence in influences:
        node = influence
        seen = set()
        while node is not None and node not in seen:
            seen.add(node)
            if node in targets:
                break
            node = parent_of.get(node)
        owner[influence] = node if node in targets else None
    return owner


# Joints the measurement gets wrong, and what to do about them.
#
# spine_05 loses every vertex to the clavicles and spine_03, measuring about 4
# in a chest that is 16 across, which buries its ring inside the geometry. It
# borrows its neighbour's size instead, slightly larger so it stays visible.
_BORROW = {"spine_05": ("spine_04", 1.05)}

# The feet measure their length rather than their girth: the bone axis runs
# along the foot, so the perpendicular spread picks up the whole sole.
_SCALE = {"foot_l": 0.5, "foot_r": 0.5}


def apply_size_rules(radii):
    """Correct the radii the skin measurement gets wrong.

    Pure: takes and returns a {joint: radius} mapping. Borrowing happens before
    scaling, and a joint borrows from the measured value, not a corrected one,
    so the rules cannot chain into each other.
    """
    corrected = dict(radii)
    for joint, (source, factor) in _BORROW.items():
        if joint in corrected and radii.get(source):
            corrected[joint] = radii[source] * factor
    for joint, factor in _SCALE.items():
        if joint in corrected:
            corrected[joint] *= factor
    return corrected


def stagger(index):
    """Alternating size factor for rings along a chain.

    Torso segments genuinely are the same width, so their rings come out the
    same size and stack into one indistinguishable tube. Nudging every other one
    inward makes them read as nested rings instead.
    """
    return 1.0 if index % 2 == 0 else 0.88


def radius_from(distances, percentile=0.75, margin=1.1):
    """Ring radius for a spread of perpendicular distances.

    A percentile rather than the maximum, so one stray vertex on a seam does not
    inflate the ring; a margin so it clears the surface instead of grazing it.
    """
    if not distances:
        return 0.0
    ordered = sorted(distances)
    index = min(int(len(ordered) * percentile), len(ordered) - 1)
    return ordered[index] * margin


# ---------------------------------------------------------------------------
# scene side
# ---------------------------------------------------------------------------

def _world_position(node):
    return om.MVector(*cmds.xform(node, query=True, worldSpace=True,
                                  translation=True))


def _bone_axis(node):
    """The joint's local X in world space -- it runs along the bone here."""
    matrix = om.MMatrix(cmds.xform(node, query=True, worldSpace=True,
                                   matrix=True))
    return om.MVector(matrix[0], matrix[1], matrix[2]).normal()


def _skin_data(skin):
    """Influence names, flat weights, influence count and world points."""
    selection = om.MSelectionList()
    selection.add(skin)
    fn_skin = oma.MFnSkinCluster(selection.getDependNode(0))

    shape = cmds.skinCluster(skin, query=True, geometry=True)[0]
    mesh_selection = om.MSelectionList()
    mesh_selection.add(shape)
    dag = mesh_selection.getDagPath(0)

    fn_mesh = om.MFnMesh(dag)
    component_fn = om.MFnSingleIndexedComponent()
    component = component_fn.create(om.MFn.kMeshVertComponent)
    component_fn.setCompleteData(fn_mesh.numVertices)

    weights, influence_count = fn_skin.getWeights(dag, component)
    names = [path.partialPathName().split(":")[-1]
             for path in fn_skin.influenceObjects()]
    return names, weights, influence_count, fn_mesh.getPoints(om.MSpace.kWorld)


def _parent_map():
    parent_of = {}
    for joint in cmds.ls(type="joint", long=True) or []:
        short = joint.split("|")[-1].split(":")[-1]
        parents = cmds.listRelatives(joint, parent=True, type="joint") or []
        parent_of[short] = (parents[0].split(":")[-1] if parents else None)
    return parent_of


def _vertex_buckets(targets):
    """World points grouped by the target joint they mostly belong to.

    Two passes: the first assigns each vertex to whichever target owns most of
    its weight; the second picks up joints that never won -- thin spine and neck
    segments lose every vertex to fatter neighbours.
    """
    parent_of = _parent_map()
    dominant = {}
    shared = {}

    for skin in cmds.ls(type="skinCluster") or []:
        names, weights, count, points = _skin_data(skin)
        owner = rollup(names, targets, parent_of)
        owners = [owner.get(name) for name in names]

        for vertex in range(len(points)):
            base = vertex * count
            totals = {}
            for index in range(count):
                weight = weights[base + index]
                if weight <= 0.0 or owners[index] is None:
                    continue
                totals[owners[index]] = totals.get(owners[index], 0.0) + weight
            if not totals:
                continue

            point = om.MVector(points[vertex].x, points[vertex].y,
                               points[vertex].z)
            best = max(totals, key=totals.get)
            if totals[best] >= _DOMINANT_FLOOR:
                dominant.setdefault(best, []).append(point)
            for joint, total in totals.items():
                if total >= _SHARED_FLOOR:
                    shared.setdefault(joint, []).append(point)

    return dominant, shared


def _radius_for(joint, joint_path, dominant, shared, floor):
    """Ring radius for a joint.

    `joint` is the bare name the vertex buckets are keyed by; `joint_path` is
    the DAG path to query. Passing the path where the name belongs silently
    finds nothing and sends every joint to the fallback size.
    """
    for source in (dominant, shared):
        points = source.get(joint)
        if not points:
            continue
        origin = _world_position(joint_path)
        axis = _bone_axis(joint_path)
        spread = []
        for point in points:
            relative = point - origin
            spread.append((relative - axis * (relative * axis)).length())
        radius = radius_from(spread)
        if radius >= floor:
            return radius
    return None


def _make_ring(name, radius, normal, colour):
    ring = cmds.circle(name=name, normal=normal, radius=radius,
                       sections=_SECTIONS, constructionHistory=False)[0]
    shape = cmds.listRelatives(ring, shapes=True, fullPath=True)[0]
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *colour)
    if cmds.attributeQuery("lineWidth", node=shape, exists=True):
        cmds.setAttr(shape + ".lineWidth", _LINE_WIDTH)
    return ring


def has_fk():
    """True when FK markers are recorded in the scene."""
    return bool(cmds.objExists(FK_SET) and cmds.sets(FK_SET, query=True))


def remove_fk():
    """Delete the markers and their set. Returns how many went."""
    if not cmds.objExists(FK_SET):
        return 0
    members = [m for m in (cmds.ls(cmds.sets(FK_SET, query=True) or [],
                                   long=True) or []) if cmds.objExists(m)]
    if members:
        cmds.delete(members)
    if cmds.objExists(FK_SET):
        cmds.delete(FK_SET)
    return len(members)


def _final_radii(scene_map):
    """One {joint: ring radius} map for every buildable bone.

    Everything is measured before anything is built: the correction rules let
    one joint borrow another's size, and the stagger walks the body-map order.
    """
    buildable = [b for b in bodymap.BUTTONS
                 if b.joint in scene_map and cmds.objExists(scene_map[b.joint])]
    targets = {b.joint for b in buildable}

    skinned = bool(cmds.ls(type="skinCluster"))
    dominant, shared = _vertex_buckets(targets) if skinned else ({}, {})

    # Character height from the spread of the joints themselves. A bounding
    # box of one joint gives a box of nothing.
    heights = [_world_position(scene_map[b.joint]).y for b in buildable]
    height = max(max(heights) - min(heights), 1.0) if heights else 1.0
    floor = height * 0.004

    radii = {}
    guessed = []
    for button in buildable:
        radius = _radius_for(button.joint, scene_map[button.joint],
                             dominant, shared, floor)
        if radius is None:
            radius = floor * 6.0
            guessed.append(button.joint)
        radii[button.joint] = radius
    radii = apply_size_rules(radii)

    seen_in_region = {}
    for button in buildable:
        index = seen_in_region.get(button.region, 0)
        seen_in_region[button.region] = index + 1
        if button.region in ("spine", "head"):
            radii[button.joint] *= stagger(index)

    if "root" in radii:
        radii["root"] = max(radii["root"], height * 0.16)
    return radii, guessed, skinned


def _bone_knot_map(chain_paths, fresh_knots):
    """Map each chain bone to the fresh knot that drives it.

    Read from the bone side: constraint -> driver -> up the driver's ancestors
    until a fresh knot is hit. A ForwHierarhy knot drives its bone through a
    child locator (`joint2 -> locator8 -> parentConstraint -> spine_01`), while
    a single parentConstrAnim knot drives directly -- the ancestor walk covers
    both. Never map by name or creation order: OverRig names knots `joint1..N`
    and suffixes on collision.
    """
    knots = set(fresh_knots)
    mapping = {}
    for bone in chain_paths:
        found = None
        for con in cmds.listRelatives(bone, children=True, type="constraint",
                                      fullPath=True) or []:
            for driver in cmds.listConnections(con + ".target", source=True,
                                               destination=False) or []:
                if cmds.objectType(driver).endswith("Constraint"):
                    continue
                paths = cmds.ls(driver, long=True) or []
                node = paths[0] if paths else None
                while node:
                    if node in knots:
                        found = node
                        break
                    trimmed = node.rsplit("|", 1)[0]
                    node = trimmed if trimmed else None
                if found:
                    break
            if found:
                break
        if found:
            mapping[bone] = found
    return mapping


def _hide_native_shapes(knot):
    """Hide what the knot draws on its own; only our ring should show."""
    if cmds.objectType(knot) == "joint":
        cmds.setAttr(knot + ".drawStyle", 2)
    for shape in cmds.listRelatives(knot, shapes=True, fullPath=True) or []:
        if cmds.objectType(shape) != "nurbsCurve":
            cmds.setAttr(shape + ".visibility", 0)


def _hide_rig_machinery(nodes):
    """Hide the ForwHierarhy internals -- driver and attach locators, helper
    joints -- so only the rings show. Display-only; nothing is disconnected.

    Without this, 64 bones' worth of machinery locators drown the rings in
    cyan crosses, worst around the hands.
    """
    for node in nodes:
        if not cmds.objExists(node):
            continue
        node_type = cmds.objectType(node)
        try:
            if node_type == "joint":
                cmds.setAttr(node + ".drawStyle", 2)
            elif node_type == "locator":
                cmds.setAttr(node + ".visibility", 0)
        except RuntimeError:
            pass  # connected or locked display attr -- cosmetics, skip


def _dress_knots(knot_paths, chain_paths, radii, region_of):
    """Rename fresh knots to <bone>_FK_ctrl and put our ring shapes on them.

    Works through UUIDs: renaming a chain parent changes every descendant's
    path, so each knot's path is re-resolved just before its own rename.
    """
    by_bone = _bone_knot_map(chain_paths, knot_paths)
    # UUIDs for every mapped knot BEFORE any rename: renaming the chain root
    # invalidates the stored paths of every knot beneath it.
    uuid_by_bone = {bone: naming.uuid_of(knot)
                    for bone, knot in by_bone.items()}
    dressed = 0
    for bone, uuid in sorted(uuid_by_bone.items()):
        knot = naming.path_from_uuid(uuid)
        if not knot:
            continue
        bare = naming.leaf(bone)

        knot = cmds.ls(cmds.rename(knot, controller_name(bare)), long=True)[0]
        _hide_native_shapes(knot)

        if bare == "root":
            # The ring must lie flat on the ground whatever the knot's own
            # axes are: transform world-up into the knot's local space.
            inverse = om.MMatrix(cmds.xform(knot, query=True, worldSpace=True,
                                            matrix=True)).inverse()
            up = om.MVector(0, 1, 0) * inverse
            normal = (up.x, up.y, up.z)
        else:
            normal = (1, 0, 0)
        ring = _make_ring(bare + "_FK_ring_tmp", radii.get(bare, 1.0), normal,
                          colour_for(region_of[bare]))
        shape = cmds.listRelatives(ring, shapes=True, fullPath=True)[0]
        cmds.parent(shape, knot, relative=True, shape=True)
        cmds.delete(ring)
        dressed += 1
    return dressed


def _attach_chains(scene_map):
    """Hang every chain's root controller off its parent bone's controller.

    OverRig's apply_Parent_in does the heavy lifting: the child knot becomes a
    DAG child of the parent knot and its animation is re-baked into the new
    local space, so world motion is unchanged (verified: zero drift). Selection
    order is child first, parent last.

    Without this the chains are independent world-space knots, and moving the
    pelvis tears the skeleton apart at every chain boundary.
    """
    parent_of = _parent_map()
    targeted = {j for _, chain in CHAINS for j in chain}
    attached = 0
    for _chain_name, chain in CHAINS:
        first = chain[0]
        parent = attach_parent(first, parent_of, targeted)
        if parent is None:
            continue
        child_ctrl = controller_name(first)
        parent_ctrl = controller_name(parent)
        if not (cmds.objExists(child_ctrl) and cmds.objExists(parent_ctrl)):
            continue
        cmds.select([child_ctrl, parent_ctrl], replace=True)
        mel.eval("apply_Parent_in()")
        attached += 1
    return attached


def _teardown_fk(scene_map):
    """Bake the FK back onto the bones and remove every trace of it.

    Order matters: bake while the knots still drive, then delete. The reclaim
    pass at the end is a safety net for anything the manifest diff missed.
    """
    joints = [scene_map[j] for _, chain in CHAINS for j in chain
              if j in scene_map and cmds.objExists(scene_map[j])]
    constrained = [j for j in joints
                   if cmds.listRelatives(j, children=True, type="constraint")]
    if constrained:
        overrig.fast_bake(constrained)
        overrig.delete_constraint_attributes(constrained)

    removed = remove_fk()
    if constrained:
        extra, _foreign = builder._reclaim(constrained)
        removed += extra
    return removed


def bake_fk(scene_map):
    """Bake the whole FK build back to the bones. Returns (removed, message)."""
    cmds.undoInfo(openChunk=True, chunkName="Rig Picker FK bake")
    try:
        removed = _teardown_fk(scene_map)
    finally:
        cmds.undoInfo(closeChunk=True)
    return removed, "FK baked back - {0} node(s) removed".format(removed)


def build_fk(scene_map):
    """Build FK controllers through OverRig knots. Returns (count, message).

    The caller guards against an existing IK build; this function assumes the
    bones are free apart from a previous FK, which it bakes back first.
    """
    if not any(j in scene_map for _, chain in CHAINS for j in chain):
        return 0, "Not connected to a skeleton"

    region_of = {b.joint: b.region for b in bodymap.BUTTONS}

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker FK")
    try:
        replaced = _teardown_fk(scene_map) if has_fk() else 0

        radii, guessed, skinned = _final_radii(scene_map)

        created = 0
        recorded = []
        for _chain_name, chain in CHAINS:
            paths = [scene_map[j] for j in chain
                     if j in scene_map and cmds.objExists(scene_map[j])]
            if not paths:
                continue

            before = builder._scene_nodes()
            before_knots = set(overrig.set_members(overrig.KNOT_SET))

            cmds.select(paths, replace=True)
            if len(paths) == 1:
                mel.eval("apply_parentConstrAnim(1)")
            else:
                mel.eval("apply_ForwHierarhy(1)")

            fresh_knots = [k for k in overrig.set_members(overrig.KNOT_SET)
                           if k not in before_knots]
            created += _dress_knots(fresh_knots, paths, radii, region_of)

            fresh = sorted(n for n in (builder._scene_nodes() - before)
                           if builder._recordable(n))
            if fresh:
                if not cmds.objExists(FK_SET):
                    cmds.sets(name=FK_SET, empty=True)
                cmds.sets(fresh, addElement=FK_SET)
                _hide_rig_machinery(fresh)
                recorded.extend(fresh)

        # Couple the chains: neck and arms onto the spine, legs onto the
        # pelvis, fingers onto the hands, spine onto root.
        before = builder._scene_nodes()
        attached = _attach_chains(scene_map)
        fresh = sorted(n for n in (builder._scene_nodes() - before)
                       if builder._recordable(n))
        if fresh:
            cmds.sets(fresh, addElement=FK_SET)
            _hide_rig_machinery(fresh)
            recorded.extend(fresh)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Built {0} FK controller(s), {1} chain(s) coupled, " \
              "{2} node(s) recorded".format(created, attached, len(recorded))
    if replaced:
        message += ", previous FK baked back"
    if not skinned:
        message += " - no skinCluster, ring sizes are guesses"
    elif guessed:
        message += " - {0} ring(s) sized from neighbours".format(len(guessed))
    return created, message
