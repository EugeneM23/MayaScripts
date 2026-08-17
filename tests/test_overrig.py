import contextlib
import unittest

from maya_overrig import overrig


@contextlib.contextmanager
def _fake_mel(answer):
    """Stand in for `mel.eval` while the test runs.

    `maya.mel` imports fine under mayapy but grows its `eval` only once a
    Maya session is initialised, so the attribute is often ABSENT rather than
    real -- saving and restoring it needs the absent case, or every test that
    patches mel raises AttributeError before it starts.
    """
    missing = object()
    original = getattr(overrig.mel, "eval", missing)
    overrig.mel.eval = answer
    try:
        yield
    finally:
        if original is missing:
            del overrig.mel.eval
        else:
            overrig.mel.eval = original


class TestHalfFrameTimes(unittest.TestCase):
    """The doubled-time capture leaves its interpolation artifacts on
    half-frame keys; these are the times the cleanup removes."""

    def test_picks_the_halves(self):
        self.assertEqual(overrig.half_frame_times([0.0, 0.5, 1.0, 1.5, 2.0]),
                         [0.5, 1.5])

    def test_integer_times_survive(self):
        self.assertEqual(overrig.half_frame_times([-1.0, 0.0, 38.0]), [])

    def test_negative_halves_are_caught(self):
        self.assertEqual(overrig.half_frame_times([-0.5, 0.0]), [-0.5])

    def test_float_noise_does_not_kill_an_integer(self):
        self.assertEqual(overrig.half_frame_times([1.0000000001]), [])

    def test_empty(self):
        self.assertEqual(overrig.half_frame_times([]), [])

    def test_none_reads_as_empty(self):
        """cmds.keyframe returns None for a curve with no keys."""
        self.assertEqual(overrig.half_frame_times(None), [])


class TestCaptureChannel(unittest.TestCase):
    """Only transform channels get their half-frame keys cut. OverRig's
    `attach` weight keys its fade half a frame outside the range after the
    rescale, and cutting those would turn the constraint weight into a ramp
    across the whole clip."""

    def test_rotates(self):
        for attr in ("rotateX", "rotateY", "rotateZ"):
            self.assertTrue(overrig.capture_channel(attr), attr)

    def test_translates_and_scales(self):
        for attr in ("translateX", "translateZ", "scaleY"):
            self.assertTrue(overrig.capture_channel(attr), attr)

    def test_pair_blend_inputs(self):
        for attr in ("inRotateX1", "inTranslateY2"):
            self.assertTrue(overrig.capture_channel(attr), attr)

    def test_attach_is_left_alone(self):
        self.assertFalse(overrig.capture_channel("attach"))

    def test_visibility_is_left_alone(self):
        self.assertFalse(overrig.capture_channel("visibility"))

    def test_empty(self):
        self.assertFalse(overrig.capture_channel(""))


class TestSliderMessage(unittest.TestCase):

    def test_names_the_range(self):
        message = overrig.slider_message((10.0, 25.0))
        self.assertIn("10", message)
        self.assertIn("25", message)
        self.assertIn("time slider", message)


class TestAimProcs(unittest.TestCase):
    """The aim path leans on four internal, hash-named procs.

    They are global procs and stable inside v10.2, but an OverRig update can
    rename them -- and a renamed proc must reach the status line by name, not
    a traceback out of a Qt slot (trap 20).
    """

    def test_all_six_procs_are_named(self):
        self.assertEqual(len(overrig.AIM_PROCS), 6)
        self.assertIn("make_aim_from_selected", overrig.AIM_PROCS)

    def test_create_comes_before_build(self):
        """The build proc reads MEL globals the create proc sets."""
        self.assertLess(overrig.AIM_PROCS.index(overrig.AIM_CREATE_PROC),
                        overrig.AIM_PROCS.index(overrig.AIM_BUILD_PROC))

    def test_missing_procs_are_reported_by_name(self):
        with _fake_mel(lambda c: 0 if overrig.AIM_BUILD_PROC in c else 1):
            missing = overrig.missing_aim_procs()
        self.assertEqual(missing, [overrig.AIM_BUILD_PROC])
        self.assertIn(overrig.AIM_BUILD_PROC,
                      overrig.AIM_PROCS_MESSAGE.format(", ".join(missing)))

    def test_nothing_missing_when_they_all_exist(self):
        with _fake_mel(lambda c: 1):
            self.assertEqual(overrig.missing_aim_procs(), [])


if __name__ == "__main__":
    unittest.main()
