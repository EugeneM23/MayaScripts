"""The Tools card's re-parenting (2026-10-12): OverRig's inside / world / swap, native.

The animator: «Теперь давай реализуем весь функционал из вкладки parent». Each node that moves in
the DAG keeps its world motion on every frame: a temporary locator takes its world track, the DAG
moves, the node is constrained to its locator with no offset (an offset captured after the move
would read the old curves in the new space) and baked, the locator goes. Always the whole take,
never a highlight - a re-parent changes the node's space on every frame.

The world scale crosses the move too (2026-10-13, the animator: «скрипты не работают если на
объектах уже есть ключи» - the S key keys scale, and a keyed scale under a differently scaled new
parent was refused): the old parent's world scale over the new one's, read before the move - one
factor, and the scale keys are multiplied by it (they stay keys; an unkeyed channel Maya's parent
command compensates), or a factor changing over the take (a parent's scale animated), and the
scale is keyed on every frame. OverRig cut the scale keys and hid scale and visibility; not copied.

Refused before anything changes (asked: «Отказывать для них»): a skeleton bone, a control of an
AdvancedSkeleton rig, the plugin's own nodes, an object riding a knot, locked or driven translate /
rotate channels, an uneven new parent, a scale channel locked or driven by anything but a time
curve while the parents' scales differ.

Spec: docs/superpowers/specs/2026-10-12-tools-parent-design.md
"""

import maya.cmds as cmds
import maya_timewarp

from maya_tools import knotplan as plan
from maya_tools import knots

#  maya_scenesetup.deletion.OUR_ATTR_PREFIXES (a test pins them equal): a node carrying one of
#  these is the plugin's own - a knot, a pivot, a weapon, armor, a space, a CoM, a label.
OUR_PREFIXES = ("skeldar", "mayaWeapon", "mayaArmor", "mayaSceneSetup", "rigPicker")


def _parent_of(path):
    return knots._parent(path)


def _world_scale(path):
    """The mean length of a node's world axes - 1 for the world itself."""
    if not path:
        return 1.0
    m = cmds.getAttr(path + ".worldMatrix[0]")
    return sum(sum(v * v for v in m[i * 4:i * 4 + 3]) ** 0.5 for i in range(3)) / 3.0


def _rig_part(path, rigs):
    """'' or what `path` is that must not move in the DAG."""
    import maya_rigs
    if cmds.objectType(path, isAType="joint"):
        return "a skeleton bone"
    if any(attr.startswith(OUR_PREFIXES) for attr in cmds.listAttr(path, userDefined=True) or []):
        return "the plugin's own node"
    rig = maya_rigs.rig_of(path, rigs)
    if rig is not None:
        if rig.namespace:
            if maya_rigs.namespace_of(path) == rig.namespace:
                return "a control of %s" % maya_rigs.label(rig)
        elif maya_rigs.under(path, rig.group):
            return "a control of %s" % maya_rigs.label(rig)
    return ""


def _refusal(node, new_parent, rigs):
    """'' or why `node` cannot move under `new_parent` (None: world level)."""
    name = plan.leaf(node)
    what = _rig_part(node, rigs)
    if what:
        return plan.rig_part_line(name, what)
    if knots.constraints_of(node):
        return plan.riding_refusal(name)
    locked, drivers = knots._channels(node, plan.CHANNELS, layers=True)
    if any(locked.values()):
        return plan.locked_line(name)
    _free, _skipped, refusal = plan.channel_plan(name, locked, drivers)
    if refusal:
        return refusal
    if new_parent:
        refusal = plan.uneven_parent(name, cmds.getAttr(new_parent + ".worldMatrix[0]"))
        if refusal:
            return refusal
    return ""


def _animates_scale(node):
    """True when something may change `node`'s world scale over the take: a scale channel fed by
    anything but a time curve holding one value, or an offset parent matrix fed at all."""
    for plug in ("scale",) + plan.SCALE:
        for source in cmds.listConnections(node + "." + plug, source=True, destination=False,
                                           skipConversionNodes=True) or []:
            if cmds.nodeType(source) not in plan.TIME_CURVES:
                return True
            if not plan.is_constant(cmds.keyframe(source, query=True, valueChange=True) or []):
                return True
    return bool(cmds.listConnections(node + ".offsetParentMatrix", source=True,
                                     destination=False))


def _scale_ratios(moves, span):
    """{node: [its old parent's world scale over its new parent's]} for `moves` [(node, new
    parent or None)], read before anything moves: one value when nothing in the parents' chains
    animates scale (the S key keys scale too - a constant curve), else one per frame of the span,
    read in one time walk (unrecorded)."""
    pairs = [(node, _parent_of(node), new) for node, new in moves]
    parents = []
    for _node, old, new in pairs:
        for parent in (old, new):
            if parent and parent not in parents:
                parents.append(parent)
    chain = set(n for parent in parents for n in knots._chain(parent))
    if not any(_animates_scale(n) for n in chain):
        readings = dict((parent, [_world_scale(parent)]) for parent in parents)
        frames = 1
    else:
        from maya_poselib import timewalk
        readings = dict((parent, []) for parent in parents)
        frames = int(span[1]) - int(span[0]) + 1
        with timewalk.Walk(fresh=False) as walk:
            for frame in range(int(span[0]), int(span[1]) + 1):
                walk.go(frame)
                for parent in parents:
                    readings[parent].append(_world_scale(parent))
    ones = [1.0] * frames
    return dict((node, [o / n for o, n in zip(readings.get(old, ones), readings.get(new, ones))])
                for node, old, new in pairs)


def _scale_plans(moves, span):
    """({node UUID: (kind, factor, ratios, the scale values now)}, '') - how each moving node's
    world scale crosses the move (`knotplan.scale_plan`) - or (None, refusal) before anything
    changes."""
    ratios = _scale_ratios(moves, span)
    plans = {}
    for node, _new in moves:
        kind, factor = plan.scale_plan(ratios[node])
        locked, drivers = knots._channels(node, plan.SCALE)
        refusal = plan.scale_refusal(plan.leaf(node), kind, locked, drivers)
        if refusal:
            return None, refusal
        values = dict((ch, cmds.getAttr(node + "." + ch)) for ch in plan.SCALE)
        plans[knots._uuid(node)] = (kind, factor, ratios[node], values)
    return plans, ""


def _carry_scale(node, scale_plan, span):
    """After the DAG move, `node`'s world scale as it was: keys multiplied by one factor (an
    unkeyed channel Maya's parent command has compensated already), or every frame of the span
    keyed when the factor changes."""
    kind, factor, ratios, values = scale_plan
    if kind == "keep":
        return
    for ch in plan.SCALE:
        plug = node + "." + ch
        curve = (cmds.listConnections(plug, source=True, destination=False,
                                      skipConversionNodes=True) or [None])[0]
        if kind == "rescale":
            if curve:
                cmds.scaleKey(curve, valueScale=factor, valuePivot=0.0)
            continue
        frames = range(int(span[0]), int(span[1]) + 1)
        before = ([cmds.keyframe(curve, query=True, eval=True, time=(f, f))[0] for f in frames]
                  if curve else [values[ch]] * len(ratios))
        after = plan.carried_scale(before, ratios)
        if curve:
            cmds.cutKey(plug, time=(span[0], span[1]), clear=True)
        if plan.is_constant(after) and not cmds.listConnections(plug, source=True,
                                                                destination=False):
            cmds.setAttr(plug, after[0])
            continue
        for frame, value in zip(frames, after):
            cmds.setKeyframe(node, attribute=ch, time=frame, value=value)


def _take(nodes, parents):
    """The whole take for the move: playback ∪ animation range ∪ the keys of the moving nodes,
    their ancestors now and their new parents' chains."""
    involved = []
    for node in list(nodes) + [p for p in parents if p]:
        for n in knots._chain(node):
            if n not in involved:
                involved.append(n)
    keys = cmds.keyframe(involved, query=True, timeChange=True) or []
    take = plan.take_range((cmds.playbackOptions(query=True, min=True),
                            cmds.playbackOptions(query=True, max=True)),
                           (cmds.playbackOptions(query=True, animationStartTime=True),
                            cmds.playbackOptions(query=True, animationEndTime=True)))
    return plan.span_for(take, keys, None)


def _rebake(nodes, span, operate, scales, layer=None):
    """Keep `nodes`' world motion across `operate(uuids)` (the DAG move) - their world scale
    too (`scales`, `_scale_plans`); the nodes after. A node on animation layers (2026-10-15)
    is not baked (`bakeResults` would land in the layers' blend node): what it shows in its new
    space is read on every frame and keyed on `layer` as final values, the other layers kept."""
    uuids = [knots._uuid(n) for n in nodes]
    locators, temps = [], []
    for node in nodes:
        loc = cmds.spaceLocator(name="skeldarReparent_" + plan.leaf(node))[0]
        loc = knots._by_uuid(knots._uuid(loc))
        cmds.setAttr(loc + ".rotateOrder", cmds.getAttr(node + ".rotateOrder"))
        temps.append(knots._constrain(cmds.parentConstraint, node, loc, maintainOffset=False))
        locators.append(loc)
    maya_timewarp.call(cmds.bakeResults, locators, attribute=list(plan.CHANNELS), time=(span[0], span[1]),
                     simulation=True, sampleBy=1, disableImplicitControl=True)
    cmds.delete([t for t in temps if cmds.objExists(t)])
    operate(uuids)
    nodes = [knots._by_uuid(u) for u in uuids]
    for uuid, node in zip(uuids, nodes):          # before the bake: a child's space reads it
        _carry_scale(node, scales[uuid], span)
    cons = [knots._constrain(cmds.parentConstraint, loc, node, maintainOffset=False)
            for loc, node in zip(locators, nodes)]
    from maya_tools import layered
    stacked = [n for n in nodes if layered.is_layered(n)]
    plain = [n for n in nodes if n not in stacked]
    first, last = int(round(span[0])), int(round(span[1]))
    shown = layered.read(stacked, plan.CHANNELS, range(first, last + 1)) if stacked else {}
    if plain:
        maya_timewarp.call(cmds.bakeResults, plain, attribute=list(plan.CHANNELS), time=(span[0], span[1]),
                         simulation=True, sampleBy=1, preserveOutsideKeys=True,
                         disableImplicitControl=True)
    cmds.delete([c for c in cons if cmds.objExists(c)])
    for node in stacked:          # a layered node: its new local motion keyed on `layer`
        layered.key_shown(node, plan.CHANNELS, first, last, shown[node], layer)
    plain_ids = set(knots._uuid(n) for n in plain)
    nodes = [knots._by_uuid(u) for u in uuids]
    for node in nodes:
        if knots._uuid(node) in plain_ids:
            knots._continuous(node, plan.CHANNELS, span[0], span[1])
    cmds.delete([loc for loc in locators if cmds.objExists(loc)])
    return nodes


def _layer_for(nodes):
    """(the layer a layered node's new motion is keyed on, refusal) - None when no node is on
    layers: the active layer (`layered.target`)."""
    from maya_tools import layered
    if not any(layered.is_layered(n) for n in nodes):
        return None, ""
    layer, refusal = layered.target()
    return layer, refusal or layered.check_target(layer, plan.CHANNELS)


def _to_world(path):
    if _parent_of(path):
        cmds.parent(path, world=True)


def inside(selection=None):
    """Inside: the selected objects go under the LAST selected, their motion kept."""
    nodes = knots._selection(selection)
    if len(nodes) < 2:
        return plan.INSIDE_TWO
    children, parent = nodes[:-1], nodes[-1]
    refusal = plan.inside_refusal(children, parent, _parent_of)
    if refusal:
        return refusal
    import maya_rigs
    rigs = maya_rigs.rigs()
    for child in children:
        refusal = _refusal(child, parent, rigs)
        if refusal:
            return refusal
    span = _take(children, [parent])
    scales, refusal = _scale_plans([(child, parent) for child in children], span)
    if refusal:
        return refusal
    layer, refusal = _layer_for(children)
    if refusal:
        return refusal
    parent_uuid = knots._uuid(parent)

    def operate(uuids):
        for uuid in uuids:
            cmds.parent(knots._by_uuid(uuid), knots._by_uuid(parent_uuid))

    with knots._press("skeldarInside"):
        moved = _rebake(children, span, operate, scales, layer)
        cmds.select(moved, replace=True)
    return plan.reparent_message("Inside", [plan.leaf(c) for c in children], plan.leaf(parent),
                                 span)


def to_world(selection=None):
    """World: the selected objects out to world level, their motion kept."""
    nodes = knots._selection(selection)
    if not nodes:
        return "select the objects to take out to world level"
    refusal = plan.world_refusal(nodes, _parent_of)
    if refusal:
        return refusal
    import maya_rigs
    rigs = maya_rigs.rigs()
    for node in nodes:
        refusal = _refusal(node, None, rigs)
        if refusal:
            return refusal
    span = _take(nodes, [])
    scales, refusal = _scale_plans([(node, None) for node in nodes], span)
    if refusal:
        return refusal
    layer, refusal = _layer_for(nodes)
    if refusal:
        return refusal

    def operate(uuids):
        for uuid in uuids:
            _to_world(knots._by_uuid(uuid))

    with knots._press("skeldarWorld"):
        moved = _rebake(nodes, span, operate, scales, layer)
        cmds.select(moved, replace=True)
    return plan.reparent_message("World", [plan.leaf(n) for n in nodes], None, span)


def swap(selection=None):
    """Swap: the others go under the LAST selected and the last takes the place of the one
    before it (select the parent first, then its child), the motion of every one kept."""
    nodes = knots._selection(selection)
    moves, refusal = plan.swap_plan(nodes, _parent_of)
    if refusal:
        return refusal
    import maya_rigs
    rigs = maya_rigs.rigs()
    for node, new_parent in moves:
        refusal = _refusal(node, new_parent, rigs)
        if refusal:
            return refusal
    span = _take(nodes, [p for _n, p in moves])
    scales, refusal = _scale_plans(moves, span)
    if refusal:
        return refusal
    layer, refusal = _layer_for(nodes)
    if refusal:
        return refusal
    ids = dict((n, knots._uuid(n)) for n in nodes)
    plan_ids = [(ids[n], knots._uuid(p) if p else None) for n, p in moves]

    def operate(uuids):
        for uuid in uuids:
            _to_world(knots._by_uuid(uuid))
        for node_id, parent_id in plan_ids:
            if parent_id:
                cmds.parent(knots._by_uuid(node_id), knots._by_uuid(parent_id))

    with knots._press("skeldarSwap"):
        moved = _rebake(nodes, span, operate, scales, layer)
        cmds.select(moved, replace=True)
    return plan.reparent_message("Swap", [plan.leaf(n) for n in nodes], plan.leaf(nodes[-1]),
                                 span)
