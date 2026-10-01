"""The body's mass, from its mesh and its skin. numpy only, no Maya.

The animator chose «из меша и скина»: every joint's mass is the volume of the
body its skin weights give it. Measured on the shipped assets (2026-10-01) the
meshes are open and overlap - Manny's Skin_3p is 45 shells with 5142 border
edges, the Creep five meshes with the arms open at the shoulder, the Orc D
cloth layered over the skin - so a per-surface volume would leak through the
holes and count every overlap twice. The body here is therefore the UNION of
the shells, each closed by fan caps over its border loops, sampled on a voxel
grid:

- `welded` rejoins a mesh split along its normal seams (Unreal's are, every
  hard edge a border) so a shell is a shell;
- `solid` is ray parity per closed shell along X, Y and Z, a majority vote of
  the three, OR-ed over the shells - a box inside a box, or a vest over a
  torso, is counted once;
- `accumulate` skins each voxel with the weights of its closest surface point
  and finds its rest point through the blended skin matrix, so a joint gets a
  mass m_j and a centre c_j in its own space, and at ANY frame

      CoM = Σ m_j (c_j · M_j) / Σ m_j

  exactly, for linear skinning (`com` is that formula, the reference the DG
  network is checked against).

Maya's matrices are row-vector (a point is p · M), and so are these.
"""

import collections

import numpy as np

#  The grid's offset off the lattice of whole steps, in steps: irrational-ish
#  fractions, so a ray never runs exactly through a vertex or an edge of a
#  model whose numbers are round.
JITTER = (0.37, 0.61, 0.23)

#  Positions this close are one vertex (model units, cm).
WELD = 1e-4

Model = collections.namedtuple("Model", "masses centres volume")


# ------------------------------------------------------------------ topology

def welded(points, triangles, tol=WELD):
    """(points, triangles) with coincident vertices merged and the triangles
    that collapsed dropped."""
    points = np.asarray(points, float)
    triangles = np.asarray(triangles, int).reshape(-1, 3)
    if not len(points):
        return points.reshape(0, 3), triangles
    key = np.round(points / tol).astype(np.int64)
    _, first, inverse = np.unique(key, axis=0, return_index=True,
                                  return_inverse=True)
    inverse = inverse.ravel()
    tris = inverse[triangles]
    keep = ((tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2])
            & (tris[:, 0] != tris[:, 2]))
    return points[first], tris[keep]


def _edges(triangles):
    t = np.asarray(triangles, int).reshape(-1, 3)
    return np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])


def border_loops(triangles):
    """Ordered vertex loops of the edges only one triangle uses."""
    e = _edges(triangles)
    if not len(e):
        return []
    key = np.sort(e, axis=1)
    _, inverse, counts = np.unique(key, axis=0, return_inverse=True,
                                   return_counts=True)
    once = counts[inverse.ravel()] == 1
    outgoing = {}
    for a, b in e[once]:
        outgoing.setdefault(int(a), []).append(int(b))
    total = int(once.sum())
    loops = []
    for start in sorted(outgoing):
        while outgoing.get(start):
            loop, cur = [start], start
            while len(loop) <= total:
                nxt = outgoing.get(cur)
                if not nxt:
                    break
                cur = nxt.pop()
                if cur == start:
                    break
                loop.append(cur)
            if len(loop) >= 3:
                loops.append(loop)
    return loops


def capped(points, triangles):
    """(points, triangles) with a fan over every border loop, its centre the
    loop's mean (appended to the points)."""
    points = np.asarray(points, float)
    triangles = np.asarray(triangles, int).reshape(-1, 3)
    loops = border_loops(triangles)
    if not loops:
        return points, triangles
    extra, fans = [], []
    n = len(points)
    for i, loop in enumerate(loops):
        centre = n + i
        extra.append(points[loop].mean(axis=0))
        for k in range(len(loop)):
            fans.append((centre, loop[k], loop[(k + 1) % len(loop)]))
    return (np.concatenate([points, np.array(extra)]),
            np.concatenate([triangles, np.array(fans, int)]))


def shells(triangles):
    """Triangle index arrays of the connected shells (by shared vertices)."""
    t = np.asarray(triangles, int).reshape(-1, 3)
    if not len(t):
        return []
    parent = {}

    def find(x):
        root = x
        while parent.get(root, root) != root:
            root = parent[root]
        while parent.get(x, x) != root:
            parent[x], x = root, parent[x]
        return root

    for a, b, c in t.tolist():
        ra, rb, rc = find(a), find(b), find(c)
        if rb != ra:
            parent[rb] = ra
        if rc != ra and find(rc) != ra:
            parent[find(rc)] = ra
    labels = np.array([find(int(a)) for a in t[:, 0]])
    out = []
    for label in np.unique(labels):
        out.append(np.nonzero(labels == label)[0])
    return out


# ---------------------------------------------------------------------- grid

class Grid(collections.namedtuple("Grid", "origin step shape")):
    """Voxel centres at origin + i·step, i in [0, shape) per axis."""

    @classmethod
    def around(cls, lo, hi, step, jitter=JITTER):
        lo = np.asarray(lo, float)
        hi = np.asarray(hi, float)
        origin = lo - step + np.asarray(jitter, float) * step
        shape = tuple(int(x) for x in np.floor((hi - origin) / step) + 2)
        return cls(origin, float(step), shape)

    def coords(self, axis):
        return self.origin[axis] + np.arange(self.shape[axis]) * self.step

    def centres(self):
        """(N, 3) in the order of `solid(...).ravel()` (x slowest)."""
        x, y, z = np.meshgrid(self.coords(0), self.coords(1), self.coords(2),
                              indexing="ij")
        return np.stack([x.ravel(), y.ravel(), z.ravel()], axis=1)

    def index_range(self, lo, hi):
        """Per axis the [first, last+1) voxel indices whose centres lie in
        [lo, hi]."""
        first = np.ceil((np.asarray(lo) - self.origin) / self.step).astype(int)
        last = np.floor((np.asarray(hi) - self.origin) / self.step).astype(int)
        first = np.clip(first, 0, self.shape)
        last = np.clip(last + 1, 0, self.shape)
        return first, last


def _parity(points, triangles, grid, axis, first, last):
    """Odd-crossing flags for the sub-grid [first, last) along `axis`'s rays,
    shaped (nx, ny, nz) of the sub-grid."""
    u, v = [k for k in range(3) if k != axis]
    size = last - first
    out = np.zeros(tuple(size), bool)
    if not len(triangles) or (size <= 0).any():
        return out
    tri = points[triangles]                       # (T, 3 corners, 3)
    pu, pv, pa = tri[:, :, u], tri[:, :, v], tri[:, :, axis]
    s, o = grid.step, grid.origin
    iu0 = np.maximum(np.ceil((pu.min(1) - o[u]) / s).astype(int), first[u])
    iu1 = np.minimum(np.floor((pu.max(1) - o[u]) / s).astype(int), last[u] - 1)
    iv0 = np.maximum(np.ceil((pv.min(1) - o[v]) / s).astype(int), first[v])
    iv1 = np.minimum(np.floor((pv.max(1) - o[v]) / s).astype(int), last[v] - 1)
    cu = np.maximum(iu1 - iu0 + 1, 0)
    cv = np.maximum(iv1 - iv0 + 1, 0)
    counts = cu * cv
    total = int(counts.sum())
    if not total:
        return out
    which = np.repeat(np.arange(len(tri)), counts)
    local = np.arange(total) - np.repeat(np.cumsum(counts) - counts, counts)
    lu = iu0[which] + local // cv[which]
    lv = iv0[which] + local % cv[which]
    qu = o[u] + lu * s
    qv = o[v] + lv * s
    au, av = pu[which], pv[which]
    #  2D barycentrics of (qu, qv) in the projected triangle
    d = ((av[:, 1] - av[:, 2]) * (au[:, 0] - au[:, 2])
         + (au[:, 2] - au[:, 1]) * (av[:, 0] - av[:, 2]))
    ok = np.abs(d) > 1e-12
    d = np.where(ok, d, 1.0)
    l0 = ((av[:, 1] - av[:, 2]) * (qu - au[:, 2])
          + (au[:, 2] - au[:, 1]) * (qv - av[:, 2])) / d
    l1 = ((av[:, 2] - av[:, 0]) * (qu - au[:, 2])
          + (au[:, 0] - au[:, 2]) * (qv - av[:, 2])) / d
    l2 = 1.0 - l0 - l1
    hit = ok & (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
    if not hit.any():
        return out
    paw = pa[which][hit]
    coord = l0[hit] * paw[:, 0] + l1[hit] * paw[:, 1] + l2[hit] * paw[:, 2]
    line = (lu[hit] - first[u]) * size[v] + (lv[hit] - first[v])
    base = o[axis] - s
    span = (grid.shape[axis] + 2) * s
    keys = np.sort(line * 2.0 + np.clip((coord - base) / span, 0, 0.999999))
    #  queries: every (line, voxel along the axis) of the sub-grid
    ia = np.arange(first[axis], last[axis])
    ca = np.clip((o[axis] + ia * s - base) / span, 0, 0.999999)
    lines = np.arange(size[u] * size[v])
    qkeys = (lines[:, None] * 2.0 + ca[None, :]).ravel()
    starts = np.searchsorted(keys, lines * 2.0)
    below = np.searchsorted(keys, qkeys) - np.repeat(starts, len(ia))
    odd = (below % 2 == 1).reshape(size[u], size[v], len(ia))
    #  (u, v, axis) -> (x, y, z)
    order = [None, None, None]
    order[u], order[v], order[axis] = 0, 1, 2
    return np.transpose(odd, order)


def solid(points, triangles, grid):
    """Bool array of `grid.shape`: inside the union of the capped shells."""
    inside = np.zeros(grid.shape, bool)
    points, triangles = welded(points, triangles)
    for shell in shells(triangles):
        tris = triangles[shell]
        used = np.unique(tris)
        remap = -np.ones(len(points), int)
        remap[used] = np.arange(len(used))
        pts, tri = capped(points[used], remap[tris])
        first, last = grid.index_range(pts.min(axis=0), pts.max(axis=0))
        if (last <= first).any():
            continue
        votes = sum(_parity(pts, tri, grid, axis, first, last).astype(int)
                    for axis in range(3))
        sub = tuple(slice(first[k], last[k]) for k in range(3))
        inside[sub] |= votes >= 2
    return inside


# --------------------------------------------------------------------- skin

def blend_weights(corner_weights, bary):
    """The skin at a point of a triangle: its corners' weights blended."""
    out = {}
    for weights, b in zip(corner_weights, bary):
        for joint, w in weights.items():
            out[joint] = out.get(joint, 0.0) + w * b
    return out


def accumulate(centres, dv, joints, weights, bind, world):
    """Model of the voxels `centres` (each `dv` of volume, world space now),
    skinned by `joints` (per centre a tuple of names, "" or None unused) with
    `weights` (N, K). `bind[j]` is the joint's bindPreMatrix, `world[j]` its
    world matrix now, both 4x4 row-vector."""
    centres = np.asarray(centres, float).reshape(-1, 3)
    weights = np.asarray(weights, float).reshape(len(centres), -1)
    names = sorted({j for row in joints for j in row if j})
    index = {name: i for i, name in enumerate(names)}
    zero = len(names)
    idx = np.array([[index.get(j, zero) if j else zero for j in row]
                    + [zero] * (weights.shape[1] - len(row))
                    for row in joints], int).reshape(weights.shape)
    bm = np.zeros((zero + 1, 4, 4))
    b = np.zeros((zero + 1, 4, 4))
    for name, i in index.items():
        b[i] = np.asarray(bind[name], float)
        bm[i] = b[i] @ np.asarray(world[name], float)
    blend = np.einsum("nk,nkab->nab", weights, bm[idx])
    homogeneous = np.concatenate([centres, np.ones((len(centres), 1))], axis=1)
    rest = np.einsum("na,nab->nb", homogeneous, np.linalg.inv(blend))
    mass = np.zeros(zero + 1)
    moment = np.zeros((zero + 1, 3))
    for k in range(weights.shape[1]):
        w = weights[:, k] * dv
        local = np.einsum("na,nab->nb", rest, b[idx[:, k]])[:, :3]
        np.add.at(mass, idx[:, k], w)
        np.add.at(moment, idx[:, k], local * w[:, None])
    masses, local_centres = {}, {}
    for name, i in index.items():
        if mass[i] > 1e-12:
            masses[name] = float(mass[i])
            local_centres[name] = moment[i] / mass[i]
    return Model(masses, local_centres, float(dv * len(centres)))


def com(model, world):
    """Σ m_j (c_j · M_j) / Σ m_j: the CoM at the joints' matrices `world`."""
    total = sum(model.masses.values())
    acc = np.zeros(3)
    for name, m in model.masses.items():
        point = np.append(model.centres[name], 1.0) @ np.asarray(world[name], float)
        acc += m * point[:3]
    return acc / total


def segment_fractions(model, segment_of):
    """{segment: share of the mass}; joints `segment_of` does not name go to
    "other"."""
    total = sum(model.masses.values())
    out = {}
    for name, m in model.masses.items():
        key = segment_of.get(name, "other")
        out[key] = out.get(key, 0.0) + m / total
    return out
