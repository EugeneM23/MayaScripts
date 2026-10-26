"""maya_walk.keyrig - a cycle's four key poses on four Manny rigs, edited for the whole cycle (2026-10-26).

The animator: «Мы находим в нашем цикле 4 ключевые позы через которые строится походка или бег, выносим эти позы
каждую на свой риг и изменяя риги контролируем весь наш цикл а умные обработчики нам помогают. Для этой фичи
давай сделаем отдельную кнопку как сейчас для создания одной средней позы».

`press(walk)`: four Manny [rig]s (Add Character, one a key; a second press poses the cycle's own again) in a row
beside the first walker on the cycle, each marked `MARKER` on its Main and stood in its key pose - Contact, Down,
Passing, Up of the cycle's first step of the left foot (maya_walk.keyposes.find), with every edit made so far -
through the Pose Library's solve: plain values, no keys. What a rig shows is read back (maya_walk.meanrig._read)
and kept on its marker as the BASE.

`update(rekey)`: every key rig read again; what changed against its base goes into the cycle's key poses
(keyposes.combine), written beside the walk's file; the rigs that changed are stood again in what the cycle
now does at their key (a move the cycle does not take - a foot planted flat - shows as not taken, and the line
says so), their base what they show; `rekey(walk)` keys the walkers on the cycle again. `reset(walk)`: the
cycle's key poses dropped, its rigs back in the plain key poses. `delete(walk)`: the cycle's key rigs out of the
scene; the edits stay. The design: docs/superpowers/specs/2026-10-26-walk-key-poses-design.md.
"""
import json
import traceback

from . import keyposes as kp
from . import meanrig
from . import scene

MARKER = "skeldarWalkKey"          # on a key rig's Main: {"walk", "clean", "key", "frame", "base": {bone: 16}}
OFFSET = 150.0                     # cm beside the first walker on the cycle (along -X: the mean pose rig is +X)...
GAP = 110.0                        # ...the next key this much further
LABEL = "%s - %s"


class Refusal(scene.Refusal):
    """What the key rigs do not do, and why."""


def _cmds():
    import maya.cmds as cmds
    return cmds


# ---- which rigs ----

def rigs(walk=None):
    """Every key rig in the scene (a maya_rigs.Rig whose Main carries MARKER), of the cycle `walk` when given, in
    the keys' order."""
    import maya_rigs
    cmds = _cmds()
    out = []
    for rig in maya_rigs.rigs():
        if not (rig.main and cmds.objExists(rig.main) and cmds.attributeQuery(MARKER, node=rig.main, exists=True)):
            continue
        if walk is None or memo_of(rig).get("walk") == walk:
            out.append(rig)
    order = dict((k, i) for i, k in enumerate(kp.KEYS))
    return sorted(out, key=lambda r: (memo_of(r).get("walk") or "", order.get(memo_of(r).get("key"), 9)))


def find(walk, key):
    for rig in rigs(walk):
        if memo_of(rig).get("key") == key:
            return rig
    return None


def memo_of(rig):
    cmds = _cmds()
    try:
        return json.loads(cmds.getAttr(rig.main + "." + MARKER) or "{}")
    except (ValueError, RuntimeError):
        return {}


def _set_memo(rig, memo):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=rig.main, exists=True):
        cmds.addAttr(rig.main, longName=MARKER, dataType="string")
    cmds.setAttr(rig.main + "." + MARKER, json.dumps(memo), type="string")


# ---- the presses ----

def _point(walk, i):
    """The `i`th key's place: beside the first walker on the cycle `walk` (else the first walker, else the
    origin), the row going along -X."""
    cmds = _cmds()
    walkers = scene.walkers()
    on = [r for r in walkers if scene.memo_of(r).get("walk") == walk] or walkers
    x, z = 0.0, 0.0
    if on:
        x, _, z = cmds.xform(on[0], query=True, worldSpace=True, translation=True)
    return (x - OFFSET - GAP * i, 0.0, z)


def _add(walk, i):
    import maya_rigs
    from maya_scenesetup import catalog, character
    from maya_uebridge import rigimport
    cmds = _cmds()
    selection = cmds.ls(selection=True, long=True) or []
    before = maya_rigs.rigs()
    text = character.add_character(catalog.default_rig(), at=_point(walk, i))
    rig = rigimport.fresh_rig(before, maya_rigs.rigs())
    if rig is None:
        raise Refusal("no Manny rig was added: %s" % text)
    with scene.Unrecorded():
        kept = [s for s in selection if cmds.objExists(s)]
        if kept:
            cmds.select(kept, replace=True)
    return rig


def _steps(walk):
    steps = getattr(walk, "key_steps", None)
    if not steps:
        raise Refusal("no key poses in this cycle: %s" % (getattr(walk, "key_note", "") or "its steps were not read"))
    return steps


def _frame_worlds(walk, f):
    return dict((name, walk.clip.worlds[j, f]) for j, name in enumerate(walk.names))


def _stand(rig, walk, statics, walk_name, key, frame, clean):
    """The rig stood in the cycle's pose at `frame` (the Pose Library's solve, no keys), its base what it then
    shows. The solve's notes."""
    with scene.Unrecorded():
        _set_memo(rig, {"walk": walk_name, "clean": clean, "key": key, "frame": frame, "base": {}})
    meanrig._state()["bones"] = None
    data = meanrig.card_data(walk, statics, _frame_worlds(walk, frame), walk_name)
    data["name"] = LABEL % (scene.walk_label(walk_name), kp.LABELS[key])
    plan = meanrig._pose(rig, data)
    _legs_ik(rig)
    base = meanrig._read(rig, walk, statics)
    with scene.Unrecorded():
        _set_memo(rig, {"walk": walk_name, "clean": clean, "key": key, "frame": frame,
                        "base": meanrig._flat(base)})
    return [n for n in plan.notes if n]


def _legs_ik(rig):
    """The rig's legs stood in IK (the Pose Library posed both halves alike): lowering the hips leaves the feet
    where they stand and a foot is moved by its own control - with FK legs the hips dragged the swinging foot down
    with them, and that read as a foot moved (2026-10-26)."""
    import maya_rigs
    cmds = _cmds()
    with scene.Unrecorded():
        for side in ("L", "R"):
            plug = maya_rigs.node(rig, "FKIKLeg_%s" % side) + ".FKIKBlend"
            try:
                if cmds.objExists(plug) and cmds.getAttr(plug, settable=True):
                    cmds.setAttr(plug, 10.0)
            except RuntimeError:
                pass


def press(walk_name, clean=None):
    """Create key poses: the cycle `walk_name`'s four key rigs (added, or its own standing) stood in their key
    poses with every edit so far. Returns the status line."""
    clean = dict(scene.wc.knobs(clean))
    walk, statics = scene.load_walk(walk_name, clean)[:2]
    steps = _steps(walk)
    frames = kp.frames_of(steps, walk.P)
    added, posed, notes = [], [], []
    for i, key in enumerate(kp.KEYS):
        rig = find(walk_name, key)
        if rig is None:
            rig = _add(walk_name, i)
            added.append(rig.namespace)
        else:
            posed.append(rig.namespace)
        notes += _stand(rig, walk, statics, walk_name, key, frames[key], clean)
        with scene.Unrecorded():
            try:
                from maya_scenesetup import cliplabel
                cliplabel.label_rig(rig, "%s (frame %d)" % (LABEL % (scene.walk_label(walk_name), kp.LABELS[key]),
                                                             frames[key]))
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
    keys = scene.walk_keys(walk_name)[0]
    what = ", ".join("%s %d" % (kp.LABELS[k], frames[k]) for k in kp.KEYS)
    line = "key poses of %s on %d rigs (%s; %s)" % (scene.walk_label(walk_name), len(kp.KEYS), what,
                                                     kp.summary(keys))
    if added:
        line += " - added %s" % ", ".join(added)
    return line + " - pose their controls, then Update" + (" | " + notes[0] if notes else "")


NO_RIG = "no key poses in the scene - press Create key poses first"
NOTHING_MOVED = "nothing moved on the key poses since the last Update"


def update(rekey=None):
    """Update: every key rig read; each cycle's changes into its key poses (the module docstring), the rigs that
    changed stood again in what the cycle does, `rekey(walk)` answering a tail for the line. Refuses with no key
    rig."""
    standing = rigs()
    if not standing:
        raise Refusal(NO_RIG)
    by_walk = {}
    for rig in standing:
        by_walk.setdefault(memo_of(rig).get("walk"), []).append(rig)
    lines = []
    for name, cycle_rigs in by_walk.items():
        if not name or not scene.walk_exists(name):
            lines.append("key poses of %s: not a saved walk" % (scene.walk_label(name) or "no walk"))
            continue
        clean = memo_of(cycle_rigs[0]).get("clean")
        walk, statics = scene.load_walk(name, clean)[:2]
        try:
            steps = _steps(walk)
        except Refusal as error:
            lines.append("key poses of %s: %s" % (scene.walk_label(name), error))
            continue
        frames = kp.frames_of(steps, walk.P)
        keys, path = scene.walk_keys(name)
        changed, said, ignored = [], [], []
        for rig in cycle_rigs:
            memo = memo_of(rig)
            key = memo.get("key")
            if key not in kp.KEYS:
                continue
            now = meanrig._read(rig, walk, statics)
            base = meanrig._unflat(memo.get("base") or {})
            if not base:
                with scene.Unrecorded():
                    _set_memo(rig, dict(memo, base=meanrig._flat(now)))
                continue
            keys, moved, not_taken = kp.combine(keys, key, kp.measure(base, walk), kp.measure(now, walk), walk,
                                                frames[key])
            ignored += not_taken
            if moved:
                changed.append(rig)
                said.append("%s: %s" % (kp.LABELS[key], kp.describe(moved, 3)))
            elif not_taken:
                changed.append(rig)            # stood again: it shows what the cycle does
        if not changed:
            continue
        kp.save(path, keys)
        walk, statics = scene.load_walk(name, clean)[:2]
        frames = kp.frames_of(_steps(walk), walk.P)
        for rig in changed:
            memo = memo_of(rig)
            _stand(rig, walk, statics, name, memo["key"], frames[memo["key"]], clean)
        line = "key poses of %s: %s" % (scene.walk_label(name), "; ".join(said) if said else "nothing taken")
        if ignored:
            line += " | not taken: " + "; ".join(ignored[:2]) + (" (+%d more)" % (len(ignored) - 2)
                                                                 if len(ignored) > 2 else "")
        lines.append(line + ((rekey or meanrig.rekey_target)(name) if said else ""))
    if not lines:
        return NOTHING_MOVED
    return " | ".join(lines)


def reset(walk_name, clean=None, rekey=None):
    """Reset key poses: the cycle's edits dropped; its key rigs (when standing) back in the plain key poses; its
    walkers keyed again. Returns the status line."""
    keys, path = scene.walk_keys(walk_name)
    had = not kp.is_empty(keys)
    kp.save(path, {})
    label = scene.walk_label(walk_name)
    line = ("%s: the key poses' edits dropped" % label) if had else "%s has no key pose edited" % label
    if rigs(walk_name):
        press(walk_name, clean)
        line += ", the key rigs back in the cycle's key poses"
    return line + ((rekey or meanrig.rekey_target)(walk_name) if had else "")


def delete(walk=None):
    """Delete key poses: the cycle `walk`'s key rigs out of the scene, whole (Animation Setup's Delete, no question
    asked - they are this tool's) - those of the only cycle that has some when `walk` has none; the edits stay.
    Returns the status line."""
    from maya_scenesetup import deletion
    standing = rigs(walk)
    if not standing:
        cycles = sorted(set(memo_of(r).get("walk") for r in rigs()))
        if len(cycles) == 1:
            walk, standing = cycles[0], rigs(cycles[0])
        elif cycles:
            raise Refusal("%s has no key poses - %d other cycles have some (select a walker on one to make its "
                          "cycle the active one)" % (scene.walk_label(walk), len(cycles)))
        else:
            raise Refusal("no key poses in the scene")
    meanrig._state()["bones"] = None
    text = deletion.delete_selected([r.main for r in standing], confirm=lambda _text: True)
    return "key poses of %s deleted (%s) - the walk keeps their edits" % (scene.walk_label(walk), text)
