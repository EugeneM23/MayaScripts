"""Bind the picker to one skeleton and resolve joint names inside it.

The picker is bound to a specific skeleton root rather than searching the whole
scene, so several characters can coexist without the panel guessing which one
is meant. Every lookup is scoped to the bound root's subtree, which is also
what makes namespaces and per-character prefixes a non-issue: `hero:spine_03`
and `spine_03` live in different subtrees and never compete.

Fuzzy suffix matching is deliberately NOT supported. On a UE5 skeleton it would
make `hand_l` match the export helper `ik_hand_l`, and `foot_l` match
`ik_foot_l`. Names are compared exactly, after the namespace is stripped.
"""

import maya.cmds as cmds


def leaf(dag_path):
    """Strip DAG path and namespace: '|a|ns:hand_l' -> 'hand_l'."""
    return dag_path.split("|")[-1].split(":")[-1]


def find_root(node):
    """Return the skeleton root reachable from `node`, or None.

    A joint walks up through its joint parents to the top of the chain, so
    clicking any bone in the character is enough. A non-joint -- the enclosing
    group, say -- yields the shallowest joint beneath it.
    """
    if not node:
        return None

    if cmds.objectType(node) == "joint":
        current = node
        while True:
            parents = cmds.listRelatives(current, parent=True, type="joint",
                                         fullPath=True)
            if not parents:
                return current
            current = parents[0]

    below = cmds.ls(node, dagObjects=True, type="joint", long=True) or []
    if not below:
        return None
    return min(below, key=lambda j: j.count("|"))


def hierarchy_map(root):
    """Map leaf name -> long DAG path for `root` and every joint under it.

    Namespaces are stripped from the keys but kept in the values, so a picker
    bound to `hero:root` looks names up as `spine_03` and still selects
    `|hero:...|hero:spine_03`.
    """
    mapping = {}
    for dag in cmds.ls(root, dagObjects=True, type="joint", long=True) or []:
        mapping.setdefault(leaf(dag), dag)
    return mapping


def find_skeleton_roots():
    """Every topmost joint in the scene -- one per skeleton."""
    roots = []
    for joint in cmds.ls(type="joint", long=True) or []:
        if not cmds.listRelatives(joint, parent=True, type="joint",
                                  fullPath=True):
            roots.append(joint)
    return roots


def uuid_of(node):
    """UUID of a node, or None. Survives renaming and reparenting."""
    if not node:
        return None
    found = cmds.ls(node, uuid=True) or []
    return found[0] if found else None


def path_from_uuid(uuid):
    """Long DAG path for a UUID, or None if the node is gone."""
    if not uuid:
        return None
    found = cmds.ls(uuid, long=True) or []
    return found[0] if found else None
