"""verify_hub_skin.py - the SkeldarAnim hub's skin, live, in the animator's Maya.

Send through the command port (CLAUDE.md, "Driving the user's live Maya")
against the INSTALLED copy (the shelf's), in PHASES, one send each - a
rebuild is deferred and a grab in the same send as a layout change
photographs the old layout (trap 68):

    PHASE = 0   every card opened (the collapse memory saved first)
    PHASE = 1   the standing skin: structure, marks, sizes, the header, the
                segments, the subtitles, expand + the active card; photos
    PHASE = 2   set_classic(True)  (the rebuild runs after this send)
    PHASE = 3   the classic hub stands with its way back; set_classic(False)
    PHASE = 4   the skin is back, the collapse memory as it was

UI only: the hub is rebuilt IN PLACE (where it is docked survives), never
deleted; no node of the scene is touched; the collapse memory, the header
message and the hotkey paint are put back.

Spec: docs/superpowers/specs/2026-09-28-hub-skin-design.md
"""
import json
import os

import maya.cmds as cmds

FAILED = []
PASSED = []
DIR = os.environ.get("SKELDAR_VERIFY_DIR", os.path.dirname(
    os.path.abspath(globals().get("__file__", "."))))
MEMORY = os.path.join(DIR, "verify_hub_skin_memory.json")


def gate(n, name, ok, detail=""):
    (PASSED if ok else FAILED).append(n)
    print("%s %2d %s%s" % ("ok  " if ok else "FAIL", n, name,
                           (" - " + str(detail)) if detail else ""))


import maya_hub
import maya_hubqt
import maya_hubstyle
import maya_update
import maya_hotkeys
from maya_scenesetup import window as ss
from maya_scenesetup import connections as cx
from maya_uebridge import window as ue
import maya_colour

PHASE = globals().get("PHASE", 1)
qt = maya_hubqt.qt()


def body_of(name):
    path = cmds.control(name, query=True, fullPathName=True) or ""
    for sec in maya_hub.card_sections():
        if "skeldarHubBodyLayout_" + sec.key in path.split("|"):
            return sec.key
    return None


if PHASE == 0:
    #  Every card open for the measurements, in a send of its own: a hidden
    #  body is never laid out (the segments read their size hints, 35 and
    #  56 px, in the animator's hub with Connections collapsed). The memory
    #  is saved first and put back at the end of phase 1.
    memory = dict((s.key, maya_hub.collapsed(s.key))
                  for s in maya_hub.SECTIONS)
    with open(MEMORY, "w") as handle:
        json.dump(memory, handle)
    for card in maya_hub._SKIN.cards.values():
        card.set_collapsed(False)
    print("cards opened; memory saved", memory)

elif PHASE == 1:
    skin = maya_hub._SKIN
    with open(MEMORY) as handle:
        memory = json.load(handle)
    installed = maya_update.installed_dir().replace("\\", "/")
    here = maya_hub.__file__.replace("\\", "/")

    # ---- 1-2: the skin stands, from the installed copy, in the control
    gate(1, "the skin stands (built by the installed copy)",
         maya_hub.is_skinned() and here.startswith(installed), here)
    host = skin.root.parentWidget()
    roots = [w for w in host.findChildren(qt.QtWidgets.QWidget)
             if w.objectName() == maya_hubstyle.ROOT] if host else []
    gate(2, "its root, alone, sits in the workspaceControl",
         host is not None and host.objectName() == maya_hub.CONTROL
         and skin.root.objectName() == maya_hubstyle.ROOT
         and len(roots) == 1,
         (host.objectName() if host else None, len(roots)))

    # ---- 3-5: the header
    actions = [a.text() for a in skin.menu.actions() if not a.isSeparator()]
    gate(3, "the header: hotkeys, version chip, menu",
         actions == ["Check update", "Hotkey Editor...", "Classic look"]
         and skin.hotkeys.isCheckable(), actions)
    record = maya_update.read_record(maya_update.installed_dir())
    short = record.get("short") or (record.get("commit") or "")[:7]
    gate(4, "the chip is the installed build", skin.version.text() == short
         and short, (skin.version.text(), short))
    gate(5, "the hotkey switch shows the map's state",
         skin.hotkeys.isChecked() == maya_hotkeys.is_active(),
         maya_hotkeys.is_active())

    # ---- 6-7: strip and cards
    cards = [s.key for s in maya_hub.card_sections()]
    gate(6, "the strip: one jump per card, in order",
         list(skin.jumps) == cards, list(skin.jumps))
    column = skin.column
    order = [column.itemAt(i).widget().objectName()
             for i in range(column.count()) if column.itemAt(i).widget()]
    wanted = []
    group = None
    for sec in maya_hub.card_sections():
        if sec.group != group:
            wanted.append("skeldarHubGroup_" + sec.group)
            group = sec.group
        wanted.append("skeldarHubCard_" + sec.key)
    gate(7, "cards in order under Scene / Animation / Look", order == wanted,
         order)

    # ---- 8: every card's named controls live in its body
    homes = {"characters": (ss._PORTRAITS, ss._CHARACTER_STATUS),
             "weapons": (ss._MENU, ss._STATUS, ss._ROTATE),
             "connections": (cx.STATUS, cx.HEADER),
             "uebridge": (ue._LIST, ue._STATUS),
             "retarget": ("skeldarRetargetStatus",),
             "studio": ("vpStudioStatus",),
             "colour": (maya_colour.STATUS,),
             "update": (maya_update.STATUS,)}
    wrong = [(key, name, body_of(name)) for key, names in homes.items()
             for name in names if body_of(name) != key]
    gate(8, "every card's controls are in its body", not wrong, wrong)

    # ---- 9-10: subtitles moved and still written by cmds
    moved = []
    for key, name in (("characters", ss._BOUND), ("uebridge", ue._HEADER),
                      ("colour", maya_colour.TAKEN),
                      ("update", maya_update.INSTALLED)):
        widget = maya_hubqt.find(name)
        moved.append(bool(widget) and skin.cards[key].header.isAncestorOf(
            widget))
    gate(9, "the four subtitles sit in their card headers", all(moved),
         moved)
    before = cmds.text(ss._BOUND, query=True, label=True)
    cmds.text(ss._BOUND, edit=True, label="verify subtitle")
    seen = maya_hubqt.find(ss._BOUND).property("text")
    cmds.text(ss._BOUND, edit=True, label=before)
    gate(10, "cmds still writes a moved subtitle", seen == "verify subtitle",
         seen)

    # ---- 11-13: the marks became the look
    def role_of_label(label):
        for widget in skin.root.findChildren(qt.QtWidgets.QPushButton):
            if widget.text() == label:
                return widget.property("skRole")
        return None
    roles = dict((label, role_of_label(label)) for label in
                 ("Add Character", "Remove Weapon", "Add", "Apply all",
                  "Import", "Retarget", "Apply Look"))
    gate(11, "one primary action per card, Remove is danger",
         roles == {"Add Character": "primary", "Remove Weapon": "danger",
                   "Add": "primary", "Apply all": "primary",
                   "Import": "primary", "Retarget": "primary",
                   "Apply Look": "primary"}, roles)
    sheet = skin.root.styleSheet()
    gate(12, "the stylesheet is on the root, at the display scale",
         '[skRole="primary"]' in sheet and "down-arrow" in sheet
         and maya_hubstyle.TOKENS["accent"] in sheet, len(sheet))
    dot = maya_hubqt.find(ss._CHARACTER_DOT.format(0))
    gate(13, "the palette dots are painted swatches",
         bool(dot) and "background:" in dot.styleSheet(),
         dot.styleSheet()[:60] if dot else None)

    # ---- 14-16: segments
    free = maya_hubqt.find(cx.segment_name("R", "Free"))
    weapon = maya_hubqt.find(cx.segment_name("R", "Weapon"))
    gate(14, "the segments share their track equally",
         abs(free.width() - weapon.width()) <= 3 and free.width() > 60,
         (free.width(), weapon.width()))
    saved = cx.menus()
    cx._set_menus({"R": "Weapon", "W": "Hand_L"})
    after = cx.menus()
    cx._set_menus(saved)
    gate(15, "cmds still reads and writes the moved segments",
         after["R"] == "Weapon" and after["W"] == "Hand_L"
         and cx.menus() == saved, after)
    mode_before = ue.import_mode()
    cmds.iconTextRadioButton(ue.mode_button("new_rig"), edit=True,
                             select=True)
    mode_after = ue.import_mode()
    cmds.iconTextRadioButton(ue.mode_button(mode_before), edit=True,
                             select=True)
    gate(16, "the bridge's import mode reads its segments",
         mode_after == "new_rig" and ue.import_mode() == mode_before,
         (mode_before, mode_after))

    # ---- 17: fits the dock
    need = skin.content.minimumSizeHint().width()
    have = skin.scroll.viewport().width()
    gate(17, "nothing is wider than the dock", need <= have, (need, have))

    # ---- 18-19: the header message, the hotkey paint
    skin.say("verify message")
    shown = not skin.message.isHidden()
    skin.say("")
    gate(18, "the message line shows while it holds text",
         shown and skin.message.isHidden())
    active = maya_hotkeys.is_active()
    maya_hub.paint_hotkeys(not active)
    lit = skin.hotkeys.isChecked()
    maya_hub.paint_hotkeys(active)
    gate(19, "paint_hotkeys lights the header switch",
         lit == (not active) and skin.hotkeys.isChecked() == active)

    # ---- 20-21: expand from the strip, the active card
    skin.cards["studio"].set_collapsed(True)
    skin.jumps["studio"].click()
    others = [k for k, c in skin.cards.items()
              if k != "studio" and not c.collapsed()]
    gate(20, "a jump opens its card ONLY and lights it",
         not skin.cards["studio"].collapsed() and skin.active == "studio"
         and not maya_hub.collapsed("studio") and not others, others)
    field = maya_hubqt.find(ue._SEARCH)
    qt.QtWidgets.QApplication.sendEvent(
        field, qt.QtGui.QFocusEvent(qt.QtCore.QEvent.FocusIn))
    gate(21, "focus inside a card lights that card",
         skin.active == "uebridge", skin.active)
    point = qt.QtCore.QPointF(1, 1)
    qt.QtWidgets.QApplication.sendEvent(
        maya_hubqt.find(maya_colour.STATUS),
        qt.QtGui.QEnterEvent(point, point, point))
    hovered = skin.active
    qt.QtWidgets.QApplication.sendEvent(
        skin.root, qt.QtCore.QEvent(qt.QtCore.QEvent.Leave))
    pending = skin._fallback.isActive() and skin.active == "colour"
    skin._fallback.timeout.emit()
    #  uebridge was pinned by the focus above while CLOSED (the jump to
    #  studio closed it): off the hub nothing is lit; opened, it is
    closed_rest = skin.active
    skin.cards["uebridge"].set_collapsed(False)
    open_rest = skin.resting()
    skin.cards["uebridge"].set_collapsed(True)
    gate(27, "the mouse over a card lights it; off the hub, after a pause, "
             "the one worked in only if open",
         hovered == "colour" and pending and closed_rest is None
         and open_rest == "uebridge", (hovered, pending, closed_rest,
                                       open_rest))
    skin.set_active(None)

    # ---- memory back
    for key, value in memory.items():
        maya_hub.remember(key, value)
        card = skin.cards.get(key)
        if card is not None:
            card.set_collapsed(value)

elif PHASE == 2:
    maya_hub.set_classic(True)
    print("classic asked; the rebuild runs after this send")

elif PHASE == 3:
    gate(22, "the classic hub stands, frames and the way back",
         not maya_hub.is_skinned()
         and cmds.frameLayout("skeldarHubFrameCharacters", exists=True)
         and cmds.control(maya_hub.NEW_LOOK_BUTTON, exists=True))
    gate(23, "the classic hub has Hotkeys and Update as sections",
         cmds.frameLayout("skeldarHubFrameHotkeys", exists=True)
         and cmds.frameLayout("skeldarHubFrameUpdate", exists=True))
    maya_hub.set_classic(False)
    print("skin asked; the rebuild runs after this send")

elif PHASE == 4:
    with open(MEMORY) as handle:
        memory = json.load(handle)
    now = dict((s.key, maya_hub.collapsed(s.key)) for s in maya_hub.SECTIONS)
    gate(24, "the skin is back, in the same control",
         maya_hub.is_skinned() and not maya_hub.classic_asked()
         and maya_hub._SKIN.root.parentWidget().objectName()
         == maya_hub.CONTROL)
    gate(25, "the collapse memory survived both rebuilds", now == memory,
         dict((k, (memory.get(k), now[k])) for k in now
              if memory.get(k) != now[k]))
    gate(26, "the cards open as remembered",
         all(maya_hub._SKIN.cards[s.key].collapsed() == memory[s.key]
             for s in maya_hub.card_sections()))

print("VERIFY phase %s: %d passed, %d failed %s" % (PHASE, len(PASSED),
                                                     len(FAILED), FAILED))
