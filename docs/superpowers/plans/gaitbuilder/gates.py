"""gates.py - Gait Builder measured on the animator's real walks, headless (mayapy; no Maya scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/gaitbuilder/gates.py <gate> [walk ...]

Gates: parity (the fork against Walk Builder at Walk Builder's knobs), speed, clicks, identity, readback, effect,
redundancy, all. The walks: the animator's saved walks (WALKS_HOME, default <Documents>/maya/SkeldarWalks) - asd,
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

SPEED_SHARE = 0.45                # an evaluation's CPU time against Walk Builder's
PARITY_APPROX = (0.1, 0.2)        # cm, deg: the fork's speed-ups against Walk Builder
FAILED = []
COUNT = [0]


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


def signed_change(a, b, idx):
    pa, ra = against_line(a)
    pb, rb = resampled(*against_line(b), pa.shape[1])
    rel = np.einsum("jfab,jfcb->jfac", rb[idx], ra[idx])
    return np.concatenate([np.degrees(gm.log_rot(rel)).ravel(), (pb[idx] - pa[idx]).ravel()])


class Bench(object):
    """One walk under Gait Builder's knobs: its base measure and an evaluator by knob values."""

    def __init__(self, name):
        got = read(name)
        self.ok = got is not None
        if not self.ok:
            return
        self.name = name
        self.walk, self.theirs, self.statics = got
        self.base_result = self.walk.evaluate(asp.base_engine(self.walk))
        self.base = asp.measure(self.walk, self.base_result.worlds)
        self.range = asp.ranges(self.base, self.walk.leg_length)
        self.groups = groups_of(self.walk.names)

    def run(self, gait):
        return self.walk.evaluate(asp.engine_knobs(self.walk, self.base, gait))

    def own(self, knob):
        v = asp.defaults(self.base)[knob]
        return 0.5 * (v["l"] + v["r"]) if isinstance(v, dict) else v


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
        b = Bench(name)
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
                m = asp.measure(b.walk, b.run({knob.name: target}).worlds)
                got = m[knob.key]
                got = 0.5 * (got["l"] + got["r"]) if isinstance(got, dict) else got
                change = got - own
                unit = 0.05 if knob.name == "speed" else READBACK_UNIT
                ok = abs(change - asked) <= max(READBACK_SHARE * abs(asked), unit)
                gate(ok, "readback %s %s: asked %+.2f %s, got %+.2f" % (name, knob.name, asked, knob.unit, change))


def gate_effect(names):
    for name in names:
        b = Bench(name)
        if not b.ok:
            continue
        for knob in asp.KNOBS:
            lo, hi = b.range[knob.name]
            best = (0.0, 0.0, "")
            for end in (lo, hi):
                change = group_change(b.base_result.worlds, b.run({knob.name: end}).worlds, b.groups)
                for g, (deg, cm) in change.items():
                    if deg / EFFECT_DEG + cm / EFFECT_CM > best[0] / EFFECT_DEG + best[1] / EFFECT_CM:
                        best = (deg, cm, g)
            gate(best[0] >= EFFECT_DEG or best[1] >= EFFECT_CM,
                 "effect %s %s over %.1f..%.1f %s: %.1f deg, %.1f cm (%s)" % (name, knob.name, lo, hi, knob.unit,
                                                                             best[0], best[1], best[2]))


def gate_redundancy(names):
    for name in names:
        b = Bench(name)
        if not b.ok:
            continue
        idx = np.concatenate(list(b.groups.values()))
        vecs, labels = [], []
        for knob in asp.KNOBS:
            lo, hi = b.range[knob.name]
            own = b.own(knob.name) if knob.kind == "measured" else knob.default
            step = 0.15 * (hi - lo)
            target = own + step if own + step <= hi else own - step
            v = signed_change(b.base_result.worlds, b.run({knob.name: target}).worlds, idx)
            if np.linalg.norm(v) > 1e-6:
                vecs.append(v / np.linalg.norm(v))
                labels.append(knob.name)
        sim = np.abs(np.array(vecs) @ np.array(vecs).T)
        pairs = [(sim[i, j], labels[i], labels[j]) for i in range(len(labels)) for j in range(i + 1, len(labels))
                 if sim[i, j] > SIMILAR]
        sv = np.linalg.svd(np.array(vecs), compute_uv=False)
        share = np.cumsum(sv ** 2) / np.sum(sv ** 2)
        gate(not pairs, "redundancy %s: %d knobs, %s; 90 %% of the change in %d directions, 99 %% in %d" % (
            name, len(labels), "; ".join("%s~%s %.2f" % (a, c, v) for v, a, c in sorted(pairs, reverse=True)) or
            "no pair past %.2f" % SIMILAR, np.searchsorted(share, 0.9) + 1, np.searchsorted(share, 0.99) + 1))


def gate_clicks(names):
    for name in names:
        b = Bench(name)
        if not b.ok:
            continue
        own, _ = knee_click(b.walk.clip.worlds, b.walk.names)
        limit = max(CLICK_ABS, CLICK_SHARE * own)
        configs = [("defaults", {})]
        for knob in ("step", "duty", "bob", "lift"):
            lo, hi = b.range[knob]
            configs += [(knob + " low", {knob: lo}), (knob + " high", {knob: hi})]
        configs += [("height +10", {"height": 10.0}), ("height -15", {"height": -15.0}), ("weight +1", {"weight": 1.0}),
                    ("speed high", {"speed": b.range["speed"][1]})]
        for label, gait in configs:
            click, straight = knee_click(b.run(gait).worlds, b.walk.names)
            gate(click <= limit, "clicks %s %s: %.1f deg/fr^2 (the clip's own %.1f, limit %.1f), straightest %.1f"
                 % (name, label, click, own, limit, straight))


GATES = {"parity": gate_parity, "speed": gate_speed, "identity": gate_identity, "readback": gate_readback,
         "effect": gate_effect, "redundancy": gate_redundancy, "clicks": gate_clicks}


def main(argv):
    which = argv[0] if argv else "all"
    names = argv[1:] or ["asd", "dw", "HavyRun", "cat:Walk"]
    for key, fn in GATES.items():
        if which in (key, "all"):
            fn(names)
    print("%d gates, %d failed" % (COUNT[0], len(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
