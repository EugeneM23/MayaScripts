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
    return {"root.translateX": 1.0 * frame,
            "root.Pose_3": 0.1 * frame,
            "root.Pose_7": 2.0 * frame,
            "pelvis.rotateY": 7.0 * frame,
            "spine_01.rotateZ": -3.0 * frame}[channel]


def clip_b(channel, frame):
    #  pelvis.rotateY starts at 350 while A's is near 70 at the boundary: a
    #  280 degree step, which is a wrap and must be composed as one.
    return {"root.translateX": 100.0 - 2.0 * frame,
            "root.Pose_3": 9.0,                  # still: no curve at all
            "pelvis.rotateY": 350.0 - 2.0 * frame,
            "spine_01.rotateZ": 4.0 * frame}[channel]


A_CHANNELS = ("root.translateX", "root.Pose_3", "root.Pose_7",
              "pelvis.rotateY", "spine_01.rotateZ")
B_CURVES = ("root.translateX", "pelvis.rotateY", "spine_01.rotateZ")
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

PAYLOAD = {"montages": {MONTAGE: {
    "name": "AM_Fixture", "length": 1.0889, "skeleton": "SK_Fixture",
    "sections": [],
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

    #  every channel, every frame, against the closed form
    worst = {}
    for channel in A_CHANNELS:
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
    worst = 0.0
    where = ""
    compared = 0
    for channel in A_CHANNELS:
        leaf, attr = channel.split(".")
        plug = "AM_Fixture_1P:{0}.{1}".format(leaf, attr)
        for frame in range(frames + 1):
            seconds = frame / FPS
            chosen = None
            for span in spans_here():
                if span[1] <= seconds + 1e-9:
                    chosen = span
            clip, t0, t1, src, rate = chosen
            inside = min(max(seconds, t0), t1)
            source_frame = (src + (inside - t0) * rate) * FPS
            check = "chkA" if clip == CLIP_A else "chkB"
            source_plug = "{0}:{1}.{2}".format(check, leaf, attr)
            if not cmds.objExists(source_plug):
                continue
            want = cmds.getAttr(source_plug, time=source_frame)
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


PHASES = {"compose": phase_compose, "import": phase_import}


def main():
    asked = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not asked:
        asked = ["compose", "import"]
    if "live" in asked:
        from verify_montage_live import phase_live      # noqa: E402
        PHASES["live"] = phase_live
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
