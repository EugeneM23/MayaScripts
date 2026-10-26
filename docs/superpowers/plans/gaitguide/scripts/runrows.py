import json
d = json.load(open("gait_curves.json"))
out = []
for clip, tag in (("HavyRun", "heavy"), ("AGS_Sprint", "sprint")):
    rows = d[clip]["rows"]
    mean = sum(r["bob"] for r in rows) / len(rows)
    for r in rows:
        out.append("{clip:'%s', pct:%.1f, bob:%.1f, heel:%.1f, ball:%.1f, fwd:%.1f, knee:%.1f, thigh:%.1f, arm:%.1f, down_l:%s, down_r:%s}" % (
            tag, r["pct"], r["bob"] - mean, r["heel_h_l"], r["ball_h_l"], r["foot_fwd_l"], r["knee_l"], r["thigh_l"], r["arm_l"],
            "true" if r["down_l"] else "false", "true" if r["down_r"] else "false"))
print("[" + ",".join(out) + "]")
for clip in ("asd", "HavyRun", "RunFast", "AGS_Sprint"):
    a = d[clip]
    print(clip, {k: a[k] for k in a if k not in ("rows", "poses", "pelvis_fwd")})
