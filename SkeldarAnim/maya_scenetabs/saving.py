"""Scene tabs: a tab saved into its own plain file - no prefix, its own fps
and ranges, its own layers and references.

The tab's nodes go into the root namespace for the length of the export and
come back by UUID (`session.lift` / `lower`); its layer root is cut from the
session's and written as BaseAnimation; its ranges go into its configuration
node; the file is written to a temporary name and then replaces the tab's file,
so a failed save never leaves half a file. Unrecorded: a save nets to nothing.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import os

import maya.cmds as cmds

from . import layers, records, session, switching

CONFIRM = None      # seam: callable(question) -> bool
PICK = None         # seam: callable() -> a path, or "" for none


def _confirm(question):
    if CONFIRM is not None:
        return CONFIRM(question)
    if cmds.about(batch=True):
        return False
    return cmds.confirmDialog(title="Scene Tabs", message=question, button=["Overwrite", "Cancel"],
                              defaultButton="Cancel", cancelButton="Cancel",
                              dismissString="Cancel") == "Overwrite"


def _pick():
    if PICK is not None:
        return PICK()
    if cmds.about(batch=True):
        return ""
    found = cmds.fileDialog2(fileMode=0, caption="Save the tab as",
                             fileFilter="Maya ASCII (*.ma);;Maya Binary (*.mb)") or []
    return found[0].replace("\\", "/") if found else ""


def _config(namespace, ranges):
    """The tab's configuration node carrying its ranges into its file."""
    node = ":%s:%s" % (namespace, records.CONFIG_NODE)
    text = records.config_script(ranges)
    if cmds.objExists(node):
        cmds.setAttr(node + ".before", text, type="string")
        return node
    return cmds.scriptNode(name=node, scriptType=records.CONFIG_SCRIPT_TYPE, beforeScript=text,
                           sourceType="mel")


def export_uuids(namespace, references=True):
    """Every node the tab's file holds: its own nodes at every level (not
    referenced, not furniture, not a reference node) and its top references'
    nodes - found by their namespace, since a saved reference's node sits in
    the root (`session._ref_file`)."""
    own_config = "%s:%s" % (namespace, records.CONFIG_NODE)
    out = []
    for path in cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, recurse=True,
                                   dagPath=True) or []:
        if cmds.referenceQuery(path, isNodeReferenced=True):
            continue
        kind = cmds.nodeType(path)
        leaf = path.split("|")[-1].split(":")[-1]
        if kind == "reference" or records.is_furniture(leaf, kind):
            continue
        if leaf == records.CONFIG_NODE and path.lstrip(":") != own_config:
            #  an import made inside the tab brought its file's configuration
            #  node (Maya skips it only when the ROOT has one - a tab's sits in
            #  the tab); in the file it runs after ours and wins (measured:
            #  the rig tab reopened at 1-120 for 0-50)
            continue
        out.append(cmds.ls(path, uuid=True)[0])
    #  the startup cameras stand where this tab has them (a save makes it the active one):
    #  written into its file, they open with it (an export writes none unselected, measured)
    out += cmds.ls([n for pair in switching.startup_cameras().values() for n in pair], uuid=True) or []
    if not references:
        #  the references written in (stage 2, a copy for a colleague): their nodes, never
        #  their reference nodes, go into the file as plain nodes
        refs = [cmds.referenceQuery(cmds.ls(uid)[0], filename=True)
                for uid, _ in session.top_references(namespace)]
        return out + (cmds.ls([n for f in refs for n in cmds.referenceQuery(f, nodes=True, dagPath=True) or []],
                              uuid=True) or [])
    return out + [uid for uid, _ in session.top_references(namespace)]


def _foreign(name, namespace, tabs, own=(records.LAYER_ROOT, records.SESSION_NODE)):
    """A node another tab's (its outermost namespace is another tab) or the session's own
    (`own`: the session's root layer and node, in the root namespace)."""
    parts = name.lstrip(":").split(":")
    if len(parts) == 1:
        return parts[0] in own
    return parts[0] != namespace and parts[0] in tabs


def foreign_inputs(uuids, namespace, tabs):
    """Every connection by which the export would reach another tab or the session's own
    nodes: `exportSelected` writes a node's whole upstream, so one input from another tab -
    directly, or through a node of the root namespace - wrote that whole tab into this tab's
    file, and the session's layer root with it (2026-10-16, live: a MaterialX blinn fed by
    another tab's stack; measured: a root node between them leaks too). Walks upstream from
    the tab's nodes through every node the export would write (not Maya's defaults or shared
    nodes, not a reference's). Returns the edges as (source MPlug, destination MPlug)."""
    import maya.api.OpenMaya as om
    own = set(uuids)
    session_nodes = (layers.root().lstrip(":") or records.LAYER_ROOT, records.SESSION_NODE)
    found = om.MSelectionList()
    for path in cmds.ls(uuids, long=True) or []:
        try:
            found.add(path)
        except RuntimeError:
            pass
    queue = [found.getDependNode(i) for i in range(found.length())]
    seen = set(own)
    edges = []
    while queue:
        node = queue.pop()
        for plug in om.MFnDependencyNode(node).getConnections():
            source = plug.sourceWithConversion()
            if source.isNull:
                continue
            fn = om.MFnDependencyNode(source.node())
            uid = fn.uuid().asString()
            if uid in own:
                continue
            if _foreign(fn.absoluteName(), namespace, tabs, session_nodes):
                edges.append((source, plug))
                continue
            if uid in seen:
                continue
            seen.add(uid)
            if fn.isDefaultNode or fn.isShared or fn.isFromReferencedFile:
                continue
            queue.append(source.node())
    return edges


def _end(plug):
    """A plug kept as its node's handle and its attribute's full name: an MPlug held across
    the save's renames and moves crashed Maya when read again (measured, 2026-10-16)."""
    import maya.api.OpenMaya as om
    return (om.MObjectHandle(plug.node()),
            plug.partialName(includeNonMandatoryIndices=True, includeInstancedIndices=True,
                             useFullAttributePath=True, useLongNames=True))


def _plug_name(end):
    import maya.api.OpenMaya as om
    handle, attribute = end
    if not handle.isValid():
        return ""
    node = handle.object()
    if node.hasFn(om.MFn.kDagNode):
        name = om.MDagPath.getAPathTo(node).fullPathName()
    else:
        name = om.MFnDependencyNode(node).absoluteName()
    return "%s.%s" % (name, attribute)


def _cut(edges):
    """The edges cut, one by one; returns them as (source end, destination end), those a
    locked node refuses left out."""
    import maya.api.OpenMaya as om
    done = []
    for source, destination in edges:
        ends = (_end(source), _end(destination))
        modifier = om.MDGModifier()
        try:
            modifier.disconnect(source, destination)
            modifier.doIt()
        except RuntimeError:
            continue
        done.append(ends)
    return done


def _join(edges):
    """`_cut` undone, edge by edge; raises after the rest when one does not go back."""
    failed = []
    for ends in edges:
        source, destination = _plug_name(ends[0]), _plug_name(ends[1])
        try:
            if not cmds.isConnected(source, destination):
                cmds.connectAttr(source, destination)
        except (RuntimeError, ValueError):
            failed.append("%s -> %s" % (source or "(gone)", destination or "(gone)"))
    if failed:
        raise RuntimeError("Scene Tabs: %d connection(s) to other tabs did not come back: %s"
                           % (len(failed), ", ".join(failed[:5])))


def save_tab(namespace=None, path=None, adopt=True, preserve_references=True):
    """The tab (the active one by default) into `path` (its own file by
    default). `adopt`: the tab takes the path and is clean after. A save
    the animator cancels (no path picked, an overwrite refused) returns
    `session.Cancelled` with everything as it was - the active tab too."""
    with session.busy():
        return _save_tab(namespace, path, adopt, preserve_references)


def _save_tab(namespace, path, adopt, preserve_references):
    state = session.state()
    namespace = namespace or state["active"]
    item = records.tab(state, namespace)
    if item is None:
        raise session.TabError("no tab %s" % namespace)
    target = (path or item["path"] or "").replace("\\", "/")
    if not target:
        target = _pick()
        if not target:
            return session.Cancelled("Save cancelled - %s has no file yet"
                                     % records.title(dict(item, modified=False)))
        path = target
    ext = os.path.splitext(target)[1].lower()
    if ext not in records.FILE_TYPES:
        raise session.TabError("a tab saves as .ma or .mb: %s" % os.path.basename(target))
    was_active = state["active"]
    if namespace != was_active:
        state = switching.switch(namespace)
        item = records.tab(state, namespace)
    if not path and records.changed_on_disk(target, item["mtime"]):
        if not _confirm("%s changed on disk since you opened it. Overwrite it?" % os.path.basename(target)):
            if was_active != namespace:
                switching.switch(was_active)
            return session.Cancelled("Save cancelled - %s left as it is on disk" % os.path.basename(target))
    ranges = session.current_ranges()
    # ends in the target's own extension: with Maya's «Default file extensions» on, an
    # export to `x.ma.skeldartmp` writes `x.ma.skeldartmp.ma` and the rename below found
    # nothing (2026-10-16, measured)
    temporary = os.path.splitext(target)[0] + ".skeldartmp" + ext
    recording = cmds.undoInfo(q=True, stateWithoutFlush=True)
    selection = cmds.ls(selection=True, uuid=True) or []
    current = cmds.namespaceInfo(currentNamespace=True) or ":"
    moved, links, folded, outside = None, [], [], []
    cmds.undoInfo(stateWithoutFlush=False)
    failures = []           # cleanup steps that raised; the export's own error wins

    def step(action):
        try:
            action()
        except Exception as exc:        # noqa: BLE001 - every other restore still runs
            failures.append(exc)

    def reselect():
        found = cmds.ls(selection) or []
        if found:
            cmds.select(found, replace=True)
        else:
            cmds.select(clear=True)

    try:
        try:
            #  a paste from another tab nested that tab's namespace here: folded for good, the
            #  file holds the pasted nodes as the tab's own (2026-10-16)
            folded = session.fold_pasted(namespace, [t["ns"] for t in state["tabs"]])
            _config(namespace, ranges)
            #  a layer of the tab Maya hung on the session root goes under the tab's (for good)
            layers.adopt_strays(namespace)
            layers.home_blends(namespace)
            uuids = export_uuids(namespace, preserve_references)
            renames = {}
            tab_root = layers.tab_root(namespace)
            if tab_root:
                links = layers.detach(tab_root)
                renames[cmds.ls(tab_root, uuid=True)[0]] = records.FILE_LAYER_ROOT
            #  nothing of another tab or of the session reachable from the file's nodes
            outside = _cut(foreign_inputs(uuids, namespace, [t["ns"] for t in state["tabs"]]))
            cmds.namespace(setNamespace=":")
            moved = session.lift(namespace, renames)
            cmds.select(cmds.ls(uuids) or [], noExpand=True, replace=True)
            cmds.file(temporary, exportSelected=True, preserveReferences=preserve_references,
                      type=records.FILE_TYPES[ext], force=True)
        except Exception:
            if os.path.exists(temporary):
                os.remove(temporary)
            raise
        finally:
            if moved is not None:
                step(lambda: session.lower(moved))
            step(lambda: cmds.namespace(setNamespace=current if current.startswith(":") else ":" + current))
            step(lambda: layers.attach(links))
            step(lambda: _join(outside))
            step(lambda: layers.home_blends(namespace))   # Maya rebuilt some in the root (measured)
            step(reselect)
    finally:
        cmds.undoInfo(stateWithoutFlush=recording)
    if failures:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise failures[0]
    os.replace(temporary, target)
    if adopt:
        item = dict(item, path=target, mtime=os.path.getmtime(target), modified=False)
        session.write_quiet(records.with_tab(session.state(), item))
        cmds.file(modified=False)
    message = "Saved %s (%s, %s)" % (os.path.basename(target), cmds.currentUnit(q=True, time=True),
                                     records.range_text(ranges))
    if folded:
        message += " | nodes pasted from %s are this tab's own now" % ", ".join(folded)
    return message


def save_as(namespace=None):
    target = _pick()
    if not target:
        return session.Cancelled("Save As cancelled")
    return save_tab(namespace, path=target)
