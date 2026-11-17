"""Our markers that name a node by UUID, pointed again at the node when that UUID is gone
(2026-11-17, the animator: «не можу забейкати ейм»).

Maya gives every IMPORTED node a new UUID (`cmds.file(i=True)`; an open keeps them, measured in
mayapy), and Scene Tabs bring every tab after the first in by import. The markers are strings, so
they keep the old UUIDs: a knot no longer knows its object, Connections showed Default over a
weapon in Aim Mode, and Bake deleted a knot without baking it. A tab saved to a file carries the
dead markers into it.

What a dead marker meant is still in the scene graph, so it is read back from there:
  - a knot's constraint (`skeldarKnotOf`) and 1P Setup's arm constraints (`skeldar1PArm`): the knot
    the constraint follows;
  - a knot (`skeldarKnotSource`): the object its own constraint drives;
  - a double knot's inner node (`skeldarKnotInner`): the knot it lies in;
  - an Aim Mode group (the weapon's, the camera's): the node its name was made from
    (`<node>_aim`), and its aimConstraint: the node of the group holding its controllers.
A marker that the graph does not answer with exactly one node is left as it is. The pure half
(`is_uuid`, `one`, `aim_base`) is unit-tested; `heal` needs Maya.
"""

import re

_UUID = re.compile(r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$")
_AIM_SUFFIX = re.compile(r"_aim\d*$")

KNOT_OF = "skeldarKnotOf"
ARM_1P = "skeldar1PArm"
KNOT_SOURCE = "skeldarKnotSource"
KNOT_INNER = "skeldarKnotInner"
#  (the group's marker, its aimConstraint's marker) - weaponaim.KIND, cameraaim.KIND
AIM_MARKERS = (("skeldarWeaponAim", "skeldarWeaponAimOf"),
               ("skeldarCameraAim", "skeldarCameraAimOf"))


def is_uuid(text):
    return bool(text) and bool(_UUID.match(text))


def one(found):
    """The single node `found` names (repeats allowed), else None."""
    unique = []
    for node in found:
        if node and node not in unique:
            unique.append(node)
    return unique[0] if len(unique) == 1 else None


def aim_base(group_leaf):
    """`ns:Dagger_aim1` -> `ns:Dagger`: the node an Aim Mode group was named after, or None."""
    namespace, _sep, name = group_leaf.rpartition(":")
    if not _AIM_SUFFIX.search(name):
        return None
    base = _AIM_SUFFIX.sub("", name)
    if not base:
        return None
    return (namespace + ":" + base) if namespace else base


# ------------------------------------------------------------------ Maya

def _cmds():
    import maya.cmds as cmds
    return cmds


def _carrying(attr, namespace=None):
    """Every node carrying `attr`, long paths (all namespaces, or under `namespace`)."""
    cmds = _cmds()
    pattern = ("%s:*.%s" % (namespace, attr)) if namespace else ("*." + attr)
    return cmds.ls(pattern, recursive=True, objectsOnly=True, long=True) or []


def _get(node, attr):
    try:
        return _cmds().getAttr(node + "." + attr)
    except (RuntimeError, ValueError):
        return None


def _dead(value):
    if not is_uuid(value):
        return False
    try:
        return not _cmds().ls(value)
    except RuntimeError:                       # a string ls cannot parse names no node
        return False


def _uuid(node):
    found = _cmds().ls(node, uuid=True) or []
    return found[0] if found else None


def _parent(node):
    found = _cmds().listRelatives(node, parent=True, fullPath=True) or []
    return found[0] if found else None


def _targets(con):
    cmds = _cmds()
    query = {"parentConstraint": cmds.parentConstraint, "orientConstraint": cmds.orientConstraint,
             "pointConstraint": cmds.pointConstraint, "aimConstraint": cmds.aimConstraint,
             "scaleConstraint": cmds.scaleConstraint}.get(cmds.nodeType(con))
    if query is None:
        return []
    return cmds.ls(query(con, query=True, targetList=True) or [], long=True) or []


def _knot_top(node):
    from maya_tools import knots
    return knots.top_of(node)


def plan(namespace=None):
    """[(node, attr, old uuid, new uuid)] for every dead marker the graph answers."""
    cmds = _cmds()
    out = []
    #  constraints that follow a knot: the knot of their target
    con_knot = {}
    for attr in (KNOT_OF, ARM_1P):
        for con in _carrying(attr, namespace):
            value = _get(con, attr)
            if not _dead(value):
                continue
            top = one([_knot_top(t) for t in _targets(con)])
            if top:
                new = _uuid(top)
                out.append((con, attr, value, new))
                if attr == KNOT_OF:
                    con_knot[con] = new
    #  a knot's object: what its own constraint drives
    for top in _carrying(KNOT_SOURCE, namespace):
        value = _get(top, KNOT_SOURCE)
        if not _dead(value):
            continue
        me = _uuid(top)
        driven = [_parent(con) for con in _carrying(KNOT_OF)
                  if con_knot.get(con, _get(con, KNOT_OF)) == me]
        obj = one(driven)
        if obj:
            out.append((top, KNOT_SOURCE, value, _uuid(obj)))
    #  a double knot's inner node: the knot it lies in
    for inner in _carrying(KNOT_INNER, namespace):
        value = _get(inner, KNOT_INNER)
        if not _dead(value):
            continue
        top = _knot_top(_parent(inner) or "")
        if top:
            out.append((inner, KNOT_INNER, value, _uuid(top)))
    #  Aim Mode groups and their constraints: the node the group was named after
    for group_attr, con_attr in AIM_MARKERS:
        for group in _carrying(group_attr, namespace):
            value = _get(group, group_attr)
            #  an empty group is a leftover: pointing it at the node would give it two groups
            if not _dead(value) or not cmds.listRelatives(group, children=True):
                continue
            node = _aim_node(group)
            if node:
                out.append((group, group_attr, value, _uuid(node)))
        for con in _carrying(con_attr, namespace):
            value = _get(con, con_attr)
            if not _dead(value):
                continue
            group = one([_parent(t) for t in _targets(con)])
            node = _aim_node(group) if group else None
            if node:
                out.append((con, con_attr, value, _uuid(node)))
    return out


def _aim_node(group):
    base = aim_base(group.split("|")[-1])
    if not base:
        return None
    cmds = _cmds()
    return one([n for n in cmds.ls(base, long=True) or [] if cmds.objectType(n, isAType="transform")])


def heal(namespace=None):
    """Every dead marker the graph answers written again (in the caller's undo chunk, if any).
    The number written. Never raises: a scene it cannot read is left as it is."""
    try:
        fixes = plan(namespace)
        cmds = _cmds()
        for node, attr, _old, new in fixes:
            cmds.setAttr(node + "." + attr, new, type="string")
        return len(fixes)
    except Exception:                                        # noqa: BLE001
        import traceback
        print("SkeldarAnim relink: markers not checked")
        print(traceback.format_exc())
        return 0


def heal_quietly(namespace=None):
    """`heal` kept out of the undo queue: a scene's own repair, not a step to undo (an undo would
    kill the markers again). Never raises - without Maya (the unit tests) it does nothing."""
    cmds = _cmds()
    try:
        state = cmds.undoInfo(query=True, stateWithoutFlush=True)
    except AttributeError:                     # maya.cmds not initialised
        return 0
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        return heal(namespace)
    finally:
        cmds.undoInfo(stateWithoutFlush=state)
