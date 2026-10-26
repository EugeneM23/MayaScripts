"""Read saved walk/run cycles (skeldar.walk) and measure what an animator would key: pelvis bob/sway/surge,
pelvis and chest turns, feet heights and in-place slide, knee/hip/ankle/elbow/shoulder angles, contacts,
key poses. Writes gait_curves.json beside this script."""
import gzip, json, math, os, sys
import numpy as np

FOLDER = r"C:/Users/MY PC/Documents/maya/SkeldarWalks"
OUT = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "gait_curves.json")


def load(name):
    with gzip.open(os.path.join(FOLDER, name + ".walk.gz"), "rt", encoding="utf-8") as h:
        d = json.load(h)
    names = d["names"]
    w = np.array(d["worlds"], float).reshape(len(names), -1, 4, 4)
    return d, names, w


def unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n == 0, 1, n)


def angle(a, b):
    c = np.sum(unit(a) * unit(b), axis=-1)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def analyse(name, label, kind, strides=1, drop_last_dupe=False):
    d, names, w = load(name)
    fps = float(d["fps"])
    P = w[:, :, 3, :3]
    F = P.shape[1]
    if drop_last_dupe and np.allclose(P[:, -1], P[:, -2], atol=1e-4):
        P = P[:, :-1]; F -= 1
    J = lambda n: P[names.index(n)]
    st = d["statics"]
    rest = lambda j: np.array(st[j]["rest"], float).reshape(4, 4)[3, :3]
    pel = J("pelvis")
    travel = pel[-1] - pel[0]
    NT = F - 1                      # frames of the whole clip cycle
    N = NT // strides               # frames of one stride
    up = np.array([0.0, 1.0, 0.0])
    fwd = travel.copy(); fwd[1] = 0; fwd = fwd / np.linalg.norm(fwd)
    left = np.cross(up, fwd)
    cyc = slice(0, NT)
    t = np.arange(NT)
    spf = np.linalg.norm(travel[[0, 2]]) / NT        # cm per frame
    line = np.outer(t, travel / NT) + pel[0]
    rel = pel[cyc] - line
    bob = pel[cyc, 1]; sway = rel @ left; surge = rel @ fwd

    def proj(v):
        return np.stack([v @ fwd, v @ left, v @ up], axis=-1)

    S = {}
    for s in ("l", "r"):
        heel = J("foot_" + s); ball = J("ball_" + s); knee = J("calf_" + s); hip = J("thigh_" + s)
        hh = heel[cyc, 1] - heel[cyc, 1].min(); bh = ball[cyc, 1] - ball[cyc, 1].min()
        vh = np.linalg.norm((heel[1:NT + 1] - heel[0:NT])[:, [0, 2]], axis=1)
        vb = np.linalg.norm((ball[1:NT + 1] - ball[0:NT])[:, [0, 2]], axis=1)
        heel_down = (hh < 2.5) & (vh < 0.35 * spf)
        ball_down = (bh < 2.5) & (vb < 0.35 * spf)
        down = heel_down | ball_down
        h, k_, a_, b_ = hip[cyc], knee[cyc], heel[cyc], ball[cyc]
        S[s] = dict(
            heel_h=hh, ball_h=bh, down=down,
            knee=180.0 - angle(h - k_, a_ - k_),
            thigh=np.degrees(np.arctan2(proj(k_ - h)[:, 0], -proj(k_ - h)[:, 2])),
            dorsi=angle(rest("calf_" + s) - rest("foot_" + s), rest("ball_" + s) - rest("foot_" + s)) - angle(k_ - a_, b_ - a_),
            foot_pitch=np.degrees(np.arctan2(proj(b_ - a_)[:, 2], np.hypot(proj(b_ - a_)[:, 0], proj(b_ - a_)[:, 1]))),
            foot_fwd=(a_ - pel[cyc]) @ fwd,
            ankle_fwd=a_ @ fwd,
        )
        sho = J("upperarm_" + s)[cyc]; elb = J("lowerarm_" + s)[cyc]; wri = J("hand_" + s)[cyc]
        S[s]["arm"] = np.degrees(np.arctan2(proj(elb - sho)[:, 0], -proj(elb - sho)[:, 2]))
        S[s]["elbow"] = 180.0 - angle(sho - elb, wri - elb)

    hl = J("thigh_l")[cyc] - J("thigh_r")[cyc]
    sl = J("upperarm_l")[cyc] - J("upperarm_r")[cyc]
    yaw = lambda v: np.degrees(np.arctan2(-(v @ fwd), v @ left))   # + = right side forward
    roll = lambda v: np.degrees(np.arctan2(v @ up, v @ left))      # + = left side up
    pel_yaw, pel_obl, tho_yaw = yaw(hl), roll(hl), yaw(sl)
    # trunk lean (pelvis -> neck_01) against vertical, relative to the rest pose (rest faces +Z, up Y)
    tr = proj(J("neck_01")[cyc] - pel[cyc])
    rv = rest("neck_01") - rest("pelvis")
    trunk = np.degrees(np.arctan2(tr[:, 0], tr[:, 2])) - math.degrees(math.atan2(rv[2], rv[1]))
    head_y = J("head")[cyc, 1]

    # left initial contact
    dl = S["l"]["down"]
    ic = next((f for f in range(NT) if dl[f] and not dl[f - 1]), 0)
    order = [(ic + k) % NT for k in range(N)]
    pct = [round(100.0 * k / N, 2) for k in range(N)]
    rows = []
    for k, i in enumerate(order):
        r = dict(pct=pct[k], frame=k, bob=bob[i], sway=sway[i], surge=surge[i], pel_yaw=pel_yaw[i], pel_obl=pel_obl[i],
                 tho_yaw=tho_yaw[i], trunk=trunk[i], head_y=head_y[i])
        for s in ("l", "r"):
            for k2 in ("heel_h", "ball_h", "knee", "thigh", "dorsi", "foot_pitch", "foot_fwd", "arm", "elbow"):
                r["%s_%s" % (k2, s)] = S[s][k2][i]
            r["down_" + s] = bool(S[s]["down"][i])
        rows.append(dict((a, (round(float(b), 3) if isinstance(b, (float, np.floating)) else b)) for a, b in r.items()))

    # events inside the stride (frame indices k)
    def first(pred, start=0):
        for k in range(start, N):
            if pred(rows[k]):
                return k
        return None
    to_l = first(lambda r: not r["down_l"])
    ic_r = first(lambda r: r["down_r"], first(lambda r: not r["down_r"]) or 0)
    to_r = first(lambda r: not r["down_r"], ic_r or 0)
    # passing: swing ankle crosses stance ankle during left stance (right foot passes the left)
    af = [S["r"]["ankle_fwd"][i] - S["l"]["ankle_fwd"][i] for i in order]
    passing = next((k for k in range(1, N) if af[k - 1] < 0 <= af[k]), None)
    passing_r = next((k for k in range(1, N) if af[k - 1] > 0 >= af[k]), None)
    bobs = [r["bob"] for r in rows]
    low1 = int(np.argmin(bobs[: (ic_r or N // 2)]))
    high1 = int(np.argmax(bobs[: (ic_r or N // 2)]))
    events = dict(ic_l=0, to_l=to_l, ic_r=ic_r, to_r=to_r, passing=passing, passing_r=passing_r, low=low1, high=high1)

    cyc_s = N / fps
    stride = np.linalg.norm(travel[[0, 2]]) / strides
    stance_l = sum(r["down_l"] for r in rows) / N
    stance_r = sum(r["down_r"] for r in rows) / N
    both = sum(1 for r in rows if r["down_l"] and r["down_r"]) / N
    none = sum(1 for r in rows if not r["down_l"] and not r["down_r"]) / N
    take = lambda key: [r[key] for r in rows]
    rng = lambda key: round(max(take(key)) - min(take(key)), 2)
    out = dict(name=name, label=label, kind=kind, fps=fps, frames=N, cycle_s=round(cyc_s, 4),
               stride_cm=round(float(stride), 1), step_cm=round(float(stride) / 2, 1),
               speed_mps=round(float(stride) / 100 / cyc_s, 3), cadence_spm=round(120.0 / cyc_s, 1),
               frames_per_step=round(N / 2, 2), bob_cm=rng("bob"), sway_cm=rng("sway"), surge_cm=rng("surge"),
               pelvis_mean=round(float(np.mean(take("bob"))), 2), stance_l=round(stance_l, 3), stance_r=round(stance_r, 3),
               double_support=round(both, 3), flight=round(none, 3), pel_yaw_range=rng("pel_yaw"),
               pel_obl_range=rng("pel_obl"), tho_yaw_range=rng("tho_yaw"),
               knee_l_min=round(min(take("knee_l")), 1), knee_l_max=round(max(take("knee_l")), 1),
               thigh_l_min=round(min(take("thigh_l")), 1), thigh_l_max=round(max(take("thigh_l")), 1),
               dorsi_l_min=round(min(take("dorsi_l")), 1), dorsi_l_max=round(max(take("dorsi_l")), 1),
               arm_l_min=round(min(take("arm_l")), 1), arm_l_max=round(max(take("arm_l")), 1),
               elbow_l_min=round(min(take("elbow_l")), 1), elbow_l_max=round(max(take("elbow_l")), 1),
               heel_max=round(max(take("heel_h_l")), 1), ball_max=round(max(take("ball_h_l")), 1),
               trunk_mean=round(float(np.mean(take("trunk"))), 1), trunk_range=rng("trunk"), head_bob=rng("head_y"),
               events=events)
    out["rows"] = rows
    joints = [j for j in ("pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head",
                          "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
                          "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r") if j in names]
    floor = min(J(j)[cyc, 1].min() for j in ("ball_l", "ball_r", "foot_l", "foot_r"))
    out["poses"] = dict((k, dict((j, [round(float((J(j)[order[k]] - pel[order[k]]) @ fwd), 2),
                                      round(float(J(j)[order[k]][1] - floor), 2)]) for j in joints)) for k in range(N))
    out["pelvis_fwd"] = [round(float((pel[order[k]] - pel[order[0]]) @ fwd), 2) for k in range(N)]
    return out


def main():
    clips = [("asd", "walk", 1, False), ("HavyRun", "run", 1, False), ("RunFast", "run", 1, False),
             ("AGS_Sprint", "sprint", 4, True)]
    res = {}
    for name, kind, strides, dupe in clips:
        a = analyse(name, name, kind, strides, dupe)
        res[name] = a
        print("== %s: N=%d fps=%g cycle %.3fs stride %.1f step %.1f speed %.2f m/s cadence %.1f frames/step %.1f" % (
            name, a["frames"], a["fps"], a["cycle_s"], a["stride_cm"], a["step_cm"], a["speed_mps"], a["cadence_spm"], a["frames_per_step"]))
        print("   bob %.2f sway %.2f surge %.2f pelvis %.1f | stance L %.2f R %.2f double %.2f flight %.2f" % (
            a["bob_cm"], a["sway_cm"], a["surge_cm"], a["pelvis_mean"], a["stance_l"], a["stance_r"], a["double_support"], a["flight"]))
        print("   pel yaw %.1f obl %.1f thorax yaw %.1f | knee %.1f..%.1f thigh %.1f..%.1f dorsi %.1f..%.1f arm %.1f..%.1f elbow %.1f..%.1f" % (
            a["pel_yaw_range"], a["pel_obl_range"], a["tho_yaw_range"], a["knee_l_min"], a["knee_l_max"], a["thigh_l_min"], a["thigh_l_max"],
            a["dorsi_l_min"], a["dorsi_l_max"], a["arm_l_min"], a["arm_l_max"], a["elbow_l_min"], a["elbow_l_max"]))
        print("   heel max %.1f ball max %.1f trunk %.1f (range %.1f) head bob %.2f events %s" % (
            a["heel_max"], a["ball_max"], a["trunk_mean"], a["trunk_range"], a["head_bob"], a["events"]))
        print("   down L:", "".join("L" if r["down_l"] else "." for r in a["rows"]))
        print("   down R:", "".join("R" if r["down_r"] else "." for r in a["rows"]))
    with open(OUT, "w") as h:
        json.dump(res, h)
    print("wrote", OUT)


main()
