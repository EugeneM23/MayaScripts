"""Export in Cascadeur's layout: a Null `Armature` over `root`, `root` at zero.

2026-09-25. The animator moves animation Maya <-> Cascadeur and chose one layout for every
export, Cascadeur's own. Cascadeur writes a Y-up file whose skeleton hangs under a Null rotated
-90 deg X (named for the character in Cascadeur's own files, and in ours that morning; since the
evening `Armature` for every character -- «появилось требование чтобы верхняя группа
называлась Armature»); `root` stands beneath it with no orientation of its own,
its translation in the Null's Z-up space -- which is also Unreal's root space. We keep that
turn on `root`'s jointOrient in the scene (Maya is Y-up and stays Y-up: AdvancedSkeleton's
author advises against Z-up, and Unreal is left-handed anyway). So for the length of an export
`root` is re-parented under a temporary wrapper, given `jointOrient . W^-1` (zero for our
usual -90 X) and `t . W^-1` = (x, -z, y), and everything goes back in a `finally`. The world
pose of every joint never changes and no key is edited.

Measured before building: our export, Unreal's and Cascadeur's agree bone for bone below the
root; only where the Z-up turn lives differs. `FBXExportUpAxis z` is no way round it: it writes
a Z-up header and leaves +90 on the root, and reads back 169 units off.

Spec: docs/superpowers/specs/2026-09-25-cascadeur-export-layout-design.md
"""
import contextlib
import math

import maya.cmds as cmds

WRAP_ROTATE = (-90.0, 0.0, 0.0)     # Cascadeur's Null: Z-up content in a Y-up file
WRAPPER_NAME = "Armature"           # the Null's name, one for every character (2026-09-25 evening)
# the catalog key Add Character wrote on a root on 2026-09-25 alone (the morning's per-character
# wrapper); nothing writes it since, but a root tagged that day must still not carry it into a file
TAG = "skeldarCharacter"
HOLD_PREFIX = "rpHold_"             # the bridge's own prefix for a name held aside
TRANSLATE = ("translateX", "translateY", "translateZ")
ROTATE = ("rotateX", "rotateY", "rotateZ")


def _om():
    # lazy: the bridge's tests install a fake `maya` with no `api` (trap 60's family)
    import maya.api.OpenMaya as om
    return om


# ------------------------------------------------------------------ pure

def swizzled(t):
    """`t` in the wrapper's space: t . W^-1 for W = Rx(-90), i.e. (x, -z, y). Pure."""
    return (t[0], -t[2], t[1])


def _euler_matrix(degrees):
    return _om().MEulerRotation(*[math.radians(v) for v in degrees]).asMatrix()


def jo_after(jo):
    """The jointOrient that keeps `root`'s world under the wrapper: JO . W^-1 (XYZ, degrees).

    A joint's world is R . JO . parent (row vectors); with the parent now W, R . JO' . W equals
    R . JO exactly, so the rotate channels -- keyed or driven -- need nothing.
    """
    om = _om()
    m = _euler_matrix(jo) * _euler_matrix(WRAP_ROTATE).inverse()
    e = om.MTransformationMatrix(m).rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
    return tuple(math.degrees(v) for v in (e.x, e.y, e.z))


def layout_plan(parent, kinds):
    """How `root` goes under the wrapper, as (mode, reason). Pure.

    constrained -- every driven channel a constraint's (the rig's `root <- Main`): it reads
                   parentInverseMatrix and jointOrient, so it re-solves under the wrapper;
    keyed       -- curves or nothing: translate routed through a swizzle, rotate untouched
                   (the jointOrient change absorbs the wrapper);
    static      -- nothing at all: the translate values rewritten, written back after;
    None        -- anything else, with the reason: the plain layout is exported instead.
    """
    if parent:
        return None, ("root stands under %s - exported in the plain layout"
                      % parent.split("|")[-1])
    odd = sorted(set(k for k in kinds.values() if k not in (None, "curve", "constraint")))
    if odd:
        return None, "root is driven by %s - exported in the plain layout" % ", ".join(odd)
    present = set(k for k in kinds.values() if k)
    if present == {"constraint"}:
        return "constrained", ""
    if "constraint" in present:
        return None, "root mixes keys and a constraint - exported in the plain layout"
    return ("keyed" if present else "static"), ""


# ------------------------------------------------------------------ scene

def _kind(plug):
    src = cmds.listConnections(plug, source=True, destination=False,
                               skipConversionNodes=True) or []
    if not src:
        return None
    node_type = cmds.nodeType(src[0])
    if node_type.startswith("animCurve"):
        return "curve"
    if node_type.endswith("Constraint"):
        return "constraint"
    return "pairBlend" if node_type == "pairBlend" else "other"


def root_state(root):
    """(parent long path or "", {channel: kind}) for `root`."""
    parent = (cmds.listRelatives(root, parent=True, fullPath=True) or [""])[0]
    return parent, dict((c, _kind(root + "." + c)) for c in TRANSLATE + ROTATE)


@contextlib.contextmanager
def tag_held(root):
    """Our TAG off `root` for the length of the block, put back after.

    The FBX exporter writes a node's user attributes into the file (measured: `skeldarCharacter`
    rode into every export as a property of `root`), and Unreal reads the root's properties as
    the game's own data (trap 40's Pose_* / MoveData_*). Our bookkeeping stays home.
    """
    uuid = (cmds.ls(root, uuid=True) or [None])[0]
    value = None
    if uuid and cmds.attributeQuery(TAG, node=root, exists=True):
        value = cmds.getAttr(root + "." + TAG) or ""
        cmds.deleteAttr(root + "." + TAG)
    try:
        yield
    finally:
        now = (cmds.ls(uuid, long=True) or [None])[0] if uuid else None
        if now and value is not None and not cmds.attributeQuery(TAG, node=now, exists=True):
            cmds.addAttr(now, longName=TAG, dataType="string")
            cmds.setAttr(now + "." + TAG, value, type="string")


@contextlib.contextmanager
def unwrapped():
    """The plain layout: nothing to do."""
    yield None, ""


def _set(plug, value):
    locked = cmds.getAttr(plug, lock=True)
    if locked:
        cmds.setAttr(plug, lock=False)
    if isinstance(value, (tuple, list)):
        cmds.setAttr(plug, *value, type="double3")
    else:
        cmds.setAttr(plug, value)
    if locked:
        cmds.setAttr(plug, lock=True)


def _route_translate(root):
    """Put `root`'s translate into the wrapper's space -- x' = x, y' = -z, z' = y -- without
    touching a key: a curve is routed (through a negating multDoubleLinear for -z), a static
    channel's value is rewritten. Returns what `_unroute_translate` needs to put it back."""
    record = {"sources": {}, "values": {}, "nodes": []}
    conversions = set(cmds.ls(type="unitConversion") or [])
    for channel in TRANSLATE:
        plug = root + "." + channel
        src = cmds.listConnections(plug, source=True, destination=False, plugs=True) or []
        record["sources"][channel] = src[0] if src else None
        record["values"][channel] = cmds.getAttr(plug)
        if src:
            cmds.disconnectAttr(src[0], plug)
    values = swizzled(tuple(record["values"][c] for c in TRANSLATE))
    feeds = (("translateX", 1.0), ("translateZ", -1.0), ("translateY", 1.0))
    for target, (source, sign), value in zip(TRANSLATE, feeds, values):
        src = record["sources"][source]
        plug = root + "." + target
        if src is None:
            _set(plug, value)
        elif sign > 0:
            cmds.connectAttr(src, plug, force=True)
        else:
            negate = cmds.createNode("multDoubleLinear", name="cascadeurLayoutNegate")
            record["nodes"].append(negate)
            cmds.setAttr(negate + ".input2", -1.0)
            cmds.connectAttr(src, negate + ".input1", force=True)
            cmds.connectAttr(negate + ".output", plug, force=True)
    record["nodes"] += [n for n in cmds.ls(type="unitConversion") or [] if n not in conversions]
    return record


def _unroute_translate(root, record):
    for channel in TRANSLATE:
        plug = root + "." + channel
        for src in cmds.listConnections(plug, source=True, destination=False, plugs=True) or []:
            cmds.disconnectAttr(src, plug)
    # A node is deleted with the animCurves feeding it -- measured: deleting the negate node took
    # `root_translateZ` along -- so its inputs are let go first.
    for node in record["nodes"]:
        if not cmds.objExists(node):
            continue
        pairs = cmds.listConnections(node, source=True, destination=False, plugs=True,
                                     connections=True) or []
        for dst, src in zip(pairs[0::2], pairs[1::2]):
            cmds.disconnectAttr(src, dst)
        cmds.delete(node)
    for channel in TRANSLATE:
        plug = root + "." + channel
        if record["sources"][channel]:
            cmds.connectAttr(record["sources"][channel], plug, force=True)
        else:
            _set(plug, record["values"][channel])


@contextlib.contextmanager
def wrapped(root, name):
    """For the length of the block, `root` stands under a Null `name` rotated WRAP_ROTATE.

    Yields (the wrapper's long path, "") -- or (None, reason) when the root's drivers are not
    ones this can move without editing a key, or the name cannot be had; nothing is left
    changed then. The name is freed first (the Creep skeleton's meshes stand under a group
    `|Creep`, which would make the wrapper `Creep1`): whatever answers to it is held aside as
    HOLD_PREFIX + name. Everything is put back in a `finally`, found again by UUID -- the
    re-parent changes every path below the root (trap 16).
    """
    parent, kinds = root_state(root)
    mode, reason = layout_plan(parent, kinds)
    if mode is None:
        yield None, reason
        return
    root_uuid = cmds.ls(root, uuid=True)[0]
    held, wrapper_uuid, jo, record, parented = [], None, None, None, False
    try:
        for node in cmds.ls(":" + name, long=True) or []:
            held.append(cmds.ls(node, uuid=True)[0])
            cmds.rename(node, HOLD_PREFIX + name)
        wrapper = cmds.createNode("transform", name=":" + name)
        wrapper_uuid = cmds.ls(wrapper, uuid=True)[0]
        if wrapper.split("|")[-1] != name:
            yield None, ("could not name the wrapper %s (Maya gave %s) - exported in the plain "
                         "layout" % (name, wrapper))
            return
        cmds.setAttr(wrapper + ".rotate", *WRAP_ROTATE, type="double3")
        cmds.parent(cmds.ls(root_uuid, long=True)[0], wrapper, relative=True)
        parented = True
        now = cmds.ls(root_uuid, long=True)[0]
        jo = tuple(cmds.getAttr(now + ".jointOrient")[0])
        _set(now + ".jointOrient", jo_after(jo))
        if mode in ("keyed", "static"):
            record = _route_translate(now)
        yield cmds.ls(wrapper_uuid, long=True)[0], ""
    finally:
        now = (cmds.ls(root_uuid, long=True) or [None])[0]
        if now and record is not None:
            _unroute_translate(now, record)
        if now and jo is not None:
            _set(now + ".jointOrient", jo)
        if now and parented:
            cmds.parent(now, world=True, relative=True)
        for path in (cmds.ls(wrapper_uuid, long=True) or []) if wrapper_uuid else []:
            cmds.delete(path)
        for uuid in held:
            for path in cmds.ls(uuid, long=True) or []:
                cmds.rename(path, name)
