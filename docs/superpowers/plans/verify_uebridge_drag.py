"""Live proof of the UE Bridge list's drag into the viewport (2026-10-01).

Run in a DISPOSABLE Maya (it opens a new scene and adds rigs): its own
MAYA_APP_DIR, MAYA_NO_HOME=1, its own port. No Unreal editor is needed: the
editor's export is replaced for the run by FBX clips already on disk (the UE
clips verify_many_rigs.py retargets). Each send sets PHASE first:

    PHASE = "setup"     gates 1-4: two Manny rigs side by side, the hub on UE
                        Bridge, the list's drag attached; clip_target over each
                        rig's pelvis names it, beside them "new_rig", off every
                        viewport "none"
    PHASE = "drag"      gate 5: a press - drag - release sent through Qt to the
                        real list, released on the SECOND rig while the FIRST is
                        selected and the mode reads Skeleton (the drop queues its
                        import one idle later, as a real release does)
    PHASE = "measure1"  gate 6: the second rig plays the clip, the source is
                        gone, the first rig never moved; gate 12: the second
                        rig - turned 60 deg before the drop - kept its place
                        and its facing, and plays the clip rigidly moved there
    PHASE = "floor"     gate 7: with Creep [rig] active in Characters, drop_at
                        on empty floor queues a new rig - a Creep - on that point
    PHASE = "measure2"  gate 8: after every bake the Creep's Main stands on the
                        floor point at the clip's first frame, its root track is
                        the clip's moved by that much, the camera sits on its
                        camera_root, the first two rigs are as they were
    PHASE = "entry"     gate 9: Characters on a skeleton (or nothing) adds Manny,
                        on a rig adds that rig
    PHASE = "floor2"    gate 10: Manny [rig] active, a clip carrying the camera
                        bones dropped on another floor point
    PHASE = "measure3"  gate 11: that Manny on its point, its camera (set up on
                        camera_root by the bake) with it

Spec: docs/superpowers/specs/2026-10-01-uebridge-drag-to-viewport-design.md
"""

import math
import sys

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402

PHASE = globals().get("PHASE", "setup")
FAILED = []
WORLD = sys.__dict__.setdefault("_verify_uebridge_drag", {})   # across sends

CLIPS = {"LongSword_Attack_Right_Heavy_1P":
         "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_1P.FBX",
         "ShortSword_Walk_1P":
         "C:/!!!Work/Animations/Export/ShortSword_Walk_1P.fbx"}
A_AT, B_AT = (-90.0, 0.0, 0.0), (90.0, 0.0, 0.0)
FLOOR = (-260.0, 0.0, 60.0)
FLOOR2 = (230.0, 0.0, 150.0)
FRAMES = (0, 10, 20, 30)


def gate(number, text, ok, detail=""):
    print("gate %2d %s  %s  %s" % (number, "PASS" if ok else "FAIL", text, detail))
    if not ok:
        FAILED.append(number)


def world_t(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def settle():
    import maya_hubqt
    maya_hubqt.qt().QtWidgets.QApplication.processEvents()
    cmds.refresh(force=True)


def rigs():
    import maya_rigs
    return dict((r.namespace, r) for r in maya_rigs.rigs())


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
    if not any(maya_hubqt.on_hub(x, y) for x, y in points):
        return "the hub stands clear"
    top = maya_hubqt.find("skeldarAnimHub").window()
    screen = top.screen().availableGeometry()
    corners = [(screen.left(), screen.top()),
               (screen.right() - top.width(), screen.top()),
               (screen.left(), screen.bottom() - top.height()),
               (screen.right() - top.width(), screen.bottom() - top.height())]
    for x, y in corners:
        top.move(x, y)
        settle()
        if not any(maya_hubqt.on_hub(px, py) for px, py in points):
            return "hub moved to %s" % (top.pos(),)
    return "the hub covers a point wherever it stands (%s)" % (top.pos(),)


def pelvis(namespace):
    return world_t(namespace + ":pelvis")


def track(node):
    """The node's world translation at FRAMES (a real time change each)."""
    out = []
    for frame in FRAMES:
        cmds.currentTime(frame, update=True)
        out.append(world_t(node))
    return out


def drag():
    import maya_hubqt
    from maya_uebridge import listdrag
    found = listdrag._DRAGS.get("ueAnimBridgeList")
    return found if found is not None and maya_hubqt.qt().shiboken.isValid(found) else None


def click_mode(mode):
    import maya_hubqt
    from maya_uebridge import window
    q = maya_hubqt.qt()
    widget = maya_hubqt.find(window.mode_button(mode))
    button = q.shiboken.wrapInstance(int(q.shiboken.getCppPointer(widget)[0]),
                                     q.QtWidgets.QAbstractButton)
    button.click()
    q.QtWidgets.QApplication.processEvents()


def phase_setup():
    import maya_hub
    import maya_hubqt
    from maya_scenesetup import catalog, character, droptarget
    from maya_uebridge import listdrag, records, window

    cmds.file(new=True, force=True)
    for at in (A_AT, B_AT):
        character.add_character(catalog.default_rig(), at=at)
    maya_hub.show("uebridge")
    settle()
    cmds.viewPlace("persp", eye=(0.0, 260.0, 720.0), lookAt=(0.0, 90.0, 0.0))
    settle()

    found = sorted(rigs())
    WORLD["a"], WORLD["b"] = found[0], found[1]
    window._STATE["records"] = records.parse_payload({"assets": [
        {"name": name, "package": "/Game/Verify/" + name, "fps": 30.0}
        for name in sorted(CLIPS)]})
    window._repopulate()
    window._export_from_editor = lambda record: (CLIPS[record.name], 30.0)

    # ---- 1: the list carries the drag
    d = drag()
    rows = cmds.textScrollList(window._LIST, query=True, allItems=True) or []
    gate(1, "the UE Bridge list carries the drag, two rows",
         d is not None and d.list.inherits("QListWidget") and len(rows) == 2
         and d.list.count() == 2,
         "%s rows %s" % (d, rows))

    # ---- 2-3: each rig's projected pelvis names that rig
    points = [to_global(pelvis(WORLD[k])) for k in ("a", "b")]
    floor = to_global(FLOOR)
    print("   ", keep_hub_off(points + [floor]))
    points = [to_global(pelvis(WORLD[k])) for k in ("a", "b")]
    snap = droptarget.rig_snapshot()
    aims = [droptarget.clip_target(x, y, snap, listdrag.Scene().scale(),
                                   catalog.default_rig().label) for x, y in points]
    gate(2, "over the first rig's pelvis: that rig",
         aims[0].get("kind") == "rig" and aims[0].get("rig") == WORLD["a"], aims[0])
    gate(3, "over the second rig's pelvis: that rig",
         aims[1].get("kind") == "rig" and aims[1].get("rig") == WORLD["b"], aims[1])

    # ---- 4: beside them a new rig; off every viewport nothing; the list is the hub
    floor = to_global(FLOOR)
    beside = droptarget.clip_target(floor[0], floor[1], snap)
    import maya.mel as mel
    slider = maya_hubqt.find(mel.eval("$skeldarTmp = $gPlayBackSlider"))
    centre = slider.mapToGlobal(slider.rect().center())
    off = droptarget.clip_target(centre.x(), centre.y(), snap)
    row = d.list.viewport().mapToGlobal(d.list.visualItemRect(d.list.item(0)).center())
    gate(4, "beside the rigs a new rig, on the time slider nothing, the list is the hub",
         beside.get("kind") == "new_rig" and off.get("kind") == "none"
         and listdrag.Scene().over_hub(row.x(), row.y()),
         "%s | %s" % (beside, off))


def phase_drag():
    import maya_hubqt
    from maya_uebridge import listdrag, window
    q = maya_hubqt.qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    E = QtCore.QEvent
    d = drag()
    a, b = WORLD["a"], WORLD["b"]
    WORLD["a_track"] = track(a + ":hand_r")
    # «я хочу чтобы риг остался на своем месте»: B stands at x = 90, turned
    cmds.setAttr(b + ":Main.rotateY", 60.0)
    settle()
    m = cmds.xform(b + ":Main", query=True, worldSpace=True, matrix=True)
    WORLD["b_place"] = (m[12], m[13], m[14], math.degrees(math.atan2(m[8], m[10])))
    click_mode("skeleton")
    cmds.select(a + ":Main", replace=True)
    target = to_global(pelvis(b))
    print("   ", keep_hub_off([target]))
    target = QtCore.QPoint(*to_global(pelvis(b)))

    port = d.list.viewport()
    start = d.list.visualItemRect(d.list.item(0)).center()

    def mouse(kind, local=None, global_point=None, button=QtCore.Qt.LeftButton,
              buttons=QtCore.Qt.LeftButton):
        global_point = global_point or port.mapToGlobal(local)
        local = local if local is not None else port.mapFromGlobal(global_point)
        event = QtGui.QMouseEvent(kind, QtCore.QPointF(local), QtCore.QPointF(global_point),
                                  button, buttons, QtCore.Qt.NoModifier)
        q.QtWidgets.QApplication.sendEvent(port, event)

    mouse(E.MouseButtonPress, local=start)
    mouse(E.MouseMove, local=start + QtCore.QPoint(40, 0), button=QtCore.Qt.NoButton)
    carried = d.dragging()
    mouse(E.MouseMove, global_point=target, button=QtCore.Qt.NoButton)
    d.caption_at(target, force=True)
    caption = d.ghost().text if d.ghost() else ""
    if d.ghost() and WORLD.get("ghost_png"):
        d.ghost().grab().save(WORLD["ghost_png"])     # our own widget, not Maya's
    mouse(E.MouseButtonRelease, global_point=target, buttons=QtCore.Qt.NoButton)
    picked = cmds.textScrollList(window._LIST, query=True, selectItem=True) or []
    gate(5, "press-drag-release on the first row, released on the second rig",
         carried is not None and carried.name == "LongSword_Attack_Right_Heavy_1P"
         and d.dragging() is None and ("retarget onto %s" % b) in caption
         and window.import_mode() == "skeleton" and len(picked) == 1
         and picked[0].strip().startswith("LongSword"),
         "carried %s | caption '%s' | said '%s' | list %s" % (
             carried.name if carried else None, caption, d.status_text, picked))


def phase_measure1():
    from maya_uebridge import window
    a, b = WORLD["a"], WORLD["b"]
    said = cmds.text(window._STATUS, query=True, label=True)
    b_track = track(b + ":hand_r")
    moved = max(dist(b_track[0], p) for p in b_track[1:])
    a_now = track(a + ":hand_r")
    a_drift = max(dist(p, q) for p, q in zip(WORLD["a_track"], a_now))
    left = [ns for ns in (cmds.namespaceInfo(":", listOnlyNamespaces=True) or [])
            if "LongSword" in ns]
    gate(6, "the second rig plays the clip (hand_r), its source deleted, the first rig unmoved",
         ("retargeted onto %s" % b) in said and moved > 1.0 and not left
         and a_drift < 1e-9 and sorted(rigs()) == sorted([a, b]),
         "b hand_r travels %.3f | a drift %.2e | left %s | '%s'" % (
             moved, a_drift, left, said[:160]))
    WORLD["b_track"] = b_track
    _kept_place(b)


def _kept_place(b):
    """Gate 12: B kept its place and facing; it plays the clip rigidly moved
    there - root and hand_r on every sampled frame against the same clip
    imported as a plain skeleton, through the one transform that takes the
    clip's root at its first frame onto B's."""
    import maya.api.OpenMaya as om
    from maya_uebridge import animimport
    if cmds.namespace(exists="verifyClip"):
        cmds.namespace(removeNamespace="verifyClip", deleteNamespaceContent=True)
    animimport.import_clip(CLIPS["LongSword_Attack_Right_Heavy_1P"], "verifyClip",
                           set_timeline=False, clip_fps=30.0, merge=False)

    def wm(node):
        return om.MMatrix(cmds.xform(node, query=True, worldSpace=True, matrix=True))

    cmds.currentTime(0, update=True)
    main = cmds.xform(b + ":Main", query=True, worldSpace=True, matrix=True)
    facing = math.degrees(math.atan2(main[8], main[10]))
    move = wm("verifyClip:root").inverse() * wm(b + ":root")
    worst = 0.0
    for frame in range(0, 61, 6):
        cmds.currentTime(frame, update=True)
        for bone in ("root", "hand_r"):
            want = om.MPoint(cmds.xform("verifyClip:" + bone, query=True, worldSpace=True,
                                        translation=True)) * move
            got = cmds.xform(b + ":" + bone, query=True, worldSpace=True, translation=True)
            worst = max(worst, dist((want.x, want.y, want.z), got))
    cmds.namespace(removeNamespace="verifyClip", deleteNamespaceContent=True)
    place = WORLD["b_place"]
    turn = (facing - place[3] + 180.0) % 360.0 - 180.0
    gate(12, "the rig dropped on kept its place (x = 90) and its 60 deg facing, and plays "
             "the clip rigidly moved there",
         abs(main[12] - place[0]) < 1e-3 and abs(main[14] - place[2]) < 1e-3
         and abs(turn) < 1e-3 and worst < 0.01,
         "Main at frame 0 (%.4f, %.4f) facing %.4f vs place (%.4f, %.4f) facing %.4f | "
         "root and hand_r off the moved clip by %.2e cm" % (
             main[12], main[14], facing, place[0], place[2], place[3], worst))


def choose_character(model, kind):
    """What the Characters card remembers: its portrait and its switch."""
    cmds.optionVar(stringValue=("mayaSceneSetup_characterModel", model))
    cmds.optionVar(stringValue=("mayaSceneSetup_characterKind", kind))


def _floor_drop(number, model, label, where, clip):
    from maya_uebridge import listdrag, window
    choose_character(model, "rig")
    floor = to_global(where)
    print("   ", keep_hub_off([floor]))
    floor = to_global(where)
    scene = listdrag.Scene()
    aim = scene.target(floor[0], floor[1], scene.snapshot())
    record = [r for r in window._STATE["filtered"] if r.name == clip][0]
    WORLD["a_track"] = track(WORLD["a"] + ":hand_r")
    WORLD["b_track"] = track(WORLD["b"] + ":hand_r")
    WORLD["floor"] = aim.get("point")
    WORLD["clip"] = clip
    WORLD["rigs_before"] = sorted(rigs())
    said = drag().drop_at(floor[0], floor[1], record)
    gate(number, "%s active: drop_at on empty floor aims at a new one on the floor "
                 "point and queues it" % label,
         aim.get("kind") == "new_rig" and aim.get("point") is not None
         and dist(aim["point"], where) < 3.0 and ("a new %s" % label) in said,
         "%s | '%s'" % (aim, said))


def phase_floor():
    _floor_drop(7, "Creep", "Creep [rig]", FLOOR, "ShortSword_Walk_1P")


def phase_floor2():
    _floor_drop(10, "Manny", "Manny [rig]", FLOOR2, "LongSword_Attack_Right_Heavy_1P")


def phase_measure2():
    _measure_floor(8, "Creep_Rig", 18)


def phase_measure3():
    _measure_floor(11, "Manny_Rig", 60)


def _measure_floor(number, prefix, last):
    from maya_uebridge import animimport, window
    a, b = WORLD["a"], WORLD["b"]
    said = cmds.text(window._STATUS, query=True, label=True)
    now = rigs()
    new = sorted(set(now) - set(WORLD["rigs_before"]))
    ns = new[0] if len(new) == 1 else None
    point = WORLD["floor"]
    # the same clip as a plain skeleton: where its root walks unmoved
    if cmds.namespace(exists="verifyClip"):
        cmds.namespace(removeNamespace="verifyClip", deleteNamespaceContent=True)
    animimport.import_clip(CLIPS[WORLD["clip"]], "verifyClip",
                           set_timeline=False, clip_fps=30.0, merge=False)
    clip_root = [p for p in cmds.ls("verifyClip:root", long=True) or []][0]
    frames = list(range(0, last + 1, 3))
    first = frames[0]
    off, worst, cam = [], 0.0, 0.0
    # the Creep carries no camera bones (only weapon_r / weapon_l travel), so
    # its camera is asked about only where the rig has camera_root
    has_camera = bool(ns) and cmds.objExists(ns + ":camera_root")
    if ns:
        for frame in frames:
            cmds.currentTime(frame, update=True)
            ours = world_t(ns + ":root")
            theirs = world_t(clip_root)
            off.append([ours[i] - theirs[i] for i in range(3)])
            if has_camera:
                cam = max(cam, dist(world_t(ns + ":SceneSetup_camera"),
                                    world_t(ns + ":camera_root")))
        shift = off[0]
        worst = max(dist(o, shift) for o in off)
        cmds.currentTime(first, update=True)
        # the RIG stands on the point: its Main, as a portrait dropped from
        # Characters does (the Creep's root bone stands 2.4 cm ahead of Main)
        at_start = world_t(ns + ":Main")
    drift = max(max(dist(p, q) for p, q in zip(WORLD[k + "_track"], track(WORLD[k] + ":hand_r")))
                for k in ("a", "b"))
    if ns:
        WORLD["c"] = WORLD.get("c") or ns
    cmds.namespace(removeNamespace="verifyClip", deleteNamespaceContent=True)
    on_point = (ns is not None and abs(at_start[0] - point[0]) < 1e-3
                and abs(at_start[2] - point[2]) < 1e-3 and abs(shift[1]) < 1e-3)
    gate(number, "the new rig stands on the floor point after every bake, its root "
                 "walks the clip's track moved by that much, the camera on its "
                 "camera_root, the rigs before it unmoved",
         bool(ns) and ns.startswith(prefix) and on_point and worst < 1e-2
         and (has_camera or prefix == "Creep_Rig")
         and cam < 1e-3 and drift < 1e-9 and ("retargeted onto %s" % ns) in said
         and "standing at floor" in said,
         "%s Main at frame %d %s vs floor %s | root shift %s, track off it by %.2e | "
         "camera %s | others drift %.2e | '...%s'" % (
             ns, first, [round(v, 4) for v in at_start] if ns else None,
             [round(v, 4) for v in point], [round(v, 4) for v in shift] if ns else None,
             worst, ("%.2e" % cam) if has_camera else "none (no camera_root)",
             drift, said[-120:]))


def phase_entry():
    from maya_uebridge import rigimport
    seen = []
    for model, kind in (("Creep", "skeleton"), ("Orc_D", "rig"), ("UE4_Mannequin", "rig"),
                        ("Creep", "rig")):
        choose_character(model, kind)
        seen.append(rigimport.new_rig_entry().key)
    gate(9, "Characters on a skeleton or a model with no rig adds Manny, on a rig "
            "adds that rig",
         seen == ["Manny_Rig", "Orc_D_Rig", "Manny_Rig", "Creep_Rig"], seen)


{"setup": phase_setup, "drag": phase_drag, "measure1": phase_measure1,
 "floor": phase_floor, "measure2": phase_measure2, "entry": phase_entry,
 "floor2": phase_floor2, "measure3": phase_measure3}[PHASE]()
print("%s: %s" % (PHASE, "FAILURES %s" % FAILED if FAILED else "all gates passed"))
