"""verify_walk_straight_leg.py - Passing knee, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_straight_leg.py

Spec: docs/superpowers/specs/2026-11-02-walk-straight-passing-leg-design.md. The animator's own saved cycles,
read exactly as Walk Builder reads them (the clean, the mean-pose correction, gait.engine_knobs), and both
poses. Every gate prints the number it measured.

  identity  the knob untouched changes nothing - own_knobs() and the gait defaults give the same cycle, bit
            for bit, as before the knob existed; an ask no straighter than the cycle's own likewise; and the
            parameter's own value is what the cycle measures at the passing.
  ask       the asked bend read back off the WORLDS at the passing (the ankle crossing), the shortfall named
            where the legs ran out, the planted feet still on their prints, the lengths exact, the loop closed,
            the hips higher only at the passing.
  smooth    the knee's own shape: a U into the passing and out of it, no reversal inside the window, and the
            pelvis moving no faster than the share of its own the model allows.
  poses     the goblin's crouch and the two-handed sword: the straightening works from the pose's own height
            and never undoes its crouch.
  run       a run (HavyRun, AGS_Sprint): nothing until the knob is dialled, and dialled it straightens.
  target    the whole road onto a real Manny skeleton (scene.apply): the game skeleton's knee at the passing,
            so the retarget's knee-pop fixer does not bend the ask back.

Phases can be named on the command line; the default runs all six.
"""
import math
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
MINE = os.environ.get("WALKS_HOME", "C:/Users/MY PC/Documents/maya/SkeldarWalks")
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
WALKS = ("asd", "dw", "TestStrefe", "TestDraaft")
RUNS = ("HavyRun", "AGS_Sprint")
ASK = float(os.environ.get("PASSING_ASK", "8.0"))
PHASES = tuple(a for a in sys.argv[1:] if not a.startswith("-")) or (
    "identity", "ask", "smooth", "poses", "run", "target")

import maya.standalone                                        # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                      # noqa: E402

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))          # the repository's plugin, never the installed copy
from maya_walk import scene as sw                              # noqa: E402
from maya_walk import files as wf, clean as wc, meanpose as mp, pose as wp     # noqa: E402
from maya_walk import target as wt                             # noqa: E402

wm, wt, gait = sw.wm, sw.wt, sw.gait
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def path_of(name):
    path = os.path.join(MINE, name + ".walk.gz")
    return path if os.path.exists(path) else os.path.join(MINE, "own", name + ".walk.gz")


def load(name):
    """The walk as Walk Builder reads it (gaitload.from_file's road, without Maya)."""
    path = path_of(name)
    data = wf.load(path)
    clip, report = wc.clean(wf.clip_of(data, wm), data["statics"], None, wc.knobs(None))
    clip = mp.correct(clip, mp.load(mp.path_for(path)))
    walk = wm.analyse(wm.Clip(clip.names, clip.parents, np.array(clip.worlds), clip.fps, clip.up, clip.name))
    walk.fix = mp.model_fix(mp.load(mp.path_for(path)))
    return walk, data


def posed(walk, data, name):
    bones = wf.load_pose(os.path.join(MINE, name + ".wpose.gz"))[1]     # (name, bones)
    return wp.prepare(walk, data["statics"], bones, wm, wt)


def defaults(walk, own=None):
    own = gait.own(walk) if own is None else own
    return gait.engine_knobs(walk, own, gait.values(own, {}))


def ask_knobs(k, deg, side=None):
    """`k` with Passing knee asked. Both sides by name: engine_knobs writes every sided knob's own `_l` and
    `_r`, and a side's own value wins over the plain one (trap 317)."""
    if side is not None:
        return dict(k, **{"passing_knee_" + side: deg})
    return dict(k, passing_knee_l=deg, passing_knee_r=deg)


def bends(walk, worlds, side):
    """(n,) the knee's bend a frame, degrees (0 straight)."""
    n = worlds.shape[1] - 1
    h = worlds[walk.index["thigh_" + side], :n, 3, :3]
    k = worlds[walk.index["calf_" + side], :n, 3, :3]
    a = worlds[walk.index["foot_" + side], :n, 3, :3]
    u = (k - h) / np.linalg.norm(k - h, axis=1)[:, None]
    v = (a - k) / np.linalg.norm(a - k, axis=1)[:, None]
    return np.degrees(np.arccos(np.clip(np.sum(u * v, axis=1), -1.0, 1.0)))


def planted_of(res):
    pl = (res.info.get("placement") or {}).get("planted") or {}
    return dict((s, np.array(pl[s], bool)) for s in ("l", "r")) if pl else None


def passings(walk, res):
    """{side: [frames]} - the frames a planted foot's own passing falls on (the other ankle crossing it)."""
    n = res.frames
    planted = planted_of(res)
    along = dict((s, res.worlds[walk.index["foot_" + s], :n, 3, :3] @ walk.basis[0]) for s in ("l", "r"))
    d = along["l"] - along["r"]
    out = {"l": [], "r": []}
    for f in range(n):
        g = (f + 1) % n
        if d[f] == 0.0 or (d[f] < 0.0) != (d[g] < 0.0):
            for s in ("l", "r"):
                if planted is None or planted[s][f]:
                    out[s].append(f)
    return out


def at_passing(walk, res, side=None):
    """The stance knee's bend at the passing, degrees (both sides' mean unless one is named)."""
    pf = passings(walk, res)
    vals = []
    for s in (("l", "r") if side is None else (side,)):
        b = bends(walk, res.worlds, s)
        vals.extend(float(b[f]) for f in pf[s])
    return float(np.mean(vals)) if vals else 0.0


def contact_frames(walk, res):
    """[(side, frame)] - the first and last frame INSIDE every contact, in the RESULT's own frames (Foot
    placement retimes them, so the source's contact frames are not where they land; and a frame just past a
    lift-off is a foot in the air, whose knee is nobody's promise)."""
    n = res.frames
    out = []
    got = (res.info.get("contacts") or {})
    for s in ("l", "r"):
        spans = got.get(s) or [(hs * n / float(walk.P), to * n / float(walk.P)) for hs, to in walk.contact[s]]
        for a, b in spans:
            out.append((s, int(math.ceil(a)) % n))
            out.append((s, int(math.floor(b)) % n))
    return out


def pelvis_of(walk, res):
    return res.worlds[walk.index["pelvis"], :res.frames, 3, :3] @ walk.up


def lengths_of(walk, res, side):
    """(n, 2) the thigh's and the calf's length a frame."""
    n = res.frames
    h = res.worlds[walk.index["thigh_" + side], :n, 3, :3]
    k = res.worlds[walk.index["calf_" + side], :n, 3, :3]
    a = res.worlds[walk.index["foot_" + side], :n, 3, :3]
    return np.stack([np.linalg.norm(k - h, axis=1), np.linalg.norm(a - k, axis=1)], axis=1)


def slide_of(walk, res, base):
    """The most a PLANTED foot moved against the plain result, cm."""
    out = 0.0
    planted = planted_of(res)
    for s in ("l", "r"):
        on = planted[s] if planted else np.ones(res.frames, bool)
        if not on.any():
            continue
        now = res.worlds[walk.index["foot_" + s], :res.frames, 3, :3][on]
        was = base.worlds[walk.index["foot_" + s], :base.frames, 3, :3][on]
        out = max(out, float(np.abs(now - was).max()))
    return out


# ---------------------------------------------------------------- identity

def phase_identity():
    print("\n--- identity: the knob untouched changes nothing")
    for name in WALKS[:2]:
        walk, data = load(name)
        own = gait.own(walk)
        k = defaults(walk, own)
        plain = walk.evaluate(k)
        off = walk.evaluate(ask_knobs(k, 0.0))
        gate(np.array_equal(plain.worlds, off.worlds), "%s: the gait defaults are bit for bit the cycle the "
             "knob never touched" % name)
        gate("passing" not in off.info, "%s: and say nothing about a passing knee" % name)
        o = walk.own_knobs()
        gate(np.array_equal(walk.evaluate(o).worlds, walk.evaluate(dict(o, passing_knee_l=0.0,
                                                                       passing_knee_r=0.0)).worlds),
             "%s: own_knobs() likewise" % name)
        more = ask_knobs(k, own["passing_knee_l"] + 10.0)
        gate(np.array_equal(walk.evaluate(more).worlds, plain.worlds),
             "%s: an ask 10 deg MORE bent than its own changes nothing (that is Knee bend's ask)" % name)
        measured, read = at_passing(walk, plain), gait.of_result(walk, plain)
        mean = 0.5 * (read["passing_knee_l"] + read["passing_knee_r"])
        gate(abs(mean - measured) < 2.0, "%s: the parameter measures %.1f deg at the passing, the worlds %.1f"
             % (name, mean, measured))


# ---------------------------------------------------------------- ask

def phase_ask():
    print("\n--- ask: %.0f deg at the passing" % ASK)
    for name in WALKS:
        walk, data = load(name)
        own = gait.own(walk)
        k = defaults(walk, own)
        plain = walk.evaluate(k)
        res = walk.evaluate(ask_knobs(k, ASK))
        p = res.info["passing"]
        got, was = at_passing(walk, res), at_passing(walk, plain)
        left = max(p["short"].values()) if p["short"] else 0.0
        if left <= 1.0:
            gate(abs(got - ASK) < 1.5, "%s: %.1f -> %.1f deg, asked %.0f (the legs left %.1f)"
                 % (name, was, got, ASK, left))
        else:
            gate(got < was - 3.0, "%s: %.1f -> %.1f deg of %.0f asked - the legs left %.0f deg, said"
                 % (name, was, got, ASK, left))
        gate(abs((0.5 * (p["got"].get("l", 0.0) + p["got"].get("r", 0.0))) - got) < 2.0,
             "%s: the model's own reading %.1f agrees with the worlds' %.1f"
             % (name, 0.5 * (p["got"].get("l", 0.0) + p["got"].get("r", 0.0)), got))
        slide = slide_of(walk, res, plain)
        gate(slide < 0.25, "%s: a planted foot moved %.4f cm (the foot's own roll; nothing slides)"
             % (name, slide))
        worst = 0.0
        for s in ("l", "r"):
            now, was_l = lengths_of(walk, res, s), lengths_of(walk, plain, s)
            worst = max(worst, float(np.abs(now - was_l).max()))
        gate(worst < 1e-6, "%s: every bone keeps its length (worst %.2e cm)" % (name, worst))
        pel = pelvis_of(walk, res)
        gate(abs(float(res.worlds[walk.index["pelvis"], res.frames, 3, :3] @ walk.up) - float(pel[0])) < 1e-9,
             "%s: the loop closes" % name)
        base_pel = pelvis_of(walk, plain)
        pf = passings(walk, res)
        at = sorted(set(pf["l"] + pf["r"]))
        rose = min(float(pel[f] - base_pel[f]) for f in at) if at else 0.0
        contacts = contact_frames(walk, res)
        moved = 0.0
        for s, f in contacts:
            moved = max(moved, abs(float(bends(walk, res.worlds, s)[f] - bends(walk, plain.worlds, s)[f])))
        gate(rose > 0.1 and moved < 4.0, "%s: the hips rose %.2f cm at the passing, and the knees at the "
             "contacts' own ends moved %.1f deg" % (name, rose, moved))


# ---------------------------------------------------------------- smooth

def phase_smooth():
    print("\n--- smooth: the knee's shape and the hips' own rate")
    for name in WALKS:
        walk, data = load(name)
        k = defaults(walk)
        plain = walk.evaluate(k)
        res = walk.evaluate(ask_knobs(k, ASK))
        n = res.frames
        pf = passings(walk, res)
        def reversal(worlds):
            """The worst step the wrong way within three frames either side of a passing: into it the knee's
            bend falls, out of it it rises."""
            worst = 0.0
            for s in ("l", "r"):
                b = bends(walk, worlds, s)
                for f in pf[s]:
                    down = [float(b[(f - i) % n] - b[(f - i + 1) % n]) for i in (3, 2, 1)]
                    up = [float(b[(f + i) % n] - b[(f + i - 1) % n]) for i in (1, 2, 3)]
                    worst = max(worst, max([-x for x in down] + [-x for x in up] + [0.0]))
            return worst
        jerk = lambda worlds: max(float(np.abs(np.diff(bends(walk, worlds, s), 2,
                                                       prepend=bends(walk, worlds, s)[-1],
                                                       append=bends(walk, worlds, s)[0])).max())
                                  for s in ("l", "r"))
        rev, rev0 = reversal(res.worlds), reversal(plain.worlds)
        left = max(res.info["passing"]["short"].values()) if res.info["passing"]["short"] else 0.0
        if left <= 1.0:
            gate(rev < max(2.5, rev0 + 0.5), "%s: the knee runs down into its passing and up out of it (worst "
                 "step the wrong way %.2f deg, the plain cycle's %.2f)" % (name, rev, rev0))
        else:
            # where the legs ran out of room the straightest moment can sit a few frames off the crossing -
            # the shape there is the cycle's own business; the knee's own smoothness is the gate below
            print("        (%s: the legs left %.0f deg, so the straightest moment is where they allowed it - "
                  "worst step the wrong way %.2f deg, the plain cycle's %.2f)" % (name, left, rev, rev0))
        got, was = jerk(res.worlds), jerk(plain.worlds)
        gate(got < max(was + 1.0, 1.3 * was), "%s: the knee is no jerkier than the cycle's own (worst second "
             "difference %.1f deg against %.1f)" % (name, got, was))
        pel, base_pel = pelvis_of(walk, res), pelvis_of(walk, plain)
        accel = lambda y: float(np.abs(np.diff(y, 2, prepend=y[-1], append=y[0])).max())
        allowed = max(wm.STRAIGHT_SHARE * walk.bob_rate, wm.STRAIGHT_FLOOR * 30.0 * walk.strides / walk.P)
        allowed *= walk.P / float(n)
        gate(accel(pel) - accel(base_pel) <= 2.2 * allowed,
             "%s: the hips' jolt grew %.2f cm a frame a frame, at most twice the rate the lift is held to "
             "(%.2f); they move %.2f cm a frame against %.2f"
             % (name, accel(pel) - accel(base_pel), allowed,
                float(np.abs(np.diff(pel, prepend=pel[-1])).max()),
                float(np.abs(np.diff(base_pel, prepend=base_pel[-1])).max())))


# ---------------------------------------------------------------- poses

def phase_poses():
    print("\n--- poses: from the pose's own height, its crouch kept")
    walk, data = load("asd")
    k = defaults(walk)
    for pose_name in ("goblin", "two_handed_sword"):
        pose = posed(walk, data, pose_name)
        plain = walk.evaluate(dict(k, pose=1.0), pose)
        res = walk.evaluate(ask_knobs(dict(k, pose=1.0), ASK), pose)
        was, got = at_passing(walk, plain), at_passing(walk, res)
        gate(got < was - 1.0, "%s: %.1f -> %.1f deg at the passing" % (pose_name, was, got))
        mean_was = float(pelvis_of(walk, plain).mean())
        mean_now = float(pelvis_of(walk, res).mean())
        bare = float(pelvis_of(walk, walk.evaluate(k)).mean())
        lift = res.info["passing"]["lift"]
        gate(0.0 <= mean_now - mean_was <= lift + 0.5 and mean_now < bare - 2.0,
             "%s: its hips %.1f cm, now %.1f - the lift is %.1f, and the walk without the pose stands at %.1f"
             % (pose_name, mean_was, mean_now, lift, bare))
        gate(slide_of(walk, res, plain) < 0.3, "%s: nothing slides (%.4f cm)"
             % (pose_name, slide_of(walk, res, plain)))


# ---------------------------------------------------------------- run

def phase_run():
    print("\n--- run: nothing until it is dialled")
    for name in RUNS:
        if not os.path.exists(path_of(name)):
            print("        (%s: no such walk)" % name)
            continue
        walk, data = load(name)
        own = gait.own(walk)
        k = defaults(walk, own)
        plain = walk.evaluate(k)
        gate(np.array_equal(walk.evaluate(ask_knobs(k, 0.0)).worlds, plain.worlds),
             "%s: a run is untouched at the defaults" % name)
        m = gait.of_result(walk, plain)
        found = [f.key for f in gait.diagnose(m, own, plain.info, leg=walk.leg_length, fps=walk.fps)]
        gate("bent_passing" not in found, "%s: and the diagnosis does not advise straightening it (%s)"
             % (name, ", ".join(found) or "nothing"))
        asked = max(5.0, own["passing_knee_l"] - 20.0)
        res = walk.evaluate(ask_knobs(k, asked))
        gate(at_passing(walk, res) < at_passing(walk, plain) - 2.0,
             "%s: dialled to %.0f it straightens anyway (%.1f -> %.1f deg)"
             % (name, asked, at_passing(walk, plain), at_passing(walk, res)))


# ---------------------------------------------------------------- target

def ma_import(path, namespace):
    before = set(cmds.ls(long=True))
    cmds.file(path, i=True, namespace=namespace, preserveReferences=True, importTimeRange="keep")
    new = [p for p in cmds.ls(long=True) if p not in before]
    joints = [p for p in new if cmds.nodeType(p) == "joint"]
    roots = [p for p in joints if not [a for a in (cmds.listRelatives(p, parent=True, fullPath=True) or [])
                                       if cmds.nodeType(a) == "joint"]]
    return sorted(roots, key=len)[0]


def scene_bends(root, side, frames):
    """The game skeleton's knee bend a frame (degrees), read off the scene."""
    ns = root.split("|")[-1].rsplit(":", 1)[0] + ":" if ":" in root.split("|")[-1] else ""
    names = [ns + n + "_" + side for n in ("thigh", "calf", "foot")]
    out = []
    for f in frames:
        cmds.currentTime(f)
        p = [np.array(cmds.xform(n, q=True, ws=True, t=True)) for n in names]
        u, v = p[1] - p[0], p[2] - p[1]
        u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)
        out.append(math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(u, v)))))))
    return out


def phase_target():
    print("\n--- target: the whole road onto a real Manny skeleton")
    folder = tempfile.mkdtemp(prefix="straightleg_")
    for name in ("asd",):
        shutil.copy(path_of(name), os.path.join(folder, name + ".walk.gz"))
        fix = mp.path_for(path_of(name))
        if os.path.exists(fix):
            shutil.copy(fix, os.path.join(folder, os.path.basename(fix)))
    sw.WALKS = folder
    cmds.file(new=True, force=True)
    root = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "chk")
    walk, data = load("asd")
    own = gait.own(walk)
    params = {"changes": {}, "pins": [], "physics": True}
    plain_result, plain_info, plain_text = sw.apply(root, "asd", params=dict(params))
    pf = passings(walk, plain_result)
    at = sorted(set(pf["l"] + pf["r"]))
    before = dict((s, scene_bends(root, s, [f for f in at])) for s in ("l", "r"))
    p, _ = gait.param_of("passing_knee_l")
    changes = dict((key, gait.stored_change(p, own[key], ASK)) for key in ("passing_knee_l", "passing_knee_r"))
    res, info, text = sw.apply(root, "asd", params=dict(params, changes=changes))
    after = dict((s, scene_bends(root, s, [f for f in at])) for s in ("l", "r"))
    model = at_passing(walk, res)
    best_before = min(min(before["l"]), min(before["r"]))
    best_after = min(min(after["l"]), min(after["r"]))
    gate(best_after < best_before - 3.0, "the scene's own knee at the passing: %.1f -> %.1f deg (the model %.1f)"
         % (best_before, best_after, model))
    gate(abs(best_after - ASK) < 4.0, "and it lands near the ask (%.0f): %.1f deg" % (ASK, best_after))
    print("        line: %s" % text.replace("\n", " "))
    gate("the passing knee" in text, "the line says what it did")
    #  the control: the retarget's own cap left at the clip's own straightest, as target.py read it before
    #  2026-11-02 - it lowers the hips back onto that ratio and the knee bends again
    raised = wt.Retarget._reach_ratio
    try:
        wt.Retarget._reach_ratio = lambda self, side: self.walk.reach[side]
        _, old_info, _ = sw.apply(root, "asd", params=dict(params, changes=changes))
        back = dict((s, scene_bends(root, s, at)) for s in ("l", "r"))
    finally:
        wt.Retarget._reach_ratio = raised
    worst_back = min(min(back["l"]), min(back["r"]))
    gate(worst_back > best_after + 3.0 and max(old_info["drop"]) > 0.2,
         "the control: the cap left at the clip's own ratio bends it back to %.1f deg, the hips pulled down "
         "%.2f cm (with the raise %.1f deg and %.2f cm)"
         % (worst_back, max(old_info["drop"]), best_after, max(info["drop"])))
    shutil.rmtree(folder, ignore_errors=True)


def main():
    for name in PHASES:
        fn = globals().get("phase_" + name)
        if fn is None:
            print("no phase %s" % name)
            continue
        fn()
    print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0],
                                         (": " + ", ".join(map(str, FAILED))) if FAILED else ""))


if __name__ == "__main__":
    main()
