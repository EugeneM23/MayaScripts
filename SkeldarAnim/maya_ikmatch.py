"""The IK limbs of an AdvancedSkeleton rig take the FK limbs' shape (2026-10-02).

The animator: «анимация IK должна соответствовать анимации FK это обязательное условие» -
after a squash & stretch take the FK limbs carry the clip's lengths, and switching a limb to IK
showed the rig's own.

## What an AdvancedSkeleton IK limb is

Read off the rig's network and the vendor's `asAlignFKIK`:

- the chain's lengths: `IKX<mid>.tx = |input2X| * Lenght1` and `IKX<end>.tx` the same with
  `Lenght2`, the multiplyDivide on `IK<Limb>.Lenght1`'s output holding the rest length (negative
  on the left side) - with `stretchy` 0, whose stretch factor is 1 (its measure runs through an
  animCurveUU that is flat at the rest sum below it);
- the chain's root: `IKX<start>` stands at `t = 0` under `IKXOffset<start>` (the clavicle's or the
  pelvis's rest offset), its translate free; nothing follows the FK start control's translation;
- the foot: `IKX<end>` is aimed by an SC handle under `RollToes` at the ball, `IKXToes.t` is the
  ball in the ankle, the toe control pivots at the rest ball (`IKOffsetToes`). Moving `IKXToes.t`
  alone re-aims the ankle (measured 6.8 deg for 2 cm sideways), so the handle and the toe pivot
  move onto the ball with it.

## What this does

`carry(rig, start, end)`, after a retarget's bake: one walk over the span reads each limb's FKX
chain and the frames the IK nodes hang in, and writes the IK chain's root translate, `Lenght1/2`
and, on a leg, the foot - so the IK chain stands where the FK chain stands. A series that never
leaves its rest writes nothing, a constant one a plain value, anything else a key on every frame.
`restore(rig)` puts all of it back (every reset before a new take calls it): curves deleted,
`Lenght` at its default, each translate at its own value - kept on the node the first time it
moved (`REST_ATTR`).

The pure halves (`lenght`, `local_point`, `moved_local`, `plan_series`, `frame_values`) take the
scene as matrices; the Connections FK / IK switch (`maya_scenesetup.fkik`) uses them on the chain
an arm SHOWS.

Spec: docs/superpowers/specs/2026-10-02-ik-follows-fk-design.md
"""

import math
from collections import namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_rigs

REST_ATTR = "skeldarIkRest"          # on a node whose translate the match moves: its own value
LIMBS = (("Arm", "R"), ("Arm", "L"), ("Leg", "R"), ("Leg", "L"))
JOINTS = {"Arm": ("Shoulder", "Elbow", "Wrist"), "Leg": ("Hip", "Knee", "Ankle")}
LENGHTS = ("Lenght1", "Lenght2")     # AdvancedSkeleton's own spelling
TRANSLATE = ("translateX", "translateY", "translateZ")
CONSTANT = 1e-6                      # a value this near its rest is the rest (restore)
TOL_RATIO = 1e-5                     # a Lenght series this flat is one value, this near 1 is 1
TOL_CM = 1e-4                        # ... a translate's, in cm (a micron): a world-space reading
                                     # of an unchanging length wanders by ~1e-6 relative
TIME_CURVES = ("animCurveTL", "animCurveTA", "animCurveTT", "animCurveTU")

# label   -- "arm_r"
# ik      -- the IK end control (IKArm_R), which carries Lenght1/2
# fkx/ikx -- [start, mid, end] joints of the two chains
# root_parent -- IKXOffset<start>: what the IK chain's root joint stands in
# units   -- (|input2X| of Lenght1, of Lenght2), None where the rig has no such attribute
# foot    -- a Foot, or None (an arm, or a leg without toes)
Limb = namedtuple("Limb", "label ik fkx ikx root_parent units foot")
# fkx / ikx -- the toes joints; handle -- the ankle's SC handle; offset -- the toe control's offset
Foot = namedtuple("Foot", "fkx ikx handle offset")


# ------------------------------------------------------------------- pure

def position(matrix):
    return om.MVector(matrix[12], matrix[13], matrix[14])


def scale_of(matrix):
    """A world matrix's (uniform) scale: the length of its first row."""
    return om.MVector(matrix[0], matrix[1], matrix[2]).length()


def lenght(a, b, unit, scale):
    """The `Lenght` that makes an IK segment of rest length |unit| (in a chain at world `scale`)
    as long as a -> b. None without a unit. Pure."""
    if not unit or not scale:
        return None
    return (om.MVector(b) - om.MVector(a)).length() / (abs(unit) * scale)


def local_point(point, parent_world):
    """A world point in a parent's space - a child's translate that stands there. Pure."""
    p = om.MPoint(point) * om.MMatrix(parent_world).inverse()
    return (p.x, p.y, p.z)


def moved_local(local, now, wanted, parent_world):
    """The translate that moves a node standing at `now` (world, with translate `local`) onto
    `wanted`: the move carried into the parent's space as a vector, so a pivot of the node's own
    does not enter. Pure."""
    d = (om.MVector(wanted) - om.MVector(now)) * om.MMatrix(parent_world).inverse()
    return (local[0] + d.x, local[1] + d.y, local[2] + d.z)


def plan_series(values, rest, tol=CONSTANT):
    """("rest", rest) when every value is the rest, ("value", v) when they are one value,
    ("keys", values) otherwise. Pure."""
    values = list(values)
    if not values or all(abs(v - rest) <= tol for v in values):
        return "rest", rest
    if max(values) - min(values) <= tol:
        return "value", sum(values) / len(values)
    return "keys", values


def frame_values(limb, sample):
    """One frame's IK values for `limb` from what the walk read (`_read`): {(node, attr): value},
    a translate as one (node, "translate") 3-tuple. Pure."""
    fa, fb, fc = sample["fkx"]
    out = {(limb.ikx[0], "translate"): local_point(position(fa), sample["root_parent"])}
    scale = scale_of(sample["root_parent"])
    for attr, (p, q), unit in zip(LENGHTS, ((fa, fb), (fb, fc)), limb.units):
        value = lenght(position(p), position(q), unit, scale)
        if value is not None:
            out[(limb.ik, attr)] = value
    if limb.foot:
        ball = position(sample["toes"])
        # the ball in the FK ankle: where the IK ankle - which then stands in the FK ankle's
        # frame - holds its toes joint
        out[(limb.foot.ikx, "translate")] = local_point(ball, fc)
        for node in (limb.foot.handle, limb.foot.offset):
            world, parent_world, local = sample[node]
            out[(node, "translate")] = moved_local(local, position(world), ball, parent_world)
    return out


ROOT_NAME = {"arm": "shoulder", "leg": "hip"}
SHOWN_CM = 0.005                     # a move below this is not worth a word


def summary(label, series, limb, rests=None):
    """What the walk found for one limb, or '' when it stands as it was. Pure.
    `series`: {(node, attr): [values]}; `rests`: {node: its rest translate} (the root's
    defaults to (0, 0, 0))."""
    rests = rests or {}
    parts = []
    lens = [series.get((limb.ik, attr)) for attr in LENGHTS]
    if all(lens) and any(abs(v - 1.0) > 1e-4 for s in lens for v in s):
        parts.append("lengths x%s/%s" % tuple(_span(s) for s in lens))
    moved = [(limb.ikx[0], ROOT_NAME.get(label.split("_")[0], "root"))]
    if limb.foot:
        moved.append((limb.foot.ikx, "ball"))
    for node, name in moved:
        values = series.get((node, "translate")) or []
        rest = om.MVector(rests.get(node) or (0.0, 0.0, 0.0))
        off = max([(om.MVector(t) - rest).length() for t in values] or [0.0])
        if off > SHOWN_CM:
            parts.append("the %s moved %.2f cm" % (name, off))
    return ("%s %s" % (label, ", ".join(parts))) if parts else ""


def _span(values):
    lo, hi = min(values), max(values)
    return ("%.3f" % lo) if hi - lo < 5e-4 else ("%.3f..%.3f" % (lo, hi))


# ------------------------------------------------------------------ scene

def _one(rig, leaf):
    paths = cmds.ls(maya_rigs.node(rig, leaf), long=True) or []
    return paths[0] if len(paths) == 1 else None


def _parent(node):
    return (cmds.listRelatives(node, parent=True, fullPath=True) or [None])[0]


def _world(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def _leaf(path):
    return path.split("|")[-1].split(":")[-1]


def unit_of(ik, attr):
    """|input2X| of the multiplyDivide `ik.attr` feeds - the IK segment's rest length - or None."""
    if not cmds.attributeQuery(attr, node=ik, exists=True):
        return None
    for node in cmds.listConnections(ik + "." + attr, source=False, destination=True,
                                     skipConversionNodes=True) or []:
        if cmds.nodeType(node) == "multiplyDivide":
            value = cmds.getAttr(node + ".input2X")
            return abs(value) if value else None
    return None


def _joints(rig, base, side):
    blend = _one(rig, "FKIK%s_%s" % (base, side))
    names = list(JOINTS[base])
    if blend:
        for i, attr in enumerate(("startJoint", "middleJoint", "endJoint")):
            if cmds.attributeQuery(attr, node=blend, exists=True):
                names[i] = cmds.getAttr(blend + "." + attr) or names[i]
    return names


def _foot(rig, side, fkx_end, ikx_end):
    """The toes of a leg: the nearest FKX joint below the FK ankle (its own FK control stands
    between them) whose IKX twin is the IK ankle's child, the SC handle that starts at the IK
    ankle, the toe control's offset."""
    suffix = "_" + side
    below = cmds.listRelatives(fkx_end, allDescendents=True, type="joint", fullPath=True) or []
    ik_children = set(cmds.listRelatives(ikx_end, children=True, type="joint", fullPath=True) or [])
    for child in sorted(below, key=lambda p: (p.count("|"), p)):
        name = _leaf(child)
        if not (name.startswith("FKX") and name.endswith(suffix)):
            continue
        toes = name[3:-len(suffix)]
        ikx = _one(rig, "IKX" + name[3:])
        if ikx not in ik_children:
            continue
        offset = _one(rig, "IKOffset" + toes + suffix)
        handle = None
        for h in cmds.ls(maya_rigs.node(rig, "*"), type="ikHandle", long=True) or []:
            start = cmds.ikHandle(h, query=True, startJoint=True) or ""
            if (cmds.ls(start, long=True) or [""])[0] == ikx_end:
                handle = h
                break
        if ikx and offset and handle:
            return Foot(child, ikx, handle, offset)
    return None


def limb(rig, base, side):
    """The limb's nodes, or None when the rig lacks any of them."""
    names = _joints(rig, base, side)
    suffix = "_" + side
    fkx = [_one(rig, "FKX" + n + suffix) for n in names]
    ikx = [_one(rig, "IKX" + n + suffix) for n in names]
    ik = _one(rig, "IK%s%s" % (base, suffix))
    if not (all(fkx) and all(ikx) and ik):
        return None
    root_parent = _parent(ikx[0])
    if not root_parent:
        return None
    units = tuple(unit_of(ik, attr) for attr in LENGHTS)
    foot = _foot(rig, side, fkx[2], ikx[2]) if base == "Leg" else None
    return Limb("%s_%s" % (base.lower(), side.lower()), ik, fkx, ikx, root_parent, units, foot)


def limbs(rig):
    return [l for l in (limb(rig, base, side) for base, side in LIMBS) if l]


def _plugs(limb):
    """[(node, attr, rest or None)]: what the match writes on one limb. A translate's rest is
    its kept value (REST_ATTR), the root joint's (0, 0, 0) when none was kept; a Lenght's its
    default."""
    out = []
    for attr, unit in zip(LENGHTS, limb.units):
        if unit:
            default = (cmds.attributeQuery(attr, node=limb.ik, listDefault=True) or [1.0])[0]
            out.append((limb.ik, attr, default))
    out.append((limb.ikx[0], "translate", _kept(limb.ikx[0]) or (0.0, 0.0, 0.0)))
    if limb.foot:
        for node in (limb.foot.ikx, limb.foot.handle, limb.foot.offset):
            out.append((node, "translate", _kept(node)))
    return out


def _kept(node):
    if cmds.attributeQuery(REST_ATTR, node=node, exists=True):
        return tuple(cmds.getAttr(node + "." + REST_ATTR)[0])
    return None


def keep(node):
    """Remember the node's translate as its rest, the first time it moves."""
    if cmds.attributeQuery(REST_ATTR, node=node, exists=True):
        return
    rest = cmds.getAttr(node + ".translate")[0]
    cmds.addAttr(node, longName=REST_ATTR, attributeType="double3")
    for axis in "XYZ":
        cmds.addAttr(node, longName=REST_ATTR + axis, attributeType="double", parent=REST_ATTR)
    cmds.setAttr(node + "." + REST_ATTR, *rest)


def _channels(attr):
    return TRANSLATE if attr == "translate" else (attr,)


def _time_curves(plug):
    return [c for c in cmds.listConnections(plug, source=True, destination=False) or []
            if cmds.nodeType(c) in TIME_CURVES]


def _driven(plug):
    """What drives `plug` other than a time curve (a constraint, a connection), or None."""
    for node in cmds.listConnections(plug, source=True, destination=False,
                                     skipConversionNodes=True) or []:
        if cmds.nodeType(node) not in TIME_CURVES:
            return node
    return None


def restore(rig):
    """Every value the match wrote, back at its rest: time curves deleted, the value written.
    Returns how many plugs it touched."""
    touched = 0
    for one in limbs(rig) if rig else []:
        for node, attr, rest in _plugs(one):
            if rest is None:
                continue
            rests = rest if isinstance(rest, tuple) else (rest,)
            for channel, value in zip(_channels(attr), rests):
                plug = node + "." + channel
                if _driven(plug) or cmds.getAttr(plug, lock=True):
                    continue
                curves = _time_curves(plug)
                if curves:
                    cmds.delete(curves)
                if curves or abs(cmds.getAttr(plug) - value) > CONSTANT:
                    cmds.setAttr(plug, value)
                    touched += 1
    return touched


def _read(limb):
    """One frame of what `frame_values` needs, read off the scene."""
    out = {"fkx": [_world(j) for j in limb.fkx], "root_parent": _world(limb.root_parent)}
    if limb.foot:
        out["toes"] = _world(limb.foot.fkx)
        for node in (limb.foot.handle, limb.foot.offset):
            out[node] = (_world(node), _world(_parent(node)),
                         tuple(cmds.getAttr(node + ".translate")[0]))
    return out


def frames_of(start, end):
    """The bake's frames: start, start + 1, ... up to end."""
    out, frame = [], float(start)
    while frame <= end + 1e-6:
        out.append(frame)
        frame += 1.0
    return out


def carry(rig, start, end):
    """The IK limbs take the FK limbs' shape over start..end (`frame_values` on every frame).
    Returns a line for the status, '' when every IK limb stood as its FK already."""
    found = limbs(rig) if rig else []
    if not found:
        return ""
    restore(rig)
    frames = frames_of(start, end)
    now = cmds.currentTime(query=True)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    series = dict((one.label, {}) for one in found)
    try:
        for frame in frames:
            cmds.currentTime(frame, update=True)
            for one in found:
                for key, value in frame_values(one, _read(one)).items():
                    series[one.label].setdefault(key, []).append(value)
        notes, skipped = [], []
        for one in found:
            plugs = dict(((node, attr), rest) for node, attr, rest in _plugs(one))
            rests = {}
            for (node, attr), values in series[one.label].items():
                if (node, attr) not in plugs:
                    continue
                rest = plugs[(node, attr)]
                if attr == "translate":
                    rest = rest or tuple(cmds.getAttr(node + ".translate")[0])
                    rests[node] = rest
                    columns = list(zip(*values))
                    kinds = [plan_series(col, r, TOL_CM) for col, r in zip(columns, rest)]
                    if all(kind == "rest" for kind, _ in kinds):
                        continue
                    keep(node)
                    for channel, (kind, value) in zip(TRANSLATE, kinds):
                        _write(node + "." + channel, frames, kind, value, skipped)
                else:
                    kind, value = plan_series(values, rest, TOL_RATIO)
                    _write(node + "." + attr, frames, kind, value, skipped)
            note = summary(one.label, series[one.label], one, rests)
            if note:
                notes.append(note)
    finally:
        cmds.currentTime(now, update=True)
        cmds.autoKeyframe(state=auto)
    text = ("the IK limbs take the FK's shape: " + "; ".join(notes)) if notes else ""
    if skipped:
        text += ("; " if text else "") + "not written (driven or locked): " + ", ".join(
            sorted(set(_leaf(p.split(".")[0]) + "." + p.split(".")[-1] for p in skipped)))
    return text


def _write(plug, frames, kind, value, skipped):
    if _driven(plug) or cmds.getAttr(plug, lock=True):
        skipped.append(plug)
        return
    curves = _time_curves(plug)
    if curves:
        cmds.delete(curves)
    if kind in ("rest", "value"):
        cmds.setAttr(plug, value)
        return
    node, channel = plug.rsplit(".", 1)
    for frame, v in zip(frames, value):
        cmds.setKeyframe(node, attribute=channel, time=frame, value=v)
