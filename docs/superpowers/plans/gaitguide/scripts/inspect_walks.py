import gzip, json, os, sys
import numpy as np

FOLDER = r"C:/Users/MY PC/Documents/maya/SkeldarWalks"
for name in ("asd", "dw", "AGS_Sprint", "HavyRun", "RunFast", "sadda", "TestStrefe"):
    path = os.path.join(FOLDER, name + ".walk.gz")
    with gzip.open(path, "rt", encoding="utf-8") as h:
        d = json.load(h)
    names = d["names"]
    w = np.array(d["worlds"], float).reshape(len(names), -1, 4, 4)
    frames = w.shape[1]
    pel = w[names.index("pelvis"), :, 3, :3]
    travel = pel[-1] - pel[0]
    print("%-12s fps=%s frames=%d joints=%d up=%s start=%s" % (name, d["fps"], frames, len(names), d["up"], d.get("start")))
    print("   travel=%s  (%.1f cm/cycle) pelvis y %.1f..%.1f" % (np.round(travel, 1), np.linalg.norm(travel[[0, 2]]), pel[:, 1].min(), pel[:, 1].max()))
    print("   has:", [j for j in ("root", "pelvis", "thigh_l", "calf_l", "foot_l", "ball_l", "upperarm_l", "lowerarm_l", "hand_l", "spine_01", "spine_03", "spine_05", "neck_01", "head", "clavicle_l") if j in names])
