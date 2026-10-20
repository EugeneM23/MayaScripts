"""The skill bar's page row with Maya's status-line tools (2026-10-20), offscreen at 150 %:
object mode (one mask partial, a snap on, a hovered button), component mode, hierarchy mode.
mayapy docs/superpowers/plans/render_skill_bar_status.py [out.png]"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
sys.path.insert(0, REPO)

import maya_hubqt  # noqa: E402
import maya_hubstyle  # noqa: E402
from maya_skillbar import look, status  # noqa: E402
from maya_timebar import bar  # noqa: E402
from tests.test_skillbar_grid import SkillLink  # noqa: E402

q = maya_hubqt.qt()
app = q.QtWidgets.QApplication.instance() or q.QtWidgets.QApplication([])
for face in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf", "consolab.ttf"):
    q.QtGui.QFontDatabase.addApplicationFont(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", face))
app.setFont(q.QtGui.QFont("Segoe UI"))

shots = []
for mode in (status.OBJECT, status.COMPONENT, status.HIERARCHY):
    link = SkillLink(look.defaults())
    strip = bar.make(link, 1.5, maya_hubstyle.TOKENS, motion=False)
    model = strip.tabs.tools.model
    model.state = status.blank_state(mode)
    if mode == status.OBJECT:
        model.state["masks"]["Rendering"] = "part"
        model.state["masks"]["Dynamic"] = ""
        model.state["snaps"]["point"] = True
        model.state["lock"] = True
    if mode == status.COMPONENT:
        model.state["masks"]["Facet"] = "on"
        model.state["masks"]["Line"] = "part"
    strip.resize(1800, 140)
    strip.show()
    app.processEvents()
    tools = strip.tabs.tools
    tools.poll()
    if mode == status.OBJECT:
        tools.under = ("snap", "grid")
        tools.hover[("snap", "grid")] = 1.0
    app.processEvents()
    image = q.QtGui.QImage(strip.size(), q.QtGui.QImage.Format_ARGB32)
    image.fill(q.QtGui.QColor(maya_hubstyle.TOKENS["panel"]))
    strip.render(image)
    shots.append(image.copy(0, 0, strip.width(), strip.tabs.height() + 6))
    strip.deleteLater()

h = sum(s.height() for s in shots) + 10 * len(shots)
out = q.QtGui.QImage(shots[0].width(), h, q.QtGui.QImage.Format_ARGB32)
out.fill(q.QtGui.QColor("#121315"))
p = q.QtGui.QPainter(out)
y = 0
for s in shots:
    p.drawImage(0, y, s)
    y += s.height() + 10
p.end()
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "skill_bar_status.png")
out.save(path)
print(path)
