"""verify_inventory_live.py - two weapons in Connections, and the inventory window's
drop onto a hand and onto the floor, in a LIVE Maya (2026-09-29).

Send through the command port of a DISPOSABLE Maya (CLAUDE.md, "Driving the user's live
Maya"; a scratch MAYA_APP_DIR, its own port, killed afterwards) - never the animator's scene:
it adds a rig, puts weapons in and out of hands and drops them on the floor. Live, not
standalone: OverRig's parent_in/out (Connections' lift and hang) read the time slider, and the
drop needs a real model panel to project through.

In STAGES, one send each (a grab in the same send as the change that altered the layout
photographs the old layout - trap 68): set STAGE in the globals the runner passes, or it runs
"setup". Stages: "setup" (rig, two weapons, Connections gates, the inventory and the hub
open), "photo" (grabs to PHOTO_DIR), "drops" (drop_at onto the projected left hand, a slot onto
the grid, onto the floor, slot to slot).

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""
import os
import sys

import maya.cmds as cmds
import maya.api.OpenMaya as om

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)
STAGE = globals().get("STAGE", "setup")
PHOTO_DIR = globals().get("PHOTO_DIR", os.path.join(os.environ.get("TEMP", "C:/Temp"), "skeldar_inventory"))
STATE = sys.modules.setdefault("_skeldar_inventory_live", type(sys)("_skeldar_inventory_live"))
FAILED, PASSED = [], []


def gate(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("%s %s%s" % ("ok  " if ok else "FAIL", name, (" - " + str(detail)) if detail else ""))


def lowest(node):
    low = None
    for mesh in cmds.listRelatives(node, allDescendents=True, type="mesh", fullPath=True) or []:
        if cmds.getAttr(mesh + ".intermediateObject"):
            continue
        fn = om.MFnMesh(om.MSelectionList().add(mesh).getDagPath(0))
        ys = [p.y for p in fn.getPoints(om.MSpace.kWorld)]
        low = min(ys) if low is None else min(low, min(ys))
    return low


def middle_xz(node):
    box = cmds.exactWorldBoundingBox(node)
    return ((box[0] + box[3]) / 2.0, (box[2] + box[5]) / 2.0)


def setup():
    for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
        try:
            cmds.loadPlugin(plugin, quiet=True)
        except Exception:
            pass
    cmds.file(new=True, force=True)
    import maya_rigs
    from maya_scenesetup import attach, catalog, character, connections as cx, equip
    from maya_scenesetup import bonedrive, grips, weaponspace
    for entry in catalog.WEAPONS:              # a disposable Maya: its grips are ours
        for side in ("R", "L"):
            name = grips.optionvar_name(entry.key, side)
            if cmds.optionVar(exists=name):
                cmds.optionVar(remove=name)
    character.add_character(catalog.character_by_key("Manny_Rig"))
    rig = maya_rigs.rigs()[0]
    root = rig.skeleton_root
    STATE.rig, STATE.root = rig, root
    sword, dagger = catalog.by_key("LongSword_02"), catalog.by_key("Dagger_01")
    print(equip.to_hand(root, "R", sword))
    print(equip.to_hand(root, "L", dagger))
    bones = cx.bones_of(rig)
    s, d = attach.find_attached(bones["R"][0]), attach.find_attached(bones["L"][0])
    s, d = cmds.ls(s, long=True)[0], cmds.ls(d, long=True)[0]
    su, du = cmds.ls(s, uuid=True)[0], cmds.ls(d, uuid=True)[0]
    now = lambda uuid: cmds.ls(uuid, long=True)[0]
    cmds.select(clear=True)
    gate("the rig's two weapons, right hand first", cx.weapons_of(rig) == [s, d], cx.weapons_of(rig))
    text = cx.apply({"L": cx.HOLDS, "R": None}, rig, weapon=s)
    gate("the sword into the left hand is refused: the dagger hangs there",
         text == "Hand_L holds the Dagger 01 - move it first"
         and weaponspace.holding_hand(now(su)) == bones["R"][0], text)
    text = cx.apply({"L": cx.FOLLOWS, "R": cx.HOLDS}, rig, weapon=s)
    gate("the left hand following the sword is refused while it holds the dagger",
         text == "Hand_L holds the Dagger 01 - move it first", text)
    text = cx.apply({"L": None, "R": None}, rig, weapon=d)
    gate("the dagger lifted to world, still driving weapon_l",
         text.startswith("Applied") and not bonedrive.is_held(now(du))
         and bonedrive.driving_weapon(bones["L"][1]) == now(du), text)
    text = cx.apply({"L": cx.HOLDS, "R": None}, rig, weapon=s)
    gate("the sword into the left hand is refused: the dagger drives weapon_l from world",
         text.startswith("weapon_l is driven by the Dagger 01 (in world)"), text)
    text = cx.apply({"L": cx.FOLLOWS, "R": cx.HOLDS}, rig, weapon=s)
    gate("the left hand follows the sword",
         text.startswith("Applied") and cx.following(rig, "L") == now(su)
         and cx.read_scheme(rig, weapon=now(su)) == {"R": cx.HOLDS, "L": cx.FOLLOWS}
         and cx.read_scheme(rig, weapon=now(du)) == {"R": None, "L": None}, text)
    text = equip.to_hand(root, "L", dagger)
    gate("the inventory will not put a weapon into a hand that follows one",
         text == "the left hand follows the Long Sword 02 - release it in Connections first"
         and cmds.objExists(now(du)), text)
    import maya_hub
    maya_hub.show("connections")          # the section as the animator sees it
    header = cx.refresh()
    labels = [cmds.iconTextRadioButton(cx.chooser_segment(i), query=True, label=True) for i in (0, 1)]
    gate("the panel's chooser names both weapons and the header the other one",
         labels == ["Long Sword 02", "Dagger 01"] and "also Dagger 01 in world" in header,
         "%s | %s" % (labels, header))
    cx._chooser_picked(1)()
    header = cmds.text(cx.HEADER, query=True, label=True)
    gate("picking the dagger in the chooser moves the rows onto it", "DaggerMesh" in header, header)
    cmds.select(now(su))
    gate("selecting the sword names it", cx.chosen_weapon(rig) == now(su))
    cmds.select(clear=True)
    cx._PICKED["uuid"] = None
    text = cx.apply({"R": cx.HOLDS, "L": None}, rig, weapon=now(su))
    text2 = cx.apply({"L": cx.HOLDS, "R": None}, rig, weapon=now(du))
    gate("released, then the dagger hung back into the left hand driving weapon_l",
         weaponspace.holding_hand(now(du)) == bones["L"][0]
         and bonedrive.driving_weapon(bones["L"][1]) == now(du)
         and weaponspace.holding_hand(now(su)) == bones["R"][0], "%s | %s" % (text, text2))

    from maya_scenesetup import window as ww
    maya_hub.show("weapons")
    cmds.iconTextRadioButton(ww.hand_segment("L"), edit=True, select=True)
    ww.refresh()
    status = cmds.text("mayaSceneSetupStatus", query=True, label=True)
    gate("the Weapons section's Left hand reads the dagger", ww.side() == "L" and "Dagger" in status,
         "%s / %s" % (ww.side(), status))
    import maya_inventory
    inv = maya_inventory.show()
    inv.refresh()
    held = inv.holding
    gate("the inventory is open on the rig with both hands",
         inv.isVisible() and inv.name == "Manny_Rig" and held["R"].key == "LongSword_02"
         and held["L"].key == "Dagger_01", (inv.name, dict((k, (v.where, v.key)) for k, v in held.items())))
    cmds.select(rig.group)
    cmds.viewFit("persp", fitFactor=0.8)
    cmds.select(clear=True)
    cmds.refresh(force=True)


def photo():
    import maya_inventory
    inv = maya_inventory.live()
    if not os.path.isdir(PHOTO_DIR):
        os.makedirs(PHOTO_DIR)
    stamp = globals().get("PHOTO_TAG", "a")
    if inv:
        inv.grab().save(os.path.join(PHOTO_DIR, "inventory_%s.png" % stamp))
    import maya_hubqt
    q = maya_hubqt.qt()
    try:
        import maya.OpenMayaUI as omui
        ptr = omui.MQtUtil.findControl("skeldarAnimHub")
        if ptr:
            hub = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
            hub.grab().save(os.path.join(PHOTO_DIR, "hub_%s.png" % stamp))
    except Exception as error:
        print("hub photo:", error)
    try:
        cmds.playblast(frame=[cmds.currentTime(q=True)], format="image", compression="png",
                       completeFilename=os.path.join(PHOTO_DIR, "viewport_%s.png" % stamp),
                       viewer=False, showOrnaments=False, percent=60, widthHeight=(1280, 720),
                       forceOverwrite=True)
    except Exception as error:
        print("playblast:", error)
    print("photos in", PHOTO_DIR, os.listdir(PHOTO_DIR))


def global_of(view, world):
    import maya_hubqt
    q = maya_hubqt.qt()
    x, y = view.project(world)
    local = q.QtCore.QPoint(int(round(x / view.sx)), int(round(view.widget.height() - y / view.sy)))
    point = view.widget.mapToGlobal(local)
    return point.x(), point.y()


def drops():
    import maya_hubqt
    import maya_inventory
    from maya_scenesetup import attach, bonedrive, catalog, droptarget, equip
    q = maya_hubqt.qt()
    rig, root = STATE.rig, STATE.root
    inv = maya_inventory.live()
    bones = dict((s, equip.bones(root, s)) for s in ("R", "L"))
    view = None
    for panel in cmds.getPanel(type="modelPanel"):
        if cmds.modelPanel(panel, query=True, camera=True).split("|")[-1] in ("persp", "perspShape"):
            import maya.api.OpenMayaUI as omui
            v = omui.M3dView.getM3dViewFromModelPanel(panel)
            w = q.shiboken.wrapInstance(int(v.widget()), q.QtWidgets.QWidget)
            if w.isVisible():
                view = droptarget.Viewport(panel, v, w)
                break
    gate("a perspective viewport to drop into", view is not None)
    if view is None:
        return
    cmds.select(rig.group)
    cmds.viewFit(cmds.modelPanel(view.panel, query=True, camera=True), fitFactor=0.8)
    cmds.select(clear=True)
    cmds.refresh(force=True)
    # keep the inventory off the points we drop on
    inv.move(-20000, -20000)
    hand_l = cmds.xform(bones["L"][0], query=True, worldSpace=True, translation=True)
    gx, gy = global_of(view, hand_l)
    aim = droptarget.target(gx, gy, droptarget.snapshot(), inv.k)
    gate("the cursor on the projected left hand aims at the left hand",
         aim.get("kind") == "hand" and aim.get("side") == "L" and aim.get("root") == root, aim.get("text"))
    text = inv.drop_at(gx, gy, ("grid", "Spear_03"))
    held = equip.holdings(root)
    gate("Spear 03 dropped on the left hand from the grid: into the left hand, the dagger replaced",
         held["L"].where == "hand" and held["L"].key == "Spear_03" and held["R"].key == "LongSword_02", text)
    grid = inv.rects["grid"]
    g = inv.mapToGlobal(q.QtCore.QPoint(int(grid[0]) + 5, int(grid[1]) + 5))
    text = inv.drop_at(g.x(), g.y(), ("slot", "L"))
    gate("the left slot dropped on the grid: taken off", equip.holdings(root)["L"].where is None
         and not bonedrive.driving_weapon(bones["L"][1]), text)
    here = cmds.xform(root, query=True, worldSpace=True, translation=True)
    target = (here[0] + 80.0, 0.0, here[2] + 60.0)
    gx, gy = global_of(view, target)
    text = inv.drop_at(gx, gy, ("grid", "Spear_01"))
    spear = bonedrive.driving_weapon(bones["L"][1])
    gate("Spear 01 dropped on the floor: the left bone (the free one) follows it", bool(spear)
         and not bonedrive.is_held(spear) and bonedrive.is_parked(spear), text)
    if spear:
        mx, mz = middle_xz(spear)
        off = ((mx - target[0]) ** 2 + (mz - target[2]) ** 2) ** 0.5
        low = lowest(spear)
        gate("it lies where the cursor was, flat on the floor",
             off < 3.0 and low is not None and abs(low) < 1e-3,
             "%.3f cm from the point, lowest vertex %.6f" % (off, low))
    slot_l = inv.rects["slot_L"]
    g = inv.mapToGlobal(q.QtCore.QPoint(int(slot_l[0]) + 5, int(slot_l[1]) + 5))
    text = inv.drop_at(g.x(), g.y(), ("slot", "R"))
    held = equip.holdings(root)
    gate("the right slot dropped on the left slot: the sword moved into the left hand, the floor spear gone",
         held["L"].key == "LongSword_02" and held["L"].where == "hand" and held["R"].where is None
         and (not spear or not cmds.objExists(spear)), text)
    sword = attach.find_attached(bones["L"][0])
    near = (om.MVector(*cmds.xform(sword, query=True, worldSpace=True, translation=True))
            - om.MVector(*cmds.xform(bones["L"][1], query=True, worldSpace=True, translation=True))).length()         if sword else 999.0
    gate("...and it hangs AT the left hand: the mirror grip was read from weapon_l's own socket, "
         "not from the floor spear it followed", near < 20.0, "%.3f cm from weapon_l" % near)
    inv.move(40, 40)
    inv.refresh()


if STAGE == "setup":
    setup()
elif STAGE == "photo":
    photo()
elif STAGE == "drops":
    drops()
print("STAGE %s: %d of %d gates failed %s" % (STAGE, len(FAILED), len(FAILED) + len(PASSED), FAILED))
