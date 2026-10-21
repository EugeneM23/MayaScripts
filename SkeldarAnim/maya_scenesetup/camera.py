"""Put a camera on the camera bone, then let the camera drive the bone.

The animator wants to animate a camera, not a joint; the export wants the
joint. So the bone's motion is baked onto a real Maya camera and the bone is
then parent-constrained to it. After the press, the camera is the thing you
animate and the bone follows it exactly.

**The camera jumps into the bone's transform.** Same position, and only the
axes differ: a Maya camera looks down its own -Z and a UE camera bone does not.
That turn was measured 2026-08-17 from the animator's own `camera1` against
`camera_bone` -- (90, 0, 180) XYZ in the channel box -- and it is a rotation and
nothing else. Nothing in the scene changes it: "the reference camera does not
matter, only the rotation axes do", so the offset is a constant here and a
camera lying around somewhere cannot move the result. Any translation that ever
finds its way into the constant is stripped (`rotation_only`), because the one
thing the camera must not do is stand away from the bone.

Maya's matrices are row-vector: a child's world matrix is `local · parent`. So
the camera's world matrix is `OFFSET · bone_world`, and the bone's is
`OFFSET⁻¹ · camera_world`. Getting that order backwards produces a camera that
looks plausible from one angle and is wrong everywhere else.
"""

import math

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya_timewarp

from maya_scenetabs import scope

# camera_root since 2026-09-18 (the animator: «не camera bone привязывать к
# камере, а camera root»). At rest the two coincide on the rig (world
# matrices equal to 0.000000, measured), camera_bone being camera_root's
# child, so the measured axis turn below holds for either.
BONE = "camera_root"
MARKER = "mayaSceneSetupCamera"
CAMERA_NAME = "SceneSetup_camera"

# The camera's control (2026-10-21): the camera stands under it, the control carries the motion
# and lives under the rig's Main; its parent can be switched with the motion kept (`set_parent`).
CONTROL_MARKER = "mayaSceneSetupCameraControl"
CONTROL_NAME = "Camera_ctrl"
PARENT_MARKER = "skeldarCameraParent"       # which of PARENTS it stands under
PARENTS = ("Main", "Root", "Chest", "World")
PARENT_LINE = "%s follows %s now - its motion kept"
CONTROL_WORDS = " - animate %s (under %s)"
CONTROL_SIZE = 9.0                          # cm: the drawing's half width is 0.6 of it

# The turn between camera1 and camera_bone, measured in the user's scene.
AXIS_OFFSET = (-1.0, 0.0, 0.0, 0.0,
               0.0, 0.0, 1.0, 0.0,
               0.0, 1.0, 0.0, 0.0,
               0.0, 0.0, 0.0, 1.0)

# The game's lens (2026-10-15, the animator: «максимально правильный фов такой
# же как и у нас в игре atone»), read from the open Atone editor: the player's
# camera, `BP_Character`'s `PlayerCamera`, has FieldOfView 100, aspect 16:9,
# AspectRatio_MaintainXFOV (the project overrides neither) -- so 100 degrees is
# the HORIZONTAL angle -- and DefaultEngine.ini's NearClipPlane is 0.5 cm.
# Until then FOCAL was camera1's 16.494 mm: 95.0 degrees across the gate.
GAME_FOV = 100.0
GAME_ASPECT = 16.0 / 9.0
GAME_NEAR_CLIP = 0.5
APERTURE = 1.417  # inches, Maya's default 36 mm across


def focal_for(fov, aperture=APERTURE):
    """The focal length (mm) giving `fov` degrees across `aperture` inches."""
    return (aperture * 25.4 / 2.0) / math.tan(math.radians(fov) / 2.0)


FOCAL = focal_for(GAME_FOV)

CHANNELS = tuple(channel + axis
                 for channel in ("translate", "rotate") for axis in "XYZ")

NO_BONE = "no camera_root in the scene"
AMBIGUOUS_BONE = ("several camera_root candidates - select any control or "
                  "bone of the character you mean")


# ------------------------------------------------------------------ algebra

def leaf(path):
    """Strip DAG path and namespace: '|a|ns:camera_bone' -> 'camera_bone'."""
    return path.split("|")[-1].split(":")[-1]


def offset_matrix(euler_degrees):
    """A pure-rotation offset from XYZ euler degrees, as 16 floats."""
    radians = [math.radians(value) for value in euler_degrees]
    rotation = om.MEulerRotation(radians[0], radians[1], radians[2],
                                 om.MEulerRotation.kXYZ)
    return tuple(rotation.asMatrix())


def placed_matrix(bone_matrix, offset):
    """Where the camera stands: `offset · bone`."""
    return tuple(om.MMatrix(offset) * om.MMatrix(bone_matrix))


def bone_matrix_for(camera_matrix, offset):
    """Where the bone stands, given the camera: `offset⁻¹ · camera`."""
    return tuple(om.MMatrix(offset).inverse() * om.MMatrix(camera_matrix))


def offset_between(bone_matrix, camera_matrix):
    """The offset a placed camera implies: `camera · bone⁻¹`."""
    return tuple(om.MMatrix(camera_matrix)
                 * om.MMatrix(bone_matrix).inverse())


def rotation_only(matrix):
    """The same offset with its translation removed."""
    return tuple(matrix[:12]) + (0.0, 0.0, 0.0, 1.0)


def bone_candidates(paths, name=BONE):
    """Paths whose leaf name is exactly `name`.

    A leaf comparison rather than `ls("*camera_bone")`, which also matches
    `fake_camera_bone`, or `ls("*:camera_bone")`, which misses the plain one.
    """
    return [path for path in paths if leaf(path) == name]


def setup_message(camera_name, frames):
    return "{0} sits on {1} and drives it - {2} frames baked".format(
        camera_name, BONE, frames)


# -------------------------------------------------------------------- scene

def world_matrix(node):
    return tuple(cmds.xform(node, query=True, matrix=True, worldSpace=True))


def our_cameras():
    """Every camera this tool has made in the scene, found by its marker."""
    found = []
    for shape in cmds.ls(type="camera", long=True) or []:
        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        if parents and cmds.attributeQuery(MARKER, node=parents[0],
                                           exists=True):
            found.append(parents[0])
    return found


def existing_camera():
    """Some camera a previous press made, or None. For a scene with one rig;
    with several, `camera_for(bone)` is the question."""
    found = our_cameras()
    return found[0] if found else None


def camera_name_for(bone):
    """The camera's name, in the bone's own namespace. Pure.

    Two rigs mean two cameras (2026-09-08), and `Manny_Rig1:SceneSetup_camera`
    says whose it is where `SceneSetup_camera1` would not.
    """
    short = (bone or "").split("|")[-1]
    namespace = short.rsplit(":", 1)[0] if ":" in short else ""
    return namespace + ":" + CAMERA_NAME if namespace else CAMERA_NAME


def control_name_for(bone):
    """The camera control's name, in the bone's own namespace. Pure."""
    short = (bone or "").split("|")[-1]
    namespace = short.rsplit(":", 1)[0] if ":" in short else ""
    return namespace + ":" + CONTROL_NAME if namespace else CONTROL_NAME


def is_main(node):
    """Is `node` a rig's Main (its leaf)?"""
    return leaf(node) == "Main"


def _filter(node):
    curves = []
    for axis in "XYZ":
        curves += cmds.listConnections("%s.rotate%s" % (node, axis), source=True,
                                       destination=False, type="animCurve") or []
    if curves:
        cmds.filterCurve(curves, filter="euler")


def camera_for(bone):
    """The camera of ours driving THIS bone, or None -- never "any of ours"."""
    for node in our_constraints(bone):
        for target in cmds.parentConstraint(node, query=True,
                                            targetList=True) or []:
            paths = cmds.ls(target, long=True) or []
            if paths and cmds.attributeQuery(MARKER, node=paths[0],
                                             exists=True):
                return paths[0]
    return None


def resolve_bone(scene_map):
    """(bone path, problem message). The bound character first, then the scene.

    The camera bone often sits outside the character's own subtree, so a
    scene-wide fallback is required rather than optional -- but it is a
    fallback: with a character bound, its own bone is the answer and a second
    character cannot interfere.
    """
    if BONE in scene_map:
        return scene_map[BONE], ""
    candidates = bone_candidates(cmds.ls(long=True, transforms=True) or [])
    if not candidates:
        return None, NO_BONE
    if len(candidates) > 1:
        return None, AMBIGUOUS_BONE
    return candidates[0], ""


def our_constraints(bone):
    """parentConstraints on `bone` that our camera drives."""
    found = []
    children = cmds.listRelatives(bone, children=True, type="parentConstraint",
                                 fullPath=True) or []
    for node in children:
        for target in cmds.parentConstraint(node, query=True,
                                            targetList=True) or []:
            paths = cmds.ls(target, long=True) or []
            if paths and cmds.attributeQuery(MARKER, node=paths[0],
                                             exists=True):
                found.append(node)
                break
    return found


def _bake(node, start, end):
    maya_timewarp.call(cmds.bakeResults, node, time=(start, end), attribute=list(CHANNELS),
                     simulation=False, sampleBy=1,
                     disableImplicitControl=True, preserveOutsideKeys=False,
                     sparseAnimCurveBake=False)


def teardown(bone, start, end):
    """Undo a previous press without losing the animation.

    The bone's own curves were deleted when it was constrained, so the motion
    lives on the camera. Deleting that camera first would take the animation
    with it -- so the bone is baked back from it before anything goes.

    Only THIS bone's camera: with two rigs in the scene each has one, and
    tearing down "any camera of ours" would take the other rig's away.
    """
    camera_node = camera_for(bone)
    control = control_of(camera_node)
    constraints = our_constraints(bone)
    if not camera_node and not constraints:
        return False

    if constraints:
        _bake(bone, start, end)
        cmds.delete(constraints)
    if control:
        cmds.delete(control)            # its camera with it
    elif camera_node:
        cmds.delete(camera_node)
    return True


# ------------------------------------------------------------ the camera's control

def control_of(camera_node):
    """The control carrying `camera_node` (its parent, marked), or None - a camera made before
    2026-10-21 stands alone."""
    if not camera_node or not cmds.objExists(camera_node):
        return None
    parents = cmds.listRelatives(camera_node, parent=True, fullPath=True) or []
    if parents and cmds.attributeQuery(CONTROL_MARKER, node=parents[0], exists=True):
        return parents[0]
    return None


def control_for(bone):
    """The control of the camera of ours driving `bone`, or None."""
    return control_of(camera_for(bone))


def is_control(node):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery(
        CONTROL_MARKER, node=node, exists=True)


def keyed_node(bone):
    """What holds the camera's motion for `bone`: its control, else the camera itself (an older
    one), else None."""
    camera_node = camera_for(bone)
    return control_of(camera_node) or camera_node


def _rig_of(bone):
    try:
        import maya_rigs
        return maya_rigs.rig_of(bone, maya_rigs.rigs())
    except Exception:                                            # noqa: BLE001
        return None


def home_of(bone):
    """Where the camera's control lives by default: the bone's rig's Main, else its character
    group (None: world level). The animator: «всегда держать камеру в паренте главного
    контроллера для персонажа»."""
    rig = _rig_of(bone)
    main = getattr(rig, "main", None) if rig else None
    if main and cmds.objExists(main):
        return (cmds.ls(main, long=True) or [main])[0]
    from maya_scenesetup import chargroup
    return chargroup.group_of(bone)


def go_home(control):
    """The control back under its default parent (its rig's Main, else its character group, else
    world level), its motion kept - a knot it rode is going (1P Setup's chest baked off). Its
    long path."""
    rig = _rig_of(control)
    main = getattr(rig, "main", None) if rig else None
    if main and cmds.objExists(main):
        return move_control(control, (cmds.ls(main, long=True) or [main])[0], "Main")
    from maya_scenesetup import chargroup
    group = chargroup.group_of(control)
    return move_control(control, group if group != control else None, "World")


def parent_target(bone, choice):
    """(the node the control would stand under for `choice`, refusal). World: the character
    group (None: world level)."""
    rig = _rig_of(bone)
    if choice == "World":
        from maya_scenesetup import chargroup
        return chargroup.group_of(bone), ""
    if not rig:
        return None, "%s: no rig - the camera can follow the world only" % choice
    if choice == "Main":
        return (cmds.ls(rig.main, long=True) or [rig.main])[0], ""
    if choice == "Root":
        from maya_scenesetup import rootcontrol
        ctrl, words = rootcontrol.ensure(rig)
        return (ctrl, "") if ctrl else (None, "Root: " + words)
    if choice == "Chest":
        from maya_tools import firstperson
        chest = firstperson.chest_of(rig)
        return (chest, "") if chest else (None, "Chest: no 1P Setup on %s"
                                          % rig.namespace.split(":")[-1])
    return None, "no parent called %s" % choice


def parent_choice(control):
    """Which of PARENTS the control stands under (its marker), "" when unknown."""
    if not is_control(control) or not cmds.attributeQuery(PARENT_MARKER, node=control,
                                                          exists=True):
        return ""
    return cmds.getAttr(control + "." + PARENT_MARKER) or ""


def _mark_parent(control, choice):
    if not cmds.attributeQuery(PARENT_MARKER, node=control, exists=True):
        cmds.addAttr(control, longName=PARENT_MARKER, dataType="string")
    cmds.setAttr(control + "." + PARENT_MARKER, lock=False)
    cmds.setAttr(control + "." + PARENT_MARKER, choice, type="string")
    cmds.setAttr(control + "." + PARENT_MARKER, lock=True)


def move_control(control, parent, choice):
    """The control under `parent` (None: world level) with its motion kept: its world track
    baked back in its new space (Tools > Inside's road, `reparent._rebake`). Its long path."""
    from maya_tools import knots, reparent
    current = cmds.listRelatives(control, parent=True, fullPath=True)
    current = current[0] if current else None
    if current == parent:
        _mark_parent(control, choice)
        return control
    span = reparent._take([control], [parent])
    scales, refusal = reparent._scale_plans([(control, parent)], span)
    if refusal:            # a camera's scale is its own: left as it stands rather than refused
        scales = {knots._uuid(control): ("keep", 1.0, [], {})}
    parent_uuid = knots._uuid(parent) if parent else None

    def operate(uuids):
        for uuid in uuids:
            node = knots._by_uuid(uuid)
            if parent_uuid:
                cmds.parent(node, knots._by_uuid(parent_uuid))
            else:
                cmds.parent(node, world=True)

    control = reparent._rebake([control], span, operate, scales)[0]
    _mark_parent(control, choice)
    return control


def set_parent(bone, choice):
    """The camera's control for `bone` under the parent `choice` names, its motion kept. The
    line."""
    control = control_for(bone)
    if not control:
        return "no camera with a control on %s - press Camera Setup first" % leaf(bone)
    target, refusal = parent_target(bone, choice)
    if refusal:
        return refusal
    from maya_tools import knots
    with knots._press("skeldarCameraParent"):       # one undo step, autoKey off
        control = move_control(control, target, choice)
    return PARENT_LINE % (leaf(control), choice)


def _control_points(size):
    """The control's curve: a camera drawn in the control's space (the camera stands in it at
    the axis turn, so it is drawn through that turn)."""
    from maya_scenesetup import curvectrl
    return curvectrl.transformed(curvectrl.camera_body(size), rotation_only(AXIS_OFFSET))


def lens(shape):
    """The game's lens on a camera shape: a 16:9 gate fitted horizontally, so
    the viewport shows the game's 100 degrees across whatever its own shape."""
    cmds.setAttr(shape + ".horizontalFilmAperture", APERTURE)
    cmds.setAttr(shape + ".verticalFilmAperture", APERTURE / GAME_ASPECT)
    cmds.setAttr(shape + ".filmFit", 1)  # horizontal: UE's MaintainXFOV
    cmds.setAttr(shape + ".focalLength", FOCAL)
    cmds.setAttr(shape + ".nearClipPlane", GAME_NEAR_CLIP)


def setup(bone, start, end):
    """Bake the bone onto a fresh camera, then drive the bone from it."""
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)  # trap 14: the user works with autoKey on
    cmds.undoInfo(openChunk=True, chunkName="Camera setup")
    try:
        offset = rotation_only(AXIS_OFFSET)
        teardown(bone, start, end)

        # The camera's CONTROL (2026-10-21, the animator: «держать камеру в паренте главного
        # контроллера для персонажа, а управление камерой совершать через специальный
        # контроллер камеры который уже будет иметь возможность смены парентов»): under the
        # rig's Main (a bare skeleton: its character group), standing on the bone. The camera
        # is its child at the axis turn and is never keyed: the control carries the motion.
        from maya_scenesetup import curvectrl
        name = camera_name_for(bone)
        home = home_of(bone)
        if not home:
            from maya_scenesetup import chargroup
            home = chargroup.group_of(bone)
        control = curvectrl.make(scope.as_created(control_name_for(bone)), home,
                                 _control_points(CONTROL_SIZE), curvectrl.CYAN)
        control_uuid = cmds.ls(control, uuid=True)[0]
        cmds.addAttr(control, longName=CONTROL_MARKER, attributeType="bool", defaultValue=True)
        _mark_parent(control, "Main" if home and is_main(home) else "World")
        for attr in ("scaleX", "scaleY", "scaleZ", "visibility"):
            cmds.setAttr(control + "." + attr, keyable=False, channelBox=False)

        # Created then renamed: `cmds.camera(name=...)` leaves a numbered
        # transform, and the animator picks this camera out of a menu by name.
        transform, _shape = cmds.camera()
        transform = cmds.ls(cmds.rename(transform, scope.as_created(name)), long=True)[0]
        shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        shape = cmds.rename(shape, scope.as_created(name + "Shape"))
        lens(shape)
        cmds.addAttr(transform, longName=MARKER, attributeType="bool",
                     defaultValue=True)
        uuid = cmds.ls(transform, uuid=True)[0]
        cmds.parent(transform, cmds.ls(control_uuid, long=True)[0], relative=True)
        transform = cmds.ls(uuid, long=True)[0]
        control = cmds.ls(control_uuid, long=True)[0]
        cmds.xform(transform, matrix=offset, objectSpace=True)
        for attr in CHANNELS:
            cmds.setAttr(transform + "." + attr, lock=True)

        cmds.xform(control, matrix=world_matrix(bone), worldSpace=True)

        # Follow the bone and bake, then stand alone. The control is already in
        # the right place, so the offset maintainOffset captures is ours.
        temporary = cmds.parentConstraint(bone, control,
                                          maintainOffset=True)[0]
        _bake(control, start, end)
        cmds.delete(temporary)
        _filter(control)

        # Invert the drive. Order is load-bearing: constraining first and
        # cutting the curves after leaves a pairBlend nobody asked for, and
        # cutting without the snap lets maintainOffset capture the bone's REST
        # pose against the camera and bake a wrong offset in for ever.
        cmds.cutKey(bone, attribute=list(CHANNELS), clear=True)
        cmds.xform(bone, matrix=bone_matrix_for(world_matrix(transform),
                                                offset),
                   worldSpace=True)
        cmds.parentConstraint(transform, bone, maintainOffset=True)

        frames = int(round(end - start)) + 1
        return setup_message(leaf(transform), frames) + CONTROL_WORDS % (
            leaf(control), leaf(home) if home else "the world")
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=autokey)
