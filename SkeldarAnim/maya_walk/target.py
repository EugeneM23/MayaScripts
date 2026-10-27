"""maya_walk.target - a walk (the model's result) carried onto any skeleton.

Per frame: the Pose Library's transfer (`maya_poselib.posemath.Transfer`: bones paired by name or canonical
name, rotations carried through the two rests, the target's own lengths, the pelvis and the travel scaled
by the size ratio, from the target's PLACE); then the legs by IK in the target's own lengths onto the
walk's ankles mapped as the pelvis is (a planted foot stays planted at any size); the pelvis dropped per
frame where the target's legs fall short (walkmodel.smooth_cover); the helpers on the bones they follow in
the walk. Bones as data (`maya_poselib.scene.skeleton`'s dicts); the target is read at its REST.

numpy and maya.api.OpenMaya (through posemath) - no maya.cmds.
The design: docs/superpowers/specs/2026-10-12-walk-onto-any-skeleton-design.md.
"""
import numpy as np
import maya.api.OpenMaya as om

from maya_poselib import posemath as pm

from . import model as _walkmodel

SIDES = ("l", "r")
UP = np.array([0.0, 1.0, 0.0])
LEG_TWIN = 0.01        # legs within 1 % of the walk's, on a twin: carried at the walk's own size
#  The knee pop fix (2026-10-27, the gait guide's section 12: «колено щёлкает, когда нога в IK выпрямляется до
#  конца и сразу сгибается ... никогда не выпрямляют ногу до конца, а на кадрах, где она почти прямая, опускают
#  корень»): a CLICK is a local minimum of a leg's knee bend under POP_STRAIGHT whose curvature (its two
#  neighbours less twice it) is over POP_CURVE; around it (POP_WINDOW frames a side) the bend may not fall under
#  its own smoothed curve (Gaussian, POP_SIGMA frames) - the pelvis lowered for it while the foot stands, the
#  ankle drawn in while it swings (a centimetre in the air slides nothing)
POP_STRAIGHT = np.radians(15.0)
POP_CURVE = np.radians(6.0)
POP_WINDOW = 3
POP_SIGMA = 1.5
POP_ROUNDS = 3


def _model():
    """The walk's model (maya_walk.model)."""
    return _walkmodel


class Refusal(Exception):
    """A target this tool does not take; the message says why."""


def _np(m):
    return np.array(pm.flat(m)).reshape(4, 4)


def _om(a):
    return om.MMatrix([float(v) for v in np.asarray(a, float).reshape(16)])


def _angle(a, b):
    """The angle between two vectors (radians)."""
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.arccos(max(-1.0, min(1.0, float(np.dot(a, b)) / (na * nb)))))


def pops(bends):
    """{side: [frames]} - the clicks in each leg's knee bends (one value a frame, periodic): a local minimum under
    POP_STRAIGHT whose curvature is over POP_CURVE."""
    out = {}
    for side, m in bends.items():
        m = np.asarray(m, float)
        n = len(m)
        at = []
        for f in range(n):
            left, right = m[(f - 1) % n], m[(f + 1) % n]
            if m[f] <= left and m[f] <= right and m[f] < POP_STRAIGHT and left + right - 2.0 * m[f] > POP_CURVE:
                at.append(f)
        out[side] = at
    return out


def _smoothed(values, sigma):
    """A periodic Gaussian blur of `values` (one a frame)."""
    v = np.asarray(values, float)
    n = len(v)
    offsets = np.arange(n)
    distance = np.minimum(offsets, n - offsets)
    kernel = np.exp(-0.5 * (distance / max(sigma, 1e-6)) ** 2)
    return np.real(np.fft.ifft(np.fft.fft(v) * np.fft.fft(kernel / kernel.sum())))


def _stance(result, side, n):
    """(n,) bools: the foot `side` stands (the model's contacts, in the result's frames); all True without them."""
    contacts = ((result.info or {}).get("contacts") or {}).get(side)
    if not contacts:
        return np.ones(n, bool)
    out = np.zeros(n, bool)
    for a, b in contacts:
        span = (b - a) % n if b - a < n else n
        for f in range(n):
            if (f - a) % n <= span:
                out[f] = True
    return out


def _drop_for(hip, goal, limit):
    """The least pelvis drop (along UP) that brings `goal` within `limit` of `hip`; 0 when it is."""
    q = np.asarray(goal, float) - np.asarray(hip, float)
    if float(np.linalg.norm(q)) <= limit:
        return 0.0
    qu = float(np.dot(q, UP))
    disc = qu * qu - (float(np.dot(q, q)) - limit * limit)
    if disc < 0.0:
        return 0.0
    return max(0.0, -qu - disc ** 0.5)


def pops_line(pops):
    """«knee pops smoothed: 3 (L 9, 24; R 33), pelvis down up to 0.8 cm»."""
    found = pops.get("found") or {}
    where = "; ".join("%s %s" % (side.upper(), ", ".join(str(f) for f in at)) for side, at in sorted(found.items()) if at)
    text = "knee pops smoothed: %d (%s)" % (pops.get("fixed", 0), where)
    if pops.get("drop", 0.0) > 0.05:
        text += ", pelvis down up to %.1f cm" % pops["drop"]
    if pops.get("left"):
        text += ", %d left" % pops["left"]
    return text


def _unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v * 0.0


def _rot(m):
    """A world matrix's rotation as a numpy 3x3 (scale stripped)."""
    return _model().orthonormal(_np(m)[:3, :3])


def _leg_lengths(bones, leaves):
    """(thigh, calf) lengths of a leg at rest: hip to knee, knee to ankle."""
    th, ca, fo = (_np(bones[leaf]["rest"])[3, :3] for leaf in leaves)
    return float(np.linalg.norm(ca - th)), float(np.linalg.norm(fo - ca))


def at_rest(bones):
    """The skeleton standing at its rest: each bone's `world` its `rest` (a new dict)."""
    out = {}
    for leaf, bone in bones.items():
        fresh = dict(bone)
        fresh["world"] = list(bone["rest"])
        fresh.pop("drive", None)
        out[leaf] = fresh
    return out


class Retarget(object):
    """One walk onto one target, prepared once: the pairing, the size, the transfer, the target's leg
    bones and lengths, the helpers' relations. `frames(result)` carries an evaluated walk.

    `walk` the analysed walk (walkmodel.Walk), `statics` its skeleton {leaf: {parent, canonical, rest}},
    `target` the target {leaf: bone} as it stands (scene.skeleton's), `place` the target's root frame to
    walk from (16 floats; default: where the target stands), `scale` the size of the target against the
    walk's (default: 1 for a twin - posemath.twin, the same body - else `leg_ratio`: a stride is as long
    as the legs that take it)."""

    def __init__(self, walk, statics, target, place=None, scale=None):
        self.walk = walk
        self.statics = statics
        self.source = self._bones(walk.clip.worlds[:, 0])
        self.target = at_rest(target)
        self.pairs = pm.pairs(self.source, self.target)
        self.members = set(s for t, s in self.pairs.items() if not pm.is_helper(t))
        played = {}
        for t, s in self.pairs.items():
            played.setdefault(s, t)
        self.legs, self.lengths = {}, {}
        for side in SIDES:
            leaves = tuple(played.get("%s_%s" % (b, side)) for b in ("thigh", "calf", "foot"))
            if None in leaves:
                missing = [b for b, leaf in zip(("thigh", "calf", "foot"), leaves) if leaf is None]
                raise Refusal("the target has no %s for the %s leg - a skeleton with two legs only"
                              % (" / ".join(missing), "left" if side == "l" else "right"))
            self.legs[side] = leaves
            self.lengths[side] = _leg_lengths(self.target, leaves)
        if scale is not None:
            self.scale = float(scale)
        else:
            legs = self.leg_ratio()
            # the same body (posemath.twin: a median bone and every rest chord alike) on the same legs - the
            # twin test's median would let 6 changed leg bones of 30 through - is 1: its bind read two ways
            # (a skin's, the template's) differs in the 5th digit
            same = pm.twin(self.pairs, self.source, self.target) and abs(legs - 1.0) <= LEG_TWIN
            self.scale = 1.0 if same else legs
        self.transfer = pm.Transfer(self.source, self.target, self.pairs, self.members, scale=self.scale)
        self.place = om.MMatrix(place) if place is not None else self.transfer.place(target)
        self.pelvis = self.transfer.target_pelvis
        self.order = pm._ordered(self.target)
        self.helpers = self._helpers(played)
        self.root_bone = self.transfer.target_root
        self._solved_legs = set(leaf for leaves in self.legs.values() for leaf in leaves)

    # -- reading --

    def leg_ratio(self):
        """The target's legs (thigh + calf, at rest) against the walk's, the two sides averaged: the size a
        walk is carried at, so a longer-legged body takes longer steps and stands as high as its legs."""
        ratios = []
        for side in SIDES:
            walk_legs = _leg_lengths(self.statics, ("thigh_" + side, "calf_" + side, "foot_" + side))
            ratios.append(sum(self.lengths[side]) / max(sum(walk_legs), 1e-9))
        return float(np.mean(ratios))

    def _bones(self, worlds):
        """The walk's skeleton as posemath bones for one frame of worlds (J, 4, 4)."""
        out = {}
        for j, name in enumerate(self.walk.names):
            bone = dict(self.statics[name])
            bone["world"] = [float(v) for v in np.asarray(worlds[j]).reshape(16)]
            out[name] = bone
        return out

    def _helpers(self, played):
        """{target helper: (target body bone, the walk's helper index, its body's index)}: a helper the walk's
        own helper of that name plays keeps, frame by frame, the relation the walk's result gives it to the bone
        it follows there (translation x the size) - the walk's own, or the one a pose holds a weapon by."""
        out = {}
        for t, s in self.pairs.items():
            if not pm.is_helper(t) or s not in self.walk.index:
                continue
            follow = self.walk.follows.get(self.walk.index[s])
            if follow is None:
                continue
            body = played.get(self.walk.names[follow[0]])
            if body is None:
                continue
            out[t] = (body, self.walk.index[s], follow[0])
        return out

    def written(self):
        """The target bones whose rotations the walk keys: the paired members, the legs, the root frame's
        bone and the helpers it re-places."""
        out = set(self.helpers) | self._solved_legs
        out.update(t for t, s in self.pairs.items() if s in self.members)
        if self.root_bone is not None:
            out.add(self.root_bone)
        return sorted(out, key=lambda leaf: self.order.index(leaf))

    def translated(self):
        """The target bones whose translations the walk keys: the root frame's bone, the pelvis, the
        helpers it re-places (and what rides them)."""
        out = set(self.helpers)
        out.update(b for b in (self.root_bone, self.pelvis) if b is not None)
        for leaf in self.order:
            parent = self.target[leaf].get("parent")
            if pm.is_helper(leaf) and parent in out and parent != self.root_bone:
                out.add(leaf)
        return sorted(out, key=lambda leaf: self.order.index(leaf))

    # -- the frames --

    def _mapped(self, point, source_root, root_world):
        """A walk point carried into the target as the transfer carries the pelvis: its offset from the
        source's root frame, scaled, in the target's root frame."""
        d_local = (om.MVector(*[float(v) for v in point]) - pm.position(source_root)) * \
            pm.rotation(source_root).inverse()
        d_t = d_local * pm.rotation(self.transfer.root_offset).inverse() * self.scale
        p = pm.position(root_world) + d_t * pm.rotation(root_world)
        return np.array([p.x, p.y, p.z])

    def frames(self, result, knee_pops=True):
        """([{target leaf: om.MMatrix} a frame], info {"drop": [cm a frame], "short": cm, "scale", "pairs",
        "pops"}). `knee_pops`: the knee pop fix after the legs are solved (fix_pops)."""
        model = _model()
        n = result.frames
        first = self._bones(result.worlds[:, 0])
        outs, goals = [], []
        for f in range(n + 1):
            src = self._bones(result.worlds[:, f])
            root_world = self.transfer.travel(src, first) * self.place
            outs.append(self.transfer.frame(source=src, target=self.target, root_world=root_world))
            source_root = self.transfer._source_root_pose(src)
            goals.append(dict((side, self._mapped(result.worlds[self.walk.index["foot_" + side], f, 3, :3],
                                                  source_root, root_world)) for side in SIDES))
        need = np.array([self._need(out, goal) for out, goal in zip(outs[:-1], goals[:-1])])
        drop = model.smooth_cover(need, model.LOWER_BLUR * len(need) / getattr(self.walk, "strides", 1))   # a stride
        drop = np.append(drop, drop[0])
        relations = [self._relations(result.worlds[:, f]) for f in range(n + 1)]
        frames, short = self._solve_all(outs, goals, drop, relations)
        pops = {"found": {}, "fixed": 0, "left": 0, "drop": 0.0}
        if knee_pops:
            frames, short, drop, pops = self.fix_pops(outs, goals, need, drop, relations, frames, short, result)
        info = {"drop": [float(d) for d in drop], "short": short, "scale": self.scale,
                "pairs": len(self.pairs), "frames": n, "pops": pops}
        return frames, info

    def _solve_all(self, outs, goals, drop, relations):
        frames, short = [], 0.0
        for f, (out, goal, d) in enumerate(zip(outs, goals, drop)):
            final, frame_short = self._solve(out, goal, float(d), relations[f])
            frames.append(final)
            short = max(short, frame_short)
        return frames, short

    def bends(self, frames):
        """{side: (n,) knee bends, radians} of solved frames (the closing frame left out)."""
        out = {}
        for side in SIDES:
            th, ca, fo = self.legs[side]
            values = []
            for final in frames[:-1]:
                hip, knee, ankle = (_np(final[leaf])[3, :3] for leaf in (th, ca, fo))
                values.append(_angle(knee - hip, ankle - knee))
            out[side] = np.array(values)
        return out

    def fix_pops(self, outs, goals, need, drop, relations, frames, short, result):
        """The knee pop fix (POP_* above), up to POP_ROUNDS times. (frames, short, drop, {"found": {side:
        [frames]}, "fixed", "left", "drop": the extra pelvis drop at most, cm})."""
        model = _model()
        n = len(outs) - 1
        stance = dict((side, _stance(result, side, n)) for side in SIDES)
        found = pops(self.bends(frames))
        first = dict((side, list(frames_)) for side, frames_ in found.items())
        goals = [dict(goal) for goal in goals]
        base = np.array(drop[:-1], float)
        original = base.copy()
        for _ in range(POP_ROUNDS):
            if not any(found.values()):
                break
            bends = self.bends(frames)
            want_need = np.zeros(n)
            for side, at in found.items():
                if not at:
                    continue
                smooth = _smoothed(bends[side], POP_SIGMA)
                l1, l2 = self.lengths[side]
                th = self.legs[side][0]
                window = sorted(set((f + k) % n for f in at for k in range(-POP_WINDOW, POP_WINDOW + 1)))
                for f in window:
                    want = max(float(bends[side][f]), float(smooth[f]))
                    if want <= float(bends[side][f]) + 1e-9:
                        continue
                    limit = float(np.sqrt(l1 * l1 + l2 * l2 + 2.0 * l1 * l2 * np.cos(want)))
                    hip = _np(outs[f][th])[3, :3] - UP * float(drop[f])
                    if stance[side][f]:
                        want_need[f] = max(want_need[f], float(drop[f]) + _drop_for(hip, goals[f][side], limit))
                    else:
                        q = goals[f][side] - hip
                        d = float(np.linalg.norm(q))
                        if d > limit:
                            goals[f][side] = hip + q * (limit / d)
                            if f == 0:
                                goals[n][side] = goals[n][side] + (goals[0][side] - (hip + q))
            total = np.maximum(np.asarray(need, float), want_need)
            if total.max() > base.max() + 1e-9 or (want_need > base + 1e-9).any():
                cover = model.smooth_cover(total, model.LOWER_BLUR * n / getattr(self.walk, "strides", 1))
                base = np.maximum(base, cover)
            drop = np.append(base, base[0])
            frames, short = self._solve_all(outs, goals, drop, relations)
            found = pops(self.bends(frames))
        left = sum(len(v) for v in found.values())
        fixed = sum(len(v) for v in first.values()) - left
        added = float(np.max(base - original)) if n else 0.0
        return frames, short, drop, {"found": first, "fixed": max(fixed, 0), "left": left, "drop": max(added, 0.0)}

    def _reach(self, side):
        return self.walk.reach[side] * sum(self.lengths[side])

    def _need(self, out, goal):
        """The least pelvis drop that lets both legs reach this frame's goals."""
        need = 0.0
        for side in SIDES:
            hip = _np(out[self.legs[side][0]])[3, :3]
            q = goal[side] - hip
            limit = self._reach(side)
            if np.linalg.norm(q) <= limit * (1.0 + 1e-9):
                continue
            qu = float(np.dot(q, UP))
            disc = qu * qu - (float(np.dot(q, q)) - limit * limit)
            if disc >= 0.0:
                need = max(need, -qu - disc ** 0.5)
        return need

    def _relations(self, worlds):
        """{target helper: relation 4x4}: each helper against its body in one frame of the walk's result."""
        out = {}
        for leaf, (body, h, b) in self.helpers.items():
            rel = worlds[h] @ np.linalg.inv(worlds[b])
            rel[:3, :3] = _model().orthonormal(rel[:3, :3])
            rel[3, :3] *= self.scale
            out[leaf] = rel
        return out

    def _solve(self, out, goal, drop, relations):
        """The frame's final worlds: the pelvis dropped, the legs solved, every other bone on its transferred
        local over its (moved) parent, the helpers on their bones."""
        final, moved, short = {}, set(), 0.0
        for leaf in self.order:
            if leaf in final:
                continue
            parent = self.target[leaf].get("parent")
            if leaf == self.pelvis and drop > 0.0:
                m = _np(out[leaf])
                m[3, :3] -= UP * drop
                final[leaf] = _om(m)
                moved.add(leaf)
            elif leaf in (legs[0] for legs in self.legs.values()):
                side = [s for s in SIDES if self.legs[s][0] == leaf][0]
                short = max(short, self._leg(side, out, final, goal[side]))
                moved.update(self.legs[side])
            elif parent in moved:
                final[leaf] = (out[leaf] * out[parent].inverse()) * final[parent]
                moved.add(leaf)
            else:
                final[leaf] = om.MMatrix(out[leaf])
        for leaf in self.order:
            parent = self.target[leaf].get("parent")
            if leaf in self.helpers:
                final[leaf] = _om(relations[leaf]) * final[self.helpers[leaf][0]]
                moved.add(leaf)
            elif pm.is_helper(leaf) and parent in moved:
                final[leaf] = (out[leaf] * out[parent].inverse()) * final[parent]
                moved.add(leaf)
        return final, short

    def _leg(self, side, out, final, goal):
        model = _model()
        th, ca, fo = self.legs[side]
        parent = self.target[th].get("parent")
        thigh = (out[th] * out[parent].inverse()) * final[parent] if parent in final else om.MMatrix(out[th])
        hip = _np(thigh)[3, :3]
        shift = hip - _np(out[th])[3, :3]
        knee_tr = _np(out[ca])[3, :3] + shift
        ankle_tr = _np(out[fo])[3, :3] + shift
        l1, l2 = self.lengths[side]
        e = _unit(ankle_tr - hip)
        bend = (knee_tr - hip) - np.dot(knee_tr - hip, e) * e
        if np.linalg.norm(bend) < 1e-6:
            fwd = _np(self.place)[2, :3]
            bend = fwd - np.dot(fwd, e) * e
        bend = _unit(bend)
        knee, reached, short = model.two_bone(hip, goal, l1, l2, bend, self.walk.reach[side])
        e2 = _unit(reached - hip)
        bend2 = _unit((knee - hip) - np.dot(knee - hip, e2) * e2)
        n_tr, n_new = _unit(np.cross(e, bend)), _unit(np.cross(e2, bend2))
        r_th = _rot(thigh) @ model.align(_unit(knee_tr - hip), n_tr, _unit(knee - hip), n_new)
        r_ca = _rot(out[ca]) @ model.align(_unit(ankle_tr - knee_tr), n_tr, _unit(reached - knee), n_new)
        final[th] = _om(model.matrix(r_th, hip))
        final[ca] = _om(model.matrix(r_ca, knee))
        final[fo] = _om(model.matrix(_rot(out[fo]), reached))
        return short
