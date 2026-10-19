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
    picked = [n for n in [root] + names if cmds.animLayer(n, q=True, selected=True)]
    preferred = [n for n in picked if _preferred(n)]
    active = preferred[-1] if preferred else ([n for n in picked if n != root] or picked or [root])[-1]
    selected = set(picked)
    rows = []
    for name in reversed(names):
        rows.append({"name": name, "label": _label(name),
                     "mode": "ovr" if _get(name + ".override", False) else "add",
                     "weight": float(_get(name + ".weight", 1.0)),
                     "weight_keyed": bool(cmds.listConnections(name + ".weight", source=True,
                                                               destination=False, type="animCurve")),
                     "mute": bool(_get(name + ".mute", False)), "solo": bool(_get(name + ".solo", False)),
                     "lock": bool(_get(name + ".lock", False)), "active": name == active,
                     "selected": name in selected, "base": False})
    rows.append({"name": root, "label": "BaseAnimation", "mode": "base", "weight": 1.0,
                 "weight_keyed": False, "mute": bool(_get(root + ".mute", False)), "solo": False,
                 "lock": bool(_get(root + ".lock", False)), "active": root == active,
                 "selected": root in selected, "base": True})
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
        curves = _layer_curves(name, nodes, root)
        out[name] = sorted(set(cmds.keyframe(curves, q=True, timeChange=True) or [])) if curves else []
    return out


def _maya_root(root):
    """Maya's own root layer: the base CURVES hang under it. In a scene tab the panel's
    BaseAnimation is the tab's `AnimLayerRoot`, a layer under `skeldarTabsLayerRoot` to
    Maya, holding no curves of its own (2026-10-19: the base lane and the timeline read
    nothing there, a key with the base active went to a layer)."""
    try:
        return cmds.animLayer(q=True, root=True) or root
    except Exception:                                        # noqa: BLE001
        return root


def _layer_curves(name, nodes, root):
    """The time curves of `nodes` in layer `name` (the base layer's for the root)."""
    if name == root:
        return _base_curves(_maya_root(root), nodes)
    curves = []
    for plug in (cmds.animLayer(name, q=True, attribute=True) or []):
        if plug.split(".")[0] not in nodes:
            continue
        try:
            curves.extend(cmds.animLayer(name, q=True, findCurveForPlug=plug) or [])
        except Exception:                                    # noqa: BLE001 - trap 211
            pass
    return sorted(set(curves))


def curves_of(names):
    """Every time curve of the selection in the layers `names` (the lanes' keys)."""
    nodes = _selected_nodes()
    if not nodes:
        return []
    root, _layers = _anim_names()
    out = set()
    for name in names:
        out.update(_layer_curves(name, nodes, root))
    return sorted(out)


def active_layer():
    """(root, the layer keys go to) - Maya's: the preferred selected layer, else the last
    selected one, else the base (`anim_layers`' rule, without reading every row).
    (None, None) without animation layers below the root."""
    root, layers = _anim_names()
    if not root or not layers:
        return None, None
    picked = [n for n in [root] + layers if cmds.animLayer(n, q=True, selected=True)]
    preferred = [n for n in picked if _preferred(n)]
    if preferred:
        return root, preferred[-1]
    rest = [n for n in picked if n != root]
    return root, (rest or picked or [root])[-1]


def active_curves():
    """The selection's curves in the active layer: what the Time Bar shows and edits
    with layers in the scene, as Maya's slider shows only the selected layer's keys
    (2026-10-19: «Ключи из других слоев на таймлайне не видно»). None without layers
    (every curve of the selection, as before)."""
    root, layer = active_layer()
    if layer is None:
        return None
    nodes = _selected_nodes()
    if not nodes:
        return []
    return _layer_curves(layer, nodes, root)


_KEY_FLAGS = sys.__dict__.setdefault("_skeldar_timebar_key_flags", {})


def _base_for_the_key(root):
    """BaseAnimation active in a scene tab: Maya's own root selected and preferred for
    the length of the key (every other layer not), so the key lands on the base as it
    does with no tabs; `after_key` puts every flag back."""
    maya_root = _maya_root(root)
    if maya_root == root:
        return False
    _KEY_FLAGS.clear()
    for layer in cmds.ls(type="animLayer") or []:
        try:
            _KEY_FLAGS[layer] = (bool(cmds.animLayer(layer, q=True, selected=True)),
                                 bool(cmds.animLayer(layer, q=True, preferred=True)))
            on = layer == maya_root
            cmds.animLayer(layer, e=True, selected=on, preferred=on)
        except Exception:                                    # noqa: BLE001
            pass
    return True


def after_key():
    """Called by our `performSetKeyframeArgList` after Maya's: the layer flags
    `_base_for_the_key` changed, put back. Never raises."""
    flags = dict(_KEY_FLAGS)
    _KEY_FLAGS.clear()
    for layer, (selected, preferred) in flags.items():
        try:
            if cmds.objExists(layer):
                cmds.animLayer(layer, e=True, selected=selected, preferred=preferred)
        except Exception:                                    # noqa: BLE001
            pass
    return bool(flags)


def before_key():
    """Called by our `performSetKeyframeArgList` (S, Key > Set Key) before Maya's: the
    selected objects not yet in the active layer are added to it, so the key goes into
    the layer that is selected (2026-10-19: «Если выбран слой то ключик ставим в него»;
    Maya would key them on another layer or the base); BaseAnimation active in a scene
    tab: Maya's own root takes the key (`_base_for_the_key`). A locked layer or no
    layers: nothing. Never raises."""
    try:
        root, layer = active_layer()
        if layer is None:
            return False
        if layer == root:
            return _base_for_the_key(root)
        if cmds.getAttr(layer + ".lock"):
            return False
        nodes = sorted(_selected_nodes())
        if not nodes:
            return False
        have = set(p.split(".")[0] for p in (cmds.animLayer(layer, q=True, attribute=True) or []))
        missing = [n for n in nodes if n not in have and cmds.listAttr(n, keyable=True)]
        if not missing:
            return False
        cmds.animLayer(layer, e=True, addRelatedKG=True, attribute=[
            "%s.%s" % (n, a) for n in missing for a in (cmds.listAttr(n, keyable=True) or [])])
        return True
    except Exception:                                        # noqa: BLE001
        return False


KEY_PROC = "performSetKeyframeArgList"
KEY_HOOK_VERSION = 2        # raised when the wrapper changes: a session sources it again
KEY_MAYA = "skeldarMayaPerformSetKeyframeArgList"
KEY_WRAPPER = r'''
global proc string performSetKeyframeArgList(string $version, string $args[])
{
    catch(python("__import__('maya_timebar.layerscene', fromlist=['layerscene']).before_key()"));
    string $result;
    int $failed = catch($result = %s($version, $args));
    catch(python("__import__('maya_timebar.layerscene', fromlist=['layerscene']).after_key()"));
    if ($failed)
        warning "Set Key failed - see above";
    return $result;
}
''' % KEY_MAYA


def key_hook():
    """Our `performSetKeyframeArgList` over Maya's (a copy of Maya's file, its proc
    renamed), once a session; GUI only. A Maya whose file is not the one this knows
    keeps its own. Never raises."""
    import re
    state = sys.__dict__.setdefault("_skeldar_timebar_key_hook", {})
    if state.get("done") == KEY_HOOK_VERSION:            # an older build's wrapper is replaced
        return state.get("ok", False)
    state["done"], state["ok"] = KEY_HOOK_VERSION, False
    try:
        if cmds.about(batch=True):
            return False
        import os
        import tempfile
        import maya.mel as mel
        path = mel.eval('whatIs "%s"' % KEY_PROC)
        path = path.split(": ", 1)[-1].strip() if ":" in path else ""
        if not path.lower().endswith(".mel") or not os.path.exists(path):
            mel.eval('source "%s.mel"' % KEY_PROC)
            path = mel.eval('whatIs "%s"' % KEY_PROC).split(": ", 1)[-1].strip()
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        header = re.compile(r"global\s+proc\s+string\s+performSetKeyframeArgList\s*\(")
        if len(header.findall(text)) != 1:
            print("Time Bar: Maya's %s is not the one we know - keys go where Maya puts them" % KEY_PROC)
            return False
        copy = os.path.join(tempfile.gettempdir(), "skeldar_timebar", "skeldarSetKeyframe.mel")
        if not os.path.isdir(os.path.dirname(copy)):
            os.makedirs(os.path.dirname(copy))
        with open(copy, "w", encoding="utf-8") as handle:
            handle.write(header.sub("global proc string %s(" % KEY_MAYA, text, count=1))
        mel.eval('source "%s"' % copy.replace("\\", "/"))
        mel.eval(KEY_WRAPPER)
        state["ok"] = True
        return True
    except Exception:                                        # noqa: BLE001
        import traceback
        print(traceback.format_exc())
        return False


def _preferred(name):
    try:
        return cmds.animLayer(name, q=True, preferred=True) is True
    except Exception:                                        # noqa: BLE001
        return False


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


def free_name(stem, taken, first=1):
    """The plainest name of `stem` not in `taken` (leaf names): `stem<first>`,
    `stem<first + 1>` ... - `first` 0 tries the bare stem first."""
    taken = set(taken)
    if first == 0 and stem not in taken:
        return stem
    i = max(1, first)
    while "%s%d" % (stem, i) in taken:
        i += 1
    return "%s%d" % (stem, i)


def _blends_of(layer):
    try:
        return [b for b in (cmds.animLayer(layer, q=True, blendNodes=True) or []) if cmds.objExists(b)]
    except Exception:                                        # noqa: BLE001
        return []


def _layer_named_blends(ns, stems):
    """Blend nodes in namespace `ns` named like a layer (`AnimLayer4`): in a scene tab Maya
    names a new layer's blend nodes after the next free LAYER name, which then pushes the
    next layer's number on by a dozen (AnimLayer3, 15, 27 - measured 2026-10-19)."""
    out = []
    for layer in cmds.ls(type="animLayer") or []:
        if layer.rpartition(":")[0] != ns:
            continue
        for blend in _blends_of(layer):
            leaf = blend.rpartition(":")[2]
            if any(leaf.startswith(stem) and leaf[len(stem):].isdigit() or leaf == stem for stem in stems):
                out.append((blend, layer))
    return out


def _named(layer, stem, first=1):
    """`layer` renamed to the plainest free `stem` name in its own namespace (2026-10-19:
    «странные названия слоев» - Maya gave AnimLayer3, AnimLayer15, AnimLayer27,
    Merged_Layer2408). Blend nodes of the namespace's layers that wear a layer's name
    are renamed `<layer>_blend` first, so they hold no layer number."""
    ns = layer.rpartition(":")[0]
    absolute = (lambda leaf: ":%s:%s" % (ns, leaf)) if ns else (lambda leaf: ":" + leaf)
    for blend, owner in _layer_named_blends(ns, ("AnimLayer", "Merged_Layer")):
        try:
            cmds.rename(blend, absolute(owner.rpartition(":")[2] + "_blend#"))
        except Exception:                                    # noqa: BLE001
            pass
    leaf = layer.rpartition(":")[2]
    pattern = (":%s:%s*" % (ns, stem)) if ns else (":%s*" % stem)
    taken = set(n.split("|")[-1].rpartition(":")[2] for n in (cmds.ls(pattern) or []))
    taken.discard(leaf)
    want = free_name(stem, taken, first)
    if want != leaf:
        try:
            layer = cmds.rename(layer, absolute(want))
        except Exception:                                    # noqa: BLE001 - Maya's name stays
            return layer
    for blend in _blends_of(layer):
        if blend.rpartition(":")[2].startswith(leaf + "_blend") and leaf != want:
            try:
                cmds.rename(blend, absolute(want + "_blend#"))
            except Exception:                                # noqa: BLE001
                pass
    return layer


def create_anim():
    from . import scene
    with _chunk():
        if cmds.ls(selection=True):
            name = cmds.animLayer("AnimLayer1", addSelectedObjects=True)
        else:
            name = cmds.animLayer("AnimLayer1")
        #  in a scene tab the new layer belongs under the tab's own root, not the session's
        root = _anim_names()[0]
        if root and cmds.animLayer(name, q=True, parent=True) != root:
            cmds.animLayer(name, e=True, parent=root)
        name = _named(name, "AnimLayer")
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
        #  the layer right over the base merges into BaseAnimation, as Maya's Merge Layers
        #  does with both selected (2026-10-19: «нельзя слой смерджить с базовым»)
        return merge_selected([under, name])
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


def _mel_strings(names):
    return "{%s}" % ", ".join('"%s"' % n for n in names)


def select_layers(names, active=None):
    """Maya's own layer selection (2026-10-19, «множество слоев выделяем через ctrl»):
    `names` selected, every other layer not, `active` (else the last of `names`) the
    preferred one keys go to; the Layer Editor's `$gSelectedAnimLayers` follows."""
    from . import scene
    root, layers = _anim_names()
    if not root:
        return False, "no animation layers"
    every = [root] + layers
    names = [n for n in every if n in set(names)]
    active = active if active in names else (names[-1] if names else None)
    with _chunk():
        for other in every:
            try:
                cmds.animLayer(other, e=True, selected=other in names, preferred=other == active)
            except Exception:                                # noqa: BLE001
                pass
    try:
        import maya.mel as mel
        mel.eval("global string $gSelectedAnimLayers[]; $gSelectedAnimLayers = %s;" % _mel_strings(names))
        #  no rebuild of Maya's Layer Editor here: its treeView re-selects row by row while it
        #  rebuilds and a selection of several came back as one (2026-10-19)
    except Exception:                                        # noqa: BLE001 - a UI refresh only
        pass
    return True, ""


#  Maya's Merge Layers defaults (performAnimLayerMerge.mel, setOptionVars)
MERGE_DEFAULTS = (("animLayerMergeUp", 1), ("animLayerMergeChilds", 0), ("animLayerMergeResultType", 0),
                  ("animLayerMergeDeleteLayers", 1), ("animLayerMergeByTime", 1.0),
                  ("animLayerMergeOversamplingRate", 1), ("animLayerMergeSmartBake", 0),
                  ("animLayerMergeSmartFidelity", 0), ("animLayerMergeSmartFidelityDelta", 5.0))


def _merge_options():
    return dict((name, cmds.optionVar(q=name) if cmds.optionVar(exists=name) else value)
                for name, value in MERGE_DEFAULTS)


def _ordered(root):
    """Every layer from `root` down, depth first (Maya's getAllLayersOrdered)."""
    out = []

    def walk(name):
        out.append(name)
        for child in cmds.animLayer(name, q=True, children=True) or []:
            walk(child)
    walk(root)
    return out


def _maya_merge(layers, root):
    """Maya's own `animLayerMerge` (performAnimLayerMerge.mel, Maya 2027) step for step,
    with one difference: the base is `root`, the layer the panel reads as
    BaseAnimation. Maya's proc knows the base only as the layer with no parent, and a
    scene tab's base (`tab_x:AnimLayerRoot`) has one (2026-10-19: a merge with
    BaseAnimation in a tab baked the base into a new layer and moved the character)."""
    opts = _merge_options()
    #  the base CURVES are Maya's root's: a tab's root holds none of its own
    curves_root = cmds.animLayer(q=True, root=True) or root
    order = _ordered(curves_root)
    layers = [n for n in order if n in set(layers)]
    merging_base = bool(layers) and layers[0] == root
    if merging_base:
        new_base = cmds.animLayer("BaseCopy", override=True)
        if cmds.animLayer(new_base, q=True, parent=True) != root:
            cmds.animLayer(new_base, e=True, parent=root)
        children = [c for c in (cmds.animLayer(root, q=True, children=True) or []) if c != new_base]
        if children:
            cmds.animLayer(new_base, e=True, moveLayerBefore=children[0])
        layers[0] = new_base
    selected = list(layers)
    if opts["animLayerMergeChilds"]:
        everything = _ordered(curves_root)
        out = []
        for name in everything:
            if name in layers and name not in out:
                out.extend(n for n in _ordered(name) if n not in out)
        layers = out
    attributes = sorted(set(a for n in layers for a in (cmds.animLayer(n, q=True, attribute=True) or [])))
    dest = cmds.animLayer("Merged_Layer")
    dest = _named(dest, "Merged_Layer", first=0)
    kind = int(opts["animLayerMergeResultType"]) + 1
    overrides = sum(1 for n in layers if cmds.animLayer(n, q=True, override=True))
    rotations = sum(1 for n in layers if cmds.getAttr(n + ".rotationAccumulationMode"))
    scalings = sum(1 for n in layers if cmds.getAttr(n + ".scaleAccumulationMode"))
    if (kind < 2 and overrides > 0) or kind == 3:
        cmds.animLayer(dest, e=True, override=True)
    cmds.setAttr(dest + ".scaleAccumulationMode", 1 if scalings * 2 >= len(layers) else 0)
    cmds.setAttr(dest + ".rotationAccumulationMode", 1 if rotations * 2 >= len(layers) else 0)
    target = selected[0] if opts["animLayerMergeUp"] else selected[-1]
    cmds.animLayer(dest, e=True, parent=cmds.animLayer(target, q=True, parent=True))
    if opts["animLayerMergeUp"]:
        cmds.animLayer(dest, e=True, moveLayerBefore=target)
    else:
        cmds.animLayer(dest, e=True, moveLayerAfter=target)
    if merging_base:
        for attr in attributes:
            cmds.animLayer(selected[0], e=True, addRelatedKG=False, attribute=attr)
        if opts["animLayerMergeUp"] or not opts["animLayerMergeDeleteLayers"]:
            cmds.animLayer(selected[0], e=True, copyAnimation=curves_root)
        else:
            cmds.animLayer(selected[0], e=True, extractAnimation=curves_root)
    kept = []
    for attr in attributes:
        try:
            ok = cmds.animLayer(dest, e=True, addRelatedKG=False, attribute=attr)
        except Exception:                                    # noqa: BLE001
            ok = None
        if ok is None or ok:
            kept.append(attr)
    if kept:
        cmds.animLayer(dest, e=True, mute=True)
        flags = dict(simulation=False, disableImplicitControl=False,
                     removeBakedAttributeFromLayer=bool(opts["animLayerMergeDeleteLayers"]),
                     destinationLayer=dest, sampleBy=opts["animLayerMergeByTime"],
                     oversamplingRate=int(opts["animLayerMergeOversamplingRate"]),
                     time=(":",), resolveWithoutLayer=layers)
        if opts["animLayerMergeSmartBake"]:
            flags["smart"] = (True, opts["animLayerMergeSmartFidelityDelta"]) \
                if opts["animLayerMergeSmartFidelity"] else True
        cmds.bakeResults(kept, **flags)
        cmds.animLayer(dest, e=True, mute=False)
    if opts["animLayerMergeDeleteLayers"]:
        doomed = list(layers)
        if merging_base and opts["animLayerMergeUp"]:
            cmds.animLayer(curves_root, e=True, extractAnimation=dest)
            doomed.append(dest)
        order = _ordered(curves_root)
        for name in reversed([n for n in order if n in set(doomed)]):
            if not (cmds.animLayer(name, q=True, children=True) or cmds.animLayer(name, q=True, attribute=True)):
                cmds.delete(name)
    else:
        for name in selected:
            cmds.animLayer(name, e=True, mute=True)
        if merging_base:
            cmds.animLayer(curves_root, e=True, extractAnimation=selected[0])
            cmds.delete(selected[0])
    return dest


def merge_selected(names):
    """Maya's Merge Layers on `names` (2026-10-19, «делай все как в стандартной мае»):
    `$gSelectedAnimLayers` set to them and `performAnimLayerMerge 0`, so the animator's
    own Merge Layers options apply and the order is the stack's. BaseAnimation among
    them merges into the base. One undo chunk."""
    root, layers = _anim_names()
    every = [root] + layers if root else []
    names = [n for n in every if n in set(names)]
    if len(names) < 2:
        return False, "select two layers or more to merge (Ctrl-click)"
    import maya.mel as mel
    mel.eval('source "performAnimLayerMerge.mel"')
    before = set(every)
    picked = cmds.ls(selection=True) or []
    with _chunk():
        mel.eval("global string $gSelectedAnimLayers[]; $gSelectedAnimLayers = %s;" % _mel_strings(names))
        _maya_merge(names, root)
        #  Maya's merge ends in `select -cl`; the animator's selection stays
        live = cmds.ls(picked) or []
        if live:
            cmds.select(live, replace=True)
    after = [r["name"] for r in anim_layers()]
    made = [n for n in after if n not in before]
    into = _label(made[0]) if made else ("BaseAnimation" if root in names else "one layer")
    return True, "%s merged into %s" % (", ".join(_label(n) if n != root else "BaseAnimation" for n in names), into)


# -- the lanes: keys of a layer --------------------------------------------------------

def _cells(selection):
    a, b = selection
    return (a, b + 1 - 1e-3)


def set_time(frame):
    """The timeline's own (unrecorded: Maya's slider records no undo step either)."""
    from . import scene
    scene.set_time(frame)


def scrub_only(frame):
    from . import scene
    scene.scrub_only(frame)


def begin_scrub():
    from . import scene
    scene.begin_scrub()


def end_scrub():
    from . import scene
    scene.end_scrub()


def lane_move(names, selection, target):
    """The keys of the selection in the layers `names` inside the highlight
    `selection` moved, or scaled by an edge, onto `target`: the timeline's rule
    (whole frames, a key between frames keeps its place in its cell). One undo step."""
    a, b = selection
    na, nb = target
    if (na, nb) == (a, b):
        return True, ""
    curves = curves_of(names)
    span = _cells(selection)
    curves = [c for c in curves if cmds.keyframe(c, q=True, time=span, keyframeCount=True)]
    if not curves:
        return False, "no keys there"
    with _chunk():
        if b <= a or (nb - na) == (b - a):
            cmds.keyframe(curves, edit=True, time=span, relative=True, timeChange=na - a, option="over")
        else:
            pivot = b if nb == b else a
            factor = float(nb - na) / (b - a)
            cmds.scaleKey(curves, time=span, timeScale=factor, timePivot=pivot)
            far = pivot + (b + 1 - pivot) * factor
            cmds.snapKey(curves, time=(min(na, a) - 0.5, max(nb, b, far) + 0.5), timeMultiple=1)
    return True, ""


def lane_live_begin(names, selection):
    """A key drag on the lanes begins: the timeline's live drag (scene.live_*), on the
    curves of the layers `names` only. True when there are keys to drag."""
    from . import scene
    scene._LIVE.clear()
    span = _cells(selection)
    curves = {}
    for curve in curves_of(names):
        if not cmds.keyframe(curve, q=True, time=span, keyframeCount=True):
            continue
        keys = scene._curve_keys(curve)
        moved = [(t, d) for t, d in keys if look_inside(t, selection)]
        if not moved:
            continue
        start = dict((round(t, 4), (t, d)) for t, d in keys)
        fixed = dict((round(t, 4), (t, d)) for t, d in keys if not look_inside(t, selection))
        curves[curve] = {"start": start, "now": dict(start), "fixed": fixed, "moved": moved, "stamped": set()}
    if not curves:
        return False
    scene._LIVE.update(selection=tuple(selection), target=tuple(selection), curves=curves)
    return True


def look_inside(t, selection):
    from . import look
    return look.inside(t, selection)


def lane_live_to(target):
    from . import scene
    scene.live_to(target)


def lane_live_stamp():
    from . import scene
    return scene.live_stamp()


def lane_live_end(target=None):
    from . import scene
    scene.live_end(target)


def _span(selection, frame):
    return _cells(selection) if selection else (frame, frame)


def lane_keys(op, names, selection, frame, kind=None):
    """A key-menu row on the lanes `names`: op in cut / copy / paste / delete /
    tangents / snap / breakdown, over the highlight (else the frame)."""
    curves = curves_of(names)
    if not curves:
        return False, "the selection has no keys in %s" % ", ".join(_label(n) for n in names)
    span = _span(selection, frame)
    with _chunk():
        if op == "cut":
            cmds.cutKey(curves, time=span, option="keys")
        elif op == "copy":
            cmds.copyKey(curves, time=span, option="keys")
        elif op == "paste":
            cmds.pasteKey(curves, time=(span[0],), option="merge")
        elif op == "delete":
            cmds.cutKey(curves, time=span, clear=True)
        elif op == "snap":
            cmds.snapKey(curves, time=span, timeMultiple=1)
        elif op == "breakdown":
            cmds.keyframe(curves, edit=True, time=span, breakdown=True)
        elif op == "tangents":
            if kind == "step":
                cmds.keyTangent(curves, time=span, outTangentType="step")
            else:
                cmds.keyTangent(curves, time=span, inTangentType=kind, outTangentType=kind)
        else:
            return False, "no such key command: %s" % op
    return True, ""


def lane_set_key(name):
    """A key at the current frame on layer `name` for the selection's channels in it
    (on BaseAnimation: their keyable channels)."""
    nodes = _selected_nodes()
    if not nodes:
        return False, "nothing selected"
    root, _layers = _anim_names()
    if name == root:
        plugs = ["%s.%s" % (n, a) for n in sorted(nodes) for a in (cmds.listAttr(n, keyable=True) or [])]
    else:
        plugs = [p for p in (cmds.animLayer(name, q=True, attribute=True) or []) if p.split(".")[0] in nodes]
    if not plugs:
        return False, "the selection is not in %s" % _label(name)
    with _chunk():
        cmds.setKeyframe(plugs, animLayer=_maya_root(root) if name == root else name)
    return True, ""


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
