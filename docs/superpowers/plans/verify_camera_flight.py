"""Camera flight (2026-10-21), proven in mayapy standalone - never in the animator's scene.

  $env:MAYA_APP_DIR = "$env:TEMP\\claude\\cf_mad"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_camera_flight.py

The cameras, the substitute and every write onto it are Maya's own; only the PANEL is faked (mayapy
has none): which camera it shows, its aspect. 27 points about the subject are projected through
the substitute (with its own frustum for the panel's aspect) and through each end.

Every gate prints PASS/FAIL with its number; the last line is the count.
"""

import math
import os
import sys
import tempfile
import traceback

import maya.standalone

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = r"C:\!!!Work\MayaScripts"
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya_camflight as cf  # noqa: E402
import maya_camflight_rules as rules  # noqa: E402

ASPECT = 1.6
RESULTS = []
POINTS = [(x, y, z) for x in (-60.0, 0.0, 60.0) for y in (30.0, 90.0, 150.0)
          for z in (-60.0, 0.0, 60.0)]


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s %2d %s%s" % ("PASS" if ok else "FAIL", len(RESULTS), name,
                           ("  - " + detail) if detail else ""))


def shape_fn(cam):
    sel = om.MSelectionList()
    sel.add(cam)
    path = sel.getDagPath(0)
    path.extendToShape()
    return path, om.MFnCamera(path)


def project(cam, points=POINTS):
    """Each point's place in the frame, -1..1 across the panel, through `cam`."""
    path, fn = shape_fn(cam)
    inv = path.inclusiveMatrixInverse()
    left, right, bottom, top = fn.getViewingFrustum(ASPECT, True, True, True)
    near = fn.nearClippingPlane
    out = []
    for p in points:
        c = om.MPoint(*p) * inv
        if fn.isOrtho():
            x, y = c.x, c.y
        else:
            x, y = c.x * near / -c.z, c.y * near / -c.z
        out.append(((x - (left + right) / 2.0) / ((right - left) / 2.0),
                    (y - (bottom + top) / 2.0) / ((top - bottom) / 2.0)))
    return out


def apart(a, b):
    return max(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for p, q in zip(a, b))


class Clock(object):
    now = 0.0

    def __call__(self):
        return self.now


class Panel(object):
    """The scene half with Maya's cameras and a fake panel."""

    def __init__(self, shows):
        self.shows = shows
        self.refreshed = 0

    def install(self, scene):
        scene.animated = lambda: True
        scene.shown = lambda panel: self.shows
        scene.look = self.look
        scene.aspect = lambda panel: ASPECT
        scene.panel_alive = lambda panel: True
        scene.refresh = self.refresh
        return scene

    def look(self, panel, cam):
        self.shows = (cmds.ls(cam, long=True) or [cam])[0]

    def refresh(self, panel):
        self.refreshed += 1


def subs():
    return [n for n in (cmds.ls("*.skeldarCameraFlight", recursive=True, objectsOnly=True) or [])]


def flights_from(shows):
    clock = Clock()
    panel = Panel(shows)
    scene = panel.install(cf.MayaScene())
    return cf.Flights(scene, clock, rules.FLIGHT_S), clock, panel


def scene_setup():
    cmds.file(new=True, force=True)
    persp = "|persp"
    cmds.setAttr(persp + ".translate", 300, 200, 500)
    cmds.viewPlace(persp, lookAt=(0, 90, 0))
    cmds.setAttr("|persp|perspShape.centerOfInterest",
                 math.sqrt(300 ** 2 + 110 ** 2 + 500 ** 2))
    cmds.setAttr("|top|topShape.orthographicWidth", 400)
    cam, shape = cmds.camera(name="charCam")
    cam = cmds.ls(cam, long=True)[0]
    cmds.setAttr(shape + ".horizontalFilmAperture", 1.417)
    cmds.setAttr(shape + ".verticalFilmAperture", 1.417 * 9 / 16.0)
    cmds.setAttr(shape + ".filmFit", 1)
    cmds.setAttr(shape + ".focalLength", 15.1)
    cmds.setAttr(shape + ".overscan", 1.3)
    cmds.setAttr(shape + ".horizontalFilmOffset", 0.05)
    cmds.setAttr(shape + ".nearClipPlane", 0.5)
    cmds.setAttr(cam + ".translate", 0, 160, 200)
    cmds.setKeyframe(cam, attribute="translateX", time=0, value=0)
    cmds.setKeyframe(cam, attribute="translateX", time=24, value=50)
    cmds.currentTime(0)
    return persp, "|top", cam


def main():
    persp, top, char = scene_setup()
    path = os.path.join(tempfile.mkdtemp(), "flight.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii")
    gate("the scene starts clean", not cmds.file(query=True, modified=True))
    curves = len(cmds.ls(type="animCurve") or [])
    cmds.undoInfo(state=True)
    cmds.autoKeyframe(state=True)             # itself an (unnamed) undo step: before the marker
    cmds.undoInfo(openChunk=True, chunkName="skeldarUndoMarker")
    cmds.createNode("transform", name="undoMarker")
    cmds.undoInfo(closeChunk=True)
    undo_name = cmds.undoInfo(query=True, undoName=True)
    gate("the undo queue holds a step of ours to watch", undo_name == "skeldarUndoMarker",
         repr(undo_name))
    cmds.file(modified=False)

    # 1. persp -> the character's camera
    flights, clock, panel = flights_from(persp)
    took = flights.fly("modelPanel4", char)
    sub = panel.shows
    gate("the flight takes the switch over", took and sub != persp, sub)
    gate("one substitute, in the root namespace, marked and hidden",
         subs() == ["skeldarCameraFlight"] and cmds.getAttr(sub + ".hiddenInOutliner"),
         str(subs()))
    gate("at the start it shows what persp showed", apart(project(sub), project(persp)) < 1e-5,
         "%.2e" % apart(project(sub), project(persp)))
    worst_axis = 0.0
    for t in (0.05, 0.1, 0.15, 0.2, 0.25):
        clock.now = t
        flights.tick()
        view = flights._view_at(flights.flights["modelPanel4"], t, ASPECT)
        (px, py), = project(sub, [view.pivot])
        _, fn = shape_fn(sub)
        left, right, bottom, top_ = fn.getViewingFrustum(ASPECT, True, True, True)
        axis = (-(left + right) / (right - left), -(bottom + top_) / (top_ - bottom))
        worst_axis = max(worst_axis, abs(px - axis[0]), abs(py - axis[1]))
    gate("mid-flight what is looked at stays on the axis", worst_axis < 1e-5,
         "%.2e" % worst_axis)
    clock.now = rules.FLIGHT_S - 1e-6
    flights.tick()
    end = apart(project(sub), project(char))
    gate("at the end it shows what the character's camera shows (its 16:9 lens, overscan, "
         "film offset)", end < 1e-4, "%.2e" % end)
    gate("the panel was redrawn every tick", panel.refreshed >= 6, str(panel.refreshed))
    clock.now = rules.FLIGHT_S
    alive = flights.tick()
    gate("then the panel looks through the character's camera", not alive and panel.shows == char,
         panel.shows)
    gate("and the substitute is gone", subs() == [] and not cmds.objExists(sub))
    gate("no undo step was made", cmds.undoInfo(query=True, undoName=True) == undo_name,
         repr(cmds.undoInfo(query=True, undoName=True)))
    gate("the clean scene is clean again", not cmds.file(query=True, modified=True))
    gate("autoKey on keyed nothing", len(cmds.ls(type="animCurve") or []) == curves)

    # 2. the character's camera, animated, into Top: flattened
    cmds.currentTime(12)
    flights, clock, panel = flights_from(char)
    flights.fly("modelPanel4", top)
    sub = panel.shows
    start = apart(project(sub), project(char))
    gate("from an animated camera it starts where that camera stands now", start < 1e-4,
         "%.2e" % start)
    clock.now = rules.FLIGHT_S - 1e-6
    flights.tick()
    flat = apart(project(sub), project(top))
    gate("into Top the picture is flat: under 0.5 % of the frame from the ortho view",
         flat < 0.01, "%.4f" % flat)
    _, fn = shape_fn(sub)
    d = math.dist(cmds.xform(sub, query=True, worldSpace=True, translation=True), (0, 0, 0))
    gate("its depth keeps Top's clip range about the pivot",
         fn.nearClippingPlane < d - 150 and fn.farClippingPlane > d + 30,
         "near %.0f far %.0f at %.0f" % (fn.nearClippingPlane, fn.farClippingPlane, d))
    clock.now = rules.FLIGHT_S
    flights.tick()
    gate("Top shown, nothing left", panel.shows == top and subs() == [])

    # 3. out of Top, and a new target mid-flight
    flights, clock, panel = flights_from(top)
    flights.fly("modelPanel4", persp)
    sub = panel.shows
    out = apart(project(sub), project(top))
    gate("out of Top it starts flat", out < 0.01, "%.4f" % out)
    clock.now = 0.15
    flights.tick()
    here = project(sub)
    flights.fly("modelPanel4", char)
    gate("a new target mid-flight keeps the one substitute", subs() == ["skeldarCameraFlight"])
    flights.tick()
    gate("and starts from where it stood", apart(project(sub), here) < 1e-5,
         "%.2e" % apart(project(sub), here))
    clock.now = 0.15 + rules.FLIGHT_S + 1e-9
    flights.tick()
    gate("then lands on the new target", panel.shows == char and subs() == [],
         "%s %s" % (panel.shows, subs()))

    # 4. the time callback drives it (playback turns no timer)
    flights, clock, panel = flights_from(persp)
    saved = cf.flights
    cf.flights = lambda: flights
    st = cf._state()

    class Timer(object):
        active = False

        def isActive(self):
            return self.active

        def start(self):
            self.active = True

        def stop(self):
            self.active = False

    st["timer"], st["callback"] = Timer(), None
    try:
        flights.fly("modelPanel4", char)
        cf._drive()
        before = panel.refreshed
        clock.now = 0.1
        cmds.currentTime(13)
        gate("a time change moves the flight on", panel.refreshed > before and st["callback"],
             "%d -> %d" % (before, panel.refreshed))
        clock.now = rules.FLIGHT_S
        cmds.currentTime(14)
        gate("and the last one lands it and lets the callback go",
             panel.shows == char and st["callback"] is None and not st["timer"].active
             and subs() == [])
    finally:
        cf.flights = saved
        cf._stop()
        st["timer"] = None

    # 5. a modified scene stays modified; a scene tab's namespace
    cmds.setAttr(char + ".translateY", 170)
    gate("the scene is modified by hand", cmds.file(query=True, modified=True))
    if not cmds.namespace(exists=":tab_x"):
        cmds.namespace(add=":tab_x")
    cmds.namespace(setNamespace=":tab_x")
    flights, clock, panel = flights_from(persp)
    flights.fly("modelPanel4", char)
    gate("the substitute stands in the root namespace while a tab's is current",
         panel.shows == "|skeldarCameraFlight", panel.shows)
    clock.now = rules.FLIGHT_S
    flights.tick()
    cmds.namespace(setNamespace=":")
    gate("a modified scene stays modified", cmds.file(query=True, modified=True))

    # 6. a substitute left behind (a crash, a save mid-flight) is swept by the next flight
    stale = cmds.camera()[0]
    cmds.addAttr(stale, longName=rules.MARKER, attributeType="bool", defaultValue=True)
    flights, clock, panel = flights_from(persp)
    flights.fly("modelPanel4", char)
    gate("the next flight sweeps a stale substitute away",
         subs() == ["skeldarCameraFlight"] and not cmds.objExists(stale), str(subs()))
    clock.now = rules.FLIGHT_S
    flights.tick()

    # 7. Interface animations off
    cmds.optionVar(intValue=("skeldarAnimHub_animations", 0))
    gate("with Interface animations off Maya's half says no flight",
         not cf.MayaScene().animated())
    cmds.optionVar(remove="skeldarAnimHub_animations")

    print("%d of %d gates failed" % (RESULTS.count(False), len(RESULTS)))


try:
    main()
except Exception:
    traceback.print_exc()
    print("verify died after %d gates" % len(RESULTS))
