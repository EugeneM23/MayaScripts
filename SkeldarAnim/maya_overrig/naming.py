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


def detect_prefix(names, known_names):
    """Return the name prefix this skeleton carries, or "" if it carries none.

    Rigs are routinely imported with every joint prefixed -- `prefix_root`,
    `char_spine_01`. The prefix is derived once for the whole skeleton by asking
    which candidate lines up the most known names, and is adopted only if it
    beats using no prefix at all.

    Deriving it skeleton-wide rather than per name is what keeps the UE export
    helpers honest. `ik_hand_l` ends with `hand_l`, so a per-name suffix match
    would happily read it as a prefixed `hand_l`; here "ik_" only ever wins if
    it explains more of the skeleton than the plain names do, which on a real
    UE5 rig it never does.
    """
    known = set(known_names)
    leaves = set(names)
    baseline = len(leaves & known)

    counts = {}
    for leaf_name in leaves:
        for known_name in known:
            if len(leaf_name) > len(known_name) and leaf_name.endswith(known_name):
                candidate = leaf_name[:-len(known_name)]
                counts[candidate] = counts.get(candidate, 0) + 1

    if not counts:
        return ""

    # sorted() first so ties resolve the same way every run.
    best = max(sorted(counts), key=lambda candidate: counts[candidate])
    return best if counts[best] > baseline else ""


def strip_prefix(mapping, prefix):
    """Re-key a hierarchy map with `prefix` removed from each name.

    Names that do not start with the prefix are kept as they are.
    """
    if not prefix:
        return mapping
    stripped = {}
    for name, dag in mapping.items():
        key = name[len(prefix):] if name.startswith(prefix) else name
        stripped.setdefault(key, dag)
    return stripped


def find_skeleton_roots(exclude_under=()):
    """Every topmost joint in the scene -- one per skeleton.

    `exclude_under` lists DAG paths whose contents should be ignored, along
    with the paths themselves. Rig setups built over a skeleton carry joints of
    their own: OverRig's IK puts `fin_jnt` and `knee_ctrl` joints inside the
    groups it creates, and since none of them has a joint parent, every one
    would otherwise register as another skeleton -- which stops the picker
    auto-connecting the moment anything has been built.
    """
    excluded = tuple(exclude_under)
    inside = tuple(path + "|" for path in excluded)

    roots = []
    for joint in cmds.ls(type="joint", long=True) or []:
        if joint in excluded or (inside and joint.startswith(inside)):
            continue
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
