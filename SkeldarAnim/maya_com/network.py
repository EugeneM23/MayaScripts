"""The scene side of the CoM: the character, its mass from the skin, and the
nine stock nodes that sum it live.

Which character: the toolset's rule (`maya_scenesetup.skeleton.current_root`:
the selection, the sole rig, the sole skeleton), plus a selected CoM handle
naming its own. The network is identified by ATTRIBUTE (`skeldarCom` on its
group, the parts linked to it by message), never by name - Maya uniquifies
the second bare skeleton's `CenterOfMass`.

The live sum (spec): CoM = Σ m̂_j (c_j · M_j), and with row vectors
c·M = c_x·row0 + c_y·row1 + c_z·row2 + row3, so four wtAddMatrix over the
joints' worldMatrix - weights m̂·c_x, m̂·c_y, m̂·c_z, m̂ - give it as
row0(Wx) + row1(Wy) + row2(Wz) + row3(Wt): four rowFromMatrix and one
plusMinusAverage. No constraint, no transform per bone.
"""

import collections
import time

import maya.cmds as cmds

import maya_rigs
from maya_com import massmodel

MARKER = "skeldarCom"            # on the group: the model's version
PART = "skeldarComPart"          # on every DAG part: what it is
NODES = "skeldarComNodes"        # on the group: UUIDs of every node we made
ROOT_LINK = "skeldarComRoot"     # message from the character's root
VERSION = "1"

VOXEL = 1.5                      # cm: the mass model's voxel
HANDLE_SHARE = 0.03              # the handle's radius, of the character's height

HANDLE_COLOUR = (1.0, 0.72, 0.15)
FLOOR_COLOUR = (0.55, 0.62, 0.70)
TRAIL_COLOUR = (1.0, 0.72, 0.15)
FLOOR_TRAIL_COLOUR = (0.45, 0.52, 0.60)

Character = collections.namedtuple("Character", "root rig namespace label")

NO_CHARACTER = "no character - select a control, a bone or a CoM handle"


# ------------------------------------------------------------------ pure

def is_first_person(name):
    """A 1P mesh - Manny's `Hands_1P`, the Orc D's `Orc_D_1P` - is a second
    copy of the arms (or the body without its head): counted, the arms would
    weigh twice."""
    leaf = name.split("|")[-1].split(":")[-1].lower()
    tokens = leaf.replace("shape", "").replace("-", "_").split("_")
    return "1p" in tokens


def weight_rows(model):
    """[(joint, wx, wy, wz, wt)]: the four wtAddMatrix weights a joint."""
    total = sum(model.masses.values())
    rows = []
    for joint in sorted(model.masses):
        m = model.masses[joint] / total
        c = model.centres[joint]
        rows.append((joint, m * c[0], m * c[1], m * c[2], m))
    return rows


def name_in(namespace, leaf):
    return namespace + ":" + leaf if namespace else leaf


# ----------------------------------------------------------- the character

def _root_of_handle(path):
    group = group_of_part(path)
    return root_of(group) if group else None


def character(selection=None):
    """(Character, refusal) the CoM acts on."""
    from maya_scenesetup import skeleton
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    for path in selection:
        root = _root_of_handle(path)
        if root:
            return _character_for(root), ""
    root = skeleton.current_root()
    if not root:
        return None, NO_CHARACTER
    return _character_for(root), ""


def _character_for(root):
    rigs = maya_rigs.rigs()
    rig = maya_rigs.rig_of(root, rigs)
    namespace = rig.namespace if rig else maya_rigs.namespace_of(root)
    label = maya_rigs.label(rig) if rig else root.split("|")[-1]
    return Character(root, rig, namespace, label)


def joints_of(root):
    return [root] + (cmds.listRelatives(root, allDescendents=True,
                                        type="joint", fullPath=True) or [])


def skins_of(char):
    """[(skinCluster, mesh shape long path)] of the character, 1P meshes and
    intermediate shapes left out."""
    clusters = []
    for joint in joints_of(char.root):
        for node in cmds.listConnections(joint, type="skinCluster") or []:
            if node not in clusters:
                clusters.append(node)
    out = []
    for cluster in clusters:
        for name in cmds.skinCluster(cluster, query=True, geometry=True) or []:
            paths = cmds.ls(name, long=True) or []
            if len(paths) != 1 or cmds.objectType(paths[0]) != "mesh":
                continue
            if cmds.getAttr(paths[0] + ".intermediateObject"):
                continue
            if is_first_person(paths[0]):
                continue
            out.append((cluster, paths[0]))
    return out


# --------------------------------------------------------------- sampling

def _om():
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma
    return om, oma


def _matrix(om, plug_name):
    sel = om.MSelectionList()
    sel.add(plug_name)
    plug = sel.getPlug(0)
    return om.MFnMatrixData(plug.asMObject()).matrix()


def _np_matrix(m):
    import numpy as np
    return np.array([[m.getElement(r, c) for c in range(4)] for r in range(4)])


def _mesh_arrays(om, shape):
    """(points (n,3) world, triangles (t,3), face offsets of the triangle
    list, MDagPath) of a mesh as drawn now."""
    import numpy as np
    sel = om.MSelectionList()
    sel.add(shape)
    dag = sel.getDagPath(0)
    fn = om.MFnMesh(dag)
    pts = fn.getPoints(om.MSpace.kWorld)
    points = np.array([(p.x, p.y, p.z) for p in pts])
    counts, verts = fn.getTriangles()
    triangles = np.array(verts, int).reshape(-1, 3)
    offsets = np.concatenate([[0], np.cumsum(np.array(counts, int))[:-1]])
    return points, triangles, offsets, dag


def _skin_weights(om, oma, cluster, dag):
    """(influence long paths, weights (n_verts, n_influences), bind matrices
    {path: 4x4}) of one skinCluster on one mesh."""
    import numpy as np
    sel = om.MSelectionList()
    sel.add(cluster)
    fn = oma.MFnSkinCluster(sel.getDependNode(0))
    influences = fn.influenceObjects()
    paths = [influences[i].fullPathName() for i in range(len(influences))]
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(
        om.MFnMesh(dag).numVertices)
    weights, count = fn.getWeights(dag, comp)
    w = np.array(weights).reshape(-1, count)
    bind = {}
    for i, path in enumerate(paths):
        index = fn.indexForInfluenceObject(influences[i])
        bind[path] = _np_matrix(_matrix(om, "%s.bindPreMatrix[%d]" % (cluster, index)))
    return paths, w, bind


def build_model(char, step=VOXEL, report=None):
    """(Model, info) of the character's body as it stands now."""
    import numpy as np
    om, oma = _om()
    started = time.time()
    meshes = []
    for cluster, shape in skins_of(char):
        points, triangles, offsets, dag = _mesh_arrays(om, shape)
        paths, w, bind = _skin_weights(om, oma, cluster, dag)
        meshes.append((shape, points, triangles, offsets, dag, paths, w, bind))
    if not meshes:
        raise RuntimeError("%s has no skinned mesh to weigh" % char.label)
    all_points = np.concatenate([m[1] for m in meshes])
    all_tris = np.concatenate([m[2] + sum(len(x[1]) for x in meshes[:i])
                               for i, m in enumerate(meshes)])
    lo, hi = all_points.min(axis=0), all_points.max(axis=0)
    grid = massmodel.Grid.around(lo, hi, step)
    inside = massmodel.solid(all_points, all_tris, grid)
    centres = grid.centres()[inside.ravel()]
    t_voxels = time.time() - started
    if report:
        report("%d voxels inside" % len(centres))
    #  each voxel's skin: the closest surface point of any of the meshes
    intersectors = []
    for shape, points, triangles, offsets, dag, paths, w, bind in meshes:
        mi = om.MMeshIntersector()
        mi.create(dag.node(), dag.inclusiveMatrix())
        intersectors.append(mi)
    best = [None] * len(centres)
    best_d = np.full(len(centres), np.inf)
    for mesh_i, mi in enumerate(intersectors):
        points = meshes[mesh_i][1]
        for i, q in enumerate(centres):
            hit = mi.getClosestPoint(om.MPoint(q[0], q[1], q[2]))
            p = hit.point
            #  the intersector answers in the mesh's object space
            wp = om.MPoint(p) * meshes[mesh_i][4].inclusiveMatrix()
            d = (wp.x - q[0]) ** 2 + (wp.y - q[1]) ** 2 + (wp.z - q[2]) ** 2
            if d < best_d[i]:
                best_d[i] = d
                best[i] = (mesh_i, hit.face, hit.triangle, hit.barycentricCoords)
    t_closest = time.time() - started - t_voxels
    #  per voxel: up to K joints and weights
    K = 8
    joints, weights = [], np.zeros((len(centres), K))
    bind_all, world = {}, {}
    for i, (mesh_i, face, tri, bary) in enumerate(best):
        shape, points, triangles, offsets, dag, paths, w, bind = meshes[mesh_i]
        corners = triangles[offsets[face] + tri]
        u, v = bary
        blend = u * w[corners[0]] + v * w[corners[1]] + (1 - u - v) * w[corners[2]]
        top = np.argsort(blend)[::-1][:K]
        top = [k for k in top if blend[k] > 1e-6]
        total = sum(blend[k] for k in top) or 1.0
        joints.append(tuple(paths[k] for k in top))
        for slot, k in enumerate(top):
            weights[i, slot] = blend[k] / total
        for k in top:
            bind_all.setdefault(paths[k], bind[paths[k]])
    for path in bind_all:
        world[path] = _np_matrix(_matrix(om, path + ".worldMatrix[0]"))
    model = massmodel.accumulate(centres, step ** 3, joints, weights,
                                 bind_all, world)
    info = {"voxels": len(centres), "meshes": [m[0] for m in meshes],
            "seconds": time.time() - started, "voxel_seconds": t_voxels,
            "closest_seconds": t_closest, "height": float(hi[1] - lo[1]),
            "low": lo.tolist(), "high": hi.tolist()}
    return model, info


# ---------------------------------------------------------------- network

def _uuid(node):
    return (cmds.ls(node, uuid=True) or [""])[0]


def _tag(node, part):
    if not cmds.attributeQuery(PART, node=node, exists=True):
        cmds.addAttr(node, longName=PART, dataType="string")
    cmds.setAttr(node + "." + PART, part, type="string")


def _curve_shape(parent, points, colour, degree=1):
    curve = cmds.curve(degree=degree, point=points)
    shape = cmds.listRelatives(curve, shapes=True, fullPath=True)[0]
    shape = cmds.parent(shape, parent, shape=True, relative=True)[0]
    cmds.delete(curve)
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *colour)
    cmds.setAttr(shape + ".alwaysDrawOnTop", 1)
    cmds.setAttr(shape + ".lineWidth", 2)
    return shape


def _circle_points(radius, plane, segments=24):
    import math
    out = []
    for k in range(segments + 1):
        a = 2 * math.pi * k / segments
        x, y = radius * math.cos(a), radius * math.sin(a)
        out.append({"xy": (x, y, 0), "yz": (0, x, y), "xz": (x, 0, y)}[plane])
    return out


def _handle(namespace, parent, radius):
    handle = cmds.createNode("transform", name=name_in(namespace, "COM_handle"),
                             parent=parent)
    for plane in ("xy", "yz", "xz"):
        _curve_shape(handle, _circle_points(radius, plane), HANDLE_COLOUR)
    r = radius * 1.6
    for a, b in (((-r, 0, 0), (r, 0, 0)), ((0, -r, 0), (0, r, 0)),
                 ((0, 0, -r), (0, 0, r))):
        _curve_shape(handle, [a, b], HANDLE_COLOUR)
    for attr in ("rx", "ry", "rz", "sx", "sy", "sz", "v"):
        cmds.setAttr(handle + "." + attr, lock=True, keyable=False,
                     channelBox=False)
    _tag(handle, "handle")
    return cmds.ls(handle, long=True)[0]


def _floor_marker(namespace, parent, radius):
    floor = cmds.createNode("transform", name=name_in(namespace, "COM_floor"),
                            parent=parent)
    _curve_shape(floor, _circle_points(radius * 1.4, "xz"), FLOOR_COLOUR)
    r = radius * 2.0
    for a, b in (((-r, 0, 0), (r, 0, 0)), ((0, 0, -r), (0, 0, r))):
        _curve_shape(floor, [a, b], FLOOR_COLOUR)
    for attr in ("rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(floor + "." + attr, lock=True, keyable=False,
                     channelBox=False)
    _tag(floor, "floor")
    return cmds.ls(floor, long=True)[0]


def _trail(namespace, parent, leaf, colour, part):
    xform = cmds.createNode("transform", name=name_in(namespace, leaf),
                            parent=parent)
    cmds.setAttr(xform + ".inheritsTransform", 0)
    shape = cmds.createNode("motionTrailShape", name=name_in(namespace, leaf + "Shape"),
                            parent=xform)
    cmds.setAttr(shape + ".trailColor", *colour)
    cmds.setAttr(shape + ".trailThickness", 2)
    cmds.setAttr(shape + ".showFrameMarkers", 1)
    cmds.setAttr(shape + ".frameMarkerSize", 4)
    cmds.setAttr(shape + ".frameMarkerColor", *colour)
    cmds.setAttr(shape + ".xrayDraw", 1)
    cmds.setAttr(shape + ".increment", 1)
    _tag(xform, part)
    return cmds.ls(xform, long=True)[0]


def create(char, model, info):
    """Build the network for `char` from `model`; returns the group."""
    namespace = char.namespace
    parent = char.rig.group if char.rig else None
    made = []

    def node(kind, leaf, **kw):
        n = cmds.createNode(kind, name=name_in(namespace, leaf), **kw)
        made.append(n)
        return n

    group = cmds.createNode("transform", name=name_in(namespace, "CenterOfMass"),
                            **({"parent": parent} if parent else {}))
    made.append(group)
    cmds.addAttr(group, longName=MARKER, dataType="string")
    cmds.setAttr(group + "." + MARKER, VERSION, type="string")
    cmds.addAttr(group, longName=ROOT_LINK, attributeType="message")
    cmds.connectAttr(char.root + ".message", group + "." + ROOT_LINK)
    for attr, kind, value in (("trail", "bool", 1), ("floor", "bool", 1),
                              ("around", "long", 20)):
        cmds.addAttr(group, longName=attr, attributeType=kind, defaultValue=value)
    cmds.addAttr(group, longName="range", attributeType="enum",
                 enumName="Playback:Around")
    for attr in ("volume", "height"):
        cmds.addAttr(group, longName=attr, attributeType="double")
    cmds.setAttr(group + ".volume", model.volume / 1000.0)    # litres
    cmds.setAttr(group + ".height", info["height"])
    cmds.addAttr(group, longName=NODES, dataType="string")
    for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(group + "." + attr, lock=True, keyable=False)
    group = cmds.ls(group, long=True)[0]

    rows = weight_rows(model)
    sums = []
    for axis, leaf in enumerate(("comWx", "comWy", "comWz", "comWt")):
        wt = node("wtAddMatrix", leaf)
        for i, row in enumerate(rows):
            cmds.connectAttr(row[0] + ".worldMatrix[0]",
                             "%s.wtMatrix[%d].matrixIn" % (wt, i))
            cmds.setAttr("%s.wtMatrix[%d].weightIn" % (wt, i), row[1 + axis])
        pick = node("rowFromMatrix", leaf + "Row")
        cmds.setAttr(pick + ".input", axis)
        cmds.connectAttr(wt + ".matrixSum", pick + ".matrix")
        sums.append(pick)
    total = node("plusMinusAverage", "comSum")
    cmds.setAttr(total + ".operation", 1)
    for i, pick in enumerate(sums):
        for src, dst in (("X", "x"), ("Y", "y"), ("Z", "z")):
            cmds.connectAttr(pick + ".output" + src,
                             "%s.input3D[%d].input3D%s" % (total, i, dst))
    _tag(total, "sum")
    root_row = node("rowFromMatrix", "comRootRow")
    cmds.setAttr(root_row + ".input", 3)
    cmds.connectAttr(char.root + ".worldMatrix[0]", root_row + ".matrix")
    _tag(root_row, "rootRow")

    radius = max(info["height"], 1.0) * HANDLE_SHARE
    handle = _handle(namespace, group, radius)
    to_local = node("multiplyPointByMatrix", "comHandleLocal")
    cmds.connectAttr(total + ".output3D", to_local + ".input")
    cmds.connectAttr(handle + ".parentInverseMatrix[0]", to_local + ".matrix")
    cmds.connectAttr(to_local + ".output", handle + ".translate")

    floor = _floor_marker(namespace, group, radius)
    floor_local = node("multiplyPointByMatrix", "comFloorLocal")
    cmds.connectAttr(total + ".output3Dx", floor_local + ".inputX")
    cmds.connectAttr(root_row + ".outputY", floor_local + ".inputY")
    cmds.connectAttr(total + ".output3Dz", floor_local + ".inputZ")
    cmds.connectAttr(floor + ".parentInverseMatrix[0]", floor_local + ".matrix")
    cmds.connectAttr(floor_local + ".output", floor + ".translate")
    cmds.connectAttr(group + ".floor", floor + ".visibility")

    trail = _trail(namespace, group, "COM_trail", TRAIL_COLOUR, "trail")
    floor_trail = _trail(namespace, group, "COM_floorTrail", FLOOR_TRAIL_COLOUR,
                         "floorTrail")
    cmds.connectAttr(group + ".trail", trail + ".visibility")
    floor_and = node("multDoubleLinear", "comFloorTrailOn")
    cmds.connectAttr(group + ".trail", floor_and + ".input1")
    cmds.connectAttr(group + ".floor", floor_and + ".input2")
    cmds.connectAttr(floor_and + ".output", floor_trail + ".visibility")

    uuids = [_uuid(n) for n in made] + [_uuid(n) for n in
                                        (handle, floor, trail, floor_trail)]
    cmds.setAttr(group + "." + NODES, " ".join(u for u in uuids if u),
                 type="string")
    return group


# ----------------------------------------------------------------- lookup

def find_all():
    """Every CoM group in the scene (long paths)."""
    out = []
    for node in cmds.ls(type="transform", long=True) or []:
        if cmds.attributeQuery(MARKER, node=node, exists=True):
            out.append(node)
    return out


def root_of(group):
    roots = cmds.listConnections(group + "." + ROOT_LINK, source=True,
                                 destination=False, fullNodeName=True) or []
    paths = cmds.ls(roots[0], long=True) if roots else []
    return paths[0] if paths else None


def group_of_part(path):
    """The CoM group a selected part (handle, floor, trail) belongs to."""
    node = path
    for _ in range(4):
        if not node or not cmds.objExists(node):
            return None
        if cmds.objectType(node) != "transform":
            parents = cmds.listRelatives(node, parent=True, fullPath=True)
            node = parents[0] if parents else None
            continue
        if cmds.attributeQuery(MARKER, node=node, exists=True):
            return cmds.ls(node, long=True)[0]
        parents = cmds.listRelatives(node, parent=True, fullPath=True)
        node = parents[0] if parents else None
    return None


def group_for(char):
    for group in find_all():
        if root_of(group) == char.root:
            return group
    return None


def part(group, name):
    """The DAG part `name` ("handle", "floor", "trail", "floorTrail") or the
    DG node ("sum", "rootRow")."""
    for uuid in (cmds.getAttr(group + "." + NODES) or "").split():
        nodes = cmds.ls(uuid, long=True) or []
        if not nodes:
            continue
        n = nodes[0]
        if cmds.attributeQuery(PART, node=n, exists=True) \
                and cmds.getAttr(n + "." + PART) == name:
            return n
    return None


def trail_shape(group, name="trail"):
    xform = part(group, name)
    shapes = cmds.listRelatives(xform, shapes=True, fullPath=True) if xform else []
    return shapes[0] if shapes else None


def mass_joints(group):
    """The joints the sum reads (long paths)."""
    wt = None
    for uuid in (cmds.getAttr(group + "." + NODES) or "").split():
        nodes = cmds.ls(uuid, long=True) or []
        if nodes and cmds.objectType(nodes[0]) == "wtAddMatrix":
            wt = nodes[0]
            break
    if not wt:
        return []
    out = []
    for plug in cmds.listConnections(wt + ".wtMatrix", source=True,
                                     destination=False, plugs=False,
                                     fullNodeName=True) or []:
        paths = cmds.ls(plug, long=True) or []
        if paths and paths[0] not in out:
            out.append(paths[0])
    return out


def remove(group):
    """Delete every node of the network."""
    uuids = (cmds.getAttr(group + "." + NODES) or "").split()
    nodes = []
    for uuid in uuids:
        nodes.extend(cmds.ls(uuid, long=True) or [])
    dg = [n for n in nodes if not cmds.objectType(n, isAType="dagNode")]
    for n in dg:
        if cmds.objExists(n):
            cmds.delete(n)
    if cmds.objExists(group):
        cmds.delete(group)


# ---------------------------------------------------------------- drivers

def drivers(char):
    """The world drivers the CoM tool moves (long paths), in order."""
    from maya_com import dragmath
    out = []
    if char.rig:
        for leaf in dragmath.RIG_DRIVERS:
            paths = cmds.ls(name_in(char.rig.namespace, leaf), long=True) or []
            if len(paths) == 1:
                out.append(paths[0])
        return out
    joints = joints_of(char.root)
    for leaf in dragmath.SKELETON_DRIVERS:
        for joint in joints:
            if joint.split("|")[-1].split(":")[-1] == leaf:
                out.append(joint)
                break
    return out
