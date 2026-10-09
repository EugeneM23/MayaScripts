"""Skin of Manny's first-person cut (Skin_1p) from the third-person mesh (Skin_3p).

Skin_1p is an exact cut of Skin_3p: its faces are the 3P faces whose vertices all lie on the
1P (sources/manny/manny_1p_faces.json). A vertex correspondence comes from the faces (position
and UV of every corner), and the weights are copied through it. Maya API only, so the same
code runs in the live scene and in mayapy.
"""
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

ROUND = 4


def dag_of(name):
    sel = om.MSelectionList()
    sel.add(name)
    return sel.getDagPath(0)


def skin_of(name):
    sel = om.MSelectionList()
    sel.add(name)
    return oma.MFnSkinCluster(sel.getDependNode(0))


def _corners(dag):
    fn = om.MFnMesh(dag)
    pts = fn.getPoints(om.MSpace.kWorld)
    faces = []
    for f in range(fn.numPolygons):
        ks = []
        for k, v in enumerate(fn.getPolygonVertices(f)):
            u, w = fn.getPolygonUV(f, k)
            p = pts[v]
            ks.append(((round(p.x, ROUND), round(p.y, ROUND), round(p.z, ROUND), round(u, 5), round(w, 5)), v))
        faces.append(ks)
    return fn, faces


def vertex_map(dag3, dag1):
    """For every vertex of the 1P mesh, the vertex of the 3P mesh it is. Refuses anything not an exact cut."""
    fn3, faces3 = _corners(dag3)
    fn1, faces1 = _corners(dag1)
    by_face = {}
    for f, ks in enumerate(faces3):
        by_face.setdefault(tuple(sorted(k for k, _ in ks)), []).append(f)
    vmap = [None] * fn1.numVertices
    for ks in faces1:
        cands = by_face.get(tuple(sorted(k for k, _ in ks)))
        if not cands:
            raise ValueError("a face of %s is not a face of %s" % (dag1.partialPathName(), dag3.partialPathName()))
        at = dict((k, v) for k, v in faces3[cands.pop(0)])
        for k, v1 in ks:
            if vmap[v1] is None:
                vmap[v1] = at[k]
            elif vmap[v1] != at[k]:
                raise ValueError("vertex %d maps to two vertices" % v1)
    if None in vmap or len(set(vmap)) != len(vmap):
        raise ValueError("the vertex map is not one to one")
    return vmap


def _all_verts(dag):
    comp = om.MFnSingleIndexedComponent()
    obj = comp.create(om.MFn.kMeshVertComponent)
    comp.addElements(list(range(om.MFnMesh(dag).numVertices)))
    return obj


def weights_of(skin, dag):
    """Dense weights (vertex-major) and the influence names in logical order."""
    names = [d.partialPathName() for d in skin.influenceObjects()]
    w, n = skin.getWeights(dag, _all_verts(dag))
    return w, n, names


def copy_weights(skin3, dag3, skin1, dag1, vmap):
    w3, n3, names3 = weights_of(skin3, dag3)
    names1 = [d.partialPathName() for d in skin1.influenceObjects()]
    at1 = dict((name, i) for i, name in enumerate(names1))
    to1 = [at1[name] for name in names3]
    n1 = len(names1)
    out = [0.0] * (len(vmap) * n1)
    for i, j in enumerate(vmap):
        b3, b1 = j * n3, i * n1
        for k in range(n3):
            out[b1 + to1[k]] = w3[b3 + k]
    skin1.setWeights(dag1, _all_verts(dag1), om.MIntArray(list(range(n1))), om.MDoubleArray(out), False)
    return out, n1


def check_copy(skin3, dag3, skin1, dag1, vmap):
    """Largest difference between the 3P's weights and the 1P's, vertex by vertex, and the largest row-sum error."""
    w3, n3, names3 = weights_of(skin3, dag3)
    w1, n1, names1 = weights_of(skin1, dag1)
    at1 = dict((name, i) for i, name in enumerate(names1))
    worst, sums = 0.0, 0.0
    for i, j in enumerate(vmap):
        row1 = [0.0] * n1
        for k in range(n3):
            row1[at1[names3[k]]] = w3[j * n3 + k]
        got = w1[i * n1:(i + 1) * n1]
        worst = max(worst, max(abs(a - b) for a, b in zip(row1, got)))
        sums = max(sums, abs(sum(got) - 1.0))
    return worst, sums
