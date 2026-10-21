"""The Tools card's knots in the scene (2026-10-12).

OverRig's Knot, Knot Offset, Knot Orient and Double knot (local, world), rebuilt in `cmds` - no
MEL of OverRig's runs (the time slider's highlight is read through `overrig.slider_selection`).
A knot is a locator carrying an object's world track, baked on every frame of its span; the object
follows it through one constraint, its own animation kept under the constraint by Maya's pairBlend,
so `attach` (0..1 on the knot) blends between the two, Remove gives the object its curves back
exactly, and Bake writes what the knot shows into them.

Ours are known by our attributes (`knotplan`'s markers) and found by walking locators (trap 70).
Every press is one undo chunk with autoKey off; a refusal changes nothing.
The pure half is `knotplan`. Spec: docs/superpowers/specs/2026-10-12-tools-knots-design.md

The aim tab (2026-10-13) adds the `aim` kind: two presses as Knot Offset (a target and an up
riding the object while placed, then Finish), a group holding the baked target and up, the
object's rotation following an `aimConstraint` through the same pairBlend and attach. Spec:
docs/superpowers/specs/2026-10-13-tools-aim-overlap-design.md

The snapshot (2026-10-13, «Давай реализуем создание снапшотов»): OverRig's object snapshot - a
locator per object repeating its world motion, keyed on every frame of the highlight (else the
whole take), in the object's Knots group. A knot that drives nothing: the object is never touched,
the snapshot rides nothing (it carries `skeldarSnapshotOf`, never `skeldarKnotSource`), Bake and
Remove delete it (Bake skipped it until 2026-10-15). Spec: docs/superpowers/specs/2026-10-13-tools-snapshot-design.md
"""

import contextlib

import maya.cmds as cmds
import maya_timewarp

from maya_tools import knotplan as plan

SLIDER = "slider"            # `highlight=SLIDER`: read the time slider; None: the whole take

_AXIS = {"tx": "x", "ty": "y", "tz": "z", "rx": "x", "ry": "y", "rz": "z"}


# ------------------------------------------------------------------- nodes

def _long(node):
    found = cmds.ls(node, long=True) if node else []
    return found[0] if found else None


def _uuid(node):
    found = cmds.ls(node, uuid=True) if node else []
    return found[0] if found else None


def _by_uuid(uuid):
    found = cmds.ls(uuid, long=True) if uuid else []
    return found[0] if found else None


def _has(node, attr):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery(attr, node=node,
                                                                       exists=True)


def _get(node, attr):
    return cmds.getAttr(node + "." + attr) if _has(node, attr) else None


def _set_string(node, attr, value):
    if not _has(node, attr):
        cmds.addAttr(node, longName=attr, dataType="string")
    cmds.setAttr(node + "." + attr, value, type="string")


def _parent(path):
    found = cmds.listRelatives(path, parent=True, fullPath=True) if path else None
    return found[0] if found else None


def _transforms(selection):
    """The selection as transform long paths, shapes and components resolved, no repeats."""
    out = []
    for item in selection or []:
        found = cmds.ls(item, long=True, objectsOnly=True) or []
        if not found:
            continue
        path = found[0]
        if not cmds.objectType(path, isAType="transform"):
            path = _parent(path)
            if not path or not cmds.objectType(path, isAType="transform"):
                continue
        if path not in out:
            out.append(path)
    return out


def _selection(selection):
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    return _transforms(selection)


def _groups():
    """Our knots groups: at world level or one level down, in a character group."""
    import maya_rigs
    return maya_rigs.marked_near_top(plan.GROUP_MARKER, depth=2)


def _children(node):
    return cmds.listRelatives(node, children=True, type="transform", fullPath=True) or []


def knots():
    """Every knot of ours: their top nodes, long paths. Read from our groups and the across
    registry - the card asks on every selection change, and a walk over every locator in the
    scene grew with the rigs."""
    out = [child for group in _groups() for child in _children(group)
           if _has(child, plan.KIND_MARKER)]
    registry = _registry()
    if registry:
        for member in cmds.ls(cmds.sets(registry, query=True) or [], long=True) or []:
            if member not in out and _has(member, plan.KIND_MARKER):
                out.append(member)
    return out


def _registry():
    """The objectSet every across knot is a member of (an across knot lives inside its parent,
    not in a Knots group), or None. Maya deletes the set with its last member (trap 18)."""
    for found in cmds.ls(exactType="objectSet") or []:
        if _has(found, plan.REGISTRY_MARKER):
            return found
    return None


def _register(top):
    registry = _registry()
    if registry:
        cmds.sets(top, addElement=registry)
        return
    registry = cmds.sets(top, name=plan.REGISTRY_NAME)
    cmds.addAttr(registry, longName=plan.REGISTRY_MARKER, attributeType="bool",
                 defaultValue=True)


def _space_kind(space):
    """What waits in a waiting space: "aim", else Knot Offset's pivot ("offset")."""
    return _get(space, plan.PENDING_KIND_MARKER) or "offset"


def pivots(kind="offset"):
    """Every waiting pivot of `kind`: Knot Offset's ("offset"), or an aim's target ("aim")."""
    return [child for group in _groups() for space in _children(group)
            if _has(space, plan.PENDING_SPACE_MARKER) and _space_kind(space) == kind
            for child in _children(space) if _has(child, plan.PENDING_MARKER)]


def waiting():
    return bool(pivots())


def aims_waiting():
    """Every waiting aim's target (2026-10-13)."""
    return pivots("aim")


def top_of(node):
    """The knot `node` is, or lies inside (a double knot's inner), or None."""
    path = _long(node)
    while path:
        if _has(path, plan.KIND_MARKER):
            return path
        path = _parent(path)
    return None


def pending_of(node):
    """The waiting pivot `node` is, or the space it rides in, or another node in that space (a
    waiting aim's up), or None."""
    path = _long(node)
    if _has(path, plan.PENDING_MARKER):
        return path
    if _has(path, plan.PENDING_SPACE_MARKER):
        for child in cmds.listRelatives(path, children=True, type="transform",
                                        fullPath=True) or []:
            if _has(child, plan.PENDING_MARKER):
                return child
        return None
    parent = _parent(path)
    if parent and _has(parent, plan.PENDING_SPACE_MARKER):
        return pending_of(parent)
    return None


def _pending_kind(pivot):
    return _space_kind(_parent(pivot))


def source_of(top):
    """The object a knot drives."""
    return _by_uuid(_get(top, plan.SOURCE_MARKER))


def constraints_of(obj):
    """Our constraints on `obj` (a knot drives it through each)."""
    return [con for con in cmds.listRelatives(obj, children=True, type="constraint",
                                              fullPath=True) or []
            if _has(con, plan.OF_MARKER)]


def _knots_driving(obj):
    out = []
    for con in constraints_of(obj):
        top = _by_uuid(_get(con, plan.OF_MARKER))
        if top and top not in out:
            out.append(top)
    return out


def is_snapshot(top):
    """True for a snapshot (2026-10-13): a knot of ours that drives nothing."""
    return _get(top, plan.KIND_MARKER) == "snapshot"


def snapshots():
    """Every snapshot in the scene: their long paths."""
    return [top for top in knots() if is_snapshot(top)]


def snapshot_of(top):
    """The object a snapshot was taken of (it may be gone), or None."""
    return _by_uuid(_get(top, plan.SNAPSHOT_OF_MARKER))


def _waiting_for(obj, kind="offset"):
    uuid = _uuid(obj)
    return [p for p in pivots(kind) if _get(p, plan.PENDING_MARKER) == uuid]


# --------------------------------------------------------------- the press

@contextlib.contextmanager
def _press(name):
    """One undo chunk, autoKey off (through the API: no undo step of its own, trap 212), the
    current frame left where it was."""
    import maya.api.OpenMayaAnim as oma
    auto = oma.MAnimControl.autoKeyMode()
    now = cmds.currentTime(query=True)
    oma.MAnimControl.setAutoKeyMode(False)
    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        yield
    finally:
        try:
            if cmds.currentTime(query=True) != now:
                cmds.currentTime(now)
        finally:
            cmds.undoInfo(closeChunk=True)
            oma.MAnimControl.setAutoKeyMode(auto)


def _highlight(highlight):
    if highlight != SLIDER:
        return highlight
    try:
        from maya_overrig import overrig
        return overrig.slider_selection()
    except Exception:                                           # batch: no time slider
        return None


def _chain(node):
    out, path = [], node
    while path:
        out.append(path)
        path = _parent(path)
    return out


def _span(obj, highlight, extra=(), rule=plan.span_for):
    """The knot's span: the highlight, else the playback and animation ranges with the keys of
    the object and of everything above it (a parent's motion moves the object too) - and of
    `extra` nodes and their ancestors (an across knot's target). `rule` reads them
    (`knotplan.span_for`; a snapshot's `snapshot_span`)."""
    nodes = _chain(obj)
    for node in extra:
        nodes += [n for n in _chain(node) if n not in nodes]
    keys = cmds.keyframe(nodes, query=True, timeChange=True) or []
    take = plan.take_range((cmds.playbackOptions(query=True, min=True),
                            cmds.playbackOptions(query=True, max=True)),
                           (cmds.playbackOptions(query=True, animationStartTime=True),
                            cmds.playbackOptions(query=True, animationEndTime=True)))
    return rule(take, keys, highlight)


def _channels(obj, channels, layers=False):
    """(locked, drivers) for `knotplan.channel_plan`: drivers None for no input, '' for a time
    curve - and, with `layers`, for animation layers whose inputs are all time curves or values
    (`layered.stack_word`) - else what drives the channel in words."""
    locked, drivers = {}, {}
    for ch in channels:
        plug = obj + "." + ch
        locked[ch] = bool(cmds.getAttr(plug, lock=True))
        found = cmds.listConnections(plug, source=True, destination=False,
                                     skipConversionNodes=True) or []
        if not found:
            drivers[ch] = None
            continue
        if layers and cmds.nodeType(found[0]).startswith("animBlendNode"):
            from maya_tools import layered
            drivers[ch] = layered.stack_word(plug)
            continue
        drivers[ch] = plan.driver_word(cmds.nodeType(found[0]),
                                       cmds.objectType(found[0], isAType="constraint"))
    return locked, drivers


def _plan_object(obj, kind, finishing=False):
    """((free, skipped, drivers), '') or (None, refusal) for knotting `obj` as `kind` (an aim
    takes the rotate channels, as Knot Orient; `finishing`: its own waiting aim is no refusal)."""
    name = obj.split("|")[-1]
    if constraints_of(obj):
        return None, plan.riding_refusal(name)
    if pending_of(obj):
        return None, "%s is a waiting pivot - press Finish, or Remove it" % name
    if kind == "offset" and _waiting_for(obj):
        return None, "%s already has a pivot waiting - press Finish, or Remove it" % name
    if kind == "aim" and not finishing and _waiting_for(obj, "aim"):
        return None, "%s already has an aim waiting - press Finish, or Remove it" % name
    refusal = plan.uneven_parent(name, cmds.getAttr(obj + ".parentMatrix[0]"))
    if refusal:
        return None, refusal
    channels = plan.ROTATE if kind in ("orient", "aim") else plan.CHANNELS
    locked, drivers = _channels(obj, channels, layers=True)
    free, skipped, refusal = plan.channel_plan(name, locked, drivers, channels)
    if refusal:
        return None, refusal
    return (free, skipped, drivers), ""


# ----------------------------------------------------------------- building

def _group_for(obj):
    """The group the object's knots live in: `Knots` inside its character group, else the
    world-level `SkeldarKnots`; made on first use, its transform locked at identity."""
    from maya_scenesetup import chargroup
    character = chargroup.group_of(obj)
    for group in _groups():
        if _parent(group) == character:
            return group
    if character:
        group = cmds.createNode("transform", name=plan.GROUP_IN_CHARACTER, parent=character,
                                skipSelect=True)
    else:
        group = cmds.createNode("transform", name=plan.GROUP_AT_WORLD, skipSelect=True)
    uuid = _uuid(group)
    group = _by_uuid(uuid)
    cmds.addAttr(group, longName=plan.GROUP_MARKER, attributeType="bool", defaultValue=True)
    for attr in ("translate", "rotate", "scale"):
        cmds.setAttr(group + "." + attr, lock=True)
    return group


def _prune():
    for group in _groups():
        if cmds.objExists(group) and not cmds.listRelatives(group, children=True):
            cmds.delete(group)


def _size(obj):
    shapes = cmds.listRelatives(obj, shapes=True, fullPath=True, noIntermediate=True) or []
    diagonal = 0.0
    if shapes:
        box = cmds.exactWorldBoundingBox(shapes)
        diagonal = ((box[3] - box[0]) ** 2 + (box[4] - box[1]) ** 2
                    + (box[5] - box[2]) ** 2) ** 0.5
    radius = cmds.getAttr(obj + ".radius") if cmds.objectType(obj, isAType="joint") else None
    return plan.knot_size(diagonal, radius)


def _locator(name, parent, size, colour, rotate_order):
    loc = cmds.spaceLocator(name=name)[0]
    uuid = _uuid(loc)
    cmds.parent(_by_uuid(uuid), parent, relative=True)
    loc = _by_uuid(uuid)
    shape = cmds.listRelatives(loc, shapes=True, fullPath=True)[0]
    cmds.setAttr(shape + ".localScale", size, size, size, type="double3")
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *colour)
    cmds.setAttr(loc + ".rotateOrder", rotate_order)
    return loc


def _constrain(command, driver, node, **kwargs):
    """`command(driver, node, **kwargs)`; the new constraint's long path (found under `node`:
    a returned short name can be ambiguous)."""
    before = set(cmds.listRelatives(node, children=True, type="constraint", fullPath=True) or [])
    command(driver, node, **kwargs)
    after = cmds.listRelatives(node, children=True, type="constraint", fullPath=True) or []
    return [c for c in after if c not in before][0]


def _filter_euler(node, channels):
    found = []
    for ch in channels:
        if ch in plan.ROTATE:
            found += cmds.listConnections(node + "." + ch, source=True, destination=False,
                                          type="animCurve") or []
    if found:
        cmds.filterCurve(found, filter="euler")


def _bake_node(node, channels, span):
    """`node`'s channels baked on every frame of the span, rotates euler-filtered (trap 108), a
    still channel a plain value."""
    maya_timewarp.call(cmds.bakeResults, node, attribute=list(channels), time=(span[0], span[1]),
                     simulation=True, sampleBy=1, disableImplicitControl=True)
    _filter_euler(node, channels)
    for ch in channels:
        plug = node + "." + ch
        values = cmds.keyframe(plug, query=True, valueChange=True) or []
        if values and plan.is_constant(values):
            cmds.cutKey(plug, clear=True)
            cmds.setAttr(plug, values[0])


def _key_free(obj, free, drivers):
    """Key the free channels nothing drives at their current values, so Maya's pairBlend keeps
    the object's own animation under the constraint. {channel: value}."""
    keyed = {}
    now = cmds.currentTime(query=True)
    for ch in free:
        if drivers.get(ch) is not None:
            continue
        value = cmds.getAttr(obj + "." + ch)
        cmds.setKeyframe(obj, attribute=ch, time=now, value=value)
        keyed[ch] = value
    return keyed


def _mark(top, kind, obj, span, keyed):
    _set_string(top, plan.KIND_MARKER, kind)
    _set_string(top, plan.SOURCE_MARKER, _uuid(obj))
    _set_string(top, plan.SPAN_MARKER, plan.encode_span(span))
    _set_string(top, plan.KEYED_MARKER, plan.encode_keyed(keyed))
    cmds.addAttr(top, longName=plan.ATTACH, attributeType="double", minValue=0.0,
                 maxValue=1.0, defaultValue=1.0, keyable=True)
    for time, value in plan.attach_keys(span):
        cmds.setKeyframe(top, attribute=plan.ATTACH, time=time, value=value,
                         inTangentType="flat", outTangentType="flat")


def _follow(obj, driver, top, constraint, skipped, aim=None):
    """The object follows `driver` (offset kept, its locked channels skipped), the constraint
    marked with the knot; `attach` drives the constraint's weight and Maya's pairBlend (an aim's:
    `blendAimCnstraint1`, measured). `aim` (aim vector, up vector, up node) for an aim knot."""
    if constraint == "aim":
        skip = [_AXIS[ch] for ch in skipped if ch in plan.ROTATE] or "none"
        con = _constrain(cmds.aimConstraint, driver, obj, maintainOffset=True,
                         aimVector=aim[0], upVector=aim[1], worldUpType="object",
                         worldUpObject=aim[2], skip=skip)
        alias = cmds.aimConstraint(con, query=True, weightAliasList=True)[0]
    elif constraint == "orient":
        skip = [_AXIS[ch] for ch in skipped if ch in plan.ROTATE] or "none"
        con = _constrain(cmds.orientConstraint, driver, obj, maintainOffset=True, skip=skip)
        alias = cmds.orientConstraint(con, query=True, weightAliasList=True)[0]
    else:
        st = [_AXIS[ch] for ch in skipped if ch in plan.TRANSLATE] or "none"
        sr = [_AXIS[ch] for ch in skipped if ch in plan.ROTATE] or "none"
        con = _constrain(cmds.parentConstraint, driver, obj, maintainOffset=True,
                         skipTranslate=st, skipRotate=sr)
        alias = cmds.parentConstraint(con, query=True, weightAliasList=True)[0]
    _set_string(con, plan.OF_MARKER, _uuid(top))
    cmds.connectAttr(top + "." + plan.ATTACH, con + "." + alias, force=True)
    for blend in set(cmds.listConnections(obj, source=True, destination=False,
                                          type="pairBlend") or []):
        weight = cmds.listConnections(blend + ".weight", source=True, destination=False,
                                      plugs=True) or []
        if weight:
            cmds.connectAttr(top + "." + plan.ATTACH, weight[0], force=True)
        cmds.setAttr(blend + ".rotInterpolation", 1)                # quaternion
    return con


def _make(kind, obj, group, size, order):
    """Create kind's nodes for `obj` in `group` (a Knots group; for an across knot its target):
    (top, driver, [(node, channels to bake)], temporaries, the node to select)."""
    k = plan.kind(kind)
    name = plan.leaf(obj)
    if kind in ("knot", "orient", "across"):
        top = _locator(name + k.suffix, group, size, k.colour, order)
        if kind in ("knot", "across"):
            temps = [_constrain(cmds.parentConstraint, obj, top, maintainOffset=False)]
            return top, top, [(top, plan.CHANNELS)], temps, top
        _constrain(cmds.pointConstraint, obj, top, maintainOffset=False)   # kept: it rides
        temps = [_constrain(cmds.orientConstraint, obj, top, maintainOffset=False)]
        return top, top, [(top, plan.ROTATE)], temps, top
    outer = _locator(name + k.suffix, group, size * plan.OUTER_SCALE, k.colour, order)
    inner = _locator(name + k.inner_suffix, outer, size, k.inner_colour, order)
    _set_string(inner, plan.INNER_MARKER, _uuid(outer))
    if kind == "double_local":
        temps = [_constrain(cmds.parentConstraint, obj, outer, maintainOffset=False)]
        return outer, inner, [(outer, plan.CHANNELS)], temps, inner
    temps = [_constrain(cmds.pointConstraint, obj, outer, maintainOffset=False),
             _constrain(cmds.orientConstraint, obj, inner, maintainOffset=False)]
    return outer, inner, [(outer, plan.TRANSLATE), (inner, plan.ROTATE)], temps, outer


def _order(obj, choice):
    return plan.rotate_order_index(choice, cmds.getAttr(obj + ".rotateOrder"))


def _build(kind, obj, info, highlight, choice, home=None):
    free, skipped, drivers = info
    span = _span(obj, highlight, [home] if home else ())
    top, driver, bakes, temps, selected = _make(kind, obj, home or _group_for(obj), _size(obj),
                                                _order(obj, choice))
    for node, channels in bakes:
        _bake_node(node, channels, span)
    cmds.delete([t for t in temps if cmds.objExists(t)])
    if kind == "orient":
        for ch in plan.TRANSLATE:
            cmds.setAttr(top + "." + ch, lock=True)
    keyed = _key_free(obj, free, drivers)
    _mark(top, kind, obj, span, keyed)
    if kind == "across":
        _register(top)
    _follow(obj, driver, top, plan.kind(kind).constraint, skipped)
    return top, selected, span


def create(kind, selection=None, order=plan.ORDER_DEFAULT, highlight=SLIDER):
    """Knot, Knot Orient, Double knot Local or World on every selected object. The line."""
    objs = _selection(selection)
    if not objs:
        return plan.NOTHING
    infos, kept, passed = [], [], []
    for obj in objs:
        info, refusal = _plan_object(obj, kind)
        if refusal and len(objs) > 1 and plan.all_locked(refusal):
            passed.append(plan.leaf(obj))
            continue
        if refusal:
            return refusal
        kept.append(obj)
        infos.append(info)
    if not kept:
        return _plan_object(objs[0], kind)[1]
    objs = kept
    highlight = _highlight(highlight)
    made = []
    with _press("skeldarKnot"):
        for obj, info in zip(objs, infos):
            made.append((obj,) + _build(kind, obj, info, highlight, order))
        cmds.select([m[2] for m in made], replace=True)
    pairs = [(plan.leaf(m[0]), m[1].split("|")[-1]) for m in made]
    return (plan.created_message(plan.kind(kind).label, pairs, made[0][3])
            + plan.passed_over_words(passed))


def _build_snapshot(obj, highlight, choice):
    """One snapshot of `obj`: a locator in its Knots group carrying its world track on every
    frame of the span, the temporary constraint gone. (snapshot, span)."""
    k = plan.kind("snapshot")
    span = _span(obj, highlight, rule=plan.snapshot_span)
    top = _locator(plan.leaf(obj) + k.suffix, _group_for(obj), _size(obj), k.colour,
                   _order(obj, choice))
    temp = _constrain(cmds.parentConstraint, obj, top, maintainOffset=False)
    _bake_node(top, plan.CHANNELS, span)
    if cmds.objExists(temp):
        cmds.delete(temp)
    _set_string(top, plan.KIND_MARKER, "snapshot")
    _set_string(top, plan.SNAPSHOT_OF_MARKER, _uuid(obj))
    _set_string(top, plan.SPAN_MARKER, plan.encode_span(span))
    return top, span


def snapshot(selection=None, order=plan.ORDER_DEFAULT, highlight=SLIDER):
    """Snapshot (2026-10-13): a locator per selected object repeating its world motion, keyed on
    every frame of the highlight (else the whole take). The object is not touched, so a rig
    control, a bone, a constrained object, a knot all may be snapshotted; a component is refused.
    The line."""
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    if any("." in str(item) for item in selection):
        return plan.SNAPSHOT_COMPONENTS
    objs = _transforms(selection)
    if not objs:
        return plan.SNAPSHOT_NOTHING
    highlight = _highlight(highlight)
    made = []
    with _press("skeldarSnapshot"):
        for obj in objs:
            made.append((obj,) + _build_snapshot(obj, highlight, order))
        cmds.select([m[1] for m in made], replace=True)
    return plan.snapshot_message([(plan.leaf(m[0]), m[1].split("|")[-1]) for m in made],
                                 made[0][2])


def create_across(pairs, order=plan.ORDER_DEFAULT, highlight=SLIDER, rotate=True,
                  translate=True):
    """Across: each object rides a knot inside its target (`pairs` [(object, target)]): the
    knot baked from the object's world track, its keys in the target's space. Rotate / Translate
    off leave that half of the object to its own animation (Multiple across). The line."""
    pairs = [(_long(o), _long(t)) for o, t in pairs]
    if not pairs or any(not o or not t for o, t in pairs):
        return plan.ACROSS_TWO
    if not rotate and not translate:
        return plan.multiple_refusal(len(pairs), len(pairs), rotate, translate)
    off = (() if rotate else plan.ROTATE) + (() if translate else plan.TRANSLATE)
    objects = [o for o, _t in pairs]
    infos = []
    for obj, target in pairs:
        name = plan.leaf(obj)
        if objects.count(obj) > 1:
            return "%s is listed twice - one target per object" % name
        if obj == target:
            return "%s is its own target - select the objects, then the one they ride LAST" % name
        if target.startswith(obj + "|"):
            return "the target %s lies inside %s - a cycle" % (plan.leaf(target), name)
        info, refusal = _plan_object(obj, "across")
        if refusal:
            return refusal
        refusal = plan.uneven_target(name, plan.leaf(target),
                                     cmds.getAttr(target + ".worldMatrix[0]"))
        if refusal:
            return refusal
        free, skipped, drivers = info
        free = [ch for ch in free if ch not in off]
        skipped = list(skipped) + [ch for ch in off if ch not in skipped]
        if not free:
            return "%s has no free channel left to follow" % name
        infos.append((free, skipped, drivers))
    highlight = _highlight(highlight)
    made = []
    with _press("skeldarAcross"):
        for (obj, target), info in zip(pairs, infos):
            made.append((obj,) + _build("across", obj, info, highlight, order, home=target))
        cmds.select([m[2] for m in made], replace=True)
    names = [(plan.leaf(m[0]), m[1].split("|")[-1]) for m in made]
    return plan.created_message("Across", names, made[0][3])


def across(selection=None, order=plan.ORDER_DEFAULT, highlight=SLIDER):
    """The Across button: every selected object rides a knot inside the LAST selected one."""
    objs = _selection(selection)
    if len(objs) < 2:
        return plan.ACROSS_TWO
    return create_across([(obj, objs[-1]) for obj in objs[:-1]], order, highlight)


def set_attach(value, selection=None, highlight=SLIDER):
    """Attach 0 / 1: the selected knots' `attach` keyed `value` (flat) at the highlight's ends,
    else the selected graph keys' first and last time, else the current frame."""
    tops, _waiting = _picked(selection)
    if not tops:
        return plan.ATTACH_NOTHING
    times = plan.attach_times(_highlight(highlight),
                              cmds.keyframe(query=True, selected=True, timeChange=True) or [],
                              cmds.currentTime(query=True))
    done = 0
    with _press("skeldarKnotAttach"):
        for top in tops:
            plug = top + "." + plan.ATTACH
            if not cmds.objExists(plug):
                continue
            if cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, lock=False)
            for time in times:
                cmds.setKeyframe(top, attribute=plan.ATTACH, time=time, value=value,
                                 inTangentType="flat", outTangentType="flat")
            done += 1
    return plan.attach_message(value, done, times)


# ------------------------------------------------------------- Knot Offset

def begin_offset(selection=None, order=plan.ORDER_DEFAULT, highlight=SLIDER):
    """The first press: a pivot riding the object, waiting to be placed."""
    objs = _selection(selection)
    if not objs:
        return plan.NOTHING
    if len(objs) > 1:
        return plan.OFFSET_ONE
    obj = objs[0]
    _info, refusal = _plan_object(obj, "offset")
    if refusal:
        return refusal
    span = _span(obj, _highlight(highlight))
    name = plan.leaf(obj)
    with _press("skeldarKnotOffsetBegin"):
        group = _group_for(obj)
        space = cmds.createNode("transform", name=name + plan.PIVOT_SPACE_SUFFIX,
                                parent=group, skipSelect=True)
        space = _by_uuid(_uuid(space))
        _set_string(space, plan.PENDING_SPACE_MARKER, _uuid(obj))
        _constrain(cmds.parentConstraint, obj, space, maintainOffset=False)
        pivot = _locator(name + plan.PIVOT_SUFFIX, space, _size(obj), plan.PIVOT_COLOUR, 0)
        _set_string(pivot, plan.PENDING_MARKER, _uuid(obj))
        _set_string(pivot, plan.SPAN_MARKER, plan.encode_span(span))
        _set_string(pivot, plan.ORDER_MARKER, order)
        cmds.select(pivot, replace=True)
    try:
        cmds.setToolTo("moveSuperContext")
    except Exception:                                           # batch: no tools
        pass
    return plan.begin_message(name)


def finish_offset(selection=None):
    """The second press: the knot on the pivot's place and axes."""
    named = []
    for node in _selection(selection):
        found = pending_of(node) or next(iter(_waiting_for(node)), None)
        if found and found not in named:
            named.append(found)
    pivot, refusal = plan.choose_pivot(named, pivots())
    if refusal:
        return refusal
    obj = _by_uuid(_get(pivot, plan.PENDING_MARKER))
    if not obj:
        return "the object of %s is gone - Remove the pivot" % pivot.split("|")[-1]
    info, refusal = _plan_object(obj, "knot")
    if refusal:
        return refusal
    span = plan.decode_span(_get(pivot, plan.SPAN_MARKER)) or _span(obj, None)
    choice = _get(pivot, plan.ORDER_MARKER) or plan.ORDER_DEFAULT
    free, skipped, drivers = info
    k = plan.kind("offset")
    with _press("skeldarKnotOffset"):
        top = _locator(plan.leaf(obj) + k.suffix, _group_for(obj), _size(obj), k.colour,
                       _order(obj, choice))
        temp = _constrain(cmds.parentConstraint, pivot, top, maintainOffset=False)
        _bake_node(top, plan.CHANNELS, span)
        cmds.delete(temp)
        cmds.delete(_parent(pivot))
        keyed = _key_free(obj, free, drivers)
        _mark(top, "offset", obj, span, keyed)
        _follow(obj, top, top, k.constraint, skipped)
        cmds.select(top, replace=True)
    return plan.finish_message(plan.leaf(obj), top.split("|")[-1], span)


# --------------------------------------------------------------------- Aim

def _lock_rotation(node):
    """A point locator: its rotation locked out of the channel box (an aim's target and up are
    positions only - OverRig cut, zeroed and hid their rotation)."""
    for ch in plan.ROTATE:
        cmds.setAttr(node + "." + ch, lock=True, keyable=False, channelBox=False)


def begin_aim(selection=None, order=plan.ORDER_DEFAULT, highlight=SLIDER):
    """The first Aim press, every selected object: a space riding it (at its rotate pivot, in
    its axes) holding a target along its X and an up along its Y, four knot sizes out - placed
    while they ride it, then Finish (2026-10-13, «двухшаговая кнопка» as Knot Offset)."""
    objs = _selection(selection)
    if not objs:
        return plan.AIM_NOTHING
    kept, passed = [], []
    for obj in objs:
        _info, refusal = _plan_object(obj, "aim")
        if refusal and len(objs) > 1 and plan.all_locked(refusal):
            passed.append(plan.leaf(obj))
            continue
        if refusal:
            return refusal
        kept.append(obj)
    if not kept:
        return _plan_object(objs[0], "aim")[1]
    objs = kept
    highlight = _highlight(highlight)
    k = plan.kind("aim")
    targets = []
    with _press("skeldarAimBegin"):
        for obj in objs:
            name = plan.leaf(obj)
            size = _size(obj)
            space = cmds.createNode("transform", name=name + plan.AIM_SPACE_SUFFIX,
                                    parent=_group_for(obj), skipSelect=True)
            space = _by_uuid(_uuid(space))
            _set_string(space, plan.PENDING_SPACE_MARKER, _uuid(obj))
            _set_string(space, plan.PENDING_KIND_MARKER, "aim")
            _constrain(cmds.parentConstraint, obj, space, maintainOffset=False)
            target = _locator(name + plan.AIM_TARGET_SUFFIX, space, size, k.colour, 0)
            up = _locator(name + k.inner_suffix, space, size, k.inner_colour, 0)
            reach = plan.aim_reach(size)
            cmds.setAttr(target + ".translateX", reach)
            cmds.setAttr(up + ".translateY", reach)
            for node in (target, up):
                _lock_rotation(node)
            _set_string(target, plan.PENDING_MARKER, _uuid(obj))
            _set_string(target, plan.SPAN_MARKER, plan.encode_span(_span(obj, highlight)))
            _set_string(target, plan.ORDER_MARKER, order)
            targets.append(target)
        cmds.select(targets, replace=True)
    try:
        cmds.setToolTo("moveSuperContext")
    except Exception:                                           # batch: no tools
        pass
    return plan.aim_begin_message([plan.leaf(o) for o in objs]) + plan.passed_over_words(passed)


def _pending_up(target):
    """A waiting aim's up: the other locator in its space."""
    for child in _children(_parent(target)):
        if child != target and not cmds.objectType(child, isAType="constraint"):
            return child
    return None


def _in_axes(obj, node):
    """Where `node` stands off the object's rotate pivot, in the object's own axes."""
    pivot = cmds.xform(obj, query=True, worldSpace=True, rotatePivot=True)
    where = cmds.xform(node, query=True, worldSpace=True, translation=True)
    offset = [where[i] - pivot[i] for i in range(3)]
    return tuple(sum(offset[j] * row[j] for j in range(3))
                 for row in plan.axes_of(cmds.getAttr(obj + ".worldMatrix[0]")))


def _build_aim(target_pending, obj, info, up_pending, vectors):
    """One aim knot: a group (the top, at identity) holding the target and the up, each baked
    from the waiting one's world position over the span; the waiting space gone; the object's
    rotation aiming at the target, leaning to the up."""
    free, skipped, drivers = info
    span = plan.decode_span(_get(target_pending, plan.SPAN_MARKER)) or _span(obj, None)
    k = plan.kind("aim")
    name = plan.leaf(obj)
    size = _size(obj)
    top = cmds.createNode("transform", name=name + k.suffix, parent=_group_for(obj),
                          skipSelect=True)
    top = _by_uuid(_uuid(top))
    target = _locator(name + plan.AIM_TARGET_SUFFIX, top, size, k.colour, 0)
    up = _locator(name + k.inner_suffix, top, size, k.inner_colour, 0)
    temps = [_constrain(cmds.pointConstraint, target_pending, target, maintainOffset=False),
             _constrain(cmds.pointConstraint, up_pending, up, maintainOffset=False)]
    for node in (target, up):
        _bake_node(node, plan.TRANSLATE, span)
    cmds.delete(temps)
    cmds.delete(_parent(target_pending))
    for node in (target, up):
        _set_string(node, plan.INNER_MARKER, _uuid(top))
        _lock_rotation(node)
    for attr in ("translate", "rotate", "scale"):
        cmds.setAttr(top + "." + attr, lock=True)
    keyed = _key_free(obj, free, drivers)
    _mark(top, "aim", obj, span, keyed)
    _follow(obj, target, top, k.constraint, skipped, aim=(vectors[0], vectors[1], up))
    return obj, target, span


def finish_aim(selection=None):
    """The second Aim press: the waiting aims the selection names (a target, an up, the space,
    or the object), else every aim waiting, built. A target standing on its object, or an up on
    the line to the target, is refused before anything changes."""
    named = []
    for node in _selection(selection):
        found = pending_of(node)
        if found and _pending_kind(found) != "aim":
            found = None
        found = found or next(iter(_waiting_for(node, "aim")), None)
        if found and found not in named:
            named.append(found)
    chosen, refusal = plan.choose_aims(named, aims_waiting())
    if refusal:
        return refusal
    jobs = []
    for pending in chosen:
        label = pending.split("|")[-1]
        obj = _by_uuid(_get(pending, plan.PENDING_MARKER))
        if not obj:
            return "the object of %s is gone - Remove it" % label
        info, refusal = _plan_object(obj, "aim", finishing=True)
        if refusal:
            return refusal
        up = _pending_up(pending)
        if not up:
            return "the up of %s is gone - Remove it and press Aim again" % label
        aim, upv, refusal = plan.aim_vectors(plan.leaf(obj), _in_axes(obj, pending),
                                             _in_axes(obj, up))
        if refusal:
            return refusal
        jobs.append((pending, obj, info, up, (aim, upv)))
    made = []
    with _press("skeldarAim"):
        for pending, obj, info, up, vectors in jobs:
            made.append(_build_aim(pending, obj, info, up, vectors))
        cmds.select([m[1] for m in made], replace=True)
    return plan.aim_finish_message([(plan.leaf(m[0]), m[1].split("|")[-1]) for m in made],
                                   made[0][2])


# --------------------------------------------------------- Bake and Remove

def _picked(selection):
    """(knot tops, waiting pivots) the selection names."""
    tops, waiting_pivots = [], []
    for node in _selection(selection):
        top = top_of(node)
        if top:
            if top not in tops:
                tops.append(top)
            continue
        pivot = pending_of(node)
        if pivot:
            if pivot not in waiting_pivots:
                waiting_pivots.append(pivot)
            continue
        for found in _knots_driving(node):
            if found not in tops:
                tops.append(found)
        for found in _waiting_for(node) + _waiting_for(node, "aim"):
            if found not in waiting_pivots:
                waiting_pivots.append(found)
    return tops, waiting_pivots


def _ordered(tops):
    pairs = [(_uuid(t), _get(t, plan.SOURCE_MARKER)) for t in tops]
    return plan.bake_order(pairs)


def _driven(obj):
    """The object's channels a constraint drives (through Maya's pairBlend or directly)."""
    out = []
    for ch in plan.CHANNELS:
        found = cmds.listConnections(obj + "." + ch, source=True, destination=False,
                                     skipConversionNodes=True) or []
        if found and (cmds.nodeType(found[0]) == "pairBlend"
                      or cmds.objectType(found[0], isAType="constraint")):
            out.append(ch)
    return out


def _knot_keys(top):
    nodes = [top] + (cmds.listRelatives(top, allDescendents=True, type="transform",
                                        fullPath=True) or [])
    return cmds.keyframe(nodes, query=True, timeChange=True) or []


def _influence(top, obj):
    """(first, last, ranged) frames the knot shows in the object - where `attach` is above
    zero - or None. An unkeyed attach above zero is the whole take (span, the knot's and the
    object's keys)."""
    span = plan.decode_span(_get(top, plan.SPAN_MARKER)) or _span(obj, None)
    whole = plan.widen(span, _knot_keys(top) + (cmds.keyframe(obj, query=True,
                                                              timeChange=True) or []))
    attach = top + "." + plan.ATTACH
    if not cmds.keyframe(attach, query=True, keyframeCount=True):
        return (whole[0], whole[1], False) if cmds.getAttr(attach) > plan.TOLERANCE else None
    samples = [(f, cmds.getAttr(attach, time=f))
               for f in range(int(whole[0]), int(whole[1]) + 1)]
    found = plan.influence(samples)
    return None if found is None else (found[0], found[1], True)


_BLEND_INPUT = {"tx": "inTranslateX1", "ty": "inTranslateY1", "tz": "inTranslateZ1",
                "rx": "inRotateX1", "ry": "inRotateY1", "rz": "inRotateZ1"}
#  Tangent types a key computes from its neighbours: a bake changing a neighbour moves them.
_NEIGHBOURLY = ("spline", "clamped", "plateau", "auto", "autoMix", "autoEase", "autoCustom")


def _own_curve(obj, ch):
    """The object's own time curve on `ch` - under Maya's pairBlend when a knot drives it."""
    found = cmds.listConnections(obj + "." + ch, source=True, destination=False,
                                 skipConversionNodes=True) or []
    if not found:
        return None
    node = found[0]
    if cmds.nodeType(node) == "pairBlend":
        curves = cmds.listConnections(node + "." + _BLEND_INPUT[ch], source=True,
                                      destination=False, type="animCurve") or []
        return curves[0] if curves else None
    return node if cmds.nodeType(node) in plan.TIME_CURVES else None


def _pin(curve, time):
    for flag in ("inTangentType", "outTangentType"):
        kind = (cmds.keyTangent(curve, time=(time, time), query=True, **{flag: True}) or [""])[0]
        if kind in _NEIGHBOURLY:
            cmds.keyTangent(curve, time=(time, time), **{flag: "fixed"})


def _protect(obj, channels, first, last):
    """Before a bake of [first, last]: the object's curves keep what they play outside it. A
    key is inserted on every curve one frame outside each end (Maya's insert keeps the shape
    and pins the neighbours; a curve keyed only inside the range - the key we set at creation -
    keeps its value outside through it), and that key and its outer neighbour have their
    neighbour-made tangents pinned: a bake replacing the keys inside would otherwise re-aim
    them and bend the curve outside the range."""
    for ch in channels:
        curve = _own_curve(obj, ch)
        if not curve:
            continue
        times = cmds.keyframe(curve, query=True, timeChange=True) or []
        for edge in (first - 1.0, last + 1.0):
            if not any(abs(t - edge) < 1e-6 for t in times):
                cmds.setKeyframe(curve, time=edge, insert=True)
            _pin(curve, edge)
            outer = [t for t in times if (t < edge if edge < first else t > edge)]
            if outer:
                _pin(curve, max(outer) if edge < first else min(outer))


def _set_key_values(curve, times, old, new):
    for time, before, after in zip(times, old, new):
        if abs(after - before) > 1e-9:
            cmds.keyframe(curve, edit=True, time=(time, time), absolute=True,
                          valueChange=after)


def _continuous(obj, channels, first, last):
    """The bake's own rotate keys in [first, last] made continuous from the key before them -
    and nothing else of the animator's curves (filterCurve over the whole curve rewrote a key at
    300 to -60 far outside the knot, the review's finding). With all three rotates baked the other
    euler solution is tried too; with one locked, whole turns only."""
    rotates = [ch for ch in plan.ROTATE if ch in channels]
    curves = dict((ch, _own_curve(obj, ch)) for ch in rotates)
    rotates = [ch for ch in rotates if curves[ch]]
    if not rotates:
        return
    times = [t for t in cmds.keyframe(curves[rotates[0]], query=True, timeChange=True) or []
             if first - 1e-6 <= t <= last + 1e-6]
    if not times:
        return
    before = [t for t in cmds.keyframe(curves[rotates[0]], query=True, timeChange=True) or []
              if t < first - 1e-6]
    values = dict((ch, [cmds.keyframe(curves[ch], query=True, eval=True, time=(t, t))[0]
                        for t in times]) for ch in rotates)
    anchor = None
    if before:
        anchor = dict((ch, cmds.keyframe(curves[ch], query=True, eval=True,
                                         time=(before[-1], before[-1]))[0]) for ch in rotates)
    if rotates == list(plan.ROTATE):
        rows = list(zip(values["rx"], values["ry"], values["rz"]))
        made = plan.continuous_eulers(
            tuple(anchor[ch] for ch in plan.ROTATE) if anchor else None, rows,
            cmds.getAttr(obj + ".rotateOrder"))
        for index, ch in enumerate(plan.ROTATE):
            _set_key_values(curves[ch], times, values[ch], [row[index] for row in made])
        return
    for ch in rotates:
        made = plan.continuous_channel(anchor[ch] if anchor else None, values[ch])
        _set_key_values(curves[ch], times, values[ch], made)


def _bake_one(top, obj, mine, layer=None):
    """One knot's motion written into its object's curves, the constraint deleted. A layered
    object (2026-10-15): what it shows over the knot's region read on every frame and keyed on
    `layer` (the active one) as final values - `bakeResults` would bake into the pairBlend's
    input 1, the layers' blend node, and land wrong."""
    region = _influence(top, obj)
    channels = _driven(obj)
    baked = region is not None and bool(channels)
    from maya_tools import layered
    if baked and layered.is_layered(obj, channels):
        first, last = int(round(region[0])), int(round(region[1]))
        shown = layered.read([obj], channels, range(first - 1, last + 2))[obj]
        cmds.delete(mine)
        layered.key_shown(obj, channels, first, last, shown, layer, ranged=region[2])
        for ch, value in plan.decode_keyed(_get(top, plan.KEYED_MARKER)).items():
            _unkey(obj, ch, value)
        return
    if baked:
        if region[2]:
            _protect(obj, channels, region[0], region[1])
        maya_timewarp.call(cmds.bakeResults, obj, attribute=channels, time=(region[0], region[1]),
                         simulation=True, sampleBy=1, preserveOutsideKeys=True,
                         disableImplicitControl=True)
    cmds.delete(mine)
    if baked:
        _continuous(obj, channels, region[0], region[1])
    for ch, value in plan.decode_keyed(_get(top, plan.KEYED_MARKER)).items():
        _unkey(obj, ch, value)


def _with_riders(tops):
    """`tops` and every knot riding one of them, however deep (a knot on a knot: deleting the
    inner knot takes the outer one's constraint along and leaves it driving nothing)."""
    out = list(tops)
    grown = True
    while grown:
        grown = False
        ids = set(_uuid(t) for t in out)
        for found in knots():
            #  riding: on a knot, or an Across knot standing INSIDE one (1P Setup's IK arms in
            #  its chest, 2026-10-21) - the chest gone, they would be left driving from nowhere
            if found not in out and (_get(found, plan.SOURCE_MARKER) in ids
                                     or any(found.startswith(t + "|") for t in out)):
                out.append(found)
                grown = True
    return out


def _release_children(top):
    """The nodes parented under a knot (the animator's, or 1P Setup's camera) out of it, so
    deleting the knot keeps them - and keeps their motion: a child with keys is moved by Tools >
    World's road (its world track baked back in its new space, `reparent._rebake`), else a plain
    parent (2026-10-20: 1P Setup's camera, keyed in the knot's space, stood 190 cm off after a
    Bake). They go where the knot's group stands - the character group, else world level."""
    group = _parent(top)
    home = _parent(group) if group else None
    for node in [top] + [c for c in _children(top) if _has(c, plan.INNER_MARKER)]:
        for child in _children(node):
            if cmds.objectType(child, isAType="constraint") or _has(child, plan.INNER_MARKER):
                continue
            if _aim_group(child):           # a weapon's Aim Mode: its controllers keep moving
                try:
                    _carry_group_out(child, home)
                    continue
                except Exception:           # never stop a Bake / Remove over a passenger
                    pass
            if _camera_control(child):      # the camera's control goes back under Main
                try:
                    from maya_scenesetup import camera
                    camera.go_home(child)
                    continue
                except Exception:           # never stop a Bake / Remove over a passenger
                    pass
            _move_out(child, home)


def _aim_group(node):
    try:
        from maya_scenesetup import weaponaim
    except ImportError:
        return False
    return _has(node, weaponaim.MARKER)


def _carry_group_out(group, home):
    """A weapon's aim group out of a knot (1P Setup's chest, 2026-10-21): the group under `home`
    (None: world level), its controllers' world motion kept."""
    from maya_scenesetup import weaponaim
    from maya_tools import firstperson
    uuid = _uuid(group)
    weapon = weaponaim.weapon_of_group(group)
    from maya_scenesetup import weaponspace
    if weapon and weaponspace.holding_hand(weapon):        # in a hand: back under Main
        home = weaponaim.home_of(weapon, chest=False) or home
    #  out of the hands it repeats the weapon, which leaves the chest for `home` too

    def move():
        node = _by_uuid(uuid)
        if home:
            cmds.parent(node, home)
        else:
            cmds.parent(node, world=True)
    firstperson.carry_into(list(weaponaim.controllers(group).values()), home, move)


def _camera_control(node):
    try:
        from maya_scenesetup import camera
    except ImportError:
        return False
    return camera.is_control(node)


def _move_out(child, home):
    """`child` under `home` (None: world level), its motion kept when it has keys and its
    translate / rotate are free."""
    def operate(uuids):
        for uuid in uuids:
            node = _by_uuid(uuid)
            if not node or _parent(node) == home:
                continue
            if home:
                cmds.parent(node, home)
            else:
                cmds.parent(node, world=True)

    keyed = cmds.keyframe(child, attribute=list(plan.CHANNELS), query=True, keyframeCount=True)
    locked, _drivers = _channels(child, plan.CHANNELS, layers=True)
    if keyed and not any(locked.values()):
        from maya_tools import reparent
        try:
            span = reparent._take([child], [home])
            scales, refusal = reparent._scale_plans([(child, home)], span)
            layer, layer_refusal = reparent._layer_for([child])
            if not refusal and not layer_refusal:
                reparent._rebake([child], span, operate, scales, layer)
                return
        except Exception:                   # never stop a Bake / Remove over a passenger
            pass
    operate([_uuid(child)])


def _delete_knot(top):
    _release_arms(top)
    _release_children(top)
    cmds.delete(top)


def _release_arms(top):
    """1P Setup's IK arms following this knot (the chest) let go with their motion kept - the
    constraint would otherwise die with its target and leave the arms' keys in a space that no
    longer moves (trap 157)."""
    try:
        from maya_tools import firstperson
        if firstperson.arm_constraints(top):
            firstperson.release_arms(top)
    except Exception:                       # never stop a Bake / Remove over a passenger
        import traceback
        traceback.print_exc()


def bake(selection=None):
    """The objects baked where their knots carry them; the knots gone. A snapshot drives nothing:
    nothing to bake, it is deleted too (2026-10-15, «После нажатия бейк если были выделены
    какие-то наши knot то они должны удалиться»). The line."""
    tops, _waiting = _picked(selection)
    if not tops:
        return plan.BAKE_NOTHING
    from maya_tools import layered
    layer = None
    if any(o and layered.is_layered(o) for o in (source_of(t) for t in tops)):
        layer, refusal = layered.target()
        refusal = refusal or layered.check_target(layer, plan.CHANNELS)
        if refusal:
            return refusal
    names, objs, snaps = [], [], 0
    with _press("skeldarKnotBake"):
        for uuid in _ordered(_with_riders(tops)):
            top = _by_uuid(uuid)
            if not top:
                continue
            snaps += int(is_snapshot(top))
            obj = source_of(top)
            mine = [c for c in constraints_of(obj) if _get(c, plan.OF_MARKER) == uuid] \
                if obj else []
            if mine:
                _bake_one(top, obj, mine, layer)
                names.append(plan.leaf(obj))
                objs.append(_uuid(obj))
            elif obj:                                   # its constraint deleted by hand
                for ch, value in plan.decode_keyed(_get(top, plan.KEYED_MARKER)).items():
                    _unkey(obj, ch, value)
            _delete_knot(top)
        _prune()
        live = [p for p in (_by_uuid(u) for u in objs) if p]
        if live:
            cmds.select(live, replace=True)
    return plan.baked_message(names, snaps)


def _unkey(obj, ch, value):
    """A channel we keyed at creation: cut while it still holds only that value, the value
    written back (cutKey leaves whatever was last evaluated, trap 58)."""
    plug = obj + "." + ch
    found = cmds.listConnections(plug, source=True, destination=False, type="animCurve") or []
    target = plug
    if not found:
        #  the channel went onto an animation layer since (a bake keyed it there): our key is the
        #  base's, under the layers' blend nodes
        from maya_tools import layered
        target, curve, _word, _layered = layered.walk(plug, ch)
        found = [curve] if curve else []
        if not found:
            return
    values = cmds.keyframe(found[0], query=True, valueChange=True) or []
    if not plan.still_static(values, value):
        return
    if target == plug:
        cmds.cutKey(plug, clear=True)
    else:
        cmds.delete(found[0])
    if not cmds.getAttr(plug, lock=True):
        cmds.setAttr(target, value)


def remove(selection=None):
    """The knots deleted and their objects' own animation back; waiting pivots dropped; a
    snapshot deleted (with any knot riding it)."""
    tops, waiting_pivots = _picked(selection)
    if not tops and not waiting_pivots:
        return plan.REMOVE_NOTHING
    names, objs, snaps = [], [], 0
    with _press("skeldarKnotRemove"):
        for uuid in _ordered(_with_riders(tops)):
            top = _by_uuid(uuid)
            if not top:
                continue
            snaps += int(is_snapshot(top))
            obj = source_of(top)
            if obj:
                mine = [c for c in constraints_of(obj) if _get(c, plan.OF_MARKER) == uuid]
                if mine:
                    cmds.delete(mine)
                for ch, value in plan.decode_keyed(_get(top, plan.KEYED_MARKER)).items():
                    _unkey(obj, ch, value)
                names.append(plan.leaf(obj))
                objs.append(_uuid(obj))
            _delete_knot(top)
        for pivot in waiting_pivots:
            space = _parent(pivot)
            if space and cmds.objExists(space):
                cmds.delete(space)
        _prune()
        live = [p for p in (_by_uuid(u) for u in objs) if p]
        if live:
            cmds.select(live, replace=True)
    return plan.removed_message(names, len(waiting_pivots), snaps)
