"""Bone targets -> joint channels on a bare skeleton (the Pose Library, 2026-10-02).

The animator: «если анимация относится к ригу то мы должны сохранять анимацию не контроллов а
костей, таким образом мы сможем потом переносить эту анимацию на скелеты и на риги». A card holds
bones; `posemath.targets` turns it into the world matrix every TARGET bone should stand at; this
module turns those into the values a skeleton's channels take - the skeleton half of the spec's
"Onto a skeleton". The rig half, AdvancedSkeleton's controls, is `rigsolve`.

A member's local is `W*[t] . W*[parent]^-1` - its own target against its PARENT'S target, so a
chain of members solves parents and children alike from the targets, with no scene write in
between - and a joint's local rotation is `RA . R . JO` (row vectors, Maya's joint matrix
`S . RA . R . JO . IS . T`), so its rotate channels are `R = RA^-1 . rot(local) . JO^-1` in the
joint's rotate order, the euler NEAREST the channel's current value (`closestSolution`: the
alternate triple and the 360 multiples both count - a key next to the old one carries no flip,
trap 108). Only the PELVIS (canonical `pelvis`, else the leaf) also takes its translate: every
other bone keeps the target's own length (the spec's "rotations only"; `posemath.targets` already
placed it by the bone's own local translation). The ROOT is never written by a pose - the
character stays where it stands - and a member that is the root is left out without a word; an
animation carrying its travel asks for it (`root=True`, 2026-10-03: the clip starts where the
character stands and walks on from there), and then the root is written like the pelvis, rotate
and translate. A frame of an animation is solved with the previous frame's values as the
nearest-euler `seed`, so its curves never flip (trap 108). A skeleton with no
root of its own (`posemath.has_root`: Mixamo's Hips are its top joint AND its pelvis) has its
top joint written like the pelvis it is, rotate and translate: `posemath.targets` puts it on its
GROUND frame as it stands, which is what keeps that character in place (the final review,
2026-10-03: left out, the card's hips turn and height were lost, 15.8 deg on a twin).

The parent a joint's channels are relative to is its DAG parent. A card's `parent` is the nearest
JOINT above, and a group can stand between the two (a skeleton parked under a transform of its
own): the piece between them is read off the scene (`parentMatrix[0]` against the recorded
parent's world) and carried onto the parent's target, so such a joint still lands.

A channel a constraint, an expression or anything but a time curve or an animation layer drives
is not written (`keys.writable`: a constrained plug takes a `setAttr` silently and loses it - the
weapon link's constraint on `weapon_r` is the case); the bone is skipped and named in `skipped`,
with all three rotate channels left alone (two eulers of three are a different rotation).

Nothing here writes the scene: it reads the joints' current rotate values, their parents' worlds
and whether a plug is writable, and answers the values - each plug spelled with the joint's LONG
path: a skeleton's joints carry plain names (`pelvis`), so a short name unique now turns
ambiguous when a second skeleton arrives before a Blend session keys (trap 47).

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Onto a skeleton").
"""

import math
from collections import namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

from maya_poselib import keys
from maya_poselib import posemath as pm

# values:  {plug: FINAL value}; notes: [str]; skipped: {leaf (skeleton) or plug (rig): why}
Solution = namedtuple("Solution", "values notes skipped")

ROTATE = ("rotateX", "rotateY", "rotateZ")
TRANSLATE = ("translateX", "translateY", "translateZ")
PELVIS = "pelvis"

NOT_IN = "%d member(s) not in the skeleton: %s"
NAMED = 4


# ------------------------------------------------------------------- pure

def joint_channels(local, joint_orient, rotate_axis, rotate_order, current):
    """(rx, ry, rz) in degrees: the joint's rotate channels for its local matrix `local`.

    `R = RA^-1 . rot(local) . JO^-1` (`joint_orient` / `rotate_axis` are xyz eulers in degrees,
    the way Maya stores both whatever the rotate order), decomposed in `rotate_order` (cmds'
    0..5) and taken as the solution nearest `current` (degrees). Scale and translation in
    `local` are ignored. Pure (OpenMaya). A transform has no jointOrient: pass (0, 0, 0)."""
    jo = om.MEulerRotation(*[math.radians(v) for v in joint_orient]).asMatrix()
    ra = om.MEulerRotation(*[math.radians(v) for v in rotate_axis]).asMatrix()
    turn = ra.inverse() * pm.rotation(local) * jo.inverse()
    euler = om.MTransformationMatrix(turn).rotation().reorder(int(rotate_order))
    previous = om.MEulerRotation(*([math.radians(v) for v in current] + [int(rotate_order)]))
    euler = euler.closestSolution(previous)
    return (math.degrees(euler.x), math.degrees(euler.y), math.degrees(euler.z))


def pelvis_of(bones):
    """The leaf playing the pelvis: the bone whose canonical name is `pelvis`, else the leaf
    `pelvis`, else None. Pure."""
    for leaf in sorted(bones):
        if (bones[leaf] or {}).get("canonical") == PELVIS:
            return leaf
    return PELVIS if PELVIS in bones else None


def _depth(bones, leaf):
    depth, node, seen = 0, (bones.get(leaf) or {}).get("parent"), set()
    while node in bones and node not in seen:
        seen.add(node)
        depth += 1
        node = bones[node].get("parent")
    return depth


def parents_first(bones, members):
    """`members` ordered parents first (by depth in `bones`, ties by name); leaves `bones` does
    not hold go last, in their own order. Pure."""
    known = sorted((m for m in members if m in bones), key=lambda m: (_depth(bones, m), m))
    return known + [m for m in members if m not in bones]


def local_of(target, parent_target):
    """A bone's local matrix for its world `target` under a parent standing at `parent_target`:
    `target . parent_target^-1` (row vectors). Pure."""
    return pm.matrix(target) * pm.matrix(parent_target).inverse()


def _named(leaves):
    shown = ", ".join(leaves[:NAMED])
    if len(leaves) > NAMED:
        shown += " and %d more" % (len(leaves) - NAMED)
    return shown


# ------------------------------------------------------------------ scene

def root_leaf(ref, bones):
    """The skeleton's root among `bones`: the bone whose path is the reference's `root`, else
    the shallowest bone (`posemath.root_of`). Pure."""
    path = getattr(ref, "root", None)
    if path:
        for leaf in sorted(bones):
            if (bones[leaf] or {}).get("path") == path:
                return leaf
    return pm.root_of(bones)


def _blocked(path, channels):
    """(channels' plugs, why the first unwritable one is not writable or "")."""
    plugs = ["%s.%s" % (path, ch) for ch in channels]
    for plug in plugs:
        ok, why = keys.writable(plug)
        if not ok:
            return plugs, "%s %s" % (plug.rsplit(".", 1)[-1], why)
    return plugs, ""


def _seeded(plugs, seed):
    """The rotate values `seed` ({plug: value}) holds for all of `plugs`, else None - two eulers
    of three from one frame and one from another are no reference at all."""
    if not seed:
        return None
    found = [seed.get(plug) for plug in plugs]
    if any(value is None for value in found):
        return None
    return [float(value) for value in found]


def solve(ref, bones, wanted, members, seed=None, root=False):
    """Solution for a bare skeleton: the FINAL rotate channels of every member joint (and the
    pelvis's translate) that put it on `wanted`.

    `ref` is the CharacterRef, `bones` `scene.skeleton(ref)[0]` ({leaf: {path, parent, rest,
    world, rotateOrder, jointOrient, rotateAxis}}), `wanted` {leaf: matrix (MMatrix or 16
    floats)} for every target bone - `posemath.targets` - and `members` the leaves to write. A
    bone missing from `wanted` stands where it stands. A member whose rotate channels are not
    writable is skipped and named (`skipped[leaf]`); a member the skeleton does not hold is
    noted.

    `seed` ({plug: value}, a previous frame's `Solution.values`) is the nearest-euler reference
    of every joint it names all three rotate channels of, in place of what the channel shows: an
    animation walk keys frame after frame, each frame's eulers nearest the previous frame's so
    the curves never flip (trap 108) - a channel the walk has not keyed yet still shows the
    take's value. `root` (an animation's travel): the skeleton's own root (`posemath.has_root`),
    when `wanted` holds it, is written too - rotate and translate, against its DAG parent, like
    the pelvis; its blocked channels land in `skipped[root]`. Without it the root is never
    written (the pose rule: the character stays where it stands)."""
    wanted = dict((leaf, pm.matrix(m)) for leaf, m in (wanted or {}).items())
    # a root of its own is written only for the travel (`root`); a top joint that is no root
    # (Mixamo's Hips: its pelvis) is a member like any other - `posemath.targets` keeps its
    # ground frame in place
    top = root_leaf(ref, bones) if pm.has_root(bones) else None
    write_root = bool(root) and top is not None and top in wanted
    pelvis = pelvis_of(bones)
    values, notes, skipped = {}, [], {}
    missing = []

    def target(leaf):
        if leaf in wanted:
            return wanted[leaf]
        return pm.matrix(bones[leaf]["world"])

    order = parents_first(bones, list(members or ()))
    if write_root and top not in order:
        order.insert(0, top)                          # the shallowest: before every member
    for leaf in order:
        if leaf not in bones:
            missing.append(leaf)
            continue
        if leaf == top and not write_root:
            continue
        bone = bones[leaf]
        path = bone["path"]
        parent = bone.get("parent")
        dag_parent = pm.matrix(cmds.getAttr(path + ".parentMatrix[0]"))
        if parent in bones:
            # the piece between the recorded parent joint and the DAG parent (a group), carried:
            # both read off the scene now, so it is the identity when nothing stands between
            above = pm.matrix(cmds.getAttr(bones[parent]["path"] + ".worldMatrix[0]"))
            piece = dag_parent * above.inverse()
            parent_world = piece * target(parent)
        else:
            parent_world = dag_parent
        local = local_of(target(leaf), parent_world)

        plugs, why = _blocked(path, ROTATE)
        if why:
            skipped[leaf] = why
        else:
            current = _seeded(plugs, seed)
            if current is None:
                current = [float(cmds.getAttr(p)) for p in plugs]
            channels = joint_channels(local, bone.get("jointOrient") or (0, 0, 0),
                                      bone.get("rotateAxis") or (0, 0, 0),
                                      bone.get("rotateOrder", 0), current)
            name = path
            for channel, value in zip(ROTATE, channels):
                values["%s.%s" % (name, channel)] = value

        if leaf == pelvis or leaf == top:
            t_plugs, t_why = _blocked(path, TRANSLATE)
            if t_why:
                skipped[leaf] = (skipped[leaf] + "; " if leaf in skipped else "") + t_why
            else:
                t = pm.position(local)
                name = path
                for channel, value in zip(TRANSLATE, (t.x, t.y, t.z)):
                    values["%s.%s" % (name, channel)] = value
    if missing:
        notes.append(NOT_IN % (len(missing), _named(missing)))
    return Solution(values, notes, skipped)
