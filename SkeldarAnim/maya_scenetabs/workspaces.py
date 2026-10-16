"""Scene tabs: the Maya workspaces the first build left behind.

Until 2026-10-16 every tab saved a workspace `SkeldarTab_<tab>` (`workspaceLayoutManager
-saveAs`) on every switch, which also made it Maya's CURRENT workspace - and so the
workspace Maya opens on its next start (`workspaceLayoutToLoadOnStartup`). Maya lists
that workspace as `SkeldarTab <tab>` (spaces for underscores, measured), so the
plugin's own restore and delete, which asked for the underscore name, never matched:
a tab's layout was never brought back, and no workspace was ever deleted - 29 in the
animator's prefs on the day. Tabs no longer touch workspaces; `sweep` takes the old
ones out, once a Maya session.

A workspace cannot be deleted while it is the current one (measured: the delete does
nothing). When the current one is ours, what is on screen is saved first over the
animator's own workspace - the one most recently written before ours took over,
else General (`home`) - which is silent and leaves the screen as it is (measured,
0.01 s), and Maya's start-up workspace is pointed at it.
"""

import os
import sys
import traceback

PREFIX = "SkeldarTab"
DEFAULT_HOME = "General"
STARTUP_VAR = "workspaceLayoutToLoadOnStartup"


def is_ours(name):
    """A workspace a tab saved: `SkeldarTab_<tab>`, listed by Maya as `SkeldarTab <tab>`.
    Pure."""
    text = name or ""
    return text.startswith(PREFIX + " ") or text.startswith(PREFIX + "_")


def listed_name(file_name):
    """The name Maya lists a workspace file under (`Modeling_-_Standard.json` ->
    `Modeling - Standard`). Pure."""
    return os.path.splitext(file_name)[0].replace("_", " ")


def home(listed, written):
    """The workspace to keep the screen under when the current one is ours: of the
    animator's own workspaces (`listed`, the names Maya lists), the one written last
    (`written`: {listed name: mtime}), else General, else the first one listed. Pure."""
    own = [name for name in listed if not is_ours(name)]
    dated = [name for name in own if name in written]
    if dated:
        return max(dated, key=lambda name: written[name])
    if DEFAULT_HOME in own or not own:
        return DEFAULT_HOME
    return own[0]


def _written(cmds):
    folder = os.path.join(cmds.internalVar(userPrefDir=True), "workspaces")
    found = {}
    try:
        for file_name in os.listdir(folder):
            if file_name.lower().endswith(".json"):
                found[listed_name(file_name)] = os.path.getmtime(os.path.join(folder, file_name))
    except OSError:
        pass
    return found


def sweep(cmds=None):
    """Every workspace a tab saved deleted. Returns how many (GUI only, never raises)."""
    try:
        if cmds is None:
            import maya.cmds as cmds
        if cmds.about(batch=True):
            return 0
        manager = cmds.workspaceLayoutManager
        listed = manager(listLayouts=True) or []
        ours = [name for name in listed if is_ours(name)]
        if not ours:
            return 0
        current = manager(q=True, current=True) or ""
        if is_ours(current):
            manager(saveAs=home(listed, _written(cmds)))
        gone = 0
        for name in ours:
            manager(delete=name)
            gone += 1
        if cmds.optionVar(exists=STARTUP_VAR) and is_ours(cmds.optionVar(q=STARTUP_VAR) or ""):
            cmds.optionVar(stringValue=(STARTUP_VAR, manager(q=True, current=True) or DEFAULT_HOME))
        print("Scene Tabs: %d workspace(s) of old scene tabs deleted" % gone)
        return gone
    except Exception:                                           # noqa: BLE001 - housekeeping only
        print(traceback.format_exc())
        return 0


def sweep_once():
    """`sweep` the first time it is asked in this Maya session (the flag on `sys`:
    an update reloads this module)."""
    if getattr(sys, "_skeldar_tab_workspaces_swept", False):
        return 0
    sys._skeldar_tab_workspaces_swept = True
    return sweep()
