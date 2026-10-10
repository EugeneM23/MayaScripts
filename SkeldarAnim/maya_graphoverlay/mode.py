"""Graph Overlay: Maya's own Graph Editor in a window of its own, background out.

The animator (2026-10-02): «нужен стандартный граф эдитор только с
прозрачным фоном». Maya's canvas cannot be made transparent (it clears
opaque whatever the background alpha, measured), so:

- the WINDOW (`ghost.py`): Maya's own Graph Editor, borrowed, in a standard
  window of ours - title bar, borders, the menus and the channel list as
  Maya draws them - invisible at a layered alpha of 1: it still renders and
  takes every click, key and drag;
- the GLASS (`glass.py`): a click-through translucent window on the same
  frame, showing DWM's copy of the window with the curve area's flat
  background keyed out (`keying.py`) - grabbed on every `frameSwapped`,
  coalesced, at most every `MIN_UPDATE_S`;
- the window's own move, resize and close are followed at once (an event
  filter), the glass moves with it; the place is remembered;
- a 10 Hz follow timer: Maya behind another program or minimised, the glass
  hides; the window closed or our panel gone, the mode ends. The window
  takes every click and drag as the standard Graph Editor does - nothing
  of the mode reaches the viewport's camera or its selection.

    import maya_graphoverlay; maya_graphoverlay.toggle()      # alt+c

Spec: docs/superpowers/specs/2026-09-30-graph-overlay-design.md (its
addendum of 2026-10-02 replaces the viewport-sized window with this one).
"""

import sys
import time
import traceback

import maya.cmds as cmds

import maya_hubstyle as hubstyle
from maya_graphoverlay import geometry

HUB_SECTION = "graphoverlay"
STATUS = "skeldarGraphOverlayStatus"
BUTTON = "skeldarGraphOverlayButton"

FOLLOW_MS = 100
MIN_UPDATE_S = 0.015
MIN_CHROME_S = 0.03
# The chrome is first captured this long after switching on: the borrowed
# panel is still being rebuilt by Maya in its new place just after.
CHROME_SETTLE_S = 0.5
MOST_TONES = 3      # background tones learnt over a session of frames
TONE_SPREAD = 24    # levels a later tone may stand from the first
# Maya's own graphEditor1 borrowed rather than a panel of ours: 55 of Maya's
# runtime commands name it outright (the view modes, Copy/Paste keys,
# infinity, frame all...) and the toolbar, menus and hotkeys reach them.
BORROW = True
REWATCH_TICKS = 10  # follow ticks between looks for new chrome widgets
# The window's frame as the animator left it: "x,y,width,height" (global).
RECT_OPTION = "skeldarGraphOverlayRect"

HINT = "F / A: frame the graph  |  alt+c: leave"
PANEL_HINT = "The Graph Editor in its own window, background see-through"
PANEL_NOTE = ("Maya's own Graph Editor in a window of its own: move and "
              "resize it like any window. Its background is see-through, so "
              "the viewport shows through the graph. Closing the window "
              "leaves the mode.")


class _State(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.ghost = None
        self.glass = None
        self.canvas = None
        self.frame_watch = None         # the window's own event filter
        self.timers = []
        self.jobs = []
        self.rect = None
        self.placed = False
        self.active = True
        self.keys = []
        self.table = None
        self.pending = False
        self.last = None
        self.frames = 0
        self.cost = 0.0
        self.closing = False
        self.canvas_pointer = None      # the connected canvas's address
        self.chrome_after = 0.0         # no chrome capture before this
        self.watch = None               # the chrome's event filter
        self.watched = set()            # C++ addresses it is installed on
        self.grabbing = False
        self.chrome_pending = False
        self.chrome_last = None
        self.chrome_grabs = 0
        self.ticks = 0


SESSION_STATE = "_skeldar_graphoverlay_state"


def _shared_state():
    """ONE state per Maya session, whichever copy of this module asks.

    Measured live 2026-09-30: an install purges our modules, the hub's
    button stays bound to the copy that built it, and four copies each
    kept a state of their own - the running overlay lived in a copy nobody
    could reach and `import` handed out one that said it was off (trap 49's
    shape). So the state hangs off `sys`, and a state an older copy made
    gains any field this one has added.
    """
    state = getattr(sys, SESSION_STATE, None)
    if state is None:
        state = _State()
        setattr(sys, SESSION_STATE, state)
    else:
        for name, value in vars(_State()).items():
            if not hasattr(state, name):
                setattr(state, name, value)
    return state


def reset_state(state=None):
    """Every field back to THIS module's defaults. Never `state.reset()`:
    the session's state may have been made by an older copy whose class
    knows fewer fields (measured - its `reset()` left a dead event filter
    in place, and the next switch-on died on it)."""
    state = _STATE if state is None else state
    for name, value in vars(_State()).items():
        setattr(state, name, value)
    return state


_STATE = _shared_state()
_POOL = []          # the keying threads, made once a module


# ------------------------------------------------------------------ the mode

def is_on():
    return _STATE.ghost is not None


def enable():
    if is_on():
        return "Graph Overlay is already on"
    from maya_graphoverlay import viewport, winstyle
    if not winstyle.available():
        return "Graph Overlay needs Windows"
    rect = _start_rect(viewport)
    if rect is None:
        return "Graph Overlay: no viewport to open it over"
    from maya_graphoverlay import ghost, glass, keying
    parent = viewport.maya_main_window()
    reset_state()                   # whatever an older copy left in it
    try:
        _STATE.ghost = ghost.Ghost(parent, rect, borrow=BORROW)
        _STATE.glass = glass.Glass(parent)
        _STATE.placed = _STATE.ghost.showing()
        _STATE.rect = _STATE.ghost.frame_rect()
        _STATE.glass.place(_STATE.rect)
        _remember(_STATE.rect)
        _STATE.table = keying.alpha_table()
        if not _POOL:
            _POOL.append(keying.make_pool())
        _connect_canvas()
        _STATE.chrome_after = time.perf_counter() + CHROME_SETTLE_S
        _watch_chrome()
        _on_chrome_paint()
        _watch_frame()
        _start_timers()
        _install_jobs()
    except Exception:
        traceback.print_exc()
        disable()
        raise
    return "Graph Overlay ON  -  " + HINT


def _start_rect(viewport):
    """Where the window opens: the place the animator left it, while that
    still shows on a screen; else the default in the viewport's lower right.
    None when there is no viewport to size the default from."""
    saved = _remembered()
    if geometry.on_some_screen(saved, _screens()):
        return saved
    view = viewport.gl_rect(viewport.active_panel())
    if not geometry.usable(view):
        return None
    return geometry.default_rect(view)


def _screens():
    try:
        from PySide6 import QtGui
        return [(s.geometry().x(), s.geometry().y(), s.geometry().width(),
                 s.geometry().height())
                for s in QtGui.QGuiApplication.screens()]
    except Exception:                                         # noqa: BLE001
        return []


def _remembered():
    """The window's frame the animator left, or None."""
    try:
        if not cmds.optionVar(exists=RECT_OPTION):
            return None
        parts = [int(v) for v in
                 str(cmds.optionVar(query=RECT_OPTION)).split(",")]
    except Exception:                                         # noqa: BLE001
        return None
    return tuple(parts) if len(parts) == 4 else None


def _remember(rect):
    try:
        cmds.optionVar(stringValue=(RECT_OPTION,
                                    ",".join(str(int(v)) for v in rect)))
    except Exception:                                         # noqa: BLE001
        pass


def disable():
    if not is_on():
        return "Graph Overlay is already off"
    _STATE.closing = True
    try:
        _stop_timers()
        _kill_jobs()
        # Only from the canvas still alive and still the one connected: a
        # deleted sender has let go by itself, and asking a wrapper of a
        # deleted object anything reads freed memory.
        ghost_ = _STATE.ghost
        live = ghost_.canvas() if ghost_ is not None else None
        if live is not None and _STATE.canvas_pointer is not None and \
                ghost_.canvas_pointer() == _STATE.canvas_pointer:
            try:
                live.frameSwapped.disconnect(_on_swap)
            except (RuntimeError, TypeError):
                pass
        if _STATE.watch is not None:
            try:
                _STATE.watch.deleteLater()      # Qt drops it from every widget
            except RuntimeError:
                pass
        if _STATE.frame_watch is not None:
            try:
                _STATE.frame_watch.deleteLater()
            except RuntimeError:
                pass
        if _STATE.glass is not None:
            _STATE.glass.close_glass()
        if _STATE.ghost is not None:
            _STATE.ghost.destroy()
    finally:
        reset_state()
    return "Graph Overlay OFF"


def toggle():
    return _show(disable() if is_on() else enable())


# ------------------------------------------------------------- the pipeline

def _connect_canvas():
    canvas = _STATE.ghost.canvas() if _STATE.ghost is not None else None
    if canvas is None:
        return
    canvas.frameSwapped.connect(_on_swap)
    _STATE.canvas = canvas
    _STATE.canvas_pointer = _STATE.ghost.canvas_pointer()
    _on_swap()


def _on_swap():
    """The graph drew a frame: key it now, or as soon as it is due."""
    if not is_on() or _STATE.pending:
        return
    _STATE.pending = True
    from PySide6 import QtCore
    delay = geometry.due_in(time.perf_counter(), _STATE.last, MIN_UPDATE_S)
    QtCore.QTimer.singleShot(int(round(delay * 1000)), _update)


def learn_tones(found):
    """Grow the background tones with what this frame shows, never shrink
    them: the out-of-range tint leaves the frame when the view is inside
    the range and must not flash back grey when it returns.

    A tone further than `TONE_SPREAD` from the first is never one: measured
    live, a frame drawn half black while the host grew taught (0, 0, 0),
    which would key out the black range flags. The Graph Editor's own tones
    stand a few levels apart (64 and 55)."""
    for tone in found:
        if tone in _STATE.keys or len(_STATE.keys) >= MOST_TONES:
            continue
        if _STATE.keys and max(abs(int(a) - int(b)) for a, b
                               in zip(tone, _STATE.keys[0])) > TONE_SPREAD:
            continue
        _STATE.keys.append(tone)
    return list(_STATE.keys)


def _update():
    _STATE.pending = False
    if not is_on() or not _STATE.placed or _STATE.closing:
        return
    started = time.perf_counter()
    try:
        import numpy as np
        from maya_graphoverlay import keying, winstyle
        with winstyle.gl_kept():
            image = _STATE.ghost.canvas_frame()
        if image is None or image.isNull():
            return
        width, height = image.width(), image.height()
        pixels = np.frombuffer(image.constBits(), np.uint8).reshape(
            height, image.bytesPerLine() // 4, 4)[:, :width]
        if not _STATE.keys and keying.is_uniform(pixels):
            return                          # not drawn yet: nothing to show
        learn_tones(keying.backgrounds(pixels))
        _STATE.glass.set_frame(
            keying.key_out(pixels, _STATE.keys, _STATE.table,
                           _POOL[0] if _POOL else None),
            offset=_STATE.ghost.canvas_offset())
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()
        return
    _STATE.last = time.perf_counter()
    _STATE.frames += 1
    _STATE.cost = _STATE.last - started


# --------------------------------------------------------------- the chrome

def _make_watch():
    """The event filter on the chrome's widgets: a repaint there means the
    menus, the toolbar or the channel list changed, so the glass takes a new
    picture of them. Silent while the grab itself repaints them."""
    from PySide6 import QtCore

    class ChromeWatch(QtCore.QObject):

        def eventFilter(self, watched, event):
            try:
                if event.type() == QtCore.QEvent.Paint and \
                        not _STATE.grabbing:
                    _on_chrome_paint()
            except Exception:                                 # noqa: BLE001
                pass
            return False

    return ChromeWatch()


def _watch_chrome():
    """Put the filter on every chrome widget it is not on yet."""
    if not is_on():
        return 0
    import shiboken6
    if _STATE.watch is not None:
        try:
            _STATE.watch.objectName()
        except RuntimeError:                    # deleted: start over
            _STATE.watch, _STATE.watched = None, set()
    if _STATE.watch is None:
        _STATE.watch = _make_watch()
    added = 0
    for widget in _STATE.ghost.chrome_widgets():
        try:
            address = int(shiboken6.getCppPointer(widget)[0])
        except RuntimeError:
            continue
        if address in _STATE.watched:
            continue
        widget.installEventFilter(_STATE.watch)
        _STATE.watched.add(address)
        added += 1
    return added


def _on_chrome_paint():
    """The chrome repainted: a new picture of it, now or when it is due."""
    if not is_on() or _STATE.chrome_pending:
        return
    _STATE.chrome_pending = True
    from PySide6 import QtCore
    now = time.perf_counter()
    delay = max(geometry.due_in(now, _STATE.chrome_last, MIN_CHROME_S),
                _STATE.chrome_after - now)
    QtCore.QTimer.singleShot(int(round(delay * 1000)), _update_chrome)


def _update_chrome():
    _STATE.chrome_pending = False
    if not is_on() or _STATE.closing:
        return
    _STATE.grabbing = True
    try:
        pieces = _STATE.ghost.chrome_pieces()
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()
        return
    finally:
        _STATE.grabbing = False
    _STATE.glass.set_chrome(pieces)
    _STATE.chrome_last = time.perf_counter()
    _STATE.chrome_grabs += 1


# ---------------------------------------------------------------- following

def _sync_glass():
    """The glass on the window's frame: shown while the window stands on
    screen and Maya is in front, hidden otherwise. The place is remembered
    when it changes, and the chrome picture taken again when the size does."""
    if not is_on() or _STATE.closing:
        return
    ghost_, glass_ = _STATE.ghost, _STATE.glass
    _STATE.placed = ghost_.showing()
    if not (_STATE.placed and _STATE.active):
        if glass_.isVisible():
            glass_.hide()
        return
    rect = ghost_.frame_rect()
    if rect == _STATE.rect and glass_.isVisible():
        return
    previous, _STATE.rect = _STATE.rect, rect
    glass_.place(rect)
    _remember(rect)
    if previous is None or previous[2:] != rect[2:]:
        _on_chrome_paint()


def _make_frame_watch():
    """The window's own event filter: its move, resize, show and hide are
    followed at once, not on the next follow tick - a tick would leave the
    glass a beat behind a drag. Its close leaves the mode: the window's X is
    the way out, as the Graph Editor's own window's would be."""
    from PySide6 import QtCore

    class FrameWatch(QtCore.QObject):

        def eventFilter(self, watched, event):
            try:
                kind = event.type()
                if kind in (QtCore.QEvent.Move, QtCore.QEvent.Resize,
                            QtCore.QEvent.Show, QtCore.QEvent.Hide,
                            QtCore.QEvent.WindowStateChange):
                    _sync_glass()
                elif kind == QtCore.QEvent.Close:
                    QtCore.QTimer.singleShot(0, _leave_from_window)
            except Exception:                                 # noqa: BLE001
                traceback.print_exc()
            return False

    return FrameWatch()


def _watch_frame():
    if _STATE.frame_watch is None:
        _STATE.frame_watch = _make_frame_watch()
    _STATE.ghost.host.installEventFilter(_STATE.frame_watch)


def _leave_from_window():
    if is_on() and not _STATE.closing:
        _show(disable() + " - the window was closed")


def _start_timers():
    from PySide6 import QtCore
    for interval, slot in ((FOLLOW_MS, _follow),):
        timer = QtCore.QTimer()
        timer.setInterval(interval)
        timer.timeout.connect(slot)
        timer.start()
        _STATE.timers.append(timer)


def _stop_timers():
    for timer in _STATE.timers:
        try:
            timer.stop()
            timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass
    _STATE.timers = []


def _follow():
    if not is_on() or _STATE.closing:
        return
    try:
        _follow_once()
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()


def _follow_once():
    from maya_graphoverlay import viewport
    ghost_, glass_ = _STATE.ghost, _STATE.glass
    if not ghost_.alive():
        why = (" - the Graph Editor was opened in its own window"
               if ghost_.borrowed else " - its Graph Editor panel was deleted")
        _show(disable() + why)
        return
    _STATE.active = viewport.maya_active()
    _sync_glass()
    if _STATE.placed and _STATE.active:
        ghost_.open_channel_list()          # once, when laid out
        glass_.keep_click_through()
    ghost_.keep_invisible()
    # Re-parenting a panel can recreate its canvas window: follow the new
    # one, compared by address - never by asking the old wrapper.
    if ghost_.canvas_pointer() != _STATE.canvas_pointer:
        _connect_canvas()
    _STATE.ticks += 1
    if _STATE.ticks % REWATCH_TICKS == 0:
        _watch_chrome()


def _install_jobs():
    for event in ("SceneOpened", "NewSceneOpened"):
        try:
            _STATE.jobs.append(cmds.scriptJob(event=[event, _on_scene],
                                              killWithScene=False))
        except Exception:                                     # noqa: BLE001
            pass


def _kill_jobs():
    for job in _STATE.jobs:
        try:
            cmds.scriptJob(kill=job, force=True)
        except Exception:                                     # noqa: BLE001
            pass
    _STATE.jobs = []


def _leave_for_scene():
    if is_on():
        _show(disable() + " - a scene was opened")


def _on_scene():
    """A scene's UI configuration may delete panels: leave cleanly first."""
    if is_on() and not _STATE.closing:
        cmds.evalDeferred(_leave_for_scene)


# --------------------------------------------------------------- the section

def button_label():
    return "Graph Overlay: ON" if is_on() else "Graph Overlay: OFF"


def _each_card(fn):
    fn()


def _paint_button():
    def paint():
        try:
            if cmds.control(BUTTON, exists=True):
                cmds.button(BUTTON, edit=True, label=button_label())
        except Exception:                                     # noqa: BLE001
            pass
    _each_card(paint)


def _show(text):
    """The first line on the section's status line and in the viewport, the
    whole of it in the Script Editor."""
    print(text)
    first = text.splitlines()[0] if text.strip() else ""

    def line():
        try:
            if cmds.control(STATUS, exists=True):
                cmds.text(STATUS, edit=True, label=first)
        except Exception:                                     # noqa: BLE001
            pass
    _each_card(line)
    _paint_button()
    try:
        cmds.inViewMessage(assistMessage=first, position="midCenterTop",
                           fade=True)
    except Exception:                                         # noqa: BLE001
        pass
    #  2026-10-08: the skin's one message line carries it too; the viewport
    #  already has it, so the edge panel need not show it again.
    hubstyle.tell(STATUS, first, viewport=True)
    return text


def _press(*_args):
    try:
        return toggle()
    except Exception as exc:                                  # noqa: BLE001
        _show("%s: %s" % (type(exc).__name__, exc))
        raise


def is_open():
    return bool(cmds.control(STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on this section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def build_panel():
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(label=PANEL_HINT, align="left", wordWrap=True,
                            height=36), "note")
    hubstyle.mark(cmds.button(BUTTON, label=button_label(),
                              height=hubstyle.height("button", 34),
                              backgroundColor=(0.45, 0.60, 0.70),
                              annotation=PANEL_NOTE, command=_press),
                  "primary", "chart-line")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    return column
