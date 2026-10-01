"""maya_hubmotion: how the hub's cards move - the numbers and the switch.

Spec: docs/superpowers/specs/2026-10-01-hub-card-motion-design.md
"""

import os
import subprocess
import sys
import unittest

import maya_hubmotion as motion

_PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


class FakeCmds(object):

    def __init__(self):
        self.vars = {}

    def optionVar(self, exists=None, query=None, intValue=None):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars[query]
        if intValue is not None:
            self.vars[intValue[0]] = intValue[1]
        return None


class Ease(unittest.TestCase):

    def test_the_ends_and_the_middle(self):
        self.assertEqual(motion.ease(0.0), 0.0)
        self.assertEqual(motion.ease(1.0), 1.0)
        self.assertAlmostEqual(motion.ease(0.5), 0.875)

    def test_clamped_outside_the_slide(self):
        self.assertEqual(motion.ease(-0.5), 0.0)
        self.assertEqual(motion.ease(1.5), 1.0)

    def test_monotonic_and_fast_first(self):
        values = [motion.ease(i / 20.0) for i in range(21)]
        self.assertEqual(values, sorted(values))
        #  ease-out: the first half covers most of the way
        self.assertGreater(motion.ease(0.5), 0.5)

    def test_lerp(self):
        self.assertEqual(motion.lerp(10, 20, 0.25), 12.5)
        self.assertEqual(motion.lerp(20, 10, 1.0), 10)


class Duration(unittest.TestCase):

    def test_opening_is_half_as_slow_again(self):
        """2026-10-01, the animator: «замедлим анимацию открытия вкладки
        примерно на 50%» - an opening takes 1.5 times a shutting."""
        self.assertEqual(motion.OPEN_FACTOR, 1.5)
        self.assertEqual(motion.duration(420, 1.5, opening=True), 260)
        self.assertEqual(motion.duration(810, 1.5, opening=True), 307)
        self.assertEqual(motion.duration(0, opening=True), 240)
        self.assertEqual(motion.duration(10000, opening=True), 390)
        self.assertEqual(motion.duration(420, 1.5), 174)     # shutting as was

    def test_by_the_logical_distance(self):
        #  measured 2026-10-01 at 150 %: Characters 420 physical, UE Bridge 810
        self.assertEqual(motion.duration(420, 1.5), 174)
        self.assertEqual(motion.duration(810, 1.5), 205)

    def test_never_shorter_or_longer_than_the_bounds(self):
        self.assertEqual(motion.duration(0), motion.MIN_MS)
        self.assertEqual(motion.duration(150 * 1.5, 1.5), 160)
        self.assertEqual(motion.duration(10000), motion.MAX_MS)

    def test_the_direction_does_not_matter(self):
        self.assertEqual(motion.duration(-420, 1.5), 174)

    def test_the_glide_is_as_long_as_a_slide(self):
        """It starts once the other cards have finished sliding, so a jump
        is a fold then a glide: neither may drag."""
        self.assertEqual(motion.SCROLL_MS, 240)
        self.assertLessEqual(motion.SCROLL_MS, motion.MAX_MS)


class Switch(unittest.TestCase):

    def setUp(self):
        self.saved = motion._cmds
        self.cmds = FakeCmds()
        motion._cmds = lambda: self.cmds

    def tearDown(self):
        motion._cmds = self.saved

    def test_on_by_default(self):
        self.assertTrue(motion.enabled())

    def test_set_enabled_remembers(self):
        self.assertFalse(motion.set_enabled(False))
        self.assertEqual(self.cmds.vars[motion.OPTIONVAR], 0)
        self.assertFalse(motion.enabled())
        self.assertTrue(motion.set_enabled(True))
        self.assertTrue(motion.enabled())

    def test_without_maya_it_is_on(self):
        def broken():
            raise ImportError("no maya")
        motion._cmds = broken
        self.assertTrue(motion.enabled())
        self.assertFalse(motion.set_enabled(False))


class Purity(unittest.TestCase):

    def test_imports_nothing_of_maya_or_qt(self):
        code = ("import sys; import maya_hubmotion; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; "
                "print(','.join(bad))")
        out = subprocess.run([sys.executable, "-c", code], cwd=_PLUGIN,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()


class Light(unittest.TestCase):
    """2026-10-01: the card light fades in fast, out slowly, and flashes."""

    def test_in_quicker_than_out(self):
        self.assertEqual((motion.LIGHT_IN_MS, motion.LIGHT_OUT_MS), (140, 260))
        self.assertEqual(motion.FLASH_MS, 480)

    def test_smooth_is_an_ease_in_out(self):
        self.assertEqual(motion.smooth(0.0), 0.0)
        self.assertEqual(motion.smooth(1.0), 1.0)
        self.assertAlmostEqual(motion.smooth(0.5), 0.5)
        self.assertLess(motion.smooth(0.2), 0.2)
        self.assertGreater(motion.smooth(0.8), 0.8)
        self.assertEqual(motion.smooth(2.0), 1.0)

    def test_the_flash_rises_fast_and_falls_slowly(self):
        self.assertEqual(motion.flash_at(0.0), 0.0)
        self.assertAlmostEqual(motion.flash_at(motion.FLASH_RISE), 1.0)
        self.assertEqual(motion.flash_at(1.0), 0.0)
        rise = [motion.flash_at(i * motion.FLASH_RISE / 10) for i in range(11)]
        fall = [motion.flash_at(motion.FLASH_RISE + i * (1 - motion.FLASH_RISE)
                                / 10) for i in range(11)]
        self.assertEqual(rise, sorted(rise))
        self.assertEqual(fall, sorted(fall, reverse=True))
        self.assertLess(motion.FLASH_RISE, 0.3)

    def test_a_partial_fade_takes_its_share(self):
        self.assertEqual(motion.light_ms(True, 0.0, 1.0), 140)
        self.assertEqual(motion.light_ms(False, 1.0, 0.0), 260)
        self.assertEqual(motion.light_ms(False, 0.5, 0.0), 130)
        self.assertGreaterEqual(motion.light_ms(True, 0.99, 1.0), 40)
