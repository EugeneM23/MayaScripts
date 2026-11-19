"""Per-frame insides of wholeclip.build for one clip under the card's settings (2026-11-19, legs and pelvis).

    mayapy probe_wholeclip_legs.py <settings.json> <out.json> <clip.fbx> [variant]

The clip onto a Manny UE5 skeleton (diag_walk_batch's road), the walker's animation evaluated, then
wholeclip.build run with its cover and its leg solve watched: the stance weight, the pelvis height of the raw clip /
the stance / the out before the sink, the reach need and the sink, each foot's down flag and the legs' shortfall.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_walk_batch as diag  # noqa: E402


def main():
    settings_path, out_path, fbx = sys.argv[1:4]
    variant = sys.argv[4] if len(sys.argv) > 4 else "preset"
    cmds = diag.setup(settings_path)
    from maya_uebridge import rigimport, skeletonimport
    from maya_scenesetup import catalog
    from maya_walk import panel, scene as ws, wholeclip
    name = os.path.splitext(os.path.basename(fbx))[0]
    ns, info, source = rigimport.import_source(fbx, name, 30.0, True)
    before = set(cmds.ls(cmds.ls(type="joint", long=True) or [], uuid=True) or [])
    line, failure, _top = skeletonimport.onto_skeleton(catalog.character_for("Manny", "skeleton"), ns, info, source,
                                                       name, (0.0, 0.0, 0.0), decide=skeletonimport.choose_for)
    new = [j for j in cmds.ls(type="joint", long=True) if (cmds.ls(j, uuid=True) or [""])[0] not in before]
    root = [j for j in new if j.endswith("|root") and not cmds.listRelatives(j, parent=True, type="joint")][0]
    walk = panel._own_for(root)
    panel._preset_onto([root], [walk])
    params = json.loads(json.dumps(panel.card_params()))
    spec = diag.VARIANTS[variant]
    if "_all" in spec:
        params["changes"].clear()
    for k, val in spec.items():
        if k.startswith("_"):
            continue
        if val is None:
            for sfx in ("", "_l", "_r"):
                params["changes"].pop(k + sfx, None)
        else:
            params["changes"][k] = val
    if spec.get("_physics"):
        params["physics"] = True
    params["in_place"] = 1.0
    params = ws.normal_params(params)
    if "_edits" in spec:
        ws.set_edits(root, ws.empty_edits())
    anim = ws.animate(root, walk, panel.values(), None, panel.chosen_parts(), panel.chosen_card(), params,
                      whole=True)
    seen = {}
    real_cover = wholeclip.ss.cover

    def cover(need, sigma, periodic=False):
        out = real_cover(need, sigma, periodic)
        seen["need"], seen["drop"] = np.array(need), np.array(out)
        return out
    wholeclip.ss.cover = cover
    real_fix = wholeclip._leg_fix
    shorts = {"l": [], "r": []}

    def leg_fix(clip, worlds, targets, side, reach=wholeclip.REACH):
        s = real_fix(clip, worlds, targets, side, reach)
        shorts[side].append(s)
        return s
    wholeclip._leg_fix = leg_fix
    real_build = wholeclip.build

    def build(raw, loop, result, statics=None, bones=None, parts=None, share=1.0, k=None):
        import pickle
        def plain(c):
            return {"names": list(c.names), "parents": list(c.parents), "worlds": np.asarray(c.worlds),
                    "fps": c.fps, "name": c.name}
        pickle.dump({"raw": plain(raw), "loop": plain(loop), "result": plain(result), "statics": statics,
                     "bones": bones, "parts": parts, "share": share, "k": k},
                    open(os.path.splitext(out_path)[0] + "_args.pkl", "wb"))
        return real_build(raw, loop, result, statics, bones, parts, share, k)
    wholeclip.build = build
    worlds, names, winfo = ws._whole(anim, walk)
    from maya_startstop import model as ss
    data = ws.wf.load(ws.walk_path(walk))
    raw = np.asarray(data["worlds"], float)
    ix = dict((n, i) for i, n in enumerate(names))
    pel = ix["pelvis"]
    rep = {"clip": name, "walking": winfo["walking"], "start": winfo["start"], "stop": winfo["stop"],
           "transition": winfo["transition"],
           "still": [round(float(x), 3) for x in winfo["still"]],
           "raw_pelvis_y": [round(float(x), 2) for x in raw[pel, :, 3, 1]],
           "out_pelvis_y": [round(float(x), 2) for x in worlds[pel, :, 3, 1]],
           "need": [round(float(x), 2) for x in seen.get("need", [])],
           "drop": [round(float(x), 2) for x in seen.get("drop", [])],
           "short_l": [round(float(x), 2) for x in shorts["l"]],
           "short_r": [round(float(x), 2) for x in shorts["r"]]}
    st = winfo.get("stance_worlds")
    if st is not None:
        rep["stance_pelvis_y"] = [round(float(x), 2) for x in st[pel, :, 3, 1]]
    a = ss.Analysis(ss.Clip(data["names"], data["parents"], raw, data["fps"], name))
    for s in ("l", "r"):
        rep["down_" + s] = [int(x) for x in a.feet[s]["down"]]
        rep["contacts_" + s] = [list(map(int, c)) for c in a.feet[s]["contacts"]]
        th, ca, fo = (ix["%s_%s" % (b, s)] for b in ("thigh", "calf", "foot"))
        rep["out_leg_" + s] = [round(float(x), 2) for x in np.linalg.norm(worlds[fo, :, 3, :3] - worlds[th, :, 3, :3], axis=1)]
        rep["raw_leg_" + s] = [round(float(x), 2) for x in np.linalg.norm(raw[fo, :, 3, :3] - raw[th, :, 3, :3], axis=1)]
        rep["len_" + s] = round(float(np.linalg.norm(raw[ca, 0, 3, :3] - raw[th, 0, 3, :3])
                                      + np.linalg.norm(raw[fo, 0, 3, :3] - raw[ca, 0, 3, :3])), 2)
    json.dump(rep, open(out_path, "w"), indent=0)
    print("probe done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
