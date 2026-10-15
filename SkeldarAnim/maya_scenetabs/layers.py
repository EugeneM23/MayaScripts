"""Scene tabs: animation layers with tabs.

Maya keeps ONE root layer and remembers it internally: delete it and the other
layers lose theirs, and the next new layer crashed mayapy (measured
2026-10-15). So while tabs are on the session owns the root
(`skeldarTabsLayerRoot`), every tab's layers hang under a tab root of their own
(`<tab>:AnimLayerRoot` - Maya's own name for an imported BaseAnimation), and a
tab's file gets its tree back with that root named BaseAnimation.
"""

import maya.cmds as cmds

from . import records


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
        cmds.rename(found, ":" + records.LAYER_ROOT, ignoreShape=True)
    return children


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
    for layer in cmds.ls(":%s:*" % namespace, type="animLayer", recursive=True) or []:
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
    -parent`, which rebuilds the layer's blend nodes in the current namespace."""
    for source, destination in links or []:
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
    if is_tab_root_name(layer) or layer.split(":")[-1] == records.LAYER_ROOT:
        return False
    made = tab_root(namespace, make=True)
    if not made or made == layer:
        return False
    cmds.animLayer(layer, e=True, parent=made)
    home_blends(namespace)
    return True


def flatten(namespace):
    """Back to one scene: the tab root's layers under the session root, the
    tab root gone, the root named BaseAnimation again - or no root at all when
    no layer is left (a fresh scene's state, safe)."""
    session_root = root()
    if not session_root:
        return
    made = tab_root(namespace)
    if made:
        for layer in _children(made):
            cmds.animLayer(layer, e=True, parent=session_root)
        cmds.delete(made)
    if [l for l in cmds.ls(type="animLayer") or [] if l != session_root]:
        cmds.rename(session_root, ":" + records.FILE_LAYER_ROOT, ignoreShape=True)
    else:
        cmds.delete(session_root)
