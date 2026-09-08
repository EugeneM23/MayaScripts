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

BONE = "camera_bone"
MARKER = "mayaSceneSetupCamera"
CAMERA_NAME = "SceneSetup_camera"

# The turn between camera1 and camera_bone, measured in the user's scene.
AXIS_OFFSET = (-1.0, 0.0, 0.0, 0.0,
               0.0, 0.0, 1.0, 0.0,
               0.0, 1.0, 0.0, 0.0,
               0.0, 0.0, 0.0, 1.0)

# camera1's lens, which was a framing choice rather than a Maya default.
FOCAL = 16.493949366848657

CHANNELS = tuple(channel + axis
                 for channel in ("translate", "rotate") for axis in "XYZ")

NO_BONE = "no camera_bone in the scene"
AMBIGUOUS_BONE = ("several camera_bone candidates - connect the picker to the "
                  "character you mean")


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
    cmds.bakeResults(node, time=(start, end), attribute=list(CHANNELS),
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
    constraints = our_constraints(bone)
    if not camera_node and not constraints:
        return False

    if constraints:
        _bake(bone, start, end)
        cmds.delete(constraints)
    if camera_node:
        cmds.delete(camera_node)
    return True


def setup(bone, start, end):
    """Bake the bone onto a fresh camera, then drive the bone from it."""
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)  # trap 14: the user works with autoKey on
    cmds.undoInfo(openChunk=True, chunkName="Camera setup")
    try:
        offset = rotation_only(AXIS_OFFSET)
        teardown(bone, start, end)

        # Created then renamed: `cmds.camera(name=...)` leaves a numbered
        # transform, and the animator picks this camera out of a menu by name.
        transform, _shape = cmds.camera()
        name = camera_name_for(bone)
        transform = cmds.ls(cmds.rename(transform, name), long=True)[0]
        shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        shape = cmds.rename(shape, name + "Shape")
        cmds.setAttr(shape + ".focalLength", FOCAL)
        cmds.addAttr(transform, longName=MARKER, attributeType="bool",
                     defaultValue=True)

        cmds.xform(transform, matrix=placed_matrix(world_matrix(bone), offset),
                   worldSpace=True)

        # Follow the bone and bake, then stand alone. The camera is already in
        # the right place, so the offset maintainOffset captures is ours.
        temporary = cmds.parentConstraint(bone, transform,
                                          maintainOffset=True)[0]
        _bake(transform, start, end)
        cmds.delete(temporary)

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
        return setup_message(leaf(transform), frames)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=autokey)
