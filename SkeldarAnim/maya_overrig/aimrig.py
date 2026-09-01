"""The aim manifest: what one aim rig is made of, and how to take it apart.

An aim is recorded the way limbs and chains are -- a UUID diff of every node in
the scene across the build, minus animCurves. Nothing smaller works: OverRig's
aim leaves a constraint node parented under the source object, and a manifest
assembled from `OverRig_knots` records only the locators and leaves that
constraint live, driven by nothing (traps 3 and 4).

This module knows nothing about weapons. The picker's Bake+Delete has to be
able to resolve an aim, and `maya_overrig` importing `maya_scenesetup` would
invert the layering that already runs the other way.
"""

import maya.cmds as cmds

from maya_overrig import builder, overrig

SET_PREFIX = "RigPicker_aim_"

# The source is recorded in an ATTRIBUTE, never as a member: members get
# deleted when the aim is baked, and the sword must survive that.
SOURCE_ATTR = "rigPickerSource"
HANDLES_ATTR = "rigPickerHandles"


def set_name(key):
    """Name for a new aim manifest. Maya may uniquify it, which is why nothing
    ever looks an aim up by this name again."""
    return SET_PREFIX + key


# ---------------------------------------------------------------------------
# pure
# ---------------------------------------------------------------------------

def normalise(selected, shapes):
    """Selected paths with shapes replaced by their transforms.

    `shapes` maps a shape path to its transform path. Order is kept and
    duplicates collapse, so clicking a mesh and its transform is one hit.
    """
    return list(dict.fromkeys(shapes.get(path, path) for path in selected))


def sets_hit(selected, table):
    """Which aim sets the selection touches.

    `table` is [(set name, handles, members)] -- the scene as data.

    Exact match, deliberately. A descendant walk would resolve an IK hand
    control -- a DAG child of the sword geometry once Connect has hung it
    there -- into the aim, and Bake+Delete would then bake the aim when the
    animator asked for the arm. The safe direction of failure here is
    "nothing happens", not "the wrong rig comes apart".
    """
    wanted = set(selected)
    return [name for name, handles, members in table
            if wanted.intersection(set(handles) | set(members))]


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

def aim_sets():
    """Every aim manifest in the scene, found by prefix.

    Never by exact name: Maya uniquifies, so two characters holding the same
    sword give `RigPicker_aim_LongSword_02` and `RigPicker_aim_LongSword_021`.
    """
    return sorted(s for s in (cmds.ls(type="objectSet") or [])
                  if s.startswith(SET_PREFIX))


def _uuid_paths(text):
    """Long paths for a space-separated UUID list, skipping what is gone."""
    out = []
    for uuid in (text or "").split():
        paths = cmds.ls(uuid, long=True) or []
        if paths:
            out.append(paths[0])
    return out


def _read(name, attr):
    if not cmds.attributeQuery(attr, node=name, exists=True):
        return []
    return _uuid_paths(cmds.getAttr("{0}.{1}".format(name, attr)))


def aim_handles(name):
    """The nodes whose selection means this aim. Never deleted by a bake."""
    return _read(name, HANDLES_ATTR)


def aim_source(name):
    """The node whose animation the bake lands on, or None if it is gone."""
    found = _read(name, SOURCE_ATTR)
    return found[0] if found else None


def aim_table():
    """[(set name, handles, members)] for every aim in the scene."""
    return [(name, aim_handles(name), overrig.set_members(name))
            for name in aim_sets()]


def _shape_map(selected):
    """{shape path: transform path} for the shapes among `selected`."""
    out = {}
    for path in selected:
        if not cmds.objExists(path):
            continue
        if cmds.objectType(path, isAType="shape"):
            parents = cmds.listRelatives(path, parent=True,
                                         fullPath=True) or []
            if parents:
                out[path] = parents[0]
    return out


def aim_targets():
    """The aim sets the current selection touches."""
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        return []
    return sets_hit(normalise(selected, _shape_map(selected)), aim_table())


def aim_for(handle):
    """The aim set `handle` stands for, or None."""
    if not handle:
        return None
    paths = cmds.ls(handle, long=True) or []
    hit = sets_hit([paths[0] if paths else handle], aim_table())
    return hit[0] if hit else None


def record(key, source, handles, before):
    """Record everything created since `before` as one aim manifest.

    `before` is a UUID snapshot, not a path snapshot: OverRig re-parents
    existing nodes, and a re-parented node's new path reads as a fresh one
    (trap 8). Returns the set's name, which Maya may have uniquified.
    """
    fresh = [n for n in builder._fresh_paths(before, builder._scene_nodes())
             if builder._recordable(n)]
    name = cmds.sets(name=set_name(key), empty=True)
    if fresh:
        cmds.sets(fresh, addElement=name)

    cmds.addAttr(name, longName=SOURCE_ATTR, dataType="string")
    cmds.setAttr("{0}.{1}".format(name, SOURCE_ATTR),
                 cmds.ls(source, uuid=True)[0], type="string")
    cmds.addAttr(name, longName=HANDLES_ATTR, dataType="string")
    cmds.setAttr("{0}.{1}".format(name, HANDLES_ATTR),
                 " ".join(cmds.ls(h, uuid=True)[0] for h in handles),
                 type="string")
    return name


def bake_aims(names):
    """Bake each aim onto its source and remove the rig. Returns a message."""
    message = overrig.mel_gate()
    if message:
        return message

    baked = 0
    cmds.undoInfo(openChunk=True, chunkName="Rig Picker aim bake")
    try:
        for name in names:
            if not cmds.objExists(name):
                continue
            source = aim_source(name)
            members = [m for m in overrig.set_members(name)
                       if cmds.objExists(m)]

            # Baked while the constraint still drives, exactly as the FK
            # teardown does. A source someone deleted by hand leaves orphaned
            # locators behind, and those still get cleaned up.
            if source:
                overrig.fast_bake([source])
                overrig.delete_constraint_attributes([source])
            if members:
                cmds.delete(members)
            # Maya deletes an objectSet together with its last member (trap
            # 18), so by now the set may be gone and deleting it would raise
            # on every successful run.
            if cmds.objExists(name):
                cmds.delete(name)
            baked += 1
    finally:
        cmds.undoInfo(closeChunk=True)

    if not baked:
        return "No aim to bake"
    return "{0} aim(s) baked onto the weapon and removed".format(baked)
