"""The AT bar's motion trails (2026-11-05): our own points on Maya's motionTrailShape.

«дуже тормозить сцена ... це все через моушен трейл з АТ ... переписати цю функцію трейлів щоб таких проблем
не виникало більше», and «дугу потрібно постійно бачити». Maya's `snapshot -motionTrail` re-evaluates the rig
through a DG time context for every trail frame after every key edit: with a 63-frame trail on a dagger,
moving FKWrist_R with Auto Key cost 1.3 s a change (20 ms without the trail; measured live). The same frame
through the parallel EM costs 8.7 ms there. So, as maya_com's engine does for the CoM:

- nothing is computed in a callback - callbacks only mark frames DIRTY: after any curve change every time
  curve is sampled again over the trails' spans (1172 curves x 63 frames: 6 ms) and the frames whose value
  moved are dirty; a value set on an unkeyed channel of the character dirties every frame;
- the dirty frames are walked nearest the current frame first, in slices of SLICE_MS on a Qt timer under
  `refresh -suspend`, never while a mouse button is down or the timeline plays; unkeyed tweaks are put
  back after a walk;
- a tweak moves the current frame's point at once (LIVE_MS);
- a trail on a hidden object (a scene tab not shown) is not walked until it shows.

State lives on `sys._skeldar_attrail` (trap 111).
"""

import sys
import time

from maya_com import frames

SLICE_MS = 40.0
IDLE_MS = 0
WAIT_MS = 120
LIVE_MS = 15
TIME_CURVES = (0, 1, 2, 3)          # MFnAnimCurve TL, TA, TT, TU: time-driven
SPAN_ATTR = "skeldarATTrailSpan"    # "start end" on the handle
MAX_WATCHED = 3000


def state():
    st = getattr(sys, "_skeldar_attrail", None)
    if st is None:
        st = {}
        sys._skeldar_attrail = st
    for key, default in (("tracks", {}), ("callbacks", []), ("node_callbacks", {}), ("jobs", []),
                         ("timer", None), ("snapshot", {}), ("snap_span", None), ("check_curves", False),
                         ("live", False), ("live_frames", set()), ("per_frame_ms", 9.0), ("busy", False),
                         ("running", False), ("stats", {"walked": 0, "slices": 0, "longest_ms": 0.0})):
        st.setdefault(key, default)
    return st


# ------------------------------------------------------------------ pure

def span_text(span):
    return "%d %d" % (int(span[0]), int(span[1]))


def parse_span(text):
    """(start, end) from "start end", None for anything else. Pure."""
    try:
        a, b = (int(round(float(v))) for v in str(text).split())
    except (TypeError, ValueError):
        return None
    return (min(a, b), max(a, b))


def union_span(spans):
    spans = [s for s in spans if s]
    if not spans:
        return None
    return (min(s[0] for s in spans), max(s[1] for s in spans))


def pivot_point(rotate_pivot, matrix):
    """The object's rotate pivot in world space: the pivot (object space) times its world matrix, row
    vectors, as `xform -q -ws -rp` reads it - where Maya's own trail stood (measured: equal on DaggerMesh).
    Pure."""
    x, y, z = rotate_pivot
    m = matrix
    return (x * m[0] + y * m[4] + z * m[8] + m[12],
            x * m[1] + y * m[5] + z * m[9] + m[13],
            x * m[2] + y * m[6] + z * m[10] + m[14])


def shown(chain):
    """True when nothing in `chain` ([(visibility, lodVisibility, overrideEnabled, overrideVisibility)],
    the object and its parents) hides it. Pure."""
    for vis, lod, override, override_vis in chain:
        if not vis or not lod or (override and not override_vis):
            return False
    return True


def curve_changes(before, after):
    """{frame} whose value changed between two {curve: {frame: value}} samples; a curve new or gone
    changes every frame it has. Pure."""
    out = set()
    for name in set(before) | set(after):
        a, b = before.get(name), after.get(name)
        if a is None or b is None:
            out |= set(a or b or {})
        else:
            out |= frames.changed_frames(a, b)
    return out


class Track(object):
    """One trail: its handle and object (by UUID), its frames, their points and the dirty ones."""

    def __init__(self, handle, target, span):
        self.handle = handle
        self.target = target
        self.span = span
        self.points = {}
        self.dirty = set(frames.frames_of(span))

    def dirty_all(self):
        self.dirty = set(frames.frames_of(self.span))


# ------------------------------------------------------------------ the scene seam

class Scene(object):
    """Everything the engine asks Maya. A test hands in its own."""

    def __init__(self):
        import maya.api.OpenMaya as om
        import maya.api.OpenMayaAnim as oma
        import maya.cmds as cmds
        self.cmds, self.om, self.oma = cmds, om, oma

    def current(self):
        return self.cmds.currentTime(query=True)

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

    def _node(self, uuid):
        nodes = self.cmds.ls(uuid, long=True) or []
        return nodes[0] if nodes else None

    def exists(self, uuid):
        return self._node(uuid) is not None

    def visible(self, uuid):
        node = self._node(uuid)
        if not node:
            return False
        c = self.cmds
        chain, parts = [], node.split("|")
        for i in range(len(parts), 1, -1):
            path = "|".join(parts[:i])
            try:
                chain.append((c.getAttr(path + ".visibility"), c.getAttr(path + ".lodVisibility"),
                              c.getAttr(path + ".overrideEnabled"), c.getAttr(path + ".overrideVisibility")))
            except Exception:
                return False
        return shown(chain)

    def reader(self, uuid):
        """A function reading the object's world pivot now, or None when it is gone."""
        om = self.om
        node = self._node(uuid)
        if not node:
            return None
        sel = om.MSelectionList()
        sel.add(node)
        fn = om.MFnDependencyNode(sel.getDependNode(0))
        world = fn.findPlug("worldMatrix", False).elementByLogicalIndex(0)
        rp = fn.findPlug("rotatePivot", False)
        pivot = tuple(rp.child(i).asDouble() for i in range(3))
        return lambda: pivot_point(pivot, om.MFnMatrixData(world.asMObject()).matrix())

    def walk(self, frame_list, readers):
        """{frame: {key: point}} walking the time through the EM, back to the current frame after."""
        om, oma, cmds = self.om, self.oma, self.cmds
        unit = om.MTime.uiUnit()
        here = oma.MAnimControl.currentTime()
        out = {}
        cmds.refresh(suspend=True)
        try:
            for frame in frame_list:
                oma.MAnimControl.setCurrentTime(om.MTime(frame, unit))
                out[frame] = {key: read() for key, read in readers.items()}
        finally:
            oma.MAnimControl.setCurrentTime(here)
            cmds.refresh(suspend=False)
        return out

    def curves(self, span):
        """{curve UUID: {frame: value}} of every time curve in the scene over `span`."""
        om, oma = self.om, self.oma
        unit = om.MTime.uiUnit()
        times = [(f, om.MTime(f, unit)) for f in frames.frames_of(span)]
        out = {}
        it = om.MItDependencyNodes(om.MFn.kAnimCurve)
        while not it.isDone():
            node = it.thisNode()
            it.next()
            try:
                fn = oma.MFnAnimCurve(node)
                if fn.animCurveType not in TIME_CURVES:
                    continue
                out[om.MFnDependencyNode(node).uuid().asString()] = {f: fn.evaluate(t) for f, t in times}
            except Exception:
                continue
        return out

    def held(self, plugs):
        """[(plug, value)] of the animated plugs now - the values a walk must not take away."""
        out = []
        for plug in plugs:
            try:
                out.append((plug, plug.asDouble()))
            except Exception:
                pass
        return out

    def put_back(self, held):
        """The held values the walk changed (unkeyed tweaks) set again; no undo entry."""
        mod, changed = self.om.MDGModifier(), False
        for plug, value in held:
            try:
                if abs(plug.asDouble() - value) > 1e-9:
                    mod.newPlugValueDouble(plug, value)
                    changed = True
            except Exception:
                pass
        if changed:
            mod.doIt()

    def write(self, uuid, span, points):
        """The handle's trail shape takes the points; no undo entry, the scene's modified flag kept."""
        om, cmds = self.om, self.cmds
        node = self._node(uuid)
        if not node:
            return
        shapes = cmds.listRelatives(node, shapes=True, type="motionTrailShape", fullPath=True) or []
        if not shapes:
            return
        was = cmds.file(query=True, modified=True)
        arr = om.MPointArray()
        for p in frames.ordered_points(points, span):
            arr.append(om.MPoint(p[0], p[1], p[2]))
        sel = om.MSelectionList()
        sel.add(shapes[0])
        fn = om.MFnDependencyNode(sel.getDependNode(0))
        fn.findPlug("points", False).setMObject(om.MFnPointArrayData().create(arr))
        fn.findPlug("startTime", False).setMTime(om.MTime(span[0], om.MTime.uiUnit()))
        if not was:
            cmds.file(modified=False)


SCENE = [None]


def scene():
    if SCENE[0] is None:
        SCENE[0] = Scene()
    return SCENE[0]


# ------------------------------------------------------------------ tracking

def track(handle, target, span):
    st = state()
    tr = st["tracks"].get(handle)
    if tr is None or tr.target != target or tr.span != span:
        tr = Track(handle, target, span)
        st["tracks"][handle] = tr
        _watch(tr)
        arm(IDLE_MS)
    return tr


def untrack(handle):
    state()["tracks"].pop(handle, None)
    _unwatch(handle)


def pending():
    return sum(len(tr.dirty) for tr in state()["tracks"].values())


def dirty_all(handle=None):
    for key, tr in state()["tracks"].items():
        if handle is None or key == handle:
            tr.dirty_all()
    arm(IDLE_MS)


# ------------------------------------------------------------------ the slice

def tick(sc=None):
    """One slice. Returns the number of frames walked."""
    sc = sc or scene()
    st = state()
    if st["busy"]:
        return 0
    st["busy"] = True
    try:
        return _tick(sc, st)
    finally:
        st["busy"] = False


def _absorb_curves(sc, st):
    span = union_span([tr.span for tr in st["tracks"].values()])
    if span is None:
        st["check_curves"] = False
        return
    if span != st["snap_span"]:
        #  a new span is a new baseline: its tracks start all dirty anyway
        st["snapshot"], st["snap_span"], st["check_curves"] = sc.curves(span), span, False
        return
    if not st["check_curves"]:
        return
    st["check_curves"] = False
    after = sc.curves(span)
    changed = curve_changes(st["snapshot"], after)
    st["snapshot"] = after
    for tr in st["tracks"].values():
        tr.dirty |= {f for f in changed if tr.span[0] <= f <= tr.span[1]}


def _tick(sc, st):
    for handle in list(st["tracks"]):
        tr = st["tracks"][handle]
        if not sc.exists(handle) or not sc.exists(tr.target):
            untrack(handle)
    if not st["tracks"]:
        return 0
    _absorb_curves(sc, st)
    shown_tracks = {h: tr for h, tr in st["tracks"].items() if sc.visible(h)}
    readers = {}
    for h, tr in shown_tracks.items():
        read = sc.reader(tr.target)
        if read is not None:
            readers[h] = read
    current = int(round(sc.current()))
    touched = set()
    if st["live"]:
        st["live"] = False
        for h, read in readers.items():
            tr = st["tracks"][h]
            if tr.span[0] <= current <= tr.span[1]:
                tr.points[current] = read()
                tr.dirty.discard(current)
                st["live_frames"].add(current)
                touched.add(h)
    work = set()
    for h in readers:
        work |= st["tracks"][h].dirty
    walked = 0
    if work and not sc.mouse_down() and not sc.playing():
        n = frames.budget(st["per_frame_ms"], SLICE_MS, st["per_frame_ms"])
        batch = frames.nearest_first(work, current)[:n]
        held = sc.held(_animated_plugs(st, readers))
        started = time.time()
        try:
            values = sc.walk(batch, readers)
        finally:
            sc.put_back(held)
        spent = (time.time() - started) * 1000.0
        st["per_frame_ms"] = 0.7 * st["per_frame_ms"] + 0.3 * spent / (len(batch) + 1)
        st["stats"]["walked"] += len(batch)
        st["stats"]["slices"] += 1
        st["stats"]["longest_ms"] = max(st["stats"]["longest_ms"], spent)
        for frame, by_handle in values.items():
            for h, point in by_handle.items():
                tr = st["tracks"][h]
                if not tr.span[0] <= frame <= tr.span[1]:
                    continue
                tr.dirty.discard(frame)
                if frame == current and frame in st["live_frames"]:
                    continue                 # the live (tweaked) point wins on its frame
                tr.points[frame] = point
                touched.add(h)
        walked = len(batch)
    for h in touched:
        tr = st["tracks"][h]
        sc.write(h, tr.span, tr.points)
    if any(st["tracks"][h].dirty for h in readers):
        arm(WAIT_MS if (sc.mouse_down() or sc.playing()) else IDLE_MS)
    return walked


def run_until_clean(sc=None, limit=10000):
    sc = sc or scene()
    total = 0
    for _ in range(limit):
        st = state()
        if not pending() and not st["live"] and not st["check_curves"]:
            break
        walked = tick(sc)
        total += walked
        if not walked and not st["live"] and not st["check_curves"]:
            break                            # what is left is hidden or waits for the mouse
    return total


# ------------------------------------------------------------------ the timer

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
    except Exception as exc:                 # the trail must never spam the UI
        state()["last_error"] = repr(exc)


# ------------------------------------------------------------------ callbacks

def start():
    """Callbacks and jobs, once per module object (a purge's fresh module removes the old one's)."""
    stop()
    st = state()
    import maya.api.OpenMayaAnim as oma
    import maya.cmds as cmds
    import maya_hubcopy as hubcopy
    st["callbacks"] = [oma.MAnimMessage.addAnimCurveEditedCallback(_on_curves)]
    with hubcopy.entered(None):
        st["jobs"] = [cmds.scriptJob(event=[event, fn]) for event, fn in (
            ("timeChanged", _on_time), ("Undo", _on_curves), ("Redo", _on_curves),
            ("SceneOpened", _on_scene), ("NewSceneOpened", _on_scene))]
    st["running"] = True


def stop():
    st = state()
    try:
        import maya.api.OpenMaya as om
        for cb in st.get("callbacks", []):
            try:
                om.MMessage.removeCallback(cb)
            except Exception:
                pass
    except Exception:
        pass
    for handle in list(st.get("node_callbacks", {})):
        _unwatch(handle)
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


def _on_scene(*_):
    st = state()
    for handle in list(st["tracks"]):
        untrack(handle)
    st["snapshot"], st["snap_span"], st["live_frames"] = {}, None, set()


def _on_time(*_):
    """A tweaked frame goes back to the keyed pose once the time has really moved (the engine's own walk
    ends on the frame it started from and fires this too - that frame keeps its live point)."""
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


def _on_curves(*_):
    state()["check_curves"] = True
    arm(IDLE_MS)


# ------------------------------------------------------------------ the character's nodes

def watched_nodes(target):
    """The nodes whose values move the trail's object: the controls (curve-shaped transforms) of the
    object's top namespace - a scene tab or the whole scene - its parents, and the animation layers."""
    import maya.cmds as cmds
    leaf = target.split("|")[-1]
    ns = leaf.split(":")[0] if ":" in leaf else ""
    curves = cmds.ls((ns + ":*") if ns else "*", recursive=True, type="nurbsCurve", long=True) or []
    nodes = list(dict.fromkeys(cmds.listRelatives(curves, parent=True, fullPath=True) or []))
    parts = target.split("|")
    nodes += ["|".join(parts[:i]) for i in range(len(parts), 1, -1)]
    nodes += cmds.ls(type="animLayer") or []
    return list(dict.fromkeys(nodes))[:MAX_WATCHED]


def _watch(tr):
    import maya.api.OpenMaya as om
    import maya.cmds as cmds
    _unwatch(tr.handle)
    target = (cmds.ls(tr.target, long=True) or [None])[0]
    ids, plugs = [], []
    if target:
        for path in watched_nodes(target):
            sel = om.MSelectionList()
            try:
                sel.add(path)
            except Exception:
                continue
            obj = sel.getDependNode(0)
            ids.append(om.MNodeMessage.addAttributeChangedCallback(obj, _on_attribute, tr.handle))
            plugs += _animated(om.MFnDependencyNode(obj))
    state()["node_callbacks"][tr.handle] = {"ids": ids, "plugs": plugs}


def _animated(fn):
    """The node's plugs fed by an animation curve or a layer's blend: what a walk changes and a tweak
    lives on."""
    import maya.api.OpenMaya as om
    out = []
    try:
        conns = fn.getConnections()
    except Exception:
        return out
    for plug in conns:
        if not plug.isDestination:
            continue
        src = plug.source()
        if src.isNull:
            continue
        node = src.node()
        if node.hasFn(om.MFn.kAnimCurve) or "Blend" in om.MFnDependencyNode(node).typeName:
            out.append(plug)
    return out


def _unwatch(handle):
    entry = state()["node_callbacks"].pop(handle, None)
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


def _animated_plugs(st, handles):
    out, seen = [], set()
    for h in handles:
        for plug in st["node_callbacks"].get(h, {}).get("plugs", []):
            try:
                name = plug.name()
            except Exception:
                continue
            if name not in seen:
                seen.add(name)
                out.append(plug)
    return out


def _on_attribute(msg, plug, other, handle):
    import maya.api.OpenMaya as om
    if not (msg & om.MNodeMessage.kAttributeSet):
        return
    st = state()
    tr = st["tracks"].get(handle)
    if tr is None:
        return
    try:
        driven = plug.isDestination
    except Exception:
        driven = False
    st["live"] = True
    if driven:
        arm(LIVE_MS)                         # a tweak: this frame only, at once
    else:
        tr.dirty_all()                       # a static value: every frame
        st["check_curves"] = True
        arm(IDLE_MS)
