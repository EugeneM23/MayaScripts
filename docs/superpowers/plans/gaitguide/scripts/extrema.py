import json
import numpy as np
d = json.load(open("gait_curves.json"))
for clip in ("asd", "HavyRun"):
    rows = d[clip]["rows"]; N = len(rows)
    print("==", clip, "N =", N)
    for key in ("bob", "sway", "pel_yaw", "tho_yaw", "pel_obl", "heel_h_l", "ball_h_l", "foot_fwd_l", "knee_l", "thigh_l", "dorsi_l", "foot_pitch_l", "arm_l", "elbow_l", "trunk", "head_y"):
        v = np.array([r[key] for r in rows])
        # periodic smoothing to avoid frame noise
        vs = (np.roll(v, 1) + 2 * v + np.roll(v, -1)) / 4
        ext = []
        for i in range(N):
            a, b, c = vs[i - 1], vs[i], vs[(i + 1) % N]
            if b > a and b >= c:
                ext.append(("max", i, v[i]))
            elif b < a and b <= c:
                ext.append(("min", i, v[i]))
        txt = "  ".join("%s@%.0f%%(%s)" % (t, 100.0 * i / N, ("%.1f" % val)) for t, i, val in ext)
        print("  %-12s range %.1f..%.1f | %s" % (key, v.min(), v.max(), txt))
