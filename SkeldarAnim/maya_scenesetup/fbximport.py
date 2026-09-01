"""Importing an FBX into the current scene, with trap 33 handled once.

The FBX plugin's import MODE is one global setting for the whole Maya
session, and it DOES reach `cmds.file` even though the curve-related
settings do not (trap 22, from the other side). `maya_uebridge` leaves it
on `exmerge`, where the importer matches names against what is already in
the scene and **creates nothing at all** -- so after any animation import
from Unreal, a weapon silently stopped arriving, and a character would too.
Set it for every import; inherit never.

This lived inside `attach.import_model` until 2026-09-01, when Add
Character needed the same thing for `UE4_Mannequin.fbx`. One home, because
a fix for a silent failure that exists in two copies is a fix that will
exist in one copy soon enough.

`cmds.file` rather than the plugin's `FBXImport`, which is the opposite of
what the UE bridge does and is deliberate: trap 22 is about losing
animation curves, and neither a weapon model nor a reference skeleton has
any, while `returnNewNodes` gives the exact node list `FBXImport` cannot
report at all.
"""

import maya.cmds as cmds
import maya.mel as mel

MODE = "add"


def ensure_plugin():
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya", quiet=True)


def _quietly(command):
    """A flag missing on some Maya build must not stop an import."""
    try:
        return mel.eval(command)
    except Exception:
        return None


def import_nodes(path):
    """Import `path` and return every node that arrived, as long names."""
    ensure_plugin()

    previous = _quietly("FBXImportMode -q")
    _quietly("FBXImportMode -v {0}".format(MODE))
    # The scene's frame rate is never ours to write. `cmds.file` ignores the
    # FBXImport* curve settings anyway, so this is belt-and-braces -- but the
    # rule is worth stating where an import happens.
    _quietly("FBXImportSetMayaFrameRate -v false")
    try:
        return cmds.file(path, i=True, type="FBX", returnNewNodes=True,
                         ignoreVersion=True) or []
    finally:
        if previous:
            _quietly("FBXImportMode -v {0}".format(previous))
