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

## The root is in the switch too

`Root_M` (the root the pelvis and both legs hang from) is blended by the same spine
blend: it reads FKXRoot_M and IKXRoot_M. And the IK root IS the spline's hip
control: `IKXRoot_M` follows `IKSpine1_M` (CV0) - at the FK state the three stand in
one place. The first version fitted CV0 for the spine alone, so every switch to IK
moved the IK root, and with it the root, the pelvis and both legs: measured on a
retargeted UE take, the root 0.39 cm and 1.16 deg off, the feet 2 cm off on every
frame (2026-10-10, «при переключении с ФК на ИК спины у нас ломается анимация»).
Every gate had passed, because they all measured the spine.

## What the switch does

To IK: the IK root and the four blended joints are FIT to the shown root and the
shown FK joints, places AND turns. The unknowns are the local translates of the five
CV controls, the rotates of the two end controls (IKSpine1_M, IKSpine3_M: they turn
the root and the spline's ends - the top's turn carries Spine5) and of the mid control
(IKSpine2_M: it twists the middle, the root untouched - with the root held it is the
spine's start twist; without it the Orc D's spine rolled 2.6 deg off on a strong
bend, with it 0.4); the residual
is `fkik.joint_residual` of IKXRoot, IKX1..4 against the shown ones, read from the
rig's own evaluation, the root's part counted `ROOT_WEIGHT` times - where the spline
cannot reach the FK spine, the spine gives, never the root - nor the top joint, counted
as the root (`TOP_WEIGHT`). AdvancedSkeleton's own switch puts `IKSpine1_M` on the root
and `IKSpine3_M` on the top exactly and the middle approximately ("Target might not
fully Align"); the fit holds both ends as exactly and the middle better. Every frame is
fitted twice, from the frame before and from AdvancedSkeleton's own placement, and the
better kept: started only from the frame before, a chest the spline cannot follow (the
animator's FKSpine4_M moved 12 cm and turned 140 deg) dragged the fit into a worse twist
frame after frame, the top 29 cm and 167 deg off (2026-10-15, «при использовании
переключения FK IK из вкладки connection у нас ломается спина»). A Levenberg-Marquardt
step per frame (`gauss_newton_step`, the damping
raised and the step retried when it does not help), the sensitivities measured by
small probes (`FIT_STEP`), the controls' keys cut first (a keyed channel takes no
setAttr) and written back as keys on the frames the switch keys.

To FK: when the IK root stands off the FK root (the hip control moved in IK), the FK
root control `FKRoot_M` is put on it first (`_root_to_fk`) and the FK chain read
again; then the FK spine controls take the shown joints' places and turns, through
the same rigid chain as the limbs (`fkik.fk_locals`) - as AdvancedSkeleton's own
switch does (`.t` and `.r` of every FK spine control): the IK spine stretches.
Roots that agree get no keys.

The status line says how far the deform root moved (`root_note`): it carries the
pelvis and both legs.

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
# the mid control: its turn twists the spine's middle and leaves the root alone (measured
# 2026-10-10 on Orc_D_Rig: rotateY +10 turns IKX1..3 by 5, 10, 5 deg, the root 0) - with the
# root held, IKSpine1_M's turn (which carries the root 1:1) is no longer the fit's to use
MID_CONTROL = "IKSpine2_M"
BLENDED = 4                          # Spine1..4 are blended (Spine<n>BM_M); Spine5 follows the FK chain
# the root is blended by the same spine blend (`Root_M` reads FKXRoot_M and IKXRoot_M): the
# IK root IS the spline's hip control, so the fit must hold it on the FK root (2026-10-10:
# moving the hip control moved the root, the pelvis and both legs - the feet 2 cm off)
ROOT_FK, ROOT_IK, ROOT_CONTROL, ROOT_DEFORM = "FKXRoot_M", "IKXRoot_M", "FKRoot_M", "Root_M"
ROOT_TOLERANCE_CM, ROOT_TOLERANCE_DEG = 0.005, 0.01    # roots this close need no FK root keys
# the root's residual counts this many times a spine joint's: the root carries the pelvis and
# both legs, so the fit may not trade it for the spine (2026-10-10: on the Creep a spine the
# spline cannot reach pulled the root 0.017 cm, 0.094 deg - the feet a lever of a metre away)
ROOT_WEIGHT = 100.0
# AdvancedSkeleton's own FK2IK switch turns the spline's end controls as these (children of
# FKXRoot_M and FKXSpine4_M): the fit starts there on every frame (`_as_seed`)
ALIGN_ROOT, ALIGN_TOP = "AlignIKToRoot_M", "AlignIKToSpine4_M"
# the top joint (Spine4) counts as much as the root: it carries Spine5, the neck, the head and
# both arms - a chest the spline cannot follow gives in the middle, never at the top (2026-10-15)
TOP_WEIGHT = ROOT_WEIGHT
FIT_STEP, FIT_TOLERANCE, FIT_TRIES = fkik.FIT_STEP, fkik.FIT_TOLERANCE, fkik.FIT_TRIES
LM_ATTEMPTS = 6                      # damping raises tried before a frame's fit gives up

Spine = namedtuple("Spine", "blend deform fk fkx ikx cv side kind root_fk root_ik root_ctl "
                            "root_deform mid align_root align_top",
                   defaults=(None, None, None, None, None, None, None))

_TRANSLATE = fkik.TRANSLATE
_ROTATE = fkik.ROTATE
_CHANNELS = fkik.CHANNELS
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
    root_fk, root_ik, root_ctl = _one(rig, ROOT_FK), _one(rig, ROOT_IK), _one(rig, ROOT_CONTROL)
    if not root_fk or not root_ik or not root_ctl:
        return None, fkik.MISSING % (_LABEL, "/".join((ROOT_FK, ROOT_IK, ROOT_CONTROL)),
                                     maya_rigs.label(rig))
    return Spine(blend + "." + BLEND_ATTR, found["deform"], found["fk"], found["fkx"],
                 found["ikx"], found["cv"], SIDE, fkik.SPINE, root_fk, root_ik, root_ctl,
                 _one(rig, ROOT_DEFORM), _one(rig, MID_CONTROL), _one(rig, ALIGN_ROOT),
                 _one(rig, ALIGN_TOP)), ""


def _ik_controls(sp):
    """The IK spine's controls the switch writes: the five CV controls and the mid."""
    return list(sp.cv) + ([sp.mid] if sp.mid else [])


def state(rig):
    """FK / IK / None (mixed) for the spine, or None with no spine."""
    sp, _refusal = spine(rig)
    return fkik.mode_of(fkik.blend_values(sp)) if sp else None


def whole_take(sp):
    """Playback range and the keys of every control the spine's switch involves,
    unsnapped (`fkik.whole_take`'s shape)."""
    keys = []
    for node in list(sp.fk) + _ik_controls(sp) + [sp.root_ctl, sp.blend.split(".")[0]]:
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
    """What the spine shows at the current frame: the blended joints Spine1..4,
    then the FK joint Spine5 (its point constraint reads the FK chain)."""
    weight = cmds.getAttr(sp.blend) / fkik.BLEND[IK]
    out = [fkik.blended(_world(fk), _world(ik), weight)
           for fk, ik in zip(sp.fkx[:BLENDED], sp.ikx[:BLENDED])]
    return out + [_world(node) for node in sp.fkx[BLENDED:]]


def _sample(sp, frames):
    """One walk over the frames: what the spine shows, the root (shown, FK, the FK
    root control's parent), the deform joints and the deform root (for the measure
    after), the FK chain's rigid pieces."""
    s = dict((key, {}) for key in ("shown", "root", "root_fk", "root_parent", "deform",
                                   "root_deform", "fk_parent", "chain"))
    extras = [fkik._parent(node) for node in sp.fk]
    root_parent = fkik._parent(sp.root_ctl)
    for frame in frames:
        fkik._goto(frame)
        s["shown"][frame] = _shown(sp)
        weight = cmds.getAttr(sp.blend) / fkik.BLEND[IK]
        s["root_fk"][frame] = _world(sp.root_fk)
        s["root"][frame] = fkik.blended(s["root_fk"][frame], _world(sp.root_ik), weight)
        s["root_parent"][frame] = _world(root_parent)
        s["deform"][frame] = [_world(node) for node in sp.deform]
        if sp.root_deform:
            s["root_deform"][frame] = _world(sp.root_deform)
        s["fk_parent"][frame], s["chain"][frame] = _fk_pieces(sp, extras, s["shown"][frame])
    return s


def _under(node, parent):
    """Whether the long path `node` hangs below the long path `parent`. Pure."""
    return node.startswith(parent + "|")


def _fk_pieces(sp, extras, shown):
    """The FK chain as it stands now: the first control's parent, and the rigid
    piece from each joint to the next control's parent. A parent below the previous
    FKX joint is rigid on that joint; one that is not - Spine5's hangs under the
    DEFORM Spine4 (`FKParentConstraintToSpine4_M`) - is rigid on the joint the spine
    shows, and measured against the FKX joint in IK it is not rigid at all (measured
    2026-10-10: 0.0000 against the deform Spine4, 0.0045 cm, 0.014 deg against FKX4 on
    an unedited take; more on an edited one)."""
    chain = [None]
    for i in range(1, len(extras)):
        anchor = _world(sp.fkx[i - 1]) if _under(extras[i], sp.fkx[i - 1]) else shown[i - 1]
        chain.append(_world(extras[i]) * anchor.inverse())
    return _world(extras[0]), chain


def _reread_fk(sp, frames, samples):
    """The FK chain's pieces read again on every frame (after the FK root moved)."""
    extras = [fkik._parent(node) for node in sp.fk]
    for frame in frames:
        fkik._goto(frame)
        samples["fk_parent"][frame], samples["chain"][frame] = _fk_pieces(
            sp, extras, samples["shown"][frame])


def root_note(before, after):
    """How far the deform root moved across the switch ({frame: matrix} each), in the
    status line's words: the root carries the pelvis and both legs. Pure."""
    cm = deg = 0.0
    at = None
    for frame in sorted(before):
        if frame not in after:
            continue
        d = (fkik.position(before[frame]) - fkik.position(after[frame])).length()
        if d > cm:
            cm, at = d, frame
        deg = max(deg, math.degrees(fkik.rotation_vector(after[frame], before[frame]).length()))
    if cm <= ROOT_TOLERANCE_CM and deg <= ROOT_TOLERANCE_DEG:
        return "the root and legs kept to %.4f cm" % cm
    return "the root MOVED %.3f cm, %.2f deg (frame %s) - the legs with it" % (
        cm, deg, "%g" % at if at is not None else "?")


def roots_apart(shown, fk, cm=ROOT_TOLERANCE_CM, deg=ROOT_TOLERANCE_DEG):
    """Whether the shown root and the FK root part anywhere ({frame: matrix} each),
    past `cm` or `deg`. Pure."""
    for frame, target in shown.items():
        current = fk[frame]
        if (fkik.position(target) - fkik.position(current)).length() > cm:
            return True
        if math.degrees(fkik.rotation_vector(target, current).length()) > deg:
            return True
    return False


def _root_to_fk(sp, frames, samples, span):
    """The FK root control, frame by frame, on the root the spine shows - when the
    IK root has been moved off the FK root (the animator moved the hip control in
    IK): switched to FK as it stands, the root and both legs would jump back. {}
    when the two roots agree (nothing to key), or when the control is driven."""
    if not roots_apart(samples["root"], samples["root_fk"]):
        return {}, ""
    for ch in _TRANSLATE + _ROTATE:
        driver = fkik._foreign(sp.root_ctl + "." + ch)
        if driver:
            return {}, "%s.%s is driven by %s - the root was not aligned" % (
                sp.root_ctl.split("|")[-1], ch, driver)
    fkx_in_ctrl = _world(sp.root_fk) * _world(sp.root_ctl).inverse()
    order = cmds.getAttr(sp.root_ctl + ".rotateOrder")
    seed = frames[0] - 1 if span[2] else frames[0]
    previous = fkik._seed(sp.root_ctl, _ROTATE, seed)
    values = dict(((sp.root_ctl, ch), []) for ch in _TRANSLATE + _ROTATE)
    for frame in frames:
        local = fkik.fk_locals([samples["root"][frame]], samples["root_parent"][frame], [None],
                               [fkx_in_ctrl])[0]
        t, r = fkik.local_channels(local, order, previous)
        previous = r
        for ch, v in zip(_TRANSLATE + _ROTATE, t + r):
            values[(sp.root_ctl, ch)].append(v)
    return values, "the FK root put on the IK hip"


def _cv_plugs(sp):
    """What the fit moves: the translates of the five CV controls, the rotates of the
    two end controls (IKSpine1_M, IKSpine3_M), which turn the spline's end joints (the
    top's orientation carries Spine5 - measured 2026-10-10), and the mid control's
    rotates (`MID_CONTROL`, the middle's twist)."""
    mid = [(sp.mid, ch) for ch in _ROTATE] if sp.mid else []
    return ([(node, ch) for node in sp.cv for ch in _TRANSLATE] +
            [(sp.cv[0], ch) for ch in _ROTATE] + [(sp.cv[-1], ch) for ch in _ROTATE] + mid)


def weighted(residual, weight=ROOT_WEIGHT, top=1.0):
    """The fit's residual with the root's six entries (place, turn) counted `weight`
    times, and the last joint's six `top` times. Pure."""
    out = [v * weight for v in residual[:6]] + list(residual[6:])
    if top != 1.0 and len(out) > 6:
        out[-6:] = [v * top for v in out[-6:]]
    return out


def _align_offsets(sp):
    """The AlignIKTo nodes' places in their FKX joints (AdvancedSkeleton's own switch
    puts the spline's end controls on them): {control: local matrix}, read now."""
    out = {}
    for control, align in ((sp.cv[0], sp.align_root), (sp.cv[-1], sp.align_top)):
        if align:
            out[control] = _world(align) * _world(fkik._parent(align)).inverse()
    return out


def _as_seed(sp, plugs, offsets, root, top, previous):
    """The fit's start on one frame, as AdvancedSkeleton's own FK2IK switch places the
    spline (`asAlignFKIK`): the hip control on the root, the top control on the top
    joint - both turned as their AlignIKTo nodes - the mid control unturned, the CV
    controls at rest. Set on the controls, read back as the
    fit's values, every turn the euler nearest `previous` (the frame before)."""
    for node in sp.cv[1:-1]:
        cmds.setAttr(node + ".translate", 0.0, 0.0, 0.0)
    for control, target in ((sp.cv[0], root), (sp.cv[-1], top)):
        world = offsets[control] * target
        rot = om.MTransformationMatrix(world).rotation().reorder(
            cmds.getAttr(control + ".rotateOrder"))    # xform -ro reads the control's order
        cmds.xform(control, worldSpace=True, translation=list(_pos(target))[:3],
                   rotation=[math.degrees(a) for a in (rot.x, rot.y, rot.z)])
    if sp.mid:
        # its turn only: its translate is not the fit's and is not keyed - moved here it
        # stayed moved under every later frame's fit
        cmds.xform(sp.mid, objectSpace=True, rotation=(0.0, 0.0, 0.0))
    x = [cmds.getAttr(node + "." + ch) for node, ch in plugs]
    if previous is not None:
        for node in set(node for node, ch in plugs if ch in _ROTATE):
            idx = [i for i, (n, ch) in enumerate(plugs) if n == node and ch in _ROTATE]
            order = cmds.getAttr(node + ".rotateOrder")
            now = om.MEulerRotation(*[math.radians(x[i]) for i in idx] + [order])
            before = om.MEulerRotation(*[math.radians(previous[i]) for i in idx] + [order])
            near = now.closestSolution(before)
            for i, a in zip(idx, (near.x, near.y, near.z)):
                x[i] = math.degrees(a)
    return x


def _fit_ik(sp, frames, samples, span):
    """The spline's controls, frame by frame, that put the IK root and the blended
    IK joints Spine1..4 on the shown root and joints - their places AND their turns,
    the root and the top held hardest (`ROOT_WEIGHT`, `TOP_WEIGHT`: they carry the legs,
    and the neck, the head and the arms). Each frame is fitted from two starts - the frame
    before, and AdvancedSkeleton's own placement (`_as_seed`) - and the better kept.
    Returns ({(control, channel): [values]}, the spine's worst place error in cm and
    turn in deg, the root's) over the frames. A Levenberg-Marquardt step per frame
    (`gauss_newton_step`)."""
    plugs = _cv_plugs(sp)
    seed = frames[0] - 1 if span[2] else frames[0]
    x = [cmds.getAttr(node + "." + ch, time=seed) for node, ch in plugs]
    out = dict(((node, ch), []) for node, ch in plugs)
    worst = {"cm": 0.0, "deg": 0.0, "root_cm": 0.0, "root_deg": 0.0}
    joints = (sp.root_ik,) + tuple(sp.ikx[:BLENDED])

    def place(values):
        for (node, ch), v in zip(plugs, values):
            cmds.setAttr(node + "." + ch, v)

    offsets = _align_offsets(sp) if sp.align_root and sp.align_top else None

    def residual(values, targets):
        place(values)
        return weighted(fkik.joint_residual([_world(node) for node in joints], targets),
                        top=TOP_WEIGHT if offsets is not None else 1.0)

    def fit(x, targets):
        r = residual(x, targets)
        damp = fkik.FIT_DAMP
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
            # Levenberg-Marquardt: a step that does not lower the residual is retried
            # with more damping (the same Jacobian), not abandoned
            accepted = False
            for _attempt in range(LM_ATTEMPTS):
                dx = gauss_newton_step(jacobian, r, damp=damp)
                if dx is None:
                    break
                trial = [a + d for a, d in zip(x, dx)]
                rt = residual(trial, targets)
                if sum(v * v for v in rt) < sum(v * v for v in r):
                    x, r = trial, rt
                    damp = max(damp / 3.0, 1e-9)
                    accepted = True
                    break
                damp *= 10.0
            if not accepted:
                break
        return x, sum(v * v for v in r)

    for frame in frames:
        fkik._goto(frame)
        targets = [samples["root"][frame]] + list(samples["shown"][frame][:BLENDED])
        x, cost = fit(x, targets)
        if offsets is not None:
            # a second start, where AdvancedSkeleton's own switch puts the spline - the root
            # and the top exact - and the better fit kept: started only from the frame
            # before, a chest the spline cannot follow (moved 12 cm, turned 140 deg) dragged
            # the fit frame after frame 29 cm and 167 deg off its top (2026-10-15)
            other, other_cost = fit(_as_seed(sp, plugs, offsets, targets[0], targets[-1], x),
                                    targets)
            if other_cost < cost:
                x = other
        place(x)
        matrices = [_world(node) for node in joints]
        for i, (current, goal) in enumerate(zip(matrices, targets)):
            cm = (_pos(current) - _pos(goal)).length()
            deg = math.degrees(fkik.rotation_vector(goal, current).length())
            key = "root_" if i == 0 else ""
            worst[key + "cm"] = max(worst[key + "cm"], cm)
            worst[key + "deg"] = max(worst[key + "deg"], deg)
        for (node, ch), v in zip(plugs, x):
            out[(node, ch)].append(v)
    return out, worst


def _to_fk(sp, frames, samples, span):
    """The FK controls, frame by frame, on the shown joints - their places AND their
    turns (`fkik.fk_locals`, the limbs' rigid chain), as AdvancedSkeleton's own switch
    sets every FK spine control (`xform -ws -t -ro`, keyed `.t` and `.r`). The IK spine
    stretches (`IKSpine3_M.stretchy` 10), so turns alone leave the joints where the FK
    lengths put them: measured 2026-10-10, the hip control moved 3 cm in IK, then every
    spine joint 0.30 cm off after a rotate-only switch."""
    fkx_in_ctrl = [_world(fkx) * _world(ctl).inverse() for fkx, ctl in zip(sp.fkx, sp.fk)]
    values = dict(((node, ch), []) for node in sp.fk for ch in _CHANNELS)
    seed = frames[0] - 1 if span[2] else frames[0]
    previous = [fkik._seed(node, _ROTATE, seed) for node in sp.fk]
    for frame in frames:
        locals_ = fkik.fk_locals(samples["shown"][frame], samples["fk_parent"][frame],
                                 samples["chain"][frame], fkx_in_ctrl)
        for i, node in enumerate(sp.fk):
            order = cmds.getAttr(node + ".rotateOrder")
            t, r = fkik.local_channels(locals_[i], order, previous[i])
            previous[i] = r
            for ch, v in zip(_CHANNELS, t + r):
                values[(node, ch)].append(v)
    return values


def key_plan(sp, span):
    """(frames to sample, frames keyed, {frame: (in, out) tangents}) of a keys-only
    switch: the keys of the spine's own controls (`fkik.own_keys`)."""
    mode = fkik.mode_of(fkik.blend_values(sp))
    ik = _ik_controls(sp)
    if mode == FK:
        nodes, plugs, own = list(sp.fkx), [], list(sp.fk)
    elif mode == IK:
        nodes, plugs, own = list(sp.fkx) + list(sp.ikx) + ik, [], ik
    else:
        nodes, plugs, own = list(sp.fkx) + list(sp.ikx) + ik, [sp.blend], list(sp.fk) + ik
    return fkik.own_keys(own, plugs, span)


def refusal(sp, mode, span):
    """Why the spine may not be switched to `mode`, or ''."""
    driver = fkik._foreign(sp.blend)
    if driver:
        return fkik.DRIVEN % (_LABEL, "FKIKBlend", driver)
    if fkik.mode_of(fkik.blend_values(sp)) == mode:
        return fkik.ALREADY % (_LABEL, mode)
    plugs = _cv_plugs(sp) if mode == IK else [(node, ch) for node in sp.fk for ch in _CHANNELS]
    for node, ch in plugs:
        driver = fkik._foreign(node + "." + ch)
        if driver:
            return fkik.DRIVEN % (_LABEL, node.split("|")[-1] + "." + ch, driver)
    why = fkik.layer_refusal([node + "." + ch for node, ch in plugs] + [sp.blend])
    if why:
        return "%s: %s" % (_LABEL, why)
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
            # the root first: the FK spine hangs under it, so its pieces are read again after
            root_values, root_text = _root_to_fk(sp, frames, samples, span)
            for (node, channel), series in root_values.items():
                plug = node + "." + channel
                fkik._write(plug, frames, series, span, cmds.getAttr(plug, lock=True), tangents)
            if root_values:
                _reread_fk(sp, frames, samples)
            if root_text:
                notes.append(root_text)
            values = _to_fk(sp, frames, samples, span)
        else:
            cmds.evaluationManager(mode="off")
            for node, ch in _cv_plugs(sp):
                fkik._unkey(node + "." + ch, span)
            # the fit's own worst is not said: the measure of the deform spine after says it
            values, _worst = _fit_ik(sp, frames, samples, span)
        for (node, channel), series in values.items():
            plug = node + "." + channel
            fkik._write(plug, frames, series, span, cmds.getAttr(plug, lock=True), tangents)
        fkik._write_blend(sp, mode, span)
        after, root_after = {}, {}
        for frame in frames:
            fkik._goto(frame)
            after[frame] = [_world(node) for node in sp.deform]
            if sp.root_deform:
                root_after[frame] = _world(sp.root_deform)
        moved = fkik.measure(samples["deform"], after)
        if root_after:
            notes.insert(0, root_note(samples["root_deform"], root_after))
    finally:
        cmds.evaluationManager(mode=before_mode)
        fkik._goto(now)
        cmds.autoKeyframe(state=auto)
        fkik._suspend(False)
    return fkik.switched_message(SIDE, mode, span, moved, notes, keys, kind=fkik.SPINE)
