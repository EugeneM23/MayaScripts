"""Walk Builder on a whole clip: its start, its walk and its stop (2026-11-17, numpy, pure).

docs/superpowers/specs/2026-11-17-walk-builder-whole-clip-design.md. A walker's own clip that does not loop (a start
into steps, steps into a stop, or both) is kept whole - its frames and timing - and edited:

- the walking frames take Walk Builder's change to the loop the clean cut out of the clip, as a DIFFERENCE laid over
  the clip's own frame at its phase (each joint's local turn and offset), so the clip keeps its own strides; at the
  parameters' own values the difference is nothing and the clip comes out as it went in;
- where the body stands the difference fades and the stance comes in from the same pose card (Start/Stop Builder's
  model, `maya_startstop.model`), weighted by how still the body is against the walk's own speed;
- the legs last: each foot's contact moved by one rigid motion (a planted foot never slides), the swing carried
  between, the legs by two-bone IK, the hips sunk where a down foot is out of reach.

`build(raw, loop, result, statics, bones=None, parts, share)` answers (worlds (J, F, 4, 4) in the raw clip's joint
order, info). Nothing here reads Maya.
"""
import math

import numpy as np

from maya_startstop import model as ss

WALK_SHARE = 0.75          # a stride as fast as this share of the loop's is walking
MIN_RUN = 8                # frames: the least walking run a clip with no whole walking stride is aligned on
REACH = 0.999              # a leg reaches no further than this share of its length
SINK_SIGMA = 3.0           # frames: the hips' sink smoothed
STANCE_SIGMA = 4.0         # frames: the stance's weight spread
JOLT = 1.0                 # cm a frame^2: the most the hand-over from a held pose to the walk may jolt the body
PACE_LOOK = 10             # frames past the fall the stance-to-walk distance is read over
PACE_POINTS = ("pelvis", "spine_05", "head")
LEGS = ("thigh", "calf", "foot")


class Refusal(Exception):
    pass


# ---- reading ----

def ss_clip(names, parents, worlds, fps, name):
    return ss.Clip(names, parents, np.asarray(worlds, float), fps, name)


def _rots(w):
    """(..., 3, 3) the rotations of worlds (..., 4, 4), scale and shear stripped."""
    return ss._batch_orthonormal(np.asarray(w)[..., :3, :3])


def _locals(clip, worlds):
    """(rots (J, 3, 3), offsets (J, 3)) of one frame's worlds (J, 4, 4): each joint's turn in its parent's rigid
    frame and its place there; a top joint's are its world's."""
    r = _rots(worlds)
    p = worlds[:, 3, :3]
    lr, lo = np.zeros_like(r), np.zeros((len(r), 3))
    for j, q in enumerate(clip.parents):
        if q < 0:
            lr[j], lo[j] = r[j], p[j]
        else:
            lr[j] = r[j] @ r[q].T
            lo[j] = (p[j] - p[q]) @ r[q].T
    return lr, lo


def _fk(clip, lr, lo, scales):
    """One frame's worlds (J, 4, 4) from locals, each joint's own scale (J, 3) put back on its rows."""
    J = len(clip.parents)
    r, p = np.zeros((J, 3, 3)), np.zeros((J, 3))
    for j in clip.order:
        q = clip.parents[j]
        if q < 0:
            r[j], p[j] = lr[j], lo[j]
        else:
            r[j] = lr[j] @ r[q]
            p[j] = lo[j] @ r[q] + p[q]
    out = np.zeros((J, 4, 4))
    out[:, :3, :3] = r * scales[:, :, None]
    out[:, 3, :3] = p
    out[:, 3, 3] = 1.0
    return out


def _strikes(analysis, side="l"):
    """The frames a foot comes down (the contacts' starts, a contact the clip opens on left out)."""
    return [int(c0) for c0, _c1 in analysis.feet[side]["contacts"] if c0 > 0]


def _speed(analysis):
    """(F,) the body's speed along the floor, cm/s (the centre of mass's)."""
    return np.asarray(analysis.com_speed, float)


def _body_points(clip, worlds):
    """(J, 3) every joint's place against the pelvis, in the root's heading frame (one frame's worlds)."""
    pelvis = worlds[clip.index["pelvis"], 3, :3]
    h = ss.yaw(ss.yaw_of(ss.orthonormal(worlds[clip.parents.index(-1)])))
    return (worlds[:, 3, :3] - pelvis) @ h.T


def _align(raw, loop, loop_cycle, t0, t1, step, grain=0.25):
    """The loop's phase at the raw stride (t0, t1)'s first frame: the one whose frames match the stride's best
    (each joint's place against the pelvis in the root's heading frame, summed over the stride). Strikes read
    off the two clips disagree by a frame at the loop's seam, and a phase a frame off turned an arm 6 deg."""
    pairs = [(raw.index[n], loop.index[n]) for n in raw.names if n in loop.index]
    rj, lj = [p[0] for p in pairs], [p[1] for p in pairs]
    frames = range(t0, t1)
    mine = [_body_points(raw, raw.worlds[:, f])[rj] for f in frames]
    best = None
    for phase in np.arange(0.0, loop_cycle.period, grain):
        cost = 0.0
        for i, f in enumerate(frames):
            w = loop_cycle.sample(phase + step * (f - t0) / float(t1 - t0))
            cost += float(np.sum((_body_points(loop, w)[lj] - mine[i]) ** 2))
        if best is None or cost < best[0]:
            best = (cost, float(phase))
    return best[1]


def phase_of(raw_a, loop_a, loop_cycle, loop_strides=1):
    """(phases (F,), walking strides [(t0, t1)], loop speed cm/s): every raw frame's place in the loop. Inside a
    walking stride (a left strike to the next, at least WALK_SHARE of the loop's speed) the stride maps linearly onto
    `period / loop_strides` of the loop from the phase matched at the first walking stride (_align); before the first
    walking stride and after the last the phase runs on at the loop's rate (the two clips share their fps)."""
    loop_speed = float(np.mean(_speed(loop_a)))
    strikes = _strikes(raw_a)
    raw_speed = _speed(raw_a)
    walking = []
    for t0, t1 in zip(strikes[:-1], strikes[1:]):
        if t1 > t0 and float(np.mean(raw_speed[t0:t1])) >= WALK_SHARE * loop_speed:
            walking.append((t0, t1))
    step = float(loop_cycle.period) / max(1, loop_strides)
    F = raw_a.clip.F
    if not walking:
        # less than a whole stride at walking pace (a short start, a short stop): the longest run of frames at
        # walking pace, matched against the loop at the loop's own rate
        fast = raw_speed >= WALK_SHARE * loop_speed
        runs, start = [], None
        for f in range(F + 1):
            if f < F and fast[f]:
                start = f if start is None else start
            elif start is not None:
                runs.append((start, f))
                start = None
        runs = [r for r in runs if r[1] - r[0] >= MIN_RUN]
        if not runs:
            raise Refusal("no walking to read the walk from (%d frame%s at walking pace, %d needed) - Start/Stop "
                          "Builder takes a clip with no walk" % (int(fast.sum()), "" if fast.sum() == 1 else "s",
                                                                  MIN_RUN))

        t0, t1 = max(runs, key=lambda r: r[1] - r[0])
        s0 = _align(raw_a.clip, loop_a.clip, loop_cycle, t0, t1, float(t1 - t0))
        phases = s0 + (np.arange(F) - t0).astype(float)
        return phases, [(t0, t1)], loop_speed
    s0 = _align(raw_a.clip, loop_a.clip, loop_cycle, walking[0][0], walking[0][1], step)
    phases = np.zeros(F)
    first, last = walking[0][0], walking[-1][1]
    # the strides between the first and the last walking strike, walking or not (a slow stride inside the walk
    # keeps the phase running)
    inside = [(t0, t1) for t0, t1 in zip(strikes[:-1], strikes[1:]) if first <= t0 and t1 <= last]
    count = 0.0
    for t0, t1 in inside:
        for f in range(t0, t1):
            phases[f] = s0 + step * (count + (f - t0) / float(t1 - t0))
        count += 1.0
    end_phase = s0 + step * count
    for f in range(0, first):
        phases[f] = s0 - (first - f)
    for f in range(last, F):
        phases[f] = end_phase + (f - last)
    return phases, walking, loop_speed


# ---- the walk's difference ----

def walk_difference(raw, loop_cycle, result_cycle, phases, names_raw, names_walk):
    """(J, F) local turns and offsets of the raw clip with the walk's change at each frame's phase laid over: the
    change is the result's local against the loop's own (each joint's turn in its own frame, its offset in its
    parent's; the top joint's place turned from the loop's heading onto the clip's)."""
    J, F = raw.worlds.shape[:2]
    idx = dict((n, i) for i, n in enumerate(names_walk))
    lr = np.zeros((J, F, 3, 3))
    lo = np.zeros((J, F, 3))
    loop_clip = loop_cycle.clip
    for f in range(F):
        rl, ro = _locals(raw, raw.worlds[:, f])
        S = loop_cycle.sample(phases[f])
        R = result_cycle.sample(phases[f])
        sl, so = _locals(loop_clip, S)
        rr, rro = _locals(loop_clip, R)
        for j, name in enumerate(names_raw):
            w = idx.get(name)
            if w is None:
                lr[j, f], lo[j, f] = rl[j], ro[j]
                continue
            turn = rr[w] @ sl[w].T                     # the result's local against the loop's, in the joint's frame
            lr[j, f] = turn @ rl[j]
            d = rro[w] - so[w]
            if raw.parents[j] < 0:                     # the top joint: its place's change carried by the headings
                h_loop = ss.yaw(ss.yaw_of(sl[w]))
                h_raw = ss.yaw(ss.yaw_of(rl[j]))
                d = d @ h_loop.T @ h_raw
            lo[j, f] = ro[j] + d
    return lr, lo


# ---- the whole clip ----

def _scales(worlds):
    return np.linalg.norm(np.asarray(worlds)[:, :3, :3], axis=2)


def _blend(lr_a, lo_a, lr_b, lo_b, w):
    """Locals from a (w 0) to b (w 1): turns slerped, offsets lerped with their lengths lerped."""
    if w <= 0.0:
        return lr_a, lo_a
    if w >= 1.0:
        return lr_b, lo_b
    lr = np.array([ss.slerp(a, b, w) for a, b in zip(lr_a, lr_b)])
    lo = (1.0 - w) * lo_a + w * lo_b
    na, nb = np.linalg.norm(lo_a, axis=1), np.linalg.norm(lo_b, axis=1)
    n = np.linalg.norm(lo, axis=1)
    keep = n > 1e-9
    lo[keep] *= (((1.0 - w) * na + w * nb)[keep] / n[keep])[:, None]
    return lr, lo


def _rigid(m):
    out = np.eye(4)
    out[:3, :3] = ss.orthonormal(m)
    out[3, :3] = np.asarray(m)[3, :3]
    return out


def _mix(a, b, w):
    """Two rigid transforms mixed: turn slerped, place lerped."""
    out = np.eye(4)
    out[:3, :3] = ss.slerp(a[:3, :3], b[:3, :3], w)
    out[3, :3] = (1.0 - w) * a[3, :3] + w * b[3, :3]
    return out


def _leg_fix(clip, worlds, targets, side, reach=REACH):
    """The leg of `side` solved onto its foot target, in place (worlds (J, 4, 4)): the thigh and the calf turned the
    least way onto the two-bone IK's knee (toward the leg's own bend), the foot standing in its target's turn. The
    children of the three bones carried rigidly. Returns how far it fell short."""
    ix = clip.index
    th, ca, fo = (ix["%s_%s" % (b, side)] for b in LEGS)
    hip, knee0, ankle0 = worlds[th, 3, :3], worlds[ca, 3, :3], worlds[fo, 3, :3]
    l1, l2 = float(np.linalg.norm(knee0 - hip)), float(np.linalg.norm(ankle0 - knee0))
    goal = targets[3, :3]
    e = ss._unit(goal - hip)
    bend = ss.bend_side(knee0 - hip, e)
    knee, reached, short = ss.two_bone(hip, goal, l1, l2, bend, reach)
    before = {j: worlds[j].copy() for j in range(len(worlds))}
    new = {}
    new[th] = _aimed(worlds[th], knee0 - hip, knee - hip, bend)
    new[th][3, :3] = hip
    new[ca] = _aimed(worlds[ca], ankle0 - knee0, reached - knee, bend)
    new[ca][3, :3] = knee
    foot = np.array(worlds[fo])
    foot[:3, :3] = ss.orthonormal(targets) * np.linalg.norm(worlds[fo][:3, :3], axis=1)[:, None]
    foot[3, :3] = reached
    new[fo] = foot
    _carry(clip, worlds, before, new)
    return float(short)


def _aimed(world, old_dir, new_dir, bend):
    """`world` turned the least way taking the direction `old_dir` (with the plane of `bend`) onto `new_dir`."""
    u0, u1 = ss._unit(old_dir), ss._unit(new_dir)
    n0, n1 = ss._unit(np.cross(u0, bend)), ss._unit(np.cross(u1, bend))
    if np.linalg.norm(n0) < 1e-9 or np.linalg.norm(n1) < 1e-9:
        return np.array(world)
    o = np.array([u0, n0, np.cross(u0, n0)])
    m = np.array([u1, n1, np.cross(u1, n1)])
    turn = o.T @ m
    out = np.array(world)
    out[:3, :3] = world[:3, :3] @ turn
    return out


def _carry(clip, worlds, before, new):
    """The joints in `new` set, every joint under one of them carried as it hung off it."""
    changed = dict(new)
    for j in clip.order:
        if j in changed:
            worlds[j] = changed[j]
            continue
        q = clip.parents[j]
        if q >= 0 and q in changed:
            changed[j] = before[j] @ np.linalg.inv(before[q]) @ changed[q]
            worlds[j] = changed[j]


def build(raw, loop, result, statics=None, bones=None, parts=None, share=1.0, k=None):
    """(worlds (J, F, 4, 4), info): the raw clip (ss.Clip, every frame) edited by the walk's change and the stance.

    `loop` the clean loop the walk was read from and `result` Walk Builder's evaluated loop (ss.Clip each, the
    walk's joint order, with their closing frames); `statics` the raw skeleton's rest ({leaf: parent, canonical,
    rest}) and `bones` the pose card's bones (None: no pose - the stance stays the clip's own); `parts` the pose's
    parts (walk Builder's names), `share` its share; `k` Start/Stop's knobs for the stance."""
    raw_a = ss.Analysis(raw)
    # the clip's own standing frames stand in the pose whatever the body does there: a start begins in it, a stop
    # ends in it (Unreal's starts move from frame 0, 2026-11-17)
    raw_a.hold_reference = True
    loop_a = ss.Analysis(loop)
    loop_cycle = ss.Cycle(loop)
    result_cycle = ss.Cycle(result)
    # how many strides the loop holds: its period against the raw clip's own stride
    raw_strikes = _strikes(raw_a)
    lengths = np.diff(raw_strikes) if len(raw_strikes) > 1 else np.array([loop_cycle.period])
    strides = max(1, int(round(loop_cycle.period / max(float(np.median(lengths)), 1.0))))
    phases, walking, loop_speed = phase_of(raw_a, loop_a, loop_cycle, strides)
    lr, lo = walk_difference(raw, loop_cycle, result_cycle, phases, raw.names, loop.names)
    F, J = raw.F, raw.J
    # the stance: Start/Stop Builder's model on the same clip with the same pose, its run the clip's own, standing
    # where the body is slower than the walk
    # the stance's weight: how still the body is against the walk's own speed, eased (smoothstep) and spread over
    # STANCE_SIGMA frames - a start reaching walking pace in 8 frames turned a crouched pose into a guard in as many
    eased = np.array([ss._smooth(float(x)) for x in raw_a.stillness_at(loop_speed)])
    pad = int(3 * STANCE_SIGMA) + 1          # the ends held as they are: the clip's first frame stands in the pose
    still = ss._blur(np.concatenate([np.full(pad, eased[0]), eased, np.full(pad, eased[-1])]), STANCE_SIGMA)
    # never under the weight itself (joined softly): the spread only lengthens a stance into the walk, never takes the pose off
    # the clip's own standing frames (the blur alone left frame 0 of a start at 0.93)
    still = np.clip(eased + (1.0 - eased) * still[pad:pad + len(eased)], 0.0, 1.0)
    stance = None
    if bones is not None and share > 0.0:
        kk = dict(k or {})
        names = set(parts or ("torso", "pelvis", "knees", "arm_l", "arm_r", "feet"))
        for part in ss.PARTS:
            on = (part in names) if part != "arms" else bool(names & {"arm_l", "arm_r", "arms"})
            kk["share_" + part] = share if on else 0.0
        kk["final_speed"] = kk["stance_speed"] = loop_speed
        pose = ss.prepare(raw_a, statics, bones)
        # the pose all through (the walk it hands over to wears the same pose; the clip's own run between them sent
        # a goblin through the plain clip and back in a few frames)
        stance = ss.evaluate(raw_a, pose, k=ss.knobs(**kk)).worlds
        still = _paced(raw, lr, lo, stance, still)
    out = np.zeros_like(raw.worlds)
    for f in range(F):
        scales = _scales(raw.worlds[:, f])
        flr, flo = lr[:, f], lo[:, f]
        if stance is not None and still[f] > 0.0:
            sr, so = _locals(raw, stance[:, f])
            flr, flo = _blend(flr, flo, sr, so, float(still[f]))
        out[:, f] = _fk(raw, flr, flo, scales)
    # the legs: each contact moved by one rigid motion, the swing carried between, the hips sunk where a planted
    # foot is out of reach
    targets = dict((s, _foot_targets(raw_a, raw.worlds[raw.index["foot_" + s]], out[raw.index["foot_" + s]], s))
                   for s in ss.SIDES)
    need = np.zeros(F)
    for f in range(F):
        for s in ss.SIDES:
            if not raw_a.feet[s]["down"][f]:
                continue
            th, ca, fo = (raw.index["%s_%s" % (b, s)] for b in LEGS)
            length = (np.linalg.norm(out[ca, f, 3, :3] - out[th, f, 3, :3])
                      + np.linalg.norm(out[fo, f, 3, :3] - out[ca, f, 3, :3]))
            # no further than the legs' reach - or the clip's own stretch there, a clip walking on legs straighter
            # than REACH is not sunk for it
            own = float(np.linalg.norm(raw.worlds[fo, f, 3, :3] - raw.worlds[th, f, 3, :3]))
            gap = float(np.linalg.norm(targets[s][f, 3, :3] - out[th, f, 3, :3])) - max(REACH * length, own)
            need[f] = max(need[f], gap)
    drop = ss.cover(np.maximum(need, 0.0), SINK_SIGMA) if need.max() > 1e-4 else np.zeros(F)
    pelvis = raw.index["pelvis"]
    above = _under(raw, pelvis)
    shorts = np.zeros(F)
    for f in range(F):
        if drop[f] > 0.0:
            out[above, f, 3, 1] -= drop[f]
        for s in ss.SIDES:
            shorts[f] = max(shorts[f], _leg_fix(raw, out[:, f], targets[s][f], s))
    info = {"walking": walking, "phases": phases, "loop_speed": loop_speed, "still": still,
            "start": (0, walking[0][0] - 1) if walking[0][0] > 0 else None,
            "stop": (walking[-1][1], F - 1) if walking[-1][1] < F - 1 else None,
            "drop": float(drop.max()), "short": float(shorts.max()), "stance": stance is not None,
            "stance_worlds": stance, "names": list(raw.names),
            "transition": raw_a.transition}
    return out, info


def _paced(raw, lr, lo, stance, still):
    """The stance's weight `still` with each end that stands in the pose (a start's first frames, a stop's last) let
    go over long enough that the body's jolt stays under JOLT: a smoothstep over T frames jolts about 6 D / T^2 + 3 V / T
    for D cm between the stance and the walk parting at V cm a frame (2026-11-17: the goblin's crouch is 85 cm off its walk
    at the head, which 8 frames made a 6 cm a frame^2 jolt). Joined softly, never under `still`."""
    F = raw.F
    points = [raw.index[n] for n in PACE_POINTS if n in raw.index]
    if not points:
        return still
    walk_pos = np.zeros((len(points), F, 3))
    for f in range(F):
        w = _fk(raw, lr[:, f], lo[:, f], _scales(raw.worlds[:, f]))
        walk_pos[:, f] = w[points, 3, :3]
    apart = walk_pos - stance[points, :, 3, :3]                                       # (P, F, 3) cm
    gap = np.linalg.norm(apart, axis=2).max(axis=0)                                  # (F,) cm
    drift = np.linalg.norm(np.gradient(apart, axis=1), axis=2).max(axis=0)          # (F,) cm a frame
    out = np.array(still, float)
    for forward in (True, False):
        s = out if forward else out[::-1]
        g = gap if forward else gap[::-1]
        v = drift if forward else drift[::-1]
        if s[0] < 0.999:
            continue
        hold = int(np.argmax(s < 0.999)) - 1 if np.any(s < 0.999) else F - 1
        if hold >= F - 1:
            continue
        rest = s[hold:]
        fall = int(np.argmax(rest < 0.01)) if np.any(rest < 0.01) else len(rest)
        window = slice(hold, min(F, hold + fall + PACE_LOOK))
        reach, speed = float(g[window].max()), float(v[window].max())
        # jolt ~ 6 D / T^2 + 3 V / T (the two apart by D cm, parting at V cm a frame): T where it is JOLT
        span = max(float(fall), (3.0 * speed + math.sqrt(9.0 * speed * speed + 24.0 * reach * JOLT)) / (2.0 * JOLT))
        f = np.arange(F, dtype=float)
        ramp = np.array([1.0 - ss._smooth(float(u)) for u in np.clip((f - hold) / span, 0.0, 1.0)])
        ramp[:hold] = 1.0
        joined = np.clip(ramp + (1.0 - ramp) * s, 0.0, 1.0)
        out = joined if forward else joined[::-1]
    return out


def _under(clip, top):
    """Every joint at or under `top`."""
    out, seen = [], {top}
    for j in clip.order:
        if j == top or clip.parents[j] in seen:
            seen.add(j)
            out.append(j)
    return out


def _foot_targets(raw_a, clip_foot, blended_foot, side):
    """(F, 4, 4) where the foot of `side` stands: in a contact the clip's foot moved by one rigid
    motion, in the swing the blended foot carried by the correction mixed from the lift-off's to the landing's."""
    F = len(clip_foot)
    contacts = [(int(c0), int(c1)) for c0, c1 in raw_a.feet[side]["contacts"]]
    out = np.array([_rigid(m) for m in blended_foot])
    if not contacts:
        return out
    motions = []
    for c0, c1 in contacts:
        mid = (c0 + c1) // 2
        motion = np.linalg.inv(_rigid(clip_foot[mid])) @ _rigid(blended_foot[mid])
        motions.append(motion)
        for f in range(c0, c1 + 1):
            out[f] = _rigid(clip_foot[f]) @ motion
    # the swings: the blended foot carried by a correction going from the one at the lift-off to the landing's
    def correction(f):
        return np.linalg.inv(_rigid(blended_foot[f])) @ out[f]
    for (a0, a1), (b0, b1) in zip(contacts[:-1], contacts[1:]):
        ca, cb = correction(a1), correction(b0)
        for f in range(a1 + 1, b0):
            u = ss._smooth((f - a1) / float(b0 - a1))
            out[f] = _rigid(blended_foot[f]) @ _mix(ca, cb, u)
    first, last = contacts[0], contacts[-1]
    c = correction(first[0])
    for f in range(0, first[0]):
        out[f] = _rigid(blended_foot[f]) @ c
    c = correction(last[1])
    for f in range(last[1] + 1, F):
        out[f] = _rigid(blended_foot[f]) @ c
    return out


def line(info):
    """The parts, as the status line names them."""
    def span(p):
        return "%d-%d" % p if p else "-"
    walking = info["walking"]
    return "start %s, walk %d-%d (%d stride%s), stop %s" % (
        span(info["start"]), walking[0][0], walking[-1][1], len(walking), "" if len(walking) == 1 else "s",
        span(info["stop"]))
