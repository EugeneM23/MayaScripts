"""verify_hub_compact.py - the compact hub (variant B): live.

Run in a DISPOSABLE GUI Maya (scratch MAYA_APP_DIR, MAYA_NO_HOME, a
userSetup.py opening its own command port), never the animator's: phases are
sent one per line, `run(phase, build, source)` called by a runner that marks
`<out>.ran` first and guards with an `if` (the port runs a line twice;
bridge notes 5, 7, 8). Every widget is found AGAIN by name in each send and
never kept across `processEvents` (traps 135, 148); pictures come from DWM's
copy of the window (PrintWindow), never `.grab()` (trap 134).

The hub is the INSTALLED copy's (bridge note 9): `install` copies the plugin
folder it is given into the scratch userAppDir and opens the hub from there.
The same script measures the build before the compact hub (`ed00397`, from a
`git archive`, in a second disposable Maya) for the heights gate and the
classic hub's width.

The disposable Maya stands on the animator's screen and they try a new hub
as soon as it appears (trap 100, measured three times on 2026-10-08: the edge
panel switched on between two sends, every card but two collapsed, the
animation list's source changed). Hence `all`: the dock forced back and every
phase in ONE send, the hub's root deaf to the real mouse first.

    all       dock, size, heights, cards, relay, notes, grips, grips2, watch,
              picture, classic2, restore - in one send (build "new")
    install   SOURCE: install that plugin folder, open the hub
    open      the hub of the copy installed earlier (a Maya restarted)
    dock      the edge panel off (deferred), when somebody switched it on
    size      float the hub, size it until its scroll viewport is the
              animator's dock (510 physical), Interface animations off, every
              card opened through maya_hub.expand
    heights   every card's height and the content's -> heights_<build>.json;
              with both builds measured: gate 2
    cards     gate 1: the content's minimum width within the viewport; no
              widget past its card's right edge; every row within 30 logical
              except the lists and tiles; no text clipped; a header line too
              long elided, its tooltip the whole text
    relay     gate 3: each section's status writer -> the hub's message line,
              that card's icon at its left, the card's height unchanged
    notes     gate 4: the static hints are their cards' header tooltips
    grips     gate 5: both lists show 10 rows; a grip drag +3 -> 13 and
              remembered; then the hub rebuilt
    grips2    gate 5 (cont.): 13 again after the rebuild; -9999 -> 5; put back
    watch     the reviewers' live watch list (task-14-watch.md), a gate each
    scene     a Manny skeleton with a sword and a spear in its hands (the
              inventory's pills, Connections' chooser, every subtitle)
    picture   gate 6: hub_compact.png, every card open, the dock's width
    classic   ⋮ -> Classic look (deferred)
    classic2  the classic hub at the same width: every section open, its
              rows within the viewport and no text clipped (the classic
              watch items: the tab row, Retarget's, CoM's),
              hub_compact_classic.png; the skin asked back (deferred)
    restore   Interface animations as found; the scene left as it is (a
              disposable Maya)
    probe     a scratch file run in this module's namespace (diagnosis)
    summary   every gate recorded, per build

UI only but for `scene`. Gates go to gates_<build>.json in the output folder
($SKELDAR_VERIFY_OUT); `summary` prints them all.

Spec: docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md
"""

import json
import os
import sys
import tempfile
import time
import traceback

import maya.cmds as cmds
import maya.utils

HERE = os.path.dirname(os.path.abspath(globals().get("__file__") or "."))
OUT = (os.environ.get("SKELDAR_VERIFY_OUT")
       or os.path.join(tempfile.gettempdir(), "skeldar_hub_compact"))
PNG = os.path.join(HERE, "hub_compact.png")
PNG_CLASSIC = os.path.join(HERE, "hub_compact_classic.png")
DOCK = 510                  # the animator's dock: the scroll viewport, physical
ROW_MAX = 30                # a row's height at most, logical
LISTS = ("ueAnimBridgeList", "skeldarShareList")
GRIPS = {"ueAnimBridgeList": "ueAnimBridgeListGrip",
         "skeldarShareList": "skeldarShareListGrip"}
STATE = "state.json"

RESULTS = []


def picture_path(path, build):
    """The compact build's pictures beside this script; the build before it
    (`old`) photographs into the output folder."""
    if build == "new":
        return path
    return os.path.join(OUT, build + "_" + os.path.basename(path))


def gate(n, name, ok, detail=""):
    RESULTS.append((str(n), name, bool(ok), str(detail)))
    print("%s %4s %s%s" % ("ok  " if ok else "FAIL", n, name,
                           (" - " + str(detail)) if detail else ""))


def _save_gates(build):
    path = os.path.join(OUT, "gates_%s.json" % build)
    data = {}
    if os.path.isfile(path):
        with open(path) as handle:
            data = json.load(handle)
    for n, name, ok, detail in RESULTS:
        data[n] = [name, ok, detail]
    with open(path, "w") as handle:
        json.dump(data, handle, indent=1, sort_keys=True)


def _state(update=None):
    path = os.path.join(OUT, STATE)
    data = {}
    if os.path.isfile(path):
        with open(path) as handle:
            data = json.load(handle)
    if update:
        data.update(update)
        with open(path, "w") as handle:
            json.dump(data, handle, indent=1)
    return data


# ------------------------------------------------------------------ helpers

def hub():
    import maya_hub
    return maya_hub


def hubqt():
    import maya_hubqt
    return maya_hubqt


def hubstyle():
    import maya_hubstyle
    return maya_hubstyle


def q():
    return hubqt().qt()


def turn(n=8):
    app = q().QtWidgets.QApplication.instance()
    for _ in range(n):
        app.processEvents()
        maya.utils.processIdleEvents()
        time.sleep(0.01)


def skin():
    s = hub()._SKIN
    assert s is not None and s.alive(), "no skinned hub standing"
    return s


def scale():
    return float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)


def px(n):
    return hubstyle().px(n, scale())


def name_of(widget):
    return "%s<%s>" % (widget.objectName() or "?",
                       widget.metaObject().className())


def window():
    """The hub's floating top-level (never MayaWindow: trap 150)."""
    return hubqt().host_widget(hub().CONTROL).window()


def ui_type(widget):
    """cmds' type of a Maya control's widget ('rowLayout', 'button', ...),
    or '' for a widget of ours."""
    try:
        path = hubqt().path_of(widget)
        return cmds.objectTypeUI(path) or ""
    except Exception:                                        # noqa: BLE001
        return ""


def wrap(name, cls, layout=False):
    """Maya control `name` wrapped as `cls` (a cached QWidget wrapper of the
    same address invalidated first: trap 96), or None."""
    import maya.OpenMayaUI as omui
    Q = q()
    ptr = (omui.MQtUtil.findLayout(name) if layout
           else omui.MQtUtil.findControl(name))
    if not ptr and not layout:
        ptr = omui.MQtUtil.findLayout(name)
    if not ptr:
        return None
    widget = Q.shiboken.wrapInstance(int(ptr), cls)
    if not isinstance(widget, cls):
        Q.shiboken.invalidate(widget)
        widget = Q.shiboken.wrapInstance(int(ptr), cls)
    return widget if Q.shiboken.isValid(widget) else None


def classic_scroll():
    """The classic hub's scroll area (inside Maya's scrollLayout), found
    AFRESH on every call and never kept: a wrapper of a Maya-owned widget
    held past that widget's deletion is not "already deleted" - it reads
    freed memory (traps 135, 148). Callers hold what this answers only
    between two turns of the event loop and find it again after each.

    Maya's scrollLayout holds a QmayaScrollArea, found with `findChildren`
    on the layout's widget. A wrapper `findChildren` answers is TIED to the
    parent's wrapper: measured 2026-10-09, dropping the layout's wrapper
    marked the scroll area's dead (`isValid` False, the next call «Internal
    C++ object (QScrollArea) already deleted») - why the first version kept
    both in a module list, across turns and rebuilds. So the address is
    read while the parent's wrapper stands, the tied wrapper invalidated
    (shiboken's own bookkeeping only; the widget is untouched) and the
    scroll area wrapped afresh from that address - a wrapper of its own,
    valid as long as the caller holds it, which is never across a turn."""
    Q = q()
    widget = hubqt().find(hub().SCROLL, layout=True)
    if widget is None:
        return None
    if widget.inherits("QAbstractScrollArea"):
        return wrap(hub().SCROLL, Q.QtWidgets.QScrollArea, layout=True)
    children = widget.findChildren(Q.QtWidgets.QScrollArea)
    if not children:
        return None
    address = int(Q.shiboken.getCppPointer(children[0])[0])
    for child in children:
        Q.shiboken.invalidate(child)
    del children, widget
    area = Q.shiboken.wrapInstance(address, Q.QtWidgets.QScrollArea)
    return area if Q.shiboken.isValid(area) else None


def classic_parts():
    """`_stitch`'s finder for the classic hub: (the widget photographed, its
    scroll area) - the scroll area both, found afresh."""
    area = classic_scroll()
    if area is None:
        raise RuntimeError("no classic hub standing")
    return area, area


def skin_parts():
    """`_stitch`'s finder for the skin: (its root, its scroll area), found
    afresh (a rebuild deletes both)."""
    s = skin()
    return s.root, s.scroll


def viewport_width():
    """The scroll viewport's width (the skin's, else the classic hub's), read
    while its scroll area's wrapper stands - a viewport's wrapper is tied to
    it like a found child (`classic_scroll`) - and nothing kept."""
    if hub().is_skinned():
        return skin().scroll.viewport().width()
    area = classic_scroll()
    return None if area is None else area.viewport().width()


def fit_width(target=DOCK):
    """The floating hub's window resized until the scroll viewport is
    `target` physical px wide; the window as tall as the screen allows.
    The window and the viewport are found again after every turn of the
    event loop, never held across one (traps 135, 148)."""
    win = window()
    if win.objectName() == "MayaWindow":
        raise RuntimeError("the hub is docked - float it first (trap 150)")
    avail = win.screen().availableGeometry()        # a QRect: a copy
    height = max(600, avail.height() - 160)
    win.move(avail.x() + 80, avail.y() + 60)
    del win
    for _ in range(14):
        width = viewport_width()
        if width is None:
            turn(4)
            continue
        delta = target - width
        win = window()
        if delta == 0 and win.height() == height:
            del win
            break
        win.resize(win.width() + delta, height)
        del win
        turn(6)
    return viewport_width()


def open_every_card():
    h = hub()
    for key in list(skin().cards):
        h.expand(key)
    turn(10)


def deaf(on=True):
    """The real mouse kept off the hub for the run (verify_hub_glow's lesson:
    the disposable Maya is on the animator's screen and they use it - trap
    100; here every card but two came back collapsed between two sends and
    the animation list's source changed): Qt's childAt skips a root that is
    transparent for mouse events; this script calls the widgets directly."""
    s = hub()._SKIN
    if s is not None and s.alive():
        s.root.setAttribute(q().QtCore.Qt.WA_TransparentForMouseEvents, on)


def deaf_classic(on=True):
    """The classic hub deaf too, while it is measured and photographed: a
    click on «Switch to the new look» (or a section's header) in the middle
    of the stitch would delete what is being scrolled. The attribute goes on
    Maya's scrollLayout widget - every control of the classic hub is under
    it, and Qt keeps the mouse from a widget's children too; the widget dies
    with the classic hub, so the skin built after it hears again. Found
    afresh and dropped at once."""
    widget = hubqt().find(hub().SCROLL, layout=True)
    if widget is not None:
        widget.setAttribute(q().QtCore.Qt.WA_TransparentForMouseEvents, on)
        return True
    return False


def _classic_deaf():
    """Whether the classic hub is deaf now: the attribute on its scrollLayout
    AND Qt's own hit test (`childAt` on the hub's window, the routing a real
    click takes) over «Switch to the new look» answering nothing of the
    classic hub. Measured both ways 2026-10-09: hearing it answered that
    button, deaf the workspaceControl around it. (`QApplication.widgetAt`
    answered None for both - no use as a control.) Read, not kept."""
    Q = q()
    widget = hubqt().find(hub().SCROLL, layout=True)
    if widget is None or not widget.testAttribute(
            Q.QtCore.Qt.WA_TransparentForMouseEvents):
        return False
    buttons = [b for b in widget.findChildren(Q.QtWidgets.QAbstractButton)
               if "new look" in b.text() and b.isVisible()]
    if not buttons:
        return False
    centre = buttons[0].mapToGlobal(buttons[0].rect().center())
    top = window()
    hit = top.childAt(top.mapFromGlobal(centre))
    return hit is None or not widget.isAncestorOf(hit)


def prepare():
    """Before a measuring phase: the hub deaf, animations off, every card
    open, the dock's width - whatever happened between two sends."""
    h = hub()
    h.set_animations(False)
    deaf(True)
    if h.is_skinned():
        open_every_card()
    width = fit_width()
    turn(10)
    if width != DOCK:
        print("WARNING: the viewport is %s, not %d" % (width, DOCK))
    return width


def visible_in(widget, top):
    return (not widget.isWindow() and widget.isVisibleTo(top)
            and widget.width() > 0 and widget.height() > 0)


def rect_in(widget, top):
    Q = q()
    pos = widget.mapTo(top, Q.QtCore.QPoint(0, 0))
    return pos.x(), pos.y(), widget.width(), widget.height()


def builder_column(card):
    """The builder's columnLayout inside a card's body."""
    Q = q()
    for child in card.body.children():
        if isinstance(child, Q.QtWidgets.QWidget) and not child.isWindow():
            return child
    return None


# ------------------------------------------------------------------- phases

def phase_install(build, source):
    source = (source or "").replace("\\", "/").rstrip("/")
    if not os.path.isfile(os.path.join(source, "install.py")):
        raise RuntimeError("no install.py in %r" % source)
    sys.path[:] = [p for p in sys.path
                   if p.replace("\\", "/").rstrip("/") != source]
    sys.path.insert(0, source)
    sys.modules.pop("install", None)
    import install
    dest = install.install(quiet=True).replace("\\", "/")
    sys.path[:] = [p for p in sys.path
                   if p.replace("\\", "/").rstrip("/") != source]
    sys.modules.pop("install", None)
    gone = []
    for name, module in list(sys.modules.items()):
        path = (getattr(module, "__file__", None) or "").replace("\\", "/")
        if path.startswith(source + "/") or path.startswith(dest + "/"):
            del sys.modules[name]
            gone.append(name)
    if dest in sys.path:
        sys.path.remove(dest)
    sys.path.insert(0, dest)
    print("installed", source, "->", dest, "; purged", len(gone))
    h = hub()
    print("maya_hub from", h.__file__)
    h.show()
    turn(10)
    deaf(True)          # at once: the animator tries a fresh hub (trap 100)
    print("skinned", h.is_skinned(), "open", h.is_open())


def phase_open(build):
    """The hub of the copy installed earlier (a Maya restarted on the same
    scratch MAYA_APP_DIR)."""
    dest = os.path.join(cmds.internalVar(userAppDir=True), "scripts",
                        "SkeldarAnim").replace("\\", "/")
    if dest not in sys.path:
        sys.path.insert(0, dest)
    h = hub()
    print("maya_hub from", h.__file__)
    h.show()
    turn(10)
    deaf(True)


def phase_dock(build):
    """The hub back in the dock when somebody switched the edge panel on in
    the disposable Maya between two sends (measured twice: the animator
    tries a new Maya's hub as soon as it appears - trap 100). Deferred, as
    the ⋮ switch is; `size` follows in the next send."""
    h = hub()
    print("edge on:", h.edge_on())
    if getattr(h, "edge_on", lambda: False)():
        h.set_edge(False)


def phase_size(build):
    h = hub()
    if not cmds.workspaceControl(h.CONTROL, exists=True):
        h.show()
        turn(10)
    deaf(True)
    cmds.workspaceControl(h.CONTROL, edit=True, floating=True)
    turn(8)
    import maya_hubmotion
    state = _state()
    if "animations" not in state:
        _state({"animations": bool(maya_hubmotion.enabled())})
    width = prepare()
    print("viewport", width, "window", window().width(), "x",
          window().height(), "scale", scale())


def card_heights():
    s = skin()
    closed = [k for k, c in s.cards.items()
              if c.collapsed() or c.body.isHidden()]
    heights = dict((k, c.frame.height()) for k, c in s.cards.items())
    Q = q()
    used = 0
    for child in s.content.children():
        if isinstance(child, Q.QtWidgets.QWidget) and child.isVisible():
            used = max(used, child.geometry().bottom() + 1)
    over = s.root.height() - s.scroll.height()
    return closed, heights, used, over


def phase_heights(build):
    prepare()
    turn(6)
    closed, heights, used, over = card_heights()
    vp = viewport_width()
    data = {"build": build, "viewport": vp, "scale": scale(),
            "cards": heights, "content": used, "above_scroll": over,
            "closed": closed}
    with open(os.path.join(OUT, "heights_%s.json" % build), "w") as handle:
        json.dump(data, handle, indent=1, sort_keys=True)
    print(json.dumps(data, indent=1, sort_keys=True))
    gate("2a", "%s: every card open, the dock's viewport" % build,
         not closed and vp == DOCK, "closed %s, viewport %d" % (closed, vp))
    compare()


def compare():
    paths = [os.path.join(OUT, "heights_%s.json" % b) for b in ("old", "new")]
    if not all(os.path.isfile(p) for p in paths):
        print("(gate 2 waits for both builds' heights)")
        return
    old, new = [json.load(open(p)) for p in paths]
    rows, taller = [], []
    for key in new["cards"]:
        a, b = old["cards"].get(key), new["cards"][key]
        rows.append("%s %s -> %s" % (key, a, b))
        if a is not None and b > a:
            taller.append(key)
    total_old = old["content"] + old["above_scroll"]
    total_new = new["content"] + new["above_scroll"]
    cut = 1.0 - new["content"] / float(old["content"])
    gate(2, "every card shorter or equal; the content at least 35 % shorter",
         not taller and cut >= 0.35 and old["viewport"] == new["viewport"],
         "%s | content %d -> %d (%.1f %% shorter), with the header %d -> %d;"
         " taller: %s" % ("; ".join(rows), old["content"], new["content"],
                          cut * 100, total_old, total_new, taller))


def _text_need(widget):
    """The width a button / label / chip needs to show its text unclipped
    (the stylesheet's padding, the icon), or None for a widget whose text
    is not ours to judge (wrapping, elided by design, empty)."""
    Q = q()
    W = Q.QtWidgets
    text = ""
    if isinstance(widget, W.QAbstractButton):
        text = widget.text()
    elif isinstance(widget, W.QLabel):
        if widget.wordWrap():
            return None
        policy = widget.sizePolicy().horizontalPolicy()
        if policy == W.QSizePolicy.Ignored:
            return None                  # a subtitle: clipped by design
        text = widget.text()
    else:
        return None
    if not text or not text.strip():
        return None
    return widget.sizeHint().width()


def phase_cards(build):
    """Gate 1. Each step a function of its own: the widgets it walks are its
    locals and die with it, before the next turn of the event loop (traps
    135, 148 - never a wrapper held across one)."""
    prepare()
    _cards_fit()
    _repaint_headers()
    turn(6)
    lines, bad = _subtitle_lines()
    #  and one made too long on purpose (the CoM line, put back after): the
    #  first build drew it cut mid-letter under the chevron
    name = "skeldarComSubtitle"
    was = cmds.text(name, query=True, label=True)
    long_text = ("no character - select a control, a bone or a CoM handle "
                 "of the character whose centre of mass you want")
    cmds.text(name, edit=True, label=long_text)
    _repaint_headers("com")
    turn(6)
    elided, tip = _elided_and_tip(name)
    cmds.text(name, edit=True, label=was)
    turn(4)
    lines.append("a long CoM line: elided %s, tooltip whole %s" % (
        elided, tip == long_text))
    if not (elided and tip == long_text):
        bad.append("the long CoM line: elided %s, tooltip %r" % (elided, tip))
    gate("1e", "a header line too long for its card is elided, its tooltip "
         "the whole text", not bad and lines, "; ".join(bad or lines))


def _repaint_headers(key=None):
    """Every card's header (or `key`'s) asked to paint again."""
    for each, card in skin().cards.items():
        if key is None or each == key:
            card.header.update()


def _elided_and_tip(name):
    label = hubqt().find(name)
    return bool(label.property("skElided")), label.toolTip()


def _subtitle_lines():
    """The moved subtitles: elided at the card's width, the whole text their
    tooltip (the spec); every one painted since this send's layout."""
    W = q().QtWidgets
    lines, bad = [], []
    for key, card in skin().cards.items():
        for label in card.subtitle_slot.findChildren(W.QWidget):
            #  a property: Maya's labels come back as QWidget wrappers
            text = label.property("text") or ""
            if not text or not label.isVisible():
                continue
            long_ = label.fontMetrics().horizontalAdvance(text) > \
                label.contentsRect().width()
            elided = bool(label.property("skElided"))
            lines.append("%s %s%s" % (key, "elided" if elided else "fits",
                                      "" if long_ == elided else " WRONG"))
            if long_ != elided or (long_ and label.toolTip() != text):
                bad.append("%s: %r long %s elided %s tip %r" % (
                    key, text, long_, elided, label.toolTip()))
    return lines, bad


def _cards_fit():
    """Gates 1a-1d, no turn of the event loop inside."""
    Q = q()
    W = Q.QtWidgets
    s = skin()
    vp = viewport_width()
    minimum = s.content.minimumSizeHint().width()
    gate("1a", "the content's minimum width within the viewport",
         minimum <= vp, "minimum %d, viewport %d" % (minimum, vp))

    over, tall, clipped = [], [], []
    limit = px(ROW_MAX)
    for key, card in s.cards.items():
        frame = card.frame
        fw = frame.width()
        for w in frame.findChildren(W.QWidget):
            if not visible_in(w, frame):
                continue
            x, _y, ww, _h = rect_in(w, frame)
            if x + ww > fw:
                over.append("%s: %s right %d > %d" % (key, name_of(w),
                                                      x + ww, fw))
            need = _text_need(w)
            if need is not None and ww + 1 < need:
                clipped.append("%s: %s '%s' %d < %d" % (
                    key, name_of(w), w.text()[:24], ww, need))
        column = builder_column(card)
        if column is None:
            continue
        for row in rows_of(column, card):
            if row.height() > limit:
                tall.append("%s: %s %s %d > %d" % (key, name_of(row),
                                                   ui_type(row), row.height(),
                                                   limit))
    gate("1b", "no widget past its card's right edge", not over,
         "; ".join(over[:12]) + (" ... %d" % len(over) if len(over) > 12
                                 else ""))
    gate("1c", "every row within %d logical (%d px), lists and tiles aside"
         % (ROW_MAX, limit), not tall, "; ".join(tall))
    gate("1d", "no button's or label's text clipped", not clipped,
         "; ".join(clipped[:16]))


#  Rows that are not rows: the lists, the tiles' placeholders (a grid of
#  ours laid over them), the containers whose children are the rows.
EXEMPT = ("textScrollList",)
TILES = ("mayaSceneSetupPortraits", "mayaSceneSetupInventory",
         "mayaSceneSetupArmorTiles")
CONTAINERS = ("columnLayout", "flowLayout")


def rows_of(column, card):
    """The visible rows of a builder's column, recursing into the columns and
    flow layouts it holds (the Connect block, the Inventory tabs, Studio's
    chips): each row a widget whose height a compact row must keep."""
    Q = q()
    out = []
    for child in column.children():
        if not isinstance(child, Q.QtWidgets.QWidget):
            continue
        if not visible_in(child, card.frame):
            continue
        kind = ui_type(child)
        name = child.objectName()
        if kind in EXEMPT or name in TILES:
            continue
        if kind in CONTAINERS:
            out.extend(rows_of(child, card))
            continue
        if not kind:
            continue                     # a widget of ours (a grip, a cover)
        out.append(child)
    return out


# The status writers, per card (the spec's list): (card, module, call)
WRITERS = (
    ("characters", "maya_scenesetup.window",
     lambda m, t: m._status(t, m._CHARACTER_STATUS)),
    ("characters", "maya_uebridge.window", lambda m, t: m._status(t)),
    ("weapons", "maya_scenesetup.window", lambda m, t: m._status(t)),
    ("weapons", "maya_scenesetup.armorpanel", lambda m, t: m._status(t)),
    ("connections", "maya_scenesetup.connections", lambda m, t: m._status(t)),
    ("shared", "maya_share", lambda m, t: m._status(t)),
    ("retarget", "maya_rig_retarget", lambda m, t: m._show(t)),
    ("graphoverlay", "maya_graphoverlay.mode", lambda m, t: m._show(t)),
    ("com", "maya_com.panel", lambda m, t: m.status(t)),
    ("studio", "maya_vpstudio", lambda m, t: m._status(t)),
    ("colour", "maya_colour", lambda m, t: m._status(t)),
    ("update", "maya_update", lambda m, t: m._status(t)),
)


def _module(dotted):
    module = __import__(dotted)
    for part in dotted.split(".")[1:]:
        module = getattr(module, part)
    return module


def _image_bytes(pixmap):
    Q = q()
    image = pixmap.toImage().convertToFormat(
        Q.QtGui.QImage.Format_ARGB32)
    return bytes(image.constBits())[:image.bytesPerLine() * image.height()]


def phase_relay(build):
    prepare()
    bad, seen = [], []
    for n, (key, dotted, call) in enumerate(WRITERS):
        before = _heights_now()
        text = "verify relay %d: %s via %s" % (n, key, dotted)
        try:
            call(_module(dotted), text)
        except Exception as error:                           # noqa: BLE001
            bad.append("%s: %s raised %r" % (key, dotted, error))
            continue
        turn(4)
        ok, problem = _relay_read(key, dotted, text, before)
        seen.append("%s:%s" % (key, "ok" if ok else "BAD"))
        if not ok:
            bad.append(problem)
    skin().say("")
    turn(4)
    gate(3, "each writer's status on the hub's line with its card's icon, "
         "no card resized", not bad, "; ".join(bad) or ", ".join(seen))


def _heights_now():
    """Every card's height, as values."""
    return dict((k, c.frame.height()) for k, c in skin().cards.items())


def _relay_read(key, dotted, text, before):
    """After a writer's turn: the hub's line, its icon, the cards' heights -
    read from the skin found afresh. (ok, what was wrong)."""
    s = skin()
    card = s.cards[key]
    shown = s.message_text.text()
    icon_ok = (s._message_source == key and s.message_icon.isVisible()
               and _image_bytes(s.message_icon.pixmap()) == _image_bytes(
                   hubqt().pixmap(card.icon_name, card.colour, px(14))))
    after = _heights_now()
    moved = dict((k, (before[k], after[k])) for k in after
                 if after[k] != before[k])
    ok = shown == text and s.message.isVisible() and icon_ok and not moved
    return ok, ("%s via %s: shown %r, source %r, icon %s, cards moved %s" % (
        key, dotted, shown, s._message_source, icon_ok, moved))


HINTS = (
    ("retarget", "maya_rig_retarget", "PANEL_HINT"),
    ("graphoverlay", "maya_graphoverlay.mode", "PANEL_HINT"),
    ("poses", "maya_poselib.window", "NOTE"),
    ("studio", None, "lighting, shadows, AO and motion blur, live"),
    ("colour", None, "paints the selection, else the connected character"),
)


def phase_notes(build):
    prepare()
    Q = q()
    s = skin()
    bad = []
    for key, dotted, attr in HINTS:
        hint = getattr(_module(dotted), attr) if dotted else attr
        card = s.cards[key]
        tip = card.header.toolTip()
        if hint not in tip:
            bad.append("%s: header tooltip %r lacks %r" % (key, tip, hint))
        for label in card.body.findChildren(Q.QtWidgets.QLabel):
            if label.text() == hint and label.isVisibleTo(card.frame):
                bad.append("%s: the note still shows in the body" % key)
    gate(4, "the static hints are their cards' header tooltips, none shown",
         not bad, "; ".join(bad))


def grip_of(list_name):
    Q = q()
    holder = hubqt().find(GRIPS[list_name])
    if holder is None:
        return None
    return holder.findChild(Q.QtWidgets.QWidget, GRIPS[list_name] + "_grip")


def ensure_rows(list_name, n=45):
    """The list holds rows to measure (a fresh Maya's Shared list is empty):
    placeholder rows appended, their count answered (0 when it had some)."""
    have = cmds.textScrollList(list_name, query=True, numberOfItems=True)
    if have:
        return 0
    cmds.textScrollList(list_name, edit=True,
                        append=["verify row %02d" % i for i in range(n)])
    turn(4)
    return n


def drop_rows(list_name, added):
    """The placeholder rows `ensure_rows` put in, taken out again (the list's
    height stays at the rows it was sized for)."""
    if added:
        cmds.textScrollList(list_name, edit=True, removeAll=True)
        turn(4)


def shown_rows(list_name):
    """(full rows the list's viewport shows, its row px, viewport px)."""
    lw = hubqt().list_widget(list_name)
    row = lw.sizeHintForRow(0) if lw.count() else 0
    vh = lw.viewport().height()
    return (vh // row if row else 0), row, vh


def _grip_drag(list_name, dy):
    """A synthetic drag of the list's grip by `dy` physical px: press, move,
    release, the grip found here and dropped with this function - before the
    caller turns the event loop."""
    grip = grip_of(list_name)
    grip.press(1000)
    grip.drag(1000 + dy)
    grip.release()


def phase_grips(build):
    prepare()
    h = hubstyle()
    stats, bad = [], []
    added = {}
    for name in LISTS:
        var = h.LIST_VAR.format(name)
        saved = (cmds.optionVar(query=var) if cmds.optionVar(exists=var)
                 else None)
        _state({"listvar_" + name: saved})
        added[name] = ensure_rows(name)
        rows, row, vh = shown_rows(name)
        stats.append("%s: %d rows (row %d px, viewport %d)" % (name, rows,
                                                               row, vh))
        if rows != h.LIST_ROWS:
            bad.append("%s shows %d rows" % (name, rows))
    gate("5a", "both lists show 10 rows", not bad, "; ".join(stats + bad))

    bad = []
    name = LISTS[0]
    if grip_of(name) is None:
        gate("5b", "a grip drag +3 rows -> 13, remembered", False, "no grip")
        return
    _rows, row, _vh = shown_rows(name)
    _grip_drag(name, 3 * row)
    turn(6)
    rows, row, vh = shown_rows(name)
    var = h.LIST_VAR.format(name)
    remembered = cmds.optionVar(query=var) if cmds.optionVar(exists=var) \
        else None
    gate("5b", "a grip drag +3 rows -> 13, remembered",
         grip_of(name).rows == 13 and rows == 13 and remembered == 13,
         "grip %s, shown %d (row %d, viewport %d), optionVar %s" % (
             grip_of(name).rows, rows, row, vh, remembered))
    hub().rebuild()
    turn(6)
    print("rebuilt; grips2 measures in the next send")


def phase_grips2(build):
    h = hubstyle()
    name = LISTS[0]
    turn(6)
    ensure_rows(name)
    rows, row, vh = shown_rows(name)
    gate("5c", "the rebuilt hub opens the list at 13 rows",
         rows == 13 and grip_of(name).rows == 13,
         "shown %d (row %d, viewport %d), grip %s" % (rows, row, vh,
                                                      grip_of(name).rows))
    _grip_drag(name, -9999)
    turn(6)
    rows, row, vh = shown_rows(name)
    var = h.LIST_VAR.format(name)
    remembered = cmds.optionVar(query=var)
    gate("5d", "a drag to -9999 -> 5 rows (the minimum), remembered",
         rows == 5 and grip_of(name).rows == 5 and remembered == 5,
         "shown %d, grip %s, optionVar %s" % (rows, grip_of(name).rows,
                                              remembered))
    #  put back: the remembered rows as found, the lists' placeholder rows
    state = _state()
    for list_name in LISTS:
        saved = state.get("listvar_" + list_name)
        var = h.LIST_VAR.format(list_name)
        if saved is None:
            if cmds.optionVar(exists=var):
                cmds.optionVar(remove=var)
        else:
            cmds.optionVar(intValue=(var, int(saved)))
    hub().rebuild()
    turn(6)
    print("put back; the hub rebuilt at the remembered rows")


# ---------------------------------------------------------------- the watch

def _segment_rows(card_key):
    """Every segments track in a card: (track, cover, buttons)."""
    Q = q()
    s = skin()
    out = []
    for cover in s.cards[card_key].frame.findChildren(Q.QtWidgets.QWidget):
        name = cover.objectName()
        if name.endswith("_skinSegments"):
            track = cover.parentWidget()
            buttons = cover.findChildren(Q.QtWidgets.QAbstractButton)
            out.append((track, cover, buttons))
    return out


def _segments_report(card_key):
    """The card's segment tracks, read from the skin found afresh; answers
    values only."""
    top = skin().cards[card_key].frame
    bad, info = [], []
    for track, cover, buttons in _segment_rows(card_key):
        #  judged by its ROW: Maya hides a track it gives no width (a
        #  0-wide track read as "not visible", so a skipped one hid the
        #  defect); only a row that is itself unmanaged (Connections'
        #  chooser while one weapon stands) is not shown at all
        row = track.parentWidget()
        if row is None or not row.isVisibleTo(top):
            continue
        tr = track.rect()
        same = cover.geometry() == tr
        need = sum(b.sizeHint().width() for b in buttons)
        narrow = [name_of(b) for b in buttons
                  if b.width() + 1 < b.sizeHint().width()]
        info.append("%s %dx%d (%d buttons, need %d)" % (
            track.objectName(), tr.width(), tr.height(), len(buttons), need))
        if not same or narrow or tr.width() <= 0:
            bad.append("%s: cover %s track %s, narrow %s" % (
                track.objectName(), cover.geometry(), tr, narrow))
    return bad, info


def phase_watch(build):
    """The reviewers' watch list (task-14-watch.md). Each item a function of
    its own: the widgets it reads are its locals, found after the last turn
    of the event loop and dropped with it (traps 135, 148)."""
    prepare()
    _watch_lists()
    _watch_inventory()
    # Task 6: the nested segments in Animation Setup's 4- and 5-column rows
    bad, info = _segments_report("characters")
    gate("W6", "Animation Setup's segments stand over their tracks, every "
         "segment its text's width", not bad, "; ".join(info + bad))
    _watch_connections()
    _watch_look()


def _list_state(name):
    """List `name` as values: (rows, its row px - measured on a throwaway
    list when empty since 2026-10-09 -, the font's old guess, height)."""
    import maya_hubqt
    lw = maya_hubqt.list_widget(name)
    count = lw.count()
    real = lw.sizeHintForRow(0) if count else None
    return (count, real if count else maya_hubqt.list_row_px(name),
            lw.fontMetrics().lineSpacing() + 4, lw.height())


def _watch_lists():
    """Task 3: the lists' 10 rows from a real row, not the fallback; and an
    empty list already at the height its rows will give it."""
    info, bad = [], []
    for name in LISTS:
        count, empty_row, guess, height_empty = _list_state(name)
        empty = not count
        #  an empty list's first rows arriving (a refresh after the build)
        added = ensure_rows(name)
        turn(4)
        count, real, _guess, height_filled = _list_state(name)
        info.append("%s: %s at the build%s" % (
            name, "empty" if empty else "filled",
            ", %d rows arrived" % added if added else ""))
        rows, _row, _vh = shown_rows(name)
        info.append("%s: empty row %s (the old guess %d), real row %s, "
                    "height empty %d / filled %d, shows %d" % (
                        name, empty_row if empty else None, guess, real,
                        height_empty, height_filled, rows))
        if count and rows != hubstyle().LIST_ROWS:
            bad.append("%s shows %d rows" % (name, rows))
        if empty and (empty_row != real or height_empty != height_filled):
            bad.append("%s jumped when its first rows came" % name)
        drop_rows(name, added)
    gate("W3", "the 10 rows hold once the list fills, and an empty list "
         "stands at that height already", not bad, "; ".join(info + bad))


def _watch_inventory():
    """Task 5: the hand rows, the tiles' names, the pill. No turn inside."""
    Q = q()
    W = Q.QtWidgets
    s = skin()
    k = scale()
    import maya_invlook as look
    panel = s.cards["weapons"].frame.findChild(W.QWidget,
                                               "skeldarInventoryPanel")
    if panel is None:
        for w in s.cards["weapons"].frame.findChildren(W.QWidget):
            if w.metaObject().className() == "InventoryPanel":
                panel = w
    detail, bad = [], []
    if panel is not None:
        rects = panel.rects()
        row_h = rects["row_R_tx"][3]
        fm = Q.QtGui.QFontMetrics(panel.field_font)
        fields = [f for f in panel.fields.values()]
        field = fields[0]
        detail.append("row %d px, font %d px (lineSpacing %d), field %dx%d"
                      % (row_h, panel.field_font.pixelSize(), fm.lineSpacing(),
                         field.width(), field.height()))
        #  the value's glyphs (digits, sign, point - no descenders), not the
        #  font's line box: a 19 px line box in an 18 px field draws its
        #  digits whole (photographed)
        ink = fm.tightBoundingRect("-0123456789.").height()
        detail.append("the values' ink %d px" % ink)
        if ink > field.height():
            bad.append("the values' glyphs %d are taller than their field %d"
                       % (ink, field.height()))
        labels_w = max(fm.horizontalAdvance(c) for c in look.CHANNELS)
        if labels_w > panel.label_w.get("R", 0):
            bad.append("channel label %d > column %d" % (labels_w,
                                                         panel.label_w["R"]))
        # the values: the widest one the mockup shows must fit its field
        need = fm.horizontalAdvance("-179.508") + int(6 * k)
        if field.width() < need:
            bad.append("a value field %d < %d for '-179.508'" % (
                field.width(), need))
        tiles = rects["tiles"]
        tile = tiles[0]
        nfont = Q.QtGui.QFont(panel.font())
        nfont.setPixelSize(int(round(10 * k)))
        nfm = Q.QtGui.QFontMetrics(nfont)
        elided = []
        import maya_charlook as charlook
        nx, ny, nw, nh = charlook.name_rect(tile, k)
        for key in panel.keys:
            label = panel._label(key)
            if nfm.horizontalAdvance(label) > int(nw - 6 * k):
                elided.append(label)
        pfont = Q.QtGui.QFont(panel.font())
        pfont.setPixelSize(int(round(10.5 * k)))
        pfont.setBold(True)
        pill_need = Q.QtGui.QFontMetrics(pfont).horizontalAdvance(
            look.WORN_TEXT)
        pill_w = tile[2] - 2 * int(4 * k)
        detail.append("tile %dx%d, names elided: %s; pill '%s' needs %d of "
                      "%d" % (tile[2], tile[3], elided or "none",
                              look.WORN_TEXT, pill_need, pill_w))
        if pill_need > pill_w:
            bad.append("the pill's text %d > its %d" % (pill_need, pill_w))
        if nh < nfm.height():
            bad.append("the name strip %d < its font %d" % (nh, nfm.height()))
    else:
        bad.append("no inventory panel found")
    gate("W5", "the hand rows, the tiles' names and the pill fit", not bad,
         "; ".join(detail + bad))


def _arm_widths(cx):
    """Connections' Arm R / Arm L tracks' widths, as values."""
    arm = {}
    for side in ("R", "L"):
        box = hubqt().find(cx.fkik_box(side, "FK"))
        if box is not None and box.parentWidget() is not None:
            arm[side] = box.parentWidget().parentWidget().width()
    return arm


def _chooser_shown(cx):
    row = hubqt().find(cx.CHOOSER_ROW, layout=True)
    return row is not None and row.isVisible()


def _watch_connections():
    """Task 8: Connections - the chooser row (shown for two weapons), the Arm
    row's halves, BakeAcross and the labels unclipped (gate 1d covers them).
    Every widget read after the chooser's turn, by the helpers."""
    from maya_scenesetup import connections as cx
    weapons = [n for n in cmds.ls(type="transform", long=True) or []
               if cmds.attributeQuery("mayaWeapon", node=n, exists=True)]
    shown_chooser = False
    if len(weapons) >= 2:
        cx._set_chooser(weapons[:2], weapons[0])
        turn(8)
        shown_chooser = True
    bad, info = _segments_report("connections")
    arm = _arm_widths(cx)
    ratio = (min(arm.values()) / float(max(arm.values()))
             if len(arm) == 2 and max(arm.values()) else 0.0)
    info.append("Arm R / Arm L tracks %s (ratio %.2f); chooser shown: %s"
                % (arm, ratio, shown_chooser))
    if ratio < 0.75:
        bad.append("the two arms' [FK | IK] are lopsided: %s" % arm)
    if shown_chooser:
        if not _chooser_shown(cx):
            bad.append("the chooser row is not shown for two weapons")
        cx._set_chooser([], None)
        turn(4)
    gate("W8", "Connections' segments over their tracks, nothing narrow, "
         "the arms' halves about equal, the chooser row's segments shown",
         not bad and shown_chooser, "; ".join(info + bad))


def _watch_look():
    """Task 9: Studio's chips flow inside their layout; the 8 swatches. No
    turn inside."""
    Q = q()
    W = Q.QtWidgets
    s = skin()
    bad, info = [], []
    frame = s.cards["studio"].frame
    flows = [w for w in frame.findChildren(W.QWidget)
             if ui_type(w) == "flowLayout"]
    for flow in flows:
        fr = flow.rect()
        chips = [c for c in flow.children()
                 if isinstance(c, W.QWidget) and c.isVisibleTo(frame)]
        outside = [name_of(c) for c in chips
                   if not fr.contains(c.geometry())]
        lines = sorted(set(c.geometry().y() for c in chips))
        info.append("flow %dx%d, %d chips on %d lines" % (
            fr.width(), fr.height(), len(chips), len(lines)))
        if outside:
            bad.append("chips outside the flow: %s" % outside)
    frame = s.cards["colour"].frame
    swatches = [w for w in frame.findChildren(W.QAbstractButton)
                if w.property("skRole") == "swatch"
                and w.isVisibleTo(frame)]
    ys = sorted(set(w.mapTo(frame, Q.QtCore.QPoint(0, 0)).y()
                    for w in swatches))
    info.append("%d swatches on %d row(s), widths %s" % (
        len(swatches), len(ys), sorted(set(w.width() for w in swatches))))
    if len(swatches) >= 8 and len(ys) != 1:
        bad.append("the swatches stand on %d rows" % len(ys))
    gate("W9", "Studio's chips inside their flow; Colour's eight swatches "
         "on one row", not bad and flows, "; ".join(info + bad))


# ------------------------------------------------------------------ scene

def phase_scene(build):
    from maya_scenesetup import catalog, character, window as sw
    entry = next(c for c in catalog.CHARACTERS if c.key == "Manny")
    print(character.add_character(entry))
    turn(6)
    sw.select_hand("R")
    sw.select_weapon("LongSword_02")
    sw.add_weapon()
    turn(4)
    sw.select_hand("L")
    sw.select_weapon("Spear_01")
    sw.add_weapon()
    turn(4)
    sw.select_hand("R")
    sw.select_weapon("LongSword_02")
    try:
        from maya_scenesetup import connections
        connections.refresh()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    turn(8)
    print("scene: a Manny skeleton holding a sword and a spear")


# ---------------------------------------------------------------- pictures

def _capture(window_id):
    """DWM's copy of the top-level window `window_id` (its HWND, an int) as
    a QImage (PrintWindow, PW_RENDERFULLCONTENT) and its window rect's
    origin. An int, not the window's wrapper: PrintWindow calls into the
    window on this thread, and nothing Maya-owned is held over it."""
    import ctypes
    from ctypes import wintypes as wt
    Q = q()
    user32, gdi = ctypes.windll.user32, ctypes.windll.gdi32
    hwnd = wt.HWND(int(window_id))
    rect = wt.RECT()
    user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                    ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                    ("biSizeImage", wt.DWORD),
                    ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]

    user32.GetDC.argtypes = [wt.HWND]
    user32.GetDC.restype = wt.HDC
    user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
    user32.PrintWindow.argtypes = [wt.HWND, wt.HDC, wt.UINT]
    user32.PrintWindow.restype = wt.BOOL
    gdi.CreateCompatibleDC.argtypes = [wt.HDC]
    gdi.CreateCompatibleDC.restype = wt.HDC
    gdi.CreateDIBSection.argtypes = [wt.HDC, ctypes.c_void_p, wt.UINT,
                                     ctypes.POINTER(ctypes.c_void_p),
                                     wt.HANDLE, wt.DWORD]
    gdi.CreateDIBSection.restype = wt.HBITMAP
    gdi.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
    gdi.SelectObject.restype = wt.HGDIOBJ
    gdi.DeleteObject.argtypes = [wt.HGDIOBJ]
    gdi.DeleteDC.argtypes = [wt.HDC]
    header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), width,
                              -height, 1, 32, 0, 0, 0, 0, 0, 0)
    screen = user32.GetDC(None)
    dc = gdi.CreateCompatibleDC(screen)
    bits = ctypes.c_void_p()
    bitmap = gdi.CreateDIBSection(dc, ctypes.byref(header), 0,
                                  ctypes.byref(bits), None, 0)
    old = gdi.SelectObject(dc, bitmap)
    try:
        if not user32.PrintWindow(hwnd, dc, 2):          # PW_RENDERFULLCONTENT
            return None, None
        data = ctypes.string_at(bits, width * height * 4)
    finally:
        gdi.SelectObject(dc, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(dc)
        user32.ReleaseDC(None, screen)
    image = Q.QtGui.QImage(data, width, height, width * 4,
                           Q.QtGui.QImage.Format_RGB32).copy()
    return image, Q.QtCore.QPoint(rect.left, rect.top)


def _scroll_to(find, value):
    """The scroll area `find` answers scrolled to `value`; its wrappers
    dropped before the caller turns the event loop."""
    _top, area = find()
    area.verticalScrollBar().setValue(value)


def _stitch(find, path):
    """A tall picture of the hub with its scroll area scrolled through: the
    part above the scroll once, then the viewport slice by slice. Saved to
    `path`; its size answered.

    `find` answers (the widget photographed, its scroll area) and is asked
    AGAIN after every turn of the event loop: nothing Maya-owned - the
    classic hub's scroll area, the floating window - is held across one
    (the review of 2026-10-09; traps 135, 148). Between two turns only
    values are kept: the geometry as ints and QPoints, the window as its
    HWND."""
    Q = q()
    zero = Q.QtCore.QPoint(0, 0)
    _scroll_to(find, 0)
    turn(10)
    top, area = find()
    vp = area.viewport()
    vtop = vp.mapToGlobal(zero)
    origin = top.mapToGlobal(zero)
    width = top.width()
    above = vtop.y() - origin.y()
    view_h = vp.height()
    total = above + area.verticalScrollBar().maximum() + view_h
    below = origin.y() + top.height() - (vtop.y() + view_h)
    del top, area, vp
    canvas = Q.QtGui.QImage(width, total + max(0, below),
                            Q.QtGui.QImage.Format_RGB32)
    canvas.fill(Q.QtGui.QColor("#1f2023"))
    painter = Q.QtGui.QPainter(canvas)
    value = 0
    first = True
    try:
        while True:
            _scroll_to(find, value)
            turn(10)
            top, area = find()
            bar = area.verticalScrollBar()
            got, maximum = bar.value(), bar.maximum()
            origin = top.mapToGlobal(zero)      # the window may have moved
            window_id = int(top.window().winId())
            del top, area, bar
            image, at = _capture(window_id)
            if image is None:
                raise RuntimeError("PrintWindow failed")
            ox, oy = origin.x() - at.x(), origin.y() - at.y()
            if first:
                painter.drawImage(0, 0, image.copy(ox, oy, width, above))
                first = False
            painter.drawImage(0, above + got,
                              image.copy(ox, oy + above, width, view_h))
            if got >= maximum:
                if below > 0:
                    painter.drawImage(0, above + got + view_h, image.copy(
                        ox, oy + above + view_h, width, below))
                break
            value = got + view_h - 40
    finally:
        painter.end()
    _scroll_to(find, 0)
    canvas.save(path)
    return canvas.width(), canvas.height()


def phase_picture(build):
    prepare()
    skin().say("")
    turn(6)
    path = picture_path(PNG, build)
    size = _stitch(skin_parts, path)
    closed, _heights, used, _over = card_heights()
    gate(6, "the picture: every card open at the dock's width",
         os.path.isfile(path) and not closed and viewport_width() == DOCK,
         "%s %dx%d (content %d)" % (path, size[0], size[1], used))


def phase_classic(build):
    hub().set_classic(True)
    print("Classic look asked (deferred); classic2 measures it")


def _classic_texts():
    """The classic hub's texts against their widgets (gate C3): a button's,
    a segment's or a label's words wider than its contents, a check box
    asking more than it has. And the three classic rows the reviewers asked
    to see (task-14-watch.md): each one's right edge against its section's.
    Answers (texts examined, clipped, the rows)."""
    Q = q()
    W = Q.QtWidgets
    h = hub()
    examined, clipped = 0, []
    frames = {}
    for sec in h.SECTIONS:
        frame = hubqt().find(sec.frame, layout=True)
        if frame is None:
            continue
        frames[sec.key] = frame
        for w in frame.findChildren(W.QWidget):
            if not visible_in(w, frame):
                continue
            if isinstance(w, W.QAbstractButton):
                text = w.text()
            elif isinstance(w, W.QLabel) and not w.wordWrap():
                text = w.text()
            else:
                continue
            if not text or not text.strip():
                continue
            examined += 1
            if isinstance(w, (W.QCheckBox, W.QRadioButton)):
                need, have = w.sizeHint().width(), w.width() + 1
            else:
                need = w.fontMetrics().horizontalAdvance(text)
                have = w.contentsRect().width()
            if need > have:
                clipped.append("%s: %s %r needs %d of %d" % (
                    sec.key, name_of(w), text[:24], need, have))
    from maya_scenesetup import window as sw
    import maya_rig_retarget as rr
    from maya_com import panel as com
    rows = []
    for label, key, name, up in (
            ("the tab row", "weapons", sw.tab_segment("weapon"), 2),
            ("Retarget's row", "retarget", rr.bones_button("auto"), 2),
            ("CoM's chips row", "com", com.TRAIL, 1)):
        widget = hubqt().find(name)
        frame = frames.get(key)
        for _ in range(up):
            widget = None if widget is None else widget.parentWidget()
        if widget is None or frame is None:
            clipped.append("%s not found" % label)
            continue
        x, _y, ww, _hh = rect_in(widget, frame)
        rows.append("%s right %d of %d" % (label, x + ww, frame.width()))
        if x + ww > frame.width():
            clipped.append("%s past its section" % label)
    return examined, clipped, rows


def phase_classic2(build, deferred=True):
    """The classic hub measured and photographed, deaf to the real mouse
    the whole time (`deaf_classic`); a failure part-way gives it its ears
    back. Every Maya-owned widget is found again after each turn of the
    event loop (`classic_scroll`, `_stitch`'s finder)."""
    h = hub()
    if h.is_skinned():
        turn(10)                       # the deferred switch (`classic`)
    if h.is_skinned():
        raise RuntimeError("the hub is still skinned")
    deaf_classic(True)
    try:
        _classic2(build, h)
    except Exception:
        deaf_classic(False)
        raise
    if deferred:
        h.set_classic(False)
        print("the skin asked back (deferred)")


def _classic2(build, h):
    Q = q()
    W = Q.QtWidgets
    for sec in h.SECTIONS:
        if cmds.frameLayout(sec.frame, exists=True):
            cmds.frameLayout(sec.frame, edit=True, collapse=False)
    turn(10)
    width = fit_width()
    turn(10)
    deaf_classic(True)                 # idempotent; the widget found again
    area = classic_scroll()
    vp_width = area.viewport().width()
    content = area.widget()
    minimum = content.minimumSizeHint().width() if content else -1
    h_scroll = area.horizontalScrollBar().isVisible()
    del area, content
    over = []
    for sec in h.SECTIONS:
        frame = hubqt().find(sec.frame, layout=True)
        if frame is None:
            continue
        fw = frame.width()
        for w in frame.findChildren(W.QWidget):
            if not visible_in(w, frame):
                continue
            x, _y, ww, _hh = rect_in(w, frame)
            if x + ww > fw + 1:
                over.append("%s: %s %s right %d > %d" % (
                    sec.key, name_of(w), ui_type(w), x + ww, fw))
    gate("C1", "the classic hub at the dock's width: no horizontal scroll, "
         "no control past its section (the classic watch items: the tab "
         "row, Retarget's row, CoM's row)",
         not over and minimum <= vp_width and not h_scroll,
         "viewport %s, content minimum %d, h-scroll %s; %s" % (
             width, minimum, h_scroll, "; ".join(over[:12])))
    examined, clipped, rows = _classic_texts()
    gate("C3", "the classic hub at the dock's width: no button's, "
         "segment's, check box's or label's text clipped (the watch: the "
         "tab row's Equip / Unequip at 80, Retarget's Bones row, CoM's five "
         "columns)", examined and not clipped,
         "%d texts; %s%s" % (examined, "; ".join(rows),
                             (" | CLIPPED " + "; ".join(clipped[:12]))
                             if clipped else ""))
    path = picture_path(PNG_CLASSIC, build)
    deafened = _classic_deaf()
    size = _stitch(classic_parts, path)
    gate("C2", "the classic picture, the classic hub deaf to the real mouse "
         "while it was taken", os.path.isfile(path) and deafened,
         "%s %dx%d, deaf %s" % (path, size[0], size[1], deafened))


def phase_restore(build):
    h = hub()
    turn(10)
    state = _state()
    if "animations" in state:
        h.set_animations(state["animations"])
    print("skinned", h.is_skinned(), "animations",
          state.get("animations"))


def phase_summary(build):
    for b in ("old", "new"):
        path = os.path.join(OUT, "gates_%s.json" % b)
        if not os.path.isfile(path):
            continue
        data = json.load(open(path))
        passed = sum(1 for v in data.values() if v[1])
        print("%s: %d of %d gates" % (b, passed, len(data)))
        for n in sorted(data):
            name, ok, detail = data[n]
            print("  %s %4s %s - %s" % ("ok  " if ok else "FAIL", n, name,
                                         detail[:300]))


def dock_now():
    """The hub in the dock NOW (not deferred as the ⋮ switch is): the edge
    panel stopped, the mode off, the dock shown."""
    h = hub()
    if cmds.optionVar(exists=h.EDGE_VAR) and cmds.optionVar(query=h.EDGE_VAR):
        cmds.optionVar(intValue=(h.EDGE_VAR, 0))
        h.stop()
        turn(4)
    if not cmds.workspaceControl(h.CONTROL, exists=True):
        h.show()
        turn(10)


def classic_now(on):
    """⋮ -> Classic look (on) or Switch to the new look, NOW."""
    h = hub()
    cmds.optionVar(intValue=(h.CLASSIC_VAR, int(bool(on))))
    h.rebuild()
    turn(10)


def phase_all(build):
    """Every phase in ONE send. Measured twice: the animator switched the
    edge panel on in the disposable Maya between two sends (it is on their
    screen and new - trap 100), and a send then found no dock at all. In one
    send - the hub made deaf first - nothing of theirs gets in between."""
    dock_now()
    phase_size(build)
    for fn in (phase_heights, phase_cards, phase_relay, phase_notes,
               phase_grips):
        fn(build)
    turn(10)
    phase_grips2(build)
    turn(10)
    for fn in (phase_watch, phase_picture):
        fn(build)
    classic_now(True)
    phase_classic2(build, deferred=False)
    classic_now(False)
    phase_restore(build)


def phase_probe(build):
    """A scratch file run in this module's namespace (a diagnosis between
    gates): $SKELDAR_VERIFY_PROBE."""
    path = os.environ.get("SKELDAR_VERIFY_PROBE") or os.path.join(OUT,
                                                                  "probe.py")
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"),
         globals())


PHASES = {
    "probe": phase_probe,
    "dock": phase_dock,
    "all": phase_all,
    "open": phase_open,
    "install": phase_install, "size": phase_size, "heights": phase_heights,
    "cards": phase_cards, "relay": phase_relay, "notes": phase_notes,
    "grips": phase_grips, "grips2": phase_grips2, "watch": phase_watch,
    "scene": phase_scene, "picture": phase_picture,
    "classic": phase_classic, "classic2": phase_classic2,
    "restore": phase_restore, "summary": phase_summary,
}


def run(phase, build="new", source=""):
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    del RESULTS[:]
    try:
        if phase == "install":
            phase_install(build, source)
        else:
            PHASES[phase](build)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        RESULTS.append((phase + "!", "the phase crashed", False, ""))
    finally:
        if RESULTS:
            _save_gates(build)
    print("PASSED %d FAILED %d %s" % (
        sum(1 for r in RESULTS if r[2]), sum(1 for r in RESULTS if not r[2]),
        [r[0] for r in RESULTS if not r[2]]))
