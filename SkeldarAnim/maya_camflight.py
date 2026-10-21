"""maya_camflight - Space's camera menu flies to the chosen camera (2026-10-21).

The animator: «переключение между камерами при использование нашего меню не мгновенное а с
анимацией ... скрипт создает подмену камеры и анимирует 0.3 сек полет от камеры персонажа в
перспективу». Asked, both the recommendation: Top / Side / Front are flattened into smoothly, and
the flight orbits what is looked at.

`fly(panel, target)` puts a substitute camera in the panel standing as the panel's view stands,
flies it 0.3 s to stand as `target` (`maya_camflight_rules`), then the panel looks through
`target` and the substitute goes. True when a flight took the switch over; False when the caller
switches at once (Interface animations off, not a camera, the camera already shown, a failure).

- `Flights` is the state machine, over a scene object and a clock (the tests give fakes);
  `MayaScene` is Maya's half. One flight a panel; both ends are read again every tick, so an
  animated camera is followed; a new target mid-flight starts from where the substitute stands.
- The driver: a 16 ms Qt timer while a flight runs, and a time-change callback, since playback
  turns no timer (trap 269). The wall clock decides, so a slow viewport drops frames, never
  stretches the flight.
- The substitute `:skeldarCameraFlight` (marked `skeldarCameraFlight`, hidden in the Outliner, not
  renderable) is made and deleted with the undo queue off and moved through the API: no undo
  step, no autoKey. A scene that was clean when the first flight began is clean after the last.
  The first flight sweeps away any substitute a crash or a mid-flight save left in the scene.
- State on `sys._skeldar_camflight` (trap 111).
"""

import contextlib
import sys
import time
import traceback

import maya_camflight_rules as rules

FILM_FIT_VERTICAL = 2
TICK_MS = 16


class _Flight(object):
    def __init__(self, panel, source, target, sub, start):
        self.panel = panel
        self.source = source            # ("camera", path) read live, or ("view", View) frozen
        self.target = target
        self.sub = sub
        self.start = start


class Flights(object):
    """Every flight in the air, over `scene` (see MayaScene) and `clock` (seconds)."""

    def __init__(self, scene, clock=time.perf_counter, duration=rules.FLIGHT_S):
        self.scene = scene
        self.clock = clock
        self.duration = duration
        self.flights = {}
        self.clean = False

    # ---------------------------------------------------------------- starting

    def fly(self, panel, target):
        scene = self.scene
        flight = self.flights.get(panel)
        if flight is not None and flight.target == target:
            return True
        if not scene.animated():
            return self._abandon(panel, target)
        aspect = scene.aspect(panel)
        if scene.view(target, aspect) is None:
            return self._abandon(panel, target)
        now = self.clock()
        if flight is not None:
            here = self._view_at(flight, now, aspect)
            if here is None:
                return self._abandon(panel, target)
            flight.source, flight.target, flight.start = ("view", here), target, now
            return True
        shown = scene.shown(panel)
        if not shown or shown == target:
            return False
        start = scene.view(shown, aspect)
        if start is None:
            return False
        # a stale substitute shown (its flight lost to a reload) is read now: the sweep takes it
        source = ("view", start) if scene.is_sub(shown) else ("camera", shown)
        if not self.flights:
            self.clean = not scene.modified()
            try:
                scene.sweep()                    # a substitute a crash or a save left behind
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
        sub = None
        try:
            sub = scene.make_sub()
            flight = _Flight(panel, source, target, sub, now)
            scene.place(sub, rules.shot(self._view_at(flight, now, aspect)), aspect)
            scene.look(panel, sub)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            if sub is not None:
                self._drop(sub)
            try:
                back = shown if scene.exists(shown) else target
                if scene.shown(panel) != back:
                    scene.look(panel, back)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
            return False
        self.flights[panel] = flight
        return True

    def _abandon(self, panel, target):
        """No flight to `target`: one already in the air in that panel lands there."""
        if panel in self.flights:
            self._end(self.flights.pop(panel), target)
        return False

    # ---------------------------------------------------------------- the air

    def _source_view(self, flight, aspect):
        kind, value = flight.source
        if kind == "view":
            return value
        return self.scene.view(value, aspect)

    def _view_at(self, flight, now, aspect):
        a = self._source_view(flight, aspect)
        b = self.scene.view(flight.target, aspect)
        if a is None or b is None:
            return None
        u = rules.ease(rules.progress(now - flight.start, self.duration))
        return rules.blend(a, b, u)

    def tick(self):
        """Move every flight on; True while any is still in the air."""
        now = self.clock()
        for panel in list(self.flights):
            flight = self.flights[panel]
            scene = self.scene
            if not scene.panel_alive(panel) or not scene.exists(flight.sub):
                self.flights.pop(panel)
                self._end(flight, None)
                continue
            if rules.progress(now - flight.start, self.duration) >= 1.0:
                self.flights.pop(panel)
                self._end(flight, flight.target)
                continue
            try:
                aspect = scene.aspect(panel)
                view = self._view_at(flight, now, aspect)
                if view is None:
                    self.flights.pop(panel)
                    self._end(flight, self._landing(flight))
                    continue
                scene.place(flight.sub, rules.shot(view), aspect)
                scene.refresh(panel)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                self.flights.pop(panel, None)
                self._end(flight, flight.target)
        return bool(self.flights)

    def _landing(self, flight):
        """Where a flight whose end is gone lands: the target, else a live source, else persp."""
        scene = self.scene
        if scene.exists(flight.target):
            return flight.target
        kind, value = flight.source
        if kind == "camera" and scene.exists(value):
            return value
        return "persp"

    # ---------------------------------------------------------------- landing

    def _end(self, flight, land):
        scene = self.scene
        try:
            if land and scene.panel_alive(flight.panel) and scene.exists(land):
                scene.look(flight.panel, land)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
        self._drop(flight.sub)
        if not self.flights and self.clean:
            try:
                scene.set_clean()
            except Exception:                                # noqa: BLE001
                pass

    def _drop(self, sub):
        try:
            self.scene.drop(sub)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()

    def stop_all(self):
        """Every flight lands on its target at once."""
        for panel in list(self.flights):
            flight = self.flights.pop(panel)
            self._end(flight, flight.target)

    def target_of(self, panel):
        flight = self.flights.get(panel)
        return flight.target if flight is not None else None


# ------------------------------------------------------------------ Maya's half

def _cmds():
    import maya.cmds as cmds
    return cmds


@contextlib.contextmanager
def _unrecorded():
    cmds = _cmds()
    was = bool(cmds.undoInfo(query=True, state=True))
    if was:
        cmds.undoInfo(stateWithoutFlush=False)
    try:
        yield
    finally:
        if was:
            cmds.undoInfo(stateWithoutFlush=True)


def _dag(node):
    import maya.api.OpenMaya as om
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


class MayaScene(object):
    def animated(self):
        try:
            import maya_hubmotion
            if not maya_hubmotion.enabled():
                return False
        except Exception:                                    # noqa: BLE001
            pass
        try:
            import maya_hubqt
            return bool(maya_hubqt.available())
        except Exception:                                    # noqa: BLE001
            return False

    def view(self, cam, aspect):
        import maya.api.OpenMaya as om
        try:
            path = _dag(cam)
            shape = om.MDagPath(path)
            if not shape.hasFn(om.MFn.kCamera):
                shape.extendToShape()
            if not shape.hasFn(om.MFn.kCamera):
                return None
            fn = om.MFnCamera(shape)
            matrix = list(shape.inclusiveMatrix())
            frustum = fn.getViewingFrustum(aspect, True, True, True)
            return rules.view_of(matrix, frustum, fn.nearClippingPlane, fn.farClippingPlane,
                                 fn.centerOfInterest, fn.isOrtho())
        except Exception:                                    # noqa: BLE001
            return None

    def shown(self, panel):
        cmds = _cmds()
        try:
            cam = cmds.modelPanel(panel, query=True, camera=True) or ""
        except Exception:                                    # noqa: BLE001
            return ""
        if cam and cmds.objExists(cam) and cmds.objectType(cam, isAType="camera"):
            cam = (cmds.listRelatives(cam, parent=True, fullPath=True) or [cam])[0]
        found = (cmds.ls(cam, long=True) or []) if cam else []
        return found[0] if found else cam

    def look(self, panel, cam):
        with _unrecorded():
            _cmds().lookThru(panel, cam)

    def aspect(self, panel):
        try:
            import maya.api.OpenMayaUI as omui
            view = omui.M3dView.getM3dViewFromModelPanel(panel)
            w, h = view.portWidth(), view.portHeight()
            if w > 0 and h > 0:
                return float(w) / float(h)
        except Exception:                                    # noqa: BLE001
            pass
        return 16.0 / 9.0

    def make_sub(self):
        cmds = _cmds()
        with _unrecorded():
            made = cmds.camera()
            top, shape = made[0], made[1]
            try:
                top = cmds.rename(top, rules.SUB_NAME)
                shape = (cmds.listRelatives(top, shapes=True, fullPath=True) or [shape])[0]
                shape = cmds.rename(shape, rules.SUB_NAME + "Shape")
                cmds.addAttr(top, longName=rules.MARKER, attributeType="bool", defaultValue=True)
                cmds.setAttr(top + ".hiddenInOutliner", True)
                cmds.setAttr(shape + ".renderable", False)
                cmds.setAttr(shape + ".filmFit", FILM_FIT_VERTICAL)
                cmds.setAttr(shape + ".overscan", 1.0)
                cmds.setAttr(shape + ".panZoomEnabled", False)
            except Exception:
                cmds.delete(top)
                raise
        return (cmds.ls(top, long=True) or [top])[0]

    def place(self, sub, shot, aspect):
        import maya.api.OpenMaya as om
        path = _dag(sub)
        om.MFnTransform(path).setTransformation(
            om.MTransformationMatrix(om.MMatrix(shot.matrix)))
        shape = om.MDagPath(path)
        shape.extendToShape()
        node = om.MFnDependencyNode(shape.node())
        lens = rules.lens(shot.tan, shot.ox, shot.oy, aspect)
        for attr, value in (("verticalFilmAperture", lens["vertical"]),
                            ("horizontalFilmAperture", lens["horizontal"]),
                            ("focalLength", lens["focal"]),
                            ("horizontalFilmOffset", lens["hoffset"]),
                            ("verticalFilmOffset", lens["voffset"]),
                            ("farClipPlane", shot.far),
                            ("nearClipPlane", shot.near)):
            node.findPlug(attr, False).setDouble(value)

    def drop(self, sub):
        cmds = _cmds()
        if cmds.objExists(sub):
            with _unrecorded():
                cmds.delete(sub)

    def is_sub(self, node):
        try:
            return bool(_cmds().objExists(node + "." + rules.MARKER))
        except Exception:                                    # noqa: BLE001
            return False

    def sweep(self):
        """Delete every substitute standing (none is in the air when this is asked)."""
        cmds = _cmds()
        left = cmds.ls("*." + rules.MARKER, recursive=True, objectsOnly=True, long=True) or []
        if left:
            with _unrecorded():
                cmds.delete(left)

    def exists(self, node):
        try:
            return bool(_cmds().objExists(node))
        except Exception:                                    # noqa: BLE001
            return False

    def panel_alive(self, panel):
        try:
            return bool(_cmds().modelPanel(panel, exists=True))
        except Exception:                                    # noqa: BLE001
            return False

    def refresh(self, panel):
        try:
            import maya.api.OpenMayaUI as omui
            omui.M3dView.getM3dViewFromModelPanel(panel).refresh(False, True)
        except Exception:                                    # noqa: BLE001
            pass

    def modified(self):
        return bool(_cmds().file(query=True, modified=True))

    def set_clean(self):
        _cmds().file(modified=False)


# ------------------------------------------------------------------- the driver

def _state():
    st = getattr(sys, "_skeldar_camflight", None)
    if st is None:
        st = {"flights": None, "timer": None, "callback": None}
        sys._skeldar_camflight = st
    return st


def flights():
    st = _state()
    current = st["flights"]
    if not isinstance(current, Flights):                     # made by an older module (trap 226)
        if current is not None:
            try:
                current.stop_all()
            except Exception:                                # noqa: BLE001
                pass
        current = Flights(MayaScene())
        st["flights"] = current
    return current


def fly(panel, target):
    """Fly `panel` to `target`; True when a flight took the switch over."""
    try:
        took = flights().fly(panel, target)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return False
    if took:
        try:
            _drive()
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            flights().stop_all()
    return took


def target_of(panel):
    """The camera a flight in `panel` is going to, else None."""
    st = _state()
    current = st["flights"]
    try:
        return current.target_of(panel) if current is not None else None
    except Exception:                                        # noqa: BLE001
        return None


def _slot(*_args):
    """The timer's and the time callback's call: always the module standing now."""
    import maya_camflight
    maya_camflight._tick()


def _drive():
    st = _state()
    if st["timer"] is None:
        import maya_hubqt
        q = maya_hubqt.qt()
        timer = q.QtCore.QTimer()
        timer.setInterval(TICK_MS)
        timer.timeout.connect(_slot)
        st["timer"] = timer
    if not st["timer"].isActive():
        st["timer"].start()
    if st["callback"] is None:
        try:
            import maya.api.OpenMaya as om
            st["callback"] = om.MDGMessage.addTimeChangeCallback(_slot)
        except Exception:                                    # noqa: BLE001
            st["callback"] = None


def _tick():
    try:
        active = flights().tick()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        active = False
    if not active:
        _stop()


def _stop():
    st = _state()
    timer = st["timer"]
    if timer is not None:
        try:
            timer.stop()
        except Exception:                                    # noqa: BLE001
            st["timer"] = None
    callback = st["callback"]
    st["callback"] = None
    if callback is not None:
        try:
            import maya.api.OpenMaya as om
            om.MMessage.removeCallback(callback)
        except Exception:                                    # noqa: BLE001
            pass
