"""Scene tabs: one undo history for every tab, where nothing is lost (2026-10-19).

The animator asked first for each tab's own history («Для каждой вкладки нужно
реализовать свою историю действий»). Maya keeps ONE linear undo queue, so two
histories that both go on after edits in the other tab cannot exist in one Maya:
a tab boundary was built, and in use every visit buried the tab before it (they
key and move in both tabs). Asked again, they chose one shared history where
nothing is lost («Общая история, ничего не терять»). What this gives:

- a switch runs outside the queue (`switching.switch`) and leaves a MARKER on it:
  a recorded chunk named `skeldarTabSwitch:<from>:<to>:<serial>`, a setAttr of a
  counter on the session node (Maya records no empty chunk);
- Ctrl+Z (any road) that undoes a marker switches to the tab it came from and
  undoes that tab's last step in the same press, saying so in the viewport; Redo
  that redoes a marker switches to the tab it led to and redoes the step after it.
  So one press is always one real step, wherever it was made (measured in mayapy:
  an undo or redo inside the Undo / Redo event callback holds);
- leaving a tab takes the steps that only LOOKED off the queue (MEL selections
  and time changes on its marker, `_drop_selection`), and a tab left with nothing
  done has its marker taken back (`plan_enter`): A -> B (only looked) -> A leaves
  nothing, and Ctrl+Z never walks into a tab for somebody's click;
- a marker popped that way is not redone (`on_redo` takes it back).

What is whose lives on `sys` (the queue is the session's, never saved). `reset`
after a flush (an import, an open): the queue is empty, its top the active tab's.
Spec: docs/superpowers/specs/2026-10-19-scene-tabs-undo-design.md
"""

import sys

PREFIX = "skeldarTabSwitch:"
LEGACY = "skeldarTabFence:"         # the boundary build's fences: which tab lay below is unknown
COUNTER = "skeldarFence"            # the counter attribute on the session node

UNDO_IN = "Undo in %s"
REDO_IN = "Redo in %s"
OLDER = "Older steps are from before the tabs update - Ctrl+Z stops here"


# ------------------------------------------------------------------ pure

def marker_name(leaving, entering, serial):
    return "%s%s:%s:%d" % (PREFIX, leaving, entering, serial)


def is_marker(name):
    return bool(name) and str(name).startswith(PREFIX)


def is_legacy(name):
    return bool(name) and str(name).startswith(LEGACY)


def marker_tabs(name):
    """(from, to) of a marker's name, ("", "") for anything else."""
    if not is_marker(name):
        return "", ""
    parts = str(name)[len(PREFIX):].split(":")
    if len(parts) != 3:
        return "", ""
    return parts[0], parts[1]


SELECTION = ("select", "selectKey", "hilite", "currentTime")


def is_selection(name):
    """A step that only LOOKS: a MEL selection (a click in a viewport, the Outliner,
    the Graph Editor) or a time change (`currentTime -e`, Maya's frame hotkeys -
    measured 2026-10-19: in a GUI Maya a time change is an undo step), by its undo
    name. A Python `cmds.select` / `cmds.currentTime` is unnamed (''), and stays unknown."""
    words = str(name or "").split(None, 1)
    return bool(words) and words[0] in SELECTION


def plan_enter(markers, owner, leaving, entering, top):
    """(pop, lay) for a switch from `leaving` to `entering` with `top` the queue's
    top name: pop the marker that led into `leaving` when nothing was done there
    (it is still the top), then lay a marker unless the steps left on top are
    `entering`'s own. `markers` {name: {"from", "to", "below"}}, `owner` the tab
    whose steps are on top (None unknown)."""
    record = markers.get(top) if top else None
    pop = bool(record) and record.get("to") == leaving
    after = record.get("below") if pop else owner
    return pop, after != entering


def say_step(template, title, step):
    """«Undo in attack: move -r 1 0 0» - the step's name when Maya gave it one."""
    text = template % title
    return text + (": " + step.strip() if step and step.strip() else "")


def _serial(name):
    try:
        return int(str(name).rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return -1


# ------------------------------------------------------------------ state

def state():
    st = getattr(sys, "_skeldar_tabundo", None)
    if st is None or "markers" not in st:
        old = st or {}
        st = {"markers": {}, "owner": None, "popped": set(), "serial": old.get("serial", 0),
              "inside": False, "callbacks": old.get("callbacks", []), "handler": old.get("handler")}
        sys._skeldar_tabundo = st
    return st


def reset(owner):
    """The queue flushed: no marker is on it, its top (empty) is `owner`'s."""
    st = state()
    st["markers"] = {}
    st["popped"] = set()
    st["owner"] = owner


# ------------------------------------------------------------------ the scene

def _cmds():
    import maya.cmds as cmds
    return cmds


def recording(cmds=None):
    cmds = cmds or _cmds()
    return bool(cmds.undoInfo(q=True, state=True)) and bool(cmds.undoInfo(q=True, stateWithoutFlush=True))


def before_switch(leaving, entering, cmds=None):
    """Called before the switch's unrecorded work: the leaving tab's looking steps
    off, its marker popped when nothing was done there. Returns True when
    `after_switch` must lay a marker. Does nothing (False) while not recording."""
    cmds = cmds or _cmds()
    if not recording(cmds):
        return False
    install(cmds)
    st = state()
    top = _drop_selection(leaving, cmds)
    pop, lay = plan_enter(st["markers"], st["owner"], leaving, entering, top)
    if pop:
        record = st["markers"].pop(top)
        st["inside"] = True
        try:
            cmds.undo()
        finally:
            st["inside"] = False
        st["popped"].add(top)
        st["owner"] = record.get("below")
    return lay


def _drop_selection(leaving, cmds):
    """The queue's top after taking off the leaving tab's steps that only looked
    (`is_selection`) from the top of the queue, down to its first real step or a
    marker (2026-10-19: a click in a tab is a `select` step, a frame change a
    `currentTime` one - left on, Ctrl+Z from another tab would come back here to
    undo a click). The selection and the frame shown are put back unrecorded:
    `switching.leave` records them."""
    st = state()
    top = cmds.undoInfo(q=True, undoName=True) or ""
    if st["owner"] != leaving or not is_selection(top):
        return top
    shown = cmds.ls(selection=True, long=True) or []
    frame = cmds.currentTime(q=True)
    undone = 0
    st["inside"] = True
    try:
        while is_selection(cmds.undoInfo(q=True, undoName=True) or ""):
            cmds.undo()
            undone += 1
    finally:
        st["inside"] = False
    if undone:
        was = cmds.undoInfo(q=True, stateWithoutFlush=True)
        cmds.undoInfo(stateWithoutFlush=False)
        try:
            found = cmds.ls(shown, long=True) or []
            cmds.select(found, replace=True) if found else cmds.select(clear=True)
            if cmds.currentTime(q=True) != frame:
                cmds.currentTime(frame, edit=True)
        finally:
            cmds.undoInfo(stateWithoutFlush=was)
    return cmds.undoInfo(q=True, undoName=True) or ""


def after_switch(leaving, entering, session_node, cmds=None):
    """Lays the marker of a switch from `leaving` to `entering` (one recorded chunk)."""
    cmds = cmds or _cmds()
    if not recording(cmds) or not cmds.objExists(session_node):
        return ""
    st = state()
    plug = session_node + "." + COUNTER
    if not cmds.attributeQuery(COUNTER, node=session_node, exists=True):
        was = cmds.undoInfo(q=True, stateWithoutFlush=True)
        cmds.undoInfo(stateWithoutFlush=False)
        try:
            cmds.addAttr(session_node, longName=COUNTER, attributeType="long")
        finally:
            cmds.undoInfo(stateWithoutFlush=was)
    st["serial"] += 1
    name = marker_name(leaving, entering, st["serial"])
    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        cmds.setAttr(plug, st["serial"])
    finally:
        cmds.undoInfo(closeChunk=True)
    st["markers"][name] = {"from": leaving, "to": entering, "below": st["owner"]}
    st["owner"] = entering
    return name


def _title(namespace):
    """A tab's name as the bar shows it."""
    try:
        from . import records, session
        item = records.tab(session.state(), namespace)
        return records.title(dict(item, modified=False)) if item else namespace
    except Exception:                                           # noqa: BLE001
        return namespace


def _active():
    try:
        from . import session
        return session.state()["active"] if session.exists() else ""
    except Exception:                                           # noqa: BLE001
        return ""


def _tabs():
    try:
        from . import session
        return [t["ns"] for t in session.state()["tabs"]] if session.exists() else []
    except Exception:                                           # noqa: BLE001
        return []


def _go(namespace):
    """The tab shown, outside the history (no marker, no pop)."""
    if not namespace or namespace == _active() or namespace not in _tabs():
        return False
    from . import switching
    switching.switch(namespace, history=False)
    return True


def _say(message, cmds):
    print(message)
    if not cmds.about(batch=True):
        try:
            cmds.inViewMessage(assistMessage=message, position="topCenter", fade=True, fadeStayTime=2500)
        except Exception:                                       # noqa: BLE001
            pass


def on_undo(*_):
    """An undo that took a marker off: the tab it came from shown, and that tab's
    last step undone in the same press (markers in a row crossed the same way)."""
    st = state()
    if st["inside"]:
        return
    cmds = _cmds()
    name = cmds.undoInfo(q=True, redoName=True) or ""
    if is_legacy(name):
        #  a boundary-build fence (an update mid-session): the steps under it may be a
        #  hidden tab's, and which one is not known - undoing past it would change a tab
        #  nobody sees. Put back, and say so.
        st["inside"] = True
        try:
            cmds.redo()
        finally:
            st["inside"] = False
        _say(OLDER, cmds)
        return
    if not is_marker(name):
        return
    st["inside"] = True
    step, shown = "", _active()
    try:
        for _ in range(256):
            source, _target = marker_tabs(name)
            if _go(source):
                shown = source
            try:
                cmds.undo()
            except RuntimeError:                    # nothing left to undo
                break
            name = cmds.undoInfo(q=True, redoName=True) or ""
            if not is_marker(name):
                step = name
                break
    finally:
        st["inside"] = False
    st["owner"] = shown
    _say(say_step(UNDO_IN, _title(shown), step), cmds)


def on_redo(*_):
    """A redo that put a marker back: the tab it led to shown, and the step after
    it redone in the same press. A marker a switch popped is taken back off."""
    st = state()
    if st["inside"]:
        return
    cmds = _cmds()
    name = cmds.undoInfo(q=True, undoName=True) or ""
    if not is_marker(name):
        return
    st["inside"] = True
    step, shown = "", _active()
    try:
        if name in st["popped"]:
            cmds.undo()                             # a visit that left nothing: not history
            _say("Nothing to redo", cmds)
            return
        for _ in range(256):
            _source, target = marker_tabs(name)
            if _go(target):
                shown = target
            try:
                cmds.redo()
            except RuntimeError:                    # nothing left to redo
                break
            name = cmds.undoInfo(q=True, undoName=True) or ""
            if not is_marker(name) or name in st["popped"]:
                step = "" if is_marker(name) else name
                break
    finally:
        st["inside"] = False
    st["owner"] = shown
    _say(say_step(REDO_IN, _title(shown), step), cmds)


def install(cmds=None):
    """The Undo / Redo callbacks, once (again after an update: the old module's
    functions are taken off)."""
    st = state()
    if st["callbacks"] and st.get("handler") is on_undo:
        return
    remove()
    import maya.api.OpenMaya as om
    st["callbacks"] = [om.MEventMessage.addEventCallback("Undo", on_undo),
                       om.MEventMessage.addEventCallback("Redo", on_redo)]
    st["handler"] = on_undo


def remove():
    st = state()
    if st["callbacks"]:
        try:
            import maya.api.OpenMaya as om
            for cid in st["callbacks"]:
                try:
                    om.MMessage.removeCallback(cid)
                except Exception:                               # noqa: BLE001
                    pass
        except Exception:                                       # noqa: BLE001
            pass
    st["callbacks"] = []
    st["handler"] = None
