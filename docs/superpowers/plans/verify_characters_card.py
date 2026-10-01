"""Live proof of the Characters card holding the UE Bridge (2026-10-01).

«UE bridge и character эти две вкладки имеют общий функционал ... их нужно
объеденить в одно окно». Run in a DISPOSABLE Maya (it opens new scenes, adds
characters): its own MAYA_APP_DIR, MAYA_NO_HOME=1, its own port. No Unreal
editor: the editor's export is replaced by FBX clips on disk. Each send sets
PHASE first:

    PHASE = "card"      gates 1-5: the hub's first card is Characters, the
                        UE Bridge no card of its own and its key opening
                        Characters; the card's controls top down (kind,
                        portraits, Add / Delete, Camera Setup, the editor
                        line, the list, Import [Onto selected | New], Import,
                        the exports, ONE status line); its content within
                        the animator's 360 px dock; Import its one primary;
                        both modules writing that one line
    PHASE = "photo"     the card photographed at the dock's width
    PHASE = "modes"     gate 6: the card's kind and the Import row clicked
                        through Qt - the four modes
    PHASE = "rig_onto"  gate 7: Rig x Onto selected onto a Manny rig moved
                        to (-150, 0, 80) and turned 45: it keeps its place
                        and facing, its hand plays the clip
    PHASE = "skel_new"  gate 8: Skeleton x New with Characters on Manny UE5
                        [skeleton]: a new skeleton, with its mesh, playing
                        the clip exactly where the clip is
    PHASE = "skel_onto" gates 9-10: a Manny UE5 skeleton moved to
                        (100, 0, -50) and turned 90, a sword in its right
                        hand, its MESH selected; Skeleton x Onto selected:
                        every bone (weapon_r too) on the clip moved by one
                        rigid floor move, the root at the first frame on
                        (100, -50) facing 90, the sword relinked and riding
                        weapon_r, the clip's skeleton gone
    PHASE = "skel_refuse" gate 11: two skeletons, nothing selected - refused,
                        both named; a rig selected - refused, «is a rig»;
                        the editor never asked
    PHASE = "drag_skel" gate 12: Skeleton picked, a clip dragged through Qt
                        onto a skeleton's pelvis - the ghost names it
    PHASE = "measure_drag" gate 13: that skeleton took the clip in its place

Spec: docs/superpowers/specs/2026-10-01-characters-and-bridge-one-card-design.md
"""

import math
import os
import sys

REPO = globals().get("REPO", "C:/!!!Work/MayaScripts/SkeldarAnim")
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402

PHASE = globals().get("PHASE", "card")
FAILED = []
WORLD = sys.__dict__.setdefault("_verify_characters_card", {})   # across sends
SHOTS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
VIEWPORT = 510          # the animator's 360 px dock: its scroll viewport, physical px

EXPORT = "C:/!!!Work/Animations/Export/"
CLIPS = {"LongSword_Attack_Right_Heavy_1P": EXPORT + "LongSword_Attack_Right_Heavy_1P.FBX",
         "ShortSword_Attack_Thrust_3P": EXPORT + "ShortSword_Attack_Thrust_3P.FBX",
         "ShortSword_Walk_1P": EXPORT + "ShortSword_Walk_1P.fbx"}
ORDER = sorted(CLIPS)               # the list's order
THRUST = "ShortSword_Attack_Thrust_3P"
LONGSWORD = "LongSword_Attack_Right_Heavy_1P"
BONES = ("pelvis", "spine_03", "head", "upperarm_l", "lowerarm_r", "hand_r",
         "weapon_r", "thigh_l", "calf_r", "foot_l", "ball_r")


def gate(number, text, ok, detail=""):
    print("gate %2d %s  %s  %s" % (number, "PASS" if ok else "FAIL", text, detail))
    if not ok:
        FAILED.append(number)


def world_t(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def world_m(node):
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def settle():
    import maya_hubqt
    q = maya_hubqt.qt()
    for _ in range(3):
        q.QtWidgets.QApplication.processEvents()
    cmds.refresh(force=True)


def qbutton(name):
    import maya_hubqt
    q = maya_hubqt.qt()
    widget = maya_hubqt.find(name)
    return q.shiboken.wrapInstance(int(q.shiboken.getCppPointer(widget)[0]),
                                   q.QtWidgets.QAbstractButton)


def click(name):
    """A segment clicked the animator's way: the Qt button (trap 116)."""
    import maya_hubqt
    qbutton(name).click()
    maya_hubqt.qt().QtWidgets.QApplication.processEvents()


def pick_kind(kind):
    from maya_scenesetup import window as scene
    click(scene.kind_segment(kind))


def pick_target(target):
    from maya_uebridge import window
    click(window.target_button(target))


def choose_model(model):
    cmds.optionVar(stringValue=("mayaSceneSetup_characterModel", model))


def status():
    from maya_uebridge import window
    return cmds.text(window._STATUS, query=True, label=True) or ""


def rigs():
    import maya_rigs
    return dict((r.namespace, r) for r in maya_rigs.rigs())


def clip_namespaces():
    return [ns for ns in (cmds.namespaceInfo(":", listOnlyNamespaces=True) or [])
            if any(name in ns for name in CLIPS)]


def pick_rows(rows):
    from maya_uebridge import window
    cmds.textScrollList(window._LIST, edit=True, deselectAll=True)
    for row in rows:
        cmds.textScrollList(window._LIST, edit=True, selectIndexedItem=row)
    settle()


def row_of(name):
    return ORDER.index(name) + 1


def list_ready():
    """The list filled with the three clips on disk, the editor's export
    replaced by them (no Unreal)."""
    from maya_uebridge import records, window
    window._STATE["records"] = records.parse_payload({"assets": [
        {"name": name, "package": "/Game/Verify/" + name, "fps": 30.0} for name in ORDER]})
    window._repopulate()
    window._export_from_editor = lambda record: (
        WORLD.setdefault("exported", []).append(record.name) or (CLIPS[record.name], 30.0))


def new_scene():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    WORLD["exported"] = []


def card_widget():
    import maya_hub
    return maya_hub._SKIN.cards["characters"].frame


def skeleton_root_of(before):
    """The topmost new joint since `before` (a set of joint paths)."""
    fresh = [j for j in (cmds.ls(type="joint", long=True) or []) if j not in before]
    return min(fresh, key=lambda p: (p.count("|"), p)) if fresh else None


def bone(root, name):
    for joint in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                              fullPath=True) or []):
        if joint.split("|")[-1].split(":")[-1] == name:
            return joint
    return None


def skinned(root):
    joints = set([root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                              fullPath=True) or []))
    count = 0
    for skin in cmds.ls(type="skinCluster") or []:
        inf = set(cmds.ls(cmds.skinCluster(skin, query=True, influence=True) or [], long=True))
        if inf & joints:
            count += len(cmds.skinCluster(skin, query=True, geometry=True) or [])
    return count


def mmat(flat):
    import maya.api.OpenMaya as om
    return om.MMatrix(flat)


def angle(a, b):
    """Degrees between the orientations of two matrices, their scale taken
    out: 3P clips animate bone scale (trap 152) and the transfer carries
    translate and rotate only."""
    import maya.api.OpenMaya as om
    qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def rigid_check(root, name, frames):
    """The skeleton under `root` against the clip imported again plainly:
    one rigid move W (taken at the clip's first frame, from the roots) must
    carry every sampled bone of the clip onto ours. Returns (worst cm, worst
    orientation off in degrees, W's turn about Y in degrees, W's tilt,
    the root's place and facing at the first frame)."""
    import maya.api.OpenMaya as om
    from maya_uebridge import animimport, rigimport
    if cmds.namespace(exists="vcChk"):
        cmds.namespace(removeNamespace="vcChk", deleteNamespaceContent=True)
    info = animimport.import_clip(CLIPS[name], "vcChk", set_timeline=False, clip_fps=30.0,
                                  merge=False)
    clip = cmds.ls("vcChk:root", long=True)[0]
    start = int(info["start"])
    cmds.currentTime(start, update=True)
    w = mmat(world_m(clip)).inverse() * mmat(world_m(root))
    place = world_m(root)
    facing = rigimport.facing(place)
    tw = om.MTransformationMatrix(w)
    rot = tw.rotation(asQuaternion=False)
    tilt = max(abs(math.degrees(rot.x)), abs(math.degrees(rot.z)))
    turn = math.degrees(rot.y)
    worst_cm, worst_rot = 0.0, 0.0
    for frame in frames:
        cmds.currentTime(frame, update=True)
        for b in ("root",) + BONES:
            ours, theirs = bone(root, b), bone(clip, b)
            if ours is None or theirs is None:
                continue
            want = mmat(world_m(theirs)) * w
            got = mmat(world_m(ours))
            worst_cm = max(worst_cm, math.sqrt(sum((want[12 + i] - got[12 + i]) ** 2
                                                   for i in range(3))))
            worst_rot = max(worst_rot, angle(want, got))
    cmds.namespace(removeNamespace="vcChk", deleteNamespaceContent=True)
    return worst_cm, worst_rot, turn, tilt, (place[12], place[14]), facing


# ------------------------------------------------------------------ phases

def phase_card():
    import maya_hub
    import maya_hubqt
    from maya_scenesetup import window as scene
    from maya_uebridge import window

    new_scene()
    choose_model("Manny")
    maya_hub.show("uebridge")
    settle()
    skin = maya_hub._SKIN
    column = skin.column
    cards, groups = [], []
    for i in range(column.count()):
        widget = column.itemAt(i).widget()
        name = widget.objectName() if widget is not None else ""
        if name.startswith("skeldarHubGroup_"):
            groups.append(name.split("_", 1)[1])
        elif name.startswith("skeldarHubCard_"):
            cards.append(name.split("_", 1)[1])
    gate(1, "the first card is Animation Setup (key characters), the Scene group first; "
            "no UE Bridge card; show('uebridge') opened and lit it",
         cards[0] == "characters" and groups[0] == "scene" and "uebridge" not in skin.cards
         and maya_hub.section("characters").label == "Animation Setup"
         and not skin.cards["characters"].collapsed() and skin.active == "characters",
         "cards %s | groups %s | active %s" % (cards[:4], groups, skin.active))

    # the hub floated and sized to the animator's dock, the card open
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
    list_ready()
    settle()

    names = [scene.kind_segment("rig"), scene._PORTRAITS, scene._BOUND,
             window._HEADER, window._PROJECT, window._SEARCH, window._LIST,
             window.target_button("onto"), window.target_button("new"),
             window._TIMELINE, scene._CHARACTER_STATUS]
    frame = card_widget()
    ys = []
    for name in names:
        widget = maya_hubqt.find(name, name == scene._PORTRAITS)
        ys.append(None if widget is None else widget.mapTo(frame, q.QtCore.QPoint(0, 0)).y())
    labels = {}
    for button in frame.findChildren(q.QtWidgets.QPushButton):
        if button.text():
            labels[button.text()] = button.mapTo(frame, q.QtCore.QPoint(0, 0)).y()
    body = [n for n in names[3:]]
    order_ok = (None not in ys and ys[0] < ys[1]
                and labels.get("Import", 1e9) > ys[1]
                and labels.get("Camera Setup", 1e9) < ys[3]
                and all(ys[i] <= ys[i + 1] for i in range(3, len(ys) - 1))
                and ys[-2] < labels.get("Import Animation", -1)
                < labels.get("Export FBX...", -1) < ys[-1])
    #  the status lines in the card, by their names: the card's, and the
    #  bridge's own of before the merge (which must be gone)
    lines = [w.objectName() for w in frame.findChildren(q.QtWidgets.QWidget)
             if w.objectName() in (scene._CHARACTER_STATUS, "ueAnimBridgeStatus")]
    gate(2, "the card top down: kind, portraits, Add / Delete, Camera Setup, the editor "
            "line, the editor, search, list, Import [Onto selected | New], timeline, Import, "
            "the exports, ONE status line",
         order_ok and lines == [scene._CHARACTER_STATUS] and "Delete" in labels,
         "y %s | buttons %s | status lines %s" % (
             dict(zip([n.split("|")[-1] for n in names], ys)),
             dict((k, v) for k, v in labels.items() if k in (
                 "Import", "Delete", "Camera Setup", "Import Animation", "Export FBX...",
                 "Export to uasset", "Onto selected", "New")), lines))

    content = skin.content
    need = content.minimumSizeHint().width()
    gate(3, "the content fits the animator's 360 px dock",
         need <= scroll.viewport().width(),
         "content minimum %d <= viewport %d" % (need, scroll.viewport().width()))

    primaries = [b.text() for b in frame.findChildren(q.QtWidgets.QPushButton)
                 if b.property("skRole") == "primary"]
    gate(4, "two primaries, one per half: + Import and Import Animation",
         sorted(primaries) == ["Import", "Import Animation"], "%s" % primaries)

    window._status("from the bridge")
    first = status()
    scene.say_character("from Characters")
    second = cmds.text(scene._CHARACTER_STATUS, query=True, label=True)
    gate(5, "both modules write the card's one line",
         first == "from the bridge" and second == "from Characters"
         and window._STATUS == scene._CHARACTER_STATUS,
         "%r %r" % (first, second))
    cmds.workspaceControl(maya_hub.CONTROL, edit=True, restore=True)


def phase_photo():
    import maya_hub
    from maya_scenesetup import window as scene
    maya_hub.focus("characters")
    choose_model("Manny")
    pick_kind("rig")
    pick_target("onto")
    scene._say_choice()
    settle()
    frame = card_widget()
    path = os.path.join(SHOTS, "characters_card.png")
    frame.grab().save(path)
    print("saved", path, frame.size())


def phase_modes():
    from maya_uebridge import window
    seen = {}
    for kind in ("rig", "skeleton"):
        pick_kind(kind)
        for target in ("onto", "new"):
            pick_target(target)
            seen[(kind, target)] = window.import_mode()
    pick_kind("rig")
    pick_target("onto")
    gate(6, "the card's kind x the Import row, clicked through Qt: the four modes",
         seen == {("rig", "onto"): "rig", ("rig", "new"): "new_rig",
                  ("skeleton", "onto"): "onto_skeleton", ("skeleton", "new"): "skeleton"},
         "%s" % seen)


def phase_rig_onto():
    from maya_scenesetup import catalog, character
    from maya_uebridge import window
    new_scene()
    choose_model("Manny")
    pick_kind("rig")
    pick_target("onto")
    list_ready()
    character.add_character(catalog.default_rig())
    ns = list(rigs())[0]
    cmds.setAttr(ns + ":Main.translate", -150.0, 0.0, 80.0)
    cmds.setAttr(ns + ":Main.rotateY", 45.0)
    cmds.select(ns + ":Main", replace=True)
    pick_rows([row_of(LONGSWORD)])
    window._run(window.import_selected)
    said = status()
    cmds.currentTime(0, update=True)
    main = world_t(ns + ":Main")
    yaw = math.degrees(math.atan2(world_m(ns + ":Main")[8], world_m(ns + ":Main")[10]))
    hand = []
    for frame in range(0, 40, 4):
        cmds.currentTime(frame, update=True)
        hand.append(world_t(ns + ":hand_r"))
    travel = max(dist(hand[0], p) for p in hand)
    gate(7, "Rig x Onto selected: the moved, turned rig keeps its place and facing, its "
            "hand plays the clip",
         "retargeted onto %s" % ns in said and "kept in place at (-150, 80)" in said
         and abs(main[0] + 150) < 1e-3 and abs(main[2] - 80) < 1e-3 and abs(yaw - 45) < 1e-3
         and travel > 1.0 and len(rigs()) == 1 and not clip_namespaces(),
         "Main (%.3f, %.3f) yaw %.4f, hand travels %.2f | '%s'" % (
             main[0], main[2], yaw, travel, said[:200]))


def phase_skel_new():
    from maya_uebridge import window
    new_scene()
    choose_model("Manny")
    pick_kind("skeleton")
    pick_target("new")
    list_ready()
    cmds.select(clear=True)
    before = set(cmds.ls(type="joint", long=True) or [])
    pick_rows([row_of(THRUST)])
    window._run(window.import_selected)
    said = status()
    root = skeleton_root_of(before)
    cm = rot = None
    meshes = 0
    if root:
        meshes = skinned(root)
        cm, rot, turn, tilt, _place, _facing = rigid_check(root, THRUST, range(0, 37, 3))
    gate(8, "Skeleton x New: a new Manny UE5 skeleton with its mesh playing the clip exactly "
            "where the clip is",
         root is not None and meshes > 0 and cm < 1e-3 and rot < 1e-3 and abs(turn) < 1e-4
         and "onto Manny UE5 [skeleton]" in said and "exact" in said and not rigs()
         and not clip_namespaces(),
         "root %s meshes %d | off %s cm, rotation %s, turn %s | '%s'" % (
             root, meshes, cm, rot, None if root is None else round(turn, 6), said[:200]))


def phase_skel_onto():
    from maya_scenesetup import bonedrive, catalog, character, equip
    from maya_uebridge import window
    new_scene()
    choose_model("Manny")
    pick_kind("skeleton")
    pick_target("onto")
    list_ready()
    before = set(cmds.ls(type="joint", long=True) or [])
    character.add_character(catalog.default_character())
    root = skeleton_root_of(before)
    root_uuid = cmds.ls(root, uuid=True)[0]
    cmds.move(100.0, 0.0, -50.0, root, absolute=True, worldSpace=True)
    cmds.rotate(0.0, 90.0, 0.0, root, relative=True, worldSpace=True)
    sword = catalog.WEAPONS[0]
    said_sword = equip.to_hand(root, "R", sword)
    root = cmds.ls(root_uuid, long=True)[0]
    weapon_r = bone(root, "weapon_r")
    linked_before = bonedrive.find_links([weapon_r])
    # the MESH selected: the selection names the skeleton through its skin
    mesh = None
    for skin in cmds.ls(type="skinCluster") or []:
        if root.split("|")[1] in "".join(cmds.ls(cmds.skinCluster(skin, query=True,
                                                                   influence=True), long=True)):
            mesh = cmds.listRelatives(cmds.skinCluster(skin, query=True, geometry=True)[0],
                                      parent=True, fullPath=True)[0]
            break
    cmds.select(mesh, replace=True)
    WORLD["exported"] = []
    pick_rows([row_of(THRUST)])
    window._run(window.import_selected)
    said = status()
    root = cmds.ls(root_uuid, long=True)[0]
    cm, rot, turn, tilt, place, facing = rigid_check(root, THRUST, range(0, 37, 3))
    gate(9, "Skeleton x Onto selected, the mesh selected: every bone (weapon_r too) on the "
            "clip moved by one rigid floor move; the root at the first frame on (100, -50) "
            "facing 90",
         cm < 1e-3 and rot < 1e-3 and tilt < 1e-4 and abs(place[0] - 100) < 1e-3
         and abs(place[1] + 50) < 1e-3 and abs(facing - 90) < 1e-3
         and WORLD["exported"] == [THRUST] and not clip_namespaces(),
         "off %.2e cm, rotation %.2e, turn %.4f tilt %.1e | root at (%.4f, %.4f) facing %.4f | "
         "mesh %s | '%s'" % (cm, rot, turn, tilt, place[0], place[1], facing, mesh, said[:260]))

    links = bonedrive.find_links([bone(root, "weapon_r")])
    sword_node = links[0][1] if links else None
    rides = []
    if sword_node:
        for frame in range(0, 37, 6):
            cmds.currentTime(frame, update=True)
            seat = mmat(world_m(sword_node)) * mmat(world_m(bone(root, "weapon_r"))).inverse()
            rides.append(seat)
    spread = 0.0
    for seat in rides[1:]:
        spread = max(spread, max(abs(seat[i] - rides[0][i]) for i in range(16)))
    gate(10, "the sword relinked: weapon_r driven by it again, the sword riding the bone "
             "at one grip over the take; the status says it",
         bool(linked_before) and sword_node is not None and spread < 1e-6
         and "weapon re-linked on weapon_r" in said and "kept in place at (100, -50)" in said
         and "onto Manny UE5 [skeleton] (root)" in said,
         "%s | before %s after %s | grip spread %.2e" % (
             said_sword, linked_before, links, spread))


def phase_skel_refuse():
    from maya_scenesetup import catalog, character
    from maya_uebridge import window
    new_scene()
    choose_model("Manny")
    pick_kind("skeleton")
    pick_target("onto")
    list_ready()
    character.add_character(catalog.default_character())
    character.add_character(catalog.default_character())
    cmds.select(clear=True)
    pick_rows([row_of(LONGSWORD)])
    window._run(window.import_selected)
    two = status()
    character.add_character(catalog.default_rig())
    ns = list(rigs())[0]
    cmds.select(ns + ":Main", replace=True)
    window._run(window.import_selected)
    rig = status()
    gate(11, "refusals before the editor: two skeletons and nothing selected (both "
             "named), a rig selected with Skeleton picked",
         two.startswith("2 skeletons in the scene (") and "select any bone or mesh" in two
         and rig == "%s is a rig - pick Rig in Animation Setup, or select a skeleton" % ns
         and WORLD["exported"] == [],
         "%r | %r | exported %s" % (two, rig, WORLD["exported"]))


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


def phase_drag_skel():
    import maya_hubqt
    from maya_scenesetup import catalog, character
    from maya_uebridge import listdrag, window
    new_scene()
    choose_model("Manny")
    pick_kind("skeleton")
    list_ready()
    before = set(cmds.ls(type="joint", long=True) or [])
    character.add_character(catalog.default_character())
    root = skeleton_root_of(before)
    cmds.move(-120.0, 0.0, 30.0, root, absolute=True, worldSpace=True)
    WORLD["drag_uuid"] = cmds.ls(root, uuid=True)[0]
    cmds.select(clear=True)
    cmds.viewPlace("persp", eye=(-120.0, 200.0, 650.0), lookAt=(-120.0, 90.0, 30.0))
    q = maya_hubqt.qt()
    for top in q.QtWidgets.QApplication.topLevelWidgets():
        if top.objectName() == "MayaWindow" and (top.isMinimized() or not top.isVisible()):
            top.showMaximized()
    settle()
    pick_rows([row_of(LONGSWORD)])
    target_world = world_t(bone(root, "pelvis"))
    print("   ", keep_hub_off([to_global(target_world)]))
    QtCore, QtGui = q.QtCore, q.QtGui
    E = QtCore.QEvent
    target = QtCore.QPoint(*to_global(target_world))
    d = listdrag._DRAGS.get(window._LIST)
    port = d.list.viewport()
    start = d.list.visualItemRect(d.list.item(row_of(LONGSWORD) - 1)).center()

    def mouse(kind, local=None, global_point=None, button=QtCore.Qt.LeftButton,
              buttons=QtCore.Qt.LeftButton):
        global_point = global_point or port.mapToGlobal(local)
        local = local if local is not None else port.mapFromGlobal(global_point)
        event = QtGui.QMouseEvent(kind, QtCore.QPointF(local), QtCore.QPointF(global_point),
                                  button, buttons, QtCore.Qt.NoModifier)
        q.QtWidgets.QApplication.sendEvent(port, event)

    mouse(E.MouseButtonPress, local=start)
    mouse(E.MouseMove, local=start + QtCore.QPoint(40, 0), button=QtCore.Qt.NoButton)
    mouse(E.MouseMove, global_point=target, button=QtCore.Qt.NoButton)
    d.caption_at(target, force=True)
    caption = d.ghost().text if d.ghost() else ""
    mouse(E.MouseButtonRelease, global_point=target, buttons=QtCore.Qt.NoButton)
    gate(12, "Skeleton picked, a clip dragged onto a skeleton's pelvis: the ghost names it",
         caption == "%s · onto Manny UE5 [skeleton] (root)" % LONGSWORD
         and d.dragging() is None,
         "caption '%s' said '%s'" % (caption, d.status_text))


def phase_measure_drag():
    said = status()
    root = cmds.ls(WORLD["drag_uuid"], long=True)[0]
    cm, rot, turn, tilt, place, facing = rigid_check(root, LONGSWORD, range(0, 40, 4))
    gate(13, "that skeleton took the clip in its place: (-120, 30) facing 0, every bone on "
             "the moved clip",
         cm < 1e-3 and rot < 1e-3 and abs(place[0] + 120) < 1e-3 and abs(place[1] - 30) < 1e-3
         and abs(facing) < 1e-3 and "kept in place at (-120, 30)" in said
         and not clip_namespaces(),
         "off %.2e cm rot %.2e | at (%.3f, %.3f) facing %.4f | '%s'" % (
             cm, rot, place[0], place[1], facing, said[:240]))


{"card": phase_card, "photo": phase_photo, "modes": phase_modes,
 "rig_onto": phase_rig_onto, "skel_new": phase_skel_new, "skel_onto": phase_skel_onto,
 "skel_refuse": phase_skel_refuse, "drag_skel": phase_drag_skel,
 "measure_drag": phase_measure_drag}[PHASE]()
print("%s: %s" % (PHASE, "FAILURES %s" % FAILED if FAILED else "all gates passed"))
