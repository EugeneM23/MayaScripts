"""The Cascadeur bridge window, offscreen. No Cascadeur, Unreal or network."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

from skeldar_cascadeur import window  # noqa: E402
from maya_uebridge import records  # noqa: E402


def clip(name):
    return records.AnimRecord(name=name, package="/Game/" + name, skeleton="",
                              frames=10, length=0.3, fps=30.0, source="unreal",
                              path="", clip="", fmt="")


class FakeBridge(object):
    def __init__(self):
        self.records = [clip("A_Jump"), clip("B_Walk")]
        self.target = None
        self.calls = []

    def refresh(self, project=None):
        self.calls.append("refresh")
        return "2 animation(s) in Unreal"

    def import_clips(self, picked, project=None):
        self.calls.append(("import", [r.name for r in picked]))
        return "done"

    def export_to_uasset(self, record=None, project=None):
        self.calls.append(("export", record.name if record else None))
        return "exported"

    def send_to_shared(self, typed_name, author, project=None):
        self.calls.append(("send", typed_name, author))
        return "sent"


class Window(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_lists_every_clip(self):
        win = window.BridgeWindow(FakeBridge())
        win.populate()
        self.assertEqual(win.visible_names(), ["A_Jump", "B_Walk"])

    def test_search_filters_the_list(self):
        win = window.BridgeWindow(FakeBridge())
        win.populate()
        win.search.setText("walk")
        self.assertEqual(win.visible_names(), ["B_Walk"])

    def test_import_button_passes_the_selection(self):
        bridge = FakeBridge()
        win = window.BridgeWindow(bridge)
        win.populate()
        win.list.item(0).setSelected(True)
        win.import_selected()
        self.assertIn(("import", ["A_Jump"]), bridge.calls)
        self.assertIn("done", win.status.text())

    def test_export_uses_the_single_selected_row(self):
        bridge = FakeBridge()
        win = window.BridgeWindow(bridge)
        win.populate()
        win.list.item(1).setSelected(True)
        win.export_selected()
        self.assertIn(("export", "B_Walk"), bridge.calls)

    def test_export_with_no_selection_asks_the_bridge_for_its_target(self):
        bridge = FakeBridge()
        win = window.BridgeWindow(bridge)
        win.populate()
        win.export_selected()
        self.assertIn(("export", None), bridge.calls)

    def test_send_passes_name_and_author(self):
        bridge = FakeBridge()
        win = window.BridgeWindow(bridge)
        win.author.setText("Yevhen")
        win.name.setText("attack")
        win.send_selected()
        self.assertIn(("send", "attack", "Yevhen"), bridge.calls)


if __name__ == "__main__":
    unittest.main()
