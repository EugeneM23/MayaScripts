"""The Pose Library's Save of an ANIMATION (2026-10-03): a card's header and frames read off the
scene, the source's key times, objects' curves, and the preview sheet a card plays on hover.

The animator: «теперь давай добавим возможность сохранять анимации. Все правила которые работают
для поз должны работать и для анимаций». So a CHARACTER animation card is a pose card per frame -
`capture.character_pose`'s rules over a range:

- the selection names ONE character, by any part of it (`scene.resolve`), and its member bones
  and regions as for a pose (`scene.members_of`, `capture.region_members`); two characters are
  refused, objects selected beside one are left out and said;
- each bone's STATIC half - parent, canonical name, rest, rotate order - is read ONCE, by
  `scene.skeleton` at the current frame (one rest for the whole skeleton, trap 209), into the
  header's `bones`; the header holds no world;
- the per-frame half is ONE time walk over the range (`timewalk.Walk(fresh=False)`: a read
  switches no evaluation; the animator's tweaks are read first and set back after, the time put
  back): every bone's `worldMatrix[0]` and, on a rig, the unrolled limb bones' drive
  (`rigsolve.drive_matrices`), each as seven numbers (`animdata.encode`), into the arrays of
  `frames.json.gz` - every bone of the skeleton, helpers too, in the skeleton's order;
- `key_times` are the source's own keys inside the range, rounded to whole frames, both ends of
  the range always in - the keys of a rig's CONTROLS (its ControlSet: what the animator keyed;
  its game bones are constrained and its helper bones carry a bake on every frame) or of a
  skeleton's joints, looked for through the animation layers' blend nodes. The «Source keys»
  paste keys only there.

An OBJECTS card (nothing of a character selected) holds each selected transform's keyable scalar
unlocked channels as CURVES (`object_curves`): a channel keyed by a plain time curve keeps that
curve's keys inside the range with their tangents - read off a DUPLICATE given a shape-keeping key
at each end of the range (`setKeyframe -insert`), never off the scene's curve; a channel a layer,
a constraint or anything else feeds is sampled on every frame; a free one is a static value.

Frames are WHOLE frames: a range's ends are rounded half up ONCE (`_whole`, `animdata`'s rule:
Python's round() goes to even) and every count, walk and preview frame comes from those two ints.
The header carries them as the floats the card's shape names (`"start": 0.0`).

**The preview** (`preview`) is the thumbnail's machinery over the range - its pieces are
`capture`'s, called here, not copied (fix round 1): the panel the animator looks at
(`maya_vpstudio.active_panel`) at its port's size, `capture.HIDDEN`'s editor flags off for the
blasts and put back (`capture.shown_flags`, `set_flags`), the first frame blasted until two
blasts agree (trap 120, `capture.settle` over `capture.blast_file`, `capture.pump` between), then
ONE playblast of the preview's frames (`look.preview_frames`: at most 60, every `step`-th) with
the thumbnail's options (`capture.blast_options`) into a temporary folder; each frame
centre-cropped square and scaled to 320 px (`capture.square_scaled`), painted into one SPRITE
SHEET (`paint_sheet`, `look.sheet_cell`) and written as the thumbnail is (`capture.save_jpg`);
the tweaks and the time put back. Batch mode, no panel or no Qt: no preview, and the card shows
its still.

**A Save is no step of the animator's undo queue.** It runs outside any undo chunk, so the walk
and the preview's blasts run with the queue off (`_unrecorded`), and so do the duplicates
`object_curves` reads curves off.

`progress` (a `timewalk.Progress`) is stepped once per frame read and once per preview cell
painted; a cancel saves nothing (`CANCELLED`, which the window tells apart from «no preview»).

Measured (2026-10-03, mayapy standalone, Maya 2027):
- `duplicate` of an animCurve is an UNCONNECTED copy; `setKeyframe -insert -time t` on it makes a
  key on the curve's value there with FIXED tangents (the neighbours' facing sides turned fixed
  too, so the shape holds), answers 0 where a key already stands, and past the last key makes one
  on the post-infinity's value; the scene's curve keeps every key;
- read RECORDED, that duplicate leaves steps on the undo queue: the animator's next Ctrl+Z brought
  the deleted duplicate back (`prop_translateX1`) instead of their own last step - unrecorded
  (`_unrecorded`), one Ctrl+Z takes their step back and no curve is left over;
- a walk, and a preview's blasts, throw an unkeyed tweak away, and `keys.Tweaks.restore` sets it
  back with autoKey turned off and on around it - TWO steps of the queue (fix round 1: a
  locator's tx keyed 0/10 and set to 99 by hand at frame 0, autoKey then turned on; after a Save
  over 0-6 the first Ctrl+Z switched autoKey off, the second on, the third off again, tx 99 all
  along - where a scene with no Save took the setAttr back on the second); with the walk and the
  blasts unrecorded the queue is the no-Save scene's, step for step;
- `keyframe -q -breakdown -time (a, b)` answers the TIMES of the breakdown keys in the span;
- `getAttr(plug, time=t)` on a LAYERED channel reads the composite - base plus layer - exactly as
  a time change shows it (frames 0, 3, 5, 7 and 10 compared);
- an animation layer's blend node feeds each channel by itself (`animBlendNodeAdditiveDL.output ->
  translateY`, `...DA.output -> rotateX`), and so does a QUATERNION layer's
  (`animBlendNodeAdditiveRotation.outputX -> rotateX`), whose blend node also takes the node's own
  `rotateOrder` as an input - a walk up a blend node takes curves and blend nodes, nothing else;
- on Manny_Rig a frame of the walk reads 93 bone worlds in 1.5 ms and the eight drives in 6.5 ms.

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md ("What an animation card
is", "Save")
"""

import contextlib
import math
import os
import re
import shutil
import tempfile

import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

from maya_poselib import animdata
from maya_poselib import capture
from maya_poselib import keys
from maya_poselib import look
from maya_poselib import scene
from maya_poselib import store
from maya_poselib import timewalk

NAME = "Anim"                      # a new animation card's name before the animator types one
SHEET_QUALITY = 85                 # the preview sheet's JPG quality (the spec's)
BLAST_BASE = "frame"               # the preview's playblast writes <BLAST_BASE>.<frame>.jpg
FRAME_PADDING = 4
SAMPLED = "spline"                 # the tangents of a channel sampled on every frame

MANY = "pick one character for an animation"
NOTHING = scene.NOTHING
CANCELLED = "cancelled - nothing saved"
EMPTY = "the range %d-%d holds no frame"
NO_BONE = "no bone of %s in the animation of %s"
NO_VIEWPORT = "no viewport for a preview"

_TANGENTS = ("inTangentType", "outTangentType", "inAngle", "inWeight", "outAngle", "outWeight")


# ------------------------------------------------------------------ whole frames

def _whole(value):
    """A time as a whole frame, rounded half UP - `animdata`'s rule (its `_frame`): Python's
    round() goes to even, and a range must not end on 12 for 12.5 and on 14 for 13.5."""
    return int(math.floor(float(value) + 0.5))


def _frames_text(start, end):
    """«48 frames (0-47)»; «1 frame (5)»."""
    count = end - start + 1
    span = "%d" % start if start == end else "%d-%d" % (start, end)
    return "%d frame%s (%s)" % (count, "" if count == 1 else "s", span)


def _span(start, end):
    """The header's range: the whole source frames as the floats the card's shape names, and
    their count."""
    return {"start": float(start), "end": float(end), "frames": end - start + 1}


# ------------------------------------------------------------------ the undo queue

@contextlib.contextmanager
def _unrecorded():
    """Undo recording off for the block, without the flush `undoInfo(state=False)` does, and
    back as it was after, whatever ends the block (`apply._unrecorded`'s rule): a Save is no
    step of the animator's. Around the duplicates `object_curves` reads curves off, and around
    the walk (`_walk`) and the preview's blasts (`_blast`), whose tweak set-back
    (`keys.Tweaks.restore`) turns autoKey off and back - each toggle a step of the queue in
    Maya, so the animator's next Ctrl+Z switched autoKey off instead of taking their last step
    back (fix round 1, measured). A save runs outside any undo chunk - toggled inside one, the
    recording breaks that chunk (trap 145)."""
    was = bool(cmds.undoInfo(query=True, state=True))
    if was:
        cmds.undoInfo(stateWithoutFlush=False)
    try:
        yield
    finally:
        if was:
            cmds.undoInfo(stateWithoutFlush=True)


# ------------------------------------------------------------------ the range

def _highlight():
    """(start, end + 1) highlighted on the time slider - `overrig.slider_selection`, which
    answers only a highlight spanning more than one frame - or None: nothing highlighted, batch
    mode, or a slider that cannot be read. Imported here, late: a seam."""
    try:
        from maya_overrig import overrig
        return overrig.slider_selection()
    except Exception:                                        # noqa: BLE001 - no slider here
        return None


def default_range():
    """(start, end) whole frames: the time slider's highlight when the animator dragged one over
    more than a frame (the slider answers [start, end + 1)), else the playback range."""
    highlight = _highlight()
    if highlight and len(highlight) == 2 and highlight[1] - highlight[0] > 1:
        return _whole(highlight[0]), _whole(highlight[1]) - 1
    return (_whole(cmds.playbackOptions(query=True, minTime=True)),
            _whole(cmds.playbackOptions(query=True, maxTime=True)))


# ------------------------------------------------------------------ the key times

def _time_curves(nodes):
    """Every time curve (`keys.TIME_CURVES`) feeding a KEYABLE channel of `nodes`, each once, in
    the order met: the channel's own curve (unit conversions looked through), and for a channel
    in animation layers every curve behind its blend nodes - a layer's blend node takes the base
    curve, or the blend node below it, as one input and the layer's curve as another; its
    weights come from the layer, which is no curve. A driven-key curve (`animCurveU*`: its x axis
    is a driver's value), a curve feeding a channel the node does not key and a node that is not
    there add nothing."""
    curves, seen, kinds = [], set(), {}

    def kind_of(node):
        if node not in kinds:
            try:
                kinds[node] = cmds.nodeType(node) or ""
            except (RuntimeError, ValueError):
                kinds[node] = ""
        return kinds[node]

    def take(node):
        kind = kind_of(node)
        if node in seen:
            return
        if kind in keys.TIME_CURVES:
            seen.add(node)
            curves.append(node)
        elif kind.startswith("animBlendNode"):
            seen.add(node)
            for source in cmds.listConnections(node, source=True, destination=False,
                                               skipConversionNodes=True) or []:
                take(source)

    for node in nodes or ():
        try:
            keyable = set(cmds.listAttr(node, keyable=True) or [])
            pairs = cmds.listConnections(node, source=True, destination=False,
                                         connections=True, plugs=True,
                                         skipConversionNodes=True) or []
        except (RuntimeError, ValueError):
            continue
        for plug, source in zip(pairs[0::2], pairs[1::2]):
            if plug.split(".", 1)[-1] in keyable:
                take(source.split(".")[0])
    return curves


def key_times(nodes, start, end):
    """Sorted whole frames, as floats: every key time inside [start, end] of every time curve
    feeding a keyable channel of `nodes` (`_time_curves`: directly, or through animBlendNode
    chains - a layered take), each rounded to a whole frame (`_whole`), the two ends always in
    (a paste on the source's keys starts and ends with the clip). An empty range has none."""
    start, end = _whole(start), _whole(end)
    if end < start:
        return []
    found = set([start, end])
    for curve in _time_curves(nodes):
        for time in cmds.keyframe(curve, query=True, time=(start, end), timeChange=True) or []:
            found.add(_whole(time))
    return [float(frame) for frame in sorted(found)]


def _timing_nodes(ref, bones):
    """The nodes whose keys are a character's key times: a rig's CONTROLS (the members of its
    ControlSet, long paths), a skeleton's joints. `cmds.ls` is never handed an empty list."""
    if ref.kind == "rig" and ref.rig is not None:
        members = cmds.sets(ref.rig.control_set, query=True) or []
        return (cmds.ls(members, long=True) or []) if members else []
    return [bone["path"] for bone in bones.values()]


# ------------------------------------------------------------------ a character's frames

def _common(kind):
    """The header's common fields: the pose card's (`capture._common`: the author, the time it
    was made, the scene's file name, the time unit) as an animation's - `skeldar.anim`, named
    «Anim», and no `frame` (an animation is a range)."""
    data = capture._common(kind)
    data.pop("frame", None)
    data.update({"format": store.ANIM_FORMAT, "version": store.VERSION, "name": NAME})
    return data


def _static(bone):
    """A bone's STATIC half, as the header keeps it: `scene.skeleton`'s answer without its
    path, world, drive, joint orient or rotate axis."""
    return {"parent": bone["parent"], "canonical": bone["canonical"], "rest": bone["rest"],
            "rotateOrder": bone["rotateOrder"]}


def _drive_matrices(rig):
    """`rigsolve.drive_matrices(rig)` ({game leaf: 16 floats} of the unrolled limb bones) -
    imported on first use: the solver pulls the retarget modules in, and a skeleton's or objects'
    save never needs them. A seam."""
    from maya_poselib import rigsolve
    return rigsolve.drive_matrices(rig)


def _walk(ref, bones, start, end, progress=None):
    """The per-frame half of a character card - `{"bones": [leaf...], "world": [[7 floats per
    bone] per frame], "drive": {leaf: [[7 floats] per frame]}}` - read in ONE time walk over
    `start`..`end` (`timewalk.Walk(fresh=False)`), or None when the animator cancelled.

    Per frame: every bone's `worldMatrix[0]` in `bones`' order (the skeleton's), encoded
    (`animdata.encode`) one after another into a flat row; on a rig the drives
    (`_drive_matrices`) of the bones the FIRST frame answered for, which are the rig's structure
    and the same every frame - so every drive series holds one entry a frame, as the world rows
    do; then `progress.step`. A cancel leaves the walk at once (the time goes back with it).

    The walk runs with the undo queue off (`_unrecorded`), its exit included: the walk throws
    the animator's unkeyed tweaks away and its exit sets them back, toggling autoKey - left
    recorded, two loose steps the animator's next Ctrl+Z presses replay (fix round 1)."""
    order = list(bones)
    paths = [bones[name]["path"] for name in order]
    rig = ref.rig if ref.kind == "rig" else None
    world, drive, driven = [], {}, None
    count = end - start + 1
    with _unrecorded(), timewalk.Walk(fresh=False) as walk:
        for index, frame in enumerate(range(start, end + 1)):
            walk.go(frame)
            row = []
            for path in paths:
                row.extend(animdata.encode(cmds.getAttr(path + ".worldMatrix[0]")))
            world.append(row)
            if rig is not None:
                matrices = _drive_matrices(rig)
                if driven is None:
                    driven = [leaf for leaf in matrices if leaf in bones]
                for leaf in driven:
                    drive.setdefault(leaf, []).append(animdata.encode(matrices[leaf]))
            if progress is not None and not progress.step(
                    "frame %d (%d of %d)" % (frame, index + 1, count)):
                return None
    return {"bones": order, "world": world, "drive": drive}


def character_animation(ref, nodes, regions, start, end, progress=None):
    """(header, frames, note) of the character `ref` over `start`..`end` (whole frames) as
    `nodes` (the selection's parts of it) name its bones, narrowed by `regions` when given;
    (None, None, why) when no member is left or the animator cancelled. The static half is read
    at the CURRENT frame before the walk; the members and regions as for a pose
    (`capture.character_pose`)."""
    notes = []
    bones, convention = scene.skeleton(ref, notes)
    members = capture.region_members(bones, scene.members_of(ref, nodes, bones), regions)
    if not members:
        return None, None, NO_BONE % (", ".join(regions or ()) or "the selection", ref.label)
    frames = _walk(ref, bones, start, end, progress)
    if frames is None:
        return None, None, CANCELLED
    header = _common("character")
    header.update(_span(start, end))
    header.update({
        "key_times": key_times(_timing_nodes(ref, bones), start, end),
        "character": scene.identity(ref, convention),
        "bones": dict((name, _static(bone)) for name, bone in bones.items()),
        "members": members,
        "regions": scene.regions_of(bones, members),
        "rig_source": bool(frames["drive"]),
        "objects": [],
    })
    line = "%s: %s, %d of %d bones" % (scene.describe([ref], []), _frames_text(start, end),
                                       len(members), len(bones))
    if header["regions"]:
        line += " - " + ", ".join(header["regions"])
    return header, frames, " | ".join([line] + notes)


# ------------------------------------------------------------------ objects' curves

def _number(value):
    """A channel's value as a float (a bool and an enum's int too), None for anything that is no
    number."""
    if isinstance(value, (bool, int, float)):
        return float(value)
    return None


def _copied(curve, start, end):
    """The CURVE of a plain time curve over [start, end]: `{"keys": [[t, v, in type, out type,
    in angle, in weight, out angle, out weight]...], "weighted", "breakdown": [t...]}` - its
    keys there with their tangents, read off a DUPLICATE given a shape-keeping key at each end
    (`setKeyframe -insert`: a clip cut out of the curve plays as the curve did), so the scene's
    curve is never touched. The duplicate is deleted whatever happens; the caller holds the undo
    queue off."""
    duplicate = cmds.duplicate(curve)[0]
    try:
        for frame in (start, end):
            cmds.setKeyframe(duplicate, insert=True, time=frame)
        span = (start, end)
        pairs = cmds.keyframe(duplicate, query=True, time=span, timeChange=True,
                              valueChange=True) or []
        columns = [cmds.keyTangent(duplicate, query=True, time=span, **{flag: True}) or []
                   for flag in _TANGENTS]
        weighted = bool((cmds.keyTangent(duplicate, query=True, weightedTangents=True)
                         or [False])[0])
        breakdown = [float(time) for time in
                     cmds.keyframe(duplicate, query=True, time=span, breakdown=True) or []]
    finally:
        cmds.delete(duplicate)
    out = []
    for index, (time, value) in enumerate(zip(pairs[0::2], pairs[1::2])):
        in_type, out_type, in_angle, in_weight, out_angle, out_weight = (
            column[index] for column in columns)
        out.append([float(time), float(value), str(in_type), str(out_type), float(in_angle),
                    float(in_weight), float(out_angle), float(out_weight)])
    return {"keys": out, "weighted": weighted, "breakdown": breakdown}


def _sampled(plug, start, end):
    """The CURVE of a channel no plain curve holds - a layer's blend node, a constraint, an
    expression or a driven key feeds it: its value on every frame of [start, end]
    (`getAttr(time=)`, measured to read a layered channel's composite) as spline keys. None for
    a channel that is no number. Not measured: a constraint riding an IK chain (a prop held by a
    rigged hand), which `getAttr(time=)` was seen NOT to pull (trap 69) - such a prop is saved
    right once its channels are baked."""
    out = []
    for frame in range(start, end + 1):
        value = _number(cmds.getAttr(plug, time=frame))
        if value is None:
            return None
        out.append([float(frame), value, SAMPLED, SAMPLED, 0.0, 1.0, 0.0, 1.0])
    return {"keys": out, "weighted": False, "breakdown": []}


def _channel(plug, start, end):
    """One channel's CURVE over [start, end] by what feeds it (`keys.feed_of`): a plain time
    curve copied (`_copied`), nothing at all a static value (`{"static": v}`), anything else
    sampled (`_sampled`); None for a plug that is missing or holds no number."""
    kind, node = keys.feed_of(plug)
    if kind == "missing":
        return None
    if kind == "free":
        value = _number(cmds.getAttr(plug))
        return None if value is None else {"static": value}
    if kind == "curve":
        return _copied(node, start, end)
    return _sampled(plug, start, end)


def object_curves(nodes, start, end):
    """[{name, path, attrs: {attr: CURVE}}] of the transforms `nodes` name (a shape or a
    component names its transform; each once, in selection order): per object its leaf name
    without the namespace, its long path, and the CURVE of each keyable scalar unlocked
    attribute over [start, end] (whole frames) - a plain time curve copied through a duplicate,
    a layered or otherwise fed channel sampled every frame, a free one static (`_channel`). A
    channel that cannot be read is left out; an object with no channel keeps an empty record
    (the apply pairs objects by order too). The duplicates are made, read and deleted with the
    undo queue off (`_unrecorded`)."""
    start, end = _whole(start), _whole(end)
    objects, seen = [], set()
    with _unrecorded():
        for node in nodes or ():
            path = scene.dag_object(node)
            if path is None or path in seen:
                continue
            seen.add(path)
            attrs = {}
            try:
                names = cmds.listAttr(path, keyable=True, scalar=True, unlocked=True) or []
            except (RuntimeError, ValueError):
                names = []
            for attr in names:
                try:
                    curve = _channel(path + "." + attr, start, end)
                except (RuntimeError, ValueError, TypeError):
                    continue
                if curve is not None:
                    attrs[attr] = curve
            objects.append({"name": scene.leaf(path), "path": path, "attrs": attrs})
    return objects


# ------------------------------------------------------------------ the card

def build_animation(selection=None, regions=None, start=None, end=None, progress=None):
    """(header, frames, note) of the selection over [start, end] - each end `default_range`'s
    when None, both made whole once (`_whole`): a CHARACTER card when the selection touches
    exactly one character (`character_animation`), else an OBJECTS card of its transforms
    (frames None: an objects card keeps its curves in the header), else (None, None, why) - an
    empty range, two characters, nothing selected, no member left, a cancel (`CANCELLED`).
    `progress` (a `timewalk.Progress`, or None) is stepped once per frame of a character's walk
    - `end - start + 1` steps; an objects card walks no time and steps nothing."""
    if start is None or end is None:
        first, last = default_range()
        start = first if start is None else start
        end = last if end is None else end
    start, end = _whole(start), _whole(end)
    if end < start:
        return None, None, EMPTY % (start, end)
    resolved = scene.resolve(selection)
    refs, loose = [], []
    for path, ref in resolved:
        if ref is None:
            loose.append(path)
        elif all(r.root != ref.root for r in refs):
            refs.append(ref)
    if len(refs) > 1:
        return None, None, MANY
    if refs:
        nodes = [path for path, ref in resolved if ref is not None]
        header, frames, note = character_animation(refs[0], nodes, regions, start, end,
                                                   progress)
        if header is not None and loose:
            note += " | %s outside %s left out" % (scene.describe([], loose), refs[0].label)
        return header, frames, note
    if loose:
        header = _common("objects")
        header.update(_span(start, end))
        header["objects"] = object_curves(loose, start, end)
        return header, None, "%s: %s" % (scene.describe([], loose), _frames_text(start, end))
    return None, None, NOTHING


# ------------------------------------------------------------------ the preview

def _panel():
    """The model panel the animator looks at (`maya_vpstudio.active_panel`), or None. A seam."""
    import maya_vpstudio
    return maya_vpstudio.active_panel()


def _qt():
    """Qt as one namespace (`maya_hubqt.qt()`), or None without it. A seam."""
    import maya_hubqt
    return maya_hubqt.qt()


def _blast(qt, panel, width, height, frames, folder):
    """(blasts taken at the first frame, settled): the first of `frames` blasted until two blasts
    in a row agree (`capture.settle` over `capture.blast_file`, idle events pumped between by
    `capture.pump` - trap 120), then ONE playblast of `frames` into `folder` as
    `<BLAST_BASE>.<frame>.jpg` - the thumbnail's own options (`capture.blast_options`: the
    port's size, offscreen), only where the frames go added.

    Around it, in this order: the editor flags read (`capture.shown_flags`) and the animator's
    tweaks read (`keys.Tweaks`: a playblast steps the time, which throws away unkeyed tweaks on
    keyed channels), the time remembered, the flags off (`capture.set_flags`); after it,
    whatever happened: the flags back, the time back (`MAnimControl`, unrecorded), the tweaks
    set back. All of it with the undo queue off (`_unrecorded`): the set-back toggles autoKey,
    and a preview is no step of the animator's (fix round 1). A playblast that fails raises,
    after all of that."""
    options = capture.blast_options(panel, width, height)
    first = folder + "/first.jpg"
    with _unrecorded():
        shown = capture.shown_flags(panel)
        tweaks = keys.Tweaks()
        here = oma.MAnimControl.currentTime()
        try:
            capture.set_flags(panel, dict((flag, False) for flag in shown))
            _picture, count, settled = capture.settle(
                lambda: capture.blast_file(options, frames[0], first),
                lambda: capture.pump(qt))
            cmds.playblast(frame=list(frames), filename=folder + "/" + BLAST_BASE,
                           framePadding=FRAME_PADDING, **options)
        finally:
            capture.set_flags(panel, shown)
            try:
                oma.MAnimControl.setCurrentTime(here)
            finally:
                tweaks.restore()
    return count, settled


def blasted(folder, base=BLAST_BASE):
    """[(frame, path)] of the image sequence a playblast wrote into `folder` as
    `<base>.<frame>.jpg` (any padding, a negative frame included: `frame.-001.jpg`), sorted by
    frame; [] for a folder that is not there."""
    pattern = re.compile(r"^%s\.(-?\d+)\.jpe?g$" % re.escape(base), re.IGNORECASE)
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    root = folder.replace("\\", "/").rstrip("/")
    found = []
    for name in names:
        match = pattern.match(name)
        if match:
            found.append((int(match.group(1)), root + "/" + name))
    return sorted(found)


def paint_sheet(qt, pictures, path, size=look.PREVIEW_SIZE, progress=None):
    """(ok, note): `pictures` (image paths, in play order) painted into ONE sprite sheet at
    `path` - each centre-cropped square and scaled to `size` px with smooth filtering as the
    thumbnail is (`capture.square_scaled`), into its cell (`look.sheet_cell`:
    `look.sheet_columns` cells to a row, left to right, top to bottom; a short last row stays
    black) - and written as a JPG (SHEET_QUALITY) the thumbnail's way (`capture.save_jpg`:
    through `path + ".part"` and `os.replace`, so a reader never sees half a sheet).
    `progress.step` once per cell; a cancel (False, CANCELLED) and a picture that cannot be read
    write nothing. `qt` is `maya_hubqt.qt()` (a QImage needs no QApplication)."""
    if not pictures:
        return False, "no frame for a preview"
    gui = qt.QtGui
    columns = look.sheet_columns(len(pictures))
    rows = int(math.ceil(len(pictures) / float(columns)))
    sheet = gui.QImage(columns * size, rows * size, gui.QImage.Format_RGB32)
    sheet.fill(gui.QColor(0, 0, 0))
    painter = gui.QPainter(sheet)
    try:
        for index, picture in enumerate(pictures):
            image = gui.QImage(picture)
            if image.isNull():
                return False, "the playblast wrote nothing readable for cell %d" % index
            x, y, _w, _h = look.sheet_cell(index, columns, size)
            painter.drawImage(qt.QtCore.QPoint(x, y), capture.square_scaled(qt, image, size))
            if progress is not None and not progress.step(
                    "preview %d of %d" % (index + 1, len(pictures))):
                return False, CANCELLED
    finally:
        painter.end()
    return capture.save_jpg(sheet, path, SHEET_QUALITY)


def _first_line(error):
    """The first line of an error, short enough for a status line."""
    lines = str(error).strip().splitlines()
    return (lines[0] if lines else type(error).__name__)[:80]


def preview(sheet_path, start, end, progress=None):
    """(ok, note, info): the active panel blasted over `look.preview_frames(start, end)` (whole
    frames: at most PREVIEW_MAX, every `step`-th) and painted into a sprite sheet JPG at
    `sheet_path` (`paint_sheet`); `info` = {"frames", "columns", "size", "step"} - the header's
    `preview`. The HIDDEN flags off and back, the first frame settled (trap 120), the tweaks and
    the time put back (`_blast`); the playblast's frames go to a temporary folder, removed after.

    No preview: (False, why, None) - batch mode, no model panel, a hidden port (smaller than
    `capture.SMALLEST_PORT`, trap 105), no Qt, an empty range, a playblast that failed or wrote
    a frame short; and (False, CANCELLED, None) when the animator cancelled while the cells were
    painted - nothing written then. `progress.step` once per cell painted."""
    if cmds.about(batch=True):
        return False, NO_VIEWPORT, None
    panel = _panel()
    port = capture._port(panel) if panel else None
    if not port:
        return False, NO_VIEWPORT, None
    width, height = port
    if width < capture.SMALLEST_PORT or height < capture.SMALLEST_PORT:
        return False, "the viewport is %dx%d - too small for a preview" % (width, height), None
    qt = _qt()
    if qt is None:
        return False, "no Qt for a preview", None
    start, end = _whole(start), _whole(end)
    frames, step = look.preview_frames(start, end)
    if not frames:
        return False, EMPTY % (start, end), None
    folder = tempfile.mkdtemp(prefix="skeldar_anim_preview_").replace("\\", "/")
    try:
        try:
            count, settled = _blast(qt, panel, width, height, frames, folder)
        except (RuntimeError, OSError) as error:
            return False, "no preview - " + _first_line(error), None
        found = dict(blasted(folder))
        missing = [frame for frame in frames if frame not in found]
        if missing:
            return False, "the playblast wrote %d of %d frames" % (
                len(frames) - len(missing), len(frames)), None
        ok, note = paint_sheet(qt, [found[frame] for frame in frames], sheet_path,
                               look.PREVIEW_SIZE, progress)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    if not ok:
        return False, note, None
    info = {"frames": len(frames), "columns": look.sheet_columns(len(frames)),
            "size": look.PREVIEW_SIZE, "step": step}
    every = "" if step == 1 else ", every %d frames" % step
    return True, "preview from %s: %d cells%s (%dx%d, %d blast%s%s)" % (
        panel, len(frames), every, width, height, count, "" if count == 1 else "s",
        "" if settled else ", textures still loading"), info
