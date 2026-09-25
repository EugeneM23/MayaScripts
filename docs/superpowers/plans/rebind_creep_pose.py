"""The Creep's bind pose becomes SKM_Manny_Simple's keyed pose -- in place, without unbinding.

    mayapy rebind_creep_pose.py <in .ma/.mb holding the clean Creep skeleton> <out .mb>
    mayapy rebind_creep_pose.py --normals-only <in: a scene already re-bound> <out .mb>

2026-09-24, the animator: «исходная поза у рига Creep_Rig:Group и у скелета этого рига не
должна никак отличаться от позы скелета SKM_Manny_Simple ... текущая поза SKM_Manny_Simple
должна стать байнд позой для Creep_Rig:root».  SKM_Manny_Simple is the ORIGINAL creature
(its T bind, the old joint scales), keyed at frame 0 into the pose wanted; that pose and the
five meshes exactly as that skin deforms them there were dumped from the animator's scene into
`creep_bind_pose.json.gz` (read-only).  Asked about the wrists (the pose turns the hands ~50 deg
against the old bind, and the skin stretches there x3-4.7), the animator chose: the exact pose,
the mesh as SKM shows it.

What this does, on a scene holding the clean Creep skeleton (`|root`, the five Creep meshes):

1. every bone the pose names takes the pose's world matrix, SCALE STRIPPED (the original
   carries 1.12-1.32 on its forearms and fingers; ours are 1), parents first; the helpers keep
   their rules -- ik_hand_r / ik_hand_l exactly on the hands, ik_hand_gun untouched at zero,
   ik_foot_* keeping their relation to the feet, weapon_r / weapon_l riding their hands with
   their local channels untouched;
2. each mesh's Orig shape takes the pose's deformed points (world -> the mesh's object space),
   every influence's bindPreMatrix becomes its new world inverse, and bindPose1 is reset --
   the rebind in place (the skin is p.G.Sum w(BPM.WM).G^-1, so at the bind it hands the Orig
   points back unchanged);
3. the Orig shapes' LOCKED normals take SKM's normals in the pose (`creep_bind_normals.json.gz`,
   `dump_creep_bind_normals.py`): moving the points leaves locked normals where they were, and
   the hands shaded dark («почему она стала такой тёмной?», the same night);
3b. the edges get their smoothing from those normals (`set_edges`): soft where the two faces
   of an edge carry the same normal at both its ends, hard at the seams and the borders -- what
   the creature's source FBX carries, edge for edge.  The animator's creature scene had every
   edge HARD under its locked normals, so the viewport looked right and every FBX export carried
   a smoothing layer of zeros («скелет выгрузился без групп сглаживания на геометрии»);
3c. every joint of the skeleton is a member of the bind pose (`whole_bind_pose`): the FBX
   exporter writes NO bind pose at all when one bone of the hierarchy is missing from it
   («Unable to find the bind pose for: / root / ik_foot_root / ik_foot_l»), and root, weapon_l,
   interaction and center_of_mass were not members;
4. it reports the worst joint and mesh distance from the pose, and refuses a mesh whose
   vertex order does not match (checked against the pose's T rest on the vertices the old
   A-pose bake never moved).
"""
import gzip
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    "C:/!!!Work/MayaScripts/docs/superpowers/plans"
DATA = os.path.join(HERE, "creep_bind_pose.json.gz")

# helpers placed by rule, not copied from the pose
IK_HANDS = (("hand_r", "ik_hand_r"), ("hand_l", "ik_hand_l"))
IK_FEET = (("foot_r", "ik_foot_r"), ("foot_l", "ik_foot_l"))
UNTOUCHED = ("ik_hand_gun", "weapon_r", "weapon_l", "weapon_test")


def load(path=DATA):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _cmds():
    import maya.cmds as cmds
    return cmds


def _om():
    import maya.api.OpenMaya as om
    return om


def unscaled(m):
    """A world matrix with each axis row normalised: the rotation and position, no scale."""
    om = _om()
    m = om.MMatrix(m)
    rows = []
    for r in range(3):
        v = om.MVector(m.getElement(r, 0), m.getElement(r, 1), m.getElement(r, 2)).normal()
        rows += [v.x, v.y, v.z, 0.0]
    return om.MMatrix(rows + [m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2), 1.0])


def skeleton(root="|root"):
    cmds = _cmds()
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    return dict((p.split("|")[-1].split(":")[-1], p) for p in paths)


def _wm(n):
    return _om().MMatrix(_cmds().getAttr(n + ".worldMatrix[0]"))


def targets(b, pose):
    """{leaf: target world matrix} for every bone of `b` the pose decides, helpers by their rules.

    `b` is {leaf: long path}; the current matrices are read for the relative rules."""
    om = _om()
    out = {}
    for leaf in b:
        if leaf in pose and leaf not in UNTOUCHED and leaf not in dict(IK_HANDS).values() \
                and leaf not in dict(IK_FEET).values():
            out[leaf] = unscaled(pose[leaf])
    for hand, helper in IK_HANDS:
        if helper in b and hand in out:
            out[helper] = out[hand]
    for foot, helper in IK_FEET:
        if helper in b and foot in out:
            rel = _wm(b[helper]) * _wm(b[foot]).inverse()
            out[helper] = unscaled(rel * out[foot])
    return out


def _mesh(name):
    cmds = _cmds()
    tr = cmds.ls(name, "*:" + name, type="transform", long=True)
    if len(tr) != 1:
        raise RuntimeError("expected one %s, found %s" % (name, tr))
    shapes = cmds.listRelatives(tr[0], shapes=True, fullPath=True) or []
    live = [s for s in shapes if not cmds.getAttr(s + ".intermediateObject")]
    orig = [s for s in shapes if cmds.getAttr(s + ".intermediateObject")
            and cmds.listConnections(s + ".worldMesh", d=True, s=False)]
    return tr[0], live[0], orig[0]


def _fn(shape):
    om = _om()
    sel = om.MSelectionList(); sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0))


def vertex_order(data, tol=1e-3):
    """How well each mesh's vertex order matches the pose's meshes, 0..1.

    First the share of vertices whose Orig point equals the pose's T rest (the ones the old A
    bake never moved -- legs, lower body, head).  A mesh the A bake moved WHOLE (the arm meshes
    read 0 there) is judged by its edges instead: the share whose length is within 10 % of the
    rest's -- the bake stretched those arms by <= x1.06, a scrambled order gives ~0."""
    om = _om()
    out = {}
    for name, rest in data["rest"].items():
        _, _, orig = _mesh(name)
        pts = _fn(orig).getPoints(om.MSpace.kObject)
        if len(pts) != len(rest):
            out[name] = 0.0
            continue
        same = sum(1 for p, r in zip(pts, rest) if abs(p.x - r[0]) + abs(p.y - r[1]) + abs(p.z - r[2]) < tol)
        share = same / float(len(pts))
        if share < 0.2:
            sel = om.MSelectionList(); sel.add(orig)
            it = om.MItMeshEdge(sel.getDagPath(0))
            near = total = 0
            while not it.isDone():
                a, b = it.vertexId(0), it.vertexId(1)
                lr = math.sqrt(sum((rest[a][i] - rest[b][i]) ** 2 for i in range(3)))
                if lr > 1e-6:
                    total += 1
                    near += abs(pts[a].distanceTo(pts[b]) / lr - 1.0) < 0.1
                it.next()
            share = near / float(max(total, 1))
        out[name] = share
    return out


NORMALS = os.path.join(HERE, "creep_bind_normals.json.gz")


def load_normals(path=NORMALS):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def set_normals(normals):
    """Each mesh's Orig takes SKM's normals in the pose (world -> the mesh's object space), LOCKED as
    the FBX's own were.  The rebind moves the Orig POINTS and leaves locked normals where they
    were -- the T-pose's -- so without this the hands shade dark (2026-09-24: 55-59 deg median off
    the surface).  The skin turns locked normals as the rig moves, so the rest is all that needs
    them.  Returns {mesh: face-vertex normals written}."""
    om = _om()
    out = {}
    for name, world in normals["normals"].items():
        tr, live, orig = _mesh(name)
        fn = _fn(orig)
        counts, verts = fn.getVertices()
        if len(verts) != len(world):
            raise RuntimeError("%s: %d face-vertices, the data has %d" % (name, len(verts), len(world)))
        faces = om.MIntArray()
        for f, c in enumerate(counts):
            for _ in range(c):
                faces.append(f)
        inv = _wm(tr).inverse()
        vecs = om.MVectorArray([(om.MVector(n[0], n[1], n[2]) * inv).normal() for n in world])
        fn.setFaceVertexNormals(vecs, faces, verts, om.MSpace.kObject)
        out[name] = len(verts)
    _cmds().dgdirty(allPlugs=True)
    return out


def soft_edges(shape, tol_deg=0.01):
    """Per edge of `shape`, whether it is SOFT: an interior edge whose two faces carry the same
    normal (within `tol_deg`: the same normal, a shared one in the source) at both its ends.  Border edges are hard, as in the source.

    Measured 2026-09-24 on the creature's source FBX (`creep_T-pose_draft (1).fbx`, the same
    five meshes): its hard edges are EXACTLY these -- 618 of 2949 on an arm, 2832 of 16735 on
    the back, 10833 of 43992 on the body (to one edge), 1284 of 139827 on the face."""
    om = _om()
    sel = om.MSelectionList(); sel.add(shape)
    dag = sel.getDagPath(0)
    fn = om.MFnMesh(dag)
    tol = math.radians(tol_deg)
    soft = [False] * fn.numEdges
    it = om.MItMeshEdge(dag)
    while not it.isDone():
        faces = it.getConnectedFaces()
        if len(faces) == 2:
            soft[it.index()] = all(
                fn.getFaceVertexNormal(faces[0], v, om.MSpace.kObject).angle(
                    fn.getFaceVertexNormal(faces[1], v, om.MSpace.kObject)) <= tol
                for v in (it.vertexId(0), it.vertexId(1)))
        it.next()
    return soft


def set_edges(names):
    """Each mesh's edges soft where its (locked) normals are continuous, hard at the seams and
    the borders (`soft_edges`) -- on the Orig, which the skin hands to the shown shape.  The
    normals stay locked and unchanged: in Maya a locked normal wins over the edge flags, which is
    why an all-hard mesh LOOKED right; an FBX's smoothing layer is the edge flags, which is why it
    exported as all hard.  Returns {mesh: (edges, hard)}.

    The flags only -- NO `cleanupEdgeSmoothing`, which re-shares the normals around each vertex:
    on the body (non-manifold edges, coincident faces) that changed 5449 face-vertex normals,
    some by 180 deg, measured.  Nor can the normals be written back after it: a per-face-vertex
    `setFaceVertexNormals` hardens every edge it touches (measured: all 43992 hard again).  The
    edge flags and the locked normals are separate data in the mesh (and in the .ma), so the
    flags are set and the normals left alone.  The hard count is read back."""
    om = _om()
    out = {}
    for name in names:
        tr, live, orig = _mesh(name)
        soft = soft_edges(orig)
        fn = _fn(orig)
        fn.setEdgeSmoothings(om.MIntArray(list(range(len(soft)))), soft)
        fn.updateSurface()
        out[name] = (len(soft), sum(1 for e in range(fn.numEdges) if not fn.isEdgeSmooth(e)))
    _cmds().dgdirty(allPlugs=True)
    return out


def whole_bind_pose(root="|root"):
    """The skins' bind pose made again, whole: every joint under `root`, where it stands.

    Call it with the skeleton AT its bind.  Measured 2026-09-24: the Creep's bindPose1 held 87
    of the 91 bones -- not root, weapon_l, interaction, center_of_mass -- and three of its members
    (ik_foot_l, ik_hand_gun, ik_hand_l) named their parent through the parent NODE's .message
    instead of the parent's slot in the pose.  Maya's FBX exporter reads either as a broken
    hierarchy and writes no bind pose for it («Unable to find the bind pose for : / root /
    ik_foot_root / ik_foot_l. No bind poses in the hierarchy containing the object will be
    exported»), and Unreal then warns.  Adding the missing four fixed nothing (measured), so the
    pose is saved afresh over all the joints, every skin's .bindPose moved onto it, the old pose(s)
    deleted, and the new one takes the old name.  Returns (pose, members)."""
    cmds = _cmds()
    joints = cmds.ls(root, dag=True, type="joint", long=True) or []
    skins = cmds.ls(type="skinCluster") or []
    old = set()
    for sc in skins:
        old.update(p for p in cmds.listConnections(sc + ".bindPose", s=True, d=False) or []
                   if cmds.objectType(p) == "dagPose")
    name = sorted(old)[0] if old else "bindPose1"
    new = cmds.dagPose(joints, save=True, bindPose=True, name="skeldarBindPose_new")
    new = new[0] if isinstance(new, (list, tuple)) else new
    # a save takes the joints' DAG children along too -- on the rig, the 85 constraints driving
    # the bones (measured); a bind pose holds bones
    strays = [m for m in cmds.ls(cmds.dagPose(new, q=True, members=True) or [], long=True)
              if cmds.objectType(m) != "joint"]
    if strays:
        cmds.dagPose(strays, remove=True, name=new)
    for sc in skins:
        cmds.connectAttr(new + ".message", sc + ".bindPose", force=True)
    for pose in old:
        if cmds.objExists(pose) and not cmds.listConnections(pose + ".message", d=True, s=False):
            cmds.delete(pose)
    if not cmds.objExists(name):
        new = cmds.rename(new, name)
    return new, len(cmds.dagPose(new, q=True, members=True) or [])


def normal_error(normals):
    """Worst angle (deg) between each shown mesh's face-vertex normal and SKM's."""
    om = _om()
    worst = 0.0
    for name, world in normals["normals"].items():
        _, live, _ = _mesh(name)
        fn = _fn(live)
        shown = fn.getNormals(om.MSpace.kWorld)
        counts, ids = fn.getNormalIds()
        for i, n in zip(ids, world):
            a, b = om.MVector(shown[i]), om.MVector(n[0], n[1], n[2])
            if a.length() > 1e-9 and b.length() > 1e-9:      # SKM's body carries one zero normal
                worst = max(worst, math.degrees(a.angle(b)))
    return worst


def rebind(data, root="|root", min_order=0.2):
    """Pose the skeleton, write the Orig shapes, re-express every bindPreMatrix, reset bindPose1.

    Returns {"joints": worst joint element off its target, "mesh": worst vertex off the pose,
    "order": vertex_order}."""
    cmds, om = _cmds(), _om()
    order = vertex_order(data)
    bad = [n for n, f in order.items() if f < min_order]
    if bad:
        raise RuntimeError("vertex order does not match the pose's meshes: %s" % order)
    b = skeleton(root)
    goal = targets(b, data["joints"])
    for leaf in sorted(goal, key=lambda k: b[k].count("|")):          # parents first
        j = b[leaf]
        for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            if cmds.getAttr(j + "." + a, lock=True):
                cmds.setAttr(j + "." + a, lock=False)
        cmds.setAttr(j + ".scale", 1, 1, 1)
        cmds.xform(j, worldSpace=True, matrix=list(goal[leaf]))
    joints = max(max(abs(x - y) for x, y in zip(list(_wm(b[k])), list(goal[k]))) for k in goal)
    # the rebind: identity skinning at the new pose, the pose's mesh as the new rest
    for name, world in data["meshes"].items():
        tr, live, orig = _mesh(name)
        if cmds.listConnections(orig + ".inMesh", s=True, d=False):
            raise RuntimeError("%s has an input on its Orig shape" % orig)
        inv = _wm(tr).inverse()
        _fn(orig).setPoints(om.MPointArray([om.MPoint(p[0], p[1], p[2]) * inv for p in world]), om.MSpace.kObject)
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                cmds.setAttr("%s.bindPreMatrix[%d]" % (sc, idx),
                             list(_wm(cmds.ls(src[0], long=True)[0]).inverse()), type="matrix")
    for pose in cmds.ls(type="dagPose"):
        if cmds.getAttr(pose + ".bindPose"):
            members = [m for m in cmds.ls(cmds.dagPose(pose, q=True, members=True) or [], long=True)
                       if m in b.values()]
            if members:
                cmds.dagPose(members, reset=True, name=pose)
    whole_bind_pose(root)
    cmds.dgdirty(allPlugs=True)
    mesh = 0.0
    for name, world in data["meshes"].items():
        _, live, _ = _mesh(name)
        pts = _fn(live).getPoints(om.MSpace.kWorld)
        mesh = max(mesh, max(abs(p.x - w[0]) + abs(p.y - w[1]) + abs(p.z - w[2]) for p, w in zip(pts, world)))
    result = {"joints": joints, "mesh": mesh, "order": order}
    if os.path.exists(NORMALS):                    # the pose's normals too, or the hands shade dark
        normals = load_normals()
        set_normals(normals)
        result["edges"] = set_edges(list(normals["normals"]))
        result["normals"] = normal_error(normals)
    return result


if __name__ == "__main__":
    import maya.standalone
    maya.standalone.initialize()
    cmds = _cmds()
    for p in ("matrixNodes", "quatNodes"):
        try:
            cmds.loadPlugin(p, quiet=True)
        except Exception:
            pass
    only_normals = "--normals-only" in sys.argv
    src, out = [a for a in sys.argv[1:] if not a.startswith("--")][:2]
    cmds.file(src, open=True, force=True, executeScriptNodes=False)
    if only_normals:                               # a scene already re-bound (a built rig): the normals alone
        normals = load_normals()
        print("normals written:", set_normals(normals))
        print("edges (count, hard):", set_edges(list(normals["normals"])))
        print("shown normals off SKM's: worst %.4f deg" % normal_error(normals))
    else:
        result = rebind(load())
        print("vertex order (share on the old rest):", dict((k, round(v, 3)) for k, v in result["order"].items()))
        print("joints off the pose: %.2e   mesh off the pose: %.2e   normals off SKM's: %s deg"
              % (result["joints"], result["mesh"], "%.4f" % result["normals"] if "normals" in result else "-"))
    if not os.path.isdir(os.path.dirname(out)):
        os.makedirs(os.path.dirname(out))
    cmds.file(rename=out)
    cmds.file(save=True, type="mayaBinary" if out.endswith(".mb") else "mayaAscii", force=True)
    print("saved", out)
