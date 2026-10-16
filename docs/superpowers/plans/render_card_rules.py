"""The card rules (2026-10-16) drawn offscreen with the skin's own code and stylesheet at 150 %: a
Connections-like card built from Qt stand-ins marked as its builder marks them (captions, row
labels, segments, Apply all, the message line with a tone), and the real Inventory panel over a
fake scene. Saved as card_rules.png beside this file.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_card_rules.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
sys.path.insert(0, REPO)

from PySide6 import QtGui, QtWidgets  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
_font = QtGui.QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\segoeui.ttf")
if _font >= 0:      # offscreen Qt has no font of its own and draws boxes
    app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(_font)[0], 9))

import maya_hubqt as hubqt  # noqa: E402
import maya_hubstyle as style  # noqa: E402
import maya_inventory as inv  # noqa: E402
from tests.test_inventory import FakeScene  # noqa: E402

SCALE = 1.5
W = 540
CONTROLS = {}
hubqt.find = lambda name, layout=False: CONTROLS.get(name)
hubqt.path_of = lambda obj: "path|" + obj.objectName()


def control(cls, name, parent, *args):
    widget = cls(*args)
    widget.setParent(parent)
    widget.setObjectName(name)
    CONTROLS[name] = widget
    return widget


def connections(skin):
    card = skin.add_card("connections", "Connections", "hand-grab", "#f0a26b", "#4a3322",
                         collapsible=False)
    body, marks = card.body, []
    lay = card.body_layout
    s = lambda n: style.px(n, SCALE)                         # noqa: E731

    def caption(name, text):
        lay.addWidget(control(QtWidgets.QLabel, name, body, text))
        marks.append(style.Mark(name, "heading", None, False, None))

    def row(label, choices, lit, tool=True):
        box = QtWidgets.QWidget(body)
        h = QtWidgets.QHBoxLayout(box)
        h.setContentsMargins(0, s(2), 0, s(2))
        name = "lab_" + label
        h.addWidget(control(QtWidgets.QLabel, name, box, label))
        marks.append(style.Mark(name, "label", None, False, None))
        track = control(QtWidgets.QWidget, "seg_" + label, box)
        track.setAttribute(hubqt.qt().QtCore.Qt.WA_StyledBackground, True)
        t = QtWidgets.QHBoxLayout(track)
        t.setContentsMargins(s(2), s(2), s(2), s(2))
        for choice in choices:
            b = control(QtWidgets.QPushButton, "b_%s_%s" % (label, choice), track, choice)
            b.setCheckable(True)
            b.setChecked(choice == lit)
            b.setMinimumHeight(s(20))
            t.addWidget(b)
            marks.append(style.Mark(b.objectName(), "segment", None, False, None))
        track.setProperty("skRole", "segments")
        h.addWidget(track, 1)
        if tool:
            apply = control(QtWidgets.QPushButton, "apply_" + label, box)
            apply.setFixedSize(s(28), s(24))
            marks.append(style.Mark(apply.objectName(), "tool", "check", False, None))
            h.addWidget(apply)
        lay.addWidget(box)

    caption("capLimbs", "FK / IK")
    row("Arm R", ("FK", "IK"), "IK", tool=False)
    row("Leg R", ("FK", "IK"), "FK", tool=False)
    caption("capWeapon", "Weapon in hands")
    row("Hand R", ("Free", "Weapon"), "Free")
    row("Hand L", ("Free", "Weapon"), "Free")
    row("Weapon", ("World", "Hand R", "Hand L"), "Hand R")
    go = control(QtWidgets.QPushButton, "applyAll", body, "Apply all")
    go.setMinimumHeight(s(30))
    lay.addSpacing(s(4))
    lay.addWidget(go)
    marks.append(style.Mark("applyAll", "primary", "check", False, None))
    caption("capAny", "Any object")
    box = QtWidgets.QWidget(body)
    h = QtWidgets.QHBoxLayout(box)
    h.setContentsMargins(0, s(2), 0, 0)
    for text, icon in (("BakeAcross", "link"), ("Release", "unlink")):
        b = control(QtWidgets.QPushButton, "b_" + text, box, text)
        b.setMinimumHeight(s(26))
        h.addWidget(b)
        marks.append(style.Mark(b.objectName(), "secondary", icon, False, None))
    lay.addWidget(box)
    hubqt.apply_marks(marks, card, SCALE)
    return card


class Scene(FakeScene):
    def scale(self):
        return SCALE


def build():
    host = QtWidgets.QWidget()
    host.resize(W, 980)
    QtWidgets.QVBoxLayout(host).setContentsMargins(0, 0, 0, 0)
    skin = hubqt.Skin(host, scale=SCALE, callbacks={}, layout="accordion")
    connections(skin)
    weapons = skin.add_card("weapons", "Inventory", "backpack", "#f0a26b", "#4a3322")
    panel = inv.make_panel(Scene(), weapons.body)
    weapons.body_layout.addWidget(panel)
    panel.setFixedHeight(panel.heightForWidth(W - 40) if panel.hasHeightForWidth() else 420)
    skin.finish(style.stylesheet(SCALE))
    skin.set_active("connections")
    skin.say("Imported LongSword_Attack_Heavy_3P onto Manny_Rig, 61 fr",
             source="connections")
    host.show()
    for _ in range(6):
        app.processEvents()
    return host.grab()


pix = build()
path = os.path.join(HERE, "card_rules.png")
pix.save(path)
print("saved", path, pix.size())
