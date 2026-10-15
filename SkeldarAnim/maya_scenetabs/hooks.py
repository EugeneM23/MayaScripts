"""Scene tabs: Maya's own Save, Open and New redirected while two or more tabs
are open; a new animation layer put under the active tab's root; the bar kept
in step with Undo, Redo and a scene opened; a quit that asks about unsaved
tabs.

The checks return False (Maya then prints «File operation cancelled by user
supplied callback») and do the tab's work one idle later. The Save check has
no file variant (kInvalidParameter, measured) and reads the target from the
scene name, which Save As has already set; the Open check gets the file
(`(MFileObject, clientData) -> bool`). State on `sys._skeldar_scenetabs`
(trap 111). `executeDeferred` never runs in mayapy, so `defer` has a seam.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import sys
import tempfile
import traceback

import maya.cmds as cmds

from . import records, session


def _st():
    state = getattr(sys, "_skeldar_scenetabs", None)
    if state is None:
        state = {"callbacks": [], "jobs": [], "bypass": 0, "defer": None, "quit_filter": None}
        sys._skeldar_scenetabs = state
    return state


def defer(fn):
    hook = _st()["defer"]
    if hook is not None:
        return hook(fn)
    import maya.utils
    maya.utils.executeDeferred(fn)
    return None


class bypass(object):
    """Our own file -open / -new / -save pass the checks."""

    def __enter__(self):
        _st()["bypass"] += 1
        return self

    def __exit__(self, *exc):
        _st()["bypass"] -= 1
        return False


def _bypassed():
    return _st()["bypass"] > 0


def _say(message):
    if not message:
        return
    try:
        from . import bar
        bar.say(message)
        bar.refresh()
    except Exception:                                           # noqa: BLE001
        print("Scene Tabs: " + message)


def _reported(fn):
    def run():
        try:
            _say(fn())
        except Exception as exc:                                # noqa: BLE001
            print(traceback.format_exc())
            _say("Scene Tabs: %s" % exc)
    return run


def _refused(what, exc):
    """A check callback that failed refuses the operation: nothing is written,
    the tabs are not replaced; the reason reaches the bar."""
    print(traceback.format_exc())
    _say("Scene Tabs: %s refused - %s (Tabs off in the bar's menu turns the tabs off)" % (what, exc))
    return False


def _checked(what):
    def wrap(fn):
        def check(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:                            # noqa: BLE001
                return _refused(what, exc)
        check.__name__ = fn.__name__
        check.__doc__ = fn.__doc__
        return check
    return wrap


def _untitled_save():
    """Tabs off: a scene still named as one of our session files is untitled
    (Maya cannot rename a scene back to untitled), so Save asks for a name
    instead of writing into SkeldarTabs (2026-10-15)."""
    if session.exists():
        return True
    target = (cmds.file(q=True, sceneName=True) or "").replace("\\", "/")
    from . import opening
    if not records.is_session_file(target, opening.folder()):
        return True

    def save_as():
        import maya.mel as mel
        mel.eval("SaveSceneAs")
    defer(_reported(save_as))
    return False


@_checked("Save")
def on_save(client_data=None):
    if _bypassed():
        return True
    if not session.is_on():
        return _untitled_save()
    target = (cmds.file(q=True, sceneName=True) or "").replace("\\", "/")
    try:
        autosave = cmds.autoSave(q=True, destinationFolder=True) or ""
    except RuntimeError:
        autosave = ""
    if records.is_autosave(target, autosave) or records.is_emergency(target, tempfile.gettempdir()):
        return True                 # an autosave, or Maya's emergency save on a crash
    state = session.state()
    action, path = records.save_plan(target, state.get("session", ""))
    if state.get("session"):
        cmds.file(rename=state["session"])
    from . import saving
    if action == "save":
        defer(_reported(lambda: saving.save_tab()))
    else:
        defer(_reported(lambda: saving.save_tab(path=path)))
    return False


@_checked("Open")
def on_open(file_obj, client_data=None):
    if _bypassed() or not session.is_on():
        return True
    path = (file_obj.resolvedFullName() or file_obj.rawFullName() or "").replace("\\", "/")
    from . import opening
    defer(_reported(lambda: opening.open_any(path)))
    return False


@_checked("New")
def on_new(client_data=None):
    if _bypassed() or not session.is_on():
        return True
    from . import opening
    defer(_reported(opening.new_tab))
    return False


def restored_here():
    """opening.open_any restored the session itself; the SceneOpened job that
    follows (possibly after bypass is gone) must not restore it again. A job
    that already fired inside the bypass (`seen`, synchronous) needs no flag;
    otherwise it is set, and only where a job exists to consume it."""
    state = _st()
    if state.pop("seen", False):
        return
    if state["jobs"]:
        state["restored"] = True


def opening_session():
    """open_any is about to open a session file: forget a job seen before."""
    _st().pop("seen", None)


def on_layer(node, client_data=None):
    """Called as the node is created, before the command names and parents it:
    the layer is followed by its UUID and adopted one idle later."""
    if _bypassed() or not session.exists():
        return
    import maya.api.OpenMaya as om
    uid = om.MFnDependencyNode(node).uuid().asString()

    def later():
        from . import layers
        found = cmds.ls(uid) or []
        if session.exists() and found:
            layers.adopt(found[0], session.state()["active"])
    defer(later)


def _refresh_bar():
    try:
        from . import bar
        bar.refresh()
    except Exception:                                           # noqa: BLE001
        pass


def _undone():
    """Undo / Redo: the bar and the Layer Editor (a switch undone brings the other
    tab's layers back in; the editors do not notice by themselves)."""
    _refresh_bar()
    try:
        from . import layers
        layers.refresh_editors()
    except Exception:                                           # noqa: BLE001
        pass


def _scene_opened():
    """A scene opened by any road: a session file brings its tabs back."""
    state = _st()
    if _bypassed():
        state["seen"] = True
        return
    if state.pop("restored", False):
        return
    if session.exists():
        from . import opening

        def later():
            if state.pop("restored", False):
                return
            return opening.restore()
        defer(_reported(later))
    else:
        _refresh_bar()


def _install_quit_filter():
    import maya_hubqt
    q = maya_hubqt.qt()
    if q is None:
        return
    import maya.OpenMayaUI as omui
    window = q.shiboken.wrapInstance(int(omui.MQtUtil.mainWindow()), q.QtWidgets.QWidget)

    class QuitFilter(q.QtCore.QObject):
        def eventFilter(self, obj, event):
            if event.type() == q.QtCore.QEvent.Close:
                from . import opening
                try:
                    if not opening.quit_ok():
                        event.ignore()
                        return True
                except Exception:                               # noqa: BLE001
                    print(traceback.format_exc())
            return False

    keeper = QuitFilter(window)
    window.installEventFilter(keeper)
    _st()["quit_filter"] = (keeper, window)


def install(force=False):
    """The callbacks (and in a GUI the jobs and the quit filter), once. After
    an update reloaded this module the registered ones are the OLD module's
    functions (the state lives on `sys`): they are removed and these installed."""
    if cmds.about(batch=True) and not force:
        return False
    state = _st()
    if state["callbacks"] and state.get("owner") is on_save:
        return True
    if state["callbacks"] or state["jobs"] or state["quit_filter"]:
        remove()
    state["owner"] = on_save
    import maya.api.OpenMaya as om
    try:
        state["callbacks"].append(om.MSceneMessage.addCheckCallback(om.MSceneMessage.kBeforeSaveCheck, on_save))
        state["callbacks"].append(
            om.MSceneMessage.addCheckFileCallback(om.MSceneMessage.kBeforeOpenCheck, on_open))
        state["callbacks"].append(om.MSceneMessage.addCheckCallback(om.MSceneMessage.kBeforeNewCheck, on_new))
        state["callbacks"].append(om.MDGMessage.addNodeAddedCallback(on_layer, "animLayer"))
    except Exception:
        remove()
        raise
    if not cmds.about(batch=True):
        state["jobs"] = [cmds.scriptJob(event=("Undo", _undone)),
                         cmds.scriptJob(event=("Redo", _undone)),
                         cmds.scriptJob(event=("SceneOpened", _scene_opened))]
        try:
            _install_quit_filter()
        except Exception:                                       # noqa: BLE001
            print(traceback.format_exc())
    return True


def remove():
    state = _st()
    if state["callbacks"]:
        import maya.api.OpenMaya as om
        for callback in state["callbacks"]:
            try:
                om.MMessage.removeCallback(callback)
            except RuntimeError:
                pass
    for job in state["jobs"]:
        try:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        except RuntimeError:
            pass
    if state["quit_filter"]:
        keeper, window = state["quit_filter"]
        try:
            window.removeEventFilter(keeper)
        except RuntimeError:
            pass
    state.update(callbacks=[], jobs=[], quit_filter=None, defer=None, owner=None)
