import json
d = json.load(open("gait_curves.json"))
for name in ("asd", "HavyRun"):
    a = d[name]
    print(name)
    print(" k   pct   bob   heelL ballL heelR ballR  kneeL kneeR  thighL  footfwdL  armL  pelyaw  thoyaw  obl")
    for r in a["rows"]:
        print("%2d %5.1f %6.2f %5.1f %5.1f %5.1f %5.1f %6.1f %6.1f %6.1f %7.1f %6.1f %6.1f %6.1f %5.1f" % (
            r["frame"], r["pct"], r["bob"], r["heel_h_l"], r["ball_h_l"], r["heel_h_r"], r["ball_h_r"], r["knee_l"], r["knee_r"],
            r["thigh_l"], r["foot_fwd_l"], r["arm_l"], r["pel_yaw"], r["tho_yaw"], r["pel_obl"]))
