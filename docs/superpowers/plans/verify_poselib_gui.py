"""The Pose Library's window, live, in a DISPOSABLE GUI Maya (2026-10-03).

Never in the animator's Maya (port 7001): this adds rigs, keys them and starts new scenes. A
second Maya is launched for it with a scratch MAYA_APP_DIR (its own prefs, its own library),
`MAYA_NO_HOME=1`, and a userSetup opening port 7031 (in `<MAYA_APP_DIR>/2027/scripts/` too - trap
109); it is killed after. Each send runs one PHASE through `verify_poselib_gui_run.py`, sent by
`verify_poselib_gui_send.py`:

    fresh    under the GUI's PARALLEL evaluation manager, is a `getAttr .worldMatrix[0]` after a
             `setAttr` fresh? Every FK control of a Manny_Rig set level by level down the game
             skeleton (rigsolve's own order), its FKX joint, deformation joint and game bone
             read after each set - in parallel, against the same sequence in DG; then a whole
             `plan_for` onto a second rig with `rigsolve.FRESH_MODE` None (nothing switched) and
             "off", the values compared and timed, onto an unkeyed Manny_Rig, a Creep_Rig (IK
             legs, numeric toes) and a KEYED Manny_Rig (four trials); the cost of the switch (off
             and back, and the first evaluation after it) against a plain evaluation; what it
             does to Cached Playback (`cacheEvaluator -q -cachedFrames`); and the shipped
             FRESH_MODE landing the keyed rig's bones (0.01 deg). The measurements are reported,
             the shipped default gated - they are rigsolve's docstring's evidence
    stale    which read goes stale in parallel on a keyed rig: the solve's own setAttr/getAttr
             sequence recorded in DG and replayed in parallel, the first read that differs named
    open     a new scene, two Manny_Rigs (A at x -90, B at +90 turned 25 deg), A posed; the hub
             opened on its Pose Library card and its Open button CLICKED: the workspaceControl
             floating, the window standing in it; its content fits 600 px wide
    sizes    the window at 1000 x 640 and at 600 x 640 (logical): every visible button, check
             box, field, dropdown and slider at or above its size hint, every wrapped label as
             tall as its text needs, nothing outside the window or cut by the side panel's
             viewport - the details and the save panel both
    save     a Manny_Rig control selected (A's Main), + Save pose CLICKED: the save panel, its
             snapshot; Save CLICKED - a card with a thumbnail, a 320 x 320 JPG that is not blank
             (pixel spread); a second card from A's left wrist control
    list     both cards listed; the search narrows to one; a folder made (New folder, the name
             answered by the verify) and the hand card moved there by `drop_at` over the folder
             item of the tree
    drop_rig the full card `drop_at` over the projected `hand_l` of the second Manny_Rig (B,
             standing elsewhere, turned, in another pose): B takes the pose - every member bone
             on the card relative to its root to 0.01 deg, Main unchanged (verify_poselib_apply's
             tolerances); the caption first
    drop_floor the full card `drop_at` over the empty floor: the caption, the line «- adding it»;
             the drop is DEFERRED (one idle), so it is measured in the next send
    floor_check a new Manny_Rig of the card's row with Main ON the point (0.01 cm) and posed
             (0.01 deg)
    blend    A reset, selected; the Blend slider PRESSED at 50 on its groove (Qt mouse events):
             the controls previewed HALFWAY (each rotation's quaternion angle from the current
             is half the way, 0.01 deg; translations halfway); the RELEASE keys - a key at the
             frame on every channel, the mixed values, «at 50 %»
    middle   a MIDDLE drag across the full card (Qt mouse events on the canvas): the preview
             moves the controls; Esc (to the keyboard grabber, as Qt routes it) - every value
             back exactly, no curve changed, no key
    apply    the hand card picked, a part of A selected, Apply CLICKED: only the hand's controls
             change (FKWrist_L and the IK arm's end), the hand on its forearm as the card holds it
             (verify_poselib_apply's `partial`, 0.01 deg)
    photo    the window (DWM's copy of it - never `QWidget.grab()` of Maya widgets, trap 134)
             with the full card picked and with the save panel, and the viewport after the drops
             (a playblast) into docs/superpowers/plans/poselib_*.png
    close    Maya minimised again, the window closed

Widgets are found AGAIN by objectName right before each use (trap 148). A deferred action is
measured in the next send (trap 191). Every gate prints `PASS/FAIL <name> <value>`, each send
ends `SUMMARY x/y`; `ORDER` is the run (`open` clears what an earlier run left). Maya is
minimised again at the end of every send - a disposable Maya standing on the animator's screen
gets closed - and a phase that projects, picks or blasts restores it first (trap 192).

    $env:POSELIB_GUI_OUT = "<a scratch folder>"
    foreach ($p in "fresh","stale","open","save","sizes","list","drop_rig","drop_floor",
                   "floor_check","blend","middle","apply","photo","close") {
        & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' `
            docs/superpowers/plans/verify_poselib_gui_send.py $p }       # --purge on the first

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("The window", "Blend")
"""

import math
import os
import sys
import time
import traceback

import maya.api.OpenMaya as om
import maya.cmds as cmds

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
SHOTS = HERE
WORLD = sys.__dict__.setdefault("_verify_poselib_gui", {})
RESULTS = []

ROT = ("rotateX", "rotateY", "rotateZ")
TR = ("translateX", "translateY", "translateZ")
UNROLLED_LIMB = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot"}
HINGE = {"Elbow": ("Shoulder", "Wrist"), "Knee": ("Hip", "Ankle")}
A_AT = (-90.0, 0.0, 0.0)
B_AT, B_TURN = (90.0, 0.0, -20.0), -25.0
FLOOR = (0.0, 0.0, 140.0)
FRAME = 12.0
SPREAD_MIN = 12.0          # the thumbnail's grey-level standard deviation: a blank one is ~0
DEFAULT_FRESH = "off"      # rigsolve's shipped FRESH_MODE (the `fresh` phase gates it)


def say(*parts):
    print(" ".join(str(p) for p in parts))


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))
    return bool(ok)


# ------------------------------------------------------------------ Maya and Qt

def qt():
    import maya_hubqt
    return maya_hubqt.qt()


def settle(times=3):
    q = qt()
    for _ in range(times):
        q.QtWidgets.QApplication.processEvents()
    cmds.refresh(force=True)


def W(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def matrix_diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def frame():
    return float(cmds.currentTime(query=True))


def evaluate():
    t = frame()
    cmds.currentTime(t + 1, update=True)
    cmds.currentTime(t, update=True)


def maya_window():
    for top in qt().QtWidgets.QApplication.topLevelWidgets():
        if top.objectName() == "MayaWindow":
            return top
    return None


def show_maya():
    """MayaWindow restored (a minimised one draws no viewport: no pick, no projection - trap
    192), with a model panel up."""
    top = maya_window()
    if top is not None and (top.isMinimized() or not top.isVisible()):
        top.showNormal()
    settle()


def model_panel():
    """The visible model panel with the largest port."""
    import maya.api.OpenMayaUI as omui
    q = qt()
    best = None
    for panel in cmds.getPanel(type="modelPanel") or []:
        try:
            view = omui.M3dView.getM3dViewFromModelPanel(panel)
        except RuntimeError:
            continue
        widget = q.shiboken.wrapInstance(int(view.widget()), q.QtWidgets.QWidget)
        if not widget.isVisible():
            continue
        area = view.portWidth() * view.portHeight()
        if best is None or area > best[0]:
            best = (area, panel)
    return best[1] if best else None


def to_global(world, panel=None):
    """A world point's global screen position through the panel's view (Qt px)."""
    import maya.api.OpenMayaUI as omui
    q = qt()
    panel = panel or model_panel()
    view = omui.M3dView.getM3dViewFromModelPanel(panel)
    widget = q.shiboken.wrapInstance(int(view.widget()), q.QtWidgets.QWidget)
    x, y, _clipped = view.worldToView(om.MPoint(*world))
    sx = view.portWidth() / float(widget.width())
    sy = view.portHeight() / float(widget.height())
    local = q.QtCore.QPoint(int(round(x / sx)), int(round(widget.height() - y / sy)))
    point = widget.mapToGlobal(local)
    return point.x(), point.y()


def world_t(node):
    return tuple(cmds.xform(node, query=True, worldSpace=True, translation=True))


# ------------------------------------------------------------------ the window

def control():
    from maya_poselib import window as w
    return w.CONTROL


def window():
    """The PoseWindow standing in the control, found by its objectName now (trap 148)."""
    import maya_hubqt
    from maya_poselib import window as w
    host = maya_hubqt.find(w.CONTROL)
    if host is None:
        return None
    for child in host.findChildren(qt().QtWidgets.QWidget):
        if child.objectName() == w.ROOT:
            return child
    return None


def child(name, cls=None):
    win = window()
    if win is None:
        return None
    cls = cls or qt().QtWidgets.QWidget
    for widget in win.findChildren(cls):
        if widget.objectName() == name:
            return widget
    return None


def click(name):
    """The button `name` of the window CLICKED (a Qt click: its signal, as a press makes it)."""
    button = child(name, qt().QtWidgets.QAbstractButton)
    if button is None:
        raise RuntimeError("no button %s" % name)
    button.click()
    settle()


def top_level():
    """The floating window holding the control (never MayaWindow - trap 150)."""
    import maya_hubqt
    host = maya_hubqt.find(control())
    top = host.window() if host is not None else None
    if top is not None and top.objectName() == "MayaWindow":
        return None
    return top


def keep_off(points):
    """The floating Pose Library window moved to a corner where no aimed point lies on it."""
    top = top_level()
    if top is None:
        return "no floating window"

    def covers():
        geometry = top.frameGeometry()
        return any(geometry.contains(qt().QtCore.QPoint(int(x), int(y))) for x, y in points)

    if not covers():
        return "the window stands clear"
    screen = top.screen().availableGeometry()
    for x, y in [(screen.right() - top.frameGeometry().width(), screen.top()),
                 (screen.right() - top.frameGeometry().width(),
                  screen.bottom() - top.frameGeometry().height()),
                 (screen.left(), screen.top()),
                 (screen.left(), screen.bottom() - top.frameGeometry().height())]:
        top.move(x, y)
        settle()
        if not covers():
            return "window moved to (%d, %d)" % (x, y)
    return "the window covers a point wherever it stands"


def size_window(width, height):
    """The window's content at `width` x `height` LOGICAL px (x the display scale)."""
    win = window()
    k = float(win.k)
    top = top_level()
    want = (int(round(width * k)), int(round(height * k)))
    for _ in range(5):
        win = window()
        dw, dh = want[0] - win.width(), want[1] - win.height()
        if not dw and not dh:
            break
        top.resize(top.width() + dw, top.height() + dh)
        settle()
    win = window()
    return win.width(), win.height(), want


def status():
    label = child("skeldarPoseStatus")
    return label.text() if label is not None else ""


# ------------------------------------------------------------------ the characters

def add(key):
    """The new Rig after Add Character of the catalog row `key`; its channel values as Add left
    them recorded (the run's reset goes back to them)."""
    import maya_rigs
    from maya_scenesetup import catalog, character
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    new = [r for r in maya_rigs.rigs() if r.namespace not in before]
    if new:
        WORLD.setdefault("defaults", {})[new[0].namespace] = values_of(control_plugs(new[0]))
    return new[0] if new else None


def rig_by(namespace):
    import maya_rigs
    return next((r for r in maya_rigs.rigs() if r.namespace == namespace), None)


def control_plugs(rig):
    out = []
    for member in cmds.sets(rig.control_set, query=True) or []:
        node = (cmds.ls(member, long=True) or [None])[0]
        if node is None or not cmds.objectType(node, isAType="transform"):
            continue
        for attr in cmds.listAttr(node, keyable=True, unlocked=True, scalar=True) or []:
            plug = node + "." + attr
            try:
                if cmds.getAttr(plug, settable=True):
                    out.append(plug)
            except (RuntimeError, ValueError):
                continue
    return out


def values_of(plugs):
    return dict((p, float(cmds.getAttr(p))) for p in plugs)


def set_values(values):
    for plug, value in values.items():
        cmds.setAttr(plug, value)


def curve_state():
    out = {}
    for curve in cmds.ls(type="animCurve") or []:
        times = tuple(cmds.keyframe(curve, query=True, timeChange=True) or ())
        values = tuple(cmds.keyframe(curve, query=True, valueChange=True) or ())
        out[curve] = (times, values)
    return out


class Char(object):
    """A rig of the run, by namespace: its ref, its default channel values, a reset."""

    def __init__(self, namespace):
        from maya_poselib import scene
        self.namespace = namespace
        self.rig = rig_by(namespace)
        self.root = self.rig.skeleton_root
        self.ref = scene.rig_ref(self.rig)
        self.plugs = control_plugs(self.rig)
        self.defaults = WORLD.setdefault("defaults", {}).get(namespace) or {}

    def reset(self):
        """Every key on its channels cut, every channel but Main's back at Add's value (Main
        keeps the place the run gave it)."""
        curves = cmds.listConnections(self.plugs, source=True, destination=False,
                                      type="animCurve") or []
        if curves:
            cmds.delete(list(set(curves)))
        main = self.rig.main + "."
        for plug, value in self.defaults.items():
            if plug.startswith(main):
                continue
            try:
                cmds.setAttr(plug, value)
            except RuntimeError:
                pass
        evaluate()

    def node(self, leaf):
        import maya_rigs
        return maya_rigs.node(self.rig, leaf)

    def bones(self):
        from maya_poselib import scene
        return scene.skeleton(self.ref)[0]

    def game(self):
        return dict((leaf, b["path"]) for leaf, b in self.bones().items())


# a deterministic FK pose (verify_poselib_apply's): the hinges bent on their anatomical axis

def _perp(a, b, c):
    from maya_poselib import posemath as pm
    s, e, w = (pm.position(W(n)) for n in (a, b, c))
    line = (w - s).normal()
    return e - (s + line * ((e - s) * line))


def bend_channels(ch, joint, side):
    key = ("bend", ch.namespace, joint, side)
    if key in WORLD:
        return WORLD[key]
    up, down = HINGE[joint]
    ref = om.MVector(0, 0, 1) if joint == "Knee" else om.MVector(0, 0, -1)
    ctrl = ch.node("FK" + joint + side)
    effect = {}
    for channel in ROT:
        old = cmds.getAttr(ctrl + "." + channel)
        cmds.setAttr(ctrl + "." + channel, old + 30)
        effect[channel] = _perp(ch.node("FKX" + up + side), ch.node("FKX" + joint + side),
                                ch.node("FKX" + down + side))
        cmds.setAttr(ctrl + "." + channel, old)
    bend = max(ROT, key=lambda c: abs(effect[c] * ref))
    sign = 1.0 if effect[bend] * ref > 0 else -1.0
    roll = min([c for c in ROT if c != bend], key=lambda c: effect[c].length())
    other = [c for c in ROT if c not in (bend, roll)][0]
    WORLD[key] = (bend, sign, roll, other)
    return WORLD[key]


def pose_values(ch, seed=0.0):
    """{plug: value}: every FK control of `maya_asretarget.ROWS` turned, the hinges bent
    forward, RootX_M moved and turned."""
    import maya_asretarget
    out = {}
    k = 0
    for base, _ue in maya_asretarget.ROWS:
        for side in ("_M", "_L", "_R"):
            node = ch.node("FK" + base + side)
            if not cmds.objExists(node):
                continue
            k += 1
            amp = 12.0 if "Finger" in base else 18.0
            vals = (amp * math.sin(1.3 * k + seed), amp * math.cos(0.7 * k + 2 * seed),
                    amp * math.sin(0.4 * k + 1 + seed))
            if base in HINGE:
                bend, sign, roll, other = bend_channels(ch, base, side)
                amount = {"Elbow": (42.0, 20.0, 4.0), "Knee": (35.0, 9.0, 3.0)}[base]
                by = {bend: sign * (amount[0] + 6 * seed), roll: amount[1], other: amount[2]}
                vals = tuple(by[c] for c in ROT)
            if base == "Toes":
                vals = (0.0, 0.0, 0.0)
            for channel, value in zip(ROT, vals):
                plug = node + "." + channel
                if not cmds.getAttr(plug, lock=True):
                    out[plug] = value
    rootx = ch.node("RootX_M")
    for channel, value in zip(TR + ROT, (3.0, -4.0, 5.0, 8.0, 15.0, -6.0)):
        out[rootx + "." + channel] = value * (1.0 - 0.6 * seed)
    return out


# ------------------------------------------------------------------ measures

def rel(a, b):
    from maya_poselib import posemath as pm
    return pm.rigid(a) * pm.rigid(b).inverse()


def target_members(data, ch):
    from maya_poselib import apply as ap
    from maya_poselib import posemath as pm
    bones = ch.bones()
    pairs = pm.pairs(data["bones"], bones)
    return ap.target_members(bones, pairs, data["members"])


def rel_rows(data, ch, members):
    """[(leaf, deg, cm)]: each non-twist member bone RELATIVE TO ITS ROOT against the card's -
    the four unrolled limb bones by where they point (verify_poselib_apply's `rel_rows`)."""
    from maya_poselib import posemath as pm
    source = data["bones"]
    game = dict((leaf, pm.rigid(W(path))) for leaf, path in ch.game().items())
    root = pm.root_of(ch.bones())
    s_root = pm.root_of(source)
    g_root, c_root = game[root], pm.rigid(source[s_root]["world"])
    rows = []
    for leaf in members:
        if leaf not in game or leaf not in source or pm.is_twist(leaf) or leaf == root:
            continue
        got, want = rel(game[leaf], g_root), rel(source[leaf]["world"], c_root)
        cm = (pm.position(got) - pm.position(want)).length()
        base = leaf[:-2] if leaf.endswith(("_l", "_r")) else leaf
        kid = UNROLLED_LIMB.get(base)
        if kid is not None and kid + leaf[-2:] in game:
            kid = kid + leaf[-2:]
            a = (pm.position(game[kid]) - pm.position(game[leaf])) * pm.rotation(g_root).inverse()
            b = (pm.position(source[kid]["world"]) - pm.position(source[leaf]["world"])) * \
                pm.rotation(c_root).inverse()
            rows.append((leaf, pm.direction_angle(a, b), cm))
        else:
            rows.append((leaf, pm.angle(got, want), cm))
    return rows


def worst_of(rows):
    deg = max(rows, key=lambda r: r[1]) if rows else (None, 0.0, 0.0)
    cm = max(rows, key=lambda r: r[2]) if rows else (None, 0.0, 0.0)
    return deg[1], cm[2], deg[0], cm[0]


def _q(values, order):
    return om.MEulerRotation(*([math.radians(v) for v in values] + [order])).asQuaternion()


def _qangle(a, b):
    d = a.inverse() * b
    v = math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    return math.degrees(2.0 * math.atan2(v, abs(d.w)))


def halfway(current, final, now, alpha):
    """(worst deg off the way, worst translation off, the largest turn, rows): each rotation
    triple's quaternion angle from `current` against alpha x the whole angle, and the rest of
    the way against (1 - alpha) x it; every translation against the lerp."""
    from maya_poselib import apply as ap
    worst, largest, rows = 0.0, 0.0, 0
    for node, spec in ap.rotations_of(final).items():
        plugs, order = spec[:3], spec[3]
        q0 = _q([current[p] for p in plugs], order)
        q1 = _q([final[p] for p in plugs], order)
        qn = _q([now[p] for p in plugs], order)
        whole = _qangle(q0, q1)
        largest = max(largest, whole)
        off = max(abs(_qangle(q0, qn) - alpha * whole), abs(_qangle(qn, q1) - (1 - alpha) * whole))
        worst = max(worst, off)
        rows += 1
    worst_t = 0.0
    for plug in final:
        if plug.rsplit(".", 1)[-1] in TR:
            worst_t = max(worst_t, abs(now[plug] - (current[plug] + alpha *
                                                    (final[plug] - current[plug]))))
    return worst, worst_t, largest, rows


# ------------------------------------------------------------------ fresh: the parallel EM

def _chain_reads(rig, ref, mode):
    """Every FK control set level by level down the game skeleton, each read after its set:
    [(leaf, FKX, deformation, game bone)] - under evaluation `mode`; every value put back."""
    from maya_poselib import rigsolve, scene
    cmds.evaluationManager(mode=mode)
    bases = rigsolve.bases(rig)
    bones = scene.skeleton(ref)[0]
    order = sorted((leaf for leaf in bases if leaf in bones),
                   key=lambda leaf: (bones[leaf]["path"].count("|"), leaf))
    originals, reads = [], []
    k = 0
    t0 = time.time()
    try:
        for leaf in order:
            b = bases[leaf]
            if not b.fk:
                continue
            k += 1
            for i, channel in enumerate(ROT):
                plug = b.fk + "." + channel
                if cmds.getAttr(plug, lock=True) or not cmds.getAttr(plug, settable=True):
                    continue
                originals.append((plug, float(cmds.getAttr(plug))))
                cmds.setAttr(plug, originals[-1][1] + 9.0 * math.sin(k + 1.7 * i))
            reads.append((leaf, W(b.fkx) if b.fkx else None,
                          W(b.deform) if b.deform else None, W(bones[leaf]["path"])))
    finally:
        took = time.time() - t0
        for plug, value in reversed(originals):
            cmds.setAttr(plug, value)
    return reads, took, len(originals)


def _cached():
    try:
        return cmds.cacheEvaluator(query=True, cachedFrames=True)
    except Exception as exc:                                 # noqa: BLE001
        return "query failed: %s" % exc


def _count_cached(raw):
    """How many frames the `cachedFrames` answer holds. Measured in Maya 2027: a list of
    (state, start, end) triples, `[(1, 0, 60)]` for a filled 0..60."""
    if not isinstance(raw, (list, tuple)):
        return None
    total = 0.0
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) == 3:
            if int(item[0]) == 1:
                total += float(item[2]) - float(item[1]) + 1.0
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            total += float(item[1]) - float(item[0]) + 1.0
    return total


def _wait_cache(seconds=20.0):
    t0 = time.time()
    try:
        cmds.cacheEvaluator(waitForCache=seconds)
    except Exception as exc:                                 # noqa: BLE001
        say("   waitForCache failed: %s" % exc)
    return time.time() - t0


def phase_fresh():
    from maya_poselib import apply as ap
    from maya_poselib import capture, rigsolve
    new_scene()
    a, b = Char(add("Manny_Rig").namespace), Char(add("Manny_Rig").namespace)
    mode = cmds.evaluationManager(query=True, mode=True)[0]
    say("   evaluation manager: %s; cached playback %s" % (
        mode, cmds.evaluator(name="cache", query=True, enable=True)))
    gate("fresh the GUI runs the parallel evaluation manager", mode == "parallel", mode)
    gate("fresh rigsolve's FRESH_MODE is the shipped %r" % DEFAULT_FRESH,
         rigsolve.FRESH_MODE == DEFAULT_FRESH, "%r" % rigsolve.FRESH_MODE)

    # 1. a set then a read, level by level, parallel against DG
    par, par_took, n = _chain_reads(a.rig, a.ref, "parallel")
    dg, dg_took, _n = _chain_reads(a.rig, a.ref, "off")
    cmds.evaluationManager(mode="parallel")
    worst, at = 0.0, None
    for (leaf, *mats_p), (_leaf, *mats_d) in zip(par, dg):
        for mp, md in zip(mats_p, mats_d):
            if mp is None or md is None:
                continue
            d = matrix_diff(mp, md)
            if d > worst:
                worst, at = d, leaf
    gate("fresh a getAttr after a setAttr reads the same in parallel as in DG (level by level)",
         len(par) == len(dg) and par and worst < 1e-6,
         "worst matrix element %.3g at %s over %d levels (%d channels set); parallel %.2f s, "
         "DG %.2f s" % (worst, at, len(par), n, par_took, dg_took))

    # 2. a whole solve, with nothing switched against under DG
    for plug, value in pose_values(a, seed=0.3).items():
        cmds.setAttr(plug, value)
    evaluate()
    card, note = capture.build_pose([a.rig.main])
    say("   card: %s" % note)
    a.reset()
    plans, took = {}, {}
    for fresh in (None, "off"):
        rigsolve.FRESH_MODE = fresh
        t0 = time.time()
        plans[fresh] = ap.plan_for(card, b.ref)
        took[fresh] = time.time() - t0
    rigsolve.FRESH_MODE = DEFAULT_FRESH
    keys_ = set(plans[None].values) | set(plans["off"].values)
    diff = max(abs(plans[None].values.get(k, 1e9) - plans["off"].values.get(k, -1e9))
               for k in keys_) if keys_ else 0.0
    gate("fresh a whole plan_for in parallel (nothing switched) gives DG's values",
         keys_ and diff < 1e-6,
         "%d values, worst %.3g; parallel %.2f s, DG (switched) %.2f s" % (
             len(keys_), diff, took[None], took["off"]))
    WORLD["fresh_took"] = took

    # 3. the bones land, applied under each
    members = target_members(card, b)
    for fresh in (None, "off"):
        b.reset()
        rigsolve.FRESH_MODE = fresh
        cmds.select(b.rig.main, replace=True)
        ok, text = ap.apply(card)
        evaluate()
        deg, cm, at_deg, _at = worst_of(rel_rows(card, b, members))
        gate("fresh applied with FRESH_MODE %r: every member on the card relative to the root"
             % fresh, ok and deg <= 0.01, "%.6f deg (%s), %.6f cm" % (deg, at_deg, cm))
    rigsolve.FRESH_MODE = DEFAULT_FRESH
    b.reset()

    # 4. the switch's cost, and Cached Playback
    cmds.playbackOptions(minTime=0, maxTime=60, animationStartTime=0, animationEndTime=60)
    for plug, value in list(pose_values(a, seed=0.7).items())[:40]:
        cmds.setKeyframe(plug, time=0, value=a.defaults.get(plug, 0.0))
        cmds.setKeyframe(plug, time=60, value=value)
    cmds.currentTime(30, update=True)
    waited = _wait_cache()
    before = _cached()
    t0 = time.time()
    evaluate()
    plain = time.time() - t0
    t0 = time.time()
    cmds.evaluationManager(mode="off")
    t_off = time.time() - t0
    t0 = time.time()
    cmds.evaluationManager(mode="parallel")
    t_on = time.time() - t0
    t0 = time.time()
    evaluate()
    first = time.time() - t0
    right_after = _cached()
    waited2 = _wait_cache()
    later = _cached()
    say("   cached frames: before %s | right after the switch %s | after %.1f s %s" % (
        _count_cached(before), _count_cached(right_after), waited2, _count_cached(later)))
    say("   raw before %s | raw after %s" % (str(before)[:120], str(right_after)[:120]))
    WORLD["switch"] = dict(off=t_off, on=t_on, first=first, plain=plain)
    gate("fresh the cost of the switch measured", True,
         "off %.3f s, back to parallel %.3f s, the first evaluation after %.3f s against %.3f s "
         "plain; the cache waited %.1f s first" % (t_off, t_on, first, plain, waited))
    flushed = (_count_cached(before) or 0) > 0 and (_count_cached(right_after) or 0) < \
        (_count_cached(before) or 0)
    gate("fresh does the switch flush Cached Playback (measured, not a requirement)", True,
         "flushed %s: %s -> %s frames, refilled to %s in %.1f s" % (
             flushed, _count_cached(before), _count_cached(right_after), _count_cached(later),
             waited2))
    # and a whole plan_for, nothing switched against switched: what is left of the cache
    cache = {}
    for fresh in (None, "off"):
        _wait_cache()
        full = _count_cached(_cached())
        rigsolve.FRESH_MODE = fresh
        t0 = time.time()
        ap.plan_for(card, b.ref)
        took_plan = time.time() - t0
        left = _count_cached(_cached())
        _wait_cache()
        idle = _count_cached(_cached())
        t0 = time.time()
        evaluate()                                  # the next evaluation: the fill starts again
        _wait_cache()
        cache[fresh] = (full, left, idle, _count_cached(_cached()), time.time() - t0, took_plan)
    rigsolve.FRESH_MODE = DEFAULT_FRESH
    gate("fresh the cache across a plan_for: nothing switched against switched (measured)", True,
         "; ".join("%r: %s cached -> %s right after (plan %.2f s), %s while idle, %s after the "
                   "next evaluation (%.1f s)" % (f, c[0], c[1], c[5], c[2], c[3], c[4])
                   for f, c in cache.items()))
    WORLD["cache"] = cache

    # 5. the IK legs and the numeric toes: a Creep_Rig (legs in IK) solved both ways
    creep = Char(add("Creep_Rig").namespace)
    plans = {}
    for fresh in (None, "off"):
        rigsolve.FRESH_MODE = fresh
        t0 = time.time()
        plans[fresh] = (ap.plan_for(card, creep.ref), time.time() - t0)
    rigsolve.FRESH_MODE = DEFAULT_FRESH
    keys_ = set(plans[None][0].values) | set(plans["off"][0].values)
    diff = max(abs(plans[None][0].values.get(k, 1e9) - plans["off"][0].values.get(k, -1e9))
               for k in keys_) if keys_ else 0.0
    ik = [k for k in keys_ if "IKLeg" in k or "PoleLeg" in k or "IKToes" in k]
    gate("fresh a Creep_Rig (IK legs, numeric toes) solved in parallel gives DG's values",
         keys_ and ik and diff < 1e-6,
         "%d values (%d of the IK legs), worst %.3g; parallel %.2f s, DG %.2f s" % (
             len(keys_), len(ik), diff, plans[None][1], plans["off"][1]))

    # 6. a KEYED rig with Cached Playback FILLED: the temporary setAttr on a keyed channel, read
    #    in parallel, against DG - the case where a cache could serve a stale value
    for plug, value in list(pose_values(b, seed=1.1).items()):
        cmds.setKeyframe(plug, time=0, value=b.defaults.get(plug, 0.0))
        cmds.setKeyframe(plug, time=60, value=value)
    cmds.currentTime(30, update=True)
    evaluate()
    _wait_cache()
    full = _count_cached(_cached())
    par, _t, n = _chain_reads(b.rig, b.ref, "parallel")
    cached_after = _count_cached(_cached())
    dg, _t, _n = _chain_reads(b.rig, b.ref, "off")
    cmds.evaluationManager(mode="parallel")
    cmds.currentTime(30, update=True)
    worst = 0.0
    for (_leaf, *mats_p), (_l, *mats_d) in zip(par, dg):
        for mp, md in zip(mats_p, mats_d):
            if mp is not None and md is not None:
                worst = max(worst, matrix_diff(mp, md))
    gate("fresh on a KEYED rig with the cache filled, a read after a setAttr is fresh",
         par and worst < 1e-6, "worst %.3g over %d levels (%d channels), the cache %s frames "
         "before, %s after the parallel pass" % (worst, len(par), n, full, cached_after))
    # ... but a whole solve on a keyed rig: four trials, B keyed anew each time, the solve in
    #     parallel (nothing switched) against DG - the evidence for FRESH_MODE (`stale` names
    #     the read that goes stale)
    rows = []
    for trial in range(4):
        b.reset()
        for plug, value in pose_values(b, seed=1.1 + 0.3 * trial).items():
            cmds.setKeyframe(plug, time=0, value=b.defaults.get(plug, 0.0))
            cmds.setKeyframe(plug, time=60, value=value)
        cmds.currentTime(30, update=True)
        if trial % 2:
            evaluate()
            _wait_cache()
        plans = {}
        for fresh in (None, "off"):
            rigsolve.FRESH_MODE = fresh
            plans[fresh] = ap.plan_for(card, b.ref)
            cmds.evaluationManager(mode="parallel")
        keys_ = [k for k in plans["off"].values if k in plans[None].values]
        worst = max(keys_, key=lambda k: abs(plans[None].values[k] - plans["off"].values[k]))
        lands = [n for n in plans[None].notes if "lands within" in n]
        rows.append((abs(plans[None].values[worst] - plans["off"].values[worst]),
                     worst.split(":")[-1], lands[0] if lands else "lands"))
    rigsolve.FRESH_MODE = DEFAULT_FRESH
    WORLD["keyed_parallel"] = rows
    gate("fresh on a KEYED rig a solve read in parallel misses (measured: the evidence for "
         "FRESH_MODE)", True, "; ".join("%.3f at %s (%s)" % r for r in rows))
    # the shipped default, on that keyed rig: the bones land
    members = target_members(card, b)
    cmds.select(b.rig.main, replace=True)
    ok, text = ap.apply(card)
    evaluate()
    deg, cm, at_deg, _at = worst_of(rel_rows(card, b, members))
    gate("fresh the shipped FRESH_MODE (%r) lands the keyed rig's bones" % DEFAULT_FRESH,
         ok and deg <= 0.01, "%.6f deg (%s), %.6f cm | %s" % (deg, at_deg, cm, text))
    cmds.currentTime(FRAME, update=True)


# ------------------------------------------------------------------ the run's scene

def new_scene():
    cmds.file(new=True, force=True)
    WORLD["defaults"] = {}
    for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
        cmds.loadPlugin(plugin, quiet=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=0, maxTime=40, animationStartTime=0, animationEndTime=40)
    cmds.autoKeyframe(state=False)
    cmds.currentTime(FRAME, update=True)


def library_root():
    """The run's own library, in the scratch prefs (never the plugin's poses/)."""
    app = cmds.internalVar(userAppDir=True).replace("\\", "/")
    return app.rstrip("/") + "/poselib_verify_library"


def guard():
    """Refuse to run in what looks like the animator's Maya."""
    app = cmds.internalVar(userAppDir=True).replace("\\", "/")
    if "Documents/maya" in app or cmds.commandPort(":7001", query=True):
        raise RuntimeError("this looks like the animator's Maya (%s) - refused" % app)


def phase_open():
    import shutil
    import maya_hub
    import maya_hubqt
    from maya_poselib import store
    from maya_poselib import window as w
    new_scene()
    for key in ("full", "hand", "A", "B", "C", "floor_point", "rigs_before"):
        WORLD.pop(key, None)
    root = library_root()
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)
    cmds.optionVar(stringValue=(store.ROOT_VAR, root))
    for var in (w.SORT_VAR, w.SIZE_VAR):
        if cmds.optionVar(exists=var):
            cmds.optionVar(remove=var)
    a, b = add("Manny_Rig"), add("Manny_Rig")
    WORLD["A"], WORLD["B"] = a.namespace, b.namespace
    cmds.setAttr(a.main + ".translate", *A_AT)
    cmds.setAttr(b.main + ".translate", *B_AT)
    cmds.setAttr(b.main + ".rotateY", B_TURN)
    A, B = Char(a.namespace), Char(b.namespace)
    set_values(pose_values(A, seed=0.0))
    set_values(pose_values(B, seed=1.0))
    evaluate()
    show_maya()
    cmds.modelEditor(model_panel(), edit=True, camera="persp")
    cmds.viewPlace("persp", eye=(0.0, 160.0, 640.0), lookAt=(0.0, 90.0, 0.0))
    settle()

    if cmds.workspaceControl(w.CONTROL, exists=True):
        cmds.deleteUI(w.CONTROL)
    maya_hub.show("poses")
    settle()
    button = maya_hubqt.find(w.OPEN_BUTTON)
    found = button is not None
    if found:
        q = qt()
        clicker = q.shiboken.wrapInstance(int(q.shiboken.getCppPointer(button)[0]),
                                          q.QtWidgets.QAbstractButton)
        clicker.click()
    settle(6)
    win = window()
    floating = cmds.workspaceControl(w.CONTROL, query=True, floating=True) \
        if cmds.workspaceControl(w.CONTROL, exists=True) else None
    gate("open the hub's Pose Library card, its Open button clicked: the floating control and "
         "the window in it", found and win is not None and floating and win is w.live(),
         "button %s, window %s, floating %s, live %s" % (found, win is not None, floating,
                                                        win is w.live()))
    if cmds.workspaceControl(maya_hub.CONTROL, exists=True):
        cmds.workspaceControl(maya_hub.CONTROL, edit=True, close=True)   # off the viewport
    settle()
    win = window()
    k = float(win.k)
    hint = win.minimumSizeHint()
    gate("open the window's content fits 600 px wide (logical)",
         hint.width() <= int(round(600 * k)),
         "minimum %d x %d physical at scale %.2f (600 logical = %d)" % (
             hint.width(), hint.height(), k, int(round(600 * k))))
    gate("open the library is the run's own", win.root == root.rstrip("/"), win.root)


def _clipped(win):
    """[(what, why)] of every visible control of the window that is under its size hint, or
    outside the window, or cut horizontally by the side panel's viewport."""
    q = qt()
    W_ = q.QtWidgets
    rows = []
    side = child("skeldarPoseSideViewport")
    outer = win.rect()
    kinds = (W_.QAbstractButton, W_.QComboBox, W_.QLineEdit, W_.QSlider, W_.QLabel)
    seen = 0
    for widget in win.findChildren(W_.QWidget):
        if not isinstance(widget, kinds) or not widget.isVisible():
            continue
        name = widget.objectName() or type(widget).__name__
        if isinstance(widget, W_.QLabel) and not widget.text() and widget.pixmap().isNull():
            continue
        if name == "skeldarPosePath":
            continue                       # Ignored on purpose: the path elides, its tooltip
        seen += 1
        if isinstance(widget, W_.QLabel):
            if widget.wordWrap():
                need = widget.heightForWidth(widget.width())
                if need > widget.height():
                    rows.append((name, "%d px tall, its text needs %d" % (widget.height(), need)))
            else:
                hint = widget.minimumSizeHint()
                if widget.width() < hint.width() or widget.height() < hint.height():
                    rows.append((name, "%dx%d under %dx%d" % (widget.width(), widget.height(),
                                                              hint.width(), hint.height())))
        else:
            hint = widget.sizeHint() if isinstance(widget, (W_.QPushButton, W_.QCheckBox)) \
                else widget.minimumSizeHint()
            if widget.width() < hint.width() or widget.height() < hint.height():
                rows.append((name, "%dx%d under %dx%d" % (widget.width(), widget.height(),
                                                          hint.width(), hint.height())))
        box = q.QtCore.QRect(widget.mapTo(win, q.QtCore.QPoint(0, 0)), widget.size())
        inside_side = side is not None and side.isAncestorOf(widget)
        if inside_side:
            local = q.QtCore.QRect(widget.mapTo(side, q.QtCore.QPoint(0, 0)), widget.size())
            if local.left() < 0 or local.right() > side.width() - 1:
                rows.append((name, "cut by the side panel: x %d..%d of %d" % (
                    local.left(), local.right(), side.width())))
        elif not outer.contains(box):
            rows.append((name, "outside the window: %s in %s" % (box, outer)))
    return rows, seen


def phase_sizes():
    show_maya()
    if WORLD.get("full"):
        window().set_folder("")
        window().pick(WORLD["full"])            # the details filled: its texts measured too
    settle()
    for width, height in ((1000, 640), (600, 640)):
        got = size_window(width, height)
        for page in ("details", "save"):
            win = window()
            win.side.setCurrentWidget(win.details_page if page == "details" else win.save_page)
            settle()
            rows, seen = _clipped(window())
            sizes = window().splitter.sizes()
            gate("sizes %dx%d the %s: every control at or above its size hint, nothing cut"
                 % (width, height, page), not rows and seen > 5,
                 "window %dx%d (want %s), splitter %s, %d controls%s" % (
                     got[0], got[1], got[2], sizes, seen,
                     "" if not rows else " | " + "; ".join("%s %s" % r for r in rows[:6])))
        window().side.setCurrentWidget(window().details_page)
    size_window(1000, 640)


def _thumb_spread(path):
    """(width, height, grey-level standard deviation) of an image file."""
    q = qt()
    image = q.QtGui.QImage(path)
    if image.isNull():
        return 0, 0, 0.0
    grey = image.convertToFormat(q.QtGui.QImage.Format_Grayscale8)
    values = []
    for y in range(0, grey.height(), 4):
        for x in range(0, grey.width(), 4):
            values.append(q.QtGui.qGray(grey.pixel(x, y)))
    mean = sum(values) / float(len(values))
    spread = math.sqrt(sum((v - mean) ** 2 for v in values) / float(len(values)))
    return image.width(), image.height(), spread


def _save(name, select):
    cmds.select(select, replace=True)
    settle()
    click("skeldarPoseSave")
    win = window()
    opened = win.saving()
    snapshot = win._save["snapshot"] if win._save else None
    shot = os.path.isfile(snapshot) if snapshot else False
    line = status()
    child("skeldarPoseSaveName", qt().QtWidgets.QLineEdit).setText(name)
    click("skeldarPoseSaveOk")
    return opened, shot, line, status()


def phase_save():
    from maya_poselib import store
    show_maya()
    A = Char(WORLD["A"])
    root = library_root()
    opened, shot, snap_line, line = _save("Full", A.rig.main)
    path = root + "/Full" + store.CARD_SUFFIX
    thumb = path + "/" + store.THUMB_FILE
    exists = os.path.isfile(path + "/" + store.POSE_FILE)
    head = b""
    if os.path.isfile(thumb):
        with open(thumb, "rb") as handle:
            head = handle.read(3)
    w_, h_, spread = _thumb_spread(thumb) if os.path.isfile(thumb) else (0, 0, 0.0)
    gate("save Main selected, + Save pose and Save clicked: a card with a thumbnail",
         opened and shot and exists and os.path.isfile(thumb) and not window().saving(),
         "panel %s, snapshot %s ('%s'), card %s | '%s'" % (opened, shot, snap_line, exists, line))
    gate("save the thumbnail is a 320 x 320 JPG that is not blank",
         head == b"\xff\xd8\xff" and (w_, h_) == (320, 320) and spread > SPREAD_MIN,
         "%dx%d, jpeg %s, grey spread %.1f (> %.0f)" % (w_, h_, head == b"\xff\xd8\xff", spread,
                                                       SPREAD_MIN))
    data = store.read(path)
    WORLD["full"] = path
    gate("save the card holds Manny_Rig's whole body", data["character"]["key"] == "Manny_Rig"
         and len(data["members"]) > 60, "%s, %d members" % (data["character"]["key"],
                                                            len(data["members"])))
    _opened, _shot, _s, line = _save("Hand", A.node("FKWrist_L"))
    hand = root + "/Hand" + store.CARD_SUFFIX
    WORLD["hand"] = hand
    data = store.read(hand) if os.path.isdir(hand) else {"members": []}
    gate("save a second card from the left wrist control: the hand's bones",
         os.path.isdir(hand) and "hand_l" in data["members"] and len(data["members"]) < 30,
         "%d members | '%s'" % (len(data["members"]), line))


def phase_list():
    from maya_poselib import store
    win = window()
    full, hand = WORLD["full"], WORLD["hand"]
    win.set_folder("")
    shown = window().cards_shown()
    gate("list both cards listed", full in shown and hand in shown, "%s" % shown)
    child("skeldarPoseSearch", qt().QtWidgets.QLineEdit).setText("hand")
    settle()
    narrowed = window().cards_shown()
    child("skeldarPoseSearch", qt().QtWidgets.QLineEdit).setText("")
    settle()
    gate("list the search narrows to the hand card", narrowed == [hand], "%s" % narrowed)
    win = window()
    win.ask_text = lambda title, label, text: "Hands"        # the dialog answered
    win.new_folder("")
    del win.ask_text
    made = "Hands" in store.folders(win.root)
    window().set_folder("")
    settle()
    item = window().folder_item("Hands")
    gate("list a folder made from the tree's row", made and item is not None,
         "folders %s" % store.folders(window().root))
    tree = window().tree
    rect = tree.visualItemRect(item)
    point = tree.viewport().mapToGlobal(rect.center())
    aim = window().aim(point.x(), point.y(), hand)
    line = window().drop_at(point.x(), point.y(), hand)
    moved = window().root + "/Hands/Hand" + store.CARD_SUFFIX
    gate("list the hand card dropped over the folder's item moves there",
         aim.get("kind") == "folder" and os.path.isdir(moved) and not os.path.isdir(hand)
         and moved in window().cards_shown(),
         "aim %s | '%s'" % (aim, line))
    WORLD["hand"] = moved
    # the selection followed: a part of B selected now, the window's SelectionChanged job runs
    # on idle - after this send - and `drop_rig` reads the target line it wrote
    window().set_folder("")
    window().pick(WORLD["full"])
    WORLD["line_before"] = child("skeldarPoseTarget").text()
    cmds.select(Char(WORLD["B"]).node("FKElbow_R"), replace=True)


def _projected(points):
    show_maya()
    first = [to_global(p) for p in points]
    print("   ", keep_off(first))
    return [to_global(p) for p in points]


def phase_drop_rig():
    from maya_poselib import look, store
    B = Char(WORLD["B"])
    settle()
    line = child("skeldarPoseTarget").text()
    apply_on = child("skeldarPoseApply", qt().QtWidgets.QAbstractButton).isEnabled()
    gate("drop_rig the window followed the selection (its scriptJob, between two sends)",
         line == "onto %s" % B.namespace and line != WORLD.get("line_before") and apply_on,
         "'%s' (was '%s'), Apply enabled %s" % (line, WORLD.get("line_before"), apply_on))
    card = store.read(WORLD["full"])
    main_before = W(B.rig.main)
    hand = B.game()["hand_l"]
    (gx, gy), = _projected([world_t(hand)])
    snap = window().scene.snapshot_scene()
    aim = window().aim(gx, gy, WORLD["full"], snap)
    text = look.drop_caption("Full", aim)[0]
    gate("drop_rig over the second rig's projected hand_l the caption names it",
         aim.get("kind") == "character" and aim.get("root") == B.root,
         "'%s' | %s" % (text, aim.get("root")))
    line = window().drop_at(gx, gy, WORLD["full"], snap)
    evaluate()
    members = target_members(card, B)
    deg, cm, at_deg, at_cm = worst_of(rel_rows(card, B, members))
    gate("drop_rig B takes the pose: every member on the card relative to its root",
         deg <= 0.01 and len(members) > 60,
         "%.6f deg (%s), places %.6f cm (%s), %d members | '%s'" % (
             deg, at_deg, cm, at_cm, len(members), line))
    gate("drop_rig B's Main unchanged", matrix_diff(main_before, W(B.rig.main)) < 1e-9,
         "%.3g" % matrix_diff(main_before, W(B.rig.main)))


def phase_drop_floor():
    import maya_rigs
    (gx, gy), = _projected([FLOOR])
    snap = window().scene.snapshot_scene()
    aim = window().aim(gx, gy, WORLD["full"], snap)
    point = aim.get("point")
    off = math.sqrt(sum((a - b) ** 2 for a, b in zip(point, FLOOR))) if point else None
    gate("drop_floor over the empty floor: the caption names a new Manny [rig] on the point",
         aim.get("kind") == "floor" and off is not None and off < 2.0,
         "%s, %.3f cm off the aimed point" % (aim, off if off is not None else -1))
    WORLD["floor_point"] = point
    WORLD["rigs_before"] = [r.namespace for r in maya_rigs.rigs()]
    line = window().drop_at(gx, gy, WORLD["full"], snap)
    WORLD["floor_line"] = line
    gate("drop_floor the release says it is adding it (deferred)", line.endswith("adding it"),
         "'%s'" % line)


def phase_floor_check():
    import maya_rigs
    from maya_poselib import store
    new = [r for r in maya_rigs.rigs() if r.namespace not in WORLD["rigs_before"]]
    gate("floor_check one new rig", len(new) == 1, "%s" % [r.namespace for r in new])
    if len(new) != 1:
        return
    C = Char(new[0].namespace)
    WORLD["C"] = C.namespace
    point = WORLD["floor_point"]
    at = world_t(C.rig.main)
    off = math.sqrt((at[0] - point[0]) ** 2 + (at[2] - point[2]) ** 2)
    gate("floor_check Main on the point", off <= 0.01 and abs(at[1]) < 1e-6,
         "(%.4f, %.4f, %.4f) for (%.4f, %.4f, %.4f): %.6f cm" % (at + tuple(point) + (off,)))
    card = store.read(WORLD["full"])
    evaluate()
    members = target_members(card, C)
    deg, cm, at_deg, _at = worst_of(rel_rows(card, C, members))
    gate("floor_check the new rig posed: every member on the card relative to its root",
         deg <= 0.01, "%.6f deg (%s), %.6f cm | '%s'" % (deg, at_deg, cm, status()))
    gate("floor_check the row is the card's", C.ref.key == card["character"]["key"],
         "%s" % C.ref.key)


def _mouse(widget, kind, local, button, buttons):
    q = qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    event = QtGui.QMouseEvent(kind, QtCore.QPointF(local),
                              QtCore.QPointF(widget.mapToGlobal(local)),
                              button, buttons, QtCore.Qt.NoModifier)
    q.QtWidgets.QApplication.sendEvent(widget, event)


def _session():
    """(current, final) of the window's blend session now, or (None, None)."""
    blend = window().scene._blend
    if blend is None:
        return None, None
    current, final = {}, {}
    for plan, _extra in blend.entries:
        current.update(plan.current)
        final.update(plan.values)
    return current, final


def phase_blend():
    from maya_poselib import apply as ap
    q = qt()
    Qt = q.QtCore.Qt
    E = q.QtCore.QEvent
    A = Char(WORLD["A"])
    A.reset()
    cmds.currentTime(FRAME, update=True)
    cmds.select(A.rig.main, replace=True)
    settle()
    window().pick(WORLD["full"])
    settle()
    slider = child("skeldarPoseBlend", q.QtWidgets.QSlider)
    xs = [x for x in range(slider.width()) if slider.value_at(x) == 50]
    x = xs[len(xs) // 2]
    point = q.QtCore.QPoint(x, slider.height() // 2)
    on_handle = slider.on_handle(point)
    before_curves = curve_state()
    t0 = time.time()
    _mouse(slider, E.MouseButtonPress, point, Qt.LeftButton, Qt.LeftButton)
    took = time.time() - t0
    slider = child("skeldarPoseBlend", q.QtWidgets.QSlider)
    value = slider.value()
    current, final = _session()
    if final is None:
        gate("blend the slider's press started a session", False, "'%s'" % status())
        return
    now = values_of(final)
    worst, worst_t, largest, rows = halfway(current, final, now, value / 100.0)
    gate("blend the slider pressed at 50 on its groove: the controls previewed halfway",
         value == 50 and not on_handle and worst <= 0.01 and worst_t <= 1e-6 and largest > 5.0,
         "value %d, %.6f deg off the way (largest turn %.1f), translations %.3g, %d rotations; "
         "the press (start + preview) %.2f s" % (value, worst, largest, worst_t, rows, took))
    expected = ap.mix(current, final, 0.5, ap.rotations_of(final))
    t0 = time.time()
    _mouse(child("skeldarPoseBlend", q.QtWidgets.QSlider), E.MouseButtonRelease, point,
           Qt.LeftButton, Qt.NoButton)
    took = time.time() - t0
    settle()
    line = status()
    evaluate()
    keyed = 0
    off = 0.0
    for plug, want in expected.items():
        times = cmds.keyframe(plug, query=True, timeChange=True) or []
        if FRAME in [float(t) for t in times]:
            keyed += 1
        off = max(off, abs(float(cmds.getAttr(plug)) - want))
    gate("blend the release keys the mix at the frame, «at 50 %»",
         keyed == len(expected) and off <= 1e-4 and "50 %" in line and not window().blending()
         and child("skeldarPoseBlend", q.QtWidgets.QSlider).value() == 0,
         "%d of %d keyed at %g, worst %.3g off the mix, the release %.2f s | '%s'" % (
             keyed, len(expected), FRAME, off, took, line))
    WORLD["after_blend"] = len(curve_state()) - len(before_curves)


def phase_middle():
    from maya_poselib import cardgrid
    q = qt()
    Qt = q.QtCore.Qt
    E = q.QtCore.QEvent
    A = Char(WORLD["A"])
    cmds.currentTime(FRAME, update=True)
    cmds.select(A.rig.main, replace=True)
    settle()
    window().set_folder("")
    settle()
    canvas = child(cardgrid.CANVAS_NAME)
    paths = [card.path for card in canvas.cards]
    index = paths.index(WORLD["full"])
    x, y, w_, h_ = canvas.rects()[index][:4]
    centre = q.QtCore.QPoint(int(x + w_ / 2), int(y + h_ / 2))
    before = values_of(control_plugs(A.rig))
    curves = curve_state()
    dx = int(round(0.5 * 200 * float(window().k)))
    _mouse(canvas, E.MouseButtonPress, centre, Qt.MiddleButton, Qt.MiddleButton)
    for step in (dx // 3, 2 * dx // 3, dx):
        _mouse(child(canvas.objectName()), E.MouseMove, centre + q.QtCore.QPoint(step, 0),
               Qt.NoButton, Qt.MiddleButton)
    blending = window().blending()
    now = values_of(control_plugs(A.rig))
    moved = max(abs(now[p] - v) for p, v in before.items())
    current, final = _session()
    worst = None
    if final is not None:
        worst = halfway(current, final, values_of(final), 0.5)[0]
    gate("middle a middle drag across the card previews the blend (at 50 %)",
         blending and moved > 1.0 and worst is not None and worst <= 0.01,
         "blending %s, a channel moved %.3f, %s deg off halfway | '%s'" % (
             blending, moved, "%.6f" % worst if worst is not None else None, status()))
    grabber = q.QtWidgets.QWidget.keyboardGrabber()
    grabbed = grabber is not None and grabber.objectName()
    target = grabber or window()
    press = q.QtGui.QKeyEvent(E.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    q.QtWidgets.QApplication.sendEvent(target, press)
    settle()
    after = values_of(control_plugs(A.rig))
    back = max(abs(after[p] - v) for p, v in before.items())
    now_curves = curve_state()
    changed = [c for c in curves if now_curves.get(c) != curves[c]]
    gate("middle Esc puts every value back, nothing keyed",
         not window().blending() and back <= 1e-9 and not changed
         and len(now_curves) == len(curves) and "cancelled" in status(),
         "the keyboard grabber %s, worst %.3g off, %d curves changed | '%s'" % (
             grabbed, back, len(changed), status()))
    _mouse(child(canvas.objectName()), E.MouseButtonRelease, centre + q.QtCore.QPoint(dx, 0),
           Qt.MiddleButton, Qt.NoButton)
    after = values_of(control_plugs(A.rig))
    gate("middle the release after Esc keys nothing", max(abs(after[p] - v) for p, v in
                                                         before.items()) <= 1e-9
         and len(curve_state()) == len(curves), "")


def phase_apply():
    """The hand card picked, A's control selected, Apply CLICKED: only the hand's controls
    change, the hand lands on its forearm as the card holds it (through the drive form both
    sides keep - verify_poselib_apply's `partial`, 0.01 deg)."""
    from maya_poselib import posemath as pm
    from maya_poselib import rigsolve, store
    A = Char(WORLD["A"])
    cmds.currentTime(FRAME, update=True)
    cmds.select(A.node("FKShoulder_R"), replace=True)        # any part names the character
    settle()
    window().set_folder("")
    window().pick(WORLD["hand"])
    settle()
    before = values_of(A.plugs)
    click("skeldarPoseApply")
    line = status()
    evaluate()
    after = values_of(A.plugs)
    changed = sorted(set(p.rsplit(".", 1)[0].split(":")[-1] for p, v in before.items()
                         if abs(after[p] - v) > 1e-9))
    card = store.read(WORLD["hand"])
    drives = rigsolve.drive_matrices(A.rig)
    game = A.game()
    got = rel(W(game["hand_l"]), drives["lowerarm_l"])
    source = card["bones"]
    want = rel(source["hand_l"]["world"], source["lowerarm_l"].get("drive") or
               source["lowerarm_l"]["world"])
    deg = pm.angle(got, want)
    gate("apply the Apply button: only the hand's controls change",
         changed and "FKWrist_L" in changed and set(changed) <= {"FKWrist_L", "IKArm_L"},
         "%s | '%s'" % (changed, line))
    gate("apply the hand on its forearm as the card holds it", deg <= 0.01, "%.6f deg" % deg)


def _dwm(path):
    """The floating window's own pixels (DWM's copy, PrintWindow) into `path`."""
    from maya_graphoverlay import winstyle
    q = qt()
    top = top_level()
    width, height = top.width(), top.height()
    data = winstyle.capture(int(top.winId()), width, height)
    if not data:
        return None
    image = q.QtGui.QImage(data, width, height, width * 4, q.QtGui.QImage.Format_RGB32).copy()
    image.save(path)
    return image.size()


def phase_photo():
    show_maya()
    window().set_folder("")
    window().pick(WORLD["full"])
    cmds.select(Char(WORLD["B"]).rig.main, replace=True)
    settle(6)
    top = top_level()
    top.raise_()
    settle(6)
    shot = _dwm(SHOTS + "/poselib_window.png")
    gate("photo the window (DWM)", shot is not None, "%s" % shot)
    cmds.select(Char(WORLD["A"]).node("FKWrist_L"), replace=True)
    window().open_save()
    settle(6)
    shot = _dwm(SHOTS + "/poselib_window_save.png")
    window().close_save()
    gate("photo the save panel (DWM)", shot is not None, "%s" % shot)
    panel = model_panel()
    cmds.select(clear=True)
    cmds.viewPlace("persp", eye=(0.0, 220.0, 760.0), lookAt=(0.0, 80.0, 40.0))
    out = SHOTS + "/poselib_viewport"
    #  a JPG blast, saved as PNG: a PNG blast carries alpha and its background reads white
    #  (CLAUDE.md, Viewport Studio)
    blast = os.path.join(cmds.internalVar(userTmpDir=True), "poselib_viewport.jpg")
    cmds.playblast(frame=[frame()], format="image", compression="jpg", quality=95,
                   completeFilename=blast, widthHeight=(1280, 720), percent=100, viewer=False,
                   showOrnaments=False, offScreen=True, forceOverwrite=True,
                   editorPanelName=panel)
    saved = qt().QtGui.QImage(blast).save(out + ".png")
    gate("photo the viewport after the drops (playblast)", saved and os.path.isfile(out + ".png"),
         out + ".png")


def phase_close():
    from maya_poselib import window as w
    if cmds.workspaceControl(w.CONTROL, exists=True):
        cmds.deleteUI(w.CONTROL)
    top = maya_window()
    if top is not None:
        top.showMinimized()
    gate("close", True, "")


class _Recorder(object):
    """`maya.cmds` with every setAttr and getAttr recorded (the solve's own sequence)."""

    def __init__(self, real, log):
        self._real, self._log = real, log

    def __getattr__(self, name):
        fn = getattr(self._real, name)
        if name == "setAttr":
            def set_(*args, **kwargs):
                self._log.append(("set", args, kwargs, None))
                return fn(*args, **kwargs)
            return set_
        if name == "getAttr":
            def get_(*args, **kwargs):
                value = fn(*args, **kwargs)
                self._log.append(("get", args, kwargs, value))
                return value
            return get_
        return fn


def phase_stale():
    """Which read goes stale under the parallel EM: the solve's own setAttr / getAttr sequence
    recorded in DG (`_Recorder` as rigsolve's, fkik's and keys' `cmds`) on a freshly KEYED
    Manny_Rig, replayed in parallel from the same state, every read compared with DG's - the
    first that differs named (with the sets just before it)."""
    from maya_poselib import apply as ap
    from maya_poselib import capture, rigsolve, keys
    from maya_scenesetup import fkik
    new_scene()
    cmds.playbackOptions(minTime=0, maxTime=60, animationStartTime=0, animationEndTime=60)
    a, b = Char(add("Manny_Rig").namespace), Char(add("Manny_Rig").namespace)
    set_values(pose_values(a, seed=0.3))
    evaluate()
    card, _note = capture.build_pose([a.rig.main])
    for plug, value in pose_values(b, seed=1.1).items():
        cmds.setKeyframe(plug, time=0, value=b.defaults.get(plug, 0.0))
        cmds.setKeyframe(plug, time=60, value=value)
    cmds.currentTime(30, update=True)
    log = []
    modules = (rigsolve, fkik, keys)
    real = [m.cmds for m in modules]
    try:
        for m in modules:
            m.cmds = _Recorder(real[0], log)
        rigsolve.FRESH_MODE = DEFAULT_FRESH
        ap.plan_for(card, b.ref)
    finally:
        for m, r in zip(modules, real):
            m.cmds = r
    cmds.evaluationManager(mode="parallel")
    cmds.currentTime(30, update=True)
    say("   %d calls recorded (%d sets)" % (len(log), sum(1 for e in log if e[0] == "set")))
    shown = 0
    first = None
    for i, (op, args, kwargs, value) in enumerate(log):
        if op == "set":
            cmds.setAttr(*args, **kwargs)
            continue
        if args and isinstance(args[0], str) and args[0].endswith(".mode"):
            continue
        try:
            now = cmds.getAttr(*args, **kwargs)
        except Exception:                                    # noqa: BLE001
            continue
        try:
            flat_a = list(om.MMatrix(now)) if isinstance(now, list) and len(now) == 16 else now
            flat_b = list(om.MMatrix(value)) if isinstance(value, list) and len(value) == 16 \
                else value
            if isinstance(flat_a, list) and isinstance(flat_b, list) and \
                    len(flat_a) == len(flat_b) and all(isinstance(x, float) for x in flat_a):
                d = max(abs(x - y) for x, y in zip(flat_a, flat_b))
            elif isinstance(flat_a, float) and isinstance(flat_b, float):
                d = abs(flat_a - flat_b)
            else:
                d = 0.0 if flat_a == flat_b else 1.0
        except Exception:                                    # noqa: BLE001
            continue
        if d > 1e-6:
            if first is None:
                first = i
            if shown < 12:
                previous = [e for e in log[max(0, i - 6):i] if e[0] == "set"]
                say("   #%d %s off by %.4g; sets before: %s" % (
                    i, args[0].split(":")[-1] if args else args, d,
                    [e[1][0].split(":")[-1] for e in previous]))
                shown += 1
    # the log ends with the solve's own restores: replayed, the rig is as found
    cmds.currentTime(31, update=True)
    cmds.currentTime(30, update=True)
    named = log[first][1][0].split(":")[-1] if first is not None else None
    gate("stale the first read that differs in parallel (measured)", True,
         "%s of %d calls: %s" % (first, len(log), named))
    WORLD["stale"] = (first, named)


PHASES = {"stale": phase_stale, "fresh": phase_fresh, "open": phase_open,
          "sizes": phase_sizes, "save": phase_save, "list": phase_list,
          "drop_rig": phase_drop_rig, "drop_floor": phase_drop_floor,
          "floor_check": phase_floor_check, "blend": phase_blend, "middle": phase_middle,
          "apply": phase_apply, "photo": phase_photo, "close": phase_close}
ORDER = ("fresh", "stale", "open", "save", "sizes", "list", "drop_rig", "drop_floor",
         "floor_check", "blend", "middle", "apply", "photo", "close")


def run(phase):
    guard()
    del RESULTS[:]
    t0 = time.time()
    try:
        PHASES[phase]()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        gate("%s ran to its end" % phase, False, "")
    finally:
        # `fresh` and `stale` switch the solve's evaluation and the manager: never left so
        from maya_poselib import rigsolve
        rigsolve.FRESH_MODE = DEFAULT_FRESH
        if cmds.evaluationManager(query=True, mode=True)[0] != "parallel":
            cmds.evaluationManager(mode="parallel")
    totals = WORLD.setdefault("totals", {})
    totals[phase] = (sum(RESULTS), len(RESULTS))
    say("SUMMARY %s %d/%d in %.1f s" % (phase, sum(RESULTS), len(RESULTS), time.time() - t0))
    # out of the animator's sight between two sends (a disposable Maya on their screen gets
    # closed - the memory's lesson); a phase that needs the viewport restores it
    top = maya_window()
    if top is not None:
        top.showMinimized()
