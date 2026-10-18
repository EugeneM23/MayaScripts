"""A filmstrip of a hub popup bursting out of a point and folding back into one (2026-10-17,
maya_hubburst), drawn offscreen through the popup's own effect on the test suite's seams.
Saves popup_burst.png beside this file.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_popup_burst.py
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
_font = QtGui.QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\segoeui.ttf")
if _font >= 0:      # offscreen Qt has no font of its own and draws boxes
    app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(_font)[0], 9))

from tests import test_hubpop as t  # noqa: E402

hubpop = t.hubpop
OUT = os.path.join(HERE, "popup_burst.png")
OPEN_MS = (0, 30, 60, 100, 150, 200, 260, 330, 520)
CLOSE_FRACTION = (0.0, 0.25, 0.5, 0.7, 0.85, 1.0)


class Strip(t.Seams):
    def runTest(self):
        popup = hubpop.open_popup("alpha")
        for label in ("Characters", "Rig  |  Skeleton", "+ Import", "Delete",
                      "Camera Setup", "Import Animation", "Export FBX..."):
            button = QtWidgets.QPushButton(label)
            button.setMinimumHeight(26)
            popup.body.addWidget(button)
        popup.root.resize(260, 330)
        app.processEvents()
        point = popup.root.mapToGlobal(QtCore.QPoint(30, 20))
        frames = []

        def shoot(opening, moments, total=None):
            if opening:
                popup.show_open(animate=True, origin=(point.x(), point.y()))
                held, popup.burster.anim = popup.burster.anim, None
                held.stop()
            else:
                popup._burst(False, (point.x(), point.y()), lambda: None)
                held, popup.burster.anim = popup.burster.anim, None
                held.stop()
            effect = popup.burst
            popup.root.grab()               # the first draw makes the plan
            for m in moments:
                ms = m if total is None else m * effect.plan.total
                effect.ms = float(ms)
                frames.append((popup.root.grab().toImage(),
                               ("open " if opening else "close ") + "%d ms" % ms))
            popup._end_burst()

        shoot(True, OPEN_MS)
        shoot(False, CLOSE_FRACTION, total=True)

        w, h = popup.root.width(), popup.root.height()
        cols = 5
        rows = (len(frames) + cols - 1) // cols
        pad, cap = 12, 20
        sheet = QtGui.QImage(cols * (w + pad) + pad, rows * (h + cap + pad) + pad,
                             QtGui.QImage.Format_ARGB32)
        sheet.fill(QtGui.QColor("#5a5e66"))   # lighter than the card, so its shape shows
        p = QtGui.QPainter(sheet)
        p.setPen(QtGui.QColor("#c8c8c8"))
        for i, (image, label) in enumerate(frames):
            x = pad + (i % cols) * (w + pad)
            y = pad + (i // cols) * (h + cap + pad)
            p.drawText(x, y + 14, label)
            p.drawImage(x, y + cap, image)
            p.setPen(QtGui.QColor("#e07a36"))
            o = popup.root.mapFromGlobal(point)
            p.drawEllipse(QtCore.QPoint(x + o.x(), y + cap + o.y()), 3, 3)
            p.setPen(QtGui.QColor("#c8c8c8"))
        p.end()
        sheet.save(OUT)
        print("saved", OUT, len(frames), "frames, broken:", popup.burst.broken,
              popup.burst.error)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=0).run(Strip())
    sys.exit(0 if result.wasSuccessful() else 1)
