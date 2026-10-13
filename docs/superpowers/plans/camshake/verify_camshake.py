"""Camera Shake, proven in mayapy standalone (never in the animator's scene).

  $env:MAYA_APP_DIR = "$env:TEMP\\claude\\cs_mad"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/camshake/verify_camshake.py

Every gate prints PASS/FAIL with its number; the last line is the count.
"""

import importlib.util
import math
import os
import sys
import traceback

import maya.standalone

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import numpy as np  # noqa: E402

REPO = r"C:\!!!Work\MayaScripts"
SCRIPT = os.path.join(REPO, "SkeldarAnim", "maya_camshake.py")   # in the plugin since 2026-10-13
PLUGIN = os.path.join(REPO, "SkeldarAnim")


def load():
    spec = importlib.util.spec_from_file_location("skeldar_camshake_verify", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cs = load()
RESULTS = []
VIEW = np.array([0.0, 0.0, -1.0])


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s %2d %s%s" % ("PASS" if ok else "FAIL", len(RESULTS), name, ("  - " + detail) if detail else ""))


def shown(node, frame):
    """What the node shows at a frame, after a real time change."""
    cmds.currentTime(frame + 0.5)
    cmds.currentTime(frame)
    return (np.array(cmds.getAttr(node + ".rotate")[0], float), np.array(cmds.getAttr(node + ".translate")[0], float))


def frame_of(node, euler):
    order, axis, orient = cs._static(node)
    return (cs.euler_matrix(np.radians(axis), "xyz") @ cs.euler_matrix(np.radians(euler), order)
            @ cs.euler_matrix(np.radians(orient), "xyz"))


def expected(node, base, rot):
    """The rotate a node should show: its base turned by `rot` (deg) about its own axes."""
    order, axis, _ = cs._static(node)
    return cs.shaken(base, order, rot, axis)


def matrix_gap(node, a, b):
    return float(np.abs(frame_of(node, a) - frame_of(node, b)).max())


def base_curves(node):
    found = {}
    for attr in cs.ROTATE + cs.TRANSLATE:
        curves = cmds.listConnections("%s.%s" % (node, attr), source=True, destination=False, type="animCurve") or []
        if curves:
            found[attr] = curves[0]
    return found


def curve_values(curve):
    return list(zip(cmds.keyframe(curve, query=True, timeChange=True) or [],
                    cmds.keyframe(curve, query=True, valueChange=True) or []))


def our_curve(layer, node, attr):
    return cs._find_curve(layer, "%s.%s" % (node, attr))


def keyed_camera(name, order=2, axis=(5.0, -10.0, 3.0)):
    camera = cmds.camera()[0]
    camera = cmds.rename(camera, name)
    camera = cmds.ls(camera, long=True)[0]
    cmds.setAttr(camera + ".rotateOrder", order)
    cmds.setAttr(camera + ".rotateAxis", *axis)
    for frame, rx, ry, tx in ((0, -10.0, 0.0, 0.0), (60, -25.0, 50.0, 40.0), (120, -5.0, 90.0, 100.0)):
        cmds.setKeyframe(camera, attribute="rotateX", time=frame, value=rx)
        cmds.setKeyframe(camera, attribute="rotateY", time=frame, value=ry)
        cmds.setKeyframe(camera, attribute="translateX", time=frame, value=tx)
    cmds.setKeyframe(camera, attribute="rotateZ", time=0, value=3.0)
    cmds.setKeyframe(camera, attribute="translateY", time=0, value=160.0)
    cmds.setKeyframe(camera, attribute="translateZ", time=0, value=300.0)
    return camera


def node_names():
    return set(cmds.ls())


def phase_handheld():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=0, maxTime=120, animationStartTime=0, animationEndTime=120)
    cmds.undoInfo(state=True, infinity=True)
    camera = keyed_camera("camA")
    own = base_curves(camera)
    before = {attr: curve_values(curve) for attr, curve in own.items()}
    base = {f: shown(camera, f) for f in range(0, 121)}

    given = {"sway": 2.0, "jitter": 0.3, "drift": 3.0, "ease": 6.0, "seed": 5}
    layer, message = cs.apply("handheld", given, selection=[camera], frames=(10, 100))
    print("   ", message)
    found = cs.record(layer)
    gate("a layer of its own, marked, additive, by component, locked",
         cmds.nodeType(layer) == "animLayer" and found and found["mode"] == "handheld"
         and found["frames"] == [10, 100] and not cmds.animLayer(layer, query=True, override=True)
         and cmds.getAttr(layer + ".rotationAccumulationMode") == 0
         and cmds.animLayer(layer, query=True, lock=True), layer)

    after = {attr: curve_values(curve) for attr, curve in own.items()}
    gate("the camera's own keys untouched", after == before and len(own) == 6)

    times = sorted(cmds.keyframe(our_curve(layer, camera, "rotateY"), query=True, timeChange=True))
    gate("keys on every frame 9..101", times == [float(f) for f in range(9, 102)], "%d keys" % len(times))

    s = cs.settings("handheld", given)
    frames = np.arange(10, 101)
    rot, off = cs.handheld(frames, 10, 100, 30.0, s)
    worst_r, worst_t = 0.0, 0.0
    order, axis, orient = cs._static(camera)
    for i, f in enumerate(frames):
        r, t = shown(camera, int(f))
        e = expected(camera, base[int(f)][0], rot[i])
        worst_r = max(worst_r, matrix_gap(camera, r, e))
        dt = cs.along_axes(off[i], base[int(f)][0], order, axis, orient)
        worst_t = max(worst_t, float(np.abs(t - (base[int(f)][1] + dt)).max()))
    gate("the camera shows the shake in its own axes on every frame", worst_r < 1e-9 and worst_t < 1e-6,
         "rotation %.2e, translation %.2e cm" % (worst_r, worst_t))
    gate("the shake is there (not a no-op)", np.abs(rot).max() > 0.8 and np.abs(off).max() > 1.0,
         "peak %.2f deg, %.2f cm" % (np.abs(rot).max(), np.abs(off).max()))

    outside = 0.0
    for attr in cs.ROTATE + cs.TRANSLATE:
        curve = our_curve(layer, camera, attr)
        for t in (0.0, 5.0, 9.0, 9.25, 9.5, 9.75, 100.25, 100.5, 100.75, 101.0, 110.0, 120.0):
            outside = max(outside, abs(cmds.keyframe(curve, query=True, eval=True, time=(t, t))[0]))
    gate("nothing outside the range, between frames too", outside < 1e-9, "%.2e" % outside)
    return camera, layer, base


def phase_retune(camera, layer, base):
    cmds.setAttr(layer + ".weight", 0.6)
    curve = our_curve(layer, camera, "rotateY")
    old = np.array([v for _, v in curve_values(curve)])
    uuid = cmds.ls(layer, uuid=True)[0]
    message = cs.retune(layer, {"sway": 4.0, "jitter": 0.6, "drift": 6.0, "ease": 6.0, "seed": 5})
    new = np.array([v for _, v in curve_values(curve)])
    print("   ", message)
    gate("a re-tune keeps the layer, its weight and its lock", cmds.ls(layer, uuid=True)[0] == uuid
         and abs(cmds.getAttr(layer + ".weight") - 0.6) < 1e-12 and len(cs.shakes()) == 1
         and cmds.animLayer(layer, query=True, lock=True))
    gate("doubling the settings doubles the shake, same shape",
         np.abs(new - 2.0 * old).max() < 0.02 * np.abs(new).max(), "%.4f of %.3f" % (np.abs(new - 2.0 * old).max(), np.abs(new).max()))
    cmds.undo()
    back = np.array([v for _, v in curve_values(curve)])
    gate("one undo puts the old shake back", np.abs(back - old).max() < 1e-12)
    cmds.redo()
    s = cs.settings("handheld", {"sway": 4.0, "jitter": 0.6, "drift": 6.0, "ease": 6.0, "seed": 5})
    frames = np.arange(10, 101)
    rot, _ = cs.handheld(frames, 10, 100, 30.0, s)
    worst = 0.0
    for i in (5, 30, 60, 85):
        f = int(frames[i])
        r, _ = shown(camera, f)
        # at weight 0.6 the layer adds 0.6 of its eulers
        e = base[f][0] + 0.6 * (expected(camera, base[f][0], rot[i]) - base[f][0])
        worst = max(worst, float(np.abs(r - e).max()))
    gate("the weight scales what the layer adds", worst < 1e-6, "%.2e deg" % worst)
    cmds.setAttr(layer + ".weight", 1.0)


def phase_impact(camera, base):
    hand = {f: shown(camera, f) for f in range(38, 63)}
    given = {"direction": "Below", "strength": 5.0, "push": 2.0, "wave": 8.0, "decay": "Linear", "rattle": 0.8,
             "roll": 0.3, "seed": 2}
    layer, message = cs.apply("impact", given, selection=[camera], frames=(40, 60))
    print("   ", message)
    gate("an impact is a second layer", len(cs.shakes()) == 2 and cs.record(layer)["mode"] == "impact")
    s = cs.settings("impact", given)
    frames = np.arange(40, 61)
    rot, off = cs.impact(frames, 40, 60, 30.0, s)
    worst = 0.0
    for i, f in enumerate(frames):
        r, _ = shown(camera, int(f))
        worst = max(worst, matrix_gap(camera, r, expected(camera, hand[int(f)][0], rot[i])))
    gate("stacked on the handheld one, exactly", worst < 1e-9, "%.2e" % worst)
    r40, _ = shown(camera, 40)
    r60, _ = shown(camera, 60)
    gate("still at the hit frame and at the end", np.abs(r40 - hand[40][0]).max() < 1e-9
         and np.abs(r60 - hand[60][0]).max() < 1e-9)
    tilt = []
    for f in (41, 42):
        r, _ = shown(camera, f)
        before = frame_of(camera, hand[f][0])
        seen = VIEW @ frame_of(camera, r) @ before.T
        tilt.append(math.degrees(math.asin(seen[1])))
    gate("a hit from below throws the view up", min(tilt) > 3.0, "%.2f, %.2f deg" % tuple(tilt))

    own = {f: shown(camera, f) for f in range(102, 119)}
    tilted, _ = cs.apply("impact", {"direction": "Left", "strength": 6.0, "rattle": 2.0, "decay": "Smooth",
                                    "pan_on": False, "roll_on": False}, selection=[camera], frames=(102, 118))
    sideways, turned = 0.0, 0.0
    for f in range(102, 119):
        r, _ = shown(camera, f)
        turn = frame_of(camera, r) @ frame_of(camera, own[f][0]).T      # S, in the camera's own axes
        sideways = max(sideways, abs(turn[0, 1]), abs(turn[0, 2]), abs(turn[1, 0]), abs(turn[2, 0]))
        turned = max(turned, math.degrees(math.acos(min(1.0, turn[1, 1]))))
    gate("Pan and Roll off: the camera turns about its own X only", sideways < 1e-9 and turned > 0.3,
         "off the X axis %.1e, tilt up to %.2f deg" % (sideways, turned))
    cs.delete(tilted)
    return layer


def phase_undo_delete(camera, impact_layer):
    layers = set(cmds.ls(type="animLayer"))
    names = node_names()
    cs.apply("impact", {"direction": "Left"}, selection=[camera], frames=(70, 90))
    cmds.undo()
    gate("one undo takes a whole new shake away", set(cmds.ls(type="animLayer")) == layers
         and node_names() == names)
    cmds.redo()
    gate("redo brings it back", len(cs.shakes()) == 3)
    cmds.undo()
    keys = len(cmds.keyframe(our_curve(impact_layer, camera, "rotateX"), query=True, timeChange=True))
    cs.delete(impact_layer)
    gone = not cmds.objExists(impact_layer)
    cmds.undo()
    gate("Delete removes the shake, undo brings it back", gone and cmds.objExists(impact_layer)
         and len(cmds.keyframe(our_curve(impact_layer, camera, "rotateX"), query=True, timeChange=True)) == keys)


def phase_cameras():
    camB = cmds.ls(cmds.rename(cmds.camera()[0], "camB"), long=True)[0]
    camC = cmds.ls(cmds.rename(cmds.camera()[0], "camC"), long=True)[0]
    for camera in (camB, camC):
        cmds.setAttr(camera + ".rotate", -5.0, 30.0, 0.0)
        cmds.setAttr(camera + ".translate", 0.0, 150.0, 200.0)
    layer, message = cs.apply("handheld", {"sway": 1.5, "drift": 0.0}, selection=[camB, camC], frames=(0, 60))
    print("   ", message)
    a = np.array([v for _, v in curve_values(our_curve(layer, camB, "rotateY"))])
    b = np.array([v for _, v in curve_values(our_curve(layer, camC, "rotateY"))])
    corr = float(np.corrcoef(a, b)[0, 1])
    gate("two cameras, one layer, each its own shake", len(cs.record(layer)["targets"]) == 2 and abs(corr) < 0.9,
         "correlation %.2f" % corr)
    gate("no translate keyed when Drift is 0", our_curve(layer, camB, "translateX") is None)
    before = curve_values(our_curve(layer, camB, "rotateY"))
    cmds.currentTime(30)
    cmds.setKeyframe(camB, attribute="rotateY", value=45.0)
    base_curve = cs._find_curve("BaseAnimation", camB + ".rotateY")
    gate("a plain key after it lands on the base layer, not the shake",
         curve_values(our_curve(layer, camB, "rotateY")) == before and base_curve is not None
         and 30.0 in (cmds.keyframe(base_curve, query=True, timeChange=True) or []))

    cmds.select(clear=True)
    joint = cmds.ls(cmds.joint(name="shakeJoint", orientation=(0.0, 45.0, 0.0)), long=True)[0]
    cmds.setAttr(joint + ".rotateOrder", 4)
    cmds.setKeyframe(joint, attribute="rotateX", time=0, value=10.0)
    cmds.setKeyframe(joint, attribute="rotateX", time=30, value=40.0)
    base = {f: shown(joint, f) for f in range(0, 31)}
    given = {"direction": "Left", "strength": 4.0, "push": 3.0, "seed": 3}
    layer, _ = cs.apply("impact", given, selection=[joint], frames=(0, 30))
    rot, off = cs.impact(np.arange(0, 31), 0, 30, 30.0, cs.settings("impact", given))
    order, axis, orient = cs._static(joint)
    worst_r, worst_t = 0.0, 0.0
    for f in range(0, 31):
        r, t = shown(joint, f)
        worst_r = max(worst_r, matrix_gap(joint, r, expected(joint, base[f][0], rot[f])))
        worst_t = max(worst_t, float(np.abs(t - base[f][1] - cs.along_axes(off[f], base[f][0], order, axis, orient)).max()))
    gate("a joint (orient, yxz) shaken in its own axes", worst_r < 1e-9 and worst_t < 1e-6,
         "%.2e, %.2e" % (worst_r, worst_t))

    try:
        cmds.animLayer(layer, edit=True, selected=True)
        others = [l for l in cs.shakes() if l != layer]
        for other in others:
            cmds.animLayer(other, edit=True, selected=False)
        gate("a shake selected in the layer editor is the one picked", cs.editor_pick() == layer)
    except Exception as error:
        gate("a shake selected in the layer editor is the one picked", False, str(error))


def phase_ranges_and_speed():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=0, maxTime=300, animationStartTime=0, animationEndTime=300)
    cmds.currentTime(30)
    hand = cs.frames_for("handheld", cs.settings("handheld"))
    hit = cs.frames_for("impact", cs.settings("impact", {"length": 24}))
    gate("no highlight: handheld takes the playback range, an impact the current frame + Length",
         hand[:2] == (0, 300) and hit[:2] == (30, 54), "%s / %s" % (hand, hit))
    camera = keyed_camera("camSpeed")
    import time
    start = time.time()
    layer, _ = cs.apply("handheld", {"drift": 2.0}, selection=[camera], frames=(0, 300))
    applied = time.time() - start
    start = time.time()
    cs.retune(layer, {"sway": 1.5, "drift": 2.0})
    retuned = time.time() - start
    gate("a 300-frame shake applies and re-tunes fast enough to follow a slider",
         applied < 3.0 and retuned < 3.0, "apply %.2f s, re-tune %.2f s (mayapy)" % (applied, retuned))


def phase_refusals():
    cmds.file(new=True, force=True)
    plain = cmds.ls(cmds.rename(cmds.camera()[0], "plainCam"), long=True)[0]
    cmds.select(clear=True)
    names = node_names()
    refused = []
    try:
        cs.apply("handheld", selection=[], frames=(0, 20))
    except cs.Refused as error:
        refused.append(str(error))
    aimed = cmds.ls(cmds.rename(cmds.camera()[0], "aimedCam"), long=True)[0]
    target = cmds.spaceLocator(name="aimHere")[0]
    cmds.aimConstraint(target, aimed)
    names = node_names()
    try:
        cs.apply("handheld", selection=[aimed], frames=(0, 20))
    except cs.Refused as error:
        refused.append(str(error))
    try:
        cs.apply("impact", selection=[plain], frames=(5, 5))
    except cs.Refused as error:
        refused.append(str(error))
    gate("refusals, by name, change nothing", len(refused) == 3 and node_names() == names and not cs.shakes(),
         " / ".join(refused))
    gate("the aimed camera's refusal names the constraint", "aimConstraint" in refused[1] if len(refused) > 1 else False)


def phase_manny():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=0, maxTime=60, animationStartTime=0, animationEndTime=60)
    for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
        try:
            cmds.loadPlugin(plugin, quiet=True)
        except Exception:
            pass
    sys.path.insert(0, PLUGIN)
    from maya_scenesetup import camera as plugcam  # noqa: E402
    from maya_scenesetup import catalog, character  # noqa: E402
    character.add_character(catalog.default_character())
    bones = [b for b in cmds.ls(type="joint", long=True) if b.split("|")[-1].split(":")[-1] == "camera_root"]
    bone = bones[0]
    cmds.setKeyframe(bone, attribute="rotateY", time=0, value=cmds.getAttr(bone + ".rotateY"))
    plugcam.setup(bone, 0, 60)
    ours = cs.our_cameras()
    cmds.select(clear=True)
    layer, message = cs.apply("handheld", {"sway": 2.0, "jitter": 0.2, "drift": 2.0, "seed": 11}, frames=(0, 60))
    print("   ", message)
    gate("nothing selected: our SceneSetup camera is the one shaken",
         len(ours) == 1 and cs.record(layer)["targets"] == [cmds.ls(ours[0], uuid=True)[0]], ours[0] if ours else "")
    offset = plugcam.rotation_only(plugcam.AXIS_OFFSET)
    worst, moved = 0.0, 0.0
    for f in (5, 20, 35, 50):
        cmds.currentTime(f + 0.5)
        cmds.currentTime(f)
        want = plugcam.bone_matrix_for(plugcam.world_matrix(ours[0]), offset)
        have = plugcam.world_matrix(bone)
        worst = max(worst, max(abs(x - y) for x, y in zip(want, have)))
        cmds.animLayer(layer, edit=True, mute=True)
        cmds.currentTime(f + 0.5)
        cmds.currentTime(f)
        still = plugcam.world_matrix(bone)
        cmds.animLayer(layer, edit=True, mute=False)
        moved = max(moved, max(abs(x - y) for x, y in zip(still[:12], have[:12])))
    gate("camera_root follows the shaken camera, so the shake reaches the export",
         worst < 1e-6 and moved > 0.005, "follow %.2e, the shake moves the bone's axes %.4f" % (worst, moved))


def main():
    try:
        camera, layer, base = phase_handheld()
        phase_retune(camera, layer, base)
        impact_layer = phase_impact(camera, base)
        phase_undo_delete(camera, impact_layer)
        phase_cameras()
        phase_ranges_and_speed()
        phase_refusals()
        phase_manny()
    except Exception:
        traceback.print_exc()
        gate("the run finished", False)
    print("%d of %d gates passed" % (sum(RESULTS), len(RESULTS)))


main()
