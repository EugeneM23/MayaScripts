"""Live check (a disposable GUI Maya with a scratch MAYA_APP_DIR, never the animator's):
the scene tabs make no Maya workspace, and the sweep takes the old build's out
(2026-10-16, 8/8 on port 7051). Sent through the bridge."""
import os, sys, tempfile
REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO not in sys.path:
    sys.path.insert(0, REPO)
for name in [n for n in sys.modules if n.split(".")[0] == "maya_scenetabs"]:
    del sys.modules[name]
import maya.cmds as cmds
W = cmds.workspaceLayoutManager
folder = os.path.join(cmds.internalVar(userPrefDir=True), "workspaces").replace("\\", "/")
RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def ours():
    return [l for l in W(listLayouts=True) or [] if l.startswith("SkeldarTab")]


def files():
    return [f for f in os.listdir(folder) if f.startswith("SkeldarTab")]


# the old build's road: a saveAs per tab, the last one current
for name in ("SkeldarTab_tab_one", "SkeldarTab_tab_untitled1", "SkeldarTab_tab_x_ma_skeldartmp"):
    W(saveAs=name)
cmds.optionVar(stringValue=("workspaceLayoutToLoadOnStartup", W(q=True, current=True)))
main = None
try:
    import maya.OpenMayaUI as omui
    from shiboken6 import wrapInstance
    from PySide6 import QtWidgets
    main = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
except Exception:
    pass
docks_before = sorted(c for c in cmds.lsUI(type="workspaceControl") or [] if cmds.workspaceControl(c, q=True, visible=True))
print("seeded:", ours(), files(), "current", W(q=True, current=True))

from maya_scenetabs import hooks, workspaces, opening, switching, session
sys._skeldar_tab_workspaces_swept = False
hooks.install()
gate("sweep: no SkeldarTab workspace listed", not ours(), ours())
gate("sweep: no SkeldarTab file in prefs", not files(), files())
gate("sweep: the current workspace is the animator's", not workspaces.is_ours(W(q=True, current=True)),
     W(q=True, current=True))
gate("sweep: Maya starts in it", cmds.optionVar(q="workspaceLayoutToLoadOnStartup") == W(q=True, current=True),
     cmds.optionVar(q="workspaceLayoutToLoadOnStartup"))
docks_after = sorted(c for c in cmds.lsUI(type="workspaceControl") or [] if cmds.workspaceControl(c, q=True, visible=True))
gate("sweep: the screen kept (the same docked panels)", docks_after == docks_before, (docks_before, docks_after))

home = W(q=True, current=True)
work = os.path.join(tempfile.gettempdir(), "skeldar_ws_probe").replace("\\", "/")
os.makedirs(work, exist_ok=True)
paths = {}
hooks.remove()
for tag in ("A", "B", "C"):
    cmds.file(new=True, force=True)
    cmds.polyCube(name="cube" + tag)
    paths[tag] = work + "/ws%s.ma" % tag
    cmds.file(rename=paths[tag]); cmds.file(save=True, type="mayaAscii", force=True)
cmds.file(paths["A"], open=True, force=True)
opening.ASK = lambda message, buttons: "Don't Save"
opening.open_tab(paths["B"])
opening.open_tab(paths["C"])
for target in ("tab_wsA", "tab_wsB", "tab_wsC", "tab_wsA"):
    switching.switch(target)
opening.new_tab()
gate("tabs: three tabs, a new one and four switches made no workspace", not ours() and not files(),
     (ours(), files()))
gate("tabs: the current workspace untouched", W(q=True, current=True) == home, W(q=True, current=True))
opening.close_others(session.state()["active"])
gate("tabs: back to one scene, still none", not ours() and not files() and W(q=True, current=True) == home)
print("%d of %d gates failed" % (RESULTS.count(False), len(RESULTS)))
