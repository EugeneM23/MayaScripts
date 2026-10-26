import json, sys
d = json.load(open("gait_curves.json"))
def js(rows, keys):
    out = []
    for r in rows:
        parts = []
        for k in keys:
            v = r[k]
            if isinstance(v, bool):
                parts.append("%s:%s" % (k, "true" if v else "false"))
            else:
                parts.append("%s:%s" % (k, ("%.1f" % v).rstrip("0").rstrip(".") if k != "pct" else ("%.1f" % v)))
        out.append("{" + ", ".join(parts) + "}")
    return "[" + ",".join(out) + "]"
keys = ["pct", "bob", "sway", "pel_yaw", "tho_yaw", "pel_obl", "heel_h_l", "ball_h_l", "foot_fwd_l", "foot_fwd_r", "knee_l", "thigh_l", "dorsi_l", "arm_l", "arm_r", "elbow_l", "down_l", "down_r"]
which = sys.argv[1]
print(js(d[which]["rows"], keys))
