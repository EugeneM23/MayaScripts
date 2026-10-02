"""Bone targets -> AdvancedSkeleton control values (the Pose Library, 2026-10-02).

The animator: «если анимация относится к ригу то мы должны сохранять анимацию не контроллов а
костей». A card holds the game skeleton's bones; `posemath.targets` says where every game bone of
the TARGET rig should stand; this module finds the control values that put them there - the
spec's "Onto a rig", `maya_scenesetup.fkik`'s analytic switch generalised from one arm to the
whole rig. Nothing is constrained, nothing baked, `reset_build_pose` is never called; `Main`,
`FKNeck_M.bias`, the neck's twist share and every `FKIK*.FKIKBlend` are read, never written.

## What the rig is (measured 2026-10-02, mayapy standalone, Manny_Rig / Creep_Rig / Orc_D_Rig)

- Every game bone follows an AdvancedSkeleton DEFORMATION joint (D, the target of its orient
  constraint: `pelvis <- Root_M`, `upperarm_l <- Shoulder_L` ...) with a constant offset
  `O_g = rigid(G) . rigid(D)^-1` (orient + point + scale on Manny; orientation only on the Creep
  and the Orc D, the pelvis position too). D follows the drive chain S - the FKX and IKX joints
  blended by `FKIK<Limb>_<side>.FKIKBlend` - standing in one frame with it at build pose
  (<= 1e-5 deg) EXCEPT on the six unrolled bones: Shoulder, Elbow, Hip, Knee, whose constraint
  offsetX the twist network drives (trap 126), and Neck / NeckPart1, whose in-between takes a
  share of the head's twist. Those six are given in DRIVE form (`drive_matrices`: `G . D^-1 .
  S`, the bone with the roll put back) - a card saved from a rig stores them so, and the
  target's own `wanted` for them is in that form too.
- An FK control's FKX joint is a DAG DESCENDANT of the control (`FKShoulder_L > ... >
  FKXShoulder_L`, through `CustomOrientReverse*`), so `L = rigid(FKX) . rigid(C)^-1` is constant
  and the control's world for its joint to stand on `S*` is `L^-1 . S*` - **except the neck**:
  `FKXNeck_M` hangs under `FKOffsetNeck_M` and is a `blendMatrix` (`NeckInbetweenBM_M`) between a
  fixed base and `InbetweenTargetNeck_M`, which rides `FKNeck_M`, its rotate weight
  `remapValue(FKNeck_M.bias)`: measured +20 deg on any axis of `FKNeck_M` turns `FKXNeck_M` by
  exactly 10.0000 at bias 0 and 20.0000 at bias 10, while `FKOffsetNeckPart1_M` (driven by
  `NeckPart1InbetweenDM_M`) takes the full 20 so the head chain keeps the whole turn; rotating
  `FKNeckPart1_M` moves `FKXNeck_M` by 0.000000. So `FKNeck_M` is solved NUMERICALLY (`_numeric`:
  Newton on the world rotation of `FKXNeck_M`, the Jacobian by finite differences, a few
  rounds) and everything below it analytically against its parent read afterwards. Any control
  whose FKX joint is not below it takes the same road (`_analytic`).
- A control's parent space is not a constant piece of anything the solve knows: the finger
  metacarpals hang under `FKParentConstraintToWrist_*` (orient + point constrained to the
  DEFORMATION wrist - the IK wrist in IK), the hips under `FKParentConstraintToRoot_M`,
  `FKSpine5_M` under `...ToSpine4_M`, the head under `FKGlobalHead_M` (its `Global` blend), the
  phalanges under the curl's SDK groups, `FKOffset*` point-constrained to `FKPS2*`. So the solve
  goes **level by level down the GAME skeleton** (its depth, `level_order`; the DAG's depth would
  put a metacarpal - under FKSystem - before the wrist it follows) and reads each control's
  parent world NOW, after the levels above were set (`setAttr`, temporarily). No control carries
  a rotateAxis or a pivot (all three rigs, every control), so a control's world rotation is its
  rotate channels times its parent's; `joint_channels` would take a rotateAxis anyway.
- In mayapy (`evaluationManager -mode off`, DG) a `getAttr` after a `setAttr` is FRESH: the FKX
  joint and the game hand read after a control's `setAttr` equal what `dgdirty -allPlugs` gives.
  A GUI Maya runs the parallel EM, where freshness is not measured yet: `_fresh()` is the one
  switch point (`FRESH_MODE`, the evaluation the solve reads under - "off" by default, switched
  only when the scene is not already there and put back in a `finally`).
- `setAttr` on a keyed channel holds until the next time change, and downstream reads see it -
  so the temporary writes work on a keyed rig, and every one is put back (`_Session`).
- `AlignIKToWrist_*` / `AlignIKToAnkle_*` are DAG children of `FKXWrist_*` / `FKXAnkle_*` and
  stand where `IKArm_*` / `IKLeg_*` do at build pose (0.000001 cm): `K = rigid(AlignIKTo) .
  rigid(FKX)^-1` is the IK end in the drive chain's end, constant. The IK ankle rides `IKLeg`
  rigidly (its offset constant under any IKLeg move), the FKX and IKX joints stand in one
  frame at rest (0.0000 deg, every limb joint, all three rigs). `RootX_M` stands 117.9 deg off
  `Root_M` at rest, its relation to the pelvis constant.
- `IKXToes_*` is NOT rigid with `IKToes_*`: an SC handle under `IKToes` (`IKToesHandle_*`,
  effector at `IKXToesEnd_*`) aims it, and the relation `IKToes . IKXToes^-1` read off the rig
  (176.67 deg, 174.90 on the Orc D) put a 3-axis toe turn 9.88 deg off on the Creep (9.91 Orc D)
  - while the whole turn IS within reach. So the relation is a first guess, finished by the
  numeric solve (`_toes`).
- The pole: `fkik.pole_point` turns the pole's side, read off the IK chain, with the elbow's
  frame; an FK elbow rolled about its bone turns that side out of the bend plane and the IK
  elbow landed 0.059 cm off on Manny. `pole_point` here keeps a bent chain's pole in its own
  plane (0.0002 cm).
- The pole's `followArm` defaults to 0 and `followLeg` to 10; `stretchy`, `antiPop`, `lock` to
  0. The pole's rotation is locked; the IK ends' and RootX_M's are free.
- Shipped blends: Manny all FK; the Creep's and the Orc D's legs IK (10), arms FK.

## The solve

1. sample the rig once (after one evaluation at the current frame): every G, D, FKX, IKX,
   control, the constant pieces `O_g`, `L`, `K`, the toes' relation, `RootX . G_pelvis^-1`, the
   pole's side of the CURRENT IK chain (`fkik.pole_side`), the blends;
2. the drive chain's target `S*[b] = O_g^-1 . wanted[g]` for every base `wanted` holds;
3. **RootX_M** from the pelvis (translate + rotate) when the pelvis is a member - first, every
   chain hangs below it;
4. level by level down the game skeleton: each member's FK control onto `L^-1 . S*` against its
   parent read now (rotate channels only - lengths are the rig's); **at a limb's END level** (the
   hand, the foot) the limb's IK half, before anything below it reads the deformation wrist:
   - the IK end onto `K . S*[end]` (translate + rotate) for any member of the limb's chain - from
     `S*`, not from the FKX end after the FK solve, so a hand pose onto an IK arm whose FK half
     stands elsewhere keeps the arm where it is shown;
   - the leg's `roll` / `rock` at their defaults with it (the end is computed for them);
   - `IKToes` onto the ball's `S*` (rotate only: the relation, then `_numeric`);
   - the pole on the plane of the limb's `S*` (`pole_point`, the side sampled before), and the
     `swivel` at its default, only when the limb's UPPER or MIDDLE bone is a member: a hand alone
     moves neither the elbow nor the plane, and keying the pole or zeroing an animated swivel
     there would move the elbow;
   - a limb whose `stretchy`, `antiPop`, pole `follow*` or `lock` is off its default
     (`fkik.off_default`) keeps its IK half unposed, named;
5. measure every member against its target (`worst`: directions for the four unrolled limb
   bones - an IK elbow is a hinge and AdvancedSkeleton moves their roll into the twist joints -
   full rotations for the rest, every position) and, off by more than 0.01 deg / 0.01 cm, solve
   again from the new state, at most `PASSES` times; what is still off is named;
6. read every value written (`values`, the FINAL channel values), put every temporary write back
   in reverse order, autoKey as it was.

**All of it is ONE closed undo chunk** (`UNDO_CHUNK`, `_one_undo_step`, outermost: around the
evaluation switch, the settle, the autoKey toggles, every temporary `setAttr` and every restore),
so a Ctrl+Z after a solve is one step that changes nothing and the next undoes what the animator
did before it - inside Apply's own chunk it nests and goes with Apply. Measured without it
(mayapy, Manny_Rig, autoKey on, a solve of `lowerarm_l` outside any chunk, its target the
unkeyed `FKElbow_L.rotateX` at 30 with the rig at 0): the scene came back exact, then the first
Ctrl+Z turned the animator's autoKey OFF and the second set `FKElbow_L.rotateX` to 30 - the
solve's temporary value, lasting on a static channel - while the marker the animator changed
just before the solve stayed changed (trap 186: a round trip leaves its steps on the queue).
With the chunk, on that scene, on a keyed rig solved whole under the parallel EM, nested in an
outer chunk and on a solve that raises half way: one Ctrl+Z leaves every control channel, its
keys, autoKey, the evaluation mode and the time as found, redo too, and the second takes the
marker back.

The spine in IK (`FKIKSpine_M` not 0) takes the pose on its FK half, said so. A limb in IK whose
FK forearm / calf is twisted about its own bone loses that twist (an IK elbow is a hinge) - the
angle is measured after the IK is set and said, as the Connections FK / IK switch does.

**One cost, stated:** the sample starts with `currentTime(currentTime)` (`settle`), which
re-evaluates the frame - an unkeyed tweak on a KEYED channel reverts to its curve, as any time
change reverts it.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Onto a rig").
"""

import contextlib
import math
from collections import OrderedDict, namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_asretarget as asr
import maya_rigs
from maya_scenesetup import fkik

from maya_poselib import keys
from maya_poselib import posemath as pm
from maya_poselib.skelsolve import Solution, joint_channels

__all__ = ["Solution", "Base", "bases", "drive_matrices", "solve", "controls_for", "measure"]

# leaf  -- the game bone ("hand_l"); base / side -- AdvancedSkeleton's ("Wrist", "_L");
# fk    -- the control (RootX_M for the pelvis); fkx / ikx / deform -- the joints; long paths or
#          None; limb -- "arm" / "leg" / None
Base = namedtuple("Base", "leaf base side fk fkx ikx deform limb")

UNROLLED = ("Shoulder", "Elbow", "Hip", "Knee", "Neck", "NeckPart1")
DIRECTION_BASES = ("Shoulder", "Elbow", "Hip", "Knee")
LIMB_OF = {"Shoulder": "arm", "Elbow": "arm", "Wrist": "arm",
           "Hip": "leg", "Knee": "leg", "Ankle": "leg", "Toes": "leg"}
# the next joint down a limb: the child an unrolled bone points at
CHILD = {"Shoulder": "Elbow", "Elbow": "Wrist", "Hip": "Knee", "Knee": "Ankle"}

# kind -> (AS name, game bones - the three of the IK chain, the leg's ball after them -, the
#          upper/middle ones, IK end, pole, align, toes control, the end's attributes held at
#          default, the pole's)
Limb = namedtuple("Limb", "name game upper ik pole align toes end_attrs pole_attrs")
LIMBS = OrderedDict([
    ("arm", Limb("Arm", ("upperarm", "lowerarm", "hand"), ("upperarm", "lowerarm"),
                 "IKArm", "PoleArm", "AlignIKToWrist", None, (), ("swivel",))),
    ("leg", Limb("Leg", ("thigh", "calf", "foot", "ball"), ("thigh", "calf"),
                 "IKLeg", "PoleLeg", "AlignIKToAnkle", "IKToes", ("roll", "rock"), ("swivel",))),
])
GAME_SIDES = {"_l": "L", "_r": "R"}
# attributes that must sit at their defaults for the IK half to be posed (fkik's refusal)
IK_GUARD = ("stretchy", "antiPop")
POLE_GUARD_PREFIX = ("follow", "lock")

PELVIS = "pelvis"
ROOT_CONTROL = "RootX_M"
ROOT_DEFORM = "Root_M"
SPINE_SWITCH = "FKIKSpine_M"
BLEND = "FKIKBlend"
ROTATE = ("rotateX", "rotateY", "rotateZ")
TRANSLATE = ("translateX", "translateY", "translateZ")

FRESH_MODE = "off"         # the evaluation the solve reads under; None leaves the manager be
UNDO_CHUNK = "skeldarPoseSolve"   # the one undo step a solve's round trip makes
PASSES = 3                 # solve, measure, solve again - at most
TOL_DEG = 0.01
TOL_CM = 0.01
HINGE_DEG = fkik.TOLERANCE_DEG
STRAIGHT = 1e-4            # of the limb: an elbow nearer its line than this has no plane
NUMERIC_ROUNDS = 6
NUMERIC_EPS = 1e-4         # rad: the finite difference of the numeric solve
NUMERIC_TOL = 1e-7         # rad: converged
DAMPING = 1e-9             # of J'J's mean diagonal: Newton at full rank, the least step below it
NAMED = 4

DRIVEN = "%d member(s) are driven on a rig (twist and helper bones): %s"
NO_CONTROL = "%d member(s) have no control on %s: %s"
SPINE_IK = "the spine shows IK - its FK took the pose"
IK_KEPT = "%s: the IK half is not posed - %s off the default"
NO_SIDE = "%s: the IK pole stands on the limb's line - no bend plane to read, the pole kept"
HINGE = "the FK %s twist is lost on %s (an IK %s is a hinge): %g deg"
TOES = "the IK toes do not reach the ball's turn on %s: %g deg"
OFF = "the pose lands within %.3f deg / %.3f cm (worst: %s)"


# ------------------------------------------------------------------- pure

def depth_of(path):
    """How deep a node stands in the DAG: the count of its path's `|`. Pure."""
    return (path or "").count("|")


def level_order(depths):
    """[[names at the shallowest depth], ...]: `depths` {name: depth} grouped by depth, each
    group sorted by name, shallowest first. Pure."""
    levels = {}
    for name, depth in depths.items():
        levels.setdefault(depth, []).append(name)
    return [sorted(levels[d]) for d in sorted(levels)]


def _game_parts(leaf):
    """("hand", "L") for "hand_l"; (leaf, None) for a centre bone. Pure."""
    for suffix, side in GAME_SIDES.items():
        if leaf.endswith(suffix):
            return leaf[:-len(suffix)], side
    return leaf, None


def limb_members(members):
    """{(kind, side): {"end": bool, "pole": bool}} for the limbs a set of game members touches.

    Any bone of a limb's chain (the arm's upperarm, lowerarm, hand; the leg's thigh, calf,
    foot, ball) poses its IK END; its UPPER or MIDDLE bone also its POLE (and its swivel) - a
    hand or a foot alone keeps the plane. The clavicle is no part of the IK arm. Pure."""
    out = {}
    for leaf in members or ():
        base, side = _game_parts(leaf)
        if side is None:
            continue
        for kind, limb in LIMBS.items():
            if base in limb.game:
                entry = out.setdefault((kind, side), {"end": False, "pole": False})
                entry["end"] = True
                entry["pole"] = entry["pole"] or base in limb.upper
    return out


def pole_point(s, e, w, elbow_rotation, side_local, nudge=fkik.NUDGE):
    """Where a limb's pole goes for a drive chain shoulder `s`, elbow `e`, wrist `w` (MVectors):
    on the shoulder-wrist line at the elbow's share, nudged `nudge` of the limb away from the
    pole's side, aimed at the elbow, a limb out - `fkik.pole_point`'s geometry, with one change.

    A BENT chain takes its side from its own bend (the elbow off the line, toward it), so the
    pole lies in the chain's plane and an IK elbow lands where the FK one stands. fkik turns the
    side it read off the IK chain with the elbow's frame (`side_local . elbow_rotation`), and an
    FK elbow ROLLED about its bone - the forearm twist a pose carries, which the hinge cannot -
    turns that side out of the plane: measured 0.059 cm off on Manny's IK arm. Only a straight
    chain (the elbow within `STRAIGHT` of the limb from the line), which has no plane of its
    own, takes fkik's side and so keeps the roll. Pure."""
    upper, lower = (s - e).length(), (e - w).length()
    length = upper + lower
    base = (s * lower + w * upper) / length
    line = (w - s).normal()
    bend = (e - base) - line * ((e - base) * line)
    if bend.length() <= STRAIGHT * length:
        return fkik.pole_point(s, e, w, elbow_rotation, side_local, nudge)
    nudged = base - bend.normal() * (nudge * length)
    aim = (e - nudged).normal()
    return nudged + aim * length


def rotation_vector(m):
    """The rotation of a matrix as a rotation vector (axis x angle, radians), the short way.
    Pure."""
    q = om.MTransformationMatrix(pm.matrix(m)).rotation(asQuaternion=True)
    if q.w < 0:
        q = om.MQuaternion(-q.x, -q.y, -q.z, -q.w)
    size = math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z)
    if size < 1e-15:
        return (0.0, 0.0, 0.0)
    angle = 2.0 * math.atan2(size, q.w)
    return (q.x / size * angle, q.y / size * angle, q.z / size * angle)


def turn(vector):
    """The rotation matrix of a rotation vector (radians). Pure."""
    angle = math.sqrt(sum(v * v for v in vector))
    if angle < 1e-15:
        return om.MMatrix()
    axis = om.MVector(*[v / angle for v in vector])
    return om.MQuaternion(angle, axis).asMatrix()


def _det(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def solve_step(columns, error, damping=DAMPING):
    """The step `d` minimising `|error + J . d|^2 + lambda |d|^2` - damped least squares,
    `d = -(J'J + lambda I)^-1 J' error` - `J`'s columns being the error's response to a unit
    step of each parameter, `lambda` = `damping` x the mean of J'J's diagonal.

    With `J` of full rank this is Newton's step to within `damping` (the neck's in-between and
    the IK toes: three channels, three degrees of freedom); should a rig hold a joint with less
    freedom than its control, a parameter the error does not answer to takes no step and two
    answering along one axis share it, so the solve lands as near as the rig allows instead of
    flying off. None when no parameter answers at all. Pure (3 x 3, Cramer's rule)."""
    j = [[columns[c][r] for c in range(3)] for r in range(3)]          # rows of J
    jtj = [[sum(j[k][a] * j[k][b] for k in range(3)) for b in range(3)] for a in range(3)]
    trace = jtj[0][0] + jtj[1][1] + jtj[2][2]
    if trace < 1e-24:
        return None
    lam = damping * trace / 3.0
    for a in range(3):
        jtj[a][a] += lam
    rhs = [-sum(j[k][a] * error[k] for k in range(3)) for a in range(3)]
    whole = _det(jtj)
    if abs(whole) < 1e-300:
        return None
    out = []
    for c in range(3):
        m = [row[:] for row in jtj]
        for r in range(3):
            m[r][c] = rhs[r]
        out.append(_det(m) / whole)
    return tuple(out)


def worst(rows):
    """(worst degrees, worst cm, the worst row's leaf) over `rows` (leaf, actual, wanted,
    direction): a row with a `direction` (the bone's child offset in its own frame) is judged by
    where that offset points under the two rotations, the others by their whole rotation; every
    row by its position. The worst row is the one furthest past the tolerances (`TOL_DEG`,
    `TOL_CM`). Nothing measured: (0, 0, None). Pure."""
    deg_worst = cm_worst = 0.0
    leaf_worst, score_worst = None, -1.0
    for leaf, actual, wanted, direction in rows:
        actual, wanted = pm.matrix(actual), pm.matrix(wanted)
        if direction is not None:
            v = om.MVector(*direction)
            deg = pm.direction_angle(v * pm.rotation(actual), v * pm.rotation(wanted))
        else:
            deg = pm.angle(actual, wanted)
        cm = (pm.position(actual) - pm.position(wanted)).length()
        deg_worst, cm_worst = max(deg_worst, deg), max(cm_worst, cm)
        score = max(deg / TOL_DEG, cm / TOL_CM)
        if score > score_worst:
            score_worst, leaf_worst = score, leaf
    return deg_worst, cm_worst, leaf_worst


def _named(items):
    items = list(items)
    shown = ", ".join(items[:NAMED])
    if len(items) > NAMED:
        shown += " and %d more" % (len(items) - NAMED)
    return shown


# ------------------------------------------------------------------ scene reads

def _one(rig, leaf):
    """The long path of one of the rig's nodes, or None when it is missing or ambiguous."""
    found = cmds.ls(maya_rigs.node(rig, leaf), long=True) or []
    return found[0] if len(found) == 1 else None


def _world(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def _parent_world(node):
    return om.MMatrix(cmds.getAttr(node + ".parentMatrix[0]"))


def _name(path):
    found = cmds.ls(path) or []
    return found[0] if len(found) == 1 else path


def game_bones(rig):
    """{leaf: long path} of the rig's game skeleton (the namespace stripped from the leaf)."""
    root = rig.skeleton_root
    if not root or not cmds.objExists(root):
        return {}
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                         fullPath=True) or [])
    out = {}
    for path in paths:
        out.setdefault(maya_rigs.leaf(path), path)
    return out


def _driver(game_path):
    """The node a game bone's orientation follows: the one target of its orient (or parent)
    constraint, long path; None when there is none or several."""
    for kind in ("orientConstraint", "parentConstraint"):
        for constraint in cmds.listRelatives(game_path, children=True, type=kind,
                                             fullPath=True) or []:
            query = getattr(cmds, kind)
            targets = query(constraint, query=True, targetList=True) or []
            if len(targets) == 1:
                found = cmds.ls(targets[0], long=True) or []
                if len(found) == 1:
                    return found[0]
    return None


def bases(rig):
    """{game leaf: Base} for the game bones the rig drives through a joint base of
    `maya_asretarget.ROWS` (and the pelvis, whose control is `RootX_M`): node fields are long
    paths of the nodes that exist, None for the ones that do not; `deform` is the target of
    the game bone's orient constraint (measured, never assumed), its spelling by name the
    fallback."""
    game = game_bones(rig)
    out = {}
    for base, ue in asr.ROWS:
        for side, ue_side in asr.SIDES:
            leaf = ue + ue_side
            if leaf not in game:
                continue
            fk = _one(rig, "FK" + base + side)
            fkx = _one(rig, "FKX" + base + side)
            ikx = _one(rig, "IKX" + base + side)
            deform = _driver(game[leaf]) or _one(rig, base + side)
            if not (fk or fkx or deform):
                continue
            out[leaf] = Base(leaf, base, side, fk, fkx, ikx, deform, LIMB_OF.get(base))
    if PELVIS in game:
        deform = _driver(game[PELVIS]) or _one(rig, ROOT_DEFORM)
        out[PELVIS] = Base(PELVIS, "Root", "_M", _one(rig, ROOT_CONTROL), None, None, deform,
                           None)
    return out


def _blend(rig, kind, side):
    """The limb's FK/IK blend as a weight (0 FK, 1 IK); 0 for a rig without the switch."""
    node = _one(rig, fkik.FKIK_NODE.format(LIMBS[kind].name, side.strip("_")))
    if not node:
        return 0.0
    return float(cmds.getAttr(node + "." + BLEND)) / fkik.BLEND[fkik.IK]


def _shown(rig, base):
    """The drive chain S of a base as the rig shows it: the FKX and IKX joints blended for a
    limb joint (`fkik.blended`), the FKX joint otherwise; rigid."""
    fkx = pm.rigid(_world(base.fkx))
    if base.limb and base.ikx:
        weight = _blend(rig, base.limb, base.side)
        return fkik.blended(fkx, pm.rigid(_world(base.ikx)), weight)
    return fkx


def _drive(rig, base, game_path):
    """`rigid(G) . rigid(D)^-1 . S`: the game bone as the drive chain holds it."""
    return pm.rigid(_world(game_path)) * pm.rigid(_world(base.deform)).inverse() * \
        _shown(rig, base)


def drive_matrices(rig):
    """{game leaf: 16 floats} for the six unrolled bones the rig drives (upperarm, lowerarm,
    thigh, calf per side; neck_01, neck_02): `G . D^-1 . S` - `S` the FKX and IKX joints blended
    as the rig blends them for a limb, the FKX joint for the neck. The other bones are absent:
    their `world` is their drive."""
    game = game_bones(rig)
    out = {}
    for leaf, base in bases(rig).items():
        if base.base in UNROLLED and base.deform and base.fkx and leaf in game:
            out[leaf] = pm.flat(_drive(rig, base, game[leaf]))
    return out


# ------------------------------------------------------------------ scene state

@contextlib.contextmanager
def _one_undo_step():
    """The block as ONE closed undo chunk (`UNDO_CHUNK`), closed whatever happens: a solve's
    writes and their restores net to nothing, so undoing the chunk is a step that changes
    nothing - left loose, each write, each restore and each autoKey toggle is a step of its own
    and the animator's next Ctrl+Z presses replay them onto the rig (trap 186). Not
    `stateWithoutFlush`: switching the queue off inside Apply's chunk breaks that chunk (trap
    145); a chunk nests in it."""
    cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


@contextlib.contextmanager
def _fresh():
    """The evaluation the solve reads under (`FRESH_MODE`): switched only when the scene is not
    already there, put back whatever happens."""
    mode = (cmds.evaluationManager(query=True, mode=True) or [None])[0]
    switch = bool(FRESH_MODE) and mode != FRESH_MODE
    if switch:
        cmds.evaluationManager(mode=FRESH_MODE)
    try:
        yield
    finally:
        if switch:
            cmds.evaluationManager(mode=mode)


class _Session(object):
    """The solve's temporary writes: autoKey off, the original of every plug recorded on its
    first write, `values()` the last value written to each, `restore()` every original back in
    reverse order and autoKey as it was. A plug `keys.writable` refuses is not written: it lands
    in `skipped`, once."""

    def __init__(self):
        self.original = OrderedDict()
        self.last = OrderedDict()
        self.skipped = {}
        self._writable = {}
        self._auto = None

    def __enter__(self):
        self._auto = cmds.autoKeyframe(query=True, state=True)
        cmds.autoKeyframe(state=False)
        return self

    def __exit__(self, *exc):
        self.restore()
        cmds.autoKeyframe(state=self._auto)
        return False

    def allowed(self, plugs):
        """True when every plug can be written; the first refusal is remembered by plug."""
        for plug in plugs:
            if plug not in self._writable:
                self._writable[plug] = keys.writable(plug)
            ok, why = self._writable[plug]
            if not ok:
                self.skipped.setdefault(plug, why)
                return False
        return True

    def set(self, plug, value):
        if plug not in self.original:
            self.original[plug] = float(cmds.getAttr(plug))
        cmds.setAttr(plug, value)
        self.last[plug] = float(value)

    def get(self, plug):
        return self.last[plug] if plug in self.last else float(cmds.getAttr(plug))

    def values(self):
        return OrderedDict((self._spelled(plug), value) for plug, value in self.last.items())

    @staticmethod
    def _spelled(plug):
        node, attr = plug.rsplit(".", 1)
        return _name(node) + "." + attr

    def restore(self):
        for plug in reversed(list(self.original)):
            try:
                cmds.setAttr(plug, self.original[plug])
            except RuntimeError:
                pass


# ------------------------------------------------------------------ the solve

def _plain(members):
    """The members as plain game leaves (a path and a namespace dropped), each once, in order."""
    out = []
    for leaf in members or ():
        leaf = leaf.split("|")[-1].split(":")[-1]
        if leaf not in out:
            out.append(leaf)
    return out


def _analytic(base):
    """Is the control's FKX joint below it (its world a constant piece of the control's)?"""
    return bool(base.fk and base.fkx) and base.fkx.startswith(base.fk + "|")


class _Job(object):
    """One solve: the samples, the targets and the writes of `solve`."""

    def __init__(self, rig, wanted, members):
        self.rig = rig
        self.wanted = dict((leaf.split(":")[-1], pm.rigid(m)) for leaf, m in (wanted or {}).items())
        self.game = game_bones(rig)
        self.bases = bases(rig)
        self.root = maya_rigs.leaf(rig.skeleton_root) if rig.skeleton_root else None
        self.members = []
        self.notes = OrderedDict()
        driven, missing = [], []
        for leaf in _plain(members):
            if leaf == self.root:
                continue                                  # Main is never written
            if leaf in self.bases and self.bases[leaf].fk:       # the pelvis's is RootX_M
                self.members.append(leaf)
            elif pm.is_helper(leaf) or pm.is_twist(leaf):
                driven.append(leaf)
            else:
                missing.append(leaf)
        if driven:
            self.notes["driven"] = DRIVEN % (len(driven), _named(driven))
        if missing:
            self.notes["missing"] = NO_CONTROL % (len(missing), maya_rigs.label(rig),
                                                  _named(missing))
        self.limbs = limb_members(self.members)
        self.session = _Session()

    # ---- sampling

    def sample(self):
        """Everything the solve holds constant, read once before anything moves."""
        self.offset, self.in_control, self.order, self.axis, self.rest_rotate = {}, {}, {}, {}, {}
        self.shown = {}
        for leaf, base in self.bases.items():
            if leaf not in self.game or not base.deform:
                continue
            g, d = pm.rigid(_world(self.game[leaf])), pm.rigid(_world(base.deform))
            self.offset[leaf] = g * d.inverse()
            if base.fkx:
                self.shown[leaf] = _shown(self.rig, base)
        for leaf in self.members:
            base = self.bases[leaf]
            control = base.fk
            if not control:
                continue
            if _analytic(base):
                self.in_control[leaf] = pm.rigid(_world(base.fkx)) * \
                    pm.rigid(_world(control)).inverse()
            self._remember(control)
        if PELVIS in self.members:
            self.root_offset = pm.rigid(_world(self.bases[PELVIS].fk)) * \
                pm.rigid(_world(self.game[PELVIS])).inverse()
        self.blends = dict((key, _blend(self.rig, key[0], "_" + key[1])) for key in self.limbs)
        self.ik = {}
        for key in self.limbs:
            self.ik[key] = self._sample_limb(*key)

    def _remember(self, control):
        """The control's rotate order, rotateAxis and rotate values before anything moved."""
        if control in self.order:
            return
        self.order[control] = int(cmds.getAttr(control + ".rotateOrder"))
        self.axis[control] = tuple(cmds.getAttr(control + ".rotateAxis")[0])
        self.rest_rotate[control] = tuple(float(v) for v in cmds.getAttr(control + ".rotate")[0])

    def _sample_limb(self, kind, side):
        """The limb's IK nodes and constants, or None when the rig has no IK for it."""
        limb = LIMBS[kind]
        suffix = "_" + side
        ik, pole = _one(self.rig, limb.ik + suffix), _one(self.rig, limb.pole + suffix)
        align = _one(self.rig, limb.align + suffix)
        game = [name + suffix.lower() for name in limb.game]
        chain = [self.bases.get(name) for name in game[:3]]
        if not (ik and align) or not all(b and b.fkx for b in chain):
            return None
        out = {"ik": ik, "pole": pole, "game": game, "chain": chain,
               "k": pm.rigid(_world(align)) * pm.rigid(_world(chain[2].fkx)).inverse()}
        self._remember(ik)
        out["guard"] = self._guard(ik, pole)
        if pole:
            ikx = [b.ikx for b in chain]
            side_local = None
            for joints in (ikx, [b.fkx for b in chain]):
                if all(joints):
                    s, e, w = (pm.position(_world(j)) for j in joints)
                    side_local = fkik.pole_side(pm.position(_world(pole)), s, e, w,
                                                pm.rotation(_world(joints[1])))
                    if side_local is not None:
                        break
            out["side"] = side_local
        toes = _one(self.rig, limb.toes + suffix) if limb.toes else None
        ball = self.bases.get(game[3]) if len(game) > 3 else None
        if toes and ball and ball.ikx:
            out["toes"] = toes
            out["toes_joint"] = ball.ikx
            out["toes_rel"] = pm.rigid(_world(toes)) * pm.rigid(_world(ball.ikx)).inverse()
            self._remember(toes)
        return out

    @staticmethod
    def _guard(ik, pole):
        """The IK half's solve attributes off their defaults (sorted plug leaves)."""
        attrs = {}
        for node, names in ((ik, IK_GUARD), (pole, None)):
            if not node:
                continue
            names = names or [a for a in (cmds.listAttr(node, userDefined=True) or [])
                              if a.startswith(POLE_GUARD_PREFIX)]
            for name in names:
                if not cmds.attributeQuery(name, node=node, exists=True):
                    continue
                default = (cmds.attributeQuery(name, node=node, listDefault=True) or [0.0])[0]
                attrs[maya_rigs.leaf(node) + "." + name] = (
                    float(cmds.getAttr(node + "." + name)), [], float(default))
        return fkik.off_default(attrs)

    # ---- targets

    def target(self, leaf):
        """S*[leaf]: where the drive chain of a base should stand - `O_g^-1 . wanted`; the chain
        as it is shown when `wanted` does not hold the bone."""
        if leaf in self.wanted and leaf in self.offset:
            return self.offset[leaf].inverse() * self.wanted[leaf]
        return self.shown.get(leaf)

    # ---- writes

    def _turn(self, node, world_turn):
        """The node's rotate channels for its world rotation to be `world_turn`, its parent read
        now; nearest the values it had before the solve."""
        plugs = [node + "." + ch for ch in ROTATE]
        if not self.session.allowed(plugs):
            return False
        local = pm.rotation(world_turn) * pm.rotation(_parent_world(node)).inverse()
        channels = joint_channels(local, (0.0, 0.0, 0.0), self.axis[node], self.order[node],
                                  self.rest_rotate[node])
        for plug, value in zip(plugs, channels):
            self.session.set(plug, value)
        return True

    def _move(self, node, point):
        """The node's translate channels for its world position to be `point`: the world
        difference brought into the parent's frame - exact whatever the pivots and the parent's
        scale, a translate moves its node linearly."""
        plugs = [node + "." + ch for ch in TRANSLATE]
        if not self.session.allowed(plugs):
            return False
        delta = om.MVector(point) - pm.position(_world(node))
        step = delta * _parent_world(node).inverse()
        for plug, d in zip(plugs, (step.x, step.y, step.z)):
            self.session.set(plug, self.session.get(plug) + d)
        return True

    def _hold_default(self, node, names):
        for name in names:
            if not node or not cmds.attributeQuery(name, node=node, exists=True):
                continue
            plug = node + "." + name
            if not self.session.allowed([plug]):
                continue
            default = (cmds.attributeQuery(name, node=node, listDefault=True) or [0.0])[0]
            self.session.set(plug, float(default))

    # ---- the pieces

    def _root(self):
        base = self.bases[PELVIS]
        aim = self.root_offset * self.wanted.get(PELVIS, pm.rigid(_world(self.game[PELVIS])))
        if self._turn(base.fk, aim):
            self._move(base.fk, pm.position(aim))

    def _fk(self, leaf):
        base = self.bases[leaf]
        aim = self.target(leaf)
        if aim is None or not base.fk:
            return
        if leaf in self.in_control:
            self._turn(base.fk, self.in_control[leaf].inverse() * aim)
        elif base.fkx:
            self._numeric(base.fk, base.fkx, pm.rotation(aim))

    def _numeric(self, control, joint, aim):
        """The control turned until `joint` stands on `aim` - damped least squares
        (`solve_step`) on the joint's world rotation, its Jacobian by finite differences of the
        control's world rotation, a few rounds. Its two users: the neck's in-between (its joint
        is not below its control) and the IK toes (their SC handle aims the toes joint, which
        does not compose rigidly with the control). The last write is always a solution, never
        a probe."""

        def error():
            return rotation_vector(pm.rotation(_world(joint)).inverse() * aim)

        now = pm.rotation(_world(control))
        e0 = error()
        for _ in range(NUMERIC_ROUNDS):
            if math.sqrt(sum(v * v for v in e0)) < NUMERIC_TOL:
                return
            columns = []
            for axis in range(3):
                probe = [0.0, 0.0, 0.0]
                probe[axis] = NUMERIC_EPS
                if not self._turn(control, now * turn(probe)):
                    return
                e = error()
                columns.append(tuple((e[k] - e0[k]) / NUMERIC_EPS for k in range(3)))
            step = solve_step(columns, e0)
            if step is None:
                self._turn(control, now)
                return
            now = now * turn(step)
            self._turn(control, now)
            e0 = error()

    def _toes(self, key, info):
        """The IK toes onto the ball's target. `IKXToes` is aimed by an SC handle that hangs
        under `IKToes` (`IKToesHandle_*`, its effector at `IKXToesEnd_*`), and the aim does not
        compose rigidly with the control: the relation `IKToes . IKXToes^-1` read off the rig
        put a 3-axis toe turn 9.88 deg off (Creep, 9.91 Orc D) while the turn is within reach.
        So the relation is the first guess and `_numeric` finishes it; a turn still out of
        reach, the leg shown in IK, is said."""
        self.notes.pop("toes %s %s" % key, None)
        ball = self.target(info["game"][3])
        if ball is None or not self._turn(info["toes"], info["toes_rel"] * ball):
            return
        joint = info["toes_joint"]
        self._numeric(info["toes"], joint, pm.rotation(ball))
        lost = pm.angle(pm.rigid(_world(joint)), ball)
        if self.blends.get(key, 0.0) > 0.0 and lost > HINGE_DEG:
            self.notes["toes %s %s" % key] = TOES % ("%s_%s" % (key[0], key[1].lower()),
                                                     round(lost, 1))

    def _ik_limb(self, key):
        """The limb's IK half (step 4 of the module's solve), at its end's level."""
        limb, info = LIMBS[key[0]], self.ik.get(key)
        if not info:
            return
        label = "%s_%s" % (key[0], key[1].lower())
        if info["guard"]:
            self.notes["guard " + label] = IK_KEPT % (label, ", ".join(info["guard"]))
            return
        pose_pole = self.limbs[key]["pole"] and info.get("pole")
        self._hold_default(info["ik"], limb.end_attrs)
        if pose_pole:
            self._hold_default(info["ik"], limb.pole_attrs)
        chain = [self.target(name) for name in info["game"][:3]]
        if any(m is None for m in chain):
            return
        aim = info["k"] * chain[2]
        if self._turn(info["ik"], aim):
            self._move(info["ik"], pm.position(aim))
        if "toes" in info:
            self._toes(key, info)
        if pose_pole:
            if info["side"] is None:
                self.notes["side " + label] = NO_SIDE % label
            else:
                s, e, w = (pm.position(m) for m in chain)
                point = pole_point(s, e, w, pm.rotation(chain[1]), info["side"])
                self._move(info["pole"], point)
        self._hinge(key, info, chain)

    def _hinge(self, key, info, chain):
        """A limb SHOWN in IK whose upper or middle bone is posed: the FK twist about the bone
        that the IK hinge cannot hold, measured on the IKX joints just solved."""
        self.notes.pop("hinge %s %s" % key, None)
        if self.blends.get(key, 0.0) <= 0.0 or not self.limbs[key]["pole"]:
            return
        turns = []
        for base, aim in zip(info["chain"][:2], chain[:2]):
            if base.ikx:
                turns.append(pm.angle(pm.rigid(_world(base.ikx)), aim))
        if turns and max(turns) > HINGE_DEG:
            bone, joint = ("forearm", "elbow") if key[0] == "arm" else ("calf", "knee")
            self.notes["hinge %s %s" % key] = HINGE % (bone, "%s_%s" % (key[0], key[1].lower()),
                                                       joint, round(max(turns), 1))

    # ---- passes

    def plan_levels(self):
        """The game skeleton's levels the passes walk: every member but the pelvis, and the END
        of every limb a member touches - a thigh alone poses its leg's IK at the foot's depth,
        before anything below the foot (the toes) reads the deformation ankle."""
        self.ends = {}
        for key, info in self.ik.items():
            if info:
                self.ends.setdefault(info["game"][2], []).append(key)
        depths = dict((leaf, depth_of(self.game[leaf])) for leaf in self.members
                      if leaf != PELVIS and leaf in self.game)
        for leaf in self.ends:
            if leaf in self.game:
                depths.setdefault(leaf, depth_of(self.game[leaf]))
        self.levels = level_order(depths)

    def run_pass(self):
        if PELVIS in self.members:
            self._root()
        members = set(self.members)
        for level in self.levels:
            for leaf in level:
                if leaf in members:
                    self._fk(leaf)
            for leaf in level:
                for key in self.ends.get(leaf, ()):
                    self._ik_limb(key)

    def rows(self):
        return _rows(self.rig, self.bases, self.game, self.wanted, self.members)

    def run(self, settle=True):
        with _one_undo_step(), _fresh(), self.session:
            if settle:
                cmds.currentTime(cmds.currentTime(query=True), update=True)
            self.sample()
            self.plan_levels()
            measured = (0.0, 0.0, None)
            for _ in range(PASSES):
                self.run_pass()
                measured = worst(self.rows())
                if measured[0] <= TOL_DEG and measured[1] <= TOL_CM:
                    break
            values = self.session.values()
        if measured[0] > TOL_DEG or measured[1] > TOL_CM:
            self.notes["off"] = OFF % measured
        if any(self._spine(leaf) for leaf in self.members):
            node = _one(self.rig, SPINE_SWITCH)
            if node and abs(float(cmds.getAttr(node + "." + BLEND))) > fkik.CONSTANT:
                self.notes["spine"] = SPINE_IK
        skipped = OrderedDict((_Session._spelled(plug), why)
                              for plug, why in self.session.skipped.items())
        return Solution(values, list(self.notes.values()), skipped)

    def _spine(self, leaf):
        return self.bases[leaf].base.startswith("Spine")


def _rows(rig, all_bases, game, wanted, members):
    """`worst`'s rows for the members as the rig stands now: the six unrolled bones by their
    drive (`_drive`), the four limb ones by where they point, every other member by its game
    bone."""
    by_joint = dict(((b.base, b.side), b) for b in all_bases.values())

    def shown(base):
        if base.base in UNROLLED and base.deform and base.fkx:
            return _drive(rig, base, game[base.leaf])
        return pm.rigid(_world(game[base.leaf]))

    rows = []
    for leaf in members:
        if leaf not in wanted or leaf not in game or leaf not in all_bases:
            continue
        base = all_bases[leaf]
        actual = shown(base)
        direction = None
        child = by_joint.get((CHILD.get(base.base), base.side))
        if base.base in DIRECTION_BASES and child is not None and child.leaf in game:
            offset = (pm.position(shown(child)) - pm.position(actual)) * \
                pm.rotation(actual).inverse()
            direction = (offset.x, offset.y, offset.z)
        rows.append((leaf, actual, pm.matrix(wanted[leaf]), direction))
    return rows


def solve(rig, wanted, members, settle=True):
    """Solution: the FINAL channel values of the rig's controls that put the `members` (game
    leaves) on `wanted` ({game leaf: matrix} for every target bone - `posemath.targets`, the six
    unrolled bones in drive form). The scene is left exactly as found: every temporary
    `setAttr` is put back, autoKey as it was, the evaluation manager as it was - and the round
    trip is ONE undo step (`UNDO_CHUNK`) that changes nothing when undone, nested in a caller's
    own chunk when there is one. `skipped` names the plugs that could not be written
    (`keys.writable`), `notes` what the line should say."""
    return _Job(rig, wanted, members).run(settle)


def controls_for(rig, members):
    """The controls Apply would key for `members` (long paths, in solve order): each member's FK
    control (`RootX_M` for the pelvis), and for every limb a member touches its IK end (the
    leg's toes too) and - when its upper or middle bone is a member - its pole; a limb whose IK
    solve attributes are off their defaults keeps its IK half and gives none."""
    job = _Job(rig, {}, members)
    out = []
    for leaf in job.members:
        control = job.bases[leaf].fk
        if control and control not in out:
            out.append(control)
    for (kind, side), how in job.limbs.items():
        limb, suffix = LIMBS[kind], "_" + side
        ik, pole = _one(rig, limb.ik + suffix), _one(rig, limb.pole + suffix)
        if not ik or job._guard(ik, pole):
            continue
        nodes = [ik]
        if limb.toes:
            nodes.append(_one(rig, limb.toes + suffix))
        if how["pole"]:
            nodes.append(pole)
        out.extend(n for n in nodes if n and n not in out)
    return out


def measure(rig, wanted, members):
    """(worst degrees, worst cm, worst leaf) of the members against `wanted` as the rig stands
    now (after the keys): the four unrolled limb bones by where they point, the rest by their
    whole rotation, every member's position - the unrolled bones read in drive form."""
    all_bases = bases(rig)
    game = game_bones(rig)
    wanted = dict((leaf.split(":")[-1], pm.rigid(m)) for leaf, m in (wanted or {}).items())
    root = maya_rigs.leaf(rig.skeleton_root) if rig.skeleton_root else None
    leaves = [leaf for leaf in _plain(members) if leaf != root]
    return worst(_rows(rig, all_bases, game, wanted, leaves))
