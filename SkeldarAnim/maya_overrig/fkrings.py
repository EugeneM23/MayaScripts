"""Ring sizing from the skinned mesh, and dressing OverRig knots as controls.

Sizing comes from the mesh rather than bone length -- on this skeleton bone
length is meaningless (`head` measures 0 for having no children). A joint's
radius is the perpendicular spread of the vertices it dominates; _BORROW and
_SCALE hold the user-driven corrections, _SQUARE the bones drawn square so
they read among same-size neighbours. Dressing renames each knot to
<joint>_FK_ctrl and attaches our sized shape -- UUID-safe, because renaming
a chain parent invalidates every descendant path.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

from maya_overrig import bodymap, naming
from maya_overrig import fkchains

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


def colour_for(region):
    """RGB for a body region, by side."""
    return _REGION_COLOURS[region]


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
# The clavicle rings live around the DELTOID (see _AT_BONE_END) and must
# clear it whole; the skin-measured 9.0 buried them («контролеры не видно»,
# 2026-08-21), and 1.4 still dipped the lower arc into the arm on the real
# mesh -- judged on a viewport capture, not a guess. 1.7 floats free.
_SCALE = {"foot_l": 0.5, "foot_r": 0.5,
          "clavicle_l": 1.7, "clavicle_r": 1.7}


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


# Bones whose controller draws as a square instead of a ring. The pelvis sits
# in a stack of near-equal spine rings and disappears among them.
_SQUARE = frozenset({"pelvis"})

# Bones whose ring is centred on the bone's far END (its first joint child)
# instead of its origin. The clavicle's origin sits 1.4 cm off the midline,
# INSIDE the chest, so a ring centred there is invisible from everywhere;
# its band belongs around the deltoid, at the other end of the bone -- the
# same visual language as every other ring, just at the far end. The pivot
# does not move: the control still turns about the bone origin, and the
# ring sweeping with the shoulder is what a clavicle control does anywhere.
_AT_BONE_END = frozenset({"clavicle_l", "clavicle_r"})


def is_square(joint):
    """True when the joint's controller draws as a square, not a ring."""
    return joint in _SQUARE


def at_bone_end(joint):
    """True when the joint's ring is drawn at the bone's far end."""
    return joint in _AT_BONE_END


def square_points(radius):
    """Closed square in the plane perpendicular to the bone axis (local X).

    Corners at (0, +-r, +-r): the sides face the local axes and span the
    diameter of the ring the square replaces, so it reads as the same size
    with the corners standing slightly proud of the neighbouring rings.
    """
    r = float(radius)
    return [(0.0, -r, -r), (0.0, -r, r), (0.0, r, r), (0.0, r, -r),
            (0.0, -r, -r)]


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


def _make_ring(name, radius, normal, colour, center=(0.0, 0.0, 0.0)):
    ring = cmds.circle(name=name, normal=normal, radius=radius,
                       center=center, sections=_SECTIONS,
                       constructionHistory=False)[0]
    _style_curve(ring, colour)
    return ring


def twist_ring(name, radius, colour):
    """A free ring for a twist control, encircling its own local X.

    Unlike `_dress_knots`, which attaches a shape to an OverRig knot, the
    twist control is a transform of its own parented under a BONE -- so this
    hands the caller a free transform to parent, place and lock. Same circle
    and same styling as every other ring in the toolset: one place makes
    them, or they drift apart.
    """
    return _make_ring(name, radius, (1.0, 0.0, 0.0), colour)


def measured_radii(scene_map):
    """{joint: ring radius} measured from the skinned mesh.

    The public face of `_final_radii` for a caller that wants the sizes
    without dressing anything -- `twist.build` asks for them to size its
    manual controls against the same skin the FK rings are sized against.
    """
    radii, _guessed, _skinned = _final_radii(scene_map)
    return radii


def _bone_end_local(knot, bone):
    """The bone's far end (its first joint child) in the knot's local space.

    The knot stands ON the bone (parentConstrAnim), so this is very nearly
    (bone length, 0, 0) -- but computed, never assumed: the knot's frame is
    OverRig's, not ours. A bone with no joint child keeps the origin --
    nothing to point at, and a buried ring beats a wrong one.
    """
    kids = cmds.listRelatives(bone, children=True, type="joint",
                              fullPath=True) or []
    if not kids:
        return (0.0, 0.0, 0.0)
    end = om.MPoint(*cmds.xform(kids[0], query=True, worldSpace=True,
                                translation=True))
    inverse = om.MMatrix(cmds.xform(knot, query=True, worldSpace=True,
                                    matrix=True)).inverse()
    local = end * inverse
    return (local.x, local.y, local.z)


def _make_square(name, radius, colour):
    square = cmds.curve(name=name, degree=1, point=square_points(radius))
    # cmds.curve names the transform but leaves the shape as curveShapeN;
    # match the <name>Shape convention the circles get for free.
    shape = cmds.listRelatives(square, shapes=True, fullPath=True)[0]
    cmds.rename(shape, name + "Shape")
    _style_curve(square, colour)
    return square


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

    Returns {bone leaf name: knot path} -- the controller index for what
    this call created. Since 2026-09-01 that return value is load-bearing
    rather than a count: with two characters in the scene the rename comes
    out as `upperarm_l_FK_ctrl1`, so the build cannot find its own knots
    by name afterwards and is handed them here instead.

    Works through UUIDs: renaming a chain parent changes every descendant's
    path, so each knot's path is re-resolved just before its own rename.
    """
    by_bone = _bone_knot_map(chain_paths, knot_paths)
    # UUIDs for every mapped knot BEFORE any rename: renaming the chain root
    # invalidates the stored paths of every knot beneath it.
    uuid_by_bone = {bone: naming.uuid_of(knot)
                    for bone, knot in by_bone.items()}
    dressed = {}
    for bone, uuid in sorted(uuid_by_bone.items()):
        knot = naming.path_from_uuid(uuid)
        if not knot:
            continue
        bare = naming.leaf(bone)

        knot = cmds.ls(cmds.rename(knot, fkchains.controller_name(bare)),
                       long=True)[0]
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
        center = (_bone_end_local(knot, bone) if at_bone_end(bare)
                  else (0.0, 0.0, 0.0))
        if is_square(bare):
            ring = _make_square(bare + "_FK_ring_tmp", radii.get(bare, 1.0),
                                colour_for(region_of[bare]))
        else:
            ring = _make_ring(bare + "_FK_ring_tmp", radii.get(bare, 1.0),
                              normal, colour_for(region_of[bare]),
                              center=center)
        shape = cmds.listRelatives(ring, shapes=True, fullPath=True)[0]
        cmds.parent(shape, knot, relative=True, shape=True)
        cmds.delete(ring)
        dressed[bare] = knot
    return dressed
