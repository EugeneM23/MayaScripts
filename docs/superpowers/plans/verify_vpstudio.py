"""Live verification for maya_vpstudio -- Viewport Studio.

Sent through the command port into the animator's OPEN scene. It builds
the studio for real, measures it, presses again to prove the press is
idempotent, works the dials, restores, and leaves the scene as it found
it (with the studio back on at the end, which is the point of the tool).

Nothing here assumes an empty scene: every node is resolved by long path
or UUID, everything created is registered as it is created, each teardown
step is guarded on its own, and the frame, the playback range, autoKey,
the selection and the panel's camera all go back exactly as found.

    PHASES = (1,)      # pure only, no scene touched
    PHASES = (1, 2)    # and the real build
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
    if _key.split(".")[0] == "maya_vpstudio":
        del sys.modules[_key]

import maya.cmds as cmds

import maya_vpstudio as v

PHASES = (1, 2)

SHOTS = (r"C:\Users\MYPC~1\AppData\Local\Temp\claude"
         r"\C-----Work-MayaScripts\73dfdfcc-7a3f-4a6b-8734-a0527c6e4cf9"
         r"\scratchpad")

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("%-4s %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
    return bool(ok)


def near(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def blast(path, frame=None):
    cmds.refresh(force=True)
    return cmds.playblast(
        frame=[cmds.currentTime(query=True) if frame is None else frame],
        format="image", compression="png", completeFilename=path,
        widthHeight=(960, 540), percent=100, viewer=False, offScreen=True,
        showOrnaments=False, forceOverwrite=True, quality=100)


print("module under test:", v.__file__)
print()

# ===========================================================================
#  Phase 1 -- the pure half. No scene is touched.
# ===========================================================================

if 1 in PHASES:
    print("--- phase 1: pure ---")

    opts = v.merged_options({"quality": "Beauty", "nonsense": True})
    gate("unknown options are dropped", "nonsense" not in opts)
    gate("given options win", opts["quality"] == "Beauty")
    gate("the rest are the defaults", opts["floor"] is True)

    box = (-40.0, 0.0, -40.0, 40.0, 180.0, 40.0)
    frame = v.subject_frame(box)
    gate("centre is the middle of the box",
         near(frame["centre"][1], 90.0) and near(frame["centre"][0], 0.0),
         str(frame["centre"]))
    gate("height is the box height", near(frame["height"], 180.0))
    gate("floor is the bottom of the box", near(frame["floor_y"], 0.0))
    gate("radius is half the diagonal",
         near(frame["radius"], 0.5 * math.sqrt(80 ** 2 + 180 ** 2 + 80 ** 2),
              1e-9), "%.3f" % frame["radius"])

    gate("an empty scene still gets a subject",
         v.subject_frame(None)["height"] > 1.0)

    m = v.look_at_matrix((0.0, 100.0, 0.0), (0.0, 0.0, 0.0))
    z_row = (m[8], m[9], m[10])
    gate("a light's -Z points at the target",
         near(dot(z_row, (0.0, 1.0, 0.0)), 1.0, 1e-9), str(z_row))
    m2 = v.look_at_matrix((300.0, 200.0, 100.0), (0.0, 50.0, 0.0))
    rows = [(m2[0], m2[1], m2[2]), (m2[4], m2[5], m2[6]),
            (m2[8], m2[9], m2[10])]
    gate("the matrix is orthonormal",
         all(near(dot(r, r), 1.0, 1e-9) for r in rows)
         and near(dot(rows[0], rows[1]), 0.0, 1e-9)
         and near(dot(rows[1], rows[2]), 0.0, 1e-9)
         and near(dot(rows[0], rows[2]), 0.0, 1e-9))
    want = v.normalise((300.0 - 0.0, 200.0 - 50.0, 100.0 - 0.0))
    gate("and it aims at the target from anywhere",
         near(dot(rows[2], want), 1.0, 1e-9))
    gate("straight down does not blow up on the up vector",
         all(abs(c) < 1e9 for c in v.look_at_matrix((0.0, 500.0, 0.0),
                                                    (0.0, 0.0, 0.0))))
    gate("translation is the light's position",
         near(m2[12], 300.0) and near(m2[13], 200.0) and near(m2[14], 100.0))

    gate("the camera decides the azimuth",
         near(v.studio_azimuth((100.0, 0.0, 0.0), (0.0, 0.0, 0.0)), 90.0,
              1e-9),
         "%.3f" % v.studio_azimuth((100.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
    gate("straight overhead falls back to zero",
         near(v.studio_azimuth((0.0, 500.0, 0.0), (0.0, 0.0, 0.0)), 0.0))

    gate("a wider subject wants a wider cone",
         v.cone_angle(200.0, 500.0) > v.cone_angle(100.0, 500.0))
    gate("a further light wants a narrower cone",
         v.cone_angle(100.0, 1000.0) < v.cone_angle(100.0, 300.0))

    small = v.render_settings(v.subject_frame(box))
    big = v.render_settings(v.subject_frame(
        (-400.0, 0.0, -400.0, 400.0, 1800.0, 400.0)))
    gate("the AO radius follows the scene's scale",
         small["ssaoRadius"] == 18 and big["ssaoRadius"] == 180,
         "%s vs %s" % (small["ssaoRadius"], big["ssaoRadius"]))
    gate("bloom never blooms the whole frame",
         small["bloomThreshold"] >= 1.0)
    gate("bloom needs the float target on",
         small["floatingPointRTEnable"] is True)

    gate("an unknown quality is Good",
         v.quality_of("nonsense") == v.quality_of("Good"))
    gate("Beauty costs more than Fast",
         v.quality_of("Beauty")["samples"] > v.quality_of("Fast")["samples"])

    plain = v.panel_settings({"clean": False})
    clean = v.panel_settings({"clean": True})
    gate("the plain view hides nothing of the animator's",
         "joints" not in plain and plain["grid"] is False)
    gate("clean view hides the rig clutter",
         clean["joints"] is False and clean["nurbsCurves"] is False)
    gate("but never the manipulators",
         "manipulators" not in clean,
         "an animator who cannot see the manipulator cannot animate")
    gate("the light icons go, the lighting stays",
         plain["lights"] is False and plain["displayLights"] == "all")

    fl = v.floor_plan(v.subject_frame(box))
    gate("the floor is many radii across",
         fl["size"] > 10 * v.subject_frame(box)["radius"],
         "%.0f" % fl["size"])
    gate("a tiny subject still gets a usable floor",
         v.floor_plan(v.subject_frame(
             (-1.0, 0.0, -1.0, 1.0, 2.0, 1.0)))["size"] >= 400.0)
    gate("the floor sits just under the feet",
         -1.0 < fl["position"][1] < 0.0, "%.4f" % fl["position"][1])

    gate("the union encloses both boxes",
         v.bbox_union([(0, 0, 0, 1, 1, 1), (-5, -5, -5, 0, 0, 0)])
         == (-5, -5, -5, 1, 1, 1))
    gate("a union of nothing is nothing", v.bbox_union([]) is None)
    gate("no rig picks nothing", v.pick_rig([]) is None)
    gate("two rigs pick the same one twice",
         v.pick_rig(["|b", "|a"]) == "|a")

    gate("the backdrop sets the flat colour playblast uses",
         "background" in v.backdrop_settings({"backdrop": True}))
    gate("and nothing at all when it is off",
         v.backdrop_settings({"backdrop": False}) == {})

    gate("dof is off unless asked", v.dof_plan(500.0, {"dof": False}) == {})
    gate("dof focuses on the subject",
         near(v.dof_plan(523.0, {"dof": True})["focusDistance"], 523.0))

    gate("every render attr we write is one Restore knows",
         set(v.render_settings(v.subject_frame(box))) <= set(v.RENDER_ATTRS),
         "or the animator never gets it back")
    print()

# ===========================================================================
#  Phase 2 -- the real build, in whatever scene is open.
# ===========================================================================

if 2 in PHASES:
    print("--- phase 2: the live build ---")

    panel = v.active_panel()

    #  Anything left over from an earlier run goes FIRST, and the entry
    #  state is read after it. The other way round cost a false failure:
    #  the leftover rig's own `shadows True` was recorded as "what the
    #  animator had", and Restore correctly handing back their `False`
    #  then read as a broken restore.
    if v.find_rig():
        print("  (clearing a studio left in the scene:", v.restore(), ")")

    was_frame = cmds.currentTime(query=True)
    was_autokey = cmds.autoKeyframe(query=True, state=True)
    was_range = (cmds.playbackOptions(query=True, min=True),
                 cmds.playbackOptions(query=True, max=True))
    was_selection = cmds.ls(selection=True, long=True) or []
    was_camera = cmds.modelEditor(panel, query=True, camera=True)
    was_shadows = cmds.modelEditor(panel, query=True, shadows=True)
    was_joints = cmds.modelEditor(panel, query=True, joints=True)
    was_ssao = cmds.getAttr("hardwareRenderingGlobals.ssaoEnable")
    was_gradient = cmds.displayPref(query=True, displayGradient=True)
    print("scene state on entry: frame %s, autoKey %s, ssao %s, shadows %s,"
          " joints %s" % (was_frame, was_autokey, was_ssao, was_shadows,
                          was_joints))

    made = []          # UUIDs of everything WE create, registered as created
    cam_tr = None
    try:
        frame = v.subject_frame(v.subject_bbox())
        before_bbox = v.subject_bbox()
        print("subject: centre %s radius %.1f height %.1f" % (
            ["%.1f" % c for c in frame["centre"]], frame["radius"],
            frame["height"]))

        cam_tr, _shape = cmds.camera(name="vpVerifyCam", focalLength=45)
        cam_tr = cmds.ls(cam_tr, long=True)[0]
        made += cmds.ls(cam_tr, uuid=True)
        cmds.xform(cam_tr, worldSpace=True, matrix=v.look_at_matrix(
            v.spherical(frame["centre"], 3.0 * frame["radius"], 22.0, 9.0),
            frame["centre"]))
        cmds.lookThru(panel, cam_tr)

        # --- the press ---------------------------------------------------
        said = v.setup({"quality": "Good"})
        print("setup said:", said)
        rig = v.find_rig()
        gate("the press builds a rig", bool(rig), str(rig))
        gate("it is found by its marker, not its name",
             rig in (cmds.ls("*." + v.MARKER, objectsOnly=True,
                             long=True) or []))

        lights = [l for l in (cmds.ls(lights=True, long=True) or [])
                  if l.startswith(rig)]
        gate("five lights, all inside our group", len(lights) == 5,
             "%d" % len(lights))
        kinds = sorted(cmds.nodeType(l) for l in lights)
        gate("three kinds: spots, directionals, one ambient",
             kinds == ["ambientLight", "directionalLight",
                       "directionalLight", "spotLight", "spotLight"],
             str(kinds))

        index = v.read_index(rig)
        gate("every light is in the index by UUID",
             sorted(index) == sorted(v.LIGHT_NAMES)
             and all(v.resolve(u) for u in index.values()))

        key = v.resolve(index["key"])
        key_shape = cmds.listRelatives(key, shapes=True, fullPath=True)[0]
        gate("the key light casts a depth map",
             cmds.getAttr(key_shape + ".useDepthMapShadows") == 1
             and cmds.getAttr(key_shape + ".dmapResolution") == 2048,
             "res %s" % cmds.getAttr(key_shape + ".dmapResolution"))
        gate("its cone is sized to the subject",
             20.0 < cmds.getAttr(key_shape + ".coneAngle") < 120.0,
             "%.1f deg" % cmds.getAttr(key_shape + ".coneAngle"))
        fill_shape = cmds.listRelatives(v.resolve(index["fill"]),
                                        shapes=True, fullPath=True)[0]
        gate("the fill casts nothing (it is there to lift, not to shadow)",
             cmds.getAttr(fill_shape + ".useDepthMapShadows") == 0)
        gate("and emits no specular",
             cmds.getAttr(fill_shape + ".emitSpecular") == 0)

        # --- the floor ---------------------------------------------------
        floor = [n for n in (cmds.listRelatives(rig, children=True,
                                                fullPath=True) or [])
                 if cmds.listRelatives(n, shapes=True, type="mesh",
                                       fullPath=True)]
        gate("there is exactly one floor", len(floor) == 1, str(floor))
        if floor:
            fshape = cmds.listRelatives(floor[0], shapes=True,
                                        fullPath=True)[0]
            fbox = cmds.exactWorldBoundingBox(floor[0])
            gate("the floor is under the feet, not through them",
                 fbox[1] < frame["floor_y"] + 1e-6
                 and fbox[1] > frame["floor_y"] - 5.0,
                 "floor %.3f vs feet %.3f" % (fbox[1], frame["floor_y"]))
            gate("it reaches past the subject on every side",
                 fbox[0] < before_bbox[0] and fbox[3] > before_bbox[3]
                 and fbox[2] < before_bbox[2] and fbox[5] > before_bbox[5])
            gate("it catches shadows and casts none",
                 cmds.getAttr(fshape + ".receiveShadows") == 1
                 and cmds.getAttr(fshape + ".castsShadows") == 0)
            gate("it stays out of a marquee select",
                 cmds.getAttr(floor[0] + ".overrideEnabled") == 1
                 and cmds.getAttr(floor[0] + ".overrideDisplayType") == 2)

        # --- the viewport ------------------------------------------------
        hw = "hardwareRenderingGlobals."
        gate("AO is on, sized for a %.0f cm subject" % frame["height"],
             cmds.getAttr(hw + "ssaoEnable") == 1
             and cmds.getAttr(hw + "ssaoRadius") == 18,
             "radius %s" % cmds.getAttr(hw + "ssaoRadius"))
        gate("anti-aliasing is on at 8 samples",
             cmds.getAttr(hw + "multiSampleEnable") == 1
             and cmds.getAttr(hw + "multiSampleCount") == 8)
        gate("motion blur is on", cmds.getAttr(hw + "motionBlurEnable") == 1)
        gate("bloom is on and thresholded above white",
             cmds.getAttr(hw + "bloomEnable") == 1
             and cmds.getAttr(hw + "bloomThreshold") >= 1.0)
        #  The gate that would have caught the whole silent-skip bug in
        #  one line: compare EVERY planned setting against the scene.
        mismatched = []
        for attr, value in v.render_settings(
                frame, {"quality": "Good"}).items():
            got = cmds.getAttr(hw + attr)
            if isinstance(value, bool):
                landed = bool(got) == value
            elif isinstance(value, float):
                landed = abs(float(got) - value) < 1e-4
            else:
                landed = got == value
            if not landed:
                mismatched.append("%s=%r want %r" % (attr, got, value))
        gate("every render setting we plan actually lands in the scene",
             not mismatched, "; ".join(mismatched[:4]))
        gate("and the status line does not report any as unavailable",
             "unavailable" not in said, said)

        gate("every model panel lights, textures and shadows",
             all(cmds.modelEditor(p, query=True, shadows=True)
                 and cmds.modelEditor(p, query=True,
                                      displayLights=True) == "all"
                 and cmds.modelEditor(p, query=True, displayTextures=True)
                 for p in v.model_panels()))
        gate("the light icons are not drawn",
             not cmds.modelEditor(panel, query=True, lights=True))
        gate("the playblast background is dark too",
             max(cmds.displayRGBColor("background", query=True)) < 0.2,
             str(["%.3f" % c
                  for c in cmds.displayRGBColor("background", query=True)]))

        # --- what the animator will actually look at ----------------------
        print("studio shot:", blast(SHOTS + r"\v_studio.png"))

        # --- the state that makes it reversible --------------------------
        state = v.read_state(rig)
        gate("the animator's own viewport is remembered",
             state.get("plugs", {}).get(hw + "ssaoEnable") == was_ssao,
             "recorded %r, was %r" % (
                 state.get("plugs", {}).get(hw + "ssaoEnable"), was_ssao))
        gate("all %d panels are remembered" % len(v.model_panels()),
             sorted(state.get("panels", {})) == sorted(v.model_panels()))

        # --- press it again ----------------------------------------------
        first_floor_size = (cmds.exactWorldBoundingBox(floor[0])[3]
                            - cmds.exactWorldBoundingBox(floor[0])[0])
        said2 = v.setup({"quality": "Good"})
        rig2 = v.find_rig()
        lights2 = [l for l in (cmds.ls(lights=True, long=True) or [])
                   if l.startswith(rig2)]
        floor2 = [n for n in (cmds.listRelatives(rig2, children=True,
                                                 fullPath=True) or [])
                  if cmds.listRelatives(n, shapes=True, type="mesh",
                                        fullPath=True)]
        second_floor_size = (cmds.exactWorldBoundingBox(floor2[0])[3]
                             - cmds.exactWorldBoundingBox(floor2[0])[0])
        gate("a second press does not double the rig",
             len(lights2) == 5 and len(floor2) == 1,
             "%d lights, %d floors" % (len(lights2), len(floor2)))
        gate("nor grow the floor by measuring its own floor",
             abs(second_floor_size - first_floor_size) < 1.0,
             "%.1f then %.1f" % (first_floor_size, second_floor_size))
        gate("the subject measures the same both times",
             all(near(a, b, 1e-6) for a, b in
                 zip(before_bbox, v.subject_bbox())))
        gate("and the FIRST press's memory is carried forward",
             v.read_state(rig2).get("plugs", {}).get(hw + "ssaoEnable")
             == was_ssao,
             "or Restore hands back our own studio settings")

        # --- the dials ---------------------------------------------------
        index2 = v.read_index(rig2)
        v.retune({"brightness": 1.5, "rotate": 40.0})
        key2 = v.resolve(v.read_index(rig2)["key"])
        key2_shape = cmds.listRelatives(key2, shapes=True, fullPath=True)[0]
        gate("brightness scales the rig without rebuilding it",
             near(cmds.getAttr(key2_shape + ".intensity"), 1.30 * 1.5, 1e-5)
             and v.read_index(rig2) == index2,
             "key now %.3f" % cmds.getAttr(key2_shape + ".intensity"))
        pivot = v.resolve(v._string_attr(rig2, v.PIVOT_ATTR))
        gate("rotate spins the whole studio on one pivot",
             near(cmds.getAttr(pivot + ".rotateY"), 40.0, 1e-5))
        v.retune({"brightness": 1.0, "rotate": 0.0})

        # --- quality -----------------------------------------------------
        v.setup({"quality": "Beauty"})
        rigb = v.find_rig()
        keyb = cmds.listRelatives(v.resolve(v.read_index(rigb)["key"]),
                                  shapes=True, fullPath=True)[0]
        gate("Beauty raises the shadow map and the samples",
             cmds.getAttr(keyb + ".dmapResolution") == 4096
             and cmds.getAttr(hw + "multiSampleCount") == 16,
             "dmap %s, aa %s" % (cmds.getAttr(keyb + ".dmapResolution"),
                                 cmds.getAttr(hw + "multiSampleCount")))
        v.setup({"quality": "Good", "motion_blur": False})
        gate("a switched-off option really goes off",
             cmds.getAttr(hw + "motionBlurEnable") == 0)

        # --- clean view --------------------------------------------------
        v.setup({"quality": "Good", "clean": True})
        gate("clean view hides the joints in the panel",
             not cmds.modelEditor(panel, query=True, joints=True))
        print("clean shot:", blast(SHOTS + r"\v_clean.png"))
        v.setup({"quality": "Good"})
        gate("and the next press without it brings them back",
             cmds.modelEditor(panel, query=True, joints=True)
             == was_joints,
             "or the animator's rig stays invisible and the tool looks "
             "broken")

        # --- motion blur, on a frame where something moves ---------------
        moving = min(was_range[1], 100.0)
        cmds.currentTime(moving, edit=True)
        v.setup({"quality": "Good", "motion_blur": False})
        print("no-blur shot:", blast(SHOTS + r"\v_noblur.png", moving))
        v.setup({"quality": "Good", "motion_blur": True})
        print("blur shot:", blast(SHOTS + r"\v_blur.png", moving))
        cmds.currentTime(was_frame, edit=True)

        # --- what it costs to play --------------------------------------
        for level in ("Fast", "Good", "Beauty"):
            v.setup({"quality": level})
            start = cmds.playbackOptions(query=True, min=True)
            t0 = time.time()
            for i in range(24):
                cmds.currentTime(start + i, edit=True)
                cmds.refresh(force=True)
            span = (time.time() - t0) / 24.0
            print("  %-7s %6.1f ms/frame (%5.1f fps)"
                  % (level, 1000.0 * span, 1.0 / max(span, 1e-6)))
        cmds.currentTime(was_frame, edit=True)

        # --- restore -----------------------------------------------------
        v.setup({"quality": "Good"})
        rig_before_restore = v.find_rig()
        our_uuids = v.recorded_nodes(rig_before_restore) + \
            (cmds.ls(rig_before_restore, uuid=True) or [])
        said3 = v.restore()
        print("restore said:", said3)
        gate("nothing of ours is left in the scene",
             not v.find_rig()
             and not any(cmds.ls(u, long=True) for u in our_uuids))
        gate("the shading group goes with it",
             not cmds.objExists(v.SHADER))
        gate("AO is back where the animator had it",
             cmds.getAttr(hw + "ssaoEnable") == was_ssao,
             "%r" % cmds.getAttr(hw + "ssaoEnable"))
        gate("the panel's shadows are back",
             cmds.modelEditor(panel, query=True, shadows=True)
             == was_shadows)
        gate("so is the background gradient",
             cmds.displayPref(query=True, displayGradient=True)
             == was_gradient)
        gate("restoring twice is not an error",
             "nothing to restore" in v.restore())

        # --- leave the studio on: it is what the animator asked for ------
        print("final:", v.setup({"quality": "Good"}))
        gate("the tool is on at the end", bool(v.find_rig()))

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
        except Exception as exc:
            print("  frame restore failed:", exc)
        try:
            cmds.autoKeyframe(state=was_autokey)
        except Exception as exc:
            print("  autoKey restore failed:", exc)
        try:
            cmds.playbackOptions(min=was_range[0], max=was_range[1])
        except Exception as exc:
            print("  range restore failed:", exc)
        try:
            alive = [n for n in was_selection if cmds.objExists(n)]
            if alive:
                cmds.select(alive, replace=True)
            else:
                cmds.select(clear=True)
        except Exception as exc:
            print("  selection restore failed:", exc)

    gate("the verify camera is gone",
         not cmds.objExists("vpVerifyCam"))
    gate("the frame is where the animator left it",
         near(cmds.currentTime(query=True), was_frame))
    gate("autoKey is as we found it",
         cmds.autoKeyframe(query=True, state=True) == was_autokey)
    gate("the playback range is untouched",
         near(cmds.playbackOptions(query=True, min=True), was_range[0])
         and near(cmds.playbackOptions(query=True, max=True), was_range[1]))
    gate("the panel looks through the animator's camera again",
         cmds.modelEditor(panel, query=True, camera=True) == was_camera,
         str(cmds.modelEditor(panel, query=True, camera=True)))

print()
failed = [name for name, ok in RESULTS if not ok]
print("=== %d of %d gates failed ===" % (len(failed), len(RESULTS)))
for name in failed:
    print("  FAILED:", name)
