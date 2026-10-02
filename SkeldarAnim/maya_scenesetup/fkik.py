"""FK / IK for the arms of an AdvancedSkeleton rig: the arm keeps what it shows.

The animator (2026-09-30): «для вкладки connections нужно реализовать кнопочки
которые будут переключать руки в FK IK ... у адванцед скелетона уже есть
встроенный переключатель FK IK».

## AdvancedSkeleton's own switch, and why it is replicated

The state is `FKIKArm_<side>.FKIKBlend` (0 FK, 10 IK): it blends the
deformation joints' constraints between the FKX and the IKX chain. The
vendor's `asSwitchFKIK` / `asAlignFKIK` (AdvancedSkeleton.mel) align one
chain onto the other on the current frame, or over a highlighted range, and
set the blend. A colleague's Maya has no AdvancedSkeleton, and the plugin
runs nothing of it since 2026-09-07 (`vendor_bake` is the precedent), so the
alignment is done here in cmds - with one difference that is the design:

## The source is what the arm SHOWS

The arm shows the FKX and the IKX chain blended by `FKIKBlend` - the
deformation joints' constraints and AS's twist network (`<Joint>BM_<side>`,
a blendMatrix of the two) read exactly that. So both chains and the blend
are sampled on every frame of the span BEFORE anything moves, blended as
the rig blends them (positions lerped, rotations slerped the short way), and
the target mode's controls are keyed to reproduce the blend. A switch
therefore works from FK, from IK and from a keyed or half-way blend alike.
The deformation joints themselves are NOT the source: their constraint's
offsetX is driven by the twist network (`twistAddition<Joint>`), so they
stand off both chains by the arm's own roll (measured 59 deg at one frame).
Measured on the three shipped rigs (build pose): the deformation joint, its
FKX and its IKX joint stand in one frame (<= 3e-6 deg), and
`AlignIKTo<Wrist>` stands where `IKArm` does.

- to FK: control world = L^-1 . source (L = the FKX joint in its control,
  constant: CustomOrientReverse), local = that . (parent world)^-1 with the
  elbow's and wrist's parents the rigid chain from the NEW upper joint. An
  FK arm reproduces any IK pose exactly;
- to IK: control world = K . source_wrist (K = AlignIKTo in the FKX wrist);
  the pole from the source chain - on the shoulder-wrist line at the
  elbow's share, nudged NUDGE of the limb away from the pole side in the
  elbow's frame, aimed at the elbow, a limb out (`maya_pmretarget`'s pole).
  The IK chain takes the source chain's SHAPE (2026-10-02, `maya_ikmatch`: a
  squash & stretch take gives the FK arm the clip's lengths, and «анимация IK
  должна соответствовать анимации FK»): `Lenght1/2` from the source's two
  segments, the chain's root joint `IKX<Shoulder>` onto the source's
  shoulder. The solve attributes (`swivel`, `antiPop`, `stretchy`, the
  pole's `followArm` and `lock`) at their defaults: reset over a whole take,
  a refusal inside a range. The hand and the elbow's place are reproduced;
  **an FK elbow twisted about its own bone is not** - an IK elbow is a
  hinge in the plane, AS's own switch has the same limit, and a retargeted
  UE take carries the forearm's pronation there. It is measured and said.

Every euler is the one nearest the frame before (trap 108); a whole-take
channel that comes out constant collapses to a plain value; the blend is
unkeyed at 0 / 10 over a whole take and keyed stepped around a range. The
result is MEASURED on the deformation joints against their samples - the
joints' places, the hand's turn, the arm's roll - and said.

Spec: docs/superpowers/specs/2026-09-30-connections-fkik-switch-design.md
"""

import math
from collections import namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_ikmatch
import maya_rigs

FK, IK = "FK", "IK"
MODES = (FK, IK)
BLEND = {FK: 0.0, IK: 10.0}
LIMB = "Arm"
FKIK_NODE = "FKIK{0}_{1}"            # FKIKArm_R
BLEND_ATTR = "FKIKBlend"
IK_CONTROL = "IK{0}_{1}"             # IKArm_R
POLE = "Pole{0}_{1}"                 # PoleArm_R
ALIGN = "AlignIKTo{0}_{1}"           # AlignIKToWrist_R
TRANSLATE = ("translateX", "translateY", "translateZ")
ROTATE = ("rotateX", "rotateY", "rotateZ")
CHANNELS = TRANSLATE + ROTATE
# what a matched IK needs at its default (AS resets every custom attribute); the lengths
# are not among them since 2026-10-02 - they are the source's (`maya_ikmatch`)
IK_SOLVE = ("swivel", "antiPop", "stretchy")
LENGHTS = maya_ikmatch.LENGHTS
POLE_SOLVE = ("followArm", "lock")
NUDGE = 0.002                        # of the limb's length (maya_pmretarget)
CONSTANT = 1e-6
TOLERANCE_CM = 0.05                  # "kept" below these, "moved" above: the pole's
                                     # nudge leaves an IK elbow 0.02-0.05 cm off
TOLERANCE_DEG = 0.05

ARM_LABEL = "Arm_{0}"
ALREADY = "%s is already %s"
MISSING = "%s: %s not found on %s"
DRIVEN = "%s: %s is driven by %s - not a key the switch can rewrite"
SOLVE_IN_RANGE = ("%s: %s not at the default - switch the whole take (no "
                  "highlight) to reset it, or zero it first")
NO_POLE_SIDE = "%s: the IK pole stands on the arm's line - no bend plane to read"

# root_parent -- what the IK chain's root joint stands in (IKXOffset<Shoulder>);
# units       -- the IK segments' rest lengths behind Lenght1/2 (`maya_ikmatch.unit_of`)
Limb = namedtuple("Limb", "side blend deform fk fkx ikx ik pole align root_parent units")


# ------------------------------------------------------------------- pure

def mode_of(values, tolerance=CONSTANT):
    """FK / IK when every value (the blend now, or each of its keys) sits at
    one end, else None - a mixed take. Pure."""
    values = list(values)
    for mode in MODES:
        if values and all(abs(v - BLEND[mode]) <= tolerance for v in values):
            return mode
    return None


def span_for(highlight, whole):
    """(start, end, ranged): the highlighted frames (the slider answers
    [start, end + 1)) or the whole take snapped outward. Pure."""
    if highlight:
        return int(round(highlight[0])), int(round(highlight[1])) - 1, True
    return int(math.floor(whole[0])), int(math.ceil(whole[1])), False


def blend_keys(start, end, target):
    """The blend's keys around a range: (time, value or None to insert with
    the curve's shape kept, stepped out of it). Pure."""
    keys = [(start - 1, None, True), (start, target, start == end)]
    if end != start:
        keys.append((end, target, True))
    keys.append((end + 1, None, False))
    return keys


def local_channels(local, rotate_order, previous):
    """(translate, rotate in degrees) of a local matrix for a control in
    `rotate_order` (cmds' 0..5), the euler nearest `previous`. Pure."""
    tm = om.MTransformationMatrix(local)
    t = tm.translation(om.MSpace.kTransform)
    euler = tm.rotation().reorder(rotate_order)
    prev = om.MEulerRotation(*[math.radians(v) for v in previous] + [rotate_order])
    euler = euler.closestSolution(prev)
    return ((t.x, t.y, t.z),
            (math.degrees(euler.x), math.degrees(euler.y), math.degrees(euler.z)))


def fk_locals(shown, parent, chain, fkx_in_ctrl):
    """Each FK control's local matrix for its FKX joint to stand on `shown`:
    the first control's parent is `parent`; control i's parent is the rigid
    chain[i] from FKX i-1, which by then stands on shown[i-1]. Pure."""
    out = []
    for i, target in enumerate(shown):
        world = fkx_in_ctrl[i].inverse() * target
        parent_world = parent if i == 0 else chain[i] * shown[i - 1]
        out.append(world * parent_world.inverse())
    return out


def _on_line(s, e, w):
    upper, lower = (s - e).length(), (e - w).length()
    length = upper + lower
    return (s * lower + w * upper) / length, length


def pole_side(pole, s, e, w, elbow_rotation):
    """The pole's side of the arm, in the elbow's own frame: the pole off the
    shoulder-wrist line (its along-line part removed), else the elbow's bend,
    else None. Pure."""
    base, length = _on_line(s, e, w)
    line = (w - s).normal()
    for side in (pole - base, e - base):
        side = side - line * (side * line)
        if side.length() > 1e-6 * length:
            return side.normal() * elbow_rotation.inverse()
    return None


def pole_point(s, e, w, elbow_rotation, side_local, nudge=NUDGE):
    """Where the pole goes for the shown chain: on the line at the elbow's
    share, nudged away from the pole side in the elbow's frame, aimed at the
    elbow, a limb out. Bent, the bend decides; straight, the nudge - and it
    turns with the elbow, so the roll survives. Pure."""
    base, length = _on_line(s, e, w)
    nudged = base + (side_local * elbow_rotation) * (-nudge * length)
    aim = (e - nudged).normal()
    return nudged + aim * length


def off_default(attrs, tolerance=CONSTANT):
    """The solve attributes not at their default: {name: (value, key values,
    default)} -> sorted names. Pure."""
    out = []
    for name, (value, keys, default) in attrs.items():
        values = [value] + list(keys)
        if any(abs(v - default) > tolerance for v in values):
            out.append(name)
    return sorted(out)


def rotation_only(matrix):
    return om.MTransformationMatrix(matrix).rotation(asQuaternion=True).asMatrix()


def position(matrix):
    return om.MVector(matrix[12], matrix[13], matrix[14])


def angle(a, b):
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True).inverse() * \
        om.MTransformationMatrix(b).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def blended(fk, ik, weight):
    """The rig's blend of an FKX and an IKX joint (weight 0 = FK, 1 = IK):
    position lerped, rotation slerped the short way - the deformation
    joint's point and orient constraints, before the twist offset. Pure."""
    if weight <= 0.0:
        return om.MMatrix(fk)
    if weight >= 1.0:
        return om.MMatrix(ik)
    qa = om.MTransformationMatrix(fk).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(ik).rotation(asQuaternion=True)
    if qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w < 0:
        qb = om.MQuaternion(-qb.x, -qb.y, -qb.z, -qb.w)
    tm = om.MTransformationMatrix(om.MQuaternion.slerp(qa, qb, weight).asMatrix())
    tm.setTranslation(position(fk) * (1.0 - weight) + position(ik) * weight,
                      om.MSpace.kTransform)
    return tm.asMatrix()


Measure = namedtuple("Measure", "cm cm_frame hand roll roll_frame")


def measure(before, after):
    """How far the shown arm moved: {frame: [shoulder, elbow, wrist]}
    matrices before and after -> the joints' places (worst cm, at), the
    hand's turn (deg), the arm's roll - the shoulder's and elbow's turn
    (worst deg, at). Pure."""
    cm = hand = roll = 0.0
    cm_at = roll_at = None
    for frame in sorted(before):
        pairs = list(zip(before[frame], after.get(frame, [])))
        for i, (a, b) in enumerate(pairs):
            d = (position(a) - position(b)).length()
            if d > cm:
                cm, cm_at = d, frame
            turn = angle(a, b)
            if i == 2:
                hand = max(hand, turn)
            elif turn > roll:
                roll, roll_at = turn, frame
    return Measure(cm, cm_at, hand, roll, roll_at)


def switched_message(side, mode, span, m, notes):
    """What the press did, measured (`Measure`). Pure."""
    start, end, ranged = span
    where = ("over the range %d..%d" if ranged else "over %d..%d") % (start, end)
    text = "%s to %s %s" % (ARM_LABEL.format(side), mode, where)
    held = m.cm <= TOLERANCE_CM and m.hand <= TOLERANCE_DEG
    if held and m.roll <= TOLERANCE_DEG:
        text += " - the arm kept to %.4f cm, %.3f deg" % (m.cm, max(m.hand, m.roll))
    elif held:
        text += (" - hand and elbow kept to %.3f cm; the FK forearm twist is lost, "
                 "up to %g deg at frame %s (an IK elbow does not twist)" % (
                     m.cm, round(m.roll), m.roll_frame))
    else:
        text += " - the arm moved up to %.2f cm (frame %s), the hand %g deg" % (
            m.cm, m.cm_frame, round(m.hand, 3))
    return text + "".join("; " + note for note in notes)


# ------------------------------------------------------------------ scene

def _one(rig, leaf):
    paths = cmds.ls(maya_rigs.node(rig, leaf), long=True) or []
    return paths[0] if len(paths) == 1 else None


def limb(rig, side):
    """The arm's nodes on `rig` (side "R"/"L"), or (None, refusal)."""
    suffix = "_" + side
    label = ARM_LABEL.format(side)
    blend_node = _one(rig, FKIK_NODE.format(LIMB, side))
    if not blend_node:
        return None, MISSING % (label, FKIK_NODE.format(LIMB, side), maya_rigs.label(rig))
    joints = [cmds.getAttr(blend_node + "." + attr)
              for attr in ("startJoint", "middleJoint", "endJoint")]
    found = {}
    for key, leaves in (("deform", [j + suffix for j in joints]),
                        ("fk", ["FK" + j + suffix for j in joints]),
                        ("fkx", ["FKX" + j + suffix for j in joints]),
                        ("ikx", ["IKX" + j + suffix for j in joints]),
                        ("ik", [IK_CONTROL.format(LIMB, side)]),
                        ("pole", [POLE.format(LIMB, side)]),
                        ("align", [ALIGN.format(joints[2], side)])):
        nodes = []
        for leaf in leaves:
            path = _one(rig, leaf)
            if not path:
                return None, MISSING % (label, leaf, maya_rigs.label(rig))
            nodes.append(path)
        found[key] = nodes
    root_parent = _parent(found["ikx"][0])
    if not root_parent:
        return None, MISSING % (label, "the parent of " + found["ikx"][0].split("|")[-1],
                                maya_rigs.label(rig))
    units = tuple(maya_ikmatch.unit_of(found["ik"][0], attr) for attr in LENGHTS)
    return Limb(side, blend_node + "." + BLEND_ATTR, found["deform"], found["fk"],
                found["fkx"], found["ikx"], found["ik"][0], found["pole"][0],
                found["align"][0], root_parent, units), ""


def _inputs(plug):
    return cmds.listConnections(plug, source=True, destination=False,
                                skipConversionNodes=True) or []


def _curve(plug):
    for node in _inputs(plug):
        if cmds.objectType(node).startswith("animCurve"):
            return node
    return None


def _foreign(plug):
    """What drives `plug` other than an animCurve, or None."""
    for node in _inputs(plug):
        if not cmds.objectType(node).startswith("animCurve"):
            return node
    return None


def blend_values(arm):
    """The blend now plus every key of it."""
    curve = _curve(arm.blend)
    keys = list(cmds.keyframe(curve, query=True, valueChange=True) or []) if curve else []
    return [cmds.getAttr(arm.blend)] + keys


def state(rig, side):
    """FK / IK / None (mixed) for the arm, or None with no such arm."""
    arm, _refusal = limb(rig, side)
    return mode_of(blend_values(arm)) if arm else None


def lenghts(arm):
    """The Lenght attributes this rig's IK control has."""
    return tuple(attr for attr, unit in zip(LENGHTS, arm.units) if unit)


def targets(arm, mode):
    """(node, channels) the switch keys."""
    if mode == FK:
        return [(node, CHANNELS) for node in arm.fk]
    return [(arm.ik, CHANNELS + lenghts(arm)), (arm.pole, TRANSLATE),
            (arm.ikx[0], TRANSLATE)]


def whole_take(arm):
    """Playback range and the keys of every control involved, unsnapped."""
    keys = []
    for node in arm.fk + [arm.ik, arm.pole, arm.ikx[0], arm.blend.split(".")[0]]:
        keys.extend(cmds.keyframe(node, query=True, timeChange=True) or [])
    start = cmds.playbackOptions(query=True, min=True)
    end = cmds.playbackOptions(query=True, max=True)
    if keys:
        start, end = min(start, min(keys)), max(end, max(keys))
    return start, end


def _solve_attrs(arm):
    out = {}
    for node, names in ((arm.ik, IK_SOLVE), (arm.pole, POLE_SOLVE)):
        for name in names:
            if not cmds.attributeQuery(name, node=node, exists=True):
                continue
            plug = node + "." + name
            curve = _curve(plug)
            keys = cmds.keyframe(curve, query=True, valueChange=True) or [] if curve else []
            default = (cmds.attributeQuery(name, node=node, listDefault=True) or [0.0])[0]
            out[plug] = (cmds.getAttr(plug), keys, default)
    return out


def refusal(arm, mode, span, ignore=()):
    """Why `arm` may not be switched to `mode` over `span`, or ''."""
    label = ARM_LABEL.format(arm.side)
    driver = _foreign(arm.blend)
    if driver:
        return DRIVEN % (label, arm.blend.split("|")[-1], driver)
    start, end, ranged = span
    if mode_of(blend_values(arm)) == mode:
        return ALREADY % (label, mode)
    for node, channels in targets(arm, mode):
        if node in ignore:
            continue
        for channel in channels:
            driver = _foreign(node + "." + channel)
            if driver:
                return DRIVEN % (label, node.split("|")[-1] + "." + channel, driver)
    if mode == IK and ranged:
        off = off_default(_solve_attrs(arm))
        if off:
            return SOLVE_IN_RANGE % (label, ", ".join(p.split("|")[-1] for p in off))
    return ""


def _world(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def _parent(node):
    return (cmds.listRelatives(node, parent=True, fullPath=True) or [None])[0]


def _seed(node, channels, frame):
    """The channels' values at `frame` - where the new curve starts from."""
    return [cmds.getAttr(node + "." + ch, time=frame) for ch in channels]


def _reset_solve(arm):
    """The solve attributes to their defaults, their keys cut; names them."""
    notes = []
    for plug in off_default(_solve_attrs(arm)):
        node, name = plug.rsplit(".", 1)
        default = (cmds.attributeQuery(name, node=node, listDefault=True) or [0.0])[0]
        cmds.cutKey(plug, clear=True)
        cmds.setAttr(plug, default)
        notes.append("%s reset to %g" % (plug.split("|")[-1], default))
    return notes


def _write(plug, frames, values, span, locked):
    """Keys for `plug` over the span; a whole take's constant channel becomes
    a plain value."""
    if locked:
        return
    start, end, ranged = span
    if ranged:
        cmds.cutKey(plug, time=(start, end), clear=True)
    else:
        cmds.cutKey(plug, clear=True)
        if max(values) - min(values) <= CONSTANT:
            value = sum(values) / len(values)
            cmds.setAttr(plug, 0.0 if abs(value) < CONSTANT else value)
            return
    node, channel = plug.rsplit(".", 1)
    for frame, value in zip(frames, values):
        cmds.setKeyframe(node, attribute=channel, time=frame, value=value)


def _write_blend(arm, mode, span):
    start, end, ranged = span
    target = BLEND[mode]
    if not ranged:
        cmds.cutKey(arm.blend, clear=True)
        cmds.setAttr(arm.blend, target)
        return
    node, attr = arm.blend.rsplit(".", 1)
    outside = {start - 1: cmds.getAttr(arm.blend, time=start - 1),
               end + 1: cmds.getAttr(arm.blend, time=end + 1)}
    had_curve = bool(_curve(arm.blend))
    cmds.cutKey(arm.blend, time=(start, end), clear=True)
    for frame, value, step in blend_keys(start, end, target):
        if value is None:
            if had_curve:
                cmds.setKeyframe(node, attribute=attr, time=frame, insert=True)
            else:
                cmds.setKeyframe(node, attribute=attr, time=frame, value=outside[frame])
        else:
            cmds.setKeyframe(node, attribute=attr, time=frame, value=value)
    for frame, value, step in blend_keys(start, end, target):
        if step:
            cmds.keyTangent(arm.blend, time=(frame, frame), outTangentType="step")


def _goto(frame):
    cmds.currentTime(frame, update=True)


def _sample(arm, frames):
    """One walk over the frames (each costs a whole rig evaluation - 14 ms
    on Manny live; `currentTime -update 0` is 12x faster and reads stale
    values, measured, in parallel and in DG alike): what the arm shows (the
    FKX and IKX chains blended as the rig blends them), the deformation
    joints (for the measure after), the rigid pieces of the FK chain
    between the joints, the IK control's and the pole's parents (sampled:
    nothing assumes they stand still), and the pole's side off the IK chain
    as it stands on the first frame."""
    s = dict((key, {}) for key in ("shown", "deform", "fk_parent", "chain",
                                   "ik_parent", "pole_parent", "root_parent"))
    extras = [_parent(node) for node in arm.fk]
    ik_parent, pole_parent = _parent(arm.ik), _parent(arm.pole)
    for frame in frames:
        _goto(frame)
        if "side" not in s:
            a, b, c = (position(_world(j)) for j in arm.ikx)
            s["side"] = pole_side(position(_world(arm.pole)), a, b, c,
                                  rotation_only(_world(arm.ikx[1])))
        weight = cmds.getAttr(arm.blend) / BLEND[IK]
        s["shown"][frame] = [blended(_world(fk), _world(ik), weight)
                             for fk, ik in zip(arm.fkx, arm.ikx)]
        s["deform"][frame] = [_world(node) for node in arm.deform]
        s["fk_parent"][frame] = _world(extras[0])
        s["chain"][frame] = [None] + [_world(extras[i]) * _world(arm.fkx[i - 1]).inverse()
                                      for i in (1, 2)]
        s["ik_parent"][frame] = _world(ik_parent)
        s["pole_parent"][frame] = _world(pole_parent)
        s["root_parent"][frame] = _world(arm.root_parent)
    return s


def _to_fk(arm, frames, samples, span):
    shown, fk_parent, chain = samples["shown"], samples["fk_parent"], samples["chain"]
    fkx_in_ctrl = [_world(fkx) * _world(ctrl).inverse()
                   for fkx, ctrl in zip(arm.fkx, arm.fk)]
    values = dict(((node, ch), []) for node in arm.fk for ch in CHANNELS)
    seed = frames[0] - 1 if span[2] else frames[0]
    previous = [_seed(node, ROTATE, seed) for node in arm.fk]
    for frame in frames:
        locals_ = fk_locals(shown[frame], fk_parent[frame], chain[frame], fkx_in_ctrl)
        for i, node in enumerate(arm.fk):
            order = cmds.getAttr(node + ".rotateOrder")
            t, r = local_channels(locals_[i], order, previous[i])
            previous[i] = r
            for ch, v in zip(CHANNELS, t + r):
                values[(node, ch)].append(v)
    return values


def _to_ik(arm, frames, samples, span):
    """The IK control on the shown wrist, the pole on the shown plane."""
    side = samples["side"]
    if side is None:
        return None, NO_POLE_SIDE % ARM_LABEL.format(arm.side)
    k = _world(arm.align) * _world(arm.fkx[2]).inverse()
    order = cmds.getAttr(arm.ik + ".rotateOrder")
    seed = frames[0] - 1 if span[2] else frames[0]
    previous = _seed(arm.ik, ROTATE, seed)
    values = dict(((arm.ik, ch), []) for ch in CHANNELS + lenghts(arm))
    values.update(((arm.pole, ch), []) for ch in TRANSLATE)
    values.update(((arm.ikx[0], ch), []) for ch in TRANSLATE)
    for frame in frames:
        d_s, d_e, d_w = samples["shown"][frame]
        # the chain's shape: its root on the shown shoulder, its two segments the shown ones
        root_parent = samples["root_parent"][frame]
        for ch, v in zip(TRANSLATE, maya_ikmatch.local_point(position(d_s), root_parent)):
            values[(arm.ikx[0], ch)].append(v)
        scale = maya_ikmatch.scale_of(root_parent)
        for attr, (a, b), unit in zip(LENGHTS, ((d_s, d_e), (d_e, d_w)), arm.units):
            if unit:
                values[(arm.ik, attr)].append(
                    maya_ikmatch.lenght(position(a), position(b), unit, scale))
        local = (k * d_w) * samples["ik_parent"][frame].inverse()
        t, r = local_channels(local, order, previous)
        previous = r
        for ch, v in zip(CHANNELS, t + r):
            values[(arm.ik, ch)].append(v)
        point = pole_point(position(d_s), position(d_e), position(d_w),
                           rotation_only(d_e), side)
        p = om.MPoint(point) * samples["pole_parent"][frame].inverse()
        for ch, v in zip(TRANSLATE, (p.x, p.y, p.z)):
            values[(arm.pole, ch)].append(v)
    return values, ""


def switch(arm, mode, span):
    """Bring `arm` to `mode` over `span` keeping what it shows. The caller
    has checked `refusal` and holds the undo chunk. Returns the status."""
    start, end, ranged = span
    frames = list(range(start, end + 1))
    now = cmds.currentTime(query=True)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    _suspend(True)
    notes = []
    try:
        samples = _sample(arm, frames)
        if mode == FK:
            values = _to_fk(arm, frames, samples, span)
        else:
            if not ranged:
                notes.extend(_reset_solve(arm))
            if any(".followArm " in note for note in notes):
                # the pole's parent rode the IK control: read it again
                pole_parent = _parent(arm.pole)
                for frame in frames:
                    _goto(frame)
                    samples["pole_parent"][frame] = _world(pole_parent)
            values, text = _to_ik(arm, frames, samples, span)
            if values is None:
                return text
        if mode == IK:
            maya_ikmatch.keep(arm.ikx[0])        # its rest, for the next retarget's reset
        for (node, channel), series in values.items():
            plug = node + "." + channel
            _write(plug, frames, series, span, cmds.getAttr(plug, lock=True))
        _write_blend(arm, mode, span)
        after = {}
        for frame in frames:
            _goto(frame)
            after[frame] = [_world(node) for node in arm.deform]
        moved = measure(samples["deform"], after)
    finally:
        _goto(now)
        cmds.autoKeyframe(state=auto)
        _suspend(False)
    return switched_message(arm.side, mode, span, moved, notes)


def _suspend(on):
    """The viewport's redraw off for the frame walk (best effort)."""
    try:
        cmds.refresh(suspend=on)
    except Exception:                                        # noqa: BLE001
        pass
