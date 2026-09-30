"""The see-through window: Qt only, never Maya."""

import os
import subprocess
import sys
import unittest

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


def _run(code):
    return subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                          capture_output=True, text=True, timeout=120)


class Purity(unittest.TestCase):

    def test_the_glass_never_imports_maya_cmds(self):
        result = _run("import os, sys; "
                      "os.environ['QT_QPA_PLATFORM'] = 'offscreen'; "
                      "import maya_graphoverlay.glass; "
                      "print('maya.cmds' in sys.modules)")
        self.assertEqual(result.stdout.strip().splitlines()[-1:], ["False"],
                         result.stderr)


class TheFrame(unittest.TestCase):

    def test_it_holds_the_array_and_shows_it_as_argb32(self):
        result = _run(
            "import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; "
            "import numpy as np; from PySide6 import QtWidgets, QtGui; "
            "app = QtWidgets.QApplication([]); "
            "from maya_graphoverlay import glass; g = glass.Glass(); "
            "a = np.zeros((3, 4, 4), np.uint8); a[1, 2] = (35, 35, 255, 255); "
            "g.set_frame(a); im = g.frame(); c = im.pixelColor(2, 1); "
            "print(im.width(), im.height(), "
            "im.format() == QtGui.QImage.Format_ARGB32, c.red(), c.green(), "
            "c.blue(), c.alpha(), im.pixelColor(0, 0).alpha(), g.objectName())")
        self.assertEqual(result.stdout.strip().splitlines()[-1:],
                         ["4 3 True 255 35 35 255 0 skeldarGraphOverlayGlass"],
                         result.stderr)


class TheChrome(unittest.TestCase):
    """The Graph Editor's own chrome drawn opaque, the keyed curve area at
    its offset inside it (2026-09-30: the channel list and the toolbar back)."""

    def test_the_picture_is_the_chrome_and_the_curves_at_their_offset(self):
        result = _run(
            "import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; "
            "import numpy as np; from PySide6 import QtWidgets, QtGui, QtCore; "
            "app = QtWidgets.QApplication([]); "
            "from maya_graphoverlay import glass; g = glass.Glass(); "
            "g.resize(10, 6); "
            "band = QtGui.QImage(3, 6, QtGui.QImage.Format_ARGB32); "
            "band.fill(QtGui.QColor(90, 90, 90)); g.set_chrome([(band, 0, 0)]); "
            "a = np.zeros((6, 7, 4), np.uint8); a[2, 4] = (35, 35, 255, 255); "
            "g.set_frame(a, offset=(3, 0)); p = g.picture(); "
            "c = p.pixelColor(1, 1); k = p.pixelColor(7, 2); e = p.pixelColor(5, 5); "
            "print(p.width(), p.height(), c.red(), c.alpha(), k.red(), k.alpha(), e.alpha())")
        self.assertEqual(result.stdout.strip().splitlines()[-1:],
                         ["10 6 90 255 255 255 0"], result.stderr)


if __name__ == "__main__":
    unittest.main()
