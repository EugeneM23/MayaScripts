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


def draw_sheet(path, panels, frames):
    """Side views (forward right, up up) of each skeleton's walk, every third frame as an onion skin; the
    left side blue, the right orange, the pelvis's path dashed."""
    from PySide6 import QtCore, QtGui
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
    width, height, cols = 760, 330, 2
    rows = (len(panels) + 1) // cols
    image = QtGui.QImage(width * cols, height * rows, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor(250, 249, 246))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    colours = {"l": QtGui.QColor(70, 140, 230), "r": QtGui.QColor(235, 120, 50), "c": QtGui.QColor(60, 60, 60)}
    body = ("pelvis", "spine", "neck", "head", "clavicle", "upperarm", "lowerarm", "hand", "thigh", "calf", "foot",
            "ball")
    for k, (label, root) in enumerate(panels):
        ox, oy = (k % cols) * width, (k // cols) * height
        bones = bones_of(root)
        shown = [(leaf, b) for leaf, b in bones.items()
                 if (b.get("canonical") or "").split("_")[0] in body and b.get("parent") in bones
                 and bones[b["parent"]].get("canonical") != "root"]
        paths = [b["path"] for leaf, b in shown] + [bones[b["parent"]]["path"] for leaf, b in shown]
        w = worlds(paths, list(frames))
        half = len(shown)
        pelvis = bones[leaf_of(bones, "pelvis")]["path"]
        pw = worlds([pelvis], list(frames))[0]
        z0, ground = pw[0, 3, 2], oy + height - 25
        scale = 1.45
        painter.setPen(QtGui.QPen(QtGui.QColor(190, 190, 190), 1))
        painter.drawLine(ox + 10, ground, ox + width - 10, ground)
        painter.setPen(QtGui.QColor(30, 30, 30))
        painter.setFont(QtGui.QFont("Segoe UI", 11))
        painter.drawText(ox + 14, oy + 22, label)
        floor = min(float(w[:, :, 3, 1].min()), 0.0)
        steps = list(range(0, len(frames), 3))
        for n, f in enumerate(steps):
            alpha = 80 + int(175 * n / max(1, len(steps) - 1))
            for i, (leaf, b) in enumerate(shown):
                canonical = b.get("canonical") or ""
                side = canonical[-1] if canonical.endswith(("_l", "_r")) else "c"
                colour = QtGui.QColor(colours[side])
                colour.setAlpha(alpha)
                painter.setPen(QtGui.QPen(colour, 1.6))
                a, c = w[half + i, f, 3], w[i, f, 3]
                painter.drawLine(QtCore.QPointF(ox + 40 + (a[2] - z0) * scale, ground - (a[1] - floor) * scale),
                                 QtCore.QPointF(ox + 40 + (c[2] - z0) * scale, ground - (c[1] - floor) * scale))
        painter.setPen(QtGui.QPen(QtGui.QColor(200, 40, 90), 1.3, QtCore.Qt.DashLine))
        painter.drawPolyline([QtCore.QPointF(ox + 40 + (p[3, 2] - z0) * scale, ground - (p[3, 1] - floor) * scale)
                              for p in pw])
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

    def check(root, label, given=None, expect_scale=None):
        started = time.time()
        result, info, text = sw.apply(root, name, given)
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
    walked, knobs = sw.pick(creep)
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
    if sheet:
        panels = [("Walk_01 (its own skeleton)", source), ("Manny skeleton", manny), ("Creep skeleton", creep),
                  ("UE4 Mannequin", ue4), ("Manny at 0.6", small)]
        if os.path.exists(MIXAMO_FBX):
            panels.insert(4, ("Mixamo Sweep Fall", mixamo))
        draw_sheet(sheet, panels, range(start, start + P + 1))
        print("        picture: " + sheet)
    try:
        sw.skeleton_root_of(cmds.createNode("transform", name="empty"))
        gate(False, "an empty transform was taken for a skeleton")
    except sw.REFUSALS as refusal:
        gate("holds no skeleton" in str(refusal), "refused: %s" % refusal)
finally:
    shutil.rmtree(TEMP, ignore_errors=True)

print("\n%d gates, %d failed%s" % (COUNT[0], len(FAILED), (": " + str(FAILED)) if FAILED else ""))
