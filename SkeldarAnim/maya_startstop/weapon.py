"""maya_startstop.weapon - Walk Builder's Weapon tab on a start or a stop (2026-11-17). numpy, no maya.cmds.

The animator, with the card half built: «Сразу давай перенесем новый функционал из вкладки weapon в инструмент по
обработке стартов и стопов новую систему захлестов ... Все отличие стартов и стопов это в том что тут нет цикла и
средней позы тяжело вычислить, но все остальное должно работать по тем же принципам.»

Walk Builder's five knobs (maya_walk.model `_weapon_hold`, `_weapon_aim`, `_shoulder_assist`), each read the same:

- **Hold** (`weapon_hold`, on): the hand rides the CHEST rigidly at its own offset from it - so it stops playing
  the arm's swing and keeps the pose's hold on the torso;
- **Inherit** (`weapon_inherit`, 1): the share of the chest's own motion the held hand takes;
- **Overlap** (`weapon_overlap`, ms): the chest the hand rides is that old - the weapon trails the body;
- **Aim target** (`weapon_aim`, 1): the blade swung about its grip onto a target keeping that share of its own
  motion - the weapon's weight;
- **Shoulder** (`weapon_shoulder`, 0): the share of the arm's reach changes the clavicle takes.

What a cycle gave Walk Builder and a start or a stop has not got, and what stands for it:

- **the mean** (the hand's offset held, the chest at Inherit 0, the aim target at 0, the shoulder's reach): a
  start or a stop has no mean - its run and its stance are different poses. Each is read off its SLOW part, a
  Gaussian of `SLOW` frames (`slow_mats`): what the clip does over a stride and more - running into the stance,
  crouching into the brake - stays, the swing over it goes;
- **the travel taken out**: a cycle's linear travel; here the ROOT's own motion (the clip's locomotion). The chest,
  the aim target are read in the root's frame and put back on the root of the frame they land on;
- **a lag**: no wrap - the clip read that many frames earlier, held on its first frame before it starts (a lead on
  its last).

A held hand takes no arm spring (Walk Builder's rule: Whip would soften the rigidity). Two hands holding one thing
(a pose's grip) hold together: the carrier drives, the other takes its delta. The arms are rebuilt by IK from the
current shoulder (the elbow bending as the frames bend it, the bones keeping their lengths).
Spec: docs/superpowers/specs/2026-11-17-start-stop-builder-design.md (its addendum).
"""
import math

import numpy as np

from . import model as m

SLOW = 8.0                 # frames: what moves slower than a Gaussian of this is the clip's own slow part (its "mean")
AIM_REACH = 1.15           # the aim target this far past the blade's tip, x its length (Aim Mode's own)
AIM_BLADE = 100.0          # cm: the blade a weapon BONE stands for where the scene holds no weapon (along its +Z)
QUIET = 1e-9
SHOULDER_MAX_DEG = 35.0    # the clavicle turns no further than this off the frames' own...
SHOULDER_FREE = 0.6        # ...freely up to this share of it, then easing in with no corner
NAMES = ("weapon_hold", "weapon_inherit", "weapon_overlap", "weapon_aim", "weapon_shoulder")


def soft_reach(d, soft, hard):
    """`d` itself up to `soft`, then easing into `hard` with no corner (Walk Builder's)."""
    if d <= soft or soft >= hard:
        return min(d, hard)
    band = hard - soft
    return soft + band * (1.0 - math.exp(-(d - soft) / band))


def aim_swing(a, b):
    """The minimal rotation (3x3, row vectors) taking the direction `a` onto `b` - a swing with no twist."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if float(np.linalg.norm(a)) < 1e-9 or float(np.linalg.norm(b)) < 1e-9:
        return np.eye(3)
    a, b = m._unit(a), m._unit(b)
    axis = np.cross(a, b)
    s, c = float(np.linalg.norm(axis)), float(np.dot(a, b))
    if s < 1e-12:
        return np.eye(3) if c > 0.0 else m.exp_rot(m._any_perpendicular(a) * math.pi)
    return m.exp_rot(axis / s * math.atan2(s, c))


def swung_about(origin, rot):
    """The world turn `rot` about `origin`, a 4x4 (row vectors): the origin held, all else swings about it."""
    o = np.asarray(origin, float)
    out = np.eye(4)
    out[:3, :3] = rot
    out[3, :3] = o - o @ rot
    return out


def late(mats, lag):
    """Matrices (F, 4, 4) read `lag` frames earlier (a fraction falls between two frames: the rotation slerped,
    the place lerped), held on the first frame before the clip starts and on the last after it ends. lag 0: the
    input, matrix for matrix."""
    mats = np.asarray(mats, float)
    if abs(lag) < QUIET:
        return np.array(mats)
    F = mats.shape[0]
    out = np.tile(np.eye(4), (F, 1, 1))
    for f in range(F):
        g = min(max(f - lag, 0.0), F - 1.0)
        lo = int(math.floor(g))
        hi = min(lo + 1, F - 1)
        a = g - lo
        ra, rb = m.orthonormal(mats[lo]), m.orthonormal(mats[hi])
        out[f, :3, :3] = ra @ m.exp_rot(a * m.log_rot(ra.T @ rb))
        out[f, 3, :3] = (1.0 - a) * mats[lo, 3, :3] + a * mats[hi, 3, :3]
    return out


def slow_mats(mats, sigma=SLOW):
    """The slow part of a matrix series (F, 4, 4): its turn and place blurred by a Gaussian of `sigma` frames
    (the turn as its log about the series' mean turn, the ends held) - what stands for a cycle's mean."""
    mats = np.asarray(mats, float)
    F = mats.shape[0]
    rots = np.array([m.orthonormal(mats[f]) for f in range(F)])
    anchor = m.mean_rot(rots)
    logs = np.array([m.log_rot(anchor.T @ r) for r in rots])
    smooth = np.stack([m._blur(logs[:, i], sigma) for i in range(3)], axis=1)
    out = np.tile(np.eye(4), (F, 1, 1))
    for f in range(F):
        out[f, :3, :3] = anchor @ m.exp_rot(smooth[f])
    for i in range(3):
        out[:, 3, i] = m._blur(mats[:, 3, i], sigma)
    return out


def keeping(mats, keep, sigma=SLOW):
    """A matrix series keeping the share `keep` of its motion over its slow part: 1 the input, 0 the slow part
    alone."""
    mats = np.asarray(mats, float)
    if keep >= 1.0 - QUIET:
        return np.array(mats)
    slow = slow_mats(mats, sigma)
    out = np.array(slow)
    for f in range(mats.shape[0]):
        sr = slow[f, :3, :3]
        out[f, :3, :3] = sr @ m.exp_rot(m.log_rot(sr.T @ m.orthonormal(mats[f])) * keep)
        out[f, 3, :3] = slow[f, 3, :3] + (mats[f, 3, :3] - slow[f, 3, :3]) * keep
    return out


def keeping_points(pts, keep, sigma=SLOW):
    """Points (F, 3) keeping the share `keep` of their motion over their slow part."""
    pts = np.asarray(pts, float)
    if keep >= 1.0 - QUIET:
        return np.array(pts)
    slow = np.stack([m._blur(pts[:, i], sigma) for i in range(3)], axis=1)
    return slow + (pts - slow) * keep


def _in(mats, frame):
    """Each of `mats` (F, 4, 4) in the frame `frame` (F, 4, 4): mats . inv(frame)."""
    return np.einsum("fij,fjk->fik", mats, np.linalg.inv(frame))


def _on(mats, frame):
    return np.einsum("fij,fjk->fik", mats, frame)


def _chest(clip):
    for name in ("spine_05", "spine_04", "spine_03"):
        if name in clip.index:
            return clip.index[name]
    return None


def chains(clip):
    """{side: (clavicle or None, upper arm, forearm, hand)} for the sides the skeleton has."""
    out = {}
    for s in m.SIDES:
        names = ["%s_%s" % (b, s) for b in ("upperarm", "lowerarm", "hand")]
        if all(n in clip.index for n in names):
            clav = clip.index.get("clavicle_" + s)
            out[s] = (clav,) + tuple(clip.index[n] for n in names)
    return out


def held_sides(k, chains_, posed, weapons):
    """The sides Hold holds: its chip on, and the pose holding that arm or the scene giving the hand a weapon
    (with no pose a hand with nothing in it keeps its swing - Walk Builder's 2026-11-11 rule)."""
    ks = m.sided(k)
    armed = set(weapons or {})
    return set(s for s in chains_ if float(ks[s]["weapon_hold"]) > 0.5 and (posed or s in armed))


def arm_to_hand(clip, kin, side_chain, want):
    """One arm rebuilt to a wanted hand (F, 4, 4) from the current shoulder: {joint: (F, 4, 4)} for the upper
    arm, the forearm and the hand - the elbow bending the way the frames bend it, the bones their own lengths (a
    hand past reach clamped along its line)."""
    _clav, up, low, hand = side_chain
    F = kin.shape[1]
    mu, ml, mh = (np.tile(np.eye(4), (F, 1, 1)) for _ in range(3))
    for f in range(F):
        sh, el, wr = kin[up, f, 3, :3], kin[low, f, 3, :3], kin[hand, f, 3, :3]
        l1, l2 = float(np.linalg.norm(el - sh)), float(np.linalg.norm(wr - el))
        e = m._unit(wr - sh)
        bend = (el - sh) - np.dot(el - sh, e) * e
        bend = m._unit(bend) if np.linalg.norm(bend) > 1e-4 else m._any_perpendicular(e)
        knee, reached, _ = m.two_bone(sh, want[f, 3, :3], l1, l2, bend, 1.0)
        e2 = m._unit(reached - sh)
        bend2 = m.bend_side(bend, e2)          # the plane two_bone bent toward, never read back (trap 245)
        n1, n2 = m._unit(np.cross(e, bend)), m._unit(np.cross(e2, bend2))
        mu[f, :3, :3] = m.orthonormal(kin[up, f]) @ m.align(m._unit(el - sh), n1, m._unit(knee - sh), n2)
        ml[f, :3, :3] = m.orthonormal(kin[low, f]) @ m.align(m._unit(wr - el), n1, m._unit(reached - knee), n2)
        mu[f, 3, :3], ml[f, 3, :3] = sh, knee
        mh[f, :3, :3], mh[f, 3, :3] = m.orthonormal(want[f]), reached
    return {up: mu, low: ml, hand: mh}


def levers(clip, kin, chains_, weapons, sides):
    """{side: (grip, aim point, "weapon" | "bone")} in the hand's own frame: the scene's weapon in that hand (its
    grip, its tip pushed AIM_REACH past), else - where the scene holds no weapon at all - the right hand's weapon
    BONE (the grip on the bone, AIM_BLADE along its +Z, where frame 0 holds it in the hand)."""
    out = {}
    for side in sides:
        held = (weapons or {}).get(side)
        if held:
            grip, tip = (np.asarray(held[key], float) for key in ("grip", "tip"))
            if float(np.linalg.norm(tip - grip)) > 1e-6:
                out[side] = (grip, grip + (tip - grip) * AIM_REACH, "weapon")
    if not weapons and "r" in sides and "r" not in out and "weapon_r" in clip.index:
        hand = chains_["r"][3]
        rel = kin[clip.index["weapon_r"], 0] @ np.linalg.inv(kin[hand, 0])
        grip = np.array(rel[3, :3], float)
        out["r"] = (grip, grip + m._unit(rel[2, :3]) * AIM_BLADE * AIM_REACH, "bone")
    return out


def _shoulder(clip, kin, side_chain, want, share):
    """The clavicle turned about its pivot so the shoulder follows the wanted hand: with d the shoulder-to-hand
    distance and `ref` its slow part, the arm is left d' = ref + (d - ref)(1 - share), the least turn in the plane of
    the clavicle and the hand, no further than SHOULDER_MAX_DEG, eased in. Returns ({clavicle, upper arm, forearm,
    hand: their worlds carried by the turn}, the most it turned in degrees)."""
    clav, up, low, hand = side_chain
    if clav is None:
        return {}, 0.0
    F = kin.shape[1]
    P, S, H = kin[clav, :, 3, :3], kin[up, :, 3, :3], want[:, 3, :3]
    d = np.linalg.norm(H - S, axis=1)
    ref = m._blur(d, SLOW)
    limit = math.radians(SHOULDER_MAX_DEG)
    carried = dict((j, np.array(kin[j])) for j in (clav, up, low, hand))
    most = 0.0
    for f in range(F):
        c, h = S[f] - P[f], H[f] - P[f]
        r, D = float(np.linalg.norm(c)), float(np.linalg.norm(h))
        if r < 1e-6 or D < 1e-6:
            continue
        e = h / D
        p = c - np.dot(c, e) * e
        if float(np.linalg.norm(p)) < 1e-6 * r:
            continue
        p = m._unit(p)
        phi = math.acos(min(max(float(np.dot(c, e)) / r, -1.0), 1.0))
        wanted = ref[f] + (d[f] - ref[f]) * (1.0 - share)
        phi2 = math.acos(min(max((r * r + D * D - wanted * wanted) / (2.0 * r * D), -1.0), 1.0))
        theta = math.copysign(soft_reach(abs(phi - phi2), SHOULDER_FREE * limit, limit), phi - phi2)
        c2 = r * (math.cos(phi - theta) * e + math.sin(phi - theta) * p)
        M = swung_about(P[f], aim_swing(c, c2))
        for j in carried:
            carried[j][f] = kin[j, f] @ M
        most = max(most, math.degrees(abs(theta)))
    return carried, most


def apply(a, worlds, k, alpha=None, grip=False, weapons=None, still=None):
    """Walk Builder's Weapon tab on the frames (J, F, 4, 4) of a start or a stop. `alpha` (F,) how much a pose holds
    the arms a frame (Hold blends in by it; a hand the scene gives a weapon is held whole). `still` (F,) how still
    the body stands a frame: where it stands the hand keeps its own place on the chest (the pose's), the slow part
    taking over as it moves - a Gaussian reaching into the run put a start's hands 12-20 cm off its pose
    (2026-11-17). Returns (worlds, info, the sides held - their arm springs to be left off)."""
    F = np.asarray(worlds).shape[1]
    alpha = np.zeros(F) if alpha is None else np.clip(np.asarray(alpha, float), 0.0, 1.0)
    posed = bool(alpha.max() > 0.0)
    clip = a.clip
    ks = m.sided(k)
    chains_ = chains(clip)
    chest = _chest(clip)
    info = {"hold": [], "inherit": 1.0, "lag": 0.0, "hold_cm": 0.0, "aim": {"keep": {}, "lever": {}, "deg": 0.0,
                                                                            "asked": []},
            "shoulder": {"share": {}, "deg": 0.0}}
    if chest is None or not chains_:
        return worlds, info, set()
    held = held_sides(k, chains_, posed, weapons)
    aims = dict((s, min(max(float(ks[s]["weapon_aim"]), 0.0), 1.0)) for s in chains_)
    aims = dict((s, v) for s, v in aims.items() if v < 1.0 - QUIET)
    shoulders = dict((s, min(max(float(ks[s]["weapon_shoulder"]), 0.0), 1.0)) for s in chains_)
    shoulders = dict((s, v) for s, v in shoulders.items() if v > QUIET)
    info["aim"]["asked"] = sorted(aims)
    if not held and not aims and not shoulders:
        return worlds, info, held
    both = grip and len(chains_) == 2
    carrier = (list(weapons)[0] if weapons and len(weapons) == 1 else "r") if both else None
    body = m._Body(clip, worlds, a.follows)
    kin = body.kin
    root = kin[a.root]
    hands = {}
    # Hold: the hand rigid on the chest at its slow offset, on the chest of `lag` frames ago keeping `inherit` of
    # its motion over its slow part - the chest read in the root's frame (the locomotion taken out) and put back
    if held:
        fps = clip.fps
        C = kin[chest]
        Cr = _in(C, root)
        rows = {carrier: [carrier] + [s for s in sorted(held) if s != carrier]} if both and len(held) == 2 \
            else dict((s, [s]) for s in held)
        for side, riders in sorted(rows.items()):
            lag = sum(float(ks[s]["weapon_overlap"]) for s in riders) / len(riders) * fps / 1000.0
            keep = sum(min(max(float(ks[s]["weapon_inherit"]), 0.0), 1.0) for s in riders) / len(riders)
            H = np.array(kin[chains_[side][3]])
            own = _in(H, C)
            offset = slow_mats(own)
            if still is not None:
                offset = np.array([m.blend_matrix(offset[f], own[f], float(still[f])) for f in range(F)])
            want = _on(_on(offset, late(keeping(Cr, keep), lag)), root)
            weight = np.ones(F) if any(s in (weapons or {}) for s in riders) else alpha
            want = np.array([m.blend_matrix(H[f], want[f], float(weight[f])) for f in range(F)])
            T = np.einsum("fij,fjk->fik", np.linalg.inv(H), want)      # H_other . inv(H) . want: the hold kept
            for s in riders:
                hands[s] = want if s == side else np.einsum("fij,fjk->fik", np.array(kin[chains_[s][3]]), T)
            info["hold_cm"] = max(info["hold_cm"], float(np.linalg.norm(want[:, 3, :3] - H[:, 3, :3], axis=1).max()))
            info["lag"] = max(info["lag"], abs(lag))
            info["inherit"] = min(info["inherit"], keep)
        info["hold"] = sorted(held)
    # Aim target: the blade swung about its grip onto a target (read in the root's frame) keeping `keep` of its
    # motion over its slow part; hands holding one thing swing together
    if aims:
        lev = levers(clip, kin, chains_, weapons, sorted(aims))
        rows = {carrier: [carrier] + [s for s in sorted(aims) if s != carrier]} if both and len(aims) == 2 \
            else dict((s, [s]) for s in aims)
        for side, riders in sorted(rows.items()):
            if side not in lev:
                continue
            gp, ap, kind = lev[side]
            keep = sum(aims[s] for s in riders) / len(riders)
            for s in riders:
                if s not in hands:
                    hands[s] = np.array(kin[chains_[s][3]])
            H = hands[side]
            G = np.array([gp @ H[f, :3, :3] + H[f, 3, :3] for f in range(H.shape[0])])
            T = np.array([ap @ H[f, :3, :3] + H[f, 3, :3] for f in range(H.shape[0])])
            rr = np.array([m.orthonormal(r) for r in root])
            Tr = np.einsum("fi,fij->fj", T - root[:, 3, :3], np.swapaxes(rr, -1, -2))
            want = np.einsum("fi,fij->fj", keeping_points(Tr, keep), rr) + root[:, 3, :3]
            for f in range(H.shape[0]):
                a_, b_ = T[f] - G[f], want[f] - G[f]
                M = swung_about(G[f], aim_swing(a_, b_))
                for s in riders:
                    hands[s][f] = hands[s][f] @ M
                cos = float(np.dot(m._unit(a_), m._unit(b_)))
                info["aim"]["deg"] = max(info["aim"]["deg"], math.degrees(math.acos(min(max(cos, -1.0), 1.0))))
            info["aim"]["keep"][side], info["aim"]["lever"][side] = keep, kind
    # Shoulder, last: the clavicle follows the hand everything above has placed
    new = {}
    base = kin
    if shoulders:
        base = kin.copy()
        for side, share in sorted(shoulders.items()):
            if side not in hands:
                hands[side] = np.array(kin[chains_[side][3]])
            carried, deg = _shoulder(clip, kin, chains_[side], hands[side], share)
            for j, mats in carried.items():
                base[j] = mats
            if chains_[side][0] is not None and carried:
                new[chains_[side][0]] = carried[chains_[side][0]]
            info["shoulder"]["share"][side] = share
            info["shoulder"]["deg"] = max(info["shoulder"]["deg"], deg)
    for side, want in hands.items():
        new.update(arm_to_hand(clip, base, chains_[side], want))
    if new:
        body.set(new)
    return body.worlds, info, held


def line(info):
    """What the Weapon tab did, for a status line ("" for nothing)."""
    text = ""
    if info.get("hold"):
        who = "both hands" if len(info["hold"]) > 1 else "the %s hand" % {"l": "left", "r": "right"}[info["hold"][0]]
        keep = info.get("inherit", 1.0)
        if keep < 0.005:
            text += " | %s on the chest's slow motion only" % who
        else:
            text += " | %s ride the chest" % who + (" at %.0f %% of its motion" % (100 * keep) if keep < 1 - QUIET else "")
        if info.get("lag"):
            text += ", %.1f fr late" % info["lag"]
    aim = info.get("aim") or {}
    if aim.get("keep"):
        keep = min(aim["keep"].values())
        text += " | the blade aims at a target keeping %.0f %% of its motion (swung up to %.0f deg)" % (
            100 * keep, aim.get("deg", 0.0))
    elif aim.get("asked"):
        text += " | no weapon in the hand and no weapon bone: Aim target does nothing"
    did = info.get("shoulder") or {}
    if did.get("share"):
        text += " | the shoulder takes %.0f %% of the arm's reach (up to %.0f deg)" % (
            100 * max(did["share"].values()), did["deg"])
    return text
