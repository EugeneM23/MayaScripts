"""verify_walk_weapon_aim.py - Walk Builder's Aim target, in mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_weapon_aim.py

The animator, with an example on port 7005 (2026-11-10): the weapon in Aim Mode, its aim target's keys
thinned out «для придания веса оружию» - «Сделай ручку которая будет имитировать этот эффект 1 - вся
анимация 0 - аим таргет полностью статичен». Spec:
docs/superpowers/specs/2026-11-10-walk-weapon-aim-target-design.md. Three phases:

  example  the example's own tracks (weapon_aim_example.json.gz, read off their scene): the aim target's
           track from before they thinned it is rebuilt from the FK wrist, and the knob's own arithmetic
           (model.damped_points) is put on it - what the animator did by hand against what 0 gives.
  model    the pass's promise on a COPY of the animator's walks folder, their own cycle under their
           two-handed card with a Long Sword's blade in the right hand: 1 the identity matrix for matrix,
           the blade's line through a target keeping the asked share, the grip unmoved, the hold kept,
           the bones whole, the loop closed, Balance seeing it, and the weapon-bone lever.
  keys     the whole road through scene.apply onto a plain Manny UE5 skeleton with a Long Sword in its
           right hand: the weapon's own world track read back off the scene keeps the same promise.

Phases can be named on the command line; the default runs all three.
"""
import gzip
import json
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
EXAMPLE = os.path.join(HERE, "weapon_aim_example.json.gz")
BENT = 70.0          # deg: the elbows bent so the arm can follow its hand (a stretched arm is clamped on its line)
BASE = {"changes": {"tempo": ["ratio", 0.8709677419354839]}, "pins": ["tempo"], "in_place": 1.0,
        "physics": True}
PHASES = tuple(a for a in sys.argv[1:] if not a.startswith("-")) or ("example", "model", "keys")

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


def place(local, mats):
    """A point of a frame's own in the world, per frame (row vectors)."""
    return np.array([np.asarray(local, float) @ m[:3, :3] + m[3, :3] for m in mats])


def still(points):
    """A cycle of points with its linear travel out, the closing frame dropped."""
    n = len(points) - 1
    per = (points[n] - points[0]) / float(n)
    return np.array([points[f] - per * f for f in range(n)])


def miss(G, P, targets):
    """How far the blade's line - from the grip G through its own point P - passes from its target, the
    worst frame (cm); inf where a target lies behind the grip."""
    worst = 0.0
    for f in range(len(G)):
        u = (P[f] - G[f]) / np.linalg.norm(P[f] - G[f])
        to = targets[f] - G[f]
        if float(np.dot(to, u)) <= 0.0:
            return float("inf")
        worst = max(worst, float(np.linalg.norm(np.cross(u, to))))
    return worst


def swing(G, P):
    """The most the blade's direction stands off its own mean over the cycle (deg)."""
    d = P - G
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    mean = d.mean(axis=0)
    mean /= np.linalg.norm(mean)
    return float(np.degrees(np.arccos(np.clip(d @ mean, -1.0, 1.0))).max())


def harmonic(points, h):
    """A cycle of points' amplitude at its h-th harmonic, the largest axis (cm)."""
    flat = still(points)
    spec = np.abs(np.fft.rfft(flat - flat.mean(axis=0), axis=0)) * 2.0 / len(flat)
    return float(spec[h].max())


# ------------------------------------------------------------------ example

def phase_example():
    print("\n-- example: the animator's own scene, the target they thinned against the knob's arithmetic")
    if not os.path.isfile(EXAMPLE):
        print("   %s is not here - skipped" % EXAMPLE)
        return
    with gzip.open(EXAMPLE, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    F = dict((k, np.array(v, float).reshape(-1, 4, 4)) for k, v in data["frames"].items())
    n = len(F["weapon"]) - 1
    keys, reach = data["target_keys"], data["aim_distance"]

    def rot(k):
        r = F[k][:, :3, :3].copy()
        return r / np.linalg.norm(r, axis=2, keepdims=True)

    Rw, Rh = rot("weapon"), rot("fkx_wrist_r")
    #  the weapon's turn from before the aim: the FK wrist (it still plays the take) times a constant,
    #  read at the target's kept keys - where the aimed weapon is the animation's own
    Cs = [Rw[f] @ Rh[f].T for f in keys]
    spread = max(math.degrees(float(np.linalg.norm(wm.log_rot(Cs[0].T @ C)))) for C in Cs)
    G = F["weapon"][:, 3, :3]
    was_target = G + np.array([(Cs[0] @ Rh[f])[1] for f in range(n + 1)]) * reach
    now_target = F["target"][:, 3, :3]
    at_keys = max(float(np.linalg.norm(was_target[f] - now_target[f])) for f in keys)
    gate(spread < 0.01 and at_keys < 0.01,
         "the target's track from before is known: the FK wrist times one constant (%.4f deg apart at the "
         "kept keys), on the kept keys to %.4f cm" % (spread, at_keys))
    strides = 4                               # read off the feet: four strides in the 76 frames
    before, after = harmonic(was_target, strides), harmonic(now_target, strides)
    gate(before > 10.0 and after < 0.1 * before,
         "what the animator took out is the stride's own swing: %.1f cm of amplitude there before, %.1f after "
         "(the target's range %.0f -> %.0f cm)" % (before, after, float(np.ptp(was_target, axis=0).max()),
                                                    float(np.ptp(now_target, axis=0).max())))
    same = wm.damped_points(was_target, 1.0)
    gate(np.array_equal(same, was_target), "the knob at 1 is the target's whole animation, point for point")
    static = wm.damped_points(was_target, 0.0)
    gate(float(np.ptp(still(static), axis=0).max()) < 1e-9 and harmonic(static, strides) < 1e-9,
         "the knob at 0 is a static target: it moves %.1e cm" % float(np.ptp(still(static), axis=0).max()))
    print("   the blade's swing off its own mean, the grip playing the whole animation:")
    print("      the animation as it was   %.1f deg" % swing(G, was_target))
    print("      the animator's example    %.1f deg (a slow drift, nothing at the stride)" % swing(G, now_target))
    for keep in (0.5, 0.25, 0.0):
        print("      Aim target %.2f           %.1f deg" % (keep, swing(G, wm.damped_points(was_target, keep))))
    gate(swing(G, static) < swing(G, now_target) < swing(G, was_target) + 1e-9,
         "a static target calms the blade further than the example's own (%.1f < %.1f < %.1f deg)"
         % (swing(G, static), swing(G, now_target), swing(G, was_target)))


# ------------------------------------------------------------------ model

TEMP = tempfile.mkdtemp(prefix="weapon_aim_")
COPY = os.path.join(TEMP, "SkeldarWalks")
HAS_CARD = bool(CARD) and os.path.isdir(os.path.join(LIBRARY, CARD))


def ready_walks():
    global WALK
    if not os.path.isdir(MINE):
        print("   no walks folder at %s - skipped" % MINE)
        return False
    if not os.path.isdir(COPY):
        shutil.copytree(MINE, COPY)
    sw.WALKS = COPY
    if HAS_CARD:
        cmds.optionVar(stringValue=("skeldarPoseLibraryRoot", LIBRARY))
    if not sw.walk_exists(WALK):
        names = sw.walk_names()
        if not names:
            print("   no walk to read in %s - skipped" % MINE)
            return False
        print("   note: %s is not in the folder - using %s" % (WALK, names[0]))
        WALK = names[0]
    if not HAS_CARD:
        print("   %s is not in %s - skipped (the knob acts under an additive pose)" % (CARD, LIBRARY))
    return HAS_CARD


def phase_model():
    print("\n-- model: the pass's promise on the animator's own cycle under their two-handed card")
    cmds.file(new=True, force=True)
    if not ready_walks():
        return
    walk, statics = sw.load_walk(WALK, sw.normal_params(BASE)["clean"])[:2]
    bones = wcards.read_card(os.path.join(LIBRARY, CARD))[1]
    pose = wp.filtered(wp.prepare(walk, statics, bones, wm, wt), sw.ALL_PARTS)
    base = sw.params_knobs(walk, sw.normal_params(dict(BASE, pose=1.0)))[0]
    base = dict(base, in_place=0.0)             # In place is a post-pass (trap 318): the cycle as it travels
    held = {"r": {"grip": (2.0, -3.0, 1.0), "tip": (2.0, -3.0, 116.0)}}      # the Long Sword's own blade
    grip = np.array(held["r"]["grip"])
    aim = grip + (np.array(held["r"]["tip"]) - grip) * wm.AIM_REACH

    def run(weapons=held, **over):
        ks = dict(base, elbow_add=BENT, elbow_add_l=BENT, elbow_add_r=BENT, balance=0.0, arm_drag=0.0)
        for name, value in over.items():        # a sided knob on both sides too (trap 317)
            ks[name] = value
            if name in wm.SIDED:
                ks[name + "_l"] = ks[name + "_r"] = value
        return walk.evaluate(ks, pose, weapons=weapons)

    chains = walk._arm_chains()
    hand_r, hand_l = chains["r"][-1], chains["l"][-1]
    quiet = run()
    n = quiet.frames
    Hq = np.asarray(quiet.worlds[hand_r], float)
    Gq, Tq = place(grip, Hq), place(aim, Hq)

    gate(np.array_equal(run(weapon_aim=1.0).worlds, quiet.worlds),
         "Aim target 1 is the walk itself, matrix for matrix")
    own = walk.evaluate(dict(walk.own_knobs(), in_place=0.0), pose, weapons=held)
    plain = walk.evaluate(dict(walk.own_knobs(), in_place=0.0), pose, weapons=None)
    gate(np.array_equal(own.worlds, plain.worlds),
         "the cycle's own knobs with a weapon in the hand are the cycle with none")
    moves = float(np.ptp(still(Tq), axis=0).max())
    gate(moves > 1.0, "the blade's target moves at all on this cycle: %.2f cm (so the gates below can fail)"
         % moves)

    for keep in (0.0, 0.5):
        got = run(weapon_aim=keep)
        H = np.asarray(got.worlds[hand_r], float)
        want = wm.damped_points(Tq, keep)
        control, off = miss(Gq, Tq, want), miss(place(grip, H), place(aim, H), want)
        gate(off < 1e-4 < control,
             "Aim target %.1f: the blade's line passes %.2e cm from a target keeping that share (the walk's "
             "own blade misses it by %.2f cm)" % (keep, off, control))
        moved = float(np.abs(place(grip, H) - Gq).max())
        gate(moved < 1e-4, "   ...and the grip plays the whole animation: it moves %.2e cm" % moved)
        if keep == 0.0:
            static = got
            said = got.info["arms"]["overlap"]["aim"]
            gate(said["lever"] == {"r": "weapon"} and said["deg"] > 0.5,
                 "   ...the blade swung up to %.1f deg to get there, the info names the weapon's lever"
                 % said["deg"])
            print("      the blade's swing off its mean: %.1f deg as the walk has it, %.1f at Aim target 0"
                  % (swing(Gq, Tq), swing(place(grip, H), place(aim, H))))

    Hs_r, Hs_l = np.asarray(static.worlds[hand_r], float), np.asarray(static.worlds[hand_l], float)
    Hq_l = np.asarray(quiet.worlds[hand_l], float)
    hold = max(float(np.abs(Hs_l[f] @ np.linalg.inv(Hs_r[f]) - Hq_l[f] @ np.linalg.inv(Hq[f])).max())
               for f in range(n + 1))
    carried = float(np.linalg.norm(Hs_l[:, 3, :3] - Hq_l[:, 3, :3], axis=1).max())
    gate(hold < 1e-6 and carried > 0.05,
         "two hands keep their hold: %.2e (the other hand is carried %.2f cm)" % (hold, carried))
    worst_len = 0.0
    for side, chain in chains.items():
        for a, b in ((chain[0], chain[1]), (chain[1], chain[2])):
            d = np.linalg.norm(static.worlds[b, :, 3, :3] - static.worlds[a, :, 3, :3], axis=1)
            worst_len = max(worst_len, float(np.ptp(d)))
    gate(worst_len < 1e-3, "the arms' bones keep their lengths: %.2e cm" % worst_len)
    loop = float(np.abs((static.worlds[:, n] - static.worlds[:, 0]) - (quiet.worlds[:, n] - quiet.worlds[:, 0])).max())
    gate(loop < 1e-6, "the loop closes as the walk's own: %.2e" % loop)
    body = [j for j, kind in enumerate(walk.kind) if kind in ("root", "pelvis", "leg", "spine", "head")]
    gate(float(np.abs(static.worlds[body] - quiet.worlds[body]).max()) < 1e-9,
         "the body itself is untouched: %.2e" % float(np.abs(static.worlds[body] - quiet.worlds[body]).max()))

    free = run(weapon_hold=0.0)
    Hf = np.asarray(free.worlds[hand_r], float)
    aimed = np.asarray(run(weapon_hold=0.0, weapon_aim=0.0).worlds[hand_r], float)
    want = wm.damped_points(place(aim, Hf), 0.0)
    gate(miss(place(grip, aimed), place(aim, aimed), want) < 1e-4 < miss(place(grip, Hf), place(aim, Hf), want),
         "it needs no Hold: %.2e (the unheld blade misses by %.2f cm)"
         % (miss(place(grip, aimed), place(aim, aimed), want), miss(place(grip, Hf), place(aim, Hf), want)))

    with_balance = lambda v: walk.evaluate(dict(base, elbow_add=BENT, elbow_add_l=BENT, elbow_add_r=BENT,
                                                 arm_drag=0.0, weapon_aim=v, weapon_aim_l=v, weapon_aim_r=v),
                                           pose, weapons=held)
    pelvis = walk.index["pelvis"]
    carry = float(np.abs(with_balance(0.0).worlds[pelvis] - with_balance(1.0).worlds[pelvis]).max())
    gate(0.0 < carry < 2.0, "Balance sees the swung arms: the hips are carried %.4f cm differently" % carry)

    #  no weapon in the scene: the right hand's weapon bone stands for a 1 m blade
    bone = walk.index.get("weapon_r")
    if bone is None:
        print("   the walk has no weapon_r - the bone lever is not measured here")
    else:
        bare = run(weapons=None)
        got = run(weapons=None, weapon_aim=0.0)
        tip = np.array([0.0, 0.0, wm.AIM_BLADE * wm.AIM_REACH])
        Bq, Bg = np.asarray(bare.worlds[bone], float), np.asarray(got.worlds[bone], float)
        want = wm.damped_points(place(tip, Bq), 0.0)
        off = miss(Bg[:, 3, :3], place(tip, Bg), want)
        control = miss(Bq[:, 3, :3], place(tip, Bq), want)
        gate(off < 1e-4 < control and got.info["arms"]["overlap"]["aim"]["lever"] == {"r": "bone"},
             "with no weapon in the scene the weapon bone is the lever: %.2e (misses by %.2f cm unaimed)"
             % (off, control))
    text = wm.describe(static)
    gate("the blade aims at a static target" in text, "the line says it: ...%s"
         % text[text.find("the blade aims"):][:70])


# ------------------------------------------------------------------ keys

def world(node, frame):
    cmds.currentTime(frame, update=True)          # a real time change: the weapon's space is constrained
    return np.array(cmds.xform(node, query=True, worldSpace=True, matrix=True), float).reshape(4, 4)


def add_walker():
    """A Manny UE5 SKELETON with a Long Sword in its right hand: (root, the weapon)."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    character.add_character(catalog.character_for("Manny", "skeleton"))
    root = [p for p in cmds.ls(type="joint", long=True) if p.rsplit("|", 1)[-1] == "root"][0]
    said = equip.to_hand(root, "R", catalog.by_key("LongSword_02"))
    marked = [node for node in cmds.ls(transforms=True, long=True)
              if cmds.attributeQuery(bonedrive.MARKER, node=node, exists=True)]
    if not marked:
        raise RuntimeError("no weapon in the hand: %s" % said)
    return root, marked[0]


def phase_keys():
    print("\n-- keys: the whole road onto a plain Manny UE5 skeleton with a Long Sword in its right hand")
    if not ready_walks():
        return
    root, weapon = add_walker()
    lever = sw.weapons_in_hands(root)
    gate(sorted(lever) == ["r"], "the scene's reading: a weapon in the right hand (%s)" % sorted(lever))
    length = float(np.linalg.norm(np.array(lever["r"]["tip"]) - np.array(lever["r"]["grip"])))
    blade = np.array([0.0, length * wm.AIM_REACH, 0.0])       # along the model's own +Y, as Aim Mode reads it

    def press(keep):
        params = sw.normal_params(dict(BASE, pose=1.0))
        changes, pins = dict(params["changes"]), set(params["pins"])
        changes["whip"] = ["offset", -gait.P["whip"].default]
        changes["elbow"] = ["offset", BENT]
        pins.update(("whip", "elbow"))
        if keep < 1.0:
            changes["weapon_aim"] = ["offset", keep - 1.0]
            pins.add("weapon_aim")
        params["changes"], params["pins"] = changes, sorted(pins)
        params["in_place"] = 0.0
        params["physics"] = False              # Balance's carry moves the body when the arms move
        return sw.apply(root, WALK, params=params, pose_card=CARD)

    quiet = press(1.0)
    start, frames = sw.memo_of(root)["start"], quiet[0].frames
    was = np.array([world(weapon, start + f) for f in range(frames + 1)])
    Gq, Tq = was[:, 3, :3], place(blade, was)
    gate("the blade aims" not in quiet[2], "Aim target 1 says nothing of the blade")
    moves = float(np.ptp(still(Tq), axis=0).max())

    said = press(0.0)[2]
    now = np.array([world(weapon, start + f) for f in range(frames + 1)])
    want = wm.damped_points(Tq, 0.0)
    off, control = miss(now[:, 3, :3], place(blade, now), want), miss(Gq, Tq, want)
    gate(off < 0.25 < control,
         "the keys: the sword's own line passes %.4f cm from a static target (it moved %.1f cm; the walk's "
         "own blade misses by %.2f cm)" % (off, moves, control))
    grip_moved = float(np.linalg.norm(now[:, 3, :3] - Gq, axis=1).max())
    gate(grip_moved < 0.25, "the sword's grip plays the whole animation: it moves %.4f cm" % grip_moved)
    print("      the sword's swing off its mean: %.1f deg before, %.1f deg at Aim target 0"
          % (swing(Gq, Tq), swing(now[:, 3, :3], place(blade, now))))
    gate("the blade aims at a static target" in said,
         "the line says it: ...%s" % said[said.find("the blade aims"):][:60])

    press(0.5)
    half = np.array([world(weapon, start + f) for f in range(frames + 1)])
    want = wm.damped_points(Tq, 0.5)
    off = miss(half[:, 3, :3], place(blade, half), want)
    gate(off < 0.25, "a half: the sword's line passes %.4f cm from a target keeping half its motion" % off)


def main():
    if "example" in PHASES:
        phase_example()
    if "model" in PHASES:
        phase_model()
    if "keys" in PHASES:
        phase_keys()
    print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": %s" % FAILED) if FAILED else ""))
    shutil.rmtree(TEMP, ignore_errors=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
