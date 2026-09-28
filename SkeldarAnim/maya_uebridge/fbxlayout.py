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


def unswizzled(t):
    """`t` out of the wrapper's space: t . W, i.e. (x, z, -y) -- `swizzled` undone. Pure."""
    return (t[0], t[2], -t[1])


# how near the wrapper's turn and a zero root orient must be to count as the layout standing
LAYOUT_TOLERANCE = 1e-3                 # matrix elements
ORIENT_TOLERANCE = 0.01                 # degrees


def in_layout(parent_type, parent_world, root_jo):
    """Pure: does `root` already stand in Cascadeur's layout -- under a plain transform (not a
    joint) whose world matrix is WRAP_ROTATE at the origin, unscaled, its own jointOrient near
    zero? (2026-09-28: the Creep arrives in the scene the way its FBX has it.) `parent_world` is
    the 16 floats of the parent's worldMatrix, None with no parent."""
    if parent_type != "transform" or not parent_world:
        return False
    wanted = list(_euler_matrix(WRAP_ROTATE))
    if max(abs(a - b) for a, b in zip(parent_world, wanted)) > LAYOUT_TOLERANCE:
        return False
    om = _om()
    q = om.MTransformationMatrix(_euler_matrix(root_jo)).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(min(1.0, abs(q.w)))) <= ORIENT_TOLERANCE


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


def jo_before(jo):
    """`jo_after` undone: JO . W, the orient a root out of the wrapper needs to keep its world."""
    om = _om()
    m = _euler_matrix(jo) * _euler_matrix(WRAP_ROTATE)
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


def root_in_layout(root):
    """`in_layout` asked of the scene: (True, parent long path) when `root` stands under a
    Cascadeur-layout Null already, else (False, parent or "")."""
    parent = (cmds.listRelatives(root, parent=True, fullPath=True) or [""])[0]
    if not parent:
        return False, ""
    return (in_layout(cmds.nodeType(parent), cmds.getAttr(parent + ".worldMatrix[0]"),
                      tuple(cmds.getAttr(root + ".jointOrient")[0])), parent)


def _route_translate(root, inverse=False):
    """Put `root`'s translate into the wrapper's space -- x' = x, y' = -z, z' = y -- without
    touching a key: a curve is routed (through a negating multDoubleLinear for -z), a static
    channel's value is rewritten. `inverse` goes the other way, out of the wrapper's space --
    x = x', y = z', z = -y'. Returns what `_unroute_translate` needs to put it back."""
    record = {"sources": {}, "values": {}, "nodes": []}
    conversions = set(cmds.ls(type="unitConversion") or [])
    for channel in TRANSLATE:
        plug = root + "." + channel
        src = cmds.listConnections(plug, source=True, destination=False, plugs=True) or []
        record["sources"][channel] = src[0] if src else None
        record["values"][channel] = cmds.getAttr(plug)
        if src:
            cmds.disconnectAttr(src[0], plug)
    current = tuple(record["values"][c] for c in TRANSLATE)
    if inverse:
        values = unswizzled(current)
        feeds = (("translateX", 1.0), ("translateZ", 1.0), ("translateY", -1.0))
    else:
        values = swizzled(current)
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
def _named(node, name):
    """`node` called `name` in the root namespace for the length of the block, whatever else
    answers to it held aside as HOLD_PREFIX + name; both put back by UUID. Yields (its long
    path, "") -- or (None, reason) when Maya would not give it the name."""
    uuid = cmds.ls(node, uuid=True)[0]
    original = node.split("|")[-1]
    held, renamed = [], False
    try:
        if original != name:
            for other in cmds.ls(":" + name, long=True) or []:
                held.append(cmds.ls(other, uuid=True)[0])
                cmds.rename(other, HOLD_PREFIX + name)
            got = cmds.rename(cmds.ls(uuid, long=True)[0], ":" + name)
            renamed = True
            if got.split("|")[-1] != name:
                yield None, ("could not name %s %s (Maya gave %s) - exported in the plain layout"
                             % (original, name, got))
                return
        yield cmds.ls(uuid, long=True)[0], ""
    finally:
        if renamed:
            for path in cmds.ls(uuid, long=True) or []:
                cmds.rename(path, ":" + original if ":" not in original else original)
        for other in held:
            for path in cmds.ls(other, long=True) or []:
                cmds.rename(path, name)


@contextlib.contextmanager
def flattened(root):
    """The PLAIN layout for a root standing in Cascadeur's (2026-09-28: the Creep arrives under its
    `Armature`): for the length of the block `root` is out at world level with the wrapper's turn
    back on its jointOrient (`jo_before`) and its translate out of the wrapper's space
    (`unswizzled`, a curve routed, never edited) -- the file every export wrote before 2026-09-25,
    which the roads into Unreal still take. A root not in the layout: nothing to do. Yields
    (None, "") or (None, reason) when the root's drivers are not ones this can move; everything is
    put back in a `finally`, found again by UUID."""
    standing, parent = root_in_layout(root)
    if not standing:
        yield None, ""
        return
    _parent, kinds = root_state(root)
    mode, reason = layout_plan("", kinds)
    if mode is None:
        # not one this can move: the file goes out in the layout the root stands in -- its Null
        # included, named WRAPPER_NAME -- and says so, rather than bones missing their Null
        with _named(parent, WRAPPER_NAME) as (null, why):
            yield null, why or reason.replace(
                "plain layout", "layout it stands in (under %s)" % WRAPPER_NAME)
        return
    root_uuid = cmds.ls(root, uuid=True)[0]
    parent_uuid = cmds.ls(parent, uuid=True)[0]
    jo, record, moved = None, None, False
    try:
        cmds.parent(cmds.ls(root_uuid, long=True)[0], world=True, relative=True)
        moved = True
        now = cmds.ls(root_uuid, long=True)[0]
        jo = tuple(cmds.getAttr(now + ".jointOrient")[0])
        _set(now + ".jointOrient", jo_before(jo))
        if mode in ("keyed", "static"):
            record = _route_translate(now, inverse=True)
        yield None, ""
    finally:
        now = (cmds.ls(root_uuid, long=True) or [None])[0]
        if now and record is not None:
            _unroute_translate(now, record)
        if now and jo is not None:
            _set(now + ".jointOrient", jo)
        home = (cmds.ls(parent_uuid, long=True) or [None])[0]
        if now and moved and home:
            cmds.parent(now, home, relative=True)


@contextlib.contextmanager
def wrapped(root, name):
    """For the length of the block, `root` stands under a Null `name` rotated WRAP_ROTATE.

    Yields (the wrapper's long path, "") -- or (None, reason) when the root's drivers are not
    ones this can move without editing a key, or the name cannot be had; nothing is left
    changed then. The name is freed first (the Creep skeleton's meshes stand under a group
    `|Creep`, which would make the wrapper `Creep1`): whatever answers to it is held aside as
    HOLD_PREFIX + name. Everything is put back in a `finally`, found again by UUID -- the
    re-parent changes every path below the root (trap 16).

    A root already standing in the layout (2026-09-28: the Creep arrives that way) is exported
    as it is: its own Null, called `name` in the root namespace for the length of the block --
    the exporter writes whatever the node is called, a rig's namespace included (trap 61).
    """
    standing, parent = root_in_layout(root)
    if standing:
        with _named(parent, name) as (null, reason):
            yield null, reason
        return
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
