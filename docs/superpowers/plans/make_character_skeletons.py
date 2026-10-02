"""Write SkeldarAnim/assets/character_skeletons.json: every catalog character's game skeleton at its bind.

The Auto card (2026-10-02, docs/superpowers/specs/2026-10-02-auto-character-import-design.md) decides
whether a clip's skeleton is one of ours by comparing its bone lengths with these. One entry per
`catalog.CHARACTERS` row: the asset's file name and sha1 (a unit test pins it: rebuild a character
asset, re-run this), and every joint of its game skeleton as `leaf: [parent leaf or null, x, y, z]`
at the bind (`maya_retargetmode.rest_world`: the skinCluster's bindPreMatrix, else where it stands).

Run in mayapy standalone, never in the animator's Maya (it opens each asset in turn):

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_character_skeletons.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
OUT = os.path.join(PLUGIN, "assets", "character_skeletons.json")


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def main():
    sys.path.insert(0, PLUGIN)
    import maya.standalone
    maya.standalone.initialize()
    import maya.cmds as cmds
    for plugin in ("fbxmaya", "matrixNodes", "quatNodes"):
        try:
            cmds.loadPlugin(plugin, quiet=True)
        except Exception:                                    # noqa: BLE001
            pass
    import maya_retargetmode
    import maya_rigs
    from maya_overrig import builder
    from maya_scenesetup import catalog, character

    rows = {}
    for entry in catalog.CHARACTERS:
        cmds.file(new=True, force=True)
        path = catalog.character_file(entry)
        namespace = character.rig_namespace(entry) if catalog.is_rig(entry) else None
        character.import_asset(path, namespace)
        if catalog.is_rig(entry):
            found = maya_rigs.rigs()
            assert len(found) == 1, "%s: %d rigs" % (entry.key, len(found))
            root = found[0].skeleton_root
        else:
            roots = builder.character_roots()
            assert len(roots) == 1, "%s: roots %s" % (entry.key, roots)
            root = roots[0]
        joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                              fullPath=True) or [])
        bones = {}
        for joint in joints:
            parent = cmds.listRelatives(joint, parent=True, type="joint", fullPath=True)
            matrix = maya_retargetmode.rest_world(joint)
            name = leaf(joint)
            assert name not in bones, "%s: %s twice" % (entry.key, name)
            bones[name] = [leaf(parent[0]) if parent and joint != root else None,
                           round(matrix[12], 4), round(matrix[13], 4), round(matrix[14], 4)]
        from maya_uebridge import skeletonmatch
        rows[entry.key] = {"file": entry.file, "sha1": skeletonmatch.asset_digest(path),
                           "kind": entry.kind,
                           "model": entry.model, "bones": bones}
        print("row", entry.key, len(bones), "bones, root", leaf(root))
        sys.stdout.flush()
    with open(OUT, "w") as handle:
        json.dump({"version": 1, "rows": rows}, handle, indent=0, sort_keys=True)
    print("wrote", OUT)
    maya.standalone.uninitialize()


if __name__ == "__main__":
    main()
