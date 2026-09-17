"""maya_hub - the SkeldarAnim window: one dockable panel, every tool a section.

The animator's ask (2026-09-17): «объединим наши скрипты в одно окошко,
которое можно будет куда-то прикрепить или открепить; каждый раздел -
вкладка с возможностью закрыть и раскрыть». So: one `workspaceControl`
(dock it to any edge, tab it into any dock, tear it off, Maya remembers
where) holding a scrollable column of `frameLayout` sections in shelf
order, each collapsible, several open at once, the collapsed set
remembered per section in an optionVar.

    import maya_hub; maya_hub.show()            # the SkeldarAnim shelf button
    maya_hub.show("colour")                      # what Colour's button does

Every tool builds its controls with `build_panel()` into whatever layout is
current; this module supplies the layout. The tools are imported lazily
inside `build()` and import this module lazily inside their `show_window`,
so nothing here imports a tool at module level and there is no cycle.

Two facts the shape rests on:

- A `cmds` control has ONE name per Maya session. `mayaSceneSetupStatus`
  can exist in the hub or in a window of its own, not both - which is why
  every `show_window()` now opens the hub on its section and the old
  standalone windows are gone rather than kept beside it.
- Maya replays a docked workspaceControl's `uiScript` at startup, before
  any shelf button has put our folder on `sys.path`. So the script carries
  the bootstrap with the plugin folder baked in (`uiscript`), read from
  this file's own location - the hotkey runTimeCommands' pattern.

Spec: docs/superpowers/specs/2026-09-17-skeldar-hub-design.md
"""

import collections
import os
import traceback

import maya.cmds as cmds

CONTROL = "skeldarAnimHub"
LABEL = "SkeldarAnim"
SCROLL = "skeldarAnimHubScroll"
COLUMN = "skeldarAnimHubColumn"
OPTIONVAR = "skeldarAnimHub_collapsed_{0}"

INITIAL_WIDTH = 500
INITIAL_HEIGHT = 900
ROW_SPACING = 4                 # the column's gap between sections

# Windows earlier builds opened on their own. Deleted on every show, or a
# panel left up from the previous build stays wired to dead code beside
# the hub (the checkouts popup taught this in August).
LEGACY_WINDOWS = ("ueAnimBridgeWindow", "ueBridgeCheckouts",
                  "mayaSceneSetupWindow", "mayaWeaponsWindow",
                  "skeldarVpStudioWin", "skeldarColourWin")

Section = collections.namedtuple("Section",
                                 "key label module builder frame")

# Shelf order. `module.builder()` builds the tool's controls into the
# current parent; `frame` is the frameLayout's control name. Scene Setup is
# two sections of one module (2026-09-17, «декомпозируем scenesetup на
# characters и weapons»); Weapons must follow Characters, because the
# weapons builder's refresh writes the Characters header.
SECTIONS = (
    Section("uebridge", "UE Bridge", "maya_uebridge.window",
            "build_panel", "skeldarHubFrameUebridge"),
    Section("characters", "Characters", "maya_scenesetup.window",
            "build_characters_panel", "skeldarHubFrameCharacters"),
    Section("weapons", "Weapons", "maya_scenesetup.window",
            "build_weapons_panel", "skeldarHubFrameWeapons"),
    Section("connections", "Connections", "maya_scenesetup.connections",
            "build_panel", "skeldarHubFrameConnections"),
    Section("retarget", "Retarget", "maya_rig_retarget",
            "build_panel", "skeldarHubFrameRetarget"),
    Section("hotkeys", "Hotkeys", "maya_hotkeys",
            "build_panel", "skeldarHubFrameHotkeys"),
    Section("studio", "Studio", "maya_vpstudio",
            "build_panel", "skeldarHubFrameStudio"),
    Section("colour", "Colour", "maya_colour",
            "build_panel", "skeldarHubFrameColour"),
)

_BY_KEY = dict((s.key, s) for s in SECTIONS)


# ------------------------------------------------------------------- pure

def section(key):
    """The Section for `key`, or None."""
    return _BY_KEY.get(key)


def uiscript(root):
    """The Python Maya replays to (re)build the panel, plugin folder baked in.

    Forward slashes only: the string reaches Maya's workspace file, where a
    backslash starts an escape.
    """
    root = root.replace("\\", "/").rstrip("/")
    return ("import sys\n"
            "_p = \"{0}\"\n"
            "if _p not in sys.path:\n"
            "    sys.path.insert(0, _p)\n"
            "import maya_hub\n"
            "maya_hub.build()\n").format(root)


def scroll_offset(heights, index, spacing):
    """Pixels from the column's top to section `index`: the sections above
    it as Maya laid them out plus the gaps between them. Pure."""
    above = list(heights)[:index]
    return int(sum(above) + spacing * len(above))


# ------------------------------------------------------------------ memory

def collapsed(key):
    """Whether section `key` was left collapsed. Open by default."""
    var = OPTIONVAR.format(key)
    if cmds.optionVar(exists=var):
        return bool(cmds.optionVar(query=var))
    return False


def remember(key, is_collapsed):
    cmds.optionVar(intValue=(OPTIONVAR.format(key), int(bool(is_collapsed))))


# ------------------------------------------------------------------- build

def plugin_root():
    return os.path.dirname(os.path.abspath(__file__))


def _import(dotted):
    module = __import__(dotted)
    for part in dotted.split(".")[1:]:
        module = getattr(module, part)
    return module


def _build_section(sec):
    """One frameLayout with the tool's controls inside.

    A tool whose build fails gets a section holding the error text instead
    of taking the whole panel down: the other five still have to work.
    """
    cmds.frameLayout(
        sec.frame, label=sec.label, collapsable=True,
        collapse=collapsed(sec.key), marginWidth=4, marginHeight=4,
        collapseCommand=lambda *_a, k=sec.key: remember(k, True),
        expandCommand=lambda *_a, k=sec.key: remember(k, False))
    cmds.columnLayout(adjustableColumn=True)
    try:
        getattr(_import(sec.module), sec.builder)()
    except Exception:                                        # noqa: BLE001
        text = traceback.format_exc().strip().splitlines()[-1]
        cmds.text(label="{0} could not be built: {1}".format(sec.label,
                                                             text),
                  align="left", wordWrap=True)
        print(traceback.format_exc())
    cmds.setParent("..")
    cmds.setParent("..")
    return sec.frame


def build():
    """The uiScript body: the accordion inside the workspaceControl."""
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.setParent(CONTROL)
    cmds.scrollLayout(SCROLL, childResizable=True)
    cmds.columnLayout(COLUMN, adjustableColumn=True, rowSpacing=ROW_SPACING)
    for sec in SECTIONS:
        _build_section(sec)
    cmds.setParent("..")
    cmds.setParent("..")
    return CONTROL


# -------------------------------------------------------------------- show

def is_open():
    return bool(cmds.workspaceControl(CONTROL, exists=True))


def _close_legacy_windows():
    for name in LEGACY_WINDOWS:
        if cmds.window(name, exists=True):
            cmds.deleteUI(name)


def show(key=None):
    """Open the hub (or raise it) and, given a section key, expand that
    section. The shelf button and every tool's `show_window`."""
    _close_legacy_windows()
    if is_open():
        cmds.workspaceControl(CONTROL, edit=True, restore=True)
    else:
        cmds.workspaceControl(
            CONTROL, label=LABEL, retain=False, floating=True,
            initialWidth=INITIAL_WIDTH, initialHeight=INITIAL_HEIGHT,
            uiScript=uiscript(plugin_root()))
    if key:
        expand(key)
    return CONTROL


def expand(key):
    """Un-collapse section `key`, remember it open, scroll it into view."""
    sec = section(key)
    if sec is None:
        raise KeyError("no section '{0}'".format(key))
    if cmds.frameLayout(sec.frame, exists=True):
        cmds.frameLayout(sec.frame, edit=True, collapse=False)
    remember(key, False)
    #  The heights are real only after Maya lays the column out, which
    #  happens once this command returns - hence deferred.
    cmds.evalDeferred(lambda: scroll_to(key), lowestPriority=True)
    return sec.frame


def scroll_to(key):
    """Scroll the column so section `key` starts at the top. Best effort:
    a control that is not there any more just skips it."""
    sec = section(key)
    try:
        if not cmds.scrollLayout(SCROLL, exists=True):
            return None
        frames = [s.frame for s in SECTIONS]
        heights = [cmds.control(f, query=True, height=True) or 0
                   for f in frames]
        offset = scroll_offset(heights, frames.index(sec.frame), ROW_SPACING)
        cmds.scrollLayout(SCROLL, edit=True, scrollByPixel=("up", 1000000))
        if offset:
            cmds.scrollLayout(SCROLL, edit=True,
                              scrollByPixel=("down", offset))
        return offset
    except Exception:                                        # noqa: BLE001
        return None


if __name__ == "__main__":
    show()
