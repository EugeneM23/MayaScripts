"""Where a whole clip's turn gets sharper, pass by pass (2026-11-19, review note F).

    mayapy diag_walk_turn.py <settings.json> <out.json> <clip.fbx> [stage ...]

The clip onto a Manny UE5 skeleton with the card's settings (diag_walk_batch.setup), then `wholeclip.build` run
in memory with passes switched off one at a time (no scene writing): per stage every bone's peak acceleration
relative to the root (the root's horizontal place taken off, as the batch's metric F) against the raw clip's, and
the per-frame series around the worst frame. Stages:

  full      build as it stands
  nostance  the pose's stance blend off (bones=None)
  nolegs    the legs' contact fix and the sink off
  nogrip    the two-handed grip off
  diff      the walk's difference alone (all three off)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_walk_batch as base     # noqa: E402

BODY = ("pelvis", "spine_03", "head", "lowerarm_l", "lowerarm_r", "hand_r", "foot_l", "foot_r")


def accel(worlds, names, bone):
    j = names.index(bone)
    r = names.index("root")
    p = worlds[j, :, 3, :3].copy()
    p[:, 0] -= worlds[r, :, 3, 0]
    p[:, 2] -= worlds[r, :, 3, 2]
    return np.linalg.norm(np.diff(p, 2, axis=0), axis=1)


def yaw_deg(worlds, names, bone="root"):
    m = worlds[names.index(bone)]
    x = m[:, 0, :3]
    return np.degrees(np.arctan2(x[:, 0], x[:, 2]))


def main():
    settings_path, out_path, fbx = sys.argv[1:4]
    stages = sys.argv[4:] or ["full", "nostance", "nolegs", "nogrip", "diff"]
    cmds = base.setup(settings_path)
    from maya_uebridge import rigimport, skeletonimport
    from maya_scenesetup import catalog
    from maya_walk import panel, scene as ws, wholeclip
    name = os.path.splitext(os.path.basename(fbx))[0]
    ns, info, source = rigimport.import_source(fbx, name, 30.0, True)
    line, failure, _top = skeletonimport.onto_skeleton(catalog.character_for("Manny", "skeleton"), ns, info, source,
                                                       name, (0.0, 0.0, 0.0), decide=skeletonimport.choose_for)
    roots = [j for j in cmds.ls(type="joint", long=True) if j.endswith("|root")
             and not cmds.listRelatives(j, parent=True, type="joint")]
    root = roots[-1]
    walk = panel._own_for(root)
    panel._preset_onto([root], [walk])
    params = ws.normal_params(dict(panel.card_params(), in_place=1.0))
    anim = ws.animate(root, walk, panel.values(), None, panel.chosen_parts(), pose_card=panel.chosen_card(),
                      params=params, whole=True)
    dump = os.environ.get("SKELDAR_TURN_DUMP")
    if dump:                    # the build's inputs, for offline runs (pure numpy, no Maya)
        import pickle
        from maya_walk import files as wf, cards as wcards, model as wm
        data = wf.load(ws.walk_path(walk))
        lc = anim.walk.clip
        moving = anim.moving if anim.moving is not None else anim.result.worlds
        order = [list(anim.walk.names).index(n) for n in lc.names]
        pickle.dump({"raw": (list(data["names"]), list(data["parents"]), np.asarray(data["worlds"], float),
                             data["fps"]),
                     "loop": (list(lc.names), list(lc.parents), np.asarray(lc.worlds, float), lc.fps),
                     "result": np.asarray(moving, float)[order],
                     "statics": data["statics"],
                     "bones": wcards.unpack(anim.packed) if anim.packed is not None else None,
                     "parts": list(anim.parts), "share": float(wm.knobs(**anim.knobs).get("pose", 1.0))},
                    open(dump, "wb"))
        if os.environ.get("SKELDAR_TURN_DUMP_ONLY"):
            os._exit(0)
    orig = {k: getattr(wholeclip, k) for k in ("_leg_fix", "grip_hold", "build")}
    report = {"clip": name, "stages": {}}
    raw_w = None
    for st in stages:
        for k, v in orig.items():
            setattr(wholeclip, k, v)
        if st in ("nolegs", "diff"):
            wholeclip._leg_fix = lambda *a, **kw: 0.0
            wholeclip.REACH = 1e6
        else:
            wholeclip.REACH = 0.999
        if st in ("nogrip", "diff"):
            wholeclip.grip_hold = lambda *a, **kw: None
        if st in ("nostance", "diff"):
            def b(raw, loop, result, statics=None, bones=None, parts=None, share=1.0, k=None, _o=orig["build"]):
                return _o(raw, loop, result, statics, None, parts, share, k)
            wholeclip.build = b
        worlds, names, winfo = ws._whole(anim, walk)
        names = list(names)
        if raw_w is None:
            from maya_walk import files as wf
            data = wf.load(ws.walk_path(walk))
            raw_w = np.asarray(data["worlds"], float)
            report["yaw_root"] = [round(float(x), 1) for x in yaw_deg(raw_w, names)]
            report["yaw_pelvis_src"] = [round(float(x), 1) for x in yaw_deg(raw_w, names, "pelvis")]
            report["walking"] = winfo["walking"]
            report["still"] = [round(float(x), 3) for x in winfo["still"]]
            report["phases"] = [round(float(x), 2) for x in winfo["phases"]]
            report["src"] = {b: [round(float(x), 3) for x in accel(raw_w, names, b)] for b in BODY}
        report["yaw_pelvis_" + st] = [round(float(x), 1) for x in yaw_deg(worlds, names, "pelvis")]
        acc = {b: accel(worlds, names, b) for b in BODY}
        report["stages"][st] = {"peak": {b: (round(float(np.max(report["src"][b])), 2), round(float(acc[b].max()), 2),
                                             int(np.argmax(acc[b])) + 1) for b in BODY},
                                "series": {b: [round(float(x), 3) for x in acc[b]] for b in BODY}}
        print(st, json.dumps(report["stages"][st]["peak"]), flush=True)
    json.dump(report, open(out_path, "w"), indent=0)
    os._exit(0)


if __name__ == "__main__":
    main()
