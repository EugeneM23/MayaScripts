"""maya_walk.meanpose - a walk's mean pose, and the correction an animator makes to it (2026-10-15).

The animator: «кнопочку которая рядом с нашей походкой будет создавать manny rig на котором будет наша средняя
поза и меняя анимацию на этом риге мы будем менять нашу позу для всего цикла». The rig is maya_walk.meanrig; this
module is what it reads and writes, numpy only (no Maya):

- `mean_pose(walk)`: the walk's mean pose on its own skeleton - each bone by FK of its local means (an abstract
  pose: each bone's mean is taken alone), the legs then given the correction's height, width, knees and feet;
- `measure(worlds, walk)`: what is read off a pose of the walk's skeleton - the upper body's local rotations, the
  pelvis's height over the root, the feet's width, each knee's and foot's heading about up;
- `combine(fix, base, now)`: the correction moved by what changed between two readings (`now` against `base`);
- `correct(clip, fix)`: the cycle's frames with the upper body's correction in them, before the analysis - every
  frame's local of a corrected bone turned as its mean was (the motion about the mean kept), the body by FK, each
  leg solved again from its new hip onto its old ankle so the feet stay where the cycle plants them, a helper that
  followed a bone rigidly following it again. The legs' own corrections (height, width, knees, feet) are the
  model's: `Walk.fix`, added where a pose's are.

The correction lives beside the walk's file as <walk>.walkfix.json (`load`, `save`). The design:
docs/superpowers/specs/2026-10-15-walk-mean-pose-rig-design.md.
"""
import json
import math
import os

import numpy as np

from . import model as wm

FORMAT = "skeldar.walkfix"
VERSION = 1
SUFFIX = ".walkfix.json"
SIDES = ("l", "r")
LEGS = ("thigh", "calf", "foot")
UPPER_KINDS = ("pelvis", "spine", "head", "arm", "finger")
MIN_TURN = math.radians(0.01)      # a bone turned less than this between two readings did not move
MIN_CM = 0.01                      # ... a length changed less than this did not change


class Refusal(Exception):
    """A correction this tool does not read; the message says why."""


def empty():
    return {"rot": {}, "height": 0.0, "width": 0.0, "knee": {"l": 0.0, "r": 0.0}, "toe": {"l": 0.0, "r": 0.0}}


def is_empty(fix):
    return (not fix.get("rot") and abs(fix.get("height", 0.0)) < 1e-9 and abs(fix.get("width", 0.0)) < 1e-9
            and all(abs(fix.get(k, {}).get(s, 0.0)) < 1e-12 for k in ("knee", "toe") for s in SIDES))


def model_fix(fix):
    """What `Walk.fix` takes: the legs' share of a correction."""
    return {"height": float(fix.get("height", 0.0)), "width": float(fix.get("width", 0.0)),
            "knee": dict((s, float(fix.get("knee", {}).get(s, 0.0))) for s in SIDES),
            "toe": dict((s, float(fix.get("toe", {}).get(s, 0.0))) for s in SIDES)}


# ---- the file ----

def path_for(walk_path):
    """The correction's file beside a walk's file (<walk>.walk.gz -> <walk>.walkfix.json)."""
    from . import files
    base = walk_path[:-len(files.SUFFIX)] if walk_path.endswith(files.SUFFIX) else walk_path
    return base + SUFFIX


def loads(data, what="the correction"):
    """The correction from the plain data `dumps` gives (a file's, a walker's attribute); empty for none."""
    if not data:
        return empty()
    if data.get("format") != FORMAT or int(data.get("version", 0)) > VERSION:
        raise Refusal("%s is not a correction this tool reads" % what)
    fix = empty()
    fix["rot"] = dict((name, np.array(m, float).reshape(3, 3)) for name, m in data.get("rot", {}).items())
    fix["height"] = float(data.get("height", 0.0))
    fix["width"] = float(data.get("width", 0.0))
    for key in ("knee", "toe"):
        fix[key] = dict((s, float(data.get(key, {}).get(s, 0.0))) for s in SIDES)
    return fix


def dumps(fix):
    """The plain data (JSON) of the correction `fix`; {} for none."""
    if is_empty(fix):
        return {}
    return {"format": FORMAT, "version": VERSION,
            "rot": dict((name, [round(float(v), 12) for v in np.asarray(m).reshape(9)]) for name, m in fix["rot"].items()),
            "height": float(fix["height"]), "width": float(fix["width"]),
            "knee": dict((s, float(fix["knee"][s])) for s in SIDES), "toe": dict((s, float(fix["toe"][s])) for s in SIDES)}


def load(path):
    """The correction in `path`, or an empty one when there is none."""
    if not os.path.exists(path):
        return empty()
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise Refusal("%s is not a walk correction (%s)" % (os.path.basename(path), error))
    return loads(data, os.path.basename(path))


def save(path, fix):
    """`fix` to `path`; an empty correction removes the file."""
    if is_empty(fix):
        if os.path.exists(path):
            os.remove(path)
        return
    data = dumps(fix)
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    temporary = path + ".part"
    with open(temporary, "w") as handle:
        json.dump(data, handle, indent=1)
    if os.path.exists(path):
        os.remove(path)
    os.rename(temporary, path)


# ---- geometry ----

def _unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def turn_between(a, b):
    """The least rotation taking direction `a` onto `b`, row-vector (a . R = b, both unit)."""
    a, b = _unit(a), _unit(b)
    axis = np.cross(a, b)
    s, c = float(np.linalg.norm(axis)), float(np.dot(a, b))
    if s < 1e-12:
        if c > 0.0:
            return np.eye(3)
        axis = wm._any_perpendicular(a)
        s = 0.0
        c = -1.0
    k = axis / max(float(np.linalg.norm(axis)), 1e-12)
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    column = np.eye(3) + s * K + (1.0 - c) * (K @ K)       # column-vector: M a = b
    return column.T


def _leg_turns(h0, k0, a0, h1, k1, a1):
    """(thigh turn, calf turn), row-vector: each bone's frame carried from the old hip-knee-ankle onto the new by
    the turn that takes the bone onto its new direction and the leg's plane onto its new plane (the least one
    when either leg stands straight)."""
    n0, n1 = np.cross(k0 - h0, a0 - h0), np.cross(k1 - h1, a1 - h1)
    out = []
    for u0, u1 in ((k0 - h0, k1 - h1), (a0 - k0, a1 - k1)):
        if np.linalg.norm(n0) > 1e-9 and np.linalg.norm(n1) > 1e-9:
            out.append(wm.align(_unit(u0), _unit(_perp(n0, u0)), _unit(u1), _unit(_perp(n1, u1))))
        else:
            out.append(turn_between(u0, u1))
    return out


def _perp(n, u):
    """`n` made perpendicular to `u` (a plane's normal against a bone in it: already so, to round-off)."""
    u = _unit(u)
    return n - np.dot(n, u) * u


def heading(v, walk):
    """A direction's angle about up, from the walk's forward toward its left (radians)."""
    return math.atan2(float(np.dot(v, walk.side)), float(np.dot(v, walk.fwd)))


def knee_turn(base, now):
    """How far a knee turned (radians) from the reading `base` to `now` (each (hip, knee - hip, ankle)): about
    the leg's line as it stands now, ankle to hip (right hand) - the axis the model turns a knee about
    (`turned_about(bend, -e, turn)`) - from the old bend laid across the new line. A leg that only moved (the
    pelvis lowered, the feet apart) reads no turn; a straight leg reads none."""
    hip, bend, ankle = now
    a = _unit(hip - ankle)
    ref = base[1] - np.dot(base[1], a) * a
    cur = bend - np.dot(bend, a) * a
    if np.linalg.norm(ref) < 1e-6 or np.linalg.norm(cur) < 1e-6:
        return 0.0
    return math.atan2(float(np.dot(np.cross(ref, cur), a)), float(np.dot(ref, cur)))


KNEE_BENT = math.radians(10.0)      # a knee's turn is read only while the leg is bent this much in both readings...
KNEE_FLIP = math.radians(120.0)     # ...and under this: past it the IK solver flipped the knee (2026-10-27)


def leg_bend(knee):
    """A leg's knee bend (radians, 0 straight) from a reading's (hip, knee - hip, ankle)."""
    hip, thigh, ankle = (np.asarray(v, float) for v in knee)
    shin = ankle - (hip + thigh)
    a, b = float(np.linalg.norm(thigh)), float(np.linalg.norm(shin))
    if a < 1e-9 or b < 1e-9:
        return 0.0
    return math.acos(max(-1.0, min(1.0, float(np.dot(thigh, shin)) / (a * b))))


def knee_readable(base, now, turn):
    """A knee's turn is the animator's only while the leg is bent KNEE_BENT in both readings and the turn is under
    KNEE_FLIP: a straightened IK leg flips its knee (the live key rigs read 78-161 deg there, 2026-10-27)."""
    return min(leg_bend(base), leg_bend(now)) >= KNEE_BENT and abs(turn) <= KNEE_FLIP


def _wrapped(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def _bend(hip, knee, ankle):
    e = _unit(ankle - hip)
    b = (knee - hip) - np.dot(knee - hip, e) * e
    return b if np.linalg.norm(b) > 1e-9 else None


def _children(parents):
    kids = dict((j, []) for j in range(len(parents)))
    for j, p in enumerate(parents):
        if p >= 0:
            kids[p].append(j)
    return kids


def _order(parents):
    kids, queue, out = _children(parents), [j for j, p in enumerate(parents) if p < 0], []
    while queue:
        j = queue.pop(0)
        out.append(j)
        queue.extend(kids[j])
    return out


def _below(j, kids):
    out, stack = [], [j]
    while stack:
        k = stack.pop()
        out.append(k)
        stack.extend(kids[k])
    return out


def upper_bones(walk):
    """The bones whose local rotation the correction reads: the pelvis, spine, neck, head, clavicles, arms and
    fingers - no twist bone (it rides its parent), no helper, no leg, no root."""
    return [n for j, n in enumerate(walk.names)
            if walk.kind[j] in UPPER_KINDS and "_twist_" not in n and walk.parents[j] >= 0]


# ---- the mean pose ----

def mean_pose(walk, fix=None):
    """{name: 4x4 world} - the walk's mean pose on its own skeleton: the root at its mean rotation on the walk's
    origin, every bone by FK of its local means (rotation and translation); then the legs given the correction's
    height (the pelvis and the body over it raised), width (each ankle half of it out), knees (the bend turned
    about the hip-ankle line) and feet (the foot and its toes turned about up at the ankle)."""
    fix = model_fix(fix or empty())
    names, parents = walk.names, walk.parents
    worlds = {}
    for j in _order(parents):
        p = parents[j]
        if p < 0:
            worlds[j] = wm.matrix(walk.wmean[j], walk.origin if names[j] == "root" else walk.pos[j].mean(axis=0))
            continue
        local = wm.matrix(walk.lmean[j], walk.lt[j].mean(axis=0))
        worlds[j] = local @ worlds[p]
    _legs_fixed(walk, worlds, fix)
    return dict((names[j], worlds[j]) for j in worlds)


def _legs_fixed(walk, worlds, fix):
    """The correction's legs put on a pose `worlds` ({index: 4x4}) of the walk's skeleton, in place."""
    idx, kids, up = walk.index, _children(walk.parents), walk.up
    if "pelvis" not in idx or not all("%s_%s" % (b, s) in idx for b in LEGS for s in SIDES):
        return
    pelvis = idx["pelvis"]
    feet = dict((s, idx["foot_" + s]) for s in SIDES)
    ankles = dict((s, worlds[feet[s]][3, :3].copy()) for s in SIDES)
    foot_trees = dict((s, _below(feet[s], kids)) for s in SIDES)
    leg_trees = set(j for s in SIDES for j in _below(idx["thigh_" + s], kids))
    if abs(fix["height"]) > 1e-12:
        for j in _below(pelvis, kids):
            worlds[j] = worlds[j].copy()
            worlds[j][3, :3] += fix["height"] * up
    for side in SIDES:
        sign = 1.0 if side == "l" else -1.0
        th, ca, fo = (idx["%s_%s" % (b, side)] for b in LEGS)
        old = dict((j, worlds[j].copy()) for j in leg_trees if j in _below(th, kids))
        h0, k0, a0 = old[th][3, :3], old[ca][3, :3], old[fo][3, :3]
        target = ankles[side] + sign * 0.5 * fix["width"] * walk.side
        l1, l2 = float(np.linalg.norm(walk.lt[ca].mean(axis=0))), float(np.linalg.norm(walk.lt[fo].mean(axis=0)))
        e = _unit(target - h0)
        bend = (k0 - h0) if fix["knee"][side] == 0.0 else wm.turned_about(k0 - h0, -e, fix["knee"][side])
        knee, ankle, _ = wm.two_bone(h0, target, l1, l2, bend, 1.0)
        rt, rc = _leg_turns(h0, k0, a0, h0, knee, ankle)
        worlds[th] = wm.matrix(old[th][:3, :3] @ rt, h0)
        worlds[ca] = wm.matrix(old[ca][:3, :3] @ rc, knee)
        toe = wm.exp_rot(up * fix["toe"][side]) if fix["toe"][side] else np.eye(3)
        for j in _below(th, kids):
            if j in (th, ca):
                continue
            if j in foot_trees[side]:
                rel = old[j][3, :3] - a0
                worlds[j] = wm.matrix(old[j][:3, :3] @ toe, ankle + rel @ toe)
            else:                                       # a twist bone rides its thigh or calf
                parent = walk.parents[j]
                local = old[j] @ np.linalg.inv(old[parent])
                worlds[j] = local @ worlds[parent]


# ---- reading ----

def measure(worlds, walk):
    """What the correction reads off a pose of the walk's skeleton ({name: 4x4 world}): {"local": {bone: 3x3}},
    "height" (the pelvis over the root, cm along up), "width" (the ankles apart along the walk's side axis),
    "knee" ({side: (hip, knee - hip, ankle)} - `knee_turn` compares two), "toe" ({side: the foot's heading,
    radians})."""
    W = lambda n: np.asarray(worlds[n], float)
    rot = lambda n: wm.orthonormal(W(n)[:3, :3])
    out = {"local": {}, "knee": {}, "toe": {}}
    for name in upper_bones(walk):
        parent = walk.names[walk.parents[walk.index[name]]]
        if name in worlds and parent in worlds:
            out["local"][name] = rot(name) @ rot(parent).T
    root = W("root")[3, :3] if "root" in worlds else np.zeros(3)
    out["height"] = float(np.dot(W("pelvis")[3, :3] - root, walk.up))
    out["width"] = float(np.dot(W("foot_l")[3, :3] - W("foot_r")[3, :3], walk.side))
    for side in SIDES:
        hip, knee, ankle = (W("%s_%s" % (b, side))[3, :3] for b in LEGS)
        out["knee"][side] = (hip, knee - hip, ankle)
        ball = "ball_" + side
        out["toe"][side] = heading(W(ball)[3, :3] - ankle, walk) if ball in worlds else 0.0
    return out


def combine(fix, base, now):
    """(the new correction, [(what moved, how much, unit)]): `fix` moved by what changed from the reading `base`
    to the reading `now` - a bone's local turned X = now . base^T makes its correction X . C; the height, the width,
    each knee's and foot's heading are added."""
    out = {"rot": dict((k, np.asarray(v, float)) for k, v in fix.get("rot", {}).items()),
           "height": float(fix.get("height", 0.0)), "width": float(fix.get("width", 0.0)),
           "knee": dict(fix.get("knee", {"l": 0.0, "r": 0.0})), "toe": dict(fix.get("toe", {"l": 0.0, "r": 0.0}))}
    moved = []
    for name, rot_now in now["local"].items():
        if name not in base["local"]:
            continue
        turn = rot_now @ base["local"][name].T
        deg = float(np.linalg.norm(wm.log_rot(turn)))
        if deg < MIN_TURN:
            continue
        out["rot"][name] = wm.orthonormal(turn @ out["rot"].get(name, np.eye(3)))
        moved.append((name, math.degrees(deg), "deg"))
    for key, label in (("height", "pelvis"), ("width", "width")):
        d = now[key] - base[key]
        if abs(d) >= MIN_CM:
            out[key] += d
            moved.append((label, d, "cm"))
    for key in ("knee", "toe"):
        for side in SIDES:
            d = knee_turn(base[key][side], now[key][side]) if key == "knee" \
                else _wrapped(now[key][side] - base[key][side])
            if key == "knee" and not knee_readable(base[key][side], now[key][side], d):
                continue
            if abs(d) >= MIN_TURN:
                out[key][side] = _wrapped(out[key][side] + d)
                moved.append(("%s_%s" % ("knee" if key == "knee" else "foot", side), math.degrees(d), "deg"))
    for name in [n for n, m in out["rot"].items() if float(np.linalg.norm(wm.log_rot(m))) < 1e-9]:
        del out["rot"][name]
    return out, moved


def describe(moved, limit=4):
    """«upperarm_l 12.0, spine_03 8.0 deg, pelvis -3.0 cm» - the largest first."""
    if not moved:
        return "nothing moved"
    turns = sorted([m for m in moved if m[2] == "deg"], key=lambda m: -abs(m[1]))
    lengths = sorted([m for m in moved if m[2] == "cm"], key=lambda m: -abs(m[1]))
    parts = []
    if turns:
        shown = turns[:limit]
        parts.append(", ".join("%s %.1f" % (n, v) for n, v, _ in shown) + " deg"
                     + (" (+%d more)" % (len(turns) - limit) if len(turns) > limit else ""))
    if lengths:
        parts.append(", ".join("%s %+.1f cm" % (n, v) for n, v, _ in lengths))
    return ", ".join(parts)


def summary(fix):
    """What a correction holds, for a line: «12 bones turned, pelvis -3.0 cm, width +2.0 cm, knees, feet»."""
    if is_empty(fix):
        return "no correction"
    parts = []
    if fix["rot"]:
        parts.append("%d bone%s turned" % (len(fix["rot"]), "" if len(fix["rot"]) == 1 else "s"))
    if abs(fix["height"]) >= MIN_CM:
        parts.append("pelvis %+.1f cm" % fix["height"])
    if abs(fix["width"]) >= MIN_CM:
        parts.append("width %+.1f cm" % fix["width"])
    for key, word in (("knee", "knees"), ("toe", "feet")):
        if any(abs(fix[key][s]) >= MIN_TURN for s in SIDES):
            parts.append("%s %s" % (word, "/".join("%+.0f" % math.degrees(fix[key][s]) for s in SIDES)))
    return ", ".join(parts)


# ---- into the cycle ----

def correct(clip, fix):
    """A new model.Clip: `clip` with the upper body's correction in every frame (the module docstring). An empty
    rotation part gives the clip back as it is."""
    rots = dict((n, np.asarray(m, float)) for n, m in (fix or {}).get("rot", {}).items() if n in clip.names)
    if not rots:
        return clip
    names, parents = clip.names, clip.parents
    index = dict((n, j) for j, n in enumerate(names))
    W = np.asarray(clip.worlds, float)
    J, F = W.shape[:2]
    R, P = W[..., :3, :3], W[..., 3, :3]
    kids = _children(parents)
    lr, lt = np.zeros((J, F, 3, 3)), np.zeros((J, F, 3))
    for j, p in enumerate(parents):
        if p >= 0:
            back = np.swapaxes(R[p], -1, -2)
            lr[j] = R[j] @ back
            lt[j] = np.einsum("fi,fij->fj", P[j] - P[p], back)
    for name, C in rots.items():
        j = index[name]
        if parents[j] < 0:
            continue
        mean = wm.mean_rot(lr[j])
        lr[j] = lr[j] @ mean.T @ C @ mean
    legs = dict((s, index["thigh_" + s]) for s in SIDES if all("%s_%s" % (b, s) in index for b in LEGS))
    solved = set()
    feet = {}
    for side, th in legs.items():
        solved.update(_below(th, kids))
        feet[side] = set(_below(index["foot_" + side], kids))
    helper = _helpers(names, parents)
    follows = _follows(W, helper, names, parents)
    newR, newP = R.copy(), P.copy()
    order = _order(parents)
    for j in order:
        p = parents[j]
        if p < 0 or j in solved:
            continue
        newR[j] = lr[j] @ newR[p]
        newP[j] = np.einsum("fi,fij->fj", lt[j], newR[p]) + newP[p]
        for s, th in legs.items():
            if parents[th] == j:
                _solve_leg(s, th, index, lr, lt, R, P, newR, newP, kids, feet[s])
    out = np.array(W, copy=True)
    out[..., :3, :3], out[..., 3, :3] = newR, newP
    for j in order:                         # a helper that followed a bone rigidly follows it again
        if j not in helper:
            continue
        if j in follows:
            b, rel = follows[j]
            out[j] = rel[None] @ out[b]
        elif parents[j] >= 0:
            p = parents[j]
            local = W[j] @ np.linalg.inv(W[p])
            out[j] = local @ out[p]
    return wm.Clip(names, parents, out, clip.fps, clip.up, clip.name)


def _solve_leg(side, th, index, lr, lt, R, P, newR, newP, kids, foot_tree):
    """A leg solved again on every frame: from its new hip onto its old ankle (its lengths, its plane turned the
    least); the foot and everything under it kept in the world - where the ankle is out of reach the leg stands
    straight at it, its shin stretched; a twist bone riding its thigh or calf by its local."""
    ca, fo = index["calf_" + side], index["foot_" + side]
    F = R.shape[1]
    parent = [k for k, v in kids.items() if th in v][0]
    hip = np.einsum("fi,fij->fj", lt[th], newR[parent]) + newP[parent]
    for f in range(F):
        h0, k0, a0 = P[th, f], P[ca, f], P[fo, f]
        l1, l2 = float(np.linalg.norm(k0 - h0)), float(np.linalg.norm(a0 - k0))
        knee, _, _ = wm.two_bone(hip[f], a0, l1, l2, k0 - h0, 1.0)
        # out of reach (a hip the turn raised over a straight leg): the leg straight at the ankle, its shin
        # stretched - the foot stays planted, and the target's own reach takes the pelvis down where it falls short
        rt, rc = _leg_turns(h0, k0, a0, hip[f], knee, a0)
        newR[th, f], newP[th, f] = R[th, f] @ rt, hip[f]
        newR[ca, f], newP[ca, f] = R[ca, f] @ rc, knee
        for j in foot_tree:
            newR[j, f], newP[j, f] = R[j, f], P[j, f]
    for j in _below(th, kids):
        if j in (th, ca) or j in foot_tree:
            continue
        q = [k for k, v in kids.items() if j in v][0]
        newR[j] = lr[j] @ newR[q]
        newP[j] = np.einsum("fi,fij->fj", lt[j], newR[q]) + newP[q]


def _helpers(names, parents):
    """The helper bones (model.HELPER_PREFIXES, and what hangs under one)."""
    out = set()
    for j in _order(parents):
        if names[j].startswith(wm.HELPER_PREFIXES) or (parents[j] >= 0 and parents[j] in out):
            out.add(j)
    return out


def _follows(W, helper, names, parents):
    """{helper: (the body bone it follows rigidly - the shallowest, (4x4) its relation)} in the clip `W`."""
    depth = {}
    for j in _order(parents):
        depth[j] = 0 if parents[j] < 0 else depth[parents[j]] + 1
    body = [j for j in range(len(names)) if j not in helper]
    inv = dict((b, np.linalg.inv(W[b])) for b in body)
    out = {}
    for h in helper:
        best = None
        for b in body:
            rel = W[h] @ inv[b]
            err = float(np.abs(rel - rel[0]).max())
            if err < wm.FOLLOW_TOL:
                key = (depth[b], err)
                if best is None or key < best[0]:
                    best = (key, b, rel[0])
        if best is not None:
            out[h] = (best[1], best[2])
    return out
