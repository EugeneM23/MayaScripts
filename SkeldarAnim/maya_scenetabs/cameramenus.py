"""Scene tabs: a panel's camera menus list the active tab's cameras only.

Maya fills Panels > Perspective / Orthographic from `listCameras`, which knows
nothing of tabs, so every tab's cameras showed in every tab (2026-10-16, found
live). Maya's own builders (`buildPerspLookthruMenu`, `buildOrthoLookthruMenu`,
others/*.mel) are read from Maya's file and defined again under a name of ours
(`skeldarTabsOrig_<proc>`); the proc of Maya's name then calls that and takes
out the rows naming a hidden tab's camera (`scope.shown`). With tabs off
nothing is taken out. GUI only; never raises.
"""

import os
import traceback

import maya.cmds as cmds

from . import scope

PROCS = ("buildPerspLookthruMenu", "buildOrthoLookthruMenu")
PREFIX = "skeldarTabsOrig_"


def renamed(text, proc):
    """Maya's file text with its global proc `proc` renamed ours. Pure; None when the
    file does not define it."""
    head = "global proc %s(" % proc
    spaced = "global proc %s (" % proc
    if head in text:
        return text.replace(head, "global proc %s%s(" % (PREFIX, proc), 1)
    if spaced in text:
        return text.replace(spaced, "global proc %s%s (" % (PREFIX, proc), 1)
    return None


def wrapper(proc):
    return ('global proc %s(string $parent, string $panel) {\n'
            '    %s%s($parent, $panel);\n'
            '    python("import maya_scenetabs.cameramenus as _m; _m.prune(\'" + $parent + "\')");\n'
            '}\n' % (proc, PREFIX, proc))


def _source_file(proc):
    import maya.mel as mel
    path = mel.eval('whatIs "%s"' % proc)
    marker = "found in: "
    if marker in path:
        return path.split(marker, 1)[1].strip()
    found = os.path.join(os.environ.get("MAYA_LOCATION", ""), "scripts", "others", proc + ".mel")
    return found if os.path.isfile(found) else ""


def install():
    if cmds.about(batch=True):
        return False
    import maya.mel as mel
    done = 0
    for proc in PROCS:
        try:
            if not mel.eval('exists "%s%s"' % (PREFIX, proc)):
                mel.eval('source "%s"' % proc)          # Maya's own, loaded
                path = _source_file(proc)
                if not path:
                    continue
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = renamed(handle.read(), proc)
                if text is None:
                    continue
                mel.eval(text)
            mel.eval(wrapper(proc))
            done += 1
        except Exception:                                       # noqa: BLE001
            print(traceback.format_exc())
    return done == len(PROCS)


def prune(parent):
    """The rows of `parent` naming a hidden tab's camera deleted."""
    try:
        if not scope.tabs_on():
            return 0
        gone = 0
        for item in cmds.menu(parent, q=True, itemArray=True) or []:
            full = parent + "|" + item
            try:
                if cmds.menuItem(full, q=True, divider=True) or cmds.menuItem(full, q=True, subMenu=True):
                    continue
                label = cmds.menuItem(full, q=True, label=True) or ""
            except RuntimeError:
                continue
            if not label or not cmds.objExists(label):
                continue
            if not scope.shown([label]):
                cmds.deleteUI(full, menuItem=True)
                gone += 1
            elif scope.local(label) != label:
                cmds.menuItem(full, e=True, label=scope.local(label))   # as the tab shows it
        return gone
    except Exception:                                           # noqa: BLE001
        print(traceback.format_exc())
        return 0
