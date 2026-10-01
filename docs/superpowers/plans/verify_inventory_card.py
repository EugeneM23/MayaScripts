"""Live proof of the Inventory card: Weapon and Armor in one, tiles everywhere (2026-10-01).

«объеденим вкладки weapon и армор в одну inventory ... для wepon раздела уберем функционал
сетчатого инвентаря ... Пусть все будет конссистентно». Run in a DISPOSABLE Maya (it adds a rig,
equips it): its own MAYA_APP_DIR, MAYA_NO_HOME=1, its own port. Each send sets PHASE first:

    PHASE = "card"   gates 1-4: Inventory right after Animation Setup, no Armor card,
                     show("armor") opening and lighting it; the four headings; the Inventory card
                     top down (Weapon, the hands and tiles, Equip / Unequip, Armor, its tiles,
                     Equip / Unequip, ONE status line); the content within the animator's dock;
                     the weapon panel's tiles - every catalog row, no grid left
    PHASE = "drops"  gates 5-7: a weapon tile dropped (drop_at, the panel's own release) onto a
                     Manny rig's right hand in the viewport, then Spear 01 onto the floor, then
                     the right hand card onto the tiles - into the hand, on the floor (the left
                     bone following it), taken off; the «equipped» pills following
    PHASE = "armor_drag" gate 8: the Tech Limb tile pressed, dragged and released through Qt on
                     the rig's spine - worn, the caption naming the rig
    PHASE = "photo"  the Inventory card photographed

Spec: docs/superpowers/specs/2026-10-01-inventory-card-design.md
"""

import os
import sys

REPO = globals().get("REPO", "C:/!!!Work/MayaScripts/SkeldarAnim")
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402

PHASE = globals().get("PHASE", "card")
FAILED = []
WORLD = sys.__dict__.setdefault("_verify_inventory_card", {})
SHOTS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
VIEWPORT = 510


def gate(number, text, ok, detail=""):
    print("gate %2d %s  %s  %s" % (number, "PASS" if ok else "FAIL", text, detail))
    if not ok:
        FAILED.append(number)


def settle():
    import maya_hubqt
    q = maya_hubqt.qt()
    for _ in range(3):
        q.QtWidgets.QApplication.processEvents()
    cmds.refresh(force=True)


def world_t(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def card(key):
    import maya_hub
    return maya_hub._SKIN.cards[key].frame


def panel():
    import maya_inventory
    return maya_inventory.live()


def tiles():
    import maya_armorgrid
    from maya_scenesetup import armorpanel
    return maya_armorgrid.live(armorpanel._TILES)


def status():
    from maya_scenesetup import window
    return cmds.text(window._STATUS, query=True, label=True) or ""


def show_maya():
    import maya_hubqt
    q = maya_hubqt.qt()
    for top in q.QtWidgets.QApplication.topLevelWidgets():
        if top.objectName() == "MayaWindow" and (top.isMinimized() or not top.isVisible()):
            top.showMaximized()
    settle()


def to_global(world):
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
    import maya_hubqt
    if not any(maya_hubqt.on_hub(x, y) for x, y in points):
        return "the hub stands clear"
    top = maya_hubqt.find("skeldarAnimHub").window()
    screen = top.screen().availableGeometry()
    for x, y in [(screen.left(), screen.top()), (screen.right() - top.width(), screen.top()),
                 (screen.left(), screen.bottom() - top.height()),
                 (screen.right() - top.width(), screen.bottom() - top.height())]:
        top.move(x, y)
        settle()
        if not any(maya_hubqt.on_hub(px, py) for px, py in points):
            return "hub moved to %s" % (top.pos(),)
    return "the hub covers a point wherever it stands"


def bone(root, name):
    for joint in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                              fullPath=True) or []):
        if joint.split("|")[-1].split(":")[-1] == name:
            return joint
    return None


def holdings(root):
    from maya_scenesetup import equip
    return dict((side, (h.where, h.key)) for side, h in equip.holdings(root).items())


# ------------------------------------------------------------------ phases

def phase_card():
    import maya_hub
    import maya_hubqt
    from maya_scenesetup import armorpanel
    from maya_scenesetup import window as scene
    from maya_uebridge import window as bridge
    cmds.file(new=True, force=True)
    maya_hub.show("armor")
    settle()
    skin = maya_hub._SKIN
    column = skin.column
    cards = []
    for i in range(column.count()):
        widget = column.itemAt(i).widget()
        name = widget.objectName() if widget is not None else ""
        if name.startswith("skeldarHubCard_"):
            cards.append(name.split("_", 1)[1])
    gate(1, "Inventory right after Animation Setup, no Armor card; show('armor') opened and lit it",
         cards[:3] == ["characters", "weapons", "connections"] and "armor" not in skin.cards
         and maya_hub.section("weapons").label == "Inventory"
         and not skin.cards["weapons"].collapsed() and skin.active == "weapons",
         "cards %s | active %s" % (cards[:4], skin.active))

    q = maya_hubqt.qt()
    cmds.workspaceControl(maya_hub.CONTROL, edit=True, floating=True)
    settle()
    top = maya_hubqt.find(maya_hub.CONTROL).window()
    scroll = None
    for _ in range(4):
        scroll = [a for a in maya_hubqt.find(maya_hub.CONTROL).findChildren(
            q.QtWidgets.QScrollArea) if a.objectName() == "skeldarHubScrollArea"][0]
        top.resize(top.width() + (VIEWPORT - scroll.viewport().width()), max(top.height(), 900))
        settle()
    maya_hub.expand("characters")
    settle()

    heads = {}
    for name in (scene._CHARACTERS_HEADING, bridge._HEADING, scene._WEAPON_HEADING,
                 armorpanel._HEADING):
        widget = maya_hubqt.find(name)
        heads[name] = (widget.property("text") if widget is not None else None,
                       widget.property("skRole") if widget is not None else None)
    gate(2, "the four headings, each a heading: Characters, UE Connect, Weapon, Armor",
         [v[0] for v in heads.values()] == ["Characters", "UE Connect", "Weapon", "Armor"]
         and all(v[1] == "heading" for v in heads.values()), "%s" % heads)

    frame = card("weapons")

    def y_of(name, layout=False):
        widget = maya_hubqt.find(name, layout)
        return None if widget is None else widget.mapTo(frame, q.QtCore.QPoint(0, 0)).y()

    buttons = [(b.text(), b.mapTo(frame, q.QtCore.QPoint(0, 0)).y(), b.property("skRole"))
               for b in frame.findChildren(q.QtWidgets.QPushButton) if b.text()]
    buttons.sort(key=lambda b: b[1])
    ys = [y_of(scene._WEAPON_HEADING), y_of(scene._INVENTORY, True),
          y_of(armorpanel._HEADING), y_of(armorpanel._TILES, True), y_of(scene._STATUS)]
    lines = [w.objectName() for w in frame.findChildren(q.QtWidgets.QWidget)
             if w.objectName() in (scene._STATUS, "mayaSceneSetupArmorStatus")]
    labels = [b[0] for b in buttons]
    ordered = None not in ys and ys == sorted(ys)
    between = (labels == ["Equip", "Unequip", "Equip", "Unequip"]
               and ys[1] < buttons[0][1] < ys[2] < ys[3] < buttons[2][1] < ys[4])
    content = skin.content.minimumSizeHint().width()
    gate(3, "the Inventory top down: Weapon, the panel, Equip / Unequip, Armor, its tiles, "
            "Equip / Unequip, one line; the two Equips orange; within the dock",
         ordered and between and lines == [scene._STATUS]
         and [b[2] for b in buttons] == ["primary", "danger", "primary", "danger"]
         and content <= scroll.viewport().width(),
         "y %s | buttons %s | lines %s | content %d <= %d" % (
             ys, buttons, lines, content, scroll.viewport().width()))

    p = panel()
    from maya_scenesetup import catalog
    gate(4, "the weapon panel holds a tile per catalog row and no grid",
         p is not None and p.keys == [e.key for e in catalog.WEAPONS]
         and len(p.rects()["tiles"]) == len(catalog.WEAPONS)
         and not hasattr(p, "placements") and not hasattr(p, "sort"),
         "keys %s" % (p.keys if p else None))
    cmds.workspaceControl(maya_hub.CONTROL, edit=True, restore=True)


def phase_drops():
    import maya_hub
    import maya_rigs
    from maya_scenesetup import catalog, character
    cmds.file(new=True, force=True)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]
    root = rig.skeleton_root
    WORLD["root"] = root
    cmds.select(rig.main, replace=True)
    cmds.viewPlace("persp", eye=(0.0, 150.0, 420.0), lookAt=(0.0, 100.0, 0.0))
    show_maya()
    maya_hub.focus("weapons")
    settle()
    p = panel()
    p.refresh()
    hand = to_global(world_t(bone(root, "hand_r")))
    floor = to_global((-90.0, 0.0, 60.0))
    print("   ", keep_hub_off([hand, floor]))
    hand = to_global(world_t(bone(root, "hand_r")))
    floor = to_global((-90.0, 0.0, 60.0))
    said = p.drop_at(hand[0], hand[1], ("tile", "LongSword_02"))
    p.refresh()
    held = holdings(root)
    import maya_invlook as look
    from maya_scenesetup import equip
    pills = look.worn(equip.holdings(root))
    gate(5, "a weapon tile dropped on the rig's right hand: into the right hand, its tile wears "
            "the pill",
         held.get("R") == ("hand", "LongSword_02") and pills == {"LongSword_02"},
         "'%s' | %s | pills %s" % (said, held, sorted(pills)))
    said = p.drop_at(floor[0], floor[1], ("tile", "Spear_01"))
    p.refresh()
    held = holdings(root)
    gate(6, "Spear 01 dropped on the floor: on the floor, the left bone following it",
         held.get("L") == ("floor", "Spear_01") and held.get("R") == ("hand", "LongSword_02"),
         "'%s' | %s" % (said, held))
    tile = p.tile_of("Dagger_01")
    point = p.mapToGlobal(p.rect().topLeft()) + __import__("maya_hubqt").qt().QtCore.QPoint(
        tile[0] + 5, tile[1] + 5)
    said = p.drop_at(point.x(), point.y(), ("slot", "R"))
    p.refresh()
    held = holdings(root)
    gate(7, "the right hand card dropped on the tiles: taken off, the floor spear left",
         held.get("R", (None,))[0] in (None, "", "none") and held.get("L") == ("floor", "Spear_01"),
         "'%s' | %s" % (said, held))


def phase_armor_drag():
    import maya_hubqt
    from maya_scenesetup import armor
    q = maya_hubqt.qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    E = QtCore.QEvent
    root = WORLD["root"]
    show_maya()
    grid = tiles()
    spine = to_global(world_t(bone(root, "spine_03")))
    print("   ", keep_hub_off([spine]))
    spine = QtCore.QPoint(*to_global(world_t(bone(root, "spine_03"))))
    grid = tiles()
    x, y, w, h = grid.rects()[0]
    start = QtCore.QPoint(x + w // 2, y + h // 2)

    def mouse(kind, local=None, global_point=None, button=QtCore.Qt.LeftButton,
              buttons=QtCore.Qt.LeftButton):
        global_point = global_point or grid.mapToGlobal(local)
        local = local if local is not None else grid.mapFromGlobal(global_point)
        event = QtGui.QMouseEvent(kind, QtCore.QPointF(local), QtCore.QPointF(global_point),
                                  button, buttons, QtCore.Qt.NoModifier)
        q.QtWidgets.QApplication.sendEvent(grid, event)

    mouse(E.MouseButtonPress, local=start)
    mouse(E.MouseMove, local=start + QtCore.QPoint(40, 0), button=QtCore.Qt.NoButton)
    mouse(E.MouseMove, global_point=spine, button=QtCore.Qt.NoButton)
    grid._caption(spine, force=True)
    caption = grid._drag["ghost"].text if grid._drag else ""
    mouse(E.MouseButtonRelease, global_point=spine, buttons=QtCore.Qt.NoButton)
    worn = armor.worn(root)
    gate(8, "the Tech Limb tile dragged through Qt onto the rig's spine: worn, the caption "
            "naming the rig",
         "Tech_Limb" in worn and caption.startswith("Tech Limb · onto ") and grid._drag is None,
         "caption '%s' | worn %s | '%s'" % (caption, sorted(worn), status()))


def phase_photo():
    import maya_hub
    maya_hub.focus("weapons")
    settle()
    frame = card("weapons")
    path = os.path.join(SHOTS, "inventory_card.png")
    frame.grab().save(path)
    print("saved", path, frame.size())


{"card": phase_card, "drops": phase_drops, "armor_drag": phase_armor_drag,
 "photo": phase_photo}[PHASE]()
print("%s: %s" % (PHASE, "FAILURES %s" % FAILED if FAILED else "all gates passed"))
