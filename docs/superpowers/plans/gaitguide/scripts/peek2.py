import json, math
d = json.load(open("gait_curves.json"))
for name in ("asd", "HavyRun", "RunFast", "AGS_Sprint"):
    p = d[name]["poses"]["0"]
    px, py = p["pelvis"]; nx, ny = p["neck_01"]; hx, hy = p["head"]
    s3 = p["spine_03"]
    print(name, "pelvis", p["pelvis"], "spine_03", s3, "neck", p["neck_01"], "head", p["head"],
          "lean pelvis->neck %.1f" % math.degrees(math.atan2(nx - px, ny - py)),
          "lean spine3->head %.1f" % math.degrees(math.atan2(hx - s3[0], hy - s3[1])))
