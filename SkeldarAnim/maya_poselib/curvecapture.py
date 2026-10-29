"""The Pose Library's ORIGINAL curves read off the scene (2026-10-28): every curve of a card's
channels, layer by layer - what `animcapture.build_clip` writes into `curves.json.gz` (a
character's controls or joints) and into an objects card's layered channels. The rules of the
data are `curvedata`'s.

The animator: «...сохранения по слоям и сохранения ключей». Which channels:
- a rig's ControlSet controls whose bones (`scene._control_bones`, the rule a selected control
  follows) meet the card's members - `Main` (the whole body) only with a whole-body card; a
  skeleton's member joints (`character_nodes`);
- each keyable unlocked scalar channel (`objects.channel_names`); per layer, bottom to top
  (`stack`: the root as `curvedata.BASE`, a scene tab's root left out), the curve
  `keys.curve_for` answers - a layer above the base asked only for the plugs it holds
  (`keys.layer_plugs`, one query a layer), so another character's layers never enter the card -
  read by the caller's `copy` (`animcapture._copied`: a duplicate cut to the range with a
  shape-keeping key at each end) plus its infinity; a channel nothing feeds a `{"static": v}` on
  the base; a channel a constraint, an expression or a driven key feeds holds no curve of its own
  and is named (`driven_note`) - the bones' frames still carry what it did.

The caller holds the undo queue off (the duplicates are made and deleted).

Spec: docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md
"""

from collections import OrderedDict

import maya.cmds as cmds

from maya_poselib import curvedata
from maya_poselib import keys
from maya_poselib import objects as objs
from maya_poselib import scene

DRIVEN = "%s driven - no curve of theirs kept (%s)"


def _named(leaf, bones):
    """What a control names: its bones, or `curvedata.WHOLE` (`scene._control_bones`). A seam."""
    named = scene._control_bones(leaf, bones)
    return curvedata.WHOLE if named == scene._WHOLE else named


def character_nodes(ref, bones, members):
    """The long paths whose channels a character card keeps as curves: a rig's controls whose
    bones meet `members` (`curvedata.keeps_control`; the card is the whole body when its members
    hold every bone `scene.whole_body` names), a skeleton's member joints in skeleton order."""
    if ref.kind == "rig" and ref.rig is not None:
        found = cmds.sets(ref.rig.control_set, query=True) or []
        controls = (cmds.ls(found, long=True) or []) if found else []
        whole = set(scene.whole_body(bones)) <= set(members or ())
        return [path for path in controls
                if curvedata.keeps_control(_named(scene.leaf(path), bones), members, whole)]
    return [bones[name]["path"] for name in bones
            if name in set(members or ()) and bones[name].get("path")]


def stack():
    """[(the scene's layer name, its card record)] bottom to top - the root first as
    `curvedata.BASE`; [(None, the base)] in a scene without layers (the plain curves are the
    base)."""
    names = keys.layer_stack()
    if not names:
        return [(None, curvedata.layer_record(curvedata.BASE, base=True))]
    return [(name, keys.layer_record(name, base=(index == 0))) for index, name in enumerate(names)]


def _infinity(curve):
    """{"pre", "post"} of `curve` in `setInfinity`'s spelling, {} when they cannot be read."""
    try:
        pre = int(cmds.getAttr(curve + ".preInfinity"))
        post = int(cmds.getAttr(curve + ".postInfinity"))
    except (RuntimeError, ValueError, TypeError):
        return {}
    return {"pre": keys._INFINITY.get(pre, "constant"), "post": keys._INFINITY.get(post, "constant")}


def _number(value):
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def channel_curves(plugs, start, end, copy, layers):
    """(OrderedDict {plug: {card layer: CURVE}}, [driven plugs]) of `plugs` over [start, end] on
    `layers` (`stack()`'s answer, read once by the caller). A plug no layer holds a curve for
    and nothing feeds is `{"static": v}` on the base; a missing plug, or one that answers no
    number, is left out."""
    holds = dict((name, keys.layer_plugs(name)) for name, _record in layers[1:])
    out, driven = OrderedDict(), []
    for plug in plugs:
        kind, _node = keys.feed_of(plug)
        if kind == "missing":
            continue
        if kind == "driven":
            driven.append(plug)
            continue
        per = OrderedDict()
        for index, (name, record) in enumerate(layers):
            if index and plug not in holds.get(name, ()):
                continue
            curve = keys.curve_for(plug, name)
            if curve is None:
                continue
            found = dict(copy(curve, start, end))
            found.update(_infinity(curve))
            per[record["name"]] = found
        if not per:
            try:
                value = _number(cmds.getAttr(plug))
            except (RuntimeError, ValueError, TypeError):
                value = None
            if value is None:
                continue
            per[curvedata.BASE] = {"static": value}
        out[plug] = per
    return out, driven


def node_curves(nodes, start, end, copy, layers):
    """([{"name": leaf, "attrs": {attr: {card layer: CURVE}}}], [driven plugs]) of `nodes`' keyable
    channels (`objects.channel_names`), in `nodes`' order; a node with no channel left out."""
    plugs, owner = [], {}
    for path in nodes or ():
        for attr in objs.channel_names(path, cmds):
            plug = path + "." + attr
            plugs.append(plug)
            owner[plug] = (path, attr)
    found, driven = channel_curves(plugs, start, end, copy, layers)
    by_node = OrderedDict()
    for plug, per in found.items():
        path, attr = owner[plug]
        by_node.setdefault(path, OrderedDict())[attr] = dict(per)
    return [{"name": scene.leaf(path), "attrs": dict(attrs)} for path, attrs in by_node.items()], \
        driven


def used_records(layers, per_layer_dicts):
    """The card's layer records: the base first, then every layer some {card layer: CURVE} of
    `per_layer_dicts` names, in stack order."""
    used = set(name for per in per_layer_dicts for name in per)
    return [layers[0][1]] + [record for _name, record in layers[1:] if record["name"] in used]


def driven_note(driven):
    """The save line's note on the channels kept without curves, "" when there are none."""
    if not driven:
        return ""
    count = len(driven)
    shown = ", ".join(scene.leaf(plug.rsplit(".", 1)[0]) + "." + plug.rsplit(".", 1)[1]
                      for plug in driven[:keys.NAMED])
    if count > keys.NAMED:
        shown += " and %d more" % (count - keys.NAMED)
    return DRIVEN % ("%d channel%s" % (count, "" if count == 1 else "s"), shown)
