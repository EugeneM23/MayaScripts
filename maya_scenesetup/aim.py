"""OverRig's aim on the attached weapon, with the locators placed for you.

The two locators are placed from the model's OWN measured extents rather than
from any axis convention: the longest local axis is the blade, and its further
end is the tip. On the user's LongSword that reads Y=+115.925 with the
crossguard on X and the blade's thickness on Z -- and a model authored down -Y
works with no special case, because the further end is taken signed.

That is correct even though OverRig hardcodes `aimVector 1 0 0`. The constraint
is built with `-mo`, so the direction that tracks the target afterwards is
whichever direction pointed at it when the offset was measured -- the blade, not
the local +X. Placing by geometry is what makes the aim intuitive, not a
workaround for it. Placing along local +X would aim a direction 90 degrees off
the blade on this model.

The aim goes on the GEOMETRY. Since Add stopped building a group that is
usually the marked node itself, and the two only differ for a file that kept a
group; either way what the animator grabs in the viewport is the geometry (trap
34) and the IK hands ride it once Connect has hung them there. An honest side
effect stays: once the aim exists the constraint fixes the geometry's world
orientation, so the Rotate field has no visible effect -- `setAttr` into a
constrained channel raises, and Translate still works.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from maya_overrig import aimrig, overrig

from maya_scenesetup import attach

MARGIN = 0.15
LOCATOR_SIZE = 1.0

NO_GEOMETRY_MESSAGE = "no geometry to measure - cannot place the aim"
ALREADY_MESSAGE = ("aim is already on this weapon - Bake+Delete in the picker "
                   "removes it")
ROTATE_INERT_NOTE = "Rotate is now driven by the aim"


# ---------------------------------------------------------------------------
# policy
# ---------------------------------------------------------------------------

def placement(lo, hi, margin=MARGIN):
    """Local offsets for the two locators, or None if there is nothing to aim.

    `lo`/`hi` are the model's extents in its own frame. Returns
    (top_offset, side_offset) as triples: `top` along the blade past the tip,
    `side` on the next longest axis at the same distance.
    """
    extents = [hi[axis] - lo[axis] for axis in range(3)]
    # Ties break by axis order, so a symmetric model never depends on sort
    # stability -- and a blade IS symmetric across its width, so ties are the
    # normal case rather than a curiosity.
    order = sorted(range(3), key=lambda axis: (-extents[axis], axis))
    blade, side = order[0], order[1]
    if extents[blade] <= 0.0:
        return None

    def further(axis):
        """The end of the box further from the origin, signed.

        The origin sits in the grip, because the weapon seats the model on the
        bone -- so the further end is the tip.
        """
        return hi[axis] if abs(hi[axis]) >= abs(lo[axis]) else lo[axis]

    distance = further(blade) * (1.0 + margin)
    side_sign = 1.0 if further(side) >= 0.0 else -1.0

    top_offset = [0.0, 0.0, 0.0]
    top_offset[blade] = distance
    side_offset = [0.0, 0.0, 0.0]
    side_offset[side] = abs(distance) * side_sign
    return tuple(top_offset), tuple(side_offset)


def added_message(label, top, note=ROTATE_INERT_NOTE):
    """What the status line says after a successful press."""
    return "Aim on {0} - drag {1} to point the blade ({2})".format(
        label, top.split("|")[-1], note)


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

def local_extents(model):
    """The model's mesh extents in its own local frame, or None.

    Mesh points rather than a bounding-box query: the model may hold several
    meshes under nested transforms, and what is wanted is the box in the
    MODEL's frame, which no world-space AABB gives.
    """
    meshes = cmds.listRelatives(model, allDescendents=True, type="mesh",
                                fullPath=True) or []
    if not meshes:
        return None

    selection = om.MSelectionList()
    selection.add(model)
    inverse = selection.getDagPath(0).inclusiveMatrix().inverse()

    lo = [None, None, None]
    hi = [None, None, None]
    for shape in meshes:
        one = om.MSelectionList()
        one.add(shape)
        points = om.MFnMesh(one.getDagPath(0)).getPoints(om.MSpace.kWorld)
        for point in points:
            local = point * inverse
            for axis in range(3):
                if lo[axis] is None or local[axis] < lo[axis]:
                    lo[axis] = local[axis]
                if hi[axis] is None or local[axis] > hi[axis]:
                    hi[axis] = local[axis]

    if lo[0] is None:
        return None
    return tuple(lo), tuple(hi)


def _place(locator, model, offset):
    """Put a locator at a point given in the model's local frame."""
    matrix = om.MMatrix(cmds.xform(model, query=True, worldSpace=True,
                                   matrix=True))
    world = om.MPoint(offset[0], offset[1], offset[2]) * matrix
    cmds.xform(locator, worldSpace=True,
               translation=(world[0], world[1], world[2]))


def _scene_nodes():
    """The UUID snapshot the manifest diff runs on.

    builder is imported here rather than at module scope so that importing this
    module does not drag the whole rig builder in behind it.
    """
    from maya_overrig import builder
    return builder._scene_nodes()


def add_aim(entry, weapon):
    """Put OverRig's aim on the attached `weapon`. Returns a message.

    Not gated on the time slider highlight, and that is measured rather than
    assumed: this path's bake reads `playbackOptions -ast/-aet` and never
    `timeControl -q -ra`, so trap 36 does not reach it. The aim BAKE is gated,
    because `apply_Fast_Bake` is one of the nineteen that do read it.
    """
    if not overrig.ensure_loaded():
        return overrig.NOT_LOADED_MESSAGE
    absent = overrig.missing_aim_procs()
    if absent:
        return overrig.AIM_PROCS_MESSAGE.format(", ".join(absent))

    model = attach.model_root(weapon)
    if aimrig.aim_for(model) or aimrig.aim_for(weapon):
        return ALREADY_MESSAGE

    extents = local_extents(model)
    if extents is None:
        return NO_GEOMETRY_MESSAGE
    offsets = placement(*extents)
    if offsets is None:
        return NO_GEOMETRY_MESSAGE
    top_offset, side_offset = offsets

    # The user works with autoKey ON, and a scripted poke at a keyed channel
    # writes real keys (trap 14). The locators are fresh and unkeyed, but the
    # cost of being wrong about that is keys in the animator's curves.
    state = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    cmds.undoInfo(openChunk=True, chunkName="Add weapon aim")
    try:
        before = _scene_nodes()

        # The same calls the native button makes, in the same order -- but the
        # build runs here instead of in a deferred scriptJob, so placement and
        # the build share one undo chunk and one node diff.
        overrig.add_to_set([model], "OverRig_rig_objects")
        top, side = overrig.make_aim_locators(model)
        overrig.aim_outliner_colour()
        overrig.aim_locator_size([top, side], LOCATOR_SIZE)

        _place(top, model, top_offset)
        _place(side, model, side_offset)

        overrig.add_to_set([top], overrig.KNOT_SET)
        overrig.add_to_set([side], overrig.KNOT_SET)
        overrig.build_aim()

        # Handles, never members: selecting one must resolve to this aim, and
        # a bake must not delete it. Deduplicated, because with no group the
        # model and the marked weapon are one node and the same UUID twice is
        # bookkeeping nobody can read.
        handles = [model] if model == weapon else [model, weapon]
        aimrig.record(entry.key, model, handles, before)
        return added_message(entry.label, top)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=state)
