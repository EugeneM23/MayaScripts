import unittest

from maya_overrig import overrig


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


if __name__ == "__main__":
    unittest.main()
