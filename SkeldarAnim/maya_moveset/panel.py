"""The hub card Moveset: the Longsword combo trees, statuses and assignees shared
with the moveset page, and an attack's montage slot opened through the UE
Bridge's montage import.

The trees are a Qt view (`view.TreeView`) laid over the `cmds` placeholder
PLACE; everything else is `cmds`, so the hub's skin and a popup copy reach it.
Each card copy keeps its own context, keyed by the placeholder's resolved name.
"""
import os

from maya import cmds

import maya_hubcopy as hubcopy
from maya_moveset import model as m

HUB_SECTION = "moveset"
SUB = "skeldarMovesetSub"
FOLDER_BTN = "skeldarMovesetFolderBtn"
WEAPONS_COLL = "skeldarMovesetWeapons"
WEAPON_SEG = "skeldarMovesetWeapon_{0}"
ROOT_MENU = "skeldarMovesetRoot"
MODE_MENU = "skeldarMovesetMode"
WHO_MENU = "skeldarMovesetWho"
CHIP = "skeldarMovesetType_{0}"
PLACE = "skeldarMovesetTree"
OPEN = "skeldarMovesetOpen{0}"
FRAME_BTN = "skeldarMovesetFrame"
STATUS = "skeldarMovesetStatus"
TREE_HEIGHT = 470
POLL_MS = 1500
MODES = (("combos", "Combos only"), ("all", "All transitions"))
ANYONE, UNASSIGNED = "Anyone", "Unassigned"

_CARDS = {}          # resolved PLACE -> {"view", "roots", "status", "people", "mtime"}


def folder():
    if cmds.optionVar(exists=m.FOLDER_VAR):
        return cmds.optionVar(query=m.FOLDER_VAR)
    return m.default_folder()


# ---- the card -----------------------------------------------------------------

def build_panel():
    import maya_hubstyle as hubstyle
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1)
    cmds.text(SUB, label="", align="left")
    hubstyle.mark(cmds.button(FOLDER_BTN, label=hubstyle.tool_label("Folder..."),
                              annotation="The moveset folder (graph.json, media, state.json)",
                              command=lambda *_a: pick_folder()), "tool", "folder")
    cmds.setParent("..")

    #  one segment a weapon the folder holds, the chosen one lit; a folder of
    #  one weapon gets no segments at all
    found = m.weapons(folder())
    if len(found) > 1:
        shown = m.chosen_weapon(m.read_state(folder()), found)
        cmds.rowLayout(numberOfColumns=len(found))
        cmds.iconTextRadioCollection(WEAPONS_COLL)
        for weapon in found:
            hubstyle.mark(cmds.iconTextRadioButton(
                WEAPON_SEG.format(weapon.key), style="textOnly", label=weapon.label,
                height=hubstyle.height("segment", 24), select=weapon.key == shown.key,
                collection=WEAPONS_COLL,
                annotation="The weapon whose combo trees are shown - the page shows the same one",
                onCommand=_press_weapon(weapon.key)), "segment")
        cmds.setParent("..")

    cmds.optionMenu(ROOT_MENU, label="Opening",
                    changeCommand=lambda *_a: _filter(root=True))
    cmds.menuItem(label="All")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2)
    cmds.optionMenu(MODE_MENU, label="Branches", changeCommand=lambda *_a: _filter(mode=True))
    for _k, label in MODES:
        cmds.menuItem(label=label)
    cmds.optionMenu(WHO_MENU, label="Assignee", changeCommand=lambda *_a: _filter(who=True))
    cmds.menuItem(label=ANYONE)
    cmds.setParent("..")

    cmds.rowLayout(numberOfColumns=len(m.TYPES))
    for key, label in m.TYPES:
        hubstyle.mark(cmds.checkBox(CHIP.format(key), label=label, value=False,
                                    changeCommand=lambda *_a: _filter(types=True)), "chip")
    cmds.setParent("..")

    cmds.columnLayout(PLACE, adjustableColumn=True, height=TREE_HEIGHT)
    cmds.setParent("..")

    row = cmds.rowLayout(numberOfColumns=3)
    hubstyle.mark(row, "fill", layout=True)
    hubstyle.mark(cmds.button(OPEN.format("3p"), label="Open 3P",
                              height=hubstyle.height("button", 30),
                              annotation="The picked attack's 3P montage slot onto the rig "
                                         "(the selected one, else a new one) - UE Bridge",
                              command=lambda *_a: open_picked("3p")), "primary", "download")
    hubstyle.mark(cmds.button(OPEN.format("1p"), label="Open 1P",
                              height=hubstyle.height("button", 30),
                              annotation="The picked attack's 1P montage slot",
                              command=lambda *_a: open_picked("1p")), "secondary", "download")
    hubstyle.mark(cmds.button(FRAME_BTN, label="Fit", height=hubstyle.height("button", 30),
                              annotation="Fit the trees' width; read the files again",
                              command=lambda *_a: reload(frame=True)), "secondary", "refresh")
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", height=36, wordWrap=True), "status")
    cmds.setParent("..")
    attach()
    return column


def _card():
    return _CARDS.get(hubcopy.resolve(PLACE))


def attach():
    """The tree view laid over PLACE, its keeper and its state watch."""
    import maya_hubqt
    if maya_hubqt.qt() is None:
        return None
    host = maya_hubqt.find(PLACE, layout=True)
    if host is None:
        return None
    from PySide6 import QtCore
    from maya_moveset import view as treeview
    key = hubcopy.resolve(PLACE)
    #  every name a callback of ours keeps is resolved here: the state poll runs
    #  on a timer, outside the copy's scope, where a bare name is the hub's
    card = {"status": hubcopy.resolve(STATUS), "root_menu": hubcopy.resolve(ROOT_MENU),
            "who_menu": hubcopy.resolve(WHO_MENU), "sub": hubcopy.resolve(SUB),
            "chips": dict((chip, hubcopy.resolve(CHIP.format(chip))) for chip, _l in m.TYPES),
            "segs": dict((w.key, hubcopy.resolve(WEAPON_SEG.format(w.key)))
                         for w in m.weapons(folder())),
            "weapon": None,
            "roots": [], "people": [], "mtime": 0.0, "host": host}
    actions = {"open": lambda i, v, c=card: _say(c, open_slot(c["view"].graph, i, v)),
               "status": lambda i, v, s, c=card: _set(c, i, v, status=s),
               "assign": lambda i, v, p, c=card: _set(c, i, v, person=p),
               "picked": lambda i, c=card: _say(c, picked_line(c["view"], i))}
    view = treeview.TreeView(host, actions)
    card["view"] = view
    card["keeper"] = treeview.Keeper(host, view)
    timer = QtCore.QTimer(view)
    timer.setInterval(POLL_MS)
    timer.timeout.connect(lambda c=card: _poll(c))
    timer.start()
    card["timer"] = timer
    _CARDS[key] = card
    view.show()
    _load(card, frame=True)
    return view


def _load(card, frame=False):
    view, where = card["view"], folder()
    state = m.read_state(where)
    weapon = m.chosen_weapon(state, m.weapons(where))
    if weapon is None:
        card["weapon"] = None
        view.set_data({"nodes": {}, "edges": [], "entries": []}, m.read_state(""), where)
        _sub(card, "No moveset here")
        _say(card, "No {0} in {1} - press the folder button and pick the moveset "
                   "folder".format(m.GRAPH, where))
        return
    path = os.path.join(where, weapon.graph)
    try:
        graph = m.load_graph(where, weapon.graph)
    except (OSError, ValueError) as error:
        _say(card, "Cannot read {0}: {1}".format(path, error))
        return
    card["mtime"] = m.state_mtime(where)
    card["weapon"] = weapon
    view.set_data(graph, state, where, weapon)
    held = _chips(card, graph)
    kept = [key for key in view.types if key in held]
    if set(kept) != set(view.types):
        #  a type this weapon has none of cannot stay in the filter, or the
        #  card would open on «No tree matches the filter»
        view.set_filter(types=kept)
    _fill_menus(card)
    _lit(card, weapon)
    _sub(card, _summary(graph, state, weapon))
    if frame:
        view.frame()


def _chips(card, graph):
    """The type chips this weapon has attacks for; the rest dimmed and cleared.
    Returns the types held, in TYPES order."""
    held = [key for key, _label in m.types_in(graph)]
    for key, _label in m.TYPES:
        name = card["chips"].get(key, CHIP.format(key))
        if not cmds.checkBox(name, exists=True):
            continue
        there = key in held
        if not there and cmds.checkBox(name, query=True, value=True):
            cmds.checkBox(name, edit=True, value=False)
        cmds.checkBox(name, edit=True, enable=there)
    return held


def _lit(card, weapon):
    """The weapon's segment, lit - a switch may have come from the page."""
    name = card["segs"].get(weapon.key)
    if name and cmds.iconTextRadioButton(name, exists=True):
        cmds.iconTextRadioButton(name, edit=True, select=True)


def _press_weapon(key):
    return lambda *_a: pick_weapon(key)


def pick_weapon(key):
    """The weapon the card shows. Written where the page reads it too, so the
    two never show different weapons; the page takes it on its next look."""
    m.write_state(folder(), **{m.STATE_WEAPON: key})
    card = _card()
    if not card:
        return
    _load(card, frame=True)
    weapon = card.get("weapon")
    _say(card, "{0} - the page shows it on its next look".format(weapon.label if weapon else key))


def reload(frame=False):
    card = _card()
    if card:
        _load(card, frame)
        _say(card, "Read {0} again".format(folder()))


def _poll(card):
    try:
        mtime = m.state_mtime(card["view"].folder)
    except RuntimeError:
        return
    if mtime and mtime != card["mtime"]:
        card["mtime"] = mtime
        where = card["view"].folder
        state = m.read_state(where)
        here, wanted = card.get("weapon"), m.chosen_weapon(state, m.weapons(where))
        if here is not None and wanted is not None and wanted.key != here.key:
            #  the page switched the weapon: the whole card follows it
            _load(card, frame=True)
            return
        card["view"].set_state(state)
        if state["people"] != card["people"]:
            _fill_menus(card)
        _sub(card, _summary(card["view"].graph, state, here))


def _summary(graph, state, weapon=None):
    """«Dagger - 22 attacks, 0 of 44 done» - counted for the weapon shown: the
    two weapons share one state file, and their node ids cannot collide."""
    nodes = graph.get("nodes", {})
    done = sum(1 for key, value in state["status"].items()
               if value == "done" and key.split("|")[0] in nodes)
    return "{0} - {1} attacks, {2} of {3} done".format(
        weapon.label if weapon else m.LONGSWORD[1], len(nodes), done, len(nodes) * len(m.VIEWS))


def _fill_menus(card):
    view = card["view"]
    roots = [t.root for t in m.trees(view.graph, view.state, view.mode)]
    menu = card["root_menu"]
    if cmds.optionMenu(menu, exists=True):
        for item in cmds.optionMenu(menu, query=True, itemListLong=True) or []:
            cmds.deleteUI(item)
        cmds.menuItem(label="All", parent=menu)
        for root in roots:
            cmds.menuItem(label=m.label(root, view.state["custom"]), parent=menu)
        if view.root in roots:
            cmds.optionMenu(menu, edit=True, select=roots.index(view.root) + 2)
        else:
            view.root = ""
    card["roots"] = roots
    who = card["who_menu"]
    people = list(view.state["people"])
    card["people"] = people
    if cmds.optionMenu(who, exists=True):
        for item in cmds.optionMenu(who, query=True, itemListLong=True) or []:
            cmds.deleteUI(item)
        for label in [ANYONE, UNASSIGNED] + people:
            cmds.menuItem(label=label, parent=who)
        if view.who and view.who in people:
            cmds.optionMenu(who, edit=True, select=people.index(view.who) + 3)
        elif view.who == "":
            cmds.optionMenu(who, edit=True, select=2)
        else:
            view.who = None


def _filter(root=False, mode=False, who=False, types=False):
    card = _card()
    if not card:
        return
    view = card["view"]
    if root:
        index = cmds.optionMenu(ROOT_MENU, query=True, select=1) - 2
        view.set_filter(root=card["roots"][index] if 0 <= index < len(card["roots"]) else "")
    if mode:
        index = cmds.optionMenu(MODE_MENU, query=True, select=1) - 1
        view.set_filter(mode=MODES[index][0])
        _fill_menus(card)
    if who:
        index = cmds.optionMenu(WHO_MENU, query=True, select=1)
        view.set_filter(who=None if index == 1 else "" if index == 2 else card["people"][index - 3])
    if types:
        view.set_filter(types=[k for k, _l in m.TYPES
                               if cmds.checkBox(CHIP.format(k), query=True, value=True)])


def pick_folder():
    picked = cmds.fileDialog2(fileMode=3, dialogStyle=2, startingDirectory=folder(),
                              caption="The moveset folder (holding graph.json)")
    if not picked:
        return
    cmds.optionVar(stringValue=(m.FOLDER_VAR, picked[0]))
    card = _card()
    before = sorted(card["segs"]) if card else []
    reload(frame=True)
    after = sorted(w.key for w in m.weapons(picked[0]))
    if card and after != before:
        #  the segments were built for the folder the card opened on: a cmds
        #  control keeps its name for the session, so the row cannot grow
        _say(card, "{0} - close and open the Moveset section for its weapons "
                   "({1})".format(picked[0], ", ".join(after) or "none"))


# ---- presses ------------------------------------------------------------------

def _set(card, node_id, view_key, status=None, person=None):
    where = card["view"].folder
    state = m.read_state(where)
    if status is not None:
        m.write_state(where, status=m.set_status(state, node_id, view_key, status))
        word = next((l for s, l, _c in m.STATUSES if s == status), "Not planned")
        line = "{0} {1}: {2}".format(m.label(node_id, state["custom"]), view_key.upper(), word)
    else:
        m.write_state(where, assignee=m.set_assignee(state, node_id, view_key, person))
        line = "{0} {1} → {2}".format(m.label(node_id, state["custom"]), view_key.upper(),
                                           person or "nobody")
    card["mtime"] = m.state_mtime(where)
    state = m.read_state(where)
    card["view"].set_state(state)
    _sub(card, _summary(card["view"].graph, state))
    _say(card, line + " - the page shows it on its next look")


def picked_line(view, node_id):
    node = view.graph.get("nodes", {}).get(node_id) or {}
    slots = ", ".join("{0} {1}".format(v.upper(), m.slot_of(view.graph, node_id, v) or "-")
                      for v in m.VIEWS)
    length = node.get("montageLength") or node.get("duration")
    return "{0} - {1}{2}".format(m.label(node_id, view.state["custom"]), slots,
                                 ", {0:.2f} s".format(length) if length else "")


def open_picked(view_key):
    card = _card()
    if not card:
        return
    view = card["view"]
    if not view.picked_id:
        _say(card, "Pick an attack in the tree first")
        return
    _say(card, open_slot(view.graph, view.picked_id, view_key))


def open_slot(graph, node_id, view_key):
    """The attack's montage slot for `view_key` through the UE Bridge's montage
    road: onto the selected rig (else the only one), a new rig when the scene has
    none. Returns the status line."""
    node = graph.get("nodes", {}).get(node_id)
    if not node:
        if m.is_custom(node_id):
            return "{0} is a card of your own - it has no montage".format(m.label(node_id))
        return "{0}: graph.json holds no montage for it".format(m.label(node_id))
    slot = m.slot_of(graph, node_id, view_key)
    if not slot:
        return "{0} has no {1} slot".format(m.label(node_id), view_key.upper())
    import maya_rigs
    from maya_uebridge import records, rigimport, uelink
    from maya_uebridge import window as bridge
    record = records.with_slot(records.AnimRecord(
        node_id, m.package_of(node.get("path", "")), "", 0,
        node.get("montageLength") or 0.0, None, kind=records.MONTAGE), slot)
    target = "new_rig"
    if maya_rigs.rigs():
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return refusal
        target = "rig"
    try:
        exported, fps = bridge._export_from_editor(record)
        return rigimport.import_and_retarget(exported, record.name, clip_fps=fps,
                                             set_timeline=True, target=target)
    except uelink.UeBridgeError as error:
        return str(error)


def _say(card, text):
    name = card["status"]
    if cmds.text(name, exists=True):
        cmds.text(name, edit=True, label=text)
    return text


def _sub(card, text):
    if cmds.text(card["sub"], exists=True):
        cmds.text(card["sub"], edit=True, label=text)
