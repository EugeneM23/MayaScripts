"""verify_walk_gait - Walk Builder's parameters (maya_walk.gait) on the animator's saved walks, headless (mayapy,
no Maya scene): `mayapy verify_walk_gait.py [phase ...] [--walks a,b]`.

Phases:
- complaints: the legs' complaints measured with the physics on - at Step x1, x1.15, x1.3, plain and under the
  goblin and the two-handed sword: the pelvis drop, the planted knee's straightest, the knee's clicks, the trailing
  heel up at the toe-off, the leading knee at the contact, the side sway of the centre of mass against the linear
  inverted pendulum's, the arms' swing and lag kept under Whip;
- identity: the parameters at the clip's own values, the physics off, give the engine's own reading of the clip
  (walk.own_knobs: <= 1e-5 cm) and that the clip (<= 5e-4 cm: its own seam);
- readback: each parameter at three values in its range, the physics off: each side's change within its own reach
  (gait.ranges with the walk: an arm swings, an elbow straightens, a foot lowers only so far), the sides' mean
  within 10 % of it or 0.3 of its unit - wherever the pelvis did not lower for the reach (the Diagnosis's "physics
  gave way"; 0.5 cm for the pelvis's height and bob). Foot flat only on a foot that lands on its heel (5 deg of
  toes up): a foot landing flat has no foot-flat to move;
- effect: each parameter over its range moves its body part at least 5 deg or 3 cm (a fifth of its range where
  that is less).

The walks are read from the animator's walks folder (never written); the poses' .wpose files beside them.
"""
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
from maya_walk import clean as wc, files as wf, gait, model as wm, pose as wp, target as wt     # noqa: E402

FOLDER = os.environ.get("SKELDAR_WALKS", os.path.join(os.path.expanduser("~"), "Documents", "maya", "SkeldarWalks"))
WALKS = ("asd", "dw", "HavyRun", "sadda", "TestStrefe")
POSES = ("goblin", "two_handed_sword")
FAILED = []


def gate(ok, text):
    print("  %s %s" % ("ok  " if ok else "FAIL", text))
    if not ok:
        FAILED.append(text)
    return ok


def load(name):
    data = wf.load(os.path.join(FOLDER, name + ".walk.gz"))
    clip, _ = wc.clean(wf.clip_of(data, wm), data["statics"], given={})
    return wm.analyse(clip), data["statics"]


def pose_of(walk, statics, name):
    path = os.path.join(FOLDER, name + ".wpose.gz")
    if not os.path.exists(path):
        return None
    return wp.prepare(walk, statics, wf.load_pose(path)[1], wm, wt)


def run(walk, own, asked, pins, pose=None, share=1.0, physics=True):
    k = gait.engine_knobs(walk, own, asked, pins=pins, physics=physics)
    if pose is not None:
        k["pose"] = share
    return walk.evaluate(k, pose)


def knee_series(walk, r, side):
    c = gait.Cycle(walk, r.worlds, r.info["contacts"])
    return gait._knee_bend(c, side), c


def clicks(walk, r):
    """The knees' worst second difference (deg / frame^2) on frames within 25 deg of straight."""
    worst = 0.0
    for s in gait.SIDES:
        bend, c = knee_series(walk, r, s)
        n = len(bend)
        for f in range(n):
            if bend[f] < 25.0:
                worst = max(worst, abs(bend[(f + 1) % n] - 2.0 * bend[f] + bend[f - 1]))
    return worst


def leading_knee(walk, r):
    """The knee's bend at its heel strike (mean of the contacts), deg."""
    out = []
    for s in gait.SIDES:
        bend, c = knee_series(walk, r, s)
        out += [c.at(bend, hs) for hs, _ in c.contacts[s]]
    return float(np.mean(out)) if out else 0.0


def lipm_sway(walk, r, m):
    """(the centre of mass's side sway p2p, the linear inverted pendulum's p2p for the result's width, step time
    and CoM height): 2 b (1 - sech(w T / 2)), b half the width, T a step's seconds, w = sqrt(g / h)."""
    com = walk.com(r.worlds[:, :r.frames])
    n = r.frames
    line = r.worlds[walk.index["root"], 0, 3, :3][None] + np.outer(np.arange(n) / float(n),
                                                                    r.worlds[walk.index["root"], n, 3, :3]
                                                                    - r.worlds[walk.index["root"], 0, 3, :3])
    side = (com - line) @ np.asarray(walk.basis)[1]
    h = float((com @ np.asarray(walk.up)).mean() - min(r.worlds[walk.index["foot_l"], :, 3, :3] @ np.asarray(walk.up)))
    w = math.sqrt(981.0 / max(h, 1.0))
    T = m["tempo"] / walk.fps
    b = 0.5 * m["width"]
    return float(np.ptp(side)), 2.0 * b * (1.0 - 1.0 / math.cosh(w * T / 2.0))


def phase_complaints(walks):
    print("complaints (physics on)")
    for name in walks:
        walk, statics = load(name)
        own = gait.own(walk)
        poses = [("plain", None)] + [(p, pose_of(walk, statics, p)) for p in POSES]
        for label, pose in poses:
            if label != "plain" and pose is None:
                continue
            for factor in (1.0, 1.15, 1.3):
                changes = {"step": ("ratio", factor)}
                vals = gait.values(own, changes, pins={"step"})
                t0 = time.time()
                r = run(walk, own, vals, {"step"}, pose)
                m = gait.of_result(walk, r)
                sway, lipm = lipm_sway(walk, r, m)
                print("  %-10s %-17s x%.2f drop %5.1f cm  knee min %5.1f  clicks %5.1f  push %5.1f (asked %5.1f)  "
                      "lead knee %5.1f  sway %4.1f / LIPM %4.1f  arm %5.1f (own %5.1f) lag %+5.1f (own %+5.1f)  %.1fs"
                      % (name, label, factor, r.info["lowered"], m["knee_bend"], clicks(walk, r), m["push"],
                         vals["push"], leading_knee(walk, r), sway, lipm, m["arm_swing"], own["arm_swing"],
                         m["arm_lag"], own["arm_lag"], time.time() - t0))


def phase_identity(walks):
    print("identity")
    for name in walks:
        walk, _ = load(name)
        own = gait.own(walk)
        r = run(walk, own, own, set(), physics=False)
        engine = walk.evaluate(walk.own_knobs())
        d = float(np.abs(r.worlds - engine.worlds).max())
        seam = float(np.abs(engine.worlds[:, :walk.P + 1] - walk.clip.worlds).max())
        gate(d <= 1e-5, "%s: the own values give the engine's own reading (%.2g cm)" % (name, d))
        gate(seam <= 5e-4, "%s: which is the clip (%.2g cm)" % (name, seam))


def _wrapped(name, d, frames):
    if name == "chest_timing":
        return (d + 180.0) % 360.0 - 180.0
    if name in ("arm_lag", "elbow_lag"):
        return (d + 0.5 * frames) % frames - 0.5 * frames
    return d


VERTICAL = ("bounce", "low_point", "double_bounce", "height", "knee_bend")    # read off the pelvis's height


def phase_readback(walks):
    print("readback (physics off)")
    for name in walks:
        walk, _ = load(name)
        own = gait.own(walk)
        rng = gait.ranges(own, walk.leg_length, walk)
        base = gait.of_result(walk, run(walk, own, own, set(), physics=False))
        for p in gait.PARAMS:
            if p.kind in ("added", "toggle"):
                continue
            lo, hi = rng[p.name]
            sides = [p.name + "_" + s for s in gait.SIDES] if p.sided else [p.name]
            if p.name == "foot_flat":         # a foot landing flat has no foot-flat to move
                sides = [k for k in sides if own[k.replace("foot_flat", "heel_strike")] >= 5.0]
                if not sides:
                    print("    (%s foot_flat: both feet land flat)" % name)
                    continue
            for share in (-0.5, 0.35, 0.8):
                o = own[p.name]
                d = share * ((hi - o) if share > 0 else (o - lo))
                if abs(d) < 0.05:
                    continue
                asked = dict(own, **{p.name: o + d})
                if p.sided:
                    for s in gait.SIDES:
                        asked[p.name + "_" + s] = own[p.name + "_" + s] + d
                r = run(walk, own, asked, {p.name}, physics=False)
                if r.info["lowered"] > (0.5 if p.name in VERTICAL else 2.0):
                    print("    (%s %s %+.2f: the pelvis lowered %.1f cm - physics)" % (name, p.name, d, r.info["lowered"]))
                    continue
                m = gait.of_result(walk, r)
                frames = r.frames / float(walk.strides)
                bound = lambda k, v: min(max(v, gait.reach(walk, k)[0] if gait.reach(walk, k)[0] is not None
                                             else v), gait.reach(walk, k)[1] if gait.reach(walk, k)[1] is not None
                                         else v)
                floor = (lambda v: max(v, 0.0)) if (p.kind == "size" or p.name == "foot_flat") else (lambda v: v)
                want = [floor(bound(k, own[k] + d)) - own[k] for k in sides]       # within its reach
                got = [_wrapped(p.name, m[k] - base[k], frames) for k in sides]
                want, got = float(np.mean(want)), float(np.mean(got))
                if p.name == "foot_flat":     # the stretch of a heel strike, sampled at whole frames: approximate
                    gate(got * want > 0.0 and abs(got) >= 0.5 * abs(want) or abs(want) < 0.3,
                         "%s foot_flat %+.2f (%+.2f in reach) -> %+.2f (at least half, approximate)"
                         % (name, d, want, got))
                    continue
                gate(abs(got - want) <= max(0.1 * abs(want), 0.3),
                     "%s %s %+.2f (%+.2f in reach) -> %+.2f" % (name, p.name, d, want, got))


def phase_effect(walks):
    print("effect")
    parts = {"step": "foot_l", "width": "foot_l", "bounce": "pelvis", "lean": "neck_01", "arm_swing": "hand_l",
             "sway": "pelvis", "surge": "pelvis", "hips_twist": "pelvis", "chest_twist": "upperarm_l",
             "head_motion": "head", "foot_lift": "foot_l", "elbow": "hand_l", "arms_forward": "hand_l",
             "arm_out": "hand_l", "push": "foot_l", "heel_strike": "ball_l", "height": "pelvis", "forward": "pelvis",
             "toe_out": "ball_l", "tempo": "foot_l", "arm_lag": "hand_l", "low_point": "pelvis"}
    for name in walks:
        walk, _ = load(name)
        own = gait.own(walk)
        rng = gait.ranges(own, walk.leg_length, walk)
        base = run(walk, own, own, set())
        for pname, joint in parts.items():
            p = gait.P[pname]
            lo, hi = rng[pname]
            cm = deg = 0.0
            for v in (lo, hi):
                asked = dict(own, **{pname: v})
                if p.sided:
                    for s in gait.SIDES:
                        asked[pname + "_" + s] = own[pname + "_" + s] + (v - own[pname])
                r = run(walk, own, asked, {pname})
                j = walk.index[joint]
                n = min(r.frames, base.frames)
                a = r.worlds[j, :n, 3, :3] - r.worlds[walk.index["root"], :n, 3, :3]
                b = base.worlds[j, :n, 3, :3] - base.worlds[walk.index["root"], :n, 3, :3]
                cm = max(cm, float(np.linalg.norm(a - b, axis=1).max()))
                turn = np.einsum("fij,fkj->fik", r.worlds[j, :n, :3, :3], base.worlds[j, :n, :3, :3])
                deg = max(deg, float(np.degrees(np.arccos(np.clip((np.trace(turn, axis1=1, axis2=2) - 1.0) / 2.0,
                                                                   -1.0, 1.0))).max()))
            span = hi - lo
            need_cm = min(3.0, 0.2 * span) if p.unit == "cm" else 3.0
            need_deg = min(5.0, 0.2 * span) if p.unit == "deg" else 5.0
            gate(cm >= need_cm or deg >= need_deg, "%s %s moves %s %.1f cm / %.1f deg over its range (%.1f %s)"
                 % (name, pname, joint, cm, deg, span, p.unit))


PHASES = {"complaints": phase_complaints, "identity": phase_identity, "readback": phase_readback,
          "effect": phase_effect}


def main(argv):
    walks = list(WALKS)
    names = []
    for a in argv:
        if a.startswith("--walks="):
            walks = a.split("=", 1)[1].split(",")
        else:
            names.append(a)
    walks = [w for w in walks if os.path.exists(os.path.join(FOLDER, w + ".walk.gz"))]
    for phase in names or ["identity", "readback", "complaints", "effect"]:
        PHASES[phase](walks)
    print("%d gate(s) failed" % len(FAILED))
    for text in FAILED:
        print("  - " + text)


if __name__ == "__main__":
    main(sys.argv[1:])
