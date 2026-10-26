"""The helpers' quality under stress, both tools: knee clicks (the knee angle's second difference), the
straightest knee, a planted foot's slide, the pelvis's jerk; and whether Balance / Foot placement undo a knob.

mayapy quality.py  -> quality.json + a printed table
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan  # noqa: E402


def leg_metrics(names, worlds, fps):
    """worlds (J, F+1, 4, 4) closed cycle"""
    w = worlds[:, :-1]
    F = w.shape[1]
    out = {}
    ix = dict((n.split("|")[-1].split(":")[-1], i) for i, n in enumerate(names))
    for s in ("l", "r"):
        hip, knee, ank, ball = (w[ix[n + "_" + s], :, 3, :3] for n in ("thigh", "calf", "foot", "ball"))
        a, b = knee - hip, ank - knee
        cos = np.sum(a * b, 1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
        bend = np.degrees(np.arccos(np.clip(cos, -1, 1)))           # 0 straight
        acc = np.abs(np.roll(bend, -1) - 2 * bend + np.roll(bend, 1))
        reach = np.linalg.norm(ank - hip, axis=1) / (np.linalg.norm(a, axis=1) + np.linalg.norm(b, axis=1))
        # a planted foot: the ball within 2 cm of its lowest - its slide a frame along the ground
        h = ball[:, 1]
        down = h < h.min() + 2.0
        step = np.linalg.norm(np.roll(ball, -1, 0) - ball, axis=1)
        step[:, ] = step
        both = down & np.roll(down, -1)
        travel = np.linalg.norm(worlds[ix["root"], -1, 3, [0, 2]] - worlds[ix["root"], 0, 3, [0, 2]]) / F
        slide = step[both].max() if both.any() else 0.0
        out[s] = {"bend_min": float(bend.min()), "bend_acc_max": float(acc.max()), "reach_max": float(reach.max()),
                  "slide_max": float(slide), "travel_frame": float(travel)}
    pel = w[ix["pelvis"], :, 3, 1]
    jerk = np.abs(np.roll(pel, -2) - 3 * np.roll(pel, -1) + 3 * pel - np.roll(pel, 1))
    out["pelvis_jerk"] = float(jerk.max())
    return out


def wb_eval(walk_name, pose_name=None):
    from maya_walk import model as wm, files as wf, clean as wc, pose as wp, target as wt, meanpose as mp
    path = os.path.join(scan.MINE, walk_name + ".walk.gz")
    data = wf.load(path)
    clip, report = wc.clean(wf.clip_of(data, wm), data["statics"], None, wc.knobs({}))
    fix = mp.load(mp.path_for(path))
    walk = wm.analyse(mp.correct(clip, fix))
    walk.fix = mp.model_fix(fix)
    pose = None
    if pose_name:
        bones = wf.load_pose(os.path.join(scan.MINE, pose_name + ".wpose.gz"))[1]
        pose = wp.prepare(walk, data["statics"], bones, wm, wt)

    def ev(given):
        g = dict(given)
        if pose is not None:
            g.setdefault("pose", 1.0)
        r = walk.evaluate(g, pose)
        return list(walk.names), np.asarray(r.worlds), walk.fps
    return ev, walk


def main():
    rows = []
    for walk_name, pose_name in (("asd", None), ("asd", "goblin"), ("HavyRun", None), ("dw", None)):
        ev, walk = wb_eval(walk_name, pose_name)
        tag = walk_name + ("+" + pose_name if pose_name else "")
        configs = [("defaults", {}), ("own", walk.own_knobs()), ("stride 1.4", {"stride": 1.4}),
                   ("stride 0.6", {"stride": 0.6}), ("pelvis +10", {"pelvis_height": 10.0}),
                   ("pelvis -15", {"pelvis_height": -15.0}), ("ground 1.3", {"ground_time": 1.3}),
                   ("lift 2", {"lift": 2.0}), ("no placement", {"foot_placement": 0.0})]
        for label, given in configs:
            names, worlds, fps = ev(given)
            m = leg_metrics(names, worlds, fps)
            rows.append(("WB " + tag, label, m))
            print("WB %-14s %-14s" % (tag, label), fmt(m))
            sys.stdout.flush()
        # does Balance undo the pelvis knobs?
        for knob, val in (("sway", 2.5), ("surge", 2.5), ("pelvis_forward", 10.0), ("bob", 2.5)):
            effects = []
            for bal in (1.0, 0.0):
                names, base, _ = ev({"balance": bal})
                names, other, _ = ev({"balance": bal, knob: val})
                i = names.index("pelvis")
                d = np.linalg.norm(scan.line_of(other[:, :, 3, :3], names.index("root"))[i]
                                   - scan.line_of(base[:, :, 3, :3], names.index("root"))[i], axis=1)
                effects.append(float(np.sqrt(np.mean(d ** 2))))
            print("WB %-14s balance on/off: %s=%s moves the pelvis %.2f / %.2f cm rms" % (tag, knob, val, effects[0], effects[1]))
            rows.append(("WB " + tag, "balance " + knob, {"on": effects[0], "off": effects[1]}))
    import importlib.util
    spec = importlib.util.spec_from_file_location("catmodel", os.path.join(scan.REPO, "docs/superpowers/plans/catwalk/catmodel.py"))
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    with open(os.path.join(scan.REPO, "SkeldarAnim/assets/manny_skeleton_template.json")) as handle:
        joints = json.load(handle)["joints"]
    skel = cm.Skeleton.from_template(dict((j["name"], {"parent": j.get("parent"), "world_matrix": j["world_matrix"]})
                                          for j in joints))
    for preset in ("Walk", "Run"):
        base = cm.preset(preset, 30)
        for label, given in (("defaults", {}), ("stride 1.4", {"stride": base["stride"] * 1.4}),
                             ("stride 0.6", {"stride": base["stride"] * 0.6}), ("crouch -0.06", {"crouch": -0.06}),
                             ("crouch 0.2", {"crouch": 0.2}), ("duty +0.15", {"duty": base["duty"] + 0.15}),
                             ("lift x2", {"lift": base["lift"] * 2}), ("knee drive", {"knee_drive": 1.0})):
            g = dict(base)
            g.update(given)
            c = cm.generate(skel, g, 30)
            leaves = list(c.frames[0].keys())
            worlds = np.array([[c.frames[f][leaf] for f in range(len(c.frames))] for leaf in leaves])
            m = leg_metrics(leaves, worlds, 30)
            rows.append(("CAT " + preset, label, m))
            print("CAT %-12s %-14s" % (preset, label), fmt(m))
    with open(os.path.join(HERE, "quality.json"), "w") as handle:
        json.dump(rows, handle)


def fmt(m):
    return "knee min %5.1f/%5.1f  knee acc %5.1f/%5.1f  reach %.3f/%.3f  slide %.2f/%.2f (travel %.1f)  pelvis jerk %.2f" % (
        m["l"]["bend_min"], m["r"]["bend_min"], m["l"]["bend_acc_max"], m["r"]["bend_acc_max"],
        m["l"]["reach_max"], m["r"]["reach_max"], m["l"]["slide_max"], m["r"]["slide_max"], m["l"]["travel_frame"],
        m["pelvis_jerk"])


if __name__ == "__main__":
    main()
