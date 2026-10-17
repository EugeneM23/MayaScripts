"""A contact sheet of Maya's icons beside ours (2026-10-17), in mayapy:

    mayapy render_maya_icons.py <out.png> [scale]

Each drawn name (maya_mayaicons_art.NAMES) as three cells: Maya's own, Maya's
recoloured (maya_mayaicons.recolour), ours drawn at Maya's pixel size; each
cell drawn `scale` times larger (default 2), without smoothing, as Maya draws
it at that display scale. Maya's pictures are read from this machine's Maya and
only drawn into the sheet.
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets                 # noqa: E402

import maya_mayaicons as icons                               # noqa: E402
import maya_mayaicons_art as art                             # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
out = sys.argv[1]
scale = int(sys.argv[2]) if len(sys.argv) > 2 else 2
QtGui.QFontDatabase.addApplicationFont(r"C:/Windows/Fonts/segoeui.ttf")
tmp = tempfile.mkdtemp()
names = list(art.NAMES)
cols, cw, ch = 6, 210, 34 * scale + 22
rows = (len(names) + cols - 1) // cols
sheet = QtGui.QImage(cols * cw, rows * ch + 10, QtGui.QImage.Format_RGB32)
sheet.fill(QtGui.QColor("#17181a"))
p = QtGui.QPainter(sheet)
p.setFont(QtGui.QFont("Segoe UI", 7))
for i, name in enumerate(names):
    x, y = (i % cols) * cw + 6, (i // cols) * ch + 6
    path = os.path.join(tmp, name + ".png")
    try:
        cmds.resourceManager(saveAs=(name + ".png", path))
        maya_img = QtGui.QImage(path)
    except Exception:                                        # noqa: BLE001
        maya_img = QtGui.QImage()
    size = maya_img.width() if not maya_img.isNull() else 20
    cells = [("#444444", maya_img)]
    if not maya_img.isNull():
        cells.append(("#1f2023", icons.qimage_recoloured(maya_img, name)))
    else:
        cells.append(("#1f2023", QtGui.QImage()))
    cells.append(("#1f2023", icons.render(name, size, size)))
    for k, (bg, img) in enumerate(cells):
        cx = x + k * (size * scale + 10)
        p.fillRect(cx - 3, y - 3, size * scale + 6, size * scale + 6, QtGui.QColor(bg))
        if not img.isNull():
            p.drawImage(QtCore.QRect(cx, y, size * scale, size * scale), img)
    p.setPen(QtGui.QColor("#9a9ca3"))
    p.drawText(QtCore.QRect(x - 4, y + size * scale + 4, cw - 4, 14),
               QtCore.Qt.AlignLeft, name[:30])
p.end()
sheet.save(out)
print(out, sheet.size(), len(names))
