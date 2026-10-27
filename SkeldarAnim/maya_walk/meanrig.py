"""maya_walk.meanrig - the walk's mean pose on a Manny rig, edited for the whole cycle (2026-10-15).

The animator: «кнопочку которая рядом с нашей походкой будет создавать manny rig на котором будет наша средняя
поза и меняя анимацию на этом риге мы будем менять нашу позу для всего цикла».

`press(walk)`: a Manny [rig] added (Add Character; one a cycle since 2026-10-16 - a second press poses that
cycle's rig again) 150 cm beside the first walker on the cycle, marked `MARKER` on its Main, and stood in the walk's mean pose with its
correction (maya_walk.meanpose.mean_pose) through the Pose Library's solve - its controls hold plain values, no
keys. What the rig shows is read back (`_read`: its game skeleton carried onto the walk's skeleton the way a pose
is, maya_walk.pose._onto) and kept on the marker as the BASE.

`update()` - the card's Update: the rig read again; what changed against the base (meanpose.combine) moves its
WALKER's correction (scene.set_edits - since 2026-10-27 a rig belongs to one walker and its edits are that walker's,
the library's walk is never written); the walker is keyed again UNRECORDED (Ctrl+Z is the rig's: undo there, Update
again); the base becomes what the rig shows. Nothing changed: nothing written. `delete()`: the rig out of the scene
(Animation Setup's Delete); the walker keeps its correction. A rig is read in its own Main frame as it stood (`_read`:
Main or Root_ctrl moved is no pose change - the live rigs read a 23.5 cm pelvis move off a root nobody posed).

A press, not a watch (the same day: «изменения применялись по нажатию кнопки сейчас не удобно ждать по 2 секунды
после каждого поворота контрола»): the first build re-keyed the target a pause after every control let go; `stop()`
only takes down a watch an older build left in the session.
The design: docs/superpowers/specs/2026-10-15-walk-mean-pose-rig-design.md.
"""
import json
import sys
import traceback

import numpy as np

from . import meanpose as mp
from . import pose as wp
from . import scene
from . import target as wt

MARKER = "skeldarWalkMean"         # on the rig's Main: {"walker": its UUID, "walk", "clean", "base": {bone: 16},
                                   # "main0", "root0": Main's and the game root's worlds as it stood}
OFFSET = 150.0                     # cm beside its walker (along X)
LABEL = "%s - mean pose"


class Refusal(scene.Refusal):
    """What the mean pose rig does not do, and why."""


def _cmds():
    import maya.cmds as cmds
    return cmds


def _state():
    state = getattr(sys, "_skeldar_walk_mean", None)
    if state is None:
        state = {"callbacks": [], "jobs": [], "timer": None, "bones": None, "busy": False}
        sys._skeldar_walk_mean = state
    return state


# ---- which rig ----

def rigs(walker=None):
    """Every mean pose rig in the scene (a maya_rigs.Rig whose Main carries MARKER) - those of the walker `walker`
    (its top joint) when given. A rig from before the walkers owned rigs belongs to the first working walker on its
    walk, else the first walker on it (adopted once)."""
    import maya_rigs
    cmds = _cmds()
    found = [rig for rig in maya_rigs.rigs()
             if rig.main and cmds.objExists(rig.main) and cmds.attributeQuery(MARKER, node=rig.main, exists=True)]
    if walker is None:
        return found
    want = uuid_of(walker)
    return [rig for rig in found if walker_uuid(rig, memo_of, _set_memo) == want]


def find(walker=None):
    """The mean pose rig of the walker `walker` (any one without it), or None."""
    standing = rigs(walker)
    return standing[0] if standing else None


def uuid_of(root):
    cmds = _cmds()
    found = cmds.ls(root, uuid=True) if root else None
    return found[0] if found else ""


def walker_of(uuid):
    """The walker (top joint, long path) a UUID names, or None."""
    cmds = _cmds()
    found = cmds.ls(uuid, long=True) if uuid else None
    return found[0] if found else None


def walker_uuid(rig, read, write):
    """The UUID of the walker a rig belongs to (its memo's "walker"); a rig from before that names none takes the
    first working walker on its walk, else the first walker on it, and keeps it."""
    memo = read(rig)
    if memo.get("walker"):
        return memo["walker"]
    walk = memo.get("walk")
    on = [r for r in scene.working() if scene.memo_of(r).get("walk") == walk] or \
        [r for r in scene.walkers() if scene.memo_of(r).get("walk") == walk]
    if not on:
        return ""
    uuid = uuid_of(on[0])
    with scene.Unrecorded():
        write(rig, dict(memo, walker=uuid))
    return uuid


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


# ---- the rig as data ----

def _ref(rig):
    from maya_poselib import scene as pscene
    ref = pscene.rig_ref(rig)
    if ref is None:
        raise Refusal("%s drives no game skeleton" % rig.namespace)
    return ref


def _bones(rig, ref):
    """The rig's game skeleton (the Pose Library's reading), its static half read once a rig."""
    from maya_poselib import scene as pscene
    state = _state()
    cached = state.get("bones")
    if cached is None or cached[0] != rig.main:
        bones = pscene.skeleton(ref)[0]
        state["bones"] = (rig.main, bones)
        return bones
    return pscene.refresh_world(ref, cached[1])


def placement(rig):
    """(Main's world, the game root's world), 16 floats each, as the rig stands - kept on its memo when it is stood:
    `_read` holds the rig there."""
    import maya_rigs
    cmds = _cmds()
    main = [float(v) for v in cmds.xform(rig.main, query=True, worldSpace=True, matrix=True)]
    ref = _ref(rig)
    bones = _bones(rig, ref)
    top = [leaf for leaf, bone in bones.items() if not bone.get("parent")]
    root = [float(v) for v in np.asarray(bones[top[0]]["world"], float).reshape(16)] if top else None
    return main, root


def _held(rig, bones, memo):
    """`bones` (the Pose Library's reading of the rig's game skeleton) put back in the rig's Main frame as it
    stood (`memo` "main0") and the game root where it stood ("root0"): Main or Root_ctrl moved by hand is no pose
    change."""
    main0, root0 = (memo or {}).get("main0"), (memo or {}).get("root0")
    if not main0:
        return bones
    cmds = _cmds()
    now = np.array(cmds.xform(rig.main, query=True, worldSpace=True, matrix=True), float).reshape(4, 4)
    D = np.linalg.inv(now) @ np.array(main0, float).reshape(4, 4)
    out = {}
    for leaf, bone in bones.items():
        bone = dict(bone)
        for field in ("world", "drive"):
            if bone.get(field):
                bone[field] = [float(v) for v in (np.asarray(bone[field], float).reshape(4, 4) @ D).reshape(16)]
        out[leaf] = bone
    if root0:
        top = [leaf for leaf, bone in out.items() if not bone.get("parent")]
        if top:
            out[top[0]]["world"] = [float(v) for v in root0]
            if out[top[0]].get("drive"):
                out[top[0]]["drive"] = [float(v) for v in root0]
    return out


def _read(rig, walk, statics, memo=None):
    """{bone of the walk's skeleton: 4x4 world} - the rig's game skeleton as it stands carried onto the walk's
    skeleton (as a pose is: pose._onto). The four limb bones a side are read in their DRIVE: AdvancedSkeleton's
    shoulder, elbow, hip and knee never roll - the roll lives in the twist joints - and the drive puts it back on
    the bone, where the walk keeps it (read bare, a rolled arm came back 8-14 deg off)."""
    bones = {}
    for leaf, bone in _held(rig, _bones(rig, _ref(rig)), memo).items():
        bone = dict(bone)
        if bone.get("drive"):
            bone["world"] = bone["drive"]
        bones[leaf] = bone
    out = wp._onto(walk.names, walk.clip.worlds[:, 0], statics, bones, wt)[0]
    return dict((name, wp._np(out[name])) for name in walk.names if name in out)


def _flat(worlds):
    return dict((n, [float(v) for v in np.asarray(m, float).reshape(16)]) for n, m in worlds.items())


def _unflat(flat):
    return dict((n, np.array(v, float).reshape(4, 4)) for n, v in flat.items())


def card_data(walk, statics, worlds, name):
    """The mean pose as a Pose Library card: the walk's bones with their rests, standing in `worlds`."""
    from maya_poselib import posemath as pm
    bones = {}
    for leaf in walk.names:
        if leaf not in statics or leaf not in worlds:
            continue
        b = statics[leaf]
        bones[leaf] = {"parent": b.get("parent"), "canonical": b.get("canonical"), "rest": list(b["rest"]),
                       "world": [float(v) for v in np.asarray(worlds[leaf], float).reshape(16)]}
    members = [leaf for leaf in bones if not pm.is_helper(leaf)]
    return {"name": LABEL % name, "bones": bones, "members": members}


def _controls(rig):
    cmds = _cmds()
    found = cmds.sets(rig.control_set, query=True) or []
    return [p for p in (cmds.ls(found, long=True) or []) if cmds.objectType(p, isAType="transform")]


def _pose(rig, data):
    """The rig's controls set to the card `data` (the Pose Library's solve), no keys: their time curves go, the
    values are set - unrecorded, autoKey off."""
    from maya_poselib import apply as papply
    cmds = _cmds()
    plan = papply.plan_for(data, _ref(rig))
    auto = cmds.autoKeyframe(query=True, state=True)
    with scene.Unrecorded():
        cmds.autoKeyframe(state=False)
        try:
            curves = set()
            for control in _controls(rig):
                for curve in cmds.listConnections(control, source=True, destination=False,
                                                  type="animCurve") or []:
                    if cmds.nodeType(curve) in ("animCurveTL", "animCurveTA", "animCurveTU", "animCurveTT"):
                        curves.add(curve)
            if curves:
                cmds.delete(sorted(curves))
            for plug, value in plan.values.items():
                try:
                    cmds.setAttr(plug, value)
                except RuntimeError:
                    pass
        finally:
            cmds.autoKeyframe(state=auto)
    return plan


# ---- the presses ----

def _point(root):
    """Beside the walker `root`, else at the origin."""
    cmds = _cmds()
    if not root or not cmds.objExists(root):
        return (0.0, 0.0, 0.0)
    x, _, z = cmds.xform(root, query=True, worldSpace=True, translation=True)
    return (x + OFFSET, 0.0, z)


def _add(root):
    import maya_rigs
    from maya_scenesetup import catalog, character
    from maya_uebridge import rigimport
    cmds = _cmds()
    selection = cmds.ls(selection=True, long=True) or []
    before = maya_rigs.rigs()
    text = character.add_character(catalog.default_rig(), at=_point(root))
    rig = rigimport.fresh_rig(before, maya_rigs.rigs())
    if rig is None:
        raise Refusal("no Manny rig was added: %s" % text)
    with scene.Unrecorded():
        kept = [s for s in selection if cmds.objExists(s)]
        if kept:
            cmds.select(kept, replace=True)
    return rig


def _walker(root):
    if not root:
        raise Refusal(NO_WALKER)
    memo = scene.memo_of(root)
    if not memo.get("walk"):
        raise Refusal("%s walks nothing of this tool - Pick puts a walk on it" % scene.walker_label(root))
    return memo


NO_WALKER = "no working walker - press Pick on a skeleton, or click one in the list"


def press(root, clean=None):
    """Create rig pose: the walker `root`'s mean pose rig (added, or its own standing) stood in its mean pose with
    its correction. Every walker has a rig of its own. Returns the status line."""
    stop()
    memo = _walker(root)
    anim = scene.walker_animation(root, with_steps=False)
    walk, statics = anim.walk, anim.statics
    fix = anim.edits.get("fix") or mp.empty()
    worlds = mp.mean_pose(walk, fix)
    rig = find(root)
    added = rig is None
    if added:
        rig = _add(root)
    uuid = uuid_of(root)
    with scene.Unrecorded():
        _set_memo(rig, {"walker": uuid, "walk": memo["walk"], "clean": dict(scene.wc.knobs(clean)), "base": {}})
    _state()["bones"] = None
    plan = _pose(rig, card_data(walk, statics, worlds, memo["walk"]))
    main0, root0 = placement(rig)
    stood = {"walker": uuid, "walk": memo["walk"], "clean": dict(scene.wc.knobs(clean)), "main0": main0,
             "root0": root0}
    base = _read(rig, walk, statics, stood)
    with scene.Unrecorded():
        _set_memo(rig, dict(stood, base=_flat(base)))
        try:
            from maya_scenesetup import cliplabel
            cliplabel.label_rig(rig, LABEL % scene.walker_label(root))
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
    line = "%s %s in the mean pose of %s (%s)" % ("added" if added else "posed", rig.namespace,
                                                  scene.walker_label(root), mp.summary(fix))
    notes = [n for n in plan.notes if n]
    return line + " - pose its controls, then Update" + (" | " + notes[0] if notes else "")


NO_RIG = "no rig pose in the scene - press Create first"
NOTHING_MOVED = "nothing moved on the rig pose since the last Update"


def update(rekey=None):
    """Update: every mean pose rig read; each one's change goes into its walker's correction (the module
    docstring), and `rekey(root)` - the card's: that walker keyed again, unrecorded - answers a tail for the
    line. Refuses with no rig."""
    stop()                           # an older build's watch, left in the session by an update, goes now
    standing = rigs()
    if not standing:
        raise Refusal(NO_RIG)
    lines = []
    for rig in standing:
        root = walker_of(walker_uuid(rig, memo_of, _set_memo))
        memo = memo_of(rig)
        if root is None or not scene.memo_of(root).get("walk"):
            lines.append("%s stands for no walker in the scene - Delete it and Create again" % rig.namespace)
            continue
        anim = scene.walker_animation(root, with_steps=False)
        now = _read(rig, anim.walk, anim.statics, memo)
        base = _unflat(memo.get("base") or {})
        if not base:
            with scene.Unrecorded():
                _set_memo(rig, dict(memo, base=_flat(now)))
            continue
        edits = dict(anim.edits)
        new, moved = mp.combine(edits.get("fix") or mp.empty(), mp.measure(base, anim.walk),
                                mp.measure(now, anim.walk))
        if not moved:
            continue
        edits["fix"] = new
        scene.set_edits(root, edits)
        with scene.Unrecorded():
            _set_memo(rig, dict(memo, base=_flat(now)))
        line = "mean pose of %s: %s" % (scene.walker_label(root), mp.describe(moved))
        lines.append(line + ((rekey or rekey_root)(root)))
    if not lines:
        return NOTHING_MOVED
    return " | ".join(lines)


def rekey_root(root):
    """The walker `root` keyed again, unrecorded, as it was keyed last (its own memo): « -> ...»."""
    memo = scene.memo_of(root)
    scene.apply(root, memo["walk"], memo.get("knobs"), memo.get("pose") or None,
                tuple(memo.get("parts", scene.ALL_PARTS)), record=False,
                pose_card=memo.get("pose_card") or None,
                params=scene.memo_params(root, memo, translate=False))
    return " -> %s keyed again" % scene.walker_label(root)


def reset(root, clean=None, rekey=None):
    """Reset: the walker's mean pose correction dropped; its rig (when standing) back in the plain mean pose; the
    walker keyed again (`rekey(root)`, the card's; else as it was keyed last). Returns the status line."""
    memo = _walker(root)
    edits = scene.walker_edits(root, memo["walk"])[0]
    had = not mp.is_empty(edits.get("fix") or mp.empty())
    edits["fix"] = mp.empty()
    scene.set_edits(root, edits)
    label = scene.walker_label(root)
    line = ("%s: the mean pose correction dropped" % label) if had else "%s has no correction" % label
    if find(root) is not None:
        press(root, clean)
        line += ", the rig pose back in the mean pose"
    return line + (rekey or rekey_root)(root)


def delete(root=None):
    """Delete rig pose: the walker `root`'s rig out of the scene, whole (Animation Setup's Delete, no question
    asked - it is this tool's) - the only one standing when that walker has none; the walker keeps its correction.
    Returns the status line."""
    from maya_scenesetup import deletion
    rig = find(root) if root else None
    if rig is None:
        standing = rigs()
        if len(standing) == 1:
            rig = standing[0]
        elif standing:
            raise Refusal("%s has no rig pose - %d others stand (click the walker that owns one in the list)"
                          % (scene.walker_label(root) if root else "the working walker", len(standing)))
        else:
            raise Refusal("no rig pose in the scene")
    owner = walker_of(memo_of(rig).get("walker"))
    stop()
    _state()["bones"] = None
    text = deletion.delete_selected([rig.main], confirm=lambda _text: True)
    return "rig pose of %s deleted (%s) - the walker keeps its correction" % (
        scene.walker_label(owner) if owner else "-", text)


def stop():
    """Takes down a watch an older build left in the session (its callbacks, jobs and timer on `sys`)."""
    state = _state()
    try:
        import maya.api.OpenMaya as om
        for cid in state.get("callbacks") or []:
            try:
                om.MMessage.removeCallback(cid)
            except RuntimeError:
                pass
    except ImportError:
        pass
    state["callbacks"] = []
    cmds = _cmds()
    for job in state.get("jobs") or []:
        try:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        except Exception:                                    # noqa: BLE001
            pass
    state["jobs"] = []
    timer = state.get("timer")
    if timer is not None:
        try:
            timer.stop()
        except RuntimeError:
            pass
        state["timer"] = None
