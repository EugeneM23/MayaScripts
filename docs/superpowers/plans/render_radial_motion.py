"""A filmstrip of the radial menu's motion (2026-10-16), drawn offscreen the way maya_radial paints it:
the opening, a pill lit under the mouse, the chosen pill's flash, the close back into the centre.
Saves radial_menu_motion.png beside this file.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_radial_motion.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "SkeldarAnim")
sys.path.insert(0, PLUGIN)

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
_font = QtGui.QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\segoeui.ttf")
if _font >= 0:      # offscreen Qt has no font of its own and draws boxes
    app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(_font)[0], 9))

import maya_hubqt as hubqt  # noqa: E402
import maya_radial as radial  # noqa: E402
import maya_radial_rules as rules  # noqa: E402

q = hubqt.qt()
radial.slots = lambda: rules.DEFAULTS
radial.count = lambda: rules.SLOTS
radial.waiting = lambda key: False
radial._scale = lambda: 1.0
radial.animated = lambda: True
radial._run_later = lambda *a: None
CLOCK = [0.0]
radial._now_ms = lambda: CLOCK[0]

W, H = 520, 440
FRAMES = []


def menu_at(cursor):
    menu = radial.Menu(q)
    menu.centre = (W // 2, H // 2)
    menu.origin = (0, 0)
    menu.cursor = lambda: cursor
    menu.window = radial._overlay_class(q)(menu)
    menu.window.resize(W, H)
    radial._state()["menu"] = menu
    return menu


def shot(menu, caption):
    image = QtGui.QImage(W, H, QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor("#3b3e44"))
    menu.paint(menu.window, device=image)
    FRAMES.append((image, caption))


m = menu_at((W // 2, H // 2))
for t in (0, 40, 80, 130, 200, 330):
    CLOCK[0] = m.opened_at + t
    shot(m, "open {0} ms".format(t))
CLOCK[0] = m.opened_at + 400
m.cursor = lambda: (W // 2 + 140, H // 2 + 10)      # toward E: Aim
m.hover = m.pointed()
for dt in (55, 55):
    m.step_lift(dt)
    CLOCK[0] += dt
    shot(m, "hover {0:.0%}".format(m.lift[m.hover]))
m.choose(m.hover)
CLOCK[0] += 30
shot(m, "chosen: flash")
CLOCK[0] = m.fired_at + rules.FLASH_MS
m.tick()
start = CLOCK[0]
for t in (40, 90, 160):
    CLOCK[0] = start + t
    shot(m, "close {0} ms".format(t))

cols = 4
rows = (len(FRAMES) + cols - 1) // cols
sheet = QtGui.QImage(cols * W, rows * (H + 28), QtGui.QImage.Format_ARGB32)
sheet.fill(QtGui.QColor("#202226"))
p = QtGui.QPainter(sheet)
p.setPen(QtGui.QColor("#c9cacf"))
f = app.font()
f.setPixelSize(16)
p.setFont(f)
for i, (image, caption) in enumerate(FRAMES):
    x, y = (i % cols) * W, (i // cols) * (H + 28)
    p.drawImage(x, y + 28, image)
    p.drawText(QtCore.QRectF(x + 10, y, W - 20, 28), QtCore.Qt.AlignVCenter, caption)
p.end()
path = os.path.join(HERE, "radial_menu_motion.png")
sheet.save(path)
print("saved", path, len(FRAMES))
