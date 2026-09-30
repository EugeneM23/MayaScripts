"""Open scene: a character's or a weapon's own file, opened as the scene.

2026-09-30, the animator: «когда я нажимал правой клавишей по иконке рига или
оружия то у меня появлялось опция Open scene и при нажатии на нее у нас бы
открывался соответствующий фаил». The right button on a portrait in the
Characters grid, or on a weapon in the Weapons inventory, offers it; this is
what it does with the file the catalog names (`catalog.character_file`, a
weapon row's `path`) -- the plugin's own copy under assets/.

- a modified scene gets Maya's own «save changes?» first, and Cancel changes
  nothing;
- a `.ma`/`.mb` opens with its script nodes OFF (the Shared rule: nothing in a
  file runs on the way in -- the Manny scenes this studio had were infected,
  trap "vaccine"), and what the scene configuration node would have set --
  the playback and animation ranges -- is read out of it and applied, never
  evaluated (trap 129); a vaccine node that got in anyway is deleted; the
  shipped textures, which the assets name relatively (`colour.ASSET_IMAGE`),
  are pointed at the plugin's own images;
- an `.fbx` opens through `fbximport.open_file`, the import-mode guard of
  trap 33 (under `exmerge` the open brings nothing);
- either way the scene then reads as unmodified: it is the file as it is on
  disk (an FBX open reads as a change otherwise).

The line names the file under the plugin and says a save writes into the
plugin, which the next update replaces: Save As keeps a change.

Shared (maya_share) opens a colleague's scene the same way and keeps its own
copy of these few lines: its tests drive it on a fake `cmds` of their own.

Spec: docs/superpowers/specs/2026-09-30-open-scene-menu-design.md
"""

import os

import maya.cmds as cmds
import maya.mel as mel

from maya_scenesetup import catalog, character, colour, fbximport

SCENE_CONFIG = "sceneConfigurationScriptNode"


# ------------------------------------------------------------------ policy

def plugin_relative(path):
    """`path` as the plugin names it -- `assets/Manny_Rig.ma` -- or the path
    itself when it lies outside the plugin. Pure."""
    norm = (path or "").replace("\\", "/")
    container = catalog._CONTAINER.replace("\\", "/").rstrip("/")
    if container and norm.lower().startswith(container.lower() + "/"):
        return norm[len(container) + 1:]
    return norm


def opened_message(label, path, note=""):
    """What the line says after the open."""
    return ("Opened {0} - {1}{2}. Save As to keep changes: a save writes into "
            "the plugin, and an update replaces its files.").format(
                label, plugin_relative(path), note)


def missing_message(label, path):
    return "{0}: the plugin has no {1} - nothing opened.".format(
        label, plugin_relative(path))


CANCELLED = "Open scene cancelled - nothing changed."


# ------------------------------------------------------------------- scene

def save_changes():
    """Maya's own «save changes?» for a modified scene; True to go on."""
    if cmds.about(batch=True):
        return True
    try:
        return bool(mel.eval('saveChanges("")'))
    except RuntimeError:
        if not cmds.file(query=True, modified=True):
            return True
        answer = cmds.confirmDialog(
            title="Open scene", message="The scene has unsaved changes. "
                                        "Open the file anyway?",
            button=["Open", "Cancel"], defaultButton="Cancel",
            cancelButton="Cancel", dismissString="Cancel")
        return answer == "Open"


def restore_playback():
    """The opened scene's ranges, parsed out of its scene configuration node
    (which did not run) and applied. True when applied."""
    import maya_sharerecords
    if not cmds.objExists(SCENE_CONFIG):
        return False
    values = maya_sharerecords.playback_from_script(
        cmds.scriptNode(SCENE_CONFIG, query=True, beforeScript=True) or "")
    if not values:
        return False
    cmds.playbackOptions(**values)
    return True


def _clean():
    """After a scene open: a vaccine node out, the shipped images on the
    plugin's own copy. Returns a note naming only what went wrong."""
    removed = []
    for node in character.malware_nodes(cmds.ls(type="script") or []):
        if cmds.objExists(node):
            try:
                cmds.lockNode(node, lock=False)
                cmds.delete(node)
                removed.append(node)
            except Exception:                                # noqa: BLE001
                pass
    _relinked, missing = colour.relink_images(cmds.ls(type="file") or [],
                                              catalog.asset_path)
    notes = []
    if missing:
        notes.append("missing in the plugin: " + ", ".join(
            os.path.basename(m) for m in missing[:3]))
    if removed:
        notes.append("removed malware script node(s): " + ", ".join(removed))
    return (" (" + "; ".join(notes) + ")") if notes else ""


def open_asset(path, label):
    """Open the plugin's `path` as the scene; returns what the line says."""
    if not path or not os.path.isfile(path):
        return missing_message(label, path)
    if not save_changes():
        return CANCELLED
    note = ""
    if character.is_fbx(path):
        fbximport.open_file(path)
    else:
        cmds.file(path, open=True, force=True, executeScriptNodes=False,
                  ignoreVersion=True, prompt=False)
        restore_playback()
        note = _clean()
    # The scene is the file on disk: the relink wrote attributes, and an FBX
    # comes in as an import into a new scene, which Maya reads as a change
    # (measured 2026-09-30 on every catalog weapon) - the next Open scene
    # would ask to save an untouched file.
    cmds.file(modified=False)
    return opened_message(label, path, note)
