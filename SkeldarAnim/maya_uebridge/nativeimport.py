"""A clip kept in its OWN skeleton, as a character of the scene (2026-10-02, the Auto card).

The animator: «если скрипт обнаружит что совпадений нету то импортируем в сцену родной риг или
скелет». With the Auto card picked, a clip whose skeleton is no character of ours
(`skeletonmatch`) is not retargeted: the skeleton it was imported in - and what its file brought
with it, Unreal's preview mesh skinned to it (`uescripts.export_script(..., preview_mesh=True)`) -
stays, and becomes a character like a skeleton row of Add Character:

- standing on the floor point a drop or a square slot names: the root's own translate keys are
  offset (its parent's space at the clip's first frame), so no wrapper is left - the FBX exporter
  writes a bone's ancestors (trap 182), and `fbxlayout` reads a root under a moved transform as
  "plain, with a note";
- in ONE outliner group with its own display layer (`chargroup.make`), named for its largest
  skinned mesh (`Kwang_GDC_Character`), else the clip;
- with plain names: the clip's namespace - and any the file nested in it (Mixamo's `mixamorig:`) -
  merged into the root namespace after the group exists, so nothing at world level can collide;
- in the next free palette colour (asked: Unreal's FBX carries no textures);
- recorded for Characters > Delete (`deletion.record_import`) and labelled with the clip's name
  (`cliplabel.label_skeleton`).

After that it is a skeleton like any other: Skeleton x Onto selected puts a later clip on it,
Export FBX writes its bones, Delete takes it whole, Colour repaints it. Everything here runs
unrecorded (trap 115: the import flushed the undo queue, a chunk would only half-undo).

Spec: docs/superpowers/specs/2026-10-02-auto-character-import-design.md
"""

import traceback

import maya.cmds as cmds

LABEL = "{0} [own skeleton]"
AXES = ("X", "Y", "Z")


# --------------------------------------------------------------------- pure

def native_base(meshes, namespace, root_leaf):
    """What the character's group is named for: its largest mesh (`meshes` [(transform leaf,
    vertex count)]), else the clip's namespace, else its root. Pure."""
    named = [(count, leaf) for leaf, count in meshes or [] if leaf]
    if named:
        return sorted(named, key=lambda pair: (-pair[0], pair[1]))[0][1]
    return namespace or root_leaf or "Character"


def local_delta(delta, parent_inverse):
    """A world move (dx, dy, dz) in the space of a parent whose world-inverse matrix is
    `parent_inverse` (flat, row-major, Maya's row vectors) - its rotation and scale, not its
    translation; None is the world. Pure."""
    if not parent_inverse:
        return tuple(delta)
    x, y, z = delta
    m = parent_inverse
    return (x * m[0] + y * m[4] + z * m[8],
            x * m[1] + y * m[5] + z * m[9],
            x * m[2] + y * m[6] + z * m[10])


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def depth_first(namespaces):
    """Namespaces deepest first, so a nested one empties into its parent's place. Pure."""
    return sorted(set(n for n in namespaces or [] if n),
                  key=lambda name: (-name.count(":"), name))


def _plural(count, word):
    return "{0} {1}{2}".format(count, word, "" if count == 1 else "es" if word == "mesh"
                               else "s")


def line_for(name, base, joints, meshes, info, why="", placed="", notes=()):
    """What the status says after a clip was kept in its own skeleton. Pure."""
    span = ""
    if info.get("start") is not None:
        span = ", frames {0:g}-{1:g}".format(info["start"], info["end"])
    head = "{0}: {1}".format(name, why) if why else name
    line = "{0} - in its own skeleton {1}: {2}, {3}{4}".format(
        head, base, _plural(joints, "joint"), _plural(meshes, "mesh"), span)
    for text in [placed] + list(notes or ()):
        if text:
            line = "{0}  |  {1}".format(line, text)
    return line


# --------------------------------------------------------------------- scene

def _uuid(node):
    return (cmds.ls(node, uuid=True) or [None])[0]


def _long(uuid):
    return (cmds.ls(uuid, long=True) or [None])[0] if uuid else None


def _namespace_of(path):
    node = path.split("|")[-1]
    return node.rsplit(":", 1)[0].lstrip(":") if ":" in node else ""


def _in(namespace, path):
    owner = _namespace_of(path)
    return owner == namespace or owner.startswith(namespace + ":")


def _meshes(nodes):
    """[(transform leaf, vertex count)] of the renderable meshes among `nodes`."""
    out = []
    for shape in cmds.ls(nodes, type="mesh", noIntermediate=True, long=True) or []:
        parent = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        try:
            count = int(cmds.polyEvaluate(shape, vertex=True) or 0)
        except Exception:                                    # noqa: BLE001
            count = 0
        if parent:
            out.append((leaf(parent[0]), count))
    return out


def _curve_on(plug):
    found = cmds.listConnections(plug, source=True, destination=False,
                                 type="animCurve") or []
    return found[0] if found else None


def move_root(root, delta):
    """Offset the root's translate - its keys, else its values - by the world move `delta`, in
    its parent's space. Returns a note for what could not move ("" when everything did)."""
    parent = cmds.listRelatives(root, parent=True, fullPath=True)
    inverse = cmds.getAttr(parent[0] + ".worldInverseMatrix[0]") if parent else None
    local = local_delta(delta, inverse)
    stuck = []
    for axis, offset in zip(AXES, local):
        if abs(offset) < 1e-9:
            continue
        plug = "{0}.translate{1}".format(root, axis)
        curve = _curve_on(plug)
        if curve is not None:
            count = cmds.keyframe(curve, query=True, keyframeCount=True) or 0
            if count:
                cmds.keyframe(curve, edit=True, relative=True, valueChange=offset,
                              index=(0, count - 1))
                continue
        if cmds.getAttr(plug, settable=True):
            cmds.setAttr(plug, cmds.getAttr(plug) + offset)
        else:
            stuck.append("translate" + axis)
    if stuck:
        return "the root's {0} could not move - it stands where the clip has it".format(
            ", ".join(stuck))
    return ""


def merge_into_root(namespace):
    """The clip's namespace and every one nested in it merged into the root namespace, deepest
    first. Returns a note ("" when every one went)."""
    nested = cmds.namespaceInfo(namespace, listOnlyNamespaces=True, recurse=True) or []
    left = []
    for each in depth_first(nested + [namespace]):
        each = each.lstrip(":")
        if not cmds.namespace(exists=":" + each):
            continue
        try:
            cmds.namespace(removeNamespace=":" + each, mergeNamespaceWithRoot=True)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            left.append(each)
    if left:
        return "names kept in {0}".format(", ".join(left))
    return ""


def keep(namespace, info, source, name, point=None, why=""):
    """(line, failure, base): the clip imported into `namespace` (its root `source`) kept as a
    character of the scene in its own skeleton, standing on the floor `point` at the clip's first
    frame (None: where the clip has it). `why` is what the match said («no skeleton of ours ...»).
    `base` is what its group is named for (`Kwang_GDC`)."""
    from maya_scenesetup import character, chargroup, cliplabel, colour, deletion
    from maya_uebridge import rigimport

    nodes = cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True, recurse=True,
                               dagPath=True) or []
    uuids = [u for u in (cmds.ls(nodes, uuid=True) or []) if u]
    root_uuid = _uuid(source)
    if not root_uuid:
        return "", "{0}: the clip's root is gone".format(name), ""
    notes = []
    with character._unrecorded():
        placed = ""
        if point is not None:
            start = rigimport.root_at(source, info.get("start"))
            dx, dy, dz = rigimport.shift_for(point, start)
            stuck = move_root(source, (dx, dy, dz))
            if stuck:
                notes.append(stuck)
            else:
                placed = "standing at floor ({0}, {1})".format(int(round(point[0])),
                                                              int(round(point[2])))
        meshes = _meshes(nodes)
        base = native_base(meshes, namespace, leaf(source))
        label = LABEL.format(base)
        tops = [t for t in cmds.ls(assemblies=True, long=True) or [] if _in(namespace, t)]
        try:
            chargroup.make(base, label, _long(root_uuid), tops)
        except Exception as exc:                             # noqa: BLE001
            traceback.print_exc()
            notes.append(character.group_failed_note(exc))
        merged = merge_into_root(namespace)
        if merged:
            notes.append(merged)
        live = [p for u in uuids for p in (cmds.ls(u, long=True) or [])]
        root = _long(root_uuid)
        try:
            colour.paint_nodes(live, colour.free_colour().rgb, chargroup.legal(base))
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            notes.append("not painted")
        try:
            deletion.record_import(root, uuids, label)
        except Exception as exc:                             # noqa: BLE001
            print("Auto import: no record for Delete ({0})".format(exc))
        cliplabel.label_skeleton(root, name)
        joints = len(cmds.ls(live, type="joint") or [])
        line = line_for(name, base, joints, len(meshes), info, why, placed, notes)
    return line, "", base
