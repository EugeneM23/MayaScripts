"""maya_walk.keyrig - a walker's four key poses on four Manny rigs, edited for the whole cycle (2026-10-26).

The animator: «Мы находим в нашем цикле 4 ключевые позы через которые строится походка или бег, выносим эти позы
каждую на свой риг и изменяя риги контролируем весь наш цикл а умные обработчики нам помогают. Для этой фичи
давай сделаем отдельную кнопку как сейчас для создания одной средней позы».

Since 2026-10-27 the rigs belong to one WALKER (its UUID on each rig's memo) and stand in that walker's own
animation (scene.walker_animation: the walk with the walker's edits, its parameters, pose and physics, the key
edits on top) at its key frames - the key poses found on the evaluated result (keyposes.on_result). What a rig
shows is what the walker does.

`press(root)`: four Manny [rig]s (Add Character, one a key; a second press poses the walker's own again) in a line
along the walker's travel - Contact first - each marked `MARKER` on its Main and stood in its key pose - Contact,
Down, Passing, Up of the first step of the left foot - through the Pose Library's solve: plain values, no keys. What
a rig shows is read back in its own Main frame as it stood (maya_walk.meanrig._read) and kept as its BASE.

`update(rekey, shift)`: every key rig read again; what changed against its base (keyposes.increment) is split
(keyposes.split_common): the pelvis moved alike on all four keys is a setting of the whole walk - Height, Forward -
given to `shift(root, common)` (the card's parameters when the walker is working, else the walker's own); the rest
goes into the walker's key edits (scene.set_edits); the walker is keyed again (`rekey(root)`), and the rigs stood
again in what it now does. `reset(root)`: the walker's key edits dropped, its rigs back in the plain key poses.
`delete(root)`: the walker's key rigs out of the scene; the edits stay. The design:
docs/superpowers/specs/2026-10-26-walk-key-poses-design.md, docs/superpowers/specs/2026-10-27-walk-builder-working-walkers-design.md.
"""
import json
import traceback

from . import keyposes as kp
from . import meanrig
from . import scene

MARKER = "skeldarWalkKey"          # on a key rig's Main: {"walker", "walk", "key", "frame", "base", "main0", "root0"}
OFFSET = 150.0                     # cm beside the walker (to its right: the mean pose rig is +X)...
GAP = 110.0                        # ...Contact first, each next key this much further along the walk's travel
LABEL = "%s - %s"


class Refusal(scene.Refusal):
    """What the key rigs do not do, and why."""


def _cmds():
    import maya.cmds as cmds
    return cmds


# ---- which rigs ----

def rigs(walker=None):
    """Every key rig in the scene (a maya_rigs.Rig whose Main carries MARKER), the walker `walker`'s (its top joint)
    when given, in the keys' order."""
    import maya_rigs
    cmds = _cmds()
    found = [rig for rig in maya_rigs.rigs()
             if rig.main and cmds.objExists(rig.main) and cmds.attributeQuery(MARKER, node=rig.main, exists=True)]
    if walker is not None:
        want = meanrig.uuid_of(walker)
        found = [rig for rig in found if meanrig.walker_uuid(rig, memo_of, _set_memo) == want]
    order = dict((k, i) for i, k in enumerate(kp.KEYS))
    return sorted(found, key=lambda r: (memo_of(r).get("walker") or "", order.get(memo_of(r).get("key"), 9)))


def find(walker, key):
    for rig in rigs(walker):
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

def line_point(origin, travel, i):
    """The `i`th key's place: OFFSET to the right of `origin` (the walker), then GAP a key along `travel` (a flat
    direction): Contact first and the others after it, one behind another the way the walk goes - not side by
    side (2026-10-27, «не в шеренгу а в линию один за одним начиная с контакта»)."""
    x, z = float(travel[0]), float(travel[2])
    length = (x * x + z * z) ** 0.5
    if length < 1e-6:
        x, z, length = 0.0, 1.0, 1.0
    x, z = x / length, z / length
    right = (-z, x)                    # up x travel, then turned to the walker's right (-X for a walk along +Z)
    return (origin[0] + OFFSET * right[0] + GAP * i * x, 0.0, origin[2] + OFFSET * right[1] + GAP * i * z)


def _travel(top):
    """Where the walker `top` goes: its root's world place at the playback end less its start (flat); +Z for a
    walker in place."""
    cmds = _cmds()
    a = cmds.playbackOptions(query=True, minTime=True)
    b = cmds.playbackOptions(query=True, maxTime=True)
    try:
        p = cmds.getAttr(top + ".worldMatrix[0]", time=a)[12:15]
        q = cmds.getAttr(top + ".worldMatrix[0]", time=b)[12:15]
    except (RuntimeError, ValueError, TypeError):
        return (0.0, 0.0, 1.0)
    d = (q[0] - p[0], 0.0, q[2] - p[2])
    return d if (d[0] * d[0] + d[2] * d[2]) > 1.0 else (0.0, 0.0, 1.0)


def _point(root, i):
    """The `i`th key's place beside the walker `root`, in a line along its travel (line_point)."""
    cmds = _cmds()
    origin, travel = (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    if root and cmds.objExists(root):
        origin = cmds.xform(root, query=True, worldSpace=True, translation=True)
        travel = _travel(root)
    return line_point(origin, travel, i)


def _add(root, i):
    import maya_rigs
    from maya_scenesetup import catalog, character
    from maya_uebridge import rigimport
    cmds = _cmds()
    selection = cmds.ls(selection=True, long=True) or []
    before = maya_rigs.rigs()
    text = character.add_character(catalog.default_rig(), at=_point(root, i))
    rig = rigimport.fresh_rig(before, maya_rigs.rigs())
    if rig is None:
        raise Refusal("no Manny rig was added: %s" % text)
    with scene.Unrecorded():
        kept = [s for s in selection if cmds.objExists(s)]
        if kept:
            cmds.select(kept, replace=True)
    return rig


def _animation(root):
    """The walker's animation with its key poses found on it (scene.walker_animation)."""
    anim = scene.walker_animation(root, with_steps=True)
    if not anim.steps:
        raise Refusal("no key poses in %s's walk: %s" % (scene.walker_label(root),
                                                         anim.layer_note or "its steps were not read"))
    return anim


def _frame_worlds(anim, f):
    worlds = anim.moving
    return dict((name, worlds[j, f]) for j, name in enumerate(anim.walk.names))


def _stand(rig, anim, root, key, frame):
    """The rig stood in the walker's animation at `frame` (the Pose Library's solve, no keys), its base what it
    then shows, read in its own Main frame. The solve's notes."""
    uuid = meanrig.uuid_of(root)
    walk_name = anim.walk_name
    with scene.Unrecorded():
        _set_memo(rig, {"walker": uuid, "walk": walk_name, "key": key, "frame": frame, "base": {}})
    meanrig._state()["bones"] = None
    data = meanrig.card_data(anim.walk, anim.statics, _frame_worlds(anim, frame), walk_name)
    data["name"] = LABEL % (scene.walker_label(root), kp.LABELS[key])
    plan = meanrig._pose(rig, data)
    _legs_ik(rig)
    main0, root0 = meanrig.placement(rig)
    stood = {"walker": uuid, "walk": walk_name, "key": key, "frame": frame, "main0": main0, "root0": root0,
             "poles": _poles(rig)}
    base = meanrig._read(rig, anim.walk, anim.statics, stood)
    with scene.Unrecorded():
        _set_memo(rig, dict(stood, base=meanrig._flat(base)))
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


def _poles(rig):
    """{"l"/"r": {"ik": the leg in IK, "t": its pole control's translate}} as the rig stands."""
    import maya_rigs
    cmds = _cmds()
    out = {}
    for side, s in (("l", "L"), ("r", "R")):
        try:
            ik = float(cmds.getAttr(maya_rigs.node(rig, "FKIKLeg_%s" % s) + ".FKIKBlend")) > 5.0
            t = [float(v) for v in cmds.getAttr(maya_rigs.node(rig, "PoleLeg_%s" % s) + ".translate")[0]]
        except (RuntimeError, ValueError, TypeError):
            ik, t = False, None
        out[side] = {"ik": ik, "t": t}
    return out


def knees_taken(before, now):
    """{"l"/"r": a knee's turn is the animator's} - in IK only when its pole control moved: a pelvis or a foot moved
    turns an IK leg's plane by itself (lowered 10 cm, the rigs read 1.6-2.3 deg knees, 2026-10-27). None (a rig
    stood by a build before): every knee."""
    if not before:
        return None
    out = {}
    for side in ("l", "r"):
        a, b = before.get(side) or {}, now.get(side) or {}
        still = a.get("ik") and b.get("ik") and a.get("t") and b.get("t") and \
            max(abs(x - y) for x, y in zip(a["t"], b["t"])) < 1e-3
        out[side] = not still
    return out


def _label(rig, root, key, frame):
    with scene.Unrecorded():
        try:
            from maya_scenesetup import cliplabel
            cliplabel.label_rig(rig, "%s (frame %d)" % (LABEL % (scene.walker_label(root), kp.LABELS[key]), frame))
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()


def press(root):
    """Create key poses: the walker `root`'s four key rigs (added, or its own standing) stood in its animation's
    key poses. Returns the status line."""
    if not root:
        raise Refusal(meanrig.NO_WALKER)
    anim = _animation(root)
    frames = kp.frames_of(anim.steps, anim.rw.P)
    added, notes = [], []
    for i, key in enumerate(kp.KEYS):
        rig = find(root, key)
        if rig is None:
            rig = _add(root, i)
            added.append(rig.namespace)
        notes += _stand(rig, anim, root, key, frames[key])
        _label(rig, root, key, frames[key])
    what = ", ".join("%s %d" % (kp.LABELS[k], frames[k]) for k in kp.KEYS)
    line = "key poses of %s on %d rigs (%s; %s)" % (scene.walker_label(root), len(kp.KEYS), what,
                                                     kp.summary(anim.edits.get("keys") or {}))
    if added:
        line += " - added %s" % ", ".join(added)
    return line + " - pose their controls, then Update" + (" | " + notes[0] if notes else "")


NO_RIG = "no key poses in the scene - press Create key poses first"
NOTHING_MOVED = "nothing moved on the key poses since the last Update"


def _pelvis_height(anim):
    """The walker's pelvis over the cycle, its mean height (cm along up)."""
    import numpy as np
    j = anim.walk.index["pelvis"]
    return float(np.mean(anim.moving[j, :-1, 3, :3] @ np.asarray(anim.walk.up, float)))


def _height_of(root):
    """The walker's Height (cm, its offset from the clip's own) as it was keyed last, None when unread."""
    try:
        change = scene.memo_params(root, scene.memo_of(root), translate=False)["changes"].get("height")
        return float(change[1]) if change else 0.0
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def common_line(common):
    """«on all four: Height +5.0 cm, Forward -2.0 cm»."""
    parts = ["%s %+.1f cm" % (label, common[what]) for what, label in (("height", "Height"), ("forward", "Forward"))
             if abs(common.get(what, 0.0)) > 1e-9]
    return ("on all four: " + ", ".join(parts)) if parts else ""


def shift_memo(root, common):
    """The walker `root`'s own parameters moved by `common` ({"height", "forward"} cm, each a pinned change):
    update's default `shift` (the card's own when the walker is working: the panel's)."""
    memo = scene.memo_of(root)
    params = scene.shift_params(scene.memo_params(root, memo, translate=False), common)
    memo["params"] = scene.plain_params(params)
    with scene.Unrecorded():
        scene._set_memo(root, memo)
    return ""


def update(rekey=None, shift=None):
    """Update (the card's): every walker's key rigs read; their change since the last Update split - the pelvis alike
    on all four keys to `shift(root, common)` (Height, Forward), the rest into the walker's key edits; the walker
    keyed again (`rekey(root)`, else as it was keyed last, unrecorded), the rigs stood again in what it now does.
    Refuses with no rig."""
    standing = rigs()
    if not standing:
        raise Refusal(NO_RIG)
    by_walker = {}
    for rig in standing:
        by_walker.setdefault(meanrig.walker_uuid(rig, memo_of, _set_memo), []).append(rig)
    lines = []
    for uuid, own in by_walker.items():
        root = meanrig.walker_of(uuid)
        if root is None or not scene.memo_of(root).get("walk"):
            lines.append("key poses %s stand for no walker in the scene - Delete them and Create again"
                         % ", ".join(r.namespace for r in own))
            continue
        try:
            anim = _animation(root)
        except Refusal as error:
            lines.append(str(error))
            continue
        frames = kp.frames_of(anim.steps, anim.rw.P)
        incs = dict((key, kp.empty_key()) for key in kp.KEYS)
        said, ignored, stood_again, older = [], [], [], []
        for rig in own:
            memo = memo_of(rig)
            key = memo.get("key")
            if key not in kp.KEYS:
                continue
            if not memo.get("main0"):
                # stood by a build before 2026-10-27: in the source cycle, read without its Main frame - its base
                # is not what the rig showed (the animator's rigs read 23.5 cm of pelvis nobody moved)
                older.append(rig)
                continue
            now = meanrig._read(rig, anim.walk, anim.statics, memo)
            base = meanrig._unflat(memo.get("base") or {})
            if not base:
                with scene.Unrecorded():
                    _set_memo(rig, dict(memo, base=meanrig._flat(now)))
                continue
            frame = int(memo.get("frame", frames[key]))
            inc, moved, not_taken = kp.increment(key, kp.measure(base, anim.rw), kp.measure(now, anim.rw), anim.rw,
                                                 frame, knees=knees_taken(memo.get("poles"), _poles(rig)))
            ignored += not_taken
            if moved:
                incs[key] = inc
                said.append("%s: %s" % (kp.LABELS[key], kp.describe(moved, 3)))
            if moved or not_taken:
                stood_again.append(rig)
        if older:
            lines.append(_stand_older(older, root, anim if not stood_again else None))
        if not stood_again:
            continue
        incs = kp.one_print(incs)
        common, incs = kp.split_common(incs)
        edits = dict(anim.edits)
        keys = edits.get("keys") or {}
        for key, inc in incs.items():
            if not kp.key_empty(inc):
                keys = kp.add(keys, key, inc)
        edits["keys"] = keys
        scene.set_edits(root, edits)
        whole = common_line(common)
        height_before = _pelvis_height(anim)
        if whole:
            (shift or shift_memo)(root, common)
            stood_again = own                      # the whole walk changed: every key does
        tail = (rekey or meanrig.rekey_root)(root) if (said or whole) else ""
        anim = _animation(root)
        asked = common.get("height", 0.0)
        if abs(asked) > 1e-9:
            rose = _pelvis_height(anim) - height_before
            if abs(rose) < 0.8 * abs(asked):
                height = _height_of(root)
                total = "" if height is None or abs(height - asked) < 0.05 else "Height now %+.1f cm, " % height
                whole += " (%sthe walk moves %+.1f cm%s)" % (
                    total, rose, " - its legs reach no further, a shorter Step raises it more" if asked > 0.0 else "")
        frames = kp.frames_of(anim.steps, anim.rw.P)
        for rig in list(stood_again) + [r for r in older if r not in stood_again]:
            key = memo_of(rig)["key"]
            if key not in frames:
                continue        # a rig of no key the walk has (an old memo): left alone, as the reading leaves it
            _stand(rig, anim, root, key, frames[key])
            _label(rig, root, key, frames[key])
        line = "key poses of %s: %s" % (scene.walker_label(root), "; ".join(said) if said else "nothing taken")
        if whole:
            line += " | " + whole
        if ignored:
            line += " | not taken: " + "; ".join(ignored[:2]) + (" (+%d more)" % (len(ignored) - 2)
                                                                 if len(ignored) > 2 else "")
        lines.append(line + tail)
    if not lines:
        return NOTHING_MOVED
    return " | ".join(lines)


def _stand_older(older, root, anim):
    """The rigs `older` (stood by a build before 2026-10-27) stood again in the walker's animation `anim` (None: the
    caller stands them after its own Update). Their line."""
    if anim is not None:
        frames = kp.frames_of(anim.steps, anim.rw.P)
        for rig in older:
            key = memo_of(rig)["key"]
            _stand(rig, anim, root, key, frames[key])
            _label(rig, root, key, frames[key])
    return ("%s stood by an older build: stood again in %s's animation, nothing read - pose them again, then "
            "Update" % (", ".join(r.namespace for r in older), scene.walker_label(root)))


def reset(root, rekey=None):
    """Reset key poses: the walker's key edits dropped; its key rigs (when standing) back in the plain key poses;
    the walker keyed again. Returns the status line."""
    if not root:
        raise Refusal(meanrig.NO_WALKER)
    memo = scene.memo_of(root)
    edits = scene.walker_edits(root, memo.get("walk"))[0]
    had = not kp.is_empty(edits.get("keys"))
    edits["keys"] = kp.empty()
    scene.set_edits(root, edits)
    label = scene.walker_label(root)
    line = ("%s: the key poses' edits dropped" % label) if had else "%s has no key pose edited" % label
    tail = (rekey or meanrig.rekey_root)(root) if had else ""
    if rigs(root):
        press(root)
        line += ", the key rigs back in its key poses"
    return line + tail


def delete(root=None):
    """Delete key poses: the walker `root`'s key rigs out of the scene, whole (Animation Setup's Delete, no
    question asked - they are this tool's) - those of the only walker that has some when `root` has none; the
    edits stay. Returns the status line."""
    from maya_scenesetup import deletion
    standing = rigs(root) if root else []
    if not standing:
        owners = sorted(set(meanrig.walker_uuid(r, memo_of, _set_memo) for r in rigs()))
        if len(owners) == 1:
            root, standing = meanrig.walker_of(owners[0]), [r for r in rigs()]
        elif owners:
            raise Refusal("%s has no key poses - %d other walkers have some (click one in the list)"
                          % (scene.walker_label(root) if root else "the working walker", len(owners)))
        else:
            raise Refusal("no key poses in the scene")
    meanrig._state()["bones"] = None
    text = deletion.delete_selected([r.main for r in standing], confirm=lambda _text: True)
    return "key poses of %s deleted (%s) - the walker keeps their edits" % (
        scene.walker_label(root) if root else "-", text)
