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
