"""Draws the hub's Tools card as the skin shows it - offscreen, no Maya UI - into tools_card.png.

The card's builder runs on the recording `cmds` of the unit tests; its calls are replayed into
plain Qt widgets standing for Maya's controls (a button, a label, a row, a column, a check box, a
field), the skin's marks and states are applied and the hub's own stylesheet set - so the picture
is the skin's code drawing the card's real controls, at the animator's 150 % display in their
360 px dock (the hub's viewport 510 physical px). Two states side by side: as a first open shows
it (Knots open, a pivot waiting so Offset reads Finish) and every subsection open.

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/render_tools_card.py

Spec: docs/superpowers/specs/2026-10-13-tools-card-list-design.md
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
sys.path.insert(0, REPO)

from PySide6 import QtCore, QtGui, QtWidgets          # noqa: E402

import maya_hubqt as hubqt                              # noqa: E402
import maya_hubstyle as hubstyle                        # noqa: E402
from maya_tools import panel                            # noqa: E402
from tests import test_tools_panel as fakes             # noqa: E402

SCALE = 1.5
WIDTH = 510            # the hub's viewport in the animator's dock, physical px
CREATIONS = ("text", "button", "rowLayout", "checkBox", "floatField", "iconTextRadioButton",
             "columnLayout")


def _built(open_all):
    """The card's builder on the recording cmds: its calls, its marks, the states it lit."""
    fake = fakes._Cmds()
    stub = fakes._Knots()
    stub.count, stub.pivot_count = 3, 1
    lit = []
    saved = (panel.cmds, panel.knots, panel._light)
    panel.cmds, panel.knots = fake, stub
    panel._light = lambda name, state: lit.append((name, state))
    fake.ls = lambda *a, **k: []
    if open_all:
        for key, _, _ in panel.SECTIONS:
            fake.optionvars[panel.OPEN_VAR % key] = 1
    hubstyle.take_marks()
    hubstyle.set_skinning(True)
    try:
        panel.build_panel()
    finally:
        hubstyle.set_skinning(False)
        panel.cmds, panel.knots, panel._light = saved
    return fake, hubstyle.take_marks(), lit


def _replay(fake, parent_layout, controls):
    """The recorded creations as Qt widgets standing for Maya's, nested as cmds nested them."""
    s = lambda n: hubstyle.px(n, SCALE)                 # noqa: E731
    names = iter(fake.children)
    stack = [parent_layout]
    for kind, args, kwargs in fake.calls:
        if kind == "setParent" and args == ("..",):
            stack.pop()
            continue
        if kind not in CREATIONS or any(kwargs.get(k) for k in ("query", "edit", "exists", "q", "e")):
            continue
        named = kind != "columnLayout" or (args and args[0] in fake.layouts)
        name = next(names) if named else "toolsColumn"
        if kind in ("columnLayout", "rowLayout"):
            widget = QtWidgets.QWidget()
            box = (QtWidgets.QVBoxLayout(widget) if kind == "columnLayout"
                   else QtWidgets.QHBoxLayout(widget))
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(s(kwargs.get("rowSpacing", 3)) if kind == "columnLayout" else s(4))
            if kwargs.get("manage") is False:
                widget.setVisible(False)
        elif kind == "text":
            widget = QtWidgets.QLabel(kwargs.get("label", ""))
            if kwargs.get("wordWrap"):
                widget.setWordWrap(True)
        elif kind == "button":
            widget = QtWidgets.QPushButton(fake.labels.get(name, kwargs.get("label", "")))
            widget.setMinimumHeight(s(kwargs.get("height", 24)))
        elif kind == "checkBox":
            widget = QtWidgets.QCheckBox(kwargs.get("label", ""))
            widget.setChecked(bool(kwargs.get("value")))
        elif kind == "floatField":
            widget = QtWidgets.QLineEdit("%.2f" % kwargs.get("value", 0.0))
            widget.setFixedHeight(s(kwargs.get("height", 20)))
        else:
            widget = QtWidgets.QPushButton(kwargs.get("label", ""))
            widget.setCheckable(True)
            widget.setChecked(bool(kwargs.get("select")))
            widget.setFixedHeight(s(kwargs.get("height", 22)))
        widget.setObjectName(name)
        if kwargs.get("annotation"):
            widget.setToolTip(kwargs["annotation"])
        controls[name] = widget
        stack[-1].addWidget(widget)
        if kind in ("columnLayout", "rowLayout"):
            stack.append(widget.layout())


def render(open_all):
    controls = {}
    saved = (hubqt.find, hubqt.path_of)
    hubqt.find = lambda name, layout=False: controls.get(name)
    hubqt.path_of = lambda obj: obj.objectName()
    host = QtWidgets.QWidget()
    host_layout = QtWidgets.QVBoxLayout(host)
    host_layout.setContentsMargins(0, 0, 0, 0)
    try:
        skin = hubqt.Skin(host_layout, scale=SCALE, callbacks={})
        group = hubstyle.group("animation")
        card = skin.add_card("tools", "Tools", "tool", group.colour, group.chip)
        fake, marks, lit = _built(open_all)
        _replay(fake, card.body_layout, controls)
        for name, state in lit:
            hubqt.set_state(name, state)
        hubqt.apply_marks(marks, card, SCALE)
        skin.finish(hubstyle.stylesheet(SCALE))
        host.resize(WIDTH, 1600)
        host.show()
        for _ in range(4):
            QtWidgets.QApplication.processEvents()
        height = card.frame.geometry().bottom() + hubstyle.px(10, SCALE)
        return card.frame.grab(), height
    finally:
        hubqt.find, hubqt.path_of = saved


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    font_id = QtGui.QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\segoeui.ttf")
    families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
    font = QtGui.QFont(families[0] if families else "Segoe UI")
    font.setPixelSize(16)                 # Maya's UI font at 150 %
    app.setFont(font)
    pictures = [render(False)[0], render(True)[0]]
    gap = 24
    width = sum(p.width() for p in pictures) + gap * (len(pictures) + 1)
    height = max(p.height() for p in pictures) + 2 * gap
    sheet = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)
    sheet.fill(QtGui.QColor(hubstyle.TOKENS["panel"]))
    painter = QtGui.QPainter(sheet)
    x = gap
    for picture in pictures:
        painter.drawPixmap(x, gap, picture)
        x += picture.width() + gap
    painter.end()
    out = os.path.join(HERE, "tools_card.png")
    sheet.save(out)
    print("saved %s (%dx%d)" % (out, width, height))


if __name__ == "__main__":
    main()
