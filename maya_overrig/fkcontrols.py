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

import math

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

from maya_overrig import axes, bodymap, builder, naming, overrig

FK_SET = "RigPicker_fk"          # legacy flat set; absorbed by a full bake
FK_SET_PREFIX = "RigPicker_fk_"  # one set per chain, the switchable unit
SUFFIX = "_FK_ctrl"

# The four limb chains -- they carry the finger bracket on arm switches.
LIMB_CHAINS = ("arm_l", "arm_r", "leg_l", "leg_r")

# Everything Switch FK/IK may convert. The spine converts like a limb but
# carries a different bracket: whole chains hang off its controllers.
SWITCHABLE = LIMB_CHAINS + ("spine",)

# Where a chain re-hangs when the spine it sat on goes IK: the attach bone
# maps to the IK role that now carries it. spine_05 is driven by the end
# control; the pelvis follows the base group's attach machinery, so anything
# hung on the base group follows the pelvis exactly.
SPINE_REHANG = {"spine_05": "end", "pelvis": "base"}


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


def chain_set(chain):
    """Name of the object set recording one chain's created nodes."""
    return FK_SET_PREFIX + chain


def finger_chains_for(limb):
    """The finger chains riding on an arm's hand; empty for legs.

    These hang inside the hand controller, so an arm switch must lift them out
    first or they die with the arm's rig.
    """
    if limb not in ("arm_l", "arm_r"):
        return []
    side = limb[-1]
    fingers = ("index", "middle", "ring", "pinky", "thumb")
    return [name for name, _ in CHAINS
            if name.endswith("_" + side) and name.split("_")[0] in fingers]


def colour_for(region):
    """RGB for a body region, by side."""
    return _REGION_COLOURS[region]


def dependent_chains(root_ctrls, containers):
    """Chains whose root controller sits inside one of the container paths.

    `root_ctrls` is {chain: long path or None}, `containers` a list of long
    paths about to be deleted. A controller that is a DAG descendant of a
    container dies with it, so the caller must lift these chains out first.
    Pure -- both arguments are plain data; results keep CHAINS order.
    """
    found = []
    for chain_name, _ in CHAINS:
        path = root_ctrls.get(chain_name)
        if not path:
            continue
        if any(builder._is_inside(path, container)
               for container in containers):
            found.append(chain_name)
    return found


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


# Bones whose controller draws as a square instead of a ring. The pelvis sits
# in a stack of near-equal spine rings and disappears among them.
_SQUARE = frozenset({"pelvis"})


def is_square(joint):
    """True when the joint's controller draws as a square, not a ring."""
    return joint in _SQUARE


def square_points(radius):
    """Closed square in the plane perpendicular to the bone axis (local X).

    Corners at (0, +-r, +-r): the sides face the local axes and span the
    diameter of the ring the square replaces, so it reads as the same size
    with the corners standing slightly proud of the neighbouring rings.
    """
    r = float(radius)
    return [(0.0, -r, -r), (0.0, -r, r), (0.0, r, r), (0.0, r, -r),
            (0.0, -r, -r)]


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


def _style_curve(transform, colour):
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *colour)
    if cmds.attributeQuery("lineWidth", node=shape, exists=True):
        cmds.setAttr(shape + ".lineWidth", _LINE_WIDTH)


def _make_ring(name, radius, normal, colour):
    ring = cmds.circle(name=name, normal=normal, radius=radius,
                       sections=_SECTIONS, constructionHistory=False)[0]
    _style_curve(ring, colour)
    return ring


def _make_square(name, radius, colour):
    square = cmds.curve(name=name, degree=1, point=square_points(radius))
    # cmds.curve names the transform but leaves the shape as curveShapeN;
    # match the <name>Shape convention the circles get for free.
    shape = cmds.listRelatives(square, shapes=True, fullPath=True)[0]
    cmds.rename(shape, name + "Shape")
    _style_curve(square, colour)
    return square


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


def _record_fresh(chain, before):
    """Record (and visually mute) everything created since `before`."""
    fresh = sorted(n for n in (builder._scene_nodes() - before)
                   if builder._recordable(n))
    if fresh:
        cmds.sets(fresh, addElement=_ensure_chain_set(chain))
        _hide_rig_machinery(fresh)
    return fresh


def remove_fk():
    """Delete every recorded FK node and set, without baking. Returns count."""
    doomed = list(_legacy_members())
    for name, _ in CHAINS:
        doomed.extend(chain_members(name))
    doomed = [d for d in doomed if cmds.objExists(d)]
    if doomed:
        cmds.delete(doomed)
    for name, _ in CHAINS:
        if cmds.objExists(chain_set(name)):
            cmds.delete(chain_set(name))
    if cmds.objExists(FK_SET):
        cmds.delete(FK_SET)
    return len(doomed)


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
        if is_square(bare):
            ring = _make_square(bare + "_FK_ring_tmp", radii.get(bare, 1.0),
                                colour_for(region_of[bare]))
        else:
            ring = _make_ring(bare + "_FK_ring_tmp", radii.get(bare, 1.0),
                              normal, colour_for(region_of[bare]))
        shape = cmds.listRelatives(ring, shapes=True, fullPath=True)[0]
        cmds.parent(shape, knot, relative=True, shape=True)
        cmds.delete(ring)
        dressed += 1
    return dressed


_ROTATE_CHANNELS = ("rotateX", "rotateY", "rotateZ")


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
    locked = [plug for plug in
              (ctrl + ".jointOrient" + axis for axis in "XYZ")
              if cmds.getAttr(plug, lock=True)]
    for plug in locked:
        cmds.setAttr(plug, lock=False)
    try:
        cmds.setAttr(ctrl + ".rotateAxis", *axes.euler_degrees(rotate_axis))
        cmds.setAttr(ctrl + ".jointOrient", *axes.euler_degrees(joint_orient))
        for time, values in retargeted:
            for attr, value in zip(_ROTATE_CHANNELS, values):
                cmds.keyframe(ctrl, attribute=attr, time=(time, time),
                              valueChange=value, absolute=True)
        if not times:
            cmds.setAttr(ctrl + ".rotate", *axes.euler_degrees(
                axes.retarget(reference, offset, reference), order))
    finally:
        for plug in locked:
            cmds.setAttr(plug, lock=True)
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


def _attach_chain(chain_name, chain, parent_of, targeted):
    """Hang one chain's root controller off its parent bone's controller.

    OverRig's apply_Parent_in does the heavy lifting: the child knot becomes a
    DAG child of the parent knot and its animation is re-baked into the new
    local space, so world motion is unchanged (verified: zero drift). Selection
    order is child first, parent last. Returns True when coupled.
    """
    parent = attach_parent(chain[0], parent_of, targeted)
    if parent is None:
        return False
    child_ctrl = controller_name(chain[0])
    parent_ctrl = controller_name(parent)
    if not (cmds.objExists(child_ctrl) and cmds.objExists(parent_ctrl)):
        return False
    cmds.select([child_ctrl, parent_ctrl], replace=True)
    mel.eval("apply_Parent_in()")
    return True


def _bake_fk_chains(scene_map, chains=None):
    """Bake FK chains back onto the bones and remove their nodes. No undo chunk.

    `chains=None` means everything recorded, including the legacy flat set.
    The requested list is expanded with chains nested inside it, order does not
    matter beyond that: bones are baked while the knots still drive, then every
    doomed node goes at once.
    """
    members_by_chain = {name: chain_members(name) for name, _ in CHAINS}
    legacy = []
    if chains is None:
        wanted = [name for name, _ in CHAINS if members_by_chain[name]]
        legacy = [m for m in _legacy_members() if cmds.objExists(m)]
    else:
        wanted = [c for c in chains if members_by_chain.get(c)]

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


def bake_fk(scene_map, chains=None):
    """Bake FK back to the bones -- everything, or just the given chains."""
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

    region_of = {b.joint: b.region for b in bodymap.BUTTONS}
    parent_of = _parent_map()
    targeted = {j for _, chain in CHAINS for j in chain}

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker FK")
    try:
        if only is None:
            replaced = _bake_fk_chains(scene_map)[0] if has_fk() else 0
        else:
            existing = [c for c in only if chain_members(c)]
            replaced = (_bake_fk_chains(scene_map, existing)[0]
                        if existing else 0)

        radii, guessed, skinned = _final_radii(scene_map)

        created = 0
        recorded = 0
        attached = 0
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
            if len(paths) == 1:
                mel.eval("apply_parentConstrAnim(1)")
            else:
                mel.eval("apply_ForwHierarhy(1)")

            fresh_knots = [k for k in overrig.set_members(overrig.KNOT_SET)
                           if k not in before_knots]
            created += _dress_knots(fresh_knots, paths, radii, region_of)

            # Couple inside the same diff window so the coupling nodes land in
            # this chain's manifest. Parents precede children in CHAINS, so a
            # full build always finds its target; a restricted build couples
            # only if the target controller happens to exist.
            if _attach_chain(chain_name, chain, parent_of, targeted):
                attached += 1

            recorded += len(_record_fresh(chain_name, before))

        # Last, once every chain is built and coupled: put the controllers on
        # the skeleton's mirror convention. Creates nothing, so it stays out
        # of the manifests, and moves nothing, so the animation is untouched.
        aligned = align_controllers(scene_map, only)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Built {0} FK controller(s), {1} chain(s) coupled, " \
              "{2} node(s) recorded, {3} on bone axes".format(
                  created, attached, recorded, aligned)
    if replaced:
        message += ", previous FK baked back"
    if not skinned:
        message += " - no skinCluster, ring sizes are guesses"
    elif guessed:
        message += " - {0} ring(s) sized from neighbours".format(len(guessed))
    return created, message


# ---------------------------------------------------------------------------
# Switch FK/IK
# ---------------------------------------------------------------------------

def _parent_out(ctrl, record_chain):
    """Lift a nested controller to world through OverRig, re-baked."""
    before = builder._scene_nodes()
    cmds.select(ctrl, replace=True)
    mel.eval("apply_Parent_out()")
    _record_fresh(record_chain, before)


def _parent_in(child_ctrl, parent_ctrl, record_chain):
    """Hang a controller inside another through OverRig, re-baked."""
    before = builder._scene_nodes()
    cmds.select([child_ctrl, parent_ctrl], replace=True)
    mel.eval("apply_Parent_in()")
    _record_fresh(record_chain, before)


def _ik_hand_control(limb):
    """The IK end control of a built IK limb, found through its manifest.

    Never by bare name -- OverRig suffixes renames on collision.
    """
    return builder.ik_control(limb, "end")


def _spine_dependents():
    """Chains whose root controller currently hangs inside the spine's nodes.

    Both representations count as containers: FK chain members before an
    FK -> IK switch, IK manifest members before the way back.
    """
    containers = [m for m in (chain_members("spine")
                              + overrig.set_members(builder.limb_set("spine")))
                  if cmds.objExists(m)]
    if not containers:
        return []
    root_ctrls = {}
    for chain_name, chain in CHAINS:
        if chain_name == "spine":
            continue
        paths = cmds.ls(controller_name(chain[0]), long=True) or []
        root_ctrls[chain_name] = paths[0] if paths else None
    return dependent_chains(root_ctrls, containers)


def _spine_rehang_target(bone, now_ik):
    """The control a dependent chain hangs on after the spine converted."""
    if bone is None:
        return None
    if now_ik:
        role = SPINE_REHANG.get(bone)
        return builder.ik_control("spine", role) if role else None
    ctrl = controller_name(bone)
    return ctrl if cmds.objExists(ctrl) else None


def switch_limbs(scene_map, limbs):
    """Convert each limb to the opposite rig type, animation re-baked.

    FK becomes IK, IK becomes FK. Fingers riding on an arm's hand are lifted to
    world before the arm converts and hung back on the new hand control after
    -- they are DAG children of what gets deleted, so anything less loses them.
    The spine carries the same bracket writ large: whole chains (neck, FK
    clavicles, FK thighs) hang off its controllers and are re-hung onto
    whichever control now drives their attach bone.
    """
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
                skipped.append(limb)
                continue

            if limb == "spine":
                riders = _spine_dependents()
            else:
                riders = [c for c in finger_chains_for(limb)
                          if chain_members(c)]
            for chain in riders:
                ctrl = controller_name(table[chain][0])
                if cmds.objExists(ctrl):
                    _parent_out(ctrl, chain)

            if is_fk:
                _bake_fk_chains(scene_map, [limb])
                builder.build(scene_map, only=[limb])
                target = _ik_hand_control(limb)
                done.append(limb + " -> IK")
            else:
                builder.bake_limbs(scene_map, [limb])
                _count, build_message = build_fk(scene_map, only=[limb])
                target = controller_name(table[limb][-1])
                if "0 chain(s) coupled" in build_message:
                    notes.append(limb + " uncoupled (no parent control)")
                done.append(limb + " -> FK")

            if limb == "spine":
                # Each rider goes where its attach bone now lives, not onto
                # one shared control: the neck and clavicles follow the
                # chest, the thighs follow the pelvis.
                parent_of = _parent_map()
                targeted = {j for _, chain in CHAINS for j in chain}
                for chain in riders:
                    bone = attach_parent(table[chain][0], parent_of, targeted)
                    target = _spine_rehang_target(bone, now_ik=is_fk)
                    ctrl = controller_name(table[chain][0])
                    if target and cmds.objExists(ctrl):
                        _parent_in(ctrl, target, chain)
                    else:
                        notes.append(chain + " left in world")
                continue

            for chain in riders:
                ctrl = controller_name(table[chain][0])
                if target and cmds.objExists(ctrl) and cmds.objExists(target):
                    _parent_in(ctrl, target, chain)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Switched: " + ", ".join(done) if done else "Nothing to switch"
    if skipped:
        message += ". No rig on: " + ", ".join(skipped)
    if notes:
        message += ". " + "; ".join(notes)
    return done, skipped, message
