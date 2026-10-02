"""The Pose Library's Apply (2026-10-02): a card onto the selection, onto a character it was dropped
on, onto a new character on the floor; Blend, Mirror, Select objects.

The animator: «Выделив наши объекты мы можем применить на них карточку ... мне не обязательно
выделять именно сохраненные элементы достаточно выделить любую часть скелета или рига нажать apply
... перетягивать наши карточки на персонажа драгом мышки ... Поза должна накладываться на текущий
активный анимационный слой. Если мы перетягиваем карточку в пустую сцену ... загрузит исходный риг
или скелет и выставит позу».

## A press (`apply`, `apply_onto`, `drop_floor`)

1. **who**: every character the selection touches (`scene.characters`: any part of it); nothing
   selected -> the only character in the scene, else a refusal naming them (`choose_targets`); a
   selection of nothing that is a character is refused rather than redirected - the animator
   pointed at something;
2. **which layer** (`keys.active_layer`): a locked layer, or an additive layer accumulating
   rotation as quaternions (`keys.quaternion_note` - a character pose always turns bones), is
   refused HERE, before anything is read or written;
3. **the plan** per target (`_plan`, the road `verify_poselib_solve.py` proved on every shipped
   character): `bones = scene.skeleton(ref)` (a rig's unrolled limb bones in their drive),
   `source = data["bones"]` and its members (both reflected by `posemath.mirror` when mirrored),
   `pairs`, `scale_between`, `targets(use_drive = the target is a rig)`, the target members =
   the target leaves paired with a source member; then `rigsolve.solve` / `skelsolve.solve` - the
   FINAL channel values, the scene left as found. A source member nothing pairs with is named
   («no hand_l on Creep_Rig»); twist bones are not (the target's own twist bones ride its limb);
4. **the keys** (`keys.write`) on the current frame, the layer and `value=` final, `alpha` < 1
   mixing the current values and the pose's first (`mix`);
5. the frame re-evaluated (`currentTime(t, update=True)`) and **measured** - `rigsolve.measure`
   on a rig, every member joint's world against its target on a skeleton - the worst in the
   status line (`summary`).

Steps 3-5 are ONE undo chunk (`UNDO_CHUNK`, `_press`), autoKey off inside it and put back:
`rigsolve.solve`'s own chunk nests in it, so one Ctrl+Z takes the whole press back - the keys,
the solve's net-nothing round trip, the autoKey toggles - and the next Ctrl+Z what the animator
did before. Measured (`verify_poselib_apply.py` `undo`): every channel of the rig back exactly,
keyed and static ones alike (an undone `setKeyframe` on a static channel puts its value back).

**Main and a skeleton's root are never written** - the character stays where it stands and faces
(the animator's answer); the pelvis comes relative to the root.

## Onto the floor (`drop_floor`)

The card's catalog row (`character.key`) is added at the point (`add_character(entry, at=)`, the
new rig or root found by a diff - `rigimport.fresh_rig`, `character.new_root`), the animator's
selection put back (Add selects the rig's Main), and the pose applied onto it as its own press.
`file -import` flushes Maya's undo queue (trap 115), so only the pose is undoable: one Ctrl+Z
takes the pose keys and leaves the character. A card with no row of ours (a native skeleton, the
Auto card's own) is REBUILT, bones only, from its rests (`rebuild_joints`, `formats.build`, in the
namespace `pose_<name>`) - with one hidden cube skinned to it at that rest (`REST_PROXY`): an
unskinned joint's rest reads as its current world (`maya_retargetmode.rest_world`), so without it
the next card applied onto the posed rebuild, or a pose saved from it, would take the first pose
for the bind. The rebuild is unrecorded too, as an Add is.

## Blend (`Blend`, and `apply(alpha=)`)

`mix` blends per channel: translations and scalars lerped, each node's rotate triple slerped as a
quaternion the short way and written as the euler NEAREST the current one (no flip on the next
key, trap 108). A slider or a middle-drag previews live (`keys.preview`, a plain `setAttr` that
holds until the next time change) and keys on release; Esc puts every value back.

A session is NOT one long undo chunk: the solve at `start` and every preview run with undo
recording OFF (`_unrecorded`: `undoInfo -stateWithoutFlush false`, outside any chunk - trap 145
breaks a chunk it is toggled inside), autoKey off around each write; `cancel` puts every value
back the same way - so a cancel leaves NO undo step at all (a chunk held open from start to
cancel would leave a step that changes nothing, and would fold whatever else the animator did
during the drag into it). `finish` puts the values back unrecorded first, then keys the mix in
one `UNDO_CHUNK` - so its Ctrl+Z finds every static channel at its value from before the session,
not at the preview's.

## Objects (`apply_objects`)

Studio Library's attribute pose: the stored values onto the selected objects matched by name
with the namespace ignored, else onto the stored objects found in the scene (by path, else by a
leaf name only one transform carries), else by selection order when the counts match
(`pair_objects`, the spec's order).

## Select objects (`select_objects`)

What a press would key: on a rig `rigsolve.controls_for` the target members, on a skeleton the
member joints, an objects pose its objects. The character is the selection's, else the only one,
else the one in the card's own namespace.

Proof: docs/superpowers/plans/verify_poselib_apply.py, mayapy standalone, 51/51 (2026-10-03),
the bones measured against the card after a real time change: a full card onto a second
Manny_Rig standing at (300, 0, -120) turned 70 deg, Main unmoved, every member on the card
relative to the root 0.0007 deg; a mirrored right arm onto the left 0.0002 deg on each parent;
a blend at 0.5 halfway to 0.000000 deg on all 69 controls (`set` 0.013 s for 242 channels);
the hand card onto the Manny skeleton and onto Creep_Rig moving the hand's channels only; a
Mixamo card onto Manny_Rig pointing 0.0074 deg; keys only on the selected additive / override
layer, every base curve key for key, the pose on the card 0.0001 deg, a locked layer refused
with nothing changed; one Ctrl+Z after a press putting all 1408 channels and every curve back
exactly; a Creep_Rig card dropped on an empty floor standing its Main on the point (0.000000
cm) and its bones on the pose (0.00006 deg), the selection kept, one Ctrl+Z taking the pose
keys only. Each family fails on the code it guards against (no chunk, plain keys under a layer,
a session held in one chunk, eulers lerped, the neck not held - task 7's mutation runs).

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Apply - where, and how", "Keys
- the active layer", "Blend", "The window").
"""

import contextlib
import math
from collections import OrderedDict, namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_rigs
from maya_poselib import keys
from maya_poselib import posemath as pm
from maya_poselib import rigsolve
from maya_poselib import scene
from maya_poselib import skelsolve

__all__ = ["Plan", "Result", "plan_for", "apply", "apply_onto", "drop_floor", "apply_objects",
           "select_objects", "mix", "Blend", "summary"]

# ref: the CharacterRef (None for an objects pose); values: {plug: FINAL value}; current: {plug:
# what it shows now}; notes: [str]; skipped: {leaf or plug: why} (the solver's)
Plan = namedtuple("Plan", "ref values current notes skipped")
# one target's line of the status (`summary`)
Result = namedtuple("Result", "name target count noun layer frame worst notes alpha mirror")
# what the measure after the keys needs: the targets, the target members, the target's bones;
# `label` names an objects pose's target (a character's comes from its ref)
Extra = namedtuple("Extra", "wanted members bones label")

UNDO_CHUNK = "skeldarPoseApply"
NATIVE_PREFIX = "pose_"             # the namespace a native card's skeleton is rebuilt in
REST_PROXY = "restBind"             # the hidden cube skinned to it, so its rest stays its bind
REST_MARK = "skeldarPoseRest"       # ... marked so
ROTATE = ("rotateX", "rotateY", "rotateZ")
ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")
NAMED = 4
SHOW_CM = 0.0005                    # a worst place smaller than this is not said

NO_CARD = "no pose card"
NO_BONES = "the card holds no bones"
NO_OBJECTS = "the card holds no objects"
NO_CHARACTER = "no character in the scene to apply a pose to"
NOT_A_CHARACTER = "the selection holds no character - select any part of one"
MANY = "%d characters in the scene (%s) - select any part of the one you mean"
NOT_FOUND = "no character at %s"
OBJECTS_MISSING = "none of the pose's %d object%s is selected or in the scene"
OBJECTS_ONTO = "an objects pose goes onto objects - select them and Apply"
NO_SOURCE = "the card names no character of ours and holds no bones - nothing to add"
NOT_ADDED = "%s was not added: %s"
ADDED = "a new %s %s at floor (%d, %d)"
REBUILT = "%s rebuilt (bones only) at floor (%d, %d)"
UNPAIRED = "no %s on %s"
NOT_POSED = "%d not posed (%s): %s"
BY_ORDER = "matched by selection order"
NO_BLEND = "no blend to finish"
BLEND_ZERO = "Blend at 0 % - nothing keyed"
TIME_MOVED = "the time changed during the blend - every value put back, nothing keyed"
NOTHING = "nothing to key: %s"
SELECTED = "Selected %d %s on %s"

# the rig's twist (and helper) bones are DRIVEN by its own network from the limbs the pose turns
# (rigsolve.DRIVEN): saying so on every full pose onto a rig is no news to the animator
_QUIET = rigsolve.DRIVEN.split("%d", 1)[1].split("%s", 1)[0]


# ------------------------------------------------------------------ pure

def _clamp(alpha):
    return max(0.0, min(1.0, float(alpha)))


def _euler(values, order):
    return om.MEulerRotation(*([math.radians(v) for v in values] + [int(order)]))


def mix(current, final, alpha, rotations):
    """{plug: value} between `current` (alpha 0) and `final` (alpha 1), for every plug of `final`,
    in its order.

    Translations and scalars are lerped. Each node of `rotations` ({node: (plugX, plugY, plugZ,
    rotate order 0..5)}) whose three plugs `final` holds is slerped as a quaternion the short way
    and written as the euler in its rotate order NEAREST its current one (`closestSolution`: a
    wound 730 stays wound). Alpha is clamped to 0..1, and the two ends are the values exactly. A
    plug `current` lacks starts at its final value. Pure (OpenMaya)."""
    alpha = _clamp(alpha)
    current = current or {}
    if alpha >= 1.0:
        return OrderedDict((plug, final[plug]) for plug in final)
    start = OrderedDict((plug, current.get(plug, final[plug])) for plug in final)
    if alpha <= 0.0:
        return start
    out = OrderedDict()
    turned = {}
    for node, spec in (rotations or {}).items():
        plugs, order = spec[:3], spec[3]
        if not all(p in final for p in plugs):
            continue
        q0 = _euler([start[p] for p in plugs], order).asQuaternion()
        q1 = _euler([final[p] for p in plugs], order).asQuaternion()
        if q0.x * q1.x + q0.y * q1.y + q0.z * q1.z + q0.w * q1.w < 0.0:
            q1 = om.MQuaternion(-q1.x, -q1.y, -q1.z, -q1.w)
        euler = om.MQuaternion.slerp(q0, q1, alpha).asEulerRotation().reorder(int(order))
        euler = euler.closestSolution(_euler([start[p] for p in plugs], order))
        for plug, value in zip(plugs, (euler.x, euler.y, euler.z)):
            turned[plug] = math.degrees(value)
    for plug in final:
        if plug in turned:
            out[plug] = turned[plug]
        else:
            out[plug] = start[plug] + (final[plug] - start[plug]) * alpha
    return out


def _num(value, places=3):
    """A number as the status line prints it: at most `places` decimals, no trailing zeros,
    never «-0»."""
    text = ("%.*f" % (places, float(value))).rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _counted(count, noun):
    """«23 controls», «1 control» (`noun` in the plural)."""
    if count == 1 and noun.endswith("s"):
        noun = noun[:-1]
    return "%d %s" % (count, noun)


def _named(items):
    items = list(items)
    shown = ", ".join(items[:NAMED])
    if len(items) > NAMED:
        shown += " and %d more" % (len(items) - NAMED)
    return shown


def _line(result):
    head = result.name or "Pose"
    if result.mirror:
        head += " mirrored"
    if result.alpha is not None and result.alpha < 1.0:
        head += " at %s %%" % _num(result.alpha * 100.0, 1)
    text = "%s onto %s: " % (head, result.target)
    if result.count:
        text += "%s keyed" % _counted(result.count, result.noun)
        if result.layer:
            text += " on " + result.layer
        text += " at frame " + _num(result.frame)
        if result.worst is not None:
            deg, cm = result.worst[0], result.worst[1]
            text += " - worst %s deg" % _num(deg)
            if cm >= SHOW_CM:
                text += " / %s cm" % _num(cm)
    else:
        text += "nothing keyed"
    for note in result.notes or ():
        text += " | " + note
    return text


def summary(results):
    """The status line of a press: one line per target (`Result`), joined with « | ».

    «Fist onto Manny_Rig1: 23 controls keyed on AnimLayer1 at frame 12 - worst 0.003 deg | the FK
    forearm twist is lost on arm_r (31 deg)» - the layer only when the scene has layers, the worst
    place only when it is worth a word, «mirrored» / «at 50 %» when so. Pure."""
    return " | ".join(_line(result) for result in results)


def shown_notes(notes):
    """The notes worth the status line: all but the rig saying its twist and helper bones are
    driven - they ride the limbs the pose turns, by the rig's own network. Pure."""
    return [note for note in notes or () if _QUIET not in note]


def target_label(ref):
    """How the status line names a character: a rig by its namespace (`Manny_Rig1`), a skeleton
    as the save panel does («Manny UE5 [skeleton] (root)»). Pure."""
    if ref.kind == "rig" and ref.namespace:
        return ref.namespace
    return scene.describe([ref], [])


def choose_targets(refs, selected, every, prefer=None):
    """(the characters a press acts on, refusal). `refs` are the selection's characters,
    `selected` whether anything at all is selected, `every` every character in the scene.

    The selection's characters when it names any; a selection of nothing that is a character is
    refused («select any part of one»), never redirected; nothing selected -> the only character,
    else the one whose namespace is `prefer` (Select objects: the card's own) when exactly one is,
    else a refusal naming them all. Pure."""
    if refs:
        return list(refs), ""
    if selected:
        return [], NOT_A_CHARACTER
    every = list(every or ())
    if len(every) == 1:
        return every, ""
    if not every:
        return [], NO_CHARACTER
    if prefer:
        preferred = [ref for ref in every if ref.namespace == prefer]
        if len(preferred) == 1:
            return preferred, ""
    return [], MANY % (len(every), ", ".join(target_label(ref) for ref in every))


def target_members(bones, pairs, members):
    """The target leaves (in the target skeleton's order) whose partner is a source member."""
    wanted = set(members or ())
    return [leaf for leaf in bones if pairs.get(leaf) in wanted]


def unpaired(members, pairs, source=None):
    """The source members no target bone plays, in their order - twist bones aside (the target's
    own twist bones ride its limb, a twist the target lacks is nothing lost) and, given the
    `source` bones, every bone with no name of its own: its canonical name, else - on a UE-named
    card - its leaf. Mixamo's finger end joints and HeadTop_End carry none, nothing can pair
    them, and «no LeftHandIndex4 ... and 7 more» said nothing on every Mixamo card. Pure."""
    taken = set(pairs.values())
    ue = source is not None and pm.ue_named(source)

    def named(m):
        if source is None:
            return True
        return bool((source.get(m) or {}).get("canonical") or ue)
    return [m for m in members or () if m not in taken and not pm.is_twist(m) and named(m)]


def unpaired_note(names, label):
    """«no hand_l on Creep_Rig», or "" when nothing is missing. Pure."""
    return UNPAIRED % (_named(names), label) if names else ""


def pair_objects(objects, selected, found):
    """([(stored record, scene path)], how) for an objects pose - the spec's order:

    - `name`: every selected path whose leaf, namespace dropped, is a stored object's name (two
      selected copies of one object both take it);
    - `stored`: else the stored objects found in the scene (`found`: {index: path or None});
    - `order`: else the selection by order, when as many are selected as the card holds;
    - else ([], ""). Pure."""
    by_name = []
    for record in objects:
        for path in selected or ():
            if scene.leaf(path) == record.get("name"):
                by_name.append((record, path))
    if by_name:
        return by_name, "name"
    stored = [(record, found[i]) for i, record in enumerate(objects) if (found or {}).get(i)]
    if stored:
        return stored, "stored"
    if selected and len(selected) == len(objects):
        return list(zip(objects, selected)), "order"
    return [], ""


def _depth(bones, leaf):
    depth, node, seen = 0, bones[leaf].get("parent"), set()
    while node in bones and node not in seen:
        seen.add(node)
        depth += 1
        node = bones[node].get("parent")
    return depth


def rebuild_joints(bones):
    """`formats.build`'s joints for a card's skeleton at its REST, parents first: each `name`
    (made legal for Maya, `formats.legal`), `parent` (an index), `t` / `q` its rest local
    translation and rotation (`rest . rest[parent]^-1`, rigid; the rotation becomes the
    jointOrient, so rotate reads 0 at rest) and `order` its rotate order's name."""
    from maya_uebridge import formats
    order = sorted(bones, key=lambda leaf: (_depth(bones, leaf), leaf))
    index, out = {}, []
    for leaf in order:
        bone = bones[leaf]
        parent = bone.get("parent")
        rest = pm.rigid(bone["rest"])
        if parent in bones:
            local = rest * pm.rigid(bones[parent]["rest"]).inverse()
            parent_index = index[parent]
        else:
            local, parent_index = rest, None
        t = pm.position(local)
        q = om.MTransformationMatrix(local).rotation(asQuaternion=True)
        out.append({"name": formats.legal(leaf), "parent": parent_index, "t": (t.x, t.y, t.z),
                    "q": (q.x, q.y, q.z, q.w),
                    "order": ORDERS[int(bone.get("rotateOrder") or 0) % 6]})
        index[leaf] = len(out) - 1
    return out


def _skipped_note(skipped):
    """One note per reason for the solver's skipped bones or plugs."""
    by_reason = OrderedDict()
    for name, why in (skipped or {}).items():
        by_reason.setdefault(why, []).append(name.split("|")[-1])
    return [NOT_POSED % (len(names), why, _named(names)) for why, names in by_reason.items()]


# ------------------------------------------------------------------ scene state

@contextlib.contextmanager
def _press():
    """The block as ONE undo chunk (`UNDO_CHUNK`), autoKey off inside it and put back - closed
    whatever happens. A solve's own chunk nests in it, so one Ctrl+Z is the whole press."""
    cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK)
    auto = cmds.autoKeyframe(query=True, state=True)
    try:
        cmds.autoKeyframe(state=False)
        yield
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)


@contextlib.contextmanager
def _unrecorded():
    """Undo recording off for the block, without the flush `undoInfo(state=False)` does, and back
    as it was after (`maya_scenesetup.character._unrecorded`'s rule). Only ever outside a chunk:
    toggled inside one it breaks that chunk (trap 145)."""
    was = bool(cmds.undoInfo(query=True, state=True))
    if was:
        cmds.undoInfo(stateWithoutFlush=False)
    try:
        yield
    finally:
        if was:
            cmds.undoInfo(stateWithoutFlush=True)


@contextlib.contextmanager
def _auto_off():
    """autoKey off for the block (a scripted `setAttr` KEYS under autoKey) and back."""
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        yield
    finally:
        cmds.autoKeyframe(state=auto)


def _refresh():
    try:
        cmds.refresh(currentView=True)
    except RuntimeError:
        pass


def _frame():
    return float(cmds.currentTime(query=True))


def rotations_of(values):
    """{node: (plugX, plugY, plugZ, rotate order)} for every node whose three rotate plugs
    `values` holds, spelled as `values` spells them - `mix`'s `rotations`."""
    attrs = OrderedDict()
    for plug in values:
        node, attr = plug.rsplit(".", 1)
        if attr in ROTATE:
            attrs.setdefault(node, set()).add(attr)
    out = {}
    for node, found in attrs.items():
        if len(found) != 3:
            continue
        try:
            order = int(cmds.getAttr(node + ".rotateOrder"))
        except (RuntimeError, ValueError):
            continue
        out[node] = tuple(node + "." + attr for attr in ROTATE) + (order,)
    return out


def _has_rotate(values):
    return any(plug.rsplit(".", 1)[-1] in ROTATE for plug in values)


def _selected(selection):
    """The selected DAG transforms, long paths, each once (Maya's selection when None)."""
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    out = []
    for item in selection:
        path = scene.dag_object(item)
        if path is not None and path not in out:
            out.append(path)
    return out


def _targets(selection, prefer=None):
    """(the characters a press acts on, refusal) - `choose_targets` on the scene."""
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    refs, _loose = scene.characters(selection)
    every = [] if (refs or selection) else scene.all_characters()
    return choose_targets(refs, bool(selection), every, prefer)


# ------------------------------------------------------------------ the plan

def _plan(data, ref, mirror=False):
    """(Plan, Extra) for one target - the module's step 3. Writes nothing."""
    notes = []
    bones, _convention = scene.skeleton(ref, notes)
    source = data.get("bones") or {}
    members = list(data.get("members") or ())
    if mirror:
        source, members = pm.mirror(source, members)
    pairs = pm.pairs(source, bones)
    scale = pm.scale_between(source, bones, pairs)
    wanted = pm.targets(source, bones, pairs, members, use_drive=(ref.kind == "rig"),
                        scale=scale)
    members_t = target_members(bones, pairs, members)
    missing = unpaired_note(unpaired(members, pairs, source), target_label(ref))
    if missing:
        notes.append(missing)
    if ref.kind == "rig":
        solution = rigsolve.solve(ref.rig, wanted, members_t)
    else:
        solution = skelsolve.solve(ref, bones, wanted, members_t)
    values = OrderedDict(solution.values)
    plan = Plan(ref, values, keys.current(values), notes + list(solution.notes),
                dict(solution.skipped))
    return plan, Extra(wanted, members_t, bones, None)


def plan_for(data, ref, mirror=False):
    """The Plan of `data` onto the character `ref` (`scene.CharacterRef`): every channel value
    the press would key, what those channels show now, the notes, what the solver skipped. The
    scene is left exactly as found (a rig's solve is one net-nothing undo step of its own)."""
    return _plan(data, ref, mirror)[0]


def _measure(plan, extra):
    """(worst deg, worst cm, its leaf) of the target's members as the scene now stands, or None:
    on a rig `rigsolve.measure` (the unrolled limb bones by where they point, the pelvis's place),
    on a skeleton every member joint's world against its target (the root and the skipped
    aside)."""
    ref = plan.ref
    if ref is None or extra is None or not extra.members:
        return None
    if ref.kind == "rig":
        return rigsolve.measure(ref.rig, extra.wanted, extra.members)
    root = skelsolve.root_leaf(ref, extra.bones)
    worst = (0.0, 0.0, None)
    for leaf in extra.members:
        if leaf == root or leaf in plan.skipped or leaf not in extra.wanted:
            continue
        path = extra.bones.get(leaf, {}).get("path")
        if not path or not cmds.objExists(path):
            continue
        now = om.MMatrix(cmds.getAttr(path + ".worldMatrix[0]"))
        want = pm.matrix(extra.wanted[leaf])
        deg = pm.angle(now, want)
        cm = (pm.position(now) - pm.position(want)).length()
        worst = (max(worst[0], deg), max(worst[1], cm),
                 leaf if deg >= worst[0] else worst[2])
    return worst


def _noun(ref):
    if ref is None:
        return "objects"
    return "controls" if ref.kind == "rig" else "joints"


def _key_entries(entries, name, frame, layer, alpha=1.0, mirror=False):
    """[Result] after keying every entry's values (mixed at `alpha`) on `frame` / `layer`, the
    frame re-evaluated and measured (alpha 1 only: a blend lands where it was asked, between).
    Runs inside the caller's `_press`."""
    keyed = []
    for plan, extra in entries:
        values = plan.values if alpha >= 1.0 else \
            mix(plan.current, plan.values, alpha, rotations_of(plan.values))
        count, notes = keys.write(values, frame, layer) if values else (0, [])
        keyed.append((plan, extra, values, count, notes))
    if any(count for _p, _e, _v, count, _n in keyed):
        cmds.currentTime(frame, update=True)
    results = []
    for plan, extra, values, count, notes in keyed:
        worst = _measure(plan, extra) if count and alpha >= 1.0 else None
        nodes = len(set(plug.rsplit(".", 1)[0] for plug in values)) if count else 0
        label = target_label(plan.ref) if plan.ref is not None else extra.label
        results.append(Result(name, label, nodes, _noun(plan.ref),
                              layer.name if layer is not None else None, frame,
                              worst[:2] if worst else None,
                              shown_notes(list(plan.notes) + _skipped_note(plan.skipped) + notes),
                              alpha, mirror))
    return results


def _apply_refs(data, refs, mirror=False, alpha=1.0):
    """The press onto `refs` - the module's steps 2-5."""
    layer, refusal = keys.active_layer()
    if refusal:
        return False, refusal
    note = keys.quaternion_note(layer)
    if note:
        return False, note                  # a character pose always turns its bones
    frame = _frame()
    with _press():
        entries = [_plan(data, ref, mirror) for ref in refs]
        results = _key_entries(entries, data.get("name"), frame, layer, alpha, mirror)
    return any(r.count for r in results), summary(results)


def _card_refusal(data):
    if not data:
        return NO_CARD
    if not data.get("bones"):
        return NO_BONES
    return ""


# ------------------------------------------------------------------ the presses

def apply(data, selection=None, mirror=False, alpha=1.0):
    """(ok, text): the card `data` (a pose dict) onto every character the selection touches -
    `selection` a list of nodes, Maya's when None - keyed on the active layer at the current
    frame, mirrored when asked, `alpha` < 1 blending from the current values. An objects pose goes
    to `apply_objects`. One undo chunk."""
    if data and data.get("kind") == "objects":
        return apply_objects(data, selection, alpha)
    refusal = _card_refusal(data)
    if refusal:
        return False, refusal
    refs, refusal = _targets(selection)          # reads the scene, writes nothing
    if refusal:
        return False, refusal
    return _apply_refs(data, refs, mirror, alpha)


def apply_onto(data, root, mirror=False):
    """(ok, text): the card onto the character whose game skeleton's root (or any node of it)
    is `root` - a card dropped on a character in a viewport. One undo chunk."""
    if data and data.get("kind") == "objects":
        return False, OBJECTS_ONTO
    refusal = _card_refusal(data)
    if refusal:
        return False, refusal
    ref = scene.character_of(root) if root else None
    if ref is None:
        return False, NOT_FOUND % (root or "nothing")
    return _apply_refs(data, [ref], mirror)


def _reselect(selection):
    """The animator's selection back, unrecorded (Add left the new rig's Main selected)."""
    with _unrecorded():
        kept = []
        for item in selection or ():
            try:
                if cmds.objExists(item):
                    kept.append(item)
            except RuntimeError:
                continue
        if kept:
            cmds.select(kept, replace=True, noExpand=True)
        else:
            cmds.select(clear=True)


def _add(entry, point):
    """(the new character's root, the line) after Add Character of `entry` at `point`."""
    from maya_overrig import builder
    from maya_scenesetup import catalog, character
    from maya_uebridge import rigimport
    x, _y, z = character.placement(point)
    if catalog.is_rig(entry):
        before = maya_rigs.rigs()
        text = character.add_character(entry, at=point)
        rig = rigimport.fresh_rig(before, maya_rigs.rigs())
        if rig is None or not rig.skeleton_root:
            return None, NOT_ADDED % (entry.label, text)
        return rig.skeleton_root, ADDED % (entry.label, rig.namespace, x, z)
    before = builder.character_roots()
    text = character.add_character(entry, at=point)
    root = character.new_root(before, builder.character_roots())
    if root is None:
        return None, NOT_ADDED % (entry.label, text)
    return root, ADDED % (entry.label, scene.leaf(root), x, z)


def _rebuild(data, point):
    """(root, line): the card's skeleton rebuilt at its rest, bones only, in `pose_<name>`, with
    a hidden cube skinned to it at that rest (`REST_PROXY` - its bind is its rest from then on),
    moved onto the floor point. Unrecorded, as an Add is."""
    from maya_scenesetup import character
    from maya_uebridge import formats
    joints = rebuild_joints(data["bones"])
    namespace = character.free_namespace(
        NATIVE_PREFIX + formats.legal(data.get("name") or "Pose").replace(":", "_"),
        character.existing_namespaces())
    x, _y, z = character.placement(point)
    with _unrecorded():
        formats.build(namespace, joints, [None] * len(joints), [], set_timeline=False)
        paths = dict((scene.leaf(p), p) for p in
                     cmds.ls(namespace + ":*", type="joint", long=True) or [])
        built = [paths[j["name"]] for j in joints if j["name"] in paths]
        if not built:
            return None, NOT_ADDED % (data.get("name") or "the pose's skeleton", "no joint built")
        root_uuid = cmds.ls(built[0], uuid=True)[0]
        proxy = cmds.polyCube(name=namespace + ":" + REST_PROXY, constructionHistory=False)[0]
        cmds.skinCluster(built + [proxy], toSelectedBones=True, name=namespace + ":restSkin")
        cmds.addAttr(proxy, longName=REST_MARK, attributeType="bool", defaultValue=True)
        cmds.setAttr(proxy + ".visibility", False)
        root = cmds.ls(root_uuid, long=True)[0]
        cmds.move(x, 0.0, z, root, relative=True, worldSpace=True)
        root = cmds.ls(root_uuid, long=True)[0]
    return root, REBUILT % (namespace, x, z)


def drop_floor(data, point, mirror=False):
    """(ok, text): the card's source character added at the floor `point` (x, y, z) and the pose
    applied onto it. Its catalog row (`character.key`) through Add Character, else - a native
    skeleton - rebuilt bones only from the card; a card with neither is refused. The animator's
    selection is put back; the pose is its own undo step (the import flushed the queue)."""
    if data and data.get("kind") == "objects":
        return False, OBJECTS_ONTO
    if not data:
        return False, NO_CARD
    from maya_scenesetup import catalog
    key = (data.get("character") or {}).get("key")
    entry = catalog.character_by_key(key) if key else None
    if entry is None and not data.get("bones"):
        return False, NO_SOURCE
    if not data.get("bones"):
        return False, NO_BONES
    layer, refusal = keys.active_layer()          # refused before anything is added
    if refusal or keys.quaternion_note(layer):
        return False, refusal or keys.quaternion_note(layer)
    selection = cmds.ls(selection=True, long=True) or []
    root, line = _add(entry, point) if entry is not None else _rebuild(data, point)
    if root is None:
        return False, line
    _reselect(selection)
    ok, text = apply_onto(data, root, mirror)
    return ok, line + " | " + text


# ------------------------------------------------------------------ objects

def _find_object(record):
    """A stored object in the scene: its path, else the one transform carrying its leaf name in
    any namespace; None when there is none or several."""
    path = record.get("path")
    if path:
        found = cmds.ls(path, long=True) or []
        if len(found) == 1:
            return found[0]
    name = record.get("name")
    if not name:
        return None
    found = cmds.ls(name, recursive=True, long=True, type="transform") or []
    return found[0] if len(found) == 1 else None


def _objects_entry(data, selection):
    """((Plan, Extra), refusal) for an objects pose against the selection (`pair_objects`)."""
    objects = (data or {}).get("objects") or []
    if not objects:
        return None, NO_OBJECTS
    selected = _selected(selection)
    found = dict((i, _find_object(record)) for i, record in enumerate(objects))
    matched, how = pair_objects(objects, selected, found)
    if not matched:
        return None, OBJECTS_MISSING % (len(objects), "" if len(objects) == 1 else "s")
    values, missing = OrderedDict(), []
    for record, path in matched:
        for attr, value in (record.get("attrs") or {}).items():
            if cmds.attributeQuery(attr, node=path, exists=True):
                values[path + "." + attr] = float(value)
            else:
                missing.append("%s.%s" % (scene.leaf(path), attr))
    notes = [BY_ORDER] if how == "order" else []
    if missing:
        notes.append(NOT_POSED % (len(missing), "no such attribute", _named(missing)))
    nodes = len(set(path for _record, path in matched))
    label = _counted(nodes, "objects")
    plan = Plan(None, values, keys.current(values), notes, {})
    return (plan, Extra(None, None, None, label)), ""


def apply_objects(data, selection=None, alpha=1.0):
    """(ok, text): an objects pose's stored attribute values onto the objects `pair_objects`
    finds, keyed on the active layer at the current frame (blended from the current values at
    `alpha` < 1). One undo chunk."""
    layer, refusal = keys.active_layer()
    if refusal:
        return False, refusal
    entry, refusal = _objects_entry(data, selection)
    if refusal:
        return False, refusal
    note = keys.quaternion_note(layer)
    if note and _has_rotate(entry[0].values):
        return False, note
    frame = _frame()
    with _press():
        results = _key_entries([entry], data.get("name"), frame, layer, alpha)
    return any(r.count for r in results), summary(results)


# ------------------------------------------------------------------ select objects

def select_objects(data, selection=None):
    """(ok, text): what a press would key, selected - on a rig its controls
    (`rigsolve.controls_for`), on a skeleton the member joints, for an objects pose its objects.
    The character is the selection's, else the only one, else the card's own namespace's."""
    if not data:
        return False, NO_CARD
    if data.get("kind") == "objects":
        entry, refusal = _objects_entry(data, selection)
        if refusal:
            return False, refusal
        nodes = []
        for plug in entry[0].values:
            node = plug.rsplit(".", 1)[0]
            if node not in nodes:
                nodes.append(node)
        if not nodes:
            return False, "nothing of the pose on %s" % entry[1].label
        cmds.select(nodes, replace=True)
        return True, SELECTED % (len(nodes), "objects" if len(nodes) != 1 else "object",
                                 entry[1].label)
    refusal = _card_refusal(data)
    if refusal:
        return False, refusal
    prefer = (data.get("character") or {}).get("namespace") or None
    refs, refusal = _targets(selection, prefer)
    if refusal:
        return False, refusal
    nodes, labels = [], []
    for ref in refs:
        bones, _convention = scene.skeleton(ref)
        pairs = pm.pairs(data["bones"], bones)
        members_t = target_members(bones, pairs, data.get("members"))
        if ref.kind == "rig":
            found = rigsolve.controls_for(ref.rig, members_t)
        else:
            root = skelsolve.root_leaf(ref, bones)
            found = [bones[leaf]["path"] for leaf in members_t if leaf != root]
        nodes.extend(n for n in found if n not in nodes)
        labels.append(target_label(ref))
    if not nodes:
        return False, "nothing of the pose on %s" % ", ".join(labels)
    cmds.select(nodes, replace=True)
    noun = "controls" if all(r.kind == "rig" for r in refs) else \
        "joints" if all(r.kind != "rig" for r in refs) else "nodes"
    return True, SELECTED % (len(nodes), noun if len(nodes) != 1 else noun[:-1],
                             ", ".join(labels))


# ------------------------------------------------------------------ Blend

class Blend(object):
    """A live blend session (the window's slider, a middle-drag across a card): `start` plans
    every target once, `set(alpha)` previews, `finish` keys the last alpha in one undo chunk,
    `cancel` puts every value back. Nothing of a session but `finish` is recorded on the undo
    queue (the module docstring), and nothing stays open between two calls."""

    def __init__(self):
        self._clear()

    def _clear(self):
        self.entries = []
        self.data = None
        self.mirror = False
        self.alpha = 0.0
        self.frame = None
        self.layer = None
        self.rotations = {}

    def active(self):
        """Is a session running?"""
        return bool(self.entries)

    def start(self, data, mirror=False, selection=None):
        """"" when a session started, else the refusal (nothing changed). A session already
        running is cancelled first."""
        if self.active():
            self.cancel()
        if not data:
            return NO_CARD
        layer, refusal = keys.active_layer()
        if refusal:
            return refusal
        objects = data.get("kind") == "objects"
        if objects:
            with _unrecorded():
                entry, refusal = _objects_entry(data, selection)
            if refusal:
                return refusal
            if keys.quaternion_note(layer) and _has_rotate(entry[0].values):
                return keys.quaternion_note(layer)
            entries = [entry]
        else:
            refusal = _card_refusal(data) or keys.quaternion_note(layer)
            if refusal:
                return refusal
            refs, refusal = _targets(selection)
            if refusal:
                return refusal
            with _unrecorded():
                entries = [_plan(data, ref, mirror) for ref in refs]
        if not any(plan.values for plan, _extra in entries):
            notes = [n for plan, _e in entries for n in shown_notes(plan.notes)]
            return NOTHING % ("; ".join(notes) or "no channel the pose can turn")
        values = OrderedDict()
        for plan, _extra in entries:
            values.update(plan.values)
        self.entries = entries
        self.data, self.mirror, self.layer = data, bool(mirror) and not objects, layer
        self.alpha = 0.0
        self.frame = _frame()
        self.rotations = rotations_of(values)
        return ""

    def _show(self, alpha):
        with _unrecorded(), _auto_off():
            for plan, _extra in self.entries:
                if alpha is None:
                    keys.preview(plan.current)
                else:
                    keys.preview(mix(plan.current, plan.values, alpha, self.rotations))
        _refresh()

    def set(self, alpha):
        """Preview the mix at `alpha` (0..1, clamped) - live `setAttr`, unrecorded."""
        if not self.active():
            return
        self.alpha = _clamp(alpha)
        self._show(self.alpha)

    def finish(self):
        """Key the last alpha (one `UNDO_CHUNK`) and end the session; the status line. At 0 %,
        or with the time moved since `start`, every value is put back and nothing keyed."""
        if not self.active():
            return NO_BLEND
        if self.alpha <= 0.0:
            self.cancel()
            return BLEND_ZERO
        if abs(_frame() - self.frame) > 1e-9:
            self.cancel()
            return TIME_MOVED
        self._show(None)             # the values from before the session, so a Ctrl+Z finds them
        entries, data, alpha, mirror, layer = (self.entries, self.data, self.alpha, self.mirror,
                                               self.layer)
        self._clear()
        with _press():
            results = _key_entries(entries, data.get("name"), _frame(), layer, alpha, mirror)
        return summary(results)

    def cancel(self):
        """Every value back as it was at `start`; the session ends. Unrecorded."""
        if self.active():
            self._show(None)
        self._clear()
