"""The overlay's boundary, and that it paints what it is given.

The window itself is proved live through the bridge -- compositing over a GL
surface is not something a headless run can see. What is worth pinning here
is the boundary (`overlay.py` must never reach for Maya) and that a paint of
a real scene does not raise, which is easy to break with a namedtuple field
rename and impossible to notice until the animator sees an empty viewport.
"""

import os
import subprocess
import sys
import unittest


PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


class TestBoundary(unittest.TestCase):

    def test_overlay_never_imports_maya_cmds(self):
        script = (
            "import sys\n"
            "from maya_curveview import overlay\n"
            "print('maya.cmds' in sys.modules)\n")
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        result = subprocess.run([sys.executable, "-c", script], env=env,
                                cwd=PLUGIN, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False")

    def test_the_click_through_bits_are_the_windows_ones(self):
        from maya_curveview import overlay
        self.assertEqual(overlay.WS_EX_LAYERED, 0x00080000)
        self.assertEqual(overlay.WS_EX_TRANSPARENT, 0x00000020)
        self.assertEqual(overlay.GWL_EXSTYLE, -20)


class TestSceneShape(unittest.TestCase):

    def test_a_drawn_curve_carries_its_own_frame_and_selection(self):
        from maya_curveview import mapping, overlay
        frame = mapping.Frame(0.0, 10.0, 0.0, 1.0)
        drawn = overlay.Drawn("translateX", frame, [(0.0, 0.0)],
                              [(0.0, 0.0)], {0}, {})
        self.assertEqual(drawn.selected, {0})
        self.assertIs(drawn.frame, frame)

    def test_an_empty_scene_is_usable(self):
        from maya_curveview import overlay
        scene = overlay.empty_scene()
        self.assertEqual(scene.curves, [])
        self.assertIsNone(scene.marquee)
        self.assertLess(scene.frame.t0, scene.frame.t1)


class TestPainting(unittest.TestCase):
    """Paints a real scene offscreen and asserts the paint happened.

    A namedtuple field renamed in one module and not the other raises inside
    paintEvent, where Qt swallows it into the Script Editor and the animator
    just sees nothing drawn. This is the cheapest possible guard against
    that, and it runs headless.
    """

    def test_painting_a_full_scene_does_not_raise(self):
        script = (
            "from PySide6 import QtGui, QtWidgets\n"
            "from maya_curveview import mapping, overlay\n"
            "app = QtWidgets.QApplication.instance() "
            "or QtWidgets.QApplication([])\n"
            "frame = mapping.Frame(0.0, 100.0, -1.0, 1.0)\n"
            "drawn = overlay.Drawn('translateX', frame,\n"
            "                      [(t, 0.5) for t in range(0, 101, 5)],\n"
            "                      [(0.0, 0.0), (50.0, 1.0)], {1},\n"
            "                      {1: (10.0, 20.0)})\n"
            "scene = overlay.Scene(frame, [drawn], 42.0, 'hello',\n"
            "                      (10.0, 10.0, 80.0, 60.0))\n"
            "widget = overlay.CurveOverlay()\n"
            "widget.resize(400, 300)\n"
            "widget.set_scene(scene)\n"
            "image = QtGui.QImage(400, 300, QtGui.QImage.Format_ARGB32)\n"
            "image.fill(0)\n"
            "widget.render(image)\n"
            "print('painted', widget.paint_count)\n")
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        result = subprocess.run([sys.executable, "-c", script], env=env,
                                cwd=PLUGIN, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("painted", result.stdout)
        count = int(result.stdout.strip().split()[-1])
        self.assertGreaterEqual(count, 1, "paintEvent never ran")

    def test_painting_an_empty_scene_does_not_raise(self):
        script = (
            "from PySide6 import QtGui, QtWidgets\n"
            "from maya_curveview import overlay\n"
            "app = QtWidgets.QApplication.instance() "
            "or QtWidgets.QApplication([])\n"
            "widget = overlay.CurveOverlay()\n"
            "widget.resize(200, 100)\n"
            "widget.set_scene(overlay.empty_scene())\n"
            "image = QtGui.QImage(200, 100, QtGui.QImage.Format_ARGB32)\n"
            "image.fill(0)\n"
            "widget.render(image)\n"
            "print('painted', widget.paint_count)\n")
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        result = subprocess.run([sys.executable, "-c", script], env=env,
                                cwd=PLUGIN, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(int(result.stdout.strip().split()[-1]), 1)


if __name__ == "__main__":
    unittest.main()
