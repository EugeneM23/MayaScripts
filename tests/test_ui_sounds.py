"""Where the animator's interface sounds play (2026-10-22): the drag ghost's
lift (the whoosh), Maya's own Delete (the fireball). The sound module is replaced by a recorder."""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_hubsound
import maya_hubqt
from maya_timebar import bar


class Recorder(object):

    def setUp(self):
        self.heard = []
        self.saved = (maya_hubsound.dragged, maya_hubsound.deleted)
        maya_hubsound.dragged = lambda: self.heard.append("drag")
        maya_hubsound.deleted = lambda: self.heard.append("delete")

    def tearDown(self):
        maya_hubsound.dragged, maya_hubsound.deleted = self.saved


class GhostWhoosh(Recorder, unittest.TestCase):

    def test_a_ghost_whooshes_once_when_it_first_shows(self):
        q = maya_hubqt.qt()
        app = q.QtWidgets.QApplication.instance() or q.QtWidgets.QApplication(sys.argv)
        ghost = maya_hubqt.ghost_class()(q.QtGui.QPixmap(8, 8), 8, 8, 1.0)
        ghost.show()
        ghost.hide()
        ghost.show()
        app.processEvents()
        ghost.close()
        ghost.deleteLater()
        self.assertEqual(self.heard, ["drag"])


class MayaDelete(Recorder, unittest.TestCase):

    def test_maya_s_delete_on_the_selection_plays_the_fireball(self):
        bar._command("delete;\n")
        self.assertEqual(self.heard, ["delete"])

    def test_a_delete_with_flags_or_another_command_is_silent(self):
        bar._command("delete -ch pCube1;")
        bar._command("setKeyframe -t 3;")
        bar._command("doDelete;")
        self.assertEqual(self.heard, [])


if __name__ == "__main__":
    unittest.main()
