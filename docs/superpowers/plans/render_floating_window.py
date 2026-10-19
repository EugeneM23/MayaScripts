"""Render the floating window in look B at chosen instants of its burst, offscreen at 150 %
(2026-10-18, spec 2026-10-18-floating-windows-design.md), and time a burst's paint.

    $env:QT_QPA_PLATFORM='offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/render_floating_window.py
"""

import os
import statistics
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import maya_hubburst as hubburst              # noqa: E402
import maya_hubwindow as hubwindow            # noqa: E402

SCALE = 1.5
MOMENTS = (0, 40, 90, 150, 230, 320, 520, 900)
TITLE = int(34 * SCALE)


def window():
    frame = hubwindow.frame_class()(SCALE)
    frame.resize(int(300 * SCALE), int(260 * SCALE))
    column = QtWidgets.QVBoxLayout(frame)
    column.setContentsMargins(int(5 * SCALE), TITLE, int(5 * SCALE), int(5 * SCALE))
    frame.content = QtWidgets.QFrame()
    inner = QtWidgets.QVBoxLayout(frame.content)
    for text in ("Knot", "Offset", "Orient", "Local x2", "World x2", "Aim", "Snapshot"):
        button = QtWidgets.QPushButton(text)
        button.setFixedHeight(int(24 * SCALE))
        inner.addWidget(button)
    column.addWidget(frame.content)
    hubwindow.dress(frame, SCALE)
    frame.show()
    QtWidgets.QApplication.processEvents()
    return frame


def parts(frame):
    def read():
        rects = [(0, 0, frame.width(), TITLE)]
        for b in frame.findChildren(QtWidgets.QPushButton):
            p = b.mapTo(frame, QtCore.QPoint())
            rects.append((p.x(), p.y(), b.width(), b.height()))
        return rects
    return read


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    frame = window()
    burster = hubwindow.Burster(frame, parts(frame), lambda: (42, 44, 48), SCALE)
    origin = frame.mapToGlobal(QtCore.QPoint(int(20 * SCALE), int(18 * SCALE)))
    cell_w, cell_h = frame.width() + 20, frame.height() + 40
    sheet = QtGui.QImage(cell_w * 4, cell_h * 2, QtGui.QImage.Format_ARGB32)
    sheet.fill(QtGui.QColor("#4d5562"))
    painter = QtGui.QPainter(sheet)
    painter.setPen(QtGui.QColor("#e4e4e6"))
    for i, ms in enumerate(MOMENTS):
        burster.run(True, (origin.x(), origin.y()), lambda: None)
        if burster.anim is not None:
            burster.anim.stop()
        burster.effect.ms = float(ms)
        frame.grab()                    # the first paint makes the plan
        burster.effect.ms = float(ms)
        image = frame.grab().toImage()
        x, y = (i % 4) * cell_w + 10, (i // 4) * cell_h + 30
        painter.drawText(x, y - 10, "open %d ms" % ms)
        painter.drawImage(x, y, image)
        burster.stop()
    painter.end()
    out = os.path.join(HERE, "floating_window.png")
    sheet.save(out)

    # the budget: a burst's paint per tick at 90 ms (racing edges, rows popping)
    burster.run(True, (origin.x(), origin.y()), lambda: None)
    if burster.anim is not None:
        burster.anim.stop()
    burster.effect.ms = 90.0
    frame.grab()
    times = []
    for _ in range(30):
        burster.effect.ms = 90.0
        t0 = time.perf_counter()
        frame.grab()
        times.append((time.perf_counter() - t0) * 1000.0)
    burster.stop()
    print("wrote", out, "plan total", hubburst.plan_open((0, 0), (300, 260), [], 1.0).total)
    print("burst paint at 90 ms, %dx%d px: median %.2f ms, max %.2f ms (30 grabs)"
          % (frame.width(), frame.height(), statistics.median(times), max(times)))


if __name__ == "__main__":
    main()
