"""The normals of SKM_Manny_Simple's five meshes as its own skin shows them in the keyed pose -> a data file.

    mayapy dump_creep_bind_normals.py C:/!!!Work/MayaScripts/sources/creep/creep_T-pose_draft.fbx

2026-09-24, the animator, after the rebind: «что произошло с геометрией, почему она стала такой
тёмной?»  The Creep's meshes carry LOCKED normals (the FBX's own, every one of them), and the
rebind wrote new points into the Orig shapes while their normals stayed the T-pose ones: on the
hand meshes the stored normals stood a median 55-59 deg off the surface (p90 99-107), 44 deg already
after the morning's A bake; body, back and face 4-8.  The skin DOES turn locked normals when the
rig moves (measured: 34-56 deg for a 60 deg shoulder turn), so only the REST normals are wrong.

The right rest normals are the ones SKM_Manny_Simple showed in that pose -- its skin turning the
T normals.  The FBX the animator imported as SKM_Manny_Simple is read in mayapy STANDALONE (import,
never the live scene), its points at the pose checked against `creep_bind_pose.json.gz` (so this
is the very mesh), and its world-space face-vertex normals written to `creep_bind_normals.json.gz`
in face-vertex order (the order `MFnMesh.getVertices()` walks).
"""
import gzip
import json
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1].replace("\\", "/")
MESHES = {"body": "Creep_Body", "back": "Creep_Back", "arm_l": "Creep_Arm_L", "arm_r": "Creep_Arm_R", "face": "Creep_Face"}
for p in ("fbxmaya", "matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
POSE = json.load(gzip.open(os.path.join(HERE, "creep_bind_pose.json.gz"), "rt", encoding="utf-8"))

cmds.file(new=True, force=True)
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % SRC)
frame = float(POSE["source"].split("frame ")[1].split(",")[0]) if "frame " in POSE["source"] else 0.0
cmds.currentTime(frame + 1)
cmds.currentTime(frame)
out = {"source": "%s at frame %g, the skin's own normals, world space" % (os.path.basename(SRC), frame), "normals": {}}
for src, dst in MESHES.items():
    tr = [t for t in cmds.ls(src, "*:" + src, type="transform", long=True)]
    if len(tr) != 1:
        raise RuntimeError("expected one %s in the FBX, found %s" % (src, tr))
    live = [s for s in cmds.listRelatives(tr[0], shapes=True, fullPath=True) if not cmds.getAttr(s + ".intermediateObject")][0]
    sel = om.MSelectionList(); sel.add(live)
    fn = om.MFnMesh(sel.getDagPath(0))
    pts = fn.getPoints(om.MSpace.kWorld)
    goal = POSE["meshes"][dst]
    if len(pts) != len(goal):
        raise RuntimeError("%s: %d vertices, the pose has %d" % (src, len(pts), len(goal)))
    off = max(abs(p.x - g[0]) + abs(p.y - g[1]) + abs(p.z - g[2]) for p, g in zip(pts, goal))
    if off > 1e-3:
        raise RuntimeError("%s is not the pose's mesh: its points are %.4f off" % (src, off))
    normals = fn.getNormals(om.MSpace.kWorld)
    counts, ids = fn.getNormalIds()
    out["normals"][dst] = [[round(normals[i].x, 6), round(normals[i].y, 6), round(normals[i].z, 6)] for i in ids]
    print("%-6s points on the pose to %.2e, %d face-vertex normals" % (src, off, len(ids)))
path = os.path.join(HERE, "creep_bind_normals.json.gz")
with gzip.open(path, "wt", encoding="utf-8") as fh:
    json.dump(out, fh)
print("wrote %s (%.2f MB)" % (path, os.path.getsize(path) / 1e6))
