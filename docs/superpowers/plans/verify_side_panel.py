"""Side panel (2026-10-17), GUI Maya only - the animator's live check.

Run in a Maya with the hub (Script Editor, Python):
    exec(open(r"C:/!!!Work/MayaScripts/docs/superpowers/plans/verify_side_panel.py").read())

It switches the side panel on, checks that Maya's own editors moved into it and still
work, then switches it off and checks everything is back. Leaves the mode as it found it.
Spec: docs/superpowers/specs/2026-10-17-side-panel-design.md
"""
import maya.cmds as cmds
import maya.mel as mel

import maya_sidepanel
from maya_sidepanel import holder

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def form_in_panel(form):
    edge = maya_sidepanel._state().get("edge")
    w = holder.widget(form)
    return w is not None and edge is not None and edge.host.isAncestorOf(w)


before = maya_sidepanel.mode()
print(maya_sidepanel.set_mode("edge"))
edge = maya_sidepanel._state().get("edge")
gate("1 the panel stands", edge is not None and edge.alive())
gate("2 the Attribute Editor is in it", form_in_panel("MainAttributeEditorLayout"))
gate("3 the Channel Box / Layer Editor is in it",
     form_in_panel("MainChannelsLayersLayout") or form_in_panel("MainChannelBoxLayout"))
gate("4 Maya's two controls hidden",
     not holder.ws_visible(holder.dock_control("Attribute Editor")))
gate("5 isAttributeEditorVisible answers for the panel",
     mel.eval("isAttributeEditorVisible()") == 1)
cube = cmds.polyCube(name="sidePanelProbe")[0]
cmds.select(cube)
mel.eval("showEditor %s" % cube)
gate("6 showEditor did not bring Maya's control back",
     not holder.ws_visible(holder.dock_control("Attribute Editor")))
edge.reveal(instant=True, tab="attributes")
gate("7 out on Attributes", edge.shown and edge.panel.tab == "attributes")
mel.eval("ToggleChannelsLayers")          # Maya's own toggle: ours comes out on Channels
edge.place_tick()
gate("8 Maya's toggle brings ours out on Channels", edge.panel.tab == "channels")
print(maya_sidepanel.set_mode("maya"))
gate("9 the Attribute Editor is back", not form_in_panel("MainAttributeEditorLayout")
     and holder.widget("MainAttributeEditorLayout") is not None)
gate("10 Maya's procs again",
     "interactively" not in (mel.eval('whatIs "isAttributeEditorVisible"') or ""))
cmds.delete(cube)
maya_sidepanel.set_mode(before)
print("%d of %d gates passed" % (sum(ok for _n, ok in RESULTS), len(RESULTS)))
