"""The AT bar's tools (2026-10-21): animBot's keys, blend sliders, pose and animation clipboard, mirror,
xform, space switch, temp controls and pivot, trails, bookmarks and anim recovery, native."""
import datetime
import json
import math
import os
import re
from contextlib import contextmanager
from functools import wraps

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

ANIM_CURVE_TYPES = ["animCurveTL", "animCurveTA", "animCurveTU", "animCurveTT"]
DATA_NODE = "AT_data"
TEMP_GRP = "AT_TEMP"
TEMP_CTRL, TEMP_PIVOT = "AT_tempCtrl_", "AT_tempPivot"
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


def highlighted_range():
    """(first, last) of the frames highlighted on the Time Bar (or Maya's time slider), else None."""
    try:
        import maya_timebar
        span = maya_timebar.highlight()
    except Exception:                                        # noqa: BLE001 - no Time Bar
        span = None
    if span is None:
        try:
            slider = mel.eval("$t=$gPlayBackSlider")
            if cmds.timeControl(slider, q=True, rangeVisible=True):
                span = cmds.timeControl(slider, q=True, rangeArray=True)
        except RuntimeError:
            span = None
    return (span[0], span[1] - 1) if span else None


def keys_in_range(times, first, last):
    """The key times from `first` to `last`, both ends counted. Pure."""
    return sorted(t for t in set(times) if first - 1e-6 <= t <= last + 1e-6)


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


@contextmanager
def detached(curves):
    """Curve outputs disconnected while their keys move: on a connected curve every moved key re-dirties
    the rig downstream (~20 ms a key on a spine IK control, 30+ s for a scene-wide insert), detached ~0.1 ms."""
    links = []
    for c in curves:
        for dst in cmds.listConnections(c + ".output", s=False, d=True, plugs=True) or []:
            try:
                cmds.disconnectAttr(c + ".output", dst)
                links.append((c + ".output", dst))
            except RuntimeError:
                pass
    try:
        yield
    finally:
        for src, dst in links:
            cmds.connectAttr(src, dst, force=True)


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
    with detached(curves):
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
    selected controls or on every curve in the scene. A removal deletes the keys on those frames, then
    every curve moves by the same amount - the channels stay in sync."""
    if not frames:
        return
    ct = current_time()
    curves = scene_curves() if scene else selected_curves()
    if not curves:
        return warn("nothing animated in the scene" if scene else "select animated controls")
    #  baked animation has a key on every frame: a removal that only closed empty gaps removed nothing
    end = ct - frames if frames < 0 else ct
    spans = []
    doomed = []
    for c in curves:
        times = cmds.keyframe(c, q=True, tc=True) or []
        cut = [t for t in times if ct < t <= end]
        if cut:
            doomed.append((c, min(cut), max(cut)))
        after = [t for t in times if t > end]
        if after:
            spans.append((c, min(after), max(after)))
    if not spans and not doomed:
        return warn("no keys after frame %g" % ct)
    with detached(list(dict.fromkeys(c for c, _first, _last in doomed + spans))):
        for c, first, last in doomed:
            cmds.cutKey(c, time=(first, last), clear=True)
        for c, first, last in spans:
            try:
                cmds.keyframe(c, e=True, t=(first, last), relative=True, timeChange=frames, option="over")
            except RuntimeError:
                pass
    where = "the scene" if scene else "%d curves" % len(curves)
    message("%s %d frame(s) after frame %g in %s" % ("inserted" if frames > 0 else "removed", abs(frames), ct, where))


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
def paste_relationship(in_range=False, channels="tr"):
    """On the current frame, or (`in_range`, 2026-10-23 «тільки виділеної кількості ключів, умовно з 10
    по 20»; it replaced "on all keys") on the keys of the anchor and the followers inside the frames
    highlighted on the Time Bar."""
    if not _clip["rel"]:
        return warn("copy a relationship first")
    anchor, items = _clip["rel"]
    if not cmds.objExists(anchor):
        return warn("anchor no longer exists")
    items = [item for item in items if cmds.objExists(item[0])]
    times = None
    if in_range:
        span = highlighted_range()
        if span is None:
            return warn("highlight the frames on the Time Bar first (e.g. 10-20)")
        times = keys_in_range(key_times([anchor] + [item[0] for item in items]), *span)
        if not times:
            return warn("no keys from %g to %g" % span)

    def apply(t=None):
        a = world_matrix(anchor)
        for n, rel, offset in items:
            set_world_matrix(n, _relationship_target(n, rel, offset, a, channels), channels)
            key_transform(n, t, force=t is not None, channels=channels)
    if times:
        run_at_times(times, apply)
        message("relationship pasted on %d keys (%g-%g)" % (len(times), times[0], times[-1]))
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

def here(name, namespace):
    """`name` (or a pattern) in `namespace`, absolute: what a node made now is called. In a scene tab the
    current namespace is the tab's (2026-10-26: the tab's temp controls were never found). Pure."""
    namespace = (namespace or ":").strip(":")
    return ":%s:%s" % (namespace, name) if namespace else ":" + name


def _here(name):
    return here(name, cmds.namespaceInfo(currentNamespace=True, absoluteName=True))


def _shape(node):
    #  Maya numbers the transform, not always the shape (AT_tempCtrl_IKArm_L3 over AT_tempCtrl_IKArm_LShape)
    return (cmds.listRelatives(node, shapes=True, fullPath=True) or [node + "Shape"])[0]


def _temp_group():
    found = _here(TEMP_GRP)
    if cmds.objExists(found):
        return found
    return cmds.createNode("transform", name=TEMP_GRP, skipSelect=True)


def _drop_empty_temp_group():
    grp = _here(TEMP_GRP)
    if cmds.objExists(grp) and not cmds.listRelatives(grp, children=True):
        cmds.delete(grp)


def _constrain(driver, driven):
    skip_t = [ax for ax in "xyz" if not cmds.getAttr("%s.t%s" % (driven, ax), settable=True)]
    skip_r = [ax for ax in "xyz" if not cmds.getAttr("%s.r%s" % (driven, ax), settable=True)]
    if len(skip_t) == 3 and len(skip_r) == 3:
        return None
    return cmds.parentConstraint(driver, driven, mo=True, skipTranslate=skip_t or "none",
                                 skipRotate=skip_r or "none")[0]


def _temp_controls():
    return cmds.ls(_here(TEMP_CTRL + "*"), type="transform", long=True) or []


def temp_controls_active():
    return bool(_temp_controls())


@undoable
def toggle_temp_controls():
    locs = _temp_controls()
    if locs:
        return _release_temp_controls(locs)
    sel = selection()
    if not sel:
        return warn("select controls to drive with world-space temp controls")
    grp = _temp_group()
    times = key_times(sel) or [current_time()]
    pairs = []
    for n in sel:
        loc = cmds.spaceLocator(name=TEMP_CTRL + strip_ns(n))[0]
        loc = cmds.parent(loc, grp)[0]
        cmds.setAttr(_shape(loc) + ".localScale", 10, 10, 10)
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
    _drop_empty_temp_group()

    def apply(t):
        for n in nodes:
            set_world_matrix(n, mats[(n, t)])
            key_transform(n, t, force=True)
    run_at_times(times, apply)
    cmds.select(nodes)
    message("temp controls baked back")


def temp_pivot_active():
    return cmds.objExists(_here(TEMP_PIVOT))


@undoable
def toggle_temp_pivot():
    if temp_pivot_active():
        piv = _here(TEMP_PIVOT)
        nodes = cmds.getAttr(piv + ".atTargets").split(";") if cmds.attributeQuery("atTargets", node=piv, exists=True) else []
        nodes = [n for n in nodes if cmds.objExists(n)]
        mats = {n: world_matrix(n) for n in nodes}
        for n in nodes:
            cons = cmds.listRelatives(n, type="parentConstraint", fullPath=True) or []
            if cons:
                cmds.delete(cons)
        cmds.delete(piv)
        _drop_empty_temp_group()
        for n in nodes:
            set_world_matrix(n, mats[n])
            key_transform(n)
        cmds.select(nodes)
        return
    sel = selection()
    if not sel:
        return warn("select the objects to pivot (the last one is the pivot)")
    pos = cmds.xform(sel[-1], q=True, ws=True, rotatePivot=True)
    piv = cmds.spaceLocator(name=TEMP_PIVOT)[0]
    piv = cmds.parent(piv, _temp_group())[0]
    cmds.setAttr(_shape(piv) + ".localScale", 8, 8, 8)
    cmds.xform(piv, ws=True, t=pos)
    cmds.addAttr(piv, longName="atTargets", dataType="string")
    cmds.setAttr(piv + ".atTargets", ";".join(sel), type="string")
    for n in sel:
        _constrain(piv, n)
    cmds.select(piv)
    cmds.setToolTo("RotateSuperContext")
    message("temp pivot - rotate it, click again to key and release")


# ---------------------------------------------------------------- motion trail / bookmarks / viewport

TRAIL_MARKER = "skeldarATTrails"


def is_trail_group_name(node):
    """`AT_MOTION_TRAILS`, or Maya's numbered `AT_MOTION_TRAILS12`, in any namespace. Pure."""
    return re.match(r"^%s\d*$" % TRAIL_GRP, node.split("|")[-1].split(":")[-1]) is not None


def trail_groups():
    """Our trails' groups, found by their marker and by name: 2026-10-23 «моушн тейл перестав справно
    працювати» - Maya had named the groups AT_MOTION_TRAILS3..12, `objExists("AT_MOTION_TRAILS")` saw
    none of them, and every click added a trail instead of taking it away."""
    found = cmds.ls("*." + TRAIL_MARKER, recursive=True, objectsOnly=True, long=True) or []
    found += [n for n in cmds.ls(TRAIL_GRP + "*", recursive=True, type="transform", long=True) or []
              if is_trail_group_name(n) and not cmds.listRelatives(n, parent=True)]
    return sorted(set(found))


def motion_trails_exist():
    return bool(trail_groups())


#  2026-10-23 «щоб можна було окремі трейли видаляти ... кнопка едд, і кнопки клір (для одного, і клар
#  ол для всіх)»: each trail's handle says whose trail it is
TRAIL_OF = "skeldarATTrailOf"
TRAIL_PREFIX = "AT_trail_"


def legacy_trail_of(handle, leaf):
    """A handle made before TRAIL_OF (`AT_trail_DaggerMesh3Handle`) is the trail of `leaf`
    (`DaggerMesh`): our prefix, the leaf, Maya's number, `Handle`. Pure."""
    name = handle.split("|")[-1].split(":")[-1]
    return re.match(r"^%s%s\d*Handle$" % (TRAIL_PREFIX, re.escape(leaf)), name) is not None


def trail_handles():
    """[(handle, the UUID of its object or None)] of every trail in our groups."""
    out = []
    for grp in trail_groups():
        for handle in cmds.listRelatives(grp, children=True, type="transform", fullPath=True) or []:
            of = None
            if cmds.attributeQuery(TRAIL_OF, node=handle, exists=True):
                of = cmds.getAttr(handle + "." + TRAIL_OF) or None
            out.append((handle, of))
    return out


def handles_of(handles, nodes):
    """The handles among `handles` ([(handle, uuid)]) that trail `nodes` ([(uuid, leaf)]). Pure."""
    uuids = set(u for u, _ in nodes)

    def ours(handle, of):
        return of in uuids if of else any(legacy_trail_of(handle, leaf) for _, leaf in nodes)
    return [h for h, of in handles if ours(h, of)]


def _uuid(node):
    return (cmds.ls(node, uuid=True) or [None])[0]


def _drop_handles(handles):
    trails = []
    for handle in handles:
        for shape in cmds.listRelatives(handle, shapes=True, fullPath=True) or []:
            trails += cmds.listConnections(shape, type="motionTrail") or []
    for node in sorted(set(trails)) + list(handles):
        if cmds.objExists(node):                             # a trail's handle may go with it
            cmds.delete(node)
    for grp in trail_groups():
        if not cmds.listRelatives(grp, children=True):
            cmds.delete(grp)


def _drop_trails(groups):
    handles = []
    for grp in groups:
        handles += cmds.listRelatives(grp, children=True, type="transform", fullPath=True) or []
    _drop_handles(handles)
    for grp in groups:
        if cmds.objExists(grp):
            cmds.delete(grp)


def _trail_group():
    marked = cmds.ls("*." + TRAIL_MARKER, recursive=True, objectsOnly=True, long=True) or []
    if marked:
        return marked[0]
    grp = cmds.createNode("transform", name=TRAIL_GRP, skipSelect=True)
    cmds.addAttr(grp, longName=TRAIL_MARKER, attributeType="bool")
    return cmds.ls(grp, long=True)[0]


def _build_trails(nodes):
    """A trail on each of `nodes` that has none yet. How many were made."""
    have = set(of for _, of in trail_handles() if of)
    nodes = [n for n in nodes if _uuid(n) not in have]
    if not nodes:
        return 0
    st, et = time_range()
    grp = _trail_group()
    for n in nodes:
        res = cmds.snapshot(n, motionTrail=True, increment=1, startTime=st, endTime=et, name=TRAIL_PREFIX + strip_ns(n))
        handle = res[0] if cmds.nodeType(res[0]) == "transform" else (cmds.listRelatives(res[0], parent=True) or [None])[0]
        if not handle:
            continue
        cmds.addAttr(handle, longName=TRAIL_OF, dataType="string")
        cmds.setAttr(handle + "." + TRAIL_OF, _uuid(n), type="string")
        try:
            cmds.parent(handle, grp)
        except RuntimeError:
            pass
    return len(nodes)


@undoable
def motion_trail_click():
    """The button: a trail on the selection in place of the ones standing; nothing selected, every
    trail away."""
    sel = selection()
    _drop_trails(trail_groups())
    if sel:
        _build_trails(sel)
        cmds.select(sel)


@undoable
def add_motion_trail():
    """A trail on each selected control, the others kept."""
    sel = selection()
    if not sel:
        return warn("select the controls to add a trail to")
    made = _build_trails(sel)
    cmds.select(sel)
    if not made:
        message("the selection has its trails already")


@undoable
def clear_motion_trail():
    """The trails of the selected controls away, the others kept."""
    sel = selection()
    if not sel:
        return warn("select the controls whose trails to clear")
    doomed = handles_of(trail_handles(), [(_uuid(n), strip_ns(n)) for n in sel])
    if not doomed:
        return warn("the selection has no trails")
    _drop_handles(doomed)


@undoable
def clear_all_motion_trails():
    _drop_trails(trail_groups())


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

def set_label(node):
    """`L_fingers` for `tab_x:AT_sel_L_fingers`: the set's name without its namespace and our prefix. Pure."""
    leaf = node.split("|")[-1].split(":")[-1]
    return leaf[len(SELSET_PREFIX):] if leaf.startswith(SELSET_PREFIX) else leaf


def sets_in(nodes, namespace):
    """[(label, node)] of our select sets among `nodes` that live in `namespace` (":" the root), by label. Pure."""
    wanted = (namespace or ":").strip(":")
    found = []
    for node in nodes:
        leaf = node.split(":")[-1]
        if leaf.startswith(SELSET_PREFIX) and node[:-len(leaf)].strip(":") == wanted:
            found.append((set_label(node), node))
    return sorted(found)


# 2026-10-23 «щоб селекшн сет зберігався в ядрі АТ ... в будь-якій сцені»: the sets live in a library of
# the animator's own (LIBRARY_NAME in Maya's user folder), not in the scene. A member is kept as its name
# without namespaces and found again in whatever scene is open: Manny_Rig1:FKWrist_L there is
# FKWrist_L, which is Manny_Rig:FKWrist_L here.
LIBRARY_NAME = "AT_selection_sets.json"


def library_path():
    return os.path.join(cmds.internalVar(userAppDir=True), LIBRARY_NAME)


def load_library(path=None):
    """{"sets": {label: {"members": [...], "colour": str|None}}, "seen": [labels taken from scenes]}."""
    path = path or library_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    sets = data.get("sets") if isinstance(data.get("sets"), dict) else {}
    seen = data.get("seen") if isinstance(data.get("seen"), list) else []
    return {"sets": sets, "seen": seen}


def save_library(lib, path=None):
    """Written to a .partial first: a crash mid-write never loses the sets already there."""
    path = path or library_path()
    tmp = path + ".partial"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(lib, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def member_key(node):
    """`FKWrist_L` for `tab_x:Manny_Rig1:FKWrist_L` or `|grp|ns:FKWrist_L`. Pure."""
    return node.split("|")[-1].split(":")[-1]


def member_keys(nodes):
    """The members' keys, each once, in the order picked. Pure."""
    out = []
    for node in nodes:
        key = member_key(node)
        if key not in out:
            out.append(key)
    return out


def _namespace(node):
    return node.split("|")[-1].rpartition(":")[0]


def resolve(keys, found, prefer=(), within=""):
    """The scene's nodes for the set's `keys`. `found` holds every node named like a key in any namespace;
    one per key, from the first namespace of `prefer` (the selection's) that has it, else from the
    namespace most of the set lives in - a set made on Manny_Rig1 selects one character, not every rig's
    hands. `within` (the scene tab's namespace) keeps the search inside the tab. Pure."""
    within = (within or "").strip(":")
    by_key = {}
    for node in found:
        ns = _namespace(node)
        if within and ns != within and not ns.startswith(within + ":"):
            continue
        by_key.setdefault(member_key(node), []).append(node)
    count = {}
    for key in keys:
        for ns in set(_namespace(n) for n in by_key.get(key, [])):
            count[ns] = count.get(ns, 0) + 1
    order = [ns for ns in prefer if ns in count] + sorted(count, key=lambda ns: (-count[ns], ns))
    rank = {}
    for i, ns in enumerate(order):
        rank.setdefault(ns, i)
    out = []
    for key in keys:
        nodes = by_key.get(key, [])
        if nodes:
            out.append(min(nodes, key=lambda n: (rank.get(_namespace(n), len(order)), n)))
    return out


def take_scene_sets(lib, scene_sets):
    """The sets the scene still holds as objectSets (made before the library) added to `lib` once each:
    `scene_sets` is [(label, member nodes)]. A label already in the library, or taken once and deleted
    since, is left alone. True when `lib` changed. Pure."""
    changed = False
    for label, members in scene_sets:
        if label in lib["sets"] or label in lib["seen"]:
            continue
        lib["sets"][label] = {"members": member_keys(members), "colour": None}
        lib["seen"].append(label)
        changed = True
    return changed


def _library():
    """The library, with the open scene's old objectSets taken into it."""
    lib = load_library()
    scene = [(label, cmds.sets(node, q=True) or [])
             for label, node in sets_in(cmds.ls(type="objectSet") or [], cmds.namespaceInfo(currentNamespace=True))]
    if take_scene_sets(lib, scene):
        save_library(lib)
    return lib


def selection_sets():
    """[(label, label)] of the library's sets, by label - every scene shows the same ones. The second is
    what the cells and menus hand back to the functions below."""
    return [(label, label) for label in sorted(_library()["sets"])]


def has_set(name):
    return name in load_library()["sets"]


def set_members(name):
    """The set's members in the open scene."""
    entry = load_library()["sets"].get(name)
    keys = (entry or {}).get("members") or []
    if not keys:
        return []
    found = cmds.ls(keys, recursive=True) or []
    prefer = []
    for node in cmds.ls(sl=True) or []:
        ns = _namespace(node)
        if ns not in prefer:
            prefer.append(ns)
    current = cmds.namespaceInfo(currentNamespace=True)
    return resolve(keys, found, prefer, "" if current in (":", "") else current)


def _ask_label(text=""):
    res = cmds.promptDialog(title="AT Select Set", message="Name:", text=text, button=["OK", "Cancel"],
                            defaultButton="OK", cancelButton="Cancel", dismissString="Cancel")
    if res != "OK":
        return None
    return re.sub(r"\W", "_", cmds.promptDialog(q=True, text=True).strip())


def create_selection_set():
    """A set of the selection under a name asked for; a name already used updates that set."""
    sel = cmds.ls(sl=True) or []
    if not sel:
        return warn("select objects for the set")
    label = _ask_label()
    if label is None:
        return
    label = label or "set"
    lib = load_library()
    old = lib["sets"].get(label)
    lib["sets"][label] = {"members": member_keys(sel), "colour": old.get("colour") if old else None}
    save_library(lib)
    message("select set %s %s: %d objects" % (label, "updated" if old else "saved", len(sel)))


def select_set(name, add=False):
    members = set_members(name)
    if not members:
        return warn("select set %s: none of its objects are in this scene" % name)
    cmds.select(members, add=add)


def deselect_set(name):
    members = set_members(name)
    if members:
        cmds.select(members, deselect=True)


def set_size(name):
    return len(set_members(name))


def delete_selection_set(name):
    lib = load_library()
    if lib["sets"].pop(name, None) is not None:
        save_library(lib)
        message("select set %s deleted" % name)


def update_selection_set(name):
    """The set holds the selection now."""
    sel = cmds.ls(sl=True) or []
    if not sel:
        return warn("select the objects the set should hold")
    lib = load_library()
    entry = lib["sets"].setdefault(name, {"colour": None})
    entry["members"] = member_keys(sel)
    save_library(lib)
    message("select set %s updated: %d objects" % (name, len(sel)))


def rename_selection_set(name):
    """A new name asked for. The set's new name, or None."""
    label = _ask_label(name)
    if not label or label == name:
        return None
    lib = load_library()
    if label in lib["sets"]:
        return warn("select set %s already exists" % label)
    if name not in lib["sets"]:
        return None
    lib["sets"][label] = lib["sets"].pop(name)
    save_library(lib)
    return label


def set_colour(name):
    """The colour the animator gave the set's cell, or None."""
    return (load_library()["sets"].get(name) or {}).get("colour") or None


def paint_set(name, colour):
    lib = load_library()
    if name in lib["sets"]:
        lib["sets"][name]["colour"] = colour
        save_library(lib)


def sets_grid(count, columns=4):
    """[(row, column)] of `count` cells, `columns` wide at most and no wider than they need. Pure."""
    width = max(1, min(columns, count))
    return [(i // width, i % width) for i in range(count)]


# ---------------------------------------------------------------- anim recovery

def recovery_dir():
    return os.path.join(cmds.internalVar(userAppDir=True), "AT_recovery")


RECOVERY_KEEP = 20
RECOVERY_STAMP = "%Y%m%d_%H%M%S"


def backups_of(stem, names):
    """[(time, name)] of the backups of the scene `stem` among the file names `names`, oldest first. Pure.
    The stamp is matched exactly: the backups of `shot_1` are not those of `shot_1_2`."""
    found = []
    for name in names:
        m = re.match(r"^(.*)_(\d{8}_\d{6})\.m[ab]$", name)
        if m and m.group(1) == stem:
            found.append((datetime.datetime.strptime(m.group(2), RECOVERY_STAMP), name))
    return sorted(found)


def newest_backup(stem, saved_at, names):
    """The name of the newest backup of `stem` made after the file was saved (`saved_at`, a datetime),
    else None. Pure."""
    newer = [name for when, name in backups_of(stem, names) if when > saved_at]
    return newer[-1] if newer else None


def _stem(path):
    return os.path.splitext(os.path.basename(path or "untitled"))[0] or "untitled"


def save_recovery(force=False):
    if not force and not cmds.file(q=True, modified=True):
        return None
    folder = recovery_dir()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    scene = _stem(cmds.file(q=True, sn=True))
    path = os.path.join(folder, "%s_%s.mb" % (scene, datetime.datetime.now().strftime(RECOVERY_STAMP)))
    #  a crash in the middle of the export leaves a .partial, never a broken newest backup; GUI Maya
    #  appends .mb to an export path without it, so the extension stays last
    tmp = path[:-3] + ".partial.mb"
    cmds.file(tmp, exportAll=True, type="mayaBinary", force=True, preserveReferences=True)
    os.replace(tmp, path)
    for _when, old in backups_of(scene, os.listdir(folder))[:-RECOVERY_KEEP]:
        try:
            os.remove(os.path.join(folder, old))
        except OSError:
            pass
    return path


def restore_recovery(backup, scene):
    """The backup opened in place of `scene`: named as the scene, so Save writes the scene's own file."""
    cmds.file(backup, open=True, force=True)
    cmds.file(rename=scene)
    cmds.file(type="mayaAscii" if scene.lower().endswith(".ma") else "mayaBinary")
    cmds.file(modified=True)
    message("recovered changes from %s - save to keep them" % os.path.basename(backup))


def check_recovery(*_args):
    """After a scene opens: changes backed up later than its file was saved (a crash, a close without
    saving) are offered in its place."""
    scene = cmds.file(q=True, sn=True)
    folder = recovery_dir()
    if not scene or not os.path.isfile(scene) or not os.path.isdir(folder):
        return
    if os.path.normcase(os.path.dirname(os.path.abspath(scene))) == os.path.normcase(os.path.abspath(folder)):
        return
    key = (scene, os.path.getmtime(scene))
    if _state.get("recovery_checked") == key:
        return
    _state["recovery_checked"] = key
    saved_at = datetime.datetime.fromtimestamp(key[1])
    name = newest_backup(_stem(scene), saved_at, os.listdir(folder))
    if not name:
        return
    when = backups_of(_stem(scene), [name])[0][0]
    answer = cmds.confirmDialog(
        title="AT Anim Recovery",
        message="%s was saved at %s.\nAnim Recovery has newer changes from %s.\n\nOpen the recovered changes?"
                % (os.path.basename(scene), saved_at.strftime("%d.%m %H:%M:%S"), when.strftime("%d.%m %H:%M:%S")),
        button=["Open recovered", "Keep saved file"], defaultButton="Open recovered",
        cancelButton="Keep saved file", dismissString="Keep saved file")
    if answer == "Open recovered":
        restore_recovery(os.path.join(folder, name), scene)


def _deferred_check(*_args):
    import maya.utils
    maya.utils.executeDeferred(check_recovery)


def install_recovery_check():
    """check_recovery after every scene open, and once now for the scene Maya started with. Idempotent."""
    old = _state.pop("recovery_callback", None)
    if old is not None:
        try:
            om.MMessage.removeCallback(old)
        except RuntimeError:
            pass
    _state["recovery_callback"] = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, _deferred_check)
    _deferred_check()


def open_recovery_folder():
    folder = recovery_dir()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    os.startfile(folder)
