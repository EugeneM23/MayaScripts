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
"""

import collections

import maya.cmds as cmds

# namespace: "" for the root namespace. control_set / main: scene names.
# group: the rig's top DAG node (long path). skeleton_root: the game
# skeleton the rig drives (long path), or "" when it drives none.
Rig = collections.namedtuple("Rig", "namespace control_set main group skeleton_root")

CONTROL_SET = "ControlSet"      # AdvancedSkeleton's own set of every control
MAIN = "Main"                   # ... and its top control

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
        if under(path, rig.group) or under(path, rig.skeleton_root):
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


# ----------------------------------------------------------------- scene

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
    namespace; the group is `Main`'s top ancestor, never `|Group` by name.
    """
    out = []
    for control_set in control_sets():
        namespace = namespace_of(control_set)
        mains = cmds.ls(node(namespace, MAIN), long=True) or []
        if len(mains) != 1:
            continue
        group = top_of(mains[0])
        out.append(Rig(namespace, control_set, mains[0], group,
                       skeleton_root_of(namespace, group)))
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
