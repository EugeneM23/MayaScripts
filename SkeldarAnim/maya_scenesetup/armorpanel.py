"""The Armor section of the hub's Inventory card: pick a piece, press Equip.

Since 2026-10-01, the evening («объеденим вкладки weapon и армор в одну inventory. Пускай в ней
будет два раздела weapon и армор ... Пусть все будет конссистентно»), not a card of its own: the
rows (`build_rows` - the «Armor» heading, the tiles, Equip + Unequip) stand under the Weapon
section of the Inventory card, write that card's one status line (`_STATUS`) and its subtitle
(`_BOUND`), and `watch` hangs the pills' SelectionChanged job on that line. A tile also DRAGS onto a
character in a viewport (`maya_armorgrid`, `equip_on`). Spec:
docs/superpowers/specs/2026-10-01-inventory-card-design.md

2026-10-01, the animator: «не будем добавлять его в панель с оружием а сделаем для него отдельную
панель Armor в которой пока будет только техно лимб но позже мы добавим еще разные варианты одежды
и брони ... просто будем выделять предмет нажимать кнопочку equip и он будет добавляться к нашему
персонажу в заранее указанное место». The card: the character it acts on (the subtitle, as the
Characters and Weapons cards write it), the tiles (`maya_armorgrid`, laid over the `_TILES`
placeholder; without Qt a dropdown of the rows), Equip and Unequip in one row, the line. Equip puts
the picked row on the current character through `armor.equip` -- its bone's armor space, at
identity, where the game puts it; Unequip takes it off.

The character is the one the selection names, then the sole rig, then the sole skeleton
(`skeleton.current_root`), as in every other card; a selected piece names its own. The tiles'
«equipped» pills follow the selection through a scriptJob the line owns (it dies with the card).
Every callback goes through `_run`, which puts a failure on the line.

Spec: docs/superpowers/specs/2026-10-01-armor-techlimb-design.md
"""

import traceback

import maya.cmds as cmds

import maya_hubstyle as hubstyle

from maya_scenesetup import armor
from maya_scenesetup import catalog
from maya_scenesetup import skeleton

HUB_SECTION = "weapons"                   # the Inventory card we live in (its key)
#  The Inventory card's line and subtitle - `window._STATUS` / `window._WEAPONS_BOUND`,
#  spelled here so this module imports no window (a test pins them equal).
_STATUS = "mayaSceneSetupStatus"
_BOUND = "mayaSceneSetupWeaponsBound"
_TILES = "mayaSceneSetupArmorTiles"      # the tiles are laid over it
_MENU = "mayaSceneSetupArmorMenu"        # the rows, where the tiles cannot stand
_OPTIONVAR = "mayaSceneSetup_armor"      # the row picked

NO_CHARACTER = ("no character - select any control or joint of it (with one rig in the scene "
                "nothing needs selecting)")


# ------------------------------------------------------------------ policy

def bound_message(root, rig=False):
    """The subtitle: which character the presses act on, and what it is."""
    if not root:
        return "no character"
    return "{0} ({1})".format(root.split("|")[-1], "rig" if rig else "skeleton")


def _stored():
    if cmds.optionVar(exists=_OPTIONVAR):
        return cmds.optionVar(query=_OPTIONVAR) or ""
    return ""


def chosen_armor():
    """The row picked last, else the first."""
    return catalog.armor_by_key(_stored()) or catalog.ARMOR[0]


# ------------------------------------------------------------------- scene

def _status(message):
    try:
        cmds.text(_STATUS, edit=True, label=message)
    except RuntimeError:
        pass                               # the card is not built


def say(text):
    """The line, for the tiles' Open scene."""
    try:
        _status(text)
    except RuntimeError:
        pass


def _bound_root():
    """The character, with the subtitle refreshed to match."""
    root = skeleton.current_root()
    rig = bool(root) and root == skeleton.rig_root()
    try:
        cmds.text(_BOUND, edit=True, label=bound_message(root, rig))
    except RuntimeError:
        pass
    return root


def worn_keys():
    """The rows the current character wears (the tiles' pills)."""
    root = skeleton.current_root()
    return set(armor.worn(root)) if root else set()


def _tiles():
    try:
        import maya_armorgrid
        return maya_armorgrid.live(_TILES)
    except Exception:                                        # noqa: BLE001
        return None


def _say_pick(root, worn):
    entry = chosen_armor()
    _status(armor.pick_message(entry.label, entry.bone, entry.key in worn) if root
            else NO_CHARACTER)


def refresh(*_args, **kwargs):
    """Re-read the scene once: the character, the pills, and - unless
    `say=False` (the selection job: the line is the card's last press's) -
    the line."""
    root = _bound_root()
    worn = set(armor.worn(root)) if root else set()
    tiles = _tiles()
    if tiles is not None:
        tiles.refresh(worn)
    if kwargs.get("say", True):
        _say_pick(root, worn)


def select_armor(key):
    """A tile picked: remembered, and the line says what Equip will do."""
    if catalog.armor_by_key(key) is None:
        return
    cmds.optionVar(stringValue=(_OPTIONVAR, key))
    refresh()


def _run(action):
    """Run a callback, and put anything it throws on the line."""
    try:
        action()
    except Exception:
        _status(traceback.format_exc().strip().splitlines()[-1])
        raise


def _after(text):
    """The pills re-read after a press changed what the character wears, then the press's own
    line (a queued SelectionChanged refresh can run in the middle of an import, trap 118)."""
    refresh()
    _status(text)


def equip_armor():
    """The picked row onto the current character, in its predetermined place."""
    root = _bound_root()
    if not root:
        _status(NO_CHARACTER)
        return
    _after(armor.equip(root, chosen_armor()))


def equip_on(root, key):
    """The row `key` onto the character `root` - a tile dropped on him in a
    viewport (2026-10-01). Returns the line."""
    entry = catalog.armor_by_key(key)
    if entry is None or not root:
        return NO_CHARACTER if entry is not None else ""
    cmds.optionVar(stringValue=(_OPTIONVAR, key))
    text = armor.equip(root, entry)
    _after(text)
    return text


def unequip_armor():
    """The picked row off the current character."""
    root = _bound_root()
    if not root:
        _status(NO_CHARACTER)
        return
    _after(armor.unequip(root, chosen_armor().key))


def open_armor_scene(key):
    """Open scene on a tile: the row's model opened as the scene. Returns the line."""
    from maya_scenesetup import opener
    entry = catalog.armor_by_key(key)
    if entry is None:
        return ""
    return opener.open_asset(entry.path, entry.label)


# ------------------------------------------------------------------ window

def is_open():
    """True while the card is built in the hub (read by maya_hotkeys)."""
    return bool(cmds.control(_STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on the Inventory card, its Armor tab."""
    import maya_hub
    from maya_scenesetup import window
    window.show_tab("armor")
    return maya_hub.show(HUB_SECTION)


def _attach_tiles():
    """The tiles laid over the placeholder; False where they cannot stand (no Qt)."""
    try:
        import maya_armorgrid
        return maya_armorgrid.attach(_TILES, selected=chosen_armor().key) is not None
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return False


def menu_changed(*_args):
    """The fallback dropdown: the row it names is the picked one."""
    entry = catalog.armor_by_label(cmds.optionMenu(_MENU, query=True, value=True) or "")
    if entry is not None:
        select_armor(entry.key)


def _dropdown():
    cmds.optionMenu(_MENU, annotation="The piece Equip puts on",
                    changeCommand=lambda *_a: _run(menu_changed))
    for label in catalog.armor_labels():
        cmds.menuItem(label=label)
    cmds.optionMenu(_MENU, edit=True, value=chosen_armor().label)


def build_rows():
    """The Armor tab's rows, into whatever layout is current - the Inventory
    card's Armor column: the tiles (a dropdown where they cannot stand),
    Equip / Unequip. The tab's segment names it; the card builds the status
    line after them; then `watch`."""
    cmds.columnLayout(_TILES, adjustableColumn=True)
    cmds.setParent("..")
    if not _attach_tiles():
        _dropdown()

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "left", 4)])
    hubstyle.mark(cmds.button(
        label="Equip", height=32,
        annotation="Put the picked piece on the character, in its place: the bone it rides "
                   "(the Tech Limb: lowerarm_l, where Atone puts it), outside the skeleton, so "
                   "an export stays bones only. Replaces what that slot held. Or drag the tile "
                   "onto a character in a viewport.",
        command=lambda *_args: _run(equip_armor)), "primary", "shield")
    hubstyle.mark(cmds.button(
        label="Unequip", height=32, width=110,
        annotation="Take the picked piece off the character",
        command=lambda *_args: _run(unequip_armor)), "danger", "trash")
    cmds.setParent("..")


def show():
    """The Armor tab just shown: the tiles fitted to their placeholder (a
    hidden widget gets no resize event) and the line saying the pick."""
    tiles = _tiles()
    if tiles is not None:
        host = getattr(tiles, "_host", None)
        if host is not None:
            tiles.fit(host)
    refresh()


def watch():
    """After the card's line exists: the pills and the subtitle follow the
    selection through a job the line owns (it dies with the card); the line
    itself is left to the presses."""
    cmds.scriptJob(event=["SelectionChanged",
                          lambda: _quiet(lambda: refresh(say=False))],
                   parent=_STATUS)
    _quiet(lambda: refresh(say=False))


def _quiet(action):
    try:
        action()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
