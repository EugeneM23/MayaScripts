"""verify_walk_weapon_inherit.py - Walk Builder's Inherit, in mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_weapon_inherit.py

The animator (2026-11-10): «ручку которая будет контролировать процент холда 1 - 100% наследования как
сейчас 0 - 0 процентов полная статика». Spec:
docs/superpowers/specs/2026-11-10-walk-weapon-hold-inherit-design.md. Two phases, on a COPY of the
animator's walks folder (the harness is verify_walk_weapon_aim's):

  model  their own cycle under their two-handed card: 1 the identity matrix for matrix, 0 the hand
         standing still in the travelling frame, a half on the chest's cycle keeping half its motion,
         Overlap reading that chest late, the hold kept, the bones whole, the loop closed, the body
         untouched, Balance seeing it.
  keys   the whole road through scene.apply onto a plain Manny UE5 skeleton with a Long Sword in its right
         hand: the SWORD's own world track read back off the scene stands still at 0.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PHASES = tuple(a for a in sys.argv[1:] if not a.startswith("-")) or ("model", "keys")
sys.argv = sys.argv[:1]                    # the harness reads its own phases off the command line

import verify_walk_weapon_aim as A         # noqa: E402  (initializes Maya, loads the repository's plugin)

cmds, sw, wm, wt, wp, wcards, gait = A.cmds, A.sw, A.wm, A.wt, A.wp, A.wcards, A.gait
gate = A.gate
MS = 150.0                                 # the Overlap the lag gate measures at


def wander(mats):
    """How far a cycle of matrices moves with its linear travel out: (cm, deg), the worst frame against
    the first."""
    n = len(mats) - 1
    per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
    cm = max(float(np.linalg.norm((mats[f, 3, :3] - per * f) - mats[0, 3, :3])) for f in range(n + 1))
    deg = max(math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(mats[0, :3, :3]).T
                                                           @ wm.orthonormal(mats[f, :3, :3])))))
              for f in range(n + 1))
    return cm, deg


def phase_model():
    print("\n-- model: the pass's promise on the animator's own cycle under their two-handed card")
    cmds.file(new=True, force=True)
    if not A.ready_walks():
        return
    walk, statics = sw.load_walk(A.WALK, sw.normal_params(A.BASE)["clean"])[:2]
    bones = wcards.read_card(os.path.join(A.LIBRARY, A.CARD))[1]
    pose = wp.filtered(wp.prepare(walk, statics, bones, wm, wt), sw.ALL_PARTS)
    base = dict(sw.params_knobs(walk, sw.normal_params(dict(A.BASE, pose=1.0)))[0], in_place=0.0)

    def run(balance=0.0, **over):
        ks = dict(base, elbow_add=A.BENT, elbow_add_l=A.BENT, elbow_add_r=A.BENT, balance=balance, arm_drag=0.0)
        for name, value in over.items():        # a sided knob on both sides too (trap 317)
            ks[name] = value
            if name in wm.SIDED:
                ks[name + "_l"] = ks[name + "_r"] = value
        return walk.evaluate(ks, pose)

    chains = walk._arm_chains()
    hand_r, hand_l, chest = chains["r"][-1], chains["l"][-1], walk._chest_joint()
    quiet = run()
    n = quiet.frames
    C = np.asarray(quiet.worlds[chest], float)
    Hq = np.asarray(quiet.worlds[hand_r], float)
    offset = Hq[0] @ np.linalg.inv(C[0])

    def promised(keep, lag=0.0):
        carrier = wm.shifted_cycle(walk.steady_chest(C, keep, keep), lag)
        return np.array([offset @ carrier[f] for f in range(n + 1)])

    gate(np.array_equal(run(weapon_inherit=1.0).worlds, quiet.worlds),
         "Inherit 1 is the walk itself, matrix for matrix")
    rides = float(np.abs(Hq - promised(1.0)).max())
    cm, deg = wander(Hq)
    gate(rides < 1e-6 and cm > 1.0 and deg > 1.0,
         "at 1 the hand rides the chest rigidly (%.2e) and so moves %.2f cm, turns %.2f deg" % (rides, cm, deg))

    still = run(weapon_inherit=0.0)
    Hs = np.asarray(still.worlds[hand_r], float)
    s_cm, s_deg = wander(Hs)
    gate(s_cm < 1e-4 and s_deg < 1e-4,
         "Inherit 0 is full statics: the hand moves %.2e cm, turns %.2e deg" % (s_cm, s_deg))
    gate(float(np.abs(Hs - promised(0.0)).max()) < 1e-4,
         "   ...standing where its own offset puts it on the chest's mean pose: %.2e"
         % float(np.abs(Hs - promised(0.0)).max()))

    half = np.asarray(run(weapon_inherit=0.5).worlds[hand_r], float)
    h_cm, h_deg = wander(half)
    gate(float(np.abs(half - promised(0.5)).max()) < 1e-4 and s_cm < h_cm < cm,
         "a half rides the chest's cycle keeping half its motion: %.2e (it moves %.2f cm, turns %.2f deg)"
         % (float(np.abs(half - promised(0.5)).max()), h_cm, h_deg))

    lag = MS * walk.fps / 1000.0
    late = np.asarray(run(weapon_inherit=0.5, weapon_overlap=lag).worlds[hand_r], float)
    gate(float(np.abs(late - promised(0.5, lag)).max()) < 1e-4 and float(np.abs(late - half).max()) > 0.05,
         "Overlap reads that same chest %.1f frames late: %.2e" % (lag, float(np.abs(late - promised(0.5, lag)).max())))

    Hs_l, Hq_l = np.asarray(still.worlds[hand_l], float), np.asarray(quiet.worlds[hand_l], float)
    hold = max(float(np.abs(Hs_l[f] @ np.linalg.inv(Hs[f]) - Hq_l[f] @ np.linalg.inv(Hq[f])).max())
               for f in range(n + 1))
    gate(hold < 1e-6, "two hands keep their hold: %.2e" % hold)
    worst_len = 0.0
    for side, chain in chains.items():
        for a, b in ((chain[0], chain[1]), (chain[1], chain[2])):
            d = np.linalg.norm(still.worlds[b, :, 3, :3] - still.worlds[a, :, 3, :3], axis=1)
            worst_len = max(worst_len, float(np.ptp(d)))
    gate(worst_len < 1e-3, "the arms' bones keep their lengths: %.2e cm" % worst_len)
    loop = float(np.abs((still.worlds[:, n] - still.worlds[:, 0]) - (quiet.worlds[:, n] - quiet.worlds[:, 0])).max())
    gate(loop < 1e-6, "the loop closes as the walk's own: %.2e" % loop)
    body = [j for j, kind in enumerate(walk.kind) if kind in ("root", "pelvis", "leg", "spine", "head")]
    gate(float(np.abs(still.worlds[body] - quiet.worlds[body]).max()) < 1e-9,
         "the body itself is untouched: %.2e" % float(np.abs(still.worlds[body] - quiet.worlds[body]).max()))
    off = run(weapon_hold=0.0)
    gate(np.array_equal(run(weapon_hold=0.0, weapon_inherit=0.0).worlds, off.worlds),
         "with Hold off Inherit does nothing, matrix for matrix")
    pelvis = walk.index["pelvis"]
    carry = float(np.abs(run(balance=base.get("balance", 1.0) or 1.0, weapon_inherit=0.0).worlds[pelvis]
                         - run(balance=base.get("balance", 1.0) or 1.0).worlds[pelvis]).max())
    gate(0.0 < carry < 3.0, "Balance sees the still arms: the hips are carried %.4f cm differently" % carry)
    text = wm.describe(still)
    gate("both hands stand still: none of the chest's motion" in text,
         "the line says it: ...%s" % text[text.find("both hands"):][:55])
    gate("ride the chest at 50 % of its motion" in wm.describe(run(weapon_inherit=0.5)),
         "...and a share: ride the chest at 50 % of its motion")


def phase_keys():
    print("\n-- keys: the whole road onto a plain Manny UE5 skeleton with a Long Sword in its right hand")
    if not A.ready_walks():
        return
    root, weapon = A.add_walker()

    def press(keep):
        params = sw.normal_params(dict(A.BASE, pose=1.0))
        changes, pins = dict(params["changes"]), set(params["pins"])
        changes["whip"] = ["offset", -gait.P["whip"].default]
        changes["elbow"] = ["offset", A.BENT]
        pins.update(("whip", "elbow"))
        if keep < 1.0:
            changes["weapon_inherit"] = ["offset", keep - 1.0]
            pins.add("weapon_inherit")
        params["changes"], params["pins"] = changes, sorted(pins)
        params["in_place"] = 0.0
        params["physics"] = False              # Balance's carry moves the body when the arms move
        return sw.apply(root, A.WALK, params=params, pose_card=A.CARD)

    quiet = press(1.0)
    start, frames = sw.memo_of(root)["start"], quiet[0].frames
    read = lambda: np.array([A.world(weapon, start + f) for f in range(frames + 1)])
    was = read()
    cm, deg = wander(was)
    gate("of its motion" not in quiet[2] and "stand still" not in quiet[2] and "ride the chest" in quiet[2],
         "Inherit 1 says what Hold said: ...%s" % quiet[2][quiet[2].find("both hands"):][:30])

    said = press(0.0)[2]
    now = read()
    s_cm, s_deg = wander(now)
    gate(s_cm < 0.05 and s_deg < 0.05 and cm > 1.0,
         "the keys: the sword stands still - it moves %.4f cm and turns %.4f deg (%.2f cm and %.2f deg at 1)"
         % (s_cm, s_deg, cm, deg))
    gate("both hands stand still" in said, "the line says it: ...%s" % said[said.find("both hands"):][:55])

    press(0.5)
    h_cm, h_deg = wander(read())
    gate(s_cm < h_cm < cm, "a half: the sword moves %.2f cm, turns %.2f deg" % (h_cm, h_deg))

    press(1.0)
    back = float(np.abs(read() - was).max())
    gate(back < 1e-6, "back at 1 the sword is where it was: %.2e" % back)


def main():
    if "model" in PHASES:
        phase_model()
    if "keys" in PHASES:
        phase_keys()
    print("\n%d of %d gates failed%s" % (len(A.FAILED), A.COUNT[0], (": %s" % A.FAILED) if A.FAILED else ""))
    A.shutil.rmtree(A.TEMP, ignore_errors=True)
    return 1 if A.FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
