"""Which character to act on, and where its weapon bone is.

Since 2026-09-07 the answer is the AdvancedSkeleton rig's, read three ways in
order (the animator: «какой сейчас персонаж рабочий мы понимаем по выделению,
достаточно выделить любой контрол персонажа»):

1. the SELECTION -- a node under the rig's top group (any control) means the
   rig's game skeleton; a joint means its topmost joint; a mesh or a locator
   means nothing. Two different answers is no answer;
2. the RIG's skeleton, when a rig stands in the scene;
3. the ONLY skeleton, when there is exactly one;
4. otherwise none -- arming the wrong character in silence is worse than
   saying no.

The picker's Connect used to sit at the top of this list; the picker is off
the shelf now (`skeldar_features.PICKER`), and the rig took its place as
"the character the animator is working on".

The bone is looked up inside the chosen root's subtree, never scene-wide.
That is what makes a namespace, a per-joint prefix or a second skeleton in
the scene a non-issue -- a scene-wide `ls("weapon_r")` would arm whichever
character Maya happened to list first.
"""

import maya.cmds as cmds

from maya_overrig import bodymap
from maya_overrig import naming


# ------------------------------------------------------------------ the rig

def rig_group():
    """The rig's top group -- the top ancestor of `Main` -- or None.

    Not `|Group` by name: a `.ma` import renames a clashing top node with
    the file stem, so the group is found from a node the retarget already
    addresses by name.
    """
    if not (cmds.objExists("ControlSet") and cmds.objExists("Main")):
        return None
    main = cmds.ls("Main", long=True) or []
    parts = [p for p in main[0].split("|") if p] if main else []
    return "|" + parts[0] if parts else None


def rig_root():
    """The game skeleton the rig drives, or None without a rig.

    Schema-blind: `rig_paths`/`rig_skeleton_root` read the constraints our
    deformation joints leave on the game joints, and both retarget modules
    carry the same pair -- the PlayerMale one is imported because it asks
    nothing of the bone names.
    """
    if rig_group() is None:
        return None
    import maya_pmretarget  # lazy: a cmds module, but a big one
    return maya_pmretarget.rig_skeleton_root(maya_pmretarget.rig_paths()) \
        or None


def inside(path, group):
    """True when `path` is `group` or lies under it. Pure."""
    return bool(group) and (path == group or path.startswith(group + "|"))


# --------------------------------------------------------------- the policy

def selection_roots(selection, rig_group_path, rig_root_path, top_joint):
    """What each selected path means, as a root or nothing. Pure.

    `top_joint(path)` answers a joint's topmost joint and None for anything
    that is not a joint -- the one scene question this needs, injected so
    the policy runs without a scene.
    """
    roots = []
    for path in selection or []:
        if inside(path, rig_group_path):
            roots.append(rig_root_path)
        else:
            roots.append(top_joint(path))
    return roots


def choose_root(selection_roots_, rig_root_path, scene_roots):
    """Selection, then the rig, then the only skeleton. Pure."""
    # dict.fromkeys keeps order and collapses the repeats that come from
    # selecting several controls or bones of the same character.
    selected = list(dict.fromkeys(root for root in selection_roots_ if root))
    if len(selected) == 1:
        return selected[0]
    if selected:
        return None
    if rig_root_path:
        return rig_root_path
    if len(scene_roots) == 1:
        return scene_roots[0]
    return None


def current_root():
    """Ask the scene the three questions and let `choose_root` decide.

    Whatever it decides also becomes the picker modules' ACTIVE character:
    `maya_overrig.active` still underlies the guards in Add/Remove Weapon
    that protect files rigged before 2026-09-07, and those read the rig
    through this character's manifests.
    """
    from maya_overrig import active  # drags maya.mel in; not needed to import
    from maya_overrig import builder

    group, rig = rig_group(), rig_root()

    def top_joint(path):
        if cmds.objExists(path) and cmds.objectType(path) == "joint":
            return naming.find_root(path)
        return None

    selection = cmds.ls(selection=True, long=True) or []
    # The rig's own deformation joints have no joint parent and would count
    # as skeletons of their own; the game skeleton it drives is the one.
    scene_roots = [root for root in builder.character_roots()
                   if not inside(root, group)]
    root = choose_root(selection_roots(selection, group, rig, top_joint),
                       rig, scene_roots)
    active.set_root(root)
    return root


# ----------------------------------------------------------------- the bone

def bone_in(hierarchy, bone_name):
    """Long path of `bone_name` in a prefix-stripped hierarchy map, or None."""
    return hierarchy.get(bone_name)


def scene_map(root):
    """Leaf name -> long path for the whole skeleton, prefix stripped.

    The prefix is derived once for the skeleton, exactly as the picker
    derives it, so a rig imported as `char_weapon_r` resolves too. This is
    also the shape the rig's own entry points take.
    """
    if not root:
        return {}
    raw = naming.hierarchy_map(root)
    known = [button.joint for button in bodymap.BUTTONS]
    return naming.strip_prefix(raw, naming.detect_prefix(raw, known))


def resolve_bone(root, bone_name):
    """Long path of `bone_name` inside `root`'s subtree, or None."""
    return bone_in(scene_map(root), bone_name)
