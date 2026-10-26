"""Dynamics' setup in the scene (2026-10-26): the chains, the colliders and the wind arrow.

Everything lives with the character, so Delete character takes it whole:
- a locked `Dynamics` group (marked `skeldarDynamicsGroup`) in the chain's character group (at
  world level for a chain of no character) holds the chains and the floor;
- a chain is a transform `<root leaf>_dyn` there, marked `skeldarDynChain`, holding its members'
  UUIDs (root first), its settings as JSON and the UUID of its carrier (the node whose travel
  Inertia leaves out: the rig's Main, else the skeleton's top joint, else the root's top ancestor);
- a sphere or capsule collider hangs in a dynamics space of its bone (the weapon spaces'
  `ensure_marked_space`: a transform following the bone with no offset), so its own channels are
  its offset in the bone's axes; its `radius` and `length` (cm) are attributes, its segment runs
  along its local X, centred; `enabled` is keyable; a plane (`Floor`) stands in the Dynamics group,
  its local Y the normal;
- the wind is one arrow `Wind` at world level (its local +Z the direction), its strength in g,
  turbulence, gust, frequency and seed keyable.

Every node and attribute of ours starts with `skeldar` (Delete character's rule). Lookups by
marker, never by name, through `scope.active_only` (scene tabs). Spec:
docs/superpowers/specs/2026-10-26-bone-dynamics-design.md
"""

import json
import math

import maya.cmds as cmds
import numpy as np

from maya_dynamics import model
from maya_scenetabs import scope

GROUP_MARKER = "skeldarDynamicsGroup"
GROUP_NAME = "Dynamics"
CHAIN_MARKER = "skeldarDynChain"
MEMBERS = "skeldarDynMembers"
SETTINGS = "skeldarDynSettings"
CARRIER = "skeldarDynCarrier"
CHAIN_SUFFIX = "_dyn"
COLLIDER_MARKER = "skeldarDynCollider"           # = its kind
AUTO_MARKER = "skeldarDynAuto"
SPACE_MARKER = "skeldarDynSpace"
SPACES_MARKER = "skeldarDynSpacesGroup"
SPACES_NAME = "DynamicsSpaces"
SPACE_SUFFIX = "_dynSpace"
WIND_MARKER = "skeldarDynWind"
WIND_NAME = "Wind"
LAYER_MARKER = "skeldarDynamics"                 # = the chain's UUID
LAYER_PREFIX = "Dynamics_"
FLOOR_NAME = "Floor"
KINDS = ("sphere", "capsule", "plane")
SUFFIXES = {"sphere": "_dynSphere1", "capsule": "_dynCapsule1"}
COLOUR = (0.3, 0.85, 0.8)                        # the Tools palette's teal (Across)
WIND_COLOUR = (0.65, 0.9, 1.0)
FLOOR_HALF = 60.0                                # cm: the floor's drawing
WIND_SIZE = 60.0
SEGMENTS = 24
#  (attribute, default, low, high) - the wind arrow's keyable channels
WIND_CHANNELS = (("strength", 0.3, 0.0, 10.0), ("turbulence", 0.5, 0.0, 1.0),
                 ("gust", 0.3, 0.0, 1.0), ("frequency", 1.0, 0.05, 10.0))
#  the bodies Auto body puts a capsule on (the Ragdoll's table)
AUTO_BODIES = ("pelvis", "spine_lo", "spine_hi", "head", "upperarm_l", "lowerarm_l",
               "upperarm_r", "lowerarm_r", "thigh_l", "calf_l", "thigh_r", "calf_r")
DEFAULT_RADIUS = 5.0
MIN_RADIUS, MAX_RADIUS = 1.0, 25.0

NOTHING = "select a chain's root - a joint or control with one of its kind below it"
ALONE = "%s has nothing of its kind below it - a chain needs two members"
IN_CHAIN = "%s is in %s already - select that chain, or Remove it first"
ON_CHAIN = "%s lies under %s's chain - chains on chains are not supported"
NO_CHARACTER = "select a character for Auto body - any part of a rig or skeleton"


# --------------------------------------------------------------------- nodes

def leaf(path):
    return (path or "").split("|")[-1].split(":")[-1]


def _long(node):
    found = cmds.ls(node, long=True) if node else []
    return found[0] if found else None


def _uuid(node):
    found = cmds.ls(node, uuid=True) if node else []
    return found[0] if found else None


def _by_uuid(uuid):
    found = cmds.ls(uuid, long=True) if uuid else []
    return found[0] if found else None


def _has(node, attr):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery(attr, node=node,
                                                                       exists=True)


def _get(node, attr, fallback=None):
    return cmds.getAttr(node + "." + attr) if _has(node, attr) else fallback


def _set_string(node, attr, value):
    if not _has(node, attr):
        cmds.addAttr(node, longName=attr, dataType="string")
    cmds.setAttr(node + "." + attr, value, type="string")


def _number(node, attr, value, low=None, high=None, keyable=True, kind="double"):
    if not _has(node, attr):
        flags = {}
        if low is not None:
            flags["minValue"] = low
        if high is not None:
            flags["maxValue"] = high
        cmds.addAttr(node, longName=attr, attributeType=kind, defaultValue=value, **flags)
        cmds.setAttr(node + "." + attr, keyable=keyable)
        if not keyable:
            cmds.setAttr(node + "." + attr, channelBox=True)
    cmds.setAttr(node + "." + attr, value)


def _marked(marker):
    """Our nodes carrying `marker`, in the active tab, long paths."""
    found = cmds.ls("*." + marker, recursive=True, objectsOnly=True, long=True) or []
    return scope.active_only(sorted(set(found)), cmds)


def group_for(node):
    """The Dynamics group of `node`'s character (its character group's), made on demand; at world
    level for a node of no character."""
    from maya_scenesetup import chargroup
    from maya_scenesetup import weaponspace
    return weaponspace._group_under(chargroup.group_of(node), GROUP_MARKER, GROUP_NAME)


def _character(node):
    from maya_scenesetup import chargroup
    return chargroup.group_of(node)


# -------------------------------------------------------------------- chains

def chains():
    """Every chain of ours in the active tab, long paths."""
    return [c for c in _marked(CHAIN_MARKER) if cmds.nodeType(c) == "transform"]


def members(chain):
    """`chain`'s members, root first, long paths (None for one that is gone)."""
    try:
        uuids = json.loads(_get(chain, MEMBERS, "[]") or "[]")
    except ValueError:
        uuids = []
    return [_by_uuid(u) for u in uuids]


def root_of(chain):
    found = members(chain)
    return found[0] if found else None


def chain_of(node):
    """The chain `node` is, or is a member of, or None."""
    path = _long(node)
    if not path:
        return None
    for chain in chains():
        if chain == path or path in members(chain):
            return chain
    return None


def read_settings(chain):
    """`chain`'s settings (`model.settings` fills and clamps)."""
    try:
        given = json.loads(_get(chain, SETTINGS, "{}") or "{}")
    except ValueError:
        given = {}
    return model.settings(given if isinstance(given, dict) else {})


def write_settings(chain, s):
    _set_string(chain, SETTINGS, json.dumps(model.settings(s), sort_keys=True))


def carrier_of(node):
    """What Inertia leaves the travel of for a chain rooted at `node`: the rig's Main, else the
    skeleton's top joint, else the top ancestor."""
    import maya_rigs
    path = _long(node)
    rig = maya_rigs.rig_of(path, maya_rigs.rigs())
    if rig is not None:
        main = _long(maya_rigs.node(rig, "Main"))
        if main:
            return main
    top, walk = None, path
    while walk:
        if cmds.nodeType(walk) == "joint":
            top = walk
        walk = (cmds.listRelatives(walk, parent=True, fullPath=True) or [None])[0]
    return top or "|" + path.split("|")[1]


def carrier(chain):
    return _by_uuid(_get(chain, CARRIER)) or carrier_of(root_of(chain))


def _held(existing):
    """{member long path: its chain} of the standing chains."""
    out = {}
    for chain in existing:
        for member in members(chain):
            if member:
                out[member] = chain
    return out


def plan_chains(roots, existing_members):
    """(new chains, picked, refusal) for `roots` against `existing_members` {member: chain}:
    a root already in a chain picks that chain; a new chain may share no member with a standing
    one, nor lie under or over one. `chain_from(root)` gives (chain, note) - the scene's seam."""
    from maya_tools import overlap
    new, picked, notes = [], [], []
    for root in roots:
        if root in existing_members:
            if existing_members[root] not in picked:
                picked.append(existing_members[root])
            continue
        chain, note = overlap.chain_from(root)
        if note:
            notes.append(note)
        if len(chain) < 2:
            return [], [], notes, ALONE % leaf(root)
        for node in chain:
            if node in existing_members:
                return [], [], notes, IN_CHAIN % (leaf(node), leaf(existing_members[node]))
            for member, owner in existing_members.items():
                if node.startswith(member + "|") or member.startswith(node + "|"):
                    return [], [], notes, ON_CHAIN % (leaf(node), leaf(owner))
        new.append(chain)
    inner = set(node for chain in new for node in chain[1:])
    new = [chain for chain in new if chain[0] not in inner]
    return new, picked, notes, ""


def add_chains(selection=None, given=None):
    """+ Chain: every selected node a root (Overlap's Hierarchy rule). (chains, notes, refusal);
    a refusal makes nothing."""
    from maya_tools import knots
    from maya_tools import overlap
    roots = knots._selection(selection)
    if not roots:
        return [], [], NOTHING
    new, picked, notes, refusal = plan_chains(roots, _held(chains()))
    if refusal:
        return [], notes, refusal
    for chain in new:
        for node in chain:
            refusal = overlap._member_refusal(node)
            if refusal:
                return [], notes, refusal
    made = [_make_chain(chain, given) for chain in new]
    return made + picked, notes, ""


def _make_chain(chain, given):
    node = cmds.createNode("transform", name=leaf(chain[0]) + CHAIN_SUFFIX,
                           parent=group_for(chain[0]), skipSelect=True)
    node = _long(node)
    for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(node + "." + attr, lock=True, keyable=False, channelBox=False)
    _set_string(node, CHAIN_MARKER, "1")
    _set_string(node, MEMBERS, json.dumps([_uuid(m) for m in chain]))
    _set_string(node, CARRIER, _uuid(carrier_of(chain[0])) or "")
    write_settings(node, given or {})
    return node


def remove(chain):
    """A chain's layer and setup gone (its colliders stay). The layer's name, or None."""
    layer = layer_of(chain)
    if layer:
        cmds.delete(layer)
    group = (cmds.listRelatives(chain, parent=True, fullPath=True) or [None])[0]
    cmds.delete(chain)
    _prune(group)
    return layer


def _prune(group):
    if group and cmds.objExists(group) and _has(group, GROUP_MARKER) \
            and not cmds.listRelatives(group, children=True):
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(group + "." + attr, lock=False)
        cmds.delete(group)


def layer_of(chain):
    """The chain's Dynamics layer, or None."""
    uuid = _uuid(chain)
    for layer in cmds.ls(type="animLayer") or []:
        if uuid and _get(layer, LAYER_MARKER) == uuid:
            return layer
    return None


def layers():
    """Every Dynamics layer of ours."""
    return [layer for layer in cmds.ls(type="animLayer") or [] if _has(layer, LAYER_MARKER)]


def layer_name(chain):
    return LAYER_PREFIX + leaf(root_of(chain) or chain).replace(CHAIN_SUFFIX, "")


def label(chain):
    """A chain's row in the card's list: «hair_01 · 6 · baked»."""
    found = members(chain)
    gone = sum(1 for m in found if m is None)
    words = [leaf(found[0]) if found and found[0] else leaf(chain), str(len(found))]
    if gone:
        words.append("%d gone" % gone)
    if layer_of(chain):
        words.append("baked")
    return " · ".join(words)


# ----------------------------------------------------------------- colliders

def colliders(chain=None):
    """Every collider of ours (the active tab's); with `chain`, the ones it collides with: its
    character's and those of no character."""
    found = [c for c in _marked(COLLIDER_MARKER) if cmds.nodeType(c) == "transform"]
    if chain is None:
        return found
    own = _character(root_of(chain) or chain)
    return [c for c in found if _character(c) in (own, None)]


def kind_of(collider):
    kind = _get(collider, COLLIDER_MARKER)
    return kind if kind in KINDS else None


def is_collider(node):
    return kind_of(node) is not None


def _local_point(point, matrix):
    """A world `point` in the frame of a row-vector world `matrix` (4x4)."""
    homogeneous = np.append(np.asarray(point, float), 1.0)
    return (homogeneous @ np.linalg.inv(matrix))[:3]


def _world(node):
    return np.reshape(cmds.getAttr(node + ".worldMatrix[0]"), (4, 4))


def rigid(matrix):
    """`matrix` (4x4) without its scale or shear: what a parent constraint carries."""
    out = np.array(matrix, float)
    u, _s, vt = np.linalg.svd(out[:3, :3])
    out[:3, :3] = u @ vt
    return out


def segment_frame(a, b, up_hint=(0.0, 1.0, 0.0)):
    """A frame (4x4, row vectors) with X along a-b, centred between them, Y as near `up_hint` as
    is square to X."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    x = b - a
    size = np.linalg.norm(x)
    x = x / size if size > 1e-9 else np.array([1.0, 0.0, 0.0])
    hint = np.asarray(up_hint, float)
    if abs(float(np.dot(hint, x))) > 0.95:
        hint = np.array([0.0, 0.0, 1.0]) if abs(x[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, hint)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    out = np.eye(4)
    out[:3, :3] = [x, y, z]
    out[3, :3] = (a + b) * 0.5
    return out


def default_shape(kind, child_local):
    """(local matrix 4x4, radius, length) of a new collider of `kind` on a bone whose next joint
    stands at `child_local` in the bone's own space (None: none)."""
    if child_local is None or float(np.linalg.norm(child_local)) < 1e-6:
        return np.eye(4), DEFAULT_RADIUS, (0.0 if kind == "sphere" else 2.0 * DEFAULT_RADIUS)
    span = float(np.linalg.norm(child_local))
    if kind == "sphere":
        return np.eye(4), min(MAX_RADIUS, max(MIN_RADIUS, 0.4 * span)), 0.0
    radius = min(MAX_RADIUS, max(MIN_RADIUS, 0.25 * span))
    return segment_frame(np.zeros(3), child_local), radius, span


def _child_local(bone):
    kids = cmds.listRelatives(bone, children=True, type="joint", fullPath=True) or \
        cmds.listRelatives(bone, children=True, type="transform", fullPath=True) or []
    if not kids:
        return None
    point = cmds.xform(kids[0], query=True, worldSpace=True, rotatePivot=True)
    return _local_point(point, rigid(_world(bone)))


def _space(bone):
    from maya_scenesetup import weaponspace
    return weaponspace.ensure_marked_space(bone, SPACE_MARKER, SPACES_MARKER, SPACES_NAME,
                                           SPACE_SUFFIX)


def _collider(kind, parent, name, matrix, radius, length):
    node = cmds.createNode("transform", name=name, parent=parent, skipSelect=True)
    node = _long(node)
    _set_string(node, COLLIDER_MARKER, kind)
    if kind != "plane":
        _number(node, "radius", float(radius), low=0.0, keyable=False)
        _number(node, "length", float(length), low=0.0, keyable=False)
    _number(node, "enabled", True, keyable=True, kind="bool")
    cmds.xform(node, matrix=[float(v) for v in np.asarray(matrix, float).ravel()])
    redraw(node)
    return node


def add_collider(kind, bone):
    """+ Sphere / + Capsule on `bone`, sized from the bone up to its next joint; + Floor for
    "plane". The collider's path."""
    if kind == "plane":
        return add_floor(bone)
    bone = _long(bone)
    matrix, radius, length = default_shape(kind, _child_local(bone))
    return _collider(kind, _space(bone), leaf(bone) + SUFFIXES[kind], matrix, radius, length)


def floor_of(node):
    """The plane collider standing for `node`'s character (or of no character), or None."""
    own = _character(node)
    for collider in colliders():
        if kind_of(collider) == "plane" and _character(collider) == own:
            return collider
    return None


def add_floor(node, height=None):
    """+ Floor: a plane in `node`'s Dynamics group at `height` (the lowest point of the
    character's skin when None, else 0); the one standing is handed back."""
    found = floor_of(node)
    if found:
        return found
    if height is None:
        height = lowest_point(node)
    matrix = np.eye(4)
    matrix[3, 1] = float(height)
    return _collider("plane", group_for(node), FLOOR_NAME, matrix, 0.0, 0.0)


def _meshes(root):
    from maya_scenesetup import colour
    shapes = colour.character_meshes(root) or []
    return [s for s in cmds.ls(shapes, long=True) or []
            if cmds.nodeType(s) == "mesh" and not cmds.getAttr(s + ".intermediateObject")]


def _root_of_character(node):
    from maya_poselib import apply as ap
    refs, refusal = ap._targets([node])
    return refs[0] if refs and not refusal else None


def lowest_point(node):
    """The lowest world Y of `node`'s character's skin, 0 when it has none."""
    ref = _root_of_character(node)
    low = None
    for shape in _meshes(ref.root) if ref else []:
        box = cmds.exactWorldBoundingBox(shape)
        low = box[1] if low is None else min(low, box[1])
    return 0.0 if low is None else float(low)


def auto_body(selection=None):
    """Auto body: capsules on the selected character's pelvis, spine, head, arms and legs (the
    Ragdoll's axes and radii from its skin), a second press replacing them, and the floor when
    none stands. (paths, refusal)."""
    import maya_skeletonmap
    from maya_poselib import apply as ap
    from maya_ragdoll import plan as rplan
    from maya_ragdoll import sim as rsim
    refs, refusal = ap._targets(selection)
    if refusal or not refs:
        return [], refusal or NO_CHARACTER
    ref = refs[0]
    joints = [ref.root] + (cmds.listRelatives(ref.root, allDescendents=True, type="joint",
                                              fullPath=True) or [])
    positions = dict((j, tuple(cmds.xform(j, query=True, worldSpace=True, translation=True)))
                     for j in joints)
    found = maya_skeletonmap.recognize(joints, positions)
    if found.refusal:
        return [], found.refusal
    mapping = found.mapping
    worlds = dict((name, _world(path)) for name, path in mapping.items())
    rider_of = dict((leaf(mapping[bone]), body) for bone, body in rplan.body_of_bone().items()
                    if bone in mapping)
    points = rsim.skinned_points(_meshes(ref.root), rider_of)
    own = _character(ref.root)
    for collider in colliders():
        if _has(collider, AUTO_MARKER) and _character(collider) == own:
            cmds.delete(collider)
    made = []
    rows = dict((row[0], row) for row in rplan.BODIES)
    for key in AUTO_BODIES:
        first = rows[key][1][0]
        if first not in mapping:
            continue
        try:
            a, b = rplan.axis_points(key, worlds)
        except KeyError:
            continue
        length = float(np.linalg.norm(b - a))
        radius = rplan.radius(points.get(key), a, b, length)
        bone = mapping[first]
        up = rplan.rot(worlds[first])[1]
        local = segment_frame(a, b, up) @ np.linalg.inv(rigid(worlds[first]))
        node = _collider("capsule", _space(bone), leaf(bone) + "_dynAuto1", local, radius, length)
        _set_string(node, AUTO_MARKER, key)
        made.append(node)
    if not floor_of(ref.root):
        made.append(add_floor(ref.root))
    return made, ""


# ----------------------------------------------------------------- drawings

def _ring(axes, centre, radius, segments=SEGMENTS):
    out = []
    for i in range(segments + 1):
        angle = 2.0 * math.pi * i / segments
        point = list(centre)
        point[axes[0]] += radius * math.cos(angle)
        point[axes[1]] += radius * math.sin(angle)
        out.append(tuple(point))
    return out


def _stadium(axis, radius, length, segments=SEGMENTS):
    """A capsule's outline in the plane of X and `axis` (1: Y, 2: Z)."""
    half = 0.5 * length
    out = []
    for end, start in ((half, -0.5 * math.pi), (-half, 0.5 * math.pi)):
        for i in range(segments // 2 + 1):
            angle = start + math.pi * i / (segments // 2)
            point = [end + radius * math.cos(angle), 0.0, 0.0]
            point[axis] = radius * math.sin(angle)
            out.append(tuple(point))
    out.append(out[0])
    return out


def capsule_lines(radius, length):
    """A capsule's (a sphere's when `length` is 0) drawing in its own space: polylines."""
    half = 0.5 * length
    lines = [_stadium(1, radius, length), _stadium(2, radius, length)]
    for x in ((0.0,) if length <= 1e-9 else (-half, 0.0, half)):
        lines.append(_ring((1, 2), (x, 0.0, 0.0), radius))
    return lines


def floor_lines(half=FLOOR_HALF):
    square = [(-half, 0.0, -half), (half, 0.0, -half), (half, 0.0, half), (-half, 0.0, half),
              (-half, 0.0, -half)]
    tick = [(0.0, 0.0, 0.0), (0.0, 0.2 * half, 0.0)]
    return [square, tick]


def wind_lines(size=WIND_SIZE):
    head = 0.25 * size
    shaft = [(0.0, 0.0, 0.0), (0.0, 0.0, size)]
    tip = [(-head * 0.5, 0.0, size - head), (0.0, 0.0, size), (head * 0.5, 0.0, size - head)]
    tip2 = [(0.0, -head * 0.5, size - head), (0.0, 0.0, size), (0.0, head * 0.5, size - head)]
    tail = [(-head * 0.4, 0.0, 0.0), (head * 0.4, 0.0, 0.0)]
    return [shaft, tip, tip2, tail]


def _draw(node, lines, colour):
    from maya_scenesetup import curvectrl
    for shape in cmds.listRelatives(node, shapes=True, fullPath=True) or []:
        cmds.delete(shape)
    for index, points in enumerate(lines):
        temp = cmds.curve(degree=1, point=list(points))
        shape = cmds.listRelatives(temp, shapes=True, fullPath=True)[0]
        cmds.parent(shape, node, shape=True, relative=True)
        cmds.delete(temp)
        shape = cmds.listRelatives(node, shapes=True, fullPath=True)[-1]
        shape = cmds.rename(shape, "%sShape%d" % (leaf(node), index + 1))
        curvectrl._dress(_long(shape) or shape, colour)


def redraw(collider):
    """A collider's drawing from its radius and length."""
    kind = kind_of(collider)
    if kind == "plane":
        _draw(collider, floor_lines(), COLOUR)
    elif kind:
        radius = max(0.01, float(_get(collider, "radius", DEFAULT_RADIUS)))
        length = 0.0 if kind == "sphere" else max(0.0, float(_get(collider, "length", 0.0)))
        _draw(collider, capsule_lines(radius, length), COLOUR)


# ---------------------------------------------------------------------- wind

def wind():
    """The scene's (the active tab's) wind arrow, or None."""
    found = [w for w in _marked(WIND_MARKER) if cmds.nodeType(w) == "transform"]
    return found[0] if found else None


def _in_view():
    """A point in front of the active view's camera (3 m out at its height), else 2 m up."""
    try:
        panel = cmds.getPanel(withFocus=True)
        if cmds.getPanel(typeOf=panel) == "modelPanel":
            camera = cmds.modelPanel(panel, query=True, camera=True)
            matrix = _world(camera)
            return matrix[3, :3] - 300.0 * matrix[2, :3]
    except Exception:                                            # noqa: BLE001 - batch, no view
        pass
    return np.array([0.0, 200.0, 0.0])


def add_wind():
    """+ Wind: the arrow, made in front of the camera when none stands. Its path."""
    found = wind()
    if found:
        return found
    node = _long(cmds.createNode("transform", name=WIND_NAME, skipSelect=True))
    _set_string(node, WIND_MARKER, "1")
    for attr, value, low, high in WIND_CHANNELS:
        _number(node, attr, value, low=low, high=high)
    _number(node, "seed", 1, low=0, keyable=True, kind="long")
    point = _in_view()
    cmds.xform(node, worldSpace=True, translation=[float(v) for v in point])
    cmds.setAttr(node + ".rotateY", 90.0)             # blowing along +X: across a character
    _draw(node, wind_lines(), WIND_COLOUR)
    return node
