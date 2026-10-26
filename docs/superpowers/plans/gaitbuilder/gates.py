"""gates.py - Gait Builder measured on the animator's real walks, headless (mayapy; no Maya scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/gaitbuilder/gates.py <gate> [walk ...]

Gates: parity (the fork against Walk Builder at Walk Builder's knobs), speed, clicks, identity, readback, effect,
redundancy, all. GATE_POSE=<pose> (GATE_POSE_SHARE, default 1) runs readback, effect, redundancy and clicks under a
saved pose. The walks: the animator's saved walks (WALKS_HOME, default <Documents>/maya/SkeldarWalks) - asd,
dw, HavyRun when there - and the CAT Walk preset. A walk not on this machine is skipped and named.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
WALKS = os.environ.get("WALKS_HOME", os.path.join(os.path.expanduser("~"), "Documents", "maya", "SkeldarWalks"))
for path in (HERE, PLUGIN):
    if path not in sys.path:
        sys.path.insert(0, path)

import gaitmodel as gm                                       # noqa: E402
import aspects as asp                                        # noqa: E402
import gaitgen                                               # noqa: E402
from maya_walk import model as wm, files as wf, clean as wc, meanpose as mp      # noqa: E402
from maya_walk import pose as wp, target as wt                                  # noqa: E402

SPEED_SHARE = 0.45                # an evaluation's CPU time against Walk Builder's
PARITY_APPROX = (0.1, 0.2)        # cm, deg: the fork's speed-ups against Walk Builder
FAILED = []
COUNT = [0]
ONLY = [k for k in os.environ.get("GATE_KNOBS", "").split(",") if k]     # the knobs to gate (none: all)
# readback, effect, redundancy and clicks under a saved pose (WALKS/<name>.wpose.gz) at its share, when set
POSE = os.environ.get("GATE_POSE") or None
POSE_SHARE = float(os.environ.get("GATE_POSE_SHARE", "1.0"))


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(text)


def read(name):
    """(the fork's walk, Walk Builder's walk, statics) of the saved walk `name`, read as Walk Builder reads it
    (cleaned at the default Clean knobs, the animator's mean pose correction applied), or None when absent.
    "cat:<preset>" is a CAT preset made a clip (gaitgen)."""
    if name.startswith("cat:"):
        clip, statics = gaitgen.preset_clip(name[4:], 30.0, gm)
        theirs = wm.analyse(wm.Clip(clip.names, clip.parents, np.array(clip.worlds), clip.fps, clip.up, clip.name))
        return gm.analyse(clip), theirs, statics
    path = os.path.join(WALKS, name + ".walk.gz")
    if not os.path.exists(path):
        print("skip: no walk %s in %s" % (name, WALKS))
        return None
    data = wf.load(path)
    clip, _ = wc.clean(wf.clip_of(data, wm), data["statics"], None, wc.knobs({}))
    fix = mp.load(mp.path_for(path))
    clip = mp.correct(clip, fix)
    ours = gm.analyse(gm.Clip(clip.names, clip.parents, np.array(clip.worlds), clip.fps, clip.up, clip.name))
    ours.fix = mp.model_fix(fix)
    theirs = wm.analyse(clip)
    theirs.fix = mp.model_fix(fix)
    return ours, theirs, data["statics"]


def best_time(fn, runs=5):
    best = 1e9
    for _ in range(runs):
        t0 = time.process_time()           # CPU time: other programs on this machine (Unity) skew the wall clock
        fn()
        best = min(best, time.process_time() - t0)
    return best


def worst(a, b):
    return float(np.abs(np.asarray(a) - np.asarray(b)).max())


def apart(a, b):
    """(cm, deg): the worst place and turn difference of two cycles of world matrices (J, F, 4, 4)."""
    a, b = np.asarray(a), np.asarray(b)
    cm = float(np.linalg.norm(a[..., 3, :3] - b[..., 3, :3], axis=-1).max())
    rel = np.einsum("...ij,...kj->...ik", a[..., :3, :3], b[..., :3, :3])
    c = np.clip((np.trace(rel, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0)
    return cm, float(np.degrees(np.arccos(c)).max())


def gate_parity(names):
    for name in names:
        got = read(name)
        if got is None:
            continue
        ours, theirs, _ = got
        # exact without the balance's arm re-swing (ARM_RECARRY, the one named approximation), within
        # PARITY_APPROX with it
        for given in ({}, theirs.own_knobs(), {"stride": 1.3}, {"ground_time": 1.2, "weight": 1.0}):
            cm, deg = apart(ours.evaluate(given).worlds, theirs.evaluate(given).worlds)
            gate(cm <= PARITY_APPROX[0] and deg <= PARITY_APPROX[1],
                 "parity %s %s: %.4f cm, %.4f deg" % (name, sorted(given)[:3], cm, deg))


def gate_speed(names):
    for name in names:
        got = read(name)
        if got is None:
            continue
        ours, theirs, _ = got
        ours.evaluate({})
        t_ours = best_time(lambda: ours.evaluate({}))
        t_theirs = best_time(lambda: theirs.evaluate({}))
        # the spec's 0.35 s, or SPEED_SHARE of Walk Builder's in the same run (this machine runs Unity beside)
        gate(t_ours <= 0.35 or t_ours <= SPEED_SHARE * t_theirs,
             "speed %s: %.3f s CPU, %.0f %% of Walk Builder's %.3f s" % (name, t_ours, 100 * t_ours / t_theirs, t_theirs))


GROUPS = (("pelvis", ("pelvis",)), ("spine", ("spine_", "neck_")), ("head", ("head",)),
          ("arms", ("clavicle_", "upperarm_", "lowerarm_")), ("hands", ("hand_",)),
          ("legs", ("thigh_", "calf_")), ("feet", ("foot_", "ball_")))
SKIP = ("twist", "ik_", "weapon", "camera", "interaction", "center_of_mass", "metacarpal")
READBACK_SHARE, READBACK_UNIT = 0.15, 1.0     # within 15 % of the asked change, or 1 unit
EFFECT_DEG, EFFECT_CM = 5.0, 3.0              # a knob over its range moves its part at least this (rms)
SIMILAR = 0.85                                # no two knobs' signed effects correlated past this
# Pairs that move together by design, not a duplicate: Speed sets the step by the walk ratio (the macro), and a
# helper (Foot placement, Balance) acts through what the other knobs change
REDUNDANT_OK = (("speed", "step"),)
HELPERS = ("placement", "balance")
# A switch is on or off, not a range of motion: its effect is whatever the walk's own motion there is (the root's
# weave, the travel), so it has no effect to gate
SWITCHES = ("root_line", "in_place", "placement")
# Balance acts on what changes the feet's support: gated at the widest stance, and under a pose that leans the
# body off its feet (the animator's goblin, when on this machine)
BALANCE_UNDER = {"width": "hi"}
BALANCE_POSE = "goblin"
CLICK_ABS, CLICK_SHARE = 12.0, 1.5            # knee clicks: at most max(12, 1.5 x the clip's own) deg/frame^2


def groups_of(names):
    out = {}
    for i, name in enumerate(names):
        leaf = name.lower()
        if any(k in leaf for k in SKIP):
            continue
        for g, prefixes in GROUPS:
            if any(leaf == p or leaf.startswith(p) for p in prefixes):
                out.setdefault(g, []).append(i)
    return dict((g, np.array(v)) for g, v in out.items())


def against_line(worlds):
    """places (J, n, 3) against the root's straight line, rotations (J, n, 3, 3), n frames (closing dropped)"""
    w = np.asarray(worlds)
    n = w.shape[1] - 1
    root = 0
    t = np.linspace(0.0, 1.0, n + 1)[:, None]
    line = w[root, 0, 3, :3][None] + (w[root, n, 3, :3] - w[root, 0, 3, :3])[None] * t
    return (w[:, :, 3, :3] - line[None])[:, :n], w[:, :n, :3, :3]


def resampled(pos, rot, n):
    F = pos.shape[1]
    if F == n:
        return pos, rot
    idx = np.round(np.arange(n) * F / float(n)).astype(int) % F
    return pos[:, idx], rot[:, idx]


def group_change(a, b, groups):
    """{group: (rms deg, rms cm)} of cycle b against cycle a (by phase)"""
    pa, ra = against_line(a)
    pb, rb = resampled(*against_line(b), pa.shape[1])
    rel = np.einsum("jfab,jfcb->jfac", rb, ra)
    c = np.clip((np.trace(rel, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0)
    ang = np.degrees(np.arccos(c))
    d = np.linalg.norm(pb - pa, axis=-1)
    return dict((g, (float(np.sqrt(np.mean(ang[i] ** 2))), float(np.sqrt(np.mean(d[i] ** 2))))) for g, i in groups.items())


def joint_change(a, b, groups):
    """{group: (deg, cm)} of cycle b against cycle a: the most any one joint of the group moves (rms over the
    cycle) - a chest knob turns the top spine joint far and the lumbar little, which a group rms dilutes"""
    pa, ra = against_line(a)
    pb, rb = resampled(*against_line(b), pa.shape[1])
    rel = np.einsum("jfab,jfcb->jfac", rb, ra)
    c = np.clip((np.trace(rel, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0)
    ang = np.sqrt(np.mean(np.degrees(np.arccos(c)) ** 2, axis=1))
    d = np.sqrt(np.mean(np.linalg.norm(pb - pa, axis=-1) ** 2, axis=1))
    return dict((g, (float(ang[i].max()), float(d[i].max()))) for g, i in groups.items())


def own_motion(worlds, idx):
    """deg: the most any joint of `idx` turns about its own mean over the cycle (rms) - what a knob that holds it
    still can take away"""
    _, r = against_line(worlds)
    out = 0.0
    for j in idx:
        u, _, vt = np.linalg.svd(np.sum(r[j], axis=0))
        mean = u @ vt
        c = np.clip((np.einsum("fab,ab->f", r[j], mean) - 1.0) / 2.0, -1.0, 1.0)
        out = max(out, float(np.sqrt(np.mean(np.degrees(np.arccos(c)) ** 2))))
    return out


def signed_change(a, b, idx):
    pa, ra = against_line(a)
    pb, rb = resampled(*against_line(b), pa.shape[1])
    rel = np.einsum("jfab,jfcb->jfac", rb[idx], ra[idx])
    return np.concatenate([np.degrees(gm.log_rot(rel)).ravel(), (pb[idx] - pa[idx]).ravel()])


def read_pose(name, walk, statics):
    """The saved pose `name` (WALKS/<name>.wpose.gz) carried onto the walk (walkpose.prepare with the fork), or
    None when absent."""
    path = os.path.join(WALKS, name + ".wpose.gz")
    if not os.path.exists(path):
        print("skip: no pose %s in %s" % (name, WALKS))
        return None
    return wp.prepare(walk, statics, wf.load_pose(path)[1], gm, wt)


class Bench(object):
    """One walk under Gait Builder's knobs: its base measure and an evaluator by knob values; under a saved pose
    at `share` when `pose` names one (the calibrated knobs' responses probed with no pose, as gaitload keeps
    them)."""

    def __init__(self, name, pose=None, share=1.0):
        got = read(name)
        self.ok = got is not None
        if not self.ok:
            return
        self.name = name
        self.walk, self.theirs, self.statics = got
        self.pose, self.share = None, 0.0
        if pose:
            self.pose = read_pose(pose, self.walk, self.statics)
            self.ok = self.pose is not None
            if not self.ok:
                return
            self.share = share
        plain_result = self.walk.evaluate(asp.base_engine(self.walk))
        plain = asp.measure(self.walk, plain_result.worlds)
        asp.annotate(self.walk, plain, plain_result)
        curves = asp.calibrate(self.walk, plain,
                               lambda g: self.walk.evaluate(asp.engine_knobs(self.walk, plain, g)))
        if self.pose is None:
            self.base_result, self.base = plain_result, plain
        else:
            e = asp.base_engine(self.walk)
            e["pose"] = self.share
            self.base_result = self.walk.evaluate(e, self.pose)
            self.base = asp.measure(self.walk, self.base_result.worlds)
            asp.annotate(self.walk, self.base, self.base_result)
            self.base["_curve"] = curves
        self.range = asp.ranges(self.base, self.walk.leg_length)
        self.groups = groups_of(self.walk.names)

    def run(self, gait):
        e = asp.engine_knobs(self.walk, self.base, gait)
        if self.pose is None:
            return self.walk.evaluate(e)
        e["pose"] = self.share
        return self.walk.evaluate(e, self.pose)

    def own(self, knob):
        v = asp.defaults(self.base)[knob]
        return 0.5 * (v["l"] + v["r"]) if isinstance(v, dict) else v

    def ask(self, knob, delta):
        """The gait moving `knob` by `delta` from the walk's own value - a sided knob each side from its own
        (HavyRun's planted knees straighten to 52 and 15 deg: one value for both moved one side 24 and the
        other none)."""
        v = asp.defaults(self.base)[knob]
        if isinstance(v, dict):
            return dict((knob + "_" + s, v[s] + delta) for s in "lr")
        return {knob: v + delta}

    def change(self, knob, m):
        """The measured change of `knob` in the measure `m` against the walk's own (both sides' mean)."""
        got = m[asp.BY_NAME[knob].key]
        own = self.base[asp.BY_NAME[knob].key]
        if isinstance(got, dict):
            return 0.5 * sum(got[s] - own[s] for s in "lr")
        return got - own


def knee_click(worlds, names):
    """(the worst knee click, deg / frame^2, over both legs: the knee angle's second difference on frames within
    25 deg of straight; the straightest knee, deg)"""
    w = np.asarray(worlds)
    ix = dict((n, i) for i, n in enumerate(names))
    worst, straight = 0.0, 180.0
    for s in "lr":
        h, k, a = (w[ix[b + "_" + s], :-1, 3, :3] for b in ("thigh", "calf", "foot"))
        u, v = k - h, a - k
        bend = np.degrees(np.arccos(np.clip(np.sum(u * v, 1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1)),
                                            -1.0, 1.0)))
        acc = np.abs(np.roll(bend, -1) - 2.0 * bend + np.roll(bend, 1))
        near = bend < 25.0
        if near.any():
            worst = max(worst, float(acc[near].max()))
        straight = min(straight, float(bend.min()))
    return worst, straight


def gate_identity(names):
    for name in names:
        b = Bench(name)
        if not b.ok:
            continue
        off = {"placement": 0.0, "follow": 0.0, "root_line": 0.0}
        cm, deg = apart(b.run(off).worlds, b.walk.clip.worlds)
        wb_cm, wb_deg = apart(b.theirs.evaluate(b.theirs.own_knobs()).worlds, b.walk.clip.worlds)
        gate(cm <= max(1e-3, wb_cm + 1e-6) and deg <= max(1e-2, wb_deg + 1e-6),
             "identity %s: the physics off gives the clip to %.4f cm, %.4f deg (Walk Builder's own knobs: %.4f cm, "
             "%.4f deg)" % (name, cm, deg, wb_cm, wb_deg))


def gate_readback(names):
    for name in names:
        b = Bench(name, POSE, POSE_SHARE)
        if not b.ok:
            continue
        for knob in asp.KNOBS:
            if knob.kind != "measured":
                continue
            own = b.own(knob.name)
            lo, hi = b.range[knob.name]
            for target in (own + 0.25 * (hi - own), own - 0.25 * (own - lo)):
                asked = target - own
                if abs(asked) < 1e-3:
                    continue
                change = b.change(knob.name, asp.measure(b.walk, b.run(b.ask(knob.name, asked)).worlds))
                unit = 0.05 if knob.name == "speed" else READBACK_UNIT
                ok = abs(change - asked) <= max(READBACK_SHARE * abs(asked), unit)
                gate(ok, "readback %s %s: asked %+.2f %s, got %+.2f" % (name, knob.name, asked, knob.unit, change))


def _effect_of(b, knob, under=None):
    """(deg, cm, group): the most a knob moves any joint over its range, from its own value to either end, with
    the gait `under` held."""
    lo, hi = b.range[knob.name]
    best = (0.0, 0.0, "")
    own = b.own(knob.name) if knob.kind == "measured" else knob.default
    start = b.run(under).worlds if under else b.base_result.worlds
    for end in (lo, hi):
        gait = dict(under or {})
        gait.update(b.ask(knob.name, end - own) if knob.kind == "measured" else {knob.name: end})
        for g, (deg, cm) in joint_change(start, b.run(gait).worlds, b.groups).items():
            if deg / EFFECT_DEG + cm / EFFECT_CM > best[0] / EFFECT_DEG + best[1] / EFFECT_CM:
                best = (deg, cm, g)
    return best


def gate_effect(names):
    for name in names:
        b = Bench(name, POSE, POSE_SHARE)
        if not b.ok:
            continue
        head_own = own_motion(b.base_result.worlds, b.groups.get("head", []))
        for knob in asp.KNOBS:
            if ONLY and knob.name not in ONLY:
                continue
            lo, hi = b.range[knob.name]
            deg, cm, g = _effect_of(b, knob)
            text = "effect %s %s over %.1f..%.1f %s: %.1f deg, %.1f cm (%s)" % (name, knob.name, lo, hi, knob.unit,
                                                                              deg, cm, g)
            if knob.name in SWITCHES:
                print("        %s - a switch, not gated" % text)
                continue
            need = EFFECT_DEG
            if knob.name == "head_steady":
                # holds the head still: it can take away the walk's own head motion and no more
                need = min(EFFECT_DEG, 0.8 * head_own)
                text += " - the walk's head turns %.1f deg of its own" % head_own
            if knob.name == "balance":
                under = {}
                for other, end in BALANCE_UNDER.items():
                    lo2, hi2 = b.range[other]
                    under.update(b.ask(other, (hi2 if end == "hi" else lo2) - b.own(other)))
                deg2, cm2, g2 = _effect_of(b, knob, under)
                text += "; at the widest stance %.1f deg, %.1f cm (%s)" % (deg2, cm2, g2)
                deg, cm = max(deg, deg2), max(cm, cm2)
                posed = Bench(name, BALANCE_POSE) if BALANCE_POSE else None
                if posed is not None and posed.ok:
                    deg3, cm3, g3 = _effect_of(posed, knob)
                    text += "; under the %s pose %.1f deg, %.1f cm (%s)" % (BALANCE_POSE, deg3, cm3, g3)
                    deg, cm = max(deg, deg3), max(cm, cm3)
            gate(deg >= need or cm >= EFFECT_CM, text)


def gate_redundancy(names):
    for name in names:
        b = Bench(name, POSE, POSE_SHARE)
        if not b.ok:
            continue
        idx = np.concatenate(list(b.groups.values()))
        vecs, labels = [], []
        for knob in asp.KNOBS:
            lo, hi = b.range[knob.name]
            own = b.own(knob.name) if knob.kind == "measured" else knob.default
            step = 0.15 * (hi - lo)
            target = own + step if own + step <= hi else own - step
            gait = b.ask(knob.name, target - own) if knob.kind == "measured" else {knob.name: target}
            v = signed_change(b.base_result.worlds, b.run(gait).worlds, idx)
            if np.linalg.norm(v) > 1e-6:
                vecs.append(v / np.linalg.norm(v))
                labels.append(knob.name)
        sim = np.abs(np.array(vecs) @ np.array(vecs).T)
        pairs = [(sim[i, j], labels[i], labels[j]) for i in range(len(labels)) for j in range(i + 1, len(labels))
                 if sim[i, j] > SIMILAR]
        declared = [p for p in pairs if tuple(sorted(p[1:])) in [tuple(sorted(x)) for x in REDUNDANT_OK]
                    or p[1] in HELPERS or p[2] in HELPERS]
        pairs = [p for p in pairs if p not in declared]
        sv = np.linalg.svd(np.array(vecs), compute_uv=False)
        share = np.cumsum(sv ** 2) / np.sum(sv ** 2)
        gate(not pairs, "redundancy %s: %d knobs, %s%s; 90 %% of the change in %d directions, 99 %% in %d" % (
            name, len(labels), "; ".join("%s~%s %.2f" % (a, c, v) for v, a, c in sorted(pairs, reverse=True)) or
            "no pair past %.2f" % SIMILAR,
            " (by design: %s)" % "; ".join("%s~%s %.2f" % (a, c, v) for v, a, c in sorted(declared, reverse=True))
            if declared else "", np.searchsorted(share, 0.9) + 1, np.searchsorted(share, 0.99) + 1))


def gate_clicks(names):
    for name in names:
        b = Bench(name, POSE, POSE_SHARE)
        if not b.ok:
            continue
        clip_click, _ = knee_click(b.walk.clip.worlds, b.walk.names)
        ref = "the clip's own"
        if b.pose is not None:
            # under a pose the engine's own walk is the reference: Walk Builder at its own knobs under the goblin
            # clicks 21 deg/fr^2 on dw's knees with nothing asked (Gait Builder's defaults 21.1, the bare clip 12.9)
            posed, _ = knee_click(b.base_result.worlds, b.walk.names)
            if posed > clip_click:
                clip_click, ref = posed, "the posed walk's own"
        configs = [("defaults", {})]
        for knob in ("step", "duty", "bob", "lift"):
            lo, hi = b.range[knob]
            own = b.own(knob)
            configs += [(knob + " low", b.ask(knob, lo - own)), (knob + " high", b.ask(knob, hi - own))]
        configs += [("height +10", {"height": 10.0}), ("height -15", {"height": -15.0}), ("weight +1", {"weight": 1.0}),
                    ("speed high", {"speed": b.range["speed"][1]})]
        for label, gait in configs:
            r = b.run(gait)
            click, straight = knee_click(r.worlds, b.walk.names)
            # deg / frame^2 grow as the cadence squared: the clip's own motion played faster is not a click
            pace = (b.walk.P / float(r.frames)) ** 2
            limit = max(CLICK_ABS, CLICK_SHARE * clip_click * pace)
            gate(click <= limit, "clicks %s %s: %.1f deg/fr^2 (%s %.1f x%.2f the pace, limit %.1f), "
                 "straightest %.1f, pelvis down %.1f" % (name, label, click, ref, clip_click, pace, limit, straight,
                                                        r.info["lowered"]))


GATES = {"parity": gate_parity, "speed": gate_speed, "identity": gate_identity, "readback": gate_readback,
         "effect": gate_effect, "redundancy": gate_redundancy, "clicks": gate_clicks}


def main(argv):
    which = argv[0] if argv else "all"
    names = argv[1:] or ["asd", "dw", "HavyRun", "cat:Walk"]
    for key, fn in GATES.items():
        if which in (key, "all"):
            fn(names)
    if POSE:
        print("under the %s pose at %.2f" % (POSE, POSE_SHARE))
    print("%d gates, %d failed" % (COUNT[0], len(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
