"""Our Channel Box's road into Maya (cmds): what the box shows - the selection's
channels and their state - and what a press writes. The widget talks to Maya only
through this module (a fake one in the tests).

Maya's own `mainChannelBox` stays alive, hidden, while ours shows: its object lists
(shapes, inputs, outputs) are read from it, and the channels ours selects are written
into it so every tool reading the Channel Box's selection keeps working.
Spec: docs/superpowers/specs/2026-10-18-channel-box-rows-design.md
"""

import maya.cmds as cmds

MAIN = "mainChannelBox"
TIME_TOL = 1e-3
TITLES = (("shapes", "SHAPES", "shapeObjectList"), ("inputs", "INPUTS", "historyObjectList"),
          ("outputs", "OUTPUTS", "outputObjectList"))


def _box_exists():
    try:
        return bool(cmds.channelBox(MAIN, exists=True))
    except Exception:                                        # noqa: BLE001
        return False


def _box_list(flag):
    if not _box_exists():
        return []
    try:
        return list(cmds.channelBox(MAIN, q=True, **{flag: True}) or [])
    except Exception:                                        # noqa: BLE001
        return []


def now():
    return float(cmds.currentTime(q=True))


def short(node):
    try:
        from maya_scenetabs import scope
        return scope.local(node.split("|")[-1])
    except Exception:                                        # noqa: BLE001
        return node.split("|")[-1]


def objects():
    """The selected nodes, long names, the lead (last selected) last."""
    found = cmds.ls(selection=True, long=True, objectsOnly=True) or []
    out = []
    for node in found:
        if node not in out:
            out.append(node)
    return out


def _attrs(node):
    keyable = cmds.listAttr(node, keyable=True) or []
    shown = cmds.listAttr(node, channelBox=True) or []
    out = []
    for attr in keyable + shown:
        if attr not in out:
            out.append(attr)
    return ordered(out)


def ordered(attrs):
    """Maya's Channel Box order: listAttr puts visibility first, the Channel Box shows
    it after the scales (seen live 2026-10-18)."""
    if "visibility" not in attrs:
        return list(attrs)
    rest = [a for a in attrs if a != "visibility"]
    at = 0
    for i, a in enumerate(rest):
        if a.startswith(("translate", "rotate", "scale")) and not a.startswith(("rotateOrder", "rotateAxis")):
            at = i + 1
    return rest[:at] + ["visibility"] + rest[at:]


def _shapes(lead):
    try:
        return cmds.listRelatives(lead, shapes=True, noIntermediate=True, fullPath=True) or []
    except Exception:                                        # noqa: BLE001
        return []


def _inputs(lead):
    """The history Maya's Channel Box lists under INPUTS: what feeds the shapes,
    DAG nodes left out, the uninteresting ones (groupParts, tweak) too."""
    out = []
    for shape in _shapes(lead):
        try:
            found = cmds.listHistory(shape, pruneDagObjects=True, interestLevel=2) or []
        except Exception:                                    # noqa: BLE001
            found = []
        for node in found:
            if node not in out and node != shape:
                out.append(node)
    return out


def _object_list(kind, flag, lead):
    """Maya's own list for SHAPES / INPUTS / OUTPUTS - empty while its Channel Box is
    hidden (live 2026-10-18), so shapes and inputs are read ourselves then."""
    found = _box_list(flag)
    if found:
        return found
    if kind == "shapes":
        return _shapes(lead)
    if kind == "inputs":
        return _inputs(lead)
    return []


def _enum_names(node, attr):
    try:
        text = (cmds.attributeQuery(attr, node=node, listEnum=True) or [""])[0]
    except Exception:                                        # noqa: BLE001
        return []
    return [part.split("=")[0] for part in text.split(":") if part]


def _range(node, attr):
    try:
        if (cmds.attributeQuery(attr, node=node, minExists=True)
                and cmds.attributeQuery(attr, node=node, maxExists=True)):
            return (cmds.attributeQuery(attr, node=node, minimum=True)[0],
                    cmds.attributeQuery(attr, node=node, maximum=True)[0])
    except Exception:                                        # noqa: BLE001
        pass
    return None, None


def _source(plug):
    """'curve' (time keys), 'layer' (an animation layer's blend), 'driven' (anything
    else feeding it) or None; a mute node is looked through."""
    try:
        found = cmds.listConnections(plug, source=True, destination=False,
                                     skipConversionNodes=True) or []
    except Exception:                                        # noqa: BLE001
        return None
    if not found:
        return None
    kind = cmds.nodeType(found[0])
    if kind == "mute":
        inner = cmds.listConnections(found[0] + ".input", source=True, destination=False,
                                     skipConversionNodes=True) or []
        kind = cmds.nodeType(inner[0]) if inner else "animCurveTL"
    if kind.startswith("animCurveT"):
        return "curve"
    if kind.startswith("animBlendNode"):
        return "layer"
    return "driven"


def channel(node, attr, objects_=None, frame=None, main=False):
    """One row's facts: the value, its kind, its limits, its state."""
    plug = node + "." + attr
    frame = now() if frame is None else frame
    kind = cmds.getAttr(plug, type=True) or "double"
    value = cmds.getAttr(plug)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else 0
    if isinstance(value, bool):
        value = int(value)
    try:
        nice = cmds.attributeName(plug, nice=True)
    except Exception:                                        # noqa: BLE001
        nice = attr
    lo, hi = _range(node, attr)
    source = _source(plug)
    try:
        muted = bool(cmds.mute(plug, q=True))
    except Exception:                                        # noqa: BLE001
        muted = False
    keys, bds, on_key, breakdown, changed = [], [], False, False, False
    if source in ("curve", "layer") or muted:
        keys = sorted(set(cmds.keyframe(plug, q=True, timeChange=True) or []))
        on_key = any(abs(k - frame) < TIME_TOL for k in keys)
        if keys:
            bds = sorted(set(cmds.keyframe(plug, q=True, breakdown=True) or []))
            breakdown = on_key and any(abs(k - frame) < TIME_TOL for k in bds)
        if source == "curve" and not muted and keys and kind not in ("bool", "enum"):
            try:
                curve = (cmds.keyframe(plug, q=True, eval=True, time=(frame, frame)) or [None])[0]
                changed = curve is not None and abs(float(curve) - float(value)) > 1e-4
            except Exception:                                # noqa: BLE001
                changed = False
    targets = [plug]
    if main:
        targets = []
        for obj in objects_ or [node]:
            try:
                if cmds.attributeQuery(attr, node=obj, exists=True):
                    targets.append(obj + "." + attr)
            except Exception:                                # noqa: BLE001
                pass
    return {"key": attr if main else plug, "node": node, "attr": attr, "plug": plug,
            "nice": nice, "kind": kind, "value": value,
            "names": _enum_names(node, attr) if kind == "enum" else None,
            "lo": lo, "hi": hi, "locked": bool(cmds.getAttr(plug, lock=True)),
            "muted": muted, "source": source, "keys": keys, "breakdowns": bds, "on_key": on_key,
            "breakdown": breakdown, "changed": changed, "targets": targets}


def channels(node, objects_=None, main=False):
    out = []
    frame = now()
    for attr in _attrs(node):
        try:
            out.append(channel(node, attr, objects_, frame, main))
        except Exception:                                    # noqa: BLE001 - a plug the box cannot show
            pass
    return out


def snapshot(opened=()):
    """{'objects', 'lead', 'frame', 'sections'}: the lead object's channels, then its
    shapes, inputs and outputs (Maya's own lists) as closed sections unless their key
    is in `opened`."""
    objs = objects()
    if not objs:
        return {"objects": [], "lead": None, "frame": now(), "sections": []}
    lead = objs[-1]
    sections = [{"key": "main", "kind": "main", "label": short(lead), "title": "",
                 "channels": channels(lead, objs, main=True)}]
    for kind, title, flag in TITLES:
        first = True
        for node in _object_list(kind, flag, lead):
            if not cmds.objExists(node):
                continue
            key = kind + ":" + node
            sections.append({"key": key, "kind": kind, "label": short(node),
                             "title": title if first else "",
                             "channels": channels(node) if key in opened else []})
            first = False
    return {"objects": objs, "lead": lead, "frame": now(), "sections": sections}


def values(plugs):
    out = []
    for plug in plugs:
        try:
            v = cmds.getAttr(plug)
            if isinstance(v, (list, tuple)):
                v = v[0] if v else 0
            out.append(int(v) if isinstance(v, bool) else v)
        except Exception:                                    # noqa: BLE001
            out.append(None)
    return out


def write(pairs):
    """[(plug, value)] set - a locked plug is passed by. How many were set."""
    done = 0
    for plug, value in pairs:
        try:
            if cmds.getAttr(plug, lock=True):
                continue
            cmds.setAttr(plug, value)
            done += 1
        except Exception:                                    # noqa: BLE001 - a driven plug
            pass
    return done


def key(plugs, breakdown=False):
    done = 0
    for plug in plugs:
        try:
            if cmds.getAttr(plug, lock=True):
                continue
            cmds.setKeyframe(plug, breakdown=bool(breakdown))
            done += 1
        except Exception:                                    # noqa: BLE001
            pass
    return done


def unkey(plugs, frame):
    done = 0
    for plug in plugs:
        try:
            done += int(cmds.cutKey(plug, time=(frame, frame), clear=True) or 0)
        except Exception:                                    # noqa: BLE001
            pass
    return done


def mute(plugs, on):
    for plug in plugs:
        try:
            if on:
                cmds.mute(plug)
            else:
                cmds.mute(plug, disable=True, force=True)
        except Exception:                                    # noqa: BLE001
            pass


def lock(plugs, on):
    for plug in plugs:
        try:
            cmds.setAttr(plug, lock=bool(on))
        except Exception:                                    # noqa: BLE001
            pass


def _sources(plug):
    try:
        return cmds.listConnections(plug, source=True, destination=False, plugs=True,
                                    skipConversionNodes=True) or []
    except Exception:                                        # noqa: BLE001
        return []


def select_connection(plugs):
    nodes = []
    for plug in plugs:
        for src in _sources(plug):
            node = src.split(".")[0]
            if node not in nodes:
                nodes.append(node)
    if nodes:
        cmds.select(nodes, replace=True)
    return nodes


def break_connections(plugs):
    """Each plug's input cut; a time curve feeding nothing else goes with it."""
    done = 0
    for plug in plugs:
        try:
            raw = cmds.listConnections(plug, source=True, destination=False, plugs=True) or []
        except Exception:                                    # noqa: BLE001
            raw = []
        for src in raw:
            try:
                cmds.disconnectAttr(src, plug)
                done += 1
                node = src.split(".")[0]
                if (cmds.nodeType(node).startswith("animCurve")
                        and not cmds.listConnections(node, source=False, destination=True)):
                    cmds.delete(node)
            except Exception:                                # noqa: BLE001
                pass
    return done


def sync_selection(plugs):
    """The channels ours selects, written into Maya's hidden Channel Box."""
    if not _box_exists():
        return False
    try:
        cmds.channelBox(MAIN, edit=True, select=list(plugs) if plugs else "")
        return True
    except Exception:                                        # noqa: BLE001
        return False


def speed():
    try:
        return float(cmds.channelBox(MAIN, q=True, speed=True) or 1.0) if _box_exists() else 1.0
    except Exception:                                        # noqa: BLE001
        return 1.0


def set_speed(value):
    try:
        cmds.channelBox(MAIN, edit=True, speed=float(value))
    except Exception:                                        # noqa: BLE001
        pass


def precision():
    try:
        return int(cmds.channelBox(MAIN, q=True, precision=True) or 3) if _box_exists() else 3
    except Exception:                                        # noqa: BLE001
        return 3


def chunk_open(name):
    cmds.undoInfo(openChunk=True, chunkName=name)


def chunk_close():
    cmds.undoInfo(closeChunk=True)


def layers():
    from maya_timebar import scene as bar_scene
    try:
        return bar_scene.layers()
    except Exception:                                        # noqa: BLE001
        return []


def layer_label():
    from maya_timebar import scene as bar_scene
    try:
        return bar_scene.layer_label()
    except Exception:                                        # noqa: BLE001
        return ""


def pick_layer(name):
    from maya_timebar import scene as bar_scene
    bar_scene.pick_layer(name)


def show_maya_box():
    """⋮ off: ours away, Maya's back (the side panel rebuilt)."""
    import maya_channelbox
    return maya_channelbox.set_enabled(False)
