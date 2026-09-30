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


if __name__ == "__main__":
    unittest.main()
