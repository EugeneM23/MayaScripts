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


def start():
    """The open scene becomes tab 1: its layer root to the session, its content
    into its own namespace, the scene renamed to the session's file. Returns
    the state (unchanged when tabs are on already)."""
    state = session.state()
    if state["tabs"]:
        return state
    scene = (cmds.file(q=True, sceneName=True) or "").replace("\\", "/")
    namespace = records.namespace_for(scene or records.UNTITLED, _taken())
    first = records.new_tab(namespace, scene, cmds.currentUnit(q=True, time=True),
                            session.current_ranges(), _mtime(scene))
    first["frame"] = cmds.currentTime(q=True)
    first["modified"] = bool(cmds.file(q=True, modified=True))
    children = layers.take_root()
    session.move_into(namespace)
    layers.give_children(namespace, children)
    state = records.empty_state()
    state["tabs"], state["active"] = [first], namespace
    state["session"] = records.session_name(folder(), time.strftime("%Y%m%d_%H%M%S"))
    session.write(state)
    cmds.namespace(setNamespace=":" + namespace)
    cmds.file(rename=state["session"])
    return state


def _sweep(namespace):
    """The imported file's ui configuration node and any vaccine malware node
    deleted (never run: the import did not execute script nodes)."""
    from maya_scenesetup import character
    scripts = [s for s in cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, recurse=True) or []
               if cmds.nodeType(s) == "script" and not cmds.referenceQuery(s, isNodeReferenced=True)]
    doomed = character.malware_nodes(scripts) + [
        s for s in scripts if s.split(":")[-1] == "uiConfigurationScriptNode"]
    for node in doomed:
        if cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    return doomed


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
    return unit, (_ranges_of(namespace) or session.current_ranges())


def _check(path):
    path = (path or "").replace("\\", "/")
    if os.path.splitext(path)[1].lower() not in records.FILE_TYPES:
        raise session.TabError("only Maya scenes open in a tab (.ma, .mb): %s" % os.path.basename(path))
    if not os.path.isfile(path):
        raise session.TabError("no such file: %s" % path)
    return path


def open_tab(path, index=None):
    """`path` into a new tab (the open scene becomes tab 1 first)."""
    path = _check(path)
    state = start()
    namespace = records.namespace_for(path, _taken())
    state = switching.leave(state)
    unit, ranges = _import(path, namespace)
    state = records.with_tab(state, records.new_tab(namespace, path, unit, ranges, _mtime(path)), index)
    state = switching.enter(state, namespace, fresh=True)
    session.write(state)
    cmds.file(modified=False)
    return "Opened %s in a tab (%s, %s)" % (os.path.basename(path), unit, records.range_text(ranges))


def open_any(path):
    """Maya's own Open while tabs are on: a saved session replaces the tabs
    (after asking about unsaved ones), any other scene opens in a new tab."""
    path = _check(path)
    if not records.holds_session(path):
        return open_tab(path)
    if not quit_ok():
        return "Open cancelled - the tabs are as they were"
    from . import hooks
    with hooks.bypass():
        cmds.file(path, open=True, force=True)
    return restore()


def new_tab():
    """An empty tab (its first Save asks for a path)."""
    state = start()
    namespace = records.namespace_for(records.UNTITLED, _taken())
    state = switching.leave(state)
    cmds.namespace(add=namespace, parent=":")
    state = records.with_tab(state, records.new_tab(namespace, "", cmds.currentUnit(q=True, time=True),
                                                    session.current_ranges()))
    state = switching.enter(state, namespace, fresh=True)
    session.write(state)
    return "New empty tab"


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


def close_tab(namespace=None, ask=True):
    """A tab closed (asking about unsaved changes); down to one tab, the last
    one becomes an ordinary scene again."""
    state = session.state()
    namespace = namespace or state["active"]
    item = records.tab(state, namespace)
    if item is None:
        raise session.TabError("no tab %s" % namespace)
    name = records.title(dict(item, modified=False))
    if ask and _is_modified(state, item):
        answer = _ask("%s has unsaved changes." % name, ("Save", "Don't Save", "Cancel"), "Don't Save")
        if answer == "Cancel":
            return "Close cancelled - %s is still open" % name
        if answer == "Save":
            from . import saving
            saving.save_tab(namespace)
            state = session.state()
    if namespace == state["active"] and len(state["tabs"]) > 1:
        state = switching.switch(records.neighbour(state, namespace))
    _delete_namespace(namespace)
    switching.forget_layout(item)
    state = records.removed(state, namespace)
    session.write(state)
    if len(state["tabs"]) == 1:
        return finish()
    return "Closed %s" % name


def close_others(namespace=None):
    state = session.state()
    keep = namespace or state["active"]
    message = ""
    for item in [t for t in state["tabs"] if t["ns"] != keep]:
        message = close_tab(item["ns"])
        if "cancelled" in message:
            return message
    return message or "No other tab"


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
            return "Reload cancelled - %s is as it was" % name
    active = namespace == state["active"]
    keep_unit = cmds.currentUnit(q=True, time=True)
    _delete_namespace(namespace)
    unit, ranges = _import(item["path"], namespace)
    fresh_item = records.new_tab(namespace, item["path"], unit, ranges, _mtime(item["path"]))
    fresh_item["layout"] = item["layout"]
    state = records.with_tab(state, fresh_item)
    if active:
        state = switching.enter(state, namespace)
        cmds.file(modified=False)
    else:
        switching.hide(namespace)
        cmds.currentUnit(time=keep_unit, updateAnimation=True)
        cmds.namespace(setNamespace=":" + state["active"])
    session.write(state)
    return "Reloaded %s from disk" % name


def finish():
    """The last tab becomes an ordinary scene: its layers flattened, its nodes
    into the root namespace, the session gone, the scene named for its file."""
    state = session.state()
    if len(state["tabs"]) != 1:
        return ""
    last = state["tabs"][0]
    namespace = last["ns"]
    modified = _is_modified(state, last)
    switching.show(namespace)
    cmds.namespace(setNamespace=":")
    layers.flatten(namespace)
    moved = session.lift(namespace)
    session.drop_held(moved)
    _remove_namespace(namespace)            # what is left in it is the import's furniture
    session.delete()
    switching.forget_layout(last)
    if last["path"]:
        cmds.file(rename=last["path"])
    cmds.file(modified=modified)
    return "Back to one scene: %s" % records.title(dict(last, modified=False))


def restore():
    """A session file opened (autosave, a crash's recovery file): its tabs
    back, only the active one shown, the scene named for the session."""
    state = session.state()
    if not state["tabs"]:
        return ""
    for item in state["tabs"]:
        if item["ns"] != state["active"]:
            switching.hide(item["ns"])
    state = switching.enter(state, state["active"])
    session.write_quiet(state)
    if state.get("session"):
        cmds.file(rename=state["session"])
    cmds.file(modified=False)
    from . import hooks
    hooks.install()
    return "Restored %d tabs" % len(state["tabs"])


def tabs_off():
    """Every tab but the active one closed (asking), the active one an
    ordinary scene again."""
    state = session.state()
    if not state["tabs"]:
        return "Tabs are off already"
    message = close_others(state["active"])
    if "cancelled" in message:
        return "Tabs off cancelled - " + message
    return finish() or message


def unsaved():
    state = session.state()
    return [item for item in state["tabs"] if _is_modified(state, item)]


def quit_ok():
    """Maya may quit (or replace the tabs): nothing unsaved, or the animator
    saved or dropped it."""
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
            for item in pending:
                saving.save_tab(item["ns"])
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
