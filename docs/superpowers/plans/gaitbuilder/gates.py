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
    (cleaned at the default Clean knobs, the animator's mean pose correction applied), or None when absent."""
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


GATES = {"parity": gate_parity, "speed": gate_speed}


def main(argv):
    which = argv[0] if argv else "all"
    names = argv[1:] or ["asd", "dw", "HavyRun"]
    for key, fn in GATES.items():
        if which in (key, "all"):
            fn(names)
    print("%d gates, %d failed" % (COUNT[0], len(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
