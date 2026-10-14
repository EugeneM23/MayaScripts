"""verify_walk_sprint.py - a sprint under a side-on pose (2026-10-14), in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_sprint.py

The animator's AGS_Sprint walk and two_handed_sword pose (SkeldarWalks; skipped without them) put onto the plugin's
Manny skeleton through the card's own apply, the keys read back: the repeated end frame dropped and no frame
standing still; the legs matched to the gait (the knees swing in the line of travel, the hips face the run, the
shoulders keep the pose's turn, the trunk leans as a run does); the arms without the seam's flips; the trunk and the
head on springs smoother than the frames and the clip; bones whole, the grip held. WALK_SPRINT_SHEET=<png> draws
the old reading against the new one.
The design: docs/superpowers/specs/2026-10-14-walk-sprint-legs-and-body-design.md.
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
MINE = os.environ.get("WALKS_HOME", "C:/Users/MY PC/Documents/maya/SkeldarWalks")
SPRINT_FILE = os.path.join(MINE, "AGS_Sprint.walk.gz")
SWORD_FILE = os.path.join(MINE, "two_handed_sword.wpose.gz")
# the knobs the animator's scene carried (port 7002, 2026-10-14) - the tempo the walk's own
SCENE = {"pose": 1.0, "leg_turn": 0.57}

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
from maya_walk import scene as sw                        # noqa: E402
wm = sw.wm
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def top_joint(joints):
    def is_top(j):
        above = cmds.listRelatives(j, parent=True, fullPath=True)
        return not above or cmds.nodeType(above[0]) != "joint"
    return min([j for j in joints if is_top(j)], key=lambda p: (p.count("|"), p))


def ma_import(path, namespace):
    before = set(cmds.ls(type="joint", long=True) or [])
    cmds.file(path, i=True, namespace=namespace, ignoreVersion=True, preserveReferences=False)
    return top_joint(set(cmds.ls(type="joint", long=True) or []) - before)


def keyed(root, walk, start, n):
    """The skeleton's keys as the model's joints (J, n+1, 4, 4) - a twin: the same names."""
    bones = sw.read_bones(root)[0]
    out = np.tile(np.eye(4), (len(walk.names), n + 1, 1, 1))
    for j, leaf in enumerate(walk.names):
        if leaf in bones:
            path = bones[leaf]["path"]
            out[j] = np.array([cmds.getAttr(path + ".worldMatrix[0]", time=t)
                               for t in range(start, start + n + 1)]).reshape(n + 1, 4, 4)
    return out


def noise(worlds, j, n, rel=None):
    """A joint's world (or relative) turn against its periodic 1-frame Gaussian blur: (rms, max) degrees."""
    R = np.array([wm.orthonormal(worlds[j, f, :3, :3]) for f in range(n)])
    if rel is not None:
        R = np.array([R[f] @ wm.orthonormal(worlds[rel, f, :3, :3]).T for f in range(n)])
    logs = wm.log_rot(R @ wm.mean_rot(R).T)
    d = np.minimum(np.arange(n), n - np.arange(n))
    kernel = np.exp(-0.5 * d * d)
    kernel /= kernel.sum()
    smooth = np.real(np.fft.ifft(np.fft.fft(logs, axis=0) * np.fft.fft(kernel)[:, None], axis=0))
    e = np.degrees(np.linalg.norm(logs - smooth, axis=1))
    return float(np.sqrt((e ** 2).mean())), float(e.max())


def heading(v, walk):
    return math.degrees(math.atan2(float(np.dot(v, walk.side)), float(np.dot(v, walk.fwd))))


def lean(worlds, walk, n):
    i = walk.index
    return float(np.mean([math.degrees(math.atan2(*(lambda v: (float(v @ walk.fwd), float(v @ walk.up)))(
        worlds[i["neck_01"], f, 3, :3] - worlds[i["pelvis"], f, 3, :3]))) for f in range(n)]))


def line_heading(worlds, walk, a, b, n):
    i = walk.index
    return float(np.mean([heading(worlds[i[a], f, 3, :3] - worlds[i[b], f, 3, :3], walk) for f in range(n)]))


def knee_aside(worlds, walk, side, n):
    i = walk.index
    d = np.array([float(np.dot(worlds[i["calf_" + side], f, 3, :3] - worlds[i["thigh_" + side], f, 3, :3], walk.side))
                  for f in range(n)])
    return float(d.min()), float(d.max())


def sheet(path, walk, panels, frames):
    """Side, front and top onion skins of each (label, worlds); the left side blue, the right orange."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtCore, QtGui, QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    font_id = QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    family = (QtGui.QFontDatabase.applicationFontFamilies(font_id) or ["Segoe UI"])[0]
    body = ("pelvis", "spine", "neck", "head", "clavicle", "upperarm", "lowerarm", "hand", "thigh", "calf", "foot", "ball")
    bones = [(j, p, (n[-1] if n.endswith(("_l", "_r")) else "c")) for j, (n, p) in enumerate(zip(walk.names, walk.parents))
             if p >= 0 and walk.names[p] != "root" and n.split("_")[0] in body and "twist" not in n]
    colour = {"l": QtGui.QColor(70, 130, 230), "r": QtGui.QColor(235, 130, 40), "c": QtGui.QColor(60, 60, 60)}
    W, H = 420, 420
    image = QtGui.QImage(3 * W, len(panels) * H, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor(250, 250, 248))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    for row, (label, worlds) in enumerate(panels):
        n = worlds.shape[1] - 1
        root = walk.index["root"]
        travel = worlds[root, n, 3, :3] - worlds[root, 0, 3, :3]
        for col, view in enumerate(("side", "front", "top")):
            def proj(p, f):
                q = (p - worlds[root, 0, 3, :3] - travel * f / n) @ walk.basis.T
                return {"side": (q[0], q[2]), "front": (-q[1], q[2]), "top": (-q[1], q[0])}[view]
            pts = [proj(worlds[j, f, 3, :3], f) for f in frames for j, p, s in bones]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            scale = (H - 40) / max(max(xs) - min(xs), max(ys) - min(ys))
            to = lambda p: QtCore.QPointF(col * W + W / 2 + (p[0] - cx) * scale, row * H + H / 2 + 10 - (p[1] - cy) * scale)
            for k, f in enumerate(frames):
                for j, p, s in bones:
                    c = QtGui.QColor(colour[s])
                    c.setAlpha(60 + int(195 * (k + 1) / len(frames)))
                    painter.setPen(QtGui.QPen(c, 2.0))
                    painter.drawLine(to(proj(worlds[p, f, 3, :3], f)), to(proj(worlds[j, f, 3, :3], f)))
            painter.setPen(QtGui.QColor(20, 20, 20))
            painter.setFont(QtGui.QFont(family, 10))
            painter.drawText(QtCore.QRectF(col * W + 6, row * H + 4, W - 12, 18), "%s - %s" % (label, view))
    painter.end()
    image.save(path)


TEMP = tempfile.mkdtemp(prefix="walksprint_")
sw.WALKS = os.path.join(TEMP, "walks")
try:
    if not (os.path.exists(SPRINT_FILE) and os.path.exists(SWORD_FILE)):
        print("no %s or %s: nothing to verify" % (SPRINT_FILE, SWORD_FILE))
        raise SystemExit(0)
    os.makedirs(sw.WALKS)
    shutil.copy(SPRINT_FILE, sw.wf.path_for(sw.WALKS, "AGS_Sprint"))
    shutil.copy(SWORD_FILE, sw.wf.pose_path_for(sw.WALKS, "two_handed_sword"))
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    walk, statics, start = sw.load_walk("AGS_Sprint")
    data = sw.wf.load(sw.wf.path_for(sw.WALKS, "AGS_Sprint"))
    gate(walk.P == 60 and walk.dropped == 1 and "1 repeated frame dropped" in walk.summary(),
         "the walk read without its repeated last frame: %s" % walk.summary())
    manny = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "manny")
    result, info, text = sw.apply(manny, "AGS_Sprint", SCENE, "two_handed_sword")
    print("        " + text)
    n = result.frames
    new = keyed(manny, walk, start, n)
    gate(n == 60 and "legs matched x0.15, hips 36 deg to the spine" in text,
         "%d frames, the status line says what Leg match did: %s"
         % (n, ([part for part in text.split(" | ") if part.startswith("legs")] or ["-"])[0]))
    i = walk.index
    root = new[i["root"], :, 3, :3]
    steps = np.linalg.norm(np.diff(root, axis=0), axis=1)
    pelvis_steps = np.linalg.norm(np.diff(new[i["pelvis"], :, 3, :3], axis=0), axis=1)
    gate(float(steps.min()) > 0.9 * float(steps.mean()) and float(pelvis_steps.min()) > 0.5 * float(pelvis_steps.mean()),
         "no frame stands still: the root moves %.2f..%.2f cm a frame, the pelvis %.2f..%.2f (the old reading stood "
         "still a frame a cycle)" % (steps.min(), steps.max(), pelvis_steps.min(), pelvis_steps.max()))

    # the old reading: the 61-frame cycle, Leg match, Gait lean and the bodies off - what the scene had
    saved = wm.trimmed
    wm.trimmed = lambda clip: (clip, 0)
    try:
        old_walk = wm.analyse(sw.wf.clip_of(data, wm))
    finally:
        wm.trimmed = saved
    old_pose = sw.wp.filtered(sw.wp.prepare(old_walk, statics, sw.wf.load_pose(sw.wf.pose_path_for(
        sw.WALKS, "two_handed_sword"))[1], wm, sw.wt), sw.ALL_PARTS)
    old = old_walk.evaluate(dict(SCENE, tempo=61, leg_match=0.0, gait_lean=0.0, torso_drag=0.0, head_drag=0.0),
                            old_pose).worlds
    src = walk.clip.worlds
    worst = lambda w, names, m: max(noise(w, i[nm], m)[1] for nm in names)
    arms = ("upperarm_l", "lowerarm_l", "upperarm_r", "lowerarm_r")
    gate(worst(new, arms, n) < 5.0 < worst(old, arms, 61),
         "the arms without the seam's jolt: worst world jitter %.2f deg (the old reading %.1f, the clip %.2f)"
         % (worst(new, arms, n), worst(old, arms, 61), worst(src, arms, n)))

    # the legs: in the line of travel, the hips facing the run, the shoulders the pose's turn, the run's lean
    for side in ("l", "r"):
        lo, hi = knee_aside(new, walk, side, n)
        slo, shi = knee_aside(src, walk, side, n)
        olo, ohi = knee_aside(old, walk, side, 61)
        gate(lo > slo - 5.0 and hi < shi + 5.0,
             "the %s knee swings in the line of travel: %.1f..%.1f cm aside of its hip (the clip %.1f..%.1f, the old "
             "reading %.1f..%.1f)" % (side, lo, hi, slo, shi, olo, ohi))
    hips, shoulders = line_heading(new, walk, "thigh_l", "thigh_r", n), line_heading(new, walk, "upperarm_l", "upperarm_r", n)
    o_hips, o_shoulders = line_heading(old, walk, "thigh_l", "thigh_r", 61), line_heading(old, walk, "upperarm_l", "upperarm_r", 61)
    s_hips = line_heading(src, walk, "thigh_l", "thigh_r", n)
    gate(abs(hips - s_hips) < 3.0 and shoulders - hips < -20.0,
         "the hips face the run (%.1f deg, the clip %.1f, the old reading %.1f) and the shoulders keep the pose's turn "
         "(%.1f deg against the hips, the old reading %.1f)" % (hips, s_hips, o_hips, shoulders - hips, o_shoulders - o_hips))
    gate(lean(new, walk, n) > lean(src, walk, n) - 2.0 and lean(old, walk, 61) < 15.0,
         "the trunk leans into the run: %.1f deg (the clip %.1f, the old reading %.1f)"
         % (lean(new, walk, n), lean(src, walk, n), lean(old, walk, 61)))

    # the trunk and the head on springs: smoother than the frames, calmer than the clip
    frames_only = walk.evaluate(dict(SCENE, torso_drag=0.0, head_drag=0.0),
                                sw.prepared_pose("AGS_Sprint", "two_handed_sword")).worlds
    for name, ref, factor in (("spine_05", frames_only, 0.8), ("head", src, 0.6)):
        a, b = noise(new, i[name], n), noise(ref, i[name], n)
        gate(a[0] < factor * b[0], "the %s's jitter %.2f/%.2f deg (rms/max) against %s %.2f/%.2f"
             % (name, a[0], a[1], "the frames'" if ref is frames_only else "the clip's", b[0], b[1]))
    off = max(math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(new[i["spine_05"], f, :3, :3]) @
                                                            wm.orthonormal(frames_only[i["spine_05"], f, :3, :3]).T))))
              for f in range(n))
    gate(2.0 < off < 20.0, "the chest trails the frames by up to %.1f deg (Torso drag 1.5)" % off)

    # whole: lengths, the grip
    lengths = []
    for j, p in enumerate(walk.parents):
        if p >= 0 and walk.kind[j] != "helper" and walk.names[p] != "root":      # the root is no bone's start
            d = np.linalg.norm(new[j, :, 3, :3] - new[p, :, 3, :3], axis=1)
            lengths.append(float(np.ptp(d)))
    hold = [new[i["hand_l"], f] @ np.linalg.inv(new[i["hand_r"], f]) for f in range(n)]
    gate(max(lengths) < 0.05 and float(np.abs(np.array(hold) - hold[0])[:, 3, :3].max()) < 0.05,
         "bones whole (length changes up to %.4f cm, the walk's own breathing legs), the grip held to %.4f cm"
         % (max(lengths), float(np.abs(np.array(hold) - hold[0])[:, 3, :3].max())))
    if os.environ.get("WALK_SPRINT_SHEET"):
        sheet(os.environ["WALK_SPRINT_SHEET"], walk, [("the clip", src), ("the old reading", old), ("now", new)],
              list(range(0, 16)))
        print("        picture: %s" % os.environ["WALK_SPRINT_SHEET"])
finally:
    shutil.rmtree(TEMP, ignore_errors=True)
print("%d of %d gates failed" % (len(FAILED), COUNT[0]) if FAILED else "all %d gates passed" % COUNT[0])
