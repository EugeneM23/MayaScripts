"""Which character to act on, and where its weapon bone is.

Since 2026-09-07 the answer is an AdvancedSkeleton rig's, and since
2026-09-08 there may be several of them (`maya_rigs`). Read in order (the
animator: «какой сейчас персонаж рабочий мы понимаем по выделению,
достаточно выделить любой контрол персонажа»):

1. the SELECTION -- a node of a rig (any control, bone or mesh in its
   namespace; a node under a root-namespace rig's group or skeleton) means
   that rig's game skeleton; a bare joint means its topmost joint; anything
   else means nothing. Two different answers is no answer;
2. the ONLY rig's skeleton, when exactly one rig stands in the scene;
3. the ONLY skeleton, when there is no rig and exactly one skeleton;
4. otherwise none -- arming the wrong character in silence is worse than
   saying no.

The bone is looked up inside the chosen root's subtree, never scene-wide.
That is what makes a namespace, a per-joint prefix or a second skeleton in
the scene a non-issue -- a scene-wide `ls("weapon_r")` would arm whichever
character Maya happened to list first.
"""

import maya.cmds as cmds

import maya_rigs
from maya_overrig import bodymap
from maya_overrig import naming


# ------------------------------------------------------------------ the rig

def rigs():
    """Every AdvancedSkeleton rig in the scene (`maya_rigs.rigs`)."""
    return maya_rigs.rigs()


def rig_root():
    """The game skeleton of the CURRENT rig (selection, else the sole rig),
    or None."""
    rig, _ = maya_rigs.current_rig()
    return (rig.skeleton_root or None) if rig else None


def is_rig_skeleton(root):
    """True when `root` is the game skeleton some rig drives."""
    return bool(root) and any(rig.skeleton_root == root for rig in rigs())


def inside(path, group):
    """True when `path` is `group` or lies under it. Pure."""
    return maya_rigs.under(path, group)


# --------------------------------------------------------------- the policy

def selection_roots(selection, rigs_, top_joint):
    """What each selected path means, as a root or None. Pure.

    `rigs_` are the scene's rigs; `top_joint(path)` answers a joint's
    topmost joint and None for anything that is not a joint -- the one
    scene question this needs, injected so the policy runs without a scene.
    A rig's node means its skeleton root (None when it drives none).
    """
    roots = []
    for path in selection or []:
        rig = maya_rigs.rig_of(path, rigs_)
        if rig is not None:
            roots.append(rig.skeleton_root or None)
        else:
            roots.append(top_joint(path))
    return roots


def choose_root(selection_roots_, rig_roots, scene_roots):
    """Selection, then the only rig, then the only skeleton. Pure.

    Several rigs and nothing selected is no answer: the wrong character in
    silence is exactly what this exists to prevent.
    """
    # dict.fromkeys keeps order and collapses the repeats that come from
    # selecting several controls or bones of the same character.
    selected = list(dict.fromkeys(root for root in selection_roots_ if root))
    if len(selected) == 1:
        return selected[0]
    if selected:
        return None
    rig_roots = [root for root in rig_roots if root]
    if len(rig_roots) == 1:
        return rig_roots[0]
    if rig_roots:
        return None
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

    rigs_ = rigs()

    def top_joint(path):
        if cmds.objExists(path) and cmds.objectType(path) == "joint":
            return naming.find_root(path)
        return None

    selection = cmds.ls(selection=True, long=True) or []
    # The rigs' own deformation joints have no joint parent and would count
    # as skeletons of their own; the game skeletons they drive are the ones.
    scene_roots = [root for root in builder.character_roots()
                   if not any(inside(root, rig.group) for rig in rigs_)]
    root = choose_root(selection_roots(selection, rigs_, top_joint),
                       [rig.skeleton_root for rig in rigs_], scene_roots)
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
