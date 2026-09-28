"""maya_hub - the SkeldarAnim window: one dockable panel, every tool a section.

The animator's ask (2026-09-17): «объединим наши скрипты в одно окошко,
которое можно будет куда-то прикрепить или открепить; каждый раздел -
вкладка с возможностью закрыть и раскрыть». So: one `workspaceControl`
(dock it to any edge, tab it into any dock, tear it off, Maya remembers
where) holding a scrollable column of collapsible sections, several open at
once, the collapsed set remembered per section in an optionVar.

And its look (2026-09-28): «нарисовать кастомный красивый интерфейс ... как
сделать расположение кнопок более красивым». Where Qt is there the hub is
SKINNED (`maya_hubqt`, `maya_hubstyle`): a header (the hotkey map's switch,
the installed build's chip, a menu), a strip of icons jumping to a section,
and the sections as cards in three groups - Scene, Animation, Look. Hotkeys
and Update are the header there, not cards. Without Qt, or when the
animator asks for it (the menu's Classic look), the CLASSIC hub is built:
the frameLayout accordion of 2026-09-17, every section in it.

    import maya_hub; maya_hub.show()            # the SkeldarAnim shelf button
    maya_hub.show("colour")                      # what Colour's button does

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
       docs/superpowers/specs/2026-09-28-hub-skin-design.md
"""

import collections
import os
import traceback

import maya.cmds as cmds

import maya_hubstyle as hubstyle

CONTROL = "skeldarAnimHub"
LABEL = "SkeldarAnim"
SCROLL = "skeldarAnimHubScroll"
COLUMN = "skeldarAnimHubColumn"
OPTIONVAR = "skeldarAnimHub_collapsed_{0}"
CLASSIC_VAR = "skeldarAnimHub_classic"     # 1: the classic hub even with Qt
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
# Characters header. The settings group is the skin's header.
SECTIONS = (
    Section("characters", "Characters", "maya_scenesetup.window",
            "build_characters_panel", "skeldarHubFrameCharacters",
            "scene", "user"),
    Section("weapons", "Weapons", "maya_scenesetup.window",
            "build_weapons_panel", "skeldarHubFrameWeapons",
            "scene", "sword"),
    Section("connections", "Connections", "maya_scenesetup.connections",
            "build_panel", "skeldarHubFrameConnections",
            "scene", "hand-grab"),
    Section("uebridge", "UE Bridge", "maya_uebridge.window",
            "build_panel", "skeldarHubFrameUebridge",
            "animation", "transfer-in"),
    Section("retarget", "Retarget", "maya_rig_retarget",
            "build_panel", "skeldarHubFrameRetarget",
            "animation", "arrows-exchange"),
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

HEADER_GROUP = "settings"       # in the skin these are the header, not cards

_BY_KEY = dict((s.key, s) for s in SECTIONS)


# ------------------------------------------------------------------- pure

def section(key):
    """The Section for `key`, or None."""
    return _BY_KEY.get(key)


def card_sections():
    """The sections the skin draws as cards, in order."""
    return [s for s in SECTIONS if s.group != HEADER_GROUP]


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

#  The skin standing in the control, built by this module object (a
#  maya_hubqt.Skin), or None while the hub is classic.
_SKIN = None


def _build_classic():
    cmds.scrollLayout(SCROLL, childResizable=True)
    cmds.columnLayout(COLUMN, adjustableColumn=True, rowSpacing=ROW_SPACING)
    if _qt_available():
        cmds.button(NEW_LOOK_BUTTON, label="Switch to the new look",
                    height=26,
                    annotation="The SkeldarAnim hub in its own skin: cards, "
                               "a jump strip, the hotkeys and the update in "
                               "the header",
                    command=lambda *_a: set_classic(False))
    for sec in SECTIONS:
        _build_section(sec)
    cmds.setParent("..")
    cmds.setParent("..")
    hubstyle.take_marks()               # marks mean nothing here


def _callbacks():
    return {
        "hotkeys": _press_hotkeys,
        "version": _press_update,
        "check_update": _press_update,
        "hotkey_editor": _press_hotkey_editor,
        "classic": lambda: set_classic(True),
        "jump": expand,
        "toggled": remember,
    }


def _dress_header(skin):
    """The chip = the installed build; the hotkey switch = the map's state."""
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


def _build_skin():
    """The skinned hub. Deleted whole if any of it fails, then re-raised."""
    qt = _hubqt()
    scale = _scale()
    skin = qt.Skin(qt.host_widget(CONTROL), scale=scale,
                   callbacks=_callbacks())
    hubstyle.set_skinning(True)
    try:
        for sec in card_sections():
            skin.add_jump(sec.key, sec.label, sec.icon,
                          hubstyle.group(sec.group).colour)
        current = None
        for sec in card_sections():
            grp = hubstyle.group(sec.group)
            if sec.group != current:
                skin.add_group(grp.key, grp.label)
                current = sec.group
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
    survives, which deleting and recreating the control would not."""
    global _SKIN
    if _SKIN is not None:
        _SKIN.destroy()
        _SKIN = None
    if cmds.scrollLayout(SCROLL, exists=True):
        cmds.deleteUI(SCROLL)
    return build()


def set_classic(on):
    """Switch between the skin and the classic hub. Deferred: the press
    comes from inside the hub the rebuild deletes."""
    cmds.optionVar(intValue=(CLASSIC_VAR, int(bool(on))))
    cmds.evalDeferred(rebuild, lowestPriority=True)
    return bool(on)


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
    import maya_update
    return maya_update._press()


def _press_hotkey_editor():
    import maya_hotkeys
    return maya_hotkeys._maya_mel("HotkeyPreferencesWindow")


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


def expand(key):
    """Un-collapse section `key`, remember it open, scroll it into view. In
    the skin a header section (Hotkeys, Update) has no card: nothing to do."""
    sec = section(key)
    if sec is None:
        raise KeyError("no section '{0}'".format(key))
    if is_skinned():
        card = _SKIN.cards.get(key)
        if card is None:
            return None
        card.set_collapsed(False)
        _SKIN.set_active(key)
        remember(key, False)
        cmds.evalDeferred(lambda: scroll_to(key), lowestPriority=True)
        return card
    if cmds.frameLayout(sec.frame, exists=True):
        cmds.frameLayout(sec.frame, edit=True, collapse=False)
    remember(key, False)
    #  The heights are real only after Maya lays the column out, which
    #  happens once this command returns - hence deferred.
    cmds.evalDeferred(lambda: scroll_to(key), lowestPriority=True)
    return sec.frame


def scroll_to(key):
    """Scroll so section `key` starts at the top. Best effort: a control
    that is not there any more just skips it."""
    sec = section(key)
    try:
        if is_skinned():
            return _SKIN.scroll_to(key)
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
