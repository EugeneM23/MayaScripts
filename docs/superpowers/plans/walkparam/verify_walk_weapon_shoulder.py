"""verify_walk_weapon_shoulder.py - Walk Builder's Shoulder, in mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_weapon_shoulder.py

The animator (2026-11-10, a walker on port 7005): «перерастягивается локоть при текущих настройках. Нужно
сделать доводчик плеча которые будет подкручивать плече что бы мы избавились от перерастяжения». Their own
cycle, their own two-handed card and their card's own settings (read off the walker's memo), the whole road
through scene.apply onto a plain Manny UE5 skeleton with a Long Sword in its right hand, every number read
back off the scene's joints. On a COPY of the walks folder (the harness is verify_walk_weapon_aim's).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("WEAPON_WALK", "own:c1d1b1c8e510aa98")       # the walker's own captured cycle
sys.argv = sys.argv[:1] + ["none"]         # the harness reads its own phases off the command line

import verify_walk_weapon_aim as A         # noqa: E402  (initializes Maya, loads the repository's plugin)

cmds, sw, wm = A.cmds, A.sw, A.wm
gate = A.gate
#  the walker's card as its memo holds it (params), 2026-11-10
THEIRS = {"changes": {"balance": ["offset", -1.0], "foot_placement": ["offset", -1.0], "whip": ["offset", 0.36],
                      "height": ["offset", 39.99481778508405], "weapon_overlap": ["offset", 43.1],
                      "weapon_aim": ["offset", -0.7], "weapon_inherit": ["offset", -0.33],
                      "width": ["ratio", 0.3895847787104724]},
          "pins": ["arms", "balance", "foot_placement", "hands", "height", "weapon_aim", "weapon_hold",
                   "weapon_inherit", "weapon_overlap", "whip", "width"],
          "macros": {}, "character": "", "strength": 1.0, "physics": False, "pose": 1.0, "in_place": 1.0,
          "clean": {"smooth": 0.92, "seam": 10.26}, "knee_pops": True}
SEEN = 0.942           # the left arm's reach in their scene, of its length (frame 53)
NAMES = ("clavicle", "upperarm", "lowerarm", "hand")
BODY = ("pelvis", "spine_05", "head", "foot_l", "foot_r")


def main():
    if not A.ready_walks():
        print("skipped")
        return 0
    root, weapon = A.add_walker()
    joints = dict((p.rsplit("|", 1)[-1], p) for p in cmds.listRelatives(root, allDescendents=True, type="joint",
                                                                        fullPath=True))

    def press(share):
        params = sw.normal_params(dict(THEIRS))
        if share > 0.0:
            params["changes"] = dict(params["changes"], weapon_shoulder=["offset", share])
            params["pins"] = sorted(set(params["pins"]) | {"weapon_shoulder"})
        result, _info, said = sw.apply(root, A.WALK, params=params, pose_card=A.CARD)[:3]
        start, n = sw.memo_of(root)["start"], result.frames
        read = dict((name, []) for name in list(BODY) + ["weapon"] + [b + "_" + s for b in NAMES for s in "lr"])
        for f in range(n + 1):
            cmds.currentTime(start + f, update=True)
            for name in read:
                node = weapon if name == "weapon" else joints[name]
                read[name].append(np.array(cmds.xform(node, query=True, worldSpace=True, matrix=True)).reshape(4, 4))
        return dict((name, np.array(mats)) for name, mats in read.items()), said

    def reach(read, side):
        up, lo, hand = (read[b + "_" + side][:, 3, :3] for b in NAMES[1:])
        arm = np.linalg.norm(lo - up, axis=1) + np.linalg.norm(hand - lo, axis=1)
        return np.linalg.norm(hand - up, axis=1) / arm

    def bend(read, side):
        up, lo, hand = (read[b + "_" + side][:, 3, :3] for b in NAMES[1:])
        a, b = lo - up, hand - lo
        cos = np.sum(a * b, axis=1) / np.linalg.norm(a, axis=1) / np.linalg.norm(b, axis=1)
        return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))

    def turn(a, b):
        return max(math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(a[f, :3, :3]).T
                                                               @ wm.orthonormal(b[f, :3, :3])))))
                   for f in range(len(a)))

    none, said0 = press(0.0)
    r0 = reach(none, "l")
    gate(abs(float(r0.max()) - SEEN) < 0.01,
         "Shoulder 0 is their scene: the left arm stretched to %.3f of its length (their scene %.3f), the "
         "elbow's bend %.0f..%.0f deg" % (r0.max(), SEEN, bend(none, "l").min(), bend(none, "l").max()))
    gate("shoulder takes" not in said0, "...and the line says nothing of the shoulder")

    full, said = press(1.0)
    for side, word in (("l", "left"), ("r", "right")):
        was, got = reach(none, side), reach(full, side)
        gate(float(np.ptp(got)) < 0.005 < float(np.ptp(was)) and abs(float(got.mean()) - float(was[:-1].mean())) < 0.01,
             "Shoulder 1, the %s arm: one reach, %.3f..%.3f of its length (it was %.3f..%.3f), the elbow's bend "
             "%.1f..%.1f deg (was %.1f..%.1f)" % (word, got.min(), got.max(), was.min(), was.max(),
                                                  bend(full, side).min(), bend(full, side).max(),
                                                  bend(none, side).min(), bend(none, side).max()))
        hand = float(np.abs(full["hand_" + side] - none["hand_" + side]).max())
        gate(hand < 1e-3, "   ...its hand stays where the tab put it: %.2e" % hand)
        pivot = float(np.abs(full["clavicle_" + side][:, 3, :3] - none["clavicle_" + side][:, 3, :3]).max())
        deg = turn(none["clavicle_" + side], full["clavicle_" + side])
        moved = float(np.linalg.norm(full["upperarm_" + side][:, 3, :3] - none["upperarm_" + side][:, 3, :3],
                                     axis=1).max())
        gate(pivot < 1e-3 and 1.0 < deg <= wm.SHOULDER_MAX_DEG,
             "   ...the clavicle turns about its own pivot (%.2e): up to %.1f deg, the shoulder %.2f cm"
             % (pivot, deg, moved))
        lens = max(float(np.ptp(np.linalg.norm(full[b + "_" + side][:, 3, :3] - full[a + "_" + side][:, 3, :3],
                                               axis=1)))
                   for a, b in zip(NAMES[:-1], NAMES[1:]))
        gate(lens < 1e-3, "   ...every bone keeps its length: %.2e cm" % lens)
    sword = float(np.abs(full["weapon"] - none["weapon"]).max())
    gate(sword < 1e-3, "the sword stays where it was: %.2e" % sword)
    body = max(float(np.abs(full[name] - none[name]).max()) for name in BODY)
    gate(body < 1e-6, "the body itself is untouched: %.2e" % body)
    gate("the shoulder takes 100 % of the arm's reach" in said,
         "the line says it: ...%s" % said[said.find("the shoulder takes"):][:110])

    half, _said = press(0.5)
    was, got = reach(none, "l"), reach(half, "l")
    mean = float(was[:-1].mean())
    off = float(np.abs((got - mean) - 0.5 * (was - mean)).max())
    gate(off < 0.003, "a half leaves half of the change: %.3f..%.3f (%.4f off the promise)" % (got.min(), got.max(), off))

    back, _said = press(0.0)
    again = max(float(np.abs(back[name] - none[name]).max()) for name in none)
    gate(again < 1e-4, "back at 0 the walker is where it was: %.2e" % again)       # the keys' own euler noise

    print("\n%d of %d gates failed%s" % (len(A.FAILED), A.COUNT[0], (": %s" % A.FAILED) if A.FAILED else ""))
    A.shutil.rmtree(A.TEMP, ignore_errors=True)
    return 1 if A.FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
