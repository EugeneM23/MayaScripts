"""The trail engine: every tracked CoM's points, computed through the parallel
Evaluation Manager in idle slices, drawn by Maya's own motionTrailShape.

Measured 2026-10-01 (spec): Maya's Motion Trail on a CoM costs 4.5 s per key
edit (each trail frame through a DG time context, 41 ms), the same frame
through the EM 5 ms. So the engine

- marks frames DIRTY, never computes in a callback: a time curve edited
  (only the frames whose sampled value changed, against a snapshot), a static
  attribute set on a control or joint (all frames), the range moving (the
  new frames), a scene opened (all);
- walks the dirty frames nearest the current time in slices of SLICE_MS
  under `refresh -suspend` (MAnimControl.setCurrentTime), never while a mouse
  button is down or the timeline plays, and comes back to the current frame
  with every unkeyed tweak put back;
- keeps the current frame's point LIVE: a tweak moves it at once.

State lives on `sys._skeldar_com` (trap 111): callbacks, the timer and the
points outlive a module purge, and a fresh module removes the old one's
callbacks before it registers its own.
"""

import sys
import time

import maya_hubcopy as hubcopy

from maya_com import frames

SLICE_MS = 40.0
IDLE_MS = 0                     # the next slice, when work remains
WAIT_MS = 120                   # retry while the mouse is down / playing
LIVE_MS = 15                    # a tweak's live point
TIME_CURVES = (0, 1, 2, 3)      # MFnAnimCurve TL, TA, TT, TU: time-driven


def state():
    st = getattr(sys, "_skeldar_com", None)
    if st is None:
        st = {}
        sys._skeldar_com = st
    for key, default in (("tracks", {}), ("callbacks", []), ("node_callbacks", {}),
                         ("jobs", []), ("timer", None), ("pending_curves", set()),
                         ("snapshots", {}), ("live", False), ("live_frames", set()),
                         ("per_frame_ms", 6.0), ("running", False),
                         ("stats", {"walked": 0, "slices": 0, "longest_ms": 0.0})):
        st.setdefault(key, default)
    return st


class Track(object):
    """One CoM's trail: its group (by UUID), span, points and dirty frames."""

    def __init__(self, uuid, span):
        self.uuid = uuid
        self.span = span
        self.points = {}            # frame -> (x, y, z, root_y)
        self.dirty = set(frames.frames_of(span))
        self.written = False

    def rerange(self, span):
        if span == self.span:
            return
        self.points, new = frames.rerange(self.points, span)
        self.dirty = {f for f in self.dirty if span[0] <= f <= span[1]} | new
        self.span = span

    def dirty_all(self):
        self.dirty = set(frames.frames_of(self.span))


# ------------------------------------------------------------------ seams

class Scene(object):
    """Everything the engine asks Maya. A test hands in its own."""

    def __init__(self):
        import maya.cmds as cmds
        import maya.api.OpenMaya as om
        import maya.api.OpenMayaAnim as oma
        self.cmds, self.om, self.oma = cmds, om, oma

    # time and state
    def current(self):
        return self.cmds.currentTime(query=True)

    def playback(self):
        c = self.cmds
        return (c.playbackOptions(q=True, minTime=True),
                c.playbackOptions(q=True, maxTime=True))

    def animation(self):
        c = self.cmds
        return (c.playbackOptions(q=True, animationStartTime=True),
                c.playbackOptions(q=True, animationEndTime=True))

    def playing(self):
        try:
            return bool(self.cmds.play(q=True, state=True))
        except Exception:
            return False

    def mouse_down(self):
        try:
            from PySide6 import QtCore, QtWidgets
            app = QtWidgets.QApplication.instance()
            return bool(app and app.mouseButtons() != QtCore.Qt.NoButton)
        except Exception:
            return False

    # the network
    def group(self, uuid):
        nodes = self.cmds.ls(uuid, long=True) or []
        return nodes[0] if nodes else None

    def settings(self, group):
        c = self.cmds
        return {"trail": c.getAttr(group + ".trail"),
                "range": c.getAttr(group + ".range"),
                "around": c.getAttr(group + ".around")}

    def _plug(self, name):
        sel = self.om.MSelectionList()
        sel.add(name)
        return sel.getPlug(0)

    def reader(self, group):
        """A function reading (x, y, z, root_y) of the group's CoM now."""
        from maya_com import network
        total = self._plug(network.part(group, "sum") + ".output3D")
        root_y = self._plug(network.part(group, "rootRow") + ".outputY")
        children = [total.child(i) for i in range(3)]
        return lambda: tuple(p.asDouble() for p in children) + (root_y.asDouble(),)

    def walk(self, frame_list, readers):
        """{frame: {uuid: point}} walking the time, back to the current frame
        after; the unkeyed tweaks of `tweak_plugs` put back."""
        om, oma, cmds = self.om, self.oma, self.cmds
        unit = om.MTime.uiUnit()
        here = oma.MAnimControl.currentTime()
        out = {}
        cmds.refresh(suspend=True)
        try:
            for frame in frame_list:
                oma.MAnimControl.setCurrentTime(om.MTime(frame, unit))
                out[frame] = {uuid: read() for uuid, read in readers.items()}
        finally:
            oma.MAnimControl.setCurrentTime(here)
            cmds.refresh(suspend=False)
        return out

    def tweaks(self, curve_plugs):
        """[(plug, live value)] of the curve-driven plugs whose value is not
        their curve's at the current time - an unkeyed pose change."""
        om, oma = self.om, self.oma
        now = oma.MAnimControl.currentTime()
        out = []
        for plug, curve in curve_plugs:
            try:
                live = plug.asDouble()
                keyed = oma.MFnAnimCurve(curve).evaluate(now)
            except Exception:
                continue
            if abs(live - keyed) > 1e-9:
                out.append((plug, live))
        return out

    def put_back(self, tweaks):
        if not tweaks:
            return
        mod = self.om.MDGModifier()
        for plug, value in tweaks:
            mod.newPlugValueDouble(plug, value)
        mod.doIt()

    def write(self, group, span, points):
        """The two trail shapes' points; no undo entry, the scene's modified
        flag as it was."""
        from maya_com import network
        om, cmds = self.om, self.cmds
        was = cmds.file(query=True, modified=True)
        ordered = frames.ordered_points(points, span)
        for name, flat in (("trail", False), ("floorTrail", True)):
            shape = network.trail_shape(group, name)
            if not shape:
                continue
            arr = om.MPointArray()
            for p in ordered:
                arr.append(om.MPoint(p[0], p[3] if flat else p[1], p[2]))
            data = om.MFnPointArrayData().create(arr)
            self._plug(shape + ".points").setMObject(data)
            self._plug(shape + ".startTime").setMTime(
                om.MTime(span[0], om.MTime.uiUnit()))
        if not was:
            cmds.file(modified=False)


SCENE = [None]


def scene():
    if SCENE[0] is None:
        SCENE[0] = Scene()
    return SCENE[0]


# --------------------------------------------------------------- tracking

def span_for(settings, sc=None):
    sc = sc or scene()
    mode = ("playback", "around")[int(settings.get("range", 0)) == 1]
    return frames.trail_range(mode, sc.playback(), sc.current(),
                              settings.get("around", 20), sc.animation())


def track(group, sc=None):
    sc = sc or scene()
    import maya.cmds as cmds
    uuid = (cmds.ls(group, uuid=True) or [None])[0]
    if not uuid:
        return None
    st = state()
    tr = st["tracks"].get(uuid)
    span = span_for(sc.settings(group), sc)
    if tr is None:
        tr = Track(uuid, span)
        st["tracks"][uuid] = tr
        _watch_nodes(uuid, group)
        _snapshot_curves(uuid, group, span)
    else:
        tr.rerange(span)
    arm(IDLE_MS)
    return tr


def untrack(uuid):
    st = state()
    st["tracks"].pop(uuid, None)
    _unwatch_nodes(uuid)


def dirty_all(uuid=None):
    for key, tr in state()["tracks"].items():
        if uuid is None or key == uuid:
            tr.dirty_all()
    arm(IDLE_MS)


def pending():
    return sum(len(tr.dirty) for tr in state()["tracks"].values())


# ------------------------------------------------------------- the slice

def tick(sc=None):
    """One slice. Returns the number of frames walked."""
    sc = sc or scene()
    st = state()
    if st.get("busy"):
        return 0
    st["busy"] = True
    try:
        return _tick(sc, st)
    finally:
        st["busy"] = False


def _resolve(sc, st):
    """{uuid: group path} of the live tracks; vanished ones dropped."""
    out = {}
    for uuid in list(st["tracks"]):
        group = sc.group(uuid)
        if not group:
            untrack(uuid)
            continue
        out[uuid] = group
    return out


def _tick(sc, st):
    groups = _resolve(sc, st)
    if not groups:
        return 0
    #  ranges follow the settings and the time (Around)
    for uuid, group in groups.items():
        st["tracks"][uuid].rerange(span_for(sc.settings(group), sc))
    _absorb_curves(st, groups)
    current = int(round(sc.current()))
    readers = {uuid: sc.reader(group) for uuid, group in groups.items()}
    touched = set()
    if st["live"]:
        st["live"] = False
        for uuid, read in readers.items():
            tr = st["tracks"][uuid]
            if tr.span[0] <= current <= tr.span[1]:
                tr.points[current] = read()
                tr.dirty.discard(current)
                st["live_frames"].add(current)
                touched.add(uuid)
    walked = 0
    work = set()
    for tr in st["tracks"].values():
        work |= tr.dirty
    if work and not sc.mouse_down() and not sc.playing():
        n = frames.budget(st["per_frame_ms"], SLICE_MS, st["per_frame_ms"])
        batch = frames.nearest_first(work, current)[:n]
        tweaks = sc.tweaks(_curve_plugs(st, groups))
        started = time.time()
        try:
            values = sc.walk(batch, readers)
        finally:
            sc.put_back(tweaks)
        spent = (time.time() - started) * 1000.0
        st["per_frame_ms"] = 0.7 * st["per_frame_ms"] + 0.3 * spent / (len(batch) + 1)
        st["stats"]["walked"] += len(batch)
        st["stats"]["slices"] += 1
        st["stats"]["longest_ms"] = max(st["stats"]["longest_ms"], spent)
        for frame, by_uuid in values.items():
            for uuid, point in by_uuid.items():
                tr = st["tracks"][uuid]
                if tr.span[0] <= frame <= tr.span[1]:
                    if frame == current and frame in st["live_frames"]:
                        continue        # the live (tweaked) point wins here
                    tr.points[frame] = point
                    tr.dirty.discard(frame)
                    touched.add(uuid)
        walked = len(batch)
    for uuid in touched:
        tr = st["tracks"][uuid]
        sc.write(groups[uuid], tr.span, tr.points)
        tr.written = True
    if touched:
        st["stats"]["last_write"] = time.time()
    if pending():
        arm(WAIT_MS if (sc.mouse_down() or sc.playing()) else IDLE_MS)
    return walked


def run_until_clean(sc=None, limit=10000):
    """Slices until nothing is dirty (the verify's and a Rebuild's road)."""
    sc = sc or scene()
    total = 0
    for _ in range(limit):
        st = state()
        if not pending() and not st["live"] and not st["pending_curves"]:
            break
        total += tick(sc)
    return total


# --------------------------------------------------------------- the timer

def arm(ms):
    st = state()
    timer = st.get("timer")
    if timer is None:
        try:
            from PySide6 import QtCore, QtWidgets
            if QtWidgets.QApplication.instance() is None:
                return
            timer = QtCore.QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(_on_timer)
            st["timer"] = timer
        except Exception:
            return
    if not timer.isActive():
        timer.start(int(ms))


def _on_timer():
    try:
        tick()
    except Exception as exc:              # the trail must never spam the UI
        state()["last_error"] = repr(exc)


# --------------------------------------------------------------- callbacks

def start():
    """Register (once per module object), track every CoM in the scene."""
    stop()
    st = state()
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma
    import maya.cmds as cmds
    st["callbacks"] = [
        oma.MAnimMessage.addAnimCurveEditedCallback(_on_curves),
    ]
    #  The engine is the scene's, not a card's (2026-10-09): its jobs are made
    #  in the root scope even when a popup copy's build starts it - a copy that
    #  closed would otherwise take the hub's time changes with its own jobs.
    with hubcopy.entered(None):
        st["jobs"] = [
            cmds.scriptJob(event=["playbackRangeChanged", _on_range]),
            cmds.scriptJob(event=["playbackRangeSliderChanged", _on_range]),
            cmds.scriptJob(event=["timeChanged", _on_time]),
            cmds.scriptJob(event=["SceneOpened", rescan]),
            cmds.scriptJob(event=["NewSceneOpened", rescan]),
        ]
    st["running"] = True
    rescan()


def stop():
    st = state()
    try:
        import maya.api.OpenMaya as om
        for cb in st.get("callbacks", []):
            try:
                om.MMessage.removeCallback(cb)
            except Exception:
                pass
        for uuid in list(st.get("node_callbacks", {})):
            _unwatch_nodes(uuid)
    except Exception:
        pass
    st["callbacks"] = []
    try:
        import maya.cmds as cmds
        for job in st.get("jobs", []):
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
    except Exception:
        pass
    st["jobs"] = []
    timer = st.get("timer")
    if timer is not None:
        try:
            timer.stop()
            timer.timeout.disconnect()
        except Exception:
            pass
    st["timer"] = None
    st["running"] = False


def rescan(*_):
    from maya_com import network
    st = state()
    for uuid in list(st["tracks"]):
        untrack(uuid)
    st["snapshots"] = {}
    st["live_frames"] = set()
    for group in network.find_all():
        track(group)


def _on_range(*_):
    arm(IDLE_MS)


def _on_time(*_):
    """A tweaked frame's point goes back to the keyed pose once the time has
    really moved. The engine's own walk ends on the frame it started from and
    fires this too - that frame keeps its live point (measured: without the
    check the trail drew the keyed pose under a standing tweak)."""
    st = state()
    if st["live_frames"]:
        try:
            current = int(round(scene().current()))
        except Exception:
            current = None
        gone = {f for f in st["live_frames"] if f != current}
        for tr in st["tracks"].values():
            tr.dirty |= {f for f in gone if tr.span[0] <= f <= tr.span[1]}
        st["live_frames"] -= gone
    arm(IDLE_MS)


def _on_curves(curves, *_):
    st = state()
    import maya.api.OpenMaya as om
    for i in range(len(curves)):
        try:
            st["pending_curves"].add(om.MObjectHandle(curves[i]))
        except Exception:
            pass
    arm(IDLE_MS)


def _absorb_curves(st, groups):
    """Turn the curves edited since the last slice into dirty frames."""
    if not st["pending_curves"]:
        return
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma
    handles, st["pending_curves"] = st["pending_curves"], set()
    unit = om.MTime.uiUnit()
    for handle in handles:
        if not handle.isValid():
            continue
        node = handle.object()
        try:
            fn = oma.MFnAnimCurve(node)
        except Exception:
            continue
        if fn.animCurveType not in TIME_CURVES:
            continue
        owners = _owners(fn, groups)
        name = om.MFnDependencyNode(node).uuid().asString()
        for uuid in owners:
            tr = st["tracks"][uuid]
            after = {f: fn.evaluate(om.MTime(f, unit))
                     for f in frames.frames_of(tr.span)}
            key = (uuid, name)
            before = st["snapshots"].get(key)
            st["snapshots"][key] = after
            tr.dirty |= (frames.changed_frames(before, after) if before is not None
                         else set(after))
            _remember_curve_plug(uuid, fn)


def _owners(fn, groups):
    """The tracks whose character the curve drives - through blend nodes
    too (an animation layer's animBlendNode, a pairBlend), a few hops down."""
    import maya.api.OpenMaya as om
    st = state()
    watched = {uuid: st["node_callbacks"].get(uuid, {}).get("hashes", set())
               for uuid in groups}
    out = []
    try:
        frontier = [fn.findPlug("output", False)]
    except Exception:
        return out
    seen = set()
    for _ in range(4):
        nxt = []
        for plug in frontier:
            for dest in plug.connectedTo(False, True):
                node = dest.node()
                code = om.MObjectHandle(node).hashCode()
                if code in seen:
                    continue
                seen.add(code)
                hit = False
                for uuid, codes in watched.items():
                    if code in codes:
                        hit = True
                        if uuid not in out:
                            out.append(uuid)
                if not hit:
                    dep = om.MFnDependencyNode(node)
                    for name in ("output", "outTranslate", "outRotate"):
                        try:
                            nxt.append(dep.findPlug(name, False))
                        except Exception:
                            pass
        frontier = nxt
        if not frontier:
            break
    return out


# -------------------------------------------- the character's nodes and plugs

def _character_nodes(group):
    """The controls (a rig) or joints (a bare skeleton) whose changes move
    the CoM: node names."""
    import maya.cmds as cmds
    from maya_com import network
    import maya_rigs
    root = network.root_of(group)
    if not root:
        return []
    rig = maya_rigs.rig_of(root, maya_rigs.rigs())
    nodes = []
    if rig:
        for member in cmds.ls(cmds.sets(rig.control_set, q=True) or [], long=True) or []:
            if cmds.listRelatives(member, shapes=True, type="nurbsCurve"):
                nodes.append(member)
    nodes.extend(network.joints_of(root))
    return nodes


def _watch_nodes(uuid, group):
    import maya.api.OpenMaya as om
    import maya.cmds as cmds
    st = state()
    ids, hashes = [], set()
    for path in _character_nodes(group):
        sel = om.MSelectionList()
        try:
            sel.add(path)
        except Exception:
            continue
        obj = sel.getDependNode(0)
        hashes.add(om.MObjectHandle(obj).hashCode())
        ids.append(om.MNodeMessage.addAttributeChangedCallback(
            obj, _on_attribute, uuid))
    st["node_callbacks"][uuid] = {"ids": ids, "hashes": hashes, "curve_plugs": {}}
    _gather_curve_plugs(uuid, group)


def _unwatch_nodes(uuid):
    st = state()
    entry = st["node_callbacks"].pop(uuid, None)
    if not entry:
        return
    try:
        import maya.api.OpenMaya as om
        for cb in entry["ids"]:
            try:
                om.MMessage.removeCallback(cb)
            except Exception:
                pass
    except Exception:
        pass


def _gather_curve_plugs(uuid, group):
    """Every curve-driven plug of the character: what a tweak can be on."""
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma
    entry = state()["node_callbacks"][uuid]
    for path in _character_nodes(group):
        sel = om.MSelectionList()
        try:
            sel.add(path)
        except Exception:
            continue
        fn = om.MFnDependencyNode(sel.getDependNode(0))
        for plug in fn.getConnections():
            if not plug.isDestination:
                continue
            src = plug.source()
            if src.isNull or not src.node().hasFn(om.MFn.kAnimCurve):
                continue
            try:
                if oma.MFnAnimCurve(src.node()).animCurveType not in TIME_CURVES:
                    continue
            except Exception:
                continue
            entry["curve_plugs"][plug.name()] = (plug, src.node())


def _remember_curve_plug(uuid, fn):
    import maya.api.OpenMaya as om
    entry = state()["node_callbacks"].get(uuid)
    if not entry:
        return
    try:
        for dest in fn.findPlug("output", False).connectedTo(False, True):
            entry["curve_plugs"][dest.name()] = (dest, fn.object())
    except Exception:
        pass


def _curve_plugs(st, groups):
    out = []
    for uuid in groups:
        entry = st["node_callbacks"].get(uuid)
        if entry:
            out.extend(entry["curve_plugs"].values())
    return out


def _snapshot_curves(uuid, group, span):
    """Every time curve of the character sampled over the span, so a later
    edit dirties only the frames it changed."""
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma
    st = state()
    unit = om.MTime.uiUnit()
    entry = st["node_callbacks"].get(uuid, {})
    seen = set()
    for plug, curve in entry.get("curve_plugs", {}).values():
        fn = oma.MFnAnimCurve(curve)
        name = om.MFnDependencyNode(curve).uuid().asString()
        if name in seen:
            continue
        seen.add(name)
        st["snapshots"][(uuid, name)] = {f: fn.evaluate(om.MTime(f, unit))
                                         for f in frames.frames_of(span)}


def _on_attribute(msg, plug, other, uuid):
    import maya.api.OpenMaya as om
    if not (msg & om.MNodeMessage.kAttributeSet):
        return
    st = state()
    tr = st["tracks"].get(uuid)
    if tr is None:
        return
    try:
        driven = plug.isDestination
    except Exception:
        driven = False
    if driven:
        st["live"] = True            # a tweak: this frame only, at once
        arm(LIVE_MS)
    else:
        tr.dirty_all()               # a static value: every frame
        st["live"] = True
        arm(IDLE_MS)
