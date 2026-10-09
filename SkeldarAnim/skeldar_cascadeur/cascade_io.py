"""The Cascadeur side of the bridge. The only module that imports csc.

It runs inside Cascadeur. The call shapes come from the stub files
resources/scripts/stubs/csc/fbx.pyi and app/__init__.pyi, and from
pycsc/general/wrapping.py. Task 0's live probe confirms the lookups marked
PROBE below; docs/superpowers/plans/cascadeur_probe_results.md records them.
"""

import csc
import csc.app
from pycsc.general import wrapping

# PROBE: the object-type name Cascadeur's scene query uses for a skeleton's
# joints. Task 0 writes the confirmed value into cascadeur_probe_results.md.
JOINT_TYPE = "joint"


def _app():
    return csc.app.get_application()


def current_scene():
    """The csc view scene of the tab in front."""
    return _app().current_scene()


def _loader(scene=None):
    tools = _app().get_tools_manager()
    return tools.get_tool("FbxSceneLoader").get_fbx_loader(scene or current_scene())


def import_clip_new_tab(path):
    """The FBX into a new scene tab (scene import: skeleton and animation)."""
    wrapping.new_scene()
    _loader(current_scene()).import_scene(path.replace("\\", "/"))


def export_skeleton(path):
    """The current scene's joints and their animation into `path` (bones only)."""
    _loader().export_joints(path.replace("\\", "/"))


def skeleton_roots():
    """Names of the root joints in the current scene.

    PROBE: the domain-scene query below is the shape the probe tries first;
    if the probe recorded a different chain, change this function to it.
    """
    domain = wrapping.get_current_scene().domain_scene()
    return [obj.name for obj in domain.get_scene_objects(only_roots=True,
                                                         of_type=JOINT_TYPE)]


def animation_frames():
    """The animation's frame count, or None when it cannot be read.

    PROBE: get_animation_size() is the call the stubs name; the probe confirms it.
    """
    domain = wrapping.get_current_scene().domain_scene()
    return domain.get_animation_size()


def scene_fps():
    """The scene's frame rate, or None when no call reads it.

    PROBE: the stubs expose no scene fps getter; if the probe found one, return
    it here. Until then None means the fps warning is skipped (rules.fps_problem).
    """
    return None
