"""render_poseclip - side and front sheets of the clip and its posed copies (offscreen Qt under mayapy).

    & '...\\mayapy.exe' render_poseclip.py <verify's npz (POSECLIP_OUT)> <out.png>

Rows: the clip, the goblin, the two-handed sword; columns: frames across the stop. Each cell is centred on the
clip's pelvis at that frame, so the three stand where they stand against one another; the floor line at 0."""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

FRAMES = tuple(int(f) for f in os.environ.get("POSECLIP_FRAMES", "0,10,18,22,26,32,42,56,120").split(","))
LABELS = os.environ.get("POSECLIP_LABELS", "the clip,goblin,two-handed sword").split(",")
ROWS = (("clip", LABELS[0], (150, 150, 160)), ("goblin", LABELS[1], (224, 122, 54)),
        ("sword", LABELS[2], (90, 160, 230)))
HELPERS = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass", "attach", "poi", "props_")
CELL, PAD, SCALE = 190, 26, 0.95


def main(npz, out):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    font_path = r"C:\Windows\Fonts\segoeui.ttf"
    family = "Segoe UI"
    if os.path.exists(font_path):
        fid = QtGui.QFontDatabase.addApplicationFont(font_path)
        families = QtGui.QFontDatabase.applicationFontFamilies(fid)
        family = families[0] if families else family
    d = np.load(npz)
    names, parents = [str(n) for n in d["names"]], [int(p) for p in d["parents"]]
    pelvis = names.index("pelvis")
    bones = [(j, parents[j]) for j in range(len(names)) if parents[j] >= 0 and names[parents[j]] != "root"
             and not names[j].startswith(HELPERS) and not names[parents[j]].startswith(HELPERS)]
    views = (("side", 2, 1), ("front", 0, 1))
    width = PAD * 2 + 110 + CELL * len(FRAMES)
    height = PAD * 2 + len(views) * (len(ROWS) * CELL + 40)
    image = QtGui.QImage(width, height, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor(30, 31, 35))
    p = QtGui.QPainter(image)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setFont(QtGui.QFont(family, 10))
    floor = float(d["floor"]) - 3.0
    y0 = PAD
    for view, hx, vy in views:
        p.setPen(QtGui.QColor(200, 200, 205))
        p.drawText(PAD, y0 + 14, "%s view" % view)
        for c, f in enumerate(FRAMES):
            p.drawText(PAD + 110 + c * CELL + CELL // 2 - 20, y0 + 14, "frame %d" % f)
        y0 += 24
        for r, (key, label, colour) in enumerate(ROWS):
            w = d[key]
            top = y0 + r * CELL
            p.setPen(QtGui.QColor(*colour))
            p.drawText(PAD, top + CELL // 2, label)
            for c, f in enumerate(FRAMES):
                if f >= w.shape[1]:
                    continue
                left = PAD + 110 + c * CELL
                centre = d["clip"][pelvis, f, 3, hx]
                ground = top + CELL - 12

                def at(v):
                    return QtCore.QPointF(left + CELL / 2 + (v[hx] - centre) * SCALE,
                                          ground - (v[vy] - floor) * SCALE)
                p.setPen(QtGui.QPen(QtGui.QColor(70, 72, 80), 1))
                p.drawLine(QtCore.QPointF(left + 8, ground), QtCore.QPointF(left + CELL - 8, ground))
                if key != "clip":            # the clip, faint, behind each posed figure
                    p.setPen(QtGui.QPen(QtGui.QColor(90, 92, 100), 1.2))
                    for j, q in bones:
                        p.drawLine(at(d["clip"][q, f, 3, :3]), at(d["clip"][j, f, 3, :3]))
                p.setPen(QtGui.QPen(QtGui.QColor(*colour), 2.0))
                for j, q in bones:
                    p.drawLine(at(w[q, f, 3, :3]), at(w[j, f, 3, :3]))
        y0 += len(ROWS) * CELL + 16
    p.end()
    image.save(out)
    print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
