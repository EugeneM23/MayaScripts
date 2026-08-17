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


class TheMeasuredDefault(unittest.TestCase):
    """Measured in the user's scene on 2026-08-17 from camera1 vs camera_bone.

    The camera stands AT the bone, turned by a constant; a Maya camera looks
    down its own -Z and the UE camera bone does not, so this offset is the
    whole reason the button can exist.
    """

    def test_is_a_pure_rotation(self):
        offset = camera.DEFAULT_OFFSET
        self.assertAlmostEqual(offset[12], 0.0)
        self.assertAlmostEqual(offset[13], 0.0)
        self.assertAlmostEqual(offset[14], 0.0)

    def test_matches_the_measured_matrix(self):
        expected = (-1.0, 0.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 0.0, 1.0)
        self.assertLess(worst(camera.DEFAULT_OFFSET, expected), 1e-9)

    def test_is_what_the_euler_produces(self):
        """(90, 0, 180) in XYZ is how the same offset reads in the channel box."""
        self.assertLess(
            worst(camera.offset_matrix((90.0, 0.0, 180.0)),
                  camera.DEFAULT_OFFSET), 1e-9)

    def test_the_focal_length_is_the_framing_the_animator_chose(self):
        self.assertAlmostEqual(camera.DEFAULT_FOCAL, 16.493949366848657)


class Placing(unittest.TestCase):

    def test_an_identity_offset_puts_the_camera_on_the_bone(self):
        self.assertLess(worst(camera.placed_matrix(BONE, IDENTITY), BONE), 1e-9)

    def test_the_camera_lands_at_the_bone_position(self):
        """The measured offset is a pure rotation, so only the axes change."""
        placed = camera.placed_matrix(BONE, camera.DEFAULT_OFFSET)
        self.assertLess(worst(placed[12:], BONE[12:]), 1e-9)

    def test_the_camera_does_not_land_on_the_bone_axes(self):
        placed = camera.placed_matrix(BONE, camera.DEFAULT_OFFSET)
        self.assertGreater(worst(placed[:12], BONE[:12]), 0.5)

    def test_the_bone_is_recovered_from_the_camera(self):
        """The round trip is what the constraint reproduces every frame."""
        placed = camera.placed_matrix(BONE, camera.DEFAULT_OFFSET)
        back = camera.bone_matrix_for(placed, camera.DEFAULT_OFFSET)
        self.assertLess(worst(back, BONE), 1e-9)

    def test_the_round_trip_holds_for_an_arbitrary_offset(self):
        offset = camera.offset_matrix((13.0, -47.0, 91.0))
        placed = camera.placed_matrix(BONE, offset)
        self.assertLess(worst(camera.bone_matrix_for(placed, offset), BONE),
                        1e-9)

    def test_the_offset_between_two_matrices_is_recoverable(self):
        """This is how a reference camera in the scene is read."""
        placed = camera.placed_matrix(BONE, camera.DEFAULT_OFFSET)
        self.assertLess(
            worst(camera.offset_between(BONE, placed), camera.DEFAULT_OFFSET),
            1e-9)


class DefaultCameras(unittest.TestCase):

    def test_mayas_own_cameras_are_recognised(self):
        for name in ("persp", "top", "front", "side"):
            self.assertTrue(camera.is_default_camera("|" + name), name)

    def test_a_named_camera_is_not(self):
        self.assertFalse(camera.is_default_camera("|camera1"))

    def test_a_namespaced_persp_still_counts(self):
        """An imported reference brings its own persp along."""
        self.assertTrue(camera.is_default_camera("|ref:persp"))

    def test_a_camera_merely_containing_persp_is_not_default(self):
        self.assertFalse(camera.is_default_camera("|perspective_hero"))


class PickReference(unittest.TestCase):
    """Which camera in the scene defines the offset.

    The user places the camera as it should stand by default, so a camera they
    placed beats anything baked into the code -- but never Maya's own, and
    never the one this tool made, which would make the choice circular.
    """

    def test_takes_the_animator_camera(self):
        self.assertEqual(
            camera.pick_reference(["|persp", "|camera1", "|top"]), "|camera1")

    def test_is_none_when_only_defaults_are_there(self):
        self.assertIsNone(camera.pick_reference(["|persp", "|side"]))

    def test_is_none_for_an_empty_scene(self):
        self.assertIsNone(camera.pick_reference([]))

    def test_sorted_first_wins_so_two_runs_agree(self):
        self.assertEqual(
            camera.pick_reference(["|shotCam", "|aCam"]), "|aCam")


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

    def test_says_where_the_offset_came_from(self):
        message = camera.setup_message("SceneSetup_camera", "|camera1", 60)
        self.assertIn("camera1", message)
        self.assertIn("60", message)

    def test_names_the_built_in_default_when_there_is_no_reference(self):
        message = camera.setup_message("SceneSetup_camera", None, 60)
        self.assertIn("default", message.lower())

    def test_missing_bone_names_the_bone(self):
        self.assertIn("camera_bone", camera.NO_BONE)

    def test_ambiguous_asks_for_the_picker(self):
        self.assertIn("picker", camera.AMBIGUOUS_BONE.lower())
