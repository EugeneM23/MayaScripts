"""Render the floating window and the edge rail's card in look B at chosen instants of their
burst and of their fold, offscreen at 150 % (2026-10-18, spec 2026-10-18-floating-windows-design.md
section 8), and time a burst's paint.

The window is the real look-B frame with the real title row (icon, name, roll and close pills,
maya_hubwindow) over a card of hub-styled buttons; the rail card is a real windowed
maya_hubqt.Skin card (look B, its close and float pills), bursting out of its rail icon and
folding into its close pill. Both are driven by the real maya_hubwindow.Burster and the plan it
makes (maya_hubburst).

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

import maya_hubqt as hubqt                    # noqa: E402
import maya_hubstyle as hubstyle              # noqa: E402
import maya_hubwindow as hubwindow            # noqa: E402

SCALE = 1.5
OPEN_MS = (20, 40, 90, 150, 230, 320, 520, 900)
FOLD_MS = (60, 160)
LABELS = ("Knot", "Offset", "Orient", "Local x2", "World x2", "Aim", "Snapshot")
COLUMNS = len(OPEN_MS) + len(FOLD_MS)


def xy(point):
    return (point.x(), point.y())


def px(n):
    return hubstyle.px(n, SCALE)


def use_font(app):
    """Offscreen Qt has no font of its own: take Windows' Segoe UI so captions and titles
    read (the way render_camshake_curves.py does); without the file the default stays."""
    path = r"C:\Windows\Fonts\segoeui.ttf"
    if not os.path.isfile(path):
        return
    loaded = QtGui.QFontDatabase.addApplicationFont(path)
    if loaded >= 0:
        families = QtGui.QFontDatabase.applicationFontFamilies(loaded)
        if families:
            app.setFont(QtGui.QFont(families[0]))


def buttons(parent_layout, parent):
    for i, text in enumerate(LABELS):
        button = QtWidgets.QPushButton(text, parent)
        button.setProperty("skRole", "primary" if i == 0 else "tool")
        button.setFixedHeight(px(24))
        parent_layout.addWidget(button)


def window():
    """A section's window as maya_hubpop builds it: the frame, the title row, the card."""
    root = QtWidgets.QWidget()
    root.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
    outer = QtWidgets.QVBoxLayout(root)
    outer.setContentsMargins(0, 0, 0, 0)
    frame = hubqt._named(hubwindow.frame_class()(SCALE), "renderWindowFrame")
    outer.addWidget(frame)
    column = QtWidgets.QVBoxLayout(frame)
    column.setContentsMargins(px(5), 0, px(5), px(5))
    column.setSpacing(0)
    title = QtWidgets.QWidget(frame)
    title.setFixedHeight(px(hubwindow.TITLE_H))
    row = QtWidgets.QHBoxLayout(title)
    row.setContentsMargins(px(5), 0, 0, 0)
    row.setSpacing(px(6))
    pill = hubwindow.pill_class()
    roll, close = pill("chevron-down", SCALE), pill("x", SCALE)
    row.addWidget(hubwindow.title_icon("tool", hubstyle.group("animation").colour, SCALE,
                                       "renderWindowIcon"))
    row.addWidget(hubwindow.title_label("Tools", SCALE, "renderWindowName"))
    row.addStretch(1)
    row.addWidget(roll)
    row.addWidget(close)
    column.addWidget(title)
    card = QtWidgets.QFrame()
    card.setObjectName("renderWindowCard")
    frame.content = card
    inner = QtWidgets.QVBoxLayout(card)
    inner.setContentsMargins(px(8), px(8), px(8), px(8))
    buttons(inner, card)
    column.addWidget(card, 1)
    root.setStyleSheet(hubstyle.stylesheet(SCALE)
                       + "\n#renderWindowFrame { border: none; background: transparent; }")
    hubwindow.dress(frame, SCALE)
    root.resize(px(300), px(280))
    root.show()
    QtWidgets.QApplication.processEvents()
    return root, frame, title, card, close


def rail_card():
    """The edge rail's card: a real windowed Skin, one card shown, the rail beside it."""
    host = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(host)
    skin = hubqt.Skin(layout, scale=SCALE, layout="rail", windowed=True)
    skin.add_jump("tools", "Tools", "tool", hubstyle.group("animation").colour,
                  group="animation")
    card = skin.add_card("tools", "Tools", "tool", hubstyle.group("animation").colour,
                         "#4a3322", collapsible=False)
    buttons(card.body_layout, card.body)
    skin.finish(hubstyle.stylesheet(SCALE))
    skin.show_card("tools")
    host.resize(px(340), px(330))
    host.show()
    QtWidgets.QApplication.processEvents()
    return host, skin, card


def film(painter, frame, burster, open_point, fold_point, top, cell_w, cell_h, caption):
    """One row of cells: the burst at OPEN_MS, then the fold at FOLD_MS."""
    plan_total = None
    for i, (opening, ms) in enumerate([(True, m) for m in OPEN_MS]
                                      + [(False, m) for m in FOLD_MS]):
        point = open_point if opening else fold_point
        burster.run(opening, point, lambda: None)
        if burster.anim is not None:
            burster.anim.stop()
        burster.effect.ms = float(ms)
        frame.grab()                    # the first paint makes the plan
        burster.effect.ms = float(ms)
        image = frame.grab().toImage()
        if opening:
            plan_total = burster.effect.plan.total
        x, y = i * cell_w + 10, top + 44
        painter.drawText(x, y - 8, "%s %d ms" % ("open" if opening else "fold", ms))
        painter.drawImage(x, y, image)
        burster.stop()
    painter.drawText(10, top + 14, caption)
    return plan_total


def paint_cost(frame, burster, point):
    """A burst's paint per tick at 90 ms, from the real burster's plan."""
    burster.run(True, point, lambda: None)
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
    total = burster.effect.plan.total
    burster.stop()
    return statistics.median(times), max(times), total


def main():
    # kept for the whole run: widgets and Qt's event machinery need the application alive
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    use_font(app)
    root, frame, title, card, close = window()
    window_burster = hubwindow.Burster(
        frame, lambda: hubqt.burst_parts(frame, title, card, None, SCALE),
        lambda: (42, 44, 48), SCALE)
    w_open = xy(frame.mapToGlobal(QtCore.QPoint(px(20), px(18))))
    w_fold = xy(close.mapToGlobal(close.rect().center()))

    host, skin, rail = rail_card()
    rail_burster = hubwindow.Burster(
        rail.frame, lambda: hubqt.card_parts(skin, rail),
        lambda: (42, 44, 48), SCALE)
    icon = skin.jumps["tools"]
    r_open = xy(icon.mapToGlobal(icon.rect().center()))
    r_fold = xy(rail.close.mapToGlobal(rail.close.rect().center()))

    cell_w = max(frame.width(), rail.frame.width()) + 20
    cell_h = max(frame.height(), rail.frame.height()) + 56
    sheet = QtGui.QImage(cell_w * COLUMNS, cell_h * 2, QtGui.QImage.Format_ARGB32)
    sheet.fill(QtGui.QColor("#4d5562"))
    painter = QtGui.QPainter(sheet)
    painter.setPen(QtGui.QColor("#e4e4e6"))
    total_w = film(painter, frame, window_burster, w_open, w_fold, 0, cell_w, cell_h,
                   "floating window, look B: burst out of a point, fold into the close pill")
    total_r = film(painter, rail.frame, rail_burster, r_open, r_fold, cell_h, cell_w, cell_h,
                   "edge rail card, look B: burst out of its rail icon, fold into its close pill")
    painter.end()
    out = os.path.join(HERE, "floating_window.png")
    sheet.save(out)

    mid_w, max_w, plan_w = paint_cost(frame, window_burster, w_open)
    mid_r, max_r, plan_r = paint_cost(rail.frame, rail_burster, r_open)
    print("wrote", out)
    print("plan total (open, from the burster's plan): window %.0f ms, rail card %.0f ms"
          % (total_w, total_r))
    print("burst paint at 90 ms, window %dx%d px: median %.2f ms, max %.2f ms (30 grabs)"
          % (frame.width(), frame.height(), mid_w, max_w))
    print("burst paint at 90 ms, rail card %dx%d px: median %.2f ms, max %.2f ms (30 grabs)"
          % (rail.frame.width(), rail.frame.height(), mid_r, max_r))
    skin.destroy()


if __name__ == "__main__":
    main()
