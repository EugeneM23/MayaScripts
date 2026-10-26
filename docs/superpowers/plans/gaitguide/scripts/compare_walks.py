import gzip, json, os, math, numpy as np
F = r"C:/Users/MY PC/Documents/maya/SkeldarWalks"
def load(n):
    d = json.load(gzip.open(os.path.join(F, n + ".walk.gz"), "rt", encoding="utf-8"))
    names = d["names"]; w = np.array(d["worlds"], float).reshape(len(names), -1, 4, 4)
    return d, names, w[:, :, 3, :3]
def unit(v): return v / np.linalg.norm(v, axis=-1, keepdims=True)
def ang(a, b): return np.degrees(np.arccos(np.clip(np.sum(unit(a)*unit(b), -1), -1, 1)))
def measure(n):
    d, names, P = load(n)
    fps = d["fps"]; J = lambda j: P[names.index(j)]
    pel = J("pelvis"); NT = pel.shape[0] - 1
    tr = pel[-1] - pel[0]; up = np.array([0, 1., 0]); fwd = tr.copy(); fwd[1] = 0; fwd /= np.linalg.norm(fwd); left = np.cross(up, fwd)
    spf = np.linalg.norm(tr[[0, 2]]) / NT
    t = np.arange(NT); line = np.outer(t, tr / NT) + pel[0]; rel = pel[:NT] - line
    out = {"fps": fps, "frames": NT, "speed": spf * fps / 100, "pelvis_h": pel[:NT, 1].mean()}
    leg = np.linalg.norm(J("thigh_l")[0] - J("calf_l")[0]) + np.linalg.norm(J("calf_l")[0] - J("foot_l")[0])
    out["leg"] = leg
    # contacts
    ev = []
    for s in "lr":
        heel = J("foot_" + s); ball = J("ball_" + s)
        hh = heel[:, 1] - heel[:NT, 1].min(); bh = ball[:, 1] - ball[:NT, 1].min()
        vh = np.r_[np.linalg.norm(np.diff(heel[:, [0, 2]], axis=0), axis=1), 0]
        vb = np.r_[np.linalg.norm(np.diff(ball[:, [0, 2]], axis=0), axis=1), 0]
        down = ((hh < 2.5) & (vh < 0.35 * spf)) | ((bh < 2.5) & (vb < 0.35 * spf))
        down = down[:NT]
        for f in range(NT):
            if down[f] and not down[f - 1]:
                # place: ankle position at the middle of this contact
                g = f
                while down[g % NT] and g - f < NT: g += 1
                p = heel[f]
                ev.append((f, s, float(p @ fwd), float(p @ left), (g - f)))
        out["stance_" + s] = down.mean()
    ev.sort()
    steps = []
    k = len(ev)
    for i in range(k):
        f, s, x, y, ln = ev[i]; f2, s2, x2, y2, _ = ev[(i + 1) % k]
        dt = (f2 - f) % NT
        dx = x2 - x if i + 1 < k else x2 + tr @ fwd - x
        steps.append(dict(foot=s2, frames=dt, length=dx, width=abs(y2 - y)))
    out["steps"] = steps
    out["bob"] = np.ptp(pel[:NT, 1]); out["sway"] = np.ptp(rel @ left)
    hl = J("thigh_l")[:NT] - J("thigh_r")[:NT]; sl = J("upperarm_l")[:NT] - J("upperarm_r")[:NT]
    yaw = lambda v: np.degrees(np.arctan2(-(v @ fwd), v @ left)); roll = lambda v: np.degrees(np.arctan2(v @ up, v @ left))
    out["pel_yaw"] = np.ptp(yaw(hl)); out["pel_obl"] = np.ptp(roll(hl)); out["sho_yaw"] = np.ptp(yaw(sl)); out["sho_roll"] = np.ptp(roll(sl))
    tv = J("neck_01")[:NT] - pel[:NT]
    pitch = np.degrees(np.arctan2(tv @ fwd, tv @ up)); lean_side = np.degrees(np.arctan2(tv @ left, tv @ up))
    out["trunk_pitch_mean"] = pitch.mean(); out["trunk_side_range"] = np.ptp(lean_side)
    head = J("head")[:NT]; out["head_bob"] = np.ptp(head[:, 1]); out["head_sway"] = np.ptp((head - line) @ left)
    for s in "l":
        sho = J("upperarm_" + s)[:NT]; elb = J("lowerarm_" + s)[:NT]; wri = J("hand_" + s)[:NT]
        a = np.degrees(np.arctan2((elb - sho) @ fwd, -((elb - sho) @ up)))
        out["arm_range"] = np.ptp(a); out["elbow_min"] = (180 - ang(sho - elb, wri - elb)).min(); out["elbow_max"] = (180 - ang(sho - elb, wri - elb)).max()
        heel = J("foot_" + s)[:NT]; out["heel_lift"] = np.ptp(heel[:, 1])
        k = (180 - ang(J("thigh_" + s)[:NT] - J("calf_" + s)[:NT], heel - J("calf_" + s)[:NT]))
        out["knee_max"] = k.max(); out["knee_min"] = k.min()
    return out
for n in ["asd", "dw", "Creep_Drunk", "Sword_Drunked", "TestStrefe", "sadda"]:
    o = measure(n)
    st = o.pop("steps")
    print("== %s" % n)
    print("  " + "  ".join("%s %.2f" % (k, v) for k, v in o.items()))
    for s in st:
        print("   step onto %s: %d fr, length %.1f cm, width %.1f cm" % (s["foot"], s["frames"], s["length"], s["width"]))
