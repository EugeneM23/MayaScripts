"""Which character to arm, and where its weapon bone is.

The picker holds its binding in the live window, so when it is open that is
the answer -- the whole point of the module is to act on the character the
animator is already driving. With no picker the module binds the same way the
picker itself does, and refuses to guess between two candidates: arming the
wrong character in silence is worse than saying no.

The bone is looked up inside the bound root's subtree, never scene-wide. That
is what makes a namespace, a per-joint prefix or a second character in the
scene a non-issue -- and a scene-wide `ls("weapon_r")` would arm whichever
character Maya happened to list first.
"""

import maya.cmds as cmds

from maya_overrig import bodymap
from maya_overrig import naming


def picker_root():
    """The root the Rig Picker is bound to, or None if it is not open."""
    try:
        from maya_overrig import picker_window
    except ImportError:
        return None  # no Qt in this session; the fallbacks still work
    return picker_window.bound_root()


def choose_root(picker_root_path, selection_roots, scene_roots):
    """Decide which skeleton to act on. Pure: the scene arrives as data."""
    if picker_root_path:
        return picker_root_path

    # dict.fromkeys keeps order and collapses the repeats that come from
    # selecting several bones of the same character.
    selected = list(dict.fromkeys(root for root in selection_roots if root))
    if len(selected) == 1:
        return selected[0]
    if selected:
        return None

    if len(scene_roots) == 1:
        return scene_roots[0]
    return None


def current_root():
    """Ask the scene the three questions and let `choose_root` decide."""
    from maya_overrig import builder  # drags maya.mel in; not needed to import

    selection = cmds.ls(selection=True, long=True) or []
    return choose_root(picker_root(),
                       [naming.find_root(node) for node in selection],
                       builder.character_roots())


def bone_in(hierarchy, bone_name):
    """Long path of `bone_name` in a prefix-stripped hierarchy map, or None."""
    return hierarchy.get(bone_name)


def resolve_bone(root, bone_name):
    """Long path of `bone_name` inside `root`'s subtree, or None.

    The prefix is derived once for the whole skeleton, exactly as the picker
    derives it, so a rig imported as `char_weapon_r` resolves too.
    """
    if not root:
        return None
    raw = naming.hierarchy_map(root)
    known = [button.joint for button in bodymap.BUTTONS]
    prefix = naming.detect_prefix(raw, known)
    return bone_in(naming.strip_prefix(raw, prefix), bone_name)
