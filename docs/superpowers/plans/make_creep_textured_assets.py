"""Dress SkeldarAnim/assets/Creep_Rig.ma and Creep_Skeleton.ma in the Creep's own textures, in place.

    mayapy make_creep_textured_assets.py [Creep_Rig.ma] [Creep_Skeleton.ma] [--out DIR]

mayapy STANDALONE.  2026-09-30 (spec: docs/superpowers/specs/2026-09-30-creep-textured-design.md): the
Manny's road (make_manny_textured_assets.py), with the machinery in asset_dress.py.  The Creep's five
meshes carry the UVs of the Cascadeur FBX its textures were made for, index for index (measured: counts
equal, values to 7.5e-9, per-face uv ids equal) -- checked again here by their uv counts -- and each mesh
wears ONE set whole:

    Creep_Body                           Creep_Body_{Color,Normal}.jpg
    Creep_Face (the head)                Creep_Face_{Color,Normal}.jpg
    Creep_Back, Creep_Arm_L, Creep_Arm_R Creep_Limbs_{Color,Normal}.jpg  (Cascadeur's shared set)

(make_creep_textures.py's maps) as `skeldarTexture_Creep_Body/_Face/_Limbs`, the one shader with the
colour map and the normal map through a bump2d in tangent space, every file node naming its image
relatively ("Creep/<file>").  The meshes' old materials and all shading left unused go; the file is saved
and checked as the Manny's are (the header, `git diff` explaining every line, banned text, relative
paths) and moved over the asset -- or into `--out DIR`.  On the way `fileInfo "exportedFrom"` goes: both
assets carried the path of the animator's creature scene they were cut out of.  Re-runnable: a second run
replaces its own materials.  The Creep pipeline's LAST step, after make_creep_weapon_sockets.py.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asset_dress as dress  # noqa: E402

MAPS = "Creep/"
SETS = {"Body": ("Creep_Body",), "Face": ("Creep_Face",), "Limbs": ("Creep_Back", "Creep_Arm_L", "Creep_Arm_R")}
MESHES = tuple(m for meshes in SETS.values() for m in meshes)
UVS = {"Creep_Body": 25956, "Creep_Face": 52295, "Creep_Back": 8779, "Creep_Arm_L": 2265, "Creep_Arm_R": 2265}
IMAGES = tuple("Creep_%s_%s.jpg" % (k, kind) for k in SETS for kind in ("Color", "Normal"))
BANNED = ("FBXASC", "creep_T-pose", "blinn1")

dress.begin()


def dress_asset(name, out_dir=None):
    path = dress.ASSETS + "/" + name
    before_text = dress.open_asset(path)
    print("== %s" % name)

    shapes = {}
    for mesh in MESHES:
        found = cmds.ls(mesh, type="transform", long=True)
        assert len(found) == 1, (mesh, found)
        shape = dress.live_shape(found[0])
        uvsets = cmds.polyUVSet(shape, q=True, allUVSets=True)
        n_uvs = dress.mfn(shape).numUVs()
        if uvsets != ["map1"] or n_uvs != UVS[mesh]:
            raise RuntimeError("%s: uv sets %s, %d uvs -- not the Cascadeur mesh its textures were made for (%d)"
                               % (mesh, uvsets, n_uvs, UVS[mesh]))
        shapes[mesh] = shape
    worn_before = dict((m, sorted(set(cmds.listConnections(s, type="shadingEngine") or [])))
                       for m, s in shapes.items())
    worn_nodes = dress.worn_network(list(shapes.values()))
    print("  worn before:", worn_before)
    old_ours, doomed = dress.ours(MAPS), []
    if old_ours:
        doomed = dress.network(old_ours)
        print("  our own materials from an earlier run go: %s" % old_ours)
        cmds.delete(doomed)

    cmds.select(clear=True)
    made = dict((k, dress.material(MAPS, "Creep_" + k, "Creep_%s_Color.jpg" % k, "Creep_%s_Normal.jpg" % k))
                for k in SETS)
    for key, meshes in SETS.items():
        cmds.sets([shapes[m] for m in meshes], edit=True, forceElement=made[key][1])

    gone = dress.unused_shading()
    print("  unused shading deleted (%d): %s" % (len(gone), sorted(set(t for _n, t in gone))))
    print("    %s" % [n for n, _t in gone])

    # what must be there: each mesh wears its set's material whole
    for key, meshes in SETS.items():
        for mesh in meshes:
            engines, per_face = dress.mfn(shapes[mesh]).getConnectedShaders(0)
            names = [om.MFnDependencyNode(e).name() for e in engines]
            assert names == [made[key][1]] and -1 not in list(per_face), (mesh, names)
            print("  %-12s wears %s (%d faces)" % (mesh, made[key][0], len(per_face)))
    print("  materials:", sorted(m for m in cmds.ls(materials=True) if m not in dress.KEEP))
    print("  files:", dress.check_images(MAPS, IMAGES))

    shading_names = set(n for n, _t in gone) | set(dress.network([m for m, _e in made.values()]))
    shading_names |= set(n for sgs in worn_before.values() for n in sgs) | set(doomed) | set(worn_nodes)
    # both assets carried `fileInfo "exportedFrom" "C:/Users/MY PC/Downloads/creep_T-pose_MIX_06_skin.mb"`
    # from the scene they were cut out of -- a path of the animator's machine, in a file colleagues get
    dress.save_checked(path, before_text, shading_names, MESHES, BANNED, out_dir, drop_info=("exportedFrom",))


args, out_dir = dress.out_dir_arg(sys.argv[1:])
todo = args or ["Creep_Rig.ma", "Creep_Skeleton.ma"]
if len(todo) == 1:
    dress_asset(todo[0], out_dir)
else:
    dress.run_each(todo, __file__, out_dir)
