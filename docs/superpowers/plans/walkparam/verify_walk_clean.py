"""verify_walk_clean.py - Walk Builder reading a broken raw clip, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_clean.py

The animator's broken walk (2026-10-14: «анимация сломаной походки») as it was read from their scene -
walks/Walking_broken.walk.gz, git-ignored like every walk here - and the walk it was broken from (asd.walk.gz).
What is kept of the clean after the animator's try (the same day: «полезным оказались функции inPlace,
FixPosture, Seam ... Можно еще сглаживание оставить ... Fix pos давай сделаем кнопкой»): the loop and its seam
(the short-keyed helpers and twists rebuilt), Smooth, the Fix posture button (the clavicles, the turned foot, a
bone off its joint - written into the walk's file) and In place. Then every saved walk the animator has is read
with nothing but its loop touched, and Apply onto the plugin's Manny skeleton loops and stays in place.
"""
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
        return wc.Rig(data_or_clip["names"], data_or_clip["parents"], np.asarray(data_or_clip["worlds"], float))
    return wc.Rig(data_or_clip.names, data_or_clip.parents, data_or_clip.worlds)


if not os.path.exists(BROKEN) or not os.path.exists(ORIGINAL):
    print("SKIP: the fixtures are not here (%s, %s)" % (BROKEN, ORIGINAL))
    sys.exit(0)

TEMP = tempfile.mkdtemp(prefix="walkclean_")
for path in (BROKEN, ORIGINAL):
    shutil.copy(path, TEMP)
sw.WALKS = TEMP

# ---- reading the broken clip: the loop and its seam, nothing else ----
walk, statics, start, report = sw.load_walk("Walking_broken", {})
text = report.text()
print(text)
steps = set(s for s, _, _ in report.lines)
gate(bool(steps) and steps <= {"loop", "seam", "helpers", "twists"}, "the broken clip is looped: %s" % report.short())
gate(any(s == "helpers" for s, _, _ in report.lines) and any(s == "twists" for s, _, _ in report.lines),
     "short-keyed helpers and twists rebuilt")
gate("posture" not in steps, "reading leaves the posture to the button")
path = wf.path_for(TEMP, "Walking_broken")
cleaned = sw._cleaned(path, os.path.getmtime(path), wf.load(path), {})[0]
gate(wc.is_closed(cleaned.worlds, wc._Clip(cleaned)), "the cleaned cycle is closed (every joint)")
pos = cleaned.worlds[..., 3, :3]
travel = pos[:, -1] - pos[:, 0] - (pos[cleaned.names.index("root"), -1] - pos[cleaned.names.index("root"), 0])
gate(float(np.abs(travel).max()) < 0.1, "every joint, helpers and twists too, loops (%.4f cm)" % float(np.abs(travel).max()))

# ---- Fix posture: written into the walk's file once ----
raw = wf.load(path)["worlds"]
report, line = sw.fix_posture("Walking_broken", {})
print(line)
text = report.text()
gate("clavicle_l" in text and "clavicle_r" in text, "both clavicles set right")
gate("foot_l" in text and "mirrored" in text, "foot_l takes the right foot mirrored")
gate(os.path.exists(path + sw.BACKUP) and np.array_equal(wf.load(path + sw.BACKUP)["worlds"], raw),
     "the original kept beside it")
fixed = wf.load(path)
original = wf.load(ORIGINAL)
a, b = rig(fixed), rig(original)
P = a.frames - 1
fl = float(deg(wm.mean_rot(a.rot[a.index["foot_l"], :P]) @ wm.mean_rot(b.rot[b.index["foot_l"], :P]).T))
gate(fl < 15.0, "foot_l's mean against the original: %.1f deg (was 72 out)" % fl)
again, line2 = sw.fix_posture("Walking_broken", {})
gate("nothing out of place" in line2, "a second press: %s" % line2)
walk2 = sw.load_walk("Walking_broken", {})[0]
gate(walk2.P > 10, "the fixed walk reads: %d frames" % walk2.P)
smooth = sw.load_walk("Walking_broken", {"smooth": 2.0})[3]
gate("smooth" in set(s for s, _, _ in smooth.lines), "Smooth still runs at read")

# ---- every saved walk of the animator: read unchanged ----
mine = [f for f in sorted(os.listdir(MINE)) if f.endswith(".walk.gz")] if os.path.isdir(MINE) else []
for f in mine:
    shutil.copy(os.path.join(MINE, f), TEMP)
for f in mine:
    name = f[:-len(".walk.gz")]
    w, _, _, rep = sw.load_walk(name, {})
    gate(set(s for s, _, _ in rep.lines) <= {"loop", "seam", "helpers", "twists"},
         "%s: %s" % (name, rep.short() or "unchanged"))

# ---- Apply onto the plugin's Manny skeleton ----
cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
before = set(cmds.ls(type="joint", long=True) or [])
cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace="M", ignoreVersion=True,
          preserveReferences=False)
joints = set(cmds.ls(type="joint", long=True) or []) - before
root = min([j for j in joints if not cmds.listRelatives(j, parent=True, type="joint")], key=lambda p: p.count("|"))
result, info, line = sw.apply(root, "Walking_broken", {})
print(line)
n = result.frames
path_of = dict((p.rsplit("|", 1)[-1].split(":")[-1], p) for p in joints)
frames = list(range(start, start + n + 1))
W = dict((leaf, np.array([cmds.getAttr(path_of[leaf] + ".worldMatrix[0]", time=t) for t in frames]).reshape(-1, 4, 4))
         for leaf in ("root", "hand_l"))
r_travel = W["root"][-1, 3, :3] - W["root"][0, 3, :3]
loop = float(np.abs((W["hand_l"][-1, 3, :3] - W["hand_l"][0, 3, :3]) - r_travel).max())
gate(loop < 0.1, "the keyed cycle loops: hand_l %.4f cm off" % loop)
result, info, line = sw.apply(root, "Walking_broken", {"in_place": 1.0})
r = np.array([cmds.getAttr(path_of["root"] + ".worldMatrix[0]", time=t) for t in frames]).reshape(-1, 4, 4)[:, 3, :3]
gate(float(np.linalg.norm(r[-1] - r[0])) < 0.5, "In place: the root stays (%.3f cm a cycle)" % float(np.linalg.norm(r[-1] - r[0])))
gate("in place" in line, "the status line says in place")

shutil.rmtree(TEMP, ignore_errors=True)
print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": %s" % FAILED) if FAILED else ""))
