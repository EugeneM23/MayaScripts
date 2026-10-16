"""The hub in the rail layout (2026-10-16, layout C), drawn offscreen with the skin's own code and
stylesheet at 150 %: the real rail (every card section's icon, by group), stub card bodies. Two
pictures side by side, Tools shown and Inventory shown, into hub_rail.png beside this file.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_hub_rail.py
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

import maya_hub as hub  # noqa: E402
import maya_hubqt as hubqt  # noqa: E402
import maya_hubstyle as hubstyle  # noqa: E402

SCALE = 1.5
W, H = 540, 900          # the animator's 360 logical px dock


def stub(card, key):
    """A body standing in for a builder's: a few rows of real Qt widgets in the skin's roles."""
    layout = card.body_layout
    s = lambda n: hubstyle.px(n, SCALE)                     # noqa: E731
    rows = {
        "tools": ["Knot", "Offset", "Orient", "Local x2", "World x2", "Aim", "Snapshot"],
        "weapons": ["Right hand  Long Sword", "Left hand  -", "Long Sword", "Spear 01"],
    }.get(key, ["A row", "Another row"])
    for text in rows:
        button = QtWidgets.QPushButton(text)
        button.setProperty("skRole", "secondary")
        button.setMinimumHeight(s(24))
        layout.addWidget(button)
        layout.addSpacing(s(3))
    primary = QtWidgets.QPushButton({"tools": "Bake", "weapons": "Equip"}.get(key, "Apply"))
    primary.setProperty("skRole", "primary")
    primary.setMinimumHeight(s(26))
    layout.addWidget(primary)


def build(shown):
    host = QtWidgets.QWidget()
    host.resize(W, H)
    QtWidgets.QVBoxLayout(host).setContentsMargins(0, 0, 0, 0)
    skin = hubqt.Skin(host, scale=SCALE, callbacks={}, layout="rail")
    for sec in hub.card_sections():
        grp = hubstyle.group(sec.group)
        skin.add_jump(sec.key, sec.label, sec.icon, grp.colour, group=sec.group)
        card = skin.add_card(sec.key, sec.label, sec.icon, grp.colour, grp.chip,
                             collapsible=False)
        stub(card, sec.key)
    skin.finish(hubstyle.stylesheet(SCALE))
    skin.show_card(shown)
    skin.set_active(shown)
    host.show()
    for _ in range(5):
        app.processEvents()
    content = skin.content.minimumSizeHint().width()
    viewport = skin.scroll.viewport().width()
    print(shown, "content min", content, "viewport", viewport, "rail", skin.rail.width())
    return host.grab()


pictures = [build("tools"), build("weapons")]
sheet = QtGui.QImage(W * 2 + 20, H, QtGui.QImage.Format_ARGB32)
sheet.fill(QtGui.QColor("#141517"))
p = QtGui.QPainter(sheet)
for i, pix in enumerate(pictures):
    p.drawPixmap(i * (W + 20), 0, pix)
p.end()
path = os.path.join(HERE, "hub_rail.png")
sheet.save(path)
print("saved", path)
