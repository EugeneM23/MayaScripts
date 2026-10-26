"""Knob sensitivity of Walk Builder (maya_walk.model) and the CAT script (catwalk/catmodel), headless.

mayapy scan.py wb <walk name> [pose name]   -> wb_<walk>[_<pose>].json
mayapy scan.py cat <preset>                 -> cat_<preset>.json

For each knob: the result at its low and high end (and a small step for the signed sensitivity) against the
defaults' result, per body group: rms of the joints' world-turn change (deg) and of their place change against
the travel line (cm), over every frame of the cycle (by phase when the frame count changes).
"""
import importlib.util
import json
import math
import os
import sys
import time

import numpy as np

REPO = "C:/!!!Work/MayaScripts"
HERE = os.path.dirname(os.path.abspath(__file__))
MINE = "C:/Users/MY PC/Documents/maya/SkeldarWalks"
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

GROUPS = (("pelvis", ("pelvis",)), ("spine", ("spine_", "neck_")), ("head", ("head",)),
          ("arms", ("clavicle_", "upperarm_", "lowerarm_")), ("hands", ("hand_",)),
          ("legs", ("thigh_", "calf_")), ("feet", ("foot_", "ball_")),
          ("fingers", ("thumb_", "index_", "middle_", "ring_", "pinky_")))
SKIP = ("twist", "ik_", "weapon", "camera", "interaction", "center_of_mass", "metacarpal")


def group_of(name):
    leaf = name.split("|")[-1].split(":")[-1].lower()
    if any(s in leaf for s in SKIP):
        return None
    for g, prefixes in GROUPS:
        if any(leaf == p or leaf.startswith(p) for p in prefixes):
            return g
    return None


def line_of(pos, root):
    """positions minus the straight line from the root's first to its last frame. pos (J, F, 3)."""
    F = pos.shape[1]
    a, b = pos[root, 0], pos[root, F - 1]
    t = np.linspace(0.0, 1.0, F)[:, None]
    return pos - (a[None] + (b - a)[None] * t)[None]


def log_rot(r):
    """rotation vectors of (..., 3, 3) row-vector rotations"""
    c = np.clip((np.trace(r, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0)
    ang = np.arccos(c)
    w = np.stack([r[..., 1, 2] - r[..., 2, 1], r[..., 2, 0] - r[..., 0, 2], r[..., 0, 1] - r[..., 1, 0]], -1)
    s = np.sin(ang)
    k = np.where(s > 1e-6, ang / (2.0 * np.maximum(s, 1e-12)), 0.5)
    return w * k[..., None]


class Cyc(object):
    """a cycle as arrays: rot (J, F, 3, 3), pos (J, F, 3) against the travel line, names"""

    def __init__(self, names, worlds):   # worlds (J, F+1, 4, 4): the closing frame dropped
        w = worlds[:, :-1]
        self.names = names
        self.rot = w[:, :, :3, :3].copy()
        root = names.index("root") if "root" in names else 0
        self.pos = line_of(worlds[:, :, 3, :3], root)[:, :-1]
        self.F = w.shape[1]

    def at(self, F):
        """resampled to F frames by phase (nearest)"""
        if F == self.F:
            return self
        idx = np.round(np.arange(F) * self.F / float(F)).astype(int) % self.F
        out = Cyc.__new__(Cyc)
        out.names, out.rot, out.pos, out.F = self.names, self.rot[:, idx], self.pos[:, idx], F
        return out


def diff(base, other, groups):
    o = other.at(base.F)
    rel = np.einsum("jfab,jfcb->jfac", o.rot, base.rot)          # o . base^T
    ang = np.degrees(np.linalg.norm(log_rot(rel), axis=-1))     # (J, F)
    d = np.linalg.norm(o.pos - base.pos, axis=-1)              # (J, F)
    out = {}
    for g, idx in groups.items():
        out[g] = (float(np.sqrt(np.mean(ang[idx] ** 2))), float(np.sqrt(np.mean(d[idx] ** 2))),
                  float(ang[idx].max()), float(d[idx].max()))
    return out


def signed(base, other, idx_all):
    """the signed change vector (deg for turns, cm for places) over the body joints"""
    o = other.at(base.F)
    rel = np.einsum("jfab,jfcb->jfac", o.rot[idx_all], base.rot[idx_all])
    w = np.degrees(log_rot(rel)).ravel()
    p = (o.pos[idx_all] - base.pos[idx_all]).ravel()
    return np.concatenate([w, p])


def scan(evaluate, names, knob_table, defaults, base_given, label):
    groups = {}
    for i, n in enumerate(names):
        g = group_of(n)
        if g:
            groups.setdefault(g, []).append(i)
    groups = dict((g, np.array(v)) for g, v in groups.items())
    idx_all = np.concatenate(list(groups.values()))
    t0 = time.time()
    base = evaluate(dict(base_given))
    t_eval = time.time() - t0
    rows = []
    for name, default, lo, hi in knob_table:
        cur = base_given.get(name, default)
        row = {"knob": name, "default": cur, "low": lo, "high": hi, "ends": {}}
        for tag, value in (("low", lo), ("high", hi)):
            if abs(value - cur) < 1e-9:
                continue
            g = dict(base_given)
            g[name] = value
            try:
                row["ends"][tag] = {"value": value, "groups": diff(base, evaluate(g), groups)}
            except Exception as error:      # noqa
                row["ends"][tag] = {"value": value, "error": repr(error)}
        step = 0.15 * (hi - lo)
        value = cur + step if cur + step <= hi else cur - step
        g = dict(base_given)
        g[name] = value
        try:
            other = evaluate(g)
            vec = signed(base, other, idx_all) / (value - cur) * (hi - lo)   # per whole range, linearised
            row["vec"] = vec
        except Exception as error:      # noqa
            row["vec_error"] = repr(error)
        rows.append(row)
        print("%-22s %s" % (name, " ".join("%s %s" % (t, max((v[0] for v in e["groups"].values()), default=0)
                                                       if "groups" in e else e.get("error"))
                                          for t, e in row["ends"].items())))
        sys.stdout.flush()
    names_k = [r["knob"] for r in rows if "vec" in r]
    vecs = np.array([r["vec"] for r in rows if "vec" in r])
    norms = np.linalg.norm(vecs, axis=1)
    sim = (vecs @ vecs.T) / np.maximum(norms[:, None] * norms[None], 1e-9)
    sv = np.linalg.svd(vecs, compute_uv=False) if len(vecs) else np.array([])
    for r in rows:
        r.pop("vec", None)
    out = {"label": label, "eval_s": t_eval, "frames": base.F, "rows": rows, "sim_names": names_k,
           "sim": sim.tolist(), "norms": norms.tolist(), "singular": sv.tolist()}
    with open(os.path.join(HERE, label + ".json"), "w") as handle:
        json.dump(out, handle)
    print("wrote", label, "eval %.2fs" % t_eval)


def run_wb(walk_name, pose_name=None):
    from maya_walk import model as wm, files as wf, clean as wc, pose as wp, target as wt, meanpose as mp
    path = os.path.join(MINE, walk_name + ".walk.gz")
    data = wf.load(path)
    clip, report = wc.clean(wf.clip_of(data, wm), data["statics"], None, wc.knobs({}))
    fix = mp.load(mp.path_for(path))
    walk = wm.analyse(mp.correct(clip, fix))
    walk.fix = mp.model_fix(fix)
    pose = None
    base_given = {}
    if pose_name:
        bones = wf.load_pose(os.path.join(MINE, pose_name + ".wpose.gz"))[1]
        pose = wp.prepare(walk, data["statics"], bones, wm, wt)
        base_given["pose"] = 1.0
    names = list(walk.names)

    def evaluate(given):
        r = walk.evaluate(given, pose)
        return Cyc(names, np.asarray(r.worlds))
    table = [k for k in wm.KNOBS if k[0] not in ("pose", "in_place")]
    table = [(n, (d if n != "tempo" else float(walk.P)), (lo if n != "tempo" else round(walk.P * 0.6)),
              (hi if n != "tempo" else round(walk.P * 1.6))) for n, d, lo, hi in table]
    base_given.setdefault("tempo", float(walk.P))
    scan(evaluate, names, table, None, base_given, "wb_%s%s" % (walk_name, "_" + pose_name if pose_name else ""))


def run_cat(preset):
    spec = importlib.util.spec_from_file_location("catmodel", os.path.join(REPO, "docs/superpowers/plans/catwalk/catmodel.py"))
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    with open(os.path.join(REPO, "SkeldarAnim/assets/manny_skeleton_template.json")) as handle:
        joints = json.load(handle)["joints"]
    skel = cm.Skeleton.from_template(dict((j["name"], {"parent": j.get("parent"), "world_matrix": j["world_matrix"]})
                                          for j in joints))
    names = None
    base_given = cm.preset(preset, 30)

    def evaluate(given):
        c = cm.generate(skel, given, 30)
        leaves = list(c.frames[0].keys())
        worlds = np.array([[c.frames[f][leaf] for f in range(len(c.frames))] for leaf in leaves])
        cy = Cyc(leaves, worlds)
        return cy
    probe = evaluate(base_given)
    names = probe.names
    table = [(k[0], k[1], k[2], k[3]) for k in cm.KNOBS]
    scan(evaluate, names, table, None, base_given, "cat_%s" % preset.replace(" ", ""))


if __name__ == "__main__":
    if sys.argv[1] == "wb":
        run_wb(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        run_cat(sys.argv[2])
