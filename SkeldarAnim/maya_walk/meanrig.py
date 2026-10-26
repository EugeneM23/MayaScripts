"""maya_walk.meanrig - the walk's mean pose on a Manny rig, edited for the whole cycle (2026-10-15).

The animator: «кнопочку которая рядом с нашей походкой будет создавать manny rig на котором будет наша средняя
поза и меняя анимацию на этом риге мы будем менять нашу позу для всего цикла».

`press(walk)`: a Manny [rig] added (Add Character; one a cycle since 2026-10-16 - a second press poses that
cycle's rig again) 150 cm beside the first walker on the cycle, marked `MARKER` on its Main, and stood in the walk's mean pose with its
correction (maya_walk.meanpose.mean_pose) through the Pose Library's solve - its controls hold plain values, no
keys. What the rig shows is read back (`_read`: its game skeleton carried onto the walk's skeleton the way a pose
is, maya_walk.pose._onto) and kept on the marker as the BASE.

`update()` - the card's Update: the rig read again; what changed against the base (meanpose.combine) moves the walk's
correction, written beside the walk's file; every walker on the cycle (scene.walkers) is keyed again UNRECORDED
(Ctrl+Z is the rig's: undo there, Update again); the base becomes what the rig shows. Nothing changed: nothing
written. `delete()`: the rig out of the scene (Animation Setup's Delete); the walk's correction stays.

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

MARKER = "skeldarWalkMean"         # on the rig's Main: {"walk", "clean", "base": {bone: 16 floats}}
OFFSET = 150.0                     # cm beside the first walker on the cycle (along X)
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

def rigs():
    """Every mean pose rig in the scene (a maya_rigs.Rig whose Main carries MARKER) - one a cycle."""
    import maya_rigs
    cmds = _cmds()
    return [rig for rig in maya_rigs.rigs()
            if rig.main and cmds.objExists(rig.main) and cmds.attributeQuery(MARKER, node=rig.main, exists=True)]


def find(walk=None):
    """The mean pose rig of the cycle `walk` (any one without `walk`), or None."""
    for rig in rigs():
        if walk is None or memo_of(rig).get("walk") == walk:
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


def _read(rig, walk, statics):
    """{bone of the walk's skeleton: 4x4 world} - the rig's game skeleton as it stands carried onto the walk's
    skeleton (as a pose is: pose._onto). The four limb bones a side are read in their DRIVE: AdvancedSkeleton's
    shoulder, elbow, hip and knee never roll - the roll lives in the twist joints - and the drive puts it back on
    the bone, where the walk keeps it (read bare, a rolled arm came back 8-14 deg off)."""
    bones = {}
    for leaf, bone in _bones(rig, _ref(rig)).items():
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

def _point(walk=None):
    """Beside the first walker on the cycle `walk`, else the first walker, else at the origin."""
    cmds = _cmds()
    walkers = scene.walkers()
    on = [r for r in walkers if scene.memo_of(r).get("walk") == walk] or walkers
    if not on:
        return (0.0, 0.0, 0.0)
    x, _, z = cmds.xform(on[0], query=True, worldSpace=True, translation=True)
    return (x + OFFSET, 0.0, z)


def _add(walk=None):
    import maya_rigs
    from maya_scenesetup import catalog, character
    from maya_uebridge import rigimport
    cmds = _cmds()
    selection = cmds.ls(selection=True, long=True) or []
    before = maya_rigs.rigs()
    text = character.add_character(catalog.default_rig(), at=_point(walk))
    rig = rigimport.fresh_rig(before, maya_rigs.rigs())
    if rig is None:
        raise Refusal("no Manny rig was added: %s" % text)
    with scene.Unrecorded():
        kept = [s for s in selection if cmds.objExists(s)]
        if kept:
            cmds.select(kept, replace=True)
    return rig


def press(walk_name, clean=None):
    """Create rig pose: the cycle `walk_name`'s mean pose rig (added, or its own standing) stood in its mean pose
    with its correction. Every cycle has a rig of its own. Returns the status line."""
    stop()
    clean = dict(scene.wc.knobs(clean))
    walk, statics = scene.load_walk(walk_name, clean)[:2]
    fix = scene.walk_fix(walk_name)[0]
    worlds = mp.mean_pose(walk, fix)
    rig = find(walk_name)
    added = rig is None
    if added:
        rig = _add(walk_name)
    with scene.Unrecorded():
        _set_memo(rig, {"walk": walk_name, "clean": clean, "base": {}})
    _state()["bones"] = None
    plan = _pose(rig, card_data(walk, statics, worlds, walk_name))
    base = _read(rig, walk, statics)
    with scene.Unrecorded():
        _set_memo(rig, {"walk": walk_name, "clean": clean, "base": _flat(base)})
        try:
            from maya_scenesetup import cliplabel
            cliplabel.label_rig(rig, LABEL % scene.walk_label(walk_name))
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
    line = "%s %s in the mean pose of %s (%s)" % ("added" if added else "posed", rig.namespace,
                                                  scene.walk_label(walk_name),
                                                  mp.summary(fix))
    notes = [n for n in plan.notes if n]
    return line + " - pose its controls, then Update" + (" | " + notes[0] if notes else "")


NO_RIG = "no rig pose in the scene - press Create first"
NOTHING_MOVED = "nothing moved on the rig pose since the last Update"


def update(rekey=None):
    """Update: every mean pose rig read; each one's change goes into its own cycle's correction (the module
    docstring), and `rekey(walk)` - the card's: the walkers on that cycle keyed again, unrecorded - answers a
    tail for the line. Refuses with no rig."""
    stop()                           # an older build's watch, left in the session by an update, goes now
    standing = rigs()
    if not standing:
        raise Refusal(NO_RIG)
    lines, untouched = [], []
    for rig in standing:
        memo = memo_of(rig)
        name = memo.get("walk")
        if not name or not scene.walk_exists(name):
            lines.append("%s stands for %s, which is not a saved walk"
                         % (rig.namespace, scene.walk_label(name) or "no walk"))
            continue
        walk, statics = scene.load_walk(name, memo.get("clean"))[:2]
        fix, path = scene.walk_fix(name)
        now = _read(rig, walk, statics)
        base = _unflat(memo.get("base") or {})
        if not base:
            with scene.Unrecorded():
                _set_memo(rig, dict(memo, base=_flat(now)))
            untouched.append(name)
            continue
        new, moved = mp.combine(fix, mp.measure(base, walk), mp.measure(now, walk))
        if not moved:
            untouched.append(name)
            continue
        mp.save(path, new)
        with scene.Unrecorded():
            _set_memo(rig, dict(memo, base=_flat(now)))
        line = "mean pose of %s: %s" % (scene.walk_label(name), mp.describe(moved))
        lines.append(line + ((rekey or rekey_target)(name)))
    if not lines:
        return NOTHING_MOVED
    return " | ".join(lines)


def rekey_target(name):
    """Every walker on the cycle `name` keyed again, unrecorded, as it was keyed last (its own memo): « -> ...»."""
    roots = [r for r in scene.walkers() if scene.memo_of(r).get("walk") == name]
    if not roots:
        return " (no walker on it - Pick puts it on skeletons)"
    for root in roots:
        memo = scene.memo_of(root)
        scene.apply(root, name, memo.get("knobs"), memo.get("pose") or None,
                    tuple(memo.get("parts", scene.ALL_PARTS)), record=False,
                    pose_card=memo.get("pose_card") or None,
                    params=scene.memo_params(root, memo, translate=False))
    return " -> %s keyed again" % ", ".join(scene.walker_label(r) for r in roots)


def reset(walk_name, clean=None, rekey=None):
    """Reset: the cycle's correction dropped; its rig (when standing) back in the plain mean pose; its walkers
    keyed again (`rekey(walk)`, the card's; else as each was keyed last). Returns the status line."""
    fix, path = scene.walk_fix(walk_name)
    had = not mp.is_empty(fix)
    mp.save(path, mp.empty())
    label = scene.walk_label(walk_name)
    line = ("%s: the mean pose correction dropped" % label) if had else "%s has no correction" % label
    if find(walk_name) is not None:
        press(walk_name, clean)
        line += ", the rig pose back in the mean pose"
    return line + (rekey or rekey_target)(walk_name)


def delete(walk=None):
    """Delete rig pose: the cycle `walk`'s rig out of the scene, whole (Animation Setup's Delete, no question
    asked - it is this tool's) - the only one standing when that cycle has none; the cycle's correction stays.
    Returns the status line."""
    from maya_scenesetup import deletion
    rig = find(walk)
    if rig is None:
        standing = rigs()
        if len(standing) == 1:
            rig = standing[0]
        elif standing:
            raise Refusal("%s has no rig pose - %d others stand (select a walker on one to make its cycle the "
                          "active one)" % (scene.walk_label(walk), len(standing)))
        else:
            raise Refusal("no rig pose in the scene")
    name = memo_of(rig).get("walk") or "-"
    stop()
    _state()["bones"] = None
    text = deletion.delete_selected([rig.main], confirm=lambda _text: True)
    return "rig pose of %s deleted (%s) - the walk keeps its correction" % (scene.walk_label(name), text)


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
