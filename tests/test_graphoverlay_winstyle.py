"""The Win32 styles the overlay stands on."""

import os
import subprocess
import sys
import unittest

from maya_graphoverlay import winstyle

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


class WithBits(unittest.TestCase):

    def test_on_and_off(self):
        on = winstyle.with_bits(0x100, on=winstyle.WS_EX_LAYERED
                                | winstyle.WS_EX_TRANSPARENT)
        self.assertEqual(on, 0x100 | 0x80000 | 0x20)
        self.assertEqual(winstyle.with_bits(on, off=winstyle.WS_EX_TRANSPARENT),
                         0x100 | 0x80000)

    def test_it_stays_32_bits(self):
        self.assertEqual(winstyle.with_bits(-1, off=0x20), 0xFFFFFFDF)


class OnThisMachine(unittest.TestCase):

    def test_windows_is_here(self):
        self.assertTrue(winstyle.available())

    def test_alt_answers_a_bool(self):
        self.assertIn(winstyle.alt_down(), (True, False))

    def test_the_ghost_is_one_level_of_alpha(self):
        self.assertEqual(winstyle.GHOST_ALPHA, 1)

    def test_gl_kept_is_harmless_with_no_context(self):
        with winstyle.gl_kept():
            pass

    def test_a_capture_of_nothing_is_none(self):
        self.assertIsNone(winstyle.capture(0, 0, 0))

    def test_a_capture_of_the_desktop_has_the_size_asked(self):
        """The desktop window (GetDesktopWindow) always exists; the bytes
        come back as width x height x 4, whatever they show."""
        import ctypes
        desktop = ctypes.windll.user32.GetDesktopWindow()
        data = winstyle.capture(desktop, 8, 5)
        if data is not None:                       # a locked session: None
            self.assertEqual(len(data), 8 * 5 * 4)


class Purity(unittest.TestCase):

    def test_it_imports_neither_maya_nor_qt(self):
        code = ("import sys; import maya_graphoverlay.winstyle; "
                "print([m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'shiboken6')])")
        result = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stdout.strip(), "[]", result.stderr)


if __name__ == "__main__":
    unittest.main()
