"""Take our Qt down while Python is still alive (2026-11-02).

Measured: every quit of the animator's Maya wrote a crash dump -- 244 of 256 GUI
crashes in October were one ACCESS_VIOLATION in `shiboken6.abi3.dll` on the main
thread, 227 of them with the C runtime's exit handlers (`_execute_onexit_table`)
on the stack, the chain reading

    _execute_onexit_table -> ~QObject -> ~QObjectPrivate -> ~QMetaObject::Connection
    -> PySide's signal machinery -> shiboken reads 0

and the same crash mid-session as `QTimer::timerEvent -> QMetaObject::activate ->
SignalManager::callPythonMetaMethod -> PyGILState_Ensure -> shiboken reads 0`.

The cause was ours and there was nothing to blame in Qt: the plugin attaches Python
to Maya's own Qt objects -- 261 `.connect(` against 17 `.disconnect(`, 82 QTimers, 38
event filters, graphics effects on Maya's controls, and Maya's own Channel Box and
Attribute Editor held INSIDE our window -- and nothing detached any of it. Python
finalises first; Qt then destroys those objects and PySide calls into dead Python.
Before 2026-09-29 the plugin had 0 timers and 0 event filters, which is the day the
crash signature changed (reproduced in a throwaway Maya: our interface standing ->
a dump on quit at the identical offset; the same Maya without the plugin -> none).

So: one `kMayaExiting` hook that runs the teardown the plugin already has, in an
order that matters, early enough that Python is healthy. `install.install` runs the
same thing before `purge_modules`, which is the mid-session half -- a timer of a
module that has just been dropped is exactly the second stack above.

Two rules hold the whole thing up:

- **Only what is standing.** A step is looked up in `sys.modules` and never imported:
  importing `maya_chat` here would START the chat as Maya closes.
- **Maya's widgets go back BEFORE anything of ours is destroyed.** The side panel's
  own docstring says why -- "a host deleted with a form inside would delete Maya's
  editor". Every step is guarded, so one refusal cannot strand the rest.
"""

import collections
import sys
import traceback

STATE = "_skeldar_shutdown"

GIVE_BACK = "give back"
STOP = "stop"
DESTROY = "destroy"

Step = collections.namedtuple("Step", "module function what phase")

#: In order. The phase says why a step sits where it does, and the tests pin that
#: every GIVE_BACK runs before every DESTROY.
PLAN = (
    # 1. Maya's own widgets out of ours, while both still live.
    Step("maya_graphoverlay.mode", "disable",
         "Maya's Graph Editor back in its own window, frameSwapped disconnected",
         GIVE_BACK),
    Step("maya_sidepanel", "drop_edge",
         "Maya's Channel Box and Attribute Editor out of our window", GIVE_BACK),
    Step("maya_channelbox", "unmount",
         "Maya's own Channel Box back in its page", GIVE_BACK),
    Step("maya_timebar", "drop_edge",
         "Maya's time slider back, our edge host gone", GIVE_BACK),
    Step("maya_viewportbar", "remove_all",
         "Maya's own icons and sheets back on the viewport bars", GIVE_BACK),
    Step("maya_viewportbar", "unwatch", "the viewport bar's re-skin watch", GIVE_BACK),
    Step("maya_mainbar", "remove",
         "Maya's own title bar and menu bar back", GIVE_BACK),
    Step("maya_mainbar", "unwatch", "the main bar's re-skin watch", GIVE_BACK),

    # 2. Nothing of ours may tick while Maya tears itself down.
    Step("maya_windowlight", "stop", "the 50 ms cursor poll", STOP),
    Step("maya_camview", "unwatch", "the camera watch, views put back", STOP),
    Step("maya_camflight", "_stop",
         "a camera flight in the air (its only stop is private)", STOP),
    Step("maya_com.engine", "stop", "the centre-of-mass engine", STOP),
    Step("maya_chat.session", "close", "the chat's socket, its timers and its calls", STOP),
    Step("maya_hubsound", "forget_players", "the sound pools", STOP),

    # 3. Ours destroyed by us, not by Qt after Python has gone.
    Step("maya_hubpop", "destroy_all", "every floating section window", DESTROY),
    Step("maya_hubedge", "destroy_all", "the edge rail and its panel", DESTROY),
    Step("maya_hub", "drop_skin",
         "the hub's skin and its application-wide watcher", DESTROY),
)


def ours(module):
    """Is a dotted module name one of ours? Every module of the plugin is `maya_*`;
    Maya's own are `maya.*` and `maya` exactly, so the underscore is the whole test."""
    if not module:
        return False
    return module.split(".")[0].startswith("maya_")


def steps(loaded):
    """The steps that apply, in PLAN order: `loaded` is what is in `sys.modules`."""
    return tuple(step for step in PLAN if step.module in loaded)


def _state():
    state = getattr(sys, STATE, None)
    if not isinstance(state, dict):
        state = {"callback": None}
        setattr(sys, STATE, state)
    return state


def run():
    """Every standing step, in order, each guarded. Imports nothing.

    Returns {"done": [...], "skipped": [...], "failed": [...]} of "module.function"."""
    report = {"done": [], "skipped": [], "failed": []}
    for step in steps(set(sys.modules)):
        name = "%s.%s" % (step.module, step.function)
        module = sys.modules.get(step.module)
        call = getattr(module, step.function, None)
        if not callable(call):
            report["skipped"].append(name)
            continue
        try:
            call()
            report["done"].append(name)
        except Exception:                                    # noqa: BLE001
            report["failed"].append(name)
            print("SkeldarAnim shutdown: %s refused\n%s" % (name, traceback.format_exc()))
    return report


def _widgets(app=None):
    """Every widget Qt knows about, or () when our Qt never ran. Imports nothing:
    at exit PySide6 is long since imported, and if it is not there is nothing of
    ours to take down."""
    qtw = sys.modules.get("PySide6.QtWidgets")
    if qtw is None:
        return (), None
    app = app or qtw.QApplication.instance()
    if app is None:
        return (), None
    return tuple(app.allWidgets()), app


def stop_timers(widgets=None):
    """Stop every QTimer living under one of our widgets, destroying nothing.

    The mid-session crash is a timer tick delivered to a Python slot that is gone;
    at shutdown the same tick can land after Python has begun finalising. Stopping
    is free and cannot upset Maya, so it runs before anything is destroyed."""
    qtc = sys.modules.get("PySide6.QtCore")
    if qtc is None:
        return 0
    if widgets is None:
        widgets, _app = _widgets()
    stopped = 0
    for widget in widgets:
        try:
            if not ours(type(widget).__module__):
                continue
            for timer in widget.findChildren(qtc.QTimer):
                try:
                    if timer.isActive():
                        timer.stop()
                        stopped += 1
                except RuntimeError:                         # a dead wrapper: leave it
                    continue
        except RuntimeError:
            continue
    return stopped


def sweep_windows(widgets=None, delete=None):
    """Destroy our own top-level windows NOW, while Python can still run their
    teardown. Only windows whose Python CLASS is one of ours: Maya's own popups
    (an optionMenu's, a menu's) are top-level too and are not ours to delete."""
    if widgets is None:
        _all, app = _widgets()
        if app is None:
            return []
        widgets = app.topLevelWidgets()
    if delete is None:
        shiboken = sys.modules.get("shiboken6")
        delete = getattr(shiboken, "delete", None)
    gone = []
    for widget in list(widgets):
        try:
            if not ours(type(widget).__module__):
                continue
            name = widget.objectName() or type(widget).__name__
        except RuntimeError:
            continue
        try:
            widget.hide()
            widget.setParent(None)                  # out of Maya's tree first
            if delete is not None:
                delete(widget)
            else:
                widget.deleteLater()
            gone.append(name)
        except Exception:                                    # noqa: BLE001
            print("SkeldarAnim shutdown: %s would not go\n%s"
                  % (name, traceback.format_exc()))
    return gone


def _valid(obj):
    shiboken = sys.modules.get("shiboken6")
    is_valid = getattr(shiboken, "isValid", None)
    if is_valid is None:
        return True
    try:
        return bool(is_valid(obj))
    except Exception:                                        # noqa: BLE001
        return False


def _depth(widget):
    """How deep in the Qt tree, so children are destroyed before their parents."""
    n = 0
    try:
        while widget.parent() is not None and n < 64:
            widget = widget.parent()
            n += 1
    except RuntimeError:
        pass
    return n


def sweep_widgets(widgets=None, delete=None):
    """Every widget of ours ANYWHERE, deepest first - not only the top-level windows.

    Measured 2026-11-02: with the named steps done and no top-level window of ours
    left, 32 of our widgets were still standing re-parented under `MayaWindow` - the
    whole Time Bar strip with its 10 timers and its DragKeys filter, the side panel
    with its grips and burst overlay, the skill bar's rows, the scene tabs bar - and
    Maya still crashed on quit. They are what Qt destroys after Python has gone.

    Only at exit (`deep`), never on an install: there is nothing to rebuild afterwards.
    By then the hub's skin is destroyed by its own step, so nothing swept here holds
    Maya's `cmds` controls."""
    if widgets is None:
        allw, app = _widgets()
        if app is None:
            return []
        widgets = allw
    if delete is None:
        shiboken = sys.modules.get("shiboken6")
        delete = getattr(shiboken, "delete", None)
    mine = [w for w in widgets if ours(type(w).__module__)]
    mine.sort(key=_depth, reverse=True)
    gone = []
    for widget in mine:
        try:
            if not _valid(widget):
                continue
            name = widget.objectName() or type(widget).__name__
            widget.hide()
            widget.setParent(None)
            if delete is not None:
                delete(widget)
            else:
                widget.deleteLater()
            gone.append(name)
        except Exception:                                    # noqa: BLE001
            continue
    return gone


def _qt_in(value, path, found, depth=0, seen=None):
    """Every QObject our own `sys._skeldar_*` state still holds, by path."""
    qtc = sys.modules.get("PySide6.QtCore")
    if qtc is None or depth > 3:
        return
    seen = seen if seen is not None else set()
    if id(value) in seen:
        return
    seen.add(id(value))
    try:
        if isinstance(value, qtc.QObject):
            found.append((path, value))
            return
    except RuntimeError:                       # a dead wrapper: nothing to take down
        return
    if isinstance(value, dict):
        for key, item in list(value.items()):
            _qt_in(item, "%s[%r]" % (path, key), found, depth + 1, seen)
    elif isinstance(value, (list, tuple, set)):
        for i, item in enumerate(list(value)):
            _qt_in(item, "%s[%d]" % (path, i), found, depth + 1, seen)
    elif hasattr(value, "__dict__") and ours(type(value).__module__):
        for key, item in list(vars(value).items()):
            _qt_in(item, "%s.%s" % (path, key), found, depth + 1, seen)


def takeable(obj):
    """Is a QObject our state holds ours to take down?

    Ours when its class is ours, or when it is no widget at all: we made the
    QMediaDevices watcher, the QTimers and the chat's socket, while a plain
    `PySide6.QtWidgets.QWidget` in our state is MAYA's - its main window, or one of
    its controls we merely keep a handle on - and deleting that would be a disaster."""
    qtw = sys.modules.get("PySide6.QtWidgets")
    if ours(type(obj).__module__):
        return True
    if qtw is None:
        return False
    try:
        return not isinstance(obj, qtw.QWidget)
    except RuntimeError:
        return False


def drop_qt_state(delete=None):
    """The QObjects our own module state holds: disconnected, then deleted.

    Measured: after everything else, `sys._skeldar_hubsound['devices']` was still a
    QMediaDevices connected to a Python function, `_skeldar_scenetabs['quit_filter']`
    an event filter on Maya's main window and `_skeldar_stash['timer']` a QTimer. Each
    is a sender whose destructor tears a connection to Python down - the crash."""
    if delete is None:
        shiboken = sys.modules.get("shiboken6")
        delete = getattr(shiboken, "delete", None)
    found = []
    seen = set()                 # one object held by two states is taken down once
    for name in sorted(n for n in dir(sys) if n.startswith("_skeldar")):
        _qt_in(getattr(sys, name, None), name, found, seen=seen)
    gone = []
    for path, obj in found:
        try:
            if not takeable(obj) or not _valid(obj):
                continue
            try:
                obj.disconnect()               # nothing of ours may fire on the way out
            except (RuntimeError, TypeError):
                pass
            if delete is not None:
                delete(obj)
            gone.append(path)
        except Exception:                                    # noqa: BLE001
            continue
    return gone


def forget_maya_wrappers(widgets=None, invalidate=None):
    """Tell shiboken to forget every wrapper we ever took of MAYA's own widgets.

    Measured 2026-11-02, and it inverted the diagnosis: of eleven throwaway Mayas,
    the four that crashed on quit were exactly the four that had ENUMERATED Maya's
    widgets mid-session (`QApplication.allWidgets()` / `topLevelWidgets()`, which
    makes a Python wrapper for every one of ~4800 Maya-owned widgets), and the seven
    that never did all quit clean - the animator's own full interface among them.
    Our plugin enumerates and wraps constantly while it runs (the window light's
    50 ms cursor poll, the viewport bar's and main bar's watches, every
    `maya_hubqt.find`), which is why the crash rate grew with the Qt surface.

    A wrapper of a Maya-owned widget is not ours to delete - the C++ belongs to Maya -
    so the only thing to hand back is shiboken's knowledge of it. Last of all, after
    ours are gone, and only at exit: invalidating a live wrapper mid-session would
    break whoever holds it (trap 96's hazard, deliberately taken only here)."""
    if invalidate is None:
        shiboken = sys.modules.get("shiboken6")
        invalidate = getattr(shiboken, "invalidate", None)
    if invalidate is None:
        return 0
    if widgets is None:
        widgets, app = _widgets()
        if app is None:
            return 0
    count = 0
    for widget in widgets:
        try:
            if ours(type(widget).__module__):
                continue
            invalidate(widget)
            count += 1
        except Exception:                                    # noqa: BLE001
            continue
    return count


def teardown(reason="Maya exiting", deep=False):
    """The whole cleanup. Safe to call twice, and safe when nothing of ours stands.

    `deep` is for Maya's exit alone: it destroys every widget of ours and the Qt our
    state holds, which an install must not do - it rebuilds the interface afterwards."""
    report = run()
    report["timers"] = stop_timers()
    report["windows"] = sweep_windows()
    if deep:
        report["widgets"] = sweep_widgets()
        report["state"] = drop_qt_state()
        report["forgotten"] = forget_maya_wrappers()
    if report["done"] or report["windows"] or report["timers"]:
        said = "%d step(s), %d timer(s), %d window(s)" % (
            len(report["done"]), report["timers"], len(report["windows"]))
        if deep:          # an install says nothing about what it deliberately keeps
            said += ", %d widget(s), %d held, %d wrapper(s) handed back" % (
                len(report.get("widgets") or []), len(report.get("state") or []),
                report.get("forgotten") or 0)
        if report["failed"]:
            said += "; refused: %s" % ", ".join(report["failed"])
        print("SkeldarAnim: took its Qt down before %s - %s" % (reason, said))
    return report


def _on_exiting(*_args):
    """Maya's kMayaExiting callback: it may never raise into Maya."""
    try:
        teardown("Maya exiting", deep=True)
    except Exception:                                        # noqa: BLE001
        print("SkeldarAnim shutdown failed\n%s" % traceback.format_exc())


def _api():
    import maya.api.OpenMaya as om
    return om


def arm(api=None):
    """Register the kMayaExiting hook once a session. True when this call did it.

    The id lives on `sys` (not in a module global) so an install that purges our
    modules cannot register a second one - trap 111's rule."""
    state = _state()
    if state.get("callback") is not None:
        return False
    api = api or _api()
    state["callback"] = api.MSceneMessage.addCallback(
        api.MSceneMessage.kMayaExiting, _on_exiting)
    return True


def disarm(api=None):
    """Take the hook off (an install does it before it purges, then arms again)."""
    state = _state()
    callback = state.get("callback")
    if callback is None:
        return False
    api = api or _api()
    try:
        api.MMessage.removeCallback(callback)
    finally:
        state["callback"] = None
    return True
