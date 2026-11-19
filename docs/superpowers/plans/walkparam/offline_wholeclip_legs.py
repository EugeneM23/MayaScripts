"""wholeclip.build offline on the inputs probe_wholeclip_legs.py pickled (2026-11-19): no scene, seconds a clip.

    mayapy offline_wholeclip_legs.py <args.pkl> [frames ...]

Prints the legs' and the pelvis's numbers for the clip as it went in (raw) and as build gives it back: the pelvis
height (min / max / range / frame of the min), each ankle's height against the raw's, the knee angle's worst second
difference (a kink), the ankles' spread across the hips (max / median), the contacts (ball or heel down and still,
as maya_startstop reads them) of raw against out, and the sink. With frames: a per-frame table there.
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim")))
if os.environ.get("WHOLECLIP_PLUGIN"):      # another build's maya_walk first (a control: the commit before)
    sys.path.insert(0, os.environ["WHOLECLIP_PLUGIN"])

from maya_startstop import model as ss  # noqa: E402
from maya_walk import wholeclip  # noqa: E402


def clip(d):
    return ss.Clip(d["names"], d["parents"], d["worlds"], d["fps"], d["name"])


def knee(w, ix, s):
    h, k, a = (w[ix["%s_%s" % (b, s)], :, 3, :3] for b in ("thigh", "calf", "foot"))
    u, v = h - k, a - k
    c = np.sum(u * v, 1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1))
    return 180.0 - np.degrees(np.arccos(np.clip(c, -1, 1)))


def spread(w, ix, signed=False):
    """|ankle_l - ankle_r| along the hips' line (thigh_r -> thigh_l), cm, per frame (signed: negative = crossed)."""
    hip = w[ix["thigh_l"], :, 3, :3] - w[ix["thigh_r"], :, 3, :3]
    hip[:, 1] = 0.0
    hip /= np.linalg.norm(hip, axis=1, keepdims=True)
    d = w[ix["foot_l"], :, 3, :3] - w[ix["foot_r"], :, 3, :3]
    v = np.sum(d * hip, 1)
    return v if signed else np.abs(v)


def knee_out(w, ix, s):
    """(F,) how far the knee stands off its hip-ankle line toward the outside of the body (cm, along the hips'
    line; negative: the knee falls in)."""
    hip_l, hip_r = w[ix["thigh_l"], :, 3, :3], w[ix["thigh_r"], :, 3, :3]
    side = hip_l - hip_r if s == "l" else hip_r - hip_l
    side[:, 1] = 0.0
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    h, k, a = (w[ix["%s_%s" % (b, s)], :, 3, :3] for b in ("thigh", "calf", "foot"))
    line = a - h
    t = np.sum((k - h) * line, 1) / np.sum(line * line, 1)
    off = k - (h + line * t[:, None])
    return np.sum(off * side, 1)


def hinge_drift(w, ix, s, bone):
    """(F,) degrees the knee's hinge axis (normal of hip-knee-ankle) stands off its median in `bone`'s own frame:
    a bone that keeps its roll keeps the hinge still in its frame; a roll flip shows as tens of degrees. Frames with
    the leg near straight (< 15 deg bend) are left out (no hinge to read)."""
    h, k, a = (w[ix["%s_%s" % (b, s)], :, 3, :3] for b in ("thigh", "calf", "foot"))
    n = np.cross(h - k, a - k)
    nn = np.linalg.norm(n, axis=1)
    R = w[ix["%s_%s" % (bone, s)], :, :3, :3]
    R = R / np.linalg.norm(R, axis=2, keepdims=True)
    loc = np.einsum("fi,fji->fj", n / np.maximum(nn, 1e-9)[:, None], R)
    bent = knee(w, ix, s) > 15.0
    if not bent.any():
        return np.zeros(len(loc))
    med = np.median(loc[bent], axis=0)
    med /= np.linalg.norm(med)
    ang = np.degrees(np.arccos(np.clip(loc @ med, -1, 1)))
    ang[~bent] = 0.0
    return ang


def report(raw, out, info, frames=()):
    ix = raw.index
    w0, w1 = raw.worlds, out
    p0, p1 = w0[ix["pelvis"], :, 3, 1], w1[ix["pelvis"], :, 3, 1]
    g = lambda p: "%.1f/%.1f rng %.1f @%d" % (p.min(), p.max(), np.ptp(p), int(np.argmin(p)))
    print("G pelvis raw %s | out %s | sink max %.1f" % (g(p0), g(p1), info["drop"]))
    for s in "lr":
        k0, k1 = knee(w0, ix, s), knee(w1, ix, s)
        a0, a1 = w0[ix["foot_" + s], :, 3, 1], w1[ix["foot_" + s], :, 3, 1]
        dk = lambda k: float(np.abs(np.diff(k, 2)).max())
        print("K %s kink raw %.1f out %.1f @%d | knee min %.1f->%.1f | ankle y off max %.1f @%d" % (
            s, dk(k0), dk(k1), int(np.argmax(np.abs(np.diff(k1, 2)))) + 1, k0.min(), k1.min(),
            float(np.abs(a1 - a0).max()), int(np.argmax(np.abs(a1 - a0)))))
    for s in "lr":
        for bone in ("thigh", "calf"):
            d0, d1 = hinge_drift(w0, ix, s, bone), hinge_drift(w1, ix, s, bone)
            step1 = np.abs(np.diff(d1)).max()
            print("R %s %s hinge drift in its frame raw max %.1f out max %.1f @%d (worst frame step %.1f)" % (
                s, bone, d0.max(), d1.max(), int(np.argmax(d1)), step1))
    for s in "lr":
        q0, q1 = knee_out(w0, ix, s), knee_out(w1, ix, s)
        print("E %s knee out min raw %.1f out %.1f @%d | median %.1f -> %.1f" % (
            s, q0.min(), q1.min(), int(np.argmin(q1)), np.median(q0), np.median(q1)))
    s0, s1 = spread(w0, ix), spread(w1, ix)
    print("E spread raw max %.1f med %.1f | out max %.1f med %.1f" % (s0.max(), np.median(s0), s1.max(),
                                                                       np.median(s1)))
    g0, g1 = spread(w0, ix, True), spread(w1, ix, True)
    d = g1 - g0
    print("E signed width raw min %.1f out min %.1f | out-raw min %.1f @%d max %.1f @%d" % (
        g0.min(), g1.min(), d.min(), int(np.argmin(d)), d.max(), int(np.argmax(d))))
    a0 = ss.Analysis(raw)
    a1 = ss.Analysis(ss.Clip(raw.names, raw.parents, out, raw.fps, "out"))
    for s in "lr":
        c0 = [tuple(map(int, c)) for c in a0.feet[s]["contacts"]]
        c1 = [tuple(map(int, c)) for c in a1.feet[s]["contacts"]]
        print("A %s contacts %s %s" % (s, "same" if c0 == c1 else "DIFFER", c0 if c0 == c1 else (c0, c1)))
    for f in frames:
        lens = [(np.linalg.norm(w1[ix["foot_" + s], f, 3, :3] - w1[ix["thigh_" + s], f, 3, :3]),
                 np.linalg.norm(w0[ix["foot_" + s], f, 3, :3] - w0[ix["thigh_" + s], f, 3, :3])) for s in "lr"]
        print("       reach out/raw L %.1f/%.1f R %.1f/%.1f" % (lens[0][0], lens[0][1], lens[1][0], lens[1][1]))
        print("  f%3d pelvis %.1f->%.1f knees %.0f/%.0f->%.0f/%.0f ankles y %.1f/%.1f->%.1f/%.1f spread %.0f->%.0f" % (
            f, p0[f], p1[f], knee(w0, ix, "l")[f], knee(w0, ix, "r")[f], knee(w1, ix, "l")[f], knee(w1, ix, "r")[f],
            w0[ix["foot_l"], f, 3, 1], w0[ix["foot_r"], f, 3, 1], w1[ix["foot_l"], f, 3, 1],
            w1[ix["foot_r"], f, 3, 1], s0[f], s1[f]))


def main():
    path = sys.argv[1]
    frames = [int(x) for x in sys.argv[2:]]
    a = pickle.load(open(path, "rb"))
    raw = clip(a["raw"])
    out, info = wholeclip.build(raw, clip(a["loop"]), clip(a["result"]), a["statics"], a["bones"], a["parts"],
                                a["share"], a["k"])
    print("==", os.path.basename(path), wholeclip.line(info))
    report(raw, out, info, frames)


if __name__ == "__main__":
    main()
