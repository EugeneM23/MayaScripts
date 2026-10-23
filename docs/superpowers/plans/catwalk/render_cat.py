"""Filmstrip of our CAT's presets on Manny's template: side and front stick figures, offscreen Qt.

    mayapy render_cat.py [out.png]

Each preset is one row: 8 frames of the cycle side by side (side view, the travel taken off so the
figure stays in its cell), then a front view of the same frames overlaid."""

import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)

import numpy as np                      # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets   # noqa: E402

import catmodel as cm                   # noqa: E402

TEMPLATE = os.path.join(REPO, "SkeldarAnim", "assets", "manny_skeleton_template.json")
CELL, SCALE, SAMPLES = 150, 0.75, 8
LEFT_COLOUR, RIGHT_COLOUR, MID_COLOUR = QtGui.QColor(232, 122, 54), QtGui.QColor(90, 160, 230), QtGui.QColor(220, 220, 225)


def manny():
    joints = json.load(open(TEMPLATE))["joints"]
    return cm.Skeleton.from_template(dict((j["name"], {"parent": j.get("parent"), "world_matrix": j["world_matrix"]})
                                          for j in joints))


def colour(leaf):
    if leaf.endswith("_l"):
        return LEFT_COLOUR
    if leaf.endswith("_r"):
        return RIGHT_COLOUR
    return MID_COLOUR


def draw_figure(p, skel, world, origin, axis_x, axis_y, shift):
    for leaf, parent in skel.parent.items():
        if parent is None or leaf.startswith(("ik_", "weapon", "camera", "interaction", "center")):
            continue
        if parent == skel.root:
            continue
        a, b = world[parent][3, :3] - shift, world[leaf][3, :3] - shift
        pa = QtCore.QPointF(origin[0] + float(np.dot(a, axis_x)) * SCALE, origin[1] - float(np.dot(a, axis_y)) * SCALE)
        pb = QtCore.QPointF(origin[0] + float(np.dot(b, axis_x)) * SCALE, origin[1] - float(np.dot(b, axis_y)) * SCALE)
        pen = QtGui.QPen(colour(leaf), 2.0)
        p.setPen(pen)
        p.drawLine(pa, pb)


def main(out):
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    QtGui.QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\segoeui.ttf")   # offscreen Qt has no font
    skel = manny()
    rows = cm.PRESET_ORDER
    width, height = CELL * (SAMPLES + 2), CELL * 1.6 * len(rows)
    img = QtGui.QImage(int(width), int(height), QtGui.QImage.Format_RGB32)
    img.fill(QtGui.QColor(30, 31, 34))
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    font = QtGui.QFont("Segoe UI")
    font.setPointSize(9)
    p.setFont(font)
    for r, name in enumerate(rows):
        cycle = cm.generate(skel, cm.preset(name, 30), 30)
        top = r * CELL * 1.6
        ground = top + CELL * 1.45
        p.setPen(QtGui.QColor(160, 160, 165))
        p.drawText(QtCore.QPointF(6, top + 14), "%s  T=%d  %.0f cm/s  drop %.1f  flight %d  double %d" % (
            name, cycle.info["frames"], cycle.info["speed"], cycle.info["drop"], cycle.info["flight"],
            cycle.info["double"]))
        p.setPen(QtGui.QColor(70, 72, 78))
        p.drawLine(QtCore.QPointF(0, ground), QtCore.QPointF(width, ground))
        n = cycle.info["frames"]
        for i in range(SAMPLES):
            f = int(round(i * n / float(SAMPLES)))
            world = cycle.frames[f]
            shift = world[skel.pelvis][3, :3] * np.array([1.0, 0.0, 1.0])
            draw_figure(p, skel, world, (CELL * (i + 0.5), ground), skel.fwd, cm.UP, shift)
        for i in range(SAMPLES):
            f = int(round(i * n / float(SAMPLES)))
            world = cycle.frames[f]
            shift = world[skel.pelvis][3, :3] * np.array([1.0, 0.0, 1.0])
            draw_figure(p, skel, world, (CELL * (SAMPLES + 1), ground), -skel.left, cm.UP, shift)
    p.end()
    img.save(out)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "cat_presets.png"))
