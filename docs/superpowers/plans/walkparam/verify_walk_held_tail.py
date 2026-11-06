"""verify_walk_held_tail.py - a clip whose keys run on past its motion is read as the cycle it is. mayapy
standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_held_tail.py

The animator, 2026-11-06, a Maya on port 7002: «walk builder добавляет ключи к походке но в итоге у меня
ломается цикл. Наш плагин должен обеспечивать соблюдение цикличности». Their walker carried its own cycle
(own:462dab8fd658b3cb), captured from the skeleton's keys on its first Pick: 131 frames read, 0-130 - and every
bone stood still from frame 120 on (frame 120 IS frame 0 moved by the travel, to 0.0185 cm: the cycle is 120
frames). The clean's loop check took frame 130 for the closing frame, the seam step read the pelvis (closing to
0.0185 cm, past SEAM_TOL) as a bone keyed short and refilled it through the hold - so the model's own
repeated-frame trim found the held frames no longer equal and kept them. Pick keyed 0-130: the walk slowed
almost to a stop over its last frames and jumped back into motion at frame 0.

This keys their cycle, their settings and their pose card onto a Manny UE5 skeleton, reads the keys back, and
runs it again with the hold check switched off as the control (what they had), so every gate can fail.
Needs their own cycle and card on this machine; says so and stops without them.
"""
import math
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
DOCS = os.path.expanduser("~").replace("\\", "/")
OWN_DIGEST = "462dab8fd658b3cb"
OWN_FILE = "C:/Users/MY PC/Documents/maya/SkeldarWalks/own/%s.walk.gz" % OWN_DIGEST
CARD = "C:/Users/MY PC/Documents/maya/scripts/SkeldarAnim/poses/LongSword_Idle_3P.pose"
PARAMS = {"changes": {"weapon_overlap": ["offset", 125.3]}, "pins": ["weapon_hold", "weapon_overlap"],
          "macros": {}, "character": "", "strength": 1.0, "physics": True, "pose": 1.0, "in_place": 1.0,
          "clean": {"smooth": 0.92, "seam": 10.26}, "knee_pops": True}    # read off their walker's memo

if not (os.path.exists(OWN_FILE) and os.path.isdir(CARD)):
    print("SKIP: their cycle %s or card %s is not here" % (OWN_FILE, CARD))
    sys.exit(0)

import maya.standalone                                     # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                   # noqa: E402
import numpy as np                                         # noqa: E402

for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except RuntimeError:
        pass

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
from maya_walk import scene as sw, clean as wc             # noqa: E402
from maya_poselib import store                             # noqa: E402

FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


TEMP = tempfile.mkdtemp(prefix="walkheld_")
os.makedirs(os.path.join(TEMP, "walks", sw.OWN_CACHE))
shutil.copy(OWN_FILE, os.path.join(TEMP, "walks", sw.OWN_CACHE, OWN_DIGEST + ".walk.gz"))
shutil.copytree(CARD, os.path.join(TEMP, "library", os.path.basename(CARD)))
sw.WALKS = os.path.join(TEMP, "walks")
cmds.optionVar(stringValue=(store.ROOT_VAR, os.path.join(TEMP, "library").replace("\\", "/")))
WALK = sw.OWN + OWN_DIGEST


def keyed(label):
    """Their cycle Picked onto a fresh Manny UE5 skeleton: (worlds (J, F, 4, 4) of the body read back off the
    keys, joint names, the last key's frame, the status line, the clean report)."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, ignoreVersion=True)
    root = cmds.ls("root", long=True)[0]
    sw._state()["loaded"] = {}
    result, info, text = sw.apply(root, WALK, pose_card="LongSword_Idle_3P.pose", params=dict(PARAMS))
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    times = set()
    for j in joints:
        for ch in sw.CHANNELS:
            times.update(cmds.keyframe(j, attribute=ch, query=True, timeChange=True) or [])
    first, last = int(round(min(times))), int(round(max(times)))
    body = [j for j in joints if not wc.is_helper(sw._short(j)) and not wc.is_twist(sw._short(j))]
    worlds = np.zeros((len(body), last - first + 1, 4, 4))
    for f in range(first, last + 1):
        cmds.currentTime(f)
        for i, j in enumerate(body):
            worlds[i, f - first] = np.array(cmds.xform(j, query=True, worldSpace=True, matrix=True)).reshape(4, 4)
    print("    [%s] %s" % (label, text))
    return worlds, [sw._short(j) for j in body], (first, last), text, info["clean"]


def turn(a, b):
    """degrees between two rotations (row vectors, scale stripped)"""
    ra = a[:3, :3] / np.linalg.norm(a[:3, :3], axis=1)[:, None]
    rb = b[:3, :3] / np.linalg.norm(b[:3, :3], axis=1)[:, None]
    c = (np.trace(ra @ rb.T) - 1.0) / 2.0
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def seam_reading(worlds, names):
    """(the worst joint's last-frame place against its first (cm), its turn (deg); the worst seam jolt as a share
    of that joint's own largest jolt inside the cycle - a cycle moving the same way through its seam as anywhere
    else reads 1 or less; the pelvis's last five steps against its median step)"""
    pos = worlds[:, :, 3, :3]
    off = float(np.linalg.norm(pos[:, -1] - pos[:, 0], axis=1).max())
    rot = max(turn(worlds[j, -1], worlds[j, 0]) for j in range(len(names)))
    p = pos[:, :-1]                                              # one cycle, its closing frame left out
    inner = np.linalg.norm(p[:, 2:] - 2.0 * p[:, 1:-1] + p[:, :-2], axis=2)
    jolt = np.linalg.norm(p[:, 1] - 2.0 * p[:, 0] + p[:, -1], axis=1)
    moving = inner.max(axis=1) > 0.05
    share = float((jolt[moving] / inner.max(axis=1)[moving]).max())
    pelvis = names.index("pelvis")
    steps = np.linalg.norm(np.diff(pos[pelvis], axis=0), axis=1)
    return off, rot, share, float(steps[-5:].min() / np.median(steps))


# ---------------------------------------------------------------- the fix
worlds, names, keys, text, report = keyed("fixed")
off, rot, share, tail = seam_reading(worlds, names)
gate("stood still over its last 10 frames" in report.text() and "refilled" not in report.text(),
     "the clean reads the hold and cuts it: %s" % report.text().replace("\n", " | "))
gate("10 still frames cut" in text, "the Pick line says it")
gate(keys == (0, 120), "keyed on frames %d-%d - the cycle's 120 frames and its closing frame, nothing past" % keys)
gate(off < 0.01 and rot < 0.01, "the last frame stands on the first: %.5f cm, %.5f deg (in place)" % (off, rot))
gate(share <= 1.0, "through its seam the walk jolts %.2f of its own worst jolt inside the cycle" % share)
gate(tail > 0.4, "the pelvis keeps moving into the seam: its last five steps at least %.2f of its median" % tail)

# ---------------------------------------------------------------- the control: what they had
saved = wc.held_ends
wc.held_ends = lambda worlds, c: (0, worlds.shape[1] - 1)
try:
    worlds, names, keys, text, report = keyed("hold check off")
finally:
    wc.held_ends = saved
off0, rot0, share0, tail0 = seam_reading(worlds, names)
gate(keys == (0, 130) and "refilled back to the first frame: pelvis" in report.text(),
     "control: keyed %d-%d with the pelvis refilled through the hold, as in their scene" % keys)
#  the jolt through the seam does not tell the two apart (the hold eases out of the motion: 0.85 against 0.79):
#  gate 5 says only that the cut brings no jolt of its own. The stop before the seam is what they saw.
gate(tail0 < 0.4, "control: the pelvis's last five steps %.2f of its median - the walk stops before its seam "
                  "(through the seam %.2f of its own worst jolt)" % (tail0, share0))

cmds.optionVar(remove=store.ROOT_VAR)
shutil.rmtree(TEMP, ignore_errors=True)
print("%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": " + str(FAILED)) if FAILED else ""))
