"""maya_hub - the SkeldarAnim window: one dockable panel, every tool a section.

The animator's ask (2026-09-17): «объединим наши скрипты в одно окошко,
которое можно будет куда-то прикрепить или открепить; каждый раздел -
вкладка с возможностью закрыть и раскрыть». So: one `workspaceControl`
(dock it to any edge, tab it into any dock, tear it off, Maya remembers
where) holding a scrollable column of collapsible sections, several open at
once, the collapsed set remembered per section in an optionVar.

And its look (2026-09-28): «нарисовать кастомный красивый интерфейс ... как
сделать расположение кнопок более красивым». Where Qt is there the hub is
SKINNED (`maya_hubqt`, `maya_hubstyle`): one header row (the mark, an icon
per section jumping to it - the update's carries the installed build as its
tooltip -, the hotkey map's switch, a menu), and the sections as cards in
groups - Scene, Animation, Look, Settings - each group a colour (a stripe),
never a label (2026-10-08, the compact hub). Hotkeys are the header there,
not a card. Without Qt, or when the
animator asks for it (the menu's Classic look), the CLASSIC hub is built:
the frameLayout accordion of 2026-09-17, every section in it.

    import maya_hub; maya_hub.show()            # the SkeldarAnim shelf button
    maya_hub.show("colour")                      # what Colour's button does

And its second home (2026-10-08, the animator: «когда я подношу мышку к
левому краю экрана то появляется наша полка когда убираю то полка
скрывается»): ⋮ -> Edge panel (off by default, remembered) builds the skin
into `maya_hubedge`'s panel at the screen's left edge instead of the dock -
the dock's control is deleted, `show(key)` slides the panel out on that card
and holds it, `start()` is the startup plug-in's call (the panel waiting,
hidden), and a card's status while the panel is hidden is also Maya's
viewport message. Only the skin lives there: Classic look takes the hub back
to the dock.

Every tool builds its controls with `build_panel()` into whatever layout is
current; this module supplies the layout. The tools are imported lazily
inside `build()` and import this module lazily inside their `show_window`,
so nothing here imports a tool at module level and there is no cycle.

Two facts the shape rests on:

- A `cmds` control has ONE name per Maya session. `mayaSceneSetupStatus`
  can exist in the hub or in a window of its own, not both - which is why
  every `show_window()` opens the hub on its section and the old
  standalone windows are gone rather than kept beside it.
- Maya replays a docked workspaceControl's `uiScript` at startup, before
  any shelf button has put our folder on `sys.path`. So the script carries
  the bootstrap with the plugin folder baked in (`uiscript`), read from
  this file's own location - the hotkey runTimeCommands' pattern.

Specs: docs/superpowers/specs/2026-09-17-skeldar-hub-design.md,
       docs/superpowers/specs/2026-09-28-hub-skin-design.md,
       docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md
"""

import collections
import os
import traceback

import maya.cmds as cmds

import maya_edgerules as edgerules
import maya_hubstyle as hubstyle

CONTROL = "skeldarAnimHub"
LABEL = "SkeldarAnim"
SCROLL = "skeldarAnimHubScroll"
COLUMN = "skeldarAnimHubColumn"
OPTIONVAR = "skeldarAnimHub_collapsed_{0}"
CLASSIC_VAR = "skeldarAnimHub_classic"     # 1: the classic hub even with Qt
EDGE_VAR = edgerules.EDGE_VAR              # 1: the hub in the edge panel
NEW_LOOK_BUTTON = "skeldarAnimHubNewLook"

INITIAL_WIDTH = 500
INITIAL_HEIGHT = 900
ROW_SPACING = 4                 # the classic column's gap between sections

# Windows earlier builds opened on their own. Deleted on every show, or a
# panel left up from the previous build stays wired to dead code beside
# the hub (the checkouts popup taught this in August).
LEGACY_WINDOWS = ("ueAnimBridgeWindow", "ueBridgeCheckouts",
                  "mayaSceneSetupWindow", "mayaWeaponsWindow",
                  "skeldarVpStudioWin", "skeldarColourWin")

Section = collections.namedtuple("Section",
                                 "key label module builder frame group icon")

# The order of the hub. `module.builder()` builds the tool's controls into
# the current parent; `frame` is the classic frameLayout's name; `group`
# and `icon` are the skin's (maya_hubstyle.GROUPS, maya_hubicons.ICONS).
# Scene Setup is two sections of one module (2026-09-17); Weapons must
# follow Characters, because the weapons builder's refresh writes the
# Characters header. UE Bridge on top, where it always was (2026-09-28,
# the evening: «UE bridge давай передвинем наверх как он и был») - and a
# group stays together, so Animation is the first group.
#
#  2026-10-01 («UE bridge и character ... их нужно объеденить в одно окно»):
#  the UE Bridge is part of the Characters card, and that card is the first
#  - the Scene group above Animation now (asked: «Characters самой первой,
#  Scene выше»). Weapons still follows Characters. The same evening it is
#  called Animation Setup («Раздел Character Заменим на Animationsetup»); its
#  key stays "characters" - the collapse memory, the aliases, every opener.
SECTIONS = (
    Section("characters", "Animation Setup", "maya_scenesetup.window",
            "build_characters_panel", "skeldarHubFrameCharacters",
            "scene", "user"),
    #  2026-10-01, the evening («объеденим вкладки weapon и армор в одну
    #  inventory»): Weapons and Armor are one card, Inventory - its key stays
    #  "weapons" (the collapse memory, every opener), "armor" an alias.
    Section("weapons", "Inventory", "maya_scenesetup.window",
            "build_weapons_panel", "skeldarHubFrameWeapons",
            "scene", "backpack"),
    Section("connections", "Connections", "maya_scenesetup.connections",
            "build_panel", "skeldarHubFrameConnections",
            "scene", "hand-grab"),
    #  2026-09-30: scenes and FBX between colleagues, over ntfy.sh + litterbox.
    Section("shared", "Shared", "maya_share",
            "build_panel", "skeldarHubFrameShared",
            "scene", "send"),
    Section("retarget", "Retarget", "maya_rig_retarget",
            "build_panel", "skeldarHubFrameRetarget",
            "animation", "arrows-exchange"),
    #  2026-09-30: Maya's own Graph Editor over the viewport, see-through.
    Section("graphoverlay", "Graph Overlay", "maya_graphoverlay.mode",
            "build_panel", "skeldarHubFrameGraphOverlay",
            "animation", "chart-line"),
    #  2026-10-01: the centre of mass - a live point, its trail, the CoM tool.
    Section("com", "Center of Mass", "maya_com.panel",
            "build_panel", "skeldarHubFrameCom",
            "animation", "target"),
    #  2026-10-02: the Pose Library - cards of a character's bones. The window
    #  is its own workspaceControl; the card is one line and Open Pose Library.
    Section("poses", "Pose Library", "maya_poselib.window",
            "build_panel", "skeldarHubFramePoses",
            "animation", "books"),
    Section("studio", "Studio", "maya_vpstudio",
            "build_panel", "skeldarHubFrameStudio",
            "look", "bulb"),
    Section("colour", "Colour", "maya_colour",
            "build_panel", "skeldarHubFrameColour",
            "look", "palette"),
    Section("hotkeys", "Hotkeys", "maya_hotkeys",
            "build_panel", "skeldarHubFrameHotkeys",
            "settings", "keyboard"),
    #  2026-09-28: Check update, the latest build from GitHub's releases.
    Section("update", "Update", "maya_update",
            "build_panel", "skeldarHubFrameUpdate",
            "settings", "refresh"),
)

#  In the skin these are the header's, not cards: the hotkey map is the
#  keyboard button. Update was the header's chip alone for an afternoon and
#  is a card again (2026-09-28, «раздел с обновлением давай вернём»); the
#  chip stays and opens it.
HEADER_ONLY = ("hotkeys",)

_BY_KEY = dict((s.key, s) for s in SECTIONS)

#  Keys of sections that became part of another: `show("uebridge")` (the
#  hotkey row, a flagged shelf button, an older uiScript or verify run)
#  opens the card the section lives in now.
ALIASES = {"uebridge": "characters", "armor": "weapons"}


# ------------------------------------------------------------------- pure

def section(key):
    """The Section for `key` (or for the card an alias names), or None."""
    return _BY_KEY.get(ALIASES.get(key, key))


def card_sections():
    """The sections the skin draws as cards, in order."""
    return [s for s in SECTIONS if s.key not in HEADER_ONLY]


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


def classic_asked():
    """The animator chose the classic hub (the skin's menu, Classic look)."""
    if cmds.optionVar(exists=CLASSIC_VAR):
        return bool(cmds.optionVar(query=CLASSIC_VAR))
    return False


def edge_on():
    """The hub lives in the edge panel (⋮ -> Edge panel; off by default, so
    a colleague keeps the dock until they turn it on) - only with the skin,
    and not after the skin failed there in this module object's session
    (`_EDGE_FAILED`)."""
    if _EDGE_FAILED or classic_asked() or not _qt_available():
        return False
    if cmds.optionVar(exists=EDGE_VAR):
        return bool(cmds.optionVar(query=EDGE_VAR))
    return False


# ------------------------------------------------------------------- build

def plugin_root():
    return os.path.dirname(os.path.abspath(__file__))


def _import(dotted):
    module = __import__(dotted)
    for part in dotted.split(".")[1:]:
        module = getattr(module, part)
    return module


def _hubqt():
    """The Qt layer, imported only when a hub is built (a seam for tests)."""
    import maya_hubqt
    return maya_hubqt


def _hubedge():
    """The edge panel's Qt (maya_hubedge), imported only when the edge panel
    is asked about (a seam for tests)."""
    import maya_hubedge
    return maya_hubedge


def _qt_available():
    try:
        return bool(_hubqt().available())
    except Exception:                                        # noqa: BLE001
        return False


def skinned():
    """Whether `build()` would build the skin."""
    return not classic_asked() and _qt_available()


def _scale():
    """The display factor Maya scales its UI by (1.5 at 150 %)."""
    try:
        return float(cmds.mayaDpiSetting(query=True, realScaleValue=True)
                     or 1.0)
    except Exception:                                        # noqa: BLE001
        return 1.0


def _run_builder(sec):
    """Run section `sec`'s builder into the current parent. A tool whose
    build fails gets a line with the error instead of taking the whole panel
    down: the other sections still have to work."""
    try:
        getattr(_import(sec.module), sec.builder)()
    except Exception:                                        # noqa: BLE001
        text = traceback.format_exc().strip().splitlines()[-1]
        cmds.text(label="{0} could not be built: {1}".format(sec.label,
                                                             text),
                  align="left", wordWrap=True)
        print(traceback.format_exc())


def _build_section(sec):
    """One classic frameLayout with the tool's controls inside."""
    cmds.frameLayout(
        sec.frame, label=sec.label, collapsable=True,
        collapse=collapsed(sec.key), marginWidth=4, marginHeight=4,
        collapseCommand=lambda *_a, k=sec.key: remember(k, True),
        expandCommand=lambda *_a, k=sec.key: remember(k, False))
    cmds.columnLayout(adjustableColumn=True)
    _run_builder(sec)
    cmds.setParent("..")
    cmds.setParent("..")
    return sec.frame


#  Did THIS module object build the accordion standing in the control?  An
#  update purges the plugin's modules (install.purge_modules) while the hub
#  stays open, and a plain restore then kept showing the old build: the old
#  character dropdown, missing the Creep row the update had just added
#  (2026-09-24, «НЕ вижу хантера в списке персонажей»), and callbacks into
#  module objects nothing imports any more. Maya's startup replay of the
#  uiScript runs build() in the module object of that session, so a docked
#  hub counts as ours from the start.
_BUILT_HERE = False

#  The skin standing in the control - or in the edge panel's slot - built by
#  this module object (a maya_hubqt.Skin), or None while the hub is classic.
_SKIN = None

#  The skin failed to build in the edge panel (2026-10-08): the hub stays in
#  the dock for the rest of this module object's session, or the uiScript,
#  start() and show() would hand it back and forth to each other. ⋮ -> Edge
#  panel (set_edge(True)) tries again; an install brings a fresh module.
_EDGE_FAILED = False


def _build_classic():
    cmds.scrollLayout(SCROLL, childResizable=True)
    cmds.columnLayout(COLUMN, adjustableColumn=True, rowSpacing=ROW_SPACING)
    if _qt_available():
        cmds.button(NEW_LOOK_BUTTON, label="Switch to the new look",
                    height=26,
                    annotation="The SkeldarAnim hub in its own skin: cards, "
                               "a jump icon per section, the hotkeys and "
                               "the update in the header",
                    command=lambda *_a: set_classic(False))
    for sec in SECTIONS:
        _build_section(sec)
    cmds.setParent("..")
    cmds.setParent("..")
    hubstyle.take_marks()               # marks mean nothing here


def _callbacks():
    #  "version" is gone (2026-10-08): the compact header has no chip to
    #  press - the update jump focuses its card, ⋮ -> Check update checks.
    return {
        "hotkeys": _press_hotkeys,
        "check_update": _press_update,
        "hotkey_editor": _press_hotkey_editor,
        "classic": lambda: set_classic(True),
        "jump": focus,
        "toggled": remember,
        "told": _told,
        "hover": _hover_sound,
        "sounds": set_sounds,
        "animations": set_animations,
        #  the edge panel (2026-10-08): the header's 📌 and ⋮ -> Edge panel
        "pin": _press_pin,
        "edge": set_edge,
    }


def _told(key, text, viewport):
    """A card's status reached the message line (maya_hubqt.Skin._told,
    2026-10-08). While the edge panel is hidden nobody sees that line - an
    import by drag finishing after the panel slid away - so the status's
    first line is also Maya's viewport message for 3 s, unless its writer
    showed one itself (`viewport`: the Retarget button does). Docked, or
    with the panel out, nothing to add."""
    if not text or viewport:
        return None
    current = edge()
    if current is None or current.shown:
        return None
    try:
        cmds.inViewMessage(assistMessage=text.splitlines()[0],
                           position="topCenter", fade=True,
                           fadeStayTime=3000)
    except Exception:                                        # noqa: BLE001
        pass
    return text


def _dress_header(skin):
    """The update jump's tooltip = the installed build; the hotkey switch =
    the map's state."""
    try:
        import maya_update
        record = maya_update.read_record(maya_update.installed_dir())
        short = (record.get("short") or (record.get("commit") or "")[:7]
                 or ("source" if record.get("source") else "?"))
        skin.set_version(short, "Installed: {0} - press to check for an "
                         "update".format(maya_update.describe(
                             record, subject=False)))
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
        skin.set_version("?", "Check update")
    try:
        import maya_hotkeys
        skin.paint_hotkeys(maya_hotkeys.is_active())
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    _dress_sounds(skin)
    _dress_animations(skin)
    _dress_edge(skin)


def _dress_edge(skin):
    """The menu's Edge panel row = the mode (2026-10-08). The 📌 shows once
    the skin stands in the edge panel (`Skin.set_edge_mode`, _ensure_edge)."""
    try:
        skin.paint_edge(edge_on())
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def _dress_sounds(skin):
    """The menu's Interface sounds row = the switch (off by default); while
    it is on, the hover sound loaded now, so the first hover is not the one
    waiting for the file (0.44 s for the pool's three effects, measured
    2026-10-01). Off, no audio is opened at all."""
    try:
        import maya_hubsound
        on = maya_hubsound.enabled()
        skin.paint_sounds(on)
        if on:
            maya_hubsound.preload("hover")
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def _dress_animations(skin):
    """The menu's Interface animations row = the switch (2026-10-01: the
    cards slide, a jump glides; maya_hubmotion's optionVar, on by
    default)."""
    try:
        import maya_hubmotion
        skin.paint_animations(maya_hubmotion.enabled())
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def _build_skin(host=None):
    """The skinned hub - into the workspaceControl, or into `host` (the edge
    panel's slot, 2026-10-08). Deleted whole if any of it fails, then
    re-raised."""
    qt = _hubqt()
    scale = _scale()
    #  a skin an older module object built (an install purges the modules,
    #  not the widgets) goes first, or its controls answer to our names
    if host is None:
        qt.destroy_roots(CONTROL)
        host = qt.host_widget(CONTROL)
    else:
        qt.destroy_roots_in(host)
    skin = qt.Skin(host, scale=scale, callbacks=_callbacks())
    hubstyle.set_skinning(True)
    try:
        for sec in card_sections():
            skin.add_jump(sec.key, sec.label, sec.icon,
                          hubstyle.group(sec.group).colour)
        #  No group labels (2026-10-08, the compact hub): a card's group is
        #  the colour of its stripe and of its jump; the cards stand in their
        #  groups' order all the same (Skin.add_group stays an API).
        for sec in card_sections():
            grp = hubstyle.group(sec.group)
            card = skin.add_card(sec.key, sec.label, sec.icon, grp.colour,
                                 grp.chip, collapsed=collapsed(sec.key))
            cmds.setParent(card.body_path())
            _run_builder(sec)
            qt.apply_marks(hubstyle.take_marks(), card, scale)
        _dress_header(skin)
        skin.finish(hubstyle.stylesheet(scale, arrow=_arrow(qt)))
    except Exception:
        hubstyle.take_marks()
        skin.destroy()
        raise
    finally:
        hubstyle.set_skinning(False)
    return skin


def _arrow(qt):
    """The dropdowns' arrow as a file, or None (the style's own arrow)."""
    try:
        return qt.icon_file("chevron-down", hubstyle.TOKENS["muted"])
    except Exception:                                        # noqa: BLE001
        return None


def build():
    """The uiScript body: the hub inside the workspaceControl."""
    global _BUILT_HERE, _SKIN
    if edge_on():
        #  A docked control Maya restored from an older workspace while the
        #  hub lives at the edge now (2026-10-08): nothing is built in it -
        #  deferred, the control goes and the edge panel waits. Before
        #  anything touches _SKIN: it may be the edge panel's, standing.
        cmds.evalDeferred(_drop_dock_for_edge, lowestPriority=True)
        _BUILT_HERE = True
        return CONTROL
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.setParent(CONTROL)
    hubstyle.take_marks()
    _SKIN = None
    if skinned():
        try:
            _SKIN = _build_skin()
        except Exception:                                    # noqa: BLE001
            print("SkeldarAnim: the hub's skin failed, building the "
                  "classic hub instead")
            print(traceback.format_exc())
            _SKIN = None
            if cmds.workspaceControl(CONTROL, exists=True):
                cmds.setParent(CONTROL)
    if _SKIN is None:
        _build_classic()
    _BUILT_HERE = True
    return CONTROL


def is_skinned():
    """A skin built by this module object stands."""
    return _SKIN is not None and _SKIN.alive()


def rebuild():
    """The hub rebuilt inside the standing control -- where it is docked
    survives, which deleting and recreating the control would not.

    In edge mode (2026-10-08) the edge panel is rebuilt instead: a new Edge
    (an install brings a new maya_hubedge; the width lives in its optionVar)
    holding a new skin (`_rebuild_edge`). An edge panel standing while the
    hub lives in the dock (⋮ -> Classic look pressed in it) goes, and the
    dock opens. Callers defer it: it deletes what may hold the press."""
    global _SKIN
    if edge_on():
        return _rebuild_edge()
    if edge() is not None:
        stop()
        if not cmds.workspaceControl(CONTROL, exists=True):
            return show()
    if _SKIN is not None:
        _SKIN.destroy()
        _SKIN = None
    _delete_classic()
    return build()


def _delete_classic():
    """The classic accordion deleted, its collapse memory kept."""
    if cmds.scrollLayout(SCROLL, exists=True):
        #  Deleting the classic frames runs their collapseCommand (measured
        #  2026-09-28: every section came back remembered collapsed after a
        #  classic hub was deleted), so the memory is put back after.
        memory = dict((s.key, collapsed(s.key)) for s in SECTIONS)
        cmds.deleteUI(SCROLL)
        for key, value in memory.items():
            remember(key, value)


def set_classic(on):
    """Switch between the skin and the classic hub. Deferred: the press
    comes from inside the hub the rebuild deletes."""
    cmds.optionVar(intValue=(CLASSIC_VAR, int(bool(on))))
    cmds.evalDeferred(rebuild, lowestPriority=True)
    return bool(on)


# --------------------------------------------------------------- the edge

#  The edge panel (2026-10-08): maya_hubedge's windows at the screen's left
#  edge, the skin in their slot. Its Edge object lives on `sys` (an install
#  purges our modules; maya_hubedge.state()), found by `edge()`.
#
#  Edge.destroy() deletes its windows NOW, and with them the slot and every
#  control of ours in it. So nothing here destroys the edge panel on a path
#  that can start from a control inside it without deferring first (the
#  ⋮ switch, Classic look, a show() meeting a panel an older module built),
#  and the skin is always destroyed BEFORE its Edge.

def edge():
    """The Edge standing (maya_hubedge.state()), alive, or None."""
    try:
        current = _hubedge().state().get("edge")
    except Exception:                                        # noqa: BLE001
        return None
    return current if current is not None and current.alive() else None


def _skin_at(current):
    """This module object's skin stands in Edge `current`'s slot."""
    return is_skinned() and getattr(_SKIN, "host", None) is current.slot


def _edge_width():
    """The panel's logical width, as the animator's grip left it."""
    if cmds.optionVar(exists=edgerules.WIDTH_VAR):
        return cmds.optionVar(query=edgerules.WIDTH_VAR)
    return edgerules.WIDTH


def _save_edge_width(width):
    """The grip released (Edge.on_width): remembered for the next panel."""
    cmds.optionVar(intValue=(edgerules.WIDTH_VAR, int(width)))


def _ensure_edge():
    """The edge panel built (hidden) with the skin in it; the Edge. One
    standing with this module object's skin in it is the answer as it is.

    Any other goes first, found by name (an older module object's
    included); then a new Edge, registered on maya_hubedge.state(), and the
    skin in its slot. A skin that fails to build there takes its Edge with
    it, keeps the hub in the dock for this session (`_EDGE_FAILED`) and is
    re-raised."""
    global _SKIN, _BUILT_HERE, _EDGE_FAILED
    current = edge()
    if current is not None and _skin_at(current):
        return current
    he = _hubedge()
    if _SKIN is not None:
        #  the skin first: the windows destroy_all deletes may hold its root
        _SKIN.destroy()
        _SKIN = None
    he.destroy_all()
    current = he.Edge(scale=_scale(), width=_edge_width(),
                      on_width=_save_edge_width)
    he.state()["edge"] = current
    try:
        _SKIN = _build_skin(host=current.slot)
        _SKIN.set_edge_mode(True)
    except Exception:
        print("SkeldarAnim: the hub's skin failed in the edge panel - the "
              "hub stays docked for this session")
        print(traceback.format_exc())
        if _SKIN is not None:
            _SKIN.destroy()
            _SKIN = None
        current.destroy()
        he.state()["edge"] = None
        _EDGE_FAILED = True
        raise
    _BUILT_HERE = True
    return current


def start():
    """The startup plug-in's call: in edge mode the panel waits at the edge,
    hidden; docked, nothing. Never raises (a skin failing there is printed
    by `_ensure_edge`; the shelf button then opens the dock). The Edge, or
    None."""
    if not edge_on():
        return None
    try:
        return _ensure_edge()
    except Exception:                                        # noqa: BLE001
        return None


def stop():
    """The plug-in unloaded (and every switch away from the edge): the edge
    panel goes - the skin standing in it first. True when one stood."""
    global _SKIN
    current = edge()
    if current is None:
        return False
    if _SKIN is not None and getattr(_SKIN, "host", None) is current.slot:
        _SKIN.destroy()
        _SKIN = None
    current.destroy()
    _hubedge().state()["edge"] = None
    return True


def set_edge(on):
    """⋮ -> Edge panel: switched, remembered. Deferred: the press comes from
    inside the hub the switch rebuilds elsewhere. Refused (False) without
    the skin - the classic hub does not live at the edge (the spec's "not
    built"). Turning it on tries again after a skin that failed there."""
    global _EDGE_FAILED
    if on and (classic_asked() or not _qt_available()):
        #  ASCII: printed, and a cp1252 stdout cannot encode the menu's mark
        message = "The edge panel needs the new look (Classic look is on)"
        print("SkeldarAnim: " + message)
        say(message)
        return False
    if on:
        _EDGE_FAILED = False
    cmds.optionVar(intValue=(EDGE_VAR, int(bool(on))))
    cmds.evalDeferred(lambda: _switch_edge(bool(on)), lowestPriority=True)
    return bool(on)


def _switch_edge(on):
    """The deferred half of `set_edge`. The last press wins: a switch whose
    mode was turned back before it ran does nothing."""
    if on:
        if not edge_on():
            return None
        #  2026-10-08 (the spec): the docked hub closes, the panel is built
        #  and slides out once, so the animator sees where the hub went
        _drop_dock()
        stop()
        try:
            current = _ensure_edge()
        except Exception:                                    # noqa: BLE001
            return show()                   # the dock: edge_on() is False
        current.reveal(hold=True)
        return current
    if edge_on():
        return None
    #  the edge panel goes and the dock opens as `show()` does - not where
    #  it was docked: that control was deleted while the panel stood
    stop()
    return show()


def _drop_dock():
    """The docked hub goes: its skin (or its classic accordion, the
    collapse memory kept) and its control."""
    global _SKIN
    if _SKIN is not None:
        _SKIN.destroy()
        _SKIN = None
    _delete_classic()
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.deleteUI(CONTROL)


def _drop_dock_for_edge():
    """Deferred from `build()`: the control Maya restored goes and the edge
    panel waits. The edge first - a skin failing there leaves the hub in the
    control Maya restored, built now. With the mode turned off meanwhile the
    control gets the hub `build()` did not put in it."""
    if not edge_on():
        if cmds.workspaceControl(CONTROL, exists=True):
            return rebuild()
        return None
    try:
        _ensure_edge()
    except Exception:                                        # noqa: BLE001
        if cmds.workspaceControl(CONTROL, exists=True):
            return rebuild()
        return None
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.deleteUI(CONTROL)
    return CONTROL


def _rebuild_edge():
    """`rebuild()` in edge mode: the edge panel (and a dock the hub leaves,
    the classic one after ⋮ -> Switch to the new look) gone, a new one
    built. One that was out comes out again - the animator was working in
    it (an install from the Update card) - and the pin, per session, stays;
    the hub arriving from the dock slides out as a switch does."""
    current = edge()
    shown = bool(current is not None and current.shown)
    pinned = bool(current is not None and getattr(current, "pinned", False))
    from_dock = bool(cmds.workspaceControl(CONTROL, exists=True))
    if from_dock:
        _drop_dock()
    stop()
    try:
        current = _ensure_edge()
    except Exception:                                        # noqa: BLE001
        return show()                       # the dock: edge_on() is False
    if pinned:
        current.set_pinned(True)
        _SKIN.paint_pin(True)
    if shown or from_dock:
        current.reveal(hold=True)
    return CONTROL


def _press_pin(on):
    """The header's 📌: a pinned panel stays out (maya_hubedge.Edge)."""
    current = edge()
    if current is not None:
        current.set_pinned(on)
    return bool(on)


def _show_edge(key):
    """`show(key)` in edge mode: the panel out on section `key`, held until
    the cursor has been in it and left, or a press lands outside it. A
    panel an older module object built (an install purged our modules and
    nothing rebuilt it yet) is rebuilt first, DEFERRED - the call may come
    from a control inside it. The Edge, or None when the skin failed there
    (the caller opens the dock)."""
    current = edge()
    if current is not None and not _skin_at(current):
        cmds.evalDeferred(lambda: _rebuild_then_show(key),
                          lowestPriority=True)
        return current
    try:
        current = _ensure_edge()
    except Exception:                                        # noqa: BLE001
        return None
    current.reveal(hold=True)
    if key:
        expand(key)
    return current


def _rebuild_then_show(key):
    rebuild()
    return show(key)


def _leave_edge_then_show(key):
    """Deferred from `show()` docked with an edge panel still standing."""
    stop()
    return show(key)


# ------------------------------------------------------------------ header

def say(message, state=None):
    """The skin's message line (quiet while the hub is classic)."""
    if is_skinned():
        _SKIN.say(message, state=state)
    return message


def paint_hotkeys(active):
    if is_skinned():
        _SKIN.paint_hotkeys(active)
    return bool(active)


def _press_hotkeys():
    import maya_hotkeys
    try:
        message = maya_hotkeys.toggle()
    finally:
        paint_hotkeys(maya_hotkeys.is_active())
    if message:
        say(message)
    return message


def _press_update():
    """The menu's Check update (the header's version chip is gone since
    2026-10-08): the Update card opened (its status line is where the answer
    goes), then the check."""
    import maya_update
    if is_skinned() and "update" in _SKIN.cards:
        expand("update")
    return maya_update._press()


def chip_state(state):
    """Colour the header's update jump ("ok", "new", "" its group's colour);
    2026-10-08: it was the version chip's colour before the compact header."""
    if is_skinned():
        _SKIN.set_state(state)
    return state


def _hover_sound():
    """The mouse entered a button of the skin (maya_hubqt.sounding)."""
    import maya_hubsound
    return maya_hubsound.play("hover")


def set_sounds(on):
    """The menu's Interface sounds: switched, remembered, the row painted."""
    import maya_hubsound
    on = maya_hubsound.set_enabled(on)
    if is_skinned():
        _SKIN.paint_sounds(on)
    return on


def set_animations(on):
    """The menu's Interface animations: switched, remembered, the skin
    told (off = every card and every jump instant, as before)."""
    import maya_hubmotion
    on = maya_hubmotion.set_enabled(on)
    if is_skinned():
        _SKIN.paint_animations(on)
    return on


def _press_hotkey_editor():
    import maya_hotkeys
    return maya_hotkeys._maya_mel("HotkeyPreferencesWindow")


# -------------------------------------------------------------------- show

def is_open():
    """The hub stands: docked, or in the edge panel (2026-10-08) - out or
    waiting hidden."""
    return (bool(cmds.workspaceControl(CONTROL, exists=True))
            or edge() is not None)


def _close_legacy_windows():
    for name in LEGACY_WINDOWS:
        if cmds.window(name, exists=True):
            cmds.deleteUI(name)


def show(key=None):
    """Open the hub (or raise it) and, given a section key, expand that
    section. The shelf button and every tool's `show_window`.

    In edge mode (2026-10-08) the edge panel slides out on that section and
    stays until visited (`_show_edge`). Docked with an edge panel still
    standing (a switch on its way), the panel goes first - deferred, the
    call may come from a control inside it - or two skins would answer to
    the controls' names (trap 102's shape)."""
    _close_legacy_windows()
    if edge_on():
        if _show_edge(key) is not None:
            return CONTROL
    elif edge() is not None:
        cmds.evalDeferred(lambda: _leave_edge_then_show(key),
                          lowestPriority=True)
        return CONTROL
    if cmds.workspaceControl(CONTROL, exists=True):
        if not _BUILT_HERE:
            rebuild()
        cmds.workspaceControl(CONTROL, edit=True, restore=True)
    else:
        cmds.workspaceControl(
            CONTROL, label=LABEL, retain=False, floating=True,
            initialWidth=INITIAL_WIDTH, initialHeight=INITIAL_HEIGHT,
            uiScript=uiscript(plugin_root()))
    if key:
        expand(key)
    return CONTROL


def focus(key):
    """A header jump's press: section `key` opened and every other card
    closed (2026-09-28: «при нажатии на верхнюю панель с разделами все другие
    панели должны закрыться и открыться только нужная»), remembered so, lit,
    scrolled to. Outside the skin it is `expand`."""
    key = ALIASES.get(key, key)
    if not is_skinned():
        return expand(key)
    if key not in _SKIN.cards:
        return None
    for other, card in _SKIN.cards.items():
        if other != key:
            card.set_collapsed(True, animate=True)
            remember(other, True)
    return expand(key)


def expand(key):
    """Un-collapse section `key`, remember it open, scroll it into view. In
    the skin a header section (Hotkeys) has no card: nothing to do."""
    key = ALIASES.get(key, key)
    sec = section(key)
    if sec is None:
        raise KeyError("no section '{0}'".format(key))
    if is_skinned():
        card = _SKIN.cards.get(key)
        if card is None:
            return None
        card.set_collapsed(False, animate=True)
        _SKIN.set_active(key)
        remember(key, False)
        cmds.evalDeferred(lambda: scroll_to(key, animate=True),
                          lowestPriority=True)
        return card
    if cmds.frameLayout(sec.frame, exists=True):
        cmds.frameLayout(sec.frame, edit=True, collapse=False)
    remember(key, False)
    #  The heights are real only after Maya lays the column out, which
    #  happens once this command returns - hence deferred.
    cmds.evalDeferred(lambda: scroll_to(key), lowestPriority=True)
    return sec.frame


def scroll_to(key, animate=False):
    """Scroll so section `key` starts at the top -- in the skin gliding when
    `animate` (the animator's move; maya_hubqt.Skin.scroll_to). Best effort:
    a control that is not there any more just skips it."""
    key = ALIASES.get(key, key)
    sec = section(key)
    try:
        if is_skinned():
            return _SKIN.scroll_to(key, animate=animate)
        if not cmds.scrollLayout(SCROLL, exists=True):
            return None
        frames = [s.frame for s in SECTIONS]
        heights = [cmds.control(f, query=True, height=True) or 0
                   for f in frames]
        offset = scroll_offset(heights, frames.index(sec.frame), ROW_SPACING)
        if cmds.control(NEW_LOOK_BUTTON, exists=True):
            offset += ((cmds.control(NEW_LOOK_BUTTON, query=True,
                                     height=True) or 0) + ROW_SPACING)
        cmds.scrollLayout(SCROLL, edit=True, scrollByPixel=("up", 1000000))
        if offset:
            cmds.scrollLayout(SCROLL, edit=True,
                              scrollByPixel=("down", offset))
        return offset
    except Exception:                                        # noqa: BLE001
        return None


if __name__ == "__main__":
    show()
