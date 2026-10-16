"""Scene tabs: the session in the scene - its node, which nodes are a tab's,
and moving a tab between its namespace and the root namespace.

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
A save lifts the tab's nodes into the root namespace for the length of the
export and lowers them back by UUID: a whole-namespace move refuses on the
furniture an import brings, and `exportSelected -relativeNamespace` refuses
with `-preserveReferences` (measured 2026-10-15). The same pair converts the
open scene into tab 1 (`move_into`) and back.
"""

import contextlib
import sys

import maya.cmds as cmds

from . import records

HELD_PREFIX = "skeldarHeld_"


class TabError(RuntimeError):
    """A tab operation refused; the message says why."""


class Cancelled(str):
    """The message of an operation the animator cancelled: nothing changed.
    A plain string to every caller that only shows it; `isinstance` is the
    flag for one that must stop (closing a tab whose save was cancelled)."""


# ------------------------------------------------------------------ busy

def _busy_state():
    state = getattr(sys, "_skeldar_scenetabs_busy", None)
    if state is None:
        state = {"depth": 0}
        sys._skeldar_scenetabs_busy = state
    return state


@contextlib.contextmanager
def busy():
    """A tab operation running: the bar ignores clicks meanwhile (a dialog it
    asks runs Maya's event loop, and the bar stays clickable under it)."""
    state = _busy_state()
    state["depth"] += 1
    try:
        yield
    finally:
        state["depth"] -= 1


def is_busy():
    return _busy_state()["depth"] > 0


# ------------------------------------------------------------------ the node

def exists():
    return cmds.objExists(records.SESSION_NODE)


def state():
    if not exists():
        return records.empty_state()
    return records.loads(cmds.getAttr(records.SESSION_NODE + "." + records.SESSION_ATTR) or "")


def write(new_state):
    node = records.SESSION_NODE
    if not cmds.objExists(node):
        cmds.createNode("network", name=":" + node, skipSelect=True)
        cmds.addAttr(node, longName=records.SESSION_ATTR, dataType="string")
    cmds.setAttr(node + "." + records.SESSION_ATTR, records.dumps(new_state), type="string")


def write_quiet(new_state):
    """`write` outside the undo queue (never inside an open chunk, trap 145)."""
    recording = cmds.undoInfo(q=True, stateWithoutFlush=True)
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        write(new_state)
    finally:
        cmds.undoInfo(stateWithoutFlush=recording)


def delete():
    if exists():
        cmds.lockNode(records.SESSION_NODE, lock=False)
        cmds.delete(records.SESSION_NODE)


def is_on():
    """Tab mode: two or more tabs."""
    return exists() and len(state()["tabs"]) >= 2


def current_ranges():
    return {key: cmds.playbackOptions(q=True, **{key: True}) for key in records.RANGE_KEYS}


def apply_ranges(ranges):
    if ranges:
        cmds.playbackOptions(**{key: ranges[key] for key in records.RANGE_KEYS if key in ranges})


# ------------------------------------------------------------------ which nodes

def _name(uid):
    found = cmds.ls(uid, long=True) or []
    return found[0] if found else ""


def _leaf(path):
    return path.split("|")[-1].split(":")[-1]


def _startup_nodes():
    cameras = [c for c in cmds.ls(type="camera") or [] if cmds.camera(c, q=True, startupCamera=True)]
    return cameras + (cmds.listRelatives(cameras, parent=True) or [])


def _skipped():
    names = (cmds.ls(defaultNodes=True) or []) + (cmds.ls(readOnly=True) or []) + _startup_nodes()
    names += [n for n in (records.SESSION_NODE, records.LAYER_ROOT) if cmds.objExists(":" + n)]
    return set(cmds.ls(names, uuid=True) or [])


def typed(namespace, kind):
    """The tab's nodes of `kind`, its own namespace AND every one nested in it (a rig's
    `tab:Manny_Rig:`). `ls(":tab:*", recursive=True)` does NOT reach a nested namespace
    (measured 2026-10-16: the rig's UE5_Skeleton layer and ControlSet escaped every hide)."""
    if not namespace or not cmds.namespace(exists=":" + namespace):
        return []
    nodes = cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, recurse=True) or []
    return cmds.ls(nodes, type=kind) or [] if nodes else []


def own_nodes(namespace):
    """The UUIDs of a namespace's OWN nodes at its own level ("" = the root
    namespace): not Maya's default, read-only or startup nodes, not referenced,
    not a reference node, not furniture, not the session's own."""
    skip = _skipped()
    if namespace:
        paths = cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, dagPath=True) or []
    else:
        paths = [p for p in cmds.ls(long=True) or [] if ":" not in p.split("|")[-1]]
    out = []
    for path in paths:
        uid = (cmds.ls(path, uuid=True) or [None])[0]
        if uid is None or uid in skip or cmds.referenceQuery(path, isNodeReferenced=True):
            continue
        kind = cmds.nodeType(path)
        if kind == "reference" or records.is_furniture(_leaf(path), kind):
            continue
        out.append(uid)
    return out


def top_references(namespace):
    """(reference node UUID, namespace leaf) of the references whose namespace
    sits directly in `namespace` ("" = the root)."""
    parent = (":" + namespace) if namespace else ""
    out = []
    for node in cmds.ls(type="reference") or []:
        if node.split(":")[-1] == "sharedReferenceNode" or cmds.referenceQuery(node, isNodeReferenced=True):
            continue
        try:
            ref_ns = cmds.referenceQuery(node, namespace=True)
        except RuntimeError:
            continue
        above, _, leaf = ref_ns.rpartition(":")
        if above == parent:
            out.append((cmds.ls(node, uuid=True)[0], leaf))
    return out


def child_namespaces(namespace, skip=()):
    """The leaves of the namespaces directly in `namespace` that are not a
    reference's and not in `skip` (Maya's own, the tabs)."""
    references = set(leaf for _, leaf in top_references(namespace))
    found = cmds.namespaceInfo(":" + namespace if namespace else ":", listOnlyNamespaces=True) or []
    leaves = [n.split(":")[-1] for n in found]
    return [n for n in leaves if n not in references and n not in skip
            and n not in records.SYSTEM_NAMESPACES]


# ------------------------------------------------------------------ moving

class Moved(object):
    """What `lift` took into the root namespace (or `move_into` takes out of
    it), for `lower` to put back."""

    def __init__(self, namespace):
        self.namespace = namespace
        self.nodes = []          # (uuid, leaf in the tab, locked)
        self.references = []     # (reference node uuid, namespace leaf)
        self.children = []       # child namespace leaves
        self.held = []           # (uuid, root name) of root nodes held aside


def _ref_file(uid):
    """The reference's file WITH its copy number ({1}, {2}): two tabs of one
    file reference the same file twice. A reference node is never renamed by
    hand: that breaks its link to its namespace («Cannot find the associated
    namespace», measured), so after a save its node may sit in the root as
    `refRN` - which is why references are always found by their NAMESPACE."""
    return cmds.referenceQuery(_name(uid), filename=True)


def _hold(moved, wanted):
    """A root node of Maya's own config name blocking `wanted` goes aside."""
    blocker = ":" + wanted
    if wanted != records.CONFIG_NODE or not cmds.objExists(blocker):
        return
    uid = cmds.ls(blocker, uuid=True)[0]
    cmds.rename(blocker, ":" + HELD_PREFIX + wanted, ignoreShape=True)
    moved.held.append((uid, wanted))


def lift(namespace, renames=None):
    """The tab's content into the root namespace, its own nodes renamed by
    UUID (`renames` maps a UUID to the leaf it takes outside: the tab's layer
    root -> BaseAnimation), its references and child namespaces moved. A name
    the root already uses refuses by name, after everything taken is back."""
    renames = renames or {}
    moved = Moved(namespace)
    try:
        for uid in own_nodes(namespace):
            path = _name(uid)
            locked = bool(cmds.lockNode(path, q=True, lock=True)[0])
            if locked:
                cmds.lockNode(path, lock=False)
            leaf = _leaf(path)
            wanted = renames.get(uid, leaf)
            _hold(moved, wanted)
            got = _leaf(cmds.rename(path, ":" + wanted, ignoreShape=True))
            moved.nodes.append((uid, leaf, locked))
            if got != wanted:
                raise TabError("cannot save %s: the scene already holds a node named %s"
                               % (namespace, wanted))
        for uid, leaf in top_references(namespace):
            if cmds.namespace(exists=":" + leaf):
                raise TabError("cannot save %s: the scene already holds a namespace %s" % (namespace, leaf))
            cmds.file(_ref_file(uid), edit=True, namespace=leaf)
            moved.references.append((uid, leaf))
        for child in child_namespaces(namespace):
            if cmds.namespace(exists=":" + child):
                raise TabError("cannot save %s: the scene already holds a namespace %s" % (namespace, child))
            cmds.namespace(rename=(":%s:%s" % (namespace, child), child), parent=":")
            moved.children.append(child)
    except Exception:
        lower(moved)
        raise
    return moved


def lower(moved):
    """`lift` undone exactly: child namespaces, references and nodes back in
    the tab's namespace by UUID, locks back, held root nodes back."""
    namespace = moved.namespace
    if not cmds.namespace(exists=":" + namespace):
        cmds.namespace(add=namespace, parent=":")
    for child in reversed(moved.children):
        if cmds.namespace(exists=":" + child):
            cmds.namespace(rename=(":" + child, child), parent=":" + namespace)
    for uid, leaf in reversed(moved.references):
        cmds.file(_ref_file(uid), edit=True, namespace="%s:%s" % (namespace, leaf))
    for uid, leaf, locked in reversed(moved.nodes):
        path = _name(uid)
        if path:
            cmds.rename(path, ":%s:%s" % (namespace, leaf), ignoreShape=True)
            if locked:
                cmds.lockNode(_name(uid), lock=True)
    for uid, name in reversed(moved.held):
        path = _name(uid)
        if path:
            cmds.rename(path, ":" + name, ignoreShape=True)
    moved.nodes, moved.references, moved.children, moved.held = [], [], [], []


def move_into(namespace, skip_namespaces=()):
    """The root namespace's own content into `namespace` (the open scene
    becoming tab 1): a `Moved` built from the root and lowered."""
    moved = Moved(namespace)
    for uid in own_nodes(""):
        path = _name(uid)
        moved.nodes.append((uid, _leaf(path), bool(cmds.lockNode(path, q=True, lock=True)[0])))
    moved.references = top_references("")
    moved.children = child_namespaces("", skip=tuple(skip_namespaces) + (namespace,))
    unlocked = []
    try:
        for uid, _, locked in moved.nodes:
            if locked:
                cmds.lockNode(_name(uid), lock=False)
                unlocked.append(uid)
        lower(moved)
    except Exception:
        for uid in unlocked:                     # what was unlocked locked again
            path = _name(uid)
            if path:
                try:
                    cmds.lockNode(path, lock=True)
                except RuntimeError:
                    pass
        raise
    return moved


def move_out(namespace):
    """`move_into` undone: the namespace's content back into the root
    namespace, the locks as they were, the emptied namespace removed."""
    moved = lift(namespace)
    for uid, _, locked in moved.nodes:
        if locked and _name(uid):
            cmds.lockNode(_name(uid), lock=True)
    drop_held(moved)
    if cmds.namespace(exists=":" + namespace) and not cmds.namespaceInfo(":" + namespace, listNamespace=True):
        cmds.namespace(removeNamespace=":" + namespace)
    return moved


def drop_held(moved):
    """Held root nodes deleted (a lift that is not lowered: back to one scene)."""
    for uid, _ in moved.held:
        path = _name(uid)
        if path:
            cmds.lockNode(path, lock=False)
            cmds.delete(path)
    moved.held = []
