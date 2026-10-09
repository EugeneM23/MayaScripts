"""The Cascadeur side of the bridge. The only module that imports csc.

It runs inside Cascadeur. The call shapes come from the stub files
resources/scripts/stubs/csc/fbx.pyi and app/__init__.pyi, and from
pycsc/general/wrapping.py. Task 0's live probe confirms the lookups marked
PROBE below; docs/superpowers/plans/cascadeur_probe_results.md records them.
"""

import os

import csc
import csc.app
from pycsc.general import wrapping

# What Cascadeur says when its licence cannot write FBX (probe, 2026-10-09:
# the free and trial builds write .CASC only, and export_joints writes nothing).
EXPORT_BLOCKED = ("Cascadeur wrote no FBX - its licence does not allow FBX "
                  "export (free and trial builds write .CASC only). Nothing "
                  "was written to Unreal or Shared.")


def _app():
    return csc.app.get_application()


def current_scene():
    """The csc view scene of the tab in front."""
    return _app().current_scene()


def _loader(scene=None):
    tools = _app().get_tools_manager()
    return tools.get_tool("FbxSceneLoader").get_fbx_loader(scene or current_scene())


def import_clip_onto(character_path, clip_path):
    """A new scene tab with the character (its mesh and skeleton), and the clip's
    animation on that skeleton. The character is the scene import, so the clip
    lands on its joints by name; the clip's own skeleton is not brought in."""
    wrapping.new_scene()
    _loader(current_scene()).import_scene(character_path.replace("\\", "/"))
    _loader(current_scene()).import_animation(clip_path.replace("\\", "/"))


def export_skeleton(path):
    """The current scene's joints and their animation into `path` (bones only).

    Raises RuntimeError with EXPORT_BLOCKED when no file was written: the
    licence refusal arrives as a message, not as an exception.
    """
    if os.path.exists(path):
        os.remove(path)
    _loader().export_joints(path.replace("\\", "/"))
    if not os.path.isfile(path):
        raise RuntimeError(EXPORT_BLOCKED)


def skeleton_roots():
    """Names of the scene's root objects (probe: get_scene_objects with
    only_roots=True and no type filter found the rig's 'root'; a type filter
    of 'joint' or 'bone' found nothing)."""
    domain = wrapping.get_current_scene().domain_scene()
    return [obj.name for obj in domain.get_scene_objects(only_roots=True)]


def animation_frames():
    """The animation's frame count (probe: a 37-frame clip reads 38)."""
    domain = wrapping.get_current_scene().domain_scene()
    return domain.get_animation_size()


def confirm(text, on_yes):
    """Cascadeur's own two-button dialog. `on_yes` runs only on Overwrite; the
    call returns at once (the dialog is asynchronous, the view never blocks)."""
    import csc.view
    buttons = [csc.view.DialogButton("Overwrite", on_yes),
               csc.view.DialogButton(csc.view.StandardButton.Cancel)]
    csc.view.DialogManager.instance().show_buttons_dialog(
        "Export to uasset", text, buttons)


def scene_fps():
    """None: the probe found no call that reads the scene's frame rate (the
    loader has no fps attribute, the scene exposes only the current frame).
    rules.fps_problem treats None as unknown and says nothing."""
    return None
