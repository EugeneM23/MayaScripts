"""Tools > 1P Setup (2026-10-16): a 3P take split for first person, on one press.

The animator: «мы нажимаем кнопку и у нас все распределяется по слоям. Включив слой нижней
анимации мы получим нашу анимацию нижней части и стабилизированый верх, но ... старая анимация
для третего лица на верхней части ... в слое хранится на всякий случай».

One press on any part of a rig, in one undo chunk:
- the rig's geometry to 1P (`Main.view` = 1) where it has the switch;
- a knot on `FKSpine3_M` (Tools > Knot), so the chest lives on its own - drawn since 2026-10-21
  as the chest control `Chest_1P_ctrl`, a red square;
- the rig's Root control made when it has none (`rootcontrol`);
- Tools > Layer: the lower body and the knot onto `_3P_Lower_Body`, the upper body onto
  `_3P_Upper_Body` - the base keeps the first frame's pose - then the knot's turn moved from
  Lower to Upper (both add by component, so the sum is the take exactly);
- Camera Setup on `camera_root` when it has none; the camera's control (`Camera_ctrl`, under
  Main) moved under the chest control, its motion kept as local keys in the chest's space
  (2026-10-20, through the control since 2026-10-21). A Bake of the chest sends it back to Main.

Maya will not start a node name with a digit (`3P_...` becomes `P_...`), hence the `_`.
Spec: docs/superpowers/specs/2026-10-16-tools-1p-setup-design.md.
"""

import maya.cmds as cmds
import maya_timewarp

from maya_tools import knotplan as plan
from maya_tools import knots
from maya_tools import layerbake

LOWER = "_3P_Lower_Body"
UPPER = "_3P_Upper_Body"
MARKER = "skeldarFirstPerson"            # on both layers: the rig's namespace
KNOT_CONTROL = "FKSpine3_M"
VIEW_ATTR = "view"                       # Main.view: 0 3P, 1 1P (Manny, Orc D)
SPINE_SWITCH = "FKIKSpine_M"
CAMERA_BONE = "camera_root"

#  The lower body: these controls, and every control whose name holds a leg word (2026-10-16,
#  asked: Spine1-2 with the hips - Spine3 rides its knot, so they cannot move the chest).
LOWER_EXACT = frozenset(("Main", "Root_ctrl", "RootX_M", "FKRoot_M", "HipSwinger_M",
                         "FKSpine1_M", "FKSpine2_M"))

#  The chest control (2026-10-21, the animator: «нужно изменить создание узла на создание
#  нормального контроллера (квадратной формы красного цвета)»): the knot on FKSpine3_M drawn as a
#  red square around the chest, named for what it is. Still a knot to Tools (Bake, Remove,
#  Attach): only its drawing and its name changed.
#  The controls' display layers (2026-10-21, the animator: «слои отображения с контроллерами
#  верхней и нижней части тела ... по умолчанию мы сразу выключим контроллер нижней части тела
#  и отключим анимационный слой верхней части тела что бы он был стабилизирован»).
LOWER_CONTROLS = "_1P_Lower_Controls"
UPPER_CONTROLS = "_1P_Upper_Controls"
DEFAULTS_WORDS = "stabilized: %s muted, %s hidden"

CHEST_NAME = "Chest_1P_ctrl"
CHEST_MARKER = "skeldar1PChest"          # the rig's namespace
CHEST_GROW = 1.35                        # the square over FKSpine3_M's drawing
CHEST_LEAST = 8.0                        # cm, half side when the control draws nothing
LOWER_WORDS = ("Hip_", "Knee", "Ankle", "Toes", "Heel", "Leg", "Foot", "IKSpine")

NO_RIG = "1P Setup: select any part of a rig"
NO_KNOT_CONTROL = "1P Setup: %s has no %s - the setup needs AdvancedSkeleton's spine"
SPINE_IK = ("1P Setup: %s's spine is in IK (%s.FKIKBlend) - switch the spine to FK in "
            "Connections first")
ALREADY = ("1P Setup: %s is set up already (%s) - Ctrl+Z, or delete the layers and the knot "
           "first")


# -------------------------------------------------------------------- pure

def leaf(path):
    """The control's name without its path and namespace."""
    return path.split("|")[-1].split(":")[-1]


def is_lower(name):
    name = leaf(name)
    return name in LOWER_EXACT or any(word in name for word in LOWER_WORDS)


def split(controls):
    """(lower, upper) of `controls` (paths), in their order; the knot's control in neither."""
    lower, upper = [], []
    for path in controls:
        if leaf(path) == KNOT_CONTROL:
            continue
        (lower if is_lower(path) else upper).append(path)
    return lower, upper


def message(rig, view, lower, upper, camera, notes):
    parts = ["1P Setup on %s" % rig,
             "1P mesh on" if view == "on" else ("1P mesh already on" if view == "already"
                                                else "no 1P mesh on this rig"),
             "%s on %s" % (KNOT_CONTROL, CHEST_NAME),
             "%s: %d control%s + the chest's travel" % (LOWER, lower, "" if lower == 1 else "s"),
             "%s: %d control%s + the chest's turn" % (UPPER, upper, "" if upper == 1 else "s"),
             camera]
    return " | ".join(parts + list(notes))


def chest_square(box, grow=CHEST_GROW, least=CHEST_LEAST):
    """The chest control's curve (pure): a square in the plane FKSpine3_M's drawing is widest in
    (`box` its CVs' (min, max) in its own space), about the drawing's centre, `grow` times its
    larger half extent; a plain square of half side `least` in XZ without a box."""
    from maya_scenesetup import curvectrl
    if not box:
        return curvectrl.square(least, ("x", "z"))
    lo, hi = box
    extents = [hi[i] - lo[i] for i in range(3)]
    axes = curvectrl.plane_of(extents)
    half = max(extents[curvectrl.AXES[axes[0]]], extents[curvectrl.AXES[axes[1]]]) / 2.0
    centre = tuple((lo[i] + hi[i]) / 2.0 for i in range(3))
    return curvectrl.square(max(half * grow, 1e-3), axes, centre)


# ------------------------------------------------------------------- scene

def setup_layers(namespace):
    """Our 1P layers standing for the rig in `namespace`."""
    return [layer for layer in cmds.ls(type="animLayer") or []
            if knots._has(layer, MARKER) and knots._get(layer, MARKER) == namespace]


def chest_of(rig):
    """The rig's 1P chest control (a knot of ours marked with its namespace), long path, or
    None."""
    for top in knots.knots():
        if knots._has(top, CHEST_MARKER) and knots._get(top, CHEST_MARKER) == rig.namespace:
            return top
    return None


def display_layer_names(rig_name):
    """(lower, upper) display layer names for the rig (pure)."""
    base = (rig_name or "Rig").split(":")[-1]
    return ("%s%s" % (base, LOWER_CONTROLS), "%s%s" % (base, UPPER_CONTROLS))


def camera_control(bone):
    from maya_scenesetup import camera
    return camera.control_for(bone)


def _curve_shapes(paths):
    """The drawn shapes of `paths` (a control's own curves - never its transform: AS nests its FK
    controls, and a hidden spine control's transform would hide the chest's under it)."""
    out = []
    for path in paths:
        if not path or not cmds.objExists(path):
            continue
        for shape in cmds.listRelatives(path, shapes=True, fullPath=True,
                                        noIntermediate=True) or []:
            if cmds.nodeType(shape) in ("nurbsCurve", "locator") and shape not in out:
                out.append(shape)
    return out


#  Maya's default index colours (Window > Settings > Colour > Index), for `colorIndex -q`, which
#  answers None in batch mode.
INDEX_RGB = (
    (0.47, 0.47, 0.47), (0.0, 0.0, 0.0), (0.25, 0.25, 0.25), (0.6, 0.6, 0.6),
    (0.608, 0.0, 0.157), (0.0, 0.016, 0.376), (0.0, 0.0, 1.0), (0.0, 0.275, 0.098),
    (0.149, 0.0, 0.263), (0.784, 0.0, 0.784), (0.541, 0.282, 0.2), (0.247, 0.137, 0.122),
    (0.6, 0.149, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.255, 0.6),
    (1.0, 1.0, 1.0), (1.0, 1.0, 0.0), (0.392, 0.863, 1.0), (0.263, 1.0, 0.639),
    (1.0, 0.69, 0.69), (0.894, 0.675, 0.475), (1.0, 1.0, 0.388), (0.0, 0.6, 0.329),
    (0.631, 0.416, 0.188), (0.62, 0.631, 0.188), (0.408, 0.631, 0.188), (0.188, 0.631, 0.365),
    (0.188, 0.631, 0.631), (0.188, 0.404, 0.631), (0.435, 0.188, 0.631), (0.631, 0.188, 0.416))


def override_rgb(enabled, use_rgb, rgb, index, index_rgb=None):
    """The colour a drawing override shows (pure): its RGB, else its index's colour; None when
    it is off or index 0 (Maya's default)."""
    if not enabled:
        return None
    if use_rgb:
        return tuple(rgb)
    if not index:
        return None
    if index_rgb:
        return tuple(index_rgb)
    return INDEX_RGB[index] if 0 <= index < len(INDEX_RGB) else None


def _own_colour(node):
    try:
        index = cmds.getAttr(node + ".overrideColor")
        index_rgb = None
        try:
            index_rgb = cmds.colorIndex(index, query=True) if index else None
        except Exception:                                        # noqa: BLE001
            index_rgb = None
        return override_rgb(cmds.getAttr(node + ".overrideEnabled"),
                            cmds.getAttr(node + ".overrideRGBColors"),
                            cmds.getAttr(node + ".overrideColorRGB")[0], index, index_rgb)
    except Exception:                                            # noqa: BLE001
        return None


_RENDERING = {}


def invert(to_display, target, rounds=3, steps=24):
    """The colour `to_display` maps onto `target` (pure): per channel, bisection on [0, 1] with
    the others held, a few rounds (a view transform is monotonic per channel, nearly separable)."""
    rgb = list(target)
    for _ in range(rounds):
        for i in range(3):
            lo, hi = 0.0, 1.0
            for _ in range(steps):
                mid = (lo + hi) / 2.0
                probe = list(rgb)
                probe[i] = mid
                if to_display(probe)[i] < target[i]:
                    lo = mid
                else:
                    hi = mid
            rgb[i] = (lo + hi) / 2.0
    return tuple(rgb)


def _rendering(rgb):
    """`rgb` as the display shows an index colour, in the rendering space the object colour is
    read in (2026-10-21, measured: with colour management on, ACES, a wireColorRGB equal to the
    index's colour drew (0, 119, 182) where the index drew (0, 65, 153)). Unmanaged: as it is."""
    if rgb in _RENDERING:
        return _RENDERING[rgb]
    out = rgb
    try:
        if cmds.colorManagementPrefs(query=True, cmEnabled=True):
            out = invert(lambda c: cmds.colorManagementConvert(toDisplaySpace=list(c)), rgb)
    except Exception:                                            # noqa: BLE001
        out = rgb
    _RENDERING[rgb] = out
    return out


def keep_colour(shape):
    """A display layer drives its members' drawing override, colour included: a control in one
    loses its colour (measured 2026-10-21, a GUI Maya: index and RGB overrides alike, on the shape
    or its transform). The object colour (`useObjectColor` 2, `wireColorRGB`) is not part of the
    override and survives the layer - the shape's colour moved there first. The RGB or None."""
    parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
    rgb = _own_colour(shape) or (_own_colour(parents[0]) if parents else None)
    if rgb is None:
        return None
    rgb = _rendering(tuple(rgb))
    cmds.setAttr(shape + ".wireColorRGB", *rgb)
    cmds.setAttr(shape + ".useObjectColor", 2)
    return rgb


def _display_layers(rig, lower, upper):
    """The two display layers of the 1P controls (2026-10-21): the lower body's controls and the
    upper body's (the chest and the camera control with them), by their SHAPES, the lower one
    hidden. Marked with the rig's namespace. Their names."""
    import maya_rigs
    names = display_layer_names(maya_rigs.label(rig))
    made = []
    for name, paths, visible in ((names[0], lower, 0), (names[1], upper, 1)):
        layer = cmds.createDisplayLayer(name=name, empty=True, noRecurse=True)
        shapes = _curve_shapes(paths)
        for shape in shapes:
            keep_colour(shape)
        if shapes:
            cmds.editDisplayLayerMembers(layer, shapes, noRecurse=True)
        cmds.setAttr(layer + ".visibility", visible)
        knots._set_string(layer, MARKER, rig.namespace)
        made.append(layer)
    return made


def display_layers_of(namespace):
    """Our 1P display layers standing for the rig in `namespace`."""
    return [layer for layer in cmds.ls(type="displayLayer") or []
            if knots._has(layer, MARKER) and knots._get(layer, MARKER) == namespace]


def _make_chest(knot, control, namespace):
    """The knot on FKSpine3_M made the chest control: a red square around the chest, its name,
    its marker. Its long path."""
    from maya_scenesetup import curvectrl
    uuid = knots._uuid(knot)
    curvectrl.reshape(knot, chest_square(curvectrl.local_box(control)), curvectrl.RED)
    cmds.rename(knots._by_uuid(uuid), CHEST_NAME)
    knot = knots._by_uuid(uuid)
    for shape in cmds.listRelatives(knot, shapes=True, fullPath=True) or []:
        cmds.rename(shape, knot.split("|")[-1] + "Shape")
    knot = knots._by_uuid(uuid)
    knots._set_string(knot, CHEST_MARKER, namespace)
    return knot


def _controls(rig):
    members = cmds.sets(rig.control_set, query=True) or []
    out = []
    for path in cmds.ls(members, long=True, type="transform") or []:
        if path not in out:
            out.append(path)
    return out


def _spine_in_ik(rig):
    import maya_rigs
    node = maya_rigs.node(rig, SPINE_SWITCH)
    plug = node + ".FKIKBlend"
    if not cmds.objExists(node) or not cmds.attributeQuery("FKIKBlend", node=node,
                                                           exists=True):
        return ""
    values = cmds.keyframe(plug, query=True, valueChange=True) or [cmds.getAttr(plug)]
    return node if max(values) > 1e-6 else ""


def _camera_bone(rig):
    if not rig.skeleton_root:
        return None
    joints = [rig.skeleton_root] + (cmds.listRelatives(rig.skeleton_root, allDescendents=True,
                                                       type="joint", fullPath=True) or [])
    found = [j for j in joints if leaf(j) == CAMERA_BONE]
    return found[0] if len(found) == 1 else None


def _layered(controls, rigs):
    """(controls something animates, refusal): Layer's own plan for each; a still one left."""
    out = []
    for path in controls:
        _info, refusal = layerbake._plan(path, rigs)
        if refusal:
            if refusal.startswith("nothing animates"):
                continue
            return None, "1P Setup: " + refusal
        out.append(path)
    return out, ""


def _new_layer(before):
    made = [layer for layer in cmds.ls(type="animLayer") or [] if layer not in before]
    return made[-1] if made else None


def _empty_layer(name):
    layer = cmds.animLayer(name)
    cmds.setAttr(layer + ".rotationAccumulationMode", 0)
    cmds.setAttr(layer + ".scaleAccumulationMode", 0)
    return layer


def move_curve(plug, source, target):
    """`plug`'s curve on additive layer `source` moved onto additive layer `target` - the same
    curve node, every key kept. False when `source` holds none for it."""
    curve = (cmds.animLayer(source, query=True, findCurveForPlug=plug) or [None])[0]
    if not curve:
        return False
    for dest in cmds.listConnections(curve + ".output", source=False, destination=True,
                                     plugs=True) or []:
        cmds.disconnectAttr(curve + ".output", dest)
    cmds.animLayer(source, edit=True, removeAttribute=plug)
    cmds.animLayer(target, edit=True, attribute=plug)
    node, attr = plug.split(".", 1)
    cmds.setKeyframe(node, attribute=attr, animLayer=target, identity=True,
                     time=cmds.keyframe(curve, query=True, timeChange=True)[0])
    temporary = cmds.animLayer(target, query=True, findCurveForPlug=plug)[0]
    dests = cmds.listConnections(temporary + ".output", source=False, destination=True,
                                 plugs=True) or []
    cmds.delete(temporary)
    for dest in dests:
        cmds.connectAttr(curve + ".output", dest, force=True)
    return True


def _view_on(rig):
    plug = rig.main + "." + VIEW_ATTR
    if not cmds.attributeQuery(VIEW_ATTR, node=rig.main, exists=True):
        return "none"
    if cmds.getAttr(plug) == 1:
        return "already"
    cmds.setAttr(plug, 1)
    return "on"


def _camera(bone, chest):
    """The camera's control under the chest control with its motion kept (`camera.move_control`:
    its world track re-expressed in the chest's space, Tools > Inside's road). A camera already
    set up with its control is kept as it is (a retarget made it, or the animator); one without
    a control (made before 2026-10-21), or none, is set up first (Camera Setup: the control under
    Main). With both layers on the camera plays the take; with Upper muted it rides the steadied
    chest and keeps its own motion relative to it. The words for the line."""
    from maya_scenesetup import bonedrive, camera
    control = camera.control_for(bone)
    if not control:
        keys = cmds.keyframe(bone, query=True, timeChange=True) or []
        start, end = bonedrive.union_range(cmds.playbackOptions(query=True, min=True),
                                           cmds.playbackOptions(query=True, max=True), keys)
        camera.setup(bone, start, end)
        control = camera.control_for(bone)
    if not control:
        return "no camera made"
    control = camera.move_control(control, chest, "Chest")
    return "%s follows %s with its motion, %s follows the camera" % (
        leaf(control), CHEST_NAME, CAMERA_BONE)


#  In 1P the hands and the weapon ride the chest (2026-10-21, the animator: «в режиме 1P IK руки
#  и оружие находились в паренте нашего Chest контрола. Это правило работает и для aim системы
#  оружия»). The IK arm controls are AdvancedSkeleton's and stay where they are: each rides an
#  Across knot inside the chest (Tools > Across, its motion kept, Remove / Bake give it back);
#  our weapon out of the hands and a weapon's Aim Mode controllers are moved under the chest.
IK_ARMS = ("IKArm_R", "IKArm_L")


def _arms_into(rig, chest):
    """The IK arm controls riding Across knots inside `chest`. (knots made, notes)."""
    import maya_rigs
    pairs, notes = [], []
    for leaf_name in IK_ARMS:
        found = cmds.ls(maya_rigs.node(rig, leaf_name), long=True) or []
        if not found:
            continue
        _info, refusal = knots._plan_object(found[0], "across")
        if refusal:
            notes.append("%s stays (%s)" % (leaf_name, refusal))
            continue
        pairs.append((found[0], chest))
    if not pairs:
        return [], notes
    before = set(knots.knots())
    line = knots.create_across(pairs, highlight=None)
    made = [k for k in knots.knots() if k not in before]
    if not made:
        notes.append("IK arms not in the chest: %s" % line)
    return made, notes


def _rig_weapons(rig):
    """Our weapons of this rig: marked nodes the rig answers for."""
    import maya_rigs
    from maya_scenesetup import bonedrive
    try:
        marked = cmds.ls("*." + bonedrive.MARKER, recursive=True, objectsOnly=True, long=True,
                         type="transform") or []
    except Exception:                                            # noqa: BLE001
        return []
    rigs = maya_rigs.rigs()
    out = []
    for weapon in dict.fromkeys(marked):
        owner = maya_rigs.rig_of(weapon, rigs)
        if owner is None:
            from maya_scenesetup import weaponspace
            hand = weaponspace.holding_hand(weapon)
            owner = maya_rigs.rig_of(hand, rigs) if hand else None
        if owner is not None and owner.namespace == rig.namespace:
            out.append(weapon)
    return out


def _free(node, channels):
    """The channels of `node` a bake may write: not locked, not driven but by curves."""
    out = []
    for ch in channels:
        plug = node + "." + ch
        if cmds.getAttr(plug, lock=True):
            continue
        src = cmds.listConnections(plug, source=True, destination=False, skipConversionNodes=True)
        if src and not all(cmds.objectType(s, isAType="animCurve") or
                           cmds.nodeType(s).startswith("animBlendNode") for s in src):
            continue
        out.append(ch)
    return out


def carry_into(nodes, parent, move):
    """`nodes` keep their world motion across `move()` (a DAG move putting them, or their group,
    under `parent`): each one's free translate / rotate baked back in its new space on every frame
    of the take - Tools > Inside's road for a node whose rotate may be locked (an aim controller)
    or driven (a weapon an aim turns). The nodes after (by UUID)."""
    from maya_tools import reparent
    span = reparent._take(nodes, [parent])
    uuids = [knots._uuid(n) for n in nodes]
    locs, temps = [], []
    for node in nodes:
        loc = cmds.spaceLocator(name="skeldar1PCarry_" + leaf(node))[0]
        loc = knots._by_uuid(knots._uuid(loc))
        cmds.setAttr(loc + ".rotateOrder", cmds.getAttr(node + ".rotateOrder"))
        temps.append(knots._constrain(cmds.parentConstraint, node, loc, maintainOffset=False))
        locs.append(loc)
    maya_timewarp.call(cmds.bakeResults, locs, attribute=list(knots.plan.CHANNELS),
                       time=(span[0], span[1]), simulation=True, sampleBy=1,
                       disableImplicitControl=True)
    cmds.delete([t for t in temps if cmds.objExists(t)])
    move()
    nodes = [knots._by_uuid(u) for u in uuids]
    cons = []
    for loc, node in zip(locs, nodes):
        free = _free(node, knots.plan.CHANNELS)
        st = [c[-1].lower() for c in knots.plan.TRANSLATE if c not in free] or "none"
        sr = [c[-1].lower() for c in knots.plan.ROTATE if c not in free] or "none"
        if len(st) == 3 and len(sr) == 3:
            continue
        cons.append(knots._constrain(cmds.parentConstraint, loc, node, maintainOffset=False,
                                     skipTranslate=st, skipRotate=sr))
        maya_timewarp.call(cmds.bakeResults, node, attribute=free, time=(span[0], span[1]),
                           simulation=True, sampleBy=1, disableImplicitControl=True)
    cmds.delete([c for c in cons if cmds.objExists(c)])
    for node in nodes:
        knots._filter_euler(node, _free(node, knots.plan.ROTATE))
    cmds.delete([l for l in locs if cmds.objExists(l)])
    return [knots._by_uuid(u) for u in uuids]


def _weapons_into(rig, chest):
    """Our weapons of the rig out of the hands, and every Aim Mode's controllers, moved under
    `chest` with their motion kept. The words."""
    from maya_scenesetup import bonedrive, weaponspace
    words = []
    chest_uuid = knots._uuid(chest)
    for weapon in _rig_weapons(rig):
        #  in a hand it rides the IK hand; on the floor it stays on the floor
        if not weaponspace.holding_hand(weapon) and not bonedrive.is_parked(weapon):
            uuid = knots._uuid(weapon)

            def move(uuid=uuid):
                cmds.parent(knots._by_uuid(uuid), knots._by_uuid(chest_uuid))
            carry_into([weapon], chest, move)
            words.append("%s in the chest" % leaf(weapon))
    for group in _rig_aims(rig):
        if aim_group_into(group, chest):
            words.append("%s in the chest" % leaf(group))
    return words


def _aim_groups():
    try:
        from maya_scenesetup import weaponaim
    except ImportError:
        return []
    return weaponaim.groups()


def _rig_aims(rig):
    """Every Aim Mode group of this rig's weapons: found from the group itself (its character
    group), from its weapon, or from the hand holding the weapon."""
    import maya_rigs
    from maya_scenesetup import weaponaim, weaponspace
    rigs = maya_rigs.rigs()
    out = []
    for group in _aim_groups():
        weapon = weaponaim.weapon_of_group(group)
        candidates = [group, weapon]
        if weapon:
            candidates.append(weaponspace.holding_hand(weapon))
        for node in candidates:
            owner = maya_rigs.rig_of(node, rigs) if node else None
            if owner is not None:
                if owner.namespace == rig.namespace:
                    out.append(group)
                break
    return out


def aim_group_into(group, chest):
    """A weapon's Aim Mode group under `chest`, its controllers' world motion kept. False when it
    stands there already."""
    from maya_scenesetup import weaponaim
    parents = cmds.listRelatives(group, parent=True, fullPath=True) or []
    if parents and parents[0] == chest:
        return False
    ctrls = list(weaponaim.controllers(group).values())
    group_uuid, chest_uuid = knots._uuid(group), knots._uuid(chest)

    def move():
        cmds.parent(knots._by_uuid(group_uuid), knots._by_uuid(chest_uuid))
    carry_into(ctrls, chest, move)
    return True


def aim_into_chest(weapon):
    """Aim Mode entered on a rig already in 1P (2026-10-21, the animator: «мы можем сперва
    создать эйм а потом нажать на 1p setup» - and the other way round): its group into the rig's
    chest. The words, "" when the rig is not in 1P."""
    import maya_rigs
    from maya_scenesetup import weaponaim, weaponspace
    group = weaponaim.group_of(weapon)
    if not group:
        return ""
    rigs = maya_rigs.rigs()
    owner = None
    for node in (group, weapon, weaponspace.holding_hand(weapon)):
        owner = maya_rigs.rig_of(node, rigs) if node else None
        if owner is not None:
            break
    chest = chest_of(owner) if owner is not None else None
    if not chest or not aim_group_into(group, chest):
        return ""
    return "the aim in %s (1P)" % CHEST_NAME


def _selected_bone(selection=None):
    """(camera_root of the character the selection names, refusal): a rig's, else a bare
    skeleton's."""
    import maya_rigs
    rig, refusal = maya_rigs.current_rig(selection)
    if rig is not None and not refusal:
        bone = _camera_bone(rig)
        return (bone, "") if bone else (None, "no %s on %s" % (CAMERA_BONE,
                                                               maya_rigs.label(rig)))
    from maya_scenesetup import skeleton
    root = skeleton.current_root()
    if not root:
        return None, refusal or "select any part of a character"
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or [])
    found = [j for j in joints if leaf(j) == CAMERA_BONE]
    return (found[0], "") if len(found) == 1 else (None, "no %s under %s"
                                                   % (CAMERA_BONE, leaf(root)))


@maya_timewarp.wrapped
def camera_parent(choice, selection=None):
    """Camera parent (2026-10-21): the selected character's camera control under Main / Root /
    Chest / World, its motion kept. The line."""
    from maya_scenesetup import camera
    bone, refusal = _selected_bone(selection)
    if refusal:
        return "Camera parent: " + refusal
    keep = cmds.ls(selection=True, long=True) or []
    line = camera.set_parent(bone, choice)
    kept = [n for n in keep if cmds.objExists(n)]
    if kept:
        cmds.select(kept, replace=True)
    return "Camera parent: " + line


@maya_timewarp.wrapped
def setup(selection=None):
    """The 1P Setup press. The line."""
    import maya_rigs
    rig, refusal = maya_rigs.current_rig(selection)
    if refusal or rig is None:
        return ("1P Setup: " + refusal) if refusal else NO_RIG
    name = maya_rigs.label(rig)
    standing = setup_layers(rig.namespace)
    if standing:
        return ALREADY % (name, ", ".join(standing))
    control = maya_rigs.node(rig, KNOT_CONTROL)
    if not cmds.objExists(control):
        return NO_KNOT_CONTROL % (name, KNOT_CONTROL)
    control = cmds.ls(control, long=True)[0]
    switch = _spine_in_ik(rig)
    if switch:
        return SPINE_IK % (name, leaf(switch))
    rigs = maya_rigs.rigs()
    all_lower, all_upper = split(_controls(rig))
    lower, upper = list(all_lower), list(all_upper)
    lower, refusal = _layered(lower, rigs)
    if refusal:
        return refusal
    upper, refusal = _layered(upper, rigs)
    if refusal:
        return refusal
    _info, refusal = knots._plan_object(control, "knot")
    if refusal:
        return "1P Setup: " + refusal
    bone = _camera_bone(rig)
    notes = []
    with knots._press("skeldar1PSetup"):
        view = _view_on(rig)
        from maya_scenesetup import rootcontrol
        rootcontrol.ensure(rig)            # a rig added before 2026-10-21 has none
        knots.create("knot", [control], highlight=None)
        knot = _make_chest(knots._knots_driving(control)[0], control, rig.namespace)
        before = set(cmds.ls(type="animLayer") or [])
        #  inside this press's chunk: Layer neither shows its window nor undoes anything itself
        line = layerbake.bake(lower + [knot], highlight=None, name=LOWER, cancellable=False)
        lower_layer = _new_layer(before)
        if not lower_layer:
            raise RuntimeError("the lower body did not bake: %s" % line)
        before = set(cmds.ls(type="animLayer") or [])
        if upper:
            line = layerbake.bake(upper, highlight=None, name=UPPER, cancellable=False)
            upper_layer = _new_layer(before)
            if not upper_layer:
                raise RuntimeError("the upper body did not bake: %s" % line)
        else:
            upper_layer = _empty_layer(UPPER)
            notes.append("nothing animates the upper body")
        for ch in ("rotateX", "rotateY", "rotateZ"):
            move_curve(knot + "." + ch, lower_layer, upper_layer)
        for layer in (lower_layer, upper_layer):
            knots._set_string(layer, MARKER, rig.namespace)
        if bone:
            words = _camera(bone, knot)
        else:
            words = "no %s on this rig - no camera" % CAMERA_BONE
        arm_knots, arm_notes = _arms_into(rig, knot)
        notes.extend(arm_notes)
        if arm_knots:
            notes.append("%s ride %s" % (" and ".join(leaf(k).replace("_across", "")
                                                       for k in arm_knots), CHEST_NAME))
        notes.extend(_weapons_into(rig, knot))
        knot = knots._by_uuid(knots._uuid(knot)) or knot
        layers = _display_layers(rig, all_lower, all_upper + [knot, control] + arm_knots
                                 + ([camera_control(bone)] if bone else []))
        #  stabilized by default (2026-10-21): the upper body's 3P motion muted, the lower
        #  body's controls hidden - the animator works the chest and the arms
        cmds.setAttr(upper_layer + ".mute", 1)
        notes.append(DEFAULTS_WORDS % (UPPER, layers[0]))
        cmds.select(knot, replace=True)
    return message(name, view, len(lower), len(upper), words, notes)
