"""What Walk Builder does to a clip, measured against the clip itself - the animator's batch review (2026-11-19).

    mayapy diag_walk_batch.py <settings.json> <out.json> <clip.fbx> [variant ...]

One clip from Unreal (an FBX the batch worker exported) onto a Manny UE5 skeleton, processed with the card's
settings out of `settings.json` (the animator's optionVars, `batch.py settings`) and the preset they light, In
place - once per variant, each variant a set of parameter changes taken off or set (`ablate`). Every bone that
matters is sampled on the source (before the transfer) and on each result, and `metrics` gives one number per
defect the animator named:

  A timing     the key range, and each foot's contacts (ball near the ground, slow) against the source's
  B elbow out  the elbow's distance from the body's midline in the chest's frame (the worst frame)
  C wobble     the elbow's high-frequency motion in the chest's frame (what a 2-frame Gaussian takes off), RMS / max
  D jitter     the same for the clavicle and the upper arm's direction, in degrees
  E feet       the ankles' spread across the pelvis, the worst frame; the knees' lean in (deg) against the leg
  F turns      the body's peak acceleration relative to the root, per bone, against the source's (the ratio)
  G pelvis     the pelvis height's range over the take against the source's, and its lowest frame
  K knees      the knee angle's worst second difference (a kink)
"""
import json
import os
import sys
import tempfile

import numpy as np

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PLUGIN = os.path.join(REPO, "SkeldarAnim").replace("\\", "/")

BONES = ["root", "pelvis", "spine_01", "spine_03", "spine_05", "neck_01", "head",
         "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
         "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r"]

# a variant: the name and what it does to the card's parameter changes (key -> None to drop, else a change)
VARIANTS = {
    "preset": {},
    "no_rigpose": {"_edits": None},
    "shoulder0": {"weapon_shoulder": None},
    "overlap0": {"weapon_overlap": None},
    "hold_off": {"weapon_hold": ["offset", -1.0]},
    "inherit1": {"weapon_inherit": None},
    "aim1": {"weapon_aim": None},
    "width_own": {"width": None},
    "height_own": {"height": None},
    "physics_on": {"_physics": True, "balance": None, "foot_placement": None},
    "plain": {"_edits": None, "_all": None},       # every change off: the walk's own with the pose
    "motion": {"_motion": True},                     # the card as it is, with root motion (the export's road)
}


def setup(settings_path):
    import maya.standalone
    maya.standalone.initialize(name="python")
    import maya.cmds as cmds
    for p in ("fbxmaya", "matrixNodes", "quatNodes"):
        try:
            cmds.loadPlugin(p, quiet=True)
        except Exception:
            pass
    sys.path.insert(0, PLUGIN)
    settings = json.load(open(settings_path))
    for k, v in settings.items():
        if isinstance(v, list):
            cmds.optionVar(remove=k)
            for x in v:
                cmds.optionVar(**{("stringValueAppend" if isinstance(x, str) else "floatValueAppend"): (k, x)})
        elif isinstance(v, str):
            cmds.optionVar(stringValue=(k, v))
        elif isinstance(v, int):
            cmds.optionVar(intValue=(k, v))
        else:
            cmds.optionVar(floatValue=(k, v))
    shared = settings.get("skeldarWalkFolder") or os.path.join(cmds.internalVar(userAppDir=True), "SkeldarWalks")
    walks = tempfile.mkdtemp(prefix="skeldar_diag_walks_")
    import shutil
    for keep in ("presets.json", "library_walks.json", "library_poses.json"):
        if os.path.exists(os.path.join(shared, keep)):
            shutil.copy(os.path.join(shared, keep), walks)
    cmds.optionVar(stringValue=("skeldarWalkFolder", walks))
    if not settings.get("skeldarPoseLibraryRoot"):
        theirs = os.path.join(cmds.internalVar(userAppDir=True), "scripts", "SkeldarAnim", "poses")
        if os.path.isdir(theirs):
            cmds.optionVar(stringValue=("skeldarPoseLibraryRoot", theirs.replace("\\", "/")))
    from maya_walk import panel
    preset = settings.get("skeldarWalk_preset")
    if preset:
        panel.apply_preset(preset)
    return cmds


def sample(cmds, top, frames):
    """{bone: (n, 4, 4) world matrices} under `top` (a skeleton root's long path) over `frames`."""
    joints = cmds.listRelatives(top, allDescendents=True, type="joint", fullPath=True) or []
    joints.append(top)
    pick = {}
    for b in BONES:
        hit = [j for j in joints if j.split("|")[-1].split(":")[-1] == b]
        if hit:
            pick[b] = hit[0]
    out = {b: np.zeros((len(frames), 4, 4)) for b in pick}
    for i, f in enumerate(frames):
        cmds.currentTime(f)
        for b, j in pick.items():
            out[b][i] = np.array(cmds.getAttr(j + ".worldMatrix[0]")).reshape(4, 4)
    return out


def key_range(cmds, top):
    js = (cmds.listRelatives(top, allDescendents=True, type="joint", fullPath=True) or []) + [top]
    t = cmds.keyframe(js, q=True, timeChange=True) or [0.0]
    return float(min(t)), float(max(t))


# ---------------------------------------------------------------- the metrics (pure numpy)

def pos(s, b):
    return s[b][:, 3, :3]


def smooth(x, sigma=2.0):
    """A periodic-free Gaussian along axis 0 (edges reflected)."""
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.concatenate([x[r:0:-1], x, x[-2:-r - 2:-1]], axis=0)
    return np.stack([np.convolve(pad[:, c], k, mode="valid") for c in range(x.shape[1])], axis=1)


def in_frame(s, frame_bone, b):
    """`b`'s place in `frame_bone`'s frame (row vectors: p_local = (p - o) . R^T with R the 3x3 rows)."""
    m = s[frame_bone]
    p = pos(s, b)
    out = np.zeros_like(p)
    for i in range(len(p)):
        R = m[i, :3, :3]
        R = R / np.linalg.norm(R, axis=1, keepdims=True)
        out[i] = (p[i] - m[i, 3, :3]) @ R.T
    return out


def ground_path(s, b, travel):
    """`b`'s place against the ground: relative to the root's horizontal place, the source's root travel put back.
    The source reads its own world; an In place result (the root's travel taken off) reads as if it travelled -
    a planted foot stands still in both (2026-11-19: read in world, every In place contact slid at walk speed)."""
    p = pos(s, b).copy()
    r = pos(s, "root")
    p[:, 0] += travel[:, 0] - r[:, 0]
    p[:, 2] += travel[:, 2] - r[:, 2]
    return p


def contacts(s, side, travel=None, up=1):
    """Each frame the foot of `side` is down: the ball or the ankle near its own low AND that point still against
    the ground (cm a frame)."""
    down = None
    for b in ("ball_" + side, "foot_" + side):
        p = pos(s, b) if travel is None else ground_path(s, b, travel)
        h = p[:, up]
        # near the floor it stands on: the median height of the frames it holds still - not the lowest frame, which
        # a swing dipped through the floor (Box_B_LR_Lfoot's left ball, -6 cm mid-swing at the turn) would make the
        # floor, and every contact would then read as lifted; the height it stands at is the legs' question, not the
        # timing's
        v = np.linalg.norm(np.diff(p, axis=0), axis=1)
        v = np.concatenate([v[:1], v])
        still = v < 1.5
        low = float(np.median(h[still])) if still.any() else float(np.percentile(h, 5))
        hit = (h < low + 3.0) & still
        down = hit if down is None else (down | hit)
    return down


def runs(mask):
    out, start = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and start is None:
            start = i
        elif not m and start is not None:
            if i - start >= 2:
                out.append((start, i - 1))
            start = None
    return out


def body_rel(s, b):
    p = pos(s, b).copy()
    r = pos(s, "root")
    p[:, 0] -= r[:, 0]
    p[:, 2] -= r[:, 2]
    return p


def angle_deg(a, b):
    c = np.sum(a * b, axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1) + 1e-12)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def knee_angle(s, side):
    h, k, a = pos(s, "thigh_" + side), pos(s, "calf_" + side), pos(s, "foot_" + side)
    return 180.0 - angle_deg(h - k, a - k)


def metrics(src, res, rng_src, rng_res):
    m = {}
    # A
    m["A_range_src"], m["A_range_res"] = rng_src, rng_res
    shifts, ends = [], []
    travel = pos(src, "root") - pos(src, "root")[:1]        # the source root's travel: what In place took off
    travel[:, 1] = 0.0
    own = pos(res, "root") - pos(res, "root")[:1]          # a result with root motion (variant motion): its own
    own[:, 1] = 0.0
    travel_res = own if float(np.linalg.norm(own, axis=1).max()) > 1.0 else travel
    for side in "lr":
        cs, cr = runs(contacts(src, side, travel)), runs(contacts(res, side, travel_res))
        m["A_contacts_%s_src" % side] = cs
        m["A_contacts_%s_res" % side] = cr
        for a, b in cs:
            best = min(cr, key=lambda r: abs(r[0] - a), default=None)
            if best:
                shifts.append(abs(best[0] - a))
                ends.append(abs(best[1] - b))
        m["A_contact_count_%s" % side] = (len(cs), len(cr))
    m["A_worst_contact_shift_fr"] = max(shifts) if shifts else None
    m["A_worst_contact_end_shift_fr"] = max(ends) if ends else None
    # B, C
    for side in "lr":
        for tag, s in (("src", src), ("res", res)):
            e = in_frame(s, "spine_03", "lowerarm_" + side)
            m["B_elbow_out_%s_%s" % (side, tag)] = float(np.max(np.abs(e[:, 2]))) if False else None
            hf = e - smooth(e)
            m["C_elbow_hf_%s_%s" % (side, tag)] = (round(float(np.sqrt(np.mean(np.sum(hf ** 2, 1)))), 3),
                                                   round(float(np.max(np.linalg.norm(hf, axis=1))), 3))
    # elbow out: distance from the shoulder-hand line toward outside, in cm, its worst
    for side in "lr":
        for tag, s in (("src", src), ("res", res)):
            sh, el, ha = pos(s, "upperarm_" + side), pos(s, "lowerarm_" + side), pos(s, "hand_" + side)
            mid = pos(s, "spine_03")
            line = ha - sh
            t = np.sum((el - sh) * line, 1) / (np.sum(line * line, 1) + 1e-12)
            foot = sh + line * t[:, None]
            off = el - foot
            out_dir = sh - mid
            out_dir[:, 1] = 0
            out_dir /= np.linalg.norm(out_dir, axis=1, keepdims=True) + 1e-12
            m["B_elbow_out_%s_%s" % (side, tag)] = round(float(np.max(np.sum(off * out_dir, 1))), 2)
    # D: the clavicle's and upper arm's direction jitter, deg
    for side in "lr":
        for tag, s in (("src", src), ("res", res)):
            vals = []
            for a, b in (("clavicle_" + side, "upperarm_" + side), ("upperarm_" + side, "lowerarm_" + side)):
                d = pos(s, b) - pos(s, a)
                d /= np.linalg.norm(d, axis=1, keepdims=True)
                sm = smooth(d)
                sm /= np.linalg.norm(sm, axis=1, keepdims=True)
                vals.append(round(float(np.max(angle_deg(d, sm))), 2))
            m["D_jitter_clav_upper_%s_%s" % (side, tag)] = vals
    # E: feet spread across the pelvis, knees in
    for tag, s in (("src", src), ("res", res)):
        fl, fr = in_frame(s, "pelvis", "foot_l"), in_frame(s, "pelvis", "foot_r")
        # the pelvis's lateral axis: the hips' line
        hl, hr = in_frame(s, "pelvis", "thigh_l"), in_frame(s, "pelvis", "thigh_r")
        ax = int(np.argmax(np.abs((hl - hr).mean(0))))
        spread = np.abs(fl[:, ax] - fr[:, ax])
        m["E_feet_spread_max_%s" % tag] = round(float(spread.max()), 1)
        m["E_feet_spread_med_%s" % tag] = round(float(np.median(spread)), 1)
        m["E_hip_width_%s" % tag] = round(float(np.abs(hl[:, ax] - hr[:, ax]).mean()), 1)
    # F
    ratios = {}
    for b in ("pelvis", "spine_03", "head", "lowerarm_l", "lowerarm_r", "hand_r", "foot_l", "foot_r"):
        a_s = np.linalg.norm(np.diff(body_rel(src, b), 2, axis=0), axis=1)
        a_r = np.linalg.norm(np.diff(body_rel(res, b), 2, axis=0), axis=1)
        n = min(len(a_s), len(a_r))
        ratios[b] = (round(float(a_s[:n].max()), 2), round(float(a_r[:n].max()), 2),
                     round(float(np.percentile(a_s[:n], 95)), 2), round(float(np.percentile(a_r[:n], 95)), 2))
    m["F_accel_max_src_res_p95_src_res"] = ratios
    # G
    for tag, s in (("src", src), ("res", res)):
        y = pos(s, "pelvis")[:, 1]
        m["G_pelvis_%s" % tag] = (round(float(y.min()), 1), round(float(y.max()), 1), round(float(y.max() - y.min()), 1),
                                  int(np.argmin(y)))
    # K
    for side in "lr":
        for tag, s in (("src", src), ("res", res)):
            k = knee_angle(s, side)
            m["K_knee_%s_%s" % (side, tag)] = (round(float(k.min()), 1), round(float(k.max()), 1),
                                              round(float(np.max(np.abs(np.diff(k, 2)))), 2))
    return m


def main():
    settings_path, out_path, fbx = sys.argv[1:4]
    variants = sys.argv[4:] or ["preset"]
    cmds = setup(settings_path)
    from maya_uebridge import rigimport, skeletonimport
    from maya_scenesetup import catalog
    from maya_walk import panel, scene as ws
    name = os.path.splitext(os.path.basename(fbx))[0]
    ns, info, source = rigimport.import_source(fbx, name, 30.0, True)
    src_top = cmds.ls(source, long=True)[0]
    a, b = key_range(cmds, src_top)
    frames = list(range(int(a), int(b) + 1))
    src = sample(cmds, src_top, frames)
    before = set(cmds.ls(cmds.ls(type="joint", long=True) or [], uuid=True) or [])
    line, failure, _top = skeletonimport.onto_skeleton(catalog.character_for("Manny", "skeleton"), ns, info, source,
                                                       name, (0.0, 0.0, 0.0), decide=skeletonimport.choose_for)
    if failure:
        raise SystemExit(failure)
    new = [j for j in cmds.ls(type="joint", long=True) if (cmds.ls(j, uuid=True) or [""])[0] not in before]
    root = [j for j in new if j.endswith("|root") and not cmds.listRelatives(j, parent=True, type="joint")][0]
    ru = cmds.ls(root, uuid=True)[0]
    walk = panel._own_for(root)
    panel._preset_onto([root], [walk])
    edits = ws.edits_of(cmds.ls(ru, long=True)[0])
    report = {"clip": name, "frames": [frames[0], frames[-1]], "variants": {}}
    base = panel.card_params()
    for v in variants:
        spec = VARIANTS[v]
        top = cmds.ls(ru, long=True)[0]
        ws.set_edits(top, edits if "_edits" not in spec else ws.empty_edits())
        params = json.loads(json.dumps(base))
        changes = params["changes"]
        if "_all" in spec:
            changes.clear()
        for k, val in spec.items():
            if k.startswith("_"):
                continue
            if val is None:
                changes.pop(k, None)
                for sfx in ("_l", "_r"):
                    changes.pop(k + sfx, None)
            else:
                changes[k] = val
        if spec.get("_physics"):
            params["physics"] = True
        params["in_place"] = 0.0 if spec.get("_motion") else 1.0
        params = ws.normal_params(params)
        _r, info2, text = ws.apply(top, walk, panel.values(), None, panel.chosen_parts(),
                                   pose_card=panel.chosen_card(), params=params, whole=panel.whole_on())
        res = sample(cmds, cmds.ls(ru, long=True)[0], frames)
        report["variants"][v] = {"line": text, "m": metrics(src, res, (a, b), key_range(cmds, top))}
        # the sampled bones kept beside the report, so a metric can be read again with no Maya
        np.savez_compressed(os.path.splitext(out_path)[0] + "_%s.npz" % v,
                            **dict(("src_" + k, x) for k, x in src.items()),
                            **dict(("res_" + k, x) for k, x in res.items()))
        print("done", v, flush=True)
    json.dump(report, open(out_path, "w"), indent=1, default=str)
    os._exit(0)


if __name__ == "__main__":
    main()
