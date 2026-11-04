"""verify_walk_two_handed.py - a two-handed hold is 2H, not the pose. In mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_two_handed.py

The animator (2026-11-04): «Я не понимаю почему сейчас работает по разному один и тот же функционал с
разными позами у меча руки стоят на месте при ручках в 0 у ножа дагера сильно двигаются. Наши ручки не
должны зависит от позы». The design:
docs/superpowers/specs/2026-11-04-walk-two-handed-not-the-pose-design.md.

Their own cycle under their own two pose cards and their own card state, where 2H is ON: with the fix the
dagger card reads the sword card's numbers, and the control is the same card with 2H off. Every gate
measures what the eye reads: the hand in the PELVIS's frame and each finger's own local turn.

Row vectors: a local is w[j] @ w[parent].T, never the other way round (trap 225).
"""
import math
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
LIBRARY = os.environ.get("POSE_LIBRARY", "C:/Users/MY PC/Documents/maya/scripts/SkeldarAnim/poses")
WALK = os.environ.get("HANDS_WALK", "own:7833074715b34c33")
SWORD = os.environ.get("HANDS_SWORD", "LongSword_Idle_3P.pose")
DAGGER = os.environ.get("HANDS_DAGGER", "DG_Idle.pose")
#  their card, read off userPrefs.mel 2026-11-03 20:48: the Chest chip on, Rotation 0, Position 0, 2H on
THEIRS = {"changes": {"weapon_chest": ["offset", 1.0], "weapon_chest_rotation": ["offset", -1.0],
                      "weapon_chest_position": ["offset", -1.0], "weapon_hold": ["offset", 1.0]},
          "pins": ["weapon_chest", "weapon_chest_position", "weapon_chest_rotation", "weapon_hold"],
          "physics": True}
HELD = {"r": {"grip": (2.0, -3.0, 1.0), "tip": (2.0, -3.0, 116.0)}}   # the Long Sword's own blade
LEFT = {"l": HELD["r"]}
FLOOR = 6.84          # deg: a still hand in the pelvis's frame on this cycle - the body's own turn
STILL = 0.05          # deg: what counts as a still finger

import maya.standalone                                        # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                      # noqa: E402

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))          # the repository's plugin, never the installed copy
from maya_walk import scene as sw                              # noqa: E402
from maya_walk import cards as wcards                          # noqa: E402
from maya_walk import pose as wp                               # noqa: E402

wm, gait = sw.wm, sw.gait
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


TEMP = tempfile.mkdtemp(prefix="walk_2h_")
COPY = os.path.join(TEMP, "SkeldarWalks")
shutil.copytree(sw.folder(), COPY)                             # never the animator's own folder
sw.WALKS = COPY
cmds.optionVar(stringValue=("skeldarPoseLibraryRoot", LIBRARY))
if not sw.walk_exists(WALK):
    print("no walk %s in %s - nothing to verify" % (WALK, sw.folder()))
    raise SystemExit(1)

walk, statics = sw.load_walk(WALK, sw.normal_params(THEIRS)["clean"])[:2]
chains = walk._arm_chains()
PELVIS = walk.index["pelvis"]
print("walk %s: %d frames at %.1f fps" % (WALK, walk.P, walk.fps))


def fingers(side):
    hand = chains[side][-1]
    out, queue = [], [hand]
    while queue:
        p = queue.pop(0)
        for j, par in enumerate(walk.parents):
            if par == p:
                if walk.kind[j] == "finger":
                    out.append(j)
                queue.append(j)
    return out


def spread(rots):
    mean = wm.orthonormal(np.mean(rots, axis=0))
    return max(math.degrees(float(np.linalg.norm(wm.log_rot(mean.T @ r)))) for r in rots)


def own_turn(res, j):
    w, p = res.worlds, walk.parents[j]
    return spread([w[j, f, :3, :3] @ w[p, f, :3, :3].T for f in range(w.shape[1])])


def in_pelvis(res, j):
    w = res.worlds
    return spread([w[j, f, :3, :3] @ w[PELVIS, f, :3, :3].T for f in range(w.shape[1])])


def read(res):
    """{side: (the hand in the pelvis's frame, the most any finger turns)} in degrees."""
    out = {}
    for side in ("l", "r"):
        fing = fingers(side)
        out[side] = (in_pelvis(res, chains[side][-1]),
                     max([own_turn(res, j) for j in fing] or [0.0]))
    return out


def card(name, parts=None):
    path = os.path.join(LIBRARY, name)
    if not os.path.isdir(path):
        return None
    bones = wcards.read_card(path)[1]
    return wp.filtered(wp.prepare(walk, statics, bones, wm, sw.wt),
                       sw.ALL_PARTS if parts is None else parts)


def run(pose, changes=(), drop=(), weapons=HELD):
    p = dict(THEIRS)
    p["changes"] = dict((n, v) for n, v in dict(THEIRS["changes"], **dict(changes)).items()
                        if n not in set(drop))
    p["pins"] = sorted((set(THEIRS["pins"]) | set(dict(changes))) - set(drop))
    ks = dict(sw.params_knobs(walk, sw.normal_params(dict(p, pose=1.0)))[0], in_place=0.0)
    return walk.evaluate(ks, pose, weapons=weapons)


def still(r, text):
    """Their own words: the hands stand on the body and the fingers do not flex."""
    return (abs(r["r"][0] - FLOOR) < 0.2 and abs(r["l"][0] - FLOOR) < 0.2
            and max(r["r"][1], r["l"][1]) < STILL), text


sword, dagger = card(SWORD), card(DAGGER)
if sword is None or dagger is None:
    print("missing a card in %s - nothing to verify" % LIBRARY)
    raise SystemExit(1)
NO_2H = ("weapon_hold",)

# ---- 1-2: their own card, both poses - the ask
s, d = read(run(sword)), read(run(dagger))
gate(*still(s, "the sword card's hands are still: %.2f / %.2f deg in the pelvis, fingers %.3f / %.3f"
            % (s["r"][0], s["l"][0], s["r"][1], s["l"][1])))
gate(*still(d, "and the dagger card's read the same at the same knobs: %.2f / %.2f deg, fingers "
            "%.3f / %.3f" % (d["r"][0], d["l"][0], d["r"][1], d["l"][1])))
gate(max(abs(d[side][i] - s[side][i]) for side in "lr" for i in (0, 1)) < 0.05,
     "the two poses agree to %.3f deg" % max(abs(d[side][i] - s[side][i])
                                             for side in "lr" for i in (0, 1)))

# ---- 4: the control - the same card with 2H off, which is what they saw
loose = read(run(dagger, drop=NO_2H))
gate(min(loose["r"][0], loose["l"][0]) > FLOOR + 3.0 and min(loose["r"][1], loose["l"][1]) > 5.0,
     "the control: with 2H off the dagger's hands move again - %.2f / %.2f deg, fingers %.2f / %.2f"
     % (loose["r"][0], loose["l"][0], loose["r"][1], loose["l"][1]))

# ---- 5: the sword card is untouched by the change (its own grip already held it)
s_off = read(run(sword, drop=NO_2H))
gate(max(abs(s_off[side][i] - s[side][i]) for side in "lr" for i in (0, 1)) < 1e-6,
     "the sword card reads the same with 2H off: its own grip holds it (%.2f / %.2f deg)"
     % (s_off["r"][0], s_off["l"][0]))

# ---- 6: the one-body spring follows the knob
gate(run(dagger).info["arms"]["grip"] and not run(dagger, drop=NO_2H).info["arms"]["grip"]
     and run(sword, drop=NO_2H).info["arms"]["grip"],
     "the one-body spring is on under 2H and off without it, and a pose's grip still has it")

# ---- 7: 2H with no weapon in the scene holds nothing
none = read(run(dagger, weapons={}))
gate(min(none["r"][0], none["l"][0]) > FLOOR + 3.0,
     "2H with no weapon in the scene binds nobody: %.2f / %.2f deg" % (none["r"][0], none["l"][0]))

# ---- 8: the weapon in the LEFT hand - the left carries it
seen = {}
real = walk._grip_motion


def spy(kin, n, chains_, w0, zeta, S, hold_side="r"):
    seen["side"] = hold_side
    return real(kin, n, chains_, w0, zeta, S, hold_side=hold_side)


walk._grip_motion = spy
try:
    left = read(run(dagger, weapons=LEFT))
finally:
    del walk._grip_motion
gate(seen.get("side") == "l" and (abs(left["r"][0] - FLOOR) < 0.5 and abs(left["l"][0] - FLOOR) < 0.5),
     "a weapon in the left hand is carried by the left (%s), the hands still: %.2f / %.2f deg"
     % (seen.get("side"), left["r"][0], left["l"][0]))

# ---- 9: an arm out of the pose plays the cycle - 2H cannot bind it
out = card(DAGGER, [p for p in sw.ALL_PARTS if p != "arm_l"])
r_out = read(run(out))
gate(r_out["l"][0] > FLOOR + 3.0 and r_out["l"][1] > 5.0,
     "the left arm out of the pose plays the cycle: %.2f deg, fingers %.2f"
     % (r_out["l"][0], r_out["l"][1]))

# ---- 10-11: the cycle still closes and the bones keep their lengths
res = run(dagger)
w = res.worlds
seam = max(float(np.max(np.abs(w[j, -1, :3, :3] - w[j, 0, :3, :3]))) for j in range(len(walk.names)))
gate(seam < 2e-3, "the loop still closes (worst rotation element %.2e)" % seam)
worst = 0.0
for side in ("l", "r"):
    chain = chains[side]
    for a, b in zip(chain[:-1], chain[1:]):
        lens = [float(np.linalg.norm(w[b, f, 3, :3] - w[a, f, 3, :3])) for f in range(w.shape[1])]
        worst = max(worst, max(lens) - min(lens))
gate(worst < 1e-4, "the arm bones keep their lengths (worst %.2e cm)" % worst)

# ---- 12: the line says the held weapon trails
gate("the held weapon trails" in wm.describe(res),
     "the line says it: %s" % [t for t in wm.describe(res).split(" | ") if "trail" in t])

print("\n%d gate(s) failed%s" % (len(FAILED), (": " + ", ".join(map(str, FAILED))) if FAILED else ""))
shutil.rmtree(TEMP, ignore_errors=True)
raise SystemExit(1 if FAILED else 0)
