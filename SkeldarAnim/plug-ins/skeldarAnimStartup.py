"""skeldarAnimStartup - SkeldarAnim at Maya's start (2026-10-08).

The animator asked the hub's edge panel to wait at the screen edge from the
first second (the brainstorm's «Панель сразу ждёт у края»). Maya runs this
plug-in at startup because the installer copies it into the user's
plug-ins folder (`<userAppDir>/<version>/plug-ins`), loads it and sets it
to autoload (`install.register_startup` - its docstring has what was
measured). When the install had to make that folder, Maya would ask before
loading from it (its «Untrusted Plugin Loading» dialog) until its next
start: then the first hub opened in the next session loads it and sets the
autoload (`install.complete_startup`, Task 13b, 2026-10-09), and it starts
with Maya from the session after. In a GUI Maya it defers
`maya_hub.start()`, which builds the
edge panel hidden when ⋮ -> Edge panel is on and does nothing otherwise.
It registers no node and no command. Unloading it removes the edge panel.

Turn it off in Windows > Settings/Preferences > Plug-in Manager (untick
Auto load), or ⋮ -> Edge panel off (the plug-in then does nothing).

Stdlib at import: every Maya import lives inside the functions. And no
`__file__` at module level - Maya's loader runs a Python plug-in with
neither `__file__` nor `__name__` in its globals (measured 2026-10-08,
Maya 2027.2): `os.path.abspath(__file__)` there is a NameError and the
plug-in does not load. Its own path comes from `pluginInfo -path` inside
`initializePlugin` (measured answering the full path there).
"""

import os
import sys

NAME = "skeldarAnimStartup"
VENDOR = "SkeldarAnim"
VERSION = "1.0"
SHELF = "SkeldarAnim"                   # install.SHELF: the installed folder's name


def maya_useNewAPI():
    """Maya Python API 2.0."""


def plugin_dir(own_path, user_app_dir):
    """The SkeldarAnim folder this plug-in starts. Pure.

    The folder holding this file's folder when that is a SkeldarAnim (the
    repository's `SkeldarAnim/plug-ins/`, the installed copy's own
    `plug-ins/`): it holds `maya_hub.py`. Otherwise - the copy the installer
    puts into `<userAppDir>/<version>/plug-ins/` - the installed folder
    `install.install` copies the payload to: `<userAppDir>/scripts/SkeldarAnim`.
    """
    if own_path:
        here = os.path.dirname(os.path.dirname(os.path.abspath(own_path)))
        if os.path.isfile(os.path.join(here, "maya_hub.py")):
            return here
    return os.path.normpath(os.path.join(user_app_dir or "", "scripts", SHELF))


#  When Python imports the file (the tests), __file__ answers; under Maya's
#  loader it does not, and initializePlugin asks pluginInfo instead.
_OWN = globals().get("__file__")
PLUGIN_DIR = plugin_dir(_OWN, "") if _OWN else ""


def _start():
    """The hub's startup call, from the installed folder. Never raises: a
    hub that cannot start is no reason for a plug-in error at every start."""
    if not os.path.isfile(os.path.join(PLUGIN_DIR, "maya_hub.py")):
        print("SkeldarAnim startup: no SkeldarAnim at {0} - nothing started"
              " (drag install.py into Maya again, or untick skeldarAnimStartup's"
              " Auto load in the Plug-in Manager)".format(PLUGIN_DIR))
        return
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)
    try:
        import maya_hub
        maya_hub.start()
    except Exception:                                        # noqa: BLE001
        import traceback
        print("SkeldarAnim startup: the hub did not start")
        print(traceback.format_exc())


def initializePlugin(plugin):                                # noqa: N802
    global PLUGIN_DIR
    import maya.api.OpenMaya as om
    import maya.cmds as cmds
    om.MFnPlugin(plugin, VENDOR, VERSION)
    if not PLUGIN_DIR:
        PLUGIN_DIR = plugin_dir(cmds.pluginInfo(NAME, query=True, path=True),
                                cmds.internalVar(userAppDir=True))
    if cmds.about(batch=True):
        return
    import maya.utils
    maya.utils.executeDeferred(_start)


def uninitializePlugin(plugin):                              # noqa: N802
    import maya.api.OpenMaya as om
    om.MFnPlugin(plugin)
    #  only a hub already imported is stopped: unloading is no reason to
    #  import one (and an install has purged it - its own rebuild follows)
    hub = sys.modules.get("maya_hub")
    if hub is not None:
        try:
            hub.stop()
        except Exception:                                    # noqa: BLE001
            pass
