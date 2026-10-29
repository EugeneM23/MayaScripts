"""Montage slot import, verified: the composite against the clips themselves.

    mayapy docs/superpowers/plans/verify_montage_import.py [phases...]

Phases:

  compose  the composition in Maya with no FBX and no editor: three skeletons
           built here with LINEAR curves, so every composed value has a closed
           form the verify computes itself.
  import   the whole `montage.import_clip` over fixture FBXs: the composite
           against the imported source clips read at the mapped times.
  live     the real thing against the open editor: Atone's own montages
           imported, and every composed bone compared with the ENGINE's own
           reading of the source clips at the mapped times.

Default: compose import. `live` needs the editor up with Remote Execution on.

Nothing is written into the Unreal project and nothing is saved.
"""

import math
import os
import sys

#  .../MayaScripts/docs/superpowers/plans/this file
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
for path in (PLUGIN, REPO):
    if path not in sys.path:
        sys.path.insert(0, path)

import maya.standalone                                          # noqa: E402
maya.standalone.initialize(name="python")

import maya.cmds as cmds                                        # noqa: E402
import maya.mel as mel                                          # noqa: E402
from maya.api import OpenMaya as om                             # noqa: E402

from maya_uebridge import animimport, montage, records           # noqa: E402

FPS = 30.0
JOINTS = (("root", (0.0, 0.0, 0.0)),
          ("pelvis", (0.0, 95.0, 0.0)),
          ("spine_01", (0.0, 12.0, 0.0)))

#  Clip A and clip B, defined as closed forms of the source FRAME, so the
#  verify can compute every composed value without asking our own code.
#  Keyed with LINEAR tangents, so a fractional frame is exactly the form.
A_KEYS = 21            # 0..20 at 30 fps = 0.6667 s, like Atone's 1P clips
B_KEYS = 16


def clip_a(channel, frame):
    #  the pelvis turns about all THREE axes, so a euler read between two
    #  frames is NOT the engine's slerp of them - the slerp path is what the
    #  composer takes for a rotate triple, and the gates below prove it with
    #  a positive control
    return {"root.translateX": 1.0 * frame,
            "root.Pose_3": 0.1 * frame,
            "root.Pose_7": 2.0 * frame,
            "pelvis.rotateX": 6.0 * frame,
            "pelvis.rotateY": 7.0 * frame,
            "pelvis.rotateZ": -5.0 * frame,
            "spine_01.rotateZ": -3.0 * frame}[channel]


def clip_b(channel, frame):
    #  pelvis.rotateY starts at 350 while A's is near 70 at the boundary: a
    #  280 degree step, which is a wrap and must be composed as one.
    return {"root.translateX": 100.0 - 2.0 * frame,
            "root.Pose_3": 9.0,                  # still: no curve at all
            "pelvis.rotateX": 4.0 * frame,
            "pelvis.rotateY": 350.0 - 2.0 * frame,
            "pelvis.rotateZ": 3.0 * frame,
            "spine_01.rotateZ": 4.0 * frame}[channel]


TRIPLE = ("pelvis.rotateX", "pelvis.rotateY", "pelvis.rotateZ")
A_CHANNELS = ("root.translateX", "root.Pose_3", "root.Pose_7",
              "spine_01.rotateZ") + TRIPLE
B_CURVES = ("root.translateX", "spine_01.rotateZ") + TRIPLE
B_STATIC = ("root.Pose_3",)        # the attribute exists, nothing animates it
#  root.Pose_7 is absent from B: the composite must HOLD the last value and
#  say so.

CLIP_A = "/Game/Fixture/Clip_A"
CLIP_B = "/Game/Fixture/Clip_B"
MONTAGE = "/Game/Fixture/AM_Fixture"

#  Three spans over two clips at three rates - the shape of Atone's own
#  AM_SwordShield_1p_blockreact_mid (1.5 / 0.8 / 1.2).
SEGMENTS = [
    {"clip": CLIP_A, "clip_name": "Clip_A", "start_pos": 0.0,
     "anim_start_time": 0.0, "anim_end_time": 0.3, "anim_play_rate": 1.5,
     "looping_count": 1, "additive": "<AdditiveAnimationType.AAT_NONE: 0>"},
    {"clip": CLIP_B, "clip_name": "Clip_B", "start_pos": 0.2,
     "anim_start_time": 0.1, "anim_end_time": 0.5, "anim_play_rate": 0.8,
     "looping_count": 1, "additive": "<AdditiveAnimationType.AAT_NONE: 0>"},
    {"clip": CLIP_A, "clip_name": "Clip_A", "start_pos": 0.7,
     "anim_start_time": 0.2, "anim_end_time": 0.6666667,
     "anim_play_rate": 1.2, "looping_count": 1,
     "additive": "<AdditiveAnimationType.AAT_NONE: 0>"}]

#  Atone's own shape: the scan windows are STATES on the montage's own clock
#  (no clip carries a notify), beside point notifies of other classes. One of
#  these is named `GameplayEvent Window` - two of the project's 90 are.
SCAN = "AnimNotifyState_MeleeScanWindow"
NOTIFIES = [
    {"name": "MeleeScanWindow", "class": SCAN, "state": True,
     "trigger": 0.2, "duration": 0.1},
    {"name": "Footstep", "class": "AnimNotify_Footstep", "state": False,
     "trigger": 0.4, "duration": 0.0},
    {"name": "GameplayEvent Window", "class": SCAN, "state": True,
     "trigger": 0.6, "duration": 0.3}]

PAYLOAD = {"montages": {MONTAGE: {
    "name": "AM_Fixture", "length": 1.0889, "skeleton": "SK_Fixture",
    "sections": [], "notifies": NOTIFIES,
    "slots": [{"slot": "1P", "segments": SEGMENTS},
              {"slot": "DefaultSlot", "segments": SEGMENTS[:1]}]}}}

FAILED = []
PASSED = []


def gate(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("{0} {1}{2}".format("ok  " if ok else "FAIL", name,
                              "  -  " + detail if detail else ""))


def close(name, got, want, tol, unit=""):
    gate(name, abs(got - want) <= tol,
         "{0:.7f} against {1:.7f} {2}(tol {3:g})".format(got, want, unit, tol))


# ------------------------------------------------------------ the fixture

def build_skeleton(namespace, channels, curves, statics, forms):
    """A joint chain in `namespace` with `channels` keyed by `forms`.

    `namespace` "" builds it at the root: the FBX exporter writes namespaces
    into the file (trap 61), so a fixture meant to stand in for an Unreal
    export must carry plain bone names.
    """
    if namespace and not cmds.namespace(exists=namespace):
        cmds.namespace(addNamespace=namespace)
    cmds.namespace(setNamespace=":")
    parent = None
    nodes = {}
    for leaf, offset in JOINTS:
        node = cmds.createNode("joint", parent=parent, skipSelect=True,
                               name=("{0}:{1}".format(namespace, leaf)
                                     if namespace else leaf))
        cmds.setAttr(node + ".translate", *offset)
        nodes[leaf] = node
        parent = node
    for channel in channels:
        leaf, attr = channel.split(".")
        if attr.startswith("Pose_"):
            cmds.addAttr(nodes[leaf], longName=attr, attributeType="double",
                         keyable=True)
    keys = A_KEYS if forms is clip_a else B_KEYS
    for channel in curves:
        leaf, attr = channel.split(".")
        plug = "{0}.{1}".format(nodes[leaf], attr)
        for frame in range(keys):
            cmds.setKeyframe(plug, time=frame, value=forms(channel, frame))
        cmds.keyTangent(plug, edit=True, itt="linear", ott="linear")
    for channel in statics:
        leaf, attr = channel.split(".")
        cmds.setAttr("{0}.{1}".format(nodes[leaf], attr),
                     forms(channel, 0))
    return nodes


def fixture():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")                # 30 fps, the project's rate
    build_skeleton("srcA", A_CHANNELS, A_CHANNELS, (), clip_a)
    build_skeleton("srcB", B_CURVES + B_STATIC, B_CURVES, B_STATIC, clip_b)
    #  the target is what `animimport.import_clip` of clip A leaves behind
    return build_skeleton("AM_Fixture_1P", A_CHANNELS, A_CHANNELS, (), clip_a)


# ------------------------------------------- the expectation, computed here

def spans_here():
    """The segments expanded, by this script's own arithmetic."""
    out = []
    for segment in SEGMENTS:
        lo, hi = segment["anim_start_time"], segment["anim_end_time"]
        rate = segment["anim_play_rate"]
        length = abs(hi - lo) / abs(rate)
        out.append((segment["clip"], segment["start_pos"],
                    segment["start_pos"] + length, lo, rate))
    return out


def expected(channel, frame):
    """What the montage shows for `channel` at target `frame`."""
    seconds = frame / FPS
    chosen = None
    for span in spans_here():
        if span[1] <= seconds + 1e-9:
            chosen = span
    clip, t0, t1, src, rate = chosen
    inside = min(max(seconds, t0), t1)
    source_seconds = src + (inside - t0) * rate
    source_frame = source_seconds * FPS
    forms = clip_a if clip == CLIP_A else clip_b
    if clip == CLIP_B and channel == "root.Pose_7":
        return None                     # B has no such attribute: HELD
    if clip == CLIP_B and channel == "root.Pose_3":
        return 9.0                      # still on B
    keys = (A_KEYS if clip == CLIP_A else B_KEYS) - 1
    return forms(channel, min(max(source_frame, 0.0), keys))


def last_frame():
    end = spans_here()[-1][2]
    return int(math.floor(end * FPS + 1e-6))


def source_frame(frame):
    """(clip, source frame) the montage shows at target `frame`, by this
    script's own arithmetic."""
    seconds = frame / FPS
    chosen = None
    for span in spans_here():
        if span[1] <= seconds + 1e-9:
            chosen = span
    clip, t0, t1, src, rate = chosen
    inside = min(max(seconds, t0), t1)
    return clip, (src + (inside - t0) * rate) * FPS


def _quat(degrees_xyz):
    from maya.api import OpenMaya as om
    return om.MEulerRotation(*[math.radians(v) for v in degrees_xyz],
                             om.MEulerRotation.kXYZ).asQuaternion()


def expected_rotation(frame, slerp=True):
    """The pelvis's rotation at target `frame`, as the engine would read it:
    the two neighbouring source frames SLERPED. `slerp` False gives the euler
    lerp instead - the positive control, which must differ."""
    from maya.api import OpenMaya as om

    clip, source = source_frame(frame)
    forms = clip_a if clip == CLIP_A else clip_b
    keys = (A_KEYS if clip == CLIP_A else B_KEYS) - 1
    source = min(max(source, 0.0), keys)
    low, high = math.floor(source), math.ceil(source)
    share = 0.0 if high == low else (source - low) / float(high - low)
    sides = [[forms(channel, side) for channel in TRIPLE]
             for side in (low, high)]
    if not slerp:
        return _quat([a + (b - a) * share for a, b in zip(*sides)])
    if share <= 0.0:
        return _quat(sides[0])
    return om.MQuaternion.slerp(_quat(sides[0]), _quat(sides[1]), share)


def _angle(first, second):
    dot = (first.x * second.x + first.y * second.y + first.z * second.z
           + first.w * second.w)
    return 2.0 * math.degrees(math.acos(min(1.0, abs(dot))))


# ------------------------------------------------------------ phase compose

def phase_compose():
    print("\n--- compose: the arithmetic in Maya, no FBX, no editor")
    target = fixture()
    plan = montage.plan_for(PAYLOAD, MONTAGE, "1P")
    gate("the plan has three spans", len(plan.spans) == 3,
         "{0}".format([round(s.t1, 4) for s in plan.spans]))
    close("the take's end is the slot's own", plan.end, spans_here()[-1][2],
          1e-9, "s ")

    done = montage.compose(plan, {CLIP_A: "AM_Fixture_1P", CLIP_B: "srcB"},
                           "AM_Fixture_1P", FPS)
    frames = last_frame()
    gate("the last frame is floor(end x fps)", done["frames"] == frames,
         "{0} against {1}".format(done["frames"], frames))

    #  the pelvis turns about three axes: what the composite must show is the
    #  SLERP of the two neighbouring source frames, as the engine reads its
    #  own keys - not a euler lerp of them
    from maya.api import OpenMaya as om
    worst_rot = 0.0
    control = 0.0
    at_rot = -1
    for frame in range(frames + 1):
        got = _quat([cmds.getAttr("AM_Fixture_1P:{0}".format(channel),
                                  time=frame) for channel in TRIPLE])
        error = _angle(got, expected_rotation(frame))
        if error > worst_rot:
            worst_rot, at_rot = error, frame
        control = max(control, _angle(expected_rotation(frame),
                                      expected_rotation(frame, slerp=False)))
    close("the pelvis is the slerp of the source's keys", worst_rot, 0.0,
          0.001, "at frame {0} ".format(at_rot))
    gate("a euler lerp would have been another rotation", control > 0.05,
         "the two readings differ by up to {0:.3f} deg".format(control))

    #  every other channel, every frame, against the closed form
    worst = {}
    for channel in [c for c in A_CHANNELS if c not in TRIPLE]:
        leaf, attr = channel.split(".")
        plug = "AM_Fixture_1P:{0}.{1}".format(leaf, attr)
        bad = 0.0
        at = -1
        for frame in range(frames + 1):
            want = expected(channel, frame)
            if want is None:
                continue
            got = cmds.getAttr(plug, time=frame)
            error = abs(got - want)
            if attr.startswith("rotate"):
                #  a wrap is composed as a turn: the same rotation
                error = min(error, abs(error - 360.0), abs(error + 360.0))
            if error > bad:
                bad, at = error, frame
        worst[channel] = (bad, at)
        close("{0} on every frame".format(channel), bad, 0.0, 1e-4,
              "at frame {0} ".format(at))

    #  the wrap itself: the composed curve must not step 280 degrees
    steps = []
    plug = "AM_Fixture_1P:pelvis.rotateY"
    for frame in range(1, frames + 1):
        steps.append(abs(cmds.getAttr(plug, time=frame)
                         - cmds.getAttr(plug, time=frame - 1)))
    gate("no wrap is left in the composed rotation", max(steps) < 180.0,
         "worst step {0:.3f} deg".format(max(steps)))
    raw = abs(clip_b("pelvis.rotateY", 0) - clip_a("pelvis.rotateY", 9))
    gate("the fixture really had a wrap to compose", raw > 180.0,
         "{0:.1f} deg between the clips at the boundary".format(raw))

    #  a channel one clip does not carry is held and named
    gate("a channel B lacks is held and named", done["held"] == ["root.Pose_7"],
         "{0}".format(done["held"]))
    held_plug = "AM_Fixture_1P:root.Pose_7"
    inside_b = [f for f in range(frames + 1)
                if expected("root.Pose_7", f) is None]
    if inside_b:
        first = inside_b[0]
        before = cmds.getAttr(held_plug, time=first - 1)
        during = [cmds.getAttr(held_plug, time=f) for f in inside_b]
        gate("the held channel holds its last value",
             max(abs(v - before) for v in during) < 1e-6,
             "{0:.4f} through frames {1}..{2}".format(before, inside_b[0],
                                                      inside_b[-1]))

    #  a still channel on B is its value, not a curve's
    still = [f for f in range(frames + 1) if expected("root.Pose_3", f) == 9.0]
    if still:
        values = [cmds.getAttr("AM_Fixture_1P:root.Pose_3", time=f)
                  for f in still]
        gate("a still channel on B reads its own value",
             max(abs(v - 9.0) for v in values) < 1e-6,
             "{0:.4f} through {1} frames".format(values[0], len(values)))

    #  keys on whole frames, one a frame, nothing past the end
    curve_times = cmds.keyframe("AM_Fixture_1P:root.translateX", query=True,
                                timeChange=True) or []
    gate("a key on every whole frame and no other",
         curve_times == [float(f) for f in range(frames + 1)],
         "{0} keys, {1}..{2}".format(len(curve_times),
                                     curve_times[0] if curve_times else None,
                                     curve_times[-1] if curve_times else None))

    #  the cuts the status line reports
    reported = montage.cuts(plan, FPS)
    want_cuts = [round(span[1] * FPS, 1) for span in spans_here()[1:]]
    gate("the cuts are the boundaries in frames", reported == want_cuts,
         "{0} against {1}".format(reported, want_cuts))

    #  the refusals
    gate("the good slot is not refused",
         montage.refusal(PAYLOAD, MONTAGE, "1P") == "")
    gate("a slot the montage lacks is refused",
         "UpperBody" in montage.refusal(PAYLOAD, MONTAGE, "UpperBody"))
    additive = {"montages": {MONTAGE: {"name": "AM_Fixture", "slots": [
        {"slot": "1P", "segments": [dict(SEGMENTS[0], additive=
         "<AdditiveAnimationType.AAT_ROTATION_OFFSET_MESH_SPACE: 2>")]}]}}}
    gate("an additive slot is refused by name",
         "additive" in montage.refusal(additive, MONTAGE, "1P"),
         montage.refusal(additive, MONTAGE, "1P"))


# ------------------------------------------------------------- phase import

def export_fixture_fbx(path):
    """The fixture's skeleton out as an FBX, bones and curves as they are.

    The scene holds exactly one clip at the root namespace, so the file comes
    out with plain bone names - what an Unreal export looks like.
    """
    joints = [n for n in cmds.ls(type="joint", long=True) or []]
    cmds.select(joints, replace=True)
    animimport.ensure_fbx_plugin()
    mel.eval('FBXResetExport')
    mel.eval('FBXExportBakeComplexAnimation -v false')
    mel.eval('FBXExportInputConnections -v false')
    mel.eval('FBXExportSkins -v false')
    mel.eval('FBXExportShapes -v false')
    #  There is no custom-attribute flag on this build (measured: neither
    #  FBXExportCustomAttributes nor an Export|...|CustomAttributes property)
    #  and the exporter writes animated custom attributes anyway - the
    #  fixture's Pose_* curves make the round trip, which is 51 of this
    #  phase's 150 readings (a UE root's own curves, trap 40).
    mel.eval('FBXExportUpAxis y')
    mel.eval('FBXExport -f "{0}" -s'.format(path.replace("\\", "/")))
    cmds.select(clear=True)
    return os.path.isfile(path) and os.path.getsize(path) > 0


def phase_import():
    print("\n--- import: the whole import_clip over fixture FBXs")
    folder = os.path.join(cmds.internalVar(userTmpDir=True),
                          "montage_verify").replace("\\", "/")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    paths = {}
    for clip, channels, curves, statics, forms in (
            (CLIP_A, A_CHANNELS, A_CHANNELS, (), clip_a),
            (CLIP_B, B_CURVES + B_STATIC, B_CURVES, B_STATIC, clip_b)):
        #  one clip a scene, at the root namespace
        cmds.file(new=True, force=True)
        cmds.currentUnit(time="ntsc")
        build_skeleton("", channels, curves, statics, forms)
        path = os.path.join(folder, clip.rsplit("/", 1)[-1] + ".fbx")
        ok = export_fixture_fbx(path)
        gate("the fixture {0} exported".format(clip.rsplit("/", 1)[-1]), ok,
             path)
        paths[clip] = path

    plan = montage.plan_for(PAYLOAD, MONTAGE, "1P")
    ref = montage.ref_of(montage.write_plan(folder, plan, paths, FPS))
    gate("the plan file is a montage reference", montage.is_ref(ref), ref)

    #  a fresh scene: the import must stand on its own
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    info = montage.import_clip(ref, "AM_Fixture_1P", set_timeline=True)
    frames = last_frame()
    gate("the import reports the take's frames",
         info["montage"]["frames"] == frames + 1,
         "{0} against {1}".format(info["montage"]["frames"], frames + 1))
    gate("the timeline is the take",
         (cmds.playbackOptions(query=True, minTime=True),
          cmds.playbackOptions(query=True, maxTime=True)) == (0.0, float(frames)),
         "{0}..{1}".format(cmds.playbackOptions(query=True, minTime=True),
                           cmds.playbackOptions(query=True, maxTime=True)))
    gate("the scratch namespaces are gone",
         not [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True,
                                            recurse=True) or []
              if "_src" in n],
         "{0}".format([n for n in cmds.namespaceInfo(
             ":", listOnlyNamespaces=True, recurse=True) or []]))
    gate("the composite is one skeleton in its own namespace",
         bool(cmds.objExists("AM_Fixture_1P:root")))

    #  the composite against the clips THEMSELVES: import each source again
    #  and read it at the mapped time with getAttr, which is not the read the
    #  composer used (`keyframe -eval`)
    for clip, namespace in ((CLIP_A, "chkA"), (CLIP_B, "chkB")):
        animimport.import_clip(paths[clip], namespace, set_timeline=False,
                               merge=False)
    #  the pelvis triple: the composite slerps the clip's two neighbouring
    #  frames, so the control slerps the IMPORTED clip's own, read here
    worst_rot = 0.0
    at_rot = -1
    for frame in range(frames + 1):
        clip, source = source_frame(frame)
        space = "chkA" if clip == CLIP_A else "chkB"
        low, high = math.floor(source), math.ceil(source)
        share = 0.0 if high == low else (source - low) / float(high - low)
        sides = [_quat([cmds.getAttr("{0}:{1}".format(space, channel),
                                     time=side) for channel in TRIPLE])
                 for side in (low, high)]
        want = sides[0] if share <= 0.0 else om.MQuaternion.slerp(
            sides[0], sides[1], share)
        got = _quat([cmds.getAttr("AM_Fixture_1P:{0}".format(channel),
                                  time=frame) for channel in TRIPLE])
        if _angle(got, want) > worst_rot:
            worst_rot, at_rot = _angle(got, want), frame
    close("the pelvis against the imported clips' own slerp", worst_rot, 0.0,
          1e-4, "at frame {0} ".format(at_rot))

    worst = 0.0
    where = ""
    compared = 0
    for channel in [c for c in A_CHANNELS if c not in TRIPLE]:
        leaf, attr = channel.split(".")
        plug = "AM_Fixture_1P:{0}.{1}".format(leaf, attr)
        for frame in range(frames + 1):
            clip, mapped = source_frame(frame)
            check = "chkA" if clip == CLIP_A else "chkB"
            source_plug = "{0}:{1}.{2}".format(check, leaf, attr)
            if not cmds.objExists(source_plug):
                continue
            want = cmds.getAttr(source_plug, time=mapped)
            got = cmds.getAttr(plug, time=frame)
            compared += 1
            error = abs(got - want)
            if attr.startswith("rotate"):
                error = min(error, abs(error - 360.0), abs(error + 360.0))
            if error > worst:
                worst, where = error, "{0} at frame {1}".format(channel, frame)
    #  a comparison that compared nothing is a gate that cannot fail: the
    #  first run of this phase skipped every channel (the fixture's FBX
    #  carried its namespace into the file, trap 61) and read 0.0
    gate("the comparison really ran", compared >= 3 * (frames + 1),
         "{0} readings".format(compared))
    close("every frame against the imported clips", worst, 0.0, 1e-4,
          where + " ")

    #  the montage's scan windows as time-slider bookmarks
    marks = sorted((cmds.getAttr(node + ".timeRangeStart"),
                    cmds.getAttr(node + ".timeRangeStop"),
                    cmds.getAttr(node + ".name"))
                   for node in montage.our_bookmarks(cmds))
    gate("one bookmark a scan window, the point notify left out",
         len(marks) == 2, "{0} bookmarks: {1}".format(len(marks), marks))
    gate("the first window's frames snapped outward",
         marks and marks[0][:2] == (6.0, 9.0), "{0}".format(marks[:1]))
    gate("the second window keeps the notify's own name",
         len(marks) > 1 and marks[1][2] == "GameplayEvent Window",
         "{0}".format(marks[1:]))
    gate("the second window's frames",
         len(marks) > 1 and marks[1][:2] == (18.0, 27.0),
         "{0}".format(marks[1:]))
    gate("each one carries the montage and the slot",
         all(cmds.getAttr(node + "." + montage.MARK_ATTR) ==
             "AM_Fixture · 1P" for node in montage.our_bookmarks(cmds)),
         "{0}".format([cmds.getAttr(n + "." + montage.MARK_ATTR)
                       for n in montage.our_bookmarks(cmds)]))
    gate("the colour is ours",
         all(tuple(round(c, 3) for c in cmds.getAttr(node + ".color")[0])
             == tuple(round(c, 3) for c in montage.SCAN_COLOUR)
             for node in montage.our_bookmarks(cmds)))
    gate("the press counted them", info["montage"]["windows"] == 2,
         "{0}".format(info["montage"].get("windows")))
    gate("the status line names them",
         "2 scan windows" in (info.get("warning") or ""),
         info.get("warning") or "")

    #  a bookmark of the animator's own must outlive a re-import, and ours
    #  must be replaced rather than piled up
    mine = cmds.createNode("timeSliderBookmark", skipSelect=True,
                           name="animatorsOwn")
    cmds.setAttr(mine + ".timeRangeStart", 2.0)
    cmds.setAttr(mine + ".timeRangeStop", 4.0)
    was = set(cmds.ls(type="timeSliderBookmark"))
    montage.import_clip(ref, "AM_Fixture_again", set_timeline=False)
    now = set(cmds.ls(type="timeSliderBookmark"))
    gate("a re-import replaces ours", len(montage.our_bookmarks(cmds)) == 2,
         "{0}".format(sorted(montage.our_bookmarks(cmds))))
    gate("the animator's own bookmark survives it", cmds.objExists(mine))
    gate("nothing piled up", len(now) == 3,
         "{0} bookmarks: {1}".format(len(now), sorted(now)))

    #  the writing is unrecorded: a montage import is FBX imports, which an
    #  undo chunk does not take back (measured), so a Ctrl+Z must not strip
    #  the bookmarks off a take that stays
    fresh = sorted(now - was)
    cmds.undo()
    gate("a Ctrl+Z after the press leaves the bookmarks",
         all(cmds.objExists(node) for node in fresh),
         "{0}".format([node for node in fresh if not cmds.objExists(node)]))
    gate("and leaves the take", bool(cmds.objExists("AM_Fixture_again:root")))

    #  a slot too short for a window gets none: the DefaultSlot ends at 0.2 s
    short = montage.plan_for(PAYLOAD, MONTAGE, "DefaultSlot")
    gate("a slot that ends before the first window holds none",
         not short.windows, "{0}".format(list(short.windows)))

    #  a plan whose clip is gone refuses and leaves the scene alone
    before = set(cmds.ls(long=True))
    gone = montage.write_plan(folder, plan, {CLIP_A: paths[CLIP_A],
                                             CLIP_B: folder + "/nope.fbx"},
                              FPS)
    try:
        montage.import_clip(montage.ref_of(gone), "AM_Gone_1P")
        gate("a missing clip refuses", False, "it did not")
    except RuntimeError as error:
        gate("a missing clip refuses by name", "Clip_B" in str(error),
             str(error))
    gate("the refused import changed nothing",
         set(cmds.ls(long=True)) == before)


# --------------------------------------------------------------- phase live

#  Atone's own montages: one slot of three slices of ONE clip at three rates,
#  one slot of three DIFFERENT clips, and the montage the animator pointed at.
LIVE = (("/Game/Prototype/Animation/PlayerCharacter/Block/Montages/"
         "AM_LongSword_Block_Stun", "DefaultSlot"),
        ("/Game/Prototype/Animation/PlayerCharacter/Block/Montages/"
         "AM_LongSword_Block_Stun", "1P"),
        ("/Game/Prototype/Animation/PlayerCharacter/Block/Montages/"
         "AM_SwordShield_1p_blockreact_mid", "1P"),
        #  four MeleeScanWindow states (measured 0.600+0.397, 1.000+0.115,
        #  1.114+0.187, 1.301+0.107) - the bookmarks' live case
        ("/Game/Prototype/Animation/PlayerCharacter/Weapons/Longsword/"
         "Montages/AM_Longsword_Attack_Left_Forward_Hold", "1P"))

LIVE_BONES = ("pelvis", "spine_03", "hand_r", "foot_l", "head")

#  The editor's own reading of a clip's bone at a time:
#  `AnimationLibrary.get_bone_pose_for_time` (measured 2026-10-29 - it answers
#  the bone's LOCAL transform). Comparing a local transform across the two
#  programs would be an axis-convention minefield, so what travels is the
#  ANGLE from the clip's own first sampled pose: a rigid change of basis
#  leaves the angle between two rotations alone.
_POSE_SCRIPT = '''\
import json
import os
import traceback

import unreal

_OUT = %(out)s
_ASKS = %(asks)s

result = {"ok": False, "error": "", "poses": []}

try:
    cache = {}
    for clip, bone, time in _ASKS:
        anim = cache.get(clip)
        if anim is None:
            anim = unreal.load_asset(clip)
            cache[clip] = anim
        transform = unreal.AnimationLibrary.get_bone_pose_for_time(
            anim, bone, float(time), False)
        rotation = transform.rotation
        result["poses"].append([float(rotation.x), float(rotation.y),
                                float(rotation.z), float(rotation.w)])
    result["ok"] = True
except Exception:
    result["error"] = traceback.format_exc()
finally:
    try:
        with open(_OUT, "w") as handle:
            json.dump(result, handle)
    except Exception:
        unreal.log_error("pose probe: cannot write the reply")
    print(%(marker)s)
'''


def _angle_between(first, second):
    """Degrees between two unit quaternions (x, y, z, w). Convention-free."""
    dot = sum(a * b for a, b in zip(first, second))
    return 2.0 * math.degrees(math.acos(min(1.0, abs(dot))))


def _maya_quat(node, frame):
    """The node's local rotation at `frame` as (x, y, z, w)."""
    from maya.api import OpenMaya as om
    order = cmds.getAttr(node + ".rotateOrder")
    values = [math.radians(cmds.getAttr("{0}.rotate{1}".format(node, axis),
                                        time=frame))
              for axis in "XYZ"]
    euler = om.MEulerRotation(values[0], values[1], values[2], order)
    quat = euler.asQuaternion()
    return (quat.x, quat.y, quat.z, quat.w)


def phase_live():
    import json

    from maya_uebridge import uelink, uescripts, window

    print("\n--- live: Atone's own montages against the engine's own reading")
    folder = os.path.join(window.temp_folder(), "montage_verify")
    out = os.path.join(window.temp_folder(), "verify.json")

    packages = sorted(set(package for package, _slot in LIVE))
    plans = uelink.run_script(uescripts.montage_plan_script(out, packages),
                              out, project="Atone")
    gate("the editor answered for every montage",
         len(plans.get("montages") or {}) == len(packages),
         "{0} of {1}".format(len(plans.get("montages") or {}), len(packages)))

    for package, slot in LIVE:
        name = montage.montage_name(plans, package)
        print("\n  {0} · {1}".format(name, slot))
        refusal = montage.refusal(plans, package, slot)
        gate("{0} · {1} is importable".format(name, slot), refusal == "",
             refusal)
        if refusal:
            continue
        plan = montage.plan_for(plans, package, slot)

        clips = uelink.run_script(
            uescripts.montage_export_script(out, plan.clips, folder), out,
            project="Atone")
        paths = dict((p, row.get("path") or "")
                     for p, row in (clips.get("clips") or {}).items())
        gate("the editor exported every clip of the slot",
             not clips.get("failed") and len(paths) == len(plan.clips),
             "{0} clips{1}".format(len(paths),
                                   ", failed " + str(clips.get("failed"))
                                   if clips.get("failed") else ""))
        if len(paths) != len(plan.clips):
            continue

        cmds.file(new=True, force=True)
        reference = montage.ref_of(
            montage.write_plan(folder, plan, paths, 30.0))
        info = montage.import_clip(reference,
                                   records.namespace_for(
                                       montage.clip_name(plan.montage, slot),
                                       ()))
        namespace = info["namespace"]
        frames = info["montage"]["frames"]
        gate("{0} · {1} came in as one take".format(name, slot),
             frames > 1 and cmds.objExists(namespace + ":root"),
             "{0} frames, cuts {1}, {2} clip(s)".format(
                 frames, info["montage"]["cuts"],
                 len(info["montage"]["clips"])))
        fps = animimport.scene_fps()
        rows = montage.samples(plan, fps)

        #  the scan windows as bookmarks, against the ENGINE's own numbers:
        #  the frames are worked out here from the raw reply, not asked of the
        #  code under test
        engine = []
        for row in (plans["montages"][package].get("notifies") or []):
            if str(row.get("class") or "") != montage.SCAN_CLASS:
                continue
            start = float(row.get("trigger") or 0.0)
            stop = min(start + float(row.get("duration") or 0.0), plan.end)
            if start >= plan.end:
                continue
            low = math.floor(start * fps + 1e-6)
            high = max(math.ceil(stop * fps - 1e-6), low + 1)
            engine.append((float(low), float(high)))
        got = sorted((cmds.getAttr(node + ".timeRangeStart"),
                      cmds.getAttr(node + ".timeRangeStop"))
                     for node in montage.our_bookmarks(cmds))
        gate("{0} · {1}: the bookmarks are the engine's own scan "
             "windows".format(name, slot), got == sorted(engine),
             "{0} against {1}".format(got, sorted(engine)))
        gate("{0} · {1}: each bookmark is named for its notify".format(
            name, slot),
             all(cmds.getAttr(node + ".name")
                 for node in montage.our_bookmarks(cmds)),
             "{0}".format([cmds.getAttr(n + ".name")
                           for n in montage.our_bookmarks(cmds)]))

        #  what to ask the engine: a handful of bones, every fourth frame
        bones = [b for b in LIVE_BONES
                 if cmds.objExists("{0}:{1}".format(namespace, b))]
        gate("the clip's bones are in the scene",
             len(bones) == len(LIVE_BONES), ", ".join(bones))
        asks = []
        wanted = [row for row in rows if row[0] % 4 == 0]
        for bone in bones:
            for _frame, clip, time in [rows[0]] + wanted:
                asks.append([clip, bone, time])
        answer = uelink.run_script(
            _POSE_SCRIPT % {"out": json.dumps(out.replace("\\", "/")),
                            "asks": json.dumps(asks),
                            "marker": json.dumps(uescripts.MARKER)},
            out, project="Atone")
        poses = answer.get("poses") or []
        gate("the engine answered every pose asked",
             len(poses) == len(asks),
             "{0} of {1}".format(len(poses), len(asks)))
        if len(poses) != len(asks):
            continue

        #  the slot's clips imported plainly beside the composite: read at the
        #  SAME mapped times they are the interpolation floor - the composite
        #  can be no closer to the engine than Maya's own reading of the clip
        checks = {}
        for index, clip in enumerate(plan.clips):
            space = "chk{0}".format(index)
            animimport.import_clip(paths[clip], space, set_timeline=False,
                                   merge=False)
            checks[clip] = space

        #  the angle each bone has turned from the take's first pose, in each
        #  program; a rigid change of basis leaves it alone
        worst = 0.0
        where = ""
        floor = 0.0
        apart = 0.0
        index = 0
        compared = 0
        for bone in bones:
            node = "{0}:{1}".format(namespace, bone)
            engine_first = poses[index]
            maya_first = _maya_quat(node, rows[0][0])
            clip_first = _maya_quat("{0}:{1}".format(checks[rows[0][1]], bone),
                                    rows[0][2] * fps)
            index += 1
            for frame, clip, time in wanted:
                engine = poses[index]
                index += 1
                theirs = _angle_between(engine_first, engine)
                ours = _angle_between(maya_first, _maya_quat(node, frame))
                mine = _angle_between(
                    clip_first,
                    _maya_quat("{0}:{1}".format(checks[clip], bone),
                               time * fps))
                compared += 1
                #  what matters: the composite against the ENGINE's own
                #  evaluation of the same clip at the same time
                if abs(theirs - ours) > worst:
                    worst = abs(theirs - ours)
                    where = ("{0} at frame {1} ({2:.4f} against the engine's "
                             "{3:.4f} deg)".format(bone, frame, ours, theirs))
                #  and two numbers that say where any difference comes from:
                #  a plainly imported clip read at the same times, and how
                #  far our reading of it sits from that
                floor = max(floor, abs(mine - theirs))
                apart = max(apart, abs(mine - ours))
        gate("the comparison really ran", compared >= 4 * len(bones),
             "{0} readings".format(compared))
        close("{0} · {1} against the engine".format(name, slot), worst, 0.0,
              0.25, where + " ")
        print("     the same clip imported plainly and read at the same times "
              "sits {0:.3f} deg from the engine; our reading of it {1:.3f} deg "
              "from that".format(floor, apart))

    #  and the card's own road, with the real editor: the press's export plus
    #  the import funnel, which is what every button, drag and square takes -
    #  on the montage WITH scan windows, so the press's own plan file carries
    #  them
    package, slot = LIVE[3]
    cmds.file(new=True, force=True)
    window._STATE["choice"] = "Atone"
    window._STATE["montage_plans"] = {}
    record = records.AnimRecord(package.rsplit("/", 1)[-1], package,
                                "SK_Mannequin_proto", None, None, None,
                                kind="montage")
    reference, fps = window._export_from_editor(records.with_slot(record, slot))
    from maya_uebridge import rigimport
    namespace, info, source = rigimport.import_source(
        reference, montage.clip_name(record.name, slot), clip_fps=fps,
        set_timeline=True)
    gate("the card's own road brings the slot in",
         bool(source) and info.get("montage", {}).get("slot") == slot,
         "{0}: {1}".format(namespace, info.get("warning", "")))
    gate("the card's own road carries the scan windows",
         info.get("montage", {}).get("windows") == 4
         and len(montage.our_bookmarks(cmds)) == 4,
         "{0} in the plan, {1} in the scene".format(
             info.get("montage", {}).get("windows"),
             len(montage.our_bookmarks(cmds))))


PHASES = {"compose": phase_compose, "import": phase_import,
          "live": phase_live}


def main():
    asked = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not asked:
        asked = ["compose", "import"]
    for name in asked:
        PHASES[name]()
    print("\n{0} of {1} gates failed".format(len(FAILED),
                                             len(FAILED) + len(PASSED)))
    for name in FAILED:
        print("  FAILED: " + name)


#  guarded, so a probe can import the fixture and the closed form without
#  running every phase (the command port sets __main__ itself, trap 17)
if __name__ == "__main__":
    main()
