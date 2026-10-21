"""The AT bar's tools (2026-10-21): animBot's keys, blend sliders, pose and animation clipboard, mirror,
xform, space switch, temp controls and pivot, trails, bookmarks and anim recovery, native."""
import datetime
import glob
import json
import math
import os
import re
from functools import wraps

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

ANIM_CURVE_TYPES = ["animCurveTL", "animCurveTA", "animCurveTU", "animCurveTT"]
DATA_NODE = "AT_data"
TEMP_GRP = "AT_TEMP"
TRAIL_GRP = "AT_MOTION_TRAILS"
SELSET_PREFIX = "AT_sel_"
TRANSFORM_ATTRS = ("tx", "ty", "tz", "rx", "ry", "rz")

_state = {"suspended": False}


# ---------------------------------------------------------------- helpers

def undoable(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(openChunk=True, chunkName="AT_" + fn.__name__)
        try:
            return fn(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrapper


def message(text):
    cmds.inViewMessage(amg="<hl>AT</hl>&nbsp;&nbsp;" + text, pos="botCenter", fade=True, fst=800, fot=200)


def warn(text):
    cmds.warning("AT: " + text)


def selection():
    return cmds.ls(sl=True, long=True, type="transform") or []


def strip_ns(name):
    return name.split("|")[-1].split(":")[-1]


def current_time():
    return cmds.currentTime(q=True)


def time_range():
    """Highlighted time-slider range if any, else the playback range."""
    slider = mel.eval("$t=$gPlayBackSlider")
    if cmds.timeControl(slider, q=True, rangeVisible=True):
        a, b = cmds.timeControl(slider, q=True, rangeArray=True)
        return a, b - 1
    return cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True)


def channelbox_attrs():
    cb = mel.eval("$t=$gChannelBoxName")
    attrs = []
    for flag in ("sma", "ssa", "sha", "soa"):
        attrs += cmds.channelBox(cb, q=True, **{flag: True}) or []
    return attrs


def graph_editor_visible():
    return "graphEditor1" in (cmds.getPanel(vis=True) or [])


def anim_curves(nodes_or_plugs):
    curves = []
    for item in nodes_or_plugs:
        curves += cmds.keyframe(item, q=True, name=True) or []
    curves = cmds.ls(list(dict.fromkeys(curves)), type=ANIM_CURVE_TYPES) or []
    return curves


def node_curves(node, attrs=None):
    if attrs:
        plugs = ["%s.%s" % (node, a) for a in attrs if cmds.attributeQuery(a, node=node, exists=True)]
        return anim_curves(plugs)
    return anim_curves([node])


def selected_curves():
    attrs = channelbox_attrs()
    curves = []
    for node in selection():
        curves += node_curves(node, attrs)
    return list(dict.fromkeys(curves))


def scene_curves():
    return cmds.ls(type=ANIM_CURVE_TYPES) or []


def driven_plug(curve):
    cons = cmds.listConnections(curve + ".output", s=False, d=True, plugs=True, skipConversionNodes=True) or []
    return cons[0] if cons else None


def is_animated(node):
    return bool(cmds.keyframe(node, q=True, keyframeCount=True))


def keyable_attrs(node):
    attrs = []
    for a in cmds.listAttr(node, keyable=True, unlocked=True, scalar=True) or []:
        plug = "%s.%s" % (node, a)
        try:
            if cmds.getAttr(plug, settable=True):
                attrs.append(a)
        except (RuntimeError, ValueError):
            pass
    return attrs


def free_transform_attrs(node):
    return [a for a in TRANSFORM_ATTRS
            if cmds.getAttr("%s.%s" % (node, a), keyable=True) and cmds.getAttr("%s.%s" % (node, a), settable=True)]


def key_transform(node, t=None, force=False, channels="tr"):
    if not (force or is_animated(node) or cmds.autoKeyframe(q=True, state=True)):
        return
    attrs = [a for a in free_transform_attrs(node) if a[0] in channels]
    if attrs:
        if t is None:
            cmds.setKeyframe(node, attribute=attrs)
        else:
            cmds.setKeyframe(node, attribute=attrs, t=t)


def key_times(nodes):
    times = set()
    for n in nodes:
        times.update(cmds.keyframe(n, q=True, tc=True) or [])
    return sorted(times)


def world_matrix(node, t=None):
    if t is None:
        return cmds.getAttr(node + ".worldMatrix[0]")
    return cmds.getAttr(node + ".worldMatrix[0]", time=t)


def set_world_matrix(node, m, channels="tr"):
    """channels: "tr", "t" or "r" - the other transform channels (and scale) keep their local values."""
    keep = [a for a in TRANSFORM_ATTRS + ("sx", "sy", "sz") if a[0] not in channels]
    saved = {a: cmds.getAttr("%s.%s" % (node, a)) for a in keep} if channels != "tr" else {}
    cmds.xform(node, ws=True, matrix=m)
    for a, v in saved.items():
        if cmds.getAttr("%s.%s" % (node, a), settable=True):
            cmds.setAttr("%s.%s" % (node, a), v)


def run_at_times(times, fn):
    """Call fn(t) with the scene evaluated at each time; viewport refresh suspended meanwhile."""
    ct = current_time()
    cmds.refresh(suspend=True)
    try:
        for t in times:
            cmds.currentTime(t, update=True)
            fn(t)
    finally:
        cmds.currentTime(ct, update=True)
        cmds.refresh(suspend=_state["suspended"])


def mmul(a, b):
    return list(om.MMatrix(a) * om.MMatrix(b))


def minv(a):
    return list(om.MMatrix(a).inverse())


# ---------------------------------------------------------------- scene data (default pose snapshot)

def _data_node():
    if not cmds.objExists(DATA_NODE):
        cmds.createNode("network", name=DATA_NODE, skipSelect=True)
    if not cmds.attributeQuery("defaultPose", node=DATA_NODE, exists=True):
        cmds.addAttr(DATA_NODE, longName="defaultPose", dataType="string")
        cmds.setAttr(DATA_NODE + ".defaultPose", "{}", type="string")
    return DATA_NODE


def _load_snapshot():
    if not cmds.objExists(DATA_NODE) or not cmds.attributeQuery("defaultPose", node=DATA_NODE, exists=True):
        return {}
    try:
        return json.loads(cmds.getAttr(DATA_NODE + ".defaultPose") or "{}")
    except ValueError:
        return {}


def _save_snapshot(data):
    cmds.setAttr(_data_node() + ".defaultPose", json.dumps(data), type="string")


def snapshot_value(node, attr):
    long_attr = cmds.attributeQuery(attr, node=node, longName=True)
    return _load_snapshot().get(strip_ns(node), {}).get(long_attr)


@undoable
def snapshot_default_pose():
    sel = selection()
    if not sel:
        return warn("select controls to snapshot as the default pose")
    data = _load_snapshot()
    for node in sel:
        data[strip_ns(node)] = {cmds.attributeQuery(a, node=node, longName=True): cmds.getAttr("%s.%s" % (node, a))
                                for a in keyable_attrs(node)}
    _save_snapshot(data)
    message("default pose snapshot: %d controls" % len(sel))


@undoable
def reset_to_default_pose():
    for node in selection():
        for a in keyable_attrs(node):
            d = default_value("%s.%s" % (node, a))
            if d is not None:
                cmds.setAttr("%s.%s" % (node, a), d)
        if is_animated(node) or cmds.autoKeyframe(q=True, state=True):
            cmds.setKeyframe(node, attribute=keyable_attrs(node))


def clear_default_pose():
    if cmds.objExists(DATA_NODE):
        _save_snapshot({})
    message("default pose snapshot cleared")


def default_value(plug):
    node, attr = plug.split(".", 1)
    try:
        snap = snapshot_value(node, attr)
    except RuntimeError:
        snap = None
    if snap is not None:
        return snap
    try:
        d = cmds.attributeQuery(attr, node=node, listDefault=True)[0]
    except (RuntimeError, IndexError, TypeError):
        return None
    if cmds.getAttr(plug, type=True) == "doubleAngle":
        d = om.MAngle(d).asUnits(om.MAngle.uiUnit())
    return d


# ---------------------------------------------------------------- nudge / inbetweens

@undoable
def nudge(frames):
    """Every key of the selected controls (the channels picked in the Channel Box, else all) moved
    `frames` along the timeline."""
    if not frames:
        return
    curves = selected_curves()
    if not curves:
        return warn("select animated controls")
    moved = 0
    for c in curves:
        try:
            cmds.keyframe(c, e=True, relative=True, timeChange=frames, option="over")
            moved += 1
        except RuntimeError:
            pass
    message("%d curves moved %+d frames" % (moved, frames))


@undoable
def inbetween(frames, scene=False):
    """Insert (frames > 0) or remove (frames < 0) that many frames after the current time, on the
    selected controls or on every curve in the scene. Every curve moves by the same amount, so a removal
    stops at the first key it would run into - the channels stay in sync."""
    if not frames:
        return
    ct = current_time()
    curves = scene_curves() if scene else selected_curves()
    if not curves:
        return warn("nothing animated in the scene" if scene else "select animated controls")
    spans = []
    for c in curves:
        after = [t for t in cmds.keyframe(c, q=True, tc=True) or [] if t > ct]
        if after:
            spans.append((c, min(after), max(after)))
    if not spans:
        return warn("no keys after frame %g" % ct)
    shift = frames
    if frames < 0:
        room = int(math.floor(min(first for _c, first, _l in spans) - ct - 1))
        if room <= 0:
            return warn("no empty frames right after frame %g to remove" % ct)
        shift = -min(-frames, room)
    for c, first, last in spans:
        try:
            cmds.keyframe(c, e=True, t=(first, last), relative=True, timeChange=shift, option="over")
        except RuntimeError:
            pass
    where = "the scene" if scene else "%d curves" % len(spans)
    text = "%s %d frame(s) after frame %g in %s" % ("inserted" if shift > 0 else "removed", abs(shift), ct, where)
    if shift != frames:
        text += " (only %d empty)" % abs(shift)
    message(text)


# ---------------------------------------------------------------- sliders

def smoothed(values, passes=3):
    """Each key's value under a 1-2-1 filter run `passes` times (about a Gaussian over a few keys);
    the ends repeat themselves. A neighbours-only average flips alternating noise instead of removing it."""
    out = list(values)
    last = len(out) - 1
    for _ in range(passes):
        out = [(out[max(i - 1, 0)] + 2.0 * out[i] + out[min(i + 1, last)]) / 4.0 for i in range(len(out))]
    return out


SM_PASSES_AT_100 = 4      # the smoothing widens pass by pass as the slider goes left
SM_MAX_PASSES = 6         # -150%
SM_ROUGH_PASSES = 3       # what the right side pushes away from


def smoothing_levels(values, passes=SM_MAX_PASSES):
    """[values, 1 pass, 2 passes, ...]: the curve smoothed a little more at each level."""
    levels = [list(values)]
    for _ in range(passes):
        levels.append(smoothed(levels[-1], 1))
    return levels


def smooth_at(levels, p):
    """A key's value at slider `p` (< 0) from its levels: -p * SM_PASSES_AT_100 passes, fractions blended."""
    x = min(-p * SM_PASSES_AT_100, len(levels) - 1)
    k = int(x)
    hi = levels[min(k + 1, len(levels) - 1)]
    return levels[k] + (hi - levels[k]) * (x - k)


class SliderSession(object):
    """One drag / click of a blend slider: collects the target keys once and re-applies from the originals."""

    def __init__(self, mode):
        self.mode = mode
        self.keys = []
        self.statics = []
        self.tangents = {}            # SM: {curve: {index: (itt, ott, ia, oa, lock)}} as they were
        self.tangents_aligned = False
        cmds.undoInfo(openChunk=True, chunkName="AT_slider_" + mode)
        try:
            self._collect()
        except Exception:
            cmds.undoInfo(closeChunk=True)
            raise

    def _collect(self):
        sel_curves = cmds.keyframe(q=True, sl=True, name=True) if graph_editor_visible() else None
        if sel_curves:
            for c in cmds.ls(sel_curves, type=ANIM_CURVE_TYPES) or []:
                idx = sorted(int(i) for i in cmds.keyframe(c, q=True, sl=True, indexValue=True) or [])
                self._add_curve(c, idx)
            return
        ct = current_time()
        attrs = channelbox_attrs()
        for node in selection():
            for c in node_curves(node, attrs):
                if not cmds.keyframe(c, q=True, t=(ct, ct), keyframeCount=True):
                    cmds.setKeyframe(c, t=ct, insert=True)
                idx = cmds.keyframe(c, q=True, t=(ct, ct), indexValue=True)
                if idx:
                    self._add_curve(c, [int(idx[0])])
            if self.mode == "BD":
                self._add_statics(node, attrs)

    def _add_curve(self, curve, idx):
        vals = cmds.keyframe(curve, q=True, valueChange=True) or []
        default = None
        if self.mode == "BD":
            plug = driven_plug(curve)
            default = default_value(plug) if plug else None
            if default is None:
                return
        n, sel = len(vals), set(idx)
        levels = smoothing_levels(vals) if self.mode == "SM" else None
        if levels:
            self._remember_tangents(curve, idx)
        for i in idx:
            lo = hi = i
            while lo - 1 in sel:
                lo -= 1
            while hi + 1 in sel:
                hi += 1
            self.keys.append((curve, i, vals[i],
                              vals[lo - 1] if lo > 0 else None, vals[hi + 1] if hi + 1 < n else None,
                              [level[i] for level in levels] if levels else None, default))

    def _remember_tangents(self, curve, idx):
        q = dict(q=True)
        columns = [cmds.keyTangent(curve, itt=True, **q), cmds.keyTangent(curve, ott=True, **q),
                   cmds.keyTangent(curve, ia=True, **q), cmds.keyTangent(curve, oa=True, **q),
                   cmds.keyTangent(curve, lock=True, **q)]
        self.tangents[curve] = dict((i, tuple(col[i] for col in columns)) for i in idx)

    def _align_tangents(self, on):
        """Smoothing: the keys' tangents set to Auto - in and out aligned, following the new values without
        overshooting. Back to 0 or onto the rough side: the tangents they had. The lock is never touched:
        Maya's undo of a keyTangent edit with -lock leaves the lock off (measured in 2027)."""
        if on == self.tangents_aligned:
            return
        self.tangents_aligned = on
        for curve, keys in self.tangents.items():
            if on:
                cmds.keyTangent(curve, e=True, index=[(i, i) for i in keys], itt="auto", ott="auto")
                continue
            for i, (itt, ott, ia, oa, _lock) in keys.items():
                at = (i, i)
                try:
                    cmds.keyTangent(curve, e=True, index=at, itt=itt, ott=ott)
                    if itt == "fixed":
                        cmds.keyTangent(curve, e=True, index=at, ia=ia)
                    if ott == "fixed":
                        cmds.keyTangent(curve, e=True, index=at, oa=oa)
                except RuntimeError:
                    pass

    def _add_statics(self, node, attrs):
        for a in attrs or keyable_attrs(node):
            plug = "%s.%s" % (node, a)
            if not cmds.objExists(plug) or cmds.listConnections(plug, s=True, d=False):
                continue
            try:
                if not cmds.getAttr(plug, settable=True):
                    continue
                v0 = cmds.getAttr(plug)
            except (RuntimeError, ValueError):
                continue
            d = default_value(plug)
            if d is not None and isinstance(v0, (int, float)):
                self.statics.append((plug, v0, d))

    def _target(self, v0, prev, nxt, smooth, d, p):
        if self.mode == "TW":
            if prev is None and nxt is None:
                return None
            prev = v0 if prev is None else prev
            nxt = v0 if nxt is None else nxt
            return prev + (nxt - prev) * (p + 1.0) / 2.0
        if self.mode == "BN":
            other = nxt if p >= 0 else prev
            return v0 + ((v0 if other is None else other) - v0) * abs(p)
        if self.mode == "BD":
            return v0 + (d - v0) * p
        if self.mode == "SM":
            if p < 0:
                return smooth_at(smooth, p)
            return v0 - (smooth[SM_ROUGH_PASSES] - v0) * p
        return None

    def apply(self, pct):
        p = pct / 100.0
        if self.mode == "SM":
            self._align_tangents(p < 0)
        for c, i, v0, prev, nxt, smooth, d in self.keys:
            v = self._target(v0, prev, nxt, smooth, d, p)
            if v is not None:
                cmds.keyframe(c, e=True, index=(i, i), absolute=True, valueChange=v)
        for plug, v0, d in self.statics:
            cmds.setAttr(plug, v0 + (d - v0) * p)

    def finish(self):
        cmds.undoInfo(closeChunk=True)


# ---------------------------------------------------------------- pose / animation clipboard

_clip = {"pose": None, "anim": None, "world": None, "rel": None}


def _match_clip(clip_items, nodes):
    """Pair target nodes with clipboard entries by namespace-less name, falling back to selection order."""
    by_name = {k: v for k, v in clip_items}
    pairs = []
    for i, node in enumerate(nodes):
        data = by_name.get(strip_ns(node))
        if data is None and len(clip_items) == len(nodes):
            data = clip_items[i][1]
        elif data is None and len(clip_items) == 1:
            data = clip_items[0][1]
        if data is not None:
            pairs.append((node, data))
    return pairs


def copy_pose():
    sel = selection()
    if not sel:
        return warn("select controls to copy the pose from")
    _clip["pose"] = [(strip_ns(n), {a: cmds.getAttr("%s.%s" % (n, a)) for a in keyable_attrs(n)}) for n in sel]
    message("pose copied: %d controls" % len(sel))


@undoable
def paste_pose():
    if not _clip["pose"]:
        return warn("copy a pose first")
    for node, data in _match_clip(_clip["pose"], selection()):
        attrs = [a for a in data if cmds.attributeQuery(a, node=node, exists=True)]
        for a in attrs:
            try:
                cmds.setAttr("%s.%s" % (node, a), data[a])
            except RuntimeError:
                pass
        if attrs and (is_animated(node) or cmds.autoKeyframe(q=True, state=True)):
            cmds.setKeyframe(node, attribute=attrs)


def _curve_data(curve):
    q = {"q": True}
    return {
        "times": cmds.keyframe(curve, tc=True, **q),
        "values": cmds.keyframe(curve, vc=True, **q),
        "itt": cmds.keyTangent(curve, itt=True, **q), "ott": cmds.keyTangent(curve, ott=True, **q),
        "ia": cmds.keyTangent(curve, ia=True, **q), "oa": cmds.keyTangent(curve, oa=True, **q),
        "iw": cmds.keyTangent(curve, iw=True, **q), "ow": cmds.keyTangent(curve, ow=True, **q),
        "lock": cmds.keyTangent(curve, lock=True, **q),
        "weighted": cmds.keyTangent(curve, weightedTangents=True, **q)[0],
        "pre": cmds.getAttr(curve + ".preInfinity"), "post": cmds.getAttr(curve + ".postInfinity"),
    }


def copy_animation():
    sel = selection()
    if not sel:
        return warn("select animated controls")
    items = []
    for n in sel:
        attrs = {}
        for c in node_curves(n):
            plug = driven_plug(c)
            if plug:
                attrs[plug.split(".", 1)[1]] = _curve_data(c)
        items.append((strip_ns(n), attrs))
    _clip["anim"] = items
    message("animation copied: %d controls" % len(sel))


PASTE_MODES = ("current", "insert", "original")


def _make_room(plug, at, length):
    """Keys of `plug` at or after `at` pushed `length` frames later (paste insert)."""
    after = [t for t in cmds.keyframe(plug, q=True, tc=True) or [] if t >= at]
    if after:
        cmds.keyframe(plug, e=True, time=(min(after), max(after)), relative=True, timeChange=length,
                      option="over")


def _paste_tangents(curve, d, offset, weights):
    """The copied tangents onto the pasted keys. The lock is set only to break a key that was broken (Maya's
    undo of a -lock edit leaves the lock off)."""
    for i, t in enumerate(d["times"]):
        at = (t + offset, t + offset)
        kwargs = dict(itt=d["itt"][i], ott=d["ott"][i])
        if d["itt"][i] == "fixed":
            kwargs["ia"] = d["ia"][i]
        if d["ott"][i] == "fixed":
            kwargs["oa"] = d["oa"][i]
        if weights:
            kwargs.update(iw=d["iw"][i], ow=d["ow"][i])
        try:
            if not d["lock"][i]:
                cmds.keyTangent(curve, e=True, time=at, lock=False)
            cmds.keyTangent(curve, e=True, time=at, **kwargs)
        except RuntimeError:
            pass


@undoable
def paste_animation(mode="current"):
    """current: from the current frame, keys inside the pasted span replaced, the rest kept (animBot's
    paste); insert: from the current frame, later keys pushed after the pasted span; original: each
    curve replaced whole, at the frames it was copied from."""
    if not _clip["anim"]:
        return warn("copy animation first")
    pairs = _match_clip(_clip["anim"], selection())
    if not pairs:
        return warn("no selected control matches the copied ones (by name, or by selection order)")
    times = [t for _n, attrs in _clip["anim"] for d in attrs.values() for t in d["times"]]
    if not times:
        return warn("the copied controls had no keys")
    first, last = min(times), max(times)
    offset = 0.0 if mode == "original" else current_time() - first
    pasted = set()
    for node, attrs in pairs:
        for attr, d in attrs.items():
            plug = "%s.%s" % (node, attr)
            if not d["times"] or not cmds.objExists(plug):
                continue
            keyed = cmds.keyframe(plug, q=True, name=True)
            if not keyed and not cmds.getAttr(plug, settable=True):
                continue
            if keyed and mode == "original":
                cmds.cutKey(plug, clear=True)
            elif keyed and mode == "insert":
                _make_room(plug, first + offset, last - first + 1)
            elif keyed:
                cmds.cutKey(plug, time=(first + offset, last + offset), clear=True)
            for t, v in zip(d["times"], d["values"]):
                cmds.setKeyframe(plug, t=t + offset, v=v)
            curve = (cmds.keyframe(plug, q=True, name=True) or [None])[0]
            if not curve:
                continue
            if mode == "original" or not keyed:
                cmds.keyTangent(curve, e=True, weightedTangents=d["weighted"])
            weighted = cmds.keyTangent(curve, q=True, weightedTangents=True)[0]
            _paste_tangents(curve, d, offset, weighted and d["weighted"])
            if mode == "original" or not keyed:
                cmds.setAttr(curve + ".preInfinity", d["pre"])
                cmds.setAttr(curve + ".postInfinity", d["post"])
            pasted.add(node)
    where = "at the copied frames" if mode == "original" else "at frame %g" % (first + offset)
    message("animation pasted onto %d controls %s" % (len(pasted), where))


# ---------------------------------------------------------------- mirror

_SIDE_RULES = [
    (r"(?<![A-Za-z])L(?=[_\d]|$)", "L", "R"),
    (r"(?<![A-Za-z])R(?=[_\d]|$)", "R", "L"),
    (r"(?<![A-Za-z])l(?=[_\d]|$)", "l", "r"),
    (r"(?<![A-Za-z])r(?=[_\d]|$)", "r", "l"),
    (r"Left", "Left", "Right"), (r"Right", "Right", "Left"),
    (r"left", "left", "right"), (r"right", "right", "left"),
    (r"(?<![A-Za-z])Lf(?![a-z])", "Lf", "Rt"), (r"(?<![A-Za-z])Rt(?![a-z])", "Rt", "Lf"),
    (r"(?<![A-Za-z])lf(?![a-z])", "lf", "rt"), (r"(?<![A-Za-z])rt(?![a-z])", "rt", "lf"),
]


def opposite(node):
    path, short = node.rsplit("|", 1) if "|" in node else ("", node)
    ns, base = short.rsplit(":", 1) if ":" in short else ("", short)
    for pattern, _, repl in _SIDE_RULES:
        for m in re.finditer(pattern, base):
            cand = base[:m.start()] + repl + base[m.end():]
            full = (ns + ":" if ns else "") + cand
            found = cmds.ls(full, long=True, type="transform") or []
            if found:
                return found[0]
    return None


_MIRROR = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])


def _rotation3(node):
    m = om.MMatrix(cmds.getAttr(node + ".parentMatrix[0]"))
    if cmds.nodeType(node) == "joint":
        jo = [math.radians(v) for v in cmds.getAttr(node + ".jointOrient")[0]]
        m = om.MEulerRotation(*jo).asMatrix() * m
    return m


def _axis_signs(src, dst):
    """Per-axis sign that maps src's local channels onto dst after a world YZ-plane mirror."""
    a = _rotation3(src) * _MIRROR * _rotation3(dst).inverse()
    diag = [a.getElement(i, i) for i in range(3)]
    if any(abs(d) < 0.95 for d in diag):
        return None
    t = [1 if d > 0 else -1 for d in diag]
    det = t[0] * t[1] * t[2]
    return t, [s * det for s in t]


def _mirrored_values(src, dst):
    vals = {a: cmds.getAttr("%s.%s" % (src, a)) for a in keyable_attrs(src)}
    signs = _axis_signs(src, dst)
    if signs:
        tsign, rsign = signs
        for i, ax in enumerate("xyz"):
            if "translate" + ax.upper() in vals:
                vals["translate" + ax.upper()] *= tsign[i]
            if "rotate" + ax.upper() in vals:
                vals["rotate" + ax.upper()] *= rsign[i]
    return vals


@undoable
def mirror_pose():
    sel = selection()
    if not sel:
        return warn("select controls to mirror")
    targets, done = {}, set()
    for node in sel:
        if node in done:
            continue
        opp = opposite(node)
        if opp:
            targets[opp] = _mirrored_values(node, opp)
            targets[node] = _mirrored_values(opp, node)
            done.update((node, opp))
        else:
            targets[node] = _mirrored_values(node, node)
            done.add(node)
    for node, vals in targets.items():
        attrs = [a for a in vals if cmds.attributeQuery(a, node=node, exists=True)]
        for a in attrs:
            try:
                cmds.setAttr("%s.%s" % (node, a), vals[a])
            except RuntimeError:
                pass
        if attrs and (is_animated(node) or cmds.autoKeyframe(q=True, state=True)):
            cmds.setKeyframe(node, attribute=attrs)


@undoable
def select_opposite(add=False):
    opps = [o for o in (opposite(n) for n in selection()) if o]
    if opps:
        cmds.select(opps, add=add)


# ---------------------------------------------------------------- xform tools

@undoable
def align_objects():
    sel = selection()
    if len(sel) < 2:
        return warn("select the objects to move, then the target last")
    target = world_matrix(sel[-1])
    for n in sel[:-1]:
        set_world_matrix(n, target)
        key_transform(n)


def copy_world_space():
    sel = selection()
    if not sel:
        return warn("select objects")
    _clip["world"] = [(n, world_matrix(n)) for n in sel]
    message("world space copied: %d" % len(sel))


@undoable
def paste_world_space(all_keys=False):
    if not _clip["world"]:
        return warn("copy world space first")
    items = [(n, m) for n, m in _clip["world"] if cmds.objExists(n)]
    sel = selection()
    if sel and len(items) == 1 and sel != [items[0][0]]:
        items = [(n, items[0][1]) for n in sel]
    if not all_keys:
        for n, m in items:
            set_world_matrix(n, m)
            key_transform(n)
        return

    def apply(t):
        for n, m in items:
            set_world_matrix(n, m)
            key_transform(n, t, force=True)
    run_at_times(key_times([n for n, _ in items]) or [current_time()], apply)


def copy_relationship():
    sel = selection()
    if len(sel) < 2:
        return warn("select the followers, then the anchor last")
    anchor = sel[-1]
    a = world_matrix(anchor)
    inv = minv(a)
    items = []
    for n in sel[:-1]:
        m = world_matrix(n)
        items.append((n, mmul(m, inv), [m[12 + i] - a[12 + i] for i in range(3)]))
    _clip["rel"] = (anchor, items)
    message("relationship to %s copied" % strip_ns(anchor))


def _relationship_target(n, rel, offset, a, channels):
    """tr: rigid follow; t: world-space position offset only (ignores anchor rotation); r: rotation offset only."""
    if channels == "t":
        m = world_matrix(n)
        for i in range(3):
            m[12 + i] = a[12 + i] + offset[i]
        return m
    return mmul(rel, a)


@undoable
def paste_relationship(all_keys=False, channels="tr"):
    if not _clip["rel"]:
        return warn("copy a relationship first")
    anchor, items = _clip["rel"]
    if not cmds.objExists(anchor):
        return warn("anchor no longer exists")
    items = [item for item in items if cmds.objExists(item[0])]

    def apply(t=None):
        a = world_matrix(anchor)
        for n, rel, offset in items:
            set_world_matrix(n, _relationship_target(n, rel, offset, a, channels), channels)
            key_transform(n, t, force=t is not None, channels=channels)
    if all_keys:
        run_at_times(key_times([anchor] + [item[0] for item in items]) or [current_time()], apply)
    else:
        apply()


# ---------------------------------------------------------------- space switch

def enum_attrs(nodes):
    """Enum attributes present on every node, with their field names."""
    common = None
    for n in nodes:
        attrs = {}
        for a in cmds.listAttr(n, keyable=True) or []:
            try:
                if cmds.attributeQuery(a, node=n, attributeType=True) == "enum":
                    attrs[a] = cmds.attributeQuery(a, node=n, listEnum=True)[0].split(":")
            except RuntimeError:
                pass
        common = attrs if common is None else {k: v for k, v in common.items() if k in attrs}
    return common or {}


@undoable
def space_switch(attr, index, all_keys=False):
    nodes = [n for n in selection() if cmds.attributeQuery(attr, node=n, exists=True)]
    if not nodes:
        return
    if not all_keys:
        mats = {n: world_matrix(n) for n in nodes}
        for n in nodes:
            cmds.setAttr("%s.%s" % (n, attr), index)
            if is_animated(n) or cmds.autoKeyframe(q=True, state=True):
                cmds.setKeyframe(n, attribute=attr)
            set_world_matrix(n, mats[n])
            key_transform(n)
        return
    times = key_times(nodes) or [current_time()]
    mats = {(n, t): world_matrix(n, t) for n in nodes for t in times}
    for n in nodes:
        for t in times:
            cmds.setKeyframe(n, attribute=attr, t=t, v=index)

    def apply(t):
        for n in nodes:
            set_world_matrix(n, mats[(n, t)])
            key_transform(n, t, force=True)
    run_at_times(times, apply)


# ---------------------------------------------------------------- temp controls / pivot

def _temp_group():
    if not cmds.objExists(TEMP_GRP):
        cmds.createNode("transform", name=TEMP_GRP, skipSelect=True)
    return TEMP_GRP


def _constrain(driver, driven):
    skip_t = [ax for ax in "xyz" if not cmds.getAttr("%s.t%s" % (driven, ax), settable=True)]
    skip_r = [ax for ax in "xyz" if not cmds.getAttr("%s.r%s" % (driven, ax), settable=True)]
    if len(skip_t) == 3 and len(skip_r) == 3:
        return None
    return cmds.parentConstraint(driver, driven, mo=True, skipTranslate=skip_t or "none",
                                 skipRotate=skip_r or "none")[0]


def temp_controls_active():
    return bool(cmds.ls("AT_tempCtrl_*", type="transform"))


@undoable
def toggle_temp_controls():
    locs = cmds.ls("AT_tempCtrl_*", type="transform", long=True) or []
    if locs:
        return _release_temp_controls(locs)
    sel = selection()
    if not sel:
        return warn("select controls to drive with world-space temp controls")
    grp = _temp_group()
    times = key_times(sel) or [current_time()]
    pairs = []
    for n in sel:
        loc = cmds.spaceLocator(name="AT_tempCtrl_" + strip_ns(n))[0]
        loc = cmds.parent(loc, grp)[0]
        cmds.setAttr(loc + "Shape.localScale", 10, 10, 10)
        cmds.addAttr(loc, longName="atTarget", dataType="string")
        cmds.setAttr(loc + ".atTarget", n, type="string")
        pairs.append((n, loc))
    mats = {(n, t): world_matrix(n, t) for n, _ in pairs for t in times}

    def apply(t):
        for n, loc in pairs:
            set_world_matrix(loc, mats[(n, t)])
            cmds.setKeyframe(loc, attribute=["t", "r"], t=t)
    run_at_times(times, apply)
    for n, loc in pairs:
        _constrain(loc, n)
    cmds.select([loc for _, loc in pairs])
    message("temp controls on %d objects - click again to bake back" % len(pairs))


def _release_temp_controls(locs):
    pairs = []
    for loc in locs:
        n = cmds.getAttr(loc + ".atTarget") if cmds.attributeQuery("atTarget", node=loc, exists=True) else None
        if n and cmds.objExists(n):
            pairs.append((n, loc))
    nodes = [n for n, _ in pairs]
    times = sorted(set(key_times(nodes)) | set(key_times(locs))) or [current_time()]
    mats = {(n, t): world_matrix(n, t) for n in nodes for t in times}
    for n in nodes:
        cons = cmds.listRelatives(n, type="parentConstraint", fullPath=True) or []
        if cons:
            cmds.delete(cons)
    cmds.delete(locs)
    if cmds.objExists(TEMP_GRP) and not cmds.listRelatives(TEMP_GRP, children=True):
        cmds.delete(TEMP_GRP)

    def apply(t):
        for n in nodes:
            set_world_matrix(n, mats[(n, t)])
            key_transform(n, t, force=True)
    run_at_times(times, apply)
    cmds.select(nodes)
    message("temp controls baked back")


def temp_pivot_active():
    return cmds.objExists("AT_tempPivot")


@undoable
def toggle_temp_pivot():
    if temp_pivot_active():
        piv = "AT_tempPivot"
        nodes = cmds.getAttr(piv + ".atTargets").split(";") if cmds.attributeQuery("atTargets", node=piv, exists=True) else []
        nodes = [n for n in nodes if cmds.objExists(n)]
        mats = {n: world_matrix(n) for n in nodes}
        for n in nodes:
            cons = cmds.listRelatives(n, type="parentConstraint", fullPath=True) or []
            if cons:
                cmds.delete(cons)
        cmds.delete(piv)
        if cmds.objExists(TEMP_GRP) and not cmds.listRelatives(TEMP_GRP, children=True):
            cmds.delete(TEMP_GRP)
        for n in nodes:
            set_world_matrix(n, mats[n])
            key_transform(n)
        cmds.select(nodes)
        return
    sel = selection()
    if not sel:
        return warn("select the objects to pivot (the last one is the pivot)")
    pos = cmds.xform(sel[-1], q=True, ws=True, rotatePivot=True)
    piv = cmds.spaceLocator(name="AT_tempPivot")[0]
    piv = cmds.parent(piv, _temp_group())[0]
    cmds.setAttr(piv + "Shape.localScale", 8, 8, 8)
    cmds.xform(piv, ws=True, t=pos)
    cmds.addAttr(piv, longName="atTargets", dataType="string")
    cmds.setAttr(piv + ".atTargets", ";".join(sel), type="string")
    for n in sel:
        _constrain(piv, n)
    cmds.select(piv)
    cmds.setToolTo("RotateSuperContext")
    message("temp pivot - rotate it, click again to key and release")


# ---------------------------------------------------------------- motion trail / bookmarks / viewport

def motion_trails_exist():
    return cmds.objExists(TRAIL_GRP)


@undoable
def toggle_motion_trail():
    if cmds.objExists(TRAIL_GRP):
        cmds.delete(TRAIL_GRP)
        return
    sel = selection()
    if not sel:
        return warn("select objects to trail")
    st, et = time_range()
    grp = cmds.createNode("transform", name=TRAIL_GRP, skipSelect=True)
    for n in sel:
        res = cmds.snapshot(n, motionTrail=True, increment=1, startTime=st, endTime=et, name="AT_trail_" + strip_ns(n))
        handle = cmds.listRelatives(res[0], parent=True) if cmds.nodeType(res[0]) != "transform" else [res[0]]
        if handle:
            try:
                cmds.parent(handle[0], grp)
            except RuntimeError:
                pass
    cmds.select(sel)


def _bookmarks():
    cmds.loadPlugin("timeSliderBookmark", quiet=True)
    import maya.plugin.timeSliderBookmark.timeSliderBookmark as tsb
    return tsb


@undoable
def add_bookmark():
    tsb = _bookmarks()
    slider = mel.eval("$t=$gPlayBackSlider")
    if cmds.timeControl(slider, q=True, rangeVisible=True):
        a, b = cmds.timeControl(slider, q=True, rangeArray=True)
        tsb.createBookmark(start=a, stop=b - 1)
    else:
        ct = current_time()
        tsb.createBookmark(start=ct, stop=ct)


def _bookmark_starts():
    return sorted(cmds.getAttr(b + ".timeRangeStart") for b in cmds.ls(type="timeSliderBookmark") or [])


def bookmarks():
    marks = []
    for b in cmds.ls(type="timeSliderBookmark") or []:
        marks.append((cmds.getAttr(b + ".name") or b, cmds.getAttr(b + ".timeRangeStart"), cmds.getAttr(b + ".timeRangeStop")))
    return sorted(marks, key=lambda m: m[1])


def go_to_bookmark(direction):
    ct = current_time()
    starts = _bookmark_starts()
    nxt = [t for t in starts if t > ct] if direction > 0 else [t for t in starts if t < ct]
    if nxt:
        cmds.currentTime(nxt[0] if direction > 0 else nxt[-1])


def delete_bookmark_here():
    _bookmarks().deleteBookmarkAtCurrentTime()


def clear_bookmarks():
    bms = cmds.ls(type="timeSliderBookmark")
    if bms:
        cmds.delete(bms)


def set_viewport_suspended(state):
    _state["suspended"] = bool(state)
    cmds.refresh(suspend=bool(state))
    message("viewport suspended" if state else "viewport resumed")


# ---------------------------------------------------------------- curves / misc

@undoable
def euler_filter():
    nodes = selection()
    curves = [c for c in (anim_curves(nodes) if nodes else scene_curves()) if cmds.nodeType(c) == "animCurveTA"]
    if curves:
        cmds.filterCurve(curves, filter="euler")
        message("euler filter: %d curves" % len(curves))


@undoable
def select_rig_controls():
    sel = cmds.ls(sl=True) or []
    if not sel:
        return warn("select one control of the rig")
    ns = sel[0].rpartition(":")[0]
    curves = cmds.ls((ns + ":*") if ns else "*", type="nurbsCurve", long=True) or []
    ctrls = list(dict.fromkeys(cmds.listRelatives(curves, parent=True, fullPath=True) or []))
    cmds.select(ctrls)


@undoable
def select_animated():
    sel = cmds.ls(sl=True) or []
    ns = sel[0].rpartition(":")[0] if sel else None
    nodes = []
    for c in scene_curves():
        plug = driven_plug(c)
        if plug:
            node = plug.split(".")[0]
            if ns is None or node.startswith(ns + ":"):
                nodes.append(node)
    cmds.select(list(dict.fromkeys(nodes)))


@undoable
def key_selection():
    if selection():
        cmds.setKeyframe(selection())


@undoable
def delete_static_channels():
    if selection():
        cmds.delete(selection(), staticChannels=True)


@undoable
def bake_selection():
    sel = selection()
    if sel:
        st, et = time_range()
        cmds.bakeResults(sel, t=(st, et), simulation=True, sampleBy=1, preserveOutsideKeys=True)


# ---------------------------------------------------------------- selection sets

def selection_sets():
    return sorted(cmds.ls(SELSET_PREFIX + "*", type="objectSet") or [])


@undoable
def create_selection_set():
    sel = cmds.ls(sl=True) or []
    if not sel:
        return warn("select objects for the set")
    res = cmds.promptDialog(title="AT Select Set", message="Name:", button=["OK", "Cancel"],
                            defaultButton="OK", cancelButton="Cancel", dismissString="Cancel")
    if res != "OK":
        return
    name = re.sub(r"\W", "_", cmds.promptDialog(q=True, text=True).strip()) or "set"
    cmds.sets(sel, name=SELSET_PREFIX + name)


def select_set(name, add=False):
    members = cmds.sets(name, q=True) or []
    cmds.select(members, add=add)


def delete_selection_set(name):
    if cmds.objExists(name):
        cmds.delete(name)


# ---------------------------------------------------------------- anim recovery

def recovery_dir():
    return os.path.join(cmds.internalVar(userAppDir=True), "AT_recovery")


RECOVERY_KEEP = 20


def save_recovery(force=False):
    if not force and not cmds.file(q=True, modified=True):
        return None
    folder = recovery_dir()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    scene = os.path.splitext(os.path.basename(cmds.file(q=True, sn=True) or "untitled"))[0] or "untitled"
    path = os.path.join(folder, "%s_%s.ma" % (scene, datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    cmds.file(path, exportAll=True, type="mayaAscii", force=True, preserveReferences=True)
    backups = sorted(glob.glob(os.path.join(folder, scene + "_*.ma")))
    for old in backups[:-RECOVERY_KEEP]:
        try:
            os.remove(old)
        except OSError:
            pass
    return path


def open_recovery_folder():
    folder = recovery_dir()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    os.startfile(folder)
