"""maya_filedrag: rows of Stash and Shared dragged between them and into the
scene (2026-10-21). The pure half here; the drag on a real QListWidget below.

Spec: docs/superpowers/specs/2026-10-21-stash-shared-drag-design.md
"""
import unittest

import maya_filedrag as fd


class SectionUnder(unittest.TestCase):

    def test_the_hub_s_list_and_a_popup_copy_s(self):
        self.assertEqual(fd.section_under(["skeldarStashList", "x"]), "stash")
        self.assertEqual(fd.section_under(["hubcopy3_skeldarShareList"]), "shared")

    def test_a_child_of_the_list_counts(self):
        self.assertEqual(fd.section_under(["qt_scrollarea_viewport", "skeldarShareList"]), "shared")

    def test_the_rail_icons(self):
        self.assertEqual(fd.section_under(["skeldarHubJump_stash", "rail"]), "stash")
        self.assertEqual(fd.section_under(["skeldarHubJump_shared"]), "shared")
        self.assertIsNone(fd.section_under(["skeldarHubJump_tools"]))

    def test_nothing_of_ours(self):
        self.assertIsNone(fd.section_under(["", "MayaWindow"]))
        self.assertIsNone(fd.section_under([]))


class AimFor(unittest.TestCase):

    def test_a_viewport_imports_from_either(self):
        for source in ("stash", "shared"):
            aim = fd.aim_for(source, None, True)
            self.assertEqual(aim["kind"], "import")
            self.assertEqual(aim["text"], "import into the scene")

    def test_the_other_section(self):
        self.assertEqual(fd.aim_for("stash", "shared", False)["kind"], "send")
        self.assertEqual(fd.aim_for("stash", "shared", False)["text"], "send to Shared")
        self.assertEqual(fd.aim_for("shared", "stash", False)["kind"], "stash")
        self.assertEqual(fd.aim_for("shared", "stash", False)["text"], "copy into Stash")

    def test_a_section_wins_over_a_viewport_behind_it(self):
        self.assertEqual(fd.aim_for("stash", "shared", True)["kind"], "send")

    def test_its_own_section_and_nowhere_are_nothing(self):
        self.assertEqual(fd.aim_for("stash", "stash", False)["kind"], "none")
        aim = fd.aim_for("shared", None, False)
        self.assertEqual(aim["kind"], "none")
        self.assertEqual(aim["text"], fd.NOWHERE)


class Caption(unittest.TestCase):

    def items(self, *names):
        return [fd.Item(n, "stash", n) for n in names]

    def test_one_and_several(self):
        aim = fd.aim_for("stash", "shared", False)
        self.assertEqual(fd.caption(self.items("A.fbx"), aim), ("A.fbx · send to Shared", True))
        self.assertEqual(fd.caption(self.items("A.fbx", "B.ma", "C.mb"), aim),
                         ("3 files · send to Shared", True))

    def test_nothing_is_muted(self):
        text, good = fd.caption(self.items("A.fbx"), fd.aim_for("stash", None, False))
        self.assertFalse(good)
        self.assertEqual(text, fd.NOWHERE)


class Pure(unittest.TestCase):

    def test_no_maya_or_qt_at_import(self):
        import subprocess, sys, os
        code = ("import sys; import maya_filedrag; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6')]; "
                "sys.exit(1 if bad else 0)")
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")
        self.assertEqual(subprocess.call([sys.executable, "-c", code], cwd=plugin), 0)


import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None


class Scene(unittest.TestCase):
    """FileScene with the widget lookup, the viewport and the action faked."""

    def make(self, source, names=(), viewport=False):
        acted = []
        scene = fd.FileScene(source, names_at=lambda gx, gy: list(names),
                             viewport_at=lambda gx, gy: viewport,
                             act=lambda kind, items: acted.append((kind, [i.key for i in items])) or "ok")
        return scene, acted

    def test_over_the_other_list_is_not_the_hub(self):
        scene, _ = self.make("stash", ["skeldarShareList"])
        self.assertFalse(scene.over_hub(0, 0))
        self.assertEqual(scene.target(0, 0, None)["kind"], "send")

    def test_over_its_own_list_is_the_hub(self):
        scene, _ = self.make("stash", ["skeldarStashList"])
        self.assertTrue(scene.over_hub(0, 0))

    def test_a_viewport_imports(self):
        scene, acted = self.make("shared", ["modelPanel4"], viewport=True)
        aim = scene.target(0, 0, None)
        self.assertEqual(aim["kind"], "import")
        scene.drop([fd.Item("A.fbx", "shared", "rid1")], aim)
        self.assertEqual(acted, [("import", ["rid1"])])

    def test_seams(self):
        scene, _ = self.make("stash")
        self.assertEqual(scene.drops, fd.DROPS)
        self.assertEqual(scene.icon, "archive")
        self.assertEqual(scene.caption([fd.Item("A.fbx", "stash", "A.fbx")],
                                       fd.aim_for("stash", "shared", False)),
                         (u"A.fbx \u00b7 send to Shared", True))


@unittest.skipIf(QT is None, "no Qt")
class OnAList(unittest.TestCase):
    """The real listdrag on an offscreen QListWidget named like Stash's, a
    second list named like Shared's as the target."""

    def setUp(self):
        q = QT
        self.app = q.QtWidgets.QApplication.instance() or q.QtWidgets.QApplication([])
        self.source = q.QtWidgets.QListWidget()
        self.source.setObjectName("skeldarStashList")
        self.source.addItems(["A.fbx", "B.ma"])
        self.source.resize(200, 120)
        self.source.move(3000, 3000)
        self.source.show()
        self.other = q.QtWidgets.QListWidget()
        self.other.setObjectName("skeldarShareList")
        self.other.resize(200, 120)
        self.other.move(3400, 3000)
        self.other.show()
        for w in (self.source, self.other):
            self.addCleanup(w.deleteLater)
        self.acted = []
        other = self.other

        def names_at(gx, gy):
            local = other.mapFromGlobal(QT.QtCore.QPoint(int(gx), int(gy)))
            return ["skeldarShareList"] if other.rect().contains(local) else []
        scene = fd.FileScene("stash", names_at=names_at, viewport_at=lambda gx, gy: False,
                             act=lambda kind, items: self.acted.append((kind, [i.key for i in items])) or "ok")
        items = [fd.Item("A.fbx", "stash", "A.fbx"), fd.Item("B.ma", "stash", "B.ma")]
        from maya_uebridge import listdrag
        self.drag = listdrag.attach_widget(self.source, lambda: items, scene)

    def test_a_row_dropped_on_the_other_list_sends(self):
        port = self.source.viewport()
        start = self.source.visualItemRect(self.source.item(0)).center()
        target = self.other.mapToGlobal(self.other.rect().center())
        self.drag._press = None
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton

        def send(kind, local, button, buttons):
            g = port.mapToGlobal(local)
            ev = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(local), QT.QtCore.QPointF(g),
                                      button, buttons, QT.QtCore.Qt.NoModifier)
            QT.QtWidgets.QApplication.sendEvent(port, ev)
        send(E.MouseButtonPress, start, L, L)
        send(E.MouseMove, start + QT.QtCore.QPoint(40, 0), N, L)
        self.drag.drop_at(target.x(), target.y())
        self.assertEqual(self.acted, [("send", ["A.fbx"])])


if __name__ == "__main__":
    unittest.main()
