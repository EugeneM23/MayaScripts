"""Live check (a disposable GUI Maya with a scratch MAYA_APP_DIR, never the animator's):
the Anim Layer Editor shows the active tab as an ordinary scene (2026-10-16). Sent through
the bridge after scenes A (layers LA1, LA2) and B (LB1, LB2) are open as tabs plus a new
empty tab, the Layer Editor's Anim tab visible. Clicks are real Qt mouse events down the
tree's text column; Maya's refresh is deferred, so the tree is rebuilt by its own proc here."""
import sys
REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO not in sys.path:
    sys.path.insert(0, REPO)
for name in [n for n in sys.modules if n.split(".")[0] == "maya_scenetabs"]:
    del sys.modules[name]
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaUI as omui
from shiboken6 import wrapInstance
from PySide6 import QtWidgets, QtCore, QtGui
from maya_scenetabs import layereditor, layers, switching, session, opening

T = "AnimLayerTabanimLayerEditor"
RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def rebuild():
    mel.eval('rebuildAnimLayerEditor("AnimLayerTab")')
    QtWidgets.QApplication.processEvents()


def items():
    return cmds.treeView(T, q=True, children="") or []


def label(item):
    try:
        return cmds.treeView(T, q=True, itemDisplayLabel=item)    # Maya 2027 spells it so
    except TypeError:
        return None


def selected():
    return [l for l in cmds.ls(type="animLayer") if cmds.animLayer(l, q=True, selected=True)]


def clear():
    for l in cmds.ls(type="animLayer"):
        cmds.animLayer(l, e=True, selected=False)
    for item in items():
        cmds.treeView(T, e=True, selectItem=(item, False))
    QtWidgets.QApplication.processEvents()


def click(y, x=250):
    tree = wrapInstance(int(omui.MQtUtil.findControl(T)), QtWidgets.QWidget)
    point = QtCore.QPointF(x, y)
    for kind, buttons in ((QtCore.QEvent.MouseButtonPress, QtCore.Qt.LeftButton),
                          (QtCore.QEvent.MouseButtonRelease, QtCore.Qt.NoButton)):
        tree = wrapInstance(int(omui.MQtUtil.findControl(T)), QtWidgets.QWidget)
        event = QtGui.QMouseEvent(kind, point, QtCore.QPointF(tree.mapToGlobal(point.toPoint())),
                                  QtCore.Qt.LeftButton, buttons, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(tree, event)
    QtWidgets.QApplication.processEvents()


def scan():
    hits = []
    for y in range(4, 160, 6):
        clear()
        click(y)
        hits.append(tuple(selected()))
    return hits


cmds.workspaceControl("ChannelBoxLayerEditor", e=True, visible=True, restore=True)
cmds.tabLayout("DisplayLayerUITabLayout", e=True, selectTab="AnimLayerTab")
gate("installed", layereditor.install() and layereditor.installed())
root = cmds.animLayer(q=True, root=True)
switching.switch("tab_leB")
rebuild()
gate("tab B: the base and B's layers, no holder", items() == [root, "tab_leB:LB1", "tab_leB:LB2"], items())
labels = [label(i) for i in items()]
gate("tab B: the base reads BaseAnimation, the layers their own names",
     labels == ["BaseAnimation", "LB1", "LB2"] or labels == [None, None, None], labels)
cmds.setAttr(root + ".collapse", 1)                     # as the animator's root carried it
rebuild()
hits = scan()
gate("a click never selects more than one layer, with the base collapsed", all(len(h) <= 1 for h in hits),
     sorted(set(hits)))
gate("a click on the base selects the base alone", (root,) in hits, sorted(set(hits)))
gate("each of B's layers can be clicked", ("tab_leB:LB1",) in hits and ("tab_leB:LB2",) in hits)
cmds.setAttr(root + ".collapse", 0)
clear()
switching.switch("tab_untitled")
rebuild()
gate("the empty tab: an empty editor", items() == [], items())
switching.switch("tab_leA")
rebuild()
gate("tab A: the base and A's layers", items() == [root, "tab_leA:LA1", "tab_leA:LA2"], items())
gate("buildAnimLayerArray holds no holder", not [l for l in mel.eval("buildAnimLayerArray()")
                                                 if l.endswith("AnimLayerRoot")], mel.eval("buildAnimLayerArray()"))
mel.eval('catch(`eval "source layerEditor"`)')          # as Maya does when it builds the editor (the UI
                                                        # it then builds exists here: its error is caught)
gate("Maya's own file sourced again: ours no longer", not layereditor.installed())
layers._rebuild_editors()
gate("our refresh puts ours back", layereditor.installed())
gate("...and the editor shows tab A again", items() == [root, "tab_leA:LA1", "tab_leA:LA2"], items())
for other in [t["ns"] for t in session.state()["tabs"] if t["ns"] != "tab_leA"]:
    opening.close_tab(other, ask=False)                 # no dialog over the port
rebuild()
gate("back to one scene: Maya's own tree", items() == ["BaseAnimation", "LA1", "LA2"], items())
print("%d of %d gates failed" % (RESULTS.count(False), len(RESULTS)))
