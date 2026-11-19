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
SINK_MOST = 0.15           # the most the hips sink a frame for a leg's reach, a share of the leg
HINGE_MIN = 0.5            # cm: a knee this near its hip-end line is straight - its hinge read from the bend asked
HINGE_SHARE = 0.06         # a leg's own bend is read off its knee once the thigh stands this share off the hip-ankle
                           # line (about 13 deg of knee), its thigh's hinge (thigh_hinge) below half of it
WIDTH_LEAST = 5.0          # cm: a narrowing never brings the ankles nearer than this across the body (unless the clip does)
WIDTH_SLACK = 3.0          # cm: the feet's width may leave what the walk asks by this much either way
WIDTH_ROUNDS = 6           # rounds the contacts are moved in (each foot takes half the excess a round)
SOFT = 0.04              # a leg's last share of its reach eased into (soft_reach): a near-straight knee never clicks
STANCE_SIGMA = 4.0         # frames: the stance's weight spread
JOLT = 1.0                 # cm a frame^2: the most the hand-over from a held pose to the walk may jolt the body
PACE_LOOK = 10             # frames past the fall the stance-to-walk distance is read over
PACE_POINTS = ("pelvis", "spine_05", "head")
LEGS = ("thigh", "calf", "foot")
ARMS = ("upperarm", "lowerarm", "hand")
GRIP_DIST = 30.0           # cm: two hands this near each other, holding still against each other, hold one thing
GRIP_STILL = 0.5           # cm: how little the two hands may move against each other in the walk to count as held
RATE_FREE = 1.1            # a stride this much faster than the clip's own walking pace still takes the whole change


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
    first, last = walking[0][0], walking[-1][1]
    # the strides between the first and the last walking strike, walking or not (a slow stride inside the walk
    # keeps the phase running): each strike a knot one loop stride on, the phase a monotone C1 curve through them
    # (2026-11-19: piecewise linear, the rate jumped at every strike - 1.15 to 1.67 at a Box clip's turn stride -
    # and the walk's change, laid at that rate, jolted the body there)
    inside = [(t0, t1) for t0, t1 in zip(strikes[:-1], strikes[1:]) if first <= t0 and t1 <= last]
    knots = [first] + [t1 for _t0, t1 in inside]
    values = [s0 + step * i for i in range(len(knots))]
    # before the first walking strike and after the last the phase runs at the loop's own rate, as it always did:
    # the curve leaves and joins it at rate 1
    phases = monotone(np.asarray(knots, float), np.asarray(values, float), np.arange(F, dtype=float), ends=(1.0, 1.0))
    return phases, walking, loop_speed


def monotone(x, y, at, ends=None):
    """The monotone C1 cubic through the knots (x, y) (Fritsch-Carlson's harmonic slopes) at `at`; past the ends a
    straight line on. `ends` (slope at the first knot, at the last): the curve's slopes there and the lines past
    them (each held to 3 times its secant, the monotone bound); None: the end secants."""
    x, y, at = np.asarray(x, float), np.asarray(y, float), np.asarray(at, float)
    h = np.diff(x)
    secant = np.diff(y) / h
    m = np.zeros(len(x))
    m[0], m[-1] = secant[0], secant[-1]
    if ends is not None:
        m[0] = min(float(ends[0]), 3.0 * secant[0])
        m[-1] = min(float(ends[1]), 3.0 * secant[-1])
    for i in range(1, len(x) - 1):
        a, b = secant[i - 1], secant[i]
        if a * b <= 0.0:
            m[i] = 0.0
        else:
            w1, w2 = 2.0 * h[i] + h[i - 1], h[i] + 2.0 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / a + w2 / b)
    out = np.empty(len(at))
    for k, t in enumerate(at):
        if t <= x[0]:
            out[k] = y[0] + m[0] * (t - x[0])
            continue
        if t >= x[-1]:
            out[k] = y[-1] + m[-1] * (t - x[-1])
            continue
        i = min(int(np.searchsorted(x, t, side="right")) - 1, len(x) - 2)
        u = (t - x[i]) / h[i]
        u2, u3 = u * u, u * u * u
        out[k] = ((2 * u3 - 3 * u2 + 1) * y[i] + (u3 - 2 * u2 + u) * h[i] * m[i]
                  + (-2 * u3 + 3 * u2) * y[i + 1] + (u3 - u2) * h[i] * m[i + 1])
    return out


def change_share(phases, walking):
    """(F,) how much of the walk's change - its motion about its own cycle mean - each frame takes: all of it where
    the phase runs no faster than RATE_FREE times the clip's own walking pace (the median of its walking strides'
    rates, never under the loop's - a walk's strides differ by a few frames), (free pace / rate)^2 where it runs
    faster. The change laid at a stride's own rate has its accelerations times rate^2: a turn's short stride (a Box
    clip's corner, 18 frames for the loop's 30) took the walk's swing and bob at 2.8 times their accelerations and
    jolted the body (2026-11-19, review note F). Its posture - the change's cycle mean - is always taken whole."""
    phases = np.asarray(phases, float)
    rate = np.gradient(phases)
    per = [(phases[t1] - phases[t0]) / float(t1 - t0) for t0, t1 in walking if t1 > t0 and t1 < len(phases)]
    pace = RATE_FREE * (max(1.0, float(np.median(per))) if per else 1.0)
    return np.where(rate <= pace * (1.0 + 1e-9), 1.0, (pace / np.maximum(rate, 1e-6)) ** 2)


# ---- the walk's difference ----

def change_mean(loop_cycle, result_cycle):
    """(turns (J, 3, 3), offsets (J, 3)): the walk's change over one period of the loop, each joint's mean - the
    change's posture, what stays when its motion is let go (change_share)."""
    loop_clip = loop_cycle.clip
    turns, offsets = [], []
    for u in range(int(loop_cycle.period)):
        sl, so = _locals(loop_clip, loop_cycle.sample(float(u)))
        rr, rro = _locals(loop_clip, result_cycle.sample(float(u)))
        turns.append(rr @ np.swapaxes(sl, 1, 2))
        offsets.append(rro - so)
    turns = np.asarray(turns)
    return np.array([ss.mean_rot(turns[:, j]) for j in range(turns.shape[1])]), np.mean(offsets, axis=0)


def walk_difference(raw, loop_cycle, result_cycle, phases, names_raw, names_walk, share=None, absolute=()):
    """(J, F) local turns and offsets of the raw clip with the walk's change at each frame's phase laid over: the
    change is the result's local against the loop's own (each joint's turn in its own frame, its offset in its
    parent's; the top joint's place turned from the loop's heading onto the clip's). `share` (F,) (change_share):
    where it is under 1 the change's motion about its cycle mean is taken that much, its mean whole. A joint in
    `absolute` (raw indices) takes the result's own turn at the phase instead - an arm the walk holds in a pose's
    grip, which is the pose's arm and not a change to the clip's (absolute_arms)."""
    J, F = raw.worlds.shape[:2]
    idx = dict((n, i) for i, n in enumerate(names_walk))
    lr = np.zeros((J, F, 3, 3))
    lo = np.zeros((J, F, 3))
    loop_clip = loop_cycle.clip
    mean = None
    if share is not None and float(np.min(share)) < 1.0:
        mean = change_mean(loop_cycle, result_cycle)
    for f in range(F):
        rl, ro = _locals(raw, raw.worlds[:, f])
        S = loop_cycle.sample(phases[f])
        R = result_cycle.sample(phases[f])
        sl, so = _locals(loop_clip, S)
        rr, rro = _locals(loop_clip, R)
        a = 1.0 if mean is None else float(share[f])
        for j, name in enumerate(names_raw):
            w = idx.get(name)
            if w is None:
                lr[j, f], lo[j, f] = rl[j], ro[j]
                continue
            turn = rr[w] @ sl[w].T                     # the result's local against the loop's, in the joint's frame
            d = rro[w] - so[w]
            if a < 1.0:                                # its motion about the cycle mean taken `a` of the way
                turn = ss.slerp(np.eye(3), turn @ mean[0][w].T, a) @ mean[0][w]
                d = mean[1][w] + a * (d - mean[1][w])
            lr[j, f] = rr[w] if j in absolute else turn @ rl[j]
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


def _leg_fix(clip, worlds, targets, side, reach=REACH, outward=None, floor=None, hinge=None):
    """The leg of `side` solved onto its foot target, in place (worlds (J, 4, 4)): the thigh and the calf turned
    onto the two-bone IK's knee (toward the leg's own bend), the foot standing in its target's turn. The children of
    the three bones carried rigidly. `hinge` (the knee's hinge axis in the thigh's own frame, `thigh_hinge`): where
    the leg comes in near straight and leaves bent (its own bend too small to say which way, a few millimetres of
    noise), the knee bends about it. With `outward` (the body's outside for this leg, world) and `floor` the knee's
    bend turns about the hip-ankle line no further in than `floor` (knee_plane). Returns how far it fell short."""
    chain = ["%s_%s" % (b, side) for b in LEGS]
    ix = clip.index
    th, ca, fo = (ix[n] for n in chain)
    hip, knee0, ankle0 = worlds[th, 3, :3], worlds[ca, 3, :3], worlds[fo, 3, :3]
    e = ss._unit(targets[3, :3] - hip)
    plane = ss.bend_side(knee0 - hip, e)
    old = None
    if hinge is not None:
        l1, l2 = float(np.linalg.norm(knee0 - hip)), float(np.linalg.norm(ankle0 - knee0))
        d = min(float(np.linalg.norm(targets[3, :3] - hip)), reach * (l1 + l2))
        d = max(d, abs(l1 - l2) + 1e-6)
        along = (l1 * l1 - l2 * l2 + d * d) / (2.0 * d)
        h_out = math.sqrt(max(0.0, l1 * l1 - along * along))
        e0 = ss._unit(ankle0 - hip)
        h_in = float(np.linalg.norm((knee0 - hip) - float(np.dot(knee0 - hip, e0)) * e0))
        # how far the leg's own bend can be trusted: bent enough to say which way (HINGE_SHARE of the thigh off its
        # line), or bent the way it will be bent (solved to about its own bend - and the clip given back as it is)
        sure = ss._smooth(min(1.0, max(0.0, (h_in / max(l1, 1e-6) - HINGE_SHARE) / HINGE_SHARE)))
        same = ss._smooth(min(1.0, max(0.0, (h_in / max(h_out, 1e-6) - 0.5) / 0.4))) if h_out > 1e-6 else 1.0
        w = max(sure, same)
        if w < 1.0:
            rot = ss.orthonormal(worlds[th])
            n = np.asarray(hinge, float) @ rot
            pref, pref0 = ss.bend_side(np.cross(n, e), e), ss.bend_side(np.cross(n, e0), e0)
            mixed = w * plane + (1.0 - w) * pref
            plane = ss.bend_side(mixed if np.linalg.norm(mixed) > 1e-6 else pref, e)
            # the leg as it came in read the same way: its bones keep their roll about the hinge they carry
            geom0 = ss.bend_side(knee0 - hip, e0)
            mixed0 = w * geom0 + (1.0 - w) * pref0
            old = ss.bend_side(mixed0 if np.linalg.norm(mixed0) > 1e-6 else pref0, e0)
    if outward is not None and floor is not None:
        plane = knee_plane(plane, e, outward, floor)
    return _limb_fix(clip, worlds, targets, chain, reach, plane, old)


def thigh_hinge(clip, worlds, side, least=20.0):
    """The knee's hinge axis (unit, the normal of hip-knee-ankle) in the thigh's own frame, the median over the
    frames of `worlds` (J, F, 4, 4) the knee bends at least `least` degrees - or None."""
    ix = clip.index
    th, ca, fo = (ix["%s_%s" % (b, side)] for b in LEGS)
    h, k, a = worlds[th, :, 3, :3], worlds[ca, :, 3, :3], worlds[fo, :, 3, :3]
    u, v = h - k, a - k
    bent = 180.0 - np.degrees(np.arccos(np.clip(np.sum(u * v, 1) / (np.linalg.norm(u, axis=1)
                                                                     * np.linalg.norm(v, axis=1) + 1e-12), -1, 1)))
    keep = bent >= least
    if not keep.any():
        return None
    n = np.cross(h - k, a - k)            # = (hip-end line) x (the knee's bend direction): bend = n x line
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    rot = _rots(worlds[th])
    local = np.einsum("fi,fji->fj", n, rot)[keep]
    m = np.median(local, axis=0)
    return m / np.linalg.norm(m) if np.linalg.norm(m) > 1e-9 else None


def knee_share(hip, knee, ankle, outward):
    """How far the knee's bend direction points to the body's outside: its unit share along `outward` made square to
    the hip-ankle line (1 straight out, -1 straight in, 0 forward or back)."""
    e = ss._unit(np.asarray(ankle, float) - hip)
    bend = ss.bend_side(np.asarray(knee, float) - hip, e)
    side = np.asarray(outward, float) - float(np.dot(outward, e)) * e
    if np.linalg.norm(side) < 1e-9:
        return 0.0
    return float(np.dot(bend, ss._unit(side)))


def knee_plane(bend, e, outward, floor):
    """The knee's bend direction `bend` (a unit vector off the hip-ankle line `e`) turned about `e` the least way
    until it points no further into the body than `floor`: its share along `outward` (made square to `e`) at least
    `floor` (2026-11-19: a leg of a Box clip's sideways step under the walk's knee turns fell 7 cm in, the animator:
    «колени смотрят внутрь»). Returns `bend` itself when it is out far enough."""
    e = ss._unit(np.asarray(e, float))
    side = np.asarray(outward, float) - float(np.dot(outward, e)) * e
    if np.linalg.norm(side) < 1e-9:
        return bend
    side = ss._unit(side)
    a = float(np.dot(bend, side))
    if a >= floor:
        return bend
    q = np.cross(e, bend)
    b = float(np.dot(q, side))
    r = math.hypot(a, b)
    if r < 1e-9:
        return bend
    turn = math.acos(max(-1.0, min(1.0, min(floor, r) / r)))
    base = math.atan2(b, a)
    phi = min((base - turn, base + turn), key=lambda x: abs(math.atan2(math.sin(x), math.cos(x))))
    return math.cos(phi) * np.asarray(bend, float) + math.sin(phi) * q


def _limb_fix(clip, worlds, targets, chain, reach=REACH, plane=None, old=None):
    """A three-joint chain (`chain` leaf names, root to end) solved onto `targets` (4x4, the end's world), in place;
    the middle joint bending toward `plane` when given (else the chain's own bend), the root bone rolled with it;
    `old` the bend the chain came in with when its own knee is too near straight to say (else read off it)."""
    ix = clip.index
    th, ca, fo = (ix[n] for n in chain)
    hip, knee0, ankle0 = worlds[th, 3, :3], worlds[ca, 3, :3], worlds[fo, 3, :3]
    l1, l2 = float(np.linalg.norm(knee0 - hip)), float(np.linalg.norm(ankle0 - knee0))
    goal = targets[3, :3]
    e = ss._unit(goal - hip)
    bend0 = ss.bend_side(knee0 - hip, e)
    bend = bend0 if plane is None else ss.bend_side(plane, e)
    knee, reached, short = ss.two_bone(hip, goal, l1, l2, bend, reach)
    # the chain's hinge before and after: the normal of the plane the hip-end line and the knee's offset make. Both
    # bones are turned by what takes their direction and THAT normal onto the new ones, so each keeps its roll about
    # its own length (2026-11-19): read against the bend direction instead, a lower bone bent past square to the
    # hip-end line crossed it and flipped its roll by half a turn - the legs' hinges drifted 30-115 deg in their own
    # bones' frames, 15-30 deg in one frame (the knee kinks and knees turning in of the TwoHand Box clips)
    e0 = ss._unit(ankle0 - hip)
    off0 = (knee0 - hip) - float(np.dot(knee0 - hip, e0)) * e0
    if old is not None:
        b0 = ss.bend_side(old, e0)
    else:
        b0 = ss._unit(off0) if np.linalg.norm(off0) > HINGE_MIN else ss.bend_side(bend, e0)
    n0 = ss._unit(np.cross(e0, b0))
    e1 = ss._unit(reached - hip)
    n1 = ss._unit(np.cross(e1, ss.bend_side(bend, e1)))
    before = {j: worlds[j].copy() for j in range(len(worlds))}
    new = {}
    new[th] = _hinged(worlds[th], knee0 - hip, knee - hip, n0, n1)
    new[th][3, :3] = hip
    new[ca] = _hinged(worlds[ca], ankle0 - knee0, reached - knee, n0, n1)
    new[ca][3, :3] = knee
    foot = np.array(worlds[fo])
    foot[:3, :3] = ss.orthonormal(targets) * np.linalg.norm(worlds[fo][:3, :3], axis=1)[:, None]
    foot[3, :3] = reached
    new[fo] = foot
    _carry(clip, worlds, before, new)
    return float(short)


def _arm_fix(clip, worlds, target, chain, reach=1.0):
    """An arm (`chain` leaf names: upper arm, forearm, hand) solved onto `target` (4x4, the hand's world), in place.
    The arm's own PLANE carried onto the new one - the shoulder-wrist line and the elbow's side of it, before and
    after - both bones turned by that one map, so the forearm keeps its roll in the arm (2026-11-19). _limb_fix turns
    each bone on its own about a normal crossed from that bone and the elbow's side: where the forearm stood near
    that side the normal flipped, and a two-handed grip's forearms rolled 180-340 deg against the upper arm (the
    Transition clips' "elbows out, twists broken"); the twist bones under the forearm rode it. Returns how far the
    hand fell short."""
    ix = clip.index
    up, low, hand = (ix[n] for n in chain)
    sh, el0, wr0 = worlds[up, 3, :3], worlds[low, 3, :3], worlds[hand, 3, :3]
    l1, l2 = float(np.linalg.norm(el0 - sh)), float(np.linalg.norm(wr0 - el0))
    goal = target[3, :3]
    e0 = ss._unit(wr0 - sh)
    side0 = el0 - sh - np.dot(el0 - sh, e0) * e0
    e1 = ss._unit(goal - sh)
    hint = side0 if np.linalg.norm(side0) > 1e-6 else ss._any_perpendicular(e0)
    side1 = ss.bend_side(hint, e1)
    side0 = ss.bend_side(hint, e0)
    elbow, reached, short = ss.two_bone(sh, goal, l1, l2, side1, reach)
    n0, n1 = ss._unit(np.cross(e0, side0)), ss._unit(np.cross(e1, side1))
    before = {j: worlds[j].copy() for j in range(len(worlds))}
    new = {}
    for j, a0, a1, place in ((up, el0 - sh, elbow - sh, sh), (low, wr0 - el0, reached - elbow, elbow)):
        u0, u1 = ss._unit(a0), ss._unit(a1)
        p0 = ss._unit(n0 - np.dot(n0, u0) * u0)       # the plane's normal, square to the bone (exactly so already)
        p1 = ss._unit(n1 - np.dot(n1, u1) * u1)
        m = np.array(worlds[j])
        m[:3, :3] = worlds[j][:3, :3] @ ss.align(u0, p0, u1, p1)
        m[3, :3] = place
        new[j] = m
    h = np.array(worlds[hand])
    h[:3, :3] = ss.orthonormal(target) * np.linalg.norm(worlds[hand][:3, :3], axis=1)[:, None]
    h[3, :3] = reached
    new[hand] = h
    _carry(clip, worlds, before, new)
    return float(short)


def _chest(clip):
    """The joint the right arm hangs from (its clavicle's parent), or None."""
    j = clip.index.get("clavicle_r")
    if j is None or clip.parents[j] < 0:
        return None
    return clip.parents[j]


def grip_hold(result, names):
    """The left hand in the right hand's frame (4x4, rigid) when Walk Builder's loop holds the two hands together -
    near each other and still against each other on every frame (a pose's two-handed grip) - else None."""
    ix = dict((n, i) for i, n in enumerate(result.names))
    if "hand_r" not in ix or "hand_l" not in ix or "hand_r" not in names or "hand_l" not in names:
        return None
    w = np.asarray(result.worlds)
    rel = np.array([_rigid(w[ix["hand_l"], f]) @ np.linalg.inv(_rigid(w[ix["hand_r"], f])) for f in range(w.shape[1])])
    if float(np.linalg.norm(rel[:, 3, :3], axis=1).max()) > GRIP_DIST:
        return None
    if float(np.ptp(rel[:, 3, :3], axis=0).max()) > GRIP_STILL:
        return None
    return _rigid(rel[0])


def absolute_arms(clip):
    """The raw indices of both arms - each clavicle and every joint under it (the upper and lower arms, their twist
    bones, the hand, the fingers, the weapon bone) - that a pose's two-handed grip in the walk takes over whole
    (2026-11-19). The grip's arm is the pose's: its elbow bends ~110 deg where the walk's own bends ~25, so its
    change is ~85 deg of elbow - and laid over a clip's own arm as a difference, onto a run's elbow already bent
    100-115 deg, it bent the elbow through 180: the forearm folded back and rolled 180-340 deg against the upper
    arm (the Transition clips' "elbows out, twists broken"). Taken from the walk, the arm is the walk's at the
    frame's phase and the grip's IK only follows the clip's own chest."""
    out = set()
    for side in ("l", "r"):
        top = clip.index.get("clavicle_" + side)
        if top is not None:
            out.update(_under(clip, top))
    return out


def _hinged(world, old_dir, new_dir, n0, n1):
    """`world` turned by the rotation taking the bone direction `old_dir` and the chain's hinge normal `n0` onto
    `new_dir` and `n1` (each direction square to its normal: both lie in the chain's plane)."""
    u0, u1 = ss._unit(old_dir), ss._unit(new_dir)
    m0 = ss._unit(n0 - float(np.dot(n0, u0)) * u0)
    m1 = ss._unit(n1 - float(np.dot(n1, u1)) * u1)
    if np.linalg.norm(m0) < 1e-9 or np.linalg.norm(m1) < 1e-9:
        return np.array(world)
    o = np.array([u0, m0, np.cross(u0, m0)])
    m = np.array([u1, m1, np.cross(u1, m1)])
    out = np.array(world)
    out[:3, :3] = world[:3, :3] @ (o.T @ m)
    return out


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
    # a two-handed grip the walk holds and the loop does not: the pose's arms, taken whole (absolute_arms)
    hold = grip_hold(result, raw.index) if grip_hold(loop, raw.index) is None else None
    share_of_change = change_share(phases, walking)
    lr, lo = walk_difference(raw, loop_cycle, result_cycle, phases, raw.names, loop.names, share_of_change,
                             absolute_arms(raw) if hold is not None else ())
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
    asked = asked_width(raw, loop, result, loop_cycle, result_cycle, phases, stance, still)
    targets, widths = _placed_feet(raw, raw_a, out, asked)
    # how straight a leg may come: the clip's own straightest, eased into over its last SOFT share
    # of the leg - a knee near straight turns tens of degrees for a centimetre of reach (trap 266), and a leg pinned
    # at its reach for a few frames of a push-off clicked 18-30 deg a frame (the animator's Box_B_LR_Lfoot, 2026-11-19)
    lengths, limits = {}, {}
    for s in ss.SIDES:
        th, ca, fo = (raw.index["%s_%s" % (b, s)] for b in LEGS)
        lengths[s] = float(np.linalg.norm(raw.worlds[ca, 0, 3, :3] - raw.worlds[th, 0, 3, :3])
                           + np.linalg.norm(raw.worlds[fo, 0, 3, :3] - raw.worlds[ca, 0, 3, :3]))
        own = np.linalg.norm(raw.worlds[fo, :, 3, :3] - raw.worlds[th, :, 3, :3], axis=1)
        limits[s] = min(lengths[s], float(own.max()))       # the clip's own straightest (it is given back as it is)
    need = np.zeros(F)
    for f in range(F):
        for s in ss.SIDES:
            if not raw_a.feet[s]["down"][f]:
                continue
            th, fo = raw.index["thigh_" + s], raw.index["foot_" + s]
            hip, goal = out[th, f, 3, :3], targets[s][f, 3, :3]
            # never sunk past the clip's own stretch there: a clip that walks that straight keeps it
            own = float(np.linalg.norm(raw.worlds[fo, f, 3, :3] - raw.worlds[th, f, 3, :3]))
            want = max(soft_reach(float(np.linalg.norm(goal - hip)), limits[s], SOFT * lengths[s]), own)
            # (never past SINK_MOST of the leg: a goal that far is a step the hips cannot reach for - it falls short)
            need[f] = max(need[f], min(sink_for(hip, goal, want), SINK_MOST * lengths[s]))
    drop = ss.cover(np.maximum(need, 0.0), SINK_SIGMA) if need.max() > 1e-4 else np.zeros(F)
    pelvis = raw.index["pelvis"]
    above = _under(raw, pelvis)
    shorts = np.zeros(F)
    other = {"l": "r", "r": "l"}
    hinges = dict((s, thigh_hinge(raw, out, s)) for s in ss.SIDES)      # read before the legs are solved
    for f in range(F):
        if drop[f] > 0.0:
            out[above, f, 3, 1] -= drop[f]
        for s in ss.SIDES:
            # the knee no further into the body than the clip's own there (and never in where the clip's is out)
            th, ca, fo = (raw.index["%s_%s" % (b, s)] for b in LEGS)
            w0 = raw.worlds[:, f]
            raw_out = w0[th, 3, :3] - w0[raw.index["thigh_" + other[s]], 3, :3]
            raw_out[1] = 0.0
            floor = min(0.0, knee_share(w0[th, 3, :3], w0[ca, 3, :3], w0[fo, 3, :3], raw_out))
            outward = out[th, f, 3, :3] - out[raw.index["thigh_" + other[s]], f, 3, :3]
            outward[1] = 0.0
            target = targets[s][f]
            if not raw_a.feet[s]["down"][f]:     # a foot in the air passes nearer the hip than its reach: eased
                hip = out[raw.index["thigh_" + s], f, 3, :3]
                d = float(np.linalg.norm(target[3, :3] - hip))
                own = float(np.linalg.norm(w0[fo, 3, :3] - w0[th, 3, :3]))   # a leg the clip swings this straight
                if d > 1e-6:
                    target = np.array(target)
                    target[3, :3] = hip + (target[3, :3] - hip) * (
                        max(soft_reach(d, limits[s], SOFT * lengths[s]), min(d, own)) / d)
            shorts[f] = max(shorts[f], _leg_fix(raw, out[:, f], target, s,
                                                max(limits[s], 1e-6) / lengths[s] + 1e-6, outward, floor,
                                                hinges[s]))
    # the hands last: a two-handed grip in the walk holds on every frame of the clip - the right hand carries the
    # weapon and the left arm is solved by IK onto its hold (2026-11-17: in a whole clip the clip's own swinging arms
    # under the walk's difference let the hands drift 64 cm apart)
    # (a clip that holds its weapon two-handed already keeps its grip under the difference: left as it is, so the walk's
    # own values still give the clip back)
    grip_short = 0.0
    if hold is not None:
        hand_r = raw.index["hand_r"]
        chest = _chest(raw)
        widx = dict((n, i) for i, n in enumerate(result.names))
        for f in range(F):
            # the weapon where the walk carries it against the chest (its Hold, Inherit, Overlap...), the stance's
            # where the body stands: the clip's own arm swing under the difference must not reach it
            walk = 1.0 - float(still[f]) if stance is not None else 1.0
            if walk > 0.0 and chest is not None:
                R = result_cycle.sample(phases[f])
                in_chest = _rigid(R[widx["hand_r"]]) @ np.linalg.inv(_rigid(R[widx[raw.names[chest]]]))
                want = _mix(_rigid(out[hand_r, f]), in_chest @ _rigid(out[chest, f]), walk)
                scale = np.linalg.norm(out[hand_r, f][:3, :3], axis=1)
                want[:3, :3] = want[:3, :3] * scale[:, None]
                grip_short = max(grip_short, _arm_fix(raw, out[:, f], want, ["%s_r" % b for b in ARMS], 1.0))
            target = hold @ out[hand_r, f]
            scale = np.linalg.norm(out[raw.index["hand_l"], f][:3, :3], axis=1)
            target[:3, :3] = ss.orthonormal(target) * scale[:, None]
            grip_short = max(grip_short, _arm_fix(raw, out[:, f], target, ["%s_l" % b for b in ARMS], 1.0))
    info = {"walking": walking, "phases": phases, "loop_speed": loop_speed, "still": still,
            "change_share": share_of_change,
            "grip": hold is not None, "grip_short": float(grip_short),
            "start": (0, walking[0][0] - 1) if walking[0][0] > 0 else None,
            "stop": (walking[-1][1], F - 1) if walking[-1][1] < F - 1 else None,
            "drop": float(drop.max()), "short": float(shorts.max()), "stance": stance is not None,
            "width": {"raw": widths[0], "asked": asked, "before": widths[1], "after": widths[2]},
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


def feet_width(worlds, index):
    """(F,) the feet's width across the body: the left ankle against the right along the hips' line (right hip to
    left, along the floor), cm, signed - negative where the feet cross. `worlds` (J, F, 4, 4)."""
    w = np.asarray(worlds)
    hip = w[index["thigh_l"], :, 3, :3] - w[index["thigh_r"], :, 3, :3]
    hip[:, 1] = 0.0
    hip /= np.maximum(np.linalg.norm(hip, axis=1, keepdims=True), 1e-9)
    return np.sum((w[index["foot_l"], :, 3, :3] - w[index["foot_r"], :, 3, :3]) * hip, axis=1)


def asked_width(raw, loop, result, loop_cycle, result_cycle, phases, stance, still):
    """(F,) how much the walk asks the feet's width to change at each frame of the clip: Walk Builder's loop against
    its own source at the frame's phase (its Width, Stance, the pose's feet), and the stance's against the clip
    where the body stands, mixed by `still`."""
    F = raw.F
    ask = np.zeros(F)
    for f in range(F):
        R, S = result_cycle.sample(phases[f]), loop_cycle.sample(phases[f])
        ask[f] = feet_width(R[:, None], result.index)[0] - feet_width(S[:, None], loop.index)[0]
    if stance is not None:
        stand = feet_width(stance, raw.index) - feet_width(raw.worlds, raw.index)
        ask = (1.0 - np.asarray(still)) * ask + np.asarray(still) * stand
    return ask


def width_bounds(raw_width, asked, least=WIDTH_LEAST, slack=WIDTH_SLACK):
    """(lo, hi) (F,) each: the feet's width a frame may take - the clip's own moved by no more than the walk asks
    (`asked`, give or take `slack` cm either way), and never narrower than the clip's own or `least`, whichever is
    narrower: a narrowing never crosses feet the clip keeps apart, and never crosses them further than it does
    (2026-11-19, the animator: «ноги не должны разъезжаться сверх нормы ... высчитывать дельту и придерживаться»;
    a person's step width is 5-15 cm between the ankles, the gait guide's norm)."""
    raw_width, asked = np.asarray(raw_width, float), np.asarray(asked, float)
    hi = raw_width + np.maximum(asked, 0.0) + slack
    lo = np.maximum(raw_width + np.minimum(asked, 0.0) - slack, np.minimum(raw_width, least))
    return lo, np.maximum(hi, lo)


def width_shifts(widths, lo, hi, contacts, rate=0.5):
    """{contact index: cm} how far each of one foot's contacts moves along the body's line to bring the feet's width
    (F,) back inside (lo, hi): `rate` of the median excess over the contact's frames (the other foot takes the rest),
    a contact already inside left out. Positive: the width grows."""
    excess = np.asarray(widths) - np.clip(widths, lo, hi)
    out = {}
    for i, (c0, c1) in enumerate(contacts):
        e = excess[c0:c1 + 1]
        if not len(e) or float(np.abs(e).max()) < 0.05:
            continue
        out[i] = -rate * float(np.median(e[np.abs(e) > 1e-9])) if np.any(np.abs(e) > 1e-9) else 0.0
    return out


def _placed_feet(raw, raw_a, out, asked, rounds=WIDTH_ROUNDS):
    """({side: (F, 4, 4)} the feet's targets, (raw, before, after) widths): `_foot_targets` with each contact moved
    along the hips' line where the feet's width leaves `width_bounds` (the rounds converge: each foot takes half)."""
    ix = raw.index
    feet = dict((s, (raw.worlds[ix["foot_" + s]], out[ix["foot_" + s]])) for s in ss.SIDES)
    contacts = dict((s, edge_contacts(raw_a.feet[s]["contacts"], raw_a.feet[s]["down"], raw.F)) for s in ss.SIDES)
    raw_width = feet_width(raw.worlds, ix)
    lo, hi = width_bounds(raw_width, asked)
    hip = out[ix["thigh_l"], :, 3, :3] - out[ix["thigh_r"], :, 3, :3]
    hip[:, 1] = 0.0
    hip /= np.maximum(np.linalg.norm(hip, axis=1, keepdims=True), 1e-9)
    shifts = dict((s, {}) for s in ss.SIDES)
    first = None
    for _ in range(rounds + 1):
        targets = dict((s, _foot_targets(raw_a, feet[s][0], feet[s][1], s, shifts[s])) for s in ss.SIDES)
        widths = _target_width(out, ix, targets)
        if first is None:
            first = widths
        moved = False
        for s, sign in (("l", 1.0), ("r", -1.0)):
            for i, cm in width_shifts(widths, lo, hi, contacts[s]).items():
                c0, c1 = contacts[s][i]
                axis = hip[(c0 + c1) // 2]
                shifts[s][i] = shifts[s].get(i, np.zeros(3)) + sign * cm * axis
                moved = True
        if not moved:
            break
    return targets, (raw_width, first, widths)


def _target_width(out, ix, targets):
    hip = out[ix["thigh_l"], :, 3, :3] - out[ix["thigh_r"], :, 3, :3]
    hip[:, 1] = 0.0
    hip /= np.maximum(np.linalg.norm(hip, axis=1, keepdims=True), 1e-9)
    return np.sum((targets["l"][:, 3, :3] - targets["r"][:, 3, :3]) * hip, axis=1)


def soft_reach(d, limit, soft):
    """How far a leg asked to reach `d` reaches: `d` itself up to `limit - soft`, then eased (C1, an exponential)
    toward `limit` without ever getting there."""
    start = limit - soft
    if d <= start or soft <= 1e-9:
        return min(d, limit)
    return limit - soft * math.exp(-(d - start) / soft)


def sink_for(hip, goal, want):
    """How far the hips sink (straight down) for the leg from `hip` to `goal` to be `want` long: 0 when it already
    is; a goal further than `want` along the floor alone takes the whole height (the legs then fall short)."""
    v = np.asarray(goal, float) - np.asarray(hip, float)
    d = float(np.linalg.norm(v))
    if d <= want:
        return 0.0
    flat = math.hypot(float(v[0]), float(v[2]))
    down = -float(v[1])                       # the hip above the goal
    if flat >= want:
        return max(0.0, down)
    return max(0.0, down - math.sqrt(want * want - flat * flat))


def _under(clip, top):
    """Every joint at or under `top`."""
    out, seen = [], {top}
    for j in clip.order:
        if j == top or clip.parents[j] in seen:
            seen.add(j)
            out.append(j)
    return out


def edge_contacts(contacts, down, F):
    """The contacts a foot holds with the clip's two ends' landings in them (2026-11-19): a foot down from the
    clip's first frame (or to its last) that is not still there - a start's first push, a stop's or a Box clip's
    last landing - is planted as a contact too, or the frames before the first contact and after the last had
    only a lift-off's correction carried through a whole stride (the animator's Box_B_LR_Lfoot: the last landing
    8 cm under the floor and 30 cm aside, the hips sunk 14 cm for it). A down run reaching an end joins the contact
    it runs into, else it is a contact of its own. `contacts` [(c0, c1)] inclusive, `down` (F,) bools."""
    down = np.asarray(down, bool)
    out = [(int(a), int(b)) for a, b in contacts]
    if not len(down):
        return out
    if down[0] and (not out or out[0][0] > 0):
        end = 0
        while end + 1 < F and down[end + 1]:
            end += 1
        if out and end >= out[0][0] - 1:
            out[0] = (0, out[0][1])
        else:
            out.insert(0, (0, min(end, out[0][0] - 2) if out else end))
    if down[-1] and (not out or out[-1][1] < F - 1):
        begin = F - 1
        while begin - 1 >= 0 and down[begin - 1]:
            begin -= 1
        if out and begin <= out[-1][1] + 1:
            out[-1] = (out[-1][0], F - 1)
        else:
            out.append((max(begin, out[-1][1] + 2) if out else begin, F - 1))
    return [(a, b) for a, b in out if b >= a]


def contact_motion(clip_foot, blended_foot):
    """The one rigid motion a contact's foot takes (4x4, row vectors, world): the blended foot's place along the
    floor and its turn about up, at the contact's middle - never its height or its tilt (2026-11-19). The walk's
    difference laid over the leg's joints puts a planted foot a centimetre or two off the floor and tilted; the
    clip's own foot is on it, and moved only along the floor and about up it stays there, with every contact read
    off the result on the frames the clip has it (the animator: the timing must match)."""
    pivot = np.asarray(clip_foot)[3, :3]
    turn = ss.orthonormal(clip_foot).T @ ss.orthonormal(blended_foot)      # blended = clip . turn (world)
    spin = ss.yaw(ss.yaw_of(turn))
    shift = np.asarray(blended_foot)[3, :3] - pivot
    shift[1] = 0.0
    out = np.eye(4)
    out[:3, :3] = spin
    out[3, :3] = pivot - pivot @ spin + shift
    return out


def _correction(blended, target):
    """(the turn in the foot's own frame, the offset in the world) taking the foot `blended` onto `target`: a
    correction that means the same wherever the foot is - mixed along a swing, or held - where a world transform
    (a turn about the room's origin) carried a stride swings the foot by its whole distance from the origin."""
    rb, rt = ss.orthonormal(blended), ss.orthonormal(target)
    return rt @ rb.T, np.asarray(target)[3, :3] - np.asarray(blended)[3, :3]


def _corrected(blended, turn, offset):
    out = np.eye(4)
    out[:3, :3] = turn @ ss.orthonormal(blended)
    out[3, :3] = np.asarray(blended)[3, :3] + offset
    return out


def _foot_targets(raw_a, clip_foot, blended_foot, side, shifts=None):
    """(F, 4, 4) where the foot of `side` stands: in a contact (and in a landing at either end of the clip,
    `edge_contacts`) the clip's foot moved by one rigid motion, in the swing the blended foot carried by the
    correction (a turn in the foot's frame, an offset in the world: `_correction`) mixed from the lift-off's to the
    landing's, before the first contact and after the last the nearest's held. `shifts` {contact index: world
    offset} moves a contact's whole place further (`width_shifts`)."""
    F = len(clip_foot)
    contacts = edge_contacts(raw_a.feet[side]["contacts"], raw_a.feet[side]["down"], F)
    out = np.array([_rigid(m) for m in blended_foot])
    if not contacts:
        return out
    motions = []
    for i, (c0, c1) in enumerate(contacts):
        motion = contact_motion(clip_foot[(c0 + c1) // 2], blended_foot[(c0 + c1) // 2])
        if shifts and i in shifts:
            motion[3, :3] += shifts[i]
        motions.append(motion)
        for f in range(c0, c1 + 1):
            out[f] = _rigid(clip_foot[f]) @ motion

    def correction(f):
        return _correction(blended_foot[f], out[f])
    for i, ((a0, a1), (b0, b1)) in enumerate(zip(contacts[:-1], contacts[1:])):
        (ra, da), (rb, db) = correction(a1), correction(b0)
        for f in range(a1 + 1, b0):
            u = (f - a1) / float(b0 - a1)
            s = ss._smooth(u)
            walk = _corrected(blended_foot[f], ss.slerp(ra, rb, s), (1.0 - s) * da + s * db)
            # the clip's own swing carried between the two contacts' places: the foot leaves and lands as the clip
            # has it (its speed there, so each contact is read on its own frames), the walk's swing in the middle
            # (mixed on a smootherstep: flat to its second derivative at both ends, the place it moves to barely
            # changes the foot's speed in the frames next to a contact)
            s2 = u * u * u * (u * (6.0 * u - 15.0) + 10.0)
            copy = _mix(_rigid(clip_foot[f]) @ motions[i], _rigid(clip_foot[f]) @ motions[i + 1], s2)
            out[f] = _mix(copy, walk, math.sin(math.pi * u) ** 4)
    # before the first contact and after the last (a foot in the air at an end): as a swing's half - the clip's own
    # moved as its nearest contact next to it, the walk's (its correction held) half a swing away (a contact's turn
    # about its own place swings a foot far from it aside: Box_F's first step is 1.8 m long)
    swings = [b0 - a1 for (a0, a1), (b0, b1) in zip(contacts[:-1], contacts[1:])]
    half = max(3.0, 0.5 * float(np.median(swings))) if swings else 6.0
    for ends, frames, motion in (((contacts[0][0]), range(0, contacts[0][0]), motions[0]),
                                 ((contacts[-1][1]), range(contacts[-1][1] + 1, F), motions[-1])):
        turn, offset = correction(ends)
        for f in frames:
            e = ss._smooth(min(1.0, abs(f - ends) / half))
            out[f] = _mix(_rigid(clip_foot[f]) @ motion, _corrected(blended_foot[f], turn, offset), e)
    return out


def line(info):
    """The parts, as the status line names them."""
    def span(p):
        return "%d-%d" % p if p else "-"
    walking = info["walking"]
    return "start %s, walk %d-%d (%d stride%s), stop %s" % (
        span(info["start"]), walking[0][0], walking[-1][1], len(walking), "" if len(walking) == 1 else "s",
        span(info["stop"]))


def in_place(worlds, names, parents, up=(0.0, 1.0, 0.0)):
    """A whole clip on the spot (2026-11-19, the animator: the scene shows the clips in place, the export keeps the
    root motion): every joint moved back by the root's travel along the floor since the first frame. The root's
    own height and turn and everything relative to it stay, so the body plays exactly as before about a root that
    stands still. `worlds` (J, F, 4, 4), row vectors; returns (a copy, the travel in cm)."""
    out = np.array(worlds, float, copy=True)
    names = list(names)
    if "root" in names:
        root = names.index("root")
    else:
        tops = [j for j, p in enumerate(parents) if p is None or p < 0]
        if not tops:
            return out, 0.0
        root = tops[0]
    up = np.asarray(up, float)
    up = up / np.linalg.norm(up)
    travel = out[root, :, 3, :3] - out[root, 0, 3, :3]
    travel = travel - np.outer(travel @ up, up)
    out[:, :, 3, :3] -= travel[None]
    return out, float(np.linalg.norm(travel, axis=1).max())
