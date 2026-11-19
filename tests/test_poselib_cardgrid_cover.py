"""The card grid's module-level helpers, the parts `test_poselib_cardgrid` leaves out: the last line of
an error. The Qt classes are not covered here.
"""
import unittest

from maya_poselib import cardgrid


class LastLine(unittest.TestCase):

    def test_a_traceback_is_reduced_to_its_last_line(self):
        text = "Traceback (most recent call last):\n  File \"x.py\", line 1\nRuntimeError: no sheet\n"
        self.assertEqual(cardgrid._last_line(text), "RuntimeError: no sheet")

    def test_blank_lines_around_the_text_do_not_count(self):
        self.assertEqual(cardgrid._last_line("\n\nfirst\n  \nsecond  \n\n  \n"), "second")

    def test_nothing_to_say_is_failed(self):
        for text in (None, "", "   \n \n"):
            self.assertEqual(cardgrid._last_line(text), "failed", repr(text))


class NoMotion(unittest.TestCase):

    def test_the_grid_asks_no_animations_switch(self):
        """2026-11-19: nothing in the grid moves, so it never asks maya_hubmotion."""
        with open(cardgrid.__file__, encoding="utf-8") as handle:
            self.assertNotIn("maya_hubmotion", handle.read())


if __name__ == "__main__":
    unittest.main()
