"""Which curves the overlay draws, and their shape.

Thin over `maya.cmds` on purpose: the policy that is worth testing is the
channel-box rule and it is three lines, while everything geometric lives in
`mapping.py`.

`cmds` is held as a module attribute so a test can rebind it
(`curves.cmds = fake`) and put it back. Never re-import to swap it: the
stale module stays bound as an attribute of the parent package and the next
`from maya_curveview import curves` hands the old object back.
"""

from collections import namedtuple

import maya.cmds as cmds

_real_cmds = cmds

# plug: "ctrl.translateX";  curve: the animCurve NODE, never the plug.
Curve = namedtuple("Curve", "plug node attribute curve keys")

CHANNEL_BOX = "mainChannelBox"


# ------------------------------------------------------------- the selection

def _scene_selection():
    return cmds.ls(selection=True, long=True) or []


def _channel_box_selection():
    """What the animator has picked in the channel box, or [].

    Guarded: the control does not exist in a headless session, and a tool
    must not die of a missing panel.
    """
    try:
        chosen = cmds.channelBox(CHANNEL_BOX, query=True,
                                 selectedMainAttributes=True)
    except Exception:
        return []
    return list(chosen or [])


def curve_of(plug):
    """The animCurve driving `plug`, or None."""
    found = cmds.listConnections(plug, source=True, destination=False,
                                 type="animCurve") or []
    return found[0] if found else None


def channel_attributes(node):
    """The channel-box rule for one node.

    The animator's own words: selected channels of the selected objects, and
    every animated channel when nothing is picked in the channel box. The
    channel box answers attribute NAMES with no owner, so the answer is
    intersected with what this node actually has animated -- otherwise a
    second selected control borrows the first one's channels.
    """
    animated = [attribute
                for attribute in (cmds.listAttr(node, keyable=True) or [])
                if curve_of("{0}.{1}".format(node, attribute))]
    chosen = _channel_box_selection()
    if chosen:
        return [attribute for attribute in chosen if attribute in animated]
    return animated


def visible_curves(selection=None):
    """Every curve the overlay should draw right now.

    No selection means no curves at all -- the animator's rule («если у нас
    не выделен объект то и кривые его рисовать не нужно»), which is also
    what makes the mode cheap to leave switched on.
    """
    nodes = list(selection) if selection is not None else _scene_selection()
    found = []
    for node in nodes:
        for attribute in channel_attributes(node):
            plug = "{0}.{1}".format(node, attribute)
            curve = curve_of(plug)
            if not curve:
                continue
            found.append(Curve(plug, node, attribute, curve, keys_of(curve)))
    return found


# ------------------------------------------------------------------ the keys

def keys_of(curve):
    """[(time, value)] for every key on the curve, in curve order."""
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    values = cmds.keyframe(curve, query=True, valueChange=True) or []
    return [(float(t), float(v)) for t, v in zip(times, values)]


def selected_indices(curve):
    """Positions of the keys Maya has SELECTED on `curve`.

    Maya's own key selection, deliberately, rather than a private set of
    ours. Three things fall out for free: a key picked in the overlay is
    picked in the Graph Editor too, `cmds.keyframe` can move "the selected
    keys" with no list to pass, and undo needs no bookkeeping.

    Matched on time rounded to six places -- a key can sit on a fraction,
    and comparing floats straight would drop it.
    """
    chosen = cmds.keyframe(curve, query=True, selected=True,
                           timeChange=True) or []
    if not chosen:
        return []
    wanted = set(round(float(t), 6) for t in chosen)
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    return [index for index, time in enumerate(times)
            if round(float(time), 6) in wanted]


def tangent_angles(curve, indices):
    """{index: (in_angle, out_angle)} in degrees, for those keys only.

    Asked for selected keys alone: handles are drawn only there, and this is
    two calls into Maya per key.
    """
    angles = {}
    for index in indices:
        pair = []
        for flag in ("inAngle", "outAngle"):
            answer = cmds.keyTangent(curve, query=True, index=(index, index),
                                     **{flag: True}) or [0.0]
            pair.append(float(answer[0]))
        angles[index] = (pair[0], pair[1])
    return angles


# ------------------------------------------------------------- the sampling

def sample(curve, t0, t1, count):
    """`count` points along the curve, evenly in time.

    Evaluates the animCURVE NODE, never the driven plug: a plug sample pulls
    a whole rig evaluation, and on the animator's scene that is 10 fps per
    sample. The curve answers by itself and touches no rig, so this stays
    cheap enough to run per repaint.
    """
    count = max(int(count), 1)
    if count == 1:
        times = [float(t0)]
    else:
        step = (float(t1) - float(t0)) / (count - 1)
        times = [float(t0) + step * index for index in range(count)]
    points = []
    for time in times:
        value = cmds.keyframe(curve, query=True, eval=True,
                              time=(time, time))
        if value:
            points.append((time, float(value[0])))
    return points


def time_range():
    """The playback range, which is the overlay's whole X axis."""
    return (float(cmds.playbackOptions(query=True, min=True)),
            float(cmds.playbackOptions(query=True, max=True)))
