"""The Pose Library's ANIMATION cards, live, in a DISPOSABLE GUI Maya (2026-10-08).

What only a GUI Maya can prove: the preview sheet made from a real playblast, the playback on
hover and in the details, the window's widgets driven by real Qt events, the progress window,
the drops, undo with autoKey on under the GUI's parallel evaluation manager, the per-frame cost
of a paste there, pictures. The scene halves (capture, paste modes, options, cross, mirror,
blend, objects, undo in DG) are `verify_poselib_anim.py`'s, in mayapy standalone.

Never in the animator's Maya (port 7001): this adds rigs, keys them and starts a new scene. A
second Maya is launched for it with a scratch MAYA_APP_DIR (its own prefs), `MAYA_NO_HOME=1`
(trap 109: a fresh prefs folder keeps MayaWindow hidden behind the Home screen otherwise) and a
userSetup in `<MAYA_APP_DIR>/2027/scripts/` opening port 7051 deferred; it is killed after. Each
send runs one PHASE through `verify_poselib_anim_gui_run.py`, sent by
`verify_poselib_anim_gui_send.py`:

    open      a new scene, two Manny_Rigs: A keyed over 0..23 (every FK control and RootX_M at
              five frames, another pose at each, Main travelling (0, 0, 0) -> (60, 0, 120) and
              turning 30 deg), B standing at (200, 0, -100) turned 90 deg; the playback range
              0..80 (so the save panel's range is the run's to set); the run's library in TEMP;
              every remembered option of the window removed; the hub opened on its Pose Library
              card and its Open button CLICKED
    save      A's Main selected, + Save CLICKED, the Animation segment CLICKED (Start / End read
              the playback range), the range set to 0..23 (the line «24 frames · 24 preview
              cells»), the panel photographed, Save CLICKED: an `.anim` card - its header of 24
              frames, `frames.json.gz`, a 640 px still, `preview.jpg` a 5 x 5 sheet of 320 px
              cells (24 used), each cell not blank (the 25th, black, the control), cells 0 / 6 /
              11 / 17 / 23 each nearest a fresh blast of ITS frame (the order), each cell
              differing from the next more than one frame rendered twice does (its cell against
              its own fresh blast: the noise floor); the progress window opened with 48 steps
              (24 frames + 24 cells), shown while stepping and gone after
    list      the grid lists the card as an animation and paints its badge (against the same
              card painted as a pose); + Save opens as the last save was; a pose card saved
              through the window (the Pose segment); the type filter: Animations lists the
              animation only, Poses the pose only; the search knows the type word
    hover     sent mouse moves onto the card: the canvas plays its sheet - many cells drawn in
              ~0.7 s, two renders 200 ms apart drawing cells ~6 apart (30 fps) with different
              pixels (two renders at a frozen clock: identical, the control); a frame's repaint
              timed; the window photographed hovered; a Leave stops the timer and the drawing
    details   the card picked by a click: the details picture changes over time (a pose card's
              does not: the control), the options block shown (hidden for a pose); the defaults
              read back, then Insert, At current time off, Connect on, Source keys, In place on
              and the range 5..15 CLICKED / set - `options()` and the remembered optionVars read
              back exactly that; the details photographed (the side panel scrolled to the block)
    apply     back to the defaults but Insert, B carrying a take of its own (keys at 30, 40, 50,
              70 on its FK controls, RootX_M and Main at its place), the time at 40, a part of B
              selected (the window's line follows), Apply CLICKED: every channel the paste keyed
              carries the clip on 40..63 and its old keys at or after 40 moved 24 later with
              their values (the ones before 40 kept), every other channel key for key; B's
              member bones on the card relative to its root (0.05 deg; the next frame of the card
              as the control); B's root on A's travel carried from where B stood at 40 (0.05 cm /
              0.05 deg); A untouched; the progress window of 24 steps; the PER-FRAME COST of the
              paste in the GUI (parallel EM, one DG switch for the walk) reported; a viewport
              playblast
    undo      autoKey ON, the parallel EM: an unkeyed tweak on A's keyed wrist, a marker step (a
              locator moved), then Replace onto B at 100 CLICKED: nothing keyed at idle after it,
              autoKey still on; ONE undo puts every curve back and leaves the tweak standing; a
              second undo takes the marker back, not an autoKey toggle (Task 10's review)
    drop_floor at frame 10, nothing selected: the card pressed, dragged past the start distance
              and released over the empty floor with SENT mouse events on the canvas: the aim is
              the floor near the aimed point, the line «- adding it» (the drop is DEFERRED - one
              idle - so it is measured in the next send, trap 191); its progress window watched
    floor_check one new Manny_Rig, its root at frame 10 ON the point facing as Add put it, its
              members on the card relative to its root and its root on the card's travel from
              there over 10..33, 24 keys on a control; the floor paste's progress window (and how
              long it stood at 0 while the character was added); a viewport playblast
    drop_rig  C (the floor's rig) keyed at 60 and 80 too, the card dragged onto its projected
              pelvis with Replace at 50: its keys inside 50..73 cut, the clip keyed there, the
              rest kept; C on the card from where it stood; A and B untouched
    replace   right-button rows of the animation card: a plain refresh keeps the decoded sheet
              (Task 9's review, minor 3); «Replace thumbnail and preview» from another camera -
              a new still and a new sheet of the same grid, the frames untouched, the card's own
              sheet decoded again; «Update from selection» onto C's take over the card's range,
              the still and the preview byte for byte
    minimised the details playback with Maya minimised (Windows hides the floating window, Qt
              still says visible): it rests - a beat every PLAY_HIDDEN_MS, nothing drawn - and
              plays again when Maya is back (before the fix it drew on at 33 ms)
    close     the window closed

Widgets are found AGAIN by objectName right before each use (trap 148); buttons are CLICKED
(`QAbstractButton.click`), the mouse is `QApplication.sendEvent` of real QMouseEvents. Pictures go
through DWM (`maya_graphoverlay.winstyle.capture`) - never `QWidget.grab()` of Maya widgets (trap
134); only our own CardCanvas, which holds no Maya widget, is `render`ed into a QImage to read
what it paints. Every gate prints `PASS/FAIL <name> <value>`, each send ends `SUMMARY x/y`. Maya
is minimised again at the end of every send - a disposable Maya on the animator's screen gets
used (trap 85) - and a phase that projects, picks, plays or blasts restores it first (trap 192).
The floating control is built once, never deleted and opened again mid-run (`minimised` rebuilds
it in place when a fix changed its module): the run that churned it found a Maya that
un-minimised itself mid-pump and, later, crashed while idle in Qt's window-message dispatch.

    $env:POSELIB_ANIM_GUI_OUT = "<a scratch folder>"
    foreach ($p in "open","save","list","hover","details","apply","undo","drop_floor",
                   "floor_check","drop_rig","replace","minimised","close") {
        & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' `
            docs/superpowers/plans/verify_poselib_anim_gui_send.py $p }   # --purge on the first

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md ("Save", "The window",
"Apply - the options", "Drops")
"""

import math
import os
import sys
import tempfile
import time
import traceback

import maya.api.OpenMaya as om
import maya.cmds as cmds

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
SHOTS = HERE
WORLD = sys.__dict__.setdefault("_verify_poselib_anim_gui", {})
RESULTS = []

ROT = ("rotateX", "rotateY", "rotateZ")
TR = ("translateX", "translateY", "translateZ")
UNROLLED_LIMB = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot"}
HINGE = {"Elbow": ("Shoulder", "Wrist"), "Knee": ("Hip", "Ankle")}

START, END = 0, 23                 # A's clip
KEY_FRAMES = (0, 6, 12, 18, 23)    # ... keyed here
TRAVEL = (60.0, 0.0, 120.0)        # A's Main over the take
TURN = 30.0
PLAYBACK = (0, 80)                 # the scene's playback range: NOT the clip's, so the save
#                                    panel's range is the run's to set
B_PLACE, B_TURN = (200.0, 0.0, -100.0), 90.0
B_TAKE = (30.0, 40.0, 50.0, 70.0)  # B's own keys before the paste
AT = 40                            # where the Insert paste lands
SUB_RANGE = (5, 15)                # the details phase's sub-range
FLOOR = (-150.0, 0.0, 150.0)       # the empty floor of the drop
FLOOR_FRAME = 10                   # the current frame at the drop (At current time on)
DROP_AT = 50                       # where the card dropped on the floor rig lands (Replace)
UNDO_AT = 100                      # the undo phase's Replace onto B
MARKER_TX = 7.0                    # ... and its marker step: a locator moved there
SNAP_FRAME = 12                    # the frame the save panel's snapshot is taken at
CAMERA = dict(eye=(40.0, 190.0, 720.0), lookAt=(20.0, 80.0, 20.0))
TOL_DEG = 0.05                     # the controller's tolerance for the GUI (the standalone verify
TOL_CM = 0.05                      # holds 0.01): bones relative to their root, the travel
SPREAD_MIN = 6.0                   # a cell's grey-level standard deviation: a blank one is ~0
SAMPLE = 4                         # every 4th pixel each way when an image is measured
CHANGED = 16                       # grey levels: a pixel changed by more moved (not JPG noise)


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


def pump(ms):
    """The event loop turned for `ms` of real time (the Qt timers fire in it)."""
    q = qt()
    end = time.time() + ms / 1000.0
    while time.time() < end:
        q.QtWidgets.QApplication.processEvents()
        time.sleep(0.002)


def idle():
    """Maya's idle queue turned (the scriptJobs run there), then Qt's events."""
    import maya.utils
    maya.utils.processIdleEvents()
    settle()


def W(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def matrix_diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def frame():
    return float(cmds.currentTime(query=True))


def go(t):
    """A REAL time change: every keyed channel and the rig downstream read fresh (traps 14, 69)."""
    cmds.currentTime(t, update=True)


def evaluate():
    t = frame()
    go(t + 1)
    go(t)


def maya_window():
    for top in qt().QtWidgets.QApplication.topLevelWidgets():
        if top.objectName() == "MayaWindow":
            return top
    return None


def show_maya():
    """MayaWindow restored (a minimised one draws no viewport: no pick, no projection - trap
    192)."""
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


def port_of(panel):
    import maya.api.OpenMayaUI as omui
    view = omui.M3dView.getM3dViewFromModelPanel(panel)
    return view.portWidth(), view.portHeight()


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


def visible_titles():
    """The titles of every visible top-level window (the progress window is one)."""
    out = []
    for top in qt().QtWidgets.QApplication.topLevelWidgets():
        try:
            if top.isVisible() and top.windowTitle():
                out.append(top.windowTitle())
        except RuntimeError:
            continue
    return out


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
    for child_ in host.findChildren(qt().QtWidgets.QWidget):
        if child_.objectName() == w.ROOT:
            return child_
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


def checked(name):
    button = child(name, qt().QtWidgets.QAbstractButton)
    return None if button is None else bool(button.isChecked())


def spin(name):
    return child(name, qt().QtWidgets.QSpinBox)


def canvas():
    from maya_poselib import cardgrid
    return child(cardgrid.CANVAS_NAME)


def top_level():
    """The floating window holding the control (never MayaWindow - trap 150)."""
    import maya_hubqt
    host = maya_hubqt.find(control())
    top = host.window() if host is not None else None
    if top is not None and top.objectName() == "MayaWindow":
        return None
    return top


def ensure_window():
    """The Pose Library open (a phase run after `close` opens it again, as the hub card does)."""
    from maya_poselib import window as w
    if window() is None:
        w.show_window()
        settle(6)


def raise_window():
    top = top_level()
    if top is not None:
        if top.isMinimized():
            top.showNormal()
        top.raise_()
    settle(6)


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
    for shrink in (1.0, 0.7, 0.5):
        if shrink < 1.0:                   # a corner never clears: a smaller window then
            top.resize(int(top.width() * shrink), int(top.height() * shrink))
            settle()
        for x, y in [(screen.right() - top.frameGeometry().width(), screen.top()),
                     (screen.right() - top.frameGeometry().width(),
                      screen.bottom() - top.frameGeometry().height()),
                     (screen.left(), screen.top()),
                     (screen.left(), screen.bottom() - top.frameGeometry().height())]:
            top.move(x, y)
            settle()
            if not covers():
                return "window %dx%d moved to (%d, %d)" % (top.width(), top.height(), x, y)
    return "the window covers a point wherever it stands"


def status():
    label = child("skeldarPoseStatus")
    return label.text() if label is not None else ""


def mouse(widget, kind, local, button=None, buttons=None):
    """A real QMouseEvent sent to `widget` at `local` (QPoint)."""
    q = qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    Qt = QtCore.Qt
    types = {"move": QtCore.QEvent.MouseMove, "press": QtCore.QEvent.MouseButtonPress,
             "release": QtCore.QEvent.MouseButtonRelease}
    button = Qt.NoButton if button is None else button
    buttons = (button if kind == "press" else Qt.NoButton) if buttons is None else buttons
    event = QtGui.QMouseEvent(types[kind], QtCore.QPointF(local),
                              QtCore.QPointF(widget.mapToGlobal(local)), button, buttons,
                              Qt.NoModifier)
    q.QtWidgets.QApplication.sendEvent(widget, event)


def leave(widget):
    q = qt()
    q.QtWidgets.QApplication.sendEvent(widget, q.QtCore.QEvent(q.QtCore.QEvent.Leave))


def card_index(cv, path):
    paths = [card.path for card in cv.cards]
    return paths.index(path) if path in paths else None


def card_centre(cv, index):
    x, y, w_, h_ = cv.rects()[index][:4]
    return qt().QtCore.QPoint(int(x + w_ / 2), int(y + w_ / 2))


def _dwm(path):
    """The floating window's own pixels (DWM's copy, PrintWindow) into `path`; its size."""
    from maya_graphoverlay import winstyle
    q = qt()
    top = top_level()
    if top is None:
        return None
    width, height = top.width(), top.height()
    data = winstyle.capture(int(top.winId()), width, height)
    if not data:
        return None
    image = q.QtGui.QImage(data, width, height, width * 4, q.QtGui.QImage.Format_RGB32).copy()
    image.save(path)
    return image.width(), image.height()


def blast_png(name, at):
    """A playblast of the viewport at frame `at` saved as `SHOTS/<name>.png` - a JPG blast saved
    as PNG (a PNG blast carries alpha and its background reads white)."""
    panel = model_panel()
    jpg = os.path.join(cmds.internalVar(userTmpDir=True), name + ".jpg")
    cmds.playblast(frame=[at], format="image", compression="jpg", quality=95,
                   completeFilename=jpg, widthHeight=(1280, 720), percent=100, viewer=False,
                   showOrnaments=False, offScreen=True, forceOverwrite=True,
                   editorPanelName=panel)
    out = SHOTS + "/" + name + ".png"
    return qt().QtGui.QImage(jpg).save(out), out


# ------------------------------------------------------------------ the progress window, seen

class _ProgressSeen(object):
    """`timewalk.Progress` swapped for a subclass that records what Maya's progress window does:
    on entry whether it opened, on each step its progress and whether a window with its title
    stands visible, on exit the progress reached and whether that window is gone. It calls the
    real class for everything: it observes, it does not stand in."""

    def __init__(self):
        from maya_poselib import timewalk
        self.module = timewalk
        self.real = timewalk.Progress
        self.log = []
        log, real = self.log, self.real

        class Seen(real):
            def __enter__(self):
                out = real.__enter__(self)
                log.append({"title": self.title, "total": self.total, "on": self.on,
                            "steps": 0, "shown": 0, "progress": 0, "after": None,
                            "titles": None, "opened": time.time(), "first": None,
                            "closed": None})
                return out

            def step(self, text=""):
                ok = real.step(self, text)
                entry = log[-1]
                if entry["first"] is None:
                    entry["first"] = time.time()
                entry["steps"] += 1
                try:
                    entry["progress"] = int(cmds.progressWindow(query=True, progress=True))
                except Exception:                            # noqa: BLE001
                    pass
                titles = visible_titles()
                if self.title in titles:
                    entry["shown"] += 1
                if entry["titles"] is None:
                    entry["titles"] = titles
                return ok

            def __exit__(self, *args):
                out = real.__exit__(self, *args)
                log[-1]["after"] = self.title in visible_titles()
                log[-1]["closed"] = time.time()
                return out

        self.seen = Seen

    def __enter__(self):
        self.module.Progress = self.seen
        return self

    def __exit__(self, *args):
        self.module.Progress = self.real
        return False

    def of(self, title):
        return [entry for entry in self.log if entry["title"] == title]


def progress_gate(name, seen, title, total):
    """One gate: the progress window `title` opened once with `total` steps, every step taken,
    shown while stepping and gone after."""
    entries = seen.of(title)
    entry = entries[0] if len(entries) == 1 else None
    ok = (entry is not None and entry["on"] and entry["total"] == total and
          entry["steps"] == total and entry["shown"] == total and entry["after"] is False and
          entry["progress"] == total)
    return gate(name, ok, "%s" % (entries if entry is None else dict(
        (k, entry[k]) for k in ("title", "total", "on", "steps", "shown", "progress", "after"))))


# ------------------------------------------------------------------ the characters

def add(key):
    """The new Rig after Add Character of the catalog row `key`; its channel values as Add left
    them recorded (a reset goes back to them)."""
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
    """Every keyable, unlocked, settable scalar channel of the rig's ControlSet members (long
    paths)."""
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


def long_plug(plug):
    node, attr = plug.rsplit(".", 1)
    return (cmds.ls(node, long=True) or [node])[0] + "." + attr


def values_of(plugs):
    return dict((p, float(cmds.getAttr(p))) for p in plugs)


def keys_of(plug):
    """((times), (values)) of the plain curve keying `plug`, ((), ()) without one (no layers in
    this run)."""
    times = cmds.keyframe(plug, query=True, timeChange=True) or []
    values = cmds.keyframe(plug, query=True, valueChange=True) or []
    return tuple(float(t) for t in times), tuple(float(v) for v in values)


def curve_state(plugs):
    return dict((plug, keys_of(plug)) for plug in plugs)


class Char(object):
    """A rig of the run, by namespace: its ref, its channels, its bones (static fields, read
    once)."""

    def __init__(self, namespace):
        from maya_poselib import scene
        self.namespace = namespace
        self.rig = rig_by(namespace)
        self.root = self.rig.skeleton_root
        self.ref = scene.rig_ref(self.rig)
        self.plugs = control_plugs(self.rig)
        self.defaults = WORLD.setdefault("defaults", {}).get(namespace) or {}
        self._bones = None

    def node(self, leaf):
        import maya_rigs
        return maya_rigs.node(self.rig, leaf)

    def bones(self):
        from maya_poselib import scene
        if self._bones is None:
            self._bones = scene.skeleton(self.ref)[0]
        return self._bones

    def game(self):
        return dict((leaf, b["path"]) for leaf, b in self.bones().items())


def _perp(a, b, c):
    from maya_poselib import posemath as pm
    s, e, w = (pm.position(W(n)) for n in (a, b, c))
    line = (w - s).normal()
    return e - (s + line * ((e - s) * line))


def bend_channels(ch, joint, side):
    """(bend, sign, roll, other): which rotate channel of the FK hinge bends it forward
    (measured on the rig, verify_poselib_apply's)."""
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
    """{long plug: value}: every FK control of `maya_asretarget.ROWS` turned, the hinges bent
    forward, RootX_M moved and turned (verify_poselib_gui's)."""
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
                    out[long_plug(plug)] = value
    rootx = ch.node("RootX_M")
    for channel, value in zip(TR + ROT, (3.0, -4.0, 5.0, 8.0, 15.0, -6.0)):
        out[long_plug(rootx + "." + channel)] = value * (1.0 - 0.6 * seed)
    return out


def key_source(a):
    """A's take: every FK control and RootX_M at KEY_FRAMES, another pose at each; Main
    travelling TRAVEL and turning TURN (verify_poselib_anim's)."""
    for n, f in enumerate(KEY_FRAMES):
        for plug, value in pose_values(a, seed=0.35 * n).items():
            cmds.setKeyframe(plug, time=f, value=value)
        u = float(f - START) / (END - START)
        for attr, value in zip(TR + ("rotateY",),
                               (TRAVEL[0] * u, TRAVEL[1] * u, TRAVEL[2] * u, TURN * u)):
            cmds.setKeyframe(a.rig.main + "." + attr, time=f, value=value)
    evaluate()


def key_place(b):
    """B's own take before the paste - an earlier run's wiped first (every curve on its channels
    deleted, Add's values back): its FK controls and RootX_M in another pose at each of B_TAKE,
    its Main at B's place there (all six channels keyed)."""
    curves = cmds.listConnections(b.plugs, source=True, destination=False,
                                  type="animCurve") or []
    if curves:
        cmds.delete(list(set(curves)))
    for plug, value in b.defaults.items():
        try:
            cmds.setAttr(plug, value)
        except RuntimeError:
            pass
    main = b.rig.main
    for n, t in enumerate(B_TAKE):
        for plug, value in pose_values(b, seed=1.0 + 0.4 * n).items():
            cmds.setKeyframe(plug, time=t, value=value)
        for attr, value in zip(TR + ROT, B_PLACE + (0.0, B_TURN, 0.0)):
            cmds.setKeyframe(main + "." + attr, time=t, value=value)
    evaluate()


# ------------------------------------------------------------------ measures

def rel(a, b):
    from maya_poselib import posemath as pm
    return pm.rigid(a) * pm.rigid(b).inverse()


def placed(turn, point):
    values = [float(v) for v in om.MMatrix(turn)]
    values[12:15] = [float(point[0]), float(point[1]), float(point[2])]
    values[15] = 1.0
    return om.MMatrix(values)


def cm_deg(a, b):
    from maya_poselib import posemath as pm
    return (pm.position(a) - pm.position(b)).length(), pm.angle(a, b)


def card_bones(card, i):
    """The card's frame `i` (an index from its first frame) as a pose card's bones."""
    from maya_poselib import animdata
    header, frames = card
    return animdata.bones_at(header, frames, i)


def target_members(header, ch, source):
    """The card's members on `ch`, as the press pairs them (`posemath.pairs`)."""
    from maya_poselib import posemath as pm
    bones = ch.bones()
    pairs = pm.pairs(source, bones)
    wanted = set(header["members"])
    return [leaf for leaf in bones if pairs.get(leaf) in wanted]


def rel_rows(source, ch, members):
    """[(leaf, deg, cm)]: each non-twist member bone RELATIVE TO ITS ROOT against the card's
    frame `source` relative to the card's root - the four unrolled limb bones by where they
    point (verify_poselib_anim's)."""
    from maya_poselib import posemath as pm
    worlds = dict((leaf, pm.rigid(W(path))) for leaf, path in ch.game().items())
    root = pm.root_of(ch.bones())
    s_root = pm.root_of(source)
    g_root, c_root = worlds[root], pm.rigid(source[s_root]["world"])
    rows = []
    for leaf in members:
        if leaf not in worlds or leaf not in source or pm.is_twist(leaf) or leaf == root:
            continue
        got, want = rel(worlds[leaf], g_root), rel(source[leaf]["world"], c_root)
        cm = (pm.position(got) - pm.position(want)).length()
        base = leaf[:-2] if leaf.endswith(("_l", "_r")) else leaf
        kid = UNROLLED_LIMB.get(base)
        if kid is not None and kid + leaf[-2:] in worlds:
            kid = kid + leaf[-2:]
            a = (pm.position(worlds[kid]) - pm.position(worlds[leaf])) * \
                pm.rotation(g_root).inverse()
            b = (pm.position(source[kid]["world"]) - pm.position(source[leaf]["world"])) * \
                pm.rotation(c_root).inverse()
            rows.append((leaf, pm.direction_angle(a, b), cm))
        else:
            rows.append((leaf, pm.angle(got, want), cm))
    return rows


class Worst(object):
    def __init__(self):
        self.value, self.at = 0.0, None

    def see(self, value, at):
        if self.at is None or value > self.value:
            self.value, self.at = value, at

    def __str__(self):
        return "%.6f (%s)" % (self.value, self.at)


def heading(turn):
    """The yaw about world +Y of a world-space turn (the swing-twist split's twist)."""
    q = om.MTransformationMatrix(om.MMatrix(turn)).rotation(asQuaternion=True)
    size = math.hypot(q.y, q.w)
    if size < 1e-12:
        return om.MMatrix()
    return om.MQuaternion(0.0, q.y / size, 0.0, q.w / size).asMatrix()


def root_frames(bones, world=None):
    """(pose frame, rest frame) of a skeleton's root frame: its root bone's own at the floor,
    else its ground frame (verify_poselib_anim's)."""
    from maya_poselib import posemath as pm
    top = pm.root_of(bones)
    rest = pm.matrix(bones[top]["rest"])
    pose = pm.matrix(world if world is not None else bones[top]["world"])
    if pm.has_root(bones):
        return pm.rigid(pose), pm.rigid(rest)
    turn = pm.rotation(rest).inverse() * pm.rotation(pose)
    at_pose, at_rest = pm.position(pose), pm.position(rest)
    return (placed(heading(turn), (at_pose.x, 0.0, at_pose.z)),
            placed(om.MMatrix(), (at_rest.x, 0.0, at_rest.z)))


def body_height(bones):
    from maya_poselib import posemath as pm
    pelvis = next((leaf for leaf, b in sorted(bones.items()) if b.get("canonical") == "pelvis"),
                  "pelvis" if "pelvis" in bones else None)
    top = pm.root_of(bones)
    floor = pm.position(bones[top]["rest"]).y if pm.has_root(bones) else 0.0
    return pm.position(bones[pelvis]["rest"]).y - floor


def body_scale(source, target):
    """Target over source pelvis height, 1.0 within 2 % (posemath's rule) - computed here."""
    ratio = body_height(target) / body_height(source)
    return 1.0 if abs(ratio - 1.0) <= 0.02 else ratio


def expected_root(first, now, target_bones, place, scale):
    """Where the target's root frame stands for the card's frame `now` (the first pasted frame
    `first`): the source root's motion carried into the target's root axes, its translation
    scaled, from where the target stood (`place`) - verify_poselib_anim's."""
    from maya_poselib import posemath as pm
    s_now, s_rest = root_frames(now)
    s_first, _r = root_frames(first)
    motion = pm.rigid(s_now) * pm.rigid(s_first).inverse()
    t_rest = root_frames(target_bones)[1]
    q = pm.rotation(pm.rigid(t_rest) * pm.rigid(s_rest).inverse())
    carried = q * motion * q.inverse()
    return placed(pm.rotation(carried), pm.position(carried) * scale) * place


def target_place(ch):
    """The target's root frame as it stands now."""
    from maya_poselib import posemath as pm
    bones = ch.bones()
    top = pm.root_of(bones)
    return root_frames(bones, W(bones[top]["path"]))[0]


def follow_rows(card, ch, a, members, place, scale, indices):
    """(members' worst deg/cm, the next frame's worst deg - the control -, the root's worst
    cm/deg against the carried travel, how far the root travelled) over the card's frames
    `indices` pasted from `a`."""
    from maya_poselib import posemath as pm
    bones = ch.bones()
    top = pm.root_of(bones)
    first = card_bones(card, 0)
    deg, cm, nxt = Worst(), Worst(), Worst()
    rcm, rdeg = Worst(), Worst()
    travelled = 0.0
    for i in indices:
        go(a + i)
        rows = rel_rows(card_bones(card, i), ch, members)
        for leaf, d, c in rows:
            deg.see(d, "%s @%d" % (leaf, a + i))
            cm.see(c, "%s @%d" % (leaf, a + i))
        if i + 1 < len(card[1]["world"]):
            for leaf, d, _c in rel_rows(card_bones(card, i + 1), ch, members):
                nxt.see(d, "%s @%d" % (leaf, a + i))
        want = expected_root(first, card_bones(card, i), bones, place, scale)
        got = root_frames(bones, W(bones[top]["path"]))[0]
        c, d = cm_deg(got, want)
        rcm.see(c, "@%d" % (a + i))
        rdeg.see(d, "@%d" % (a + i))
        travelled = max(travelled, (pm.position(got) - pm.position(place)).length())
    return deg, cm, nxt, rcm, rdeg, travelled


# ------------------------------------------------------------------ images

def grey(image):
    """(bytes, bytes per line, width, height) of `image` in 8-bit grey."""
    q = qt()
    g = image.convertToFormat(q.QtGui.QImage.Format_Grayscale8)
    return bytes(g.constBits()), g.bytesPerLine(), g.width(), g.height()


def stats(image, rect=None):
    """(mean, standard deviation) of the grey levels of `image` (every SAMPLE-th pixel), inside
    `rect` (x, y, w, h) when given."""
    data, bpl, width, height = grey(image)
    x0, y0, w_, h_ = rect if rect is not None else (0, 0, width, height)
    values = [data[y * bpl + x] for y in range(y0, y0 + h_, SAMPLE)
              for x in range(x0, x0 + w_, SAMPLE)]
    mean = sum(values) / float(len(values))
    return mean, math.sqrt(sum((v - mean) ** 2 for v in values) / float(len(values)))


def mean_diff(a, b, rect_a=None, rect_b=None):
    """The mean absolute grey difference of two images (or a rectangle of each, the same size),
    every SAMPLE-th pixel."""
    da, ba, wa, ha = grey(a)
    db, bb, _wb, _hb = grey(b)
    xa, ya, w_, h_ = rect_a if rect_a is not None else (0, 0, wa, ha)
    xb, yb = (rect_b[0], rect_b[1]) if rect_b is not None else (0, 0)
    total, count = 0, 0
    for dy in range(0, h_, SAMPLE):
        for dx in range(0, w_, SAMPLE):
            total += abs(da[(ya + dy) * ba + xa + dx] - db[(yb + dy) * bb + xb + dx])
            count += 1
    return total / float(count)


def cell_image(sheet, index, columns, size):
    from maya_poselib import look
    x, y, w_, h_ = look.sheet_cell(index, columns, size)
    return sheet.copy(x, y, w_, h_)


def changed(a, b, threshold=None):
    """The share of the sampled pixels (every SAMPLE-th) whose grey levels differ by more than
    `threshold` (CHANGED) between two images of one size: what moved, above a render's noise."""
    threshold = CHANGED if threshold is None else threshold
    da, ba, wa, ha = grey(a)
    db, bb, _wb, _hb = grey(b)
    hits, count = 0, 0
    for y in range(0, ha, SAMPLE):
        for x in range(0, wa, SAMPLE):
            hits += abs(da[y * ba + x] - db[y * bb + x]) > threshold
            count += 1
    return hits / float(count)


def render_canvas(cv):
    """What our CardCanvas paints now, as a QImage (`render`: its own paintEvent - it holds no
    Maya widget, so trap 134 does not reach it)."""
    q = qt()
    image = q.QtGui.QImage(cv.size(), q.QtGui.QImage.Format_ARGB32)
    image.fill(0)
    cv.render(image)
    return image


# ------------------------------------------------------------------ the run's scene

def new_scene():
    cmds.file(new=True, force=True)
    WORLD["defaults"] = {}
    for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
        cmds.loadPlugin(plugin, quiet=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=PLAYBACK[0], maxTime=PLAYBACK[1],
                         animationStartTime=PLAYBACK[0], animationEndTime=PLAYBACK[1])
    cmds.autoKeyframe(state=False)
    cmds.currentTime(START, update=True)


def library_root():
    """The run's own library, in TEMP (never the plugin's poses/, never the animator's)."""
    return os.path.join(tempfile.gettempdir(), "skeldar_anim_gui_library").replace("\\", "/")


def guard():
    """Refuse to run in what looks like the animator's Maya, or onto a library of theirs."""
    app = cmds.internalVar(userAppDir=True).replace("\\", "/")
    if "Documents/maya" in app or cmds.commandPort(":7001", query=True):
        raise RuntimeError("this looks like the animator's Maya (%s) - refused" % app)
    root = library_root().lower()
    if "mayascripts" in root or "skeldaranim" in root:
        raise RuntimeError("the run's library %s is inside a checkout - refused" % root)


def card_paths():
    from maya_poselib import store
    root = library_root()
    return root + "/Walk" + store.ANIM_SUFFIX, root + "/Fist" + store.CARD_SUFFIX


def fresh(path):
    """An earlier run's card at `path` gone (a phase run again saves it again), the window's
    listing read again."""
    import shutil
    if os.path.isdir(path):
        shutil.rmtree(path)
        win = window()
        if win is not None:
            win.refresh()
        settle()


def read_card():
    from maya_poselib import store
    walk = card_paths()[0]
    return store.read(walk), store.read_frames(walk)


# ------------------------------------------------------------------ open

def phase_open():
    import shutil
    import maya_hub
    import maya_hubqt
    from maya_poselib import posemath as pm
    from maya_poselib import rigsolve, store
    from maya_poselib import window as w
    new_scene()
    for key in ("A", "B", "floor_point", "rigs_before", "floor_line"):
        WORLD.pop(key, None)
    root = library_root()
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)
    cmds.optionVar(stringValue=(store.ROOT_VAR, root))
    for var in (w.SORT_VAR, w.SIZE_VAR, w.TYPE_VAR, w.SAVE_TYPE_VAR, w.PASTE_VAR,
                w.AT_CURRENT_VAR, w.CONNECT_VAR, w.KEYS_VAR, w.IN_PLACE_VAR):
        if cmds.optionVar(exists=var):
            cmds.optionVar(remove=var)
    a, b = add("Manny_Rig"), add("Manny_Rig")
    WORLD["A"], WORLD["B"] = a.namespace, b.namespace
    A, B = Char(a.namespace), Char(b.namespace)
    key_source(A)
    for attr, value in zip(TR + ROT, B_PLACE + (0.0, B_TURN, 0.0)):
        cmds.setAttr(B.rig.main + "." + attr, value)
    evaluate()

    # gate 2: A travels and its limbs move; B stands
    go(START)
    main0, root0 = W(A.rig.main), W(A.game()["root"])
    hand0 = rel(W(A.game()["hand_l"]), W(A.game()["root"]))
    b0 = W(B.rig.main)
    go(END)
    main1 = W(A.rig.main)
    hand1 = rel(W(A.game()["hand_l"]), W(A.game()["root"]))
    b1 = W(B.rig.main)
    travel = (pm.position(main1) - pm.position(main0)).length()
    want = math.sqrt(sum(v * v for v in TRAVEL))
    turned = pm.angle(main0, main1)
    hand_moved = (pm.position(hand1) - pm.position(hand0)).length()
    gate("open A keyed over 0..23: Main travels and turns as keyed, its limbs move, B stands",
         abs(travel - want) < 0.01 and abs(turned - TURN) < 0.01 and hand_moved > 5.0 and
         matrix_diff(b0, b1) < 1e-9,
         "Main %.3f cm (keyed %.3f), %.3f deg (keyed %.1f); hand_l moved %.2f cm against its "
         "root; B %.3g" % (travel, want, turned, TURN, hand_moved, matrix_diff(b0, b1)))
    go(SNAP_FRAME)

    show_maya()
    panel = model_panel()
    cmds.modelEditor(panel, edit=True, camera="persp")
    cmds.viewPlace("persp", **CAMERA)
    settle()
    width, height = port_of(panel)
    gate("open a model panel with a real port (trap 105)", width > 200 and height > 200,
         "%s %dx%d" % (panel, width, height))
    mode = cmds.evaluationManager(query=True, mode=True)[0]
    gate("open the GUI runs the parallel evaluation manager, the solve's FRESH_MODE 'off'",
         mode == "parallel" and rigsolve.FRESH_MODE == "off",
         "%s, %r" % (mode, rigsolve.FRESH_MODE))

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
    gate("open the hub's Pose Library card, its Open button clicked: the floating window",
         found and win is not None and floating and win is w.live(),
         "button %s, window %s, floating %s" % (found, win is not None, floating))
    if cmds.workspaceControl(maya_hub.CONTROL, exists=True):
        cmds.workspaceControl(maya_hub.CONTROL, edit=True, close=True)   # off the viewport
    settle()
    win = window()
    gate("open the library is the run's own, empty", win.root == root.rstrip("/") and
         not win.cards_shown(), "%s, %d cards" % (win.root, len(win.cards_shown())))


# ------------------------------------------------------------------ save

def _blast_frames(frames_wanted):
    """{frame: QImage}: the active panel blasted at each frame as the preview blasts it
    (`capture.blast_options`, the HIDDEN flags off, the first frame settled - trap 120), each
    centre-cropped and scaled to the preview's cell; the time and the flags put back."""
    import maya_vpstudio
    from maya_poselib import capture, look
    q = qt()
    panel = maya_vpstudio.active_panel()
    width, height = port_of(panel)
    options = capture.blast_options(panel, width, height)
    shown = capture.shown_flags(panel)
    here = frame()
    folder = tempfile.mkdtemp(prefix="skeldar_anim_gui_blast_").replace("\\", "/")
    out = {}
    try:
        capture.set_flags(panel, dict((flag, False) for flag in shown))
        capture.settle(lambda: capture.blast_file(options, frames_wanted[0], folder + "/s.jpg"),
                       lambda: capture.pump(q))
        for t in frames_wanted:
            path = "%s/f%d.jpg" % (folder, t)
            capture.blast_file(options, t, path)
            out[t] = capture.square_scaled(q, q.QtGui.QImage(path), look.PREVIEW_SIZE)
    finally:
        capture.set_flags(panel, shown)
        go(here)
    return out, panel


def phase_save():
    from maya_poselib import capture, look, store
    from maya_poselib import window as w
    show_maya()
    raise_window()
    A = Char(WORLD["A"])
    fresh(card_paths()[0])
    if cmds.optionVar(exists=w.SAVE_TYPE_VAR):          # never remembered: the panel's Pose
        cmds.optionVar(remove=w.SAVE_TYPE_VAR)
    go(SNAP_FRAME)
    cmds.select(A.rig.main, replace=True)
    idle()
    click("skeldarPoseSave")
    win = window()
    opened = win.saving()
    lit_pose = checked("skeldarPoseSaveType_pose")
    click("skeldarPoseSaveType_anim")
    start_box, end_box = spin("skeldarPoseSaveStart"), spin("skeldarPoseSaveEnd")
    defaults = (start_box.value(), end_box.value())
    gate("save + Save and Animation clicked: the save panel as an animation, Start / End the "
         "playback range", opened and lit_pose and checked("skeldarPoseSaveType_anim") and
         child("skeldarPoseSaveRange").isVisible() and defaults == PLAYBACK and
         window().save_heading.text() == "Save animation" and
         cmds.optionVar(query=w.SAVE_TYPE_VAR) == "anim",
         "panel %s, Pose lit first %s, range %s (playback %s), name '%s', remembered %r" % (
             opened, lit_pose, defaults, PLAYBACK, child("skeldarPoseSaveName").text(),
             cmds.optionVar(query=w.SAVE_TYPE_VAR)))
    spin("skeldarPoseSaveStart").setValue(START)
    spin("skeldarPoseSaveEnd").setValue(END)
    settle()
    words = child("skeldarPoseSaveFrames").text()
    want = w.save_frames_text(START, END)
    gate("save the range set to 0..23: the panel says what it takes", words == want and
         "24 frames" in want and "24 preview cells" in want, "'%s' (computed '%s')" % (
             words, want))
    raise_window()
    shot = _dwm(SHOTS + "/poselib_anim_save.png")
    gate("save the save panel in Animation photographed (DWM)", shot is not None, "%s" % (shot,))

    child("skeldarPoseSaveName", qt().QtWidgets.QLineEdit).setText("Walk")
    walk = card_paths()[0]
    with _ProgressSeen() as seen:
        t0 = time.time()
        click("skeldarPoseSaveOk")
        took = time.time() - t0
    line = status()
    cells = len(look.preview_frames(START, END)[0])
    frames_count = END - START + 1
    progress_gate("save the progress window: %d steps (%d frames + %d cells), shown while "
                  "stepping, gone after" % (frames_count + cells, frames_count, cells),
                  seen, "Saving Walk", frames_count + cells)
    say("   titles seen while saving: %s" % ((seen.of("Saving Walk") or [{}])[0].get("titles"),))
    files = dict((name, os.path.isfile(walk + "/" + name)) for name in (
        store.ANIM_FILE, store.FRAMES_FILE, store.THUMB_FILE, store.PREVIEW_FILE))
    header = store.read(walk) if files[store.ANIM_FILE] else {}
    gate("save Save clicked: an .anim card - its header of 24 frames, frames, still, preview",
         all(files.values()) and header.get("frames") == frames_count and
         header.get("start") == float(START) and header.get("end") == float(END) and
         not window().saving() and window().picked == walk,
         "%s, frames %s (%s-%s), picked %s, %.1f s | '%s'" % (
             files, header.get("frames"), header.get("start"), header.get("end"),
             window().picked == walk, took, line))
    frames = store.read_frames(walk) if files[store.FRAMES_FILE] else {"world": []}
    gate("save the frames file holds the 24 frames, every bone a row",
         len(frames["world"]) == frames_count and
         all(len(row) == 7 * len(frames["bones"]) for row in frames["world"]) and
         len(frames["bones"]) == len(header.get("bones") or {}),
         "%d frames x %d bones, %d drives" % (len(frames["world"]), len(frames["bones"]),
                                              len(frames.get("drive") or {})))
    q = qt()
    still = q.QtGui.QImage(walk + "/" + store.THUMB_FILE)
    _m, still_spread = stats(still) if not still.isNull() else (0.0, 0.0)
    gate("save the still is a %d px square JPG, not blank" % capture.THUMB_SIZE,
         (still.width(), still.height()) == (capture.THUMB_SIZE, capture.THUMB_SIZE) and
         still_spread > SPREAD_MIN, "%dx%d, grey spread %.1f" % (still.width(), still.height(),
                                                               still_spread))

    # the sheet: its grid, every cell not blank, each differing from the next, in frame order
    info = header.get("preview") or {}
    columns = look.sheet_columns(cells)
    rows_ = -(-cells // columns)
    want_info = {"frames": cells, "columns": columns, "size": look.PREVIEW_SIZE, "step": 1}
    sheet = q.QtGui.QImage(walk + "/" + store.PREVIEW_FILE)
    gate("save preview.jpg: a %d x %d sheet of %d px cells, the header naming its grid" % (
        columns, rows_, look.PREVIEW_SIZE),
         info == want_info and (sheet.width(), sheet.height()) == (
             columns * look.PREVIEW_SIZE, rows_ * look.PREVIEW_SIZE) and
         "%d cells" % cells in line,
         "header %s (computed %s), sheet %dx%d" % (info, want_info, sheet.width(),
                                                    sheet.height()))
    size = look.PREVIEW_SIZE
    images = [cell_image(sheet, i, columns, size) for i in range(cells)]
    spreads = [stats(image)[1] for image in images]
    unused = cell_image(sheet, cells, columns, size) if cells < columns * rows_ else None
    unused_spread = stats(unused)[1] if unused is not None else None
    gate("save every cell holds a picture (its grey spread); the unused cell is blank (the "
         "control)", min(spreads) > SPREAD_MIN and unused_spread is not None and
         unused_spread < 1.0,
         "cells %.1f..%.1f, unused cell %.2f" % (min(spreads), max(spreads),
                                                 unused_spread if unused_spread is not None
                                                 else -1))
    # fresh blasts of five frames, as the preview blasts them: the order, and the noise floor -
    # one frame rendered twice (its cell against its own fresh blast) - the cells must clear
    probes = (START, START + 6, START + 11, START + 17, END)
    blasts, panel = _blast_frames(list(probes))
    table = []
    for i in probes:
        table.append([mean_diff(images[i - START], blasts[t]) for t in probes])
    nearest = [probes[min(range(len(row)), key=lambda j, r=row: r[j])] for row in table]
    gate("save cells %s are each nearest a fresh blast of ITS frame (the order)" % (probes,),
         nearest == list(probes),
         "%s; rows (cell) x columns (blast): %s" % (panel, "; ".join(
             " ".join("%.2f" % v for v in row) for row in table)))
    noise = max(changed(images[i - START], blasts[i]) for i in probes)
    steps = [changed(images[i], images[i + 1]) for i in range(cells - 1)]
    gate("save each cell differs from the next more than one frame rendered twice does (the "
         "character moves)", min(steps) > 3.0 * noise and min(steps) > 0.0,
         "pixels off by more than %d grey levels: consecutive cells %.4f..%.4f of the cell, "
         "a frame against its own fresh blast at most %.4f" % (
             CHANGED, min(steps), max(steps), noise))
    WORLD["walk"] = walk


# ------------------------------------------------------------------ list

def phase_list():
    from maya_poselib import store
    from maya_poselib import window as w
    show_maya()
    raise_window()
    walk, fist = card_paths()
    win = window()
    win.set_folder("")
    settle()
    cv = canvas()
    index = card_index(cv, walk)
    card = cv.cards[index] if index is not None else None
    gate("list the grid lists the card as an animation of 24 frames with its sheet",
         card is not None and card.type == "anim" and card.frames == 24 and
         os.path.isfile(card.preview or ""),
         "%s" % ((card.type, card.frames, card.preview) if card else None,))
    # the badge: the card painted as it is against the same card painted as a pose, at rest
    leave(cv)
    pump(250)
    x, y, w_, _h = cv.rects()[index][:4]
    quarter = (int(x + w_ / 2), int(y + w_ * 3 / 4), int(w_ / 2) - 2, int(w_ / 4) - 2)
    painted = render_canvas(cv)
    again = render_canvas(cv)
    real = list(cv.cards)
    try:
        cv.cards[index] = card._replace(type="pose")
        as_pose = render_canvas(cv)
    finally:
        cv.cards[:] = real
        cv.update()
    badge = mean_diff(painted, as_pose, quarter, quarter)
    control_ = mean_diff(painted, again, quarter, quarter)
    gate("list the card paints its badge (its square's bottom-right against the card painted "
         "as a pose; painted twice, the control)", badge > 1.0 and control_ < 1e-9,
         "%.3f grey levels against %.3f" % (badge, control_))

    # a pose card through the window: the Pose segment
    A = Char(WORLD["A"])
    fresh(fist)
    cmds.select(A.node("FKWrist_L"), replace=True)
    idle()
    click("skeldarPoseSave")
    remembered_anim = checked("skeldarPoseSaveType_anim") and \
        child("skeldarPoseSaveRange").isVisible()
    click("skeldarPoseSaveType_pose")
    hidden = not child("skeldarPoseSaveRange").isVisible()
    child("skeldarPoseSaveName", qt().QtWidgets.QLineEdit).setText("Fist")
    click("skeldarPoseSaveOk")
    gate("list + Save opens as the last save was (Animation); a pose card saved through the "
         "window (the Pose segment, no frames row)", remembered_anim and hidden and
         os.path.isfile(fist + "/" + store.POSE_FILE) and
         cmds.optionVar(query=w.SAVE_TYPE_VAR) == "pose", "'%s'" % status())

    combo = child("skeldarPoseType", qt().QtWidgets.QComboBox)
    shown = {}
    for key in ("all", "anim", "pose"):
        combo = child("skeldarPoseType", qt().QtWidgets.QComboBox)
        combo.setCurrentIndex(combo.findData(key))
        settle()
        shown[key] = sorted(os.path.basename(p) for p in window().cards_shown())
    remembered = cmds.optionVar(query=w.TYPE_VAR)
    combo = child("skeldarPoseType", qt().QtWidgets.QComboBox)
    combo.setCurrentIndex(combo.findData("all"))
    settle()
    gate("list the type filter: Animations lists the animation only, Poses the pose only",
         shown["all"] == ["Fist.pose", "Walk.anim"] and shown["anim"] == ["Walk.anim"] and
         shown["pose"] == ["Fist.pose"] and remembered == "pose",
         "%s, remembered %r before All" % (shown, remembered))
    found = {}
    for word in ("animation", "pose", "manny"):
        child("skeldarPoseSearch", qt().QtWidgets.QLineEdit).setText(word)
        settle()
        found[word] = sorted(os.path.basename(p) for p in window().cards_shown())
    child("skeldarPoseSearch", qt().QtWidgets.QLineEdit).setText("")
    settle()
    gate("list the search knows the type word: «animation» finds the animation, «pose» the pose "
         "(«manny», both: the control)", found["animation"] == ["Walk.anim"] and
         found["pose"] == ["Fist.pose"] and found["manny"] == ["Fist.pose", "Walk.anim"],
         "%s" % found)


# ------------------------------------------------------------------ hover

def phase_hover():
    from maya_poselib import look
    show_maya()
    raise_window()
    walk = card_paths()[0]
    win = window()
    win.set_folder("")
    settle()
    cv = canvas()
    index = card_index(cv, walk)
    leave(cv)
    pump(300)
    drawn = []
    real_draw = cv._draw_playing

    def recording(p, card, box):
        did = real_draw(p, card, box)
        if did:
            drawn.append((time.time(), card.path, cv._now() - cv._play_started))
        return did

    cv._draw_playing = recording
    header, _frames = read_card()
    info = header["preview"]
    fps = look.fps_of(header.get("fps"))
    try:
        mouse(cv, "move", card_centre(cv, index))
        on = cv.play_timer.isActive()
        playing = cv._playing == walk
        t0 = time.time()
        pump(250)
        first = render_canvas(cv)
        first_at = cv._now() - cv._play_started
        pump(200)
        second = render_canvas(cv)
        second_at = cv._now() - cv._play_started
        pump(250)
        window_shot = _dwm(SHOTS + "/poselib_anim_hover.png")
        hovered = [d for d in drawn if d[1] == walk and d[0] >= t0]
        cells = sorted(set(look.play_cell(d[2], info["frames"], info["step"], fps)
                           for d in hovered))
        gate("hover a move onto the card: its play timer runs and it plays",
             on and playing and cv.play_timer.interval() == look.PLAY_MS,
             "timer %s at %d ms, playing %s" % (on, cv.play_timer.interval(), playing))
        span = time.time() - t0
        expected = min(info["frames"], int(span * fps / info["step"]))
        gate("hover many different cells drawn while hovered (the clip's own rate)",
             len(cells) >= max(4, expected // 3),
             "%d different cells in %.2f s (%d paints; at %g fps the clip shows %d)" % (
                 len(cells), span, len(hovered), fps, expected))
        cell_a = look.play_cell(first_at, info["frames"], info["step"], fps)
        cell_b = look.play_cell(second_at, info["frames"], info["step"], fps)
        want_step = int(round((second_at - first_at) * fps / 1000.0 / info["step"]))
        got_step = (cell_b - cell_a) % info["frames"]
        tile, _z = cv.shown(index)
        square = tuple(int(v) for v in (tile[0] + 2, tile[1] + 2, tile[2] - 4, tile[2] - 4))
        changed = mean_diff(first, second, square, square)
        gate("hover two renders %d ms apart draw cells %d apart (%d computed at %g fps) with "
             "different pixels" % (second_at - first_at, got_step, want_step, fps),
             abs(got_step - want_step) <= 1 and got_step > 0 and changed > 1.0,
             "cells %d -> %d, the card's square %.2f grey levels apart" % (cell_a, cell_b,
                                                                       changed))
        frozen = cv._now()
        cv._now = lambda: frozen
        try:
            still_a = render_canvas(cv)
            pump(150)
            still_b = render_canvas(cv)
        finally:
            del cv._now
        gate("hover two renders at a frozen clock are identical (the control)",
             mean_diff(still_a, still_b, square, square) < 1e-9,
             "%.3f" % mean_diff(still_a, still_b, square, square))
        # a frame's repaint of what the playing card covers, timed
        times = []
        q = qt()
        reach = cv._reach(index)
        for _ in range(30):
            clock = q.QtCore.QElapsedTimer()
            clock.start()
            cv.repaint(reach)
            times.append(clock.nsecsElapsed() / 1e6)
        times.sort()
        p95 = times[int(len(times) * 0.95) - 1]
        gate("hover a playing frame's repaint is cheap (p95 under 16 ms)", p95 < 16.0,
             "median %.2f ms, p95 %.2f ms over %dx%d" % (times[len(times) // 2], p95,
                                                       reach.width(), reach.height()))
        gate("hover the window photographed with the card hovered (DWM)",
             window_shot is not None, "%s" % (window_shot,))
        leave(cv)
        stopped = not cv.play_timer.isActive() and cv._playing is None
        after = len(drawn)
        pump(300)
        gate("hover a Leave stops the timer and the drawing",
             stopped and len(drawn) == after,
             "timer %s, playing %s, %d draws after the leave" % (
                 cv.play_timer.isActive(), cv._playing, len(drawn) - after))
    finally:
        del cv._draw_playing


# ------------------------------------------------------------------ details

def _thumb_keys(ms):
    """The details picture's distinct pixmaps over `ms` of real time (their cache keys)."""
    keys_ = []
    end = time.time() + ms / 1000.0
    q = qt()
    while time.time() < end:
        q.QtWidgets.QApplication.processEvents()
        label = child("skeldarPoseThumb")
        pixmap = label.pixmap() if label is not None else None
        if pixmap is not None and not pixmap.isNull():
            key = pixmap.cacheKey()
            if not keys_ or keys_[-1] != key:
                keys_.append(key)
        time.sleep(0.005)
    return keys_


def _click_card(path):
    cv = canvas()
    index = card_index(cv, path)
    point = card_centre(cv, index)
    Qt = qt().QtCore.Qt
    mouse(cv, "press", point, Qt.LeftButton)
    mouse(canvas(), "release", point, Qt.LeftButton, Qt.NoButton)
    settle()


def phase_details():
    from maya_poselib import window as w
    show_maya()
    raise_window()
    walk, fist = card_paths()
    # the options as a fresh session finds them: never remembered, the window built again (a
    # run of this phase after another starts where the first did)
    for var in (w.PASTE_VAR, w.AT_CURRENT_VAR, w.CONNECT_VAR, w.KEYS_VAR, w.IN_PLACE_VAR):
        if cmds.optionVar(exists=var):
            cmds.optionVar(remove=var)
    w.rebuild()
    settle(6)
    window().set_folder("")
    settle()
    _click_card(fist)
    pose_keys = _thumb_keys(350)
    pose_options = child("skeldarPoseAnimOptions").isVisible()
    pose_timer = window().play_timer.isActive()
    _click_card(walk)
    keys_ = _thumb_keys(700)
    gate("details the picked animation's picture changes over time (a pose card's does not: "
         "the control)", window().picked == walk and window().play_timer.isActive() and
         len(keys_) >= 5 and len(pose_keys) <= 1 and not pose_timer,
         "%d pictures in 0.7 s (the pose card: %d, its timer %s)" % (len(keys_), len(pose_keys),
                                                                    pose_timer))
    gate("details the options block shown for the animation, hidden for the pose",
         child("skeldarPoseAnimOptions").isVisible() and not pose_options,
         "pose %s" % pose_options)
    defaults = {"mode": "replace", "at_current": True, "start": float(START),
                "end": float(END), "connect": False, "keys": "every", "in_place": False}
    read = window().options()
    gate("details the block starts on the defaults, the range the card's", read == defaults,
         "%s" % read)
    click("skeldarPosePaste_insert")
    click("skeldarPoseAtCurrent")
    click("skeldarPoseConnect")
    click("skeldarPoseKeys_source")
    click("skeldarPoseInPlace")
    spin("skeldarPoseRangeStart").setValue(SUB_RANGE[0])
    spin("skeldarPoseRangeEnd").setValue(SUB_RANGE[1])
    settle()
    want = {"mode": "insert", "at_current": False, "start": float(SUB_RANGE[0]),
            "end": float(SUB_RANGE[1]), "connect": True, "keys": "source", "in_place": True}
    read = window().options()
    remembered = dict((var, cmds.optionVar(query=var)) for var in (
        w.PASTE_VAR, w.AT_CURRENT_VAR, w.CONNECT_VAR, w.KEYS_VAR, w.IN_PLACE_VAR))
    want_vars = {w.PASTE_VAR: "insert", w.AT_CURRENT_VAR: 0, w.CONNECT_VAR: 1,
                 w.KEYS_VAR: "source", w.IN_PLACE_VAR: 1}
    gate("details what was clicked reads back: options() and the remembered optionVars",
         read == want and remembered == want_vars and checked("skeldarPosePaste_insert") and
         checked("skeldarPoseKeys_source") and not checked("skeldarPosePaste_replace"),
         "%s | %s" % (read, remembered))
    raise_window()
    side = child("skeldarPoseSideScroll", qt().QtWidgets.QScrollArea)
    side.ensureWidgetVisible(child("skeldarPoseAnimOptions"))     # the whole block in sight
    settle(6)
    shot = _dwm(SHOTS + "/poselib_anim_details.png")
    side.verticalScrollBar().setValue(0)
    gate("details the details with the options photographed (DWM)", shot is not None,
         "%s" % (shot,))


# ------------------------------------------------------------------ apply

def phase_apply():
    from maya_poselib import posemath as pm
    show_maya()
    raise_window()
    walk = card_paths()[0]
    A, B = Char(WORLD["A"]), Char(WORLD["B"])
    window().set_folder("")
    window().pick(walk)
    settle()
    # back to the defaults but Insert
    if not checked("skeldarPoseAtCurrent"):
        click("skeldarPoseAtCurrent")
    if checked("skeldarPoseConnect"):
        click("skeldarPoseConnect")
    click("skeldarPoseKeys_every")
    if checked("skeldarPoseInPlace"):
        click("skeldarPoseInPlace")
    click("skeldarPosePaste_insert")
    spin("skeldarPoseRangeStart").setValue(START)
    spin("skeldarPoseRangeEnd").setValue(END)
    settle()
    want = {"mode": "insert", "at_current": True, "start": float(START), "end": float(END),
            "connect": False, "keys": "every", "in_place": False}
    read = window().options()
    gate("apply the block back on the defaults but Insert", read == want, "%s" % read)

    key_place(B)
    before = curve_state(B.plugs)
    a_before = curve_state(A.plugs)
    go(AT)
    place = target_place(B)
    cmds.select(B.node("FKWrist_L"), replace=True)
    idle()
    pump(300)
    line = child("skeldarPoseTarget").text()
    apply_on = child("skeldarPoseApply", qt().QtWidgets.QAbstractButton).isEnabled()
    gate("apply the window followed the selection: the line names B, Apply enabled",
         line == "onto %s" % B.namespace and apply_on, "'%s', %s" % (line, apply_on))
    mode_before = cmds.evaluationManager(query=True, mode=True)[0]
    with _ProgressSeen() as seen:
        t0 = time.time()
        click("skeldarPoseApply")
        took = time.time() - t0
    text = status()
    mode_after = cmds.evaluationManager(query=True, mode=True)[0]
    count = END - START + 1
    per_frame = took / count
    WORLD["cost"] = (per_frame, took, count)
    say("   %s" % text)
    progress_gate("apply the progress window: %d steps, shown while stepping, gone after"
                  % count, seen, "Pasting Walk", count)
    gate("apply the per-frame cost of a paste onto a rig in the GUI (under a second a frame)",
         per_frame < 1.0 and mode_before == mode_after == "parallel",
         "%.3f s a frame (%.1f s for %d frames), the EM %s -> %s" % (
             per_frame, took, count, mode_before, mode_after))
    gate("apply the line says what was pasted", text.startswith("Walk onto %s" % B.namespace)
         and "insert" in text and "%d-%d" % (AT, AT + count - 1) in text, "'%s'" % text)

    # the keys: the pasted channels carry the clip on AT..AT+23, their old keys at or after AT
    # moved by the clip's length, those before kept; every other channel key for key
    after = curve_state(B.plugs)
    pasted = [AT + i for i in range(count)]
    keyed, wrong, untouched_bad = [], [], []
    for plug in B.plugs:
        times, values = after[plug]
        old_t, old_v = before[plug]
        if float(AT + 1) in times:
            keyed.append(plug)
            want_t = sorted([t for t in old_t if t < AT] + [float(t) for t in pasted] +
                            [t + count for t in old_t if t >= AT])
            moved = dict((t + count, v) for t, v in zip(old_t, old_v) if t >= AT)
            got = dict(zip(times, values))
            kept = dict((t, v) for t, v in zip(old_t, old_v) if t < AT)
            if list(times) != want_t or any(abs(got[t] - v) > 1e-6 for t, v in moved.items()) \
                    or any(abs(got[t] - v) > 1e-6 for t, v in kept.items()):
                wrong.append(plug)
        elif after[plug] != before[plug]:
            untouched_bad.append(plug)
    had = [p for p in keyed if before[p][0]]
    main_keyed = [p for p in keyed if p.rsplit(".", 1)[0] == cmds.ls(B.rig.main, long=True)[0]]
    gate("apply Insert: every pasted channel carries the clip on %d-%d, its old keys at or "
         "after %d moved %d later with their values, the ones before kept" % (
             AT, AT + count - 1, AT, count),
         len(keyed) > 50 and len(had) > 50 and not wrong and len(main_keyed) == 6,
         "%d channels pasted (%d had a take, Main's %d), %d wrong %s" % (
             len(keyed), len(had), len(main_keyed), len(wrong),
             [p.split("|")[-1] for p in wrong[:3]]))
    gate("apply every channel the paste did not key is key for key as it was",
         not untouched_bad, "%d changed %s" % (len(untouched_bad),
                                               [p.split("|")[-1] for p in untouched_bad[:3]]))
    gate("apply A untouched", curve_state(A.plugs) == a_before, "")

    card = read_card()
    header = card[0]
    members = target_members(header, B, card_bones(card, 0))
    scale = body_scale(header["bones"], B.bones())
    deg, cm, nxt, rcm, rdeg, travelled = follow_rows(card, B, AT, members, place, scale,
                                                     (0, 5, 11, 17, 23))
    gate("apply B's members on the card relative to its root, sampled frames (the next "
         "frame's: the control)", deg.value <= TOL_DEG and cm.value <= TOL_CM and
         nxt.value > 1.0 and len(members) > 60,
         "%s deg, %s cm over %d members; against the next frame %s deg" % (
             deg, cm, len(members), nxt))
    gate("apply B's root on A's travel carried from where B stood at %d" % AT,
         rcm.value <= TOL_CM and rdeg.value <= TOL_DEG and travelled > 100.0 and scale == 1.0,
         "%s cm, %s deg; travelled %.2f cm (scale %.4f)" % (rcm, rdeg, travelled, scale))
    go(AT + count // 2)
    saved, out = blast_png("poselib_anim_viewport", AT + count // 2)
    gate("apply the viewport after the apply (playblast)", saved and os.path.isfile(out), out)
    go(AT)


# ------------------------------------------------------------------ undo, autoKey on

def all_curves():
    """{curve: (times, values)} of every animCurve in the scene."""
    out = {}
    for curve in cmds.ls(type="animCurve") or []:
        times = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        out[curve] = (tuple(float(t) for t in times), tuple(float(v) for v in values))
    return out


def curves_diff(before, after):
    """(changed, gone, new) curve names between two `all_curves` readings."""
    changed = [c for c in before if c in after and before[c] != after[c]]
    return changed, [c for c in before if c not in after], [c for c in after if c not in before]


def phase_undo():
    """Task 10's review asked: an animation Apply through the window with autoKey ON under the
    GUI's PARALLEL evaluation manager - `keys.Tweaks.restore` switches autoKey through
    `MAnimControl.setAutoKeyMode` so the restore leaves no step of its own (standalone runs in
    DG; this path was never run in parallel). The animator's last steps: an unkeyed tweak on
    ANOTHER character's keyed channel (A's wrist), autoKey turned on, a locator moved (the
    marker step); then Replace onto B at UNDO_AT. Nothing keys at idle after the press, autoKey
    is on; ONE `cmds.undo()` takes the whole paste back (every curve as it was) and leaves the
    tweak standing; a second undo takes the MARKER back - not an autoKey toggle."""
    show_maya()
    ensure_window()
    raise_window()
    walk = card_paths()[0]
    A, B = Char(WORLD["A"]), Char(WORLD["B"])
    window().set_folder("")
    window().pick(walk)
    settle()
    click("skeldarPosePaste_replace")
    want = {"mode": "replace", "at_current": True, "start": float(START), "end": float(END),
            "connect": False, "keys": "every", "in_place": False}
    read = window().options()
    gate("undo the block on the defaults (Replace)", read == want, "%s" % read)
    go(UNDO_AT)
    mode = cmds.evaluationManager(query=True, mode=True)[0]

    # the animator's own last steps (each recorded): the tweak, autoKey on, a locator made (it
    # selects itself), B selected, the marker - the last step before the press
    cmds.autoKeyframe(state=False)
    tweak_plug = long_plug(A.node("FKWrist_R") + ".rotateX")
    keyed_before = keys_of(tweak_plug)
    shows = float(cmds.getAttr(tweak_plug))
    tweak = shows + 23.0
    cmds.setAttr(tweak_plug, tweak)
    cmds.autoKeyframe(state=True)
    marker = cmds.spaceLocator(name="skeldarUndoMarker")[0]
    cmds.select(B.node("FKWrist_L"), replace=True)
    cmds.setAttr(marker + ".translateX", MARKER_TX)
    marker_name = cmds.undoInfo(query=True, undoName=True)
    idle()
    pump(300)                               # the window's SelectionChanged job reads B
    line = child("skeldarPoseTarget").text()
    before = all_curves()
    standing = float(cmds.getAttr(tweak_plug))
    gate("undo the scene before the press: parallel EM, autoKey on, the line names B, A's keyed "
         "wrist tweaked unkeyed, the marker the last step",
         mode == "parallel" and cmds.autoKeyframe(query=True, state=True) and
         line == "onto %s" % B.namespace and len(keyed_before[0]) > 1 and
         abs(standing - tweak) < 1e-6 and keys_of(tweak_plug) == keyed_before and
         not cmds.keyframe(marker, query=True, keyframeCount=True),
         "%s, autoKey %s, '%s', tweak %.3f over the curve's %.3f, last step '%s'" % (
             mode, cmds.autoKeyframe(query=True, state=True), line, standing, shows,
             marker_name))

    click("skeldarPoseApply")
    text = status()
    say("   %s" % text)
    pressed = all_curves()
    changed, gone, new = curves_diff(before, pressed)
    auto_after = bool(cmds.autoKeyframe(query=True, state=True))
    tweak_after = float(cmds.getAttr(tweak_plug))
    idle()
    pump(500)
    idled = all_curves()
    at_idle = curves_diff(pressed, idled)
    gate("undo the press pasted onto B (the positive control: curves changed), autoKey ON after "
         "it, the tweak standing, nothing keyed at idle after it",
         text.startswith("Walk onto %s" % B.namespace) and len(changed) + len(new) > 50 and
         auto_after and abs(tweak_after - tweak) < 1e-6 and
         not any(at_idle) and keys_of(tweak_plug) == keyed_before,
         "%d curves changed, %d new, autoKey %s, tweak %.3f; at idle %d changed / %d new | "
         "'%s'" % (len(changed), len(new), auto_after, tweak_after, len(at_idle[0]),
                   len(at_idle[2]), text))

    first_name = cmds.undoInfo(query=True, undoName=True)
    cmds.undo()
    undone = all_curves()
    back = curves_diff(before, undone)
    tweak_undone = float(cmds.getAttr(tweak_plug))
    marker_tx = float(cmds.getAttr(marker + ".translateX"))
    gate("undo ONE undo takes the whole paste back - every curve as it was - and leaves the "
         "tweak standing and the marker moved",
         not any(back) and abs(tweak_undone - tweak) < 1e-6 and
         abs(marker_tx - MARKER_TX) < 1e-9 and
         bool(cmds.autoKeyframe(query=True, state=True)),
         "undid '%s': %d changed, %d gone, %d new; tweak %.3f; marker tx %.3f; autoKey %s" % (
             first_name, len(back[0]), len(back[1]), len(back[2]), tweak_undone, marker_tx,
             cmds.autoKeyframe(query=True, state=True)))
    second_name = cmds.undoInfo(query=True, undoName=True)
    cmds.undo()
    marker_tx = float(cmds.getAttr(marker + ".translateX"))
    auto_second = bool(cmds.autoKeyframe(query=True, state=True))
    gate("undo the second undo takes the MARKER back - not an autoKey toggle",
         abs(marker_tx) < 1e-9 and auto_second and not any(curves_diff(before, all_curves())),
         "undid '%s': marker tx %.3f, autoKey %s" % (second_name, marker_tx, auto_second))
    cmds.autoKeyframe(state=False)          # the run's other phases key with autoKey off
    if cmds.objExists(marker):
        cmds.delete(marker)
    go(START)                               # the tweak let go: the take shows again


# ------------------------------------------------------------------ the floor

def phase_drop_floor():
    import maya_rigs
    q = qt()
    Qt = q.QtCore.Qt
    show_maya()
    raise_window()
    walk = card_paths()[0]
    go(FLOOR_FRAME)
    cmds.select(clear=True)
    idle()
    window().set_folder("")
    settle()
    (gx, gy), = [to_global(FLOOR)]
    say("   %s" % keep_off([(gx, gy)]))
    settle()
    gx, gy = to_global(FLOOR)
    cv = canvas()
    index = card_index(cv, walk)
    press = card_centre(cv, index)
    mouse(cv, "press", press, Qt.LeftButton)
    distance = q.QtWidgets.QApplication.startDragDistance()
    mouse(canvas(), "move", press + q.QtCore.QPoint(distance + 4, 0), Qt.NoButton,
          Qt.LeftButton)
    started = canvas()._drag is not None
    floor_local = canvas().mapFromGlobal(q.QtCore.QPoint(gx, gy))
    mouse(canvas(), "move", floor_local, Qt.NoButton, Qt.LeftButton)
    drag = canvas()._drag or {}
    aim = window().aim(gx, gy, walk, drag.get("snap"))
    point = aim.get("point")
    off = math.sqrt(sum((a - b) ** 2 for a, b in zip(point, FLOOR))) if point else None
    gate("drop_floor the card dragged past the start distance and over the empty floor: the "
         "aim is the floor on the aimed point", started and aim.get("kind") == "floor" and
         off is not None and off < 2.0,
         "drag %s, %s, %.3f cm off" % (started, aim, off if off is not None else -1))
    WORLD["floor_point"] = point
    WORLD["rigs_before"] = [r.namespace for r in maya_rigs.rigs()]
    # the progress window of the deferred paste, watched until floor_check takes it off
    old = WORLD.pop("floor_seen", None)
    if old is not None:
        old.__exit__()
    seen = _ProgressSeen()
    seen.__enter__()
    WORLD["floor_seen"] = seen
    mouse(canvas(), "release", floor_local, Qt.LeftButton, Qt.NoButton)
    line = status()
    WORLD["floor_line"] = line
    gate("drop_floor the release says it is adding it (deferred), the drag over",
         line.endswith("adding it") and canvas()._drag is None, "'%s'" % line)


def phase_floor_check():
    import maya_rigs
    from maya_poselib import posemath as pm
    show_maya()
    seen = WORLD.pop("floor_seen", None)
    if seen is not None:
        seen.__exit__()
    new = [r for r in maya_rigs.rigs() if r.namespace not in WORLD["rigs_before"]]
    gate("floor_check one new rig", len(new) == 1, "%s" % [r.namespace for r in new])
    if len(new) != 1:
        return
    C = Char(new[0].namespace)
    WORLD["C"] = C.namespace
    count = END - START + 1
    if seen is not None:
        progress_gate("floor_check the floor paste's progress window: %d steps, shown while "
                      "stepping, gone after" % count, seen, "Pasting Walk", count)
        entry = (seen.of("Pasting Walk") or [{}])[0]
        if entry.get("first") and entry.get("closed"):
            say("   the floor drop: the progress window stood %.2f s at 0 before its first step "
                "(the Add of the character, Task 9's concern 4), then %.2f s for the %d frames"
                % (entry["first"] - entry["opened"], entry["closed"] - entry["first"], count))
            WORLD["floor_idle"] = (entry["first"] - entry["opened"],
                                   entry["closed"] - entry["first"])
    card = read_card()
    header = card[0]
    point = WORLD["floor_point"]
    go(FLOOR_FRAME)
    bones = C.bones()
    top = pm.root_of(bones)
    at = root_frames(bones, W(bones[top]["path"]))[0]
    rest = root_frames(bones)[1]
    off = math.hypot(pm.position(at).x - point[0], pm.position(at).z - point[2])
    turned = pm.angle(pm.rotation(at), pm.rotation(rest))
    gate("floor_check its root at frame %d ON the point, facing as Add put it" % FLOOR_FRAME,
         off <= 0.01 and abs(pm.position(at).y) < 1e-4 and turned <= 0.01,
         "(%.4f, %.4f, %.4f) for (%.4f, 0, %.4f): %.6f cm, %.6f deg off its rest heading" % (
             pm.position(at).x, pm.position(at).y, pm.position(at).z, point[0], point[2],
             off, turned))
    members = target_members(header, C, card_bones(card, 0))
    scale = body_scale(header["bones"], bones)
    deg, cm, nxt, rcm, rdeg, travelled = follow_rows(card, C, FLOOR_FRAME, members, at, scale,
                                                     (0, 7, 15, 23))
    gate("floor_check its members on the card relative to its root (the next frame's: the "
         "control)", deg.value <= TOL_DEG and cm.value <= TOL_CM and nxt.value > 1.0,
         "%s deg, %s cm; against the next frame %s deg" % (deg, cm, nxt))
    gate("floor_check its root on the card's travel from the point",
         rcm.value <= TOL_CM and rdeg.value <= TOL_DEG and travelled > 100.0,
         "%s cm, %s deg; travelled %.2f cm" % (rcm, rdeg, travelled))
    wrist = long_plug(C.node("FKWrist_L") + ".rotateX")
    times = keys_of(wrist)[0]
    gate("floor_check the clip keyed from frame %d: %d keys on a control" % (FLOOR_FRAME, count),
         list(times) == [float(FLOOR_FRAME + i) for i in range(count)],
         "%d keys %s..%s | '%s'" % (len(times), times[0] if times else None,
                                    times[-1] if times else None, status()))
    saved, out = blast_png("poselib_anim_floor", FLOOR_FRAME + count // 2)
    gate("floor_check the viewport after the drop (playblast)", saved and os.path.isfile(out),
         out)


def _long(node):
    return (cmds.ls(node, long=True) or [node])[0]


def phase_drop_rig():
    """The card dragged onto the floor rig C (sent mouse events) with Replace at 50: C's keys
    inside 50..73 cut, the clip keyed there, the rest kept; C on the card from where it stood."""
    q = qt()
    Qt = q.QtCore.Qt
    show_maya()
    raise_window()
    walk = card_paths()[0]
    A, B, C = Char(WORLD["A"]), Char(WORLD["B"]), Char(WORLD["C"])
    window().set_folder("")
    window().pick(walk)
    settle()
    click("skeldarPosePaste_replace")
    want = {"mode": "replace", "at_current": True, "start": float(START), "end": float(END),
            "connect": False, "keys": "every", "in_place": False}
    read = window().options()
    gate("drop_rig the block on the defaults (Replace)", read == want, "%s" % read)
    # C's own keys inside the paste range (and one after): what Replace must cut and keep
    for t in (DROP_AT + 10, DROP_AT + 30):
        for plug, value in pose_values(C, seed=2.5 + 0.01 * t).items():
            cmds.setKeyframe(plug, time=t, value=value)
    evaluate()
    count = END - START + 1
    go(DROP_AT)
    cmds.select(clear=True)
    idle()
    place = target_place(C)
    before = curve_state(C.plugs)
    others = curve_state(A.plugs + B.plugs)
    pelvis = world_t(C.game()["pelvis"])
    say("   %s" % keep_off([to_global(pelvis)]))
    settle()
    gx, gy = to_global(pelvis)
    cv = canvas()
    press = card_centre(cv, card_index(cv, walk))
    mouse(cv, "press", press, Qt.LeftButton)
    distance = q.QtWidgets.QApplication.startDragDistance()
    mouse(canvas(), "move", press + q.QtCore.QPoint(distance + 4, 0), Qt.NoButton,
          Qt.LeftButton)
    started = canvas()._drag is not None
    local = canvas().mapFromGlobal(q.QtCore.QPoint(gx, gy))
    mouse(canvas(), "move", local, Qt.NoButton, Qt.LeftButton)
    drag = canvas()._drag or {}
    aim = window().aim(gx, gy, walk, drag.get("snap"))
    gate("drop_rig the card dragged over C's projected pelvis: the aim names C",
         started and aim.get("kind") == "character" and
         _long(aim.get("root") or "") == _long(C.root), "%s" % aim)
    with _ProgressSeen() as seen:
        t0 = time.time()
        mouse(canvas(), "release", local, Qt.LeftButton, Qt.NoButton)
        took = time.time() - t0
    text = status()
    say("   %s (%.1f s)" % (text, took))
    progress_gate("drop_rig the progress window: %d steps" % count, seen, "Pasting Walk", count)
    gate("drop_rig the line says it went onto C with Replace over %d-%d" % (
        DROP_AT, DROP_AT + count - 1), text.startswith("Walk onto %s" % C.namespace) and
         "replace" in text and "%d-%d" % (DROP_AT, DROP_AT + count - 1) in text, "'%s'" % text)
    after = curve_state(C.plugs)
    pasted = [float(DROP_AT + i) for i in range(count)]
    keyed, wrong, untouched_bad = [], [], []
    for plug in C.plugs:
        times, values = after[plug]
        old_t, old_v = before[plug]
        if float(DROP_AT + 1) in times:
            keyed.append(plug)
            kept = dict((t, v) for t, v in zip(old_t, old_v)
                        if t < DROP_AT or t > DROP_AT + count - 1)
            got = dict(zip(times, values))
            if list(times) != sorted(list(kept) + pasted) or \
                    any(abs(got[t] - v) > 1e-6 for t, v in kept.items()):
                wrong.append(plug)
        elif after[plug] != before[plug]:
            untouched_bad.append(plug)
    cut = [p for p in keyed if float(DROP_AT + 10) in before[p][0]]
    gate("drop_rig Replace: every pasted channel's keys inside %d-%d cut and the clip keyed, "
         "those outside kept with their values; the others key for key" % (
             DROP_AT, DROP_AT + count - 1),
         len(keyed) > 50 and len(cut) > 50 and not wrong and not untouched_bad,
         "%d pasted (%d had a key at %d to cut), %d wrong %s, %d others changed" % (
             len(keyed), len(cut), DROP_AT + 10, len(wrong),
             [p.split("|")[-1] for p in wrong[:3]], len(untouched_bad)))
    gate("drop_rig A and B untouched", curve_state(A.plugs + B.plugs) == others, "")
    card = read_card()
    header = card[0]
    members = target_members(header, C, card_bones(card, 0))
    scale = body_scale(header["bones"], C.bones())
    deg, cm, nxt, rcm, rdeg, travelled = follow_rows(card, C, DROP_AT, members, place, scale,
                                                     (0, 8, 16, 23))
    gate("drop_rig C's members on the card relative to its root, its root on the travel from "
         "where it stood", deg.value <= TOL_DEG and cm.value <= TOL_CM and nxt.value > 1.0 and
         rcm.value <= TOL_CM and rdeg.value <= TOL_DEG and travelled > 100.0,
         "members %s deg, %s cm (the next frame %s deg); root %s cm, %s deg, travelled %.2f" % (
             deg, cm, nxt, rcm, rdeg, travelled))


def _file_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def phase_replace():
    """Right button rows of the animation card, the real Scene behind them: a plain refresh
    keeping the decoded sheet; «Replace thumbnail and preview» from another camera (two
    playblasts' worth, one progress window); «Update from selection» onto C's take over the
    card's own range, the still and the preview kept."""
    from maya_poselib import animdata, look, store
    from maya_poselib import posemath as pm
    show_maya()
    raise_window()
    walk = card_paths()[0]
    window().set_folder("")
    window().pick(walk)
    settle()
    cv = canvas()
    held = cv.sheet(cv.cards[card_index(cv, walk)])[0]
    window().refresh()
    settle()
    cv = canvas()
    again = cv.sheet(cv.cards[card_index(cv, walk)])[0]
    gate("replace a plain refresh keeps the decoded sheet (Task 9's review, minor 3)",
         again is held and walk in cv.sheets, "the same pixmap %s" % (again is held))

    q = qt()
    old_header = store.read(walk)
    old_sheet = q.QtGui.QImage(walk + "/" + store.PREVIEW_FILE).copy()
    old_still = q.QtGui.QImage(walk + "/" + store.THUMB_FILE).copy()
    frames_bytes = _file_bytes(walk + "/" + store.FRAMES_FILE)
    go(SNAP_FRAME)
    #  another camera than the card's picture was taken from: the save's, or the other of the
    #  two this phase alternates between when it runs again
    turn = WORLD.get("replace_turn", 0)
    WORLD["replace_turn"] = turn + 1
    eye = ((-520.0, 140.0, 330.0), (480.0, 260.0, 420.0))[turn % 2]
    cmds.viewPlace("persp", eye=eye, lookAt=(20.0, 80.0, 20.0))
    settle()
    rows = dict(row for row in window().context_actions(walk) if row)
    with _ProgressSeen() as seen:
        rows["Replace thumbnail and preview"]()
    line = status()
    cmds.viewPlace("persp", **CAMERA)
    settle()
    cells = len(look.preview_frames(START, END)[0])
    progress_gate("replace the progress window: %d steps (the cells)" % cells, seen,
                  "Previewing Walk", cells)
    header = store.read(walk)
    new_sheet = q.QtGui.QImage(walk + "/" + store.PREVIEW_FILE)
    new_still = q.QtGui.QImage(walk + "/" + store.THUMB_FILE)
    size = look.PREVIEW_SIZE
    columns = look.sheet_columns(cells)
    moved = mean_diff(cell_image(old_sheet, 0, columns, size),
                      cell_image(new_sheet, 0, columns, size))
    steps = [changed(cell_image(new_sheet, i, columns, size),
                     cell_image(new_sheet, i + 1, columns, size)) for i in range(cells - 1)]
    gate("replace «Replace thumbnail and preview»: a new still and a new sheet of the same grid "
         "(another camera), the frames file untouched",
         line.startswith("new thumbnail and preview") and
         header.get("preview") == old_header.get("preview") and moved > 2.0 and
         mean_diff(old_still, new_still) > 2.0 and min(steps) > 0.0 and
         _file_bytes(walk + "/" + store.FRAMES_FILE) == frames_bytes,
         "cell 0 moved %.2f grey levels, the still %.2f; consecutive new cells changed "
         "%.4f..%.4f | '%s'" % (moved, mean_diff(old_still, new_still), min(steps), max(steps),
                                 line))
    cv = canvas()
    reread = cv.sheet(cv.cards[card_index(cv, walk)])[0]
    gate("replace the card's own sheet decoded again (forget(path))", reread is not held and
         mean_diff(reread.toImage(), new_sheet) < 1e-9, "a new pixmap %s" % (reread is not held))

    # Update from selection: C's take over the card's own range, the still and the preview kept
    C = Char(WORLD["C"])
    sheet_bytes = _file_bytes(walk + "/" + store.PREVIEW_FILE)
    still_bytes = _file_bytes(walk + "/" + store.THUMB_FILE)
    cmds.select(C.rig.main, replace=True)
    idle()
    win = window()
    asked = []
    win.confirm = lambda title, text: asked.append((title, text)) or True   # the dialog said yes
    try:
        rows = dict(row for row in win.context_actions(walk) if row)
        with _ProgressSeen() as seen:
            rows["Update from selection"]()
    finally:
        del win.confirm
    line = status()
    count = END - START + 1
    progress_gate("replace Update's progress window: %d steps (the frames)" % count, seen,
                  "Updating Walk", count)
    header = store.read(walk)
    frames = store.read_frames(walk)
    bones = C.bones()
    root = pm.root_of(bones)
    worst = Worst()
    for i in (0, 9, 17, 23):
        go(START + i)
        decoded = animdata.bones_at(header, frames, i)
        worst.see(matrix_diff(decoded[root]["world"], pm.rigid(W(bones[root]["path"]))),
                  "@%d" % (START + i))
    gate("replace «Update from selection»: the card is C's take over 0..23 (its root's decoded "
         "world the scene's), the still and the preview byte for byte",
         asked and asked[0][0] == "Update animation" and
         header["character"]["namespace"] == C.namespace and header["frames"] == count and
         header["start"] == float(START) and header["end"] == float(END) and
         worst.value <= 1e-5 and
         _file_bytes(walk + "/" + store.PREVIEW_FILE) == sheet_bytes and
         _file_bytes(walk + "/" + store.THUMB_FILE) == still_bytes,
         "%s, root %s | '%s'" % (header["character"]["namespace"], worst, line))


def _seen(top):
    """(Qt's isVisible, Qt's isExposed, Win32's IsWindowVisible) of a top-level widget."""
    import ctypes
    if top is None:
        return None
    handle = top.windowHandle()
    return (top.isVisible(), handle.isExposed() if handle is not None else None,
            bool(ctypes.windll.user32.IsWindowVisible(int(top.winId()))))


def phase_minimised():
    """The details playback - and the hovered card beside it - with Maya minimised. Windows then
    hides the floating window while Qt still calls it visible (no hideEvent); the details rest
    (a beat every PLAY_HIDDEN_MS, nothing drawn) and play again once Maya is back. Before the
    fix (2026-10-08) they ticked on at 33 ms, 0.8 ms each, drawing cells nobody saw."""
    import ctypes
    from maya_poselib import look
    from maya_poselib import window as w
    show_maya()
    # built again IN PLACE (`rebuild`, the plugin's own road) only when the module loaded now is
    # not the one that built it: deleting and opening the floating control on every run was
    # followed by a Maya that un-minimised itself mid-pump and, later, crashed while idle
    if window() is None:
        w.show_window()
        settle(6)
    elif window() is not w.live():
        w.rebuild()
        settle(6)
    raise_window()
    walk = card_paths()[0]
    window().set_folder("")
    window().pick(walk)
    settle()
    win, cv = window(), canvas()
    ticks, pictures, drawn = [], [], []
    real_tick, real_draw = win._play_tick, cv._draw_playing

    def counting():
        t0 = time.perf_counter()
        real_tick()
        ticks.append(time.perf_counter() - t0)
        key = win.thumb.pixmap().cacheKey()
        if not pictures or pictures[-1] != key:
            pictures.append(key)

    def drawing(p, card, box):
        did = real_draw(p, card, box)
        if did:
            drawn.append(time.time())
        return did

    def reading(span):
        return dict(ticks=len(ticks), pictures=max(0, len(pictures) - 1),
                    tick_ms=round(1000.0 * sum(ticks) / max(1, len(ticks)), 3),
                    interval=win.play_timer.interval(), timer=win.play_timer.isActive(),
                    canvas_draws=len(drawn), canvas_timer=cv.play_timer.isActive(),
                    floating=_seen(top_level()), span_ms=span)

    def reset():
        del ticks[:], drawn[:]
        pictures[:] = [win.thumb.pixmap().cacheKey()]

    win.play_timer.timeout.disconnect()
    win.play_timer.timeout.connect(counting)
    cv._draw_playing = drawing
    try:
        reset()
        pump(600)
        shown = reading(600)
        mouse(cv, "move", card_centre(cv, card_index(cv, walk)))        # the card hovered too
        pump(100)
        reset()
        maya_window().showMinimized()
        pump(1200)
        hidden = reading(1200)
        hidden["maya_iconic"] = bool(ctypes.windll.user32.IsIconic(int(maya_window().winId())))
        show_maya()
        raise_window()
        reset()
        pump(1000)
        back = reading(1000)
    finally:
        win.play_timer.timeout.disconnect()
        win.play_timer.timeout.connect(win._play_tick)
        del cv._draw_playing
        leave(cv)
    for label, state in (("shown", shown), ("minimised", hidden), ("back", back)):
        say("   %s: %s" % (label, state))
    WORLD["minimised"] = (shown, hidden, back)
    most = 1 + int(math.ceil(1200.0 / w.PLAY_HIDDEN_MS))
    gate("minimised shown, the details play (the control): pictures change every few ticks",
         shown["ticks"] >= 10 and shown["pictures"] >= 5 and shown["interval"] == look.PLAY_MS,
         "%d ticks, %d pictures in 0.6 s" % (shown["ticks"], shown["pictures"]))
    gate("minimised with Maya minimised (the window hidden by Windows, Qt still saying visible) "
         "the details rest: at most %d beats in 1.2 s, nothing drawn" % most,
         hidden["maya_iconic"] and hidden["floating"][2] is False and
         hidden["floating"][1] is False and hidden["ticks"] <= most and
         hidden["pictures"] == 0 and hidden["interval"] == w.PLAY_HIDDEN_MS,
         "%d beats, %d pictures, every %d ms, %.3f ms a beat; floating (visible, exposed, "
         "Win32 visible) %s; the hovered canvas: %d draws, its timer %s" % (
             hidden["ticks"], hidden["pictures"], hidden["interval"], hidden["tick_ms"],
             hidden["floating"], hidden["canvas_draws"], hidden["canvas_timer"]))
    gate("minimised Maya back: the details play again at %d ms" % look.PLAY_MS,
         back["interval"] == look.PLAY_MS and back["pictures"] >= 5 and
         back["floating"][1] is True,
         "%d pictures in 1 s, every %d ms" % (back["pictures"], back["interval"]))


def phase_close():
    from maya_poselib import window as w
    if cmds.workspaceControl(w.CONTROL, exists=True):
        cmds.deleteUI(w.CONTROL)
    gate("close the window closed", not cmds.workspaceControl(w.CONTROL, exists=True), "")


PHASES = {"open": phase_open, "save": phase_save, "list": phase_list, "hover": phase_hover,
          "details": phase_details, "apply": phase_apply, "undo": phase_undo,
          "drop_floor": phase_drop_floor,
          "floor_check": phase_floor_check, "drop_rig": phase_drop_rig,
          "minimised": phase_minimised,
          "replace": phase_replace, "close": phase_close}
ORDER = ("open", "save", "list", "hover", "details", "apply", "undo", "drop_floor", "floor_check",
         "drop_rig", "replace", "minimised", "close")


def run(phase):
    guard()
    del RESULTS[:]
    from maya_poselib import window as w
    say("   the plugin: %s" % os.path.dirname(os.path.dirname(w.__file__)).replace("\\", "/"))
    t0 = time.time()
    try:
        PHASES[phase]()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        gate("%s ran to its end" % phase, False, "")
    totals = WORLD.setdefault("totals", {})
    totals[phase] = (sum(RESULTS), len(RESULTS))
    say("SUMMARY %s %d/%d in %.1f s" % (phase, sum(RESULTS), len(RESULTS), time.time() - t0))
    # out of the animator's sight between two sends; a phase that needs the viewport restores it
    top = maya_window()
    if top is not None:
        top.showMinimized()
