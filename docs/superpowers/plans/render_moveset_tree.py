"""The Moveset card's tree view drawn offscreen from the animator's moveset folder.

    mayapy render_moveset_tree.py <folder> <out.png>
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SkeldarAnim"))

from PySide6 import QtGui, QtWidgets  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeuib.ttf")
QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/seguiemj.ttf")
app.setFont(QtGui.QFont("Segoe UI"))

from maya_moveset import model as m  # noqa: E402
from maya_moveset import view as v  # noqa: E402

folder, out = sys.argv[1], sys.argv[2]
graph = m.load_graph(folder)
state = m.read_state(folder)
state["status"].update({"AM_Longsword_Attack_Forward_Combo_2_Hold_1|3p": "done",
                        "AM_Longsword_Attack_Forward_Combo_2_Hold_1|1p": "progress",
                        "AM_Longsword_Attack_Forward_Combo_2_Hold_2_Left_Hold|3p": "backlog"})
state["people"] = ["Anna"]
state["icons"] = {"Anna": "\U0001f98a"}
state["assignee"] = {"AM_Longsword_Attack_Forward_Combo_2_Hold_1|1p": "Anna"}
view = v.TreeView()
view.resize(900, 640)
view.set_data(graph, state, folder)
view.set_filter(root="AM_Longsword_Attack_Forward_Combo_2_Hold_1")
view.frame()
view.pick(view.cards[1].node)
view.show()
app.processEvents()
image = view.grab()
image.save(out)
print("trees", len(view.trees()), "cards", len(view.cards), "->", out)
