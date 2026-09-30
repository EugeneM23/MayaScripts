"""Dress SkeldarAnim/assets/Manny_Rig.ma and Manny_Skeleton.ma in Unreal's own textures, in place.

    mayapy make_manny_textured_assets.py [Manny_Rig.ma] [Manny_Skeleton.ma]

mayapy STANDALONE.  2026-09-30 (spec: docs/superpowers/specs/2026-09-30-manny-textured-design.md),
the Orc D's road.  For each asset: open it (script nodes NOT executed), import
`sources/manny/SKM_Manny_Simple.fbx` into a namespace to learn which face wears which of Unreal's two
slots, and dress both meshes:

- `Skin_3p` IS that mesh index for index (every uv equal, measured 0.000000): each face is found by
  its three vertex ids -- all 92178 must be found, the slot counts must be Unreal's 38166 / 54012;
- `Hands_1P` is a cut of it (arms, shoulders, hands): its vertices are matched to Unreal's by
  position and uv, a face by its three matched vertices, and a face the cut made new (a vertex
  matching nothing) takes the slot of the Unreal face closest to its centre;
- two materials, `skeldarTexture_Manny_HeadLegs` and `skeldarTexture_Manny_Torso`, the one shader
  (`colour.SHADER` wearing `colour.LOOK`, `colour.TEXTURE_MARKER`) with the colour map and the
  normal map through a bump2d in tangent-space mode (make_manny_textures.py's maps), every file node
  naming its image RELATIVELY (`colour.ASSET_IMAGE`, "Manny/<file>") -- Add Character points it at
  the installed copy.

Then everything shading left unused is deleted (the meshes' old material, the dead `MI_Manny_*`
networks naming `D:/dev/...` and `/Users/Shared/...`, the MaterialX `Maya_Blinn1/3`, ...), the
`UsdDefaultRenderSettings` mayaUsd makes on every open is dropped (the file keeps its own), the
scene's time unit is put back if the FBX importer moved it (trap 80), the file saved as `.ma`, the
script-node blocks cut from the text (trap 74), banned words refused -- and the text compared with
the file before: outside the shading blocks, the two meshes' face-group lines and Maya's known resave
noise, not one line may differ.  Re-runnable: a second run replaces its own materials.  The machinery
that is not Manny's lives in asset_dress.py (shared with make_creep_textured_assets.py); `--out DIR`
writes the dressed files there instead of over the assets (a proof run).
"""

import os
import re
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asset_dress as dress  # noqa: E402
from asset_dress import colour, mfn, dag, leaf  # noqa: E402

REPO = dress.REPO
ASSETS = dress.ASSETS
FBX = os.path.join(REPO, "sources", "manny", "SKM_Manny_Simple.fbx").replace("\\", "/")
NS = "ueManny"
MAPS = "Manny/"
MESHES = ("Skin_3p", "Hands_1P")
SLOT_OF = {"MI_Manny_01": "HeadLegs", "MI_Manny_02": "Torso"}
UNREAL_SLOTS = {"HeadLegs": 38166, "Torso": 54012}
IMAGES = ("Manny_HeadLegs_Color.jpg", "Manny_HeadLegs_Normal.jpg", "Manny_Torso_Color.jpg",
          "Manny_Torso_Normal.jpg")
BANNED = (NS + ":", "MI_Manny", "T_Manny_0", "EnvSamplerTex", "Maya_Blinn")

dress.begin()


def unreal_slots():
    """Unreal's mesh in NS: its shape, points, uvs, the slot of each face, {sorted vertex ids: face}."""
    time_unit = cmds.currentUnit(query=True, time=True)
    cmds.namespace(add=NS)
    cmds.namespace(set=NS)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval('FBXImport -f "%s"' % FBX)
    cmds.namespace(set=":")
    if cmds.currentUnit(query=True, time=True) != time_unit:        # trap 80: the importer moves it
        print("  (the FBX importer moved the time unit to %s; back to %s)"
              % (cmds.currentUnit(query=True, time=True), time_unit))
        cmds.currentUnit(time=time_unit, updateAnimation=False)
    shapes = [m for m in cmds.ls(NS + ":*", type="mesh", long=True) if not cmds.getAttr(m + ".intermediateObject")]
    assert len(shapes) == 1, shapes
    fn = mfn(shapes[0])
    engines, per_face = fn.getConnectedShaders(0)
    slot_of_engine = []
    for e in engines:
        mat = leaf((cmds.listConnections(om.MFnDependencyNode(e).name() + ".surfaceShader") or ["?"])[0])
        if mat not in SLOT_OF:
            raise RuntimeError("Unreal's mesh wears %s, measured on %s" % (mat, sorted(SLOT_OF)))
        slot_of_engine.append(SLOT_OF[mat])
    slots = [slot_of_engine[k] for k in per_face]
    counts = dict((s, slots.count(s)) for s in UNREAL_SLOTS)
    if counts != UNREAL_SLOTS:
        raise RuntimeError("Unreal's slots %s, measured %s" % (counts, UNREAL_SLOTS))
    _counts, verts = fn.getVertices()
    face_of = dict((tuple(sorted(verts[3 * f:3 * f + 3])), f) for f in range(fn.numPolygons))
    return shapes[0], fn, slots, face_of


def dress_skin_3p(shape, ufn, slots, face_of):
    fn = mfn(shape)
    if (fn.numVertices, fn.numPolygons) != (ufn.numVertices, ufn.numPolygons):
        raise RuntimeError("Skin_3p is %d/%d, Unreal's %d/%d" % (fn.numVertices, fn.numPolygons,
                                                                 ufn.numVertices, ufn.numPolygons))
    u, v = fn.getUVs()
    uu, uv = ufn.getUVs()
    duv = max(max(abs(a - b) for a, b in zip(u, uu)), max(abs(a - b) for a, b in zip(v, uv)))
    if duv > 1e-6:
        raise RuntimeError("Skin_3p's uvs are not Unreal's index for index: %.2e" % duv)
    _c, verts = fn.getVertices()
    out = {}
    for f in range(fn.numPolygons):
        uf = face_of.get(tuple(sorted(verts[3 * f:3 * f + 3])))
        if uf is None:
            raise RuntimeError("Skin_3p face %d is no face of Unreal's" % f)
        out.setdefault(slots[uf], []).append(f)
    counts = dict((k, len(v)) for k, v in out.items())
    print("  Skin_3p: uvs Unreal's to %.1e, every face found by its vertex ids: %s" % (duv, counts))
    if counts != UNREAL_SLOTS:
        raise RuntimeError("Skin_3p's slots %s, Unreal's %s" % (counts, UNREAL_SLOTS))
    return out


def dress_hands_1p(shape, ushape, ufn, slots, face_of):
    fn = mfn(shape)
    pts, upts = fn.getPoints(om.MSpace.kWorld), ufn.getPoints(om.MSpace.kWorld)
    u, v = fn.getUVs()
    uu, uv = ufn.getUVs()
    q = 0.05

    def key(p, a, b):
        return (int(round(p.x / q)), int(round(p.y / q)), int(round(p.z / q)),
                int(round(a * 2000)), int(round(b * 2000)))

    table = {}
    for i in range(ufn.numVertices):
        table.setdefault(key(upts[i], uu[i], uv[i]), []).append(i)
    vmap, worst = [], 0.0
    for i in range(fn.numVertices):
        k = key(pts[i], u[i], v[i])
        cands = table.get(k, [])
        if not cands:                                        # a quantum boundary: the neighbours
            cands = [c for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                     for du in (-1, 0, 1) for dv in (-1, 0, 1)
                     for c in table.get((k[0] + dx, k[1] + dy, k[2] + dz, k[3] + du, k[4] + dv), [])]
        cands = [c for c in cands if pts[i].distanceTo(upts[c]) < 0.01 and
                 abs(u[i] - uu[c]) < 1e-3 and abs(v[i] - uv[c]) < 1e-3]
        if len(set(cands)) == 1:
            vmap.append(cands[0])
            worst = max(worst, pts[i].distanceTo(upts[cands[0]]))
        else:
            vmap.append(None)
    _c, verts = fn.getVertices()
    intersector = om.MMeshIntersector()
    udag = dag(ushape)
    intersector.create(udag.node(), udag.inclusiveMatrix())
    out, by_ids, by_near = {}, 0, 0
    for f in range(fn.numPolygons):
        ids = [vmap[x] for x in verts[3 * f:3 * f + 3]]
        uf = face_of.get(tuple(sorted(ids))) if None not in ids else None
        if uf is None:
            c = om.MPoint()
            for x in verts[3 * f:3 * f + 3]:
                c += om.MVector(pts[x])
            c = om.MPoint(c.x / 3.0, c.y / 3.0, c.z / 3.0)
            uf = intersector.getClosestPoint(c, 1000.0).face
            by_near += 1
        else:
            by_ids += 1
        out.setdefault(slots[uf], []).append(f)
    lost = sum(1 for x in vmap if x is None)
    print("  Hands_1P: %d of %d vertices Unreal's (to %.4f cm, position and uv), %d faces by their vertex "
          "ids, %d by the closest Unreal face: %s" % (fn.numVertices - lost, fn.numVertices, worst, by_ids,
                                                    by_near, dict((k, len(v)) for k, v in out.items())))
    if by_near > 200 or lost > 50:
        raise RuntimeError("Hands_1P is not the cut this was measured on (%d vertices unmatched)" % lost)
    return out


def dress_asset(name, out_dir=None):
    path = ASSETS + "/" + name
    before_text = dress.open_asset(path)
    print("== %s" % name)
    time_unit = cmds.currentUnit(query=True, time=True)

    shapes = {}
    for mesh in MESHES:
        found = cmds.ls(mesh, type="transform", long=True)
        assert len(found) == 1, (mesh, found)
        shapes[mesh] = dress.live_shape(found[0])
    worn_before = dict((m, sorted(set(cmds.listConnections(s, type="shadingEngine") or [])))
                       for m, s in shapes.items())
    print("  worn before:", worn_before)
    old_ours, doomed = dress.ours(MAPS), []
    if old_ours:
        doomed = dress.network(old_ours)
        print("  our own materials from an earlier run go: %s" % old_ours)
        cmds.delete(doomed)

    ushape, ufn, slots, face_of = unreal_slots()
    faces = {"Skin_3p": dress_skin_3p(shapes["Skin_3p"], ufn, slots, face_of),
             "Hands_1P": dress_hands_1p(shapes["Hands_1P"], ushape, ufn, slots, face_of)}
    cmds.namespace(removeNamespace=NS, deleteNamespaceContent=True)
    cmds.select(clear=True)
    made = {"HeadLegs": dress.material(MAPS, "Manny_HeadLegs", "Manny_HeadLegs_Color.jpg", "Manny_HeadLegs_Normal.jpg"),
            "Torso": dress.material(MAPS, "Manny_Torso", "Manny_Torso_Color.jpg", "Manny_Torso_Normal.jpg")}
    for mesh in MESHES:
        transform = cmds.listRelatives(shapes[mesh], parent=True, fullPath=True)[0]
        for slot in ("HeadLegs", "Torso"):
            ids = faces[mesh].get(slot, [])
            if ids:
                cmds.sets(["%s.f[%d]" % (transform, i) for i in ids], edit=True, forceElement=made[slot][1])
    if cmds.currentUnit(query=True, time=True) != time_unit:
        cmds.currentUnit(time=time_unit, updateAnimation=False)

    gone = dress.unused_shading()
    print("  unused shading deleted (%d): %s" % (len(gone), sorted(set(t for _n, t in gone))))
    print("    %s" % [n for n, _t in gone])

    # what must be there
    for mesh in MESHES:
        s = shapes[mesh]
        n_faces = mfn(s).numPolygons
        engines, per_face = mfn(s).getConnectedShaders(0)
        names = [om.MFnDependencyNode(e).name() for e in engines]
        worn = dict((names[k], list(per_face).count(k)) for k in range(len(names)))
        assert sorted(worn) == sorted(e for _m, e in made.values()), (mesh, worn)
        assert -1 not in list(per_face) and sum(worn.values()) == n_faces, (mesh, worn)
        want = dict((made[k][1], len(v)) for k, v in faces[mesh].items())
        assert worn == want, (mesh, worn, want)
        print("  %s wears %s" % (mesh, worn))
    print("  materials:", sorted(m for m in cmds.ls(materials=True) if m not in dress.KEEP))
    print("  files:", dress.check_images(MAPS, IMAGES))
    assert not cmds.namespace(exists=NS)

    shading_names = set(n for n, _t in gone) | set(dress.network([m for m, _e in made.values()]))
    shading_names |= set(n for sgs in worn_before.values() for n in sgs) | set(doomed)
    dress.save_checked(path, before_text, shading_names, MESHES, BANNED, out_dir)


args, out_dir = dress.out_dir_arg(sys.argv[1:])
todo = args or ["Manny_Rig.ma", "Manny_Skeleton.ma"]
if len(todo) == 1:
    dress_asset(todo[0], out_dir)
else:
    dress.run_each(todo, __file__, out_dir)
