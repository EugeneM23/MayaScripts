"""An AnimMontage's slot, read as a plan and composed into one take.

An AnimMontage is SLOTS (`DefaultSlot`, `1P`, `FullBody`, `UpperBody`), and a
slot is a track of SEGMENTS. Each segment is a slice of an AnimSequence -
`anim_start_time`..`anim_end_time` - laid at `start_pos` on the montage's clock
and played at `anim_play_rate`. Measured in Atone 2026-10-29: 195 montages,
498 segments, 121 of them at a rate other than 1 (0.42 to 3.5), 70 slot tracks
with more than one segment, no sections anywhere, no gaps, every track starting
at 0, every `looping_count` 1, every reference a plain AnimSequence, and one
additive clip in the whole project.

Two engine limits shape this module. `AnimSequenceExporterFBX` supports an
`AnimSequence` only, so a montage cannot be exported at all; and this build
(5.8.4) exposes no `AnimSequence` controller to Python, so a montage cannot be
baked into a temporary asset either. The composite is therefore assembled in
Maya out of the slot's own clips - nothing is written into the Unreal project.

The halves are kept apart on purpose: everything above `# --- the scene` is
stdlib (a test pins it), so the arithmetic that decides which frame reads which
clip at which time is tested with no Maya and no editor running.
"""

import collections
import json
import math
import os

from maya_uebridge import records

#  The import funnel's reference for a montage: the plan file the export step
#  left behind. `rigimport.import_source` sends it here.
REF_PREFIX = "montage:"

#  A slice shorter than this is no animation (float noise in the montage's own
#  numbers; a real segment is tens of milliseconds at least).
TINY = 1e-6

#  Every channel of the slot's clips is composed, not only translate / rotate /
#  scale: a UE root carries the game's own curves as custom attributes
#  (`Pose_0..9`, `MoveData_*` - trap 40). These are the ones nothing animates
#  and that must never be keyed on a resample.
SKIP_ATTRS = ("visibility",)

clip_name = records.clip_name          # one spelling for montage + slot

Span = collections.namedtuple("Span", "clip t0 t1 src rate")
Plan = collections.namedtuple("Plan", "montage slot spans end clips")


# ------------------------------------------------------------ the reference

def ref_of(plan_path):
    """The import funnel's reference for a plan file. Pure."""
    return REF_PREFIX + (plan_path or "").replace("\\", "/")


def is_ref(text):
    """True for a montage reference. Pure."""
    return bool(text) and str(text).startswith(REF_PREFIX)


def plan_file_of(ref):
    """The plan file a reference names. Pure."""
    text = str(ref or "").replace("\\", "/")
    return text[len(REF_PREFIX):] if is_ref(text) else text


# ------------------------------------------------------------ reading a plan

def _montage(payload, package):
    return ((payload or {}).get("montages") or {}).get(package) or {}


def slots_of(payload, package):
    """The montage's slot names, in the montage's own order. Pure."""
    return [str(slot.get("slot") or "")
            for slot in _montage(payload, package).get("slots") or []]


def segments_of(payload, package, slot):
    """The segments of one slot, in order. Pure."""
    for row in _montage(payload, package).get("slots") or []:
        if str(row.get("slot") or "") == slot:
            return list(row.get("segments") or [])
    return []


def montage_name(payload, package):
    """The montage's asset name, falling back to its package's tail. Pure."""
    name = _montage(payload, package).get("name") or ""
    return str(name or (package or "").rsplit("/", 1)[-1])


def pick_slot(slots, remembered):
    """The slot to show for a montage: the remembered one when it has it,
    else its first. Pure."""
    slots = [s for s in (slots or []) if s]
    if remembered and remembered in slots:
        return remembered
    return slots[0] if slots else ""


def is_additive(text):
    """True for an additive clip. The editor sends the enum's repr, and
    `AAT_NONE` is the ordinary pose kind. Pure."""
    text = str(text or "")
    return "AAT_" in text and "AAT_NONE" not in text


def _duration(segment):
    """How long a segment's slice lasts on the montage's clock. Pure."""
    lo = float(segment.get("anim_start_time") or 0.0)
    hi = float(segment.get("anim_end_time") or 0.0)
    rate = float(segment.get("anim_play_rate") or 0.0)
    if not rate:
        return 0.0
    return abs(hi - lo) / abs(rate)


def plan_for(payload, package, slot):
    """The slot's track as a `Plan`. Pure.

    A segment with `looping_count` N lays N repeats of its slice inside its own
    span, back to back, which is what the engine plays. A slice of no length -
    float noise in the montage's numbers - is left out rather than written as a
    zero-length span nothing can sample.
    """
    spans = []
    clips = []
    for segment in segments_of(payload, package, slot):
        clip = str(segment.get("clip") or "")
        rate = float(segment.get("anim_play_rate") or 0.0)
        length = _duration(segment)
        if not clip or not rate or length <= TINY:
            continue
        start = float(segment.get("start_pos") or 0.0)
        lo = float(segment.get("anim_start_time") or 0.0)
        hi = float(segment.get("anim_end_time") or 0.0)
        loops = int(segment.get("looping_count") or 1) or 1
        for repeat in range(max(loops, 1)):
            t0 = start + repeat * length
            spans.append(Span(clip=clip, t0=t0, t1=t0 + length,
                              src=(lo if rate > 0 else hi), rate=rate))
        if clip not in clips:
            clips.append(clip)
    end = spans[-1].t1 if spans else 0.0
    return Plan(montage=montage_name(payload, package), slot=slot,
                spans=spans, end=end, clips=clips)


def source_at(span, t):
    """The time inside the span's clip that the montage shows at `t`. Pure.

    `t` is clamped into the span first, so the source time can never leave the
    segment's own slice - the last frame of a take sits a thousandth of a
    second past the track's end.
    """
    if t < span.t0:
        t = span.t0
    elif t > span.t1:
        t = span.t1
    return span.src + (t - span.t0) * span.rate


def span_at(plan, t):
    """The span the montage plays at `t`: the last one that has started. Pure.

    A span starting exactly at `t` owns `t` - the engine starts the new
    segment there - so the boundary frame belongs to the later span.
    """
    found = plan.spans[0] if plan.spans else None
    for span in plan.spans:
        if span.t0 <= t + TINY:
            found = span
        else:
            break
    return found


def frame_count(plan, fps):
    """The last whole frame of the take: the track's end never overrun. Pure."""
    if not plan.spans or fps <= 0:
        return 0
    return int(math.floor(plan.end * fps + TINY))


def samples(plan, fps):
    """[(frame, clip, source time)] for every whole frame of the take. Pure.

    This is the whole fidelity statement: at frame `f` the pose is the
    montage's pose at `f / fps`, read from the span covering it at its own
    rate. A segment boundary falls on a fractional frame and gets no key of its
    own - on every whole frame the pose is exact.
    """
    out = []
    for frame in range(frame_count(plan, fps) + 1):
        t = frame / float(fps)
        span = span_at(plan, t)
        if span is None:
            break
        out.append((frame, span.clip, source_at(span, t)))
    return out


def cuts(plan, fps):
    """Where the montage's edits fall, in frames, for the status line. Pure."""
    return [round(span.t0 * fps, 1) for span in plan.spans[1:]]


def refusal(payload, package, slot):
    """Why this slot cannot be imported, "" when it can. Pure.

    Called BEFORE anything is exported or imported, so a refusal leaves the
    scene and the editor exactly as they were.
    """
    name = montage_name(payload, package)
    row = _montage(payload, package)
    if not row:
        return ("{0}: the editor sent no plan for it - press "
                "Refresh".format(name))
    slots = slots_of(payload, package)
    if not slot or slot not in slots:
        return ("{0} has no slot {1} - it has {2}".format(
            name, slot or "(none picked)", ", ".join(slots) or "no slots"))
    where = "{0} · {1}".format(name, slot)
    segments = segments_of(payload, package, slot)
    for segment in segments:
        if is_additive(segment.get("additive")):
            return ("{0} is additive ({1}) - an additive slot is a delta on "
                    "top of a pose, not an animation".format(
                        where, segment.get("clip_name")
                        or str(segment.get("clip") or "").rsplit("/", 1)[-1]))
        if not float(segment.get("anim_play_rate") or 0.0):
            return "{0} has a segment at play rate 0".format(where)
    if not plan_for(payload, package, slot).spans:
        return "{0} holds no animation".format(where)
    return ""


def plan_line(plan, fps, frames=None):
    """What the status says about the composite: «AM_X · 1P: 43 frames, cuts
    at 5.4, 27.8». Pure."""
    frames = frame_count(plan, fps) + 1 if frames is None else frames
    text = "{0} · {1}: {2} frames".format(plan.montage, plan.slot, frames)
    edits = cuts(plan, fps)
    if edits:
        text += ", cuts at " + ", ".join(
            ("{0:g}".format(cut) for cut in edits))
    if len(plan.clips) > 1:
        text += " from {0} clips".format(len(plan.clips))
    return text


# ------------------------------------------------------- the plan on disk

def plan_payload(plan, clips, fps, mesh=False):
    """The JSON the export step leaves for the import step. Pure."""
    return {"montage": plan.montage, "slot": plan.slot, "end": plan.end,
            "fps": fps, "mesh": bool(mesh),
            "name": clip_name(plan.montage, plan.slot),
            "spans": [{"clip": span.clip, "t0": span.t0, "t1": span.t1,
                       "src": span.src, "rate": span.rate}
                      for span in plan.spans],
            "clips": dict(clips or {})}


def plan_of_payload(payload):
    """The `Plan` a plan file holds. Pure, the inverse of `plan_payload`."""
    spans = [Span(clip=row.get("clip") or "", t0=float(row.get("t0") or 0.0),
                  t1=float(row.get("t1") or 0.0),
                  src=float(row.get("src") or 0.0),
                  rate=float(row.get("rate") or 1.0))
             for row in (payload or {}).get("spans") or []]
    clips = []
    for span in spans:
        if span.clip not in clips:
            clips.append(span.clip)
    return Plan(montage=(payload or {}).get("montage") or "",
                slot=(payload or {}).get("slot") or "",
                spans=spans,
                end=float((payload or {}).get("end") or
                          (spans[-1].t1 if spans else 0.0)),
                clips=clips)


def write_plan(folder, plan, clips, fps, mesh=False):
    """The plan plus `{clip package: fbx}` written where the import step
    reads it; its path."""
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    stem = records.namespace_for(clip_name(plan.montage, plan.slot), ())
    path = os.path.join(folder, "montage_{0}.json".format(stem))
    with open(path, "w") as handle:
        json.dump(plan_payload(plan, clips, fps, mesh), handle)
    return path.replace("\\", "/")


def read_plan(path):
    """The plan file's payload."""
    with open(path, "r") as handle:
        return json.load(handle)


# ------------------------------------------------------------ the composite

def continuous(values):
    """The series with whole turns added where a step exceeds 180. Pure.

    Two spans can read their clips' euler curves a turn apart, and a wrap
    inside one clip's curve crosses +-180 as well. At the density this module
    writes - a key a frame - a step over 180 degrees is a wrap and not motion
    (180 degrees in a 30th of a second is 5400 deg/s), which is the assumption
    every bake in this plugin already makes (trap 108). The first value never
    moves: the take must start where the montage starts.
    """
    out = []
    shift = 0.0
    previous = None
    for value in values:
        if previous is not None:
            step = (value + shift) - previous
            while step > 180.0:
                shift -= 360.0
                step -= 360.0
            while step < -180.0:
                shift += 360.0
                step += 360.0
        out.append(value + shift)
        previous = out[-1]
    return out


def channel_plan(animated):
    """Every (joint leaf, attribute) the slot's clips animate. Pure.

    `animated` is {clip: {leaf: [attr, ...]}}. The UNION, because a slot can
    run several clips and a channel only the second one animates is still part
    of the composite - the first clip's static value fills the frames before
    it. Sorted, so a rebuild writes the same curves in the same order.
    """
    found = set()
    for clips in (animated or {}).values():
        for leaf, attrs in (clips or {}).items():
            for attr in attrs or []:
                if attr not in SKIP_ATTRS:
                    found.add((leaf, attr))
    return sorted(found)


# --------------------------------------------------------------- the scene

def _maya():
    """`maya.cmds`, imported here: the plan half above must stay stdlib."""
    from maya import cmds
    return cmds


def _leaf(path):
    return path.rsplit("|", 1)[-1].rsplit(":", 1)[-1]


def _joint_map(cmds, namespace):
    """{leaf: long path} of the joints a clip's import left in `namespace`."""
    nodes = cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True,
                               recurse=True, dagPath=True) or []
    out = {}
    for node in nodes:
        if cmds.objExists(node) and cmds.objectType(node) == "joint":
            out.setdefault(_leaf(node), node)
    return out


def _curve_of(cmds, plug):
    """The animCurve driving `plug`, or "" - through a unitConversion too
    (Maya splices one wherever a unitless double meets an angle, trap 42)."""
    curves = cmds.keyframe(plug, query=True, name=True) or []
    if curves:
        return curves[0]
    found = cmds.listConnections(plug, source=True, destination=False,
                                 type="animCurve") or []
    return found[0] if found else ""


def _animated_channels(cmds, joints):
    """{leaf: [attr, ...]} - what a clip's own import actually keyed."""
    out = {}
    for leaf, node in joints.items():
        pairs = cmds.listConnections(node, connections=True, plugs=True,
                                     source=True, destination=False,
                                     type="animCurve") or []
        attrs = []
        for plug in pairs[0::2]:
            attr = plug.split(".", 1)[-1]
            if attr not in attrs:
                attrs.append(attr)
        if attrs:
            out[leaf] = attrs
    return out


def _evs(cmds, curve, times):
    """{time: value} of a curve at many times, UI units - ONE query
    (`keyframe -eval` takes every time at once, `layerbake._evs`'s idiom)."""
    times = sorted(set(times))
    if not times:
        return {}
    values = cmds.keyframe(curve, query=True, eval=True,
                           time=[(t, t) for t in times]) or []
    if len(values) != len(times):
        raise RuntimeError("{0} answered {1} values for {2} times".format(
            curve, len(values), len(times)))
    return dict(zip(times, values))


def _is_angle(cmds, plug):
    """True for a plug the API keeps in radians (trap 224's other half)."""
    try:
        return cmds.getAttr(plug, type=True) == "doubleAngle"
    except (RuntimeError, ValueError):
        return False


def _write_curve(plug, frames, values, angle):
    """One fresh animCurve over `frames` - `MFnAnimCurve.addKeys`, which is
    ~16x faster than a setKeyframe a key (trap 224). Times in UI units,
    values in RADIANS for an angle plug. Auto tangents: a dense resample is
    what a Maya bake leaves, and the animator edits it as one."""
    import math as _math

    from maya.api import OpenMaya as om
    from maya.api import OpenMayaAnim as oma

    selection = om.MSelectionList()
    selection.add(plug)
    curve = oma.MFnAnimCurve()
    curve.create(selection.getPlug(0))
    unit = om.MTime.uiUnit()
    times = om.MTimeArray()
    numbers = om.MDoubleArray()
    for frame, value in zip(frames, values):
        times.append(om.MTime(float(frame), unit))
        numbers.append(_math.radians(value) if angle else value)
    curve.addKeys(times, numbers, oma.MFnAnimCurve.kTangentAuto,
                  oma.MFnAnimCurve.kTangentAuto)
    return curve.name()


def _drop_namespace(cmds, namespace):
    """A scratch namespace and everything in it, locks and all (trap 164)."""
    if not cmds.namespace(exists=namespace):
        return
    for node in cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True,
                                   recurse=True, dagPath=True) or []:
        if cmds.objExists(node) and cmds.lockNode(node, query=True,
                                                  lock=True)[0]:
            cmds.lockNode(node, lock=False)
    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)


def compose(plan, sources, target, fps):
    """Write the slot's composite onto the target namespace's skeleton.

    `sources` is {clip package: namespace}, `target` the namespace whose
    skeleton is keyed (the first clip's own import, so the skeleton is exactly
    what a plain import of that clip gives). Returns what was written and what
    could not be.
    """
    cmds = _maya()
    #  the montage's clock is SECONDS (Unreal's) and a curve is keyed in
    #  FRAMES (Maya's UI unit, and the clip's own import landed its keys on
    #  whole frames at the scene's rate), so the source time is read in
    #  frames here and the plan half stays in the montage's own language
    rows = [(frame, clip, time * fps)
            for frame, clip, time in samples(plan, fps)]
    joints = dict((namespace, _joint_map(cmds, namespace))
                  for namespace in set(sources.values()))
    animated = dict((clip, _animated_channels(cmds, joints[namespace]))
                    for clip, namespace in sources.items())
    wanted = channel_plan(animated)
    target_joints = joints[target]

    times_by_clip = {}
    for _frame, clip, time in rows:
        times_by_clip.setdefault(clip, []).append(time)

    #  TWO passes, and the order is load-bearing: the first span's clip IS the
    #  target namespace (its own import is the composite's skeleton), so every
    #  source is read BEFORE the target's curves are deleted. Reading after
    #  made every frame of that clip's spans answer one dead DG value - the
    #  composite stood still through half the take (trap 58's family, found by
    #  the verify's per-frame comparison).
    gathered = []
    held = []
    skipped = []
    for leaf, attr in wanted:
        node = target_joints.get(leaf)
        if not node or not cmds.objExists("{0}.{1}".format(node, attr)):
            skipped.append("{0}.{1}".format(leaf, attr))
            continue
        plug = "{0}.{1}".format(node, attr)
        columns = {}
        for clip, namespace in sources.items():
            source_node = joints[namespace].get(leaf)
            source_plug = ("{0}.{1}".format(source_node, attr)
                           if source_node else "")
            if not source_plug or not cmds.objExists(source_plug):
                columns[clip] = None     # the clip has no such channel
                continue
            curve = _curve_of(cmds, source_plug)
            if curve:
                columns[clip] = _evs(cmds, curve, times_by_clip.get(clip) or [])
            else:
                #  the clip holds this channel still: its own value, which is
                #  the pose it shows for every frame of its spans
                columns[clip] = cmds.getAttr(source_plug)

        frames = []
        values = []
        previous = None
        missed = False
        standing = cmds.getAttr(plug)
        for frame, clip, time in rows:
            column = columns.get(clip)
            if column is None:
                value = previous           # the clip has nothing to say here
                missed = True
            elif isinstance(column, dict):
                value = column.get(time, previous)
            else:
                value = column
            if value is None:
                value = standing
            frames.append(frame)
            values.append(value)
            previous = value
        if missed:
            held.append("{0}.{1}".format(leaf, attr))
        angle = _is_angle(cmds, plug)
        gathered.append((plug, frames,
                         continuous(values) if angle else values, angle))

    #  now the target's own curves go: what the montage plays is this plan and
    #  nothing else.
    stale = []
    for node in target_joints.values():
        stale.extend(cmds.listConnections(node, source=True, destination=False,
                                          type="animCurve") or [])
    if stale:
        cmds.delete(list(set(stale)))

    written = []
    for plug, frames, values, angle in gathered:
        _write_curve(plug, frames, values, angle)
        written.append(plug)

    return {"written": written, "held": sorted(held),
            "skipped": sorted(skipped), "frames": rows[-1][0] if rows else 0}


def import_clip(ref, namespace, set_timeline=True, clip_fps=None):
    """The montage slot `ref` names into `namespace` as one keyed skeleton.

    The shape `formats.import_clip` has - the info dict
    `animimport.import_clip` returns - so `rigimport.import_source` gains one
    branch and everything downstream (the retarget onto a rig or a skeleton,
    Auto, the drag, the square, the clip label, Export FBX) is untouched.
    """
    cmds = _maya()
    from maya_uebridge import animimport

    path = plan_file_of(ref)
    if not os.path.isfile(path):
        raise RuntimeError("the montage plan is gone ({0}) - press Import "
                           "again".format(path))
    payload = read_plan(path)
    plan = plan_of_payload(payload)
    clips = payload.get("clips") or {}
    if not plan.spans:
        raise RuntimeError("{0}: the slot holds no animation".format(
            payload.get("name") or "this montage"))
    missing = [clip for clip in plan.clips
               if not os.path.isfile(clips.get(clip) or "")]
    if missing:
        raise RuntimeError(
            "{0}: the editor did not export {1}".format(
                payload.get("name") or "this montage",
                ", ".join(c.rsplit("/", 1)[-1] for c in missing)))

    #  the FIRST span's clip into the target namespace: the composite's
    #  skeleton is then exactly what a plain import of that clip gives -
    #  hierarchy, orients, rotate orders, and its mesh when Auto asked
    info = animimport.import_clip(clips[plan.clips[0]], namespace,
                                  set_timeline=False, clip_fps=clip_fps,
                                  merge=False)
    sources = {plan.clips[0]: namespace}
    scratch = []
    for index, clip in enumerate(plan.clips[1:], 1):
        other = "{0}_src{1}".format(namespace, index)
        animimport.import_clip(clips[clip], other, set_timeline=False,
                               clip_fps=clip_fps, merge=False)
        sources[clip] = other
        scratch.append(other)

    fps = animimport.scene_fps() or 30.0
    try:
        done = compose(plan, sources, namespace, fps)
    finally:
        for other in scratch:
            _drop_namespace(cmds, other)

    frames = done["frames"]
    if set_timeline:
        cmds.playbackOptions(minTime=0, maxTime=frames,
                             animationStartTime=0, animationEndTime=frames)

    warnings = [info.get("warning") or "",
                plan_line(plan, fps, frames=frames + 1)]
    if done["held"]:
        warnings.append("held where a clip had nothing: "
                        + ", ".join(done["held"][:4]))
    if done["skipped"]:
        warnings.append("not on this skeleton: "
                        + ", ".join(done["skipped"][:4]))
    info.update({"start": 0, "end": frames,
                 "curves": len(done["written"]),
                 "warning": "  |  ".join([w for w in warnings if w]),
                 "montage": {"name": plan.montage, "slot": plan.slot,
                             "frames": frames + 1,
                             "cuts": cuts(plan, fps),
                             "clips": list(plan.clips),
                             "held": done["held"],
                             "skipped": done["skipped"]}})
    return info
