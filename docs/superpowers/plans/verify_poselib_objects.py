"""The Pose Library's objects beside a character (2026-10-15), end to end, mayapy STANDALONE.

Never in the animator's Maya: it adds rigs and cameras and keys them. Run with a scratch
MAYA_APP_DIR:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_poselib_objects.py [out]

Two Manny rigs (A, B), each with Camera Setup's SceneSetup camera on its camera_root (in its
namespace and character group), a free camera `shotCam` and a locator `prop`. A pose and an
animation are saved from A + A's camera + shotCam + prop; then shotCam moves into a namespace
`shot:` (as another scene would have it) and the cards go onto B:
  save      the card is a character card holding the three objects, A's camera `own`, the
            shot camera's focal length in `shape`;
  pose      B:Main + shot:shotCam selected: B's OWN camera takes A's camera's values (its
            namespace), shot:shotCam the shot camera's (by name, namespace ignored) focal length
            too, the prop its by exact path, A's camera untouched; one undo puts every one back;
  unsel     B:Main alone: the shot camera is not searched for by name (said), the prop posed;
  alone     shot:shotCam alone: the camera posed, B untouched, said;
  anim      the animation onto B:Main + shot:shotCam: their curves keyed, focal length too, in
            the character's one undo chunk.
Every gate prints PASS/FAIL, the run ends SUMMARY x/y.
"""

import io
import json
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("POSELIB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_rigs  # noqa: E402
from maya_scenesetup import camera, catalog, character  # noqa: E402
from maya_poselib import animapply, animcapture  # noqa: E402
from maya_poselib import apply as ap  # noqa: E402
from maya_poselib import capture  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))


def near(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol


def evaluate():
    """A real time change, OFF the undo queue (a `currentTime` is on it in mayapy and would take
    the next `cmds.undo()`)."""
    t = cmds.currentTime(query=True)
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        cmds.currentTime(t + 1, update=True)
        cmds.currentTime(t, update=True)
    finally:
        cmds.undoInfo(stateWithoutFlush=True)


def goto(t):
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        cmds.currentTime(t, update=True)
    finally:
        cmds.undoInfo(stateWithoutFlush=True)
    evaluate()


def add_rig():
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key("Manny_Rig"))
    cmds.select(clear=True)
    return [r for r in maya_rigs.rigs() if r.namespace not in before][0]


def cam_of(rig):
    bone = cmds.ls(rig.namespace + ":camera_root", long=True)[0]
    camera.setup(bone, 0, 10)
    return cmds.ls(camera.camera_name_for(bone), long=True)[0]


def get(plug):
    return float(cmds.getAttr(plug))


def roundtrip(data):
    return json.loads(json.dumps(data))


try:
    cmds.playbackOptions(minTime=0, maxTime=10, animationStartTime=0, animationEndTime=10)
    cmds.currentTime(0)
    a, b = add_rig(), add_rig()
    a_cam, b_cam = cam_of(a), cam_of(b)
    shot = cmds.rename(cmds.camera()[0], "shotCam")
    shot = cmds.ls(shot, long=True)[0]
    prop = cmds.ls(cmds.spaceLocator(name="prop")[0], long=True)[0]
    say("rigs", a.namespace, b.namespace, "cameras", a_cam, b_cam)

    wrist_a = cmds.ls(a.namespace + ":FKWrist_R", long=True)[0]
    wrist_b = cmds.ls(b.namespace + ":FKWrist_R", long=True)[0]

    # ---- the source pose (frame 0), and an animation over 0..10
    for t, v in ((0, 0.0), (10, 1.0)):
        cmds.setKeyframe(wrist_a, attribute="rotateZ", time=t, value=30.0 * v)
        cmds.setKeyframe(a_cam, attribute="translateX", time=t, value=12.0 + 10 * v)
        cmds.setKeyframe(shot, attribute="translateX", time=t, value=5.0 + 10 * v)
        cmds.setKeyframe(shot, attribute="rotateY", time=t, value=30.0)
        cmds.setKeyframe(cmds.listRelatives(shot, shapes=True, fullPath=True)[0], attribute="focalLength", time=t,
                         value=50.0 + 10 * v)
        cmds.setKeyframe(prop, attribute="translateY", time=t, value=7.0 + v)
    evaluate()
    selection = [a.main, a_cam, shot, prop]
    pose, note = capture.build_pose(selection)
    pose = roundtrip(pose)
    say("pose note:", note)
    header, frames, anote = animcapture.build_animation(selection, start=0, end=10)
    header, frames = roundtrip(header), roundtrip(frames)
    say("anim note:", anote)

    # ---- save
    objs = dict((o["name"], o) for o in pose.get("objects") or [])
    gate("save.kind", pose["kind"] == "character", pose["kind"])
    gate("save.objects", sorted(objs) == ["SceneSetup_camera", "prop", "shotCam"], sorted(objs))
    gate("save.own", objs.get("SceneSetup_camera", {}).get("own") is True
         and objs.get("shotCam", {}).get("own") is False)
    gate("save.shape", near(objs["shotCam"]["shape"].get("focalLength", -1), 50.0),
         objs["shotCam"]["shape"].get("focalLength"))
    aobjs = dict((o["name"], o) for o in header.get("objects") or [])
    gate("save.anim", sorted(aobjs) == ["SceneSetup_camera", "prop", "shotCam"]
         and "focalLength" in aobjs["shotCam"]["shape"], sorted(aobjs))

    # ---- another scene: shotCam in a namespace, everything at zero, B's camera somewhere else
    cmds.namespace(add="shot")
    shot = cmds.ls(cmds.rename(shot, "shot:shotCam"), long=True)[0]
    shot_shape = cmds.listRelatives(shot, shapes=True, fullPath=True)[0]
    for node in (wrist_a, wrist_b, a_cam, b_cam, shot, prop):
        cmds.cutKey(node, clear=True)
    cmds.cutKey(shot_shape, clear=True)
    for plug in (a_cam + ".translateX", b_cam + ".translateX", shot + ".translateX",
                 shot + ".rotateY", prop + ".translateY"):
        cmds.setAttr(plug, 0.0)
    cmds.setAttr(shot_shape + ".focalLength", 35.0)
    cmds.currentTime(0)
    evaluate()

    # ---- pose: B + the namespaced shot camera selected
    ok, text = ap.apply(pose, [b.main, shot])
    evaluate()
    say("pose:", text)
    gate("pose.ok", ok)
    gate("pose.b_cam_own", near(get(b_cam + ".translateX"), 12.0), get(b_cam + ".translateX"))
    gate("pose.a_cam_untouched", near(get(a_cam + ".translateX"), 0.0),
         get(a_cam + ".translateX"))
    gate("pose.shot_by_name", near(get(shot + ".translateX"), 5.0)
         and near(get(shot + ".rotateY"), 30.0), (get(shot + ".translateX"),
                                                    get(shot + ".rotateY")))
    gate("pose.shot_focal", near(get(shot_shape + ".focalLength"), 50.0),
         get(shot_shape + ".focalLength"))
    gate("pose.prop_exact", near(get(prop + ".translateY"), 7.0), get(prop + ".translateY"))
    cmds.undo()
    evaluate()
    gate("pose.undo", near(get(b_cam + ".translateX"), 0.0)
         and near(get(shot + ".translateX"), 0.0)
         and near(get(shot_shape + ".focalLength"), 35.0)
         and near(get(prop + ".translateY"), 0.0),
         (get(b_cam + ".translateX"), get(shot + ".translateX"),
          get(shot_shape + ".focalLength"), get(prop + ".translateY")))

    # ---- B alone: the shot camera is not searched for by name
    ok, text = ap.apply(pose, [b.main])
    evaluate()
    say("unsel:", text)
    gate("unsel.shot_not_searched", near(get(shot + ".translateX"), 0.0)
         and "not in the scene: shotCam" in text, get(shot + ".translateX"))
    gate("unsel.prop", near(get(prop + ".translateY"), 7.0))
    gate("unsel.b_cam", near(get(b_cam + ".translateX"), 12.0))
    cmds.undo()
    evaluate()

    # ---- the camera alone
    before_wrist = get(wrist_b + ".rotateZ")
    ok, text = ap.apply(pose, [shot])
    evaluate()
    say("alone:", text)
    gate("alone.ok", ok and ap.OBJECTS_ALONE in text, text)
    gate("alone.shot", near(get(shot + ".translateX"), 5.0)
         and near(get(shot_shape + ".focalLength"), 50.0))
    gate("alone.b_untouched", near(get(wrist_b + ".rotateZ"), before_wrist)
         and near(get(b_cam + ".translateX"), 0.0))
    cmds.undo()
    evaluate()

    # ---- the animation onto B + the shot camera
    ok, text = animapply.apply(header, frames, [b.main, shot])
    say("anim:", text)
    gate("anim.ok", ok, text)
    goto(10)
    gate("anim.shot_tx", near(get(shot + ".translateX"), 15.0), get(shot + ".translateX"))
    gate("anim.shot_focal", near(get(shot_shape + ".focalLength"), 60.0),
         get(shot_shape + ".focalLength"))
    gate("anim.b_cam_own", near(get(b_cam + ".translateX"), 22.0), get(b_cam + ".translateX"))
    gate("anim.prop", near(get(prop + ".translateY"), 8.0), get(prop + ".translateY"))
    gate("anim.a_cam_untouched", not cmds.keyframe(a_cam + ".translateX", query=True))
    goto(0)
    cmds.undo()
    gate("anim.undo_one_chunk", not cmds.keyframe(shot + ".translateX", query=True)
         and not cmds.keyframe(shot_shape + ".focalLength", query=True)
         and not cmds.keyframe(b_cam + ".translateX", query=True),
         (cmds.keyframe(shot + ".translateX", query=True),
          cmds.keyframe(b_cam + ".translateX", query=True)))
except Exception:                                        # noqa: BLE001
    say(traceback.format_exc())
    RESULTS.append(False)
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
os._exit(0)
