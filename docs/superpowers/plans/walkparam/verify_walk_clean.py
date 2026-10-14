"""verify_walk_clean.py - Walk Builder reading a broken raw clip, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_clean.py

The animator's broken walk (2026-10-14: «анимация сломаной походки») as it was read from their scene -
walks/Walking_broken.walk.gz, git-ignored like every walk here - and the walk it was broken from (asd.walk.gz):
the clean finds every breakage (the loop's short-keyed helpers and twists, the spikes, the moved clavicle, the
dropped shoulders, the turned foot, the floor) against the built-in UE5 idle; the cleaned cycle against the
original; every saved walk the animator has, left alone or only put on the floor; then Apply onto the plugin's
Manny skeleton: the keys on the floor, looping, In place, the levers moving a still spine, the upper body late.
"""
import math
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
FIXTURES = os.path.join(HERE, "walks")
MINE = os.environ.get("WALKS_HOME", "C:/Users/MY PC/Documents/maya/SkeldarWalks")
BROKEN = os.path.join(FIXTURES, "Walking_broken.walk.gz")
ORIGINAL = os.path.join(FIXTURES, "asd.walk.gz")

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
from maya_walk import scene as sw                        # noqa: E402
wm, wc, wf = sw.wm, sw.wc, sw.wf
FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def deg(r):
    return np.degrees(np.linalg.norm(wm.log_rot(r), axis=-1))


def rig(data_or_clip):
    if isinstance(data_or_clip, dict):
        return wc.Rig(data_or_clip["names"], data_or_clip["parents"], data_or_clip["worlds"])
    return wc.Rig(data_or_clip.names, data_or_clip.parents, data_or_clip.worlds)


if not os.path.exists(BROKEN) or not os.path.exists(ORIGINAL):
    print("SKIP: the fixtures are not here (%s, %s)" % (BROKEN, ORIGINAL))
    sys.exit(0)

TEMP = tempfile.mkdtemp(prefix="walkclean_")
for path in (BROKEN, ORIGINAL):
    shutil.copy(path, TEMP)
sw.WALKS = TEMP
REF = sw.BUILT_IN_REFERENCE

# ---- the clean on the broken clip ----
walk, statics, start, report = sw.load_walk("Walking_broken", {}, REF)
text = report.text()
print(text)
gate("lowerarm_r 17-19" in text and "hand_l 23" in text, "spikes: lowerarm_r 17-19 and hand_l 23")
gate("clavicle_l 8.3 cm" in text, "clavicle_l moved off its joint, put back")
gate("clavicle_l" in text and "clavicle_r" in text and "reference" in text, "both clavicles set on the reference")
gate("foot_l" in text and "mirrored" in text, "foot_l takes the right foot mirrored")
floor_line = [t for s, t, _ in report.lines if s == "floor"]
gate(bool(floor_line) and "lowered 5" in floor_line[0], "the floor: %s" % (floor_line[0] if floor_line else "-"))
gate(any(s == "helpers" for s, _, _ in report.lines) and any(s == "twists" for s, _, _ in report.lines),
     "short-keyed helpers and twists rebuilt")
cleaned = sw._cleaned(wf.path_for(TEMP, "Walking_broken"), os.path.getmtime(wf.path_for(TEMP, "Walking_broken")),
                      wf.load(wf.path_for(TEMP, "Walking_broken")), {}, REF)[0]
gate(wc.is_closed(cleaned.worlds, wc._Clip(cleaned)), "the cleaned cycle is closed (every joint)")
pos = cleaned.worlds[..., 3, :3]
travel = pos[:, -1] - pos[:, 0] - (pos[cleaned.names.index("root"), -1] - pos[cleaned.names.index("root"), 0])
gate(float(np.abs(travel).max()) < 0.1, "every joint, helpers and twists too, loops (%.4f cm)" % float(np.abs(travel).max()))

# ---- against the original ----
original = wf.load(ORIGINAL)
a, b = rig(cleaned), rig(original)
ai, bi = a.index, b.index


def err(name, frames=None):
    j, k = ai[name], bi[name]
    e = deg(a.rot[j] @ np.swapaxes(b.rot[k], -1, -2))
    return float(e[frames].max() if frames is not None else e.max())


gate(err("lowerarm_r", [17, 18, 19]) < 3.0, "lowerarm_r 17-19 against the original: %.2f deg" % err("lowerarm_r", [17, 18, 19]))
gate(err("hand_l", [23]) < 3.0, "hand_l 23 against the original: %.2f deg" % err("hand_l", [23]))
fl = [deg(wm.mean_rot(a.rot[ai["foot_l"], :-1]) @ wm.mean_rot(b.rot[bi["foot_l"], :-1]).T)]
gate(float(fl[0]) < 15.0, "foot_l's mean against the original: %.1f deg (was 72 out)" % float(fl[0]))
pel_a = cleaned.worlds[ai["pelvis"], :, 3, 1]
pel_b = original["worlds"][bi["pelvis"], :, 3, 1]
gate(abs(float(pel_a.mean() - pel_b.mean())) < 5.0, "the pelvis on the floor: %.1f cm (the original %.1f)"
     % (float(pel_a.mean()), float(pel_b.mean())))
# the clip the animator broke is not asd to the degree everywhere (its neck 11.7, legs 4-5 deg apart before any
# clean): what the clean did not touch must stand as the BROKEN clip had it
source = wf.load(BROKEN)
s = rig(source)
untouched = [n for n in ("thigh_l", "calf_r", "lowerarm_l", "head", "index_01_r", "neck_01", "spine_03")]
same = lambda n: float(deg(a.rot[ai[n]] @ np.swapaxes(s.rot[s.index[n]], -1, -2)).max())
worst = max(same(n) for n in untouched)
gate(worst < 1e-3, "untouched bones as the clip had them: %.2e deg" % worst)
# the upper arms keep their WORLD turn under the raised shoulders (they hang)
up = [float(deg(wm._batch_rot(cleaned.worlds[ai[n]]) @ np.swapaxes(wm._batch_rot(source["worlds"][s.index[n]]), -1, -2)).max())
      for n in ("upperarm_l", "upperarm_r")]
gate(max(up) < 1e-3, "the upper arms hang in the world as the clip had them: %.2e / %.2e deg" % tuple(up))

# ---- every saved walk of the animator ----
mine = [f for f in sorted(os.listdir(MINE)) if f.endswith(".walk.gz")] if os.path.isdir(MINE) else []
for f in mine:
    shutil.copy(os.path.join(MINE, f), TEMP)
for f in mine:
    name = f[:-len(".walk.gz")]
    w, _, _, rep = sw.load_walk(name, {}, REF)
    steps = set(s for s, _, _ in rep.lines)
    gate(steps <= {"floor", "posture"} and ("posture" not in steps or name == "dw"),
         "%s: %s" % (name, rep.short() or "unchanged"))

# ---- Apply onto the plugin's Manny skeleton ----
cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
before = set(cmds.ls(type="joint", long=True) or [])
cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace="M", ignoreVersion=True,
          preserveReferences=False)
joints = set(cmds.ls(type="joint", long=True) or []) - before
root = min([j for j in joints if not cmds.listRelatives(j, parent=True, type="joint")], key=lambda p: p.count("|"))
result, info, line = sw.apply(root, "Walking_broken", {}, None, sw.ALL_PARTS, REF)
print(line)
gate("cleaned" in line, "the status line says what was cleaned")
n = result.frames
path = dict((p.rsplit("|", 1)[-1].split(":")[-1], p) for p in joints)
frames = list(range(start, start + n + 1))
W = dict((leaf, np.array([cmds.getAttr(path[leaf] + ".worldMatrix[0]", time=t) for t in frames]).reshape(-1, 4, 4))
         for leaf in ("root", "pelvis", "ball_l", "ball_r", "foot_l", "clavicle_l", "spine_03", "hand_l"))
low = min(float(W["ball_l"][:, 3, 1].min()), float(W["ball_r"][:, 3, 1].min()))
gate(-3.0 < low < 3.0, "the keyed feet on the floor: the lowest ball at %.2f cm" % low)
r_travel = W["root"][-1, 3, :3] - W["root"][0, 3, :3]
loop = float(np.abs((W["hand_l"][-1, 3, :3] - W["hand_l"][0, 3, :3]) - r_travel).max())
gate(loop < 0.1, "the keyed cycle loops: hand_l %.4f cm off" % loop)
result, info, line = sw.apply(root, "Walking_broken", {"in_place": 1.0}, None, sw.ALL_PARTS, REF)
r = np.array([cmds.getAttr(path["root"] + ".worldMatrix[0]", time=t) for t in frames]).reshape(-1, 4, 4)[:, 3, :3]
gate(float(np.linalg.norm(r[-1] - r[0])) < 0.5, "In place: the root stays (%.3f cm a cycle)" % float(np.linalg.norm(r[-1] - r[0])))
spine0 = np.array([cmds.getAttr(path["spine_03"] + ".worldMatrix[0]", time=t) for t in frames]).reshape(-1, 4, 4)
result, info, line = sw.apply(root, "Walking_broken", {"in_place": 1.0, "chest_pitch": 4.0, "pelvis_tilt": 3.0},
                              None, sw.ALL_PARTS, REF)
spine1 = np.array([cmds.getAttr(path["spine_03"] + ".worldMatrix[0]", time=t) for t in frames]).reshape(-1, 4, 4)
moved = float(deg(wm._batch_rot(spine1) @ np.swapaxes(wm._batch_rot(spine0), -1, -2)).max())
gate(moved > 1.0, "the levers move the still spine: spine_03 up to %.1f deg" % moved)
memo = sw.memo_of(root)
gate(memo.get("reference") == REF and "smooth" in memo.get("knobs", {}), "the marker keeps the reference and the clean knobs")
# the Overlap tab on the keys: the upper body late, a wave up the spine, the shoulders and the hips dragged
over = {"upper_offset": 3.0, "spine_wave": 2.0, "shoulder_drag": 2.0, "pelvis_drag": 2.0, "in_place": 1.0}
result, info, line = sw.apply(root, "Walking_broken", over, None, sw.ALL_PARTS, REF)
print(line)
chain = ("upperarm_l", "lowerarm_l", "hand_l", "thigh_r", "calf_r", "foot_r")
K = dict((leaf, np.array([cmds.getAttr(path[leaf] + ".worldMatrix[0]", time=t) for t in frames]).reshape(-1, 4, 4))
         for leaf in chain)
lengths = [np.linalg.norm(K[b][:, 3, :3] - K[a][:, 3, :3], axis=1) for a, b in zip(chain[:2], chain[1:3])]
lengths += [np.linalg.norm(K[b][:, 3, :3] - K[a][:, 3, :3], axis=1) for a, b in zip(chain[3:5], chain[4:6])]
whole = max(float(np.ptp(l)) for l in lengths)
seam = float(np.abs(K["hand_l"][-1, 3, :3] - K["hand_l"][0, 3, :3]).max())
gate(whole < 1e-3 and seam < 0.1, "Overlap on the keys: the bones whole (%.6f cm), the cycle loops (%.4f cm)" % (whole, seam))

shutil.rmtree(TEMP, ignore_errors=True)
print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": %s" % FAILED) if FAILED else ""))
