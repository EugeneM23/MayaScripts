"""The Pose Library's OBJECTS beside a character (2026-10-15): which selected nodes are the body and
which are objects, an object's channels (its transform's and its shape's), and where a card's
object is found again on load.

The animator: «объекты которые не относятся к ригу мы не сохраняем ... мы сохранили наш риг и
камеру в сцене при загрузке мы должны выполнить поиск камеры с учетом того что в другой сцене на
ней уже может быть немспейс (такой тип поиска ... только для тех объектов которые находятся в
выделении)».

**Body or object** (`scene.is_body`): the body is a joint, anything under a rig's AdvancedSkeleton
`Group` (its controls, meshes, weapon spaces), a skinned mesh, a group holding the skeleton or the
rig (the character group, the Creep's `Armature`), a weapon or an armour piece (Inventory's). Any
other node is an OBJECT - a camera (the rig's own SceneSetup camera too), a knot, a locator, a
prop - whoever's group it stands in. `scene.split` divides a selection so.

**A record** - `{"name": leaf without namespace, "path", "attrs": {attr: payload}, "shape":
{attr: payload}, "own": bool}` - `attrs` the transform's keyable scalar unlocked attributes,
`shape` its first non-intermediate shape's (a camera's focal length), `own` True for an object of
the card's own character. The payload is a value (a pose) or a curve (an animation card).

**Found again** (`pair_card`, pure; `find_owned`, `find_exact`): the selected objects pair as an
objects card always paired (`apply.pair_objects`: path, name without namespace, order); the card's
objects left over are found - an `own` one in each target character (its namespace + name, else
by name under its character group), any other by its exact path - and never by name elsewhere.

Spec: docs/superpowers/specs/2026-10-15-pose-library-any-objects-design.md
"""

from collections import OrderedDict

import maya.cmds as cmds

import maya_rigs
from maya_poselib import scene


# ------------------------------------------------------------------ channels

def shape_of(path, cmds=cmds):
    """The first non-intermediate shape of a transform, long path, or None."""
    for shape in cmds.listRelatives(path, shapes=True, fullPath=True) or []:
        try:
            if not cmds.getAttr(shape + ".intermediateObject"):
                return shape
        except (RuntimeError, ValueError):
            continue
    return None


def channel_names(node, cmds=cmds):
    """The keyable, scalar, unlocked attributes of `node`; [] when it has none or is gone."""
    try:
        return cmds.listAttr(node, keyable=True, scalar=True, unlocked=True) or []
    except (RuntimeError, ValueError):
        return []


def _number(value):
    if isinstance(value, (bool, int, float)):
        return float(value)
    return None


def values_of(node, cmds=cmds):
    """{attr: float} of `node`'s channels (`channel_names`) - a channel answering no number is
    left out."""
    out = {}
    for attr in channel_names(node, cmds):
        try:
            value = _number(cmds.getAttr(node + "." + attr))
        except (RuntimeError, ValueError):
            continue
        if value is not None:
            out[attr] = value
    return out


def pose_record(path, own=False, cmds=cmds):
    """An object's pose record (the module docstring) - its values now."""
    shape = shape_of(path, cmds)
    return {"name": scene.leaf(path), "path": path, "attrs": values_of(path, cmds),
            "shape": values_of(shape, cmds) if shape else {}, "own": bool(own)}


def plugs_of(record, path, cmds=cmds):
    """(OrderedDict {plug: payload}, missing ["leaf.attr"]) - a record's channels on the scene
    object `path`: the transform's on it, the shape's on its first shape (`shape_of`)."""
    plugs, missing = OrderedDict(), []
    for attr, payload in (record.get("attrs") or {}).items():
        if cmds.attributeQuery(attr, node=path, exists=True):
            plugs[path + "." + attr] = payload
        else:
            missing.append("%s.%s" % (scene.leaf(path), attr))
    shape_attrs = record.get("shape") or {}
    if shape_attrs:
        shape = shape_of(path, cmds)
        for attr, payload in shape_attrs.items():
            if shape and cmds.attributeQuery(attr, node=shape, exists=True):
                plugs[shape + "." + attr] = payload
            else:
                missing.append("%s.%s" % (scene.leaf(path), attr))
    return plugs, missing


# ------------------------------------------------------------------ found again

def find_exact(record):
    """A record's object by its exact stored path, or None."""
    path = record.get("path")
    if not path:
        return None
    found = cmds.ls(path, long=True) or []
    return found[0] if len(found) == 1 else None


def find_owned(record, ref):
    """A character's own object in the character `ref`: the transform named as the record in the
    rig's (or the skeleton's) namespace, else - a skeleton with none - the one transform of that
    name under its character group; None when none or several, or when it is the body."""
    name = record.get("name")
    if not name or ref is None:
        return None
    if ref.namespace:
        found = cmds.ls(ref.namespace + ":" + name, long=True, type="transform") or []
    else:
        group = maya_rigs.group_of(ref.root)
        if not group:
            return None
        found = [p for p in cmds.listRelatives(group, allDescendents=True, type="transform",
                                               fullPath=True) or [] if scene.leaf(p) == name]
    found = [p for p in found if not scene.is_body(p, ref)]
    return found[0] if len(found) == 1 else None


def pair_card(objects, selected, found, pair_objects):
    """([(record, scene path)], how, unfound records) for a CHARACTER card's objects. Pure.

    `selected` the selected objects' paths, paired first by `pair_objects` (the objects card's
    rule: path, name without the namespace, order); `found` {record index: [scene paths]} - the
    ones the scene answered for each record left over (`find_owned` per target, `find_exact`);
    a found path already taken by the selection is not taken twice. `unfound` the records
    neither the selection nor the scene answered."""
    matched, how = (pair_objects(objects, selected, {}) if selected else ([], ""))
    matched = list(matched)
    taken_records = set(id(record) for record, _path in matched)
    paths = set(path for _record, path in matched)
    unfound, extra = [], False
    for index, record in enumerate(objects):
        if id(record) in taken_records:
            continue
        hits = [p for p in (found or {}).get(index) or () if p not in paths]
        if not hits:
            unfound.append(record)
            continue
        for path in hits:
            matched.append((record, path))
            paths.add(path)
            extra = True
    if extra:
        how = "+".join(part for part in (how, "found") if part)
    return matched, how, unfound


def found_for(objects, refs, only=False):
    """{index: [paths]} the scene answers for a character card's objects onto `refs`
    (`pair_card`'s `found`): an `own` record in each target (`find_owned`), any other by its exact
    path. Nothing with Selected only (`only`): it keys the selection alone."""
    if only:
        return {}
    out = {}
    for index, record in enumerate(objects or ()):
        if record.get("own"):
            hits = [find_owned(record, ref) for ref in refs or ()]
        else:
            hits = [find_exact(record)]
        hits = [p for p in hits if p]
        if hits:
            out[index] = list(OrderedDict((p, None) for p in hits))
    return out


def names(records):
    """The records' names for a line."""
    return [record.get("name") or scene.leaf(record.get("path") or "?") for record in records]
