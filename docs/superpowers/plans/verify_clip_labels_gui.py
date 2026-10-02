"""verify_clip_labels_gui.py - the clip labels SEEN (2026-10-02), in a DISPOSABLE GUI Maya.

It adds rigs and opens new scenes: its own MAYA_APP_DIR, MAYA_NO_HOME=1, its own port, never the
animator's Maya. No Unreal editor: the editor's export is replaced by UE clips on disk. Each send
sets PHASE (and REPO, the plugin folder to prove) first:

    PHASE = "square"     gates 1-4, 9: a batch of four clips onto New rig (`lineimport.run`, the
                         Import Animation button's own road) - four rigs on a 2 x 2 square, each
                         with its clip's label; playblasts from a three-quarter working camera
                         with one label (or one body) hidden at a time: each label's ink is
                         drawn, stands at its own character's feet and overlaps no other; a
                         marquee over the whole view selects the rigs and no label; the
                         contrast behind every label's ink for the hub's colour tokens, on the
                         default and a dark background; the pictures clip_labels_square.png and
                         clip_labels_square_dark.png
    PHASE = "drag"       the UE list on the hub, `listdrag.drop_at` of a clip onto empty floor;
                         the drop's import runs on the next idle, AFTER the send - so:
    PHASE = "drag_rig1"  gate 5: a new rig on the point, labelled with it; a second clip
                         dropped onto the standing rig
    PHASE = "drag_rig2"  its label read; a third clip dropped onto it
    PHASE = "drag_end"   gate 6: labelled, then relabelled with the second clip;
                         clip_labels_drag.png

Spec: docs/superpowers/specs/2026-10-02-clip-labels-design.md
"""

import math
import os
import sys

REPO = globals().get("REPO", "C:/!!!Work/MayaScripts/SkeldarAnim")
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402
import maya.api.OpenMayaUI as omui  # noqa: E402

PHASE = globals().get("PHASE", "square")
OUT = globals().get("OUT", os.path.join(os.path.dirname(REPO), "docs", "superpowers", "plans"))
FAILED = []
WORLD = sys.__dict__.setdefault("_verify_clip_labels_gui", {})
EXPORT = "C:/!!!Work/Animations/Export/"
CLIPS = {"LongSword_Attack_Right_Heavy_1P": EXPORT + "LongSword_Attack_Right_Heavy_1P.FBX",
         "ShortSword_Attack_Thrust_3P": EXPORT + "ShortSword_Attack_Thrust_3P.FBX",
         "ShortSword_Walk_1P": EXPORT + "ShortSword_Walk_1P.fbx",
         "Sword_Idle": EXPORT + "Sword_Idle.fbx",
         "Sword_Idle_02": EXPORT + "Sword_Idle_02.fbx",
         "ShortSword_Jump_1P": EXPORT + "ShortSword_Jump_1P.fbx"}
SQUARE = ["LongSword_Attack_Right_Heavy_1P", "ShortSword_Attack_Thrust_3P",
          "ShortSword_Walk_1P", "Sword_Idle"]
PANEL = "modelPanel4"
W, H = 1280, 720


def gate(number, text, ok, detail=""):
    print("gate %2d %s  %s  %s" % (number, "PASS" if ok else "FAIL", text, detail))
    if not ok:
        FAILED.append(number)


def purge():
    for name in list(sys.modules):
        if name.split(".")[0] in ("maya_scenesetup", "maya_uebridge", "maya_overrig", "maya_rigs",
                                  "maya_hub", "maya_hubqt", "maya_hubstyle", "maya_rig_retarget",
                                  "maya_asretarget", "maya_pmretarget", "maya_com", "maya_inventory",
                                  "maya_invlook", "maya_chargrid", "maya_charlook", "maya_armorgrid"):
            sys.modules.pop(name, None)


def settle():
    try:
        from PySide6 import QtWidgets
        QtWidgets.QApplication.processEvents()
    except Exception:                                        # noqa: BLE001
        pass
    cmds.refresh(force=True)


def wt(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def choose(model, kind):
    cmds.optionVar(stringValue=("mayaSceneSetup_characterModel", model))
    cmds.optionVar(stringValue=("mayaSceneSetup_characterKind", kind))


def camera():
    cam = "clipLabelsCam"
    if not cmds.objExists(cam):
        cam = cmds.camera(name=cam)[0]
    cmds.setAttr(cam + ".focalLength", 35)
    cmds.modelPanel(PANEL, edit=True, camera=cam)
    cmds.modelEditor(PANEL, edit=True, displayAppearance="smoothShaded", grid=False,
                     displayTextures=True, dimensions=True)
    return cam


def idle():
    import maya.utils
    for _ in range(4):
        maya.utils.processIdleEvents()
        settle()


def blast(path, dimensions=True):
    """A JPG (a PNG's transparent background reads white, CLAUDE.md); `.png` asked for is
    written from the JPG through MImage."""
    cmds.modelEditor(PANEL, edit=True, dimensions=dimensions)
    idle()
    jpg = os.path.splitext(path)[0] + ".jpg"
    cmds.playblast(completeFilename=jpg, format="image", compression="jpg", frame=[0],
                   viewer=False, showOrnaments=False, offScreen=True, percent=100,
                   widthHeight=(W, H), forceOverwrite=True, quality=100)
    cmds.modelEditor(PANEL, edit=True, dimensions=True)
    if path.lower().endswith(".png"):
        img = om.MImage()
        img.readFromFile(jpg)
        img.writeToFile(path, "png")
        os.remove(jpg)
        return path
    return jpg


def textures_loaded(path):
    """Blast until two blasts in a row agree (Viewport 2.0 loads textures only while idle,
    trap 120); at least three."""
    last = None
    for attempt in range(12):
        _w, _h, img = image(blast(path))
        if attempt >= 2 and img == last:
            return attempt + 1
        last = img
    return -1


def luminance(r, g, b):
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def behind(masks, hidden):
    """The luminances behind every ink pixel: [(mask, the image with that label hidden)]."""
    out = []
    for mask, raw in zip(masks, hidden):
        for i in range(len(mask)):
            if mask[i]:
                j = 4 * i
                out.append(luminance(raw[j], raw[j + 1], raw[j + 2]))
    return out


def percentile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))] if values else 0.0


def image(path):
    img = om.MImage()
    img.readFromFile(path)
    w, h = img.getSize()
    import ctypes
    raw = ctypes.string_at(img.pixels(), w * h * 4)
    return w, h, raw


def bbox(mask, w, h):
    """(x0, y0, x1, y1 from the top, count) of the set pixels, or None. MImage rows run
    from the bottom of the picture."""
    xs, ys, count = [], [], 0
    for i in range(w * h):
        if mask[i]:
            xs.append(i % w)
            ys.append(h - 1 - i // w)
            count += 1
    if not count:
        return None
    # trimmed to the 2nd..98th percentile: a stray changed pixel elsewhere (a texture
    # filtered differently between two blasts) must not stretch the box across the picture
    xs.sort()
    ys.sort()
    lo, hi = int(0.02 * count), max(0, int(0.98 * count) - 1)
    return xs[lo], ys[lo], xs[hi], ys[hi], count


def diff_mask(a, b, w, h):
    out = bytearray(w * h)
    for i in range(w * h):
        j = 4 * i
        if abs(a[j] - b[j]) + abs(a[j + 1] - b[j + 1]) + abs(a[j + 2] - b[j + 2]) > 30:
            out[i] = 1
    return out


def phase_square():
    purge()
    from maya_scenesetup import cliplabel
    from maya_uebridge import lineimport
    import maya_rigs
    print("plugin from", os.path.dirname(cliplabel.__file__))
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    choose("Manny", "rig")
    import types
    line = lineimport.run([types.SimpleNamespace(name=n) for n in SQUARE],
                          lambda r: (CLIPS[r.name], 30), "new_rig")
    print(line)
    rigs = maya_rigs.rigs()
    labels = {}
    for rig in rigs:
        found = cliplabel.labels_of(rig.skeleton_root)
        if len(found) == 1:
            labels[rig.namespace] = found[0]
    gate(1, "four rigs, each with one label reading its clip",
         len(rigs) == 4 and len(labels) == 4
         and sorted(cliplabel.text_of(l) for l in labels.values()) == sorted(SQUARE),
         dict((k, cliplabel.text_of(v)) for k, v in labels.items()))

    cmds.currentTime(0)
    cam = camera()
    # a working camera: three-quarter, from above, the whole square in view
    cmds.viewPlace(cam, eye=(380.0, 560.0, 1080.0), lookAt=(0.0, 40.0, 0.0))
    settle()
    WORLD["cam"] = cam
    scratch = os.path.join(OUT, "_clip_labels_probe.jpg")
    print("textures settled after %d blasts" % textures_loaded(scratch))
    shown = blast(os.path.join(OUT, "clip_labels_square.png"))
    w, h, full = image(shown)
    # Where each label's ink is and where each body is: hide one, blast, diff - no projection
    # arithmetic to get wrong.
    ink, body, masks, hidden = {}, {}, [], []
    for rig in rigs:
        label = labels[rig.namespace]
        cmds.setAttr(label + ".visibility", 0)
        _w, _h, img = image(blast(scratch))
        cmds.setAttr(label + ".visibility", 1)
        mask = diff_mask(full, img, w, h)
        masks.append(mask)
        hidden.append(img)
        ink[rig.namespace] = bbox(mask, w, h)
        meshes = set()
        for shape in cmds.ls(rig.namespace + ":*", type="mesh", long=True) or []:
            if not cmds.getAttr(shape + ".intermediateObject"):
                meshes.add(cmds.listRelatives(shape, parent=True, fullPath=True)[0])
        meshes = sorted(meshes)
        was = [cmds.getAttr(m + ".visibility") for m in meshes]
        for m in meshes:
            cmds.setAttr(m + ".visibility", 0)
        _w, _h, img = image(blast(scratch))
        for m, v in zip(meshes, was):
            cmds.setAttr(m + ".visibility", v)
        body[rig.namespace] = bbox(diff_mask(full, img, w, h), w, h)

    # What lies behind each label's ink, on the default background and on a dark one: the
    # contrast every candidate colour would have there (WCAG ratio, the worst tenth).
    old = cmds.displayRGBColor("background", query=True)
    cmds.displayRGBColor("background", 0.07, 0.07, 0.08)
    dark = []
    for rig in rigs:
        label = labels[rig.namespace]
        cmds.setAttr(label + ".visibility", 0)
        _w, _h, img = image(blast(scratch))
        cmds.setAttr(label + ".visibility", 1)
        dark.append(img)
    cmds.displayRGBColor("background", *old)
    grey_l, dark_l = behind(masks, hidden), behind(masks, dark)
    import maya_hubstyle
    table = {}
    for key in ("muted", "text", "text2", "accent", "accent_text", "ok", "faint"):
        c = cliplabel.colour_of(maya_hubstyle.TOKENS[key])
        lc = luminance(*(v * 255 for v in c))
        ratios_g = [contrast(lc, l) for l in grey_l]
        ratios_d = [contrast(lc, l) for l in dark_l]
        table[key] = (round(percentile(ratios_g, 0.1), 2), round(percentile(ratios_d, 0.1), 2),
                      round(min(percentile(ratios_g, 0.1), percentile(ratios_d, 0.1)), 2))
    best = max(table, key=lambda k: table[k][2])
    chosen = [k for k, v in maya_hubstyle.TOKENS.items()
              if v.lower() == cliplabel.COLOUR.lower() and k in table]
    print("colour (grey p10, dark p10, worst):", table, "best", best, "ours", chosen)
    WORLD["colours"] = table
    gate(9, "our colour keeps the worst tenth of the ink at a contrast of 2 or more, on the "
            "default and a dark background (the hue does the rest)",
         bool(chosen) and table[chosen[0]][2] >= 2.0,
         "ours %s %s, best by luminance %s %s" % (chosen, table[chosen[0]] if chosen else None,
                                                  best, table[best]))
    try:
        os.remove(scratch)
    except OSError:
        pass
    gate(2, "each label's ink is drawn (hidden against shown)",
         all(b and b[4] > 150 for b in ink.values()),
         dict((k, v[4] if v else 0) for k, v in ink.items()))
    placed, overlaps = {}, []
    for ns in ink:
        lb, bb = ink[ns], body[ns]
        if not (lb and bb):
            placed[ns] = None
            continue
        cx, cy = (lb[0] + lb[2]) / 2.0, (lb[1] + lb[3]) / 2.0
        feet, height = bb[3], bb[3] - bb[1]
        placed[ns] = (bb[0] <= cx <= bb[2], round((cy - feet) / float(height), 3))
    names = sorted(ink)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if ink[a] and ink[b] and not (ink[a][2] < ink[b][0] or ink[b][2] < ink[a][0]
                                          or ink[a][3] < ink[b][1] or ink[b][3] < ink[a][1]):
                overlaps.append((a, b))
    gate(3, "each label under its own character's feet (x inside the body, y at the feet), "
            "no two overlapping",
         all(p and p[0] and -0.15 < p[1] < 0.25 for p in placed.values()) and not overlaps,
         "(x inside, y below the feet in body heights) %s, overlaps %s; ink %s; bodies %s"
         % (placed, overlaps, ink, body))

    # a marquee over the whole view: the meshes come, the labels do not
    view = omui.M3dView.getM3dViewFromModelPanel(PANEL)
    cmds.select(clear=True)
    settle()
    om.MGlobal.selectFromScreen(0, 0, view.portWidth(), view.portHeight(),
                                om.MGlobal.kReplaceList)
    picked = cmds.ls(selection=True, long=True) or []
    labelled = [p for p in picked if p in labels.values()]
    gate(4, "a marquee over the whole view takes the rigs and no label",
         len(picked) > 4 and not labelled, "%d picked, labels %s" % (len(picked), labelled))
    cmds.select(clear=True)

    cmds.displayRGBColor("background", 0.07, 0.07, 0.08)
    blast(os.path.join(OUT, "clip_labels_square_dark.png"))
    cmds.displayRGBColor("background", *old)


def window_status():
    from maya_uebridge import window
    try:
        return cmds.text(window._STATUS, query=True, label=True) or ""
    except RuntimeError:
        return ""


def to_global(world):
    from PySide6 import QtCore, QtWidgets
    import shiboken6
    view = omui.M3dView.getM3dViewFromModelPanel(PANEL)
    widget = shiboken6.wrapInstance(int(view.widget()), QtWidgets.QWidget)
    x, y, _clipped = view.worldToView(om.MPoint(*world))
    sx = view.portWidth() / float(widget.width())
    sy = view.portHeight() / float(widget.height())
    local = QtCore.QPoint(int(round(x / sx)), int(round(widget.height() - y / sy)))
    point = widget.mapToGlobal(local)
    return point.x(), point.y()


DRAG_FLOOR = (140.0, 0.0, 0.0)
RIG_CLIPS = ("ShortSword_Walk_1P", "ShortSword_Jump_1P")


def _drag_tools():
    import maya_rigs
    from maya_scenesetup import cliplabel
    from maya_uebridge import listdrag, window
    return maya_rigs, cliplabel, listdrag._DRAGS.get("ueAnimBridgeList"), window


def _by_name(window):
    return dict((r.name, r) for r in window._STATE["records"])


def _drop_on_rig(clip):
    maya_rigs, cliplabel, drag, window = _drag_tools()
    rig_a = maya_rigs.find(WORLD["rig_a"])
    cmds.currentTime(0)
    settle()
    px, py = to_global(wt(rig_a.namespace + ":pelvis"))
    print("rig drop:", drag.drop_at(px, py, _by_name(window)[clip]))


def _rig_labels():
    maya_rigs, cliplabel, _drag, _window = _drag_tools()
    rig_a = maya_rigs.find(WORLD["rig_a"])
    found = cliplabel.labels_of(rig_a.skeleton_root)
    return [cliplabel.text_of(l) for l in found], set(cmds.ls(found, uuid=True) or [])


def phase_drag():
    """The scene, the hub, the list, and a clip released on the empty floor. Its import runs
    on the next idle - after this send - so the next phase measures it."""
    purge()
    import maya_hub
    import maya_hubqt
    import maya_rigs
    from maya_uebridge import listdrag, records, window
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    choose("Manny", "rig")
    from maya_scenesetup import catalog, character
    character.add_character(catalog.default_rig(), at=(-120.0, 0.0, 0.0))
    maya_hub.show("characters")
    settle()
    if cmds.workspaceControl("skeldarAnimHub", exists=True):
        cmds.workspaceControl("skeldarAnimHub", edit=True, floating=True)
    settle()
    window._STATE["records"] = records.parse_payload({"assets": [
        {"name": name, "package": "/Game/Verify/" + name, "fps": 30.0} for name in sorted(CLIPS)]})
    window._repopulate()
    window._export_from_editor = lambda record: (CLIPS[record.name], 30.0)
    cam = camera()
    cmds.setFocus(PANEL)
    cmds.viewPlace(cam, eye=(150.0, 420.0, 900.0), lookAt=(0.0, 40.0, 0.0))
    settle()
    drag = listdrag._DRAGS.get("ueAnimBridgeList")
    rig_a = maya_rigs.rigs()[0]
    WORLD["rig_a"] = rig_a.namespace
    pelvis = wt(rig_a.namespace + ":pelvis")
    top = maya_hubqt.find("skeldarAnimHub").window()
    screen = top.screen().availableGeometry()
    for x, y in ((screen.left(), screen.top()), (screen.right() - top.width(), screen.top()),
                 (screen.left(), screen.bottom() - top.height())):
        top.move(x, y)
        settle()
        pts = [to_global(DRAG_FLOOR), to_global(pelvis)]
        if not any(maya_hubqt.on_hub(px, py) for px, py in pts):
            break
    fx, fy = to_global(DRAG_FLOOR)
    print("floor drop:", drag.drop_at(fx, fy, _by_name(window)["ShortSword_Attack_Thrust_3P"]))


def phase_drag_rig1():
    maya_rigs, cliplabel, _drag, window = _drag_tools()
    new = [r for r in maya_rigs.rigs() if r.namespace != WORLD["rig_a"]]
    labels = cliplabel.labels_of(new[0].skeleton_root) if new else []
    cmds.currentTime(0)
    settle()
    landed = wt(new[0].main) if new else None
    print("status:", window_status())
    gate(5, "a clip dropped on the floor: a new rig on the point, labelled with it",
         len(new) == 1 and len(labels) == 1
         and cliplabel.text_of(labels[0]) == "ShortSword_Attack_Thrust_3P"
         # the drop lands where the cursor's PIXEL meets the floor: ~1-2 cm a pixel here
         and landed and math.hypot(landed[0] - DRAG_FLOOR[0], landed[2] - DRAG_FLOOR[2]) < 5.0,
         "%s, Main at %s" % ([cliplabel.text_of(l) for l in labels], landed))
    _drop_on_rig(RIG_CLIPS[0])


def phase_drag_rig2():
    texts, nodes = _rig_labels()
    WORLD["after1"] = (texts, nodes)
    print("status:", window_status())
    _drop_on_rig(RIG_CLIPS[1])


def phase_drag_end():
    texts1, nodes1 = WORLD["after1"]
    texts2, nodes2 = _rig_labels()
    print("status:", window_status())
    # Since the 2026-10-02 fix pass the reset in front of a drop onto a standing rig takes the
    # old label with the take, and the press writes a fresh one: one label, the new text.
    gate(6, "two clips dropped in turn onto the standing rig: labelled, then relabelled with the "
            "second clip, one label throughout",
         texts1 == [RIG_CLIPS[0]] and texts2 == [RIG_CLIPS[1]]
         and len(nodes1) == 1 and len(nodes2) == 1, "%s -> %s" % (texts1, texts2))
    cmds.currentTime(0)
    scratch = os.path.join(OUT, "_clip_labels_probe.jpg")
    textures_loaded(scratch)
    try:
        os.remove(scratch)
    except OSError:
        pass
    blast(os.path.join(OUT, "clip_labels_drag.png"))


try:
    {"square": phase_square, "drag": phase_drag, "drag_rig1": phase_drag_rig1,
     "drag_rig2": phase_drag_rig2, "drag_end": phase_drag_end}[PHASE]()
except Exception:
    import traceback
    traceback.print_exc()
    FAILED.append("crashed")
print("PHASE %s: %s" % (PHASE, "FAILED %s" % FAILED if FAILED else "all gates passed"))
