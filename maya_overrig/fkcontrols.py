"""FK-looking selection markers on every animator bone.

The controllers are inert on purpose: they sit on their bone, follow it and can
be clicked, but drive nothing. How they should interact with the IK build is a
separate decision, and building them inert avoids putting two drivers on one
joint before that decision is made.

Sizing comes from the skinned mesh rather than from bone length. On this
skeleton bone length is meaningless: `pelvis` measures 3.68 because its first
child sits on top of it, `lowerarm_l` measures 9.08 because its first child is a
twist joint, and `head` measures 0 for having no children at all.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

from maya_overrig import bodymap

FK_SET = "RigPicker_fk"
SUFFIX = "_FK_ctrl"

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


def build_fk(scene_map):
    """Put a ring marker on every animator bone. Returns (count, message)."""
    targets = {b.joint for b in bodymap.BUTTONS if b.joint in scene_map}
    if not targets:
        return 0, "Not connected to a skeleton"

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker FK")
    try:
        removed = remove_fk()

        skinned = bool(cmds.ls(type="skinCluster"))
        dominant, shared = _vertex_buckets(targets) if skinned else ({}, {})

        # Character height, from the spread of the joints themselves. Taking a
        # bounding box of one joint gives a box of nothing.
        heights = [_world_position(scene_map[j]).y for j in targets]
        height = max(max(heights) - min(heights), 1.0)
        floor = height * 0.004

        # Measure everything first: the correction rules let one joint borrow
        # another's size, so they need the whole picture before anything is
        # built.
        buildable = [b for b in bodymap.BUTTONS
                     if b.joint in scene_map
                     and cmds.objExists(scene_map[b.joint])]
        radii = {}
        guessed = []
        for button in buildable:
            joint = button.joint
            radius = _radius_for(joint, scene_map[joint], dominant, shared,
                                 floor)
            if radius is None:
                radius = floor * 6.0
                guessed.append(joint)
            radii[joint] = radius
        radii = apply_size_rules(radii)

        created = []
        seen_in_region = {}
        for button in buildable:
            joint = button.joint
            radius = radii[joint]

            index = seen_in_region.get(button.region, 0)
            seen_in_region[button.region] = index + 1
            if button.region in ("spine", "head"):
                radius *= stagger(index)

            normal = (0, 1, 0) if joint == "root" else (1, 0, 0)
            if joint == "root":
                radius = max(radius, height * 0.16)

            ring = _make_ring(controller_name(joint), radius, normal,
                              colour_for(button.region))
            ring = cmds.parent(ring, scene_map[joint], relative=True)[0]
            ring = cmds.ls(ring, long=True)[0]
            for attr in ("translate", "rotate", "scale"):
                for axis in "XYZ":
                    cmds.setAttr("%s.%s%s" % (ring, attr, axis), lock=True)
            created.append(ring)

        if created:
            if not cmds.objExists(FK_SET):
                cmds.sets(name=FK_SET, empty=True)
            cmds.sets(created, addElement=FK_SET)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Built {0} FK marker(s)".format(len(created))
    if removed:
        message += ", {0} replaced".format(removed)
    if not skinned:
        message += " - no skinCluster, sizes are guesses"
    elif guessed:
        message += " - {0} sized from neighbours".format(len(guessed))
    return len(created), message
