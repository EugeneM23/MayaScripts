"""Live proof of the Weapons card as the inventory (2026-09-30).

Run in a DISPOSABLE Maya (it opens a new scene, adds a rig and weapons): its
own MAYA_APP_DIR, MAYA_NO_HOME=1, a free port. Each send sets PHASE first:

    PHASE = "card"      gates 1-3: the card holds the panel, nothing retired
                        is left, the channel columns at a 360 px dock
    PHASE = "hands"     gates 4-9: click-pick + Add into the left hand, an
                        edit of a grip, Remove, a drop onto the projected
                        hand, the Colour section on the selected weapon
    PHASE = "photo"     the card and the panel grabbed to PNGs (a send of its
                        own - trap 68)
    PHASE = "classic"   asks for the classic hub (deferred rebuild)
    PHASE = "classic2"  gate 10: the panel stands in the classic hub too;
                        back to the skin

Spec: docs/superpowers/specs/2026-09-30-weapons-card-inventory-design.md
"""

import math
import os
import sys

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402

PHASE = globals().get("PHASE", "card")
if PHASE == "card":
    # a fresh start: every module of ours re-imported from the repo, all
    # package roots together (trap 84), so the hub rebuilds from this code
    for _name in list(sys.modules):
        if _name.split(".")[0] in ("maya_overrig", "maya_uebridge", "maya_scenesetup",
                                   "maya_graphoverlay", "skeldar_features", "install") \
                or (_name.startswith("maya_") and "." not in _name
                    and getattr(sys.modules[_name], "__file__", "")
                    and "SkeldarAnim" in (sys.modules[_name].__file__ or "")):
            del sys.modules[_name]
SHOTS = globals().get("SHOTS", os.path.join(os.environ.get("TEMP", "C:/Temp"),
                                            "weapons_card"))
FAILED = []
WORLD = sys.__dict__.setdefault("_verify_weapons_card", {})   # across sends
DOCK = 360                                   # the animator's dock, logical px
VIEWPORT = 510                               # ... its scroll viewport, physical px


def gate(number, text, ok, detail=""):
    print("gate %2d %s  %s  %s" % (number, "PASS" if ok else "FAIL", text, detail))
    if not ok:
        FAILED.append(number)


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(a))))


def settle():
    import maya_hubqt
    q = maya_hubqt.qt()
    for _ in range(3):
        q.QtWidgets.QApplication.processEvents()
    cmds.refresh(force=True)


def panel():
    import maya_inventory
    return maya_inventory.live()


def card():
    import maya_hubqt
    return maya_hubqt.find("skeldarHubCard_weapons")


def root():
    from maya_scenesetup import skeleton
    return skeleton.current_root()


def held(side):
    """(key, where) of what `side` holds, or (None, None)."""
    from maya_scenesetup import equip
    weapon, where = equip.occupant(root(), side)
    return (equip._key(weapon) if weapon else None), where


def to_global(world):
    """The global screen point of a world point through the perspective panel."""
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaUI as omui
    import maya_hubqt
    q = maya_hubqt.qt()
    view = omui.M3dView.getM3dViewFromModelPanel("modelPanel4")
    widget = q.shiboken.wrapInstance(int(view.widget()), q.QtWidgets.QWidget)
    x, y, _clipped = view.worldToView(om.MPoint(*world))
    sx = view.portWidth() / float(widget.width())
    sy = view.portHeight() / float(widget.height())
    local = q.QtCore.QPoint(int(round(x / sx)), int(round(widget.height() - y / sy)))
    point = widget.mapToGlobal(local)
    return point.x(), point.y()


def keep_hub_off(points):
    """Move a floating hub off every point a drop is aimed at."""
    import maya_hubqt
    host = maya_hubqt.find("skeldarAnimHub")
    top = host.window()
    frame = top.frameGeometry()
    if not any(frame.contains(maya_hubqt.qt().QtCore.QPoint(x, y)) for x, y in points):
        return "the hub stands clear"
    screen = top.screen().availableGeometry()
    top.move(screen.left(), screen.top())
    settle()
    return "hub moved to %s" % (top.pos(),)


def click(widget, local, button=None):
    """A real press + release at `local` on `widget` (QMouseEvents sent)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    button = QtCore.Qt.LeftButton if button is None else button
    point = QtCore.QPoint(int(local[0]), int(local[1]))
    glob = QtCore.QPointF(widget.mapToGlobal(point))
    for kind, buttons in ((QtCore.QEvent.MouseButtonPress, button),
                          (QtCore.QEvent.MouseButtonRelease, QtCore.Qt.NoButton)):
        event = QtGui.QMouseEvent(kind, QtCore.QPointF(point), glob, button,
                                  buttons, QtCore.Qt.NoModifier)
        q.QtWidgets.QApplication.sendEvent(widget, event)
    settle()


def pick_item(key):
    import maya_invlook as look
    p = panel()
    rects = p.rects()
    x, y, _w, h = look.item_rect(rects, p.placements[key], p.cells[key], rects["cell"])
    click(p, (x + 4, y + h // 2))


def pick_hand(side):
    p = panel()
    x, y, _w, h = p.rects()["name_" + side]
    click(p, (x + 6, y + h // 2))


def press_button(label):
    """The card's own Qt button with `label`, clicked."""
    import maya_hubqt
    q = maya_hubqt.qt()
    buttons = [b for b in card().findChildren(q.QtWidgets.QPushButton)
               if b.text() == label]
    buttons[0].click()
    settle()
    return len(buttons)


def status():
    from maya_scenesetup import window
    return cmds.text(window._STATUS, query=True, label=True)


def column(side):
    import maya_invlook as look
    p = panel()
    return [p.field(side, c).text() for c in look.CHANNELS]


def shown(side):
    """What the scene says the column should read."""
    import maya_inventory
    import maya_invlook as look
    from maya_scenesetup import window
    values = maya_inventory.hand_values(window.hand_grips(root())[side])
    return [look.channel_text(values[c]) for c in look.CHANNELS]


# ------------------------------------------------------------------ phases

def phase_card():
    import maya_hub
    import maya_hubqt
    from maya_scenesetup import catalog
    from maya_scenesetup import character
    from maya_scenesetup import window

    cmds.file(new=True, force=True)
    maya_hub.show("weapons")
    settle()
    WORLD["added"] = character.add_character(catalog.default_rig())
    cmds.select(clear=True)
    cmds.viewPlace("persp", eye=(0.0, 160.0, 330.0), lookAt=(0.0, 110.0, 0.0))
    window.refresh()
    settle()

    # ---- 1: the card holds the panel
    p = panel()
    host = maya_hubqt.find(window._INVENTORY, layout=True)
    c = card()
    inside = bool(c is not None and host is not None and c.isAncestorOf(host))
    fields = p.findChildren(maya_hubqt.qt().QtWidgets.QLineEdit) if p else []
    icons = [k for k in (p.pixmaps if p else {}) if not p.pixmaps[k].isNull()]
    gate(1, "the Weapons card holds the inventory: 12 channel fields, every weapon",
         maya_hub.is_skinned() and inside and p is not None and len(fields) == 12
         and set(p.placements) == set(e.key for e in catalog.WEAPONS)
         and len(icons) == len(catalog.WEAPONS)
         and host.height() == p.height_for(host.width()) > 0,
         "host %s panel %s fields %d icons %d | %s" % (
             (host.width(), host.height()) if host else None,
             p.geometry() if p else None, len(fields), len(icons), WORLD["added"]))

    # ---- 2: nothing retired is left
    retired = [name for name in ("mayaSceneSetupMenu", "mayaSceneSetupCustomFbx",
                                 "mayaSceneSetupBrowseFbx", "mayaSceneSetupRotate",
                                 "mayaSceneSetupTranslate", "mayaSceneSetupWeaponColour",
                                 "mayaSceneSetupWeaponDot0", "mayaSceneSetupHand_R",
                                 window._WEAPON_MENU)
               if cmds.control(name, exists=True)]
    import maya_inventory
    labels = sorted(b.text() for b in c.findChildren(maya_hubqt.qt().QtWidgets.QPushButton)
                    if b.text())
    floating = [(w.objectName(), type(w).__name__) for w in maya_inventory._windows()
                if w.isVisible()]
    gate(2, "no dropdown, FBX, Hand row, grip rows, colour or Inventory button; "
            "the subtitle names Manny",
         not retired and labels == ["Add", "Remove Weapon"] and not floating
         and "root" in cmds.text(window._WEAPONS_BOUND, query=True, label=True),
         "retired %s buttons %s floating %s subtitle '%s'" % (
             retired, labels, floating,
             cmds.text(window._WEAPONS_BOUND, query=True, label=True)))

    # ---- 3: at the animator's 360 px dock the Channel Box names fit. The
    #  dock measured live 2026-09-28: its scroll viewport 510 physical px at
    #  150 %; the floating hub is sized so its viewport is that wide.
    q = maya_hubqt.qt()
    top = maya_hubqt.find(maya_hub.CONTROL).window()
    for _ in range(3):
        scroll = [a for a in maya_hubqt.find(maya_hub.CONTROL).findChildren(
            q.QtWidgets.QScrollArea) if a.objectName() == "skeldarHubScrollArea"][0]
        viewport = scroll.viewport().width()
        top.resize(top.width() + (VIEWPORT - viewport), top.height())
        settle()
    print("    hub window %s, viewport %d" % (top.size(), scroll.viewport().width()))
    host = maya_hubqt.find(window._INVENTORY, layout=True)
    p = panel()
    k = p.k
    metrics = maya_hubqt.qt().QtGui.QFontMetrics(p.field_font)
    need = metrics.horizontalAdvance("-179.51")
    widths = [p.field(s, "tx").width() for s in "RL"]
    gate(3, "at a %d px dock the nice names fit and every value field holds -179.51" % DOCK,
         not p.short["R"] and not p.short["L"] and min(widths) >= need
         and host.height() == p.height_for(host.width()),
         "card width %.0f logical, fields %s px, need %d, short %s" % (
             host.width() / k, widths, need, p.short))


def phase_hands():
    import maya_colour
    import maya_invlook as look
    from maya_scenesetup import bonedrive
    from maya_scenesetup import colour
    from maya_scenesetup import equip
    from maya_scenesetup import grips
    from maya_scenesetup import window

    settle()
    # ---- 4: a click on Spear 03 and on the left hand, then Add
    pick_item("Spear_03")
    pick_hand("L")
    picked = window.picked()
    press_button("Add")
    got = held("L")
    gate(4, "click Spear 03, click the left hand, Add: Spear 03 in Manny's left hand",
         picked == ("Spear_03", "L") and got == ("Spear_03", "hand"),
         "picked %s held %s | %s" % (picked, got, status()))

    # ---- 5: the left column reads its grip - the right one's mirror
    left = column("L")
    gate(5, "the left column shows Spear 03's grip there (the mirror, not zeros)",
         left == shown("L") and any(v != "0" for v in left),
         "%s vs %s" % (left, shown("L")))

    # ---- 6: the Long Sword into the right hand, then its Rotate Y typed
    pick_item("LongSword_02")
    pick_hand("R")
    press_button("Add")
    weapon, _where = equip.occupant(root(), "R")
    _hand, bone = equip.bones(root(), "R")
    before_bone = cmds.xform(bone, query=True, worldSpace=True, matrix=True)
    old = float(panel().field("R", "ry").text())
    field = panel().field("R", "ry")
    field.setText(look.channel_text(old + 30.0))
    field.editingFinished.emit()
    settle()
    after_bone = cmds.xform(bone, query=True, worldSpace=True, matrix=True)
    entry = window.catalog.by_key("LongSword_02")
    rotate, translate = bonedrive.measured_grip(weapon, bone)
    rotate, translate = grips.standard(rotate, translate, bonedrive.frame_of(weapon), entry)
    stored = grips.stored("LongSword_02", "R")
    gate(6, "Rotate Y typed in the right column turns the sword in the hand, the bone "
            "stays, the value reads back and is remembered",
         held("R") == ("LongSword_02", "hand")
         and dist(before_bone, after_bone) < 1e-6
         and abs(rotate[1] - (old + 30.0)) < 1e-3
         and stored is not None and abs(stored[0][1] - (old + 30.0)) < 1e-6
         and panel().field("R", "ry").text() == look.channel_text(old + 30.0),
         "ry %.3f -> grip %s bone moved %.2e stored %s field %s | %s" % (
             old, ["%.3f" % v for v in rotate], dist(before_bone, after_bone),
             stored, panel().field("R", "ry").text(), status()))

    # ---- 7: Remove on the right hand
    pick_hand("R")
    press_button("Remove Weapon")
    gate(7, "Remove Weapon takes the right hand's sword off, the left keeps Spear 03",
         held("R") == (None, None) and held("L") == ("Spear_03", "hand")
         and not cmds.objExists(weapon),
         "R %s L %s | %s" % (held("R"), held("L"), status()))

    # ---- 8: the Dagger dropped onto the projected right hand
    from maya_scenesetup import skeleton
    hand_r = skeleton.resolve_bone(root(), "hand_r")
    point = cmds.xform(hand_r, query=True, worldSpace=True, translation=True)
    target = to_global(point)
    print("   ", keep_hub_off([target]))
    target = to_global(point)
    text = panel().drop_at(target[0], target[1], ("grid", "Dagger_01"))
    gate(8, "the Dagger dropped onto the projected right hand goes into it",
         held("R") == ("Dagger_01", "hand"), "%s at %s | %s" % (text, target, held("R")))

    # ---- 9: the Colour section repaints the selected weapon only
    dagger, _w = equip.occupant(root(), "R")
    body = [s for s in colour.character_meshes(root())]

    def worn(shapes):
        out = set()
        for shape in shapes:
            for group in cmds.listConnections(shape, type="shadingEngine") or []:
                for material in cmds.listConnections(group + ".surfaceShader") or []:
                    out.add(tuple(round(v, 4) for v in cmds.getAttr(material + ".color")[0]))
        return out
    body_before = worn(maya_colour.without_weapons(body))
    cmds.select(dagger, replace=True)
    rgb = colour.PALETTE[5].rgb
    said = maya_colour.paint(rgb)
    dagger_shapes = colour.mesh_shapes([dagger])
    gate(9, "Colour paints the selected dagger and leaves Manny as he was",
         worn(dagger_shapes) == set([tuple(round(v, 4) for v in rgb)])
         and worn(maya_colour.without_weapons(body)) == body_before,
         "%s | dagger %s body %s" % (said, worn(dagger_shapes), body_before))
    cmds.select(clear=True)


def phase_photo():
    import maya_hub
    if not os.path.isdir(SHOTS):
        os.makedirs(SHOTS)
    maya_hub.focus("weapons")
    settle()
    c = card()
    path = os.path.join(SHOTS, "weapons_card.png")
    c.grab().save(path)
    p = panel()
    p.grab().save(os.path.join(SHOTS, "weapons_panel.png"))
    print("saved", path, c.size())


def phase_classic():
    import maya_hub
    maya_hub.set_classic(True)
    print("asked for the classic hub")


def phase_classic2():
    import maya_hub
    import maya_hubqt
    from maya_scenesetup import window
    settle()
    p = panel()
    host = maya_hubqt.find(window._INVENTORY, layout=True)
    ok = (not maya_hub.is_skinned() and p is not None and host is not None
          and host.height() == p.height_for(host.width()) > 0 and p.isVisible()
          and len(p.fields) == 12)
    gate(10, "the inventory stands in the classic hub too", ok,
         "host %s panel %s" % ((host.width(), host.height()) if host else None,
                               p.geometry() if p else None))
    maya_hub.set_classic(False)


{"card": phase_card, "hands": phase_hands, "photo": phase_photo,
 "classic": phase_classic, "classic2": phase_classic2}[PHASE]()
print("%s: %s" % (PHASE, "FAILURES %s" % FAILED if FAILED else "all gates passed"))
