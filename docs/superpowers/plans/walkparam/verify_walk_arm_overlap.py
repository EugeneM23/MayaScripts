"""verify_walk_arm_overlap.py - the arms' overlap, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py

On a COPY of the animator's walks folder, with their own walker's settings (2026-10-29: their captured cycle,
the Pose Library card LongSword_Idle_3P at share 1 - a two-handed grip - In place, physics on, tempo pinned),
and the same cycle with DG_Idle (no grip) and with no pose at all: the hand stands where it stood that many
frames earlier (the direction from the shoulder exact, the distance clamped at the arm's own length), the
shoulder has not moved, the grip is held, the bones keep their lengths, the cycle is still a loop, 0 ms
changes nothing, the milliseconds are counted at the scene's rate, a lead goes the other way, Whip stacks on
top, and Balance sees it.
"""
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
MINE = os.environ.get("WALKS_HOME", "C:/Users/MY PC/Documents/maya/SkeldarWalks")
LIBRARY = os.environ.get("POSE_LIBRARY", "C:/Users/MY PC/Documents/maya/scripts/SkeldarAnim/poses")
WALK = os.environ.get("ARM_WALK", "own:7833074715b34c33")
SWORD = os.environ.get("ARM_SWORD_CARD", "LongSword_Idle_3P.pose")
DAGGER = os.environ.get("ARM_DAGGER_CARD", "DG_Idle.pose")
BASE = {"changes": {"tempo": ["ratio", 0.8709677419354839]}, "pins": ["tempo"], "in_place": 1.0,
        "physics": True}
LAG = 4.0                   # frames of the new cycle the gates measure at

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))         # the repository's plugin, never the installed copy
from maya_walk import scene as sw                             # noqa: E402
from maya_walk import cards as wcards                         # noqa: E402
from maya_walk import pose as wp                              # noqa: E402

wm, wt, gait = sw.wm, sw.wt, sw.gait
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


TEMP = tempfile.mkdtemp(prefix="arm_overlap_")
COPY = os.path.join(TEMP, "SkeldarWalks")
shutil.copytree(MINE, COPY)
sw.WALKS = COPY


def setup(share, card):
    """(walk, the base knobs, the prepared pose or None) of the animator's cycle under a pose card."""
    params = sw.normal_params(dict(BASE, pose=share))
    walk, statics = sw.load_walk(WALK, params["clean"])[:2]
    pose = None
    if share > 0.0 and card:
        bones = wcards.read_card(os.path.join(LIBRARY, card))[1]
        pose = wp.filtered(wp.prepare(walk, statics, bones, wm, wt), sw.ALL_PARTS)
    knobs = sw.params_knobs(walk, params)[0]
    return walk, knobs, pose


def run(walk, knobs, pose, **over):
    """The cycle under the card's knobs with `over` on top. A sided knob is set on BOTH sides as well: the
    card's knobs carry every side's own value (engine_knobs writes arm_overlap_l / _r), and the engine's
    `sided` rule gives a side's own value precedence over the plain knob - without this a plain
    arm_overlap=4 would be overridden by the two zeros beside it."""
    ks = dict(knobs)
    for name, value in over.items():
        ks[name] = value
        if name in wm.SIDED:
            ks[name + "_l"] = ks[name + "_r"] = value
    return walk.evaluate(ks, pose)


def path(walk, result, leaf):
    return np.array(result.worlds[walk.index[leaf]][:, 3, :3])


def lengths(walk, result, side):
    out = []
    for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_")):
        out.append(np.linalg.norm(path(walk, result, b + side) - path(walk, result, a + side), axis=1))
    return out


for label, share, card in (("the sword at 1.0 (a grip)", 1.0, SWORD),
                           ("the dagger at 1.0 (no grip)", 1.0, DAGGER),
                           ("no pose", 0.0, None)):
    print()
    print("=" * 78)
    print(label)
    print("=" * 78)
    walk, knobs, pose = setup(share, card)
    #  Balance and In place off for the geometry gates, so the pass is the only thing at work. With Balance
    #  on the late arms move the whole body (its own case below); In place runs AFTER the pass and subtracts
    #  a per-frame shift that follows the root's own path, not exactly the travel a frame, so a strict
    #  "where it stood LAG frames earlier" cannot be reconstructed from an in-place result (its own case
    #  below too: measured, 1.3 deg / 2.23 cm of In place's re-centring against 0.0000 with it off)
    plain = run(walk, knobs, pose, arm_drag=0.0, balance=0.0, in_place=0.0)
    n = plain.frames
    late = run(walk, knobs, pose, arm_drag=0.0, balance=0.0, in_place=0.0, arm_overlap=LAG)
    gate(late.info["arms"]["overlap"]["frames"] == LAG,
         "%s: the pass reports %g frames" % (label, late.info["arms"]["overlap"]["frames"]))
    gate(late.info["arms"]["overlap"]["grip"] == (share > 0.0 and card == SWORD),
         "%s: the grip branch is %s, as the pose is" % (label, late.info["arms"]["overlap"]["grip"]))

    worst_dir, worst_reach, moved = 0.0, 0.0, 0.0
    for side in ("l", "r"):
        chain = walk._arm_chains()[side]
        reach = sum(float(np.linalg.norm(walk.lt[j].mean(axis=0))) for j in chain[1:])
        was_path = path(walk, plain, "hand_" + side)
        per = (was_path[n] - was_path[0]) / float(n)
        for f in range(n):
            early = int((f - LAG) % n)
            want = was_path[early] - per * early + per * f
            sh = path(walk, late, "upperarm_" + side)[f]
            got = path(walk, late, "hand_" + side)[f]
            uw, ug = want - sh, got - sh
            rw, rg = float(np.linalg.norm(uw)), float(np.linalg.norm(ug))
            cos = float(np.dot(uw, ug) / (rw * rg))
            worst_dir = max(worst_dir, np.degrees(np.arccos(min(1.0, max(-1.0, cos)))))
            worst_reach = max(worst_reach, abs(rg - min(rw, reach)))
            moved = max(moved, float(np.linalg.norm(got - was_path[f])))
    gate(worst_dir < 1e-4, "%s: the late hand is on the line to where it stood %g frames earlier (%.2e deg)"
         % (label, LAG, worst_dir))
    gate(worst_reach < 1e-4, "%s: at that distance, or at the arm's own length where it clamps (%.2e cm)"
         % (label, worst_reach))
    gate(moved > 1.0, "%s: and it really moved, worst %.2f cm" % (label, moved))

    shoulder = max(float(np.abs(path(walk, late, "upperarm_" + s) - path(walk, plain, "upperarm_" + s)).max())
                   for s in ("l", "r"))
    gate(shoulder < 1e-9, "%s: the shoulder has not moved (%.2e cm)" % (label, shoulder))

    bones = max(float(np.abs(a - b).max()) for s in ("l", "r")
                for a, b in zip(lengths(walk, late, s), lengths(walk, plain, s)))
    #  the rebuild takes each bone's MEAN length over the cycle, the frames their own per frame: 5.6e-6 cm
    gate(bones < 1e-4, "%s: the bones keep their lengths (%.2e cm)" % (label, bones))

    loop_r = float(np.abs(late.worlds[:, -1, :3, :3] - late.worlds[:, 0, :3, :3]).max())
    travel = plain.worlds[:, -1, 3, :3] - plain.worlds[:, 0, 3, :3]
    loop_x = float(np.abs((late.worlds[:, -1, 3, :3] - late.worlds[:, 0, 3, :3]) - travel).max())
    gate(loop_r < 1e-7 and loop_x < 1e-6, "%s: still a loop (%.2e, %.2e)" % (label, loop_r, loop_x))

    zero = run(walk, knobs, pose, arm_drag=0.0, balance=0.0, in_place=0.0, arm_overlap=0.0)
    gate(np.array_equal(zero.worlds, plain.worlds), "%s: 0 ms changes nothing, matrix for matrix" % label)

    if share > 0.0 and card == SWORD:
        hold_l, hold_r = walk.index["hand_l"], walk.index["hand_r"]
        held = max(float(np.abs(late.worlds[hold_l, f] @ np.linalg.inv(late.worlds[hold_r, f])
                                - plain.worlds[hold_l, f] @ np.linalg.inv(plain.worlds[hold_r, f])).max())
                   for f in range(n + 1))
        gate(held < 1e-6, "%s: the grip is held - the left hand in the right's is unchanged (%.2e)"
             % (label, held))

    lead = run(walk, knobs, pose, arm_drag=0.0, balance=0.0, in_place=0.0, arm_overlap=-LAG)
    back = float(np.abs(path(walk, late, "hand_l") - path(walk, plain, "hand_l")).max())
    ahead = float(np.abs(path(walk, lead, "hand_l") - path(walk, plain, "hand_l")).max())
    gate(abs(back - ahead) < 0.5 * back, "%s: a lead goes as far the other way (%.2f against %.2f cm)"
         % (label, ahead, back))

    whip = run(walk, knobs, pose, arm_drag=2.0, arm_bounce=0.0, balance=0.0, in_place=0.0)
    both = run(walk, knobs, pose, arm_drag=2.0, arm_bounce=0.0, balance=0.0, in_place=0.0, arm_overlap=LAG)
    #  not "further from the plain arm": a lag of a quarter of a periodic cycle can bring the hand back
    #  toward where it started (no pose: the lag alone 25.8 cm, with the springs 22.9). What the ordering
    #  claims is that the springs take the LATE arm as their target, so the two together are neither
    apart = lambda a, b: float(np.abs(path(walk, a, "hand_l") - path(walk, b, "hand_l")).max())
    gate(apart(both, whip) > 1.0 and apart(both, late) > 1.0,
         "%s: Whip takes the late arm as its target (%.2f cm from the springs alone, %.2f from the lag alone)"
         % (label, apart(both, whip), apart(both, late)))

#  In place, which is how the animator walks their own cycle
print()
print("=" * 78)
print("In place (the animator's own setting)")
print("=" * 78)
walk, knobs, pose = setup(1.0, SWORD)
plain = run(walk, knobs, pose, arm_drag=0.0, balance=0.0)
late = run(walk, knobs, pose, arm_drag=0.0, balance=0.0, arm_overlap=LAG)
n = plain.frames
gate(float(knobs["in_place"]) > 0.0, "the card's own knobs carry In place (%g)" % knobs["in_place"])
moved = float(np.abs(path(walk, late, "hand_r") - path(walk, plain, "hand_r")).max())
gate(moved > 1.0, "the hand moves In place too (%.2f cm)" % moved)
shoulder = float(np.abs(path(walk, late, "upperarm_r") - path(walk, plain, "upperarm_r")).max())
gate(shoulder < 1e-9, "the shoulder has not moved (%.2e cm)" % shoulder)
hold_l, hold_r = walk.index["hand_l"], walk.index["hand_r"]
held = max(float(np.abs(late.worlds[hold_l, f] @ np.linalg.inv(late.worlds[hold_r, f])
                        - plain.worlds[hold_l, f] @ np.linalg.inv(plain.worlds[hold_r, f])).max())
           for f in range(n + 1))
gate(held < 1e-6, "the grip is held In place too (%.2e)" % held)
loop_r = float(np.abs(late.worlds[:, -1, :3, :3] - late.worlds[:, 0, :3, :3]).max())
loop_x = float(np.abs(late.worlds[:, -1, 3, :3] - late.worlds[:, 0, 3, :3]).max())
gate(loop_r < 1e-7 and loop_x < 1e-6, "still a loop, and standing on the spot (%.2e, %.2e)" % (loop_r, loop_x))
bones = max(float(np.abs(a - b).max()) for s in ("l", "r")
            for a, b in zip(lengths(walk, late, s), lengths(walk, plain, s)))
gate(bones < 1e-4, "the bones keep their lengths In place too (%.2e cm)" % bones)

#  the milliseconds, counted at the scene's own rate
print()
print("=" * 78)
print("milliseconds at the scene's rate")
print("=" * 78)
walk, _, pose = setup(1.0, SWORD)
own = gait.own(walk)
vals = gait.values(own, {"arm_overlap": ("offset", 150.0)})
at30 = gait.engine_knobs(walk, own, vals, fps_out=30.0)["arm_overlap_l"]
at24 = gait.engine_knobs(walk, own, vals, fps_out=24.0)["arm_overlap_l"]
gate(abs(at30 - 4.5) < 1e-6 and abs(at24 - 3.6) < 1e-6,
     "150 ms is %.3f frames at 30 fps and %.3f at 24" % (at30, at24))
for unit, want in (("ntsc", 30.0), ("film", 24.0)):
    cmds.currentUnit(time=unit)
    gate(abs(sw.output_fps() - want) < 1e-6, "the scene at %s reads %g fps" % (unit, sw.output_fps()))
cmds.currentUnit(time="ntsc")
params = sw.normal_params(dict(BASE, pose=1.0,
                               changes=dict(BASE["changes"], arm_overlap=["offset", 150.0]),
                               pins=BASE["pins"] + ["arm_overlap"]))
knobs = sw.params_knobs(walk, params)[0]
gate(abs(knobs["arm_overlap_l"] - 4.5) < 1e-6,
     "the card's 150 ms reach the engine as %.3f frames" % knobs["arm_overlap_l"])

#  Balance sees the late arms
print()
print("=" * 78)
print("Balance")
print("=" * 78)
walk, knobs, pose = setup(1.0, SWORD)
flat = run(walk, knobs, pose, arm_drag=0.0, balance=1.0, arm_overlap=0.0)
bent = run(walk, knobs, pose, arm_drag=0.0, balance=1.0, arm_overlap=6.0)
carry = abs(float(flat.info["balance"]["carry"]) - float(bent.info["balance"]["carry"]))
gate(carry > 1e-4, "the carry differs with the arms late (%.4f cm)" % carry)

shutil.rmtree(TEMP, ignore_errors=True)
print()
print("%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": " + ", ".join(map(str, FAILED))) if FAILED else ""))
sys.exit(1 if FAILED else 0)
