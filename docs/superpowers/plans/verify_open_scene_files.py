"""Standalone proof: Open scene opens every file the catalog names (2026-09-30).

mayapy, no GUI (it opens scenes):

    mayapy docs/superpowers/plans/verify_open_scene_files.py

For every character row and every weapon, `opener.open_asset` on the repo's
own asset: the scene is that file, it reads unmodified, a `.ma` came in with
its script nodes OFF and every shipped image pointed at the plugin's copy, an
`.fbx` came in whole under the `exmerge` a UE-bridge import leaves (and the
mode is put back). The menu half is verify_open_scene_menu.py's.

Spec: docs/superpowers/specs/2026-09-30-open-scene-menu-design.md
"""

import os
import sys

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, REPO)

import maya.standalone  # noqa: E402
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

for plugin in ("fbxmaya", "matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except Exception:                                        # noqa: BLE001
        pass

from maya_scenesetup import catalog, colour, opener  # noqa: E402

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("[{0}] {1}{2}".format("PASS" if ok else "FAIL", name,
                                (" - " + str(detail)) if detail != "" else ""))


def scene():
    return (cmds.file(query=True, sceneName=True) or "").replace("\\", "/")


def shipped_images():
    nodes = [n for n in cmds.ls(type="file") or []
             if cmds.attributeQuery(colour.ASSET_IMAGE, node=n, exists=True)]
    paths = [cmds.getAttr(n + ".fileTextureName").replace("\\", "/") for n in nodes]
    good = [p for p in paths if p.startswith(REPO + "/assets/") and os.path.isfile(p)]
    return len(nodes), len(good)


rows = [(e.label, catalog.character_file(e), e.textured) for e in catalog.CHARACTERS]
rows += [(w.label, w.path, False) for w in catalog.WEAPONS]
for label, path, textured in rows:
    cmds.file(new=True, force=True)
    if path.lower().endswith(".fbx"):
        mel.eval("FBXImportMode -v exmerge")
    text = opener.open_asset(path, label)
    name = os.path.basename(path)
    gate("{0}: the scene is {1}".format(label, name), scene() == path, scene())
    gate("{0}: the line names assets/{1}".format(label, name),
         text.startswith("Opened {0} - assets/{1}".format(label, name)), text)
    gate("{0}: reads unmodified".format(label),
         not cmds.file(query=True, modified=True))
    meshes = cmds.ls(type="mesh", noIntermediate=True) or []
    gate("{0}: its geometry came in".format(label), len(meshes) > 0, len(meshes))
    if path.lower().endswith(".fbx"):
        gate("{0}: the import mode is put back".format(label),
             (mel.eval("FBXImportMode -q") or "").strip() == "exmerge",
             mel.eval("FBXImportMode -q"))
    else:
        scripts = [s for s in cmds.ls(type="script") or []
                   if s not in ("uiConfigurationScriptNode",
                                "sceneConfigurationScriptNode")]
        gate("{0}: no script node of its own".format(label), not scripts, scripts)
        count, good = shipped_images()
        if textured:
            gate("{0}: every shipped image on the plugin's copy".format(label),
                 count > 0 and good == count, (count, good))

# a missing file and a modified scene in batch (no dialog there: it goes on)
cmds.file(new=True, force=True)
text = opener.open_asset(REPO + "/assets/Nope.ma", "Nope")
gate("a missing file opens nothing and says so",
     text == "Nope: the plugin has no assets/Nope.ma - nothing opened." and scene() == "",
     text)

cmds.file(new=True, force=True)
print("{0} of {1} gates failed".format(RESULTS.count(False), len(RESULTS)))
maya.standalone.uninitialize()
