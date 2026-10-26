"""knee clicks only: the knee angle's second difference on frames where the knee is near straight (< 25 deg),
and a planted foot's slide (ball under 0.5 cm over its lowest on both frames), no wrap across the seam"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality, scan
def metrics(names, worlds):
    ix = dict((n.split("|")[-1].split(":")[-1], i) for i, n in enumerate(names))
    w = worlds
    res = []
    for s in ("l", "r"):
        hip, knee, ank, ball = (w[ix[n + "_" + s], :, 3, :3] for n in ("thigh", "calf", "foot", "ball"))
        a, b = knee - hip, ank - knee
        bend = np.degrees(np.arccos(np.clip(np.sum(a*b,1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)),-1,1)))
        F = len(bend) - 1     # closed: frame F = frame 0
        bb = bend[:F]
        acc = np.abs(np.roll(bb, -1) - 2 * bb + np.roll(bb, 1))
        near = bb < 25.0
        click = acc[near].max() if near.any() else 0.0
        h = ball[:, 1]; low = h[:F].min()
        down = h < low + 0.5
        st = [np.linalg.norm((ball[f+1] - ball[f])[[0, 2]]) for f in range(F) if down[f] and down[f+1]]
        res.append((bb.min(), click, max(st) if st else 0.0))
    return res
def show(tag, label, names, worlds):
    m = metrics(names, worlds)
    print("%-14s %-15s straightest %5.1f/%5.1f  click %5.1f/%5.1f  slide %5.2f/%5.2f" % (tag, label, m[0][0], m[1][0], m[0][1], m[1][1], m[0][2], m[1][2]))
for walk_name in ("asd", "HavyRun"):
    ev, walk = quality.wb_eval(walk_name)
    for label, g in (("defaults", {}), ("own", walk.own_knobs()), ("stride 1.4", {"stride": 1.4}), ("pelvis +10", {"pelvis_height": 10.0}), ("ground 1.3", {"ground_time": 1.3}), ("no placement", {"foot_placement": 0.0})):
        names, worlds, _ = ev(g)
        show("WB " + walk_name, label, names, worlds)
import importlib.util
spec = importlib.util.spec_from_file_location("catmodel", os.path.join(scan.REPO, "docs/superpowers/plans/catwalk/catmodel.py"))
cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)
joints = json.load(open(os.path.join(scan.REPO, "SkeldarAnim/assets/manny_skeleton_template.json")))["joints"]
skel = cm.Skeleton.from_template(dict((j["name"], {"parent": j.get("parent"), "world_matrix": j["world_matrix"]}) for j in joints))
for preset in ("Walk", "Run"):
    base = cm.preset(preset, 30)
    for label, g in (("defaults", {}), ("stride x1.4", {"stride": base["stride"] * 1.4}), ("crouch -0.06", {"crouch": -0.06}), ("duty +0.15", {"duty": base["duty"] + 0.15}), ("knee drive", {"knee_drive": 1.0})):
        k = dict(base); k.update(g)
        c = cm.generate(skel, k, 30)
        leaves = list(c.frames[0].keys())
        worlds = np.array([[c.frames[f][leaf] for f in range(len(c.frames))] for leaf in leaves])
        show("CAT " + preset, label, leaves, worlds)
