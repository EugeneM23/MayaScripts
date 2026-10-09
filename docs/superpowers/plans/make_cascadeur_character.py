"""Build the Cascadeur character asset: UE5 Manny with its mesh, Y-up, no wrapper.

    mayapy make_cascadeur_character.py

The source is sources/manny/SKM_Manny_Simple.fbx, exported from the animator's
Unreal project (the Orc Marauder pack's UE5 demo mannequin, the same mesh that
Skin_3p is). Its top node carries a -90 X rotation (Unreal's Z-up file read
by Maya). Cascadeur does not apply that rotation when it imports a model, so the
character lay on its side; the clips it receives come in Y-up with the root at
identity and stand upright.

Fix, measured on 2026-10-09 in the animator's Cascadeur: every child of the top
node (the `root` joint and the mesh) keeps its WORLD matrix, the top node is
deleted, and the result is exported Y-up. Then the character stands (head 162.6,
pelvis 95.9, foot 8.2, the clip's own 159.7 / 94.6 / 8.6) and the clip imported
onto it reproduces the clip-only pose frame for frame (frame 0 identical, the
root walks 0 -> -100 as the clip's root does).

Writes SkeldarAnim/assets/Cascadeur/Manny_UE5.fbx. Re-run after a change to the
source file.
"""

import os

import maya.standalone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(REPO, "sources", "manny", "SKM_Manny_Simple.fbx")
OUT = os.path.join(REPO, "SkeldarAnim", "assets", "Cascadeur", "Manny_UE5.fbx")

TOP = "|SKM_Manny_Simple"


def build(src=SRC, out=OUT):
    """Import `src`, flatten the top node's rotation into the children, export."""
    import maya.cmds as cmds
    import maya.mel as mel

    maya.standalone.initialize(name="python")
    try:
        cmds.loadPlugin("fbxmaya", quiet=True)
        cmds.file(new=True, force=True)
        mel.eval("FBXResetImport")
        mel.eval("FBXImportMode -v add")
        mel.eval('FBXImport -f "%s"' % src.replace("\\", "/"))

        kids = cmds.listRelatives(TOP, children=True, fullPath=True) or []
        if not kids:
            raise RuntimeError("no children under %s - is %s the Manny file?"
                               % (TOP, src))
        uuids = cmds.ls(kids, uuid=True)
        worlds = {}
        for kid in kids:
            worlds[kid] = cmds.xform(kid, q=True, ws=True, m=True)
        cmds.parent(kids, world=True)
        for uid, kid in zip(uuids, kids):
            node = cmds.ls(uid, long=True)[0]
            cmds.xform(node, ws=True, m=worlds[kid])
        cmds.delete(TOP)

        cmds.select(clear=True)
        for uid in uuids:
            cmds.select(cmds.ls(uid, long=True)[0], add=True, hierarchy=True)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        mel.eval("FBXExportUpAxis y")
        mel.eval("FBXExportInputConnections -v false")
        mel.eval('FBXExport -f "%s" -s' % out.replace("\\", "/"))
    finally:
        maya.standalone.uninitialize()
    if not os.path.isfile(out):
        raise RuntimeError("the export wrote nothing: " + out)
    return out


if __name__ == "__main__":
    print("wrote", build())
