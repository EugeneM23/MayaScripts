"""verify_walk_weapon_chest.py - the weapon's overlap from the CHEST and 2H, in mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_weapon_chest.py

The animator: «он должен быть в walk builder во вкладке Weapon и работать без рига». Two phases, on a COPY
of the animator's walks folder (their own cycle and the Pose Library card LongSword_Idle_3P, a two-handed
grip - the scene on port 7004 on 2026-10-30):

  model  the pass's own promise on their cycle under their card: the defaults the identity matrix for
         matrix, the weapon sitting on the chest of `lag` frames ago, the strengths each measured against
         the body's own turn and travel as the control, the grip held, the bones' lengths, the loop closed,
         2H binding the free hand, and Balance seeing it.
  keys   the whole road through scene.apply onto a plain Manny UE5 skeleton with a Long Sword in its right
         hand and NO RIG: the keys read back off the joints show the same promise, and the Pick line says
         it.

Phases can be named on the command line (`model`, `keys`); the default runs both.
"""
import math
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
MINE = os.environ.get("WALKS_HOME", "C:/Users/MY PC/Documents/maya/SkeldarWalks")
LIBRARY = os.environ.get("POSE_LIBRARY", "C:/Users/MY PC/Documents/maya/scripts/SkeldarAnim/poses")
WALK = os.environ.get("WEAPON_WALK", "own:8e4ef9f3703a44a3")
CARD = os.environ.get("WEAPON_CARD", "LongSword_Idle_3P.pose")
MS = float(os.environ.get("CHEST_MS", "150"))        # the lag the gates measure at
BENT = 70.0          # deg: the elbows bent so the arm can follow its hand (see `run`)
BASE = {"changes": {"tempo": ["ratio", 0.8709677419354839]}, "pins": ["tempo"], "in_place": 1.0,
        "physics": True}
PHASES = tuple(a for a in sys.argv[1:] if not a.startswith("-")) or ("model", "keys")

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))         # the repository's plugin, never the installed copy
from maya_walk import scene as sw                             # noqa: E402
from maya_walk import cards as wcards                         # noqa: E402
from maya_walk import pose as wp                              # noqa: E402
from maya_scenesetup import catalog, character, equip, bonedrive   # noqa: E402

wm, wt, gait = sw.wm, sw.wt, sw.gait
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


TEMP = tempfile.mkdtemp(prefix="weapon_chest_")
COPY = os.path.join(TEMP, "SkeldarWalks")
shutil.copytree(MINE, COPY)
sw.WALKS = COPY
HAS_CARD = bool(CARD) and os.path.isdir(os.path.join(LIBRARY, CARD))
if HAS_CARD:
    cmds.optionVar(stringValue=("skeldarPoseLibraryRoot", LIBRARY))
else:
    print("note: %s is not in %s - the gates run with no pose (straight arms)" % (CARD, LIBRARY))
if not sw.walk_exists(WALK):
    names = sw.walk_names()
    if not names:
        print("no walk to read in %s - nothing to verify" % MINE)
        raise SystemExit(1)
    WALK = names[0]
    print("note: %s is not in the folder - using %s" % (os.environ.get("WEAPON_WALK", WALK), WALK))


def place(local, m):
    return np.asarray(local, float) @ m[:3, :3] + m[3, :3]


def world(node, frame=None):
    """A node's world matrix (4, 4), Maya's own row-vector order, at `frame` (a real time change: the
    weapon's space is parent-constrained, trap 69)."""
    if frame is not None:
        cmds.currentTime(frame, update=True)
    return np.array(cmds.xform(node, query=True, worldSpace=True, matrix=True), float).reshape(4, 4)


def add_walker():
    """A Manny UE5 SKELETON - no rig at all - with a Long Sword in its right hand: (root, the weapon)."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    character.add_character(catalog.character_for("Manny", "skeleton"))
    root = [p for p in cmds.ls(type="joint", long=True) if p.rsplit("|", 1)[-1] == "root"][0]
    said = equip.to_hand(root, "R", catalog.by_key("LongSword_02"))
    marked = [n for n in cmds.ls(transforms=True, long=True)
              if cmds.attributeQuery(bonedrive.MARKER, node=n, exists=True)]
    if not marked:
        raise RuntimeError("no weapon in the hand: %s" % said)
    return root, marked[0]


def turned(a, b):
    """The angle between two rotations (3x3), degrees."""
    return math.degrees(float(np.linalg.norm(wm.log_rot(np.asarray(a, float).T @ np.asarray(b, float)))))


# ------------------------------------------------------------------ model

def phase_model():
    print("\n-- model: the pass's promise on the animator's own cycle")
    cmds.file(new=True, force=True)
    walk, statics = sw.load_walk(WALK, sw.normal_params(BASE)["clean"])[:2]
    pose = None
    if HAS_CARD:
        bones = wcards.read_card(os.path.join(LIBRARY, CARD))[1]
        pose = wp.filtered(wp.prepare(walk, statics, bones, wm, wt), sw.ALL_PARTS)
    base = sw.params_knobs(walk, sw.normal_params(dict(BASE, pose=1.0 if pose else 0.0)))[0]
    #  the geometry is measured in the travelling cycle the pass works in: In place takes the root's own
    #  per-frame shift out AFTER the arms pass (trap 318), and the springs move the hands after it
    base = dict(base, in_place=0.0)
    held = {"r": {"grip": (2.0, -3.0, 1.0), "tip": (2.0, -3.0, 116.0)}}   # the Long Sword's own blade

    def run(with_pose=True, **over):
        #  the elbows bent (BENT) and the arm springs off, the reasons Weapon overlap's own tests give: the
        #  walker's arm hangs 99 % extended, and an arm at full stretch cannot follow a hand the pass moves -
        #  two_bone clamps it on its line and the promise gives by millimetres. Bent, the arm reaches it.
        #  Balance off for the geometry: its carry moves the BODY when the arms move late (gate 11 is
        #  its own), and the chest the promise is read against must be the same in both runs
        ks = dict(base, elbow_add=BENT, elbow_add_l=BENT, elbow_add_r=BENT, balance=0.0)
        for name, value in over.items():            # a sided knob on both sides too (trap 317)
            ks[name] = value
            if name in wm.SIDED:
                ks[name + "_l"] = ks[name + "_r"] = value
        return walk.evaluate(ks, pose if with_pose else None, weapons=held)

    lag = MS * walk.fps / 1000.0
    chains = walk._arm_chains()
    hand_r, hand_l = chains["r"][-1], chains["l"][-1]
    chest = walk._chest_joint()
    #  no pose for the geometry: under the two-handed card at full share the model stills the arms
    #  and the hand rides the chest rigidly, where the promise is trivially true. Gate 12 is the
    #  card's own (the hold kept through the pass).
    quiet = run(with_pose=False, arm_drag=0.0)
    n = quiet.frames
    grip_p = np.array(held["r"]["grip"])

    #  1 - the defaults
    same = run(with_pose=False, arm_drag=0.0, weapon_chest_rotation=1.0, weapon_chest_position=1.0,
               weapon_chest_lag=0.0)
    gate(np.array_equal(same.worlds, quiet.worlds),
         "1 / 1 / 0 is the walk itself, matrix for matrix")

    #  2 - own_knobs
    own = walk.evaluate(dict(walk.own_knobs(), in_place=0.0, arm_drag=0.0), pose, weapons=held)
    plain = walk.evaluate(dict(walk.own_knobs(), in_place=0.0, arm_drag=0.0), pose, weapons=None)
    gate(np.array_equal(own.worlds, plain.worlds),
         "the cycle's own knobs with a weapon in the hand are the cycle with none")

    #  3 - the promise
    late = run(with_pose=False, arm_drag=0.0, weapon_chest_lag=lag)
    C = np.asarray(quiet.worlds[chest], float)
    shifted = wm.shifted_cycle(C, lag)
    worst = 0.0
    for f in range(n + 1):
        was = np.asarray(quiet.worlds[hand_r, f], float) @ np.linalg.inv(C[f])
        now = np.asarray(late.worlds[hand_r, f], float) @ np.linalg.inv(shifted[f])
        worst = max(worst, float(np.abs(now - was).max()))
    gate(worst < 1e-4, "the weapon sits on the chest of %.2f frames ago: %.2e" % (lag, worst))

    #  4 - and it really moves
    before = np.array([place(grip_p, m) for m in np.asarray(quiet.worlds[hand_r], float)])
    after = np.array([place(grip_p, m) for m in np.asarray(late.worlds[hand_r], float)])
    moved = max(float(np.linalg.norm(after[f] - before[f])) for f in range(n + 1))
    said = late.info["arms"]["overlap"]
    gate(moved > 0.5 and said["chest"] == ["r"],
         "the grip really trails: %.2f cm, the info names the side %s" % (moved, said["chest"]))

    #  5 - rotation 0, with NO LAG: the weapon is left on the cycle's mean heading (the animator's own
    #  report, 2026-11-03 - the strengths must act whether or not a lag is dialled)
    flat = run(with_pose=False, arm_drag=0.0, weapon_chest_rotation=0.0)
    steady_r = walk.steady_chest(C, 0.0, 1.0)
    worst_r = own_turn = 0.0
    for f in range(n + 1):
        want = (np.asarray(quiet.worlds[hand_r, f, :3, :3], float)
                @ C[f, :3, :3].T @ steady_r[f, :3, :3])
        worst_r = max(worst_r, turned(want, flat.worlds[hand_r, f, :3, :3]))
        own_turn = max(own_turn, turned(C[0, :3, :3], C[f, :3, :3]))
    gate(worst_r < 1e-3 < own_turn,
         "Chest rotation 0 leaves the weapon on the mean heading: %.2e deg (the chest turns %.2f)"
         % (worst_r, own_turn))

    #  6 - position 0, with NO LAG: a pure translation, minus the chest's own bob and sway
    still = run(with_pose=False, arm_drag=0.0, weapon_chest_position=0.0)
    steady_p = walk.steady_chest(C, 1.0, 0.0)
    worst_p = off = 0.0
    for f in range(n + 1):
        want = (np.asarray(quiet.worlds[hand_r, f, 3, :3], float)
                + steady_p[f, 3, :3] - C[f, 3, :3])
        worst_p = max(worst_p, float(np.linalg.norm(np.asarray(still.worlds[hand_r, f, 3, :3], float)
                                                    - want)))
        off = max(off, float(np.linalg.norm(steady_p[f, 3, :3] - C[f, 3, :3])))
    gate(worst_p < 1e-4 < off,
         "Chest position 0 takes the chest's bob and sway off the weapon: %.2e cm (it bobs %.2f)"
         % (worst_p, off))

    #  7 - and the promise is not trivially true: the hand swings against the chest in the quiet run
    rel = [np.asarray(quiet.worlds[hand_r, f], float) @ np.linalg.inv(C[f]) for f in range(n + 1)]
    own = max(float(np.linalg.norm(rel[f][3, :3] - rel[0][3, :3])) for f in range(n + 1))
    gate(own > 1.0, "the hand swings against the chest, so gate 3 is a real constraint: %.2f cm" % own)

    #  8 - the bones
    worst_len = 0.0
    for side, chain in chains.items():
        for a, b in zip(chain, chain[1:]):
            for f in range(n + 1):
                was = float(np.linalg.norm(quiet.worlds[b, f, 3, :3] - quiet.worlds[a, f, 3, :3]))
                now = float(np.linalg.norm(late.worlds[b, f, 3, :3] - late.worlds[a, f, 3, :3]))
                worst_len = max(worst_len, abs(now - was))
    gate(worst_len < 1e-4, "every arm bone keeps its length: %.2e cm" % worst_len)

    #  9 - the loop
    travel = (quiet.worlds[hand_r, n, 3, :3] - quiet.worlds[hand_r, 0, 3, :3])
    seam = max(float(np.abs(late.worlds[hand_r, n, :3, :3] - late.worlds[hand_r, 0, :3, :3]).max()),
               float(np.abs(late.worlds[hand_r, n, 3, :3] - late.worlds[hand_r, 0, 3, :3]
                            - travel).max()))
    gate(seam < 1e-4, "the loop closes: %.2e" % seam)

    #  10 - 2H
    bound = run(with_pose=False, arm_drag=0.0, weapon_chest_lag=lag, weapon_hold=1.0)
    loose = run(with_pose=False, arm_drag=0.0)
    offs = [np.asarray(bound.worlds[hand_l, f], float)
            @ np.linalg.inv(np.asarray(bound.worlds[hand_r, f], float)) for f in range(n + 1)]
    worst_hold = max(float(np.abs(offs[f] - offs[0]).max()) for f in range(n + 1))
    free = [np.asarray(loose.worlds[hand_l, f], float)
            @ np.linalg.inv(np.asarray(loose.worlds[hand_r, f], float)) for f in range(n + 1)]
    swung = max(float(np.linalg.norm(free[f][3, :3] - free[0][3, :3])) for f in range(n + 1))
    gate(worst_hold < 1e-3 and bound.info["arms"]["overlap"]["hold"] == ["l"],
         "2H holds the free hand at its frame-0 offset: %.2e (free it swings %.2f cm)"
         % (worst_hold, swung))

    #  11 - Balance
    carried = walk.evaluate(dict(base, arm_drag=0.0, balance=1.0,
                                 weapon_chest_lag=lag, weapon_chest_lag_l=lag, weapon_chest_lag_r=lag),
                            pose, weapons=held)
    plain_carry = walk.evaluate(dict(base, arm_drag=0.0, balance=1.0), pose, weapons=held)
    pelvis = walk.index["pelvis"]
    apart = float(np.abs(np.asarray(carried.worlds[pelvis], float)[:, 3, :3]
                         - np.asarray(plain_carry.worlds[pelvis], float)[:, 3, :3]).max())
    gate(apart > 1e-9, "Balance carries the hips differently with the pass on: %.4f cm" % apart)

    #  12 - under the animator's own two-handed card: the hold is kept through the pass
    if pose is not None:
        held_quiet = run(arm_drag=0.0)
        held_late = run(arm_drag=0.0, weapon_chest_lag=lag)
        worst_hold = 0.0
        for f in range(n + 1):
            a = (np.asarray(held_quiet.worlds[hand_l, f], float)
                 @ np.linalg.inv(np.asarray(held_quiet.worlds[hand_r, f], float)))
            b = (np.asarray(held_late.worlds[hand_l, f], float)
                 @ np.linalg.inv(np.asarray(held_late.worlds[hand_r, f], float)))
            worst_hold = max(worst_hold, float(np.abs(a - b).max()))
        gate(worst_hold < 1e-3, "the card's two-handed hold is kept through the pass: %.2e" % worst_hold)
        #  13 - and what the animator asked for in words: with the arms stilled by the card's own grip,
        #  0 / 0 hangs the weapon in the air - it keeps nothing of the body but the walk's locomotion
        hung = run(arm_drag=0.0, weapon_chest_rotation=0.0, weapon_chest_position=0.0)
        hung_p = np.array([place(grip_p, m) for m in np.asarray(hung.worlds[hand_r], float)])
        held_p = np.array([place(grip_p, m) for m in np.asarray(held_quiet.worlds[hand_r], float)])
        per_hung = (hung_p[n] - hung_p[0]) / float(n)
        per_held = (held_p[n] - held_p[0]) / float(n)
        wander = max(float(np.linalg.norm(hung_p[f] - hung_p[0] - per_hung * f)) for f in range(n + 1))
        was = max(float(np.linalg.norm(held_p[f] - held_p[0] - per_held * f)) for f in range(n + 1))
        gate(wander < 0.5 < was,
             "0 / 0 hangs the weapon in the air: it wanders %.3f cm off its line (the body carries it %.2f)"
             % (wander, was))
        #  14 - the pose's own arm chip reaches the Weapon tab (2026-11-03): with Arm L out of the pose,
        #  2H cannot bind that hand and nothing of the weapon's passes moves it
        bones = wcards.read_card(os.path.join(LIBRARY, CARD))[1]
        whole = wp.prepare(walk, statics, bones, wm, wt)
        without = wp.filtered(whole, [part for part in sw.ALL_PARTS if part != "arm_l"])

        def one_armed(**over):
            ks = dict(base, elbow_add=BENT, elbow_add_l=BENT, elbow_add_r=BENT, balance=0.0)
            for name, value in over.items():
                ks[name] = value
                if name in wm.SIDED:
                    ks[name + "_l"] = ks[name + "_r"] = value
            return walk.evaluate(ks, without, weapons=held)

        bare = one_armed(arm_drag=0.0)
        worked = one_armed(arm_drag=0.0, weapon_chest_lag=lag, weapon_hold=1.0)
        left_moved = max(float(np.linalg.norm(worked.worlds[hand_l, f, 3, :3]
                                              - bare.worlds[hand_l, f, 3, :3])) for f in range(n + 1))
        right_moved = max(float(np.linalg.norm(worked.worlds[hand_r, f, 3, :3]
                                               - bare.worlds[hand_r, f, 3, :3])) for f in range(n + 1))
        said_hold = ((worked.info.get("arms") or {}).get("overlap") or {})["hold"]
        gate(left_moved < 1e-9 and not said_hold and right_moved > 0.5,
             "Arm L out of the pose: the Weapon knobs leave it alone (%.2e cm) while the right one works "
             "(%.2f cm), 2H binds nobody" % (left_moved, right_moved))
    else:
        gate(True, "no card in the library: the two-handed hold is not measured here")
        gate(True, "no card in the library: the hung weapon is not measured here")
        gate(True, "no card in the library: the arm chip is not measured here")
    return lag


# ------------------------------------------------------------------ keys

def phase_keys(lag_frames):
    print("\n-- keys: the whole road onto a plain Manny UE5 skeleton, no rig")
    root, weapon = add_walker()
    gate(not any(cmds.objExists(n) for n in cmds.ls("*ControlSet*") or ["x"]),
         "the walker is a bare skeleton: no rig in the scene")

    def press(ms, share=None):
        want = (1.0 if HAS_CARD else 0.0) if share is None else share
        params = sw.normal_params(dict(BASE, pose=want))
        changes = dict(params["changes"])
        pins = set(params["pins"])
        changes["whip"] = ["offset", -gait.P["whip"].default]
        pins.add("whip")
        #  the elbows bent, the reason the model phase bends them: an arm at full stretch cannot follow a
        #  hand the pass moves - two_bone clamps it on its line and the promise gives by centimetres
        changes["elbow"] = ["offset", BENT]
        pins.add("elbow")
        if ms:
            changes["weapon_chest_lag"] = ["offset", ms]
            pins.add("weapon_chest_lag")
        params["changes"], params["pins"] = changes, sorted(pins)
        params["in_place"] = 0.0
        #  the physics helpers off: Balance's carry moves the BODY when the arms move late (0.08 cm,
        #  measured), and the chest the promise is read against must be the same in both presses
        params["physics"] = False
        return sw.apply(root, WALK, params=params, pose_card=CARD if HAS_CARD else None)

    quiet, _, said_quiet = press(0.0)
    #  the take's own window, as the walk keyed it (the playback range is not it: Maya's own start is 1)
    start, frames = sw.memo_of(root)["start"], quiet.frames
    print("   (the take: start %s, %d frames, playback %s..%s)"
          % (start, frames, cmds.playbackOptions(query=True, minTime=True),
             cmds.playbackOptions(query=True, maxTime=True)))
    chest = [p for p in (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
             if p.rsplit("|", 1)[-1].split(":")[-1] == "spine_05"]
    hand = [p for p in (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
            if p.rsplit("|", 1)[-1].split(":")[-1] == "hand_r"][0]
    chest = chest[0] if chest else hand
    was_chest = np.array([world(chest, start + f) for f in range(frames + 1)])
    was_hand = np.array([world(hand, start + f) for f in range(frames + 1)])

    said = press(MS)[2]
    now_chest = np.array([world(chest, start + f) for f in range(frames + 1)])
    now_hand = np.array([world(hand, start + f) for f in range(frames + 1)])
    gate(float(np.abs(now_chest - was_chest).max()) < 1e-6,
         "the body itself is untouched: the chest %.2e" % float(np.abs(now_chest - was_chest).max()))
    shifted = wm.shifted_cycle(was_chest, lag_frames)
    worst = 0.0
    for f in range(frames + 1):
        a = was_hand[f] @ np.linalg.inv(was_chest[f])
        b = now_hand[f] @ np.linalg.inv(shifted[f])
        worst = max(worst, float(np.abs(a - b).max()))
    gate(worst < 0.05, "the keys put the weapon on the chest of %.2f frames ago: %.4f" % (lag_frames, worst))
    moved = max(float(np.linalg.norm(now_hand[f][3, :3] - was_hand[f][3, :3])) for f in range(frames + 1))
    gate(moved > 0.5, "the hand really trails: %.2f cm" % moved)
    gate("trails the chest" in said, "the line says it: %s" % said.strip().splitlines()[0][:160])
    gate("no weapon in the hands" not in said_quiet, "0 ms says nothing of the weapon")

    #  and with the pose off, where the arms swing against the chest: the promise is a real constraint
    bare_quiet = press(0.0, share=0.0)[0]
    bare_start, bare_frames = sw.memo_of(root)["start"], bare_quiet.frames
    q_chest = np.array([world(chest, bare_start + f) for f in range(bare_frames + 1)])
    q_hand = np.array([world(hand, bare_start + f) for f in range(bare_frames + 1)])
    press(MS, share=0.0)
    l_hand = np.array([world(hand, bare_start + f) for f in range(bare_frames + 1)])
    bare_shift = wm.shifted_cycle(q_chest, lag_frames)
    worst_bare = swing = 0.0
    for f in range(bare_frames + 1):
        a = q_hand[f] @ np.linalg.inv(q_chest[f])
        b = l_hand[f] @ np.linalg.inv(bare_shift[f])
        worst_bare = max(worst_bare, float(np.abs(a - b).max()))
        swing = max(swing, float(np.linalg.norm(a[3, :3] - (q_hand[0] @ np.linalg.inv(q_chest[0]))[3, :3])))
    gate(worst_bare < 0.5 and swing > 1.0,
         "with the arms swinging (%.1f cm against the chest) the keys keep the promise: %.4f"
         % (swing, worst_bare))


def main():
    lag = None
    if "model" in PHASES:
        lag = phase_model()
    if "keys" in PHASES:
        if lag is None:
            walk = sw.load_walk(WALK, sw.normal_params(BASE)["clean"])[0]
            lag = MS * walk.fps / 1000.0
        phase_keys(lag)
    print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": %s" % FAILED) if FAILED else ""))
    shutil.rmtree(TEMP, ignore_errors=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
