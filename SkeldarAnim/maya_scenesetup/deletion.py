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

from maya_scenetabs import scope

import maya_rigs

# `strangers`: children of the character's outliner group (2026-10-02) that are none of its -- the
# animator's own props parked in the folder. They name no character and are kept on Delete.
Character = collections.namedtuple("Character", "kind label namespace root rig parts strangers",
                                   defaults=((),))
Plan = collections.namedtuple(
    "Plan", "characters tops core doomed namespaces riders disconnects foreign summaries refusal "
            "kept layers", defaults=((), ()))

# A node carrying a user attribute that starts with one of these is ours (a weapon, a space, the
# camera, the CoM, a label, a record...), never a stranger in a character's group.
OUR_ATTR_PREFIXES = ("skeldar", "mayaWeapon", "mayaArmor", "mayaSceneSetup", "rigPicker")

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
LABEL_MARKER = "skeldarClipLabel"    # cliplabel.MARKER: the clip's name under a character
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


def doomed_layers(layers, going, keep=()):
    """The animation layers to delete with the character. Pure.

    `layers`: {name: (parent or None, set of the nodes it holds - its members' nodes and its blend
    nodes, [child layer names])}; `going`: the nodes the delete takes. A layer goes when it held
    something that goes, or a child layer of it goes, and it holds nothing that stays and every
    child of it goes too. A layer that never held the character (an empty one of the animator's), a
    root layer (no parent) and a `keep` one stay - Scene Tabs' tab root has a parent (the session's
    root), and went with its tab's last character until 2026-10-29. 2026-10-16: «удалять и слои в
    которых находился персонаж (только если там нет объектов которые не относятся к удаляемому)».
    """
    keep = set(keep or ())
    verdict = {}

    def goes(name):
        if name in verdict:
            return verdict[name]
        verdict[name] = False                                 # a cycle never deletes
        parent, nodes, children = layers[name]
        kids = [goes(child) for child in children if child in layers]
        verdict[name] = bool(parent) and name not in keep and nodes <= going and all(kids) and (
            bool(nodes & going) or any(kids))
        return verdict[name]

    return [name for name in layers if goes(name)]


def emptied_roots(layers, doomed, keep=()):
    """Root layers every child of which goes, holding nothing themselves: Maya's editor removes an
    emptied BaseAnimation with its last layer. `keep`: roots of other tools (Scene Tabs'). Pure."""
    out = []
    for name, (parent, nodes, children) in layers.items():
        if parent or nodes or name in keep or not children:
            continue
        if all(child in doomed for child in children):
            out.append(name)
    return out


def layers_note(names):
    """The confirm's line on the animation layers that go. Pure."""
    if not names:
        return ""
    shown = list(names)[:6]
    more = len(names) - len(shown)
    return ("Their animation {0}, holding nothing else - deleted: ".format(
        "layer" if len(names) == 1 else "layers") + ", ".join(shown)
            + (" and {0} more".format(more) if more else ""))


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
    """The characters `path` belongs to: under one of its parts, or in its namespace -- and not
    under one of its group's strangers (the animator's own prop in the folder). Pure."""
    return [c for c in characters
            if (in_namespace(path, c.namespace)
                or any(_under(path, part) for part in c.parts))
            and not any(_under(path, s) for s in getattr(c, "strangers", ()) or ())]


def strangers(children, parts, namespace, recorded, uuid_of, attrs_of):
    """The children of a character's outliner group that are none of the character's: not a
    part, nor above or under one, not in its namespace, not recorded by its Add, carrying none of
    our markers (`OUR_ATTR_PREFIXES`). `parts` must not hold the group itself. Pure over the two
    injected questions.

    2026-10-02: the group is the folder the animator opens the outliner on, and a prop dropped
    into it would otherwise go with the character on Delete, unnamed."""
    out = []
    for child in children or []:
        if any(_under(child, part) or _under(part, child) for part in parts or []):
            continue
        if in_namespace(child, namespace):
            continue
        if recorded and uuid_of(child) in recorded:
            continue
        if any(attr.startswith(OUR_ATTR_PREFIXES) for attr in attrs_of(child) or []):
            continue
        out.append(child)
    return out


def kept_note(kept):
    """The line's word on the strangers moved out of a group. Pure."""
    if not kept:
        return ""
    return "Kept at world level (not the character's): {0}.".format(
        ", ".join(path.split("|")[-1] for path in kept))


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


def confirm_text(summaries, disconnects=(), foreign=(), kept=(), layers=()):
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
    if kept:
        shown = [path.split("|")[-1] for path in kept][:6]
        more = len(kept) - len(shown)
        lines += ["", "Not theirs, in their group - moved out to world level and kept: "
                  + ", ".join(shown) + (" and {0} more".format(more) if more else "")]
    if layers:
        lines += ["", layers_note(layers)]
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


def _having(nodes, attr):
    """The long paths among `nodes` that carry `attr`: ONE `ls` of their plugs (a node without
    the attribute answers nothing). An attributeQuery a node cost 0.74 s on a rig's 1500
    transforms for four markers; this 0.09 s (2026-10-27)."""
    nodes = [node for node in nodes if node]
    if not nodes:
        return set()
    return set(cmds.ls([node + "." + attr for node in nodes], objectsOnly=True, long=True) or [])


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
            if path and (_marked(path, bonedrive.MARKER) or _marked(path, camera.MARKER)):
                path = camera.control_of(path) or path      # the camera's control with it
                if path not in out:
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


def _com_groups(root, marker=COM_MARKER):
    out = []
    if root and cmds.objExists(root):
        for node in cmds.listConnections(root + ".message", source=False, destination=True) or []:
            path = (cmds.ls(node, long=True) or [None])[0]
            if path and _marked(path, marker) and path not in out:
                out.append(path)
    return out


def _clip_labels(root):
    """The clip's name under the character (2026-10-02, `cliplabel`): linked to the root by
    message. A rig's lies under its group already; a bare skeleton's stands at world level."""
    return _com_groups(root, LABEL_MARKER)


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


def _character_group(path):
    """The character's outliner group (2026-10-02), or None for one added before the groups.
    Its display layer is a DG node touching only the group, so it goes as garbage."""
    found = maya_rigs.group_of(path) if path else None
    return [found] if found else []


def _strangers_of(group, parts, namespace, recorded_uuids):
    """`strangers` over the scene: the group's children (long paths)."""
    if not group or not cmds.objExists(group):
        return []
    children = cmds.listRelatives(group, children=True, fullPath=True) or []
    others = [part for part in parts if part != group]
    return strangers(children, others, namespace, recorded_uuids, _uuid,
                     lambda node: cmds.listAttr(node, userDefined=True) or [])


def _rig_character(rig):
    if rig.namespace:
        tops = [top for top in cmds.ls(assemblies=True, long=True) or []
                if in_namespace(top, rig.namespace)]
    else:
        tops = [rig.group] + ([rig.skeleton_root] if rig.skeleton_root else [])
    if getattr(rig, "character", ""):
        tops = [rig.character] + tops
    joints = maya_rigs.rig_paths(rig)
    roots = [rig.skeleton_root] if rig.skeleton_root else []
    parts = tops + _skinned_meshes(roots) + _drivers(joints) + _spaces(joints) \
        + sum((_com_groups(root) for root in roots), []) \
        + sum((_clip_labels(root) for root in roots), [])
    group = getattr(rig, "character", "") or ""
    return Character("rig", "{0} (rig)".format(maya_rigs.label(rig)), rig.namespace,
                     rig.skeleton_root or "", rig, _raise(parts),
                     _strangers_of(group, parts, rig.namespace, set()))


def _skeleton_character(root):
    uuids, label = recorded(root)
    joints = _joints(root)
    group = _character_group(root)
    parts = group + [root] + _skinned_meshes([root]) + _drivers(joints) \
        + _spaces(joints) + _com_groups(root) + _clip_labels(root) \
        + _recorded_tops(uuids)
    leaf = root.split("|")[-1]
    shown = "{0} ({1})".format(label, leaf) if label else "{0} (skeleton)".format(leaf)
    return Character("skeleton", shown, "", root, None, _raise(parts),
                     _strangers_of(group[0] if group else "", parts,
                                   maya_rigs.namespace_of(root), uuids))


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
    transforms = cmds.ls(list(core), type="transform", long=True) or []
    for path in sorted(_having(transforms, armor.NAMESPACE)):
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
    nodes = cmds.ls(nodes, long=True) or []
    for key, attr in (("weapon", bonedrive.MARKER), ("armor piece", armor.MARKER),
                      ("camera", camera.MARKER), ("CoM", COM_MARKER)):
        counts[key] += len(_having(nodes, attr))
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


def _layer_roots_kept():
    """Scene Tabs' layer roots: never ours to delete (trap 248)."""
    try:
        from maya_scenetabs import records
    except ImportError:
        return lambda name: False
    def kept(name):
        leaf = name.split(":")[-1]
        rest = leaf[len(records.TAB_LAYER_ROOT):]
        return leaf == records.LAYER_ROOT or (
            leaf.startswith(records.TAB_LAYER_ROOT) and (rest == "" or rest.isdigit()))
    return kept


def _anim_layers(going):
    """UUIDs of the animation layers the delete takes (and of a root it empties). Reads only."""
    names = cmds.ls(type="animLayer") or []
    if not names:
        return []
    layers, uuid_of = {}, {}
    for name in names:
        uuid_of[name] = _uuid(name)
        held = set()
        for plug in cmds.animLayer(name, query=True, attribute=True) or []:
            held.update(cmds.ls(plug.split(".")[0], uuid=True) or [])
        held.update(cmds.ls(cmds.animLayer(name, query=True, blendNodes=True) or [],
                            uuid=True) or [])
        parent = cmds.animLayer(name, query=True, parent=True) or None
        layers[name] = (parent, held, list(cmds.animLayer(name, query=True, children=True) or []))
    kept = _layer_roots_kept()
    keep = [n for n in layers if kept(n)]
    doomed = doomed_layers(layers, going, keep)
    doomed += emptied_roots(layers, doomed, keep=keep)
    return [uuid_of[name] for name in doomed if uuid_of.get(name)]


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
    kept = outermost(sum((list(getattr(c, "strangers", ()) or ()) for c in chars), []))
    core = _descendants(tops) - _descendants(kept)
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
    for node in sorted(_having(cmds.ls(list(core), type="transform", long=True) or [],
                               RECORD_NODES)):
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
    layers = _anim_layers(set(core) | set(doomed))
    return Plan(chars, outermost(tops), core, doomed, namespaces, riders, disconnects, foreign,
                summaries, refusal, kept, layers)


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


def _existing(paths):
    """`paths` that still stand, in their order."""
    if not paths:
        return []
    standing = set(cmds.ls(paths, long=True) or [])
    return [path for path in paths if path in standing]


def _unlock(paths):
    """Unlock the locked among `paths`: one query for all, one at a time when Maya
    answers a list of another length."""
    if not paths:
        return
    locks = cmds.lockNode(paths, query=True, lock=True) or []
    if len(locks) != len(paths):
        locks = [cmds.lockNode(path, query=True, lock=True)[0] for path in paths]
    locked = [path for path, on in zip(paths, locks) if on]
    if locked:
        cmds.lockNode(locked, lock=False)


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
        moved = _keep(p.kept)
        if moved:
            notes.append(kept_note(moved))
        _untrack_com(p.core)
        everything = set(p.core) | set(p.doomed)
        #  every UUID resolved ONCE (a delete renames nothing that stays), the locks
        #  read in one query (2026-10-27: a query a node cost 0.25 s on one rig)
        paths = [path for path in (_path(uuid) for uuid in everything) if path]
        _unlock(paths)
        _delete(outermost([path for path in (_path(_uuid(t)) for t in p.tops) if path]))
        left = _existing(paths)
        dag = outermost([path for path in left if cmds.objectType(path, isAType="dagNode")])
        _delete(dag)
        _delete(_existing(paths))
        layers = _delete_layers(p.layers)
        if layers:
            notes.append("{0} deleted: {1}.".format(
                "Animation layer" if len(layers) == 1 else "Animation layers",
                ", ".join(name.split(":")[-1] for name in layers)))
        for namespace in sorted(p.namespaces, key=lambda ns: -ns.count(":")):
            _remove_namespace(namespace, notes)
        from maya_scenesetup import connections
        connections.sweep_orphans()
    finally:
        cmds.undoInfo(closeChunk=True)
    gone = before - len(cmds.ls() or [])
    return deleted_message([c.label for c in p.characters], gone, unowned, notes)


def layer_names(uuids):
    """The layers among `uuids` the animator made (roots left out), by name."""
    out = []
    for uuid in uuids or []:
        path = _path(uuid)
        if path and cmds.animLayer(path, query=True, parent=True):
            out.append(path)
    return out


def _delete_layers(uuids):
    """Delete the layers, children before their parent. Returns the names of the non-root ones."""
    shown = layer_names(uuids)
    left = [u for u in uuids or [] if _path(u)]
    while left:
        leaves = [u for u in left
                  if not any(_uuid(c) in left for c in
                             cmds.animLayer(_path(u), query=True, children=True) or [])]
        if not leaves:
            leaves = left
        for uuid in leaves:
            path = _path(uuid)
            if path:
                if cmds.lockNode(path, query=True, lock=True)[0]:
                    cmds.lockNode(path, lock=False)
                cmds.delete(path)
        left = [u for u in left if u not in leaves and _path(u)]
    return shown


def _keep(kept):
    """The strangers out of their character's group to world level, where they stood (the group is
    an identity folder; `parent -world` keeps the world matrix either way). Returns their paths."""
    out = []
    for uuid in [_uuid(path) for path in kept or []]:
        path = _path(uuid) if uuid else None
        if not path or path.count("|") == 1:
            continue
        cmds.parent(path, world=True)
        out.append(_path(uuid) or path)
    return out


def _remove_namespace(namespace, notes):
    if not cmds.namespace(exists=":" + namespace):
        return
    current = (cmds.namespaceInfo(currentNamespace=True, absoluteName=True) or ":").lstrip(":")
    inside = current == namespace or current.startswith(namespace + ":")
    if inside:
        scope.enter_active(cmds)
    try:
        _remove_namespaces(namespace, notes)
    finally:
        # Maya leaves the root current after a remove (measured 2026-10-29): a tab's next Add
        # Character landed outside the tab, where no tool of the tab finds it
        if not inside and current and cmds.namespace(exists=":" + current):
            cmds.namespace(setNamespace=":" + current)
        else:
            scope.enter_active(cmds)


def _remove_namespaces(namespace, notes):
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
                                              p.foreign, p.kept, layer_names(p.layers))):
        return CANCELLED
    return execute(p, len(unowned))
