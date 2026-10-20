"""Draw Space's camera menu offscreen (2026-10-20): open, Side lit, at 150 %.

    mayapy docs/superpowers/plans/render_camera_radial.py [out.png]
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))

from PySide6 import QtGui, QtWidgets  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
font_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
for name in ("segoeui.ttf", "segoeuib.ttf"):
    if os.path.exists(os.path.join(font_dir, name)):
        QtGui.QFontDatabase.addApplicationFont(os.path.join(font_dir, name))
app.setFont(QtGui.QFont("Segoe UI", 9))

import maya_hubqt  # noqa: E402
import maya_radial  # noqa: E402
import maya_radial_rules as rules  # noqa: E402

PERSP = [0.707, 0, -0.707, 0, -0.33, 0.88, -0.33, 0, 0.62, 0.47, 0.62, 0, 0, 0, 0, 1]
MATS = {"|top": [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1],
        "|front": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "|side": [0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
        "|persp": PERSP, "|rig:SceneSetup_camera": PERSP, "|shotCam": PERSP}

q = maya_hubqt.qt()
maya_radial._scale = lambda: 1.5
maya_radial.animated = lambda: True
clock = [0.0]
maya_radial._now_ms = lambda: clock[0]
items = rules.camera_slots({"persp": "|persp", "top": "|top", "front": "|front", "side": "|side"},
                           ["|rig:SceneSetup_camera", "|shotCam"])
texts = []
for item in items:
    kind, path = rules.parse(item)
    texts.append({"|persp": "Persp", "|top": "Top", "|front": "Front", "|side": "Side"}.get(path, path.rsplit(":", 1)[-1].lstrip("|")) if kind else "")
axes = [rules.axes_seen(MATS[rules.parse(i)[1]]) if i else {} for i in items]
spec = {"items": items, "texts": texts, "axes": axes, "marked": {6}, "centre": "camera"}

W = H = 640
strip = QtGui.QImage(W * 4, H, QtGui.QImage.Format_ARGB32)
strip.fill(QtGui.QColor("#30343b"))
painter = QtGui.QPainter(strip)
for col, (t, hover) in enumerate(((60, None), (120, None), (500, None), (700, 2))):
    menu = maya_radial.Menu(q, spec)
    menu.centre = (W / 2, H / 2)
    menu.origin = (0, 0)
    menu.cursor = (lambda h: (lambda: (W / 2 + 150, H / 2) if h is not None else (W / 2, H / 2)))(hover)
    menu.window = maya_radial._overlay_class(q)(menu)
    menu.window.resize(W, H)
    clock[0] = t
    menu.hover = hover
    if hover is not None:
        menu.lift[hover] = 1.0
    image = QtGui.QImage(W, H, QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor(0, 0, 0, 0))
    menu.paint(menu.window, now=t, device=image)
    painter.drawImage(col * W, 0, image)
    menu.window.deleteLater()
painter.end()
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "camera_radial_menu.png")
strip.save(out)
print("wrote", out)
