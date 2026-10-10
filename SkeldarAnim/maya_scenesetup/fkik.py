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

Every euler is the one nearest the key before (trap 108); a whole-take
channel that comes out constant collapses to a plain value; the blend is
unkeyed at 0 / 10 over a whole take and keyed stepped around a range. The
result is MEASURED on the deformation joints against their samples - the
joints' places, the hand's turn, the arm's roll - and said.

## Keys where the arm has keys (2026-10-08)

«если на ФК руке 3 ключа то и на ИК тоже должно быть 3 ключа и наоборот».
The switch keys only the frames that something moving the SHOWN arm is
keyed on: every time curve upstream of the source chain's world matrices
(`driving_curves`: the arm's own controls, and what it hangs on - clavicle,
spine, pelvis, Main, an animation layer, a constraint's weights), over a
range its keys inside plus the range's two ends (`key_frames`); the new
keys take the source keys' tangent types (`tangents_at`). Nothing keyed
over the whole take: the arm stands still, one plain value. Between keys
each chain interpolates its own way; the measure is at the keys. Hand ->
Weapon still switches on every frame (`every_frame`): a proxy baked on
every frame follows it anyway.

## Legs (2026-10-10)

A leg is the same limb with the toes as a fourth joint (`kind=LEG`, `Limb.tip`: the
toes IK control). The toes are fitted, the pole sits on the shown knee's bend side and
is read after the IK control is written. The spine has its own module (`fkikspine`).
The knee's roll is not held (measured 84 deg with the places exact) - the spec has the
numbers: docs/superpowers/specs/2026-10-10-legs-spine-fkik-design.md

Spec: docs/superpowers/specs/2026-09-30-connections-fkik-switch-design.md,
docs/superpowers/specs/2026-10-08-fkik-keys-only-design.md
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
ARM, LEG, SPINE = "Arm", "Leg", "Spine"
KINDS = (ARM, LEG)                   # the limbs with a blend per side; the spine is its own (`fkikspine`)
FKIK_NODE = "FKIK{0}_{1}"            # FKIKArm_R, FKIKLeg_R
BLEND_ATTR = "FKIKBlend"
IK_CONTROL = "IK{0}_{1}"             # IKArm_R, IKLeg_R
POLE = "Pole{0}_{1}"                 # PoleArm_R, PoleLeg_R
ALIGN = "AlignIKTo{0}_{1}"           # AlignIKToWrist_R, AlignIKToAnkle_R
# a leg's toes: the fourth joint of the chain, and its own IK control (`Limb.tip`)
TOES = "Toes"
TOES_IK = "IKToes_{0}"
TOES_ALIGN = "AlignIKToToes_{0}"
TRANSLATE = ("translateX", "translateY", "translateZ")
ROTATE = ("rotateX", "rotateY", "rotateZ")
CHANNELS = TRANSLATE + ROTATE
# what a matched IK needs at its default (AS resets every custom attribute); the lengths
# are not among them since 2026-10-02 - they are the source's (`maya_ikmatch`)
IK_SOLVE = ("swivel", "antiPop", "stretchy")
LENGHTS = maya_ikmatch.LENGHTS
POLE_SOLVE = {ARM: ("followArm", "lock"), LEG: ("followLeg", "lock")}
NUDGE = 0.002                        # of the limb's length (maya_pmretarget)
CONSTANT = 1e-6
TOLERANCE_CM = 0.05                  # "kept" below these, "moved" above: the pole's
                                     # nudge leaves an IK elbow 0.02-0.05 cm off
TOLERANCE_DEG = 0.05
KEY_TOLERANCE = 1e-4                 # key times closer than this (frames) are one key
TIP_TOLERANCE = math.radians(0.01)   # the toes solve stops once within this
TIP_STEP = 0.25                      # deg: the probe that measures the toes' sensitivity
TIP_TRIES = 6                        # Newton steps a frame may take
# the fits (a leg's pole, the spine's spline): one residual of places and turns
FIT_STEP = 0.05                      # the probe of a control's sensitivity (cm, or deg)
FIT_TOLERANCE = 0.005                # stop once the residual's RMS is this small
FIT_TRIES = 8                        # Gauss-Newton steps a frame may take
FIT_DAMP = 1e-3                      # Levenberg damping on JtJ
ORIENT_WEIGHT = 30.0                 # cm per radian of turn in a residual (a bone's length)
TIME_CURVES = ("animCurveTL", "animCurveTA", "animCurveTT", "animCurveTU")


def _names(pairs, axes="XYZ"):
    """Long and short names of compound attributes and their children."""
    out = set()
    for long_name, short in pairs:
        out.update((long_name, short))
        for axis in axes:
            out.update((long_name + axis, short + axis.lower()))
    return out


# what moves a transform's matrix: its own channels (a joint's included)
MATRIX_INPUTS = frozenset(
    _names((("translate", "t"), ("rotate", "r"), ("scale", "s"), ("rotateAxis", "ra"),
            ("jointOrient", "jo"), ("rotatePivot", "rp"), ("rotatePivotTranslate", "rpt"),
            ("scalePivot", "sp"), ("scalePivotTranslate", "spt"), ("inverseScale", "is")))
    | _names((("shear", "sh"),), axes=("XY", "XZ", "YZ"))
    | {"rotateOrder", "ro", "offsetParentMatrix", "opm", "segmentScaleCompensate", "ssc"})
# what a constraint or a matrix node reads off a transform: its matrices and channels
MATRIX_OUTPUTS = MATRIX_INPUTS | frozenset(
    ("worldMatrix", "wm", "worldInverseMatrix", "wim", "parentMatrix", "pm",
     "parentInverseMatrix", "pim", "matrix", "m", "inverseMatrix", "im", "xformMatrix", "xm",
     "dagLocalMatrix", "dlm", "dagLocalInverseMatrix", "dlim"))

LABEL = {ARM: "Arm_{0}", LEG: "Leg_{0}", SPINE: "Spine"}
# the words the message uses for each kind: what the limb is, its end, what is kept, what is
# lost in the roll and why (an IK elbow is a hinge; a leg's knee frame is the IK knee's own)
ROLL_WORDS = {
    ARM: {"what": "arm", "end": "hand", "kept": "hand and elbow",
          "lost": "the FK forearm twist is lost", "why": "an IK elbow does not twist"},
    LEG: {"what": "leg", "end": "foot", "kept": "hip, knee, ankle and toes",
          "lost": "the knee's roll differs", "why": "the IK knee's frame is its own"},
    SPINE: {"what": "spine", "end": "top", "kept": "the spine's joints",
            "lost": "the spine's roll differs", "why": "the IK spine is a spline"},
}
ALREADY = "%s is already %s"
MISSING = "%s: %s not found on %s"
DRIVEN = "%s: %s is driven by %s - not a key the switch can rewrite"
SOLVE_IN_RANGE = ("%s: %s not at the default - switch the whole take (no "
                  "highlight) to reset it, or zero it first")
NO_POLE_SIDE = "%s: the IK pole stands on the limb's line - no bend plane to read"

# kind   -- ARM or LEG; `LABEL[kind]` names it in the messages
# deform, fk, fkx, ikx -- one entry per joint of the chain: three for an arm (shoulder,
#           elbow, wrist), four for a leg (hip, knee, ankle, toes)
# tip    -- a leg's toes IK control and its align (`Tip`), None for an arm
# root_parent -- what the IK chain's root joint stands in (IKXOffset<Shoulder>);
# units  -- the IK segments' rest lengths behind Lenght1/2 (`maya_ikmatch.unit_of`)
Limb = namedtuple("Limb", "side blend deform fk fkx ikx ik pole align root_parent units "
                          "kind tip", defaults=(ARM, None))
Tip = namedtuple("Tip", "ik align")


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


def key_frames(times, span, tolerance=KEY_TOLERANCE):
    """The frames a keys-only switch keys: every key time once over a whole
    take; over a range the key times inside it plus its first and last
    frame (the blend steps there). Pure."""
    start, end, ranged = span
    pool = sorted(float(t) for t in times)
    if ranged:
        pool = sorted([float(start), float(end)] +
                      [t for t in pool if start - tolerance <= t <= end + tolerance])
    out = []
    for t in pool:
        if not out or t - out[-1] > tolerance:
            out.append(t)
    return out


def tangent_for(own, every):
    """(in, out) tangent types for a new key from the source keys' pairs:
    the arm's own controls' when there are any, else every curve's; a type
    where all agree, never `fixed` (its angle is the other curve's), else
    None - Maya's default. Pure."""
    pool = own or every
    out = []
    for i in (0, 1):
        kinds = set(pair[i] for pair in pool)
        kind = kinds.pop() if len(kinds) == 1 else None
        out.append(None if kind == "fixed" else kind)
    return tuple(out)


def _pairs_on(keys, frame, tolerance):
    return [(i, o) for curve in keys for t, i, o in curve if abs(t - frame) <= tolerance]


def _pairs_inside(keys, frame, tolerance):
    """A frame no source key stands on lies in each curve's segment after
    its key before: that key's out type is the segment's."""
    out = []
    for curve in keys:
        before = [o for t, _i, o in curve if t < frame - tolerance]
        if before:
            out.append((None, before[-1]))
    return out


def tangents_at(own, every, frame, tolerance=KEY_TOLERANCE):
    """(in, out) types for a new key at `frame` from the source curves' keys
    ([[(time, in, out)], ...], the arm's own and every walked curve): the
    keys ON the frame, else - a range's end - the segments it lies in. Pure."""
    on_own, on_every = _pairs_on(own, frame, tolerance), _pairs_on(every, frame, tolerance)
    if on_own or on_every:
        return tangent_for(on_own, on_every)
    return tangent_for(_pairs_inside(own, frame, tolerance),
                       _pairs_inside(every, frame, tolerance))


def attr_root(plug):
    """`node.worldMatrix[0]` -> worldMatrix, `node.translate.translateX` ->
    translate, a bare attribute name -> itself. Pure."""
    attr = plug.split(".", 1)[1] if "." in plug else plug
    return attr.split(".")[0].split("[")[0]


def moves_matrix(attr):
    """Whether a transform's input `attr` moves its matrix. Pure."""
    return attr_root(attr) in MATRIX_INPUTS


def matrix_output(attr):
    """Whether reading a transform's `attr` reads where it stands (its matrices,
    its channels) rather than a value of its own. Pure."""
    return attr_root(attr) in MATRIX_OUTPUTS


def sources(arm, mode):
    """What the arm shows in `mode` (FK / IK / None for a mixed take): (the
    DAG nodes whose world matrices it is, plugs read beside them, the arm's
    own controls - whose keys decide tangents first). Pure."""
    ik_own = _ik_controls(arm)
    fk_nodes, ik_nodes = list(arm.fkx), list(arm.ikx) + ik_own
    if mode == FK:
        return fk_nodes, [], list(arm.fk)
    if mode == IK:
        return ik_nodes, [], ik_own
    return fk_nodes + ik_nodes, [arm.blend], list(arm.fk) + ik_own


def _ik_controls(arm):
    """The IK controls of a limb: the end control, the pole and - a leg's -
    the toes control."""
    out = [arm.ik, arm.pole]
    if arm.tip:
        out.append(arm.tip.ik)
    return out


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


def rotation_vector(target, current):
    """The world rotation (radians, as a vector) that turns `current` onto
    `target` - both matrices. Pure."""
    q = (om.MTransformationMatrix(target).rotation(asQuaternion=True) *
         om.MTransformationMatrix(current).rotation(asQuaternion=True).inverse())
    if q.w < 0:
        q = om.MQuaternion(-q.x, -q.y, -q.z, -q.w)
    w = max(-1.0, min(1.0, q.w))
    s = math.sqrt(max(0.0, 1.0 - w * w))
    if s < 1e-9:
        return om.MVector(2.0 * q.x, 2.0 * q.y, 2.0 * q.z)
    return om.MVector(q.x, q.y, q.z) * (2.0 * math.acos(w) / s)


def solve3(columns, rhs):
    """The x with x0*columns[0] + x1*columns[1] + x2*columns[2] = rhs (3-vectors),
    by Cramer's rule; None when the columns are degenerate. Pure."""
    def det(a, b, c):
        return (a.x * (b.y * c.z - b.z * c.y) - b.x * (a.y * c.z - a.z * c.y)
                + c.x * (a.y * b.z - a.z * b.y))
    d = det(*columns)
    if abs(d) < 1e-12:
        return None
    return [det(*[rhs if j == i else columns[j] for j in range(3)]) / d for i in range(3)]


def solve_linear(a, b):
    """x with a x = b, Gaussian elimination with partial pivoting; None when
    singular. Pure."""
    n = len(b)
    m = [list(row) + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-18:
            return None
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            if f:
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))) / m[r][r]
    return x


def gauss_newton_step(jacobian, residual, damp=FIT_DAMP):
    """The step dx minimising |residual + J dx|^2 with Levenberg damping:
    (JtJ + damp I) dx = -Jt r. `jacobian` is a list of rows (one per residual).
    None when the system is singular. Pure."""
    n = len(jacobian[0])
    jtj = [[sum(row[i] * row[j] for row in jacobian) + (damp if i == j else 0.0)
            for j in range(n)] for i in range(n)]
    jtr = [sum(row[i] * residual[k] for k, row in enumerate(jacobian)) for i in range(n)]
    return solve_linear(jtj, [-v for v in jtr])


def joint_residual(matrices, targets):
    """A fit's residual for a chain of joints: each joint's place (cm) and its turn
    (ORIENT_WEIGHT cm per radian) against its target matrix. Pure over the matrices."""
    out = []
    for current, goal in zip(matrices, targets):
        d = position(current) - position(goal)
        turn = rotation_vector(goal, current) * ORIENT_WEIGHT
        out.extend([d.x, d.y, d.z, turn.x, turn.y, turn.z])
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


def bend_side(s, e, w):
    """The shown knee's own bend: its offset from the hip-ankle line, perpendicular
    to it, as a unit vector - None while the leg is straight (no bend to read).
    Pure."""
    base, length = _on_line(s, e, w)
    line = (w - s).normal()
    side = (e - base) - line * ((e - base) * line)
    if side.length() <= 1e-6 * length:
        return None
    return side.normal()


def pole_on_side(s, e, w, bend):
    """The pole exactly on the bend side: a limb out from the hip-ankle line at the
    knee's share, along `bend` (unit, from `bend_side`). The IK plane then holds the
    shown knee. Pure."""
    base, length = _on_line(s, e, w)
    return base + bend * length


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
    """How far the shown limb moved: {frame: [joint matrices]} before and after
    -> the joints' places (worst cm, at), the end's turn (deg; the wrist, the
    ankle and toes of a leg - the third joint on), the limb's roll - the
    upper joints' turn (worst deg, at). Pure."""
    cm = hand = roll = 0.0
    cm_at = roll_at = None
    for frame in sorted(before):
        pairs = list(zip(before[frame], after.get(frame, [])))
        for i, (a, b) in enumerate(pairs):
            d = (position(a) - position(b)).length()
            if d > cm:
                cm, cm_at = d, frame
            turn = angle(a, b)
            if i >= 2:
                hand = max(hand, turn)
            elif turn > roll:
                roll, roll_at = turn, frame
    return Measure(cm, cm_at, hand, roll, roll_at)


def _frame_text(t):
    t = float(t)
    return str(int(t)) if t == int(t) else ("%.3f" % t).rstrip("0").rstrip(".")


def switched_message(side, mode, span, m, notes, keys=None, kind=ARM):
    """What the press did, measured (`Measure`); `keys` the frames keyed by a
    keys-only switch (None: every frame of the span). Pure."""
    start, end, ranged = span
    label = LABEL[kind].format(side)
    if keys is None:
        where = ("over the range %d..%d" if ranged else "over %d..%d") % (start, end)
        text = "%s to %s %s" % (label, mode, where)
    elif not keys:
        text = "%s to %s, no keys - nothing keyed moves the arm" % (label, mode)
    else:
        count = "%d key%s" % (len(keys), "" if len(keys) == 1 else "s")
        if ranged:
            text = "%s to %s over the range %d..%d on %s" % (label, mode, start, end, count)
        else:
            frames = _frame_text(keys[0]) if len(keys) == 1 else "%s..%s" % (
                _frame_text(keys[0]), _frame_text(keys[-1]))
            text = "%s to %s on %s (%s)" % (label, mode, count, frames)
    held = m.cm <= TOLERANCE_CM and m.hand <= TOLERANCE_DEG
    words = ROLL_WORDS[kind]
    if held and m.roll <= TOLERANCE_DEG:
        text += " - the %s kept to %.4f cm, %.3f deg" % (words["what"], m.cm,
                                                          max(m.hand, m.roll))
    elif held:
        text += (" - %s kept to %.3f cm; %s, up to %g deg at frame %s (%s)" % (
            words["kept"], m.cm, words["lost"], round(m.roll), m.roll_frame, words["why"]))
    else:
        text += " - the %s moved up to %.2f cm (frame %s), the %s %g deg" % (
            words["what"], m.cm, m.cm_frame, words["end"], round(m.hand, 3))
    return text + "".join("; " + note for note in notes)


# ------------------------------------------------------------------ scene

def _one(rig, leaf):
    paths = cmds.ls(maya_rigs.node(rig, leaf), long=True) or []
    return paths[0] if len(paths) == 1 else None


def limb(rig, side, kind=ARM):
    """The arm's (or, kind=LEG, the leg's) nodes on `rig` (side "R"/"L"), or
    (None, refusal)."""
    suffix = "_" + side
    label = LABEL[kind].format(side)
    blend_node = _one(rig, FKIK_NODE.format(kind, side))
    if not blend_node:
        return None, MISSING % (label, FKIK_NODE.format(kind, side), maya_rigs.label(rig))
    joints = [cmds.getAttr(blend_node + "." + attr)
              for attr in ("startJoint", "middleJoint", "endJoint")]
    chain = joints + [TOES] if kind == LEG else joints
    found = {}
    checks = [("deform", [j + suffix for j in chain]),
              ("fk", ["FK" + j + suffix for j in chain]),
              ("fkx", ["FKX" + j + suffix for j in chain]),
              ("ikx", ["IKX" + j + suffix for j in chain]),
              ("ik", [IK_CONTROL.format(kind, side)]),
              ("pole", [POLE.format(kind, side)]),
              ("align", [ALIGN.format(joints[2], side)])]
    if kind == LEG:
        checks.append(("tip", [TOES_IK.format(side), TOES_ALIGN.format(side)]))
    for key, leaves in checks:
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
    tip = Tip(found["tip"][0], found["tip"][1]) if kind == LEG else None
    return Limb(side, blend_node + "." + BLEND_ATTR, found["deform"], found["fk"],
                found["fkx"], found["ikx"], found["ik"][0], found["pole"][0],
                found["align"][0], root_parent, units, kind, tip), ""


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
    out = [(arm.ik, CHANNELS + lenghts(arm)), (arm.pole, TRANSLATE),
           (arm.ikx[0], TRANSLATE)]
    if arm.tip:
        out.append((arm.tip.ik, ROTATE))
    return out


def whole_take(arm):
    """Playback range and the keys of every control involved, unsnapped."""
    keys = []
    for node in arm.fk + _ik_controls(arm) + [arm.ikx[0], arm.blend.split(".")[0]]:
        keys.extend(cmds.keyframe(node, query=True, timeChange=True) or [])
    start = cmds.playbackOptions(query=True, min=True)
    end = cmds.playbackOptions(query=True, max=True)
    if keys:
        start, end = min(start, min(keys)), max(end, max(keys))
    return start, end


def _solve_attrs(arm):
    out = {}
    for node, names in ((arm.ik, IK_SOLVE), (arm.pole, POLE_SOLVE[arm.kind])):
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
    label = LABEL[arm.kind].format(arm.side)
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


def driving_curves(nodes, plugs=()):
    """Every time curve that can move the world matrices of `nodes` (and the
    values of `plugs`): a transform's matrix inputs and its parent, the IK
    handles a joint starts, a compute node's (DG, constraint, shape, handle)
    every input and its parent, a transform's own attribute read by
    something (`IKArm.Lenght1`, a follow) - that attribute's input. Driven
    keys are not time: their driver is followed. A set of curve names."""
    curves = set()
    seen = set()
    long_of = {}
    type_of = {}

    def full(node):
        if node not in long_of:
            found = cmds.ls(node, long=True) or [node]
            long_of[node] = found[0]
        return long_of[node]

    def kind(node):
        if node not in type_of:
            type_of[node] = cmds.nodeType(node)
        return type_of[node]

    todo = [("dag", full(n)) for n in nodes] + [("plug", p) for p in plugs]

    def take(source):
        node = source.split(".", 1)[0]
        t = kind(node)
        if t in TIME_CURVES:
            curves.add(node)
        elif t in ("transform", "joint"):
            todo.append(("dag", full(node)) if matrix_output(source) else ("plug", source))
        else:
            todo.append(("all", full(node)))

    while todo:
        how, item = todo.pop()
        if (how, item) in seen:
            continue
        seen.add((how, item))
        if how == "plug":
            for source in cmds.listConnections(item, source=True, destination=False,
                                               plugs=True) or []:
                take(source)
            continue
        node = item
        if how == "dag" and kind(node) not in ("transform", "joint"):
            how = "all"
        parent = _parent(node) if cmds.objectType(node, isAType="dagNode") else None
        if parent:
            todo.append(("dag", parent))
        pairs = cmds.listConnections(node, source=True, destination=False, connections=True,
                                     plugs=True) or []
        for dest, source in zip(pairs[0::2], pairs[1::2]):
            if how == "all" or moves_matrix(dest):
                take(source)
        if how == "dag" and kind(node) == "joint":
            for handle in cmds.listConnections(node + ".message", source=False, destination=True,
                                               type="ikHandle") or []:
                todo.append(("all", full(handle)))
    return curves


def _keys_of(curve):
    """[(time, in type, out type)] of a curve's keys."""
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    ins = cmds.keyTangent(curve, query=True, inTangentType=True) or [None] * len(times)
    outs = cmds.keyTangent(curve, query=True, outTangentType=True) or [None] * len(times)
    return list(zip(times, ins, outs))


def key_plan(arm, span):
    """(frames to sample, frames keyed, {frame: (in, out) tangent types}) of
    a keys-only switch: the keys of what moves the arm it shows."""
    nodes, plugs, own = sources(arm, mode_of(blend_values(arm)))
    curves = driving_curves(nodes, plugs)
    table = dict((curve, _keys_of(curve)) for curve in curves)
    own_set = set(_long(node) for node in own)
    mine = [table[c] for c in curves
            if own_set & set(_long(node) for node in cmds.listConnections(
                c + ".output", source=False, destination=True) or [])]
    every = list(table.values())
    keys = key_frames([t for curve in every for t, _i, _o in curve], span)
    tangents = dict((frame, tangents_at(mine, every, frame)) for frame in keys)
    frames = keys or [cmds.currentTime(query=True)]
    return frames, keys, tangents


def _long(node):
    found = cmds.ls(node, long=True) if node else None   # never ls() of nothing: that lists all
    return found[0] if found else node


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


def _unkey(plug, span):
    """The plug's keys in the span cut (the whole take when not ranged)."""
    start, end, ranged = span
    if ranged:
        cmds.cutKey(plug, time=(start, end), clear=True)
    else:
        cmds.cutKey(plug, clear=True)


def _write(plug, frames, values, span, locked, tangents=None):
    """Keys for `plug` on the frames; a whole take's constant channel becomes
    a plain value. `tangents` {frame: (in, out)}: a type None is Maya's
    default."""
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
        flags = {}
        in_type, out_type = (tangents or {}).get(frame, (None, None))
        if in_type:
            flags["inTangentType"] = in_type
        if out_type:
            flags["outTangentType"] = out_type
        try:
            cmds.setKeyframe(node, attribute=channel, time=frame, value=value, **flags)
        except (RuntimeError, TypeError):                    # a type this key cannot take
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
            a, b, c = (position(_world(j)) for j in arm.ikx[:3])
            s["side"] = pole_side(position(_world(arm.pole)), a, b, c,
                                  rotation_only(_world(arm.ikx[1])))
        weight = cmds.getAttr(arm.blend) / BLEND[IK]
        s["shown"][frame] = [blended(_world(fk), _world(ik), weight)
                             for fk, ik in zip(arm.fkx, arm.ikx)]
        s["deform"][frame] = [_world(node) for node in arm.deform]
        s["fk_parent"][frame] = _world(extras[0])
        s["chain"][frame] = [None] + [_world(extras[i]) * _world(arm.fkx[i - 1]).inverse()
                                      for i in range(1, len(extras))]
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
    """The IK control on the shown wrist, and the chain's root and lengths. The pole
    is `_pole_values`' - it needs the IK control written first."""
    k = _world(arm.align) * _world(arm.fkx[2]).inverse()
    order = cmds.getAttr(arm.ik + ".rotateOrder")
    seed = frames[0] - 1 if span[2] else frames[0]
    previous = _seed(arm.ik, ROTATE, seed)
    values = dict(((arm.ik, ch), []) for ch in CHANNELS + lenghts(arm))
    values.update(((arm.ikx[0], ch), []) for ch in TRANSLATE)
    for frame in frames:
        d_s, d_e, d_w = samples["shown"][frame][:3]
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
    return values, ""


def _pole_refusal(arm, frames, samples):
    """Why no pole can stand on the shown plane, or '' - checked before anything is
    written. An arm needs the rest pole off the line; a leg needs either that or a
    bend on every frame. Pure."""
    if samples["side"] is not None:
        return ""
    for frame in frames:
        d_s, d_e, d_w = samples["shown"][frame][:3]
        if arm.kind != LEG or bend_side(position(d_s), position(d_e), position(d_w)) is None:
            return NO_POLE_SIDE % LABEL[arm.kind].format(arm.side)
    return ""


def _pole_values(arm, frames, samples):
    """The pole's translate on the shown plane, frame by frame. The pole's parent
    must be read AFTER the IK control is written (a leg's pole rides the IK leg,
    `followLeg`: measured 2026-10-10, the pole 31 cm off when read before) - the
    caller does that. `_pole_refusal` has passed before this runs: every frame has a
    bend side, or the rest pole stands off the line. Returns {(pole, channel): [values]}."""
    side = samples["side"]
    values = dict(((arm.pole, ch), []) for ch in TRANSLATE)
    for frame in frames:
        d_s, d_e, d_w = samples["shown"][frame][:3]
        bend = bend_side(position(d_s), position(d_e), position(d_w)) if arm.kind == LEG \
            else None
        if bend is not None:
            # a leg's knee bends about its own hinge: the bend side of the shown knee THIS
            # frame, not the rest pole's carried through the knee's turn (that plane turns
            # with the bend and misplaces the knee - measured 2026-10-10). The pole stands
            # exactly on that side, so the knee is in the shown plane.
            point = pole_on_side(position(d_s), position(d_e), position(d_w), bend)
        else:
            point = pole_point(position(d_s), position(d_e), position(d_w),
                               rotation_only(d_e), side)
        p = om.MPoint(point) * samples["pole_parent"][frame].inverse()
        for ch, v in zip(TRANSLATE, (p.x, p.y, p.z)):
            values[(arm.pole, ch)].append(v)
    return values


def _set_rotate(node, angles):
    for ch, value in zip(ROTATE, angles):
        cmds.setAttr(node + "." + ch, value)


def _fit_toes(arm, frames, samples, span):
    """The toes' IK control, frame by frame: the three rotate channels that turn
    the IK toes joint (`Limb.tip`'s chain end, IKXToes) onto the shown toes.

    The toes are not a wrist: a toes control's rest frame is its FK control's,
    not the toes joint's, so no fixed relation holds (measured 2026-10-10: the
    rest pose read 177 deg off). The rotation is found the way the rig makes it:
    each frame, the joint's orientation read from the evaluated scene, the
    sensitivity of that orientation to each channel probed by a small step, and
    a Newton step - a few evaluations a frame. The control's own keys are cut
    first (a keyed channel does not take a setAttr), the values come back as
    keys in the caller. Returns ({(control, channel): [values]}, worst error
    in degrees)."""
    tip = arm.tip
    joint = arm.ikx[3]
    seed = frames[0] - 1 if span[2] else frames[0]
    angles = list(_seed(tip.ik, ROTATE, seed))
    out = dict(((tip.ik, ch), []) for ch in ROTATE)
    worst = 0.0
    for frame in frames:
        _goto(frame)
        target = samples["shown"][frame][3]
        for _ in range(TIP_TRIES):
            _set_rotate(tip.ik, angles)
            current = _world(joint)
            error = rotation_vector(target, current)
            if error.length() <= TIP_TOLERANCE:
                break
            columns = []
            for i in range(3):
                probe = list(angles)
                probe[i] += TIP_STEP
                _set_rotate(tip.ik, probe)
                # radians of turn per degree of channel: the probe moved TIP_STEP degrees
                columns.append(rotation_vector(_world(joint), current) / TIP_STEP)
            delta = solve3(columns, error)
            if delta is None:
                break
            angles = [a + d for a, d in zip(angles, delta)]
        _set_rotate(tip.ik, angles)
        residual = rotation_vector(target, _world(joint)).length()
        worst = max(worst, math.degrees(residual))
        for ch, value in zip(ROTATE, angles):
            out[(tip.ik, ch)].append(value)
    return out, worst


def switch(arm, mode, span, every_frame=False):
    """Bring `arm` to `mode` over `span` keeping what it shows - on the
    frames something moving it is keyed on (`key_plan`), or on every frame
    of the span (`every_frame`). The caller has checked `refusal` and holds
    the undo chunk. Returns the status."""
    start, end, ranged = span
    now = cmds.currentTime(query=True)
    if every_frame:
        frames, keys, tangents = list(range(start, end + 1)), None, {}
    else:
        frames, keys, tangents = key_plan(arm, span)
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
            refusal = _pole_refusal(arm, frames, samples)
            if refusal:
                return refusal
            values, text = _to_ik(arm, frames, samples, span)
        if mode == IK:
            maya_ikmatch.keep(arm.ikx[0])        # its rest, for the next retarget's reset
        for (node, channel), series in values.items():
            plug = node + "." + channel
            _write(plug, frames, series, span, cmds.getAttr(plug, lock=True), tangents)
        _write_blend(arm, mode, span)
        if mode == IK:
            # the pole after the IK control: its parent may ride the control (a leg's
            # followLeg), so it is read now, on the frames as they stand
            pole_parent = _parent(arm.pole)
            for frame in frames:
                _goto(frame)
                samples["pole_parent"][frame] = _world(pole_parent)
            pole = _pole_values(arm, frames, samples)
            for (node, channel), series in pole.items():
                plug = node + "." + channel
                _write(plug, frames, series, span, cmds.getAttr(plug, lock=True), tangents)
        if mode == IK and arm.tip:
            # the toes need the IK chain as it now stands, frame by frame (see _fit_toes)
            for ch in ROTATE:
                _unkey(arm.tip.ik + "." + ch, span)
            before_mode = (cmds.evaluationManager(query=True, mode=True) or ["parallel"])[0]
            cmds.evaluationManager(mode="off")
            try:
                fit, worst = _fit_toes(arm, frames, samples, span)
            finally:
                cmds.evaluationManager(mode=before_mode)
            for (node, channel), series in fit.items():
                plug = node + "." + channel
                _write(plug, frames, series, span, cmds.getAttr(plug, lock=True), tangents)
            notes.append("toes solved to %.3f deg" % worst)
        after = {}
        for frame in frames:
            _goto(frame)
            after[frame] = [_world(node) for node in arm.deform]
        moved = measure(samples["deform"], after)
    finally:
        _goto(now)
        cmds.autoKeyframe(state=auto)
        _suspend(False)
    return switched_message(arm.side, mode, span, moved, notes, keys, kind=arm.kind)


def _suspend(on):
    """The viewport's redraw off for the frame walk (best effort)."""
    try:
        cmds.refresh(suspend=on)
    except Exception:                                        # noqa: BLE001
        pass
