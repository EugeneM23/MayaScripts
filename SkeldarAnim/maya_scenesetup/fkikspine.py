"""FK / IK for the spine of an AdvancedSkeleton rig (2026-10-10).

The spine switch of `fkik`, for the one spine: `FKIKSpine_M.FKIKBlend` (0 FK,
10 IK) blends the deform joints Spine1..4 between the FK chain (FKXSpine) and the
IK spline chain (IKXSpine) through `Spine<n>BM_M`. Spine5 follows the FK chain
whatever the blend says (measured 2026-10-10: its point constraint reads FKXSpine5
only), but it hangs under Spine4 (`FKParentConstraintToSpine4_M` ties the FK top to
the deform Spine4), so it moves when Spine4 turns.

## The IK spine is a spline, not a chain of controls

The spline (`IKSpineCurve_M`, its ikSpline solver `IKSpineHandle_M`) is driven by
five CVs, each the world position of an `IKSpineLocator` parented to a control:
CV0 `IKSpine1_M`, CV1 `IKcvSpine1_M`, CV2 `IKcvSpine2_M`, CV3 `IKcvSpine3_M`, CV4
`IKSpine3_M`. The IK joints `IKXSpine1..4_M` sit on the curve, and they do NOT
sit on the CVs in general (measured 2026-10-10: moving CV2 by 6.7 cm moved IKX2
3.2 cm). So there is no direct copy of the FK joints onto the controls.

## What the switch does

To IK: the four blended joints' IK places AND turns are FIT to the shown FK
joints. The unknowns are the local translates of the five CV controls and the
rotates of the two end controls (IKSpine1_M, IKSpine3_M: they turn the spline's
end joints - the top's turn carries Spine5, measured 2026-10-10); the residual is
`fkik.joint_residual` of IKX1..4 against the shown joints, read from the rig's own
evaluation. A damped Gauss-Newton step per frame, the sensitivities measured by
small probes (`FIT_STEP`), the controls' keys cut first (a keyed channel takes no
setAttr) and written back as keys on the frames the switch keys. Measured on Manny
and Creep: places and turns within 0.01 cm and 0.01 deg at the keys, both ways.

To FK: the FK controls take the shown joints' rotations, through the same rigid
chain as the limbs (`fkik.fk_locals`).

Keys: keys-only, as the limbs (`fkik.key_plan` - the keys of what moves the
shown spine). A range is cut and keyed as the limbs' ranges are.

Spec: docs/superpowers/specs/2026-10-10-legs-spine-fkik-design.md
"""

import math
from collections import namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_rigs
from maya_scenesetup import fkik

FK, IK = fkik.FK, fkik.IK
BLEND_NODE = "FKIKSpine_M"
BLEND_ATTR = "FKIKBlend"
SIDE = "M"
DEFORM = tuple("Spine%d_M" % i for i in range(1, 6))
FK_CONTROLS = tuple("FKSpine%d_M" % i for i in range(1, 6))
FKX = tuple("FKXSpine%d_M" % i for i in range(1, 6))
IKX = tuple("IKXSpine%d_M" % i for i in range(1, 5))
# CV0..CV4 of the spline: the control each one is a locator of
CV_CONTROLS = ("IKSpine1_M", "IKcvSpine1_M", "IKcvSpine2_M", "IKcvSpine3_M", "IKSpine3_M")
BLENDED = 4                          # Spine1..4 are blended (Spine<n>BM_M); Spine5 follows the FK chain
FIT_STEP, FIT_TOLERANCE, FIT_TRIES = fkik.FIT_STEP, fkik.FIT_TOLERANCE, fkik.FIT_TRIES

Spine = namedtuple("Spine", "blend deform fk fkx ikx cv side kind")

_TRANSLATE = fkik.TRANSLATE
_ROTATE = fkik.ROTATE
_LABEL = fkik.LABEL[fkik.SPINE]


# ------------------------------------------------------------------- pure
# the Gauss-Newton helpers are `fkik`'s (the leg's pole is fitted the same way)

solve_linear = fkik.solve_linear
gauss_newton_step = fkik.gauss_newton_step


# ------------------------------------------------------------------ scene

def _one(rig, leaf):
    paths = cmds.ls(maya_rigs.node(rig, leaf), long=True) or []
    return paths[0] if len(paths) == 1 else None


def spine(rig):
    """The spine's nodes on `rig`, or (None, refusal)."""
    blend = _one(rig, BLEND_NODE)
    if not blend:
        return None, fkik.MISSING % (_LABEL, BLEND_NODE, maya_rigs.label(rig))
    found = {}
    for key, leaves in (("deform", DEFORM), ("fk", FK_CONTROLS), ("fkx", FKX),
                        ("ikx", IKX), ("cv", CV_CONTROLS)):
        nodes = []
        for leaf in leaves:
            path = _one(rig, leaf)
            if not path:
                return None, fkik.MISSING % (_LABEL, leaf, maya_rigs.label(rig))
            nodes.append(path)
        found[key] = nodes
    return Spine(blend + "." + BLEND_ATTR, found["deform"], found["fk"], found["fkx"],
                 found["ikx"], found["cv"], SIDE, fkik.SPINE), ""


def state(rig):
    """FK / IK / None (mixed) for the spine, or None with no spine."""
    sp, _refusal = spine(rig)
    return fkik.mode_of(fkik.blend_values(sp)) if sp else None


def whole_take(sp):
    """Playback range and the keys of every control the spine's switch involves,
    unsnapped (`fkik.whole_take`'s shape)."""
    keys = []
    for node in list(sp.fk) + list(sp.cv) + [sp.blend.split(".")[0]]:
        keys.extend(cmds.keyframe(node, query=True, timeChange=True) or [])
    start = cmds.playbackOptions(query=True, min=True)
    end = cmds.playbackOptions(query=True, max=True)
    if keys:
        start, end = min(start, min(keys)), max(end, max(keys))
    return start, end


def _world(node):
    return fkik._world(node)


def _pos(matrix):
    return fkik.position(matrix)


def _shown(sp):
    """What the spine shows at the current frame: the blended joints, then the
    FK joints Spine4 and Spine5 (their point constraints read the FK chain)."""
    weight = cmds.getAttr(sp.blend) / fkik.BLEND[IK]
    out = [fkik.blended(_world(fk), _world(ik), weight)
           for fk, ik in zip(sp.fkx[:BLENDED], sp.ikx[:BLENDED])]
    return out + [_world(node) for node in sp.fkx[BLENDED:]]


def _sample(sp, frames):
    """One walk over the frames: what the spine shows, the deform joints (for the
    measure after), the FK chain's rigid pieces and the CV controls' parents."""
    s = dict((key, {}) for key in ("shown", "deform", "fk_parent", "chain"))
    extras = [fkik._parent(node) for node in sp.fk]
    for frame in frames:
        fkik._goto(frame)
        s["shown"][frame] = _shown(sp)
        s["deform"][frame] = [_world(node) for node in sp.deform]
        s["fk_parent"][frame] = _world(extras[0])
        s["chain"][frame] = [None] + [_world(extras[i]) * _world(sp.fkx[i - 1]).inverse()
                                      for i in range(1, len(extras))]
    return s


def _cv_plugs(sp):
    """What the fit moves: the translates of the five CV controls, and the rotates
    of the two end controls (IKSpine1_M, IKSpine3_M), which turn the spline's
    end joints (the top's orientation carries Spine5 - measured 2026-10-10)."""
    return ([(node, ch) for node in sp.cv for ch in _TRANSLATE] +
            [(sp.cv[0], ch) for ch in _ROTATE] + [(sp.cv[-1], ch) for ch in _ROTATE])


def _fit_ik(sp, frames, samples, span):
    """The spline's controls, frame by frame, that put the blended IK joints
    Spine1..4 on the shown FK joints - their places AND their turns. Returns
    ({(control, channel): [values]}, worst place error in cm, worst turn in deg)
    over the frames. A damped Gauss-Newton step per frame (`gauss_newton_step`)."""
    plugs = _cv_plugs(sp)
    seed = frames[0] - 1 if span[2] else frames[0]
    x = [cmds.getAttr(node + "." + ch, time=seed) for node, ch in plugs]
    out = dict(((node, ch), []) for node, ch in plugs)
    worst_cm = worst_deg = 0.0
    joints = sp.ikx[:BLENDED]

    def place(values):
        for (node, ch), v in zip(plugs, values):
            cmds.setAttr(node + "." + ch, v)

    def residual(values, targets):
        place(values)
        return fkik.joint_residual([_world(node) for node in joints], targets)

    for frame in frames:
        fkik._goto(frame)
        targets = list(samples["shown"][frame][:BLENDED])
        r = residual(x, targets)
        for _try in range(FIT_TRIES):
            if math.sqrt(sum(v * v for v in r) / len(r)) <= FIT_TOLERANCE:
                break
            jacobian = [[0.0] * len(plugs) for _ in range(len(r))]
            for i in range(len(plugs)):
                probe = list(x)
                probe[i] += FIT_STEP
                rp = residual(probe, targets)
                for k in range(len(r)):
                    jacobian[k][i] = (rp[k] - r[k]) / FIT_STEP
            dx = gauss_newton_step(jacobian, r)
            if dx is None:
                break
            trial = [a + d for a, d in zip(x, dx)]
            rt = residual(trial, targets)
            if sum(v * v for v in rt) < sum(v * v for v in r):
                x, r = trial, rt
            else:
                break
        place(x)
        matrices = [_world(node) for node in joints]
        for current, goal in zip(matrices, targets):
            worst_cm = max(worst_cm, (_pos(current) - _pos(goal)).length())
            worst_deg = max(worst_deg, math.degrees(fkik.rotation_vector(goal, current).length()))
        for (node, ch), v in zip(plugs, x):
            out[(node, ch)].append(v)
    return out, worst_cm, worst_deg


def _to_fk(sp, frames, samples, span):
    """The FK controls' rotations, frame by frame, that put the shown joints where
    they stand (`fkik.fk_locals`, the limbs' rigid chain)."""
    fkx_in_ctrl = [_world(fkx) * _world(ctl).inverse() for fkx, ctl in zip(sp.fkx, sp.fk)]
    values = dict(((node, ch), []) for node in sp.fk for ch in _ROTATE)
    seed = frames[0] - 1 if span[2] else frames[0]
    previous = [fkik._seed(node, _ROTATE, seed) for node in sp.fk]
    for frame in frames:
        locals_ = fkik.fk_locals(samples["shown"][frame], samples["fk_parent"][frame],
                                 samples["chain"][frame], fkx_in_ctrl)
        for i, node in enumerate(sp.fk):
            order = cmds.getAttr(node + ".rotateOrder")
            _t, r = fkik.local_channels(locals_[i], order, previous[i])
            previous[i] = r
            for ch, v in zip(_ROTATE, r):
                values[(node, ch)].append(v)
    return values


def key_plan(sp, span):
    """(frames to sample, frames keyed, {frame: (in, out) tangents}) of a keys-only
    switch: the keys of what moves the spine it shows (`fkik.driving_curves`)."""
    mode = fkik.mode_of(fkik.blend_values(sp))
    if mode == FK:
        nodes, plugs, own = list(sp.fkx), [], list(sp.fk)
    elif mode == IK:
        nodes, plugs, own = list(sp.fkx) + list(sp.ikx) + list(sp.cv), [], list(sp.cv)
    else:
        nodes, plugs, own = list(sp.fkx) + list(sp.ikx) + list(sp.cv), [sp.blend], \
            list(sp.fk) + list(sp.cv)
    curves = fkik.driving_curves(nodes, plugs)
    table = dict((curve, fkik._keys_of(curve)) for curve in curves)
    own_set = set(fkik._long(node) for node in own)
    mine = [table[c] for c in curves
            if own_set & set(fkik._long(node) for node in cmds.listConnections(
                c + ".output", source=False, destination=True) or [])]
    every = list(table.values())
    keys = fkik.key_frames([t for curve in every for t, _i, _o in curve], span)
    tangents = dict((frame, fkik.tangents_at(mine, every, frame)) for frame in keys)
    frames = keys or [cmds.currentTime(query=True)]
    return frames, keys, tangents


def refusal(sp, mode, span):
    """Why the spine may not be switched to `mode`, or ''."""
    driver = fkik._foreign(sp.blend)
    if driver:
        return fkik.DRIVEN % (_LABEL, "FKIKBlend", driver)
    if fkik.mode_of(fkik.blend_values(sp)) == mode:
        return fkik.ALREADY % (_LABEL, mode)
    plugs = _cv_plugs(sp) if mode == IK else [(node, ch) for node in sp.fk for ch in _ROTATE]
    for node, ch in plugs:
        driver = fkik._foreign(node + "." + ch)
        if driver:
            return fkik.DRIVEN % (_LABEL, node.split("|")[-1] + "." + ch, driver)
    return ""


def switch(sp, mode, span, every_frame=False):
    """The spine to `mode` over `span`, keeping what it shows, keyed on the frames
    the shown spine is keyed on (`key_plan`), or on every frame (`every_frame`).
    The caller has checked `refusal` and holds the undo chunk. Returns the status."""
    start, end, ranged = span
    now = cmds.currentTime(query=True)
    if every_frame:
        frames, keys, tangents = list(range(start, end + 1)), None, {}
    else:
        frames, keys, tangents = key_plan(sp, span)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    before_mode = (cmds.evaluationManager(query=True, mode=True) or ["parallel"])[0]
    fkik._suspend(True)
    notes = []
    try:
        samples = _sample(sp, frames)
        if mode == FK:
            values = _to_fk(sp, frames, samples, span)
        else:
            cmds.evaluationManager(mode="off")
            for node, ch in _cv_plugs(sp):
                fkik._unkey(node + "." + ch, span)
            values, worst_cm, worst_deg = _fit_ik(sp, frames, samples, span)
            notes.append("spline fit to the FK spine: places within %.3f cm, turns within "
                         "%.2f deg" % (worst_cm, worst_deg))
        for (node, channel), series in values.items():
            plug = node + "." + channel
            fkik._write(plug, frames, series, span, cmds.getAttr(plug, lock=True), tangents)
        fkik._write_blend(sp, mode, span)
        after = {}
        for frame in frames:
            fkik._goto(frame)
            after[frame] = [_world(node) for node in sp.deform]
        moved = fkik.measure(samples["deform"], after)
    finally:
        cmds.evaluationManager(mode=before_mode)
        fkik._goto(now)
        cmds.autoKeyframe(state=auto)
        fkik._suspend(False)
    return fkik.switched_message(SIDE, mode, span, moved, notes, keys, kind=fkik.SPINE)
