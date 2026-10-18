"""The Time Bar's layer panel in Maya (2026-10-18): animation and display layers
read and written, every write one undo chunk. The active scene tab's layers only.

Measured (docs/superpowers/plans/probe_timebar_layers.py, Maya 2027):
- `animLayer -q -root` is BaseAnimation, `-children` its layers in order; `-attribute` answers FULL plug
  names ('cube.translateX'); `findCurveForPlug` answers a LIST (None / raises for a plug it has no keys for).
- A layer has mute, solo, lock, weight, override; a display layer visibility, hideOnPlayback, displayType,
  color, displayOrder, overrideRGBColors, overrideColorRGB.
- `cmds.colorIndex(i, q=True)` answers None in standalone: an index colour then reads "" (no table is kept).
- MERGE: the global MEL proc `animLayerMerge(string $layers[])` of performAnimLayerMerge.mel, unknown until
  that file is sourced. It makes a NEW layer `Merged_Layer` before the first given layer, bakes with
  `bakeResults -destinationLayer`, deletes the source layers and reads the `animLayerMerge*` optionVars
  (Up, DeleteLayers ...). Here the options it reads are set for the call and put back, and the result is
  renamed to the upper layer's name, so "A merged into B" leaves one layer called A.

Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md
"""

import sys

import maya.cmds as cmds


CHUNK = "skeldarTimeBarLayers"
FLAGS = ("mute", "solo", "lock")
MERGE_OPTIONS = (("animLayerMergeUp", 1), ("animLayerMergeDeleteLayers", 1))


class _chunk(object):
    """One undo chunk (scene._chunk, on this module's cmds)."""

    def __enter__(self):
        cmds.undoInfo(openChunk=True, chunkName=CHUNK)

    def __exit__(self, *_exc):
        cmds.undoInfo(closeChunk=True)
        return False


def _active_only(names):
    try:
        from maya_scenetabs import scope
        return list(scope.active_only(names))
    except Exception:                                        # noqa: BLE001
        return list(names)


def _label(name):
    try:
        from maya_scenetabs import scope
        return scope.local(name)
    except Exception:                                        # noqa: BLE001
        return name.split(":")[-1]


def _is_tab_root(name):
    try:
        from maya_scenetabs import layers
        return layers.is_tab_root_name(name)
    except Exception:                                        # noqa: BLE001
        return False


def _get(plug, default=None):
    try:
        return cmds.getAttr(plug)
    except Exception:                                        # noqa: BLE001
        return default


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(max(0.0, min(1.0, c)) * 255)) for c in rgb)


# -- reads -------------------------------------------------------------------------

def _anim_names():
    """(root, [layer, ...]) - every layer below the root, breadth first, scoped. A tab's
    own AnimLayerRoot is the root then (it reads BaseAnimation) and is not a layer."""
    root = cmds.animLayer(q=True, root=True)
    if not root:
        return None, []
    found, i = [root], 0
    while i < len(found):
        found.extend(cmds.animLayer(found[i], q=True, children=True) or [])
        i += 1
    names = _active_only(found[1:])
    roots = [n for n in names if _is_tab_root(n)]
    if roots:
        root = roots[0]
    return root, [n for n in names if not _is_tab_root(n)]


def anim_layers():
    """The animation layers, newest first, BaseAnimation last; [] without any."""
    root, names = _anim_names()
    if not root:
        return []
    picked = [n for n in names if cmds.animLayer(n, q=True, selected=True)]
    active = picked[-1] if picked else root
    rows = []
    for name in reversed(names):
        rows.append({"name": name, "label": _label(name),
                     "mode": "ovr" if _get(name + ".override", False) else "add",
                     "weight": float(_get(name + ".weight", 1.0)),
                     "weight_keyed": bool(cmds.listConnections(name + ".weight", source=True,
                                                               destination=False, type="animCurve")),
                     "mute": bool(_get(name + ".mute", False)), "solo": bool(_get(name + ".solo", False)),
                     "lock": bool(_get(name + ".lock", False)), "active": name == active, "base": False})
    rows.append({"name": root, "label": "BaseAnimation", "mode": "base", "weight": 1.0,
                 "weight_keyed": False, "mute": bool(_get(root + ".mute", False)), "solo": False,
                 "lock": bool(_get(root + ".lock", False)), "active": root == active, "base": True})
    return rows


def _colour(name):
    if _get(name + ".overrideRGBColors", False):
        rgb = _get(name + ".overrideColorRGB")
        if not rgb:
            return ""
        return _hex(rgb[0] if isinstance(rgb[0], (list, tuple)) else rgb)
    index = int(_get(name + ".color", 0) or 0)
    if index <= 0:
        return ""
    try:
        rgb = cmds.colorIndex(index, q=True)
    except Exception:                                        # noqa: BLE001
        rgb = None
    return _hex(rgb) if rgb else ""


def display_layers():
    """Maya's display layers, the Layer Editor's order (displayOrder, highest first)."""
    names = [n for n in (cmds.ls(type="displayLayer") or []) if n.split(":")[-1] != "defaultLayer"]
    names = _active_only(names)
    names.sort(key=lambda n: -(_get(n + ".displayOrder", 0) or 0))
    return [{"name": n, "label": _label(n), "colour": _colour(n),
             "visible": bool(_get(n + ".visibility", True)),
             "playback": not bool(_get(n + ".hideOnPlayback", False)),
             "type": int(_get(n + ".displayType", 0) or 0)} for n in names]


def _selected_nodes():
    return set(n.split(".")[0] for n in (cmds.ls(selection=True) or []))


TIME_CURVES = ["animCurveTL", "animCurveTA", "animCurveTT", "animCurveTU"]


def _base_curves(root, nodes):
    """The base layer's time curves of `nodes` (2026-10-18, the final review: one
    findCurveForPlug per keyable attribute of every selected node, and a keyframe
    call per curve): the curves on the nodes themselves (a channel no layer holds) in
    one listConnections; then, for the channels a layer's blend node drives (one more
    listConnections), the base curve under the blends, which only the root's
    findCurveForPlug finds. A driven key's curve is no time and is left out."""
    nodes = sorted(nodes)
    curves = set(cmds.listConnections(nodes, source=True, destination=False, type="animCurve") or [])
    pairs = cmds.listConnections(nodes, source=True, destination=False, type="animBlendNodeBase",
                                 connections=True, plugs=True) or []
    for plug in sorted(set(pairs[0::2])):
        try:
            curves.update(cmds.animLayer(root, q=True, findCurveForPlug=plug) or [])
        except Exception:                                    # noqa: BLE001 - trap 211
            pass
    if not curves:
        return []
    return cmds.ls(sorted(curves), type=TIME_CURVES) or []


def keys_by_layer(names):
    """{layer: [times]} of the selection's keys in each layer of `names`."""
    nodes = _selected_nodes()
    out = {}
    if not nodes:
        return out
    root, _layers = _anim_names()
    for name in names:
        if name == root:
            curves = _base_curves(root, nodes)
        else:
            curves = []
            for plug in (cmds.animLayer(name, q=True, attribute=True) or []):
                if plug.split(".")[0] not in nodes:
                    continue
                try:
                    curves.extend(cmds.animLayer(name, q=True, findCurveForPlug=plug) or [])
                except Exception:                            # noqa: BLE001 - trap 211
                    pass
        out[name] = sorted(set(cmds.keyframe(curves, q=True, timeChange=True) or [])) if curves else []
    return out


# -- writes on animation layers -------------------------------------------------------

def _is_root(name):
    return name == _anim_names()[0]


def pick(name):
    from . import scene
    with _chunk():
        scene.pick_layer(name)
    return True, ""


def set_flag(name, flag, on):
    if flag not in FLAGS:
        return False, "no such switch: %s" % flag
    if flag == "solo" and _is_root(name):
        return False, "BaseAnimation has no solo"
    with _chunk():
        cmds.setAttr(name + "." + flag, bool(on))
    return True, ""


#  kept on sys (trap 111): a weight chunk opened by a module an install purged is
#  still the one a rebuild's destroy_all must close
_WEIGHT = sys.__dict__.setdefault("_skeldar_timebar_weight", {"open": False})


def begin_weight():
    if _WEIGHT["open"]:                      # a lost end_weight must not nest chunks
        end_weight()
    cmds.undoInfo(openChunk=True, chunkName=CHUNK)
    _WEIGHT["open"] = True


def set_weight(name, value):
    """While dragging: a keyed weight is keyed at the current frame, else set."""
    value = max(0.0, min(1.0, float(value)))
    if cmds.listConnections(name + ".weight", source=True, destination=False, type="animCurve"):
        cmds.setKeyframe(name, attribute="weight", value=value)
    else:
        cmds.setAttr(name + ".weight", value)
    return True, ""


def end_weight():
    if _WEIGHT["open"]:
        cmds.undoInfo(closeChunk=True)
        _WEIGHT["open"] = False


def set_mode(name, mode):
    if _is_root(name):
        return False, "BaseAnimation has no mode"
    with _chunk():
        cmds.setAttr(name + ".override", mode == "ovr")
    return True, ""


def rename(name, new):
    new = (new or "").strip()
    if not new or _is_root(name):
        return False, "nothing renamed"
    with _chunk():
        done = cmds.rename(name, new)
    return True, "renamed to %s" % _label(done)


def create_anim():
    from . import scene
    with _chunk():
        if cmds.ls(selection=True):
            name = cmds.animLayer("AnimLayer1", addSelectedObjects=True)
        else:
            name = cmds.animLayer("AnimLayer1")
        scene.pick_layer(name)
    return True, "%s made" % _label(name)


def add_selection(name):
    if not cmds.ls(selection=True):
        return False, "nothing selected"
    with _chunk():
        cmds.animLayer(name, e=True, addSelectedObjects=True)
    return True, ""


def remove_selection(name):
    nodes = _selected_nodes()
    if not nodes:
        return False, "nothing selected"
    plugs = [p for p in (cmds.animLayer(name, q=True, attribute=True) or []) if p.split(".")[0] in nodes]
    if not plugs:
        return False, "the selection is not in %s" % _label(name)
    with _chunk():
        for plug in plugs:
            cmds.animLayer(name, e=True, removeAttribute=plug)
    return True, ""


def merge_down(name):
    """The layer and the one under it become one layer, by Maya's own merge; the result
    keeps the upper layer's name."""
    rows = anim_layers()
    names = [r["name"] for r in rows]
    if name not in names or rows[names.index(name)]["base"]:
        return False, "BaseAnimation has nothing under it"
    under = names[names.index(name) + 1]
    if rows[names.index(under)]["base"]:
        return False, "nothing to merge into: %s is on BaseAnimation" % _label(name)
    import maya.mel as mel
    mel.eval('source "performAnimLayerMerge.mel"')
    before = set(names)
    kept = {}
    for opt, value in MERGE_OPTIONS:
        if cmds.optionVar(exists=opt):
            kept[opt] = cmds.optionVar(q=opt)
        cmds.optionVar(intValue=(opt, value))
    try:
        with _chunk():
            mel.eval('animLayerMerge({"%s", "%s"})' % (under, name))
            made = [n for n in (r["name"] for r in anim_layers()) if n not in before]
            if made:
                try:
                    cmds.rename(made[0], name.split(":")[-1])
                except Exception:                            # noqa: BLE001 - the name stays Maya's
                    pass
    finally:
        for opt, value in MERGE_OPTIONS:
            if opt in kept:
                cmds.optionVar(intValue=(opt, kept[opt]))
            else:
                cmds.optionVar(remove=opt)
    return True, "%s merged into %s" % (_label(name), _label(under))


def delete_anim(name):
    if _is_root(name):
        return False, "BaseAnimation stays"
    with _chunk():
        cmds.delete(name)
    return True, "%s deleted" % _label(name)


def select_objects(name):
    nodes = sorted(set(p.split(".")[0] for p in (cmds.animLayer(name, q=True, attribute=True) or [])))
    cmds.select(nodes, replace=True)
    return True, ""


# -- display layers ------------------------------------------------------------------

def set_display(name, flag, value):
    attr = {"visible": "visibility", "playback": "hideOnPlayback", "type": "displayType", "colour": "color"}.get(flag)
    if attr is None:
        return False, "no such switch: %s" % flag
    if flag == "playback":
        value = not value
    with _chunk():
        if flag == "colour":
            cmds.setAttr(name + ".overrideRGBColors", False)
        cmds.setAttr(name + "." + attr, value)
    return True, ""


def create_display():
    with _chunk():
        if cmds.ls(selection=True):
            name = cmds.createDisplayLayer(name="layer1", noRecurse=True)
        else:
            name = cmds.createDisplayLayer(name="layer1", empty=True)
    return True, "%s made" % _label(name)


def display_add(name):
    picked = cmds.ls(selection=True) or []
    if not picked:
        return False, "nothing selected"
    with _chunk():
        cmds.editDisplayLayerMembers(name, picked, noRecurse=True)
    return True, ""


def display_remove(name):
    picked = cmds.ls(selection=True) or []
    if not picked:
        return False, "nothing selected"
    with _chunk():
        cmds.editDisplayLayerMembers("defaultLayer", picked, noRecurse=True)
    return True, ""


def display_select(name):
    cmds.select(cmds.editDisplayLayerMembers(name, q=True, fullNames=True) or [], replace=True)
    return True, ""


def delete_display(name):
    with _chunk():
        cmds.delete(name)
    return True, "%s deleted" % _label(name)


# -- memory --------------------------------------------------------------------------

def option(name, default):
    return cmds.optionVar(q=name) if cmds.optionVar(exists=name) else default


def set_option(name, value):
    if isinstance(value, str):
        cmds.optionVar(stringValue=(name, value))
    else:
        cmds.optionVar(intValue=(name, int(value)))
