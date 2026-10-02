"""Verify the sources and formats of the Connect block (2026-10-02), in mayapy STANDALONE.

    mayapy docs/superpowers/plans/verify_import_sources.py [phase ...]

Phases (all by default): formats, listing, roads. It never touches a live
Maya: it imports one real UE clip into an empty scene, writes it out in
every format the bridge reads (an FBX of two split takes, Collada through the
FBX plugin, USD through mayaUsd, a Maya .ma with a script node in it, and
BVH, glTF/GLB and two Unity .anim clips through writers of our own), reads
each back through the REAL funnel (`rigimport.import_source`) and compares
every joint's world matrix with the original's over sampled frames - with a
positive control (a frame off) that must fail. Then the folder is listed
(`sources.scan` with Maya's FBX take reader), and the roads run end to end:
a NEW Manny rig, a new Manny UE5 skeleton, and three clips at once
(`lineimport.run`), each clip's namespace gone afterwards.
"""

import math
import os
import shutil
import sys
import tempfile
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, REPO)

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

for plugin in ("fbxmaya", "matrixNodes", "quatNodes", "mayaUsdPlugin"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except Exception as error:      # noqa: BLE001
        print("plugin", plugin, error)

from maya_uebridge import animimport, bvh, gltf, rigimport, sources  # noqa: E402
from maya_uebridge import formats, unityfiles  # noqa: E402

CLIP = "C:/!!!Work/Animations/Export/ShortSword_Attack_Thrust_3P.FBX"
UNITY_REAL = ("C:/!!!Work/work/Assets/PluginsQ/Pixel Crushers/Dialogue System/"
              "Demo/Art/Recon Troop/Model/TwoHandGunFireStanding.anim")
SANDBOX = os.path.join(tempfile.gettempdir(), "agentA_sources_verify").replace("\\", "/")
CLIPS = SANDBOX + "/clips"
PHASES = sys.argv[1:] or ["formats", "listing", "roads"]
RESULTS = []
TOL_CM = 1e-3
TOL_DEG = 1e-2
WORST = [None]


def gate(number, label, ok, detail=""):
    RESULTS.append((number, label, bool(ok), detail))
    print("[{0}] gate {1}: {2} - {3}".format("PASS" if ok else "FAIL", number,
                                             label, detail))


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def joints_of(root):
    return [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                        fullPath=True) or [])


def worlds(joints, frames):
    """{leaf: [world matrix per frame]} by a real time walk."""
    out = dict((leaf(j), []) for j in joints)
    for f in frames:
        cmds.currentTime(f, update=True)
        for j in joints:
            out[leaf(j)].append(cmds.xform(j, query=True, worldSpace=True, matrix=True))
    return out


def compare(ref, got, shift=0):
    """(worst position cm, worst angle deg, bones compared) between two
    {leaf: [matrices]} - got[k] against ref[k + shift]."""
    worst_p = worst_a = 0.0
    bones = 0
    if shift == 0:
        WORST[0] = None
    for name, mats in ref.items():
        if name not in got:
            continue
        bones += 1
        for k in range(len(got[name])):
            if not 0 <= k + shift < len(mats):
                continue
            a, b = om.MMatrix(mats[k + shift]), om.MMatrix(got[name][k])
            dist = math.sqrt(sum((a[12 + i] - b[12 + i]) ** 2 for i in range(3)))
            if dist > worst_p and shift == 0:
                WORST[0] = (name, k, round(dist, 3))
            worst_p = max(worst_p, dist)
            qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
            qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
            dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
            worst_a = max(worst_a, math.degrees(2 * math.acos(min(1.0, dot))))
    return worst_p, worst_a, bones


def local_rt(joint, frame):
    m = om.MMatrix(cmds.getAttr(joint + ".matrix", time=frame))
    tm = om.MTransformationMatrix(m)
    return tm.translation(om.MSpace.kTransform), tm.rotation(asQuaternion=True)


# ------------------------------------------------------------------ writers

def write_bvh(joints, frames, fps, path):
    index = dict((j, i) for i, j in enumerate(joints))
    chans = ("Xposition", "Yposition", "Zposition", "Zrotation", "Xrotation",
             "Yrotation")
    rows = [[] for _ in frames]
    previous = [None] * len(joints)
    table = []
    for i, j in enumerate(joints):
        parent = cmds.listRelatives(j, parent=True, fullPath=True)
        p = index.get(parent[0]) if parent else None
        t0 = cmds.getAttr(j + ".translate", time=frames[0])[0]
        table.append(bvh.Joint(leaf(j), p, t0, chans))
    for k, f in enumerate(frames):
        for i, j in enumerate(joints):
            t, q = local_rt(j, f)
            e = q.asEulerRotation().reorder(om.MEulerRotation.kYXZ)
            if previous[i] is not None:
                e = e.closestSolution(previous[i])
            previous[i] = e
            rows[k].extend([t.x, t.y, t.z, math.degrees(e.z), math.degrees(e.x),
                            math.degrees(e.y)])
    with open(path, "w") as handle:
        handle.write(bvh.write(table, rows, 1.0 / fps))


def write_glb(joints, frames, fps, path):
    index = dict((j, i) for i, j in enumerate(joints))
    nodes, tracks = [], {}
    for i, j in enumerate(joints):
        parent = cmds.listRelatives(j, parent=True, fullPath=True)
        t, q = local_rt(j, frames[0])
        nodes.append((leaf(j), index.get(parent[0]) if parent else None,
                      (t.x / 100, t.y / 100, t.z / 100), (q.x, q.y, q.z, q.w),
                      (1, 1, 1)))
        ts, qs = [], []
        for f in frames:
            t, q = local_rt(j, f)
            ts.append((t.x / 100, t.y / 100, t.z / 100))
            qs.append((q.x, q.y, q.z, q.w))
        tracks[i] = {"t": ts, "r": qs}
    gltf.write_glb(path, nodes, "thrust", [k / fps for k in range(len(frames))],
                   tracks)


def write_anim(joints, frames, fps, path, name, positions=True):
    """A generic Unity AnimationClip of the skeleton, in Unity's units and
    handedness (metres, X mirrored), keys on every frame."""
    paths = {}
    for j in joints:
        chain = [leaf(p) for p in j.split("|")[1:]]
        paths[j] = "/".join(chain)
    lines = ["%YAML 1.1", "%TAG !u! tag:unity3d.com,2011:", "--- !u!74 &7400000",
             "AnimationClip:", "  m_Name: " + name, "  serializedVersion: 6",
             "  m_Legacy: 0", "  m_Compressed: 0", "  m_RotationCurves:"]
    data = {}
    for j in joints:
        data[j] = [local_rt(j, f) for f in frames]
    for j in joints:
        lines += ["  - curve:", "      serializedVersion: 2", "      m_Curve:"]
        for k, (t, q) in enumerate(data[j]):
            x, y, z, w = q.x, -q.y, -q.z, q.w
            lines += ["      - serializedVersion: 3", "        time: %r" % (k / fps),
                      "        value: {x: %r, y: %r, z: %r, w: %r}" % (x, y, z, w),
                      "        inSlope: {x: 0, y: 0, z: 0, w: 0}",
                      "        outSlope: {x: 0, y: 0, z: 0, w: 0}",
                      "        tangentMode: 0"]
        lines += ["      m_PreInfinity: 2", "      m_PostInfinity: 2",
                  "      m_RotationOrder: 4", "    path: " + paths[j]]
    lines += ["  m_CompressedRotationCurves: []", "  m_EulerCurves: []",
              "  m_PositionCurves:" + ("" if positions else " []")]
    for j in (joints if positions else []):
        lines += ["  - curve:", "      serializedVersion: 2", "      m_Curve:"]
        for k, (t, q) in enumerate(data[j]):
            lines += ["      - serializedVersion: 3", "        time: %r" % (k / fps),
                      "        value: {x: %r, y: %r, z: %r}" % (-t.x / 100, t.y / 100,
                                                              t.z / 100),
                      "        inSlope: {x: 0, y: 0, z: 0}",
                      "        outSlope: {x: 0, y: 0, z: 0}", "        tangentMode: 0"]
        lines += ["      m_PreInfinity: 2", "      m_PostInfinity: 2",
                  "    path: " + paths[j]]
    lines += ["  m_ScaleCurves: []", "  m_FloatCurves: []", "  m_PPtrCurves: []",
              "  m_SampleRate: %g" % fps, "  m_WrapMode: 0",
              "  m_AnimationClipSettings:", "    serializedVersion: 2",
              "    m_StartTime: 0", "    m_StopTime: %r" % ((len(frames) - 1) / fps),
              "  m_EditorCurves: []", "  m_Events: []"]
    with open(path, "w") as handle:
        handle.write("\n".join(lines) + "\n")


HUMANOID_ANIM = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!74 &7400000
AnimationClip:
  m_Name: Humanoid_Walk
  m_Compressed: 0
  m_RotationCurves: []
  m_PositionCurves: []
  m_ScaleCurves: []
  m_FloatCurves:
  - curve:
      serializedVersion: 2
      m_Curve:
      - serializedVersion: 3
        time: 0
        value: 0.5
    attribute: RootT.x
    path:
  - curve:
      serializedVersion: 2
      m_Curve: []
    attribute: Spine Front-Back
    path:
  m_SampleRate: 30
  m_AnimationClipSettings:
    m_StartTime: 0
    m_StopTime: 1
"""


# ------------------------------------------------------------------ phases

def setup():
    cmds.file(new=True, force=True)
    if os.path.isdir(SANDBOX):
        shutil.rmtree(SANDBOX)
    os.makedirs(SANDBOX + "/alone")
    os.makedirs(CLIPS + "/unity")
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval('FBXImport -f "{0}"'.format(CLIP))
    root = cmds.ls("|root", long=True)[0]
    joints = joints_of(root)
    curves = cmds.ls(type="animCurve")
    times = cmds.keyframe(curves, query=True, timeChange=True)
    first, last = int(math.ceil(max(0, min(times)))), int(math.floor(max(times)))
    fps = animimport.scene_fps()
    frames = list(range(first, last + 1))
    # A UE 3P clip animates bone SCALE (trap 152: spine_01 1.0022), which BVH
    # cannot carry at all - the round trip is about the formats' transforms,
    # so the reference stands at scale 1 (and says how much scale it had).
    scaled = 0
    for j in joints:
        for attr in ("scaleX", "scaleY", "scaleZ"):
            for c in cmds.listConnections(j + "." + attr, type="animCurve") or []:
                cmds.delete(c)
                scaled += 1
            cmds.setAttr(j + "." + attr, 1.0)
    print("scale curves removed from the reference:", scaled)
    print("clip", CLIP, "joints", len(joints), "frames", first, last, "fps", fps)
    return root, joints, frames, fps


def write_all(root, joints, frames, fps):
    made = {}
    cmds.select(root)
    two = CLIPS + "/two_takes.fbx"
    mel.eval("FBXResetExport")
    mel.eval("FBXExportSplitAnimationIntoTakes -c")
    mid = frames[len(frames) // 2]
    mel.eval('FBXExportSplitAnimationIntoTakes -v "first" {0} {1}'.format(frames[0], mid))
    mel.eval('FBXExportSplitAnimationIntoTakes -v "second" {0} {1}'.format(mid, frames[-1]))
    mel.eval('FBXExport -f "{0}" -s'.format(two))
    made["fbx"] = two
    mel.eval("FBXExportSplitAnimationIntoTakes -c")
    cmds.select(root)
    dae = CLIPS + "/thrust.dae"
    cmds.file(dae, force=True, options="v=0;", type="DAE_FBX export", exportSelected=True)
    made["dae"] = dae
    group = cmds.group(root, name="SkelGrp")
    cmds.select(group)
    usd = CLIPS + "/thrust.usda"
    cmds.mayaUSDExport(file=usd, selection=True, exportSkels="auto",
                       frameRange=(frames[0], frames[-1]))
    made["usd"] = usd
    cmds.parent(cmds.ls(group + "|root", long=True)[0], world=True)
    cmds.delete(group)
    root = cmds.ls("|root", long=True)[0]
    joints = joints_of(root)
    script = cmds.scriptNode(name="agentA_probe_script", scriptType=1,
                             sourceType="python",
                             beforeScript="import sys; sys._agentA_script_ran = True")
    cmds.select([root, script])
    ma = CLIPS + "/thrust.ma"
    cmds.file(ma, force=True, options="v=0;", type="mayaAscii", exportSelected=True,
              preserveReferences=False)
    made["ma"] = ma
    cmds.delete(script)
    write_bvh(joints, frames, fps, CLIPS + "/thrust.bvh")
    made["bvh"] = CLIPS + "/thrust.bvh"
    write_glb(joints, frames, fps, CLIPS + "/thrust.glb")
    made["gltf"] = CLIPS + "/thrust.glb"
    cmds.select(root)
    mel.eval("FBXResetExport")
    mel.eval('FBXExport -f "{0}" -s'.format(CLIPS + "/unity/Model.fbx"))
    write_anim(joints, frames, fps, CLIPS + "/unity/Thrust_generic.anim", "Thrust_generic")
    made["anim"] = CLIPS + "/unity/Thrust_generic.anim"
    write_anim(joints, frames, fps, SANDBOX + "/alone/Thrust_nomodel.anim",
               "Thrust_nomodel")
    made["anim_nomodel"] = SANDBOX + "/alone/Thrust_nomodel.anim"
    # rotations only, and no model beside it: nothing to stand its bones on
    write_anim(joints, frames, fps, SANDBOX + "/alone/Rotations_only.anim",
               "Rotations_only", positions=False)
    made["anim_rotonly"] = SANDBOX + "/alone/Rotations_only.anim"
    with open(CLIPS + "/unity/Humanoid_Walk.anim", "w") as handle:
        handle.write(HUMANOID_ANIM)
    return made, root, joints


def phase_formats():
    root, joints, frames, fps = setup()
    ref = worlds(joints, frames)
    made, root, joints = write_all(root, joints, frames, fps)
    sizes = dict((k, os.path.getsize(v)) for k, v in made.items())
    print("written", sizes)
    takes = formats.fbx_takes(made["fbx"])
    gate(1, "an FBX of two split takes lists three takes, each a span",
         len(takes) == 3 and all(t[3] > t[2] for t in takes), str(takes))
    refs = [
        ("fbx_take2", sources.ref(made["fbx"], sources.clip_text(take=2)), 0),
        ("fbx_take3", sources.ref(made["fbx"], sources.clip_text(take=3)),
         frames.index(frames[len(frames) // 2])),
        ("dae", made["dae"], 0), ("usd", made["usd"], 0), ("ma", made["ma"], 0),
        ("bvh", made["bvh"], 0), ("gltf", sources.ref(made["gltf"],
                                                       sources.clip_text(anim=0)), 0),
        ("anim", made["anim"], 0), ("anim_nomodel", made["anim_nomodel"], 0),
    ]
    number = 2
    for name, clip_ref, offset in refs:
        try:
            t0 = time.time()
            namespace, info, source = rigimport.import_source(clip_ref, name,
                                                              set_timeline=False)
            took = time.time() - t0
            got_joints = joints_of(source) if source else []
            span = (info.get("start"), info.get("end"))
            start = int(round(span[0])) if span[0] is not None else 0
            if name == "dae":
                # Maya's Collada WRITER resamples onto 24 fps whatever the
                # scene's rate (measured: keys 1.25 frames apart at 30 fps),
                # so the file is not the clip between its keys; what the READ
                # must reproduce is the original at the file's own key times.
                keyed = cmds.keyframe(got_joints[0] + ".rotateX", query=True,
                                      timeChange=True) or []
                sample = [t for t in keyed if t <= frames[-1]][::2]
                ref_slice = worlds(joints, sample)
            elif name in ("fbx_take2", "fbx_take3", "usd", "ma"):
                # these keep the original timeline's frames
                sample = [f for f in frames if span[0] is not None
                          and span[0] - 1e-6 <= f <= span[1] + 1e-6]
                ref_slice = dict((k, [v[frames.index(f)] for f in sample])
                                 for k, v in ref.items())
            else:
                sample = [start + k for k in range(len(frames))]
                ref_slice = ref
            got = worlds(got_joints, sample)
            p, a, bones = compare(ref_slice, got)
            pc, ac, _ = compare(ref_slice, got, shift=1)
            ok = (bones >= len(joints) - 2 and p < TOL_CM and a < TOL_DEG
                  and (pc > 0.5 or ac > 0.5))
            gate(number, "{0}: {1} bones on the original over {2} frames".format(
                name, bones, len(sample)), ok,
                "worst {0:.6f} cm {1:.6f} deg; a frame off: {2:.3f} cm {3:.3f} deg; "
                "frames {4}-{5}; {6:.2f} s; {7} (worst {8})".format(
                    p, a, pc, ac, span[0], span[1], took, info.get("warning", ""),
                    WORST[0]))
        except Exception:
            traceback.print_exc()
            gate(number, name, False, traceback.format_exc().splitlines()[-1])
        number += 1
    gate(number, "the .ma's script node was deleted and never ran",
         not getattr(sys, "_agentA_script_ran", False)
         and not [n for n in cmds.ls(type="script") if "agentA_probe" in n],
         str([n for n in cmds.ls(type="script")]))
    number += 1
    try:
        rigimport.import_source(CLIPS + "/unity/Humanoid_Walk.anim", "hum")
        gate(number, "a Humanoid muscle clip is refused by name", False, "imported")
    except RuntimeError as error:
        gate(number, "a Humanoid muscle clip is refused by name",
             "Humanoid" in str(error), str(error))
    number += 1
    # ---- the fix review (2026-10-02): what a press must refuse BEFORE it adds
    # a rig is decided by formats.check, and the import says the same
    two = made["fbx"]
    bad = sources.ref(two, sources.clip_text(take_name="mixamo.com", first="0",
                                             last="5"))
    good = sources.ref(two, sources.clip_text(take_name="second", first="0",
                                              last="5"))
    said, raised = formats.check(bad), ""
    try:
        rigimport.import_source(bad, "badtake", set_timeline=False)
    except RuntimeError as error:
        raised = str(error)
    gate(number, "a take the FBX does not hold is refused by name, by the check "
         "and by the import; a take it holds is not",
         "'mixamo.com' is not in the file" in said and "it holds" in said
         and raised == said and formats.check(good) == "",
         "check: {0!r}; import: {1!r}".format(said, raised))
    number += 1
    said, raised = formats.check(made["anim_rotonly"]), ""
    try:
        rigimport.import_source(made["anim_rotonly"], "rotonly", set_timeline=False)
    except RuntimeError as error:
        raised = str(error)
    gate(number, "a Unity clip with no model and no positions is refused by the "
         "check and by the import; one with positions is not",
         "no position curve" in said and raised == said
         and formats.check(made["anim_nomodel"]) == "",
         "check: {0!r}".format(said))
    number += 1
    number = _media_gate(number)
    if os.path.isfile(UNITY_REAL):
        number = _real_unity_gates(number)
    return made


EMBEDDED = os.path.normpath(os.path.join(HERE, "..", "..", "..", "sources", "creep",
                                         "creep_T-pose_draft.fbx"))


def _media_gate(number):
    """The FBX plugin extracts a file's embedded media into `<file>.fbm` BESIDE
    the file it reads - in a Unity project that is a folder in Assets Unity then
    imports (the fix review). A Folder/Unity file is read from a copy in the
    bridge's temp folder; the positive control reads the original and must
    make the folder."""
    if not os.path.isfile(EMBEDDED):
        gate(number, "embedded media stay out of the source folder", False,
             "no " + EMBEDDED)
        return number + 1
    try:
        folder = SANDBOX + "/media"
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
        here = folder + "/creep_T-pose_draft.fbx"
        shutil.copyfile(EMBEDDED, here)
        cmds.file(new=True, force=True)
        rigimport.import_source(here, "media", set_timeline=False)
        after_ours = sorted(os.listdir(folder))
        control = SANDBOX + "/media_control"
        if os.path.isdir(control):
            shutil.rmtree(control)
        os.makedirs(control)
        shutil.copyfile(EMBEDDED, control + "/creep_T-pose_draft.fbx")
        animimport.import_clip(control + "/creep_T-pose_draft.fbx", "mediaControl",
                               set_timeline=False, merge=False)
        after_control = sorted(os.listdir(control))
        gate(number, "a file of the animator's is read from a copy: no .fbm beside "
             "it (the plugin's own read of the original makes one)",
             after_ours == ["creep_T-pose_draft.fbx"] and any(
                 n.endswith(".fbm") for n in after_control),
             "source folder after our import: {0}; after the plugin's own: {1}".format(
                 after_ours, after_control))
    except Exception:
        traceback.print_exc()
        gate(number, "embedded media stay out of the source folder", False,
             traceback.format_exc().splitlines()[-1])
    return number + 1


UNITY_REAL_TAKE = "TwoHandGunIFirestanding"   # the model clip the .anim duplicates


def _quat(node):
    return om.MTransformationMatrix(om.MMatrix(cmds.getAttr(node + ".matrix"))).rotation(
        asQuaternion=True)


def _angle(qa, qb):
    dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
    return math.degrees(2 * math.acos(min(1.0, dot)))


def _real_unity_gates(number):
    """The handedness conversion against UNITY'S OWN data, not our writer's:
    TwoHandGunFireStanding.anim is Unity's copy of the model clip
    TwoHandGunIFirestanding (39 frames both), so the .anim road on the model and
    the FBX take road through Maya's own importer must agree bone for bone. The
    fix review: the old gate wrote its .anim with the inverse of the same
    conversion (any error cancels) and passed on a MEDIAN."""
    try:
        text = open(UNITY_REAL).read()
        curves = dict((p, t) for p, t in unityfiles.anim_curves(text).items() if p)
        held = sorted(set(p.split("/")[-1] for p in curves))
        model = formats.model_for(UNITY_REAL, held)
        meta = open(model + ".meta").read()
        clip = [c for c in unityfiles.meta_clips(meta) if c[0] == UNITY_REAL_TAKE][0]
        take_ref = sources.record_ref(sources.unity_model_rows(model, [clip], [])[0])
        cmds.file(new=True, force=True)
        ns_take, info_take, _s = rigimport.import_source(take_ref, "uTake",
                                                         set_timeline=False)
        ns_anim, info_anim, _s = rigimport.import_source(UNITY_REAL, "uAnim",
                                                         set_timeline=False)

        def nodes(ns):
            out = {}
            for n in cmds.namespaceInfo(ns, listOnlyDependencyNodes=True,
                                        recurse=True, dagPath=True) or []:
                if cmds.objExists(n) and cmds.nodeType(n) in ("joint", "transform"):
                    out.setdefault(leaf(n), n)
            return out
        a, b = nodes(ns_take), nodes(ns_anim)
        common = [n for n in held if n in a and n in b]
        frames = int(round(info_anim["end"] - info_anim["start"])) + 1
        worst = dict((n, [0.0, 0.0, None, 0.0]) for n in common)  # ang, pos, min, max
        for k in range(frames):
            cmds.currentTime(info_take["start"] + k, update=True)
            qa = dict((n, _quat(a[n])) for n in common)
            ta = dict((n, cmds.getAttr(a[n] + ".translate")[0]) for n in common)
            cmds.currentTime(info_anim["start"] + k, update=True)
            for n in common:
                ang = _angle(qa[n], _quat(b[n]))
                tb = cmds.getAttr(b[n] + ".translate")[0]
                pos = math.sqrt(sum((ta[n][i] - tb[i]) ** 2 for i in range(3)))
                w = worst[n]
                w[0], w[1] = max(w[0], ang), max(w[1], pos)
                w[2] = ang if w[2] is None else min(w[2], ang)
                w[3] = max(w[3], ang)
        # 0.6 deg: Unity writes a model clip's copy through its keyframe
        # reduction, whose default rotation error is 0.5 deg (one bone read
        # 0.500 here), so a copy may stand that far off the take by design
        inside = [n for n in common if worst[n][0] < 0.6 and worst[n][1] < 0.05]
        outliers = [n for n in common if n not in inside]
        constant = all(worst[n][3] - worst[n][2] < 2.0 for n in outliers)
        gate(number, "a real Unity .anim (Unity's copy of a model clip) on its model "
             "agrees with Maya's own import of that take, every bone, every frame",
             len(common) == len(held) and len(inside) >= 0.95 * len(common),
             "{0}/{1} bones within 0.6 deg and 0.05 cm over {2} frames (worst inside "
             "{3:.3f} deg, {4:.4f} cm); outliers {5} - each a near-constant offset "
             "({6}): an edit made in Unity on its copy".format(
                 len(inside), len(common), frames,
                 max([worst[n][0] for n in inside] or [0]),
                 max([worst[n][1] for n in inside] or [0]),
                 ["%s %.3f..%.3f deg" % (n, worst[n][2], worst[n][3]) for n in outliers],
                 constant))
        number += 1
        # the positive control: the same frame read back through the three
        # other mirrorings must NOT agree - so the gate above can fail
        cmds.currentTime(info_take["start"], update=True)
        conventions = {
            "mirror X (ours)": lambda q: (q[0], -q[1], -q[2], q[3]),
            "mirror Y": lambda q: (-q[0], q[1], -q[2], q[3]),
            "mirror Z": lambda q: (-q[0], -q[1], q[2], q[3]),
            "none": lambda q: q}
        _times, samples = formats.unity_samples(curves, unityfiles.anim_summary(text))

        def converted(conv, q):
            q = conv(q)
            norm = math.sqrt(sum(c * c for c in q)) or 1.0
            return om.MQuaternion(*[c / norm for c in q])
        firsts = dict((path.split("/")[-1], s["q"][0]) for path, s in samples.items()
                      if s.get("q") and path.split("/")[-1] in a)
        ours = conventions["mirror X (ours)"]
        landed = sum(_angle(converted(ours, q), _quat(a[n])) < 0.6
                     for n, q in firsts.items())
        report = ["mirror X (ours) lands %d/%d" % (landed, len(firsts))]
        others_ok = True
        for label, conv in conventions.items():
            if conv is ours:
                continue
            # only where the two mirrorings disagree can one be told from the
            # other (a bone turning about its own Z alone reads alike in both)
            differ = [n for n, q in firsts.items()
                      if _angle(converted(conv, q), converted(ours, q)) > 1.0]
            hits = sum(_angle(converted(conv, firsts[n]), _quat(a[n])) < 0.6
                       for n in differ)
            others_ok = others_ok and len(differ) >= 5 and hits <= 0.1 * len(differ)
            report.append("%s lands %d of the %d bones where it differs" % (
                label, hits, len(differ)))
        gate(number, "the positive control: only Unity's X mirror lands the clip's "
             "first frame on the take's", landed >= 0.9 * len(firsts) and others_ok,
             "; ".join(report))
        number += 1
        # a bone the clip does not hold stands at the model's REST: the model
        # came in with no take of its own (it carries one: 333 curves)
        keyed = set(leaf(n) for n in b.values()
                    if cmds.listConnections(n, type="animCurve"))
        unheld = sorted(set(b) - set(held))
        gate(number, "the model under a Unity clip brings no take of its own: only "
             "the clip's bones are keyed",
             keyed == set(common) and not (keyed & set(unheld)),
             "{0} keyed, {1} not held by the clip and unkeyed: {2}".format(
                 len(keyed), len(unheld), unheld[:4]))
        number += 1
    except Exception:
        traceback.print_exc()
        gate(number, "the real Unity clip", False, traceback.format_exc().splitlines()[-1])
        number += 1
    return number


def phase_listing():
    t0 = time.time()
    rows = sources.scan(CLIPS, "folder", formats.fbx_takes)
    took = time.time() - t0
    by_fmt = {}
    for r in rows:
        by_fmt.setdefault(r.fmt, []).append(r.name)
    print("rows", [(r.name, r.fmt, r.frames, r.skeleton, r.clip) for r in rows])
    gate(40, "the folder lists every clip of every format", all(
        f in by_fmt for f in ("fbx", "dae", "usd", "ma", "bvh", "gltf", "anim"))
        and len(by_fmt["fbx"]) == 4 and len(by_fmt["anim"]) == 2,
        "{0} rows in {1:.2f} s: {2}".format(len(rows), took, dict(
            (k, len(v)) for k, v in by_fmt.items())))
    hum = [r for r in rows if r.name == "Humanoid_Walk"]
    gate(41, "the humanoid clip keeps its row, marked", hum and hum[0].skeleton ==
         "humanoid", str(hum))
    unity = "C:/!!!Work/work"
    if os.path.isdir(unity + "/Assets"):
        t0 = time.time()
        found = sources.scan(unity, "unity", formats.fbx_takes)
        took = time.time() - t0
        kinds = {}
        for r in found:
            kinds[r.fmt + (":" + r.skeleton if r.skeleton else "")] = \
                kinds.get(r.fmt + (":" + r.skeleton if r.skeleton else ""), 0) + 1
        clipped = [r for r in found if "first=" in r.clip]
        gate(42, "a real Unity project lists its model clips and .anim clips",
             len(found) > 100 and clipped,
             "{0} rows in {1:.1f} s: {2}; e.g. {3}".format(
                 len(found), took, kinds, [(r.name, r.clip) for r in clipped[:2]]))
    return rows


def phase_roads(rows=None):
    import maya_rigs
    from maya_scenesetup import catalog
    from maya_uebridge import lineimport, skeletonimport
    cmds.file(new=True, force=True)
    rows = rows or sources.scan(CLIPS, "folder", formats.fbx_takes)
    pick = dict((r.fmt + ("2" if "take=2" in r.clip else ""), r) for r in rows)

    def namespaces():
        return set(cmds.namespaceInfo(":", listOnlyNamespaces=True) or [])

    before = namespaces()
    r = pick["bvh"]
    text = rigimport.import_and_retarget(sources.record_ref(r), r.name,
                                         set_timeline=True, target="new_rig")
    rig = maya_rigs.rigs()[-1] if maya_rigs.rigs() else None
    moved = _travel(rig, "hand_r") if rig else 0
    gate(50, "BVH onto a NEW Manny rig: retargeted, the clip's namespace gone",
         rig is not None and moved > 1.0 and not (namespaces() - before - {
             rig.namespace if rig else ""}), "{0} | hand_r travels {1:.2f} cm".format(
                 text[:160], moved))
    before = namespaces()
    r = pick["gltf"]
    entry = catalog.character_for("Manny", "skeleton")
    text = skeletonimport.import_onto_skeleton(sources.record_ref(r), r.name,
                                               set_timeline=True, entry=entry)
    new = sorted(namespaces() - before)
    roots = [j for j in cmds.ls(type="joint", long=True) if j.count("|") == 1
             and ":" not in j]
    moved = max((_travel_joint(j.rsplit("|", 1)[0] + "|" + j.split("|")[1]
                               if False else j, "hand_r") for j in roots), default=0)
    gate(51, "glTF onto a new Manny UE5 skeleton: transferred, no clip namespace left",
         moved > 1.0 and not new, "{0} | hand_r travels {1:.2f} cm; namespaces "
         "left {2}".format(text[:160], moved, new))
    before = namespaces()
    rigs_before = len(maya_rigs.rigs())
    chosen = [pick["fbx2"], pick["dae"], pick["usd"]]
    text = lineimport.run(chosen, lambda rec: (sources.record_ref(rec), rec.fps),
                          "new_rig")
    rigs = maya_rigs.rigs()
    added = rigs[rigs_before:]
    travels = [_travel(rg, "hand_r") for rg in added]
    gate(52, "three clips (FBX take, Collada, USD) at once onto three new rigs",
         len(added) == 3 and all(t > 1.0 for t in travels)
         and not (namespaces() - before - set(rg.namespace for rg in added)),
         "{0} | hand_r travels {1}".format(text[:200], ["%.1f" % t for t in travels]))
    _fix_review_roads(namespaces)


def _fix_review_roads(namespaces):
    """The fix review's roads (2026-10-02): a Maya scene the animator SAVED WHOLE
    (mayaUsd's locked settings node inside it), and a clip that fails - before
    the press by the check, and inside it after a rig was added."""
    import maya_rigs
    from maya_uebridge import window
    full = SANDBOX + "/full/take_full.ma"
    if not os.path.isdir(os.path.dirname(full)):
        os.makedirs(os.path.dirname(full))
    cmds.file(new=True, force=True)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval('FBXImport -f "{0}"'.format(CLIP))
    cmds.file(rename=full)
    cmds.file(save=True, type="mayaAscii", force=True)
    locked_inside = "createNode UsdDefaultSettings" in open(full).read()
    cmds.file(new=True, force=True)
    before = namespaces()
    text = rigimport.import_and_retarget(full, "take_full", set_timeline=True,
                                         target="new_rig")
    rigs = maya_rigs.rigs()
    rig = rigs[-1] if rigs else None
    moved = _travel(rig, "hand_r") if rig else 0
    left = sorted(namespaces() - before - set([rig.namespace if rig else ""]))
    gate(53, "a .ma saved whole (a locked UsdDefaultSettings inside) onto a NEW "
         "rig: retargeted, the clip's namespace gone with all of it",
         locked_inside and rig is not None and moved > 1.0 and not left,
         "file carries the locked node: {0}; {1} | hand_r travels {2:.2f} cm; "
         "namespaces left {3}".format(locked_inside, text[:140], moved, left))
    # before the press: the check refuses, nothing is added or imported
    cmds.file(new=True, force=True)
    alone = SANDBOX + "/alone/Rotations_only.anim"
    record = sources.file_record(alone, "Rotations_only", source="folder")
    before = namespaces()
    try:
        window._export_from_editor(record)
        refused = ""
    except Exception as error:      # noqa: BLE001
        refused = str(error)
    gate(54, "a clip the check refuses is refused at the export step, before the "
         "press: no rig added, nothing imported",
         "no position curve" in refused and not maya_rigs.rigs()
         and namespaces() == before, refused)
    # inside the press, after the add: what the press made goes again
    cmds.file(new=True, force=True)
    before = namespaces()
    t0 = time.time()
    text = rigimport.import_and_retarget(alone, "Rotations_only", target="new_rig")
    gate(55, "a clip failing INSIDE the import after the press added a rig: the "
         "rig and the half-made clip namespace are taken back, the line says why",
         "could not be imported" in text and not maya_rigs.rigs()
         and namespaces() == before,
         "{0} ({1:.1f} s); namespaces now {2}".format(text[:220], time.time() - t0,
                                                     sorted(namespaces())))


def _travel(rig, bone):
    import maya_rigs
    node = maya_rigs.node(rig, bone) if hasattr(maya_rigs, "node") else None
    hits = [j for j in cmds.ls(type="joint", long=True)
            if leaf(j) == bone and j.split("|")[1].startswith(rig.namespace + ":")
            and "Group" not in j]
    return _travel_joint(hits[0], None) if hits else 0.0


def _travel_joint(joint, bone):
    if bone:
        hits = [j for j in cmds.listRelatives(joint, allDescendents=True,
                                              type="joint", fullPath=True) or []
                if leaf(j) == bone]
        if not hits:
            return 0.0
        joint = hits[0]
    lo = cmds.playbackOptions(query=True, minTime=True)
    hi = cmds.playbackOptions(query=True, maxTime=True)
    points = []
    for f in range(int(lo), int(hi) + 1, 2):
        cmds.currentTime(f, update=True)
        points.append(cmds.xform(joint, query=True, worldSpace=True, translation=True))
    return max((math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))
                for a in points for b in points), default=0.0)


def main():
    rows = None
    if "formats" in PHASES:
        phase_formats()
    if "listing" in PHASES:
        rows = phase_listing()
    if "roads" in PHASES:
        try:
            phase_roads(rows)
        except Exception:
            traceback.print_exc()
            gate(59, "the roads", False, traceback.format_exc().splitlines()[-1])
    failed = [r for r in RESULTS if not r[2]]
    print("RESULT: {0}/{1} gates passed".format(len(RESULTS) - len(failed), len(RESULTS)))
    for number, label, _ok, detail in failed:
        print("  FAILED gate", number, label, detail)


main()
