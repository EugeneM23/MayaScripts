"""Scene tabs: animation layers with tabs.

Maya keeps ONE root layer and remembers it internally: delete it and the other
layers lose theirs, and the next new layer crashed mayapy (measured
2026-10-15). So while tabs are on the session owns the root
(`skeldarTabsLayerRoot`), every tab's layers hang under a tab root of their own
(`<tab>:AnimLayerRoot` - Maya's own name for an imported BaseAnimation), and a
tab's file gets its tree back with that root named BaseAnimation.
"""

import json

import maya.cmds as cmds

from . import records, session


def root():
    return cmds.animLayer(q=True, root=True) or ""


def _children(layer):
    return [l for l in cmds.ls(type="animLayer") or []
            if (cmds.animLayer(l, q=True, parent=True) or "") == layer]


def ensure_root():
    """The session's root, made once: a temporary layer makes Maya's root,
    the temporary goes, the root is renamed."""
    found = root()
    if found:
        return found
    temporary = cmds.animLayer("skeldarTabsTempLayer")
    made = root()
    cmds.delete(temporary)
    return cmds.rename(made, ":" + records.LAYER_ROOT, ignoreShape=True)


def _in_namespace(namespace, make):
    """`make()` run with `namespace` current ("" = the root), the current one
    put back. A layer's name is relative to the current namespace, and so are
    the blend nodes Maya rebuilds when a layer is re-parented (measured: a
    re-parent run in the root put a tab's blend nodes in the root)."""
    current = cmds.namespaceInfo(currentNamespace=True) or ":"
    cmds.namespace(setNamespace=(":" + namespace) if namespace else ":")
    try:
        return make()
    finally:
        cmds.namespace(setNamespace=current if current.startswith(":") else ":" + current)


def _in_root_namespace(make):
    return _in_namespace("", make)


def take_root():
    """The open scene's root handed to the session (renamed). Returns the
    UUIDs of its children: they become tab 1's (`give_children`)."""
    found = root()
    if not found:
        return []
    children = cmds.ls(_children(found), uuid=True) or []
    if found.split(":")[-1] != records.LAYER_ROOT:
        #  a scene saved by an old build can hold a copy of the session root under its name:
        #  out of the way first, or the real root comes out `skeldarTabsLayerRoot1` and the copy
        #  is taken for it (2026-10-16); the copy goes into tab 1 and `tidy_imported` dissolves it
        clash = ":" + records.LAYER_ROOT
        if cmds.objExists(clash):
            cmds.rename(clash, ":" + records.LAYER_ROOT + "Copy", ignoreShape=True)
        cmds.rename(found, ":" + records.LAYER_ROOT, ignoreShape=True)
    return children


def is_root_copy(layer):
    """A copy of the session root (`skeldarTabsLayerRoot`, `...Copy`, `...1`) inside a tab: an
    old save wrote the session root into a tab's file (2026-10-16)."""
    return ":" in layer and layer.split(":")[-1].startswith(records.LAYER_ROOT)


def is_tab_root_name(layer):
    """`AnimLayerRoot` (Maya's own name for an imported BaseAnimation, and
    ours), with Maya's uniqueness number if any."""
    leaf = layer.split(":")[-1]
    rest = leaf[len(records.TAB_LAYER_ROOT):]
    return leaf.startswith(records.TAB_LAYER_ROOT) and (rest == "" or rest.isdigit())


def _make_tab_root(namespace, session_root):
    return _in_root_namespace(lambda: cmds.animLayer("%s:%s" % (namespace, records.TAB_LAYER_ROOT),
                                                     parent=session_root))


def tab_root(namespace, make=False):
    """The tab's layer root: the layer of its namespace named AnimLayerRoot
    hanging on the session's root (by NAME: right after tab 1's conversion
    its own layers hang on the session root too, measured); made when asked
    and missing."""
    session_root = root()
    if not session_root:
        return ""
    for layer in cmds.ls(":%s:*" % namespace, type="animLayer") or []:
        if is_tab_root_name(layer) and (cmds.animLayer(layer, q=True, parent=True) or "") == session_root:
            return layer
    return _make_tab_root(namespace, session_root) if make else ""


def home_blends(namespace):
    """The blend nodes of the tab's layers renamed into the tab's namespace.
    Re-parenting a layer (`animLayer -e -parent`) rebuilds its blend nodes in
    the ROOT namespace whatever namespace is current (measured): left there
    they are not the tab's - not lifted, not deleted with it - and they clash
    by name with another tab's when that tab is saved."""
    prefix = namespace + ":"
    moved = 0
    for layer in session.typed(namespace, "animLayer"):
        for node in cmds.animLayer(layer, q=True, blendNodes=True) or []:
            if node.startswith(prefix) or not cmds.objExists(node):
                continue
            locked = bool(cmds.lockNode(node, q=True, lock=True)[0])
            if locked:
                cmds.lockNode(node, lock=False)
            renamed = cmds.rename(node, ":%s:%s" % (namespace, node.split(":")[-1]))
            if locked:
                cmds.lockNode(renamed, lock=True)
            moved += 1
    return moved


def give_children(namespace, children):
    """Tab 1's layers (by UUID) under a tab root made for them; their rebuilt
    blend nodes brought home."""
    found = cmds.ls(children or []) or []
    if not found:
        return ""
    made = tab_root(namespace, make=True)
    for layer in found:
        cmds.animLayer(layer, e=True, parent=made)
    home_blends(namespace)
    return made


def detach(layer):
    """Every connection between `layer` and its parent cut (five, measured).
    Returns them as (source plug, destination plug), for `attach`."""
    parent = cmds.animLayer(layer, q=True, parent=True) or ""
    if not parent:
        return []
    cut = []
    pairs = cmds.listConnections(layer, connections=True, plugs=True) or []
    for own, other in zip(pairs[0::2], pairs[1::2]):
        if other.split(".")[0] != parent:
            continue
        if cmds.isConnected(own, other):
            cut.append((own, other))
        elif cmds.isConnected(other, own):
            cut.append((other, own))
    for source, destination in cut:
        cmds.disconnectAttr(source, destination)
    return cut


def attach(links):
    """`detach` undone: exactly those connections back. Never `animLayer -e
    -parent`, which rebuilds the layer's blend nodes in the current namespace.
    A link whose node is gone is skipped: it names another session's scene."""
    for source, destination in links or []:
        if not (cmds.objExists(source.split(".")[0]) and cmds.objExists(destination.split(".")[0])):
            continue
        if not cmds.isConnected(source, destination):
            cmds.connectAttr(source, destination)


def adopt(layer, namespace):
    """A layer Maya parented to the session root while `namespace` was the
    active tab goes under that tab's root. True when it moved."""
    if not namespace or not cmds.objExists(layer):
        return False
    session_root = root()
    if not session_root or (cmds.animLayer(layer, q=True, parent=True) or "") != session_root:
        return False
    if is_tab_root_name(layer) or is_root_copy(layer) or layer.split(":")[-1] == records.LAYER_ROOT:
        return False
    made = tab_root(namespace, make=True)
    if not made or made == layer:
        return False
    cmds.animLayer(layer, e=True, parent=made)
    home_blends(namespace)
    return True


def adopt_strays(namespace):
    """Every layer of the tab hanging on the session root (not its own root) moved under
    the tab's root, as `adopt` does when Maya makes one. One left there takes the session
    root into the tab's file, and every tab it holds with it (2026-10-16). Returns them."""
    session_root = root()
    if not session_root:
        return []
    strays = [layer for layer in session.typed(namespace, "animLayer")
              if (cmds.animLayer(layer, q=True, parent=True) or "") == session_root
              and not is_tab_root_name(layer) and not is_root_copy(layer)]
    return [layer for layer in strays if adopt(layer, namespace)]


def tidy_imported(namespace):
    """An imported tab's layers that hang on the session root (not its own root) moved under
    its root, and a copy of the session root it carries dissolved: an old save could write
    another whole tab into a tab's file, the session's root with it (2026-10-16, live).
    Returns how many layers moved."""
    session_root = root()
    if not session_root:
        return 0
    found = session.typed(namespace, "animLayer")
    made = tab_root(namespace)
    copies = [layer for layer in found if is_root_copy(layer)]
    strays = [layer for layer in found if layer != made and layer not in copies
              and (cmds.animLayer(layer, q=True, parent=True) or "") == session_root]
    children = [child for copy in copies for child in _children(copy)]
    if not (copies or strays):
        return 0
    made = made or tab_root(namespace, make=True)
    for layer in children + strays:
        if layer != made:
            cmds.animLayer(layer, e=True, parent=made)
    for copy in copies:
        if cmds.objExists(copy) and not _children(copy):
            cmds.delete(copy)
    home_blends(namespace)
    return len(children) + len(strays)


def give_back(namespace, name):
    """`take_root` + `give_children` undone (a conversion that failed half
    way): the tab root's layers back on the root, the tab root gone, the root
    named `name` again."""
    session_root = root()
    if not session_root:
        return
    made = tab_root(namespace)
    if made:
        for layer in _children(made):
            cmds.animLayer(layer, e=True, parent=session_root)
        cmds.delete(made)
        session_root = root()
    if name and session_root.split(":")[-1] != name:
        cmds.rename(session_root, ":" + name, ignoreShape=True)


def flatten(namespace, made=None):
    """Back to one scene: the tab root's layers under the session root, the
    tab root gone, the root named BaseAnimation again - or no root at all when
    no layer is left (a fresh scene's state, safe). `made`: the tab root when
    the caller found it before the tab's names left its namespace."""
    session_root = root()
    if not session_root:
        return
    made = made if made is not None else tab_root(namespace)
    if made:
        for layer in _children(made):
            cmds.animLayer(layer, e=True, parent=session_root)
        cmds.delete(made)
    if [l for l in cmds.ls(type="animLayer") or [] if l != session_root]:
        cmds.rename(session_root, ":" + records.FILE_LAYER_ROOT, ignoreShape=True)
    else:
        cmds.delete(session_root)


# ------------------------------------------------------------------ a hidden tab's layers
#  2026-10-15, found live: the Layer Editor showed every tab's layers. Its Anim tab walks
#  down from the root layer and its Display tab lists every display layer whose
#  `identification` is not 0 (0 is Maya's default layer) - layerEditor.mel's
#  buildAnimLayerArray and updateLayersByType. A hidden tab's anim layers are cut off the
#  session root and its display layers taken off layerManager (identification 0); what was
#  cut is kept on the layer itself (OUT_ATTR), so a session file saved meanwhile carries it.

OUT_ATTR = "skeldarTabOut"


def _store(node, value):
    if not cmds.attributeQuery(OUT_ATTR, node=node, exists=True):
        cmds.addAttr(node, longName=OUT_ATTR, dataType="string")
    cmds.setAttr(node + "." + OUT_ATTR, json.dumps(value), type="string")


def _take(node):
    if not cmds.attributeQuery(OUT_ATTR, node=node, exists=True):
        return None
    value = json.loads(cmds.getAttr(node + "." + OUT_ATTR) or "null")
    cmds.deleteAttr(node + "." + OUT_ATTR)
    return value


def _manager_index_free(plug):
    return not (cmds.listConnections(plug, source=False, destination=True) or [])


def hide_layers(namespace):
    """The tab's layers out of the Layer Editor: its layers on the session root cut off it
    (`detach`), its display layers off layerManager with identification 0. Again on a
    hidden tab: nothing."""
    session_root = root()
    for layer in session.typed(namespace, "animLayer"):
        if session_root and (cmds.animLayer(layer, q=True, parent=True) or "") == session_root:
            if cmds.attributeQuery(OUT_ATTR, node=layer, exists=True):
                continue
            _store(layer, detach(layer))
    for layer in session.typed(namespace, "displayLayer"):
        if cmds.attributeQuery(OUT_ATTR, node=layer, exists=True):
            continue
        sources = cmds.listConnections(layer + ".identification", source=True, destination=False,
                                       plugs=True) or []
        if not sources:
            continue
        cmds.disconnectAttr(sources[0], layer + ".identification")
        cmds.setAttr(layer + ".identification", 0)
        _store(layer, sources[0])


def _on_manager(layer, source):
    """A display layer back on its manager slot (a free one when that slot was taken
    meanwhile, Maya's own manager when the stored one is gone)."""
    manager = source.split(".")[0]
    if not cmds.objExists(manager):
        manager = "layerManager"
        source = manager + ".displayLayerId[0]"
    if not _manager_index_free(source):
        used = cmds.getAttr(manager + ".displayLayerId", multiIndices=True) or [0]
        source = "%s.displayLayerId[%d]" % (manager, max(used) + 1)
    cmds.connectAttr(source, layer + ".identification", force=True)


def show_layers(namespace):
    """`hide_layers` undone: the cut links back, each display layer on its manager slot again
    (a free one when its old slot was taken meanwhile)."""
    for layer in session.typed(namespace, "animLayer"):
        links = _take(layer)
        if links:
            attach([tuple(link) for link in links])
    for layer in session.typed(namespace, "displayLayer"):
        source = _take(layer)
        if not source:
            continue
        _on_manager(layer, source)


def forget_stored(namespace):
    """What an imported file brought of the hide state of the session that wrote it, dropped:
    its layers' stored links name that session's plugs. An old save wrote a whole hidden tab
    into another tab's file, its root's links with it, and the file did not open («No object
    matches name: tab_...:AnimLayerRoot.solo», 2026-10-16, live). Its display layers go back
    on the Layer Editor. Returns how many layers carried one."""
    dropped = 0
    for layer in session.typed(namespace, "animLayer"):
        if cmds.attributeQuery(OUT_ATTR, node=layer, exists=True):
            _take(layer)
            dropped += 1
    for layer in session.typed(namespace, "displayLayer"):
        if cmds.attributeQuery(OUT_ATTR, node=layer, exists=True):
            source = _take(layer)
            if isinstance(source, str) and source:
                _on_manager(layer, source)
            dropped += 1
    return dropped


def refresh_editors():
    """The Layer Editor's Anim and Display tabs rebuilt (GUI only, deferred, never raises)."""
    if cmds.about(batch=True):
        return
    cmds.evalDeferred(_rebuild_editors, lowestPriority=True)


def _rebuild_editors():
    import maya.mel as mel
    try:
        from . import layereditor
        layereditor.ensure()        # Maya sources its own layerEditor.mel again when it builds the editor
    except Exception:                                           # noqa: BLE001 - a UI refresh only
        pass
    for command in ('if (`treeView -exists AnimLayerTabanimLayerEditor` && `exists rebuildAnimLayerEditor`) '
                    'rebuildAnimLayerEditor("AnimLayerTab");',
                    'if (`exists updateLayersByType`) updateLayersByType("Display");'):
        try:
            mel.eval(command)
        except Exception:                                       # noqa: BLE001 - a UI refresh only
            pass
