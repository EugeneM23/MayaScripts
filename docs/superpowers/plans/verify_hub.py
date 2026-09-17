"""verify_hub.py - the SkeldarAnim hub, live, in the animator's Maya.

Send through the command port (CLAUDE.md, "Driving the user's live Maya")
with the INSTALLED copy first on sys.path - the hub is what the shelf
opens, so the proof is against what the shelf imports. Read-only for the
scene: it opens and closes UI, writes six optionVars (the collapse memory,
put back at the end) and touches no node.

Spec: docs/superpowers/specs/2026-09-17-skeldar-hub-design.md
"""
import maya.cmds as cmds

FAILED = []
PASSED = []


def gate(n, name, ok, detail=""):
    (PASSED if ok else FAILED).append(n)
    print("%s %2d %s%s" % ("ok  " if ok else "FAIL", n, name,
                           (" - " + str(detail)) if detail else ""))


import maya_hub
from maya_uebridge import window as ue
from maya_scenesetup import window as ss
import maya_vpstudio
import maya_colour
import maya_rig_retarget
import maya_hotkeys

memory = dict((s.key, maya_hub.collapsed(s.key)) for s in maya_hub.SECTIONS)
had_hub = cmds.workspaceControl(maya_hub.CONTROL, exists=True)
try:
    # ---- 1-3: the hub comes up from show(), the way the shelf button calls it
    if had_hub:
        cmds.deleteUI(maya_hub.CONTROL)
    for s in maya_hub.SECTIONS:
        maya_hub.remember(s.key, False)
    control = maya_hub.show()
    gate(1, "show() creates the workspaceControl",
         cmds.workspaceControl(maya_hub.CONTROL, exists=True), control)
    #  `workspaceControl -q -uiScript` answers None (measured 2026-09-17):
    #  Maya stores the script but will not show it, so the gate is on the
    #  script show() hands over - it must bootstrap THE INSTALLED folder,
    #  the one this run imported maya_hub from.
    script = maya_hub.uiscript(maya_hub.plugin_root())
    installed = maya_hub.__file__.replace("\\", "/").rsplit("/", 1)[0]
    gate(2, "the uiScript bootstraps the installed folder and builds",
         ('_p = "%s"' % installed) in script
         and "sys.path.insert(0, _p)" in script
         and "maya_hub.build()" in script, installed)
    gate(3, "no legacy standalone window is left",
         not [w for w in maya_hub.LEGACY_WINDOWS if cmds.window(w, exists=True)])

    # ---- 4-5: six collapsable frames in shelf order, all open
    frames = [s.frame for s in maya_hub.SECTIONS]
    gate(4, "seven frames exist", all(cmds.frameLayout(f, exists=True) for f in frames)
         and len(frames) == 7,
         [s.label for s in maya_hub.SECTIONS])
    gate(5, "all open (memory says open)",
         not any(cmds.frameLayout(f, query=True, collapse=True) for f in frames))

    # ---- 6-11: every section built its controls, and says it is open
    checks = (
        (6, "UE Bridge", ue._STATUS, ue.is_open),
        (7, "Characters + Weapons", ss._STATUS, lambda: ss.is_open()
         and cmds.control(ss._CHARACTER_STATUS, exists=True)
         and cmds.control(ss._BOUND, exists=True)),
        (8, "Retarget", maya_rig_retarget.STATUS, maya_rig_retarget.is_open),
        (9, "Hotkeys", maya_hotkeys.PANEL_BUTTON, maya_hotkeys.is_open),
        (10, "Studio", maya_vpstudio.STATUS, maya_vpstudio.is_open),
        (11, "Colour", maya_colour.STATUS, maya_colour.is_open),
    )
    for n, label, name, is_open in checks:
        gate(n, label + " section built and is_open()",
             cmds.control(name, exists=True) and is_open(), name)

    # ---- 12: the hotkeys toggle reads the real state
    gate(12, "Hotkeys toggle label follows the active set",
         cmds.button(maya_hotkeys.PANEL_BUTTON, query=True, label=True)
         == maya_hotkeys.panel_label(maya_hotkeys.is_active()))

    # ---- 13-15: a shelf button's baked command opens its section
    buttons = cmds.shelfLayout("SkeldarAnim", query=True, childArray=True) or []
    labels = [cmds.shelfButton(b, query=True, label=True) for b in buttons]
    gate(13, "shelf: the hub first, then the seven", labels[:8] == [
        "SkeldarAnim", "UE Bridge", "Characters", "Weapons", "Retarget",
        "Hotkeys", "Studio", "Colour"], labels)
    for key in ("uebridge", "characters", "weapons", "studio", "colour"):
        cmds.frameLayout(maya_hub.section(key).frame, edit=True, collapse=True)
        maya_hub.remember(key, True)
    colour = [b for b, l in zip(buttons, labels) if l == "Colour"]
    if colour:
        exec(cmds.shelfButton(colour[0], query=True, command=True),
             {"__name__": "__main__"})
    gate(14, "the Colour shelf button expands Colour and nothing else",
         bool(colour)
         and not cmds.frameLayout(maya_hub.section("colour").frame,
                                  query=True, collapse=True)
         and cmds.frameLayout(maya_hub.section("studio").frame,
                              query=True, collapse=True)
         and cmds.frameLayout(maya_hub.section("uebridge").frame,
                              query=True, collapse=True))
    gate(15, "and remembers Colour open", maya_hub.collapsed("colour") is False)

    # ---- 16: one control, not two - show() on an open hub restores it
    maya_hub.show("studio")
    gate(16, "show() on an open hub keeps ONE control and expands the section",
         cmds.workspaceControl(maya_hub.CONTROL, exists=True)
         and not cmds.frameLayout(maya_hub.section("studio").frame,
                                  query=True, collapse=True))

    # ---- 17: the column fits a docked panel: its minimum width in logical
    # units is under the hub's initial width (a formLayout inside the column
    # once asked for 1128 px - measured 2026-09-17)
    try:
        from PySide6 import QtWidgets
        from shiboken6 import wrapInstance
        import maya.OpenMayaUI as omui
        ptr = omui.MQtUtil.findLayout(maya_hub.COLUMN)
        column = wrapInstance(int(ptr), QtWidgets.QWidget)
        scale = float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        need = column.minimumSizeHint().width() / scale
        gate(17, "column minimum width fits the initial hub width",
             need <= maya_hub.INITIAL_WIDTH, "%.0f logical of %d" % (
                 need, maya_hub.INITIAL_WIDTH))
    except Exception as exc:                                  # noqa: BLE001
        gate(17, "column minimum width fits the initial hub width", False, exc)

    # ---- 18: an unknown section is refused
    try:
        maya_hub.expand("nonsense")
        gate(18, "expand of an unknown key raises", False)
    except KeyError:
        gate(18, "expand of an unknown key raises", True)
finally:
    for key, was in memory.items():
        maya_hub.remember(key, was)
        if cmds.frameLayout(maya_hub.section(key).frame, exists=True):
            cmds.frameLayout(maya_hub.section(key).frame, edit=True,
                             collapse=was)

print("")
if FAILED:
    print("FAILURES: %d of %d gates failed: %s" % (
        len(FAILED), len(FAILED) + len(PASSED), FAILED))
else:
    print("checks passed: %d of %d gates" % (len(PASSED), len(PASSED)))
