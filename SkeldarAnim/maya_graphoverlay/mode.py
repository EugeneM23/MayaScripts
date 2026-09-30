"""Graph Overlay: Maya's own Graph Editor over the viewport, background out.

The animator (2026-09-30): «мне нужен граф эдитор с прозрачным фоном» -
shape Б, a mode on a key, the curve area on the whole viewport; alt+mouse
is the camera («1, камеры»). Maya's drawing cannot be made transparent (the
canvas clears opaque whatever the background alpha, measured), so:

- the GHOST (`ghost.py`): a Graph Editor panel of ours, chrome hidden, its
  canvas on the viewport pixel for pixel, invisible at a layered alpha of
  1 - it still renders and takes every click and key;
- the GLASS (`glass.py`): a click-through translucent window on the same
  rectangle showing the ghost's frames with the flat background keyed out
  (`keying.py`) - grabbed on every `frameSwapped`, coalesced, at most every
  `MIN_UPDATE_S`;
- a 30 ms alt poll: held, the ghost lets the mouse through to the viewport
  and Maya's camera takes it; released, the graph takes it again;
- a 10 Hz follow timer: the viewport moved, the two follow it; Maya behind
  another program or no viewport, the glass hides and the ghost lets
  clicks through; our panel gone, the mode ends.

    import maya_graphoverlay; maya_graphoverlay.toggle()      # alt+c

Spec: docs/superpowers/specs/2026-09-30-graph-overlay-design.md
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
ALT_MS = 30
MIN_UPDATE_S = 0.015
MIN_CHROME_S = 0.03
MOST_TONES = 3      # background tones learnt over a session of frames
TONE_SPREAD = 24    # levels a later tone may stand from the first
# The whole Graph Editor on the viewport - menus, toolbar, channel list -
# with only the curve area see-through (2026-09-30, the animator: «я не могу
# выделить отдельно каналы для редактирования кривых и нет остальных
# инструментов»). False is the first build: the curve area alone.
CHROME = True
# Maya's own graphEditor1 borrowed rather than a panel of ours: 55 of Maya's
# runtime commands name it outright (the view modes, Copy/Paste keys,
# infinity, frame all...) and the toolbar, menus and hotkeys reach them.
BORROW = True
REWATCH_TICKS = 10  # follow ticks between looks for new chrome widgets

HINT = "alt+mouse: camera  |  F / A: frame the graph  |  alt+c: leave"
PANEL_HINT = "The Graph Editor over the viewport, see-through (alt+c)"
PANEL_NOTE = ("Maya's own Graph Editor lies on the viewport with its "
              "background taken out: every click and key is the Graph "
              "Editor's. Hold alt for the camera; select objects in the "
              "outliner or the channel box, or leave the mode.")


class _State(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.ghost = None
        self.glass = None
        self.canvas = None
        self.model_panel = None
        self.timers = []
        self.jobs = []
        self.rect = None
        self.placed = False
        self.active = True
        self.through = None
        self.keys = []
        self.table = None
        self.pending = False
        self.last = None
        self.frames = 0
        self.cost = 0.0
        self.closing = False
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
    panel = viewport.active_panel()
    rect = viewport.gl_rect(panel)
    if not geometry.usable(rect):
        return "Graph Overlay: no viewport to lie on"
    from maya_graphoverlay import ghost, glass, keying
    parent = viewport.maya_main_window()
    try:
        _STATE.model_panel = panel
        _STATE.ghost = ghost.Ghost(parent, rect, chrome=CHROME, borrow=BORROW)
        _STATE.glass = glass.Glass(parent)
        _STATE.glass.place(rect)
        _STATE.rect, _STATE.placed = rect, True
        _STATE.table = keying.alpha_table()
        if not _POOL:
            _POOL.append(keying.make_pool())
        _connect_canvas()
        _watch_chrome()
        _on_chrome_paint()
        _start_timers()
        _install_jobs()
    except Exception:
        traceback.print_exc()
        disable()
        raise
    return "Graph Overlay ON  -  " + HINT


def disable():
    if not is_on():
        return "Graph Overlay is already off"
    _STATE.closing = True
    try:
        _stop_timers()
        _kill_jobs()
        canvas = _STATE.canvas
        if canvas is not None:
            try:
                canvas.frameSwapped.disconnect(_on_swap)
            except (RuntimeError, TypeError):
                pass
        if _STATE.watch is not None:
            try:
                _STATE.watch.deleteLater()      # Qt drops it from every widget
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
    _on_swap()


def _same_object(first, second):
    """Whether two wrappers hold the same live Qt object."""
    if first is None or second is None:
        return False
    try:
        import shiboken6
        return (shiboken6.getCppPointer(first)[0]
                == shiboken6.getCppPointer(second)[0])
    except (RuntimeError, TypeError):
        return False


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
            image = _STATE.ghost.grab()
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
    if not is_on() or not _STATE.ghost.chrome:
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
    if not is_on() or _STATE.chrome_pending or not _STATE.ghost.chrome:
        return
    _STATE.chrome_pending = True
    from PySide6 import QtCore
    delay = geometry.due_in(time.perf_counter(), _STATE.chrome_last,
                            MIN_CHROME_S)
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

def _start_timers():
    from PySide6 import QtCore
    for interval, slot in ((FOLLOW_MS, _follow), (ALT_MS, _alt_tick)):
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
    from maya_graphoverlay import viewport, winstyle
    ghost_, glass_ = _STATE.ghost, _STATE.glass
    if not ghost_.alive():
        why = (" - the Graph Editor was opened in its own window"
               if ghost_.borrowed else " - its Graph Editor panel was deleted")
        _show(disable() + why)
        return
    if not viewport.visible(_STATE.model_panel):
        _STATE.model_panel = viewport.active_panel()
    rect = viewport.gl_rect(_STATE.model_panel)
    _STATE.active = viewport.maya_active()
    _STATE.placed = geometry.usable(rect)
    if not (_STATE.active and _STATE.placed):
        if glass_.isVisible():
            glass_.hide()
    else:
        if rect != _STATE.rect or not glass_.isVisible():
            _STATE.rect = rect
            glass_.place(rect)
        if not ghost_.aligned(rect):
            ghost_.place(rect)
            _on_chrome_paint()
        glass_.keep_click_through()
    ghost_.keep_invisible()
    # Re-parenting a panel can recreate its canvas window: follow the new one.
    if not _same_object(ghost_.canvas(), _STATE.canvas):
        _connect_canvas()
    _STATE.ticks += 1
    if _STATE.ticks % REWATCH_TICKS == 0:
        _watch_chrome()
    _poll_alt()


def _alt_tick():
    try:
        _poll_alt()
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()


def _poll_alt(alt=None):
    """Compared with the window's REAL style, never a remembered one: Qt
    rewrites the styles of its windows (measured - it dropped our
    WS_EX_TRANSPARENT when the opacity was set), so a cached "already
    through" can be a lie."""
    if not is_on() or _STATE.closing:
        return
    from maya_graphoverlay import winstyle
    if alt is None:
        alt = winstyle.alt_down()
    through = geometry.let_through(alt, _STATE.active, _STATE.placed)
    hwnd = _STATE.ghost.hwnd()
    if winstyle.is_click_through(hwnd) != through:
        winstyle.set_click_through(hwnd, through)
    _STATE.through = through


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


def _paint_button():
    try:
        if cmds.control(BUTTON, exists=True):
            cmds.button(BUTTON, edit=True, label=button_label())
    except Exception:                                         # noqa: BLE001
        pass


def _show(text):
    """The first line on the section's status line and in the viewport, the
    whole of it in the Script Editor."""
    print(text)
    first = text.splitlines()[0] if text.strip() else ""
    try:
        if cmds.control(STATUS, exists=True):
            cmds.text(STATUS, edit=True, label=first)
    except Exception:                                         # noqa: BLE001
        pass
    _paint_button()
    try:
        cmds.inViewMessage(assistMessage=first, position="midCenterTop",
                           fade=True)
    except Exception:                                         # noqa: BLE001
        pass
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
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(label=PANEL_HINT, align="left", wordWrap=True,
                            height=36), "note")
    hubstyle.mark(cmds.button(BUTTON, label=button_label(), height=34,
                              backgroundColor=(0.45, 0.60, 0.70),
                              annotation=PANEL_NOTE, command=_press),
                  "primary", "chart-line")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    return column
