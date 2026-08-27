"""Extract the Manny skeleton template JSON from Manny_Skeleton.ma.

Run under mayapy (there is no system Python on this machine):

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' assets/make_skeleton_template.py

Reads the shipped character scene next to this file and writes
manny_skeleton_template.json beside it.  The JSON is the single source the
skeleton builder (maya_skelfit.py) consumes: joint hierarchy, every
orientation channel verbatim, world transforms for the fit math, and the
skin influence lists of the shipped meshes.  The scene is IMPORTED, never
opened -- import does not execute script nodes (the shipped copy has the
"vaccine" lines cut, but the habit stays).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCENE = os.path.join(HERE, "Manny_Skeleton.ma")
OUT = os.path.join(HERE, "manny_skeleton_template.json")


def weight_stats(shape, skin, influence_names):
    """Influences carrying real weight anywhere, and the true per-vertex
    influence count maximum.  Read through MFnSkinCluster.getWeights -- one
    call for the whole mesh; per-vertex skinPercent over 48k vertices is
    minutes, this is under a second."""
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma

    sel = om.MSelectionList()
    sel.add(shape)
    dag = sel.getDagPath(0)
    sel2 = om.MSelectionList()
    sel2.add(skin)
    fn = oma.MFnSkinCluster(sel2.getDependNode(0))

    comp = om.MFnSingleIndexedComponent()
    comp_obj = comp.create(om.MFn.kMeshVertComponent)
    comp.setCompleteData(om.MFnMesh(dag).numVertices)

    weights, count = fn.getWeights(dag, comp_obj)
    n_verts = len(weights) // count
    carries = [False] * count
    real_max = 0
    for v in range(n_verts):
        row = weights[v * count:(v + 1) * count]
        live = 0
        for i, w in enumerate(row):
            if w > 1e-6:
                carries[i] = True
                live += 1
        real_max = max(real_max, live)
    weighted = [influence_names[i] for i in range(count) if carries[i]]
    return weighted, real_max


def body_points(cmds, transform):
    """World position of every vertex, one API call for the whole mesh."""
    import maya.api.OpenMaya as om
    sel = om.MSelectionList()
    sel.add(transform)
    fn = om.MFnMesh(sel.getDagPath(0))
    return [[p.x, p.y, p.z] for p in fn.getPoints(om.MSpace.kWorld)]


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    import maya.cmds as cmds

    cmds.file(new=True, force=True)
    cmds.file(SCENE, i=True, force=True, ignoreVersion=True,
              mergeNamespacesOnClash=False, options="v=0;")

    joints = cmds.ls(type="joint", long=True) or []
    if not joints:
        raise SystemExit("no joints came out of %s" % SCENE)

    def short(path):
        return path.rsplit("|", 1)[-1]

    entries = []
    for j in sorted(joints):
        parent = cmds.listRelatives(j, parent=True, fullPath=True)
        parent = parent[0] if parent else None
        parent_is_joint = bool(parent) and cmds.nodeType(parent) == "joint"
        entry = {
            "name": short(j),
            "parent": short(parent) if parent_is_joint else None,
            "dag_parent": short(parent) if (parent and not parent_is_joint) else None,
            "translate": cmds.getAttr(j + ".translate")[0],
            "rotate": cmds.getAttr(j + ".rotate")[0],
            "jointOrient": cmds.getAttr(j + ".jointOrient")[0],
            "rotateAxis": cmds.getAttr(j + ".rotateAxis")[0],
            "rotateOrder": cmds.getAttr(j + ".rotateOrder"),
            "preferredAngle": cmds.getAttr(j + ".preferredAngle")[0],
            "radius": cmds.getAttr(j + ".radius"),
            "segmentScaleCompensate": cmds.getAttr(j + ".segmentScaleCompensate"),
            "side": cmds.getAttr(j + ".side"),
            "type": cmds.getAttr(j + ".type"),
            "world_position": cmds.xform(j, q=True, ws=True, t=True),
            "world_matrix": cmds.getAttr(j + ".worldMatrix[0]"),
        }
        entries.append(entry)

    names = [e["name"] for e in entries]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise SystemExit("duplicate joint names, template would be ambiguous: %s" % dupes)

    meshes = {}
    for shape in cmds.ls(type="mesh", long=True, noIntermediate=True) or []:
        transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
        skins = cmds.ls(cmds.listHistory(shape) or [], type="skinCluster") or []
        influences = []
        weighted = []
        real_max = None
        if skins:
            influences = [short(cmds.ls(i, long=True)[0])
                          for i in (cmds.skinCluster(skins[0], q=True, influence=True) or [])]
            weighted, real_max = weight_stats(shape, skins[0], influences)
        bbox = cmds.exactWorldBoundingBox(transform)
        meshes[short(transform)] = {
            "vertices": cmds.polyEvaluate(transform, vertex=True),
            "bbox": bbox,
            "influences": influences,
            "weighted_influences": weighted,
            "max_influences": (cmds.getAttr(skins[0] + ".maxInfluences") if skins else None),
            "measured_max_influences": real_max,
        }

    # landmarks come from the SAME function the fit uses on a target mesh,
    # so fitting Manny's mesh onto itself is exact by construction
    sys.path.insert(0, os.path.dirname(HERE))
    import maya_skelfit
    body = max(meshes, key=lambda n: meshes[n]["vertices"])
    landmarks = maya_skelfit.mesh_landmarks(body_points(cmds, body))

    data = {
        "source_scene": os.path.basename(SCENE),
        "linear_unit": cmds.currentUnit(q=True, linear=True),
        "landmarks": landmarks,
        "joints": entries,
        "meshes": meshes,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    roots = [e["name"] for e in entries if e["parent"] is None]
    sys.stdout.write("wrote %s: %d joints, roots=%s, %d meshes\n"
                     % (OUT, len(entries), roots, len(meshes)))


if __name__ == "__main__":
    main()
