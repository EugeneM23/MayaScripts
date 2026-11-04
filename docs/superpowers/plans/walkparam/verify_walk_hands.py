"""verify_walk_hands.py - Arms % and Hands % on the animator's own cycle, in mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_hands.py

The animator (2026-11-04): «нужен парамметр который будет контролировать процент анимации кистей с
оригинального цикла ... В позе с ножиком не удается получить статические руки при нулевых значениях
ручек в weapon». The design: docs/superpowers/specs/2026-11-04-walk-hands-from-the-cycle-design.md.

Their own cycle under their own two pose cards and their own card state (read off userPrefs.mel): the
sword card's grip stills its hands by itself (6.84 deg of hand in the pelvis's frame, 0.0 deg of
finger); the dagger card's do not (16.25 / 14.01 and 11.1 / 12.8). Every gate measures what the eye
reads: the hand in the PELVIS's frame and each finger's own local turn.

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


TEMP = tempfile.mkdtemp(prefix="walk_hands_")
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


def card(name):
    path = os.path.join(LIBRARY, name)
    if not os.path.isdir(path):
        return None
    bones = wcards.read_card(path)[1]
    return wp.filtered(wp.prepare(walk, statics, bones, wm, sw.wt), sw.ALL_PARTS)


def run(pose, changes=()):
    p = dict(THEIRS)
    p["changes"] = dict(THEIRS["changes"], **dict(changes))
    p["pins"] = sorted(set(THEIRS["pins"]) | set(dict(changes)))
    ks = dict(sw.params_knobs(walk, sw.normal_params(dict(p, pose=1.0)))[0], in_place=0.0)
    return walk.evaluate(ks, pose, weapons=HELD)


sword, dagger = card(SWORD), card(DAGGER)
if sword is None or dagger is None:
    print("missing a card in %s - nothing to verify" % LIBRARY)
    raise SystemExit(1)
#  Whip is the card knob behind the springs: engine_knobs writes arm_drag = WHIP_DRAG * on, and `on`
#  is 1.0 while Whip > 0. There is no "arm_drag" parameter at all - and normal_params drops an unknown
#  key silently, so naming one reads as a change that does nothing
ZERO = [("arms", ("offset", -100.0)), ("hands", ("offset", -100.0)), ("whip", ("offset", -0.3))]

# ---- 1-2: the two cards as they are, the problem the animator reported
s, d = read(run(sword)), read(run(dagger))
gate(abs(s["r"][0] - FLOOR) < 0.2 and abs(s["l"][0] - FLOOR) < 0.2 and max(s["r"][1], s["l"][1]) < STILL,
     "the sword card's hands are still: %.2f / %.2f deg in the pelvis, fingers %.2f / %.2f"
     % (s["r"][0], s["l"][0], s["r"][1], s["l"][1]))
gate(min(d["r"][0], d["l"][0]) > FLOOR + 3.0 and min(d["r"][1], d["l"][1]) > 5.0,
     "the dagger card's are not: %.2f / %.2f deg, fingers %.2f / %.2f"
     % (d["r"][0], d["l"][0], d["r"][1], d["l"][1]))

# ---- 3: the defaults change nothing at all
plain = run(dagger)
same = run(dagger, [("arms", ("offset", 0.0)), ("hands", ("offset", 0.0))])
gate(np.array_equal(plain.worlds, same.worlds),
     "Arms 100 % and Hands 100 % are the cycle itself, matrix for matrix")

# ---- 4-5: Hands 0 % stills the fingers, per side
both = read(run(dagger, [("hands", ("offset", -100.0))]))
gate(max(both["r"][1], both["l"][1]) < STILL,
     "Hands 0 %%: the dagger's fingers stand still (%.3f / %.3f deg)" % (both["r"][1], both["l"][1]))
one = read(run(dagger, [("hands_l", ("offset", -100.0))]))
gate(one["l"][1] < STILL and abs(one["r"][1] - d["r"][1]) < 0.01,
     "Hands_l 0 %%: the left fingers still (%.3f), the right as they were (%.2f against %.2f)"
     % (one["l"][1], one["r"][1], d["r"][1]))

# ---- 6: the whole ask together reaches the sword's floor
held = read(run(dagger, ZERO))
gate(abs(held["r"][0] - FLOOR) < 0.2 and abs(held["l"][0] - FLOOR) < 0.2
     and max(held["r"][1], held["l"][1]) < STILL,
     "Arms 0 %% + Hands 0 %% + Whip 0 bring the dagger to the sword's floor: %.2f / %.2f deg, "
     "fingers %.3f / %.3f" % (held["r"][0], held["l"][0], held["r"][1], held["l"][1]))

# ---- 7: the control - nothing but Hands reaches the fingers
drag_only = read(run(dagger, [("whip", ("offset", -0.3))]))
gate(min(drag_only["r"][1], drag_only["l"][1]) > 5.0,
     "the control: with Whip 0 alone the fingers still turn (%.2f / %.2f deg) - nothing but "
     "Hands reaches them" % (drag_only["r"][1], drag_only["l"][1]))

# ---- 8: the sword card is untouched by the new knobs at their own value
s2 = read(run(sword, [("arms", ("offset", 0.0)), ("hands", ("offset", 0.0))]))
gate(abs(s2["r"][0] - s["r"][0]) < 1e-6 and abs(s2["l"][0] - s["l"][0]) < 1e-6,
     "the sword card reads the same at the defaults (%.2f / %.2f deg)" % (s2["r"][0], s2["l"][0]))

# ---- 9-10: the cycle still closes and the bones keep their lengths
res = run(dagger, ZERO)
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

# ---- 11: the line says what is held
text = wm.describe(res)
gate("the arms keep 0 %" in text and "the hands keep 0 %" in text,
     "the line says it: %s" % text.split(" | ")[-3:])

print("\n%d gate(s) failed%s" % (len(FAILED), (": " + ", ".join(map(str, FAILED))) if FAILED else ""))
shutil.rmtree(TEMP, ignore_errors=True)
raise SystemExit(1 if FAILED else 0)
