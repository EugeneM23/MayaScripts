"""Scene tabs: each tab's own undo history, as far as Maya's ONE queue allows
(2026-10-19, the animator: «Для каждой вкладки нужно реализовать свою историю
действий сейчас одна на все вкладки»).

Maya keeps one linear undo queue, so separate stacks are impossible: a tab's
steps made before another tab's work lie under that work. What this gives:

- a switch is no step: it runs outside the queue (`switching.switch`);
- entering a tab lays a FENCE when the queue's top is not already this tab's
  work - a recorded no-op chunk named `skeldarTabFence:<namespace>:<serial>`
  (a setAttr of a counter on the session node; Maya records no empty chunk);
- Ctrl+Z (any road: the hotkey, Edit > Undo, a script) that undoes a fence is
  redone at once from the Undo event, and the viewport says it is the start
  of this tab's history - it never reaches another tab's work and never
  switches tabs (measured 2026-10-19 in mayapy: a redo inside the Undo event
  callback holds, three undos in a row stayed on the fence);
- a tab left with nothing done in it has its fence taken back off the queue's
  top as it is left, so A -> B (nothing) -> A goes on with A's history;
- a fence redone from the redo queue in another tab is undone back the same way.

What is whose lives on `sys` (the queue is the session's, never saved).
`reset` after a flush (an import, an open): the queue is empty, its top the
active tab's. Spec: docs/superpowers/specs/2026-10-19-scene-tabs-undo-design.md
"""

import sys

PREFIX = "skeldarTabFence:"
COUNTER = "skeldarFence"            # the counter attribute on the session node

START = "Start of this tab's undo history"
UNDER = "Start of this tab's undo history - its earlier steps are under another tab's work"
UNDER_NAMED = "%s: start of undo here - earlier steps are under the work done in %s (Maya keeps one undo list)"
ENTERED = "%s: earlier undo steps are under the work done in %s - Ctrl+Z here starts from now"


# ------------------------------------------------------------------ pure

def fence_name(namespace, serial):
    return "%s%s:%d" % (PREFIX, namespace, serial)


def is_fence(name):
    return bool(name) and str(name).startswith(PREFIX)


def fence_tab(name):
    """The namespace a fence's name stands for ("" for anything else)."""
    if not is_fence(name):
        return ""
    return str(name)[len(PREFIX):].rsplit(":", 1)[0]


def plan_enter(fences, owner, leaving, entering, top):
    """(pop, lay) for a switch from `leaving` to `entering` with `top` the
    queue's top name: pop the leaving tab's fence when nothing was done on it
    (it is still the top), then lay a fence unless the work left on top is
    `entering`'s own. `fences` {name: {"ns", "below"}}, `owner` the tab whose
    work is on top (None unknown)."""
    record = fences.get(top) if top else None
    pop = bool(record) and record["ns"] == leaving
    after = record["below"] if pop else owner
    return pop, after != entering


def blocked_message(fences, name, title=None):
    """What Ctrl+Z says on a fence: whether this tab's work was on the queue
    before the fence was laid (then it lies under another tab's work, named
    through `title(namespace)` when given)."""
    record = fences.get(name) or {}
    if not record.get("earlier"):
        return START
    if title and record.get("ns") and record.get("below"):
        return UNDER_NAMED % (title(record["ns"]), title(record["below"]))
    return UNDER


def entered_message(record, title):
    """What entering a tab says when its history went under another tab's work ("" otherwise)."""
    if not record or not record.get("earlier") or not record.get("below"):
        return ""
    return ENTERED % (title(record["ns"]), title(record["below"]))


def _serial(name):
    try:
        return int(str(name).rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return -1


# ------------------------------------------------------------------ state

def state():
    st = getattr(sys, "_skeldar_tabundo", None)
    if st is None:
        st = {"fences": {}, "owner": None, "seen": set(), "serial": 0, "inside": False,
              "callbacks": [], "handler": None}
        sys._skeldar_tabundo = st
    st.setdefault("seen", set())
    return st


def reset(owner):
    """The queue flushed: nothing on it is fenced, its top (empty) is `owner`'s."""
    st = state()
    st["fences"] = {}
    st["owner"] = owner
    st["seen"] = {owner} if owner else set()


# ------------------------------------------------------------------ the scene

def _cmds():
    import maya.cmds as cmds
    return cmds


def recording(cmds=None):
    cmds = cmds or _cmds()
    return bool(cmds.undoInfo(q=True, state=True)) and bool(cmds.undoInfo(q=True, stateWithoutFlush=True))


def before_switch(leaving, entering, cmds=None):
    """Called before the switch's unrecorded work: pops the leaving tab's fence
    when nothing was done on it. Returns True when `after_switch` must lay a
    fence for `entering`. Does nothing (False) while the queue is not recording."""
    cmds = cmds or _cmds()
    if not recording(cmds):
        return False
    install(cmds)
    st = state()
    top = cmds.undoInfo(q=True, undoName=True) or ""
    pop, lay = plan_enter(st["fences"], st["owner"], leaving, entering, top)
    if pop:
        record = st["fences"].pop(top)
        st["inside"] = True
        try:
            cmds.undo()
        finally:
            st["inside"] = False
        st["owner"] = record["below"]
    return lay


def after_switch(entering, session_node, cmds=None):
    """Lays the fence for `entering` (one recorded chunk)."""
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
    name = fence_name(entering, st["serial"])
    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        cmds.setAttr(plug, st["serial"])
    finally:
        cmds.undoInfo(closeChunk=True)
    record = {"ns": entering, "below": st["owner"], "earlier": entering in st["seen"]}
    st["fences"][name] = record
    st["owner"] = entering
    st["seen"].add(entering)
    said = entered_message(record, _title)
    if said:
        _say(said, cmds)
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


def _say(message, cmds):
    print(message)
    if not cmds.about(batch=True):
        try:
            cmds.inViewMessage(assistMessage=message, position="topCenter", fade=True, fadeStayTime=3000)
        except Exception:                                       # noqa: BLE001
            pass


def on_undo(*_):
    """An undo that took a fence off: redo it."""
    st = state()
    if st["inside"]:
        return
    cmds = _cmds()
    name = cmds.undoInfo(q=True, redoName=True) or ""
    if not is_fence(name):
        return
    st["inside"] = True
    try:
        cmds.redo()
    finally:
        st["inside"] = False
    _say(blocked_message(st["fences"], name, _title), cmds)


def on_redo(*_):
    """A redo that put another tab's fence back on: undo it."""
    st = state()
    if st["inside"]:
        return
    cmds = _cmds()
    name = cmds.undoInfo(q=True, undoName=True) or ""
    if not is_fence(name) or fence_tab(name) == _active():
        return
    st["inside"] = True
    try:
        cmds.undo()
    finally:
        st["inside"] = False
    _say("Nothing to redo in this tab", cmds)


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
