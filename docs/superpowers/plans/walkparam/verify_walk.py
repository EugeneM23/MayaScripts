"""verify_walk.py - a saved walk onto skeletons, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk.py

Desktop/Walk_01.fbx (a temp copy) imported and saved as a walk (into a temp walks folder); then applied onto
the plugin's Manny skeleton (a twin: the walk itself, moved to where Manny stands), the Creep skeleton, the
UE4 Mannequin, the animator's Mixamo Sweep Fall.fbx (Downloads, when there) and a Manny shrunk to 0.6:
stance feet as still as the walk's (x the size), the stride x the size, bone lengths unchanged, the seam;
re-tuned from its stored place, Pick, one Ctrl+Z; onto its own skeleton: the cycle itself. Last, Balance on
Manny's keys: the CoM's change the pendulum's on the keyed feet (wider, slower, faster), the goblin's lean and
the sword's feet carried back over the support (WALK_BALANCE_SHEET draws it).
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


def draw_balance(path, walk, tops, figures):
    """The balance sheet. `tops` (label, Balance 0 run, Balance 1 run): two cycles from above - forward right,
    the character's left up, sideways x4 - the feet's prints, the pressure (green), the CoM at Balance 0
    (grey, dashed) and 1 (red). `figures` (label, Balance 0 run, 1 run, 'side' or 'front'): the skeleton at
    the left foot's mid-stance, its CoM and the CoM's plumb line to the floor, grey against red."""
    from PySide6 import QtCore, QtGui
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
    width, height, cols = 760, 420, 2
    panels = [("top",) + t for t in tops] + [("figure",) + f for f in figures if f[1] is not None]
    rows = (len(panels) + 1) // cols
    image = QtGui.QImage(width * cols, height * rows, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor(250, 249, 246))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    grey, red, green = QtGui.QColor(120, 120, 120), QtGui.QColor(210, 40, 60), QtGui.QColor(60, 160, 90)
    fwd, side, up = walk.fwd, walk.side, walk.up

    def pen(colour, w=1.6, dash=False, alpha=255):
        c = QtGui.QColor(colour)
        c.setAlpha(alpha)
        return QtGui.QPen(c, w, QtCore.Qt.DashLine if dash else QtCore.Qt.SolidLine)

    for k, panel in enumerate(panels):
        ox, oy = (k % cols) * width, (k // cols) * height
        painter.setPen(QtGui.QColor(30, 30, 30))
        painter.setFont(QtGui.QFont("Segoe UI", 11))
        painter.drawText(ox + 14, oy + 22, panel[1])
        painter.setFont(QtGui.QFont("Segoe UI", 9))
        if panel[0] == "top":
            _, label, off, on = panel
            n, line0 = on["n"], on["line"][0]
            span = on["line"][n] - line0
            sx, sy, cx, cy = 2.0, 4.0, ox + 26, oy + height / 2 + 6
            to = lambda p, cycle=0: QtCore.QPointF(cx + float(np.dot(p - line0 + cycle * span, fwd)) * sx,
                                                   cy - float(np.dot(p - line0 + cycle * span, side)) * sx * sy)
            for cycle in (0, 1):
                for s in walk.feet:
                    for f in range(n):
                        tau = f * walk.P / float(n)
                        if max(float(wm.periodic_cr(walk.ground["foot_" + s], tau)),
                               float(wm.periodic_cr(walk.ground["ball_" + s], tau))) < 0.5:
                            continue
                        painter.setPen(pen(QtGui.QColor(70, 140, 230) if s == "l" else QtGui.QColor(235, 120, 50),
                                           7, alpha=40))
                        painter.drawLine(to(on["feet"]["foot_" + s][f], cycle), to(on["feet"]["ball_" + s][f], cycle))
                cop = [on["line"][f] + on["cop"][f, 0] * fwd + on["cop"][f, 1] * side for f in range(n)]
                painter.setPen(pen(green, 1.2, alpha=170))
                painter.drawPolyline([to(p, cycle) for p in cop] + [to(cop[0], cycle + 1)])
                painter.setPen(pen(grey, 1.6, dash=True))
                painter.drawPolyline([to(p, cycle) for p in off["com"]])
                painter.setPen(pen(red, 2.2))
                painter.drawPolyline([to(p, cycle) for p in on["com"]])
            painter.setPen(QtGui.QColor(60, 60, 60))
            painter.drawText(ox + 14, oy + height - 14,
                             "from above, sideways x4 | grey dashed: Balance 0, sways %.1f cm | red: Balance 1, sways "
                             "%.1f cm | green: the feet's pressure" % (float(np.ptp(off["dev"][:, 1])),
                                                                         float(np.ptp(on["dev"][:, 1]))))
        else:
            _, label, off, on, view = panel
            across = fwd if view == "side" else side
            ground, scale = oy + height - 40, 1.75
            painter.setPen(pen(QtGui.QColor(190, 190, 190), 1))
            painter.drawLine(ox + 10, ground, ox + width - 10, ground)
            for run, colour, cx, name in ((off, grey, ox + width * 0.27, "Balance 0"),
                                          (on, red, ox + width * 0.73, "Balance 1")):
                sides, w, pw = run["stick"]
                f0, n = run["mid"], run["n"]
                base = run["line"][f0]
                at = lambda p: cx + float(np.dot(p - base, across)) * scale
                to = lambda p: QtCore.QPointF(at(p), ground - float(np.dot(p, up)) * scale)
                prints = []
                for s in walk.feet:                   # the feet on the ground: heel to toe on the floor
                    tau = f0 * walk.P / float(n)
                    if max(float(wm.periodic_cr(walk.ground["foot_" + s], tau)),
                           float(wm.periodic_cr(walk.ground["ball_" + s], tau))) < 0.5:
                        continue
                    a, b = run["feet"]["foot_" + s][f0], run["feet"]["ball_" + s][f0]
                    xa, xb = at(a), at(b)
                    prints.append(0.5 * (float(np.dot(a, across)) + float(np.dot(b, across))))
                    painter.setPen(pen(QtGui.QColor(40, 40, 40), 6, alpha=130))
                    painter.drawLine(QtCore.QPointF(min(xa, xb) - 5, ground), QtCore.QPointF(max(xa, xb) + 5, ground))
                half = len(sides)
                painter.setPen(pen(colour, 2.0))
                for i in range(half):
                    painter.drawLine(to(w[half + i, 0, 3, :3]), to(w[i, 0, 3, :3]))
                com = run["com"][f0]
                floor = com - np.dot(com, up) * up
                painter.setPen(pen(colour, 1.2, dash=True))
                painter.drawLine(to(com), to(floor))
                painter.setBrush(QtGui.QColor(colour))
                painter.setPen(pen(colour, 1.0))
                painter.drawEllipse(to(com), 6, 6)
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.setPen(QtGui.QColor(30, 30, 30))
                ahead = float(np.dot(com, across)) - float(np.mean(prints)) if prints else float("nan")
                word = ("ahead of" if ahead > 0 else "behind") if view == "side" else ("left of" if ahead > 0 else "right of")
                painter.drawText(QtCore.QPointF(cx - 120, oy + 50), "%s: the CoM %.1f cm %s the foot" % (
                    name, abs(ahead), word))
            painter.setPen(QtGui.QColor(60, 60, 60))
            pel = lambda run: float(run["pelvis"][:, 0 if view == "side" else 1].mean())
            moved = pel(on) - pel(off)
            way = ("back" if moved < 0 else "forward") if view == "side" else ("to its left" if moved > 0 else "to its right")
            painter.drawText(ox + 14, oy + height - 14, "the left foot's mid-stance | dot: the CoM, dashed: its plumb "
                             "line, bar: the foot down | the pelvis carried %.1f cm %s" % (abs(moved), way))
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
    OWN = walk.own_knobs()      # the walk's own pelvis (the defaults' Twist and Hip drop are people's)
    print("        the walk's own pelvis: Twist %.2f (x%.3f at its step: +-%.2f deg), Hip drop %.2f deg"
          % (OWN["pelvis_twist"], walk.twist_gain, OWN["pelvis_twist"] * walk.twist_gain, OWN["pelvis_list"]))
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
        # the stance feet: as still as the model's own, x the size (Foot placement plants them; without it
        # they slip as the walk's do)
        spreads = []
        for k, side in enumerate("lr"):
            foot = walk.feet[side]
            src_stance = [f for f in (foot.on + i for i in range(foot.length + 1)) if f <= P]
            stance = src_stance if n == P else [g for g in range(n + 1)
                                                if foot.on - 1e-9 <= g * P / float(n) <= src_stance[-1] + 1e-9]
            ankle = got[4 + 3 * k, stance, 3, :3]
            model = result.worlds[walk.index["foot_" + side], stance, 3, :3]
            spreads.append((float(np.ptp(ankle, axis=0).max()), scale * float(np.ptp(model, axis=0).max())))
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
        gate(ok, "%s: size x%.3f, %d bones; stance spread L %.3f (model x size %.3f) R %.3f (%.3f); lengths %.6f; "
             "travel %.2f cm (x%.3f); seam %.5f; drop up to %.4f; %.2f s"
             % (label, scale, len(bones), spreads[0][0], spreads[0][1], spreads[1][0], spreads[1][1],
                length_err, moved, moved / travel, seam, max(info["drop"]), took))
        return result, info, got

    # 1. Manny's skeleton (a twin): the walk itself, where Manny stands
    manny = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "manny")
    result, info, got = check(manny, "Manny skeleton, the walk's own knobs", OWN, expect_scale=1.0)
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
            result, info, got = check(manny, "Manny under the goblin pose x%.1f" % amount, dict(OWN, pose=amount),
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
        for k, side in enumerate("lr"):     # no Feet part: the toes stay, the knee meets them half way
            f = int(round(walk.feet[side].mid)) % P
            met = wm.meet(prepared["knee_turn"][side], 0.0, wm.DEFAULTS["knee_foot"])[0]
            turns.append((knee(w1, k, f) - knee(w0, k, f), math.degrees(met), math.degrees(prepared["knee_turn"][side])))
        gate(all(abs(a - b) < 4.0 for a, b, c in turns),
             "the knees turned by the pose, met by their feet: left %.1f deg (%.1f; the pose %.1f), right %.1f "
             "(%.1f; %.1f)" % (turns[0] + turns[1]))
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
        held_result = check(manny, "Manny under the two-handed sword x1, every part (the walk's own feet)",
                            {"pose": 1.0, "foot_placement": 0.0},
                            expect_scale=1.0, pose="two_handed_sword")[0]
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
        toe = [math.degrees(wm.meet(held["knee_turn"][s], held["toe"][s], wm.DEFAULTS["knee_foot"])[1]) for s in "lr"]
        gate(abs(gap - walk_gap - held["width"]) < 0.1 and all(abs(a - b) < 1.5 for a, b in zip(turned, toe)),
             "the feet: %.1f cm apart (the walk %.1f, the pose's extra %.1f), toes turned %.1f / %.1f deg (the pose "
             "%.1f / %.1f)" % (gap, walk_gap, held["width"], turned[0], turned[1], toe[0], toe[1]))
        sink = np.array(held_result.info["drop"][:P])     # the reach's drop under Balance's carry over the feet
        height = float(np.mean(w["pelvis"][:P, 3, 1] - w["root"][:P, 3, 1] + sink))
        gate(abs(height - held["height"]) < 0.5, "the pelvis at the pose's height: %.2f cm (the pose %.2f; the "
             "reach lowers it up to %.2f cm where Balance carries it over the wide feet)"
             % (height, held["height"], float(sink.max())))
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
    result, info, text = sw.apply(source, name, OWN)
    own = worlds(list(src_leaf.values()), range(start, start + P + 1))
    helpers = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass")
    err = max(float(np.abs(own[i] - src[leaf]).max()) for i, leaf in enumerate(src_leaf)
              if not leaf.startswith(helpers))
    rest_err = max(float(np.abs(own[i] - src[leaf]).max()) for i, leaf in enumerate(src_leaf)
                   if not leaf.startswith(helpers + ("thigh", "calf")))
    gate(err < 2 * breath + 1e-3 and rest_err < max(info["drop"]) + 1e-3,
         "onto its own skeleton, the cycle itself to %.6f (thighs, calves) and %.6f (every other bone; the pelvis "
         "sinks up to %.4f) | %s" % (err, rest_err, max(info["drop"]), text))
    # 5. Balance: the centre of mass over the feet, measured on Manny's keys (a twin: the model's names)
    mb = bones_of(manny)
    weighed = [(mb[leaf]["path"], walk.mass[j]) for j, leaf in enumerate(walk.names) if walk.mass[j] > 0.0]
    gate(all(leaf in mb for j, leaf in enumerate(walk.names) if walk.mass[j] > 0.0) and
         abs(sum(m for _, m in weighed) - 1.0) < 1e-9,
         "the masses on Manny's bones: %d weighed joints; this walk's body follows its pendulum %.2f forward, %.2f "
         "sideways (fitted on its own CoM against its feet's pressure)" % (len(weighed), walk.follow[0], walk.follow[1]))

    def keyed_balance(label, given, pose=None, parts=sw.ALL_PARTS):
        """Applied onto Manny; its keyed CoM, its feet's pressure and its root line's frame, (fwd, side, up)
        against the root's own straight line, a frame (the seam dropped)."""
        result, info, got = check(manny, label, given, expect_scale=1.0, pose=pose, parts=parts)
        n = result.frames
        frames = range(start, start + n + 1)
        w = worlds([p for p, _ in weighed], frames)
        com = np.tensordot(np.array([m for _, m in weighed]), w[:, :, 3, :3], axes=(0, 0))
        root = worlds([mb["root"]["path"]], frames)[0][:, 3, :3]
        line = root[0] + np.outer(np.arange(n + 1) / float(n), root[n] - root[0])
        mats = dict((nm, worlds([mb[nm]["path"]], frames)[0][:n]) for nm in walk.ground)
        feet = dict((nm, m[:, 3, :3]) for nm, m in mats.items())
        heels = dict((s, feet["foot_" + s] + np.einsum("i,fij->fj", walk.heel_loc[s], mats["foot_" + s][:, :3, :3]))
                     for s in walk.feet)
        cop = walk.pressure(feet, [f * P / float(n) for f in range(n)])
        dev = ((com - line) @ walk.basis.T)[:n]
        mid = int(round(walk.feet["l"].mid * n / float(P))) % n
        return {"result": result, "dev": dev, "cop": ((cop - line[:n]) @ walk.basis.T)[:, :2], "n": n,
                "pelvis": ((got[0, :n, 3, :3] - line[:n]) @ walk.basis.T), "frames": frames, "line": line,
                "feet": feet, "heels": heels, "com": com, "mid": mid, "stick": capture(manny, [start + mid])}

    def demeaned(v):
        return v - v.mean(axis=0)

    def same_feet(on, off):
        """How far Balance moves a planted foot (the frames the model plants it): a frame, the less moved of its
        heel and its ball - the point it rolls about (under a carried hip it may roll further over it, never
        slide; a foot in the air may pass nearer the body)."""
        n, worst = on["n"], 0.0
        for s in walk.feet:
            ball, heel = off["feet"]["ball_" + s], off["heels"][s]
            planted = off["result"].info["placement"]["planted"][s]
            for f in range(n):
                if not planted[f]:
                    continue
                worst = max(worst, min(float(np.abs(on["feet"]["ball_" + s][f] - ball[f]).max()),
                                       float(np.abs(on["heels"][s][f] - heel[f]).max())))
        return worst

    walk0 = keyed_balance("Manny, the walk (its own knobs, Balance 1)", OWN)
    gate(walk0["result"].info["balance"]["carry"] < 1e-6 and
         float(np.abs(demeaned(walk0["dev"][:, :2]) - demeaned(walk.s_dev[:, :2])).max()) < 0.01,
         "at the walk's own knobs nothing is carried and Manny's CoM is the walk's: %.4f cm (sways %.2f cm)"
         % (float(np.abs(demeaned(walk0["dev"][:, :2]) - demeaned(walk.s_dev[:, :2])).max()),
            float(np.ptp(walk0["dev"][:, 1]))))

    def pendulum_gate(label, given):
        on = keyed_balance("Manny, %s, Balance 1" % label, dict(given, balance=1.0))
        off = keyed_balance("Manny, %s, Balance 0" % label, dict(given, balance=0.0))
        n, k = on["n"], on["result"].info["knobs"]
        h = float(off["dev"][:, 2].mean())
        l_new = wm.pendulum(on["cop"], n / walk.fps, h)
        l_src = np.array([wm.periodic_cr(walk.l_dev, f * P / float(n)) for f in range(n)])
        gain = walk.follow * np.array([k["exaggeration"], k["sway"] * k["exaggeration"]])
        predicted = gain * (demeaned(l_new) - demeaned(l_src))
        measured = demeaned(on["dev"][:, :2]) - demeaned(off["dev"][:, :2])
        miss = float(np.abs(predicted - measured).max())
        sways = float(np.ptp(on["dev"][:, 1])), float(np.ptp(off["dev"][:, 1]))
        gate(miss < 0.05 and same_feet(on, off) < 1e-3,
             "%s: the CoM's change is the pendulum's on the keyed feet to %.4f cm; it sways %.2f cm (Balance 0: "
             "%.2f, the walk %.2f); the pelvis carried up to %.2f cm, the feet where Balance 0 puts them to %.6f"
             % (label, miss, sways[0], sways[1], float(np.ptp(walk.s_dev[:, 1])),
                on["result"].info["balance"]["carry"], same_feet(on, off)))
        return on, off, sways

    spread = walk.feet["l"].coords[1] - walk.feet["r"].coords[1]
    wide = pendulum_gate("the feet 20 cm wider (Stance x%.2f)" % ((spread + 20.0) / spread),
                         {"stance": (spread + 20.0) / spread})
    gate(wide[2][0] > wide[2][1] + 2.0, "wider feet sway the CoM more: %.2f cm against %.2f" % wide[2][:2])
    slow = pendulum_gate("tempo 45 (slower)", {"tempo": 45})
    fast = pendulum_gate("tempo 22 (faster)", {"tempo": 22})
    gate(slow[2][0] > slow[2][1] + 0.2 and fast[2][0] < fast[2][1] - 0.2,
         "slower sways more (%.2f against %.2f), faster less (%.2f against %.2f)"
         % (slow[2][0], slow[2][1], fast[2][0], fast[2][1]))
    long_ = keyed_balance("Manny, stride 1.3, Balance 1", {"stride": 1.3})
    gate(long_["result"].info["balance"]["residual"] < 0.05 and long_["result"].info["balance"]["carry"] > 0.1,
         "stride 1.3: Balance takes the pelvis's forward swing over from the stride's guess - carried up to %.2f cm, "
         "the CoM on its pendulum to %.4f cm" % (long_["result"].info["balance"]["carry"],
                                                long_["result"].info["balance"]["residual"]))

    posed_on = posed_off = sword_on = sword_off = None
    if os.path.exists(POSE_FILE):
        posed_on = keyed_balance("Manny, the goblin x1, Balance 1", {"pose": 1.0, "balance": 1.0}, "goblin",
                                 ("torso", "pelvis", "knees"))
        posed_off = keyed_balance("Manny, the goblin x1, Balance 0", {"pose": 1.0, "balance": 0.0}, "goblin",
                                  ("torso", "pelvis", "knees"))
        mean = lambda run: run["dev"][:, :2].mean(axis=0)
        held, leaned = mean(posed_on), mean(posed_off)
        own = mean(walk0) + (posed_on["cop"].mean(axis=0) - walk0["cop"].mean(axis=0))   # the knees turn the feet
        back = float((posed_on["pelvis"][:, 0] - posed_off["pelvis"][:, 0]).mean())
        gate(float(np.abs(held - own).max()) < 0.1 and leaned[0] - own[0] > 1.0 and back < -1.0
             and same_feet(posed_on, posed_off) < 1e-3,
             "the goblin's lean: at Balance 0 the CoM stands %.2f cm ahead of the walk's over these feet (%.2f "
             "aside); Balance 1 carries the pelvis %.2f cm back and the CoM over the feet again to %.3f cm; the feet "
             "unmoved %.6f" % (leaned[0] - own[0], leaned[1] - own[1], -back, float(np.abs(held - own).max()),
                               same_feet(posed_on, posed_off)))
    if os.path.exists(SWORD_FILE):
        sword_on = keyed_balance("Manny, the two-handed sword x1, Balance 1", {"pose": 1.0, "balance": 1.0},
                                 "two_handed_sword")
        sword_off = keyed_balance("Manny, the two-handed sword x1, Balance 0", {"pose": 1.0, "balance": 0.0},
                                  "two_handed_sword")
        want = walk0["dev"][:, :2].mean(axis=0) + (sword_on["cop"].mean(axis=0) - walk0["cop"].mean(axis=0))
        got_ = sword_on["dev"][:, :2].mean(axis=0)
        off_ = sword_off["dev"][:, :2].mean(axis=0)
        gate(float(np.abs(got_ - want).max()) < 0.1,
             "the sword: the CoM's mean moves with the feet's pressure (the pose's wider, turned feet) to %.3f cm "
             "- %.2f / %.2f cm (forward / aside) from the walk's, at Balance 0 %.2f / %.2f"
             % (float(np.abs(got_ - want).max()), *(got_ - walk0["dev"][:, :2].mean(axis=0)),
                *(off_ - walk0["dev"][:, :2].mean(axis=0))))
    # 6. the legs and the pelvis on Manny's keys: Twist and Hip drop, the chest, Stance, Swing out, the shins
    def keyed_model(root, n):
        """Manny's keys as the model's joints (J, n+1, 4, 4) - a twin: the same names."""
        bones = bones_of(root)
        out = np.tile(np.eye(4), (len(walk.names), n + 1, 1, 1))
        have = [(j, bones[leaf]["path"]) for j, leaf in enumerate(walk.names) if leaf in bones]
        for (j, _), m in zip(have, worlds([p for _, p in have], range(start, start + n + 1))):
            out[j] = m
        return out

    def shin_twist(m, side):
        """The knee's hinge against the foot's sideways axis about the shin, a frame (degrees, folded into
        -90..90: a hinge has no front or back)."""
        i = walk.index
        h, k, a = (m[i["%s_%s" % (b, side)], :-1, 3, :3] for b in ("thigh", "calf", "foot"))
        foot = m[i["foot_" + side], :-1, :3, :3]
        rest = walk.rot[i["foot_" + side], int(round(walk.feet[side].mid)) % P]   # the walk's own foot standing
        ax = int(np.argmax(np.abs(rest @ walk.side)))
        lat = foot[:, ax, :] * np.sign(rest[ax] @ walk.side)
        s_ax = (a - k) / np.linalg.norm(a - k, axis=1)[:, None]
        hinge = np.cross(k - h, a - k)
        hp = hinge - np.sum(hinge * s_ax, axis=1)[:, None] * s_ax
        lp = lat - np.sum(lat * s_ax, axis=1)[:, None] * s_ax
        tw = np.degrees(np.arctan2(np.sum(np.cross(hp, lp) * s_ax, axis=1), np.sum(hp * lp, axis=1)))
        return (tw + 90.0) % 180.0 - 90.0

    def yaw(m, name):
        rot = m[walk.index[name], :-1, :3, :3]
        ax = int(np.argmax(np.abs(rot[0] @ walk.fwd)))
        v = rot[:, ax, :] * np.sign(rot[0, ax] @ walk.fwd)
        return np.degrees(np.arctan2(v @ walk.side, v @ walk.fwd))

    runs = {}
    for label, given in (("own", OWN), ("defaults", None),     # "more" keeps the walk's own chest (Chest twist, sway)
                         ("more", {"pelvis_twist": 9.0, "pelvis_list": 7.0, "chest_twist": OWN["chest_twist"],
                                   "chest_sway": OWN["chest_sway"]})):
        result, info, got = check(manny, "Manny, the pelvis - %s" % label, given, expect_scale=1.0)
        runs[label] = keyed_model(manny, result.frames)
    fit = dict((label, walk.pelvis_fit(m)) for label, m in runs.items())
    g = walk.twist_gain
    gate(abs(fit["own"][0] - OWN["pelvis_twist"] * g) < 0.05 and abs(fit["own"][1] - OWN["pelvis_list"]) < 0.05
         and abs(fit["defaults"][0] - 5.0 * g) < 0.3 and abs(fit["defaults"][1] - 4.0) < 0.3
         and abs(fit["more"][0] - 9.0 * g) < 0.3 and abs(fit["more"][1] - 7.0) < 0.3,
         "the hip line on Manny's keys: twist +-%.2f / drop +-%.2f deg at the walk's own; +-%.2f / +-%.2f at the "
         "defaults (asked %.2f / 4); +-%.2f / +-%.2f at Twist 9, Hip drop 7 (asked %.2f / 7)"
         % (fit["own"] + fit["defaults"] + (5.0 * g,) + fit["more"] + (9.0 * g,)))
    chest = walk.index["spine_05"]
    held_chest = float(np.abs(runs["more"][chest, :, :3, :3] - runs["own"][chest, :, :3, :3]).max())
    gate(held_chest < 1e-4, "the lower back takes the added twist and drop back: the chest turns as at the walk's own "
         "to %.6f" % held_chest)
    spread_l = walk.feet["l"].coords[1] - walk.feet["r"].coords[1]
    if os.path.exists(POSE_FILE):
        prepared = sw.prepared_pose(name, "goblin")
        result, info, got = check(manny, "Manny, the goblin x1 every part, Stance 0.35 (the walk's own feet)",
                                  {"pose": 1.0, "stance": 0.35, "foot_placement": 0.0}, expect_scale=1.0,
                                  pose="goblin")
        gob = keyed_model(manny, result.frames)
        ml, mr = (int(round(walk.feet[x].mid)) % P for x in "lr")
        apart = float(np.dot(gob[walk.index["foot_l"], ml, 3, :3] - gob[walk.index["foot_r"], mr, 3, :3], walk.side))
        want = 0.35 * (spread_l + prepared["width"])
        twists = dict((side, (shin_twist(gob, side), shin_twist(runs["own"], side))) for side in "lr")
        worst = max(float(np.abs(t[0]).max()) for t in twists.values())
        walk_worst = max(float(np.abs(t[1]).max()) for t in twists.values())
        corr = lambda m: float(np.corrcoef(yaw(m, "pelvis") - yaw(m, "pelvis").mean(),
                                           yaw(m, "spine_05") - yaw(m, "spine_05").mean())[0, 1])
        gate(abs(apart - want) < 0.1 and result.info["swing_in"] < 0.5 and info["short"] < 1e-3
             and worst <= max(20.0, walk_worst + 3.0) and corr(gob) < -0.6,
             "the goblin, every part, Stance 0.35: the feet %.1f cm apart (0.35 x (the walk's %.1f + the pose's %.1f)); "
             "no foot out of reach (%.2f cm nearer the body); the shins twist up to %.1f deg (the walk's own %.1f); "
             "the chest counter-turns against the pelvis, corr %.2f (the walk's %.2f)"
             % (apart, spread_l, prepared["width"], result.info["swing_in"], worst, walk_worst, corr(gob),
                corr(runs["own"])))
    out_run = keyed_model(manny, check(manny, "Manny, Swing out 8", dict(OWN, swing_out=8.0), expect_scale=1.0)[0].frames)
    bows = []
    for side, sign in (("l", 1.0), ("r", -1.0)):
        j = walk.index["foot_" + side]
        across = sign * (out_run[j, :P, 3, :3] - runs["own"][j, :P, 3, :3]) @ walk.side
        down = [f for f in range(P) if walk.down(side, f)]
        bows.append((float(across.max()), float(np.abs(across[down]).max()) if down else 0.0))
    gate(all(abs(b - 8.0) < 0.3 and d < 1e-3 for b, d in bows),
         "Swing out 8: the swinging feet bow out %.2f / %.2f cm, the feet on the ground stay to %.6f / %.6f"
         % (bows[0][0], bows[1][0], bows[0][1], bows[1][1]))
    lag_run = keyed_model(manny, check(manny, "Manny, Foot lag 2", dict(OWN, foot_lag=2.0), expect_scale=1.0)[0].frames)
    errs = []
    for side in "lr":
        fo, ca = walk.index["foot_" + side], walk.index["calf_" + side]
        for f in range(P):
            if walk.swing_at(side, float(f)) >= 1.0:
                now = lag_run[fo, f, :3, :3] @ lag_run[ca, f, :3, :3].T
                late = src["foot_" + side][(f - 2) % P, :3, :3] @ src["calf_" + side][(f - 2) % P, :3, :3].T
                errs.append(math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(now) @ wm.orthonormal(late).T)))))
    gate(errs and max(errs) < 0.05, "Foot lag 2: mid-swing the foot hangs in its calf as the walk's 2 frames earlier, "
         "to %.4f deg over %d frames" % (max(errs) if errs else -1.0, len(errs)))

    # Foot placement (on at the defaults): a foot on the ground never slides, one foot is always down, and the
    # trailing foot rolls over its ball rather than the pelvis dropping
    def feet_of(m, n):
        """A cycle's feet on the keys: per foot (down a frame - its ankle or ball within CONTACT_TOL of its own
        lowest -, the least of its heel point's and ball's slide along the ground a frame step, how high its
        heel point stands while its ball is on the ground - 0 elsewhere)."""
        out = {}
        flat = lambda v: v - np.outer(v @ walk.up, walk.up)
        for side in "lr":
            ankle = m[walk.index["foot_" + side], :n + 1, 3, :3]
            ball = m[walk.index["ball_" + side], :n + 1, 3, :3]
            heel = ankle + np.einsum("i,fij->fj", walk.heel_loc[side], m[walk.index["foot_" + side], :n + 1, :3, :3])
            h = lambda v: v @ walk.up - (v[:n] @ walk.up).min()
            down = (h(ankle)[:n] <= wm.CONTACT_TOL) | (h(ball)[:n] <= wm.CONTACT_TOL)
            slide = np.minimum(np.linalg.norm(np.diff(flat(heel), axis=0), axis=1),
                               np.linalg.norm(np.diff(flat(ball), axis=0), axis=1))
            on_ball = h(ball)[:n] <= wm.CONTACT_TOL
            raised = np.where(on_ball, (heel[:n] - ball[:n]) @ walk.up, 0.0)
            out[side] = (down, slide, raised)
        return out

    def runs_of(mask):
        mask = list(mask)
        if all(mask) or not any(mask):
            return [len(mask)] if all(mask) else []
        k = mask.index(False)
        found, run = [], 0
        for v in mask[k:] + mask[:k] + [False]:
            if v:
                run += 1
            elif run:
                found.append(run)
                run = 0
        return found

    def placement_numbers(m, n):
        feet = feet_of(m, n)
        held = max(float(feet[s][1][feet[s][0] & np.roll(feet[s][0], -1)].max()) for s in "lr")
        both_move = [f for f in range(n) if feet["l"][1][f] > 0.5 and feet["r"][1][f] > 0.5]
        both = feet["l"][0] & feet["r"][0]
        neither = int(np.sum(~feet["l"][0] & ~feet["r"][0]))
        return feet, held, both_move, runs_of(both), neither

    placed_result = check(manny, "Manny, the defaults (Foot placement 1)", None, expect_scale=1.0)[0]
    placed = keyed_model(manny, placed_result.frames)
    _, own_held, own_both, own_runs, own_neither = placement_numbers(runs["own"], P)
    _, held, both_move, both_runs, neither = placement_numbers(placed, placed_result.frames)
    gate(held < 0.2 and own_held > 0.5,
         "Foot placement: a foot on the ground slides at most %.3f cm a frame (heel or ball; the walk's own %.3f)"
         % (held, own_held))
    gate(not both_move and own_both and neither == 0 and len(both_runs) == 2 and min(both_runs) >= 2,
         "Foot placement: no frame where both feet move (the walk's own: %s); both feet down %s frames at the "
         "steps (the walk's own %s), never neither" % (own_both, both_runs, own_runs))
    long_free = check(manny, "Manny, stride 1.3, no Foot placement", {"stride": 1.3, "foot_placement": 0.0},
                      expect_scale=1.0)[0]
    long_placed = check(manny, "Manny, stride 1.3", {"stride": 1.3}, expect_scale=1.0)[0]
    lp = keyed_model(manny, long_placed.frames)
    feet_long, held_long, both_long, runs_long, neither_long = placement_numbers(lp, long_placed.frames)
    pitch_free = feet_of(keyed_model(manny, long_free.frames), long_free.frames)["l"][2]
    pitch_long = feet_long["l"][2]
    gate(held_long < 0.25 and not both_long and neither_long == 0 and min(runs_long) >= 1
         and long_placed.info["lowered"] <= long_free.info["lowered"] + 0.05,
         "Foot placement at stride 1.3: slides %.3f cm a frame at most, both down %s frames; the trailing foot rolls "
         "over its ball, the heel up to %.1f cm over it (without placement %.1f) and the pelvis drops %.2f cm (without "
         "placement %.2f)" % (held_long, runs_long, pitch_long.max(), pitch_free.max(), long_placed.info["lowered"],
                              long_free.info["lowered"]))
    if os.path.exists(POSE_FILE):
        gob_result = check(manny, "Manny, the goblin x1 every part (Foot placement 1)", {"pose": 1.0},
                           expect_scale=1.0, pose="goblin")[0]
        _, held_gob, both_gob, runs_gob, neither_gob = placement_numbers(keyed_model(manny, gob_result.frames),
                                                                         gob_result.frames)
        gate(held_gob < 0.25 and not both_gob and neither_gob == 0 and min(runs_gob) >= 1,
             "Foot placement under the goblin, every part: slides %.3f cm a frame at most, both feet down %s frames "
             "at the steps, never neither" % (held_gob, runs_gob))

    balance_sheet = os.environ.get("WALK_BALANCE_SHEET")
    if balance_sheet:
        draw_balance(balance_sheet, walk, [
            ("The feet 20 cm wider - the CoM from above", wide[1], wide[0]),
            ("Tempo 45, slower - the CoM from above", slow[1], slow[0]),
        ], [("The goblin x1 - from the side", posed_off, posed_on, "side"),
            ("The two-handed sword x1 - from the front", sword_off, sword_on, "front")])
        print("        picture: " + balance_sheet)

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
    # the upper body on Manny's keys: the chest's degrees, the arms' inertia, a held weapon trailing as one
    def segment_lengths(m, sides="lr"):
        worst = 0.0
        i = walk.index
        for side in sides:
            for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_")):
                d = np.linalg.norm(m[i[b + side], :, 3, :3] - m[i[a + side], :, 3, :3], axis=1)
                worst = max(worst, float(np.ptp(d)))
        return worst

    def forearm_peak(m, side, n):
        i = walk.index
        d = m[i["hand_" + side], :n, 3, :3] - m[i["lowerarm_" + side], :n, 3, :3]
        d = d / np.linalg.norm(d, axis=1)[:, None]
        x = np.degrees(np.arcsin(np.clip(d @ walk.fwd, -1, 1)))
        x = x - x.mean()
        t = np.arange(n) / float(n)
        c, s_ = 2.0 / n * float(np.dot(x, np.cos(2 * math.pi * t))), 2.0 / n * float(np.dot(x, np.sin(2 * math.pi * t)))
        return math.hypot(c, s_), math.atan2(s_, c) / (2.0 * math.pi) * n

    chest_result = sw.apply(manny, name, {"chest_twist": 10.0, "chest_sway": 7.0, "arm_drag": 0.0})[0]
    keyed = keyed_model(manny, chest_result.frames)
    got = walk.chest_fit(keyed)
    want = (10.0 * walk.twist_gain, 7.0)
    gate(abs(got[0] - want[0]) < 0.3 and abs(got[1] - want[1]) < 0.3,
         "Chest twist 10 and sway 7 on Manny's keys: the shoulders turn +-%.2f deg (asked %.2f) and tilt +-%.2f (asked "
         "%.2f)" % (got[0], want[0], got[1], want[1]))
    plain_arms = keyed_model(manny, sw.apply(manny, name, {"arm_drag": 0.0})[0].frames)
    drag_result = sw.apply(manny, name, {"arm_drag": 3.0, "arm_bounce": 0.6})[0]
    dragged = keyed_model(manny, drag_result.frames)
    n_d = drag_result.frames
    lates = []
    for side in "lr":
        a0, p0 = forearm_peak(plain_arms, side, n_d)
        a1, p1 = forearm_peak(dragged, side, n_d)
        lates.append(((p1 - p0 + n_d / 2.0) % n_d - n_d / 2.0, a1 / max(a0, 1e-9)))
    seam = float(np.abs(dragged[:, n_d, :3, :3] - dragged[:, 0, :3, :3]).max())
    gate(all(late > 2.0 for late, _ in lates) and segment_lengths(dragged) < 1e-3 and seam < 2e-3,
         "Arm drag 3, bounce 0.6 on Manny's keys: the forearms swing %s frames late (x%s their swing), the arms' bones "
         "whole (%.6f), the loop closed (%.5f)" % (", ".join("%.1f" % l for l, _ in lates),
                                                   ", ".join("%.2f" % a for _, a in lates), segment_lengths(dragged), seam))
    if os.path.exists(SWORD_FILE):
        grip_target = keyed_model(manny, sw.apply(manny, name, {"pose": 1.0, "arm_drag": 0.0}, "two_handed_sword")[0].frames)
        grip_result = sw.apply(manny, name, {"pose": 1.0, "arm_drag": 3.0, "arm_bounce": 0.5}, "two_handed_sword")[0]
        gripped = keyed_model(manny, grip_result.frames)
        i = walk.index
        n_g = grip_result.frames
        hold = [gripped[i["hand_l"], f] @ np.linalg.inv(gripped[i["hand_r"], f]) for f in range(n_g + 1)]
        hold0 = [grip_target[i["hand_l"], f] @ np.linalg.inv(grip_target[i["hand_r"], f]) for f in range(n_g + 1)]
        weapon = [gripped[i["weapon_r"], f] @ np.linalg.inv(gripped[i["hand_r"], f]) for f in range(n_g + 1)] \
            if "weapon_r" in i else [np.eye(4)]
        weapon0 = [grip_target[i["weapon_r"], f] @ np.linalg.inv(grip_target[i["hand_r"], f]) for f in range(n_g + 1)] \
            if "weapon_r" in i else [np.eye(4)]
        trail = float(np.linalg.norm(gripped[i["hand_r"], :, 3, :3] - grip_target[i["hand_r"], :, 3, :3], axis=1).max())
        held_err = float(np.abs(np.array(hold) - np.array(hold0)).max())
        weapon_err = float(np.abs(np.array(weapon) - np.array(weapon0)).max())
        gate(grip_result.info["arms"]["grip"] and held_err < 1e-3 and weapon_err < 1e-3 and trail > 1.0
             and segment_lengths(gripped) < 1e-3,
             "the two-handed sword under Arm drag 3: both hands keep the grip (%.6f) and the sword in it (%.6f), the "
             "held sword trails up to %.1f cm, the arms reach it whole (%.6f)" % (held_err, weapon_err, trail,
                                                                                   segment_lengths(gripped)))

    # the animator's correction keyed on an animation layer stays on top of every re-key
    bones = bones_of(manny)
    fix_foot = bones[leaf_of(bones, "foot_r")]["path"]
    sw.apply(manny, name)
    cmds.select(fix_foot)
    fix_layer = cmds.animLayer("FootFix", addSelectedObjects=True)
    fix_frame = start + 11

    def shown_at(frame):
        """A layered channel's value as the scene shows it: getAttr(time=) reads the base under a layer's blend
        (measured: 11 where the scene shows 31) - a real time change."""
        cmds.currentTime(frame + 1)
        cmds.currentTime(frame)
        return cmds.getAttr(fix_foot + ".rotateX")
    shown = shown_at(fix_frame)
    cmds.setKeyframe(fix_foot, attribute="rotateX", time=fix_frame, value=shown + 20.0, animLayer=fix_layer)
    try:
        sw.apply(manny, name, {"stride": 1.2})
        rekeyed = True
    except Exception as error:
        rekeyed = error
    base_curve = (cmds.animLayer("BaseAnimation", query=True, findCurveForPlug=fix_foot + ".rotateX") or [None])[0]
    base_at = cmds.keyframe(base_curve, query=True, eval=True, time=(fix_frame, fix_frame), valueChange=True)[0]
    after = shown_at(fix_frame)
    layer_curve = (cmds.animLayer(fix_layer, query=True, findCurveForPlug=fix_foot + ".rotateX") or [None])[0]
    gate(rekeyed is True and abs(after - base_at - 20.0) < 1e-3 and abs(base_at - shown) > 0.01 and layer_curve,
         "an animation layer's correction (+20 deg on foot_r at frame %d) stays on top of the re-key (stride 1.2: "
         "%s): the base re-keyed %.3f -> %.3f, shown %.3f" % (fix_frame, rekeyed, shown, base_at, after))
    cmds.delete(fix_layer)
    try:
        sw.skeleton_root_of(cmds.createNode("transform", name="empty"))
        gate(False, "an empty transform was taken for a skeleton")
    except sw.REFUSALS as refusal:
        gate("holds no skeleton" in str(refusal), "refused: %s" % refusal)
finally:
    shutil.rmtree(TEMP, ignore_errors=True)

print("\n%d gates, %d failed%s" % (COUNT[0], len(FAILED), (": " + str(FAILED)) if FAILED else ""))
