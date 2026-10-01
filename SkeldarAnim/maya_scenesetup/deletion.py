"""Characters > Delete: a character out of the scene, whole.

2026-10-01, the animator: «я выделяю любую часть персонажа рига или скелета не важно какую нажимаю
эту кнопку и у меня удаляется из сцены все что связано с этим персонажем. Также если я выделил
несколько разных персонажей кнопка должна удалить все их части». A confirm first («Диалог с
подтверждением»), one undo chunk. Spec: docs/superpowers/specs/2026-10-01-delete-character-design.md.

**Which characters**: every one a selected node belongs to -- lying under one of its PARTS (its DAG
tops: a rig's group, skeleton and the asset's other tops; a skeleton's root, its layout Null; the meshes
skinned to it; the weapon / armor spaces following its bones; our weapons and cameras driving its
bones; its centre-of-mass group) or in its namespace. Nothing selected is a refusal: a destructive
button never falls back to "the only character".

**What goes**: the CORE -- the parts raised over the plain transforms they empty, everything below
them, the rig's namespace whole (an Add puts every one of its 2700 nodes there, measured), a skeleton's
namespace when it holds nothing else, a skeletal armor piece's namespace -- and the DG GARBAGE around
it: a plain delete of the DAG leaves materials, layers, sets, curves and AdvancedSkeleton's utility
nodes behind (measured: 292 after Manny's skeleton, 28 after the Creep's, 9 after the UE4 Mannequin).
A component of the connection graph outside the core, with the scene's HUBS cut out (`HUB_TYPES`,
default, locked and referenced nodes), goes when it holds no DAG node and touches the core. Measured:
`lightLinker1` is not a default node and joins every shading group of the scene into one component.
An unknown hub only merges components, so the failure mode is keeping, never deleting another's node.

**What an Add brought** cannot all be found by connection: Manny's skeleton asset carries the dead
half of an AdvancedSkeleton rig (275 DG nodes, `AllSet`, `BodyControls`, a `camera1`), and the palette
unassigns an FBX's own materials. So `character._after_import` RECORDS the import on a `network` node
fed by the root's message (`record_import`); a recorded DAG node with nothing foreign below it joins
the core, a recorded component that touches nothing goes when every node in it was recorded.
"""

import collections

import maya.cmds as cmds

import maya_rigs

Character = collections.namedtuple("Character", "kind label namespace root rig parts")
Plan = collections.namedtuple(
    "Plan", "characters tops core doomed namespaces riders disconnects foreign summaries refusal")

# The scene's registries: a node of these types links unrelated characters (every shading group
# meets `lightLinker1`, every ikHandle its solver) and never belongs to one.
HUB_TYPES = ("lightLinker", "partition", "renderLayer", "renderLayerManager",
             "displayLayerManager", "ikSolver", "ikSystem", "shapeEditorManager",
             "poseInterpolatorManager", "UsdDefaultSettings", "nodeGraphEditorInfo",
             "hyperLayout", "hyperView", "hyperGraphInfo", "animLayer", "time",
             "sequenceManager", "reference", "defaultRenderUtilityList",
             "defaultShaderList", "defaultTextureList", "defaultLightList")

# Maya's per-scene managers (and mayaUsd's settings): an import makes copies of them (traps 121,
# 122) that are the scene's, not a character's.
SINGLETONS = ("shapeEditorManager", "poseInterpolatorManager", "UsdDefaultSettings")

# The Add's record (a `network` node): which root, which nodes, which catalog row.
RECORD_ROOT = "skeldarImportRoot"
RECORD_NODES = "skeldarImportNodes"
RECORD_LABEL = "skeldarImportLabel"
RECORD_SUFFIX = "_skeldarImport"

# Markers of the things a character carries, for the confirm's summary. maya_com.network's and
# connections' spelled here (a test pins them equal): importing those drags numpy / maya.mel in.
COM_MARKER = "skeldarCom"
COM_ROOT_LINK = "skeldarComRoot"
HAND_LINK = "skeldarHandLink"        # connections.MARKER: on a rider's constraint, the proxy's UUID
HOLDER = "MoCapConstraints"
HOLDER_SOURCES = ("asrtSourceRoot", "pmrtSourceRoot")

NOTHING_SELECTED = ("Select any part of a character - a control, a bone, a mesh, its weapon - then "
                    "press Delete. Several characters: a part of each.")
NOT_A_CHARACTER = ("Nothing selected belongs to a character - select a control, a bone, a mesh or "
                   "a weapon of the one to delete.")
CANCELLED = "Delete cancelled - nothing changed."
REFERENCED = ("{0} comes from a reference ({1}) - remove it in the Reference Editor; "
              "nothing deleted.")


# ------------------------------------------------------------------- pure

def doomed_components(core, frontier, provenance, neighbours, is_dag, is_hub):
    """The DG nodes to delete besides `core`. Pure over injected graph questions.

    Components of the graph over the nodes outside `core`, `is_hub` nodes cut out, started from
    `frontier` (the core's neighbours) and from the recorded nodes. One goes when it holds no DAG
    node and touches the core, or when every node in it was recorded.
    """
    doomed, seen = set(), set()
    starts = list(frontier) + [node for node in provenance if node not in frontier]
    for start in starts:
        if start in seen or start in core or is_hub(start):
            continue
        comp, stack, touches = set(), [start], False
        while stack:
            node = stack.pop()
            if node in comp:
                continue
            comp.add(node)
            for other in neighbours(node):
                if other in core:
                    touches = True
                elif other not in comp and not is_hub(other):
                    stack.append(other)
        seen |= comp
        if any(is_dag(node) for node in comp):
            continue
        if touches or comp <= provenance:
            doomed |= comp
    return doomed


def _under(path, top):
    return path == top or path.startswith(top + "|")


def outermost(paths):
    """The paths no other one of them lies above, in their order. Pure, separator-aware."""
    unique = list(dict.fromkeys(paths))
    return [path for path in unique
            if not any(other != path and _under(path, other) for other in unique)]


def raised(tops, parent_of, children_of, plain):
    """`tops` raised over every plain parent whose children all go, outermost. Pure.

    The Creep skeleton's `Armature` goes with its root, Manny's `SKM_Manny_Simple` with its two
    meshes, an emptied `WeaponSpaces` with its spaces; a group holding anything else stays.
    """
    doomed = list(dict.fromkeys(tops))

    def going(path):
        return any(_under(path, top) for top in doomed)

    changed = True
    while changed:
        changed = False
        for path in list(doomed):
            parent = parent_of(path)
            if not parent or going(parent) or not plain(parent):
                continue
            if all(going(child) for child in children_of(parent)):
                doomed.append(parent)
                changed = True
    return outermost(doomed)


def in_namespace(path, namespace):
    """Whether `path`'s own node lies in `namespace` or a namespace nested in it. Pure."""
    if not namespace:
        return False
    own = maya_rigs.namespace_of(path)
    return own == namespace or own.startswith(namespace + ":")


def owners(path, characters):
    """The characters `path` belongs to: under one of its parts, or in its namespace. Pure."""
    return [c for c in characters
            if in_namespace(path, c.namespace)
            or any(_under(path, part) for part in c.parts)]


def choose(selection, characters):
    """(the characters the selection names, in order; the selected paths that name none). Pure."""
    picked, unowned = [], []
    for path in selection or []:
        found = owners(path, characters)
        if not found:
            unowned.append(path)
        for c in found:
            if c not in picked:
                picked.append(c)
    return picked, unowned


def counted(count, word):
    """`1 weapon`, `2 armor pieces`. Pure."""
    return "{0} {1}{2}".format(count, word, "" if count == 1 else "s")


def confirm_text(summaries, disconnects=(), foreign=()):
    """The question before the delete. `summaries`: [(label, [what of theirs goes])]. Pure."""
    count = len(summaries)
    lines = ["Delete {0} and everything that belongs to {1}?".format(
        counted(count, "character"), "it" if count == 1 else "them"), ""]
    for label, extras in summaries:
        lines.append(label + (" - " + ", ".join(extras) if extras else ""))
    if disconnects:
        lines += ["", "{0} {1} retargeted from them: disconnected first, the take not baked."
                  .format(", ".join(disconnects), "is" if len(disconnects) == 1 else "are")]
    if foreign:
        shown = list(foreign)[:6]
        more = len(foreign) - len(shown)
        lines += ["", "Constrained to them - the constraint goes with them, they keep their pose: "
                  + ", ".join(shown) + (" and {0} more".format(more) if more else "")]
    lines += ["", "Ctrl+Z brings them back."]
    return "\n".join(lines)


def deleted_message(labels, count, unowned=0, notes=()):
    """The line after the delete. Pure."""
    parts = ["Deleted {0} - {1} nodes. Ctrl+Z brings them back.".format(", ".join(labels), count)]
    parts += list(notes)
    if unowned:
        parts.append("{0} {1} to no character and {2}.".format(
            counted(unowned, "selected node"), "belongs" if unowned == 1 else "belong",
            "stays" if unowned == 1 else "stay"))
    return " ".join(parts)


# ------------------------------------------------------------- the record

def _uuid(node):
    found = cmds.ls(node, uuid=True) if node else []
    return found[0] if found else None


def _path(uuid):
    found = cmds.ls(uuid, long=True) if uuid else []
    return found[0] if found else None


def _hub_types():
    """Every concrete node type a hub can be, derived ones included (`ikRPsolver` is an
    `ikSolver`). A plug-in's type that is not loaded is simply absent."""
    names = set()
    for kind in HUB_TYPES:
        try:
            derived = cmds.nodeType(kind, derived=True, isTypeName=True) or []
        except RuntimeError:
            continue
        names.add(kind)
        names.update(derived)
    return names


def _is_hub_type(node, names=None):
    try:
        return cmds.nodeType(node) in (names if names is not None else _hub_types())
    except RuntimeError:
        return False


def _recordable(nodes):
    """The UUIDs of `nodes` (names or UUIDs) worth recording: hubs left out."""
    uuids = []
    hub_types = _hub_types()
    for node in cmds.ls(nodes or [], long=True) or []:
        if _is_hub_type(node, hub_types):
            continue
        uuid = _uuid(node)
        if uuid and uuid not in uuids:
            uuids.append(uuid)
    return uuids


def record_on(node, nodes):
    """Record on `node` itself what its import brought (a weapon: its FBX's own materials, which
    the palette unassigns). A weapon is never exported, so the attribute reaches no file."""
    if not node or not cmds.objExists(node):
        return
    if not cmds.attributeQuery(RECORD_NODES, node=node, exists=True):
        cmds.addAttr(node, longName=RECORD_NODES, dataType="string")
    cmds.setAttr(node + "." + RECORD_NODES, " ".join(_recordable(nodes)), type="string")


def record_import(root, nodes, label):
    """Record what an Add of a skeleton brought, for Delete. Returns the record node or None.

    A `network` node fed by `root.message`: DG, so it is the root's alone and goes with it; and
    nothing about the root changes (an FBX export of the bones writes no attribute of ours).
    """
    if not root or not cmds.objExists(root):
        return None
    uuids = _recordable(nodes)
    leaf = root.split("|")[-1].split(":")[-1]
    record = cmds.createNode("network", name=leaf + RECORD_SUFFIX, skipSelect=True)
    cmds.addAttr(record, longName=RECORD_ROOT, attributeType="message")
    cmds.addAttr(record, longName=RECORD_NODES, dataType="string")
    cmds.addAttr(record, longName=RECORD_LABEL, dataType="string")
    cmds.connectAttr(root + ".message", record + "." + RECORD_ROOT)
    cmds.setAttr(record + "." + RECORD_NODES, " ".join(uuids), type="string")
    cmds.setAttr(record + "." + RECORD_LABEL, label or "", type="string")
    return record


def records_of(root):
    """The Add records of `root` (node names)."""
    out = []
    for node in cmds.listConnections(root + ".message", source=False, destination=True) or []:
        if cmds.attributeQuery(RECORD_NODES, node=node, exists=True) and node not in out:
            out.append(node)
    return out


def recorded(root):
    """(the UUIDs `root`'s Add records hold, the catalog label they name or "")."""
    uuids, label = set(), ""
    for record in records_of(root):
        uuids.update((cmds.getAttr(record + "." + RECORD_NODES) or "").split())
        label = label or (cmds.getAttr(record + "." + RECORD_LABEL) or "")
    return uuids, label


# ------------------------------------------------------------- the parts

def _parent(path):
    found = cmds.listRelatives(path, parent=True, fullPath=True) or []
    return found[0] if found else None


def _children(path):
    return cmds.listRelatives(path, children=True, fullPath=True) or []


def _plain(path):
    """A transform that is only a transform: no shape, not ours to keep, not referenced or locked."""
    try:
        if cmds.nodeType(path) != "transform":
            return False
        if cmds.listRelatives(path, shapes=True):
            return False
        if cmds.referenceQuery(path, isNodeReferenced=True):
            return False
        return not cmds.lockNode(path, query=True, lock=True)[0]
    except RuntimeError:
        return False


def _raise(tops):
    return raised(tops, _parent, _children, _plain)


def _joints(top):
    if not top or not cmds.objExists(top):
        return []
    found = [top] if cmds.objectType(top) == "joint" else []
    return found + (cmds.listRelatives(top, allDescendents=True, type="joint",
                                       fullPath=True) or [])


def _skinned_meshes(roots):
    from maya_scenesetup import colour
    out = []
    for root in roots:
        if not root or not cmds.objExists(root):
            continue
        for shape in colour.skinned_shapes(root):
            parent = _parent(shape)
            if parent and parent not in out:
                out.append(parent)
    return out


def _marked(node, attr):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery(attr, node=node, exists=True)


def _drivers(joints):
    """Our weapons and cameras driving any of `joints` (a weapon on the floor, a camera on
    camera_root): the targets of the parentConstraints under them that carry our markers."""
    from maya_scenesetup import bonedrive
    from maya_scenesetup import camera
    out = []
    if not joints:
        return out
    for con in cmds.listRelatives(joints, children=True, type="parentConstraint",
                                  fullPath=True) or []:
        for target in cmds.parentConstraint(con, query=True, targetList=True) or []:
            path = (cmds.ls(target, long=True) or [None])[0]
            if path and (_marked(path, bonedrive.MARKER) or _marked(path, camera.MARKER)) \
                    and path not in out:
                out.append(path)
    return out


def _spaces(joints):
    """The weapon / armor spaces at world level that follow any of `joints` (a rig's stand in
    its group, which is a part already)."""
    from maya_scenesetup import armor
    from maya_scenesetup import weaponspace
    wanted = set(joints)
    out = []
    for top in cmds.ls(assemblies=True, long=True) or []:
        if not (_marked(top, weaponspace.GROUP_MARKER) or _marked(top, armor.GROUP_MARKER)):
            continue
        for space in cmds.listRelatives(top, children=True, type="transform", fullPath=True) or []:
            if (_marked(space, weaponspace.SPACE_MARKER) or _marked(space, armor.SPACE_MARKER)) \
                    and weaponspace.bone_of(space) in wanted:
                out.append(space)
    return out


def _com_groups(root):
    out = []
    if root and cmds.objExists(root):
        for node in cmds.listConnections(root + ".message", source=False, destination=True) or []:
            path = (cmds.ls(node, long=True) or [None])[0]
            if path and _marked(path, COM_MARKER) and path not in out:
                out.append(path)
    return out


def _recorded_tops(uuids):
    """The recorded DAG nodes standing at world level (a `camera1` the asset carried)."""
    out = []
    for top in cmds.ls(assemblies=True, long=True) or []:
        if _uuid(top) in uuids:
            out.append(top)
    return out


def _skeleton_roots(rigs):
    """The bare skeletons: `character_roots` minus the rigs' own joints and their game skeletons,
    and minus anything hanging in a weapon / armor space (a skeletal armor piece)."""
    from maya_overrig import builder
    from maya_scenesetup import armor
    from maya_scenesetup import weaponspace
    out = []
    for root in builder.character_roots():
        if any(maya_rigs.under(root, rig.group) or root == rig.skeleton_root for rig in rigs):
            continue
        if maya_rigs.rig_of(root, rigs) is not None:
            continue
        if weaponspace.hand_for(root) or armor.bone_for(root):
            continue
        out.append(root)
    return out


def _rig_character(rig):
    if rig.namespace:
        tops = [top for top in cmds.ls(assemblies=True, long=True) or []
                if in_namespace(top, rig.namespace)]
    else:
        tops = [rig.group] + ([rig.skeleton_root] if rig.skeleton_root else [])
    joints = maya_rigs.rig_paths(rig)
    roots = [rig.skeleton_root] if rig.skeleton_root else []
    parts = tops + _skinned_meshes(roots) + _drivers(joints) + _spaces(joints) \
        + sum((_com_groups(root) for root in roots), [])
    return Character("rig", "{0} (rig)".format(maya_rigs.label(rig)), rig.namespace,
                     rig.skeleton_root or "", rig, _raise(parts))


def _skeleton_character(root):
    uuids, label = recorded(root)
    joints = _joints(root)
    parts = [root] + _skinned_meshes([root]) + _drivers(joints) + _spaces(joints) \
        + _com_groups(root) + _recorded_tops(uuids)
    leaf = root.split("|")[-1]
    shown = "{0} ({1})".format(label, leaf) if label else "{0} (skeleton)".format(leaf)
    return Character("skeleton", shown, "", root, None, _raise(parts))


def characters():
    """Every character in the scene, rigs first."""
    rigs = maya_rigs.rigs()
    out = [_rig_character(rig) for rig in rigs]
    out += [_skeleton_character(root) for root in _skeleton_roots(rigs)]
    return out


def _selection_paths(selection):
    out = []
    for item in selection or []:
        node = item.split(".")[0]
        path = (cmds.ls(node, long=True) or [None])[0]
        if path and path not in out:
            out.append(path)
    return out


def selected_characters(selection=None):
    """(the characters the selection names, the selected paths naming none, the selection)."""
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    paths = _selection_paths(selection)
    if not paths:
        return [], [], paths
    picked, unowned = choose(paths, characters())
    return picked, unowned, paths


# -------------------------------------------------------------- the plan

class _Graph(object):
    """The connection graph by UUID, asked lazily and cached."""

    def __init__(self):
        self.hubs = set(cmds.ls(cmds.ls(defaultNodes=True) or [], uuid=True) or [])
        kinds = sorted(_hub_types())
        if kinds:
            self.hubs.update(cmds.ls(cmds.ls(type=kinds) or [], uuid=True) or [])
        self._hub, self._dag, self._near = {}, {}, {}

    def is_hub(self, uuid):
        if uuid in self.hubs:
            return True
        if uuid not in self._hub:
            path = _path(uuid)
            try:
                self._hub[uuid] = path is None or bool(
                    cmds.lockNode(path, query=True, lock=True)[0]
                    or cmds.referenceQuery(path, isNodeReferenced=True))
            except RuntimeError:
                self._hub[uuid] = True
        return self._hub[uuid]

    def is_dag(self, uuid):
        if uuid not in self._dag:
            path = _path(uuid)
            self._dag[uuid] = bool(path) and cmds.objectType(path, isAType="dagNode")
        return self._dag[uuid]

    def neighbours(self, uuid):
        if uuid not in self._near:
            path = _path(uuid)
            found = cmds.listConnections(path, source=True, destination=True) if path else []
            self._near[uuid] = set(cmds.ls(found or [], uuid=True) or [])
        return self._near[uuid]


def _namespace_nodes(namespace):
    """UUIDs of every node in `namespace` and the namespaces nested in it."""
    if not namespace or not cmds.namespace(exists=":" + namespace):
        return set()
    nodes = cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, recurse=True,
                               dagPath=True) or []
    return set(cmds.ls(nodes, uuid=True) or [])


def _descendants(tops):
    found = list(tops)
    if tops:
        found += cmds.listRelatives(tops, allDescendents=True, fullPath=True) or []
    return set(cmds.ls(found, uuid=True) or [])


def _exclusive_namespace(root, tops):
    """A skeleton's namespace when every top-level node in it goes (a clip imported as its own
    skeleton), else ""."""
    namespace = maya_rigs.namespace_of(root)
    if not namespace:
        return ""
    in_it = [top for top in cmds.ls(assemblies=True, long=True) or [] if in_namespace(top, namespace)]
    return namespace if all(any(_under(top, t) for t in tops) for top in in_it) else ""


def _armor_namespaces(core):
    from maya_scenesetup import armor
    out = []
    for uuid in core:
        path = _path(uuid)
        if path and cmds.objectType(path, isAType="transform") and _marked(path, armor.NAMESPACE):
            namespace = cmds.getAttr(path + "." + armor.NAMESPACE)
            if namespace and namespace not in out:
                out.append(namespace)
    return out


def _summary(char):
    """What of the character's goes, for the confirm: weapons, armor, camera, centre of mass."""
    from maya_scenesetup import armor
    from maya_scenesetup import bonedrive
    from maya_scenesetup import camera
    counts = collections.Counter()
    nodes = list(char.parts) + (cmds.listRelatives(char.parts, allDescendents=True,
                                                   type="transform", fullPath=True) or [])
    for node in nodes:
        for key, attr in (("weapon", bonedrive.MARKER), ("armor piece", armor.MARKER),
                          ("camera", camera.MARKER), ("CoM", COM_MARKER)):
            if cmds.attributeQuery(attr, node=node, exists=True):
                counts[key] += 1
    out = []
    for key in ("weapon", "armor piece"):
        if counts[key]:
            out.append(counted(counts[key], key))
    if counts["camera"]:
        out.append("camera")
    if counts["CoM"]:
        out.append("centre of mass")
    return out


def _riders(core):
    """Objects outside the core riding a proxy inside it (BakeAcross): released first."""
    out = []
    for con in cmds.ls(type="parentConstraint", long=True) or []:
        if not cmds.attributeQuery(HAND_LINK, node=con, exists=True):
            continue
        if cmds.getAttr(con + "." + HAND_LINK) not in core:
            continue
        rider = _parent(con)
        if rider and _uuid(rider) not in core and rider not in out:
            out.append(rider)
    return out


def _disconnects(core, chars):
    """Rigs left standing whose MoCap holder's source is a skeleton that goes."""
    going = set(c.rig for c in chars if c.rig is not None)
    out = []
    for rig in maya_rigs.rigs():
        if rig in going:
            continue
        holder = maya_rigs.node(rig, HOLDER)
        if not cmds.objExists(holder):
            continue
        for attr in HOLDER_SOURCES:
            if cmds.attributeQuery(attr, node=holder, exists=True):
                source = cmds.getAttr(holder + "." + attr) or ""
                if _uuid(source) in core:
                    out.append(rig)
                    break
    return out


def _foreign(core, skip):
    """Constraints outside the core aimed at it: named, kept."""
    out = []
    for con in cmds.ls(type="constraint", long=True) or []:
        uuid = _uuid(con)
        if uuid in core or uuid in skip:
            continue
        sources = cmds.ls(cmds.listConnections(con, source=True, destination=False) or [],
                          uuid=True) or []
        if any(source in core for source in sources):
            owner = _parent(con)
            name = (owner or con).split("|")[-1]
            if name not in out:
                out.append(name)
    return out


def _holder_constraints(rigs):
    out = set()
    for rig in rigs:
        holder = maya_rigs.node(rig, HOLDER)
        if cmds.objExists(holder):
            out.update(cmds.ls(cmds.listConnections(holder, source=False, destination=True) or [],
                               uuid=True) or [])
    return out


def _refusal(chars):
    for char in chars:
        for top in char.parts:
            if cmds.objExists(top) and cmds.referenceQuery(top, isNodeReferenced=True):
                return REFERENCED.format(char.label,
                                         cmds.referenceQuery(top, filename=True, shortName=True))
    return ""


def plan(chars):
    """Everything the delete of `chars` takes, and what it does on the way. Reads only."""
    refusal = _refusal(chars)
    tops = _raise(sum((list(c.parts) for c in chars), []))
    core = _descendants(tops)
    namespaces = []
    for char in chars:
        if char.kind == "rig":
            namespace = char.namespace
        else:
            namespace = _exclusive_namespace(char.root, tops)
        if namespace and namespace not in namespaces:
            namespaces.append(namespace)
    for namespace in namespaces:
        core |= _namespace_nodes(namespace)
    for namespace in _armor_namespaces(core):
        if namespace not in namespaces:
            namespaces.append(namespace)
            core |= _namespace_nodes(namespace)

    provenance = set()
    for char in chars:
        if char.kind == "skeleton":
            provenance |= recorded(char.root)[0]
    for node in cmds.ls(list(core), type="transform", long=True) or []:
        if cmds.attributeQuery(RECORD_NODES, node=node, exists=True):
            provenance.update((cmds.getAttr(node + "." + RECORD_NODES) or "").split())
    for uuid in sorted(provenance - core):
        path = _path(uuid)
        if not path or not cmds.objectType(path, isAType="dagNode"):
            continue
        parent = _parent(path)
        if parent is not None and _uuid(parent) not in core:
            continue
        below = _descendants([path])
        if below <= (provenance | core):
            core |= below
            tops.append(path)

    graph = _Graph()
    frontier = set()
    names = cmds.ls(list(core), long=True) or []
    if names:
        frontier = set(cmds.ls(cmds.listConnections(names, source=True, destination=True) or [],
                               uuid=True) or []) - core
    doomed = doomed_components(core, frontier, provenance - core, graph.neighbours,
                               graph.is_dag, graph.is_hub)
    riders = _riders(core)
    disconnects = _disconnects(core, chars)
    skip = _holder_constraints(disconnects)
    for rider in riders:
        skip.update(cmds.ls(cmds.listRelatives(rider, children=True, type="constraint",
                                               fullPath=True) or [], uuid=True) or [])
    foreign = _foreign(core, skip)
    summaries = [(c.label, _summary(c)) for c in chars]
    return Plan(chars, outermost(tops), core, doomed, namespaces, riders, disconnects, foreign,
                summaries, refusal)


# ----------------------------------------------------------- the delete

def _delete(names):
    """Delete `names`; one at a time when the batch refuses (a node another one took along)."""
    if not names:
        return
    try:
        cmds.delete(names)
    except (RuntimeError, ValueError):
        for name in names:
            if cmds.objExists(name):
                cmds.delete(name)


def _untrack_com(core):
    import sys
    engine = sys.modules.get("maya_com.engine")
    if engine is None:
        return
    for uuid in core:
        path = _path(uuid)
        if path and _marked(path, COM_MARKER):
            try:
                engine.untrack(uuid)
            except Exception:                                    # noqa: BLE001
                pass


def execute(p, unowned=0):
    """Do the plan, in one undo chunk. Returns the line."""
    before = len(cmds.ls() or [])
    notes = []
    cmds.undoInfo(openChunk=True, chunkName="skeldarDeleteCharacters")
    try:
        if p.riders:
            from maya_scenesetup import connections
            connections.release_across(list(p.riders))
            notes.append("Released from the proxies: {0}.".format(", ".join(
                r.split("|")[-1] for r in p.riders)))
        for rig in p.disconnects:
            import maya_rig_retarget
            maya_rig_retarget.disconnect(rig=rig)
            notes.append("{0} disconnected (the take not baked).".format(maya_rigs.label(rig)))
        _untrack_com(p.core)
        everything = set(p.core) | set(p.doomed)
        for uuid in everything:
            path = _path(uuid)
            if path and cmds.lockNode(path, query=True, lock=True)[0]:
                cmds.lockNode(path, lock=False)
        _delete(outermost([path for path in (_path(_uuid(t)) for t in p.tops) if path]))
        left = [path for path in (_path(uuid) for uuid in everything) if path]
        dag = outermost([path for path in left if cmds.objectType(path, isAType="dagNode")])
        _delete(dag)
        _delete([path for path in (_path(uuid) for uuid in everything) if path])
        for namespace in sorted(p.namespaces, key=lambda ns: -ns.count(":")):
            _remove_namespace(namespace, notes)
        from maya_scenesetup import connections
        connections.sweep_orphans()
    finally:
        cmds.undoInfo(closeChunk=True)
    gone = before - len(cmds.ls() or [])
    return deleted_message([c.label for c in p.characters], gone, unowned, notes)


def _remove_namespace(namespace, notes):
    if not cmds.namespace(exists=":" + namespace):
        return
    current = (cmds.namespaceInfo(currentNamespace=True, absoluteName=True) or ":").lstrip(":")
    if current == namespace or current.startswith(namespace + ":"):
        cmds.namespace(setNamespace=":")
    nested = cmds.namespaceInfo(":" + namespace, listOnlyNamespaces=True, recurse=True) or []
    for child in sorted(nested, key=lambda ns: -ns.count(":")) + [":" + namespace]:
        name = child if child.startswith(":") else ":" + child
        if not cmds.namespace(exists=name):
            continue
        left = cmds.namespaceInfo(name, listOnlyDependencyNodes=True) or []
        if not left:
            cmds.namespace(removeNamespace=name)
        elif all(cmds.nodeType(node) in SINGLETONS for node in left):
            # Maya's own managers, made inside the rig's namespace when its import was the
            # scene's first (measured: Maya will not delete them): they move to the root.
            cmds.namespace(removeNamespace=name, mergeNamespaceWithRoot=True)
        else:
            notes.append("Namespace {0} kept: it holds nodes of no character.".format(
                name.lstrip(":")))


def _confirm(text):
    """Maya's confirm; True to go on. Batch has nobody to answer (a verify, a test): it goes on."""
    if cmds.about(batch=True):
        return True
    answer = cmds.confirmDialog(
        title="Animation Setup - Delete", message=text, icon="warning",
        button=["Delete", "Cancel"], defaultButton="Cancel", cancelButton="Cancel",
        dismissString="Cancel")
    return answer == "Delete"


def delete_selected(selection=None, confirm=None):
    """The press: the characters the selection names, asked about, deleted. Returns the line."""
    picked, unowned, paths = selected_characters(selection)
    if not paths:
        return NOTHING_SELECTED
    if not picked:
        return NOT_A_CHARACTER
    p = plan(picked)
    if p.refusal:
        return p.refusal
    if not (confirm or _confirm)(confirm_text(p.summaries, [maya_rigs.label(r) for r in p.disconnects],
                                              p.foreign)):
        return CANCELLED
    return execute(p, len(unowned))
