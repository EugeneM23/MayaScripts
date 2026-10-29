"""The card grid's module-level helpers, the parts `test_poselib_cardgrid` leaves out: the last line of
an error and the Interface animations switch when the hub's menu cannot be asked. The Qt classes
are not covered here.
"""
import unittest

import maya_hubmotion

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


class Animations(unittest.TestCase):

    def setUp(self):
        saved = maya_hubmotion.enabled
        self.addCleanup(setattr, maya_hubmotion, "enabled", saved)

    def test_the_hub_menu_decides(self):
        maya_hubmotion.enabled = lambda: False
        self.assertIs(cardgrid._animations(), False)
        maya_hubmotion.enabled = lambda: True
        self.assertIs(cardgrid._animations(), True)

    def test_a_hub_that_cannot_be_asked_means_animations_on(self):
        def broken():
            raise RuntimeError("no hub")

        maya_hubmotion.enabled = broken
        self.assertIs(cardgrid._animations(), True)


if __name__ == "__main__":
    unittest.main()
