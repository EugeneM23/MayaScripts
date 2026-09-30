"""Live proof: Open scene on the right button (2026-09-30).

Runs in a DISPOSABLE GUI Maya (it opens scenes - never the animator's), sent
phase by phase over its command port, the repo's plugin first on sys.path:

    PHASE = "setup" | "check" | "rig" | "cancel" | "dontsave" | "skeleton"
            | "weapon" | "slot" | "end"

Each press is the real one: a right-button QMouseEvent sent to the Characters
grid or the Weapons inventory, the real QMenu found while its exec() runs
(QApplication.activePopupWidget), photographed, its row activated by Return
(or closed by Escape), and Maya's own «save changes?» dialog answered by
clicking its button. What is measured is the scene that results.

Spec: docs/superpowers/specs/2026-09-30-open-scene-menu-design.md
"""

import os
import sys
import tempfile

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if sys.path[:1] != [REPO]:
    sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

PHASE = globals().get("PHASE", "check")
PHOTOS = globals().get("PHOTOS") or tempfile.gettempdir()
PORTRAITS = "mayaSceneSetupPortraits"
INVENTORY = "mayaSceneSetupInventory"
CHAR_LINE = "mayaSceneSetupCharacterStatus"
WEAPON_LINE = "mayaSceneSetupStatus"

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("[{0}] {1}{2}".format("PASS" if ok else "FAIL", name,
                                (" - " + str(detail)) if detail != "" else ""))


def purge():
    for name in list(sys.modules):
        if name.startswith("maya_") or name in ("skeldar_features", "install"):
            sys.modules.pop(name, None)


def qt():
    from PySide6 import QtCore, QtGui, QtWidgets
    return QtCore, QtGui, QtWidgets


def line(control):
    try:
        return cmds.text(control, query=True, label=True) or ""
    except Exception as exc:                                 # noqa: BLE001
        return "<{0}>".format(exc)


def scene():
    return (cmds.file(query=True, sceneName=True) or "").replace("\\", "/")


def press_dialog(text, seen, tries=40):
    """Click `text` on Maya's modal «save changes?», retrying until it is up."""
    QtCore, _QtGui, QtWidgets = qt()
    modal = QtWidgets.QApplication.activeModalWidget()
    if modal is None:
        if tries > 0:
            QtCore.QTimer.singleShot(150, lambda: press_dialog(text, seen, tries - 1))
        else:
            seen["dialog"] = None
        return
    buttons = modal.findChildren(QtWidgets.QAbstractButton)
    seen["dialog"] = modal.windowTitle()
    seen["dialog_buttons"] = [b.text() for b in buttons]

    def norm(label):
        return label.replace("&", "").replace("\u2019", "'").strip().lower()
    for button in buttons:
        if norm(button.text()) == norm(text):
            button.click()
            seen["clicked"] = button.text()
            return
    seen["clicked"] = None


def right_click(widget, x, y, choose=None, dialog=None, photo=None):
    """The right button at local (x, y) on `widget`; the menu that opens is
    read (and photographed), then `choose` activated or the menu closed."""
    QtCore, QtGui, QtWidgets = qt()
    Qt = QtCore.Qt
    seen = {}

    def key(menu, which):
        QtWidgets.QApplication.sendEvent(
            menu, QtGui.QKeyEvent(QtCore.QEvent.KeyPress, which, Qt.NoModifier))

    def probe():
        menu = QtWidgets.QApplication.activePopupWidget()
        if menu is None:
            seen["menu"] = None
            return
        seen["menu"] = menu.metaObject().className()
        seen["rows"] = [(a.text(), a.isEnabled(), a.isSeparator())
                        for a in menu.actions()]
        if photo:
            menu.grab().save(os.path.join(PHOTOS, photo))
        target = None
        for action in menu.actions():
            if choose and action.text() == choose and action.isEnabled():
                target = action
        if target is None:
            key(menu, Qt.Key_Escape)
            return
        if dialog:
            QtCore.QTimer.singleShot(300, lambda: press_dialog(dialog, seen))
        menu.setActiveAction(target)
        key(menu, Qt.Key_Return)

    QtCore.QTimer.singleShot(300, probe)
    local = QtCore.QPoint(int(x), int(y))
    glob = widget.mapToGlobal(local)
    event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(local),
                              QtCore.QPointF(glob), Qt.RightButton, Qt.RightButton,
                              Qt.NoModifier)
    QtWidgets.QApplication.sendEvent(widget, event)
    return seen


def grid():
    import maya_chargrid
    return maya_chargrid.live(PORTRAITS)


def panel():
    import maya_inventory
    return maya_inventory.live(INVENTORY)


def tile(index):
    x, y, w, h = grid().rects()[index]
    return x + w // 2, y + h // 2


def item(key):
    import maya_invlook as look
    p = panel()
    rects = p.rects()
    x, y, w, h = look.item_rect(rects, p.placements[key], p.cells[key], rects["cell"])
    return x + w // 2, y + h // 2


def kind(which):
    """Click the card's Rig / Skeleton segment (its Qt button: trap 116)."""
    import maya_hubqt
    button = maya_hubqt.find("mayaSceneSetupCharacterKind_" + which)
    button.click()
    return grid().kind


def asset(name):
    return REPO + "/assets/" + name


def textures_on_plugin():
    from maya_scenesetup import colour
    nodes = [n for n in cmds.ls(type="file") or []
             if cmds.attributeQuery(colour.ASSET_IMAGE, node=n, exists=True)]
    paths = [cmds.getAttr(n + ".fileTextureName").replace("\\", "/") for n in nodes]
    good = [p for p in paths if p.startswith(REPO + "/assets/") and os.path.isfile(p)]
    return len(nodes), len(good)


# ------------------------------------------------------------------ phases

def setup():
    purge()
    cmds.file(new=True, force=True)
    for plugin in ("fbxmaya", "matrixNodes", "quatNodes"):
        try:
            cmds.loadPlugin(plugin, quiet=True)
        except Exception:                                    # noqa: BLE001
            pass
    import maya_hub
    maya_hub.show("characters")
    maya_hub.show("weapons")
    print("hub shown from", maya_hub.__file__)


def check():
    import maya_chargrid
    g, p = grid(), panel()
    gate("the grid stands, from the repo", g is not None and g.width() > 100
         and maya_chargrid.__file__.replace("\\", "/").startswith(REPO),
         (g.width() if g else None, maya_chargrid.__file__))
    gate("the inventory stands", p is not None and p.width() > 100,
         p.width() if p else None)


def rig():
    from maya_scenesetup import catalog
    gate("the switch shows Rig", kind("rig") == "rig")
    seen = right_click(grid(), *tile(0), choose="Open scene",
                       photo="open_scene_portrait.png")
    gate("a right press on Manny shows one row, Open scene", seen.get("rows")
         == [("Open scene", True, False)], seen)
    want = catalog.character_file(catalog.character_for("Manny", "rig"))
    gate("Manny_Rig.ma is the scene", scene() == want, scene())
    gate("the rig stands in the root namespace (the file, not an Add)",
         cmds.objExists("Main") and cmds.objExists("ControlSet"))
    gate("the scene reads unmodified", not cmds.file(query=True, modified=True))
    count, good = textures_on_plugin()
    gate("every shipped image on the plugin's copy", count > 0 and good == count,
         (count, good))
    text = line(CHAR_LINE)
    gate("the line names the file and warns", text.startswith(
        "Opened Manny [rig] - assets/Manny_Rig.ma") and "Save As" in text, text)


def cancel():
    import maya_scenesetup.opener as opener
    before = scene()
    loc = cmds.spaceLocator(name="openSceneVerify_loc")[0]
    gate("a change makes the scene modified", cmds.file(query=True, modified=True))
    seen = right_click(grid(), *tile(1), choose="Open scene", dialog="Cancel")
    gate("Maya asked to save, Cancel clicked", seen.get("clicked") and
         seen.get("dialog") is not None, seen)
    gate("nothing changed: the same scene, the locator there",
         scene() == before and cmds.objExists(loc), scene())
    gate("the line says cancelled", line(CHAR_LINE) == opener.CANCELLED,
         line(CHAR_LINE))


def dontsave():
    from maya_scenesetup import catalog
    seen = right_click(grid(), *tile(1), choose="Open scene", dialog="Don't Save")
    gate("Maya asked to save, Don't Save clicked", seen.get("clicked"), seen)
    want = catalog.character_file(catalog.character_for("Creep", "rig"))
    gate("Creep_Rig.ma is the scene, the change gone", scene() == want
         and not cmds.objExists("openSceneVerify_loc"), scene())


def skeleton():
    from maya_scenesetup import catalog
    gate("the switch shows Skeleton", kind("skeleton") == "skeleton")
    seen = right_click(grid(), *tile(1), choose="Open scene")
    want = catalog.character_file(catalog.character_for("Creep", "skeleton"))
    gate("Creep [skeleton] opens its own file, no question asked",
         scene() == want and "dialog" not in seen, (scene(), seen))
    seen = right_click(grid(), *tile(2), choose="Open scene",
                       photo="open_scene_dimmed.png")
    gate("Orc D (no skeleton) shows the row disabled",
         seen.get("rows") == [("Open scene (no skeleton)", False, False)], seen)
    gate("... and opens nothing", scene() == want, scene())
    kind("rig")


def weapon():
    mel.eval("FBXImportMode -v exmerge")
    seen = right_click(panel(), *item("Spear_03"), choose="Open scene",
                       photo="open_scene_weapon.png")
    rows = [(t, s) for t, _e, s in seen.get("rows") or []]
    gate("a right press on Spear 03: Open scene, a separator, Sort",
         rows == [("Open scene", False), ("", True), ("Sort the inventory", False)],
         seen)
    gate("Spear_03.fbx is the scene", scene() == asset("Spear_03.fbx"), scene())
    meshes = cmds.ls(type="mesh", noIntermediate=True) or []
    gate("the spear's mesh came in under the exmerge a bridge leaves",
         len(meshes) > 0, meshes)
    gate("the import mode is put back",
         (mel.eval("FBXImportMode -q") or "").strip() == "exmerge",
         mel.eval("FBXImportMode -q"))
    text = line(WEAPON_LINE)
    gate("the Weapons line names the file", text.startswith(
        "Opened Spear 03 - assets/Spear_03.fbx"), text)


def slot():
    from maya_scenesetup import catalog, equip, skeleton as sk, window
    cmds.file(modified=False)
    window.open_character_scene("Manny", "rig")
    root = sk.current_root()
    print(equip.to_hand(root, "R", catalog.by_key("Dagger_01")))
    p = panel()
    p.refresh()
    x, y, w, h = p.rects()["well_R"]
    seen = right_click(p, x + w // 2, y + h // 2)
    gate("a right press on the right hand holding the dagger: Open scene",
         seen.get("rows") == [("Open scene", True, False)], seen)
    x, y, w, h = p.rects()["well_L"]
    seen = right_click(p, x + w // 2, y + h // 2)
    gate("the empty left hand opens no menu", seen.get("rows") is None, seen)


def end():
    cmds.file(new=True, force=True)


{"setup": setup, "check": check, "rig": rig, "cancel": cancel,
 "dontsave": dontsave, "skeleton": skeleton, "weapon": weapon,
 "slot": slot, "end": end}[PHASE]()
print("PHASE {0}: {1} of {2} gates failed".format(
    PHASE, RESULTS.count(False), len(RESULTS)))
