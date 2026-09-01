"""maya_meltmorph -- one shape flowing into another as a wave, baked to Alembic.

Two meshes go in, a level-set (signed distance field) blend comes out: at any
point in space the surface is `(1-a)*A + a*B`, where `a` is a scalar FIELD that
sweeps along one axis.  Ahead of the front you see the source, behind it the
target, and in the band between them the material genuinely reforms -- which is
what reads as liquid.  Topology is free to change every frame, so there is no
correspondence to maintain and no blendshape to fight.

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_meltmorph as mm

    print(mm.probe())                       # read-only: what is in the scene
    print(mm.build("armShape", "gunShape")) # graph + output mesh
    print(mm.calibrate())                   # find the live part of the sweep
    print(mm.key_range(0, 20))              # 20 frames of flow
    print(mm.bake())                        # alembic (+ gpu cache)

Everything is plain `maya.cmds`; no Qt, no package.  The module keeps no state
beyond what it can re-read from the scene, so a fresh session can pick up a
graph an earlier one built.

Why the code looks the way it does -- each of these was measured, and getting
any of them wrong produces an EMPTY result with no error message:

* `vnnCompound -addNode` wants `"BifrostGraph,<Namespace::Sub>,<node>"`.  The
  `Namespace::Sub::node` spelling that appears as `nodeType` in Bifrost's own
  graph files is rejected.
* A Maya mesh enters through a port OPTION, not a connection: `pathinfo` with
  the DAG path's `|` turned into `/`.  One path per `Object` port -- two paths
  in one port silently yields nothing.
* Fan-in ports (`merge_volumes.volumes`) cannot be connected to until the child
  exists.  `createInputPort("volumes.volume")` first; children are `volume`,
  `volume1`, `volume2`...
* `Geometry::Converters::volume_to_mesh` is a TRAP: its fan-in accepts the
  child port and the connection, compiles clean, and outputs an empty mesh.
  `contour_dual_marching_cubes` takes a single `volume` and works.
* float3 port defaults must be written `"{0,0,1}"`.  Comma-separated without
  braces, and the per-component form `normal.x`, are both accepted and IGNORED.
* `bifrostGraph -createMayaGeometry` takes the BARE port name, not a path, and
  creates the mesh transform only once geometry actually flows -- so "no new
  mesh appeared" is the cheapest possible diagnostic for an empty graph.
* A published float3 input port becomes the compound attribute `front_pos`
  whose children are `front_pos.x/.y/.z` -- not `front_posX`.
* Vertex ORDER out of the contour is not stable between evaluations, so an
  Alembic can only be verified order-independently (area, bbox, closest point).
"""

import os
import time

import maya.cmds as cmds

# ---------------------------------------------------------------- naming ----
GRAPH = "meltGraph"
GRAPH_SHAPE = "meltGraphShape"
OUT_MESH = "meltMesh"
OUT_PORT = "meltout"
FRONT_PORT = "front_pos"
CLOSED_SUFFIX = "_meltClosed"

# node instance names inside the graph, so a later session can find them
LS_A = "mesh_to_level_set"
LS_B = "mesh_to_level_set1"
MERGE = "merge_volumes"
PLANE = "plane_field"
SCALE = "scale_field"
DILATE = "offset_level_set"
REBUILD1 = "rebuild_level_set"
ERODE = "offset_level_set1"
REBUILD2 = "rebuild_level_set1"
SMOOTH = "smooth_level_set_property"
CONTOUR = "contour_dual_marching_cubes"

ALPHA_BLEND_MODE = "3"          # Geometry::Volume::LevelSetMode
LEVEL_SET_PROPERTY = "voxel_signed_distance"

DEFAULTS = {
    "detail_size": 0.3,         # voxel size, scene units
    "width": 14.0,              # transition band along the sweep axis
    "fillet": 0.2,              # dilate +r / erode -r, welds near-touching bits
    "smooth_iterations": 1,     # keep low: 2 x sd 3 erased a hand's fingers
    "smooth_deviation": 1,      # in VOXELS, so world size = value * detail_size
    "mesh_scale": 1.0,          # contour triangle size relative to the voxel
    "source_hole_radius": 0.0,  # 0 once the mesh is closed by prepare()
    "target_hole_radius": 2.0,
}

AXES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


def _axis_vector(axis, target=None):
    """Resolve `axis` to a unit world-space direction for the wave.

    "x"/"y"/"z"            a world axis
    "localX"/"localY"/"localZ"   that local axis of `target`'s transform
    "local"                the LONGEST local axis of `target`, measured on its
                           own points -- for a weapon that is the direction the
                           thing points, which is what the wave should follow

    A local axis has to be read off the transform's world matrix, not assumed:
    the moment the target is rotated, a world axis sends the wave across the
    model instead of along it.
    """
    import maya.api.OpenMaya as om
    axis = str(axis)
    if axis in AXES:
        return om.MVector(*AXES[axis]).normalize(), axis
    if not target:
        raise RuntimeError("axis %r needs a target transform" % axis)
    tr = target
    if cmds.objectType(tr) == "mesh":
        tr = cmds.listRelatives(tr, parent=True, fullPath=True)[0]
    m = cmds.xform(tr, query=True, matrix=True, worldSpace=True)
    cols = {"x": om.MVector(m[0], m[1], m[2]),
            "y": om.MVector(m[4], m[5], m[6]),
            "z": om.MVector(m[8], m[9], m[10])}
    if axis.lower().startswith("local") and len(axis) == 6:
        k = axis[-1].lower()
        if k not in cols:
            raise RuntimeError("axis %r: expected localX/localY/localZ" % axis)
        return om.MVector(cols[k]).normalize(), axis
    if axis.lower() != "local":
        raise RuntimeError("axis must be x/y/z, localX/localY/localZ or local")
    shape = target if cmds.objectType(target) == "mesh" else \
        (cmds.listRelatives(tr, shapes=True, fullPath=True,
                            noIntermediate=True) or [None])[0]
    sel = om.MSelectionList()
    sel.add(shape)
    pts = om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)
    best, best_span = None, -1.0
    for k, v in cols.items():
        n = om.MVector(v).normalize()
        d = [om.MVector(p.x, p.y, p.z) * n for p in pts]
        span = max(d) - min(d)
        if span > best_span:
            best, best_span = k, span
    return om.MVector(cols[best]).normalize(), "local" + best.upper()


# ------------------------------------------------------------- plumbing ----
def _board():
    """the graph shape, or None"""
    for n in (cmds.ls(type="bifrostGraphShape", long=True) or []):
        if n.split("|")[-1].startswith(GRAPH_SHAPE):
            return n
    return None


def _require_board():
    b = _board()
    if not b:
        raise RuntimeError("no %s in the scene - call build() first" % GRAPH)
    return b


def _add(board, ns, name):
    return cmds.vnnCompound(board, "/",
                            addNode="BifrostGraph,%s,%s" % (ns, name))[0]


def _setv(board, node, port, value):
    cmds.vnnNode(board, "/" + node, setPortDefaultValues=(port, str(value)))


def _getv(board, node, port):
    return cmds.vnnNode(board, "/" + node, queryPortDefaultValues=port)


def _f3(v):
    """float3 port defaults only take the brace form"""
    return "{%g,%g,%g}" % tuple(v)


def _mesh_in(board, port, shape):
    """publish one Maya mesh as an input port; the path uses / not |"""
    cmds.vnnNode(board, "/input", createOutputPort=(port, "Object"),
                 portOptions=('pathinfo={path="%s"'
                              ';channels=*;setOperation=+;active=true'
                              ';normalsPerPoint=true;normalsPerFaceVertex=true'
                              ';normalsPerFace=false}'
                              % cmds.ls(shape, long=True)[0].replace("|", "/")))


def _fanin(board, node, port, child):
    """a fan-in child must exist before vnnConnect will accept it"""
    cmds.vnnNode(board, "/" + node,
                 createInputPort=("%s.%s" % (port, child), "Object"))
    return "/%s.%s.%s" % (node, port, child)


def _long(name):
    got = cmds.ls(name, long=True) or []
    return got[0] if got else None


def _mesh_shape(transform):
    got = cmds.listRelatives(transform, shapes=True, fullPath=True,
                             noIntermediate=True) or []
    return got[0] if got else None


def _settle():
    """Bifrost answers on the DG; nudge time so a read is not stale"""
    t = cmds.currentTime(query=True)
    cmds.dgdirty(allPlugs=True)
    cmds.currentTime(t + 1, update=True)
    cmds.currentTime(t, update=True)
    cmds.refresh(force=True)


def _stats(shape):
    bb = cmds.exactWorldBoundingBox(shape)
    return {"verts": cmds.polyEvaluate(shape, vertex=True),
            "faces": cmds.polyEvaluate(shape, face=True),
            "shells": cmds.polyEvaluate(shape, shell=True),
            "area": round(cmds.polyEvaluate(shape, area=True), 4),
            "bbox": [round(x, 3) for x in bb]}


def _border_edges(shape):
    import maya.api.OpenMaya as om
    sel = om.MSelectionList()
    sel.add(shape)
    it = om.MItMeshEdge(sel.getDagPath(0))
    n = 0
    while not it.isDone():
        if it.onBoundary():
            n += 1
        it.next()
    return n


# ----------------------------------------------------------------- probe ----
def probe():
    """Read-only survey.  Run this first and report it before touching anything.

    A mesh with border edges cannot be voxelised solid: the fill leaks and the
    level set comes out empty.  prepare() is the fix; a big `min_hole_radius`
    is NOT, because a radius large enough to cap a sleeve also welds a hand's
    fingers into a mitten.
    """
    lines = ["scene: %s" % (cmds.file(query=True, sceneName=True) or "<unsaved>"),
             "unit: %s | fps: %s | range: %s..%s"
             % (cmds.currentUnit(query=True, linear=True),
                cmds.currentUnit(query=True, time=True),
                cmds.playbackOptions(query=True, min=True),
                cmds.playbackOptions(query=True, max=True)),
             "meshes:"]
    for m in (cmds.ls(type="mesh", long=True, noIntermediate=True) or []):
        tr = (cmds.listRelatives(m, parent=True, fullPath=True) or [None])[0]
        s = _stats(m)
        lines.append("   %-46s verts=%-7s shells=%-4s border=%-6s vis=%s"
                     % (m, s["verts"], s["shells"], _border_edges(m),
                        cmds.getAttr(tr + ".visibility") if tr else "?"))
        lines.append("        bbox %s" % (s["bbox"],))
    b = _board()
    lines.append("melt graph: %s" % (b or "none"))
    if b:
        lines.append("   output mesh: %s" % (_long(OUT_MESH) or "missing"))
        lines.append("   driven: %s"
                     % bool(cmds.listConnections(_mesh_shape(_long(OUT_MESH))
                                                 + ".inMesh", source=True)
                            if _long(OUT_MESH) else False))
    return "\n".join(lines)


def prepare(shape):
    """Return a hidden, closed, history-free copy of `shape` for voxelising.

    polyCloseBorder caps every border loop (one added face per loop), which is
    what lets the voxeliser run with min_hole_radius 0 and keep small features
    -- fingers, teeth, thin plates -- separate.
    """
    shape = _long(shape)
    if not shape:
        raise RuntimeError("no such shape")
    src_tr = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
    name = src_tr.split("|")[-1].split(":")[-1] + CLOSED_SUFFIX
    if cmds.objExists(name):
        cmds.delete(name)
    dup = cmds.duplicate(src_tr, name=name, returnRootsOnly=True)[0]
    dsh = _mesh_shape(dup)
    before = _border_edges(dsh)
    try:
        cmds.polyCloseBorder(dsh, constructionHistory=False)
    except Exception:
        pass
    cmds.delete(dsh, constructionHistory=True)
    cmds.setAttr(dup + ".visibility", 0)
    return {"name": dup, "shape": _mesh_shape(dup),
            "border_before": before, "border_after": _border_edges(_mesh_shape(dup)),
            "verts": cmds.polyEvaluate(_mesh_shape(dup), vertex=True)}


# ----------------------------------------------------------------- build ----
def _ranges(indices):
    """[1,2,3,7] -> ['1:3', '7'] so a 12000-face list stays a short command"""
    out = []
    run_start = prev = None
    for i in sorted(indices):
        if run_start is None:
            run_start = prev = i
            continue
        if i == prev + 1:
            prev = i
            continue
        out.append("%d:%d" % (run_start, prev) if prev > run_start
                   else str(run_start))
        run_start = prev = i
    if run_start is not None:
        out.append("%d:%d" % (run_start, prev) if prev > run_start
                   else str(run_start))
    return out


def _grow_faces(shape, indices, rings):
    """expand a face set by whole rings, through its vertices"""
    faces = set(indices)
    for _ in range(max(0, rings)):
        comp = ["%s.f[%s]" % (shape, r) for r in _ranges(faces)]
        verts = cmds.polyListComponentConversion(comp, fromFace=True,
                                                 toVertex=True) or []
        back = cmds.polyListComponentConversion(verts, fromVertex=True,
                                                toFace=True) or []
        for f in (cmds.ls(back, flatten=True) or []):
            faces.add(int(f.split("[")[1].rstrip("]")))
    return faces


def split(shape, protected, grow=2):
    """Split a mesh into an untouched `keep` half and a `melt` half.

    `protected` is a face list or the name of an objectSet holding one -- e.g.
    what the animator selected. `keep` is those faces duplicated with their
    ORIGINAL polygons, UVs and shader, so a textured part of the model survives
    a melt that would otherwise voxelise it and throw its UVs away.

    `melt` is the remainder GROWN by `grow` face rings, so its cut edge sits
    inside `keep` rather than butting against it -- coincident edges show as a
    hairline seam, an overlapped one does not. The grown copy is then closed,
    which caps both the cut and whatever holes the model already had.

    The original is hidden, not modified.
    """
    shape = _long(shape)
    if not shape:
        raise RuntimeError("no such shape")
    if isinstance(protected, str) and cmds.objExists(protected) \
            and cmds.objectType(protected) == "objectSet":
        protected = cmds.sets(protected, query=True) or []
    prot = set()
    for f in (cmds.ls(protected, flatten=True) or []):
        prot.add(int(f.split("[")[1].rstrip("]")))
    if not prot:
        raise RuntimeError("no protected faces resolved")
    total = cmds.polyEvaluate(shape, face=True)
    free = set(range(total)) - prot
    if not free:
        raise RuntimeError("everything is protected - nothing left to melt")
    melt_faces = _grow_faces(shape, free, grow)

    src_tr = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
    stem = src_tr.split("|")[-1].split(":")[-1]
    made = {}
    for tag, wanted in (("keep", prot), ("melt", melt_faces)):
        name = "%s_melt%s" % (stem, tag.capitalize())
        if cmds.objExists(name):
            cmds.delete(name)
        dup = cmds.duplicate(src_tr, name=name, returnRootsOnly=True)[0]
        dsh = _mesh_shape(dup)
        drop = set(range(total)) - wanted
        if drop:
            cmds.polyDelFacet(["%s.f[%s]" % (dsh, r) for r in _ranges(drop)],
                              constructionHistory=False)
        cmds.delete(dsh, constructionHistory=True)
        made[tag] = {"name": dup, "shape": _mesh_shape(dup),
                     "faces": cmds.polyEvaluate(_mesh_shape(dup), face=True),
                     "uvSets": cmds.polyUVSet(_mesh_shape(dup), query=True,
                                              allUVSets=True) or []}
    # the melt half must be watertight before it can be voxelised solid
    msh = made["melt"]["shape"]
    made["melt"]["border_before"] = _border_edges(msh)
    try:
        cmds.polyCloseBorder(msh, constructionHistory=False)
    except Exception:
        pass
    cmds.delete(msh, constructionHistory=True)
    made["melt"]["border_after"] = _border_edges(msh)
    cmds.setAttr(made["melt"]["name"] + ".visibility", 0)
    cmds.setAttr(src_tr + ".visibility", 0)
    made["hidden_original"] = src_tr
    made["grown_rings"] = grow
    made["protected_faces"] = len(prot)
    return made


def build(source, target, axis="z", start="max", **params):
    """Build the melt graph.  `source` flows into `target`.

    axis/start say where the wave BEGINS: axis="z", start="max" sends the front
    from the high-Z end toward low Z.  The plane's normal is the axis vector so
    alpha is 1 behind the front (already target) and 0 ahead of it (still
    source) -- which is why source must be volume A and target volume B.
    """
    if axis not in AXES:
        raise RuntimeError("axis must be one of %s" % sorted(AXES))
    p = dict(DEFAULTS)
    unknown = set(params) - set(p)
    if unknown:
        raise RuntimeError("unknown parameter(s): %s" % sorted(unknown))
    p.update(params)

    src = _long(source)
    tgt = _long(target)
    if not src or not tgt:
        raise RuntimeError("source or target shape not found")

    teardown(keep_prepared=True)

    sh = cmds.createNode("bifrostGraphShape", name=GRAPH_SHAPE)
    cmds.sets(sh, edit=True, forceElement="initialShadingGroup")
    tr = cmds.rename(cmds.listRelatives(sh, parent=True, fullPath=True)[0], GRAPH)
    board = _mesh_shape(tr) or cmds.listRelatives(tr, shapes=True,
                                                  fullPath=True)[0]

    _mesh_in(board, "src", src)
    _mesh_in(board, "tgt", tgt)
    cmds.vnnNode(board, "/input",
                 createOutputPort=(FRONT_PORT, "Math::float3"))

    a = _add(board, "Geometry::Converters", "mesh_to_level_set")
    b = _add(board, "Geometry::Converters", "mesh_to_level_set")
    _setv(board, a, "detail_size", p["detail_size"])
    _setv(board, a, "min_hole_radius", p["source_hole_radius"])
    _setv(board, b, "detail_size", p["detail_size"])
    _setv(board, b, "min_hole_radius", p["target_hole_radius"])
    cmds.vnnConnect(board, "/input.src", "/%s.mesh" % a)
    cmds.vnnConnect(board, "/input.tgt", "/%s.mesh" % b)

    mrg = _add(board, "Modeling::Volume", "merge_volumes")
    _setv(board, mrg, "level_set_mode", ALPHA_BLEND_MODE)
    cmds.vnnConnect(board, "/%s.level_set" % a,
                    _fanin(board, mrg, "volumes", "volume"))
    cmds.vnnConnect(board, "/%s.level_set" % b,
                    _fanin(board, mrg, "volumes", "volume1"))

    # the wave: signed distance to a moving plane, divided by the band width
    sign = 1.0 if start == "max" else -1.0
    normal = tuple(c * sign for c in AXES[axis])
    pf = _add(board, "Core::Fields", "plane_field")
    sf = _add(board, "Core::Fields", "scale_field")
    _setv(board, pf, "normal", _f3(normal))
    _setv(board, sf, "scale", _f3([p["width"] if c else 1.0 for c in AXES[axis]]))
    cmds.vnnConnect(board, "/input." + FRONT_PORT, "/%s.position" % pf)
    cmds.vnnConnect(board, "/%s.plane_signed_distance" % pf, "/%s.field" % sf)
    cmds.vnnConnect(board, "/%s.scaled_field" % sf, "/%s.alpha" % mrg)

    dil = _add(board, "Geometry::Volume", "offset_level_set")
    rb1 = _add(board, "Geometry::Volume", "rebuild_level_set")
    ero = _add(board, "Geometry::Volume", "offset_level_set")
    rb2 = _add(board, "Geometry::Volume", "rebuild_level_set")
    smo = _add(board, "Geometry::Volume", "smooth_level_set_property")
    ctr = _add(board, "Geometry::Converters", "contour_dual_marching_cubes")
    _setv(board, dil, "offset", p["fillet"])
    _setv(board, ero, "offset", -p["fillet"])
    _setv(board, smo, "iterations", p["smooth_iterations"])
    _setv(board, smo, "voxel_standard_deviation", p["smooth_deviation"])
    _setv(board, smo, "voxel_filter_width", p["smooth_deviation"])
    _setv(board, ctr, "detail_size_scale", p["mesh_scale"])
    chain = [("/%s.out_volume" % mrg, "/%s.level_set" % dil),
             ("/%s.out_level_set" % dil, "/%s.volume" % rb1),
             ("/%s.rebuilt_volume" % rb1, "/%s.level_set" % ero),
             ("/%s.out_level_set" % ero, "/%s.volume" % rb2),
             ("/%s.rebuilt_volume" % rb2, "/%s.volume" % smo),
             ("/%s.out_volume" % smo, "/%s.volume" % ctr)]
    for a_, b_ in chain:
        cmds.vnnConnect(board, a_, b_)
    cmds.vnnNode(board, "/output", createInputPort=(OUT_PORT, "Object"))
    cmds.vnnConnect(board, "/%s.mesh" % ctr, "/output." + OUT_PORT)

    # remember the sweep geometry on the board so a later session can read it.
    # the source paths are stored explicitly because
    # `vnnNode -queryPortMetaDataValue (port, "pathinfo")` answers EMPTY --
    # measured, so there is no reading them back off the port.
    for attr, value in (("meltAxis", axis), ("meltStart", start),
                        ("meltSource", src), ("meltTarget", tgt)):
        if not cmds.attributeQuery(attr, node=board, exists=True):
            cmds.addAttr(board, longName=attr, dataType="string")
        cmds.setAttr(board + "." + attr, value, type="string")
    for attr, value in (("meltWidth", p["width"]),):
        if not cmds.attributeQuery(attr, node=board, exists=True):
            cmds.addAttr(board, longName=attr, attributeType="double")
        cmds.setAttr(board + "." + attr, value)

    set_front(_extent(axis)[1] + p["width"], board=board)
    before = set(cmds.ls(type="mesh", long=True) or [])
    cmds.bifrostGraph(board, createMayaGeometry=OUT_PORT)
    _settle()
    fresh = [m for m in (cmds.ls(type="mesh", long=True) or [])
             if m not in before]
    if not fresh:
        raise RuntimeError("the graph produced no geometry - check that both "
                           "meshes are closed (probe) and that detail_size is "
                           "not finer than the machine can carry")
    out = cmds.rename(cmds.listRelatives(fresh[0], parent=True,
                                         fullPath=True)[0], OUT_MESH)
    return {"board": board, "mesh": _mesh_shape(_long(out)),
            "axis": axis, "start": start, "params": p,
            "stats": _stats(_mesh_shape(_long(out)))}


def _extent(axis, board=None):
    """min/max of both source meshes along the sweep axis, in world"""
    board = board or _require_board()
    i = "xyz".index(axis)
    lo, hi = None, None
    for attr in ("meltSource", "meltTarget"):
        path = cmds.getAttr(board + "." + attr)
        if not path or not cmds.objExists(path):
            continue
        bb = cmds.exactWorldBoundingBox(path)
        lo = bb[i] if lo is None else min(lo, bb[i])
        hi = bb[i + 3] if hi is None else max(hi, bb[i + 3])
    if lo is None:
        raise RuntimeError("cannot read the source extents from the graph")
    return lo, hi


def set_front(f, board=None):
    """Park the front at world coordinate `f` along the sweep axis.

    The field is `(p.n - f)/W` because scale_field divides the plane field, so
    the plane itself has to sit at `(f - W/2)/W`.
    """
    board = board or _require_board()
    axis = cmds.getAttr(board + ".meltAxis")
    width = cmds.getAttr(board + ".meltWidth")
    i = "xyz".index(axis)
    v = [0.0, 0.0, 0.0]
    v[i] = (f - width / 2.0) / width
    cmds.setAttr(board + "." + FRONT_PORT, v[0], v[1], v[2], type="double3")
    return f


# ------------------------------------------------------------- calibrate ----
def calibrate(samples=24, board=None):
    """Find the part of the sweep that actually changes the shape.

    An SDF alpha blend shows nothing until the incoming shape's negative
    distance beats the outgoing shape's positive one, so the ends of a
    naive sweep are dead frames.  Measured on a hand-to-crossbow morph:
    the first three and last two frames of a 97..22 sweep were identical.
    This walks the whole span, notes where the output stops matching the
    pure source and starts matching the pure target, and returns that
    live range for key_range() to use.
    """
    board = board or _require_board()
    mesh = _mesh_shape(_long(OUT_MESH))
    if not mesh:
        raise RuntimeError("no %s - call build() first" % OUT_MESH)
    axis = cmds.getAttr(board + ".meltAxis")
    width = cmds.getAttr(board + ".meltWidth")
    lo, hi = _extent(axis, board)
    far, near = hi + width * 2.0, lo - width * 2.0

    set_front(far, board)
    _settle()
    pure_src = _stats(mesh)
    set_front(near, board)
    _settle()
    pure_tgt = _stats(mesh)

    def same(a, b):
        return a["verts"] == b["verts"] and abs(a["area"] - b["area"]) < 0.01

    rows = []
    last_src, first_tgt = far, near
    for i in range(samples + 1):
        f = far + (near - far) * i / float(samples)
        set_front(f, board)
        _settle()
        s = _stats(mesh)
        is_src, is_tgt = same(s, pure_src), same(s, pure_tgt)
        if is_src:
            last_src = f
        if is_tgt and first_tgt == near:
            first_tgt = f
        rows.append((round(f, 2), s["verts"], s["area"], is_src, is_tgt))
    if first_tgt == near:
        first_tgt = near
    return {"axis": axis, "extent": (round(lo, 2), round(hi, 2)),
            "live_range": (round(last_src, 2), round(first_tgt, 2)),
            "pure_source": pure_src, "pure_target": pure_tgt, "scan": rows}


def key_range(first, last, front_from=None, front_to=None, board=None):
    """Key the front over frames [first, last].  Defaults to calibrate()'s range."""
    board = board or _require_board()
    if front_from is None or front_to is None:
        live = calibrate(board=board)["live_range"]
        front_from = live[0] if front_from is None else front_from
        front_to = live[1] if front_to is None else front_to
    axis = cmds.getAttr(board + ".meltAxis")
    width = cmds.getAttr(board + ".meltWidth")
    i = "xyz".index(axis)
    plug = "%s.%s.%s" % (board, FRONT_PORT, "xyz"[i])
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        try:
            cmds.cutKey(plug, clear=True)
        except Exception:
            pass
        for f, val in ((first, front_from), (last, front_to)):
            cmds.setKeyframe(plug, time=f,
                             value=(val - width / 2.0) / width)
        cmds.keyTangent(plug, edit=True, itt="linear", ott="linear")
    finally:
        cmds.autoKeyframe(state=auto)
    return {"frames": (first, last), "front": (front_from, front_to),
            "per_frame": round((front_from - front_to) / float(last - first), 3),
            "plug": plug}


def tune(board=None, **params):
    """Change parameters on a built graph.  Same names as build()."""
    board = board or _require_board()
    p = dict(DEFAULTS)
    unknown = set(params) - set(p)
    if unknown:
        raise RuntimeError("unknown parameter(s): %s" % sorted(unknown))
    applied = {}
    for k, v in params.items():
        if k == "detail_size":
            _setv(board, LS_A, "detail_size", v)
            _setv(board, LS_B, "detail_size", v)
        elif k == "source_hole_radius":
            _setv(board, LS_A, "min_hole_radius", v)
        elif k == "target_hole_radius":
            _setv(board, LS_B, "min_hole_radius", v)
        elif k == "fillet":
            _setv(board, DILATE, "offset", v)
            _setv(board, ERODE, "offset", -v)
        elif k == "smooth_iterations":
            _setv(board, SMOOTH, "iterations", v)
        elif k == "smooth_deviation":
            _setv(board, SMOOTH, "voxel_standard_deviation", v)
            _setv(board, SMOOTH, "voxel_filter_width", v)
        elif k == "mesh_scale":
            _setv(board, CONTOUR, "detail_size_scale", v)
        elif k == "width":
            axis = cmds.getAttr(board + ".meltAxis")
            _setv(board, SCALE, "scale",
                  _f3([v if c else 1.0 for c in AXES[axis]]))
            cmds.setAttr(board + ".meltWidth", v)
        applied[k] = v
    _settle()
    mesh = _mesh_shape(_long(OUT_MESH))
    return {"applied": applied, "stats": _stats(mesh) if mesh else None}


# -------------------------------------------------------------- baking ----
def bake(first=None, last=None, path=None, gpu_cache=True, verify_frames=3,
         board=None):
    """Export the output mesh to Alembic and switch the scene onto the cache.

    Alembic stores topology per sample, which is exactly what a contour
    produces, so nothing is approximated.  Verification is order INDEPENDENT
    (counts, area, bbox, closest-point): the contour's vertex order is not
    stable between evaluations, and comparing vertex i to vertex i reports
    metres of error on geometry that is in fact identical.
    """
    board = board or _require_board()
    mesh_tr = _long(OUT_MESH)
    mesh = _mesh_shape(mesh_tr)
    if not mesh:
        raise RuntimeError("no %s to bake" % OUT_MESH)
    for plug in ("AbcExport", "AbcImport"):
        if not cmds.pluginInfo(plug, query=True, loaded=True):
            cmds.loadPlugin(plug)
    if first is None:
        first = int(cmds.playbackOptions(query=True, min=True))
    if last is None:
        last = int(cmds.playbackOptions(query=True, max=True))

    if path is None:
        scene = cmds.file(query=True, sceneName=True)
        if not scene:
            raise RuntimeError("save the scene first, or pass path=")
        folder = os.path.join(os.path.dirname(scene), "cache",
                              "alembic").replace("\\", "/")
        if not os.path.isdir(folder):
            os.makedirs(folder)
        path = _next_version(
            folder, os.path.splitext(os.path.basename(scene))[0] + "_melt")

    if cmds.listConnections(mesh + ".inMesh", source=True) is None:
        raise RuntimeError("%s is not driven - reconnect the graph before "
                           "baking" % OUT_MESH)

    ref = {}
    step = max(1, (last - first) // max(1, verify_frames - 1))
    check = list(range(first, last + 1, step))[:verify_frames]
    for f in check:
        cmds.currentTime(f, update=True)
        cmds.refresh(force=True)
        ref[f] = _stats(mesh)

    released = _release_cache_files(path)

    # Force synchronous evaluation for the export.  Left async, the board hands
    # AbcExport its LAST computed mesh and starts the new one in the background,
    # so the written samples fall progressively further behind as the mesh gets
    # heavier -- measured: frames 5..12 exact, then a lag growing 1, 2, 3, 4
    # frames with samples repeating, on a mesh going 15k -> 32k verts.  A
    # constant offset or an fps mismatch cannot produce a GROWING lag; that is
    # the tell.
    async_was = None
    try:
        async_was = cmds.bifrostGraph(board, query=True, enableAsync=True)
    except Exception:
        pass
    try:
        cmds.bifrostGraph(board, enableAsync=0)
    except Exception as e:
        print("maya_meltmorph: could not disable async evaluation: %s" % e)
    # and prime every frame so nothing is still in flight when the export starts
    for f in range(first, last + 1):
        cmds.currentTime(f, update=True)
        cmds.polyEvaluate(mesh, vertex=True)
    cmds.currentTime(first, update=True)

    start = time.time()
    try:
        cmds.AbcExport(jobArg="-frameRange %d %d -dataFormat ogawa -worldSpace"
                              " -stripNamespaces -root %s -file %s"
                              % (first, last, mesh_tr, path))
    finally:
        if async_was is not None:
            try:
                cmds.bifrostGraph(board, enableAsync=1 if async_was else 0)
            except Exception:
                pass
    export_time = time.time() - start
    if not os.path.isfile(path):
        raise RuntimeError("no alembic was written to %s" % path)

    before = set(cmds.ls(cmds.ls(), uuid=True) or [])
    cmds.AbcImport(path, mode="import")
    new = cmds.ls(list(set(cmds.ls(cmds.ls(), uuid=True) or []) - before),
                  long=True)
    cache_tr = None
    for n in new:
        if cmds.objectType(n) == "mesh":
            cache_tr = cmds.rename(cmds.listRelatives(n, parent=True,
                                                      fullPath=True)[0],
                                   OUT_MESH + "Cache")
            break
    cache = _mesh_shape(_long(cache_tr)) if cache_tr else None

    # a full per-frame count sweep is nearly free and catches a drifting export
    # that a three-frame spot check can miss
    sweep = []
    for f in range(first, last + 1):
        cmds.currentTime(f, update=True)
        cmds.refresh(force=True)
        sv = cmds.polyEvaluate(mesh, vertex=True)
        cv = cmds.polyEvaluate(cache, vertex=True) if cache else None
        sweep.append({"frame": f, "sim": sv, "cache": cv, "match": sv == cv})
    drift = [s["frame"] for s in sweep if not s["match"]]

    checks = []
    for f in check:
        cmds.currentTime(f, update=True)
        cmds.refresh(force=True)
        c = _stats(cache) if cache else {}
        worst = _closest_point_error(mesh, cache) if cache else None
        checks.append({"frame": f, "sim": ref[f], "cache": c,
                       "worst_distance": worst,
                       "match": bool(cache and c["verts"] == ref[f]["verts"]
                                     and abs(c["area"] - ref[f]["area"]) < 0.01
                                     and c["bbox"] == ref[f]["bbox"]
                                     and (worst or 0) < 1e-4)})

    if drift:
        # AbcExport in Maya 2027 does not faithfully round-trip a mesh whose
        # vertex count changes per frame: reproduced on a polyCube with a keyed
        # subdivision count (nothing to evaluate, no Bifrost), identical under
        # -dataFormat/-worldSpace/-stripNamespaces/-step and under sub-frame
        # steps.  21 frames came back mapped onto 16 archive samples: exact for
        # the first eight, then progressively behind with repeats.  Do not let
        # a silently wrong cache look like a success.
        print("maya_meltmorph: *** THE ALEMBIC IS NOT FAITHFUL *** %d of %d "
              "frames differ from the sim (%s). AbcExport under-samples a mesh "
              "whose topology changes per frame. Do not ship this cache; keep "
              "the live graph, or bake a container that survives varying "
              "topology." % (len(drift), last - first + 1, drift))

    gpu = None
    if gpu_cache:
        folder = os.path.dirname(path)
        stem = os.path.splitext(os.path.basename(path))[0] + "_gpu"
        if not cmds.pluginInfo("gpuCache", query=True, loaded=True):
            cmds.loadPlugin("gpuCache")
        cmds.gpuCache(mesh_tr, startTime=first, endTime=last, optimize=True,
                      optimizationThreshold=40000, writeMaterials=False,
                      dataFormat="ogawa", directory=folder, fileName=stem)
        gpu = "%s/%s.abc" % (folder, stem)
        if os.path.isfile(gpu):
            sh = cmds.createNode("gpuCache", name=OUT_MESH + "GpuShape")
            cmds.setAttr(sh + ".cacheFileName", gpu, type="string")
            gpu_tr = cmds.rename(cmds.listRelatives(sh, parent=True,
                                                    fullPath=True)[0],
                                 OUT_MESH + "Gpu")
            # hidden by default: the alembic MESH is the general-purpose result
            # (it renders, it can be edited), the gpu cache is a scrub proxy.
            # Leaving both on puts two copies of the shape in the viewport.
            cmds.setAttr(gpu_tr + ".visibility", 0)

    # stop the graph evaluating: nothing pulls the output any more
    src = cmds.listConnections(mesh + ".inMesh", source=True,
                               destination=False, plugs=True) or []
    if src:
        cmds.disconnectAttr(src[0], mesh + ".inMesh")
    cmds.setAttr(mesh_tr + ".visibility", 0)
    cmds.currentTime(first, update=True)

    return {"alembic": path, "mb": round(os.path.getsize(path) / 1048576.0, 2),
            "export_seconds": round(export_time, 1),
            "gpu_cache": gpu, "cache_mesh": cache, "released": released,
            "frames": (first, last),
            "verified": all(c["match"] for c in checks) and not drift,
            "drifted_frames": drift, "sweep": sweep,
            "checks": checks, "relink": "%s -> %s.inMesh"
            % (src[0] if src else "<bifrostGeoToMaya>.mayaMesh[0]", mesh)}


def _next_version(folder, stem):
    """Never overwrite an alembic: pick `<stem>_v001.abc`, `_v002`, ...

    Once Maya has READ an alembic this session it keeps an internal archive
    handle on that path, and AbcExport then refuses with a bare "Can't write to
    file" -- measured with no `AlembicNode`, `gpuCache` or `cacheFile` left in
    the scene at all, and with plain `open(path, "r+b")` from inside the same
    Maya succeeding.  So the handle is Maya's own and there is nothing to
    delete; versioning sidesteps it, and it keeps earlier takes for comparison,
    which is what a cache folder is for anyway.
    """
    n = 1
    while True:
        candidate = "%s/%s_v%03d.abc" % (folder, stem, n)
        if not os.path.exists(candidate):
            return candidate
        n += 1


def _release_cache_files(*paths):
    """Delete cache reader nodes pointing at these files, to keep the scene tidy.

    An `AlembicNode` is not a DAG node, so deleting the mesh an import created
    leaves the reader behind.  This is housekeeping, NOT the defence against
    "Can't write to file" -- see `_next_version` for that.
    """
    wanted = {os.path.normcase(os.path.abspath(p)) for p in paths if p}
    for p in list(wanted):
        wanted.add(os.path.normcase(os.path.abspath(
            os.path.splitext(p)[0] + "_gpu.abc")))
    killed = []
    for node_type, attrs in (("AlembicNode", ("abc_File", "fileName")),
                             ("gpuCache", ("cacheFileName",))):
        for n in (cmds.ls(type=node_type) or []):
            for a in attrs:
                if not cmds.attributeQuery(a, node=n, exists=True):
                    continue
                try:
                    got = cmds.getAttr("%s.%s" % (n, a))
                except Exception:
                    continue
                if got and os.path.normcase(os.path.abspath(got)) in wanted:
                    parents = cmds.listRelatives(n, parent=True,
                                                 fullPath=True) or []
                    for target in ([n] + parents):
                        if cmds.objExists(target):
                            try:
                                cmds.delete(target)
                                killed.append(target)
                            except Exception:
                                pass
                    break
    return killed


def _closest_point_error(a_shape, b_shape):
    """worst distance from b's vertices to a's surface; order independent"""
    import maya.api.OpenMaya as om
    s1 = om.MSelectionList()
    s1.add(a_shape)
    target = om.MFnMesh(s1.getDagPath(0))
    s2 = om.MSelectionList()
    s2.add(b_shape)
    worst = 0.0
    for q in om.MFnMesh(s2.getDagPath(0)).getPoints(om.MSpace.kWorld):
        cp = target.getClosestPoint(om.MPoint(q), om.MSpace.kWorld)[0]
        d = (om.MVector(cp) - om.MVector(q)).length()
        if d > worst:
            worst = d
    return round(worst, 9)


def relink(board=None):
    """Reconnect the graph to the output mesh so the sim is live again."""
    board = board or _require_board()
    mesh = _mesh_shape(_long(OUT_MESH))
    conv = [n for n in (cmds.ls(type="bifrostGeoToMaya") or [])
            if cmds.listConnections(n + ".bifrostGeo", source=True,
                                    destination=False)]
    if not mesh or not conv:
        raise RuntimeError("nothing to relink")
    cmds.connectAttr(conv[-1] + ".mayaMesh[0]", mesh + ".inMesh", force=True)
    cmds.setAttr(_long(OUT_MESH) + ".visibility", 1)
    _settle()
    return {"mesh": mesh, "stats": _stats(mesh)}


def teardown(keep_prepared=False, keep_cache=True):
    """Remove what the tool built.  Caches on disk are never touched."""
    killed = []
    names = [GRAPH + "*", OUT_MESH]
    if not keep_cache:
        names += [OUT_MESH + "Cache*", OUT_MESH + "Gpu*"]
    if not keep_prepared:
        names.append("*" + CLOSED_SUFFIX)
    for pat in names:
        for n in (cmds.ls(pat, long=True) or []):
            if cmds.objExists(n):
                try:
                    cmds.delete(n)
                    killed.append(n)
                except Exception:
                    pass
    for n in (cmds.ls(type="bifrostGeoToMaya") or []):
        if cmds.objExists(n) and not cmds.listConnections(n + ".bifrostGeo",
                                                          source=True,
                                                          destination=False):
            cmds.delete(n)
            killed.append(n)
    return killed
