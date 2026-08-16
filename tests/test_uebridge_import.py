"""Tests for the Maya-side import.

`import_clip` needs a live Maya and a real FBX, so it is proved by
docs/superpowers/plans/verify_uebridge.py. What is testable here is the policy
around it: the frame-rate rule and the key-range arithmetic.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let animimport import without Maya. See CLAUDE.md on rebinding."""
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import animimport  # noqa: E402


class FpsPolicy(unittest.TestCase):

    def test_silent_when_they_agree(self):
        self.assertEqual(animimport.fps_warning(30.0, 30.0), "")

    def test_tolerates_float_noise(self):
        """29.999999 against 30 is not worth shouting about."""
        self.assertEqual(animimport.fps_warning(30.0, 30.000001), "")

    def test_names_both_rates_when_they_differ(self):
        message = animimport.fps_warning(30.0, 24.0)
        self.assertIn("30", message)
        self.assertIn("24", message)

    def test_says_nothing_when_the_clip_rate_is_unknown(self):
        """UE does not always report a rate; silence beats a false alarm."""
        self.assertEqual(animimport.fps_warning(None, 24.0), "")

    def test_says_nothing_when_the_scene_rate_is_unknown(self):
        self.assertEqual(animimport.fps_warning(30.0, None), "")


class SceneFps(unittest.TestCase):

    def test_knows_the_units_maya_reports(self):
        self.assertEqual(animimport.TIME_UNIT_TO_FPS["ntsc"], 30)
        self.assertEqual(animimport.TIME_UNIT_TO_FPS["film"], 24)
        self.assertEqual(animimport.TIME_UNIT_TO_FPS["pal"], 25)

    def test_reads_a_numeric_unit_name(self):
        """Maya reports custom rates as e.g. '30fps', absent from the table."""
        self.assertEqual(animimport.fps_from_unit("30fps"), 30.0)
        self.assertEqual(animimport.fps_from_unit("120fps"), 120.0)

    def test_an_unknown_unit_is_none_rather_than_a_guess(self):
        self.assertIsNone(animimport.fps_from_unit("whatever"))


class ClipRange(unittest.TestCase):

    def test_takes_the_outermost_keys(self):
        self.assertEqual(animimport.clip_range([5.0, 1.0, 3.0]), (1.0, 5.0))

    def test_no_keys_is_no_range(self):
        self.assertEqual(animimport.clip_range([]), (None, None))

    def test_a_single_key_is_a_zero_length_range(self):
        self.assertEqual(animimport.clip_range([7.0]), (7.0, 7.0))


if __name__ == "__main__":
    unittest.main()
