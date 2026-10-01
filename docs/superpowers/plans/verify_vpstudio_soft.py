"""Live verification for Viewport Studio's Soft Studio look (2026-10-01).

Meant for a DISPOSABLE GUI Maya (scratch MAYA_APP_DIR, MAYA_NO_HOME=1): it
needs a model panel and playblast. Adaptive about the scene: with no mesh in
it, it adds a textured Manny skeleton and deletes it at the end; with meshes,
it lights those and creates nothing but its camera. Every node it creates is
registered by UUID as it is created; the panel's camera, the frame, autoKey
and the selection go back as found.

What it proves (spec 2026-10-01-vpstudio-soft-studio-design.md):
- six lights, the key's and the back lights' cones three times Studio's pool,
  the look's falloff, the doubled shadow map;
- warm in front of the subject as the camera sees it, cold behind;
- ONE cyclorama under the group (not the light pivot), its wall 4.5 radii
  behind the subject from the camera, every face facing the subject, soft
  edges, shadow catcher flags, a warm matte blinn;
- the Rotate dial turns the lights and leaves the paper;
- Studio <-> Soft Studio leaves nothing behind; Restore takes it all;
- the frame time, and playblasts to look at (front, three-quarter, and a
  wall pixel warm in the picture).
"""

import math
import os
import sys
import time

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)
for _key in list(sys.modules):
    if _key.split(".")[0] in ("maya_vpstudio", "maya_scenesetup",
                              "maya_hubstyle", "maya_rigs"):
        del sys.modules[_key]

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_vpstudio as v

SOFT = "Soft Studio"
SHOTS = os.environ.get("VPSOFT_SHOTS", r"C:\Users\MYPC~1\AppData\Local\Temp")
CAM = "vpSoftVerifyCam"

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("%-4s %-60s %s" % ("PASS" if ok else "FAIL", name, detail))
    return bool(ok)


def near(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol


def settle(n=3):
    """Viewport 2.0 loads textures only while Maya is idle (trap 120)."""
    import maya.utils
    from PySide6 import QtWidgets
    for _ in range(n):
        maya.utils.processIdleEvents()
        QtWidgets.QApplication.processEvents()
        cmds.refresh(force=True)
        time.sleep(0.25)


def blast(path):
    """Blast until two blasts agree, after at least three (trap 120)."""
    last = None
    for i in range(12):
        settle()
        cmds.playblast(
            frame=[cmds.currentTime(query=True)], format="image",
            compression="png", completeFilename=path, widthHeight=(1280, 720),
            percent=100, viewer=False, offScreen=True, showOrnaments=False,
            forceOverwrite=True, quality=100)
        data = open(path, "rb").read()
        if i >= 2 and data == last:
            break
        last = data
    return path


def world_pos(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def world_matrix(node):
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def shape_of(node):
    return (cmds.listRelatives(node, shapes=True, fullPath=True) or [None])[0]


def index_paths(rig):
    return {name: v.resolve(uuid) for name, uuid in v.read_index(rig).items()}


def place_camera(azimuth, frame, meshes):
    """Our camera at `azimuth` around the subject, framing its meshes."""
    centre = frame["centre"]
    distance = 3.4 * frame["radius"]
    az = math.radians(azimuth)
    cmds.xform(CAM, worldSpace=True, translation=(
        centre[0] + distance * math.sin(az),
        centre[1] + 0.12 * frame["height"],
        centre[2] + distance * math.cos(az)))
    cmds.viewLookAt(CAM, position=centre)
    if meshes:
        cmds.select(meshes, replace=True)
        cmds.viewFit(CAM, fitFactor=0.82)
        cmds.select(clear=True)


def pixel(path, fx, fy, size=9):
    """The mean RGB (0..1) of a size x size patch at a fraction of the image."""
    from PySide6 import QtGui
    image = QtGui.QImage(path)
    x0 = int(fx * image.width()) - size // 2
    y0 = int(fy * image.height()) - size // 2
    total = [0.0, 0.0, 0.0]
    for dy in range(size):
        for dx in range(size):
            c = image.pixelColor(x0 + dx, y0 + dy)
            total[0] += c.redF()
            total[1] += c.greenF()
            total[2] += c.blueF()
    n = float(size * size)
    return tuple(t / n for t in total)


print("module under test:", v.__file__)

was_frame = cmds.currentTime(query=True)
was_autokey = cmds.autoKeyframe(query=True, state=True)
was_selection = cmds.ls(selection=True, long=True) or []
panel = v.active_panel()
was_camera = cmds.modelEditor(panel, query=True, camera=True)
made = []

try:
    # --- the subject -------------------------------------------------------
    meshes = [cmds.listRelatives(m, parent=True, fullPath=True)[0]
              for m in (cmds.ls(type="mesh", long=True, noIntermediate=True)
                        or [])]
    if v.find_rig():
        meshes = [m for m in meshes if not v._under(m, v.find_rig())]
    if not meshes:
        from maya_scenesetup import catalog, character
        before = set(cmds.ls(cmds.ls(), uuid=True) or [])
        print("added:", character.add_character(catalog.default_character()))
        made += sorted(set(cmds.ls(cmds.ls(), uuid=True) or []) - before)
        meshes = [cmds.listRelatives(m, parent=True, fullPath=True)[0]
                  for m in (cmds.ls(type="mesh", long=True,
                                    noIntermediate=True) or [])]
    cam = CAM = cmds.camera(name=CAM, focalLength=45.0)[0]
    made += cmds.ls(cam, uuid=True)
    cmds.lookThru(panel, cam)

    frame = v.subject_frame(v.subject_bbox(rig=None))
    radius = frame["radius"]
    print("subject: %.1f cm tall, radius %.1f" % (frame["height"], radius))

    # --- the press, from the front ------------------------------------------
    place_camera(0.0, frame, meshes)
    said = v.setup({"look": SOFT, "quality": "Good"})
    print("setup said:", said)
    rig = v.find_rig()
    gate("the press builds a rig and names the cyclorama",
         bool(rig) and "cyclorama" in said and said.startswith(SOFT), said)
    gate("no render setting was unavailable", "unavailable" not in said)

    lights = index_paths(rig)
    gate("six lights, all in the index",
         sorted(lights) == sorted(v.light_names(SOFT))
         and all(lights.values()), str(sorted(lights)))
    shapes = {n: shape_of(p) for n, p in lights.items()}

    studio_plan = {e["name"]: e for e in v.light_plan(frame, 0.0,
                                                      {"look": "Studio"})}
    for name, studio_name in (("key", "key"), ("rim", "rim"),
                              ("kicker", "rim")):
        cone = cmds.getAttr(shapes[name] + ".coneAngle")
        ratio = (math.tan(math.radians(cone / 2.0))
                 / math.tan(math.radians(
                     studio_plan["VPStudio_" + studio_name]["cone"] / 2.0)))
        gate("the %s's pool is three times Studio's %s's" % (name,
                                                              studio_name),
             near(ratio, 3.0, 1e-4), "cone %.2f deg, x%.5f" % (cone, ratio))
        gate("its falloff is the look's (penumbra 20, dropoff 1.3)",
             near(cmds.getAttr(shapes[name] + ".penumbraAngle"), 20.0)
             and near(cmds.getAttr(shapes[name] + ".dropoff"), 1.3))
    key = shapes["key"]
    gate("the key alone casts, from a 4096 map",
         cmds.getAttr(key + ".useDepthMapShadows") == 1
         and cmds.getAttr(key + ".dmapResolution") == 4096
         and not any(cmds.getAttr(s + ".useDepthMapShadows")
                     for n, s in shapes.items()
                     if n != "key"
                     and cmds.objExists(s + ".useDepthMapShadows")))
    gate("no light throws a ray-traced shadow (Viewport 2.0 draws those)",
         not any(cmds.getAttr(s + ".useRayTraceShadows")
                 for s in shapes.values()
                 if cmds.objExists(s + ".useRayTraceShadows")))

    cam_pos = world_pos(CAM)
    view = v.normalise((cam_pos[0] - frame["centre"][0], 0.0,
                        cam_pos[2] - frame["centre"][2]))

    def side(name):
        p = world_pos(lights[name])
        return sum((p[i] - frame["centre"][i]) * view[i] for i in (0, 2))

    def colour(name):
        return cmds.getAttr(shapes[name] + ".color")[0]

    for name in ("key", "fill", "bounce"):
        c = colour(name)
        gate("%s: warm, on the camera's side" % name,
             c[0] > c[2] and side(name) > 0.0,
             "rgb %s, %.0f cm toward the camera" % (
                 tuple(round(x, 2) for x in c), side(name)))
    for name in ("rim", "kicker"):
        c = colour(name)
        gate("%s: cold, behind the subject" % name,
             c[2] > c[0] and side(name) < 0.0,
             "rgb %s, %.0f cm behind" % (
                 tuple(round(x, 2) for x in c), -side(name)))

    # --- the cyclorama -------------------------------------------------------
    pivot = v.resolve(v._string_attr(rig, v.PIVOT_ATTR))
    sweeps = [p for p in (cmds.ls(type="transform", long=True) or [])
              if v._under(p, rig) and p.endswith("VPStudio_cyclorama")]
    floors = [p for p in (cmds.ls(type="transform", long=True) or [])
              if v._under(p, rig) and p.endswith("VPStudio_floor")]
    gate("one cyclorama and no flat floor", len(sweeps) == 1 and not floors,
         str(sweeps))
    sweep = sweeps[0]
    gate("it hangs under the group, not the light pivot",
         cmds.listRelatives(sweep, parent=True, fullPath=True)[0] == rig
         and not v._under(sweep, pivot))

    mesh = om.MFnMesh(om.MSelectionList().add(sweep).getDagPath(0))
    points = mesh.getPoints(om.MSpace.kWorld)
    depth = [sum((p[i] - frame["centre"][i]) * view[i] for i in (0, 2))
             for p in points]
    gate("its wall stands 4.5 radii behind the subject from the camera",
         near(min(depth), -v.CYC_WALL * radius, 1e-3),
         "%.1f cm (= %.3f r)" % (-min(depth), -min(depth) / radius))
    gate("its floor runs 12 radii toward the camera",
         near(max(depth), v.CYC_FRONT * radius, 1e-3))
    lowest = min(p[1] for p in points)
    gate("its floor is just under the feet",
         frame["floor_y"] - 1.0 < lowest < frame["floor_y"],
         "%.4f under %.4f" % (lowest, frame["floor_y"]))
    gate("its top is 8 radii up",
         near(max(p[1] for p in points) - lowest, v.CYC_TOP * radius, 1e-3))

    target = om.MPoint(frame["centre"][0], frame["centre"][1],
                       frame["centre"][2])
    facing = []
    for i in range(mesh.numPolygons):
        normal = mesh.getPolygonNormal(i, om.MSpace.kWorld)
        verts = mesh.getPolygonVertices(i)
        mid = om.MVector(0.0, 0.0, 0.0)
        for vi in verts:
            mid += om.MVector(points[vi])
        mid /= float(len(verts))
        facing.append(normal * (om.MVector(target) - mid))
    gate("every face looks at the subject (%d faces)" % mesh.numPolygons,
         min(facing) > 0.0, "worst %.3f" % min(facing))
    #  A border edge always reads hard; only the interior ones shade.
    edges = om.MItMeshEdge(om.MSelectionList().add(sweep).getDagPath(0))
    interior = hard = 0
    while not edges.isDone():
        if not edges.onBoundary():
            interior += 1
            hard += 0 if edges.isSmooth else 1
        edges.next()
    gate("its interior edges are soft, so the cove shades as one",
         interior >= v.CYC_COVE_SEGMENTS and hard == 0,
         "%d interior, %d hard" % (interior, hard))
    sweep_shape = shape_of(sweep)
    gate("it catches shadows and casts none, double-sided",
         cmds.getAttr(sweep_shape + ".receiveShadows") == 1
         and cmds.getAttr(sweep_shape + ".castsShadows") == 0
         and cmds.getAttr(sweep_shape + ".doubleSided") == 1)
    gate("it stays out of a marquee select",
         cmds.getAttr(sweep + ".overrideDisplayType") == 2)
    groups = cmds.listConnections(sweep_shape, type="shadingEngine") or []
    shader = (cmds.listConnections(groups[0] + ".surfaceShader")
              or [None])[0] if groups else None
    paper = cmds.getAttr(shader + ".color")[0] if shader else (0, 0, 0)
    gate("it wears a warm matte blinn",
         shader and cmds.nodeType(shader) == "blinn"
         and paper[0] > paper[1] > paper[2]
         and max(cmds.getAttr(shader + ".specularColor")[0]) < 0.05,
         str(tuple(round(c, 2) for c in paper)))

    before_sweep = world_matrix(sweep)
    before_key = world_pos(lights["key"])
    print("retune:", v.retune({"look": SOFT, "rotate": 90.0}))
    after_key = world_pos(lights["key"])
    gate("Rotate turns the lights", math.dist(before_key, after_key) > 1.0,
         "key moved %.1f cm" % math.dist(before_key, after_key))
    gate("and leaves the paper behind the subject",
         max(abs(a - b) for a, b in zip(before_sweep,
                                        world_matrix(sweep))) < 1e-9)
    v.retune({"look": SOFT, "rotate": 0.0})

    v.setup({"look": SOFT, "quality": "Good", "clean": True})
    print("front shot:", blast(os.path.join(SHOTS, "soft_front.png")))
    wall = pixel(os.path.join(SHOTS, "soft_front.png"), 0.5, 0.06)
    gate("the paper reads warm in the picture",
         wall[0] > wall[1] > wall[2],
         "rgb %s above the head" % str(tuple(round(c, 3) for c in wall)))

    # --- the cost ------------------------------------------------------------
    for look in ("Studio", SOFT):
        v.setup({"look": look, "quality": "Good"})
        start = cmds.playbackOptions(query=True, min=True)
        t0 = time.time()
        for i in range(24):
            cmds.currentTime(start + i, edit=True)
            cmds.refresh(force=True)
        span = (time.time() - t0) / 24.0
        print("  %-12s %6.1f ms/frame (%5.1f fps)"
              % (look, 1000.0 * span, 1.0 / max(span, 1e-6)))
    cmds.currentTime(was_frame, edit=True)

    # --- switching looks -----------------------------------------------------
    v.setup({"look": "Studio", "quality": "Good"})
    rig = v.find_rig()
    kids = [p for p in (cmds.ls(type="transform", long=True) or [])
            if v._under(p, rig)]
    gate("Studio has its flat floor and no cyclorama",
         any(p.endswith("VPStudio_floor") for p in kids)
         and not any("cyclorama" in p for p in kids))
    gate("and no light of Soft Studio is left",
         not cmds.ls("*VPStudio_kicker*"))
    v.setup({"look": SOFT, "quality": "Good"})
    rig = v.find_rig()
    gate("Soft Studio again: one cyclorama",
         len([p for p in (cmds.ls(type="transform", long=True) or [])
              if v._under(p, rig) and "cyclorama" in p]) == 1)

    # --- three-quarter, the press again from there ---------------------------
    #  The pictures in clean view: what the animator will look at.
    place_camera(35.0, frame, meshes)
    v.setup({"look": SOFT, "quality": "Good", "clean": True})
    print("three-quarter shot:",
          blast(os.path.join(SHOTS, "soft_threequarter.png")))
    place_camera(0.0, frame, meshes)
    cmds.setAttr(CAM + ".focalLength", 30.0)
    cmds.select(meshes, replace=True)
    cmds.viewFit(CAM, fitFactor=0.45)
    cmds.select(clear=True)
    v.setup({"look": SOFT, "quality": "Good", "clean": True})
    print("wide shot:", blast(os.path.join(SHOTS, "soft_wide.png")))
    cmds.setAttr(CAM + ".focalLength", 45.0)
    place_camera(0.0, frame, meshes)
    v.setup({"look": "Studio", "quality": "Good", "clean": True})
    print("studio shot:", blast(os.path.join(SHOTS, "studio_front.png")))

    # --- restore -------------------------------------------------------------
    v.setup({"look": SOFT, "quality": "Good"})
    rig = v.find_rig()
    ours = v.recorded_nodes(rig) + (cmds.ls(rig, uuid=True) or [])
    print("restore:", v.restore())
    gate("Restore takes every node of ours",
         not v.find_rig() and not any(cmds.ls(u, long=True) for u in ours))

finally:
    try:
        cmds.lookThru(panel, was_camera)
    except Exception as exc:
        print("  camera restore failed:", exc)
    for uuid in made:
        for path in (cmds.ls(uuid, long=True) or []):
            if cmds.objExists(path):
                try:
                    cmds.delete(path)
                except Exception as exc:
                    print("  cleanup failed for", path, exc)
    try:
        cmds.currentTime(was_frame, edit=True)
        cmds.autoKeyframe(state=was_autokey)
        alive = [n for n in was_selection if cmds.objExists(n)]
        cmds.select(alive, replace=True) if alive else cmds.select(clear=True)
    except Exception as exc:
        print("  restore failed:", exc)

failed = [name for name, ok in RESULTS if not ok]
print("=== %d of %d gates failed ===" % (len(failed), len(RESULTS)))
for name in failed:
    print("  FAILED:", name)
