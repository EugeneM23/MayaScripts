"""Which AdvancedSkeleton rig -- the one question every module asks, answered once.

2026-09-08, the animator: «сделаем так чтобы наша вся система поддерживала
работу с множеством ригов, я должен иметь возможность добавить в сцену много
ригов как через add так и через import». Until then both retarget modules,
Scene Setup and the bridge addressed THE rig by name -- `Main`, `ControlSet`,
`|Group`, `FKWrist_R` -- and Maya makes every one of those ambiguous on a
second import.

**A rig is a NAMESPACE.** Add Character imports each rig into its own
(`Manny_Rig`, `Manny_Rig1`, ...; measured 2026-09-08: every one of the file's
2713 nodes lands under it, none stray), so `ns:Main`, `ns:ControlSet`,
`ns:FKWrist_R` name exactly one rig's nodes. A rig the animator already has in
the ROOT namespace -- every scene made before this -- is the rig whose
namespace is "", found through its group and its skeleton instead.

**Which rig an operation acts on**: the one whose control, bone or mesh is
selected; else the only rig in the scene; else a refusal that names the rigs.
Two rigs selected is no answer. This is the toolset's standing rule
(selection, then the sole candidate, then refuse) applied to rigs.

Spec: docs/superpowers/specs/2026-09-08-many-rigs-design.md

**A character has ONE outliner group since 2026-10-02** («все части которые относятся к одному
персонажу ригу были в одной группе ... пользователь открыл аутлайнер и сразу все понял»; spec
docs/superpowers/specs/2026-10-02-character-groups-design.md): a locked identity transform at world
level marked `skeldarCharacterGroup` (`CHARACTER_MARKER`), holding the AdvancedSkeleton `Group`, the
game skeleton, the asset's other tops and everything parked for the character. A rig's `group` stays
AdvancedSkeleton's own -- the topmost ancestor of `Main` BELOW a character group (`top_below`) -- so
"the skeleton root is outside the group", `foreign_constraints` and `rig_of` keep their meaning; the
character group is `character`. A rig added before has no character group and `character` is "".
"""

import collections

import maya.cmds as cmds

# namespace: "" for the root namespace. control_set / main: scene names.
# group: AdvancedSkeleton's top DAG node (long path) -- below the character group when there is
# one. skeleton_root: the game skeleton the rig drives (long path), or "" when it drives none.
# character: the character group holding all of it (long path), "" for a rig added before
# 2026-10-02.
Rig = collections.namedtuple("Rig", "namespace control_set main group skeleton_root character",
                             defaults=("",))

CONTROL_SET = "ControlSet"      # AdvancedSkeleton's own set of every control
MAIN = "Main"                   # ... and its top control

# A character's outliner group (2026-10-02): the marker (its catalog label, for the record) and the
# message link from the character's root (a rig's game skeleton root, a skeleton's root).
CHARACTER_MARKER = "skeldarCharacterGroup"
CHARACTER_ROOT = "skeldarCharacterRoot"

NO_RIG = "no AdvancedSkeleton rig in this scene (ControlSet/Main missing)"


# ------------------------------------------------------------------ pure

def leaf(path):
    """`|a:Group|a:Main` -> `Main`."""
    return path.split("|")[-1].split(":")[-1]


def namespace_of(path):
    """The namespace of a path's own node, "" for the root namespace. Pure.

    `|Manny_Rig:Group|Manny_Rig:Main` -> `Manny_Rig`; a nested
    `clip:mixamorig:Hips` -> `clip:mixamorig`; `|Group|Main` -> "".
    """
    short = (path or "").split("|")[-1]
    return short.rsplit(":", 1)[0] if ":" in short else ""


def node(rig, leaf_name):
    """The scene name of one of the rig's nodes. Pure.

    `rig` may be a Rig or a bare namespace string; "" (the root namespace)
    gives the plain name, which is exactly the spelling every module used
    before rigs had namespaces -- so a legacy scene is the identity case.
    """
    namespace = rig.namespace if isinstance(rig, Rig) else (rig or "")
    return namespace + ":" + leaf_name if namespace else leaf_name


def label(rig):
    """How a message names a rig: its namespace, or its group for the
    root-namespace one."""
    if rig.namespace:
        return rig.namespace
    return (rig.group or "").lstrip("|") or "the rig"


def under(path, top):
    """True when `path` is `top` or lies below it. Pure, separator-aware."""
    return bool(top) and (path == top or path.startswith(top + "|"))


def rig_of(path, rigs):
    """Which rig a path belongs to, or None. Pure.

    A path in a rig's (non-empty) namespace is that rig's -- a control, a
    bone, a mesh, the display layer; that is what the namespace is for. A
    root-namespace rig has no such mark, so its nodes are known by lying
    under its group or its skeleton. Nothing else is anybody's.
    """
    namespace = namespace_of(path)
    if namespace:
        for rig in rigs:
            if rig.namespace and namespace == rig.namespace:
                return rig
    for rig in rigs:
        if under(path, rig.group) or under(path, rig.skeleton_root) \
                or under(path, getattr(rig, "character", "")):
            return rig
    return None


def choose_rig(selected_rigs, all_rigs):
    """(rig, refusal): the selection's one rig, else the sole rig. Pure.

    `selected_rigs` is `rig_of` over the selection, Nones included; they are
    dropped, and repeats (three controls of one rig) collapse. Two different
    rigs selected is no answer, and so is a scene with several rigs and
    nothing selected -- the refusal names them, since selecting is the cure.
    """
    picked = []
    for rig in selected_rigs or []:
        if rig is not None and rig not in picked:
            picked.append(rig)
    if len(picked) == 1:
        return picked[0], ""
    if picked:
        return None, ("two rigs selected (%s) - select controls of one only"
                      % ", ".join(label(r) for r in picked))
    if not all_rigs:
        return None, NO_RIG
    if len(all_rigs) == 1:
        return all_rigs[0], ""
    return None, ("%d rigs in the scene (%s) - select any control or bone of "
                  "the one you mean" % (len(all_rigs),
                                        ", ".join(label(r) for r in all_rigs)))


def top_of(path):
    """`|a|b|c` -> `|a`. Pure."""
    return "|" + path.lstrip("|").split("|")[0]


def shallowest(paths):
    """The topmost path, ties by name, or "". Pure."""
    if not paths:
        return ""
    return sorted(paths, key=lambda p: (p.count("|"), p))[0]


def top_below(path, groups):
    """The topmost ancestor-or-self of `path` that is not one of `groups` (the character groups):
    `|Manny_Rig_Character|Manny_Rig:Group|...|Main` -> `|Manny_Rig_Character|Manny_Rig:Group`, and
    with no character group above it, `top_of`. Pure."""
    parts = [p for p in (path or "").split("|") if p]
    for i in range(1, len(parts) + 1):
        node = "|" + "|".join(parts[:i])
        if node not in groups:
            return node
    return path


# ----------------------------------------------------------------- scene

def is_character_group(node):
    """True when `node` is a character's outliner group (`CHARACTER_MARKER`)."""
    return bool(node) and cmds.objExists(node) \
        and cmds.attributeQuery(CHARACTER_MARKER, node=node, exists=True)


def character_groups():
    """Every character group in the scene (they stand at world level), long paths."""
    return [top for top in cmds.ls(assemblies=True, long=True) or [] if is_character_group(top)]


def group_of(path):
    """The character group `path` is, or lies under, or None. Found by its marker, never by name;
    a node outside every character group (a legacy character, the animator's own) answers None."""
    if not path or not cmds.objExists(path):
        return None
    long_path = (cmds.ls(path, long=True) or [path])[0]
    top = top_of(long_path)
    return top if is_character_group(top) else None


def marked_near_top(marker, depth=3):
    """Transforms carrying `marker` among the top `depth` levels of the DAG, long paths: the
    weapon / armor spaces groups stand at world level (a skeleton added before 2026-10-02), in a
    character group (a bare skeleton's), or in a rig's AdvancedSkeleton group -- which is one
    level deeper since the character groups (`|Manny_Rig_Character|Manny_Rig:Group|ArmorSpaces`)."""
    found, level = [], cmds.ls(assemblies=True, long=True) or []
    for _ in range(depth):
        nxt = []
        for node in level:
            if cmds.attributeQuery(marker, node=node, exists=True):
                found.append(node)
            nxt += cmds.listRelatives(node, children=True, type="transform", fullPath=True) or []
        level = nxt
    return found


def group_root(group):
    """The character root a character group's message link names, long path, or None."""
    if not is_character_group(group) or \
            not cmds.attributeQuery(CHARACTER_ROOT, node=group, exists=True):
        return None
    found = cmds.listConnections(group + "." + CHARACTER_ROOT, source=True, destination=False) or []
    paths = cmds.ls(found[:1], long=True) or []
    return paths[0] if paths else None

def control_sets():
    """Every `ControlSet` in the scene, whatever its namespace."""
    return [s for s in (cmds.ls(type="objectSet") or []) if leaf(s) == CONTROL_SET]


def _constrained_joints(namespace):
    """Joints of one namespace that carry a constraint: the game skeleton
    our DeformationSystem drives, which is what tells it from an imported
    clip (both retarget modules' own rule, per namespace)."""
    out = []
    for joint in cmds.ls(type="joint", long=True) or []:
        if namespace_of(joint) != namespace:
            continue
        if cmds.listRelatives(joint, children=True, type="constraint"):
            out.append(joint)
    return out


def skeleton_root_of(namespace, group):
    """The rig's game skeleton root: the shallowest constrained joint of its
    namespace outside its group, or ""."""
    return shallowest([j for j in _constrained_joints(namespace)
                       if not under(j, group)])


def rigs():
    """Every rig in the scene, sorted by namespace (the root one first).

    A rig is a `ControlSet` with exactly one `Main` beside it in the same
    namespace; the group is `Main`'s top ancestor below the character group
    (`top_below`), never `|Group` by name; the character group, when there is
    one, is `Main`'s top ancestor.
    """
    out = []
    groups = None
    for control_set in control_sets():
        namespace = namespace_of(control_set)
        mains = cmds.ls(node(namespace, MAIN), long=True) or []
        if len(mains) != 1:
            continue
        if groups is None:
            groups = set(character_groups())
        group = top_below(mains[0], groups)
        top = top_of(mains[0])
        out.append(Rig(namespace, control_set, mains[0], group,
                       skeleton_root_of(namespace, group), top if top in groups else ""))
    return sorted(out, key=lambda rig: rig.namespace)


def rig_paths(rig):
    """Long paths of every joint that belongs to the rig: its own
    deformation joints under the group and the game skeleton it drives."""
    out = []
    for top in (rig.group, rig.skeleton_root):
        if not top or not cmds.objExists(top):
            continue
        out.append(top) if cmds.objectType(top) == "joint" else None
        out.extend(cmds.listRelatives(top, allDescendents=True, type="joint",
                                      fullPath=True) or [])
    return out


def current_rig(selection=None):
    """(rig, refusal) for the scene as it stands.

    `selection` defaults to Maya's; a caller with a selection of its own
    (the bridge's verify runs) passes it.
    """
    all_rigs = rigs()
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    return choose_rig([rig_of(path, all_rigs) for path in selection], all_rigs)


def find(namespace):
    """The rig in `namespace`, or None."""
    for rig in rigs():
        if rig.namespace == namespace:
            return rig
    return None
