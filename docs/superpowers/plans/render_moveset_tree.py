"""The Moveset card's tree view drawn offscreen from the animator's moveset folder.

    mayapy render_moveset_tree.py <folder> <out.png> [weapon]

The weapon is a key the folder holds (`longsword`, `dagger`); without one, the
first weapon there. The statuses and the assignee are a demonstration, put on
the largest tree's first cards - the folder's own state is not touched.
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
key = sys.argv[3] if len(sys.argv) > 3 else ""
weapon = m.weapon_of(folder, key) if key else (m.weapons(folder) or [None])[0]
if weapon is None:
    raise SystemExit("no graph in {0}".format(folder))
graph = m.load_graph(folder, weapon.graph)
state = m.read_state(folder)

#  the biggest tree, and a status on its first cards so the dots are in the
#  picture
trees = m.trees(graph, state, "combos")
tree = max(trees, key=lambda t: len(t.nodes))
first = [node.id for node in tree.nodes]
state["status"][m.skey(first[0], "3p")] = "done"
state["status"][m.skey(first[0], "1p")] = "progress"
if len(first) > 1:
    state["status"][m.skey(first[1], "3p")] = "backlog"
state["people"] = ["Anna"]
state["icons"] = {"Anna": "\U0001f98a"}
state["assignee"] = {m.skey(first[0], "1p"): "Anna"}

view = v.TreeView()
view.resize(900, 640)
view.set_data(graph, state, folder, weapon)
view.set_filter(root=tree.root)
view.frame()
if len(view.cards) > 1:
    view.pick(view.cards[1].node)
view.show()
app.processEvents()
view.grab().save(out)
print("{0}: {1} trees, this one {2} cards -> {3}".format(
    weapon.label, len(trees), len(view.cards), out))
