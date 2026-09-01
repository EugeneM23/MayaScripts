"""Joints on the vertices of the selected geometry.

Test-mode tool, deliberately minimal (the project's spec/TDD pipeline is
skipped on purpose): a small window with a minimum-distance field and a
Create button. Select geometry, press Create, get one joint per vertex --
except that a vertex closer than the minimum distance to an already placed
joint gets no joint of its own. Every vertex joint is a direct child of one
root joint at the world origin -- the skeleton root an Unreal export expects.
With Bind skin on, every mesh gets a rigid skinCluster: each vertex weighted
1.0 to its nearest created joint, so a cluster of close vertices rides one
bone. An already skinned mesh is left alone and named in the status line.

Run:
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_geobones; maya_geobones.show()
"""

import math

import maya.cmds as cmds

WINDOW = "geoBonesWindow"
ROOT = "geoBones_root"
JOINT_PREFIX = "geoBone"

_field = None
_bind_box = None
_status = None


# ---------------------------------------------------------------- pure logic

def thin_points(points, min_dist):
    """Greedy thinning: keep a point only when no already-kept point is
    closer than min_dist; the first point wins. Grid hash with cell size
    min_dist, so only the 27 neighbouring cells are searched."""
    if min_dist <= 0.0:
        return list(points)
    inv = 1.0 / min_dist
    d2 = min_dist * min_dist
    grid = {}
    kept = []
    for p in points:
        cell = (int(math.floor(p[0] * inv)),
                int(math.floor(p[1] * inv)),
                int(math.floor(p[2] * inv)))
        if not _crowded(p, cell, grid, d2):
            kept.append(p)
            grid.setdefault(cell, []).append(p)
    return kept


def _crowded(p, cell, grid, d2):
    cx, cy, cz = cell
    for gx in (cx - 1, cx, cx + 1):
        for gy in (cy - 1, cy, cy + 1):
            for gz in (cz - 1, cz, cz + 1):
                for q in grid.get((gx, gy, gz), ()):
                    dx = p[0] - q[0]
                    dy = p[1] - q[1]
                    dz = p[2] - q[2]
                    if dx * dx + dy * dy + dz * dz < d2:
                        return True
    return False


def assign_owners(points, kept, min_dist):
    """Index into kept of the nearest kept point, one per point. Thinning
    guarantees a kept point within min_dist of every point, so the 27
    neighbouring cells hold every candidate; brute force is the paranoid
    fallback."""
    if min_dist <= 0.0:
        return list(range(len(points)))
    inv = 1.0 / min_dist
    grid = {}
    for idx, k in enumerate(kept):
        cell = (int(math.floor(k[0] * inv)),
                int(math.floor(k[1] * inv)),
                int(math.floor(k[2] * inv)))
        grid.setdefault(cell, []).append(idx)
    owners = []
    for p in points:
        cx = int(math.floor(p[0] * inv))
        cy = int(math.floor(p[1] * inv))
        cz = int(math.floor(p[2] * inv))
        best = None
        best_d2 = None
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for gz in (cz - 1, cz, cz + 1):
                    for idx in grid.get((gx, gy, gz), ()):
                        k = kept[idx]
                        dx = p[0] - k[0]
                        dy = p[1] - k[1]
                        dz = p[2] - k[2]
                        d2 = dx * dx + dy * dy + dz * dz
                        if best_d2 is None or d2 < best_d2:
                            best = idx
                            best_d2 = d2
        if best is None:
            best = min(range(len(kept)),
                       key=lambda i: sum((p[a] - kept[i][a]) ** 2
                                         for a in range(3)))
        owners.append(best)
    return owners


# ---------------------------------------------------------------- scene side

def selected_meshes():
    """Mesh shapes of the current selection; objectsOnly folds a component
    selection (vertices/faces) back to its shape."""
    shapes = []
    for node in cmds.ls(selection=True, long=True, objectsOnly=True) or []:
        if cmds.objectType(node, isAType="mesh"):
            found = [node]
        else:
            found = cmds.listRelatives(node, shapes=True, fullPath=True,
                                       type="mesh") or []
        for shape in found:
            if cmds.getAttr(shape + ".intermediateObject"):
                continue
            if shape not in shapes:
                shapes.append(shape)
    return shapes


def mesh_points(shape):
    """World position of every vertex -- one xform call per mesh."""
    if not cmds.polyEvaluate(shape, vertex=True):
        return []
    flat = cmds.xform(shape + ".vtx[*]", query=True, worldSpace=True,
                      translation=True)
    return [tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)]


def create_joints(points, min_dist):
    """One joint per point, all direct children of a fresh root joint at
    the world origin. Radius follows the spacing so a dense cloud does not
    draw as one blob."""
    radius = min_dist * 0.5 if min_dist > 0 else 1.0
    cmds.select(clear=True)
    root = cmds.joint(name=ROOT, position=(0.0, 0.0, 0.0), radius=radius)
    joints = []
    for i, p in enumerate(points, 1):
        cmds.select(root)
        j = cmds.joint(name="%s_%d" % (JOINT_PREFIX, i),
                       position=p, radius=radius)
        joints.append(cmds.ls(j, long=True)[0])
    return root, joints


def existing_skin(shape):
    """The skinCluster already deforming the shape, or None."""
    history = cmds.listHistory(shape, pruneDagObjects=True) or []
    clusters = cmds.ls(history, type="skinCluster")
    return clusters[0] if clusters else None


def bind_skin(shape, joints, owners):
    """Rigid bind: every vertex fully weighted to its owner joint."""
    skin = cmds.skinCluster(joints + [shape], toSelectedBones=True,
                            maximumInfluences=1, name="geoBones_skin")[0]
    by_owner = {}
    for vtx, owner in enumerate(owners):
        by_owner.setdefault(owner, []).append(vtx)
    for owner, verts in by_owner.items():
        cmds.skinPercent(skin, _vtx_components(shape, verts),
                         transformValue=[(joints[owner], 1.0)])
    return skin


def _vtx_components(shape, indices):
    """Consecutive vertex indices folded into vtx[a:b] ranges."""
    comps = []
    start = prev = None
    for i in sorted(indices):
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            comps.append(_vtx_range(shape, start, prev))
            start = prev = i
    if start is not None:
        comps.append(_vtx_range(shape, start, prev))
    return comps


def _vtx_range(shape, a, b):
    if a == b:
        return "%s.vtx[%d]" % (shape, a)
    return "%s.vtx[%d:%d]" % (shape, a, b)


# ------------------------------------------------------------------- window

def _say(message):
    if _status and cmds.text(_status, exists=True):
        cmds.text(_status, edit=True, label=message)
    print("geobones: " + message)


def _create_pressed(*_):
    try:
        min_dist = cmds.floatFieldGrp(_field, query=True, value1=True)
        bind = cmds.checkBox(_bind_box, query=True, value=True)
        meshes = selected_meshes()
        if not meshes:
            _say("Select a mesh first.")
            return
        per_mesh = [(shape, mesh_points(shape)) for shape in meshes]
        points = [p for _, pts in per_mesh for p in pts]
        if not points:
            _say("The selection has no vertices.")
            return
        kept = thin_points(points, min_dist)
        bound = 0
        skipped = []
        cmds.undoInfo(openChunk=True)
        try:
            root, joints = create_joints(kept, min_dist)
            if bind:
                owners = assign_owners(points, kept, min_dist)
                offset = 0
                for shape, pts in per_mesh:
                    own = owners[offset:offset + len(pts)]
                    offset += len(pts)
                    if not pts:
                        continue
                    if existing_skin(shape):
                        skipped.append(shape.split("|")[-1])
                        continue
                    bind_skin(shape, joints, own)
                    bound += 1
        finally:
            cmds.undoInfo(closeChunk=True)
        cmds.select(root)
        message = ("%s + %d joints from %d vertices, %d skipped as too close."
                   % (root, len(joints), len(points),
                      len(points) - len(kept)))
        if bound:
            message += " Skin bound."
        if skipped:
            message += (" Already skinned, left alone: %s."
                        % ", ".join(skipped))
        _say(message)
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def show():
    global _field, _bind_box, _status
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="Geo Bones", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))
    cmds.text(label="Select geometry, press Create - a joint per vertex.",
              align="left")
    _field = cmds.floatFieldGrp(
        label="Min distance", value1=1.0, precision=3,
        annotation="Vertices closer than this to an already placed joint "
                   "get no joint of their own.")
    _bind_box = cmds.checkBox(
        label="Bind skin", value=True,
        annotation="Skin each mesh to the new joints: every vertex rides "
                   "its nearest joint with weight 1.")
    cmds.button(label="Create", height=34, command=_create_pressed)
    _status = cmds.text(label="", align="left")
    cmds.separator(height=4, style="none")
    cmds.showWindow(WINDOW)
