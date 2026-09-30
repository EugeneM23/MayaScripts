"""Live proof of the Characters portrait grid (2026-09-30).

Run in a DISPOSABLE Maya (it opens a new scene and adds characters): its own
MAYA_APP_DIR, MAYA_NO_HOME=1, the port 7004. Each send sets PHASE first:

    PHASE = "place"     gates 1-9: the card, the switch, drops, Add, Colour, a mouse drag
    PHASE = "deferred"  one drop queued with evalDeferred - outside the port's command,
                        the way a real release runs
    PHASE = "undo"      gate 10: a Ctrl+Z leaves that dropped character whole
    PHASE = "classic"   asks for the classic hub (deferred rebuild)
    PHASE = "classic2"  gate 11: the grid stands in the classic hub too; back to the skin

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""

import math
import sys

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402

PHASE = globals().get("PHASE", "place")
FAILED = []
WORLD = sys.__dict__.setdefault("_verify_character_grid", {})   # across sends


def gate(number, text, ok, detail=""):
    print("gate %2d %s  %s  %s" % (number, "PASS" if ok else "FAIL", text, detail))
    if not ok:
        FAILED.append(number)


def world_t(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def rig_namespaces():
    import maya_rigs
    return set(r.namespace for r in maya_rigs.rigs())


def skeleton_roots():
    from maya_overrig import builder
    return set(builder.character_roots())


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


def pick_kind(kind):
    """Click a Rig / Skeleton segment the way the animator does: the Qt
    button's click(). Measured 2026-09-30: `iconTextRadioButton -e -select`
    ran the onCommand in one hub and not in another - a scripted select is
    not a click."""
    import maya_hubqt
    from maya_scenesetup import window
    q = maya_hubqt.qt()
    widget = maya_hubqt.find(window.kind_segment(kind))
    button = q.shiboken.wrapInstance(int(q.shiboken.getCppPointer(widget)[0]),
                                     q.QtWidgets.QAbstractButton)
    button.click()
    q.QtWidgets.QApplication.processEvents()


def grid():
    import maya_chargrid
    from maya_scenesetup import window
    return maya_chargrid.live(window._PORTRAITS)


def settle():
    import maya_hubqt
    q = maya_hubqt.qt()
    q.QtWidgets.QApplication.processEvents()
    cmds.refresh(force=True)


def keep_hub_off(points):
    """Move a floating hub off every point a drop is aimed at."""
    import maya_chargrid
    import maya_hubqt
    scene = maya_chargrid.Scene()
    if not any(scene.over_hub(x, y) for x, y in points):
        return "the hub stands clear"
    host = maya_hubqt.find("skeldarAnimHub")
    top = host.window()
    screen = top.screen().availableGeometry()
    top.move(screen.left(), screen.top())
    settle()
    return "hub moved to %s" % (top.pos(),)


def phase_place():
    import maya_chargrid
    import maya_colour
    import maya_hub
    import maya_hubqt
    from maya_scenesetup import catalog
    from maya_scenesetup import droptarget
    from maya_scenesetup import window
    from maya_uebridge import fbxlayout

    cmds.file(new=True, force=True)
    maya_hub.show("characters")
    settle()
    cmds.viewPlace("persp", eye=(420.0, 380.0, 620.0), lookAt=(40.0, 60.0, -20.0))
    settle()

    # ---- 1: the card holds the grid
    g = grid()
    host = maya_hubqt.find(window._PORTRAITS, layout=True)
    card = maya_hubqt.find("skeldarHubCard_characters")
    inside = bool(card is not None and host is not None and card.isAncestorOf(host))
    loaded = g is not None and all(not g.pixmaps[m.key].isNull()
                                   for m in catalog.MODELS if m.key in g.pixmaps)
    gate(1, "the Characters card holds the portrait grid",
         maya_hub.is_skinned() and inside and loaded and g is not None
         and len(g.pixmaps) == len(catalog.MODELS)
         and host.height() == g.height_for(host.width()) > 0,
         "host %dx%d grid %s pixmaps %d" % (host.width(), host.height(),
                                            g.geometry() if g else None,
                                            len(g.pixmaps) if g else 0))

    # ---- 2: no colour in the card
    gone = [name for name in ("mayaSceneSetupCharacterColour",
                              "mayaSceneSetupCharDot0", window._CHARACTER)
            if cmds.control(name, exists=True)]
    gate(2, "no colour control and no dropdown in the card", not gone, gone)

    # ---- 3: the switch dims
    pick_kind("skeleton")
    skeleton = (g.kind, g.available("Orc_D"), g.available("UE4_Mannequin"))
    pick_kind("rig")
    rig = (g.kind, g.available("Orc_D"), g.available("UE4_Mannequin"))
    remembered = cmds.optionVar(query=window._KIND_OPTIONVAR)
    gate(3, "Skeleton dims Orc D, Rig dims the UE4 Mannequin (the segment's own onCommand)",
         skeleton == ("skeleton", False, True) and rig == ("rig", True, False)
         and remembered == "rig",
         "%s %s remembered %s" % (skeleton, rig, remembered))

    # ---- 4: the floor point under a projected cursor
    p1, p2, p3 = (150.0, 0.0, -80.0), (-140.0, 0.0, 70.0), (60.0, 0.0, 160.0)
    points = [to_global(p) for p in (p1, p2, p3)]
    print("   ", keep_hub_off(points))
    points = [to_global(p) for p in (p1, p2, p3)]
    aims = [droptarget.floor_at(*pt) for pt in points]
    errors = [dist(a["point"], p) if a.get("kind") == "floor" else 1e9
              for a, p in zip(aims, (p1, p2, p3))]
    gate(4, "floor_at under the projected points finds them (within 3 cm)",
         max(errors) < 3.0, ["%.3f" % e for e in errors])

    # ---- 5: Manny [rig] dropped at p1
    before = rig_namespaces()
    g.set_kind("rig")
    text = g.drop_at(points[0][0], points[0][1], "Manny")
    new = sorted(rig_namespaces() - before)
    main = cmds.ls(new[0] + ":Main", long=True)[0] if new else None
    placed = world_t(main) if main else None
    turned = cmds.getAttr(main + ".rotate")[0] if main else None
    gate(5, "Manny [rig] stands on the drop's floor point, unturned",
         bool(main) and dist(placed, aims[0]["point"]) < 1e-6
         and max(abs(v) for v in turned) < 1e-9,
         "%s | %s at %s" % (text, new, placed))

    # ---- 6: Creep [skeleton] dropped at p2: root moved, Armature not
    pick_kind("skeleton")
    roots_before = skeleton_roots()
    text = g.drop_at(points[1][0], points[1][1], "Creep")
    dropped = sorted(skeleton_roots() - roots_before)
    pick_kind("skeleton")
    roots_before = skeleton_roots()
    window.select_model("Creep")
    window.add_character()
    origin = sorted(skeleton_roots() - roots_before)
    ok = len(dropped) == 1 and len(origin) == 1
    if ok:
        shift = [world_t(dropped[0])[i] - world_t(origin[0])[i] for i in range(3)]
        want = (aims[1]["point"][0], 0.0, aims[1]["point"][2])
        null = cmds.listRelatives(dropped[0], parent=True, fullPath=True)[0]
        ok = (dist(shift, want) < 1e-6 and dist(world_t(null), (0, 0, 0)) < 1e-9
              and fbxlayout.root_in_layout(dropped[0]))
    gate(6, "Creep [skeleton]: root moved by the floor point, Armature at the origin, "
            "still in Cascadeur's layout", ok, "%s | %s %s" % (text, dropped, origin))

    # ---- 7: Add Character imports at the origin
    pick_kind("rig")
    window.select_model("Creep")
    before = rig_namespaces()
    window.add_character()
    new = sorted(rig_namespaces() - before)
    main = cmds.ls(new[0] + ":Main", long=True)[0] if new else None
    gate(7, "Add Character: Creep [rig] at the origin",
         bool(main) and dist(world_t(main), (0, 0, 0)) < 1e-9,
         "%s %s" % (new, cmds.text(window._CHARACTER_STATUS, query=True, label=True)))

    # ---- 8: the Colour section repaints what Add left selected
    import maya_rigs
    from maya_scenesetup import colour
    selection = cmds.ls(selection=True, long=True)
    rgb = colour.PALETTE[4].rgb
    said = maya_colour.paint(rgb)
    rig = [r for r in maya_rigs.rigs() if r.namespace == (new[0] if new else "")]
    shapes = colour.character_meshes(rig[0].skeleton_root) if rig else []
    worn = []
    for shape in shapes:
        groups = cmds.listConnections(shape, type="shadingEngine") or []
        for group in groups:
            for material in cmds.listConnections(group + ".surfaceShader") or []:
                worn.append(tuple(round(v, 4) for v in cmds.getAttr(material + ".color")[0]))
    gate(8, "Colour repaints the rig Add left selected",
         bool(selection) and bool(worn)
         and all(w == tuple(round(v, 4) for v in rgb) for w in worn),
         "%s | %s | %s" % (selection[:1], said, sorted(set(worn))))

    # ---- 9: a real press - drag - release on the grid
    q = maya_hubqt.qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    x, y, w, h = g.rects()[1]
    start = QtCore.QPoint(x + w // 2, y + h // 2)

    def mouse(kind, local=None, global_point=None, button=QtCore.Qt.LeftButton,
              buttons=QtCore.Qt.LeftButton):
        global_point = global_point or g.mapToGlobal(local)
        local = local if local is not None else g.mapFromGlobal(global_point)
        event = QtGui.QMouseEvent(kind, QtCore.QPointF(local), QtCore.QPointF(global_point),
                                  button, buttons, QtCore.Qt.NoModifier)
        q.QtWidgets.QApplication.sendEvent(g, event)

    E = QtCore.QEvent
    before = rig_namespaces()
    mouse(E.MouseButtonPress, local=start)
    mouse(E.MouseMove, local=start + QtCore.QPoint(40, 0), button=QtCore.Qt.NoButton)
    dragging = g._drag is not None
    caption = g._drag["ghost"].text if g._drag else ""
    far = QtCore.QPoint(*points[2])
    mouse(E.MouseMove, global_point=far, button=QtCore.Qt.NoButton)
    mouse(E.MouseButtonRelease, global_point=far, buttons=QtCore.Qt.NoButton)
    new = sorted(rig_namespaces() - before)
    main = cmds.ls(new[0] + ":Main", long=True)[0] if new else None
    gate(9, "a mouse press-drag-release on the Creep portrait stands a Creep rig there",
         dragging and g._drag is None and bool(main)
         and dist(world_t(main), aims[2]["point"]) < 1e-6,
         "caption '%s' | %s at %s" % (caption, new, world_t(main) if main else None))
    WORLD["points"] = points
    WORLD["aims"] = aims


def phase_deferred():
    """Queue one drop with evalDeferred - outside the port's command, the way
    a real release runs - at a floor point projected afresh (the disposable
    Maya is on the animator's screen: its windows may have moved)."""
    pick_kind("rig")
    target = to_global((200.0, 0.0, -40.0))
    print("   ", keep_hub_off([target]))
    target = to_global((200.0, 0.0, -40.0))
    WORLD["before_undo"] = sorted(rig_namespaces())
    WORLD["dropped"] = None

    def drop():
        WORLD["dropped"] = grid().drop_at(target[0], target[1], "Orc_D")

    cmds.evalDeferred(drop)
    print("queued a drop of Orc D at", target)


def phase_undo():
    """Measured 2026-09-30: `file -import` flushes Maya's undo queue, so a
    character cannot be undone (nor can Maya's own File > Import). What
    follows the import is not recorded, so a Ctrl+Z must leave the dropped
    character exactly as it arrived - not moved back to the origin, not
    stripped of its colour."""
    print("    the drop said:", WORLD.get("dropped"))
    now = sorted(rig_namespaces())
    added = sorted(set(now) - set(WORLD["before_undo"]))
    ns = added[0] if len(added) == 1 else None
    main = (cmds.ls(ns + ":Main", long=True) or [None])[0] if ns else None
    before = world_t(main) if main else None
    name = cmds.undoInfo(query=True, undoName=True)
    try:
        cmds.undo()
        said = "undid '%s'" % name
    except RuntimeError as error:
        said = str(error).strip()
    after = world_t(main) if main and cmds.objExists(main) else None
    gate(10, "Ctrl+Z after a drop leaves the character whole where it stands",
         bool(ns) and after is not None and dist(before, after) < 1e-9
         and dist(before, (0.0, 0.0, 0.0)) > 1.0 and sorted(rig_namespaces()) == now,
         "%s at %s -> %s (%s)" % (ns, before, after, said))


def phase_classic():
    import maya_hub
    maya_hub.set_classic(True)
    print("asked for the classic hub")


def phase_classic2():
    import maya_hub
    import maya_hubqt
    from maya_scenesetup import window
    settle()
    g = grid()
    host = maya_hubqt.find(window._PORTRAITS, layout=True)
    ok = (not maya_hub.is_skinned() and g is not None and host is not None
          and host.height() == g.height_for(host.width()) > 0 and g.isVisible())
    gate(11, "the grid stands in the classic hub too", ok,
         "host %s grid %s" % ((host.width(), host.height()) if host else None,
                              g.geometry() if g else None))
    maya_hub.set_classic(False)


{"place": phase_place, "deferred": phase_deferred, "undo": phase_undo,
 "classic": phase_classic, "classic2": phase_classic2}[PHASE]()
print("%s: %s" % (PHASE, "FAILURES %s" % FAILED if FAILED else "all gates passed"))
