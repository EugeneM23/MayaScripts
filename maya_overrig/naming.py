"""Resolve logical joint names to objects in the current Maya scene.

Namespaces are tolerated: `char:hand_l` satisfies a request for `hand_l`.

Fuzzy prefix matching is deliberately NOT supported. On a UE5 skeleton a suffix
match for `hand_l` would also hit the export helper `ik_hand_l`, and `foot_l`
would hit `ik_foot_l`. Resolution is therefore an exact comparison of the leaf
name after any namespace is stripped.
"""

import maya.cmds as cmds


def leaf(dag_path):
    """Strip DAG path and namespace: '|a|ns:hand_l' -> 'hand_l'."""
    return dag_path.split("|")[-1].split(":")[-1]


def resolve(joint):
    """Return the long DAG path of `joint`, or None if it is not in the scene.

    When several joints share the leaf name -- two characters in one scene --
    the first is returned and a warning is issued.
    """
    matches = [j for j in (cmds.ls(type="joint", long=True) or [])
               if leaf(j) == joint]
    if not matches:
        return None
    if len(matches) > 1:
        cmds.warning(
            "OverRig picker: {0} matches for '{1}', using {2}".format(
                len(matches), joint, matches[0]))
    return matches[0]


def resolve_many(joints):
    """Map each name that exists in the scene to its long DAG path.

    Names that do not resolve are simply absent from the result. Walks the joint
    list once rather than calling resolve() per name.
    """
    scene = {}
    for dag in cmds.ls(type="joint", long=True) or []:
        scene.setdefault(leaf(dag), dag)
    return {name: scene[name] for name in joints if name in scene}
