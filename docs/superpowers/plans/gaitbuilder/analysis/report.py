import json, sys, glob, numpy as np
def effect(row):
    best = (0, 0, "", "")
    for tag, e in row["ends"].items():
        if "groups" not in e: continue
        for g, (r, p, rm, pm) in e["groups"].items():
            if r > best[0]: best = (r, best[1], g if r >= best[0] else best[2], best[3])
            if p > best[1]: best = (best[0], p, best[2], g)
    return best
for path in sorted(glob.glob("*.json")):
    if path.startswith("quality"): continue
    d = json.load(open(path))
    print("\n=== %s  frames %d  eval %.2fs" % (d["label"], d["frames"], d["eval_s"]))
    rows = d["rows"]
    out = []
    for r in rows:
        rot, pos, grot, gpos = effect(r)
        out.append((max(rot, pos * 1.0), r["knob"], rot, grot, pos, gpos))
    out.sort()
    for score, k, rot, grot, pos, gpos in out:
        flag = "WEAK" if rot < 2.0 and pos < 1.0 else ("low" if rot < 5.0 and pos < 2.5 else "")
        print("  %-18s rot %6.1f deg (%-7s) pos %6.1f cm (%-7s) %s" % (k, rot, grot, pos, gpos, flag))
    names = d["sim_names"]; sim = np.array(d["sim"]); norms = np.array(d["norms"])
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if norms[i] > 1e-6 and norms[j] > 1e-6 and abs(sim[i, j]) > 0.85:
                pairs.append((abs(sim[i, j]), names[i], names[j], sim[i, j]))
    pairs.sort(reverse=True)
    print("  redundant (|cos| > 0.85):", "; ".join("%s~%s %.2f" % (a, b, c) for _, a, b, c in pairs[:25]))
    sv = np.array(d["singular"])
    if len(sv):
        e = sv ** 2 / np.sum(sv ** 2)
        c = np.cumsum(e)
        print("  effective dims: 90%% of the variance in %d of %d knobs, 99%% in %d" % (np.searchsorted(c, 0.9) + 1, len(sv), np.searchsorted(c, 0.99) + 1))
