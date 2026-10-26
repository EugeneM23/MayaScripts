import re, io
out = []
meta = []
for g, tag in (("run", "h"), ("sprint", "s")):
    lines = io.open("poses_%s.txt" % g, encoding="utf-8").read().splitlines()
    m = lines[1].replace("{p:", "{g:'%s', p:" % tag)
    j = lines[2].replace("{p:", "{g:'%s', p:" % tag)
    meta.append(m[1:-1]); out.append(j[1:-1])
io.open("runposes_meta.txt", "w", encoding="utf-8").write("[" + ",".join(meta) + "]")
io.open("runposes_joints.txt", "w", encoding="utf-8").write("[" + ",".join(out) + "]")
