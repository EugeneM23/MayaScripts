"""Tests for the camera setup: the offset algebra and who the reference is.

The setup itself drives a live scene and is proved by
docs/superpowers/plans/verify_camera_setup.py. What is testable here is the
matrix arithmetic -- which is where a wrong axis convention would hide -- and
the choices made before anything is touched.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Real Maya modules win; the fakes are for an interpreter without them."""
    try:
        import maya.api.OpenMaya  # noqa: F401
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass

    maya = types.ModuleType("maya")
    api = types.ModuleType("maya.api")
    openmaya = types.ModuleType("maya.api.OpenMaya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    maya.api = api
    api.OpenMaya = openmaya
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.api"] = api
    sys.modules["maya.api.OpenMaya"] = openmaya
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import camera  # noqa: E402

IDENTITY = (1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0)

# A bone standing somewhere unhelpful, so a forgotten multiplication shows up.
BONE = (0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        1.0, 0.0, 0.0, 0.0,
        10.0, 164.0, -5.0, 1.0)


def worst(left, right):
    return max(abs(a - b) for a, b in zip(left, right))


class TheAxisOffset(unittest.TestCase):
    """Measured in the user's scene on 2026-08-17 from camera1 vs camera_bone.

    A Maya camera looks down its own -Z and the UE camera bone does not, so
    this turn is the whole reason the button can exist. It is a rotation and
    nothing else: the camera lands ON the bone's transform, by the user's call
    -- "the reference camera does not matter, only the rotation axes do".
    """

    def test_is_a_pure_rotation(self):
        offset = camera.AXIS_OFFSET
        self.assertAlmostEqual(offset[12], 0.0)
        self.assertAlmostEqual(offset[13], 0.0)
        self.assertAlmostEqual(offset[14], 0.0)

    def test_matches_the_measured_matrix(self):
        expected = (-1.0, 0.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 0.0, 1.0)
        self.assertLess(worst(camera.AXIS_OFFSET, expected), 1e-9)

    def test_is_what_the_euler_produces(self):
        """(90, 0, 180) in XYZ is how the same offset reads in the channel box."""
        self.assertLess(
            worst(camera.offset_matrix((90.0, 0.0, 180.0)),
                  camera.AXIS_OFFSET), 1e-9)

    def test_the_focal_length_is_the_framing_the_animator_chose(self):
        self.assertAlmostEqual(camera.FOCAL, 16.493949366848657)


class RotationOnly(unittest.TestCase):
    """Whatever the offset carries, only its rotation may reach the camera.

    The camera has to land in the bone's transform. An offset with translation
    in it -- measured from a camera standing somewhere else, or edited by hand
    -- would park the camera away from the bone, which is the one thing the
    user ruled out.
    """

    def test_strips_the_translation(self):
        carried = (1.0, 0.0, 0.0, 0.0,
                   0.0, 1.0, 0.0, 0.0,
                   0.0, 0.0, 1.0, 0.0,
                   7.0, -3.0, 11.0, 1.0)
        self.assertEqual(camera.rotation_only(carried)[12:], (0.0, 0.0, 0.0, 1.0))

    def test_keeps_the_rotation(self):
        self.assertLess(
            worst(camera.rotation_only(camera.AXIS_OFFSET)[:12],
                  camera.AXIS_OFFSET[:12]), 1e-12)

    def test_leaves_a_pure_rotation_alone(self):
        self.assertLess(worst(camera.rotation_only(camera.AXIS_OFFSET),
                              camera.AXIS_OFFSET), 1e-12)


class Placing(unittest.TestCase):

    def test_an_identity_offset_puts_the_camera_on_the_bone(self):
        self.assertLess(worst(camera.placed_matrix(BONE, IDENTITY), BONE), 1e-9)

    def test_the_camera_lands_in_the_bones_transform(self):
        """The whole point: the camera jumps onto the bone, axes aside."""
        placed = camera.placed_matrix(BONE, camera.AXIS_OFFSET)
        self.assertLess(worst(placed[12:], BONE[12:]), 1e-9)

    def test_the_camera_does_not_land_on_the_bone_axes(self):
        placed = camera.placed_matrix(BONE, camera.AXIS_OFFSET)
        self.assertGreater(worst(placed[:12], BONE[:12]), 0.5)

    def test_the_bone_is_recovered_from_the_camera(self):
        """The round trip is what the constraint reproduces every frame."""
        placed = camera.placed_matrix(BONE, camera.AXIS_OFFSET)
        back = camera.bone_matrix_for(placed, camera.AXIS_OFFSET)
        self.assertLess(worst(back, BONE), 1e-9)

    def test_the_round_trip_holds_for_an_arbitrary_offset(self):
        offset = camera.offset_matrix((13.0, -47.0, 91.0))
        placed = camera.placed_matrix(BONE, offset)
        self.assertLess(worst(camera.bone_matrix_for(placed, offset), BONE),
                        1e-9)

    def test_the_offset_between_two_matrices_is_recoverable(self):
        """How the live check reads back what the setup actually built."""
        placed = camera.placed_matrix(BONE, camera.AXIS_OFFSET)
        self.assertLess(
            worst(camera.offset_between(BONE, placed), camera.AXIS_OFFSET),
            1e-9)


class BoneCandidates(unittest.TestCase):

    def test_matches_the_leaf_name_through_a_namespace(self):
        self.assertEqual(
            camera.bone_candidates(["|rig:root|rig:camera_bone", "|root|pelvis"],
                                   "camera_bone"),
            ["|rig:root|rig:camera_bone"])

    def test_rejects_a_name_that_merely_ends_with_it(self):
        """`ls("*camera_bone")` would take this one; the leaf comparison does not."""
        self.assertEqual(
            camera.bone_candidates(["|fake_camera_bone"], "camera_bone"), [])

    def test_finds_every_candidate(self):
        found = camera.bone_candidates(
            ["|a|camera_bone", "|b:camera_bone"], "camera_bone")
        self.assertEqual(len(found), 2)


class Messages(unittest.TestCase):

    def test_names_the_camera_the_bone_and_the_frames(self):
        message = camera.setup_message("SceneSetup_camera", 60)
        self.assertIn("SceneSetup_camera", message)
        self.assertIn("camera_bone", message)
        self.assertIn("60", message)

    def test_missing_bone_names_the_bone(self):
        self.assertIn("camera_bone", camera.NO_BONE)

    def test_ambiguous_asks_for_the_picker(self):
        self.assertIn("picker", camera.AMBIGUOUS_BONE.lower())
