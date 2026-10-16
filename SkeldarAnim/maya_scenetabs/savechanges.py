"""Scene tabs: Maya's «save changes?» is not asked before an open that goes into a tab.

Maya's File > Open and Open Recent (`pv_performAction`, `performFileAction`) call
`saveChanges("file -f ... -o \\"<path>\\";addRecentFile(...)")`, and that asks to save a
modified scene BEFORE `file -o` runs - before the Open check (`hooks.on_open`) takes
the file into a tab of its own. Nothing is replaced then, and the question reads as if
the scene were about to go (2026-10-16).

Maya's own `saveChanges.mel` is read, its proc renamed `skeldarMayaSaveChanges`, the
copy sourced from a file of ours, and `saveChanges` defined over it: an action that
opens a Maya scene the check takes into a tab (`hooks.goes_to_tab`) runs at once;
anything else (New, an open into an empty scene, the same file opened again, a saved
session, the checks off, a Python error) is Maya's own, word for word. A Maya whose
file is not the one this knows keeps its own proc, said in the Script Editor. GUI only;
never raises.
"""

import os
import re
import sys
import tempfile
import traceback

PROC = "saveChanges"
MAYA = "skeldarMayaSaveChanges"
FILE = "saveChanges.mel"
COPY = "skeldarSaveChanges.mel"                 # never FILE: `_source_file` must not find it
ACTION = "gSkeldarSaveChangeAction"

HEADER = re.compile(r"global\s+proc\s+int\s+saveChanges\s*\(")
OPEN = re.compile(r'(?:^|[\s;])-o(?:pen)?\s+"((?:[^"\\]|\\.)*)"')

WRAPPER = r'''
global string $%(action)s;
global proc int saveChanges(string $saveChangeAction)
{
    global string $%(action)s;
    $%(action)s = $saveChangeAction;
    int $tab = 0;
    if (catch($tab = python("__import__('maya_scenetabs.savechanges', fromlist=['savechanges']).skip_question()")))
        $tab = 0;
    if (!$tab)
        return %(maya)s($saveChangeAction);
    catch(`appHome -e -visible 0`);
    if ($saveChangeAction != "")
        evalEcho($saveChangeAction);
    return 1;
}
''' % {"action": ACTION, "maya": MAYA}


def opened_path(action):
    """The file a `saveChanges` action opens (`file ... -o "<path>"`), else "". Pure."""
    found = OPEN.search(action or "")
    if not found:
        return ""
    return re.sub(r"\\(.)", r"\1", found.group(1))


def renamed(text):
    """Maya's saveChanges.mel with its proc renamed `MAYA`, or None for a file this
    does not know (no such proc, or more than one). Pure."""
    if len(HEADER.findall(text or "")) != 1:
        return None
    return HEADER.sub("global proc int %s(" % MAYA, text, count=1)


def skip_question(action=None):
    """Called by our `saveChanges` (the action read from its MEL global): True when the
    action opens a Maya scene the Open check takes into a tab. Never raises."""
    try:
        if action is None:
            import maya.mel as mel
            action = mel.eval("global string $%s; string $_skeldarAction = $%s;" % (ACTION, ACTION))
        path = opened_path(action)
        if not path:
            return False
        from . import hooks
        return bool(hooks.goes_to_tab(path))
    except Exception:                                           # noqa: BLE001
        print(traceback.format_exc())
        return False


def _source_file():
    """Maya's own saveChanges.mel: its install's, else where Maya found it."""
    path = os.path.join(os.environ.get("MAYA_LOCATION", ""), "scripts", "others", FILE)
    if os.path.isfile(path):
        return path
    import maya.mel as mel
    try:
        where = mel.eval('whatIs "%s"' % PROC) or ""
    except RuntimeError:
        where = ""
    marker = "found in: "
    if marker in where:
        path = where.split(marker, 1)[1].strip()
        if os.path.basename(path) == FILE and os.path.isfile(path):
            return path
    return ""


def _state():
    state = getattr(sys, "_skeldar_savechanges", None)
    if state is None:
        state = {"failed": ""}
        sys._skeldar_savechanges = state
    return state


def install(force=False):
    """Maya's proc copied under another name, ours defined over it. True when in place."""
    try:
        import maya.cmds as cmds
        if cmds.about(batch=True) and not force:
            return False
        state = _state()
        path = _source_file()
        if not path:
            state["failed"] = "%s not found" % FILE
            print("Scene Tabs: %s - Maya asks «save changes?» before a tab opens" % state["failed"])
            return False
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = renamed(handle.read())
        if text is None:
            state["failed"] = "%s is not the file this knows" % FILE
            print("Scene Tabs: %s - Maya asks «save changes?» before a tab opens" % state["failed"])
            return False
        folder = os.path.join(tempfile.gettempdir(), "skeldar_scenetabs")
        if not os.path.isdir(folder):
            os.makedirs(folder)
        target = os.path.join(folder, COPY)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
        import maya.mel as mel
        mel.eval('source "%s";' % target.replace("\\", "/"))
        mel.eval(WRAPPER)
        state["failed"] = ""
        return True
    except Exception:                                           # noqa: BLE001
        print(traceback.format_exc())
        return False
