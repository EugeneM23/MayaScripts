"""verify_walk.py - a saved walk onto skeletons, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk.py

Desktop/Walk_01.fbx (a temp copy) imported and saved as a walk (into a temp walks folder); then applied onto
the plugin's Manny skeleton (a twin: the walk itself, moved to where Manny stands), the Creep skeleton, the
UE4 Mannequin, the animator's Mixamo Sweep Fall.fbx (Downloads, when there) and a Manny shrunk to 0.6:
stance feet as still as the walk's (x the size), the stride x the size, bone lengths unchanged, the seam;
re-tuned from its stored place, Pick, one Ctrl+Z; last, onto its own skeleton: the cycle itself.
"""
import importlib.util
import math
import os
import shutil
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
WALK_FBX = os.environ.get("WALK_FBX", "C:/Users/MY PC/Desktop/Walk_01.fbx")
MIXAMO_FBX = "C:/Users/MY PC/Downloads/Sweep Fall.fbx"
POSE_FILE = os.path.join(HERE, "walks", "goblin.wpose.gz")   # the animator's poses, saved by Save pose
SWORD_FILE = os.path.join(HERE, "walks", "two_handed_sword.wpose.gz")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
sw = load("skeldar_walk_under_verify", os.path.join(HERE, "skeldar_walk.py"))
wm, wt = sw.wm, sw.wt
FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def fbx_import(path, namespace=None):
    copy = os.path.join(TEMP, os.path.basename(path))
    shutil.copy(path, copy)
    cmds.loadPlugin("fbxmaya", quiet=True)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval("FBXImportSetMayaFrameRate -v false")
    before = set(cmds.ls(type="joint", long=True) or [])
    if namespace:
        cmds.namespace(add=namespace)
        cmds.namespace(setNamespace=namespace)
    try:
        mel.eval('FBXImport -f "%s"' % copy.replace("\\", "/"))
    finally:
        cmds.namespace(setNamespace=":")
    return top_joint(set(cmds.ls(type="joint", long=True) or []) - before)


def ma_import(path, namespace):
    before = set(cmds.ls(type="joint", long=True) or [])
    cmds.file(path, i=True, namespace=namespace, ignoreVersion=True, preserveReferences=False)
    return top_joint(set(cmds.ls(type="joint", long=True) or []) - before)


def top_joint(joints):
    def is_top(j):
        above = cmds.listRelatives(j, parent=True, fullPath=True)
        return not above or cmds.nodeType(above[0]) != "joint"
    return min([j for j in joints if is_top(j)], key=lambda p: (p.count("|"), p))


def bones_of(root):
    bones, note = sw.read_bones(root)
    return bones


def leaf_of(bones, canonical):
    for leaf, bone in bones.items():
        if bone.get("canonical") == canonical:
            return leaf
    return canonical if canonical in bones else None


def worlds(paths, frames):
    return np.array([[cmds.getAttr(p + ".worldMatrix[0]", time=t) for t in frames] for p in paths]).reshape(
        len(paths), len(frames), 4, 4)


def curve_snapshot(paths):
    out = {}
    for p in paths:
        for c in cmds.listConnections(p, source=True, destination=False, type="animCurve") or []:
            out[c] = tuple(cmds.keyframe(c, query=True, valueChange=True) or ())
    return out


BODY = ("pelvis", "spine", "neck", "head", "clavicle", "upperarm", "lowerarm", "hand", "thigh", "calf", "foot", "ball")


def capture(root, frames):
    """A skeleton's walk for a picture: its body bones (side 'l' / 'r' / 'c'), their own and their parents'
    worlds on `frames`, the pelvis's worlds."""
    bones = bones_of(root)
    shown = [(leaf, b) for leaf, b in bones.items()
             if (b.get("canonical") or "").split("_")[0] in BODY and b.get("parent") in bones
             and bones[b["parent"]].get("canonical") != "root"]
    sides = [((b.get("canonical") or "")[-1] if (b.get("canonical") or "").endswith(("_l", "_r")) else "c")
             for leaf, b in shown]
    paths = [b["path"] for leaf, b in shown] + [bones[b["parent"]]["path"] for leaf, b in shown]
    return sides, worlds(paths, list(frames)), worlds([bones[leaf_of(bones, "pelvis")]["path"]], list(frames))[0]


def draw_sheet(path, panels):
    """Panels (label, capture, view) - 'side': forward right; 'front': the character's left right, facing the
    viewer - every third frame as an onion skin; the left side blue, the right orange, the pelvis's path
    dashed."""
    from PySide6 import QtCore, QtGui
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
    width, height, cols = 760, 330, 2
    rows = (len(panels) + 1) // cols
    image = QtGui.QImage(width * cols, height * rows, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor(250, 249, 246))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    colours = {"l": QtGui.QColor(70, 140, 230), "r": QtGui.QColor(235, 120, 50), "c": QtGui.QColor(60, 60, 60)}
    for k, (label, (sides, w, pw), view) in enumerate(panels):
        ox, oy = (k % cols) * width, (k // cols) * height
        axis, sign, x0 = (2, 1.0, 40) if view == "side" else (0, 1.0, width // 2)   # front: its left on the right
        origin, ground, scale = pw[0, 3, axis], oy + height - 25, 1.45
        across = lambda p: ox + x0 + sign * (p[axis] - origin) * scale
        painter.setPen(QtGui.QPen(QtGui.QColor(190, 190, 190), 1))
        painter.drawLine(ox + 10, ground, ox + width - 10, ground)
        painter.setPen(QtGui.QColor(30, 30, 30))
        painter.setFont(QtGui.QFont("Segoe UI", 11))
        painter.drawText(ox + 14, oy + 22, label)
        floor = min(float(w[:, :, 3, 1].min()), 0.0)
        half = len(sides)
        steps = list(range(0, w.shape[1], 3 if view == "side" else 5))
        for n, f in enumerate(steps):
            alpha = 80 + int(175 * n / max(1, len(steps) - 1))
            for i, side in enumerate(sides):
                colour = QtGui.QColor(colours[side])
                colour.setAlpha(alpha)
                painter.setPen(QtGui.QPen(colour, 1.6))
                a, c = w[half + i, f, 3], w[i, f, 3]
                painter.drawLine(QtCore.QPointF(across(a), ground - (a[1] - floor) * scale),
                                 QtCore.QPointF(across(c), ground - (c[1] - floor) * scale))
        painter.setPen(QtGui.QPen(QtGui.QColor(200, 40, 90), 1.3, QtCore.Qt.DashLine))
        painter.drawPolyline([QtCore.QPointF(across(p[3]), ground - (p[3, 1] - floor) * scale) for p in pw])
    painter.end()
    image.save(path)


TEMP = tempfile.mkdtemp(prefix="walkverify_")
sw.WALKS = os.path.join(TEMP, "walks")
try:
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.undoInfo(state=True, infinity=True)
    source = fbx_import(WALK_FBX)
    gate(source.endswith("|root"), "the walk imported: %s" % source)
    cmds.currentTime(0)
    name, line = sw.save_walk(source, "Walk_01")
    walk, statics, start = sw.load_walk(name)
    template = sw.wf.read_template(sw.TEMPLATE)
    gate(os.path.exists(sw.wf.path_for(sw.WALKS, name)) and statics["thigh_l"]["rest"] == template["thigh_l"]["world_matrix"]
         and "has no skin" not in line, "saved, resting on Manny's bind: " + line)
    P = walk.P
    src_paths = [source] + sorted(cmds.listRelatives(source, allDescendents=True, type="joint", fullPath=True) or [])
    src_leaf = dict((p.rsplit("|", 1)[-1], p) for p in src_paths)
    src = dict((leaf, w) for leaf, w in zip(src_leaf, worlds(list(src_leaf.values()), range(start, start + P + 1))))
    src_before = curve_snapshot(src_paths)
    travel = float(np.linalg.norm(walk.travel))

    # how far the walk's own leg bones breathe against Manny's rest lengths (its left leg is keyed 0.05 cm
    # long and short): a skeleton keeps ITS lengths, so its knees stand that much off the walk's
    def rest_length(child, parent):
        return float(np.linalg.norm(np.array(template[child]["world_matrix"][12:15]) -
                                    np.array(template[parent]["world_matrix"][12:15])))
    breath = max(float(np.abs(np.linalg.norm(src[c][:, 3, :3] - src[p][:, 3, :3], axis=1) - rest_length(c, p)).max())
                 for side in "lr" for c, p in (("calf_" + side, "thigh_" + side), ("foot_" + side, "calf_" + side)))
    print("        the walk's leg bones breathe %.4f cm against their rest lengths" % breath)

    def check(root, label, given=None, expect_scale=None, pose=None, parts=sw.ALL_PARTS):
        started = time.time()
        result, info, text = sw.apply(root, name, given, pose, parts)
        took = time.time() - started
        print("        " + text)
        bones = bones_of(root)
        n = result.frames
        frames = range(start, start + n + 1)
        legs = {}
        for side in "lr":
            legs[side] = [bones[leaf_of(bones, "%s_%s" % (b, side))]["path"] for b in ("thigh", "calf", "foot")]
        pelvis = bones[leaf_of(bones, "pelvis")]["path"]
        top = bones[sorted(bones, key=lambda l: bones[l]["path"].count("|"))[0]]["path"]
        got = worlds([pelvis, top] + legs["l"] + legs["r"], frames)
        scale = info["scale"]
        # the stance feet: still as the walk's, x the size
        spreads = []
        for k, side in enumerate("lr"):
            foot = walk.feet[side]
            stance = [f for f in (foot.on + i for i in range(foot.length + 1)) if f <= n]
            ankle = got[4 + 3 * k, stance, 3, :3]
            src_ankle = src["foot_" + side][[f for f in stance], 3, :3]
            spreads.append((float(np.ptp(ankle, axis=0).max()), scale * float(np.ptp(src_ankle, axis=0).max())))
        # lengths
        length_err = 0.0
        for k in range(2):
            hip, knee, ankle = got[2 + 3 * k, :, 3, :3], got[3 + 3 * k, :, 3, :3], got[4 + 3 * k, :, 3, :3]
            length_err = max(length_err, float(np.ptp(np.linalg.norm(knee - hip, axis=1))),
                             float(np.ptp(np.linalg.norm(ankle - knee, axis=1))))
        moved = float(np.linalg.norm((got[1, n, 3, :3] - got[1, 0, 3, :3]) * [1, 0, 1]))
        stride = (given or {}).get("stride", 1.0)
        seam = float(np.abs((got[:, n] @ np.linalg.inv(got[0, n]))[2:] - (got[:, 0] @ np.linalg.inv(got[0, 0]))[2:]).max())
        ok = (all(abs(a - b) < 0.05 for a, b in spreads) and length_err < 1e-3 and seam < 2e-3
              and abs(moved - scale * stride * travel) < 0.05 and info["short"] < 1e-3
              and (expect_scale is None or abs(scale - expect_scale) < 0.01))
        gate(ok, "%s: size x%.3f, %d bones; stance spread L %.3f (walk x size %.3f) R %.3f (%.3f); lengths %.6f; "
             "travel %.2f cm (x%.3f); seam %.5f; drop up to %.4f; %.2f s"
             % (label, scale, len(bones), spreads[0][0], spreads[0][1], spreads[1][0], spreads[1][1],
                length_err, moved, moved / travel, seam, max(info["drop"]), took))
        return result, info, got

    # 1. Manny's skeleton (a twin): the walk itself, where Manny stands
    manny = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "manny")
    result, info, got = check(manny, "Manny skeleton", expect_scale=1.0)
    mb = bones_of(manny)
    paths = [mb[leaf]["path"] for leaf in sorted(mb) if leaf in src and not leaf.startswith(("ik_", "camera_", "weapon_", "interaction", "center_of_mass"))]
    names = [leaf for leaf in sorted(mb) if leaf in src and not leaf.startswith(("ik_", "camera_", "weapon_", "interaction", "center_of_mass"))]
    mw = worlds(paths, range(start, start + P + 1))
    offset = mw[names.index("root"), 0, 3, :3] - src["root"][0, 3, :3]
    rot_err = max(float(np.abs(mw[i, :, :3, :3] - src[leaf][:, :3, :3]).max()) for i, leaf in enumerate(names))
    pos_err = max(float(np.abs(mw[i, :, 3, :3] - offset - src[leaf][:, 3, :3]).max()) for i, leaf in enumerate(names))
    per = sorted(((float(np.abs(mw[i, :, 3, :3] - offset - src[leaf][:, 3, :3]).max()),
                   float(np.abs(mw[i, :, :3, :3] - src[leaf][:, :3, :3]).max()), leaf) for i, leaf in enumerate(names)),
                 reverse=True)
    print("        worst bones (cm, rot):", [(l, round(p, 4), round(r, 5)) for p, r, l in per[:8]])
    legless = max(p for p, r, l in per if not l.startswith(("thigh", "calf")))
    sink = max(info["drop"])
    gate(rot_err < 5e-3 and pos_err < 2 * breath + 1e-3 and legless < sink + 1e-3,
         "Manny is a twin: %d bones on the walk's rotations to %.7f, positions (moved %.3f cm to Manny's place) "
         "to %.6f cm - thighs and calves off by the walk's breathing legs, every other bone %.6f (the pelvis "
         "sinks %.4f where Manny's legs are that much shorter than the walk's)"
         % (len(names), rot_err, np.linalg.norm(offset), pos_err, legless, sink))

    # 1b. the goblin pose under the walk, on Manny (the animator's pose, saved from their scene by Save pose)
    if os.path.exists(POSE_FILE):
        shutil.copy(POSE_FILE, sw.wf.pose_path_for(sw.WALKS, "goblin"))
        prepared = sw.prepared_pose(name, "goblin")
        pose_bones = sw.wf.load_pose(POSE_FILE)[1]
        mb = bones_of(manny)
        path = lambda c: mb[leaf_of(mb, c)]["path"]
        cycle = range(start, start + P + 1)

        def posed(amount):
            result, info, got = check(manny, "Manny under the goblin pose x%.1f" % amount, {"pose": amount},
                                      expect_scale=1.0, pose="goblin", parts=("torso", "pelvis", "knees"))
            w = worlds([path(c) for c in ("pelvis", "neck_01", "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r",
                                          "foot_r", "root")], cycle)
            return info, w

        def height(w, info):
            return float(np.mean(w[0, :P, 3, 1] - w[8, :P, 3, 1] + np.array(info["drop"][:P])))

        def lean(chain):
            return math.degrees(math.acos(float(np.clip(chain[1] / np.linalg.norm(chain), -1.0, 1.0))))

        def knee(w, k, f):
            hip, kn, ankle = (w[2 + 3 * k + i, f, 3, :3] for i in range(3))
            e = (ankle - hip) / np.linalg.norm(ankle - hip)
            b = (kn - hip) - np.dot(kn - hip, e) * e
            return math.degrees(math.atan2(float(np.dot(b, walk.side)), float(np.dot(b, walk.fwd))))

        i0, w0 = posed(0.0)
        i1, w1 = posed(1.0)
        i5, w5 = posed(0.5)
        h0, h1, h5 = height(w0, i0), height(w1, i1), height(w5, i5)
        gate(abs(h1 - prepared["height"]) < 0.05 and abs(h5 - 0.5 * (h0 + h1)) < 0.05,
             "the pelvis at the pose's height: %.2f cm at Pose 1 (the pose %.2f), %.2f at 0, %.2f at 0.5"
             % (h1, prepared["height"], h0, h5))
        want = lean(np.array(pose_bones["neck_01"]["world"][12:15]) - np.array(pose_bones["pelvis"]["world"][12:15]))
        got1 = float(np.mean([lean(w1[1, f, 3, :3] - w1[0, f, 3, :3]) for f in range(P)]))
        got0 = float(np.mean([lean(w0[1, f, 3, :3] - w0[0, f, 3, :3]) for f in range(P)]))
        gate(abs(got1 - want) < 5.0 and got0 < 10.0,
             "the torso leans %.1f deg from up at Pose 1 (the pose %.1f), %.1f at 0" % (got1, want, got0))
        turns = []
        for k, side in enumerate("lr"):
            f = int(round(walk.feet[side].mid)) % P
            turns.append((knee(w1, k, f) - knee(w0, k, f), math.degrees(prepared["knee_turn"][side])))
        gate(all(abs(a - b) < 4.0 for a, b in turns),
             "the knees turned by the pose: left %.1f deg (the pose %.1f), right %.1f (%.1f)"
             % (turns[0][0], turns[0][1], turns[1][0], turns[1][1]))
    else:
        print("        (no %s: the goblin gates skipped)" % POSE_FILE)

    # 1c. the two-handed sword pose, every part, on Manny: the grip held through the walk
    if os.path.exists(SWORD_FILE):
        shutil.copy(SWORD_FILE, sw.wf.pose_path_for(sw.WALKS, "two_handed_sword"))
        held = sw.prepared_pose(name, "two_handed_sword")
        sword = sw.wf.load_pose(SWORD_FILE)[1]
        mb = bones_of(manny)
        path = lambda c: mb[leaf_of(mb, c)]["path"]
        cycle = range(start, start + P + 1)
        check(manny, "Manny under the two-handed sword x1, every part", {"pose": 1.0}, expect_scale=1.0,
              pose="two_handed_sword")
        names_ = ("hand_l", "hand_r", "weapon_r", "weapon_l", "pelvis", "neck_01", "foot_l", "foot_r", "ball_l",
                  "ball_r", "root")
        w = dict(zip(names_, worlds([path(c) for c in names_], cycle)))
        pm_ = lambda leaf: np.array(sword[leaf]["world"]).reshape(4, 4)
        grip = np.array([w["hand_l"][f] @ np.linalg.inv(w["hand_r"][f]) for f in range(P + 1)])
        want = pm_("hand_l") @ np.linalg.inv(pm_("hand_r"))
        gate(float(np.abs(grip - grip[0]).max()) < 1e-4 and float(np.abs(grip[:, 3, :3] - want[3, :3]).max()) < 0.05
             and float(np.abs(grip[:, :3, :3] - want[:3, :3]).max()) < 1e-3,
             "the grip held: the left hand in the right's space still to %.6f over the cycle, the pose's to %.4f cm"
             % (float(np.abs(grip - grip[0]).max()), float(np.abs(grip[:, 3, :3] - want[3, :3]).max())))
        errs = []
        for weapon, hand in (("weapon_r", "hand_r"), ("weapon_l", "hand_l")):
            rel = np.array([w[weapon][f] @ np.linalg.inv(w[hand][f]) for f in range(P + 1)])
            pose_rel = pm_(weapon) @ np.linalg.inv(pm_(hand))
            errs.append(float(np.abs(rel - pose_rel).max()))
        gate(max(errs) < 1e-3, "the weapon bones where the pose holds the sword: %.6f, %.6f" % tuple(errs))
        ml, mr = int(round(walk.feet["l"].mid)) % P, int(round(walk.feet["r"].mid)) % P
        gap = float(np.dot(w["foot_l"][ml, 3, :3] - w["foot_r"][mr, 3, :3], walk.side))
        walk_gap = float(np.dot(src["foot_l"][ml, 3, :3] - src["foot_r"][mr, 3, :3], walk.side))
        heading = lambda m, foot, ball, f: math.degrees(math.atan2(
            float(np.dot(m[ball][f, 3, :3] - m[foot][f, 3, :3], walk.side)),
            float(np.dot(m[ball][f, 3, :3] - m[foot][f, 3, :3], walk.fwd))))
        turned = [heading(w, "foot_" + s, "ball_" + s, f) - heading(src, "foot_" + s, "ball_" + s, f)
                  for s, f in (("l", ml), ("r", mr))]
        toe = [math.degrees(held["toe"][s]) for s in "lr"]
        gate(abs(gap - walk_gap - held["width"]) < 0.1 and all(abs(a - b) < 1.5 for a, b in zip(turned, toe)),
             "the feet: %.1f cm apart (the walk %.1f, the pose's extra %.1f), toes turned %.1f / %.1f deg (the pose "
             "%.1f / %.1f)" % (gap, walk_gap, held["width"], turned[0], turned[1], toe[0], toe[1]))
        height = float(np.mean(w["pelvis"][:P, 3, 1] - w["root"][:P, 3, 1]))
        gate(abs(height - held["height"]) < 0.5, "the pelvis at the pose's height: %.2f cm (the pose %.2f)"
             % (height, held["height"]))
    else:
        print("        (no %s: the sword gates skipped)" % SWORD_FILE)

    # 2. the Creep, the UE4 Mannequin, Mixamo, a small Manny
    creep = ma_import(os.path.join(ASSETS, "Creep_Skeleton.ma"), "creep")
    check(creep, "Creep skeleton")
    ue4 = fbx_import(os.path.join(ASSETS, "UE4_Mannequin.fbx"), "ue4")
    check(ue4, "UE4 Mannequin")
    if os.path.exists(MIXAMO_FBX):
        mixamo = fbx_import(MIXAMO_FBX, "mixamo")
        check(mixamo, "Mixamo Sweep Fall")
    else:
        print("        (no %s: Mixamo skipped)" % MIXAMO_FBX)
    small = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "small")
    shapes = [s for s in cmds.ls("small:*", type="mesh", long=True) or []]
    cmds.delete(cmds.ls("small:*", type="skinCluster") or [])
    cmds.delete([cmds.listRelatives(s, parent=True, fullPath=True)[0] for s in shapes if cmds.objExists(s)])
    for joint in [small] + (cmds.listRelatives(small, allDescendents=True, type="joint", fullPath=True) or []):
        t = cmds.getAttr(joint + ".translate")[0]
        cmds.setAttr(joint + ".translate", 0.6 * t[0], 0.6 * t[1], 0.6 * t[2])
    check(small, "Manny at 0.6", expect_scale=0.6)

    # 3. re-tune, Pick, Ctrl+Z
    cmds.currentTime(17)
    first_root = cmds.getAttr(creep + ".worldMatrix[0]", time=start)
    check(creep, "Creep, stride 1.3, from its stored place", {"stride": 1.3})
    again = cmds.getAttr(creep + ".worldMatrix[0]", time=start)
    walked, knobs, picked_pose, picked_parts = sw.pick(creep)
    gate(np.allclose(first_root, again, atol=1e-6) and walked == name and abs(knobs["stride"] - 1.3) < 1e-9,
         "re-tuned from the stored place (frame %d's root unmoved %.7f, the time at 17); Pick reads %s, stride %.2f"
         % (start, float(np.abs(np.array(first_root) - np.array(again)).max()), walked, knobs["stride"]))
    cmds.undo()
    back = worlds([creep], [start, start + P])[0]
    walked = float(np.linalg.norm((back[1, 3, :3] - back[0, 3, :3]) * [1, 0, 1]))
    gate(abs(walked - sw.wt.Retarget(walk, statics, bones_of(creep)).scale * travel) < 0.05,
         "one Ctrl+Z puts the defaults' keys back (travel %.2f cm)" % walked)
    gate(curve_snapshot(src_paths) == src_before, "the walk's own cycle untouched by five applies")

    # 4. onto its own skeleton: the cycle itself
    cmds.currentTime(start)
    result, info, text = sw.apply(source, name)
    own = worlds(list(src_leaf.values()), range(start, start + P + 1))
    helpers = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass")
    err = max(float(np.abs(own[i] - src[leaf]).max()) for i, leaf in enumerate(src_leaf)
              if not leaf.startswith(helpers))
    rest_err = max(float(np.abs(own[i] - src[leaf]).max()) for i, leaf in enumerate(src_leaf)
                   if not leaf.startswith(helpers + ("thigh", "calf")))
    gate(err < 2 * breath + 1e-3 and rest_err < max(info["drop"]) + 1e-3,
         "onto its own skeleton, the cycle itself to %.6f (thighs, calves) and %.6f (every other bone; the pelvis "
         "sinks up to %.4f) | %s" % (err, rest_err, max(info["drop"]), text))
    sheet = os.environ.get("WALK_SHEET")
    cycle = range(start, start + P + 1)
    if sheet:
        sw.apply(manny, name)
        targets = [("Walk_01 (its own skeleton)", source), ("Manny skeleton", manny), ("Creep skeleton", creep),
                   ("UE4 Mannequin", ue4), ("Manny at 0.6", small)]
        if os.path.exists(MIXAMO_FBX):
            targets.insert(4, ("Mixamo Sweep Fall", mixamo))
        draw_sheet(sheet, [(label, capture(root, cycle), "side") for label, root in targets])
        print("        picture: " + sheet)
    sword_sheet = os.environ.get("WALK_SWORD_SHEET")
    if sword_sheet and os.path.exists(SWORD_FILE):
        sw.apply(manny, name, {"pose": 0.0}, "two_handed_sword")
        plain = capture(manny, cycle)
        sw.apply(manny, name, {"pose": 1.0}, "two_handed_sword")
        held = capture(manny, cycle)
        draw_sheet(sword_sheet, [("Walk_01 on Manny - side", plain, "side"),
                                 ("the two-handed sword x1, every part - side", held, "side"),
                                 ("Walk_01 on Manny - front", plain, "front"),
                                 ("the two-handed sword x1, every part - front", held, "front")])
        print("        picture: " + sword_sheet)
    pose_sheet = os.environ.get("WALK_POSE_SHEET")
    if pose_sheet and os.path.exists(POSE_FILE):
        sw.apply(manny, name, {"pose": 0.0}, "goblin")
        plain = capture(manny, cycle)
        sw.apply(manny, name, {"pose": 1.0}, "goblin")
        goblin = capture(manny, cycle)
        draw_sheet(pose_sheet, [("Walk_01 on Manny - side", plain, "side"),
                                ("the goblin pose x1 - side", goblin, "side"),
                                ("Walk_01 on Manny - front", plain, "front"),
                                ("the goblin pose x1 - front", goblin, "front")])
        print("        picture: " + pose_sheet)
    try:
        sw.skeleton_root_of(cmds.createNode("transform", name="empty"))
        gate(False, "an empty transform was taken for a skeleton")
    except sw.REFUSALS as refusal:
        gate("holds no skeleton" in str(refusal), "refused: %s" % refusal)
finally:
    shutil.rmtree(TEMP, ignore_errors=True)

print("\n%d gates, %d failed%s" % (COUNT[0], len(FAILED), (": " + str(FAILED)) if FAILED else ""))
