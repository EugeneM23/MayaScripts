"""The Pose Library's Apply for ANIMATION cards (2026-10-03): a clip onto any rig or skeleton,
frame by frame, with Studio Library's paste modes; onto objects; dropped on a character or on the
floor; Blend; Select objects.

The animator: «Все правила которые работают для поз должны работать и для анимаций. Так же мы
должны уметь выбирать способ вставки анимации как в studio library». An animation card is a pose
card per frame (`animdata.bones_at` gives any frame as a pose's bones), so a paste is the pose's
press (`apply`) run along a TIME WALK, everything that does not change from frame to frame
prepared once.

## A character press (`apply`, `apply_onto`, `drop_floor`), in order

1. refusals before anything is read or written (the targets are the pose's: the selection's
   characters, else the only one - `apply._targets`): the layer (`keys.active_layer`: locked; an
   additive layer in quaternion accumulation - a character card always turns bones), the card's
   frames (`NO_FRAMES`: missing, or not covering the clip its header names), the paste range
   (`animdata.paste_plan`: `EMPTY_RANGE`);
2. ONE time walk for the whole press (`timewalk.Walk(fresh=True)`: the animator's unkeyed tweaks
   read first and set back after, the time put back, the solve's DG evaluation entered once);
   the walk ARRIVES at the paste frame `a` (`Walk.arrive`: no time set when the scene already
   stands there - a same-frame time set throws every unkeyed tweak away, and a paste at the
   current frame must read what the animator sees, Main dragged by hand to place the walk
   included: the final review, M2); a ROOTLESS card's root frame read on every pasted frame,
   its heading steadied across the clip (`_clip_roots`, `posemath.clip_roots`: near upside down
   a frame's own heading is noise - a hips roll keyed Main spinning, M3) and handed to the
   travel, the transfer's pelvis offset and the mirror alike; at `a` each target is prepared
   (`_Target`): its skeleton read there
   (`scene.skeleton`), the pairing, the size and the member lists of the clip's FIRST pasted
   frame, whether it carries the travel (`_carry`), one `posemath.Transfer` - its rest alignment
   read once off that first frame UNMIRRORED (a mirrored frame's rotations against its unmirrored
   places align nothing), the frames then handed over mirrored -, the place it stands
   (`Transfer.place`), its solver (`rigsolve.Solver`, `main` for the travel; a skeleton's
   `skelsolve.solve`, `root` for it), and a DRY solve of the first frame: the plugs the press
   keys, what they show before it (`keys.current` - Connect's reference), the first seed. The
   dry solves run UNRECORDED (`_unrecorded`, outside any chunk - trap 145): a rig's solve is a
   chunk of its own, and before the press's it would be one empty Ctrl+Z for the animator;
3. BEFORE anything is cut or keyed, one pass over the pasted frames reads what later frames
   must not read off curves the press rewrites: at Blend < 100 % every planned plug as the take
   stands (the partner of each frame's mix), and the ground a ROOTLESS target that carries no
   travel stands on (`read_ground` - its top joint is a planned member, cut by Replace and keyed
   every frame: M4); then what every planned plug SHOWED when the press began
   (`keys.shown_at_start`: the walk's tweaks reading, else the value);
4. ONE undo chunk (`UNDO_CHUNK`), autoKey off inside it: FIRST every planned plug set to what it
   showed when the press began (`keys.undo_marks`) - each frame's solve records its temporary
   sets and their restores in the chunk at frames that are not the current one, and a Ctrl+Z
   replays them backwards: undone LAST, the mark leaves every channel showing what it showed
   before the press, never the first pasted frame's value (M1) -; the planned plugs' curves'
   infinity and weighting read (`keys.curve_state` - a cut that empties a curve DELETES it,
   measured, and the next key makes a curve with Maya's defaults), then the paste mode on the
   ACTIVE layer's curves of every target's planned plugs (`plan.ops`: Replace cuts [a, b],
   Replace all every key, Insert moves every key at or after `a` later by the clip's length,
   Merge nothing);
5. per pasted frame: the walk arrives there; per target its skeleton read again
   (`scene.refresh_world` - what the card does not hold plays the take under it), the frame's
   source bones decoded (`bones_at`, mirrored when asked), the root frame where the travel puts
   it (`travel · place`, else the ground read before), the transfer, the solve with the
   PREVIOUS frame's values as the
   nearest-euler seed (the curves never flip - trap 108), Connect's offsets, Blend's mix, the
   keys (`keys.write`: the final values, on the frame the walk stands on and the active layer),
   the keyed plugs handed to the walk (`walk.keyed`: never set back as tweaks), their feeding
   nodes dirtied (`keys.feed_of`: a channel the solve's temporary writes left holding a value
   would show it over its new key), the measure (only when the keys are the solve itself -
   never at a blend, which lands between, nor when Connect moved a channel off the transfer on
   purpose: a wrist that stood 20 deg off would read «worst 20 deg»; the rig's
   `Solver.measure`, a skeleton's `apply._measure`), the worst frame kept; Esc in the progress
   window cancels;
6. the curves' infinity and weighting given back (`keys.put_curve_state`), the chunk closed,
   the line (`look.anim_status` per target, joined with « | »): «Walk onto Manny_Rig1: 73
   controls keyed over frames 12-59 (48 frames, replace) on AnimLayer1 - worst 0.003 deg at
   frame 31», a card saved at another rate than the scene's said (`FPS_NOTE`: pasted frame for
   frame), a muted layer said (`keys.layer_note`). A note every frame repeats with another
   number (an IK elbow losing a forearm twist of N deg) is said once (`_note_key`);
7. Cancel: the chunk closed and undone (`cmds.undo`, once - every key, cut and move back), every
   tweak set back (`walk.restore_all`) - `CANCELLED`. With undo off nothing can be undone: what
   was keyed stays, its curves get their state back, the walk never sets the keyed plugs back,
   and the line says what stays (`CANCELLED_KEPT`: the frames keyed, what the mode cut or moved -
   S3). A press that RAISES inside its chunk is undone the same way before the error goes on
   (`_undo_failed`: half a paste is never left behind - S2).

## The travel («от места персонажа»)

A card whose members hold its PELVIS (a whole or a lower body; In place off) carries the clip's
travel: frame i's root frame is `Transfer.travel(source i, first, flip=mirror) · place` - the
source root frame's motion from the first pasted frame, carried into the target's root axes and
scaled, from where the target stands at `a`. A rig's `Main` is written onto it
(`Solver(main=True)`), a skeleton's root joint (`skelsolve.solve(root=True)`), a rootless
skeleton's top joint keeps the moving ground (`posemath._on_ground`). A Main, a root or a
rootless skeleton's top joint whose six rotate / translate channels cannot ALL be written
(locked, driven) carries nothing - half a travel would tear the pelvis off its root - and the line
says so (`rigsolve.MAIN_KEPT`, `ROOT_KEPT`); a hand card, or In place, is the pose rule: the root
never written. Connect never offsets Main or the root: the travel is placed, not offset. A
rootless card's travel moves by its ground frame with the heading `posemath.clip_roots`
steadied across the clip.

## Objects (`_press_objects`)

The pose's pairing (`apply.pair_objects`: the selection by path, name, order; a character's part
never an object); per channel the stored keys clipped to the paste's source range - a range end
that falls between two keys gets a shape-keeping key there (`_inserted`: the stored keys put on a
temporary node's plug by `keys.write_keys`, the paste's own road, then deleted, unrecorded) -,
shifted onto the paste frame; a static attribute one key at `a`; Connect moves a
channel so its first pasted value is what it showed at `a`, Blend mixes each key with what the
channel showed at that key's time (read before the ops); keyed with their tangents
(`keys.write_keys`: angles and weights only without layers - on a layer the tangents are the
layer curve's and only their types travel), a stored breakdown key made a breakdown again
(`_breakdowns`: `keyframe -edit -time (t, t) -breakdown true`, measured on a plain and a layer
curve, undone with the chunk). The paste modes as for a character; a Blend mixes the key VALUES
at the clip's own key times and keeps the clip's tangents - the take's motion between them is no
part of the mix. Measured (mayapy
2027, task 8's probe): a final-value key on an additive layer at a time that is NOT the current
one lands right - Maya reads the layers under it at the KEY's time (tx 15 at frame 10 with the
time at 0: the layer key 5, the base 10, shown 15) - so objects are keyed without a walk; a
temporary `animCurveTU` answers the same tangent angles as an `animCurveTA` keyed with the same
numbers (83.6598 both), and `setKeyframe -insert` between two keys keeps the shape (31.68, the
value before the insert) and turns the neighbouring tangents fixed.

## Drops, Blend, Select objects

`drop_floor` is the pose's road (`apply.drop_floor`: the card's character added at the point,
the layer refused before anything is added) with this press made onto the new character
(`onto`) - every refusal of the press asked first, as an Add cannot be undone (trap 115).
`Blend` previews ONE pose - the clip's frame that falls on the current frame, the first when the
current frame is outside the paste range - through the pose's own session (`apply.Blend`: live,
unrecorded), and its release puts that preview back and pastes the WHOLE range at the session's
weight. `select_objects` is the pose's, plus Main or the root joint when the travel would be
carried.

Checked in mayapy standalone before the end-to-end verify existed (task 8's smoke run, a card of
93 bones built by hand off a keyed Manny_Rig whose Main travels 50 cm and turns 20 deg over 0..5):
onto a second Manny_Rig standing at (200, 0, -100) turned 90 deg, every member on the card
relative to its root to 0.0012 deg / 0.0002 cm and its root on the travel carried from where it
stood to 0.000000 cm, 74 controls keyed over 10-15 in 0.21 s a frame; onto the Manny skeleton
moved and turned, 80 joints (its root for the travel) to 0.00005 deg, 0.06 s a frame; one
`cmds.undo()` right after a paste - every key and curve gone, Main back; Esc on the third frame -
nothing of that paste left; Insert over keys at 40 / 60 at 50 - the 60 at 66; Replace all - the
emptied curve's cycle infinity given back; an objects card's sub-range 3..14 of a spline curve
at 30 - keys at 30 / 37 / 41, the curve equal to the source's to 0.000000000, the temporary node
gone and the selection kept.

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md ("Apply - the
options", "The paste modes", "Root motion", "Per frame", "The press, in order", "Objects",
"Blend", "Drops", "Select objects").
"""

import contextlib
import re
import traceback
from collections import OrderedDict

import maya.cmds as cmds

from maya_poselib import animdata
from maya_poselib import apply as ap
from maya_poselib import keys
from maya_poselib import look
from maya_poselib import posemath as pm
from maya_poselib import rigsolve
from maya_poselib import scene
from maya_poselib import skelsolve
from maya_poselib import timewalk

__all__ = ["apply", "apply_onto", "drop_floor", "select_objects", "Blend", "UNDO_CHUNK"]

UNDO_CHUNK = "skeldarAnimApply"
CLIP_NODE = "skeldarAnimClip"       # the temporary node whose curve a stored curve is cut on
CLIP_ATTR = "clip"                  # ... and its plug
ROTATE = ("rotateX", "rotateY", "rotateZ")
TRANSLATE = ("translateX", "translateY", "translateZ")
EPS = 1e-6                          # two key times this close are one
# the worst frame of a paste is the one furthest past these (rigsolve.TOL_DEG / TOL_CM)
TOL_DEG = 0.01
TOL_CM = 0.01

NO_FRAMES = "the card has no frames - save it again"
CANCELLED = "cancelled - nothing changed"
CANCELLED_KEPT = "cancelled - undo is off, so what was done stays: %s"
FPS_NOTE = "the card is %s, the scene %s - pasted frame for frame"
ROOT_KEPT = "%s kept where it stands (%s) - the travel is not carried"
BREAKDOWN_LOST = "the breakdown keys of %s stay plain keys (%s)"
NO_ROOT = "not found"
CARRIED = " + %s (it carries the travel)"
STEP = "%s: frame %s"

# a number standing free - «31 deg», «2 member(s)» - never the digits of a name (spine_01, Rig1)
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")


# ------------------------------------------------------------------ pure

def _options(options):
    """`animdata.Options` of what a caller passes: None the defaults, an `Options` as it is, a
    mapping (the window's remembered values) made valid by `animdata.options_from`."""
    if options is None:
        return animdata.Options()
    if isinstance(options, animdata.Options):
        return options
    return animdata.options_from(options)


def _has_frames(frames):
    """Does a character card's frames data hold any frame at all?"""
    return bool(frames) and bool(frames.get("bones")) and bool(frames.get("world"))


def _covers(frames, plan):
    """Do the frames arrays hold every frame the plan pastes (a header naming more frames than
    its data holds is a broken card)?"""
    count = len(frames["world"])
    return all(0 <= index < count for _source, index, _time in plan.frames)


def _note_key(text):
    """A note's key with its free-standing numbers masked: a note every frame repeats with
    another number - «the FK forearm twist is lost on arm_l ...: 31 deg» - is one note, the
    first seen kept; the digits of a name (spine_01, Manny_Rig1) are the name's."""
    return _NUMBER.sub("#", text)


def _clip(stored, lo, hi):
    """(the stored keys inside [lo, hi], the range ends that need a key inserted) of a stored
    curve's keys (`[t, v, ...]`): an end needs one when it falls strictly BETWEEN two keys and
    carries none; before the first key or after the last the curve holds its end value
    (`_held`), and a key already there is the end. Copies of the keys. Pure."""
    times = [float(key[0]) for key in stored]
    inside = [list(key) for key in stored if lo - EPS <= float(key[0]) <= hi + EPS]
    need = []
    for end in sorted(set([lo, hi])):
        if any(abs(time - end) <= EPS for time in times):
            continue
        if any(time < end for time in times) and any(time > end for time in times):
            need.append(end)
    return inside, need


def _held(stored, time):
    """The value a stored curve holds at `time` outside its keys: its first key's before them,
    its last key's after them. Pure."""
    ordered = sorted(stored, key=lambda key: float(key[0]))
    return float(ordered[0][1] if time < float(ordered[0][0]) else ordered[-1][1])


def _shown(plan, now):
    """(source frame, index into the frames arrays) of the frame a Blend previews: the planned
    frame whose target time is nearest `now` when `now` is inside the paste range, else the
    FIRST (the spec's rule: the first when the current frame falls outside). Pure."""
    if plan.a - EPS <= now <= plan.b + EPS:
        found = min(plan.frames, key=lambda frame: (abs(frame[2] - now), frame[2]))
    else:
        found = plan.frames[0]
    return found[0], found[1]


def _card_refusal(header):
    if not header:
        return ap.NO_CARD
    if not header.get("bones"):
        return ap.NO_BONES
    return ""


def _travels(header, members, options):
    """Does the press carry the clip's travel: In place off and the card's members holding its
    PELVIS (`posemath._find` on the header's bones) - a whole or lower body; a hand card is
    always in place."""
    if options.in_place:
        return False
    pelvis = pm._find(header.get("bones") or {}, "pelvis")
    return pelvis is not None and pelvis in (members or ())


# ------------------------------------------------------------------ seams (the scene through apply)

def _targets(selection, prefer=None):
    """(the characters a press acts on, refusal): the pose's rule (`apply._targets`). A seam."""
    return ap._targets(selection, prefer)


def _character_of(root):
    """The character a drop landed on (`scene.character_of`). A seam."""
    return scene.character_of(root)


def _main_of(ref):
    """The long path of the rig's Main (`rigsolve._main_path`: `rig.main`, else its namespace's
    `Main`), or None. A seam."""
    return rigsolve._main_path(ref.rig)


def _rotations(values):
    """`apply.rotations_of`: each node's rotate triple and order, for `apply.mix`. A seam."""
    return ap.rotations_of(values)


def _measure_skeleton(ref, values, skipped, wanted, members, bones):
    """(worst deg, worst cm, its leaf) of a skeleton's members against `wanted` as it stands
    after the keys - `apply._measure`'s skeleton half (the root and the skipped joints aside).
    A seam."""
    return ap._measure(ap.Plan(ref, values, {}, [], dict(skipped or {})),
                       ap.Extra(wanted, members, bones, None))


def _objects_pairs(header, selection):
    """([(stored object, scene path)], notes, refusal) - `apply._objects_entry`'s pairing for an
    animation's objects (whose attributes hold curves, not values): the selection's character
    parts left out and named, the stored objects found by leaf never a character's. A seam."""
    objects = (header or {}).get("objects") or []
    if not objects:
        return [], [], ap.NO_OBJECTS
    plural = "" if len(objects) == 1 else "s"
    picked = ap._selected(selection)
    selected, parts = ap._not_characters(picked)
    if picked and not selected:
        return [], [], parts + ap.ONTO_OBJECTS
    found = {}
    if not selected:
        paths = dict((i, ap._find_object(record)) for i, record in enumerate(objects))
        free = set(ap._not_characters([p for p in paths.values() if p])[0])
        found = dict((i, path if path in free else None) for i, path in paths.items())
    matched, how = ap.pair_objects(objects, selected, found)
    if not matched:
        if selected:
            return [], [], ap.SELECTION_UNMATCHED % (len(objects), plural, len(objects))
        return [], [], ap.OBJECTS_MISSING % (len(objects), plural)
    notes = ([parts + ap.LEFT_OUT] if parts else []) + ([ap.BY_ORDER] if "order" in how else [])
    taken = set(path for _record, path in matched)
    idle = [path for path in selected if path not in taken]
    if idle:
        notes.append(ap.NOT_MATCHED % (len(idle), ap._named(scene.leaf(p) for p in idle)))
    return matched, notes, ""


# ------------------------------------------------------------------ scene state

@contextlib.contextmanager
def _chunk():
    """The block as ONE undo chunk (`UNDO_CHUNK`), autoKey off inside it and put back - closed
    whatever happens, a failing autoKey query included. Every solve's own chunk nests in it, so
    one Ctrl+Z is the whole paste. Never an empty chunk: `autoKeyframe -state` is a step on the
    undo queue even when it sets the state autoKey already has (measured), so `_undo_failed`
    undoes this chunk and never the animator's step before it."""
    cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK)
    auto = None
    try:
        auto = cmds.autoKeyframe(query=True, state=True)
        cmds.autoKeyframe(state=False)
        yield
    finally:
        try:
            if auto is not None:
                cmds.autoKeyframe(state=auto)
        finally:
            cmds.undoInfo(closeChunk=True)


def _undo_failed(recording, walk=None):
    """A press that RAISED inside its chunk (the chunk closed by then): the chunk undone when
    undo is on - half a paste is never left behind (the final review, S2) - and the walk's
    tweaks all set back (`walk.restore_all`: nothing it keyed stands). With undo off there is
    nothing to undo. Never raises over the press's own error."""
    if not recording:
        return
    try:
        cmds.undo()
    except Exception:                                    # noqa: BLE001 - the press's error goes on
        traceback.print_exc()
    if walk is not None:
        try:
            walk.restore_all()
        except Exception:                                # noqa: BLE001
            traceback.print_exc()


def _kept(done, plan, noun):
    """CANCELLED_KEPT's line - a press cancelled with undo off keeps what it did, and says what:
    `done` («frames 12-14», «3 channels») keyed, and what the paste mode did to the keys there
    (`plan.ops`): Replace cut [a, b], Replace all every key, Insert moved the keys from `a` on
    (the final review, S3)."""
    parts = ["%s keyed" % done] if done else ["nothing keyed"]
    for op in plan.ops:
        if op[0] == "cut":
            parts.append("the %s' keys in %s-%s cut" % (noun, _num(op[1]), _num(op[2])))
        elif op[0] == "cut_all":
            parts.append("every key of the %s cut" % noun)
        elif op[0] == "shift":
            parts.append("the %s' keys from %s on moved %s later" % (noun, _num(op[1]),
                                                                       _num(op[2])))
    return CANCELLED_KEPT % ", ".join(parts)


def _num(value):
    """A frame as the line writes it: «12», «12.5»."""
    return "%g" % float(value)


def _span(times):
    """«frame 12» / «frames 12-14» of the target times keyed so far, "" for none."""
    if not times:
        return ""
    if len(times) == 1:
        return "frame %s" % _num(times[0])
    return "frames %s-%s" % (_num(min(times)), _num(max(times)))


@contextlib.contextmanager
def _unrecorded():
    """Undo recording off for the block without the flush `undoInfo(state=False)` does, and back
    as it was (`apply._unrecorded`'s rule, on this module's `cmds`). Only ever outside a chunk:
    toggled inside one it breaks that chunk (trap 145)."""
    was = bool(cmds.undoInfo(query=True, state=True))
    if was:
        cmds.undoInfo(stateWithoutFlush=False)
    try:
        yield
    finally:
        if was:
            cmds.undoInfo(stateWithoutFlush=True)


def _plan(header, options):
    """`animdata.paste_plan` of the card at the current time; raises its ValueError."""
    return animdata.paste_plan(header.get("start", 0.0), header.get("end", 0.0),
                               header.get("key_times"), options,
                               cmds.currentTime(query=True))


def _checked_plan(header, frames, options):
    """(the paste plan, refusal) of a character card: its frames there and covering the plan,
    the range not empty."""
    if not _has_frames(frames):
        return None, NO_FRAMES
    try:
        plan = _plan(header, options)
    except ValueError as error:
        return None, str(error)
    if not _covers(frames, plan):
        return None, NO_FRAMES
    return plan, ""


def _ops(ops, plugs, layer):
    """The paste mode's `ops` (`PastePlan.ops`) on the plugs' curves on `layer`."""
    if not plugs:
        return
    for op in ops:
        if op[0] == "cut":
            keys.cut(plugs, layer, op[1], op[2])
        elif op[0] == "cut_all":
            keys.cut(plugs, layer)
        elif op[0] == "shift":
            keys.shift(plugs, layer, op[1], op[2])


def _dirty(plugs):
    """The nodes feeding the keyed plugs (a curve, a layer's blend node) dirtied, so each shows
    its new key: a channel the solve set and put back holds that value over the key until the
    next time change (`apply._key_entries`' measured rule)."""
    feeds = []
    for plug in plugs:
        kind, node = keys.feed_of(plug)
        if kind in ("curve", "layer") and node and node not in feeds:
            feeds.append(node)
    if feeds:
        cmds.dgdirty(feeds)


def _blocked(node):
    """«<attr> <why>» of the first of the node's rotate and translate channels that cannot be
    written (`keys.writable`), "" when all six can."""
    for attr in ROTATE + TRANSLATE:
        ok, why = keys.writable(node + "." + attr)
        if not ok:
            return "%s %s" % (attr, why)
    return ""


def _carry(ref, bones, travel):
    """(carries, the node that carries it, note): may this target carry the clip's travel?
    Not asked (`travel` False): no, and nothing to say. A rig carries it on its Main, a skeleton
    on its root joint - each only when all six of its rotate / translate channels can be
    written (half a travel - turned, not moved - would tear the pelvis off its root); else not,
    and the note says why (`rigsolve.MAIN_KEPT`, `ROOT_KEPT`). A skeleton with no root of its
    own carries it on its moving ground: its top joint, a member - under the same rule, all six
    of ITS channels or no travel (the final review, S6: a locked hips translate would have
    turned the body on a ground that stayed)."""
    if not travel:
        return False, None, ""
    if ref.kind == "rig":
        node = _main_of(ref)
        if not node:
            return False, None, rigsolve.MAIN_KEPT % rigsolve.NO_MAIN
        why = _blocked(node)
        return (False, None, rigsolve.MAIN_KEPT % why) if why else (True, node, "")
    if not pm.has_root(bones):
        top = pm.root_of(bones)
        node = (bones.get(top) or {}).get("path")
        why = _blocked(node) if node else ""
        return (False, None, ROOT_KEPT % (top, why)) if why else (True, None, "")
    root = skelsolve.root_leaf(ref, bones)
    node = (bones.get(root) or {}).get("path")
    if not node:
        return False, None, ROOT_KEPT % (root or "the root", NO_ROOT)
    why = _blocked(node)
    return (False, None, ROOT_KEPT % (root, why)) if why else (True, node, "")


def _plugs_of(values, node):
    """The plugs of `values` on `node` (a long path), however the solver spelled it - a rig's
    plugs carry the short name (`rigsolve`'s spelling), a skeleton's the long path."""
    names = set([node]) | set(cmds.ls(node) or [])
    return [plug for plug in values if plug.rsplit(".", 1)[0] in names]


def _clip_roots(frames, first, plan):
    """{index into the frames arrays: om.MMatrix}: the source's ROOT FRAME on every frame from
    the first pasted to the last (`posemath.clip_roots` over its top joint's world, decoded off
    the arrays): a ROOTLESS source's ground heading steadied across the clip - read frame by
    frame, a hips roll's near-upside-down frames read a 2 deg tilt as a half turn and keyed
    Main / the root spinning (the final review, M3). None for a source with a root of its own:
    its root bone is read per frame as it always was."""
    root = pm.root_of(first)
    if root is None or pm.has_root(first):
        return None
    names = list(frames.get("bones") or ())
    if root not in names:
        return None
    slot = names.index(root)
    lo, hi = plan.frames[0][1], plan.frames[-1][1]
    indices = list(range(lo, hi + 1))
    worlds = [animdata.decode(frames["world"][i][7 * slot:7 * slot + 7]) for i in indices]
    return dict(zip(indices, pm.clip_roots(first, worlds)))


# ------------------------------------------------------------------ one character

class _Target(object):
    """One character of a press, prepared ONCE at the paste frame (the module's step 2), then
    keyed frame by frame (`key`)."""

    def __init__(self, ref, first, source, members, travel, alpha, connect, first_root=None):
        """`first` is the clip's first pasted frame UNMIRRORED (the transfer's alignment),
        `source` the same frame as the press hands it over (mirrored when asked), `members` the
        card's members as the press uses them (mirrored when asked); `travel` - the card would
        carry the travel (`_travels`); `first_root` the source's root frame at that frame when
        the press steadied it (`_clip_roots`), else None."""
        self.ref = ref
        self.rig = ref.kind == "rig"
        self.notes = OrderedDict()             # note key -> note, the first seen kept
        self.skipped = OrderedDict()
        self.nodes = set()                     # the nodes that took a key
        self.handed = set()                    # the plugs handed to the walk's `keyed`
        self.worst = self.worst_frame = None
        self.score = 0.0
        self.partner = {}                      # target time -> {plug: the take there}
        self.grounds = {}                      # target time -> its root frame, read before
        found = []
        self.bones = scene.skeleton(ref, found)[0]
        self.pairs = pm.pairs(source, self.bones)
        scale = pm.scale_between(source, self.bones, self.pairs)
        self.members = ap.target_members(self.bones, self.pairs, members)
        missing = ap.unpaired_note(ap.unpaired(members, self.pairs, source),
                                   ap.target_label(ref))
        self.carry, self.root_node, kept = _carry(ref, self.bones, travel)
        self._note(found + [missing, kept])
        self.transfer = pm.Transfer(first, self.bones, self.pairs, members,
                                    use_drive=self.rig, scale=scale)
        self.place = self.transfer.place(self.bones)
        self.solver = rigsolve.Solver(ref.rig, self.members, main=self.carry) \
            if self.rig else None
        # the DRY solve of the first frame, as it will be keyed: which plugs, and the seed
        wanted = self.transfer.frame(source, self.bones, self.place if self.carry else None,
                                     source_root=first_root)
        solution = self._solve(self.bones, wanted, None)
        self._take(solution)
        self.dry = OrderedDict(solution.values)
        self.plugs = list(self.dry)
        # a ROOTLESS target that carries no travel stands on the ground its top joint makes -
        # a planned member: Replace cuts its curve and every frame keys it, so frame i read its
        # ground off the curve the press was rewriting (the final review, M4). That ground is
        # read at every pasted frame BEFORE the ops (`read_ground`) and handed to the transfer
        self.reads_ground = False
        if self.plugs and not self.carry and not pm.has_root(self.bones):
            top = (self.bones.get(pm.root_of(self.bones)) or {}).get("path")
            self.reads_ground = bool(top and _plugs_of(self.dry, top))
        self.before = keys.current(self.plugs) if self.plugs else {}
        self.seed = OrderedDict(self.dry)
        self.offsets = {}
        if connect and self.plugs:
            skip = _plugs_of(self.dry, self.root_node) if self.root_node else ()
            self.offsets = animdata.connect_offsets(self.before, self.dry, skip)
        # did Connect move any channel off the transfer? Then no frame is measured (`key`).
        # Exact on purpose: only an offset of exactly 0 leaves the keys the solve itself
        self.connected = any(self.offsets.values())
        self.rotations = _rotations(self.dry) if alpha < 1.0 and self.plugs else {}

    def _note(self, texts):
        for text in texts or ():
            if text:
                self.notes.setdefault(_note_key(text), text)

    def _take(self, solution):
        """A solution's notes and skipped plugs, each said once."""
        self._note(solution.notes)
        for name, why in (solution.skipped or {}).items():
            self.skipped.setdefault(name, why)

    def _solve(self, bones, wanted, seed):
        if self.rig:
            return self.solver.solve(wanted, seed)
        return skelsolve.solve(self.ref, bones, wanted, self.members, seed=seed, root=self.carry)

    def _measure(self, wanted, values, skipped, bones):
        if self.rig:
            return self.solver.measure(wanted)
        return _measure_skeleton(self.ref, values, skipped, wanted, self.members, bones)

    def _worse(self, measured, time):
        """Keep the frame furthest past the tolerances (`TOL_DEG`, `TOL_CM`) and its numbers."""
        if not measured:
            return
        deg, cm = float(measured[0]), float(measured[1])
        score = max(deg / TOL_DEG, cm / TOL_CM)
        if self.worst is None or score > self.score:
            self.worst, self.score, self.worst_frame = (deg, cm), score, time

    def read_ground(self, time):
        """The target's root frame as it stands at `time` (`Transfer.place` of its skeleton read
        there) - read by the press's pass BEFORE its ops (M4)."""
        self.grounds[time] = self.transfer.place(scene.refresh_world(self.ref, self.bones))

    def key(self, time, source, shown, first, mirror, layer, alpha, keyed, roots=None):
        """One pasted frame (the module's step 5), the walk standing on `time`: `source` is the
        frame's bones unmirrored (the travel reads them), `shown` as the press hands them over
        (mirrored when asked), `first` the first pasted frame unmirrored; `keyed` the walk's
        list of the plugs keyed; `roots` - (this frame's, the first's) source root frame when
        the press steadied them (`_clip_roots`), else None. The root frame: where the travel
        puts it, else the ground read before the ops (`read_ground`), else as it stands."""
        bones = scene.refresh_world(self.ref, self.bones)
        root_world = None
        if self.carry:
            root_world = self.transfer.travel(source, first, flip=mirror, roots=roots) * \
                self.place
        elif self.reads_ground:
            root_world = self.grounds.get(time)
        wanted = self.transfer.frame(shown, bones, root_world,
                                     source_root=roots[0] if roots else None)
        solution = self._solve(bones, wanted, self.seed)
        self._take(solution)
        values = OrderedDict(solution.values)
        self.seed = values                       # the next frame's eulers nearest these
        if self.offsets:
            values = animdata.apply_offsets(values, self.offsets)
        if alpha < 1.0:
            values = ap.mix(self.partner.get(time, {}), values, alpha, self.rotations)
        if not values:
            return
        written = keys.write(values, time, layer)
        # each plug handed to the walk ONCE: its exit (`keys.Tweaks.restore`) resolves every
        # entry to its node's UUID, and a frame-by-frame list would repeat them all every frame
        fresh = [plug for plug in written.plugs if plug not in self.handed]
        self.handed.update(fresh)
        keyed.extend(fresh)
        self.nodes.update(plug.rsplit(".", 1)[0] for plug in written.plugs)
        self._note(written.notes)
        _dirty(written.plugs)
        # measured only when the keys ARE the transfer's solve: a blend lands between the take
        # and the clip by design, and Connect moves its channels off the transfer on purpose
        # (each starts where it stood) - against `wanted` either reads as the transfer's error
        # («worst 20 deg» for a wrist that stood 20 deg off the clip's first frame)
        if alpha >= 1.0 and not self.connected and written.plugs:
            self._worse(self._measure(wanted, values, solution.skipped, bones), time)

    def status(self, header, plan, options, layer, alpha, mirror, notes=()):
        """This target's mapping for `look.anim_status`."""
        lines = ap.shown_notes(list(notes) + list(self.notes.values()) +
                               ap._skipped_note(self.skipped))
        return {"name": header.get("name"), "target": ap.target_label(self.ref),
                "count": len(self.nodes), "noun": ap._noun(self.ref),
                "layer": layer.name if layer is not None else None,
                "a": plan.a, "b": plan.b, "frames": plan.b - plan.a + 1, "mode": options.mode,
                "worst": self.worst, "worst_frame": self.worst_frame, "notes": lines,
                "alpha": alpha, "mirror": bool(mirror)}


def _result(targets, header, plan, options, layer, alpha, mirror):
    """(ok, the line): every target's `look.anim_status`, the first carrying what concerns the
    press as a whole - a muted layer, a card at another rate than the scene's."""
    extra = []
    if any(target.nodes for target in targets):
        hidden = keys.layer_note(layer)
        if hidden:
            extra.append(hidden)
    fps, unit = header.get("fps"), cmds.currentUnit(query=True, time=True)
    if fps and unit and fps != unit:
        extra.append(FPS_NOTE % (fps, unit))
    rows = [target.status(header, plan, options, layer, alpha, mirror,
                          extra if n == 0 else ()) for n, target in enumerate(targets)]
    return any(row["count"] for row in rows), look.anim_status(rows)


def _press_refs(header, frames, refs, mirror=False, alpha=1.0, options=None, progress=None):
    """The character press onto `refs` (the module's steps 1-7)."""
    options = _options(options)
    layer, refusal = keys.active_layer()
    if refusal:
        return False, refusal
    note = keys.quaternion_note(layer)
    if note:
        return False, note                    # a character card always turns its bones
    plan, refusal = _checked_plan(header, frames, options)
    if refusal:
        return False, refusal
    alpha = ap._clamp(alpha)
    if alpha <= 0.0:
        return False, ap.BLEND_ZERO
    members = list(header.get("members") or ())
    name = header.get("name") or "Animation"
    recording = bool(cmds.undoInfo(query=True, state=True))
    with timewalk.Walk(fresh=True) as walk:
        # `arrive`: a paste starting on the current frame reads the scene as the animator sees
        # it there, unkeyed tweaks included - Main dragged by hand to place the walk (M2)
        walk.arrive(plan.a)
        first_index = plan.frames[0][1]
        first = animdata.bones_at(header, frames, first_index)
        roots = _clip_roots(frames, first, plan)
        first_root = roots[first_index] if roots else None
        source, used = pm.mirror(first, members, root_frame=first_root) if mirror \
            else (first, members)
        travel = _travels(header, used, options)
        with _unrecorded():
            targets = [_Target(ref, first, source, used, travel, alpha, options.connect,
                               first_root) for ref in refs]
        if not any(target.plugs for target in targets):
            return _result(targets, header, plan, options, layer, alpha, mirror)
        # BEFORE anything is cut or keyed: the take each frame mixes with (Blend), the ground a
        # rootless target stands on (M4) - read at every pasted frame
        if alpha < 1.0 or any(target.reads_ground for target in targets):
            for _source, _index, time in plan.frames:
                walk.arrive(time)
                for target in targets:
                    if target.plugs and alpha < 1.0:
                        target.partner[time] = keys.current(target.plugs)
                    if target.reads_ground:
                        target.read_ground(time)
        planned = OrderedDict()
        for target in targets:
            planned.update((plug, None) for plug in target.plugs)
        began = keys.shown_at_start(walk.tweaks, list(planned))
        cancelled, keyed = False, []
        try:
            with _chunk():
                # the chunk's first step: every planned channel set to what it showed when the
                # press began - undone LAST, so one Ctrl+Z leaves each showing that (M1)
                keys.undo_marks(began)
                states = [keys.curve_state(target.plugs, layer) for target in targets]
                for target in targets:
                    _ops(plan.ops, target.plugs, layer)
                for _source, index, time in plan.frames:
                    walk.arrive(time)
                    bones = animdata.bones_at(header, frames, index)
                    root = roots.get(index) if roots else None
                    shown = pm.mirror(bones, members, root_frame=root)[0] if mirror else bones
                    pair = (root, first_root) if roots else None
                    for target in targets:
                        target.key(time, bones, shown, first, mirror, layer, alpha, walk.keyed,
                                   pair)
                    keyed.append(time)
                    if progress is not None and not progress.step(STEP % (name, "%g" % time)):
                        cancelled = True
                        break
                # with undo off a cancel keeps its keys: their curves get their state back too
                if not cancelled or not recording:
                    for state in states:
                        keys.put_curve_state(state, layer)
        except BaseException:
            _undo_failed(recording, walk)
            raise
        if cancelled:
            if recording:
                cmds.undo()
                walk.restore_all()
                return False, CANCELLED
            # undo off: what was keyed stays - and so do the walk's `keyed` (never set back)
            return False, _kept(_span(keyed), plan, "pasted channels")
    return _result(targets, header, plan, options, layer, alpha, mirror)


# ------------------------------------------------------------------ objects

def _read_keys(curve, lo, hi):
    """[[t, v, inType, outType, inAngle, inWeight, outAngle, outWeight]] of a curve's keys in
    [lo, hi], in time order - a stored CURVE's keys."""
    span = (lo, hi)

    def keyframe(**flag):
        return list(cmds.keyframe(curve, query=True, time=span, **flag) or [])

    def tangent(**flag):
        return list(cmds.keyTangent(curve, query=True, time=span, **flag) or [])

    columns = [keyframe(timeChange=True), keyframe(valueChange=True),
               tangent(inTangentType=True), tangent(outTangentType=True),
               tangent(inAngle=True), tangent(inWeight=True),
               tangent(outAngle=True), tangent(outWeight=True)]
    return [list(key) for key in zip(*columns)]


def _inserted(stored, weighted, lo, hi, need):
    """A stored curve's keys in [lo, hi] with a key INSERTED at each time of `need`: the stored
    keys put on a plain double plug of a temporary node (`CLIP_NODE`, a network) by
    `keys.write_keys` with their tangents - the paste's own road, so the cut sees the curve the
    paste would make: an `animCurveTU`, whose tangent angles read as an angle or a distance
    curve's do, measured -, `setKeyframe -insert` at each end - the shape kept, measured -, the
    keys read back (`_read_keys`), the node and its curve deleted. [] when no curve was made.
    Unrecorded, outside any chunk: a cut of the card's own data, no step of the press;
    `skipSelect`: a new node is selected otherwise."""
    with _unrecorded():
        holder = cmds.createNode("network", name=CLIP_NODE, skipSelect=True)
        made = [holder]
        try:
            cmds.addAttr(holder, longName=CLIP_ATTR, attributeType="double", keyable=True)
            plug = holder + "." + CLIP_ATTR
            keys.write_keys(plug, stored, None, weighted, tangents=True)
            curve = keys.curve_for(plug, None)
            if curve is None:
                return []
            made.append(curve)
            for time in need:
                cmds.setKeyframe(plug, insert=True, time=time)
            return _read_keys(curve, lo, hi)
        finally:
            gone = [node for node in made if cmds.objExists(node)]
            if gone:
                cmds.delete(gone)


def _object_keys(curve, lo, hi, plan):
    """([key in TARGET time], weighted) of one stored CURVE pasted with `plan`: a static value
    one key at `a`; keys clipped to the source range [lo, hi] (`_clip`, a key inserted at an end
    that falls between two - `_inserted`), shifted by the plan's offset; a range between no keys
    one key of the value the curve holds there."""
    if not isinstance(curve, dict):
        return [], False
    if "static" in curve:
        return [[float(plan.a), float(curve["static"])]], False
    stored = [list(key) for key in curve.get("keys") or () if len(key) >= 2]
    if not stored:
        return [], False
    weighted = bool(curve.get("weighted"))
    inside, need = _clip(stored, lo, hi)
    if need:
        inside = _inserted(stored, weighted, lo, hi, need)
    if not inside:
        inside = [[float(lo), _held(stored, lo)]]
    return [[float(key[0]) + plan.offset] + list(key[1:]) for key in inside], weighted


def _breakdown_times(curve, lo, hi, plan, landed):
    """The TARGET times of a stored CURVE's breakdown keys (`"breakdown": [t...]`, source times)
    inside the paste's source range [lo, hi], each one a key of `landed` (the keys the paste
    makes - an end key `_inserted` is a new key, never a breakdown). Pure."""
    if not isinstance(curve, dict):
        return []
    times = [float(key[0]) for key in landed]
    out = []
    for source in curve.get("breakdown") or ():
        try:
            source = float(source)
        except (TypeError, ValueError):
            continue
        if not lo - EPS <= source <= hi + EPS:
            continue
        target = source + plan.offset
        if any(abs(target - time) <= EPS for time in times):
            out.append(target)
    return out


def _breakdowns(plug, layer, times):
    """The keys at `times` on the plug's curve on `layer` made breakdowns (`keyframe -edit
    -breakdown`) - the objects card keeps which of its keys were breakdowns, and a paste that
    dropped it turned them into ordinary keys (the final review, S4). Notes for what could not
    be done."""
    curve = keys.curve_for(plug, layer)
    if curve is None:
        return [BREAKDOWN_LOST % (plug, keys.NO_CURVE)]
    lost = []
    for time in times:
        try:
            cmds.keyframe(curve, edit=True, time=(time, time), breakdown=True)
        except RuntimeError as error:
            lost.append(str(error).strip().splitlines()[0][:80] if str(error).strip() else
                        type(error).__name__)
    return [BREAKDOWN_LOST % (plug, lost[0])] if lost else []


def _value_at(curve, time):
    """The value a stored CURVE has at source frame `time` (a Blend's preview of an objects
    card): its static value, a key's there, else `_inserted`'s key at `time`, else the value it
    holds outside its keys; None for a curve with nothing in it."""
    if not isinstance(curve, dict):
        return None
    if "static" in curve:
        return float(curve["static"])
    stored = [list(key) for key in curve.get("keys") or () if len(key) >= 2]
    if not stored:
        return None
    for key in stored:
        if abs(float(key[0]) - time) <= EPS:
            return float(key[1])
    _inside, need = _clip(stored, time, time)
    if need:
        found = _inserted(stored, bool(curve.get("weighted")), time, time, need)
        if found:
            return float(found[0][1])
    return _held(stored, time)


def _as_pose(header, time=None):
    """An objects animation card as a POSE card: each attribute its value at source frame
    `time` (`_value_at`) - or 0.0 for every one when `time` is None (Select objects reads only
    the plugs)."""
    objects = []
    for record in header.get("objects") or []:
        attrs = OrderedDict()
        for attr, curve in (record.get("attrs") or {}).items():
            value = 0.0 if time is None else _value_at(curve, time)
            if value is not None:
                attrs[attr] = value
        objects.append(dict(record, attrs=attrs))
    return dict(header, objects=objects)


def _press_objects(header, selection=None, alpha=1.0, options=None, progress=None):
    """An objects card's press (the module's "Objects"): (ok, the line)."""
    options = _options(options)
    layer, refusal = keys.active_layer()
    if refusal:
        return False, refusal
    matched, notes, refusal = _objects_pairs(header, selection)
    if refusal:
        return False, refusal
    try:
        plan = _plan(header, options)
    except ValueError as error:
        return False, str(error)
    alpha = ap._clamp(alpha)
    if alpha <= 0.0:
        return False, ap.BLEND_ZERO
    notes = list(notes)
    channels, missing, paths = OrderedDict(), [], []
    for record, path in matched:
        if path not in paths:
            paths.append(path)
        for attr, curve in (record.get("attrs") or {}).items():
            if cmds.attributeQuery(attr, node=path, exists=True):
                channels[path + "." + attr] = curve
            else:
                missing.append("%s.%s" % (scene.leaf(path), attr))
    if missing:
        notes.append(ap.NOT_POSED % (len(missing), "no such attribute", ap._named(missing)))
    note = keys.quaternion_note(layer)
    if note and any(plug.rsplit(".", 1)[-1] in ROTATE for plug in channels):
        return False, note
    lo, hi = plan.frames[0][0], plan.frames[-1][0]
    planned, breakdowns = OrderedDict(), {}
    for plug, curve in channels.items():
        stored, weighted = _object_keys(curve, lo, hi, plan)
        if stored:
            planned[plug] = (stored, weighted)
            breakdowns[plug] = _breakdown_times(curve, lo, hi, plan, stored)
    # Connect and Blend read the take as it stands, BEFORE the paste mode cuts or moves it
    if options.connect:
        for plug, (stored, weighted) in list(planned.items()):
            offset = float(cmds.getAttr(plug, time=plan.a)) - float(stored[0][1])
            planned[plug] = ([[key[0], float(key[1]) + offset] + list(key[2:])
                              for key in stored], weighted)
    if alpha < 1.0:
        for plug, (stored, weighted) in list(planned.items()):
            mixed = []
            for key in stored:
                was = float(cmds.getAttr(plug, time=key[0]))
                mixed.append([key[0], was + (float(key[1]) - was) * alpha] + list(key[2:]))
            planned[plug] = (mixed, weighted)
    nodes, said = set(), OrderedDict()
    cancelled, done = False, []
    if planned:
        recording = bool(cmds.undoInfo(query=True, state=True))
        plugs = list(planned)
        try:
            with _chunk():
                state = keys.curve_state(plugs, layer)
                if layer is None:
                    # keyed with its tangents, a weighted card curve keeps its weights: the
                    # target curve's infinity given back, never its weighting over the card's
                    for plug, saved in state.items():
                        if plug in planned and planned[plug][1]:
                            state[plug] = dict(saved, weighted=True)
                _ops(plan.ops, plugs, layer)
                for plug, (stored, weighted) in planned.items():
                    written = keys.write_keys(plug, stored, layer, weighted,
                                              tangents=layer is None)
                    nodes.update(p.rsplit(".", 1)[0] for p in written.plugs)
                    for text in written.notes:
                        said.setdefault(text, text)
                    if written.plugs and breakdowns.get(plug):
                        for text in _breakdowns(plug, layer, breakdowns[plug]):
                            said.setdefault(text, text)
                    done.append(plug)
                    if progress is not None and not progress.step(
                            STEP % (header.get("name") or "Animation", scene.leaf(plug))):
                        cancelled = True
                        break
                # with undo off a cancel keeps its keys: their curves get their state back too
                if not cancelled or not recording:
                    keys.put_curve_state(state, layer)
        except BaseException:
            _undo_failed(recording)
            raise
        if cancelled:
            if recording:
                cmds.undo()
                return False, CANCELLED
            return False, _kept(ap._counted(len(done), "channels"), plan, "channels")
    if nodes:
        hidden = keys.layer_note(layer)
        if hidden:
            notes.insert(0, hidden)
    row = {"name": header.get("name"), "target": ap._counted(len(paths), "objects"),
           "count": len(nodes), "noun": "objects",
           "layer": layer.name if layer is not None else None, "a": plan.a, "b": plan.b,
           "frames": plan.b - plan.a + 1, "mode": options.mode, "worst": None,
           "worst_frame": None, "notes": notes + list(said.values()), "alpha": alpha,
           "mirror": False}
    return bool(nodes), look.anim_status(row)


# ------------------------------------------------------------------ the presses

def apply(header, frames, selection=None, mirror=False, alpha=1.0, options=None,
          progress=None):
    """(ok, text): the animation card - `header` its `anim.json`, `frames` its decoded
    `frames.json.gz` (the window reads it: `store.read_frames`) - onto every character the
    selection touches (`selection` a list of nodes, Maya's when None; nothing selected: the only
    character), pasted with `options` (`animdata.Options`, a mapping of its fields, or None for
    the defaults), mirrored when asked, `alpha` < 1 mixing each frame with the take as it stood;
    an objects card onto the selection's objects (`apply.pair_objects`). One undo chunk;
    `progress` (a `timewalk.Progress`) steps a frame at a time and Esc undoes the press."""
    if header and header.get("kind") == "objects":
        return _press_objects(header, selection, alpha, options, progress)
    refusal = _card_refusal(header)
    if refusal:
        return False, refusal
    refs, refusal = _targets(selection)              # reads the scene, writes nothing
    if refusal:
        return False, refusal
    return _press_refs(header, frames, refs, mirror, alpha, options, progress)


def apply_onto(header, frames, root, mirror=False, alpha=1.0, options=None, progress=None):
    """(ok, text): the animation onto the character whose skeleton's root (or any node of it) is
    `root` - a card dropped on a character in a viewport. An objects card goes onto objects
    only. One undo chunk."""
    if header and header.get("kind") == "objects":
        return False, ap.OBJECTS_ONTO
    refusal = _card_refusal(header)
    if refusal:
        return False, refusal
    ref = _character_of(root) if root else None
    if ref is None:
        return False, ap.NOT_FOUND % (root or "nothing")
    return _press_refs(header, frames, [ref], mirror, alpha, options, progress)


def drop_floor(header, frames, point, mirror=False, options=None, progress=None):
    """(ok, text): the card's source character added at the floor `point` and the animation
    pasted onto it - the pose's road (`apply.drop_floor`: Add Character or the native rebuild,
    the layer refused before anything is added, the selection put back) with this press made
    onto the new character (`onto`), its travel starting from the point. What the press would
    refuse (no frames, an empty range) is refused BEFORE the character is added: an Add cannot
    be undone (the import flushes the queue, trap 115)."""
    if header and header.get("kind") == "objects":
        return False, ap.OBJECTS_ONTO
    refusal = _card_refusal(header)
    if refusal:
        return False, refusal
    options = _options(options)
    refusal = _checked_plan(header, frames, options)[1]
    if refusal:
        return False, refusal
    return ap.drop_floor(header, point, mirror, onto=lambda root: apply_onto(
        header, frames, root, mirror, 1.0, options, progress))


def select_objects(header, selection=None, options=None):
    """(ok, text): what a press would key, selected - the pose's (`apply.select_objects`: a rig's
    controls, a skeleton's member joints, an objects card's objects) - plus each target's Main
    (a rig) or root joint (a skeleton) when the travel would be carried (`_travels`, `_carry`)."""
    if not header:
        return False, ap.NO_CARD
    if header.get("kind") == "objects":
        return ap.select_objects(_as_pose(header), selection)
    refusal = _card_refusal(header)
    if refusal:
        return False, refusal
    options = _options(options)
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    prefer = (header.get("character") or {}).get("namespace") or None
    refs, refusal = _targets(selection, prefer)
    ok, text = ap.select_objects(header, selection)
    if not ok or refusal or not _travels(header, header.get("members"), options):
        return ok, text
    carried = []
    for ref in refs:
        carries, node, _note = _carry(ref, scene.skeleton(ref)[0], True)
        if carries and node and node not in carried:
            carried.append(node)
    if carried:
        cmds.select(carried, add=True)
        text += CARRIED % ", ".join(scene.leaf(node) for node in carried)
    return ok, text


# ------------------------------------------------------------------ Blend

class Blend(object):
    """A live blend session over an animation card (the window's slider, a middle-drag across a
    card): `start(header, frames, mirror=False, options=None, selection=None)` -> refusal or "";
    `set(alpha)` previews; `finish(progress=None)` -> the line; `cancel()`; `active()`.

    The preview is ONE pose - the clip's frame that falls on the current frame, the first when
    it falls outside the paste range (`_shown`) - as a pose card through the pose's own session
    (`apply.Blend`: solved and shown unrecorded, nothing kept open between two calls). `finish`
    puts that preview back (the inner session's cancel) and pastes the WHOLE range at the
    session's weight onto the selection the session started with (`apply`); at 0 % - or with
    the time moved since `start` - nothing is keyed, as for a pose."""

    def __init__(self):
        self._clear()

    def _clear(self):
        self.inner = None
        self.header = self.frames = self.options = None
        self.mirror = False
        self.selection = None
        self.time = None

    def active(self):
        """Is a session running?"""
        return self.inner is not None and self.inner.active()

    def start(self, header, frames, mirror=False, options=None, selection=None):
        """"" when a session started, else the refusal (nothing changed). A session already
        running is cancelled first."""
        if self.inner is not None:
            self.cancel()
        if not header:
            return ap.NO_CARD
        options = _options(options)
        objects = header.get("kind") == "objects"
        if objects:
            try:
                plan = _plan(header, options)
            except ValueError as error:
                return str(error)
        else:
            refusal = _card_refusal(header)
            if refusal:
                return refusal
            plan, refusal = _checked_plan(header, frames, options)
            if refusal:
                return refusal
        now = float(cmds.currentTime(query=True))
        source, index = _shown(plan, now)
        if objects:
            data = _as_pose(header, source)
        else:
            data = dict(header, bones=animdata.bones_at(header, frames, index))
        if selection is None:
            selection = cmds.ls(selection=True, long=True) or []
        inner = ap.Blend()
        refusal = inner.start(data, mirror, selection)
        if refusal:
            return refusal
        self.inner, self.header, self.frames, self.options = inner, header, frames, options
        self.mirror = bool(mirror) and not objects
        self.selection, self.time = list(selection), now
        return ""

    def set(self, alpha):
        """Preview the pose at `alpha` (0..1) - live, unrecorded."""
        if self.active():
            self.inner.set(alpha)

    def finish(self, progress=None):
        """The preview put back, then the whole range pasted at the session's weight (one
        `UNDO_CHUNK`); the line. The session ends."""
        if not self.active():
            self._clear()
            return ap.NO_BLEND
        inner, header, frames = self.inner, self.header, self.frames
        mirror, options, selection, time = self.mirror, self.options, self.selection, self.time
        alpha = inner.alpha
        inner.cancel()                           # every value back, unrecorded
        self._clear()
        if alpha <= 0.0:
            return ap.BLEND_ZERO
        if abs(float(cmds.currentTime(query=True)) - time) > 1e-9:
            return ap.TIME_MOVED
        return apply(header, frames, selection, mirror, alpha, options, progress)[1]

    def cancel(self):
        """Every value back as it was at `start`; the session ends. Unrecorded."""
        if self.inner is not None:
            self.inner.cancel()
        self._clear()
