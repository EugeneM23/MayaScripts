"""Key poses (side view) from the saved cycles, for the stick-figure filmstrips: every joint's (forward, up)
in cm, forward relative to the pelvis at that frame, up above the cycle's floor; plus a heel point, a toe tip
and a head top carried in their joints' own frames from the rest pose."""
import gzip, json, os, sys
import numpy as np

FOLDER = r"C:/Users/MY PC/Documents/maya/SkeldarWalks"
JOINTS = ["pelvis", "spine_01", "spine_03", "spine_05", "neck_01", "head",
          "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "middle_01_l",
          "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r", "middle_01_r",
          "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r"]


def run(name, picks, strides=1, dupe=False, tag="w"):
    with gzip.open(os.path.join(FOLDER, name + ".walk.gz"), "rt", encoding="utf-8") as h:
        d = json.load(h)
    names = d["names"]
    W = np.array(d["worlds"], float).reshape(len(names), -1, 4, 4)
    if dupe and np.allclose(W[:, -1, 3, :3], W[:, -2, 3, :3], atol=1e-4):
        W = W[:, :-1]
    P = W[:, :, 3, :3]; R = W[:, :, :3, :3]
    J = lambda n: names.index(n)
    st = d["statics"]
    rest = lambda j: np.array(st[j]["rest"], float).reshape(4, 4)
    pel = P[J("pelvis")]
    travel = pel[-1] - pel[0]
    fwd = travel.copy(); fwd[1] = 0; fwd /= np.linalg.norm(fwd)
    NT = P.shape[1] - 1
    # left initial contact, as in analyse.py
    heel = P[J("foot_l")]; ball = P[J("ball_l")]
    spf = np.linalg.norm(travel[[0, 2]]) / NT
    hh = heel[:NT, 1] - heel[:NT, 1].min(); bh = ball[:NT, 1] - ball[:NT, 1].min()
    vh = np.linalg.norm((heel[1:NT + 1] - heel[:NT])[:, [0, 2]], axis=1)
    vb = np.linalg.norm((ball[1:NT + 1] - ball[:NT])[:, [0, 2]], axis=1)
    down = ((hh < 2.5) & (vh < 0.35 * spf)) | ((bh < 2.5) & (vb < 0.35 * spf))
    ic = next((f for f in range(NT) if down[f] and not down[f - 1]), 0)
    floor = min(P[J(j)][:NT, 1].min() for j in ("ball_l", "ball_r", "foot_l", "foot_r"))

    def local(j, point_rest):
        """a rest-pose world point expressed in joint j's rest frame (row vectors)"""
        m = rest(j)
        return (point_rest - m[3, :3]) @ np.linalg.inv(m[:3, :3])

    extras = {}
    for s in ("l", "r"):
        fr, br = rest("foot_" + s)[3, :3], rest("ball_" + s)[3, :3]
        lf = np.linalg.norm(br - fr)
        heel_rest = np.array([fr[0], br[1] - 2.0, fr[2] - 0.38 * lf])
        toe_rest = br + (br - fr) / lf * np.array([1.0, 0.0, 1.0]) * 0.55 * lf
        toe_rest[1] = br[1] - 1.0
        extras["heel_" + s] = ("foot_" + s, local("foot_" + s, heel_rest))
        extras["toe_" + s] = ("ball_" + s, local("ball_" + s, toe_rest))
    hr = rest("head")[3, :3]
    extras["headtop"] = ("head", local("head", hr + np.array([0.0, 19.0, 2.0])))

    rows, meta = [], []
    for order, (k, label) in enumerate(picks, 1):
        f = (ic + k) % NT
        base = pel[f]
        pts = dict((j, P[J(j)][f]) for j in JOINTS)
        for e, (j, loc) in extras.items():
            pts[e] = loc @ R[J(j)][f] + P[J(j)][f]
        for j, p in pts.items():
            rows.append("{p:%d, j:'%s', x:%.1f, y:%.1f}" % (order, j, float((p - base) @ fwd), float(p[1] - floor)))
        meta.append("{p:%d, name:'%s', frame:%d, bob:%.1f}" % (order, label, k, float(pel[f][1] - floor)))
    print("%s POSES rows=%d" % (name, len(rows)))
    print("[" + ",".join(meta) + "]")
    print("[" + ",".join(rows) + "]")


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "walk":
        run("asd", [(0, "Контакт"), (1, "Даун"), (8, "Пассинг"), (12, "Ап"), (16, "Контакт")])
    elif which == "run":
        run("HavyRun", [(0, "Контакт"), (2, "Даун"), (5, "Толчок"), (9, "Полёт"), (12, "Контакт")])
    elif which == "sprint":
        run("AGS_Sprint", [(0, "Контакт"), (2, "Даун"), (3, "Толчок"), (6, "Полёт"), (8, "Контакт")], strides=4, dupe=True)
