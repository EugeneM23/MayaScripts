"""Live proof of several UE Bridge animations at once (2026-10-01).

Run in a DISPOSABLE Maya (it opens new scenes and adds rigs): its own
MAYA_APP_DIR, MAYA_NO_HOME=1, its own port. No Unreal editor: the editor's
export is replaced by FBX clips on disk. Each send sets PHASE first:

    PHASE = "setup"         gates 1-2: the hub on UE Bridge, the list taking a
                            multiple selection, three clips listed; each
                            clip's root track walked frame by frame
                            (currentTime) on a plain import - the measure the
                            press's own time-context read is held against
    PHASE = "button_new"    gates 3-5: three picked, New rig, Import - three
                            rigs, Main at each clip's first frame on its slot
                            of a 2 x 2 square about the origin (row 0 in
                            front, left to right), no two root paths within
                            a step, the timeline the union, no clip skeleton
                            left
    PHASE = "button_skel"   gate 6: Skeleton mode - three skeletons on the
                            same square, each playing its own keys moved
    PHASE = "button_rig"    gate 7: Rig mode, one rig selected - the first
                            clip only, and the status says so
    PHASE = "drag_floor"    gate 8: a real press-drag-release of the three
                            picked rows onto empty floor, the camera looking
                            along X; the ghost names the square, the list
                            keeps the three picked
    PHASE = "measure_floor" gate 9: three rigs on the same 2 x 2 square, on the
                            world's axes about the floor point whatever the
                            camera - the thrust's 2.5 m of forward travel
                            widening its row
    PHASE = "drag_rig"      gate 10: the three dragged onto the middle rig
    PHASE = "measure_rig"   gate 11: that rig took the first clip only, the
                            other two never moved

Spec: docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md
"""

import math
import re
import sys

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402

PHASE = globals().get("PHASE", "setup")
FAILED = []
WORLD = sys.__dict__.setdefault("_verify_uebridge_many", {})   # across sends

EXPORT = "C:/!!!Work/Animations/Export/"
CLIPS = {"LongSword_Attack_Right_Heavy_1P": EXPORT + "LongSword_Attack_Right_Heavy_1P.FBX",
         "ShortSword_Attack_Thrust_3P": EXPORT + "ShortSword_Attack_Thrust_3P.FBX",
         "ShortSword_Walk_1P": EXPORT + "ShortSword_Walk_1P.fbx"}
ORDER = sorted(CLIPS)               # the list's order
FIRST = ORDER[0]
STEP = 250.0


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


def clip_namespaces():
    return [ns for ns in (cmds.namespaceInfo(":", listOnlyNamespaces=True) or [])
            if any(name in ns for name in CLIPS)]


def status():
    from maya_uebridge import window
    return cmds.text(window._STATUS, query=True, label=True) or ""


def click_mode(mode):
    import maya_hubqt
    from maya_uebridge import window
    q = maya_hubqt.qt()
    widget = maya_hubqt.find(window.mode_button(mode))
    button = q.shiboken.wrapInstance(int(q.shiboken.getCppPointer(widget)[0]),
                                     q.QtWidgets.QAbstractButton)
    button.click()
    q.QtWidgets.QApplication.processEvents()


def pick_rows(rows):
    from maya_uebridge import window
    cmds.textScrollList(window._LIST, edit=True, deselectAll=True)
    for row in rows:
        cmds.textScrollList(window._LIST, edit=True, selectIndexedItem=row)
    settle()
    return sorted(cmds.textScrollList(window._LIST, query=True, selectIndexedItem=True) or [])


def choose_manny():
    cmds.optionVar(stringValue=("mayaSceneSetup_characterModel", "Manny"))
    cmds.optionVar(stringValue=("mayaSceneSetup_characterKind", "rig"))


def drag():
    import maya_hubqt
    from maya_uebridge import listdrag
    found = listdrag._DRAGS.get("ueAnimBridgeList")
    return found if found is not None and maya_hubqt.qt().shiboken.isValid(found) else None


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


def expected_slots(centre):
    """The square's slots about `centre`, from the clips' own root tracks
    walked frame by frame on a plain import (setup)."""
    from maya_uebridge import lineup
    x = [lineup.side_extent(WORLD["tracks"][name], lineup.COLUMNS) for name in ORDER]
    z = [lineup.side_extent(WORLD["tracks"][name], lineup.ROWS) for name in ORDER]
    return lineup.square_slots(centre, x, z, STEP), (x, z)


def owners(said):
    """{clip: rig namespace} read off the summary's "Manny_Rig1 A_Jump" pairs."""
    out = {}
    for name in ORDER:
        found = re.search(r"(\S+) %s(?:,|  |$)" % re.escape(name), said)
        if found:
            out[name] = found.group(1).rstrip(":")
    return out


def path_of(node, last):
    """((x lo, x hi), (z lo, z hi)) of the node's world path over 0..last."""
    xs, zs = [], []
    for frame in range(0, last + 1):
        cmds.currentTime(frame, update=True)
        point = world_t(node)
        xs.append(point[0])
        zs.append(point[2])
    return (min(xs), max(xs)), (min(zs), max(zs))


def clearance(paths):
    """The least gap between two rigs' root paths: along X for rigs in two
    columns, along Z for two in one column."""
    from maya_uebridge import lineup
    columns, _rows = lineup.grid_shape(len(paths))
    gaps = []
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            axis = 0 if i % columns != j % columns else 1
            a, b = paths[i][axis], paths[j][axis]
            gaps.append(max(b[0] - a[1], a[0] - b[1]))
    return min(gaps) if gaps else None


def check_line(number, text, said, centre, before):
    """The new rigs: Main at frame 0 on its slot of the square; no two root
    paths within a step; every rig animated."""
    slots, extents = expected_slots(centre)
    own = owners(said)
    new = sorted(set(rigs()) - set(before))
    worst, moving, detail = 0.0, [], []
    ok = len(new) == 3 and len(own) == 3 and all(ns in new for ns in own.values())
    paths = []
    if ok:
        for name, slot in zip(ORDER, slots):
            ns = own[name]
            cmds.currentTime(0, update=True)
            main = world_t(ns + ":Main")
            off = math.hypot(main[0] - slot[0], main[2] - slot[2])
            worst = max(worst, off)
            last = int(WORLD["ends"][name])
            paths.append(path_of(ns + ":root", last))
            hand = []
            for frame in range(0, last + 1, 3):
                cmds.currentTime(frame, update=True)
                hand.append(world_t(ns + ":hand_r"))
            moving.append(max(dist(hand[0], p) for p in hand))
            detail.append("%s %s Main (%.3f, %.3f) slot (%.3f, %.3f)" % (
                ns, name[:14], main[0], main[2], slot[0], slot[2]))
    least = clearance(paths) if ok else None
    gate(number, text,
         ok and worst < 1e-3 and least is not None and least > STEP - 0.05
         and all(m > 0.5 for m in moving) and not clip_namespaces(),
         "%s | Main off its slot %.2e | least clearance between root paths %s | "
         "hand_r travels %s | left %s | reach x %s z %s" % (
             "; ".join(detail), worst, None if least is None else round(least, 3),
             [round(m, 2) for m in moving], clip_namespaces(),
             [tuple(round(v, 2) for v in e) for e in extents[0]],
             [tuple(round(v, 2) for v in e) for e in extents[1]]))
    return own


# ------------------------------------------------------------------ phases

def phase_setup():
    import maya_hub
    import maya_hubqt
    from maya_uebridge import animimport, records, window

    cmds.file(new=True, force=True)
    maya_hub.show("uebridge")
    settle()
    window._STATE["records"] = records.parse_payload({"assets": [
        {"name": name, "package": "/Game/Verify/" + name, "fps": 30.0} for name in ORDER]})
    window._repopulate()
    window._export_from_editor = lambda record: (CLIPS[record.name], 30.0)
    rows = cmds.textScrollList(window._LIST, query=True, allItems=True) or []
    multi = cmds.textScrollList(window._LIST, query=True, allowMultiSelection=True)
    d = drag()
    mode = None
    if d is not None:
        mode = getattr(d.list.selectionMode(), "name", str(d.list.selectionMode()))
    picked = pick_rows([1, 2, 3])
    qt_picked = sorted(i.row() for i in d.list.selectionModel().selectedIndexes()) if d else []
    gate(1, "the list takes several: three rows, all three picked by cmds and seen by Qt",
         len(rows) == 3 and multi and picked == [1, 2, 3] and qt_picked == [0, 1, 2]
         and [r.name for r in window._STATE["filtered"]] == ORDER
         and rows == [records.format_row(r) for r in window._STATE["filtered"]],
         "rows %s | multi %s | Qt mode %s | cmds %s Qt %s" % (rows, multi, mode, picked, qt_picked))

    # the reference: each clip's root, walked frame by frame on a plain import
    tracks, ends, starts = {}, {}, {}
    for name in ORDER:
        info = animimport.import_clip(CLIPS[name], "vmClip", set_timeline=False,
                                      clip_fps=30.0, merge=False)
        root = cmds.ls("vmClip:root", long=True)[0]
        track = []
        for frame in range(int(info["start"]), int(info["end"]) + 1):
            cmds.currentTime(frame, update=True)
            track.append(tuple(world_t(root)))
        tracks[name], ends[name], starts[name] = track, info["end"], info["start"]
        cmds.namespace(removeNamespace="vmClip", deleteNamespaceContent=True)
    WORLD.update(tracks=tracks, ends=ends, starts=starts)
    thrust = tracks["ShortSword_Attack_Thrust_3P"]
    reach = max(dist(thrust[0], p) for p in thrust)
    gate(2, "the clips' root tracks measured; the thrust travels, the other two stand",
         reach > 200.0 and all(max(dist(tracks[n][0], p) for p in tracks[n]) < 1e-6
                               for n in ORDER if n != "ShortSword_Attack_Thrust_3P"),
         "thrust reach %.1f, start %s, ranges %s" % (
             reach, [round(v, 2) for v in thrust[0]], [(starts[n], ends[n]) for n in ORDER]))


def phase_button_new():
    from maya_uebridge import window
    cmds.file(new=True, force=True)
    choose_manny()
    cmds.playbackOptions(minTime=100, maxTime=110)
    picked = pick_rows([1, 2, 3])
    click_mode("new_rig")
    before = list(rigs())
    window._run(window.import_selected)
    said = status()
    print("    status: %s" % said)
    own = check_line(3, "New rig, three picked: three rigs on their slots of a 2 x 2 square "
                        "about the origin, no two paths within a step", said,
                     (0.0, 0.0, 0.0), before)
    span = (cmds.playbackOptions(query=True, minTime=True),
            cmds.playbackOptions(query=True, maxTime=True))
    want = (min(WORLD["starts"].values()), max(WORLD["ends"].values()))
    gate(4, "the timeline is the union of the three clips' ranges",
         picked == [1, 2, 3] and abs(span[0] - want[0]) < 1e-6 and abs(span[1] - want[1]) < 1e-6,
         "%s vs %s" % (span, want))
    gate(5, "the status names each rig with its clip and the widened gap",
         "3 animations onto 3 new rigs in a 2 x 2 square about (0, 0)" in said and len(own) == 3
         and "widened beside ShortSword_Attack_Thrust_3P" in said, said[:300])


def phase_button_skel():
    from maya_uebridge import window
    cmds.file(new=True, force=True)
    pick_rows([1, 2, 3])
    click_mode("skeleton")
    window._run(window.import_selected)
    said = status()
    print("    status: %s" % said)
    slots, _extents = expected_slots((0.0, 0.0, 0.0))
    worst, found = 0.0, []
    for name, slot in zip(ORDER, slots):
        root = (cmds.ls(name + ":root", long=True) or [None])[0]
        found.append(root)
        if root is None:
            continue
        track = WORLD["tracks"][name]
        move = (slot[0] - track[0][0], 0.0, slot[2] - track[0][2])
        for frame, point in enumerate(track):
            cmds.currentTime(WORLD["starts"][name] + frame, update=True)
            want = (point[0] + move[0], point[1], point[2] + move[2])
            worst = max(worst, dist(world_t(root), want))
    gate(6, "Skeleton, three picked: three skeletons, each root playing its own keys moved "
            "onto its slot of the square about the origin",
         all(found) and worst < 1e-3 and not rigs()
         and all("skeldarDropShift" in r for r in found)
         and "3 animations as skeletons in a 2 x 2 square about (0, 0)" in said,
         "roots %s | off the moved clip %.2e | '%s'" % (found, worst, said[:200]))


def phase_button_rig():
    from maya_scenesetup import catalog, character
    from maya_uebridge import window
    cmds.file(new=True, force=True)
    choose_manny()
    character.add_character(catalog.default_rig())
    only = list(rigs())
    cmds.select(rigs()[only[0]].main, replace=True)
    pick_rows([1, 2, 3])
    click_mode("rig")
    window._run(window.import_selected)
    said = status()
    print("    status: %s" % said)
    ns = only[0]
    hand = []
    for frame in range(0, int(WORLD["ends"][FIRST]) + 1, 3):
        cmds.currentTime(frame, update=True)
        hand.append(world_t(ns + ":hand_r"))
    gate(7, "Rig, three picked: the first clip only onto the selected rig, and it says so",
         sorted(rigs()) == only and not clip_namespaces()
         and ("%s retargeted onto %s" % (FIRST, ns)) in said
         and ("only %s: a rig takes one animation (2 more picked)" % FIRST) in said
         and max(dist(hand[0], p) for p in hand) > 0.5,
         "'%s'" % said[:300])


def _drag_rows(press_row, target_world, number, text, want_caption):
    """A real press - drag - release through Qt on the list, the three rows
    picked, the press on the picked row `press_row` (0-based)."""
    import maya_hubqt
    from maya_uebridge import window
    q = maya_hubqt.qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    E = QtCore.QEvent
    picked = pick_rows([1, 2, 3])
    target = to_global(target_world)
    print("   ", keep_hub_off([target]))
    target = QtCore.QPoint(*to_global(target_world))
    d = drag()
    port = d.list.viewport()
    start = d.list.visualItemRect(d.list.item(press_row)).center()

    def mouse(kind, local=None, global_point=None, button=QtCore.Qt.LeftButton,
              buttons=QtCore.Qt.LeftButton):
        global_point = global_point or port.mapToGlobal(local)
        local = local if local is not None else port.mapFromGlobal(global_point)
        event = QtGui.QMouseEvent(kind, QtCore.QPointF(local), QtCore.QPointF(global_point),
                                  button, buttons, QtCore.Qt.NoModifier)
        q.QtWidgets.QApplication.sendEvent(port, event)

    mouse(E.MouseButtonPress, local=start)
    mouse(E.MouseMove, local=start + QtCore.QPoint(40, 0), button=QtCore.Qt.NoButton)
    carried = [r.name for r in d.carried()]
    mouse(E.MouseMove, global_point=target, button=QtCore.Qt.NoButton)
    d.caption_at(target, force=True)
    caption = d.ghost().text if d.ghost() else ""
    aim = d.scene.target(target.x(), target.y(), d._drag["snap"]) if d._drag else {}
    mouse(E.MouseButtonRelease, global_point=target, buttons=QtCore.Qt.NoButton)
    after = sorted(cmds.textScrollList(window._LIST, query=True, selectIndexedItem=True) or [])
    gate(number, text,
         picked == [1, 2, 3] and carried == ORDER and d.dragging() is None
         and want_caption(caption) and after == [1, 2, 3],
         "carried %s | caption '%s' | said '%s' | list kept %s" % (
             carried, caption, d.status_text, after))
    return aim


def phase_drag_floor():
    cmds.file(new=True, force=True)
    choose_manny()
    cmds.viewPlace("persp", eye=(900.0, 320.0, 0.0), lookAt=(0.0, 90.0, 0.0))
    settle()
    WORLD["before_floor"] = list(rigs())
    point = (0.0, 0.0, 0.0)
    aim = _drag_rows(1, point, 8, "three picked dragged onto empty floor, the press on the "
                                  "second: all three carried, the ghost names a square of "
                                  "three new rigs, the list keeps them picked",
                     lambda c: c.startswith("3 animations · 3 new Manny [rig] in a square · floor"))
    WORLD["floor"] = aim.get("point")
    print("    aim: %s" % (aim,))


def phase_measure_floor():
    said = status()
    print("    status: %s" % said)
    own = check_line(9, "the drop of three, the camera looking along X: the same 2 x 2 square "
                        "on the world's axes about the floor point, no two paths within a "
                        "step", said, WORLD["floor"], WORLD["before_floor"])
    WORLD["floor_owners"] = own


def phase_drag_rig():
    own = WORLD["floor_owners"]
    middle = own["ShortSword_Attack_Thrust_3P"]
    WORLD["middle"] = middle
    WORLD["others"] = [ns for name, ns in own.items() if ns != middle]
    WORLD["other_tracks"] = {}
    for ns in WORLD["others"]:
        track = []
        for frame in range(0, 40, 4):
            cmds.currentTime(frame, update=True)
            track.append(world_t(ns + ":hand_r"))
        WORLD["other_tracks"][ns] = track
    cmds.currentTime(0, update=True)
    settle()
    WORLD["rigs_before"] = sorted(rigs())
    _drag_rows(2, world_t(middle + ":pelvis"), 10,
               "three picked dragged onto the middle rig, the press on the third: all "
               "three carried, the ghost names the first onto that rig",
               lambda c: c == "%s · retarget onto %s · first of 3" % (FIRST, middle))


def phase_measure_rig():
    said = status()
    print("    status: %s" % said)
    middle = WORLD["middle"]
    drift = 0.0
    for ns, before in WORLD["other_tracks"].items():
        now = []
        for frame in range(0, 40, 4):
            cmds.currentTime(frame, update=True)
            now.append(world_t(ns + ":hand_r"))
        drift = max(drift, max(dist(p, q) for p, q in zip(before, now)))
    gate(11, "onto the rig: the first clip only, the other two rigs never moved",
         ("%s retargeted onto %s" % (FIRST, middle)) in said
         and ("only %s: a rig takes one animation (2 more picked)" % FIRST) in said
         and sorted(rigs()) == WORLD["rigs_before"] and drift < 1e-9
         and not clip_namespaces(),
         "others drift %.2e | '%s'" % (drift, said[:300]))


{"setup": phase_setup, "button_new": phase_button_new, "button_skel": phase_button_skel,
 "button_rig": phase_button_rig, "drag_floor": phase_drag_floor,
 "measure_floor": phase_measure_floor, "drag_rig": phase_drag_rig,
 "measure_rig": phase_measure_rig}[PHASE]()
print("%s: %s" % (PHASE, "FAILURES %s" % FAILED if FAILED else "all gates passed"))
