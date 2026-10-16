"""Scene tabs: the open scene becoming tab 1, opening a file into a tab, an
empty tab, closing, reloading, back to one scene, a saved session restored,
tabs off, and the question on quit.

Imports run with `preserveReferences=True` (a nested reference stays one) and
`executeScriptNodes=False` (an import otherwise runs a file's open-type script
nodes - measured). An import flushes Maya's undo, as opening a file does.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import os
import subprocess
import time

import maya.cmds as cmds

from . import layers, records, session, switching

ASK = None          # seam: callable(message, buttons) -> the button picked
NOTES = []          # what tidying a file found, said by the press that opened it
CHANGED = []        # the tabs tidying changed: they open flagged, so a save writes the clean file


def _quiet(fn):
    """`fn` run outside the undo queue, the queue flushed after (an import
    flushes it anyway): a Ctrl+Z could otherwise walk into a half-made tab -
    a session node that no longer matches the namespaces, a `file -rename` or
    a removed reference that undo does not take back. Never inside an open
    chunk (trap 145): these run from the bar, the hooks, the hub. A cancel
    (`session.Cancelled`) changed nothing and keeps the animator's queue.
    Busy meanwhile: the bar ignores its clicks."""
    def run(*args, **kwargs):
        recording = cmds.undoInfo(q=True, stateWithoutFlush=True)
        cmds.undoInfo(stateWithoutFlush=False)
        result = None
        try:
            with session.busy():
                result = fn(*args, **kwargs)
            return result
        finally:
            cmds.undoInfo(stateWithoutFlush=recording)
            if recording and not isinstance(result, session.Cancelled):
                cmds.flushUndo()
    run.__name__ = fn.__name__
    run.__doc__ = fn.__doc__
    return run


def _busy(fn):
    """`fn` run with the bar's clicks ignored (it may ask a question)."""
    def run(*args, **kwargs):
        with session.busy():
            return fn(*args, **kwargs)
    run.__name__ = fn.__name__
    run.__doc__ = fn.__doc__
    return run


def _ask(message, buttons, default):
    if ASK is not None:
        return ASK(message, buttons)
    if cmds.about(batch=True):
        return default
    return cmds.confirmDialog(title="Scene Tabs", message=message, button=list(buttons),
                              defaultButton=buttons[0], cancelButton=buttons[-1],
                              dismissString=buttons[-1])


def folder():
    path = os.path.join(cmds.internalVar(userAppDir=True), "SkeldarTabs").replace("\\", "/")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _taken():
    return cmds.namespaceInfo(":", listOnlyNamespaces=True) or []


def _mtime(path):
    return os.path.getmtime(path) if path and os.path.isfile(path) else 0.0


@_quiet
def start():
    """The open scene becomes tab 1: its layer root to the session, its content
    into its own namespace, the scene renamed to the session's file. Returns
    the state (unchanged when tabs are on already). A failure half way puts
    the scene back as it was (its content in the root, its layer root's name)
    and re-raises."""
    state = session.state()
    if state["tabs"]:
        return state
    scene = (cmds.file(q=True, sceneName=True) or "").replace("\\", "/")
    if records.is_session_file(scene, folder()):
        scene = ""          # an untitled scene back from tabs keeps the session's name: untitled
    namespace = records.namespace_for(scene or records.UNTITLED, _taken())
    first = records.new_tab(namespace, scene, cmds.currentUnit(q=True, time=True),
                            session.current_ranges(), _mtime(scene))
    first["frame"] = cmds.currentTime(q=True)
    first["modified"] = bool(cmds.file(q=True, modified=True))
    root_name = layers.root().split(":")[-1]
    try:
        children = layers.take_root()
        session.move_into(namespace)
        layers.give_children(namespace, children)
        _tidy_file(namespace, os.path.basename(scene) or "The scene")
        first["modified"] = first["modified"] or namespace in CHANGED
    except Exception:
        try:
            layers.give_back(namespace, root_name)
        finally:
            if cmds.namespace(exists=":" + namespace):
                session.move_out(namespace)
            cmds.namespace(setNamespace=":")
        raise
    state = records.empty_state()
    state["tabs"], state["active"] = [first], namespace
    state["session"] = records.session_name(folder(), time.strftime("%Y%m%d_%H%M%S"))
    session.write(state)
    cmds.namespace(setNamespace=":" + namespace)
    cmds.file(rename=state["session"])
    #  the moves into the namespace flagged the scene: tab 1 is as modified as the scene was
    cmds.file(modified=first["modified"])
    return state


def _sweep(namespace):
    """The imported file's ui configuration node and any vaccine malware node
    deleted (never run: the import did not execute script nodes)."""
    from maya_scenesetup import character
    #  by type, never every node by its short name: a file holding two DAG nodes of one
    #  name (OverRig's `fin_jnt11` in every rig) lists a short name that matches no
    #  single node, and nodeType raised - the tab did not open (2026-10-15, live)
    scripts = [s for s in session.typed(namespace, "script")
               if not cmds.referenceQuery(s, isNodeReferenced=True)]
    doomed = character.malware_nodes(scripts) + [
        s for s in scripts if s.split(":")[-1] == "uiConfigurationScriptNode"]
    for node in doomed:
        if cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    return doomed


def leaked_tabs(namespace):
    """Tabs an old save wrote into this tab's file, hidden (2026-10-16, live: a whole other tab
    with its Manny rig and layers in AS_DG_ATK_JA_04.ma): a child namespace named like a tab
    that holds our hide state - a layer's stored links, a set we hid. Nothing else carries it,
    so a rig the animator pasted from another tab (shown, `fold_pasted`) is never one.
    Returns [(leaf, node count)]."""
    out = []
    for child in session.child_namespaces(namespace):
        if not child.startswith(records.TAB_PREFIX):
            continue
        nodes = cmds.namespaceInfo(":%s:%s" % (namespace, child), listOnlyDependencyNodes=True,
                                   recurse=True) or []
        marked = [n for n in cmds.ls(nodes, type=("animLayer", "displayLayer", "objectSet")) or []
                  if cmds.attributeQuery(layers.OUT_ATTR, node=n, exists=True)
                  or cmds.attributeQuery(switching.SET_MARK, node=n, exists=True)]
        if marked:
            out.append((child, len(nodes)))
    return out


def _tidy_file(namespace, name):
    """A file's leftovers of the session that wrote it: another tab an old save wrote into it
    (removed when the animator says so), its layers' stored links, a copy of the session root
    and layers hanging on ours. The note goes to NOTES and the Script Editor. A tab the
    animator had removed is put in CHANGED: it opens flagged (2026-10-16, live - opened clean,
    nothing asked for a save, and the question came back on every open)."""
    leaked = leaked_tabs(namespace)
    if leaked:
        listed = ", ".join("%s (%d nodes)" % (child, count) for child, count in leaked)
        answer = _ask("%s holds another tab, hidden: %s. An old save of Scene Tabs wrote it into "
                      "this file. Remove it from this tab?" % (name, listed), ("Remove", "Keep"), "Keep")
        if answer == "Remove":
            for child, _ in leaked:
                #  node by node, as a closed tab goes: `namespace -deleteNamespaceContent` over
                #  its detached layers corrupted Maya's heap (0xc0000374 on the next file op)
                _remove_namespace("%s:%s" % (namespace, child))
            note = ("removed another tab an old save wrote into %s: %s - save this tab to clean "
                    "the file" % (name, listed))
            CHANGED.append(namespace)
        else:
            note = "%s holds another tab an old save wrote into it: %s (kept)" % (name, listed)
        NOTES.append(note)
        print("Scene Tabs: " + note)
    #  the hide state of the session that wrote the file is not this session's: its stored
    #  links named nodes that are not here, and the file did not open (2026-10-16, live)
    layers.forget_stored(namespace)
    layers.tidy_imported(namespace)


def _notes(message):
    found = " | ".join(NOTES)
    del NOTES[:]
    del CHANGED[:]
    return message + (" | " + found if found else "")


def _ranges_of(namespace):
    node = ":%s:%s" % (namespace, records.CONFIG_NODE)
    if not cmds.objExists(node):
        return {}
    return records.ranges_from_script(cmds.getAttr(node + ".before") or "")


def _import(path, namespace):
    """`path` imported into `namespace` in its own unit. Returns (unit, ranges)."""
    ext = os.path.splitext(path)[1].lower()
    unit = records.read_unit(path) or cmds.currentUnit(q=True, time=True)
    layers.ensure_root()
    cmds.currentUnit(time=unit, updateAnimation=True)
    cmds.namespace(setNamespace=":")
    cmds.file(path, i=True, type=records.FILE_TYPES[ext], namespace=namespace,
              preserveReferences=True, executeScriptNodes=False, mergeNamespacesOnClash=False,
              ignoreVersion=True)
    _sweep(namespace)
    _tidy_file(namespace, os.path.basename(path))
    return unit, (_ranges_of(namespace) or session.current_ranges())


def _check(path):
    path = (path or "").replace("\\", "/")
    if os.path.splitext(path)[1].lower() not in records.FILE_TYPES:
        raise session.TabError("only Maya scenes open in a tab (.ma, .mb): %s" % os.path.basename(path))
    if not os.path.isfile(path):
        raise session.TabError("no such file: %s" % path)
    return path


def _back_to(before, namespace):
    """A new tab that failed half way: what it made removed, the tab that was
    active entered again with its own modified flag, the session written; a
    session `start` made only now goes back to one scene."""
    try:
        _delete_namespace(namespace)
    except Exception:                                           # noqa: BLE001
        print("Scene Tabs: the failed tab %s could not be removed whole" % namespace)
    previous = records.tab(before, before["active"]) or {}
    for item in before["tabs"]:
        if item["ns"] != before["active"]:
            switching.hide(item["ns"])
    try:
        switching.enter(before, before["active"])
    finally:
        session.write(before)
        cmds.file(modified=bool(previous.get("modified")))
    if len(before["tabs"]) < 2:
        finish()


def _new(state, namespace, make, index=None):
    """Leave the active tab, `make()` the new tab's content (returns its
    record), enter it. A failure goes back (`_back_to`) and re-raises."""
    before = switching.leave(state)
    try:
        state = records.with_tab(before, make(), index)
        state = switching.enter(state, namespace, fresh=True)
        session.write(state)
        switching.settle_flag(state)
    except Exception:
        _back_to(before, namespace)
        raise
    return state


@_quiet
def open_tab(path, index=None):
    """`path` into a new tab (the open scene becomes tab 1 first)."""
    path = _check(path)
    del NOTES[:], CHANGED[:]
    state = start()
    namespace = records.namespace_for(path, _taken())
    done = {}

    def make():
        done["unit"], done["ranges"] = _import(path, namespace)
        item = records.new_tab(namespace, path, done["unit"], done["ranges"], _mtime(path))
        #  its file's persp / top / front / side: an import leaves the scene's (measured)
        item["cameras"] = switching.file_cameras(path)
        return item
    _new(state, namespace, make, index)
    cmds.file(modified=namespace in CHANGED)
    return _notes("Opened %s in a tab (%s, %s)" % (os.path.basename(path), done["unit"],
                                                   records.range_text(done["ranges"])))


@_busy
def open_any(path):
    """Maya's own Open while tabs are on: a saved session replaces the tabs
    (after asking about unsaved ones), any other scene opens in a new tab."""
    path = _check(path)
    if not records.holds_session(path):
        return open_tab(path)
    if not quit_ok():
        return "Open cancelled - the tabs are as they were"
    from . import hooks
    hooks.opening_session()
    with hooks.bypass():
        cmds.file(path, open=True, force=True)
    message = restore()
    hooks.restored_here()
    return message


@_quiet
def new_tab():
    """An empty tab (its first Save asks for a path)."""
    del NOTES[:], CHANGED[:]
    state = start()
    namespace = records.namespace_for(records.UNTITLED, _taken())

    def make():
        cmds.namespace(add=namespace, parent=":")
        item = records.new_tab(namespace, "", cmds.currentUnit(q=True, time=True), session.current_ranges())
        item["cameras"] = switching.default_cameras()      # a new scene's, not the last tab's
        return item
    _new(state, namespace, make)
    return _notes("New empty tab")


def _remove_namespace(namespace):
    """Every node of the namespace that can be deleted deleted; what Maya will
    not delete (the managers the first import into an empty scene makes inside
    the namespace, trap 158) merged into the root; the namespaces removed
    deepest first. `namespace -deleteNamespaceContent` dies on those managers
    («is locked, can not remove it», measured in the plan's own verify)."""
    if not cmds.namespace(exists=":" + namespace):
        return
    nodes = cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, recurse=True, dagPath=True) or []
    for node in nodes:
        if cmds.objExists(node) and not cmds.referenceQuery(node, isNodeReferenced=True):
            try:
                cmds.lockNode(node, lock=False)
            except RuntimeError:
                pass
    for node in nodes:
        if cmds.objExists(node) and not cmds.referenceQuery(node, isNodeReferenced=True):
            try:
                cmds.delete(node)
            except (RuntimeError, ValueError):
                pass
    found = cmds.namespaceInfo(":" + namespace, listOnlyNamespaces=True, recurse=True) or []
    for child in sorted(found, key=lambda name: -name.count(":")) + [namespace]:
        if cmds.namespace(exists=":" + child.lstrip(":")):
            cmds.namespace(removeNamespace=":" + child.lstrip(":"), mergeNamespaceWithRoot=True)


def _delete_namespace(namespace):
    """The tab's blend nodes brought home, its references removed BY NODE (a
    path is ambiguous between two tabs of one file - the wrong copy went,
    measured), then its namespace and everything in it."""
    layers.home_blends(namespace)
    for uid, _ in session.top_references(namespace):
        found = cmds.ls(uid) or []
        if found:
            cmds.file(referenceNode=found[0], removeReference=True)
    _remove_namespace(namespace)


def _is_modified(state, item):
    return bool(item["modified"] or (item["ns"] == state["active"] and cmds.file(q=True, modified=True)))


@_quiet
def close_tab(namespace=None, ask=True):
    """A tab closed (asking about unsaved changes); down to one tab, the last
    one becomes an ordinary scene again. A save that was cancelled (no path
    picked, an overwrite refused) keeps the tab: `session.Cancelled`."""
    state = session.state()
    namespace = namespace or state["active"]
    item = records.tab(state, namespace)
    if item is None:
        raise session.TabError("no tab %s" % namespace)
    name = records.title(dict(item, modified=False))
    if ask and _is_modified(state, item):
        answer = _ask("%s has unsaved changes." % name, ("Save", "Don't Save", "Cancel"), "Don't Save")
        if answer == "Cancel":
            return session.Cancelled("Close cancelled - %s is still open" % name)
        if answer == "Save":
            from . import saving
            saved = saving.save_tab(namespace)
            if isinstance(saved, session.Cancelled):
                return session.Cancelled("Close cancelled - %s is still open (%s)" % (name, saved))
            state = session.state()
    if namespace == state["active"] and len(state["tabs"]) > 1:
        state = switching.switch(records.neighbour(state, namespace))
    try:
        _delete_namespace(namespace)
    except Exception:
        # keep the session true to the scene: the tab stays listed while its
        # namespace is still there (already switched away from), else it goes
        if not cmds.namespace(exists=":" + namespace):
            state = records.removed(state, namespace)
        session.write(state)
        raise
    state = records.removed(state, namespace)
    session.write(state)
    if len(state["tabs"]) == 1:
        return str(finish())        # the tab is closed whatever finish says: not a cancel
    return "Closed %s" % name


@_busy
def close_others(namespace=None):
    state = session.state()
    keep = namespace or state["active"]
    message = ""
    for item in [t for t in state["tabs"] if t["ns"] != keep]:
        message = close_tab(item["ns"])
        if isinstance(message, session.Cancelled):
            return message
    return message or "No other tab"


@_quiet
def reload_tab(namespace=None, ask=True):
    """The tab read again from its file, its unsaved changes dropped."""
    state = session.state()
    namespace = namespace or state["active"]
    item = records.tab(state, namespace)
    if item is None or not item["path"] or not os.path.isfile(item["path"]):
        raise session.TabError("nothing on disk to reload for %s" % namespace)
    name = records.title(dict(item, modified=False))
    if ask and _is_modified(state, item):
        if _ask("Drop the changes to %s and read it from disk?" % name, ("Reload", "Cancel"), "Cancel") != "Reload":
            return session.Cancelled("Reload cancelled - %s is as it was" % name)
    active = namespace == state["active"]
    keep_unit = cmds.currentUnit(q=True, time=True)
    _delete_namespace(namespace)
    del NOTES[:], CHANGED[:]
    #  a hidden tab's file connects its camera keys to the scene's cameras: the active tab's
    #  are taken off for the length of the import, the file's kept as the hidden tab's own
    held = {} if active else switching.detach_cameras(state["active"])
    try:
        unit, ranges = _import(item["path"], namespace)
    finally:
        mine = {} if active else switching.detach_cameras(namespace)
        switching.attach_cameras(held)
    fresh_item = records.new_tab(namespace, item["path"], unit, ranges, _mtime(item["path"]))
    fresh_item["camera_curves"] = mine
    fresh_item["modified"] = namespace in CHANGED
    #  the content read again, the view kept: the active tab's as the cameras stand, a hidden one's
    fresh_item["cameras"] = switching.capture_cameras() if active else dict(item.get("cameras") or {})
    state = records.with_tab(state, fresh_item)
    if active:
        state = switching.enter(state, namespace)
        cmds.file(modified=namespace in CHANGED)
    else:
        switching.hide(namespace)
        cmds.currentUnit(time=keep_unit, updateAnimation=True)
        cmds.namespace(setNamespace=":" + state["active"])
    session.write(state)
    return _notes("Reloaded %s from disk" % name)


@_quiet
def finish():
    """The last tab becomes an ordinary scene: its nodes into the root
    namespace, its layers flattened, the session gone, the scene named for its
    file. The lift goes first: a name the root already uses refuses it with
    everything back in the tab, and the session stays a tab - said so."""
    state = session.state()
    if len(state["tabs"]) != 1:
        return ""
    last = state["tabs"][0]
    namespace = last["ns"]
    modified = _is_modified(state, last)
    switching.show(namespace)
    made = layers.tab_root(namespace)
    made_uid = (cmds.ls(made, uuid=True) or [None])[0] if made else None
    cmds.namespace(setNamespace=":")
    try:
        moved = session.lift(namespace)
    except session.TabError as exc:
        cmds.namespace(setNamespace=":" + namespace)
        return session.Cancelled("Not back to one scene - %s; %s stays a tab (Tabs off when it is free)"
                                 % (exc, records.title(dict(last, modified=False))))
    layers.flatten(namespace, made=(cmds.ls(made_uid) or [""])[0] if made_uid else "")
    session.drop_held(moved)
    _remove_namespace(namespace)            # what is left in it is the import's furniture
    session.delete()
    if last["path"]:
        cmds.file(rename=last["path"])
    cmds.file(modified=modified)
    return "Back to one scene: %s" % records.title(dict(last, modified=False))


@_quiet
def restore():
    """A session file opened (autosave, a crash's recovery file): its tabs
    back, only the active one shown, the scene named for the session."""
    state = session.state()
    if not state["tabs"]:
        return ""
    for item in state["tabs"]:
        if item["ns"] != state["active"]:
            switching.hide(item["ns"])
    #  the file's startup cameras are the active tab's as it was saved - newer than its record
    active = records.tab(state, state["active"])
    state = records.with_tab(state, dict(active, cameras=switching.capture_cameras()))
    state = switching.enter(state, state["active"])
    session.write_quiet(state)
    if state.get("session"):
        cmds.file(rename=state["session"])
    cmds.file(modified=False)
    from . import hooks
    hooks.install()
    return "Restored %d tabs" % len(state["tabs"])


@_busy
def tabs_off():
    """Every tab but the active one closed (asking), the active one an
    ordinary scene again."""
    state = session.state()
    if not state["tabs"]:
        return "Tabs are off already"
    message = close_others(state["active"])
    if isinstance(message, session.Cancelled):
        return session.Cancelled("Tabs off cancelled - " + message)
    return finish() or message


def unsaved():
    state = session.state()
    return [item for item in state["tabs"] if _is_modified(state, item)]


@_busy
def quit_ok():
    """Maya may quit (or replace the tabs): nothing unsaved, or the animator
    saved or dropped it. A save cancelled under Save all (no path picked, an
    overwrite refused) cancels the quit: False, every flag kept."""
    if not session.is_on():
        return True
    pending = unsaved()
    if pending:
        names = ", ".join(records.title(dict(t, modified=False)) for t in pending)
        answer = _ask("Unsaved tabs: %s" % names, ("Save all", "Discard", "Cancel"), "Cancel")
        if answer == "Cancel":
            return False
        if answer == "Save all":
            from . import saving
            active = session.state()["active"]
            for item in pending:
                if isinstance(saving.save_tab(item["ns"]), session.Cancelled):
                    if session.state()["active"] != active:
                        switching.switch(active)        # back where the animator was
                    return False
    cmds.file(modified=False)
    return True


def explore(namespace=None):
    state = session.state()
    item = records.tab(state, namespace or state["active"])
    path = (item or {}).get("path") or ""
    if not path:
        return "This tab has no file yet"
    subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    return "Shown in Explorer: %s" % path
