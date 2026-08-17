"""Put a camera on the camera bone, then let the camera drive the bone.

The animator wants to animate a camera, not a joint; the export wants the
joint. So the bone's motion is baked onto a real Maya camera and the bone is
then parent-constrained to it. After the press, the camera is the thing you
animate and the bone follows it exactly.

**The axis offset is measured, never derived.** A Maya camera looks down its
own -Z and a UE camera bone does not, and no amount of reasoning about
conventions beats reading the scene the animator has already set up. Measured
2026-08-17 from `camera1` against `camera_bone`: the camera stands AT the bone,
turned by a constant that reads (90, 0, 180) XYZ in the channel box. At run
time a camera the animator has placed wins over that constant -- they said they
would place it as it should stand -- and the status line names which was used.

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

# camera1 in camera_bone's space, measured in the user's scene.
DEFAULT_OFFSET = (-1.0, 0.0, 0.0, 0.0,
                  0.0, 0.0, 1.0, 0.0,
                  0.0, 1.0, 0.0, 0.0,
                  0.0, 0.0, 0.0, 1.0)
DEFAULT_FOCAL = 16.493949366848657

CHANNELS = tuple(channel + axis
                 for channel in ("translate", "rotate") for axis in "XYZ")

_DEFAULT_CAMERAS = ("persp", "top", "front", "side",
                    "back", "bottom", "left", "right")

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


def is_default_camera(path):
    """One of Maya's own cameras, namespace and all."""
    return leaf(path) in _DEFAULT_CAMERAS


def pick_reference(camera_paths):
    """Which camera defines the offset, or None.

    Sorted first, so two runs of the same scene agree; Maya's own cameras never
    count. Our own camera is filtered out before this, which would otherwise
    make the choice circular -- it was built FROM the offset.
    """
    named = sorted(path for path in camera_paths
                   if not is_default_camera(path))
    return named[0] if named else None


def bone_candidates(paths, name=BONE):
    """Paths whose leaf name is exactly `name`.

    A leaf comparison rather than `ls("*camera_bone")`, which also matches
    `fake_camera_bone`, or `ls("*:camera_bone")`, which misses the plain one.
    """
    return [path for path in paths if leaf(path) == name]


def setup_message(camera_name, reference, frames):
    origin = ("offset from " + leaf(reference) if reference
              else "built-in default offset")
    return "{0} drives {1} - {2} frames baked, {3}".format(
        camera_name, BONE, frames, origin)


# -------------------------------------------------------------------- scene

def world_matrix(node):
    return tuple(cmds.xform(node, query=True, matrix=True, worldSpace=True))


def _camera_transforms(ours=False):
    """Transforms of the scene's cameras; ours or everyone else's."""
    found = []
    for shape in cmds.ls(type="camera", long=True) or []:
        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        if not parents:
            continue
        marked = cmds.attributeQuery(MARKER, node=parents[0], exists=True)
        if bool(marked) == bool(ours):
            found.append(parents[0])
    return found


def our_cameras():
    """Every camera this tool has made in the scene."""
    return _camera_transforms(ours=True)


def existing_camera():
    """The camera a previous press made, or None."""
    found = our_cameras()
    return found[0] if found else None


def reference_offset(bone):
    """(offset, reference path). The scene's own camera wins over the default."""
    reference = pick_reference(_camera_transforms(ours=False))
    if not reference:
        return DEFAULT_OFFSET, None
    return offset_between(world_matrix(bone), world_matrix(reference)), reference


def reference_focal(reference):
    if not reference:
        return DEFAULT_FOCAL
    shapes = cmds.listRelatives(reference, shapes=True, fullPath=True) or []
    for shape in shapes:
        if cmds.objectType(shape) == "camera":
            return cmds.getAttr(shape + ".focalLength")
    return DEFAULT_FOCAL


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
    """
    camera_node = existing_camera()
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
        offset, reference = reference_offset(bone)
        focal = reference_focal(reference)
        teardown(bone, start, end)

        # Created then renamed: `cmds.camera(name=...)` leaves a numbered
        # transform, and the animator picks this camera out of a menu by name.
        transform, _shape = cmds.camera()
        transform = cmds.ls(cmds.rename(transform, CAMERA_NAME), long=True)[0]
        shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        shape = cmds.rename(shape, CAMERA_NAME + "Shape")
        cmds.setAttr(shape + ".focalLength", focal)
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
        return setup_message(leaf(transform), reference, frames)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=autokey)
