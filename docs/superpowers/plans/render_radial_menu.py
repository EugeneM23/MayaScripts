"""Draws the radial menu and its Finish popup offscreen (mayapy, QT_QPA_PLATFORM=offscreen), the way
maya_radial paints them, into radial_menu.png beside this file. No Maya UI: the scene parts are
stubbed (the slots are the defaults, Aim reads Finish).

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_radial_menu.py
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
radial.waiting = lambda key: key == "tools.aim"
radial._scale = lambda: 1.5


class FakeCursor(object):
    @staticmethod
    def pos():
        return QtCore.QPoint(400 + 150, 300 - 60)          # toward NE


W, H = 800, 600
out = QtGui.QImage(W * 2, H, QtGui.QImage.Format_ARGB32)
out.fill(QtGui.QColor("#3b3e44"))
painter = QtGui.QPainter(out)

for i, mode in enumerate(("hold", "click")):
    menu = radial.Menu(q)
    menu.mode = mode
    menu.centre = (400, 300)
    menu.origin = (0, 0)
    menu.cursor = (lambda: (550, 240)) if mode == "hold" else (lambda: (400, 300))
    menu.hover = menu.pointed()
    widget = radial._overlay_class(q)(menu)
    widget.resize(W, H)
    image = QtGui.QImage(W, H, QtGui.QImage.Format_ARGB32)
    image.fill(QtCore.Qt.transparent)
    menu.window = widget
    menu.alive = lambda: True
    widget.render(image)
    painter.drawImage(i * W, 0, image)
    print(mode, "hover", menu.hover, "texts", menu.texts)

finish = radial.Finish(q, "tools.aim")
radial._main_window = lambda q: None
finish.show((W + 470, 430), "Aim: drag the target and the up into place, then Finish")
finish.window.adjustSize()
pix = finish.window.grab()
painter.drawPixmap(W + 470, 420, pix)
painter.end()
path = os.path.join(HERE, "radial_menu.png")
out.save(path)
print("saved", path, finish.window.size())
